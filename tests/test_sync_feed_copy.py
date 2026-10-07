"""Levelling the runner's copy of the feed with the repository.

The weekly job derives market_state.json from a copy of data/ on the runner
and pushes it; CI, the daily job and the Monday gate derive it again from
the repository. On 2026-10-06 that copy lacked both history files and a
correction, and all 114 of its weekly files were older versions. The job's
first step is now scripts/sync_feed_copy.py, fetched fresh.

What is pinned here is what the job's prompt relies on. The repository's
version of a weekly file replaces the copy's only where it keeps what the
copy holds; anything else is a refusal with nothing written, because the
copy has been the true one before (0bcb75f, 87dba89). A week written on the
runner and never pushed is left alone, one the repository withdrew is not
pushed back, and no half-read repository is taken for a whole one. And the
last line of each run is what the prompt reads: every ending is run here,
not looked for in the source.

No network: the two fetches are injected, and the routes under them are
replaced where a test is about them.
"""
from __future__ import annotations

import ast
import copy
import datetime as dt
import json
import os
import re
import subprocess
import sys

import pytest

from conftest import ROOT

import panel_guard as pg  # noqa: E402
import sync_feed_copy as sfc  # noqa: E402

COMMIT, TREE = "c" * 40, "7" * 40
REMOVED = "2026-10-12T09:00:00Z"        # when the repository withdrew a path
NOW = dt.datetime(2026, 10, 10, 13, 24, 55, tzinfo=dt.timezone.utc)
STAMP = "20261010T132455Z"
ANCHOR = {"source": "yahoo-backfill", "fetched_at": "2026-10-06T01:48:08Z"}


def doc(as_of, **series):
    """A weekly document. SPY and AAPL unless told otherwise."""
    names = series or {"SPY": 100.0, "AAPL": 50.0}
    return {"as_of": as_of, "source": "yahoo",
            "fetched_at": as_of + "T21:00:00Z", "session": "close",
            "series": {t: {"close": c, "volume": 1000}
                       for t, c in names.items()},
            "rates": {"US10Y": {"close": 4.7, "volume": None}},
            "vol": {}, "commodities": {}, "fx": {}, "missing": []}


def blob(document):
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode(
        "ascii")


def week(as_of, **series):
    return blob(doc(as_of, **series))


REPO_FILES = {
    "data/weekly/2026-09-25.json": week("2026-09-25"),
    "data/weekly/2026-10-02.json": week("2026-10-02"),
    "data/weekly/2026-08-28.corrected.json": week("2026-08-28"),
    "data/us2y_treasury.json": b'{"weeks": {}}\n',
    "data/commodity_settlements.json": b'{"WTI": {}}\n',
    "data/market_state.json": b'{"as_of": "2026-10-02"}\n',
    "data/universe.json": b'{"tickers": ["SPY"]}\n',
    "data/daily/2026-10-05.json": week("2026-10-05"),
    "scan_pipeline/snapshot.py": b"VERSION = 2\n",
    "scan_pipeline/config/council_watchlist.csv": b"ticker\nSPY\n",
    "scan_pipeline/state/personas.json": b'{"repo": true}\n',
    "scan_pipeline/README.md": b"# readme\n",
    "README.md": b"# top\n",
}


class Repo:
    """The repository as the script sees it: one listing, files by path,
    and the paths its history has ever held."""

    def __init__(self, files=None, truncated=False, once_held=(),
                 removed=REMOVED):
        self.files = dict(REPO_FILES if files is None else files)
        self.truncated = truncated
        self.once_held = set(once_held)
        self.removed = removed
        self.downloads, self.asked = [], []
        self.down = False

    def api(self, repo, path):
        self.asked.append(path)
        if self.down:
            raise sfc.NotNow("could not ask the repository for " + path)
        if path == "branches/main":
            return {"commit": {"sha": COMMIT,
                               "commit": {"tree": {"sha": TREE}}}}
        if path.startswith("commits?"):
            assert "sha=" + COMMIT in path and "per_page=1" in path, (
                "the history is asked of the commit that was listed: " + path)
            held = [p for p in self.once_held | set(self.files)
                    if "path=" + p.replace("/", "%2F") in path
                    or "path=" + p in path]
            return [{"sha": "d" * 40, "commit": {
                "committer": {"date": self.removed}}}] if held else []
        assert path == "git/trees/%s?recursive=1" % TREE, path
        tree = [{"path": p, "type": "blob", "sha": sfc.blob_sha(d)}
                for p, d in self.files.items()]
        tree.append({"path": "data/weekly", "type": "tree", "sha": "0" * 40})
        return {"truncated": self.truncated, "tree": tree}

    def raw(self, repo, commit, path):
        assert commit == COMMIT, "a file is read at the commit that was listed"
        self.downloads.append(path)
        return self.files[path]


def runner_with(tmp_path, files):
    root = tmp_path / "runner"
    for path, data in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root


def run(root, repo, *flags):
    return sfc.main(["--runner", str(root)] + list(flags),
                    api=repo.api, raw=repo.raw, now=NOW)


def tree_of(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


def feed_of(files):
    return {p: d for p, d in files.items() if sfc.in_feed(p)}


def last(capsys):
    return capsys.readouterr().out.strip().splitlines()[-1]


def refused(root, repo, capsys, *flags):
    before = tree_of(root)
    assert run(root, repo, *flags) == 2
    assert tree_of(root) == before, "nothing is written by a refusal"
    out = capsys.readouterr().out
    assert "REFUSED, nothing written" in out and "INTERRUPTED" not in out
    assert out.strip().splitlines()[-1].startswith("NOT LEVEL")
    return out


def not_now(root, repo, capsys, *flags):
    """It could not be asked or read this time: nothing written, and the
    line says to run it once more."""
    before = tree_of(root)
    assert run(root, repo, *flags) == 2
    assert tree_of(root) == before, "nothing is written"
    out = capsys.readouterr().out
    assert "INTERRUPTED before anything was written" in out
    assert "REFUSED" not in out
    tail = out.strip().splitlines()[-1]
    assert tail.startswith("NOT LEVEL") and "Run this once more" in tail
    return out


def fridays(count):
    """That many Fridays, as ISO dates."""
    first = dt.date(2025, 1, 3)
    return [(first + dt.timedelta(weeks=n)).isoformat() for n in range(count)]


def stale(tmp_path):
    """A copy that is merely behind: one week, older than the repository's
    (the repository's has since gained a name)."""
    old = doc("2026-10-02")
    del old["series"]["AAPL"]
    return runner_with(tmp_path, {"data/weekly/2026-10-02.json": blob(old)})


# -- the hash ------------------------------------------------------------------

def test_the_hash_is_gits_own():
    """`git hash-object` of the six bytes "hello\\n"."""
    assert sfc.blob_sha(b"hello\n") == \
        "ce013625030ba8dba906f756967f9e9ca394464a"


def test_a_committed_file_hashes_as_git_lists_it():
    """Asked of git itself, for a file of the panel as it is committed. A
    checkout with CRLF is other bytes and another hash, which is why the
    copy is held to the committed bytes and not to a checkout's."""
    rel = "data/weekly/2026-08-21.json"
    if not (ROOT / ".git").exists():
        pytest.skip("not a checkout: an exported tree has no objects to ask")
    try:
        listed = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD:" + rel],
            capture_output=True, text=True, check=True).stdout.strip()
    except OSError:
        pytest.skip("git is not installed here")
    committed = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "blob", listed],
        capture_output=True, check=True).stdout
    assert sfc.blob_sha(committed) == listed
    assert sfc.blob_sha(committed.replace(b"\n", b"\r\n")) != listed


