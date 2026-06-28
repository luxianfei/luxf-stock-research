"""Data collection API router."""
import logging

from fastapi import APIRouter, Query, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.collector_service import (
    collect_single_stock,
    check_stock_status,
    get_task_status,
    start_batch_collect,
    start_market_collect,
    get_market_info,
    parse_csv_keywords,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/collect", tags=["collect"])


@router.post("/single")
async def collect_single(
    keyword: str = Query(..., description="股票代码或名称"),
    db: AsyncSession = Depends(get_db),
):
    """Collect financial data for a single stock."""
    result = await collect_single_stock(keyword, db)
    return result


@router.get("/stock-status/{keyword}")
async def stock_status(
    keyword: str,
    db: AsyncSession = Depends(get_db),
):
    """Check what data exists in DB for a stock."""
    return await check_stock_status(keyword, db)


@router.post("/batch")
async def batch_collect(
    keywords: list[str],
    incremental: bool = True,
):
    """Start batch collection for a list of stock keywords."""
    return await start_batch_collect(keywords, incremental)


@router.post("/batch/upload")
async def batch_upload(
    file: UploadFile = File(...),
    incremental: bool = Form(True),
):
    """Upload a CSV file with stock keywords and start batch collection."""
    content = await file.read()
    keywords = parse_csv_keywords(content)
    if not keywords:
        return {"error": "CSV文件中未找到有效的股票代码"}
    return await start_batch_collect(keywords, incremental)


@router.get("/batch/{task_id}")
async def batch_status(task_id: str):
    """Get the status of a batch collection task."""
    status = get_task_status(task_id)
    if not status:
        return {"error": "任务不存在", "taskId": task_id}
    return status


@router.get("/markets")
async def list_markets():
    """List available markets for collection."""
    return {"markets": get_market_info()}


@router.post("/market")
async def market_collect(
    market: str = Query(..., description="市场ID: gem/star/sh_main/sz_main"),
    incremental: bool = True,
):
    """Start collection for all stocks in a market."""
    return await start_market_collect(market, incremental)
