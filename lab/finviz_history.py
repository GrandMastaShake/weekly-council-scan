#!/usr/bin/env python3
"""Pass 31 -- ten years of Finviz earnings events (registered in lab/README.md, 7b6c4d7).

    python lab/finviz_history.py fetch      # the private data build: the earnings calendar in 12-week windows -> lab/cache (gitignored), no returns
    python lab/finviz_history.py            # T1 reaction, T2 drift, T3 the sleeve on the Monday clock, T4 beat-then-fall; and the yfinance comparison on S2
    python lab/finviz_history.py smoke      # plumbing on 40 names

Finviz data is for the owner's own use and this repo is public: the calendar and every per-event row stay in lab/cache; only counts and weekly aggregates are written
to lab/results/pass31_finviz_history.json.
"""
from __future__ import annotations

import bisect
import csv
import json
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass15_exits as p15  # noqa: E402
import pass21_beat_fall as p21  # noqa: E402

REGISTERED = "7b6c4d7"
CAL = lab.CACHE / "finviz_earnings_calendar.json"
ADDED = lab.LAB / "universe_sp500_added_2026-09-22.csv"
RESULT = lab.RESULTS / "pass31_finviz_history.json"
FETCH_FROM, END = "2015-10-05", "2026-10-13"
S1 = ("2016-01-04", "2026-07-03")
S2 = ("2020-10-01", "2026-07-03")
T4_FROM = "2018-01-02"
CLIP = 0.40
MIN_WEEK = 15
MIN_GROUP = 3
NW_LAGS = 4
STREAK = 8
CONFIRM_WEEKS = 12
TOP = 5
MIN_ACTIVE = 15


# ------------------------------------------------------------------------------------------------ the private data build
def fetch():
    import os
    root = os.environ.get("FINVIZ_CONNECTOR_PATH")
    if not root:
        raise SystemExit("set FINVIZ_CONNECTOR_PATH to the folder of the private finviz-elite connector")
    sys.path.insert(0, root)
    from finviz_elite import FinvizClient
    fv = FinvizClient(cache=False)
    rows, seen = [], set()
    a = datetime.strptime(FETCH_FROM, "%Y-%m-%d").date()
    end = datetime.strptime(END, "%Y-%m-%d").date()
    while a < end:
        b = a + timedelta(days=83)
        res = fv.export("calendar_earnings", dateFrom=a.isoformat(), dateTo=b.isoformat(), refresh=True)
        if not len(res):
            raise SystemExit(f"the window {a}..{b} came back empty: stop, do not build a calendar with a hole")
        for r in res.rows:
            key = (r["Ticker"], r["Date"])
            if key in seen:
                continue
            seen.add(key)
            rows.append([r["Date"], r["Ticker"], r["EPS Estimate"], r["EPS Actual"], r["EPS Surprise"], r["Revenue Surprise"], r["1-Day Price Reaction"]])
        print(f"  {a}..{b}: {len(res)} rows ({len(rows)} unique so far)", flush=True)
        a = a + timedelta(days=84)
    rows.sort(key=lambda x: (x[1], x[0]))
    lab.CACHE.mkdir(parents=True, exist_ok=True)
    CAL.write_text(json.dumps({"fetched": datetime.now().astimezone().isoformat(), "from": FETCH_FROM, "to": END,
                               "fields": ["Date", "Ticker", "EPS Estimate", "EPS Actual", "EPS Surprise", "Revenue Surprise", "1-Day Price Reaction"], "rows": rows}),
                   encoding="utf-8")
    print(f"  wrote {len(rows)} calendar rows for {len({r[1] for r in rows})} tickers to {CAL.name} (gitignored)")


def num(s):
    try:
        t = str(s).strip()
        return None if t in ("", "-") else float(t)
    except ValueError:
        return None


def universe():
    with open(ADDED, encoding="ascii") as fh:
        rows = [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))]
    return {r["ticker"]: (r["date_added"] or "") for r in rows}


