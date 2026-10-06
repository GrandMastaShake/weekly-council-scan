"""The facts check's second witness for a currency pair (#120).

`truth_check --facts` compares each yahoo-sourced field of macro/facts.json
with the provider's latest completed daily bar. On Monday 2026-09-28 it
FAILed USDJPY, 157.185 in the table against a daily close of 158.811, and a
FAIL at the Monday Council's STEP 0c is the abort path. The table was right.

The provider's daily bar for a currency pair closes at the price it opened
at, once the bar has been replaced after its session: 566 of 566 bars each
for JPY=X and EURUSD=X as served on 2026-10-06, never more than 0.18% from
the open. That Friday's bar is open 158.842, close 158.811, on a day that
ended at 157.185. The hourly bars keep the session, and their last close
inside that daily bar's own 24 hours is 157.185, the number the table holds.

So a currency pair that is out of tolerance against its daily bar gets a
second witness before it fails: the last hourly close of the same bar, under
the same tolerance. What is pinned here:

  - a field inside its tolerance reads exactly as it did and asks nothing
    more;
  - the week of the issue passes, and the line names both numbers;
  - a table neither witness agrees with still fails, and the field's own
    tolerance is the only one;
  - no answer is not agreement: no response, no bar, bars from another
    session, bars that stop early (2026-01-30, when the provider's stopped
    with the 15:00 UTC bar), and a fetch cap already spent, each leave the
    FAIL;
  - nothing but a currency pair is asked, whatever its hourly bars say;
  - the witness is asked about the bar by its own timestamp, not its date.

No network: urlopen is replaced by canned chart responses. It keeps what it
was asked, and a symbol or an interval it was given nothing for gets the
URLError a dead line would.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import urllib.error
from urllib.parse import parse_qs, urlsplit

import pytest

import truth_check as tc  # noqa: E402  (conftest puts scripts/ on the path)

HOUR = 3600
DAY = 24 * HOUR
BST = 3600                  # the provider's gmtoffset for Europe/London, summer


def utc(year, month, day, hour=0):
    return int(dt.datetime(year, month, day, hour,
                           tzinfo=dt.timezone.utc).timestamp())


# The daily bars of JPY=X as the provider served them on 2026-10-06, each
# stamped at London's midnight: (start, open, close). No close is more than
# 0.02% from its open.
THU = utc(2026, 9, 23, 23)          # the bar of Thursday 2026-09-24
FRI = utc(2026, 9, 24, 23)          # the bar of Friday 2026-09-25
JPY_DAILY = [
    (utc(2026, 9, 21, 23), 157.361, 157.369),
    (utc(2026, 9, 22, 23), 157.474, 157.464),
    (THU, 158.270, 158.265),
    (FRI, 158.842, 158.811),
]
# Its hourly closes for that Friday, as served the same day, with what the
# provider's series holds either side: Thursday's last hours, the empty row
# it ends the week with, and the first bars of the Monday.
JPY_FRIDAY = [158.839, 158.646, 158.604, 158.465, 158.355, 158.414, 158.262,
              158.048, 158.092, 158.119, 158.051, 157.834, 157.584, 157.499,
              157.030, 157.148, 157.176, 157.198, 157.247, 157.126, 157.261,
              157.258, 157.185]
JPY_HOURLY = (
    [(FRI - 3 * HOUR, 158.832), (FRI - 2 * HOUR, 158.796),
     (FRI - HOUR, 158.755)]
    + [(FRI + i * HOUR, c) for i, c in enumerate(JPY_FRIDAY)]
    + [(FRI + 23 * HOUR, None)]
    + [(utc(2026, 9, 27, 23), 157.432), (utc(2026, 9, 28, 0), 157.802),
       (utc(2026, 9, 28, 1), 157.739)])

TODAY = dt.date(2026, 9, 28)        # for the table's age only


def chart(kind, rows, offset=BST):
    """A chart response with the fields the script reads. `rows` are
    (timestamp, open, close) or (timestamp, close)."""
    rows = [(r[0], r[-1] if len(r) == 2 else r[1], r[-1]) for r in rows]
    meta = {"gmtoffset": offset}
    if kind is not None:
        meta["instrumentType"] = kind
    return {"chart": {"error": None, "result": [{
        "meta": meta,
        "timestamp": [r[0] for r in rows],
        "indicators": {"quote": [{"open": [r[1] for r in rows],
                                  "close": [r[2] for r in rows]}]},
    }]}}


class Provider:
    """urlopen, offline. Answers by symbol and interval from what it was
    given, and keeps what it was asked."""

    def __init__(self):
        self.daily = {}
        self.hourly = {}
        self.calls = []

    def __call__(self, request, timeout=None):
        parts = urlsplit(request.full_url)
        symbol = parts.path.rsplit("/", 1)[1]
        query = parse_qs(parts.query)
        interval = query["interval"][0]
        self.calls.append((symbol, interval, int(query["period1"][0]),
                           int(query["period2"][0])))
        answer = {"1d": self.daily, "60m": self.hourly}.get(
            interval, {}).get(symbol)
        if answer is None:
            raise urllib.error.URLError("nothing canned for %s %s"
                                        % (symbol, interval))
        if isinstance(answer, Exception):
            raise answer
        return io.BytesIO(json.dumps(answer).encode("utf-8"))

    def asked(self, interval):
        return [c for c in self.calls if c[1] == interval]


@pytest.fixture
def provider(monkeypatch):
    """The provider with JPY=X's bars in it, and the script's caches empty."""
    p = Provider()
    p.daily["JPY=X"] = chart("CURRENCY", JPY_DAILY)
    p.hourly["JPY=X"] = chart("CURRENCY", JPY_HOURLY)
    monkeypatch.setattr(tc.urllib.request, "urlopen", p)
    monkeypatch.setattr(tc, "_fetch_cache", {})
    monkeypatch.setattr(tc, "_bar_cache", {})
    return p


def facts(tmp_path, **fields):
    """macro/facts.json with the given cross_asset fields:
    name=(value, symbol, tolerance_pct)."""
    doc = {"schema": "macro-facts/v1", "generated": "2026-09-26",
           "cross_asset": {
               name: {"value": value, "as_of": "2026-09-25",
                      "source": "yahoo:" + symbol, "tolerance_pct": tol}
               for name, (value, symbol, tol) in fields.items()}}
    (tmp_path / "macro").mkdir(exist_ok=True)
    (tmp_path / "macro" / "facts.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return tmp_path


def check(repo, max_fetch=60):
    rep = tc.Report()
    tc.check_facts(repo, TODAY, rep, max_fetch)
    return rep


def field_lines(rep):
    """The report without the line about the table's own age."""
    return [line for line in rep.lines if "facts.json generated" not in line]


