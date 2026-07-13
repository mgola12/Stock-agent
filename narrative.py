"""
Narrative generation using Gemini's free tier.

Reads the API key from TWO possible places, in this order:
    1. Streamlit secrets (used when deployed on Streamlit Community Cloud —
       set via the app's Settings > Secrets panel, never committed to GitHub)
    2. GEMINI_API_KEY environment variable (used when running locally)

This module never hardcodes the key and never raises if it's missing —
it just disables the narrative feature so the rest of the dashboard
(red flags, scoring, peer comparison) always keeps working.
"""

import os

import streamlit as st
from google import genai

MODEL_NAME = "gemini-2.0-flash"  # free-tier eligible as of this writing


def _get_api_key():
    # Streamlit Cloud: key lives in st.secrets, set via the app dashboard
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass  # no secrets.toml present (e.g. running locally) — that's fine

    # Local dev: key lives in an environment variable
    return os.environ.get("GEMINI_API_KEY")


def _get_client():
    api_key = _get_api_key()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def is_configured() -> bool:
    return bool(_get_api_key())


def _build_prompt(fundamentals: dict, red_flags: list, score_result: dict, peer_df=None) -> str:
    flag_lines = "\n".join(
        f"- {f['rule']}: {f['status']} ({f['detail']})" for f in red_flags
    )
    peer_summary = ""
    if peer_df is not None and not peer_df.empty:
        peer_summary = "\nPeer comparison:\n" + peer_df.to_string(index=False)

    prompt = f"""You are a careful equity research assistant. Analyze the following data
for {fundamentals.get('name')} ({fundamentals.get('ticker')}) and produce a SWOT-style
bull/bear case. Use ONLY the numbers given below — do not invent figures or cite sources
you weren't given. Be direct about weaknesses; do not soften red flags.

FUNDAMENTALS:
- Sector: {fundamentals.get('sector')}
- P/E: {fundamentals.get('pe_ratio')}
- ROE: {fundamentals.get('roe')}
- Debt/Equity (as %): {fundamentals.get('debt_to_equity')}
- Revenue growth: {fundamentals.get('revenue_growth')}
- Earnings growth: {fundamentals.get('earnings_growth')}
- Current price: {fundamentals.get('current_price')}
- 50-day avg: {fundamentals.get('fifty_day_avg')}
- 200-day avg: {fundamentals.get('two_hundred_day_avg')}

RED FLAG CHECKS (deterministic, already computed):
{flag_lines}

COMPOSITE SCORE: {score_result['final_score']}/10
Sub-scores: {score_result['sub_scores']}
{peer_summary}

Write:
1. BULL CASE (2-3 concise bullet points, grounded only in the data above)
2. BEAR CASE (2-3 concise bullet points, grounded only in the data above)
3. ONE-LINE VERDICT (a single plain-English sentence, no recommendation to buy/sell,
   just a summary characterization)

Keep the whole response under 200 words. This is for research/education only,
not investment advice — do not phrase anything as a recommendation to buy or sell."""
    return prompt


def generate_narrative(fundamentals: dict, red_flags: list, score_result: dict, peer_df=None) -> dict:
    """
    Returns {"success": bool, "text": str, "error": str or None}
    Never raises — designed to fail gracefully so the rest of the dashboard
    still works if Gemini is unavailable, rate-limited, or not configured.
    """
    client = _get_client()
    if client is None:
        return {
            "success": False,
            "text": None,
            "error": "Gemini API key not configured. If running locally, set GEMINI_API_KEY. If deployed, set it in the app's Secrets panel.",
        }

    prompt = _build_prompt(fundamentals, red_flags, score_result, peer_df)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        return {"success": True, "text": response.text, "error": None}
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            friendly = "Gemini free-tier rate limit hit — wait a minute and try again."
        else:
            friendly = f"Gemini API error: {err_str}"
        return {"success": False, "text": None, "error": friendly}
