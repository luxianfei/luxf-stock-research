"""
Pool enrichment service — auto-fill financial data for stock pool items.
"""
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invest_pool import InvestStockPool
from app.services.data_fetcher import (
    get_quarterly_data,
    get_latest_price,
    search_stock,
)
from app.services.financial_calc import compute_10ps_valuation

logger = logging.getLogger(__name__)


async def enrich_pool_item(pool_item: InvestStockPool, db: AsyncSession) -> InvestStockPool:
    """Enrich a pool item with latest financial data and price info."""
    stock_code = pool_item.stock_code
    try:
        # 1. Fetch quarterly data
        quarters = await get_quarterly_data(stock_code, quarters=8)
        if quarters:
            latest = quarters[0]
            # Latest quarter metrics — baostock returns fractions, multiply by 100 for %
            gm = latest.get("gross_margin")
            nm = latest.get("net_margin")
            rg = latest.get("revenue_yoy")
            pool_item.q1_gross_margin = round(gm * 100, 2) if gm is not None else None
            pool_item.q1_net_margin = round(nm * 100, 2) if nm is not None else None
            pool_item.q1_revenue_growth = round(rg * 100, 2) if rg is not None else None
            pool_item.latest_revenue_yoy = pool_item.q1_revenue_growth
            pool_item.latest_profit_yoy = round(
                (latest.get("deducted_net_profit_yoy") or 0) * 100, 2
            ) if latest.get("deducted_net_profit_yoy") is not None else None

            # Revenue by year (group quarters by year)
            _fill_revenue_by_year(pool_item, quarters)

            # Revenue forecasts (based on latest annual revenue)
            latest_revenue = latest.get("revenue")
            if latest_revenue and latest_revenue > 0:
                rev_yi = latest_revenue / 1e8
                pool_item.revenue_forecast_y0 = round(rev_yi * 1.2, 2)
                pool_item.revenue_forecast_y1 = round(rev_yi * 1.44, 2)
                pool_item.revenue_forecast_y2 = round(rev_yi * 1.728, 2)

        # 2. Fetch latest price
        price_data = await get_latest_price(stock_code)
        if price_data:
            pool_item.latest_price = price_data.get("close")
            pool_item.ytd_gain_pct = price_data.get("pct_chg")

        # 3. Compute valuation using reference site's logic:
        # Fair = Y1 revenue * 10; if cap < Y1*10 => 低估; if cap > Y2*10 => 泡沫; else => 合理
        if pool_item.revenue_forecast_y1 and pool_item.revenue_forecast_y1 > 0:
            y1_fair_cap = pool_item.revenue_forecast_y1 * 10
            y2_fair_cap = (pool_item.revenue_forecast_y2 or 0) * 10
            current_cap = pool_item.current_market_cap or 0

            pool_item.target_market_cap = y1_fair_cap

            if current_cap > 0 and y2_fair_cap > 0:
                if current_cap < y1_fair_cap:
                    pool_item.valuation_range = "低估"
                elif current_cap > y2_fair_cap:
                    pool_item.valuation_range = "泡沫"
                else:
                    pool_item.valuation_range = "合理"
            elif current_cap > 0:
                if current_cap < y1_fair_cap:
                    pool_item.valuation_range = "低估"
                else:
                    pool_item.valuation_range = "合理"
            else:
                pool_item.valuation_range = None

        pool_item.updated_at = datetime.utcnow()
        pool_item.pool_update_error = None

    except Exception as e:
        logger.error(f"Enrichment failed for {stock_code}: {e}")
        pool_item.pool_update_error = str(e)

    return pool_item


def _fill_revenue_by_year(pool_item: InvestStockPool, quarters: list[dict]):
    """Sum quarterly revenue into annual buckets."""
    year_revenue = {}
    for q in quarters:
        rd = q.get("report_date", "")
        rev = q.get("revenue")
        if rd and rev:
            try:
                year = datetime.strptime(rd, "%Y-%m-%d").year
                year_revenue[year] = (year_revenue.get(year, 0) + rev)
            except Exception:
                pass

    years = sorted(year_revenue.keys(), reverse=True)
    if len(years) >= 1:
        pool_item.revenue_2025 = round(year_revenue.get(2025, 0) / 1e8, 2) if 2025 in year_revenue else None
    if len(years) >= 1:
        pool_item.revenue_2024 = round(year_revenue.get(2024, 0) / 1e8, 2) if 2024 in year_revenue else None
    if len(years) >= 1:
        pool_item.revenue_2023 = round(year_revenue.get(2023, 0) / 1e8, 2) if 2023 in year_revenue else None


async def refresh_all_pool(db: AsyncSession) -> dict:
    """Refresh financial data for all pool items."""
    stmt = select(InvestStockPool)
    result = await db.execute(stmt)
    pool_items = result.scalars().all()

    refreshed = 0
    errors = 0
    for item in pool_items:
        try:
            await enrich_pool_item(item, db)
            refreshed += 1
        except Exception as e:
            logger.error(f"Refresh failed for {item.stock_code}: {e}")
            errors += 1

    await db.commit()
    return {"refreshed": refreshed, "errors": errors, "total": len(pool_items)}
