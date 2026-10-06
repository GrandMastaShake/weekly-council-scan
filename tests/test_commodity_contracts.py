"""WTI, GOLD and SILVER are named contracts, and a close says which month.

Through 2026-10-02 the feed committed the provider's continuous symbols
(CL=F, GC=F, SI=F) under these keys. A continuous symbol is the provider's
choice of contract month, and the provider changed it: GC=F was the
nearest-expiry contract when the panel was backfilled and is the active one
now, for its whole history; SI=F's history and its live quote are different
months; and 2026-09-18.json holds 95.47 for WTI, the November contract's
last trade, where the October front month settled 100.30 (#110). Nothing in
those files says which month a close is.

Five things are pinned here. The roll calendar is the exchange rulebook's
and reproduces what the provider's chains did. The writer reads the named
contract and commits its name, and never falls back to the continuous
symbol. The deriver reads a commodity only where a contract is named, the
settlement file answers, or the panel was audited -- and measures WTI's
weekly change on one contract. The gate fails a market_state that shows
anything else. And the settlement file is written by a tool that reads by
name, takes a continuous symbol only on proof, and never rewrites an entry.

No network: the provider and the clock are stubbed. Bars for dates that
have happened are the provider's own, as fetched 2026-10-05; files dated
after that are what a future run would write.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from conftest import ROOT, settled_stamp, weekly_doc

import audit_instruments as ai  # noqa: E402  (conftest stubs the provider)
import backfill_commodities as bc  # noqa: E402
import backfill_weekly as bf  # noqa: E402
import daily_observe as do  # noqa: E402
import restate_instruments as ri  # noqa: E402
import truth_check as tc  # noqa: E402
from scan_pipeline import snapshot, snapshot_macro as sm  # noqa: E402

UTC = dt.timezone.utc
D = dt.date
COMMODITIES = sm.INSTRUMENTS["commodities"]
WTI = COMMODITIES["WTI"]
GOLD = COMMODITIES["GOLD"]
SILVER = COMMODITIES["SILVER"]

NOW = dt.datetime(2026, 10, 5, 22, 36, 17, tzinfo=UTC)
STAMP = "2026-10-05T22:36:17Z"

# The provider's bars as fetched 2026-10-05: (date, close, volume).
CLX26 = [(D(2026, 9, 11), 95.94, 251873), (D(2026, 9, 17), 97.23, 265281),
         (D(2026, 9, 18), 96.08, 317767), (D(2026, 9, 21), 92.37, 339728),
         (D(2026, 9, 22), 90.52, 422683), (D(2026, 9, 23), 92.16, 370714),
         (D(2026, 9, 24), 94.61, 410015), (D(2026, 9, 25), 92.41, 345783),
         (D(2026, 9, 28), 92.6, 370326), (D(2026, 10, 1), 92.87, 337181),
         (D(2026, 10, 2), 91.11, 337181)]
CLZ26 = [(D(2026, 9, 18), 92.05, 182690), (D(2026, 9, 25), 88.71, 179203),
         (D(2026, 10, 2), 89.43, 209718)]
# CL=F: the October contract through its last day, 2026-09-22 (whose bar
# carries November's volume), then November.
CL_F = [(D(2026, 9, 11), 100.05, 399142), (D(2026, 9, 17), 101.91, 265972),
        (D(2026, 9, 18), 100.3, 112698), (D(2026, 9, 21), 95.78, 76449),
        (D(2026, 9, 22), 94.59, 422683)] + CLX26[5:]
GCV26 = [(D(2026, 9, 25), 4287.7998, 15997),
         (D(2026, 9, 28), 4136.3999, 15257),
         (D(2026, 9, 29), 4147.7002, 7649), (D(2026, 9, 30), 4155.6001, 1463),
         (D(2026, 10, 1), 4172.8999, 348), (D(2026, 10, 2), 4133.7002, 348)]
# GC=F: the December contract, as the provider has served it since its
# rebuild. On no session is it the October contract.
GC_F = [(D(2026, 9, 18), 4424.8999, 142919),
        (D(2026, 9, 25), 4321.2002, 140092),
        (D(2026, 9, 28), 4168.3999, 229031),
        (D(2026, 9, 29), 4179.7002, 149747),
        (D(2026, 9, 30), 4186.7002, 156277),
        (D(2026, 10, 1), 4202.2998, 130846),
        (D(2026, 10, 2), 4162.2998, 130846)]
SIV26 = [(D(2026, 9, 25), 64.271, 945), (D(2026, 9, 28), 61.231, 1386),
         (D(2026, 9, 29), 60.668, 146), (D(2026, 9, 30), 60.098, 349),
         (D(2026, 10, 1), 60.725, 229), (D(2026, 10, 2), 59.977, 229)]
# SI=F: the September contract through its last day, 2026-09-28, then October.
SI_F = [(D(2026, 8, 28), 66.995, 4329), (D(2026, 9, 11), 64.554, 526),
        (D(2026, 9, 18), 66.556, 97), (D(2026, 9, 25), 64.245, 49),
        (D(2026, 9, 28), 61.22, 1386)] + SIV26[2:]
PROVIDER = {"CLX26.NYM": CLX26, "CLZ26.NYM": CLZ26, "CL=F": CL_F,
            "GCV26.CMX": GCV26, "GC=F": GC_F, "SIV26.CMX": SIV26,
            "SI=F": SI_F}


class Frame:
    """What Ticker.history returns, as far as snapshot_macro looks at it."""

    def __init__(self, rows):
        self.rows = rows

    @property
    def empty(self):
        return not self.rows

    def iterrows(self):
        for day, close, volume in self.rows:
            yield (dt.datetime(day.year, day.month, day.day),
                   {"Close": close, "Volume": volume})


@pytest.fixture
def provider(monkeypatch):
    """Stub yfinance and the clock. Returns (table, calls): table[symbol]
    is a list of bars or an exception; a symbol not in it has no data, which
    is how the provider answers for an expired contract."""
    table, calls = dict(PROVIDER), []

    class Ticker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, start=None, end=None):
            calls.append(self.symbol)
            rows = table.get(self.symbol, [])
            if isinstance(rows, Exception):
                raise rows
            return Frame([r for r in rows
                          if start <= r[0].isoformat() < end])

    monkeypatch.setattr(sm.yf, "Ticker", Ticker, raising=False)
    monkeypatch.setattr(sm, "_utcnow", lambda: NOW)
    return table, calls


# -- the roll calendar ---------------------------------------------------------

# Every crude expiry in the window, as CL=F's own volume shows it: two thin
# sessions, then a bar that carries the next month's volume (probed
# 2026-10-05; the smallest jump of the 32 is 1.75x).
CRUDE_LAST_DAYS = {
    "CLH24": "2024-02-20", "CLJ24": "2024-03-20", "CLK24": "2024-04-22",
    "CLM24": "2024-05-21", "CLN24": "2024-06-20", "CLQ24": "2024-07-22",
    "CLU24": "2024-08-20", "CLV24": "2024-09-20", "CLX24": "2024-10-22",
    "CLZ24": "2024-11-20", "CLF25": "2024-12-19", "CLG25": "2025-01-21",
    "CLH25": "2025-02-20", "CLJ25": "2025-03-20", "CLK25": "2025-04-22",
    "CLM25": "2025-05-20", "CLN25": "2025-06-20", "CLQ25": "2025-07-22",
    "CLU25": "2025-08-20", "CLV25": "2025-09-22", "CLX25": "2025-10-21",
    "CLZ25": "2025-11-20", "CLF26": "2025-12-19", "CLG26": "2026-01-20",
    "CLH26": "2026-02-20", "CLJ26": "2026-03-20", "CLK26": "2026-04-21",
    "CLM26": "2026-05-19", "CLN26": "2026-06-22", "CLQ26": "2026-07-21",
    "CLU26": "2026-08-20", "CLV26": "2026-09-22",
}


def last_day(code):
    return sm.last_trade_date(*sm.contract_parts(code)).isoformat()


def test_the_calendar_reproduces_every_crude_expiry_the_provider_shows():
    assert {code: last_day(code) for code in CRUDE_LAST_DAYS} == \
        CRUDE_LAST_DAYS


def test_the_three_roll_dates_confirmed_by_contract_name():
    """CLQ26.NYM's last bar is 2026-07-21; CL=F's bars are CLX26's from
    2026-09-23; SI=F's are SIV26's from 2026-09-29."""
    assert last_day("CLQ26") == "2026-07-21"
    assert last_day("CLV26") == "2026-09-22"
    assert last_day("SIU26") == last_day("GCU26") == "2026-09-28"


@pytest.mark.parametrize("code,day,why", [
    ("CLF27", "2026-12-21", "the 25th is Christmas: three business days "
                            "before the 24th"),
    ("CLQ26", "2026-07-21", "the 25th is a Saturday: before Friday the 24th"),
    ("CLG26", "2026-01-20", "the 25th is a Sunday: before Friday the 23rd"),
    ("CLZ26", "2026-11-20", "an ordinary month, and a Friday"),
    ("GCH24", "2024-03-26", "Good Friday is the 29th and is not a business "
                            "day"),
    ("GCX26", "2026-11-25", "Thanksgiving is not a business day; the Friday "
                            "after it is"),
    ("SIK27", "2027-05-26", "Memorial Day is the 31st"),
    ("GCZ26", "2026-12-29", "the year's last three business days"),
    ("GCH26", "2026-03-27", "a Friday, and in the panel"),
])
def test_last_trade_dates_follow_the_rulebook(code, day, why):
    assert last_day(code) == day, why


def test_a_business_day_is_a_day_the_exchange_settles():
    """Not the bond market's calendar: Columbus Day and Veterans Day are
    ordinary sessions for crude and metals."""
    assert sm.is_business_day(D(2026, 10, 12))          # Columbus Day
    assert sm.is_business_day(D(2026, 11, 11))          # Veterans Day
    assert sm.is_business_day(D(2026, 11, 27))          # after Thanksgiving
    assert not sm.is_business_day(D(2026, 11, 26))
    assert not sm.is_business_day(D(2026, 4, 3))        # Good Friday
    assert not sm.is_business_day(D(2026, 6, 19))       # Juneteenth
    assert not sm.is_business_day(D(2026, 7, 3))        # July 4th, observed
    assert not sm.is_business_day(D(2027, 12, 24))      # Christmas, observed
    assert not sm.is_business_day(D(2026, 10, 10))      # a Saturday


def test_new_years_day_on_a_saturday_is_not_observed_on_the_friday():
    """The one judgment in the table, written down so it is found if the
    exchange decides otherwise."""
    assert sm.is_business_day(D(2027, 12, 31))
    assert D(2027, 12, 31) not in sm.exchange_holidays(2027)
    assert D(2028, 1, 1) not in sm.exchange_holidays(2028)


@pytest.mark.parametrize("day,front,second", [
    (D(2026, 9, 18), "CLV26", "CLX26"),
    (D(2026, 9, 22), "CLV26", "CLX26"),     # its last day: still the front
    (D(2026, 9, 23), "CLX26", "CLZ26"),
    (D(2026, 10, 9), "CLX26", "CLZ26"),
    (D(2026, 10, 23), "CLZ26", "CLF27"),
    (D(2026, 12, 22), "CLG27", "CLH27"),    # across the year end
])
def test_the_front_month_is_held_through_its_last_trade_date(day, front,
                                                             second):
    assert sm.contract_for("CL", day) == front
    assert sm.contract_for("CL", day, 1) == second


@pytest.mark.parametrize("day,month", [
    (D(2026, 10, 2), "V26"), (D(2026, 10, 28), "V26"),
    (D(2026, 10, 29), "X26"), (D(2026, 10, 30), "X26"),
    (D(2026, 12, 30), "F27"),
])
def test_the_metals_are_the_spot_month(day, month):
    """The contract for the calendar month, until it stops trading on the
    third last business day; then next month's for the last two."""
    assert sm.contract_for("GC", day) == "GC" + month
    assert sm.contract_for("SI", day) == "SI" + month


