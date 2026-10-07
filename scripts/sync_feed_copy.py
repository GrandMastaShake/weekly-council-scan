#!/usr/bin/env python3
"""sync_feed_copy.py -- level a working copy of the feed with the repository.

The weekly job, and the Monday Council's fallback build, derive
market_state.json from a copy of data/ kept on the runner, and push it.
Everyone else derives it again from the repository's files: CI, the daily
job, the Monday gate. So a difference between the copy and the repository
is a FAIL somebody meets later. Until 2026-10-06 the copy was brought up to
date by hand, when someone remembered. On that day it lacked both history
files and a correction, and every one of its 114 weekly files was an older
version than the repository's.

This brings the copy up to the repository before anything is written.

    data/weekly/*.json                  corrections included
    data/us2y_treasury.json
    data/commodity_settlements.json
    data/market_state.json

WHAT A WEEKLY FILE HELD, IT STILL HOLDS. The panel's own rule
(scripts/panel_guard.py, DATA_FEED.md sec.1), applied to the copy. The
repository's version of a weekly file replaces the copy's only where it
keeps everything the copy holds: every entry in series, rates, vol,
commodities and fx, with the same bar and the same label, and the same
source, fetched_at and session_note. That is what a copy that is merely
behind looks like, because a committed week only ever gains entries. A
repository file that CHANGES or LACKS something the copy holds is not that,
and it is not for this script to say which side is right:

  * the copy can be the true one. A week is pushed by an agent, and the
    file has been mistyped on its way twice: 2026-08-14.json reached the
    repository with three volumes wrong (ALL, LOW, PGR; 87dba89) and
    2026-08-28.json with VTR's as 1916834 where the runner had written
    1916830 (0bcb75f). Each was put right against the runner's copy;
  * the repository can have been rewritten on purpose, by a declared
    full-universe backfill;
  * the repository can simply be wrong: on 2026-08-26 it held 107 weeks cut
    from 287 series to 44.

So such a file is a REFUSAL for the whole run, nothing written, with the
entries named. Two things lift it, each said out loud, and each as far as
panel_guard lifts it and no further. A correction may change an instrument
it newly records in `restated` (sec.1b). And a rewrite is declared here as
it is there: --rewritten START END, by a person, for the weeks a declared
backfill rewrote. Inside it the repository's version may change a bar, a
label or a stamp the copy holds. It may not LACK an entry the copy holds:
an honest rewrite removes nothing, and the declaration would otherwise be
the one way to wave a repository cut to 44 series onto the runner.

A copy with a byte-order mark, or in UTF-16, is the same document as a
Windows editor saves it. Where the repository has that week the copy is
read that way and held to the rule, so that what it holds is not lost for
its encoding. Nowhere else: a week only the copy holds has to read as the
writer and every reader read it, or it is not a weekly file, and one that
reads as its week only the way an editor saved it is refused as that: the
only copy of a week that was never pushed, not to be moved or deleted. A
copy that does not read as a document at all (zero bytes, the first bytes
of a write that died) holds nothing that can be compared: the repository's
takes its place, and the file is kept like any other that is replaced.

WHAT IS TAKEN FROM THE REPOSITORY IS THE FILE IT IS NAMED FOR. A weekly
file is added, or put in the copy's place, only where it reads, strictly,
as that week: its as_of is its name's date and it has series. The
repository's own gate fails one that does not. With a byte-order mark the
readers on the runner would stop on it. With another week's as_of they
would not: they would read it, as the week it is filed under. REFUSED
either way, and the repository's to put right: nothing a copy holds mends
it, and no declaration lifts it.

The other three files are never written on the runner except
market_state.json, which the job derives again in any case. The
repository's version replaces the copy's.

Whatever is replaced is kept, under data/replaced/<UTC stamp>/.

WHAT THE COPY HOLDS AND THE REPOSITORY DOES NOT.

  * A week, <Friday>.json, that reads as that week and has never been in the
    repository: written here and never pushed. Left alone and named; pushing
    it is the job's (its step 7).
  * A week the repository held and has removed: withdrawn there, on
    purpose. Pushed again it would come back. REFUSED; the line says to move
    it out by hand, after which the job writes the week whole. The week the
    job then writes is not that copy: its fetched_at is later than the
    removal, and it is left alone and named like any week not yet pushed.
  * A correction, <date>.corrected.json. The job never writes one, so it is
    withdrawn in the repository or was made here by hand, and readers
    prefer a correction: a state derived with it would not be the
    repository's. Moved aside, to data/replaced/<UTC stamp>/, and named.
    That holds beside a week that is itself not pushed yet: the week goes
    up as written, and the correction is the owner's to commit.
  * Anything else named *.json in data/weekly: not a weekly file. REFUSED,
    with what it is; nothing here deletes a file.

Nothing else is written. data/universe.json is the job's to rebuild,
data/daily is not kept on the runner, and scan_pipeline/ is synced by hand:
a difference there is REPORTED, so the run that meets one says so, and
never written. scan_pipeline/state/ is the runner's live state and is not
looked at.

All or nothing as far as the network goes. The listing, every file and the
history of a path are read at one commit, and each download is checked
against the repository's own hash before anything is decided, let alone
written.

    python sync_feed_copy.py --runner <pipeline_root>            # dry run
    python sync_feed_copy.py --runner <pipeline_root> --apply

The last line says how it ended:

    LEVEL with main <sha>: ...        exit 0. Applied; the copy is level.
    DRY RUN against main <sha> ...    exit 0 with nothing to do, exit 1 when
                                      an --apply would change the copy.
    NOT LEVEL: ...                    exit 2. REFUSED above it: nothing was
                                      written, and the reason is the
                                      owner's to settle. INTERRUPTED above
                                      it: the repository or the copy could
                                      not be read and nothing was written,
                                      or a disk error stopped the writing
                                      part-way. Run it again.

The job does not write a week on top of a copy that is not level.

A dry run is not a check of a push. Run after one, it says "kept" of a
week that did not land and "would replace" of one that went up in other
bytes, and exits 0 and 1 for them; it is read by its counts.

Standard library only, and one file: the job fetches it fresh from the
repository and runs it where nothing else is installed. It reads the public
repository without credentials, and asks the `gh` CLI only when that is
refused.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "GrandMastaShake/weekly-council-scan"
REF = "main"

API = "https://api.github.com/repos/%s/%s"
RAW = "https://raw.githubusercontent.com/%s/%s/%s"
HEADERS = {"User-Agent": "weekly-council-scan/sync_feed_copy",
           "Accept": "application/vnd.github+json"}
PAUSES_S = (2, 4)           # between attempts at one request

WEEKLY = "data/weekly/"
SINGLES = ("data/us2y_treasury.json", "data/commodity_settlements.json",
           "data/market_state.json")
REPLACED = ("data", "replaced")
CORRECTED = ".corrected.json"
WEEK_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})(\.corrected)?\.json$")

# scripts/panel_guard.py's, repeated because this file runs alone. A test
# holds the two readings of a pair of files to one answer.
BLOCKS = ("series", "rates", "vol", "commodities", "fx")
STAMPS = ("source", "fetched_at", "session_note")
GONE = "gone"               # the one kind a declared rewrite does not lift

# Reported, never written (module docstring).
CODE = "scan_pipeline/"
CODE_SUFFIXES = (".py", ".csv")
CODE_NOT_LOOKED_AT = ("scan_pipeline/state/",)

SHOW = 12                   # paths spelled out per kind; the totals cover the rest
SHOW_ENTRIES = 4            # entries named for one file that was refused

# A path the repository's history holds with a date that cannot be read is
# taken for removed later than anything the copy holds.
UNDATED = dt.datetime.max.replace(tzinfo=dt.timezone.utc)


class Refused(RuntimeError):
    """The copy could not be levelled, and why is the owner's to settle.
    Nothing was written."""


class NotNow(RuntimeError):
    """The repository or the copy could not be read this time. Nothing was
    written, and asking again may be all it takes."""


class Interrupted(RuntimeError):
    """Writing stopped part-way."""


def blob_sha(data: bytes) -> str:
    """The hash git gives these bytes as a blob, which is what the
    repository's listing carries for every file."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def in_feed(path: str) -> bool:
    """True for a file this script levels."""
    if path in SINGLES:
        return True
    rest = path[len(WEEKLY):]
    return path.startswith(WEEKLY) and path.endswith(".json") \
        and "/" not in rest


