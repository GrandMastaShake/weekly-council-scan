#!/usr/bin/env python3
"""Pass 7 -- combos and a fourth chair.

Registered in lab/README.md before any number was computed. Five designs, all
mechanical so the 96 pre-Council weeks can judge them, with the nine Council
weeks on the 111 beside them (seen weeks: reported, decide nothing).

Chairs, five names each, earnings blackout throughout:
  Ophelia, Cecil  the engines as they ran (history, from a baseline replay);
                  the Council Room v2 agents' fives (Council weeks)
  Marky           the channel screen (Pass 5), recomputed with its full ranking
  Dash            NEW, post-earnings drift: names whose market-adjusted earnings
                  reaction (the close before the report to the close of the next
                  session) was in the top fifth of the reactions in the six weeks
                  before the hold, the report at least a session before the
                  Friday; largest reactions first

Designs, each against a baseline:
  Dash alone                 vs random
  Quality pullback           Marky's ranking, only names passing Cecil's value
                             screen (positive trailing EPS, growing, P/E at or
                             below the week's median)      vs Marky alone
  Relay                      half Marky's five, half Ophelia's five from the
                             week before                   vs half each, same week
  Four chairs                a quarter each to Ophelia, Cecil, Marky and Dash
                                                           vs three chairs, a third each
  The Warden                 the four chairs' names, weighted by inverse 12-week
                             volatility, at most two a sector, 80% invested when
                             SPY closed below its 40-week average   vs four chairs

Every book is scored Monday open to Friday close against random books of the
same weights from the week's tradeable names. The primary measure clips each
name's weekly return to +/-20%, a guard against the frozen list's hindsight
(names on it because they ran); the raw measure is reported beside it.

    python lab/pass7_combos.py
"""
from __future__ import annotations

import bisect
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_room_v2 as v2  # noqa: E402
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402

TOP = 5
WINSOR = 0.20
DASH_DAYS = 42
DASH_QUANTILE = 0.80
SECTOR_CAP = 2
RISK_OFF_INVESTED = 0.80
DESIGNS = {  # design: baseline
    "Dash alone": "random",
    "Quality pullback": "Marky alone",
    "Relay": "Marky + Ophelia, same week",
    "Four chairs": "Three chairs",
    "The Warden": "Four chairs",
}


def _clip(r):
    return max(-WINSOR, min(WINSOR, r))


def reactions(adj, cal, names, W, F):
    """{ticker: market-adjusted reaction} for each name's latest report in the
    six weeks before W whose reaction window closed by F."""
    spy, lo, out = adj["SPY"], lab._plus(W, -DASH_DAYS), {}
    for t in names:
        s = adj.get(t)
        if not s:
            continue
        for R in sorted(cal.get(t) or []):
            if not lo <= R <= F:
                continue
            j = bisect.bisect_left(s.dates, R)
            if j < 1 or j >= len(s.rows):
                continue
            k = j + 1 if s.dates[j] == R else j
            if k >= len(s.rows) or s.dates[k] > F:
                continue
            d0, d1 = s.dates[j - 1], s.dates[k]
            i0, i1 = bisect.bisect_left(spy.dates, d0), bisect.bisect_left(spy.dates, d1)
            if i1 >= len(spy.rows) or spy.dates[i0] != d0 or spy.dates[i1] != d1:
                continue
            stock = s.rows[k]["close"] / s.rows[j - 1]["close"] - 1
            market = spy.rows[i1]["close"] / spy.rows[i0]["close"] - 1
            out[t] = stock - market          # later reports overwrite earlier ones
    return out


def dash_five(reacts, tradeable):
    vals = sorted(reacts.values())
    if len(vals) < 10:
        return []
    cut = vals[int(DASH_QUANTILE * (len(vals) - 1))]
    top = [t for t, r in reacts.items() if r >= cut and r > 0 and t in tradeable]
    return sorted(top, key=lambda t: -reacts[t])[:TOP]


def channel_ranking(raw, names, W, tradeable):
    """Marky's channel mode's order: qualifying names by score, deeper pullback first."""
    from scan_pipeline.engines.marky import channel_facts
    from scan_pipeline.fetch_market_data import _aggregate_weekly
    rows = []
    for t in names:
        if t not in raw or t not in tradeable:
            continue
        f = channel_facts([h.close for h in _aggregate_weekly(raw[t].before(W, p4.LONG_DAYS))])
        if f and f["qualifies"]:
            rows.append((f["position_score"] + f["trend_score"] + f["macd_score"], -f["z"], t))
    return [t for _, _, t in sorted(rows, key=lambda x: (-x[0], -x[1], x[2]))]