def test_a_contract_has_one_name_and_one_symbol():
    assert sm.contract_code("CL", 2026, 11) == "CLX26"
    assert sm.contract_parts("CLX26") == ("CL", 2026, 11)
    assert sm.contract_symbol("CLX26") == "CLX26.NYM"
    assert sm.contract_symbol("GCV26") == "GCV26.CMX"
    assert sm.contract_symbol("SIV26") == "SIV26.CMX"
    for bad in ("CL=F", "GC", "HGZ26", "CLA26", "CLX2026", ""):
        with pytest.raises(ValueError):
            sm.contract_parts(bad)


def test_resolving_leaves_a_fixed_symbol_alone():
    tnx = sm.INSTRUMENTS["rates"]["US10Y"]
    assert sm.resolved(tnx, D(2026, 10, 9)) == (tnx, None)
    cfg, contract = sm.resolved(GOLD, D(2026, 10, 9))
    assert (cfg["symbol"], contract) == ("GCV26.CMX", "GCV26")
    assert "symbol" not in GOLD, "the config holds no symbol to fall back on"


def test_the_calendar_explains_the_volume_the_panel_committed():
    """No network, and the panel's own numbers. In the days before a crude
    contract stops trading, its volume moves to the next month. Every Friday
    one or two sessions ahead of the calendar's last trade date shows it
    (WTI under 130,000 contracts), and no other Friday does. The exception
    proves the rule: 2026-09-18.json holds the November contract's quote,
    which is issue #110."""
    weekly = ROOT / "data" / "weekly"
    thin, near = set(), set()
    for path in sorted(weekly.glob("*.json")):
        if path.name.endswith(".corrected.json"):
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc["as_of"] > "2026-10-02":
            continue        # named since: the volume is the contract's own
        day = D.fromisoformat(doc["as_of"])
        last = sm.last_trade_date(*sm.contract_parts(
            sm.contract_for("CL", day)))
        sessions = sum(1 for n in range(1, (last - day).days + 1)
                       if sm.is_business_day(day + dt.timedelta(days=n)))
        if sessions in (1, 2):
            near.add(doc["as_of"])
        volume = doc["commodities"]["WTI"]["volume"]
        if volume is not None and volume < 130000:
            thin.add(doc["as_of"])
    assert len(near) == 14
    assert near - thin == {"2026-09-18"}
    assert thin - near == set()


# -- the writer ----------------------------------------------------------------

def test_the_writer_reads_the_named_contract_and_says_which(provider):
    table, calls = provider
    entry, err = sm._fetch_one("GOLD", GOLD, D(2026, 10, 2))
    assert err is None
    assert entry == {"close": 4133.7002, "volume": 348, "contract": "GCV26"}
    assert calls == ["GCV26.CMX"], "and never GC=F, which is December"


def test_the_second_contract_is_the_month_after(provider):
    entry, err = sm._fetch_one("WTI_NEXT", COMMODITIES["WTI_NEXT"],
                               D(2026, 10, 2))
    assert (entry, err) == ({"close": 89.43, "volume": 209718,
                             "contract": "CLZ26"}, None)


def test_an_expired_contract_is_missing_and_nothing_stands_in(provider):
    """2026-09-18, asked today. The October contract is gone and CL=F still
    answers for the date. A fallback to it is how 95.47 got in."""
    table, calls = provider
    entry, err = sm._fetch_one("WTI", WTI, D(2026, 9, 18))
    assert entry is None
    assert "no data returned for CLV26.NYM" in err
    assert "its last trade date is 2026-09-22" in err
    assert "CL=F" not in calls


def test_a_named_contract_waits_for_the_settlement_like_any_future(
        provider, monkeypatch):
    monkeypatch.setattr(sm, "_utcnow", lambda: dt.datetime(
        2026, 10, 3, 1, 13, tzinfo=UTC))                # Friday 21:13 ET
    entry, err = sm._fetch_one("WTI", WTI, D(2026, 10, 2))
    assert entry is None
    assert "CLX26.NYM: the bar dated 2026-10-02 is a quote" in err


def test_a_stand_in_stays_inside_one_contract(provider, monkeypatch):
    """A holiday Friday whose week's last session was another month's last
    day. The calendar is stubbed to make one; nothing stands in."""
    table, _ = provider
    table["GCJ43.CMX"] = [(D(2043, 3, 26), 9000.0, 10),
                          (D(2043, 3, 30), 9010.0, 900)]
    monkeypatch.setattr(sm, "_utcnow", lambda: dt.datetime(
        2043, 4, 6, tzinfo=UTC))
    monkeypatch.setattr(sm, "contract_for", lambda root, day, position=0: (
        "GCH43" if day <= D(2043, 3, 26) else "GCJ43"))
    entry, err = sm._fetch_one("GOLD", GOLD, D(2043, 3, 27))
    assert entry is None
    assert "2043-03-26, belongs to GCH43" in err
    assert "one contract month does not stand in for another" in err


def test_a_holiday_stand_in_names_the_contract_and_the_session(provider):
    table, _ = provider
    table["GCN26.CMX"] = [(D(2026, 7, 1), 4100.0, 400),
                          (D(2026, 7, 2), 4112.7002, 228),
                          (D(2026, 7, 6), 4120.0, 350)]
    entry, err = sm._fetch_one("GOLD", GOLD, D(2026, 7, 3))
    assert err is None
    assert (entry["close"], entry["contract"], entry["observed"]) == (
        4112.7002, "GCN26", "2026-07-02")


def special_for(day, monkeypatch):
    monkeypatch.setattr(sm, "_fetch_treasury", lambda ticker, cfg, d: (
        {"close": 4.83, "volume": None},
        {"source": "treasury", "fetched_at": STAMP}, None))
    return sm.fetch_special_instruments(day)


def test_every_commodity_is_labelled_with_its_contract(provider, monkeypatch):
    got = special_for("2026-10-02", monkeypatch)
    assert got["commodities"] == {
        "WTI": {"close": 91.11, "volume": 337181},
        "WTI_NEXT": {"close": 89.43, "volume": 209718},
        "GOLD": {"close": 4133.7002, "volume": 348},
        "SILVER": {"close": 59.977, "volume": 229},
    }
    label = {"source": "yahoo", "fetched_at": STAMP}
    assert got["provenance"]["commodities"] == {
        "WTI": dict(label, contract="CLX26"),
        "WTI_NEXT": dict(label, contract="CLZ26"),
        "GOLD": dict(label, contract="GCV26"),
        "SILVER": dict(label, contract="SIV26"),
    }
    assert not [m for m in got["missing"]
                if m["ticker"] in COMMODITIES]


def test_the_continuous_symbols_are_not_what_the_writer_reads(
        provider, monkeypatch):
    table, calls = provider
    special_for("2026-10-02", monkeypatch)
    assert not {"CL=F", "GC=F", "SI=F"} & set(calls)


# -- the committed file --------------------------------------------------------

def label(contract, as_of="2026-10-09", **more):
    """A commodity's label, read once the session had settled."""
    return dict({"source": "yahoo", "fetched_at": settled_stamp(as_of),
                 "contract": contract}, **more)


def named_week(as_of, wti=None, nxt=None, gold=None, silver=None,
               fetched_at=None):
    """A weekly doc as the writer commits it since 2026-10-05. Each
    instrument is (close, contract) or None."""
    doc = weekly_doc(as_of, ["SPY"], fetched_at=fetched_at)
    for ticker, got in (("WTI", wti), ("WTI_NEXT", nxt), ("GOLD", gold),
                        ("SILVER", silver)):
        if got is None:
            continue
        doc["commodities"][ticker] = {"close": got[0], "volume": None}
        doc.setdefault("provenance", {}).setdefault(
            "commodities", {})[ticker] = label(got[1], as_of)
    return doc


def old_week(as_of, wti=None, gold=None, silver=None):
    """A weekly doc from before: a continuous symbol's bar, and no label."""
    doc = weekly_doc(as_of, ["SPY"])
    for ticker, close in (("WTI", wti), ("GOLD", gold), ("SILVER", silver)):
        if close is not None:
            doc["commodities"][ticker] = {"close": close, "volume": None}
    return doc


def fails(rep):
    return [line for line in rep.lines if line.startswith("FAIL")]


def warns(rep):
    return [line for line in rep.lines if line.startswith("WARN")]


def file_gate(repo):
    rep = tc.Report()
    tc.check_feed(repo, rep)
    return rep


