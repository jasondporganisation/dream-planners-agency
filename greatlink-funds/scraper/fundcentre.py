"""Step 2: the ILP Fund Centre data — a newwealth.cloud white-label fund
centre (Morningstar data underneath) at https://ge-fundcentersg.newwealth.cloud.

Endpoints (all plain JSON, verified Aug 2026, see discovery/REPORT.md):
  * config   GET  /fund-center-api/ge/config/static?config_type=typesense_config
             -> search-only Typesense key (no auth needed to get it)
  * screener POST /api/multi_search  (Typesense; header X-TYPESENSE-API-KEY)
             -> every fund's trailing returns, price, risk, eligibility, doc links
  * detail   GET  /fund-center-api/ge/v4/funds?code=<SecId>_<FundCode>&mode=internal
                    &id_type=composite&lang=en_sg   (no auth)
  * history  GET  /fund-center-api/api/v2/timeseries?code=<SecId>&id_type=sec_id
                    &currency_id=BAS&ts_type=ts|nav&from_date=..&to_date=..   (no auth)
             ts = total-return index (distributions reinvested), nav = bid price

Field semantics (verified against NAV recomputation): screener YTD/ReturnM1/M3/
M6/M12 are cumulative; ReturnM36/M60/M120/MAX are annualised. The detail
endpoint's "CumulativePerformance" block does NOT agree with NAV history and is
ignored; its "AnnualizedReturn" block equals the screener figures.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .util import PoliteSession

HOST = "https://ge-fundcentersg.newwealth.cloud"
REFERER = "https://www.greateasternlife.com/"
PRODUCT_RANGE = "GreatLink funds"

SCREENER_RETURN_MAP = {   # screener field -> our key
    "YTD": "ret_ytd", "ReturnM1": "ret_1m", "ReturnM3": "ret_3m", "ReturnM6": "ret_6m",
    "ReturnM12": "ret_1y", "ReturnM36": "ret_3y_ann", "ReturnM60": "ret_5y_ann",
    "ReturnM120": "ret_10y_ann", "ReturnMAX": "ret_si_ann",
}


def _num(v):
    if v in (None, "", [], "N/A"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _iso(ts) -> str | None:
    """Epoch seconds -> ISO date (UTC), or None."""
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ts, timezone.utc).date().isoformat() if ts else None


def _en(v):
    """Unwrap {'EN_SG': ...} language dicts."""
    if isinstance(v, dict) and "EN_SG" in v:
        return v["EN_SG"]
    return v


# ------------------------------------------------------------------ fetching

def get_typesense_key(session: PoliteSession) -> str:
    res = session.get(f"{HOST}/fund-center-api/ge/config/static",
                      params={"config_type": "typesense_config"}, headers={"Referer": REFERER})
    res.raise_for_status()
    return res.json()["typesense_key"]["value"]


def fetch_screener(session: PoliteSession, key: str, product_range: str = PRODUCT_RANGE) -> list[dict]:
    """All active funds in the product range (one request, per_page 250)."""
    body = {"searches": [{
        "collection": "funds", "q": "", "query_by": "FundName", "per_page": 250, "page": 1,
        "filter_by": f"ProductRange:=[`{product_range}`] && Status:=[`Active`]",
        "sort_by": "FundName:asc",
    }]}
    res = session.post(f"{HOST}/api/multi_search", json=body,
                       headers={"X-TYPESENSE-API-KEY": key, "Referer": REFERER})
    res.raise_for_status()
    result = res.json()["results"][0]
    if "error" in result:
        raise RuntimeError(f"screener error: {result['error']}")
    hits = [h["document"] for h in result.get("hits", [])]
    if result.get("found", 0) != len(hits):
        raise RuntimeError(f"screener paginated unexpectedly: found={result.get('found')} returned={len(hits)}")
    return hits


def fetch_detail(session: PoliteSession, composite_id: str) -> dict:
    res = session.get(f"{HOST}/fund-center-api/ge/v4/funds",
                      params={"code": composite_id, "mode": "internal",
                              "id_type": "composite", "lang": "en_sg"},
                      headers={"Referer": REFERER})
    res.raise_for_status()
    return res.json()


def fetch_nav_history(session: PoliteSession, sec_id: str, from_date: str,
                      to_date: str | None = None, ts_type: str = "ts") -> dict[str, float]:
    """Daily history {iso_date: value}. ts_type="ts" is the total-return index
    (distributions reinvested, start_value 100) — this is what the screener's
    and fact sheets' returns are based on, so use it for all return maths.
    ts_type="nav" is the raw bid price (drops on ex-dividend dates)."""
    res = session.get(f"{HOST}/fund-center-api/api/v2/timeseries",
                      params={"code": sec_id, "currency_id": "BAS", "id_type": "sec_id",
                              "from_date": from_date, "to_date": to_date or date.today().isoformat(),
                              "ts_type": ts_type, "start_value": 100, "maximum": "false"},
                      headers={"Referer": REFERER})
    res.raise_for_status()
    sec = res.json().get("TimeSeries", {}).get("Security") or []
    if not sec:
        return {}
    out = {}
    for row in sec[0].get("HistoryDetail", []):
        v = _num(row.get("Value"))
        if v is not None and row.get("EndDate"):
            out[row["EndDate"]] = v
    return out


# ------------------------------------------------------------------ shaping

def normalize_screener_row(row: dict) -> dict:
    fs = row.get("FundingSource") or []
    return {
        "sec_id": row.get("SecId"), "fund_code": row.get("FundCode"),
        "name": row.get("FundName"), "currency": row.get("Currency"),
        "asset_class": row.get("GlobalAssetClassName"), "ms_category": row.get("GlobalCategoryName"),
        "manager": row.get("FundManager"), "risk_class": row.get("RiskLevel"),
        "inception_date": _iso(row.get("InceptionDate")),
        "bid_price": _num(row.get("LastPrice")), "price_date": _iso(row.get("LastPriceDate")),
        "eligibility": {"cash": "Cash" in fs, "cpf_oa": "CPF-OA" in fs,
                        "cpf_sa": "CPF-SA" in fs, "srs": "SRS" in fs},
        "returns": {k: _num(row.get(src)) for src, k in SCREENER_RETURN_MAP.items()},
        "docs": {"factsheet_url": row.get("MsProviderFactsheet") or None,
                 "phs_url": row.get("MsProductHighlights") or None,
                 "prospectus_url": row.get("MsProspectus") or None,
                 "annual_report_url": row.get("MsAnnualReport") or None,
                 "semi_annual_report_url": row.get("MsSemiAnnualReport") or None},
    }


def _alloc(block: dict | None) -> list[dict]:
    rows = (block or {}).get("data") or []
    out = []
    for r in rows:
        v = _num(r.get("value"))
        if r.get("name") and v is not None:
            out.append({"label": str(r["name"]), "pct": round(v, 2)})
    return out


def extract_detail(detail: dict) -> dict:
    po = detail.get("ProductOverview") or {}
    fee = detail.get("FeeAndCharge") or {}
    perf = detail.get("Performance") or {}
    port = detail.get("Portfolios") or {}
    docs = detail.get("FundDocument") or {}
    aum = po.get("TotalAum") or {}

    def doc(kind: str):
        d = _en(docs.get(kind) or {}) or {}
        url = d.get("External") or None
        eff = d.get("ExternalEffectiveDate") or d.get("ExternalDate")
        return url, _iso(eff)

    factsheet_url, factsheet_eff = doc("ProviderFactsheet")
    calendar = {}
    for r in (perf.get("CalendarPerformance") or {}).get("data") or []:
        v = _num(r.get("value"))
        if v is not None:
            calendar[str(r.get("key"))] = v
    mgmt = _num(fee.get("CustomManagementFee"))   # GE's own fee figure (matches fact sheets)
    if mgmt is None:
        mgmt = _num(fee.get("AnnualManagementFee"))
    bench = po.get("NWCompositeBenchmark")
    if bench in ("", "NA", "N/A", None):
        bench = None
    return {
        "objective": (_en(po.get("InvestmentObjective")) or "").strip() or None,
        "ms_category": _en(po.get("GlobalCategoryName")) or None,
        "manager": _en(po.get("FundManager")) or None,
        "underlying_fund": po.get("UnderlyingFund") or None,
        "inception_date": _iso(po.get("InceptionDate")),
        "fund_size_m": round(_num(aum.get("Value")) / 1e6, 2) if _num(aum.get("Value")) else None,
        "fund_size_as_at": _iso(aum.get("Date")),
        "mgmt_fee_pct": mgmt, "expense_ratio_pct": _num(fee.get("ExpenseRatio")),
        "benchmark_name": bench,
        "calendar_year_returns": calendar,
        "allocations_as_at": _iso((port.get("AssetAllocation") or {}).get("updateDate")),
        "allocation_asset": _alloc(port.get("AssetAllocation")),
        "allocation_geo": _alloc(port.get("GeographicalAllocation")),
        "allocation_sector": _alloc(port.get("SectorAllocation")),
        "top_holdings": [{"name": a["label"], "pct": a["pct"]}
                         for a in _alloc(port.get("TopHolding"))[:10]],
        "docs": {"factsheet_url": factsheet_url, "factsheet_as_at": factsheet_eff,
                 "phs_url": doc("ProductHighlights")[0], "prospectus_url": doc("Prospectus")[0],
                 "annual_report_url": doc("AnnualReport")[0],
                 "semi_annual_report_url": doc("SemiAnnualReport")[0]},
        "annualized_block": perf.get("AnnualizedReturn") or {},
    }


# ------------------------------------------------------------------ NAV maths

def price_on_or_before(history: dict[str, float], iso_day: str) -> tuple[float, str] | tuple[None, None]:
    keys = [d for d in history if d <= iso_day]
    if not keys:
        return None, None
    k = max(keys)
    return history[k], k


def returns_from_history(history: dict[str, float], as_of: str | None = None) -> dict:
    """Cumulative and annualised returns (%) from a total-return history, ending at
    `as_of` (default: last date in history). Uses the last price on/before each
    anchor date; the base must be within 10 days of the anchor to count."""
    if not history:
        return {}
    end = as_of or max(history)
    end_px, end_day = price_on_or_before(history, end)
    if end_px is None:
        return {}
    first = min(history)
    end_d = date.fromisoformat(end_day)
    out = {"as_of": end_day, "price": end_px}

    def anchor(days_back_years: float, key_cum: str, key_ann: str | None):
        target = end_d - timedelta(days=round(365.25 * days_back_years))
        if target < date.fromisoformat(first):
            return
        px, d = price_on_or_before(history, target.isoformat())
        if px is None or (target - date.fromisoformat(d)).days > 10:
            return
        out[key_cum] = round((end_px / px - 1) * 100, 2)
        if key_ann:
            out[key_ann] = round(((end_px / px) ** (1 / days_back_years) - 1) * 100, 2)

    anchor(1, "ret_1y", None)
    anchor(3, "ret_3y_cum", "ret_3y_ann")
    anchor(5, "ret_5y_cum", "ret_5y_ann")
    anchor(10, "ret_10y_cum", "ret_10y_ann")
    # YTD: last price of the previous calendar year
    px, d = price_on_or_before(history, f"{end_d.year - 1}-12-31")
    if px is not None and d >= f"{end_d.year - 1}-12-15":
        out["ret_ytd"] = round((end_px / px - 1) * 100, 2)
    return out