def value_screen(eps, raw, names, W):
    pe, grow = {}, {}
    for t in names:
        rows = eps.get(t) or []
        ttm, prev = v2._ttm(rows, W), v2._ttm(rows, W, skip=4)
        px = raw[t].last_close_before(W) if t in raw else None
        if ttm and ttm > 0 and px:
            pe[t] = px / ttm
            grow[t] = prev not in (None, 0) and (ttm - prev) / abs(prev) > 0
    if not pe:
        return set()
    med = statistics.median(pe.values())
    return {t for t in pe if grow[t] and pe[t] <= med}


def warden(names, raw, W, spy_below):
    from scan_pipeline.fetch_market_data import _aggregate_weekly
    from scan_pipeline.utils.data_utils import get_sector
    inv = {}
    for t in names:
        wk = _aggregate_weekly(raw[t].before(W, 120)) if t in raw else []
        rets = [h.return_ for h in wk[-12:]]
        sd = statistics.pstdev(rets) if len(rets) >= 4 else None
        if sd:
            inv[t] = 1.0 / sd
    by_sector = {}
    for t in sorted(inv, key=lambda t: -inv[t]):
        by_sector.setdefault(get_sector(t), []).append(t)
    keep = [t for ts in by_sector.values() for t in ts[:SECTOR_CAP]]
    total = sum(inv[t] for t in keep)
    exposure = RISK_OFF_INVESTED if spy_below else 1.0
    return [(t, exposure * inv[t] / total) for t in keep] if total else []


def equal(names):
    names = list(dict.fromkeys(names))
    return [(t, 1.0 / len(names)) for t in names] if names else []


def slices(groups):
    """Separate books: an equal slice per non-empty group, equal within it."""
    groups = [g for g in groups if g]
    w = {}
    for g in groups:
        for t in g:
            w[t] = w.get(t, 0.0) + 1.0 / len(groups) / len(g)
    return sorted(w.items())


def spy_below_40w(raw, W):
    from scan_pipeline.fetch_market_data import _aggregate_weekly
    closes = [h.close for h in _aggregate_weekly(raw["SPY"].before(W, 400))]
    return len(closes) >= 40 and closes[-1] < statistics.fmean(closes[-40:])


def score_week(books, adj, W, pool_names, tag):
    rets = {t: (adj[t].week_return(W) if t in adj else None) for t in set(pool_names) | {t for b in books.values() for t, _ in b}}
    rets = {t: (0.0 if r is None else r) for t, r in rets.items()}
    pool = sorted(pool_names)
    out = {}
    for name, book in books.items():
        if not book:
            continue
        ws = sorted((w for _, w in book), reverse=True)
        res = {"book": [(t, round(w, 4)) for t, w in book], "invested": sum(ws)}
        for kind, f in (("raw", lambda r: r), ("clipped", _clip)):
            r = sum(w * f(rets[t]) for t, w in book)
            rng = random.Random(f"{lab.SEED}-{W}-p7-{tag}-{name}")
            draws = [sum(w * f(rets[t]) for t, w in zip(rng.sample(pool, len(ws)), ws))
                     for _ in range(lab.RANDOM_DRAWS)]
            res[kind] = {"ret": r, "edge": r - statistics.fmean(draws)}
        out[name] = res
    return out


def build_books(fives, prev_ophelia, dash, ranking, value_ok, raw, W):
    marky = fives["Marky"]
    books = {
        "Dash alone": equal(dash),
        "Marky alone": equal(marky),
        "Quality pullback": equal([t for t in ranking if t in value_ok][:TOP]),
        "Marky + Ophelia, same week": slices([marky, fives["Ophelia"]]),
        "Three chairs": slices([fives["Ophelia"], fives["Cecil"], marky]),
        "Four chairs": slices([fives["Ophelia"], fives["Cecil"], marky, dash]),
    }
    if prev_ophelia:
        books["Relay"] = slices([marky, prev_ophelia])
    four = sorted({t for g in (fives["Ophelia"], fives["Cecil"], marky, dash) for t in g})
    books["The Warden"] = warden(four, raw, W, spy_below_40w(raw, W))
    return books


