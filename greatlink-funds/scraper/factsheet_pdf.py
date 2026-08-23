"""Fact sheet PDF parser (pdfplumber).

Used for (a) the benchmark returns, which the Fund Centre API does not carry,
(b) the official "as at" date, and (c) cross-checking the dashboard's figures
against the official document (Phase 5 verification).

Layout (GreatLink fact sheets, 2026): one fund per page, or several funds in
one PDF (Lifestyle / Dynamic Portfolios — one page per portfolio, identified by
"Fund Code Fxx"). Each page has:

    3 Mths 6 Mths 1 Year 3 Years* 5 Years* 10 Years* Since Inception*
    <fund name, may wrap>  12.70% 8.61% 23.64% 17.35% 9.47% 11.25% 3.88%
    Benchmark 14.05% 10.33% 23.22% 17.46% 10.62% 12.69% 5.78%

`*` = annualised. Restructured funds carry an 8th "Since Restructuring" column;
young funds print "-" for periods they have not reached. There is no YTD
column on fact sheets.
"""

from __future__ import annotations

import re
from pathlib import Path

from .util import parse_asat_date, parse_money_millions, parse_pct

PERIOD_KEYS = ["ret_3m", "ret_6m", "ret_1y", "ret_3y_ann", "ret_5y_ann", "ret_10y_ann", "ret_si_ann"]
# "Since Inception" (and sometimes "Since Restructuring") may wrap onto the next line.
_HEADER_RE = re.compile(r"3\s*Mths\s+6\s*Mths\s+1\s*Year\s+3\s*Years\*?\s+5\s*Years\*?\s+10\s*Years", re.I)
PERIOD_KEYS_8 = PERIOD_KEYS + ["ret_sr_ann"]   # 8th column = since last restructuring
_TOKEN_RE = re.compile(r"(-?\d+\.\d+\s?%|\bN\.?A\.?\b|(?<=\s)-(?=\s|$))")


def _tokens(line: str) -> list[str]:
    return [t.strip() for t in _TOKEN_RE.findall(line)]


def parse_performance_lines(lines: list[str]) -> dict:
    """Given the text lines of one fund page, return
    {'fund': {ret_key: float|None}, 'benchmark': {...}} (empty dicts if absent)."""
    out = {"fund": {}, "benchmark": {}}
    idx = next((i for i, ln in enumerate(lines) if _HEADER_RE.search(ln)), None)
    if idx is None:
        return out
    for ln in lines[idx + 1: idx + 10]:
        toks = _tokens(ln)
        if len(toks) < 7:
            continue          # header continuation, wrapped fund name, footnotes
        target = "benchmark" if re.match(r"\s*benchmark", ln, re.I) else "fund"
        if out[target]:
            continue
        keys = PERIOD_KEYS_8 if len(toks) >= 8 else PERIOD_KEYS
        vals = {k: parse_pct(t) for k, t in zip(keys, toks)}
        out[target] = vals
        if out["fund"] and out["benchmark"]:
            break
    return out


def parse_page_facts(text: str) -> dict:
    facts = {}
    m = re.search(r"Fund Code\s+(F\d+)", text)
    if m:
        facts["fund_code"] = m.group(1)
    m = re.search(r"Bid Price\s+SGD\s+([\d.]+)", text)
    if m:
        facts["bid_price"] = float(m.group(1))
    m = re.search(r"Offer Price\s+SGD\s+([\d.]+)", text)
    if m:
        facts["offer_price"] = float(m.group(1))
    m = re.search(r"Fund Size\s+SGD\s+([\d,.]+\s*(?:m|bn|b|million|billion)?)", text, re.I)
    if m:
        facts["fund_size_m"] = parse_money_millions(m.group(1))
    m = re.search(r"Fund Management Fee\s*\^?\s*([\d.]+)\s*%\s*p\.a\.", text)
    if m:
        facts["mgmt_fee_pct"] = float(m.group(1))
    m = re.search(r"Risk Category\s*\^?\s*(.+?)(?:\s{2,}|\s+(?:Manager|Underlying|Fund Code)|$)", text, re.M)
    if m:
        facts["risk_category"] = m.group(1).strip()
    m = re.search(r"(?:invests?\s+(?:all\s+or\s+substantially|substantially|primarily|wholly)?\s*(?:in|into)\s+the\s+)(.+?)\s*\(\s*[“\"]?(?:the\s+)?Underlying\s+Fund", text, re.I | re.S)
    if m:
        facts["underlying_fund"] = re.sub(r"\s+", " ", m.group(1)).strip()
    m = re.search(r"as at\s+(\d{1,2}\s+\w+\s+\d{4})", text, re.I)
    if m:
        facts["as_at"] = parse_asat_date(m.group(1))
    return facts


def parse_factsheet(pdf_path: Path, fund_code: str | None = None) -> dict:
    """Parse the page for `fund_code` (or the first page with a performance
    table when not given). Returns {'as_at', 'fund', 'benchmark', 'facts', 'page'}."""
    import pdfplumber

    result = {"as_at": None, "fund": {}, "benchmark": {}, "facts": {}, "page": None}
    with pdfplumber.open(pdf_path) as pdf:
        pages = [(i, (pg.extract_text() or "")) for i, pg in enumerate(pdf.pages)]
    if not pages:
        return result
    # global as-at from page 1
    result["as_at"] = parse_page_facts(pages[0][1]).get("as_at")
    candidates = pages
    if fund_code:
        matched = [(i, t) for i, t in pages if re.search(rf"Fund Code\s+{re.escape(fund_code)}\b", t)]
        if matched:
            candidates = matched
    for i, text in candidates:
        lines = text.split("\n")
        perf = parse_performance_lines(lines)
        if perf["fund"] or perf["benchmark"]:
            result.update(perf)
            result["page"] = i + 1
            facts = parse_page_facts(text)
            # underlying fund / fee sometimes only on page 1 of multi-page sheets
            p1 = parse_page_facts(pages[0][1])
            for k in ("underlying_fund", "mgmt_fee_pct"):
                facts.setdefault(k, p1.get(k)) if p1.get(k) is not None else None
            result["facts"] = facts
            result["as_at"] = facts.get("as_at") or result["as_at"]
            break
    return result
