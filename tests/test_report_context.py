"""The report's VIX, SPY and Fed Stance lines come from what is committed.

On 2026-11-23 the pipeline printed VIX 30.9 (a pre-market read; Friday
closed at 35.89), SPY -7.98% (Monday open to Friday close; Friday to Friday
was -8.56%) and "Unknown. Stance source unavailable." (facts.json said
Hike), and the Council session fixed all three by hand. These pin the
committed sources, the fallbacks that name themselves, and that the lines
still parse for portfolio/tracker.py.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scan_pipeline import run_scan as rs  # noqa: E402

LIVE = {"auditDates": {"monday": "2026-11-16", "friday": "2026-11-20"},
        "vix": "30.9", "weeklyReturns": {"SPY": -0.0798},
        "market_conditions": {"fed_stance": rs.STANCE_UNAVAILABLE}}
FACTS = {"policy": {"fed_stance": {"value": "Hike", "as_of": "2026-09-16"}}}


def test_2026_11_23_from_the_committed_panel():
    ctx = rs.report_context(LIVE, FACTS, None, str(ROOT / "data" / "weekly"))
    assert ctx["vix"].startswith("35.89 (Friday 2026-11-20 close")
    assert ctx["spy"].startswith("-8.56% (Friday 2026-11-13 to Friday 2026-11-20")
    assert ctx["fed"].startswith("Tightening. facts.json policy.fed_stance = \"Hike\"")


def _week(path: Path, day: str, spy: float, vix=None):
    doc = {"as_of": day, "series": {"SPY": {"close": spy, "volume": 1}},
           "vol": {} if vix is None else {"VIX": {"close": vix, "volume": None}}}
    (path / f"{day}.json").write_text(json.dumps(doc), encoding="utf-8")


def test_a_correction_is_read_in_place_of_its_base(tmp_path):
    _week(tmp_path, "2026-11-13", 100.0)
    _week(tmp_path, "2026-11-20", 90.0, 30.0)
    doc = {"as_of": "2026-11-20", "series": {"SPY": {"close": 95.0, "volume": 1}},
           "vol": {"VIX": {"close": 31.5, "volume": None}}}
    (tmp_path / "2026-11-20.corrected.json").write_text(json.dumps(doc), encoding="utf-8")
    ctx = rs.report_context(LIVE, FACTS, None, str(tmp_path))
    assert ctx["vix"].startswith("31.50 ")
    assert ctx["spy"].startswith("-5.00% ")


def test_a_hole_is_not_bridged_and_the_live_read_names_itself(tmp_path):
    _week(tmp_path, "2026-11-06", 100.0)
    _week(tmp_path, "2026-11-20", 90.0)          # no VIX, no 11-13 file
    ctx = rs.report_context(LIVE, {}, None, str(tmp_path))
    assert ctx["vix"].startswith("30.9 (live read at run time, not a Friday close")
    assert ctx["spy"].startswith("-7.98% (Monday open to Friday close")
    assert ctx["fed"] == rs.STANCE_UNAVAILABLE


def test_a_valid_override_wins_and_an_invalid_one_does_not():
    ctx = rs.report_context(LIVE, FACTS, "Hold. Rates 3.50-3.75%.", str(ROOT / "data" / "weekly"))
    assert ctx["fed"] == "Hold. Rates 3.50-3.75%."
    ctx = rs.report_context(LIVE, FACTS, "Fed issues enforcement action", str(ROOT / "data" / "weekly"))
    assert ctx["fed"].startswith("Tightening.")


def test_moves_read_as_the_stance_they_imply():
    for move, lead in (("Hike", "Tightening."), ("Cut", "Easing."), ("Hold", "Neutral."),
                       ("Hawkish", "Hawkish.")):
        line = rs.fed_stance_from_facts({"policy": {"fed_stance": {"value": move}}})
        assert line.startswith(lead), (move, line)
    assert rs.fed_stance_from_facts({"policy": {"fed_stance": {"value": "Enforcement action"}}}) is None


def test_lines_parse_for_the_tracker_and_are_ascii():
    ctx = rs.report_context(LIVE, FACTS, None, str(ROOT / "data" / "weekly"))
    text = "\n".join([f"- **VIX:** {ctx['vix']}", f"- **SPY Weekly Return:** {ctx['spy']}",
                      f"- **Fed Stance:** {ctx['fed']}"])
    text.encode("ascii")
    assert float(re.search(r"\*\*VIX:\*\*\s*([\d.]+)", text).group(1)) == 35.89
    assert float(re.search(r"\*\*SPY Weekly Return:\*\*\s*([\-+\d.]+)%", text).group(1)) == -8.56
    lead = re.split(r"[.,:;]", re.search(r"\*\*Fed Stance:\*\*\s*(.+)", text).group(1), maxsplit=1)[0]
    assert lead.strip().lower() == "tightening"
