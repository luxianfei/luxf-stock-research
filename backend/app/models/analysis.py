from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PracticalSelectRecord(Base):
    __tablename__ = "practical_select_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(12), index=True)
    stock_name: Mapped[str] = mapped_column(String(20))
    trend_score: Mapped[Optional[float]] = mapped_column(Float)
    financial_score: Mapped[Optional[float]] = mapped_column(Float)
    scarcity_stars: Mapped[Optional[int]] = mapped_column(Integer)
    growth_stars: Mapped[Optional[int]] = mapped_column(Integer)
    ten_ps_verdict: Mapped[Optional[str]] = mapped_column(String(20))
    summary_one_liner: Mapped[Optional[str]] = mapped_column(Text)
    verdict: Mapped[Optional[str]] = mapped_column(String(10))  # 买入/观望/回避
    ai_model: Mapped[str] = mapped_column(String(30), default="local")
    analysis_json: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(10), default="SUCCESS")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
