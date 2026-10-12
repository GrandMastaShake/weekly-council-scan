#!/usr/bin/env python3
"""Pass 26 -- Cecil's value net of rate exposure (registered in lab/README.md, cebc16e).

Captures Cecil's scored table each week as Pass 12 and Pass 19 do (the engine's legs, point-in-time P/E), adds each name's rate beta
(slope of its weekly returns on the weekly change in the 10-year yield over the trailing 52 weeks before the Monday) and re-ranks:

  as is      Pass 12's five (the engine's own ranking)
  residual   the five largest residuals of the table's total score regressed on rate beta, across the tradeable names, that week
  capped     the five highest scores among names whose absolute rate beta is under the cross-section's median

The S&P 500 as of 2024-09 decides. Decisive: a variant helps if its paired clipped edge over as is is at least +0.10%/wk with
the lab's paired t of 2 or more and both halves positive.

    python lab/pass26_cecil_rates.py
    python lab/pass26_cecil_rates.py smoke
"""
from __future__ import annotations

import json
import pickle
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass7_combos as p7  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass10_sectors as p10  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402
import pass12_cecil_legs as p12  # noqa: E402
import pass15_exits as p15  # noqa: E402
import pass19_cecil_trap as p19  # noqa: E402
import pass20_regimes as p20  # noqa: E402

BASE, RESID, CAPPED = "as is", "residual", "capped"
VARIANTS = (BASE, RESID, CAPPED)
TRAIL = 52
MIN_OBS = 40
MIN_EDGE = 0.001
RISE_BP = 0.20          # percentage points: the 10-year up 20 basis points over four weeks
NW_LAGS = 3


def week_ends(spy):
    """The last trading date of each ISO week in SPY's tape."""
    last = {}
    for d in spy.dates:
        y, w, _ = datetime.strptime(d, "%Y-%m-%d").isocalendar()
        last[(y, w)] = d
    return sorted(last.values())


def close_on_or_before(series, day):
    return series.last_close_before(lab._plus(day, 1))


def weekly_changes(series, ends, diff):
    """{week-end date: return (or yield change if diff)} against the previous week-end."""
    out, prev = {}, None
    for e in ends:
        c = close_on_or_before(series, e)
        if c is not None and prev is not None:
            out[e] = (c - prev) if diff else (c / prev - 1.0)
        prev = c
    return out


def rate_beta(stock, tnx, ends_before):
    window = ends_before[-TRAIL:]
    xs = [tnx[e] for e in window if e in tnx and e in stock]
    ys = [stock[e] for e in window if e in tnx and e in stock]
    if len(xs) < MIN_OBS:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    var = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var if var > 0 else None


def ols_residuals(xs, ys):
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    var = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var if var > 0 else 0.0
    a = my - b * mx
    return [y - a - b * x for x, y in zip(xs, ys)]


def captured_tables(names, weeks, cal, tag):
    path = lab.CACHE / f"pass26_tables_{tag}_{len(weeks)}.pkl"
    if path.exists():
        with open(path, "rb") as fh:
            return pickle.load(fh)
    cap = {}
    lab.run(verbose=False, knobs=dict(lab.VARIANTS3["base"], pe_builder=p11.pe_builder), capture=cap,
            weeks=weeks, start=lab.HISTORY_DATA_START, earnings=cal, names=names)
    tables = {W: cap[W]["cecil"] for _, W, _ in weeks}
    with open(path, "wb") as fh:
        pickle.dump(tables, fh)
    return tables


def total(s):
    return s["value_score"] + s["quality_score"] + s["safety_score"]


def key(s):
    return (-(s["pe"] if s["pe"] is not None else 999.0), s["weekly_return"])


def run_week(W, table, tradeable, betas):
    tset = set(tradeable)
    rows = [s for s in table if s["ticker"] in tset]
    order = p19.order_of(table, tset)
    withb = [s for s in rows if betas.get(s["ticker"]) is not None]
    out = {BASE: order[:p7.TOP]}
    if len(withb) >= 3 * p7.TOP:
        res = ols_residuals([betas[s["ticker"]] for s in withb], [total(s) for s in withb])
        ranked = sorted(zip(res, withb), key=lambda r: r[1]["ticker"])
        ranked.sort(key=lambda r: (r[0],) + key(r[1]), reverse=True)
        out[RESID] = [s["ticker"] for _, s in ranked[:p7.TOP]]
        med = statistics.median(abs(betas[s["ticker"]]) for s in withb)
        low = {s["ticker"] for s in withb if abs(betas[s["ticker"]]) < med}
        out[CAPPED] = [t for t in order if t in low][:p7.TOP]
    else:
        out[RESID] = out[CAPPED] = out[BASE]
    return out, len(withb), len(rows)


def _pct(x):
    return "--" if x is None else f"{x * 100:+.3f}%"


def _num(x):
    return "--" if x is None else f"{x:+.2f}"


def paired_summary(rows, name, flagged=None):
    p = p10.paired(rows, rows, name, BASE)
    if flagged is not None:
        d = [r["books"][name]["clipped"]["edge"] - r["books"][BASE]["clipped"]["edge"] for r in rows if r["rising"] == flagged]
        p["flagged_weeks"] = len(d)
        p["flagged_mean"] = statistics.fmean(d) if d else None
        p["flagged_t"] = lab._tstat(d) if len(d) > 2 else None
    p["helps"] = bool(p["mean"] >= MIN_EDGE and p["t"] >= 2 and p["halves"] and all(h > 0 for h in p["halves"]))
    return p


