# GreatLink Fund Comparison Tool

A client-meeting tool for Great Eastern (Singapore) financial representatives.
One command pulls the latest returns for all 40 GreatLink investment-linked
funds plus every fund's official fact sheet PDF, and rebuilds
`dashboard.html` — a single file that opens on any Mac, iPad (AirDrop / Files)
or laptop with no server and no internet needed after a refresh.

> **Internal reference tool.** It shows facts only — no projections, ratings or
> recommendations — and every view carries the past-performance disclaimer.
> Clients must still be given the official fund fact sheet, product highlights
> sheet and product summary.

**Where the numbers come from** — Great Eastern's ILP Fund Centre (Morningstar
data), Great Eastern's daily price feed, and the official monthly fact sheets.
Returns are bid-to-bid in SGD, net of fund management fees, excluding policy
charges. YTD / 1M / 3M / 6M / 1Y are cumulative; 3Y / 5Y / 10Y / since-inception
are annualised (cumulative versions are also stored and shown in the detail
panel). Nothing is ever estimated: a figure the source does not publish shows
as "n/a – launched MMM YYYY".

---

## One-time setup on a fresh Mac (about 5 minutes)

Open **Terminal** (press `Cmd-Space`, type "Terminal", press Enter) and paste
these lines one at a time.

```bash
# 1. Python 3.11 or newer must be installed (macOS ships with it via Xcode
#    Command Line Tools; otherwise install from https://www.python.org/downloads/)
python3 --version
```

```bash
# 2. Go to this folder (drag the greatlink-funds folder onto the Terminal
#    window after typing "cd " if you are not sure of the path)
cd ~/workspace/dream-planners-agency/greatlink-funds
```

