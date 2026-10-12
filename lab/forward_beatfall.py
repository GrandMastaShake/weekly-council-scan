#!/usr/bin/env python3
"""Pass 30 -- beat-then-fall, the corrected contrast, as a forward test (registered in lab/README.md, 36545ad).

Events are Pass 21's (reaction day, surprise percent, five-day market-adjusted return R5) on the S&P 500 list of 2026-09-22 for reports whose reaction
day is 2026-07-06 or later. A flagged beat has a positive surprise and a streak of 8 or more positive quarters before it; an other beat has a positive
surprise and a streak under 8. Each qualifying reaction week (15+ events, 3+ flagged beats, 3+ other beats) contributes the mean R5 of the flagged beats
minus the mean R5 of the other beats. Events enter the append-only ledger lab/beatfall_events.json once their five-session window has closed.

    python lab/forward_beatfall.py
"""
from __future__ import annotations

import bisect
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass15_exits as p15  # noqa: E402
import pass21_beat_fall as p21  # noqa: E402
import forward_sleeve as fs  # noqa: E402

REGISTERED = "36545ad"
LEDGER = lab.LAB / "beatfall_events.json"
PAGE = lab.LAB / "BEATFALL.md"
DATA = lab.RESULTS / "beatfall.json"
FIRST = "2026-07-06"
CLIP = 0.40
SURPRISE_CLIP = 100.0
STREAK = 8
MIN_EVENTS, MIN_GROUP = 15, 3
CONFIRM_WEEKS, MAX_WEEKS, CONFIRM_MEAN, NW_LAGS = 12, 24, -0.003, 4
BANDS = [(0, 5), (5, 10), (10, 20), (20, 1000)]


def clip(x):
    return max(-CLIP, min(CLIP, x))


def spy_ret(spy, a, b):
    ia, ib = bisect.bisect_right(spy.dates, a) - 1, bisect.bisect_right(spy.dates, b) - 1
    return spy.rows[ib]["close"] / spy.rows[ia]["close"] - 1.0 if ia >= 0 and ib >= 0 else None


def new_events(names, tables, adj):
    """Every report with a reaction day on or after FIRST whose five-session window has closed."""
    spy = adj["SPY"]
    out = []
    for t in names:
        s, rows = adj.get(t), tables.get(t) or []
        if s is None or not rows:
            continue
        for k, (ts, est, rep, sur) in enumerate(rows):
            if ts[:10] < lab._plus(FIRST, -5):
                continue
            i = p21.reaction_index(s.dates, ts)
            if i < 1 or i + 4 >= len(s.dates):
                continue
            d0, d1, d5 = s.dates[i - 1], s.dates[i], s.dates[i + 4]
            if d1 < FIRST:
                continue
            prior = 0
            for _, _, _, ps in reversed(rows[:k]):
                if ps > 0:
                    prior += 1
                else:
                    break
            m1, m5 = spy_ret(spy, d0, d1), spy_ret(spy, d0, d5)
            if m1 is None or m5 is None:
                continue
            c = s.rows
            surprise = max(-SURPRISE_CLIP, min(SURPRISE_CLIP, sur))
            out.append({"t": t, "ts": ts, "react": d1, "week": lab._plus(d1, -datetime.strptime(d1, "%Y-%m-%d").weekday()),
                        "surprise": surprise, "streak": prior, "beat": surprise > 0, "flagged": bool(surprise > 0 and prior >= STREAK),
                        "r1": clip(c[i]["close"] / c[i - 1]["close"] - 1.0) - m1, "r5": clip(c[i + 4]["close"] / c[i - 1]["close"] - 1.0) - m5})
    return out


def d20_of(adj, e):
    s = adj.get(e["t"])
    if s is None:
        return None
    i = bisect.bisect_left(s.dates, e["react"])
    if i + 20 >= len(s.dates):
        return None
    m = spy_ret(adj["SPY"], s.dates[i], s.dates[i + 20])
    return None if m is None else clip(s.rows[i + 20]["close"] / s.rows[i]["close"] - 1.0) - m


def load_ledger():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {"registered": REGISTERED, "universe": "lab/universe_sp500_2026-09-22.csv", "events": []}


