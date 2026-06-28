"""
Baostock data fetcher — wraps the synchronous baostock API
and runs it in a thread pool so it plays nicely with async FastAPI.
"""
import asyncio
import logging
import threading
from datetime import date, datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# baostock uses a global singleton socket — all operations must be serialized
_bs_lock = threading.Lock()


def _login():
    import baostock as bs
    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"baostock login failed: {lg.error_msg}")
    return bs, lg


def _logout(bs, lg):
    try:
        bs.logout()
    except Exception:
        pass


def _query_to_df(rs) -> pd.DataFrame:
    rows = []
    while (rs.error_code == '0') and rs.next():
        rows.append(rs.get_row_data())
    return pd.DataFrame(rows, columns=rs.fields)


def _sync_search_stock(keyword: str) -> list[dict]:
    """Search stock by code or name, return list of matches."""
    with _bs_lock:
        bs, lg = _login()
        try:
            # Try exact code match first
            code = keyword.strip()
            if code.isdigit() and len(code) == 6:
                # Determine exchange from code prefix
                if code.startswith(('6', '9')):
                    full_code = f"sh.{code}"
                    exchange = "SH"
                else:
                    full_code = f"sz.{code}"
                    exchange = "SZ"
                rs = bs.query_stock_basic(code=full_code)
                df = _query_to_df(rs)
                if not df.empty:
                    row = df.iloc[0]
                    return [{
                        "stock_code": f"{code}.{exchange}",
                        "stock_name": row.get("code_name", ""),
                        "exchange": exchange,
                        "ipo_date": row.get("ipoDate", ""),
                    }]

            # Fallback: search all stocks by name
            rs = bs.query_stock_basic()
            df = _query_to_df(rs)
            if df.empty:
                return []
            mask = df["code_name"].str.contains(keyword, na=False) | df["code"].str.contains(keyword, na=False)
            matches = df[mask]
            results = []
            for _, row in matches.head(10).iterrows():
                code = row["code"]
                ex = code.split(".")[0].upper() if "." in code else ""
                pure_code = code.split(".")[1] if "." in code else code
                results.append({
                    "stock_code": f"{pure_code}.{ex}" if ex else code,
                    "stock_name": row.get("code_name", ""),
                    "exchange": ex,
                    "ipo_date": row.get("ipoDate", ""),
                })
            return results
        finally:
            _logout(bs, lg)


