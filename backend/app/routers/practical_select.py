"""Practical select (实战选股) API router."""
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import select, delete as sa_delete, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analysis import PracticalSelectRecord
from app.schemas.invest import (
    PracticalSelectRequest,
    PracticalSelectResponse,
)
from app.services.data_fetcher import (
    search_stock,
    get_quarterly_data,
    get_monthly_klines,
    get_latest_price,
)
from app.services.ai_analysis import (
    heuristic_rating,
    compute_trend_score,
    compute_financial_score,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/practical-select", tags=["practical-select"])


# ---- Pagination response schema ----
class _CamelBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HistoryPageResponse(_CamelBase):
    records: list[PracticalSelectResponse]
    total: int
    page: int
    size: int
    total_pages: int


def _build_headline(record: PracticalSelectRecord) -> str:
    """Build a headline string like '德明利（001309.SZ） · 观望 · 营收高速增长'."""
    parts = [f"{record.stock_name}（{record.stock_code}）"]
    if record.verdict:
        parts.append(record.verdict)
    if record.summary_one_liner:
        # Take first clause before comma
        clause = record.summary_one_liner.split("，")[0]
        if clause:
            parts.append(clause)
    return " · ".join(parts)


def _enrich_response(record: PracticalSelectRecord) -> dict:
    """Enrich a PracticalSelectRecord with computed fields for the frontend."""
    data = {
        "id": record.id,
        "stockCode": record.stock_code,
        "stockName": record.stock_name,
        "trendScore": record.trend_score,
        "financialScore": record.financial_score,
        "scarcityStars": record.scarcity_stars,
        "growthStars": record.growth_stars,
        "tenPsVerdict": record.ten_ps_verdict,
        "summaryOneLiner": record.summary_one_liner,
        "verdict": record.verdict,
        "aiModel": record.ai_model,
        "status": record.status,
        "submittedAt": record.submitted_at.isoformat() if record.submitted_at else None,
        "completedAt": record.completed_at.isoformat() if record.completed_at else None,
        "headline": _build_headline(record),
    }
    # Compute elapsed_ms from timestamps
    if record.submitted_at and record.completed_at:
        delta = (record.completed_at - record.submitted_at).total_seconds() * 1000
        data["elapsedMs"] = round(delta)
    else:
        data["elapsedMs"] = None
    # Include analysis_json if present
    if record.analysis_json:
        data["analysisJson"] = record.analysis_json
    return data


@router.post("", response_model=PracticalSelectResponse)
async def run_analysis(req: PracticalSelectRequest, db: AsyncSession = Depends(get_db)):
    """Run practical-select analysis (Phase 1: local heuristic)."""
    t0 = time.time()

    matches = await search_stock(req.keyword)
    if not matches:
        elapsed = int((time.time() - t0) * 1000)
        record = PracticalSelectRecord(
            stock_code=req.keyword,
            stock_name=req.keyword,
            status="FAILED",
            summary_one_liner="未找到该股票",
            submitted_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    match = matches[0]
    stock_code = match["stock_code"]
    stock_name = match.get("stock_name", "")

    # Fetch quarterly data
    quarters = await get_quarterly_data(stock_code, quarters=16)

    # Fetch monthly K-lines for trend scoring
    monthly_klines = await get_monthly_klines(stock_code, months=60)

    # Fetch latest price for additional context
    price_data = await get_latest_price(stock_code)

    # Compute scores
    trend_score = compute_trend_score(monthly_klines)
    financial_score = compute_financial_score(quarters)

    # Local heuristic rating (Phase 2: integrate MiniMax AI)
    rating = heuristic_rating(quarters, trend_score, financial_score)

    # Build richer analysis_json for frontend 4-card display
    analysis_detail = {
        "quarters_count": len(quarters),
        "klines_count": len(monthly_klines),
    }
    # Add latest quarter summary if available
    if quarters:
        latest = quarters[0]
        analysis_detail["latest_quarter"] = latest.get("quarter", "")
        analysis_detail["latest_gross_margin"] = latest.get("gross_margin")
        analysis_detail["latest_net_margin"] = latest.get("net_margin")
        analysis_detail["latest_revenue_yoy"] = latest.get("revenue_yoy")
        analysis_detail["latest_profit_yoy"] = latest.get("deducted_net_profit_yoy")
        analysis_detail["latest_revenue"] = latest.get("revenue")
        analysis_detail["latest_eps"] = latest.get("eps")
        analysis_detail["latest_roe"] = latest.get("roe")
    # Add price info
    if price_data:
        analysis_detail["latest_price"] = price_data.get("close")
        analysis_detail["ytd_gain"] = price_data.get("pct_chg")
    # Add 10PS valuation info
    if quarters and price_data:
        latest = quarters[0]
        revenue = latest.get("revenue")
        net_margin = latest.get("net_margin")
        if revenue and revenue > 0 and net_margin:
            rev_yi = revenue / 1e8
            analysis_detail["forecast_revenue_y1"] = round(rev_yi * 1.2, 2)
            analysis_detail["forecast_revenue_y2"] = round(rev_yi * 1.44, 2)
            analysis_detail["fair_cap_y1"] = round(rev_yi * 1.2 * 10, 2)
            analysis_detail["fair_cap_y2"] = round(rev_yi * 1.44 * 10, 2)

    elapsed = int((time.time() - t0) * 1000)

    record = PracticalSelectRecord(
        stock_code=stock_code,
        stock_name=stock_name,
        trend_score=trend_score,
        financial_score=financial_score,
        scarcity_stars=rating["scarcity_stars"],
        growth_stars=rating["growth_stars"],
        ten_ps_verdict=rating.get("ten_ps_verdict"),
        summary_one_liner=rating["summary_one_liner"],
        verdict=rating["verdict"],
        ai_model="local",
        analysis_json=analysis_detail,
        status="SUCCESS",
        submitted_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/history")
async def list_history(
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    kw: str = Query("", description="Keyword filter"),
    db: AsyncSession = Depends(get_db),
):
    """Paginated history with optional keyword search."""
    base_stmt = select(PracticalSelectRecord)
    count_stmt = select(sa_func.count()).select_from(PracticalSelectRecord)

    if kw:
        like_pattern = f"%{kw}%"
        base_stmt = base_stmt.where(
            (PracticalSelectRecord.stock_name.ilike(like_pattern))
            | (PracticalSelectRecord.stock_code.ilike(like_pattern))
        )
        count_stmt = count_stmt.where(
            (PracticalSelectRecord.stock_name.ilike(like_pattern))
            | (PracticalSelectRecord.stock_code.ilike(like_pattern))
        )

    # Total count
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    total_pages = max(1, (total + size - 1) // size)

    # Paginated records
    stmt = (
        base_stmt.order_by(PracticalSelectRecord.submitted_at.desc())
        .offset(page * size)
        .limit(size)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return {
        "records": [PracticalSelectResponse.model_validate(r) for r in records],
        "total": total,
        "page": page,
        "size": size,
        "totalPages": total_pages,
    }


@router.delete("/history/{record_id}")
async def delete_history_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PracticalSelectRecord).where(PracticalSelectRecord.id == record_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "记录不存在")
    await db.execute(
        sa_delete(PracticalSelectRecord).where(PracticalSelectRecord.id == record_id)
    )
    await db.commit()
    return {"ok": True}
