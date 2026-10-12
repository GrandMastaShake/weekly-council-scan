#!/usr/bin/env python3
"""Pass 21 -- beat-then-fall: earnings surprise and the next days (registered in lab/README.md, d1ba76f).

Events come from yfinance Ticker.get_earnings_dates (consensus estimate, reported EPS, surprise %, timestamp) for every name on the
S&P 500 as of 2024-09 (decides) and the 111 (reported). Report dates 2024-09-09 to 2026-07-03; a name's earlier quarters from the
same table give its beat streak. Prices are dividend-adjusted daily closes, market-adjusted against SPY, clipped at +/-40%.

    python lab/pass21_beat_fall.py fetch      # download and cache the earnings tables (no prices, no outcomes)
    python lab/pass21_beat_fall.py            # the four registered tests
    python lab/pass21_beat_fall.py smoke
"""
from __future__ import annotations

import bisect
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402
import pass15_exits as p15  # noqa: E402
import pass19_cecil_trap as p19  # noqa: E402

END = "2026-09-26"
FIRST, LAST = "2024-09-09", "2026-07-03"       # reaction-day window for the events
CLIP = 0.40
MIN_WEEK = 15                                   # events per reaction week for a cross-section
MIN_FLAG_WEEK = 3                               # flagged events per week for a flagged-minus-pool difference
NW_LAGS = 4
SURPRISE_CLIP = 100.0
EARN = lab.CACHE / "earnings_surprise.json"


# ------------------------------------------------------------------------------------------------ the earnings tables
def fetch(names):
    """{ticker: [[iso timestamp, estimate, reported, surprise%], ...]} from yfinance, cached; past quarters only."""
    cached = json.loads(EARN.read_text(encoding="utf-8")) if EARN.exists() else {}
    todo = [t for t in names if t not in cached]
    if not todo:
        return cached
    import yfinance as yf

    def one(t):
        for _ in range(3):
            try:
                ed = yf.Ticker(t).get_earnings_dates(limit=24)
                if ed is not None and len(ed):
                    rows = []
                    for ts, r in ed.iterrows():
                        rep, est, sur = r.get("Reported EPS"), r.get("EPS Estimate"), r.get("Surprise(%)")
                        if rep == rep and est == est and sur == sur:          # drop NaN: future or unreported quarters
                            rows.append([ts.isoformat(), float(est), float(rep), float(sur)])
                    return t, sorted(rows)
            except Exception:
                pass
        return t, []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, (t, rows) in enumerate(pool.map(one, todo)):
            cached[t] = rows
            if (i + 1) % 100 == 0:
                print(f"  fetched {i + 1}/{len(todo)}", flush=True)
    lab.CACHE.mkdir(parents=True, exist_ok=True)
    EARN.write_text(json.dumps(cached), encoding="utf-8")
    return cached


# ------------------------------------------------------------------------------------------------ events
def reaction_index(dates, ts):
    """Index of the reaction session: the report date for a report before 12:00 ET, else the next session."""
    day, hour = ts[:10], int(ts[11:13])
    i = bisect.bisect_left(dates, day)
    if i < len(dates) and dates[i] == day and hour >= 12:
        i += 1
    return i


def build_events(names, adj, tables):
    spy = adj["SPY"]
    events = []
    for t in names:
        s = adj.get(t)
        rows = tables.get(t) or []
        if s is None or not rows:
            continue
        streak_run = 0
        for k, (ts, est, rep, sur) in enumerate(rows):
            # streak = consecutive strictly positive surprises immediately before this report
            prior = 0
            for _, _, _, ps in reversed(rows[:k]):
                if ps > 0:
                    prior += 1
                else:
                    break
            streak_run = prior
            day = ts[:10]
            if not (FIRST <= day <= LAST):
                continue
            i = reaction_index(s.dates, ts)
            if i < 1 or i + 20 >= len(s.dates):
                continue
            d0, d1, d5, d20 = s.dates[i - 1], s.dates[i], s.dates[min(i + 4, len(s.dates) - 1)], s.dates[i + 20]

            def sp(a, b):
                ia, ib = bisect.bisect_right(spy.dates, a) - 1, bisect.bisect_right(spy.dates, b) - 1
                return spy.rows[ib]["close"] / spy.rows[ia]["close"] - 1 if ia >= 0 and ib >= 0 else None

            def clip(x):
                return max(-CLIP, min(CLIP, x))
            c = s.rows
            m1, m5, m20 = sp(d0, d1), sp(d0, d5), sp(d1, d20)
            if None in (m1, m5, m20):
                continue
            events.append({"t": t, "ts": ts, "react": d1, "week": lab._plus(d1, -datetime.strptime(d1, "%Y-%m-%d").weekday()),
                           "surprise": max(-SURPRISE_CLIP, min(SURPRISE_CLIP, sur)), "streak": streak_run,
                           "r1": clip(c[i]["close"] / c[i - 1]["close"] - 1) - m1,
                           "r5": clip(c[i + 4]["close"] / c[i - 1]["close"] - 1) - m5,
                           "d20": clip(c[i + 20]["close"] / c[i]["close"] - 1) - m20})
    return events