# -- what is levelled ----------------------------------------------------------

def test_what_the_feed_is():
    assert sfc.in_feed("data/weekly/2026-10-02.json")
    assert sfc.in_feed("data/weekly/2026-08-28.corrected.json")
    for single in ("data/us2y_treasury.json",
                   "data/commodity_settlements.json",
                   "data/market_state.json"):
        assert sfc.in_feed(single)
    for other in ("data/universe.json", "data/daily/2026-10-05.json",
                  "data/weekly/old/2026-10-02.json", "data/weekly/notes.txt",
                  "scan_pipeline/snapshot.py", "README.md",
                  "xdata/weekly/2026-10-02.json"):
        assert not sfc.in_feed(other), other


def test_a_copy_that_is_level_is_left_exactly_as_it_is(tmp_path, capsys):
    root = runner_with(tmp_path, feed_of(REPO_FILES))
    before = tree_of(root)
    repo = Repo()
    assert run(root, repo, "--apply") == 0
    assert tree_of(root) == before
    assert repo.downloads == []
    assert last(capsys).startswith(
        "LEVEL with main ccccccc: 0 replaced, 0 added, 0 moved aside, "
        "6 already the repository's")


def test_a_copy_that_is_behind_is_brought_level(tmp_path, capsys):
    """The copy of 2026-10-06 in small: older versions of two weeks, each
    short of a name the repository's has gained; an old state; no history
    file and no correction."""
    older = doc("2026-09-25")
    del older["series"]["AAPL"]
    old = {"data/weekly/2026-09-25.json": blob(older),
           "data/weekly/2026-10-02.json": blob(doc("2026-10-02", SPY=100.0)),
           "data/market_state.json": b'{"as_of": "2026-09-25"}\n'}
    root = runner_with(tmp_path, old)
    repo = Repo()
    assert run(root, repo, "--apply") == 0
    now = tree_of(root)
    for path, data in feed_of(REPO_FILES).items():
        assert now[path] == data, path
    for path, data in old.items():
        kept = "data/replaced/%s/%s" % (STAMP, path[len("data/"):])
        assert now[kept] == data, "what the copy held is kept: " + path
    assert sorted(repo.downloads) == sorted(feed_of(REPO_FILES))
    assert "3 replaced, 3 added, 0 moved aside, 0 already" in last(capsys)


def test_a_dry_run_says_the_same_writes_nothing_and_exits_1(tmp_path, capsys):
    """Exit 1: the copy is not level, and a dry run is how that is asked
    without touching it."""
    root = stale(tmp_path)
    before = tree_of(root)
    assert run(root, Repo()) == 1
    assert tree_of(root) == before
    out = capsys.readouterr().out
    assert "replace  data/weekly/2026-10-02.json" in out
    assert "add      data/us2y_treasury.json" in out
    assert out.strip().splitlines()[-1].startswith(
        "DRY RUN against main ccccccc, nothing written: would replace 1, "
        "add 5 and move 0 aside")


def test_a_dry_run_of_a_level_copy_exits_0(tmp_path, capsys):
    root = runner_with(tmp_path, feed_of(REPO_FILES))
    assert run(root, Repo()) == 0
    assert "would replace 0, add 0 and move 0 aside" in last(capsys)


def test_a_crlf_copy_gets_the_repositorys_bytes(tmp_path):
    """Same document, other line endings: not the committed file."""
    crlf = REPO_FILES["data/weekly/2026-10-02.json"].replace(b"\n", b"\r\n")
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json": crlf}))
    assert run(root, Repo(), "--apply") == 0
    assert (root / "data/weekly/2026-10-02.json").read_bytes() == \
        REPO_FILES["data/weekly/2026-10-02.json"]


# -- what a weekly file held, it still holds ------------------------------------

def differing(mutate):
    """The copy's 2026-10-02.json, as the repository's with one thing the
    copy holds differently."""
    mine = doc("2026-10-02")
    mutate(mine)
    return blob(mine)


def vtr(mine):
    mine["series"]["SPY"]["volume"] = 1004      # typed as 1000 on its way


def name_the_repository_lacks(mine):
    mine["series"]["NVDA"] = {"close": 223.96, "volume": 5}


def instrument(mine):
    mine["rates"]["US10Y"]["close"] = 4.672


def label(mine):
    mine["provenance"] = {"series": {"AAPL": dict(ANCHOR)}}


def stamp(mine):
    mine["fetched_at"] = "2026-10-03T13:07:47Z"


def note(mine):
    mine["session_note"] = "Friday holiday; bars from 2026-10-01"


@pytest.mark.parametrize("mutate, said", [
    (vtr, 'series.SPY is {"close": 100.0, "volume": 1004} here and '
          '{"close": 100.0, "volume": 1000} in the repository\'s'),
    (name_the_repository_lacks, "series.NVDA is not in the repository's"),
    (instrument, "rates.US10Y is"),
    (label, "series.AAPL carries another label in the repository's"),
    (stamp, "`fetched_at` is"),
    (note, "`session_note` is"),
], ids=lambda v: getattr(v, "__name__", ""))
def test_a_file_the_repository_changed_is_refused_not_replaced(
        tmp_path, capsys, mutate, said):
    """The repository's file changes or lacks something this copy holds.
    The copy may be the true one (a week mistyped on its way: 0bcb75f), or
    the repository may have been rewritten; either way an observation is
    about to be lost, and it is the owner's to say which."""
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json": differing(mutate)}))
    out = refused(root, Repo(), capsys, "--apply")
    assert "data/weekly/2026-10-02.json is not an older copy" in out
    assert said in out
    assert "Do not edit, delete or push any of them" in out


def test_a_file_that_differs_in_many_entries_names_the_first_few(
        tmp_path, capsys):
    def many(mine):
        for n in range(7):
            mine["series"]["N%d" % n] = {"close": 1.0, "volume": 1}

    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json": differing(many)}))
    out = refused(root, Repo(), capsys, "--apply")
    assert "series.N3 is not in the repository's; and 3 more" in out
    assert "series.N4" not in out


def test_one_such_file_stops_every_other_write(tmp_path, capsys):
    """Not level in part: a copy with new history files and an old week the
    job cannot trust is worse than one that is plainly behind."""
    root = runner_with(tmp_path, {
        "data/weekly/2026-10-02.json": differing(vtr)})
    out = refused(root, Repo(), capsys, "--apply")
    assert "disagree about 1 file(s)" in out
    assert not (root / "data" / "us2y_treasury.json").exists()


def test_a_declared_rewrite_takes_the_repositorys(tmp_path, capsys):
    """By a person, for the weeks a declared backfill rewrote. Outside the
    range the rule holds."""
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json": differing(vtr),
        "data/weekly/2026-09-25.json": blob(dict(
            doc("2026-09-25"), fetched_at="2026-09-26T00:00:00Z"))}))
    out = refused(root, Repo(), capsys, "--apply", "--rewritten",
                  "2026-10-02", "2026-10-02")
    assert "2026-09-25.json is not an older copy" in out
    assert "2026-10-02.json is not an older copy" not in out

    assert run(root, Repo(), "--apply", "--rewritten", "2026-09-25",
               "2026-10-02") == 0
    out = capsys.readouterr().out
    assert "replace  data/weekly/2026-10-02.json  (declared rewritten)" in out
    assert (root / "data/weekly/2026-10-02.json").read_bytes() == \
        REPO_FILES["data/weekly/2026-10-02.json"]
    kept = root / "data" / "replaced" / STAMP / "weekly" / "2026-10-02.json"
    assert kept.read_bytes() == differing(vtr)


