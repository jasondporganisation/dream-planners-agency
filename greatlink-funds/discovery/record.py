"""Phase 1 discovery: record all network traffic while the GE fund list page,
the ILP Fund Centre screener, and one fund detail view load."""
import json, re, sys, time
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
BASE = "https://www.greateasternlife.com/sg/en/personal-insurance/our-products/wealth-accumulation/investment-linked-funds/"
FUNDLIST = BASE + "greatlink-funds.html"
CENTRE = BASE + "ilp-fund-centre.html"
DETAIL = CENTRE + "#/detail?id=F00001DUL4_F224"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

log = []          # request/response metadata
bodies = {}       # url -> body (json/text) for interesting responses
SKIP_EXT = re.compile(r"\.(png|jpe?g|gif|svg|woff2?|ttf|css|ico|webp|mp4)(\?|$)", re.I)

def on_response(resp):
    req = resp.request
    url = req.url
    entry = {"phase": current["phase"], "method": req.method, "url": url,
             "status": resp.status, "type": req.resource_type,
             "ct": resp.headers.get("content-type", "")}
    if req.method == "POST" and req.post_data:
        entry["post"] = req.post_data[:2000]
    h = req.headers
    for k in ("authorization", "x-api-key", "apikey", "x-morningstar-token", "cookie", "referer"):
        if k in h:
            entry["req_" + k] = h[k][:300]
    log.append(entry)
    if SKIP_EXT.search(url) or req.resource_type in ("image", "font", "stylesheet", "media"):
        return
    host = urlparse(url).netloc
    if "morningstar" in host or "api" in url.lower() or "json" in entry["ct"] or "greateastern" in host:
        try:
            body = resp.text()
            if body and len(body) < 5_000_000:
                bodies[url] = body
        except Exception as e:
            entry["body_err"] = str(e)[:100]

current = {"phase": ""}

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(user_agent=UA, viewport={"width": 1400, "height": 1000}, locale="en-SG")
    page = ctx.new_page()
    page.on("response", on_response)

    current["phase"] = "fundlist"
    page.goto(FUNDLIST, wait_until="domcontentloaded", timeout=90000); time.sleep(10)
    (OUT / "fundlist.html").write_text(page.content())
    page.screenshot(path=str(OUT / "fundlist.png"), full_page=True)

    current["phase"] = "screener"
    page.goto(CENTRE, wait_until="domcontentloaded", timeout=90000); time.sleep(10)
    time.sleep(8)
    page.screenshot(path=str(OUT / "screener.png"), full_page=True)
    (OUT / "screener.html").write_text(page.content())

    current["phase"] = "detail"
    page.goto(DETAIL, wait_until="domcontentloaded", timeout=90000); time.sleep(10)
    time.sleep(8)
    page.screenshot(path=str(OUT / "detail.png"), full_page=True)
    (OUT / "detail.html").write_text(page.content())
    b.close()

(OUT / "requests.json").write_text(json.dumps(log, indent=1))
for i, (u, body) in enumerate(bodies.items()):
    (OUT / f"body_{i:03d}.txt").write_text(u + "\n\n" + body)
print(f"{len(log)} requests, {len(bodies)} bodies saved")
for e in log:
    if e["type"] in ("xhr", "fetch", "document") or "morningstar" in e["url"]:
        print(e["phase"][:8].ljust(8), e["method"], e["status"], e["url"][:160])
