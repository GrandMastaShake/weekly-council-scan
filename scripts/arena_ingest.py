# arena_ingest.py -- Arena entry ingest + price fetch (ASCII-only, Windows-safe)
#
# Fixes the failure mode from week 2026-07-27, where a shell one-liner's
# redirect wrote the COMMAND into arena/YYYY-MM-DD.yaml instead of the output.
# This script never relies on shell redirection: it writes the file itself.
#
# It also pins the entry date. The old one-liner used period='1d' and took the
# last close, which returns whatever day you happen to run it on. This script
# asks yfinance for a window around the entry date and selects the entry
# date's bar explicitly. Entry price convention per arena/README.md:
# Monday's first available price (we use Monday's OPEN; falls back to Monday's
# close if open is missing, and records which one was used).
#
# An open is an open only when its own bar bears it out (#105). At 09:35-09:42
# ET on Monday 2026-09-14 the provider's forming daily bar carried Friday's
# Open while High, Low and Close followed the live session: TSM open 431.55
# against a high of 420.97, XOM open 165.07 against a low of 168.25, five of
# seven tickers checked. entry_price() took any open > 0 and accepted them
# all. So the Open is checked against the bar's own range, low <= open <= high:
#
#   entry_price_source    what entry_price is
#   open                  the bar's Open, inside the bar's own low-high range
#   close                 the bar's Close, because the bar has no Open
#   close_open_rejected   the bar's Close, because its Open was outside that
#                         range; open_rejected beside it holds the open, the
#                         high and the low it was checked against. Written by
#                         a lock run only.
#   (null)                no bar for the date. Or, with open_rejected beside
#                         it, the Open was rejected and the Close could not
#                         be checked either: the bar has no high/low, or its
#                         Close is outside them too.
#
# On a bar still forming the Close is the last trade so far, not Monday's
# close. That is the price the hand-made lock file of 2026-09-14 called
# live_intraday_open_unavailable. A lock file is provisional either way:
# --close reads every entry bar again and writes the whole file from the
# settled ones. So a lock run records the stand-in and says what it is.
#
# The stand-in is sometimes taken in place of a true open, because the bar
# does not say which of its fields is wrong. On 2026-10-06 at 15:31 ET the
# forming bars of the price feed's 320 names and the four index ETFs were
# read: 8 of 323 failed the check, all eight NYSE-listed, and each Open was
# the 09:30 one-minute bar's own (PEG 69.12 against a low of 69.15). The
# day's range had left the opening print out. open_rejected keeps the
# numbers, and --close reads the settled bar.
#
# A --close run REFUSES instead: exit 2, nothing written, the lock file left
# as it was. A closed week is final, and a settled bar has not been seen to
# fail: none of the 82,121 those names had from 2025-10-01 through
# 2026-10-05, and none of the 22,685 of the 90 tickers the Arena and the
# Council's book had priced by then, read on 2026-10-06. One that does is
# the provider's error, with nothing to say which of its fields is the wrong
# one. Run it again later.
#
# Not caught: a stale Open that happens to lie inside the day's range. On
# 2026-09-21 AGNC's Open equalled its Friday Open, sat inside Monday's range
# and passed.
#
# Usage:
#   python arena_ingest.py --week 2026-07-27 --entries entries_2026-07-27.txt
#   python arena_ingest.py --week 2026-07-27 --entries entries.txt --close
#
# Entries file format (one player per block, blank line between players):
#
#   player: some_github_user
#   BANF 30%
#   WAFD 25%
#   ATRO 20%
#   LEU 15%
#   AMPH 10%
#
# The --close flag additionally fetches Friday close for the same week and
# computes weekly returns and alpha vs SPY (run it the following Monday).
#
# Requires: pip install yfinance pyyaml

import argparse
import datetime as dt
import math
import re
import sys
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml")
    sys.exit(1)

BENCHMARK = "SPY"
PICK_RE = re.compile(r"^([A-Za-z.\-]{1,10})\s+(\d+(?:\.\d+)?)\s*%?\s*$")

# How far outside its bar's range an Open may sit and still be that bar's
# Open: float noise, and nothing a price can move by. One part in a million
# is $0.0005 on a $500 name. Open, High and Low of one bar come out of one
# download under one adjustment factor, so an Open that IS the day's high or
# low compares equal to it. The opens of 2026-09-14 were out by 0.7% to 2.5%.
OPEN_RANGE_TOL = 1e-6

# entry_price_source for a Close that stands in for an Open its bar rejected.
OPEN_REJECTED = "close_open_rejected"