# ------------------------------------------------------------------------------------------------ events
def build_events(cal_rows, adj, added, which="eps"):
    """Per-ticker quarters in time order -> events with a reaction day inside S1 that the name was a member for; streak counted on the same table."""
    by_t = {}
    for ts, t, est, act, sur, rsur, _ in cal_rows:
        by_t.setdefault(t, []).append((ts, num(sur), num(rsur)))
    events = []
    for t, rows in by_t.items():
        s = adj.get(t)
        if s is None or t not in added:
            continue
        rows = sorted(rows)
        clean = []                                     # one row per quarter: drop a row within 20 days of the previous (a moved date listed twice), keep the one with a surprise
        for ts, sur, rsur in rows:
            if clean and (datetime.strptime(ts[:10], "%Y-%m-%d") - datetime.strptime(clean[-1][0][:10], "%Y-%m-%d")).days < 20:
                if clean[-1][1] is None and sur is not None:
                    clean[-1] = (ts, sur, rsur)
                continue
            clean.append((ts, sur, rsur))
        for k, (ts, sur, rsur) in enumerate(clean):
            val = sur if which == "eps" else rsur
            if val is None:
                continue
            i = p21.reaction_index(s.dates, ts)
            if i < 1 or i + 20 >= len(s.dates):
                continue
            react = s.dates[i]
            if not (S1[0] <= react <= S1[1]) or (added[t] and added[t] >= react):
                continue
            prior = 0
            for _, ps, _ in reversed(clean[:k]):
                if ps is not None and ps > 0:
                    prior += 1
                else:
                    break
            spy = adj["SPY"]

            def sp(a, b):
                ia, ib = bisect.bisect_right(spy.dates, a) - 1, bisect.bisect_right(spy.dates, b) - 1
                return spy.rows[ib]["close"] / spy.rows[ia]["close"] - 1 if ia >= 0 and ib >= 0 else None
            d0, d1, d5, d20 = s.dates[i - 1], s.dates[i], s.dates[i + 4], s.dates[i + 20]
            m1, m5, m20 = sp(d0, d1), sp(d0, d5), sp(d1, d20)
            if None in (m1, m5, m20):
                continue
            c = s.rows

            def clip(x):
                return max(-CLIP, min(CLIP, x))
            events.append({"t": t, "ts": ts, "react": react, "week": lab._plus(react, -datetime.strptime(react, "%Y-%m-%d").weekday()),
                           "surprise": max(-100.0, min(100.0, val)), "streak": prior, "eps_surprise": sur,
                           "r1": clip(c[i]["close"] / c[i - 1]["close"] - 1) - m1, "r5": clip(c[i + 4]["close"] / c[i - 1]["close"] - 1) - m5,
                           "d20": clip(c[i + 20]["close"] / c[i]["close"] - 1) - m20})
    return events


def weekly(events):
    by = {}
    for e in events:
        by.setdefault(e["week"], []).append(e)
    return by


def stat(vals):
    if len(vals) < 8:
        return {"weeks": len(vals), "testable": False}
    h = p21.halves_of(vals)
    return {"weeks": len(vals), "testable": True, "mean": statistics.fmean(vals), "t": p15.nw_t(vals, NW_LAGS), "halves": list(h), "median": statistics.median(vals)}


def t1_t2(events):
    res = p21.run_tests(events)
    return res["V1 reaction (IC of surprise with R5)"], res["V3 drift chair (top-quintile surprise, D20)"], res["weeks_used"]


