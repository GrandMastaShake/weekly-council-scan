#!/usr/bin/env python3
"""The forward switch lines (Pass 66).

Two chains of weekly returns from 100 on 2026-11-20, each holding one of
two paper books for the week:

- "on the Council's call": the Council's booked week when the Saturday
  regime issue counts two or more flags up (a defensive week), the
  trend-strength book ("cap of three", Pass 63) when it counts fewer.
- "on the 40-week rule": the Council's booked week when SPY closed under
  its 40-week average, the trend-strength book when it did not.

Beside them, unswitched: the Council's book, the trend book, SPY.

It reads three records and writes none of them: lab/regime_calls.json
(appended by `log`, below), lab/book_ledger.json (forward_book.py) and
portfolio/history (the Council's tracker). The page is rebuilt whole
from those each run.

    python lab/forward_switch.py                                  # write lab/SWITCH.md
    python lab/forward_switch.py log 2026-11-20 2 223 "Regime flags: 2 up" [canary] [posture] [carried]

The calls file is append-only: a Friday that has a call is never logged again.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

LAB = Path(__file__).resolve().parent
CALLS = LAB / "regime_calls.json"
LEDGER = LAB / "book_ledger.json"
HISTORY = LAB.parent / "portfolio" / "history"
PAGE = LAB / "SWITCH.md"
START = "2026-11-20"
FLAGS_DEFENSIVE = 2                   # the Council's own review threshold (issue #24)
SWITCH_COST = 0.002                   # one book sold, the other bought, 0.10% a side
TREND_BOOK = "cap of three"
READ_FROM = "2027-11-19"


# ---------------------------------------------------------------- pure

def call_for(flags_up):
    return "defensive" if flags_up >= FLAGS_DEFENSIVE else "trending"


def add_call(calls, friday, flags_up, issue, heading, logged, canary=None, posture=None, carried=False):
    """Append one call. `logged` is local ISO time; the call is late if it
    was written at or after 09:30 on the Monday it applies to."""
    if any(c["friday"] == friday for c in calls):
        raise ValueError(f"a call for {friday} is already logged; the file is append-only")
    if calls and friday <= calls[-1]["friday"]:
        raise ValueError(f"{friday} is not after the last call ({calls[-1]['friday']})")
    monday_open = datetime.fromisoformat(friday) + timedelta(days=3, hours=9, minutes=30)
    row = {"friday": friday, "applies_to_week_of": (date.fromisoformat(friday) + timedelta(days=3)).isoformat(),
           "flags_up": int(flags_up), "call": call_for(int(flags_up)), "issue": issue, "heading": heading,
           "carried": bool(carried), "logged": logged, "late": datetime.fromisoformat(logged[:19]) >= monday_open,
           "context_not_scored": {"canary": canary, "posture": posture}}
    calls.append(row)
    return row


def chain(weeks):
    """`weeks`: oldest first, each {friday (the week's own Friday), call,
    cold, council (a return, or None when the Council booked no week),
    trend, spy}. Returns the rows with each line's value added."""
    val = {"on the Council's call": 100.0, "on the 40-week rule": 100.0, "the Council's book": 100.0,
           "the trend book": 100.0, "SPY": 100.0}
    last = {"on the Council's call": None, "on the 40-week rule": None}
    out = []
    for w in weeks:
        council = 0.0 if w["council"] is None else w["council"]
        src = {"on the Council's call": "council" if w["call"] == "defensive" else "trend",
               "on the 40-week rule": "council" if w["cold"] else "trend"}
        row = {"friday": w["friday"], "call": w["call"], "cold": w["cold"], "council_missing": w["council"] is None, "source": dict(src)}
        for name, s_ in src.items():
            r = council if s_ == "council" else w["trend"]
            cost = SWITCH_COST if last[name] is not None and last[name] != s_ else 0.0
            val[name] *= (1.0 - cost) * (1.0 + r)
            last[name] = s_
        val["the Council's book"] *= 1.0 + council
        val["the trend book"] *= 1.0 + w["trend"]
        val["SPY"] *= 1.0 + w["spy"]
        row["value"] = {k: round(v, 4) for k, v in val.items()}
        out.append(row)
    return out


def drawdown(values):
    peak, dd = 100.0, 0.0
    for v in values:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1.0)
    return dd


