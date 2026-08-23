"""Step 4: bid/offer prices from the GreatLink fund prices page.

The prices page loads dynamically; like the Fund Centre it calls a JSON
endpoint underneath. Discovery captures anything matching the fund-price
patterns; this module merges bid/offer/price-date into the dataset when the
Fund Centre screener did not already provide them. Its historical-price
lookup (price by date) also lets refresh.py cross-check YTD from 31 Dec
prices — logged to the refresh report, never silently substituted.
"""

from __future__ import annotations

from .util import PoliteSession, parse_asat_date, parse_pct

PRICES_URL = (
    "https://www.greateasternlife.com/sg/en/personal-insurance/our-products/"
    "wealth-accumulation/great-invest-advantage/greatlink-funds-prices.html"
)


def merge_prices(session: PoliteSession, endpoints: dict, funds: list[dict],
                 report_lines: list[str]) -> None:
    """Fill missing bid/offer prices from any price endpoint captured during
    discovery. Mutates funds in place; appends notes to report_lines."""
    price_eps = [e for e in endpoints.get("other", [])
                 if "price" in e["url"].lower()]
    if not price_eps:
        report_lines.append("- Prices: no price endpoint captured during discovery; "
                            "bid/offer taken from the Fund Centre screener only.")
        return
    for ep in price_eps:
        try:
            res = session.get(ep["url"], headers={"Accept": "application/json"})
            if res.status_code != 200:
                continue
            from .fundcentre import largest_object_array
            rows = largest_object_array(res.json())["arr"] or []
        except Exception as err:  # noqa: BLE001
            report_lines.append(f"- Prices endpoint failed ({ep['url']}): {err}")
            continue
        by_name = {}
        for row in rows:
            name = next((row[k] for k in row if "name" in k.lower()), None)
            if name:
                by_name[str(name).lower().strip()] = row
        filled = 0
        for fund in funds:
            row = by_name.get(fund["name"].lower().strip())
            if not row:
                continue
            bid = next((parse_pct(row[k]) for k in row if "bid" in k.lower()), None)
            offer = next((parse_pct(row[k]) for k in row if "offer" in k.lower()), None)
            pdate = next((parse_asat_date(row[k]) for k in row
                          if "date" in k.lower()), None)
            if fund.get("bid_price") is None and bid is not None:
                fund["bid_price"] = bid
                fund.setdefault("sources", {})["bid_price"] = "prices-page"
                filled += 1
            if fund.get("offer_price") is None and offer is not None:
                fund["offer_price"] = offer
            if fund.get("price_date") is None and pdate:
                fund["price_date"] = pdate
        if filled:
            report_lines.append(f"- Prices: filled {filled} funds from {ep['url']}")
