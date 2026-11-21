#!/usr/bin/env python3
"""Pass 52 -- ten good channels: a quality score, weights by quality, cash
by market temperature.

Ranks the names on Pass 48's screen by a four-part channel quality score
(straight, tight, long, tested), holds the best N until their own exit,
and compares with books that fill the same slots at random from the
screen.

Registered in lab/README.md (Pass 52) before any run.

    python lab/pass52_ten_good_channels.py          # full run
    python lab/pass52_ten_good_channels.py smoke    # plumbing: 300 names
"""
from __future__ import annotations

import itertools
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
import pass41_owner_channel as p41  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402
import pass48_screen_book as p48  # noqa: E402

OFF_HIGH = 0.20
TOUCH_BAND = 0.10
TOUCH_GAP = 4
COLD_WEEKS = 40
DRAWS = 200
SEED = 20261152
HALF = p38.HALF
OUT = lab.RESULTS / "pass52_ten_good_channels.json"
SPANS = {"all": ("0", "9"), "to 2016": ("0", HALF), "2017 on": (HALF, "9"), "2010 on": ("2010", "9")}


def draw(lc, lh, ll):
    """Pass 41's channel with the two extra facts the score needs: its age
    and how many separate times a low came into the bottom tenth."""
    ch = p41.draw(lc, lh, ll)
    if not ch:
        return None
    age = ch["age"]
    a = len(lc) - 1 - age
    line = ll[a] + ch["slope"] * np.arange(0, age + 1)
    near = (ll[a:] - line) <= TOUCH_BAND * ch["height"]
    touches, last = 0, 0
    for k in range(1, age + 1):
        if near[k] and k - last >= TOUCH_GAP:
            touches += 1
            last = k
    ch["touches"] = touches
    return ch


def quality_table(Cw, Hw, Lw):
    nW, n = Cw.shape
    T = {k: np.full((nW, n), np.nan) for k in ("lower", "slope", "r2", "height", "age", "touches")}
    with np.errstate(invalid="ignore", divide="ignore"):
        lC, lH, lL = np.log(Cw), np.log(Hw), np.log(Lw)
    bad = np.isnan(lC) | np.isnan(lH) | np.isnan(lL)
    run = np.zeros((nW, n), dtype=int)
    for w in range(nW):
        run[w] = np.where(bad[w], 0, (run[w - 1] if w else 0) + 1)
    for j in range(n):
        for w in range(p41.MIN_AGE, nW):
            m = min(p41.LOOKBACK, int(run[w, j]))
            if m <= p41.MIN_AGE:
                continue
            ch = draw(lC[w - m + 1:w + 1, j], lH[w - m + 1:w + 1, j], lL[w - m + 1:w + 1, j])
            if ch:
                for k in T:
                    T[k][w, j] = ch[k]
    return T


