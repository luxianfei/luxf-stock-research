"""
Big Yang scanner service.

Strategy:
1. Scan pool stocks for "big yang" events: daily gain >= 9.5%.
2. When detected, add to watching pool with trigger_price = big-yang day's open.
3. Monitor watching stocks: if price drops back near trigger, generate buy alert.
4. Expire signals after expire_days if not triggered.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invest_pool import InvestStockPool
from app.models.big_yang import BigYangSignal, BigYangAlert
from app.services.data_fetcher import get_daily_klines

logger = logging.getLogger(__name__)

BIG_YANG_PCT_THRESHOLD = 9.5
PULLBACK_TRIGGER_PCT = 3.0
DEFAULT_EXPIRE_DAYS = 10


async def scan_pool_for_big_yang(db: AsyncSession) -> dict:
    """Scan all pool stocks for big-yang events."""
    stmt = select(InvestStockPool).where(InvestStockPool.status == "watching")
    result = await db.execute(stmt)
    pool_stocks = result.scalars().all()

    new_signals = 0
    new_alerts = 0
    errors = []

    for stock in pool_stocks:
        try:
            klines = await get_daily_klines(stock.stock_code, days=30)
            if not klines:
                continue

            # Check last 5 trading days for big-yang events
            for kline in klines[-5:]:
                pct_chg = kline.get("pct_chg")
                if pct_chg is None or pct_chg < BIG_YANG_PCT_THRESHOLD:
                    continue

                signal_date = kline["date"]
                existing = await _find_existing_signal(db, stock.stock_code, signal_date)
                if existing:
                    continue

                signal = BigYangSignal(
                    stock_code=stock.stock_code,
                    stock_name=stock.stock_name,
                    signal_type="big_yang",
                    trigger_price=kline.get("open"),
                    base_price=kline.get("close"),
                    status="watching",
                    expire_days=DEFAULT_EXPIRE_DAYS,
                    created_at=datetime.utcnow(),
                )
                db.add(signal)
                new_signals += 1

                alert = BigYangAlert(
                    stock_code=stock.stock_code,
                    stock_name=stock.stock_name,
                    title=f"大阳线信号: {stock.stock_name} 涨幅 {pct_chg:.1f}%",
                    message=(
                        f"{signal_date} 出现大阳线(涨幅{pct_chg:.1f}%), "
                        f"起涨价 {kline.get('open')}, 收盘 {kline.get('close')}. "
                        f"关注回踩至 {kline.get('open')} 附近的买入机会."
                    ),
                    read=False,
                    trigger_at=datetime.strptime(signal_date, "%Y-%m-%d"),
                    created_at=datetime.utcnow(),
                )
                db.add(alert)
                new_alerts += 1

            # Check existing watching signals for pullback triggers
            triggered = await _check_pullback_triggers(db, stock, klines)
            new_alerts += triggered

        except Exception as e:
            logger.error(f"Error scanning {stock.stock_code}: {e}")
            errors.append(f"{stock.stock_code}: {str(e)}")

    expired_count = await _expire_old_signals(db)
    await db.commit()

    return {
        "scanned": len(pool_stocks),
        "new_signals": new_signals,
        "new_alerts": new_alerts,
        "expired": expired_count,
        "errors": errors,
    }


async def _find_existing_signal(
    db: AsyncSession, stock_code: str, signal_date: str
) -> Optional[BigYangSignal]:
    stmt = select(BigYangSignal).where(
        BigYangSignal.stock_code == stock_code,
        BigYangSignal.signal_type == "big_yang",
    )
    result = await db.execute(stmt)
    signals = result.scalars().all()
    for sig in signals:
        if sig.created_at and sig.created_at.strftime("%Y-%m-%d") == signal_date:
            return sig
    return None


async def _check_pullback_triggers(
    db: AsyncSession, stock: InvestStockPool, klines: list[dict]
) -> int:
    stmt = select(BigYangSignal).where(
        BigYangSignal.stock_code == stock.stock_code,
        BigYangSignal.status == "watching",
    )
    result = await db.execute(stmt)
    watching_signals = result.scalars().all()

    if not watching_signals or not klines:
        return 0

    latest = klines[-1]
    latest_close = latest.get("close")
    if not latest_close:
        return 0

    alerts_created = 0
    for signal in watching_signals:
        if not signal.trigger_price:
            continue
        trigger = signal.trigger_price
        pullback_pct = ((latest_close - trigger) / trigger) * 100

        if -PULLBACK_TRIGGER_PCT <= pullback_pct <= PULLBACK_TRIGGER_PCT:
            signal.status = "triggered"
            signal.trigger_at = datetime.utcnow()

            alert = BigYangAlert(
                signal_id=signal.id,
                stock_code=stock.stock_code,
                stock_name=stock.stock_name,
                title=f"买入信号: {stock.stock_name} 回踩起涨点",
                message=(
                    f"当前价 {latest_close} 已回踩至大阳线起涨价 {trigger} 附近"
                    f"(偏离 {pullback_pct:+.1f}%), 关注买入机会."
                ),
                read=False,
                trigger_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(alert)
            alerts_created += 1

    return alerts_created


async def _expire_old_signals(db: AsyncSession) -> int:
    stmt = select(BigYangSignal).where(BigYangSignal.status == "watching")
    result = await db.execute(stmt)
    signals = result.scalars().all()

    expired = 0
    now = datetime.utcnow()
    for signal in signals:
        if signal.created_at:
            age_days = (now - signal.created_at).days
            if age_days >= signal.expire_days:
                signal.status = "expired"
                expired += 1
    return expired
