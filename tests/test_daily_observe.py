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
from conftest import ROOT, SCRIPTS


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
    """The provider's roll is over and the session has no file. Worth a
    line, not a red run. Until 2026-10-07 this was said from the moment the
    witness settled; see the next test for why it waits now."""
    level, lines = do.audit_feed(SESSIONS[:-1], settled(SESSIONS),
                                 now=utc("2026-10-03 06:00"))    # 02:00 ET
    assert level == "WARN"
    assert lines[0].startswith("WARN: 2026-10-02 is settled")


def test_audit_calls_a_session_the_roll_may_not_have_reached_pending():
    """The witness settles early in the provider's roll. An attempt that
    finds SPY posted and other names not declines, by design, and the audit
    that runs after it used to read the same state as an attempt that
    missed. It is the session waiting for the morning, not a hole and not a
    warning: 01:01 UTC is when run 37554944269 found 2026-10-06 that way."""
    level, lines = do.audit_feed(SESSIONS[:-1], settled(SESSIONS),
                                 now=utc("2026-10-03 01:01"))
    assert level == "OK"
    assert lines[0] == ("OK: daily feed complete -- 28 settled session(s) "
                        "from 2026-08-24 through 2026-10-01, each with a "
                        "file.")
    assert lines[1].startswith(
        "PENDING: 2026-10-02 has closed, SPY has settled")
    assert "02:00 US/Eastern on 2026-10-03" in lines[1]
    assert len(lines) == 2


def test_audit_still_fails_on_a_hole_while_the_newest_session_waits():
    """Pending is for the newest session alone. One behind it with no file
    is a hole at any hour."""
    have = [d for d in SESSIONS[:-1] if d != "2026-09-30"]
    level, lines = do.audit_feed(have, settled(SESSIONS),
                                 now=utc("2026-10-03 01:01"))
    assert level == "FAIL"
    assert "2026-09-30, 2026-10-02" in lines[0]


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


# -- the half-posted session --------------------------------------------------
#
# Run 37554944269 wrote 2026-10-06.json at 01:01 UTC on the 7th with SPY
# settled and 59 names not yet posted. The panel it was written into is read
# here as committed, and never written to.

PANEL = ROOT / "data" / "daily"

# The 59, as that file's `missing` lists them. Kept here because the file is
# the owner's to repair: withdrawn or made whole, it stops saying this.
HALF_POSTED = (
    "ABBV ABNB ANET BFLY BTC CARR CEG COIN COLD CRSP CRWD CVNA DDOG DOW FIVE "
    "GEHC GEV GLPI GOOG HIMS HLT HPE INVH IONQ IQV KVUE META MP MRNA NOW NTLA "
    "OKLO OTIS PANW PLTR PSX PYPL QBTS QUBT RBLX RDDT RGTI RKLB ROKU SIDU "
    "SOFI SOLV SOUN SPCX SPOT SYM UPST VEEV VICI VST XLC XLRE ZS ZTS").split()


def committed(day: str) -> dict:
    return json.loads((PANEL / (day + ".json")).read_text(encoding="utf-8"))


def asked_for(doc: dict) -> list:
    """What the run that wrote a file asked the provider for: a name is in
    `series` or it is in `missing`, never neither."""
    return sorted(set(doc["series"]) | {m["ticker"] for m in doc["missing"]})