def test_the_weekly_file_commits_the_contract_and_stays_a_yahoo_file(
        provider, monkeypatch, tmp_path):
    """sector-regime-heatmap refuses a file-level source it does not know,
    and a source it does not know under provenance.series. Neither is
    touched: the contract sits under provenance.commodities, which that
    repo never reads."""
    special = special_for("2026-10-02", monkeypatch)
    path = snapshot.write_weekly("2026-10-02",
                                 {"SPY": {"close": 668.0, "volume": 1}},
                                 special, out_dir=str(tmp_path / "data"))
    doc = json.loads(Path(path).read_text(encoding="utf-8"))

    assert doc["source"] == snapshot.PROVIDER == "yahoo"
    assert "series" not in doc["provenance"]
    assert doc["commodities"]["GOLD"] == {"close": 4133.7002, "volume": 348}
    assert doc["provenance"]["commodities"]["GOLD"] == {
        "source": "yahoo", "fetched_at": STAMP, "contract": "GCV26"}
    assert snapshot.named_contract(doc, "commodities", "WTI") == "CLX26"
    assert snapshot.named_contract(doc, "commodities", "WTI_NEXT") == "CLZ26"
    assert snapshot.named_contract(doc, "rates", "US10Y") is None
    raw = Path(path).read_bytes()
    raw.decode("ascii")
    assert b"\r\n" not in raw and raw.endswith(b"\n")


def test_a_contract_that_is_not_one_does_not_reach_the_file(tmp_path):
    special = {"rates": {}, "vol": {}, "fx": {}, "missing": [],
               "commodities": {"GOLD": {"close": 4133.7, "volume": None}},
               "provenance": {"commodities": {"GOLD": {
                   "source": "yahoo", "fetched_at": STAMP,
                   "contract": "GC=F"}}}}
    path = snapshot.write_weekly("2026-10-02",
                                 {"SPY": {"close": 668.0, "volume": 1}},
                                 special, out_dir=str(tmp_path))
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    assert "contract" not in doc["provenance"]["commodities"]["GOLD"]
    assert snapshot.named_contract(doc, "commodities", "GOLD") is None


def test_the_daily_file_carries_the_label_the_same_way():
    special = {"rates": {}, "vol": {}, "fx": {}, "missing": [],
               "commodities": {"WTI": {"close": 91.11, "volume": 337181}},
               "provenance": {"commodities": {"WTI": label("CLX26")}}}
    bars = {"bars": {"SPY": {"close": 668.0, "volume": 1}}, "missing": []}
    doc = do.build_document("2026-10-02", bars, special)
    assert doc["source"] == "yahoo-daily"
    assert doc["provenance"]["commodities"]["WTI"]["contract"] == "CLX26"


def test_a_full_rewrite_keeps_the_contract_through_its_restamp(
        tmp_path, monkeypatch):
    special = {"rates": {}, "vol": {}, "fx": {}, "missing": [],
               "commodities": {"WTI": {"close": 91.11, "volume": 337181}},
               "provenance": {"commodities": {"WTI": label("CLX26")}}}
    monkeypatch.setattr(bf.snapshot_macro, "fetch_special_instruments",
                        lambda friday: special)
    monkeypatch.setattr(bf.time, "sleep", lambda s: None)
    day = D(2026, 10, 2)
    rec = bf.build_and_write(day, ["SPY"], {"SPY": ([day], [668.0], [1])},
                             str(tmp_path))
    doc = json.loads(Path(rec["path"]).read_text(encoding="utf-8"))
    assert doc["provenance"]["commodities"]["WTI"] == {
        "source": bf.BACKFILL_SOURCE, "fetched_at": bf.RUN_TS,
        "contract": "CLX26"}


def test_the_gate_accepts_a_file_that_names_its_contracts(panel):
    repo = panel({"2026-10-09.json": named_week(
        "2026-10-09", wti=(90.2, "CLX26"), nxt=(88.6, "CLZ26"),
        gold=(4150.0, "GCV26"), silver=(60.5, "SIV26"))}).parents[1]
    assert fails(file_gate(repo)) == []


@pytest.mark.parametrize("ticker,contract,why", [
    ("GOLD", "GCZ26", "cannot be the nearest-expiry contract"),  # the active
    ("GOLD", "SIV26", "is not a GC contract"),
    ("GOLD", "GC=F", "is not a GC contract"),
    ("WTI", "CLV26", "cannot be the nearest-expiry contract"),   # expired
    ("WTI", "CLF27", "cannot be the nearest-expiry contract"),
    ("WTI_NEXT", "CLX26", "cannot be the next contract"),        # the front
    ("SILVER", "SIZ26", "cannot be the nearest-expiry contract"),
])
def test_the_gate_refuses_a_label_that_cannot_be_right(panel, ticker,
                                                       contract, why):
    """December gold under GOLD in October is the defect itself, written by
    a writer that asked the continuous symbol and labelled the answer."""
    doc = named_week("2026-10-09", wti=(90.2, "CLX26"), nxt=(88.6, "CLZ26"),
                     gold=(4150.0, "GCV26"), silver=(60.5, "SIV26"))
    doc["provenance"]["commodities"][ticker]["contract"] = contract
    got = fails(file_gate(panel({"2026-10-09.json": doc}).parents[1]))
    assert len(got) == 1 and why in got[0]


def test_the_gate_refuses_a_contract_on_anything_but_a_commodity(panel):
    doc = named_week("2026-10-09", wti=(90.2, "CLX26"))
    doc["rates"] = {"US10Y": {"close": 5.3, "volume": None}}
    doc["provenance"]["rates"] = {"US10Y": label("CLX26")}
    got = fails(file_gate(panel({"2026-10-09.json": doc}).parents[1]))
    assert len(got) == 1
    assert "only a commodity is a named contract month" in got[0]


def test_a_stand_in_label_is_judged_against_the_session_it_is(panel):
    """Thursday 2026-10-29 is the first day November is the spot month. A
    file for a holiday Friday in a later year would carry the same shape."""
    doc = named_week("2026-07-03", gold=(4112.7002, "GCN26"))
    doc["provenance"]["commodities"]["GOLD"]["observed"] = "2026-07-02"
    assert fails(file_gate(panel({"2026-07-03.json": doc}).parents[1])) == []


def test_the_gate_and_the_writer_agree_on_the_names():
    """truth_check stays stdlib-only, so it repeats what it needs. A repeat
    that drifts is a gate enforcing last month's rule."""
    assert tc.COMMODITY_HISTORY[-1] == snapshot.COMMODITY_HISTORY_FILE
    assert tc.NEXT_CONTRACT == snapshot.NEXT_CONTRACT
    assert list(tc.COMMODITY_STATE) == snapshot.COMMODITY_TICKERS
    assert tc.COMMODITY_ROOTS == {t: cfg["root"]
                                  for t, cfg in COMMODITIES.items()}
    assert tc.COMMODITY_POSITION == {t: cfg["position"]
                                     for t, cfg in COMMODITIES.items()}
    assert set(tc.CONTRACT_MONTHS_AHEAD) == set(sm.CONTRACT_ROOTS)
    assert tc.CONTRACT_RE.pattern.replace("(", "").replace(")", "") == \
        snapshot._CONTRACT_RE.pattern
    assert bc.SCHEMA == "commodity-settlements/v1"


def test_the_gates_bound_holds_for_every_session_the_calendar_names():
    """The gate's month bound is not the calendar, but it must never refuse
    what the calendar produces."""
    day = D(2024, 1, 1)
    while day < D(2029, 1, 1):
        for ticker, cfg in COMMODITIES.items():
            rep = tc.Report()
            code = sm.contract_for(cfg["root"], day, cfg["position"])
            assert tc._contract_check("x", ticker, code, day.isoformat(),
                                      rep), (ticker, code, day)
        day += dt.timedelta(days=1)


# -- the settlement file and the reader ----------------------------------------

# The last five committed weeks as they are: continuous symbols, no label.
SEAM = {
    "2026-09-04.json": old_week("2026-09-04", 91.48, 4429.7998, 66.047),
    "2026-09-11.json": old_week("2026-09-11", 99.99, 4390.0, 65.02),
    "2026-09-18.json": old_week("2026-09-18", 95.47, 4415.8999, 66.785),
    "2026-09-25.json": old_week("2026-09-25", 92.44, 4320.5, 64.71),
    "2026-10-02.json": old_week("2026-10-02", 91.11, 4162.2998, 59.977),
}
GONE = {"contract": "GCU26", "checked_at": STAMP,
        "reason": "The file holds the December contract. The nearest-expiry "
                  "contract was September, which expired on 2026-09-28.",
        "evidence": "the provider serves nothing for GCU26"}


def entry(close, contract, symbol=None, replaces=None, **more):
    out = {"close": close, "volume": None, "contract": contract,
           "symbol": symbol or sm.contract_symbol(contract),
           "source": "yahoo-backfill", "fetched_at": STAMP}
    if replaces is not None:
        out["replaces"] = {"close": replaces, "volume": None}
    out.update(more)
    return out


def committed_history():
    """data/commodity_settlements.json as this change commits it, for the
    weeks SEAM has."""
    doc = bc.empty_history()
    doc["instruments"]["WTI"]["series"] = {
        "2026-09-11": entry(100.05, "CLV26", "CL=F", replaces=99.99),
        "2026-09-18": entry(100.3, "CLV26", "CL=F", replaces=95.47),
        "2026-09-25": entry(92.41, "CLX26", replaces=92.44),
        "2026-10-02": entry(91.11, "CLX26"),
    }
    doc["instruments"]["GOLD"]["series"] = {
        "2026-10-02": entry(4133.7002, "GCV26", replaces=4162.2998)}
    doc["instruments"]["GOLD"]["unavailable"] = {
        w: dict(GONE) for w in ("2026-09-11", "2026-09-18", "2026-09-25")}
    doc["instruments"]["SILVER"]["series"] = {
        "2026-09-11": entry(64.554, "SIU26", "SI=F", replaces=65.02),
        "2026-09-18": entry(66.556, "SIU26", "SI=F", replaces=66.785),
        "2026-09-25": entry(64.245, "SIU26", "SI=F", replaces=64.71),
        "2026-10-02": entry(59.977, "SIV26"),
    }
    return doc


