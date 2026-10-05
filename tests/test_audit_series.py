"""Which session a committed equity bar belongs to.

backfill_weekly.py::slice_week took the last bar on or before the Friday,
anywhere in the Mon..Fri week, and could only say so for a whole file. A
ticker with no Friday bar carried an earlier session under the Friday date,
unmarked. The audit asks every committed bar which session it is.

It cannot ask by comparing levels: a committed close is an adjusted close as
of its fetch date, and differs from today's for every name that has paid a
dividend or split since. So it asks twice, of things that do not move:
volume, and the close once the provider's own adjustment factor for the
fetch date has been divided out.

The numbers for dates that have happened are the committed ones and the
provider's as fetched 2026-10-05, as (adj close, close, volume, split). A
bar a test says is wrong on purpose is what the test says it is.

No network: the provider history is injected.
"""
from __future__ import annotations

import datetime as dt
import json

import pytest

from conftest import ROOT, weekly_doc

import audit_series as asr  # noqa: E402  (conftest stubs the provider)

NOW = dt.datetime(2026, 10, 5, 15, 36, 30, tzinfo=dt.timezone.utc)
BACKFILL = "2026-08-12T03:09:14Z"       # 104 files; 23:09 ET on the 11th
MERGE_44 = "2026-08-26T04:24:20Z"       # the 44 names added afterwards
MERGE_270 = "2026-08-27T14:02:49Z"      # 270 names into 2024-08-09.json

# Went ex 1.16 on 2026-08-12, the backfill's own fetch date.
TGT = {
    "2026-07-27": (139.27101135253906, 140.33999633789062, 3039300, 0.0),
    "2026-07-28": (143.10162353515625, 144.1999969482422, 4621700, 0.0),
    "2026-07-29": (144.78866577148438, 145.89999389648438, 3198400, 0.0),
    "2026-07-30": (143.4092559814453, 144.50999450683594, 2627500, 0.0),
    "2026-07-31": (143.38941955566406, 144.49000549316406, 3312000, 0.0),
    "2026-08-10": (150.862060546875, 152.02000427246094, 5256500, 0.0),
    "2026-08-11": (151.12998962402344, 152.2899932861328, 4171400, 0.0),
    "2026-08-12": (154.0, 154.0, 4601300, 0.0),
    "2026-08-13": (155.50999450683594, 155.50999450683594, 3650200, 0.0),
}
# Went ex 0.67 on 2026-08-11, the session before it.
V = {
    "2026-07-30": (365.5908203125, 366.2699890136719, 8391400, 0.0),
    "2026-07-31": (365.4510803222656, 366.1300048828125, 7828400, 0.0),
    "2026-08-10": (360.6500244140625, 361.32000732421875, 7552200, 0.0),
    "2026-08-11": (362.82000732421875, 362.82000732421875, 4440900, 0.0),
    "2026-08-12": (359.4200134277344, 359.4200134277344, 3794200, 0.0),
}
# Went ex 0.25 on 2026-09-10, a month after it.
NVDA = {
    "2026-03-30": (164.79331970214844, 165.1699981689453, 185627000, 0.0),
    "2026-03-31": (174.00225830078125, 174.39999389648438, 226181300, 0.0),
    "2026-04-01": (175.34918212890625, 175.75, 168132000, 0.0),
    "2026-04-02": (176.98545837402344, 177.38999938964844, 143143200, 0.0),
    "2026-04-06": (177.23487854003906, 177.63999938964844, 107564300, 0.0),
    "2026-07-30": (194.82199096679688, 195.0399932861328, 129010200, 0.0),
    "2026-07-31": (200.52561950683594, 200.75, 139961200, 0.0),
    "2026-08-11": (217.25689697265625, 217.5, 101273100, 0.0),
    "2026-08-12": (223.8395233154297, 224.08999633789062, 108783600, 0.0),
    "2026-10-01": (230.86000061035156, 230.86000061035156, 98591400, 0.0),
    "2026-10-02": (233.9499969482422, 233.9499969482422, 134914600, 0.0),
}
# Went ex 0.43 on 2026-08-27, the day its 2024-08-09 bar was merged in.
XYL = {
    "2024-08-07": (123.27558898925781, 126.83000183105469, 1121300, 0.0),
    "2024-08-08": (124.73355102539062, 128.3300018310547, 1020200, 0.0),
    "2024-08-09": (124.98626708984375, 128.58999633789062, 909800, 0.0),
    "2026-08-25": (112.38230895996094, 112.80999755859375, 2231400, 0.0),
    "2026-08-26": (112.98999786376953, 113.41999816894531, 1451200, 0.0),
    "2026-08-27": (112.6500015258789, 112.6500015258789, 2105400, 0.0),
    "2026-08-28": (111.30999755859375, 111.30999755859375, 1458900, 0.0),
}
# Split 2:1 on 2026-08-11. The provider's history was still on the old basis
# on the 12th, and on the 27th.
MNST = {
    "2024-08-08": (22.5049991607666, 22.5049991607666, 54646200, 0.0),
    "2024-08-09": (23.030000686645508, 23.030000686645508, 29237600, 0.0),
    "2026-07-30": (48.82500076293945, 48.82500076293945, 13081800, 0.0),
    "2026-07-31": (48.189998626708984, 48.189998626708984, 7765200, 0.0),
    "2026-08-06": (47.08000183105469, 47.08000183105469, 13658800, 0.0),
    "2026-08-07": (45.18000030517578, 45.18000030517578, 17009600, 0.0),
    "2026-08-10": (45.71500015258789, 45.71500015258789, 11943600, 0.0),
    "2026-08-11": (45.529998779296875, 45.529998779296875, 9579000, 2.0),
    "2026-08-12": (45.97999954223633, 45.97999954223633, 8544900, 0.0),
    "2026-08-13": (46.68000030517578, 46.68000030517578, 9858700, 0.0),
    "2026-08-14": (46.81999969482422, 46.81999969482422, 7930700, 0.0),
    "2026-08-26": (47.810001373291016, 47.810001373291016, 6220800, 0.0),
    "2026-08-27": (46.70000076293945, 46.70000076293945, 7431000, 0.0),
    "2026-10-01": (42.13999938964844, 42.13999938964844, 10073000, 0.0),
    "2026-10-02": (42.939998626708984, 42.939998626708984, 7745400, 0.0),
}
# Split 2:1 on 2026-09-03, after every backfilled file was fetched.
APH = {
    "2026-07-30": (79.7862548828125, 79.91000366210938, 21527600, 0.0),
    "2026-07-31": (80.22557067871094, 80.3499984741211, 18559800, 0.0),
    "2026-08-11": (83.48551177978516, 83.61499786376953, 7905400, 0.0),
    "2026-08-12": (84.84840393066406, 84.9800033569336, 10446400, 0.0),
    "2026-09-02": (79.91605377197266, 80.04000091552734, 13283400, 0.0),
    "2026-09-03": (81.94290924072266, 82.06999969482422, 10184600, 2.0),
}
# EQR until 2026-08-17. The provider serves its history under this symbol.
VMRK = {
    "2026-08-03": (67.56999969482422, 67.56999969482422, 2640100, 0.0),
    "2026-08-04": (67.69000244140625, 67.69000244140625, 2201500, 0.0),
    "2026-08-05": (67.73999786376953, 67.73999786376953, 2399700, 0.0),
    "2026-08-06": (66.69999694824219, 66.69999694824219, 1900700, 0.0),
    "2026-08-07": (67.06999969482422, 67.06999969482422, 2136000, 0.0),
    "2026-08-10": (65.83000183105469, 65.83000183105469, 1875900, 0.0),
    "2026-08-11": (65.08999633789062, 65.08999633789062, 2283700, 0.0),
    "2026-08-12": (64.41999816894531, 64.41999816894531, 7042800, 0.0),
    "2026-08-13": (65.97000122070312, 65.97000122070312, 4154300, 0.0),
    "2026-08-14": (65.97000122070312, 65.97000122070312, 7322800, 0.0),
}
# Closed at 18.90 on both the Thursday and the Friday.
AES = {
    "2024-09-18": (17.321205139160156, 19.260000228881836, 10658500, 0.0),
    "2024-09-19": (16.9974422454834, 18.899999618530273, 13604000, 0.0),
    "2024-09-20": (16.9974422454834, 18.899999618530273, 19704200, 0.0),
    "2026-08-11": (14.699999809265137, 14.699999809265137, 3722000, 0.0),
    "2026-08-12": (14.710000038146973, 14.710000038146973, 4491500, 0.0),
}
# Went ex 0.62 on Friday 2026-08-14; the file for that Friday was fetched on
# the Saturday.
SBUX = {
    "2026-08-12": (107.8703384399414, 108.48999786376953, 3924100, 0.0),
    "2026-08-13": (107.93000030517578, 108.55000305175781, 5190000, 0.0),
    "2026-08-14": (107.69000244140625, 107.69000244140625, 3499100, 0.0),
    "2026-08-17": (107.91999816894531, 107.91999816894531, 5935300, 0.0),
}
# Closed at 57.84 on Friday 2024-08-09 and again on the Monday after.
C = {
    "2024-08-08": (55.106040954589844, 58.0, 17933300, 0.0),
    "2024-08-09": (54.954017639160156, 57.84000015258789, 11421000, 0.0),
    "2024-08-12": (54.954017639160156, 57.84000015258789, 15123500, 0.0),
    "2026-08-26": (133.55999755859375, 133.55999755859375, 4543300, 0.0),
    "2026-08-27": (132.67999267578125, 132.67999267578125, 11622100, 0.0),
}
COST = {
    "2026-09-23": (904.7000122070312, 904.7000122070312, 2280700, 0.0),
    "2026-09-24": (896.47998046875, 896.47998046875, 2893300, 0.0),
    "2026-09-25": (922.77001953125, 922.77001953125, 4629300, 0.0),
    "2026-09-28": (922.9199829101562, 922.9199829101562, 2443800, 0.0),
}
# Of a delisted symbol the provider keeps one bar, the last. EA was taken
# private and last traded on Tuesday 2026-08-04. AVB was merged away after
# 2026-08-14 at 2.793 shares of the survivor, which the provider records as
# a split.
EA = {"2026-08-04": (209.6999969482422, 209.6999969482422, 48430629, 0.0)}
AVB = {"2026-08-14": (184.05999755859375, 184.05999755859375, 2468994,
                      2.793)}
