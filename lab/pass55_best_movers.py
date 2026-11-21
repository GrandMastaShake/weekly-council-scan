#!/usr/bin/env python3
"""Pass 55 -- the best movers of the last ten years, and what marked them
beforehand. A description: every trait is counted on all names, and again
on the decade before.

Registered in lab/README.md (Pass 55) before any run.

    python lab/pass55_best_movers.py          # full run
    python lab/pass55_best_movers.py smoke    # plumbing: 300 names
    python lab/pass55_best_movers.py nofloor  # the amendment: no $3 floor on adjusted prices
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
import pass41_owner_channel as p41  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402
import pass48_screen_book as p48  # noqa: E402
import pass52_ten_good_channels as p52  # noqa: E402
import pass53_other_history as p53  # noqa: E402

p41.MIN_AGE = 8                       # a channel counts after 8 weeks (Pass 54)
TOP_SHARE = 0.05
OFF_HIGH = 0.20
RUN = 104
DECADES = {"2016-26": ("2016-11-11", "9"), "2006-16": ("2006-11-10", "2016-11-11")}
OUT = lab.RESULTS / "pass55_best_movers.json"
TIER_NAMES = [t[0] for t in p43.TIERS]


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    nofloor = "nofloor" in argv            # amendment of 2026-11-21: no $3 floor on adjusted prices
    price_min = 0.0 if nofloor else p43.PRICE_MIN
    out_path = OUT.with_name("pass55_best_movers_nofloor.json") if nofloor else OUT
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
    idx = pd.DatetimeIndex([d for d in frames["SPY"].index if d.weekday() == 0 and d >= pd.Timestamp("2004-01-01")])

    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    spy_c = frames["SPY"]["Close"].reindex(idx).ffill().to_numpy(dtype=float)
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names", flush=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        lC = np.log(Cw)
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
        off_high = Cw / hi52 - 1.0
    liquid = (Cw >= price_min) & (np.nan_to_num(med_dv) >= p43.DV_MIN)
    tradeable = liquid & (np.nan_to_num(swing) >= p48.SWING_MIN)
    cap_now = np.array([float(uni[t]["cap_m"]) for t in names])
    # the list is two sources with two sets of sector names: one name each
    same = {"Finance": "Financials", "Technology": "Information Technology", "Basic Materials": "Materials",
            "Telecommunications": "Communication Services", "": "Unlabelled", "Miscellaneous": "Unlabelled"}
    sector = [same.get(uni[t]["sector"], uni[t]["sector"]) for t in names]
    ref_px = np.full(n, np.nan)
    for j, t in enumerate(names):
        good = np.flatnonzero(~np.isnan(Cw[:, j]))
        if len(good):
            upto = [w for w in good if fridays[w] <= uni[t]["cap_date"]]
            ref_px[j] = Cw[upto[-1] if upto else good[0], j]
    with np.errstate(invalid="ignore", divide="ignore"):
        size = cap_now[None, :] * Cw / ref_px[None, :]
    scale = n / 3000.0 if smoke else 1.0
    tier = np.full((nW, n), -1, dtype=int)
    for w in range(nW):
        ok = np.flatnonzero(~np.isnan(size[w]))
        order = ok[np.argsort(-size[w, ok])]
        for k, (_, lo, hi, _) in enumerate(p43.TIERS):
            tier[w, order[int(lo * scale):int(min(hi * scale, len(order)))]] = k
    print("drawing channels ...", flush=True)
    T = p52.quality_table(Cw, Hw, Lw)
    channel = ~np.isnan(T["lower"]) & (np.nan_to_num(T["slope"], nan=-1.0) >= p48.FLOOR) & (np.nan_to_num(T["r2"], nan=0.0) >= p48.R2_MIN)
    near_high = np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX
    screen = tradeable & channel & near_high

    def wk(date):
        return max(i for i, d in enumerate(fridays) if d <= date)

    def path(j, S, E):
        """One name over (S, E]: shake-outs, drawdown, screen time, and what
        buying on the screen and selling 20% under the high would have kept."""
        hi = peak = Cw[S, j]
        shakes, maxdd = 0, 0.0
        for w in range(S + 1, E + 1):
            c = Cw[w, j]
            if c != c:
                continue
            hi, peak = max(hi, c), max(peak, c)
            maxdd = min(maxdd, c / peak - 1.0)
            if c <= (1.0 - OFF_HIGH) * hi:
                shakes += 1
                hi = c
        held, g, first, trades, weeks_in, h = False, 1.0, None, 0, 0, 0.0
        for w in range(S, E):
            c, c1, o1 = Cw[w, j], Cw[w + 1, j], Ow[w + 1, j]
            if c != c or c1 != c1 or o1 != o1:
                continue
            if held:
                h = max(h, c)
                if c <= (1.0 - OFF_HIGH) * h:
                    g *= o1 / c
                    held = False
                    trades += 1
                else:
                    g *= c1 / c
                    weeks_in += 1
            elif screen[w, j]:
                held, h = True, max(hi52[w, j], c)
                g *= c1 / o1
                weeks_in += 1
                if first is None:
                    first = w
        return {"shakeouts": shakes, "max_drawdown": float(maxdd), "screen_share": float(screen[S:E + 1, j].mean()),
                "rule_growth": float(g), "rule_sales": trades, "rule_weeks_in": weeks_in / max(1, E - S), "first_buy": first}

    def lift_numeric(x, pop, win):
        v = x[pop]
        ok = ~np.isnan(v)
        if ok.sum() < 20:
            return None
        edges = np.quantile(v[ok], [0.2, 0.4, 0.6, 0.8])
        q_pop = np.digitize(x[pop][ok], edges)
        is_win = np.isin(pop[ok], win)
        base = is_win.mean()
        return {"winners_median": float(np.nanmedian(x[win])), "rest_median": float(np.nanmedian(x[np.setdiff1d(pop, win)])),
                "lift_by_fifth_low_to_high": [float(is_win[q_pop == q].mean() / base) if (q_pop == q).any() and base > 0 else None for q in range(5)]}

    def lift_cat(labels, pop, win):
        o = {}
        for lab_ in sorted(set(labels[j] for j in pop)):
            m = np.array([j for j in pop if labels[j] == lab_])
            if len(m) >= max(5, int(20 * scale)):
                o[str(lab_)] = {"names": int(len(m)), "winners": int(np.isin(m, win).sum()),
                                "lift": float(np.isin(m, win).mean() / (len(win) / len(pop)))}
        return o

    out = {"generated": fridays[-1], "names": n, "decades": {}}
    for dname, (s_date, e_date) in DECADES.items():
        S, E = wk(s_date), (nW - 1 if e_date == "9" else wk(e_date))
        pop = np.flatnonzero(liquid[S] & ~np.isnan(Cw[S]) & ~np.isnan(Cw[E]))
        ret = Cw[E] / Cw[S] - 1.0
        k = max(5, int(round(TOP_SHARE * len(pop))))
        win = pop[np.argsort(-ret[pop])][:k]
        rest = np.setdiff1d(pop, win)
        prior52 = Cw[S] / Cw[S - 52] - 1.0
        prior104 = Cw[S] / Cw[S - 104] - 1.0
        tiers = [TIER_NAMES[t] if t >= 0 else "none" for t in tier[S]]
        d = {"from": fridays[S], "to": fridays[E], "population": int(len(pop)), "winners": int(k),
             "spy_multiple": float(spy_c[E] / spy_c[S]), "median_multiple_all": float(np.median(ret[pop]) + 1.0),
             "winner_cutoff_multiple": float(ret[win[-1]] + 1.0), "winner_median_multiple": float(np.median(ret[win]) + 1.0),
             "at_start": {"size tier": lift_cat(tiers, pop, win), "sector": lift_cat(sector, pop, win),
                          "had a channel worth owning": lift_cat(["yes" if channel[S, j] else "no" for j in range(n)], pop, win),
                          "on the screen": lift_cat(["yes" if screen[S, j] else "no" for j in range(n)], pop, win),
                          "more than 20% under the 52-week high": lift_cat(["yes" if off_high[S, j] <= -OFF_HIGH else "no" for j in range(n)], pop, win),
                          "weekly swing": lift_numeric(swing[S], pop, win), "prior 52-week return": lift_numeric(prior52, pop, win),
                          "prior 104-week return": lift_numeric(prior104, pop, win), "distance under 52-week high": lift_numeric(off_high[S], pop, win),
                          "size (log)": lift_numeric(np.log(size[S]), pop, win)}}
        paths = {int(j): path(int(j), S, E) for j in pop}
        def grp(js, key, f=np.median):
            return float(f([paths[int(j)][key] for j in js]))
        def capture(j):
            p_ = paths[int(j)]
            tot = math.log(1.0 + ret[j])
            return math.log(max(p_["rule_growth"], 1e-9)) / tot if tot > 0.05 else None
        def done_by_first(j):
            p_ = paths[int(j)]
            tot = math.log(1.0 + ret[j])
            return math.log(Cw[p_["first_buy"], j] / Cw[S, j]) / tot if p_["first_buy"] is not None and tot > 0.05 else None
        caps = [c for c in (capture(j) for j in win) if c is not None]
        dones = [c for c in (done_by_first(j) for j in win) if c is not None]
        d["along_the_way"] = {g: {"shakeouts_median": grp(js, "shakeouts"), "max_drawdown_median": grp(js, "max_drawdown"),
                                  "screen_share_median": grp(js, "screen_share"), "rule_weeks_in_median": grp(js, "rule_weeks_in"),
                                  "rule_multiple_median": grp(js, "rule_growth"), "hold_multiple_median": float(np.median(ret[js]) + 1.0),
                                  "share_never_bought": float(np.mean([paths[int(j)]["first_buy"] is None for j in js])),
                                  "share_rule_beat_holding": float(np.mean([paths[int(j)]["rule_growth"] > 1.0 + ret[j] for j in js]))}
                              for g, js in (("winners", win), ("rest", rest))}
        d["along_the_way"]["winners"]["share_of_log_move_kept_median"] = float(np.median(caps)) if caps else None
        d["along_the_way"]["winners"]["share_of_log_move_over_by_first_buy_median"] = float(np.median(dones)) if dones else None
        d["top_30"] = [{"ticker": names[j], "sector": sector[j], "tier_at_start": tiers[j], "multiple": float(1.0 + ret[j]),
                        "swing_at_start": float(swing[S, j]) if swing[S, j] == swing[S, j] else None,
                        "prior_52w": float(prior52[j]) if prior52[j] == prior52[j] else None,
                        "under_high_at_start": float(off_high[S, j]) if off_high[S, j] == off_high[S, j] else None,
                        "on_screen_at_start": bool(screen[S, j]), "shakeouts": paths[int(j)]["shakeouts"],
                        "max_drawdown": paths[int(j)]["max_drawdown"], "screen_share": paths[int(j)]["screen_share"],
                        "rule_multiple": paths[int(j)]["rule_growth"], "rule_sales": paths[int(j)]["rule_sales"],
                        "first_buy": fridays[paths[int(j)]["first_buy"]] if paths[int(j)]["first_buy"] is not None else None}
                       for j in win[:30]]
        out["decades"][dname] = d

    # the best two-year runs begun inside 2016-26, later listings included
    S, E = wk(DECADES["2016-26"][0]), nW - 1
    runs = []
    for j in range(n):
        best = None
        for w in range(S, E - RUN + 1):
            a, b = Cw[w, j], Cw[w + RUN, j]
            if a == a and b == b and liquid[w, j]:
                r = b / a
                if best is None or r > best[0]:
                    best = (r, w)
        if best:
            runs.append((best[0], best[1], j))
    runs.sort(reverse=True)
    top_runs = runs[:max(10, int(100 * scale))]
    rows = []
    for r, w, j in top_runs:
        rows.append({"ticker": names[j], "sector": sector[j], "from": fridays[w], "multiple": float(r),
                     "tier_at_start": TIER_NAMES[tier[w, j]] if tier[w, j] >= 0 else "none",
                     "under_high_at_start": float(off_high[w, j]) if off_high[w, j] == off_high[w, j] else None,
                     "channel_at_start": bool(channel[w, j]), "on_screen_at_start": bool(screen[w, j]),
                     "on_screen_in_first_26_weeks": bool(screen[w:w + 27, j].any()),
                     "first_screen_week_in_run": next((int(x - w) for x in range(w, w + RUN + 1) if screen[x, j]), None),
                     "weeks_of_history_at_start": int((~np.isnan(Cw[:w + 1, j])).sum())})
    uh = [x["under_high_at_start"] for x in rows if x["under_high_at_start"] is not None]
    fs = [x["first_screen_week_in_run"] for x in rows if x["first_screen_week_in_run"] is not None]
    out["best_two_year_runs"] = {"count": len(rows), "median_multiple": float(np.median([x["multiple"] for x in rows])),
                                 "share_more_than_20_under_high_at_start": float(np.mean([u <= -OFF_HIGH for u in uh])) if uh else None,
                                 "median_under_high_at_start": float(np.median(uh)) if uh else None,
                                 "share_with_channel_at_start": float(np.mean([x["channel_at_start"] for x in rows])),
                                 "share_on_screen_at_start": float(np.mean([x["on_screen_at_start"] for x in rows])),
                                 "share_on_screen_in_first_26_weeks": float(np.mean([x["on_screen_in_first_26_weeks"] for x in rows])),
                                 "share_never_on_screen_in_run": float(np.mean([x["first_screen_week_in_run"] is None for x in rows])),
                                 "median_first_screen_week": float(np.median(fs)) if fs else None,
                                 "by_tier": {t: int(sum(1 for x in rows if x["tier_at_start"] == t)) for t in TIER_NAMES + ["none"]},
                                 "by_sector": {s_: int(sum(1 for x in rows if x["sector"] == s_)) for s_ in sorted(set(x["sector"] for x in rows))},
                                 "rows": rows}

    def P(x, d=0):
        return "  --" if x is None else f"{100 * x:.{d}f}%"
    for dname, d in out["decades"].items():
        print(f"\n=== {dname}: {d['from']} to {d['to']}; {d['population']} names, {d['winners']} winners; SPY x{d['spy_multiple']:.1f}, "
              f"median name x{d['median_multiple_all']:.1f}, winners from x{d['winner_cutoff_multiple']:.1f}, median x{d['winner_median_multiple']:.1f}")
        for trait, v in d["at_start"].items():
            if v is None:
                continue
            if "lift_by_fifth_low_to_high" in v:
                print(f"  {trait:30} winners {v['winners_median']:8.3f} rest {v['rest_median']:8.3f}  lift by fifth, low to high: "
                      + " ".join("  --" if x is None else f"{x:4.1f}" for x in v["lift_by_fifth_low_to_high"]))
            else:
                print(f"  {trait:30} " + "  ".join(f"{k_} {x['winners']}/{x['names']} ({x['lift']:.1f})" for k_, x in v.items()))
        for g, v in d["along_the_way"].items():
            print(f"  along the way, {g:7}: 20% shake-outs {v['shakeouts_median']:.0f}, largest drawdown {P(v['max_drawdown_median'])}, weeks on screen {P(v['screen_share_median'])}, "
                  f"rule held it {P(v['rule_weeks_in_median'])} of weeks, rule x{v['rule_multiple_median']:.1f} against holding x{v['hold_multiple_median']:.1f}, "
                  f"never bought {P(v['share_never_bought'])}, rule beat holding {P(v['share_rule_beat_holding'])}")
        w_ = d["along_the_way"]["winners"]
        print(f"  winners: share of the (log) move the rule kept {P(w_['share_of_log_move_kept_median'])}; over by the first buy {P(w_['share_of_log_move_over_by_first_buy_median'])}")
        print("  top 30: " + "; ".join(f"{x['ticker']} x{x['multiple']:.0f} ({x['sector'][:4]}, {x['tier_at_start']}, {x['shakeouts']} shakes, dd {P(x['max_drawdown'])}, rule x{x['rule_multiple']:.1f})" for x in d["top_30"]))
    b = out["best_two_year_runs"]
    print(f"\n=== best two-year runs begun in 2016-26: {b['count']} names, median x{b['median_multiple']:.1f}")
    print(f"  at the start of the run: more than 20% under the 52-week high {P(b['share_more_than_20_under_high_at_start'])} (median {P(b['median_under_high_at_start'])}); "
          f"had a channel {P(b['share_with_channel_at_start'])}; on the screen {P(b['share_on_screen_at_start'])}")
    print(f"  on the screen within 26 weeks {P(b['share_on_screen_in_first_26_weeks'])}; never in the run {P(b['share_never_on_screen_in_run'])}; median first screen week {b['median_first_screen_week']}")
    print(f"  by tier {b['by_tier']}\n  by sector {b['by_sector']}")
    print("  top 30: " + "; ".join(f"{x['ticker']} x{x['multiple']:.0f} from {x['from'][:7]} ({P(x['under_high_at_start'])} off high, screen wk {x['first_screen_week_in_run']})" for x in b["rows"][:30]))
    if not smoke:
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {out_path.name}")


if __name__ == "__main__":
    main(sys.argv)
