/* Pure sorting / filtering / selection helpers for the dashboard.
 *
 * No DOM access here, so the same file is inlined into dashboard.html by
 * build_dashboard.py AND unit-tested with Node from tests/test_dashboard_logic.py.
 * Keep it plain ES5 so it runs on older iPads too.
 */
var FundLogic = (function () {
  'use strict';

  var MAX_COMPARE = 3;

  /* Sortable fields. Return figures live under fund.returns. */
  var RETURN_KEYS = ['ret_ytd', 'ret_1m', 'ret_3m', 'ret_6m', 'ret_1y', 'ret_3y_ann',
                     'ret_5y_ann', 'ret_10y_ann', 'ret_si_ann'];

  function shortRisk(r) {
    return r ? String(r).replace(/\s*[–-]\s*(broadly diversified|narrowly focused)/i, '') : '—';
  }

  /* "4 - Higher Risk" -> 4 ; unknown -> null */
  function riskLevel(r) {
    var m = /^\s*(\d)/.exec(r || '');
    return m ? +m[1] : null;
  }

  function value(f, key) {
    if (RETURN_KEYS.indexOf(key) >= 0) return f.returns ? f.returns[key] : null;
    if (key === 'risk') return riskLevel(f.risk_class);
    if (key === 'name') return (f.name || '').toLowerCase();
    var v = f[key];
    return v === undefined ? null : v;
  }

  function isNum(v) { return typeof v === 'number' && !isNaN(v); }

  /* Stable sort; funds with no figure for `key` always go to the bottom,
   * whichever direction is chosen (so "best 5Y" never starts with n/a rows).
   * dir: -1 = high to low, 1 = low to high. Ties break on fund name A-Z. */
  function sortFunds(funds, key, dir) {
    dir = dir < 0 ? -1 : 1;
    return funds.map(function (f, i) { return { f: f, i: i }; }).sort(function (a, b) {
      var va = value(a.f, key), vb = value(b.f, key);
      var na = va === null || va === '' || (typeof va === 'number' && isNaN(va));
      var nb = vb === null || vb === '' || (typeof vb === 'number' && isNaN(vb));
      if (na !== nb) return na ? 1 : -1;
      if (!na && va !== vb) return (va < vb ? -1 : 1) * dir;
      var an = (a.f.name || ''), bn = (b.f.name || '');
      if (an !== bn) return an < bn ? -1 : 1;
      return a.i - b.i;
    }).map(function (x) { return x.f; });
  }

  /* criteria (all optional):
   *   search     substring of the fund name (case-insensitive)
   *   cats       {category: true} — any ticked category matches
   *   risk       shortRisk() label, e.g. "4 - Higher Risk"
   *   region     fund.region label
   *   asset      fund.asset_class label
   *   oa/sa/srs  true = must be eligible
   *   minKey     'ret_1y' | 'ret_3y_ann' | 'ret_5y_ann' ...
   *   minReturn  number; funds below it, or without that figure, are hidden */
  function filterFunds(funds, c) {
    c = c || {};
    var q = (c.search || '').toLowerCase();
    var cats = c.cats || {};
    var anyCat = Object.keys(cats).some(function (k) { return cats[k]; });
    var useMin = c.minKey && isNum(c.minReturn);
    return funds.filter(function (f) {
      if (anyCat && !cats[f.category]) return false;
      if (c.risk && shortRisk(f.risk_class) !== c.risk) return false;
      if (c.region && f.region !== c.region) return false;
      if (c.asset && f.asset_class !== c.asset) return false;
      var e = f.eligibility || {};
      if (c.oa && e.cpf_oa !== true) return false;
      if (c.sa && e.cpf_sa !== true) return false;
      if (c.srs && e.srs !== true) return false;
      if (q && (f.name || '').toLowerCase().indexOf(q) < 0) return false;
      if (useMin) {
        var v = value(f, c.minKey);
        if (!isNum(v) || v < c.minReturn) return false;
      }
      return true;
    });
  }

  /* Toggle a fund in the compare list (max MAX_COMPARE). Returns a new array. */
  function toggleSelection(selected, id, max) {
    max = max || MAX_COMPARE;
    var out = selected.slice(), ix = out.indexOf(id);
    if (ix >= 0) out.splice(ix, 1);
    else if (out.length < max) out.push(id);
    return out;
  }

  /* Distinct non-empty values of fund[field], in a stable display order. */
  function distinct(funds, field) {
    var seen = [];
    funds.forEach(function (f) {
      var v = field === 'risk' ? shortRisk(f.risk_class) : f[field];
      if (v && v !== '—' && seen.indexOf(v) < 0) seen.push(v);
    });
    return seen.sort();
  }

  return {
    MAX_COMPARE: MAX_COMPARE, RETURN_KEYS: RETURN_KEYS,
    shortRisk: shortRisk, riskLevel: riskLevel, value: value,
    sortFunds: sortFunds, filterFunds: filterFunds,
    toggleSelection: toggleSelection, distinct: distinct
  };
})();
if (typeof module !== 'undefined' && module.exports) module.exports = FundLogic;
