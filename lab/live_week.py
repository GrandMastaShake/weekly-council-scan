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
  warden LABEL       adds the Warden (Pass 8) over the recorded names as a
                     weighted variant.
  engines LABEL      adds the engine Ophelia's five (Pass 9b's lead) on the
                     live 274 and on the 111 as two variants.
  score LABEL        after that Friday's close: each member's five, all
                     fifteen and every variant, Monday open to Friday close,
                     against SPY and against random books of the same weights
                     from the 111. A variant recorded once the week was under
                     way carries `only_from` (the first open after it was
                     recorded) and is scored in that window and later ones.
  score-pending      scores every recorded week that has closed unscored
                     (the Monday task).

    python lab/live_week.py build 2026-09-21 DIR
    python lab/live_week.py record 2026-09-21 DIR
    python lab/live_week.py warden 2026-09-21
    python lab/live_week.py engines 2026-09-21
    python lab/live_week.py score 2026-09-21
    python lab/live_week.py score-pending
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


OPENS = ["Monday's open", "Tuesday's open", "Wednesday's open", "Thursday's open", "Friday's open"]


def _window(added, W):
    """The first session a variant added at `added` may be scored from. Its
    picks use nothing after the Friday before W; but a variant recorded once
    the week is under way starts at the next open after it was recorded:
    before 9:30 ET on a weekday it is that day's open, after it the next
    day's. None means Monday's open (recorded before the week)."""
    day = added.strftime("%Y-%m-%d")
    if day < W:
        return None
    d = (lab._d(day) - lab._d(W)).days
    if added.hour > 9 or (added.hour == 9 and added.minute >= 30):
        d += 1
    if d > 4:
        raise SystemExit(f"the week of {W} has no session left to score from ({added:%A %H:%M})")
    return OPENS[d] if d else None


