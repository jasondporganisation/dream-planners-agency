"""Step 4: fact sheet PDFs — local copies with an online fallback.

Fact sheet links come from the Fund Centre (Morningstar document service,
https://doc.morningstar.com/Document/<hash>.msdoc/?key=...). They change
monthly, so refresh.py re-harvests them on every run before downloading.
Files are named by fund slug, e.g. factsheets/greatlink-global-equity-fund.pdf,
and cached same-day (safe to re-run).
"""

from __future__ import annotations

from pathlib import Path

from .util import PoliteSession, slugify


def factsheet_filename(fund_name: str) -> str:
    return f"{slugify(fund_name)}.pdf"


def download_factsheet(session: PoliteSession, fund: dict, factsheets_dir: Path) -> str | None:
    """Download the fund's fact sheet; returns the relative local path or None."""
    url = (fund.get("docs") or {}).get("factsheet_url")
    if not url:
        return None
    dest = factsheets_dir / factsheet_filename(fund["name"])
    ok = session.download(url, dest, min_bytes=10_000, magic=b"%PDF")
    return f"factsheets/{dest.name}" if ok else None
