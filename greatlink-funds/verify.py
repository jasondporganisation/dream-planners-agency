#!/usr/bin/env python3
"""Phase 5 verification — run after `python refresh.py`.

    python verify.py            # everything
    python verify.py --quick    # skip online HEAD checks and screenshots

1. Fact sheet cross-check: for an equity, a bond and a mixed-asset fund (plus
   any funds named on the command line) print the official fact sheet figures
   next to the dashboard's figures recomputed AT THE FACT SHEET DATE from the
   Fund Centre total-return history (like-for-like), and the dashboard's
   current figures.
2. Every fund's fact sheet button: local PDF present and valid, online link
   answers 200 with a PDF.
3. Headless Chromium: open dashboard.html, fail on console errors, screenshot
   the overview, compare view and detail panel to verify/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scraper import factsheet_pdf, fundcentre  # noqa: E402
from scraper.util import PoliteSession  # noqa: E402

OUT = ROOT / "verify"
SAMPLE = ["GreatLink Global Equity Fund", "GreatLink Global Bond Fund", "GreatLink Lifestyle Balanced Portfolio"]
KEYS = [("1Y", "ret_1y"), ("3Y ann", "ret_3y_ann"), ("5Y ann", "ret_5y_ann"), ("10Y ann", "ret_10y_ann"), ("SI ann", "ret_si_ann")]


def fmt(v):
    return "   n/a" if v is None else f"{v:6.2f}"


def check_factsheets(funds, session, names) -> int:
    fails = 0
    print("\n== 1. Fact sheet vs dashboard (fund returns, %) ==")
    for name in names:
        f = next((x for x in funds if x["name"] == name), None)
        if not f:
            print(f"  {name}: not in dataset"); fails += 1; continue
        local = f["docs"].get("factsheet_local")
        parsed = factsheet_pdf.parse_factsheet(ROOT / local, f["fund_code"]) if local else None
        hist = fundcentre.fetch_nav_history(session, f["sec_id"], f.get("inception_date") or "1990-01-01")
        at_fs = fundcentre.returns_from_history(hist, parsed["as_at"]) if parsed and parsed["as_at"] else {}
        print(f"\n  {name}  (fact sheet as at {parsed['as_at'] if parsed else '?'}, dashboard as at {f['returns_as_at']})")
        print(f"  {'period':8} {'fact sheet':>11} {'recomputed@fs':>14} {'diff pp':>8} {'dashboard':>10}")
        for lbl, k in KEYS:
            a = parsed["fund"].get(k) if parsed else None
            b = at_fs.get(k)
            d = None if a is None or b is None else round(b - a, 2)
            flag = "" if d is None or abs(d) <= 0.1 else "   <-- >0.1pp"
            print(f"  {lbl:8} {fmt(a):>11} {fmt(b):>14} {fmt(d):>8} {fmt(f['returns'].get(k)):>10}{flag}")
            if flag:
                fails += 1
        bm = parsed["benchmark"] if parsed else {}
        if bm:
            print("  benchmark (fact sheet): " + ", ".join(f"{l} {fmt(bm.get(k)).strip()}" for l, k in KEYS))
        facts = parsed["facts"] if parsed else {}
        print(f"  fact sheet bid {facts.get('bid_price')} / fee {facts.get('mgmt_fee_pct')}% / size {facts.get('fund_size_m')}M"
              f"   | dashboard bid {f['bid_price']} ({f['price_date']}) / fee {f['mgmt_fee_pct']}% / size {f['fund_size_m']}M")
        if facts.get("mgmt_fee_pct") is not None and f["mgmt_fee_pct"] is not None and abs(facts["mgmt_fee_pct"] - f["mgmt_fee_pct"]) > 0.005:
            print("  <-- management fee differs"); fails += 1
    return fails


def check_buttons(funds, session, online: bool) -> int:
    print("\n== 2. Fact sheet buttons ==")
    missing_local, bad_online, no_link = [], [], []
    for f in funds:
        local = f["docs"].get("factsheet_local")
        url = f["docs"].get("factsheet_url")
        if not url:
            no_link.append(f["name"])
        if not local or not (ROOT / local).exists() or (ROOT / local).read_bytes()[:4] != b"%PDF":
            missing_local.append(f["name"])
        if online and url:
            try:
                r = session.get(url, timeout=60, stream=True)
                ok = r.status_code == 200 and "pdf" in (r.headers.get("content-type") or "").lower()
                r.close()
            except Exception:  # noqa: BLE001
                ok = False
            if not ok:
                bad_online.append(f["name"])
    print(f"  local PDFs valid: {len(funds) - len(missing_local)}/{len(funds)}"
          + (f"  missing: {missing_local}" if missing_local else ""))
    print(f"  online links: {'checked' if online else 'skipped (--quick)'}"
          + (f", failing: {bad_online}" if bad_online else (", all 200 application/pdf" if online else "")))
    if no_link:
        print(f"  funds with NO fact sheet link at all: {no_link}")
    return len(missing_local) + len(bad_online) + len(no_link)


def screenshots() -> int:
    print("\n== 3. Headless browser ==")
    from playwright.sync_api import sync_playwright
    OUT.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1366, "height": 900})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto((ROOT / "dashboard.html").as_uri())
        page.wait_for_selector("#tbody tr")
        rows = page.locator("#tbody tr").count()
        print(f"  overview rows rendered: {rows}")
        page.screenshot(path=str(OUT / "overview.png"), full_page=False)
        # compare: tick first three visible funds
        boxes = page.locator("#tbody input[data-sel]")
        for i in range(3):
            boxes.nth(i).check()
        page.click("#compareBtn")
        page.wait_for_selector("#compareSection:not([hidden])")
        page.locator("#compareSection").screenshot(path=str(OUT / "compare.png"))
        # detail panel
        page.locator("#tbody td.name").first.click()
        page.wait_for_selector("#detail.show")
        page.wait_for_timeout(400)
        page.locator("#detail").screenshot(path=str(OUT / "detail.png"))
        # client view hides internal columns
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        page.check("#clientView")
        hidden = page.evaluate("getComputedStyle(document.querySelector('td.internal')).display")
        print(f"  client view hides internal columns: {hidden == 'none'}")
        b.close()
    print(f"  console errors: {len(errors)}" + (f" -> {errors[:3]}" if errors else ""))
    print(f"  screenshots: {[p.name for p in sorted(OUT.glob('*.png'))]}")
    return len(errors) + (0 if rows else 1)


def main(argv) -> int:
    quick = "--quick" in argv
    names = [a for a in argv if not a.startswith("--")] or SAMPLE
    data = json.loads((ROOT / "data" / "funds.json").read_text())
    funds = data["funds"]
    print(f"Dataset: {len(funds)} funds, returns as at {data['as_at']}, fact sheets as at {data.get('factsheets_as_at')}")
    session = PoliteSession()
    fails = check_factsheets(funds, session, names)
    fails += check_buttons(funds, session, online=not quick)
    if not quick:
        fails += screenshots()
    print(f"\n{'PASS' if not fails else f'{fails} issue(s) flagged — see above'}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
