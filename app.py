"""
Stock Research Terminal — free, NSE/BSE-focused.

Run locally with:
    streamlit run app.py

Or deploy for free on Streamlit Community Cloud (share.streamlit.io)
to get a public link others can open in any browser.

Requirements (all free):
    pip install yfinance streamlit plotly pandas google-genai
"""

import time

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from data_fetcher import (
    get_fundamentals, get_price_history, get_peers,
    get_peer_comparison, normalize_ticker
)
from rules_engine import check_red_flags, count_fails
from scoring import composite_score
from history_log import log_analysis, load_history
from narrative import generate_narrative, is_configured as gemini_configured

NARRATIVE_COOLDOWN_SECONDS = 15  # per-session cooldown so shared free-tier quota isn't burned by one user

st.set_page_config(page_title="Stock Research Terminal", layout="wide", page_icon="📊")

st.title("📊 Stock Research Terminal")
st.caption("Free • Local • NSE/BSE — Research & education only, not investment advice.")

# ---------------- Sidebar: search ----------------
with st.sidebar:
    st.header("Search")
    ticker_input = st.text_input("NSE Symbol (e.g. RELIANCE, TCS, ADANIPOWER)", value="RELIANCE")
    period = st.selectbox("Price history range", ["1mo", "6mo", "1y", "3y", "5y"], index=2)
    manual_peers = st.text_input("Peer tickers (comma-separated, optional)", value="")
    run_button = st.button("Analyze", type="primary", use_container_width=True)

    st.divider()
    st.caption("Data source: Yahoo Finance via yfinance (free, no API key). "
               "Cross-check promoter pledge/holding data with screener.in — "
               "yfinance doesn't expose NSE promoter filings directly.")

if not run_button and "last_ticker" not in st.session_state:
    st.info("👈 Enter an NSE ticker in the sidebar and click **Analyze** to get started.")
    st.stop()

if run_button:
    st.session_state["last_ticker"] = ticker_input

ticker = st.session_state.get("last_ticker", ticker_input)
norm_ticker = normalize_ticker(ticker)

# ---------------- Fetch data ----------------
with st.spinner(f"Fetching data for {norm_ticker}..."):
    try:
        fundamentals = get_fundamentals(ticker)
        hist = get_price_history(ticker, period=period)
    except Exception as e:
        st.error(f"Couldn't fetch data for {norm_ticker}: {e}")
        st.stop()

if hist.empty:
    st.warning(f"No price history found for {norm_ticker}. Check the ticker symbol.")
    st.stop()

# ---------------- Header ----------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Company", fundamentals["name"])
col2.metric("Current Price", f"₹{fundamentals['current_price']:.2f}" if fundamentals["current_price"] else "N/A")
col3.metric("P/E Ratio", f"{fundamentals['pe_ratio']:.1f}" if fundamentals["pe_ratio"] else "N/A")
col4.metric("Sector", fundamentals["sector"])

st.divider()

# ---------------- Price chart ----------------
st.subheader("Price History")
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=hist.index, open=hist["Open"], high=hist["High"],
    low=hist["Low"], close=hist["Close"], name="Price"
))
if len(hist) >= 50:
    hist["50DMA"] = hist["Close"].rolling(50).mean()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["50DMA"], name="50 DMA", line=dict(color="orange")))
if len(hist) >= 200:
    hist["200DMA"] = hist["Close"].rolling(200).mean()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["200DMA"], name="200 DMA", line=dict(color="yellow")))
