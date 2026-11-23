#!/usr/bin/env python3
"""Pass 65 -- defensive names where the trend book holds cash. Pass 61's
trend-strength book (ten slots, cap of three), and in a cold market the
ten steadiest large names in place of its idle cash, or in place of the
whole book. Controls: SPY for the idle cash, ten random large names.

Registered in lab/README.md (Pass 65) before any run.

    python lab/pass65_steady_names_when_cold.py          # full run
    python lab/pass65_steady_names_when_cold.py smoke    # plumbing: 300 names
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
CAP = 3
BASKET = 10
KEEP_WITHIN = 30
MIN_RISING = 5
DRAWS = 100
SEED = 20261165
OUT = lab.RESULTS / "pass65_steady_names_when_cold.json"
PERIODS = {"unseen: 1996-07 to 2006-10": ("1996-07", "2006-11-10"), "2006-11 to 2016-11": ("2006-11-10", "2016-11-11"),
           "2016-11 to 2026-11": ("2016-11-11", "9"), "everything": ("0", "9")}
SAME = {"Finance": "Financials", "Technology": "Information Technology", "Basic Materials": "Materials",
        "Telecommunications": "Communication Services", "": "Unlabelled", "Miscellaneous": "Unlabelled"}


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
    spy_o = frames["SPY"]["Open"].reindex(idx).to_numpy(dtype=float)
    spy_o = np.where(np.isnan(spy_o), spy_c, spy_o)
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names", flush=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        lC = np.log(Cw)
        R_hold = Cw[1:] / Cw[:-1] - 1.0
        R_in = Cw[1:] / Ow[1:] - 1.0
        R_out = Ow[1:] / Cw[:-1] - 1.0
        dv = Cw * Vw
        wr = np.diff(lC, axis=0)
    # column n is SPY, for the control that parks idle cash in it
    RH = np.column_stack([R_hold, spy_c[1:] / spy_c[:-1] - 1.0])
    RI = np.column_stack([R_in, spy_c[1:] / spy_o[1:] - 1.0])
    RO = np.column_stack([R_out, spy_o[1:] / spy_c[:-1] - 1.0])
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
    liquid = np.nan_to_num(med_dv) >= p43.DV_MIN
    tradeable = liquid & (np.nan_to_num(swing) >= p48.SWING_MIN)
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
    sector = [SAME.get(uni[t]["sector"], uni[t]["sector"]) for t in names] + ["SPY"]
    spy_ma40 = np.array([spy_c[max(0, w - 39):w + 1].mean() for w in range(nW)])
    cold = np.array([w >= 39 and spy_c[w] < spy_ma40[w] for w in range(nW)])

    print("drawing channels ...", flush=True)
    T = p52.quality_table(Cw, Hw, Lw)
    channel = ~np.isnan(T["lower"]) & (np.nan_to_num(T["slope"], nan=-1.0) >= p48.FLOOR) & (np.nan_to_num(T["r2"], nan=0.0) >= p48.R2_MIN)
    screen = member & channel & (np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX)
    w0 = 110
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    trend, steady_order, steady_ok, rising = {}, {}, {}, {}
    for w in weeks:
        js = np.flatnonzero(screen[w])
        if len(js) > 1:
            tr = sum(p52.ranks(np.nan_to_num(back[k][w, js], nan=-9.0)) for k in back) / 4.0
            js = js[np.argsort(-tr, kind="stable")]
        trend[w] = js
        ok = member_size[w] & liquid[w] & ~np.isnan(swing[w]) & ~np.isnan(R_hold[w]) & ~np.isnan(R_in[w])
        es = np.flatnonzero(ok)
        steady_order[w] = [int(j) for j in es[np.argsort(swing[w, es], kind="stable")]]
        steady_ok[w] = ok
        with np.errstate(invalid="ignore"):
            rising[w] = Cw[w] > ma40[w]
    spy = [float(spy_c[w + 1] / spy_c[w] - 1.0) for w in weeks]

    def next_basket(w, held, kind, rng):
        if kind == "spy":
            return [n]
        if kind == "random":
            keep = [j for j in held if steady_ok[w][j]]
            pool = [j for j in steady_order[w] if j not in keep]
            for k in rng.permutation(len(pool)):
                if len(keep) >= BASKET:
                    break
                keep.append(pool[k])
            return keep
        order = steady_order[w]
        good = (lambda j: bool(rising[w][j])) if kind == "rising" else (lambda j: True)
        low = set(order[:KEEP_WITHIN])
        keep = [j for j in held if j in low and good(j)]
        count = {}
        for j in keep:
            count[sector[j]] = count.get(sector[j], 0) + 1
        for j in order:
            if len(keep) >= BASKET:
                break
            if j in keep or not good(j) or count.get(sector[j], 0) >= CAP:
                continue
            keep.append(j)
            count[sector[j]] = count.get(sector[j], 0) + 1
        if kind == "rising" and len(keep) < MIN_RISING:
            return []
        return keep

    def nz(x):
        return 0.0 if x != x else float(x)

    def sim(kind=None, switch=False, rng=None, detail=False):
        N = SLOTS
        cash, pos, rets = 1.0, {}, []                  # pos: j -> [entry week, high close, value, cost]
        V, M = 0.0, []                                 # the cold-market basket: its value and its names
        holds, buys, inv, bsize, bturn = [], 0, [], [], 0
        for w in weeks:
            E = cash + sum(st[2] for st in pos.values()) + V
            gone = []
            for j, st in pos.items():
                c = Cw[w, j]
                if c != c or np.isnan(R_hold[w, j]):
                    gone.append(j)
                    continue
                st[1] = max(st[1], c)
                if c / st[1] - 1.0 <= -p57.OFF_HIGH:
                    gone.append(j)
            if switch and cold[w]:
                gone = list(pos)
            for j in gone:
                st = pos.pop(j)
                holds.append(w - st[0])
                cash += st[2] * (1.0 + nz(R_out[w, j])) * (1.0 - slip)
            for j, st in pos.items():
                st[2] *= 1.0 + R_hold[w, j]
            if kind and cold[w]:
                M2 = next_basket(w, M, kind, rng)
                per = V / len(M) if M else 0.0
                stay = [j for j in M if j in M2]
                out = [j for j in M if j not in M2]
                new = [j for j in M2 if j not in M]
                val = per * sum(1.0 + nz(RH[w, j]) for j in stay)
                pot = cash + per * sum((1.0 + nz(RO[w, j])) * (1.0 - slip) for j in out)
                tgt = new if new else M2
                if tgt and pot > 0:
                    val += pot * (1.0 - slip) * float(np.mean([1.0 + nz(RI[w, j]) for j in tgt]))
                    cash = 0.0
                else:
                    cash = pot
                bturn += len(new) + len(out)
                V, M = val, (M2 if val > 0 else [])
                bsize.append(len(M))
            elif V > 0:
                per = V / len(M)
                cash += per * sum((1.0 + nz(RO[w, j])) * (1.0 - slip) for j in M)
                bturn += len(M)
                V, M = 0.0, []
            free = N - len(pos)
            if free > 0 and not cold[w]:
                cs = [int(j) for j in trend[w] if j not in pos and j not in gone and not np.isnan(R_in[w, j])]
                count = {}
                for j in pos:
                    count[sector[j]] = count.get(sector[j], 0) + 1
                new = []
                for j in cs:
                    if len(new) >= free:
                        break
                    if count.get(sector[j], 0) >= CAP:
                        continue
                    new.append(j)
                    count[sector[j]] = count.get(sector[j], 0) + 1
                per = cash / free
                for j in new:
                    cash -= per
                    pos[j] = [w, float(max(hi52[w, j], Cw[w, j])), per * (1.0 - slip) * (1.0 + R_in[w, j]), per]
                buys += len(new)
            E1 = cash + sum(st[2] for st in pos.values()) + V
            rets.append(float(E1 / E - 1.0))
            inv.append(1.0 - cash / E1)
        if not detail:
            return rets
        yrs = len(weeks) / 52.0
        return rets, {"trend_buys_a_year": buys / yrs, "median_hold_weeks": float(np.median(holds)) if holds else None,
                      "avg_invested": float(np.mean(inv)), "basket_names_avg_in_cold_weeks": float(np.mean(bsize)) if bsize else None,
                      "basket_trades_a_year": bturn / yrs}

    def dd(x):
        c = np.cumprod(1.0 + np.asarray(x, dtype=float))
        return float((c / np.maximum.accumulate(c) - 1.0).min())

    def cg(x):
        x = np.asarray(x, dtype=float)
        return float(np.prod(1.0 + x) ** (52.0 / len(x)) - 1.0)

    per_ix = {k: [i for i, d in enumerate(wk_dates) if a <= d < b] for k, (a, b) in PERIODS.items()}
    cold_w = [w for w in weeks if cold[w]]
    st10 = [float(np.mean([R_hold[w, j] for j in steady_order[w][:BASKET]])) for w in cold_w if len(steady_order[w]) >= BASKET]
    sp10 = [float(spy_c[w + 1] / spy_c[w] - 1.0) for w in cold_w if len(steady_order[w]) >= BASKET]
    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "first_week": wk_dates[0],
           "share_of_weeks_cold": float(np.mean([cold[w] for w in weeks])),
           "share_of_weeks_cold_by_period": {k: float(np.mean([cold[weeks[i]] for i in ix])) for k, ix in per_ix.items()},
           "cold_weeks_only": {"weeks": len(st10), "steadiest_ten_mean_week": float(np.mean(st10)), "spy_mean_week": float(np.mean(sp10)),
                               "steadiest_ten_share_of_weeks_down": float(np.mean(np.array(st10) < 0)),
                               "spy_share_of_weeks_down": float(np.mean(np.array(sp10) < 0)),
                               "steadiest_ten_compounded": float(np.prod(1.0 + np.array(st10)) - 1.0),
                               "spy_compounded": float(np.prod(1.0 + np.array(sp10)) - 1.0)},
           "benchmarks": {"SPY": {k: p53.stat([spy[i] for i in ix], [wk_dates[i] for i in ix]) for k, ix in per_ix.items()}},
           "books": {}}
    draws = 8 if smoke else DRAWS
    rng = np.random.default_rng(SEED)
    rr = np.array([sim("random", rng=rng) for _ in range(draws)])
    out["random_names_control"] = {"draws": draws, "median_cagr": {k: float(np.median([cg(row[ix]) for row in rr])) for k, ix in per_ix.items()},
                                   "median_drawdown_everything": float(np.median([dd(row) for row in rr])),
                                   "median_sharpe_everything": float(np.median([p53.stat(list(row), wk_dates)["sharpe"] for row in rr]))}
    print("random-names control done", flush=True)
    cells = [("1 base: cash when idle", None, False), ("2 steady names for idle cash", "steady", False),
             ("3 steady and rising for idle cash", "rising", False), ("4 full switch to the steady ten", "steady", True),
             ("control: SPY for idle cash", "spy", False)]
    for name, kind, switch in cells:
        rets, info = sim(kind, switch, detail=True)
        info["periods"] = {}
        for k, ix in per_ix.items():
            st = p53.stat([rets[i] for i in ix], [wk_dates[i] for i in ix])
            st["percentile_among_random_names_control"] = float((rr[:, ix].mean(axis=1) < np.mean([rets[i] for i in ix])).mean() * 100.0)
            info["periods"][k] = st
        info["by_year_cold_heavy"] = {y: float(np.prod([1.0 + rets[i] for i, d in enumerate(wk_dates) if d[:4] == y]) - 1.0)
                                      for y in ("2000", "2001", "2002", "2008", "2009", "2020", "2022")}
        out["books"][name] = info
        print("done:", name, flush=True)

    def P(x, d_=1):
        return "    --" if x is None else f"{100 * x:6.{d_}f}%"
    c_ = out["cold_weeks_only"]
    print(f"cold weeks: {P(out['share_of_weeks_cold'], 0).strip()} of all; by period " + ", ".join(f"{P(v, 0).strip()}" for v in out["share_of_weeks_cold_by_period"].values()))
    print(f"in {c_['weeks']} cold weeks: steadiest ten mean {P(c_['steadiest_ten_mean_week'], 2).strip()}/wk, down {P(c_['steadiest_ten_share_of_weeks_down'], 0).strip()} of weeks, "
          f"compounded {P(c_['steadiest_ten_compounded'], 0).strip()}; SPY mean {P(c_['spy_mean_week'], 2).strip()}/wk, down {P(c_['spy_share_of_weeks_down'], 0).strip()}, compounded {P(c_['spy_compounded'], 0).strip()}")
    for k in PERIODS:
        s_ = out["benchmarks"]["SPY"][k]
        print(f"== {k}: SPY {P(s_['cagr'])} Sharpe {s_['sharpe']:.2f} DD {P(s_['max_drawdown'])};  random-names control median {P(out['random_names_control']['median_cagr'][k])}")
        for nm, r in out["books"].items():
            b_ = r["periods"][k]
            print(f"     {nm:36} {P(b_['cagr'])} Sharpe {b_['sharpe']:.2f} DD {P(b_['max_drawdown'])} pct of random-names {b_['percentile_among_random_names_control']:4.0f}")
    print(f"random-names control, everything: median drawdown {P(out['random_names_control']['median_drawdown_everything']).strip()}, median Sharpe {out['random_names_control']['median_sharpe_everything']:.2f}")
    for nm, r in out["books"].items():
        print(f"{nm:36} invested {P(r['avg_invested'], 0).strip()}, trend buys/yr {r['trend_buys_a_year']:.1f}, basket names {r['basket_names_avg_in_cold_weeks']}, basket trades/yr {r['basket_trades_a_year']:.1f}; "
              + " ".join(f"{y} {P(v, 0).strip()}" for y, v in r["by_year_cold_heavy"].items()))
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main(sys.argv)
