# GreatLink Fund Dashboard

Scraper + offline dashboard for Great Eastern's ~40 GreatLink ILP sub-funds.

Great Eastern's fund data is **not** in plain HTML: the public pages only list
fund names by category, while returns, prices and documents live in the
[ILP Fund Centre](https://www.greateasternlife.com/sg/en/personal-insurance/our-products/wealth-accumulation/investment-linked-funds/ilp-fund-centre.html),
a Morningstar-powered JavaScript app. Fact sheets are monthly PDFs served from
Morningstar's document service (`doc.morningstar.com`, client id `imassg`).
So this project scrapes in three phases, with a **deliberate review checkpoint
after Phase 1**.

## Setup

```bash
cd greatlink-fund-dashboard
npm install            # installs playwright
npx playwright install chromium   # if no system Chromium is available
```

> ⚠️ Requires outbound network access to `greateasternlife.com` and
> `*.morningstar.com`. Managed/remote Claude environments with a restricted
> network policy will fail at Phase 1 — run these scripts on a machine with
> normal internet access.

## Phase 1 — Discover (then STOP and review)

```bash
npm run discover
```

Drives a headless browser through the ILP Fund Centre, records every
Morningstar/fund API response, and writes:

- `discovery/endpoints.json` — all captured endpoints
- `discovery/samples/*.json` — raw response bodies
- `discovery/report.md` — **the checkpoint**: endpoints found, one sample
  fund record, and the fund count vs the ~40 expected

**Review `discovery/report.md` before continuing.** If the fund count is far
off 40, the list is probably paginated — fix the endpoint (bump `pageSize`,
iterate `page`) via `scripts/config.json`:

```json
{
  "fundListUrl": "https://…screener endpoint…&pageSize=100",
  "fieldMap": { "name": "LegalName", "ytd": "ReturnM0" }
}
```

`fieldMap` is only needed if the auto-detection in `scripts/scrape.mjs`
(which tries common Morningstar keys like `SecId`, `LegalName`, `ReturnM12`)
doesn't match the real payload.

## Phase 2 — Scrape

```bash
npm run scrape
```

Normalizes the fund list into `data/funds.json` and `dashboard/data.js`
(returns YTD/1Y/3Y/5Y/10Y/since-inception, calendar-year returns where the
payload carries them, prices, fees, fund size). The full raw record is kept
under each fund's `raw` key so nothing is silently dropped.

## Phase 3 — Fact sheets

```bash
npm run factsheets
```

Downloads every fund's fact sheet PDF into `data/factsheets/` so the
dashboard's "Open Fact Sheet" button works offline. The online Morningstar
URL is kept as a fallback so the dashboard still works if you email it to a
colleague without the PDFs.

## Dashboard

Open `dashboard/index.html` in any browser — no server needed. It ships with
**clearly labelled sample data** (banner at the top) until the scraper has
run. Features:

- Sortable table: bid price, YTD / 1Y / 3Y / 5Y / 10Y / since-inception
  returns, category filter, search
- Click a fund name for calendar-year returns, fund facts and the fact sheet
- **Compare mode**: select 2–5 funds → side-by-side comparison → print /
  save as PDF (comparison only, with disclaimer)
- **Client view** toggle: hides internal columns (management fee, fund size,
  risk grade, internal notes)
- **Data freshness warning** when the newest price is older than 45 days
- Standing compliance footer: past performance disclaimer, bid-to-bid basis
  with dividends reinvested, no ratings or recommendation language anywhere

## Layout

```
scripts/discover.mjs            Phase 1 — Playwright endpoint discovery
scripts/scrape.mjs              Phase 2 — build dataset from discovered API
scripts/download-factsheets.mjs Phase 3 — local fact sheet PDFs
scripts/lib.mjs                 shared IO + mapping helpers
data/funds.sample.json          labelled sample dataset
data/funds.json                 (generated) real dataset
data/factsheets/                (generated) local PDFs
dashboard/index.html            the dashboard (self-contained)
dashboard/data.js               dataset as a JS global (generated; ships as sample)
discovery/                      (generated) Phase 1 output
```
