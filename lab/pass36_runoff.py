#!/usr/bin/env python3
"""Pass 36 A -- the runoff: do a screaming stock's sub-industry neighbours drift?

Trigger: an S&P 500 member up or down 8% against SPY on twice its 20-day
volume. Linked names: the rest of its GICS sub-industry, split into those
that moved with it that day (priced) and those that did not (the runoff).
Measured from the next open over 5 and 20 sessions, minus SPY, against the
rest of the sector and against each name's own ordinary excess. Prices only.

Registered in lab/README.md before any run.

    python lab/pass36_runoff.py
    python lab/pass36_runoff.py smoke
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass32_stop_random as p32  # noqa: E402

FULL_CSV = lab.LAB / "universe_sp500_full_2026-09-22.csv"
FIRST_DAY = "2007-01-01"
SPLIT_DAY = "2017-01-01"
MOVE = 0.08
VOL_X = 2.0
VOL_N = 20
PRICED = 1.0 / 3.0
COOL = 20
CLIP = 0.50
HORIZONS = (5, 20)
OUT = lab.RESULTS / "pass36_runoff.json"


def tstat(xs):
    xs = np.asarray(xs, float)
    if len(xs) < 3 or xs.std(ddof=1) == 0:
        return float("nan")
    return float(xs.mean() / (xs.std(ddof=1) / math.sqrt(len(xs))))


def monthly(vals):
    """[(month, value)] -> mean over months of the within-month mean, t over months, halves."""
    by = defaultdict(list)
    for m, v in vals:
        if v == v:
            by[m].append(v)
    ms = sorted(by)
    xs = np.array([np.mean(by[m]) for m in ms])
    if len(xs) == 0:
        return {"n_events": 0, "months": 0, "mean": None, "t": None, "first_half": None, "second_half": None}
    h = len(xs) // 2
    return {"n_events": int(sum(len(by[m]) for m in ms)), "months": len(xs), "mean": float(xs.mean()), "t": tstat(xs),
            "first_half": float(xs[:h].mean()) if h else None, "second_half": float(xs[h:].mean()) if h else None}


def main(smoke=False):
    with open(FULL_CSV, encoding="ascii") as fh:
        meta = {r["ticker"]: r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}
    tickers = sorted(p32.members())
    df = lab.download(tickers + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)
    have = set(df.columns.get_level_values(1))
    names = [t for t in tickers if t in have and t in meta]
    spy_c = df["Close"]["SPY"].to_numpy(float)
    keep = np.isfinite(spy_c)
    dates = [x.strftime("%Y-%m-%d") for x in df.index[keep]]
    O = df["Open"][names].to_numpy(float)[keep]
    C = df["Close"][names].to_numpy(float)[keep]
    V = df["Volume"][names].to_numpy(float)[keep]
    so = df["Open"]["SPY"].to_numpy(float)[keep]
    sc = spy_c[keep]
    T, N = C.shape
    sub = np.array([meta[t]["gics_sub_industry"] for t in names])
    sec = np.array([meta[t]["gics_sector"] for t in names])
    added = np.array([meta[t]["date_added"] or "0000-00-00" for t in names])
    member = np.array([[added[j] < d for j in range(N)] for d in dates])        # T x N

    with np.errstate(invalid="ignore", divide="ignore"):
        ab = np.full((T, N), np.nan)
        ab[1:] = C[1:] / C[:-1] - 1.0 - (sc[1:] / sc[:-1] - 1.0)[:, None]
        volx = np.full((T, N), np.nan)
        cs = np.nancumsum(np.where(np.isfinite(V), V, 0.0), axis=0)
        cnt = np.cumsum(np.isfinite(V), axis=0)
        volx[VOL_N:] = V[VOL_N:] / ((cs[VOL_N - 1:-1] - np.vstack([np.zeros((1, N)), cs[:-VOL_N - 1]])) / VOL_N)
        full = np.zeros((T, N), bool)
        full[VOL_N:] = (cnt[VOL_N - 1:-1] - np.vstack([np.zeros((1, N), int), cnt[:-VOL_N - 1]])) == VOL_N
        fwd = {}
        for h in HORIZONS:
            f = np.full((T, N), np.nan)
            f[:T - h] = C[h:] / O[1:T - h + 1] - 1.0 - (sc[h:] / so[1:T - h + 1] - 1.0)[:, None]
            fwd[h] = np.clip(f, -CLIP, CLIP)
    own = {h: np.array([np.nanmean(np.where(member[:, j], fwd[h][:, j], np.nan)) if member[:, j].any() else np.nan
                        for j in range(N)]) for h in HORIZONS}

    first = next(i for i, d in enumerate(dates) if d >= FIRST_DAY)
    last = T - max(HORIZONS) - 1
    days = range(first, last)
    if smoke:
        days = range(first, first + 400)
    last_trig = np.full(N, -10 ** 6)
    acc = {(d_, h, g, c): [] for d_ in ("up", "down") for h in HORIZONS for g in ("unpriced", "priced", "trigger") for c in ("sector", "own")}
    era = {(d_, h, e): [] for d_ in ("up", "down") for h in HORIZONS for e in ("2007-2016", "2017-2026")}
    counts = defaultdict(int)
    for d in days:
        cand = member[d] & full[d] & np.isfinite(ab[d]) & (np.abs(ab[d]) >= MOVE) & (volx[d] >= VOL_X) & (d - last_trig > COOL)
        if not cand.any():
            continue
        idx = np.where(cand)[0]
        groups = defaultdict(list)
        for j in idx:
            groups[(sub[j], ab[d, j] > 0)].append(j)
        for (g_sub, up), js in groups.items():
            j = max(js, key=lambda k: abs(ab[d, k]))
            for k in js:
                last_trig[k] = d
            dirn = "up" if up else "down"
            sgn = 1.0 if up else -1.0
            linked = np.where((sub == g_sub) & member[d] & np.isfinite(ab[d]) & (np.arange(N) != j))[0]
            ctrl = np.where((sec == sec[j]) & (sub != g_sub) & member[d])[0]
            counts[dirn + " events"] += 1
            if len(linked) == 0 or len(ctrl) < 5:
                counts[dirn + " events without neighbours"] += 1
            priced = sgn * ab[d, linked] >= PRICED * abs(ab[d, j])
            month = dates[d][:7]
            for h in HORIZONS:
                c_sec = np.nanmean(fwd[h][d, ctrl]) if len(ctrl) >= 5 else np.nan
                tv = fwd[h][d, j]
                acc[(dirn, h, "trigger", "sector")].append((month, tv - c_sec))
                acc[(dirn, h, "trigger", "own")].append((month, tv - own[h][j]))
                for gname, mask in (("unpriced", ~priced), ("priced", priced)):
                    sel = linked[mask]
                    vals = fwd[h][d, sel]
                    okv = np.isfinite(vals)
                    if not okv.any():
                        continue
                    v_sec = float(np.mean(vals[okv])) - c_sec
                    v_own = float(np.mean(vals[okv] - own[h][sel][okv]))
                    acc[(dirn, h, gname, "sector")].append((month, v_sec))
                    acc[(dirn, h, gname, "own")].append((month, v_own))
                    if h == HORIZONS[0]:
                        counts[f"{dirn} {gname} links"] += int(okv.sum())
                    if gname == "unpriced":
                        era[(dirn, h, "2007-2016" if dates[d] < SPLIT_DAY else "2017-2026")].append((month, v_sec))

    out = {"days": [dates[first], dates[min(last, T - 1) - 1]], "names": N, "counts": dict(counts), "tests": {}, "eras": {}}
    P = lambda x: "--" if x is None or x != x else f"{100 * x:+.2f}%"  # noqa: E731
    F = lambda x: "--" if x is None or x != x else f"{x:+.2f}"  # noqa: E731
    print(f"Pass 36 A: {dates[first]}..{out['days'][1]}, {N} names; " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print("trigger | horizon | group | vs sector: mean (t) [halves] months/events | vs own: mean (t) | verdict")
    for dirn in ("up", "down"):
        want = 1.0 if dirn == "up" else -1.0
        for h in HORIZONS:
            for g in ("unpriced", "priced", "trigger"):
                a = monthly(acc[(dirn, h, g, "sector")])
                b = monthly(acc[(dirn, h, g, "own")])
                verdict = ""
                if g == "unpriced" and a["mean"] is not None:
                    right = want * a["mean"] > 0
                    same = a["first_half"] is not None and (a["first_half"] > 0) == (a["second_half"] > 0)
                    if right and abs(a["t"]) >= 2.5 and same:
                        verdict = "PASS"
                    elif not right or abs(a["t"]) < 1.64:
                        verdict = "fail"
                    else:
                        verdict = "a lead"
                out["tests"][f"{dirn}/{h}/{g}"] = {"vs_sector": a, "vs_own": b, "verdict": verdict}
                print(f"{dirn} | {h} | {g} | {P(a['mean'])} ({F(a['t'])}) [{P(a['first_half'])} / {P(a['second_half'])}] {a['months']}/{a['n_events']} | "
                      f"{P(b['mean'])} ({F(b['t'])}) | {verdict}")
    print("eras, unpriced vs sector:")
    for (dirn, h, e), vals in sorted(era.items()):
        a = monthly(vals)
        out["eras"][f"{dirn}/{h}/{e}"] = a
        print(f"  {dirn} {h} {e}: {P(a['mean'])} (t {F(a['t'])}, {a['n_events']} events)")
    if not smoke:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
            fh.write("\n")
        print(f"wrote {OUT.relative_to(lab.ROOT)}")


if __name__ == "__main__":
    main(smoke=len(sys.argv) > 1 and sys.argv[1] == "smoke")
