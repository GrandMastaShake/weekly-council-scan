"""The per-ticker fallback reads a ticker's bars as a chunk does, and a
download that did not answer is not a ticker without bars.

download_equity_history asks for fifty tickers at a time and, when a chunk
has failed CHUNK_RETRIES times, asks for each of its tickers alone. Until
2026-10-11 that second path handed the single-ticker frame straight to
_frame_to_history. Under yfinance 1.6.0 such a frame has MultiIndex columns,
(Price, Ticker), and the row loop read 0 bars out of a frame of 10 rows:
after one bad chunk, up to fifty names with an empty history, listed in
`missing` for every week of the run, exit 0. Found by review on 2026-10-07;
reproduced on 2026-10-11 against the provider (XOM, 2026-09-21..10-02).

Two kinds of test here, and they say different things.

The ones over FakeFrame run everywhere. conftest stubs pandas, so they pin
the routing -- the fallback goes through _subframe, a frame that cannot be
read stops the run -- on a model of the two column layouts, not on pandas.

The ones marked real_pandas build the same two layouts with pandas itself
and are the only tests that run _frame_to_history on a real frame. They
skip where pandas is not installed, which is CI (requirements-dev.txt has
no pandas). The closes and volumes are made up; the layouts are the ones
yfinance 1.6.0 returned.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from datetime import date as D

import pytest

from conftest import ROOT, weekly_doc

import backfill_weekly as bf  # noqa: E402  (conftest stubs the provider)

FRIDAY = D(2026, 10, 2)
DAYS = [D(2026, 9, 30), D(2026, 10, 1), FRIDAY]
FIELDS = ("Close", "High", "Low", "Open", "Volume")


def load_mirror():
    spec = importlib.util.spec_from_file_location(
        "mirror_backfill_fallback",
        ROOT / "scan_pipeline" / "scripts" / "backfill_weekly.py")
    mirror = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mirror)
    return mirror


@pytest.fixture(params=["scripts", "mirror"])
def script(request):
    """Both copies: the fallback is the same lines in each."""
    return bf if request.param == "scripts" else load_mirror()


def values(ticker):
    """{field: [value per day]}, different for every ticker."""
    base = 100.0 + sum(ord(c) for c in ticker)
    return {f: [base + i + n for n in range(len(DAYS))]
            if f != "Volume" else [1000 * (n + 1) + len(ticker)
                                   for n in range(len(DAYS))]
            for i, f in enumerate(FIELDS)}


def expected(ticker):
    v = values(ticker)
    return (list(DAYS), v["Close"], v["Volume"])


# ------------------------------------------------- a model of the two frames

class FakeMultiIndex(list):
    """Column keys that are (level 0, level 1) pairs."""

    def get_level_values(self, level):
        return [key[level] for key in self]


class FakeFrame:
    """As much of a DataFrame as _subframe and _frame_to_history use."""

    def __init__(self, columns, rows):
        self.columns = columns
        self.rows = rows                # [(day, {column key: value})]

    def __len__(self):
        return len(self.rows)

    def iterrows(self):
        return iter(self.rows)

    def _select(self, ticker, level):
        keep = [k for k in self.columns if k[level] == ticker]
        return FakeFrame([k[1 - level] for k in keep],
                         [(day, {k[1 - level]: row[k] for k in keep})
                          for day, row in self.rows])

    def __getitem__(self, ticker):      # level 0, as df[ticker]
        return self._select(ticker, 0)

    def xs(self, ticker, axis, level):
        assert axis == 1 and level == -1
        return self._select(ticker, 1)


def fake_frame(tickers, ticker_first, fields=FIELDS):
    keys = FakeMultiIndex(
        (t, f) if ticker_first else (f, t) for t in tickers for f in fields)
    rows = []
    for n, day in enumerate(DAYS):
        row = {}
        for t in tickers:
            for f in fields:
                row[(t, f) if ticker_first else (f, t)] = values(t)[f][n]
        rows.append((day, row))
    return FakeFrame(keys, rows)


def fake_single(ticker, fields=FIELDS):
    """yf.download("XOM", ...) under 1.6.0: columns (Price, Ticker)."""
    return fake_frame([ticker], ticker_first=False, fields=fields)


def fake_chunk(tickers):
    """yf.download([...], group_by="ticker"): columns (Ticker, Price)."""
    return fake_frame(tickers, ticker_first=True)


EMPTY = FakeFrame(FakeMultiIndex(), [])


@pytest.fixture
def provider(monkeypatch, script):
    """A provider whose chunks all fail, and whose single-ticker answers
    are `answers[ticker]`: a frame, or an exception to raise."""
    answers = {}
    asked = []

    def download(ticker, **kwargs):
        asked.append(ticker)
        answer = answers[ticker]
        if isinstance(answer, BaseException):
            raise answer
        return answer

    monkeypatch.setitem(sys.modules, "pandas",
                        types.SimpleNamespace(MultiIndex=FakeMultiIndex))
    monkeypatch.setitem(sys.modules, "yfinance",
                        types.SimpleNamespace(download=download))
    monkeypatch.setattr(script, "_download_chunk", lambda *a: None)
    monkeypatch.setattr(script.time, "sleep", lambda seconds: None)
    answers["asked"] = asked
    return answers


# ----------------------------------------------------------------- the defect

def test_the_row_loop_alone_reads_no_bar_from_a_single_ticker_frame(script):
    """The defect, kept as a statement of fact about _frame_to_history: it
    reads a frame whose columns are the fields, and nothing else."""
    assert script._frame_to_history(fake_single("XOM")) == ([], [], [])


def test_the_fallback_reads_what_a_chunk_reads(provider, script):
    provider.update({"XOM": fake_single("XOM"), "CVX": fake_single("CVX")})
    history = script.download_equity_history(["XOM", "CVX"], FRIDAY, FRIDAY)
    assert provider["asked"] == ["XOM", "CVX"]
    assert history == {"XOM": expected("XOM"), "CVX": expected("CVX")}

    chunk = fake_chunk(["XOM", "CVX"])
    assert history["XOM"] == script._ticker_history(chunk, "XOM")
    assert history["CVX"] == script._ticker_history(chunk, "CVX")


# ------------------------------------------------------- unknown is not none

def test_a_fallback_frame_with_no_rows_is_a_ticker_without_bars(
        provider, script):
    """The provider's own "nothing" (a symbol it has no bars for in the
    window) is an answer, and the ticker goes to `missing` as before."""
    provider.update({"XOM": fake_single("XOM"), "SPCX": EMPTY})
    history = script.download_equity_history(["XOM", "SPCX"], FRIDAY, FRIDAY)
    assert history["SPCX"] == ([], [], [])
    assert history["XOM"] == expected("XOM")


def test_a_fallback_frame_that_cannot_be_read_stops_the_run(provider, script):
    """Rows, and no Close column for the ticker: a layout this code does
    not know. Before, that was an empty history like any other."""
    provider.update({
        "XOM": fake_single("XOM"),
        "CVX": fake_single("CVX", fields=("High", "Volume")),
        "OXY": fake_single("ZZZ"),
    })
    with pytest.raises(script.HistoryUnknown) as caught:
        script.download_equity_history(["XOM", "CVX", "OXY"], FRIDAY, FRIDAY)
    unknown = caught.value.unknown
    assert sorted(unknown) == ["CVX", "OXY"]
    assert "no Close column for CVX" in unknown["CVX"]
    assert "no columns for OXY" in unknown["OXY"]
    # Every ticker was still asked: the refusal names all of them at once.
    assert provider["asked"] == ["XOM", "CVX", "OXY"]


def test_a_fallback_download_that_raises_stops_the_run(provider, script):
    provider.update({"XOM": fake_single("XOM"),
                     "CVX": OSError("Too Many Requests")})
    with pytest.raises(script.HistoryUnknown) as caught:
        script.download_equity_history(["XOM", "CVX"], FRIDAY, FRIDAY)
    assert list(caught.value.unknown) == ["CVX"]
    assert "OSError: Too Many Requests" in caught.value.unknown["CVX"]


def test_a_chunk_that_lacks_a_ticker_stops_the_run(provider, script,
                                                   monkeypatch):
    """The same rule on the chunk path: a frame with rows and no columns
    for a ticker it was asked for was read as that ticker having no bars."""
    monkeypatch.setattr(script, "_download_chunk",
                        lambda *a: fake_chunk(["XOM"]))
    with pytest.raises(script.HistoryUnknown) as caught:
        script.download_equity_history(["XOM", "CVX"], FRIDAY, FRIDAY)
    assert list(caught.value.unknown) == ["CVX"]
    assert provider["asked"] == []


def test_a_merge_writes_nothing_when_a_history_is_unknown(
        provider, script, monkeypatch, tmp_path, capsys):
    """main(): exit 2, which stops the workflow before its commit step,
    and the week on file is byte for byte what it was. Before, CVX went
    into its `missing` and the run exited 0."""
    if script is not bf:
        pytest.skip("the mirror has no --merge that reads the week first")
    import json
    weekly = tmp_path / "weekly"
    weekly.mkdir()
    path = weekly / "2026-10-02.json"
    path.write_text(json.dumps(weekly_doc("2026-10-02", ["SPY"]), indent=2)
                    + "\n", encoding="utf-8", newline="\n")
    before = path.read_bytes()
    provider.update({"XOM": fake_single("XOM"),
                     "CVX": fake_single("CVX", fields=("Volume",))})
    monkeypatch.setattr(sys, "argv", [
        "backfill_weekly.py", "--out", str(tmp_path), "--start", "2026-10-02",
        "--end", "2026-10-02", "--only", "XOM,CVX", "--merge"])
    assert bf.main() == 2
    out = capsys.readouterr().out
    assert "REFUSED, nothing written" in out
    assert "  CVX: its own frame could not be read" in out
    assert "  XOM:" not in out
    assert path.read_bytes() == before
    assert sorted(p.name for p in weekly.iterdir()) == ["2026-10-02.json"]


# ---------------------------------------------------------------- real pandas

@pytest.fixture
def pd(monkeypatch):
    """pandas itself, for the length of one test. conftest puts an empty
    module under the name; it is put back afterwards."""
    stub = sys.modules.get("pandas")
    if hasattr(stub, "DataFrame"):
        return stub
    monkeypatch.delitem(sys.modules, "pandas", raising=False)
    try:
        import pandas
    except ImportError:
        pytest.skip("pandas is not installed: no real frame to read")
    if not hasattr(pandas, "DataFrame"):
        pytest.skip("pandas is stubbed: no real frame to read")
    monkeypatch.setitem(sys.modules, "pandas", pandas)
    return pandas


def real_frame(pd, tickers, ticker_first):
    index = pd.DatetimeIndex([pd.Timestamp(d) for d in DAYS], name="Date")
    data, keys = {}, []
    for t in tickers:
        for f in FIELDS:
            key = (t, f) if ticker_first else (f, t)
            keys.append(key)
            data[key] = values(t)[f]
    frame = pd.DataFrame(data, index=index)
    frame.columns = pd.MultiIndex.from_tuples(
        keys, names=["Ticker", "Price"] if ticker_first
        else ["Price", "Ticker"])
    return frame


def test_real_pandas_single_ticker_frame_reads_as_the_chunk_does(pd, script):
    single = real_frame(pd, ["XOM"], ticker_first=False)
    chunk = real_frame(pd, ["XOM", "CVX"], ticker_first=True)
    # The defect: every row is there and the row loop reads none of them.
    assert len(single) == len(DAYS)
    assert script._frame_to_history(single) == ([], [], [])
    # The fix: one path for both layouts, and one history.
    assert script._ticker_history(single, "XOM") == expected("XOM")
    assert script._ticker_history(chunk, "XOM") == expected("XOM")
    assert script._ticker_history(chunk, "CVX") == expected("CVX")


def test_real_pandas_plain_columns_still_read(pd, script):
    """What a single-ticker download returned before the MultiIndex, and
    returns with multi_level_index=False."""
    plain = pd.DataFrame(values("XOM"), index=pd.DatetimeIndex(
        [pd.Timestamp(d) for d in DAYS]))
    assert script._ticker_history(plain, "XOM") == expected("XOM")


def test_real_pandas_nan_closes_and_empty_frames_are_no_bars(pd, script):
    chunk = real_frame(pd, ["XOM", "CVX"], ticker_first=True)
    chunk[("CVX", "Close")] = float("nan")
    assert script._ticker_history(chunk, "CVX") == ([], [], [])
    assert script._ticker_history(chunk, "XOM") == expected("XOM")
    empty = real_frame(pd, ["XOM"], ticker_first=False).iloc[0:0]
    assert script._ticker_history(empty, "XOM") == ([], [], [])
    assert script._ticker_history(None, "XOM") == ([], [], [])


def test_real_pandas_frame_without_the_ticker_cannot_be_read(pd, script):
    single = real_frame(pd, ["XOM"], ticker_first=False)
    with pytest.raises(ValueError, match="no columns for CVX"):
        script._ticker_history(single, "CVX")
    no_close = single.drop(columns=[("Close", "XOM")])
    with pytest.raises(ValueError, match="no Close column for XOM"):
        script._ticker_history(no_close, "XOM")
