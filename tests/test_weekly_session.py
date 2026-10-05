"""Which session a weekly file is, and what happens when the Friday is none.

Run for a market holiday, the live weekly writer committed an empty panel.
`fetch_weekly_bars` kept only bars dated the Friday, so on 2026-07-03 every
ticker came back "no bar dated 2026-07-03 in window 2026-06-23..2026-07-04",
`write_weekly` wrote `series: {}` with nothing to say the Friday was not a
session, and `truth_check --feed` passed the file (confirmed by running it,
2026-10-05). The five holiday weeks in the panel never met that path: the
backfill wrote them. The live job started on 2026-08-14 and has not yet run
on a holiday. The next two are 2026-12-25 and 2027-01-01, Fridays running.

On the night, "no SPY bar dated Friday" cannot be told from a provider that
has not posted. That is not hypothetical: on Saturday 2026-08-29 the
provider's daily closes for an ordinary Friday were all null. So the rule is
the one the Treasury path and the instrument path already follow, with SPY
as the witness: the bar dated the Friday or nothing, and an earlier session
of the week only once a later bar proves the Friday was skipped, with its
date in the file.

The job runs on the Saturday and SPY's next bar is Monday's, so a holiday
week is never written by the run that first meets it. It is written by the
next run that can, oldest first, and a week left behind fails the gate.

No network: the provider is stubbed at the two places the writer meets it.
"""
from __future__ import annotations

import datetime as dt
import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yfinance  # the stub conftest installs

from conftest import ROOT, SCRIPTS, weekly_doc

import audit_series as aus  # noqa: E402  (conftest stubs the provider)
import backfill_weekly as bf  # noqa: E402
import daily_observe as do  # noqa: E402
import truth_check as tc  # noqa: E402
from scan_pipeline import snapshot, snapshot_macro as sm  # noqa: E402

D = dt.date
UTC = dt.timezone.utc

XMAS = D(2026, 12, 25)                  # a Friday, and the market is closed
EVE = D(2026, 12, 24)
XMAS_WEEK = {D(2026, 12, 21), D(2026, 12, 22), D(2026, 12, 23), EVE}
NEW_YEAR = D(2027, 1, 1)                # the Friday after, closed too
UNIVERSE = ["AAPL", "SPCX", "SPY", "XLK"]
QUIET = {"rates": {}, "vol": {}, "commodities": {}, "fx": {}, "missing": []}

TRUTH = SCRIPTS / "truth_check.py"


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    """conftest stubs yfinance; the listing probe is plain urllib and would
    get through. A test that reaches the provider fails here instead of
    quietly depending on the network. Nothing waits between retries."""
    def refuse(*a, **k):
        raise AssertionError("a test reached for the provider")
    monkeypatch.setattr(snapshot, "_fetch_chart", refuse)
    monkeypatch.setattr(snapshot.time, "sleep", lambda s: None)


def weekdays(first, last, closed=()):
    out, day = set(), first
    while day <= last:
        if day.weekday() < 5 and day not in closed:
            out.add(day)
        day += dt.timedelta(days=1)
    return out


# -- the rule ------------------------------------------------------------------

def test_the_fridays_own_bar_is_the_session():
    days = weekdays(D(2026, 10, 5), D(2026, 10, 9))
    assert snapshot.week_session(days, D(2026, 10, 9)) == (
        D(2026, 10, 9), None)


def test_a_friday_with_no_bar_and_none_after_is_no_session():
    """Saturday 2026-12-26. Four sessions that week, nothing dated the 25th
    and nothing after it. Thursday is right there and is not taken: this is
    also exactly what an ordinary Friday looks like before it is posted."""
    session, why = snapshot.week_session(XMAS_WEEK, XMAS)
    assert session is None
    assert "no SPY bar dated 2026-12-25, and none after it yet" in why
    assert "no earlier session is substituted" in why


def test_a_later_bar_proves_the_holiday_and_thursday_stands_in():
    assert snapshot.week_session(XMAS_WEEK | {D(2026, 12, 28)}, XMAS) == (
        EVE, None)


def test_a_stand_in_never_comes_from_an_earlier_week():
    """A week with no session before its Friday has nothing to stand in.
    Last week's close under this week's date would be a week-old number."""
    session, why = snapshot.week_session(
        {D(2026, 12, 18), D(2026, 12, 28)}, XMAS)
    assert session is None
    assert "its week has no earlier session to stand in" in why


def test_the_second_holiday_friday_is_answered_the_same_way():
    week = weekdays(D(2026, 12, 28), D(2026, 12, 31))
    assert snapshot.week_session(week, NEW_YEAR)[0] is None
    assert snapshot.week_session(week | {D(2027, 1, 4)}, NEW_YEAR) == (
        D(2026, 12, 31), None)


def test_the_rule_is_the_one_the_instruments_follow():
    """snapshot_macro.select_bar, without the settlement hour. Two copies of
    one rule, in two modules that cannot import each other at load, held to
    one answer over every set of bars a week and its neighbours can show."""
    span = sorted(XMAS_WEEK | {D(2026, 12, 18), XMAS, D(2026, 12, 28)})
    now = dt.datetime(2027, 2, 1, tzinfo=UTC)
    for n in range(len(span) + 1):
        for days in map(set, itertools.combinations(span, n)):
            ours, why = snapshot.week_session(days, XMAS)
            theirs, err = sm.select_bar(days, XMAS, {"symbol": "SPY"}, now)
            assert ours == theirs, sorted(days)
            assert (why is None) == (err is None), sorted(days)


# -- asking the witness --------------------------------------------------------

class Frame:
    """What Ticker.history returns, as far as _witness_days looks at it."""

    def __init__(self, rows):
        self.rows = rows

    @property
    def empty(self):
        return not self.rows

    def iterrows(self):
        for day, close in self.rows:
            yield (dt.datetime(day.year, day.month, day.day),
                   {"Close": close, "Volume": 1})


@pytest.fixture
def witness(monkeypatch):
    """Stub yfinance.Ticker. Returns (answers, calls): answers is a list the
    provider works through, one per call -- rows, or an exception."""
    answers, calls = [], []

    class Ticker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, start=None, end=None):
            calls.append((self.symbol, start, end))
            answer = answers.pop(0) if len(answers) > 1 else answers[0]
            if isinstance(answer, Exception):
                raise answer
            return Frame([r for r in answer
                          if start <= r[0].isoformat() < end])

    monkeypatch.setattr(yfinance, "Ticker", Ticker, raising=False)
    return answers, calls


def test_the_witness_is_asked_from_the_monday_to_past_the_friday(witness):
    """Nothing before the Monday can be used, and a bar that proves the
    Friday was skipped can only be found by looking past it."""
    answers, calls = witness
    answers.append([(d, 680.0) for d in sorted(
        XMAS_WEEK | {D(2026, 12, 18), D(2026, 12, 28), D(2027, 1, 4)})])
    days, problem = snapshot._witness_days(XMAS)
    assert problem is None
    assert days == XMAS_WEEK | {D(2026, 12, 28)}
    assert calls == [("SPY", "2026-12-21", "2027-01-02")]


