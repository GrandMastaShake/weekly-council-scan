#!/usr/bin/env python3
"""Pass 33 -- where the Council's gap to SPY sits.

Arithmetic on the booked record (portfolio/history/): a regression of the
weekly book on SPY, an exact split of each week's official alpha into cash,
beta, sector, selection and booking terms, and a dartboard (random books at
the Council's own weights and cash; again sector-matched).

Registered in lab/README.md before any run.

    python lab/pass33_attribution.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

FULL_CSV = lab.LAB / "universe_sp500_full_2026-09-22.csv"
SECTOR_FUND = {"Communication Services": "XLC", "Consumer Discretionary": "XLY", "Consumer Staples": "XLP",
               "Energy": "XLE", "Financials": "XLF", "Health Care": "XLV", "Industrials": "XLI",
               "Information Technology": "XLK", "Materials": "XLB", "Real Estate": "XLRE", "Utilities": "XLU"}
BY_HAND = {"SYM": "Industrials", "ZS": "Information Technology"}   # not in the S&P 500 file
BETA_START = "2025-06-01"
DATA_END = "2026-11-14"
BETA_WEEKS = 52
BETA_MIN = 26
DRAWS = 2000
SEED = 20261116
OUT = lab.RESULTS / "pass33_attribution.json"


def tstat(xs):
    xs = np.asarray(xs, dtype=float)
    if len(xs) < 3 or xs.std(ddof=1) == 0:
        return float("nan")
    return float(xs.mean() / (xs.std(ddof=1) / math.sqrt(len(xs))))


def ols(y, x):
    y, x = np.asarray(y, float), np.asarray(x, float)
    n = len(y)
    X = np.column_stack([np.ones(n), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ coef
    s2 = float(res @ res) / (n - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    r2 = 1.0 - float(res @ res) / float(((y - y.mean()) ** 2).sum())
    return {"alpha": float(coef[0]), "beta": float(coef[1]), "alpha_se": float(math.sqrt(cov[0, 0])),
            "beta_se": float(math.sqrt(cov[1, 1])), "r2": r2, "n": n}


def weekly_closes(series):
    """Last close of each ISO week: [(friday-ish date, close)]."""
    out = {}
    for r in series.rows:
        y, w, _ = date.fromisoformat(r["date"]).isocalendar()
        out[(y, w)] = (r["date"], r["close"])
    return [out[k] for k in sorted(out)]


def beta_before(wk_t, wk_spy, day):
    """OLS beta of weekly returns on SPY's over the 52 weeks ending before `day`."""
    a = {d: c for d, c in wk_t if d < day}
    b = {d: c for d, c in wk_spy if d < day}
    ds = sorted(set(a) & set(b))[-(BETA_WEEKS + 1):]
    if len(ds) < BETA_MIN + 1:
        return None
    ra = np.array([a[ds[i]] / a[ds[i - 1]] - 1 for i in range(1, len(ds))])
    rb = np.array([b[ds[i]] / b[ds[i - 1]] - 1 for i in range(1, len(ds))])
    return float(np.cov(ra, rb, ddof=1)[0, 1] / rb.var(ddof=1))


