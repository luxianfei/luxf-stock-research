"""Invest (龙江投资) API router — stock pool, big yang, SOP checkup, valuation."""
import logging
from datetime import datetime

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.invest_pool import InvestStockPool
from app.models.big_yang import BigYangSignal, BigYangAlert
from app.schemas.invest import (
    PoolItemCreate,
    PoolItemUpdate,
    PoolItemResponse,
    BigYangSummary,
    BigYangSignalResponse,
    BigYangAlertResponse,
    SopCheckupResponse,
    SopCheckupMetric,
)
from app.services.data_fetcher import search_stock, get_quarterly_data
from app.services.pool_enrichment import enrich_pool_item, refresh_all_pool
from app.services.big_yang_scanner import scan_pool_for_big_yang

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/invest", tags=["invest"])


# ---- Stock Pool ----

@router.get("/pool", response_model=list[PoolItemResponse])
async def list_pool(db: AsyncSession = Depends(get_db)):
    stmt = select(InvestStockPool).order_by(InvestStockPool.display_order.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/pool", response_model=PoolItemResponse)
async def add_to_pool(item: PoolItemCreate, db: AsyncSession = Depends(get_db)):
    # Resolve stock
    matches = await search_stock(item.keyword)
    if not matches:
        raise HTTPException(404, f"未找到股票: {item.keyword}")

    match = matches[0]
    pool_type_label = "科技风投" if item.pool_type == "tech_vc" else "质量优选"

    record = InvestStockPool(
        stock_code=match["stock_code"],
        stock_name=match.get("stock_name", ""),
        pool_type=item.pool_type,
        pool_type_label=pool_type_label,
        memo=item.memo,
        status=item.status,
        status_label="观察中",
        target_price=item.target_price,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Enrich with financial data
    record = await enrich_pool_item(record, db)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/pool/{pool_id}", response_model=PoolItemResponse)
async def update_pool_item(pool_id: int, item: PoolItemUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(InvestStockPool).where(InvestStockPool.id == pool_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "未找到该股票池记录")

    for field, value in item.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/pool/{pool_id}")
async def remove_from_pool(pool_id: int, db: AsyncSession = Depends(get_db)):
    stmt = delete(InvestStockPool).where(InvestStockPool.id == pool_id)
    await db.execute(stmt)
    await db.commit()
    return {"ok": True}


@router.patch("/pool/{pool_id}/{field}")
async def patch_pool_field(
    pool_id: int,
    field: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Inline edit a single field: body = { field: "key", value: numberOrNull }"""
    from pydantic import BaseModel

    stmt = select(InvestStockPool).where(InvestStockPool.id == pool_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "未找到该股票池记录")

    # Validate field name
    allowed_fields = {
        "revenue2023", "revenue2024", "revenue2025",
        "revenue_forecast_y0", "revenue_forecast_y1", "revenue_forecast_y2",
        "q1_gross_margin", "q1_net_margin", "q1_revenue_growth",
        "min_ps_5y", "memo",
    }
    # Accept both camelCase and snake_case
    camel_to_snake = {
        "revenueForecastY0": "revenue_forecast_y0",
        "revenueForecastY1": "revenue_forecast_y1",
        "revenueForecastY2": "revenue_forecast_y2",
        "q1GrossMargin": "q1_gross_margin",
        "q1NetMargin": "q1_net_margin",
        "q1RevenueGrowth": "q1_revenue_growth",
        "minPs5y": "min_ps_5y",
    }
    actual_field = camel_to_snake.get(field, field)
    if actual_field not in allowed_fields:
        raise HTTPException(400, f"不允许编辑的字段: {field}")

    value = body.get("value")
    setattr(record, actual_field, value)
    record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return {"ok": True, "field": field, "value": value}


@router.post("/pool/batch-import")
async def batch_import(items: list[PoolItemCreate], db: AsyncSession = Depends(get_db)):
    results = []
    for item in items:
        try:
            result = await add_to_pool(item, db)
            results.append(result)
        except HTTPException:
            continue
    return {"imported": len(results), "total": len(items)}


# ---- Big Yang ----

@router.get("/big-yang/summary", response_model=BigYangSummary)
async def big_yang_summary(db: AsyncSession = Depends(get_db)):
    watching = await db.scalar(
        select(func.count()).select_from(BigYangSignal).where(BigYangSignal.status == "watching")
    ) or 0
    triggered = await db.scalar(
        select(func.count()).select_from(BigYangSignal).where(BigYangSignal.status == "triggered")
    ) or 0
    expired = await db.scalar(
        select(func.count()).select_from(BigYangSignal).where(BigYangSignal.status == "expired")
    ) or 0
    unread = await db.scalar(
        select(func.count()).select_from(BigYangAlert).where(BigYangAlert.read == False)
    ) or 0

    today = datetime.utcnow().date()
    today_new = await db.scalar(
        select(func.count()).select_from(BigYangSignal).where(
            BigYangSignal.status == "watching",
            func.date(BigYangSignal.created_at) == today,
        )
    ) or 0
    today_triggered = await db.scalar(
        select(func.count()).select_from(BigYangSignal).where(
            BigYangSignal.status == "triggered",
            func.date(BigYangSignal.trigger_at) == today,
        )
    ) or 0

    return BigYangSummary(
        unread_alert_count=unread,
        watching_count=watching,
        triggered_count=triggered,
        expired_count=expired,
        today_new_watching_count=today_new,
        today_triggered_count=today_triggered,
    )


@router.get("/big-yang/signals", response_model=list[BigYangSignalResponse])
async def big_yang_signals(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BigYangSignal).order_by(BigYangSignal.created_at.desc())
    if status:
        stmt = stmt.where(BigYangSignal.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/big-yang/alerts", response_model=list[BigYangAlertResponse])
async def big_yang_alerts(db: AsyncSession = Depends(get_db)):
    stmt = select(BigYangAlert).order_by(BigYangAlert.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/big-yang/run")
async def big_yang_run(db: AsyncSession = Depends(get_db)):
    """Trigger a scan of the stock pool for big-yang signals."""
    result = await scan_pool_for_big_yang(db)
    return result


@router.post("/pool/refresh")
async def pool_refresh(db: AsyncSession = Depends(get_db)):
    """Refresh financial data for all pool items."""
    result = await refresh_all_pool(db)
    return result


@router.post("/big-yang/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(BigYangAlert).where(BigYangAlert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "告警不存在")
    alert.read = True
    await db.commit()
    return {"ok": True}


# ---- SOP Checkup ----

@router.get("/sop/checkup", response_model=SopCheckupResponse)
async def sop_checkup(
    keyword: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Digital health check: gross margin, revenue YoY, deducted profit YoY for last 8 quarters."""
    matches = await search_stock(keyword)
    if not matches:
        return SopCheckupResponse(matched=False, message=f"未找到股票: {keyword}")

    match = matches[0]
    quarters = await get_quarterly_data(match["stock_code"], quarters=8)

    if not quarters:
        return SopCheckupResponse(matched=False, message="无法获取财务数据")

    gm_series = [{"quarter": q["quarter"], "value": q.get("gross_margin")} for q in quarters]
    rev_series = [{"quarter": q["quarter"], "value": q.get("revenue_yoy")} for q in quarters]
    profit_series = [{"quarter": q["quarter"], "value": q.get("deducted_net_profit_yoy")} for q in quarters]

    gm_metric = _build_checkup_metric("毛利率", gm_series, thresholds={"pass": 30, "warn": 20})
    rev_metric = _build_checkup_metric("营收同比", rev_series, thresholds={"pass": 15, "warn": 0})
    profit_metric = _build_checkup_metric("扣非同比", profit_series, thresholds={"pass": 20, "warn": 0})

    pass_count = sum(1 for m in [gm_metric, rev_metric, profit_metric] if m.verdict == "pass")
    fail_count = sum(1 for m in [gm_metric, rev_metric, profit_metric] if m.verdict == "fail")

    if pass_count >= 2:
        overall = "pass"
        summary = "三项指标表现良好，值得深入研究"
    elif fail_count >= 2:
        overall = "fail"
        summary = "多项指标不达标，建议回避"
    else:
        overall = "warn"
        summary = "指标表现不一，需谨慎判断"

    return SopCheckupResponse(
        matched=True,
        stock_name=match.get("stock_name", ""),
        stock_code=match.get("stock_code", ""),
        overall_verdict=overall,
        overall_summary=summary,
        gross_margin=gm_metric,
        revenue_yoy=rev_metric,
        profit_yoy=profit_metric,
    )


def _build_checkup_metric(label: str, series: list[dict], thresholds: dict) -> SopCheckupMetric:
    values = [s["value"] for s in series if s.get("value") is not None]
    latest = values[0] if values else None

    if latest is None:
        verdict = "warn"
        tip = "无数据"
    elif latest >= thresholds.get("pass", 0):
        verdict = "pass"
        tip = f"最新值 {latest:.1f}%，表现优秀"
    elif latest >= thresholds.get("warn", 0):
        verdict = "warn"
        tip = f"最新值 {latest:.1f}%，表现一般"
    else:
        verdict = "fail"
        tip = f"最新值 {latest:.1f}%，低于阈值"

    return SopCheckupMetric(
        label=label,
        verdict=verdict,
        latest=latest,
        unit="%",
        tip=tip,
        series=series,
    )
