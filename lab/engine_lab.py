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

    python lab/engine_lab.py
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
    for rpt in sorted(REPORTS.glob("*-report.md")):
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
        else:
            book = None
        out.append((label, monday, book))
    return out


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def download(tickers, adjusted, end):
    """Daily bars for every ticker, cached on disk (lab/cache is gitignored)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"daily_{'adj' if adjusted else 'raw'}_{DATA_START}_{end}_{len(tickers)}.pkl"
    if path.exists():
        with open(path, "rb") as fh:
            return pickle.load(fh)
    import pandas as pd
    import yfinance as yf
    frames = []
    for i in range(0, len(tickers), 60):
        chunk = tickers[i:i + 60]
        df = yf.download(chunk, start=DATA_START, end=end, auto_adjust=adjusted,
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
def run(verbose=True):
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
    from scan_pipeline.engines import cecil, consensus, marky, ophelia
    from scan_pipeline.engines.personality import get_initial_personas
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _risk_stats
    from scan_pipeline.utils import wiki_signals
    from scan_pipeline.utils.data_utils import generate_deterministic_context, get_sector

    last_friday = date.today() - timedelta(days=(date.today().weekday() - 4) % 7 or 7)
    weeks_to_run = council_weeks(last_friday.strftime("%Y-%m-%d"))
    universe = sorted(set(STOCK_UNIVERSE))
    council_names = sorted({t for _, _, b in weeks_to_run if b for t, _ in b})
    tickers = sorted(set(universe + council_names)) + EXTRA
    end = _plus(last_friday.strftime("%Y-%m-%d"), 1)
    raw = {t: Series(r) for t, r in bars_by_ticker(download(tickers, False, end)).items()}
    adj = {t: Series(r) for t, r in bars_by_ticker(download(tickers, True, end)).items()}

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

    personas = get_initial_personas()
    if not isinstance(personas, dict):
        personas = {p.name: p for p in personas}

    rows = []
    for label, W, council_book in weeks_to_run:
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
            stock_data[t] = {
                "context": generate_deterministic_context(t, weekly_returns[t], F),
                "pe": None, "sector": get_sector(t), "fundamentals": None,
                "realized_vol": rv, "max_drawdown": mdd,
                "earnings_date": None, "earnings_trading_days": None,
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
            o = ophelia.analyze(market_data, W, cache)
            res = consensus.aggregate(c, m, o, personas)

        def ret(t):
            s = adj.get(t)
            r = s.week_return(W) if s else None
            return 0.0 if r is None else r      # untradeable -> flat, same rule everywhere

        book = [(t, w, res.attribution.get(t)) for t, w in res.portfolio.items()]
        spy = adj["SPY"].week_return(W) or 0.0
        book_ret = sum(w * ret(t) for t, w, _ in book)
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
                              for t, w in council_book] if council_book else "ABORT (cash)"),
            "council_invested": round(sum(w for _, w in council_book), 4) if council_book else 0.0,
            "book_ret": book_ret, "council_ret": council_ret, "spy_ret": spy,
            "alpha": book_ret - spy, "council_alpha": council_ret - spy,
            "ew_ret": ew, "rand_mean": rand_mean, "vs_random": book_ret - rand_mean,
            "pctile_vs_random": pctile,
        })
        if verbose:
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
    cal = [r["council_alpha"] for r in rows]
    vr = [r["vs_random"] for r in rows]
    b_cum, b_dd = _curve([r["book_ret"] for r in rows])
    c_cum, c_dd = _curve([r["council_ret"] for r in rows])
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
        "council": {"mean_alpha": statistics.fmean(cal), "alpha_t": _tstat(cal),
                    "weeks_beating_spy": sum(1 for x in cal if x > 0) / n,
                    "mean_invested": statistics.fmean(r["council_invested"] for r in rows),
                    "cumulative": c_cum, "max_drawdown": c_dd},
        "spy": {"cumulative": s_cum, "max_drawdown": s_dd},
        "equal_weight": {"cumulative": e_cum},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    rows = run(verbose=not args.quiet)
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
