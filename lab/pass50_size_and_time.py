#!/usr/bin/env python3
"""Pass 50 -- how much and when: sizing and staged buying and selling.

Part A puts sizing (equal dollars or equal risk), staged buying and staged
selling on Pass 48's channel-hold book. Part B puts sizing and a staged
Monday/Wednesday entry on the weekly Council's engine replay (Pass 49).

Registered in lab/README.md (Pass 50) before any run.

    python lab/pass50_size_and_time.py          # both parts
    python lab/pass50_size_and_time.py smoke    # plumbing: 300 names, eight weeks
"""
from __future__ import annotations

import itertools
import json
import math
import pickle
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import channel_universe as cu  # noqa: E402
import pass32_stop_random as p32  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402
import pass41_owner_channel as p41  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402
import pass48_screen_book as p48  # noqa: E402

ADD_AFTER = 4
HALF = p38.HALF
OUT = lab.RESULTS / "pass50_size_and_time.json"


def part_a(smoke):
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
    member = tradeable & (tier >= 0) & (tier <= 1)
    print("part A: drawing channels ...", flush=True)
    lower, slope, r2, _, _ = p41.channel_table(Cw, Hw, Lw)
    screen = (member & ~np.isnan(lower) & (np.nan_to_num(slope, nan=-1.0) >= p48.FLOOR)
              & (np.nan_to_num(r2, nan=0.0) >= p48.R2_MIN) & (np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX))
    w0 = 110
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    spans = {"all": ("0", "9"), "to 2016": ("0", HALF), "2017 on": (HALF, "9")}
    res, series = {}, {}
    for risk, buy_halves, sell_halves in itertools.product((False, True), repeat=3):
        name = ", ".join(("equal risk" if risk else "equal dollars", "buy in halves" if buy_halves else "buy at once",
                          "sell in halves" if sell_halves else "sell at once"))
        held = {}                      # j -> [entry week, line, slope, fraction, entry close, warned]
        prev_w = {}
        rets, counts, turnover = [], [], 0.0
        for w in weeks:
            out_now = []
            for j, st in list(held.items()):
                e, a_, b_, frac, c0, warned = st
                if np.isnan(R_hold[w, j]) or np.isnan(lC[w, j]):
                    out_now.append(j)
                    continue
                if lC[w, j] < a_ + b_ * (w - e):
                    if sell_halves and not warned:
                        st[5], st[3] = True, frac * 0.5
                    else:
                        out_now.append(j)
                        continue
                if buy_halves and not st[5] and st[3] < 1.0 and w - e >= ADD_AFTER and Cw[w, j] > c0:
                    st[3] = 1.0
            for j in out_now:
                held.pop(j)
            new = [int(j) for j in np.flatnonzero(screen[w] & ~np.isnan(R_in[w])) if j not in held and j not in out_now]
            for j in new:
                held[j] = [w, float(lower[w, j]), float(slope[w, j]), 0.5 if buy_halves else 1.0, float(Cw[w, j]), False]
            raw = {j: st[3] * ((1.0 / swing[w, j]) if risk and swing[w, j] == swing[w, j] and swing[w, j] > 0 else
                               (1.0 if not risk else 1.0 / 0.04)) for j, st in held.items()}
            tot = sum(raw.values())
            wts = {j: v / tot for j, v in raw.items()} if tot else {}
            r = 0.0
            for j, wt in wts.items():
                r += wt * (R_in[w, j] if j in new else R_hold[w, j])
            # A sold name leaves at the weights set here; its Friday-to-Monday gap is not counted.
            cost = sum(abs(wts.get(j, 0.0) - prev_w.get(j, 0.0)) * slip_of[tier[w, j]]
                       for j in set(wts) | set(prev_w) if (j in new or j in out_now or abs(wts.get(j, 0.0) - prev_w.get(j, 0.0)) > 0.25 * max(wts.get(j, 0.0), prev_w.get(j, 0.0))))
            turnover += sum(abs(wts.get(j, 0.0) - prev_w.get(j, 0.0)) for j in set(wts) | set(prev_w)) / 2.0
            rets.append(float(r - cost))
            counts.append(len(held))
            prev_w = wts
        series[name] = rets
        res[name] = {"avg_names_held": float(np.mean(counts)), "turnover_a_year": turnover / (len(weeks) / 52.0), "book": {}}
        for sp, (a, b) in spans.items():
            ix = [i for i, d in enumerate(wk_dates) if a <= d < b]
            st = p38.stats([rets[i] for i in ix], [0.0] * len(ix), [wk_dates[i] for i in ix])
            res[name]["book"][sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "vol": st["vol"], "max_drawdown": st["max_drawdown"]}
    return {"weeks": len(weeks), "first_week": wk_dates[0], "names": n, "books": res}


