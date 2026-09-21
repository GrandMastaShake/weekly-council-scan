#!/usr/bin/env python3
"""A live week for Council v2: the members' fifteen, recorded before the week closes.

For the week that has not closed yet, with nothing later than the Friday
before its Monday:

  build LABEL DIR    Cecil's folder (the week's synthesis and his value table)
                     and the week's sheet, from the repo as it stood just
                     before that Monday's Council report
  record LABEL DIR   the fifteen: Ophelia's five from the week before (held a
                     week late, the owner's what-if), Cecil's five from
                     DIR/LABEL/cecil/result.json, and Marky's channel five,
                     computed here on prices up to the Friday before. A name
                     reporting inside the week is dropped. Written to
                     results/live/LABEL.json, which is committed before the week
                     closes.
  score LABEL        after that Friday's close: each member's five and all
                     fifteen, equal-weighted, Monday open to Friday close,
                     against SPY and against random books from the 111.

    python lab/live_week.py build 2026-09-21 DIR
    python lab/live_week.py record 2026-09-21 DIR
    python lab/live_week.py score 2026-09-21
"""
from __future__ import annotations

import argparse
import bisect
import json
import random
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_room_v2 as v2  # noqa: E402
import engine_lab as lab  # noqa: E402

LIVE = lab.RESULTS / "live"


def _monday(label):
    d = lab._d(label)
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def _live(label, data):
    """data() -- the real v2._data -- narrowed to the live week. Its prices end
    at the last closed Friday, which is the Friday before the live week's Monday."""
    weeks, names, raw, adj = data()
    W = _monday(label)
    last = max(r["date"] for s in raw.values() for r in s.rows[-1:])
    if last >= W:
        raise SystemExit(f"prices reach {last}, inside the live week; refusing")
    return [(label, W, None)], names, raw, adj


def build(label, out_dir):
    real = v2._data
    v2._data = lambda: _live(label, real)
    try:
        v2.build(out_dir)
    finally:
        v2._data = real


def _blackout(label, names):
    from scan_pipeline.fetch_market_data import _business_days_between
    W = _monday(label)
    F = lab._plus(W, -3)                          # the Friday before
    cal = lab.earnings_calendar(names)
    out = {}
    for t in names:
        nxt = lab._next_report(cal.get(t), F)
        etd = _business_days_between(F, nxt) if nxt else None
        if etd is not None and 0 <= etd <= 5:
            out[t] = nxt
    return out


def marky_five(label):
    """Marky's channel five for the live week, on prices up to the Friday before."""
    import pass4_marky as p4
    from scan_pipeline.config.tickers import COUNCIL_WATCHLIST
    W = _monday(label)
    real = lab.download
    lab.download = lambda tickers, adjusted, end, start: real(tickers, adjusted, min(end, W), start)
    try:
        cal = lab.earnings_calendar(list(COUNCIL_WATCHLIST))
        row = p4.replay([(label, W, None)], list(COUNCIL_WATCHLIST), v2.COUNCIL_START, cal, ("channel",))[0]
    finally:
        lab.download = real
    keep = ("ticker", "score", "z", "slope_year", "hist_rising", "macd_above_zero")
    return [{k: t[k] for k in keep if k in t} for t in row["channel"]["top"]]


def marky_turn_five(label):
    """The owner's reading of Marky (2026-09-21): only pullbacks whose weekly
    MACD is turning up. A strict weekly crossover (histogram from <= 0 to > 0)
    is rare -- three of 108 stocks on 2026-09-18, none in a rising channel -- so
    this variant takes qualifying names whose histogram rose this week, ranked
    by the same score, deeper pullback first on ties."""
    from scan_pipeline.engines.marky import channel_facts
    from scan_pipeline.fetch_market_data import _aggregate_weekly
    weeks, names, raw, adj = _live(label, v2._data)
    W = weeks[0][1]
    black = _blackout(label, names)
    rows = []
    for t in names:
        if t not in raw or t in black:
            continue
        f = channel_facts([h.close for h in _aggregate_weekly(raw[t].before(W, 400))])
        if f and f["qualifies"] and f["hist_rising"]:
            f.update(ticker=t, score=f["position_score"] + f["trend_score"] + f["macd_score"])
            rows.append(f)
    rows.sort(key=lambda f: (-f["score"], f["z"]))
    keep = ("ticker", "score", "z", "slope_year", "hist_rising", "macd_above_zero")
    return [{k: f[k] for k in keep} for f in rows[:5]]