def in_code(path: str) -> bool:
    """True for a file whose difference is reported."""
    return path.startswith(CODE) and path.endswith(CODE_SUFFIXES) \
        and not path.startswith(CODE_NOT_LOOKED_AT)


def _utc(text) -> dt.datetime:
    """A `fetched_at` or a commit date: UTC to the second, with its Z."""
    if not isinstance(text, str):
        raise ValueError("not a timestamp: %r" % (text,))
    return dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.timezone.utc)


# ----------------------------------------------------------------- network

def _http(url: str) -> bytes:
    problem = None
    for pause in PAUSES_S + (0,):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as exc:        # refused, rate-limited, offline
            problem = "%s: %s" % (type(exc).__name__, str(exc)[:160])
            time.sleep(pause)
    raise OSError(problem)


def _gh(*args: str) -> bytes:
    """The same request through the `gh` CLI, where it is installed and
    signed in. Authenticated tooling the job already uses; no credential is
    read here."""
    done = subprocess.run(("gh", "api") + args, capture_output=True,
                          timeout=120)
    if done.returncode != 0:
        raise OSError("gh api: " + done.stderr.decode(
            "utf-8", "replace").strip()[:160])
    return done.stdout


def _either(what: str, routes):
    """What the first route that answers returns. NotNow, naming each, when
    none does."""
    problems = []
    for route in routes:
        try:
            return route()
        except (OSError, subprocess.SubprocessError) as exc:
            problems.append(str(exc) or type(exc).__name__)
    raise NotNow("%s (%s)" % (what, "; then ".join(problems)))


