"""Ophelia's reason line follows the pick's own scores (2026-11-25).

On 2026-11-23 EIX, a utility, was booked at 25.5% with the line "Aligned
with Energy sector rotation": the template was chosen by rank, not by the
pick. These pin that the rotation line appears only for a pick in the top
sector, and that rank no longer picks the text.
"""
from scan_pipeline.engines.ophelia import _generate_thesis


def pick(sector, regime=10.0, risk=5.0):
    return {"ticker": "X", "score": 57.0, "sector": sector, "vol": 0.018,
            "market_regime_score": regime, "risk_adjusted_score": risk}


def test_rotation_line_only_for_a_top_sector_pick():
    line = _generate_thesis(pick("Utilities"), 0, "Energy", -0.05, "bearish")
    assert "sector rotation" not in line
    assert "Utilities, not the top sector, Energy" in line
    line = _generate_thesis(pick("Energy"), 2, "Energy", -0.05, "bearish")
    assert line.startswith("Aligned with Energy sector rotation")


def test_rank_does_not_choose_the_line():
    lines = {_generate_thesis(pick("Utilities"), i, "Energy", -0.05, "bearish") for i in range(3)}
    assert len(lines) == 1


def test_larger_term_names_the_reason():
    assert "market regime" in _generate_thesis(pick("Utilities", 20.0, 5.0), 0, "Energy", -0.05)
    assert "lower volatility" in _generate_thesis(pick("Utilities", 5.0, 20.0), 0, "Energy", -0.05)


def test_lines_are_ascii():
    for i in range(3):
        _generate_thesis(pick("Utilities"), i, "Energy", 0.01).encode("ascii")
