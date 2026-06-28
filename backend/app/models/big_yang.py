from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BigYangSignal(Base):
    __tablename__ = "big_yang_signals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(12), index=True)
    stock_name: Mapped[str] = mapped_column(String(20))
    signal_type: Mapped[str] = mapped_column(String(20))  # watching / triggered / expired
    trigger_price: Mapped[Optional[float]] = mapped_column(Float)
    base_price: Mapped[Optional[float]] = mapped_column(Float)
    trigger_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="watching")
    expire_days: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BigYangAlert(Base):
    __tablename__ = "big_yang_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    signal_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("big_yang_signals.id"))
    stock_code: Mapped[str] = mapped_column(String(12), index=True)
    stock_name: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(100))
    message: Mapped[Optional[str]] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    trigger_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
