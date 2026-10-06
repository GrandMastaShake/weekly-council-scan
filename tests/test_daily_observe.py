"""The daily observation writer: session gate, shape, append-only.

No network. The witness gate and the document assembly are the two places a
wrong-but-confident file could originate, so they are tested directly rather
than through a fetch.

The date selection and the audit are tested against the feed's own history:
the instants below are when GitHub actually started each run, read from the
run logs. Between 2026-09-21 and 2026-10-02 the feed lost eight sessions and
every one of those runs was green.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

import daily_observe as do
from conftest import SCRIPTS


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    """conftest stubs yfinance; the witness probe is plain urllib and would
    get through. A test that reaches the provider fails here instead of
    quietly depending on the network."""
    def refuse(*a, **k):
        raise AssertionError("a test reached for the provider")
    monkeypatch.setattr(do, "_fetch_chart", refuse)


def bars(*tickers, close=100.0, volume=1_000_000):
    return {t: {"close": close, "volume": volume} for t in tickers}


def utc(stamp: str) -> datetime:
    """'2026-09-29 01:17' -> that instant, UTC."""
    return datetime.strptime(stamp, "%Y-%m-%d %H:%M").replace(
        tzinfo=timezone.utc)


def chart(*rows):
    """A provider chart payload from (UTC stamp, close) pairs, in the shape
    the v8 endpoint answers with."""
    return {"chart": {"error": None, "result": [{
        "meta": {"exchangeTimezoneName": "America/New_York"},
        "timestamp": [int(utc(stamp).timestamp()) for stamp, _ in rows],
        "indicators": {"quote": [{
            "close": [close for _, close in rows],
            "volume": [36666700] * len(rows)}]}}]}}


def listed(payload, start, end):
    return do.witness_rows(start, end, fetch=lambda *a: payload)


def weekdays(start: str, end: str) -> list:
    d, stop, out = date.fromisoformat(start), date.fromisoformat(end), []
    while d <= stop:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


# The panel as it stood on 2026-10-04, and the sessions the provider lists
# over the same span. Labor Day (2026-09-07) is in neither.
SESSIONS = [d for d in weekdays("2026-08-24", "2026-10-02")
            if d != "2026-09-07"]
ON_FILE = [d for d in SESSIONS
           if d <= "2026-09-23" and d != "2026-09-21"]
LOST = ["2026-09-21", "2026-09-24", "2026-09-25", "2026-09-28",
        "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]


def settled(days) -> dict:
    return {d: 100.0 for d in days}


# -- the session-witness gate ------------------------------------------------

def test_refuses_a_session_with_no_spy_bar():
    """The case this gate exists for: a session that has not settled."""
    with pytest.raises(do.SessionNotSettled) as exc:
        do.assert_session_settled("2026-09-10", bars("AAPL", "MSFT"),
                                  now=utc("2026-09-11 21:45"))
    assert "SPY" in str(exc.value)


def test_refuses_a_future_date():
    with pytest.raises(do.SessionNotSettled) as exc:
        do.assert_session_settled("2026-09-20", bars("SPY"),
                                  now=utc("2026-09-11 21:45"))
    assert "future" in str(exc.value)


def test_the_future_is_judged_in_eastern_not_utc():
    """01:17 UTC on Tuesday the 29th is Monday evening in New York. The 29th
    has not traded, whatever the runner's calendar says -- and it is the date
    the old default asked for."""
    with pytest.raises(do.SessionNotSettled) as exc:
        do.assert_session_closed("2026-09-29", now=utc("2026-09-29 01:17"))
    assert "future" in str(exc.value)
    do.assert_session_closed("2026-09-28", now=utc("2026-09-29 01:17"))


def test_accepts_a_settled_session():
    do.assert_session_settled("2026-09-10", bars("SPY", "AAPL"),
                              now=utc("2026-09-11 21:45"))


def test_today_is_acceptable_once_the_close_has_passed_and_spy_has_printed():
    do.assert_session_settled("2026-09-11", bars("SPY"),
                              now=utc("2026-09-11 21:45"))      # 17:45 ET


def test_today_is_refused_while_the_session_is_open_even_with_a_spy_bar():
    """The witness's blind spot. At 13:00 ET SPY has a bar dated today and it
    is the forming one; only the clock can refuse it."""
    with pytest.raises(do.SessionNotSettled) as exc:
        do.assert_session_settled("2026-09-11", bars("SPY"),
                                  now=utc("2026-09-11 17:00"))  # 13:00 ET
    assert "has not closed" in str(exc.value)


# -- the clock ---------------------------------------------------------------

@pytest.mark.parametrize("instant,wall", [
    ("2026-09-29 01:17", "2026-09-28 21:17"),   # EDT, UTC-4
    ("2026-12-15 01:17", "2026-12-14 20:17"),   # EST, UTC-5
    ("2026-03-08 06:59", "2026-03-08 01:59"),   # last minute of EST
    ("2026-03-08 07:00", "2026-03-08 03:00"),   # clocks spring forward
    ("2026-11-01 05:59", "2026-11-01 01:59"),   # last minute of EDT
    ("2026-11-01 06:00", "2026-11-01 01:00"),   # clocks fall back
])
def test_eastern_by_rule(instant, wall):
    assert do.eastern(utc(instant)).strftime("%Y-%m-%d %H:%M") == wall


def test_eastern_agrees_with_the_tz_database_where_there_is_one():
    """The rule is a transcription. Where a tz database exists, check the
    transcription against it hour by hour; Windows without the tzdata package
    has none, which is why there is a rule at all."""
    zoneinfo = pytest.importorskip("zoneinfo")
    try:
        new_york = zoneinfo.ZoneInfo("America/New_York")
    except zoneinfo.ZoneInfoNotFoundError:
        pytest.skip("no tz database on this machine")
    t = utc("2024-01-01 00:30")
    while t.year < 2031:
        assert do.eastern(t) == t.astimezone(new_york).replace(tzinfo=None), t
        t += timedelta(hours=1)


# -- default date ------------------------------------------------------------

@pytest.mark.parametrize("instant,expected", [
    # Started after UTC midnight, asked for the next UTC date, were refused,
    # and never looked at the session that had just closed.
    ("2026-09-22 00:17", "2026-09-21"),   # run 35671278521
    ("2026-09-25 00:00", "2026-09-24"),   # run 36075440792
    ("2026-09-29 01:17", "2026-09-28"),   # run 36507068968
    ("2026-09-30 00:46", "2026-09-29"),   # run 36651868769
    ("2026-10-01 00:50", "2026-09-30"),   # run 36798136115
    ("2026-10-02 01:05", "2026-10-01"),   # run 36949173537
    # A UTC Saturday already backed off to Friday. Must stay that way.
    ("2026-09-26 00:10", "2026-09-25"),   # run 36203730597
    ("2026-10-03 00:45", "2026-10-02"),   # run 37083274612
    # Started before UTC midnight and wrote. Must not change.
    ("2026-09-14 23:59", "2026-09-14"),   # run 34911226933
    ("2026-09-22 23:49", "2026-09-22"),   # run 35799192245
])
def test_default_date_is_the_session_that_closed_when_the_run_started(
        instant, expected):
    assert do.default_date(utc(instant)) == expected


@pytest.mark.parametrize("instant,expected", [
    ("2026-09-29 09:15", "2026-09-28"),   # the morning-after attempt, 05:15 ET
    ("2026-09-26 09:15", "2026-09-25"),   # ... on a Saturday, for Friday
    ("2026-09-29 13:45", "2026-09-28"),   # started late, after the open
    ("2026-09-29 18:00", "2026-09-28"),   # mid-session: never the forming day
    ("2026-09-29 19:59", "2026-09-28"),   # a minute before the close
    ("2026-09-29 20:00", "2026-09-29"),   # the close
    ("2026-09-27 23:00", "2026-09-25"),   # Sunday evening
    ("2026-09-28 12:00", "2026-09-25"),   # Monday before the open
    ("2026-11-03 20:30", "2026-11-02"),   # EST: 15:30, still open
    ("2026-11-03 21:45", "2026-11-03"),   # EST: 16:45, the evening cron on time
])
def test_default_date_follows_the_eastern_close(instant, expected):
    assert do.default_date(utc(instant)) == expected


# -- what the provider lists ---------------------------------------------------

def test_witness_rows_keep_a_null_close_as_a_session_not_yet_settled():
    """The payload behind both refused Fridays: the session's row is there,
    stamped at its open, volume and all, and the close is null."""
    payload = chart(("2026-09-23 13:30", 767.81),
                    ("2026-09-24 13:30", 767.18),
                    ("2026-09-25 13:30", None))
    assert listed(payload, "2026-09-15", "2026-09-25") == {
        "2026-09-23": 767.81, "2026-09-24": 767.18, "2026-09-25": None}


def test_witness_rows_take_the_live_close_over_the_sessions_own_null_row():
    """Until 20:00 ET the session's own row is null and the close rides on a
    second row stamped at the last trade. Either order, the price wins."""
    live = chart(("2026-09-24 13:30", 767.18),
                 ("2026-09-25 13:30", None),
                 ("2026-09-25 20:00", 771.35))
    assert listed(live, "2026-09-15", "2026-09-25")["2026-09-25"] == 771.35
    flipped = chart(("2026-09-25 20:00", 771.35),
                    ("2026-09-25 13:30", None))
    assert listed(flipped, "2026-09-15", "2026-09-25") == {
        "2026-09-25": 771.35}


def test_witness_rows_are_dated_in_eastern():
    """A row stamped 03:02 UTC on the 5th traded on the evening of the 4th."""
    payload = chart(("2026-10-05 03:02", 7776.75))
    assert listed(payload, "2026-10-01", "2026-10-05") == {
        "2026-10-04": 7776.75}


def test_witness_rows_drop_what_is_outside_the_range_asked_for():
    payload = chart(("2026-09-24 13:30", 767.18),
                    ("2026-09-25 13:30", 771.35),
                    ("2026-09-28 13:30", 770.00))
    assert listed(payload, "2026-09-25", "2026-09-25") == {
        "2026-09-25": 771.35}


def test_witness_rows_an_answer_with_no_rows_is_an_empty_listing():
    payload = {"chart": {"error": None, "result": [
        {"meta": {}, "indicators": {"quote": [{}]}}]}}
    assert listed(payload, "2026-09-05", "2026-09-07") == {}


@pytest.mark.parametrize("payload", [
    None,
    {},
    {"chart": {"result": None, "error": {"code": "Not Found"}}},
    {"chart": {"result": []}},
    {"chart": {"result": [None]}},
    {"chart": {"result": [{"timestamp": ["soon"], "indicators": {
        "quote": [{"close": [1.0]}]}}]}},
    "<html>Will be right back</html>",
])
def test_witness_rows_unknown_is_never_no_session(payload):
    assert listed(payload, "2026-09-15", "2026-09-25") is None


def test_explains_a_session_that_ended_and_has_not_settled():
    said = do.explain_no_witness(
        "2026-10-02", {"2026-10-01": 763.99, "2026-10-02": None})
    assert "NULL close" in said and "not settled" in said


def test_explains_a_date_that_is_not_a_session_and_names_the_latest_one():
    """What the six wrong-date refusals would have said: the day asked for
    has not traded, and the one before it is sitting there settled."""
    said = do.explain_no_witness(
        "2026-09-29", {"2026-09-25": 771.35, "2026-09-28": 770.00})
    assert "no session on 2026-09-29" in said
    assert "2026-09-28 (settled)" in said


def test_explains_a_provider_that_did_not_answer_without_guessing():
    said = do.explain_no_witness("2026-10-02", None)
    assert "Could not ask" in said
    assert "holiday" not in said and "NULL" not in said


def test_explains_a_bar_the_batch_dropped():
    said = do.explain_no_witness("2026-10-02", {"2026-10-02": 769.64})
    assert "transient" in said


# -- the audit -----------------------------------------------------------------

def test_audit_fails_on_the_feed_as_it_stood_on_2026_10_04():
    """Eight sessions gone, the newest file eleven days old, and until now
    nothing anywhere that said so."""
    level, lines = do.audit_feed(ON_FILE, settled(SESSIONS),
                                 now=utc("2026-10-05 03:07"))
    assert level == "FAIL"
    assert lines[0].startswith("FAIL: 8 settled session(s)")
    assert ", ".join(LOST) in lines[0]
    assert lines[-1] == ("  python scripts/daily_observe.py "
                         "--since 2026-09-21 --date 2026-10-02")


def test_audit_never_counts_a_holiday_as_a_hole():
    """The sessions are the provider's, not a calendar's. Labor Day has no
    file and no row, and is not missing."""
    level, lines = do.audit_feed(ON_FILE, settled(SESSIONS),
                                 now=utc("2026-10-05 03:07"))
    assert "2026-09-07" not in "\n".join(lines)
    through_the_18th = [d for d in SESSIONS if d <= "2026-09-18"]
    level, lines = do.audit_feed(through_the_18th, settled(through_the_18th),
                                 now=utc("2026-09-19 09:15"))
    assert level == "OK", lines


def test_audit_fails_on_a_hole_behind_a_fresh_head():
    """Once a run writes today's session the newest file is current again,
    and a check that looks only at the newest file goes quiet with the hole
    still there."""
    have = ON_FILE + ["2026-10-02"]
    level, lines = do.audit_feed(have, settled(SESSIONS),
                                 now=utc("2026-10-03 09:15"))
    assert level == "FAIL"
    assert "2026-10-02" not in lines[0] and "2026-10-01" in lines[0]


def test_audit_names_a_single_date_run_for_a_single_hole():
    """One session is not a range. A --date run also fetches the rates, vol,
    commodity and fx blocks, which the ranged bootstrap does not."""
    have = [d for d in SESSIONS if d != "2026-09-30"]
    level, lines = do.audit_feed(have, settled(SESSIONS),
                                 now=utc("2026-10-03 09:15"))
    assert level == "FAIL"
    assert lines[-1] == "  python scripts/daily_observe.py --date 2026-09-30"


def test_audit_passes_a_complete_panel():
    level, lines = do.audit_feed(SESSIONS, settled(SESSIONS),
                                 now=utc("2026-10-03 09:15"))
    assert level == "OK"
    assert lines == ["OK: daily feed complete -- 29 settled session(s) from "
                     "2026-08-24 through 2026-10-02, each with a file."]


def test_audit_warns_when_only_the_newest_settled_session_is_unwritten():
    """One attempt missed and the next has not run. Worth a line, not a red
    run: the morning attempt exists for exactly this."""
    level, lines = do.audit_feed(SESSIONS[:-1], settled(SESSIONS),
                                 now=utc("2026-10-03 03:00"))
    assert level == "WARN"
    assert lines[0].startswith("WARN: 2026-10-02 is settled")


def test_audit_treats_a_null_close_as_pending_not_missing():
    """The normal state of an evening run that lands after 20:00 ET."""
    rows = settled(SESSIONS[:-1])
    rows["2026-10-02"] = None
    level, lines = do.audit_feed(SESSIONS[:-1], rows,
                                 now=utc("2026-10-03 00:45"))
    assert level == "OK"
    assert lines[1].startswith("PENDING: 2026-10-02")


def test_audit_does_not_expect_a_session_that_is_still_open():
    """Monday 14:00 ET: the provider already lists today, with a price."""
    rows = settled(SESSIONS + ["2026-10-05"])
    level, lines = do.audit_feed(SESSIONS, rows, now=utc("2026-10-05 18:00"))
    assert level == "OK", lines


def test_audit_without_the_witness_falls_back_to_the_weekday_calendar():
    level, lines = do.audit_feed(SESSIONS, None, now=utc("2026-10-06 00:30"))
    assert level == "WARN" and "unverified" in lines[0]   # one weekday behind
    level, lines = do.audit_feed(ON_FILE, None, now=utc("2026-10-05 03:07"))
    assert level == "FAIL"
    assert "7 weekdays behind" in lines[0]


def test_audit_distrusts_a_witness_that_confirms_nothing_on_file():
    """An answer listing no session the panel already holds was an answer to
    something else. It must not read as 'nothing is missing'."""
    level, lines = do.audit_feed(ON_FILE, {}, now=utc("2026-10-05 03:07"))
    assert level == "FAIL"
    level, lines = do.audit_feed(SESSIONS, {"2019-01-02": 250.0},
                                 now=utc("2026-10-03 09:15"))
    assert level == "WARN" and "unverified" in lines[0]


def test_audit_of_an_empty_panel_is_a_warning():
    assert do.audit_feed([], settled(SESSIONS))[0] == "WARN"


def test_panel_sessions_lists_base_files_only(tmp_path):
    d = tmp_path / "daily"
    d.mkdir()
    for name in ("2026-09-10.json", "2026-09-09.json",
                 "2026-09-10.corrected.json", "notes.json", "README.md"):
        (d / name).write_text("{}\n", encoding="utf-8", newline="\n")
    assert do.panel_sessions(str(d)) == ["2026-09-09", "2026-09-10"]
    assert do.panel_sessions(str(tmp_path / "absent")) == []


# -- the run, end to end -------------------------------------------------------

@pytest.fixture
def at(monkeypatch):
    """Pin the script's clock to a UTC instant."""
    def pin(stamp: str):
        monkeypatch.setattr(do, "_utcnow", lambda: utc(stamp))
    return pin


