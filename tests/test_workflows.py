"""Every workflow file must parse, and declare the triggers it claims.

daily-observe.yml shipped invalid. One unquoted description --

    description: Session date YYYY-MM-DD (default: latest weekday)

-- put a bare ": " inside a scalar, so YAML read it as a nested mapping and
the file would not parse at all. GitHub still LISTED the workflow as active,
so `gh workflow list` looked fine; the triggers were simply never registered.
A manual dispatch returned "Workflow does not have 'workflow_dispatch'
trigger", and the 21:45 cron would have silently never fired.

Nothing caught it: CI runs pytest and the feed gates, and neither reads the
workflow files. This does.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def triggers(doc):
    """The `on:` block.

    YAML 1.1 resolves a bare `on` to the boolean True, so the key is not the
    string "on" -- the single most common way an Actions file is misread by
    tooling that checks it.
    """
    if "on" in doc:
        return doc["on"]
    return doc.get(True)


def test_there_are_workflows_to_check():
    assert WORKFLOWS, "no workflow files found; this test would vacuously pass"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_parses(path):
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        pytest.fail(path.name + " is not valid YAML, so GitHub cannot read "
                    "its triggers: " + str(exc))
    assert isinstance(doc, dict), path.name + " is not a mapping"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_declares_triggers_and_jobs(path):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    trig = triggers(doc)
    assert trig, (path.name + " declares no `on:` triggers. A workflow with "
                  "none is registered and never runs.")
    assert doc.get("jobs"), path.name + " declares no jobs"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_scheduled_workflows_are_dispatchable(path):
    """A cron you cannot fire by hand is a cron you cannot test."""
    trig = triggers(yaml.safe_load(path.read_text(encoding="utf-8")))
    if "schedule" not in trig:
        pytest.skip("not scheduled")
    assert "workflow_dispatch" in trig, (
        path.name + " runs on a schedule but cannot be dispatched manually")


def test_daily_observe_is_dispatchable_with_its_inputs():
    """The specific regression, pinned by name."""
    path = ROOT / ".github" / "workflows" / "daily-observe.yml"
    trig = triggers(yaml.safe_load(path.read_text(encoding="utf-8")))
    dispatch = trig["workflow_dispatch"]
    assert set(dispatch["inputs"]) == {"date", "since", "dry_run"}
    assert dispatch["inputs"]["dry_run"]["type"] == "boolean"
    assert "schedule" in trig


def daily_observe():
    path = ROOT / ".github" / "workflows" / "daily-observe.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_daily_observe_gets_a_second_attempt_the_morning_after():
    """One attempt per session lost 2026-09-25 and 2026-10-02: each was
    refused once, inside the provider's null-close window, and nothing asked
    again. The second attempt runs on the days AFTER the weekdays, when the
    session it is for is yesterday's."""
    crons = [s["cron"].split() for s in triggers(daily_observe())["schedule"]]
    assert len(crons) == 2, crons
    evening, morning = sorted(crons, key=lambda c: -int(c[1]))
    assert evening[4] == "1-5", "the evening attempt runs Monday to Friday"
    assert morning[4] == "2-6", (
        "the morning-after attempt runs Tuesday to Saturday UTC, so Friday's "
        "session is retried on Saturday")
    # Hours after the null-close window, and hours before the next close, so
    # a start three hours late still finds yesterday settled and still the
    # latest closed session.
    assert 5 <= int(morning[1]) <= 12, morning


def test_daily_observe_audits_the_panel_even_after_a_refusal():
    """A refusal exits clean, so the steps that only run after a write can
    never be the alarm. The audit is the step that goes red, and it has to
    run on exactly the runs where nothing was written."""
    steps = daily_observe()["jobs"]["observe"]["steps"]
    audits = [s for s in steps if "--audit" in str(s.get("run", ""))]
    assert len(audits) == 1, "expected one audit step"
    audit = audits[0]
    assert steps[-1] is audit, "the audit runs last, after any commit"
    condition = str(audit.get("if", ""))
    assert "cancelled()" in condition, (
        "the audit must not be skipped when an earlier step failed")
    assert "refused" not in condition and "dry_run" not in condition, (
        "the audit must run on a refused run: " + condition)
    assert "exit" in audit["run"], "the audit's exit code must reach the job"
