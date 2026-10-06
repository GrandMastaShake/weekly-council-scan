"""Which session a committed instrument close belongs to.

The writer took the bar dated the Friday when the provider had one and the
last earlier bar when it did not, and the note recording the second case
never reached the committed file. 2026-08-28.json holds Thursday's 10-year,
VIX and dollar index under Friday's date. Three Friday-evening files hold
futures quotes read before settlement; one of them is the $95.47 WTI of
issue #110, the November contract's last trade under a date whose settled
front month was $100.30.

The numbers for dates that have happened are the committed ones and the
provider's as fetched 2026-10-05; a file dated after that, or a close a test
says is wrong on purpose, is what it says it is. The classes are pinned here
because each is a different claim about the file: a prior-session value is a
wrong date, a holiday stand-in is the documented rule, and "differs" is
neither.

No network: the provider history is injected.
"""
from __future__ import annotations

import datetime as dt
import json

import pytest

from conftest import ROOT, weekly_doc

import audit_instruments as ai  # noqa: E402  (conftest stubs the provider)

NOW = dt.datetime(2026, 10, 5, 3, 9, 57, tzinfo=dt.timezone.utc)

# symbol -> {date: (close, volume)}, raw from the provider.
TNX = {"2026-08-24": (4.704, 0), "2026-08-25": (4.639, 0),
       "2026-08-26": (4.664, 0), "2026-08-27": (4.672, 0),
       "2026-08-28": (4.72, 0)}
VIX = {"2026-08-26": (15.21, 0), "2026-08-27": (14.51, 0),
       "2026-08-28": (14.43, 0)}
DXY = {"2026-08-26": (99.17, 0), "2026-08-27": (99.16, 0),
       "2026-08-28": (99.70, 0), "2026-09-04": (99.16, 0)}
# The mark sat at 4.170 for sixteen sessions.
YY2 = {"2026-08-26": (4.17, 0), "2026-08-27": (4.17, 0),
       "2026-08-28": (4.17, 0)}
CL = {"2026-08-27": (83.53, 220113), "2026-08-28": (83.40, 167615)}
GC = {"2026-08-27": (4664.0, 140302), "2026-08-28": (4529.8999, 274603)}
SI = {"2026-08-27": (69.429, 23252), "2026-08-28": (66.995, 4329)}
AUG_28 = {"^TNX": TNX, "^VIX": VIX, "DX-Y.NYB": DXY, "2YY=F": YY2,
          "CL=F": CL, "GC=F": GC, "SI=F": SI}


def provider(histories):
    def fetch(symbol, start, end):
        return histories.get(symbol, {})
    return fetch


def week(as_of, rates=None, vol=None, commodities=None, fx=None, **extra):
    doc = weekly_doc(as_of, ["SPY"])
    for block, closes in (("rates", rates), ("vol", vol),
                          ("commodities", commodities), ("fx", fx)):
        doc[block] = {t: (c if isinstance(c, dict)
                          else {"close": c, "volume": None})
                      for t, c in (closes or {}).items()}
    doc.update(extra)
    return doc


def audit(panel, files, histories, now=NOW, panels=("weekly",)):
    repo = panel(files).parents[1]
    return ai.run_audit(repo, panels, provider(histories), now)


def found(result):
    return {f["instrument"]: f for f in result["findings"]}


# -- the three claims ----------------------------------------------------------

def test_a_close_equal_to_the_bar_dated_as_of_is_not_a_finding(panel):
    result = audit(panel, {"2026-08-28.json": week(
        "2026-08-28", rates={"US10Y": 4.72}, vol={"VIX": 14.43})},
        AUG_28)
    assert result["findings"] == []
    assert result["audited"]["panels"]["weekly"]["ok"] == 2


def test_the_file_that_holds_thursdays_ten_year(panel):
    """2026-08-28.json as committed: three index instruments one session
    early. The audit names the session each one actually is."""
    result = audit(panel, {"2026-08-28.json": week(
        "2026-08-28", rates={"US10Y": 4.672, "US2Y": 4.17},
        vol={"VIX": 14.51}, fx={"DXY": 99.16})}, AUG_28)
    got = found(result)
    assert set(got) == {"rates.US10Y", "vol.VIX", "fx.DXY"}
    for name in got:
        assert got[name]["class"] == "prior_session"
        assert got[name]["session"] == "2026-08-27"
    assert got["rates.US10Y"]["provider"]["close"] == 4.72
    assert got["rates.US10Y"]["symbol"] == "^TNX"


