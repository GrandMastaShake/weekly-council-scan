#!/usr/bin/env python3
"""Guard the panel: what a file held, it still holds.

A weekly or daily file is an observation (DATA_FEED.md sec.1, sec.4). It may
gain entries -- that is what a backfill is for -- and nothing it already
holds is rewritten. This is the check that says so, because twice nothing
did.

On 2026-08-26 a targeted backfill (`--only <44 tickers> --force`) replaced
every weekly file with just those 44 series -- 287 -> 44 across 107 files --
and the workflow reported success. The counts were printed with nothing to
compare them to. The first version of this guard was that comparison: series
per file, before and after.

A count cannot see a bar that changed. Until 2026-10-06 `--merge` fetched a
named ticker again and wrote it over the committed bar. Rehearsed on a copy
of the panel it wrote over 4,612 bars in 107 files; this guard printed
"0 grew, 0 added; OK -- no file lost series", and CI, which carried its own
copy of the count, would have said the same. That writer is closed. The rule
below is for the next one: the runner's mirror of the backfill script, whose
--merge still overwrites; a copy of snapshot.write_weekly from before it
refused a week already on file, which the runner's is until it is synced; a
hand edit; a one-off script.

THE RULE. For every panel file that was there before:

  * the file is still there;
  * every entry it held -- in `series`, `rates`, `vol`, `commodities`, `fx`
    -- is still there, with the same bar;
  * each of those entries still carries the label it had: its own
    `provenance.<block>.<ticker>`, or none;
  * the file's `source`, `fetched_at` and `session_note` are unchanged. They
    are the label of every entry that has none of its own, and `fetched_at`
    is the adjustment anchor of every close under it.

New files pass, and so do new entries, under whatever label they arrive
with. Values are compared, not bytes: a file that was only re-serialised
passes.

TWO THINGS MAY CHANGE WHAT A FILE HELD, and each has to say so.

  * A correction that restates an instrument records it in `restated`
    (DATA_FEED.md sec.1b). In a <date>.corrected.json, an instrument named
    by a `restated` entry that was not there before may change its bar and
    its label. Nothing else in a correction may: its series are a copy of
    its base's.
  * A declared rewrite: `--compare PATH --rewrite START END`. The weekly
    files dated START..END, and their corrections, which are rebuilt from
    them, were rewritten whole and on purpose by a full-universe `--force`
    backfill. Inside the range a bar, a label and a file stamp may change,
    and the guard prints how many did. Outside it the rule holds. The
    "Backfill weekly panel" workflow passes this when it is dispatched with
    `rewrite` ticked, and at no other time.

An entry that VANISHED fails under both. Neither is a way to lose a bar.

WHAT THIS DOES NOT SAY. It compares a file with what the same file held. A
new file held nothing, so a NEW correction is not compared with the base it
corrects. That is `truth_check --feed`'s to say, for data/weekly and
data/daily alike: its series are its base's, bar for bar, outside a
recorded zero-volume drop (since 2026-10-07; until then only
tests/test_instrument_sessions.py said so, and only for data/weekly), and
its instruments and their labels are the base's outside what `restated`
records.

Three things a correction or a repair can need have no way through here,
on purpose: dropping one more zero-volume bar from a correction that
exists, withdrawing a correction, and reverting a bad write. Each changes
what a file held, so each fails, and goes in over a red check by someone
who has read why.

    python scripts/panel_guard.py --snapshot /tmp/panel_before.json
    ... write to data/weekly ...
    python scripts/panel_guard.py --compare /tmp/panel_before.json

    python scripts/panel_guard.py --against HEAD^

--against compares a commit with the files on disk, so one comparison
answers in three places: the backfill workflow (--snapshot / --compare,
around its write), CI (--against the tip a push replaced, or a pull
request's base) and the daily job (--against HEAD, before it commits).
There is no --rewrite with it. A commit that changes what the panel held
fails CI whatever it says about itself. And a "before" that holds no panel
file at all is refused by every command, not passed: it is what a directory
the commit does not track looks like.

The panel is the weekly directory and the `daily` directory beside it.

Pure stdlib, no network. --against needs git.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

WEEKLY_DIR = os.path.join("data", "weekly")
BLOCKS = ("series", "rates", "vol", "commodities", "fx")
STAMPS = ("source", "fetched_at", "session_note")
SCHEMA = "panel-guard/2"
CORRECTED = ".corrected.json"

SHOW_FILES = 40     # files spelled out in a failure; the totals cover the rest
SHOW_ENTRIES = 4    # entries named on one line of it

_DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})(\.corrected)?\.json$")
_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def refuse(message: str):
    raise SystemExit("panel_guard: " + message)


# ---------------------------------------------------------------------------
# Reading the panel
# ---------------------------------------------------------------------------
def parse(raw: bytes, name: str) -> dict:
    """One panel file, parsed. Refused unless it is shaped like one."""
    try:
        doc = json.loads(raw.decode("utf-8"))
    except ValueError as exc:       # not UTF-8, or not JSON
        refuse("%s does not parse as JSON (%s) -- refusing to compare "
               "against a file I cannot read" % (name, exc))
    if not isinstance(doc, dict) or not isinstance(doc.get("series"), dict):
        refuse("%s has no 'series' object -- refusing to compare against a "
               "file shape I do not recognize" % name)
    return doc


def panel_dirs(weekly_dir: str, daily_dir) -> list:
    """[(role, directory, required)]. The daily directory is the one beside
    the weekly one unless it is named, and is guarded when it exists."""
    weekly = os.path.normpath(weekly_dir)
    if daily_dir:
        return [("weekly", weekly, True),
                ("daily", os.path.normpath(daily_dir), True)]
    beside = os.path.join(os.path.dirname(os.path.abspath(weekly)), "daily")
    return [("weekly", weekly, True), ("daily", beside, False)]


def panel_on_disk(dirs: list) -> dict:
    """{"weekly/<name>": document} for every .json file in the panel."""
    panel = {}
    for role, directory, required in dirs:
        if not os.path.isdir(directory):
            if required:
                refuse("%s not found" % directory)
            continue
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".json"):
                continue
            # Bytes, decoded as UTF-8 by parse(): the same reading a blob out
            # of a commit gets, whatever the line endings on this machine.
            key = role + "/" + name
            try:
                with open(os.path.join(directory, name), "rb") as f:
                    raw = f.read()
            except OSError as exc:      # a directory by that name, say
                refuse("cannot read %s (%s) -- refusing to compare against "
                       "a file I cannot read" % (key, exc))
            panel[key] = parse(raw, key)
    return panel


# What git itself calls repository-local (`git rev-parse --local-env-vars`).
# git hands a hook, and a command run by `rebase --exec`, the repository it
# is working on in these: in a linked worktree that is GIT_DIR and no work
# tree. Left in place, every question below was answered about that
# repository with the weekly directory taken for its top: the commit showed
# no panel under it, and the guard printed "0 file(s) before ... OK" over a
# panel with three changed bars. The repository is the one the directory is
# in, and nothing else.
_GIT_LOCAL_ENV = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT", "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX",
    "GIT_SHALLOW_FILE", "GIT_COMMON_DIR")


def _git(cwd: str, *args, data=None, check=True):
    env = {name: value for name, value in os.environ.items()
           if name not in _GIT_LOCAL_ENV}
    try:
        run = subprocess.run(["git", "-C", cwd] + list(args), input=data,
                             capture_output=True, env=env)
    except OSError as exc:
        refuse("cannot run git (%s), and --against needs it" % exc)
    if check and run.returncode != 0:
        refuse("git %s failed: %s" % (
            " ".join(args), run.stderr.decode("utf-8", "replace").strip()))
    return run


def panel_at(commit: str, dirs: list) -> dict:
    """The same mapping, read out of a commit instead of off the disk."""
    panel = {}
    for role, directory, _required in dirs:
        # git is asked from the nearest directory that exists, so a panel
        # directory the commit had and the tree no longer has is still read.
        full = os.path.abspath(directory)
        anchor = full
        while not os.path.isdir(anchor):
            parent = os.path.dirname(anchor)
            if parent == anchor:
                break
            anchor = parent
        inside = _git(anchor, "rev-parse", "--show-toplevel", "--show-prefix",
                      check=False)
        if inside.returncode != 0:
            refuse("%s is not inside a git repository, and --against reads "
                   "the panel out of a commit" % directory)
        top, prefix = (inside.stdout.decode("utf-8").replace("\r", "")
                       .split("\n") + [""])[:2]
        tail = os.path.relpath(full, anchor)
        rel = prefix + ("" if tail == "." else tail.replace(os.sep, "/") + "/")

        resolved = _git(top, "rev-parse", "--verify", "--quiet",
                        commit + "^{commit}", check=False)
        if resolved.returncode != 0:
            refuse("%r is not a commit in %s -- nothing to compare the panel "
                   "with. A check that cannot find its 'before' has not "
                   "passed." % (commit, top))
        sha = resolved.stdout.decode("ascii").strip()

        listing = _git(top, "ls-tree", "-z", "--name-only", sha,
                       *(["--", rel] if rel else [])).stdout.decode("utf-8")
        paths = [p for p in listing.split("\0") if p.endswith(".json")]
        if not paths:
            continue
        # One process for the whole directory, not one per file.
        out = _git(top, "cat-file", "--batch", data="".join(
            "%s:%s\n" % (sha, p) for p in paths).encode("utf-8")).stdout
        at = 0
        for path in paths:
            key = role + "/" + path[len(rel):]
            end = out.find(b"\n", at)
            header = out[at:end].decode("utf-8", "replace").split()
            if end < 0 or len(header) != 3 or header[1] != "blob":
                refuse("could not read %s at %s" % (path, sha[:7]))
            size = int(header[2])
            blob = out[end + 1:end + 1 + size]
            at = end + 1 + size + 1
            panel[key] = parse(blob, "%s at %s" % (key, sha[:7]))
    return panel


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------
def same(a, b) -> bool:
    """Equal as JSON values. 100 and 100.0 are one number; true is not 1; and
    a NaN, which == would call different from itself, is the NaN it was."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b or (a != a and b != b)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def entries(doc: dict, block: str) -> dict:
    held = doc.get(block)
    return held if isinstance(held, dict) else {}


