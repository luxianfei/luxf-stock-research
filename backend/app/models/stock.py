from datetime import date
from typing import Optional

from sqlalchemy import String, Date, Integer, Float, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StockBasic(Base):
    __tablename__ = "stock_basic"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    stock_name: Mapped[str] = mapped_column(String(20), index=True)
    exchange: Mapped[str] = mapped_column(String(4))          # SH / SZ
    board: Mapped[Optional[str]] = mapped_column(String(20))  # 创业板/主板/科创板
    industry: Mapped[Optional[str]] = mapped_column(String(200))
    extra_industry_count: Mapped[int] = mapped_column(Integer, default=0)
    list_date: Mapped[Optional[date]] = mapped_column(Date)
    pe_ttm: Mapped[Optional[float]] = mapped_column(Float)
    pb: Mapped[Optional[float]] = mapped_column(Float)
    ps_ttm: Mapped[Optional[float]] = mapped_column(Float)
    current_market_cap_yi: Mapped[Optional[float]] = mapped_column(Float)
    latest_net_margin: Mapped[Optional[float]] = mapped_column(Float)
    forecast_revenue_y1_yi: Mapped[Optional[float]] = mapped_column(Float)
    forecast_revenue_y2_yi: Mapped[Optional[float]] = mapped_column(Float)
    forecast_revenue_y3_yi: Mapped[Optional[float]] = mapped_column(Float)
    ten_ps_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    ten_ps_fair_market_cap_yi: Mapped[Optional[float]] = mapped_column(Float)
    ten_ps_current_to_y1: Mapped[Optional[float]] = mapped_column(Float)
    ten_ps_valuation_verdict: Mapped[Optional[str]] = mapped_column(String(20))
    ten_ps_valuation_detail: Mapped[Optional[str]] = mapped_column(Text)
    valuation_level: Mapped[Optional[str]] = mapped_column(String(10))
    data_source: Mapped[str] = mapped_column(String(20), default="baostock")
    updated_at: Mapped[Optional[date]] = mapped_column(Date)
