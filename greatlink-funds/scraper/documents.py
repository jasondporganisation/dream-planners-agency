"""Step 3: fact sheet PDFs — local copies with an online fallback.

Fact sheets are monthly PDFs on Morningstar's document service
(doc.morningstar.com/document/<id>.msdoc/?clientid=imassg&key=...). The URLs
change each month, so refresh.py always re-harvests them from the Fund Centre
documents endpoint before downloading. Files are named by fund slug, e.g.
factsheets/greatlink-global-equity-fund.pdf, and cached same-day.
"""

from __future__ import annotations

from pathlib import Path

from .util import PoliteSession, slugify


def download_factsheet(session: PoliteSession, fund: dict, factsheets_dir: Path) -> str | None:
    """Download the fund's fact sheet; returns the relative local path or None."""
    url = (fund.get("docs") or {}).get("factsheet_url")
    if not url:
        return None
    dest = factsheets_dir / f"{slugify(fund['name'])}.pdf"
    ok = session.download(url, dest, min_bytes=10_000, magic=b"%PDF")
    return f"factsheets/{dest.name}" if ok else None