def own_label(doc: dict, block: str, ticker: str):
    """provenance.<block>.<ticker>, or None: the entry is the file's."""
    prov = doc.get("provenance")
    labels = prov.get(block) if isinstance(prov, dict) else None
    return labels.get(ticker) if isinstance(labels, dict) else None


def restated_pairs(doc: dict) -> set:
    """The (block, ticker) pairs a correction records as restated."""
    record = doc.get("restated")
    return {(item["block"], item["ticker"])
            for item in (record if isinstance(record, list) else [])
            if isinstance(item, dict)
            and isinstance(item.get("block"), str)
            and isinstance(item.get("ticker"), str)}


def diff_file(key: str, was: dict, now: dict) -> dict:
    """What one file no longer holds as it held it."""
    # Only a correction restates, only an instrument, and only an entry that
    # is new in `restated`: one already on record is as fixed as any close.
    fresh = (restated_pairs(now) - restated_pairs(was)
             if key.endswith(CORRECTED) else set())
    out = {"gone": [], "changed": [], "relabelled": [], "stamps": [],
           "restated": [], "grew": False, "held": 0}
    for block in BLOCKS:
        before, after = entries(was, block), entries(now, block)
        if any(t not in before for t in after):
            out["grew"] = True
        for ticker in sorted(before):
            out["held"] += 1
            if ticker not in after:
                out["gone"].append((block, ticker))
                continue
            bar = not same(before[ticker], after[ticker])
            labels = (own_label(was, block, ticker),
                      own_label(now, block, ticker))
            label = not same(*labels)
            if (bar or label) and block != "series" \
                    and (block, ticker) in fresh:
                out["restated"].append(
                    (block, ticker, before[ticker], after[ticker]))
                continue
            if bar:
                out["changed"].append(
                    (block, ticker, before[ticker], after[ticker]))
            if label:
                out["relabelled"].append((block, ticker) + labels)
    for field in STAMPS:
        if not same(was.get(field), now.get(field)):
            out["stamps"].append((field, was.get(field), now.get(field)))
    return out


