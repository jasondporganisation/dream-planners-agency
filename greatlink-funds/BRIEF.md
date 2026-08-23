# GreatLink Fund Comparison Tool — Project Brief & Handoff

**Owner:** Jason Ng (Great Eastern Singapore financial representative)
**Branch:** `claude/greatlink-fund-dashboard-qps6zh`
**Status (23 Aug 2026):** Not started — the previous Claude Code session was blocked by the
environment's network policy (all requests to `greateasternlife.com` and `morningstar.com`
denied by the egress proxy). No code has been written yet. Verify network access first
(see "Preflight" below), then start at Phase 1.

## Preflight (do this first)

```bash
curl -sS -o /dev/null -w "%{http_code}\n" "https://www.greateasternlife.com/sg/en/personal-insurance/our-products/wealth-accumulation/investment-linked-funds/greatlink-funds.html"
curl -sS -o /dev/null -w "%{http_code}\n" "https://sg.morningstar.com/"
```

Both must return an HTTP status (200/30x), not a proxy CONNECT 403. If blocked, stop and
tell the user to open network access for the environment (allow all, or allowlist
`*.greateasternlife.com` and `*.morningstar.com`).

## The task

Build a **GreatLink Fund Comparison Tool** for Great Eastern (Singapore) financial
representatives to use when sitting with a client: pull the latest returns for every
GreatLink investment-linked fund, compare funds side by side, and open each fund's official
fund fact sheet with one click. Target machine: macOS, Python 3.11+. Everything lives in
this folder (`greatlink-funds/`).

### Deliverables ("done" looks like)

1. `python refresh.py` — one command: downloads latest data for all GreatLink funds and
   every fund's fact sheet PDF, then rebuilds the dashboard.
2. `dashboard.html` — single self-contained file (CSS/JS inline, data embedded), opens
   offline with no server; if emailed on its own, fact sheet buttons fall back to the
   online PDF links.
3. `data/funds.json` and `data/funds.csv` — the clean dataset.
4. `factsheets/` — local copy of every fund's latest fact sheet PDF, clearly named
   (e.g. `greatlink-global-equity-fund.pdf`).
5. `README.md` — plain-English setup/refresh/share instructions for a non-technical agent.

### Scope — GreatLink range only (~40 funds, six categories, as at Aug 2026)

Completeness check list (all names prefixed "GreatLink"); include any new fund found that
is not listed here:

- **Global Equity (10):** Global Disruptive Innovation, Global Equity Alpha, Global Equity,
  Global Perspective, Global Real Estate Securities, Global Technology, International
  Health Care, Lifestyle Dynamic Portfolio, Multi-Theme Equity, Sustainable Global Thematic
- **Regional Equity (7):** ASEAN Growth, Asia Dividend Advantage, Asia High Dividend
  Equity, Asia Pacific Equity, Far East Ex Japan Equities, Global Emerging Markets Equity,
  European Sustainable Equity
- **Single Country Equity (5):** Singapore Equities, Lion India, Lion Japan Growth,
  Lion Vietnam, China Growth
- **Mixed Asset (12):** Income Focus, Diversified Growth Portfolio, Global Supreme,
  Lifestyle Balanced / Progressive / Secure / Steady Portfolios, Lion Asian Balanced,
  US Income and Growth (Dis), Dynamic Secure / Balanced / Growth Portfolios
- **Money Markets and Bonds (5):** Cash, Global Bond, Income Bond, Multi-Sector Income,
  Short Duration Bond
- **Commodities (1):** Singapore Physical Gold

Not in scope: the Prestige Portfolio range.

### Data sources (verified by the owner)

- **Fund list by category:**
  https://www.greateasternlife.com/sg/en/personal-insurance/our-products/wealth-accumulation/investment-linked-funds/greatlink-funds.html
  — each fund links into the ILP Fund Centre with a Morningstar-style ID, e.g.
  `ilp-fund-centre.html#/detail?id=F00001DUL4_F224` (Global Disruptive Innovation),
  `#/detail?id=F0HKG07069_F19` (Global Equity Alpha). Harvest every fund's ID here.
- **ILP Fund Centre (main data source):**
  https://www.greateasternlife.com/sg/en/personal-insurance/our-products/wealth-accumulation/investment-linked-funds/ilp-fund-centre.html
  — Morningstar-powered SPA (renders nothing without JS). Screener has returns for all
  periods; each detail view links documents (fund fact sheet, product highlights sheet…).
- **Fact sheets:** monthly PDFs from Morningstar's doc service, e.g.
  `https://doc.morningstar.com/document/<id>.msdoc/?clientid=imassg&key=...`
  URLs may change monthly — always re-harvest and download local copies.
- **Fund prices (bid/offer, historical, by-date lookup):**
  https://www.greateasternlife.com/sg/en/personal-insurance/our-products/wealth-accumulation/great-invest-advantage/greatlink-funds-prices.html
- **Backups:** compiled GreatLink overview PDF (1Y/5Y ann. returns, objective, risk class):
  https://www.greateasternlife.com/content/dam/corp-site/great-eastern/sg/gels-ftrp-imc-cm/wealth-accumulation/great-invest-advantage/gels-pdt-gia-complete-greatlink-funds.pdf ;
  annual/semi-annual reports:
  https://www.greateasternlife.com/sg/en/personal-insurance/our-products/wealth-accumulation/great-invest-advantage/annual-reports.html ;
  Morningstar SG fund pages, e.g.
  https://sg.morningstar.com/sg/report/fund/performance.aspx?t=0P00008T87 (Singapore Equities).

