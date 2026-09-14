"""Read the engines' price history from the COMMITTED weekly panel.

Why this exists
---------------
run_scan calls ``fetch_all_data(STOCK_UNIVERSE, date)``, whose ``tickers``
argument is vestigial: ``MarketDataFetcher.build_context`` hardcodes
STOCK_UNIVERSE internally. So Monday live-fetched 277 names while ignoring the
330-series panel that Friday's feed job had already fetched, gate-verified and
committed.

That narrowing had a measurable cost. Against the 110-name curated watchlist,
STOCK_UNIVERSE reached 89% of Mega caps, 74% of Large, 59% of Mid and **10% of
Micro** -- the engines' median reachable name was five times larger than the
median name they could not see. Every Small/Mid-Cap Watch ticker the sector
wikis publish weekly (AOSL, DIOD, POWI, CEVA, ACLS, BBAI, SOUN, HOPE, CUBI,
IOVA, BEAM ...) was absent from STOCK_UNIVERSE, so none could ever be picked.
Reading the panel takes every tier to 100%.

What this does NOT do
---------------------
The panel carries ``close`` and ``volume`` only. It does not carry P/E,
fundamentals, earnings dates or realized-vol, so Cecil's inputs still come from
the live path; widening his loop simply lets him score more names, and his
existing missing-P/E guard (neutral 15, "N/A" in the thesis, never fabricate)
handles the tail. This is therefore not a pure runtime win: the price fetch
goes away, the fundamentals fetch widens.

The one semantic change
-----------------------
``PriceHistory.return_`` is ``(close - open) / open`` -- an INTRA-week figure.
The panel has no open, so reconstruction sets ``open`` to the PRIOR week's
close, which makes ``return_`` a WEEK-OVER-WEEK figure. ``compute_std_dev`` is
its only consumer (Marky's volatility component, Ophelia's vol_ratio).
Week-over-week arguably measures weekly risk better, since it includes the
Friday-close-to-Monday-open gap that an intra-week figure discards -- but it is
a change, and it is why this module is opt-in.

Enabling
--------
Off by default. Set ``COUNCIL_SCAN_SOURCE=panel`` to turn it on.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Dict, List, Optional

from scan_pipeline.utils.data_utils import PriceHistory

# A ticker needs at least this many reconstructed weeks to be scored. Below it
# the trend and volatility terms are noise; data_utils degrades gracefully on
# short tapes but there is no reason to feed it a two-point series.
MIN_WEEKS = 4

_PIPELINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CACHE: Dict[tuple, Dict[str, List[PriceHistory]]] = {}


def enabled() -> bool:
    """True when the engines should read the committed panel."""
    return os.environ.get("COUNCIL_SCAN_SOURCE", "").strip().lower() == "panel"


def panel_dir() -> Optional[str]:
    """Directory holding the committed weekly files, or None if absent."""
    override = os.environ.get("COUNCIL_PANEL_DIR", "").strip()
    candidates = [override] if override else []
    candidates += [
        os.path.join(_PIPELINE_ROOT, "data", "weekly"),
        os.path.join(_PIPELINE_ROOT, "StockApp", "data", "weekly"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return None


def load_price_cache(as_of: Optional[str] = None,
                     weeks: int = 12,
                     directory: Optional[str] = None) -> Dict[str, List[PriceHistory]]:
    """``{ticker: [PriceHistory, ...]}`` reconstructed from the weekly panel.

    ``weeks`` is the number of scored weeks wanted; one extra file is read to
    anchor the first week's return. A ticker's first retained week is dropped
    because it has no prior close -- inventing one would be inventing a number.
    """
    directory = directory or panel_dir()
    if not directory:
        return {}
    key = (directory, as_of, weeks)
    if key in _CACHE:
        return _CACHE[key]

    files = sorted(glob.glob(os.path.join(directory, "*.json")))
    if as_of:
        files = [f for f in files if os.path.basename(f)[:-5] <= as_of]
    files = files[-(weeks + 1):]

    rows: Dict[str, List[tuple]] = {}
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        stamp = doc.get("as_of")
        for ticker, bar in (doc.get("series") or {}).items():
            close = bar.get("close")
            if close is None:
                continue
            rows.setdefault(ticker, []).append(
                (stamp, float(close), float(bar.get("volume") or 0.0))
            )

    cache: Dict[str, List[PriceHistory]] = {}
    for ticker, series in rows.items():
        series.sort()
        history = [
            PriceHistory(series[i][0], series[i - 1][1], series[i][1], series[i][2])
            for i in range(1, len(series))
        ]
        if history:
            cache[ticker] = history

    _CACHE[key] = cache
    return cache


def _known_equities() -> set:
    """Tickers the config recognises as bookable equities.

    The panel is a FEED: alongside equities it carries the index and sector
    instruments the dashboards need -- SPY, QQQ, IWM, DIA, SMH and the eleven
    XL* sector ETFs. Those must never reach an engine as candidates; booking
    XLU as a "stock" is not a pick, it is a category error. They are excluded
    by intersecting with the config's own equity lists rather than by pattern
    matching a ticker string, so a genuinely new equity is never silently
    dropped for looking like an ETF.
    """
    from scan_pipeline.config import tickers as _t
    known = set(getattr(_t, "STOCK_UNIVERSE", ()))
    for extra in ("FOCUS_TICKERS", "BACKFILL_44_TICKERS", "AVAILABLE_TICKERS"):
        known |= set(getattr(_t, extra, ()))
    return known


def universe(as_of: Optional[str] = None,
             weeks: int = 12,
             min_weeks: int = MIN_WEEKS) -> List[str]:
    """Tickers the panel can actually support, sorted.

    Names the feed recorded in ``missing[]`` (delisted or merged) simply do not
    appear, which is the correct outcome -- BK, HES, MMC and PEAK drop out of
    the scan set on their own rather than needing a hand-maintained exclusion.

    Non-equity feed instruments are filtered out; see ``_known_equities``.
    """
    cache = load_price_cache(as_of=as_of, weeks=weeks)
    equities = _known_equities()
    return sorted(
        t for t, h in cache.items()
        if len(h) >= min_weeks and (not equities or t in equities)
    )
