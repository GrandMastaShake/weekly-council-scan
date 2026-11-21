#!/usr/bin/env python3
"""Pass 59 -- trend strength and sector rotation inside the ten-slot book.

Six books, one change each to Pass 57's base book: leading sectors only;
no lagging sectors; sector first; stock trend strength; trend strength in
a strong market and quality otherwise; and all three layers.

Registered in lab/README.md (Pass 59) before any run.

    python lab/pass59_trend_and_sectors.py          # full run
    python lab/pass59_trend_and_sectors.py smoke    # plumbing: 300 names
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass41_owner_channel as p41  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402
import pass48_screen_book as p48  # noqa: E402
import pass52_ten_good_channels as p52  # noqa: E402
import pass53_other_history as p53  # noqa: E402
import pass57_way_back_book as p57  # noqa: E402

p41.MIN_AGE = 8
SLOTS = 10
DRAWS = 100
SEED = 20261159
WINDOW, STEP = 260, 26
SECTOR_SPAN = 13
LEAD = 4
BREADTH = 0.60
OUT = lab.RESULTS / "pass59_trend_and_sectors.json"
PERIODS = {"unseen: 1996-07 to 2006-10": ("1996-07", "2006-11-10"), "2006-11 to 2016-11": ("2006-11-10", "2016-11-11"),
           "2016-11 to 2026-11": ("2016-11-11", "9"), "everything": ("0", "9")}
SAME = {"Finance": "Financials", "Technology": "Information Technology", "Basic Materials": "Materials",
        "Telecommunications": "Communication Services", "": "Unlabelled", "Miscellaneous": "Unlabelled"}
#        name                                        rank       gate
BOOKS = [("base",                                     "quality", None),
         ("1 leading sectors only",                   "quality", "lead"),
         ("2 no lagging sectors",                     "quality", "notlag"),
         ("3 sector first",                           "sector",  None),
         ("4 stock trend strength",                   "trend",   None),
         ("5 trend strength in a strong market only", "regime",  None),
         ("6 all three layers",                       "trend",   "lead")]


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    import pandas as pd
    uni = {r["ticker"]: r for r in p43.read_universe(p43.universe_file())}
    with open(p53.BARS, "rb") as fh:
        frames = pickle.load(fh)
    for t, f in frames.items():
        if len(f) and f.index[0].weekday() != 0:
            f.index = pd.DatetimeIndex([d + pd.Timedelta(days=(7 - d.weekday()) % 7) for d in f.index])
    names = sorted(t for t in frames if t in uni)
    if smoke:
        names = names[::max(1, len(names) // 300)][:300]
    idx = pd.DatetimeIndex([d for d in frames["SPY"].index if d.weekday() == 0])

    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    spy_c = frames["SPY"]["Close"].reindex(idx).ffill().to_numpy(dtype=float)
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names", flush=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        lC = np.log(Cw)
        R_hold = Cw[1:] / Cw[:-1] - 1.0
        R_in = Cw[1:] / Ow[1:] - 1.0
        R_out = Ow[1:] / Cw[:-1] - 1.0
        dv = Cw * Vw
        wr = np.diff(lC, axis=0)
    med_dv = np.full((nW, n), np.nan)
    swing = np.full((nW, n), np.nan)
    hi52 = np.full((nW, n), np.nan)
    ma40 = np.full((nW, n), np.nan)
    back = {k: np.full((nW, n), np.nan) for k in (4, 13, 26, 52)}
    for w in range(26, nW):
        with np.errstate(invalid="ignore", divide="ignore"):
            med_dv[w] = np.nanmedian(dv[max(0, w - 51):w + 1], axis=0)
            hi52[w] = np.nanmax(Cw[max(0, w - 51):w + 1], axis=0)
            for k in back:
                if w >= k:
                    back[k][w] = Cw[w] / Cw[w - k] - 1.0
            if w >= 40:
                ma40[w] = np.nanmean(Cw[w - 39:w + 1], axis=0)
            if w >= 52:
                wn = wr[max(0, w - 104):w]
                cnt = (~np.isnan(wn)).sum(axis=0)
                swing[w] = np.where(cnt >= 40, np.nanstd(wn, axis=0), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        swings_off = (lC - np.log(hi52)) / swing
    tradeable = (np.nan_to_num(med_dv) >= p43.DV_MIN) & (np.nan_to_num(swing) >= p48.SWING_MIN)
    cap_now = np.array([float(uni[t]["cap_m"]) for t in names])
    ref_px = np.full(n, np.nan)
    for j, t in enumerate(names):
        good = np.flatnonzero(~np.isnan(Cw[:, j]))
        if len(good):
            upto = [w for w in good if fridays[w] <= uni[t]["cap_date"]]
            ref_px[j] = Cw[upto[-1] if upto else good[0], j]
    with np.errstate(invalid="ignore", divide="ignore"):
        size = cap_now[None, :] * Cw / ref_px[None, :]
    scale = n / 3000.0 if smoke else 1.0
    member_size = np.zeros((nW, n), dtype=bool)
    for w in range(nW):
        ok = np.flatnonzero(~np.isnan(size[w]))
        member_size[w, ok[np.argsort(-size[w, ok])][:int(500 * scale)]] = True
    member = tradeable & member_size
    slip = float(p43.TIERS[1][3])

    # sector strength: the 13-week return of each sector's top-500 members, equal weight
    sector = [SAME.get(uni[t]["sector"], uni[t]["sector"]) for t in names]
    sectors = sorted(set(sector) - {"Unlabelled"})
    sec_of = np.array([sectors.index(s_) if s_ in sectors else -1 for s_ in sector])
    sec_strength = np.full((nW, n), np.nan)
    allow = {"lead": np.zeros((nW, n), dtype=bool), "notlag": np.zeros((nW, n), dtype=bool)}
    lead_log = []
    for w in range(SECTOR_SPAN + 26, nW):
        vals = np.full(len(sectors), np.nan)
        for k in range(len(sectors)):
            m = member_size[w] & (sec_of == k) & ~np.isnan(back[13][w])
            if m.sum() >= max(3, int(5 * scale)):
                vals[k] = back[13][w][m].mean()
        order = [k for k in np.argsort(-np.nan_to_num(vals, nan=-9.0)) if vals[k] == vals[k]]
        lead, lag = set(order[:LEAD]), set(order[-LEAD:]) if len(order) > LEAD else set()
        lead_log.append(tuple(sorted(sectors[k] for k in lead)))
        for k in range(len(sectors)):
            cols = sec_of == k
            sec_strength[w, cols] = vals[k]
            allow["lead"][w, cols] = k in lead
            allow["notlag"][w, cols] = (k not in lag) and vals[k] == vals[k]
    spy_ma40 = np.array([spy_c[max(0, w - 39):w + 1].mean() for w in range(nW)])
    cold = np.array([w >= 39 and spy_c[w] < spy_ma40[w] for w in range(nW)])
    with np.errstate(invalid="ignore"):
        breadth = np.array([float((Cw[w][member_size[w]] > ma40[w][member_size[w]]).mean()) if member_size[w].any() else 0.0 for w in range(nW)])
    strong = np.array([w >= 53 and not cold[w] and spy_ma40[w] > spy_ma40[w - 13] and breadth[w] >= BREADTH for w in range(nW)])

    print("drawing channels ...", flush=True)
    T = p52.quality_table(Cw, Hw, Lw)
    slope = T["slope"]
    channel = ~np.isnan(T["lower"]) & (np.nan_to_num(slope, nan=-1.0) >= p48.FLOOR) & (np.nan_to_num(T["r2"], nan=0.0) >= p48.R2_MIN)
    screen = member & channel & (np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX)
    w0 = 110
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    cands = {"quality": {}, "sector": {}, "trend": {}, "regime": {}}
    for w in range(w0, nW):
        js = np.flatnonzero(screen[w])
        if len(js) > 1:
            with np.errstate(invalid="ignore", divide="ignore"):
                tight = T["height"][w, js] / (slope[w, js] * T["age"][w, js])
            q = (p52.ranks(T["r2"][w, js]) + p52.ranks(-tight) + p52.ranks(T["age"][w, js]) + p52.ranks(T["touches"][w, js])) / 4.0
            tr = sum(p52.ranks(np.nan_to_num(back[k][w, js], nan=-9.0)) for k in back) / 4.0
            by_q = js[np.argsort(-q, kind="stable")]
            by_t = js[np.argsort(-tr, kind="stable")]
            by_s = js[np.argsort(-(np.nan_to_num(sec_strength[w, js], nan=-9.0) * 1000.0 + q), kind="stable")]
        else:
            by_q = by_t = by_s = js
        cands["quality"][w], cands["trend"][w], cands["sector"][w] = by_q, by_t, by_s
        cands["regime"][w] = by_t if strong[w] else by_q
    spy = [float(spy_c[w + 1] / spy_c[w] - 1.0) for w in weeks]
    pool_ok = member[:-1] & ~np.isnan(R_hold)
    pool = [float(R_hold[w][pool_ok[w]].mean()) if pool_ok[w].any() else 0.0 for w in weeks]
    N = max(3, int(SLOTS * scale * 3)) if smoke else SLOTS

    def sim(rank, gate, pick, rng=None, detail=False):
        held, rets, holds, buys, inv = {}, [], [], 0, []
        for w in weeks:
            gone = []
            for j, st in held.items():
                c = Cw[w, j]
                if c != c or np.isnan(R_hold[w, j]):
                    gone.append(j)
                    continue
                st[1] = max(st[1], c)
                if c / st[1] - 1.0 <= -p57.OFF_HIGH:
                    gone.append(j)
            r = 0.0
            for j in gone:
                holds.append(w - held.pop(j)[0])
                r += (0.0 if np.isnan(R_out[w, j]) else R_out[w, j]) / N
            new = []
            free = N - len(held)
            if free > 0 and not cold[w]:
                cs = [int(j) for j in cands[rank][w] if j not in held and j not in gone and not np.isnan(R_in[w, j])
                      and (gate is None or allow[gate][w, j])]
                new = cs[:free] if pick == "top" else [cs[k] for k in rng.permutation(len(cs))[:free]]
            for j in held:
                r += R_hold[w, j] / N
            for j in new:
                held[j] = [w, float(max(hi52[w, j], Cw[w, j]))]
                r += R_in[w, j] / N
            buys += len(new)
            r -= (len(new) + len(gone)) * slip / N
            rets.append(float(r))
            inv.append(len(held) / N)
        if not detail:
            return rets
        return rets, {"buys_a_year": buys / (len(weeks) / 52.0), "median_hold_weeks": float(np.median(holds)) if holds else None,
                      "avg_in_stocks": float(np.mean(inv))}

    def cg(x):
        x = np.asarray(x, dtype=float)
        return float(np.prod(1.0 + x) ** (52.0 / len(x)) - 1.0)

    per_ix = {k: [i for i, d in enumerate(wk_dates) if a <= d < b] for k, (a, b) in PERIODS.items()}
    late = [s0 for s0 in range(0, len(weeks) - WINDOW + 1, STEP) if wk_dates[s0] >= "2016"]
    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "first_week": wk_dates[0], "slots": N,
           "share_of_weeks": {"cold": float(np.mean([cold[w] for w in weeks])), "strong": float(np.mean([strong[w] for w in weeks]))},
           "leading_four_changes_a_year": float(sum(1 for a, b in zip(lead_log, lead_log[1:]) if a != b) / (len(lead_log) / 52.0)),
           "benchmarks": {nm: {k: p53.stat([s_[i] for i in ix], [wk_dates[i] for i in ix]) for k, ix in per_ix.items()} for nm, s_ in (("SPY", spy), ("pool", pool))},
           "books": {}}
    draws = 8 if smoke else DRAWS
    rand_cache = {}
    for name, rank, gate in BOOKS:
        rets, info = sim(rank, gate, "top", detail=True)
        for g in {None, gate}:
            if g not in rand_cache:
                rng = np.random.default_rng(SEED)
                rand_cache[g] = np.array([sim("quality", g, "random", rng=rng) for _ in range(draws)])
        info["periods"] = {}
        for k, ix in per_ix.items():
            st = p53.stat([rets[i] for i in ix], [wk_dates[i] for i in ix])
            mine = np.mean([rets[i] for i in ix])
            st["percentile_among_base_random_books"] = float((rand_cache[None][:, ix].mean(axis=1) < mine).mean() * 100.0)
            st["own_random_median_cagr"] = float(np.median([cg(row[ix]) for row in rand_cache[gate]]))
            info["periods"][k] = st
        info["five_year_windows_from_2016_beating_spy"] = [int(sum(cg(rets[s0:s0 + WINDOW]) > cg(spy[s0:s0 + WINDOW]) for s0 in late)), len(late)]
        out["books"][name] = info
        print("done:", name, flush=True)

    def P(x, d_=1):
        return "    --" if x is None else f"{100 * x:6.{d_}f}%"
    print(f"cold {P(out['share_of_weeks']['cold'], 0).strip()} of weeks, strong {P(out['share_of_weeks']['strong'], 0).strip()}; the leading four change {out['leading_four_changes_a_year']:.0f} times a year")
    for k in PERIODS:
        s_, p_ = out["benchmarks"]["SPY"][k], out["benchmarks"]["pool"][k]
        print(f"== {k}: SPY {P(s_['cagr'])} Sharpe {s_['sharpe']:.2f} DD {P(s_['max_drawdown'])} | pool {P(p_['cagr'])} Sharpe {p_['sharpe']:.2f} DD {P(p_['max_drawdown'])}")
        for nm, r in out["books"].items():
            b = r["periods"][k]
            print(f"     {nm:42} {P(b['cagr'])} Sharpe {b['sharpe']:.2f} DD {P(b['max_drawdown'])} pct of base random {b['percentile_among_base_random_books']:4.0f}  own random {P(b['own_random_median_cagr'])}")
    for nm, r in out["books"].items():
        v = r["five_year_windows_from_2016_beating_spy"]
        print(f"{nm:42} buys/yr {r['buys_a_year']:.1f}, median hold {r['median_hold_weeks']}w, in stocks {P(r['avg_in_stocks'], 0).strip()}, five-year windows from 2016 over SPY {v[0]}/{v[1]}")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main(sys.argv)
