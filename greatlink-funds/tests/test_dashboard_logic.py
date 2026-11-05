"""Tests for the dashboard's display labels and its sort / filter / compare logic.

    python -m unittest discover tests

The sort/filter logic is plain JavaScript (templates/fund_logic.js, inlined into
dashboard.html). It is exercised here through Node.js, which GitHub's runners
and most Macs with developer tools already have; those tests are skipped with a
clear message if `node` is not installed.
"""

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper.display import annotate, na_note, region_of, HOLDINGS_NOTE  # noqa: E402

AS_AT = "2026-11-02"


def fund(name="GreatLink Test Fund", inception="2010-01-01", **returns):
    base = {k: None for k in ("ret_ytd", "ret_1y", "ret_3y_ann", "ret_5y_ann", "ret_10y_ann", "ret_si_ann")}
    base.update(returns)
    return {"name": name, "inception_date": inception, "returns": base,
            "asset_class": "Equity", "top_holdings": [{"name": "X", "pct": 5.0}]}


class TestNaNotes(unittest.TestCase):
    def test_gold_fund_launched_jan_2026(self):
        gold = fund("GreatLink Singapore Physical Gold Fund", "2026-01-23")
        self.assertEqual(na_note(gold, "ret_ytd", AS_AT), "n/a, launched Jan 2026")
        self.assertEqual(na_note(gold, "ret_1y", AS_AT), "n/a, launched Jan 2026")
        self.assertEqual(na_note(gold, "ret_5y_ann", AS_AT), "n/a, launched Jan 2026")

    def test_present_figure_has_no_note(self):
        self.assertIsNone(na_note(fund(ret_1y=4.2), "ret_1y", AS_AT))

    def test_old_fund_missing_figure_is_plain_na(self):
        self.assertEqual(na_note(fund(inception="2005-03-01"), "ret_1y", AS_AT), "n/a")

    def test_partly_too_young(self):
        f = fund(inception="2022-05-24", ret_ytd=1.0, ret_1y=2.0, ret_3y_ann=3.0)
        self.assertIsNone(na_note(f, "ret_3y_ann", AS_AT))
        self.assertEqual(na_note(f, "ret_5y_ann", AS_AT), "n/a, launched May 2022")

    def test_launched_last_year_ytd_is_plain_na(self):
        # launched Dec 2025: a YTD figure should exist, so a gap is just "n/a"
        self.assertEqual(na_note(fund(inception="2025-12-01"), "ret_ytd", AS_AT), "n/a")

    def test_unknown_inception(self):
        self.assertEqual(na_note(fund(inception=None), "ret_ytd", AS_AT), "n/a")


class TestRegionAndHoldings(unittest.TestCase):
    def test_regions_from_name(self):
        cases = {
            "GreatLink Global Emerging Markets Equity Fund": "Emerging markets",
            "GreatLink European Sustainable Equity Fund": "Europe",
            "GreatLink Far East Ex Japan Equities Fund": "Asia",
            "GreatLink Lion Asian Balanced Fund": "Asia",
            "GreatLink ASEAN Growth Fund": "Asia",
            "GreatLink Lion Japan Growth Fund": "Japan",
            "GreatLink Singapore Equities Fund": "Singapore",
            "GreatLink US Income and Growth Fund (Dis)": "United States",
            "GreatLink Cash Fund": "Global / multi-region",
            "GreatLink Lifestyle Balanced Portfolio": "Global / multi-region",
        }
        for name, region in cases.items():
            self.assertEqual(region_of({"name": name, "asset_class": "Equity"}), region, name)

    def test_gold_is_not_tagged_singapore(self):
        self.assertEqual(region_of({"name": "GreatLink Singapore Physical Gold Fund",
                                    "asset_class": "Commodity"}), "Global / multi-region")

    def test_missing_holdings_note(self):
        f = fund()
        f["top_holdings"] = []
        self.assertEqual(annotate(f, AS_AT)["holdings_note"], HOLDINGS_NOTE)
        self.assertIsNone(annotate(fund(), AS_AT)["holdings_note"])

    def test_annotate_does_not_touch_figures(self):
        f = fund(ret_1y=3.3)
        out = annotate(f, AS_AT)
        self.assertEqual(out["returns"], f["returns"])
        self.assertNotIn("na_notes", f)   # original left unchanged

    def test_committed_data_gaps_are_labelled(self):
        data = json.loads((ROOT / "data" / "funds.json").read_text())
        by_name = {f["name"]: annotate(f, data["as_at"]) for f in data["funds"]}
        gold = by_name["GreatLink Singapore Physical Gold Fund"]
        self.assertEqual(gold["na_notes"]["ret_ytd"], "n/a, launched Jan 2026")
        self.assertEqual(gold["na_notes"]["ret_1y"], "n/a, launched Jan 2026")
        no_holdings = [n for n, f in by_name.items() if f["holdings_note"]]
        for n in no_holdings:
            self.assertEqual(by_name[n]["top_holdings"], [])