def _add_variant(label, name, v):
    doc = json.loads((LIVE / f"{label}.json").read_text(encoding="utf-8"))
    added = datetime.now().astimezone()
    v["added"] = added.isoformat(timespec="seconds")
    window = _window(added, doc["monday"])
    if window:
        v["only_from"] = window
    doc.setdefault("variants", {})[name] = v
    with open(LIVE / f"{label}.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return window


def warden(label):
    """Add the Warden (Pass 8: three chairs, sized) to the week's record as a
    weighted variant. Its weights use prices up to the Friday before the
    Monday, so the book itself sees nothing of the week; it is scored from
    the first open after it was recorded (see _window)."""
    import pass7_combos as p7
    import pass8_warden as p8
    doc = json.loads((LIVE / f"{label}.json").read_text(encoding="utf-8"))
    weeks, names, raw, adj = _live(label, v2._data)
    W = weeks[0][1]
    picks = [x["ticker"] for x in doc["all15"]]
    below = p7.spy_below_40w(raw, W)
    book = p8.warden_book(sorted(picks), raw, W, below)
    v = {"book": [[t, round(w, 6)] for t, w in book], "invested": round(sum(w for _, w in book), 4),
         "spy_below_40w": below,
         "rule": "Pass 8: the members' names, inverse 12-week-volatility weights, two a sector, 80% below SPY's 40-week average"}
    window = _add_variant(label, p8.FULL, v)
    print(f"  {p8.FULL}: {len(book)} names, {v['invested']*100:.0f}% invested (SPY below 40-week: {below})"
          + (f", scored from {window}" if window else ""))
    for t, w in sorted(book, key=lambda x: -x[1]):
        print(f"    {t:<6} {w*100:5.1f}%")


def engines(label):
    """Add the engine Ophelia's five for the live week (Pass 9b's lead) as
    two variants: on the 274 the engines scan live, and on the 111's 109
    stocks (the lab's sector fold for the names the engines' map lacks).
    Prices are capped at the week's Monday, so nothing later than the Friday
    before reaches the engine; the earnings blackout is the engines' own."""
    import pass9_universe as p9
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
    U = p9.universes()                                     # installs the sector fold
    W = _monday(label)
    real = lab.download
    lab.download = lambda tickers, adjusted, end, start: real(tickers, adjusted, min(end, W), start)
    try:
        for uname, names in (("live 274", sorted(STOCK_UNIVERSE)), ("the 111", U[p9.REFERENCE])):
            cal = lab.earnings_calendar(names)
            row = lab.run(verbose=False, knobs=lab.VARIANTS3["base"], weeks=[(label, W, None)],
                          earnings=cal, names=names)[0]
            black = _blackout(label, names)
            five = [t for t in row["proposals"]["Ophelia"] if t not in black][:5]
            name = f"Ophelia engine, {uname}"
            window = _add_variant(label, name, {"picks": five, "universe": uname, "names": len(names),
                                                "rule": "Pass 9b: the engine Ophelia's five, equal weights, on this universe"})
            print(f"  {name}: {', '.join(five)}" + (f"  (scored from {window})" if window else ""))
    finally:
        lab.download = real


def add(label, name, specs):
    """Record a book the owner names, as TICKER=PERCENT pairs; the rest is
    cash. `python lab/live_week.py add 2026-09-21 "Owner's book" NUE=20 SPCX=20 ...`"""
    book = []
    for spec in specs:
        t, pct = spec.split("=")
        book.append([t.upper(), round(float(pct) / 100.0, 6)])
    invested = round(sum(w for _, w in book), 4)
    if invested > 1.0 + 1e-9:
        raise SystemExit(f"weights sum to {invested*100:.0f}%")
    window = _add_variant(label, name, {"book": book, "invested": invested,
                                        "rule": "the owner's own book for the week, as given; the rest is cash"})
    print(f"  {name}: {', '.join(f'{t} {w*100:.0f}%' for t, w in book)}; cash {(1-invested)*100:.0f}%"
          + (f"  (scored from {window})" if window else ""))


def cecil(label):
    """Add the engine Cecil's five with a point-in-time P/E (Pass 11) as two
    variants, on the live 274 and on the 111; prices capped at the week's
    Monday, the multiple from the EPS cache as known by the Friday before."""
    import pass9_universe as p9
    import pass11_cecil_themes as p11
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
    U = p9.universes()
    W = _monday(label)
    real = lab.download
    lab.download = lambda tickers, adjusted, end, start: real(tickers, adjusted, min(end, W), start)
    try:
        for uname, names in (("live 274", sorted(STOCK_UNIVERSE)), ("the 111", U[p9.REFERENCE])):
            cal = lab.earnings_calendar(names)
            row = lab.run(verbose=False, knobs=dict(lab.VARIANTS3["base"], pe_builder=p11.pe_builder),
                          weeks=[(label, W, None)], earnings=cal, names=names)[0]
            black = _blackout(label, names)
            five = [t for t in row["proposals"]["Cecil"] if t not in black][:5]
            name = f"Cecil engine with P/E, {uname}"
            window = _add_variant(label, name, {"picks": five, "universe": uname, "names": len(names),
                                                "rule": "Pass 11: the engine Cecil's five with a point-in-time P/E, equal weights"})
            print(f"  {name}: {', '.join(five)}" + (f"  (scored from {window})" if window else ""))
    finally:
        lab.download = real


def score_pending():
    """Score every recorded week whose Friday has closed and that has no
    score yet (the Monday task runs this)."""
    for path in sorted(LIVE.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if "score" in doc:
            continue
        try:
            print(f"{doc['week']}:")
            score(doc["week"])
        except SystemExit as e:
            print(f"  skipped: {e}")


def _span(s, first_day, fri):
    """First open on or after first_day to the last close on or before fri."""
    lo = bisect.bisect_left(s.dates, first_day)
    hi = bisect.bisect_right(s.dates, fri)
    return s.rows[hi - 1]["close"] / s.rows[lo]["open"] - 1.0 if lo < hi else None


def _book(v):
    """A record entry as [(ticker, weight)]: 'book' if it carries weights, else its picks equally."""
    if v.get("book"):
        return [(t, float(w)) for t, w in v["book"]]
    return [(t, 1.0 / len(v["picks"])) for t in v["picks"]]


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
    books = {m: _book(v) for m, v in doc["members"].items()}
    books["all 15"] = _book({"picks": [x["ticker"] for x in doc["all15"]]})
    books.update({name: _book(v) for name, v in doc.get("variants", {}).items()})
    # A recorded book may hold names outside the 111 (the owner's); fetch
    # their prices too. The random pool stays the 111, less its reporters.
    extra = sorted({t for book in books.values() for t, _ in book if t not in adj})
    if extra:
        end = lab._plus(W, 5)
        adj.update({t: lab.Series(r) for t, r in lab.bars_by_ticker(
            lab.download(extra, True, end, v2.COUNCIL_START)).items()})
    # A variant recorded once the week was under way (the owner's picks, the
    # Warden, the engine books) counts only from its own open onward.
    starts = {name: OPENS.index(v["only_from"]) for name, v in doc.get("variants", {}).items() if v.get("only_from")}
    windows = [0] + sorted(set(starts.values()) - {0})
    doc["score"] = {"scored": datetime.now().astimezone().isoformat(timespec="seconds")}
    for d in windows:
        window, first_day = f"from {OPENS[d]}", lab._plus(W, d)
        rets = {t: _span(adj[t], first_day, fri) for t in set(names) | set(extra) if t in adj}
        rets = {t: r for t, r in rets.items() if r is not None}
        pool, spy = sorted(t for t in names if t in rets and t not in black), _span(adj["SPY"], first_day, fri)
        out = {}
        print(f"  {window}: SPY {spy*100:+.2f}%")
        for name, full in books.items():
            if starts.get(name, 0) > d:
                continue
            invested = sum(w for _, w in full)
            book = [(t, w) for t, w in full if t in rets]
            scale = invested / sum(w for _, w in book)      # a name without prices gives its weight to the rest
            book = [(t, w * scale) for t, w in book]
            ws = [w for _, w in book]
            r = sum(w * rets[t] for t, w in book)
            rng = random.Random(f"{lab.SEED}-{W}-live-{window}-{name}")
            draws = [sum(w * rets[t] for t, w in zip(rng.sample(pool, len(ws)), ws)) for _ in range(lab.RANDOM_DRAWS)]
            out[name] = {"ret": r, "vs_spy": r - spy, "vs_random": r - statistics.fmean(draws),
                         "pctile": sum(1 for x in draws if x < r) / len(draws), "invested": invested,
                         "names": {t: rets[t] for t, _ in book}}
            if any(abs(w - ws[0]) > 1e-9 for w in ws):
                out[name]["weights"] = {t: w for t, w in book}
            print(f"    {name:<24} {r*100:+6.2f}%  vs SPY {(r-spy)*100:+6.2f}%  vs random "
                  f"{out[name]['vs_random']*100:+6.2f}%  pctile {out[name]['pctile']:.0%}")
        doc["score"][window] = {"spy": spy, "books": out}
    with open(LIVE / f"{label}.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False, default=float)
        fh.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("build", "record", "warden", "engines", "cecil", "add", "score", "score-pending"))
    ap.add_argument("label", nargs="?")
    ap.add_argument("rest", nargs="*", help="build/record: DIR; add: NAME TICKER=PERCENT ...")
    a = ap.parse_args(argv)
    if a.command == "score-pending":
        score_pending()
        return
    if not a.label:
        ap.error(f"{a.command} needs a week label")
    if a.command == "build":
        build(a.label, a.rest[0])
    elif a.command == "record":
        record(a.label, a.rest[0])
    elif a.command == "warden":
        warden(a.label)
    elif a.command == "engines":
        engines(a.label)
    elif a.command == "cecil":
        cecil(a.label)
    elif a.command == "add":
        add(a.label, a.rest[0], a.rest[1:])
    else:
        score(a.label)


if __name__ == "__main__":
    main()