def in_rewrite(key: str, rewrite) -> bool:
    """Is this file one a declared rewrite covers? Weekly files only: the
    backfill writes nothing else, so a daily file is never inside one."""
    if not rewrite:
        return False
    role, _, name = key.partition("/")
    dated = _DATED.match(name)
    return (role == "weekly" and dated is not None
            and rewrite[0] <= dated.group(1) <= rewrite[1])


def compare(before: dict, after: dict, rewrite=None) -> dict:
    """What the panel held against what it holds. Pure."""
    result = {
        "before": len(before), "after": len(after),
        "added": sum(1 for key in after if key not in before),
        "grew": 0, "held": 0,
        "vanished": [],     # (key, entries it held)
        "failed": {},       # key -> {kind: [...]}
        "restated": [],     # (key, block, ticker, was, now)
        "declared": {"files": 0, "rewritten": 0, "changed": 0,
                     "relabelled": 0, "stamps": 0},
    }
    for key in sorted(before):
        was = before[key]
        if key not in after:
            result["vanished"].append(
                (key, sum(len(entries(was, b)) for b in BLOCKS)))
            continue
        diff = diff_file(key, was, after[key])
        result["grew"] += diff["grew"]
        result["held"] += diff["held"]
        result["restated"] += [(key,) + item for item in diff["restated"]]
        kinds = ("gone", "changed", "relabelled", "stamps")
        if in_rewrite(key, rewrite):
            declared = result["declared"]
            declared["files"] += 1
            declared["rewritten"] += any(diff[k] for k in kinds[1:])
            for kind in kinds[1:]:
                declared[kind] += len(diff[kind])
            kinds = kinds[:1]       # a rewrite may change; it may not remove
        bad = {kind: diff[kind] for kind in kinds if diff[kind]}
        if bad:
            result["failed"][key] = bad
    return result


