"""Offline tests for fact sheet / price parsing (saved fixtures) and the data-sanity
checks written into data/refresh_report.md. No network.

Run with:  python -m unittest discover tests
"""

import json
import re
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT))

import refresh  # noqa: E402
from scraper import checks  # noqa: E402
from scraper.factsheet_pdf import parse_page_facts, parse_performance_lines  # noqa: E402
from scraper.prices import parse_prices  # noqa: E402

TODAY = date(2026, 11, 5)


def fund(code, name=None, bid=1.0, price_date="2026-11-03", **kw):
    f = {"fund_id": f"SEC{code}_{code}", "fund_code": code, "name": name or f"GreatLink {code} Fund",
         "bid_price": bid, "price_date": price_date, "offer_price": None,
         "missing_fields": [], "docs": {"factsheet_local": f"factsheets/{code}.pdf"}}
    f.update(kw)
    return f


def forty():
    return [fund(f"F{i:02d}") for i in range(1, 41)]


class TestFactsheetFixtures(unittest.TestCase):
    def _page(self, name):
        return (FIXTURES / name).read_text(encoding="utf-8")

    def test_standard_page_facts(self):
        facts = parse_page_facts(self._page("factsheet_page_standard.txt"))
        self.assertEqual(facts["fund_code"], "F07")
        self.assertEqual(facts["bid_price"], 2.3456)
        self.assertEqual(facts["offer_price"], 2.469)
        self.assertEqual(facts["fund_size_m"], 512.3)
        self.assertEqual(facts["mgmt_fee_pct"], 1.25)
        self.assertEqual(facts["as_at"], "2026-09-30")
        self.assertEqual(facts["underlying_fund"], "Example Global Equity Fund")

    def test_standard_page_performance(self):
        perf = parse_performance_lines(self._page("factsheet_page_standard.txt").split("\n"))
        self.assertEqual(perf["fund"]["ret_3m"], 12.7)
        self.assertEqual(perf["fund"]["ret_10y_ann"], 11.25)
        self.assertEqual(perf["fund"]["ret_si_ann"], 3.88)
        self.assertEqual(perf["benchmark"]["ret_1y"], 23.22)
        self.assertEqual(len(perf["fund"]), 7)

    def test_young_fund_page(self):
        text = self._page("factsheet_page_young_fund.txt")
        perf = parse_performance_lines(text.split("\n"))
        self.assertEqual(perf["fund"]["ret_3m"], -2.1)
        self.assertIsNone(perf["fund"]["ret_1y"])            # "-" = period not reached
        self.assertEqual(perf["fund"]["ret_si_cum"], -1.3)   # "(Cumulative)" header
        self.assertNotIn("ret_si_ann", perf["fund"])
        self.assertIsNone(perf["benchmark"]["ret_6m"])       # "N.A."
        self.assertEqual(parse_page_facts(text)["fund_code"], "F230")


class TestPriceFixture(unittest.TestCase):
    def setUp(self):
        self.px = parse_prices(json.loads((FIXTURES / "fund_prices.json").read_text()))

    def test_codes_normalised_to_F_prefix(self):
        self.assertEqual(set(self.px), {"F07", "F01", "F99"})   # blank code row ignored

    def test_values(self):
        self.assertEqual(self.px["F07"]["bid"], 2.3456)
        self.assertEqual(self.px["F07"]["offer"], 2.469)
        self.assertEqual(self.px["F07"]["date"], "2026-11-03")
        self.assertTrue(self.px["F07"]["cpf_approved"])

    def test_missing_values_are_none_not_zero(self):
        self.assertIsNone(self.px["F01"]["offer"])
        self.assertIsNone(self.px["F99"]["bid"])
        self.assertIsNone(self.px["F99"]["date"])

    def test_empty_payload(self):
        self.assertEqual(parse_prices({}), {})
        self.assertEqual(parse_prices(None), {})


class TestSanityFailures(unittest.TestCase):
    def test_clean_dataset(self):
        self.assertEqual(checks.sanity_failures(forty(), "2026-11-03", TODAY), [])

    def test_missing_fund(self):
        lines = checks.sanity_failures(forty()[:39], "2026-11-03", TODAY)
        self.assertEqual(lines, ["- FUND COUNT: 39 funds in this refresh (expected 40)"])

    def test_duplicate_fund_code(self):
        funds = forty()
        funds[5] = fund("F01", name="GreatLink Copy Fund")
        lines = checks.sanity_failures(funds, "2026-11-03", TODAY)
        self.assertTrue(any(ln.startswith("- DUPLICATE fund code F01:") for ln in lines), lines)

    def test_zero_and_negative_price(self):
        funds = forty()
        funds[0]["bid_price"] = 0.0
        funds[1]["offer_price"] = -1.2
        lines = checks.sanity_failures(funds, "2026-11-03", TODAY)
        self.assertEqual(sum(ln.startswith("- BAD PRICE") for ln in lines), 2)

    def test_stale_dataset(self):
        lines = checks.sanity_failures(forty(), "2026-10-20", TODAY)   # 16 days old
        self.assertEqual(len(lines), 1)
        self.assertIn("STALE DATA", lines[0])

    def test_ten_days_is_still_fresh(self):
        self.assertEqual(checks.sanity_failures(forty(), "2026-10-26", TODAY), [])

    def test_one_stale_fund(self):
        funds = forty()
        funds[3]["price_date"] = "2026-10-01"
        lines = checks.sanity_failures(funds, "2026-11-03", TODAY)
        self.assertEqual(len(lines), 1)
        self.assertIn("STALE PRICE", lines[0])

    def test_failure_lines_never_count_as_discrepancies(self):
        funds = forty()[:38] + [fund("F01"), fund("F02", bid=0)]
        for ln in checks.sanity_failures(funds, "2026-09-01", TODAY):
            self.assertTrue(ln.startswith("- "))
            self.assertNotIn("DISCREPANCY", ln)