def parse_entries(path):
    """Parse the entries text file into a list of player dicts."""
    text = Path(path).read_text(encoding="ascii", errors="replace")
    players = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if current and current["picks"]:
                players.append(current)
            current = None
            continue
        if line.lower().startswith("player:"):
            if current and current["picks"]:
                players.append(current)
            current = {"player": line.split(":", 1)[1].strip(), "picks": []}
            continue
        m = PICK_RE.match(line)
        if m:
            if current is None:
                current = {"player": "unknown", "picks": []}
            ticker = m.group(1).upper()
            weight = float(m.group(2)) / 100.0
            current["picks"].append({"ticker": ticker, "weight": round(weight, 4)})
            continue
        print("WARN: unparsed line skipped: " + line)
    if current and current["picks"]:
        players.append(current)

    # Validate weights
    for p in players:
        total = sum(x["weight"] for x in p["picks"])
        p["total_weight"] = round(total, 4)
        p["cash_weight"] = round(max(0.0, 1.0 - total), 4)
        if total > 1.0001:
            print("WARN: player '%s' weights sum to %.1f%% (>100%%) -- entry invalid per rules"
                  % (p["player"], total * 100))
            p["valid"] = False
        elif not (1 <= len(p["picks"]) <= 10):
            print("WARN: player '%s' has %d positions (rules: 1-10)"
                  % (p["player"], len(p["picks"])))
            p["valid"] = False
        else:
            p["valid"] = True
    return players


def _number(row, field):
    """A bar field as a finite float, or None when it is missing or NaN."""
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def fetch_bar(ticker, day):
    """Fetch the OHLC bar for a specific calendar date. Returns dict or None.

    open and close are the provider's fields as they came. high and low are
    None when the bar has none (missing or NaN): the open is checked against
    them, and a bound that is not there must not read as one that passed.
    """
    start = day - dt.timedelta(days=1)
    end = day + dt.timedelta(days=4)  # window guards against holidays/tz
    hist = yf.Ticker(ticker).history(start=start.isoformat(), end=end.isoformat())
    if hist is None or hist.empty:
        return None
    for idx, row in hist.iterrows():
        if idx.date() == day:
            return {"open": float(row["Open"]), "close": float(row["Close"]),
                    "high": _number(row, "High"), "low": _number(row, "Low")}
    return None


def _has_open(bar):
    """The test entry_price() has always made: an Open that is a number > 0."""
    return bool(bar["open"] and bar["open"] > 0)


def _in_range(price, bar):
    """True when the bar has a high and a low and price lies between them."""
    high, low = bar.get("high"), bar.get("low")
    if price is None or high is None or low is None:
        return False
    tol = OPEN_RANGE_TOL * max(abs(high), abs(low))
    return low - tol <= price <= high + tol


def _px(value):
    return "none" if value is None else str(round(value, 4))


def open_fault(bar):
    """Why this bar's Open cannot stand as an open, in words; None when it can.

    None too for no bar and for a bar with no Open: there is nothing to
    reject, and entry_price() falls back as it always has. A bar with no
    high/low is a fault, not a pass: an Open nothing can check is not one
    that was checked.
    """
    if bar is None or not _has_open(bar):
        return None
    o, high, low = bar["open"], bar.get("high"), bar.get("low")
    if high is None or low is None:
        return "open %s cannot be checked, the bar has no high/low" % _px(o)
    tol = OPEN_RANGE_TOL * max(abs(high), abs(low))
    if o > high + tol:
        return ("open %s is above the bar's high %s (low %s)"
                % (_px(o), _px(high), _px(low)))
    if o < low - tol:
        return ("open %s is below the bar's low %s (high %s)"
                % (_px(o), _px(low), _px(high)))
    return None


def rejected_open(bar):
    """For the record: the Open a bar had and the range it was held to, when
    that Open could not stand. None otherwise."""
    if open_fault(bar) is None:
        return None
    high, low = bar.get("high"), bar.get("low")
    return {"open": round(bar["open"], 4),
            "high": None if high is None else round(high, 4),
            "low": None if low is None else round(low, 4)}