### Phase 1 — Discovery (do first, then PAUSE and report to the user)

1. Playwright (headless Chromium) on the ILP Fund Centre; record all network requests
   while the screener and one fund detail page load. Find the JSON/API endpoints for
   (a) fund list, (b) trailing + calendar-year returns, (c) portfolio data (asset/country/
   sector allocation, top holdings), (d) document links. Prefer calling endpoints directly
   from Python.
2. If endpoints are signed/not reusable, fall back to driving the SPA and reading rendered
   tables. Last resort for returns: parse fact sheet PDFs with `pdfplumber`.
3. **Pause.** Show the user: endpoints found, one fully-populated sample fund record,
   fund count vs ~40 expected, and any unsourceable fields. Wait for their OK.

### Phase 2 — Data model (per fund, with "as at" date for every figure)

- Identity: name, category, Morningstar/Fund Centre ID, GE fund page URL, Fund Centre detail URL.
- Key facts: manager, underlying fund, inception date, fund size, currency, management fee,
  risk classification, CPF-OA / CPF-SA / SRS / cash eligibility, latest bid/offer price + price date.
- Returns (%): YTD, 1m, 3m, 6m, 1y, 3y, 5y, 10y, since inception. Annualised vs cumulative
  stored separately and labelled (`ret_5y_ann`, `ret_5y_cum`). Calendar-year returns for
  ≥10 years. Benchmark returns per period where available.
- Allocations: asset, geographic/country, sector; top 10 holdings (name + weight).
- Documents: fact sheet URL (online), local path, PHS URL, other docs, fact sheet "as at" date.
- Bookkeeping: source per figure + fetch timestamp.

Rules: returns are bid-to-bid, in fund currency (SGD for nearly all), net of fund management
fee, excluding policy charges — record currency per fund and state the convention in the UI.
Never invent numbers; unavailable → null, UI shows "n/a – launched MMM YYYY". If two sources
disagree by >0.1pp, keep the Fund Centre figure and log to `data/refresh_report.md`.

### Phase 3 — Dashboard (`dashboard.html`)

For an agent showing an iPad/laptop to a client: clean, large type, GE-style neutral palette,
responsive, all inline (no CDN).

- **Overview table:** one row per fund; columns Fund, Category, Risk, YTD, 1Y, 3Y (ann.),
  5Y (ann.), 10Y (ann.), Since inception, Bid price, Fund size, Mgmt fee, Fact sheet button.
  Sortable every column, default YTD desc; positive green / negative red with in-cell bars;
  rank badges; filters (category multi-select, risk, CPF-OA/SA/SRS, free-text) with match
  count; "Category leaders" strip (best YTD + best 5Y per category).
- **Compare mode:** tick 2–5 funds → side-by-side grouped bar chart of returns, key-facts
  table, allocation breakdowns. "Copy table" (clean text for WhatsApp/email) and
  "Print / Save as PDF" with print stylesheet (1–2 A4 pages incl. disclaimer).
- **Fund detail panel:** objective, key facts, full returns (trailing + calendar-year,
  benchmark), allocation charts (donut/horizontal bars), top-10 holdings; prominent
  "Open Fund Fact Sheet" button (local PDF, fallback to online link), plus PHS and
  "View on Great Eastern site" links.
- **Trust/compliance:** "Data as at DD MMM YYYY" header + per-fund fact sheet date; yellow
  stale-data banner if >45 days old; persistent footer disclaimer (short everywhere, full in
  print): "Past performance is not necessarily indicative of future performance. Returns are
  bid-to-bid in the fund currency, net of fund management fees, and exclude policy charges.
  Fund values may rise or fall. This is an internal reference tool for Great Eastern
  financial representatives; it is not an offer or a recommendation, and clients must be
  given the official fund fact sheet, product highlights sheet and product summary.
  Source: Great Eastern Life / Morningstar." No projections, no expected-return, no
  rating/recommendation language. "Client view" toggle hides internal columns.

### Phase 4 — `refresh.py`

Single command, no args; per-fund progress; polite scraping (delays, retries w/ backoff,
realistic UA, same-day caching of unchanged PDFs). Writes `data/funds.json` + `.csv`,
downloads PDFs to `factsheets/`, regenerates `dashboard.html` via `build_dashboard.py` +
`templates/dashboard.html`. Ends with `data/refresh_report.md` (processed, failures + why,
missing fields, discrepancies, overall as-at date). Write to temp + swap so a half-failed
run never destroys the previous good dataset. Keep dated JSON copies in `data/history/`.

### Phase 5 — Verification before handover

- Open three fact sheet PDFs (equity, bond, mixed) and check dashboard YTD/1Y/5Y match
  exactly; show the comparison.
- Confirm every fund's fact sheet button works (local + online); list missing documents.
- Headless-browser screenshots: overview table, compare view, fund detail panel.
- Unit tests for parsers: "12.34%", "-3.1%", "n.a.", annualised vs cumulative labels,
  dates like "as at 29 May 2026".

### Ways of working

Python 3.11+, Playwright, `requests`, `pdfplumber`; vanilla JS, small inline charts, no
frameworks. Structure: `refresh.py`, `scraper/` (fund list, fund centre, prices, documents),
`build_dashboard.py`, `templates/dashboard.html`, `tests/`, `data/`, `factsheets/`.
If the GE site blocks automation or Morningstar endpoints need a token that can't be
obtained legitimately, stop and present options. After Phase 1 approval, run Phases 2–5
without further check-ins unless blocked. Finish with exact fresh-Mac setup commands and
monthly refresh instructions.
