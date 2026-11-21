#!/usr/bin/env python3
"""Pass 38 -- the chart stack: market, sector and stock channels, nothing else.

A mechanical book from the owner's chart reading: a stock is bought while it,
its sector fund and SPY are each in a rising channel, and sold when a channel
breaks. The channel is Marky's channel_facts as production has it. Every arm
is measured against random books at the same exposure, because the frozen
S&P 500 list flatters any picker drawn from it.

Registered in lab/README.md (Pass 38) before any run.

    python lab/pass38_chart_stack.py          # every arm, 2007 on
    python lab/pass38_chart_stack.py smoke    # plumbing: 2022 on, 80 names, 20 draws
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

from scan_pipeline.engines.marky import channel_facts  # noqa: E402
from scan_pipeline.utils.data_utils import PINNED_MIN_WEEKS, PINNED_VOL_MAX  # noqa: E402

FULL_CSV = lab.LAB / "universe_sp500_full_2026-09-22.csv"
SECTOR_FUND = {"Communication Services": "XLC", "Consumer Discretionary": "XLY", "Consumer Staples": "XLP",
               "Energy": "XLE", "Financials": "XLF", "Health Care": "XLV", "Industrials": "XLI",
               "Information Technology": "XLK", "Materials": "XLB", "Real Estate": "XLRE", "Utilities": "XLU"}
FALLBACK = {"XLRE": "XLF", "XLC": "XLK"}          # where the sector sat before its own fund existed
FUNDS = sorted(set(SECTOR_FUND.values()))
SLOTS, PER_SECTOR, WEIGHT = 10, 3, 0.10
SLIP = 0.0010
BREAK = 2.5
DRAWS = 200
SEED = 20261120
HALF = "2017-01-01"
OUT = lab.RESULTS / "pass38_chart_stack.json"

#        name                  sector market break  beta   pullback
ARMS = [("stock",              False, False, 2.5,   False, True),
        ("stock+sector",       True,  False, 2.5,   False, True),
        ("full",               True,  True,  2.5,   False, True),
        ("full, 2.0",          True,  True,  2.0,   False, True),
        ("full, 3.0",          True,  True,  3.0,   False, True),
        ("full, beta",         True,  True,  2.5,   True,  True),
        ("full, no pullback",  True,  True,  2.5,   False, False)]


def weekly(df, cols, sessions):
    """Weekly first open and last close for cols, on SPY's sessions."""
    O = df["Open"][cols].to_numpy(dtype=float)[sessions]
    C = df["Close"][cols].to_numpy(dtype=float)[sessions]
    return O, C


def facts_table(Cw):
    """channel_facts for every (week, column): up, z, score, valid."""
    nW, n = Cw.shape
    up = np.zeros((nW, n), dtype=bool)
    valid = np.zeros((nW, n), dtype=bool)
    z = np.full((nW, n), np.nan)
    score = np.full((nW, n), np.nan)
    for j in range(n):
        col = Cw[:, j]
        good = ~np.isnan(col)
        for w in range(nW):
            if not good[w]:
                continue
            lo = max(0, w - 59)
            f = channel_facts([float(c) for c in col[lo:w + 1] if c == c])
            if f is None:
                continue
            valid[w, j] = True
            up[w, j] = f["why_not"] in (None, "broke below the channel")
            z[w, j] = f["z"]
            score[w, j] = f["position_score"] + f["trend_score"] + f["macd_score"]
    return up, z, score, valid


