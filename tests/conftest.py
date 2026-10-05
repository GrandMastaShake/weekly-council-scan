"""Test setup for the scripts that write and validate the price panel.

`backfill_weekly.py` imports `scan_pipeline.snapshot_macro`, which requires
yfinance at import time. The merge semantics under test never touch the
network -- they read a committed weekly file and write it back -- so the
provider is stubbed rather than installed. A test suite that needs a market
data provider to run is a test suite that does not get run. `requests` is
stubbed for the same reason: the cash-cap test imports `run_scan`, which
imports `fetch_context`, which calls requests only when it fetches.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

for name in ("yfinance", "pandas", "requests"):
    sys.modules.setdefault(name, types.ModuleType(name))

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

SCRIPTS = ROOT / "scripts"


def settled_stamp(as_of: str) -> str:
    """A fetch time at which every instrument for as_of has settled: 13:20
    UTC the next day. A file stamped the evening of its own session cannot
    carry a futures close (truth_check._feed_settlement_check), and until
    2026-10-05 this fixture stamped exactly that, 21:00 UTC on the day."""
    day = dt.date.fromisoformat(as_of) + dt.timedelta(days=1)
    return day.isoformat() + "T13:20:00Z"


def weekly_doc(as_of: str, tickers, close: float = 100.0, volume: int = 1_000_000,
               source: str = "yahoo", fetched_at: str | None = None) -> dict:
    return {
        "as_of": as_of,
        "source": source,
        "fetched_at": fetched_at or settled_stamp(as_of),
        "session": "close",
        "series": {t: {"close": close, "volume": volume} for t in tickers},
        "rates": {}, "vol": {}, "commodities": {}, "fx": {},
        "missing": [],
    }


@pytest.fixture
def panel(tmp_path):
    """A weekly directory factory: panel(files={date: doc}) -> Path."""
    def build(files: dict) -> Path:
        d = tmp_path / "data" / "weekly"
        d.mkdir(parents=True, exist_ok=True)
        for name, doc in files.items():
            (d / name).write_text(json.dumps(doc, indent=2) + "\n",
                                  encoding="utf-8", newline="\n")
        return d
    return build