# -- unchanged: inside the tolerance ----------------------------------------

def test_a_field_inside_its_tolerance_reads_as_before_and_asks_once(
        tmp_path, provider):
    """158.5 is 0.20% from the daily bar's 158.811. The line is the one the
    script has always printed, and the hourly bars are not asked for."""
    rep = check(facts(tmp_path, usdjpy=(158.5, "JPY=X", 1)))
    assert field_lines(rep) == [
        "OK: facts: cross_asset.usdjpy 158.5 vs live 158.811 "
        "(JPY=X 2026-09-25, dev 0.20% <= 1%)"]
    assert [c[:2] for c in provider.calls] == [("JPY=X", "1d")]


# -- the issue --------------------------------------------------------------

def test_the_week_of_issue_120_passes_on_the_sessions_hourly_bars(
        tmp_path, provider):
    """The table of 2026-09-25: 157.185, right, and 1.03% from the daily
    bar. The last hourly close of that bar's 24 hours is 157.185."""
    rep = check(facts(tmp_path, usdjpy=(157.185, "JPY=X", 1)))
    assert rep.counts["FAIL"] == 0 and rep.counts["WARN"] == 0
    assert field_lines(rep) == [
        "OK: facts: cross_asset.usdjpy 157.185 vs live 157.185 "
        "(JPY=X 2026-09-25, close of its last hourly bar, 2026-09-25 21:00 "
        "UTC, dev 0.00% <= 1%). The daily bar's close 158.811 is 1.03% "
        "away: a currency pair's daily bar is not where its session ended."]


