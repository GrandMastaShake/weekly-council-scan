#!/usr/bin/env python3
"""Spot check: do the Council Room picks keep working after their week?

The owner's questions (2026-09-21): how did a week's picks do a month later,
and how did they do the following week? Registered in lab/README.md before any
number was computed. Every set of picks is scored over three windows, all
dividend-adjusted:

  week 1   Monday open -> Friday close, the week it was picked for
  week 2   week 1's Friday close -> the next Friday's close (still holding)
  month    Monday open -> the fourth Friday's close

against SPY and against random books of the same size and weights drawn from
the 111's tradeable names, as in Council Room v2. A window counts only once its
last Friday has closed.

    python lab/hold_check.py [DIR]    # DIR defaults to lab/results/room_v2
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

HORIZONS = ("week1", "week2", "month")


def _row_on_or_before(s, day):
    i = bisect.bisect_right(s.dates, day) - 1
    return s.rows[i] if i >= 0 else None


def window(s, monday, horizon):
    """The return over one window, or None if the data does not reach its last Friday."""
    fri1 = lab._plus(monday, 4)
    if horizon == "week1":
        start_i = bisect.bisect_left(s.dates, monday)
        if start_i >= len(s.rows):
            return None
        start, end_day = s.rows[start_i]["open"], fri1
    elif horizon == "week2":
        r = _row_on_or_before(s, fri1)
        if r is None or r["date"] < monday:
            return None
        start, end_day = r["close"], lab._plus(fri1, 7)
    else:
        start_i = bisect.bisect_left(s.dates, monday)
        if start_i >= len(s.rows):
            return None
        start, end_day = s.rows[start_i]["open"], lab._plus(fri1, 21)
    end = _row_on_or_before(s, end_day)
    if end is None or end["date"] < lab._plus(end_day, -4):
        return None                      # the window has not closed yet
    return end["close"] / start - 1.0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    base = Path(argv[0]) if argv else lab.RESULTS / "room_v2"
    weeks, names, raw, adj = v2._data()
    cal = lab.earnings_calendar(names)
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    marky = v2._marky_top()
    rows, detail = [], {}
    for label, W, council_book in weeks:
        d = base / label
        if not (d / "ophelia/pass3/result.json").exists():
            continue
        fives = v2._fives(d, marky)
        union = sorted(set().union(*fives.values()))
        books = {m: [(t, 1.0 / len(fives[m])) for t in fives[m]] for m in v2.MEMBERS}
        books["all 15"] = [(t, 1.0 / len(union)) for t in union]
        f21 = d / "debate21/final.json"
        if f21.exists():
            books["v2.1 book"] = [(b["ticker"], float(b["weight"]))
                                  for b in json.loads(f21.read_text(encoding="utf-8"))["book"]]
        if council_book:
            books["real Council"] = [(t, float(w)) for t, w in council_book]
        F = _aggregate_weekly(raw["SPY"].before(W, 92))[-1].date
        tradeable = []
        for t in names:
            nxt = lab._next_report(cal.get(t), F) if t in raw else None
            etd = _business_days_between(F, nxt) if nxt else None
            if t in raw and not (etd is not None and 0 <= etd <= 5):
                tradeable.append(t)
        row = {"week": label}
        for h in HORIZONS:
            spy = window(adj["SPY"], W, h)
            if spy is None:
                continue
            rets = {t: window(adj[t], W, h) for t in tradeable if t in adj}
            rets = {t: r for t, r in rets.items() if r is not None}
            pool = sorted(rets)
            row[h] = {"spy": spy}
            for name, book in books.items():
                have = [(t, w) for t, w in book if t in adj and window(adj[t], W, h) is not None]
                if not have:
                    continue
                r = sum(w * window(adj[t], W, h) for t, w in have)
                ws = sorted((w for _, w in have), reverse=True)
                rng = random.Random(f"{lab.SEED}-{W}-hold-{name}-{h}")
                draws = [sum(w * rets[t] for t, w in zip(rng.sample(pool, len(ws)), ws))
                         for _ in range(lab.RANDOM_DRAWS)]
                row[h][name] = {"ret": r, "vs_spy": r - spy, "vs_random": r - statistics.fmean(draws),
                                "pctile": sum(1 for x in draws if x < r) / len(draws)}
        detail[label] = {t: {h: window(adj[t], W, h) for h in HORIZONS}
                         for t in union if t in adj}
        rows.append(row)
    sets = ["Ophelia", "Cecil", "Marky", "all 15", "v2.1 book", "real Council"]
    summary = {}
    print(f"{'':14}" + "".join(f"{h:>30}" for h in HORIZONS))
    for name in sets:
        line, summary[name] = f"{name:<14}", {}
        for h in HORIZONS:
            xs = [r[h][name] for r in rows if h in r and name in r[h]]
            if not xs:
                line += f"{'':>30}"
                continue
            per_week = 4.0 if h == "month" else 1.0
            s = {"weeks": len(xs), "mean_vs_random": statistics.fmean(x["vs_random"] for x in xs),
                 "per_week_vs_random": statistics.fmean(x["vs_random"] for x in xs) / per_week,
                 "weeks_ahead_of_random": sum(1 for x in xs if x["vs_random"] > 0),
                 "mean_pctile": statistics.fmean(x["pctile"] for x in xs),
                 "mean_vs_spy": statistics.fmean(x["vs_spy"] for x in xs)}
            summary[name][h] = s
            line += (f"  {s['mean_vs_random']*100:+6.2f}% ({s['per_week_vs_random']*100:+.2f}/wk) "
                     f"{s['weeks_ahead_of_random']}/{s['weeks']} p{s['mean_pctile']:.0%}")
        print(line)
    with open(lab.RESULTS / "hold_check.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"summary": summary, "weeks": rows, "picks": detail}, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main()
