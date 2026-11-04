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
# F11 "Sustainable Global Thematic" was renamed "Global Sustainable Equity"
# (same fund code and SecId) — the list uses the current name.
EXPECTED_FUNDS = {
    "Global Equity": ["Global Disruptive Innovation", "Global Equity Alpha", "Global Equity",
                      "Global Perspective", "Global Real Estate Securities", "Global Technology",
                      "International Health Care", "Lifestyle Dynamic Portfolio",
                      "Multi-Theme Equity", "Global Sustainable Equity"],
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

# Fund Centre deep link: "detail?id=<SecId>_<FundCode>". After decoding (see
# _decode) the id may still not be the first query parameter, and the case of
# the "detail"/"id" words has not been stable across GE page builds.
_TOKEN_RE = re.compile(
    r"<h[1-4][^>]*>(.*?)</h[1-4]>|detail\?(?:[^\"'<>\s]*?&)?id=([A-Za-z0-9]+_[Ff]\d+)",
    re.S | re.I)
_CATEGORY_KEYS = {}   # normalised heading -> canonical category (filled below)


def _heading_key(text: str) -> str:
    """'Money Markets &amp; Bonds', 'GLOBAL\xa0 EQUITY ' -> comparable key."""
    t = unescape(text).replace("\xa0", " ").replace("&", " and ")
    return re.sub(r"\s+", " ", t).strip().lower()


def _decode(html: str) -> str:
    """Undo the encodings GE has served the deep links in. Seen so far:
    a literal "?id=...", the HTML entity "?id&#61;..." (Aug 2026, still served
    Nov 2026). Also tolerated: double-encoded entities ("&amp;#61;") and
    percent-encoding ("?id%3D...", "%23/detail%3Fid%3D..."), which are the
    usual next steps when a CMS re-escapes an href."""
    for _ in range(3):          # entities can be nested (&amp;#61; -> &#61; -> =)
        decoded = unescape(html)
        if decoded == html:
            break
        html = decoded
    return re.sub(r"%(3[dD]|3[fF]|23|26|5[fF])",
                  lambda m: {"3d": "=", "3f": "?", "23": "#", "26": "&", "5f": "_"}[m.group(1).lower()],
                  html)


_CATEGORY_KEYS.update({_heading_key(c): c for c in CATEGORIES})


def parse_fund_list_html(html: str) -> list[dict]:
    """Return [{fund_id, sec_id, fund_code, category, fundcentre_url, ge_page_url}]
    in page order, de-duplicated by composite id."""
    # The page has been observed serving the anchor's query string both as a
    # literal "?id=..." and as the HTML-entity-encoded "?id&#61;...". Decode
    # entities up front so the id= regex matches either form.
    html = _decode(html)
    out, seen, category = [], set(), None
    for heading, composite in _TOKEN_RE.findall(html):
        if heading:
            text = re.sub(r"<[^>]+>", "", heading).strip()
            key = _heading_key(text)
            if key in _CATEGORY_KEYS:
                category = _CATEGORY_KEYS[key]
            elif text and not composite:
                # A non-category heading ends the fund-list section.
                category = None if text.lower().startswith(("additional", "our featured")) else category
            continue
        sec_id, fund_code = composite.split("_", 1)
        sec_id, fund_code = sec_id.upper(), fund_code.upper()
        composite = f"{sec_id}_{fund_code}"
        if composite in seen:
            continue
        seen.add(composite)
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