def test_a_declared_rewrite_may_change_and_may_not_remove(tmp_path, capsys):
    """As panel_guard takes --rewrite, and no further. Over the repository
    of 2026-08-26, 107 weeks cut from 287 series to 44, the declaration
    took all of it: 107 weeks replaced, exit 0, 286 to 289 series a week
    down to 43 or 44. An honest rewrite removes nothing a copy that is
    merely behind holds, so the allowance costs it nothing."""
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json":
            differing(name_the_repository_lacks)}))
    out = refused(root, Repo(), capsys, "--apply", "--rewritten",
                  "2026-09-25", "2026-10-02")
    assert "series.NVDA is not in the repository's" in out
    assert "inside the rewrite that was declared" in out
    assert "may change an entry and may not remove one" in out

    # changed and gone in one file: the change is lifted, the loss is not
    def both(mine):
        vtr(mine)
        name_the_repository_lacks(mine)

    root = runner_with(tmp_path / "b", dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json": differing(both)}))
    out = refused(root, Repo(), capsys, "--apply", "--rewritten",
                  "2026-10-02", "2026-10-02")
    assert "series.NVDA is not in the repository's" in out
    assert "series.SPY is" not in out


@pytest.mark.parametrize("mutate", [
    vtr, name_the_repository_lacks, instrument, label, stamp, note,
    lambda mine: None])
@pytest.mark.parametrize("name", ["2026-10-02.json",
                                  "2026-10-02.corrected.json"])
def test_a_declared_rewrite_is_the_guards_declaration(tmp_path, mutate, name):
    """One answer with panel_guard.compare for a file inside a declared
    rewrite, base week and correction alike: replaced exactly where the
    guard would pass it."""
    mine, theirs = doc("2026-10-02"), doc("2026-10-02")
    mutate(mine)
    rewrite = ("2026-10-02", "2026-10-02")
    result = pg.compare({"weekly/" + name: mine}, {"weekly/" + name: theirs},
                        rewrite)
    files = dict(REPO_FILES)
    files["data/weekly/" + name] = blob(theirs)
    root = runner_with(tmp_path, dict(feed_of(files), **{
        "data/weekly/" + name: blob(mine)}))
    code = run(root, Repo(files), "--apply", "--rewritten", *rewrite)
    assert (code == 0) == (not result["failed"]), result["failed"]
    assert sfc.in_rewrite(name, rewrite) == pg.in_rewrite(
        "weekly/" + name, rewrite)
    assert not sfc.in_rewrite(name, None)
    assert not sfc.in_rewrite("notes.json", ("0000-00-00", "zzzz"))


def test_a_correction_may_newly_restate_an_instrument(tmp_path):
    """restate_instruments.py changes a close in a correction and records
    it. The copy's older correction is behind, not in dispute."""
    older = doc("2026-08-28")
    newer = copy.deepcopy(older)
    newer["rates"]["US10Y"]["close"] = 4.72
    newer["provenance"] = {"rates": {"US10Y": dict(ANCHOR)}}
    newer["restated"] = [{"block": "rates", "ticker": "US10Y",
                          "was": {"close": 4.7, "volume": None}}]
    files = dict(REPO_FILES)
    files["data/weekly/2026-08-28.corrected.json"] = blob(newer)
    root = runner_with(tmp_path, dict(feed_of(files), **{
        "data/weekly/2026-08-28.corrected.json": blob(older)}))
    assert run(root, Repo(files), "--apply") == 0
    assert (root / "data/weekly/2026-08-28.corrected.json").read_bytes() == \
        blob(newer)


def test_a_base_week_gets_no_such_allowance(tmp_path, capsys):
    newer = doc("2026-10-02")
    newer["rates"]["US10Y"]["close"] = 4.72
    newer["restated"] = [{"block": "rates", "ticker": "US10Y",
                          "was": {"close": 4.7, "volume": None}}]
    files = dict(REPO_FILES)
    files["data/weekly/2026-10-02.json"] = blob(newer)
    root = runner_with(tmp_path, feed_of(REPO_FILES))
    assert "rates.US10Y is" in refused(root, Repo(files), capsys, "--apply")


@pytest.mark.parametrize("data", [b'{"as_of": "2026-10', b"",
                                  b'[{"as_of": "2026-10-02"}]\n'])
def test_a_copy_that_does_not_read_holds_nothing_to_lose(
        tmp_path, capsys, data):
    """A zero-byte file or the first bytes of a write that died, at a path
    the repository has a week for. Nothing in it can be compared; it is
    kept like any other file that is replaced."""
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json": data}))
    assert run(root, Repo(), "--apply") == 0
    assert (root / "data/weekly/2026-10-02.json").read_bytes() == \
        REPO_FILES["data/weekly/2026-10-02.json"]
    kept = root / "data" / "replaced" / STAMP / "weekly" / "2026-10-02.json"
    assert kept.read_bytes() == data


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
def test_a_copy_an_editor_saved_is_still_held_to_the_rule(
        tmp_path, capsys, encoding):
    """Opened and saved on Windows: a byte-order mark, or UTF-16. The same
    document, and what it holds can still be lost. It was replaced without
    the rule: one volume different from the repository's, exit 0."""
    mine = doc("2026-10-02")
    vtr(mine)
    saved = json.dumps(mine, indent=2).encode(encoding)
    assert sfc._parsed(saved, lenient=True) == mine
    assert sfc._parsed(saved) is None, "strictly, it is not the document"
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json": saved}))
    out = refused(root, Repo(), capsys, "--apply")
    assert "series.SPY is" in out

    same = json.dumps(doc("2026-10-02"), indent=2).encode(encoding)
    root = runner_with(tmp_path / "b", dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json": same}))
    assert run(root, Repo(), "--apply") == 0
    assert (root / "data/weekly/2026-10-02.json").read_bytes() == \
        REPO_FILES["data/weekly/2026-10-02.json"]


def test_a_repository_file_that_does_not_read_replaces_nothing(
        tmp_path, capsys):
    files = dict(REPO_FILES)
    files["data/weekly/2026-10-02.json"] = b"{ not json"
    root = runner_with(tmp_path, feed_of(REPO_FILES))
    out = refused(root, Repo(files), capsys, "--apply")
    assert ("1 file(s) the repository holds are not the weekly file they "
            "are named for, and are not taken.\n  - data/weekly/"
            "2026-10-02.json (it does not read as JSON)") in out


BOM = b"\xef\xbb\xbf"


@pytest.mark.parametrize("name, data, why", [
    ("2026-10-02.json", BOM + week("2026-10-02"), "it does not read as JSON"),
    ("2026-10-02.json", week("2026-10-02").decode("ascii").encode("utf-16"),
     "it does not read as JSON"),
    ("2026-10-02.json", week("2026-10-01"), 'its as_of is "2026-10-01"'),
    ("2026-10-02.json", blob(dict(doc("2026-10-02"), series={})),
     "it has no series"),
    ("2026-10-08.json", week("2026-10-08"), "its date is not a Friday"),
    ("2026-08-28.corrected.json", week("2026-08-21"),
     'its as_of is "2026-08-21"'),
    ("2026-08-28.corrected.json", BOM + week("2026-08-28"),
     "it does not read as JSON"),
    ("2026-08-28.corrected.json", blob(dict(doc("2026-08-28"), series={})),
     "it has no series"),
    ("notes.json", b'{"a": 1}',
     "its name is not <YYYY-MM-DD>.json or <YYYY-MM-DD>.corrected.json"),
])
def test_what_is_taken_from_the_repository_is_the_file_it_is_named_for(
        tmp_path, capsys, name, data, why):
    """A repository file with a byte-order mark went over a good copy,
    exit 0, and no reader on the runner could open it. One with another
    week's as_of keeps every bar the copy holds and went over it too, and
    that one the readers do open: as the week it is filed under. Main's own
    gate fails both. Taken or added, a weekly file has to read, strictly,
    as the week it is named for.

    Said apart from a disagreement: nothing the copy holds mends it (the
    copy may not hold the file at all), and no declaration lifts it."""
    files = dict(REPO_FILES)
    files["data/weekly/" + name] = data
    said = ("1 file(s) the repository holds are not the weekly file they "
            "are named for, and are not taken.\n  - data/weekly/%s (%s)\n"
            "The repository's own gate fails each." % (name, why))
    # in place of a good copy
    root = runner_with(tmp_path / "a", feed_of(REPO_FILES))
    out = refused(root, Repo(files), capsys, "--apply")
    assert said in out
    assert "disagree about" not in out and "from this copy" not in out
    # and where the copy has no such file yet
    mine = feed_of(REPO_FILES)
    mine.pop("data/weekly/" + name, None)
    root = runner_with(tmp_path / "b", mine)
    out = refused(root, Repo(files), capsys, "--apply")
    assert said in out and "It is put right in the repository" in out
    assert not (root / "data" / "weekly" / name).exists()
    # and a declaration does not lift it
    out = refused(root, Repo(files), capsys, "--apply", "--rewritten",
                  "2024-01-01", "2027-01-01")
    assert said in out and "--rewritten does not lift it" in out


def test_both_kinds_of_refusal_are_said_in_one_run(tmp_path, capsys):
    files = dict(REPO_FILES)
    files["data/weekly/2026-09-25.json"] = week("2026-09-18")
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json": differing(vtr)}))
    out = refused(root, Repo(files), capsys, "--apply")
    assert ("REFUSED, nothing written: 1 file(s) the repository holds are "
            "not the weekly file they are named for") in out
    assert ("--rewritten does not lift it.\nAlso, the repository and this "
            "copy disagree about 1 file(s)") in out


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
def test_a_week_only_the_copy_holds_is_read_as_its_readers_read_it(
        tmp_path, capsys, encoding):
    """Read leniently it was "a week written here and never pushed", for
    the job to push: a file the writer's own check says is not a weekly
    file, that the chain dies on and the gate fails. The lenient reading is
    for what a copy must not lose, and for nothing else."""
    saved = json.dumps(doc("2026-10-09"), indent=2).encode(encoding)
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-09.json": saved}))
    out = refused(root, Repo(), capsys, "--apply")
    assert ("data/weekly/2026-10-09.json is in the copy and not in the "
            "repository, and it reads as that week only the way an editor "
            "saves a file") in out
    assert "kept     " not in out
    # It is the only copy of an unpushed week. "Not a weekly file ... move
    # that one file out by hand" had it replaced by a later fetch.
    assert "it is not to be moved or deleted" in out
    assert "move that one file out" not in out

    # ... which is not said of a file an editor's reading does not make a
    # week either
    other = json.dumps(doc("2026-10-02"), indent=2).encode(encoding)
    root = runner_with(tmp_path / "b", dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-09.json": other}))
    out = refused(root, Repo(), capsys, "--apply")
    assert "it is not a weekly file (it does not read as JSON)" in out


def test_the_history_files_and_the_state_are_the_repositorys(tmp_path):
    """Never written on the runner, except the state, which the job derives
    again in any case. Nothing there is the copy's to keep."""
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/us2y_treasury.json": b'{"weeks": {"2026-10-02": 9.99}}\n',
        "data/market_state.json": b'{"as_of": "2026-10-09"}\n'}))
    assert run(root, Repo(), "--apply") == 0
    for path in ("data/us2y_treasury.json", "data/market_state.json"):
        assert (root / path).read_bytes() == REPO_FILES[path]


