"""Step 1: harvest the GreatLink fund list and Fund Centre IDs.

Source: the fund-list page — each fund links into the ILP Fund Centre with a
Morningstar-style ID, e.g. ilp-fund-centre.html#/detail?id=F00001DUL4_F224.
That page is server-rendered CMS content, so plain requests + regex works.

EXPECTED_FUNDS is the completeness check: ~40 GreatLink funds in six
categories as at August 2026. Fewer found = something is wrong; a fund found
that is not listed here is INCLUDED anyway (new funds launch from time to
time) and flagged in the refresh report.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from .util import PoliteSession

BASE = "https://www.greateasternlife.com"
FUND_LIST_URL = (
    BASE + "/sg/en/personal-insurance/our-products/wealth-accumulation/"
    "investment-linked-funds/greatlink-funds.html"
)
FUND_CENTRE_URL = (
    BASE + "/sg/en/personal-insurance/our-products/wealth-accumulation/"
    "investment-linked-funds/ilp-fund-centre.html"
)

# ~40 GreatLink funds in six categories, as at August 2026 (names without the
# "GreatLink" prefix). Completeness check only — the scrape is the source of truth.
EXPECTED_FUNDS: dict[str, list[str]] = {
    "Global Equity": [
        "Global Disruptive Innovation", "Global Equity Alpha", "Global Equity",
        "Global Perspective", "Global Real Estate Securities", "Global Technology",
        "International Health Care", "Lifestyle Dynamic Portfolio",
        "Multi-Theme Equity", "Sustainable Global Thematic",
    ],
    "Regional Equity": [
        "ASEAN Growth", "Asia Dividend Advantage", "Asia High Dividend Equity",
        "Asia Pacific Equity", "Far East Ex Japan Equities",
        "Global Emerging Markets Equity", "European Sustainable Equity",
    ],
    "Single Country Equity": [
        "Singapore Equities", "Lion India", "Lion Japan Growth", "Lion Vietnam",
        "China Growth",
    ],
    "Mixed Asset": [
        "Income Focus", "Diversified Growth Portfolio", "Global Supreme",
        "Lifestyle Balanced Portfolio", "Lifestyle Progressive Portfolio",
        "Lifestyle Secure Portfolio", "Lifestyle Steady Portfolio",
        "Lion Asian Balanced", "US Income and Growth (Dis)",
        "Dynamic Secure Portfolio", "Dynamic Balanced Portfolio",
        "Dynamic Growth Portfolio",
    ],
    "Money Markets and Bonds": [
        "Cash", "Global Bond", "Income Bond", "Multi-Sector Income",
        "Short Duration Bond",
    ],
    "Commodities": [
        "Singapore Physical Gold",
    ],
}

EXPECTED_COUNT = sum(len(v) for v in EXPECTED_FUNDS.values())  # 40

# Matches links into the Fund Centre carrying a Morningstar-style id, e.g.
#   href=".../ilp-fund-centre.html#/detail?id=F00001DUL4_F224"
_DETAIL_LINK = re.compile(
    r"""href=["']([^"']*ilp-fund-centre\.html#/detail\?id=([A-Za-z0-9_]+))["']""")
_ANCHOR = re.compile(r"<a\b[^>]*>(.*?)</a>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub(" ", text)).strip()


def normalize_name(name: str) -> str:
    """Canonical form for matching scraped names to EXPECTED_FUNDS entries."""
    n = re.sub(r"\s+", " ", name).strip()
    n = re.sub(r"^greatlink\s+", "", n, flags=re.I)
    n = re.sub(r"\s+fund$", "", n, flags=re.I)
    return n.lower()


_EXPECTED_LOOKUP = {
    normalize_name(name): (category, name)
    for category, names in EXPECTED_FUNDS.items()
    for name in names
}


def category_for(name: str) -> str | None:
    hit = _EXPECTED_LOOKUP.get(normalize_name(name))
    return hit[0] if hit else None


def harvest(session: PoliteSession) -> list[dict]:
    """Return [{name, fund_id, category, ge_page_url, fundcentre_url}, ...]."""
    res = session.get(FUND_LIST_URL)
    res.raise_for_status()
    html = res.text

    funds: dict[str, dict] = {}
    # Walk every anchor; keep the ones that link into the Fund Centre detail view.
    for anchor in re.finditer(r"<a\b[^>]*href=[^>]+>.*?</a>", html, re.S | re.I):
        block = anchor.group(0)
        m = _DETAIL_LINK.search(block)
        if not m:
            continue
        fund_id = m.group(2)
        name_m = _ANCHOR.search(block)
        name = _clean(name_m.group(1)) if name_m else ""
        if not name or "greatlink" not in name.lower():
            # The link text may be "View fund" — look for a nearby heading instead.
            start = max(0, anchor.start() - 600)
            context = html[start:anchor.start()]
            heads = re.findall(r"<h\d[^>]*>(.*?)</h\d>", context, re.S | re.I)
            for h in reversed(heads):
                t = _clean(h)
                if "greatlink" in t.lower():
                    name = t
                    break
        if not name:
            continue
        detail_url = urljoin(FUND_LIST_URL, m.group(1))
        funds[fund_id] = {
            "name": name,
            "fund_id": fund_id,
            "category": category_for(name),  # None => new/unlisted fund, kept anyway
            "ge_page_url": FUND_LIST_URL,
            "fundcentre_url": detail_url,
        }
    return list(funds.values())


def completeness_report(found: list[dict]) -> dict:
    """Compare a harvest against EXPECTED_FUNDS."""
    found_names = {normalize_name(f["name"]) for f in found}
    missing = [
        f"GreatLink {name} ({category})"
        for category, names in EXPECTED_FUNDS.items()
        for name in names
        if normalize_name(name) not in found_names
    ]
    unexpected = [f["name"] for f in found if f["category"] is None]
    return {
        "expected": EXPECTED_COUNT,
        "found": len(found),
        "missing": missing,
        "unexpected_kept": unexpected,
    }
