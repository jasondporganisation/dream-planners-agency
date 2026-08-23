# Phase 1 — Discovery report (23 Aug 2026)

**Preflight:** PASS — `greatlink-funds.html` → HTTP 302 (→ `greatlink-dynamic-portfolios.html`), `sg.morningstar.com` → 301. No proxy block.

**Headline:** the ILP Fund Centre is not Morningstar-hosted — it is a white-label fund centre at
`https://ge-fundcentersg.newwealth.cloud` (Morningstar data underneath). Every field the brief needs
is available from **plain JSON endpoints callable directly from Python** — no browser needed for the
monthly refresh. Playwright was only needed for this discovery. All 40 GreatLink funds found (40/40
vs. the brief's list, same six categories and counts).

## Endpoints found

| # | Purpose | Endpoint | Auth | Verified from Python |
|---|---|---|---|---|
| A | **Fund list + 6 GE categories + composite IDs** | `GET https://www.greateasternlife.com/sg/en/personal-insurance/our-products/wealth-accumulation/investment-linked-funds/greatlink-funds.html` (302 → `greatlink-dynamic-portfolios.html`) — `<h3>` category headings, anchors `ilp-fund-centre.html#/detail?id=<SecId>_<FundCode>` | none | ✅ 40 IDs, 10/7/5/12/5/1 |
| B | **Screener — returns for all funds in one call** | `POST https://ge-fundcentersg.newwealth.cloud/api/multi_search` (Typesense). Body: `{"searches":[{"collection":"funds","q":"","query_by":"FundName","per_page":250,"filter_by":"ProductRange:=[`GreatLink funds`] && Status:=[`Active`]"}]}` | header `X-TYPESENSE-API-KEY` = search-only key from (C) | ✅ found=40 |
| C | Typesense search key | `GET https://ge-fundcentersg.newwealth.cloud/fund-center-api/ge/config/static?config_type=typesense_config` → `typesense_key.value` | none | ✅ |
| D | **Fund detail** (objective, AUM, fees, risk, CPF/SRS, calendar-year returns, asset/geo/sector allocation, top holdings, all document links with effective dates, benchmark *name*) | `GET https://ge-fundcentersg.newwealth.cloud/fund-center-api/ge/v4/funds?code=<SecId>_<FundCode>&mode=internal&id_type=composite&lang=en_sg` | none | ✅ |
| E | **NAV history** (daily bid price series back to inception) | `GET https://ge-fundcentersg.newwealth.cloud/fund-center-api/api/v2/timeseries?code=<SecId>&currency_id=BAS&id_type=sec_id&from_date=YYYY-MM-DD&to_date=YYYY-MM-DD&ts_type=nav&start_value=100&maximum=false` | none | ✅ 1,266 pts for Global Equity since Aug 2021; series goes back to inception |
| F | **Bid/offer prices** | `GET https://www.greateasternlife.com/bin/corp-site/fund-prices.json?name=gDaily&mode=daily` → `funds[]` with `fundCode`, `fundBidPrice`, `fundOfferPrice`, `fundValueDate`, `fundCPFApproved` | none | ✅ 48 funds, 40 GreatLink, as at 2026-08-20 |
| G | **Fact sheet / PHS / prospectus / reports PDFs** | Morningstar doc URLs from (B)/(D): `https://doc.morningstar.com/Document/<hash>.msdoc/?key=<key>` | key is in the URL | ✅ 3/3 PDFs downloaded (150 KB / 82 KB / 257 KB), "as at 30 June 2026" |

Auth notes: the browser sends a `Bearer` JWT (`ROLE_FRONT_TOKEN`, public, expires 2029, embedded in
GE's public `ilp-fund-centre.html`), but (C)(D)(E) answer **without any auth**. Only (B) needs the
Typesense key, which (C) hands out unauthenticated. Nothing here requires credentials that a normal
site visitor doesn't receive. Screener and detail also work with a plain `requests` UA + Referer.

## Field-name semantics (verified against NAV recomputation, 3 funds, to 2 dp)

- Screener `YTD`, `ReturnM1/M3/M6/M12` = **cumulative**; `ReturnM36/M60/M120/MAX` = **annualised**.
  Detail `Performance.AnnualizedReturn` is the same block (same numbers).
- Detail `Performance.CumulativePerformance` is **wrong/unrelated** (e.g. Global Disruptive Innovation
  YTD −14.0% vs NAV-derived +5.64%; Global Equity −4.5% vs +9.51%). Will be ignored.
- Cumulative 3Y/5Y/10Y/SI (brief wants `ret_5y_cum` alongside `ret_5y_ann`) will be **recomputed
  from the NAV series (E)** — matches the annualised figures exactly when re-annualised.
- `LastPrice` in screener = **bid** price (equals `fundBidPrice` in F). Offer = bid × 1.0526 (5% charge).
- `FundCode` `F07` ↔ prices `fundCode` `"07"`.
- Fact-sheet performance table (pdfplumber `extract_tables`) yields rows
  `["GreatLink Global Equity Fund 12.70% 8.61% 23.64% 17.35% 9.47% 11.25% 3.88%"]` and
  `["Benchmark 14.05% …"]` with columns 3M/6M/1Y/3Y*/5Y*/10Y*/SI* (`*` = annualised). **No YTD column.**

## Sample fully-populated record

`discovery/sample_fund_record.json` — GreatLink Global Equity Fund, every Phase 2 field filled
(identity, key facts incl. bid/offer, all returns ann+cum, 10 calendar years, allocations, top
holdings, 5 document URLs with fact-sheet as-at date, per-field source + timestamp).

## Fund count vs expected

40 found / ~40 expected. Category split from GE page = brief exactly. No fund on the site that is
missing from the brief; no brief fund missing from the site. Prestige (96) and Max (8) ranges
excluded by the `ProductRange` filter.

## Unsourceable / partially sourced fields

| Field | Status |
|---|---|
| Benchmark **returns** per period | Not in API (only benchmark *name*, e.g. "MSCI World NR USD"). Source = fact-sheet PDF table (parseable, 3 of 3 worked). As-at will be the fact-sheet date, not the API date. |
| ISIN | Empty for all 40 (ILP sub-funds have none). Drop. |
| Underlying fund name | `UnderlyingFund` empty in API; derivable from top holding (99%+ single line) and printed on fact sheet. Will take fact-sheet value when parsed, else top holding. |
| Management fee | API has `AnnualManagementFee`, `ActualManagementFee`, `CustomManagementFee`, `ExpenseRatio`. They differ for Lifestyle portfolios (2.0 / 2 / 1.27 / 1.39). Will show `AnnualManagementFee` and label it; cross-check vs fact sheet in Phase 5. |
| Returns for young funds (genuinely n/a) | 10Y missing ×12, 5Y ×9, 3Y ×6, 1Y ×4 (3 Dynamic Portfolios + Physical Gold, launched 2026), YTD ×1 (Physical Gold). UI will show "n/a – launched MMM YYYY" per brief. |
| Fact-sheet "as at" | Fact sheets are **30 June 2026** while API returns are **as at 20 Aug 2026** (~7-week lag, normal monthly cycle). |

## Things for Jason to decide (the pause)

1. **Phase 5 check "dashboard YTD/1Y/5Y match fact sheet exactly" can't be literal** — the dashboard
   will be as at 20 Aug, the fact sheet 30 Jun, and the fact sheet has no YTD. Proposed: the
   verifier recomputes 1Y/3Y/5Y **at the fact-sheet date** from the NAV series and compares those
   to the PDF (that is an exact, like-for-like test), and the dashboard shows both dates.
2. Benchmark returns come only from PDFs (as at fact-sheet date). OK to show them with their own
   as-at label, or leave benchmarks out of the overview and keep them in the detail panel only?
3. The existing sibling branch `claude/great-eastern-fund-scraper-6ia69d` has a full but *blind*
   implementation (~4,100 lines incl. dashboard template, tests, README) written without network
   access. Plan: reuse its dashboard template / build / README structure, **replace** its guessed
   scraper with the real endpoints above. Say if you'd rather start clean.

Artifacts: `discovery/record.py` (Playwright recorder), `discovery/direct.py` (pure-requests proof),
`discovery/out/greatlink_screener.json` (all 40 screener docs), `discovery/sample_fund_record.json`.
Raw captures (`discovery/out/`) are git-ignored.