PROVIDER = {"TGT": TGT, "V": V, "NVDA": NVDA, "XYL": XYL, "MNST": MNST,
            "APH": APH, "VMRK": VMRK, "AES": AES, "SBUX": SBUX, "C": C,
            "COST": COST, "EA": EA, "AVB": AVB}
SATURDAY = "2026-08-15T13:45:42Z"       # the Friday job, the morning after


def provider(histories):
    def fetch(symbols, start, end):
        return {s: histories[s] for s in symbols if s in histories}
    return fetch


def week(as_of, series, source="yahoo-backfill", fetched_at=BACKFILL,
         **extra):
    doc = weekly_doc(as_of, [], source=source, fetched_at=fetched_at)
    doc["series"] = {t: {"close": c, "volume": v}
                     for t, (c, v) in series.items()}
    doc.update(extra)
    return doc


def audit(panel, files, histories=PROVIDER, now=NOW):
    repo = panel(files).parents[1]
    return asr.run_audit(repo, provider(histories), now)


def found(result):
    return {f["instrument"]: f for f in result["findings"]}


def on_file_basis(history, session, fetched_at=BACKFILL, which=0):
    """The bar slice_week would have committed for `session`: the provider's
    bar on the adjustment basis of that fetch, rounded as the writer rounds."""
    close, scale = asr.rebased(history, session,
                               asr.bases(history, fetched_at)[which])
    return round(close, 4), int(round(history[session][2] / scale))


# -- a bar that is the session the file names ----------------------------------

def test_a_bar_of_the_named_session_is_not_a_finding(panel):
    result = audit(panel, {"2026-07-31.json": week("2026-07-31", {
        "TGT": (144.49, 3312000), "V": (365.4511, 7828400),
        "NVDA": (200.75, 139961200)})})
    assert result["findings"] == []
    counts = result["audited"]["weekly"]
    assert counts["bars"] == counts["ok"] == 3
    assert counts["backfill"] == {"bars": 3, "ok": 3, "close_alone": 0}


def test_a_dividend_gone_ex_since_the_fetch_is_not_a_difference(panel):
    """NVDA is committed at 200.75 and the provider's adjusted close for the
    day is now 200.5256: it went ex 0.25 on 2026-09-10. Compared level to
    level this is a difference, and so are 19,916 of the 34,774 backfilled
    bars that are the right session."""
    assert NVDA["2026-07-31"][0] < 200.6
    result = audit(panel, {"2026-07-31.json": week(
        "2026-07-31", {"NVDA": (200.75, 139961200)})})
    assert result["findings"] == []


def test_a_dividend_that_went_ex_on_the_fetch_date(panel):
    """The backfill ran at 03:09 UTC on 2026-08-12. TGT went ex that day and
    the dividend was not in the history yet (144.49, the unadjusted close);
    V went ex on the 11th and it was (365.4511, adjusted). One rule has to
    pass both, so the factor of either session is accepted."""
    assert asr.bases(TGT, BACKFILL) == [("2026-08-11", ()), ("2026-08-12", ())]
    result = audit(panel, {"2026-07-31.json": week("2026-07-31", {
        "TGT": (144.49, 3312000), "V": (365.4511, 7828400)})})
    assert result["findings"] == []


