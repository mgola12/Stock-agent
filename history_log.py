"""
Logs every analysis run to a CSV so you can later check:
'did a high score actually predict good forward returns?'
This is the backtesting foundation — the reel's tool had no way to
check if its own verdicts were any good. This one does.
"""

import os
from datetime import datetime

import pandas as pd

from config import HISTORY_FILE

os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)


def log_analysis(ticker: str, final_score: float, price: float, sub_scores: dict, fails: int):
    row = {
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker,
        "price_at_analysis": price,
        "final_score": final_score,
        "valuation": sub_scores.get("valuation"),
        "growth": sub_scores.get("growth"),
        "financial_health": sub_scores.get("financial_health"),
        "momentum": sub_scores.get("momentum"),
        "sector_tailwind": sub_scores.get("sector_tailwind"),
        "red_flag_fails": fails,
    }

    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(HISTORY_FILE, index=False)
    return row


def load_history(ticker: str = None) -> pd.DataFrame:
    if not os.path.exists(HISTORY_FILE):
        return pd.DataFrame()
    df = pd.read_csv(HISTORY_FILE)
    if ticker:
        df = df[df["ticker"] == ticker]
    return df


def backtest_score_accuracy(current_price_lookup) -> pd.DataFrame:
    """
    For each past logged analysis, compare the score given at the time
    to the actual forward return since then (using current_price_lookup,
    a function that takes a ticker and returns today's price).
    This is a simple correlation check: do higher scores -> better returns?
    """
    df = load_history()
    if df.empty:
        return df

    def forward_return(row):
        try:
            now_price = current_price_lookup(row["ticker"])
            if now_price and row["price_at_analysis"]:
                return round((now_price - row["price_at_analysis"]) / row["price_at_analysis"] * 100, 2)
        except Exception:
            return None
        return None

    df["forward_return_pct"] = df.apply(forward_return, axis=1)
    return df
