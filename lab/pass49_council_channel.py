#!/usr/bin/env python3
"""Pass 49 -- the channel screen as the Council's universe.

Production's engine code replayed every Monday from 2024-06-03, with and
without the channel screen as the names the engines may scan, on the lab's
basis (Monday open to Friday close, adjusted, cash at zero).

Registered in lab/README.md (Pass 49) before any run.

    python lab/pass49_council_channel.py          # the history
    python lab/pass49_council_channel.py smoke    # plumbing: the last eight weeks
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import channel_universe as cu  # noqa: E402
import pass32_stop_random as p32  # noqa: E402

FIRST = "2024-06-03"
OUT = lab.RESULTS / "pass49_council_channel.json"


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    import forward as fwd
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
    names = sorted(set(STOCK_UNIVERSE))
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7 if today.weekday() < 5 else today.weekday())
    weeks, d = [], date.fromisoformat(FIRST)
    while d <= last_monday:
        weeks.append((d.isoformat(), d.isoformat(), None))
        d += timedelta(days=7)
    if smoke:
        weeks = weeks[-8:]
    cal = lab.earnings_calendar(names, max_age_days=6)
    start = lab._plus(weeks[0][1], -100)
    log = {}
    arms = {}
    for arm, extra in (("engines, whole universe", {}), ("engines, channel universe", {"universe_filter": cu.make_filter(names, log)})):
        arms[arm] = lab.run(verbose=False, knobs=dict(extra, pe_builder=fwd._pe_builder), weeks=weeks, start=start, earnings=cal)
        print(f"  replayed {arm}: {len(arms[arm])} weeks", flush=True)
    lab.run(verbose=False, knobs={}, weeks=weeks[-1:], start=start, earnings=cal)          # knobs back to production

    # every screen name, and every name, held equal weight on the same basis
    end = lab._plus(weeks[-1][1], 5)
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(sorted(set(names)) + lab.EXTRA, True, end, start)).items()}

    def ew(tickers, W):
        rs = [adj[t].week_return(W) for t in tickers if t in adj]
        rs = [r for r in rs if r is not None]
        return statistics.fmean(rs) if rs else 0.0
    rows = []
    for a, b in zip(arms["engines, whole universe"], arms["engines, channel universe"]):
        W = a["monday"]
        lg = log.get(W, {"passed": 0, "fallback": True, "names": []})
        spy = a["spy_ret"]
        rows.append({"monday": W, "spy": spy, "alpha_whole": a["alpha"], "alpha_channel": b["alpha"],
                     "invested_whole": a["invested"], "invested_channel": b["invested"],
                     "book_whole": [x["ticker"] for x in a["book"]], "book_channel": [x["ticker"] for x in b["book"]],
                     "passed": lg["passed"], "fallback": lg["fallback"],
                     "alpha_screen_equal": (ew(lg["names"], W) - spy) if lg["names"] and not lg["fallback"] else None,
                     "alpha_universe_equal": ew(names, W) - spy})

    def block(rs):
        d_ = [r["alpha_channel"] - r["alpha_whole"] for r in rs]
        scr = [r["alpha_screen_equal"] for r in rs if r["alpha_screen_equal"] is not None]
        return {"weeks": len(rs), "alpha_whole": statistics.fmean(r["alpha_whole"] for r in rs),
                "alpha_channel": statistics.fmean(r["alpha_channel"] for r in rs),
                "alpha_whole_t": p32.tstat([r["alpha_whole"] for r in rs]),
                "alpha_channel_t": p32.tstat([r["alpha_channel"] for r in rs]),
                "difference": statistics.fmean(d_), "difference_t": p32.tstat(d_),
                "weeks_channel_better": sum(1 for x in d_ if x > 0), "weeks_differed": sum(1 for x in d_ if x != 0),
                "alpha_screen_equal": statistics.fmean(scr) if scr else None,
                "alpha_screen_equal_t": p32.tstat(scr) if len(scr) > 2 else None,
                "alpha_universe_equal": statistics.fmean(r["alpha_universe_equal"] for r in rs),
                "spy_week": statistics.fmean(r["spy"] for r in rs)}
    half = len(rows) // 2
    out = {"generated": today.isoformat(), "first": rows[0]["monday"], "last": rows[-1]["monday"], "universe": len(names),
           "all": block(rows), "first_half": block(rows[:half]), "second_half": block(rows[half:]),
           "median_passed": statistics.median(r["passed"] for r in rows),
           "min_passed": min(r["passed"] for r in rows), "max_passed": max(r["passed"] for r in rows),
           "fallback_weeks": sum(1 for r in rows if r["fallback"]), "rows": rows}

    def P(x, d=3):
        return "   --" if x is None else f"{100 * x:+.{d}f}%"
    print(f"{len(rows)} weeks {out['first']} .. {out['last']}; universe {len(names)}; passed median {out['median_passed']} "
          f"(min {out['min_passed']}, max {out['max_passed']}); fallback weeks {out['fallback_weeks']}")
    for k in ("all", "first_half", "second_half"):
        b = out[k]
        print(f"{k:12} n {b['weeks']:3}  engines whole {P(b['alpha_whole'])} (t {b['alpha_whole_t']:+.2f})  engines channel {P(b['alpha_channel'])} "
              f"(t {b['alpha_channel_t']:+.2f})  difference {P(b['difference'])} (t {b['difference_t']:+.2f}), better in {b['weeks_channel_better']}/{b['weeks_differed']}  "
              f"| screen equal {P(b['alpha_screen_equal'])}  universe equal {P(b['alpha_universe_equal'])}  SPY/wk {P(b['spy_week'])}")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1, default=float)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