def test_the_prior_session_wins_over_a_later_coincidence(panel):
    """The dollar index closed at 99.16 on 08-27 and again on 09-04. The
    file dated 08-28 was not reading the future."""
    result = audit(panel, {"2026-08-28.json": week(
        "2026-08-28", fx={"DXY": 99.16})}, AUG_28)
    assert found(result)["fx.DXY"]["session"] == "2026-08-27"


def test_a_mark_that_did_not_move_is_not_called_a_prior_session(panel):
    """2YY=F printed 4.170 on the 27th and the 28th. Equal to both is equal
    to as_of; calling it stale would be a finding about nothing."""
    result = audit(panel, {"2026-08-28.json": week(
        "2026-08-28", rates={"US2Y": 4.17})}, AUG_28)
    assert result["findings"] == []


def test_a_holiday_stand_in_is_its_own_class(panel):
    """Good Friday. No bar is dated 2026-04-03, so Thursday's close under
    that date is the documented rule and not a wrong date -- but the file
    does not say which instruments it happened to, so it is still listed."""
    hist = {"^TNX": {"2026-04-01": (4.319, 0), "2026-04-02": (4.313, 0),
                     "2026-04-06": (4.335, 0)}}
    result = audit(panel, {"2026-04-03.json": week(
        "2026-04-03", rates={"US10Y": 4.313},
        session_note="Friday holiday; bars from 2026-04-02")}, hist)
    got = found(result)["rates.US10Y"]
    assert got["class"] == "holiday_stand_in"
    assert got["session"] == "2026-04-02"
    assert got["provider"] is None
    assert got["session_note"] == "Friday holiday; bars from 2026-04-02"


def test_a_stand_in_the_file_records_is_not_a_finding(panel):
    hist = {"^TNX": {"2026-04-02": (4.313, 0), "2026-04-06": (4.335, 0)}}
    doc = week("2026-04-03", rates={"US10Y": 4.313})
    doc["provenance"] = {"rates": {"US10Y": {
        "source": "yahoo", "fetched_at": "2026-04-04T13:20:00Z",
        "observed": "2026-04-02"}}}
    result = audit(panel, {"2026-04-03.json": doc}, hist)
    assert result["findings"] == []
    assert result["audited"]["panels"]["weekly"]["ok"] == 1


def test_a_recorded_date_that_is_not_the_session_is_still_a_finding(panel):
    hist = {"^TNX": {"2026-04-01": (4.319, 0), "2026-04-02": (4.313, 0)}}
    doc = week("2026-04-03", rates={"US10Y": 4.313})
    doc["provenance"] = {"rates": {"US10Y": {
        "source": "yahoo", "fetched_at": "2026-04-04T13:20:00Z",
        "observed": "2026-04-01"}}}
    got = found(audit(panel, {"2026-04-03.json": doc}, hist))["rates.US10Y"]
    assert got["class"] == "holiday_stand_in"
    assert got["recorded_observed"] == "2026-04-01"


def test_a_stand_in_is_never_matched_from_an_earlier_week(panel):
    """A close equal to last week's Friday is not a holiday rule at work.
    (No committed file does this; 4.44 is the real close of 2026-03-27.)"""
    hist = {"^TNX": {"2026-03-27": (4.44, 0), "2026-04-06": (4.335, 0)}}
    got = found(audit(panel, {"2026-04-03.json": week(
        "2026-04-03", rates={"US10Y": 4.44})}, hist))["rates.US10Y"]
    assert got["class"] == "other_session"
    assert got["session"] == "2026-03-27"