def test_a_row_with_no_close_is_not_a_bar(witness):
    """For an hour or more each evening the provider serves the session
    that just closed with a null close. It does not answer for the Friday,
    and a later one would prove nothing."""
    answers, _ = witness
    friday = D(2026, 10, 9)
    answers.append([(D(2026, 10, 8), 760.1), (friday, float("nan")),
                    (D(2026, 10, 12), None)])
    days, _ = snapshot._witness_days(friday)
    assert days == {D(2026, 10, 8)}
    assert snapshot.week_session(days, friday)[0] is None


def test_one_failed_request_is_asked_again(witness):
    answers, calls = witness
    answers.extend([OSError("timed out"), [(EVE, 690.0)]])
    assert snapshot._witness_days(XMAS) == ({EVE}, None)
    assert len(calls) == 2


def test_a_provider_that_does_not_answer_is_unknown_not_a_holiday(witness):
    answers, _ = witness
    answers.append(OSError("timed out"))
    assert snapshot._witness_days(XMAS) == (None, "OSError: timed out")

    answers[:] = [[]]
    days, problem = snapshot._witness_days(XMAS)
    assert days is None
    assert problem == "no SPY bars at all returned for 2026-12-21..2027-01-02"


# -- the provider's own listing ------------------------------------------------

def chart(*rows, meta=None):
    """A raw chart payload from (UTC stamp, close) pairs, in the shape the
    v8 endpoint answers with. A daily row is stamped at the open: 13:30 UTC
    in summer, 14:30 in winter."""
    stamps = [int(dt.datetime.strptime(stamp, "%Y-%m-%d %H:%M").replace(
        tzinfo=UTC).timestamp()) for stamp, _ in rows]
    return {"chart": {"error": None, "result": [{
        "meta": meta if meta is not None else {"gmtoffset": -18000},
        "timestamp": stamps,
        "indicators": {"quote": [{
            "close": [close for _, close in rows],
            "volume": [36666700] * len(rows)}]}}]}}


CHRISTMAS_LISTED = chart(
    ("2026-12-23 14:30", 688.02), ("2026-12-24 14:30", 690.38),
    ("2026-12-28 14:30", 690.31), ("2026-12-29 14:30", 687.85))


def test_a_holiday_is_not_listed_and_an_unsettled_session_is():
    """The one distinction a download cannot draw. Christmas has no row at
    all; a session whose close is not posted has a row and a null."""
    assert snapshot.parse_listing(CHRISTMAS_LISTED) == {
        D(2026, 12, 23): 688.02, D(2026, 12, 24): 690.38,
        D(2026, 12, 28): 690.31, D(2026, 12, 29): 687.85}

    unsettled = chart(("2026-10-08 13:30", 760.1), ("2026-10-09 13:30", None),
                      ("2026-10-12 13:30", 775.0), meta={"gmtoffset": -14400})
    assert snapshot.parse_listing(unsettled) == {
        D(2026, 10, 8): 760.1, D(2026, 10, 9): None, D(2026, 10, 12): 775.0}


def test_a_price_is_never_overwritten_by_the_null_beside_it():
    """While a session is live its own row is null and the close rides on a
    second row stamped at the last trade, same date, either way round."""
    for rows in ((("2026-10-05 13:30", None), ("2026-10-05 17:59", 774.1)),
                 (("2026-10-05 17:59", 774.1), ("2026-10-05 13:30", None))):
        assert snapshot.parse_listing(chart(*rows)) == {D(2026, 10, 5): 774.1}


@pytest.mark.parametrize("payload", [
    None, {}, {"chart": {"result": None}}, {"chart": {"result": []}},
    {"chart": {"result": [{"timestamp": [1], "indicators": {}}]}},
])
def test_a_listing_that_cannot_be_read_is_unknown_not_empty(payload):
    assert snapshot.parse_listing(payload) is None


def test_the_listing_is_read_as_the_daily_feed_reads_it():
    """scripts/daily_observe.py has drawn this distinction from this payload
    since the null-close window cost it two sessions. Two readers of one
    answer, in a package and a script that cannot share an import, held to
    the same dates in both seasons and with or without the provider's
    offset: a last trade at 20:00 New York is the next day in UTC."""
    rows = (("2026-07-02 13:30", 744.78), ("2026-07-06 13:30", 751.28),
            ("2026-10-02 13:30", 769.64), ("2026-10-05 13:30", None),
            ("2026-10-06 00:00", 774.83), ("2026-12-24 14:30", 690.38),
            ("2026-12-28 14:30", None), ("2026-12-29 01:00", 692.1))
    for meta in ({"gmtoffset": -14400}, {"gmtoffset": -18000}, {},
                 {"gmtoffset": None}):
        payload = chart(*rows, meta=meta)
        ours = {d.isoformat(): c
                for d, c in snapshot.parse_listing(payload).items()}
        assert ours == do.witness_rows("2026-07-01", "2026-12-31",
                                       fetch=lambda *a: payload), meta
    assert ours == {"2026-07-02": 744.78, "2026-07-06": 751.28,
                    "2026-10-02": 769.64, "2026-10-05": 774.83,
                    "2026-12-24": 690.38, "2026-12-28": 692.1}


def test_the_listing_is_asked_for_the_week_and_the_seven_days_after(
        monkeypatch):
    asked = []

    def fetch(symbol, start, end):
        asked.append((symbol, start, end))
        return chart(("2026-12-18 14:30", 684.0), *[
            (d.isoformat() + " 14:30", 690.0) for d in sorted(
                XMAS_WEEK | {D(2026, 12, 28), D(2027, 1, 4)})])

    monkeypatch.setattr(snapshot, "_fetch_chart", fetch)
    assert snapshot.witness_listing(XMAS) == {
        d: 690.0 for d in XMAS_WEEK | {D(2026, 12, 28)}}
    assert asked == [("SPY", D(2026, 12, 21), D(2027, 1, 1))]

    monkeypatch.setattr(snapshot, "_fetch_chart", lambda *a: None)
    assert snapshot.witness_listing(XMAS) is None


@pytest.mark.parametrize("listing,why", [
    ({EVE: 690.38, D(2026, 12, 28): 690.31}, None),
    (None, "could not be asked what it lists for that day"),
    ({EVE: 690.38, XMAS: None, D(2026, 12, 28): 690.31},
     "lists 2026-12-25 as a session whose SPY close is null"),
    ({EVE: 690.38, XMAS: 691.0, D(2026, 12, 28): 690.31},
     "lists a settled SPY close for 2026-12-25 that the download did not "
     "return"),
    ({EVE: 690.38}, "shows no SPY session after 2026-12-25 yet"),
    ({}, "shows no SPY session after 2026-12-25 yet"),
])
def test_thursday_stands_in_only_where_the_listing_skips_the_friday(
        listing, why):
    got = snapshot.stand_in_refusal(listing, XMAS)
    if why is None:
        assert got is None
    else:
        assert why in got


