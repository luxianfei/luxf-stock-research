from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class QuarterData(_CamelBase):
    quarter: str
    report_date: str
    revenue_yoy: Optional[float] = None
    revenue_qoq: Optional[float] = None
    deducted_net_profit_yoy: Optional[float] = None
    net_profit_qoq: Optional[float] = None
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    eps: Optional[float] = None
    revenue: Optional[float] = None
    net_profit: Optional[float] = None
    deducted_net_profit_ttm: Optional[float] = None
    total_assets: Optional[float] = None
    total_equity: Optional[float] = None
    operating_cashflow: Optional[float] = None
    debt_ratio: Optional[float] = None
    current_ratio: Optional[float] = None


class BasicInfo(_CamelBase):
    stock_code: str
    stock_name: str
    exchange: str
    board: Optional[str] = None
    industry: Optional[str] = None
    extra_industry_count: int = 0
    list_date: Optional[str] = None
    list_years: int = 0
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps_ttm: Optional[float] = None
    current_market_cap_yi: Optional[float] = None
    latest_net_margin: Optional[float] = None
    forecast_revenue_y1_yi: Optional[float] = None
    forecast_revenue_y2_yi: Optional[float] = None
    forecast_revenue_y3_yi: Optional[float] = None
    ten_ps_candidate: bool = False
    ten_ps_fair_market_cap_yi: Optional[float] = None
    ten_ps_current_to_y1: Optional[float] = None
    ten_ps_valuation_verdict: Optional[str] = None
    ten_ps_valuation_detail: Optional[str] = None
    valuation_level: Optional[str] = None
    data_source: str = "baostock"
    updated_at: Optional[str] = None


class StockFinancialData(_CamelBase):
    stock_code: str
    stock_name: str
    basic_info: BasicInfo
    quarters: list[QuarterData]


class FinancialQueryResponse(_CamelBase):
    requested: int
    matched: int
    not_found: list[str] = []
    stocks: list[StockFinancialData]