def _sync_get_quarterly_data(stock_code: str, quarters: int = 16, bs_session=None) -> list[dict]:
    """Fetch quarterly financial data for a stock.

    Optimizations:
    - Uses quarter=0 (batch by year) -> 25 calls instead of 100 per stock
    - Accepts optional bs_session for connection reuse in batch mode
    - Releases _bs_lock between baostock and akshare phases for true parallelism
    """
    own_session = False
    if bs_session is None:
        _bs_lock.acquire()
        bs, lg = _login()
        own_session = True
    else:
        bs = bs_session

    # ---- Phase 1: baostock queries (holds _bs_lock) ----
    try:
        # Convert code format: 301536.SZ -> sz.301536
        parts = stock_code.split(".")
        if len(parts) == 2:
            bs_code = f"{parts[1].lower()}.{parts[0]}"
        else:
            bs_code = stock_code

        current_year = datetime.now().year
        years = range(current_year, current_year - 5, -1)
        quarters_list = [1, 2, 3, 4]

        profit_by_date = {}
        balance_by_date = {}
        growth_by_date = {}
        cashflow_by_date = {}

        for year in years:
            for q in quarters_list:
                try:
                    rs = bs.query_profit_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                profit_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Profit data fetch failed for {bs_code} {year}Q{q}: {e}")

        for year in years:
            for q in quarters_list:
                try:
                    rs = bs.query_balance_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                balance_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Balance data fetch failed for {bs_code} {year}Q{q}: {e}")

        for year in years:
            for q in quarters_list:
                try:
                    rs = bs.query_growth_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                growth_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Growth data fetch failed for {bs_code} {year}Q{q}: {e}")

        for year in years:
            for q in quarters_list:
                try:
                    rs = bs.query_cash_flow_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                cashflow_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Cash flow data fetch failed for {bs_code} {year}Q{q}: {e}")

        operation_by_date = {}
        for year in years:
            for q in quarters_list:
                try:
                    rs = bs.query_operation_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                operation_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Operation data fetch failed for {bs_code} {year}Q{q}: {e}")

        all_dates = sorted(profit_by_date.keys(), reverse=True)
        if not all_dates:
            return []
    finally:
        # Release baostock session/lock BEFORE akshare HTTP calls
        if own_session:
            _logout(bs, lg)
            _bs_lock.release()

    # ---- Phase 2: akshare HTTP (no lock held — other threads can use baostock) ----
    akshare_data = {}
    try:
        akshare_data = _sync_fetch_akshare_supplement(stock_code)
    except Exception as e:
        logger.warning(f"akshare supplement fetch failed for {stock_code}: {e}")

    for ak_date in akshare_data:
        if ak_date not in profit_by_date:
            profit_by_date[ak_date] = {"_from_akshare": True}
            all_dates = sorted(profit_by_date.keys(), reverse=True)

    # ---- Phase 3: merge and build results ----
    results = []
    for stat_date in all_dates[:quarters]:
        quarter_label = _format_quarter(stat_date)
        profit = profit_by_date.get(stat_date, {})
        balance = balance_by_date.get(stat_date, {})
        growth = growth_by_date.get(stat_date, {})
        cashflow = cashflow_by_date.get(stat_date, {})
        operation = operation_by_date.get(stat_date, {}) if operation_by_date else {}

        # ---- Profit data (absolute values in yuan) ----
        net_profit_abs = _safe_float(profit.get("netProfit"))
        revenue_abs = _safe_float(profit.get("MBRevenue"))
        np_margin = _safe_float(profit.get("npMargin"))
        gp_margin = _safe_float(profit.get("gpMargin"))
        roe_avg = _safe_float(profit.get("roeAvg"))
        eps_ttm = _safe_float(profit.get("epsTTM"))

        if revenue_abs is None and net_profit_abs and np_margin and np_margin != 0:
            revenue_abs = net_profit_abs / np_margin

        # ---- Merge akshare supplement data ----
        ak_quarter = akshare_data.get(stat_date, {})
        ak_revenue = ak_quarter.get("revenue_total")
        if ak_revenue is not None:
            revenue_abs = ak_revenue
        deducted_net_profit_abs = ak_quarter.get("deducted_net_profit")

        # ---- Balance data (ratios only) ----
        current_ratio = _safe_float(balance.get("currentRatio"))
        liability_to_asset = _safe_float(balance.get("liabilityToAsset"))
        debt_ratio_calc = None
        if liability_to_asset is not None:
            debt_ratio_calc = liability_to_asset * 100

        # ---- Growth data ----
        deducted_net_profit_yoy = None
        revenue_yoy = None

        # ---- Cash flow data (ratios) ----
        cfo_to_np = _safe_float(cashflow.get("CFOToNP"))
        operating_cashflow = None
        if cfo_to_np is not None and net_profit_abs is not None:
            operating_cashflow = cfo_to_np * net_profit_abs

        # ---- Derived: total_assets (estimate from asset turnover) ----
        total_assets_est = None
        total_equity_est = None
        asset_turn = _safe_float(operation.get("AssetTurnRatio"))
        if asset_turn and asset_turn > 0 and revenue_abs:
            total_assets_est = revenue_abs / asset_turn
            if liability_to_asset is not None:
                total_equity_est = total_assets_est * (1 - liability_to_asset)

        # ---- Derived: ROA ----
        roa_calc = None
        if net_profit_abs is not None and total_assets_est and total_assets_est > 0:
            roa_calc = net_profit_abs / total_assets_est

        row = {
            "quarter": quarter_label,
            "report_date": stat_date,
            "revenue_yoy": revenue_yoy,
            "deducted_net_profit_yoy": deducted_net_profit_yoy,
            "gross_margin": gp_margin,
            "net_margin": np_margin,
            "roe": roe_avg,
            "roa": roa_calc,
            "eps": eps_ttm,
            "revenue": revenue_abs,
            "net_profit": net_profit_abs,
            "deducted_net_profit": deducted_net_profit_abs,
            "deducted_net_profit_ttm": None,
            "total_assets": total_assets_est,
            "total_equity": total_equity_est,
            "operating_cashflow": operating_cashflow,
            "debt_ratio": debt_ratio_calc,
            "current_ratio": current_ratio,
        }

        results.append(row)

    return results


