#!/usr/bin/env python3
"""Refresh the GreatLink fund dataset and rebuild the dashboard.

    python refresh.py            # the one monthly command (no arguments)
    python refresh.py --no-pdf   # skip fact sheet downloads/parsing (quick data-only run)

Pipeline
  1. fund list + GE category + Fund Centre IDs   (greateasternlife.com)
  2. screener: returns, price, risk, eligibility, doc links for all GreatLink funds
  3. per fund: detail (facts, fees, allocations, holdings, calendar years)
              + total-return history (cumulative 3Y/5Y/10Y, independent cross-check)
  4. official bid/offer prices                    (greateasternlife.com JSON)
  5. fact sheet PDFs -> factsheets/, parsed for benchmark returns + cross-check
  6. data/funds.json, data/funds.csv, data/history/, data/refresh_report.md,
     dashboard.html   (all written atomically — a failed run never damages
     the previous good dataset)
"""

from __future__ import annotations

import csv
import io
import sys
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scraper import documents, factsheet_pdf, fundcentre, fundlist, prices  # noqa: E402
from scraper.util import PoliteSession, atomic_write, atomic_write_json  # noqa: E402

DATA = ROOT / "data"
FACTSHEETS = ROOT / "factsheets"
TOLERANCE_PP = 0.1   # discrepancy tolerance in percentage points

RETURN_FIELDS = ["ret_ytd", "ret_1m", "ret_3m", "ret_6m", "ret_1y",
                 "ret_3y_ann", "ret_3y_cum", "ret_5y_ann", "ret_5y_cum",
                 "ret_10y_ann", "ret_10y_cum", "ret_si_ann"]
CSV_COLUMNS = ["name", "category", "fund_id", "fund_code", "risk_class", "currency",
               "bid_price", "offer_price", "price_date", "fund_size_m", "mgmt_fee_pct",
               "expense_ratio_pct", "inception_date", "manager", "cpf_oa", "cpf_sa", "srs",
               "returns_as_at"] + RETURN_FIELDS + ["factsheet_as_at", "factsheet_local", "factsheet_url"]
CONVENTION = ("Returns are bid-to-bid in the fund currency (SGD), net of fund management "
              "fees, excluding policy-level charges. YTD, 1M, 3M, 6M and 1Y are cumulative; "
              "3Y, 5Y, 10Y and since-inception are annualised unless labelled cumulative.")


def log(msg: str) -> None:
    print(msg, flush=True)