def test_a_saturday_fetch_has_one_basis(panel):
    """SBUX went ex on Friday 2026-08-14 and the Friday job ran the next
    morning: the dividend was in the history, and the session before is not
    a basis the file can be on. Offered anyway, it would pass Thursday's
    unadjusted close as Friday's on the one day that matters: when the price
    fell by exactly the dividend."""
    assert asr.bases(SBUX, SATURDAY) == [("2026-08-14", ())]
    live = {"source": "yahoo", "fetched_at": SATURDAY}
    assert audit(panel, {"2026-08-14.json": week(
        "2026-08-14", {"SBUX": (107.69, 3499100)}, **live)})["findings"] == []

    # Constructed: the same week, had Friday closed 0.62 under Thursday.
    exact = dict(SBUX, **{"2026-08-14": (107.93000030517578,
                                         107.93000030517578, 3499100, 0.0)})
    got = found(audit(panel, {"2026-08-14.json": week(
        "2026-08-14", {"SBUX": (108.55, 5189900)}, **live)},
        dict(PROVIDER, SBUX=exact)))["series.SBUX"]
    assert got["class"] == "differs"
    assert got["provider"] == {"close": 107.93, "volume": 3499100}


def test_a_bar_is_never_adjusted_for_a_dividend_on_its_own_date():
    """On Thursday's basis Friday's bar is still Friday's own close: the
    dividend that went ex on Friday adjusts the days before it."""
    thursday, friday = ("2026-08-13", ()), ("2026-08-14", ())
    assert asr.rebased(SBUX, "2026-08-14", thursday) == \
        asr.rebased(SBUX, "2026-08-14", friday) == (SBUX["2026-08-14"][0], 1.0)
    assert round(asr.rebased(SBUX, "2026-08-13", thursday)[0], 2) == 108.55
    assert round(asr.rebased(SBUX, "2026-08-13", friday)[0], 2) == 107.93


def test_a_merged_name_is_judged_on_its_own_fetch_date(panel):
    """XYL's 2024-08-09 bar was merged in at 14:02 UTC on 2026-08-27, its
    ex-date, into a file stamped the day before. NVDA is the case that tells
    the two stamps apart: fetched after its September dividend it is 200.5256,
    which is no session's close on the file's own date."""
    doc = week("2024-08-09", {"XYL": (125.4619, 909800)},
               fetched_at=MERGE_44)
    doc["provenance"] = {"series": {"XYL": {
        "source": "yahoo-backfill", "fetched_at": MERGE_270}}}
    late = week("2026-07-31", {"NVDA": (200.5256, 139961200)})
    late["provenance"] = {"series": {"NVDA": {
        "source": "yahoo-backfill", "fetched_at": "2026-10-03T13:07:47Z"}}}
    result = audit(panel, {"2024-08-09.json": doc, "2026-07-31.json": late})
    assert result["findings"] == []
    assert result["audited"]["weekly"]["merged"]["ok"] == 2

    del late["provenance"]
    got = found(audit(panel, {"2026-07-31.json": late}))["series.NVDA"]
    assert got["class"] == "differs" and got["origin"] == "backfill"
    assert got["provider"] == {"close": 200.75, "volume": 139961200}


def test_a_split_after_the_fetch_scales_close_and_volume(panel):
    """APH split 2:1 on 2026-09-03. The file holds 160.70 on 9,279,900
    shares; the provider now says 80.23 on 18,559,800."""
    result = audit(panel, {"2026-07-31.json": week(
        "2026-07-31", {"APH": (160.7, 9279900)})})
    assert result["findings"] == []
    assert result["audited"]["weekly"]["backfill"]["close_alone"] == 0


def test_a_split_the_provider_had_not_carried_back_yet(panel):
    """MNST split on 2026-08-11. Fetched a day later, and sixteen days
    later, its history was still on the old basis; a bar dated after the
    split never needed adjusting."""
    merged = week("2024-08-09", {"MNST": (46.06, 14618800)},
                  fetched_at=MERGE_44)
    merged["provenance"] = {"series": {"MNST": {
        "source": "yahoo-backfill", "fetched_at": MERGE_270}}}
    result = audit(panel, {
        "2026-07-31.json": week("2026-07-31", {"MNST": (96.38, 3882600)}),
        "2024-08-09.json": merged,
        "2026-08-14.json": week("2026-08-14", {"MNST": (46.82, 7929600)},
                                source="yahoo", fetched_at=SATURDAY)})
    assert result["findings"] == []
    counts = result["audited"]["weekly"]
    # The volume is on the old basis too, and fits as half the provider's.
    assert counts["backfill"] == {"bars": 1, "ok": 1, "close_alone": 0}
    assert counts["merged"] == {"bars": 1, "ok": 1, "close_alone": 0}
    assert counts["live"] == {"bars": 1, "ok": 1, "close_alone": 1}


def test_a_split_is_unsure_only_while_it_is_recent():
    """Just before the fetch, it may not have been in the history yet. Just
    before the provider's newest bar, it may not be in it even now. The
    likeliest basis comes first."""
    assert asr.bases(MNST, BACKFILL) == [
        ("2026-08-11", ()), ("2026-08-11", ("2026-08-11",)),
        ("2026-08-12", ()), ("2026-08-12", ("2026-08-11",))]
    assert asr.bases(MNST, "2026-10-03T13:07:47Z") == [("2026-10-02", ())]
    # APH's fixture ends on the day of its split, so that one is recent.
    assert asr.bases(APH, BACKFILL) == [
        ("2026-08-11", ("2026-09-03",)), ("2026-08-11", ()),
        ("2026-08-12", ("2026-09-03",)), ("2026-08-12", ())]
    assert asr._recent("2026-09-03", "2026-10-07")
    assert not asr._recent("2026-09-03", "2026-10-08")
    later = dict(APH, **{"2026-10-08": (80.0, 80.0, 1, 0.0)})
    assert {p for _, p in asr.bases(later, BACKFILL)} == {("2026-09-03",)}


def test_a_history_that_starts_after_the_fetch_has_no_basis():
    assert asr.bases(COST, BACKFILL) == []


def test_a_reverse_split_since_the_fetch_keeps_its_volume_witness(panel):
    """Constructed: a 1-for-10 after the fetch. The provider divides the old
    volumes by ten and rounds, and the committed 2,345,678 has to be found
    in its 234,568."""
    reverse = {
        "2026-07-30": (99.0, 99.0, 198765, 0.0),
        "2026-07-31": (101.0, 101.0, 234568, 0.0),
        "2026-08-11": (102.0, 102.0, 200000, 0.0),
        "2026-08-12": (103.0, 103.0, 200000, 0.0),
        "2026-09-03": (104.0, 104.0, 200000, 0.1),
        "2026-10-09": (105.0, 105.0, 200000, 0.0),
    }
    result = audit(panel, {"2026-07-31.json": week(
        "2026-07-31", {"TGT": (10.1, 2345678)})}, dict(PROVIDER, TGT=reverse),
        now=dt.datetime(2026, 10, 12, tzinfo=dt.timezone.utc))
    assert result["findings"] == []
    assert result["audited"]["weekly"]["backfill"]["close_alone"] == 0