def join(calls, ledger, council):
    """The weeks all three records cover. `council`: {week-start ISO date:
    return as a fraction} for closed weeks. A call logged for Friday F and
    the ledger's cold flag for F both apply to the week ending F + 7."""
    by_call = {c["friday"]: c for c in calls}
    cold = {w["friday"]: w["cold"] for w in ledger["weeks"]}
    hist = ledger["books"][TREND_BOOK]["history"]
    out = []
    for prev, cur in zip(hist, hist[1:]):
        f = prev["friday"]
        if f not in by_call or f not in cold:
            continue
        g = date.fromisoformat(cur["friday"])
        booked = [r for d, r in council.items() if g - timedelta(days=4) <= date.fromisoformat(d) <= g]
        out.append({"friday": cur["friday"], "call": by_call[f]["call"], "cold": cold[f],
                    "council": booked[0] if booked else None,
                    "trend": cur["equity"] / prev["equity"] - 1.0,
                    "spy": cur["spy_close"] / prev["spy_close"] - 1.0})
    return out


# ---------------------------------------------------------------- files

def read_council():
    import yaml
    out = {}
    for p in sorted(HISTORY.glob("*.yaml")):
        with open(p, encoding="utf-8") as fh:
            d = yaml.safe_load(fh)
        if d and d.get("status") == "closed" and d.get("weighted_return") is not None and str(d.get("week")) >= START:
            out[str(d["week"])] = float(d["weighted_return"]) / 100.0
    return out


def read_calls():
    if CALLS.exists():
        with open(CALLS, encoding="utf-8") as fh:
            return json.load(fh)
    return {"schema": "regime-calls/v1", "rules": "lab/README.md, Pass 66",
            "rule": f"defensive when the Saturday regime issue counts {FLAGS_DEFENSIVE} or more flags up, trending otherwise", "calls": []}


def write_page(calls, rows):
    L = ["# The switch lines, forward", "",
         "Lab Pass 66, rules frozen on 2026-11-23. Lab only: not the Council's picks and not advice.",
         "A line holds the Council's booked week in a defensive week and the trend-strength book in a trending one;",
         f"a change of source costs {100 * SWITCH_COST:.2f}%. Nothing is read from this page before the week ending {READ_FROM}.", ""]
    if rows:
        last = rows[-1]["value"]
        L += [f"After {len(rows)} week(s), to {rows[-1]['friday']}:", "", "| Line | Value (from 100) | Largest drawdown |", "|---|---|---|"]
        for name in last:
            L.append(f"| {name} | {last[name]:.2f} | {100 * drawdown([r['value'][name] for r in rows]):.1f}% |")
        n_def = sum(r["call"] == "defensive" for r in rows)
        L += ["", f"Defensive weeks on the Council's call: {n_def} of {len(rows)}. Cold weeks on the 40-week rule: {sum(r['cold'] for r in rows)} of {len(rows)}. "
              f"Weeks with no Council book: {sum(r['council_missing'] for r in rows)}."]
    else:
        L.append("No completed week yet.")
    L += ["", "## The calls", "", "| Friday | For the week of | Flags up | Call | Issue | Logged | Late |", "|---|---|---|---|---|---|---|"]
    for c in calls["calls"]:
        L.append(f"| {c['friday']} | {c['applies_to_week_of']} | {c['flags_up']}{' (carried)' if c['carried'] else ''} | {c['call']} | #{c['issue']} | {c['logged'][:16]} | {'yes' if c['late'] else 'no'} |")
    with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv):
    calls = read_calls()
    if len(argv) > 1 and argv[1] == "log":
        a = argv[2:]
        if len(a) < 4:
            raise SystemExit('usage: forward_switch.py log <friday> <flags up> <issue number> "<heading>" [canary] [posture] [carried]')
        row = add_call(calls["calls"], a[0], int(a[1]), int(a[2]), a[3], datetime.now().isoformat(timespec="seconds"),
                       canary=a[4] if len(a) > 4 and a[4] else None, posture=a[5] if len(a) > 5 and a[5] else None,
                       carried=len(a) > 6 and a[6] == "carried")
        with open(CALLS, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(calls, fh, indent=1)
            fh.write("\n")
        print(f"logged: week of {row['applies_to_week_of']} is {row['call']} ({row['flags_up']} flags up, #{row['issue']})" + (" LATE" if row["late"] else ""))
    with open(LEDGER, encoding="utf-8") as fh:
        ledger = json.load(fh)
    rows = chain(join(calls["calls"], ledger, read_council()))
    write_page(calls, rows)
    print(f"{len(calls['calls'])} call(s), {len(rows)} completed week(s); wrote {PAGE.name}")
    if rows:
        print("  " + ", ".join(f"{k} {v:.2f}" for k, v in rows[-1]["value"].items()))


if __name__ == "__main__":
    main(sys.argv)