def test_the_witness_is_asked_once_and_for_that_bars_own_24_hours(
        tmp_path, provider):
    check(facts(tmp_path, usdjpy=(157.185, "JPY=X", 1)))
    assert provider.asked("60m") == [("JPY=X", "60m", FRI, FRI + DAY)]
    assert len(provider.calls) == 2


def test_without_the_witness_that_week_is_the_fail_the_issue_quotes(
        tmp_path, provider):
    """What the Monday Council saw: the same table against the same daily
    bar, with nothing else to ask. Here the hourly bars do not answer."""
    del provider.hourly["JPY=X"]
    rep = check(facts(tmp_path, usdjpy=(157.185, "JPY=X", 1)))
    assert rep.counts["FAIL"] == 1
    assert field_lines(rep)[0].startswith(
        "FAIL: facts: cross_asset.usdjpy 157.185 vs live 158.811 "
        "(JPY=X 2026-09-25, dev 1.03% > 1%) -- canonical table disagrees "
        "with market data")


# -- a real disagreement stays a FAIL ---------------------------------------

def test_a_table_neither_witness_agrees_with_still_fails(tmp_path, provider):
    """150.0 is 5.87% from the daily bar and 4.79% from the session's last
    hourly close. Both are in the line."""
    rep = check(facts(tmp_path, usdjpy=(150.0, "JPY=X", 1)))
    assert rep.counts["FAIL"] == 1 and rep.counts["OK"] == 1
    assert field_lines(rep) == [
        "FAIL: facts: cross_asset.usdjpy 150.0 vs live 158.811 "
        "(JPY=X 2026-09-25, dev 5.87% > 1%) -- canonical table disagrees "
        "with market data. The session's last hourly bar, 2026-09-25 21:00 "
        "UTC, closed at 157.185: 4.79% away as well."]


@pytest.mark.parametrize("recorded, tol, level", [
    (155.70, 1, "OK"),      # 0.95% from 157.185
    (155.50, 1, "FAIL"),    # 1.08%
    (156.50, 0.5, "OK"),    # 0.44%
    (156.30, 0.5, "FAIL"),  # 0.57%: inside 1%, and 1% is not this field's
])
def test_the_witness_is_held_to_the_fields_own_tolerance(
        tmp_path, provider, recorded, tol, level):
    """Nothing is loosened: the hourly close is compared under the same
    tolerance_pct the daily bar just failed."""
    rep = check(facts(tmp_path, usdjpy=(recorded, "JPY=X", tol)))
    assert [line.split(":")[0] for line in field_lines(rep)] == [level]
    assert len(provider.asked("60m")) == 1


# -- no answer is not agreement ---------------------------------------------

def stops_early():
    """2026-01-30: the provider's hourly bars stop with the 15:00 UTC one.
    Here the last of them is the table's own number."""
    return chart("CURRENCY", [(FRI + i * HOUR, 157.185) for i in range(17)])


def no_close():
    return chart("CURRENCY", [(FRI + i * HOUR, None) for i in range(24)])


def another_session():
    """Bars that agree with the table, from the hours before the daily bar
    begins and after it ends."""
    return chart("CURRENCY",
                 [(FRI - (i + 1) * HOUR, 157.185) for i in range(6)]
                 + [(FRI + DAY + i * HOUR, 157.185) for i in range(6)])