# ------------------------------------------------------------------------------------------------ tests
def rank_ic(x, y):
    from scipy.stats import spearmanr
    r = spearmanr(x, y).statistic
    return 0.0 if r != r else float(r)


def halves_of(weeks_vals):
    half = len(weeks_vals) // 2
    return statistics.fmean(weeks_vals[:half]), statistics.fmean(weeks_vals[half:])


def summarize(vals):
    """mean, Newey-West t, halves, median of a time-ordered weekly series."""
    if len(vals) < 8:
        return {"weeks": len(vals), "testable": False}
    h = halves_of(vals)
    return {"weeks": len(vals), "testable": True, "mean": statistics.fmean(vals), "t": p15.nw_t(vals, NW_LAGS), "halves": list(h),
            "median": statistics.median(vals)}


def run_tests(events):
    by_week = {}
    for e in events:
        by_week.setdefault(e["week"], []).append(e)
    weeks = sorted(w for w, es in by_week.items() if len(es) >= MIN_WEEK)
    out = {"events": len(events), "weeks_all": len(by_week), "weeks_used": len(weeks)}
    # V1: reaction -- the weekly cross-sectional Spearman IC of surprise with R5
    ic = [rank_ic([e["surprise"] for e in by_week[w]], [e["r5"] for e in by_week[w]]) for w in weeks]
    v1 = summarize(ic)
    v1["holds"] = bool(v1.get("testable") and v1["mean"] > 0 and v1["t"] >= 2 and all(h > 0 for h in v1["halves"]))
    out["V1 reaction (IC of surprise with R5)"] = v1
    # V2: beat-then-fall -- streak >= 8 and a positive surprise, against the rest of the same week, on R5
    d2, w2 = [], []
    for w in weeks:
        fl = [e["r5"] for e in by_week[w] if e["streak"] >= 8 and e["surprise"] > 0]
        rest = [e["r5"] for e in by_week[w] if not (e["streak"] >= 8 and e["surprise"] > 0)]
        if len(fl) >= MIN_FLAG_WEEK and rest:
            d2.append(statistics.fmean(fl) - statistics.fmean(rest))
            w2.append(w)
    v2 = summarize(d2)
    v2["flagged_events"] = sum(1 for e in events if e["streak"] >= 8 and e["surprise"] > 0)
    v2["holds"] = bool(v2.get("testable") and v2["mean"] <= -0.003 and v2["t"] <= -2 and all(h < 0 for h in v2["halves"]))
    out["V2 beat-then-fall (streak>=8 vs same-week rest, R5)"] = v2
    # V3: drift chair -- top surprise quintile of each week, D20, against the week's pool mean (the expectation of random draws)
    d3 = []
    for w in weeks:
        es = sorted(by_week[w], key=lambda e: e["surprise"], reverse=True)
        k = max(1, len(es) // 5)
        d3.append(statistics.fmean(e["d20"] for e in es[:k]) - statistics.fmean(e["d20"] for e in es))
    v3 = summarize(d3)
    v3["passes"] = bool(v3.get("testable") and v3["t"] >= 2 and all(h > 0 for h in v3["halves"]) and v3["median"] > 0)
    out["V3 drift chair (top-quintile surprise, D20)"] = v3
    # V4: big beat then fall -- surprise over +10% and a streak of 4+, D20, against the week's pool mean
    d4 = []
    for w in weeks:
        fl = [e["d20"] for e in by_week[w] if e["surprise"] > 10 and e["streak"] >= 4]
        if len(fl) >= MIN_FLAG_WEEK:
            d4.append(statistics.fmean(fl) - statistics.fmean(e["d20"] for e in by_week[w]))
    v4 = summarize(d4)
    v4["flagged_events"] = sum(1 for e in events if e["surprise"] > 10 and e["streak"] >= 4)
    v4["holds"] = bool(v4.get("testable") and v4["t"] <= -2 and all(h < 0 for h in v4["halves"]))
    out["V4 big beat then fall (surprise>10, streak>=4, D20)"] = v4
    # descriptive: pooled deciles of surprise
    es = sorted(events, key=lambda e: e["surprise"])
    n = len(es)
    out["deciles"] = [{"decile": d + 1, "surprise_mid": statistics.median(e["surprise"] for e in es[d * n // 10:(d + 1) * n // 10]),
                       "r1": statistics.fmean(e["r1"] for e in es[d * n // 10:(d + 1) * n // 10]),
                       "r5": statistics.fmean(e["r5"] for e in es[d * n // 10:(d + 1) * n // 10]),
                       "d20": statistics.fmean(e["d20"] for e in es[d * n // 10:(d + 1) * n // 10])} for d in range(10)]
    return out


def show(title, res):
    print(f"\n  {title}: {res['events']} events, {res['weeks_used']} reaction weeks with {MIN_WEEK}+ events (of {res['weeks_all']})")
    for k, v in res.items():
        if not k.startswith("V"):
            continue
        if not v.get("testable"):
            print(f"  {k:<58} untestable ({v['weeks']} weeks)")
            continue
        flag = "HOLDS" if v.get("holds") else ("PASSES" if v.get("passes") else "no")
        extra = f", {v['flagged_events']} flagged events" if "flagged_events" in v else ""
        print(f"  {k:<58} mean {v['mean']*100:+.3f}%  t {v['t']:+.2f}  halves {v['halves'][0]*100:+.3f}/{v['halves'][1]*100:+.3f}  median {v['median']*100:+.3f}  "
              f"({v['weeks']} weeks{extra})  -> {flag}")
    print("  deciles of surprise (pooled): " + "  ".join(f"D{d['decile']}: {d['surprise_mid']:+.0f}% R1 {d['r1']*100:+.2f} R5 {d['r5']*100:+.2f} D20 {d['d20']*100:+.2f}" for d in (res["deciles"][i] for i in (0, 3, 6, 9))))


def main(mode=""):
    U = p9.universes()
    universes = {p11.CLEAN: p9.sp500_asof(), p9.REFERENCE: U[p9.REFERENCE]}
    if mode == "smoke":
        universes = {p9.REFERENCE: U[p9.REFERENCE][:40]}
    names_all = sorted({t for ns in universes.values() for t in ns})
    tables = fetch(names_all)
    if mode == "fetch":
        n_ev = sum(len(v) for v in tables.values())
        print(f"cached {len(tables)} tickers, {n_ev} reported quarters, {sum(1 for v in tables.values() if not v)} tickers with none -> {EARN}")
        return
    result = {"registered": "d1ba76f", "universes": {}}
    for uname, names in universes.items():
        tickers = sorted(set(names) | set(p19.ETFS)) + [x for x in lab.EXTRA if x not in names]
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, END, p4.HIST_START)).items()}
        events = build_events(names, adj, tables)
        res = run_tests(events)
        show(uname, res)
        result["universes"][uname] = {**res, "events_sample": events[:5]}
    clean = result["universes"].get(p11.CLEAN)
    if clean:
        v = {"V1 reaction holds": clean["V1 reaction (IC of surprise with R5)"].get("holds", False),
             "V2 beat-then-fall holds": clean["V2 beat-then-fall (streak>=8 vs same-week rest, R5)"].get("holds", False),
             "V3 drift chair passes": clean["V3 drift chair (top-quintile surprise, D20)"].get("passes", False),
             "V4 big beat then fall holds": clean["V4 big beat then fall (surprise>10, streak>=4, D20)"].get("holds", False)}
        result["verdicts"] = v
        print("\n  registered verdicts (the clean list): " + "; ".join(f"{k} {'YES' if ok else 'no'}" for k, ok in v.items()))
    out = lab.CACHE / "pass21.smoke.json" if mode == "smoke" else lab.RESULTS / "pass21_beat_fall.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
