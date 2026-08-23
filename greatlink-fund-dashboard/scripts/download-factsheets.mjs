/**
 * Phase 3 — Download a local copy of every fund's monthly fact sheet PDF
 * (served from Morningstar's document service, doc.morningstar.com), so the
 * dashboard's "Open Fact Sheet" button works offline. The online URL is
 * kept as a fallback, so the dashboard still works if you email it to a
 * colleague without the factsheets folder.
 *
 * Reads data/funds.json, writes data/factsheets/<id>.pdf, then rewrites
 * funds.json + dashboard/data.js with factSheetLocal set.
 *
 * Usage: npm run factsheets
 */

import fs from 'node:fs';
import path from 'node:path';
import { DATA_DIR, readDataset, writeOutputs } from './lib.mjs';

const SHEETS_DIR = path.join(DATA_DIR, 'factsheets');
const DELAY_MS = 1500; // be polite to the document service
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const safeName = (id) => id.replace(/[^\w.-]+/g, '_');

async function download(url, dest) {
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const res = await fetch(url, { redirect: 'follow' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const buf = Buffer.from(await res.arrayBuffer());
      if (buf.length < 1024 || !buf.subarray(0, 5).toString().startsWith('%PDF')) {
        throw new Error(`response is not a PDF (${buf.length} bytes)`);
      }
      fs.writeFileSync(dest, buf);
      return true;
    } catch (err) {
      console.warn(`  attempt ${attempt} failed: ${err.message}`);
      await sleep(2000 * attempt);
    }
  }
  return false;
}

async function main() {
  fs.mkdirSync(SHEETS_DIR, { recursive: true });
  const dataset = readDataset();
  let ok = 0, missing = 0, failed = 0;

  for (const fund of dataset.funds) {
    if (!fund.factSheetUrl) {
      missing++;
      continue;
    }
    const file = path.join(SHEETS_DIR, `${safeName(fund.id)}.pdf`);
    if (fs.existsSync(file)) {
      fund.factSheetLocal = path.relative(path.join(DATA_DIR, '..'), file);
      ok++;
      continue;
    }
    console.log(`→ ${fund.name}`);
    if (await download(fund.factSheetUrl, file)) {
      fund.factSheetLocal = path.relative(path.join(DATA_DIR, '..'), file);
      ok++;
    } else {
      failed++;
      console.warn(`  ✗ giving up on ${fund.name} — online fallback will be used`);
    }
    await sleep(DELAY_MS);
  }

  writeOutputs(dataset);
  console.log(`Done: ${ok} local, ${failed} failed (online fallback), ${missing} funds with no fact sheet URL.`);
  if (missing > 0) {
    console.log(
      'Funds without a fact sheet URL usually mean the screener payload does not carry document ' +
        'links — check discovery/samples/ for a documents endpoint (msdoc/imassg) and add ' +
        'factSheetUrl values via scripts/config.json fieldMap or a follow-up mapping step.'
    );
  }
}

main().catch((err) => {
  console.error('Fact sheet download failed:', err.message);
  process.exit(1);
});