def new_record(stub: dict) -> dict:
    return {
        "fund_id": stub["fund_id"], "sec_id": stub["sec_id"], "fund_code": stub["fund_code"],
        "name": None, "category": stub["category"] or "Uncategorised (new fund?)",
        "asset_class": None, "ms_category": None,
        "ge_page_url": stub["ge_page_url"], "fundcentre_url": stub["fundcentre_url"],
        "manager": None, "underlying_fund": None, "inception_date": None,
        "fund_size_m": None, "fund_size_as_at": None, "currency": "SGD",
        "mgmt_fee_pct": None, "expense_ratio_pct": None, "risk_class": None,
        "eligibility": {"cpf_oa": None, "cpf_sa": None, "srs": None, "cash": None},
        "bid_price": None, "offer_price": None, "price_date": None, "price_status": None,
        "returns": {k: None for k in RETURN_FIELDS}, "returns_as_at": None,
        "benchmark_name": None, "factsheet_returns": {}, "benchmark_returns": {},
        "calendar_year_returns": {}, "allocations_as_at": None,
        "allocation_asset": [], "allocation_geo": [], "allocation_sector": [],
        "top_holdings": [], "objective": None,
        "docs": {"factsheet_url": None, "factsheet_local": None, "factsheet_as_at": None,
                 "phs_url": None, "prospectus_url": None, "annual_report_url": None,
                 "semi_annual_report_url": None},
        "sources": {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "nav_check": {}, "missing_fields": [],
    }


def merge_screener(fund: dict, row: dict) -> None:
    n = fundcentre.normalize_screener_row(row)
    for k in ("name", "currency", "asset_class", "ms_category", "manager", "risk_class",
              "inception_date", "bid_price", "price_date"):
        if n.get(k) not in (None, ""):
            fund[k] = n[k]
    fund["eligibility"] = n["eligibility"]
    for k, v in n["returns"].items():
        fund["returns"][k] = v
    fund["returns_as_at"] = n["price_date"]
    for k, v in n["docs"].items():
        if v:
            fund["docs"][k] = v
    fund["sources"]["returns"] = "Fund Centre screener"
    fund["sources"]["eligibility"] = "Fund Centre screener (FundingSource)"


def merge_detail(fund: dict, detail: dict) -> None:
    d = fundcentre.extract_detail(detail)
    for k in ("objective", "ms_category", "manager", "underlying_fund", "inception_date",
              "fund_size_m", "fund_size_as_at", "mgmt_fee_pct", "expense_ratio_pct",
              "benchmark_name", "allocations_as_at", "allocation_asset", "allocation_geo",
              "allocation_sector", "top_holdings", "calendar_year_returns"):
        if d.get(k) not in (None, [], {}, ""):
            fund[k] = d[k]
    for k, v in d["docs"].items():
        if v and not fund["docs"].get(k):
            fund["docs"][k] = v
    fund["sources"]["facts"] = "Fund Centre detail (v4/funds)"
    fund["sources"]["allocations"] = "Fund Centre detail (Morningstar portfolio data)"


def merge_nav(fund: dict, history: dict, report: list[str]) -> None:
    r = fundcentre.returns_from_history(history, fund.get("returns_as_at"))
    if not r:
        report.append(f"- {fund['name']}: no total-return history returned")
        return
    for k in ("ret_3y_cum", "ret_5y_cum", "ret_10y_cum"):
        if k in r:
            fund["returns"][k] = r[k]
    fund["sources"]["cumulative_returns"] = "computed from Fund Centre total-return history"
    # Independent cross-check of the screener's figures (same date, same prices)
    diffs = {}
    for k in ("ret_ytd", "ret_1y", "ret_3y_ann", "ret_5y_ann", "ret_10y_ann"):
        a, b = fund["returns"].get(k), r.get(k)
        if a is not None and b is not None:
            diffs[k] = round(a - b, 3)
            if abs(a - b) > TOLERANCE_PP:
                report.append(f"- DISCREPANCY {fund['name']} {k}: screener {a:.2f} vs NAV-derived "
                              f"{b:.2f} (kept screener)")
    fund["nav_check"] = {"as_of": r.get("as_of"), "total_return_index": r.get("price"), "diff_pp": diffs}


def merge_prices(fund: dict, px: dict | None, report: list[str]) -> None:
    if not px:
        report.append(f"- {fund['name']}: not found on the GE prices page (fund code {fund['fund_code']})")
        return
    if px["bid"] is not None and fund["bid_price"] is not None and abs(px["bid"] - fund["bid_price"]) > 0.0005 \
            and px["date"] == fund["price_date"]:
        report.append(f"- DISCREPANCY {fund['name']} bid price: GE prices {px['bid']} vs Fund Centre "
                      f"{fund['bid_price']} on {px['date']} (kept Fund Centre)")
    if fund["bid_price"] is None:
        fund["bid_price"], fund["price_date"] = px["bid"], px["date"]
    fund["offer_price"], fund["price_status"] = px["offer"], px["status"]
    if not fund["price_date"]:
        fund["price_date"] = px["date"]
    fund["sources"]["offer_price"] = "GE fund-prices.json"


def apply_factsheet(fund: dict, history: dict, report: list[str]) -> None:
    local = fund["docs"].get("factsheet_local")
    if not local:
        return
    try:
        parsed = factsheet_pdf.parse_factsheet(ROOT / local, fund["fund_code"])
    except Exception as err:  # noqa: BLE001
        report.append(f"- {fund['name']}: fact sheet parse failed: {err}")
        return
    if parsed["as_at"]:
        fund["docs"]["factsheet_as_at"] = parsed["as_at"]
    if not parsed["fund"]:
        report.append(f"- {fund['name']}: performance table not found in fact sheet "
                      f"(page for {fund['fund_code']})")
        return
    fund["factsheet_returns"] = parsed["fund"]
    fund["benchmark_returns"] = parsed["benchmark"]
    fund["sources"]["benchmark_returns"] = f"fact sheet PDF (as at {parsed['as_at']})"
    facts = parsed["facts"]
    if facts.get("underlying_fund") and not fund.get("underlying_fund"):
        fund["underlying_fund"] = facts["underlying_fund"]
        fund["sources"]["underlying_fund"] = "fact sheet PDF"
    if facts.get("mgmt_fee_pct") is not None and fund.get("mgmt_fee_pct") is not None \
            and abs(facts["mgmt_fee_pct"] - fund["mgmt_fee_pct"]) > 0.005:
        report.append(f"- DISCREPANCY {fund['name']} management fee: Fund Centre {fund['mgmt_fee_pct']} "
                      f"vs fact sheet {facts['mgmt_fee_pct']} (kept Fund Centre)")
    # Like-for-like check: recompute 1Y/3Y/5Y/10Y at the fact sheet date from NAV history
    if parsed["as_at"] and history:
        at_fs = fundcentre.returns_from_history(history, parsed["as_at"])
        check = {}
        for k in ("ret_1y", "ret_3y_ann", "ret_5y_ann", "ret_10y_ann"):
            a, b = parsed["fund"].get(k), at_fs.get(k)
            if a is not None and b is not None:
                check[k] = {"factsheet": a, "nav_at_factsheet_date": b, "diff_pp": round(b - a, 2)}
                if abs(a - b) > TOLERANCE_PP:
                    report.append(f"- DISCREPANCY {fund['name']} {k} at {parsed['as_at']}: fact sheet "
                                  f"{a:.2f} vs NAV-derived {b:.2f} (dashboard shows Fund Centre figures "
                                  f"as at {fund['returns_as_at']})")
        fund["nav_check"]["at_factsheet_date"] = check


def finalise_missing(fund: dict) -> None:
    miss = [k for k in ("ret_ytd", "ret_1y", "ret_3y_ann", "ret_5y_ann", "ret_10y_ann", "ret_si_ann")
            if fund["returns"].get(k) is None]
    miss += [k for k in ("bid_price", "fund_size_m", "mgmt_fee_pct", "risk_class", "inception_date")
             if fund.get(k) is None]
    if not fund["docs"].get("factsheet_url"):
        miss.append("factsheet_url")
    elif not fund["docs"].get("factsheet_local"):
        miss.append("factsheet_local")
    if not fund["benchmark_returns"]:
        miss.append("benchmark_returns")
    fund["missing_fields"] = miss


def write_outputs(funds: list[dict], as_at: str, report_lines: list[str], started: datetime) -> dict:
    fs_dates = sorted({f["docs"]["factsheet_as_at"] for f in funds if f["docs"].get("factsheet_as_at")})
    dataset = {
        "as_at": as_at,
        "factsheets_as_at": fs_dates[-1] if fs_dates else None,
        "factsheets_as_at_range": fs_dates,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sample": False, "convention": CONVENTION,
        "fund_count": len(funds), "funds": funds,
    }
    atomic_write_json(DATA / "funds.json", dataset)
    atomic_write_json(DATA / "history" / f"funds-{date.today().isoformat()}.json", dataset)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_COLUMNS)
    for f in funds:
        row = []
        for c in CSV_COLUMNS:
            if c in RETURN_FIELDS:
                row.append(f["returns"].get(c))
            elif c in ("cpf_oa", "cpf_sa", "srs"):
                row.append(f["eligibility"].get(c))
            elif c in ("factsheet_as_at", "factsheet_local", "factsheet_url"):
                row.append(f["docs"].get(c))
            else:
                row.append(f.get(c))
        w.writerow(["" if v is None else v for v in row])
    atomic_write(DATA / "funds.csv", buf.getvalue())

    failures = [ln for ln in report_lines if "DISCREPANCY" not in ln]
    discrepancies = [ln for ln in report_lines if "DISCREPANCY" in ln]
    missing = [f"- {f['name']}: {', '.join(f['missing_fields'])}" for f in funds if f["missing_fields"]]
    no_pdf = [f["name"] for f in funds if not f["docs"].get("factsheet_local")]
    report = [
        "# Refresh report", "",
        f"- Run started: {started.isoformat(timespec='seconds')}",
        f"- Run finished: {dataset['generated_at']}",
        f"- Returns / prices as at: **{as_at}**",
        f"- Fact sheets as at: **{dataset['factsheets_as_at']}**"
        + (f" (range {fs_dates[0]} – {fs_dates[-1]})" if len(fs_dates) > 1 else ""),
        f"- Funds processed: {len(funds)}",
        f"- Fact sheets on disk: {len(funds) - len(no_pdf)}/{len(funds)}", "",
        "## Failures / notes", ""] + (failures or ["- none"]) + ["",
        "## Discrepancies (> 0.1 pp or price/fee mismatch)", ""] + (discrepancies or ["- none"]) + ["",
        "## Missing fields per fund", ""] + (missing or ["- none"]) + ["",
        "## Funds without a local fact sheet", ""] + ([f"- {n}" for n in no_pdf] or ["- none"]) + [""]
    atomic_write(DATA / "refresh_report.md", "\n".join(report))
    return dataset