def test_a_factor_day_with_no_price_ends_nothing(panel):
    """Constructed: an adjusted close of zero where the factor is read. The
    bar is unverified, the run goes on, and the reason is the right one."""
    broken = {d: (0.0, bar[1], bar[2], bar[3]) for d, bar in TGT.items()}
    result = audit(panel, {"2026-07-31.json": week("2026-07-31", {
        "TGT": (144.49, 3312000), "V": (365.4511, 7828400)})},
        dict(PROVIDER, TGT=broken))
    got = found(result)
    assert set(got) == {"series.TGT"}
    assert got["series.TGT"]["class"] == "unverified"
    assert "on or before the fetch date" in got["series.TGT"]["reason"]
    assert result["audited"]["weekly"]["ok"] == 1


def test_a_bar_with_no_fetch_time_is_unverified_for_that_reason(panel):
    doc = week("2026-07-31", {"TGT": (144.49, 3312000)})
    doc["fetched_at"] = None
    got = found(audit(panel, {"2026-07-31.json": doc}))["series.TGT"]
    assert got["class"] == "unverified"
    assert "on or before the fetch date" in got["reason"]


# -- the session the file names ------------------------------------------------

def test_a_holiday_file_names_its_session_in_the_note(panel):
    """Good Friday 2026. The whole file is Thursday's and says so."""
    result = audit(panel, {"2026-04-03.json": week(
        "2026-04-03", {"NVDA": (177.1835, 143143200)},
        session_note="Friday holiday; bars from 2026-04-02")})
    assert result["findings"] == []
    assert result["audited"]["weekly"]["named_by_note"] == 1


def test_thursdays_bar_with_no_note_is_a_stand_in(panel):
    got = found(audit(panel, {"2026-04-03.json": week(
        "2026-04-03", {"NVDA": (177.1835, 143143200)})}))["series.NVDA"]
    assert got["class"] == "stand_in"
    assert got["session"] == "2026-04-02"
    assert got["witnesses"] == "close+volume"
    assert got["provider"] is None


def test_in_a_holiday_file_a_bar_from_before_the_named_session(panel):
    wednesday = on_file_basis(NVDA, "2026-04-01")
    got = found(audit(panel, {"2026-04-03.json": week(
        "2026-04-03", {"NVDA": wednesday},
        session_note="Friday holiday; bars from 2026-04-02")}))["series.NVDA"]
    assert got["class"] == "prior_session"
    assert got["session"] == "2026-04-01"
    assert got["session_note"] == "Friday holiday; bars from 2026-04-02"


def test_a_note_that_names_no_date_leaves_as_of():
    assert asr.named_session({"as_of": "2026-04-03",
                              "session_note": "thin holiday trade"}) \
        == "2026-04-03"
    assert asr.named_session({"as_of": "2026-04-03"}) == "2026-04-03"


# -- what slice_week does to a ticker with no Friday bar -----------------------

def test_a_ticker_that_did_not_trade_on_the_friday_is_a_stand_in(panel):
    """Halted, or delisted mid-week: the provider has no bar for the day, and
    the file holds Thursday's under Friday's date."""
    thursday = on_file_basis(TGT, "2026-07-30")
    assert thursday == (144.51, 2627500)
    halted = {d: bar for d, bar in TGT.items() if d != "2026-07-31"}
    got = found(audit(panel, {"2026-07-31.json": week(
        "2026-07-31", {"TGT": thursday})},
        dict(PROVIDER, TGT=halted)))["series.TGT"]
    assert got["class"] == "stand_in"
    assert got["session"] == "2026-07-30"
    assert got["provider"] is None


def test_a_friday_bar_the_provider_did_not_have_yet_is_a_prior_session(
        panel):
    """A gap at fetch time that has since been filled: the provider has the
    Friday bar now, and the file holds the day before."""
    got = found(audit(panel, {"2026-07-31.json": week(
        "2026-07-31", {"TGT": (144.51, 2627500)})}))["series.TGT"]
    assert got["class"] == "prior_session"
    assert got["session"] == "2026-07-30"
    assert got["witnesses"] == "close+volume"
    assert got["provider"] == {"close": 144.49, "volume": 3312000}
    line = asr.line_for(got)
    assert "= 2026-07-30 by close+volume" in line and "+0.0200" in line


def test_every_earlier_session_of_the_week_would_have_been_caught(panel):
    """Whichever earlier bar slice_week had fallen back to, it is named, and
    what is shown beside it is Friday's bar on the basis that bar is on:
    144.49, never the 143.39 of the basis that happens to sit nearer."""
    for session in ("2026-07-27", "2026-07-28", "2026-07-29", "2026-07-30"):
        got = found(audit(panel, {"2026-07-31.json": week(
            "2026-07-31", {"TGT": on_file_basis(TGT, session)})}))
        assert got["series.TGT"]["class"] == "prior_session", session
        assert got["series.TGT"]["session"] == session
        assert got["series.TGT"]["provider"] == {
            "close": 144.49, "volume": 3312000}, session


def test_the_audit_measures_what_it_could_have_found(panel):
    """'None found' is worth what could have been found, so every run says:
    for each bar that passed, the session before it is put in its place and
    asked about. AES closed unchanged, so the close alone would pass it and
    only the volume names it. AVB's last bar has no session before it at
    the provider, and nothing to try."""
    result = audit(panel, {
        "2026-07-31.json": week("2026-07-31", {
            "TGT": (144.49, 3312000), "V": (365.4511, 7828400),
            "NVDA": (200.75, 139961200)}),
        "2024-09-20.json": week("2024-09-20", {"AES": (16.9974, 19704200)}),
        "2026-08-14.json": week("2026-08-14", {"AVB": (184.06, 2484400)},
                                source="yahoo", fetched_at=SATURDAY)})
    assert result["findings"] == []
    assert result["audited"]["weekly"]["ok"] == 5
    assert result["audited"]["weekly"]["reach"] == {
        "tried": 4, "named": 4, "blind_on_close": 1}
    assert asr.reach(184.06, "2026-08-14", "2026-08-14", AVB,
                     asr.bases(AVB, SATURDAY)) is None
    assert "is named 4 time(s)" in asr.render(result, None, False)[0]


