/**
 * Phase 2 — Scrape the fund universe discovered in Phase 1 into the
 * dashboard dataset (data/funds.json + dashboard/data.js).
 *
 * Run `npm run discover` first and review discovery/report.md (the Phase 1
 * checkpoint). If the auto-detected endpoint or field mapping is wrong,
 * override it in scripts/config.json:
 *
 *   {
 *     "fundListUrl": "https://…the screener endpoint…&pageSize=100",
 *     "fieldMap": { "name": "LegalName", "ytd": "ReturnM0", … }
 *   }
 *
 * Field mapping: Morningstar screener responses commonly use keys like
 * SecId, LegalName, ISIN, ClosePrice, ReturnM0 (YTD), ReturnM12/M36/M60/M120
 * (1/3/5/10y, 36+ annualized), ReturnLongestTenure (since inception). The
 * candidates below cover those plus variants; anything unmapped is kept
 * under `raw` so nothing is silently dropped.
 */

import fs from 'node:fs';
import path from 'node:path';
import { ROOT, writeOutputs, pick, num } from './lib.mjs';

const EXPECTED_FUND_COUNT = 40;
const DISCOVERY = path.join(ROOT, 'discovery');
const CONFIG_PATH = path.join(ROOT, 'scripts', 'config.json');

const CANDIDATES = {
  id: ['SecId', 'secid', 'Id', 'fundId', 'code'],
  name: ['LegalName', 'Name', 'FundName', 'legalName', 'name'],
  isin: ['ISIN', 'isin', 'Isin'],
  category: ['CategoryName', 'GlobalCategoryName', 'category', 'assetClass', 'Sector'],
  currency: ['PriceCurrency', 'Currency', 'currency', 'CurrencyId'],
  bid: ['ClosePrice', 'BidPrice', 'Price', 'NAV', 'nav', 'bid'],
  priceDate: ['ClosePriceDate', 'PriceDate', 'priceDate', 'Date', 'EndDate'],
  ytd: ['ReturnM0', 'YTDReturn', 'ytd', 'ReturnYTD', 'GBRReturnM0'],
  y1: ['ReturnM12', 'Return1Yr', 'y1', 'GBRReturnM12'],
  y3: ['ReturnM36', 'Return3Yr', 'y3', 'GBRReturnM36'],
  y5: ['ReturnM60', 'Return5Yr', 'y5', 'GBRReturnM60'],
  y10: ['ReturnM120', 'Return10Yr', 'y10', 'GBRReturnM120'],
  sinceInception: ['ReturnLongestTenure', 'SinceInception', 'ReturnSinceInception', 'inceptionReturn'],
  inceptionDate: ['InceptionDate', 'inceptionDate'],
  fundSizeM: ['FundSize', 'AUM', 'fundSize', 'NetAssets'],
  managementFeePct: ['ManagementFee', 'AnnualFee', 'OngoingCharge', 'ExpenseRatio', 'managementFee'],
  riskGrade: ['RiskGrade', 'RiskRating', 'CollectedSRRI', 'riskGrade'],
  factSheetUrl: ['FactsheetUrl', 'FactSheet', 'factSheetUrl', 'DocumentUrl'],
};

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

function calendarYearReturns(record) {
  // Screener payloads sometimes carry per-calendar-year keys, e.g.
  // ReturnY2023 / Return2023 / CY2023. Grab whatever is there.
  const out = {};
  for (const [k, v] of Object.entries(record)) {
    const m = k.match(/(?:return|cy)[^0-9]*?(20\d{2})$/i);
    if (m) {
      const n = num(v);
      if (n !== null) out[m[1]] = n;
    }
  }
  return out;
}

function normalize(record, fieldMap) {
  const get = (field) =>
    fieldMap?.[field] !== undefined ? record[fieldMap[field]] ?? null : pick(record, CANDIDATES[field]);
  return {
    id: String(get('id') ?? get('isin') ?? get('name') ?? '').trim(),
    name: get('name'),
    category: get('category'),
    currency: get('currency') || 'SGD',
    isin: get('isin'),
    price: { bid: num(get('bid')), asOf: get('priceDate') },
    fundSizeM: num(get('fundSizeM')),
    managementFeePct: num(get('managementFeePct')),
    riskGrade: get('riskGrade'),
    inceptionDate: get('inceptionDate'),
    returns: {
      ytd: num(get('ytd')),
      y1: num(get('y1')),
      y3: num(get('y3')),
      y5: num(get('y5')),
      y10: num(get('y10')),
      sinceInception: num(get('sinceInception')),
    },
    calendarYearReturns: calendarYearReturns(record),
    factSheetUrl: get('factSheetUrl'),
    factSheetLocal: null, // set by download-factsheets.mjs
    internalNotes: '',
    raw: record, // keep everything — nothing silently dropped
  };
}

async function fetchFundList(config) {
  if (config.fundListUrl) {
    console.log(`→ Fetching fund list from config: ${config.fundListUrl}`);
    const res = await fetch(config.fundListUrl, {
      headers: { accept: 'application/json', ...(config.headers || {}) },
    });
    if (!res.ok) throw new Error(`Fund list fetch failed: ${res.status}`);
    return largestObjectArray(await res.json()).arr ?? [];
  }
  // No config override: reuse the best sample captured during discovery.
  const samplesDir = path.join(DISCOVERY, 'samples');
  if (!fs.existsSync(samplesDir)) {
    throw new Error(
      'No scripts/config.json fundListUrl and no discovery/samples/. Run `npm run discover` first.'
    );
  }
  let best = { arr: null, len: 0, file: null };
  for (const f of fs.readdirSync(samplesDir)) {
    try {
      const json = JSON.parse(fs.readFileSync(path.join(samplesDir, f), 'utf8'));
      const { arr, len } = largestObjectArray(json);
      if (len > best.len) best = { arr, len, file: f };
    } catch { /* non-JSON sample */ }
  }
  if (!best.arr) throw new Error('No fund-list-shaped sample found in discovery/samples/.');
  console.log(`→ Using discovery sample ${best.file} (${best.len} records)`);
  return best.arr;
}

async function main() {
  const config = fs.existsSync(CONFIG_PATH) ? JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8')) : {};
  const rawFunds = await fetchFundList(config);
  const funds = rawFunds
    .map((r) => normalize(r, config.fieldMap))
    .filter((f) => f.name && f.id);

  if (funds.length === 0) {
    throw new Error(
      'Normalization produced 0 funds — the field mapping does not match this payload. ' +
        'Inspect discovery/samples/ and set fieldMap in scripts/config.json.'
    );
  }
  if (Math.abs(funds.length - EXPECTED_FUND_COUNT) > 8) {
    console.warn(
      `⚠️  ${funds.length} funds vs ~${EXPECTED_FUND_COUNT} expected — check pagination on the endpoint.`
    );
  }

  writeOutputs({
    generatedAt: new Date().toISOString(),
    source: config.fundListUrl || 'discovery samples',
    sample: false,
    disclaimerBasis: 'bid-to-bid, dividends and distributions reinvested',
    funds,
  });
}

main().catch((err) => {
  console.error('Scrape failed:', err.message);
  process.exit(1);
});