def test_the_question_is_put_to_the_provider_not_to_the_download(
        monkeypatch):
    monkeypatch.setattr(snapshot, "_fetch_chart",
                        lambda *a: CHRISTMAS_LISTED)
    assert snapshot.confirm_stand_in(XMAS) is None

    monkeypatch.setattr(snapshot, "_fetch_chart", lambda *a: chart(
        ("2026-12-24 14:30", 690.38), ("2026-12-25 14:30", None),
        ("2026-12-28 14:30", 690.31)))
    assert "it traded and has not settled" in snapshot.confirm_stand_in(XMAS)


# -- the fetch -----------------------------------------------------------------

class Provider:
    """The provider as it stands on one day: it has a bar for every session
    up to `today`, and none for a day that was not a session. A session in
    `unsettled` has traded and has no close yet: no bar comes back for it
    from a download, and the provider's own listing shows it with a null."""

    def __init__(self, monkeypatch, sessions, today):
        self.sessions = set(sessions)
        self.today = today
        self.asked = []
        self.problem = None
        self.dropped = set()
        self.unsettled = set()
        self.listing_down = False
        self.listed = []
        monkeypatch.setattr(snapshot, "_witness_days", self.witness_days)
        monkeypatch.setattr(snapshot, "fetch_session_bars", self.batch)
        monkeypatch.setattr(snapshot, "witness_listing", self.listing)

    def known(self):
        return {d for d in self.sessions
                if d <= self.today and d not in self.unsettled}

    def witness_days(self, friday):
        if self.problem:
            return None, self.problem
        monday = friday - dt.timedelta(days=friday.weekday())
        return {d for d in self.known()
                if monday <= d <= friday + dt.timedelta(days=8)}, None

    def listing(self, friday):
        self.listed.append(friday)
        if self.listing_down:
            return None
        monday = friday - dt.timedelta(days=friday.weekday())
        last = friday + dt.timedelta(days=7)
        rows = {d: 100.0 + d.day for d in self.known() if monday <= d <= last}
        rows.update({d: None for d in self.unsettled
                     if monday <= d <= min(last, self.today)})
        return rows

    def batch(self, tickers, session_date):
        self.asked.append(session_date)
        day = D.fromisoformat(session_date)
        got = {"bars": {}, "missing": []}
        for t in tickers:
            if day in self.known() and t not in self.dropped:
                got["bars"][t] = {"close": 100.0 + day.day, "volume": 1000}
            else:
                got["missing"].append({
                    "ticker": t,
                    "reason": "no bar dated " + session_date})
        return got


HOLIDAYS = weekdays(D(2026, 12, 14), D(2027, 1, 8), closed=(XMAS, NEW_YEAR))


def test_on_the_night_the_fetch_is_refused_and_says_why(monkeypatch):
    """Saturday 2026-12-26, as the old writer met 2026-07-03: it came back
    with no bars and 'no bar dated ...' for every ticker, and the caller
    wrote that down as a file."""
    provider = Provider(monkeypatch, HOLIDAYS, today=D(2026, 12, 26))
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-25")

    assert got["bars"] == {} and got["session"] is None
    assert "none after it yet" in got["refused"]
    assert [m["ticker"] for m in got["missing"]] == UNIVERSE
    assert {m["reason"] for m in got["missing"]} == {got["refused"]}
    assert provider.asked == [], "no session, so no bars were asked for"


def test_once_a_later_session_exists_every_bar_is_thursdays(monkeypatch):
    """The same call, the Saturday after. Monday the 28th has traded, so
    the 25th was skipped and the 24th answers for it -- for every ticker."""
    provider = Provider(monkeypatch, HOLIDAYS, today=D(2027, 1, 2))
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-25")

    assert got["session"] == "2026-12-24"
    assert "refused" not in got
    assert provider.asked == ["2026-12-24"]
    assert provider.listed == [XMAS], "the provider's listing was asked"
    assert got["bars"]["SPY"] == {"close": 124.0, "volume": 1000}
    assert sorted(got["bars"]) == UNIVERSE


def test_an_ordinary_friday_is_its_own_session(monkeypatch):
    provider = Provider(monkeypatch, HOLIDAYS, today=D(2026, 12, 19))
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-18")
    assert got["session"] == "2026-12-18"
    assert provider.asked == ["2026-12-18"]
    assert provider.listed == [], "its own bar needs no second opinion"


def test_a_friday_that_traded_and_has_not_settled_is_not_a_holiday(
        monkeypatch):
    """Monday 2026-12-21, and the close of Friday the 18th is still null at
    the provider. A download drops that row, so what comes back is Thursday,
    then Monday: the shape of a holiday. The provider's own listing has the
    Friday, with no close, and nothing stands in for a day that traded."""
    provider = Provider(monkeypatch, HOLIDAYS, today=D(2026, 12, 21))
    provider.unsettled = {D(2026, 12, 18)}
    days, _ = provider.witness_days(D(2026, 12, 18))
    assert snapshot.week_session(days, D(2026, 12, 18)) == (
        D(2026, 12, 17), None), "by the bars alone, Thursday would stand in"

    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-18")
    assert got["session"] is None and got["bars"] == {}
    assert "lists 2026-12-18 as a session whose SPY close is null" in \
        got["refused"]
    assert "it traded and has not settled" in got["refused"]
    assert provider.asked == []

    provider.unsettled = set()              # ... and once it has settled
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-18")
    assert got["session"] == "2026-12-18"


def test_a_holiday_nobody_could_confirm_is_not_written(monkeypatch):
    """The bars say holiday and the listing cannot be asked. Unknown is not
    'not listed': the week waits for a run that can ask."""
    provider = Provider(monkeypatch, HOLIDAYS, today=D(2027, 1, 2))
    provider.listing_down = True
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-25")
    assert got["session"] is None and provider.asked == []
    assert "could not be asked what it lists for that day" in got["refused"]


def test_a_ticker_gets_the_sessions_bar_or_is_missing(monkeypatch):
    """No ticker gets a day of its own. A name that did not trade on the
    session the witness names is listed, as on any other Friday."""
    provider = Provider(monkeypatch, HOLIDAYS, today=D(2027, 1, 2))
    provider.dropped = {"SPCX"}
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-25")
    assert "SPCX" not in got["bars"]
    assert got["missing"] == [{"ticker": "SPCX",
                               "reason": "no bar dated 2026-12-24"}]


def test_an_ordinary_friday_survives_a_witness_that_cannot_be_asked(
        monkeypatch):
    """The quick question is one more request than the old writer made, and
    its failure must not cost an ordinary week. SPY's bar dated the Friday
    in the batch IS the session; that case needs no proof."""
    provider = Provider(monkeypatch, HOLIDAYS, today=D(2026, 12, 19))
    provider.problem = "OSError: timed out"
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-18")
    assert got["session"] == "2026-12-18" and "refused" not in got
    assert sorted(got["bars"]) == UNIVERSE
    assert provider.asked == ["2026-12-18"]