```bash
# 3. Create a private Python environment and install the three libraries
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

```bash
# 4. Install the headless browser used only for the verification screenshots (one-off, ~120 MB)
python -m playwright install chromium
```

```bash
# 5. First refresh (2–3 minutes) — then open dashboard.html
python refresh.py && open dashboard.html
```

## Monthly refresh (do this after the new fact sheets come out, ~2nd week of the month)

```bash
cd ~/workspace/dream-planners-agency/greatlink-funds && source .venv/bin/activate && python refresh.py
```

That single command:

1. reads the fund list and the six GreatLink categories from greateasternlife.com,
2. pulls returns, prices, risk class, CPF/SRS eligibility and document links for
   all GreatLink funds from the Fund Centre,
3. pulls each fund's facts (objective, fund size, fees, allocations, top
   holdings, calendar-year returns) and its full total-return history, which is
   used to compute cumulative 3Y / 5Y / 10Y returns and to cross-check every
   published figure independently,
4. adds the official bid / offer prices,
5. downloads every fund's latest fact sheet into `factsheets/` (re-linked every
   run because Morningstar's links change monthly) and reads the benchmark
   returns out of the PDF,
6. writes `data/funds.json`, `data/funds.csv`, a dated copy in `data/history/`,
   `data/refresh_report.md` (what succeeded, what failed, every discrepancy),
   and rebuilds `dashboard.html`.

A failed run never corrupts the previous good dataset — files are written to a
temp file and swapped only at the end. Fact sheets already downloaded today are
not re-downloaded, so re-running is safe. `python refresh.py --no-pdf` skips
the PDFs for a quick numbers-only update.

**Always glance at `data/refresh_report.md` after a refresh.** "Failures /
notes: none" and a short discrepancy list means all is well.

## Checking the numbers (recommended after each refresh)

```bash
python verify.py
```

Prints, for an equity, a bond and a mixed-asset fund, the official fact sheet
figures next to the same figures recomputed from the Fund Centre's history *at
the fact sheet date* (they should match to 0.00 pp) and next to the
dashboard's current figures; confirms all 40 fact sheet buttons work (local PDF
present, online link answering); opens the dashboard in a headless browser,
fails on any script error and saves screenshots to `verify/`. Add fund names to
check others: `python verify.py "GreatLink Lion India Fund"`.

Parser unit tests: `python -m unittest discover tests -v` (42 tests).

## Using the dashboard

Double-click `dashboard.html`. The header shows two dates: **returns & prices
as at** (daily, from the Fund Centre) and **fact sheets as at** (monthly).

- **Overview** — every fund with YTD / 1Y / 3Y / 5Y / 10Y / since-inception
  returns, bid price, size and fee. Click a column heading to sort (default:
  YTD, best first); the rank badge follows the current sort. Filter by
  category chips, risk level, CPF-OA / CPF-SA / SRS, or free-text search.
  "Category leaders" shows the best YTD and best 5Y fund in each category.
- **Compare** — tick 2–5 funds, press **Compare**: grouped bar chart,
  key-facts and calendar-year table, asset allocations. **Copy table** puts a
  clean text table (with the disclaimer) on the clipboard for WhatsApp /
  email; **Print / Save as PDF** prints just the comparison with the full
  disclaimer (1–2 A4 pages).
- **Fund detail** — click a fund name: objective, key facts (manager,
  underlying fund, size, fee, bid/offer, CPF/SRS, benchmark), full returns
  (trailing and cumulative), the official **fund-vs-benchmark table as printed
  on the fact sheet** (with its own as-at date), calendar-year returns,
  allocations, top-10 holdings, and the **Open Fund Fact Sheet** button plus
  Product Highlights Sheet, Prospectus and Great Eastern site links.
- **Fact sheets: Local folder / Online links** (top right) — "Local folder"
  opens the PDFs saved in `factsheets/` next to the dashboard (works offline).
  Choose "Online links" if you only have `dashboard.html` by itself (e.g. it
  was emailed to you). The choice is remembered.
- **Client view** hides the internal columns (IDs, data sources, missing-field
  notes) before you turn the screen to a client.
- A yellow banner appears automatically if the data is more than 45 days old.

## Sharing with a colleague

- **Full experience:** AirDrop or zip the whole `greatlink-funds` folder
  (they only need `dashboard.html` + `factsheets/`; the rest is optional).
- **Just the dashboard:** send `dashboard.html` on its own — all data is
  embedded; switch "Fact sheets" to **Online links** (internet needed for the PDFs).

## If something breaks

- `data/refresh_report.md` says exactly which fund / field failed and why.
- "Network problem": corporate networks and VPNs sometimes block
  `greateasternlife.com` or `ge-fundcentersg.newwealth.cloud`. Try again off
  the VPN / on a hotspot.
- "0 fund IDs found": Great Eastern changed the fund list page. The Fund Centre
  screener still works on its own — funds will be kept but categorised
  "Uncategorised" until `scraper/fundlist.py` is updated.
- New fund launched / fund closed: the tool includes whatever the Fund Centre
  lists; the expected 40-name check list in `scraper/fundlist.py` just flags
  the difference in the report — update it when convenient.
- Fact sheet layout changed ("performance table not found" in the report):
  returns are still correct (they come from the Fund Centre); only the
  benchmark table in the detail panel is affected. `scraper/factsheet_pdf.py`
  holds the parser.
- How the data sources were found and verified: `discovery/REPORT.md`.

## Folder map

```
refresh.py                 the one monthly command  (--no-pdf for a quick run)
verify.py                  post-refresh checks: PDF vs dashboard, buttons, screenshots
build_dashboard.py         embeds data/funds.json into templates/dashboard.html
scraper/fundlist.py        fund list, categories and IDs from greateasternlife.com
scraper/fundcentre.py      Fund Centre screener / detail / total-return history + return maths
scraper/prices.py          official bid / offer prices
scraper/documents.py       fact sheet downloader (same-day cache)
scraper/factsheet_pdf.py   fact sheet parser (performance table, facts, as-at date)
scraper/util.py            number / date parsing, polite HTTP, atomic writes
templates/dashboard.html   dashboard source (vanilla HTML/CSS/JS, no frameworks, no CDN)
dashboard.html             the built dashboard — open this
data/funds.json | .csv     the clean dataset   ·   data/history/  dated copies
data/refresh_report.md     what the last refresh did
factsheets/                local fact sheet PDFs (greatlink-<fund-name>.pdf)
tests/                     parser and return-maths unit tests
discovery/                 Phase 1 endpoint discovery report and scripts
```