@pytest.mark.parametrize("mutate", [
    vtr, name_the_repository_lacks, instrument, label, stamp, note,
    lambda mine: None,
    lambda mine: mine["series"].pop("AAPL"),
    lambda mine: mine["rates"].pop("US10Y"),
    lambda mine: mine.pop("missing"),
])
def test_the_rule_is_panel_guards(mutate):
    """Repeated in the script because it runs alone. One answer with
    scripts/panel_guard.py for a pair of files, kind by kind: what is gone,
    changed, relabelled or restamped."""
    mine, theirs = doc("2026-10-02"), doc("2026-10-02")
    mutate(mine)
    for name in ("2026-10-02.json", "2026-10-02.corrected.json"):
        diff = pg.diff_file(name, mine, theirs)
        kinds = [kind for kind, _ in sfc.not_kept(name, mine, theirs)]
        for kind in ("gone", "changed", "relabelled", "stamps"):
            assert kinds.count(kind) == len(diff[kind]), (name, kind)
    assert sfc.BLOCKS == pg.BLOCKS and sfc.STAMPS == pg.STAMPS
    assert sfc.CORRECTED == pg.CORRECTED and sfc.GONE == "gone"


@pytest.mark.parametrize("recorded", [True, False])
def test_the_rule_is_panel_guards_for_a_restatement(recorded):
    """The one allowance, and only for an entry that is new in `restated`,
    in a correction, on an instrument."""
    mine = doc("2026-08-28")
    theirs = copy.deepcopy(mine)
    theirs["rates"]["US10Y"]["close"] = 4.72
    theirs["provenance"] = {"rates": {"US10Y": dict(ANCHOR)}}
    theirs["series"]["SPY"]["close"] = 99.0
    if recorded:
        theirs["restated"] = [
            {"block": "rates", "ticker": "US10Y",
             "was": {"close": 4.7, "volume": None}},
            {"block": "series", "ticker": "SPY",
             "was": {"close": 100.0, "volume": 1000}}]
    for name in ("2026-08-28.json", "2026-08-28.corrected.json"):
        diff = pg.diff_file(name, mine, theirs)
        kinds = [kind for kind, _ in sfc.not_kept(name, mine, theirs)]
        for kind in ("gone", "changed", "relabelled", "stamps"):
            assert kinds.count(kind) == len(diff[kind]), (name, kind)
    lifted = sfc.not_kept("2026-08-28.corrected.json", mine, theirs)
    assert (len(lifted) == 1) == recorded, "an equity close is never lifted"


# -- what the copy holds and the repository does not ---------------------------

def test_a_week_written_here_and_never_pushed_is_left_alone(tmp_path, capsys):
    """2026-10-09 is on the runner and has never been in the repository: a
    run that died between writing and pushing, as on 2026-08-15. It is the
    job's to push, and nothing here may touch it."""
    mine = week("2026-10-09")
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-09.json": mine}))
    repo = Repo()
    assert run(root, repo, "--apply") == 0
    assert (root / "data/weekly/2026-10-09.json").read_bytes() == mine
    out = capsys.readouterr().out
    assert "kept     data/weekly/2026-10-09.json" in out
    assert "1 week(s) kept that were never pushed" in \
        out.strip().splitlines()[-1]
    assert any(p.startswith("commits?") and "2026-10-09.json" in p
               for p in repo.asked), "the repository's history was asked"


