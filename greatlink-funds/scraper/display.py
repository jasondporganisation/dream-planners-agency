"""Display-only annotations added to each fund when the dashboard is built.

Nothing here changes a published figure: it only adds labels the dashboard
shows next to the facts (why a figure is missing, which region the fund's
name says it invests in, why the top-holdings table is empty). The stored
data/funds.json is not modified.
"""

from __future__ import annotations

import re
from datetime import date

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# return field -> years of history the figure needs (None = since start of year)
PERIOD_YEARS = {
    "ret_ytd": None, "ret_1y": 1, "ret_3y_ann": 3, "ret_3y_cum": 3,
    "ret_5y_ann": 5, "ret_5y_cum": 5, "ret_10y_ann": 10, "ret_10y_cum": 10,
    "ret_si_ann": 1,
}

GLOBAL = "Global / multi-region"
# First match wins; matched against the fund name (the fund's stated mandate).
REGION_RULES = [
    (r"emerging markets", "Emerging markets"),
    (r"europe", "Europe"),
    (r"asean|asia|asian|far east", "Asia"),
    (r"china", "China"),
    (r"india", "India"),
    (r"japan", "Japan"),
    (r"vietnam", "Vietnam"),
    (r"singapore equit", "Singapore"),
    (r"\bus\b", "United States"),
]

HOLDINGS_NOTE = ("Top holdings were not published for this fund in the latest Fund Centre "
                 "data. See the official fact sheet for its portfolio.")


def _parse(iso: str | None) -> date | None:
    try:
        return date.fromisoformat(str(iso)[:10]) if iso else None
    except ValueError:
        return None


def launched_label(inception: str | None) -> str:
    d = _parse(inception)
    return f"{MONTHS[d.month - 1]} {d.year}" if d else ""


def years_between(start: date, end: date) -> float:
    return (end - start).days / 365.25


def na_note(fund: dict, key: str, as_at: str | None) -> str | None:
    """Plain-English text for a missing return figure, or None if it is present.

    "n/a, launched Jan 2026" when the fund is too young for the period;
    plain "n/a" when the source simply did not publish it.
    """
    if (fund.get("returns") or {}).get(key) is not None:
        return None
    inc, asat = _parse(fund.get("inception_date")), _parse(as_at)
    if inc and asat and key in PERIOD_YEARS:
        years = PERIOD_YEARS[key]
        too_young = (inc > date(asat.year - 1, 12, 31)) if years is None \
            else years_between(inc, asat) < years
        if too_young:
            return f"n/a, launched {launched_label(fund.get('inception_date'))}"
    return "n/a"


def region_of(fund: dict) -> str:
    """Region the fund's name / mandate points to (for the dashboard filter)."""
    if (fund.get("asset_class") or "").lower().startswith("commod"):
        return GLOBAL
    name = (fund.get("name") or "").lower()
    for pattern, label in REGION_RULES:
        if re.search(pattern, name):
            return label
    return GLOBAL


def annotate(fund: dict, as_at: str | None) -> dict:
    """Return a copy of `fund` with the display-only fields added."""
    out = dict(fund)
    out["region"] = region_of(fund)
    notes = {}
    for key in PERIOD_YEARS:
        n = na_note(fund, key, as_at)
        if n:
            notes[key] = n
    out["na_notes"] = notes
    out["holdings_note"] = None if fund.get("top_holdings") else HOLDINGS_NOTE
    return out