def main(argv: list[str]) -> int:
    started = datetime.now(timezone.utc)
    do_pdf = "--no-pdf" not in argv
    DATA.mkdir(exist_ok=True)
    (DATA / "history").mkdir(exist_ok=True)
    FACTSHEETS.mkdir(exist_ok=True)
    session = PoliteSession()
    report: list[str] = []

    log("== GreatLink refresh ==")
    log("Step 1/6  Fund list + categories (greateasternlife.com)")
    stubs = fundlist.harvest(session)
    if not stubs:
        log("!! No fund links found on the GreatLink funds page — layout changed? Stopping; "
            "previous dataset untouched.")
        return 1
    log(f"          {len(stubs)} fund IDs in {len({s['category'] for s in stubs})} categories")

    log("Step 2/6  Fund Centre screener")
    key = fundcentre.get_typesense_key(session)
    rows = fundcentre.fetch_screener(session, key)
    by_id = {f"{r['SecId']}_{r['FundCode']}": r for r in rows}
    log(f"          {len(rows)} active '{fundcentre.PRODUCT_RANGE}' in the screener")
    funds = []
    for stub in stubs:
        f = new_record(stub)
        row = by_id.get(stub["fund_id"])
        if row is None:
            report.append(f"- {stub['fund_id']}: on GE page but not in screener (delisted?) — skipped")
            continue
        merge_screener(f, row)
        funds.append(f)
    for cid, row in by_id.items():
        if cid not in {f["fund_id"] for f in funds}:
            report.append(f"- NEW fund in screener not on GE page (kept, uncategorised): {row['FundName']}")
            f = new_record({"fund_id": cid, "sec_id": row["SecId"], "fund_code": row["FundCode"],
                            "category": None, "ge_page_url": fundlist.FUND_LIST_URL,
                            "fundcentre_url": f"{fundlist.FUND_CENTRE_URL}#/detail?id={cid}"})
            merge_screener(f, row)
            funds.append(f)
    check = fundlist.completeness_report(funds)
    log(f"          completeness: {check['found']} found, {check['expected']} expected; "
        f"missing={check['missing'] or 'none'}; unexpected={check['unexpected_kept'] or 'none'}")
    for n in check["missing"]:
        report.append(f"- EXPECTED fund not found anywhere: {n}")

    log("Step 3/6  Per-fund detail + NAV history")
    histories: dict[str, dict] = {}
    for i, f in enumerate(funds, 1):
        log(f"          [{i:>2}/{len(funds)}] {f['name']}")
        try:
            merge_detail(f, fundcentre.fetch_detail(session, f["fund_id"]))
        except Exception as err:  # noqa: BLE001
            report.append(f"- {f['name']}: detail fetch failed: {err}")
        try:
            start = f.get("inception_date") or "1990-01-01"
            hist = fundcentre.fetch_nav_history(session, f["sec_id"], start)
            histories[f["fund_id"]] = hist
            merge_nav(f, hist, report)
        except Exception as err:  # noqa: BLE001
            report.append(f"- {f['name']}: NAV history failed: {err}")

    log("Step 4/6  Official bid/offer prices")
    try:
        px = prices.fetch_prices(session)
        for f in funds:
            merge_prices(f, px.get(f["fund_code"]), report)
    except Exception as err:  # noqa: BLE001
        report.append(f"- prices page failed: {err}")

    if do_pdf:
        log("Step 5/6  Fact sheet PDFs")
        for i, f in enumerate(funds, 1):
            local = documents.download_factsheet(session, f, FACTSHEETS)
            f["docs"]["factsheet_local"] = local
            if f["docs"]["factsheet_url"] and not local:
                report.append(f"- {f['name']}: fact sheet download failed (online link kept)")
            elif not f["docs"]["factsheet_url"]:
                report.append(f"- {f['name']}: no fact sheet link in Fund Centre")
            log(f"          [{i:>2}/{len(funds)}] {'ok ' if local else 'MISSING'} {f['name']}")
            apply_factsheet(f, histories.get(f["fund_id"], {}), report)
    else:
        log("Step 5/6  (skipped — --no-pdf)")

    for f in funds:
        finalise_missing(f)
    funds.sort(key=lambda f: (fundlist.CATEGORIES.index(f["category"]) if f["category"] in fundlist.CATEGORIES else 99, f["name"]))
    as_at = max((f["returns_as_at"] or f["price_date"] or "" for f in funds), default="") or date.today().isoformat()

    log("Step 6/6  Writing dataset, report and dashboard")
    dataset = write_outputs(funds, as_at, report, started)
    import build_dashboard
    build_dashboard.main()
    n_disc = sum("DISCREPANCY" in ln for ln in report)
    log(f"Done: {len(funds)} funds, data as at {as_at}, fact sheets as at {dataset['factsheets_as_at']}, "
        f"{n_disc} discrepancies, {len(report) - n_disc} notes -> data/refresh_report.md")
    return 0


if __name__ == "__main__":
    import requests
    try:
        sys.exit(main(sys.argv[1:]))
    except requests.RequestException as err:
        print(f"\n!! Network problem: {err}\n   Check the internet connection (corporate networks/VPNs "
              f"can block greateasternlife.com or newwealth.cloud) and run `python refresh.py` again.\n"
              f"   The previous dataset and dashboard were NOT modified.")
        sys.exit(1)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        print("\n!! Refresh failed before writing. The previous dataset and dashboard were NOT modified.")
        sys.exit(1)