class TestWeeklyMove(unittest.TestCase):
    def test_big_move_flagged(self):
        prev = [fund("F07", bid=2.00, price_date="2026-10-27")]
        cur = [fund("F07", bid=2.40, price_date="2026-11-03")]
        lines = checks.weekly_move_discrepancies(cur, prev)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("- DISCREPANCY GreatLink F07 Fund week-on-week"))
        self.assertIn("+20.0%", lines[0])

    def test_big_fall_flagged(self):
        prev = [fund("F07", bid=2.00, price_date="2026-10-27")]
        cur = [fund("F07", bid=1.60, price_date="2026-11-03")]
        self.assertIn("-20.0%", checks.weekly_move_discrepancies(cur, prev)[0])

    def test_normal_move_and_exactly_15_not_flagged(self):
        prev = [fund("F07", bid=2.00, price_date="2026-10-27"), fund("F08", bid=1.0, price_date="2026-10-27")]
        cur = [fund("F07", bid=2.10, price_date="2026-11-03"), fund("F08", bid=1.15, price_date="2026-11-03")]
        self.assertEqual(checks.weekly_move_discrepancies(cur, prev), [])

    def test_no_previous_or_same_date_or_new_fund(self):
        cur = [fund("F07", bid=3.0), fund("F99", bid=9.0)]
        self.assertEqual(checks.weekly_move_discrepancies(cur, []), [])
        self.assertEqual(checks.weekly_move_discrepancies(cur, None), [])
        same_day = [fund("F07", bid=1.0)]   # same price_date: not a weekly move
        self.assertEqual(checks.weekly_move_discrepancies(cur, same_day), [])


class TestReportFormat(unittest.TestCase):
    """The Mac auto-merge job parses these lines; the layout must not change."""

    STARTED = datetime(2026, 11, 2, 22, 0, tzinfo=timezone.utc)

    def render(self, funds, lines):
        return refresh.render_report(funds, "2026-11-03", lines, self.STARTED,
                                     "2026-11-02T22:05:00+00:00", "2026-09-30", ["2026-09-30"])

    def test_clean_report_layout(self):
        text = self.render(forty(), [])
        self.assertIn("\n- Funds processed: 40\n", text)
        self.assertIn("\n- Fact sheets on disk: 40/40\n", text)
        self.assertIn("\n## Failures / notes\n\n- none\n\n## Discrepancies", text)
        self.assertNotIn("DISCREPANCY", text)

    def test_sanity_lines_land_in_the_right_sections(self):
        funds = forty()
        funds[0]["bid_price"] = 0.0
        prev = [fund("F02", bid=0.5, price_date="2026-10-27")]
        lines = (checks.sanity_failures(funds, "2026-11-03", TODAY)
                 + checks.weekly_move_discrepancies(funds, prev))
        text = self.render(funds, lines)
        failures = text.split("## Failures / notes")[1].split("## Discrepancies")[0]
        discrepancies = text.split("## Discrepancies")[1].split("## Missing fields")[0]
        self.assertIn("- BAD PRICE", failures)
        self.assertNotIn("- none", failures)
        self.assertEqual(len(re.findall(r"^- DISCREPANCY ", discrepancies, re.M)), 1)
        self.assertEqual(text.count("DISCREPANCY"), 1)

    def test_committed_report_has_the_lines_the_merge_job_reads(self):
        text = (ROOT / "data" / "refresh_report.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^- Funds processed: \d+$")
        self.assertRegex(text, r"(?m)^- Fact sheets on disk: \d+/\d+$")
        self.assertRegex(text, r"(?m)^## Failures / notes$")

    def test_committed_dataset_passes_sanity_checks_on_its_own_date(self):
        data = json.loads((ROOT / "data" / "funds.json").read_text(encoding="utf-8"))
        as_at = date.fromisoformat(data["as_at"])
        self.assertEqual(checks.sanity_failures(data["funds"], data["as_at"], as_at), [])


class TestDashboardFreshness(unittest.TestCase):
    def test_dashboard_warns_after_ten_days(self):
        html = (ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertRegex(html, r"var STALE_DAYS\s*=\s*10;")
        self.assertIn('id="staleBanner"', html)
        self.assertIn("data as at", html.lower())


if __name__ == "__main__":
    unittest.main()
