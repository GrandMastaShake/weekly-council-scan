#!/usr/bin/env python3
"""Pass 39 -- the straight line: trade inside the channel, buy the bottom, sell the top.

The owner's revision of Pass 38. A name must be a rising straight line on four
time frames (21, 63, 126, 252 sessions); it is bought a width below its
126-session line and sold a width above it, or on a break. The sector fund and
SPY set how much room the break line gives. Measured, as Pass 38 was, against
random books at the same exposure.

Registered in lab/README.md (Pass 39) before any run.

    python lab/pass39_straight_line.py          # every arm
    python lab/pass39_straight_line.py smoke    # plumbing: 2022 on, 80 names, 20 draws
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass32_stop_random as p32  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402

from scan_pipeline.config.tickers import STOCK_UNIVERSE  # noqa: E402

FRAMES = (21, 63, 126, 252)
CHANNEL = 126
BUY_Z, SELL_Z = -1.0, 1.0
SLOTS, PER_SECTOR, WEIGHT, SLIP = p38.SLOTS, p38.PER_SECTOR, p38.WEIGHT, p38.SLIP
DRAWS = 200
SEED = 20261121
HALF = p38.HALF
OUT = lab.RESULTS / "pass39_straight_line.json"

#        name             width       top    lined  council
ARMS = [("line",          "fixed",    True,  True,  False),
        ("line+width",    "backdrop", True,  True,  False),
        ("reversed",      "reversed", True,  True,  False),
        ("no top",        "backdrop", False, True,  False),
        ("any channel",   "backdrop", True,  False, False),
        ("council names", "backdrop", True,  True,  True)]


def fits(C, ends):
    """Per decision day and column: slope and R-squared on each frame, and the
    channel z. C is sessions x columns of closes; ends are session indexes."""
    n = C.shape[1]
    slope = {T: np.full((len(ends), n), np.nan) for T in FRAMES}
    r2 = {T: np.full((len(ends), n), np.nan) for T in FRAMES}
    z = np.full((len(ends), n), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        L = np.log(C)
        for T in FRAMES:
            x = np.arange(T) - (T - 1) / 2.0
            sxx = float((x * x).sum())
            for k, i in enumerate(ends):
                if i + 1 < T:
                    continue
                y = L[i - T + 1:i + 1]
                yb = y.mean(axis=0)
                d = y - yb
                b = (x[:, None] * d).sum(axis=0) / sxx
                resid = d - b * x[:, None]
                sse, sst = (resid ** 2).sum(axis=0), (d ** 2).sum(axis=0)
                slope[T][k] = b
                r2[T][k] = np.where(sst > 0, 1.0 - sse / sst, np.nan)
                if T == CHANNEL:
                    width = np.sqrt(sse / (T - 2))
                    z[k] = np.where(width > 0, resid[-1] / width, np.nan)
    return slope, r2, z


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    added = p32.members()
    with open(p38.FULL_CSV, encoding="utf-8") as fh:
        sector = {r["ticker"]: r["gics_sector"] for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}
    tickers = sorted(added)
    df = lab.download(tickers + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)
    fdf = lab.download(p38.FUNDS, True, p32.DATA_END, start=p32.DATA_START).reindex(df.index)
    have = set(df.columns.get_level_values(1))
    names = [t for t in tickers if t in have and sector.get(t) in p38.SECTOR_FUND]
    if smoke:
        names = names[::max(1, len(names) // 80)][:80]

    spy_d = df["Close"]["SPY"].to_numpy(dtype=float)
    sess = [i for i, v in enumerate(spy_d) if v == v]
    days = [df.index[i].date() for i in sess]
    iso = [d.isocalendar()[:2] for d in days]
    first = [i for i in range(len(days)) if i == 0 or iso[i] != iso[i - 1]]
    last = [i for i in range(len(days)) if i == len(days) - 1 or iso[i] != iso[i + 1]]
    fridays = [days[i].isoformat() for i in last]

    Od, Cd = p38.weekly(df, names, sess)
    sOd, sCd = p38.weekly(df, ["SPY"], sess)
    _, fCd = p38.weekly(fdf, p38.FUNDS, sess)
    Ow, Cw = Od[first], Cd[last]
    sCw = sCd[last][:, 0]
    nW, n = Cw.shape
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names")

    slope, r2, z = fits(Cd, last)
    s_slope, _, _ = fits(sCd, last)
    f_slope, _, _ = fits(fCd, last)
    valid = ~np.isnan(z)
    for T in FRAMES:
        valid &= ~np.isnan(slope[T]) & ~np.isnan(r2[T])
    lined = valid.copy()
    for T in FRAMES:
        lined &= np.nan_to_num(slope[T], nan=-1.0) > 0
    rising = valid & (np.nan_to_num(slope[CHANNEL], nan=-1.0) > 0)
    straight = np.mean([r2[T] for T in FRAMES], axis=0)

    def trending(sl):
        return (np.nan_to_num(sl[126], nan=-1.0) > 0) & (np.nan_to_num(sl[252], nan=-1.0) > 0)
    mkt_up = trending(s_slope)[:, 0]
    f_up_raw = trending(f_slope)
    f_has = ~np.isnan(f_slope[252])
    fidx = {f: i for i, f in enumerate(p38.FUNDS)}
    f_up = np.zeros_like(f_up_raw)
    for f, i in fidx.items():
        fb = fidx.get(p38.FALLBACK.get(f, ""), i)
        f_up[:, i] = np.where(f_has[:, i], f_up_raw[:, i], f_up_raw[:, fb])
    sec_of = np.array([fidx[p38.SECTOR_FUND[sector[t]]] for t in names])
    backdrop = f_up[:, sec_of].astype(float) + mkt_up[:, None].astype(float)        # 0, 1 or 2
    room = {"fixed": np.full((nW, n), 2.5), "backdrop": 2.0 + 0.5 * backdrop, "reversed": 3.0 - 0.5 * backdrop}

    pin = p38.pinned_table(Ow, Cw)
    added_arr = np.array([added[t] or "0000-00-00" for t in names])
    council = np.array([t in set(STOCK_UNIVERSE) for t in names])

    w0 = next(w for w in range(nW) if valid[w].sum() >= 20)
    if smoke:
        w0 = max(w0, next(w for w in range(nW) if fridays[w] >= "2022-01-01"))
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    with np.errstate(invalid="ignore", divide="ignore"):
        R_hold = Cw[1:] / Cw[:-1] - 1.0
        R_in = Cw[1:] / Ow[1:] - 1.0
        R_out = Ow[1:] / Cw[:-1] - 1.0
    spy = [float(sCw[w + 1] / sCw[w] - 1.0) for w in weeks]
    half = [i for i, d in enumerate(wk_dates) if d < HALF]
    half2 = [i for i, d in enumerate(wk_dates) if d >= HALF]

    def block(rets):
        res = {"all": p38.stats(rets, spy, wk_dates)}
        for key, idx in (("first_half", half), ("second_half", half2)):
            res[key] = (p38.stats([rets[i] for i in idx], [spy[i] for i in idx], [wk_dates[i] for i in idx])
                        if len(idx) > 2 else None)
        return res

    base_pool = valid[:-1] & (added_arr[None, :] <= np.array(fridays[:-1])[:, None]) & ~np.isnan(R_hold)
    listr = [float(R_hold[w][base_pool[w]].mean()) if base_pool[w].any() else 0.0 for w in weeks]
    draws = 20 if smoke else DRAWS
    out = {"generated": fridays[-1], "weeks": len(weeks), "names": n, "council_names": int(council.sum()),
           "first_week": wk_dates[0], "last_week": wk_dates[-1],
           "controls": {"SPY": block(spy), "list": block(listr)}, "arms": {}}

    for name, width, top, need_lined, only_council in ARMS:
        rng = np.random.default_rng(SEED)
        line = -room[width]
        alive = rising & (z >= line)
        if top:
            alive = alive & (z < SELL_Z)
        entry = (lined if need_lined else rising) & (z <= BUY_Z) & (z >= line) & ~pin
        member = council if only_council else np.ones(n, dtype=bool)
        held, since = [], {}
        rets, counts, holds, trades, exits_top, exits_break = [], [], [], 0, 0, 0
        rand = np.zeros((draws, len(weeks)))
        for i, w in enumerate(weeks):
            keep = [j for j in held if alive[w, j] and not np.isnan(R_hold[w, j])]
            gone = [j for j in held if j not in keep]
            for j in gone:
                if top and z[w, j] >= SELL_Z:
                    exits_top += 1
                else:
                    exits_break += 1
            entries = []
            if len(keep) < SLOTS:
                cand = np.flatnonzero(entry[w] & member & (added_arr <= fridays[w]) & ~np.isnan(R_in[w]))
                per = {}
                for j in keep:
                    per[sec_of[j]] = per.get(sec_of[j], 0) + 1
                kept = set(keep)
                for j in sorted(cand, key=lambda j: (-straight[w, j], names[j])):
                    if len(keep) + len(entries) >= SLOTS:
                        break
                    if j in kept or per.get(sec_of[j], 0) >= PER_SECTOR:
                        continue
                    entries.append(int(j))
                    per[sec_of[j]] = per.get(sec_of[j], 0) + 1
            r = sum(R_hold[w, j] for j in keep)
            r += sum((0.0 if np.isnan(R_out[w, j]) else R_out[w, j]) - SLIP for j in gone)
            r += sum(R_in[w, j] - SLIP for j in entries)
            rets.append(WEIGHT * float(r))
            for j in gone:
                holds.append(w - since.pop(j))
            for j in entries:
                since[j] = w
            trades += len(gone) + len(entries)
            held = keep + entries
            k = len(held)
            counts.append(k)
            pool = np.flatnonzero(base_pool[w] & member)
            if k and len(pool) >= k:
                pick = rng.random((draws, len(pool))).argpartition(k - 1, axis=1)[:, :k]
                rand[:, i] = WEIGHT * R_hold[w][pool][pick].sum(axis=1)
        res = block(rets)

        def place(idx):
            if len(idx) < 3:
                return None
            mine = float(np.mean([rets[i] for i in idx]))
            means = rand[:, idx].mean(axis=1)
            return {"percentile": float((means < mine).mean() * 100.0), "random_mean_week": float(means.mean()),
                    "arm_mean_week": mine}
        res["vs_random"] = {"all": place(list(range(len(weeks)))), "first_half": place(half), "second_half": place(half2)}
        res["avg_exposure"] = float(np.mean(counts)) * WEIGHT
        res["weeks_in_cash"] = int(sum(1 for c in counts if c == 0))
        res["trades_per_year"] = trades / (len(weeks) / 52.0)
        res["median_hold_weeks"] = float(np.median(holds)) if holds else None
        res["mean_hold_weeks"] = float(np.mean(holds)) if holds else None
        res["closed_positions"] = len(holds)
        res["exits_at_top"], res["exits_on_break"] = exits_top, exits_break
        if name == "line+width":
            years = {}
            for d, a, b in zip(wk_dates, rets, spy):
                y = years.setdefault(d[:4], [1.0, 1.0])
                y[0] *= 1.0 + a
                y[1] *= 1.0 + b
            res["by_year"] = {y: {"arm": v[0] - 1.0, "spy": v[1] - 1.0} for y, v in years.items()}
            res["held_into_last_week"] = [{"ticker": names[j], "weeks_held": int(weeks[-1] - since[j] + 1),
                                           "z": float(z[weeks[-1], j])} for j in held]
        out["arms"][name] = res

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print(f"{len(weeks)} weeks {wk_dates[0]} .. {wk_dates[-1]}; council names {out['council_names']}")
    print(f"{'arm':15} {'CAGR':>7} {'vol':>7} {'Sharpe':>6} {'maxDD':>7} {'expo':>7} {'pct':>5} {'h1':>5} {'h2':>5} {'hold':>5} {'tr/yr':>6} {'top':>5} {'break':>5}")
    for nm, b in list(out["controls"].items()) + list(out["arms"].items()):
        a = b["all"]
        v = b.get("vs_random") or {}
        g = lambda k: "   --" if not v.get(k) else f"{v[k]['percentile']:5.0f}"  # noqa: E731
        hold = b.get("median_hold_weeks")
        print(f"{nm:15} {P(a['cagr'])} {P(a['vol'])} {a['sharpe']:6.2f} {P(a['max_drawdown'])} {P(b.get('avg_exposure'), 0)} "
              f"{g('all')} {g('first_half')} {g('second_half')} {'   --' if hold is None else f'{hold:5.0f}'} "
              f"{b.get('trades_per_year', 0):6.0f} {b.get('exits_at_top', 0):5d} {b.get('exits_on_break', 0):5d}")
    prim = out["arms"]["line+width"]
    for y, v in prim["by_year"].items():
        print(f"   {y}  arm {P(v['arm'])}  SPY {P(v['spy'])}")
    print("   held:", ", ".join(f"{h['ticker']} ({h['weeks_held']}w)" for h in prim["held_into_last_week"]) or "cash")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
