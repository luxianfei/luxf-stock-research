"""
Baostock data fetcher — wraps the synchronous baostock API
and runs it in a thread pool so it plays nicely with async FastAPI.
"""
import asyncio
import logging
import threading
from datetime import date, datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# baostock uses a global singleton socket — all operations must be serialized
_bs_lock = threading.Lock()


def _login():
    import baostock as bs
    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"baostock login failed: {lg.error_msg}")
    return bs, lg


def _logout(bs, lg):
    try:
        bs.logout()
    except Exception:
        pass


def _query_to_df(rs) -> pd.DataFrame:
    rows = []
    while (rs.error_code == '0') and rs.next():
        rows.append(rs.get_row_data())
    return pd.DataFrame(rows, columns=rs.fields)


def _sync_search_stock(keyword: str) -> list[dict]:
    """Search stock by code or name, return list of matches."""
    with _bs_lock:
        bs, lg = _login()
        try:
            # Try exact code match first
            code = keyword.strip()
            if code.isdigit() and len(code) == 6:
                # Determine exchange from code prefix
                if code.startswith(('6', '9')):
                    full_code = f"sh.{code}"
                    exchange = "SH"
                else:
                    full_code = f"sz.{code}"
                    exchange = "SZ"
                rs = bs.query_stock_basic(code=full_code)
                df = _query_to_df(rs)
                if not df.empty:
                    row = df.iloc[0]
                    return [{
                        "stock_code": f"{code}.{exchange}",
                        "stock_name": row.get("code_name", ""),
                        "exchange": exchange,
                        "ipo_date": row.get("ipoDate", ""),
                    }]

            # Fallback: search all stocks by name
            rs = bs.query_stock_basic()
            df = _query_to_df(rs)
            if df.empty:
                return []
            mask = df["code_name"].str.contains(keyword, na=False) | df["code"].str.contains(keyword, na=False)
            matches = df[mask]
            results = []
            for _, row in matches.head(10).iterrows():
                code = row["code"]
                ex = code.split(".")[0].upper() if "." in code else ""
                pure_code = code.split(".")[1] if "." in code else code
                results.append({
                    "stock_code": f"{pure_code}.{ex}" if ex else code,
                    "stock_name": row.get("code_name", ""),
                    "exchange": ex,
                    "ipo_date": row.get("ipoDate", ""),
                })
            return results
        finally:
            _logout(bs, lg)