def test_an_unchanged_close_is_told_apart_by_volume(panel):
    """AES closed at 18.90 on Thursday and again on Friday. The close cannot
    say which bar this is and does not need to; the volume can."""
    friday = audit(panel, {"2024-09-20.json": week(
        "2024-09-20", {"AES": (16.9974, 19704200)})})
    assert friday["findings"] == []
    assert friday["audited"]["weekly"]["backfill"]["close_alone"] == 0
    assert friday["audited"]["weekly"]["tied"] == 0

    got = found(audit(panel, {"2024-09-20.json": week(
        "2024-09-20", {"AES": (16.9974, 13604000)})}))["series.AES"]
    assert got["class"] == "prior_session"
    assert got["session"] == "2024-09-19"


def test_an_unchanged_close_with_no_volume_to_go_on_is_counted(panel):
    """The same AES bar with a volume that is neither day's. It passes,
    because 16.9974 is Friday's close, and it is counted apart, because it is
    Thursday's close too and nothing here says which bar it is."""
    result = audit(panel, {"2024-09-20.json": week(
        "2024-09-20", {"AES": (16.9974, 13603900)})})
    assert result["findings"] == []
    assert result["audited"]["weekly"]["backfill"]["close_alone"] == 1
    assert result["audited"]["weekly"]["tied"] == 1
    assert "1 of those on the close alone share that close" in \
        asr.render(result, None, False)[0]


def test_a_volume_that_fits_no_session_is_not_evidence_of_another_day(panel):
    """The live MNST bar of 2026-08-14 holds 7,929,600 shares where the
    provider now says 7,930,700: read the next morning, revised since. The
    close is Friday's and only Friday's."""
    result = audit(panel, {"2026-08-14.json": week(
        "2026-08-14", {"MNST": (46.82, 7929600)}, source="yahoo",
        fetched_at=SATURDAY)})
    assert result["findings"] == []
    assert result["audited"]["weekly"]["live"] == {
        "bars": 1, "ok": 1, "close_alone": 1}


def test_a_session_that_fits_both_beats_one_that_fits_the_close_alone(panel):
    """C closed at 57.84 on Friday 2024-08-09 and again on the Monday. With
    Friday's volume a little off, the close alone still makes it Friday's.
    With Monday's volume to the share it is Monday's bar, though the close
    is the same number and Monday is outside the week."""
    def one(volume):
        return audit(panel, {"2024-08-09.json": week(
            "2024-08-09", {"C": (54.954, volume)}, fetched_at=MERGE_270)})

    assert one(11421000)["findings"] == []
    restated = one(11420900)
    assert restated["findings"] == []
    assert restated["audited"]["weekly"]["backfill"]["close_alone"] == 1

    got = found(one(15123500))["series.C"]
    assert got["class"] == "other_session"
    assert got["session"] == "2024-08-12"
    assert got["witnesses"] == "close+volume"


def test_close_and_volume_naming_different_sessions_is_a_conflict(panel):
    """Friday's close on Wednesday's volume is not one bar. Not ok, and not
    a guess at which half to believe: no session is named, both are shown."""
    got = found(audit(panel, {"2026-07-31.json": week(
        "2026-07-31", {"TGT": (144.49, 3198400)})}))["series.TGT"]
    assert got["class"] == "conflict"
    assert got["session"] is None
    assert got["witnesses"] == \
        "close is 2026-07-31's, volume is 2026-07-29's"
    line = asr.line_for(got)
    assert "= 2026-07-31" not in line and "volume is 2026-07-29's" in line

    # Last Friday's close on this Friday's volume is no better.
    got = found(audit(panel, {"2026-08-14.json": week(
        "2026-08-14", {"EQR": (67.07, 7322800)}, source="yahoo",
        fetched_at=SATURDAY)}))["series.EQR"]
    assert got["class"] == "conflict"
    assert got["witnesses"] == \
        "close is 2026-08-07's, volume is 2026-08-14's"


def test_a_close_read_before_the_session_was_final_differs(panel):
    """2026-09-25.json was fetched at 18:14 ET on the day. COST is half a
    cent under the close the provider settled on, with a volume still short
    of the final count."""
    got = found(audit(panel, {"2026-09-25.json": week(
        "2026-09-25", {"COST": (922.765, 4602713)}, source="yahoo",
        fetched_at="2026-09-25T22:14:29Z")}))["series.COST"]
    assert got["class"] == "differs"
    assert got["session"] is None and got["origin"] == "live"
    assert got["provider"] == {"close": 922.77, "volume": 4629300}
    assert "(-0.0050, -0.001%)" in asr.line_for(got)


def test_no_bar_is_from_a_session_after_it_was_fetched(panel):
    """922.92 is COST's close of Monday 2026-09-28. In a file fetched the
    Friday evening before, it cannot be that bar, whatever it equals."""
    got = found(audit(panel, {"2026-09-25.json": week(
        "2026-09-25", {"COST": (922.92, 2443800)}, source="yahoo",
        fetched_at="2026-09-25T22:14:29Z")}))["series.COST"]
    assert got["class"] == "differs"
    assert got["session"] is None


def test_the_bar_of_a_session_outside_the_week_is_another_session(panel):
    """Last Friday's bar under this Friday's date. (No committed file does
    this; 67.07 on 2,136,000 is the real bar of 2026-08-07.)"""
    got = found(audit(panel, {"2026-08-14.json": week(
        "2026-08-14", {"EQR": (67.07, 2136000)}, source="yahoo",
        fetched_at=SATURDAY)}))["series.EQR"]
    assert got["class"] == "other_session"
    assert got["session"] == "2026-08-07"


# -- a ticker the provider no longer serves ------------------------------------

def test_a_renamed_ticker_is_audited_against_the_symbol_with_its_history(
        panel):
    asked = []

    def fetch(symbols, start, end):
        asked.extend(symbols)
        return {"VMRK": VMRK}

    repo = panel({"2026-08-07.json": week(
        "2026-08-07", {"EQR": (67.07, 2136000)})}).parents[1]
    result = asr.run_audit(repo, fetch, NOW)
    assert asked == ["VMRK"]
    assert result["findings"] == []
    assert result["audited"]["tickers"]["through_successor"] == {
        "EQR": "VMRK"}


def test_a_successor_is_not_taken_on_trust(panel):
    """Naming VMRK for EQR passes nothing by itself: Thursday's bar is still
    Thursday's."""
    got = found(audit(panel, {"2026-08-07.json": week(
        "2026-08-07", {"EQR": (66.7, 1900700)})}))["series.EQR"]
    assert got["class"] == "prior_session"
    assert got["session"] == "2026-08-06"
    assert got["symbol"] == "VMRK"


def test_the_one_the_backfill_did_commit(panel):
    """2026-08-07.json holds EA at 209.70 on no shares. The provider's one
    surviving EA bar is 209.70 on Tuesday 2026-08-04, its last session, and
    it has nothing for the Friday: a delisting mid-week, an earlier
    session's close under the Friday date, and no mark on it. Named by the
    close alone, because the volume in the file is not that bar's."""
    result = audit(panel, {"2026-08-07.json": week(
        "2026-08-07", {"EA": (209.7, 0)})})
    got = found(result)["series.EA"]
    assert got["class"] == "stand_in"
    assert got["session"] == "2026-08-04"
    assert got["witnesses"] == "close"
    assert got["provider"] is None
    assert result["audited"]["weekly"]["no_volume"] == ["2026-08-07.json EA"]
    line = asr.line_for(got)
    assert "NO VOLUME BEHIND IT" in line and "= 2026-08-04 by close" in line


