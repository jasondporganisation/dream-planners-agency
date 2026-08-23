"""Step 3: official bid/offer prices from greateasternlife.com.

The GreatLink Funds Prices page is filled by
GET https://www.greateasternlife.com/bin/corp-site/fund-prices.json?name=gDaily&mode=daily
-> {"funds": [{"fundName", "fundCode": "07", "fundBidPrice", "fundOfferPrice",
              "fundValueDate": "2026-08-20", "fundPriceStatusDescription", ...}]}
The Fund Centre's LastPrice is the bid price; this endpoint adds the offer price
(single-pricing products ignore it) and the official value date.
"""

from __future__ import annotations

from .util import PoliteSession

PRICES_URL = "https://www.greateasternlife.com/bin/corp-site/fund-prices.json"


def fetch_prices(session: PoliteSession) -> dict[str, dict]:
    """{fund_code (e.g. 'F07'): {bid, offer, date, status, name}}"""
    res = session.get(PRICES_URL, params={"name": "gDaily", "mode": "daily"},
                      headers={"Referer": "https://www.greateasternlife.com/"})
    res.raise_for_status()
    out = {}
    for row in res.json().get("funds", []):
        code = str(row.get("fundCode") or "").strip()
        if not code:
            continue
        code = "F" + code.lstrip("F")
        out[code] = {
            "bid": _f(row.get("fundBidPrice")), "offer": _f(row.get("fundOfferPrice")),
            "date": row.get("fundValueDate") or None,
            "status": row.get("fundPriceStatusDescription") or None,
            "name": row.get("fundName"), "cpf_approved": row.get("fundCPFApproved") == "Y",
        }
    return out


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