def _format_quarter(stat_date: str) -> str:
    """Convert '2024-03-31' to '24Q1'."""
    try:
        dt = datetime.strptime(stat_date, "%Y-%m-%d")
        q = (dt.month - 1) // 3 + 1
        return f"{str(dt.year)[2:]}Q{q}"
    except Exception:
        return stat_date


def _safe_float(val) -> Optional[float]:
    if val is None or val == "" or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return round(float(val), 4)
    except (ValueError, TypeError):
        return None


def _sync_get_monthly_klines(stock_code: str, months: int = 60) -> list[dict]:
    """Fetch monthly K-line data for trend analysis."""
    _bs_lock.acquire()
    bs, lg = _login()
    try:
        bs_code = _to_bs_code(stock_code)
        end_date = date.today().strftime("%Y-%m-%d")
        # Approximate start date: go back `months` months
        start_year = date.today().year - (months // 12 + 1)
        start_date = f"{start_year}-01-01"

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume,amount,turn,pctChg",
            start_date=start_date,
            end_date=end_date,
            frequency="m",  # monthly
            adjustflag="2",  # 前复权
        )
        df = _query_to_df(rs)
        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            results.append({
                "date": row.get("date", ""),
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "close": _safe_float(row.get("close")),
                "volume": _safe_float(row.get("volume")),
                "amount": _safe_float(row.get("amount")),
                "turn": _safe_float(row.get("turn")),
                "pct_chg": _safe_float(row.get("pctChg")),
            })
        return results
    finally:
        _logout(bs, lg)
        _bs_lock.release()


def _sync_get_daily_klines(stock_code: str, days: int = 120) -> list[dict]:
    """Fetch daily K-line data for big-yang detection."""
    _bs_lock.acquire()
    bs, lg = _login()
    try:
        bs_code = _to_bs_code(stock_code)
        end_date = date.today().strftime("%Y-%m-%d")
        # Go back `days` calendar days (add buffer for weekends/holidays)
        from datetime import timedelta
        start_date = (date.today() - timedelta(days=int(days * 1.6))).strftime("%Y-%m-%d")

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg,isST",
            start_date=start_date,
            end_date=end_date,
            frequency="d",  # daily
            adjustflag="2",  # 前复权
        )
        df = _query_to_df(rs)
        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            results.append({
                "date": row.get("date", ""),
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "close": _safe_float(row.get("close")),
                "preclose": _safe_float(row.get("preclose")),
                "volume": _safe_float(row.get("volume")),
                "amount": _safe_float(row.get("amount")),
                "turn": _safe_float(row.get("turn")),
                "pct_chg": _safe_float(row.get("pctChg")),
                "is_st": row.get("isST", "0"),
            })
        return results[-days:]  # limit to requested days
    finally:
        _logout(bs, lg)
        _bs_lock.release()


def _to_bs_code(stock_code: str) -> str:
    """Convert '301536.SZ' to 'sz.301536' format for baostock."""
    parts = stock_code.split(".")
    if len(parts) == 2:
        return f"{parts[1].lower()}.{parts[0]}"
    return stock_code