def t4(events):
    by = weekly([e for e in events if e["react"] >= T4_FROM])
    gaps, weeks = [], []
    for w in sorted(by):
        es = by[w]
        if len(es) < MIN_WEEK:
            continue
        fl = [e["r5"] for e in es if e["surprise"] > 0 and e["streak"] >= STREAK]
        ot = [e["r5"] for e in es if e["surprise"] > 0 and e["streak"] < STREAK]
        if len(fl) >= MIN_GROUP and len(ot) >= MIN_GROUP:
            gaps.append(statistics.fmean(fl) - statistics.fmean(ot))
            weeks.append(w)
    st = stat(gaps)
    st["holds"] = bool(st.get("testable") and st["weeks"] >= CONFIRM_WEEKS and st["mean"] <= -0.003 and st["t"] <= -2 and all(h < 0 for h in st["halves"]) and st["median"] < 0)
    return st, gaps, weeks


# ------------------------------------------------------------------------------------------------ T3: the sleeve on the Monday clock
def hold_to(s, W, end):
    lo, hi = bisect.bisect_left(s.dates, W), bisect.bisect_right(s.dates, end)
    if lo >= hi or s.dates[hi - 1] < lab._plus(end, -4):
        return None
    return s.rows[hi - 1]["close"] / s.rows[lo]["open"] - 1.0


def t3(events, cal_rows, adj, added):
    reports = {}
    for ts, t, *_ in cal_rows:
        reports.setdefault(t, []).append(ts[:10])
    for t in reports:
        reports[t].sort()
    by_react = sorted(events, key=lambda e: e["react"])
    last = datetime.strptime(S1[1], "%Y-%m-%d").date() - timedelta(days=30)
    W = datetime.strptime(S1[0], "%Y-%m-%d").date()
    out, rows = [], []
    while W <= last:
        w = W.isoformat()
        F = lab._plus(w, -3)
        lo, hi = lab._plus(w, -7), lab._plus(w, -3)
        trade = []
        for t, s in adj.items():
            if t == "SPY" or t not in added or (added[t] and added[t] >= w):
                continue
            if bisect.bisect_left(s.dates, w) < 20:
                continue
            ds = reports.get(t, [])
            j = bisect.bisect_right(ds, F)                   # the first report strictly after the previous Friday
            if j < len(ds) and ds[j] <= lab._plus(F, 7):
                continue
            trade.append(t)
        tset = set(trade)
        cands = {}
        for e in by_react:
            if lo <= e["react"] <= hi and e["t"] in tset and e["eps_surprise"] is not None:
                cur = cands.get(e["t"])
                if cur is None or (-e["surprise"], e["t"]) < (-cur["surprise"], e["t"]):
                    cands[e["t"]] = e
        if len(cands) >= MIN_ACTIVE:
            pick = [e["t"] for e in sorted(cands.values(), key=lambda e: (-e["surprise"], e["t"]))[:TOP]]
            ex = lab._plus(w, 25)

            def r(t):
                x = hold_to(adj[t], w, ex)
                return None if x is None else max(-CLIP, min(CLIP, x))
            pool = {t: r(t) for t in trade}
            pool = {t: x for t, x in pool.items() if x is not None}
            got = [pool[t] for t in pick if t in pool]
            if len(got) == TOP and len(pool) >= 30:
                edge = (statistics.fmean(got) - statistics.fmean(pool.values())) / 4.0
                out.append(edge)
                rows.append({"week": w, "edge": edge, "candidates": len(cands)})
        W += timedelta(days=7)
    st = stat(out)
    st["has_edge"] = bool(st.get("testable") and st["t"] >= 2 and all(h > 0 for h in st["halves"]) and st["median"] > 0)
    return st, rows


# ------------------------------------------------------------------------------------------------ comparisons
def by_year(weeks, vals):
    out = {}
    for w, v in zip(weeks, vals):
        out.setdefault(w[:4], []).append(v)
    return {y: {"weeks": len(v), "mean": statistics.fmean(v)} for y, v in sorted(out.items())}


