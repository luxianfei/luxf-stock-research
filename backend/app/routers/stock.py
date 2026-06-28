"""Financial analysis API router."""
import logging
from datetime import date, datetime

from fastapi import APIRouter, Query, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stock import StockBasic
from app.models.financial import FinancialQuarterly
from app.schemas.stock import (
    FinancialQueryResponse,
    StockFinancialData,
    BasicInfo,
    QuarterData,
)
from app.services.data_fetcher import search_stock, get_quarterly_data, get_stock_basic_info
from app.services.financial_calc import compute_10ps_valuation, process_quarters_for_display

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/financial", response_model=FinancialQueryResponse)
async def get_financial_data(
    keywords: str = Query(..., description="Comma-separated stock names or codes"),
    quarters: int = Query(16, ge=1, le=40, description="Number of quarters to fetch"),
    local_only: bool = Query(False, description="If true, only check local DB without auto-fetching from baostock"),
    db: AsyncSession = Depends(get_db),
):
    keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    requested = len(keyword_list)

    stocks_data: list[StockFinancialData] = []
    not_found: list[str] = []

    for kw in keyword_list:
        if local_only:
            # Only check DB, no baostock fetch
            stock = await _find_stock_in_db(kw, db)
            if stock:
                data = await _build_stock_response(stock.stock_code, quarters, db)
                if data:
                    stocks_data.append(data)
                else:
                    not_found.append(kw)
            else:
                not_found.append(kw)
        else:
            stock = await _fetch_one_stock(kw, quarters, db)
            if stock:
                stocks_data.append(stock)
            else:
                not_found.append(kw)

    return FinancialQueryResponse(
        requested=requested,
        matched=len(stocks_data),
        not_found=not_found,
        stocks=stocks_data,
    )


async def _fetch_one_stock(keyword: str, quarters: int, db: AsyncSession) -> StockFinancialData | None:
    """Fetch financial data for one stock, trying DB cache first then baostock."""
    # 1. Try DB lookup by code or name
    stock = await _find_stock_in_db(keyword, db)

    if not stock:
        # 2. Search via baostock
        search_results = await search_stock(keyword)
        if not search_results:
            return None

        match = search_results[0]
        stock_code = match["stock_code"]

        # 3. Fetch quarterly data from baostock (+5 for YoY/TTM reference)
        raw_quarters = await get_quarterly_data(stock_code, quarters + 5)
        if not raw_quarters:
            return None

        # 4. Get basic info (reuse already-fetched quarters)
        basic = await get_stock_basic_info(stock_code, quarters_data=raw_quarters)
        if not basic:
            basic = match

        # 5. Upsert into DB
        stock = await _upsert_stock(match, basic, db)
        await _upsert_quarters(stock_code, raw_quarters, db)

    # Build response from DB
    return await _build_stock_response(stock.stock_code, quarters, db)


