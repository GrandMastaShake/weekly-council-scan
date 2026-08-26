"""Re-derive correction files from their current base files.

A correction is a full copy of the base plus `corrects` and `reason`, per
DATA_FEED.md. That means it is a snapshot, and it goes stale the moment the
base changes -- for example when backfill_weekly.py adds tickers to a week that
already carries a correction. Readers prefer the correction, so the base file's
new tickers would be silently invisible.

This regenerates each correction by re-applying its recorded edit to the
current base. Run it after any backfill that touches a corrected week.

The only edit type currently supported is dropping zero-volume bars, which is
what every existing correction does.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WEEKLY = Path(__file__).resolve().parents[1] / "data" / "weekly"


def rebuild(corrected: Path) -> bool:
    doc = json.loads(corrected.read_text(encoding="utf-8"))
    base_name = doc.get("corrects")
    if not base_name:
        print("  skip " + corrected.name + ": no 'corrects' field")
        return False
    base = corrected.with_name(base_name)
    if not base.is_file():
        print("  skip " + corrected.name + ": base " + base_name + " missing")
        return False

    dropped = {m["ticker"]: m for m in doc.get("missing", [])
               if "zero-volume" in m.get("reason", "")}
    if not dropped:
        print("  skip " + corrected.name + ": no zero-volume drops recorded")
        return False

    fresh = json.loads(base.read_text(encoding="utf-8"))
    before = len(fresh["series"])
    for ticker, entry in dropped.items():
        bar = fresh["series"].get(ticker)
        if bar is None:
            continue
        if bar.get("volume") != 0:
            print("  ABORT " + corrected.name + ": " + ticker
                  + " no longer has volume 0 in the base; the provider may have "
                    "restated. Review by hand.")
            return False
        fresh["series"].pop(ticker)
        # A per-series anchor for a series that is no longer there describes
        # nothing, and truth_check --feed refuses it. Drop it with the bar.
        prov = fresh.get("provenance")
        if isinstance(prov, dict) and isinstance(prov.get("series"), dict):
            prov["series"].pop(ticker, None)
            if not prov["series"]:
                fresh.pop("provenance", None)
        fresh.setdefault("missing", []).append(entry)

    fresh["missing"].sort(key=lambda m: m["ticker"])
    fresh["corrects"] = doc["corrects"]
    fresh["reason"] = doc["reason"]
    corrected.write_text(json.dumps(fresh, indent=2, ensure_ascii=True) + "\n",
                         encoding="utf-8", newline="\n")
    print("  rebuilt " + corrected.name + ": base had " + str(before)
          + " series, correction now carries " + str(len(fresh["series"]))
          + " (dropped " + ", ".join(sorted(dropped)) + ")")
    return True


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
    for f in files:
        rebuild(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
