from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class _CamelORM(_CamelBase):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PoolItemCreate(_CamelBase):
    keyword: str
    pool_type: str = "tech_vc"
    status: str = "watching"
    memo: Optional[str] = None
    target_price: Optional[float] = None


class PoolItemUpdate(_CamelBase):
    revenue_forecast_y0: Optional[float] = None
    revenue_forecast_y1: Optional[float] = None
    revenue_forecast_y2: Optional[float] = None
    memo: Optional[str] = None
    status: Optional[str] = None


class PoolItemResponse(_CamelORM):
    id: int
    stock_code: str
    stock_name: str
    pool_type: str
    pool_type_label: Optional[str] = None
    memo: Optional[str] = None
    undervalued_price: Optional[float] = None
    fair_price: Optional[float] = None
    overvalued_price: Optional[float] = None
    revenue_forecast_y0: Optional[float] = None
    revenue_forecast_y1: Optional[float] = None
    revenue_forecast_y2: Optional[float] = None
    revenue_2023: Optional[float] = None
    revenue_2024: Optional[float] = None
    revenue_2025: Optional[float] = None
    q1_gross_margin: Optional[float] = None
    q1_net_margin: Optional[float] = None
    q1_revenue_growth: Optional[float] = None
    min_ps_5y: Optional[float] = None
    current_market_cap: Optional[float] = None
    ytd_gain_pct: Optional[float] = None
    valuation_range: Optional[str] = None
    status: str
    status_label: Optional[str] = None
    latest_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class BigYangSummary(_CamelBase):
    unread_alert_count: int = 0
    watching_count: int = 0
    triggered_count: int = 0
    expired_count: int = 0
    today_new_watching_count: int = 0
    today_triggered_count: int = 0


class BigYangSignalResponse(_CamelORM):
    id: int
    stock_code: str
    stock_name: str
    signal_type: str
    trigger_price: Optional[float] = None
    base_price: Optional[float] = None
    status: str
    created_at: datetime


class BigYangAlertResponse(_CamelORM):
    id: int
    stock_code: str
    stock_name: str
    title: str
    message: Optional[str] = None
    read: bool
    trigger_at: Optional[datetime] = None


class SopCheckupMetric(_CamelBase):
    label: str
    verdict: str  # pass / warn / fail
    latest: Optional[float] = None
    unit: str = "%"
    tip: str = ""
    series: list[dict] = []


class SopCheckupResponse(_CamelBase):
    matched: bool
    stock_name: Optional[str] = None
    stock_code: Optional[str] = None
    overall_verdict: str = "warn"
    overall_summary: str = ""
    gross_margin: Optional[SopCheckupMetric] = None
    revenue_yoy: Optional[SopCheckupMetric] = None
    profit_yoy: Optional[SopCheckupMetric] = None
    message: Optional[str] = None


class PracticalSelectRequest(_CamelBase):
    keyword: str


class PracticalSelectResponse(_CamelORM):
    id: int
    stock_code: str
    stock_name: str
    trend_score: Optional[float] = None
    financial_score: Optional[float] = None
    scarcity_stars: Optional[int] = None
    growth_stars: Optional[int] = None
    ten_ps_verdict: Optional[str] = None
    summary_one_liner: Optional[str] = None
    verdict: Optional[str] = None
    ai_model: str = "local"
    status: str
    submitted_at: datetime
    completed_at: Optional[datetime] = None