def _sync_get_quarterly_data(stock_code: str, quarters: int = 16) -> list[dict]:
    """Fetch quarterly financial data for a stock."""
    _bs_lock.acquire()
    try:
        bs, lg = _login()
        # Convert code format: 301536.SZ -> sz.301536
        parts = stock_code.split(".")
        if len(parts) == 2:
            bs_code = f"{parts[1].lower()}.{parts[0]}"
        else:
            bs_code = stock_code

        # Fetch profit, balance, growth, and cash flow data
        profit_by_date = {}
        balance_by_date = {}
        growth_by_date = {}
        cashflow_by_date = {}

        # Fetch profit data
        for year in range(datetime.now().year, datetime.now().year - 5, -1):
            for q in [4, 3, 2, 1]:
                try:
                    rs = bs.query_profit_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                profit_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Profit data fetch failed for {bs_code} {year}Q{q}: {e}")

        # Fetch balance data
        for year in range(datetime.now().year, datetime.now().year - 5, -1):
            for q in [4, 3, 2, 1]:
                try:
                    rs = bs.query_balance_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                balance_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Balance data fetch failed for {bs_code} {year}Q{q}: {e}")

        # Fetch growth data
        for year in range(datetime.now().year, datetime.now().year - 5, -1):
            for q in [4, 3, 2, 1]:
                try:
                    rs = bs.query_growth_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                growth_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Growth data fetch failed for {bs_code} {year}Q{q}: {e}")

        # Fetch cash flow data (optional)
        for year in range(datetime.now().year, datetime.now().year - 5, -1):
            for q in [4, 3, 2, 1]:
                try:
                    rs = bs.query_cash_flow_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                cashflow_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Cash flow data fetch failed for {bs_code} {year}Q{q}: {e}")

        # Fetch operation data (for asset turnover ratio)
        operation_by_date = {}
        for year in range(datetime.now().year, datetime.now().year - 5, -1):
            for q in [4, 3, 2, 1]:
                try:
                    rs = bs.query_operation_data(code=bs_code, year=year, quarter=q)
                    df = _query_to_df(rs)
                    if not df.empty:
                        for _, row in df.iterrows():
                            stat_date = row.get("statDate", "")
                            if stat_date:
                                operation_by_date[stat_date] = row.to_dict()
                except Exception as e:
                    logger.debug(f"Operation data fetch failed for {bs_code} {year}Q{q}: {e}")

        # Merge by statDate (sorted descending)
        all_dates = sorted(profit_by_date.keys(), reverse=True)
        if not all_dates:
            return []

        # Fetch supplemental data from akshare (扣非净利润 + total revenue)
        akshare_data = {}
        try:
            akshare_data = _sync_fetch_akshare_supplement(stock_code)
        except Exception as e:
            logger.warning(f"akshare supplement fetch failed for {stock_code}: {e}")

        # Add akshare-only dates to fill gaps (e.g. 24Q1 when baostock lacks it)
        # These quarters provide revenue and deducted_net_profit for
        # cumulative→single-quarter conversion of later quarters.
        for ak_date in akshare_data:
            if ak_date not in profit_by_date:
                profit_by_date[ak_date] = {"_from_akshare": True}
                all_dates = sorted(profit_by_date.keys(), reverse=True)

        results = []
        for stat_date in all_dates[:quarters]:
            quarter_label = _format_quarter(stat_date)
            profit = profit_by_date.get(stat_date, {})
            balance = balance_by_date.get(stat_date, {})
            growth = growth_by_date.get(stat_date, {})
            cashflow = cashflow_by_date.get(stat_date, {})
            operation = operation_by_date.get(stat_date, {}) if operation_by_date else {}

            # ---- Profit data (absolute values in yuan) ----
            net_profit_abs = _safe_float(profit.get("netProfit"))
            revenue_abs = _safe_float(profit.get("MBRevenue"))
            np_margin = _safe_float(profit.get("npMargin"))
            gp_margin = _safe_float(profit.get("gpMargin"))
            roe_avg = _safe_float(profit.get("roeAvg"))
            eps_ttm = _safe_float(profit.get("epsTTM"))

            # If MBRevenue is missing, estimate from netProfit / npMargin
            if revenue_abs is None and net_profit_abs and np_margin and np_margin != 0:
                revenue_abs = net_profit_abs / np_margin

            # ---- Merge akshare supplement data ----
            ak_quarter = akshare_data.get(stat_date, {})
            # Prefer akshare total revenue (营业收入) over baostock MBRevenue (主营营业收入)
            ak_revenue = ak_quarter.get("revenue_total")
            if ak_revenue is not None:
                revenue_abs = ak_revenue
            # 扣非净利润 (cumulative, yuan)
            deducted_net_profit_abs = ak_quarter.get("deducted_net_profit")

            # For akshare-only quarters (baostock has no data), revenue already set above
            # np_margin not available — will be recalculated in process_quarters_for_display

            # ---- Balance data (ratios only) ----
            current_ratio = _safe_float(balance.get("currentRatio"))
            liability_to_asset = _safe_float(balance.get("liabilityToAsset"))
            # Debt ratio: liabilityToAsset is fraction (0~1), convert to percentage
            debt_ratio_calc = None
            if liability_to_asset is not None:
                debt_ratio_calc = liability_to_asset * 100  # e.g., 0.3674 -> 36.74%

            # ---- Growth data ----
            # YOYNI is net income YoY growth, NOT deducted net profit YoY (扣非同比).
            # deducted_net_profit_yoy will be calculated on-the-fly from single-quarter net profit.
            deducted_net_profit_yoy = None
            # Revenue YoY not directly available; approximate with YOYAsset as fallback
            revenue_yoy = None  # not available from baostock growth data

            # ---- Cash flow data (ratios) ----
            # CFOToNP = operating cash flow / net profit ratio
            cfo_to_np = _safe_float(cashflow.get("CFOToNP"))
            operating_cashflow = None
            if cfo_to_np is not None and net_profit_abs is not None:
                operating_cashflow = cfo_to_np * net_profit_abs  # in yuan

            # ---- Derived: total_assets (estimate from asset turnover) ----
            # AssetTurnRatio = revenue / total_assets → total_assets = revenue / AssetTurnRatio
            total_assets_est = None
            total_equity_est = None
            asset_turn = _safe_float(operation.get("AssetTurnRatio"))
            if asset_turn and asset_turn > 0 and revenue_abs:
                total_assets_est = revenue_abs / asset_turn
                # total_equity = total_assets * (1 - debt_ratio_fraction)
                if liability_to_asset is not None:
                    total_equity_est = total_assets_est * (1 - liability_to_asset)

            # ---- Derived: ROA ----
            roa_calc = None
            if net_profit_abs is not None and total_assets_est and total_assets_est > 0:
                roa_calc = net_profit_abs / total_assets_est

            row = {
                "quarter": quarter_label,
                "report_date": stat_date,
                "revenue_yoy": revenue_yoy,
                "deducted_net_profit_yoy": deducted_net_profit_yoy,
                "gross_margin": gp_margin,
                "net_margin": np_margin,
                "roe": roe_avg,
                "roa": roa_calc,
                "eps": eps_ttm,
                "revenue": revenue_abs,
                "net_profit": net_profit_abs,
                "deducted_net_profit": deducted_net_profit_abs,
                "deducted_net_profit_ttm": None,
                "total_assets": total_assets_est,
                "total_equity": total_equity_est,
                "operating_cashflow": operating_cashflow,
                "debt_ratio": debt_ratio_calc,
                "current_ratio": current_ratio,
            }

            results.append(row)

        return results
    finally:
        _logout(bs, lg)
        _bs_lock.release()


