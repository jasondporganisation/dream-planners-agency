"""Unit tests for the parsing helpers. Run with:  python -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.factsheet_pdf import parse_page_facts, parse_performance_lines
from scraper.fundcentre import returns_from_history, normalize_screener_row
from scraper.fundlist import parse_fund_list_html, completeness_report, EXPECTED_FUNDS
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


class TestFactsheetPerformance(unittest.TestCase):
    """Real fact sheet layouts (2026): single-line header, split header with an
    8th 'Since Restructuring' column, wrapped fund name, '-' for young funds."""

    def test_standard_seven_columns(self):
        lines = ["3 Mths 6 Mths 1 Year 3 Years* 5 Years* 10 Years* Since Inception*",
                 "GreatLink Global Equity Fund 12.70% 8.61% 23.64% 17.35% 9.47% 11.25% 3.88%",
                 "Benchmark 14.05% 10.33% 23.22% 17.46% 10.62% 12.69% 5.78%"]
        out = parse_performance_lines(lines)
        self.assertEqual(out["fund"]["ret_3m"], 12.7)
        self.assertEqual(out["fund"]["ret_1y"], 23.64)
        self.assertEqual(out["fund"]["ret_5y_ann"], 9.47)      # * columns are annualised
        self.assertEqual(out["fund"]["ret_si_ann"], 3.88)
        self.assertEqual(out["benchmark"]["ret_10y_ann"], 12.69)
        self.assertNotIn("ret_sr_ann", out["fund"])

    def test_split_header_with_since_restructuring(self):
        lines = ["Since Since",
                 "3 Mths 6 Mths 1 Year 3 Years* 5 Years* 10 Years*",
                 "Inception* Restructuring*",
                 "GreatLink Global Perspective Fund 13.09% 7.04% 15.70% 13.95% 6.11% 10.39% 4.24% 11.58%",
                 "Benchmark 15.22% 11.89% 25.59% 17.91% 10.13% 12.60% 7.19% 12.40%"]
        out = parse_performance_lines(lines)
        self.assertEqual(out["fund"]["ret_si_ann"], 4.24)
        self.assertEqual(out["fund"]["ret_sr_ann"], 11.58)
        self.assertEqual(out["benchmark"]["ret_sr_ann"], 12.4)

    def test_wrapped_fund_name(self):
        lines = ["3 Mths 6 Mths 1 Year 3 Years* 5 Years* 10 Years* Since Inception*",
                 "GreatLink Lifestyle Balanced",
                 "13.83% 11.16% 20.78% 12.49% 3.66% 6.69% 4.48%",
                 "Portfolio",
                 "Benchmark 11.92% 10.31% 19.86% 12.28% 4.77% 7.17% 5.46%"]
        out = parse_performance_lines(lines)
        self.assertEqual(out["fund"]["ret_1y"], 20.78)
        self.assertEqual(out["benchmark"]["ret_1y"], 19.86)

    def test_young_fund_dashes_and_negatives(self):
        lines = ["3 Mths 6 Mths 1 Year 3 Years* 5 Years* 10 Years* Since Inception*",
                 "GreatLink Singapore Physical Gold Fund -11.76% - - - - - -21.05%",
                 "Benchmark -11.57% - - - - - -17.43%"]
        out = parse_performance_lines(lines)
        self.assertEqual(out["fund"]["ret_3m"], -11.76)
        self.assertIsNone(out["fund"]["ret_1y"])            # '-' -> None, never 0
        self.assertIsNone(out["fund"]["ret_5y_ann"])
        self.assertEqual(out["fund"]["ret_si_ann"], -21.05)

    def test_no_table(self):
        self.assertEqual(parse_performance_lines(["Fund Objective", "blah"]), {"fund": {}, "benchmark": {}})


class TestFactsheetFacts(unittest.TestCase):
    TEXT = ("GREATLINK\nGlobal Equity Fund\nas at 30 June 2026\n"
            "The ILP Sub-Fund invests all or substantially into the Goldman Sachs Global CORE® Equity Portfolio "
            "(“Underlying Fund”)\nInception Date 1 August, 2000 Offer Price SGD 2.682\n"
            "Dealing Frequency Daily Bid Price SGD 2.547\nFund Code F07\n"
            "Subscription Mode Cash & SRS Fund Size SGD 181.6 m\n"
            "Risk Category Higher Risk - Broadly Diversified Underlying Fund ^\n"
            "Fund Management Fee 1.60% p.a. Manager ^\n")

    def test_facts(self):
        f = parse_page_facts(self.TEXT)
        self.assertEqual(f["as_at"], "2026-06-30")
        self.assertEqual(f["fund_code"], "F07")
        self.assertEqual(f["bid_price"], 2.547)
        self.assertEqual(f["offer_price"], 2.682)
        self.assertEqual(f["fund_size_m"], 181.6)
        self.assertEqual(f["mgmt_fee_pct"], 1.6)
        self.assertEqual(f["underlying_fund"], "Goldman Sachs Global CORE® Equity Portfolio")
        self.assertTrue(f["risk_category"].startswith("Higher Risk"))


class TestReturnMaths(unittest.TestCase):
    def _hist(self):
        # 100 -> 110 over one year, -> 133.1 over three (10% p.a.), daily-ish points
        from datetime import date, timedelta
        h = {}
        d0 = date(2023, 8, 20)
        for i in range(0, 365 * 3 + 2, 1):
            d = d0 + timedelta(days=i)
            h[d.isoformat()] = round(100 * (1.10 ** (i / 365.25)), 6)
        return h

    def test_cumulative_and_annualised(self):
        r = returns_from_history(self._hist())
        self.assertAlmostEqual(r["ret_1y"], 10.0, places=1)
        self.assertAlmostEqual(r["ret_3y_ann"], 10.0, places=1)
        self.assertAlmostEqual(r["ret_3y_cum"], 33.1, places=0)
        self.assertNotIn("ret_5y_ann", r)             # history too short -> absent, not invented

    def test_as_of_date_uses_last_price_on_or_before(self):
        h = self._hist()
        r = returns_from_history(h, "2024-08-20")
        self.assertEqual(r["as_of"], "2024-08-20")
        self.assertAlmostEqual(r["ret_1y"], 10.0, places=1)
        self.assertNotIn("ret_3y_ann", r)

    def test_ytd_needs_year_end_price(self):
        r = returns_from_history(self._hist(), "2024-03-01")
        self.assertIn("ret_ytd", r)
        r2 = returns_from_history({"2024-02-01": 100.0, "2024-03-01": 105.0}, "2024-03-01")
        self.assertNotIn("ret_ytd", r2)

    def test_empty(self):
        self.assertEqual(returns_from_history({}), {})


class TestScreenerRow(unittest.TestCase):
    def test_annualised_vs_cumulative_labels(self):
        row = {"SecId": "F0HKG07068", "FundCode": "F07", "FundName": "GreatLink Global Equity Fund",
               "Currency": "SGD", "FundingSource": ["Cash", "SRS"], "YTD": 9.50959, "ReturnM12": 20.62,
               "ReturnM36": 18.97, "ReturnM60": 8.88, "ReturnM120": 10.86, "ReturnMAX": 3.53,
               "LastPrice": 2.568, "LastPriceDate": 1787184000, "InceptionDate": 965088000,
               "RiskLevel": "4 - Higher Risk"}
        n = normalize_screener_row(row)
        self.assertEqual(n["returns"]["ret_ytd"], 9.50959)       # cumulative
        self.assertEqual(n["returns"]["ret_1y"], 20.62)          # cumulative
        self.assertEqual(n["returns"]["ret_5y_ann"], 8.88)       # annualised
        self.assertNotIn("ret_5y_cum", n["returns"])             # never derived here
        self.assertEqual(n["price_date"], "2026-08-20")
        self.assertEqual(n["inception_date"], "2000-08-01")
        self.assertEqual(n["eligibility"], {"cash": True, "cpf_oa": False, "cpf_sa": False, "srs": True})

    def test_missing_returns_are_none(self):
        n = normalize_screener_row({"SecId": "X", "FundCode": "F1", "FundName": "New", "FundingSource": []})
        self.assertIsNone(n["returns"]["ret_10y_ann"])
        self.assertIsNone(n["bid_price"])


class TestFundListPage(unittest.TestCase):
    HTML = """<h2>Explore our other GreatLink funds</h2>
    <h3>Global Equity</h3>
    <a href="ilp-fund-centre.html#/detail?id=F00001DUL4_F224"><span>x</span></a>
    <a href="ilp-fund-centre.html#/detail?id=F0HKG07068_F07">y</a>
    <a href="ilp-fund-centre.html#/detail?id=F0HKG07068_F07">dup</a>
    <h3>Money Markets and Bonds</h3>
    <a href="ilp-fund-centre.html#/detail?id=F0HKG07063_F01">z</a>
    <h3>Additional GreatLink Funds information</h3>
    <a href="ilp-fund-centre.html#/detail?id=F0HKG07063_F01">footer dup</a>"""

    def test_ids_and_categories(self):
        funds = parse_fund_list_html(self.HTML)
        self.assertEqual([f["fund_id"] for f in funds], ["F00001DUL4_F224", "F0HKG07068_F07", "F0HKG07063_F01"])
        self.assertEqual(funds[0]["category"], "Global Equity")
        self.assertEqual(funds[0]["sec_id"], "F00001DUL4")
        self.assertEqual(funds[0]["fund_code"], "F224")
        self.assertEqual(funds[2]["category"], "Money Markets and Bonds")
        self.assertIn("#/detail?id=F0HKG07068_F07", funds[1]["fundcentre_url"])

    def test_expected_list_is_forty_in_six(self):
        self.assertEqual(sum(len(v) for v in EXPECTED_FUNDS.values()), 40)
        self.assertEqual(len(EXPECTED_FUNDS), 6)

    def test_completeness(self):
        funds = [{"name": f"GreatLink {n} Fund"} for names in EXPECTED_FUNDS.values() for n in names]
        funds[0]["name"] = "GreatLink US Income and Growth Fund (Dis)"   # suffix variants tolerated
        funds.append({"name": "GreatLink Brand New Fund"})
        rep = completeness_report(funds)
        self.assertEqual(rep["found"], 41)
        self.assertEqual(rep["unexpected_kept"], ["brand new"])
        self.assertEqual(len(rep["missing"]), 1)                # the one we overwrote


if __name__ == "__main__":
    unittest.main()
