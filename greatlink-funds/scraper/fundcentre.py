"""Step 2: the ILP Fund Centre (Morningstar-powered SPA).

The Fund Centre renders nothing without JavaScript, so:

  1. discover()  — drive headless Chromium once, record every JSON response
     the app makes while the screener and one fund detail view load, classify
     the endpoints (fund list / returns / portfolio / documents), and save
     them to data/endpoints.json with the sample fund's id so per-fund URLs
     can be templated.  This also produces the Phase 1 checkpoint report.
  2. fetch()     — call those endpoints directly from Python (fast, reliable),
     substituting each fund's id into the templated URLs.

If the endpoints turn out to be signed/non-reusable, fetch() reports the
failure per fund in the refresh report rather than silently dropping data;
the pdfplumber fact sheet parser (factsheet_pdf.py) is the last-resort source
for returns.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .fundlist import FUND_CENTRE_URL
from .util import PoliteSession, classify_period_label, parse_asat_date, parse_pct

INTERESTING = re.compile(
    r"morningstar\.com|api/rest\.svc|screener|securit(y|ies)|msdoc|imassg|"
    r"fundcentre|fund-centre", re.I)

# Candidate payload keys per canonical field (Morningstar APIs vary by client).
CANDIDATES = {
    "fund_id": ["SecId", "secId", "Id", "fundId"],
    "name": ["LegalName", "Name", "FundName", "legalName", "name"],
    "isin": ["ISIN", "Isin", "isin"],
    "currency": ["PriceCurrency", "Currency", "CurrencyId", "currency"],
    "bid_price": ["ClosePrice", "BidPrice", "NAV", "price", "bid"],
    "offer_price": ["OfferPrice", "offer"],
    "price_date": ["ClosePriceDate", "PriceDate", "priceDate", "EndDate"],
    "fund_size_raw": ["FundSize", "AverageMarketCapital", "NetAssets", "fundSize"],
    "mgmt_fee_pct": ["ManagementFee", "AnnualManagementCharge", "OngoingCharge",
                     "ExpenseRatio", "managementFee"],
    "inception_date": ["InceptionDate", "inceptionDate"],
    "manager": ["ManagerName", "FundManager", "AdministratorCompanyName", "manager"],
    "risk_class": ["RiskClassification", "RiskGrade", "CollectedSRRI", "riskRating"],
    "benchmark_name": ["BenchmarkName", "PrimaryBenchmark", "benchmark"],
    "ret_ytd": ["ReturnM0", "GBRReturnM0", "YTDReturn"],
    "ret_1m": ["ReturnM1", "GBRReturnM1"],
    "ret_3m": ["ReturnM3", "GBRReturnM3"],
    "ret_6m": ["ReturnM6", "GBRReturnM6"],
    "ret_1y": ["ReturnM12", "GBRReturnM12"],
    "ret_3y_ann": ["ReturnM36", "GBRReturnM36"],
    "ret_5y_ann": ["ReturnM60", "GBRReturnM60"],
    "ret_10y_ann": ["ReturnM120", "GBRReturnM120"],
    "ret_si_ann": ["ReturnLongestTenure", "ReturnSinceInception", "SinceInception"],
}

RETURN_KEYS = [k for k in CANDIDATES if k.startswith("ret_")]


def _pick(record: dict, field: str):
    lower = {k.lower(): k for k in record}
    for cand in CANDIDATES[field]:
        key = lower.get(cand.lower())
        if key is not None and record[key] not in (None, ""):
            return record[key]
    return None


def largest_object_array(node, best=None):
    if best is None:
        best = {"arr": None, "len": 0}
    if isinstance(node, list):
        if len(node) > best["len"] and all(isinstance(x, dict) for x in node):
            best["arr"], best["len"] = node, len(node)
        for item in node:
            largest_object_array(item, best)
    elif isinstance(node, dict):
        for v in node.values():
            largest_object_array(v, best)
    return best


def looks_like_fund_list(arr) -> bool:
    if not arr or len(arr) < 3:
        return False
    keys = {k.lower() for k in arr[0]}
    return any("name" in k for k in keys) and any(
        k in keys for k in ("secid", "isin", "id", "fundid"))


# ------------------------------------------------------------- discovery

def discover(data_dir: Path, sample_fund_id: str | None = None) -> dict:
    """Drive the SPA once; classify and persist the endpoints it calls.

    Requires playwright + Chromium and network access to greateasternlife.com
    and *.morningstar.com. Writes data/endpoints.json and
    data/discovery_report.md; returns the report as a dict.
    """
    from playwright.sync_api import sync_playwright

    captured: list[dict] = []
    samples_dir = data_dir / "discovery_samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    def on_response(res):
        url = res.url
        if not INTERESTING.search(url):
            return
        entry = {
            "url": url,
            "method": res.request.method,
            "status": res.status,
            "content_type": res.headers.get("content-type", ""),
            "post_data": res.request.post_data,
            "sample_file": None,
            "phase": current_phase[0],
        }
        try:
            if "json" in entry["content_type"] or "javascript" in entry["content_type"]:
                body = res.text()
                fname = f"sample-{len(captured):03d}.json"
                (samples_dir / fname).write_text(body, encoding="utf-8")
                entry["sample_file"] = f"discovery_samples/{fname}"
        except Exception:
            pass
        captured.append(entry)

    current_phase = ["screener"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("response", on_response)

        page.goto(FUND_CENTRE_URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(6_000)
        for _ in range(4):
            page.mouse.wheel(0, 1500)
        page.wait_for_timeout(3_000)

        if sample_fund_id:
            current_phase[0] = "detail"
            page.goto(f"{FUND_CENTRE_URL}#/detail?id={sample_fund_id}",
                      wait_until="networkidle", timeout=120_000)
            page.wait_for_timeout(6_000)
            # Poke tabs that lazy-load returns/portfolio/documents.
            for label in ("Performance", "Portfolio", "Documents", "Price"):
                try:
                    el = page.locator(f"text=/{label}/i").first
                    if el.is_visible(timeout=1_000):
                        el.click(timeout=2_000)
                        page.wait_for_timeout(2_500)
                except Exception:
                    pass
        browser.close()

    endpoints = _classify(captured, samples_dir, sample_fund_id)
    (data_dir / "endpoints.json").write_text(
        json.dumps(endpoints, indent=2), encoding="utf-8")
    report = _write_report(data_dir, captured, endpoints, samples_dir)
    return report


def _classify(captured, samples_dir: Path, sample_fund_id) -> dict:
    """Assign roles to captured endpoints; template detail URLs on the fund id."""
    endpoints = {"fund_list": None, "returns": [], "portfolio": [],
                 "documents": [], "other": [], "sample_fund_id": sample_fund_id}
    best_list_len = 0
    for e in captured:
        role = "other"
        body = None
        if e["sample_file"]:
            try:
                body = json.loads((samples_dir.parent / "discovery_samples" /
                                   Path(e["sample_file"]).name).read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                body = None
        if body is not None:
            best = largest_object_array(body)
            if looks_like_fund_list(best["arr"]) and best["len"] > best_list_len:
                endpoints["fund_list"] = dict(e)
                best_list_len = best["len"]
                continue
            text = json.dumps(body).lower()
            if re.search(r"calendar|trailing|return", text) and e["phase"] == "detail":
                role = "returns"
            elif re.search(r"holding|allocation|sector|country|weight", text):
                role = "portfolio"
            elif re.search(r"msdoc|document|factsheet|\.pdf", text + e["url"].lower()):
                role = "documents"
        elif re.search(r"msdoc|document", e["url"], re.I):
            role = "documents"
        entry = dict(e)
        if sample_fund_id and sample_fund_id in entry["url"]:
            entry["url_template"] = entry["url"].replace(sample_fund_id, "{fund_id}")
        endpoints[role if role in endpoints else "other"].append(entry)
    return endpoints


def _write_report(data_dir: Path, captured, endpoints, samples_dir: Path) -> dict:
    fund_count = 0
    sample_record = None
    if endpoints["fund_list"] and endpoints["fund_list"].get("sample_file"):
        try:
            body = json.loads((data_dir / endpoints["fund_list"]["sample_file"])
                              .read_text(encoding="utf-8"))
            best = largest_object_array(body)
            fund_count = best["len"]
            sample_record = best["arr"][0] if best["arr"] else None
        except (json.JSONDecodeError, OSError):
            pass

    lines = ["# Phase 1 discovery report — ILP Fund Centre", ""]
    lines.append(f"Captured {len(captured)} matching endpoints "
                 f"(bodies in `data/discovery_samples/`).")
    lines.append("")
    for role in ("fund_list", "returns", "portfolio", "documents"):
        val = endpoints[role]
        items = [val] if isinstance(val, dict) else (val or [])
        lines.append(f"## {role} ({len([i for i in items if i])})")
        for item in items:
            if item:
                lines.append(f"- `{item['method']} {item.get('url_template', item['url'])}`"
                             f" ({item['status']})")
        lines.append("")
    lines.append(f"## Fund count: {fund_count} (expected ~40)")
    if fund_count and abs(fund_count - 40) > 8:
        lines.append("> WARNING: far from the ~40 expected — likely pagination; "
                     "check page/pageSize parameters on the fund_list endpoint.")
    lines.append("")
    if sample_record:
        lines.append("## Sample fund record")
        lines.append("```json")
        lines.append(json.dumps(sample_record, indent=2)[:4000])
        lines.append("```")
    else:
        lines.append("> WARNING: no fund-list-shaped response found. Inspect "
                     "`data/discovery_samples/` manually.")
    text = "\n".join(lines)
    (data_dir / "discovery_report.md").write_text(text, encoding="utf-8")
    return {"endpoint_count": len(captured), "fund_count": fund_count,
            "sample_record": sample_record, "report_path": str(data_dir / "discovery_report.md"),
            "report_text": text}


# ------------------------------------------------------------- fetching

def fetch_fund_list(session: PoliteSession, endpoints: dict) -> list[dict]:
    ep = endpoints.get("fund_list")
    if not ep:
        raise RuntimeError("No fund_list endpoint discovered — run discovery first.")
    res = session.get(ep["url"], headers={"Accept": "application/json"})
    res.raise_for_status()
    best = largest_object_array(res.json())
    return best["arr"] or []


def fetch_detail(session: PoliteSession, endpoints: dict, fund_id: str) -> dict:
    """Fetch templated detail endpoints for one fund; returns raw bodies by role."""
    out = {}
    for role in ("returns", "portfolio", "documents"):
        for ep in endpoints.get(role, []):
            template = ep.get("url_template")
            if not template:
                continue
            try:
                res = session.get(template.format(fund_id=fund_id),
                                  headers={"Accept": "application/json"})
                if res.status_code == 200:
                    out.setdefault(role, []).append(res.json())
            except Exception as err:  # noqa: BLE001 — recorded, not fatal per fund
                out.setdefault(f"{role}_errors", []).append(str(err))
    return out


# ------------------------------------------------------------- normalising

def normalize_screener_row(record: dict) -> dict:
    """Map one screener row onto canonical fields; keeps the raw record."""
    out = {"raw_screener": record}
    for field in ("fund_id", "name", "isin", "currency", "manager", "risk_class",
                  "benchmark_name"):
        out[field] = _pick(record, field)
    out["bid_price"] = parse_pct(_pick(record, "bid_price"))  # plain float parse
    out["offer_price"] = parse_pct(_pick(record, "offer_price"))
    out["price_date"] = parse_asat_date(_pick(record, "price_date"))
    out["inception_date"] = parse_asat_date(_pick(record, "inception_date"))
    out["mgmt_fee_pct"] = parse_pct(_pick(record, "mgmt_fee_pct"))
    from .util import parse_money_millions
    out["fund_size_m"] = parse_money_millions(_pick(record, "fund_size_raw"))
    out["returns"] = {k: parse_pct(_pick(record, k)) for k in RETURN_KEYS}
    out["calendar_year_returns"] = {
        m.group(1): parse_pct(v)
        for k, v in record.items()
        if (m := re.search(r"(?:return|cy)[^0-9]*?(20\d{2})$", k, re.I))
        and parse_pct(v) is not None
    }
    return out


def extract_allocations(portfolio_bodies: list) -> dict:
    """Best-effort extraction of asset/geo/sector allocations and holdings from
    portfolio endpoint payloads. Unmapped payloads are reported, not guessed."""
    out = {"allocation_asset": [], "allocation_geo": [], "allocation_sector": [],
           "top_holdings": []}
    for body in portfolio_bodies or []:
        text_keys = json.dumps(body).lower()
        best = largest_object_array(body)
        arr = best["arr"] or []
        if not arr:
            continue
        keys = {k.lower() for k in arr[0]}
        has_weight = any(k in keys for k in ("weight", "weighting", "percent", "value"))
        has_name = any("name" in k or "label" in k for k in keys)
        if not (has_weight and has_name):
            continue
        rows = []
        for item in arr[:25]:
            name = next((item[k] for k in item if "name" in k.lower() or "label" in k.lower()), None)
            weight = next((parse_pct(item[k]) for k in item
                           if k.lower() in ("weight", "weighting", "percent", "value")), None)
            if name and weight is not None:
                rows.append({"label": str(name), "pct": weight})
        if not rows:
            continue
        if "holding" in text_keys:
            out["top_holdings"] = rows[:10]
        elif re.search(r"country|region|geograph", text_keys):
            out["allocation_geo"] = rows
        elif "sector" in text_keys:
            out["allocation_sector"] = rows
        else:
            out["allocation_asset"] = rows
    return out


def extract_documents(document_bodies: list) -> dict:
    """Pull fact sheet / PHS URLs and the fact sheet 'as at' date."""
    out = {"factsheet_url": None, "factsheet_as_at": None, "phs_url": None, "other": []}
    for body in document_bodies or []:
        best = largest_object_array(body)
        for item in best["arr"] or []:
            blob = json.dumps(item)
            urls = re.findall(r"https?://[^\s\"']+", blob)
            url = next((u for u in urls if "msdoc" in u or u.lower().endswith(".pdf")), None)
            if not url:
                continue
            label = blob.lower()
            asat = parse_asat_date(blob)
            if re.search(r"fact\s*sheet|factsheet", label) and not out["factsheet_url"]:
                out["factsheet_url"] = url
                out["factsheet_as_at"] = asat
            elif re.search(r"product highlight|phs", label) and not out["phs_url"]:
                out["phs_url"] = url
            else:
                out["other"].append(url)
    return out
