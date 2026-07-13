"""
Config for the Stock Research Terminal.
All thresholds and weights live here so you can tune the agent
without touching the logic anywhere else.
"""

# ---------- Red flag rules (deterministic, no LLM) ----------
# Each rule returns PASS/FAIL based on a hard threshold.
RED_FLAG_RULES = {
    "promoter_pledge_pct": 20,       # FAIL if pledged % of promoter holding > this
    "debt_to_equity_max": 2.0,       # FAIL if D/E > this (non-financial companies)
    "interest_coverage_min": 2.0,    # FAIL if operating profit / interest < this
    "receivables_to_revenue_max": 1.5,   # FAIL if receivables growth outpaces revenue by this multiple
    "promoter_holding_falling_quarters": 3,  # FAIL if promoter holding fell for 3+ consecutive quarters
}

# ---------- Composite score weights (must sum to 1.0) ----------
SCORE_WEIGHTS = {
    "valuation": 0.25,
    "growth": 0.25,
    "financial_health": 0.25,
    "momentum": 0.15,
    "sector_tailwind": 0.10,
}

# ---------- Peer comparison ----------
DEFAULT_PEER_COUNT = 4

# ---------- Cache ----------
CACHE_DIR = "cache"
CACHE_TTL_HOURS = 6   # don't re-hit Yahoo Finance more than once per 6h per ticker

# ---------- History log ----------
HISTORY_FILE = "data/analysis_history.csv"

# ---------- Known NSE sector peer groups (fallback if yfinance sector data is thin) ----------
# You can extend this as we add more sectors.
SECTOR_PEERS = {
    "power": ["ADANIGREEN.NS", "ADANIPOWER.NS", "NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS"],
    "it": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
    "auto": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS"],
    "pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "AUROPHARMA.NS"],
}
