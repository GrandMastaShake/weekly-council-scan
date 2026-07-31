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


def fetch_bar(ticker, day):
    """Fetch the OHLC bar for a specific calendar date. Returns dict or None."""
    start = day - dt.timedelta(days=1)
    end = day + dt.timedelta(days=4)  # window guards against holidays/tz
    hist = yf.Ticker(ticker).history(start=start.isoformat(), end=end.isoformat())
    if hist is None or hist.empty:
        return None
    for idx, row in hist.iterrows():
        if idx.date() == day:
            return {"open": float(row["Open"]), "close": float(row["Close"])}
    return None


def entry_price(bar):
    """Monday's first available price: open preferred, close as fallback."""
    if bar is None:
        return None, None
    if bar["open"] and bar["open"] > 0:
        return round(bar["open"], 4), "open"
    return round(bar["close"], 4), "close"


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