def test_the_wti_of_issue_110_equals_no_session(panel):
    """$95.47 with 300,567 contracts. The settled front month was $100.30 on
    112,698. The volumes are printed because they are what says the two
    numbers are different contracts."""
    hist = {"CL=F": {"2026-09-17": (101.91, 265972),
                     "2026-09-18": (100.30, 112698)}}
    result = audit(panel, {"2026-09-18.json": week(
        "2026-09-18",
        commodities={"WTI": {"close": 95.47, "volume": 300567}})}, hist)
    got = found(result)["commodities.WTI"]
    assert got["class"] == "differs"
    assert got["session"] is None
    assert got["committed"] == {"close": 95.47, "volume": 300567}
    assert got["provider"] == {"close": 100.3, "volume": 112698}
    line = ai.line_for(got)
    assert "-4.8300" in line and "vol 300567/112698" in line


def test_float32_noise_in_a_large_close_is_not_a_difference(panel):
    """Yahoo serves 4529.89990234375; the file holds 4529.8999."""
    hist = {"GC=F": {"2026-08-28": (4529.89990234375, 274603)}}
    result = audit(panel, {"2026-08-28.json": week(
        "2026-08-28",
        commodities={"GOLD": {"close": 4529.8999, "volume": 268759}})}, hist)
    assert result["findings"] == []


def test_the_writers_normalization_is_applied_to_the_provider(panel):
    """A legacy x10 yield feed and a zero volume read the way the writer
    would have written them."""
    hist = {"^TNX": {"2026-08-28": (47.2, 0)}}
    result = audit(panel, {"2026-08-28.json": week(
        "2026-08-28", rates={"US10Y": 4.72})}, hist)
    assert result["findings"] == []
    assert ai.normalize(47.2, 0, {"kind": "yield"}) == (4.72, None)


# -- what the audit must not claim ---------------------------------------------

def test_a_symbol_the_provider_does_not_answer_for_is_unverified(panel):
    """Not ok, and not a difference either."""
    def fetch(symbol, start, end):
        if symbol == "^TNX":
            raise OSError("timed out")
        return AUG_28.get(symbol, {})

    repo = panel({"2026-08-28.json": week(
        "2026-08-28", rates={"US10Y": 4.672}, vol={"VIX": 14.43})}
    ).parents[1]
    result = ai.run_audit(repo, ("weekly",), fetch, NOW)
    got = found(result)
    assert got["rates.US10Y"]["class"] == "unverified"
    assert "vol.VIX" not in got
    assert "^TNX" in result["audited"]["symbols"]["failed"]
    assert result["audited"]["panels"]["weekly"]["ok"] == 1


def test_a_session_too_recent_to_be_final_is_unverified(panel):
    """Friday evening the provider's own bar is still a live quote. Judging
    a file against it would report the file wrong for agreeing with the
    number that is about to change."""
    hist = {"CL=F": {"2026-10-02": (91.11, 337181)}}
    files = {"2026-10-02.json": week(
        "2026-10-02", commodities={"WTI": {"close": 90.0, "volume": 5}})}
    friday_evening = dt.datetime(2026, 10, 3, 1, 13, tzinfo=dt.timezone.utc)
    early = found(audit(panel, files, hist, now=friday_evening))
    assert early["commodities.WTI"]["class"] == "unverified"
    assert "not final before 2026-10-03T13:00Z" in \
        early["commodities.WTI"]["reason"]

    saturday = dt.datetime(2026, 10, 3, 13, 7, tzinfo=dt.timezone.utc)
    late = found(audit(panel, files, hist, now=saturday))
    assert late["commodities.WTI"]["class"] == "differs"


def test_no_bar_anywhere_near_the_date_is_unverified(panel):
    hist = {"^TNX": {"2026-03-27": (4.44, 0)}}
    got = found(audit(panel, {"2026-08-28.json": week(
        "2026-08-28", rates={"US10Y": 4.672})}, hist))["rates.US10Y"]
    assert got["class"] == "unverified"


def test_another_publishers_number_is_not_audited_against_yahoo(panel):
    """Once US2Y is the Treasury 2-year, comparing it with 2YY=F would
    report the fix as the defect."""
    doc = week("2026-10-09", rates={"US2Y": 4.83})
    doc["provenance"] = {"rates": {"US2Y": {
        "source": "treasury", "fetched_at": "2026-10-10T13:20:00Z"}}}
    hist = {"2YY=F": {"2026-10-08": (4.61, 0), "2026-10-09": (4.635, 0)}}
    result = audit(panel, {"2026-10-09.json": doc}, hist,
                   now=dt.datetime(2026, 10, 12, tzinfo=dt.timezone.utc))
    assert result["findings"] == []
    assert result["audited"]["panels"]["weekly"]["closes"] == 0


