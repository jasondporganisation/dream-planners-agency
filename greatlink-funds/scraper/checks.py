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


# ---------------------------------------------------------------------------
# Data-sanity checks written into data/refresh_report.md.
#
# The Monday auto-merge job reads the report, so these only ever add ordinary
# "- ..." lines: problems go under "## Failures / notes" (which then is no
# longer "- none", so the PR waits for a person), and big price moves are
# written as "- DISCREPANCY ..." lines (counted by the merge job). They never
# change the report's layout.
# ---------------------------------------------------------------------------

EXPECTED_FUND_COUNT = 40     # GreatLink funds listed by GE since 2025
MAX_DATA_AGE_DAYS = 10       # price date may lag "today" (SGT) by at most this
MAX_WEEKLY_MOVE_PCT = 15.0   # bid move vs the previous dataset flagged above this


def _age_days(iso: str | None, today: date) -> int | None:
    try:
        return (today - date.fromisoformat(iso)).days if iso else None
    except ValueError:
        return None


def sanity_failures(funds: list[dict], as_at: str | None, today: date,
                    expected_count: int = EXPECTED_FUND_COUNT) -> list[str]:
    """Report lines ("- ...") for the Failures / notes section. Empty = clean."""
    lines = []
    if len(funds) != expected_count:
        lines.append(f"- FUND COUNT: {len(funds)} funds in this refresh (expected {expected_count})")
    for key, label in (("fund_code", "fund code"), ("fund_id", "fund ID")):
        seen: dict[str, list[str]] = {}
        for f in funds:
            if f.get(key):
                seen.setdefault(f[key], []).append(f.get("name") or f[key])
        for value, names in seen.items():
            if len(names) > 1:
                lines.append(f"- DUPLICATE {label} {value}: {', '.join(names)}")
    for f in funds:
        bid = f.get("bid_price")
        if bid is not None and not bid > 0:
            lines.append(f"- BAD PRICE {f.get('name') or f.get('fund_id')}: bid price {bid} is not above zero")
        offer = f.get("offer_price")
        if offer is not None and not offer > 0:
            lines.append(f"- BAD PRICE {f.get('name') or f.get('fund_id')}: offer price {offer} is not above zero")
    age = _age_days(as_at, today)
    if age is None:
        lines.append(f"- STALE DATA: dataset date {as_at!r} is missing or unreadable")
    elif age > MAX_DATA_AGE_DAYS:
        lines.append(f"- STALE DATA: prices as at {as_at} are {age} days old on {today.isoformat()} "
                     f"(limit {MAX_DATA_AGE_DAYS})")
    else:
        for f in funds:
            fage = _age_days(f.get("price_date"), today)
            if fage is not None and fage > MAX_DATA_AGE_DAYS:
                lines.append(f"- STALE PRICE {f.get('name')}: price date {f['price_date']} is {fage} "
                             f"days old on {today.isoformat()} (limit {MAX_DATA_AGE_DAYS})")
    return lines


def weekly_move_discrepancies(funds: list[dict], previous: list[dict] | None,
                              limit_pct: float = MAX_WEEKLY_MOVE_PCT) -> list[str]:
    """'- DISCREPANCY ...' lines for bid prices that moved more than `limit_pct`
    since the previous dataset (matched on fund code). Same-date pairs and
    funds missing from either side are skipped."""
    prev = {p.get("fund_code"): p for p in (previous or []) if p.get("fund_code")}
    lines = []
    for f in funds:
        p = prev.get(f.get("fund_code"))
        if not p:
            continue
        old, new = p.get("bid_price"), f.get("bid_price")
        if not old or new is None or old <= 0:
            continue
        if p.get("price_date") and p.get("price_date") == f.get("price_date"):
            continue
        move = (new - old) / old * 100
        if abs(move) > limit_pct:
            lines.append(f"- DISCREPANCY {f.get('name')} week-on-week bid price move {move:+.1f}%: "
                         f"{old} on {p.get('price_date')} -> {new} on {f.get('price_date')} "
                         f"(over {limit_pct:g}%, check before publishing)")
    return lines
