"""
Data collection service — fetches financial data for stocks and stores in DB.
Supports single, batch, incremental, and market-based collection.
"""
import asyncio
import csv
import io
import logging
import random
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.financial import FinancialQuarterly
from app.models.stock import StockBasic
from app.services.data_fetcher import (
    search_stock,
    get_quarterly_data,
    get_stock_basic_info,
    _sync_get_quarterly_data,
    _bs_lock,
    _login,
    _logout,
    BaostockSessionPool,
)
from app.services.financial_calc import compute_10ps_valuation
from app.routers.stock import _upsert_stock, _upsert_quarters

logger = logging.getLogger(__name__)

# Default quarters to fetch: 16 display + 5 for YoY/TTM reference
DEFAULT_QUARTERS = 21

# Concurrency: number of parallel baostock sessions
MAX_CONCURRENT_STOCKS = 3
# Anti-crawl: random delay range (seconds) between baostock requests per session
_anti_crawl_delay = (0.3, 0.8)

# In-memory task tracker for batch operations
_batch_tasks: dict[str, dict] = {}


def _new_task_id() -> str:
    return uuid.uuid4().hex[:12]


async def collect_single_stock(keyword: str, db: AsyncSession) -> dict:
    """
    Collect financial data for a single stock.
    Returns summary of collected data.
    """
    keyword = keyword.strip()
    if not keyword:
        return {"success": False, "error": "关键词不能为空"}

    # 1. Search for stock
    search_results = await search_stock(keyword)
    if not search_results:
        return {"success": False, "error": f"未找到股票: {keyword}"}

    match = search_results[0]
    stock_code = match["stock_code"]
    stock_name = match.get("stock_name", "")

    # 2. Fetch quarterly data
    try:
        raw_quarters = await get_quarterly_data(stock_code, DEFAULT_QUARTERS)
    except Exception as e:
        logger.error(f"Failed to fetch quarterly data for {stock_code}: {e}")
        return {"success": False, "error": f"获取财务数据失败: {e}", "stockCode": stock_code}

    if not raw_quarters:
        return {"success": False, "error": "未获取到财务数据", "stockCode": stock_code}

    # 3. Get basic info
    basic = await get_stock_basic_info(stock_code, quarters_data=raw_quarters)
    if not basic:
        basic = match

    # 4. Upsert into DB
    try:
        stock = await _upsert_stock(match, basic, db)
        await _upsert_quarters(stock_code, raw_quarters, db)
    except Exception as e:
        logger.error(f"Failed to upsert data for {stock_code}: {e}")
        return {"success": False, "error": f"存储数据失败: {e}", "stockCode": stock_code}

    # 5. Query stored data summary
    stmt = (
        select(FinancialQuarterly)
        .where(FinancialQuarterly.stock_code == stock_code)
        .order_by(FinancialQuarterly.report_date)
    )
    result = await db.execute(stmt)
    stored = list(result.scalars().all())

    quarters_in_db = len(stored)
    earliest = str(stored[0].report_date) if stored else None
    latest = str(stored[-1].report_date) if stored else None
    earliest_q = stored[0].quarter if stored else None
    latest_q = stored[-1].quarter if stored else None

    return {
        "success": True,
        "stockCode": stock_code,
        "stockName": stock_name,
        "quartersCollected": len(raw_quarters),
        "quartersInDb": quarters_in_db,
        "earliestQuarter": earliest_q,
        "latestQuarter": latest_q,
        "earliestDate": earliest,
        "latestDate": latest,
    }


async def check_stock_status(stock_code: str, db: AsyncSession) -> dict:
    """Check what data exists in DB for a stock."""
    # Try to find stock by code or name
    stmt = select(StockBasic).where(
        (StockBasic.stock_code == stock_code)
        | (StockBasic.stock_name == stock_code)
        | StockBasic.stock_code.like(f"{stock_code}.%")
    )
    result = await db.execute(stmt)
    stock = result.scalars().first()

    if not stock:
        return {
            "stockCode": stock_code,
            "inDb": False,
            "quartersInDb": 0,
        }

    # Count quarters
    stmt = (
        select(FinancialQuarterly)
        .where(FinancialQuarterly.stock_code == stock.stock_code)
        .order_by(FinancialQuarterly.report_date)
    )
    result = await db.execute(stmt)
    stored = list(result.scalars().all())

    quarters_in_db = len(stored)
    earliest = stored[0].quarter if stored else None
    latest = stored[-1].quarter if stored else None

    return {
        "stockCode": stock.stock_code,
        "stockName": stock.stock_name,
        "inDb": True,
        "quartersInDb": quarters_in_db,
        "earliestQuarter": earliest,
        "latestQuarter": latest,
    }


