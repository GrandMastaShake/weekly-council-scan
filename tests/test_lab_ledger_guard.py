"""scripts/lab_ledger_guard.py: a row on file in a lab ledger stays as it was.

These pin the rule on made-up ledgers (a row changed or removed fails, a row
added anywhere passes, a file gone fails, a new ledger passes), that git's
own environment does not steer it to another repository, and that every
ledger it names is one the repository has or a lab script writes.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import lab_ledger_guard as g  # noqa: E402

A = {"friday": "2026-11-20", "call": "cold"}
B = {"friday": "2026-11-27", "call": "warm"}
C = {"friday": "2026-12-04", "call": "warm"}


def test_rows_kept_pass_wherever_new_ones_land():
    assert g.compare("x", "calls", {"calls": [A, B]}, {"calls": [A, B, C]}) == []
    assert g.compare("x", "calls", {"calls": [A, C]}, {"calls": [A, B, C]}) == []
    assert g.compare("x", None, [A], [A, B]) == []


def test_a_changed_or_removed_row_fails():
    assert g.compare("x", "calls", {"calls": [A, B]}, {"calls": [A, dict(B, call="cold")]})
    assert g.compare("x", "calls", {"calls": [A, B]}, {"calls": [B]})
    assert g.compare("x", "calls", {"calls": [A, A]}, {"calls": [A]})     # a repeat counts
    assert g.compare("x", "calls", {"calls": [A]}, None)                   # the file is gone
    assert g.compare("x", "calls", {"calls": [A]}, {"rows": [A]})          # the list is gone


def test_header_fields_and_key_order_are_not_held():
    before = {"rules": "old words", "calls": [{"a": 1, "b": 2}]}
    after = {"rules": "new words", "calls": [{"b": 2, "a": 1}]}
    assert g.compare("x", "calls", before, after) == []


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_against_a_commit_and_not_steered_by_git_dir(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "lab").mkdir(parents=True)
    ledger = repo / "lab" / "regime_calls.json"
    ledger.write_text(json.dumps({"calls": [A, B]}), encoding="utf-8")
    run = lambda *a: subprocess.run(["git", "-C", str(repo)] + list(a), check=True,
                                    capture_output=True, env={"PATH": __import__("os").environ["PATH"],
                                                              "HOME": str(tmp_path)})
    run("init", "-q")
    run("add", "-A")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "one")
    # A hook or `rebase --exec` exports GIT_DIR; the guard must not follow it.
    monkeypatch.setenv("GIT_DIR", str(ROOT / ".git"))
    assert g.check(str(repo), "HEAD") == 0
    ledger.write_text(json.dumps({"calls": [A, B, C]}), encoding="utf-8")
    assert g.check(str(repo), "HEAD") == 0
    ledger.write_text(json.dumps({"calls": [A, dict(B, call="cold"), C]}), encoding="utf-8")
    assert g.check(str(repo), "HEAD") == 1
    ledger.unlink()
    assert g.check(str(repo), "HEAD") == 1
    assert g.check(str(repo), "no-such-commit") == 1


def test_every_ledger_named_is_real():
    """A ledger on disk is read under the key named; one not yet on disk is
    one a lab script writes (the weekend pick's file starts with its first
    pick)."""
    for path, key in g.LEDGERS.items():
        full = ROOT / path
        if full.exists():
            assert g.rows_of(json.loads(full.read_text(encoding="utf-8")), key) is not None, path
        else:
            name = Path(path).name
            assert any(name in p.read_text(encoding="utf-8") for p in (ROOT / "lab").glob("*.py")), path


def test_the_committed_ledgers_hold_against_head():
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("needs a git checkout")
    if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", "HEAD"],
                      capture_output=True).returncode != 0:
        pytest.skip("no HEAD")
    assert g.check(str(ROOT), "HEAD") == 0
