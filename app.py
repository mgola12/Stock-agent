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
    get_peer_comparison, get_peer_normalized_returns, normalize_ticker
)
from rules_engine import check_red_flags, count_fails
from scoring import composite_score
from history_log import log_analysis, load_history
from narrative import generate_narrative, is_configured as gemini_configured
import styles as S

NARRATIVE_COOLDOWN_SECONDS = 15  # per-session cooldown so shared free-tier quota isn't burned by one user

st.set_page_config(page_title="Stock Research Terminal", layout="wide", page_icon="📊")
S.inject_css()

st.markdown(f"""
<div style="display:flex; align-items:baseline; gap:14px; margin-bottom:2px;">
    <span style="font-size:1.7rem; font-weight:700; color:{S.TEXT}; letter-spacing:0.02em;">
        📊 STOCK RESEARCH TERMINAL
    </span>
    <span style="color:{S.TEAL}; font-size:0.75rem; letter-spacing:0.1em;">● LIVE</span>
</div>
<div style="color:{S.MUTED}; font-size:0.8rem; margin-bottom:18px;">
    FREE · NSE/BSE · Research &amp; education only — not investment advice
</div>
""", unsafe_allow_html=True)

# ---------------- Sidebar: search ----------------
with st.sidebar:
    st.markdown(f"<span style='color:{S.TEAL}; font-weight:700; letter-spacing:0.08em;'>▸ SEARCH</span>", unsafe_allow_html=True)
    ticker_input = st.text_input("NSE Symbol (e.g. RELIANCE, TCS, ADANIPOWER)", value="RELIANCE")
    period = st.selectbox("Price history range", ["1mo", "6mo", "1y", "3y", "5y"], index=2)
    manual_peers = st.text_input("Peer tickers (comma-separated, optional)", value="")
    run_button = st.button("ANALYZE", type="primary", use_container_width=True)

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

# ---------------- Ticker banner ----------------
S.ticker_banner(fundamentals)

col1, col2, col3, col4 = st.columns(4)
col1.metric("P/E Ratio", f"{fundamentals['pe_ratio']:.1f}" if fundamentals["pe_ratio"] else "N/A")
col2.metric("ROE", f"{fundamentals['roe']*100:.1f}%" if fundamentals["roe"] else "N/A")
col3.metric("52W High", f"₹{fundamentals['fifty_two_week_high']:.0f}" if fundamentals["fifty_two_week_high"] else "N/A")
col4.metric("52W Low", f"₹{fundamentals['fifty_two_week_low']:.0f}" if fundamentals["fifty_two_week_low"] else "N/A")

# ---------------- Price chart ----------------
S.section_header("Price History", f"{period.upper()} · 50/200 DMA")
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=hist.index, open=hist["Open"], high=hist["High"],
    low=hist["Low"], close=hist["Close"], name="Price",
    increasing_line_color=S.GREEN, decreasing_line_color=S.RED,
))
if len(hist) >= 50:
    hist["50DMA"] = hist["Close"].rolling(50).mean()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["50DMA"], name="50 DMA", line=dict(color=S.AMBER, width=1.4)))
if len(hist) >= 200:
    hist["200DMA"] = hist["Close"].rolling(200).mean()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["200DMA"], name="200 DMA", line=dict(color=S.TEAL, width=1.4)))
fig.update_layout(
    height=440, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=S.PANEL,
    font=dict(color=S.TEXT, family="JetBrains Mono", size=11),
    legend=dict(orientation="h", y=1.05, bgcolor="rgba(0,0,0,0)"),
    xaxis=dict(gridcolor=S.BORDER), yaxis=dict(gridcolor=S.BORDER),
)
st.plotly_chart(fig, use_container_width=True)

# ---------------- Red flags ----------------
S.section_header("Red Flag Checks", "Deterministic · No LLM")
red_flags = check_red_flags(fundamentals)
S.render_flag_rows(red_flags)

fails = count_fails(red_flags)
if fails > 0:
    st.warning(f"⚠️ {fails} red flag(s) failed. Review before considering this stock.")

# ---------------- Peer comparison ----------------
S.section_header("Peer Comparison", "Same sector · top by relevance")
if manual_peers.strip():
    peer_list = [normalize_ticker(p) for p in manual_peers.split(",")]
else:
    peer_list = get_peers(ticker, fundamentals.get("sector"))