def no_fetch(*a, **k):
    raise AssertionError("fetched when the answer needed no fetch")


def test_a_late_run_observes_the_session_that_closed(
        tmp_path, monkeypatch, at):
    """Run 36507068968 again, 01:17 UTC on Tuesday, with a provider that has
    Monday's bar. It asked for Tuesday."""
    asked = []

    def fetch(tickers, as_of):
        asked.append(as_of)
        return {"bars": bars("SPY", "AAPL"), "missing": []}

    at("2026-09-29 01:17")
    monkeypatch.setattr(do, "fetch_session_bars", fetch)
    assert do.main(["--out", str(tmp_path), "--no-special"]) == 0
    assert asked == ["2026-09-28"]
    assert (tmp_path / "daily" / "2026-09-28.json").is_file()


def test_an_unsettled_session_is_refused_and_the_refusal_says_why(
        tmp_path, monkeypatch, at, capsys):
    """Run 37083274612 again: 00:45 UTC on Saturday, rows for the whole
    window and none for Friday."""
    at("2026-10-03 00:45")
    monkeypatch.setattr(do, "fetch_session_bars", lambda tickers, as_of: {
        "bars": {}, "missing": [{"ticker": t, "reason": "no bar dated " + as_of}
                                for t in tickers]})
    monkeypatch.setattr(do, "witness_rows", lambda start, end, fetch=None: {
        "2026-10-01": 763.99, "2026-10-02": None})
    assert do.main(["--out", str(tmp_path), "--no-special"]) == 2
    out = capsys.readouterr().out
    assert "Observing 2026-10-02" in out
    assert "REFUSED: No SPY bar dated 2026-10-02" in out
    assert "NULL close" in out
    assert not (tmp_path / "daily").exists()


