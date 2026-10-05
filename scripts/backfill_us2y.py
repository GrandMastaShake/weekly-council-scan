"""backfill_us2y.py -- the Treasury 2-year for weeks whose file cannot supply it.

Every weekly file through 2026-10-02 committed the 2YY=F future under
"US2Y" (see the research log in scan_pipeline/snapshot_macro.py for why that
was never the cash yield). Those files are observations and are never
edited, so the Treasury 2-year for those weeks lives beside them in
<data>/us2y_treasury.json, and snapshot.cash_2y_series() reads it for any
week whose own file holds no Treasury-sourced US2Y.

This writes that file. It is also the repair path, for three kinds of week:

  * a Friday the Treasury fetch failed, or ran before the day's row was up;
  * a holiday Friday, which the fetch never fills on the night (below);
  * a Friday written by a runner still on the old code, whose file holds
    the future under "US2Y" with no Treasury label. The old deriver puts
    that number in market_state.json and `truth_check --feed` fails on it.

Each is filled from Treasury's archive without touching the weekly file,
and market_state.json is then re-derived through the whole chain, because
a new entry changes what it should say. The archive is permanent and is not
restated the way a provider's bars are, so a late fill reads the number the
Friday fetch would have.

Append-only by week, like the panel it sits beside: a week that has an
entry keeps it. --check re-reads the archive and REPORTS a difference; it
never rewrites one, because a changed entry is a decision, not a refresh.

A week is filled with the row dated its as_of. A holiday gets the last row
of the same Mon..Fri week, recorded as "observed", but only once the
archive holds a row dated AFTER as_of -- that is the proof Treasury skipped
the day rather than posted late. Until then the week stays a gap and this
exits 1. The rule is snapshot_macro.select_treasury_row, the one the Friday
fetch follows.

CLI:
  python scripts/backfill_us2y.py [--data data] [--facts PATH]
                                  [--dry-run] [--check]

  --data     the data root; reads <data>/weekly, writes
             <data>/us2y_treasury.json and re-derives
             <data>/market_state.json
  --facts    macro facts for the re-derive (default: macro/facts.json
             beside the data root)
  --dry-run  fetch and report the weeks that would be added; write nothing
  --check    compare every committed Treasury 2-year (this file's entries
             and the weekly files' own) against the archive; exit 1 on any
             difference; write nothing
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

# Repo root = the nearest ancestor holding the scan_pipeline package. Copied
# from scripts/backfill_weekly.py deliberately; see the note there.
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

from scan_pipeline import snapshot          # noqa: E402
from scan_pipeline import snapshot_macro    # noqa: E402
import rederive_market_state                # noqa: E402

SCHEMA = "us2y-treasury/v1"
SOURCE = snapshot.TREASURY_SOURCE + "-backfill"     # "treasury-backfill"
COLUMN = snapshot_macro.INSTRUMENTS["rates"][snapshot.CASH_2Y]["column"]

ABOUT = (
    "Treasury par yield curve 2-year for the weeks whose weekly file holds "
    "no Treasury-sourced rates.US2Y: every week through 2026-10-02 (those "
    "files carry the 2YY=F future under US2Y and are never edited) and any "
    "later week whose Treasury fetch failed. Keyed by the weekly file's "
    "as_of; 'observed' is the session the value was published for when "
    "that is not as_of. Append-only by week. Written by "
    "scripts/backfill_us2y.py; read by snapshot.cash_2y_series(). "
    "DATA_FEED.md sec.1a."
)


def empty_history() -> dict:
    return {"schema": SCHEMA, "instrument": snapshot.CASH_2Y,
            "source": SOURCE, "column": COLUMN, "session": "close",
            "about": ABOUT, "series": {}}


def load_history(path: str) -> dict:
    """The committed history document, or a fresh empty one."""
    if not os.path.exists(path):
        return empty_history()
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict) or not isinstance(doc.get("series"), dict):
        raise SystemExit(
            "backfill_us2y: %s has no 'series' object -- refusing to extend "
            "a file whose shape I do not recognize" % path)
    return doc


def cash_gaps(docs: list, series: dict) -> list:
    """Weeks with no Treasury 2-year at all: no Treasury-sourced US2Y in
    their own file and no entry here. Oldest first."""
    return [d for d, doc in docs
            if d not in series
            and not snapshot.is_treasury_sourced(doc, "rates",
                                                 snapshot.CASH_2Y)]


def observe(week: str) -> tuple:
    """(close, observed_iso, error) for one week, from the archive."""
    as_of = date.fromisoformat(week)
    try:
        rows = snapshot_macro.week_rows(as_of)
    except Exception as exc:
        return None, None, "treasury: %s: %s" % (type(exc).__name__,
                                                 str(exc)[:160])
    value, observed, err = snapshot_macro.select_treasury_row(
        rows, as_of, COLUMN)
    if err is not None:
        return None, None, err
    return round(value, 4), observed.isoformat(), None


def run_fill(docs: list, history: dict, path: str, data_root: str,
             facts_path: str | None, dry_run: bool) -> int:
    stamp = snapshot_macro._utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    series = history["series"]
    gaps = cash_gaps(docs, series)
    if not gaps:
        print("Nothing to add: all %d week(s) have a Treasury 2-year."
              % len(docs))
        return 0

    print("%d week(s) without a Treasury 2-year: %s .. %s"
          % (len(gaps), gaps[0], gaps[-1]))
    added, failed = [], []
    for week in gaps:
        close, observed, err = observe(week)
        if err is not None:
            failed.append((week, err))
            continue
        entry = {"close": close, "fetched_at": stamp}
        if observed != week:
            entry["observed"] = observed
        series[week] = entry
        added.append(week)

    for week in added:
        note = ("  (observed %s)" % series[week]["observed"]
                if "observed" in series[week] else "")
        print("  + %s  %.2f%s" % (week, series[week]["close"], note))
    for week, err in failed:
        print("  ! %s  not filled: %s" % (week, err))

    # A week still without a value is not a success, whatever else was
    # written: market_state will carry a null 2-year for it.
    status = 1 if failed else 0
    if dry_run:
        print("DRY RUN: nothing written (%d would be added)" % len(added))
        return status
    if not added:
        return status

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(snapshot.canonical_json(history))
    print("Wrote %s: %d added, %d total" % (path, len(added), len(series)))

    # The history is an input to market_state.json, so a new entry makes the
    # committed state stale, and `truth_check --feed` says so. Leave the two
    # in step rather than leave that for whoever commits this.
    if os.path.isfile(os.path.join(data_root, "market_state.json")):
        status = max(status,
                     rederive_market_state.rederive(data_root, facts_path))
    return status


def run_check(docs: list, history: dict) -> int:
    """Every committed Treasury 2-year against the archive. Writes nothing."""
    committed = {}          # week -> (close, observed, where)
    for week, rec in history["series"].items():
        committed[week] = (rec.get("close"), rec.get("observed", week),
                           snapshot.US2Y_HISTORY_FILE)
    for week, doc in docs:
        if not snapshot.is_treasury_sourced(doc, "rates", snapshot.CASH_2Y):
            continue
        own = (doc.get("rates") or {}).get(snapshot.CASH_2Y) or {}
        prov = doc["provenance"]["rates"][snapshot.CASH_2Y]
        # the week's own value is the one the deriver reads; check that one
        committed[week] = (own.get("close"), prov.get("observed", week),
                           "weekly/%s.json" % week)

    diffs = []
    for week in sorted(committed):
        close, observed, where = committed[week]
        want, want_observed, err = observe(week)
        if err is not None:
            diffs.append("%s (%s): archive not readable: %s"
                         % (week, where, err))
        elif (close, observed) != (want, want_observed):
            diffs.append("%s (%s): committed %s observed %s, archive says "
                         "%s observed %s"
                         % (week, where, close, observed, want,
                            want_observed))
    if diffs:
        print("%d of %d committed Treasury 2-year value(s) differ from the "
              "archive:" % (len(diffs), len(committed)))
        for line in diffs:
            print("  " + line)
        print("Nothing was changed. A committed value that the archive no "
              "longer agrees with is a decision for a person.")
        return 1
    print("OK: %d committed Treasury 2-year value(s) match the archive"
          % len(committed))
    return 0


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Fill the Treasury 2-year for weeks whose weekly file "
                    "cannot supply it (data/us2y_treasury.json).")
    p.add_argument("--data", default="data",
                   help="data root (default: data)")
    p.add_argument("--facts", default=None,
                   help="macro facts file for the market_state re-derive "
                        "(default: macro/facts.json beside the data root)")
    p.add_argument("--dry-run", action="store_true",
                   help="fetch and report; write nothing")
    p.add_argument("--check", action="store_true",
                   help="compare committed values against the archive; "
                        "exit 1 on any difference; write nothing")
    a = p.parse_args(argv)

    weekly_dir = os.path.join(a.data, "weekly")
    if not os.path.isdir(weekly_dir):
        print("No such directory: " + weekly_dir)
        return 1
    docs = snapshot._load_weekly_files(weekly_dir)
    path = snapshot.us2y_history_path(weekly_dir)
    history = load_history(path)

    if a.check:
        return run_check(docs, history)
    return run_fill(docs, history, path, a.data, a.facts, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
