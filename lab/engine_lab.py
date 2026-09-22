#!/usr/bin/env python3
"""Engine Lab -- replay the Council's numeric engines on the weeks it actually ran.

Scope: ONLY weeks the real Council ran and closed (portfolio/history/*.yaml),
plus weeks it ran and aborted to cash. Every week therefore has a real Council
book to compare the replay against. The set grows by one each Monday.

Pass 1 replays the engines EXACTLY as configured today (cecil, marky, ophelia
-> consensus.aggregate -> risk controls) and scores, on one basis:

  * the replayed engine book      -- what today's engines would have booked
  * the real Council book         -- what the Council actually booked that week
  * random picks at the replay's weights (200 draws) -- the noise floor
  * the equal-weight universe and SPY

POINT-IN-TIME RULES. For the week that opens on Monday W, the engines may only
see data dated strictly before W. Everything production reads "as of today" is
replaced with what was knowable at the time:

  production reads                         the lab substitutes
  ---------------------------------------  -----------------------------------
  live daily bars, range=3mo               daily bars in the 92 days before W
  today's facts.json 10Y (Marky's gate)    ^TNX at the last close before W
  today's wikis (wiki_signals)             neutral signals (Pass 1 isolates
                                           the numeric engines; the research
                                           layer is tested in the Council Room)
  today's P/E, fundamentals, earnings      none: no point-in-time source, so
                                           Cecil's value and quality legs sit
                                           at their neutral midpoints and only
                                           his safety leg is live
  real portfolio/history hit counts        the lab's own running record, built
                                           week by week from its own results

_aggregate_weekly and _risk_stats are imported from production, so the
engines see the same shape of data they see live.

SCORING matches the fixed tracker: date-pinned Monday open (first session on
or after Monday) -> Friday close, dividend-adjusted total return, cash = 0.

Pass 2 replays the pre-registered VARIANTS below (knobs on the production
engines, defaults unchanged) and measures every scoring input directly: its
rank correlation (IC) with the following week's return across the whole
eligible universe, week by week, plus the same test one level up for the
sector signals. The IC is the larger sample -- about 270 names a week rather
than a five-name book -- so it is where a mechanism shows up or fails to.

    python lab/engine_lab.py            # Pass 2: variants + diagnostics
    python lab/engine_lab.py --pass 1   # Pass 1 baseline only
    python lab/engine_lab.py --pass 3   # Pass 3: the leads on pre-Council weeks

Pass 3 replays the numeric engines on the 96 weeks before the Council
existed (2024-09-09 .. 2026-07-06) with the earnings calendar fed in, to test
the three Pass 2 leads on weeks that did not produce them.
"""
from __future__ import annotations

import argparse
import bisect
import contextlib
import io
import json
import math
import pickle
import random
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LAB = ROOT / "lab"
CACHE = LAB / "cache"
RESULTS = LAB / "results"
HISTORY = ROOT / "portfolio" / "history"
REPORTS = ROOT / "reports"

DATA_START = "2026-04-01"       # 92-day lookback before the first Council week
LOOKBACK_DAYS = 92              # production pulls range="3mo"
MIN_WEEKS = 4
RANDOM_DRAWS = 200
SEED = 20260921
EXTRA = ["SPY", "^VIX", "^TNX"]

# Pass 2 variants, registered before any of them was run (see lab/README.md).
# Keys are "module.ATTR" knobs on the production engines; "drop" replays the
# week without that engine's proposal.
VARIANTS = {
    "baseline":   {},
    "O-rs":       {"ophelia.SECTOR_SIGNAL": "rs_12_1"},
    "O-rs+":      {"ophelia.SECTOR_SIGNAL": "rs_12_1", "ophelia.STOCK_SIGNAL": "rs_12_1"},
    "M-15":       {"marky.LOW_VOL_POINTS": 15.0},
    "M-0":        {"marky.LOW_VOL_POINTS": 0.0},
    "O-rs+M-15":  {"ophelia.SECTOR_SIGNAL": "rs_12_1", "marky.LOW_VOL_POINTS": 15.0},
    "no-Ophelia": {"drop": "Ophelia"},
}

# Pass 3: the three Pass 2 leads, tested on weeks the Council never ran
# (engine-only; see lab/README.md). "earnings": False withholds the earnings
# calendar, so the blackout cannot fire.
HISTORY_DATA_START = "2024-06-03"
HISTORY_FIRST_MONDAY = "2024-09-09"
HISTORY_LAST_MONDAY = "2026-07-06"     # the week before the Council's pilot week
EARNINGS_CACHE = CACHE / "earnings_dates.json"
# The engine universe as it stood when Passes 1-3 and Council Room V1 ran. The
# 2026-09-21 review renamed or removed seven dead tickers; replays of those
# passes keep the universe they were registered on, so they still reproduce.
# The forward record uses the live universe.
FROZEN_UNIVERSE = LAB / "universe_2026-09-21.txt"


def frozen_universe():
    with open(FROZEN_UNIVERSE, encoding="ascii") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


VARIANTS3 = {
    "base":          {},
    "no-screen":     {"earnings": False},
    "O-last":        {"ophelia.SECTOR_SIGNAL": "last_week"},
    "M-skip":        {"marky.MOMENTUM_WINDOW": "skip_4w"},
    "O-last+M-skip": {"ophelia.SECTOR_SIGNAL": "last_week", "marky.MOMENTUM_WINDOW": "skip_4w"},
}