def fetch_api(repo: str, path: str):
    """One GitHub API document. Raises NotNow when neither route answers."""
    def document(route):
        def ask():
            data = route()
            try:
                return json.loads(data)
            except ValueError as exc:
                raise OSError("its answer was not JSON (%s)" % exc)
        return ask

    return _either("could not ask the repository for %s" % path, [
        document(lambda: _http(API % (repo, path))),
        document(lambda: _gh("repos/%s/%s" % (repo, path)))])


def fetch_raw(repo: str, commit: str, path: str) -> bytes:
    """One file's bytes as committed at `commit`."""
    quoted = urllib.parse.quote(path)
    return _either("could not download %s" % path, [
        lambda: _http(RAW % (repo, commit, quoted)),
        lambda: _gh("repos/%s/contents/%s?ref=%s" % (repo, quoted, commit),
                    "-H", "Accept: application/vnd.github.raw")])


# ----------------------------------------------------------------- listing

def listing(repo: str, ref: str, api=fetch_api) -> tuple:
    """(commit, {path: blob hash}) for every file of the repository at ref.

    One commit throughout: the files are downloaded at the commit the
    listing was read from, so a push in between cannot mix two panels."""
    try:
        branch = api(repo, "branches/" + ref)
        commit = branch["commit"]["sha"]
        tree_sha = branch["commit"]["commit"]["tree"]["sha"]
        tree = api(repo, "git/trees/%s?recursive=1" % tree_sha)
        if tree.get("truncated"):
            raise Refused("the repository's listing came back truncated; a "
                          "partial listing would read as files it lacks")
        files = {entry["path"]: entry["sha"] for entry in tree["tree"]
                 if entry.get("type") == "blob"}
    except (KeyError, TypeError, AttributeError) as exc:
        raise Refused("the repository's listing could not be read (%s: %s)"
                      % (type(exc).__name__, exc))
    if not any(p.startswith(WEEKLY) and in_feed(p) for p in files):
        raise Refused("the repository's listing holds no weekly file; that "
                      "is not the panel, and nothing is levelled against it")
    return commit, files


