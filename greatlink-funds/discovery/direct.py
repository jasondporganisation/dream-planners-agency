import json, re, requests, datetime as dt
from pathlib import Path
OUT = Path(__file__).parent / "out"
H = "https://ge-fundcentersg.newwealth.cloud"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
      "Referer": "https://www.greateasternlife.com/", "Origin": "https://www.greateasternlife.com"}
s = requests.Session(); s.headers.update(UA)

# 1. Harvest JWT from the public JS bundle (no auth needed to fetch it)
jwt = None
for js in ["main.js"]:
    src = s.get(f"{H}/{js}", timeout=30).text
    m = re.search(r"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", src)
    if m: jwt = m.group(0); print("JWT harvested from", js, "len", len(jwt)); break
if not jwt:
    # fallback: scan all chunk files referenced by main.js
    for chunk in sorted(set(re.findall(r'"(\d+)\.js"', src)))[:60]:
        t = s.get(f"{H}/{chunk}.js", timeout=30).text
        m = re.search(r"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", t)
        if m: jwt = m.group(0); print("JWT harvested from", chunk+".js"); break
print("JWT found:", bool(jwt))

# 2. Typesense config (search-only key) — this endpoint needs the JWT
cfg = s.get(f"{H}/fund-center-api/ge/config/static", params={"config_type": "typesense_config"},
            headers={"Authorization": f"Bearer {jwt}"}, timeout=30)
print("config status", cfg.status_code); cfg = cfg.json(); ts_key = cfg["typesense_key"]["value"]

# 3. Screener: all GreatLink funds in one page
q = {"searches": [{"collection": "funds", "q": "", "query_by": "FundName", "per_page": 250, "page": 1,
      "filter_by": "ProductRange:=[`GreatLink funds`] && Status:=[`Active`]", "sort_by": "FundName:asc",
      "facet_by": "GlobalAssetClassName,RiskLevel,FundingSource,Currency"}]}
r = s.post(f"{H}/api/multi_search", json=q, headers={"X-TYPESENSE-API-KEY": ts_key}, timeout=30)
print("screener status", r.status_code)
res = r.json()["results"][0]; hits = [h["document"] for h in res["hits"]]
print("GreatLink funds found:", res["found"], "returned:", len(hits))
(OUT / "greatlink_screener.json").write_text(json.dumps(hits, indent=1))
for f in res["facet_counts"]:
    print("  facet", f["field_name"], [(c["value"], c["count"]) for c in f["counts"]])
for h in hits:
    d = dt.datetime.utcfromtimestamp(h["LastPriceDate"]).date() if h.get("LastPriceDate") else None
    print(f'  {h["FundCode"]:>5} {h["SecId"]:<11} {h["FundName"]:<52} {h["GlobalAssetClassName"]:<12} {h["Currency"]} YTD={h.get("YTD")} 1Y={h.get("ReturnM12")} 3Y={h.get("ReturnM36")} 5Y={h.get("ReturnM60")} 10Y={h.get("ReturnM120")} px={h.get("LastPrice")}@{d}')

# 4. Detail for Global Disruptive Innovation, direct
det = s.get(f"{H}/fund-center-api/ge/v4/funds", params={"code": "F00001DUL4_F224", "mode": "internal", "id_type": "composite", "lang": "en_sg"},
            headers={"Authorization": f"Bearer {jwt}"}, timeout=30)
print("detail status", det.status_code); det = det.json()
(OUT / "detail_F00001DUL4.json").write_text(json.dumps(det, indent=1))
print("Cumulative:", det["Performance"]["CumulativePerformance"])
print("Annualized:", det["Performance"]["AnnualizedReturn"])
print("Calendar:", [(x["key"], x["value"]) for x in det["Performance"]["CalendarPerformance"]["data"]])

# 5. Timeseries NAV: compute YTD & 1Y ourselves
ts = s.get(f"{H}/fund-center-api/api/v2/timeseries", params={"code": "F00001DUL4", "currency_id": "BAS", "id_type": "sec_id",
           "from_date": "2024-12-20", "to_date": "2026-08-23", "ts_type": "nav", "start_value": 100, "maximum": "false"},
           headers={"Authorization": f"Bearer {jwt}"}, timeout=30)
print("timeseries status", ts.status_code); tsj = ts.json()
(OUT / "timeseries_F00001DUL4.json").write_text(json.dumps(tsj, indent=1)[:200000])
print("timeseries top-level:", type(tsj).__name__, list(tsj.keys())[:10] if isinstance(tsj, dict) else len(tsj))