def _format_quarter(stat_date: str) -> str:
    """Convert '2024-03-31' to '24Q1'."""
    try:
        dt = datetime.strptime(stat_date, "%Y-%m-%d")
        q = (dt.month - 1) // 3 + 1
        return f"{str(dt.year)[2:]}Q{q}"
    except Exception:
        return stat_date


def _safe_float(val) -> Optional[float]:
    if val is None or val == "" or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return round(float(val), 4)
    except (ValueError, TypeError):
        return None


def _sync_get_monthly_klines(stock_code: str, months: int = 60) -> list[dict]:
    """Fetch monthly K-line data for trend analysis."""
    _bs_lock.acquire()
    bs, lg = _login()
    try:
        bs_code = _to_bs_code(stock_code)
        end_date = date.today().strftime("%Y-%m-%d")
        # Approximate start date: go back `months` months
        start_year = date.today().year - (months // 12 + 1)
        start_date = f"{start_year}-01-01"

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume,amount,turn,pctChg",
            start_date=start_date,
            end_date=end_date,
            frequency="m",  # monthly
            adjustflag="2",  # 前复权
        )
        df = _query_to_df(rs)
        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            results.append({
                "date": row.get("date", ""),
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "close": _safe_float(row.get("close")),
                "volume": _safe_float(row.get("volume")),
                "amount": _safe_float(row.get("amount")),
                "turn": _safe_float(row.get("turn")),
                "pct_chg": _safe_float(row.get("pctChg")),
            })
        return results
    finally:
        _logout(bs, lg)
        _bs_lock.release()


def _sync_get_daily_klines(stock_code: str, days: int = 120) -> list[dict]:
    """Fetch daily K-line data for big-yang detection."""
    _bs_lock.acquire()
    bs, lg = _login()
    try:
        bs_code = _to_bs_code(stock_code)
        end_date = date.today().strftime("%Y-%m-%d")
        # Go back `days` calendar days (add buffer for weekends/holidays)
        from datetime import timedelta
        start_date = (date.today() - timedelta(days=int(days * 1.6))).strftime("%Y-%m-%d")

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg,isST",
            start_date=start_date,
            end_date=end_date,
            frequency="d",  # daily
            adjustflag="2",  # 前复权
        )
        df = _query_to_df(rs)
        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            results.append({
                "date": row.get("date", ""),
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "close": _safe_float(row.get("close")),
                "preclose": _safe_float(row.get("preclose")),
                "volume": _safe_float(row.get("volume")),
                "amount": _safe_float(row.get("amount")),
                "turn": _safe_float(row.get("turn")),
                "pct_chg": _safe_float(row.get("pctChg")),
                "is_st": row.get("isST", "0"),
            })
        return results[-days:]  # limit to requested days
    finally:
        _logout(bs, lg)
        _bs_lock.release()


def _to_bs_code(stock_code: str) -> str:
    """Convert '301536.SZ' to 'sz.301536' format for baostock."""
    parts = stock_code.split(".")
    if len(parts) == 2:
        return f"{parts[1].lower()}.{parts[0]}"
    return stock_code


def _sync_get_latest_price(stock_code: str) -> Optional[dict]:
    """Get the latest trading day's price data."""
    klines = _sync_get_daily_klines(stock_code, days=5)
    if not klines:
        return None
    return klines[-1]


def _pure_code(stock_code: str) -> str:
    """Convert '301536.SZ' to '301536'."""
    return stock_code.split(".")[0] if "." in stock_code else stock_code


