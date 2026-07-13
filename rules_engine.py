"""
Deterministic red-flag rules engine.
No LLM involved here on purpose — these are hard financial thresholds,
the same way the reel's "SRC: Deterministic rules — no LLM" panel worked.
This makes results reproducible and auditable, not vibes-based.
"""

from config import RED_FLAG_RULES


def check_red_flags(fundamentals: dict) -> list:
    """
    Run all red-flag checks against a fundamentals dict.
    Returns a list of dicts: {rule, status, detail}
    """
    results = []

    # --- Debt/Equity ---
    de = fundamentals.get("debt_to_equity")
    if de is not None:
        de_ratio = de / 100  # yfinance reports as percentage
        status = "FAIL" if de_ratio > RED_FLAG_RULES["debt_to_equity_max"] else "PASS"
        results.append({
            "rule": f"D/E > {RED_FLAG_RULES['debt_to_equity_max']} (non-financials)",
            "status": status,
            "detail": f"Debt/Equity = {de_ratio:.2f}",
        })
    else:
        results.append({
            "rule": f"D/E > {RED_FLAG_RULES['debt_to_equity_max']} (non-financials)",
            "status": "N/A",
            "detail": "Data unavailable from source",
        })

    # --- Interest coverage (approximated via EBITDA / interest if available) ---
    ebitda = fundamentals.get("ebitda")
    total_debt = fundamentals.get("total_debt")
    if ebitda and total_debt and total_debt > 0:
        # rough proxy: assume ~8% average interest rate on debt if no direct interest expense field
        est_interest = total_debt * 0.08
        coverage = ebitda / est_interest if est_interest else None
        if coverage is not None:
            status = "FAIL" if coverage < RED_FLAG_RULES["interest_coverage_min"] else "PASS"
            results.append({
                "rule": f"Interest coverage < {RED_FLAG_RULES['interest_coverage_min']}",
                "status": status,
                "detail": f"Estimated EBITDA/interest coverage ≈ {coverage:.1f}x (estimated, not exact)",
            })
    else:
        results.append({
            "rule": f"Interest coverage < {RED_FLAG_RULES['interest_coverage_min']}",
            "status": "N/A",
            "detail": "Insufficient data to estimate",
        })

    # --- Operating cash flow vs profit margin sanity check ---
    ocf = fundamentals.get("operating_cashflow")
    if ocf is not None:
        status = "FAIL" if ocf < 0 else "PASS"
        results.append({
            "rule": "Negative operating cash flow",
            "status": status,
            "detail": f"Operating cash flow = {ocf:,.0f}",
        })
    else:
        results.append({
            "rule": "Negative operating cash flow",
            "status": "N/A",
            "detail": "Data unavailable",
        })

    # --- Institutional/insider holding sanity check (proxy for promoter holding trend) ---
    insiders = fundamentals.get("held_percent_insiders")
    if insiders is not None:
        status = "PASS" if insiders > 0.1 else "N/A"
        results.append({
            "rule": "Promoter/insider holding falling",
            "status": status,
            "detail": (f"Insider holding = {insiders*100:.1f}% (yfinance proxy; "
                       f"cross-check screener.in for actual promoter pledge/holding trend)"),
        })

    # --- Valuation sanity check ---
    pe = fundamentals.get("pe_ratio")
    if pe is not None:
        status = "FLAG" if pe > 60 else "PASS"
        results.append({
            "rule": "Extreme valuation (P/E > 60)",
            "status": status,
            "detail": f"P/E = {pe:.1f}",
        })

    return results


def count_fails(red_flags: list) -> int:
    return sum(1 for r in red_flags if r["status"] == "FAIL")
