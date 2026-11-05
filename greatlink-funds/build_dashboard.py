#!/usr/bin/env python3
"""Rebuild dashboard.html from templates/dashboard.html + data/funds.json.

The dataset is embedded directly into the HTML (no fetch, no server), so the
dashboard works offline and survives being emailed as a single file. Falls
back to data/funds.sample.json when no real dataset exists yet, so the
dashboard is viewable before the first refresh.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLACEHOLDER = "/*__FUND_DATA_JSON__*/null"
LOGIC_PLACEHOLDER = "/*__FUND_LOGIC_JS__*/"

sys.path.insert(0, str(ROOT))
from scraper.display import annotate  # noqa: E402


def render(dataset: dict) -> str:
    """Return the dashboard HTML with `dataset` embedded (no files written)."""
    template = (ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
    for ph in (PLACEHOLDER, LOGIC_PLACEHOLDER):
        if ph not in template:
            raise RuntimeError(f"build_dashboard: {ph} not found in templates/dashboard.html")
    logic = (ROOT / "templates" / "fund_logic.js").read_text(encoding="utf-8")
    # Display-only labels (why a figure is n/a, region, missing holdings note).
    dataset = dict(dataset, funds=[annotate(f, dataset.get("as_at")) for f in dataset["funds"]])
    # </script> inside a JSON string would terminate the script block early.
    payload = json.dumps(dataset, ensure_ascii=False).replace("</", "<\\/")
    return template.replace(LOGIC_PLACEHOLDER, logic).replace(PLACEHOLDER, payload)


def main() -> int:
    data_path = ROOT / "data" / "funds.json"
    if not data_path.exists():
        data_path = ROOT / "data" / "funds.sample.json"
        print("build_dashboard: no data/funds.json yet — embedding the labelled "
              "SAMPLE dataset. Run `python refresh.py` for real data.")
    dataset = json.loads(data_path.read_text(encoding="utf-8"))
    html = render(dataset)
    tmp = ROOT / "dashboard.html.tmp"
    tmp.write_text(html, encoding="utf-8")
    tmp.replace(ROOT / "dashboard.html")
    print(f"build_dashboard: wrote dashboard.html "
          f"({len(dataset['funds'])} funds, as at {dataset.get('as_at')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