def test_a_witness_that_could_not_be_asked_never_lets_thursday_in(
        monkeypatch):
    """The same failure on a holiday. The batch has no SPY bar dated the
    Friday, and without the witness nothing says what followed it."""
    provider = Provider(monkeypatch, HOLIDAYS, today=D(2027, 1, 2))
    provider.problem = "OSError: timed out"
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-25")
    assert got["session"] is None and got["bars"] == {}
    assert "could not ask the provider" in got["refused"]
    assert "so the session is unknown" in got["refused"]
    assert provider.asked == ["2026-12-25"] and provider.listed == []


def test_a_batch_that_drops_the_witness_is_refused(monkeypatch):
    """The witness call saw the bar and the batch came back without it. The
    other 333 bars are not a weekly file."""
    provider = Provider(monkeypatch, HOLIDAYS, today=D(2026, 12, 19))
    provider.dropped = {"SPY"}
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-18")
    assert got["bars"] == {} and got["session"] is None
    assert "a transient provider failure" in got["refused"]


def test_a_late_post_is_refused_and_later_read_as_the_friday_it_was(
        witness, monkeypatch):
    """Saturday 2026-08-29: an ordinary Friday whose closes were all null at
    the provider. Taken for a holiday, it would have gone in as Thursday's
    close. Refused, it is read a week later as what it was."""
    answers, _ = witness
    friday, thursday = D(2026, 8, 28), D(2026, 8, 27)
    monkeypatch.setattr(snapshot, "fetch_session_bars",
                        lambda tickers, day: {
                            "bars": {t: {"close": 1.0, "volume": 1}
                                     for t in tickers},
                            "missing": [], "asked": day})
    answers.append([(thursday, 771.3), (friday, float("nan"))])
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-08-28")
    assert got["session"] is None and "none after it yet" in got["refused"]

    answers[:] = [[(thursday, 771.3), (friday, 773.9),
                   (D(2026, 8, 31), 775.0)]]
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-08-28")
    assert got["session"] == got["asked"] == "2026-08-28"


# -- the file ------------------------------------------------------------------

def bars(session=None, **extra):
    got = {"bars": {t: {"close": 100.0, "volume": 1000} for t in UNIVERSE},
           "missing": []}
    if session:
        got["session"] = session
    got.update(extra)
    return got


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_a_refused_fetch_writes_no_file_and_fetches_no_instruments(
        tmp_path, monkeypatch):
    def no_specials(friday):
        raise AssertionError("fetched instruments for a week not written")

    monkeypatch.setattr(snapshot, "get_special_instruments", no_specials)
    Provider(monkeypatch, HOLIDAYS, today=D(2026, 12, 26))
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2026-12-25")

    with pytest.raises(snapshot.NoSessionWitness) as refusal:
        snapshot.write_weekly("2026-12-25", got, out_dir=str(tmp_path))
    said = str(refusal.value)
    assert said.startswith("REFUSED, nothing written")
    assert "no SPY bar dated 2026-12-25, and none after it yet" in said
    assert "do not build one another way" in said
    assert not (tmp_path / "weekly").exists()


def test_the_empty_panel_the_old_writer_committed_is_refused(tmp_path):
    """2026-07-03 exactly as it came back on 2026-10-05: no bars, and every
    ticker missing for want of a bar dated the Friday."""
    old = {"bars": {}, "missing": [
        {"ticker": t, "reason": "no bar dated 2026-07-03 in window "
                                "2026-06-23..2026-07-04"} for t in UNIVERSE]}
    with pytest.raises(snapshot.NoSessionWitness,
                       match="hold no SPY bar"):
        snapshot.write_weekly("2026-07-03", old, QUIET,
                              out_dir=str(tmp_path))
    assert not (tmp_path / "weekly").exists()


def test_a_panel_without_the_witness_is_refused_whoever_hands_it_over(
        tmp_path):
    """Every weekly writer comes through write_weekly, so this is where a
    run restricted to a few names stops being able to start a week."""
    with pytest.raises(snapshot.NoSessionWitness):
        snapshot.write_weekly(
            "2026-10-09", {"PLTR": {"close": 180.0, "volume": 5}}, QUIET,
            out_dir=str(tmp_path))
    assert not (tmp_path / "weekly").exists()


def test_a_stand_in_week_names_its_session(tmp_path):
    path = snapshot.write_weekly("2026-12-25", bars("2026-12-24"), QUIET,
                                 out_dir=str(tmp_path / "data"))
    doc = read(path)

    assert doc["as_of"] == "2026-12-25"
    assert doc["session_note"] == "Friday holiday; bars from 2026-12-24"
    assert sorted(doc["series"]) == UNIVERSE
    assert doc["source"] == "yahoo", "sector-regime-heatmap reads this"
    assert "provenance" not in doc, (
        "the session is file-level; check_basis() refuses a "
        "provenance.series source it does not know")
    assert aus.named_session(doc) == "2026-12-24", (
        "audit_series.py reads the session back out of the note")

    raw = Path(path).read_bytes()
    raw.decode("ascii")
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    assert fails(gate(tmp_path, D(2026, 12, 29))) == []


def test_an_ordinary_week_carries_no_note(tmp_path):
    for got in (bars(), bars("2026-10-09"),
                {t: {"close": 100.0, "volume": 1} for t in UNIVERSE}):
        doc = read(snapshot.write_weekly("2026-10-09", got, QUIET,
                                         out_dir=str(tmp_path)))
        assert "session_note" not in doc


@pytest.mark.parametrize("session", [
    "2026-12-18",       # last week's Friday
    "2026-12-26",       # the day after
    "2026-12-28",       # the bar that proves it, not the one that stands in
    "Thursday",
])
def test_a_session_that_cannot_stand_in_is_not_written(tmp_path, session):
    with pytest.raises(ValueError):
        snapshot.write_weekly("2026-12-25", bars(session), QUIET,
                              out_dir=str(tmp_path))
    assert not (tmp_path / "weekly").exists()


# -- the Saturdays of 2026-12-26, 2027-01-02 and 2027-01-09 --------------------

def saturday_job(root, today):
    """What the weekly job does with the writer: every Friday the panel
    owes a file for, oldest first, stopping at the first one refused."""
    wrote, refused = [], None
    for friday in snapshot.unwritten_fridays(str(root / "weekly"), today):
        got = snapshot.fetch_weekly_bars(UNIVERSE, friday)
        try:
            snapshot.write_weekly(friday, got, QUIET, out_dir=str(root))
        except snapshot.NoSessionWitness:
            refused = friday
            break
        wrote.append(friday)
    return wrote, refused


@pytest.fixture
def december(tmp_path, monkeypatch):
    """A panel that ends on 2026-12-18, and the provider over the holidays."""
    data = tmp_path / "data"
    (data / "weekly").mkdir(parents=True)
    for friday in ("2026-12-11", "2026-12-18"):
        (data / "weekly" / (friday + ".json")).write_text(
            json.dumps(weekly_doc(friday, UNIVERSE)), encoding="utf-8")
    return tmp_path, data, Provider(monkeypatch, HOLIDAYS,
                                    today=D(2026, 12, 26))


