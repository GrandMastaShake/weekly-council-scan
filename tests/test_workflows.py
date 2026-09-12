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
    assert set(dispatch["inputs"]) == {"date", "dry_run"}
    assert dispatch["inputs"]["dry_run"]["type"] == "boolean"
    assert "schedule" in trig