def record(label, out_dir):
    from scan_pipeline.config.tickers import COUNCIL_WATCHLIST
    prev = lab._plus(_monday(label), -7)
    prev_dir = lab.RESULTS / "room_v2" / prev
    ophelia = json.loads((prev_dir / "ophelia/pass3/result.json").read_text(encoding="utf-8"))
    cecil = json.loads((Path(out_dir) / label / "cecil/result.json").read_text(encoding="utf-8"))
    marky = marky_five(label)
    turn = marky_turn_five(label)
    fives = {"Ophelia": [p["ticker"].upper() for p in ophelia["picks"]][:5],
             "Cecil": [p["ticker"].upper() for p in cecil["picks"]][:5],
             "Marky": [t["ticker"] for t in marky]}
    black = _blackout(label, sorted(set(COUNCIL_WATCHLIST)))
    dropped = {m: [t for t in ts if t in black] for m, ts in fives.items()}
    fives = {m: [t for t in ts if t not in black] for m, ts in fives.items()}
    union = list(dict.fromkeys(fives["Ophelia"] + fives["Cecil"] + fives["Marky"]))
    doc = {"week": label, "monday": _monday(label),
           "recorded": datetime.now().astimezone().isoformat(timespec="seconds"),
           "rule": "picks use nothing after the Friday before the Monday; scored Monday open to Friday close",
           "members": {
               "Ophelia": {"from_week": prev, "picks": fives["Ophelia"],
                           "why": {p["ticker"].upper(): p["why"] for p in ophelia["picks"]}},
               "Cecil": {"picks": fives["Cecil"], "why": {p["ticker"].upper(): p["why"] for p in cecil["picks"]},
                         "summary": cecil.get("summary", "")},
               "Marky": {"picks": fives["Marky"], "chart": marky}},
           "dropped_for_earnings": {m: {t: black[t] for t in ts} for m, ts in dropped.items() if ts},
           "all15": [{"ticker": t, "weight": round(1 / len(union), 6),
                      "backers": [m for m in fives if t in fives[m]]} for t in union],
           "variants": {"Marky, MACD turning up": {"picks": [t["ticker"] for t in turn], "chart": turn}}}
    LIVE.mkdir(parents=True, exist_ok=True)
    with open(LIVE / f"{label}.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for m in fives:
        print(f"  {m:<8} {', '.join(fives[m])}" + (f"   (dropped for earnings: {', '.join(dropped[m])})"
                                                   if dropped[m] else ""))
    print(f"  all {len(union)}: {', '.join(union)}")
    print(f"  variant, Marky with MACD turning up: {', '.join(t['ticker'] for t in turn)}")


def _span(s, first_day, fri):
    """First open on or after first_day to the last close on or before fri."""
    lo = bisect.bisect_left(s.dates, first_day)
    hi = bisect.bisect_right(s.dates, fri)
    return s.rows[hi - 1]["close"] / s.rows[lo]["open"] - 1.0 if lo < hi else None


def score(label):
    """Two windows: from Monday's open, like every other score in the lab, and
    from Tuesday's open, which starts after the record was committed (the
    2026-09-21 record went in Monday evening, after the session)."""
    doc = json.loads((LIVE / f"{label}.json").read_text(encoding="utf-8"))
    weeks, names, raw, adj = v2._data()
    W = doc["monday"]
    fri = lab._plus(W, 4)
    if adj["SPY"].rows[-1]["date"] < fri:
        raise SystemExit(f"{label}: Friday {fri} has not closed in the price data yet")
    black = _blackout(label, names)
    books = {m: v["picks"] for m, v in doc["members"].items()}
    books["all 15"] = [x["ticker"] for x in doc["all15"]]
    books.update({name: v["picks"] for name, v in doc.get("variants", {}).items()})
    # A variant named after the session (the owner's picks) counts only from its window.
    only = {name: v["only_from"] for name, v in doc.get("variants", {}).items() if v.get("only_from")}
    doc["score"] = {"scored": datetime.now().astimezone().isoformat(timespec="seconds")}
    for window, first_day in (("from Monday's open", W), ("from Tuesday's open", lab._plus(W, 1))):
        rets = {t: _span(adj[t], first_day, fri) for t in names if t in adj and t not in black}
        rets = {t: r for t, r in rets.items() if r is not None}
        pool, spy = sorted(rets), _span(adj["SPY"], first_day, fri)
        out = {}
        print(f"  {window}: SPY {spy*100:+.2f}%")
        for name, ts in books.items():
            if name in only and only[name] not in window:
                continue
            ts = [t for t in ts if t in rets]
            r = statistics.fmean(rets[t] for t in ts)
            rng = random.Random(f"{lab.SEED}-{W}-live-{window}-{name}")
            draws = [statistics.fmean(rets[t] for t in rng.sample(pool, len(ts))) for _ in range(lab.RANDOM_DRAWS)]
            out[name] = {"ret": r, "vs_spy": r - spy, "vs_random": r - statistics.fmean(draws),
                         "pctile": sum(1 for x in draws if x < r) / len(draws),
                         "names": {t: rets[t] for t in ts}}
            print(f"    {name:<24} {r*100:+6.2f}%  vs SPY {(r-spy)*100:+6.2f}%  vs random "
                  f"{out[name]['vs_random']*100:+6.2f}%  pctile {out[name]['pctile']:.0%}")
        doc["score"][window] = {"spy": spy, "books": out}
    with open(LIVE / f"{label}.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False, default=float)
        fh.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("build", "record", "score"))
    ap.add_argument("label")
    ap.add_argument("dir", nargs="?")
    a = ap.parse_args(argv)
    if a.command == "build":
        build(a.label, a.dir)
    elif a.command == "record":
        record(a.label, a.dir)
    else:
        score(a.label)


if __name__ == "__main__":
    main()
