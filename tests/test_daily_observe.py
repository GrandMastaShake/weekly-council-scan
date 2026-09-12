"""The daily observation writer: session gate, shape, append-only.

No network. The witness gate and the document assembly are the two places a
wrong-but-confident file could originate, so they are tested directly rather
than through a fetch.
"""
from __future__ import annotations

import json
from datetime import date

import pytest

import daily_observe as do


def bars(*tickers, close=100.0, volume=1_000_000):
    return {t: {"close": close, "volume": volume} for t in tickers}


# -- the session-witness gate ------------------------------------------------

def test_refuses_a_session_with_no_spy_bar():
    """The case this gate exists for: a session that has not settled."""
    with pytest.raises(do.SessionNotSettled) as exc:
        do.assert_session_settled("2026-09-10", bars("AAPL", "MSFT"),
                                  today=date(2026, 9, 11))
    assert "SPY" in str(exc.value)


def test_refuses_a_future_date():
    with pytest.raises(do.SessionNotSettled) as exc:
        do.assert_session_settled("2026-09-20", bars("SPY"),
                                  today=date(2026, 9, 11))
    assert "future" in str(exc.value)


def test_accepts_a_settled_session():
    do.assert_session_settled("2026-09-10", bars("SPY", "AAPL"),
                              today=date(2026, 9, 11))


def test_today_is_acceptable_once_spy_has_printed():
    """The gate is about the bar existing, not about the calendar."""
    do.assert_session_settled("2026-09-11", bars("SPY"),
                              today=date(2026, 9, 11))


# -- default date ------------------------------------------------------------

@pytest.mark.parametrize("given,expected", [
    (date(2026, 9, 11), "2026-09-11"),   # Friday
    (date(2026, 9, 12), "2026-09-11"),   # Saturday -> Friday
    (date(2026, 9, 13), "2026-09-11"),   # Sunday   -> Friday
    (date(2026, 9, 14), "2026-09-14"),   # Monday
])
def test_default_date_backs_off_weekends(given, expected):
    assert do.default_date(given) == expected


# -- document shape ----------------------------------------------------------

def test_document_carries_the_cadence_discriminator():
    doc = do.build_document("2026-09-10", {"bars": bars("SPY"), "missing": []},
                            None)
    assert doc["cadence"] == "daily"
    assert doc["source"] == "yahoo-daily"
    assert doc["as_of"] == "2026-09-10"
    assert doc["session"] == "close"


def test_missing_is_present_even_when_empty_and_never_omitted():
    doc = do.build_document("2026-09-10", {"bars": bars("SPY"), "missing": []},
                            {"rates": {}, "vol": {}, "commodities": {},
                             "fx": {}, "missing": []})
    assert doc["missing"] == []
    assert "missing" in doc


def test_missing_merges_series_and_special_failures_deduped_and_sorted():
    doc = do.build_document(
        "2026-09-10",
        {"bars": bars("SPY"), "missing": [
            {"ticker": "ZZZ", "reason": "no bar"},
            {"ticker": "AAA", "reason": "no bar"},
            {"ticker": "AAA", "reason": "no bar"},   # duplicate
        ]},
        {"rates": {}, "vol": {}, "commodities": {}, "fx": {},
         "missing": [{"ticker": "VIX", "reason": "fetch failed"}]},
    )
    got = [(m["ticker"], m["reason"]) for m in doc["missing"]]
    assert got == [("AAA", "no bar"), ("VIX", "fetch failed"), ("ZZZ", "no bar")]


def test_no_special_records_why_the_blocks_are_empty():
    """An empty block must never be silently empty -- that is the ambiguity
    the `missing` rule exists to remove."""
    doc = do.build_document("2026-09-10", {"bars": bars("SPY"), "missing": []},
                            None)
    reasons = [m["reason"] for m in doc["missing"] if m["ticker"] == "*"]
    assert reasons and "no-special" in reasons[0]