def on_file(data):
    return sorted(p.stem for p in (data / "weekly").glob("*.json"))


def test_two_holiday_fridays_running_each_land_a_week_late_and_whole(
        december):
    repo, data, provider = december

    # Saturday 12-26. Christmas has no bar and nothing proves why.
    assert saturday_job(data, D(2026, 12, 26)) == ([], "2026-12-25")
    assert on_file(data) == ["2026-12-11", "2026-12-18"]
    assert lines(gate(repo, D(2026, 12, 26)), "FAIL", "WARN") == []
    owed = lines(gate(repo, D(2026, 12, 27)), "WARN")
    assert len(owed) == 1 and "no weekly file yet for 2026-12-25" in owed[0]

    # Saturday 01-02. The week of the 28th has traded: Christmas is proven
    # and written from the 24th. New Year's Day is where Christmas was.
    provider.today = D(2027, 1, 2)
    assert saturday_job(data, D(2027, 1, 2)) == (["2026-12-25"],
                                                 "2027-01-01")
    doc = read(data / "weekly" / "2026-12-25.json")
    assert doc["session_note"] == "Friday holiday; bars from 2026-12-24"
    assert doc["series"]["SPY"]["close"] == 124.0
    assert lines(gate(repo, D(2027, 1, 2)), "FAIL", "WARN") == []

    # Saturday 01-09. New Year's Day from the 31st, then the week itself.
    provider.today = D(2027, 1, 9)
    assert saturday_job(data, D(2027, 1, 9)) == (
        ["2027-01-01", "2027-01-08"], None)
    assert read(data / "weekly" / "2027-01-01.json")["session_note"] == (
        "Friday holiday; bars from 2026-12-31")
    assert "session_note" not in read(data / "weekly" / "2027-01-08.json")
    assert on_file(data) == ["2026-12-11", "2026-12-18", "2026-12-25",
                             "2027-01-01", "2027-01-08"]
    rep = gate(repo, D(2027, 1, 12))
    assert lines(rep, "FAIL", "WARN") == []
    assert any("weekly panel is complete -- 5 week(s)" in line
               for line in rep.lines)


def test_a_job_that_steps_over_a_refused_week_is_stopped_by_the_gate(
        december):
    """The job as it was written: only ever the most recent Friday. Both
    holidays refused, then 01-08 written past them. A refusal is green by
    design, so the panel is what gets asked."""
    repo, data, provider = december
    provider.today = D(2027, 1, 9)
    got = snapshot.fetch_weekly_bars(UNIVERSE, "2027-01-08")
    snapshot.write_weekly("2027-01-08", got, QUIET, out_dir=str(data))

    failed = lines(gate(repo, D(2027, 1, 9)), "FAIL")
    assert len(failed) == 1
    assert ("no weekly file for 2026-12-25, 2027-01-01 -- 2 week(s) missing "
            "between 2026-12-11 and 2027-01-08") in failed[0]
    assert "snapshot.unwritten_fridays" in failed[0]

    # ... and the same job, done in order, clears it.
    assert saturday_job(data, D(2027, 1, 9)) == (
        ["2026-12-25", "2027-01-01"], None)
    assert lines(gate(repo, D(2027, 1, 9)), "FAIL") == []


# -- what the panel owes -------------------------------------------------------

def test_the_fridays_owed_run_from_the_newest_file_to_the_last_one_past(
        december):
    _, data, _ = december
    weekly = str(data / "weekly")
    assert snapshot.unwritten_fridays(weekly, D(2026, 12, 19)) == []
    assert snapshot.unwritten_fridays(weekly, D(2026, 12, 25)) == [], (
        "a Friday is not owed on the Friday")
    assert snapshot.unwritten_fridays(weekly, D(2026, 12, 26)) == [
        "2026-12-25"]
    assert snapshot.unwritten_fridays(weekly, D(2027, 1, 9)) == [
        "2026-12-25", "2027-01-01", "2027-01-08"]


def test_a_hole_is_owed_first_and_a_correction_is_not_a_file(december):
    _, data, _ = december
    (data / "weekly" / "2026-12-18.json").rename(
        data / "weekly" / "2026-12-18.corrected.json")
    (data / "weekly" / "2027-01-01.json").write_text("{}", encoding="utf-8")
    assert snapshot.unwritten_fridays(str(data / "weekly"),
                                      D(2027, 1, 9)) == [
        "2026-12-18", "2026-12-25", "2027-01-08"]


def test_an_empty_directory_owes_nothing(tmp_path):
    assert snapshot.unwritten_fridays(str(tmp_path), D(2027, 1, 9)) == []
    assert snapshot.unwritten_fridays(str(tmp_path / "nowhere"),
                                      D(2027, 1, 9)) == []


def test_the_writer_and_the_gate_count_the_same_fridays(december):
    """truth_check stays stdlib-only and counts for itself. From the Sunday
    on, what it calls missing or owed is what the writer says it owes."""
    _, data, _ = december
    (data / "weekly" / "2027-01-08.json").write_text("{}", encoding="utf-8")
    for today in (D(2027, 1, 10), D(2027, 1, 13), D(2027, 1, 17),
                  D(2027, 2, 1)):
        holes, owed = tc.weekly_gaps(on_file(data), today)
        assert holes + owed == snapshot.unwritten_fridays(
            str(data / "weekly"), today)
    assert tc.weekly_gaps(on_file(data), D(2027, 1, 16)) == (
        ["2026-12-25", "2027-01-01"], []), "not owed on the Saturday"


# -- the gate ------------------------------------------------------------------

def gate(repo, today):
    rep = tc.Report()
    tc.check_feed(repo, rep)
    tc.check_weekly_completeness(repo, today, rep)
    return rep


def lines(rep, *levels):
    return [line for line in rep.lines if line.startswith(levels)]


def fails(rep):
    return lines(rep, "FAIL")


def old_writer_file(as_of):
    """What the writer from before 2026-10-06 commits for a holiday."""
    doc = weekly_doc(as_of, [])
    doc["missing"] = [
        {"ticker": t, "reason": "no bar dated %s in window" % as_of}
        for t in UNIVERSE]
    return doc


def test_the_gate_fails_an_empty_series(panel):
    """The file from the 2026-10-05 run. It passed."""
    repo = panel({"2026-07-03.json": old_writer_file("2026-07-03")}).parents[1]
    got = fails(gate(repo, D(2026, 7, 4)))
    assert len(got) == 1
    assert "2026-07-03.json 'series' is empty" in got[0]
    assert "the file does not say why" in got[0]
    assert "never commit it" in got[0]


