"""The earnings blackout, now shared by all three engines.

Until 2026-09-21 only Cecil's picks were screened for earnings, and by
marking the pick for the gate to drop, which cost him the slot. The Testing
Room found TPR, an Ophelia pick, held through its 8/13 print for -20%. Every
engine now passes over a name that reports inside the holding week and
proposes its next-best name instead. These tests pin the window's edges and
prove the pass-over actually happens -- and that with no earnings data the
ranking is untouched, which is what keeps the Engine Lab's Pass 1 and Pass 2
replays reproducible.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scan_pipeline.utils.data_utils import (  # noqa: E402
    EARNINGS_BLACKOUT_TRADING_DAYS,
    earnings_blackout,
    tradeable_picks,
)


def ranking(*tickers):
    return [{"ticker": t, "score": 100.0 - i} for i, t in enumerate(tickers)]


def market(**trading_days):
    return {"stockData": {t: {"earnings_date": "2026-08-13", "earnings_trading_days": d}
                          for t, d in trading_days.items()}}


def test_window_is_the_holding_week():
    assert EARNINGS_BLACKOUT_TRADING_DAYS == 5
    md = market(A=0, B=1, C=5, D=6, E=-1, F=None)
    assert earnings_blackout(md, "A") == ("2026-08-13", 0)
    assert earnings_blackout(md, "B") == ("2026-08-13", 1)
    assert earnings_blackout(md, "C") == ("2026-08-13", 5)
    assert earnings_blackout(md, "D") is None        # reports after the week
    assert earnings_blackout(md, "E") is None        # already reported
    assert earnings_blackout(md, "F") is None        # unknown dates never exclude
    assert earnings_blackout(md, "ZZZ") is None      # no stock data at all


def test_reporter_is_passed_over_for_the_next_best_name():
    scores = ranking("TPR", "ITW", "AES", "BAC", "PCAR")
    tradeable, skipped = tradeable_picks(scores, market(TPR=4))
    assert [s["ticker"] for s in tradeable[:3]] == ["ITW", "AES", "BAC"]
    assert skipped == [{"ticker": "TPR", "earnings_date": "2026-08-13",
                        "earnings_trading_days": 4}]


def test_only_names_that_would_have_been_picked_are_logged():
    scores = ranking("A", "B", "C", "D", "E")
    _, skipped = tradeable_picks(scores, market(B=2, E=3))
    assert [s["ticker"] for s in skipped] == ["B"]   # E ranked below the third pick


def test_no_earnings_data_leaves_the_ranking_untouched():
    scores = ranking("A", "B", "C", "D")
    tradeable, skipped = tradeable_picks(scores, {"stockData": {}})
    assert tradeable == scores
    assert skipped == []