def test_a_week_the_provider_no_longer_has_is_unverified(panel):
    """Every other EA week, and every backfilled AVB week: there is nothing
    in the week to compare the bar with. Not ok, and not a difference."""
    result = audit(panel, {
        "2026-07-17.json": week("2026-07-17", {"EA": (208.9, 3883020)}),
        "2026-08-07.json": week("2026-08-07", {"AVB": (187.55, 666100)})})
    assert [f["class"] for f in result["findings"]] == ["unverified"] * 2
    assert result["audited"]["weekly"]["ok"] == 0
    assert result["findings"][0]["reason"] == \
        "the provider has no EA bar in the file's week"


def test_the_last_bar_of_a_dead_ticker_can_still_be_checked(panel):
    """AVB's bar of 2026-08-14 is the one the provider kept. The print a
    week later, 65.9005 on no volume, has no bar to be checked against; it
    is that 184.06 divided by the 2.793."""
    result = audit(panel, {
        "2026-08-14.json": week("2026-08-14", {"AVB": (184.06, 2484400)},
                                source="yahoo", fetched_at=SATURDAY),
        "2026-08-21.json": week("2026-08-21", {"AVB": (65.9005, 0)},
                                source="yahoo",
                                fetched_at="2026-08-22T16:01:01Z")})
    assert [(f["file"], f["class"]) for f in result["findings"]] == [
        ("2026-08-21.json", "unverified")]
    assert result["audited"]["weekly"]["live"] == {
        "bars": 2, "ok": 1, "close_alone": 1}
    assert round(184.06 / 2.793, 4) == 65.9005


def test_a_ticker_the_provider_returns_nothing_for_is_unverified(panel):
    """Asked in a batch of fifty the provider had nothing at all for EA.
    Then even the bar it would have confirmed is not confirmed."""
    result = audit(panel, {"2026-08-07.json": week(
        "2026-08-07", {"EA": (209.7, 0)})},
        {s: h for s, h in PROVIDER.items() if s != "EA"})
    got = found(result)["series.EA"]
    assert got["class"] == "unverified"
    assert got["reason"] == "the provider returns no history for EA"
    assert set(result["audited"]["tickers"]["failed"]) == {"EA"}


def test_a_fetch_that_raises_leaves_nothing_ok(panel):
    def fetch(symbols, start, end):
        raise OSError("timed out")

    repo = panel({"2026-07-31.json": week(
        "2026-07-31", {"TGT": (144.49, 3312000)})}).parents[1]
    result = asr.run_audit(repo, fetch, NOW)
    assert result["audited"]["tickers"]["answered"] == 0
    assert result["audited"]["weekly"]["ok"] == 0
    assert found(result)["series.TGT"]["class"] == "unverified"


def test_a_session_that_is_not_final_yet_is_not_audited(panel):
    """On Friday evening the provider's own bar is still moving, and three
    closes in 2026-09-25.json show what judging against it would mean."""
    files = {"2026-09-25.json": week(
        "2026-09-25", {"COST": (922.765, 4602713)}, source="yahoo",
        fetched_at="2026-09-25T22:14:29Z")}
    evening = dt.datetime(2026, 9, 25, 22, 30, tzinfo=dt.timezone.utc)
    early = audit(panel, files, now=evening)
    assert early["findings"] == []
    assert early["audited"]["weekly"]["too_recent"] == ["2026-09-25.json"]
    assert early["audited"]["weekly"]["bars"] == 0
    assert "NOT AUDITED" in asr.render(early, None, False)[0]

    saturday = dt.datetime(2026, 9, 26, 13, 7, tzinfo=dt.timezone.utc)
    assert found(audit(panel, files, now=saturday))["series.COST"][
        "class"] == "differs"


# -- how the provider is asked -------------------------------------------------

def test_one_request_covers_every_week_and_every_fetch_date(panel):
    asked = []

    def fetch(symbols, start, end):
        asked.append((start, end))
        return {}

    repo = panel({"2024-08-09.json": week("2024-08-09", {"XYL": (1.0, 1)}),
                  "2026-07-31.json": week("2026-07-31", {"TGT": (1.0, 1)})}
                 ).parents[1]
    asr.run_audit(repo, fetch, NOW)
    assert asked == [("2024-07-29", "2026-10-06")]
    assert dt.date.fromisoformat(asked[0][0]).weekday() == 0


def test_a_split_dated_on_a_row_with_no_price_is_not_lost():
    """The provider prints corporate actions on rows with no bar: AVB's
    history ends with a dividend dated 2026-10-05 against a blank close. A
    split there belongs to every bar before it, so it moves to the next."""
    nan = float("nan")

    class Frame:
        def iterrows(self):
            day = dt.datetime(2026, 8, 10)
            yield day, {"Adj Close": 90.0, "Close": 90.0, "Volume": 10.0,
                        "Stock Splits": 0.0}
            yield day + dt.timedelta(days=1), {
                "Adj Close": nan, "Close": nan, "Volume": nan,
                "Stock Splits": 2.0}
            yield day + dt.timedelta(days=2), {
                "Adj Close": 45.0, "Close": 45.0, "Volume": 20.0,
                "Stock Splits": 0.0}

    assert asr._bars(Frame()) == {
        "2026-08-10": (90.0, 90.0, 10, 0.0),
        "2026-08-12": (45.0, 45.0, 20, 2.0)}


def test_a_provider_row_is_read_the_way_the_writer_read_it():
    """No close is no bar; a volume the provider left blank is None."""
    nan = float("nan")

    class Frame:
        def iterrows(self):
            day = dt.datetime(2026, 8, 10)
            yield day, {"Adj Close": 45.715, "Close": 45.715,
                        "Volume": 11943600.0, "Stock Splits": 0.0}
            yield day + dt.timedelta(days=1), {
                "Adj Close": 45.53, "Close": 45.53, "Volume": nan,
                "Stock Splits": 2.0}
            yield day + dt.timedelta(days=2), {
                "Adj Close": nan, "Close": nan, "Volume": 5.0,
                "Stock Splits": nan}

    assert asr._bars(Frame()) == {
        "2026-08-10": (45.715, 45.715, 11943600, 0.0),
        "2026-08-11": (45.53, 45.53, None, 2.0)}
    assert asr._bars(None) == {}


# -- corrections ---------------------------------------------------------------

