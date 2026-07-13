"""
Composite scoring engine.
Produces a 0-10 score from weighted factors, mirroring the reel's
"Valuation / Growth / Financial Health / Momentum / Sector Tailwind" breakdown —
but fully transparent: every sub-score shows its inputs, nothing is a black box.
"""

from config import SCORE_WEIGHTS
from rules_engine import count_fails


def _clamp(x, lo=0, hi=10):
    return max(lo, min(hi, x))


def score_valuation(fundamentals: dict, peer_pe_median: float = None) -> float:
    """Lower P/E relative to peers = higher score. Missing data = neutral 5."""
    pe = fundamentals.get("pe_ratio")
    if pe is None or pe <= 0:
        return 5.0
    if peer_pe_median and peer_pe_median > 0:
        ratio = pe / peer_pe_median
        # ratio 1.0 (in line with peers) -> score 6; ratio 3x peers -> score ~1
        score = 8 - (ratio * 2.5)
    else:
        # No peer data: fall back to absolute bands
        if pe < 15:
            score = 8.5
        elif pe < 30:
            score = 6.5
        elif pe < 50:
            score = 4.5
        else:
            score = 2.0
    return round(_clamp(score), 1)


def score_growth(fundamentals: dict) -> float:
    rev_growth = fundamentals.get("revenue_growth")
    earn_growth = fundamentals.get("earnings_growth")
    if rev_growth is None and earn_growth is None:
        return 5.0
    vals = [v for v in [rev_growth, earn_growth] if v is not None]
    avg = sum(vals) / len(vals)
    # avg growth of 0% -> 5, 20%+ -> ~9, negative -> pulls down
    score = 5 + (avg * 20)
    return round(_clamp(score), 1)


def score_financial_health(fundamentals: dict, red_flags: list) -> float:
    fails = count_fails(red_flags)
    base = 8.0 - (fails * 2.0)
    roe = fundamentals.get("roe")
    if roe is not None:
        base += (roe - 0.12) * 10  # ROE above 12% nudges score up
    return round(_clamp(base), 1)


def score_momentum(fundamentals: dict) -> float:
    price = fundamentals.get("current_price")
    dma50 = fundamentals.get("fifty_day_avg")
    dma200 = fundamentals.get("two_hundred_day_avg")
    if not all([price, dma50, dma200]):
        return 5.0
    score = 5.0
    if price > dma50:
        score += 1.5
    if price > dma200:
        score += 1.5
    if dma50 > dma200:
        score += 1.0  # golden cross territory
    return round(_clamp(score), 1)


def score_sector_tailwind(peer_avg_return_6m: float = None) -> float:
    """Placeholder — richer version would pull sector news sentiment (see roadmap)."""
    if peer_avg_return_6m is None:
        return 5.0
    score = 5 + (peer_avg_return_6m * 10)
    return round(_clamp(score), 1)


def composite_score(fundamentals: dict, red_flags: list,
                     peer_pe_median: float = None,
                     peer_avg_return_6m: float = None) -> dict:
    sub_scores = {
        "valuation": score_valuation(fundamentals, peer_pe_median),
        "growth": score_growth(fundamentals),
        "financial_health": score_financial_health(fundamentals, red_flags),
        "momentum": score_momentum(fundamentals),
        "sector_tailwind": score_sector_tailwind(peer_avg_return_6m),
    }

    weighted_total = sum(sub_scores[k] * SCORE_WEIGHTS[k] for k in sub_scores)

    # Red-flag penalty: each FAIL knocks a bit off the final score, floor at 0
    fails = count_fails(red_flags)
    penalty = fails * 0.5
    final_score = round(_clamp(weighted_total - penalty), 1)

    return {
        "sub_scores": sub_scores,
        "weights": SCORE_WEIGHTS,
        "red_flag_penalty": penalty,
        "final_score": final_score,
    }
