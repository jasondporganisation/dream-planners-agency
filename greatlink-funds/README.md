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
panel). Since-inception returns are computed from each fund's full total-return
history (the Fund Centre's own "max" field is not a since-inception figure).
Nothing is ever estimated: a figure the source does not publish shows as
"n/a – launched MMM YYYY".

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
the downloads for a quick numbers-only update (fact sheets already in
`factsheets/` are still used).

The run **stops without writing anything** if any fund comes back empty (no
bid price, no price date, or no 1M/3M/6M/YTD/1Y return at all), if a fund's
price is more than 10 days older than the rest, or if fewer than 35 funds are
found. The terminal lists the funds affected. Usually a retry later fixes it; if
you really need to publish anyway, run `python refresh.py --allow-incomplete`
and the problems are recorded in `data/refresh_report.md`.

On top of that, every refresh runs **data-sanity checks** and writes the
results into `data/refresh_report.md` (same layout as before):

- under "Failures / notes": `FUND COUNT` (not exactly 40 funds), `DUPLICATE`
  (two funds share a fund code or ID), `BAD PRICE` (a price of 0 or below),
  `STALE DATA` / `STALE PRICE` (prices more than 10 days old on the run date);
- as `DISCREPANCY` lines: a bid price that moved more than 15% since the
  previous dataset ("week-on-week").

These do not stop the refresh, but the Failures section is then no longer
"- none", so the weekly PR is held for a person instead of being auto-merged.
The dashboard shows a red warning banner when its data is more than 10 days old.

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

Unit tests: `python -m unittest discover tests -v` (70 tests: parsers and
return maths, the check that the committed `data/funds.json` has no empty or
stale fund, the dashboard's "n/a, launched …" / region / missing-holdings
labels, and its sort, filter and compare logic). The sort/filter tests run the
dashboard's own JavaScript through Node.js; they are skipped with a message if
`node` is not installed.

## Automatic weekly refresh (GitHub Actions, free)

`.github/workflows/greatlink-refresh.yml` runs every **Monday 06:00 Singapore
time** on GitHub's free hosted runners. It runs `python refresh.py` against the
same public Great Eastern pages, runs the unit tests (including the "no empty
fund" check on the new data), and then **opens a pull request** called
"GreatLink fund data as at …". It never changes `main` itself: someone glances
at `data/refresh_report.md` in the PR and merges it, and Vercel publishes
`main` as before. No secrets or paid services are involved.

- **If a run fails** (a fund came back empty, the GE site was down, a test
  failed) nothing is published; GitHub emails the failure and the previous data
  stays live. Re-run it from the **Actions** tab → *GreatLink weekly data
  refresh* → **Run workflow**, which also works for an on-demand refresh.
- **One-time setting** (repo owner): Settings → Actions → General → Workflow
  permissions → tick **Allow GitHub Actions to create and approve pull
  requests**. Without it the run still pushes the new data to a
  `data-refresh/…` branch and says so in its log, but you open the PR by hand.
- GitHub pauses scheduled workflows in a repository with no activity for 60
  days; merging the weekly PRs counts as activity.

## Using the dashboard

Open `dashboard.html` (or the Vercel link). The yellow strip at the top shows
**Data as at** (the returns and prices date) and the plain disclaimer: past
performance is not indicative of future performance, and this is not advice.
The header also shows the fact sheets' as-at date.

- **On a phone** each fund is a card with YTD / 1Y / 3Y / 5Y returns, risk
  class, fee, a fact sheet link and a **Compare** tick box. Tap the fund name
  for the detail view. On a laptop or iPad you get the full table instead.
- **Sort** with the *Sort by* menu (1-, 3- or 5-year return, YTD, 10-year,
  risk class, fee, name), or click a column heading on the wide table. Funds
  without a figure for that period always go to the bottom.
- **Filter** by category chips, risk class, region, asset class, CPF-OA /
  CPF-SA / SRS, free-text search, and **Return at least … % over 1 / 3 / 5
  years** (funds without that figure are hidden while it is set). Region comes
  from the fund's name / mandate; funds that don't name one are "Global /
  multi-region". **Reset** clears everything.
- **Compare** — tick 2 or 3 funds, press **Compare**: grouped bar chart,
  key-facts and calendar-year table, asset allocations. **Copy table** puts a
  clean text table (with the disclaimer) on the clipboard for WhatsApp /
  email; **Print / Save as PDF** prints just the comparison with the full
  disclaimer.
- **Fund detail** — click a fund name: objective, key facts, a **performance
  chart** (trailing returns and the last six calendar years), full returns
  (trailing and cumulative), the official fund-vs-benchmark table from the
  fact sheet, calendar-year returns, allocations, top-10 holdings, and links to
  the fact sheet, Product Highlights Sheet, prospectus and Great Eastern site.
- **Missing figures** are never estimated. A fund too young for a period shows
  "n/a, launched MMM YYYY" (e.g. the Singapore Physical Gold Fund, launched Jan
  2026, has no YTD or 1-year figure yet); a fund whose top holdings were not
  published says so and points to its fact sheet.
- A banner appears automatically if the data is more than 45 days old.

## Sharing with a colleague

- **Full experience:** AirDrop or zip the whole `greatlink-funds` folder
  (they only need `dashboard.html` + `factsheets/`; the rest is optional).
- **Just the dashboard:** send `dashboard.html` on its own — all data is
  embedded; the fact sheet buttons open the online copies (internet needed).

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
