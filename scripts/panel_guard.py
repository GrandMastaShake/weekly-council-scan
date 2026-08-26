#!/usr/bin/env python3
"""Guard the weekly panel against silent series loss.

On 2026-08-26 a targeted backfill (`--only <44 tickers> --force`) replaced
every weekly file with just those 44 series -- 287 -> 44 across 107 files --
and the workflow reported success. The counts were printed. Nothing compared
them to anything, so a 243-name deletion read as green.

This is that comparison. Snapshot the panel before a write, compare after:
any file that loses series, or disappears entirely, fails the run.

    python scripts/panel_guard.py --snapshot /tmp/panel_before.json
    ... write to data/weekly ...
    python scripts/panel_guard.py --compare /tmp/panel_before.json

Growth is fine and expected -- that is what a backfill is for. Only loss
fails. Pure stdlib, no network.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

WEEKLY_DIR = os.path.join("data", "weekly")


def panel_counts(weekly_dir: str) -> dict:
    """Map filename -> number of series entries, for every weekly file."""
    if not os.path.isdir(weekly_dir):
        raise SystemExit("panel_guard: %s not found" % weekly_dir)
    counts = {}
    for name in sorted(os.listdir(weekly_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(weekly_dir, name)
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        series = doc.get("series")
        if not isinstance(series, dict):
            raise SystemExit(
                "panel_guard: %s has no 'series' object -- refusing to "
                "compare against a file shape I do not recognize" % name)
        counts[name] = len(series)
    return counts


def cmd_snapshot(weekly_dir: str, out_path: str) -> int:
    counts = panel_counts(weekly_dir)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(counts, f, ensure_ascii=True, indent=2, sort_keys=True)
        f.write("\n")
    total = sum(counts.values())
    print("panel_guard: snapshot %d file(s), %d series total -> %s"
          % (len(counts), total, out_path))
    return 0


def cmd_compare(weekly_dir: str, before_path: str) -> int:
    with open(before_path, "r", encoding="utf-8") as f:
        before = json.load(f)
    after = panel_counts(weekly_dir)

    lost = []       # (name, before, after) -- fewer series than before
    vanished = []   # (name, before)        -- file no longer present
    grew = 0
    added = 0

    for name, was in sorted(before.items()):
        if name not in after:
            vanished.append((name, was))
            continue
        now = after[name]
        if now < was:
            lost.append((name, was, now))
        elif now > was:
            grew += 1
    for name in after:
        if name not in before:
            added += 1

    print("panel_guard: %d file(s) before, %d after; %d grew, %d added"
          % (len(before), len(after), grew, added))

    if not lost and not vanished:
        print("panel_guard: OK -- no file lost series")
        return 0

    print("")
    print("PANEL GUARD FAILED -- series were removed, not added.")
    for name, was in vanished:
        print("  %-34s %4d -> FILE GONE" % (name, was))
    for name, was, now in lost:
        print("  %-34s %4d -> %4d  (-%d)" % (name, was, now, was - now))
    print("")
    print("A weekly file is an observation log. Losing series means the "
          "write replaced the week instead of adding to it.")
    print("Nothing has been committed. Inspect the diff before retrying.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fail a run that removes series from the weekly panel.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", metavar="PATH",
                   help="write current per-file series counts to PATH")
    g.add_argument("--compare", metavar="PATH",
                   help="compare current counts against a PATH snapshot")
    ap.add_argument("--weekly-dir", default=WEEKLY_DIR,
                    help="weekly file directory (default %s)" % WEEKLY_DIR)
    args = ap.parse_args()

    if args.snapshot:
        return cmd_snapshot(args.weekly_dir, args.snapshot)
    return cmd_compare(args.weekly_dir, args.compare)


if __name__ == "__main__":
    sys.exit(main())