def write_history(weekly_dir, doc):
    path = Path(snapshot.commodity_history_path(str(weekly_dir)))
    path.write_text(snapshot.canonical_json(doc), encoding="utf-8",
                    newline="")
    return path


def read_series(weekly_dir, ticker):
    docs = snapshot._load_weekly_files(str(weekly_dir))
    history, problem = snapshot.load_commodity_history(
        snapshot.commodity_history_path(str(weekly_dir)))
    return snapshot.commodity_series(docs, history, ticker)


def derive(weekly_dir):
    return snapshot.derive_market_state(
        str(weekly_dir), str(weekly_dir.parent / "no-facts.json"))


def test_the_settlement_file_is_found_beside_the_weekly_directory(tmp_path):
    got = Path(snapshot.commodity_history_path(
        str(tmp_path / "data" / "weekly")))
    assert got == tmp_path / "data" / "commodity_settlements.json"


def test_an_audited_close_is_read_and_a_superseded_one_is_not(panel):
    weekly = panel(SEAM)
    write_history(weekly, committed_history())
    assert read_series(weekly, "WTI") == {
        "2026-09-04": (91.48, None),        # audited: it is the settlement
        "2026-09-11": (100.05, "CLV26"),
        "2026-09-18": (100.3, "CLV26"),     # not the 95.47 of #110
        "2026-09-25": (92.41, "CLX26"),
        "2026-10-02": (91.11, "CLX26"),
    }


def test_a_week_with_no_settlement_is_a_gap_and_the_file_is_not_read(panel):
    """The four gold weeks. The file holds a number for each, and it is the
    December contract's."""
    weekly = panel(SEAM)
    write_history(weekly, committed_history())
    assert read_series(weekly, "GOLD") == {
        "2026-09-04": (4429.7998, None),
        "2026-10-02": (4133.7002, "GCV26"),
    }


def test_a_file_that_names_its_contract_speaks_for_itself(panel):
    weekly = panel(dict(SEAM, **{"2026-10-09.json": named_week(
        "2026-10-09", wti=(90.2, "CLX26"), nxt=(88.6, "CLZ26"),
        gold=(4150.0, "GCV26"), silver=(60.5, "SIV26"))}))
    write_history(weekly, committed_history())
    assert read_series(weekly, "GOLD")["2026-10-09"] == (4150.0, "GCV26")
    assert read_series(weekly, "WTI_NEXT") == {"2026-10-09": (88.6, "CLZ26")}


def test_the_weeks_own_named_close_wins_over_an_entry(panel):
    weekly = panel({"2026-10-09.json": named_week(
        "2026-10-09", gold=(4150.0, "GCV26"))})
    doc = bc.empty_history()
    doc["instruments"]["GOLD"]["series"] = {
        "2026-10-09": entry(4199.0, "GCV26")}
    write_history(weekly, doc)
    assert read_series(weekly, "GOLD") == {"2026-10-09": (4150.0, "GCV26")}


def test_an_unlabelled_close_from_after_the_audit_is_never_read(panel):
    """What a runner still on the old writer commits: GC=F under GOLD. It
    looks like every audited week, and it is the active contract."""
    weekly = panel(dict(SEAM, **{"2026-10-09.json": old_week(
        "2026-10-09", 90.2, 4178.4, 60.5)}))
    write_history(weekly, committed_history())
    for ticker in ("WTI", "GOLD", "SILVER"):
        assert "2026-10-09" not in read_series(weekly, ticker)
    commodities = derive(weekly)["commodities"]
    assert commodities["GOLD"]["px"] is None
    assert "names no contract for GOLD" in commodities["GOLD"]["px_reason"]
    assert "never used" in commodities["GOLD"]["px_reason"]


def test_an_entry_can_supply_such_a_week_afterwards(panel):
    weekly = panel(dict(SEAM, **{"2026-10-09.json": old_week(
        "2026-10-09", 90.2, 4178.4, 60.5)}))
    doc = committed_history()
    doc["instruments"]["GOLD"]["series"]["2026-10-09"] = entry(
        4150.0, "GCV26", replaces=4178.4)
    write_history(weekly, doc)
    gold = derive(weekly)["commodities"]["GOLD"]
    assert (gold["px"], gold["contract"]) == (4150.0, "GCV26")
    assert gold["d1w"] == 0.4


def test_without_the_settlement_file_no_old_close_is_read(panel):
    """A runner that has the new code and never received the file. Reading
    the unlabelled closes anyway is the old deriver again."""
    weekly = panel(dict(SEAM, **{"2026-10-09.json": named_week(
        "2026-10-09", gold=(4150.0, "GCV26"))}))
    assert read_series(weekly, "GOLD") == {"2026-10-09": (4150.0, "GCV26")}
    gold = derive(weekly)["commodities"]["GOLD"]
    assert gold["px"] == 4150.0
    assert gold["d1w"] is None
    assert "commodity_settlements.json not found" in gold["d1w_reason"]
    assert gold["pctile_2y"] is None, "a rank among one week is not a rank"
    assert "commodity_settlements.json not found" in \
        gold["pctile_2y_reason"]


def test_an_unreadable_settlement_file_degrades_the_same_way(panel):
    weekly = panel(SEAM)
    Path(snapshot.commodity_history_path(str(weekly))).write_text(
        "{not json", encoding="utf-8")
    history, problem = snapshot.load_commodity_history(
        snapshot.commodity_history_path(str(weekly)))
    assert history == {} and "unreadable" in problem
    assert derive(weekly)["commodities"]["WTI"]["px"] is None


# -- market_state --------------------------------------------------------------

def test_the_committed_seam_derives_on_one_contract_per_instrument(panel):
    """As this change regenerates it. Gold was 4162.3 with d4w -6.0: the
    December contract against the September one."""
    weekly = panel(SEAM)
    write_history(weekly, committed_history())
    got = derive(weekly)["commodities"]

    assert {k: got["WTI"][k] for k in ("px", "contract", "d1w", "d4w")} == {
        "px": 91.11, "contract": "CLX26", "d1w": -1.4, "d4w": -0.4}
    assert {k: got["SILVER"][k] for k in ("px", "contract", "d1w", "d4w")} \
        == {"px": 59.98, "contract": "SIV26", "d1w": -6.6, "d4w": -9.2}
    gold = got["GOLD"]
    assert (gold["px"], gold["contract"], gold["d4w"]) == (
        4133.7, "GCV26", -6.7)
    assert gold["d1w"] is None
    assert "no GOLD settlement on the nearest-expiry contract for " \
           "2026-09-25" in gold["d1w_reason"]
    assert "expired on 2026-09-28" in gold["d1w_reason"]
    assert gold["d13w"] is None and "no weekly file dated" in \
        gold["d13w_reason"]


def test_every_field_is_present_and_a_null_has_its_reason(panel):
    weekly = panel(SEAM)
    write_history(weekly, committed_history())
    for ticker, rec in derive(weekly)["commodities"].items():
        for field in ("px", "contract", "d1w", "d4w", "d13w", "d52w",
                      "pctile_2y"):
            assert field in rec, (ticker, field)
            if rec[field] is None:
                assert rec[field + "_reason"], (ticker, field)


def test_an_audited_week_has_a_price_and_no_contract_on_record(panel):
    weekly = panel({"2026-09-04.json": SEAM["2026-09-04.json"]})
    write_history(weekly, bc.empty_history())
    wti = derive(weekly)["commodities"]["WTI"]
    assert wti["px"] == 91.48
    assert wti["contract"] is None
    assert "predates named contracts" in wti["contract_reason"]


ROLL = {
    # 2026-09-18 and 09-25 as the writer would have committed them: the
    # October contract's last Friday, then November.
    "2026-09-18.json": named_week("2026-09-18", wti=(100.3, "CLV26"),
                                  nxt=(96.08, "CLX26")),
    "2026-09-25.json": named_week("2026-09-25", wti=(92.41, "CLX26"),
                                  nxt=(88.71, "CLZ26")),
}


def test_wti_d1w_is_one_contracts_change_in_the_week_the_front_changes(
        panel):
    """November fell 3.8 percent. Front against front is -7.9: the other
    four points are the spread between two months, not a move."""
    weekly = panel(ROLL)
    wti = derive(weekly)["commodities"]["WTI"]
    assert (wti["px"], wti["contract"]) == (92.41, "CLX26")
    assert wti["d1w"] == -3.8
    assert round(100 * (92.41 / 100.3 - 1), 1) == -7.9


def test_wti_d1w_in_an_ordinary_week_is_the_same_contract_anyway(panel):
    weekly = panel({
        "2026-10-09.json": named_week("2026-10-09", wti=(90.2, "CLX26"),
                                      nxt=(88.6, "CLZ26")),
        "2026-10-16.json": named_week("2026-10-16", wti=(89.0, "CLX26"),
                                      nxt=(87.5, "CLZ26")),
    })
    assert derive(weekly)["commodities"]["WTI"]["d1w"] == -1.3


def test_wti_d1w_is_null_when_last_week_holds_no_settlement_of_the_contract(
        panel):
    """The week before the roll lost its WTI_NEXT. A change from October to
    November is not shown as oil falling 7.9 percent."""
    before = named_week("2026-09-18", wti=(100.3, "CLV26"))
    weekly = panel({"2026-09-18.json": before,
                    "2026-09-25.json": ROLL["2026-09-25.json"]})
    wti = derive(weekly)["commodities"]["WTI"]
    assert wti["px"] == 92.41 and wti["d1w"] is None
    assert "no CLX26 settlement on file for 2026-09-18" in wti["d1w_reason"]
    assert "WTI is CLV26; WTI_NEXT is absent" in wti["d1w_reason"]
    assert "not a market move" in wti["d1w_reason"]


def test_wti_d1w_survives_a_week_that_lost_its_front_month(panel):
    """A Friday that was the front month's last day, read on the Saturday
    after the provider dropped it. WTI is missing; WTI_NEXT is there, and
    it is next week's contract."""
    weekly = panel({
        "2026-11-20.json": named_week("2026-11-20", nxt=(84.0, "CLF27")),
        "2026-11-27.json": named_week("2026-11-27", wti=(85.26, "CLF27"),
                                      nxt=(83.9, "CLG27")),
    })
    assert derive(weekly)["commodities"]["WTI"]["d1w"] == 1.5