def test_a_base_file_behind_a_correction_says_so(panel):
    base = week("2026-08-21", {"AVB": (65.9005, 0)}, source="yahoo",
                fetched_at="2026-08-22T16:01:01Z")
    fixed = week("2026-08-21", {}, source="yahoo",
                 fetched_at="2026-08-22T16:01:01Z")
    fixed["corrects"] = "2026-08-21.json"
    fixed["reason"] = "AVB printed behind zero volume"
    result = audit(panel, {"2026-08-21.json": base,
                           "2026-08-21.corrected.json": fixed})
    assert [f["file"] for f in result["findings"]] == ["2026-08-21.json"]
    assert result["findings"][0]["superseded_by"] == \
        "2026-08-21.corrected.json"


# -- the baseline --------------------------------------------------------------

THURSDAY = {"TGT": (144.51, 2627500)}
EARLY = {"COST": (922.765, 4602713)}


def cost_week(series=EARLY):
    return {"2026-09-25.json": week("2026-09-25", series, source="yahoo",
                                    fetched_at="2026-09-25T22:14:29Z")}


def test_a_finding_on_file_is_known_and_a_fresh_one_is_new(panel):
    before = audit(panel, {"2026-07-31.json": week("2026-07-31", THURSDAY)})
    after = audit(panel, {"2026-07-31.json": week(
        "2026-07-31", dict(THURSDAY, V=(365.5908, 8391400)))})
    new, changed, gone, known = asr.compare(before, after)
    assert [f["instrument"] for f in new] == ["series.V"]
    assert [f["instrument"] for f in known] == ["series.TGT"]
    assert changed == [] and gone == []


def test_a_finding_that_no_longer_reproduces_is_gone(panel):
    before = audit(panel, {"2026-07-31.json": week("2026-07-31", THURSDAY)})
    after = audit(panel, {"2026-07-31.json": week(
        "2026-07-31", {"TGT": (144.49, 3312000)})})
    new, changed, gone, known = asr.compare(before, after)
    assert [f["instrument"] for f in gone] == ["series.TGT"]
    assert new == [] and known == []


def test_a_provider_that_restated_is_changed_and_float_noise_is_not(panel):
    before = audit(panel, cost_week())
    noise = dict(COST, **{"2026-09-25": (922.7700805664062,
                                         922.7700805664062, 4629300, 0.0)})
    again = audit(panel, cost_week(), dict(PROVIDER, COST=noise))
    assert asr.compare(before, again)[1] == []

    moved = dict(COST, **{"2026-09-25": (922.78, 922.78, 4629300, 0.0)})
    after = audit(panel, cost_week(), dict(PROVIDER, COST=moved))
    new, changed, gone, known = asr.compare(before, after)
    assert len(changed) == 1 and new == [] and known == []
    assert changed[0][1]["provider"]["close"] == 922.78


def test_an_unanswered_symbol_does_not_erase_what_is_on_file(panel):
    """The provider not answering today says nothing about last month."""
    files = {"2026-07-31.json": week("2026-07-31", THURSDAY)}
    before = audit(panel, files)
    after = audit(panel, files, {})
    new, changed, gone, known = asr.compare(before, after)
    assert new == [] and changed == [] and gone == []
    assert known[0]["class"] == "prior_session"


def test_write_does_not_erase_what_the_provider_is_silent_about(
        tmp_path, panel):
    """EA's one bar is not always returned. On a day it is not, the reviewed
    finding stays on file as it was, cause and all, and the file says it was
    carried; an ok bar that went unanswered is new, and unreviewed."""
    path = tmp_path / "macro" / "series_audit.json"
    files = {"2026-08-07.json": week("2026-08-07", {
        "EA": (209.7, 0), "EQR": (67.07, 2136000)})}
    asr.write_baseline(path, audit(panel, files), None)
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert [f["class"] for f in doc["findings"]] == ["stand_in"]
    doc["findings"][0]["cause"] = "delisted_midweek"
    doc["causes"] = {"delisted_midweek": {}}

    silent = audit(panel, files, {})
    assert {f["class"] for f in silent["findings"]} == {"unverified"}
    asr.write_baseline(path, silent, doc)
    again = json.loads(path.read_text(encoding="utf-8"))
    kept = {f["instrument"]: f for f in again["findings"]}
    assert kept["series.EA"]["class"] == "stand_in"
    assert kept["series.EA"]["session"] == "2026-08-04"
    assert kept["series.EA"]["cause"] == "delisted_midweek"
    assert kept["series.EQR"]["class"] == "unverified"
    assert kept["series.EQR"]["cause"] is None
    assert again["audited"]["carried"] == ["2026-08-07.json series.EA"]
    counts = again["audited"]["weekly"]
    assert (counts["stand_in"], counts["unverified"]) == (1, 1)
    assert silent["audited"]["weekly"]["unverified"] == 2, "the run is as it was"


def test_write_keeps_the_hand_written_keys(tmp_path, panel):
    result = audit(panel, {"2026-07-31.json": week("2026-07-31", THURSDAY)})
    path = tmp_path / "macro" / "series_audit.json"
    previous = {"_purpose": "kept", "causes": {"gap_at_fetch": {}},
                "findings": [], "audited": {}}
    asr.write_baseline(path, result, previous)
    doc = json.loads(path.read_bytes().decode("ascii"))
    assert doc["_purpose"] == "kept"
    assert doc["causes"] == {"gap_at_fetch": {}}
    assert len(doc["findings"]) == 1
    assert doc["audited"]["fetched_at"] == "2026-10-05T15:36:30Z"


def test_a_cause_survives_a_rewrite_only_while_the_finding_is_the_same(
        tmp_path, panel):
    path = tmp_path / "macro" / "series_audit.json"
    first = audit(panel, cost_week(dict(EARLY, TGT=(1.0, 1))))
    asr.write_baseline(path, first, {"causes": {"evening_read": {}}})
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert [f["cause"] for f in doc["findings"]] == [None, None]
    assert len(asr.ai.unreviewed(doc)) == 2

    for f in doc["findings"]:
        f["cause"] = "evening_read"
    assert asr.ai.unreviewed(doc) == []

    moved = dict(COST, **{"2026-09-25": (922.78, 922.78, 4629300, 0.0)})
    asr.write_baseline(path, audit(panel, cost_week(dict(
        EARLY, TGT=(1.0, 1))), dict(PROVIDER, COST=moved)), doc)
    again = {f["instrument"]: f["cause"] for f in json.loads(
        path.read_text(encoding="utf-8"))["findings"]}
    assert again == {"series.COST": None, "series.TGT": "evening_read"}


