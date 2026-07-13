"""
Visual layer for the Stock Research Terminal.
Dark, monospace, terminal-style aesthetic — teal signature accent for the
'live system' feel, amber for attention, green/red for pass/fail.
Kept in one file so the look can be tuned without touching app logic.
"""

import plotly.graph_objects as go
import streamlit as st

# ---------------- Color tokens ----------------
BG = "#0A0E14"
PANEL = "#11161F"
BORDER = "#1F2733"
TEXT = "#E5E9F0"
MUTED = "#6B7684"
TEAL = "#2DD4BF"
AMBER = "#F5A623"
GREEN = "#4ADE80"
RED = "#F87171"
YELLOW = "#FBBF24"

STATUS_COLORS = {
    "PASS": GREEN,
    "FAIL": RED,
    "FLAG": YELLOW,
    "N/A": MUTED,
}


def inject_css():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"], .stMarkdown, .stText, p, span, div, label {{
            font-family: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace !important;
        }}

        /* ---------- Base app + grid backdrop ---------- */
        .stApp {{
            background:
                repeating-linear-gradient(0deg, rgba(45,212,191,0.035) 0px, rgba(45,212,191,0.035) 1px, transparent 1px, transparent 40px),
                repeating-linear-gradient(90deg, rgba(45,212,191,0.035) 0px, rgba(45,212,191,0.035) 1px, transparent 1px, transparent 40px),
                {BG};
        }}
        .block-container {{
            padding-top: 1.6rem !important;
        }}

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {{
            background: {PANEL};
            border-right: 1px solid {BORDER};
        }}
        section[data-testid="stSidebar"] label {{
            color: {MUTED} !important;
            font-size: 0.72rem !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }}

        /* ---------- Text inputs & selectboxes ---------- */
        [data-testid="stTextInput"] input,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
            background: {BG} !important;
            border: 1px solid {BORDER} !important;
            color: {TEXT} !important;
            border-radius: 3px !important;
        }}
        [data-testid="stTextInput"] input:focus,
        [data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within > div {{
            border-color: {TEAL} !important;
            box-shadow: 0 0 0 1px {TEAL} !important;
        }}
        [data-baseweb="popover"] {{
            font-family: 'JetBrains Mono', monospace !important;
        }}
        ul[data-testid="stSelectboxVirtualDropdown"] {{
            background: {PANEL} !important;
        }}

        /* ---------- Buttons ---------- */
        .stButton button, button[kind="primary"], button[kind="secondary"] {{
            background: {BG} !important;
            border: 1px solid {TEAL} !important;
            color: {TEAL} !important;
            border-radius: 3px !important;
            font-weight: 700 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            font-size: 0.78rem !important;
            transition: all 0.15s ease;
        }}
        .stButton button:hover {{
            background: {TEAL} !important;
            color: {BG} !important;
            box-shadow: 0 0 16px rgba(45,212,191,0.5);
        }}
        .stButton button:disabled {{
            border-color: {BORDER} !important;
            color: {MUTED} !important;
            background: {PANEL} !important;
        }}

        /* ---------- Metrics ---------- */
        [data-testid="stMetric"] {{
            background: {PANEL};
            border: 1px solid {BORDER};
            border-radius: 4px;
            padding: 12px 16px;
        }}
        [data-testid="stMetricLabel"] {{
            color: {MUTED} !important;
            font-size: 0.68rem !important;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        [data-testid="stMetricValue"] {{
            color: {TEAL} !important;
            font-size: 1.3rem !important;
            font-weight: 700 !important;
        }}

        /* ---------- Dataframes ---------- */
        [data-testid="stDataFrame"] {{
            border: 1px solid {BORDER};
            border-radius: 4px;
        }}

        /* ---------- Expander ---------- */
        [data-testid="stExpander"] {{
            background: {PANEL};
            border: 1px solid {BORDER} !important;
            border-radius: 4px;
        }}
        [data-testid="stExpander"] summary {{
            color: {TEXT} !important;
            font-size: 0.82rem;
        }}

        /* ---------- Native alerts (fallback styling if used) ---------- */
        [data-testid="stAlertContainer"], [data-testid="stAlert"], .stAlert {{
            background: {PANEL} !important;
            border-radius: 4px !important;
            font-size: 0.85rem !important;
        }}

        /* ---------- Custom alert boxes (used instead of st.success/info/error) ---------- */
        .term-alert {{
            border-radius: 4px;
            padding: 12px 18px;
            font-size: 0.85rem;
            margin: 6px 0 14px 0;
            border-left: 3px solid var(--alert-color, {MUTED});
            background: {PANEL};
            color: {TEXT};
        }}

        /* Terminal-style section header */
        .term-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 28px 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid {BORDER};
        }}
        .term-header .arrow {{
            color: {TEAL};
            font-size: 0.9rem;
            text-shadow: 0 0 8px rgba(45,212,191,0.6);
        }}
        .term-header .label {{
            color: {TEXT};
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .term-header .tag {{
            margin-left: auto;
            color: {MUTED};
            font-size: 0.7rem;
            letter-spacing: 0.05em;
        }}

        /* Ticker banner */
        .ticker-banner {{
            background: {PANEL};
            border: 1px solid {BORDER};
            border-left: 3px solid {TEAL};
            border-radius: 4px;
            padding: 18px 22px;
            margin-bottom: 16px;
        }}
        .ticker-name {{
            color: {TEXT};
            font-size: 1.4rem;
            font-weight: 700;
        }}
        .ticker-sub {{
            color: {MUTED};
            font-size: 0.78rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-top: 2px;
        }}

        /* Red flag rows */
        .flag-row {{
            display: flex;
            align-items: center;
            gap: 14px;
            background: {PANEL};
            border-left: 3px solid var(--flag-color, {MUTED});
            border-radius: 3px;
            padding: 10px 16px;
            margin-bottom: 6px;
        }}
        .flag-status {{
            font-weight: 700;
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            width: 52px;
            flex-shrink: 0;
            color: var(--flag-color, {MUTED});
        }}
        .flag-rule {{
            color: {TEXT};
            font-size: 0.85rem;
            flex-shrink: 0;
            min-width: 260px;
        }}
        .flag-detail {{
            color: {MUTED};
            font-size: 0.78rem;
        }}

        /* Bull/Bear cards */
        .case-card {{
            background: {PANEL};
            border-radius: 4px;
            padding: 18px 20px;
            height: 100%;
        }}
        .case-card.bull {{ border-top: 3px solid {GREEN}; }}
        .case-card.bear {{ border-top: 3px solid {RED}; }}
        .case-title {{
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        .case-card.bull .case-title {{ color: {GREEN}; }}
        .case-card.bear .case-title {{ color: {RED}; }}
        .case-card ul {{
            margin: 0;
            padding-left: 18px;
            color: {TEXT};
            font-size: 0.85rem;
            line-height: 1.6;
        }}
        .verdict-line {{
            background: {PANEL};
            border: 1px dashed {BORDER};
            border-radius: 4px;
            padding: 12px 18px;
            color: {TEXT};
            font-size: 0.85rem;
            margin-top: 12px;
        }}
        .verdict-line .lbl {{
            color: {TEAL};
            font-weight: 700;
            letter-spacing: 0.08em;
            font-size: 0.7rem;
            display: block;
            margin-bottom: 4px;
        }}

        .src-tag {{
            color: {MUTED};
            font-size: 0.68rem;
            letter-spacing: 0.05em;
            margin-top: 2px;
        }}

        /* Sidebar source note */
        .sidebar-note {{
            border: 1px solid {BORDER};
            border-radius: 4px;
            padding: 10px 12px;
            margin-top: 10px;
        }}
        .sidebar-note .lbl {{
            color: {TEAL};
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            display: block;
            margin-bottom: 4px;
        }}
        .sidebar-note .body {{
            color: {MUTED};
            font-size: 0.7rem;
            line-height: 1.5;
        }}
    </style>
    """, unsafe_allow_html=True)


def styled_alert(message: str, kind: str = "info"):
    """Custom-rendered alert box (replaces st.success/info/warning/error) so the
    look stays consistent with the terminal theme instead of Streamlit's defaults."""
    colors = {"success": GREEN, "info": TEAL, "warning": AMBER, "error": RED}
    color = colors.get(kind, TEAL)
    st.markdown(f"""
    <div class="term-alert" style="--alert-color:{color}; color:{color};">
        {message}
    </div>
    """, unsafe_allow_html=True)


def sidebar_note(label: str, body: str):
    st.markdown(f"""
    <div class="sidebar-note">
        <span class="lbl">▸ {label}</span>
        <span class="body">{body}</span>
    </div>
    """, unsafe_allow_html=True)


def section_header(label: str, tag: str = ""):
    st.markdown(f"""
    <div class="term-header">
        <span class="arrow">▸</span>
        <span class="label">{label}</span>
        <span class="tag">{tag}</span>
    </div>
    """, unsafe_allow_html=True)


def ticker_banner(fundamentals: dict):
    price = fundamentals.get("current_price")
    price_str = f"₹{price:,.2f}" if price else "N/A"
    st.markdown(f"""
    <div class="ticker-banner">
        <div class="ticker-name">{fundamentals.get('name', '—')} <span style="color:{MUTED}; font-weight:400; font-size:1rem;">({fundamentals.get('ticker','')})</span></div>
        <div class="ticker-sub">{fundamentals.get('sector','Unknown')} · {fundamentals.get('industry','')} · {price_str}</div>
    </div>
    """, unsafe_allow_html=True)


def render_flag_rows(red_flags: list):
    rows_html = ""
    for f in red_flags:
        color = STATUS_COLORS.get(f["status"], MUTED)
        rows_html += f"""
        <div class="flag-row" style="--flag-color:{color}">
            <span class="flag-status">{f['status']}</span>
            <span class="flag-rule">{f['rule']}</span>
            <span class="flag-detail">{f['detail']}</span>
        </div>
        """
    st.markdown(rows_html, unsafe_allow_html=True)


def score_gauge(score: float, title: str = "ANALYSIS SCORE"):
    """Circular gauge mirroring the reel's '5.3/10' ring — teal arc on dark panel."""
    if score >= 7:
        arc_color = GREEN
    elif score >= 4.5:
        arc_color = TEAL
    else:
        arc_color = RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": " / 10", "font": {"size": 40, "color": TEXT, "family": "JetBrains Mono"}},
        gauge={
            "axis": {"range": [0, 10], "tickcolor": MUTED, "tickfont": {"color": MUTED, "size": 10}},
            "bar": {"color": arc_color, "thickness": 0.28},
            "bgcolor": PANEL,
            "borderwidth": 0,
            "steps": [
                {"range": [0, 4.5], "color": "rgba(248,113,113,0.08)"},
                {"range": [4.5, 7], "color": "rgba(45,212,191,0.08)"},
                {"range": [7, 10], "color": "rgba(74,222,128,0.08)"},
            ],
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(
        height=240,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT},
    )
    return fig


def factor_bars(sub_scores: dict, weights: dict):
    """Horizontal weighted-factor bars, styled like the reel's Valuation/Growth/... breakdown."""
    labels = [k.replace("_", " ").title() for k in sub_scores]
    values = list(sub_scores.values())
    weight_labels = [f"{weights[k]*100:.0f}%" for k in sub_scores]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color=TEAL, line=dict(width=0)),
        text=[f"{v}/10 · wt {w}" for v, w in zip(values, weight_labels)],
        textposition="outside",
        textfont=dict(color=MUTED, size=11),
    ))
    fig.update_layout(
        height=230,
        margin=dict(l=10, r=60, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0, 10], showgrid=False, visible=False),
        yaxis=dict(color=TEXT, autorange="reversed"),
        font=dict(color=TEXT, family="JetBrains Mono", size=12),
    )
    return fig