def last_change(repo: str, commit: str, path: str, api=fetch_api):
    """When the repository last changed this path, as of `commit`: the date
    of the newest commit in that commit's history that touched it, or None
    where none did, which is a path it has never held. Asked only of a week
    the copy holds and the listing does not, so the change is its removal.

    Asked of the commit that was listed and not of the branch. Asked of the
    branch, a week pushed a moment ago had a history while the listing,
    read a second earlier or served from a cache, did not have the file:
    "the repository held it once and has removed it", of a week that had
    just arrived."""
    commits = api(repo, "commits?sha=%s&path=%s&per_page=1"
                  % (urllib.parse.quote(commit), urllib.parse.quote(path)))
    if not isinstance(commits, list):
        raise Refused("the repository's history of %s could not be read"
                      % path)
    if not commits:
        return None
    try:
        return _utc(commits[0]["commit"]["committer"]["date"])
    except (KeyError, TypeError, ValueError):
        return UNDATED


# ------------------------------------------------- what a file held (guard)

def same(a, b) -> bool:
    """Equal as JSON values: 100 and 100.0 are one number, true is not 1,
    and a NaN is the NaN it was. scripts/panel_guard.py's."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b or (a != a and b != b)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def _entries(doc: dict, block: str) -> dict:
    held = doc.get(block)
    return held if isinstance(held, dict) else {}


def _label(doc: dict, block: str, ticker: str):
    prov = doc.get("provenance")
    labels = prov.get(block) if isinstance(prov, dict) else None
    return labels.get(ticker) if isinstance(labels, dict) else None


def _restated(doc: dict) -> set:
    record = doc.get("restated")
    return {(item["block"], item["ticker"])
            for item in (record if isinstance(record, list) else [])
            if isinstance(item, dict)
            and isinstance(item.get("block"), str)
            and isinstance(item.get("ticker"), str)}


def not_kept(name: str, was: dict, now: dict) -> list:
    """What `now`, the repository's version of a weekly file, does not hold
    as `was`, the copy's, holds it: (kind, sentence) pairs, the kinds being
    panel_guard's "gone", "changed", "relabelled" and "stamps". Empty when
    the copy is merely behind.

    The rule of scripts/panel_guard.py's diff_file, read for one question:
    may this file be replaced without losing or changing an observation?"""
    fresh = _restated(now) - _restated(was) if name.endswith(CORRECTED) \
        else set()
    out = []
    for block in BLOCKS:
        before, after = _entries(was, block), _entries(now, block)
        for ticker in sorted(before, key=str):
            where = "%s.%s" % (block, ticker)
            if ticker not in after:
                out.append((GONE, where + " is not in the repository's"))
                continue
            bar = not same(before[ticker], after[ticker])
            label = not same(_label(was, block, ticker),
                             _label(now, block, ticker))
            if (bar or label) and block != "series" \
                    and (block, ticker) in fresh:
                continue        # a correction's recorded restatement
            if bar:
                out.append(("changed",
                            "%s is %s here and %s in the repository's"
                            % (where, json.dumps(before[ticker],
                                                 sort_keys=True),
                               json.dumps(after[ticker], sort_keys=True))))
            if label:
                out.append(("relabelled", where + " carries another label "
                                                  "in the repository's"))
    for field in STAMPS:
        if not same(was.get(field), now.get(field)):
            out.append(("stamps",
                        "`%s` is %s here and %s in the repository's"
                        % (field, json.dumps(was.get(field)),
                           json.dumps(now.get(field)))))
    return out


def _parsed(data: bytes, lenient: bool = False):
    """A weekly file's document, or None when it is not one that reads.

    Strictly, it reads as UTF-8 with no byte-order mark, which is how the
    writer writes it and every reader reads it. `lenient` also takes a
    byte-order mark and UTF-16, how a Windows editor saves the same
    document. That is for one question only: what does a copy hold that
    must not be lost when the repository's file takes its place? Asked
    whether a file IS a weekly file, the lenient answer called one the
    writer refuses and the chain dies on "a week written here and never
    pushed", and put a repository file with a byte-order mark over a good
    copy."""
    for encoding in ("utf-8", "utf-8-sig", "utf-16") if lenient \
            else ("utf-8",):
        try:
            doc = json.loads(data.decode(encoding))
        except ValueError:              # UnicodeDecodeError is one
            continue
        return doc if isinstance(doc, dict) else None
    return None


def not_a_week(name: str, data: bytes, lenient: bool = False):
    """Why a file at a week's name is not that week's file, or None.
    Strictly, unless asked what an editor's save of it would be."""
    match = WEEK_NAME.match(name)
    if not match:
        return "its name is not <YYYY-MM-DD>.json"
    try:
        day = dt.date.fromisoformat(match.group(1))
    except ValueError:
        return "its name is not a date"
    if day.weekday() != 4:
        return "its date is not a Friday"
    doc = _parsed(data, lenient)
    if doc is None:
        return "it does not read as JSON"
    if doc.get("as_of") != match.group(1):
        return "its as_of is %s" % json.dumps(doc.get("as_of"))
    if not isinstance(doc.get("series"), dict) or not doc["series"]:
        return "it has no series"
    return None


