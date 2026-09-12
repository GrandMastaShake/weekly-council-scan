"""daily_observe.py -- one completed US session, committed as an observation.

The weekly feed commits Friday closes because that is the cadence the council
reads. The bars behind it were never weekly: `snapshot.fetch_weekly_bars`
downloads daily bars over a ranged window and selects one. This script keeps
the other four sessions instead of discarding them.

Output: <out>/daily/<YYYY-MM-DD>.json, the same shape as DATA_FEED.md sec.1
plus a `cadence` discriminator. Append-only, exactly like the weekly files.

What this is NOT
----------------
An observation, not a forecast. Nothing here scores a sector, and no consumer
of this file may treat it as a forecast artifact: the two judgment components
in sector-regime-heatmap (`regime_fit`, `macro_catalyst`) have no daily
source, and a daily file that carried them would be inventing them. This file
records what traded. That is the whole contract.

The session-witness gate
------------------------
The failure this script exists to avoid is committing a bar that is still
forming. `truth_check` v6.1 had to learn the same lesson from the other
direction (a weekday run comparing a Friday close against overnight futures).
A partial session is indistinguishable from a settled one once it is written
to disk, so the gate is up front:

    SPY is the session witness. No SPY bar dated exactly `as_of` means the
    session did not happen or has not settled, and the run refuses.

That is deliberately stricter than "some tickers returned data" -- on a
half-formed session a handful of names will always come back.

CLI:
  python scripts/daily_observe.py [--date YYYY-MM-DD] [--out data]
         [--dry-run] [--force] [--no-special]

  --date defaults to the most recent weekday on or before today. The gate
  above, not the calendar, decides whether that date is actually writable.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

# Repo root = the nearest ancestor holding the scan_pipeline package. Copied
# from scripts/backfill_weekly.py deliberately: a fixed number of parent hops
# is correct for exactly one of the two paths this pattern lives at, and that
# is the bug that kept the backfill workflow from ever starting.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PIPELINE_ROOT = _SCRIPT_DIR
while not os.path.isdir(os.path.join(_PIPELINE_ROOT, "scan_pipeline")):
    _parent = os.path.dirname(_PIPELINE_ROOT)
    if _parent == _PIPELINE_ROOT:
        raise RuntimeError(
            "cannot locate the scan_pipeline package above " + _SCRIPT_DIR)
    _PIPELINE_ROOT = _parent
if _PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, _PIPELINE_ROOT)

from scan_pipeline.config.tickers import PRICE_FEED_UNIVERSE  # noqa: E402
from scan_pipeline.snapshot import (  # noqa: E402
    INDEX_TICKERS,
    SECTOR_TICKERS,
    canonical_json,
    fetch_weekly_bars,
    get_special_instruments,
    _normalize_block,
)

# The daily file carries its own source label so a downstream adjustment-basis
# check cannot silently treat it as the weekly feed. Both are yfinance
# auto_adjust=True and therefore total-return; the label distinguishes
# provenance, not basis.
SOURCE = "yahoo-daily"

CADENCE = "daily"

# SPY is the session witness (see module docstring). It is also the benchmark
# every relative-momentum calculation downstream divides by, so a file without
# it is useless even if it were complete.
WITNESS = "SPY"


class SessionNotSettled(RuntimeError):
    """The requested date is not a completed, settled US trading session."""


def observation_universe(weekly_dir: str | None = None) -> list:
    """Every ticker the weekly feed commits, and never fewer.

    Deliberately the full universe, not the 110-name analysis focus. The rule
    in CLAUDE.md -- do not shrink the feed to the focus set -- applies with
    more force here: a daily file is the finest-grained record this repo
    keeps, and re-fetching a name later means fetching it against a different
    adjustment anchor, which is the divergence sec.4 warns about.

    `STOCK_UNIVERSE` alone is NOT enough and the first build of this script
    got it wrong: it is the ENGINE set, 277 names covering only 66 of the
    110-name watchlist, and it left Communication Services with 2 usable
    constituents. `PRICE_FEED_UNIVERSE` (321) is the feed.

    The union with the newest weekly file's series is the self-healing part:
    if the panel grows again, the daily feed follows automatically instead of
    silently staying narrow.
    """
    universe = (set(PRICE_FEED_UNIVERSE)
                | set(INDEX_TICKERS) | set(SECTOR_TICKERS))
    if weekly_dir and os.path.isdir(weekly_dir):
        newest = sorted(f for f in os.listdir(weekly_dir)
                        if f.endswith(".json") and "corrected" not in f)
        if newest:
            path = os.path.join(weekly_dir, newest[-1])
            with open(path, encoding="utf-8") as f:
                universe |= set(json.load(f).get("series") or {})
    return sorted(universe)


def default_date(today: date | None = None) -> str:
    """Most recent weekday on or before today.

    A calendar guess only. Whether that session actually settled is decided
    by the witness gate, which is the part that cannot be wrong.
    """
    d = today or datetime.now(timezone.utc).date()
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d -= timedelta(days=1)
    return d.isoformat()


def build_document(as_of: str, fetched: dict, special: dict | None) -> dict:
    """Assemble the daily document. Pure: no network, no clock except
    fetched_at, which is the adjustment anchor and must be real."""
    bars = fetched.get("bars") or {}
    missing = list(fetched.get("missing") or [])

    if special is None:
        special = {"rates": {}, "vol": {}, "commodities": {}, "fx": {},
                   "missing": [{"ticker": "*",
                                "reason": "special instruments not requested "
                                          "(--no-special)"}]}
    missing.extend(special.get("missing") or [])

    # dedupe + sort, matching write_weekly so the two files diff the same way
    seen = set()
    uniq = []
    for m in missing:
        key = (str(m.get("ticker")), str(m.get("reason")))
        if key not in seen:
            seen.add(key)
            uniq.append({"ticker": key[0], "reason": key[1]})
    uniq.sort(key=lambda m: (m["ticker"], m["reason"]))

    return {
        "as_of": as_of,
        "cadence": CADENCE,
        "source": SOURCE,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": "close",
        "series": _normalize_block(bars),
        "rates": _normalize_block(special.get("rates")),
        "vol": _normalize_block(special.get("vol")),
        "commodities": _normalize_block(special.get("commodities")),
        "fx": _normalize_block(special.get("fx")),
        "missing": uniq,
    }


def assert_session_settled(as_of: str, bars: dict,
                           today: date | None = None) -> None:
    """Refuse anything but a completed session. See module docstring."""
    now = today or datetime.now(timezone.utc).date()
    d = date.fromisoformat(as_of)
    if d > now:
        raise SessionNotSettled(
            "as_of " + as_of + " is in the future (UTC today is "
            + now.isoformat() + "). There is no bar to observe.")
    if WITNESS not in bars:
        raise SessionNotSettled(
            "No " + WITNESS + " bar dated " + as_of + ". Either that date was "
            "not a US trading session, or the session has not settled with the "
            "provider yet. Refusing to write a file whose bars may still be "
            "forming -- a partial session is indistinguishable from a settled "
            "one once committed. Re-run after the close, or pass --date for a "
            "session known to be complete.")


def fetch_session_range(tickers: list, start: str, end: str) -> dict:
    """One ranged download, sliced into per-session bar maps.

    The bootstrap path. Fetching N sessions with N date-pinned calls costs N
    round trips and, worse, N different fetch timestamps -- so the files would
    carry N adjustment anchors for bars that a single download would have put
    on one. One ranged call gives every session the same anchor, which is what
    a consumer comparing two sessions needs.

    Returns {session_date: {ticker: {"close", "volume"}}} for every date in
    range that has a witness bar. Non-sessions simply do not appear.
    """
    import yfinance as yf

    tickers = sorted(set(tickers))
    end_excl = (date.fromisoformat(end) + timedelta(days=1)).isoformat()
    df = yf.download(tickers, start=start, end=end_excl, interval="1d",
                     group_by="ticker", auto_adjust=True,
                     progress=False, threads=True)

    sessions: dict = {}
    for ts in df.index:
        day = ts.date().isoformat()
        day_bars = {}
        for t in tickers:
            try:
                row = df[t].loc[ts]
            except Exception:
                continue
            close = row.get("Close")
            if close is None or close != close:      # NaN
                continue
            vol = row.get("Volume")
            volume = None
            try:
                if vol is not None and vol == vol and int(vol) > 0:
                    volume = int(vol)
            except (TypeError, ValueError):
                volume = None
            day_bars[t] = {"close": float(close), "volume": volume}
        if WITNESS in day_bars:
            sessions[day] = day_bars
    return sessions


def missing_for(tickers: list, day_bars: dict, as_of: str) -> list:
    """Every requested ticker without a bar, with a reason. Never omitted."""
    return [{"ticker": t,
             "reason": "no bar dated " + as_of + " in the ranged download"}
            for t in sorted(set(tickers)) if t not in day_bars]


def write_document(doc: dict, out_dir: str, force: bool = False) -> str:
    path = os.path.join(out_dir, "daily", doc["as_of"] + ".json")
    if os.path.exists(path) and not force:
        raise FileExistsError(
            path + " already exists. Daily files are append-only, exactly like "
            "the weekly ones: if the provider restated, write a "
            + doc["as_of"] + ".corrected.json rather than editing this. "
            "--force is for re-running a failed write, nothing else.")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(canonical_json(doc))
    return path


def _run_backfill(a, as_of: str, tickers: list) -> int:
    """Bootstrap every settled session in [--since, --date] from one download."""
    print("Bootstrapping " + a.since + " .. " + as_of + " over "
          + str(len(tickers)) + " tickers (one ranged download)")
    sessions = fetch_session_range(tickers, a.since, as_of)
    if not sessions:
        print("REFUSED: no settled session found in that range (no "
              + WITNESS + " bar on any date).")
        return 2

    special_note = {"rates": {}, "vol": {}, "commodities": {}, "fx": {},
                    "missing": [{"ticker": "*",
                                 "reason": "bootstrap backfill: special "
                                           "instruments not fetched"}]}
    written, skipped = 0, 0
    for day in sorted(sessions):
        day_bars = sessions[day]
        fetched = {"bars": day_bars,
                   "missing": missing_for(tickers, day_bars, day)}
        doc = build_document(day, fetched, special_note)
        if a.dry_run:
            print("  " + day + ": " + str(len(doc["series"])) + " series, "
                  + str(len(doc["missing"])) + " missing (dry run)")
            continue
        try:
            write_document(doc, a.out, force=a.force)
        except FileExistsError:
            print("  " + day + ": exists, skipped (append-only)")
            skipped += 1
            continue
        print("  " + day + ": " + str(len(doc["series"])) + " series, "
              + str(len(doc["missing"])) + " missing")
        written += 1
    print("Wrote " + str(written) + " session file(s), skipped "
          + str(skipped) + " existing.")
    return 0


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", default=None,
                   help="session date YYYY-MM-DD (default: latest weekday)")
    p.add_argument("--out", default="data", help="data root (default: data)")
    p.add_argument("--dry-run", action="store_true",
                   help="fetch and report, write nothing")
    p.add_argument("--force", action="store_true",
                   help="overwrite an existing file (re-running a failed write only)")
    p.add_argument("--no-special",
                   action="store_true",
                   help="skip rates/vol/commodities/fx (equities only)")
    p.add_argument("--since", default=None,
                   help="bootstrap: write every settled session from this date "
                        "through --date in one ranged download")
    a = p.parse_args(argv)

    as_of = a.date or default_date()
    tickers = observation_universe(os.path.join(a.out, "weekly"))

    if a.since:
        return _run_backfill(a, as_of, tickers)
    print("Observing " + as_of + " over " + str(len(tickers)) + " tickers")

    fetched = fetch_weekly_bars(tickers, as_of)
    bars = fetched.get("bars") or {}

    try:
        assert_session_settled(as_of, bars)
    except SessionNotSettled as exc:
        print("REFUSED: " + str(exc))
        return 2

    special = None if a.no_special else get_special_instruments(as_of)
    doc = build_document(as_of, fetched, special)

    got = len(doc["series"])
    print("  series " + str(got) + "/" + str(len(tickers))
          + ", missing " + str(len(doc["missing"])))
    for m in doc["missing"][:10]:
        print("    missing " + m["ticker"] + ": " + m["reason"])
    if len(doc["missing"]) > 10:
        print("    ... and " + str(len(doc["missing"]) - 10) + " more")

    if a.dry_run:
        print("DRY RUN: nothing written")
        return 0

    try:
        path = write_document(doc, a.out, force=a.force)
    except FileExistsError as exc:
        print("REFUSED: " + str(exc))
        return 2
    print("Wrote " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