def get_task_status(task_id: str) -> dict | None:
    """Get the status of a batch task."""
    return _batch_tasks.get(task_id)


async def start_batch_collect(
    keywords: list[str], incremental: bool
) -> dict:
    """Start a batch collection task in the background."""
    task_id = _new_task_id()
    keywords = [kw.strip() for kw in keywords if kw.strip()]

    _batch_tasks[task_id] = {
        "taskId": task_id,
        "status": "running",
        "total": len(keywords),
        "completed": 0,
        "failed": 0,
        "skipped": 0,
        "currentStock": "",
        "errors": [],
        "results": [],
        "startedAt": datetime.now().isoformat(),
    }

    # Launch background task
    asyncio.create_task(_run_batch(task_id, keywords, incremental))

    return {"taskId": task_id, "totalStocks": len(keywords)}


def _sync_fetch_quarterly_data(
    stock_code: str,
    quarters: int = DEFAULT_QUARTERS,
) -> dict:
    """Fetch quarterly data for a single stock in a thread.

    Creates its own baostock session (sessions can't be shared across threads).
    Uses quarter=0 (batch by year) → 25 calls instead of 100.
    Returns dict with: success, stockCode, quartersCollected, quarters, error
    """
    import time

    _bs_lock.acquire()
    try:
        bs, lg = _login()
        raw_quarters = _sync_get_quarterly_data(stock_code, quarters, bs_session=bs)
        _logout(bs, lg)

        # Anti-crawl: random delay
        delay = random.uniform(*_anti_crawl_delay)
        time.sleep(delay)

        if not raw_quarters:
            return {
                "success": False,
                "stockCode": stock_code,
                "error": "未获取到财务数据"
            }

        return {
            "success": True,
            "stockCode": stock_code,
            "quartersCollected": len(raw_quarters),
            "quarters": raw_quarters
        }

    except Exception as e:
        logger.error(f"Batch collect failed for {stock_code}: {e}")
        return {"success": False, "stockCode": stock_code, "error": str(e)}

    finally:
        _bs_lock.release()


async def _collect_one_stock(kw: str, incremental: bool, task: dict):
    """Collect data for a single stock with anti-crawl delay and thread-safe task updates."""
    task["currentStock"] = kw
    try:
        async with async_session() as db:
            # Incremental check
            if incremental:
                status = await check_stock_status(kw, db)
                if status.get("inDb") and status.get("quartersInDb", 0) >= 16:
                    latest_q = status.get("latestQuarter", "")
                    if latest_q and _is_recent_quarter(latest_q):
                        with threading.Lock():
                            task["skipped"] += 1
                            task["completed"] += 1
                            task["results"].append({
                                "keyword": kw,
                                "status": "skipped",
                                "reason": f"已有{status['quartersInDb']}季度数据，最新{latest_q}",
                            })
                        return

            result = await collect_single_stock(kw, db)
            with threading.Lock():
                if result["success"]:
                    task["completed"] += 1
                    task["results"].append({
                        "keyword": kw,
                        "status": "success",
                        "stockCode": result["stockCode"],
                        "stockName": result["stockName"],
                        "quartersInDb": result["quartersInDb"],
                    })
                else:
                    task["failed"] += 1
                    task["errors"].append({
                        "keyword": kw,
                        "error": result.get("error", "未知错误"),
                    })
    except Exception as e:
        with threading.Lock():
            task["failed"] += 1
            task["errors"].append({
                "keyword": kw,
                "error": str(e),
            })
        logger.error(f"Batch collect error for {kw}: {e}")

    # Anti-crawl: random delay between requests
    delay = random.uniform(*_anti_crawl_delay)
    await asyncio.sleep(delay)