def test_the_morning_after_attempt_writes_what_the_evening_one_could_not(
        tmp_path, monkeypatch, at):
    at("2026-10-03 09:15")                       # Saturday, 05:15 ET
    monkeypatch.setattr(do, "fetch_session_bars", lambda tickers, as_of: {
        "bars": bars("SPY", "AAPL"), "missing": []})
    assert do.main(["--out", str(tmp_path), "--no-special"]) == 0
    doc = json.loads((tmp_path / "daily" / "2026-10-02.json").read_text(
        encoding="utf-8"))
    assert doc["as_of"] == "2026-10-02" and "SPY" in doc["series"]


def test_a_session_already_on_file_is_declined_before_any_fetch(
        tmp_path, monkeypatch, at, capsys):
    """The second attempt of the day, when the first one wrote."""
    (tmp_path / "daily").mkdir()
    (tmp_path / "daily" / "2026-10-02.json").write_text(
        "{}\n", encoding="utf-8", newline="\n")
    at("2026-10-03 09:15")
    monkeypatch.setattr(do, "fetch_session_bars", no_fetch)
    assert do.main(["--out", str(tmp_path)]) == 2
    assert "already exists" in capsys.readouterr().out


def test_an_open_session_named_by_hand_is_refused_before_any_fetch(
        tmp_path, monkeypatch, at, capsys):
    at("2026-10-05 18:00")                       # Monday, 14:00 ET
    monkeypatch.setattr(do, "fetch_session_bars", no_fetch)
    assert do.main(["--out", str(tmp_path), "--date", "2026-10-05"]) == 2
    assert "has not closed" in capsys.readouterr().out


