#!/usr/bin/env python3
"""Guard the lab ledgers: a row on file stays as it was (2026-11-25).

Every forward test in lab/ keeps its record in a JSON ledger that its own
script calls append-only: the weekend pick (Pass 67), the regime calls
(Pass 66), the trend book (Pass 63), the owner's marks, and the rest below.
A forward test is only worth its record if the record was written before
the result was known, and until now nothing outside each script's own
`append` checked that a past row was never changed or removed. A hand edit,
a script rerun with a bug, or a rewrite to tidy a file would all have
passed CI. The red team of 2026-11-25 found the gap.

THE RULE. For every ledger below that was in the commit compared with:

  * the file is still there;
  * every row it had (in the list under the key named here) is still in
    it, equal value for value, as many times as it was.

Order is not held: lab/forward_beatfall.py keeps its events sorted by
reaction day, so a late report lands among the rows before it (2df6a8e,
2026-11-16: 42 events added, 886 kept, none changed). New rows pass,
wherever they land. New ledgers pass. Values are compared, not bytes,
so a file that was only re-serialised passes. The header fields beside the
rows (rules, registered, schema) are not held: a script may restate its
rules, and the rows are the record.

    python scripts/lab_ledger_guard.py --against HEAD^

CI runs it beside scripts/panel_guard.py, against the same commit. Like the
panel guard it reports and does not block, because main is not protected.
Stdlib only. git's own environment is dropped before git is asked, for the
reason CLAUDE.md gives under "Before anything".
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# path -> the key that holds the rows (None: the file is the list).
LEDGERS = {
    "lab/weekend_picks.json": None,
    "lab/regime_calls.json": "calls",
    "lab/book_ledger.json": "weeks",
    "lab/owner_marks.json": "marks",
    "lab/beatfall_events.json": "events",
    "lab/dartboard_ledger.json": "rows",
    "lab/sleeve_ledger.json": "rows",
    "lab/slow_ledger.json": "rows",
}

_GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
            "GIT_COMMON_DIR", "GIT_PREFIX", "GIT_IMPLICIT_WORK_TREE",
            "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_SHALLOW_FILE",
            "GIT_GRAFT_FILE", "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE")


def _git(root: str, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV}
    return subprocess.run(["git", "-C", root] + list(args), capture_output=True, env=env)


def _key(row) -> str:
    return json.dumps(row, sort_keys=True, ensure_ascii=True)


def rows_of(doc, key):
    """The rows of one ledger, or None when the shape is not a ledger's."""
    rows = doc if key is None else (doc.get(key) if isinstance(doc, dict) else None)
    return rows if isinstance(rows, list) else None


def compare(path: str, key, before, after) -> list:
    """Problems with one ledger, as lines. `before` is the committed doc;
    `after` is the doc on disk, or None when the file is gone."""
    old = rows_of(before, key)
    if old is None:
        return []                       # not a ledger then: nothing was held
    if after is None:
        return ["%s: the file is gone; it held %d row(s)" % (path, len(old))]
    new = rows_of(after, key)
    if new is None:
        return ["%s: no list under %r any more; it held %d row(s)"
                % (path, key or "(the file)", len(old))]
    left = {}
    for row in new:
        k = _key(row)
        left[k] = left.get(k, 0) + 1
    out = []
    for i, row in enumerate(old):
        k = _key(row)
        if left.get(k, 0) > 0:
            left[k] -= 1
            continue
        out.append("%s: row %d is gone or changed (%d row(s) held, %d now)\n    was: %s"
                   % (path, i, len(old), len(new), k[:300]))
    return out


def check(root: str, commit: str) -> int:
    if _git(root, "rev-parse", "--verify", "--quiet", commit + "^{commit}").returncode != 0:
        print("lab ledgers: %s is not a commit here; nothing compared" % commit)
        return 1
    problems, held, added = [], 0, 0
    for path, key in sorted(LEDGERS.items()):
        shown = _git(root, "show", "%s:%s" % (commit, path))
        if shown.returncode != 0:
            continue                    # new ledger, or never there
        try:
            before = json.loads(shown.stdout.decode("utf-8"))
        except ValueError:
            continue                    # nothing readable was held
        full = os.path.join(root, *path.split("/"))
        after = None
        if os.path.isfile(full):
            with open(full, "r", encoding="utf-8") as f:
                try:
                    after = json.load(f)
                except ValueError:
                    problems.append("%s: does not parse any more" % path)
                    continue
        found = compare(path, key, before, after)
        problems += found
        old = rows_of(before, key) or []
        if not found:
            held += len(old)
            added += len(rows_of(after, key) or []) - len(old)
    if problems:
        print("LAB LEDGER REGRESSION -- committed rows were changed or removed:")
        for p in problems:
            print("  " + p)
        return 1
    print("lab ledgers intact: %d row(s) unchanged, %d added" % (held, added))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--against", required=True, help="the commit to compare the files on disk with")
    ap.add_argument("--repo", default=ROOT)
    a = ap.parse_args(argv)
    return check(a.repo, a.against)


if __name__ == "__main__":
    sys.exit(main())
