#!/usr/bin/env python3
"""The weekend pick (Pass 67).

Each weekend one picker names five long names with no data after the
Saturday feed. They are kept beside the Council's booked names and both
fives are measured the same way: equal weight, Monday's open to Friday's
close, no stops, no cash, dividends in.

    python lab/weekend_pick.py log 2026-11-27 "PG|Ophelia|one sentence" ... (five of them)
    python lab/weekend_pick.py            # write lab/WEEKEND.md: the picks and the count of scored weeks
    python lab/weekend_pick.py read       # the lines; refuses before 40 scored weeks

The picks file is append-only: a Friday that has a pick is never logged
again and a past row is never changed (scripts/lab_ledger_guard.py holds
that in CI). A pick written at or after 04:00 New York time on the Monday
it applies to is marked late and left out of the lines. The time is
written with its offset; one without is refused, because a bare clock
reading means whatever zone the machine was in (2026-11-25).
Nothing here is booked in portfolio/ and the Monday Council does not read it.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

LAB = Path(__file__).resolve().parent
PICKS = LAB / "weekend_picks.json"
PAGE = LAB / "WEEKEND.md"
HISTORY = LAB.parent / "portfolio" / "history"
UNIVERSE = LAB.parent / "wiki" / "universe.md"
DESKS = ("Ophelia", "Cecil", "Marky")
NAMES = 5
READ_AT = 40                          # scored weeks before anything is read
ET = ZoneInfo("America/New_York")     # the cutoff is Monday 04:00 here


def now_et() -> str:
    """The time a pick is logged: New York, to the second, with its offset."""
    return datetime.now(ET).isoformat(timespec="seconds")


def logged_et(logged: str) -> datetime:
    """`logged` read as a moment, in New York time. A reading with no UTC
    offset is refused: 03:30 on a machine in UTC is 22:30 the night before
    in New York, and the file could not say which was meant."""
    try:
        t = datetime.fromisoformat(logged)
    except ValueError:
        raise ValueError(f"logged {logged!r} is not an ISO time")
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError(f"logged {logged!r} has no UTC offset; write it with one (now_et())")
    return t.astimezone(ET)


# ---------------------------------------------------------------- pure

def add_pick(picks, friday, names, logged, universe):
    """Append one weekend's five. `names` is a list of (ticker, desk, reason);
    `logged` is an ISO time with its UTC offset (now_et())."""
    if any(p["friday"] == friday for p in picks):
        raise ValueError(f"a pick for {friday} is already logged; the file is append-only")
    if picks and friday <= picks[-1]["friday"]:
        raise ValueError(f"{friday} is not after the last pick ({picks[-1]['friday']})")
    if date.fromisoformat(friday).weekday() != 4:
        raise ValueError(f"{friday} is not a Friday")
    tickers = [n[0].upper() for n in names]
    if len(names) != NAMES or len(set(tickers)) != NAMES:
        raise ValueError(f"a pick is {NAMES} different names")
    for t, desk, reason in names:
        if t.upper() not in universe:
            raise ValueError(f"{t} is not in the Council's universe")
        if desk not in DESKS:
            raise ValueError(f"{desk} is not one of {DESKS}")
        if not reason.strip():
            raise ValueError(f"{t} has no reason")
    when = logged_et(logged)
    cutoff = datetime.combine(date.fromisoformat(friday) + timedelta(days=3),
                              datetime.min.time().replace(hour=4), tzinfo=ET)
    row = {"friday": friday, "applies_to_week_of": (date.fromisoformat(friday) + timedelta(days=3)).isoformat(),
           "names": [{"ticker": t.upper(), "desk": d, "reason": r.strip()} for t, d, r in names],
           "logged": logged, "late": when >= cutoff}
    picks.append(row)
    return row


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def score_week(w, o, px):
    """One week. `w` and `o` are ticker lists; `px[t]` is (previous close,
    entry open, exit close), adjusted. Returns the registered measures."""
    gap = lambda t: px[t][1] / px[t][0] - 1
    week = lambda t: px[t][2] / px[t][1] - 1
    adds, drops = [t for t in o if t not in w], [t for t in w if t not in o]
    return {"W": _mean([week(t) for t in w]), "O": _mean([week(t) for t in o]), "SPY": week("SPY"),
            "overlap": len(set(w) & set(o)),
            "gap_edge": _mean([gap(t) for t in o]) - gap("SPY"),
            "adds_gap": _mean([gap(t) for t in adds]), "drops_gap": _mean([gap(t) for t in drops]),
            "adds_week": _mean([week(t) for t in adds]), "drops_week": _mean([week(t) for t in drops])}


def tstat(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None, None, len(xs)
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    return m, (m / (sd / math.sqrt(len(xs))) if sd else None), len(xs)


def lines(rows):
    """The registered lines from scored weeks. Refuses before READ_AT."""
    if len(rows) < READ_AT:
        raise ValueError(f"{len(rows)} scored weeks; nothing is read before {READ_AT}")
    out = {"W minus O": tstat([r["W"] - r["O"] for r in rows]),
           "gap edge": tstat([r["gap_edge"] for r in rows]),
           "adds gap minus drops gap": tstat([r["adds_gap"] - r["drops_gap"] for r in rows
                                              if r["adds_gap"] is not None and r["drops_gap"] is not None]),
           "adds week minus drops week": tstat([r["adds_week"] - r["drops_week"] for r in rows
                                                if r["adds_week"] is not None and r["drops_week"] is not None]),
           "overlap": tstat([float(r["overlap"]) for r in rows])}
    t = lambda k: out[k][1] or 0.0
    out["picking earlier is better"] = out["W minus O"][0] > 0 and t("W minus O") >= 2
    out["the Council buys after the move"] = (t("gap edge") >= 2 and t("adds gap minus drops gap") >= 2
                                              and t("adds week minus drops week") <= -2)
    return out


def council_week(monday, council):
    """The Council's week whose date falls Monday to Friday of that week."""
    m = date.fromisoformat(monday)
    for d in sorted(council):
        if m <= date.fromisoformat(d) <= m + timedelta(days=4):
            return d
    return None


