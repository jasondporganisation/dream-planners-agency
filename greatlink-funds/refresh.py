#!/usr/bin/env python3
"""Refresh the GreatLink fund dataset and rebuild the dashboard.

Usage:
    python refresh.py                  # full monthly refresh (no arguments needed)
    python refresh.py --discover-only  # Phase 1 checkpoint: discover the Fund
                                       # Centre endpoints, print the report, stop
    python refresh.py --rediscover     # force fresh endpoint discovery, then refresh

Pipeline: harvest fund list -> discover/reuse Fund Centre endpoints -> fetch
screener + per-fund detail -> merge prices -> download fact sheets -> write
data/funds.json + funds.csv + refresh_report.md (atomically; the previous good
dataset is never overwritten by a half-finished run) -> keep a dated copy in
data/history/ -> rebuild dashboard.html.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scraper import documents, fundcentre, fundlist, prices  # noqa: E402
from scraper.util import PoliteSession, atomic_write, atomic_write_json, slugify  # noqa: E402

DATA = ROOT / "data"
FACTSHEETS = ROOT / "factsheets"
DISCREPANCY_TOLERANCE = 0.1  # percentage points

RETURN_FIELDS = ["ret_ytd", "ret_1m", "ret_3m", "ret_6m", "ret_1y",
                 "ret_3y_ann", "ret_3y_cum", "ret_5y_ann", "ret_5y_cum",
                 "ret_10y_ann", "ret_si_ann", "ret_si_cum"]

CSV_COLUMNS = ["name", "category", "fund_id", "risk_class", "currency",
               "bid_price", "offer_price", "price_date", "fund_size_m",
               "mgmt_fee_pct", "inception_date", "manager"] + RETURN_FIELDS


def log(msg: str) -> None:
    print(msg, flush=True)


def load_endpoints() -> dict | None:
    path = DATA / "endpoints.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def build_fund_record(stub: dict, screener_row: dict | None, detail: dict,
                      report_lines: list[str]) -> dict:
    """Merge fund-list stub + screener row + detail payloads into the data model."""
    fund: dict = {
        "fund_id": stub["fund_id"],
        "name": stub["name"],
        "category": stub["category"] or "Uncategorised (new fund?)",
        "ge_page_url": stub["ge_page_url"],
        "fundcentre_url": stub["fundcentre_url"],
        "manager": None, "underlying_fund": None, "inception_date": None,
        "fund_size_m": None, "currency": "SGD", "mgmt_fee_pct": None,
        "risk_class": None,
        "eligibility": {"cpf_oa": None, "cpf_sa": None, "srs": None, "cash": True},
        "bid_price": None, "offer_price": None, "price_date": None,
        "returns": {k: None for k in RETURN_FIELDS},
        "benchmark_name": None, "benchmark_returns": {},
        "calendar_year_returns": {}, "calendar_year_benchmark": {},
        "allocation_asset": [], "allocation_geo": [], "allocation_sector": [],
        "top_holdings": [], "objective": None,
        "docs": {"factsheet_url": None, "factsheet_local": None,
                 "factsheet_as_at": None, "phs_url": None, "other": []},
        "sources": {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "missing_fields": [],
    }
    if screener_row is not None:
        norm = fundcentre.normalize_screener_row(screener_row)
        for field in ("isin", "currency", "manager", "risk_class", "benchmark_name",
                      "bid_price", "offer_price", "price_date", "inception_date",
                      "mgmt_fee_pct", "fund_size_m"):
            if norm.get(field) is not None:
                fund[field] = norm[field]
        for key, val in norm["returns"].items():
            if val is not None:
                fund["returns"][key] = val
        fund["calendar_year_returns"].update(norm["calendar_year_returns"])
        fund["sources"]["returns"] = "fundcentre-screener"
    else:
        report_lines.append(f"- {fund['name']}: no screener row matched (by id or name)")

    fund.update(fundcentre.extract_allocations(detail.get("portfolio")))
    fund["docs"].update(
        {k: v for k, v in fundcentre.extract_documents(detail.get("documents")).items() if v})
    for role in ("returns_errors", "portfolio_errors", "documents_errors"):
        for err in detail.get(role, []):
            report_lines.append(f"- {fund['name']}: {role.replace('_', ' ')}: {err}")

    fund["missing_fields"] = sorted(
        [k for k, v in fund["returns"].items() if v is None
         and k not in ("ret_3y_cum", "ret_5y_cum", "ret_si_cum")]
        + [f for f in ("bid_price", "fund_size_m", "mgmt_fee_pct", "risk_class")
           if fund[f] is None]
        + ([] if fund["docs"]["factsheet_url"] else ["factsheet_url"]))
    return fund


def cross_check_factsheets(funds: list[dict], report_lines: list[str]) -> None:
    """Compare screener returns against the downloaded fact sheet PDF; keep the
    Fund Centre figure, log discrepancies > 0.1pp."""
    from scraper.factsheet_pdf import parse_factsheet
    for fund in funds:
        local = fund["docs"].get("factsheet_local")
        if not local:
            continue
        try:
            parsed = parse_factsheet(ROOT / local)
        except Exception as err:  # noqa: BLE001
            report_lines.append(f"- {fund['name']}: fact sheet parse failed: {err}")
            continue
        if parsed["as_at"] and not fund["docs"].get("factsheet_as_at"):
            fund["docs"]["factsheet_as_at"] = parsed["as_at"]
        for key, pdf_val in parsed["fund"].items():
            fc_val = fund["returns"].get(key)
            if fc_val is None:
                fund["returns"][key] = pdf_val
                fund["sources"][f"returns.{key}"] = "factsheet-pdf"
            elif abs(fc_val - pdf_val) > DISCREPANCY_TOLERANCE:
                report_lines.append(
                    f"- DISCREPANCY {fund['name']} {key}: Fund Centre {fc_val} vs "
                    f"fact sheet {pdf_val} (kept Fund Centre)")
        for key, val in parsed["benchmark"].items():
            fund["benchmark_returns"].setdefault(key, val)


def write_outputs(funds: list[dict], as_at: str, report_lines: list[str]) -> None:
    dataset = {
        "as_at": as_at,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sample": False,
        "convention": ("Returns are bid-to-bid in the fund currency, net of fund "
                       "management fees, excluding policy-level charges."),
        "funds": funds,
    }
    atomic_write_json(DATA / "funds.json", dataset)
    atomic_write_json(DATA / "history" / f"funds-{date.today().isoformat()}.json", dataset)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)
    for f in funds:
        writer.writerow([
            f["returns"].get(c) if c in RETURN_FIELDS else f.get(c, "")
            for c in CSV_COLUMNS])
    atomic_write(DATA / "funds.csv", buf.getvalue())
    log(f"→ Wrote data/funds.json, data/funds.csv ({len(funds)} funds)")

    report = ["# Refresh report", "", f"Run finished: {dataset['generated_at']}",
              f"Data as at: {as_at}", f"Funds processed: {len(funds)}", ""]
    missing = [f"- {f['name']}: missing {', '.join(f['missing_fields'])}"
               for f in funds if f["missing_fields"]]
    report += ["## Notes and failures", ""] + (report_lines or ["- none"]) + [""]
    report += ["## Missing fields per fund", ""] + (missing or ["- none"]) + [""]
    atomic_write(DATA / "refresh_report.md", "\n".join(report))
    log("→ Wrote data/refresh_report.md")


def main() -> int:
    discover_only = "--discover-only" in sys.argv
    rediscover = "--rediscover" in sys.argv or discover_only
    DATA.mkdir(exist_ok=True)
    FACTSHEETS.mkdir(exist_ok=True)
    session = PoliteSession()
    report_lines: list[str] = []

    log("== GreatLink refresh ==")
    log("Step 1/6: harvesting fund list from greateasternlife.com …")
    stubs = fundlist.harvest(session)
    check = fundlist.completeness_report(stubs)
    log(f"  found {check['found']} funds (expected ~{check['expected']})")
    for name in check["missing"]:
        report_lines.append(f"- MISSING from fund list page: {name}")
    for name in check["unexpected_kept"]:
        report_lines.append(f"- NEW fund not in expected list (kept): {name}")
    if check["found"] == 0:
        log("!! No funds found on the fund list page — layout may have changed. Stopping "
            "without touching the previous dataset.")
        return 1

    log("Step 2/6: Fund Centre endpoints …")
    endpoints = None if rediscover else load_endpoints()
    if endpoints is None:
        log("  driving headless Chromium through the Fund Centre (this takes ~1 min)")
        sample_id = stubs[0]["fund_id"]
        result = fundcentre.discover(DATA, sample_fund_id=sample_id)
        endpoints = load_endpoints()
        log(result["report_text"])
        if discover_only:
            log("\n--discover-only: stopping at the Phase 1 checkpoint. Review "
                "data/discovery_report.md, then run `python refresh.py`.")
            return 0
    else:
        log("  using cached data/endpoints.json (run with --rediscover to refresh)")

    log("Step 3/6: fetching screener + per-fund detail …")
    rows = fundcentre.fetch_fund_list(session, endpoints)
    by_id = {str(fundcentre.normalize_screener_row(r)["fund_id"]): r for r in rows}
    by_name = {str(fundcentre.normalize_screener_row(r)["name"] or "").lower(): r for r in rows}
    funds = []
    for i, stub in enumerate(stubs, 1):
        log(f"  [{i}/{len(stubs)}] {stub['name']}")
        row = by_id.get(stub["fund_id"]) or by_name.get(stub["name"].lower())
        detail = fundcentre.fetch_detail(session, endpoints, stub["fund_id"])
        funds.append(build_fund_record(stub, row, detail, report_lines))

    log("Step 4/6: merging bid/offer prices …")
    prices.merge_prices(session, endpoints, funds, report_lines)

    log("Step 5/6: downloading fact sheets …")
    for fund in funds:
        local = documents.download_factsheet(session, fund, FACTSHEETS)
        fund["docs"]["factsheet_local"] = local
        if fund["docs"]["factsheet_url"] and not local:
            report_lines.append(f"- {fund['name']}: fact sheet download failed "
                                f"(online link kept as fallback)")
    cross_check_factsheets(funds, report_lines)

    as_at = max((f["price_date"] for f in funds if f["price_date"]),
                default=date.today().isoformat())
    log("Step 6/6: writing dataset + rebuilding dashboard …")
    write_outputs(funds, as_at, report_lines)

    import build_dashboard
    build_dashboard.main()
    log("Done. Open dashboard.html in your browser.")
    return 0


if __name__ == "__main__":
    import requests

    try:
        sys.exit(main())
    except requests.RequestException as err:
        print(f"\n!! Network problem talking to greateasternlife.com / morningstar.com:"
              f"\n   {err}"
              f"\n   Check your internet connection (corporate networks and VPNs can"
              f"\n   block these sites) and run `python refresh.py` again."
              f"\n   The previous dataset and dashboard were NOT modified.")
        sys.exit(1)
