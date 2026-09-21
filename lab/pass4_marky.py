#!/usr/bin/env python3
"""Pass 4 -- Marky v2, the chart (lab/council_v2.md).

Registered in lab/README.md before the run. Scores Marky's OWN top five under
each mode -- his job, not the Council's book -- against random fives drawn from
the same names, on the lab's basis (Monday open -> Friday close,
dividend-adjusted, cash earns zero):

  history  the 96 pre-Council weeks on the frozen 2026-09-21 universe: the
           mechanism test, with less look-ahead than the owner's list
  council  the Council's closed weeks on the owner's 111: the universe v2 uses

It also measures what each mode's ranking leans on. Its rank correlation with
a stock's 12-week volatility shows how much it prefers a calm tape, which is
Cecil's job. Its correlation with the 3-week return shows how much it chases
short-term strength, the input that ran backwards in Pass 2.

    python lab/pass4_marky.py
"""
from __future__ import annotations

import contextlib
import io
import json
import random
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

HIST_START = "2023-08-01"      # a year of weekly closes before 2024-09-09
COUNCIL_START = "2025-06-01"   # a year before the first Council week
SHORT_DAYS = lab.LOOKBACK_DAYS  # what production fetches today (range=3mo)
LONG_DAYS = 400                # about 57 weekly bars; v2 reads the last 52
TOP = 5
MODES = ("classic", "52w")
FIELDS = {"classic": ["score", "momentum_score", "trend_score", "volatility_score"],
          "52w": ["score", "range_pos", "to_high", "trend_score"]}


def replay(weeks, names, start, cal):
    from scan_pipeline.engines import marky
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    from scan_pipeline.utils import wiki_signals
    from scan_pipeline.utils.data_utils import compute_4_week_return, earnings_blackout

    end = lab._plus(weeks[-1][1], 5)
    tickers = sorted(set(names)) + lab.EXTRA
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, start)).items()}
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, start)).items()}

    neutral = wiki_signals.WikiSignals({}, {}, ["lab-neutral"], set(), fetch_ok=True)
    wiki_signals.get_signals = lambda refresh=False: neutral
    state = {"eligible": [], "tnx": None, "ranking": None}
    marky.scan_universe = lambda as_of=None: state["eligible"]
    marky.load_10y_yield = lambda: state["tnx"]
    real_log_ties = marky.log_ties

    def tap(scores, *a, **k):
        state["ranking"] = [dict(s) for s in scores]
        return real_log_ties(scores, *a, **k)
    marky.log_ties = tap

    rows = []
    try:
        for label, W, _ in weeks:
            short = {t: _aggregate_weekly(raw[t].before(W, SHORT_DAYS)) for t in names if t in raw}
            eligible = [t for t in names if len(short.get(t, [])) >= lab.MIN_WEEKS]
            long = {t: _aggregate_weekly(raw[t].before(W, LONG_DAYS)) for t in eligible}
            F = _aggregate_weekly(raw["SPY"].before(W, SHORT_DAYS))[-1].date
            stock = {}
            for t in eligible:
                nxt = lab._next_report(cal.get(t), F)
                stock[t] = {"earnings_date": nxt,
                            "earnings_trading_days": _business_days_between(F, nxt) if nxt else None}
            md = {"vix": str(raw["^VIX"].last_close_before(W)), "stockData": stock}
            state["eligible"] = eligible
            state["tnx"] = raw["^TNX"].last_close_before(W)

            def ret(t):
                s = adj.get(t)
                r = s.week_return(W) if s else None
                return 0.0 if r is None else r
            tradeable = [t for t in eligible if earnings_blackout(md, t) is None]
            nxt_ret = {t: ret(t) for t in eligible}
            vol12 = {t: statistics.pstdev([h.return_ for h in short[t][-12:]])
                     for t in eligible if len(short[t]) >= 3}
            ret3w = {t: compute_4_week_return(short[t][-4:]) for t in eligible}
            spy = adj["SPY"].week_return(W) or 0.0
            row = {"week": label, "spy": spy, "eligible": len(eligible)}
            for mode in MODES:
                marky.MARKY_MODE = mode
                state["ranking"] = None
                with contextlib.redirect_stdout(io.StringIO()):
                    marky.analyze(md, W, long if mode == "52w" else short)
                ranking = state["ranking"] or []
                picks = [s["ticker"] for s in ranking if earnings_blackout(md, s["ticker"]) is None][:TOP]
                book = statistics.fmean(nxt_ret[t] for t in picks) if picks else 0.0
                rng = random.Random(f"{lab.SEED}-{W}-{len(picks)}")
                draws = ([statistics.fmean(nxt_ret[t] for t in rng.sample(tradeable, len(picks)))
                          for _ in range(lab.RANDOM_DRAWS)] if picks else [0.0])
                ics = {}
                for f in FIELDS[mode]:
                    pairs = [(s[f], nxt_ret[s["ticker"]]) for s in ranking
                             if s.get(f) is not None and s["ticker"] in nxt_ret]
                    if len(pairs) >= 20:
                        ics[f] = lab.spearman([float(p[0]) for p in pairs], [p[1] for p in pairs])
                scored = [s for s in ranking if s["ticker"] in vol12]
                lean_vol = (lab.spearman([s["score"] for s in scored], [vol12[s["ticker"]] for s in scored])
                            if len(scored) >= 20 else None)
                lean_3w = (lab.spearman([s["score"] for s in scored], [ret3w[s["ticker"]] for s in scored])
                           if len(scored) >= 20 else None)
                row[mode] = {"picks": picks, "ret": book, "alpha": book - spy,
                             "vs_random": book - statistics.fmean(draws),
                             "pctile": sum(1 for d in draws if d < book) / len(draws),
                             "ic": ics, "lean_vol": lean_vol, "lean_3w": lean_3w, "scored": len(ranking)}
            rows.append(row)
    finally:
        marky.MARKY_MODE = "classic"
        marky.log_ties = real_log_ties
    return rows