async def _run_batch(task_id: str, keywords: list[str], incremental: bool):
    """Run batch collection with thread pool for parallel baostock calls."""
    task = _batch_tasks[task_id]

    # Phase 1: Fetch all quarterly data in parallel using thread pool
    loop = asyncio.get_event_loop()
    fetch_results = {}

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_STOCKS) as executor:
        future_to_kw = {
            executor.submit(_sync_fetch_quarterly_data, kw, DEFAULT_QUARTERS): kw
            for kw in keywords
        }
        for future in as_completed(future_to_kw):
            kw = future_to_kw[future]
            try:
                fetch_results[kw] = future.result()
            except Exception as e:
                fetch_results[kw] = {
                    "success": False,
                    "stockCode": kw,
                    "error": str(e)
                }

    # Phase 2: Process results and upsert to DB (async, one at a time for DB safety)
    for kw in keywords:
        result = fetch_results.get(kw, {"success": False, "error": "No result"})

        if result["success"]:
            try:
                async with async_session() as db:
                    search_results = await search_stock(kw)
                    if search_results:
                        match = search_results[0]
                        stock_code = result["stockCode"]
                        stock_name = match.get("stock_name", "")

                        # Get basic info
                        basic = await get_stock_basic_info(
                            stock_code,
                            quarters_data=result["quarters"]
                        )
                        if not basic:
                            basic = match

                        # Upsert
                        stock = await _upsert_stock(match, basic, db)
                        await _upsert_quarters(
                            stock_code,
                            result["quarters"],
                            db
                        )

                        # Query stored data
                        stmt = (
                            select(FinancialQuarterly)
                            .where(FinancialQuarterly.stock_code == stock_code)
                            .order_by(FinancialQuarterly.report_date)
                        )
                        db_result = await db.execute(stmt)
                        stored = list(db_result.scalars().all())

                        with threading.Lock():
                            task["completed"] += 1
                            task["results"].append({
                                "keyword": kw,
                                "status": "success",
                                "stockCode": stock_code,
                                "stockName": stock_name,
                                "quartersInDb": len(stored),
                            })
                    else:
                        with threading.Lock():
                            task["failed"] += 1
                            task["errors"].append({
                                "keyword": kw,
                                "error": "未找到股票",
                            })
            except Exception as e:
                with threading.Lock():
                    task["failed"] += 1
                    task["errors"].append({
                        "keyword": kw,
                        "error": str(e),
                    })
                logger.error(f"DB upsert error for {kw}: {e}")
        else:
            with threading.Lock():
                task["failed"] += 1
                task["errors"].append({
                    "keyword": kw,
                    "error": result.get("error", "未知错误"),
                })

    task["status"] = "complete"
    task["currentStock"] = ""


def _is_recent_quarter(quarter_label: str) -> bool:
    """Check if a quarter label like '26Q1' is within the last 2 quarters."""
    try:
        yr = int("20" + quarter_label[:2])
        qn = int(quarter_label[3])
        now = date.today()
        current_yr = now.year
        current_month = now.month
        current_qn = (current_month - 1) // 3 + 1
        # Consider "recent" if within last 2 quarters
        quarters_diff = (current_yr - yr) * 4 + (current_qn - qn)
        return quarters_diff <= 2
    except (ValueError, IndexError):
        return False


async def start_market_collect(
    market: str, incremental: bool
) -> dict:
    """Start collection for all stocks in a market — returns immediately with a task ID."""
    task_id = _new_task_id()

    # Create task entry immediately so the frontend can start polling
    _batch_tasks[task_id] = {
        "taskId": task_id,
        "status": "running",
        "total": 0,
        "completed": 0,
        "failed": 0,
        "skipped": 0,
        "currentStock": "正在获取股票列表...",
        "errors": [],
        "results": [],
        "startedAt": datetime.now().isoformat(),
    }

    # Launch background task: fetch stocks then batch collect
    asyncio.create_task(_run_market_collect(task_id, market, incremental))

    return {"taskId": task_id, "total": 0}


async def _run_market_collect(task_id: str, market: str, incremental: bool):
    """Background task: fetch market stock list then run parallel batch collection."""
    task = _batch_tasks[task_id]
    try:
        stocks = await _get_market_stocks(market)
    except Exception as e:
        task["status"] = "failed"
        task["errors"].append({"keyword": market, "error": f"获取股票列表失败: {e}"})
        task["currentStock"] = ""
        logger.error(f"Market collect failed for {market}: {e}")
        return

    if not stocks:
        task["status"] = "failed"
        task["errors"].append({"keyword": market, "error": f"市场 {market} 没有找到股票"})
        task["currentStock"] = ""
        return

    task["total"] = len(stocks)

    # Phase 1: Fetch all quarterly data in parallel using thread pool
    fetch_results = {}

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_STOCKS) as executor:
        future_to_kw = {
            executor.submit(_sync_fetch_quarterly_data, kw, DEFAULT_QUARTERS): kw
            for kw in stocks
        }
        for future in as_completed(future_to_kw):
            kw = future_to_kw[future]
            try:
                fetch_results[kw] = future.result()
            except Exception as e:
                fetch_results[kw] = {
                    "success": False,
                    "stockCode": kw,
                    "error": str(e)
                }

    # Phase 2: Process results and upsert to DB
    for kw in stocks:
        result = fetch_results.get(kw, {"success": False, "error": "No result"})

        if result["success"]:
            try:
                async with async_session() as db:
                    search_results = await search_stock(kw)
                    if search_results:
                        match = search_results[0]
                        stock_code = result["stockCode"]
                        stock_name = match.get("stock_name", "")

                        # Get basic info
                        basic = await get_stock_basic_info(
                            stock_code,
                            quarters_data=result["quarters"]
                        )
                        if not basic:
                            basic = match

                        # Upsert
                        stock = await _upsert_stock(match, basic, db)
                        await _upsert_quarters(
                            stock_code,
                            result["quarters"],
                            db
                        )

                        # Query stored data
                        stmt = (
                            select(FinancialQuarterly)
                            .where(FinancialQuarterly.stock_code == stock_code)
                            .order_by(FinancialQuarterly.report_date)
                        )
                        db_result = await db.execute(stmt)
                        stored = list(db_result.scalars().all())

                        with threading.Lock():
                            task["completed"] += 1
                            task["results"].append({
                                "keyword": kw,
                                "status": "success",
                                "stockCode": stock_code,
                                "stockName": stock_name,
                                "quartersInDb": len(stored),
                            })
                    else:
                        with threading.Lock():
                            task["failed"] += 1
                            task["errors"].append({
                                "keyword": kw,
                                "error": "未找到股票",
                            })
            except Exception as e:
                with threading.Lock():
                    task["failed"] += 1
                    task["errors"].append({
                        "keyword": kw,
                        "error": str(e),
                    })
                logger.error(f"DB upsert error for {kw}: {e}")
        else:
            with threading.Lock():
                task["failed"] += 1
                task["errors"].append({
                    "keyword": kw,
                    "error": result.get("error", "未知错误"),
                })

    task["status"] = "complete"
    task["currentStock"] = ""


