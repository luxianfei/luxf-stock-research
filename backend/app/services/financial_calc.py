"""
Financial calculations and helpers.
"""
from types import SimpleNamespace
from typing import Optional
from datetime import date, datetime


def compute_10ps_valuation(
    current_market_cap_yi: float,
    forecast_revenue_y1_yi: Optional[float],
    forecast_revenue_y2_yi: Optional[float],
    latest_net_margin: Optional[float],
) -> dict:
    """
    10PS valuation method:
    - Fair market cap = next year forecast revenue × 10
    - Candidate if net margin >= 20%
    - Verdict: fair / undervalued / bubble
    """
    result = {
        "ten_ps_candidate": False,
        "ten_ps_fair_market_cap_yi": None,
        "ten_ps_current_to_y1": None,
        "ten_ps_valuation_verdict": "不适用",
        "ten_ps_valuation_detail": "",
    }

    nm = latest_net_margin or 0
    # nm could be fraction (0.22) or percentage (22), normalize
    if nm < 1:
        nm_pct = nm * 100
    else:
        nm_pct = nm
    if nm_pct < 20:
        result["ten_ps_valuation_detail"] = "净利率未接近25%，不按10PS标尺"
        return result

    result["ten_ps_candidate"] = True

    if forecast_revenue_y1_yi and forecast_revenue_y1_yi > 0:
        fair_cap = forecast_revenue_y1_yi * 10
        result["ten_ps_fair_market_cap_yi"] = round(fair_cap, 2)

        if current_market_cap_yi and current_market_cap_yi > 0:
            ratio = current_market_cap_yi / fair_cap
            result["ten_ps_current_to_y1"] = round(ratio, 2)

            if ratio < 0.7:
                result["ten_ps_valuation_verdict"] = "低估"
                result["ten_ps_valuation_detail"] = f"当前市值仅为Y1×10的{ratio:.0%}"
            elif ratio <= 1.3:
                result["ten_ps_valuation_verdict"] = "合理/低估"
                result["ten_ps_valuation_detail"] = f"当前市值接近Y1×10"
            else:
                result["ten_ps_valuation_verdict"] = "泡沫"
                result["ten_ps_valuation_detail"] = f"当前市值超过Y1×10的{ratio:.0%}"

    return result


def format_quarter_label(year: int, quarter: int) -> str:
    """Format as '26Q1'."""
    return f"{str(year)[2:]}Q{quarter}"