def summarize(rows):
    out = {"weeks": len(rows)}
    for mode in MODES:
        r = [x[mode] for x in rows]
        cum, dd = lab._curve([x["ret"] for x in r])
        ic = {f: [x["ic"][f] for x in r if f in x["ic"]] for f in FIELDS[mode]}
        out[mode] = {
            "mean_ret": statistics.fmean(x["ret"] for x in r),
            "mean_alpha": statistics.fmean(x["alpha"] for x in r),
            "alpha_t": lab._tstat([x["alpha"] for x in r]),
            "mean_vs_random": statistics.fmean(x["vs_random"] for x in r),
            "vs_random_t": lab._tstat([x["vs_random"] for x in r]),
            "mean_pctile": statistics.fmean(x["pctile"] for x in r),
            "cumulative": cum, "max_drawdown": dd,
            "ic": {f: {"mean": statistics.fmean(v) if v else None, "t": lab._tstat(v),
                       "weeks_positive": sum(1 for z in v if z > 0), "weeks": len(v)} for f, v in ic.items()},
            "lean_vol": statistics.fmean(x["lean_vol"] for x in r if x["lean_vol"] is not None),
            "lean_3w": statistics.fmean(x["lean_3w"] for x in r if x["lean_3w"] is not None),
            "mean_scored": statistics.fmean(x["scored"] for x in r),
        }
    diff = [x["52w"]["ret"] - x["classic"]["ret"] for x in rows]
    h = len(diff) // 2
    out["paired_52w_minus_classic"] = {
        "mean": statistics.fmean(diff), "t": lab._tstat(diff),
        "weeks_better": sum(1 for d in diff if d > 0),
        "first_half": statistics.fmean(diff[:h]) if h else None,
        "second_half": statistics.fmean(diff[h:]) if h else None}
    return out


def verdict(hist):
    """The registered non-inferiority rule, computed (lab/README.md, Pass 4)."""
    to_high = hist["52w"]["ic"]["to_high"]
    p = hist["paired_52w_minus_classic"]
    harmful_mechanism = to_high["mean"] is not None and to_high["mean"] < 0 and to_high["t"] <= -2
    harmful_book = p["mean"] < 0 and p["t"] <= -2
    return {"mechanism_harmful": harmful_mechanism, "book_harmful": harmful_book,
            "v2_replaces_classic": not (harmful_mechanism or harmful_book)}


def show(name, s):
    print(f"\n  {name}: {s['weeks']} weeks")
    for mode in MODES:
        m = s[mode]
        ic = "  ".join(f"{f} {v['mean']:+.3f} (t {v['t']:+.2f})" for f, v in m["ic"].items() if v["mean"] is not None)
        print(f"    {mode:<8} top-{TOP} {m['mean_ret']*100:+.2f}%/wk, alpha {m['mean_alpha']*100:+.2f} "
              f"(t {m['alpha_t']:+.2f}), vs random {m['mean_vs_random']*100:+.2f} (t {m['vs_random_t']:+.2f}, "
              f"pctile {m['mean_pctile']:.0%}), cum {m['cumulative']*100:+.1f}%, max DD {m['max_drawdown']*100:.1f}%")
        print(f"             IC: {ic}")
        print(f"             leans: calm tape {m['lean_vol']:+.2f} (vs 12-wk volatility), "
              f"3-week chase {m['lean_3w']:+.2f}; names scored {m['mean_scored']:.0f}")
    p = s["paired_52w_minus_classic"]
    print(f"    52w minus classic: {p['mean']*100:+.2f}%/wk (t {p['t']:+.2f}), better {p['weeks_better']}/{s['weeks']}, "
          f"halves {p['first_half']*100:+.2f} / {p['second_half']*100:+.2f}")


def main():
    from scan_pipeline.config.tickers import COUNCIL_WATCHLIST
    frozen = lab.frozen_universe()
    cal = lab.earnings_calendar(sorted(set(frozen) | set(COUNCIL_WATCHLIST)))
    hist_rows = replay(lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY),
                       frozen, HIST_START, cal)
    today = date.today()
    last_friday = today - timedelta(days=(today.weekday() - 4) % 7 or 7)
    cw = lab.council_weeks(last_friday.strftime("%Y-%m-%d"))
    council_rows = replay(cw, list(COUNCIL_WATCHLIST), COUNCIL_START, cal)
    hist, council = summarize(hist_rows), summarize(council_rows)
    v = verdict(hist)
    show("history, frozen universe (mechanism)", hist)
    show("Council weeks, the owner's 111", council)
    print(f"\n  verdict: mechanism harmful {v['mechanism_harmful']}, book harmful {v['book_harmful']} -> "
          f"{'Marky v2 replaces classic in Council v2' if v['v2_replaces_classic'] else 'classic stays'}")
    lab.RESULTS.mkdir(parents=True, exist_ok=True)
    with open(lab.RESULTS / "pass4_marky.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"pass": 4, "generated": datetime.now().strftime("%Y-%m-%d %H:%M"), "verdict": v,
                   "history": hist, "council": council,
                   "weeks": {"history": hist_rows, "council": council_rows}}, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main()
