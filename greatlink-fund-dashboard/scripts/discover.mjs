/**
 * Phase 1 — Endpoint discovery for the Great Eastern ILP Fund Centre.
 *
 * The Fund Centre (greateasternlife.com …/ilp-fund-centre.html) is a
 * Morningstar-powered JavaScript app: the fund list, returns and document
 * links are loaded via XHR from Morningstar services, not present in the
 * page HTML. This script drives a real browser, records every API response
 * the app makes, and writes a discovery report you can review before
 * running the scraper.
 *
 * Output (in ./discovery/):
 *   endpoints.json   — every captured API endpoint, deduped, with metadata
 *   samples/*.json   — response bodies for the interesting endpoints
 *   report.md        — the Phase 1 checkpoint: endpoints, one sample fund
 *                      record, and fund count vs the ~40 expected
 *
 * Usage:  npm run discover
 * Requires outbound access to greateasternlife.com + *.morningstar.com.
 */

import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'discovery');
const SAMPLES = path.join(OUT, 'samples');

const FUND_CENTRE_URL =
  'https://www.greateasternlife.com/sg/en/personal-insurance/our-products/wealth-accumulation/investment-linked-funds/ilp-fund-centre.html';

const EXPECTED_FUND_COUNT = 40; // ~39-40 GreatLink sub-funds per GE's public materials

// URL patterns that indicate fund-data or document endpoints.
const INTERESTING = [
  /morningstar\.com/i,          // lt.morningstar.com, doc.morningstar.com, tools.morningstar.*
  /api\/rest\.svc/i,            // Morningstar screener/security REST API
  /screener/i,
  /securit(y|ies)/i,
  /fundcentre|fund-centre|fundcenter/i,
  /msdoc/i,                     // Morningstar document service
  /imassg/i,                    // Great Eastern's Morningstar client id (seen in doc links)
];

const isInteresting = (url) => INTERESTING.some((re) => re.test(url));

function chromiumLaunchOptions() {
  const opts = { headless: true };
  // Managed environments pre-install Chromium here; fall back gracefully.
  const preinstalled = '/opt/pw-browsers/chromium';
  if (fs.existsSync(preinstalled)) opts.executablePath = preinstalled;
  return opts;
}

/** Recursively find the largest array of objects in a JSON payload —
 *  almost always the fund list in a screener response. */
function largestObjectArray(node, best = { arr: null, len: 0 }) {
  if (Array.isArray(node)) {
    if (node.length > best.len && node.every((x) => x && typeof x === 'object')) {
      best.arr = node;
      best.len = node.length;
    }
    for (const item of node) largestObjectArray(item, best);
  } else if (node && typeof node === 'object') {
    for (const v of Object.values(node)) largestObjectArray(v, best);
  }
  return best;
}

/** Heuristic: does this array of objects look like a list of funds? */
function looksLikeFunds(arr) {
  if (!arr || arr.length < 3) return false;
  const keys = Object.keys(arr[0]).map((k) => k.toLowerCase());
  const nameKey = keys.some((k) => /name|legalname|fundname/.test(k));
  const idKey = keys.some((k) => /secid|isin|id|ticker|code/.test(k));
  return nameKey && idKey;
}

