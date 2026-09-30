"""The weekly journal update after Journal.beliefs was removed (2026-09-13).

update_agent_personality still appended a canned lesson to journal.beliefs,
so a member whose week earned one raised AttributeError, and run_scan lost
every member's journal update and the report's performance section (the
2026-09-28 log: "'Journal' object has no attribute 'beliefs'").
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scan_pipeline.engines import personality as p  # noqa: E402


@pytest.fixture(autouse=True)
def no_history(monkeypatch):
    """The accuracy EMA reads closed-week YAMLs from disk; not under test."""
    monkeypatch.setattr(p, "update_accuracy_from_history", lambda personas, *a, **k: personas)


def week(contribution, accuracy, confidence=60.0):
    return p.PerformanceReport(
        weekEndingDate="2026-09-25", portfolioReturn=contribution, benchmarkReturn=0.0067,
        alpha=contribution - 0.0067,
        agentContribution={"Cecil": p.AgentPerformance(
            proposals=["ALL", "HIG", "VICI"], inFinalPortfolio=["HIG"],
            confidence=confidence, contribution=contribution, accuracy=accuracy)},
    )


def test_a_week_that_earned_the_old_win_lesson_is_journaled():
    out = p.update_agent_personality(copy.deepcopy(p.CECIL_PERSONALITY), week(0.05, 0.9), "Cecil")
    assert out.journal.lastBigWin.result == 0.05
    assert out.evolution.recentAdjustments[-1].startswith("Week of 2026-09-25:")


def test_a_week_that_earned_the_old_hubris_lesson_is_journaled():
    out = p.update_agent_personality(copy.deepcopy(p.CECIL_PERSONALITY), week(-0.05, 0.2, 80.0), "Cecil")
    assert out.journal.lastBigLoss.result == -0.05
    assert out.evolution.nextWeekPriority.startswith("I strayed too far from value")


def test_a_saved_persona_with_the_old_field_still_loads():
    d = copy.deepcopy(p.CECIL_PERSONALITY).to_dict()
    d["journal"]["beliefs"] = ["See? Patience pays."]
    d["journal"]["bigWins"] = [{"date": "2026-09-25", "thesis": "HIG", "result": 0.05}]
    back = p.AIPersonality.from_dict(d)
    assert back.journal.bigWins[0].result == 0.05
    assert not hasattr(back.journal, "beliefs")