def part_b(smoke):
    import forward as fwd
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
    names = sorted(set(STOCK_UNIVERSE))
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7 if today.weekday() < 5 else today.weekday())
    weeks, d = [], date.fromisoformat("2024-06-03")
    while d <= last_monday:
        weeks.append((d.isoformat(), d.isoformat(), None))
        d += timedelta(days=7)
    if smoke:
        weeks = weeks[-8:]
    cal = lab.earnings_calendar(names, max_age_days=6)
    start = lab._plus(weeks[0][1], -100)
    rows = lab.run(verbose=False, knobs={"pe_builder": fwd._pe_builder}, weeks=weeks, start=start, earnings=cal)
    end = lab._plus(weeks[-1][1], 5)
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(sorted(set(names)) + lab.EXTRA, True, end, start)).items()}
    bars = cu.weekly_bars(names)

    def swing_before(t, W):
        if t not in bars:
            return None
        dates, _, _, c = bars[t]
        k = sum(1 for x in dates if x < W)
        if k and (date.fromisoformat(W) - date.fromisoformat(dates[k - 1])).days < 5:
            k -= 1
        r = np.diff(np.log(c[max(0, k - 53):k]))
        return float(r.std()) if len(r) >= 20 else None

    def legs(t, W):
        """(Monday open to Friday close, Wednesday open over Monday open - 1, Wednesday open to Friday close)."""
        s = adj.get(t)
        if not s:
            return None
        wk = [r for r in s.rows if W <= r["date"] <= lab._plus(W, 4)]
        if len(wk) < 3:
            return None
        return (wk[-1]["close"] / wk[0]["open"] - 1.0, wk[2]["open"] / wk[0]["open"] - 1.0, wk[-1]["close"] / wk[2]["open"] - 1.0)
    books = {}
    for sizing in ("production's weights", "equal dollars", "equal risk"):
        for buying in ("all on Monday", "half, then add on strength", "half, then add on weakness"):
            alphas = []
            for row in rows:
                W, spy = row["monday"], row["spy_ret"]
                picks = [(b["ticker"], b["weight"]) for b in row["book"]]
                if not picks:
                    alphas.append(-spy)
                    continue
                invested = sum(w for _, w in picks)
                if sizing == "equal dollars":
                    wts = {t: invested / len(picks) for t, _ in picks}
                elif sizing == "equal risk":
                    inv = {t: 1.0 / (swing_before(t, W) or 0.05) for t, _ in picks}
                    wts = {t: invested * v / sum(inv.values()) for t, v in inv.items()}
                else:
                    wts = dict(picks)
                r = 0.0
                for t, wt in wts.items():
                    lg = legs(t, W)
                    if lg is None:
                        continue
                    full, to_wed, from_wed = lg
                    if buying == "all on Monday":
                        r += wt * full
                    else:
                        add = to_wed > 0 if "strength" in buying else to_wed < 0
                        r += wt * (0.5 * full + (0.5 * from_wed if add else 0.0))
                alphas.append(r - spy)
            half = len(alphas) // 2

            def blk(xs):
                sd = statistics.pstdev(xs) if len(xs) > 1 else None
                return {"weeks": len(xs), "mean_alpha": statistics.fmean(xs), "sd": sd,
                        "alpha_per_sd": (statistics.fmean(xs) / sd) if sd else None, "worst_week": min(xs),
                        "t": p32.tstat(xs)}
            books[f"{sizing}; {buying}"] = {"all": blk(alphas), "first_half": blk(alphas[:half]), "second_half": blk(alphas[half:]),
                                           "series": alphas}
    base = books["production's weights; all on Monday"]["series"]
    for k, b in books.items():
        d_ = [x - y for x, y in zip(b["series"], base)]
        b["difference_from_production"] = statistics.fmean(d_)
        b["difference_t"] = p32.tstat(d_) if any(d_) else None
        del b["series"]
    return {"weeks": len(rows), "first": rows[0]["monday"], "last": rows[-1]["monday"], "books": books}


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    a = part_a(smoke)

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print(f"PART A: {a['weeks']} weeks from {a['first_week']}, {a['names']} names")
    print(f"{'book':48} {'CAGR':>7} {'h1':>7} {'h2':>7} {'vol':>7} {'Sharpe':>6} {'h1':>5} {'h2':>5} {'maxDD':>7} {'held':>5} {'turn/yr':>7}")
    for nm, r in a["books"].items():
        b = r["book"]
        print(f"{nm:48} {P(b['all']['cagr'])} {P(b['to 2016']['cagr'])} {P(b['2017 on']['cagr'])} {P(b['all']['vol'])} {b['all']['sharpe']:6.2f} "
              f"{b['to 2016']['sharpe']:5.2f} {b['2017 on']['sharpe']:5.2f} {P(b['all']['max_drawdown'])} {r['avg_names_held']:5.0f} {r['turnover_a_year']:7.1f}")
    b_ = part_b(smoke)
    print(f"PART B: {b_['weeks']} weeks {b_['first']} .. {b_['last']}")
    print(f"{'book':52} {'alpha/wk':>9} {'sd':>7} {'a/sd':>6} {'h1 a/sd':>8} {'h2 a/sd':>8} {'worst':>8} {'vs prod':>9} {'t':>6}")
    for nm, r in b_["books"].items():
        t = r["difference_t"]
        print(f"{nm:52} {P(r['all']['mean_alpha'], 3):>9} {P(r['all']['sd'], 2)} {r['all']['alpha_per_sd']:6.3f} {r['first_half']['alpha_per_sd']:8.3f} "
              f"{r['second_half']['alpha_per_sd']:8.3f} {P(r['all']['worst_week'], 1):>8} {P(r['difference_from_production'], 3):>9} "
              f"{'    --' if t is None else f'{t:6.2f}'}")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"generated": date.today().isoformat(), "A": a, "B": b_}, fh, indent=1, default=float)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