def main():
    with open(FULL_CSV, encoding="ascii") as fh:
        sp = {r["ticker"]: r["gics_sector"] for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}
    weeks = []
    for f in sorted(lab.HISTORY.glob("*.yaml")):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        if d.get("status") == "closed":
            weeks.append(d)
    picks = sorted({p["ticker"] for d in weeks for p in d["positions"]})
    sector = {t: sp.get(t) or BY_HAND[t] for t in picks}
    funds = sorted(set(SECTOR_FUND.values()))
    frozen = lab.frozen_universe()
    pool = sorted(set(frozen) | set(sp) | set(picks))

    beta_df = lab.download(sorted(set(picks) | set(funds) | {"SPY"}), True, DATA_END, start=BETA_START)
    bb = {t: lab.Series(rows) for t, rows in lab.bars_by_ticker(beta_df).items()}
    wk = {t: weekly_closes(s) for t, s in bb.items()}
    pool_df = lab.download(pool, True, DATA_END, start="2026-07-01")
    pb = {t: lab.Series(rows) for t, rows in lab.bars_by_ticker(pool_df).items()}

    rng = np.random.default_rng(SEED)
    rows, pick_rows, no_beta = [], [], []
    for d in weeks:
        W = str(d["week"])
        mon = date.fromisoformat(W)
        mon = (mon - timedelta(days=mon.weekday())).isoformat()
        r_spy = d["spy_return"] / 100.0
        book = d["weighted_return"] / 100.0
        inv = sum(p["weight"] for p in d["positions"])
        t_cash = -(1.0 - inv) * r_spy
        t_beta = t_sector = t_sel = 0.0
        sumwr = 0.0
        by = {}
        for p in d["positions"]:
            t, w, r = p["ticker"], p["weight"], p["pnl_pct"] / 100.0
            S = SECTOR_FUND[sector[t]]
            r_S = bb[S].week_return(mon)
            b_i = beta_before(wk[t], wk["SPY"], W)
            b_S = beta_before(wk[S], wk["SPY"], W)
            if b_i is None:
                no_beta.append((W, t))
                b_i = 1.0
            e_beta = (b_i - 1.0) * r_spy
            e_sec = r_S - b_S * r_spy
            e_sel = (r - b_i * r_spy) - e_sec
            t_beta += w * e_beta
            t_sector += w * e_sec
            t_sel += w * e_sel
            sumwr += w * r
            sp_ = p.get("sponsor") or "?"
            a = by.setdefault(sp_, {"beta": 0.0, "sector": 0.0, "selection": 0.0, "weight": 0.0})
            a["beta"] += w * e_beta
            a["sector"] += w * e_sec
            a["selection"] += w * e_sel
            a["weight"] += w
            pick_rows.append({"week": W, "ticker": t, "sponsor": sp_, "weight": w, "ret": r, "beta": b_i,
                              "fund": S, "fund_beta": b_S, "beta_term": e_beta, "sector_term": e_sec,
                              "selection_term": e_sel, "vs_spy": r - r_spy})
        booking = book - sumwr
        alpha = book - r_spy

        # dartboards
        ws = [p["weight"] for p in d["positions"]]
        n = len(ws)
        fr = np.array([x for x in (pb[t].week_return(mon) for t in frozen if t in pb) if x is not None])
        d1 = np.array([float(np.dot(ws, fr[rng.choice(len(fr), n, replace=False)])) for _ in range(DRAWS)])
        sec_pool = {}
        for p in d["positions"]:
            g = sector[p["ticker"]]
            if g not in sec_pool:
                sec_pool[g] = np.array([x for x in (pb[t].week_return(mon) for t, s in sp.items() if s == g and t in pb)
                                        if x is not None])
        d2 = np.zeros(DRAWS)
        for p in d["positions"]:
            arr = sec_pool[sector[p["ticker"]]]
            d2 += p["weight"] * arr[rng.integers(0, len(arr), DRAWS)]
        rows.append({"week": W, "book": book, "spy": r_spy, "alpha": alpha, "invested": inv,
                     "cash": t_cash, "beta": t_beta, "sector": t_sector, "selection": t_sel, "booking": booking,
                     "check": t_cash + t_beta + t_sector + t_sel + booking - alpha,
                     "book_beta": sum(p["weight"] * q["beta"] for p, q in zip(d["positions"], pick_rows[-n:])),
                     "names_beta": sum(p["weight"] * q["beta"] for p, q in zip(d["positions"], pick_rows[-n:])) / inv,
                     "pct_frozen": float((d1 < book).mean()), "pct_sector": float((d2 < book).mean()),
                     "dart_frozen_mean": float(d1.mean()), "dart_sector_mean": float(d2.mean()),
                     "by_sponsor": by})

    n = len(rows)
    book = np.array([r["book"] for r in rows])
    spy = np.array([r["spy"] for r in rows])
    inv = np.array([r["invested"] for r in rows])
    reg = ols(book, spy)
    reg_inv = ols(book / inv, spy)
    terms = ("cash", "beta", "sector", "selection", "booking")
    tot = {k: float(sum(r[k] for r in rows)) for k in terms}
    tot["alpha"] = float(sum(r["alpha"] for r in rows))
    cum_book = float(np.prod(1 + book) - 1)
    cum_spy = float(np.prod(1 + spy) - 1)

    def P(x):
        return f"{100 * x:+.2f}%"

    print(f"Pass 33: {n} closed weeks {rows[0]['week']}..{rows[-1]['week']}; book {P(cum_book)} vs SPY {P(cum_spy)} compounded; "
          f"sum of weekly alphas {P(tot['alpha'])}")
    print(f"A. book on SPY: beta {reg['beta']:.2f} (se {reg['beta_se']:.2f}), alpha {P(reg['alpha'])}/wk (se {P(reg['alpha_se'])}), R2 {reg['r2']:.2f}")
    print(f"   invested part on SPY: beta {reg_inv['beta']:.2f} (se {reg_inv['beta_se']:.2f}), alpha {P(reg_inv['alpha'])}/wk (se {P(reg_inv['alpha_se'])}), R2 {reg_inv['r2']:.2f}")
    print(f"   mean invested {100 * inv.mean():.0f}%; mean trailing beta of the names {np.mean([r['names_beta'] for r in rows]):.2f}; of the book {np.mean([r['book_beta'] for r in rows]):.2f}")
    print("B. week | book | SPY | alpha | cash | beta | sector | selection | booking | inv | pct frozen | pct sector")
    for r in rows:
        print(f"   {r['week']} | {P(r['book'])} | {P(r['spy'])} | {P(r['alpha'])} | {P(r['cash'])} | {P(r['beta'])} | {P(r['sector'])} | "
              f"{P(r['selection'])} | {P(r['booking'])} | {100 * r['invested']:.0f}% | {100 * r['pct_frozen']:.0f} | {100 * r['pct_sector']:.0f}")
    print("   sum   | " + " | ".join(f"{k} {P(tot[k])}" for k in ("alpha",) + terms))
    for k in terms:
        xs = [r[k] for r in rows]
        print(f"   {k}: mean {P(np.mean(xs))}/wk, t {tstat(xs):.2f}; up weeks {P(sum(r[k] for r in rows if r['spy'] > 0))}, down weeks {P(sum(r[k] for r in rows if r['spy'] <= 0))}")
    sponsors = sorted({p["sponsor"] for p in pick_rows})
    spo = {}
    print("   by sponsor (weighted contribution, summed) and per pick:")
    for s in sponsors:
        ps = [p for p in pick_rows if p["sponsor"] == s]
        c = {k: float(sum(r["by_sponsor"].get(s, {}).get(k, 0.0) for r in rows)) for k in ("beta", "sector", "selection")}
        sel = [p["selection_term"] for p in ps]
        sec = [p["sector_term"] for p in ps]
        vs = [p["vs_spy"] for p in ps]
        spo[s] = {"picks": len(ps), "contrib": c, "mean_weight": float(np.mean([p["weight"] for p in ps])),
                  "mean_beta": float(np.mean([p["beta"] for p in ps])),
                  "selection_per_pick": float(np.mean(sel)), "selection_t": tstat(sel),
                  "sector_per_pick": float(np.mean(sec)), "sector_t": tstat(sec),
                  "vs_spy_per_pick": float(np.mean(vs)), "vs_spy_t": tstat(vs)}
        print(f"   {s}: {len(ps)} picks, mean beta {spo[s]['mean_beta']:.2f}; contribution beta {P(c['beta'])}, sector {P(c['sector'])}, selection {P(c['selection'])}; "
              f"per pick vs SPY {P(np.mean(vs))} (t {tstat(vs):.2f}), sector {P(np.mean(sec))} (t {tstat(sec):.2f}), selection {P(np.mean(sel))} (t {tstat(sel):.2f})")
    pf = np.array([r["pct_frozen"] for r in rows])
    ps_ = np.array([r["pct_sector"] for r in rows])
    z = lambda m: (m - 0.5) * math.sqrt(12 * n)  # noqa: E731
    print(f"C. dartboard: mean percentile vs the frozen universe {100 * pf.mean():.0f} (z {z(pf.mean()):.2f}); sector-matched {100 * ps_.mean():.0f} (z {z(ps_.mean()):.2f}); "
          f"mean weekly book {P(book.mean())}, frozen dartboard {P(np.mean([r['dart_frozen_mean'] for r in rows]))}, sector-matched {P(np.mean([r['dart_sector_mean'] for r in rows]))}")
    if no_beta:
        print("   beta set to 1 (short history):", no_beta)
    print("   max |check|:", max(abs(r["check"]) for r in rows))
    out = {"weeks": n, "cum_book": cum_book, "cum_spy": cum_spy, "regression": reg, "regression_invested": reg_inv,
           "totals": tot, "rows": rows, "sponsors": spo, "picks": pick_rows, "no_beta": no_beta,
           "dartboard": {"frozen_mean_pct": float(pf.mean()), "frozen_z": z(pf.mean()),
                         "sector_mean_pct": float(ps_.mean()), "sector_z": z(ps_.mean())},
           "by_hand_sectors": BY_HAND}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=float)
        fh.write("\n")
    print(f"wrote {OUT.relative_to(lab.ROOT)}")


if __name__ == "__main__":
    main()