def _normalize_date(raw: str) -> str | None:
    """Normalize various date formats to YYYY-MM-DD."""
    raw = raw.strip()
    if not raw:
        return None
    if len(raw) == 10 and raw[4] == "-":
        return raw
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _sync_fetch_akshare_supplement(stock_code: str) -> dict[str, dict]:
    """
    Fetch supplemental data from akshare (Sina source):
    - 扣除非经常性损益后的净利润 (cumulative, yuan)
    - 营业收入 (cumulative, yuan) from 利润表

    Returns dict keyed by report_date (YYYY-MM-DD).
    """
    code = _pure_code(stock_code)
    result: dict[str, dict] = {}

    # 1. 扣非净利润 from stock_financial_analysis_indicator
    try:
        import akshare as ak
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2019")
        for _, row in df.iterrows():
            rd = _normalize_date(str(row.get("日期", "")))
            if not rd:
                continue
            dnp = _safe_float(row.get("扣除非经常性损益后的净利润(元)"))
            if rd not in result:
                result[rd] = {}
            if dnp is not None:
                result[rd]["deducted_net_profit"] = dnp
    except Exception as e:
        logger.warning(f"akshare financial_analysis_indicator failed for {code}: {e}")

    # 2. 营业收入 from stock_financial_report_sina 利润表
    try:
        import akshare as ak
        df = ak.stock_financial_report_sina(stock=code, symbol="利润表")
        for _, row in df.iterrows():
            rd = _normalize_date(str(row.get("报告日", "")))
            if not rd:
                continue
            rev = _safe_float(row.get("营业收入"))
            if rd not in result:
                result[rd] = {}
            if rev is not None:
                result[rd]["revenue_total"] = rev
    except Exception as e:
        logger.warning(f"akshare financial_report_sina failed for {code}: {e}")

    logger.info(f"akshare supplement for {code}: {len(result)} quarters fetched")
    return result


# ---- Async wrappers ----

async def search_stock(keyword: str) -> list[dict]:
    return await asyncio.to_thread(_sync_search_stock, keyword)


async def get_quarterly_data(stock_code: str, quarters: int = 16) -> list[dict]:
    return await asyncio.to_thread(_sync_get_quarterly_data, stock_code, quarters)


async def get_monthly_klines(stock_code: str, months: int = 60) -> list[dict]:
    return await asyncio.to_thread(_sync_get_monthly_klines, stock_code, months)


async def get_daily_klines(stock_code: str, days: int = 120) -> list[dict]:
    return await asyncio.to_thread(_sync_get_daily_klines, stock_code, days)


async def get_latest_price(stock_code: str) -> Optional[dict]:
    return await asyncio.to_thread(_sync_get_latest_price, stock_code)


async def get_stock_basic_info(stock_code: str, quarters_data: list[dict] | None = None) -> Optional[dict]:
    """Get basic stock info + computed valuation metrics."""
    results = await search_stock(stock_code)
    if not results:
        return None

    info = results[0]
    # Use pre-fetched quarters if provided, otherwise fetch
    quarters = quarters_data or await get_quarterly_data(stock_code, quarters=8)
    if quarters:
        latest = quarters[0]
        info["latest_net_margin"] = latest.get("net_margin")

        # Revenue is now in yuan; convert to 亿元 for forecast
        latest_revenue = latest.get("revenue")
        if latest_revenue and latest_revenue > 0:
            revenue_yi = latest_revenue / 1e8  # yuan -> 亿元
            y1_revenue_yi = revenue_yi * 1.2   # naive 20% growth
            y2_revenue_yi = y1_revenue_yi * 1.2
            info["forecast_revenue_y1_yi"] = round(y1_revenue_yi, 2)
            info["forecast_revenue_y2_yi"] = round(y2_revenue_yi, 2)

            # 10PS: fair market cap = next year revenue(亿) × 10
            nm = latest.get("net_margin", 0) or 0
            ten_ps_fair = y1_revenue_yi * 10  # 亿元
            info["ten_ps_fair_market_cap_yi"] = round(ten_ps_fair, 2)
            if nm >= 0.20:  # net margin ≥ 20%
                info["ten_ps_candidate"] = True
                info["ten_ps_valuation_verdict"] = "合理/低估"
                info["ten_ps_valuation_detail"] = "净利率接近25%，适用10PS标尺"
            else:
                info["ten_ps_candidate"] = False
                info["ten_ps_valuation_verdict"] = "不适用"
                info["ten_ps_valuation_detail"] = "净利率未接近25%，不按10PS标尺"

    info["updated_at"] = "刚刚更新"
    return info