def test_a_dry_run_names_a_week_that_is_kept_and_exits_0(tmp_path, capsys):
    """An --apply would change nothing: the week is the job's to push."""
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-09.json": week("2026-10-09")}))
    assert run(root, Repo()) == 0
    out = capsys.readouterr().out
    assert "kept     data/weekly/2026-10-09.json" in out
    assert "would replace 0, add 0 and move 0 aside" in out
    assert "1 week(s) kept that were never pushed" in out


def test_a_week_the_repository_withdrew_is_not_pushed_back(tmp_path, capsys):
    """Reverted in the repository on purpose. Called 'never pushed', the
    job's step 7 would put it back the next Saturday."""
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-09.json": week("2026-10-09")}))
    repo = Repo(once_held={"data/weekly/2026-10-09.json"})
    out = refused(root, repo, capsys, "--apply")
    assert "the repository held it once and has removed it" in out
    assert "it is not pushed again" in out
    assert "move the file out of data/weekly by hand" in out


def test_the_week_written_after_a_withdrawal_is_not_that_copy(
        tmp_path, capsys):
    """The refusal says to move the withdrawn copy out, after which the job
    writes the week whole. If that write's push dies, the file is again one
    the repository once held and does not list: refused as withdrawn every
    Saturday, until someone moved it by hand. It was fetched after the
    removal, so it is not what was withdrawn."""
    rewritten = dict(doc("2026-10-09"), fetched_at="2026-10-17T13:30:00Z")
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-09.json": blob(rewritten)}))
    repo = Repo(once_held={"data/weekly/2026-10-09.json"})
    assert run(root, repo, "--apply") == 0
    assert "kept     data/weekly/2026-10-09.json" in capsys.readouterr().out

    # A removal whose date cannot be read is later than any copy, and a
    # copy that does not say when it was fetched was not fetched after it.
    undated = Repo(once_held={"data/weekly/2026-10-09.json"}, removed=None)
    assert "has removed it" in refused(root, undated, capsys, "--apply")
    silent = dict(doc("2026-10-09"), fetched_at="some time in October")
    root = runner_with(tmp_path / "b", dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-09.json": blob(silent)}))
    assert "has removed it" in refused(root, repo, capsys, "--apply")


def test_a_history_that_cannot_be_read_is_refused(tmp_path, capsys):
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-09.json": week("2026-10-09")}))
    repo = Repo()
    real = repo.api
    repo.api = lambda name, path: {"message": "Not Found"} \
        if path.startswith("commits?") else real(name, path)
    assert "history of data/weekly/2026-10-09.json could not be read" in \
        refused(root, repo, capsys, "--apply")


def test_a_correction_the_repository_does_not_hold_is_moved_aside(
        tmp_path, capsys):
    """The job writes no correction, so this one was withdrawn in the
    repository or made here by hand, and every reader would prefer it to
    the week: the state derived from this copy would not be the
    repository's. It is kept, out of the readers' way."""
    mine = week("2026-09-25", SPY=1.0)
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-09-25.corrected.json": mine}))
    assert run(root, Repo(), "--apply") == 0
    assert not (root / "data/weekly/2026-09-25.corrected.json").exists()
    kept = root.joinpath("data", "replaced", STAMP, "weekly",
                         "2026-09-25.corrected.json")
    assert kept.read_bytes() == mine
    out = capsys.readouterr().out
    assert "aside    data/weekly/2026-09-25.corrected.json" in out
    assert "0 replaced, 0 added, 1 moved aside" in out


@pytest.mark.parametrize("name, data, why", [
    ("notes.json", b'{"a": 1}\n', "its name is not <YYYY-MM-DD>.json"),
    ("notes.corrected.json", week("2026-09-25"),
     "its name is not <YYYY-MM-DD>.json"),
    ("2026-10-02 (1).json", week("2026-10-02"), "its name is not"),
    ("2026-10-09.json", b'{"as_of": "2026-10', "it does not read as JSON"),
    ("2026-10-09.json", b"", "it does not read as JSON"),
    ("2026-10-09.json", week("2026-10-02"), 'its as_of is "2026-10-02"'),
    ("2026-10-08.json", week("2026-10-08"), "its date is not a Friday"),
    ("2026-13-45.json", week("2026-10-09"), "its name is not a date"),
    ("2026-10-09.json", blob(dict(doc("2026-10-09"), series={})),
     "it has no series"),
])
def test_a_file_that_is_not_a_week_is_refused_and_not_called_unpushed(
        tmp_path, capsys, name, data, why):
    """Reported as 'written here and never pushed', it would be pushed, and
    the gate fails it. unwritten_fridays counts a file at a week's path as
    the week, so the job would never write over it either."""
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/" + name: data}))
    out = refused(root, Repo(), capsys, "--apply")
    assert "is not a weekly file (%s" % why in out
    assert "It is not pushed" in out and "by hand" in out
    assert "kept     " not in out


# -- what is never written -----------------------------------------------------

def test_nothing_outside_the_feed_is_written(tmp_path, capsys):
    """universe.json is the job's to rebuild, the daily panel is not kept
    on the runner, and code is synced by hand."""
    mine = dict(feed_of(REPO_FILES), **{
        "data/universe.json": b'{"tickers": ["OLD"]}\n',
        "scan_pipeline/snapshot.py": b"VERSION = 1\n",
        "scan_pipeline/state/personas.json": b'{"live": true}\n',
        "scan_pipeline/run_scan.py.pre-pass1.bak": b"old\n"})
    root = runner_with(tmp_path, mine)
    before = tree_of(root)
    repo = Repo()
    assert run(root, repo, "--apply") == 0
    assert tree_of(root) == before
    assert repo.downloads == []
    assert not (root / "data" / "daily").exists()
    out = capsys.readouterr().out
    assert "code     scan_pipeline/snapshot.py differs" in out
    assert "council_watchlist.csv is not on the runner" in out
    assert "personas.json" not in out and "README.md" not in out
    assert "scan_pipeline: 2 file(s) behind, synced by hand" in \
        out.strip().splitlines()[-1]


def test_code_that_is_level_says_so(tmp_path, capsys):
    """Line endings aside: the runner's copy of the mirror backfill script
    is the repository's with CRLF, and it is not behind."""
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "scan_pipeline/snapshot.py":
            REPO_FILES["scan_pipeline/snapshot.py"].replace(b"\n", b"\r\n"),
        "scan_pipeline/config/council_watchlist.csv":
            REPO_FILES["scan_pipeline/config/council_watchlist.csv"]}))
    assert run(root, Repo(), "--apply") == 0
    assert capsys.readouterr().out.strip().endswith("scan_pipeline: level")


# -- a repository that could not be read ---------------------------------------

def test_no_answer_is_not_an_empty_repository(tmp_path, capsys):
    """And it is not the owner's to settle: asked again, it may answer."""
    repo = Repo()
    repo.down = True
    assert "could not ask the repository" in not_now(
        stale(tmp_path), repo, capsys, "--apply")


def test_a_truncated_listing_is_refused(tmp_path, capsys):
    """Half a listing reads as a repository that lacks the other half, and
    every week in that half would be 'kept' as never pushed."""
    assert "truncated" in refused(stale(tmp_path), Repo(truncated=True),
                                  capsys, "--apply")