class TestBuild(unittest.TestCase):
    def test_render_inlines_logic_and_data(self):
        import build_dashboard
        data = json.loads((ROOT / "data" / "funds.json").read_text())
        html = build_dashboard.render(data)
        self.assertNotIn("/*__FUND_LOGIC_JS__*/", html)
        self.assertNotIn("/*__FUND_DATA_JSON__*/", html)
        self.assertIn("var FundLogic", html)
        self.assertIn("n/a, launched Jan 2026", html)
        self.assertIn("Past performance is not indicative of future performance", html)
        self.assertNotIn("build_dir", html)   # no local folder paths in the published page


NODE = shutil.which("node")
LOGIC = ROOT / "templates" / "fund_logic.js"


def run_js(body: str):
    """Run `body` with FundLogic (L) and a small fixture (F) in scope; return its JSON output."""
    script = f"""
const L = require({json.dumps(str(LOGIC))});
const mk = (name, risk, r1, r3, r5, extra) => Object.assign(
  {{fund_id: name, name, risk_class: risk, category: 'Cat', asset_class: 'Equity', region: 'Asia',
    eligibility: {{cpf_oa: false, srs: true}},
    returns: {{ret_1y: r1, ret_3y_ann: r3, ret_5y_ann: r5, ret_ytd: r1}}}}, extra || {{}});
const F = [
  mk('Alpha', '4 - Higher Risk', 10, 5, null),
  mk('Bravo', '2 - Low to Medium Risk', -2, 3, 4, {{region: 'Global / multi-region', asset_class: 'Fixed Income', eligibility: {{cpf_oa: true, srs: true}}}}),
  mk('Charlie', '3 - Medium to High Risk', null, null, null, {{category: 'Commodities'}}),
  mk('Delta', '4 - Higher Risk - narrowly focused', 10, 8, 6),
];
const names = a => a.map(f => f.name);
console.log(JSON.stringify((() => {{ {body} }})()));
"""
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, timeout=30)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


@unittest.skipUnless(NODE, "Node.js not installed — install it to run the dashboard logic tests")
class TestFundLogicJS(unittest.TestCase):
    def test_sort_1y_high_to_low_missing_last_ties_by_name(self):
        self.assertEqual(run_js("return names(L.sortFunds(F, 'ret_1y', -1));"),
                         ["Alpha", "Delta", "Bravo", "Charlie"])

    def test_sort_low_to_high_still_puts_missing_last(self):
        self.assertEqual(run_js("return names(L.sortFunds(F, 'ret_1y', 1));"),
                         ["Bravo", "Alpha", "Delta", "Charlie"])

    def test_sort_5y(self):
        self.assertEqual(run_js("return names(L.sortFunds(F, 'ret_5y_ann', -1));"),
                         ["Delta", "Bravo", "Alpha", "Charlie"])

    def test_sort_by_risk_class_number(self):
        self.assertEqual(run_js("return names(L.sortFunds(F, 'risk', 1));"),
                         ["Bravo", "Charlie", "Alpha", "Delta"])

    def test_sort_does_not_mutate_input(self):
        self.assertEqual(run_js("L.sortFunds(F, 'ret_1y', -1); return names(F);"),
                         ["Alpha", "Bravo", "Charlie", "Delta"])

    def test_filter_risk_uses_short_label(self):
        self.assertEqual(run_js("return names(L.filterFunds(F, {risk: '4 - Higher Risk'}));"),
                         ["Alpha", "Delta"])

    def test_filter_region_and_asset_class(self):
        self.assertEqual(run_js("return names(L.filterFunds(F, {region: 'Asia'}));"),
                         ["Alpha", "Charlie", "Delta"])
        self.assertEqual(run_js("return names(L.filterFunds(F, {asset: 'Fixed Income'}));"), ["Bravo"])

    def test_filter_minimum_3y_return_hides_missing(self):
        self.assertEqual(run_js("return names(L.filterFunds(F, {minKey: 'ret_3y_ann', minReturn: 4}));"),
                         ["Alpha", "Delta"])

    def test_filter_minimum_ignored_when_blank(self):
        self.assertEqual(run_js("return L.filterFunds(F, {minKey: 'ret_5y_ann', minReturn: null}).length;"), 4)

    def test_filter_category_cpf_and_search(self):
        self.assertEqual(run_js("return names(L.filterFunds(F, {cats: {Commodities: true}}));"), ["Charlie"])
        self.assertEqual(run_js("return names(L.filterFunds(F, {oa: true}));"), ["Bravo"])
        self.assertEqual(run_js("return names(L.filterFunds(F, {search: 'ELT'}));"), ["Delta"])

    def test_compare_limited_to_three(self):
        self.assertEqual(run_js("""
          let s = [];
          ['A','B','C','D'].forEach(id => { s = L.toggleSelection(s, id); });
          const full = s.slice();
          s = L.toggleSelection(s, 'B');
          return [full, s, L.MAX_COMPARE];"""), [["A", "B", "C"], ["A", "C"], 3])

    def test_distinct_values_sorted(self):
        self.assertEqual(run_js("return L.distinct(F, 'region');"), ["Asia", "Global / multi-region"])
        self.assertEqual(run_js("return L.distinct(F, 'risk');"),
                         ["2 - Low to Medium Risk", "3 - Medium to High Risk", "4 - Higher Risk"])


if __name__ == "__main__":
    unittest.main()