@pytest.mark.parametrize("answer, why", [
    (urllib.error.URLError("timed out"),
     "its hourly bars could not be read"),
    ({"chart": {"result": None,
                "error": {"code": "Not Found", "description": "No data"}}},
     "its hourly bars could not be read"),
    ({"chart": "not what the script expects"},
     "its hourly bars could not be read"),
    (chart("CURRENCY", []),
     "the provider has no hourly bar with a close in it"),
    (no_close(),
     "the provider has no hourly bar with a close in it"),
    (another_session(),
     "the provider has no hourly bar with a close in it"),
    (stops_early(),
     "its hourly bars stop with the one of 2026-09-25 15:00 UTC, more than "
     "6 hours before the daily bar ends"),
], ids=["no-response", "error-body", "garbage", "no-bars", "no-close",
        "another-session", "stops-early"])
def test_a_witness_that_cannot_speak_leaves_the_fail(
        tmp_path, provider, answer, why):
    provider.hourly["JPY=X"] = answer
    rep = check(facts(tmp_path, usdjpy=(157.185, "JPY=X", 1)))
    assert rep.counts["FAIL"] == 1 and rep.counts["OK"] == 1
    assert field_lines(rep) == [
        "FAIL: facts: cross_asset.usdjpy 157.185 vs live 158.811 "
        "(JPY=X 2026-09-25, dev 1.03% > 1%) -- canonical table disagrees "
        "with market data. A currency pair's daily bar is not where its "
        "session ended, but nothing else speaks for this session: "
        + why + "."]


def test_hourly_bars_that_run_into_the_last_six_hours_are_a_witness(
        tmp_path, provider):
    """The line is drawn at the tail, not at a count of bars: on Monday
    2026-02-02 the provider had four hourly bars, the day's last four, and
    they say where that session ended."""
    provider.hourly["JPY=X"] = chart(
        "CURRENCY", [(FRI + i * HOUR, 157.185) for i in (18, 19, 20, 21)])
    rep = check(facts(tmp_path, usdjpy=(157.185, "JPY=X", 1)))
    assert rep.counts["FAIL"] == 0
    assert "close of its last hourly bar, 2026-09-25 20:00 UTC" in \
        field_lines(rep)[0]


@pytest.mark.parametrize("bars, level, said", [
    (18, "FAIL", "stop with the one of 2026-09-25 16:00 UTC"),
    (19, "OK", "close of its last hourly bar, 2026-09-25 17:00 UTC"),
])
def test_the_last_six_hours_begin_eighteen_hours_in(
        tmp_path, provider, bars, level, said):
    """Where the line is: a last bar that begins 17 hours into the daily
    bar has stopped more than six hours before its end, and one that begins
    18 hours in has not."""
    provider.hourly["JPY=X"] = chart(
        "CURRENCY", [(FRI + i * HOUR, 157.185) for i in range(bars)])
    rep = check(facts(tmp_path, usdjpy=(157.185, "JPY=X", 1)))
    assert field_lines(rep)[0].startswith(level + ": ")
    assert said in field_lines(rep)[0]


# -- the fetch cap ----------------------------------------------------------

def test_the_second_request_is_counted_against_the_fetch_cap(
        tmp_path, provider):
    """--max-fetch bounds what the check asks the provider. With the one
    request it allows spent on the daily bar, the hourly bars are not asked
    for, and that is a FAIL that says so."""
    rep = check(facts(tmp_path, usdjpy=(157.185, "JPY=X", 1)), max_fetch=1)
    assert rep.counts["FAIL"] == 1
    assert field_lines(rep) == [
        "FAIL: facts: cross_asset.usdjpy 157.185 vs live 158.811 "
        "(JPY=X 2026-09-25, dev 1.03% > 1%) -- canonical table disagrees "
        "with market data. A currency pair's daily bar is not where its "
        "session ended, and its hourly bars, which say where, were not "
        "asked for: fetch cap 1 reached."]
    assert provider.asked("60m") == []