def entry_price(bar):
    """Monday's first available price and which field of the bar it is:
    (price, source). The header has the table.

    The Open, when its own bar bears it out. A bar with no Open falls back to
    its Close, as it always has. A bar whose Open is there and cannot stand
    is never an "open": its Close stands in when the same range bears the
    Close out, and otherwise the bar gives no price at all.
    """
    if bar is None:
        return None, None
    if not _has_open(bar):
        return round(bar["close"], 4), "close"
    if open_fault(bar) is None:
        return round(bar["open"], 4), "open"
    if _in_range(bar["close"], bar):
        return round(bar["close"], 4), OPEN_REJECTED
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True, help="Monday scan date, YYYY-MM-DD")
    ap.add_argument("--entries", required=True, help="entries text file")
    ap.add_argument("--close", action="store_true",
                    help="also fetch Friday close and compute results")
    ap.add_argument("--outdir", default="arena", help="output directory")
    args = ap.parse_args()

    monday = dt.date.fromisoformat(args.week)
    if monday.weekday() != 0:
        print("WARN: %s is not a Monday" % args.week)
    friday = monday + dt.timedelta(days=4)

    players = parse_entries(args.entries)
    if not players:
        print("ERROR: no valid entries parsed from " + args.entries)
        sys.exit(1)

    # Collect all tickers plus benchmark
    tickers = sorted({p_["ticker"] for pl in players for p_ in pl["picks"]})
    tickers.append(BENCHMARK)

    print("Fetching entry bars for %s (%d tickers)..." % (args.week, len(tickers)))
    entry_bars = {}
    for t in tickers:
        bar = fetch_bar(t, monday)
        entry_bars[t] = bar
        if bar is None:
            print("WARN: no bar for %s on %s" % (t, monday.isoformat()))

    # An entry Open its own bar does not bear out is never booked as an open
    # (#105; the header has what a lock run records and why --close refuses).
    faults = {}
    for t in tickers:
        fault = open_fault(entry_bars[t])
        if fault:
            faults[t] = fault
    if faults and args.close:
        print("REFUSED: %s not written. --close scores the week for good, and "
              "%d entry bar(s) have an Open that cannot stand as one:"
              % (Path(args.outdir) / (args.week + ".yaml"), len(faults)))
        for t in faults:
            print("  %s %s: %s" % (t, monday.isoformat(), faults[t]))
        print("A settled bar should not read like this, and nothing says which "
              "of its fields is the wrong one. Run --close again later. If it "
              "still reads so, the provider has the bar wrong and the price is "
              "the owner's to rule on. The lock file is as it was.")
        sys.exit(2)
    for t in faults:
        stand_in, src = entry_price(entry_bars[t])
        if stand_in is None:
            print("WARN: %s %s: %s. Not booked as an open, and nothing else in "
                  "the bar could be checked: no entry price."
                  % (t, monday.isoformat(), faults[t]))
        else:
            print("WARN: %s %s: %s. Not booked as an open. Entry is the bar's "
                  "Close %s (%s): the last trade so far if the session is "
                  "still open. --close re-reads the settled bar."
                  % (t, monday.isoformat(), faults[t], _px(stand_in), src))

    close_bars = {}
    if args.close:
        print("Fetching Friday close bars for %s..." % friday.isoformat())
        for t in tickers:
            close_bars[t] = fetch_bar(t, friday)

    spy_entry, spy_src = entry_price(entry_bars.get(BENCHMARK))

    doc = {
        "week": args.week,
        "lock": args.week + " 08:50 ET",
        "entry_date": monday.isoformat(),
        "exit_date": friday.isoformat(),
        "status": "closed" if args.close else "open",
        "benchmark": {
            "ticker": BENCHMARK,
            "entry_price": spy_entry,
            "entry_price_source": spy_src,
        },
        "players": [],
    }
    rejected = rejected_open(entry_bars.get(BENCHMARK))
    if rejected:
        doc["benchmark"]["open_rejected"] = rejected

    if args.close and close_bars.get(BENCHMARK):
        spy_exit = round(close_bars[BENCHMARK]["close"], 4)
        doc["benchmark"]["exit_price"] = spy_exit
        doc["benchmark"]["return_pct"] = round(
            (spy_exit / spy_entry - 1.0) * 100.0, 2) if spy_entry else None

    for pl in players:
        entry = {
            "player": pl["player"],
            "valid": pl["valid"],
            "total_weight": pl["total_weight"],
            "cash_weight": pl["cash_weight"],
            "picks": [],
        }
        port_return = 0.0
        complete = True
        for pick in pl["picks"]:
            t = pick["ticker"]
            ep, src = entry_price(entry_bars.get(t))
            row = {
                "ticker": t,
                "weight": pick["weight"],
                "entry_price": ep,
                "entry_price_source": src,
            }
            rejected = rejected_open(entry_bars.get(t))
            if rejected:
                row["open_rejected"] = rejected
            if ep is None:
                complete = False
            if args.close:
                cb = close_bars.get(t)
                if cb and ep:
                    xp = round(cb["close"], 4)
                    ret = round((xp / ep - 1.0) * 100.0, 2)
                    row["exit_price"] = xp
                    row["return_pct"] = ret
                    port_return += pick["weight"] * ret
                else:
                    complete = False
            entry["picks"].append(row)
        if args.close and complete:
            entry["weekly_return_pct"] = round(port_return, 2)
            if doc["benchmark"].get("return_pct") is not None:
                entry["alpha_vs_spy_pct"] = round(
                    port_return - doc["benchmark"]["return_pct"], 2)
        doc["players"].append(entry)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / (args.week + ".yaml")

    # Refuse to clobber a valid existing results file; the broken command-text
    # file from the original bug will not parse as a dict, so it gets replaced.
    if outpath.exists():
        try:
            existing = yaml.safe_load(outpath.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and existing.get("status") == "closed" and not args.close:
                print("ERROR: %s is already closed. Refusing to overwrite." % outpath)
                sys.exit(1)
        except Exception:
            print("NOTE: existing file is not valid YAML -- replacing it.")

    with open(outpath, "w", encoding="ascii", newline="\n") as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False,
                  allow_unicode=False)
    print("Wrote " + str(outpath))


if __name__ == "__main__":
    main()
