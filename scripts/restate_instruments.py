#!/usr/bin/env python3
"""restate_instruments.py -- write a correction that restates instrument closes.

A weekly file is an observation and is never edited. When an instrument's
committed close turns out not to be the close for the file's date -- in
2026-08-28.json the 10-year, VIX and the dollar index are Thursday's -- the
repair is <date>.corrected.json: a full copy with those closes replaced.
Readers prefer it and the original stays (DATA_FEED.md sec.1).

This writes that file. A correction needs the owner's sign-off, so there is
no default for --reason and nothing here runs on a schedule.

For each --instrument block.TICKER it:

  * fetches the bar through the writer's own path (snapshot_macro._fetch_one),
    so the writer's rules hold: the bar dated as_of or nothing, and nothing
    the exchange has not settled. A stand-in from an earlier session is
    refused. Replacing one wrong session with another is not a correction.
  * refuses when the provider's close is the one already committed.
  * records what the base held in `restated`, and labels the replacement in
    provenance.<block>.<ticker> with the real fetch time and the
    "-backfill" source, because it was fetched now and not with the file.

One refusal stops the whole run: a correction is one reviewed statement about
one file, not whichever parts of it happened to fetch. A week that already
has a correction is refused too; add to that one by hand, then run
scripts/rebuild_corrections.py.

The file is written through rebuild_corrections.apply_edits, so rebuilding
it afterwards changes nothing.

Usage:
  python scripts/restate_instruments.py --date 2026-08-28 \\
         --instrument rates.US10Y --instrument vol.VIX --instrument fx.DXY \\
         --reason "..." [--dir data/weekly] [--dry-run]

Afterwards: scripts/truth_check.py --repo . --pipeline . --feed --derive, and
scripts/rederive_market_state.py if --derive says the state moved.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import sys
from pathlib import Path

# Repo root = the nearest ancestor holding the scan_pipeline package. Copied
# from scripts/daily_observe.py for the reason given there.
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
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import rebuild_corrections  # noqa: E402
from scan_pipeline import snapshot, snapshot_macro  # noqa: E402

BACKFILL_SOURCE = snapshot.PROVIDER + "-backfill"   # "yahoo-backfill"


class Refused(RuntimeError):
    """The correction was not written, and why."""


def build_correction(base: dict, base_name: str, names: list, reason: str,
                     fetch=None, now=None) -> dict:
    """The correction document for `base`. Fetches, writes nothing.

    names are "block.TICKER". fetch is snapshot_macro._fetch_one unless a
    test supplies one; now is an aware UTC datetime."""
    fetch = fetch or snapshot_macro._fetch_one
    now = now or dt.datetime.now(dt.timezone.utc)
    if not reason or not reason.strip():
        raise Refused("a correction needs a reason")
    if not names:
        raise Refused("no instrument named")
    if len(set(names)) != len(names):
        raise Refused("an instrument is named twice")

    as_of = dt.date.fromisoformat(base["as_of"])
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    correction = copy.deepcopy(base)
    restated = []
    for name in names:
        block, _, ticker = name.partition(".")
        cfg = (snapshot_macro.INSTRUMENTS.get(block) or {}).get(ticker)
        if block not in snapshot.SPECIAL_BLOCKS or cfg is None:
            raise Refused(name + " is not a special instrument; expected "
                          "one of " + ", ".join(
                              b + "." + t
                              for b in snapshot.SPECIAL_BLOCKS
                              for t in snapshot_macro.INSTRUMENTS.get(b, {})))
        if "symbol" not in cfg:
            raise Refused(name + " does not come from " + snapshot.PROVIDER
                          + " and is not restated from it")
        held = (base.get(block) or {}).get(ticker)
        if not isinstance(held, dict) or held.get("close") is None:
            raise Refused(name + " has no close in " + base_name
                          + "; a correction restates a close, it does not "
                          "add one")

        entry, err = fetch(ticker, cfg, as_of)
        if err is not None:
            raise Refused(name + ": " + err)
        if entry.get("observed"):
            raise Refused(
                name + ": the provider has no bar dated " + base["as_of"]
                + " (its last that week is " + entry["observed"] + "). "
                "That is a stand-in, not the close for the date")
        if entry["close"] == held["close"]:
            raise Refused(name + " is already " + repr(held["close"])
                          + ", the provider's close for " + base["as_of"])

        correction[block][ticker] = {"close": entry["close"],
                                     "volume": entry.get("volume")}
        correction.setdefault("provenance", {}).setdefault(
            block, {})[ticker] = {"source": BACKFILL_SOURCE,
                                  "fetched_at": stamp}
        restated.append({"block": block, "ticker": ticker,
                         "was": {"close": held["close"],
                                 "volume": held.get("volume")}})

    correction["restated"] = restated
    correction["corrects"] = base_name
    correction["reason"] = reason.strip()
    # Through the rebuilder, so the bytes on disk are the ones a rebuild
    # would write and the next rebuild of this week is a no-op.
    return rebuild_corrections.apply_edits(base, correction)


def restate(directory: Path, date: str, names: list, reason: str,
            dry_run: bool = False, fetch=None, now=None) -> dict:
    base_path = directory / (date + ".json")
    target = directory / (date + ".corrected.json")
    if not base_path.is_file():
        raise Refused("no file " + str(base_path))
    if target.exists():
        raise Refused(
            target.name + " already exists. Add the restatement to it by "
            "hand (the close, its provenance label and a 'restated' entry), "
            "then run scripts/rebuild_corrections.py")
    base = json.loads(base_path.read_text(encoding="utf-8"))
    if base.get("as_of") != date:
        raise Refused(base_path.name + " has as_of " + repr(base.get("as_of")))
    doc = build_correction(base, base_path.name, names, reason, fetch, now)
    if not dry_run:
        rebuild_corrections.write_correction(target, doc)
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Write a correction that restates instrument closes.")
    ap.add_argument("--date", required=True,
                    help="the file's as_of, YYYY-MM-DD")
    ap.add_argument("--instrument", action="append", default=[],
                    metavar="BLOCK.TICKER", help="repeatable")
    ap.add_argument("--reason", required=True,
                    help="why, in a sentence; it is committed in the file")
    ap.add_argument("--dir", default=str(rebuild_corrections.WEEKLY),
                    help="panel directory (default: this repo's data/weekly)")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and report, write nothing")
    args = ap.parse_args(argv)

    try:
        doc = restate(Path(args.dir), args.date, args.instrument,
                      args.reason, dry_run=args.dry_run)
    except Refused as exc:
        print("REFUSED: " + str(exc))
        return 2
    for item in doc["restated"]:
        block, ticker = item["block"], item["ticker"]
        print("  %s.%s  %s -> %s  (%s)" % (
            block, ticker, item["was"]["close"], doc[block][ticker]["close"],
            doc["provenance"][block][ticker]["fetched_at"]))
    if args.dry_run:
        print("DRY RUN: nothing written")
        return 0
    print("Wrote " + args.date + ".corrected.json. Now run:")
    print("  python scripts/truth_check.py --repo . --pipeline . --feed --derive")
    print("and scripts/rederive_market_state.py if --derive says the state "
          "moved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