def test_the_gate_fails_it_from_the_command_line(panel):
    """The Saturday job runs this and stops on a FAIL, which is what keeps
    a runner still on the old writer from pushing the file."""
    repo = panel({"2026-12-25.json": old_writer_file("2026-12-25")}).parents[1]
    r = subprocess.run([sys.executable, str(TRUTH), "--repo", str(repo),
                        "--feed", "--today", "2026-12-26"],
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "FAIL: feed: 2026-12-25.json 'series' is empty" in r.stdout


def test_the_gate_fails_a_new_file_without_the_witness(panel):
    doc = weekly_doc("2026-10-09", ["AAPL", "XLK"])
    got = fails(gate(panel({"2026-10-09.json": doc}).parents[1],
                     D(2026, 10, 10)))
    assert len(got) == 1
    assert "2026-10-09.json has 2 series and no SPY bar" in got[0]


def test_the_gate_holds_a_daily_file_to_the_witness_too(tmp_path):
    doc = weekly_doc("2026-10-07", [])
    doc["cadence"], doc["source"] = "daily", "yahoo-daily"
    daily = tmp_path / "data" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-10-07.json").write_text(json.dumps(doc), encoding="utf-8")
    rep = tc.Report()
    tc.check_feed(tmp_path, rep, subdir="daily", require_friday=False,
                  label="daily")
    assert len(fails(rep)) == 1 and "'series' is empty" in fails(rep)[0]


def test_the_one_old_file_without_the_witness_is_warned_about_not_failed(
        panel):
    """2024-08-09.json: started by a backfill restricted to 44 names, 270
    more merged in, the index and sector ETFs never. It cannot be edited."""
    doc = weekly_doc("2024-08-09", ["AAPL", "XLK"], source="yahoo-backfill")
    rep = gate(panel({"2024-08-09.json": doc}).parents[1], D(2024, 8, 10))
    assert fails(rep) == []
    warned = lines(rep, "WARN")
    assert len(warned) == 1
    assert "has 2 series and no SPY bar, and does not list it in " \
           "'missing'" in warned[0]
    assert "--merge" in warned[0]

    doc["missing"] = [{"ticker": "SPY", "reason": "not fetched"}]
    rep = gate(panel({"2024-08-09.json": doc}).parents[1], D(2024, 8, 10))
    assert "does not list it" not in lines(rep, "WARN")[0]


@pytest.mark.parametrize("note,why", [
    ("Friday holiday; bars from 2026-12-24", None),
    ("Friday holiday; bars from 2026-12-21", None),
    ("thin holiday trade", "is not 'Friday holiday; bars from YYYY-MM-DD'"),
    ("Friday holiday; bars from 12/24", "is not 'Friday holiday; bars from"),
    (["2026-12-24"], "is not 'Friday holiday; bars from"),
    ("Friday holiday; bars from 2026-12-25",
     "is not an earlier day in the week of 2026-12-25"),
    ("Friday holiday; bars from 2026-12-18",
     "is not an earlier day in the week of 2026-12-25"),
    ("Friday holiday; bars from 2026-12-28",
     "is not an earlier day in the week of 2026-12-25"),
    ("Friday holiday; bars from 2026-13-01", "is not an ISO date"),
])
def test_the_gate_reads_the_session_out_of_the_note(panel, note, why):
    doc = weekly_doc("2026-12-25", UNIVERSE)
    doc["session_note"] = note
    got = fails(gate(panel({"2026-12-25.json": doc}).parents[1],
                     D(2026, 12, 26)))
    if why is None:
        assert got == []
    else:
        assert len(got) == 1 and "session_note" in got[0] and why in got[0]


def test_a_hole_fails_and_an_unwritten_newest_week_only_warns(panel):
    weeks = {f + ".json": weekly_doc(f, UNIVERSE)
             for f in ("2026-10-09", "2026-10-16", "2026-10-30")}
    repo = panel(weeks).parents[1]

    rep = gate(repo, D(2026, 10, 31))
    assert len(fails(rep)) == 1
    assert "no weekly file for 2026-10-23 -- 1 week(s) missing between " \
           "2026-10-09 and 2026-10-30" in fails(rep)[0]
    assert lines(rep, "WARN") == []

    rep = gate(repo, D(2026, 11, 15))
    assert len(fails(rep)) == 1
    assert len(lines(rep, "WARN")) == 1
    assert "no weekly file yet for 2026-11-06, 2026-11-13 (newest is " \
           "2026-10-30)" in lines(rep, "WARN")[0]


def test_a_long_gap_is_listed_without_drowning_the_report(panel):
    repo = panel({"2026-10-09.json": weekly_doc("2026-10-09",
                                                UNIVERSE)}).parents[1]
    warned = lines(gate(repo, D(2027, 1, 3)), "WARN")
    assert len(warned) == 1
    assert "2026-10-16, 2026-10-23, 2026-10-30, 2026-11-06, 2026-11-13, " \
           "2026-11-20, ... and 6 more" in warned[0]


# -- the committed panel -------------------------------------------------------

def committed(subdir):
    return sorted((ROOT / "data" / subdir).glob("*.json"))


def test_no_committed_file_has_an_empty_series_and_the_panel_has_no_hole():
    for path in committed("weekly") + committed("daily"):
        assert read(path)["series"], path.name
    have = [p.stem for p in committed("weekly")
            if not p.name.endswith(".corrected.json")]
    holes, _ = tc.weekly_gaps(have, D.fromisoformat(have[-1]))
    assert holes == []


def test_only_the_first_week_of_the_panel_lacks_the_witness():
    """It may be healed with a --merge backfill, and this must not mind."""
    without = [p.name for p in committed("weekly") + committed("daily")
               if snapshot.WITNESS not in read(p)["series"]]
    assert set(without) <= {"2024-08-09.json"}
    assert all(name[:10] < tc.WITNESS_RULE_SINCE for name in without)


def test_the_five_committed_holiday_weeks_already_say_it_this_way():
    noted = {p.name: read(p)["session_note"] for p in committed("weekly")
             if "session_note" in read(p)}
    assert len(noted) >= 5
    for name, note in noted.items():
        session = tc.SESSION_NOTE_RE.match(note).group(1)
        assert note == snapshot.SESSION_NOTE % session
        assert snapshot.session_note(name[:10], session) == note


def test_the_committed_panel_passes_the_gate():
    rep = tc.Report()
    tc.check_feed(ROOT, rep)
    tc.check_feed(ROOT, rep, subdir="daily", require_friday=False,
                  label="daily")
    newest = max(p.stem for p in committed("weekly")
                 if not p.name.endswith(".corrected.json"))
    tc.check_weekly_completeness(ROOT, D.fromisoformat(newest), rep)
    assert fails(rep) == []


# -- one name, one note, in every module ---------------------------------------

def test_the_witness_and_the_note_are_one_definition_repeated_honestly():
    """truth_check is stdlib-only and repeats both. A repeat that drifts is
    a gate checking for a file nobody writes."""
    assert tc.WITNESS == snapshot.WITNESS == do.WITNESS == "SPY"
    note = snapshot.SESSION_NOTE % "2026-12-24"
    assert tc.SESSION_NOTE_RE.match(note).group(1) == "2026-12-24"
    assert aus._NOTE_DATE.search(note).group(1) == "2026-12-24"
    assert snapshot.session_note("2026-12-25", "2026-12-24") == note
    assert snapshot.session_note("2026-12-25", "2026-12-25") is None
    assert snapshot.session_note("2026-12-25", None) is None


# -- the daily feed takes no stand-in ------------------------------------------

def test_the_daily_feed_asks_for_its_own_date_and_nothing_else(
        tmp_path, monkeypatch, capsys):
    """A daily file is named for the session it holds. If it went through
    the weekly rule, a holiday asked for a week later would come back as
    Thursday's bars with SPY among them, and the witness gate would pass
    it."""
    assert do.fetch_session_bars is snapshot.fetch_session_bars
    assert not hasattr(do, "fetch_weekly_bars")

    asked = []

    def exact(tickers, as_of):
        asked.append(as_of)
        return {"bars": {}, "missing": []}

    monkeypatch.setattr(do, "fetch_session_bars", exact)
    monkeypatch.setattr(do, "witness_rows", lambda *a, **k: {
        "2026-12-24": 690.1, "2026-12-28": 692.4})
    monkeypatch.setattr(do, "_utcnow", lambda: dt.datetime(
        2027, 1, 2, 14, 13, tzinfo=UTC))
    assert do.main(["--out", str(tmp_path), "--date", "2026-12-25",
                    "--no-special"]) == 2
    assert asked == ["2026-12-25"]
    assert "REFUSED: No SPY bar dated 2026-12-25" in capsys.readouterr().out
    assert not (tmp_path / "daily").exists()


# -- what a reader makes of each kind of week ----------------------------------

def week_of(as_of, close):
    return as_of, weekly_doc(as_of, ["SPY"], close=close)


def spy(docs):
    state = snapshot._derive_from_files(docs, {}, None, ({}, None))
    return state["as_of"], state["index"]["SPY"]


def test_an_empty_week_blanks_market_state_and_an_unwritten_one_does_not():
    """Why no file is the better answer on the night. An empty week becomes
    the newest one and every price field derived for it is null; an
    unwritten one leaves the last real week standing, dated as what it is."""
    before = [week_of("2026-12-11", 700.0), week_of("2026-12-18", 714.0)]

    as_of, got = spy(before + [("2026-12-25", old_writer_file("2026-12-25"))])
    assert as_of == "2026-12-25"
    assert got["px"] is None and got["d1w"] is None
    assert got["px_reason"] == "no close for 2026-12-25"

    as_of, got = spy(before)
    assert (as_of, got["px"], got["d1w"]) == ("2026-12-18", 714.0, 2.0)

    as_of, got = spy(before + [week_of("2026-12-25", 721.14)])
    assert (as_of, got["px"], got["d1w"]) == ("2026-12-25", 721.14, 1.0)


def test_a_week_left_missing_nulls_the_windows_that_reach_it():
    """And why it has to be written afterwards. market_state will not read
    across a missing week; sector-regime-heatmap, which counts weeks by
    position, would, and would call two weeks one."""
    docs = [week_of("2026-12-18", 714.0), week_of("2027-01-08", 735.42)]
    _, got = spy(docs)
    assert got["px"] == 735.42 and got["d1w"] is None
    assert got["d1w_reason"] == "no weekly file dated 2027-01-01 (1w prior)"


def test_a_run_that_wrote_two_weeks_derives_through_the_chain(tmp_path):
    """Saturday 2027-01-09 writes 01-01 and 01-08 in one run. The job used
    to hand the deriver the committed state as 'last week's', and that
    state is now two weeks old: corr_prev comes from the wrong week and the
    purity check fails the file."""
    weekly = tmp_path / "data" / "weekly"
    weekly.mkdir(parents=True)
    facts = str(tmp_path / "macro" / "facts.json")
    out = tmp_path / "data" / "market_state.json"
    fridays = [(D(2026, 11, 27) + dt.timedelta(weeks=n)).isoformat()
               for n in range(7)]
    spy_px = [700.0, 707.0, 699.0, 712.0, 705.0, 721.0, 716.0]
    xlk_px = [190.0, 191.5, 192.1, 190.8, 195.0, 193.2, 199.9]

    def write(n):
        doc = weekly_doc(fridays[n], [])
        doc["series"] = {"SPY": {"close": spy_px[n], "volume": 1},
                         "XLK": {"close": xlk_px[n], "volume": 1}}
        (weekly / (fridays[n] + ".json")).write_text(json.dumps(doc),
                                                     encoding="utf-8")

    for n in range(5):
        write(n)
    committed = snapshot.derive_chain(str(weekly), facts)
    write(5)
    write(6)

    chain = snapshot.derive_chain(str(weekly), facts)
    stale = snapshot.derive_market_state(str(weekly), facts,
                                         prev_market_state=committed)
    assert stale["sectors"]["XLK"]["corr_prev"] == \
        committed["sectors"]["XLK"]["corr_spy_4w"]
    assert chain["sectors"]["XLK"]["corr_prev"] != \
        stale["sectors"]["XLK"]["corr_prev"]

    out.write_text(snapshot.canonical_json(stale), encoding="utf-8",
                   newline="")
    assert snapshot.rederive_and_compare(str(weekly), facts, str(out)) == (
        False, "$.sectors.XLK.corr_prev")

    # The night of a refusal is the same trap from the other side: nothing
    # new was written, so the committed state is this week's own.
    same = snapshot.derive_market_state(str(weekly), facts,
                                        prev_market_state=chain)
    assert same["sectors"]["XLK"]["corr_prev"] == \
        chain["sectors"]["XLK"]["corr_spy_4w"] != \
        chain["sectors"]["XLK"]["corr_prev"]

    assert snapshot.write_market_state_chain(str(weekly), facts,
                                             str(out)) == str(out)
    assert out.read_bytes() == snapshot.canonical_json(chain).encode("ascii")
    assert snapshot.rederive_and_compare(str(weekly), facts, str(out)) == (
        True, None)


# -- the backfill writer -------------------------------------------------------

def history(*days, close=655.0):
    return (list(days), [close] * len(days), [1] * len(days))


SKIPPED = {EVE: 690.38, D(2026, 12, 28): 690.31}    # Christmas, as listed


@pytest.fixture
def no_specials(monkeypatch):
    calls = []

    def fetch(friday):
        calls.append(friday)
        return dict(QUIET)

    monkeypatch.setattr(bf.snapshot_macro, "fetch_special_instruments",
                        fetch, raising=False)
    monkeypatch.setattr(bf.time, "sleep", lambda s: None)
    return calls


def test_the_backfill_no_longer_calls_an_unposted_friday_a_holiday(
        tmp_path, monkeypatch, no_specials):
    """It wrote 'Friday holiday; bars from <Thursday>' whenever no ticker
    had a Friday bar. Run on the night, that is every Friday."""
    hist = {"SPY": history(D(2026, 12, 23), EVE),
            "AAPL": history(D(2026, 12, 23), EVE)}
    with pytest.raises(snapshot.NoSessionWitness, match="none after it yet"):
        bf.build_and_write(XMAS, ["AAPL", "SPY"], hist, str(tmp_path))
    assert not (tmp_path / "weekly").exists()
    assert no_specials == []

    monkeypatch.setattr(snapshot, "witness_listing", lambda friday: SKIPPED)
    hist["SPY"] = history(D(2026, 12, 23), EVE, D(2026, 12, 28))
    rec = bf.build_and_write(XMAS, ["AAPL", "SPY"], hist, str(tmp_path))
    assert rec["session_note"] == "Friday holiday; bars from 2026-12-24"
    assert rec["doc"]["source"] == "yahoo-backfill"
    assert read(rec["path"])["session_note"] == rec["session_note"]


def test_the_backfill_asks_the_listing_before_thursday_stands_in(
        tmp_path, monkeypatch, no_specials):
    """Its history drops a row with no close like every download does. A
    Friday that traded and has not settled must not go in as a holiday
    because Monday's bar happens to be there."""
    hist = {"SPY": history(D(2026, 12, 17), D(2026, 12, 21)),
            "AAPL": history(D(2026, 12, 17), D(2026, 12, 21))}
    monkeypatch.setattr(snapshot, "witness_listing", lambda friday: {
        D(2026, 12, 17): 680.1, D(2026, 12, 18): None,
        D(2026, 12, 21): 684.9})
    with pytest.raises(snapshot.NoSessionWitness,
                       match="it traded and has not settled"):
        bf.build_and_write(D(2026, 12, 18), ["AAPL", "SPY"], hist,
                           str(tmp_path))
    assert not (tmp_path / "weekly").exists()
    assert no_specials == []


def test_a_file_that_says_thursday_holds_nothing_dated_after_it(
        tmp_path, monkeypatch, no_specials):
    """The note comes from SPY and the bars from each ticker's own slice.
    Sliced up to the Friday, a ticker with a stray Friday bar would sit in a
    file that says 'bars from Thursday'."""
    monkeypatch.setattr(snapshot, "witness_listing", lambda friday: SKIPPED)
    hist = {"SPY": history(EVE, D(2026, 12, 28)),
            "AAPL": ([EVE, XMAS], [271.5, 999.0], [10, 20])}
    rec = bf.build_and_write(XMAS, ["AAPL", "SPY"], hist, str(tmp_path))
    assert rec["session_note"] == "Friday holiday; bars from 2026-12-24"
    assert rec["doc"]["series"]["AAPL"] == {"close": 271.5, "volume": 10}


def test_a_week_is_not_written_without_its_witness_in_the_run(
        tmp_path, no_specials):
    with pytest.raises(snapshot.NoSessionWitness,
                       match="does not fetch SPY"):
        bf.build_and_write(D(2026, 10, 9), ["PLTR"],
                           {"PLTR": history(D(2026, 10, 9))}, str(tmp_path))
    assert not (tmp_path / "weekly").exists()


def run_backfill(monkeypatch, tmp_path, sessions, *args):
    """main() in-process, over a provider that has `sessions`."""
    monkeypatch.setattr(bf.snapshot, "equity_universe",
                        lambda: ["AAPL", "SPY", "XLK"])
    monkeypatch.setattr(bf, "download_equity_history",
                        lambda tickers, first, last: {
                            t: history(*sorted(sessions)) for t in tickers})
    monkeypatch.setattr(sys, "argv", [
        "backfill_weekly.py", "--out", str(tmp_path), *args])
    return bf.main()


def test_a_run_restricted_to_a_few_names_cannot_start_a_week(
        tmp_path, monkeypatch, no_specials, capsys):
    """How 2024-08-09.json was started: --only, on a Friday with no file.
    Naming SPY among the few does not make them a week: the other names
    would be in neither `series` nor `missing`, and the gate, which looks
    for SPY, would pass it."""
    sessions = weekdays(D(2026, 10, 5), D(2026, 10, 9))
    assert run_backfill(monkeypatch, tmp_path, sessions, "--only", "SPY,AAPL",
                        "--start", "2026-10-09", "--end", "2026-10-09") == 2
    out = capsys.readouterr().out
    assert "a run restricted with --only cannot start one" in out
    assert "REFUSED (1 week(s) not written):" in out
    assert list((tmp_path / "weekly").iterdir()) == []
    assert no_specials == []


def test_a_merge_adds_to_the_weeks_that_exist_and_starts_none(
        tmp_path, monkeypatch, no_specials, capsys):
    """The cure for 2024-08-09 run one Friday too far: --only the ETFs,
    --merge, over a week that has a file and one that does not."""
    weekly = tmp_path / "weekly"
    weekly.mkdir()
    (weekly / "2026-10-02.json").write_text(
        json.dumps(weekly_doc("2026-10-02", ["AAPL"])), encoding="utf-8")
    sessions = weekdays(D(2026, 9, 28), D(2026, 10, 9))

    assert run_backfill(monkeypatch, tmp_path, sessions, "--only", "SPY,XLK",
                        "--merge", "--start", "2026-10-02",
                        "--end", "2026-10-09") == 2
    out = capsys.readouterr().out
    assert sorted(p.name for p in weekly.iterdir()) == ["2026-10-02.json"]
    merged = read(weekly / "2026-10-02.json")
    assert sorted(merged["series"]) == ["AAPL", "SPY", "XLK"]
    assert sorted(merged["provenance"]["series"]) == ["SPY", "XLK"]
    assert "2026-10-09: REFUSED, nothing written: no weekly file for " \
           "2026-10-09 to add to" in out


def test_a_backfill_that_refused_a_week_does_not_exit_clean(
        tmp_path, monkeypatch, no_specials, capsys):
    """It writes the weeks it can and says which it could not. Exit 2 stops
    the workflow before its commit step."""
    sessions = weekdays(D(2026, 12, 14), EVE)
    assert run_backfill(monkeypatch, tmp_path, sessions,
                        "--start", "2026-12-18", "--end", "2026-12-25") == 2
    out = capsys.readouterr().out
    assert "REFUSED (1 week(s) not written):" in out
    assert "2026-12-25: REFUSED, nothing written for 2026-12-25" in out
    assert sorted(p.name for p in (tmp_path / "weekly").iterdir()) == [
        "2026-12-18.json"]


def test_the_history_runs_past_the_last_friday_so_a_later_bar_is_in_it(
        monkeypatch):
    asked = []

    def chunk(tickers, start, end):
        asked.append((start, end))
        return None

    class Quiet:
        @staticmethod
        def download(*a, **k):
            raise OSError("no network in tests")

    monkeypatch.setattr(bf, "_download_chunk", chunk)
    monkeypatch.setattr(bf.time, "sleep", lambda s: None)
    monkeypatch.setitem(sys.modules, "yfinance", Quiet)
    bf.download_equity_history(["SPY"], XMAS, XMAS)
    assert asked == [("2026-12-15", "2027-01-03")]
