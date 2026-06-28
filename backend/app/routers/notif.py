"""Notification-related API stubs (for the top notification bar)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analysis import PracticalSelectRecord
from app.models.big_yang import BigYangAlert

router = APIRouter(prefix="/api", tags=["notifications"])


@router.get("/market-recaps/badge")
async def recap_badge():
    """Stub — Phase 2: implement daily market recap."""
    return {"latestId": None, "latestTradeDate": None, "today": 0, "yesterday": 0}


@router.get("/stock-analysis/list")
async def analysis_list(
    limit: int = 3,
    size: int = 3,
    db: AsyncSession = Depends(get_db),
):
    """Return recent practical-select records as analysis notifications."""
    stmt = (
        select(PracticalSelectRecord)
        .where(PracticalSelectRecord.status == "SUCCESS")
        .order_by(PracticalSelectRecord.submitted_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return {
        "records": [
            {
                "id": r.id,
                "stockName": r.stock_name,
                "stockCode": r.stock_code,
                "verdict": r.verdict,
                "summaryOneLiner": r.summary_one_liner,
                "status": r.status,
                "submittedAt": r.submitted_at.isoformat() if r.submitted_at else None,
            }
            for r in records
        ]
    }


@router.get("/tech-ai/alerts")
async def tech_ai_alerts():
    """Stub — Phase 2: implement AI monitoring alerts."""
    return []