def stats(vals):
    if len(vals) < 3:
        return {"weeks": len(vals)}
    half = len(vals) // 2
    return {"weeks": len(vals), "mean": statistics.fmean(vals), "t": p15.nw_t(vals, NW_LAGS),
            "halves": [statistics.fmean(vals[:half]), statistics.fmean(vals[half:])], "median": statistics.median(vals)}


def score(ledger, adj, latest):
    by_week = {}
    for e in ledger["events"]:
        by_week.setdefault(e["week"], []).append(e)
    weeks, skipped, open_weeks = [], [], []
    for w in sorted(by_week):
        es = by_week[w]
        if latest < lab._plus(w, 4 + 7):
            open_weeks.append(w)                       # some of the week's reaction windows may still be open
            continue
        fl = [e for e in es if e["flagged"]]
        ot = [e for e in es if e["beat"] and not e["flagged"]]
        if len(es) < MIN_EVENTS or len(fl) < MIN_GROUP or len(ot) < MIN_GROUP:
            skipped.append({"week": w, "events": len(es), "flagged": len(fl), "other_beats": len(ot)})
            continue
        row = {"week": w, "events": len(es), "flagged": len(fl), "other_beats": len(ot),
               "r5": statistics.fmean(e["r5"] for e in fl) - statistics.fmean(e["r5"] for e in ot),
               "r1": statistics.fmean(e["r1"] for e in fl) - statistics.fmean(e["r1"] for e in ot),
               "vs_all_other": statistics.fmean(e["r5"] for e in fl) - statistics.fmean(e["r5"] for e in es if not e["flagged"])}
        d = [(d20_of(adj, e), e["flagged"]) for e in es if e["beat"]]
        f20 = [x for x, f in d if f and x is not None]
        o20 = [x for x, f in d if not f and x is not None]
        row["d20"] = statistics.fmean(f20) - statistics.fmean(o20) if len(f20) >= 1 and len(o20) >= 1 else None
        bands = {}
        for lo, hi in BANDS:
            f = [e["r5"] for e in fl if lo < e["surprise"] <= hi]
            o = [e["r5"] for e in ot if lo < e["surprise"] <= hi]
            if f and o:
                bands[f"{lo}-{hi if hi < 1000 else 'up'}"] = statistics.fmean(f) - statistics.fmean(o)
        row["bands"] = bands
        weeks.append(row)
    vals = [w["r5"] for w in weeks]
    st = stats(vals)
    n = len(vals)
    out = {"qualifying_weeks": n, "skipped_weeks": skipped, "open_weeks": open_weeks, "r5": st, "weeks": weeks}
    both_neg = n >= 4 and all(h < 0 for h in st["halves"])
    holds = bool(n >= CONFIRM_WEEKS and st["mean"] <= CONFIRM_MEAN and st["t"] is not None and st["t"] <= -2 and both_neg and st["median"] < 0)
    if holds:
        out["status"] = "CONFIRMED"
    elif n >= CONFIRM_WEEKS and st["mean"] >= 0:
        out["status"] = "REJECTED"
    elif n >= MAX_WEEKS:
        out["status"] = "FINAL: not confirmed"
    elif n < CONFIRM_WEEKS:
        out["status"] = f"too early ({n} qualifying weeks; 12 are needed)"
    else:
        out["status"] = f"keep running ({n} qualifying weeks)"
    for key, label in (("r1", "R1"), ("d20", "D20"), ("vs_all_other", "versus all other events")):
        v = [w[key] for w in weeks if w.get(key) is not None]
        out[key] = stats(v)
    band_rows = {}
    for lo, hi in BANDS:
        k = f"{lo}-{hi if hi < 1000 else 'up'}"
        v = [w["bands"][k] for w in weeks if k in w["bands"]]
        band_rows[k] = stats(v)
    out["bands"] = band_rows
    return out


def pct(x, d=2):
    return "--" if x is None else f"{x * 100:+.{d}f}%"