def _d(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def _plus(day, n):
    return (_d(day) + timedelta(days=n)).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------
# which weeks
# --------------------------------------------------------------------------
def council_weeks(last_closed_friday):
    """[(label, monday, council_book_or_None)] for every week the Council ran.

    label   the Council's own date for the week (a Tuesday after a holiday)
    monday  the Monday of that week, which sets the point-in-time cut-off
    book    [(ticker, weight)] from portfolio/history, or None for an abort
            week (the Council ran and held cash)
    """
    out = []
    reports = sorted(REPORTS.glob("*-report.md"))
    labels = [r.name[:10] for r in reports]
    for rpt in reports:
        label = rpt.name[:10]
        dt = _d(label)
        if dt.weekday() > 1:          # Monday/Tuesday runs only; 07-15 was a Wednesday pilot
            continue
        monday = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
        if _plus(monday, 4) > last_closed_friday:
            continue                  # week not closed yet
        hist = HISTORY / f"{label}.yaml"
        if hist.exists():
            with open(hist, encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
            book = [(p["ticker"], float(p["weight"])) for p in (doc.get("positions") or [])]
        elif any(later > label for later in labels):
            book = None               # the next session's STEP 0 found no book: an abort week, cash
        else:
            continue                  # not archived yet -- the next session's STEP 0 closes it
        out.append((label, monday, book))
    return out


def history_weeks(first_monday, last_monday):
    """[(label, monday, False)] for every Monday in the range. False marks a
    week the Council never ran: there is no real book to compare against."""
    out, d = [], _d(first_monday)
    while d <= _d(last_monday):
        w = d.strftime("%Y-%m-%d")
        out.append((w, w, False))
        d += timedelta(days=7)
    return out


def earnings_calendar(tickers, max_age_days=None):
    """{ticker: sorted report dates} from yfinance, cached on disk.

    These are the dates the companies actually reported. Dates are announced
    weeks ahead, so on a Monday the coming week's reporters were known; a
    rare moved date is the approximation. A ticker with no dates is treated
    the way production treats an unknown date: never excluded. max_age_days
    refetches a cache older than that (the forward run needs new quarters)."""
    cached, todo = {}, list(tickers)
    if EARNINGS_CACHE.exists():
        with open(EARNINGS_CACHE, encoding="utf-8") as fh:
            cached = json.load(fh)
        age_days = (datetime.now().timestamp() - EARNINGS_CACHE.stat().st_mtime) / 86400
        if max_age_days is None or age_days < max_age_days:
            todo = [t for t in tickers if t not in cached]   # fresh: fetch only the missing
        if not todo:
            return cached
    from concurrent.futures import ThreadPoolExecutor
    import yfinance as yf

    def one(t):
        for _ in range(3):
            try:
                ed = yf.Ticker(t).get_earnings_dates(limit=24)
                if ed is not None and len(ed):
                    return t, sorted({x.strftime("%Y-%m-%d") for x in ed.index})
            except Exception:
                pass
        return t, []
    with ThreadPoolExecutor(max_workers=6) as pool:
        cached.update(dict(pool.map(one, todo)))     # merged: other passes' names are kept
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(EARNINGS_CACHE, "w", encoding="ascii", newline="\n") as fh:
        json.dump(cached, fh, indent=0, sort_keys=True)
    return cached


def _next_report(dates, on_or_after):
    if not dates:
        return None
    i = bisect.bisect_left(dates, on_or_after)
    return dates[i] if i < len(dates) else None


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def download(tickers, adjusted, end, start=DATA_START):
    """Daily bars for every ticker, cached on disk (lab/cache is gitignored)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"daily_{'adj' if adjusted else 'raw'}_{start}_{end}_{len(tickers)}.pkl"
    if path.exists():
        with open(path, "rb") as fh:
            return pickle.load(fh)
    import pandas as pd
    import yfinance as yf
    frames = []
    for i in range(0, len(tickers), 60):
        chunk = tickers[i:i + 60]
        df = yf.download(chunk, start=start, end=end, auto_adjust=adjusted,
                         progress=False, group_by="column", threads=True)
        if getattr(df.columns, "nlevels", 1) == 1:
            df.columns = pd.MultiIndex.from_product([df.columns, chunk])
        frames.append(df)
    data = pd.concat(frames, axis=1)
    data = data.loc[:, ~data.columns.duplicated()]
    with open(path, "wb") as fh:
        pickle.dump(data, fh)
    return data


def bars_by_ticker(df):
    dates = [x.strftime("%Y-%m-%d") for x in df.index]
    level0 = set(df.columns.get_level_values(0))
    out = {}
    for t in sorted(set(df.columns.get_level_values(1))):
        o, c = df["Open"][t].values, df["Close"][t].values
        v = df["Volume"][t].values if "Volume" in level0 else [0.0] * len(dates)
        rows = []
        for dd, oo, cc, vv in zip(dates, o, c, v):
            if oo == oo and cc == cc and oo > 0 and cc > 0:
                rows.append({"date": dd, "open": float(oo), "close": float(cc),
                             "volume": float(vv) if vv == vv else 0.0})
        out[t] = rows
    return out


class Series:
    def __init__(self, rows):
        self.rows = rows
        self.dates = [r["date"] for r in rows]

    def before(self, day, lookback_days):
        lo = bisect.bisect_left(self.dates, _plus(day, -lookback_days))
        hi = bisect.bisect_left(self.dates, day)
        return self.rows[lo:hi]

    def last_close_before(self, day):
        hi = bisect.bisect_left(self.dates, day)
        return self.rows[hi - 1]["close"] if hi > 0 else None

    def week_return(self, monday):
        fri = _plus(monday, 4)
        lo = bisect.bisect_left(self.dates, monday)
        hi = bisect.bisect_right(self.dates, fri)
        if lo >= hi:
            return None
        return self.rows[hi - 1]["close"] / self.rows[lo]["open"] - 1.0


# --------------------------------------------------------------------------
# replay
# --------------------------------------------------------------------------
_DEFAULT_KNOBS = {}
_TAP = {"capture": None, "week": None}


def _set_knobs(engines, knobs):
    """Every knob any variant touches goes back to its production default,
    then this variant's settings go on top -- so replays never leak into each
    other, whatever order they run in."""
    keys = {k for table in (VARIANTS, VARIANTS3) for v in table.values() for k in v if "." in k}
    keys |= {k for k in knobs if "." in k}
    keys |= set(_DEFAULT_KNOBS)          # every knob any earlier replay set, back to default too
    for key in sorted(keys):
        mod, attr = key.split(".")
        _DEFAULT_KNOBS.setdefault(key, getattr(engines[mod], attr))
    for key in sorted(keys):
        mod, attr = key.split(".")
        setattr(engines[mod], attr, knobs.get(key, _DEFAULT_KNOBS[key]))


def _install_taps(engines):
    """Both engines hand their full, sorted score table to log_ties(); a tap
    there records every ticker's inputs without touching the engine code."""
    for name in ("marky", "ophelia"):
        mod = engines[name]
        if getattr(mod.log_ties, "lab_tap", False):
            continue

        def tap(scores, *a, _orig=mod.log_ties, _name=name, **k):
            if _TAP["capture"] is not None:
                _TAP["capture"].setdefault(_TAP["week"], {})[_name] = [dict(s) for s in scores]
            return _orig(scores, *a, **k)
        tap.lab_tap = True
        mod.log_ties = tap


def run(verbose=True, knobs=None, capture=None, weeks=None, start=DATA_START, earnings=None,
        names=None):
    """Replay every Council week and score it.

    knobs    {"module.ATTR": value} set on the engine modules for this replay
             only (see VARIANTS); {"drop": "Ophelia"} replays without her;
             {"solo": "Ophelia"} books that engine's top five, equal weights,
             in place of the consensus (the forward record's Ophelia-solo);
             {"sector_map_builder": f} with f(names, adj, weeks) -> (a
             SECTOR_MAP stand-in, offensive labels, defensive labels) swaps
             Ophelia's sector map for this replay only (Pass 10's clusters)
    capture  a dict that receives, per week, every ticker's scoring inputs
             from Ophelia and Marky, the sector signals, and each ticker's
             realized return -- the raw material for diagnostics()
    weeks    [(label, monday, book)] to replay instead of the Council's weeks;
             book False = the Council did not run that week
    start    first day of price data to download
    earnings {ticker: report dates} -- feeds the earnings blackout exactly as
             production does; None (Pass 1 and 2) leaves it unfed
    names    the universe to scan; None = the live STOCK_UNIVERSE
    """
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
    from scan_pipeline.engines import cecil, consensus, marky, ophelia
    from scan_pipeline.engines.personality import get_initial_personas
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _risk_stats
    from scan_pipeline.utils import wiki_signals
    from scan_pipeline.utils.data_utils import generate_deterministic_context, get_sector

    last_friday = date.today() - timedelta(days=(date.today().weekday() - 4) % 7 or 7)
    weeks_to_run = weeks if weeks is not None else council_weeks(last_friday.strftime("%Y-%m-%d"))
    universe = sorted(set(names if names is not None else STOCK_UNIVERSE))
    council_names = sorted({t for _, _, b in weeks_to_run if b for t, _ in b})
    tickers = sorted(set(universe + council_names)) + EXTRA
    end = (_plus(last_friday.strftime("%Y-%m-%d"), 1) if weeks is None
           else _plus(weeks_to_run[-1][1], 5))
    raw = {t: Series(r) for t, r in bars_by_ticker(download(tickers, False, end, start)).items()}
    adj = {t: Series(r) for t, r in bars_by_ticker(download(tickers, True, end, start)).items()}
    from scan_pipeline.fetch_market_data import _business_days_between

    # ---- point-in-time patches (see module docstring) ----
    state = {"eligible": [], "tnx": None, "counts": {}}
    neutral = wiki_signals.WikiSignals({}, {}, ["lab-neutral"], set(), fetch_ok=True)
    wiki_signals.get_signals = lambda refresh=False: neutral
    for mod in (cecil, marky, ophelia):
        mod.scan_universe = lambda as_of=None: state["eligible"]
    cecil.get_pe = lambda ticker, date=None: None
    cecil.PE_MAP = {}
    marky.load_10y_yield = lambda: state["tnx"]
    consensus.realized_hit_counts = lambda *a, **k: {s: tuple(v) for s, v in state["counts"].items()}

    from scan_pipeline.utils import data_utils
    engines = {"cecil": cecil, "marky": marky, "ophelia": ophelia, "data_utils": data_utils}
    knobs = dict(knobs or {})
    drop = knobs.get("drop")
    feed = earnings if knobs.get("earnings", True) else None
    builder = knobs.get("sector_map_builder")      # (names, adj, weeks) -> (SECTOR_MAP stand-in, offensive, defensive)
    if builder:
        smap, off, dfn = builder(universe, adj, weeks_to_run)
        knobs.update({"data_utils.SECTOR_MAP": smap, "ophelia.OFFENSIVE_SECTORS": off,
                      "ophelia.DEFENSIVE_SECTORS": dfn})
    _set_knobs(engines, knobs)
    _install_taps(engines)
    _TAP["capture"] = capture

    personas = get_initial_personas()
    if not isinstance(personas, dict):
        personas = {p.name: p for p in personas}

    rows = []
    for label, W, council_book in weeks_to_run:
        _TAP["week"] = W
        cache = {}
        for t in universe + ["SPY"]:
            s = raw.get(t)
            if s:
                hist = _aggregate_weekly(s.before(W, LOOKBACK_DAYS))
                if hist:
                    cache[t] = hist
        eligible = [t for t in universe if len(cache.get(t, [])) >= MIN_WEEKS]
        state["eligible"] = eligible
        state["tnx"] = raw["^TNX"].last_close_before(W) if "^TNX" in raw else None
        vix = raw["^VIX"].last_close_before(W) if "^VIX" in raw else None
        F = cache["SPY"][-1].date

        weekly_returns = {t: h[-1].return_ for t, h in cache.items()}
        stock_data = {}
        for t in eligible:
            rv, mdd = _risk_stats(cache[t])
            nxt = _next_report(feed.get(t), F) if feed else None
            stock_data[t] = {
                "context": generate_deterministic_context(t, weekly_returns[t], F),
                "pe": None, "sector": get_sector(t), "fundamentals": None,
                "realized_vol": rv, "max_drawdown": mdd,
                "earnings_date": nxt,
                "earnings_trading_days": _business_days_between(F, nxt) if nxt else None,
            }
        market_data = {
            "date": W, "vix": str(vix), "weeklyReturns": weekly_returns,
            "stockData": stock_data, "priceMap": {},
            "market_conditions": {"fed_stance": "Neutral.", "world_events": "-"},
            "auditDates": {"monday": W, "friday": F}, "dataSource": "engine-lab",
        }

        with contextlib.redirect_stdout(io.StringIO()):
            vote = consensus.merit_weights(["Cecil", "Marky", "Ophelia"])
            c = cecil.analyze(market_data, W)
            m = marky.analyze(market_data, W, cache)
            o = (ophelia.analyze(market_data, W, cache) if drop != "Ophelia"
                 else {"agent": "Ophelia", "stocks": []})
            res = consensus.aggregate(c, m, o, personas)

        def ret(t):
            s = adj.get(t)
            r = s.week_return(W) if s else None
            return 0.0 if r is None else r      # untradeable -> flat, same rule everywhere

        if capture is not None:
            wk = capture.setdefault(W, {})
            wk["label"] = label
            wk["ret"] = {t: ret(t) for t in eligible}
            wk["sector"] = {t: get_sector(t) for t in eligible}
            # the three sector signals, per ticker, from the same weekly bars
            wk["last_week"] = {t: cache[t][-1].return_ for t in eligible}
            wk["prior_week"] = {t: cache[t][-2].return_ for t in eligible if len(cache[t]) >= 2}
            wk["rs_12_1"] = {t: r for t in eligible
                             if (r := ophelia._weekly_rs_12_1(cache[t][-12:])) is not None}

        solo = knobs.get("solo")          # {"solo": "Ophelia"}: that engine's five, equal, no consensus
        if solo:
            picks = {"Cecil": c, "Marky": m, "Ophelia": o}[solo].get("stocks", [])[:5]
            book = [(x["ticker"], 1.0 / len(picks), solo) for x in picks]
        else:
            book = [(t, w, res.attribution.get(t)) for t, w in res.portfolio.items()]
        spy = adj["SPY"].week_return(W) or 0.0
        book_ret = sum(w * ret(t) for t, w, _ in book)
        if council_book is False:
            council_ret = None                  # no Council that week
        else:
            council_ret = sum(w * ret(t) for t, w in council_book) if council_book else 0.0
        ew = statistics.fmean(ret(t) for t in eligible)

        weights = sorted((w for _, w, _ in book), reverse=True)
        rng = random.Random(f"{SEED}-{W}")
        draws = ([sum(w * ret(t) for t, w in zip(rng.sample(eligible, len(weights)), weights))
                  for _ in range(RANDOM_DRAWS)] if weights else [0.0])
        rand_mean = statistics.fmean(draws)
        pctile = sum(1 for x in draws if x < book_ret) / len(draws)

        for t, w, s in book:
            if s:
                rec = state["counts"].setdefault(s, [0, 0])
                rec[1] += 1
                rec[0] += 1 if ret(t) > 0 else 0

        rows.append({
            "week": label, "monday": W, "friday_before": F, "eligible": len(eligible),
            "tnx": state["tnx"], "vix": vix,
            "vote": {k: round(v, 4) for k, v in vote.items()},
            "proposals": {"Cecil": [x["ticker"] for x in c.get("stocks", [])],
                          "Marky": [x["ticker"] for x in m.get("stocks", [])],
                          "Ophelia": [x["ticker"] for x in o.get("stocks", [])]},
            "book": [{"ticker": t, "weight": round(w, 4), "sponsor": s, "ret": round(ret(t), 6)}
                     for t, w, s in book],
            "invested": round(sum(w for _, w, _ in book), 4),
            "sponsors": sorted({s for _, _, s in book if s}),
            "council_book": ([{"ticker": t, "weight": round(w, 4), "ret": round(ret(t), 6)}
                              for t, w in council_book] if council_book
                             else ("ABORT (cash)" if council_book is None else None)),
            "council_invested": round(sum(w for _, w in council_book), 4) if council_book else 0.0,
            "book_ret": book_ret, "council_ret": council_ret, "spy_ret": spy,
            "alpha": book_ret - spy,
            "council_alpha": None if council_ret is None else council_ret - spy,
            "earnings_skipped": {e: [x["ticker"] for x in p.get("earnings_skipped") or []]
                                 for e, p in (("Cecil", c), ("Marky", m), ("Ophelia", o))},
            "ew_ret": ew, "rand_mean": rand_mean, "vs_random": book_ret - rand_mean,
            "pctile_vs_random": pctile,
        })
        if verbose and council_ret is not None:
            print(f"  {label}  replay {book_ret*100:+6.2f}% (a {(book_ret-spy)*100:+5.2f}, "
                  f"inv {sum(w for _, w, _ in book):4.0%}, pctile {pctile:4.0%})  "
                  f"council {council_ret*100:+6.2f}% (a {(council_ret-spy)*100:+5.2f})  "
                  f"SPY {spy*100:+5.2f}%  EW {ew*100:+5.2f}%  "
                  f"{','.join(t for t, _, _ in book)}")
    return rows


# --------------------------------------------------------------------------
# summary
# --------------------------------------------------------------------------
def _tstat(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    sd = statistics.stdev(xs)
    return statistics.fmean(xs) / (sd / math.sqrt(n)) if sd > 0 else 0.0


def _curve(xs):
    eq, peak, mdd = 1.0, 1.0, 0.0
    for x in xs:
        eq *= 1 + x
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    return eq - 1, mdd


def summarize(rows):
    n = len(rows)
    al = [r["alpha"] for r in rows]
    vr = [r["vs_random"] for r in rows]
    b_cum, b_dd = _curve([r["book_ret"] for r in rows])
    has_council = all(r["council_ret"] is not None for r in rows)
    cal = [r["council_alpha"] for r in rows] if has_council else [0.0, 0.0]
    c_cum, c_dd = _curve([r["council_ret"] for r in rows]) if has_council else (0.0, 0.0)
    s_cum, s_dd = _curve([r["spy_ret"] for r in rows])
    e_cum, _ = _curve([r["ew_ret"] for r in rows])
    return {
        "weeks": n,
        "replay": {"mean_alpha": statistics.fmean(al), "alpha_t": _tstat(al),
                   "weeks_beating_spy": sum(1 for x in al if x > 0) / n,
                   "mean_vs_random": statistics.fmean(vr), "vs_random_t": _tstat(vr),
                   "mean_pctile_vs_random": statistics.fmean(r["pctile_vs_random"] for r in rows),
                   "mean_invested": statistics.fmean(r["invested"] for r in rows),
                   "mean_sponsors": statistics.fmean(len(r["sponsors"]) for r in rows),
                   "cumulative": b_cum, "max_drawdown": b_dd},
        "council": ({"mean_alpha": statistics.fmean(cal), "alpha_t": _tstat(cal),
                     "weeks_beating_spy": sum(1 for x in cal if x > 0) / n,
                     "mean_invested": statistics.fmean(r["council_invested"] for r in rows),
                     "cumulative": c_cum, "max_drawdown": c_dd} if has_council else None),
        "spy": {"cumulative": s_cum, "max_drawdown": s_dd},
        "equal_weight": {"cumulative": e_cum},
    }


def paired(rows, base_rows):
    """Variant minus baseline, week by week, on book return."""
    d = [r["book_ret"] - b["book_ret"] for r, b in zip(rows, base_rows)]
    best = max(range(len(d)), key=lambda i: d[i])
    rest = d[:best] + d[best + 1:]
    return {"mean_diff": statistics.fmean(d), "diff_t": _tstat(d),
            "weeks_better": sum(1 for x in d if x > 0), "weeks_same": sum(1 for x in d if x == 0),
            "mean_diff_without_best_week": statistics.fmean(rest) if rest else 0.0,
            "diff_by_week": d}


# --------------------------------------------------------------------------
# diagnostics: does each scoring input predict the next week at all?
# --------------------------------------------------------------------------
OPHELIA_FIELDS = ["score", "sector_rotation_score", "flow_term", "market_regime_score",
                  "risk_adjusted_score", "rel_term", "weekly_return", "four_week_return", "vol"]
MARKY_FIELDS = ["score", "momentum_score", "trend_score", "volatility_score", "volume_score",
                "four_week_return", "momentum_return", "dist_ma", "std_dev"]
SECTOR_SIGNALS = ["last_week", "prior_week", "rs_12_1"]


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2.0          # ties share their average rank
        i = j + 1
    return out


def spearman(a, b):
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den > 0 else 0.0


def _ic_summary(ics):
    return {"mean_ic": statistics.fmean(ics) if ics else None, "t": _tstat(ics),
            "weeks_positive": sum(1 for x in ics if x > 0), "weeks": len(ics),
            "ic_by_week": [round(x, 4) for x in ics]}


def diagnostics(capture):
    """Rank IC of every scoring input with the following week's return.

    Stock level: each input vs the ticker's own next-week return, across every
    eligible ticker, one IC per week. Sector level: each sector signal vs the
    sector's next-week equal-weight return (8 sectors a week), plus how the
    sector each signal ranks first did against the universe the next week.
    """
    weeks = sorted(capture)
    out = {"stock": {}, "sector": {}}
    for engine, fields in (("ophelia", OPHELIA_FIELDS), ("marky", MARKY_FIELDS)):
        for f in fields:
            ics = []
            for W in weeks:
                wk = capture[W]
                pairs = [(s[f], wk["ret"][s["ticker"]]) for s in wk.get(engine, [])
                         if s.get(f) is not None and s["ticker"] in wk["ret"]]
                if len(pairs) >= 20:
                    ics.append(spearman([p[0] for p in pairs], [p[1] for p in pairs]))
            out["stock"][f"{engine}.{f}"] = _ic_summary(ics)
    for sig in SECTOR_SIGNALS:
        ics, top_excess, tops = [], [], []
        for W in weeks:
            wk = capture[W]
            by = {}
            for t, v in wk[sig].items():
                by.setdefault(wk["sector"][t], []).append((v, wk["ret"][t]))
            sectors = sorted(by)
            signal = [statistics.fmean(v for v, _ in by[s]) for s in sectors]
            nxt = [statistics.fmean(r for _, r in by[s]) for s in sectors]
            universe = statistics.fmean(wk["ret"].values())
            ics.append(spearman(signal, nxt))
            top = sectors[max(range(len(sectors)), key=lambda i: signal[i])]
            tops.append(top)
            top_excess.append(nxt[sectors.index(top)] - universe)
        out["sector"][sig] = dict(_ic_summary(ics), **{
            "top_sector_by_week": tops,
            "top_sector_excess_by_week": [round(x, 5) for x in top_excess],
            "top_sector_mean_excess": statistics.fmean(top_excess),
            "top_sector_weeks_beating_universe": sum(1 for x in top_excess if x > 0)})
    return out


def _print_pass2(summaries, diag):
    print(f"\n  {'variant':<11} {'alpha/wk':>9} {'t':>6} {'>SPY':>5} {'vs rand':>8} {'pctile':>7} "
          f"{'vs base':>8} {'t':>6} {'better':>7} {'w/o best':>9} {'cum':>7} {'maxDD':>7} {'inv':>5}")
    for name, s in summaries.items():
        r, p = s["replay"], s.get("vs_baseline")
        pb = (f"{p['mean_diff']*100:+7.2f}% {p['diff_t']:+6.2f} "
              f"{p['weeks_better']:>3}/{s['weeks']:<3} {p['mean_diff_without_best_week']*100:+8.2f}%"
              if p else f"{'--':>8} {'':>6} {'':>7} {'':>9}")
        print(f"  {name:<11} {r['mean_alpha']*100:+8.2f}% {r['alpha_t']:+6.2f} "
              f"{round(r['weeks_beating_spy']*s['weeks']):>3}/{s['weeks']} "
              f"{r['mean_vs_random']*100:+7.2f}% {r['mean_pctile_vs_random']:7.0%} {pb} "
              f"{r['cumulative']*100:+6.1f}% {r['max_drawdown']*100:+6.1f}% {r['mean_invested']:5.0%}")
    print("\n  stock-level rank IC with next week's return (mean over weeks, t, weeks > 0)")
    for k, v in diag["stock"].items():
        if v["mean_ic"] is not None:
            print(f"    {k:<32} {v['mean_ic']:+.3f}  t {v['t']:+5.2f}  {v['weeks_positive']}/{v['weeks']}")
    print("\n  sector signals (8 sectors): rank IC with next week, and the #1 sector's next week vs universe")
    for k, v in diag["sector"].items():
        print(f"    {k:<11} IC {v['mean_ic']:+.3f} (t {v['t']:+5.2f}, {v['weeks_positive']}/{v['weeks']})   "
              f"#1 sector {v['top_sector_mean_excess']*100:+.2f}%/wk vs universe, "
              f"beat it {v['top_sector_weeks_beating_universe']}/{v['weeks']}   "
              f"{', '.join(v['top_sector_by_week'])}")


def main_pass2(quiet=False):
    runs, summaries, capture = {}, {}, {}
    for name, knobs in VARIANTS.items():
        rows = run(verbose=False, knobs=knobs, capture=capture if name == "baseline" else None,
                   names=frozen_universe())
        runs[name] = rows
        summaries[name] = summarize(rows)
        if name != "baseline":
            summaries[name]["vs_baseline"] = paired(rows, runs["baseline"])
        if not quiet:
            print(f"  {name:<11} replayed {len(rows)} weeks")
    # the O-rs+ inputs, for the stock-level IC of the multi-week stock signal
    cap_rs = {}
    run(verbose=False, knobs=VARIANTS["O-rs+"], capture=cap_rs, names=frozen_universe())
    diag = diagnostics(capture)
    rs_diag = diagnostics(cap_rs)
    for f in ("score", "sector_rotation_score", "flow_term", "risk_adjusted_score", "weekly_return"):
        diag["stock"][f"ophelia[O-rs+].{f}"] = rs_diag["stock"][f"ophelia.{f}"]
    _print_pass2(summaries, diag)
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "pass2_variants.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"pass": 2, "variants": VARIANTS,
                   "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "summaries": summaries, "diagnostics": diag,
                   "books": {n: [{"week": r["week"], "book": r["book"], "book_ret": r["book_ret"],
                                  "alpha": r["alpha"], "pctile_vs_random": r["pctile_vs_random"]}
                                 for r in rows] for n, rows in runs.items()}},
                  fh, indent=1, default=float)
        fh.write("\n")
    return runs, summaries, diag


def _halves(xs):
    h = len(xs) // 2
    return statistics.fmean(xs[:h]), statistics.fmean(xs[h:])


def pass3_tests(summaries, diag, diag_new):
    """The registered Pass 3 tests (lab/README.md), computed, not judged by eye."""
    base = summaries["base"]["replay"]
    ic3 = diag["stock"]["marky.four_week_return"]
    ic_skip = diag_new["stock"]["marky.momentum_return"]
    ex_last = diag["sector"]["last_week"]["top_sector_excess_by_week"]
    ex_prior = diag["sector"]["prior_week"]["top_sector_excess_by_week"]
    gap = [a - b for a, b in zip(ex_last, ex_prior)]
    h1 = {"ic_3w": ic3["mean_ic"], "ic_3w_t": ic3["t"],
          "ic_3w_halves": _halves(ic3["ic_by_week"]),
          "ic_skip": ic_skip["mean_ic"], "ic_skip_t": ic_skip["t"],
          "pass": ic3["t"] <= -2 and ic_skip["mean_ic"] >= 0}
    h2 = {"last_week_top_excess": statistics.fmean(ex_last), "t": _tstat(ex_last),
          "weeks_beating_universe": sum(1 for x in ex_last if x > 0),
          "last_minus_prior": statistics.fmean(gap), "last_minus_prior_t": _tstat(gap),
          "halves": _halves(ex_last),
          "pass": statistics.fmean(ex_last) > 0 and _tstat(ex_last) >= 2 and statistics.fmean(gap) > 0}
    verdicts = {}
    for name, mech in (("O-last", h2["pass"]), ("M-skip", h1["pass"]),
                       ("O-last+M-skip", h1["pass"] and h2["pass"])):
        v = summaries[name]["vs_base"]
        book = v["mean_diff"] > 0 and summaries[name]["replay"]["mean_vs_random"] >= base["mean_vs_random"]
        stable = v["first_half_mean"] > 0 and v["second_half_mean"] > 0
        verdicts[name] = {"mechanism": mech, "book": book, "stable": stable,
                          "passes": mech and book and stable}
    ns = summaries["no-screen"]
    h3 = {"weeks_screen_changed_book": ns["vs_base"]["weeks_changed"],
          "base_minus_no_screen": -ns["vs_base"]["mean_diff"], "t": -ns["vs_base"]["diff_t"],
          "worst_week_base": summaries["base"]["worst_week"], "worst_week_no_screen": ns["worst_week"],
          "max_dd_base": base["max_drawdown"], "max_dd_no_screen": ns["replay"]["max_drawdown"]}
    return {"H1_short_horizon_reversal": h1, "H2_stale_anchor": h2,
            "H3_earnings_screen": h3, "verdicts": verdicts}


def main_pass3(quiet=False):
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
    frozen = frozen_universe()
    cal = earnings_calendar(frozen)
    hweeks = history_weeks(HISTORY_FIRST_MONDAY, HISTORY_LAST_MONDAY)
    runs, summaries, cap_base, cap_new = {}, {}, {}, {}
    for name, knobs in VARIANTS3.items():
        cap = cap_base if name == "base" else (cap_new if name == "O-last+M-skip" else None)
        rows = run(verbose=False, knobs=knobs, capture=cap, weeks=hweeks,
                   start=HISTORY_DATA_START, earnings=cal, names=frozen)
        runs[name] = rows
        summ = summarize(rows)
        summ["worst_week"] = min(r["book_ret"] for r in rows)
        if name != "base":
            v = paired(rows, runs["base"])
            v["first_half_mean"], v["second_half_mean"] = _halves(v["diff_by_week"])
            v["weeks_changed"] = sum(1 for r, b in zip(rows, runs["base"])
                                     if [x["ticker"] for x in r["book"]] != [x["ticker"] for x in b["book"]])
            summ["vs_base"] = v
        summaries[name] = summ
        if not quiet:
            print(f"  {name:<14} replayed {len(rows)} history weeks")
    council = {n: run(verbose=False, knobs=k, earnings=cal, names=frozen) for n, k in VARIANTS3.items()}
    council_summ = {}
    for n, rows in council.items():
        council_summ[n] = summarize(rows)
        if n != "base":
            council_summ[n]["vs_base"] = paired(rows, council["base"])
    diag, diag_new = diagnostics(cap_base), diagnostics(cap_new)
    tests = pass3_tests(summaries, diag, diag_new)

    print(f"\n  {len(hweeks)} history weeks, {hweeks[0][0]} .. {hweeks[-1][0]} (the Council never ran them)")
    print(f"  {'variant':<14} {'alpha/wk':>9} {'t':>6} {'>SPY':>7} {'vs rand':>8} {'pctile':>7} "
          f"{'vs base':>8} {'t':>6} {'1st half':>9} {'2nd half':>9} {'cum':>8} {'maxDD':>7}")
    for name, sm in summaries.items():
        r, v = sm["replay"], sm.get("vs_base")
        vb = (f"{v['mean_diff']*100:+7.2f}% {v['diff_t']:+6.2f} {v['first_half_mean']*100:+8.2f}% "
              f"{v['second_half_mean']*100:+8.2f}%" if v else f"{'--':>8} {'':>6} {'':>9} {'':>9}")
        print(f"  {name:<14} {r['mean_alpha']*100:+8.2f}% {r['alpha_t']:+6.2f} "
              f"{round(r['weeks_beating_spy']*sm['weeks']):>3}/{sm['weeks']:<3} {r['mean_vs_random']*100:+7.2f}% "
              f"{r['mean_pctile_vs_random']:7.0%} {vb} {r['cumulative']*100:+7.1f}% {r['max_drawdown']*100:+6.1f}%")
    h1, h2, h3 = (tests["H1_short_horizon_reversal"], tests["H2_stale_anchor"],
                  tests["H3_earnings_screen"])
    print(f"\n  H1 3-week return IC {h1['ic_3w']:+.3f} (t {h1['ic_3w_t']:+.2f}; halves "
          f"{h1['ic_3w_halves'][0]:+.3f} / {h1['ic_3w_halves'][1]:+.3f}); skip-a-month return IC "
          f"{h1['ic_skip']:+.3f} (t {h1['ic_skip_t']:+.2f})  -> mechanism {'PASS' if h1['pass'] else 'fail'}")
    print(f"  H2 last week's top sector vs universe next week {h2['last_week_top_excess']*100:+.2f}%/wk "
          f"(t {h2['t']:+.2f}, beat it {h2['weeks_beating_universe']}/{len(hweeks)}; halves "
          f"{h2['halves'][0]*100:+.2f} / {h2['halves'][1]*100:+.2f}); minus the week-before-last's "
          f"{h2['last_minus_prior']*100:+.2f}%/wk (t {h2['last_minus_prior_t']:+.2f})  -> mechanism "
          f"{'PASS' if h2['pass'] else 'fail'}")
    print(f"  H3 screen changed the book in {h3['weeks_screen_changed_book']}/{len(hweeks)} weeks; "
          f"base minus no-screen {h3['base_minus_no_screen']*100:+.2f}%/wk (t {h3['t']:+.2f}); worst week "
          f"{h3['worst_week_base']*100:+.2f}% vs {h3['worst_week_no_screen']*100:+.2f}%; max DD "
          f"{h3['max_dd_base']*100:.1f}% vs {h3['max_dd_no_screen']*100:.1f}%")
    for name, v in tests["verdicts"].items():
        print(f"  verdict {name:<14} mechanism {'yes' if v['mechanism'] else 'no ':<3}  book "
              f"{'yes' if v['book'] else 'no ':<3}  stable {'yes' if v['stable'] else 'no ':<3}  -> "
              f"{'PASSES' if v['passes'] else 'does not pass'}")
    print("\n  in-sample reference, the Council's own weeks:")
    for n, sm in council_summ.items():
        v = sm.get("vs_base")
        print(f"    {n:<14} alpha {sm['replay']['mean_alpha']*100:+.2f}%/wk, vs random "
              f"{sm['replay']['mean_vs_random']*100:+.2f}%/wk, cum {sm['replay']['cumulative']*100:+.1f}%, "
              f"max DD {sm['replay']['max_drawdown']*100:.1f}%"
              + (f", vs base {v['mean_diff']*100:+.2f}%/wk ({v['weeks_better']}/{sm['weeks']} better)" if v else ""))

    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "pass3_history.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"pass": 3, "variants": VARIANTS3, "window": [hweeks[0][0], hweeks[-1][0]],
                   "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "tests": tests, "summaries": summaries, "council_weeks": council_summ,
                   "diagnostics": diag,
                   "diagnostics_new_inputs": {k: v for k, v in diag_new["stock"].items()
                                              if k in ("marky.momentum_return", "ophelia.sector_rotation_score",
                                                       "ophelia.flow_term", "ophelia.score", "marky.score")},
                   "books": {n: [{"week": r["week"], "book": [(b["ticker"], b["weight"]) for b in r["book"]],
                                  "book_ret": round(r["book_ret"], 6), "spy_ret": round(r["spy_ret"], 6),
                                  "skipped": r["earnings_skipped"]} for r in rows]
                             for n, rows in runs.items()}},
                  fh, indent=1, default=float)
        fh.write("\n")
    return tests


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--pass", dest="pass_", type=int, choices=(1, 2, 3), default=2)
    args = ap.parse_args(argv)
    if args.pass_ == 3:
        main_pass3(quiet=args.quiet)
        return
    if args.pass_ == 2:
        main_pass2(quiet=args.quiet)
        return
    rows = run(verbose=not args.quiet, names=frozen_universe())
    s = summarize(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "pass1_baseline.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"pass": 1, "variant": "engines as configured 2026-09-21",
                   "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "summary": s, "weeks": rows}, fh, indent=1, default=float)
        fh.write("\n")
    r, c = s["replay"], s["council"]
    print(f"\n  {s['weeks']} Council weeks")
    print(f"  replayed engines : mean alpha {r['mean_alpha']*100:+.2f}%/wk (t={r['alpha_t']:+.2f}), "
          f"beat SPY {r['weeks_beating_spy']:.0%} of weeks, vs random {r['mean_vs_random']*100:+.2f}%/wk "
          f"(t={r['vs_random_t']:+.2f}, avg pctile {r['mean_pctile_vs_random']:.0%}), invested "
          f"{r['mean_invested']:.0%}, sponsors {r['mean_sponsors']:.1f}")
    print(f"  real Council     : mean alpha {c['mean_alpha']*100:+.2f}%/wk (t={c['alpha_t']:+.2f}), "
          f"beat SPY {c['weeks_beating_spy']:.0%} of weeks, invested {c['mean_invested']:.0%}")
    print(f"  cumulative       : replay {r['cumulative']*100:+.1f}%  council {c['cumulative']*100:+.1f}%  "
          f"SPY {s['spy']['cumulative']*100:+.1f}%  equal-weight {s['equal_weight']['cumulative']*100:+.1f}%")
    print(f"  max drawdown     : replay {r['max_drawdown']*100:.1f}%  council {c['max_drawdown']*100:.1f}%  "
          f"SPY {s['spy']['max_drawdown']*100:.1f}%")


if __name__ == "__main__":
    main()