async def _find_stock_in_db(keyword: str, db: AsyncSession) -> StockBasic | None:
    stmt = select(StockBasic).where(
        (StockBasic.stock_code == keyword)
        | (StockBasic.stock_name == keyword)
        | StockBasic.stock_code.like(f"{keyword}.%")
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def _upsert_stock(match: dict, basic: dict, db: AsyncSession) -> StockBasic:
    stmt = select(StockBasic).where(StockBasic.stock_code == match["stock_code"])
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    ipo_date = None
    if basic.get("ipo_date") or match.get("ipo_date"):
        try:
            ipo_str = basic.get("ipo_date") or match.get("ipo_date")
            if ipo_str:
                ipo_date = datetime.strptime(ipo_str, "%Y-%m-%d").date()
        except Exception:
            pass

    list_years = 0
    if ipo_date:
        list_years = max(0, (date.today() - ipo_date).days // 365)

    # 10PS valuation
    valuation = compute_10ps_valuation(
        current_market_cap_yi=basic.get("current_market_cap_yi", 0) or 0,
        forecast_revenue_y1_yi=basic.get("forecast_revenue_y1_yi"),
        forecast_revenue_y2_yi=basic.get("forecast_revenue_y2_yi"),
        latest_net_margin=basic.get("latest_net_margin"),
    )

    if existing:
        existing.stock_name = match.get("stock_name", existing.stock_name)
        existing.updated_at = date.today()
        await db.commit()
        await db.refresh(existing)
        return existing

    new_stock = StockBasic(
        stock_code=match["stock_code"],
        stock_name=match.get("stock_name", ""),
        exchange=match.get("exchange", ""),
        board=basic.get("board"),
        industry=basic.get("industry"),
        extra_industry_count=basic.get("extraIndustryCount", 0),
        list_date=ipo_date,
        pe_ttm=basic.get("peTtm") or basic.get("pe_ttm"),
        pb=basic.get("pb"),
        ps_ttm=basic.get("psTtm") or basic.get("ps_ttm"),
        current_market_cap_yi=basic.get("currentMarketCapYi") or basic.get("current_market_cap_yi"),
        latest_net_margin=basic.get("latest_net_margin"),
        forecast_revenue_y1_yi=basic.get("forecast_revenue_y1_yi"),
        forecast_revenue_y2_yi=basic.get("forecast_revenue_y2_yi"),
        forecast_revenue_y3_yi=basic.get("forecast_revenue_y3_yi"),
        ten_ps_candidate=valuation["ten_ps_candidate"],
        ten_ps_fair_market_cap_yi=valuation["ten_ps_fair_market_cap_yi"],
        ten_ps_current_to_y1=valuation["ten_ps_current_to_y1"],
        ten_ps_valuation_verdict=valuation["ten_ps_valuation_verdict"],
        ten_ps_valuation_detail=valuation["ten_ps_valuation_detail"],
        valuation_level=basic.get("valuation_level"),
        data_source="baostock",
        updated_at=date.today(),
    )
    db.add(new_stock)
    await db.commit()
    await db.refresh(new_stock)
    return new_stock


async def _upsert_quarters(stock_code: str, raw_quarters: list[dict], db: AsyncSession):
    for q in raw_quarters:
        report_date = q.get("report_date", "")
        try:
            rd = datetime.strptime(report_date, "%Y-%m-%d").date()
        except Exception:
            rd = date.today()

        stmt = select(FinancialQuarterly).where(
            FinancialQuarterly.stock_code == stock_code,
            FinancialQuarterly.report_date == rd,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            for key, value in q.items():
                if key not in ("quarter", "report_date") and hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            record = FinancialQuarterly(
                stock_code=stock_code,
                quarter=q.get("quarter", ""),
                report_date=rd,
                revenue_yoy=q.get("revenue_yoy"),
                deducted_net_profit_yoy=q.get("deducted_net_profit_yoy"),
                gross_margin=q.get("gross_margin"),
                net_margin=q.get("net_margin"),
                roe=q.get("roe"),
                roa=q.get("roa"),
                eps=q.get("eps"),
                revenue=q.get("revenue"),
                net_profit=q.get("net_profit"),
                deducted_net_profit=q.get("deducted_net_profit"),
                deducted_net_profit_ttm=q.get("deducted_net_profit_ttm"),
                total_assets=q.get("total_assets"),
                total_equity=q.get("total_equity"),
                operating_cashflow=q.get("operating_cashflow"),
                debt_ratio=q.get("debt_ratio"),
                current_ratio=q.get("current_ratio"),
            )
            db.add(record)

    await db.commit()


async def _build_stock_response(
    stock_code: str, quarters: int, db: AsyncSession
) -> StockFinancialData | None:
    # Load stock basic
    stmt = select(StockBasic).where(StockBasic.stock_code == stock_code)
    result = await db.execute(stmt)
    stock = result.scalar_one_or_none()
    if not stock:
        return None

    # Fetch extra quarters: +4 for YoY same-quarter-last-year reference,
    # +1 more so the YoY reference quarter can itself be converted from
    # cumulative to single-quarter (needs the quarter before it).
    fetch_count = quarters + 5
    stmt = (
        select(FinancialQuarterly)
        .where(FinancialQuarterly.stock_code == stock_code)
        .order_by(FinancialQuarterly.report_date.desc())
        .limit(fetch_count)
    )
    result = await db.execute(stmt)
    all_quarter_rows = list(result.scalars().all())

    if not all_quarter_rows:
        return None

    # Process: cumulative→single quarter, percentage×100, revenue_yoy
    all_quarter_rows = process_quarters_for_display(all_quarter_rows)

    # Slice to requested count
    quarter_rows = all_quarter_rows[:quarters]

    list_years = 0
    if stock.list_date:
        list_years = max(0, (date.today() - stock.list_date).days // 365)

    # Build basic info - normalize latest_net_margin to percentage for display
    latest_nm = stock.latest_net_margin
    if latest_nm is not None and latest_nm < 1:
        latest_nm = round(latest_nm * 100, 2)

    basic_info = BasicInfo(
        stock_code=stock.stock_code,
        stock_name=stock.stock_name,
        exchange=stock.exchange,
        board=stock.board,
        industry=stock.industry,
        extra_industry_count=stock.extra_industry_count or 0,
        list_date=str(stock.list_date) if stock.list_date else None,
        list_years=list_years,
        pe_ttm=stock.pe_ttm,
        pb=stock.pb,
        ps_ttm=stock.ps_ttm,
        current_market_cap_yi=stock.current_market_cap_yi,
        latest_net_margin=latest_nm,
        forecast_revenue_y1_yi=stock.forecast_revenue_y1_yi,
        forecast_revenue_y2_yi=stock.forecast_revenue_y2_yi,
        forecast_revenue_y3_yi=stock.forecast_revenue_y3_yi,
        ten_ps_candidate=stock.ten_ps_candidate or False,
        ten_ps_fair_market_cap_yi=stock.ten_ps_fair_market_cap_yi,
        ten_ps_current_to_y1=stock.ten_ps_current_to_y1,
        ten_ps_valuation_verdict=stock.ten_ps_valuation_verdict,
        ten_ps_valuation_detail=stock.ten_ps_valuation_detail,
        valuation_level=stock.valuation_level,
        data_source=stock.data_source or "baostock",
        updated_at=_time_ago(stock.updated_at),
    )

    quarter_list = []
    for q in quarter_rows:
        quarter_list.append(QuarterData(
            quarter=q.quarter,
            report_date=str(q.report_date),
            revenue_yoy=q.revenue_yoy,
            revenue_qoq=getattr(q, 'revenue_qoq', None),
            deducted_net_profit_yoy=q.deducted_net_profit_yoy,
            net_profit_qoq=getattr(q, 'net_profit_qoq', None),
            gross_margin=q.gross_margin,
            net_margin=q.net_margin,
            roe=q.roe,
            roa=q.roa,
            eps=q.eps,
            revenue=q.revenue,
            net_profit=q.net_profit,
            deducted_net_profit_ttm=q.deducted_net_profit_ttm,
            total_assets=q.total_assets,
            total_equity=q.total_equity,
            operating_cashflow=q.operating_cashflow,
            debt_ratio=q.debt_ratio,
            current_ratio=q.current_ratio,
        ))

    return StockFinancialData(
        stock_code=stock.stock_code,
        stock_name=stock.stock_name,
        basic_info=basic_info,
        quarters=quarter_list,
    )


def _time_ago(d: date | None) -> str | None:
    if not d:
        return None
    days = (date.today() - d).days
    if days == 0:
        return "今天更新"
    elif days == 1:
        return "昨天更新"
    elif days < 7:
        return f"{days}天前更新"
    elif days < 30:
        return f"{days // 7}周前更新"
    else:
        return f"{days // 30}个月前更新"
