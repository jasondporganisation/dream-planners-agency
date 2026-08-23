"""Unit tests for the parsing helpers. Run with:  python -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.factsheet_pdf import parse_performance_rows
from scraper.util import (classify_period_label, parse_asat_date,
                          parse_money_millions, parse_pct, slugify)


class TestParsePct(unittest.TestCase):
    def test_plain_percent(self):
        self.assertEqual(parse_pct("12.34%"), 12.34)

    def test_negative(self):
        self.assertEqual(parse_pct("-3.1%"), -3.1)
        self.assertEqual(parse_pct("-3.1"), -3.1)

    def test_plus_sign_and_spaces(self):
        self.assertEqual(parse_pct("+0.5 %"), 0.5)

    def test_accounting_negative(self):
        self.assertEqual(parse_pct("(3.1)"), -3.1)

    def test_na_tokens(self):
        for token in ("n.a.", "N.A.", "n/a", "-", "--", "", None):
            self.assertIsNone(parse_pct(token), token)

    def test_thousands_comma(self):
        self.assertEqual(parse_pct("1,234.5"), 1234.5)

    def test_numeric_passthrough(self):
        self.assertEqual(parse_pct(7), 7.0)
        self.assertEqual(parse_pct(-0.25), -0.25)

    def test_garbage_is_none_not_zero(self):
        self.assertIsNone(parse_pct("abc"))


class TestPeriodLabels(unittest.TestCase):
    def test_ytd(self):
        self.assertEqual(classify_period_label("YTD"), "ret_ytd")
        self.assertEqual(classify_period_label("Year to Date"), "ret_ytd")

    def test_months(self):
        self.assertEqual(classify_period_label("3 Month"), "ret_3m")
        self.assertEqual(classify_period_label("6-month"), "ret_6m")

    def test_one_year(self):
        self.assertEqual(classify_period_label("1 Year"), "ret_1y")

    def test_annualised_default_for_multi_year(self):
        self.assertEqual(classify_period_label("5 Year"), "ret_5y_ann")
        self.assertEqual(classify_period_label("3 Year (p.a.)"), "ret_3y_ann")
        self.assertEqual(classify_period_label("10 Years Annualised"), "ret_10y_ann")

    def test_cumulative_is_distinct(self):
        self.assertEqual(classify_period_label("5 Year Cumulative"), "ret_5y_cum")
        self.assertEqual(classify_period_label("3-yr cum."), "ret_3y_cum")

    def test_annualised_beats_cumulative_when_both(self):
        # "annualised" wording wins if a label carries both words
        self.assertEqual(classify_period_label("5 Year annualised total return"),
                         "ret_5y_ann")

    def test_since_inception(self):
        self.assertEqual(classify_period_label("Since Inception (p.a.)"), "ret_si_ann")
        self.assertEqual(classify_period_label("Since inception cumulative"), "ret_si_cum")

    def test_unknown(self):
        self.assertIsNone(classify_period_label("Fund Objective"))


class TestDates(unittest.TestCase):
    def test_as_at_phrase(self):
        self.assertEqual(parse_asat_date("as at 29 May 2026"), "2026-05-29")

    def test_bare_dmy(self):
        self.assertEqual(parse_asat_date("31 December 2025"), "2025-12-31")
        self.assertEqual(parse_asat_date("1 Jan 2020"), "2020-01-01")

    def test_iso_passthrough(self):
        self.assertEqual(parse_asat_date("2026-07-31"), "2026-07-31")

    def test_sg_slash_format(self):
        self.assertEqual(parse_asat_date("31/12/2025"), "2025-12-31")

    def test_none_for_garbage(self):
        self.assertIsNone(parse_asat_date("n.a."))
        self.assertIsNone(parse_asat_date(None))


class TestMoney(unittest.TestCase):
    def test_millions_phrase(self):
        self.assertEqual(parse_money_millions("S$ 123.4 million"), 123.4)

    def test_raw_units(self):
        self.assertEqual(parse_money_millions("123,456,789"), 123.456789)

    def test_billions(self):
        self.assertEqual(parse_money_millions("1.2bn"), 1200.0)

    def test_na(self):
        self.assertIsNone(parse_money_millions("n.a."))


class TestSlug(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("GreatLink Global Equity Fund"),
                         "greatlink-global-equity-fund")

    def test_parens(self):
        self.assertEqual(slugify("GreatLink US Income and Growth Fund (Dis)"),
                         "greatlink-us-income-and-growth-fund-dis")


class TestPerformanceTable(unittest.TestCase):
    ROWS = [
        ["", "YTD", "1 Year", "3 Year (p.a.)", "5 Year (p.a.)", "Since Inception (p.a.)"],
        ["Fund", "7.80%", "12.40%", "11.60%", "9.80%", "4.40%"],
        ["Benchmark", "8.10%", "13.00%", "12.10%", "10.40%", "n.a."],
    ]

    def test_fund_row(self):
        parsed = parse_performance_rows(self.ROWS)
        self.assertEqual(parsed["fund"]["ret_ytd"], 7.8)
        self.assertEqual(parsed["fund"]["ret_5y_ann"], 9.8)
        self.assertEqual(parsed["fund"]["ret_si_ann"], 4.4)

    def test_benchmark_row(self):
        parsed = parse_performance_rows(self.ROWS)
        self.assertEqual(parsed["benchmark"]["ret_1y"], 13.0)
        self.assertNotIn("ret_si_ann", parsed["benchmark"])  # n.a. stays absent

    def test_negative_and_na_cells(self):
        rows = [["", "YTD", "1 Year"], ["Fund", "-3.1%", "n.a."]]
        parsed = parse_performance_rows(rows)
        self.assertEqual(parsed["fund"]["ret_ytd"], -3.1)
        self.assertNotIn("ret_1y", parsed["fund"])

    def test_empty(self):
        self.assertEqual(parse_performance_rows([]), {"fund": {}, "benchmark": {}})


class TestExpectedFundList(unittest.TestCase):
    def test_forty_funds_in_six_categories(self):
        from scraper.fundlist import EXPECTED_COUNT, EXPECTED_FUNDS
        self.assertEqual(EXPECTED_COUNT, 40)
        self.assertEqual(len(EXPECTED_FUNDS), 6)

    def test_name_matching(self):
        from scraper.fundlist import category_for
        self.assertEqual(category_for("GreatLink Global Equity Alpha Fund"),
                         "Global Equity")
        self.assertEqual(category_for("GreatLink Singapore Physical Gold Fund"),
                         "Commodities")
        self.assertIsNone(category_for("GreatLink Brand New Fund"))


if __name__ == "__main__":
    unittest.main()
