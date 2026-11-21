#!/usr/bin/env python3
"""Pass 47 -- choosing: only add names in the four strongest sectors.

Pass 46's Heikin-Ashi channel with the dynamic exit (one weekly swing of
cushion) and a nine-week early entry, plus the owner's sector rule: a name is
only added in a week its sector is one of the four strongest, by the share of
its names in a channel or by the sector fund's 26-week return.

Registered in lab/README.md (Pass 47) before any run.

    python lab/pass47_sector_choice.py          # every arm, both sets
    python lab/pass47_sector_choice.py smoke    # plumbing: 400 names
"""
from __future__ import annotations

import json
import pickle
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass32_stop_random as p32  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402
import pass42_who_breaks_first as p42  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402
import pass46_ha_channel as p46  # noqa: E402

p46.EARLY_AGE, p46.EARLY_GREEN = 9, 6
TOP = 4
MIN_SECTOR = 10
FUND_WEEKS = 26
DRAWS = 200
SEED = 20261127
HALF = p38.HALF
OUT = lab.RESULTS / "pass47_sector_choice.json"
GICS = {"Finance": "Financials", "Technology": "Information Technology", "Basic Materials": "Materials",
        "Telecommunications": "Communication Services"}
ARMS = ["no sector rule", "top four by channels", "top four by fund", "bottom four by channels"]


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    uf = p43.universe_file()
    uni = {r["ticker"]: r for r in p43.read_universe(uf)}
    with open(p43.BARS, "rb") as fh:
        frames = pickle.load(fh)
    names = sorted(t for t in frames if t in uni)
    if smoke:
        names = names[::max(1, len(names) // 400)][:400]
    import pandas as pd
    idx = sorted(set().union(*[set(frames[t].index) for t in names[:200]]))
    idx = pd.DatetimeIndex([d for d in idx if d.weekday() == 0])

    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    iso = [tuple(date.fromisoformat(d).isocalendar()[:2]) for d in fridays]
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
    for w in range(26, nW):
        with np.errstate(invalid="ignore"):
            med_dv[w] = np.nanmedian(dv[max(0, w - 51):w + 1], axis=0)
            if w >= 52:
                win = wr[max(0, w - 104):w]
                cnt = (~np.isnan(win)).sum(axis=0)
                swing[w] = np.where(cnt >= 40, np.nanstd(win, axis=0), np.nan)
    tradeable = (Cw >= p43.PRICE_MIN) & (np.nan_to_num(med_dv) >= p43.DV_MIN) & (np.nan_to_num(swing) >= p46.SWING_MIN)
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
    top500 = tradeable & (tier >= 0) & (tier <= 1)
    sets = {"top 500": top500, "every tradeable name": tradeable}

    sectors = sorted(p38.SECTOR_FUND)
    sidx = {s: i for i, s in enumerate(sectors)}
    sec_of = np.array([sidx.get(GICS.get(uni[t]["sector"], uni[t]["sector"]), -1) for t in names])
    print("names with a sector:", int((sec_of >= 0).sum()), "of", n, flush=True)

    # the rule's own signals (dynamic, one swing, nine-week early entry), and who is in a channel each week
    trades = []
    in_channel = np.zeros((nW, n), dtype=bool)
    for j in range(n):
        ho, hl, hc = p46.heikin_ashi(Ow[:, j], Hw[:, j], Lw[:, j], Cw[:, j])
        for e, x, why in p46.signals(ho, hl, hc, swing[:, j], True, True, 1.0):
            trades.append((e, x, j, why))
            in_channel[e:(x if x is not None else nW), j] = True
    print("signals:", len(trades), flush=True)

    # sector strength, two ways
    breadth = np.full((nW, len(sectors)), np.nan)
    for k in range(len(sectors)):
        m = top500 & (sec_of == k)[None, :]
        cnt = m.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            breadth[:, k] = np.where(cnt >= MIN_SECTOR * (0.2 if smoke else 1.0), (m & in_channel).sum(axis=1) / cnt, np.nan)
    fdf = lab.download(p38.FUNDS, True, p32.DATA_END, start=p32.DATA_START)["Close"]
    fund_ret = np.full((nW, len(sectors)), np.nan)
    pos = {k: i for i, k in enumerate(iso)}
    for k, sname in enumerate(sectors):
        f = fdf[p38.SECTOR_FUND[sname]].dropna()
        wk = f.groupby([f.index.isocalendar().year, f.index.isocalendar().week]).last()
        col = np.full(nW, np.nan)
        for (y, wn), v in wk.items():
            i = pos.get((int(y), int(wn)))
            if i is not None:
                col[i] = float(v)
        with np.errstate(invalid="ignore", divide="ignore"):
            fund_ret[FUND_WEEKS:, k] = col[FUND_WEEKS:] / col[:-FUND_WEEKS] - 1.0

    def pick(table, w, best):
        row = table[w]
        ok = np.flatnonzero(~np.isnan(row))
        if len(ok) < TOP * 2:
            return set()
        order = ok[np.argsort(-row[ok] if best else row[ok], kind="stable")]
        return set(int(k) for k in order[:TOP])
    allow = {"no sector rule": None,
             "top four by channels": [pick(breadth, w, True) for w in range(nW)],
             "top four by fund": [pick(fund_ret, w, True) for w in range(nW)],
             "bottom four by channels": [pick(breadth, w, False) for w in range(nW)]}

    w0 = 66
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]

    def fwd(k):
        f = np.full((nW, n), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            f[:nW - k - 1] = Cw[k + 1:] / Ow[1:nW - k] - 1.0
        return f
    F13 = fwd(13)
    sdf = lab.download(sorted(p32.members()) + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)["Close"]["SPY"].dropna()
    spy_w = sdf.groupby([sdf.index.isocalendar().year, sdf.index.isocalendar().week]).last()
    spy_ret = dict(zip([(int(y), int(k)) for y, k in spy_w.index][1:], spy_w.pct_change().to_numpy()[1:]))
    spy = [float(spy_ret.get(tuple(date.fromisoformat(d).isocalendar()[:2]), 0.0)) for d in wk_dates]
    spans = {"all": ("0", "9"), "to 2016": ("0", HALF), "2017 on": (HALF, "9")}
    draws = 20 if smoke else DRAWS
    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "sectors": sectors, "spy": {}, "sets": {}}
    for sp, (a, b) in spans.items():
        ix = [i for i, d in enumerate(wk_dates) if a <= d < b]
        st = p38.stats([spy[i] for i in ix], [spy[i] for i in ix], [wk_dates[i] for i in ix])
        out["spy"][sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"]}
    chosen = {}
    for arm in ARMS[1:]:
        c = np.zeros(len(sectors))
        for w in weeks:
            for k in allow[arm][w]:
                c[k] += 1
        chosen[arm] = {sectors[k]: float(c[k] / len(weeks)) for k in range(len(sectors))}
    out["share_of_weeks_each_sector_was_chosen"] = chosen

    for sname, member in sets.items():
        pool_ok = member[:-1] & ~np.isnan(R_hold)
        pool_mean = np.array([float(R_hold[w][pool_ok[w]].mean()) if pool_ok[w].any() else 0.0 for w in range(nW - 1)])
        P13 = np.array([np.nanmean(np.where(member[w], F13[w], np.nan)) if member[w].any() else np.nan for w in range(nW)])
        res_set = {"arms": {}}
        for arm in ARMS:
            rng = np.random.default_rng(SEED)
            al = allow[arm]
            enter_at, exit_at, taken = {}, {}, []
            for e, x, j, why in trades:
                if e < w0 or e >= nW - 1 or not member[e, j] or np.isnan(R_in[e, j]):
                    continue
                if al is not None and sec_of[j] not in al[e]:
                    continue
                enter_at.setdefault(e, []).append(j)
                if x is not None and x < nW - 1:
                    exit_at.setdefault(x, []).append(j)
                taken.append((e, x, j))
            held, rets, counts = set(), [], []
            rand = np.zeros((draws, len(weeks)))
            for i, w in enumerate(weeks):
                gone = [j for j in exit_at.get(w, []) if j in held]
                for j in gone:
                    held.discard(j)
                keep = [j for j in held if not np.isnan(R_hold[w, j])]
                new = [j for j in enter_at.get(w, []) if j not in held]
                r = sum(R_hold[w, j] for j in keep)
                r += sum((0.0 if np.isnan(R_out[w, j]) else R_out[w, j]) - slip_of[tier[w, j]] for j in gone)
                r += sum(R_in[w, j] - slip_of[tier[w, j]] for j in new)
                k = len(keep) + len(gone) + len(new)
                rets.append(float(r) / k if k else 0.0)
                held = set(keep) | set(new)
                kk = len(held)
                counts.append(kk)
                pool = np.flatnonzero(pool_ok[w])
                if kk and len(pool) >= kk:
                    if kk * 3 > len(pool):
                        rand[:, i] = [R_hold[w][rng.choice(pool, kk, replace=False)].mean() for _ in range(draws)]
                    else:
                        pick_ = rng.random((draws, len(pool))).argpartition(kk - 1, axis=1)[:, :kk]
                        rand[:, i] = R_hold[w][pool][pick_].mean(axis=1)
            holds, gains = [], []
            for e, x, j in taken:
                if x is None or x >= nW - 1:
                    continue
                a_, b_ = Ow[e + 1, j], Ow[x + 1, j]
                if a_ == a_ and b_ == b_:
                    holds.append(x - e)
                    gains.append(float(b_ / a_ - 1.0))
            res = {"avg_names_held": float(np.mean(counts)), "weeks_in_cash": int(sum(1 for c in counts if c == 0)),
                   "entries_a_year": len(taken) / (len(weeks) / 52.0),
                   "median_hold_weeks": float(np.median(holds)) if holds else None,
                   "share_closed_at_a_gain": float(np.mean([g > 0 for g in gains])) if gains else None,
                   "mean_closed_gain": float(np.mean(gains)) if gains else None, "book": {}, "cards": {}}
            for sp, (a, b) in spans.items():
                ix = [i for i, d in enumerate(wk_dates) if a <= d < b]
                rr = [rets[i] for i in ix]
                st = p38.stats(rr, [spy[i] for i in ix], [wk_dates[i] for i in ix])
                pl = p38.stats([pool_mean[weeks[i]] for i in ix], [spy[i] for i in ix], [wk_dates[i] for i in ix])
                means = rand[:, ix].mean(axis=1)
                res["book"][sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"],
                                   "pool_cagr": pl["cagr"], "percentile_among_random": float((means < np.mean(rr)).mean() * 100.0)}
                by_week = {}
                for e, x, j in taken:
                    if a <= fridays[e] < b and F13[e, j] == F13[e, j] and P13[e] == P13[e]:
                        by_week.setdefault(e, []).append(F13[e, j] - P13[e])
                x13 = [v for vs in by_week.values() for v in vs]
                s13 = [float(np.mean(v)) for _, v in sorted(by_week.items())]
                m13, se13 = p42.nw_se(s13) if len(s13) > 20 else (None, None)
                res["cards"][sp] = {"cards": len(x13), "excess_13w": float(np.mean(x13)) if x13 else None,
                                    "t": (m13 / se13) if se13 else None}
            res_set["arms"][arm] = res
        out["sets"][sname] = res_set

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print("SPY: " + "; ".join(f"{sp} {P(v['cagr']).strip()} Sharpe {v['sharpe']:.2f} DD {P(v['max_drawdown']).strip()}" for sp, v in out["spy"].items()))
    for sname, rs in out["sets"].items():
        print(f"=== {sname}")
        print(f"{'arm':24} {'CAGR':>7} {'pool':>7} {'h1':>7} {'h2':>7} {'Sharpe':>6} {'maxDD':>7} {'pct':>4} {'h1':>4} {'h2':>4} | {'held':>5} {'cash':>5} {'in/yr':>6} {'hold':>5} {'won':>5} {'mean':>7} | {'13w':>7} {'t':>5} {'h1':>7} {'h2':>7}")
        for nm, r in rs["arms"].items():
            b, c = r["book"], r["cards"]
            t = c["all"]["t"]
            print(f"{nm:24} {P(b['all']['cagr'])} {P(b['all']['pool_cagr'])} {P(b['to 2016']['cagr'])} {P(b['2017 on']['cagr'])} {b['all']['sharpe']:6.2f} "
                  f"{P(b['all']['max_drawdown'])} {b['all']['percentile_among_random']:4.0f} {b['to 2016']['percentile_among_random']:4.0f} "
                  f"{b['2017 on']['percentile_among_random']:4.0f} | {r['avg_names_held']:5.0f} {r['weeks_in_cash']:5d} {r['entries_a_year']:6.0f} "
                  f"{r['median_hold_weeks'] or 0:5.0f} {P(r['share_closed_at_a_gain'], 0)[1:]} {P(r['mean_closed_gain'])} | "
                  f"{P(c['all']['excess_13w'], 2)} {'   --' if t is None else f'{t:5.1f}'} {P(c['to 2016']['excess_13w'], 2)} {P(c['2017 on']['excess_13w'], 2)}")
    for arm, sh in chosen.items():
        print(arm + ": " + ", ".join(f"{k[:14]} {100 * v:.0f}%" for k, v in sorted(sh.items(), key=lambda kv: -kv[1])))
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
