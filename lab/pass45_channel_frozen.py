#!/usr/bin/env python3
"""Pass 45 -- the channel rule, frozen, on twenty years of weekly bars.

The owner's channel as his marks of 2026-11-20 shaped it: anchored at the low
that started the move (look-backs of 1 to 4 years, never before the last
break), 13 weeks or more old, closes fairly straight, not more than 4.7 weekly
swings under the 52-week high, and sold only on a weekly close below the
lower line fixed at entry.

Registered in lab/README.md (Pass 45) before any run.

    python lab/pass45_channel_frozen.py          # every arm
    python lab/pass45_channel_frozen.py smoke    # plumbing: 300 names
"""
from __future__ import annotations

import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402
import pass42_who_breaks_first as p42  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402

LOOKBACKS = (52, 104, 156, 208)
EDGE = 4
MIN_AGE = 13
R2_MIN = 0.70
SWINGS_MAX = 4.7
SWING_MIN = 0.015
FLOOR = math.log(1.10) / 52.0
DRAWS = 200
SEED = 20261125
HALF = p38.HALF
OUT = lab.RESULTS / "pass45_channel_frozen.json"

#        name               pullback min_age slots
ARMS = [("basket",          True,    13,     None),
        ("no pullback rule", False,  13,     None),
        ("older only",      True,    26,     None),
        ("ten straightest", True,    13,     10)]