def test_volume_is_never_invented():
    doc = do.build_document(
        "2026-09-10",
        {"bars": {"SPY": {"close": 100.0, "volume": None}}, "missing": []},
        None)
    assert doc["series"]["SPY"]["volume"] is None


# -- append-only -------------------------------------------------------------

def test_refuses_to_overwrite_an_existing_file(tmp_path):
    doc = do.build_document("2026-09-10", {"bars": bars("SPY"), "missing": []},
                            None)
    do.write_document(doc, str(tmp_path))
    with pytest.raises(FileExistsError) as exc:
        do.write_document(doc, str(tmp_path))
    assert "corrected.json" in str(exc.value)


def test_force_overwrites(tmp_path):
    doc = do.build_document("2026-09-10", {"bars": bars("SPY"), "missing": []},
                            None)
    do.write_document(doc, str(tmp_path))
    do.write_document(doc, str(tmp_path), force=True)


def test_written_file_is_ascii_and_lf(tmp_path):
    """Byte-stability: a content hash must match between Windows and CI."""
    doc = do.build_document("2026-09-10", {"bars": bars("SPY"), "missing": []},
                            None)
    path = do.write_document(doc, str(tmp_path))
    raw = open(path, "rb").read()
    raw.decode("ascii")                      # raises if a non-ASCII byte got in
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")
    assert json.loads(raw.decode("ascii"))["as_of"] == "2026-09-10"


def test_lands_under_daily_not_weekly(tmp_path):
    doc = do.build_document("2026-09-10", {"bars": bars("SPY"), "missing": []},
                            None)
    path = do.write_document(doc, str(tmp_path))
    assert (tmp_path / "daily" / "2026-09-10.json").is_file()
    assert not (tmp_path / "weekly").exists()
    assert path.endswith("2026-09-10.json")


# -- universe ----------------------------------------------------------------

def test_observation_universe_is_not_shrunk_to_a_focus_set():
    """STOCK_UNIVERSE alone is 277 and covers 66 of the 110-name watchlist.
    The first build of this script used it and left Communication Services
    with 2 usable constituents, so the floor is pinned at the documented 321."""
    u = do.observation_universe()
    assert len(u) >= 321, (
        "daily feed is narrower than the live weekly panel: "
        + str(len(u)) + " tickers")
    assert "SPY" in u and "XLK" in u
    assert u == sorted(set(u)), "universe must be sorted and deduped"


def test_observation_universe_includes_the_backfilled_names():
    from scan_pipeline.config.tickers import BACKFILL_44_TICKERS
    u = set(do.observation_universe())
    assert set(BACKFILL_44_TICKERS) <= u, (
        "the 44 backfilled names are in the weekly panel; omitting them here "
        "makes the daily feed narrower than the weekly one")


def test_observation_universe_follows_a_wider_weekly_panel(tmp_path):
    """Self-healing: a panel that grows drags the daily feed with it."""
    weekly = tmp_path / "weekly"
    weekly.mkdir()
    (weekly / "2026-09-04.json").write_text(
        json.dumps({"series": {"BRAND_NEW_TICKER": {"close": 1.0,
                                                    "volume": 1}}}),
        encoding="utf-8", newline="\n")
    assert "BRAND_NEW_TICKER" in do.observation_universe(str(weekly))


def test_observation_universe_ignores_corrections_when_picking_newest(tmp_path):
    weekly = tmp_path / "weekly"
    weekly.mkdir()
    (weekly / "2026-09-04.json").write_text(
        json.dumps({"series": {"FROM_BASE": {"close": 1.0, "volume": 1}}}),
        encoding="utf-8", newline="\n")
    (weekly / "2026-09-04.corrected.json").write_text(
        json.dumps({"series": {"FROM_CORRECTION": {"close": 1.0,
                                                   "volume": 1}}}),
        encoding="utf-8", newline="\n")
    u = do.observation_universe(str(weekly))
    assert "FROM_BASE" in u
