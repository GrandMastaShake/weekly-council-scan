#!/usr/bin/env python3
"""Spot check 2: Ophelia a week late, and each member's bottom three.

Registered in lab/README.md before any number was computed.

Council weeks (07-27 to 09-14, the weeks with a week before them): each
member's bottom three against its top two, and the nine-name pool -- Ophelia's
bottom three from the week before, Cecil's and Marky's from the week itself --
against random nine-name books and against all fifteen. Every book is
equal-weighted, Monday open to Friday close, and a name reporting that week is
dropped (the earnings blackout).

History (Pass 5's 96 pre-Council weeks): Marky's #3-#5 against his #1-#2,
paired by week. The only part of the idea his mechanical ranking lets us test.

    python lab/whatif_check.py [DIR]    # DIR defaults to lab/results/room_v2
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_room_v2 as v2  # noqa: E402
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402


def _ordered_fives(d, marky_top):
    """Each member's five in its own order: Marky by score, the others as listed."""
    def picks(p):
        return [str(x["ticker"]).upper() for x in json.loads(p.read_text(encoding="utf-8"))["picks"]][:v2.TOP]
    return {"Ophelia": picks(d / "ophelia/pass3/result.json"), "Cecil": picks(d / "cecil/result.json"),
            "Marky": [t["ticker"] for t in marky_top.get(d.name, [])]}


def council(base):
    weeks, names, raw, adj = v2._data()
    cal = lab.earnings_calendar(names)
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    marky = v2._marky_top()
    rows, prev = [], None
    for label, W, _ in weeks:
        d = base / label
        if not (d / "ophelia/pass3/result.json").exists():
            continue
        fives = _ordered_fives(d, marky)
        F = _aggregate_weekly(raw["SPY"].before(W, 92))[-1].date
        blackout = set()
        for t in names:
            nxt = lab._next_report(cal.get(t), F) if t in raw else None
            etd = _business_days_between(F, nxt) if nxt else None
            if etd is not None and 0 <= etd <= 5:
                blackout.add(t)
        rets = {t: adj[t].week_return(W) for t in names if t in adj}
        rets = {t: r for t, r in rets.items() if r is not None and t not in blackout}
        spy = adj["SPY"].week_return(W) or 0.0
        if prev is not None:
            def ew(ts):
                ts = [t for t in dict.fromkeys(ts) if t in rets]
                return (statistics.fmean(rets[t] for t in ts), len(ts)) if ts else (None, 0)
            books = {f"{m} top 2": fives[m][:2] for m in v2.MEMBERS}
            books.update({f"{m} bottom 3": fives[m][2:] for m in v2.MEMBERS})
            books["Ophelia a week late"] = prev["Ophelia"]
            books["the nine"] = prev["Ophelia"][2:] + fives["Cecil"][2:] + fives["Marky"][2:]
            books["all 15"] = sum(fives.values(), [])
            row = {"week": label, "spy": spy}
            pool = sorted(rets)
            for name, ts in books.items():
                r, n = ew(ts)
                if r is None:
                    continue
                rng = random.Random(f"{lab.SEED}-{W}-whatif-{name}")
                draws = [statistics.fmean(rets[t] for t in rng.sample(pool, n)) for _ in range(lab.RANDOM_DRAWS)]
                row[name] = {"names": n, "ret": r, "vs_random": r - statistics.fmean(draws),
                             "pctile": sum(1 for x in draws if x < r) / len(draws)}
            rows.append(row)
        prev = fives
    return rows


def history():
    """Marky's #3-#5 against #1-#2 on Pass 5's history weeks, paired by week."""
    p5 = json.loads((lab.RESULTS / "pass5_marky.json").read_text(encoding="utf-8"))
    hist = p5["weeks"]["history"]
    frozen = lab.frozen_universe()
    weeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    monday = {label: W for label, W, _ in weeks}
    end = lab._plus(weeks[-1][1], 5)
    adj = {t: lab.Series(r) for t, r in
           lab.bars_by_ticker(lab.download(sorted(set(frozen)) + lab.EXTRA, True, end, p4.HIST_START)).items()}
    gaps = []
    for w in hist:
        picks = w["channel"]["picks"]
        W = monday.get(w["week"])
        if W is None or len(picks) < 5:
            continue
        r = {t: adj[t].week_return(W) for t in picks if t in adj}
        if any(r.get(t) is None for t in picks):
            continue
        top2 = statistics.fmean(r[t] for t in picks[:2])
        bottom3 = statistics.fmean(r[t] for t in picks[2:5])
        gaps.append({"week": w["week"], "top2": top2, "bottom3": bottom3, "gap": bottom3 - top2})
    g = [x["gap"] for x in gaps]
    return {"weeks": len(g), "mean_gap": statistics.fmean(g), "t": lab._tstat(g),
            "weeks_bottom_ahead": sum(1 for x in g if x > 0),
            "mean_top2": statistics.fmean(x["top2"] for x in gaps),
            "mean_bottom3": statistics.fmean(x["bottom3"] for x in gaps), "rows": gaps}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    base = Path(argv[0]) if argv else lab.RESULTS / "room_v2"
    rows = council(base)
    names = ["Ophelia top 2", "Ophelia bottom 3", "Cecil top 2", "Cecil bottom 3", "Marky top 2",
             "Marky bottom 3", "Ophelia a week late", "the nine", "all 15"]
    summary = {}
    print(f"  Council weeks ({len(rows)}), edge over random books of the same size:")
    for n in names:
        xs = [r[n] for r in rows if n in r]
        s = {"weeks": len(xs), "mean_vs_random": statistics.fmean(x["vs_random"] for x in xs),
             "t": lab._tstat([x["vs_random"] for x in xs]),
             "weeks_ahead": sum(1 for x in xs if x["vs_random"] > 0),
             "mean_pctile": statistics.fmean(x["pctile"] for x in xs)}
        summary[n] = s
        print(f"    {n:<20} {s['mean_vs_random']*100:+6.2f}%/wk (t {s['t']:+.2f})  ahead {s['weeks_ahead']}/{s['weeks']}"
              f"  pctile {s['mean_pctile']:.0%}")
    h = history()
    print(f"  History ({h['weeks']} weeks), Marky's #3-#5 minus #1-#2: {h['mean_gap']*100:+.2f}%/wk "
          f"(t {h['t']:+.2f}), bottom three ahead {h['weeks_bottom_ahead']}/{h['weeks']}; "
          f"top two {h['mean_top2']*100:+.2f}%/wk, bottom three {h['mean_bottom3']*100:+.2f}%/wk")
    with open(lab.RESULTS / "whatif_check.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"council": {"summary": summary, "weeks": rows}, "history_marky": h}, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main()
