#!/usr/bin/env python3
"""Pass 42 -- who breaks first: the stock, its sector or the market.

Three measurements on Pass 41's channel (weekly, from the swing low along the
lows): the order of breaks between a stock, its sector fund and SPY; whether
the strongest names in a sector outlast its break; and whether a channel drawn
while the sector and market sit low in theirs is broken sooner.

Registered in lab/README.md (Pass 42) before any run.

    python lab/pass42_who_breaks_first.py          # the three measurements
    python lab/pass42_who_breaks_first.py smoke    # plumbing: 80 names
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
import pass41_owner_channel as p41  # noqa: E402

R2_MIN = 0.80
H = 13
GAP = 26
OUT = lab.RESULTS / "pass42_who_breaks_first.json"
FLOOR = math.log(1.0 + p41.MIN_SLOPE_YEAR) / 52.0


def weekly_hlc(frame, cols, sess, first, last):
    O, C = p38.weekly(frame, cols, sess)
    Hd = frame["High"][cols].to_numpy(dtype=float)[sess]
    Ld = frame["Low"][cols].to_numpy(dtype=float)[sess]
    with np.errstate(invalid="ignore"):
        Hw = np.array([np.nanmax(Hd[a:b + 1], axis=0) for a, b in zip(first, last)])
        Lw = np.array([np.nanmin(Ld[a:b + 1], axis=0) for a, b in zip(first, last)])
    return O[first], C[last], Hw, Lw


def episodes(logc, lower, slope, ok):
    """Per column: list of (open week, break week or None), and an 'inside' mask."""
    nW, n = logc.shape
    eps = [[] for _ in range(n)]
    inside = np.zeros((nW, n), dtype=bool)
    for j in range(n):
        active = None
        for w in range(nW):
            if np.isnan(logc[w, j]):
                if active:
                    eps[j].append((active[2], None))
                active = None
                continue
            if active:
                a, b, e = active
                if logc[w, j] < a + b * (w - e):
                    eps[j].append((e, w))
                    active = None
                else:
                    inside[w, j] = True
            if active is None and ok[w, j]:
                active = (float(lower[w, j]), float(slope[w, j]), w)
                inside[w, j] = True
        if active:
            eps[j].append((active[2], None))
    return eps, inside


def nw_t(x, lags=H - 1):
    x = np.asarray([v for v in x if v == v], dtype=float)
    n = len(x)
    if n < lags + 5:
        return None
    d = x - x.mean()
    var = float((d * d).sum()) / n
    for k in range(1, lags + 1):
        var += 2.0 * (1.0 - k / (lags + 1.0)) * float((d[k:] * d[:-k]).sum()) / n
    return float(x.mean() / math.sqrt(var / n)) if var > 0 else None


def nw_se(x, lags=H - 1):
    """(mean, standard error) of a weekly series, allowing for overlap."""
    x = np.asarray([v for v in x if v == v], dtype=float)
    n = len(x)
    if n < lags + 5:
        return None, None
    d = x - x.mean()
    var = float((d * d).sum()) / n
    for k in range(1, lags + 1):
        var += 2.0 * (1.0 - k / (lags + 1.0)) * float((d[k:] * d[:-k]).sum()) / n
    return float(x.mean()), (math.sqrt(var / n) if var > 0 else None)


def unpaired(x, y):
    """Difference of two weekly series that never share a week (the market is
    low or it is not): means, and a t from the two overlap-adjusted errors."""
    (mx, sx), (my, sy) = nw_se(x), nw_se(y)
    if None in (mx, sx, my, sy):
        return None, None
    return mx - my, (mx - my) / math.sqrt(sx * sx + sy * sy)


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

    _, Cw, Hw, Lw = weekly_hlc(df, names, sess, first, last)
    _, fC, fH, fL = weekly_hlc(fdf, p38.FUNDS, sess, first, last)
    _, sC, sH, sL = weekly_hlc(df, ["SPY"], sess, first, last)
    nW, n = Cw.shape
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names")

    def tables(C, Hh, Ll):
        lower, slope, r2, pos, _ = p41.channel_table(C, Hh, Ll)
        rising = ~np.isnan(lower) & (np.nan_to_num(slope, nan=-1.0) >= FLOOR)
        ok = rising & (np.nan_to_num(r2, nan=0.0) >= R2_MIN)
        with np.errstate(invalid="ignore", divide="ignore"):
            lc = np.log(C)
        eps, inside = episodes(lc, lower, slope, ok)
        state = np.where(~rising, 0, np.where(pos < 1 / 3, 1, np.where(pos < 2 / 3, 2, 3)))
        return {"lower": lower, "slope": slope, "ok": ok, "lc": lc, "eps": eps, "inside": inside, "state": state,
                "listed": ~np.isnan(C)}
    S, F, M = tables(Cw, Hw, Lw), tables(fC, fH, fL), tables(sC, sH, sL)

    fidx = {f: i for i, f in enumerate(p38.FUNDS)}
    fund_col = np.zeros((nW, n), dtype=int)                       # the fund standing for each stock's sector, by week
    for j, t in enumerate(names):
        f = p38.SECTOR_FUND[sector[t]]
        own, fb = fidx[f], fidx.get(p38.FALLBACK.get(f, ""), fidx[f])
        young = np.cumsum(F["listed"][:, own]) < p41.MIN_AGE + 1
        fund_col[:, j] = np.where(young, fb, own)
    added_arr = np.array([added[t] or "0000-00-00" for t in names])
    member = added_arr[None, :] <= np.array(fridays)[:, None]

    def break_weeks(eps_j):
        return np.array(sorted(b for _, b in eps_j if b is not None), dtype=int)
    f_breaks = [break_weeks(e) for e in F["eps"]]
    m_breaks = break_weeks(M["eps"][0])

    def marks(breaks):                                            # per week: a break in the H weeks before / after / that week
        before = np.zeros(nW, dtype=bool)
        after = np.zeros(nW, dtype=bool)
        same = np.zeros(nW, dtype=bool)
        for b in breaks:
            before[b + 1:b + H + 1] = True
            after[max(0, b - H):b] = True
            same[b] = True
        return before, same, after
    f_marks = [marks(b) for b in f_breaks]
    m_marks = marks(m_breaks)

    # ---- A: the order of breaks
    def order(get_marks, get_breaks, get_inside):
        ev = {"before": 0, "same": 0, "after": 0, "none": 0, "n": 0, "other_inside": 0}
        base = {"before": 0, "same": 0, "after": 0, "n": 0}
        gaps = []
        for j in range(n):
            brk = np.zeros(nW, dtype=bool)
            for e, b in S["eps"][j]:
                if b is not None and member[b, j] and H <= b < nW - H:
                    brk[b] = True
            for w in np.flatnonzero(brk):
                bf, sm, af = get_marks(w, j)
                ev["n"] += 1
                ev["before"] += bool(bf[w])
                ev["same"] += bool(sm[w])
                ev["after"] += bool(af[w])
                ev["none"] += not (bf[w] or sm[w] or af[w])
                ev["other_inside"] += bool(get_inside(w - 1, j))
                ob = get_breaks(w, j)
                if len(ob):
                    k = ob[np.argmin(np.abs(ob - w))]
                    if abs(int(k) - int(w)) <= GAP:
                        gaps.append(int(k) - int(w))            # negative: the other broke first
            calm = S["inside"][:, j] & ~brk & member[:, j]
            calm[:H] = False
            calm[nW - H:] = False
            for w in np.flatnonzero(calm):
                bf, sm, af = get_marks(w, j)
                base["n"] += 1
                base["before"] += bool(bf[w])
                base["same"] += bool(sm[w])
                base["after"] += bool(af[w])
        res = {"stock_breaks": ev["n"]}
        for k in ("before", "same", "after", "none"):
            res[k] = ev[k] / ev["n"] if ev["n"] else None
        for k in ("before", "same", "after"):
            res["base_" + k] = base[k] / base["n"] if base["n"] else None
        res["other_was_inside_its_channel_the_week_before"] = ev["other_inside"] / ev["n"] if ev["n"] else None
        res["pairs_within_26w"] = len(gaps)
        res["median_gap_weeks"] = float(np.median(gaps)) if gaps else None
        res["share_other_first"] = float(np.mean([g < 0 for g in gaps])) if gaps else None
        res["share_same_week"] = float(np.mean([g == 0 for g in gaps])) if gaps else None
        res["share_stock_first"] = float(np.mean([g > 0 for g in gaps])) if gaps else None
        return res
    A = {"sector": order(lambda w, j: f_marks[fund_col[w, j]], lambda w, j: f_breaks[fund_col[w, j]],
                         lambda w, j: F["inside"][w, fund_col[w, j]]),
         "market": order(lambda w, j: m_marks, lambda w, j: m_breaks, lambda w, j: M["inside"][w, 0])}

    # ---- B: do the strong hang on after the sector breaks
    thirds = {k: {"n": 0, "survive": 0, "ret": 0.0} for k in ("weak", "middle", "strong")}
    diffs_s, diffs_r, events = [], [], 0
    with np.errstate(invalid="ignore", divide="ignore"):
        rel52 = np.full((nW, n), np.nan)
        rel52[52:] = (S["lc"][52:] - S["lc"][:-52])
        f52 = np.full(fC.shape, np.nan)
        f52[52:] = F["lc"][52:] - F["lc"][:-52]
    next_break = np.full((nW, n), 10 ** 6)                         # the week the episode covering w breaks
    for j in range(n):
        for e, b in S["eps"][j]:
            end = b if b is not None else nW
            next_break[e:end, j] = b if b is not None else 10 ** 6
    for fi, breaks in enumerate(f_breaks):
        for t in breaks:
            if t < 52 or t >= nW - H:
                continue
            js = [j for j in range(n) if fund_col[t, j] == fi and S["inside"][t, j] and member[t, j]
                  and next_break[t, j] > t and not np.isnan(rel52[t, j]) and not np.isnan(Cw[t + H, j])]
            if len(js) < 6:
                continue
            events += 1
            js.sort(key=lambda j: rel52[t, j] - f52[t, fi])
            k = len(js) // 3
            groups = {"weak": js[:k], "middle": js[k:len(js) - k], "strong": js[len(js) - k:]}
            ev = {}
            for g, members_ in groups.items():
                sv = [next_break[t, j] > t + H for j in members_]
                rt = [Cw[t + H, j] / Cw[t, j] - 1.0 for j in members_]
                thirds[g]["n"] += len(members_)
                thirds[g]["survive"] += sum(sv)
                thirds[g]["ret"] += float(sum(rt))
                ev[g] = (float(np.mean(sv)), float(np.mean(rt)))
            diffs_s.append(ev["strong"][0] - ev["weak"][0])
            diffs_r.append(ev["strong"][1] - ev["weak"][1])
    B = {"sector_break_events": events,
         "thirds": {g: {"n": v["n"], "unbroken_13w_later": v["survive"] / v["n"] if v["n"] else None,
                        "return_13w": v["ret"] / v["n"] if v["n"] else None} for g, v in thirds.items()},
         "strong_minus_weak_unbroken": float(np.mean(diffs_s)) if diffs_s else None,
         "strong_minus_weak_unbroken_t": p32.tstat(diffs_s) if len(diffs_s) > 2 else None,
         "strong_minus_weak_return": float(np.mean(diffs_r)) if diffs_r else None,
         "strong_minus_weak_return_t": p32.tstat(diffs_r) if len(diffs_r) > 2 else None}

    # ---- C: the tide
    last_w = nW - H
    broken = np.zeros((last_w, n), dtype=bool)
    with np.errstate(invalid="ignore"):
        for k in range(1, H + 1):
            broken |= S["lc"][k:k + last_w] < S["lower"][:last_w] + S["slope"][:last_w] * k
        fwd = Cw[H:H + last_w] / Cw[:last_w] - 1.0
    cand = S["ok"][:last_w] & member[:last_w] & ~np.isnan(fwd)
    pool = member[:last_w] & ~np.isnan(fwd)
    sec_state = np.take_along_axis(F["state"], fund_col, axis=1)[:last_w]
    mkt_state = np.repeat(M["state"][:last_w, :1], n, axis=1)
    low_s, low_m = sec_state <= 1, mkt_state <= 1
    groups = {"against (both low or none)": low_s & low_m, "with (both middle or top)": ~low_s & ~low_m,
              "sector low, market not": low_s & ~low_m, "market low, sector not": ~low_s & low_m,
              "sector: none": sec_state == 0, "sector: bottom third": sec_state == 1,
              "sector: middle": sec_state == 2, "sector: top third": sec_state == 3,
              "market: none": mkt_state == 0, "market: bottom third": mkt_state == 1,
              "market: middle": mkt_state == 2, "market: top third": mkt_state == 3,
              "all candidates": np.ones_like(cand)}
    wk_series = {}
    C = {}
    for g, mask in groups.items():
        m = cand & mask
        brk_w, exc_w, cnt = [], [], 0
        for w in range(last_w):
            if not m[w].any() or not pool[w].any():
                brk_w.append(np.nan)
                exc_w.append(np.nan)
                continue
            cnt += int(m[w].sum())
            brk_w.append(float(broken[w][m[w]].mean()))
            exc_w.append(float(fwd[w][m[w]].mean() - fwd[w][pool[w]].mean()))
        wk_series[g] = (np.array(brk_w), np.array(exc_w))
        C[g] = {"name_weeks": cnt, "weeks_present": int(np.sum(~np.isnan(brk_w))),
                "broken_within_13w": float(np.nanmean(brk_w)), "return_13w_over_list": float(np.nanmean(exc_w))}
    a, w_ = wk_series["against (both low or none)"], wk_series["with (both middle or top)"]
    db, tb = unpaired(a[0], w_[0])
    dr, tr = unpaired(a[1], w_[1])
    C["against_minus_with"] = {"note": "unpaired: the two groups never share a week",
                               "broken": db, "broken_t": tb, "return": dr, "return_t": tr}
    lo, hi = wk_series["sector: bottom third"], wk_series["sector: top third"]
    both = ~np.isnan(lo[0]) & ~np.isnan(hi[0])
    C["sector_bottom_minus_top_same_week"] = {
        "weeks_with_both": int(both.sum()),
        "broken": float((lo[0] - hi[0])[both].mean()) if both.any() else None, "broken_t": nw_t((lo[0] - hi[0])[both]),
        "return": float((lo[1] - hi[1])[both].mean()) if both.any() else None, "return_t": nw_t((lo[1] - hi[1])[both])}

    out = {"generated": fridays[-1], "weeks": nW, "names": n,
           "episodes": {"stocks": int(sum(len(e) for e in S["eps"])),
                        "stock_breaks": int(sum(1 for e in S["eps"] for _, b in e if b is not None)),
                        "fund_breaks": int(sum(len(b) for b in f_breaks)), "spy_breaks": int(len(m_breaks)),
                        "spy_break_weeks": [fridays[b] for b in m_breaks]},
           "A": A, "B": B, "C": C}

    def P(x, d=1):
        return "   --" if x is None else f"{100 * x:5.{d}f}%"
    e = out["episodes"]
    print(f"stock breaks {e['stock_breaks']}, fund breaks {e['fund_breaks']}, SPY breaks {e['spy_breaks']}: {', '.join(e['spy_break_weeks'])}")
    for k, r in A.items():
        print(f"A {k:7} n {r['stock_breaks']}  broke in 13w before {P(r['before'])} (base {P(r['base_before'])})  same week {P(r['same'])} "
              f"(base {P(r['base_same'])})  in 13w after {P(r['after'])} (base {P(r['base_after'])})  none {P(r['none'])}")
        print(f"   {k} inside its own channel the week before: {P(r['other_was_inside_its_channel_the_week_before'])}; pairs within 26w {r['pairs_within_26w']}: "
              f"median gap {r['median_gap_weeks']} wk, other first {P(r['share_other_first'])}, same week {P(r['share_same_week'])}, stock first {P(r['share_stock_first'])}")
    print(f"B {B['sector_break_events']} sector breaks")
    for g, v in B["thirds"].items():
        print(f"   {g:7} n {v['n']:5}  unbroken 13w later {P(v['unbroken_13w_later'])}  13w return {P(v['return_13w'])}")
    print(f"   strong - weak: unbroken {P(B['strong_minus_weak_unbroken'])} (t {B['strong_minus_weak_unbroken_t']:.2f}), "
          f"return {P(B['strong_minus_weak_return'])} (t {B['strong_minus_weak_return_t']:.2f})")
    for g, v in C.items():
        if not isinstance(v, dict) or "name_weeks" not in v:
            continue
        print(f"C {g:28} name-weeks {v['name_weeks']:7}  broken within 13w {P(v['broken_within_13w'])}  13w return over list {P(v['return_13w_over_list'], 2)}")
    for key in ("against_minus_with", "sector_bottom_minus_top_same_week"):
        d = C[key]
        f = lambda x: "--" if x is None else f"{x:.2f}"  # noqa: E731
        print(f"   {key}: broken {P(d['broken'])} (t {f(d['broken_t'])}), return {P(d['return'], 2)} (t {f(d['return_t'])})")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