def test_wti_d1w_needs_the_contract_of_this_weeks_close_on_record(panel):
    weekly = panel({"2026-08-28.json": old_week("2026-08-28", wti=83.4),
                    "2026-09-04.json": SEAM["2026-09-04.json"]})
    write_history(weekly, bc.empty_history())
    wti = derive(weekly)["commodities"]["WTI"]
    assert wti["px"] == 91.48 and wti["d1w"] is None
    assert "contract month of the 2026-09-04 close is not on record" in \
        wti["d1w_reason"]


def test_the_first_named_week_is_differenced_against_a_named_week(panel):
    """Why the settlement file confirms 2026-10-02 by name for WTI although
    the committed 91.11 was right: without the contract on record, the next
    week's change could not be shown to be one contract's."""
    weekly = panel(dict(SEAM, **{"2026-10-09.json": named_week(
        "2026-10-09", wti=(90.2, "CLX26"), nxt=(88.6, "CLZ26"),
        gold=(4150.0, "GCV26"), silver=(60.5, "SIV26"))}))
    write_history(weekly, committed_history())
    got = derive(weekly)["commodities"]
    assert got["WTI"]["d1w"] == -1.0
    assert got["GOLD"]["d1w"] == 0.4
    assert got["SILVER"]["d1w"] == 0.9
    assert got["GOLD"]["d4w"] is None, "2026-09-11 has no gold settlement"
    assert got["WTI"]["d4w"] == -9.8, "against the October contract's 100.05"


def test_the_settlement_file_is_an_input_the_purity_check_sees(panel):
    weekly = panel(SEAM)
    path = write_history(weekly, committed_history())
    facts = str(weekly.parent / "no-facts.json")
    out = weekly.parent / "market_state.json"
    snapshot._write_json(str(out), snapshot.derive_chain(str(weekly), facts))
    assert snapshot.rederive_and_compare(str(weekly), facts, str(out)) == (
        True, None)

    doc = committed_history()
    doc["instruments"]["GOLD"]["series"]["2026-10-02"]["close"] = 4140.0
    write_history(weekly, doc)
    match, where = snapshot.rederive_and_compare(str(weekly), facts, str(out))
    assert not match and where.startswith("$.commodities.GOLD")
    assert path.is_file()


def test_the_weekly_jobs_single_step_agrees_with_the_chain(panel):
    weekly = panel(SEAM)
    write_history(weekly, committed_history())
    facts = str(weekly.parent / "no-facts.json")
    last_week = snapshot.derive_chain(str(weekly), facts)
    weekly = panel({"2026-10-09.json": named_week(
        "2026-10-09", wti=(90.2, "CLX26"), nxt=(88.6, "CLZ26"),
        gold=(4150.0, "GCV26"), silver=(60.5, "SIV26"))})
    step = snapshot.derive_market_state(str(weekly), facts, last_week)
    chain = snapshot.derive_chain(str(weekly), facts)
    assert snapshot.canonical_json(step) == snapshot.canonical_json(chain)


# -- the gate on the settlement file and on market_state -----------------------

def gate(repo):
    rep = tc.Report()
    tc.check_feed(repo, rep)
    tc.check_commodity_history(repo, rep)
    return rep


def seam_repo(panel, extra=None, history=None, state=True):
    """A repo with the seam, its settlement file and a derived state."""
    weekly = panel(dict(SEAM, **(extra or {})))
    if history is not False:
        write_history(weekly, history or committed_history())
    if state:
        snapshot._write_json(str(weekly.parent / "market_state.json"),
                             derive(weekly))
    return weekly.parents[1], weekly


def test_the_gate_accepts_the_seam_as_this_change_commits_it(panel):
    repo, _ = seam_repo(panel)
    rep = gate(repo)
    assert fails(rep) == [] and warns(rep) == []
    assert any("validated (9 settlement(s), 3 week(s) recorded as "
               "unavailable)" in line for line in rep.lines)
    assert any("9 from data/commodity_settlements.json, 3 audited closes, "
               "3 unavailable" in line for line in rep.lines)
    assert any("WTI 91.11 (CLX26), GOLD 4133.7 (GCV26), SILVER 59.98 "
               "(SIV26)" in line for line in rep.lines)


def test_the_gate_and_the_deriver_agree_week_after_week(panel):
    """The gate recomputes px, the contract and four changes. Run it on
    every state a year of Fridays would derive, rolls included."""
    files, day = dict(SEAM), D(2026, 10, 9)
    price = 90.0
    while day <= D(2027, 3, 26):
        price *= 0.99 if day.day % 2 else 1.02
        files[day.isoformat() + ".json"] = named_week(
            day.isoformat(),
            wti=(round(price, 2), sm.contract_for("CL", day)),
            nxt=(round(price - 1.5, 2), sm.contract_for("CL", day, 1)),
            gold=(round(price * 46, 1), sm.contract_for("GC", day)),
            silver=(round(price / 1.5, 3), sm.contract_for("SI", day)))
        day += dt.timedelta(days=7)
    names = sorted(files)
    weekly = panel({names[0]: files[names[0]]})
    write_history(weekly, committed_history())
    rolled = 0
    for i in range(5, len(names)):
        (weekly / names[i]).write_text(json.dumps(files[names[i]]),
                                       encoding="utf-8")
        for name in names[:i]:
            if not (weekly / name).exists():
                (weekly / name).write_text(json.dumps(files[name]),
                                           encoding="utf-8")
        state = derive(weekly)
        snapshot._write_json(str(weekly.parent / "market_state.json"), state)
        rep = gate(weekly.parents[1])
        assert fails(rep) == [], names[i]
        wti = state["commodities"]["WTI"]
        if i > 5 and wti["d1w"] is not None and wti["contract"] != \
                sm.contract_for("CL", D.fromisoformat(names[i - 1][:10])):
            rolled += 1
    assert rolled >= 5, "the run crossed front-month changes"


def test_the_gate_refuses_a_state_that_shows_december_gold(panel):
    """The defect as it stood on main, 2026-10-05: 4162.3 under GOLD, and a
    four-week change measured from the September contract to the December
    one. This is what a runner on the old deriver would push."""
    repo, weekly = seam_repo(panel)
    state = derive(weekly)
    state["commodities"]["GOLD"].update(px=4162.3, d1w=-3.7, d4w=-6.0)
    state["commodities"]["GOLD"].pop("d1w_reason")
    snapshot._write_json(str(weekly.parent / "market_state.json"), state)
    got = fails(gate(repo))
    assert len(got) == 1
    assert "GOLD: px is 4162.3, derives as 4133.7" in got[0]
    assert "d1w is -3.7, derives as None" in got[0]
    assert "d4w is -6.0, derives as -6.7" in got[0]
    assert "WTI:" not in got[0], "only what is wrong is named"


def test_the_gate_refuses_a_state_with_no_contract_field(panel):
    """A deriver from before 2026-10-05 writes six fields per commodity."""
    repo, weekly = seam_repo(panel)
    state = derive(weekly)
    for rec in state["commodities"].values():
        rec.pop("contract", None)
    snapshot._write_json(str(weekly.parent / "market_state.json"), state)
    got = fails(gate(repo))
    assert len(got) == 1 and "no 'contract' field" in got[0]


def test_the_gate_refuses_front_against_front_in_a_roll_week(panel):
    weekly = panel(ROLL)
    write_history(weekly, bc.empty_history())
    state = derive(weekly)
    state["commodities"]["WTI"]["d1w"] = -7.9
    snapshot._write_json(str(weekly.parent / "market_state.json"), state)
    got = fails(gate(weekly.parents[1]))
    assert len(got) == 1 and "WTI: d1w is -7.9, derives as -3.8" in got[0]


def test_the_gate_refuses_a_null_once_the_settlement_exists(panel):
    """A week was filled and market_state was not re-derived."""
    repo, weekly = seam_repo(panel, extra={"2026-10-09.json": old_week(
        "2026-10-09", 90.2, 4178.4, 60.5)})
    doc = committed_history()
    doc["instruments"]["GOLD"]["series"]["2026-10-09"] = entry(
        4150.0, "GCV26", replaces=4178.4)
    write_history(weekly, doc)
    got = fails(gate(repo))
    assert len(got) == 1
    assert "GOLD: px is None, derives as 4150.0" in got[0]
    assert "rederive_market_state.py" in got[0]


def test_an_unlabelled_week_after_the_audit_is_a_warning_with_the_fix(panel):
    """The honest outcome is already in place -- market_state says null --
    so the gate names the weeks and the tool without refusing the panel."""
    repo, _ = seam_repo(panel, extra={"2026-10-09.json": old_week(
        "2026-10-09", 90.2, 4178.4, 60.5)})
    rep = gate(repo)
    assert fails(rep) == []
    got = warns(rep)
    assert len(got) == 4, "WTI, WTI_NEXT, GOLD and SILVER"
    gold = [line for line in got if "no GOLD settlement" in line][0]
    assert "1 week(s) have no GOLD settlement on a named contract: " \
           "2026-10-09." in gold
    assert "1 of them carry a close with no contract label" in gold
    assert "backfill_commodities.py" in gold
    nxt = [line for line in got if "WTI_NEXT" in line][0]
    assert "carry a close" not in nxt, "an old writer does not write it"


def test_the_gate_fails_where_a_state_was_derived_without_the_file(panel):
    """The runner's own gate, on the night it derives without the file. A
    missing file is only a warning in a tree that derives nothing."""
    repo, weekly = seam_repo(panel, history=False, state=False)
    rep = gate(repo)
    assert fails(rep) == [] and len(warns(rep)) == 1
    assert "data/commodity_settlements.json not found" in warns(rep)[0]
    assert "5 week(s), 2026-09-04 .. 2026-10-02" in warns(rep)[0]

    snapshot._write_json(str(weekly.parent / "market_state.json"),
                         derive(weekly))
    got = fails(gate(repo))
    assert len(got) == 1
    assert "data/commodity_settlements.json not found" in got[0]
    assert "copy it from the repo" in got[0]