if peer_list:
    all_tickers = [norm_ticker] + [p for p in peer_list if p != norm_ticker]
    peer_df = get_peer_comparison(all_tickers)

    # Normalized performance overlay chart
    returns_df = get_peer_normalized_returns(all_tickers, period=period)
    if not returns_df.empty:
        perf_fig = go.Figure()
        palette = [S.TEAL, S.AMBER, S.GREEN, S.RED, S.YELLOW]
        for i, col in enumerate(returns_df.columns):
            perf_fig.add_trace(go.Scatter(
                x=returns_df.index, y=returns_df[col], name=col,
                line=dict(width=2.2 if col == norm_ticker else 1.3,
                          color=palette[i % len(palette)]),
            ))
        perf_fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=S.PANEL,
            font=dict(color=S.TEXT, family="JetBrains Mono", size=11),
            yaxis=dict(title="% return", gridcolor=S.BORDER, ticksuffix="%"),
            xaxis=dict(gridcolor=S.BORDER),
            legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(perf_fig, use_container_width=True)

    st.dataframe(peer_df, use_container_width=True, hide_index=True)
    peer_pe_values = peer_df[peer_df["Ticker"] != norm_ticker]["P/E"].dropna()
    peer_pe_median = peer_pe_values.median() if not peer_pe_values.empty else None
else:
    st.caption("No peer group configured for this sector yet — add peer tickers manually in the sidebar.")
    peer_pe_median = None

# ---------------- Composite score ----------------
S.section_header("Verdict — Analysis Score")
score_result = composite_score(fundamentals, red_flags, peer_pe_median=peer_pe_median)

gauge_col, bars_col = st.columns([1, 1.6])
with gauge_col:
    st.plotly_chart(S.score_gauge(score_result["final_score"]), use_container_width=True)
    if score_result["final_score"] >= 7:
        st.success("Strong across weighted factors")
    elif score_result["final_score"] >= 4.5:
        st.info("Mixed — some strengths, some concerns")
    else:
        st.error("Weak across weighted factors")
    st.caption(f"Red flag penalty applied: −{score_result['red_flag_penalty']}")

with bars_col:
    st.plotly_chart(
        S.factor_bars(score_result["sub_scores"], score_result["weights"]),
        use_container_width=True
    )

# ---------------- AI narrative (optional, Gemini free tier) ----------------
S.section_header("Bull / Bear Case", "Gemini · on-demand")
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
        st.session_state["last_narrative_result"] = result

    result = st.session_state.get("last_narrative_result")
    if result:
        if result["success"]:
            sec = result["sections"]
            if sec and (sec["bull"] or sec["bear"]):
                bull_col, bear_col = st.columns(2)
                with bull_col:
                    bullets = "".join(f"<li>{b}</li>" for b in sec["bull"])
                    st.markdown(f"""
                    <div class="case-card bull">
                        <div class="case-title">🐂 Bull Case</div>
                        <ul>{bullets}</ul>
                    </div>
                    """, unsafe_allow_html=True)
                with bear_col:
                    bullets = "".join(f"<li>{b}</li>" for b in sec["bear"])
                    st.markdown(f"""
                    <div class="case-card bear">
                        <div class="case-title">🐻 Bear Case</div>
                        <ul>{bullets}</ul>
                    </div>
                    """, unsafe_allow_html=True)
                if sec["verdict"]:
                    st.markdown(f"""
                    <div class="verdict-line">
                        <span class="lbl">ONE-LINE VERDICT</span>
                        {sec['verdict']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Parsing didn't find the expected markers — fall back to raw text
                st.markdown(result["text"])
        else:
            st.error(result["error"])
else:
    st.info(
        "Narrative generation is off. Set a free Gemini API key as the "
        "`GEMINI_API_KEY` environment variable (local) or in the app's Secrets "
        "panel (deployed) to enable this — get one at https://aistudio.google.com/apikey. "
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
with st.expander("📜 Analysis History (for this ticker)"):
    hist_df = load_history(norm_ticker)
    if not hist_df.empty:
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.caption("No prior history yet — this is the first analysis logged.")

st.markdown(f"""
<div style="color:{S.MUTED}; font-size:0.72rem; margin-top:24px; padding-top:12px; border-top:1px solid {S.BORDER};">
⚠ Research &amp; education only — not investment advice. Fundamentals from Yahoo Finance may lag or differ
from NSE/BSE official filings; cross-check promoter holding/pledge data with screener.in before acting on anything here.
</div>
""", unsafe_allow_html=True)
