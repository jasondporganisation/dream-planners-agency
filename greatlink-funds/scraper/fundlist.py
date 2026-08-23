"""Step 1: fund list, GE category and Fund Centre composite IDs.

Source: the GreatLink funds page on greateasternlife.com (currently redirects
to greatlink-dynamic-portfolios.html). Each fund is an anchor into the ILP
Fund Centre, `ilp-fund-centre.html#/detail?id=<SecId>_<FundCode>`, grouped
under <h3>/<h2> category headings (Global Equity, Regional Equity, ...).
Fund *names* are not reliably in the anchor text, so they are filled in from
the Fund Centre screener later.
"""

from __future__ import annotations

import re
from html import unescape

from .util import PoliteSession

GE_BASE = ("https://www.greateasternlife.com/sg/en/personal-insurance/our-products/"
           "wealth-accumulation/investment-linked-funds/")
FUND_LIST_URL = GE_BASE + "greatlink-funds.html"
FUND_CENTRE_URL = GE_BASE + "ilp-fund-centre.html"

# The six GreatLink categories the tool groups by (as at Aug 2026). Any other
# heading on the page (marketing sections) is ignored for grouping.
CATEGORIES = ["Global Equity", "Regional Equity", "Single Country Equity",
              "Mixed Asset", "Money Markets and Bonds", "Commodities"]

# Completeness check list from the project brief (names without "GreatLink").
EXPECTED_FUNDS = {
    "Global Equity": ["Global Disruptive Innovation", "Global Equity Alpha", "Global Equity",
                      "Global Perspective", "Global Real Estate Securities", "Global Technology",
                      "International Health Care", "Lifestyle Dynamic Portfolio",
                      "Multi-Theme Equity", "Sustainable Global Thematic"],
    "Regional Equity": ["ASEAN Growth", "Asia Dividend Advantage", "Asia High Dividend Equity",
                        "Asia Pacific Equity", "Far East Ex Japan Equities",
                        "Global Emerging Markets Equity", "European Sustainable Equity"],
    "Single Country Equity": ["Singapore Equities", "Lion India", "Lion Japan Growth",
                              "Lion Vietnam", "China Growth"],
    "Mixed Asset": ["Income Focus", "Diversified Growth Portfolio", "Global Supreme",
                    "Lifestyle Balanced Portfolio", "Lifestyle Progressive Portfolio",
                    "Lifestyle Secure Portfolio", "Lifestyle Steady Portfolio",
                    "Lion Asian Balanced", "US Income and Growth", "Dynamic Secure Portfolio",
                    "Dynamic Balanced Portfolio", "Dynamic Growth Portfolio"],
    "Money Markets and Bonds": ["Cash", "Global Bond", "Income Bond", "Multi-Sector Income",
                                "Short Duration Bond"],
    "Commodities": ["Singapore Physical Gold"],
}

_ID_RE = re.compile(r"detail\?id=([A-Z0-9]+)_(F\d+)")
_TOKEN_RE = re.compile(r"<h[1-4][^>]*>(.*?)</h[1-4]>|detail\?id=([A-Z0-9]+_F\d+)", re.S)


def parse_fund_list_html(html: str) -> list[dict]:
    """Return [{fund_id, sec_id, fund_code, category, fundcentre_url, ge_page_url}]
    in page order, de-duplicated by composite id."""
    out, seen, category = [], set(), None
    for heading, composite in _TOKEN_RE.findall(html):
        if heading:
            text = re.sub(r"<[^>]+>", "", unescape(heading)).strip()
            if text in CATEGORIES:
                category = text
            elif text and not composite:
                # A non-category heading ends the fund-list section.
                category = None if text.lower().startswith(("additional", "our featured")) else category
            continue
        if composite in seen:
            continue
        seen.add(composite)
        sec_id, fund_code = composite.split("_", 1)
        out.append({
            "fund_id": composite, "sec_id": sec_id, "fund_code": fund_code,
            "category": category,
            "fundcentre_url": f"{FUND_CENTRE_URL}#/detail?id={composite}",
            "ge_page_url": FUND_LIST_URL,
        })
    return out


def harvest(session: PoliteSession) -> list[dict]:
    res = session.get(FUND_LIST_URL, allow_redirects=True)
    res.raise_for_status()
    return parse_fund_list_html(res.text)


def _norm(name: str) -> str:
    n = re.sub(r"^greatlink\s+", "", name.strip().lower())
    n = re.sub(r"\s*\((dis|acc)\)\s*$", "", n)
    while True:
        n2 = re.sub(r"\s+(fund|portfolio)$", "", n)
        if n2 == n:
            return n
        n = n2


def completeness_report(funds: list[dict]) -> dict:
    """Compare harvested fund names (once filled in) with EXPECTED_FUNDS."""
    expected = {_norm(n): cat for cat, names in EXPECTED_FUNDS.items() for n in names}
    found = {_norm(f["name"]): f for f in funds if f.get("name")}
    missing = sorted(n for n in expected if n not in found)
    unexpected = sorted(n for n in found if n not in expected)
    return {"found": len(funds), "expected": len(expected),
            "missing": missing, "unexpected_kept": unexpected}