def quality_table(Cw):
    """Slope over width of the 26-week log channel: the cleanest channel first."""
    nW, n = Cw.shape
    q = np.full((nW, n), np.nan)
    x = np.arange(26) - 12.5
    sxx = float((x * x).sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        for w in range(25, nW):
            y = np.log(Cw[w - 25:w + 1])
            yb = y.mean(axis=0)
            slope = (x[:, None] * (y - yb)).sum(axis=0) / sxx
            resid = y - (yb + slope * x[:, None])
            width = np.sqrt((resid ** 2).sum(axis=0) / 24.0)
            q[w] = np.where(width > 0, slope / width, np.nan)
    return q


def beta_table(Cw, spy):
    nW, n = Cw.shape
    b = np.full((nW, n), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = Cw[1:] / Cw[:-1] - 1.0
        m = spy[1:] / spy[:-1] - 1.0
        for w in range(52, nW):
            rr, mm = r[w - 52:w], m[w - 52:w]
            mv = mm - mm.mean()
            b[w] = (mv[:, None] * (rr - rr.mean(axis=0))).sum(axis=0) / float((mv * mv).sum())
    return b


def pinned_table(Ow, Cw):
    nW, n = Cw.shape
    pin = np.zeros((nW, n), dtype=bool)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (Cw - Ow) / Ow
        for w in range(nW):
            win = r[max(0, w - 12):w + 1]
            cnt = (~np.isnan(win)).sum(axis=0)
            vol = np.nanstd(win, axis=0) * 52 ** 0.5
            pin[w] = (cnt >= PINNED_MIN_WEEKS) & (vol < PINNED_VOL_MAX)
    return pin


def stats(rets, spy, fridays):
    r = np.asarray(rets, dtype=float)
    if len(r) < 3:
        return None
    cum = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(cum)
    sd = float(r.std(ddof=1))
    ex = r - np.asarray(spy, dtype=float)
    return {"weeks": len(r), "mean_week": float(r.mean()), "cagr": float(cum[-1] ** (52.0 / len(r)) - 1.0),
            "vol": sd * 52 ** 0.5, "sharpe": float(r.mean() / sd * 52 ** 0.5) if sd > 0 else None,
            "max_drawdown": float((cum / peak - 1.0).min()),
            "excess_vs_spy_week": float(ex.mean()), "excess_t": p32.tstat(ex),
            "first": fridays[0], "last": fridays[-1]}


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    added = p32.members()
    with open(FULL_CSV, encoding="utf-8") as fh:
        sector = {r["ticker"]: r["gics_sector"] for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}
    tickers = sorted(added)
    df = lab.download(tickers + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)
    fdf = lab.download(FUNDS, True, p32.DATA_END, start=p32.DATA_START)
    have = set(df.columns.get_level_values(1))
    names = [t for t in tickers if t in have and sector.get(t) in SECTOR_FUND]
    if smoke:
        names = names[::max(1, len(names) // 80)][:80]
    fdf = fdf.reindex(df.index)

    spy_c_d = df["Close"]["SPY"].to_numpy(dtype=float)
    sess = [i for i, v in enumerate(spy_c_d) if v == v]
    days = [df.index[i].date() for i in sess]
    iso = [d.isocalendar()[:2] for d in days]
    first, last = [], []
    for i in range(len(days)):
        if i == 0 or iso[i] != iso[i - 1]:
            first.append(i)
        if i == len(days) - 1 or iso[i] != iso[i + 1]:
            last.append(i)
    fridays = [days[i].isoformat() for i in last]

    def wk(frame, cols):
        O, C = weekly(frame, cols, sess)
        return O[first], C[last]

    Ow, Cw = wk(df, names)
    sOw, sCw = wk(df, ["SPY"])
    fOw, fCw = wk(fdf, FUNDS)
    nW, n = Cw.shape
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names, {len(FUNDS)} funds")

    up, z, score, valid = facts_table(Cw)
    s_up, s_z, _, s_valid = facts_table(sCw)
    f_up, f_z, _, f_valid = facts_table(fCw)
    quality = quality_table(Cw)
    beta = np.clip(np.nan_to_num(beta_table(Cw, sCw[:, 0]), nan=1.0), 0.75, 1.5)
    pin = pinned_table(Ow, Cw)

    mkt_ok = s_valid[:, 0] & s_up[:, 0] & (s_z[:, 0] >= -BREAK)
    fund_ok_raw = f_valid & f_up & (f_z >= -BREAK)
    fidx = {f: i for i, f in enumerate(FUNDS)}
    fund_ok = np.zeros((nW, len(FUNDS)), dtype=bool)
    for f, i in fidx.items():
        fb = fidx.get(FALLBACK.get(f, ""), i)
        fund_ok[:, i] = np.where(f_valid[:, i], fund_ok_raw[:, i], fund_ok_raw[:, fb])
    sec_of = np.array([fidx[SECTOR_FUND[sector[t]]] for t in names])
    sec_ok = fund_ok[:, sec_of]                                   # weeks x names
    added_arr = np.array([added[t] or "0000-00-00" for t in names])

    w0 = next(w for w in range(nW) if s_valid[w, 0])
    if smoke:
        w0 = max(w0, next(w for w in range(nW) if fridays[w] >= "2022-01-01"))
    weeks = list(range(w0, nW - 1))                                # decide at w, earn week w+1
    wk_dates = [fridays[w + 1] for w in weeks]
    with np.errstate(invalid="ignore", divide="ignore"):
        R_hold = Cw[1:] / Cw[:-1] - 1.0                            # Friday close to Friday close, index w -> week w+1
        R_in = Cw[1:] / Ow[1:] - 1.0                               # Monday open to Friday close
        R_out = Ow[1:] / Cw[:-1] - 1.0                             # Friday close to Monday open
    spy_hold = sCw[1:, 0] / sCw[:-1, 0] - 1.0
    spy_in = sCw[1:, 0] / sOw[1:, 0] - 1.0
    spy_out = sOw[1:, 0] / sCw[:-1, 0] - 1.0

    pool = [np.flatnonzero(valid[w] & (added_arr <= fridays[w]) & ~np.isnan(R_hold[w])) for w in range(nW - 1)]
    spy = [float(spy_hold[w]) for w in weeks]
    listr = [float(R_hold[w][pool[w]].mean()) if len(pool[w]) else 0.0 for w in weeks]

    gated, inside = [], False
    for w in weeks:
        want = bool(mkt_ok[w])
        if want and inside:
            gated.append(float(spy_hold[w]))
        elif want:
            gated.append(float(spy_in[w]) - SLIP)
        elif inside:
            gated.append(float(spy_out[w]) - SLIP)
        else:
            gated.append(0.0)
        inside = want

    draws = 20 if smoke else DRAWS
    out = {"generated": fridays[-1], "weeks": len(weeks), "names": n, "first_week": wk_dates[0],
           "last_week": wk_dates[-1], "arms": {}, "controls": {}}
    half = [i for i, d in enumerate(wk_dates) if d < HALF]
    half2 = [i for i, d in enumerate(wk_dates) if d >= HALF]

    def block(rets):
        res = {"all": stats(rets, spy, wk_dates)}
        for key, idx in (("first_half", half), ("second_half", half2)):
            res[key] = stats([rets[i] for i in idx], [spy[i] for i in idx], [wk_dates[i] for i in idx]) if len(idx) > 2 else None
        return res

    out["controls"] = {"SPY": block(spy), "SPY gated": block(gated), "list": block(listr)}
    out["controls"]["SPY gated"]["share_in"] = float(np.mean([mkt_ok[w] for w in weeks]))

    for name, use_sec, use_mkt, brk, use_beta, pullback in ARMS:
        rng = np.random.default_rng(SEED)
        line = -brk * (beta if use_beta else np.ones_like(beta))
        ok = valid & up & (z >= line)
        if use_sec:
            ok = ok & sec_ok
        rank = score if pullback else quality
        held, since = [], {}
        rets, counts, holds, trades = [], [], [], 0
        rand = np.zeros((draws, len(weeks)))
        for i, w in enumerate(weeks):
            m_ok = bool(mkt_ok[w]) or not use_mkt
            keep = [j for j in held if m_ok and ok[w, j] and not np.isnan(R_hold[w, j])]
            gone = [j for j in held if j not in keep]
            entries = []
            if m_ok and len(keep) < SLOTS:
                cand = np.flatnonzero(ok[w] & ~pin[w] & (added_arr <= fridays[w]) & ~np.isnan(R_in[w])
                                      & ~np.isnan(rank[w]) & ((z[w] <= 0) if pullback else True))
                per = {}
                for j in keep:
                    per[sec_of[j]] = per.get(sec_of[j], 0) + 1
                kept = set(keep)
                for j in sorted(cand, key=lambda j: (-rank[w, j], names[j])):
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
        res["avg_names_held"] = float(np.mean(counts))
        res["avg_exposure"] = float(np.mean(counts)) * WEIGHT
        res["weeks_in_cash"] = int(sum(1 for c in counts if c == 0))
        res["trades_per_year"] = trades / (len(weeks) / 52.0)
        res["median_hold_weeks"] = float(np.median(holds)) if holds else None
        res["mean_hold_weeks"] = float(np.mean(holds)) if holds else None
        res["closed_positions"] = len(holds)
        if name == "full":
            years = {}
            for d, a, b in zip(wk_dates, rets, spy):
                y = years.setdefault(d[:4], [1.0, 1.0])
                y[0] *= 1.0 + a
                y[1] *= 1.0 + b
            res["by_year"] = {y: {"full": v[0] - 1.0, "spy": v[1] - 1.0} for y, v in years.items()}
            wl = nW - 1
            res["reading_at_last_close"] = {
                "as_of": fridays[wl], "market_in_channel": bool(mkt_ok[wl]), "spy_z": float(s_z[wl, 0]),
                "sectors": {f: {"in_channel": bool(fund_ok[wl, i]), "z": None if np.isnan(f_z[wl, i]) else float(f_z[wl, i])}
                            for f, i in fidx.items()},
                "held_into_last_week": [{"ticker": names[j], "fund": FUNDS[sec_of[j]], "weeks_held": int(weeks[-1] - since[j] + 1),
                                         "z": float(z[weeks[-1], j])} for j in held]}
        out["arms"][name] = res

    def P(x, d=2):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print(f"{len(weeks)} weeks {wk_dates[0]} .. {wk_dates[-1]}")
    print(f"{'arm':20} {'CAGR':>7} {'vol':>7} {'Sharpe':>6} {'maxDD':>7} {'expo':>6} {'pct':>5} {'pct h1':>6} {'pct h2':>6} {'hold':>5} {'tr/yr':>6}")
    for nm, b in list(out["controls"].items()) + list(out["arms"].items()):
        a = b["all"]
        v = b.get("vs_random") or {}
        g = lambda k: "   --" if not v.get(k) else f"{v[k]['percentile']:5.0f}"  # noqa: E731
        hold = b.get("median_hold_weeks")
        print(f"{nm:20} {P(a['cagr'], 1)} {P(a['vol'], 1)} {a['sharpe']:6.2f} {P(a['max_drawdown'], 1)} "
              f"{P(b.get('avg_exposure'), 0)} {g('all')} {g('first_half'):>6} {g('second_half'):>6} "
              f"{'   --' if hold is None else f'{hold:5.0f}'} {b.get('trades_per_year', 0):6.0f}")
    full = out["arms"]["full"]
    for y, v in full["by_year"].items():
        print(f"   {y}  full {P(v['full'], 1)}  SPY {P(v['spy'], 1)}")
    rd = full["reading_at_last_close"]
    print(f"   at {rd['as_of']}: market in channel {rd['market_in_channel']} (z {rd['spy_z']:+.2f}); "
          f"sectors in: {', '.join(f for f, s in rd['sectors'].items() if s['in_channel']) or 'none'}")
    print("   held:", ", ".join(f"{h['ticker']} ({h['weeks_held']}w)" for h in rd["held_into_last_week"]) or "cash")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