def test_an_unlabelled_us2y_is_the_future_and_is_audited_as_one(panel):
    hist = {"2YY=F": {"2026-09-17": (4.404, 0), "2026-09-18": (4.416, 0)}}
    got = found(audit(panel, {"2026-09-18.json": week(
        "2026-09-18", rates={"US2Y": 4.404})}, hist))["rates.US2Y"]
    assert got["class"] == "prior_session"
    assert got["symbol"] == "2YY=F"


def test_a_missing_us2y_beside_the_future_is_not_filled_from_the_future(
        panel, monkeypatch):
    """After the cutover a week whose Treasury fetch failed lists US2Y in
    missing and carries the future as US2Y_FUT. The future having a bar is
    not the 2-year being available."""
    rates = ai.snapshot_macro.INSTRUMENTS["rates"]
    monkeypatch.setitem(rates, "US2Y", {"provider": "treasury",
                                        "column": "2 Yr", "kind": "yield"})
    monkeypatch.setitem(rates, "US2Y_FUT",
                        {"symbol": "2YY=F", "divisor": 1.0, "kind": "yield"})
    doc = week("2026-10-09", rates={"US2Y_FUT": 4.635})
    doc["missing"] = [{"ticker": "US2Y", "reason": "treasury: timed out"}]
    hist = {"2YY=F": {"2026-10-09": (4.635, 0)}}
    result = audit(panel, {"2026-10-09.json": doc}, hist,
                   now=dt.datetime(2026, 10, 12, tzinfo=dt.timezone.utc))
    assert result["findings"] == []


# -- absent --------------------------------------------------------------------

def test_an_instrument_the_file_lost_and_the_provider_has(panel):
    """VIX, 2025-03-14: 'no data returned for window 2025-03-09..'. The
    window opened on the Sunday the clocks went forward."""
    doc = week("2025-03-14", rates={"US10Y": 4.308})
    doc["missing"] = [{"ticker": "VIX", "reason":
                       "no data returned for window 2025-03-09..2025-03-16"}]
    hist = {"^VIX": {"2025-03-13": (24.66, 0), "2025-03-14": (21.77, 0)},
            "^TNX": {"2025-03-14": (4.308, 0)}}
    got = found(audit(panel, {"2025-03-14.json": doc}, hist))
    assert got["vol.VIX"]["class"] == "absent"
    assert got["vol.VIX"]["provider"]["close"] == 21.77
    assert "2025-03-09" in got["vol.VIX"]["reason"]


def test_an_instrument_the_file_never_carried_is_not_absent(panel):
    """A bootstrap daily file lists '*' and fetched no instrument at all."""
    doc = week("2026-08-28")
    doc["cadence"] = "daily"
    doc["missing"] = [{"ticker": "*", "reason":
                       "bootstrap backfill: special instruments not fetched"}]
    repo = panel({}).parents[1]
    daily = repo / "data" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-08-28.json").write_text(json.dumps(doc), encoding="utf-8")
    result = ai.run_audit(repo, ("daily",), provider(AUG_28), NOW)
    assert result["findings"] == []


# -- declined before settlement ------------------------------------------------

# Monday 2026-10-05, the first daily file under the rule: fetched at 01:54
# UTC on the 6th, eleven hours before its futures and the dollar index may
# be read. The audit listed all five under NEW.
OCT_5 = {"^VIX": {"2026-10-05": (15.9, 0)},
         "DX-Y.NYB": {"2026-10-05": (102.17, 0)},
         "2YY=F": {"2026-10-05": (4.638, 0)},
         "CLX26.NYM": {"2026-10-05": (89.43, 355302)}}
LATER = dt.datetime(2026, 10, 7, 12, 0, tzinfo=dt.timezone.utc)
EVENING = "2026-10-06T01:54:33Z"
AFTER_THE_HOUR = "2026-10-06T13:07:00Z"