def not_that_file(name: str, data: bytes):
    """Why a file the repository holds at a weekly name is not the file it
    is named for, or None. Read strictly."""
    if WEEK_NAME.match(name):
        return not_a_week(name, data)
    dated = DATED.match(name)
    if dated is None:
        return ("its name is not <YYYY-MM-DD>.json or "
                "<YYYY-MM-DD>.corrected.json")
    doc = _parsed(data)
    if doc is None:
        return "it does not read as JSON"
    if doc.get("as_of") != dated.group(1):
        return "its as_of is %s" % json.dumps(doc.get("as_of"))
    if not isinstance(doc.get("series"), dict) or not doc["series"]:
        return "it has no series"
    return None


def in_rewrite(name: str, rewrite) -> bool:
    """Is this weekly file, or correction, one a declared rewrite covers?"""
    dated = DATED.match(name)
    return bool(rewrite) and dated is not None \
        and rewrite[0] <= dated.group(1) <= rewrite[1]


def written_after(data: bytes, moment: dt.datetime) -> bool:
    """Was this week fetched after `moment`? False where it does not say."""
    doc = _parsed(data) or {}
    try:
        return _utc(doc.get("fetched_at")) > moment
    except ValueError:
        return False


# -------------------------------------------------------------------- plan

def plan(files: dict, runner: Path, fetch, changed_last, rewrite=None) -> dict:
    """What levelling would do, and the bytes it would write. Reads the copy
    and the repository; writes nothing. Raises Refused where the two
    disagree about something neither may lose."""
    out = {"same": [], "add": [], "replace": [], "kept": [], "aside": [],
           "rewritten": [], "code": [], "bytes": {}}
    refusals, unfit = [], []

    def download(path):
        """The repository's bytes for a path, or None where they are not
        the weekly file the path names (said, as a refusal of its own)."""
        data = fetch(path)
        if blob_sha(data) != files[path]:
            raise NotNow(
                "what was downloaded for %s is not the file the repository "
                "lists (hash %s, listed %s)"
                % (path, blob_sha(data)[:12], files[path][:12]))
        if path.startswith(WEEKLY):
            why = not_that_file(path[len(WEEKLY):], data)
            if why is not None:
                unfit.append("%s (%s)" % (path, why))
                return None
        out["bytes"][path] = data
        return data

    for path in sorted(p for p in files if in_feed(p)):
        local = runner / path
        if local.is_dir():
            refusals.append("%s is a directory here, where the repository "
                            "has a file" % path)
            continue
        if not local.is_file():
            if download(path) is not None:
                out["add"].append(path)
            continue
        mine = local.read_bytes()
        if blob_sha(mine) == files[path]:
            out["same"].append(path)
            continue
        theirs = download(path)
        if theirs is None:
            continue
        if not path.startswith(WEEKLY):
            out["replace"].append(path)     # never written on the runner
            continue
        name = path[len(WEEKLY):]
        was, now = _parsed(mine, lenient=True), _parsed(theirs)
        if was is None:
            out["replace"].append(path)     # holds nothing that reads
            continue
        lost = not_kept(name, was, now or {})
        declared = in_rewrite(name, rewrite)
        if declared:
            # As panel_guard takes --rewrite: it may change, it may not
            # remove.
            if lost and all(kind != GONE for kind, _ in lost):
                out["rewritten"].append(path)
            lost = [item for item in lost if item[0] == GONE]
        if not lost:
            out["replace"].append(path)
            continue
        shown = "; ".join(text for _, text in lost[:SHOW_ENTRIES])
        if len(lost) > SHOW_ENTRIES:
            shown += "; and %d more" % (len(lost) - SHOW_ENTRIES)
        refusals.append(
            "%s is not an older copy of the repository's file. The "
            "repository's %s what this copy holds: %s"
            % (path, "lacks, inside the rewrite that was declared, which "
                     "may change an entry and may not remove one,"
               if declared else "changes or lacks", shown))

    for local in sorted((runner / "data" / "weekly").glob("*.json")):
        path = WEEKLY + local.name
        if path in files:
            continue
        dated = DATED.match(local.name)
        if dated is not None and dated.group(2):
            out["aside"].append(path)
            continue
        data = local.read_bytes()
        why = not_a_week(local.name, data)
        if why is not None and not_a_week(local.name, data,
                                          lenient=True) is None:
            # Called "not a weekly file ... move it out by hand", it was the
            # only copy of an unpushed week, and moved out it is replaced by
            # a later fetch.
            refusals.append(
                "%s is in the copy and not in the repository, and it reads "
                "as that week only the way an editor saves a file, with a "
                "byte-order mark or in UTF-16. No reader here reads it so. "
                "It is the only copy of a week that was never pushed: it is "
                "not pushed as it is, and it is not to be moved or deleted. "
                "The owner saves it again as it was written (UTF-8, no "
                "mark, its values untouched) or has the week written again"
                % path)
            continue
        if why is not None:
            refusals.append(
                "%s is in the copy and not in the repository, and it is not "
                "a weekly file (%s). It is not pushed. Nothing here deletes "
                "a file: move that one file out of data/weekly by hand and "
                "run this again" % (path, why))
            continue
        removed = changed_last(path)
        if removed is None or written_after(data, removed):
            out["kept"].append(path)
        else:
            refusals.append(
                "%s is in the copy, and the repository held it once and has "
                "removed it. It was withdrawn there, so it is not pushed "
                "again. If that removal was meant, move the file out of "
                "data/weekly by hand and run this again; the job then "
                "writes the week whole" % path)

    said = []
    if unfit:
        # Apart from the disagreements below: which side is right is not in
        # question here, a copy may not hold the file at all, and neither
        # the copy nor a declaration mends it.
        said.append(
            "%d file(s) the repository holds are not the weekly file they "
            "are named for, and are not taken.\n  - %s\n"
            "The repository's own gate fails each. A reader here would stop "
            "on a file that does not read, and would read one with another "
            "week's as_of as the week it is filed under. It is put right in "
            "the repository: nothing on this copy is to change for it, and "
            "--rewritten does not lift it"
            % (len(unfit), "\n  - ".join(_some(unfit))))
    if refusals:
        shown = refusals[:SHOW]
        if len(refusals) > SHOW:
            shown.append("... and %d more file(s), which a run without the "
                         "ones above would name" % (len(refusals) - SHOW))
        said.append(
            "the repository and this copy disagree about %d file(s), and "
            "which is right is not this script's to say.\n  - %s\n"
            "Do not edit, delete or push any of them. Tell the owner what "
            "is printed here: where the repository is the one that is "
            "wrong it is put right there, from this copy; where a declared "
            "backfill rewrote those weeks, a person runs this with "
            "--rewritten START END, which lets the repository's version "
            "change what the copy holds and never remove it"
            % (len(refusals), "\n  - ".join(shown)))
    if said:
        raise Refused(".\nAlso, ".join(said))

    for path in sorted(p for p in files if in_code(p)):
        local = runner / path
        if not local.is_file():
            out["code"].append((path, "is not on the runner"))
            continue
        # Line endings aside, for code: a checkout with CRLF runs the same.
        # (A feed file is held to the committed bytes, above.)
        text = local.read_bytes().replace(b"\r\n", b"\n")
        if blob_sha(text) != files[path]:
            out["code"].append((path, "differs from the repository's"))
    return out


