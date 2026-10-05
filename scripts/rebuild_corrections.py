"""Re-derive correction files from their current base files.

A correction is a full copy of the base plus `corrects` and `reason`, per
DATA_FEED.md. That means it is a snapshot, and it goes stale the moment the
base changes -- for example when backfill_weekly.py adds tickers to a week that
already carries a correction. Readers prefer the correction, so the base file's
new tickers would be silently invisible.

This regenerates each correction by re-applying its recorded edits to the
current base. Run it after any backfill that touches a corrected week.

Two kinds of edit are recorded in a correction, and both are re-applied:

  * A zero-volume bar dropped from `series`. The record is the `missing`
    entry it became, with "zero-volume" in the reason (2026-08-21, AVB).
  * A special instrument's close restated from a later fetch. The record is
    `restated`: [{"block", "ticker", "was": {"close", "volume"}}], and the
    replacement carries its own `provenance.<block>.<ticker>` label
    (2026-08-28: US10Y, VIX and DXY held Thursday's close).
    scripts/restate_instruments.py writes these.

Each is re-applied only while the base still holds what the correction
replaced. If it does not, the base moved under the correction -- the provider
restated, or someone rewrote the week -- and the file is left alone with an
ABORT, which also fails the run: a backfill must not commit past a correction
nobody has looked at.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

WEEKLY = Path(__file__).resolve().parents[1] / "data" / "weekly"


class BaseMoved(RuntimeError):
    """The base no longer holds what the correction says it replaced."""


def recorded_edits(doc: dict) -> tuple:
    """(zero-volume drops by ticker, restated instruments) a correction records."""
    dropped = {m["ticker"]: m for m in doc.get("missing", [])
               if "zero-volume" in m.get("reason", "")}
    return dropped, list(doc.get("restated") or [])


def apply_edits(base: dict, correction: dict) -> dict:
    """The correction as it should read against `base` today. Pure.

    A fresh copy of the base with the correction's recorded edits re-applied
    and its `corrects`, `reason` and `restated` carried over. Raises
    BaseMoved rather than guess when the base no longer matches."""
    dropped, restated = recorded_edits(correction)
    fresh = copy.deepcopy(base)

    for ticker, entry in dropped.items():
        bar = fresh["series"].get(ticker)
        if bar is None:
            continue
        if bar.get("volume") != 0:
            raise BaseMoved(
                ticker + " no longer has volume 0 in the base; the provider "
                "may have restated. Review by hand.")
        fresh["series"].pop(ticker)
        # A per-series anchor for a series that is no longer there describes
        # nothing, and truth_check --feed refuses it. Drop it with the bar --
        # but only it: the block can also name the source of a rates
        # instrument (US2Y from Treasury), and that label must survive.
        prov = fresh.get("provenance")
        if isinstance(prov, dict) and isinstance(prov.get("series"), dict):
            prov["series"].pop(ticker, None)
            if not prov["series"]:
                prov.pop("series")
            if not prov:
                fresh.pop("provenance", None)
        fresh.setdefault("missing", []).append(entry)

    for item in restated:
        block, ticker = item["block"], item["ticker"]
        name = block + "." + ticker
        held = (fresh.get(block) or {}).get(ticker)
        was = item["was"]["close"]
        if not isinstance(held, dict) or held.get("close") != was:
            now = held.get("close") if isinstance(held, dict) else None
            raise BaseMoved(
                name + " is " + repr(now) + " in the base, not the "
                + repr(was) + " this correction replaced. Review by hand.")
        value = (correction.get(block) or {}).get(ticker)
        label = ((correction.get("provenance") or {}).get(block)
                 or {}).get(ticker)
        if not isinstance(value, dict) or not isinstance(label, dict):
            raise BaseMoved(
                name + " is recorded as restated, but the correction no "
                "longer carries its close and its provenance label. Review "
                "by hand.")
        fresh[block][ticker] = copy.deepcopy(value)
        # The replacement was fetched at another time than the file, and its
        # label is the only thing in the document that says so.
        fresh.setdefault("provenance", {}).setdefault(
            block, {})[ticker] = copy.deepcopy(label)

    fresh["missing"].sort(key=lambda m: m["ticker"])
    if restated:
        fresh["restated"] = copy.deepcopy(restated)
    fresh["corrects"] = correction["corrects"]
    fresh["reason"] = correction["reason"]
    return fresh


def write_correction(path: Path, doc: dict) -> None:
    """The one serialization every correction is written in, so that a file
    written by restate_instruments.py and one rebuilt here are the same bytes."""
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=True) + "\n",
                    encoding="utf-8", newline="\n")


def rebuild(corrected: Path) -> str:
    """Rebuild one correction in place. Returns "rebuilt", "skip" or "abort"."""
    doc = json.loads(corrected.read_text(encoding="utf-8"))
    base_name = doc.get("corrects")
    if not base_name:
        print("  skip " + corrected.name + ": no 'corrects' field")
        return "skip"
    base = corrected.with_name(base_name)
    if not base.is_file():
        print("  skip " + corrected.name + ": base " + base_name + " missing")
        return "skip"

    dropped, restated = recorded_edits(doc)
    if not dropped and not restated:
        print("  skip " + corrected.name + ": no zero-volume drops and no "
              "restated instruments recorded")
        return "skip"

    base_doc = json.loads(base.read_text(encoding="utf-8"))
    before = len(base_doc["series"])
    try:
        fresh = apply_edits(base_doc, doc)
    except BaseMoved as exc:
        print("  ABORT " + corrected.name + ": " + str(exc))
        return "abort"
    write_correction(corrected, fresh)

    did = []
    if dropped:
        did.append("dropped " + ", ".join(sorted(dropped)))
    if restated:
        did.append("restated " + ", ".join(
            item["block"] + "." + item["ticker"] for item in restated))
    print("  rebuilt " + corrected.name + ": base had " + str(before)
          + " series, correction now carries " + str(len(fresh["series"]))
          + " (" + "; ".join(did) + ")")
    return "rebuilt"


def main() -> int:
    # This took no arguments and read WEEKLY unconditionally, so a command
    # naming another directory was accepted in silence and rebuilt the live
    # panel instead. Parsing rejects that rather than quietly ignoring it.
    ap = argparse.ArgumentParser(
        description="Re-derive correction files from their current bases.")
    ap.add_argument("--dir", default=str(WEEKLY),
                    help="weekly file directory (default: this repo's "
                         "data/weekly)")
    args = ap.parse_args()

    weekly = Path(args.dir)
    if not weekly.is_dir():
        print("No such directory: " + str(weekly))
        return 1
    files = sorted(weekly.glob("*.corrected.json"))
    if not files:
        print("No correction files found.")
        return 0
    print("Rebuilding " + str(len(files)) + " correction file(s):")
    outcomes = [rebuild(f) for f in files]
    if "abort" in outcomes:
        # It used to exit 0 here, so the backfill workflow went on to commit
        # with a correction that no longer matched its base.
        print(str(outcomes.count("abort")) + " correction(s) left alone "
              "because their base moved. Nothing above was guessed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