def session_file(fetched_at, lost=("DXY", "US2Y_FUT", "WTI"), vol=None):
    """A session file as the daily job writes it: VIX read, and the
    instruments that settle the next day in `missing`."""
    doc = week("2026-10-05", vol={"VIX": 15.9} if vol is None else vol)
    doc["cadence"] = "daily"
    doc["fetched_at"] = fetched_at
    doc["missing"] = [{"ticker": t, "reason": "not read before 13:00Z"}
                      for t in lost]
    return doc


def daily_audit(panel, doc, histories=OCT_5, now=LATER):
    repo = panel({}).parents[1]
    daily = repo / "data" / "daily"
    daily.mkdir(parents=True, exist_ok=True)
    (daily / (doc["as_of"] + ".json")).write_text(json.dumps(doc),
                                                  encoding="utf-8")
    return ai.run_audit(repo, ("daily",), provider(histories), now)


def test_a_daily_file_fetched_before_the_hour_is_counted_not_listed(panel):
    """Declined, not lost. Nothing for a reviewer to put a cause to, and
    nothing that reads as ok either: the three are not among the compared."""
    result = daily_audit(panel, session_file(EVENING))
    counts = result["audited"]["panels"]["daily"]
    assert result["findings"] == []
    assert counts[ai.BEFORE_SETTLEMENT] == 3
    assert counts["absent"] == 0
    assert (counts["closes"], counts["ok"]) == (1, 1)       # VIX


def test_the_same_file_fetched_after_the_hour_lost_them(panel):
    """The reason in `missing` is the same text. The stamp is what differs,
    and a file fetched when the bar could be read has no rule to point at."""
    result = daily_audit(panel, session_file(AFTER_THE_HOUR))
    got = found(result)
    assert set(got) == {"fx.DXY", "rates.US2Y_FUT", "commodities.WTI"}
    assert {f["class"] for f in got.values()} == {"absent"}
    assert got["commodities.WTI"]["symbol"] == "CLX26.NYM"
    assert result["audited"]["panels"]["daily"][ai.BEFORE_SETTLEMENT] == 0


def test_a_weekly_file_fetched_before_the_hour_is_still_listed(panel):
    """The weekly job runs after the hour. A file in this state is a run
    that started early, and it can never be completed."""
    doc = week("2026-10-09", vol={"VIX": 16.2})
    doc["fetched_at"] = "2026-10-10T01:13:00Z"
    doc["missing"] = [{"ticker": "DXY", "reason": "not read before 13:00Z"}]
    hist = {"^VIX": {"2026-10-09": (16.2, 0)},
            "DX-Y.NYB": {"2026-10-09": (101.5, 0)}}
    result = audit(panel, {"2026-10-09.json": doc}, hist,
                   now=dt.datetime(2026, 10, 12, tzinfo=dt.timezone.utc))
    assert found(result)["fx.DXY"]["class"] == "absent"
    assert result["audited"]["panels"]["weekly"][ai.BEFORE_SETTLEMENT] == 0


def test_an_instrument_that_is_final_by_evening_is_never_counted(panel):
    """VIX does not settle the next day. Missing from an evening file, it
    was lost."""
    doc = session_file(EVENING, lost=("VIX",), vol={})
    result = daily_audit(panel, doc)
    assert found(result)["vol.VIX"]["class"] == "absent"
    assert result["audited"]["panels"]["daily"][ai.BEFORE_SETTLEMENT] == 0


@pytest.mark.parametrize("stamp", [None, "", "2026-10-06", "yesterday", 20261006])
def test_a_stamp_that_cannot_be_read_is_not_an_early_one(panel, stamp):
    doc = session_file(EVENING, lost=("DXY",))
    doc["fetched_at"] = stamp
    result = daily_audit(panel, doc)
    assert found(result)["fx.DXY"]["class"] == "absent"
    assert result["audited"]["panels"]["daily"][ai.BEFORE_SETTLEMENT] == 0


def test_the_report_gives_the_count_and_calls_nothing_new(panel):
    result = daily_audit(panel, session_file(EVENING))
    text, (new, changed, gone, known) = ai.render(
        result, {"findings": []}, False, ("daily",))
    assert (new, changed, gone, known) == ([], [], [], [])
    line = [ln for ln in text.splitlines() if ai.BEFORE_SETTLEMENT in ln]
    assert len(line) == 1 and " 3 " in line[0]
    assert "0 new" in text and "NEW" not in text.replace("0 new", "")