def level(todo: dict, files: dict, runner: Path, stamp: str) -> None:
    """Write the plan. Everything it writes was downloaded and checked
    while the plan was made."""
    keep = runner.joinpath(*REPLACED)
    if keep.exists() and not keep.is_dir():
        raise Refused("%s is not a directory, and what a replaced file "
                      "held has to be kept there" % "/".join(REPLACED))
    wanted = todo["add"] + todo["replace"]
    done, moved, part = 0, 0, None
    try:
        for path in todo["replace"] + todo["aside"]:
            # Keep what the copy held, and read it back before anything is
            # taken away. Under data/, beside the panel and out of every
            # reader's way: nothing globs data/replaced.
            held = (runner / path).read_bytes()
            kept = keep / stamp / Path(path).relative_to("data")
            kept.parent.mkdir(parents=True, exist_ok=True)
            kept.write_bytes(held)
            if kept.read_bytes() != held:
                raise OSError("the kept copy of %s did not read back as "
                              "written" % path)
        for path in todo["aside"]:
            os.remove(runner / path)
            moved += 1
        for path in wanted:
            target = runner / path
            target.parent.mkdir(parents=True, exist_ok=True)
            part = target.with_name(target.name + ".part")
            part.write_bytes(todo["bytes"][path])
            os.replace(part, target)
            part = None
            done += 1
            if blob_sha(target.read_bytes()) != files[path]:
                raise OSError("%s did not read back as written" % path)
    except OSError as exc:
        if part is not None:
            try:
                os.remove(part)
            except OSError:
                pass
        raise Interrupted(
            "%d of %d file(s) written%s, then %s: %s. %s"
            % (done, len(wanted),
               " and %d moved aside" % moved if moved else "",
               type(exc).__name__, exc,
               "The copy is part old and part new" if done
               else "Nothing in the copy was replaced"))


