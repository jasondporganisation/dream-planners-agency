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


def main() -> int:
    template = (ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
    data_path = ROOT / "data" / "funds.json"
    if not data_path.exists():
        data_path = ROOT / "data" / "funds.sample.json"
        print("build_dashboard: no data/funds.json yet — embedding the labelled "
              "SAMPLE dataset. Run `python refresh.py` for real data.")
    dataset = json.loads(data_path.read_text(encoding="utf-8"))

    if PLACEHOLDER not in template:
        print("build_dashboard: placeholder not found in template", file=sys.stderr)
        return 1
    # </script> inside a JSON string would terminate the script block early.
    payload = json.dumps(dataset, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace(PLACEHOLDER, payload)
    (ROOT / "dashboard.html").write_text(html, encoding="utf-8")
    print(f"build_dashboard: wrote dashboard.html "
          f"({len(dataset['funds'])} funds, as at {dataset.get('as_at')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