def broken(change):
    doc = committed_history()
    change(doc["instruments"])
    return doc


@pytest.mark.parametrize("change,why", [
    (lambda i: i["WTI"]["series"].update(
        {"2026-08-28": entry(83.4, "CLV26", "CL=F")}),
     "names a week with no weekly file"),
    (lambda i: i["GOLD"]["unavailable"].update({"2026-10-02": dict(GONE)}),
     "is also listed as unavailable"),
    (lambda i: i["WTI"]["series"]["2026-09-18"]["replaces"].update(
        close=95.5), "says it replaces 95.5, but weekly/2026-09-18.json "
                     "holds 95.47"),
    (lambda i: i["WTI"]["series"]["2026-09-18"].pop("replaces"),
     "does not record that it replaces it"),
    (lambda i: i["GOLD"]["unavailable"]["2026-09-18"].pop("reason"),
     "gives no 'reason'"),
    (lambda i: i["GOLD"]["series"]["2026-10-02"].update(contract="GCZ26"),
     "cannot be the nearest-expiry contract"),
    (lambda i: i["GOLD"]["series"]["2026-10-02"].update(close=-1),
     "close -1 <= 0"),
    (lambda i: i["GOLD"]["series"]["2026-10-02"].pop("symbol"),
     "lacks 'symbol'"),
    (lambda i: i["GOLD"]["series"]["2026-10-02"].update(fetched_at="today"),
     "is not a UTC"),
    (lambda i: i.update(COPPER={"series": {}}), "is not one of WTI"),
    (lambda i: i["GOLD"].update(audited_through="last week"),
     "is not an ISO date"),
])
def test_the_gate_validates_the_settlement_file(panel, change, why):
    repo, _ = seam_repo(panel, history=broken(change), state=False)
    assert any(why in line for line in fails(gate(repo))), fails(gate(repo))


def test_the_gate_refuses_two_different_settlements_for_one_week(panel):
    """The deriver reads the weekly file's. The gate does not let the
    disagreement stand, because one of the two is wrong."""
    named = {"2026-10-09.json": named_week("2026-10-09",
                                           gold=(4150.0, "GCV26"))}
    doc = committed_history()
    doc["instruments"]["GOLD"]["series"]["2026-10-09"] = entry(
        4199.0, "GCV26")
    repo, weekly = seam_repo(panel, extra=named, history=doc, state=False)
    assert any("two different GOLD settlements" in line
               for line in fails(gate(repo)))

    doc["instruments"]["GOLD"]["series"]["2026-10-09"]["close"] = 4150.0
    write_history(weekly, doc)
    assert not any("two different" in line for line in fails(gate(repo)))