def history(builder=build_books):
    """builder(fives, lagged, dash, ranking, value_ok, raw, W) -> {name: book};
    Pass 8 passes its own so the fives, blackouts and Dash are Pass 7's exactly."""
    from scan_pipeline.utils.data_utils import earnings_blackout
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    frozen = lab.frozen_universe()
    cal = lab.earnings_calendar(frozen)
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    rows = lab.run(verbose=False, knobs=lab.VARIANTS3["base"], weeks=hweeks,
                   start=lab.HISTORY_DATA_START, earnings=cal, names=frozen)
    proposals = {r["monday"]: r["proposals"] for r in rows}
    end = lab._plus(hweeks[-1][1], 5)
    tickers = sorted(set(frozen)) + lab.EXTRA
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
    eps = v2.eps_history(frozen)
    p5 = {w["week"]: w["channel"]["picks"] for w in json.loads(
        (lab.RESULTS / "pass5_marky.json").read_text(encoding="utf-8"))["weeks"]["history"]}
    out, prev_o, agree = [], None, []
    for label, W, _ in hweeks:
        short = {t: _aggregate_weekly(raw[t].before(W, p4.SHORT_DAYS)) for t in frozen if t in raw}
        eligible = [t for t in frozen if len(short.get(t, [])) >= lab.MIN_WEEKS]
        F = _aggregate_weekly(raw["SPY"].before(W, p4.SHORT_DAYS))[-1].date
        md = {"stockData": {t: {"earnings_date": (n := lab._next_report(cal.get(t), F)),
                                "earnings_trading_days": _business_days_between(F, n) if n else None}
                            for t in eligible}}
        tradeable = [t for t in eligible if earnings_blackout(md, t) is None]
        tset = set(tradeable)
        ranking = channel_ranking(raw, eligible, W, tset)
        prop = proposals[W]
        fives = {"Ophelia": [t for t in prop["Ophelia"] if t in tset][:TOP],
                 "Cecil": [t for t in prop["Cecil"] if t in tset][:TOP],
                 "Marky": ranking[:TOP]}
        if label in p5:
            agree.append(len(set(fives["Marky"]) & set(p5[label])) / max(1, len(p5[label])))
        dash = dash_five(reactions(adj, cal, eligible, W, F), tset)
        lagged = [t for t in (prev_o or []) if t in tset]     # last week's picks face this week's blackout
        books = builder(fives, lagged, dash, ranking, value_screen(eps, raw, eligible, W), raw, W)
        out.append({"week": label, "spy": adj["SPY"].week_return(W) or 0.0,
                    "books": score_week(books, adj, W, tradeable, "hist")})
        prev_o = fives["Ophelia"]
    return out, statistics.fmean(agree) if agree else None


def council(builder=build_books):
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    weeks, names, raw, adj = v2._data()
    cal = lab.earnings_calendar(names)
    eps = v2.eps_history([t for t in names if t not in ("BTC", "GLD")])
    out, prev_o = [], None
    for label, W, _ in weeks:
        d = lab.RESULTS / "room_v2" / label
        if not (d / "ophelia/pass3/result.json").exists():
            continue
        F = _aggregate_weekly(raw["SPY"].before(W, 92))[-1].date
        black = set()
        for t in names:
            n = lab._next_report(cal.get(t), F) if t in raw else None
            etd = _business_days_between(F, n) if n else None
            if etd is not None and 0 <= etd <= 5:
                black.add(t)
        tradeable = [t for t in names if t in raw and t not in black]
        tset = set(tradeable)
        ranking = channel_ranking(raw, names, W, tset)
        load = lambda p: [str(x["ticker"]).upper() for x in json.loads(p.read_text(encoding="utf-8"))["picks"]][:TOP]  # noqa: E731
        fives = {"Ophelia": [t for t in load(d / "ophelia/pass3/result.json") if t in tset],
                 "Cecil": [t for t in load(d / "cecil/result.json") if t in tset],
                 "Marky": ranking[:TOP]}
        dash = dash_five(reactions(adj, cal, names, W, F), tset)
        lagged = [t for t in (prev_o or []) if t in tset]
        books = builder(fives, lagged, dash, ranking, value_screen(eps, raw, names, W), raw, W)
        out.append({"week": label, "spy": adj["SPY"].week_return(W) or 0.0,
                    "books": score_week(books, adj, W, tradeable, "council")})
        prev_o = fives["Ophelia"]
    return out