def test_the_check_never_asks_more_than_the_cap(tmp_path, provider):
    """Two requests allowed: the pair takes both, and the field after it is
    skipped as any field past the cap is."""
    provider.daily["SPY"] = chart("ETF", [(utc(2026, 9, 25, 13), 742.0)],
                                  offset=-14400)
    rep = check(facts(tmp_path, usdjpy=(157.185, "JPY=X", 1),
                      spy=(742.0, "SPY", 1.5)), max_fetch=2)
    assert len(provider.calls) == 2
    assert [line.split(":")[0] for line in field_lines(rep)] == ["OK", "SKIP"]
    assert field_lines(rep)[1] == (
        "SKIP: facts: cross_asset.spy (fetch cap reached)")


# -- only a currency pair ---------------------------------------------------

@pytest.mark.parametrize("symbol, kind", [
    ("CL=F", "FUTURE"),
    ("DX-Y.NYB", "INDEX"),
    ("SPY", "ETF"),
    ("XOM", "EQUITY"),
    ("BTC-USD", "CRYPTOCURRENCY"),
    ("JPY=X", None),            # a response that does not say what it is
    ("JPY=X", "currency"),      # or says it in other words
])
def test_nothing_but_a_currency_pair_is_given_a_second_witness(
        tmp_path, provider, symbol, kind):
    """The daily close of every other kind is its session's, and a future's
    hourly bars can be another contract month's. So their FAIL is the line
    it always was, and the hourly bars are not asked for, though here they
    would have agreed with the table."""
    start = utc(2026, 9, 25, 4)
    provider.daily[symbol] = chart(kind, [(start - DAY, 101.0, 103.0),
                                          (start, 103.0, 100.0)],
                                   offset=-14400)
    provider.hourly[symbol] = chart(
        kind, [(start + i * HOUR, 97.0) for i in range(24)], offset=-14400)
    rep = check(facts(tmp_path, thing=(97.0, symbol, 2)))
    assert field_lines(rep) == [
        "FAIL: facts: cross_asset.thing 97.0 vs live 100.0 "
        "(%s 2026-09-25, dev 3.09%% > 2%%) -- canonical table disagrees "
        "with market data" % symbol]
    assert provider.asked("60m") == []


def test_a_pair_beside_other_fields_changes_only_its_own_line(
        tmp_path, provider):
    """The gate as the Monday Council runs it: several fields, one of them
    the pair. The others read as they did."""
    provider.daily["SPY"] = chart("ETF", [(utc(2026, 9, 25, 13), 742.0)],
                                  offset=-14400)
    provider.daily["CL=F"] = chart("FUTURE", [(utc(2026, 9, 25, 4), 92.41)],
                                   offset=-14400)
    rep = check(facts(tmp_path, spy=(742.0, "SPY", 1.5),
                      usdjpy=(157.185, "JPY=X", 1),
                      wti=(99.0, "CL=F", 3)))
    got = field_lines(rep)
    assert got[0] == ("OK: facts: cross_asset.spy 742.0 vs live 742.0 "
                      "(SPY 2026-09-25, dev 0.00% <= 1.5%)")
    assert got[1].startswith("OK: facts: cross_asset.usdjpy 157.185 vs live "
                             "157.185 (JPY=X 2026-09-25, close of its last "
                             "hourly bar")
    assert got[2] == ("FAIL: facts: cross_asset.wti 99.0 vs live 92.41 "
                      "(CL=F 2026-09-25, dev 6.66% > 3%) -- canonical table "
                      "disagrees with market data")
    assert sorted(c[:2] for c in provider.calls) == [
        ("CL=F", "1d"), ("JPY=X", "1d"), ("JPY=X", "60m"), ("SPY", "1d")]


# -- the bar, not its date --------------------------------------------------