def test_the_history_window_never_opens_on_a_sunday(panel):
    asked = []

    def fetch(symbol, start, end):
        asked.append(start)
        return {}

    repo = panel({"2025-03-14.json": week("2025-03-14")}).parents[1]
    ai.run_audit(repo, ("weekly",), fetch, NOW)
    assert asked and all(
        dt.date.fromisoformat(s).weekday() == 0 for s in asked)


# -- corrections ---------------------------------------------------------------

def test_a_base_file_behind_a_correction_says_so(panel):
    base = week("2026-08-28", rates={"US10Y": 4.672})
    fixed = week("2026-08-28", rates={"US10Y": 4.72})
    fixed["corrects"] = "2026-08-28.json"
    fixed["reason"] = "US10Y held the 2026-08-27 close"
    result = audit(panel, {"2026-08-28.json": base,
                           "2026-08-28.corrected.json": fixed}, AUG_28)
    assert [f["file"] for f in result["findings"]] == ["2026-08-28.json"]
    assert result["findings"][0]["superseded_by"] == \
        "2026-08-28.corrected.json"


# -- the baseline --------------------------------------------------------------

def run_twice(panel, first, second):
    files = {"2026-08-28.json": week("2026-08-28", **first)}
    before = audit(panel, files, AUG_28)
    files = {"2026-08-28.json": week("2026-08-28", **second)}
    after = audit(panel, files, AUG_28)
    return before, after


def test_a_finding_on_file_is_known_and_a_fresh_one_is_new(panel):
    before, after = run_twice(
        panel, {"rates": {"US10Y": 4.672}},
        {"rates": {"US10Y": 4.672}, "vol": {"VIX": 14.51}})
    new, changed, gone, known = ai.compare(before, after)
    assert [f["instrument"] for f in new] == ["vol.VIX"]
    assert [f["instrument"] for f in known] == ["rates.US10Y"]
    assert changed == [] and gone == []


def test_a_finding_that_no_longer_reproduces_is_gone(panel):
    before, after = run_twice(panel, {"rates": {"US10Y": 4.672}},
                              {"rates": {"US10Y": 4.72}})
    new, changed, gone, known = ai.compare(before, after)
    assert [f["instrument"] for f in gone] == ["rates.US10Y"]
    assert new == [] and known == []


def test_a_provider_that_restated_again_is_changed_not_known(panel):
    files = {"2026-08-28.json": week("2026-08-28", rates={"US10Y": 4.672})}
    before = audit(panel, files, AUG_28)
    moved = dict(AUG_28, **{"^TNX": dict(TNX, **{"2026-08-28": (4.73, 0)})})
    after = audit(panel, files, moved)
    new, changed, gone, known = ai.compare(before, after)
    assert len(changed) == 1 and new == [] and known == []
    assert changed[0][1]["provider"]["close"] == 4.73


def test_an_unanswered_symbol_does_not_erase_what_is_on_file(panel):
    """The provider not answering today says nothing about last month."""
    files = {"2026-08-28.json": week("2026-08-28", rates={"US10Y": 4.672})}
    before = audit(panel, files, AUG_28)
    after = audit(panel, files, {})
    new, changed, gone, known = ai.compare(before, after)
    assert new == [] and changed == [] and gone == []
    assert known[0]["class"] == "prior_session"


def test_write_keeps_the_hand_written_keys(tmp_path, panel):
    files = {"2026-08-28.json": week("2026-08-28", rates={"US10Y": 4.672})}
    result = audit(panel, files, AUG_28)
    path = tmp_path / "macro" / "instrument_audit.json"
    previous = {"_purpose": "kept", "causes": {"prior_session": {}},
                "findings": [], "audited": {}}
    ai.write_baseline(path, result, previous)
    doc = json.loads(path.read_bytes().decode("ascii"))
    assert doc["_purpose"] == "kept"
    assert doc["causes"] == {"prior_session": {}}
    assert len(doc["findings"]) == 1
    assert doc["audited"]["fetched_at"] == "2026-10-05T03:09:57Z"