def parse_report_date(date_str: str) -> tuple[int, int]:
    """Parse '2026-03-31' → (2026, 1)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    q = (dt.month - 1) // 3 + 1
    return dt.year, q


# Percentage fields that should be multiplied by 100 for display
_PCT_FIELDS = [
    "gross_margin", "net_margin", "roe", "roa",
    "revenue_yoy", "deducted_net_profit_yoy",
]

# Cumulative fields that need single-quarter conversion
_CUMULATIVE_FIELDS = ["revenue", "net_profit", "deducted_net_profit"]


def _quarter_num(report_date) -> int:
    """Get quarter number (1-4) from a date or date string."""
    if isinstance(report_date, str):
        dt = datetime.strptime(report_date, "%Y-%m-%d")
    elif isinstance(report_date, date):
        dt = report_date
    else:
        return 0
    return (dt.month - 1) // 3 + 1


def _year_of(report_date) -> int:
    if isinstance(report_date, str):
        return int(report_date[:4])
    elif isinstance(report_date, date):
        return report_date.year
    return 0


def _prev_quarter_key(yr: int, qn: int) -> tuple[int, int]:
    """Return the (year, quarter_num) key for the preceding quarter."""
    if qn == 1:
        return (yr - 1, 4)
    return (yr, qn - 1)


def process_quarters_for_display(quarters: list) -> list:
    """
    Transform raw DB quarter data for frontend display:
    1. Convert cumulative revenue/net_profit to single-quarter (pass 1)
    2. Recalculate net_margin from single-quarter values (pass 2)
    3. Calculate revenue_yoy from single-quarter values (pass 2, already in %)
    4. Convert fraction fields to percentage (pass 2, ×100)
    5. Fix debt_ratio unit inconsistency (pass 2)
    """
    if not quarters:
        return quarters

    # Convert ORM objects to plain copies to avoid SQLAlchemy identity map issues.
    # Without this, the session returns the same modified objects on subsequent calls,
    # causing double-conversion of cumulative→single-quarter values.
    _FIELDS = [
        "quarter", "report_date", "revenue_yoy", "deducted_net_profit_yoy",
        "gross_margin", "net_margin", "roe", "roa", "eps", "revenue",
        "net_profit", "deducted_net_profit", "deducted_net_profit_ttm",
        "total_assets", "total_equity", "operating_cashflow",
        "debt_ratio", "current_ratio",
        # On-the-fly fields (not DB columns, computed in Pass 2):
        "revenue_qoq", "net_profit_qoq",
    ]
    quarters = [
        SimpleNamespace(**{f: getattr(q, f, None) for f in _FIELDS})
        for q in quarters
    ]

    # Build lookup: (year, quarter_num) → quarter object
    qmap: dict[tuple[int, int], object] = {}
    for q in quarters:
        rd = q.report_date
        yr = _year_of(rd)
        qn = _quarter_num(rd)
        qmap[(yr, qn)] = q

    # --- Pass 1: Single-quarter conversion for cumulative fields ---
    # Must complete for ALL quarters before any cross-quarter comparisons (YoY)
    for q in quarters:
        rd = q.report_date
        yr = _year_of(rd)
        qn = _quarter_num(rd)

        # Save cumulative revenue before conversion (needed for gross_margin calc)
        cum_revenue = getattr(q, "revenue", None)
        cum_gp_margin = getattr(q, "gross_margin", None)

        for field in _CUMULATIVE_FIELDS:
            cum_val = getattr(q, field, None)
            if cum_val is None:
                continue
            if qn == 1:
                # Q1: cumulative = single quarter
                pass
            else:
                prev = qmap.get((yr, qn - 1))
                prev_cum = getattr(prev, field, None) if prev else None
                if prev_cum is not None:
                    setattr(q, field, cum_val - prev_cum)

        # Convert cumulative gross_margin to single-quarter gross_margin
        # gpMargin from baostock is cumulative: (cum_revenue - cum_cogs) / cum_revenue
        if cum_gp_margin is not None and cum_revenue and cum_revenue > 0:
            sq_revenue = getattr(q, "revenue", None)
            if qn == 1:
                # Q1: cumulative = single quarter, gpMargin is already single-quarter
                pass  # keep cum_gp_margin as-is
            else:
                # Q2-Q4: single-quarter gross profit = cum_gp - prev_cum_gp
                cum_gp = cum_revenue * cum_gp_margin
                prev_q = qmap.get((yr, qn - 1))
                prev_cum_rev = getattr(prev_q, "revenue", None) if prev_q else None
                prev_cum_gp_m = getattr(prev_q, "gross_margin", None) if prev_q else None
                if prev_cum_rev is not None and prev_cum_gp_m is not None:
                    prev_cum_gp = prev_cum_rev * prev_cum_gp_m
                    sq_gp = cum_gp - prev_cum_gp
                    if sq_revenue and sq_revenue > 0:
                        q.gross_margin = sq_gp / sq_revenue
                    # else: keep cumulative gpMargin as fallback

    # --- Pass 2: Derived metrics (all quarters now have single-quarter values) ---
    for q in quarters:
        rd = q.report_date
        yr = _year_of(rd)
        qn = _quarter_num(rd)

        # Recalculate net_margin from single-quarter values
        sq_revenue = getattr(q, "revenue", None)
        sq_net_profit = getattr(q, "net_profit", None)
        if sq_revenue and sq_revenue > 0 and sq_net_profit is not None:
            q.net_margin = round(sq_net_profit / sq_revenue, 6)

        # Revenue YoY (already in percentage)
        # Use abs(prev) as denominator: standard financial convention to avoid sign inversion
        # when the previous period is negative.
        if getattr(q, "revenue_yoy", None) is None:
            cur_rev = getattr(q, "revenue", None)
            prev_year_q = qmap.get((yr - 1, qn))
            prev_rev = getattr(prev_year_q, "revenue", None) if prev_year_q else None
            if cur_rev is not None and prev_rev is not None and prev_rev != 0:
                q.revenue_yoy = round(((cur_rev - prev_rev) / abs(prev_rev)) * 100, 4)

        # 扣非同比 (deducted_net_profit_yoy) — from single-quarter 扣非净利润
        # Falls back to net_profit if 扣非 data not available
        # Use abs(prev) as denominator: when last year same quarter was a loss (negative),
        # standard formula inverts sign. Financial convention uses abs() to correctly show
        # loss→profit as positive growth.
        if getattr(q, "deducted_net_profit_yoy", None) is None:
            cur_dnp = getattr(q, "deducted_net_profit", None)
            prev_year_q = qmap.get((yr - 1, qn))
            prev_dnp = getattr(prev_year_q, "deducted_net_profit", None) if prev_year_q else None
            if cur_dnp is not None and prev_dnp is not None and prev_dnp != 0:
                q.deducted_net_profit_yoy = round(((cur_dnp - prev_dnp) / abs(prev_dnp)) * 100, 4)
            else:
                # Fallback: use net_profit YoY
                cur_np = getattr(q, "net_profit", None)
                prev_np = getattr(prev_year_q, "net_profit", None) if prev_year_q else None
                if cur_np is not None and prev_np is not None and prev_np != 0:
                    q.deducted_net_profit_yoy = round(((cur_np - prev_np) / abs(prev_np)) * 100, 4)

        # Revenue QoQ (环比) — use abs(prev) for consistency
        if getattr(q, "revenue_qoq", None) is None:
            cur_rev = getattr(q, "revenue", None)
            prev_key = _prev_quarter_key(yr, qn)
            prev_q_obj = qmap.get(prev_key)
            prev_rev = getattr(prev_q_obj, "revenue", None) if prev_q_obj else None
            if cur_rev is not None and prev_rev is not None and prev_rev != 0:
                q.revenue_qoq = round(((cur_rev - prev_rev) / abs(prev_rev)) * 100, 4)

        # Net profit QoQ (环比) — use abs(prev) for consistency
        if getattr(q, "net_profit_qoq", None) is None:
            cur_np = getattr(q, "net_profit", None)
            prev_key = _prev_quarter_key(yr, qn)
            prev_q_obj = qmap.get(prev_key)
            prev_np = getattr(prev_q_obj, "net_profit", None) if prev_q_obj else None
            if cur_np is not None and prev_np is not None and prev_np != 0:
                q.net_profit_qoq = round(((cur_np - prev_np) / abs(prev_np)) * 100, 4)

        # 扣非TTM = sum of trailing 4 quarters' single-quarter 扣非净利润
        # Falls back to net_profit if 扣非 data not available
        if getattr(q, "deducted_net_profit_ttm", None) is None:
            ttm_sum = 0.0
            ttm_complete = True
            cur_yr, cur_qn = yr, qn
            use_dnp = True  # try 扣非 first
            for _ in range(4):
                lookup = qmap.get((cur_yr, cur_qn))
                if lookup is None:
                    ttm_complete = False
                    break
                val = getattr(lookup, "deducted_net_profit", None)
                if val is None:
                    # If any quarter missing 扣非, fall back to net_profit for all
                    use_dnp = False
                    break
                ttm_sum += val
                cur_yr, cur_qn = _prev_quarter_key(cur_yr, cur_qn)
            # Fallback to net_profit if 扣非 not fully available
            if not use_dnp:
                ttm_sum = 0.0
                ttm_complete = True
                cur_yr, cur_qn = yr, qn
                for _ in range(4):
                    lookup = qmap.get((cur_yr, cur_qn))
                    np_val = getattr(lookup, "net_profit", None) if lookup else None
                    if np_val is None:
                        ttm_complete = False
                        break
                    ttm_sum += np_val
                    cur_yr, cur_qn = _prev_quarter_key(cur_yr, cur_qn)
            if ttm_complete:
                q.deducted_net_profit_ttm = round(ttm_sum, 4)

        # Convert fraction fields to percentage
        # gross_margin, roe, roa: stored as fraction → ×100
        for field in ["gross_margin", "roe", "roa"]:
            val = getattr(q, field, None)
            if val is not None:
                setattr(q, field, round(val * 100, 4))

        # net_margin was recalculated above as fraction → ×100
        if q.net_margin is not None:
            q.net_margin = round(q.net_margin * 100, 4)

        # revenue_yoy, deducted_net_profit_yoy, revenue_qoq, net_profit_qoq
        # are already in % — do NOT multiply

        # Fix debt_ratio: normalize to percentage
        dr = getattr(q, "debt_ratio", None)
        if dr is not None:
            if dr < 1:
                q.debt_ratio = round(dr * 100, 2)
            else:
                q.debt_ratio = round(dr, 2)

    return quarters
