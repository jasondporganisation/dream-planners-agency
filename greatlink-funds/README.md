# GreatLink Fund Comparison Tool

A client-meeting tool for Great Eastern (Singapore) financial representatives:
one refresh command pulls the latest returns for every GreatLink
investment-linked fund plus each fund's official fact sheet PDF, and rebuilds
`dashboard.html` — a single file you can open on any Mac, iPad (via AirDrop /
Files) or laptop, with no server and no internet needed after a refresh.

> **Internal reference tool.** It shows facts only — no projections, ratings
> or recommendations — and every view carries the past-performance
> disclaimer. Clients must still be given the official fund fact sheet,
> product highlights sheet and product summary.

---

## One-time setup on a fresh Mac

Open **Terminal** (press `Cmd-Space`, type "Terminal", press Enter) and paste
these lines one at a time:

```bash
# 1. Check Python 3.11+ is available (macOS: install from python.org if not)
python3 --version

# 2. Go to this folder (drag the greatlink-funds folder onto the Terminal
#    window after typing "cd " if you're not sure of the path)
cd greatlink-funds

# 3. Create a private Python environment and install the three libraries
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Install the browser the scraper drives (one-off, ~120 MB)
python -m playwright install chromium
```

## First run — the Phase 1 checkpoint

The Fund Centre is a JavaScript app, so the first run discovers the data
endpoints it uses before anything else:

```bash
source .venv/bin/activate          # if you opened a new Terminal window
python refresh.py --discover-only
```

This prints (and saves to `data/discovery_report.md`) the endpoints found,
a sample fund record, and the fund count versus the ~40 expected. **Read it
before continuing** — if the count is far from 40 the fund list is probably
paginated and the endpoint URL in `data/endpoints.json` needs its
page/pageSize parameters adjusted.

## Monthly refresh

```bash
cd greatlink-funds
source .venv/bin/activate
python refresh.py
```

That single command:

1. harvests the fund list and IDs from the Great Eastern fund pages,
2. pulls returns, prices, allocations and document links from the Fund
   Centre's Morningstar endpoints (re-using the discovered endpoints; run
   `python refresh.py --rediscover` if the site changes),
3. downloads every fund's latest fact sheet PDF into `factsheets/`
   (re-harvested every run because the Morningstar links change monthly),
4. writes `data/funds.json` and `data/funds.csv`, keeps a dated copy in
   `data/history/`, and writes `data/refresh_report.md` (what succeeded,
   what failed, missing fields, source discrepancies),
5. rebuilds `dashboard.html`.

A failed run never corrupts the previous good dataset — files are written to
a temp file and swapped only at the end. Fact sheets already downloaded
today are not re-downloaded (safe to re-run).

## Using the dashboard

Double-click `dashboard.html`. Everything is inside the one file except the
fact sheet PDFs:

- **Overview** — every fund with YTD / 1Y / 3Y / 5Y / 10Y / since-inception
  returns, bid price, size and fee. Click a column heading to sort; the rank
  badge follows the current sort. Filter by category, risk, CPF-OA / CPF-SA
  / SRS, or search. "Category leaders" shows the best YTD and 5Y fund per
  category.
- **Compare** — tick 2–5 funds, press **Compare**: side-by-side chart,
  key-facts table and allocations. **Copy table** puts a clean text table on
  the clipboard for WhatsApp/email; **Print / Save as PDF** prints just the
  comparison with the full disclaimer.
- **Fund detail** — click a fund name: objective, key facts, full returns
  (trailing + calendar-year, benchmark where available), allocations, top 10
  holdings, and the **Open Fund Fact Sheet** button.
- **Client view** (top right) hides internal columns (IDs, data sources,
  missing-field notes) before you turn the screen to a client.
- A yellow banner appears automatically if the data is more than 45 days old.

## Sharing with a colleague

- **Full experience:** zip the whole `greatlink-funds` folder (fact sheet
  buttons open the local PDFs).
- **Just the dashboard:** email `dashboard.html` on its own — all data is
  embedded; fact sheet buttons fall back to the online Morningstar links
  (internet needed for those).

## If something breaks

- `data/refresh_report.md` lists exactly which funds/fields failed and why.
- Site layout changed? `python refresh.py --rediscover` re-discovers the
  endpoints. Still failing: `data/discovery_samples/` holds the raw API
  responses for debugging.
- The expected 40-fund list (the completeness check) lives in
  `scraper/fundlist.py` — update it when Great Eastern launches or closes
  funds; unknown new funds are included automatically either way.

## Tests

```bash
python -m unittest discover tests -v
```

## Folder map

```
refresh.py             the one command (— also --discover-only / --rediscover)
build_dashboard.py     embeds data/funds.json into templates/dashboard.html
scraper/               fund list, Fund Centre, prices, documents, PDF parser
templates/dashboard.html   dashboard source template
dashboard.html         the built dashboard (open this)
data/funds.json|csv    the clean dataset  ·  data/history/  dated copies
data/refresh_report.md what the last refresh did
factsheets/            local fact sheet PDFs (greatlink-<fund>.pdf)
tests/                 parser unit tests
```
