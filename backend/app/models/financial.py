from datetime import date
from typing import Optional

from sqlalchemy import String, Date, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FinancialQuarterly(Base):
    __tablename__ = "financial_quarterly"
    __table_args__ = (
        Index("ix_fq_stock_report", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(12), ForeignKey("stock_basic.stock_code"), index=True)
    quarter: Mapped[str] = mapped_column(String(6))  # e.g. "26Q1"
    report_date: Mapped[date] = mapped_column(Date)

    revenue_yoy: Mapped[Optional[float]] = mapped_column(Float)
    deducted_net_profit_yoy: Mapped[Optional[float]] = mapped_column(Float)
    gross_margin: Mapped[Optional[float]] = mapped_column(Float)
    net_margin: Mapped[Optional[float]] = mapped_column(Float)
    roe: Mapped[Optional[float]] = mapped_column(Float)
    roa: Mapped[Optional[float]] = mapped_column(Float)
    eps: Mapped[Optional[float]] = mapped_column(Float)
    revenue: Mapped[Optional[float]] = mapped_column(Float)
    net_profit: Mapped[Optional[float]] = mapped_column(Float)
    deducted_net_profit: Mapped[Optional[float]] = mapped_column(Float)  # cumulative 扣非净利润 from akshare
    deducted_net_profit_ttm: Mapped[Optional[float]] = mapped_column(Float)
    total_assets: Mapped[Optional[float]] = mapped_column(Float)
    total_equity: Mapped[Optional[float]] = mapped_column(Float)
    operating_cashflow: Mapped[Optional[float]] = mapped_column(Float)
    debt_ratio: Mapped[Optional[float]] = mapped_column(Float)
    current_ratio: Mapped[Optional[float]] = mapped_column(Float)