# ------------------------------------------------------------------ report

def _some(paths: list) -> list:
    shown = list(paths[:SHOW])
    if len(paths) > SHOW:
        shown.append("... and %d more" % (len(paths) - SHOW))
    return shown


def report(todo: dict, commit: str, ref: str, stamp: str,
           applied: bool) -> list:
    lines = []
    kept_in = "/".join(REPLACED) + "/" + stamp + "/"
    for path in _some(todo["replace"]):
        lines.append("  replace  %s%s" % (
            path, "  (declared rewritten)" if path in todo["rewritten"]
            else ""))
    for path in _some(todo["aside"]):
        lines.append("  aside    %s  (a correction the repository does not "
                     "hold: withdrawn there, or made here by hand. The job "
                     "writes none, and readers would prefer it)" % path)
    if todo["replace"] or todo["aside"]:
        lines.append("           what each held is %s in %s"
                     % ("kept" if applied else "to be kept", kept_in))
    for path in _some(todo["add"]):
        lines.append("  add      %s" % path)
    for path in _some(todo["kept"]):
        lines.append("  kept     %s  (a week written here and never pushed. "
                     "Left as it is; pushing it is the job's)" % path)
    for path, why in todo["code"][:SHOW]:
        lines.append("  code     %s %s. Not written: scan_pipeline/ is "
                     "synced by hand" % (path, why))
    if len(todo["code"]) > SHOW:
        lines.append("  code     ... and %d more"
                     % (len(todo["code"]) - SHOW))
    tail = ("%d already the repository's, %d week(s) kept that were never "
            "pushed; scan_pipeline: %s"
            % (len(todo["same"]), len(todo["kept"]),
               "level" if not todo["code"]
               else "%d file(s) behind, synced by hand" % len(todo["code"])))
    counts = "%d replaced, %d added, %d moved aside" if applied \
        else "would replace %d, add %d and move %d aside"
    counts %= (len(todo["replace"]), len(todo["add"]), len(todo["aside"]))
    at = "%s %s" % (ref, commit[:7])
    if applied:
        lines.append("LEVEL with %s: %s, %s" % (at, counts, tail))
    else:
        lines.append("DRY RUN against %s, nothing written: %s; %s"
                     % (at, counts, tail))
    return lines


