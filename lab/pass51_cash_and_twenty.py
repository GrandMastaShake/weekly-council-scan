#!/usr/bin/env python3
"""Pass 51 -- the channel-hold book with cash, and the owner's 20% rule.

Pass 48's screen for entries; every held name weighs one over the number
held or one hundredth, whichever is smaller, and the rest is cash. Four
exits: the line fixed at entry, 20% off the high, either, and the line or
4.7 of the stock's own weekly swings off the high.

Registered in lab/README.md (Pass 51) before any run.

    python lab/pass51_cash_and_twenty.py          # full run
    python lab/pass51_cash_and_twenty.py smoke    # plumbing: 300 names
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
import pass48_screen_book as p48  # noqa: E402

FULL = 100
OFF_HIGH = 0.20
DRAWS = 200
SEED = 20261151
HALF = p38.HALF
OUT = lab.RESULTS / "pass51_cash_and_twenty.json"
ARMS = ["line", "20% off the high", "line or 20%", "line or 4.7 swings"]
SPANS = {"all": ("0", "9"), "to 2016": ("0", HALF), "2017 on": (HALF, "9"), "2010 on": ("2010", "9")}


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    uni = {r["ticker"]: r for r in p43.read_universe(p43.universe_file())}
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
    tradeable = (Cw >= p43.PRICE_MIN) & (np.nan_to_num(med_dv) >= p43.DV_MIN) & (np.nan_to_num(swing) >= p48.SWING_MIN)
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
    channel = ~np.isnan(lower) & (np.nan_to_num(slope, nan=-1.0) >= p48.FLOOR) & (np.nan_to_num(r2, nan=0.0) >= p48.R2_MIN)
    near_high = np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX

    w0 = 110
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    sdf = lab.download(sorted(p32.members()) + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)["Close"]["SPY"].dropna()
    spy_w = sdf.groupby([sdf.index.isocalendar().year, sdf.index.isocalendar().week]).last()
    spy_ret = dict(zip([(int(y), int(k)) for y, k in spy_w.index][1:], spy_w.pct_change().to_numpy()[1:]))
    spy = [float(spy_ret.get(tuple(date.fromisoformat(d).isocalendar()[:2]), 0.0)) for d in wk_dates]
    draws = 20 if smoke else DRAWS
    full = max(3, int(FULL * scale))
    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "first_week": wk_dates[0], "full_book": full, "spy": {}, "sets": {}}
    span_ix = {sp: [i for i, d in enumerate(wk_dates) if a <= d < b] for sp, (a, b) in SPANS.items()}
    for sp, ix in span_ix.items():
        if len(ix) < 3:
            continue
        st = p38.stats([spy[i] for i in ix], [spy[i] for i in ix], [wk_dates[i] for i in ix])
        out["spy"][sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"]}

    for sname, member in sets.items():
        pool_ok = member[:-1] & ~np.isnan(R_hold)
        screen = member & channel & near_high
        res_set = {"arms": {}}
        for arm in ARMS:
            rng = np.random.default_rng(SEED)
            held = {}                  # j -> [entry week, line, slope, high close]
            entry_px = {}
            rets, counts, inv, holds, gains, falls = [], [], [], [], [], []
            rand = np.zeros((draws, len(weeks)))
            for i, w in enumerate(weeks):
                keep, gone = [], []
                for j, st in held.items():
                    e, a_, b_, hi = st
                    if np.isnan(R_hold[w, j]) or np.isnan(lC[w, j]):
                        gone.append(j)
                        continue
                    st[3] = hi = max(hi, Cw[w, j])
                    under_line = lC[w, j] < a_ + b_ * (w - e)
                    off = Cw[w, j] / hi - 1.0
                    sw = swing[w, j]
                    if arm == "line":
                        sell = under_line
                    elif arm == "20% off the high":
                        sell = off <= -OFF_HIGH
                    elif arm == "line or 20%":
                        sell = under_line or off <= -OFF_HIGH
                    else:
                        sell = under_line or (sw == sw and sw > 0 and math.log(1.0 + off) / sw <= -p48.SWINGS_MAX)
                    (gone if sell else keep).append(j)
                new = [int(j) for j in np.flatnonzero(screen[w] & ~np.isnan(R_in[w])) if j not in held]
                r = sum(R_hold[w, j] for j in keep)
                for j in gone:
                    e, _, _, hi = held.pop(j)
                    ro = 0.0 if np.isnan(R_out[w, j]) else R_out[w, j]
                    r += ro - slip_of[tier[w, j]]
                    px = Ow[w + 1, j] if not np.isnan(Ow[w + 1, j]) else Cw[w, j]
                    holds.append(w - e)
                    gains.append(float(px / entry_px.pop(j) - 1.0))
                    falls.append(float(px / hi - 1.0))
                for j in new:
                    r += R_in[w, j] - slip_of[tier[w, j]]
                    held[j] = [w, float(lower[w, j]), float(slope[w, j]), float(max(hi52[w, j], Cw[w, j]))]
                    entry_px[j] = float(Ow[w + 1, j])
                k = len(keep) + len(gone) + len(new)
                rets.append(float(r) / max(k, full) if k else 0.0)
                kk = len(held)
                counts.append(kk)
                frac = kk / max(kk, full)
                inv.append(frac)
                pool = np.flatnonzero(pool_ok[w])
                if kk and len(pool) >= kk:
                    if kk * 3 > len(pool):
                        rand[:, i] = [R_hold[w][rng.choice(pool, kk, replace=False)].mean() * frac for _ in range(draws)]
                    else:
                        pick = rng.random((draws, len(pool))).argpartition(kk - 1, axis=1)[:, :kk]
                        rand[:, i] = R_hold[w][pool][pick].mean(axis=1) * frac
            res = {"avg_names_held": float(np.mean(counts)), "avg_invested": float(np.mean(inv)),
                   "sales_a_year": len(holds) / (len(weeks) / 52.0),
                   "median_hold_weeks": float(np.median(holds)) if holds else None,
                   "share_closed_at_a_gain": float(np.mean([g > 0 for g in gains])) if gains else None,
                   "mean_closed_gain": float(np.mean(gains)) if gains else None,
                   "sale_under_high_median": float(np.median(falls)) if falls else None,
                   "sale_under_high_worst_tenth": float(np.percentile(falls, 10)) if falls else None,
                   "sale_under_high_worst": float(min(falls)) if falls else None, "book": {}}
            for sp, ix in span_ix.items():
                if len(ix) < 3:
                    continue
                rr = [rets[i] for i in ix]
                st = p38.stats(rr, [spy[i] for i in ix], [wk_dates[i] for i in ix])
                means = rand[:, ix].mean(axis=1)
                rc = np.cumprod(1.0 + rand[:, ix], axis=1)[:, -1] ** (52.0 / len(ix)) - 1.0
                res["book"][sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "vol": st["vol"], "max_drawdown": st["max_drawdown"],
                                   "percentile_among_random": float((means < np.mean(rr)).mean() * 100.0),
                                   "random_median_cagr": float(np.median(rc)),
                                   "invested": float(np.mean([inv[i] for i in ix])),
                                   "excess_over_spy_t": st["excess_t"]}
            by_year = {}
            for d, a_, c_ in zip(wk_dates, rets, spy):
                y = by_year.setdefault(d[:4], [1.0, 1.0])
                y[0] *= 1 + a_
                y[1] *= 1 + c_
            res["by_year"] = {y: {"arm": v[0] - 1, "spy": v[1] - 1} for y, v in by_year.items()}
            res_set["arms"][arm] = res
        out["sets"][sname] = res_set

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print("SPY: " + "; ".join(f"{sp} {P(v['cagr']).strip()} Sharpe {v['sharpe']:.2f} DD {P(v['max_drawdown']).strip()}" for sp, v in out["spy"].items()))
    for sname, rs in out["sets"].items():
        print(f"=== {sname}")
        for nm, r in rs["arms"].items():
            print(f"-- {nm}: held {r['avg_names_held']:.0f}, invested {P(r['avg_invested'], 0).strip()}, sales/yr {r['sales_a_year']:.0f}, "
                  f"median hold {r['median_hold_weeks'] or 0:.0f}w, won {P(r['share_closed_at_a_gain'], 0).strip()}, mean {P(r['mean_closed_gain']).strip()}, "
                  f"sale under high: median {P(r['sale_under_high_median']).strip()} worst tenth {P(r['sale_under_high_worst_tenth']).strip()} worst {P(r['sale_under_high_worst']).strip()}")
            for sp, b in r["book"].items():
                print(f"     {sp:8} CAGR {P(b['cagr'])} random {P(b['random_median_cagr'])} Sharpe {b['sharpe'] if b['sharpe'] is None else round(b['sharpe'], 2)} "
                      f"DD {P(b['max_drawdown'])} pct {b['percentile_among_random']:4.0f} invested {P(b['invested'], 0).strip()}")
            print("     by year arm/spy: " + "  ".join(f"{y} {100 * v['arm']:+.0f}/{100 * v['spy']:+.0f}" for y, v in r["by_year"].items()))
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main(sys.argv)