def test_bootstrap_stops_at_the_last_close_and_skips_what_is_on_file(
        tmp_path, monkeypatch, at, capsys):
    """A range run mid-session must not pick up the forming day, whatever the
    provider hands back, and must not touch a session already committed."""
    asked = []

    def ranged(tickers, start, end):
        asked.append((start, end))
        return {"2026-10-01": bars("SPY"), "2026-10-02": bars("SPY"),
                "2026-10-05": bars("SPY")}

    (tmp_path / "daily").mkdir()
    (tmp_path / "daily" / "2026-10-01.json").write_text(
        "{}\n", encoding="utf-8", newline="\n")
    at("2026-10-05 18:00")                       # Monday, 14:00 ET
    monkeypatch.setattr(do, "fetch_session_range", ranged)
    assert do.main(["--out", str(tmp_path), "--since", "2026-09-30",
                    "--date", "2026-10-05"]) == 0
    assert asked == [("2026-09-30", "2026-10-02")]
    assert not (tmp_path / "daily" / "2026-10-05.json").exists()
    assert (tmp_path / "daily" / "2026-10-01.json").read_text(
        encoding="utf-8") == "{}\n", "an existing file was rewritten"
    assert (tmp_path / "daily" / "2026-10-02.json").is_file()
    assert "2026-10-01: exists, skipped" in capsys.readouterr().out