fig.update_layout(height=450, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# ---------------- Red flags ----------------
st.subheader("🚩 Red Flag Checks (Deterministic — No LLM)")
red_flags = check_red_flags(fundamentals)
flag_df = pd.DataFrame(red_flags)


def _status_color(val):
    colors = {"FAIL": "background-color: #ffcccc", "PASS": "background-color: #ccffcc",
              "FLAG": "background-color: #fff3cc", "N/A": "background-color: #eeeeee"}
    return colors.get(val, "")


st.dataframe(
    flag_df.style.applymap(_status_color, subset=["status"]),
    use_container_width=True, hide_index=True
)

fails = count_fails(red_flags)
if fails > 0:
    st.warning(f"⚠️ {fails} red flag(s) failed. Review before considering this stock.")

# ---------------- Peer comparison ----------------
st.subheader("Peer Comparison")
if manual_peers.strip():
    peer_list = [normalize_ticker(p) for p in manual_peers.split(",")]
else:
    peer_list = get_peers(ticker, fundamentals.get("sector"))

if peer_list:
    all_tickers = [norm_ticker] + [p for p in peer_list if p != norm_ticker]
    peer_df = get_peer_comparison(all_tickers)
    st.dataframe(peer_df, use_container_width=True, hide_index=True)
    peer_pe_values = peer_df[peer_df["Ticker"] != norm_ticker]["P/E"].dropna()
    peer_pe_median = peer_pe_values.median() if not peer_pe_values.empty else None
else:
    st.caption("No peer group configured for this sector yet — add peer tickers manually in the sidebar.")
    peer_pe_median = None

# ---------------- Composite score ----------------
st.subheader("🎯 Composite Score")
score_result = composite_score(fundamentals, red_flags, peer_pe_median=peer_pe_median)

score_col, breakdown_col = st.columns([1, 2])
with score_col:
    st.metric("Overall Score", f"{score_result['final_score']} / 10")
    if score_result["final_score"] >= 7:
        st.success("Strong across weighted factors")
    elif score_result["final_score"] >= 4.5:
        st.info("Mixed — some strengths, some concerns")
    else:
        st.error("Weak across weighted factors")

with breakdown_col:
    breakdown_df = pd.DataFrame([
        {"Factor": k.replace("_", " ").title(), "Score /10": v,
         "Weight": f"{score_result['weights'][k]*100:.0f}%"}
        for k, v in score_result["sub_scores"].items()
    ])
    st.dataframe(breakdown_df, use_container_width=True, hide_index=True)
    st.caption(f"Red flag penalty applied: -{score_result['red_flag_penalty']}")

# ---------------- AI narrative (optional, Gemini free tier) ----------------
st.subheader("🐂🐻 Bull / Bear Case")
if gemini_configured():
    last_call = st.session_state.get("last_narrative_call", 0)
    seconds_left = NARRATIVE_COOLDOWN_SECONDS - (time.time() - last_call)

    if seconds_left > 0:
        st.button(f"Generate narrative (wait {int(seconds_left)}s)", disabled=True)
    elif st.button("Generate narrative (uses shared Gemini free tier)"):
        st.session_state["last_narrative_call"] = time.time()
        with st.spinner("Asking Gemini..."):
            peer_df_for_prompt = peer_df if peer_list else None
            result = generate_narrative(fundamentals, red_flags, score_result, peer_df_for_prompt)
        if result["success"]:
            st.markdown(result["text"])
        else:
            st.error(result["error"])
else:
    st.info(
        "Narrative generation is off. Set a free Gemini API key as the "
        "`GEMINI_API_KEY` environment variable to enable this "
        "(get one at https://aistudio.google.com/apikey). "
        "Until then, you can always paste this dashboard's numbers into a "
        "Claude chat and ask for the bull/bear case manually — also free."
    )

# ---------------- Log this analysis ----------------
log_analysis(
    ticker=norm_ticker,
    final_score=score_result["final_score"],
    price=fundamentals["current_price"],
    sub_scores=score_result["sub_scores"],
    fails=fails,
)

# ---------------- History / backtest tab ----------------
st.divider()
with st.expander("📜 Analysis History (for this ticker)"):
    hist_df = load_history(norm_ticker)
    if not hist_df.empty:
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.caption("No prior history yet — this is the first analysis logged.")

st.divider()
st.caption(
    "⚠️ Research & education only — not investment advice. "
    "Fundamentals from Yahoo Finance may lag or differ from NSE/BSE official filings; "
    "cross-check promoter holding/pledge data with screener.in before acting on anything here."
)