def test_the_gate_refuses_a_settlement_file_that_is_not_ascii(panel):
    repo, weekly = seam_repo(panel, state=False)
    doc = committed_history()
    doc["about"] = "gold " + chr(0x2014) + " spot month"
    Path(snapshot.commodity_history_path(str(weekly))).write_text(
        json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert any("not pure ASCII" in line for line in fails(gate(repo)))


# -- backfill_commodities.py ---------------------------------------------------

def run_tool(root, *args, now=NOW):
    return bc.main(["--data", str(root)] + list(args), now=now)


def read_history(root):
    return json.loads((root / "commodity_settlements.json")
                      .read_text(encoding="utf-8"))["instruments"]


REASON = "The file holds the December contract's settlement."


def test_a_week_is_read_by_contract_name_and_records_what_it_replaces(
        panel, provider):
    root = panel(SEAM).parent
    assert run_tool(root, "--week", "2026-10-02", "--instrument", "GOLD",
                    "--reason", REASON) == 0
    got = read_history(root)
    assert got["GOLD"]["series"] == {"2026-10-02": {
        "close": 4133.7002, "volume": 348, "contract": "GCV26",
        "symbol": "GCV26.CMX", "source": "yahoo-backfill",
        "fetched_at": STAMP, "reason": REASON,
        "replaces": {"close": 4162.2998, "volume": None}}}
    assert got["GOLD"]["audited_through"] == bc.AUDITED_THROUGH == \
        "2026-10-02"
    assert got["WTI_NEXT"] == {"root": "CL", "series": {}, "unavailable": {},
                               "audited_through": "2026-10-02"}
    raw = (root / "commodity_settlements.json").read_bytes()
    raw.decode("ascii")
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    assert raw.decode("ascii") == snapshot.canonical_json(json.loads(raw))


def test_a_close_that_was_right_is_confirmed_and_replaces_nothing(
        panel, provider):
    root = panel(SEAM).parent
    assert run_tool(root, "--week", "2026-10-02", "--instrument", "WTI",
                    "--instrument", "SILVER", "--reason", "by name") == 0
    got = read_history(root)
    assert got["WTI"]["series"]["2026-10-02"]["contract"] == "CLX26"
    assert "replaces" not in got["WTI"]["series"]["2026-10-02"]
    assert "replaces" not in got["SILVER"]["series"]["2026-10-02"]


def test_an_expired_contract_is_refused_by_name_and_says_how(
        panel, provider, capsys):
    root = panel(SEAM).parent
    assert run_tool(root, "--week", "2026-09-18", "--instrument", "WTI",
                    "--reason", "issue 110") == 2
    out = capsys.readouterr().out
    assert "REFUSED: WTI 2026-09-18: no data returned for CLV26.NYM" in out
    assert "--from-continuous" in out
    assert not (root / "commodity_settlements.json").exists()


def test_the_continuous_symbol_answers_on_proof(panel, provider):
    """CL=F's bars for the five sessions after October's last trade are the
    November contract's, by name. So its bar for 2026-09-18 is October's:
    100.30, where the file holds 95.47."""
    root = panel(SEAM).parent
    assert run_tool(root, "--week", "2026-09-18", "--instrument", "WTI",
                    "--instrument", "SILVER", "--from-continuous",
                    "--reason", "issue 110") == 0
    got = read_history(root)
    assert got["WTI"]["series"]["2026-09-18"] == {
        "close": 100.3, "volume": 112698, "contract": "CLV26",
        "symbol": "CL=F", "source": "yahoo-backfill", "fetched_at": STAMP,
        "reason": "issue 110", "replaces": {"close": 95.47, "volume": None}}
    silver = got["SILVER"]["series"]["2026-09-18"]
    assert (silver["close"], silver["contract"], silver["symbol"]) == (
        66.556, "SIU26", "SI=F")


def test_a_continuous_symbol_on_another_month_cannot_stand_in(
        panel, provider, capsys):
    """GC=F is the December contract. After September gold's last trade it
    holds 4179.70 where October settled 4147.70, so its bar for 2026-09-18
    is not the September contract's and is not taken."""
    root = panel(SEAM).parent
    assert run_tool(root, "--week", "2026-09-18", "--instrument", "GOLD",
                    "--from-continuous", "--reason", "x") == 2
    out = capsys.readouterr().out
    assert "GC=F is not the nearest-expiry chain at that roll" in out
    assert "it holds 4179.7002 where GCV26 settled 4147.7002" in out
    assert not (root / "commodity_settlements.json").exists()


def test_proof_needs_settled_sessions_of_the_next_contract(
        panel, provider, capsys):
    table, _ = provider
    table["CLX26.NYM"] = [r for r in CLX26 if r[0] != D(2026, 9, 23)
                          and r[0] <= D(2026, 9, 24)]
    table["CL=F"] = [r for r in CL_F if r[0] != D(2026, 9, 23)]
    root = panel(SEAM).parent
    assert run_tool(root, "--week", "2026-09-18", "--instrument", "WTI",
                    "--from-continuous", "--reason", "x") == 2
    assert "1 settled CLX26 session(s) by name" in capsys.readouterr().out


def test_unavailable_is_recorded_only_when_it_has_been_shown(
        panel, provider, capsys):
    root = panel(SEAM).parent
    assert run_tool(root, "--week", "2026-09-18", "--instrument", "GOLD",
                    "--unavailable", "--reason", GONE["reason"]) == 0
    gone = read_history(root)["GOLD"]["unavailable"]["2026-09-18"]
    assert gone["contract"] == "GCU26" and gone["reason"] == GONE["reason"]
    assert gone["checked_at"] == STAMP
    assert "the provider serves nothing for GCU26" in gone["evidence"]
    assert "GC=F is not the nearest-expiry chain" in gone["evidence"]

    for ticker, why in (("WTI", "CL=F can be shown to have held CLV26"),
                        ("SILVER", "SI=F can be shown to have held SIU26")):
        assert run_tool(root, "--week", "2026-09-18", "--instrument", ticker,
                        "--unavailable", "--reason", "x") == 2
        assert why in capsys.readouterr().out
    assert run_tool(root, "--week", "2026-10-02", "--instrument", "GOLD",
                    "--unavailable", "--reason", "x") == 2
    assert "the provider still serves GCV26" in capsys.readouterr().out


def test_no_answer_is_not_evidence_that_there_is_nothing(
        panel, provider, capsys):
    table, _ = provider
    table["GCU26.CMX"] = OSError("timed out")
    root = panel(SEAM).parent
    assert run_tool(root, "--week", "2026-09-18", "--instrument", "GOLD",
                    "--unavailable", "--reason", "x") == 2
    assert "the provider did not answer (OSError: timed out)" in \
        capsys.readouterr().out
    assert not (root / "commodity_settlements.json").exists()


def test_an_entry_is_never_rewritten(panel, provider, capsys):
    root = panel(SEAM).parent
    args = ("--week", "2026-10-02", "--instrument", "GOLD", "--reason", "x")
    assert run_tool(root, *args) == 0
    before = (root / "commodity_settlements.json").read_bytes()
    assert run_tool(root, *args) == 2
    assert "an entry is never rewritten" in capsys.readouterr().out
    assert (root / "commodity_settlements.json").read_bytes() == before


@pytest.mark.parametrize("args,why", [
    (("--week", "2026-08-28", "--instrument", "GOLD", "--reason", "x"),
     "no weekly file dated 2026-08-28"),
    (("--week", "2026-10-02", "--instrument", "GOLD"), "needs --reason"),
    (("--week", "2026-10-02", "--reason", "x"), "no instrument named"),
    (("--week", "2026-10-02", "--instrument", "COPPER", "--reason", "x"),
     "is not a commodity this feed names"),
    (("--week", "2026-10-02", "--instrument", "GOLD", "--instrument", "GOLD",
      "--reason", "x"), "named twice"),
    (("--week", "2026-10-02", "--instrument", "GOLD", "--instrument", "WTI",
      "--reason", "x", "--unavailable"), "the provider still serves"),
])
def test_one_refusal_writes_nothing(panel, provider, capsys, args, why):
    """One reviewed statement about one week, not whichever parts fetched."""
    root = panel(SEAM).parent
    assert run_tool(root, *args) == 2
    assert why in capsys.readouterr().out
    assert not (root / "commodity_settlements.json").exists()


def test_a_week_that_names_its_own_contract_takes_no_entry(
        panel, provider, capsys):
    root = panel({"2026-10-02.json": named_week(
        "2026-10-02", gold=(4133.7002, "GCV26"))}).parent
    assert run_tool(root, "--week", "2026-10-02", "--instrument", "GOLD",
                    "--reason", "x") == 2
    assert "names the contract of its own GOLD close" in \
        capsys.readouterr().out


def test_the_default_run_fills_what_a_stale_writer_left(panel, provider):
    """2026-10-02 written by the old writer after the audit date, in a tree
    whose audit stops a week earlier: three unlabelled closes and no
    WTI_NEXT. All four are read by name."""
    weekly = panel(SEAM)
    doc = bc.empty_history()
    for rec in doc["instruments"].values():
        rec["audited_through"] = "2026-09-25"
    write_history(weekly, doc)
    assert run_tool(weekly.parent) == 0
    got = read_history(weekly.parent)
    assert {t: sorted(rec["series"]) for t, rec in got.items()} == {
        t: ["2026-10-02"] for t in COMMODITIES}
    assert got["GOLD"]["series"]["2026-10-02"]["replaces"]["close"] == \
        4162.2998
    assert got["WTI_NEXT"]["series"]["2026-10-02"] == {
        "close": 89.43, "volume": 209718, "contract": "CLZ26",
        "symbol": "CLZ26.NYM", "source": "yahoo-backfill",
        "fetched_at": STAMP}
    assert "reason" not in got["GOLD"]["series"]["2026-10-02"]


def test_the_default_run_leaves_the_audited_panel_alone(panel, provider,
                                                        capsys):
    root = panel(SEAM).parent
    assert run_tool(root) == 0
    assert "Nothing to add" in capsys.readouterr().out
    assert not (root / "commodity_settlements.json").exists()


def test_a_week_it_cannot_fill_stays_a_gap_and_the_run_is_not_a_success(
        panel, provider, capsys):
    weekly = panel(SEAM)
    doc = bc.empty_history()
    for rec in doc["instruments"].values():
        rec["audited_through"] = "2026-09-18"
    write_history(weekly, doc)
    assert run_tool(weekly.parent) == 1
    out = capsys.readouterr().out
    got = read_history(weekly.parent)
    assert sorted(got["WTI"]["series"]) == ["2026-09-25", "2026-10-02"]
    assert sorted(got["GOLD"]["series"]) == ["2026-10-02"], (
        "September gold has expired; nothing is guessed for 2026-09-25")
    assert "! 2026-09-25 GOLD     not filled" in out
    assert "--from-continuous" in out and "--unavailable" in out


def test_a_dry_run_writes_nothing(panel, provider, capsys):
    root = panel(SEAM).parent
    assert run_tool(root, "--dry-run", "--week", "2026-10-02",
                    "--instrument", "GOLD", "--reason", "x") == 0
    assert "DRY RUN" in capsys.readouterr().out
    assert not (root / "commodity_settlements.json").exists()


def facts_file(repo):
    (repo / "macro").mkdir(exist_ok=True)
    (repo / "macro" / "facts.json").write_text(
        json.dumps({"schema": "macro-facts/v1"}), encoding="utf-8")


def test_a_fill_leaves_market_state_in_step_with_the_file(panel, provider):
    """Following the gate's advice must not end in a red gate: a new entry
    makes the committed state stale, so the tool re-derives it."""
    repo, weekly = seam_repo(panel, history=broken(
        lambda i: i["GOLD"]["series"].clear()))
    facts_file(repo)
    assert derive(weekly)["commodities"]["GOLD"]["px"] == 4162.3, (
        "with no entry the audited close is read: the December contract")
    assert run_tool(weekly.parent, "--week", "2026-10-02", "--instrument",
                    "GOLD", "--reason", REASON) == 0
    state = json.loads((weekly.parent / "market_state.json")
                       .read_text(encoding="utf-8"))
    assert state["commodities"]["GOLD"]["px"] == 4133.7
    assert fails(gate(repo)) == []


def test_check_passes_while_the_provider_still_agrees(panel, provider,
                                                      capsys):
    weekly = panel(SEAM)
    write_history(weekly, committed_history())
    assert run_tool(weekly.parent, "--check") == 0
    out = capsys.readouterr().out
    assert "9 settlement(s) on file: 9 checked against the provider, 0 on " \
           "a contract it no longer serves" in out


def test_check_reports_a_continuous_symbol_that_has_moved(panel, provider,
                                                          capsys):
    """What happened to gold, if it happens to silver: SI=F rebuilt onto
    the December contract. The entry stays; the difference is reported."""
    table, _ = provider
    table["SI=F"] = [(d, 67.149 if d == D(2026, 9, 18) else c, v)
                     for d, c, v in SI_F]
    weekly = panel(SEAM)
    path = write_history(weekly, committed_history())
    before = path.read_bytes()
    assert run_tool(weekly.parent, "--check") == 1
    out = capsys.readouterr().out
    assert "2026-09-18 SILVER (commodity_settlements.json): committed " \
           "66.556, SI=F now says 67.149" in out
    assert path.read_bytes() == before


def test_check_counts_an_expired_contract_and_does_not_fail_on_it(
        panel, provider, capsys):
    table, _ = provider
    del table["GCV26.CMX"]
    weekly = panel(SEAM)
    write_history(weekly, committed_history())
    assert run_tool(weekly.parent, "--check") == 0
    assert "8 checked against the provider, 1 on a contract it no longer " \
           "serves" in capsys.readouterr().out


def test_check_covers_a_weekly_files_own_named_close(panel, provider, capsys):
    weekly = panel({"2026-10-02.json": named_week(
        "2026-10-02", gold=(4140.0, "GCV26"))})
    assert run_tool(weekly.parent, "--check") == 1
    assert "2026-10-02 GOLD (weekly/2026-10-02.json): committed 4140.0, " \
           "GCV26.CMX now says 4133.7002" in capsys.readouterr().out


# -- the other tools -----------------------------------------------------------

def test_a_correction_restates_a_commodity_by_name_and_labels_it(
        panel, provider):
    """restate_instruments goes through the writer's fetch, so a commodity
    it restates is the named contract's and says so."""
    base = old_week("2026-10-02", 91.11, 4162.2998, 59.977)
    weekly = panel({"2026-10-02.json": base})
    doc = ri.restate(weekly, "2026-10-02", ["commodities.GOLD"],
                     "December contract under GOLD", now=NOW)
    assert doc["commodities"]["GOLD"] == {"close": 4133.7002, "volume": 348}
    assert doc["provenance"]["commodities"]["GOLD"] == {
        "source": "yahoo-backfill", "fetched_at": STAMP, "contract": "GCV26"}
    assert doc["restated"] == [{"block": "commodities", "ticker": "GOLD",
                                "was": {"close": 4162.2998, "volume": None}}]
    assert read_series(weekly, "GOLD") == {"2026-10-02": (4133.7002, "GCV26")}
    assert fails(file_gate(weekly.parents[1])) == []


def test_a_correction_cannot_reach_an_expired_contract(panel, provider):
    weekly = panel({"2026-09-18.json": SEAM["2026-09-18.json"]})
    with pytest.raises(ri.Refused, match="commodity_settlements.json"):
        ri.restate(weekly, "2026-09-18", ["commodities.WTI"], "issue 110",
                   now=NOW)


def audit(panel, files, histories, now=NOW):
    repo = panel(files).parents[1]
    return ai.run_audit(repo, ("weekly",),
                        lambda symbol, start, end: histories.get(symbol, {}),
                        now)


def as_history(rows):
    return {d.isoformat(): (c, v) for d, c, v in rows}


def test_the_audit_asks_a_named_file_about_its_own_contract(panel):
    """Not about GC=F, which is December: 4133.70 against 4162.30 would be
    a finding every week for a file that is right."""
    doc = named_week("2026-10-02", gold=(4133.7002, "GCV26"),
                     fetched_at="2026-10-03T13:07:47Z")
    result = audit(panel, {"2026-10-02.json": doc}, {
        "GCV26.CMX": as_history(GCV26), "GC=F": as_history(GC_F)})
    assert result["findings"] == []
    assert result["audited"]["panels"]["weekly"]["ok"] == 1

    doc["commodities"]["GOLD"]["close"] = 4162.2998
    result = audit(panel, {"2026-10-02.json": doc}, {
        "GCV26.CMX": as_history(GCV26), "GC=F": as_history(GC_F)})
    (finding,) = result["findings"]
    assert finding["symbol"] == "GCV26.CMX" and finding["class"] == "differs"


def test_the_audit_asks_an_old_file_about_the_continuous_symbol(panel):
    result = audit(panel, {"2026-10-02.json": SEAM["2026-10-02.json"]}, {
        "GC=F": as_history(GC_F), "SI=F": as_history(SI_F),
        "CL=F": as_history(CL_F), "GCV26.CMX": as_history(GCV26)})
    assert result["findings"] == [], "it equals GC=F, as it always did"
    assert result["audited"]["panels"]["weekly"]["ok"] == 3


def test_the_audit_leaves_out_a_close_on_an_expired_contract(panel):
    """Neither ok nor unverified: it can never be asked about again."""
    doc = named_week("2026-09-18", wti=(100.3, "CLV26"),
                     fetched_at="2026-09-19T13:07:00Z")
    result = audit(panel, {"2026-09-18.json": doc}, {})
    assert result["findings"] == []
    assert result["audited"]["panels"]["weekly"]["closes"] == 0
    assert result["audited"]["symbols"]["expired"] == ["CLV26.NYM"]
    assert "CLV26.NYM" not in result["audited"]["symbols"]["failed"]


def test_the_audit_asks_about_a_lost_commodity_by_the_calendars_contract(
        panel):
    doc = named_week("2026-10-02", fetched_at="2026-10-03T01:13:00Z")
    doc["missing"] = [{"ticker": "GOLD", "reason": "GCV26.CMX: the bar "
                       "dated 2026-10-02 is a quote"}]
    result = audit(panel, {"2026-10-02.json": doc}, {
        "GCV26.CMX": as_history(GCV26), "GC=F": as_history(GC_F)})
    (finding,) = result["findings"]
    assert finding["class"] == "absent" and finding["symbol"] == "GCV26.CMX"
    assert finding["provider"]["close"] == 4133.7002


# -- the CI guard on the settlement file ---------------------------------------

def ci_panel_check():
    """The inline script of ci.yml's panel step, as CI runs it."""
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml")
                         .read_text(encoding="utf-8"))
    step = [s for s in doc["jobs"]["test"]["steps"]
            if str(s.get("name", "")).startswith("Panel is intact")][0]
    return re.search(r"python - <<'PY'\n(.*)\nPY", step["run"], re.S).group(1)