def test_a_listing_with_no_weekly_file_is_refused(tmp_path, capsys):
    files = {p: d for p, d in REPO_FILES.items()
             if not p.startswith("data/weekly/")}
    assert "no weekly file" in refused(stale(tmp_path), Repo(files), capsys,
                                       "--apply")


@pytest.mark.parametrize("answer", [{}, {"commit": {}}, [], None])
def test_a_listing_that_cannot_be_read_is_refused(tmp_path, capsys, answer):
    repo = Repo()
    repo.api = lambda repo_name, path: answer
    assert "could not be read" in refused(stale(tmp_path), repo, capsys,
                                          "--apply")


def test_a_download_that_is_not_the_listed_file_writes_nothing(
        tmp_path, capsys):
    """Every file is checked before the first is written: one bad download
    among six leaves the copy as it was, not five-sixths level."""
    repo = Repo()
    real = repo.raw

    def raw(repo_name, commit, path):
        data = real(repo_name, commit, path)
        return data + b" " if path.endswith("market_state.json") else data

    repo.raw = raw
    out = not_now(stale(tmp_path), repo, capsys, "--apply")
    assert "data/market_state.json is not the file the repository lists" \
        in out


def test_a_download_that_fails_writes_nothing(tmp_path, capsys):
    repo = Repo()

    def raw(repo_name, commit, path):
        raise sfc.NotNow("could not download " + path)

    repo.raw = raw
    assert "could not download" in not_now(stale(tmp_path), repo, capsys,
                                           "--apply")


def test_the_two_fetches_have_one_commit(tmp_path):
    """The files are read at the commit the listing came from. A push
    between the two would otherwise level the copy with a panel that never
    existed."""
    seen = []
    repo = Repo()
    real = repo.raw

    def raw(repo_name, commit, path):
        seen.append(commit)
        return real(repo_name, commit, path)

    repo.raw = raw
    assert run(stale(tmp_path), repo, "--apply") == 0
    assert seen and set(seen) == {COMMIT}


# -- the two routes to the repository ------------------------------------------

class Routes:
    """The script's own two routes, with the wire replaced: what was asked
    of each, and whether the direct one answers."""

    def __init__(self, monkeypatch, direct=True, cli=True):
        self.http, self.gh = [], []
        self.direct, self.cli = direct, cli
        monkeypatch.setattr(sfc, "_http", self._http)
        monkeypatch.setattr(sfc, "_gh", self._gh)

    def _http(self, url):
        self.http.append(url)
        if not self.direct:
            raise OSError("HTTPError: HTTP Error 403: rate limit exceeded")
        return b'{"route": "direct"}'

    def _gh(self, *args):
        self.gh.append(args)
        if not self.cli:
            raise OSError("gh api: not logged in")
        return b'{"route": "gh"}'


def test_the_repository_is_read_directly_and_without_credentials(monkeypatch):
    routes = Routes(monkeypatch)
    assert sfc.fetch_api("o/r", "branches/main") == {"route": "direct"}
    assert sfc.fetch_raw("o/r", COMMIT, "data/weekly/x y.json") == \
        b'{"route": "direct"}'
    assert routes.http == [
        "https://api.github.com/repos/o/r/branches/main",
        "https://raw.githubusercontent.com/o/r/%s/data/weekly/x%%20y.json"
        % COMMIT]
    assert routes.gh == [], "the CLI is asked only when that is refused"
    assert "Authorization" not in sfc.HEADERS


def test_a_refused_request_is_asked_again_through_the_cli(monkeypatch):
    """The unauthenticated limit is 60 requests an hour for the machine."""
    routes = Routes(monkeypatch, direct=False)
    assert sfc.fetch_api("o/r", "branches/main") == {"route": "gh"}
    assert sfc.fetch_raw("o/r", COMMIT, "data/a.json") == b'{"route": "gh"}'
    assert routes.gh == [
        ("repos/o/r/branches/main",),
        ("repos/o/r/contents/data/a.json?ref=" + COMMIT, "-H",
         "Accept: application/vnd.github.raw")]


def test_neither_route_answering_names_both_and_can_be_asked_again(
        monkeypatch):
    Routes(monkeypatch, direct=False, cli=False)
    for call in (lambda: sfc.fetch_api("o/r", "branches/main"),
                 lambda: sfc.fetch_raw("o/r", COMMIT, "data/a.json")):
        with pytest.raises(sfc.NotNow) as said:
            call()
        assert "rate limit exceeded" in str(said.value)
        assert "not logged in" in str(said.value)


def test_an_answer_that_is_not_json_is_no_answer(monkeypatch):
    """A proxy's error page, served with a 200."""
    Routes(monkeypatch)
    monkeypatch.setattr(sfc, "_http", lambda url: b"<html>busy</html>")
    assert sfc.fetch_api("o/r", "branches/main") == {"route": "gh"}