# ---------------------------------------------------------------------------
# Saying it
# ---------------------------------------------------------------------------
def show(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def bar_change(was, now) -> str:
    if isinstance(was, dict) and isinstance(now, dict) \
            and set(was) | set(now) <= {"close", "volume"}:
        return ", ".join(
            "%s %s -> %s" % (field, show(was.get(field)), show(now.get(field)))
            for field in ("close", "volume")
            if not same(was.get(field), now.get(field)))
    return "%s -> %s" % (show(was), show(now))


def label_change(was, now) -> str:
    return "label %s -> %s" % ("none" if was is None else show(was),
                               "none" if now is None else show(now))


def some(items: list, sep: str = "; ") -> str:
    more = len(items) - SHOW_ENTRIES
    return sep.join(items[:SHOW_ENTRIES]) + (
        sep + "and %d more" % more if more > 0 else "")


def report(result: dict, rewrite, after_failure: str) -> int:
    print("panel_guard: %d file(s) before, %d after; %d grew, %d added"
          % (result["before"], result["after"], result["grew"],
             result["added"]))
    for key, block, ticker, was, now in result["restated"]:
        print("panel_guard: %s restates %s.%s, %s -- recorded in its "
              "`restated`" % (key, block, ticker, bar_change(was, now)
                              or "relabelled"))
    declared = result["declared"]
    if rewrite:
        print("panel_guard: DECLARED REWRITE of the weekly files %s..%s. "
              "%d file(s) on file in that range, %d rewritten: %d bar(s) "
              "changed, %d label(s) changed, %d file stamp(s) changed. "
              "Declared, so allowed; nothing outside the range may change, "
              "and nothing anywhere may vanish."
              % (rewrite[0], rewrite[1], declared["files"],
                 declared["rewritten"], declared["changed"],
                 declared["relabelled"], declared["stamps"]))

    if not result["vanished"] and not result["failed"]:
        if rewrite and declared["rewritten"]:
            print("panel_guard: OK -- every entry the panel held is still "
                  "there, and unchanged outside the declared rewrite")
        else:
            print("panel_guard: OK -- every one of the %d entries the panel "
                  "held is still there, unchanged" % result["held"])
        return 0

    print("")
    print("PANEL GUARD FAILED -- the panel no longer holds what it held.")
    totals = {"gone": 0, "changed": 0, "relabelled": 0, "stamps": 0}
    for key, held in result["vanished"]:
        print("  %-34s FILE GONE (%d entries)" % (key, held))
    shown = 0
    for key in sorted(result["failed"]):
        bad = result["failed"][key]
        for kind in totals:
            totals[kind] += len(bad.get(kind, []))
        shown += 1
        if shown > SHOW_FILES:
            continue
        print("  " + key)
        if "gone" in bad:
            print("      %d gone: %s" % (len(bad["gone"]), some(
                [b + "." + t for b, t in bad["gone"]], ", ")))
        if "changed" in bad:
            print("      %d changed: %s" % (len(bad["changed"]), some(
                ["%s.%s %s" % (b, t, bar_change(was, now))
                 for b, t, was, now in bad["changed"]])))
        if "relabelled" in bad:
            print("      %d relabelled: %s" % (len(bad["relabelled"]), some(
                ["%s.%s %s" % (b, t, label_change(was, now))
                 for b, t, was, now in bad["relabelled"]])))
        for field, was, now in bad.get("stamps", []):
            print("      file stamp: %s %s -> %s"
                  % (field, show(was), show(now)))
    if shown > SHOW_FILES:
        print("  ... and %d more file(s)" % (shown - SHOW_FILES))
    print("  TOTAL: %d file(s) gone; in %d other file(s), %d entries gone, "
          "%d bar(s) changed, %d label(s) changed, %d file stamp(s) changed"
          % (len(result["vanished"]), len(result["failed"]), totals["gone"],
             totals["changed"], totals["relabelled"], totals["stamps"]))
    print("")
    print("A panel file is an observation. It may gain entries; what it "
          "holds is not rewritten.")
    print("  * A close the provider has restated goes in "
          "<date>.corrected.json (DATA_FEED.md sec.1).")
    print("  * Names are added to a week with backfill_weekly.py --only ... "
          "--merge, which leaves every bar the week holds alone.")
    print("  * A whole-universe rewrite is declared: the \"Backfill weekly "
          "panel\" workflow with `rewrite` ticked. It may change a bar. It "
          "may not remove one.")
    print(after_failure)
    return 1


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
# A "before" with no panel file in it has nothing to hold a write to, and a
# comparison against it passes anything: "0 file(s) before ... OK". That is
# also what a mistake looks like -- a scratch copy the commit does not track,
# a directory that is not the panel -- so all three commands refuse it.
NOTHING_BEFORE = ("A comparison against nothing would pass any write, and a "
                  "check with no 'before' has not passed.")


def cmd_snapshot(dirs: list, out_path: str) -> int:
    panel = panel_on_disk(dirs)
    if not panel:
        refuse("no panel file in %s -- nothing to record. %s"
               % (dirs[0][1], NOTHING_BEFORE))
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": SCHEMA, "files": panel}, f, ensure_ascii=True,
                  sort_keys=True, separators=(",", ":"))
        f.write("\n")
    held = sum(len(entries(doc, b)) for doc in panel.values() for b in BLOCKS)
    print("panel_guard: snapshot %d file(s), %d entries -> %s"
          % (len(panel), held, out_path))
    return 0


