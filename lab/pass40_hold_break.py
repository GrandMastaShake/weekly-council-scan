#!/usr/bin/env python3
"""Pass 40 -- hold until it breaks: a wider channel, drawn once.

Pass 38's entry, with the exit changed two ways: wider break lines, and an
anchored channel (the 26-week line and width fixed on the day of entry and
extended forward) sold only on a close below that line by the break width.

Registered in lab/README.md (Pass 40) before any run.

    python lab/pass40_hold_break.py          # every arm
    python lab/pass40_hold_break.py smoke    # plumbing: 2022 on, 80 names, 20 draws
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

SLOTS, PER_SECTOR, WEIGHT, SLIP = p38.SLOTS, p38.PER_SECTOR, p38.WEIGHT, p38.SLIP
ENTRY_BREAK = 2.5
DRAWS = 200
SEED = 20261122
OUT = lab.RESULTS / "pass40_hold_break.json"

#        name                         anchored width brake
ARMS = [("refit 3",                   False,   3.0,  False),
        ("refit 4",                   False,   4.0,  False),
        ("refit 5",                   False,   5.0,  False),
        ("anchored 2.5",              True,    2.5,  False),
        ("anchored 4",                True,    4.0,  False),
        ("anchored 6",                True,    6.0,  False),
        ("anchored 4, market brake",  True,    4.0,  True)]


def line_table(Cw):
    """The 26-week log line at each week: its value at that week, slope, width."""
    nW, n = Cw.shape
    at = np.full((nW, n), np.nan)
    slope = np.full((nW, n), np.nan)
    width = np.full((nW, n), np.nan)
    x = np.arange(26) - 12.5
    sxx = float((x * x).sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        for w in range(25, nW):
            y = np.log(Cw[w - 25:w + 1])
            yb = y.mean(axis=0)
            b = (x[:, None] * (y - yb)).sum(axis=0) / sxx
            resid = y - (yb + b * x[:, None])
            at[w], slope[w] = yb + b * 12.5, b
            width[w] = np.sqrt((resid ** 2).sum(axis=0) / 24.0)
    return at, slope, width


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    added = p32.members()
    with open(p38.FULL_CSV, encoding="utf-8") as fh:
        sector = {r["ticker"]: r["gics_sector"] for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}
    tickers = sorted(added)
    df = lab.download(tickers + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)
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
    Ow, Cw, sCw = Od[first], Cd[last], sCd[last]
    nW, n = Cw.shape
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names")

    up, z, score, valid = p38.facts_table(Cw)
    s_up, s_z, _, s_valid = p38.facts_table(sCw)
    mkt_ok = s_valid[:, 0] & s_up[:, 0] & (s_z[:, 0] >= -p38.BREAK)
    at, slope, width = line_table(Cw)
    logC = np.log(Cw)
    pin = p38.pinned_table(Ow, Cw)
    fidx = {f: i for i, f in enumerate(p38.FUNDS)}
    sec_of = np.array([fidx[p38.SECTOR_FUND[sector[t]]] for t in names])
    added_arr = np.array([added[t] or "0000-00-00" for t in names])

    w0 = next(w for w in range(nW) if s_valid[w, 0])
    if smoke:
        w0 = max(w0, next(w for w in range(nW) if fridays[w] >= "2022-01-01"))
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    with np.errstate(invalid="ignore", divide="ignore"):
        R_hold = Cw[1:] / Cw[:-1] - 1.0
        R_in = Cw[1:] / Ow[1:] - 1.0
        R_out = Ow[1:] / Cw[:-1] - 1.0
    spy = [float(sCw[w + 1, 0] / sCw[w, 0] - 1.0) for w in weeks]
    half = [i for i, d in enumerate(wk_dates) if d < p38.HALF]
    half2 = [i for i, d in enumerate(wk_dates) if d >= p38.HALF]

    def block(rets):
        res = {"all": p38.stats(rets, spy, wk_dates)}
        for key, idx in (("first_half", half), ("second_half", half2)):
            res[key] = (p38.stats([rets[i] for i in idx], [spy[i] for i in idx], [wk_dates[i] for i in idx])
                        if len(idx) > 2 else None)
        return res

    pool = [np.flatnonzero(valid[w] & (added_arr <= fridays[w]) & ~np.isnan(R_hold[w])) for w in range(nW - 1)]
    listr = [float(R_hold[w][pool[w]].mean()) if len(pool[w]) else 0.0 for w in weeks]
    draws = 20 if smoke else DRAWS
    out = {"generated": fridays[-1], "weeks": len(weeks), "names": n, "first_week": wk_dates[0],
           "last_week": wk_dates[-1], "controls": {"SPY": block(spy), "list": block(listr)}, "arms": {}}
    entry_ok = (valid & up & (z >= -ENTRY_BREAK) & (z <= 0) & ~pin & ~np.isnan(score)
                & ~np.isnan(width) & (np.nan_to_num(width) > 0))

    for name, anchored, brk, brake in ARMS:
        rng = np.random.default_rng(SEED)
        refit_ok = valid & up & (z >= -brk)
        held, since, anchor = [], {}, {}
        rets, counts, holds, trades = [], [], [], 0
        rand = np.zeros((draws, len(weeks)))
        for i, w in enumerate(weeks):
            m_ok = bool(mkt_ok[w]) or not brake

            def alive(j):
                if not m_ok or np.isnan(R_hold[w, j]) or np.isnan(logC[w, j]):
                    return False
                if not anchored:
                    return bool(refit_ok[w, j])
                a, b, wd, e = anchor[j]
                return logC[w, j] >= a + b * (w - e) - brk * wd
            keep = [j for j in held if alive(j)]
            gone = [j for j in held if j not in keep]
            entries = []
            if m_ok and len(keep) < SLOTS:
                cand = np.flatnonzero(entry_ok[w] & (added_arr <= fridays[w]) & ~np.isnan(R_in[w]))
                per = {}
                for j in keep:
                    per[sec_of[j]] = per.get(sec_of[j], 0) + 1
                kept = set(keep)
                for j in sorted(cand, key=lambda j: (-score[w, j], names[j])):
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
                anchor.pop(j, None)
            for j in entries:
                since[j] = w
                anchor[j] = (float(at[w, j]), float(slope[w, j]), float(width[w, j]), w)
            trades += len(gone) + len(entries)
            held = keep + entries
            k = len(held)
            counts.append(k)
            if k and len(pool[w]) >= k:
                pick = rng.random((draws, len(pool[w]))).argpartition(k - 1, axis=1)[:, :k]
                rand[:, i] = WEIGHT * R_hold[w][pool[w]][pick].sum(axis=1)
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
        res["longest_hold_weeks"] = int(max(holds)) if holds else None
        res["closed_positions"] = len(holds)
        if name == "anchored 4":
            years = {}
            for d, a, b in zip(wk_dates, rets, spy):
                y = years.setdefault(d[:4], [1.0, 1.0])
                y[0] *= 1.0 + a
                y[1] *= 1.0 + b
            res["by_year"] = {y: {"arm": v[0] - 1.0, "spy": v[1] - 1.0} for y, v in years.items()}
            res["held_into_last_week"] = [{"ticker": names[j], "weeks_held": int(weeks[-1] - since[j] + 1)} for j in held]
        out["arms"][name] = res

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print(f"{len(weeks)} weeks {wk_dates[0]} .. {wk_dates[-1]}")
    print(f"{'arm':26} {'CAGR':>7} {'vol':>7} {'Sharpe':>6} {'maxDD':>7} {'expo':>7} {'pct':>5} {'h1':>5} {'h2':>5} {'hold':>5} {'tr/yr':>6}")
    for nm, b in list(out["controls"].items()) + list(out["arms"].items()):
        a = b["all"]
        v = b.get("vs_random") or {}
        g = lambda k: "   --" if not v.get(k) else f"{v[k]['percentile']:5.0f}"  # noqa: E731
        hold = b.get("median_hold_weeks")
        print(f"{nm:26} {P(a['cagr'])} {P(a['vol'])} {a['sharpe']:6.2f} {P(a['max_drawdown'])} {P(b.get('avg_exposure'), 0)} "
              f"{g('all')} {g('first_half')} {g('second_half')} {'   --' if hold is None else f'{hold:5.0f}'} "
              f"{b.get('trades_per_year', 0):6.0f}")
    prim = out["arms"]["anchored 4"]
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