def test_one_request_is_tried_three_times(monkeypatch):
    calls, slept = [], []

    class Answer:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"ok"

    def urlopen(req, timeout):
        calls.append(req.full_url)
        assert req.get_header("User-agent") and not req.has_header(
            "Authorization")
        if len(calls) < 3:
            raise OSError("reset")
        return Answer()

    monkeypatch.setattr(sfc.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(sfc.time, "sleep", slept.append)
    assert sfc._http("https://x/y") == b"ok"
    assert len(calls) == 3 and slept == [2, 4]

    calls.clear()
    monkeypatch.setattr(sfc.urllib.request, "urlopen",
                        lambda req, timeout: (_ for _ in ()).throw(
                            OSError("offline")))
    with pytest.raises(OSError, match="OSError: offline"):
        sfc._http("https://x/y")


def test_a_cli_that_is_not_installed_is_no_answer_too(monkeypatch):
    def http(url):
        raise OSError("URLError: offline")

    def run_gh(*args, **kwargs):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(sfc, "_http", http)
    monkeypatch.setattr(sfc.subprocess, "run", run_gh)
    with pytest.raises(sfc.NotNow, match="offline"):
        sfc.fetch_api("o/r", "branches/main")


# -- a copy that cannot be read or written -------------------------------------

@pytest.mark.parametrize("layout", [{}, {"data/weekly/notes.txt": b"x"},
                                    {"data/market_state.json": b"{}\n"}])
def test_a_directory_that_is_not_the_pipeline_root_is_refused(
        tmp_path, capsys, layout):
    """It levels a copy that exists. Pointed anywhere else it would build a
    whole panel there and call it levelled."""
    root = runner_with(tmp_path, layout)
    root.mkdir(parents=True, exist_ok=True)
    repo = Repo()
    out = refused(root, repo, capsys, "--apply")
    assert "not the pipeline root" in out and repo.downloads == []


def test_a_copy_that_cannot_be_read_is_said_and_not_a_traceback(
        tmp_path, capsys, monkeypatch):
    """A file held open by something else. No NOT LEVEL line and exit 1
    would read to the job as nothing in particular. It is not the owner's
    to settle either: the line says to run it once more."""
    root = stale(tmp_path)
    real = sfc.Path.read_bytes

    def read_bytes(self):
        if self.name == "2026-10-02.json":
            raise PermissionError(13, "The process cannot access the file")
        return real(self)

    monkeypatch.setattr(sfc.Path, "read_bytes", read_bytes)
    assert run(root, Repo(), "--apply") == 2
    out = capsys.readouterr().out
    assert ("INTERRUPTED before anything was written: the copy could not "
            "be read") in out
    assert "REFUSED" not in out
    tail = out.strip().splitlines()[-1]
    assert tail.startswith("NOT LEVEL") and "Run this once more" in tail


def test_a_directory_where_a_file_belongs_is_refused_before_any_write(
        tmp_path, capsys):
    root = stale(tmp_path)
    (root / "data" / "us2y_treasury.json").mkdir()
    out = refused(root, Repo(), capsys, "--apply")
    assert "data/us2y_treasury.json is a directory here" in out
    assert not (root / "data" / "replaced").exists()


def test_where_what_is_replaced_cannot_be_kept_nothing_is_replaced(
        tmp_path, capsys):
    root = stale(tmp_path)
    (root / "data" / "replaced").write_bytes(b"not a directory")
    out = refused(root, Repo(), capsys, "--apply")
    assert "data/replaced is not a directory" in out


def test_a_kept_copy_is_read_back_before_the_file_is_taken_away(
        tmp_path, capsys, monkeypatch):
    """A correction is moved aside by writing it under data/replaced and
    removing it. If what was written there is not what was read, removing
    it would be deleting it."""
    mine = week("2026-09-25", SPY=1.0)
    root = runner_with(tmp_path, dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-09-25.corrected.json": mine}))
    real = sfc.Path.write_bytes

    def write_bytes(self, data):
        if "replaced" in self.parts:
            data = data[:10]            # a disk that is full
        return real(self, data)

    monkeypatch.setattr(sfc.Path, "write_bytes", write_bytes)
    assert run(root, Repo(), "--apply") == 2
    out = capsys.readouterr().out
    assert "INTERRUPTED: 0 of 0 file(s) written" in out
    assert "did not read back as written" in out
    assert (root / "data/weekly/2026-09-25.corrected.json").read_bytes() == \
        mine, "still where it was"


def test_a_long_refusal_is_cut_to_what_can_be_carried(tmp_path, capsys):
    """The prompt has its agent copy what is printed into its END line.
    Over the repository of 2026-08-26 that was 111 lines and 33,611
    characters. The count stays whole; the list does not."""
    files = dict(REPO_FILES)
    mine = dict(feed_of(REPO_FILES))
    for day in fridays(28):
        name = "data/weekly/%s.json" % day
        files[name] = week(day)
        mine[name] = differing(vtr).replace(b"2026-10-02",
                                            day.encode("ascii"))
    root = runner_with(tmp_path, mine)
    out = refused(root, Repo(files), capsys, "--apply")
    assert "disagree about 28 file(s)" in out
    assert out.count("is not an older copy") == sfc.SHOW
    assert "... and 16 more file(s)" in out
    assert len(out) < 6000


def test_a_write_that_stops_part_way_says_so_and_can_be_repeated(
        tmp_path, capsys, monkeypatch):
    """Not 'nothing written': the copy is between two states. The line
    says to run it once more, and no half-written file is left behind."""
    root = stale(tmp_path)
    real = sfc.os.replace
    calls = []

    def replace(src, dst):
        calls.append(dst)
        if len(calls) == 3:
            raise OSError("disk full")
        return real(src, dst)

    monkeypatch.setattr(sfc.os, "replace", replace)
    assert run(root, Repo(), "--apply") == 2
    out = capsys.readouterr().out
    assert "INTERRUPTED: 2 of 6 file(s) written" in out
    assert "The copy is part old and part new" in out
    assert "REFUSED" not in out
    tail = out.strip().splitlines()[-1]
    assert tail.startswith("NOT LEVEL") and "Run this once more" in tail
    assert not list(root.rglob("*.part"))

    monkeypatch.setattr(sfc.os, "replace", real)
    assert run(root, Repo(), "--apply") == 0, "safe to repeat"
    for path, data in feed_of(REPO_FILES).items():
        assert (root / path).read_bytes() == data


def test_a_write_that_never_starts_does_not_claim_a_half_written_copy(
        tmp_path, capsys, monkeypatch):
    root = stale(tmp_path)

    def replace(src, dst):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(sfc.os, "replace", replace)
    assert run(root, Repo(), "--apply") == 2
    out = capsys.readouterr().out
    assert "0 of 6 file(s) written" in out
    assert "Nothing in the copy was replaced" in out
    assert "part old and part new" not in out
    assert not list(root.rglob("*.part"))


def test_a_refusal_survives_a_console_that_cannot_print_it(tmp_path):
    """Run as the job runs it, with a console encoding that cannot say the
    reason. A script that dies printing why it refused has refused nothing:
    exit 1, no line at all."""
    root = runner_with(tmp_path, {"data/weekly/café.txt": b"x"})
    script = ROOT / "scripts" / "sync_feed_copy.py"
    env = dict(os.environ, PYTHONIOENCODING="ascii", PYTHONUTF8="0")
    done = subprocess.run(
        [sys.executable, str(script), "--runner",
         str(root / "data" / "weekly" / "café.txt")],
        capture_output=True, env=env)
    assert done.returncode == 2, done.stderr.decode("ascii", "replace")
    out = done.stdout.decode("ascii")
    assert "REFUSED, nothing written" in out and "NOT LEVEL" in out
    assert r"caf\xe9" in out, "said, in what the console can print"


# -- the script as the job runs it ---------------------------------------------

def test_it_needs_nothing_but_the_standard_library():
    """Fetched fresh and run where nothing else is installed, like
    truth_check.py."""
    source = (ROOT / "scripts" / "sync_feed_copy.py").read_text(
        encoding="ascii")
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
    assert names <= set(sys.stdlib_module_names) | {"__future__"}, names


def endings(tmp_path, capsys, monkeypatch):
    """Every way a run ends, as (flags, exit code, the line that names the
    ending, the last line), each produced by running it."""
    seen = {}

    def ran(key, root, repo, *flags):
        code = run(root, repo, *flags)
        seen[key] = (code, capsys.readouterr().out.strip().splitlines())

    level = runner_with(tmp_path / "a", feed_of(REPO_FILES))
    ran("level", level, Repo(), "--apply")
    ran("dry", level, Repo())
    ran("dry, behind", stale(tmp_path / "b"), Repo())
    wrong = runner_with(tmp_path / "c", {
        "data/weekly/2026-10-02.json": differing(vtr)})
    ran("refused", wrong, Repo(), "--apply")
    down = Repo()
    down.down = True
    ran("not now", stale(tmp_path / "d"), down, "--apply")
    monkeypatch.setattr(sfc.os, "replace", lambda src, dst: (
        _ for _ in ()).throw(OSError("disk full")))
    ran("interrupted", stale(tmp_path / "e"), Repo(), "--apply")
    monkeypatch.undo()
    unpushed = runner_with(tmp_path / "f", dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-09.json": week("2026-10-09")}))
    ran("dry, a week not on main", unpushed, Repo())
    respelled = runner_with(tmp_path / "g", dict(feed_of(REPO_FILES), **{
        "data/weekly/2026-10-02.json":
            json.dumps(doc("2026-10-02")).encode("ascii")}))
    ran("dry, a week in other bytes", respelled, Repo())
    return seen


def test_every_ending_the_prompt_reads(tmp_path, capsys, monkeypatch):
    """Steps 0 and 7 of the job's prompt tell its agent what each last line
    means and what to do. The words it goes by are held here, each from a
    run that ends that way, with its exit code."""
    seen = endings(tmp_path, capsys, monkeypatch)
    # key: (exit code, how the last line starts, how a line above it starts)
    want = {
        "level": (0, "LEVEL with main ccccccc: ", None),
        "dry": (0, "DRY RUN against main ccccccc, nothing written: ", None),
        "dry, behind": (
            1, "DRY RUN against main ccccccc, nothing written: ", None),
        "dry, a week not on main": (
            0, "DRY RUN against main ccccccc, nothing written: ", None),
        "dry, a week in other bytes": (
            1, "DRY RUN against main ccccccc, nothing written: ", None),
        "refused": (
            2, "NOT LEVEL: the copy is as it was. Do not write a week on "
               "top of it.", "REFUSED, nothing written: "),
        "not now": (
            2, "NOT LEVEL: the repository or the copy could not be read "
               "this time, and the copy is as it was. Run this once more.",
            "INTERRUPTED before anything was written: "),
        "interrupted": (
            2, "NOT LEVEL: a disk error stopped the writing. Run this once "
               "more", "INTERRUPTED: 0 of 6 file(s) written"),
    }
    assert set(seen) == set(want)

    def word(line):
        return re.match(r"[A-Z]+(?: [A-Z]+)*", line).group(0)

    signs = {}
    for key, (code, last, above) in want.items():
        got, lines = seen[key]
        assert got == code, (key, lines[-1])
        assert lines[-1].startswith(last), (key, lines[-1])
        marks = [line for line in lines[:-1] if line[:1].isupper()]
        if above:
            assert marks and marks[0].startswith(above), (key, marks)
        signs.setdefault((word(marks[0]) if above else "", word(lines[-1]),
                          code), []).append(key)
    # What step 0 goes by after --apply: the first words of the last line,
    # the word above it and the exit code. Two of its endings share all
    # three, and the job is told the same thing by both: run it once more.
    assert signs[("INTERRUPTED", "NOT LEVEL", 2)] == ["not now",
                                                      "interrupted"]
    assert signs[("REFUSED", "NOT LEVEL", 2)] == ["refused"]
    assert signs[("", "LEVEL", 0)] == ["level"]
    # A dry run is read by its counts and not by its first words. Run after
    # a push, as step 7 runs it, a week that did not land looks at a glance
    # like a level copy, and its count of weeks kept is what says it is not.
    # One that went up as text looks like a copy that is behind, and nothing
    # in the line tells those two apart: "would replace 1" is all either
    # says.
    assert signs[("", "DRY RUN", 0)] == ["dry", "dry, a week not on main"]
    assert signs[("", "DRY RUN", 1)] == ["dry, behind",
                                         "dry, a week in other bytes"]
    level_line = seen["dry"][1][-1]
    assert ("would replace 0, add 0 and move 0 aside" in level_line
            and "0 week(s) kept that were never pushed" in level_line)
    kept_line = seen["dry, a week not on main"][1][-1]
    assert ("would replace 0, add 0 and move 0 aside" in kept_line
            and "1 week(s) kept that were never pushed" in kept_line)
    assert "would replace 1, add 0 and move 0 aside" in \
        seen["dry, a week in other bytes"][1][-1]


# -- small things --------------------------------------------------------------

def test_values_are_compared_as_panel_guard_compares_them():
    nan = float("nan")
    for a, b in [(100, 100.0), (True, 1), (True, True), (None, 0), ("1", 1),
                 (nan, nan), ([1], [1, 2]), ([1, {"a": 2}], [1, {"a": 2.0}]),
                 ({"a": 1}, {"b": 1}), ({"close": 1.5}, {"close": 1.5})]:
        assert sfc.same(a, b) == pg.same(a, b), (a, b)
    assert sfc.same(100, 100.0) and not sfc.same(True, 1)


def test_the_cli_route_hands_back_its_answer_or_its_error(monkeypatch):
    class Done:
        def __init__(self, code, out=b"", err=b""):
            self.returncode, self.stdout, self.stderr = code, out, err

    calls = []

    def run_gh(cmd, **kwargs):
        calls.append(cmd)
        return Done(0, b'{"ok": 1}') if len(calls) == 1 \
            else Done(1, err=b"gh: Not Found (HTTP 404)\n")

    monkeypatch.setattr(sfc.subprocess, "run", run_gh)
    assert sfc._gh("repos/o/r/branches/main") == b'{"ok": 1}'
    assert calls[0] == ("gh", "api", "repos/o/r/branches/main")
    with pytest.raises(OSError, match=r"gh api: gh: Not Found \(HTTP 404\)"):
        sfc._gh("repos/o/r/x")


def test_a_long_plan_is_cut_and_its_totals_are_whole(tmp_path, capsys):
    files = dict(REPO_FILES)
    for n, day in enumerate(fridays(28)):
        files["data/weekly/%s.json" % day] = week(day)
        files["scan_pipeline/m%02d.py" % n] = b"X = %d\n" % n
    root = stale(tmp_path)
    assert run(root, Repo(files), "--apply") == 0
    out = capsys.readouterr().out
    assert out.count("  add      ") == sfc.SHOW + 1
    assert "  add      ... and 21 more" in out
    assert "  code     ... and 18 more" in out
    assert "1 replaced, 33 added, 0 moved aside" in out
    assert "scan_pipeline: 30 file(s) behind" in out


def test_a_file_that_does_not_read_back_is_not_called_written_whole(
        tmp_path, capsys, monkeypatch):
    """The copy then holds bytes nobody wrote on purpose, and the line must
    not say nothing was replaced."""
    root = stale(tmp_path)
    real = sfc.os.replace

    def replace(src, dst):
        real(src, dst)
        with open(dst, "ab") as handle:
            handle.write(b" ")

    monkeypatch.setattr(sfc.os, "replace", replace)
    assert run(root, Repo(), "--apply") == 2
    out = capsys.readouterr().out
    assert "INTERRUPTED: 1 of 6 file(s) written, then OSError" in out
    assert "did not read back as written" in out
    assert "The copy is part old and part new" in out


def test_a_date_that_is_not_one_is_not_a_declaration(tmp_path, capsys):
    root = runner_with(tmp_path, feed_of(REPO_FILES))
    with pytest.raises(SystemExit) as stopped:
        run(root, Repo(), "--rewritten", "2026-13-01", "2026-10-02")
    assert stopped.value.code == 2
    assert "not a date" in capsys.readouterr().err


def test_it_runs_on_its_own_two_routes_when_it_is_given_none(
        tmp_path, capsys, monkeypatch):
    """As the job runs it: no fetch handed in. The one test of the defaults
    went out with a mode that was removed, and with `api` defaulting to
    nothing every live run ended REFUSED on a TypeError while 113 tests
    passed."""
    repo = Repo()
    api_at = sfc.API % (sfc.REPO, "")
    raw_at = sfc.RAW % (sfc.REPO, COMMIT, "")

    def http(url):
        if url.startswith(api_at):
            return json.dumps(repo.api(sfc.REPO, url[len(api_at):])).encode()
        assert url.startswith(raw_at), url
        return repo.raw(sfc.REPO, COMMIT, url[len(raw_at):])

    monkeypatch.setattr(sfc, "_http", http)
    monkeypatch.setattr(sfc, "_gh", lambda *args: (_ for _ in ()).throw(
        AssertionError("the CLI is asked only when that is refused")))
    root = stale(tmp_path)
    assert sfc.main(["--runner", str(root), "--apply"], now=NOW) == 0
    assert last(capsys).startswith("LEVEL with main ccccccc: 1 replaced, "
                                   "5 added")
    assert sfc.main(["--runner", str(root)]) == 0