def _sync_get_latest_price(stock_code: str) -> Optional[dict]:
    """Get the latest trading day's price data."""
    klines = _sync_get_daily_klines(stock_code, days=5)
    if not klines:
        return None
    return klines[-1]


def _pure_code(stock_code: str) -> str:
    """Convert '301536.SZ' to '301536'."""
    return stock_code.split(".")[0] if "." in stock_code else stock_code


def _normalize_date(raw: str) -> str | None:
    """Normalize various date formats to YYYY-MM-DD."""
    raw = raw.strip()
    if not raw:
        return None
    if len(raw) == 10 and raw[4] == "-":
        return raw
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _sync_fetch_akshare_supplement(stock_code: str) -> dict[str, dict]:
    """
    Fetch supplemental data from akshare (Sina source):
    - 扣除非经常性损益后的净利润 (cumulative, yuan)
    - 营业收入 (cumulative, yuan) from 利润表

    Returns dict keyed by report_date (YYYY-MM-DD).
    """
    code = _pure_code(stock_code)
    result: dict[str, dict] = {}

    # 1. 扣非净利润 from stock_financial_analysis_indicator
    try:
        import akshare as ak
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2019")
        for _, row in df.iterrows():
            rd = _normalize_date(str(row.get("日期", "")))
            if not rd:
                continue
            dnp = _safe_float(row.get("扣除非经常性损益后的净利润(元)"))
            if rd not in result:
                result[rd] = {}
            if dnp is not None:
                result[rd]["deducted_net_profit"] = dnp
    except Exception as e:
        logger.warning(f"akshare financial_analysis_indicator failed for {code}: {e}")

    # 2. 营业收入 from stock_financial_report_sina 利润表
    try:
        import akshare as ak
        df = ak.stock_financial_report_sina(stock=code, symbol="利润表")
        for _, row in df.iterrows():
            rd = _normalize_date(str(row.get("报告日", "")))
            if not rd:
                continue
            rev = _safe_float(row.get("营业收入"))
            if rd not in result:
                result[rd] = {}
            if rev is not None:
                result[rd]["revenue_total"] = rev
    except Exception as e:
        logger.warning(f"akshare financial_report_sina failed for {code}: {e}")

    logger.info(f"akshare supplement for {code}: {len(result)} quarters fetched")
    return result


# ---- Async wrappers ----

async def search_stock(keyword: str) -> list[dict]:
    return await asyncio.to_thread(_sync_search_stock, keyword)


async def get_quarterly_data(stock_code: str, quarters: int = 16) -> list[dict]:
    return await asyncio.to_thread(_sync_get_quarterly_data, stock_code, quarters)


async def get_monthly_klines(stock_code: str, months: int = 60) -> list[dict]:
    return await asyncio.to_thread(_sync_get_monthly_klines, stock_code, months)


async def get_daily_klines(stock_code: str, days: int = 120) -> list[dict]:
    return await asyncio.to_thread(_sync_get_daily_klines, stock_code, days)


async def get_latest_price(stock_code: str) -> Optional[dict]:
    return await asyncio.to_thread(_sync_get_latest_price, stock_code)


async def get_stock_basic_info(stock_code: str, quarters_data: list[dict] | None = None) -> Optional[dict]:
    """Get basic stock info + computed valuation metrics."""
    results = await search_stock(stock_code)
    if not results:
        return None

    info = results[0]
    # Use pre-fetched quarters if provided, otherwise fetch
    if quarters_data is None:
        quarters_data = await get_quarterly_data(stock_code)

    # Compute valuation metrics
    from app.services.financial_calc import compute_10ps_valuation
    valuation = compute_10ps_valuation(quarters_data)

    info.update(valuation)
    info["dataSource"] = "baostock"
    info["updatedAt"] = "刚刚"
    return info


