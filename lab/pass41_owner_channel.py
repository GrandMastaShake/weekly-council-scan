#!/usr/bin/env python3
"""Pass 41 -- the owner's channel: from the swing low along the lows, held
until a weekly close breaks it.

The channel is drawn the way the owner drew CAT's: anchored at the lowest
weekly low of the last two years, the lower line the steepest straight line
(log scale) under every low since, the upper line parallel through the highs.
A name is bought when that channel rises and its closes are a straight line;
the lower line is fixed at entry and the name is sold on the first weekly
close below it.

Registered in lab/README.md (Pass 41) before any run.

    python lab/pass41_owner_channel.py          # every arm
    python lab/pass41_owner_channel.py smoke    # plumbing: 2022 on, 80 names, 20 draws
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass32_stop_random as p32  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402

LOOKBACK = 104
MIN_AGE, MAX_AGE = 26, 100
MIN_SLOPE_YEAR = 0.10
SLOTS, PER_SECTOR, WEIGHT, SLIP = p38.SLOTS, p38.PER_SECTOR, p38.WEIGHT, p38.SLIP
DRAWS = 200
SEED = 20261123
OUT = lab.RESULTS / "pass41_owner_channel.json"

#        name               r2    lower-half buffer brake
ARMS = [("owner's channel", 0.80, False,     0.00,  False),
        ("lower half",      0.80, True,      0.00,  False),
        ("3% buffer",       0.80, False,     0.03,  False),
        ("straighter",      0.90, False,     0.00,  False),
        ("market brake",    0.80, False,     0.00,  True)]


def draw(lc, lh, ll):
    """The channel at the last bar of the window, or None. Arrays are log
    close, high and low for up to LOOKBACK weeks, no NaN."""
    n = len(lc)
    a = int(np.argmin(ll))
    age = n - 1 - a
    if age < MIN_AGE or age > MAX_AGE:
        return None
    t = np.arange(1, age + 1)
    b = float(((ll[a + 1:] - ll[a]) / t).min())
    line = ll[a] + b * np.arange(0, age + 1)
    top = float((lh[a:] - line).max())
    if top <= 0:
        return None
    y = lc[a:]
    x = np.arange(len(y)) - (len(y) - 1) / 2.0
    d = y - y.mean()
    sst = float((d * d).sum())
    if sst <= 0:
        return None
    k = float((x * d).sum() / (x * x).sum())
    r2 = 1.0 - float(((d - k * x) ** 2).sum()) / sst
    return {"lower": float(line[-1]), "slope": b, "height": top, "r2": r2, "age": age,
            "pos": float((lc[-1] - line[-1]) / top)}


def channel_table(Cw, Hw, Lw):
    nW, n = Cw.shape
    lower = np.full((nW, n), np.nan)
    slope = np.full((nW, n), np.nan)
    r2 = np.full((nW, n), np.nan)
    pos = np.full((nW, n), np.nan)
    height = np.full((nW, n), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        lC, lH, lL = np.log(Cw), np.log(Hw), np.log(Lw)
    bad = np.isnan(lC) | np.isnan(lH) | np.isnan(lL)
    run = np.zeros((nW, n), dtype=int)                 # consecutive clean weeks ending here
    for w in range(nW):
        run[w] = np.where(bad[w], 0, (run[w - 1] if w else 0) + 1)
    for j in range(n):
        for w in range(MIN_AGE, nW):
            m = min(LOOKBACK, int(run[w, j]))
            if m <= MIN_AGE:
                continue
            ch = draw(lC[w - m + 1:w + 1, j], lH[w - m + 1:w + 1, j], lL[w - m + 1:w + 1, j])
            if ch:
                lower[w, j], slope[w, j], r2[w, j] = ch["lower"], ch["slope"], ch["r2"]
                pos[w, j], height[w, j] = ch["pos"], ch["height"]
    return lower, slope, r2, pos, height


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
        if "CAT" in have and "CAT" not in names:
            names.append("CAT")

    spy_d = df["Close"]["SPY"].to_numpy(dtype=float)
    sess = [i for i, v in enumerate(spy_d) if v == v]
    days = [df.index[i].date() for i in sess]
    iso = [d.isocalendar()[:2] for d in days]
    first = [i for i in range(len(days)) if i == 0 or iso[i] != iso[i - 1]]
    last = [i for i in range(len(days)) if i == len(days) - 1 or iso[i] != iso[i + 1]]
    fridays = [days[i].isoformat() for i in last]
    Od, Cd = p38.weekly(df, names, sess)
    Hd = df["High"][names].to_numpy(dtype=float)[sess]
    Ld = df["Low"][names].to_numpy(dtype=float)[sess]
    sOd, sCd = p38.weekly(df, ["SPY"], sess)
    Ow, Cw, sCw = Od[first], Cd[last], sCd[last]
    with np.errstate(invalid="ignore"):
        Hw = np.array([np.nanmax(Hd[a:b + 1], axis=0) for a, b in zip(first, last)])
        Lw = np.array([np.nanmin(Ld[a:b + 1], axis=0) for a, b in zip(first, last)])
    nW, n = Cw.shape
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names")

    lower, slope, r2, pos, height = channel_table(Cw, Hw, Lw)
    s_up, s_z, _, s_valid = p38.facts_table(sCw)
    mkt_ok = s_valid[:, 0] & s_up[:, 0] & (s_z[:, 0] >= -p38.BREAK)
    with np.errstate(invalid="ignore", divide="ignore"):
        logC = np.log(Cw)
    pin = p38.pinned_table(Ow, Cw)
    fidx = {f: i for i, f in enumerate(p38.FUNDS)}
    sec_of = np.array([fidx[p38.SECTOR_FUND[sector[t]]] for t in names])
    added_arr = np.array([added[t] or "0000-00-00" for t in names])
    floor = math.log(1.0 + MIN_SLOPE_YEAR) / 52.0
    has = ~np.isnan(lower) & (np.nan_to_num(slope, nan=-1.0) >= floor)

    w0 = next(w for w in range(nW) if has[w].sum() >= 5)
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

    clean = ~np.isnan(Cw)
    pool = [np.flatnonzero(clean[w] & (added_arr <= fridays[w]) & ~np.isnan(R_hold[w])) for w in range(nW - 1)]
    listr = [float(R_hold[w][pool[w]].mean()) if len(pool[w]) else 0.0 for w in weeks]
    draws = 20 if smoke else DRAWS
    out = {"generated": fridays[-1], "weeks": len(weeks), "names": n, "first_week": wk_dates[0],
           "last_week": wk_dates[-1], "controls": {"SPY": block(spy), "list": block(listr)}, "arms": {},
           "share_of_name_weeks_with_a_channel": float(has[w0:].sum() / max(1, clean[w0:].sum()))}

    for name, r2_min, lower_half, buf, brake in ARMS:
        rng = np.random.default_rng(SEED)
        entry_ok = has & (np.nan_to_num(r2, nan=0.0) >= r2_min) & ~pin
        if lower_half:
            entry_ok = entry_ok & (np.nan_to_num(pos, nan=9.0) <= 0.5)
        tol = math.log(1.0 - buf) if buf else 0.0
        held, since, anchor = [], {}, {}
        rets, counts, holds, trades, gains = [], [], [], 0, []
        rand = np.zeros((draws, len(weeks)))
        cand_counts = []
        for i, w in enumerate(weeks):
            m_ok = bool(mkt_ok[w]) or not brake
            keep = []
            for j in held:
                a, b, e, _ = anchor[j]
                if m_ok and not np.isnan(R_hold[w, j]) and not np.isnan(logC[w, j]) and logC[w, j] >= a + b * (w - e) + tol:
                    keep.append(j)
            gone = [j for j in held if j not in keep]
            entries = []
            cand = np.flatnonzero(entry_ok[w] & (added_arr <= fridays[w]) & ~np.isnan(R_in[w]))
            cand_counts.append(len(cand))
            if m_ok and len(keep) < SLOTS:
                per = {}
                for j in keep:
                    per[sec_of[j]] = per.get(sec_of[j], 0) + 1
                kept = set(keep)
                for j in sorted(cand, key=lambda j: (-r2[w, j], names[j])):
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
                e_px = anchor.pop(j)[3]
                x_px = Ow[w + 1, j] if not np.isnan(Ow[w + 1, j]) else Cw[w, j]
                gains.append(float(x_px / e_px - 1.0))
            for j in entries:
                since[j] = w
                anchor[j] = (float(lower[w, j]), float(slope[w, j]), w, float(Ow[w + 1, j]))
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
        res["median_candidates"] = float(np.median(cand_counts))
        res["trades_per_year"] = trades / (len(weeks) / 52.0)
        res["median_hold_weeks"] = float(np.median(holds)) if holds else None
        res["mean_hold_weeks"] = float(np.mean(holds)) if holds else None
        res["longest_hold_weeks"] = int(max(holds)) if holds else None
        res["closed_positions"] = len(holds)
        res["share_closed_at_a_gain"] = float(np.mean([g > 0 for g in gains])) if gains else None
        res["median_closed_gain"] = float(np.median(gains)) if gains else None
        res["mean_closed_gain"] = float(np.mean(gains)) if gains else None
        if name == "owner's channel":
            years = {}
            for d, a, b in zip(wk_dates, rets, spy):
                y = years.setdefault(d[:4], [1.0, 1.0])
                y[0] *= 1.0 + a
                y[1] *= 1.0 + b
            res["by_year"] = {y: {"arm": v[0] - 1.0, "spy": v[1] - 1.0} for y, v in years.items()}
            res["held_into_last_week"] = [{"ticker": names[j], "weeks_held": int(weeks[-1] - since[j] + 1)} for j in held]
            if "CAT" in names:
                j = names.index("CAT")
                res["cat_check"] = [{"week": fridays[w], "channel": bool(has[w, j]),
                                     "r2": None if np.isnan(r2[w, j]) else round(float(r2[w, j]), 2),
                                     "pos": None if np.isnan(pos[w, j]) else round(float(pos[w, j]), 2),
                                     "close": round(float(Cw[w, j]), 2)} for w in range(nW - 30, nW, 3)]
        out["arms"][name] = res

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print(f"{len(weeks)} weeks {wk_dates[0]} .. {wk_dates[-1]}; name-weeks with a channel {P(out['share_of_name_weeks_with_a_channel'])}")
    print(f"{'arm':16} {'CAGR':>7} {'vol':>7} {'Sharpe':>6} {'maxDD':>7} {'expo':>7} {'pct':>5} {'h1':>5} {'h2':>5} {'hold':>5} {'tr/yr':>6} {'win':>7} {'med gain':>8}")
    for nm, b in list(out["controls"].items()) + list(out["arms"].items()):
        a = b["all"]
        v = b.get("vs_random") or {}
        g = lambda k: "   --" if not v.get(k) else f"{v[k]['percentile']:5.0f}"  # noqa: E731
        hold = b.get("median_hold_weeks")
        print(f"{nm:16} {P(a['cagr'])} {P(a['vol'])} {a['sharpe']:6.2f} {P(a['max_drawdown'])} {P(b.get('avg_exposure'), 0)} "
              f"{g('all')} {g('first_half')} {g('second_half')} {'   --' if hold is None else f'{hold:5.0f}'} "
              f"{b.get('trades_per_year', 0):6.0f} {P(b.get('share_closed_at_a_gain'), 0)} {P(b.get('median_closed_gain'))}")
    prim = out["arms"]["owner's channel"]
    for y, v in prim["by_year"].items():
        print(f"   {y}  arm {P(v['arm'])}  SPY {P(v['spy'])}")
    print("   held:", ", ".join(f"{h['ticker']} ({h['weeks_held']}w)" for h in prim["held_into_last_week"]) or "cash")
    for row in prim.get("cat_check", []):
        print("   CAT", row)
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
