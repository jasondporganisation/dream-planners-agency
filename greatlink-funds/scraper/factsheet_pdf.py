"""Last-resort returns source: parse the performance table out of a fact
sheet PDF with pdfplumber. Also used to cross-check dashboard figures against
the official PDFs (Phase 5 verification).
"""

from __future__ import annotations

import re
from pathlib import Path

from .util import classify_period_label, parse_asat_date, parse_pct


def parse_performance_rows(rows: list[list[str]]) -> dict:
    """Given a table (list of rows) whose header row carries period labels,
    return {'fund': {ret_key: value}, 'benchmark': {...}}.

    Row labels containing 'benchmark'/'index' go to benchmark; the first
    non-benchmark data row is taken as the fund. Annualised vs cumulative in
    the header is preserved via classify_period_label.
    """
    out = {"fund": {}, "benchmark": {}}
    if not rows:
        return out
    header = rows[0]
    keys = [classify_period_label(c or "") for c in header]
    for row in rows[1:]:
        label = (row[0] or "").lower()
        target = "benchmark" if re.search(r"benchmark|index", label) else "fund"
        if out[target]:
            continue  # keep only the first row of each kind
        for key, cell in zip(keys[1:], row[1:]):
            if key is None:
                continue
            val = parse_pct(cell)
            if val is not None:
                out[target][key] = val
    return out


def parse_factsheet(pdf_path: Path) -> dict:
    """Extract 'as at' date and performance figures from a fact sheet PDF."""
    import pdfplumber

    result = {"as_at": None, "fund": {}, "benchmark": {}}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:4]:
            text = page.extract_text() or ""
            if result["as_at"] is None:
                m = re.search(r"as at\s+([0-9]{1,2}\s+\w+\s+[0-9]{4})", text, re.I)
                if m:
                    result["as_at"] = parse_asat_date(m.group(1))
            for table in page.extract_tables() or []:
                head = " ".join(str(c or "") for c in table[0]).lower()
                if re.search(r"ytd|year|month|inception", head):
                    parsed = parse_performance_rows(table)
                    if parsed["fund"] and not result["fund"]:
                        result["fund"] = parsed["fund"]
                        result["benchmark"] = parsed["benchmark"]
    return result
