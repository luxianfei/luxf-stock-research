"""
Local heuristic scoring for practical-select (Phase 1).
Phase 2 will integrate MiniMax AI API.
"""
from typing import Optional


def heuristic_rating(
    quarters: list[dict],
    trend_score: float,
    financial_score: float,
) -> dict:
    """
    Generate scarcity stars and growth stars based on financial metrics.
    This is the local fallback when AI is not available.
    """
    scarcity = _score_scarcity(quarters)
    growth = _score_growth(quarters)

    verdict = "观望"
    if scarcity >= 4 and growth >= 4:
        verdict = "买入"
    elif scarcity <= 2 or growth <= 2:
        verdict = "回避"

    summary = _generate_summary(quarters, scarcity, growth, verdict)

    return {
        "scarcity_stars": scarcity,
        "growth_stars": growth,
        "verdict": verdict,
        "summary_one_liner": summary,
    }


def _score_scarcity(quarters: list[dict]) -> int:
    """Score scarcity from 1-5 based on gross margin stability and level."""
    if not quarters:
        return 2

    margins = [q.get("gross_margin") for q in quarters if q.get("gross_margin") is not None]
    if not margins:
        return 2

    avg_margin = sum(margins) / len(margins)
    stability = max(margins) - min(margins)

    score = 2
    if avg_margin >= 50:
        score += 2
    elif avg_margin >= 35:
        score += 1

    if stability < 5:
        score += 1

    return min(5, score)


def _score_growth(quarters: list[dict]) -> int:
    """Score growth from 1-5 based on revenue and profit growth trends."""
    if not quarters:
        return 2

    rev_growths = [q.get("revenue_yoy") for q in quarters if q.get("revenue_yoy") is not None]
    profit_growths = [q.get("deducted_net_profit_yoy") for q in quarters if q.get("deducted_net_profit_yoy") is not None]

    score = 2

    if rev_growths:
        avg_rev = sum(rev_growths) / len(rev_growths)
        if avg_rev >= 30:
            score += 2
        elif avg_rev >= 15:
            score += 1

    if profit_growths:
        avg_profit = sum(profit_growths) / len(profit_growths)
        if avg_profit >= 30:
            score += 1

    return min(5, score)


def _generate_summary(quarters: list[dict], scarcity: int, growth: int, verdict: str) -> str:
    """Generate a one-liner summary."""
    if not quarters:
        return "数据不足，无法评估"

    latest = quarters[0]
    rev_yoy = latest.get("revenue_yoy")
    gm = latest.get("gross_margin")

    parts = []
    if rev_yoy and rev_yoy > 20:
        parts.append("营收高速增长")
    elif rev_yoy and rev_yoy > 0:
        parts.append("营收稳健增长")

    if gm and gm > 40:
        parts.append("毛利率优秀")
    elif gm and gm > 25:
        parts.append("毛利率良好")

    if scarcity >= 4:
        parts.append("稀缺性强")
    if growth >= 4:
        parts.append("成长动力充足")

    if not parts:
        parts.append("综合表现一般")

    return "，".join(parts) + f"，{verdict}。"


def compute_trend_score(monthly_klines: list[dict]) -> float:
    """
    Simple trend scoring based on price movement over 60 months.
    Returns 0-100 score.
    """
    if not monthly_klines or len(monthly_klines) < 2:
        return 50.0

    prices = [k.get("close", 0) for k in monthly_klines if k.get("close")]
    if not prices or len(prices) < 2:
        return 50.0

    current = prices[-1]
    start = prices[0]

    if start == 0:
        return 50.0

    total_return = (current - start) / start * 100

    # Check if trend is consistently upward
    higher_lows = sum(1 for i in range(1, len(prices)) if prices[i] > prices[i - 1])
    consistency = higher_lows / (len(prices) - 1) * 100

    score = (total_return * 0.3 + consistency * 0.7)
    return max(0, min(100, round(score, 1)))


def compute_financial_score(quarters: list[dict]) -> float:
    """
    Score financial health based on key metrics.
    Returns 0-100 score.
    """
    if not quarters:
        return 50.0

    scores = []

    # Gross margin trend
    margins = [q.get("gross_margin") for q in quarters if q.get("gross_margin") is not None]
    if margins:
        avg = sum(margins) / len(margins)
        scores.append(min(100, avg * 2))

    # Revenue growth
    revs = [q.get("revenue_yoy") for q in quarters if q.get("revenue_yoy") is not None]
    if revs:
        avg = sum(revs) / len(revs)
        scores.append(min(100, max(0, avg + 50)))

    # Net margin
    nms = [q.get("net_margin") for q in quarters if q.get("net_margin") is not None]
    if nms:
        avg = sum(nms) / len(nms)
        scores.append(min(100, max(0, avg * 4)))

    if not scores:
        return 50.0

    return round(sum(scores) / len(scores), 1)
