"""An entry open is an open only when its own bar bears it out (#105).

At 09:35-09:42 ET on Monday 2026-09-14 the provider's forming daily bar
carried an Open that was a verbatim copy of Friday's, while High, Low and
Close followed the live session. For five of seven tickers checked the Open
lay outside that same bar's range. `arena_ingest.entry_price` took any open
above zero, and `tracker.fetch_yf_open` returned the bar's Open whatever it
was, so both books would have been entered at prices nobody could have
traded that morning. The paper book was repriced onto them, then reverted by
hand to Friday's closes, and that week was scored +0.23% where Monday open
to Friday close was -0.31% (#112).

The rule in both scripts: low <= open <= high of the same bar, beyond float
noise, or it is not an open. What each does with one that is not differs,
because each reads the entry again differently when the week closes:

- `arena_ingest.py --close` writes the whole file again from settled bars,
  so a lock file is provisional. A lock run records the bar's Close (the
  last trade so far) and says so: `close_open_rejected`, with the open and
  the range it failed beside it. A --close run refuses, because a closed
  week is final.
- `tracker.py --close` re-reads the entry by its recorded source. A Close
  booked minutes after the open would be scored from Monday's settled close,
  a different window from the Arena's. So --open books nothing and exits 2.

The check cannot tell a stale open from a range that is wrong. On
2026-10-06, six hours into the session, eight of 323 names read had a true
open outside the day's range as the provider gave it. Those fail too. The
settled bar has not been seen to fail, and it is what decides.

No network: the provider is stubbed where each script meets it. The five
impossible bars are the issue's own rows. Every other bar here says where
it is from, and which of its numbers are made up.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import sys

import pytest
import yaml
import yfinance  # the stub conftest installs

from conftest import ROOT

import arena_ingest as ai  # noqa: E402  (conftest stubs the provider)

D = dt.date
NAN = float("nan")


def _load_tracker():
    """portfolio/ is not a package, and the job runs tracker.py as a file.
    Importing it creates portfolio/, portfolio/history/ and scorecards/ when
    they are missing; all three are committed, so here that is a no-op."""
    for name in ("portfolio", "portfolio/history", "scorecards"):
        assert (ROOT / name).is_dir(), name
    spec = importlib.util.spec_from_file_location(
        "portfolio_tracker", ROOT / "portfolio" / "tracker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tk = _load_tracker()

MON = D(2026, 9, 14)
FRI = D(2026, 9, 18)

# The provider's 2026-09-14 daily bar as it read at 09:35-09:42 ET that
# morning: open, high, low, from the table in issue #105. The fourth number
# is the live price the hand-made lock file of that morning recorded at
# about 09:42 ET (arena/2026-09-14.yaml as committed in 4235542); DE was in
# the Council's book, not the Arena's, and has none on record.
MORNING = {
    "TSM": (431.55, 420.97, 416.02, 418.75),
    "SPY": (764.72, 759.19, 758.45, 759.015),
    "XOM": (165.07, 169.45, 168.25, 168.88),
    "DE": (685.92, 674.99, 668.26, None),
    "CBOE": (290.99, 287.04, 283.40, 284.93),
}
ABOVE = ("TSM", "SPY", "DE", "CBOE")
BELOW = ("XOM",)

# A bar that is right: SPY on Monday 2026-10-05 as the provider had it the
# next afternoon. Its Open is the spy_entry the book of that week holds.
SPY_OCT5 = {"Open": 769.6900024414062, "High": 776.6099853515625,
            "Low": 769.6300048828125, "Close": 774.8300170898438}

# The other way a forming bar contradicts itself. Tuesday 2026-10-06 as the
# provider had it at 15:32 ET, six hours into the session: open, high, low,
# last. Each Open is the 09:30 one-minute bar's own, so it is the true open.
# The day's range is what was wrong: it had left the opening print out. Eight
# of 323 bars read so (the price feed's names and the four index ETFs), all
# eight NYSE-listed.
SESSION = D(2026, 10, 6)
RANGE_LEFT_THE_OPEN_OUT = {
    "PEG": (69.12, 71.605, 69.15, 71.43),       # open below the low
    "COLD": (14.30, 14.255, 13.8001, 13.845),   # open above the high
}


def bar(o, high, low, close=None):
    """A provider row. No Close when the record has none."""
    row = {"Open": o, "High": high, "Low": low}
    if close is not None:
        row["Close"] = close
    return row


def morning(ticker):
    return bar(*MORNING[ticker])


def around(o, close=None):
    """A row whose range is MADE UP to hold a known open (and close): for
    bars whose high and low are not on record anywhere."""
    prices = [o] + ([close] if close is not None else [])
    return bar(o, max(prices) * 1.01, min(prices) * 0.99,
               o if close is None else close)


class Frame:
    """What the provider hands back, as far as either script looks at it:
    Ticker.history for arena_ingest.fetch_bar, download for
    tracker.fetch_yf_open."""

    columns = ("Close", "High", "Low", "Open", "Volume")

    def __init__(self, rows):
        self.rows = rows

    @property
    def empty(self):
        return not self.rows

    def iterrows(self):
        for day, fields in self.rows:
            yield dt.datetime(day.year, day.month, day.day), dict(fields)


@pytest.fixture
def provider(monkeypatch):
    """Stub yfinance at both doors. Returns (table, calls): set
    table[symbol] to {date: row} or to an exception."""
    table, calls = {}, []

    def answer(symbol, start, end):
        calls.append((symbol, start, end))
        rows = table.get(symbol, {})
        if isinstance(rows, Exception):
            raise rows
        return Frame([(day, rows[day]) for day in sorted(rows)
                      if start <= day.isoformat() < end])

    class Ticker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, start=None, end=None):
            return answer(self.symbol, start, end)

    def download(symbol, start=None, end=None, progress=False,
                 auto_adjust=True):
        assert auto_adjust is True
        return answer(symbol, start, end)

    monkeypatch.setattr(yfinance, "Ticker", Ticker, raising=False)
    monkeypatch.setattr(yfinance, "download", download, raising=False)
    return table, calls


@pytest.fixture(autouse=True)
def nothing_in_the_repo(tmp_path, monkeypatch):
    """Every path the tracker writes, moved under tmp_path. The official
    book is never touched by a test, whatever the test gets wrong."""
    book = tmp_path / "portfolio"
    book.mkdir()
    monkeypatch.setattr(tk, "PORTFOLIO_DIR", book)
    monkeypatch.setattr(tk, "CURRENT_PATH", book / "current.yaml")
    monkeypatch.setattr(tk, "HISTORY_DIR", book / "history")
    monkeypatch.setattr(tk, "METRICS_PATH", book / "metrics.json")
    monkeypatch.setattr(tk, "SCORECARDS_DIR", tmp_path / "scorecards")
    monkeypatch.setattr(tk, "SCOREBOARD_PATH", tmp_path / "scoreboard.md")
    monkeypatch.setattr(tk, "REPORTS_DIR", tmp_path / "reports")


def when(day):
    return dt.datetime(day.year, day.month, day.day)


# -- the rule ------------------------------------------------------------------

@pytest.mark.parametrize("ticker", ABOVE)
def test_an_open_above_its_own_high_is_not_an_open(ticker):
    o, high, low, _ = MORNING[ticker]
    for said in (tk.open_fault(o, high, low),
                 ai.open_fault({"open": o, "high": high, "low": low,
                                "close": low})):
        assert "open %s is above the bar's high %s" % (o, high) in said
        assert "(low %s)" % low in said


@pytest.mark.parametrize("ticker", BELOW)
def test_an_open_below_its_own_low_is_not_an_open(ticker):
    o, high, low, _ = MORNING[ticker]
    for said in (tk.open_fault(o, high, low),
                 ai.open_fault({"open": o, "high": high, "low": low,
                                "close": low})):
        assert "open %s is below the bar's low %s" % (o, low) in said
        assert "(high %s)" % high in said


def test_an_open_inside_its_own_range_stands():
    b = SPY_OCT5
    assert tk.open_fault(b["Open"], b["High"], b["Low"]) is None
    assert ai.open_fault({"open": b["Open"], "high": b["High"],
                          "low": b["Low"], "close": b["Close"]}) is None


@pytest.mark.parametrize("o", [420.97, 416.02])
def test_an_open_that_is_the_days_high_or_low_stands(o):
    """A session that opens at its high, or at its low, is an ordinary one:
    every bar starts with open == high == low."""
    assert tk.open_fault(o, 420.97, 416.02) is None
    assert ai.open_fault({"open": o, "high": 420.97, "low": 416.02,
                          "close": 418.75}) is None
    assert tk.open_fault(418.75, 418.75, 418.75) is None


def test_the_allowance_is_float_noise_and_a_cent_is_not_noise():
    high, low = 420.97, 416.02
    hair = high * 1e-9                      # the last bits of a float
    assert tk.open_fault(high + hair, high, low) is None
    assert tk.open_fault(low - hair, high, low) is None
    for off in (0.01, 0.005):               # a cent, half a cent
        assert "above" in tk.open_fault(high + off, high, low)
        assert "below" in tk.open_fault(low - off, high, low)
        assert "above" in ai.open_fault(
            {"open": high + off, "high": high, "low": low, "close": low})
    # and it scales with the price, so it is not a cent on a cheap name
    assert "above" in tk.open_fault(8.7301, 8.73, 8.59)


@pytest.mark.parametrize("high, low", [
    (None, None), (None, 416.02), (420.97, None)])
def test_a_bar_with_no_high_or_low_does_not_pass_by_default(high, low):
    """An open nothing can check is not one that was checked."""
    assert "cannot be checked" in tk.open_fault(418.75, high, low)
    assert "cannot be checked" in ai.open_fault(
        {"open": 418.75, "high": high, "low": low, "close": 418.75})
    # a bar built before the range was read has no such keys at all
    assert "cannot be checked" in ai.open_fault(
        {"open": 418.75, "close": 418.75})


@pytest.mark.parametrize("ticker", sorted(RANGE_LEFT_THE_OPEN_OUT))
def test_the_bar_does_not_say_which_field_is_wrong_so_a_true_open_fails_too(
        provider, ticker):
    """Not every bar that fails has a stale open. These two had true ones,
    and it was the range that was wrong; the bar reads the same either way.
    So the tracker books nothing, the Arena's lock run keeps the numbers
    beside its stand-in, and the settled bar is what decides."""
    table, _ = provider
    o, high, low, last = RANGE_LEFT_THE_OPEN_OUT[ticker]
    table[ticker] = {SESSION: bar(o, high, low, last)}
    with pytest.raises(tk.OpenNotVerified) as exc:
        tk.fetch_yf_open(ticker, when(SESSION))
    assert ("above the bar's high" in str(exc.value)) == (o > high)
    assert ("below the bar's low" in str(exc.value)) == (o < low)
    got = ai.fetch_bar(ticker, SESSION)
    assert ai.entry_price(got) == (last, "close_open_rejected")
    assert ai.rejected_open(got) == {"open": o, "high": high, "low": low}


def test_the_two_copies_of_the_rule_give_one_answer():
    """Two scripts that are copied to the runner one file at a time, so
    neither can import the other. One rule, held to one answer."""
    assert tk.OPEN_RANGE_TOL == ai.OPEN_RANGE_TOL
    high, low = 420.97, 416.02
    opens = [431.55, high + 0.01, high * (1 + 2e-6), high * (1 + 5e-7), high,
             418.75, low * (1 + 5e-7), low, low * (1 - 5e-7),
             low * (1 - 2e-6), low - 0.01, 165.07]
    ranges = [(high, low), (None, low), (high, None), (None, None),
              (low, high)]                  # the last: high below low
    for o in opens:
        for hi, lo in ranges:
            ours = tk.open_fault(o, hi, lo)
            theirs = ai.open_fault({"open": o, "high": hi, "low": lo,
                                    "close": 418.75})
            assert (ours is None) == (theirs is None), (o, hi, lo)
            if ours is not None:
                assert ours == theirs, (o, hi, lo)
    for ticker, (o, hi, lo, _) in MORNING.items():
        assert tk.open_fault(o, hi, lo), ticker


# -- the Arena: what a bar yields ----------------------------------------------

def test_fetch_bar_reads_the_range_with_the_open(provider):
    table, calls = provider
    table["SPY"] = {D(2026, 10, 5): SPY_OCT5}
    got = ai.fetch_bar("SPY", D(2026, 10, 5))
    assert got == {"open": 769.6900024414062, "close": 774.8300170898438,
                   "high": 776.6099853515625, "low": 769.6300048828125}
    assert calls == [("SPY", "2026-10-04", "2026-10-09")]
    assert ai.entry_price(got) == (769.69, "open")


def test_fetch_bar_says_none_for_a_bound_the_bar_does_not_have(provider):
    table, _ = provider
    table["A"] = {MON: {"Open": 100.0, "Close": 101.0}}
    table["B"] = {MON: {"Open": 100.0, "Close": 101.0,
                        "High": NAN, "Low": None}}
    for ticker in ("A", "B"):
        got = ai.fetch_bar(ticker, MON)
        assert got["high"] is None and got["low"] is None
        assert got["open"] == 100.0 and got["close"] == 101.0


@pytest.mark.parametrize("ticker", ["TSM", "SPY", "XOM", "CBOE"])
def test_the_close_stands_in_for_an_open_the_bar_rejects(ticker):
    """What the issue asked for and the lock file of 2026-09-14 did by
    hand: not the open, the live price, and a source that says so."""
    o, high, low, last = MORNING[ticker]
    b = {"open": o, "high": high, "low": low, "close": last}
    assert ai.entry_price(b) == (last, "close_open_rejected")
    assert ai.rejected_open(b) == {"open": o, "high": high, "low": low}


def test_a_stand_in_is_held_to_the_same_range():
    """A bar whose Open and Close are both outside its range cannot vouch
    for either, and one with no range cannot vouch for anything."""
    o, high, low, _ = MORNING["TSM"]
    for close in (o, 400.0, NAN):
        b = {"open": o, "high": high, "low": low, "close": close}
        assert ai.entry_price(b) == (None, None)
        assert ai.rejected_open(b) == {"open": o, "high": high, "low": low}
    unchecked = {"open": 418.75, "high": None, "low": None, "close": 418.75}
    assert ai.entry_price(unchecked) == (None, None)
    assert ai.rejected_open(unchecked) == {"open": 418.75, "high": None,
                                           "low": None}


def test_a_bar_with_no_open_falls_back_to_its_close_as_before():
    """Unchanged: there is no open to reject, and "close" still means the
    bar had none."""
    for o in (0.0, NAN, None):
        b = {"open": o, "high": 420.97, "low": 416.02, "close": 418.75}
        assert ai.entry_price(b) == (418.75, "close")
        assert ai.open_fault(b) is None and ai.rejected_open(b) is None
    assert ai.entry_price(None) == (None, None)
    assert ai.open_fault(None) is None and ai.rejected_open(None) is None


# -- the Arena: a lock run, and a close run ------------------------------------

def run_arena(monkeypatch, tmp_path, entries, *flags):
    path = tmp_path / "entries.txt"
    path.write_text(entries, encoding="ascii", newline="\n")
    out = tmp_path / "arena"
    monkeypatch.setattr(sys, "argv", [
        "arena_ingest.py", "--week", MON.isoformat(), "--entries", str(path),
        "--outdir", str(out)] + list(flags))
    ai.main()
    return yaml.safe_load((out / "2026-09-14.yaml").read_text(
        encoding="ascii"))


# Four of the five names GrandMastaShake locked that week. MO is left out:
# its open was rejected too, and its high and low are on no record.
ENTRY = "player: GrandMastaShake\nXOM 20%\nTSM 15%\nCBOE 15%\nDDOG 10%\n"


def lock_morning(table):
    for ticker in ("XOM", "TSM", "CBOE", "SPY"):
        table[ticker] = {MON: morning(ticker)}
    # DDOG's open that morning, 224.955, passed. Its range is made up.
    table["DDOG"] = {MON: around(224.955)}


def test_a_lock_run_books_the_live_price_and_says_what_it_is(
        provider, monkeypatch, tmp_path, capsys):
    """2026-09-14 again, through the script: the prices it writes are the
    ones the hand-made lock file held, and no stale open is called one."""
    table, _ = provider
    lock_morning(table)
    doc = run_arena(monkeypatch, tmp_path, ENTRY)

    assert doc["status"] == "open"
    assert doc["benchmark"] == {
        "ticker": "SPY", "entry_price": 759.015,
        "entry_price_source": "close_open_rejected",
        "open_rejected": {"open": 764.72, "high": 759.19, "low": 758.45}}
    picks = {p["ticker"]: p for p in doc["players"][0]["picks"]}
    assert picks["XOM"] == {
        "ticker": "XOM", "weight": 0.2, "entry_price": 168.88,
        "entry_price_source": "close_open_rejected",
        "open_rejected": {"open": 165.07, "high": 169.45, "low": 168.25}}
    assert picks["TSM"]["entry_price"] == 418.75
    assert picks["TSM"]["open_rejected"]["open"] == 431.55
    assert picks["CBOE"]["entry_price"] == 284.93
    assert picks["DDOG"] == {"ticker": "DDOG", "weight": 0.1,
                             "entry_price": 224.955,
                             "entry_price_source": "open"}
    for p in list(picks.values()) + [doc["benchmark"]]:
        if p["entry_price_source"] == "open":
            assert "open_rejected" not in p
        else:
            low, high = p["open_rejected"]["low"], p["open_rejected"]["high"]
            assert not low <= p["open_rejected"]["open"] <= high
            assert low <= p["entry_price"] <= high

    said = capsys.readouterr().out
    assert "WARN: TSM 2026-09-14: open 431.55 is above the bar's high 420.97" \
        in said
    assert "WARN: XOM 2026-09-14: open 165.07 is below the bar's low 168.25" \
        in said
    assert "Not booked as an open" in said and "DDOG" not in said
    said.encode("ascii")


def test_a_lock_run_books_no_price_from_a_bar_nothing_can_check(
        provider, monkeypatch, tmp_path, capsys):
    table, _ = provider
    lock_morning(table)
    table["TSM"] = {MON: {"Open": 431.55, "Close": 418.75}}     # no range
    doc = run_arena(monkeypatch, tmp_path, ENTRY)
    picks = {p["ticker"]: p for p in doc["players"][0]["picks"]}
    assert picks["TSM"] == {
        "ticker": "TSM", "weight": 0.15, "entry_price": None,
        "entry_price_source": None,
        "open_rejected": {"open": 431.55, "high": None, "low": None}}
    assert "TSM 2026-09-14: open 431.55 cannot be checked, the bar has no " \
        "high/low. Not booked as an open, and nothing else in the bar could " \
        "be checked: no entry price." in capsys.readouterr().out


# The week as arena/2026-09-14.yaml closed it on 2026-09-21: settled Monday
# opens and Friday closes, dividend-adjusted. The settled highs and lows are
# on no record, so the ranges are made up to hold them.
CLOSED = {            # ticker: (weight, entry, exit, return_pct)
    "XOM": (0.2, 168.7, 163.54, -3.06),
    "MO": (0.2, 68.9685, 69.52, 0.8),
    "TSM": (0.15, 414.897, 434.67, 4.77),
    "CBOE": (0.15, 285.04, 272.86, -4.27),
    "DDOG": (0.1, 225.02, 229.92, 2.18),
}
SPY_CLOSED = (757.1199, 761.69, 0.6)
FULL_ENTRY = ("player: GrandMastaShake\nXOM 20%\nMO 20%\nTSM 15%\nCBOE 15%\n"
              "DDOG 10%\n")


def settled_week(table):
    for ticker, (_, entry, exit_, _) in CLOSED.items():
        table[ticker] = {MON: around(entry), FRI: around(exit_)}
    table["SPY"] = {MON: around(SPY_CLOSED[0]), FRI: around(SPY_CLOSED[1])}


def test_a_week_with_sound_bars_closes_to_the_numbers_on_record(
        provider, monkeypatch, tmp_path):
    """Nothing about scoring moved: the same opens and closes give the
    committed week, GrandMastaShake -0.16% against SPY +0.60%."""
    table, _ = provider
    settled_week(table)
    doc = run_arena(monkeypatch, tmp_path, FULL_ENTRY, "--close")

    assert doc["status"] == "closed"
    assert doc["benchmark"] == {
        "ticker": "SPY", "entry_price": 757.1199,
        "entry_price_source": "open", "exit_price": 761.69,
        "return_pct": 0.6}
    player = doc["players"][0]
    for pick in player["picks"]:
        weight, entry, exit_, ret = CLOSED[pick["ticker"]]
        assert pick == {"ticker": pick["ticker"], "weight": weight,
                        "entry_price": entry, "entry_price_source": "open",
                        "exit_price": exit_, "return_pct": ret}
    assert player["weekly_return_pct"] == -0.16
    assert player["alpha_vs_spy_pct"] == -0.76


def test_a_close_run_refuses_an_entry_bar_that_contradicts_itself(
        provider, monkeypatch, tmp_path, capsys):
    """A closed week is final. Had the Monday bars still read on the 21st
    as they did at 09:40 on the 14th, the week is not scored: exit 2, and
    the lock file is as it was."""
    table, calls = provider
    settled_week(table)
    table["TSM"][MON] = morning("TSM")
    table["SPY"][MON] = morning("SPY")
    out = tmp_path / "arena"
    out.mkdir()
    lock = out / "2026-09-14.yaml"
    lock.write_bytes(b"week: '2026-09-14'\nstatus: open\n")

    with pytest.raises(SystemExit) as exc:
        run_arena(monkeypatch, tmp_path, FULL_ENTRY, "--close")
    assert exc.value.code == 2
    assert lock.read_bytes() == b"week: '2026-09-14'\nstatus: open\n"
    assert sorted(p.name for p in out.iterdir()) == ["2026-09-14.yaml"]

    said = capsys.readouterr().out
    assert "REFUSED: " in said and "not written" in said
    assert "2 entry bar(s)" in said
    assert "  TSM 2026-09-14: open 431.55 is above the bar's high 420.97 " \
        "(low 416.02)" in said
    assert "  SPY 2026-09-14: open 764.72 is above the bar's high 759.19 " \
        "(low 758.45)" in said
    assert "Run --close again later" in said
    # refused on the entry bars, before a Friday bar was asked for
    assert len(calls) == 6 and "Fetching Friday" not in said
    said.encode("ascii")


def test_a_refused_close_writes_no_directory_either(
        provider, monkeypatch, tmp_path):
    table, _ = provider
    settled_week(table)
    table["XOM"][MON] = {"Open": 165.07, "Close": 168.88}       # no range
    with pytest.raises(SystemExit) as exc:
        run_arena(monkeypatch, tmp_path, FULL_ENTRY, "--close")
    assert exc.value.code == 2
    assert not (tmp_path / "arena").exists()


# -- the Tracker: the open, or nothing -----------------------------------------

def test_the_tracker_returns_an_open_its_bar_bears_out(provider):
    table, calls = provider
    table["SPY"] = {D(2026, 10, 5): SPY_OCT5}
    assert tk.fetch_yf_open("SPY", when(D(2026, 10, 5))) \
        == 769.6900024414062
    assert calls == [("SPY", "2026-10-05", "2026-10-12")]


@pytest.mark.parametrize("ticker", sorted(MORNING))
def test_the_tracker_does_not_return_an_impossible_open(provider, ticker):
    table, _ = provider
    table[ticker] = {MON: morning(ticker)}
    o, high, low, _ = MORNING[ticker]
    with pytest.raises(tk.OpenNotVerified) as exc:
        tk.fetch_yf_open(ticker, when(MON))
    said = str(exc.value)
    assert said.startswith("%s 2026-09-14: open %s is " % (ticker, o))
    assert ("above the bar's high %s" % high in said) == (ticker in ABOVE)
    assert ("below the bar's low %s" % low in said) == (ticker in BELOW)


@pytest.mark.parametrize("o", [420.97, 416.02])
def test_the_tracker_returns_an_open_at_the_edge_of_its_range(provider, o):
    table, _ = provider
    table["TSM"] = {MON: bar(o, 420.97, 416.02, 418.75)}
    assert tk.fetch_yf_open("TSM", when(MON)) == o


@pytest.mark.parametrize("row, why", [
    ({"Open": 418.75, "Close": 418.75}, "cannot be checked"),
    ({"Open": 418.75, "High": NAN, "Low": NAN}, "cannot be checked"),
    ({"Open": 418.75, "High": 420.97, "Low": None}, "cannot be checked"),
    ({"Open": NAN, "High": 420.97, "Low": 416.02}, "no usable open"),
    ({"Open": 0.0, "High": 0.0, "Low": 0.0}, "no usable open"),
])
def test_the_tracker_does_not_return_an_open_it_cannot_check(
        provider, row, why):
    """Missing or NaN, a high or a low that is not there is not a check
    that passed. Nor is an open that is not a price: until this rule a NaN
    was returned as it came and booked under "open"."""
    table, _ = provider
    table["TSM"] = {MON: row}
    with pytest.raises(tk.OpenNotVerified) as exc:
        tk.fetch_yf_open("TSM", when(MON))
    assert why in str(exc.value)


def test_no_bar_yet_is_still_none_and_not_a_refusal(provider, capsys):
    """Unchanged. Before the open there is no Monday row at all, and a
    failed request is no row either: both are None, for the caller's
    close-based fallback. Only a bar that is there can be refused."""
    table, _ = provider
    assert tk.fetch_yf_open("TSM", when(MON)) is None
    table["TSM"] = {D(2026, 9, 11): around(431.55)}     # Friday is not asked
    assert tk.fetch_yf_open("TSM", when(MON)) is None
    table["TSM"] = OSError("timed out")
    assert tk.fetch_yf_open("TSM", when(MON)) is None
    assert "Could not fetch open for TSM" in capsys.readouterr().out


def test_a_holiday_monday_is_pinned_to_the_next_session_and_held_to_it(
        provider, capsys):
    """Labor Day, 2026-09-07. The entry is the first session after it, and
    that bar's open is checked like any other. (526.23 is where the book of
    that week entered LMT; the ranges and the second row are made up.)"""
    table, _ = provider
    labor_day, tuesday = D(2026, 9, 7), D(2026, 9, 8)
    table["LMT"] = {tuesday: bar(526.23, 529.0, 521.5),
                    D(2026, 9, 9): bar(524.0, 527.0, 520.0)}
    assert tk.fetch_yf_open("LMT", when(labor_day)) == 526.23
    assert "LMT entry pinned to 2026-09-08 open (no bar on 2026-09-07)" \
        in capsys.readouterr().out
    table["LMT"][tuesday] = bar(535.0, 529.0, 521.5)
    with pytest.raises(tk.OpenNotVerified) as exc:
        tk.fetch_yf_open("LMT", when(labor_day))
    assert "LMT 2026-09-08: open 535.0 is above the bar's high 529.0" \
        in str(exc.value)


# -- the Tracker: a book, or no file -------------------------------------------

# The Council's book for the week of 2026-09-14, as its report listed it.
PICKS = [("ALL", 0.183, "Cecil"), ("PSX", 0.167, "Marky"),
         ("HIG", 0.148, "Cecil"), ("DE", 0.10, "Marky")]
REPORT = {"vix": 15.84, "fed_stance": "Hold.",
          "picks": [{"ticker": t, "weight": w, "sponsor": s}
                    for t, w, s in PICKS]}
REPORT_MD = (
    "**Date:** 2026-09-14\n**VIX:** 15.84\n**Fed Stance:** Hold.\n\n"
    "## Top 5 Portfolio Picks\n| Ticker | Weight | Sponsor |\n|---|---|---|\n"
    + "".join("| %s | %.1f%% | %s |\n" % (t, w * 100, s) for t, w, s in PICKS))

# What the book of that week was reverted to: Friday 2026-09-11's closes
# (portfolio/history/2026-09-14.yaml).
FRIDAY_CLOSE = {"ALL": 253.71, "PSX": 259.47, "HIG": 136.36, "DE": 675.74,
                "SPY": 764.29}


def that_morning(table):
    """DE and SPY as the issue has them. ALL, PSX and HIG are on no record
    for that morning: their rows are made up, and sound."""
    table["DE"] = {MON: morning("DE")}
    table["SPY"] = {MON: morning("SPY")}
    for ticker in ("ALL", "PSX", "HIG"):
        table[ticker] = {MON: around(FRIDAY_CLOSE[ticker])}


def no_fallback(monkeypatch):
    asked = []

    def fetch_yf_price(ticker, date):
        asked.append(ticker)
        return FRIDAY_CLOSE[ticker]

    monkeypatch.setattr(tk, "fetch_yf_price", fetch_yf_price)
    return asked


def test_a_sound_morning_is_booked_at_its_opens_and_says_open(
        provider, monkeypatch):
    table, _ = provider
    that_morning(table)
    table["DE"] = {MON: around(670.5)}                  # made up, sound
    table["SPY"] = {MON: bar(758.9, 759.19, 758.45)}    # inside its range
    asked = no_fallback(monkeypatch)

    current = tk.open_positions("2026-09-14", REPORT)

    assert asked == []
    on_file = yaml.safe_load(tk.CURRENT_PATH.read_text(encoding="utf-8"))
    assert on_file == current and on_file["status"] == "open"
    assert [(p["ticker"], p["weight"]) for p in on_file["positions"]] \
        == [(t, w) for t, w, _ in PICKS]
    assert {p["ticker"]: p["entry_price"] for p in on_file["positions"]} \
        == {"ALL": 253.71, "PSX": 259.47, "HIG": 136.36, "DE": 670.5}
    assert {p["entry_price_source"] for p in on_file["positions"]} == {"open"}
    assert on_file["spy_entry"] == 758.9
    assert on_file["spy_entry_source"] == "open"


def test_the_morning_of_2026_09_14_books_nothing(provider, monkeypatch):
    """Two of the five bars are impossible. Nothing is written, both are
    named, and neither falls back to its Close."""
    table, _ = provider
    that_morning(table)
    asked = no_fallback(monkeypatch)

    with pytest.raises(tk.OpenNotVerified) as exc:
        tk.open_positions("2026-09-14", REPORT)

    assert not tk.CURRENT_PATH.exists()
    assert asked == [], "a refused bar is not a missing one"
    said = str(exc.value)
    assert "nothing booked for week 2026-09-14" in said
    assert "2 entry bar(s)" in said
    assert "  DE 2026-09-14: open 685.92 is above the bar's high 674.99 " \
        "(low 668.26)" in said
    assert "  SPY 2026-09-14: open 764.72 is above the bar's high 759.19 " \
        "(low 758.45)" in said
    assert "Run the same command again later" in said
    for sound in ("ALL", "PSX", "HIG"):
        assert "  " + sound not in said
    said.encode("ascii")


def test_a_refusal_leaves_a_book_already_on_file_as_it_was(
        provider, monkeypatch):
    table, _ = provider
    that_morning(table)
    no_fallback(monkeypatch)
    tk.CURRENT_PATH.write_bytes(b"week: '2026-09-08'\nstatus: open\n")
    with pytest.raises(tk.OpenNotVerified):
        tk.open_positions("2026-09-14", REPORT)
    assert tk.CURRENT_PATH.read_bytes() \
        == b"week: '2026-09-08'\nstatus: open\n"


def test_before_the_open_the_close_based_fallback_is_what_it_was(
        provider, monkeypatch, capsys):
    """Unchanged, and pinned so it stays visible: with no Monday bar the
    tracker books the last close and says "close". That is how the
    pre-market run of 2026-09-14 came to hold Friday's closes."""
    asked = no_fallback(monkeypatch)                    # the provider is empty
    current = tk.open_positions("2026-09-14", REPORT)
    assert asked == ["ALL", "PSX", "HIG", "DE", "SPY"]
    assert {p["ticker"]: (p["entry_price"], p["entry_price_source"])
            for p in current["positions"]} \
        == {t: (FRIDAY_CLOSE[t], "close") for t, _, _ in PICKS}
    assert (current["spy_entry"], current["spy_entry_source"]) \
        == (764.29, "close")
    assert "ALL Monday open unavailable; falling back to close-based entry" \
        in capsys.readouterr().out