def main(smoke=False):
    U = p9.universes()
    names = p9.sp500_asof()
    allweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    hweeks = allweeks[:6] if smoke else allweeks
    cal = lab.earnings_calendar(names)
    tickers = sorted(set(names) | set(p19.ETFS)) + [x for x in lab.EXTRA if x not in names]
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, p20.END, p4.HIST_START)).items()}
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, p20.END, p4.HIST_START)).items()}
    # always the full 96 weeks: lab.run then reads the 2026-07-11 price cache that Pass 19 used (a shorter window downloads fresh bars,
    # and Yahoo's unadjusted CTVA now carries the 2026 separation's adjustment, which turns its P/E from 21 into 3)
    tables = captured_tables(names, allweeks, cal, "hist")
    ends = week_ends(raw["SPY"])
    tnx = weekly_changes(raw["^TNX"], ends, diff=True)
    level = {e: close_on_or_before(raw["^TNX"], e) for e in ends}
    stock = {t: weekly_changes(adj[t], ends, diff=False) for t in names if t in adj}
    old = {r["week"]: r["five"] for r in p20.load_rows(p11.CLEAN, "hist", len(allweeks))}
    rows = []
    for label, W, _ in hweeks:
        before = [e for e in ends if e < W]
        betas = {t: rate_beta(stock[t], tnx, before) for t in stock}
        tradeable = p10.pool(names, raw, cal, W)
        fives, nb, nt = run_week(W, tables[W], tradeable, betas)
        assert fives[BASE] == old[label], f"{label}: as is does not match Pass 19's five"
        rising = len(before) >= 5 and level[before[-1]] is not None and level[before[-5]] is not None and level[before[-1]] - level[before[-5]] >= RISE_BP
        books = {n: p7.equal(f) for n, f in fives.items()}
        scored = p7.score_week(books, adj, W, tradeable, f"p26-{label}")
        mb = [abs(betas[t]) for t in fives[BASE] if betas.get(t) is not None]
        rows.append({"week": label, "W": W, "five": fives[BASE], "fives": fives, "books": scored, "rising": bool(rising),
                     "with_beta": nb, "tradeable": nt,
                     "beta_of_five": {n: (statistics.fmean(abs(betas[t]) for t in f if betas.get(t) is not None) if any(betas.get(t) is not None for t in f) else None)
                                      for n, f in fives.items()}})
    summ = {n: p10.summarize(rows, n) for n in VARIANTS}
    pairs = {n: paired_summary(rows, n, flagged=True) for n in (RESID, CAPPED)}
    for n in (RESID, CAPPED):
        pairs[n]["same_five"] = statistics.fmean(1.0 if set(r["fives"][n]) == set(r["fives"][BASE]) else 0.0 for r in rows)
        pairs[n].update(p19.same_returns(rows, n, BASE))
    print(f"\n  Cecil on the S&P 500 as of 2024-09, {len(rows)} weeks; names with a rate beta {statistics.fmean(r['with_beta'] / r['tradeable'] for r in rows):.0%} of the tradeable pool; "
          f"rising-rate weeks (10-year up 20 bp over four weeks): {sum(r['rising'] for r in rows)}")
    print(f"  {'variant':<10}{'edge/wk':>9}{'t':>7}{'ret/wk':>8}{'weekly SD':>11}{'max DD':>8}{'|beta| of the five':>20}   paired vs as is")
    for n in VARIANTS:
        x = summ[n]
        b = statistics.fmean(r["beta_of_five"][n] for r in rows if r["beta_of_five"][n] is not None)
        tail = ""
        if n in pairs:
            p = pairs[n]
            tail = (f"   {p['mean']*100:+.3f}%/wk (t {p['t']:+.2f}, halves {p['halves'][0]*100:+.3f}/{p['halves'][1]*100:+.3f}; same five {p['same_five']:.0%}) "
                    f"rising weeks {_pct(p['flagged_mean'])} (t {_num(p['flagged_t'])}, n {p['flagged_weeks']}); returns {p['ret_mean']*100:+.3f}% (t {p['ret_t']:+.2f})  -> {'HELPS' if p['helps'] else 'no'}")
        print(f"  {n:<10}{x['edge']*100:+8.3f}%{x['t']:+7.2f}{x['mean_ret']*100:+7.3f}%{x['sd']*100:10.2f}%{x['max_dd']*100:+7.1f}%{b:>18.2f}{tail}")
    result = {"registered": "cebc16e", "weeks": len(rows), "summary": summ, "paired": pairs,
              "rising_weeks": sum(r["rising"] for r in rows), "verdicts": {n: pairs[n]["helps"] for n in (RESID, CAPPED)},
              "week_rows": [{k: v for k, v in r.items() if k != "books"} for r in rows]}
    path = lab.CACHE / "pass26.smoke.json" if smoke else lab.RESULTS / "pass26_cecil_rates.json"
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"  wrote {path}")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
