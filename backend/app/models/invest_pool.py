from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InvestStockPool(Base):
    __tablename__ = "invest_stock_pool"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(12), index=True)
    stock_name: Mapped[str] = mapped_column(String(20))
    pool_type: Mapped[str] = mapped_column(String(20), default="tech_vc")  # quality / tech_vc
    pool_type_label: Mapped[Optional[str]] = mapped_column(String(20))
    memo: Mapped[Optional[str]] = mapped_column(Text)

    # 10PS valuation prices
    undervalued_price: Mapped[Optional[float]] = mapped_column(Float)
    fair_price: Mapped[Optional[float]] = mapped_column(Float)
    overvalued_price: Mapped[Optional[float]] = mapped_column(Float)
    target_buy_price: Mapped[Optional[float]] = mapped_column(Float)
    target_sell_price: Mapped[Optional[float]] = mapped_column(Float)
    target_price: Mapped[Optional[float]] = mapped_column(Float)

    # Revenue forecasts
    revenue_forecast_y0: Mapped[Optional[float]] = mapped_column(Float)
    revenue_forecast_y1: Mapped[Optional[float]] = mapped_column(Float)
    revenue_forecast_y2: Mapped[Optional[float]] = mapped_column(Float)
    revenue_2023: Mapped[Optional[float]] = mapped_column(Float)
    revenue_2024: Mapped[Optional[float]] = mapped_column(Float)
    revenue_2025: Mapped[Optional[float]] = mapped_column(Float)

    # Latest quarter metrics
    q1_gross_margin: Mapped[Optional[float]] = mapped_column(Float)
    q1_net_margin: Mapped[Optional[float]] = mapped_column(Float)
    q1_revenue_growth: Mapped[Optional[float]] = mapped_column(Float)

    min_ps_5y: Mapped[Optional[float]] = mapped_column(Float)
    target_market_cap: Mapped[Optional[float]] = mapped_column(Float)
    current_market_cap: Mapped[Optional[float]] = mapped_column(Float)
    ytd_gain_pct: Mapped[Optional[float]] = mapped_column(Float)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    pool_update_error: Mapped[Optional[str]] = mapped_column(Text)
    profit_level: Mapped[Optional[str]] = mapped_column(String(20))
    valuation_range: Mapped[Optional[str]] = mapped_column(String(10))  # 合理/低估/泡沫
    status: Mapped[str] = mapped_column(String(10), default="watching")
    status_label: Mapped[Optional[str]] = mapped_column(String(10))
    alert_state: Mapped[str] = mapped_column(String(20), default="none")
    last_alert_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    latest_price: Mapped[Optional[float]] = mapped_column(Float)
    ytd_gain: Mapped[Optional[float]] = mapped_column(Float)
    market_cap: Mapped[Optional[float]] = mapped_column(Float)
    latest_revenue_yoy: Mapped[Optional[float]] = mapped_column(Float)
    latest_profit_yoy: Mapped[Optional[float]] = mapped_column(Float)
    latest_level: Mapped[Optional[str]] = mapped_column(String(10))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