def test_bootstrap_dry_run_writes_nothing_and_says_what_it_would_do(
        tmp_path, monkeypatch, at, capsys):
    """The preview of a recovery has to show which sessions are new and which
    are already committed and will be left alone."""
    d = tmp_path / "daily"
    d.mkdir()
    for day in ("2026-09-22", "2026-09-23"):
        (d / (day + ".json")).write_text("{}\n", encoding="utf-8",
                                         newline="\n")
    at("2026-10-05 03:07")
    monkeypatch.setattr(do, "fetch_session_range", lambda tickers, start, end: {
        day: bars("SPY") for day in LOST + ["2026-09-22", "2026-09-23"]})
    assert do.main(["--out", str(tmp_path), "--since", "2026-09-21",
                    "--date", "2026-10-02", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "2026-09-22: exists, would be skipped" in out
    assert "A real run would write 8 session file(s) and skip 2" in out
    assert sorted(p.name for p in d.iterdir()) == ["2026-09-22.json",
                                                   "2026-09-23.json"]


def test_bootstrap_files_carry_the_same_fetched_at(tmp_path, monkeypatch):
    ticks = iter(utc("2026-10-05 03:07") + timedelta(seconds=n)
                 for n in range(100))
    monkeypatch.setattr(do, "_utcnow", lambda: next(ticks))
    monkeypatch.setattr(do, "fetch_session_range", lambda tickers, start, end: {
        d: bars("SPY") for d in LOST})
    assert do.main(["--out", str(tmp_path), "--since", "2026-09-21",
                    "--date", "2026-10-02"]) == 0
    stamps = {json.loads(p.read_text(encoding="utf-8"))["fetched_at"]
              for p in (tmp_path / "daily").glob("*.json")}
    assert len(list((tmp_path / "daily").glob("*.json"))) == 8
    assert len(stamps) == 1, stamps


def test_audit_mode_exits_nonzero_on_a_hole_and_writes_nothing(
        tmp_path, monkeypatch, at, capsys):
    d = tmp_path / "daily"
    d.mkdir()
    for day in ON_FILE:
        (d / (day + ".json")).write_text("{}\n", encoding="utf-8",
                                         newline="\n")
    at("2026-10-05 03:07")
    monkeypatch.setattr(do, "fetch_session_bars", no_fetch)
    monkeypatch.setattr(do, "witness_rows",
                        lambda start, end, fetch=None: settled(SESSIONS))
    assert do.main(["--audit", "--out", str(tmp_path)]) == 1
    assert "FAIL: 8 settled session(s)" in capsys.readouterr().out
    assert len(list(d.iterdir())) == len(ON_FILE)

    for day in LOST:
        (d / (day + ".json")).write_text("{}\n", encoding="utf-8",
                                         newline="\n")
    assert do.main(["--audit", "--out", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("OK: daily feed complete")


# -- the offline warning (truth_check --feed) ----------------------------------

def daily_panel(tmp_path, days):
    for day in days:
        do.write_document(
            do.build_document(day, {"bars": bars("SPY"), "missing": []}, None),
            str(tmp_path / "data"))
    return tmp_path


def truth_feed(repo, today: str):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "truth_check.py"), "--repo", str(repo),
         "--feed", "--today", today], capture_output=True, text=True)


def test_feed_gate_warns_that_the_daily_feed_has_stopped(tmp_path):
    """Every file valid, the newest eleven days old: the gate said OK. It
    has no network, so it warns rather than fails, and it must not stop a
    Monday -- but it no longer says nothing."""
    r = truth_feed(daily_panel(tmp_path, ON_FILE), "2026-10-04")
    assert ("WARN: feed: data/daily has stopped being written -- newest "
            "file 2026-09-23, 7 weekdays behind 2026-10-02") in r.stdout
    assert r.returncode == 0, r.stdout


def test_feed_gate_is_quiet_about_a_daily_feed_that_is_keeping_up(tmp_path):
    r = truth_feed(daily_panel(tmp_path, SESSIONS), "2026-10-04")
    assert "OK: feed: data/daily is current through 2026-10-02" in r.stdout
    assert "WARN" not in r.stdout


@pytest.mark.parametrize("days,today", [
    # the evening attempt was refused and the morning one has not run
    (SESSIONS[:-1], "2026-10-03"),
    # the Tuesday after Labor Day: Monday has no file and never will
    ([d for d in SESSIONS if d <= "2026-09-04"], "2026-09-08"),
])
def test_feed_gate_does_not_warn_over_one_weekday(tmp_path, days, today):
    r = truth_feed(daily_panel(tmp_path, days), today)
    assert "WARN" not in r.stdout, r.stdout


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


def test_fetched_at_is_a_utc_second_stamp():
    doc = do.build_document("2026-09-10", {"bars": bars("SPY"), "missing": []},
                            None)
    datetime.strptime(doc["fetched_at"], "%Y-%m-%dT%H:%M:%SZ")


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
    with 2 usable constituents, so the floor is pinned at the documented feed:
    321 until 2026-09-21, then 320 (EA, HES, EQR and AVB out; VMRK, BTC and
    GLD in)."""
    u = do.observation_universe()
    assert len(u) >= 320, (
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


def test_observation_universe_covers_the_whole_analysis_set():
    """Every scored name must have a daily bar, or a basket computes over
    survivors -- the denominator-honesty failure, one layer up."""
    from scan_pipeline.config.tickers import FOCUS_TICKERS
    u = set(do.observation_universe())
    missing = sorted(set(FOCUS_TICKERS) - u)
    assert not missing, "focus names absent from the daily feed: " + str(missing)


def test_observation_universe_is_the_weekly_writers_set(monkeypatch):
    """One definition of the feed for both writers.

    Each used to spell the union out for itself. From 2026-09-21 this one had
    the Council watchlist and the weekly one did not, so BTC and GLD were in
    the daily files and in no weekly file. It is one function now, and a name
    added to the feed reaches both.
    """
    from scan_pipeline import snapshot
    assert do.observation_universe() == snapshot.equity_universe()
    assert {"BTC", "GLD"} <= set(do.observation_universe())

    monkeypatch.setattr(snapshot, "PRICE_FEED_UNIVERSE",
                        list(snapshot.PRICE_FEED_UNIVERSE) + ["JOINED_LATER"])
    assert "JOINED_LATER" in do.observation_universe()
    assert do.observation_universe() == snapshot.equity_universe()


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