async function main() {
  fs.mkdirSync(SAMPLES, { recursive: true });

  const captured = new Map(); // url -> {method, status, contentType, size, sampleFile}
  let bestFundList = { arr: null, len: 0, url: null };

  const browser = await chromium.launch(chromiumLaunchOptions());
  const page = await browser.newPage();

  page.on('response', async (res) => {
    const url = res.url();
    if (!isInteresting(url)) return;
    const req = res.request();
    const meta = {
      method: req.method(),
      status: res.status(),
      contentType: res.headers()['content-type'] || '',
      postData: req.postData() || null,
      sampleFile: null,
    };
    try {
      if (/json|javascript/.test(meta.contentType)) {
        const text = await res.text();
        const idx = captured.size;
        const file = path.join(SAMPLES, `sample-${String(idx).padStart(3, '0')}.json`);
        fs.writeFileSync(file, text);
        meta.sampleFile = path.relative(ROOT, file);
        meta.size = text.length;
        try {
          const json = JSON.parse(text);
          const { arr, len } = largestObjectArray(json);
          if (looksLikeFunds(arr) && len > bestFundList.len) {
            bestFundList = { arr, len, url };
          }
        } catch { /* not JSON after all */ }
      }
    } catch { /* response body unavailable (redirect etc.) */ }
    captured.set(`${meta.method} ${url}`, meta);
  });

  console.log(`→ Opening ${FUND_CENTRE_URL}`);
  await page.goto(FUND_CENTRE_URL, { waitUntil: 'networkidle', timeout: 120_000 });

  // Give the Morningstar app time to boot and fire its XHRs, then poke it:
  // scroll, and click anything that looks like pagination / "load more" /
  // a performance tab, so we capture those endpoints too.
  await page.waitForTimeout(5_000);
  for (let i = 0; i < 5; i++) await page.mouse.wheel(0, 1500);
  const pokes = [
    'text=/load more/i', 'text=/show more/i', 'text=/next/i',
    'text=/performance/i', 'text=/all funds/i',
  ];
  for (const sel of pokes) {
    try {
      const el = page.locator(sel).first();
      if (await el.isVisible({ timeout: 1_000 })) {
        await el.click({ timeout: 2_000 });
        await page.waitForTimeout(3_000);
      }
    } catch { /* element not present — fine */ }
  }
  await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});
  await browser.close();

  // ---- write endpoints.json ----
  const endpoints = [...captured.entries()].map(([key, meta]) => ({ endpoint: key, ...meta }));
  fs.writeFileSync(path.join(OUT, 'endpoints.json'), JSON.stringify(endpoints, null, 2));

  // ---- Phase 1 checkpoint report ----
  const lines = [];
  lines.push('# Phase 1 discovery report — ILP Fund Centre');
  lines.push('');
  lines.push(`Captured **${endpoints.length}** interesting endpoints (full list in \`discovery/endpoints.json\`, bodies in \`discovery/samples/\`).`);
  lines.push('');
  lines.push('## Endpoints');
  lines.push('');
  for (const e of endpoints) lines.push(`- \`${e.endpoint}\` (${e.status}, ${e.contentType})`);
  lines.push('');
  lines.push('## Fund list candidate');
  lines.push('');
  if (bestFundList.arr) {
    lines.push(`Best candidate: \`${bestFundList.url}\``);
    lines.push('');
    lines.push(`Fund count: **${bestFundList.len}** (expected ≈ ${EXPECTED_FUND_COUNT})`);
    if (Math.abs(bestFundList.len - EXPECTED_FUND_COUNT) > 8) {
      lines.push('');
      lines.push('> ⚠️ Count is far from the ~40 expected GreatLink funds. The list may be');
      lines.push('> paginated (check pageSize/page params on the endpoint above) or this');
      lines.push('> may be the wrong endpoint. Review before running the scraper.');
    }
    lines.push('');
    lines.push('### Sample fund record');
    lines.push('');
    lines.push('```json');
    lines.push(JSON.stringify(bestFundList.arr[0], null, 2));
    lines.push('```');
  } else {
    lines.push('> ⚠️ No response looked like a fund list. Open `discovery/samples/` and');
    lines.push('> inspect manually; the app may load data via POST bodies or iframes.');
  }
  lines.push('');
  lines.push('## Next step');
  lines.push('');
  lines.push('Review the endpoint + sample record above, fill in `scripts/config.json`');
  lines.push('(fundListUrl + field mapping) if the auto-detected mapping in scrape.mjs');
  lines.push('does not match, then run `npm run scrape`.');
  const report = lines.join('\n');
  fs.writeFileSync(path.join(OUT, 'report.md'), report);

  console.log('\n' + report);
  console.log(`\n→ Wrote ${path.join(OUT, 'report.md')}`);
}

main().catch((err) => {
  console.error('Discovery failed:', err);
  process.exit(1);
});
