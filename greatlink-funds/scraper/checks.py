"""Sanity checks that stop a refresh before it writes a broken dataset.

A fund "comes back empty" when the sources answered but gave us nothing usable
for it: no name, no bid price, no price date, or not one single trailing
return. A fund is "stale" when its price date lags the dataset's as-at date by
more than STALE_DAYS (GE's price feed has stopped updating that fund, or the
screener served an old record). Either is a reason to stop and look, not to
publish quietly.

Missing *long-period* returns (no 10Y for a 4-year-old fund, no YTD for a fund
launched this year) are normal and are not errors — they are listed in the
refresh report as missing fields instead.
"""

from __future__ import annotations

from datetime import date

STALE_DAYS = 10
MIN_FUNDS = 35   # GE has listed 40 GreatLink funds since 2025; far fewer = page/screener broke
TRAILING = ("ret_1m", "ret_3m", "ret_6m", "ret_ytd", "ret_1y")


def fund_problems(fund: dict, as_at: str | None) -> list[str]:
    """Reasons this fund record is unusable (empty list = fine)."""
    problems = []
    if not fund.get("name"):
        problems.append("no fund name")
    if fund.get("bid_price") is None:
        problems.append("no bid price")
    if not fund.get("price_date"):
        problems.append("no price date")
    returns = fund.get("returns") or {}
    if all(returns.get(k) is None for k in TRAILING):
        problems.append("no returns at all (1M/3M/6M/YTD/1Y all empty)")
    if as_at and fund.get("price_date"):
        try:
            lag = (date.fromisoformat(as_at) - date.fromisoformat(fund["price_date"])).days
        except ValueError:
            problems.append(f"unreadable price date {fund['price_date']!r}")
        else:
            if lag > STALE_DAYS:
                problems.append(f"price date {fund['price_date']} is {lag} days behind {as_at}")
    return problems


def validate_dataset(funds: list[dict], as_at: str | None) -> list[str]:
    """One line per problem across the whole dataset (empty list = fine)."""
    lines = []
    if len(funds) < MIN_FUNDS:
        lines.append(f"only {len(funds)} funds (expected at least {MIN_FUNDS})")
    for f in funds:
        for p in fund_problems(f, as_at):
            lines.append(f"{f.get('name') or f.get('fund_id')}: {p}")
    return lines