def test_the_baseline_is_one_line_per_finding_and_reads_back_whole(
        tmp_path, panel):
    result = audit(panel, {
        "2026-07-31.json": week("2026-07-31", THURSDAY),
        "2026-08-07.json": week("2026-08-07", {"EA": (209.7, 0)})})
    assert [f["class"] for f in result["findings"]] == [
        "prior_session", "stand_in"]
    path = tmp_path / "macro" / "series_audit.json"
    asr.write_baseline(path, result, None)
    text = path.read_bytes().decode("ascii")
    assert "\r" not in text and text.endswith("]\n}\n")
    doc = json.loads(text)
    assert list(doc)[-1] == "findings" and len(doc["findings"]) == 2
    assert len([ln for ln in text.splitlines() if '"panel"' in ln]) == 2
    assert asr.ai.dump_baseline(doc) == text, "a rewrite of nothing is no diff"
    assert "never edited" in doc["_purpose"]
    assert "--write" in doc["_regenerate"]


def test_the_report_names_a_dropped_ticker_once(panel):
    """104 unverified AVB weeks are one fact, and one line. The bar with no
    volume behind it keeps a line of its own."""
    files = {"2026-07-%02d.json" % day: week(
        "2026-07-%02d" % day, {"AVB": (190.0 + day, 1000000 + day)})
        for day in (3, 10, 17)}
    files["2026-08-21.json"] = week("2026-08-21", {"AVB": (65.9005, 0)},
                                    source="yahoo",
                                    fetched_at="2026-08-22T16:01:01Z")
    text, _ = asr.render(audit(panel, files), None, True)
    rows = [ln for ln in text.splitlines() if " AVB " in ln]
    assert len(rows) == 2
    assert "NO VOLUME BEHIND IT" in rows[0]
    assert "AVB      3 bar(s), 2026-07-03.json .. 2026-07-17.json" in rows[1]


# -- the command ---------------------------------------------------------------

def one_finding_on_file(tmp_path, panel):
    path = tmp_path / "macro" / "series_audit.json"
    asr.write_baseline(path, audit(panel, {"2026-07-31.json": week(
        "2026-07-31", THURSDAY)}), None)
    return path


def test_a_provider_that_was_never_asked_is_not_blamed(
        tmp_path, panel, capsys):
    """Every file too recent to judge: nothing was fetched, so the run says
    what was not audited and why, and will not write a baseline from it."""
    baseline = one_finding_on_file(tmp_path, panel)
    before = baseline.read_bytes()
    repo = tmp_path / "later"
    weekly = repo / "data" / "weekly"
    weekly.mkdir(parents=True)
    (weekly / "2099-01-02.json").write_text(json.dumps(week(
        "2099-01-02", {"TGT": (1.0, 1)})), encoding="utf-8")
    args = ["--repo", str(repo), "--baseline", str(baseline)]

    assert asr.main(args) == 0
    out = capsys.readouterr().out
    assert "NOT AUDITED" in out and "2099-01-02.json" in out
    assert "NOTHING AUDITED" not in out

    assert asr.main(args + ["--write"]) == 2
    assert "REFUSED" in capsys.readouterr().out
    assert baseline.read_bytes() == before


def test_a_provider_that_answered_for_nothing_ends_the_run(
        tmp_path, panel, capsys, monkeypatch):
    """Asked and silent is exit 2 and one line, not 38,000 unverified bars."""
    baseline = one_finding_on_file(tmp_path, panel)
    before = baseline.read_bytes()
    repo = panel({"2026-07-31.json": week("2026-07-31", THURSDAY)}).parents[1]
    silent = asr.run_audit(repo, provider({}), NOW)
    assert silent["audited"]["tickers"] == {
        "asked": 1, "answered": 0, "through_successor": {},
        "failed": {"TGT": "no history returned for 2026-07-20..2026-10-06"}}
    monkeypatch.setattr(asr, "run_audit", lambda repo: silent)

    assert asr.main(["--repo", str(repo), "--baseline", str(baseline),
                     "--write"]) == 2
    assert capsys.readouterr().out.strip() == \
        "NOTHING AUDITED: the provider answered for no symbol."
    assert baseline.read_bytes() == before


# -- the committed baseline against the committed panel ------------------------

def committed_baseline():
    path = ROOT.joinpath(*asr.BASELINE)
    if not path.is_file():
        pytest.skip("no committed baseline")
    return json.loads(path.read_bytes().decode("ascii"))


def test_every_baseline_finding_quotes_the_file_it_names():
    """The baseline is evidence about committed files. An entry whose
    committed bar is not the one in the file is evidence about nothing."""
    for f in committed_baseline()["findings"]:
        path = ROOT / "data" / f["panel"] / f["file"]
        assert path.is_file(), f["file"]
        doc = json.loads(path.read_text(encoding="utf-8"))
        block, ticker = f["instrument"].split(".")
        assert block == "series"
        entry = doc["series"].get(ticker)
        assert entry is not None, (f["file"], ticker)
        assert entry == f["committed"], (f["file"], ticker)
        assert f["file"].startswith(doc["as_of"])
        origins = {t: o for t, _, o, _ in asr.bars_of(doc)}
        assert origins[ticker] == f["origin"]


def test_the_baseline_names_only_known_classes():
    doc = committed_baseline()
    assert {f["class"] for f in doc["findings"]} <= set(asr.CLASSES)
    assert doc["findings"] == sorted(doc["findings"], key=asr.ai._key)


def test_every_finding_on_file_has_a_cause_and_every_cause_is_used():
    """A baseline entry with no cause is a bar nobody looked at, filed where
    the audit will stop mentioning it."""
    doc = committed_baseline()
    causes = doc["causes"]
    assert asr.ai.unreviewed(doc) == []
    assert {f["cause"] for f in doc["findings"]} == set(causes)
    for name, cause in causes.items():
        assert cause["what"] and cause["evidence"] and cause["resolution"], name


def test_the_baseline_has_the_shape_the_code_writes(tmp_path, panel):
    """A baseline written by an older version of the script reads as fresh
    until its keys are compared with what a run produces now."""
    doc = committed_baseline()
    path = tmp_path / "macro" / "series_audit.json"
    asr.write_baseline(path, audit(panel, {"2026-07-31.json": week(
        "2026-07-31", THURSDAY)}), None)
    fresh = json.loads(path.read_text(encoding="utf-8"))

    def shape(node):
        if isinstance(node, dict):
            return {k: shape(v) for k, v in node.items()
                    if k not in ("failed", "through_successor")}
        return "list" if isinstance(node, list) else "value"

    assert shape(doc["audited"]) == shape(fresh["audited"])
    assert set(doc["_classes"]) == set(asr.CLASSES)


def test_the_baseline_accounts_for_every_bar_it_counted():
    """ok plus findings is every bar compared, origin by origin: nothing is
    in neither column."""
    doc = committed_baseline()
    counts = doc["audited"]["weekly"]
    assert counts["bars"] - counts["ok"] == len(doc["findings"])
    for origin in asr.ORIGINS:
        listed = [f for f in doc["findings"] if f["origin"] == origin]
        assert counts[origin]["bars"] - counts[origin]["ok"] == len(listed)