def test_a_cause_survives_a_rewrite_only_while_the_finding_is_the_same(
        tmp_path, panel):
    """A cause is a reviewer's statement about one finding. If the provider
    moves its number, what was reviewed is no longer what is on file."""
    path = tmp_path / "macro" / "instrument_audit.json"
    files = {"2026-08-28.json": week("2026-08-28", rates={"US10Y": 4.672},
                                     vol={"VIX": 14.51})}
    first = audit(panel, files, AUG_28)
    ai.write_baseline(path, first, {"causes": {"prior_session": {}}})
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert [f["cause"] for f in doc["findings"]] == [None, None]
    assert len(ai.unreviewed(doc)) == 2

    for f in doc["findings"]:
        f["cause"] = "prior_session"
    assert ai.unreviewed(doc) == []

    moved = dict(AUG_28, **{"^TNX": dict(TNX, **{"2026-08-28": (4.73, 0)})})
    ai.write_baseline(path, audit(panel, files, moved), doc)
    again = {f["instrument"]: f["cause"] for f in json.loads(
        path.read_text(encoding="utf-8"))["findings"]}
    assert again == {"rates.US10Y": None, "vol.VIX": "prior_session"}


def test_the_baseline_is_one_line_per_finding_and_reads_back_whole(
        tmp_path, panel):
    files = {"2026-08-28.json": week("2026-08-28", rates={"US10Y": 4.672},
                                     vol={"VIX": 14.51}, fx={"DXY": 99.16})}
    result = audit(panel, files, AUG_28)
    path = tmp_path / "macro" / "instrument_audit.json"
    ai.write_baseline(path, result, {"causes": {"x": {"what": "y"}}})
    text = path.read_bytes().decode("ascii")
    assert "\r" not in text and text.endswith("]\n}\n")
    doc = json.loads(text)
    assert list(doc)[-1] == "findings" and len(doc["findings"]) == 3
    rows = [line for line in text.splitlines() if '"panel"' in line]
    assert len(rows) == 3
    assert ai.dump_baseline(doc) == text, "a rewrite of nothing is no diff"

    empty = audit(panel, {"2026-08-28.json": week("2026-08-28")}, AUG_28)
    ai.write_baseline(path, empty, None)
    assert json.loads(path.read_text(encoding="utf-8"))["findings"] == []


def test_the_first_baseline_explains_itself(tmp_path, panel):
    result = audit(panel, {"2026-08-28.json": week("2026-08-28")}, AUG_28)
    path = tmp_path / "macro" / "instrument_audit.json"
    ai.write_baseline(path, result, None)
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert "never edited" in doc["_purpose"]
    assert "--write" in doc["_regenerate"]


# -- the committed baseline against the committed panel ------------------------

def committed_baseline():
    path = ROOT.joinpath(*ai.BASELINE)
    if not path.is_file():
        pytest.skip("no committed baseline")
    return json.loads(path.read_bytes().decode("ascii"))


def test_every_baseline_finding_quotes_the_file_it_names():
    """The baseline is evidence about committed files. An entry whose
    committed close is not the one in the file is evidence about nothing."""
    for f in committed_baseline()["findings"]:
        path = ROOT / "data" / f["panel"] / f["file"]
        assert path.is_file(), f["file"]
        doc = json.loads(path.read_text(encoding="utf-8"))
        block, ticker = f["instrument"].split(".")
        entry = (doc.get(block) or {}).get(ticker)
        if f["class"] == "absent":
            assert entry is None
            assert any(m["ticker"] == ticker for m in doc["missing"])
        else:
            assert entry is not None, (f["file"], f["instrument"])
            assert entry["close"] == f["committed"]["close"]
        assert f["file"].startswith(doc["as_of"])


def test_the_baseline_names_only_known_classes():
    doc = committed_baseline()
    assert {f["class"] for f in doc["findings"]} <= set(ai.CLASSES)
    assert doc["findings"] == sorted(doc["findings"], key=ai._key)


def test_every_finding_on_file_has_a_cause_and_every_cause_is_used():
    """A baseline entry with no cause is a difference nobody looked at,
    filed where the audit will stop mentioning it."""
    doc = committed_baseline()
    causes = doc["causes"]
    assert ai.unreviewed(doc) == []
    assert {f["cause"] for f in doc["findings"]} == set(causes)
    for name, cause in causes.items():
        assert cause["what"] and cause["evidence"] and cause["resolution"], name
