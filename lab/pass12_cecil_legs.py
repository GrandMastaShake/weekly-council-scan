#!/usr/bin/env python3
"""Pass 12 -- Cecil's legs.

Pass 11 gave the engine Cecil a point-in-time P/E and he turned mildly
positive on the clean list. His score is three legs: value (40 points; P/E
5 -> 40, 25 -> 8, above 25 or negative -> 0, unknown -> 15), quality (30; a
neutral 15 in the lab, there are no point-in-time fundamentals) and safety
(30; 20 for low realized volatility, 10 for a shallow drawdown). So the real
dial is value against safety, and the one quality input that is point in
time, EPS growth from the quarterly history, is missing. This pass captures
his per-name legs once a week (the engine's own table, P/E in) and re-ranks
them under other weights offline; "as is" must reproduce his own five.

  as is          value x1,    safety x1                 Pass 11's Cecil, P/E
  value 60:40    value x1.5,  safety x1.333
  value 70:30    value x1.75, safety x1
  value only     safety x0
  safety only    value x0                               the old lab Cecil
  + growth 20    as is, plus an EPS-growth leg of 20 points
  + growth 30    as is, plus 30

Growth: trailing-four-quarter EPS against the four quarters before, as
known by the Monday; 0 at or below zero growth, full at +30%, neutral (half)
when unknown. Quality stays at weight 1 in every variant (15 +/- a 1-point
hash nudge, the engine's own tie-break). Ties break as the engine breaks
them: score, then the cheaper multiple, then the week's return, then the
ticker. Scored as in Passes 9-11 on the S&P 500 as of 2024-09 (decides) and
the 111 (reported). Registered in lab/README.md before any run.

    python lab/pass12_cecil_legs.py
    python lab/pass12_cecil_legs.py smoke
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_room_v2 as v2  # noqa: E402
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass7_combos as p7  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass10_sectors as p10  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402

BASE = "as is"
VARIANTS = {  # name: (value weight, safety weight, growth points)
    BASE: (1.0, 1.0, 0.0),
    "value 60:40": (1.5, 40.0 / 30.0, 0.0),
    "value 70:30": (1.75, 1.0, 0.0),
    "value only": (1.0, 0.0, 0.0),
    "safety only": (0.0, 1.0, 0.0),
    "+ growth 20": (1.0, 1.0, 20.0),
    "+ growth 30": (1.0, 1.0, 30.0),
}
GROWTH_FULL = 0.30


def _ttm(rows, before, skip=0):
    past = [e for d, e in rows if d < before and e is not None]
    if len(past) < 4 + skip:
        return None
    return sum(past[len(past) - 4 - skip:len(past) - skip])


def growth_score(rows, W, points):
    """The EPS-growth leg: neutral (half) when unknown, 0 at or below zero, full at +30%."""
    if not points:
        return 0.0
    now, prev = _ttm(rows, W), _ttm(rows, W, skip=4)
    if now is None or prev in (None, 0):
        return points / 2.0
    g = (now - prev) / abs(prev)
    return points * max(0.0, min(1.0, g / GROWTH_FULL))


def rerank(table, eps, W, tradeable, wv, ws, gp):
    rows = []
    for s in table:
        if s["ticker"] not in tradeable:
            continue
        total = wv * s["value_score"] + s["quality_score"] + ws * s["safety_score"] + growth_score(eps.get(s["ticker"]) or [], W, gp)
        rows.append((total, -(s["pe"] if s["pe"] is not None else 999.0), s["weekly_return"], s["ticker"]))
    rows.sort(key=lambda r: r[3])
    rows.sort(key=lambda r: (r[0], r[1], r[2]), reverse=True)
    return [r[3] for r in rows[:p7.TOP]]


def replay(uname, names, weeks, start, cal, raw, adj, eps, tag):
    cap = {}
    lab.run(verbose=False, knobs=dict(lab.VARIANTS3["base"], pe_builder=p11.pe_builder), capture=cap,
            weeks=weeks, start=start, earnings=cal, names=names)
    out = []
    for label, W, _ in weeks:
        table = cap[W]["cecil"]
        tradeable = p10.pool(names, raw, cal, W)
        tset = set(tradeable)
        fives = {name: rerank(table, eps, W, tset, *wts) for name, wts in VARIANTS.items()}
        out.append({"week": label, "spy": adj["SPY"].week_return(W) or 0.0, "five": fives[BASE], "fives": fives,
                    "scored": len(table),
                    "books": p7.score_week({n: p7.equal(f) for n, f in fives.items()}, adj, W, tradeable, f"p12-{uname}-{tag}")})
    return out


def reproduces_pass11(rows, uname):
    doc = json.loads((lab.RESULTS / "pass11_cecil_themes.json").read_text(encoding="utf-8"))
    old = {r["week"]: r["fives"]["Cecil, P/E"] for r in doc["cecil"][uname]["history"]["weeks"]}
    hits = [r["fives"][BASE] == old[r["week"]] for r in rows if r["week"] in old]
    return statistics.fmean(hits) if hits else None


def show(title, s, pairs):
    print(f"\n  {title}")
    print(f"  {'variant':<14}{'edge/wk':>9}{'t':>7}{'ahead':>8}{'ret/wk':>8}{'weekly SD':>11}{'max DD':>8}   vs as is")
    for n in VARIANTS:
        x, p = s[n], pairs.get(n)
        tail = f"   {p['mean']*100:+.2f}%/wk (t {p['t']:+.2f}, {p['weeks_better']}/{p['weeks']}; same five {p['same_five']:.0%})" if p else ""
        print(f"  {n:<14}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['ahead']:>5}/{x['weeks']:<3}{x['mean_ret']*100:+7.2f}%"
              f"{x['sd']*100:10.2f}%{x['max_dd']*100:+7.1f}%{tail}")
    print("  by half-year: " + " | ".join(f"{n}: " + ", ".join(f"{k} {v*100:+.2f}" for k, v in s[n]["by_half_year"].items()) for n in VARIANTS))


def main(smoke=False):
    U = p9.universes()
    universes = {p11.CLEAN: p9.sp500_asof(), p9.REFERENCE: U[p9.REFERENCE]}
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cweeks = lab.council_weeks(p9._last_friday())
    if smoke:
        universes, hweeks, cweeks = {p9.REFERENCE: U[p9.REFERENCE]}, hweeks[:3], cweeks[:1]
    end = lab._plus(cweeks[-1][1], 5)
    result = {"variants": {n: list(w) for n, w in VARIANTS.items()}, "growth_full": GROWTH_FULL, "universes": {}}
    for uname, names in universes.items():
        cal = lab.earnings_calendar(names)
        eps = v2.eps_history(sorted(names))
        tickers = sorted(set(names)) + lab.EXTRA
        raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
        print(f"  Cecil on {uname}: {len(names)} names", flush=True)
        hist = replay(uname, names, hweeks, lab.HISTORY_DATA_START, cal, raw, adj, eps, "hist")
        cw = replay(uname, names, cweeks, lab.DATA_START, cal, raw, adj, eps, "council")
        rep = None if smoke else reproduces_pass11(hist, uname)
        out = {"reproduces_pass11_as_is": rep}
        for section, rows, title in (("history", hist, f"Cecil on {uname}: history, {len(hweeks)} weeks"),
                                     ("council", cw, f"Cecil on {uname}: Council weeks, {len(cweeks)} (seen; decide nothing)")):
            s = {n: p10.summarize(rows, n) for n in VARIANTS}
            pairs = {n: p10.paired(rows, rows, n, BASE) for n in VARIANTS if n != BASE}
            for n in pairs:
                pairs[n]["same_five"] = statistics.fmean(1.0 if set(r["fives"][n]) == set(r["fives"][BASE]) else 0.0 for r in rows)
            show(title, s, pairs)
            out[section] = {"summary": s, "paired": pairs, "weeks": rows}
        print(f"  'as is' reproduces Pass 11's Cecil, P/E five: {rep if rep is None else f'{rep:.0%} of weeks'}")
        result["universes"][uname] = out
    if p11.CLEAN in result["universes"]:
        pairs = result["universes"][p11.CLEAN]["history"]["paired"]
        v = {n: bool(p["t"] >= 2 and p["mean"] > 0 and p["halves"] and all(h > 0 for h in p["halves"])) for n, p in pairs.items()}
        result["verdicts"] = v
        print("\n  registered verdicts (history, the clean list): " + "; ".join(f"{n} {'HELPS' if ok else 'no'}" for n, ok in v.items()))
    out = lab.CACHE / "pass12.smoke.json" if smoke else lab.RESULTS / "pass12_cecil_legs.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