def cmd_compare(dirs: list, before_path: str, rewrite) -> int:
    try:
        with open(before_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
    except (OSError, ValueError) as exc:
        refuse("cannot read the snapshot %s (%s)" % (before_path, exc))
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA \
            or not isinstance(snapshot.get("files"), dict):
        # The count-only guard wrote {file: number of series}. That cannot
        # answer for a bar, and reading it as if it could would pass anything.
        refuse("%s is not a %s snapshot -- refusing to compare bars against "
               "one that does not record them. Take it again with --snapshot."
               % (before_path, SCHEMA))
    if not snapshot["files"]:
        refuse("%s records no panel file. %s" % (before_path, NOTHING_BEFORE))
    return report(
        compare(snapshot["files"], panel_on_disk(dirs), rewrite), rewrite,
        "Nothing has been committed. Inspect the diff before retrying.")


def cmd_against(dirs: list, commit: str) -> int:
    before = panel_at(commit, dirs)
    if not before:
        refuse("%s holds no panel file under %s. %s A copy of the panel "
               "that the commit does not track is compared with --snapshot "
               "and --compare." % (commit, dirs[0][1], NOTHING_BEFORE))
    return report(
        compare(before, panel_on_disk(dirs)), None,
        "Compared: the panel at %s, with the files on disk." % commit)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Fail a write that changes or removes what the panel "
                    "already held.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", metavar="PATH",
                   help="record every file's bars and labels in PATH")
    g.add_argument("--compare", metavar="PATH",
                   help="compare the panel on disk against a PATH snapshot")
    g.add_argument("--against", metavar="COMMIT",
                   help="compare the panel on disk against a git commit")
    ap.add_argument("--rewrite", nargs=2, metavar=("START", "END"),
                    help="with --compare: the weekly files dated START..END "
                         "were rewritten whole, on purpose (a full-universe "
                         "--force backfill). Their bars, labels and stamps "
                         "may change and are counted; nothing outside the "
                         "range may, and nothing may vanish")
    ap.add_argument("--weekly-dir", default=WEEKLY_DIR,
                    help="weekly file directory (default %s)" % WEEKLY_DIR)
    ap.add_argument("--daily-dir", default=None,
                    help="daily file directory (default: `daily` beside the "
                         "weekly directory, guarded when it exists)")
    args = ap.parse_args(argv)

    rewrite = None
    if args.rewrite:
        if not args.compare:
            ap.error("--rewrite goes with --compare. A snapshot declares "
                     "nothing, and a commit that changes what the panel held "
                     "fails --against whatever it says about itself.")
        for day in args.rewrite:
            try:
                if not _ISO_DAY.match(day):
                    raise ValueError(day)
                dt.date.fromisoformat(day)
            except ValueError:
                ap.error("--rewrite takes two dates, YYYY-MM-DD; got %r" % day)
        if args.rewrite[0] > args.rewrite[1]:
            ap.error("--rewrite %s %s: the range ends before it starts"
                     % tuple(args.rewrite))
        rewrite = tuple(args.rewrite)

    dirs = panel_dirs(args.weekly_dir, args.daily_dir)
    if args.snapshot:
        return cmd_snapshot(dirs, args.snapshot)
    if args.compare:
        return cmd_compare(dirs, args.compare, rewrite)
    return cmd_against(dirs, args.against)


if __name__ == "__main__":
    sys.exit(main())