@pytest.fixture
def two_commits(tmp_path):
    """A throwaway repo: commit one settlement file, then another, and run
    the CI step on the result. Returns (exit code, output)."""
    if shutil.which("git") is None:
        pytest.skip("git not available")

    def git(*args):
        r = subprocess.run(
            ["git", "-C", str(tmp_path), "-c", "user.name=t",
             "-c", "user.email=t@example.invalid", "-c", "core.autocrlf=false",
             "-c", "commit.gpgsign=false"] + list(args),
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

    def run(first, second):
        git("init", "-q")
        (tmp_path / "data").mkdir()
        script = tmp_path / "ci_panel_check.py"
        script.write_text(ci_panel_check(), encoding="utf-8")
        for n, doc in enumerate((first, second)):
            path = tmp_path / "data" / "commodity_settlements.json"
            if doc is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(json.dumps(doc), encoding="utf-8")
            (tmp_path / "marker.txt").write_text(str(n), encoding="utf-8")
            git("add", "-A")
            git("commit", "-q", "-m", "c%d" % n)
        r = subprocess.run([sys.executable, str(script)], cwd=str(tmp_path),
                           capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    return run


def test_ci_passes_a_settlement_file_that_only_grew(two_commits):
    after = committed_history()
    after["instruments"]["WTI"]["series"]["2026-10-09"] = entry(90.2, "CLX26")
    code, out = two_commits(committed_history(), after)
    assert code == 0, out
    assert "commodity settlements intact: 9 unchanged, 1 added" in out


def test_ci_passes_the_commit_that_introduces_the_file(two_commits):
    code, out = two_commits(None, committed_history())
    assert code == 0, out
    assert "commodity settlements: not in the previous commit" in out


def test_ci_passes_a_gap_that_was_filled(two_commits):
    after = committed_history()
    gold = after["instruments"]["GOLD"]
    gold["series"]["2026-09-18"] = entry(4391.2, "GCU26")
    del gold["unavailable"]["2026-09-18"]
    code, out = two_commits(committed_history(), after)
    assert code == 0, out


@pytest.mark.parametrize("change", [
    lambda i: i["WTI"]["series"]["2026-09-18"].update(close=95.47),
    lambda i: i["WTI"]["series"]["2026-09-18"].update(contract="CLX26"),
    lambda i: i["WTI"]["series"].pop("2026-09-18"),
    lambda i: i["GOLD"].update(audited_through="2026-10-09"),
    lambda i: i["GOLD"]["unavailable"].pop("2026-09-18"),
    lambda i: i.pop("SILVER"),
], ids=["close changed", "contract changed", "entry removed",
        "audit date moved", "gap dropped without a settlement",
        "instrument removed"])
def test_ci_fails_a_commit_that_rewrites_what_was_committed(two_commits,
                                                            change):
    code, out = two_commits(committed_history(), broken(change))
    assert code == 1, out
    assert "COMMODITY SETTLEMENT REGRESSION" in out


def test_ci_still_guards_the_us2y_history_in_the_same_step(two_commits,
                                                           tmp_path):
    """The two checks share one script; neither may end it early."""
    script = ci_panel_check()
    assert script.index("us2y_treasury.json") < \
        script.index("commodity_settlements.json")
    assert "sys.exit(0)" not in script.split("us2y_treasury.json", 1)[1]


# -- the committed data --------------------------------------------------------

WEEKLY = ROOT / "data" / "weekly"
COMMITTED = ROOT / "data" / "commodity_settlements.json"
# The last weekly file written before contracts were named. Everything up to
# it can only ever be answered by the settlement file, so the assertions
# below are about a fixed set and cannot be broken by a later Friday going
# wrong, or by a later fill.
AUDITED = "2026-10-02"


def committed():
    return json.loads(COMMITTED.read_text(encoding="utf-8"))


def test_the_committed_settlement_file_is_what_was_decided():
    """Owner decision 2026-10-05: eight closes replaced, two confirmed by
    name, four gold weeks with no settlement to be had."""
    doc = committed()
    assert doc["schema"] == bc.SCHEMA and doc["rule"] == "nearest-expiry"
    got = doc["instruments"]
    assert set(got) == set(COMMODITIES)
    assert {t: rec["audited_through"] for t, rec in got.items()} == {
        t: "2026-10-02" for t in COMMODITIES}

    def held(ticker):
        return {w: (e["close"], e["contract"], e["symbol"])
                for w, e in got[ticker]["series"].items() if w <= AUDITED}

    assert held("WTI") == {
        "2026-09-11": (100.05, "CLV26", "CL=F"),
        "2026-09-18": (100.3, "CLV26", "CL=F"),
        "2026-09-25": (92.41, "CLX26", "CLX26.NYM"),
        "2026-10-02": (91.11, "CLX26", "CLX26.NYM"),
    }
    assert held("GOLD") == {"2026-10-02": (4133.7002, "GCV26", "GCV26.CMX")}
    assert held("SILVER") == {
        "2026-08-28": (66.995, "SIU26", "SI=F"),
        "2026-09-11": (64.554, "SIU26", "SI=F"),
        "2026-09-18": (66.556, "SIU26", "SI=F"),
        "2026-09-25": (64.245, "SIU26", "SI=F"),
        "2026-10-02": (59.977, "SIV26", "SIV26.CMX"),
    }
    assert held("WTI_NEXT") == {}
    gaps = {t: sorted(w for w in rec["unavailable"] if w <= AUDITED)
            for t, rec in got.items()}
    assert gaps == {"WTI": [], "WTI_NEXT": [], "SILVER": [], "GOLD": [
        "2026-08-28", "2026-09-11", "2026-09-18", "2026-09-25"]}
    for week in gaps["GOLD"]:
        rec = got["GOLD"]["unavailable"][week]
        assert rec["contract"] == "GCU26"
        assert "GC=F is not the nearest-expiry chain" in rec["evidence"]


def test_every_committed_entry_says_what_the_weekly_file_holds():
    replaced, confirmed = 0, 0
    for ticker, rec in committed()["instruments"].items():
        for week, e in rec["series"].items():
            if week > AUDITED:
                continue
            held = json.loads((WEEKLY / (week + ".json")).read_text(
                encoding="utf-8"))["commodities"][ticker]
            assert e["reason"], (ticker, week)
            if "replaces" in e:
                assert e["replaces"] == held, (ticker, week)
                assert e["replaces"]["close"] != e["close"]
                replaced += 1
            else:
                assert held["close"] == e["close"], (ticker, week)
                confirmed += 1
    assert (replaced, confirmed) == (8, 2)


def test_the_wti_of_issue_110_is_no_longer_what_a_reader_gets():
    """2026-09-18.json still says 95.47, as it must. A reader gets 100.30,
    the October contract, which was the front month until 2026-09-22."""
    held = json.loads((WEEKLY / "2026-09-18.json").read_text(
        encoding="utf-8"))["commodities"]["WTI"]
    assert held == {"close": 95.47, "volume": 300567}
    assert read_series(WEEKLY, "WTI")["2026-09-18"] == (100.3, "CLV26")
    assert sm.contract_for("CL", D(2026, 9, 18)) == "CLV26"


def test_every_committed_week_reads_one_contract_or_says_why_not():
    docs = [(w, doc) for w, doc in snapshot._load_weekly_files(str(WEEKLY))
            if w <= AUDITED]
    assert len(docs) == 113
    history, problem = snapshot.load_commodity_history(str(COMMITTED))
    assert problem is None
    read = {}
    for ticker in ("WTI", "GOLD", "SILVER"):
        series = snapshot.commodity_series(docs, history, ticker)
        missing = [w for w, _ in docs if w not in series]
        assert missing == sorted(w for w in history[ticker]["unavailable"]
                                 if w <= AUDITED), ticker
        read[ticker] = len(series)
    assert read == {"WTI": 113, "GOLD": 109, "SILVER": 113}


def test_the_committed_state_is_on_the_nearest_expiry_contracts():
    state = json.loads((ROOT / "data" / "market_state.json").read_text(
        encoding="utf-8"))
    if state["as_of"] != "2026-10-02":
        pytest.skip("market_state has moved on to " + state["as_of"])
    got = state["commodities"]
    assert (got["GOLD"]["px"], got["GOLD"]["contract"]) == (4133.7, "GCV26")
    assert got["GOLD"]["d1w"] is None and got["GOLD"]["d4w"] == -6.7
    assert (got["GOLD"]["d13w"], got["GOLD"]["d52w"]) == (0.5, 6.5)
    assert (got["SILVER"]["contract"], got["SILVER"]["d1w"]) == (
        "SIV26", -6.6)
    assert got["WTI"] == {"px": 91.11, "contract": "CLX26", "d1w": -1.4,
                          "d4w": -0.4, "d13w": 32.6, "d52w": 49.7,
                          "pctile_2y": 86}


def test_the_gate_passes_the_committed_tree():
    rep = tc.Report()
    tc.check_commodity_history(ROOT, rep)
    assert fails(rep) == []
