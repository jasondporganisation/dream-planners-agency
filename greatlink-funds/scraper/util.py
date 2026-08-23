"""Shared helpers: number/date parsing, polite HTTP, atomic writes, caching."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import date, datetime
from pathlib import Path

import requests

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
REQUEST_DELAY_S = 0.8  # polite gap between requests to the same host


# ---------------------------------------------------------------- parsing

_NA_TOKENS = {"", "-", "--", "n.a.", "n.a", "na", "n/a", "nil", "not applicable"}


def parse_pct(value) -> float | None:
    """'12.34%' / '-3.1' / '+0.5 %' / 'n.a.' -> float or None. Never guesses."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if text in _NA_TOKENS:
        return None
    text = text.replace("%", "").replace(",", "").replace("+", "").strip()
    # Accounting negatives: (3.1) means -3.1
    m = re.fullmatch(r"\((\d+(?:\.\d+)?)\)", text)
    if m:
        return -float(m.group(1))
    try:
        return float(text)
    except ValueError:
        return None


def parse_money_millions(value) -> float | None:
    """'S$ 123.4 million' / '123,456,789' / '1.2bn' -> millions, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Heuristic: an API value above 1e5 is raw currency units, not millions.
        return float(value) / 1e6 if float(value) > 1e5 else float(value)
    text = str(value).strip().lower()
    if text in _NA_TOKENS:
        return None
    text = re.sub(r"(s\$|sgd|usd|\$)", "", text).replace(",", "").strip()
    m = re.match(r"(-?\d+(?:\.\d+)?)\s*(billion|bn|b|million|mil|mn|m)?", text)
    if not m or m.group(1) is None:
        return None
    n = float(m.group(1))
    unit = m.group(2) or ""
    if unit.startswith("b"):
        return n * 1000.0
    if unit.startswith("m"):
        return n
    return n / 1e6 if n > 1e5 else n


_MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def parse_asat_date(value) -> str | None:
    """'as at 29 May 2026' / '29 May 2026' / '2026-05-29' / '31/12/2025' -> ISO date."""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    if text.lower() in _NA_TOKENS:
        return None
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})", text)
    if m:
        mon = _MONTHS.get(m.group(2)[:3].lower())
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return m.group(0)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)  # DD/MM/YYYY (SG convention)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def classify_period_label(label: str) -> str | None:
    """Map a performance-table column label to a canonical return key.

    Handles annualised-vs-cumulative wording explicitly; returns keys like
    'ret_ytd', 'ret_3m', 'ret_5y_ann', 'ret_5y_cum', 'ret_si_ann'.
    """
    t = str(label).strip().lower().replace("‑", "-")
    if not t:
        return None
    ann = bool(re.search(r"annuali[sz]ed|ann\.?\b|p\.?a\.?", t))
    cum = bool(re.search(r"cumulative|cum\.?\b|total return", t))
    if re.search(r"\bytd\b|year[\s-]*to[\s-]*date", t):
        return "ret_ytd"
    if re.search(r"since\s+incep|\bsi\b|inception", t):
        return "ret_si_cum" if cum else "ret_si_ann"
    m = re.search(r"(\d+)\s*(?:-|\s)?\s*(month|mth|mo\b|m\b)", t)
    if m:
        return f"ret_{int(m.group(1))}m"
    m = re.search(r"(\d+)\s*(?:-|\s)?\s*(year|yr|y\b)", t)
    if m:
        n = int(m.group(1))
        if n == 1:
            return "ret_1y"
        suffix = "_cum" if cum and not ann else "_ann"
        return f"ret_{n}y{suffix}"
    return None


def slugify(name: str) -> str:
    """'GreatLink Global Equity Fund' -> 'greatlink-global-equity-fund'."""
    s = name.lower()
    s = re.sub(r"\(([^)]*)\)", r" \1 ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# ---------------------------------------------------------------- IO

def atomic_write(path: Path, content: str) -> None:
    """Write via temp file + rename so a failed run never truncates good data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def atomic_write_json(path: Path, obj) -> None:
    atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- HTTP

class PoliteSession:
    """requests.Session with UA, per-host delay, retries with backoff, and a
    same-day download cache for large binaries (fact sheet PDFs)."""

    def __init__(self, cache_dir: Path | None = None):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.session.headers["Accept-Language"] = "en-SG,en;q=0.9"
        self._last_request = 0.0
        self.cache_dir = cache_dir

    def _wait(self):
        gap = time.time() - self._last_request
        if gap < REQUEST_DELAY_S:
            time.sleep(REQUEST_DELAY_S - gap)
        self._last_request = time.time()

    def request(self, method: str, url: str, *, retries: int = 3, timeout: int = 45,
                **kw) -> requests.Response:
        last_err = None
        for attempt in range(1, retries + 1):
            self._wait()
            try:
                res = self.session.request(method, url, timeout=timeout, **kw)
                if res.status_code >= 500 or res.status_code == 429:
                    raise requests.HTTPError(f"HTTP {res.status_code} for {url}")
                return res
            except requests.RequestException as err:
                last_err = err
                if attempt < retries:
                    time.sleep(2 ** attempt)
        raise last_err

    def get(self, url: str, **kw) -> requests.Response:
        return self.request("GET", url, **kw)

    def post(self, url: str, **kw) -> requests.Response:
        return self.request("POST", url, **kw)

    def download(self, url: str, dest: Path, *, min_bytes: int = 1024,
                 magic: bytes | None = None) -> bool:
        """Download to dest. Skips if dest already exists and was written today
        (same-day cache). Returns True on success."""
        if dest.exists():
            mtime = datetime.fromtimestamp(dest.stat().st_mtime)
            if mtime.date() == date.today() and dest.stat().st_size >= min_bytes:
                return True
        res = self.get(url)
        if res.status_code != 200:
            return False
        body = res.content
        if len(body) < min_bytes:
            return False
        if magic and not body.startswith(magic):
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(body)
        os.replace(tmp, dest)
        return True