async def _get_market_stocks(market: str) -> list[str]:
    """Get all stock codes for a given market."""
    # Market definitions
    MARKET_CONFIG = {
        "gem": {"name": "创业板", "exchange": "SZ", "prefixes": ["300", "301"]},
        "star": {"name": "科创板", "exchange": "SH", "prefixes": ["688", "689"]},
        "sh_main": {"name": "上海主板", "exchange": "SH", "prefixes": ["600", "601", "603", "605"]},
        "sz_main": {"name": "深圳主板", "exchange": "SZ", "prefixes": ["000", "001", "002", "003"]},
        "all": {"name": "全市场", "exchange": None, "prefixes": None},  # all markets
    }

    config = MARKET_CONFIG.get(market)
    if not config:
        raise ValueError(f"未知市场: {market}")

    # Use baostock to get stock list
    import baostock as bs
    _bs_lock.acquire()
    lg = bs.login()
    try:
        rs = bs.query_stock_basic()
        if rs.error_code != "0":
            raise RuntimeError(f"baostock query_stock_basic failed: {rs.error_msg}")
        
        rows = []
        while rs.next():
            rows.append(rs.get_row_data())

        logger.info(f"baostock returned {len(rows)} total stocks for market={market}")

        stocks = []
        for row in rows:
            code = row[0] if row else ""  # e.g. "sh.600000"
            if "." not in code:
                continue
            exchange_part, code_part = code.split(".", 1)
            exchange = exchange_part.upper()

            # For "all" market, include all stocks
            if market == "all":
                stocks.append(f"{code_part}.{exchange}")
                continue

            # Filter by exchange
            if exchange != config["exchange"]:
                continue

            # Filter by code prefix
            if any(code_part.startswith(p) for p in config["prefixes"]):
                stocks.append(f"{code_part}.{exchange}")

        logger.info(f"Filtered {len(stocks)} stocks for market={market} (exchange={config['exchange']}, prefixes={config['prefixes']})")
        return stocks
    finally:
        bs.logout()
        _bs_lock.release()


def get_market_info() -> list[dict]:
    """Return market definitions with metadata."""
    return [
        {"id": "all", "name": "全市场", "codePrefix": "全部", "exchange": "ALL"},
        {"id": "gem", "name": "创业板", "codePrefix": "300/301", "exchange": "SZ"},
        {"id": "star", "name": "科创板", "codePrefix": "688/689", "exchange": "SH"},
        {"id": "sh_main", "name": "上海主板", "codePrefix": "600/601/603/605", "exchange": "SH"},
        {"id": "sz_main", "name": "深圳主板", "codePrefix": "000/001/002/003", "exchange": "SZ"},
    ]


def parse_csv_keywords(file_content: bytes) -> list[str]:
    """Parse stock keywords from CSV file content (first column)."""
    keywords = []
    try:
        text = file_content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        text = file_content.decode("gbk", errors="ignore")

    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if row and row[0].strip():
            val = row[0].strip()
            # Skip header-like rows
            if val.lower() in ("股票代码", "代码", "code", "symbol", "stock"):
                continue
            keywords.append(val)

    return keywords