def test_the_witness_is_asked_about_the_bar_not_about_its_date(
        tmp_path, provider):
    """yahoo_close() names a bar's date with one UTC offset, today's. A
    currency bar is stamped at London's midnight, which is 23:00 UTC until
    the clocks go back, so read with winter's offset the Friday bar of the
    week before is called Thursday. The hours asked for are the bar's own
    all the same, and the line gives the hourly bar's own time.

    The stamps are the real ones for Friday 2025-10-24, the last session
    before a clock change; the prices are made up."""
    fri = utc(2025, 10, 23, 23)
    provider.daily["JPY=X"] = chart(
        "CURRENCY", [(fri - DAY, 152.0, 152.0), (fri, 152.6, 152.6)],
        offset=0)
    provider.hourly["JPY=X"] = chart(
        "CURRENCY", [(fri - HOUR, 152.6)]
        + [(fri + i * HOUR, round(152.6 - 0.1 * i, 1)) for i in range(22)],
        offset=0)
    rep = check(facts(tmp_path, usdjpy=(150.5, "JPY=X", 1)))
    assert provider.asked("60m") == [("JPY=X", "60m", fri, fri + DAY)]
    assert rep.counts["FAIL"] == 0
    assert field_lines(rep) == [
        "OK: facts: cross_asset.usdjpy 150.5 vs live 150.5 "
        "(JPY=X 2025-10-23, close of its last hourly bar, 2025-10-24 20:00 "
        "UTC, dev 0.00% <= 1%). The daily bar's close 152.6 is 1.40% away: "
        "a currency pair's daily bar is not where its session ended."]


# -- the fetch itself -------------------------------------------------------

def test_the_last_close_is_the_latest_inside_the_bar_whatever_the_order(
        provider):
    """Bars before the daily bar begins and after it ends are another
    session's, and a row with no close is not a bar."""
    assert tc.yahoo_session_last("JPY=X", FRI) == (157.185,
                                                   "2026-09-25 21:00")
    assert provider.calls == [("JPY=X", "60m", FRI, FRI + DAY)]
    provider.hourly["JPY=X"] = chart(
        "CURRENCY", list(reversed(JPY_HOURLY)))
    assert tc.yahoo_session_last("JPY=X", FRI) == (157.185,
                                                   "2026-09-25 21:00")


def test_a_daily_bar_ends_where_the_next_one_begins(provider):
    """Thursday's bar: its last hourly close is the 22:00 UTC bar's,
    158.755. The bar that begins at 23:00 UTC, 158.839, is Friday's first,
    though it is still Thursday by the UTC date."""
    assert tc.yahoo_session_last("JPY=X", THU) == (158.755,
                                                   "2026-09-24 22:00")
    assert tc.yahoo_session_last("JPY=X", FRI)[0] == 157.185


def test_yahoo_close_remembers_the_bar_it_read(provider):
    """What check_facts hands the witness: the daily bar's own timestamp
    and the provider's word for the instrument."""
    assert tc.yahoo_close("JPY=X") == (158.811, "2026-09-25")
    assert tc._bar_cache == {"JPY=X": (FRI, "CURRENCY")}
    # and nothing at all for a symbol the provider has no bar for
    provider.daily["NOPE"] = chart("EQUITY", [])
    assert tc.yahoo_close("NOPE") == (None, None)
    assert "NOPE" not in tc._bar_cache


def test_the_tail_is_drawn_between_what_was_measured():
    """Six hours. In two years of sessions (2024-10-14 to 2026-10-05, both
    pairs) the last hourly bar of a whole one begins 20 hours into the
    daily bar at the earliest, and the one that stopped early, 2026-01-30,
    begins 15 in. Under four hours the constant refuses whole sessions; at
    nine it takes the broken one."""
    assert tc.BAR_SECONDS == DAY
    whole, broken = 20 * HOUR, 15 * HOUR
    assert whole >= tc.BAR_SECONDS - tc.SESSION_TAIL_SECONDS > broken