# ---- Batch collection with persistent sessions ----

class BaostockSessionPool:
    """Manages multiple baostock sessions for parallel batch collection."""

    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.sessions: list = []
        self._lock = threading.Lock()

    def init(self):
        """Initialize all sessions."""
        for _ in range(self.pool_size):
            _bs_lock.acquire()
            try:
                bs, lg = _login()
                self.sessions.append(bs)
            finally:
                _bs_lock.release()

    def cleanup(self):
        """Logout all sessions."""
        for bs in self.sessions:
            _bs_lock.acquire()
            try:
                _logout(bs, None)
            finally:
                _bs_lock.release()
        self.sessions.clear()

    def get_session(self) -> Optional[object]:
        """Get a session from pool (thread-safe)."""
        with self._lock:
            if self.sessions:
                return self.sessions.pop(0)
        return None

    def return_session(self, bs):
        """Return a session to pool (thread-safe)."""
        with self._lock:
            self.sessions.append(bs)


# Global session pool for batch operations
_batch_session_pool: Optional[BaostockSessionPool] = None


def init_batch_pool(pool_size: int = 3):
    """Initialize the global batch session pool."""
    global _batch_session_pool
    if _batch_session_pool is None:
        _batch_session_pool = BaostockSessionPool(pool_size)
        _batch_session_pool.init()


def cleanup_batch_pool():
    """Cleanup the global batch session pool."""
    global _batch_session_pool
    if _batch_session_pool is not None:
        _batch_session_pool.cleanup()
        _batch_session_pool = None


def _sync_batch_collect_stock(
    stock_code: str,
    quarters: int = 16,
    anti_crawl_delay: tuple = (0.3, 0.8)
) -> dict:
    """Collect data for a single stock using pooled session.

    Returns:
        dict with keys: success, stockCode, stockName, quartersCollected, error
    """
    import random
    import time

    session_pool = _batch_session_pool
    if session_pool is None:
        return {"success": False, "error": "Session pool not initialized"}

    bs = session_pool.get_session()
    if bs is None:
        return {"success": False, "error": "No available session"}

    try:
        # Fetch quarterly data with persistent session
        raw_quarters = _sync_get_quarterly_data(stock_code, quarters, bs_session=bs)

        # Anti-crawl: random delay
        delay = random.uniform(*anti_crawl_delay)
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
        session_pool.return_session(bs)


def batch_collect_stocks(
    stock_codes: list[str],
    quarters: int = 16,
    pool_size: int = 3,
    anti_crawl_delay: tuple = (0.3, 0.8)
) -> list[dict]:
    """Batch collect data for multiple stocks using thread pool.

    Args:
        stock_codes: List of stock codes to collect
        quarters: Number of quarters to fetch
        pool_size: Number of parallel threads
        anti_crawl_delay: (min, max) delay in seconds between requests

    Returns:
        List of result dicts for each stock
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Initialize session pool
    init_batch_pool(pool_size)

    results = []
    try:
        with ThreadPoolExecutor(max_workers=pool_size) as executor:
            future_to_code = {
                executor.submit(
                    _sync_batch_collect_stock,
                    code,
                    quarters,
                    anti_crawl_delay
                ): code
                for code in stock_codes
            }

            for future in as_completed(future_to_code):
                stock_code = future_to_code[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Unexpected error for {stock_code}: {e}")
                    results.append({
                        "success": False,
                        "stockCode": stock_code,
                        "error": str(e)
                    })

    finally:
        cleanup_batch_pool()

    return results


async def async_batch_collect_stocks(
    stock_codes: list[str],
    quarters: int = 16,
    pool_size: int = 3,
    anti_crawl_delay: tuple = (0.3, 0.8)
) -> list[dict]:
    """Async wrapper for batch collection."""
    return await asyncio.to_thread(
        batch_collect_stocks,
        stock_codes,
        quarters,
        pool_size,
        anti_crawl_delay
    )