def ranks(x):
    """0 worst .. 1 best among the values given (ties share the mean rank)."""
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return np.full(len(x), 0.5)
    order = x.argsort(kind="stable")
    r = np.empty(len(x))
    r[order] = np.arange(len(x))
    for v in np.unique(x):
        m = x == v
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r / (len(x) - 1)


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
    member = tradeable & (tier >= 0) & (tier <= 1)

    print("drawing channels ...", flush=True)
    T = quality_table(Cw, Hw, Lw)
    lower, slope = T["lower"], T["slope"]
    channel = ~np.isnan(lower) & (np.nan_to_num(slope, nan=-1.0) >= p48.FLOOR) & (np.nan_to_num(T["r2"], nan=0.0) >= p48.R2_MIN)
    near_high = np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX
    screen = member & channel & near_high

    w0 = 110
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    # the score, and each week's screen names best first
    Q = np.full((nW, n), np.nan)
    parts = {k: np.full((nW, n), np.nan) for k in ("straight", "tight", "long", "tested")}
    cands = {}
    for w in range(w0, nW):
        js = np.flatnonzero(screen[w])
        if not len(js):
            cands[w] = js
            continue
        with np.errstate(invalid="ignore", divide="ignore"):
            tight = T["height"][w, js] / (slope[w, js] * T["age"][w, js])
        pr = {"straight": ranks(T["r2"][w, js]), "tight": ranks(-tight), "long": ranks(T["age"][w, js]), "tested": ranks(T["touches"][w, js])}
        for k, v in pr.items():
            parts[k][w, js] = v
        q = sum(pr.values()) / 4.0
        Q[w, js] = q
        cands[w] = js[np.argsort(-q, kind="stable")]

    sdf = lab.download(sorted(p32.members()) + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)["Close"]["SPY"].dropna()
    spy_w = sdf.groupby([sdf.index.isocalendar().year, sdf.index.isocalendar().week]).last()
    keys = [(int(y), int(k)) for y, k in spy_w.index]
    spy_ret = dict(zip(keys[1:], spy_w.pct_change().to_numpy()[1:]))
    spy = [float(spy_ret.get(tuple(date.fromisoformat(d).isocalendar()[:2]), 0.0)) for d in wk_dates]
    lvl = spy_w.to_numpy(dtype=float)
    cold_key = {keys[i]: bool(lvl[i] < lvl[i - COLD_WEEKS + 1:i + 1].mean()) for i in range(COLD_WEEKS - 1, len(keys))}
    cold = np.array([cold_key.get(tuple(date.fromisoformat(fridays[w]).isocalendar()[:2]), False) for w in range(nW)])
    span_ix = {sp: [i for i, d in enumerate(wk_dates) if a <= d < b] for sp, (a, b) in SPANS.items()}
    span_ix = {sp: ix for sp, ix in span_ix.items() if len(ix) >= 3}
    slip = float(slip_of[1])

    def sim(N, exit_, market, weights, pick, rng=None, detail=False):
        held, prev_w = {}, {}          # j -> [entry week, line, slope, high close, score]
        rets, counts, inv, holds, gains, falls = [], [], [], [], [], []
        entry_px = {}
        for w in weeks:
            keep, gone = [], []
            for j, st in held.items():
                e, a_, b_, hi, _ = st
                if np.isnan(R_hold[w, j]) or np.isnan(lC[w, j]):
                    gone.append(j)
                    continue
                st[3] = hi = max(hi, Cw[w, j])
                sell = (lC[w, j] < a_ + b_ * (w - e)) if exit_ == "line" else (Cw[w, j] / hi - 1.0 <= -OFF_HIGH)
                (gone if sell else keep).append(j)
            r = 0.0
            for j in gone:
                st = held.pop(j)
                r += prev_w.get(j, 0.0) * (0.0 if np.isnan(R_out[w, j]) else R_out[w, j])
                if detail:
                    px = Ow[w + 1, j] if not np.isnan(Ow[w + 1, j]) else Cw[w, j]
                    holds.append(w - st[0])
                    gains.append(float(px / entry_px.pop(j) - 1.0))
                    falls.append(float(px / st[3] - 1.0))
            free = N - len(keep)
            new = []
            if free > 0 and not (market == "cold" and cold[w]):
                pool = [int(j) for j in cands[w] if j not in held and j not in gone and not np.isnan(R_in[w, j])]
                if pick == "top":
                    new = pool[:free]
                elif pick == "bottom":
                    new = pool[::-1][:free]
                elif pool:
                    new = [pool[i] for i in rng.permutation(len(pool))[:free]]
            for j in new:
                held[j] = [w, float(lower[w, j]), float(slope[w, j]), float(max(hi52[w, j], Cw[w, j])), float(Q[w, j])]
                if detail:
                    entry_px[j] = float(Ow[w + 1, j])
            m = len(held)
            if weights == "quality" and m > 1:
                order = sorted(held, key=lambda j: -held[j][4])
                wts = {j: (1.5 - k / (m - 1.0)) / N for k, j in enumerate(order)}
            else:
                wts = {j: 1.0 / N for j in held}
            for j, wt in wts.items():
                r += wt * (R_in[w, j] if j in new else R_hold[w, j])
            cost = sum(abs(wts.get(j, 0.0) - prev_w.get(j, 0.0)) * slip for j in set(wts) | set(prev_w)
                       if (j in new or j in gone or abs(wts.get(j, 0.0) - prev_w.get(j, 0.0)) > 0.25 * max(wts.get(j, 0.0), prev_w.get(j, 0.0))))
            rets.append(float(r - cost))
            counts.append(m)
            inv.append(sum(wts.values()))
            prev_w = wts
        if not detail:
            return rets
        return rets, {"avg_names_held": float(np.mean(counts)), "avg_invested": float(np.mean(inv)),
                      "weeks_all_cash": int(sum(1 for c in counts if c == 0)),
                      "sales_a_year": len(holds) / (len(weeks) / 52.0),
                      "median_hold_weeks": float(np.median(holds)) if holds else None,
                      "longest_hold_weeks": int(max(holds)) if holds else None,
                      "share_closed_at_a_gain": float(np.mean([g > 0 for g in gains])) if gains else None,
                      "mean_closed_gain": float(np.mean(gains)) if gains else None,
                      "sale_under_high_median": float(np.median(falls)) if falls else None,
                      "sale_under_high_worst": float(min(falls)) if falls else None}

    def book_stats(rets):
        o = {}
        for sp, ix in span_ix.items():
            st = p38.stats([rets[i] for i in ix], [spy[i] for i in ix], [wk_dates[i] for i in ix])
            o[sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"], "mean_week": st["mean_week"],
                     "excess_over_spy_t": st["excess_t"]}
        return o

    draws = 10 if smoke else DRAWS
    slots = (max(3, int(10 * scale * 3)), max(5, int(25 * scale * 3))) if smoke else (10, 25)
    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "first_week": wk_dates[0], "spy": book_stats(spy),
           "median_names_on_screen": float(np.median([len(cands[w]) for w in weeks])),
           "cold_weeks_share": float(np.mean([cold[w] for w in weeks])), "books": {}}
    for N, exit_, market in itertools.product(slots, ("line", "20% off the high"), ("none", "cold")):
        rand = None
        for weights in ("equal", "quality"):
            name = f"{N} slots | {exit_} | market {market} | weights {weights}"
            rets, info = sim(N, exit_, market, weights, "top", detail=True)
            info["book"] = book_stats(rets)
            if weights == "equal":
                rng = np.random.default_rng(SEED)
                rand = np.array([sim(N, exit_, market, "equal", "random", rng=rng) for _ in range(draws)])
                for sp, ix in span_ix.items():
                    means = rand[:, ix].mean(axis=1)
                    rc = np.cumprod(1.0 + rand[:, ix], axis=1)[:, -1] ** (52.0 / len(ix)) - 1.0
                    info["book"][sp]["percentile_among_random_screen_books"] = float((means < info["book"][sp]["mean_week"]).mean() * 100.0)
                    info["book"][sp]["random_median_cagr"] = float(np.median(rc))
            by_year = {}
            for d, a_, c_ in zip(wk_dates, rets, spy):
                y = by_year.setdefault(d[:4], [1.0, 1.0])
                y[0] *= 1 + a_
                y[1] *= 1 + c_
            info["by_year"] = {y: {"arm": v[0] - 1, "spy": v[1] - 1} for y, v in by_year.items()}
            out["books"][name] = info
            print("done:", name, flush=True)
    for exit_ in ("line", "20% off the high"):
        name = f"{slots[0]} slots | {exit_} | market none | weights equal | LOWEST scores"
        rets, info = sim(slots[0], exit_, "none", "equal", "bottom", detail=True)
        info["book"] = book_stats(rets)
        out["books"][name] = info

    # where the owner's marks fall on the score, last week of the bars (a check, not a verdict)
    marks_path = Path(__file__).resolve().parent / "owner_marks.json"
    with open(marks_path, encoding="utf-8") as fh:
        marks = json.load(fh)["marks"]
    wl = nW - 1
    pos = {t: j for j, t in enumerate(names)}
    chk = {}
    for m in marks:
        t, call = m.get("ticker"), m.get("call")
        if call not in ("ideal", "potential", "broken") or t in chk:
            continue
        j = pos.get(t)
        row = {"call": call, "in_bars": j is not None}
        if j is not None:
            row.update({"has_channel": bool(channel[wl, j]), "on_screen_ignoring_size": bool(tradeable[wl, j] and channel[wl, j] and near_high[wl, j])})
        chk[t] = row
    # score every tradeable channel name that week, whatever its size, so the marks can be placed
    js = np.flatnonzero(tradeable[wl] & channel[wl] & near_high[wl])
    if len(js) > 1:
        with np.errstate(invalid="ignore", divide="ignore"):
            tight = T["height"][wl, js] / (slope[wl, js] * T["age"][wl, js])
        q = (ranks(T["r2"][wl, js]) + ranks(-tight) + ranks(T["age"][wl, js]) + ranks(T["touches"][wl, js])) / 4.0
        qr = dict(zip([names[j] for j in js], ranks(q)))
        for t, row in chk.items():
            if t in qr:
                row["score_rank_among_all_screen_names"] = float(qr[t])
    out["owner_marks_check"] = {"week": fridays[wl], "names_scored": int(len(js)), "marks": chk}

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print(f"median names on screen {out['median_names_on_screen']:.0f}; cold weeks {P(out['cold_weeks_share'], 0).strip()}")
    print("SPY: " + "; ".join(f"{sp} {P(v['cagr']).strip()} Sharpe {v['sharpe']:.2f} DD {P(v['max_drawdown']).strip()}" for sp, v in out["spy"].items()))
    for nm, r in out["books"].items():
        print(f"-- {nm}: held {r['avg_names_held']:.1f}, invested {P(r['avg_invested'], 0).strip()}, all-cash weeks {r['weeks_all_cash']}, sales/yr {r['sales_a_year']:.1f}, "
              f"hold median {r['median_hold_weeks'] or 0:.0f}w longest {r['longest_hold_weeks'] or 0}w, won {P(r['share_closed_at_a_gain'], 0).strip()}, mean {P(r['mean_closed_gain']).strip()}, "
              f"sale under high median {P(r['sale_under_high_median']).strip()} worst {P(r['sale_under_high_worst']).strip()}")
        for sp, b in r["book"].items():
            extra = (f" pct {b['percentile_among_random_screen_books']:4.0f} random {P(b['random_median_cagr'])}" if "random_median_cagr" in b else "")
            print(f"     {sp:8} CAGR {P(b['cagr'])} Sharpe {b['sharpe'] if b['sharpe'] is None else round(b['sharpe'], 2)} DD {P(b['max_drawdown'])}{extra}")
        if "by_year" in r:
            print("     by year arm/spy: " + "  ".join(f"{y} {100 * v['arm']:+.0f}/{100 * v['spy']:+.0f}" for y, v in r["by_year"].items()))
    groups = {}
    for t, row in out["owner_marks_check"]["marks"].items():
        g = groups.setdefault("solid" if row["call"] in ("ideal", "potential") else "broken", [])
        g.append((t, row))
    for g, rows in groups.items():
        sc = [r["score_rank_among_all_screen_names"] for _, r in rows if "score_rank_among_all_screen_names" in r]
        print(f"owner marks, {g}: {len(rows)} marked, {sum(1 for _, r in rows if r['in_bars'])} in bars, "
              f"{sum(1 for _, r in rows if r.get('has_channel'))} with a channel, {len(sc)} on the screen; "
              f"score rank median {np.median(sc) if sc else float('nan'):.2f}")
    for t in ("UVE", "GRDN"):
        print(f"  {t}: {out['owner_marks_check']['marks'].get(t)}")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main(sys.argv)
