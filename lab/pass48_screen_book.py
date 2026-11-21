#!/usr/bin/env python3
"""Pass 48 -- the screen as the book: hold what the screen flags, and only that.

The snapshot screen the owner reviewed on the A names (Pass 41's channel worth
owning, plus the 4.7-swing pullback rule) held as a portfolio: weekly, for 13
weeks, or until the line fixed at entry breaks.

Registered in lab/README.md (Pass 48) before any run.

    python lab/pass48_screen_book.py          # every arm, both sets
    python lab/pass48_screen_book.py smoke    # plumbing: 300 names
"""
from __future__ import annotations

import json
import math
import pickle
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass32_stop_random as p32  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402
import pass41_owner_channel as p41  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402

R2_MIN = 0.80
SWINGS_MAX = 4.7
SWING_MIN = 0.015
HOLD = 13
FLOOR = math.log(1.10) / 52.0
DRAWS = 200
SEED = 20261128
HALF = p38.HALF
OUT = lab.RESULTS / "pass48_screen_book.json"
ARMS = ["the screen, weekly", "the screen, 13 weeks", "screen in, break out", "no pullback rule"]


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    uf = p43.universe_file()
    uni = {r["ticker"]: r for r in p43.read_universe(uf)}
    with open(p43.BARS, "rb") as fh:
        frames = pickle.load(fh)
    names = sorted(t for t in frames if t in uni)
    if smoke:
        names = names[::max(1, len(names) // 300)][:300]
    import pandas as pd
    idx = sorted(set().union(*[set(frames[t].index) for t in names[:200]]))
    idx = pd.DatetimeIndex([d for d in idx if d.weekday() == 0])

    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
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
    for w in range(26, nW):
        with np.errstate(invalid="ignore"):
            med_dv[w] = np.nanmedian(dv[max(0, w - 51):w + 1], axis=0)
            hi52[w] = np.nanmax(Cw[max(0, w - 51):w + 1], axis=0)
            if w >= 52:
                win = wr[max(0, w - 104):w]
                cnt = (~np.isnan(win)).sum(axis=0)
                swing[w] = np.where(cnt >= 40, np.nanstd(win, axis=0), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        swings_off = (lC - np.log(hi52)) / swing
    tradeable = (Cw >= p43.PRICE_MIN) & (np.nan_to_num(med_dv) >= p43.DV_MIN) & (np.nan_to_num(swing) >= SWING_MIN)
    cap_now = np.array([float(uni[t]["cap_m"]) for t in names])
    ref_px = np.full(n, np.nan)
    for j, t in enumerate(names):
        good = np.flatnonzero(~np.isnan(Cw[:, j]))
        if len(good):
            upto = [w for w in good if fridays[w] <= uni[t]["cap_date"]]
            ref_px[j] = Cw[upto[-1] if upto else good[0], j]
    with np.errstate(invalid="ignore", divide="ignore"):
        size = cap_now[None, :] * Cw / ref_px[None, :]
    tier = np.full((nW, n), -1, dtype=int)
    scale = n / 3000.0 if smoke else 1.0
    for w in range(nW):
        ok = np.flatnonzero(~np.isnan(size[w]))
        order = ok[np.argsort(-size[w, ok])]
        for k, (_, lo, hi, _) in enumerate(p43.TIERS):
            tier[w, order[int(lo * scale):int(min(hi * scale, len(order)))]] = k
    slip_of = np.array([t[3] for t in p43.TIERS] + [p43.TIERS[-1][3]])
    sets = {"top 500": tradeable & (tier >= 0) & (tier <= 1), "every tradeable name": tradeable}

    print("drawing channels ...", flush=True)
    lower, slope, r2, _, _ = p41.channel_table(Cw, Hw, Lw)
    channel = ~np.isnan(lower) & (np.nan_to_num(slope, nan=-1.0) >= FLOOR) & (np.nan_to_num(r2, nan=0.0) >= R2_MIN)
    near_high = np.nan_to_num(swings_off, nan=-99.0) >= -SWINGS_MAX

    w0 = 110
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    sdf = lab.download(sorted(p32.members()) + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)["Close"]["SPY"].dropna()
    spy_w = sdf.groupby([sdf.index.isocalendar().year, sdf.index.isocalendar().week]).last()
    spy_ret = dict(zip([(int(y), int(k)) for y, k in spy_w.index][1:], spy_w.pct_change().to_numpy()[1:]))
    spy = [float(spy_ret.get(tuple(date.fromisoformat(d).isocalendar()[:2]), 0.0)) for d in wk_dates]
    spans = {"all": ("0", "9"), "to 2016": ("0", HALF), "2017 on": (HALF, "9")}
    draws = 20 if smoke else DRAWS
    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "first_week": wk_dates[0], "spy": {}, "sets": {}}
    for sp, (a, b) in spans.items():
        ix = [i for i, d in enumerate(wk_dates) if a <= d < b]
        st = p38.stats([spy[i] for i in ix], [spy[i] for i in ix], [wk_dates[i] for i in ix])
        out["spy"][sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"]}

    for sname, member in sets.items():
        pool_ok = member[:-1] & ~np.isnan(R_hold)
        pool_mean = np.array([float(R_hold[w][pool_ok[w]].mean()) if pool_ok[w].any() else 0.0 for w in range(nW - 1)])
        res_set = {"median_names_a_week": float(np.median(member[w0:].sum(axis=1))), "arms": {}}
        for arm in ARMS:
            rng = np.random.default_rng(SEED)
            screen = member & channel & (near_high if arm != "no pullback rule" else True)
            held = {}                              # j -> (entry week, line at entry, slope)
            rets, counts, on_screen, holds, gains, trades = [], [], [], [], [], 0
            entry_px = {}
            rand = np.zeros((draws, len(weeks)))
            for i, w in enumerate(weeks):
                keep, gone = [], []
                for j, (e, a_, b_) in held.items():
                    if np.isnan(R_hold[w, j]) or np.isnan(lC[w, j]):
                        gone.append(j)
                    elif arm in ("the screen, weekly", "no pullback rule"):
                        (keep if screen[w, j] else gone).append(j)
                    elif arm == "the screen, 13 weeks":
                        (keep if (w - e < HOLD or screen[w, j]) else gone).append(j)
                    else:
                        (keep if lC[w, j] >= a_ + b_ * (w - e) else gone).append(j)
                new = [int(j) for j in np.flatnonzero(screen[w] & ~np.isnan(R_in[w])) if j not in held]
                r = sum(R_hold[w, j] for j in keep)
                for j in gone:
                    e = held.pop(j)[0]
                    ro = 0.0 if np.isnan(R_out[w, j]) else R_out[w, j]
                    r += ro - slip_of[tier[w, j]]
                    px = Ow[w + 1, j] if not np.isnan(Ow[w + 1, j]) else Cw[w, j]
                    holds.append(w - e)
                    gains.append(float(px / entry_px.pop(j) - 1.0))
                for j in new:
                    r += R_in[w, j] - slip_of[tier[w, j]]
                    held[j] = (w, float(lower[w, j]), float(slope[w, j]))
                    entry_px[j] = float(Ow[w + 1, j])
                trades += len(gone) + len(new)
                k = len(keep) + len(gone) + len(new)
                rets.append(float(r) / k if k else 0.0)
                kk = len(held)
                counts.append(kk)
                on_screen.append(int(screen[w].sum()))
                pool = np.flatnonzero(pool_ok[w])
                if kk and len(pool) >= kk:
                    if kk * 3 > len(pool):
                        rand[:, i] = [R_hold[w][rng.choice(pool, kk, replace=False)].mean() for _ in range(draws)]
                    else:
                        pick = rng.random((draws, len(pool))).argpartition(kk - 1, axis=1)[:, :kk]
                        rand[:, i] = R_hold[w][pool][pick].mean(axis=1)
            res = {"avg_names_held": float(np.mean(counts)), "avg_names_on_screen": float(np.mean(on_screen)),
                   "weeks_in_cash": int(sum(1 for c in counts if c == 0)),
                   "trades_a_year": trades / (len(weeks) / 52.0),
                   "turnover_a_year": float(sum(1 for _ in holds) / max(1.0, np.mean(counts)) / (len(weeks) / 52.0)),
                   "median_hold_weeks": float(np.median(holds)) if holds else None,
                   "share_closed_at_a_gain": float(np.mean([g > 0 for g in gains])) if gains else None,
                   "mean_closed_gain": float(np.mean(gains)) if gains else None, "book": {}}
            for sp, (a, b) in spans.items():
                ix = [i for i, d in enumerate(wk_dates) if a <= d < b]
                rr = [rets[i] for i in ix]
                st = p38.stats(rr, [spy[i] for i in ix], [wk_dates[i] for i in ix])
                pl = p38.stats([pool_mean[weeks[i]] for i in ix], [spy[i] for i in ix], [wk_dates[i] for i in ix])
                means = rand[:, ix].mean(axis=1)
                ex = np.array(rr) - np.array([pool_mean[weeks[i]] for i in ix])
                res["book"][sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"],
                                   "pool_cagr": pl["cagr"], "pool_sharpe": pl["sharpe"], "pool_max_drawdown": pl["max_drawdown"],
                                   "percentile_among_random": float((means < np.mean(rr)).mean() * 100.0),
                                   "excess_over_pool_week": float(ex.mean()), "excess_t": p32.tstat(ex),
                                   "excess_over_spy_t": st["excess_t"]}
            by_year = {}
            for d, a_, b_, c_ in zip(wk_dates, rets, [pool_mean[w] for w in weeks], spy):
                y = by_year.setdefault(d[:4], [1.0, 1.0, 1.0])
                y[0] *= 1 + a_
                y[1] *= 1 + b_
                y[2] *= 1 + c_
            res["by_year"] = {y: {"arm": v[0] - 1, "pool": v[1] - 1, "spy": v[2] - 1} for y, v in by_year.items()}
            res_set["arms"][arm] = res
        out["sets"][sname] = res_set

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print("SPY: " + "; ".join(f"{sp} {P(v['cagr']).strip()} Sharpe {v['sharpe']:.2f} DD {P(v['max_drawdown']).strip()}" for sp, v in out["spy"].items()))
    for sname, rs in out["sets"].items():
        print(f"=== {sname} (median {rs['median_names_a_week']:.0f} names a week)")
        print(f"{'arm':22} {'CAGR':>7} {'pool':>7} {'h1':>7} {'pool':>7} {'h2':>7} {'pool':>7} {'Sharpe':>6} {'maxDD':>7} {'pct':>4} {'h1':>4} {'h2':>4} {'t pool':>6} {'t SPY':>6} | {'held':>5} {'tr/yr':>6} {'hold':>5} {'won':>5} {'mean':>7}")
        for nm, r in rs["arms"].items():
            b = r["book"]
            print(f"{nm:22} {P(b['all']['cagr'])} {P(b['all']['pool_cagr'])} {P(b['to 2016']['cagr'])} {P(b['to 2016']['pool_cagr'])} "
                  f"{P(b['2017 on']['cagr'])} {P(b['2017 on']['pool_cagr'])} {b['all']['sharpe']:6.2f} {P(b['all']['max_drawdown'])} "
                  f"{b['all']['percentile_among_random']:4.0f} {b['to 2016']['percentile_among_random']:4.0f} {b['2017 on']['percentile_among_random']:4.0f} "
                  f"{b['all']['excess_t']:6.2f} {b['all']['excess_over_spy_t']:6.2f} | {r['avg_names_held']:5.0f} {r['trades_a_year']:6.0f} "
                  f"{r['median_hold_weeks'] or 0:5.0f} {P(r['share_closed_at_a_gain'], 0)[1:]} {P(r['mean_closed_gain'])}")
    prim = out["sets"]["top 500"]["arms"]["the screen, weekly"]["by_year"]
    print("top 500, the screen weekly, by year: " + "  ".join(f"{y} {100 * v['arm']:+.0f}/{100 * v['spy']:+.0f}" for y, v in prim.items()))
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