def _day(text: str) -> str:
    try:
        return dt.date.fromisoformat(text).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError("not a date: %r" % text)


def main(argv=None, api=fetch_api, raw=fetch_raw, now=None) -> int:
    # A console that is not UTF-8 must not turn a refusal into a traceback:
    # a script that dies printing why it refused has refused nothing.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    ap = argparse.ArgumentParser(
        description="Level a working copy of the feed with the repository.")
    ap.add_argument("--runner", required=True,
                    help="the pipeline root: the directory that holds data/ "
                         "and scan_pipeline/")
    ap.add_argument("--apply", action="store_true",
                    help="write; without it this is a dry run")
    ap.add_argument("--rewritten", nargs=2, type=_day,
                    metavar=("START", "END"),
                    help="the weekly files dated START..END, and their "
                         "corrections, were rewritten whole in the "
                         "repository by a declared backfill: take the "
                         "repository's although they change what the copy "
                         "holds. An entry the copy holds and the "
                         "repository's lacks is refused all the same. For a "
                         "person, never for the job")
    ap.add_argument("--repo", default=REPO, help="owner/name (default: %s)"
                    % REPO)
    ap.add_argument("--ref", default=REF, help="branch (default: %s)" % REF)
    args = ap.parse_args(argv)

    runner = Path(args.runner)
    stamp = (now or dt.datetime.now(dt.timezone.utc)).strftime(
        "%Y%m%dT%H%M%SZ")
    try:
        try:
            weekly = runner / "data" / "weekly"
            if not weekly.is_dir() or not any(weekly.glob("*.json")):
                raise Refused(
                    "%s holds no weekly file, so it is not the pipeline "
                    "root. This levels a copy that exists; it does not "
                    "start one" % weekly)
            commit, files = listing(args.repo, args.ref, api)
            print("sync_feed_copy: %s %s at %s -> %s"
                  % (args.repo, args.ref, commit[:7], runner))
            todo = plan(files, runner,
                        lambda path: raw(args.repo, commit, path),
                        lambda path: last_change(args.repo, commit, path,
                                                 api),
                        args.rewritten)
            if args.apply:
                level(todo, files, runner, stamp)
        except OSError as exc:      # the copy itself could not be read
            raise NotNow("the copy could not be read (%s: %s)"
                         % (type(exc).__name__, exc))
    except Refused as exc:
        print("REFUSED, nothing written: %s." % exc)
        print("NOT LEVEL: the copy is as it was. Do not write a week on top "
              "of it.")
        return 2
    except NotNow as exc:
        print("INTERRUPTED before anything was written: %s." % exc)
        print("NOT LEVEL: the repository or the copy could not be read this "
              "time, and the copy is as it was. Run this once more. If it "
              "ends this way twice, stop.")
        return 2
    except Interrupted as exc:
        print("INTERRUPTED: %s." % exc)
        print("NOT LEVEL: a disk error stopped the writing. Run this once "
              "more: it is safe to repeat, and what each replaced file held "
              "is in %s/%s/. If it ends this way twice, stop."
              % ("/".join(REPLACED), stamp))
        return 2
    for line in report(todo, commit, args.ref, stamp, args.apply):
        print(line)
    pending = todo["replace"] or todo["add"] or todo["aside"]
    return 1 if (pending and not args.apply) else 0


if __name__ == "__main__":
    sys.exit(main())