def run_tracker(monkeypatch, tmp_path, *argv):
    report = tmp_path / "2026-09-14-report.md"
    report.write_text(REPORT_MD, encoding="utf-8", newline="\n")
    monkeypatch.setattr(sys, "argv", ["tracker.py"] + list(argv)
                        + ["--report", str(report)])
    tk.main()


def test_open_exits_2_and_writes_nothing(
        provider, monkeypatch, tmp_path, capsys):
    table, _ = provider
    that_morning(table)
    no_fallback(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        run_tracker(monkeypatch, tmp_path, "--open", "2026-09-14")
    assert exc.value.code == 2
    assert not tk.CURRENT_PATH.exists()
    said = capsys.readouterr().out
    assert said.startswith("REFUSED: nothing booked for week 2026-09-14")
    assert "DE 2026-09-14" in said and "SPY 2026-09-14" in said
    said.encode("ascii")


def test_open_on_a_sound_morning_exits_clean_with_the_reports_book(
        provider, monkeypatch, tmp_path):
    table, _ = provider
    that_morning(table)
    table["DE"] = {MON: around(670.5)}
    table["SPY"] = {MON: bar(758.9, 759.19, 758.45)}
    no_fallback(monkeypatch)
    run_tracker(monkeypatch, tmp_path, "--open", "2026-09-14")
    on_file = yaml.safe_load(tk.CURRENT_PATH.read_text(encoding="utf-8"))
    assert on_file["week"] == "2026-09-14"
    assert [p["ticker"] for p in on_file["positions"]] \
        == ["ALL", "PSX", "HIG", "DE"]
    assert on_file["vix_at_entry"] == 15.84


def test_full_refuses_the_new_week_after_closing_the_old(
        provider, monkeypatch, tmp_path, capsys):
    """--full closes last week first. That close is not this week's to
    undo: the refusal says it stands, and how to open this week later."""
    table, _ = provider
    that_morning(table)
    no_fallback(monkeypatch)
    closed = []
    monkeypatch.setattr(tk, "close_positions",
                        lambda week: closed.append(week))
    with pytest.raises(SystemExit) as exc:
        run_tracker(monkeypatch, tmp_path, "--full", "2026-09-14")
    assert exc.value.code == 2
    assert closed == ["2026-09-14"]
    assert not tk.CURRENT_PATH.exists()
    said = capsys.readouterr().out
    assert "REFUSED: nothing booked for week 2026-09-14" in said
    assert "Open this one later with --open 2026-09-14" in said