# ---------------------------------------------------------------- data

def read_picks():
    return json.loads(PICKS.read_text(encoding="utf-8")) if PICKS.exists() else []


def read_universe():
    """The stocks in wiki/universe.md's table (the feed file also carries funds)."""
    out = set()
    for line in UNIVERSE.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 6 and cells[1].isupper() and cells[1] != "TICKER" and cells[3] and "---" not in cells[1]:
            out.add(cells[1])
    return out


def read_council():
    """{entry date: [long tickers]} for closed weeks."""
    import yaml
    out = {}
    for f in sorted(HISTORY.glob("*.yaml")):
        y = yaml.safe_load(f.read_text(encoding="utf-8"))
        if y.get("status") != "closed":
            continue
        names = [p["ticker"] for p in y.get("positions", []) if p.get("direction", "long") == "long"]
        if names:
            out[str(y["week"])] = names
    return out


def scored_weeks(picks, council):
    """(pick, council entry date) for each on-time pick whose week the Council closed."""
    out = []
    for p in picks:
        d = council_week(p["applies_to_week_of"], council)
        if d and not p["late"]:
            out.append((p, d))
    return out


def fetch(tickers, entry, monday):
    """(previous close, entry open, last close of the week), adjusted, per ticker."""
    import pandas as pd
    import yfinance as yf
    start = date.fromisoformat(entry) - timedelta(days=10)
    end = date.fromisoformat(monday) + timedelta(days=5)
    d = yf.download(sorted(tickers), start=start.isoformat(), end=end.isoformat(), auto_adjust=True, progress=False)
    out = {}
    for t in tickers:
        o, c = d["Open"][t].dropna(), d["Close"][t].dropna()
        e = pd.Timestamp(entry)
        if e not in o.index or len(c[:e]) < 2:
            raise ValueError(f"no bar for {t} on {entry}")
        out[t] = (float(c[:e].iloc[-2]), float(o[e]), float(c.iloc[-1]))
    return out


def write_page(picks, n_scored):
    L = ["# The weekend pick", "",
         "Five names picked each weekend with no data after the Saturday feed, kept beside the Council's five (lab Pass 67).",
         "Lab only: not the Council's picks and not advice. Never booked, never in the Arena.", "",
         f"Scored weeks so far: **{n_scored}**. Nothing is read before {READ_AT}.", ""]
    for p in reversed(picks):
        L.append(f"## Week of {p['applies_to_week_of']}" + (" (late: left out of the lines)" if p["late"] else ""))
        L.append("")
        L += [f"- **{n['ticker']}** ({n['desk']}): {n['reason']}" for n in p["names"]]
        L += ["", f"Logged {p['logged']}.", ""]
    PAGE.write_text("\n".join(L).rstrip("\n") + "\n", encoding="utf-8", newline="\n")


def main(argv):
    picks = read_picks()
    if len(argv) > 1 and argv[1] == "log":
        names = [tuple(x.strip() for x in a.split("|", 2)) for a in argv[3:]]
        if any(len(n) != 3 for n in names):
            raise SystemExit('each name is "TICKER|Desk|one sentence"')
        try:
            row = add_pick(picks, argv[2], names, now_et(), read_universe())
        except ValueError as e:
            raise SystemExit(str(e))
        PICKS.write_text(json.dumps(picks, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"logged {row['friday']} -> week of {row['applies_to_week_of']}: "
              + ", ".join(n["ticker"] for n in row["names"]) + (" (LATE)" if row["late"] else ""))
    council = read_council()
    scored = scored_weeks(picks, council)
    if len(argv) > 1 and argv[1] == "read":
        if len(scored) < READ_AT:
            raise SystemExit(f"{len(scored)} scored weeks; nothing is read before {READ_AT}")
        rows = []
        for p, d in scored:
            w, o = [n["ticker"] for n in p["names"]], council[d]
            rows.append(score_week(w, o, fetch(set(w) | set(o) | {"SPY"}, d, p["applies_to_week_of"])))
        for k, v in lines(rows).items():
            print(k, v)
        return
    write_page(picks, len(scored))
    print(f"{len(picks)} pick(s), {len(scored)} scored week(s); wrote {PAGE.name}")


if __name__ == "__main__":
    main(sys.argv)