def fetched(doc: dict) -> datetime:
    return datetime.strptime(doc["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc)


def replay(day: str, held: dict | None = None) -> list:
    """Put a committed file back through the gate: its own names, its own
    bars and its own clock, against the sessions that stand before it.

    Those are read from the panel on disk, or from `held` ({session:
    names}) when the test has to say which sessions count. Not quite what
    the run that wrote the file met: 2026-09-22, 09-23 and 10-05 were
    written while sessions before them were still lost, and are compared
    here with the ones recovered since."""
    doc = committed(day)
    if held is None:
        sessions, names = do.recent_bars(str(PANEL), day)
    else:
        sessions, names = do.recent_bars(str(PANEL / "none"), day, held)
    return do.assert_session_posted(day, asked_for(doc), doc["series"],
                                    sessions, names, now=fetched(doc))


def on_file(root, day: str, *tickers) -> None:
    do.write_document(
        do.build_document(day, {"bars": bars(*tickers), "missing": []}, None),
        str(root))


def short_by(*gone):
    """A fetch that came back without some names, the way the batch and the
    one-by-one retry both did that night."""
    def fetch(tickers, as_of):
        return {"bars": bars(*[t for t in tickers if t not in gone]),
                "missing": [{"ticker": t, "reason": "no bar dated " + as_of}
                            for t in tickers if t in gone]}
    return fetch


def no_special(*a, **k):
    raise AssertionError("fetched the instruments for a file it will not "
                         "write")


@pytest.fixture
def universe(monkeypatch):
    """A feed of five names, so a panel fits in a test: what the run fetches
    and what it is held to, both. Not the real feed's, so that a name
    leaving tickers.py one day cannot change what these tests count."""
    names = ["SPY", "AAPL", "MSFT", "META", "BTC"]
    monkeypatch.setattr(do, "observation_universe", lambda weekly=None: names)
    monkeypatch.setattr(do, "equity_universe", lambda: list(names))
    return names


def test_no_session_on_file_before_2026_10_06_would_have_been_refused():
    """The bound is read off the panel, and this is the reading. Each of the
    30 sessions before 2026-10-06, replayed at the minute it was fetched,
    against the sessions before it: the evening files hold every expected
    name, and the files cut days later are short by one at most. That one is
    AVB, whose last bar the provider kept is 2026-08-24, for the five
    sessions that bar stays in view.

    From 2026-08-24 through 2026-10-05 and no further either way, each
    held against the others of that span alone. Those files are append-only
    and this cannot change. A later file is the gate's to judge when it is
    written, not this test's afterwards: the suite runs in the daily job
    before a session is committed, and a pin on files not yet written would
    stop that job over a file already on main. An earlier one, bootstrapped
    some day, would bring names the first of these sessions never held."""
    days = [d for d in do.panel_sessions(str(PANEL))
            if "2026-08-24" <= d <= "2026-10-05"]
    assert len(days) == 30
    held = {day: set(committed(day)["series"]) for day in days}
    gone = {day: replay(day, held) for day in days}

    assert {day: names for day, names in gone.items() if names} == {
        day: ["AVB"] for day in ("2026-08-25", "2026-08-26", "2026-08-27",
                                 "2026-08-28", "2026-08-31")}
    assert max(len(names) for names in gone.values()) < do.MAX_GONE
    in_the_evening = [day for day in days
                      if do.roll_may_be_running(day, fetched(committed(day)))]
    assert len(in_the_evening) == 9, in_the_evening
    assert not any(gone[day] for day in in_the_evening)


def test_the_half_posted_fetch_of_2026_10_06_is_refused():
    """What run 37554944269 had in hand at 01:01 UTC on the 7th: the 336
    names of the session before, 59 of them without a bar. Built from
    2026-10-05.json and the list above, so it holds whatever becomes of
    2026-10-06.json."""
    before = committed("2026-10-05")
    assert set(HALF_POSTED) < set(before["series"]) and len(HALF_POSTED) == 59
    names = sorted(before["series"])
    posted = {t: before["series"][t] for t in names if t not in HALF_POSTED}
    sessions, held = do.recent_bars(str(PANEL), "2026-10-06")
    assert sessions == ["2026-09-29", "2026-09-30", "2026-10-01",
                        "2026-10-02", "2026-10-05"]

    with pytest.raises(do.SessionHalfPosted) as exc:
        do.assert_session_posted("2026-10-06", names, posted, sessions, held,
                                 now=utc("2026-10-07 01:01"))
    assert exc.value.gone == sorted(HALF_POSTED)
    assert len(exc.value.gone) > do.MAX_GONE
    said = str(exc.value)
    assert said.startswith(
        "59 names with a bar in the last 5 sessions on file (2026-09-29 .. "
        "2026-10-05) have none dated 2026-10-06: ABBV, ABNB, ANET, BFLY, BTC, "
        "CARR, CEG, COIN, ... and 51 more. SPY has settled and they have "
        "not.")
    assert "until 02:00 US/Eastern on 2026-10-07" in said
    assert "(it is 21:01 on 2026-10-06)" in said
    assert "The next scheduled attempt writes the session." in said

    # ... and at any hour after, because 59 is no delisting.
    with pytest.raises(do.SessionHalfPosted) as exc:
        do.assert_session_posted("2026-10-06", names, posted, sessions, held,
                                 now=utc("2026-10-07 09:15"))
    assert "did not answer for part of the panel" in str(exc.value)
    assert "The next scheduled attempt" not in str(exc.value)


def test_2026_10_06_as_committed_is_the_file_the_gate_refuses():
    """The file itself, while it stands as that run left it: short by 59,
    and not edited. Whether it is withdrawn, written again or added to is
    the owner's decision, and this test must not be what stops it: the daily
    job runs the suite before it commits a session. So it reads the file
    only while it is still that run's, and the test above goes on holding
    the bound when it is not."""
    path = PANEL / "2026-10-06.json"
    if not path.is_file():
        pytest.skip("2026-10-06.json has been withdrawn")
    doc = committed("2026-10-06")
    if (doc.get("fetched_at") != "2026-10-07T01:01:44Z"
            or len(doc["series"]) != 277):
        pytest.skip("2026-10-06.json is no longer the file run 37554944269 "
                    "left")
    assert "SPY" in doc["series"]
    assert not set(HALF_POSTED) & set(doc["series"])
    with pytest.raises(do.SessionHalfPosted) as exc:
        replay("2026-10-06")
    assert exc.value.gone == sorted(HALF_POSTED)


def test_a_short_file_does_not_hide_the_same_names_the_next_night(
        tmp_path, monkeypatch):
    """Why a file is compared with five sessions and not with the one
    before it. The provider posts oldest listing first, so a roll caught at
    the same point two nights running is short of the same names, and the
    first night's file, which stays as written, holds none of them."""
    for day in ("2026-09-30", "2026-10-01", "2026-10-02", "2026-10-05"):
        on_file(tmp_path, day, "SPY", "AAPL", "META", "BTC")
    on_file(tmp_path, "2026-10-06", "SPY", "AAPL")           # the short one
    asked, tonight = ["SPY", "AAPL", "META", "BTC"], bars("SPY", "AAPL")
    daily = str(tmp_path / "daily")

    sessions, names = do.recent_bars(daily, "2026-10-07")
    assert sessions[0] == "2026-09-30" and sessions[-1] == "2026-10-06"
    with pytest.raises(do.SessionHalfPosted) as exc:
        do.assert_session_posted("2026-10-07", asked, tonight, sessions,
                                 names, now=utc("2026-10-08 01:01"))
    assert exc.value.gone == ["BTC", "META"]

    monkeypatch.setattr(do, "RECENT_SESSIONS", 1)
    sessions, names = do.recent_bars(daily, "2026-10-07")
    assert sessions == ["2026-10-06"]
    assert do.assert_session_posted("2026-10-07", asked, tonight, sessions,
                                    names, now=utc("2026-10-08 01:01")) == []


def test_recent_bars_are_the_five_sessions_before_and_no_later_one(tmp_path):
    days = weekdays("2026-09-21", "2026-10-02")              # ten sessions
    for n, day in enumerate(days):
        on_file(tmp_path, day, "SPY", "N" + str(n))
    sessions, names = do.recent_bars(str(tmp_path / "daily"), "2026-09-30")
    assert sessions == ["2026-09-23", "2026-09-24", "2026-09-25",
                        "2026-09-28", "2026-09-29"]
    assert names == {"SPY", "N2", "N3", "N4", "N5", "N6"}
    nothing = ([], set())
    assert do.recent_bars(str(tmp_path / "daily"), "2026-09-21") == nothing
    assert do.recent_bars(str(tmp_path / "absent"), "2026-09-30") == nothing


def test_recent_bars_look_past_a_file_that_holds_no_series(tmp_path):
    """A file that cannot say what it holds is not a session to compare
    with, and does not use up one of the five. truth_check --feed is what
    fails it. A correction is not a session either."""
    for day in weekdays("2026-09-21", "2026-09-29"):         # seven
        on_file(tmp_path, day, "SPY", "AAPL")
    d = tmp_path / "daily"
    (d / "2026-09-25.json").write_text("{}\n", encoding="utf-8", newline="\n")
    (d / "2026-09-28.json").write_text("not json", encoding="utf-8")
    (d / "2026-09-29.corrected.json").write_text(
        json.dumps({"series": {"FROM_A_CORRECTION": {}}}), encoding="utf-8")
    sessions, names = do.recent_bars(str(d), "2026-09-30")
    assert sessions == ["2026-09-21", "2026-09-22", "2026-09-23",
                        "2026-09-24", "2026-09-29"]
    assert names == {"SPY", "AAPL"}


def test_recent_bars_count_what_a_bootstrap_has_already_cut(tmp_path):
    """A range is one download. Each session of it is compared with the
    ones before it whether they are on disk yet or not, which in a dry run
    they never are."""
    on_file(tmp_path, "2026-09-30", "SPY", "ON_DISK")
    cut = {"2026-10-01": {"SPY", "CUT"}, "2026-10-05": {"SPY", "LATER"}}
    sessions, names = do.recent_bars(str(tmp_path / "daily"), "2026-10-02",
                                     cut)
    assert sessions == ["2026-09-30", "2026-10-01"]
    assert names == {"SPY", "ON_DISK", "CUT"}


@pytest.mark.parametrize("instant,running", [
    ("2026-10-06 21:45", True),     # the evening attempt, on time
    ("2026-10-07 01:01", True),     # run 37554944269
    ("2026-10-07 05:59", True),
    ("2026-10-07 06:00", False),    # 02:00 EDT
    ("2026-10-07 09:15", False),    # the morning attempt
])
def test_the_roll_is_given_ten_hours_from_the_close(instant, running):
    assert do.roll_may_be_running("2026-10-06", utc(instant)) is running


def test_the_roll_hour_is_eastern_in_winter_too():
    assert do.roll_ends("2026-12-15") == datetime(2026, 12, 16, 2, 0)
    assert do.roll_may_be_running("2026-12-15", utc("2026-12-16 06:59"))
    assert not do.roll_may_be_running("2026-12-15", utc("2026-12-16 07:00"))
    # Friday's roll is over on Saturday morning, not on Monday.
    assert not do.roll_may_be_running("2026-10-02", utc("2026-10-03 09:15"))


def test_the_morning_attempt_falls_after_the_roll_in_both_seasons():
    """The two numbers are in different files and depend on each other.
    Before ROLL_HOURS a name with no bar is waited for. If the morning
    attempt ran inside that time too, a name that had really stopped trading
    would be waited for by both attempts, and no session would be written
    until it left the feed. The evening attempt is inside it on purpose."""
    import yaml
    doc = yaml.safe_load((ROOT / ".github" / "workflows" /
                          "daily-observe.yml").read_text(encoding="utf-8"))
    # YAML 1.1 reads a bare `on` as the boolean True.
    schedule = (doc.get("on") or doc.get(True))["schedule"]
    evening, morning = sorted((s["cron"].split() for s in schedule),
                              key=lambda c: -int(c[1]))
    for session, next_day in (("2026-10-06", "2026-10-07"),      # EDT
                              ("2026-12-15", "2026-12-16")):     # EST
        at_night = utc("%s %02d:%02d" % (session, int(evening[1]),
                                         int(evening[0])))
        in_the_morning = utc("%s %02d:%02d" % (next_day, int(morning[1]),
                                               int(morning[0])))
        assert do.roll_may_be_running(session, at_night)
        assert not do.roll_may_be_running(session, in_the_morning), (
            "the morning attempt would wait for a name that is gone for good")
        # GitHub starts a schedule late and never early, so the margin only
        # grows. Two hours of it, so the next person to move the cron sees
        # this before the two meet.
        assert (do.eastern(in_the_morning) - do.roll_ends(session)
                >= timedelta(hours=2)), session


def test_one_name_gone_refuses_until_the_roll_is_over():
    """The roll's last names are the newest listings, the same ones every
    night. A bound that let one through would let that one through for
    good."""
    sessions, names = ["2026-10-05"], {"SPY", "AAPL", "BTC"}
    with pytest.raises(do.SessionHalfPosted) as exc:
        do.assert_session_posted("2026-10-06", ["SPY", "AAPL", "BTC"],
                                 bars("SPY", "AAPL"), sessions, names,
                                 now=utc("2026-10-07 01:30"))
    assert str(exc.value).startswith(
        "1 name with a bar in the session on file before it (2026-10-05) "
        "has none dated 2026-10-06: BTC. SPY has settled and it has not.")
    assert do.assert_session_posted("2026-10-06", ["SPY", "AAPL", "BTC"],
                                    bars("SPY", "AAPL"), sessions, names,
                                    now=utc("2026-10-07 09:15")) == ["BTC"]


def test_after_the_roll_a_few_names_gone_are_recorded_and_more_are_refused():
    gone_for_good = ["DEAD" + str(n) for n in range(do.MAX_GONE + 1)]
    names = {"SPY", *gone_for_good}
    asked = ["SPY"] + gone_for_good
    morning = utc("2026-10-07 09:15")
    assert do.assert_session_posted(
        "2026-10-06", asked[:-1], bars("SPY"), ["2026-10-05"], names,
        now=morning) == gone_for_good[:-1]
    with pytest.raises(do.SessionHalfPosted) as exc:
        do.assert_session_posted("2026-10-06", asked, bars("SPY"),
                                 ["2026-10-05"], names, now=morning)
    said = str(exc.value)
    assert "over by 02:00 US/Eastern on 2026-10-07" in said
    assert "accounts for " + str(do.MAX_GONE) + " names at most" in said
    # Days later it is the same answer: nothing about it was waiting.
    with pytest.raises(do.SessionHalfPosted):
        do.assert_session_posted("2026-10-06", asked, bars("SPY"),
                                 ["2026-10-05"], names,
                                 now=utc("2026-10-20 15:00"))


def test_a_name_that_left_the_feed_or_never_had_a_bar_is_not_waited_for():
    """AVB had a bar on file and is not among the names handed over (the
    feed's, waited_for). SPCX before its listing was asked for and never had
    one. Neither is gone."""
    names = {"SPY", "AAPL", "AVB"}
    assert do.assert_session_posted(
        "2026-10-06", ["SPY", "AAPL", "SPCX"], bars("SPY", "AAPL"),
        ["2026-10-05"], names, now=utc("2026-10-07 01:01")) == []


def test_with_no_earlier_session_there_is_nothing_to_refuse():
    """The first file of a panel. The witness is all that speaks for it, as
    it was for every file before this rule, and no second rule is made up
    for the one night that has nothing to be compared with."""
    assert do.assert_session_posted(
        "2026-08-24", ["SPY", "AAPL"], bars("SPY"), [], set(),
        now=utc("2026-08-25 01:01")) == []


def test_a_half_posted_session_is_refused_and_says_what_the_provider_lists(
        tmp_path, monkeypatch, at, capsys, universe):
    """Run 37554944269 again, with the gate. Nothing is written, the
    instruments are not fetched, and the exit is the clean one."""
    on_file(tmp_path, "2026-10-05", *universe)
    at("2026-10-07 01:01")
    monkeypatch.setattr(do, "fetch_session_bars", short_by("META", "BTC"))
    monkeypatch.setattr(do, "get_special_instruments", no_special)
    asked = []

    def listed(symbol, start, end, fetch=None):
        asked.append((symbol, start, end))
        return {"2026-10-05": 100.0, "2026-10-06": None}

    monkeypatch.setattr(do, "listed_rows", listed)
    assert do.main(["--out", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert "Observing 2026-10-06 over 5 tickers" in out
    assert ("REFUSED: 2 names with a bar in the session on file before it "
            "(2026-10-05) have none dated 2026-10-06: BTC, META.") in out
    assert ("  It lists 2026-10-06 for BTC and META as a session with a NULL "
            "close") in out
    assert asked == [("BTC", "2026-09-26", "2026-10-06"),
                     ("META", "2026-09-26", "2026-10-06")]
    assert "Wrote" not in out
    assert sorted(p.name for p in (tmp_path / "daily").iterdir()) == [
        "2026-10-05.json"]


def test_a_dry_run_reports_the_refusal_the_same_way(
        tmp_path, monkeypatch, at, capsys, universe):
    on_file(tmp_path, "2026-10-05", *universe)
    at("2026-10-07 01:01")
    monkeypatch.setattr(do, "fetch_session_bars", short_by("BTC"))
    monkeypatch.setattr(do, "get_special_instruments", no_special)
    monkeypatch.setattr(do, "listed_rows", lambda *a, **k: None)
    assert do.main(["--out", str(tmp_path), "--dry-run"]) == 2
    out = capsys.readouterr().out
    assert "REFUSED: 1 name with a bar in" in out
    assert "DRY RUN" not in out


def test_force_does_not_write_a_half_posted_fetch_over_a_whole_file(
        tmp_path, monkeypatch, at, capsys, universe):
    """--force is the key to the append-only guard and to nothing else.
    Here it would have traded five bars for three."""
    on_file(tmp_path, "2026-10-05", *universe)
    on_file(tmp_path, "2026-10-06", *universe)
    whole = (tmp_path / "daily" / "2026-10-06.json").read_bytes()
    at("2026-10-07 01:01")
    monkeypatch.setattr(do, "fetch_session_bars", short_by("META", "BTC"))
    monkeypatch.setattr(do, "listed_rows", lambda *a, **k: None)
    assert do.main(["--out", str(tmp_path), "--force", "--no-special"]) == 2
    assert "REFUSED: 2 names" in capsys.readouterr().out
    assert (tmp_path / "daily" / "2026-10-06.json").read_bytes() == whole


def test_force_never_trades_a_whole_file_for_a_shorter_one(
        tmp_path, monkeypatch, at, capsys, universe):
    """After the roll hour one name gone is no refusal, and until this was
    added --force then wrote the shorter fetch over the file: five series
    for four, exit 0. A committed bar is not given up by any flag."""
    on_file(tmp_path, "2026-10-05", *universe)
    on_file(tmp_path, "2026-10-06", *universe)
    whole = (tmp_path / "daily" / "2026-10-06.json").read_bytes()
    at("2026-10-07 09:15")
    monkeypatch.setattr(do, "fetch_session_bars", short_by("META"))
    for flags in (["--force"], ["--force", "--dry-run"]):
        assert do.main(["--out", str(tmp_path), "--no-special"] + flags) == 2
        out = capsys.readouterr().out
        assert ("REFUSED: --force would write 2026-10-06 again without 1 "
                "name the file on disk holds a bar for: META.") in out
        assert (tmp_path / "daily" / "2026-10-06.json").read_bytes() == whole


def test_force_still_mends_a_write_that_failed(
        tmp_path, monkeypatch, at, universe):
    """What --force is for. A write that died leaves a file that does not
    read, and that holds nothing to lose."""
    on_file(tmp_path, "2026-10-05", *universe)
    broken = tmp_path / "daily" / "2026-10-06.json"
    broken.write_text('{"as_of": "2026-10-06", "series": {"SPY": {"clo',
                      encoding="utf-8")
    at("2026-10-07 09:15")
    monkeypatch.setattr(do, "fetch_session_bars", short_by())
    assert do.main(["--out", str(tmp_path), "--no-special", "--force"]) == 0
    doc = json.loads(broken.read_text(encoding="utf-8"))
    assert sorted(doc["series"]) == sorted(universe)


def test_a_name_taken_out_of_the_feed_is_fetched_and_not_waited_for(
        tmp_path, monkeypatch, at, capsys):
    """The way out of a refusal that will not clear is to take the dead
    names out of PRICE_FEED_UNIVERSE, and it has to work that day. The run
    still fetches them: observation_universe adds whatever the newest weekly
    file holds, and that file is not replaced until Saturday. So the gate
    counts the feed's names and not the fetch's."""
    feed = ["SPY", "AAPL", "MSFT"]
    dead = ["DEAD" + str(n) for n in range(do.MAX_GONE + 1)]
    monkeypatch.setattr(do, "equity_universe", lambda: list(feed))
    weekly = tmp_path / "weekly"
    weekly.mkdir()
    (weekly / "2026-10-02.json").write_text(
        json.dumps({"series": bars(*feed, *dead)}), encoding="utf-8",
        newline="\n")
    on_file(tmp_path, "2026-10-05", *feed, *dead)
    at("2026-10-07 01:01")
    monkeypatch.setattr(do, "fetch_session_bars", short_by(*dead))
    assert do.observation_universe(str(weekly)) == sorted(feed + dead)
    assert do.waited_for(sorted(feed + dead)) == sorted(feed)

    assert do.main(["--out", str(tmp_path), "--no-special"]) == 0
    assert "Observing 2026-10-06 over 7 tickers" in capsys.readouterr().out
    doc = json.loads((tmp_path / "daily" / "2026-10-06.json").read_text(
        encoding="utf-8"))
    assert sorted(doc["series"]) == sorted(feed)
    assert {m["ticker"] for m in doc["missing"]} >= set(dead)

    # Still in the feed, the same four stop the run at any hour.
    monkeypatch.setattr(do, "equity_universe", lambda: feed + dead)
    for hour in ("2026-10-08 01:01", "2026-10-08 09:15"):
        at(hour)
        monkeypatch.setattr(do, "listed_rows", lambda *a, **k: None)
        assert do.main(["--out", str(tmp_path), "--no-special"]) == 2
    assert not (tmp_path / "daily" / "2026-10-07.json").exists()


def test_the_morning_attempt_writes_a_name_that_is_gone_into_missing(
        tmp_path, monkeypatch, at, capsys, universe):
    """The same fetch eight hours on. The roll is over, so a name with no
    bar has stopped trading or been renamed, and the file says so the way a
    daily file always has."""
    on_file(tmp_path, "2026-10-05", *universe)
    at("2026-10-07 09:15")
    monkeypatch.setattr(do, "fetch_session_bars", short_by("META"))
    assert do.main(["--out", str(tmp_path), "--no-special"]) == 0
    out = capsys.readouterr().out
    assert ("META had a bar in the session on file before it (2026-10-05) "
            "and none dated 2026-10-06.") in out
    doc = json.loads((tmp_path / "daily" / "2026-10-06.json").read_text(
        encoding="utf-8"))
    assert sorted(doc["series"]) == ["AAPL", "BTC", "MSFT", "SPY"]
    assert {"ticker": "META", "reason": "no bar dated 2026-10-06"} \
        in doc["missing"]


def test_the_morning_attempt_refuses_a_panel_short_by_more_than_the_bound(
        tmp_path, monkeypatch, at, capsys, universe):
    """Four of five without a bar at 05:15 in the morning is not four
    delistings. It is refused at every attempt, which leaves the session to
    the audit: that is the alarm, and this is not."""
    on_file(tmp_path, "2026-10-05", *universe)
    at("2026-10-07 09:15")
    monkeypatch.setattr(do, "fetch_session_bars",
                        short_by("AAPL", "MSFT", "META", "BTC"))
    monkeypatch.setattr(do, "get_special_instruments", no_special)
    monkeypatch.setattr(do, "listed_rows",
                        lambda symbol, start, end, fetch=None: {
                            "2026-10-05": 100.0, "2026-10-06": 101.0})
    assert do.main(["--out", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert "REFUSED: 4 names" in out
    assert "did not answer for part of the panel" in out
    assert ("Asked the provider about the first 3 of them. It lists a "
            "settled close on 2026-10-06 for AAPL, BTC and META") in out
    assert not (tmp_path / "daily" / "2026-10-06.json").exists()


def test_a_first_file_is_written_on_the_witness_alone_and_says_so(
        tmp_path, monkeypatch, at, capsys, universe):
    at("2026-10-07 01:01")
    monkeypatch.setattr(do, "fetch_session_bars", short_by("META", "BTC"))
    assert do.main(["--out", str(tmp_path), "--no-special"]) == 0
    assert "No earlier session on file to compare with" in \
        capsys.readouterr().out
    assert (tmp_path / "daily" / "2026-10-06.json").is_file()


def ranged(by_day):
    def fetch(tickers, start, end):
        return {day: bars(*names) for day, names in by_day.items()
                if start <= day <= end}
    return fetch


def test_a_bootstrap_leaves_a_half_posted_newest_session_for_a_later_run(
        tmp_path, monkeypatch, at, capsys, universe):
    """A recovery dispatched in the small hours. Its range ends at the last
    close, and that session comes out of the same half-posted download a
    single run would have read. The settled sessions are written, so the
    exit is 0 and the workflow commits them; the newest is left to the
    morning attempt, which also reads the rates the bootstrap does not."""
    on_file(tmp_path, "2026-10-01", *universe)
    at("2026-10-07 01:01")
    monkeypatch.setattr(do, "fetch_session_range", ranged({
        "2026-10-02": universe, "2026-10-05": universe,
        "2026-10-06": ["SPY", "AAPL", "MSFT"]}))
    monkeypatch.setattr(do, "listed_rows", lambda *a, **k: {
        "2026-10-06": None})
    assert do.main(["--out", str(tmp_path), "--since", "2026-10-02"]) == 0
    out = capsys.readouterr().out
    assert ("  2026-10-06: REFUSED: 2 names with a bar in the last 3 sessions "
            "on file (2026-10-01 .. 2026-10-05) have none dated 2026-10-06: "
            "BTC, META.") in out
    assert "NULL close" in out
    assert ("Wrote 2 session file(s), skipped 0 existing. 1 refused, for the "
            "reason given above.") in out
    assert sorted(p.name for p in (tmp_path / "daily").iterdir()) == [
        "2026-10-01.json", "2026-10-02.json", "2026-10-05.json"]


def test_a_bootstrap_dry_run_compares_with_sessions_it_has_not_written(
        tmp_path, monkeypatch, at, capsys, universe):
    """Nothing is on disk in a dry run, and the preview has to refuse what
    the real run would: the session before, in the same download, is what
    the newest one is short against."""
    at("2026-10-07 01:01")
    monkeypatch.setattr(do, "fetch_session_range", ranged({
        "2026-10-05": universe, "2026-10-06": ["SPY", "AAPL", "MSFT"]}))
    monkeypatch.setattr(do, "listed_rows", lambda *a, **k: None)
    assert do.main(["--out", str(tmp_path), "--since", "2026-10-05",
                    "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "  2026-10-05: 5 series, 1 missing (dry run)" in out
    assert "  2026-10-06: REFUSED: 2 names with a bar in the session on " \
           "file before it (2026-10-05)" in out
    assert ("A real run would write 1 session file(s) and skip 0 existing. "
            "1 would be refused, for the reason given above.") in out
    assert not (tmp_path / "daily").exists()


def test_a_bootstrap_that_declines_all_it_was_asked_for_exits_2(
        tmp_path, monkeypatch, at, capsys, universe):
    """Nothing written and something refused is a run that declined, and the
    workflow treats it as one: no gates, no commit, the audit."""
    on_file(tmp_path, "2026-10-05", *universe)
    at("2026-10-07 01:01")
    monkeypatch.setattr(do, "fetch_session_range", ranged({
        "2026-10-05": universe, "2026-10-06": ["SPY", "AAPL", "MSFT"]}))
    monkeypatch.setattr(do, "listed_rows", lambda *a, **k: None)
    assert do.main(["--out", str(tmp_path), "--since", "2026-10-05"]) == 2
    out = capsys.readouterr().out
    assert "2026-10-05: exists, skipped" in out
    assert "Wrote 0 session file(s), skipped 1 existing. 1 refused" in out


def test_a_bootstrap_days_later_records_a_gone_name_and_goes_on(
        tmp_path, monkeypatch, at, capsys, universe):
    """The 2026-09-12 bootstrap met this: AVB's last bar on 2026-08-24, no
    bar after it. Long after any roll a name with no bar is gone, and every
    session is written with it in `missing`."""
    at("2026-10-12 15:00")
    monkeypatch.setattr(do, "fetch_session_range", ranged({
        "2026-10-05": universe,
        "2026-10-06": ["SPY", "AAPL", "MSFT", "BTC"],
        "2026-10-07": ["SPY", "AAPL", "MSFT", "BTC"]}))
    assert do.main(["--out", str(tmp_path), "--since", "2026-10-05",
                    "--date", "2026-10-07"]) == 0
    out = capsys.readouterr().out
    assert ("  2026-10-06: 4 series, 2 missing (META had a bar in the session "
            "on file before it (2026-10-05) and none here)") in out
    assert "Wrote 3 session file(s), skipped 0 existing." in out
    assert "refused" not in out.lower()


# -- what the provider lists for a name ---------------------------------------

def test_listed_rows_ask_for_the_symbol_named_and_witness_rows_for_spy():
    asked = []

    def fetch(symbol, start, end):
        asked.append(symbol)
        return chart(("2026-10-05 13:30", 741.9), ("2026-10-06 13:30", None))

    assert do.listed_rows("META", "2026-10-01", "2026-10-06", fetch) == {
        "2026-10-05": 741.9, "2026-10-06": None}
    do.witness_rows("2026-10-01", "2026-10-06", fetch)
    assert asked == ["META", "SPY"]


def test_explains_names_whose_close_is_not_posted_yet():
    said = do.explain_gone("2026-10-06", ["ABBV", "ABNB"], rows_for=lambda
                           symbol, start, end: {"2026-10-05": 1.0,
                                                "2026-10-06": None})
    assert said == ("It lists 2026-10-06 for ABBV and ABNB as a session with "
                    "a NULL close: the session ended and the bar is not "
                    "posted yet. Its end-of-day roll is part done.")


def test_explains_each_answer_apart_and_asks_about_three_names_only():
    answers = {"AAA": {"2026-10-05": 1.0, "2026-10-06": None},
               "BBB": {"2026-10-05": 1.0, "2026-10-06": 2.0},
               "CCC": {"2026-10-05": 1.0}}
    asked = []

    def rows_for(symbol, start, end):
        asked.append(symbol)
        return answers.get(symbol)

    said = do.explain_gone("2026-10-06", ["AAA", "BBB", "CCC", "DDD"],
                           rows_for=rows_for)
    assert asked == ["AAA", "BBB", "CCC"]
    assert said.startswith("Asked the provider about the first 3 of them.")
    assert "for AAA as a session with a NULL close" in said
    assert "a settled close on 2026-10-06 for BBB" in said
    assert "no row on 2026-10-06 for CCC" in said

    assert do.explain_gone("2026-10-06", ["DDD"], rows_for=rows_for) == (
        "It gave no answer that could be read for DDD; a symbol it has "
        "dropped answers that way too.")


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