def draw(lc, lh, ll, w, start, min_age):
    """The channel at week w, anchored no earlier than `start`. Tries each
    look-back in turn; the anchor must be a swing low (not in the window's
    first EDGE weeks) unless the window begins at `start` itself."""
    for L in LOOKBACKS:
        a0 = max(w - L + 1, start)
        if w - a0 < min_age:
            return None
        seg = ll[a0:w + 1]
        if np.isnan(seg).any():
            # shorten to the clean tail
            bad = np.flatnonzero(np.isnan(seg))
            a0 = a0 + int(bad[-1]) + 1
            if w - a0 < min_age:
                return None
            seg = ll[a0:w + 1]
        a = a0 + int(np.argmin(seg))
        age = w - a
        if a - a0 < EDGE and a0 > start and L != LOOKBACKS[-1]:
            continue                                    # the low is the window's edge: look further back
        if age < min_age:
            return None                                 # the low is too recent: no channel yet
        t = np.arange(1, age + 1)
        b = float(((ll[a + 1:w + 1] - ll[a]) / t).min())
        if b < FLOOR:
            return None
        y = lc[a:w + 1]
        if np.isnan(y).any():
            return None
        x = np.arange(len(y)) - (len(y) - 1) / 2.0
        d = y - y.mean()
        sst = float((d * d).sum())
        if sst <= 0:
            return None
        k = float((x * d).sum() / (x * x).sum())
        r2 = 1.0 - float(((d - k * x) ** 2).sum()) / sst
        return ll[a] + b * age, b, r2, age
    return None


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
        lC, lH, lL = np.log(Cw), np.log(Hw), np.log(Lw)
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
        swings_off = (lC - np.log(hi52)) / swing                    # 0 at the high, negative below it
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

    w0 = 66
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    pool_ok = tradeable[:-1] & ~np.isnan(R_hold)
    pool_mean = np.array([float(R_hold[w][pool_ok[w]].mean()) if pool_ok[w].any() else 0.0 for w in range(nW - 1)])
    spy_like = [pool_mean[w] for w in weeks]                        # the tradeable pool, equal weight

    def fwd(k):
        f = np.full((nW, n), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            f[:nW - k - 1] = Cw[k + 1:] / Ow[1:nW - k] - 1.0        # from the entry open (week w+1) to k weeks on
        return f
    F13, F26 = fwd(13), fwd(26)
    P13 = np.array([np.nanmean(np.where(tradeable[w], F13[w], np.nan)) if tradeable[w].any() else np.nan for w in range(nW)])
    P26 = np.array([np.nanmean(np.where(tradeable[w], F26[w], np.nan)) if tradeable[w].any() else np.nan for w in range(nW)])

    draws = 20 if smoke else DRAWS
    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "first_week": wk_dates[0], "last_week": wk_dates[-1],
           "arms": {}}
    spans = {"all": ("0", "9"), "to 2016": ("0", HALF), "2017 on": (HALF, "9")}

    for name, pullback, min_age, slots in ARMS:
        rng = np.random.default_rng(SEED)
        pre = tradeable.copy()
        if pullback:
            pre &= np.nan_to_num(swings_off, nan=-99.0) >= -SWINGS_MAX
        not_before = np.zeros(n, dtype=int)
        held = {}                                                   # j -> (line at entry, slope, entry week, entry open, tier)
        rets, counts, cards, holds = [], [], [], []
        rand = np.zeros((draws, len(weeks)))
        for i, w in enumerate(weeks):
            keep, gone = [], []
            for j, (a_, b_, e_, _, _) in held.items():
                if not np.isnan(lC[w, j]) and not np.isnan(R_hold[w, j]) and lC[w, j] >= a_ + b_ * (w - e_):
                    keep.append(j)
                else:
                    gone.append(j)
            cand = []
            if slots is None or len(keep) < slots:
                for j in np.flatnonzero(pre[w] & ~np.isnan(R_in[w])):
                    if j in held:
                        continue
                    ch = draw(lC[:, j], lH[:, j], lL[:, j], w, int(not_before[j]), min_age)
                    if ch and ch[2] >= R2_MIN:
                        cand.append((ch[2], int(j), ch))
                if slots is not None:
                    cand.sort(key=lambda c: (-c[0], names[c[1]]))
                    cand = cand[:slots - len(keep)]
            r = sum(R_hold[w, j] for j in keep)
            for j in gone:
                a_, b_, e_, px, tr = held.pop(j)
                ro = 0.0 if np.isnan(R_out[w, j]) else R_out[w, j]
                r += ro - slip_of[tr]
                x_px = Ow[w + 1, j] if not np.isnan(Ow[w + 1, j]) else Cw[w, j]
                holds.append((w - e_, float(x_px / px - 1.0)))
                not_before[j] = w
            for _, j, ch in cand:
                tr = int(tier[w, j])
                r += R_in[w, j] - slip_of[tr]
                held[j] = (float(ch[0]), float(ch[1]), w, float(Ow[w + 1, j]), tr)
                cards.append((w, tr, F13[w, j] - P13[w], F26[w, j] - P26[w]))
            k = len(keep) + len(gone) + len(cand)
            rets.append(float(r) / k if k else 0.0)
            kk = len(held)
            counts.append(kk)
            pool = np.flatnonzero(pool_ok[w])
            if kk and len(pool) >= kk:
                if kk * 3 > len(pool):
                    rand[:, i] = [R_hold[w][rng.choice(pool, kk, replace=False)].mean() for _ in range(draws)]
                else:
                    pick = rng.random((draws, len(pool))).argpartition(kk - 1, axis=1)[:, :kk]
                    rand[:, i] = R_hold[w][pool][pick].mean(axis=1)
            if i % 200 == 0:
                print(f"  {name}: week {i}/{len(weeks)}, held {kk}", flush=True)
        res = {"avg_names_held": float(np.mean(counts)), "weeks_in_cash": int(sum(1 for c in counts if c == 0)),
               "entries": len(cards), "closed": len(holds),
               "median_hold_weeks": float(np.median([h[0] for h in holds])) if holds else None,
               "share_closed_at_a_gain": float(np.mean([h[1] > 0 for h in holds])) if holds else None,
               "mean_closed_gain": float(np.mean([h[1] for h in holds])) if holds else None,
               "median_closed_gain": float(np.median([h[1] for h in holds])) if holds else None, "book": {}, "cards": {}}
        for span, (a, b) in spans.items():
            ix = [i for i, d in enumerate(wk_dates) if a <= d < b]
            rr = [rets[i] for i in ix]
            st = p38.stats(rr, [spy_like[i] for i in ix], [wk_dates[i] for i in ix])
            pl = p38.stats([spy_like[i] for i in ix], [spy_like[i] for i in ix], [wk_dates[i] for i in ix])
            means = rand[:, ix].mean(axis=1)
            res["book"][span] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"],
                                 "pool_cagr": pl["cagr"], "pool_sharpe": pl["sharpe"], "pool_max_drawdown": pl["max_drawdown"],
                                 "percentile_among_random": float((means < np.mean(rr)).mean() * 100.0),
                                 "arm_mean_week": float(np.mean(rr)), "random_mean_week": float(means.mean())}
            for tname, tk in [("every tier", None)] + [(t[0], k) for k, t in enumerate(p43.TIERS)]:
                cs = [c for c in cards if a <= fridays[c[0]] < b and (tk is None or c[1] == tk)]
                by_week = {}
                for c in cs:
                    by_week.setdefault(c[0], []).append(c)
                s13 = [np.nanmean([c[2] for c in v]) for _, v in sorted(by_week.items())]
                s13 = [x for x in s13 if x == x]
                m13, se13 = p42.nw_se(s13) if len(s13) > 20 else (None, None)
                x13 = [c[2] for c in cs if c[2] == c[2]]
                x26 = [c[3] for c in cs if c[3] == c[3]]
                res["cards"].setdefault(span, {})[tname] = {
                    "cards": len(cs), "excess_13w": float(np.mean(x13)) if x13 else None,
                    "excess_26w": float(np.mean(x26)) if x26 else None,
                    "share_beating_pool_13w": float(np.mean([v > 0 for v in x13])) if x13 else None,
                    "weekly_mean_excess_13w": m13, "t": (m13 / se13) if se13 else None}
        out["arms"][name] = res

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    for span in spans:
        print(f"--- {span}")
        print(f"{'arm':17} {'CAGR':>7} {'pool':>7} {'Sharpe':>6} {'pool':>5} {'maxDD':>7} {'pool':>7} {'pct':>5} | {'cards':>6} {'13w':>7} {'t':>6} {'26w':>7} {'beat':>6}")
        for nm, r in out["arms"].items():
            b, c = r["book"][span], r["cards"][span]["every tier"]
            t = c["t"]
            print(f"{nm:17} {P(b['cagr'])} {P(b['pool_cagr'])} {b['sharpe']:6.2f} {b['pool_sharpe']:5.2f} {P(b['max_drawdown'])} "
                  f"{P(b['pool_max_drawdown'])} {b['percentile_among_random']:5.0f} | {c['cards']:6d} {P(c['excess_13w'], 2)} "
                  f"{'    --' if t is None else f'{t:6.2f}'} {P(c['excess_26w'], 2)} {P(c['share_beating_pool_13w'], 0)}")
    for nm, r in out["arms"].items():
        print(f"{nm:17} held {r['avg_names_held']:.0f}, cash weeks {r['weeks_in_cash']}, entries {r['entries']}, median hold {r['median_hold_weeks']}, "
              f"won {P(r['share_closed_at_a_gain'], 0)}, mean gain {P(r['mean_closed_gain'])}, median gain {P(r['median_closed_gain'])}")
    b = out["arms"]["basket"]["cards"]
    for span in spans:
        print(f"basket cards by tier, {span}: " + "; ".join(
            f"{t} n {v['cards']} 13w {P(v['excess_13w'], 2).strip()} (t {'--' if v['t'] is None else round(v['t'], 1)})"
            for t, v in b[span].items() if t != "every tier"))
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
