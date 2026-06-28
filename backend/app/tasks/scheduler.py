"""
Scheduled tasks using APScheduler.
- Daily pool data refresh (after market close)
- Daily big-yang scan (after market close)
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import async_session
from app.services.pool_enrichment import refresh_all_pool
from app.services.big_yang_scanner import scan_pool_for_big_yang

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _refresh_pool_job():
    """Scheduled job: refresh all pool data."""
    logger.info("[Scheduler] Starting daily pool refresh...")
    async with async_session() as db:
        result = await refresh_all_pool(db)
        logger.info(f"[Scheduler] Pool refresh complete: {result}")


async def _scan_big_yang_job():
    """Scheduled job: scan for big-yang signals."""
    logger.info("[Scheduler] Starting daily big-yang scan...")
    async with async_session() as db:
        result = await scan_pool_for_big_yang(db)
        logger.info(f"[Scheduler] Big-yang scan complete: {result}")


def setup_scheduler():
    """Configure and start the scheduler."""
    # Refresh pool data at 16:30 (after A-share market close)
    scheduler.add_job(
        _refresh_pool_job,
        "cron",
        hour=16,
        minute=30,
        day_of_week="mon-fri",
        id="daily_pool_refresh",
        replace_existing=True,
    )

    # Scan for big-yang signals at 16:45
    scheduler.add_job(
        _scan_big_yang_job,
        "cron",
        hour=16,
        minute=45,
        day_of_week="mon-fri",
        id="daily_big_yang_scan",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("[Scheduler] Started with daily pool refresh (16:30) and big-yang scan (16:45)")