def write_page(res, ledger, latest, generated):
    r5 = res["r5"]
    lines = ["# Beat-then-fall: the corrected contrast, forward", "",
             f"Registered 2026-10-12 as Pass 30 (`lab/README.md`, {REGISTERED}). Flagged beats (a positive surprise after 8 or more positive quarters) against the other beats of the same reaction week, on the "
             "five-day market-adjusted return R5, for reports with a reaction day on or after 2026-07-06. `lab/forward_beatfall.py` rebuilds this page from the append-only `lab/beatfall_events.json`; edits by hand are overwritten.", "",
             f"Last run: {generated}. Latest bar: {latest}. Events in the ledger: {len(ledger['events'])}.", "",
             f"**Status: {res['status']}.** " + (f"Mean weekly gap {pct(r5['mean'])} (Newey-West t {r5['t']:+.2f}), halves {pct(r5['halves'][0])} / {pct(r5['halves'][1])}, median {pct(r5['median'])}." if "mean" in r5 else f"{res['qualifying_weeks']} qualifying weeks so far."), "",
             "| Reaction week | Events | Flagged beats | Other beats | R5 gap (flagged minus other beats) | R1 gap | Versus all other events | D20 gap |", "|---|---|---|---|---|---|---|---|"]
    for w in res["weeks"]:
        lines.append(f"| {w['week']} | {w['events']} | {w['flagged']} | {w['other_beats']} | {pct(w['r5'])} | {pct(w['r1'])} | {pct(w['vs_all_other'])} | {pct(w['d20'])} |")
    if res["skipped_weeks"]:
        lines += ["", "Weeks below the floors (not counted): " + "; ".join(f"{s['week']} ({s['events']} events, {s['flagged']} flagged, {s['other_beats']} other beats)" for s in res["skipped_weeks"]) + "."]
    if res["open_weeks"]:
        lines += ["", "Weeks whose reaction windows are still open: " + ", ".join(res["open_weeks"]) + "."]
    lines += ["", "Reported, never decisive: " + (f"R1 {pct(res['r1'].get('mean'))}" if res["r1"].get("mean") is not None else "R1 --") + "; "
              + (f"D20 {pct(res['d20'].get('mean'))}" if res["d20"].get("mean") is not None else "D20 --") + "; "
              + (f"versus all other events {pct(res['vs_all_other'].get('mean'))}" if res["vs_all_other"].get("mean") is not None else "versus all other events --")
              + ". By surprise band: " + "; ".join(f"{k}% {pct(v.get('mean'))} ({v['weeks']} weeks)" for k, v in res["bands"].items()) + ".", "",
              "Rule: confirmed at 12 or more qualifying weeks if the mean is -0.3% or lower, the Newey-West t is -2 or lower, both halves and the median are negative; rejected at 12 or more if the mean is 0 or higher; otherwise it keeps running to 24."]
    PAGE.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def main():
    names = sorted(p9.sp500())
    now = datetime.now().astimezone()
    tables, fetched_at = fs.fetch_tables(names)
    adj, missing, _ = fs.get_bars(names, "2026-05-15", lab._plus(now.date().isoformat(), 1))
    latest = adj["SPY"].dates[-1]
    ledger = load_ledger()
    have = {(e["t"], e["ts"]) for e in ledger["events"]}
    added = [dict(e, first_seen=now.isoformat(), tables_fetched_at=fetched_at) for e in new_events(names, tables, adj) if (e["t"], e["ts"]) not in have]
    if added:
        ledger["events"].extend(added)
        ledger["events"].sort(key=lambda e: (e["react"], e["t"], e["ts"]))
        fs.write_json(LEDGER, ledger)
    print(f"  logged {len(added)} newly closed events ({len(ledger['events'])} in the ledger); empty price tickers: {len(missing)}")
    res = score(ledger, adj, latest)
    generated = now.strftime("%Y-%m-%d %H:%M")
    write_page(res, ledger, latest, generated)
    fs.write_json(DATA, {"registered": REGISTERED, "generated": generated, "latest_bar": latest, "result": res})
    print(f"  status: {res['status']}; qualifying weeks {res['qualifying_weeks']}, open {len(res['open_weeks'])}, skipped {len(res['skipped_weeks'])}")
    for w in res["weeks"]:
        print(f"    {w['week']}  events {w['events']:>3} flagged {w['flagged']:>2} other beats {w['other_beats']:>3}  R5 gap {pct(w['r5'])}")
    return res


if __name__ == "__main__":
    main()