def t2_weekly(events):
    by = weekly(events)
    weeks, vals = [], []
    for w in sorted(by):
        es = by[w]
        if len(es) < MIN_WEEK:
            continue
        es = sorted(es, key=lambda e: e["surprise"], reverse=True)
        k = max(1, len(es) // 5)
        vals.append(statistics.fmean(e["d20"] for e in es[:k]) - statistics.fmean(e["d20"] for e in es))
        weeks.append(w)
    return weeks, vals


def season_bootstrap(weeks, vals, draws=5000, seed=20261012):
    rng = np.random.default_rng(seed)
    seasons = {}
    for w, v in zip(weeks, vals):
        seasons.setdefault(p21.season_of(w), []).append(v)
    groups = list(seasons.values())
    means = []
    for _ in range(draws):
        pick = rng.integers(0, len(groups), size=len(groups))
        means.append(float(np.mean([x for g in pick for x in groups[g]])))
    return {"seasons": len(groups), "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))], "p_le_0": float(np.mean(np.array(means) <= 0))}


def agreement(fz_events, yf_events):
    a = {(e["t"], e["react"]): e for e in fz_events}
    b = {(e["t"], e["react"]): e for e in yf_events}
    keys = sorted(set(a) & set(b))
    if not keys:
        return {"overlap": 0}
    same = sum(1 for k in keys if (a[k]["surprise"] > 0) == (b[k]["surprise"] > 0))
    wk = {}
    for k in keys:
        wk.setdefault(a[k]["week"], []).append((a[k]["surprise"], b[k]["surprise"]))
    ics = []
    for w, prs in wk.items():
        if len(prs) >= MIN_WEEK:
            ics.append(float(rank_corr([x for x, _ in prs], [y for _, y in prs])))
    return {"overlap": len(keys), "finviz_events": len(a), "yfinance_events": len(b), "same_sign_share": same / len(keys),
            "weekly_rank_corr_mean": statistics.fmean(ics) if ics else None, "weeks_used": len(ics)}


def rank_corr(x, y):
    from scipy.stats import spearmanr
    return spearmanr(x, y)[0]


# ------------------------------------------------------------------------------------------------ main
def pct(x):
    return "--" if x is None else f"{x * 100:+.3f}%"


def show(label, st, extra=""):
    if not st.get("testable"):
        print(f"  {label}: {st['weeks']} weeks, untestable")
        return
    f = (lambda x: f"{x:+.3f}") if "IC" in label or "T1" in label else pct          # an IC is not a percent
    print(f"  {label}: {st['weeks']} weeks, mean {f(st['mean'])}, NW t {st['t']:+.2f}, halves {f(st['halves'][0])} / {f(st['halves'][1])}, median {f(st['median'])} {extra}")


def main(smoke=False):
    if not CAL.exists():
        raise SystemExit("run `python lab/finviz_history.py fetch` first")
    doc = json.loads(CAL.read_text(encoding="utf-8"))
    cal_rows = doc["rows"]
    added = universe()
    names = sorted(added)[:40] if smoke else sorted(added)
    cal_rows = [r for r in cal_rows if r[1] in set(names)]
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(sorted(set(names) | {"SPY"}), True, END, "2015-06-01")).items() if r}
    if "SPY" not in adj or len(adj["SPY"].dates) < 2000:
        raise SystemExit("SPY bars are missing or short: delete the cached download in lab/cache and rerun")
    thin = [t for t in names if t not in adj]
    print(f"\n  {len(cal_rows)} calendar rows for {len({r[1] for r in cal_rows})} of {len(names)} names; {len(thin)} names have no Yahoo bars (delisted or renamed)")
    ev = build_events(cal_rows, adj, added)
    print(f"  S1 events with an EPS surprise, a Yahoo window and index membership: {len(ev)}")
    result = {"registered": REGISTERED, "calendar_rows": len(cal_rows), "names": len(names), "no_bars": len(thin), "s1_events": len(ev)}
    v1, v3, wk_used = t1_t2(ev)
    v1["holds"] = bool(v1.get("testable") and v1["mean"] > 0 and v1["t"] >= 2 and all(h > 0 for h in v1["halves"]))
    v3["passes"] = bool(v3.get("testable") and v3["t"] >= 2 and all(h > 0 for h in v3["halves"]) and v3["median"] > 0)
    show("T1 reaction (IC of surprise with R5)", v1, "-> HOLDS" if v1["holds"] else "-> no")
    show("T2 drift (top quintile, D20 vs the week)", v3, "-> PASSES" if v3["passes"] else "-> no")
    wk2, val2 = t2_weekly(ev)
    result.update({"T1": v1, "T2": v3, "T2_by_year": by_year(wk2, val2), "T2_season_bootstrap": season_bootstrap(wk2, val2) if val2 else None})
    print("  T2 by year:", {y: f"{d['mean']*100:+.2f}% ({d['weeks']}w)" for y, d in result["T2_by_year"].items()})
    print("  T2 season-blocked bootstrap:", result["T2_season_bootstrap"])
    t3s, t3rows = t3(ev, cal_rows, adj, added)
    show("T3 the sleeve on the Monday clock (edge per week of holding)", t3s, "-> HAS AN EDGE" if t3s.get("has_edge") else "-> no")
    result.update({"T3": t3s, "T3_by_year": by_year([r["week"] for r in t3rows], [r["edge"] for r in t3rows])})
    print("  T3 by year:", {y: f"{d['mean']*100:+.2f}% ({d['weeks']}w)" for y, d in result["T3_by_year"].items()})
    t4s, gaps, weeks4 = t4(ev)
    show("T4 beat-then-fall, flagged beats minus other beats, R5", t4s, "-> HOLDS" if t4s["holds"] else "-> no")
    result.update({"T4": t4s, "T4_by_year": by_year(weeks4, gaps)})
    # revenue surprise in place of EPS surprise (reported)
    evr = build_events(cal_rows, adj, added, which="revenue")
    r1, r3, _ = t1_t2(evr)
    result["revenue_T1"], result["revenue_T2"] = r1, r3
    show("(reported) T1 on revenue surprise", r1)
    show("(reported) T2 on revenue surprise", r3)
    # the comparison on S2 with yfinance's definition
    yf_names = [t for t in names if t in adj]
    tables = p21.fetch(sorted(set(yf_names)))
    p21.FIRST, p21.LAST = S2
    yf_ev = [e for e in p21.build_events(yf_names, adj, tables) if not added.get(e["t"]) or added[e["t"]] < e["react"]]
    fz_s2 = [e for e in ev if e["react"] >= S2[0]]
    ag = agreement(fz_s2, yf_ev)
    result["agreement_S2"] = ag
    print("  S2 agreement between the two definitions:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in ag.items()})
    for label, evs in (("finviz", fz_s2), ("yfinance", yf_ev)):
        a, b, _ = t1_t2(evs)
        a["holds"] = bool(a.get("testable") and a["mean"] > 0 and a["t"] >= 2 and all(h > 0 for h in a["halves"]))
        b["passes"] = bool(b.get("testable") and b["t"] >= 2 and all(h > 0 for h in b["halves"]) and b["median"] > 0)
        result[f"S2_{label}"] = {"events": len(evs), "T1": a, "T2": b}
        show(f"(reported) S2 {label} T1 ({len(evs)} events)", a, "-> holds" if a["holds"] else "-> no")
        show(f"(reported) S2 {label} T2", b, "-> passes" if b["passes"] else "-> no")
    result["verdicts"] = {"T1": v1["holds"], "T2": v3["passes"], "T3": bool(t3s.get("has_edge")), "T4": t4s["holds"]}
    print("\n  registered verdicts:", "; ".join(f"{k} {'YES' if v else 'no'}" for k, v in result["verdicts"].items()))
    path = lab.CACHE / "pass31.smoke.json" if smoke else RESULT
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"  wrote {path}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "fetch":
        fetch()
    else:
        main(smoke=arg == "smoke")
