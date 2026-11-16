#!/usr/bin/env python3
"""Pass 32 -- the -5% stop on random fives, twenty years of weeks.

The tracker's own stop rule (portfolio/tracker.py stop_fill: the daily Low
against a level under the entry, filled at the level or at a gap Open, cash to
Friday) applied to random equal-weight fives from the S&P 500, every week from
2007-01-01, against the plain hold and against the plain hold at the exposure
that gives the same weekly SD (rule 7). No LLM, no engine: prices only.

Registered in lab/README.md before any run.

    python lab/pass32_stop_random.py
    python lab/pass32_stop_random.py smoke
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

ADDED_CSV = lab.LAB / "universe_sp500_added_2026-09-22.csv"
DATA_START = "2006-06-01"
DATA_END = "2026-11-14"
FIRST_MONDAY = "2007-01-01"
LAST_MONDAY = "2026-11-09"
CRISIS = ("2008-09-01", "2009-03-31")
DRAWS = 200
BOOK = 5
SEED = 20261116
VOL_WINDOW = 60
SLIP = 0.0010
ARMS = [("plain", None, None), ("-3%", -3.0, None), ("-5%", -5.0, None), ("-8%", -8.0, None),
        ("-10%", -10.0, None), ("1.5 SD", None, 1.5), ("2.0 SD", None, 2.0)]
OUT = lab.RESULTS / "pass32_stop_random.json"


def members():
    with open(ADDED_CSV, encoding="ascii") as fh:
        rows = [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))]
    return {r["ticker"]: r["date_added"] for r in rows}


def tstat(xs):
    xs = np.asarray(xs, dtype=float)
    if len(xs) < 3 or xs.std(ddof=1) == 0:
        return float("nan")
    return float(xs.mean() / (xs.std(ddof=1) / math.sqrt(len(xs))))


def tail5(xs):
    xs = np.sort(np.asarray(xs, dtype=float).ravel())
    k = max(1, int(round(0.05 * len(xs))))
    return float(xs[:k].mean())


def main(smoke=False):
    added = members()
    tickers = sorted(added)
    df = lab.download(tickers + ["SPY"], True, DATA_END, start=DATA_START)
    dates = [x.strftime("%Y-%m-%d") for x in df.index]
    have = set(df.columns.get_level_values(1))
    names = [t for t in tickers if t in have]
    missing = [t for t in tickers if t not in have]
    O = df["Open"][names].to_numpy(dtype=float)
    L = df["Low"][names].to_numpy(dtype=float)
    C = df["Close"][names].to_numpy(dtype=float)
    spy_o = df["Open"]["SPY"].to_numpy(dtype=float)
    spy_c = df["Close"]["SPY"].to_numpy(dtype=float)
    sess = [i for i, v in enumerate(spy_c) if v == v]
    sess_dates = [dates[i] for i in sess]
    added_arr = np.array([added[t] or "0000-00-00" for t in names])

    mondays = []
    d = date.fromisoformat(FIRST_MONDAY)
    while d.isoformat() <= LAST_MONDAY:
        mondays.append(d)
        d += timedelta(days=7)
    if smoke:
        mondays = mondays[:6] + mondays[-6:]
    draws = 20 if smoke else DRAWS

    rng = np.random.default_rng(SEED)
    A = len(ARMS)
    weeks, spy_ret = [], []
    wk_mean = []                 # per week: mean over draws, per arm (and slipped)
    wk_mean_slip = []
    books = []                   # per week: draws x arms
    n_elig = []
    nw = {a[0]: {"n": 0, "fired": 0, "gap": 0, "above": 0, "ret_sum": 0.0} for a in ARMS}

    import bisect
    for mon in mondays:
        lo = bisect.bisect_left(sess_dates, mon.isoformat())
        hi = bisect.bisect_right(sess_dates, (mon + timedelta(days=4)).isoformat())
        if hi - lo < 2:
            continue
        idx = sess[lo:hi]
        first = idx[0]
        if lo < VOL_WINDOW + 1:
            continue
        pre = sess[lo - VOL_WINDOW - 1:lo]
        wk = np.array(idx)
        ok = (added_arr < mon.isoformat())
        ok &= np.isfinite(O[wk]).all(axis=0) & np.isfinite(L[wk]).all(axis=0) & np.isfinite(C[wk]).all(axis=0)
        ok &= (O[wk] > 0).all(axis=0)
        ok &= np.isfinite(C[np.array(pre)]).all(axis=0)
        cols = np.where(ok)[0]
        if len(cols) < 50:
            continue
        o, l, c = O[wk][:, cols], L[wk][:, cols], C[wk][:, cols]
        entry = o[0]
        pc = C[np.array(pre)][:, cols]
        dret = pc[1:] / pc[:-1] - 1.0
        sd_w = dret.std(axis=0, ddof=1) * math.sqrt(5)
        plain = c[-1] / entry - 1.0

        rets = np.zeros((A, len(cols)))
        rets_slip = np.zeros((A, len(cols)))
        for ai, (name, pct, k) in enumerate(ARMS):
            if pct is None and k is None:
                rets[ai] = plain
                rets_slip[ai] = plain
                nw[name]["n"] += len(cols)
                nw[name]["ret_sum"] += float(plain.sum())
                continue
            frac = (pct / 100.0) if pct is not None else (-k * sd_w)
            level = entry * (1.0 + frac)
            alive = np.ones(len(cols), dtype=bool)
            r = plain.copy()
            rs = plain.copy()
            gap = np.zeros(len(cols), dtype=bool)
            fill = np.full(len(cols), np.nan)
            for di in range(len(wk)):
                hit = alive & (l[di] <= level)
                if not hit.any():
                    continue
                g = hit & (o[di] <= level)
                f = np.where(g, o[di], level)
                fill[hit] = f[hit]
                r[hit] = f[hit] / entry[hit] - 1.0
                rs[hit] = r[hit] - np.where(g[hit], 0.0, SLIP)
                gap |= g
                alive &= ~hit
            fired = ~alive
            rets[ai] = r
            rets_slip[ai] = rs
            s = nw[name]
            s["n"] += len(cols)
            s["fired"] += int(fired.sum())
            s["gap"] += int(gap.sum())
            s["above"] += int((fired & (c[-1] > fill)).sum())
            s["ret_sum"] += float(r.sum())

        pick = np.stack([rng.choice(len(cols), BOOK, replace=False) for _ in range(draws)])
        b = rets[:, pick].mean(axis=2).T            # draws x arms
        bs = rets_slip[:, pick].mean(axis=2).T
        books.append(b)
        wk_mean.append(b.mean(axis=0))
        wk_mean_slip.append(bs.mean(axis=0))
        weeks.append(mon.isoformat())
        spy_ret.append(spy_c[idx[-1]] / spy_o[first] - 1.0)
        n_elig.append(len(cols))

    wk_mean = np.array(wk_mean)
    wk_mean_slip = np.array(wk_mean_slip)
    books = np.array(books)                         # weeks x draws x arms
    spy_ret = np.array(spy_ret)
    W = len(weeks)
    half = W // 2
    up = spy_ret > 0
    crisis = np.array([(CRISIS[0] <= w <= CRISIS[1]) for w in weeks])

    plain_all = books[:, :, 0]
    sd_plain = float(plain_all.std(ddof=1))
    tail_plain = tail5(plain_all)
    out = {"weeks": W, "first": weeks[0], "last": weeks[-1], "draws": draws, "names": len(names),
           "missing": missing, "eligible_min": int(min(n_elig)), "eligible_max": int(max(n_elig)),
           "eligible_mean": float(np.mean(n_elig)), "spy_mean_week": float(spy_ret.mean()), "arms": {}}

    def pct(x):
        return f"{100 * x:+.3f}%"

    print(f"Pass 32: {W} weeks {weeks[0]}..{weeks[-1]}, {draws} random fives a week, "
          f"{len(names)} names ({int(np.mean(n_elig))} eligible on average)")
    hdr = ("arm", "mean/wk", "vs plain", "t", "SD", "worst 5%", "worst", "fires", "gap", "above", "D_ret", "t", "D_tail", "verdict")
    print(" | ".join(hdr))
    for ai, (name, _, _) in enumerate(ARMS):
        allb = books[:, :, ai]
        sd = float(allb.std(ddof=1))
        t5 = tail5(allb)
        diff = wk_mean[:, ai] - wk_mean[:, 0]
        c = sd / sd_plain
        dser = wk_mean[:, ai] - c * wk_mean[:, 0]
        d_ret = float(dser.mean())
        d_tail = t5 - c * tail_plain
        dser_slip = wk_mean_slip[:, ai] - c * wk_mean_slip[:, 0]
        s = nw[name]
        rec = {
            "mean_week": float(wk_mean[:, ai].mean()),
            "vs_plain": float(diff.mean()), "vs_plain_t": tstat(diff),
            "sd": sd, "tail5": t5, "worst": float(allb.min()),
            "c": c, "D_ret": d_ret, "D_ret_t": tstat(dser),
            "D_ret_first_half": float(dser[:half].mean()), "D_ret_second_half": float(dser[half:].mean()),
            "D_tail": d_tail, "tail_cash_matched": c * tail_plain,
            "D_ret_slip": float(dser_slip.mean()), "D_ret_slip_t": tstat(dser_slip),
            "vs_plain_slip": float((wk_mean_slip[:, ai] - wk_mean_slip[:, 0]).mean()),
            "vs_plain_first_half": float(diff[:half].mean()), "vs_plain_second_half": float(diff[half:].mean()),
            "vs_plain_spy_up": float(diff[up].mean()), "vs_plain_spy_down": float(diff[~up].mean()),
            "vs_plain_crisis": float(diff[crisis].mean()) if crisis.any() else None,
            "crisis_weeks": int(crisis.sum()),
            "name_weeks": s["n"], "fire_rate": s["fired"] / s["n"] if s["n"] else 0.0,
            "gap_share": s["gap"] / s["fired"] if s["fired"] else None,
            "above_fill_share": s["above"] / s["fired"] if s["fired"] else None,
            "name_week_mean": s["ret_sum"] / s["n"] if s["n"] else None,
        }
        if ai == 0:
            verdict = "--"
        else:
            same = (rec["D_ret_first_half"] >= 0) == (rec["D_ret_second_half"] >= 0)
            tail_ok = d_tail > 0.1 * abs(c * tail_plain)
            if (d_ret >= 0 and same) or (tail_ok and rec["D_ret_t"] > -2):
                verdict = "earns its place"
            elif d_ret < 0 and rec["D_ret_t"] <= -2 and same and not tail_ok:
                verdict = "fails"
            else:
                verdict = "a cash dial"
        rec["verdict"] = verdict
        out["arms"][name] = rec
        fr = f"{100 * rec['fire_rate']:.1f}%" if ai else "--"
        gp = f"{100 * rec['gap_share']:.0f}%" if rec["gap_share"] is not None else "--"
        ab = f"{100 * rec['above_fill_share']:.0f}%" if rec["above_fill_share"] is not None else "--"
        print(" | ".join([name, pct(rec["mean_week"]), pct(rec["vs_plain"]), f"{rec['vs_plain_t']:.2f}", pct(sd), pct(t5),
                          pct(rec["worst"]), fr, gp, ab, pct(d_ret), f"{rec['D_ret_t']:.2f}", pct(d_tail), verdict]))
    print("\nsplits, stop minus plain per week:")
    for name, r in out["arms"].items():
        if name == "plain":
            continue
        print(f"  {name}: first half {pct(r['vs_plain_first_half'])}, second {pct(r['vs_plain_second_half'])}, "
              f"SPY up {pct(r['vs_plain_spy_up'])}, SPY down {pct(r['vs_plain_spy_down'])}, "
              f"2008-09..2009-03 ({r['crisis_weeks']} wk) {pct(r['vs_plain_crisis']) if r['vs_plain_crisis'] is not None else '--'}; "
              f"D_ret halves {pct(r['D_ret_first_half'])} / {pct(r['D_ret_second_half'])}; with slip: vs plain {pct(r['vs_plain_slip'])}, D_ret {pct(r['D_ret_slip'])} (t {r['D_ret_slip_t']:.2f})")
    if not smoke:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
            fh.write("\n")
        print(f"\nwrote {OUT.relative_to(lab.ROOT)}")


if __name__ == "__main__":
    main(smoke=len(sys.argv) > 1 and sys.argv[1] == "smoke")
