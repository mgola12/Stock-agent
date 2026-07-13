"""
Data fetcher for the Stock Research Terminal.
Pulls price history + fundamentals from Yahoo Finance (via yfinance) — free, no API key.
Caches results locally so repeated runs don't hammer the API or blow past rate limits.
"""

import json
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config import CACHE_DIR, CACHE_TTL_HOURS, SECTOR_PEERS

os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(ticker: str, kind: str) -> str:
    safe = ticker.replace(".", "_").replace("&", "and")
    return os.path.join(CACHE_DIR, f"{safe}_{kind}.json")


def _is_cache_fresh(path: str) -> bool:
    if not os.path.exists(path):
        return False
    age_hours = (time.time() - os.path.getmtime(path)) / 3600
    return age_hours < CACHE_TTL_HOURS


def normalize_ticker(ticker: str) -> str:
    """Add .NS suffix if user just typed the bare NSE symbol."""
    ticker = ticker.strip().upper()
    if not ticker.endswith((".NS", ".BO")):
        ticker = f"{ticker}.NS"
    return ticker


def get_fundamentals(ticker: str, force_refresh: bool = False) -> dict:
    """Fetch key fundamentals for a ticker, with caching."""
    ticker = normalize_ticker(ticker)
    cache_file = _cache_path(ticker, "fundamentals")

    if not force_refresh and _is_cache_fresh(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)

    t = yf.Ticker(ticker)
    info = t.info

    fundamentals = {
        "ticker": ticker,
        "name": info.get("longName", ticker),
        "sector": info.get("sector", "Unknown"),
        "industry": info.get("industry", "Unknown"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "debt_to_equity": info.get("debtToEquity"),  # yfinance reports as % (e.g. 519 = 5.19x)
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "profit_margin": info.get("profitMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "fifty_day_avg": info.get("fiftyDayAverage"),
        "two_hundred_day_avg": info.get("twoHundredDayAverage"),
        "dividend_yield": info.get("dividendYield"),
        "held_percent_insiders": info.get("heldPercentInsiders"),
        "held_percent_institutions": info.get("heldPercentInstitutions"),
        "beta": info.get("beta"),
        "free_cashflow": info.get("freeCashflow"),
        "operating_cashflow": info.get("operatingCashflow"),
        "total_debt": info.get("totalDebt"),
        "total_cash": info.get("totalCash"),
        "ebitda": info.get("ebitda"),
        "fetched_at": datetime.now().isoformat(),
    }

    with open(cache_file, "w") as f:
        json.dump(fundamentals, f, indent=2)

    return fundamentals


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Fetch OHLCV price history. period: 1mo, 6mo, 1y, 3y, 5y"""
    ticker = normalize_ticker(ticker)
    t = yf.Ticker(ticker)
    hist = t.history(period=period)
    return hist


def get_quarterly_holdings_trend(ticker: str) -> list:
    """
    yfinance doesn't give NSE promoter-holding history directly.
    This is a placeholder that returns institutional ownership as a proxy.
    For real promoter pledge/holding data, screener.in or NSE's own filings
    are the authoritative source (see 'Known limitations' in README).
    """
    ticker = normalize_ticker(ticker)
    t = yf.Ticker(ticker)
    try:
        holders = t.major_holders
        return holders.to_dict() if holders is not None else {}
    except Exception:
        return {}


def get_peers(ticker: str, sector: str = None) -> list:
    """Return a small peer list for comparison, using sector map fallback."""
    ticker = normalize_ticker(ticker)
    if sector:
        sector_key = sector.lower()
        for key, peers in SECTOR_PEERS.items():
            if key in sector_key:
                return [p for p in peers if p != ticker][:4]
    # No match — return empty, UI will let user pick manually
    return []


def get_peer_comparison(tickers: list) -> pd.DataFrame:
    """Build a comparison table of key ratios across a list of tickers."""
    rows = []
    for tk in tickers:
        try:
            f = get_fundamentals(tk)
            rows.append({
                "Ticker": f["ticker"],
                "Name": f["name"],
                "P/E": f["pe_ratio"],
                "ROE %": round(f["roe"] * 100, 1) if f["roe"] else None,
                "D/E": round(f["debt_to_equity"] / 100, 2) if f["debt_to_equity"] else None,
                "Rev Growth %": round(f["revenue_growth"] * 100, 1) if f["revenue_growth"] else None,
                "Market Cap (Cr)": round(f["market_cap"] / 1e7, 0) if f["market_cap"] else None,
            })
        except Exception as e:
            rows.append({"Ticker": tk, "Name": f"Error: {e}"})
    return pd.DataFrame(rows)


def get_peer_normalized_returns(tickers: list, period: str = "6mo") -> pd.DataFrame:
    """
    Fetch price history for each ticker and normalize to % return from the
    start of the period, so multiple stocks can be overlaid on one chart
    regardless of their absolute price level (mirrors the reel's peer overlay).
    """
    series = {}
    for tk in tickers:
        try:
            hist = get_price_history(tk, period=period)
            if hist.empty:
                continue
            closes = hist["Close"]
            normalized = (closes / closes.iloc[0] - 1) * 100
            series[tk] = normalized
        except Exception:
            continue
    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series)