def _dd(rets):
    return lab._curve(rets)[1]


def summarize(rows):
    names = sorted({n for r in rows for n in r["books"]})
    s = {}
    for n in names:
        rs = [r["books"][n] for r in rows if n in r["books"]]
        half = len(rs) // 2
        e = [x["clipped"]["edge"] for x in rs]
        s[n] = {"weeks": len(rs), "edge": statistics.fmean(e), "t": lab._tstat(e),
                "ahead": sum(1 for x in e if x > 0),
                "halves": [statistics.fmean(e[:half]), statistics.fmean(e[half:])] if half else None,
                "raw_edge": statistics.fmean(x["raw"]["edge"] for x in rs),
                "raw_t": lab._tstat([x["raw"]["edge"] for x in rs]),
                "sd": statistics.pstdev(x["raw"]["ret"] for x in rs),
                "max_dd": _dd([x["raw"]["ret"] for x in rs]),
                "invested": statistics.fmean(x["invested"] for x in rs)}
    for d, b in DESIGNS.items():
        if d not in s or b == "random" or b not in s:
            continue
        pairs = [(r["books"][d]["clipped"]["edge"], r["books"][b]["clipped"]["edge"])
                 for r in rows if d in r["books"] and b in r["books"]]
        diff = [x - y for x, y in pairs]
        half = len(diff) // 2
        s[d]["vs_baseline"] = {"baseline": b, "mean": statistics.fmean(diff), "t": lab._tstat(diff),
                               "halves": [statistics.fmean(diff[:half]), statistics.fmean(diff[half:])],
                               "weeks_better": sum(1 for x in diff if x > 0), "weeks": len(diff)}
    return s


def verdicts(s):
    v = {}
    for d, b in DESIGNS.items():
        x = s.get(d)
        if not x:
            continue
        if d == "The Warden":
            f = s[b]
            v[d] = (x["sd"] <= 0.9 * f["sd"] and x["max_dd"] > f["max_dd"] and x["vs_baseline"]["t"] > -2)
        elif b == "random":
            v[d] = x["t"] >= 2 and x["edge"] > 0 and all(h > 0 for h in x["halves"])
        else:
            vb = x["vs_baseline"]
            v[d] = vb["t"] >= 2 and vb["mean"] > 0 and all(h > 0 for h in vb["halves"])
    return v


def show(title, s):
    print(f"\n  {title}")
    print(f"  {'book':<28}{'edge/wk':>9}{'t':>7}{'ahead':>8}{'raw edge':>10}{'weekly SD':>11}{'max DD':>8}   vs baseline")
    for n, x in sorted(s.items(), key=lambda kv: list(DESIGNS).index(kv[0]) if kv[0] in DESIGNS else 99):
        vb = x.get("vs_baseline")
        tail = (f"   {vb['mean']*100:+.2f}%/wk (t {vb['t']:+.2f}, {vb['weeks_better']}/{vb['weeks']}) vs {vb['baseline']}"
                if vb else "")
        print(f"  {n:<28}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['ahead']:>5}/{x['weeks']:<3}{x['raw_edge']*100:+9.2f}%"
              f"{x['sd']*100:10.2f}%{x['max_dd']*100:+7.1f}%{tail}")


def main():
    hist, agree = history()
    hs = summarize(hist)
    show(f"History, 96 weeks, frozen universe (Marky recomputed: {agree:.0%} of Pass 5's picks)", hs)
    cw = council()
    cs = summarize(cw)
    show("Council weeks on the 111 (seen weeks: reported, decide nothing)", cs)
    v = verdicts(hs)
    print("\n  registered verdicts (history): " + "; ".join(f"{d} {'PROMISING' if ok else 'no'}" for d, ok in v.items()))
    with open(lab.RESULTS / "pass7_combos.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"designs": DESIGNS, "history": {"summary": hs, "weeks": hist, "marky_agreement": agree},
                   "council": {"summary": cs, "weeks": cw}, "verdicts": v}, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main()
