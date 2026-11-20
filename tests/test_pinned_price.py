"""The pinned-price screen, shared by all three engines.

AES closed inside $14.80-$15.05 for two months, the way a stock under a cash
offer does, and Cecil's engine ranked it second on 2026-11-16: a low P/E, and
full safety points for having no volatility. The Council booked it twice as
hidden cash. Every engine now passes over a name whose weekly volatility is
near zero and proposes its next-best name, exactly as the earnings blackout
does. These tests pin the rule's edges, prove the pass-over happens, and
prove that stock data without a history count leaves the ranking untouched,
which is what keeps earlier callers and fixtures behaving as they did.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scan_pipeline.engines import cecil  # noqa: E402
from scan_pipeline.fetch_market_data import _aggregate_weekly, _risk_stats  # noqa: E402
from scan_pipeline.utils import data_utils  # noqa: E402
from scan_pipeline.utils.data_utils import (  # noqa: E402
    PINNED_MIN_WEEKS,
    PINNED_VOL_MAX,
    pinned_price,
    tradeable_picks,
)


def ranking(*tickers):
    return [{"ticker": t, "score": 100.0 - i} for i, t in enumerate(tickers)]


def market(**stocks):
    return {"stockData": dict(stocks)}


def test_the_rule_and_its_edges():
    assert PINNED_VOL_MAX == 0.05
    assert PINNED_MIN_WEEKS == 8
    md = market(
        PIN={"realized_vol": 0.02, "history_weeks": 13},
        EDGE={"realized_vol": 0.05, "history_weeks": 13},      # at the line: not pinned
        QUIET={"realized_vol": 0.13, "history_weeks": 13},     # the quietest ordinary stock
        YOUNG={"realized_vol": 0.01, "history_weeks": 7},      # too little history to say
        JUST={"realized_vol": 0.01, "history_weeks": 8},
        NOVOL={"realized_vol": None, "history_weeks": 13},
        NOCOUNT={"realized_vol": 0.01},                        # a caller that sends no count
    )
    assert pinned_price(md, "PIN") == (0.02, 13)
    assert pinned_price(md, "JUST") == (0.01, 8)
    for t in ("EDGE", "QUIET", "YOUNG", "NOVOL", "NOCOUNT", "ZZZ"):
        assert pinned_price(md, t) is None, t


def test_a_pinned_name_is_passed_over_for_the_next_best_name():
    scores = ranking("ALL", "AES", "TROW", "PRU", "CI")
    md = market(AES={"realized_vol": 0.026, "history_weeks": 13},
                ALL={"realized_vol": 0.22, "history_weeks": 13})
    tradeable, skipped = tradeable_picks(scores, md)
    assert [s["ticker"] for s in tradeable[:3]] == ["ALL", "TROW", "PRU"]
    assert skipped == [{"ticker": "AES", "pinned": True, "realized_vol": 0.026, "history_weeks": 13}]


def test_only_names_that_would_have_been_picked_are_logged():
    scores = ranking("A", "B", "C", "D", "E")
    pin = {"realized_vol": 0.01, "history_weeks": 13}
    _, skipped = tradeable_picks(scores, market(B=pin, E=pin))
    assert [s["ticker"] for s in skipped] == ["B"]   # E ranked below the third pick


def test_pinned_and_reporting_is_logged_once_as_pinned():
    scores = ranking("A", "B", "C", "D")
    md = market(A={"realized_vol": 0.01, "history_weeks": 13,
                   "earnings_date": "2026-11-18", "earnings_trading_days": 3},
                B={"earnings_date": "2026-11-19", "earnings_trading_days": 4})
    tradeable, skipped = tradeable_picks(scores, md)
    assert [s["ticker"] for s in tradeable] == ["C", "D"]
    assert skipped == [
        {"ticker": "A", "pinned": True, "realized_vol": 0.01, "history_weeks": 13},
        {"ticker": "B", "earnings_date": "2026-11-19", "earnings_trading_days": 4},
    ]


def test_stock_data_without_a_history_count_leaves_the_ranking_untouched():
    scores = ranking("A", "B", "C", "D")
    md = market(A={"realized_vol": 0.0, "max_drawdown": 0.0})
    tradeable, skipped = tradeable_picks(scores, md)
    assert tradeable == scores
    assert skipped == []


def weekly_bars(closes):
    """Thirteen Monday-to-Friday weeks of daily bars from one close per week."""
    from datetime import date, timedelta
    bars, monday, prev = [], date(2026, 8, 17), closes[0]
    for c in closes:
        for i in range(5):
            px = prev + (c - prev) * (i + 1) / 5
            bars.append({"date": (monday + timedelta(days=i)).isoformat(),
                         "open": prev if i == 0 else px, "close": px, "volume": 1e6})
        monday, prev = monday + timedelta(days=7), c
    return bars


def test_a_tape_like_the_one_that_got_through_is_caught_and_an_ordinary_one_is_not():
    aes = [14.83, 14.87, 14.91, 14.94, 14.95, 15.00, 14.83, 14.87, 14.91, 14.94, 15.02, 15.02, 15.03]
    hist = _aggregate_weekly(weekly_bars(aes))
    vol, _ = _risk_stats(hist)
    assert len(hist) == 13 and vol < PINNED_VOL_MAX
    assert pinned_price(market(AES={"realized_vol": vol, "history_weeks": len(hist)}), "AES") is not None

    quiet = [100.0, 101.2, 100.1, 101.9, 100.6, 102.4, 101.0, 102.9, 101.3, 103.1, 101.8, 103.6, 102.2]
    hist = _aggregate_weekly(weekly_bars(quiet))
    vol, _ = _risk_stats(hist)
    assert vol > PINNED_VOL_MAX
    assert pinned_price(market(Q={"realized_vol": vol, "history_weeks": len(hist)}), "Q") is None


def test_cecil_does_not_propose_a_pinned_name(monkeypatch):
    names = ["AAA", "BBB", "CCC", "DDD", "PIN"]
    monkeypatch.setattr(cecil, "scan_universe", lambda date=None: names)
    monkeypatch.setattr(cecil, "get_pe", lambda t, date=None: 6.0 if t == "PIN" else 12.0)
    stock = {t: {"realized_vol": 0.20, "max_drawdown": -0.05, "history_weeks": 13, "context": "steady"}
             for t in names}
    stock["PIN"].update(realized_vol=0.02, max_drawdown=0.0)
    md = {"weeklyReturns": {t: 0.0 for t in names}, "stockData": stock, "vix": "18"}
    out = cecil.analyze(md, "2026-11-13")
    picks = [s["ticker"] for s in out["stocks"]]
    assert "PIN" not in picks and len(picks) == 3
    assert [s["ticker"] for s in out["earnings_skipped"] if s.get("pinned")] == ["PIN"]

    monkeypatch.setattr(data_utils, "PINNED_VOL_MAX", 0.0)        # the screen off: he takes it first
    assert cecil.analyze(md, "2026-11-13")["stocks"][0]["ticker"] == "PIN"
