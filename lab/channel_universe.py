#!/usr/bin/env python3
"""The channel screen as a weekly universe for the engine replay (Pass 49).

`make_filter(names)` returns f(W, eligible) -> the names of `eligible` that
are on Pass 48's screen on Monday W, read from weekly bars that end before W:
a Pass 41 channel worth owning, a weekly swing of 1.5% or more, and a close no
more than 4.7 swings under the 52-week high. With fewer than MIN_NAMES passing
it returns `eligible` unchanged and counts the week as a fallback.

Weekly bars come from Yahoo (adjusted), cached for the day in lab/cache.
"""
from __future__ import annotations

import math
import pickle
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass41_owner_channel as p41  # noqa: E402

R2_MIN = 0.80
SWINGS_MAX = 4.7
SWING_MIN = 0.015
MIN_NAMES = 10
FLOOR = math.log(1.10) / 52.0
YEARS = "6y"


def weekly_bars(names):
    """{ticker: (week-start dates, high, low, close)} of adjusted weekly bars."""
    import yfinance as yf
    names = sorted(set(names))
    path = lab.CACHE / f"weekly_cu_{date.today().isoformat()}_{len(names)}.pkl"
    if path.exists():
        with open(path, "rb") as fh:
            return pickle.load(fh)
    out = {}
    for i in range(0, len(names), 100):
        chunk = names[i:i + 100]
        df = None
        for attempt in range(3):
            try:
                df = yf.download([t.replace(".", "-") for t in chunk], period=YEARS, interval="1wk", auto_adjust=True,
                                 progress=False, group_by="ticker", threads=True)
                break
            except Exception:                                       # noqa: BLE001
                time.sleep(5 + 5 * attempt)
        if df is None:
            continue
        for t in chunk:
            y = t.replace(".", "-")
            if y in df.columns.get_level_values(0):
                sub = df[y].dropna()
                if len(sub) > 30:
                    out[t] = ([d.date().isoformat() for d in sub.index], sub["High"].to_numpy(float),
                              sub["Low"].to_numpy(float), sub["Close"].to_numpy(float))
    lab.CACHE.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        pickle.dump(out, fh)
    for old in lab.CACHE.glob(f"weekly_cu_*_{len(names)}.pkl"):
        if old != path:
            old.unlink()
    return out


def on_screen(bars, W):
    """Is one name on the screen on Monday W? bars = (dates, high, low, close)."""
    dates, h, l, c = bars
    n = sum(1 for d in dates if d < W)                 # weekly bars that began before W; the last ended the Friday before
    if n and (date.fromisoformat(W) - date.fromisoformat(dates[n - 1])).days < 5:
        n -= 1                                         # a bar that began within W's own week is not finished
    if n < 60:
        return False
    c, h, l = c[:n], h[:n], l[:n]
    r = np.diff(np.log(c[-105:]))
    swing = float(r.std()) if len(r) >= 40 else None
    if not swing or swing < SWING_MIN:
        return False
    if math.log(c[-1] / c[-52:].max()) / swing < -SWINGS_MAX:
        return False
    m = min(p41.LOOKBACK, n)
    ch = p41.draw(np.log(c[-m:]), np.log(h[-m:]), np.log(l[-m:]))
    return bool(ch and ch["slope"] >= FLOOR and ch["r2"] >= R2_MIN)


def make_filter(names, log=None):
    """f(W, eligible) for engine_lab.run's "universe_filter" knob. `log`, if
    given, receives {W: {"passed": n, "fallback": bool}}."""
    cache = {}

    def f(W, eligible):
        if "bars" not in cache:
            cache["bars"] = weekly_bars(names)
        bars = cache["bars"]
        passed = [t for t in eligible if t in bars and on_screen(bars[t], W)]
        fallback = len(passed) < MIN_NAMES
        if log is not None:
            log[W] = {"passed": len(passed), "fallback": fallback, "names": passed}
        return list(eligible) if fallback else passed
    return f
