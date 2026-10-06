"""
snapshot.py -- committed data-feed writer/deriver for weekly-council-scan.

Wave 1 (Job S). Owns the committed data feed:

  * fetch_weekly_bars()     -- the equity set for one weekly file: the bars of
                               the session that answers for the Friday
  * fetch_session_bars()    -- date-pinned yfinance fetch for one session
  * write_weekly()          -- data/weekly/<friday>.json   (DATA_FEED.md sec.1)
  * unwritten_fridays()     -- the weeks the panel still owes a file for
  * derive_market_state()   -- data/market_state.json      (MARKET_GROUNDING sec.1, sec.9)
  * build_universe()        -- data/universe.json + wiki/universe.md mirror (sec.3)
  * rederive_and_compare()  -- purity self-check for the Wave 2 truth gate

A weekly file is one equity session, and SPY is its witness (2026-10-06,
DATA_FEED.md sec.1c). The Friday's own bar is the session. Where SPY has no
bar dated the Friday, an earlier session of the week stands in only once a
later bar proves the Friday was skipped, and the file says which; until
then write_weekly raises NoSessionWitness and writes nothing. Run on a
market holiday before that, the writer used to commit `series: {}`.

A week is written once (2026-10-06). write_weekly raises WeekOnFile for a
Friday that already has its file, where it used to write over it, and the
one caller that may say otherwise is the backfill's declared rewrite.

Spec amendment (owner, supersedes DATA_FEED.md sec.1 "Ticker set"): weekly
files commit the FULL feed -- PRICE_FEED_UNIVERSE + 16 index/sector ETFs, as
equity_universe() returns it -- plus the special-instrument blocks, not just
the charted ~40. Size math adjusts to ~15KB/file.

Special instruments (US10Y, US2Y, US2Y_FUT, VIX, WTI, WTI_NEXT, GOLD, SILVER,
DXY) come from scan_pipeline.snapshot_macro.fetch_special_instruments (Job V,
built concurrently). Contract: returns {"rates": {"US10Y": {...}, "US2Y":
{...}, "US2Y_FUT": {...}}, "vol": {"VIX": {...}}, "commodities": {"WTI": ...,
"WTI_NEXT": ..., "GOLD": ..., "SILVER": ...}, "fx": {"DXY": {...}},
"missing": [{"ticker", "reason"}]} with values {"close": float, "volume":
float|None}, plus an optional "provenance" {block: {ticker: {"source",
"fetched_at"[, "contract"][, "observed"]}}} naming any instrument that did
not come from PROVIDER, the contract month of each commodity ("contract"),
and any value that is a stand-in from an earlier session of the week
("observed" is that session). A defensive stub fallback covers the module
being absent (empty blocks + a missing entry), so this file never depends on
import success.

US2Y is the one instrument with a second publisher (2026-10-04): the U.S.
Treasury par yield curve, because Yahoo has no cash 2-year series. A weekly
file says so per instrument in provenance.rates.US2Y, and that label is how
the deriver tells a cash 2-year from the 2YY=F futures mark that every file
through 2026-10-02 committed under the same key. See cash_2y_series().

WTI, GOLD and SILVER are named contracts (2026-10-05): the nearest-expiry
month, read under its own symbol, with the contract committed in
provenance.commodities. Every file through 2026-10-02 holds a continuous
symbol's bar instead and names nothing, and twelve of those closes are not
the nearest-expiry contract's settlement. The deriver therefore reads a
commodity only through commodity_series(), which takes a week's own close
where the file names its contract and otherwise asks the committed
settlement file beside the weekly directory (commodity_settlements.json).

NOTE on the block shape: DATA_FEED.md sec.1 sketches rates/vol/commodities as
bare numbers ({"US10Y": 4.66}); the Job V contract supersedes that sketch and
blocks are committed as {"close": float, "volume": float|None} dicts, same
shape as series entries. Readers must use block[ticker]["close"].

Byte-stability contract (Wave 2 backfill + truth gate depend on this):
  * Serialization: json.dumps(obj, sort_keys=True, ensure_ascii=True,
    indent=2) + trailing "\n". Pure ASCII, LF newlines, sorted keys.
  * Floats are rounded BEFORE serialization with Python round()
    (banker's rounding -- deterministic across runs and platforms):
      weekly-file close            -> 4 dp   (FX-grade precision)
      market_state px / lvl        -> 2 dp
      pct deltas (d1w/d4w/d13w/d52w) -> 1 dp
      rate deltas / curve          -> integer bps
      pctile_2y                    -> integer 0-100
      correlations                 -> 3 dp
      adv_usd                      -> integer
  * Weekly closes are split/dividend-ADJUSTED closes (yfinance
    auto_adjust=True), matching the house convention in
    fetch_market_data._parse_daily_bars which prefers adjclose.

Derivation purity: derive_market_state() reads ONLY the weekly files,
facts.json and the two committed history files beside the weekly directory
(us2y_treasury.json, commodity_settlements.json). No network, no clocks;
as_of comes from the newest weekly file. Given identical inputs it is
byte-identical (see rederive_and_compare).
"""

from __future__ import annotations

import glob
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

try:
    from scan_pipeline.config.tickers import (
        STOCK_UNIVERSE, BACKFILL_44_TICKERS, PRICE_FEED_UNIVERSE)
except ImportError:  # same-dir import when repo root is not on sys.path
    from config.tickers import (
        STOCK_UNIVERSE, BACKFILL_44_TICKERS, PRICE_FEED_UNIVERSE)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROVIDER = "yahoo"          # the ONE provider constant; backfill appends
                            # "-backfill" at call time, never here

# The single exception to "one provider": the cash 2-year, which PROVIDER
# does not carry. Never a file-level source -- a weekly file is still a Yahoo
# file. It labels one instrument, in provenance, and the history file below.
TREASURY_SOURCE = "treasury"

# Treasury 2-year for the weeks whose own file cannot supply one: every week
# through 2026-10-02 (those files hold the 2YY=F future under "US2Y" and are
# never edited), and any later week whose Treasury fetch failed. Lives beside
# the weekly directory, so a caller that names weekly_dir has named this too.
US2Y_HISTORY_FILE = "us2y_treasury.json"

# Instrument classification for the committed feed and market_state.
INDEX_TICKERS = ["SPY", "QQQ", "DIA", "IWM"]
SECTOR_TICKERS = ["SMH", "XLE", "XLF", "XLK", "XLV", "XLP",
                  "XLY", "XLI", "XLB", "XLRE", "XLU", "XLC"]
RATE_TICKERS = ["US10Y", "US2Y"]        # market_state "rates" entries
CASH_2Y = "US2Y"                        # read through cash_2y_series(), never
                                        # straight from the weekly files
VOL_TICKERS = ["VIX"]                   # weekly-file "vol" block
COMMODITY_TICKERS = ["WTI", "GOLD", "SILVER"]   # market_state "commodities"
                                        # entries; read through
                                        # commodity_series(), never straight
                                        # from the weekly files
FX_TICKERS = ["DXY"]                    # "fx" block
SPECIAL_BLOCKS = ("rates", "vol", "commodities", "fx")

# The session witness. A weekly file is the equity session of one day, and
# SPY says which day: no SPY bar that can answer for the Friday, no file.
# scripts/daily_observe.py gates on the same name for the same reason, and
# it is the benchmark every relative figure downstream divides by, so a file
# without it would be useless even if it were complete.
WITNESS = "SPY"

# How a file names a session that is not its Friday. The five holiday weeks
# the backfill wrote carry exactly this, and scripts/audit_series.py reads
# the date back out of it, so it is the record and not a comment.
SESSION_NOTE = "Friday holiday; bars from %s"

# Settlements of the nearest-expiry contract for the weeks whose own file
# does not name its contract: every week through 2026-10-02 (those files
# hold a continuous symbol's bar and are never edited), and any later week
# whose commodity fetch failed. Beside the weekly directory, like the
# Treasury 2-year history.
COMMODITY_HISTORY_FILE = "commodity_settlements.json"

# market_state measures these instruments' one-week change on ONE contract.
# The value is the block entry that carries the following contract's
# settlement for the same session: in the week the front month changes, last
# week's WTI_NEXT is this week's WTI contract a week ago. Gold and silver
# need none: their nearest contract is the spot month, and the step from one
# spot month to the next is a few days of carry.
NEXT_CONTRACT = {"WTI": "WTI_NEXT"}

MAX_WORKERS = 10
PCTILE_WINDOW = 104                     # trailing weeks for pctile_2y
CORR_WEEKS = 4                          # trailing weekly returns for corr_spy_4w

# Cap tiers (market cap, USD)
CAP_MEGA = 200e9
CAP_LARGE = 10e9
CAP_MID = 2e9

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# A futures contract as the exchange names it: product, month letter, year.
_CONTRACT_RE = re.compile(r"^[A-Z]{2}[FGHJKMNQUVXZ]\d{2}$")


# ---------------------------------------------------------------------------
# Canonical serialization (byte-stability contract -- see module docstring)
# ---------------------------------------------------------------------------
def canonical_json(obj) -> str:
    """Byte-stable serialization: sorted keys, ASCII, 2-space indent, LF,
    trailing newline. Wave 2 diffs committed files byte-for-byte."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, indent=2) + "\n"


def _write_json(path: str, obj, whole: bool = False) -> str:
    """whole: write beside the path and move the file into place, so that
    the path holds the whole file or nothing. A weekly file is written this
    way: a write that died part-way used to leave its first bytes under the
    week's name, where the writer now refuses to write again."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    target = path + ".part" if whole else path
    with open(target, "w", encoding="utf-8", newline="") as f:
        f.write(canonical_json(obj))
    if whole:
        os.replace(target, path)
    return path


def _r4(x) -> float:
    return round(float(x), 4)


def _r2(x) -> float:
    return round(float(x), 2)


def _r1(x) -> float:
    return round(float(x), 1)


def _r3(x) -> float:
    return round(float(x), 3)


def _vol_int(v) -> Optional[int]:
    """Volume as int; None stays None (instruments that don't trade shares)."""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Equity set
# ---------------------------------------------------------------------------
def equity_universe() -> List[str]:
    """Full committed equity set: PRICE_FEED_UNIVERSE + index/sector ETFs,
    deduped.

    Per the owner amendment, weekly files commit this entire set, and
    scripts/daily_observe.py fetches the same one for a daily file.

    Read from the feed constant, never listed again here. This used to
    repeat the union (STOCK_UNIVERSE | BACKFILL_44_TICKERS), so when the
    Council watchlist joined PRICE_FEED_UNIVERSE on 2026-09-21 the weekly
    writer went on fetching the old set: BTC and GLD reached the daily files
    and no weekly file, in `series` or in `missing`, until 2026-10-06. A
    name the feed lists and this leaves out is silently absent from every
    week written, and a full-file rewrite deletes it from a week that had it
    (the 8/26 incident through the front door)."""
    return sorted(set(PRICE_FEED_UNIVERSE)
                  | set(INDEX_TICKERS) | set(SECTOR_TICKERS))


# ---------------------------------------------------------------------------
# Special-instrument bridge (Job V contract, defensive stub fallback)
# ---------------------------------------------------------------------------
def get_special_instruments(friday_date: str) -> dict:
    """Fetch special instruments via snapshot_macro (Job V). On ANY failure
    returns empty blocks plus a missing entry -- never raises, never
    fabricates a level."""
    empty = {"rates": {}, "vol": {}, "commodities": {}, "fx": {}}
    try:
        from scan_pipeline.snapshot_macro import fetch_special_instruments
    except ImportError:
        try:
            from snapshot_macro import fetch_special_instruments  # type: ignore
        except ImportError:
            return dict(empty, missing=[{
                "ticker": "*",
                "reason": "snapshot_macro module absent; special-instrument blocks empty",
            }])
    try:
        result = fetch_special_instruments(friday_date)
    except Exception as exc:
        return dict(empty, missing=[{
            "ticker": "*",
            "reason": "fetch_special_instruments raised: %s" % exc,
        }])
    if not isinstance(result, dict):
        return dict(empty, missing=[{
            "ticker": "*",
            "reason": "fetch_special_instruments returned non-dict",
        }])
    for block in SPECIAL_BLOCKS:
        result.setdefault(block, {})
    result.setdefault("missing", [])
    return result


# ---------------------------------------------------------------------------
# 1. Date-pinned yfinance fetch
# ---------------------------------------------------------------------------
def _extract_bar(df, ticker: str, session_date: str) -> Optional[dict]:
    """Select the bar for exactly session_date from a yf.download frame.

    Date-pinned: we pick the row dated session_date, never 'the last row'.
    Returns {"close": float(4dp), "volume": int|None} or None."""
    if df is None or len(df) == 0:
        return None
    try:
        import pandas as pd  # noqa: F401  (yfinance hard-depends on pandas)
        if isinstance(df.columns, pd.MultiIndex):
            if ticker in df.columns.get_level_values(0):
                sub = df[ticker]
            elif ticker in df.columns.get_level_values(-1):
                sub = df.xs(ticker, axis=1, level=-1)
            else:
                return None
        else:
            sub = df  # single-ticker download: plain columns
    except Exception:
        return None
    # locate the row whose date is exactly session_date
    try:
        dates = sub.index.strftime("%Y-%m-%d")
    except Exception:
        return None
    matches = [i for i, d in enumerate(dates) if d == session_date]
    if not matches:
        return None
    row = sub.iloc[matches[0]]
    try:
        close = row["Close"]
    except Exception:
        return None
    try:
        if close != close:  # NaN check without importing math
            return None
        close = float(close)
    except (TypeError, ValueError):
        return None
    volume = None
    try:
        v = row["Volume"]
        if v == v:
            volume = int(v)
    except Exception:
        volume = None
    return {"close": _r4(close), "volume": volume}


def fetch_session_bars(tickers: List[str], session_date: str) -> dict:
    """Date-pinned fetch of one session's bar per ticker.

    Window: [session - 10d, session + 1d); the bar dated exactly
    session_date is selected, and a ticker without one is in missing. Nothing
    here stands in for anything: scripts/daily_observe.py calls this for the
    session it is observing, and fetch_weekly_bars for the session it has
    already decided the week is. period='1d'-style blind fetches are banned
    in this project. Batch via yf.download first; tickers that come back
    without a usable bar get one per-ticker retry; remaining failures land
    in missing with the exception text as the reason.

    Returns {"bars": {ticker: {"close": float, "volume": int|None}},
             "missing": [{"ticker": str, "reason": str}]}.
    """
    tickers = sorted(set(tickers))
    day = datetime.strptime(session_date, "%Y-%m-%d").date()
    start = (day - timedelta(days=10)).isoformat()
    end = (day + timedelta(days=1)).isoformat()

    try:
        import yfinance as yf
    except ImportError as exc:
        return {"bars": {}, "missing": [
            {"ticker": t, "reason": "yfinance import failed: %s" % exc}
            for t in tickers]}

    bars: Dict[str, dict] = {}
    retry: List[Tuple[str, str]] = []

    # -- batch pass -----------------------------------------------------------
    try:
        df = yf.download(tickers, start=start, end=end, interval="1d",
                         group_by="ticker", auto_adjust=True,
                         progress=False, threads=True)
        for t in tickers:
            try:
                bar = _extract_bar(df, t, session_date)
            except Exception as exc:
                bar = None
                retry.append((t, "batch parse error: %s" % exc))
                continue
            if bar is None:
                retry.append((t, "no bar dated %s in window %s..%s"
                                 % (session_date, start, end)))
            else:
                bars[t] = bar
    except Exception as exc:
        retry = [(t, "batch download failed: %s" % exc) for t in tickers]

    # -- per-ticker fallback ---------------------------------------------------
    missing: List[dict] = []
    for t, reason in retry:
        try:
            df1 = yf.download(t, start=start, end=end, interval="1d",
                              auto_adjust=True, progress=False, threads=False)
            bar = _extract_bar(df1, t, session_date)
        except Exception as exc:
            bar = None
            reason = "%s; per-ticker retry raised: %s" % (reason, exc)
        if bar is None:
            missing.append({"ticker": t, "reason": reason})
        else:
            bars[t] = bar

    return {"bars": bars, "missing": missing}


# ---------------------------------------------------------------------------
# 1b. Which session a weekly file is (DATA_FEED.md sec.1c)
# ---------------------------------------------------------------------------
# A weekly file is named for a Friday, and on a market holiday that Friday
# has no bars. The writer above answers "no bar dated the Friday" for every
# ticker, and until 2026-10-06 that went straight into a file: run for
# 2026-07-03 it committed `series: {}`, every name in `missing`, nothing to
# say why, and `truth_check --feed` passed it. The five holiday weeks already
# in the panel never met this path. The backfill wrote them, by its own rule
# (the last bar of the week, noted file-level), and the live job, which
# started on 2026-08-14, has not yet run on a holiday.
#
# The repo has already said twice what a writer does when the bar it wants
# is not there: the Treasury path, and snapshot_macro.select_bar for every
# Yahoo instrument. The equity panel follows the same three lines, with SPY
# as the witness for all of it:
#
#  * SPY's bar dated the Friday is the session, and a missing bar is NOT
#    evidence of a holiday. On Saturday 2026-08-29 the provider's daily
#    closes for the Friday before were all null, on an ordinary week, and a
#    one-off script on the runner built 2026-08-28.json from `1wk` bars
#    instead (macro/series_audit.json; the file is stamped 14:10 UTC). No
#    bar dated the Friday and none after it: no file. Not an empty one, and
#    not Thursday's.
#  * A stand-in needs proof, and is written down. A SPY bar dated AFTER the
#    Friday shows the Friday was skipped, and the last session of the same
#    Mon..Fri week stands in, never one from an earlier week. Every ticker's
#    bar is then the one dated that session, and the file says so in
#    `session_note`.
#  * The proof is checked against the provider's own listing. A later bar
#    proves a holiday only if the Friday really has no row, and the bars
#    read above cannot say: a session whose close has not been posted has
#    a row with a null close, and a row with no close is no bar to any
#    reader here, exactly like a day that never traded. So before an
#    earlier session stands in, the raw chart is asked, as the daily feed
#    asks it (scripts/daily_observe.py, witness_rows). A holiday is not
#    listed there. A session with a null close is -- seen at 00:07 UTC on
#    2026-10-06, the row for the 5th with its volume and no close -- and
#    that Friday is refused however many bars follow it.
#  * On the night itself the proof does not exist. The job runs on the
#    Saturday and the next bar is Monday's, so a holiday week is never
#    written by the run that first meets it. It is written by the first run
#    after a later session, whole: the instruments stand in under the same
#    proof (snapshot_macro), which is why this refuses rather than writing
#    the equities now and losing the other blocks for good.
#
# A refusal is a correct outcome, so it cannot be the alarm. The alarm is in
# truth_check --feed: a week missing between two files fails it.

_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"
_CHART_UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# Pauses between attempts at the two witness questions. A refusal costs the
# week until the next weekly run, so a provider that hiccups once is asked
# again before it is believed.
_WITNESS_PAUSES_S = (2, 4)


class NoSessionWitness(RuntimeError):
    """No weekly file may be written: SPY has no bar that can answer for the
    Friday. Either the date was not a session and nothing proves it yet, or
    the provider has not posted."""


def week_session(days: Set[date],
                 friday: date) -> Tuple[Optional[date], Optional[str]]:
    """Which session a weekly file is. Pure: no network, no clock.

    days is the set of dates the witness has a bar for; friday is the date
    the file is named for. Returns (session, None) or (None, reason), under
    the rules above. It is snapshot_macro.select_bar without the settlement
    hour, and tests/test_weekly_session.py holds the two to one answer.

    A session other than the Friday is a candidate, not yet an answer: the
    caller confirms it with confirm_stand_in before any bar is taken."""
    if friday in days:
        return friday, None
    if not any(d > friday for d in days):
        return None, (
            "no %s bar dated %s, and none after it yet; a holiday cannot be "
            "told from a late post, so no earlier session is substituted"
            % (WITNESS, friday.isoformat()))
    monday = friday - timedelta(days=friday.weekday())
    earlier = [d for d in days if monday <= d < friday]
    if not earlier:
        return None, ("%s printed nothing on %s and its week has no earlier "
                      "session to stand in" % (WITNESS, friday.isoformat()))
    return max(earlier), None


def _witness_days(friday: date) -> Tuple[Optional[Set[date]], Optional[str]]:
    """The dates the witness has a bar for around one Friday: (days, None),
    or (None, problem) when the provider could not be asked. "Unknown" must
    never read as "no session".

    The window is snapshot_macro._fetch_one's. It opens on the week's Monday
    because nothing earlier can be used, and its end, which is exclusive, is
    eight days past the Friday, so that a later bar, where one exists, is in
    it. A row with no close is not a bar: the provider serves a just-closed
    session that way for an hour or more each evening (DATA_FEED.md sec.4),
    and such a row neither answers for the Friday nor proves anything about
    it."""
    monday = friday - timedelta(days=friday.weekday())
    start = monday.isoformat()
    end = (friday + timedelta(days=8)).isoformat()
    try:
        import yfinance as yf
    except ImportError as exc:
        return None, "yfinance import failed: %s" % exc
    problem = None
    for pause in _WITNESS_PAUSES_S + (0,):
        try:
            hist = yf.Ticker(WITNESS).history(start=start, end=end)
        except Exception as exc:
            problem = "%s: %s" % (type(exc).__name__, str(exc)[:160])
            time.sleep(pause)
            continue
        days: Set[date] = set()
        if hist is not None and not hist.empty:
            for idx, row in hist.iterrows():
                close = row["Close"]
                if close is None or close != close:     # a NaN bar is not a bar
                    continue
                days.add(idx.date())
        if days:
            return days, None
        # Not one bar in twelve days is a provider that did not answer, not
        # a fortnight without a session.
        problem = "no %s bars at all returned for %s..%s" % (
            WITNESS, start, end)
        time.sleep(pause)
    return None, problem


def _fetch_chart(symbol: str, start: date, end: date):
    """The provider's raw daily rows for [start, end], or None. Stdlib only,
    and the same request scripts/daily_observe.py makes: two days of slack
    past `end`, because the bounds are UTC and the rows are stamped in
    exchange time."""
    import urllib.request

    def epoch(d: date) -> int:
        return int(datetime(d.year, d.month, d.day,
                            tzinfo=timezone.utc).timestamp())

    url = (_CHART + symbol + "?period1=" + str(epoch(start)) + "&period2="
           + str(epoch(end + timedelta(days=2)))
           + "&interval=1d&includePrePost=false")
    for pause in _WITNESS_PAUSES_S + (0,):
        try:
            req = urllib.request.Request(url, headers=_CHART_UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception:
            time.sleep(pause)
    return None


def parse_listing(payload) -> Optional[Dict[date, Optional[float]]]:
    """{session date: close, or None where the close is null} from a raw
    chart payload. Pure. None when the payload cannot be read: "unknown"
    must never read as "not listed".

    The distinction this draws is the one a download erases. A session that
    ended and has not settled is a row with a null close; a day that was not
    a session is no row at all. scripts/daily_observe.py reads the same
    payload the same way, and a test holds the two to one answer."""
    rows: Dict[date, Optional[float]] = {}
    try:
        result = payload["chart"]["result"][0]
        offset = (result.get("meta") or {}).get("gmtoffset")
        if isinstance(offset, bool) or not isinstance(offset, (int, float)):
            offset = -5 * 3600      # US/Eastern, standard: right to the day
        stamps = result.get("timestamp") or []
        closes = result["indicators"]["quote"][0].get("close") or []
        for stamp, close in zip(stamps, closes):
            day = datetime.fromtimestamp(stamp + offset, timezone.utc).date()
            if close is None or close != close:      # null, or NaN
                # Never overwrite a price: while a session is live its own
                # row is null and the close rides on a second row, same date.
                rows.setdefault(day, None)
            else:
                rows[day] = float(close)
    except (KeyError, IndexError, TypeError, AttributeError, ValueError,
            OverflowError, OSError):
        return None
    return rows


def witness_listing(friday: date) -> Optional[Dict[date, Optional[float]]]:
    """What the provider itself lists for the witness, from the week's
    Monday through the seven days after the Friday. None when it could not
    be asked."""
    monday = friday - timedelta(days=friday.weekday())
    last = friday + timedelta(days=7)
    rows = parse_listing(_fetch_chart(WITNESS, monday, last))
    if rows is None:
        return None
    return {d: c for d, c in rows.items() if monday <= d <= last}


def stand_in_refusal(listing: Optional[Dict[date, Optional[float]]],
                     friday: date) -> Optional[str]:
    """Why an earlier session may NOT stand in for friday, or None when the
    provider's own listing shows the Friday was skipped. Pure.

    listing is witness_listing's answer. The Friday has to be absent from
    it, and a later day present in it."""
    day = friday.isoformat()
    if listing is None:
        return ("a later %s bar says %s was skipped, but the provider could "
                "not be asked what it lists for that day; a close that has "
                "not been posted reads as a missing bar, so no earlier "
                "session stands in until it can be asked" % (WITNESS, day))
    if friday in listing:
        if listing[friday] is None:
            return ("the provider lists %s as a session whose %s close is "
                    "null: it traded and has not settled, so no earlier "
                    "session stands in for it" % (day, WITNESS))
        return ("the provider lists a settled %s close for %s that the "
                "download did not return: a transient provider failure"
                % (WITNESS, day))
    if not any(d > friday for d in listing):
        return ("the provider's own listing shows no %s session after %s "
                "yet, so nothing proves it was skipped" % (WITNESS, day))
    return None


def confirm_stand_in(friday: date) -> Optional[str]:
    """Ask the provider directly before an earlier session stands in for
    friday. None when it may; otherwise the reason it may not."""
    return stand_in_refusal(witness_listing(friday), friday)


def _refused(tickers: List[str], why: str) -> dict:
    """What fetch_weekly_bars returns when no session answers. Every ticker
    is in missing with the reason, so even the refusal is never
    empty-by-omission; write_weekly raises on "refused"."""
    return {"bars": {}, "session": None, "refused": why,
            "missing": [{"ticker": t, "reason": why} for t in tickers]}


def fetch_weekly_bars(tickers: List[str], friday_date: str) -> dict:
    """The equity panel for one weekly file: each ticker's bar for the
    session that answers for friday_date.

    The witness decides the session first (week_session, and confirm_stand_in
    for a session that is not the Friday), and every ticker's bar is then the
    one dated exactly that session (fetch_session_bars). A ticker without one
    is in missing; no ticker gets a day of its own.

    Returns {"bars": {ticker: {"close", "volume"}},
             "missing": [{"ticker", "reason"}],
             "session": the date the bars are dated -- friday_date, or the
                        last session of its week where the Friday is proven
                        to have been skipped. write_weekly records that.}
    When no session answers, bars is empty, session is None, and "refused"
    carries the reason. write_weekly raises NoSessionWitness on it and
    writes nothing; it never raises here, so a caller can report first.
    """
    tickers = sorted(set(tickers))
    friday = datetime.strptime(friday_date, "%Y-%m-%d").date()

    days, problem = _witness_days(friday)
    if days is None:
        # The quick question went unanswered. The batch can still settle the
        # one case that needs no proof: a SPY bar dated the Friday IS the
        # session, so an ordinary week is not lost to one failed request.
        got = (fetch_session_bars(tickers, friday_date)
               if WITNESS in tickers else {})
        if WITNESS in (got.get("bars") or {}):
            got["session"] = friday_date
            return got
        return _refused(tickers, (
            "could not ask the provider which sessions %s has around %s "
            "(%s), and the batch download holds no %s bar dated %s, so the "
            "session is unknown" % (WITNESS, friday_date, problem, WITNESS,
                                    friday_date)))
    session, why = week_session(days, friday)
    if session is None:
        return _refused(tickers, why)
    if session != friday:
        why = confirm_stand_in(friday)
        if why is not None:
            return _refused(tickers, why)

    got = fetch_session_bars(tickers, session.isoformat())
    if WITNESS in tickers and WITNESS not in (got.get("bars") or {}):
        return _refused(tickers, (
            "the provider lists a %s bar dated %s and the batch download "
            "came back without it: a transient provider failure"
            % (WITNESS, session.isoformat())))
    got["session"] = session.isoformat()
    return got


def session_note(friday_date: str, session: Optional[str]) -> Optional[str]:
    """The file-level note for a week whose bars are not the Friday's, or
    None when they are.

    Raises ValueError for a session that cannot stand in: a stand-in is an
    earlier day of the same Mon..Fri week, or it is nothing."""
    if session is None or str(session) == friday_date:
        return None
    session = str(session)          # a date object says the same thing
    if not _DATE_RE.match(session):
        raise ValueError("session must be YYYY-MM-DD, got %r" % (session,))
    friday = datetime.strptime(friday_date, "%Y-%m-%d").date()
    day = datetime.strptime(session, "%Y-%m-%d").date()
    monday = friday - timedelta(days=friday.weekday())
    if not monday <= day < friday:
        raise ValueError(
            "session %s is not an earlier day in the week of %s; a stand-in "
            "comes from the same week or not at all" % (session, friday_date))
    return SESSION_NOTE % session


def unwritten_fridays(weekly_dir: str,
                      today: Optional[date] = None) -> List[str]:
    """The Fridays the panel owes a file for, oldest first: every Friday
    from the first weekly file through the last one before `today` (UTC)
    that has none.

    The weekly job writes these in this order and stops at the first one
    the writer refuses. So a week that could not be written on the night is
    written by the next run that can, and is never stepped over: a reader
    that counts weeks by position (sector-regime-heatmap) reads a hole as a
    window one week longer than it says. An empty directory owes nothing;
    the backfill starts a panel, not this. A correction is not a week's
    file."""
    today = today or datetime.now(timezone.utc).date()
    have = set()
    for path in glob.glob(os.path.join(weekly_dir, "*.json")):
        stem = os.path.basename(path)[: -len(".json")]
        if _DATE_RE.match(stem):
            have.add(stem)
    if not have:
        return []
    owed: List[str] = []
    day = datetime.strptime(min(have), "%Y-%m-%d").date()
    day += timedelta(days=(4 - day.weekday()) % 7)      # the first Friday
    while day < today:
        if day.isoformat() not in have:
            owed.append(day.isoformat())
        day += timedelta(days=7)
    return owed


# ---------------------------------------------------------------------------
# 2. Weekly file writer (DATA_FEED.md sec.1)
# ---------------------------------------------------------------------------
def _normalize_block(block) -> Dict[str, dict]:
    """Normalize a special-instrument block to {ticker: {"close","volume"}}.

    Accepts the Job V contract dicts; tolerates bare numbers (older sketch
    shape) by lifting them to {"close": n, "volume": None}."""
    out: Dict[str, dict] = {}
    if not isinstance(block, dict):
        return out
    for t, rec in block.items():
        if isinstance(rec, dict):
            close = rec.get("close")
            vol = rec.get("volume")
        elif isinstance(rec, (int, float)):
            close, vol = rec, None
        else:
            continue
        if close is None:
            continue
        try:
            out[str(t)] = {"close": _r4(close), "volume": _vol_int(vol)}
        except (TypeError, ValueError):
            continue
    return out


def special_provenance(special, doc: dict) -> Dict[str, dict]:
    """Per-instrument source labels for the special blocks of one document.

    The file-level `source` says who supplied the file, and for everything
    but the cash 2-year that is PROVIDER. An instrument from another
    publisher is named here instead of being relabelled by omission:
    {block: {ticker: {"source", "fetched_at"[, "contract"][, "observed"]}}}.
    `observed` is the session the value was published for, present only when
    that is not the file's as_of: the publisher skipped as_of and a later
    row or bar proved it (snapshot_macro.select_treasury_row, select_bar).
    `contract` is the contract month a commodity's close belongs to. A
    PROVIDER instrument is named only for one of those two reasons -- any
    other, read for the date asked, has no entry, so a label here always
    means something.

    Only instruments that made it into `doc` are kept -- a label for an
    entry that is not there describes nothing, and the feed gate refuses it.
    Shared by write_weekly and scripts/daily_observe.py so the two files
    carry the label identically."""
    out: Dict[str, dict] = {}
    raw = special.get("provenance") if isinstance(special, dict) else None
    if not isinstance(raw, dict):
        return out
    for block in SPECIAL_BLOCKS:
        entries = raw.get(block)
        committed = doc.get(block)
        if not isinstance(entries, dict) or not isinstance(committed, dict):
            continue
        for ticker, rec in entries.items():
            if str(ticker) not in committed or not isinstance(rec, dict):
                continue
            src, got = rec.get("source"), rec.get("fetched_at")
            if not (isinstance(src, str) and src
                    and isinstance(got, str) and got):
                continue
            clean = {"source": src, "fetched_at": got}
            observed = rec.get("observed")
            if isinstance(observed, str) and _DATE_RE.match(observed):
                clean["observed"] = observed
            contract = rec.get("contract")
            if isinstance(contract, str) and _CONTRACT_RE.match(contract):
                clean["contract"] = contract
            out.setdefault(block, {})[str(ticker)] = clean
    return out


# A week that is on file is not written again. Until 2026-10-06 write_weekly
# wrote over it without a word: called a second time for the same Friday it
# replaced every bar with another fetch's, closes adjusted to a later date,
# restamped fetched_at, and dropped any name the second fetch did not have.
# The count of series need not move, and the count was all the gates
# compared. Nothing in the code stood in the way. The weekly job's prompt
# says not to, and that was the whole of it.
class WeekOnFile(RuntimeError):
    """No weekly file may be written: the week already has one, and a weekly
    file is an observation, written once (DATA_FEED.md sec.1)."""


ON_FILE = (
    "REFUSED, nothing written: %s is already on file, and a weekly file is "
    "written once (DATA_FEED.md sec.1). Written again it would put another "
    "fetch's closes, adjusted to a later date, over every bar the file "
    "holds, and lose any name this fetch does not have. Leave the file as "
    "it is. If it has not reached the repository yet, push it as it stands. "
    "Names it lacks are added afterwards by a merge, from the repository "
    "(the \"Backfill weekly panel\" workflow with those tickers), never by "
    "writing the week again. A close the provider has restated goes in "
    "%s.corrected.json, with the owner's sign-off. A week that has to be "
    "written again whole is a declared rewrite, which is the backfill's to "
    "do (scripts/backfill_weekly.py --force), not this call's.")

# What is at the week's path is not always the week. The refusal above told
# a run to push whatever it found: the first bytes of a write that died, a
# zero-byte file, a directory. Such a thing holds no observation, the feed
# gate fails on it, and nothing else would ever write the week: the file is
# there, so unwritten_fridays does not owe it. It is refused all the same,
# because nothing here writes over a file, and says what it is.
NOT_A_WEEK = (
    "REFUSED, nothing written: %s is there and is not the weekly file for "
    "%s (%s). It holds no observation to keep. Do not push it. Nothing here "
    "writes over a file, so remove that one file and run the same calls "
    "again; the week is then written whole.")


def _not_the_week(path: str, friday_date: str) -> Optional[str]:
    """Why what is at `path` is not friday_date's weekly file, or None when
    it is."""
    if not os.path.isfile(path):
        return "not a file"
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as exc:        # ValueError: UTF-8 or JSON
        return "it does not read as JSON: %s" % exc
    if not isinstance(doc, dict) or not isinstance(doc.get("series"), dict):
        return "it has no `series` object"
    if doc.get("as_of") != friday_date:
        return "its as_of is %r" % (doc.get("as_of"),)
    return None


def refuse_week_on_file(friday_date: str, out_dir: str = "data") -> str:
    """The path of the week's file, once it is known that nothing is there.
    Raises WeekOnFile when something is, and says whether it is the week.
    write_weekly asks this first; a caller that fetches before it writes
    can ask it before it fetches."""
    path = os.path.join(out_dir, "weekly", friday_date + ".json")
    if not os.path.lexists(path):       # a link to nowhere is something too
        return path
    why = _not_the_week(path, friday_date)
    if why is None:
        raise WeekOnFile(ON_FILE % (path, friday_date))
    raise WeekOnFile(NOT_A_WEEK % (path, friday_date, why))


def write_weekly(friday_date: str, series_bars: dict, special: Optional[dict] = None,
                 out_dir: str = "data", *, overwrite: bool = False) -> str:
    """Write data/weekly/<friday_date>.json under out_dir.

    series_bars: either a plain {ticker: {"close","volume"}} mapping (missing
        defaults to []) or the full fetch_weekly_bars() result
        {"bars": ..., "missing": ..., "session": ...}. A "session" earlier
        than friday_date is the proven stand-in for a Friday that was not a
        session, and is committed as the file-level `session_note`.
    special: the snapshot_macro contract dict, or None to call
        get_special_instruments(friday_date) (stub fallback if Job V's module
        is absent). Its "provenance" block, when present, is committed for
        the instruments it names (see special_provenance); the file-level
        source stays PROVIDER.
    out_dir: the data root; the file lands at <out_dir>/weekly/<date>.json.
    overwrite: keyword only, and False for every caller but one. The
        backfill's declared rewrite (scripts/backfill_weekly.py --force)
        writes a week again whole and says so here. Only True is yes.

    Raises WeekOnFile, and writes nothing, when something is already at the
    week's path and overwrite is not set. That is asked first, before the
    witness and before any instrument is fetched, and once more just before
    the write, because fetching the instruments takes long enough for a
    file to land. The message says which it found: the week, which is left
    as it is, or a thing that is not a weekly file, which is removed by
    hand. A correction is not the week's file, and is not looked at.

    The file is written beside its path and moved into place, so the path
    holds a whole week or nothing.

    Raises NoSessionWitness, and writes nothing, when the series carry no
    SPY bar: a fetch that was refused, or a panel that simply lacks it. A
    weekly file is one session and SPY is its witness (section 1b above).
    Everything that starts a weekly file comes through here, the backfill
    included, so this is the one place the rule cannot be walked around.

    'missing' is REQUIRED and never empty-by-omission: it is the union of
    series fetch failures and special-instrument failures, sorted and deduped.
    fetched_at is the real UTC now -- it is how stale-cache scans are caught.
    """
    if not _DATE_RE.match(friday_date):
        raise ValueError("friday_date must be YYYY-MM-DD, got %r" % friday_date)

    path = os.path.join(out_dir, "weekly", friday_date + ".json")
    if overwrite is not True:
        refuse_week_on_file(friday_date, out_dir)

    session = refused = None
    if isinstance(series_bars, dict) and ("bars" in series_bars or "missing" in series_bars):
        bars = series_bars.get("bars") or {}
        missing = list(series_bars.get("missing") or [])
        session = series_bars.get("session")
        refused = series_bars.get("refused")
    else:
        bars = series_bars
        missing = []

    series = _normalize_block(bars)
    if refused or WITNESS not in series:
        why = refused or ("the series handed to the writer hold no %s bar"
                          % WITNESS)
        raise NoSessionWitness(
            "REFUSED, nothing written: %s needs a session witness and has "
            "none -- %s. A weekly file is one equity session and %s says "
            "which (DATA_FEED.md sec.1c). No file is the correct outcome of "
            "this run; do not build one another way. Run the same calls for "
            "%s again once the provider shows a later session: the writer "
            "then takes the Friday's bars if they are there, or the last "
            "session of that week, and records which."
            % (path, why, WITNESS, friday_date))
    note = session_note(friday_date, session)

    # After the refusal, not before it: a week that will not be written has
    # no use for eight instrument fetches and Treasury's seventeen seconds.
    if special is None:
        special = get_special_instruments(friday_date)
    missing.extend(special.get("missing") or [])

    # dedupe + sort for deterministic output
    seen = set()
    uniq: List[dict] = []
    for m in missing:
        key = (str(m.get("ticker")), str(m.get("reason")))
        if key not in seen:
            seen.add(key)
            uniq.append({"ticker": key[0], "reason": key[1]})
    uniq.sort(key=lambda m: (m["ticker"], m["reason"]))

    doc = {
        "as_of": friday_date,
        "source": PROVIDER,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": "close",
        "series": series,
        "rates": _normalize_block(special.get("rates")),
        "vol": _normalize_block(special.get("vol")),
        "commodities": _normalize_block(special.get("commodities")),
        "fx": _normalize_block(special.get("fx")),
        "missing": uniq,
    }
    prov = special_provenance(special, doc)
    if prov:
        doc["provenance"] = prov
    if note:
        doc["session_note"] = note
    if overwrite is not True:
        refuse_week_on_file(friday_date, out_dir)
    return _write_json(path, doc, whole=True)


# ---------------------------------------------------------------------------
# 3. market_state derivation (MARKET_GROUNDING sec.1 + sec.9) -- PURE
# ---------------------------------------------------------------------------
def _load_weekly_files(weekly_dir: str) -> List[Tuple[str, dict]]:
    """Load weekly files, oldest first. A <date>.corrected.json supersedes
    its original (DATA_FEED.md sec.1 correction rule)."""
    originals = {}
    corrected = set()
    for path in glob.glob(os.path.join(weekly_dir, "*.json")):
        name = os.path.basename(path)
        if name.endswith(".corrected.json"):
            d = name[: -len(".corrected.json")]
            if _DATE_RE.match(d):
                corrected.add(d)
        elif _DATE_RE.match(name[: -len(".json")]):
            originals[name[: -len(".json")]] = path
    docs: List[Tuple[str, dict]] = []
    for d in sorted(set(originals) | corrected):
        path = (os.path.join(weekly_dir, d + ".corrected.json")
                if d in corrected else originals[d])
        with open(path, "r", encoding="utf-8") as f:
            docs.append((d, json.load(f)))
    return docs


def _close_series(docs: List[Tuple[str, dict]], ticker: str,
                  block: Optional[str]) -> Dict[str, float]:
    """{date: close} for one instrument across weekly files. Gaps are
    skipped, never interpolated (backfill gap rule)."""
    pts: Dict[str, float] = {}
    for d, doc in docs:
        src = doc.get("series") if block is None else doc.get(block)
        if not isinstance(src, dict):
            continue
        rec = src.get(ticker)
        if isinstance(rec, dict):
            c = rec.get("close")
        elif isinstance(rec, (int, float)):
            c = rec
        else:
            c = None
        if c is not None:
            try:
                pts[d] = float(c)
            except (TypeError, ValueError):
                pass
    return pts


# -- the cash 2-year ----------------------------------------------------------
def us2y_history_path(weekly_dir: str) -> str:
    """The Treasury 2-year history file that belongs to a weekly directory."""
    return os.path.join(os.path.dirname(os.path.abspath(weekly_dir)),
                        US2Y_HISTORY_FILE)


def load_us2y_history(path: str) -> Tuple[Dict[str, float], Optional[str]]:
    """({week: close}, problem) from us2y_treasury.json. Pure.

    Never raises. A history that cannot be read degrades the fields that
    need it to null with the reason, the same way an unreadable facts.json
    does; `problem` is None when the file loaded."""
    name = os.path.basename(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        return {}, "%s not found" % name
    except Exception as exc:
        return {}, "%s unreadable (%s)" % (name, type(exc).__name__)
    series = doc.get("series") if isinstance(doc, dict) else None
    if not isinstance(series, dict):
        return {}, "%s has no 'series' object" % name
    pts: Dict[str, float] = {}
    for d, rec in series.items():
        c = rec.get("close") if isinstance(rec, dict) else None
        if (_DATE_RE.match(str(d)) and isinstance(c, (int, float))
                and not isinstance(c, bool)):
            pts[str(d)] = float(c)
    return pts, None


def is_treasury_sourced(doc: dict, block: str, ticker: str) -> bool:
    """True when the document names Treasury as the source of one instrument.

    No label means the file-level source, which is PROVIDER: for US2Y that
    is the 2YY=F future, in every file through 2026-10-02."""
    prov = doc.get("provenance") if isinstance(doc, dict) else None
    entries = prov.get(block) if isinstance(prov, dict) else None
    rec = entries.get(ticker) if isinstance(entries, dict) else None
    src = rec.get("source") if isinstance(rec, dict) else None
    return src == TREASURY_SOURCE


def cash_2y_series(docs: List[Tuple[str, dict]],
                   history: Dict[str, float]) -> Dict[str, float]:
    """{week: Treasury 2-year close} across the panel. The only way to read
    US2Y -- do not take rates.US2Y from the weekly files directly.

    "US2Y" names two instruments in data/weekly. Every file through
    2026-10-02 holds the 2YY=F future there: a contract nobody trades, whose
    mark sat up to 36 bp under the cash yield. Files written since hold the
    Treasury par-curve 2-year and say so in provenance.rates.US2Y. The old
    files are observations and are never edited, so the Treasury value for
    those weeks comes from the history file.

    A week's own Treasury-sourced value wins over a history entry for the
    same week: it is what was observed that night. A value with no Treasury
    label is a futures mark and is NEVER used. A week with neither is a gap,
    and a gap reaches market_state as null with a reason, not as the future.
    """
    weeks = {d for d, _ in docs}
    pts = {d: v for d, v in (history or {}).items() if d in weeks}
    for d, doc in docs:
        if not is_treasury_sourced(doc, "rates", CASH_2Y):
            continue
        own = _close_series([(d, doc)], CASH_2Y, "rates")
        pts.update(own)
    return pts


# -- the commodities ----------------------------------------------------------
def commodity_history_path(weekly_dir: str) -> str:
    """The settlement file that belongs to a weekly directory."""
    return os.path.join(os.path.dirname(os.path.abspath(weekly_dir)),
                        COMMODITY_HISTORY_FILE)


def load_commodity_history(path: str) -> Tuple[Dict[str, dict], Optional[str]]:
    """({instrument: {"audited_through", "series", "unavailable"}}, problem)
    from commodity_settlements.json. Pure.

    "series" is {week: (close, contract or None)}, "unavailable" is
    {week: reason}, and "audited_through" is the last week whose committed
    close may be read without a contract label, or None. Never raises: a
    file that cannot be read degrades the fields that need it to null with
    the reason, as load_us2y_history does; `problem` is None when it loaded.
    """
    name = os.path.basename(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        return {}, "%s not found" % name
    except Exception as exc:
        return {}, "%s unreadable (%s)" % (name, type(exc).__name__)
    instruments = doc.get("instruments") if isinstance(doc, dict) else None
    if not isinstance(instruments, dict):
        return {}, "%s has no 'instruments' object" % name
    out: Dict[str, dict] = {}
    for ticker, rec in instruments.items():
        if not isinstance(rec, dict):
            continue
        series: Dict[str, Tuple[float, Optional[str]]] = {}
        for d, entry in (rec.get("series") or {}).items():
            c = entry.get("close") if isinstance(entry, dict) else None
            if not (_DATE_RE.match(str(d)) and isinstance(c, (int, float))
                    and not isinstance(c, bool)):
                continue
            contract = entry.get("contract")
            if not (isinstance(contract, str)
                    and _CONTRACT_RE.match(contract)):
                contract = None
            series[str(d)] = (float(c), contract)
        unavailable: Dict[str, str] = {}
        for d, entry in (rec.get("unavailable") or {}).items():
            why = entry.get("reason") if isinstance(entry, dict) else entry
            if _DATE_RE.match(str(d)):
                unavailable[str(d)] = str(why or "no reason recorded")
        through = rec.get("audited_through")
        if not (isinstance(through, str) and _DATE_RE.match(through)):
            through = None
        out[str(ticker)] = {"audited_through": through, "series": series,
                            "unavailable": unavailable}
    return out, None


def named_contract(doc: dict, block: str, ticker: str) -> Optional[str]:
    """The contract month a document names for one instrument, or None.

    None is the ordinary answer for every file through 2026-10-02: they
    hold a continuous symbol's bar, and nothing in them says which month."""
    prov = doc.get("provenance") if isinstance(doc, dict) else None
    entries = prov.get(block) if isinstance(prov, dict) else None
    rec = entries.get(ticker) if isinstance(entries, dict) else None
    contract = rec.get("contract") if isinstance(rec, dict) else None
    if isinstance(contract, str) and _CONTRACT_RE.match(contract):
        return contract
    return None


def commodity_series(docs: List[Tuple[str, dict]], history: Dict[str, dict],
                     ticker: str) -> Dict[str, Tuple[float, Optional[str]]]:
    """{week: (settlement, contract or None)} for one commodity, on one
    rule: the nearest-expiry contract. The only way to read WTI, WTI_NEXT,
    GOLD or SILVER -- do not take commodities.* from the weekly files
    directly.

    A commodity key names whatever contract month the provider's continuous
    symbol showed on the day it was read, in every file through 2026-10-02.
    Mostly that is the nearest-expiry contract's settlement; in twelve
    closes it is the active month's, or a last trade read before the
    settlement, up to 4.8 percent away. Nothing in those files says which.
    Files written since name the contract in provenance.commodities. So,
    for a week:

      1. its own close, where the file names the contract;
      2. else the settlement file's entry for that week (history["series"]);
      3. else nothing, where the settlement file says none can be had
         (history["unavailable"]);
      4. else its own unlabelled close, but only through the week the
         settlement file says the panel was audited to ("audited_through").
         That audit is why a close with no label can be read at all;
      5. else nothing. An unlabelled close from after the audit is a
         contract month nobody has checked, and is NEVER used.

    A gap reaches market_state as null with a reason. The contract is None
    for a week read under rule 4, and for an entry the provider could no
    longer confirm by name.
    """
    rec = (history or {}).get(ticker) or {}
    entries = rec.get("series") or {}
    unavailable = rec.get("unavailable") or {}
    through = rec.get("audited_through")
    out: Dict[str, Tuple[float, Optional[str]]] = {}
    for d, doc in docs:
        own = _close_series([(d, doc)], ticker, "commodities").get(d)
        contract = named_contract(doc, "commodities", ticker)
        if own is not None and contract:
            out[d] = (own, contract)
        elif d in entries:
            out[d] = entries[d]
        elif d in unavailable:
            continue
        elif own is not None and through and d <= through:
            out[d] = (own, None)
    return out


def _commodity_gap(docs: List[Tuple[str, dict]], history: Dict[str, dict],
                   problem: Optional[str], ticker: str, week: str) -> str:
    """Why commodity_series() has nothing for one week, in words."""
    doc = dict(docs).get(week)
    if doc is None:
        return "no weekly file dated %s" % week
    rec = (history or {}).get(ticker) or {}
    if week in (rec.get("unavailable") or {}):
        return ("no %s settlement on the nearest-expiry contract for %s: %s"
                % (ticker, week, rec["unavailable"][week]))
    where = problem or "%s has no entry for it" % COMMODITY_HISTORY_FILE
    if _close_series([(week, doc)], ticker, "commodities"):
        return ("the file for %s names no contract for %s, and %s; a close "
                "of an unknown contract month is never used"
                % (week, ticker, where))
    return "the file for %s carries no %s, and %s" % (week, ticker, where)


def _commodity_fields(ticker: str, docs: List[Tuple[str, dict]],
                      history: Dict[str, dict], problem: Optional[str],
                      as_of: str) -> dict:
    """The seven market_state fields of one commodity.

    px, d4w, d13w, d52w and pctile_2y compare the nearest-expiry contract on
    one date with the nearest-expiry contract on another: the level then and
    the level now, as the instrument is defined. `contract` says which month
    px is. d1w is the same for gold and silver; for an instrument in
    NEXT_CONTRACT it is the change in the as_of contract itself, because in
    the week the front month changes the level comparison is mostly the
    spread between two months (WTI 2026-09-25: -7.9 percent front to front,
    -3.8 on the November contract)."""
    series = commodity_series(docs, history, ticker)
    pts = {d: close for d, (close, _) in series.items()}

    def gap(week):
        return _commodity_gap(docs, history, problem, ticker, week)

    def back(weeks):
        return (datetime.strptime(as_of, "%Y-%m-%d").date()
                - timedelta(weeks=weeks)).isoformat()

    def level_change(weeks):
        if as_of not in pts:
            return None, gap(as_of)
        if back(weeks) not in pts:
            return None, gap(back(weeks))
        return _pct_delta(pts, as_of, weeks)

    def one_contract_change():
        """d1w on the contract px belongs to."""
        if as_of not in series:
            return None, gap(as_of)
        now, contract = series[as_of]
        if contract is None:
            return None, ("the contract month of the %s close is not on "
                          "record, so a one-week change cannot be shown to "
                          "be one contract's" % as_of)
        prior = back(1)
        if dict(docs).get(prior) is None:
            return None, gap(prior)
        held = []
        for name in (ticker, NEXT_CONTRACT[ticker]):
            rec = commodity_series(docs, history, name).get(prior)
            if rec is not None and rec[1] == contract:
                if rec[0] == 0:
                    return None, "prior close is 0"
                return _r1(100.0 * (now / rec[0] - 1.0)), None
            held.append("%s is %s" % (
                name, "absent" if rec is None
                else rec[1] or "a contract not on record"))
        return None, ("no %s settlement on file for %s (%s); a change "
                      "across two contract months is not a market move"
                      % (contract, prior, "; ".join(held)))

    if as_of in series:
        contract = (series[as_of][1], None)
        if contract[0] is None:
            contract = (None, "the %s close predates named contracts and "
                              "its month was not confirmed afterwards"
                              % as_of)
        px = _level(pts, as_of)
        pct = _pctile_2y(pts, as_of)
    else:
        px = contract = pct = (None, gap(as_of))
    unnamed = any(named_contract(doc, "commodities", ticker) is None
                  and _close_series([(d, doc)], ticker, "commodities")
                  for d, doc in docs)
    if pct[0] is not None and problem and unnamed:
        # Without the settlement file the window holds only the weeks since
        # contracts were named; a rank among those is not a 2y percentile.
        pct = (None, "%s: the settlements from before contracts were named "
                     "are unavailable" % problem)
    return {
        "px": px,
        "contract": contract,
        "d1w": (one_contract_change() if ticker in NEXT_CONTRACT
                else level_change(1)),
        "d4w": level_change(4),
        "d13w": level_change(13),
        "d52w": level_change(52),
        "pctile_2y": pct,
    }


def _pct_delta(pts: Dict[str, float], as_of: str, weeks: int) -> Tuple[Optional[float], Optional[str]]:
    """Pct change vs the file dated exactly 7*weeks earlier (1dp). Requires
    an exact-date prior file -- adjacent-file substitution would silently
    change the window length."""
    if as_of not in pts:
        return None, "no close for %s" % as_of
    target = (datetime.strptime(as_of, "%Y-%m-%d").date()
              - timedelta(weeks=weeks)).isoformat()
    if target not in pts:
        return None, "no weekly file dated %s (%dw prior)" % (target, weeks)
    base = pts[target]
    if base == 0:
        return None, "prior close is 0"
    return _r1(100.0 * (pts[as_of] / base - 1.0)), None


def _pctile_2y(pts: Dict[str, float], as_of: str) -> Tuple[Optional[int], Optional[str]]:
    """Percent of the trailing <=104 weekly closes strictly below the current
    close (integer 0-100). 0 = lowest of the window. Gaps are skipped, so the
    window is 'up to 104 available observations', not calendar weeks."""
    if as_of not in pts:
        return None, "no close for %s" % as_of
    vals = [v for _, v in sorted(pts.items()) if _ <= as_of][-PCTILE_WINDOW:]
    if not vals:
        return None, "no observations in window"
    cur = pts[as_of]
    below = sum(1 for v in vals if v < cur)
    return int(round(100.0 * below / len(vals))), None


def _level(pts: Dict[str, float], as_of: str, ndp: int = 2) -> Tuple[Optional[float], Optional[str]]:
    if as_of not in pts:
        return None, "no close for %s" % as_of
    return round(pts[as_of], ndp), None


def _rate_delta_bps(pts: Dict[str, float], as_of: str) -> Tuple[Optional[int], Optional[str]]:
    """Week-over-week level change in integer bps for rate series."""
    if as_of not in pts:
        return None, "no close for %s" % as_of
    target = (datetime.strptime(as_of, "%Y-%m-%d").date()
              - timedelta(weeks=1)).isoformat()
    if target not in pts:
        return None, "no weekly file dated %s (1w prior)" % target
    return int(round((pts[as_of] - pts[target]) * 100.0)), None


def _corr_spy_4w(pts: Dict[str, float], spy: Dict[str, float],
                 as_of: str) -> Tuple[Optional[float], Optional[str]]:
    """Pearson r of the trailing 4 weekly returns vs SPY's (3dp). Requires
    exact 7-day-spaced files for both series across all 4 return pairs;
    any gap -> null with the missing week named."""
    base = datetime.strptime(as_of, "%Y-%m-%d").date()
    rt: List[float] = []
    rs: List[float] = []
    for k in range(CORR_WEEKS):
        d1 = (base - timedelta(weeks=k)).isoformat()
        d0 = (base - timedelta(weeks=k + 1)).isoformat()
        for d in (d0, d1):
            if d not in pts:
                return None, "no close for %s (corr window)" % d
            if d not in spy:
                return None, "no SPY close for %s (corr window)" % d
        rt.insert(0, pts[d1] / pts[d0] - 1.0)
        rs.insert(0, spy[d1] / spy[d0] - 1.0)
    n = len(rt)
    mt = sum(rt) / n
    ms = sum(rs) / n
    cov = sum((a - mt) * (b - ms) for a, b in zip(rt, rs))
    vt = sum((a - mt) ** 2 for a in rt)
    vs = sum((b - ms) ** 2 for b in rs)
    if vt == 0 or vs == 0:
        return None, "zero variance in corr window"
    return _r3(cov / (vt * vs) ** 0.5), None


def _entry(fields: Dict[str, Tuple[Optional[float], Optional[str]]]) -> dict:
    """Assemble one instrument entry: every field present always; a null
    value carries a sibling '<field>_reason'."""
    out: Dict[str, object] = {}
    for name, (val, reason) in fields.items():
        out[name] = val
        if val is None:
            out[name + "_reason"] = reason or "unavailable"
    return out


def _px_entry(pts, spy, as_of, prev_corr, prev_corr_reason, with_corr):
    fields = {
        "px": _level(pts, as_of),
        "d1w": _pct_delta(pts, as_of, 1),
        "d4w": _pct_delta(pts, as_of, 4),
        "d13w": _pct_delta(pts, as_of, 13),
        "d52w": _pct_delta(pts, as_of, 52),
        "pctile_2y": _pctile_2y(pts, as_of),
    }
    if with_corr:
        fields["corr_spy_4w"] = _corr_spy_4w(pts, spy, as_of)
        fields["corr_prev"] = (prev_corr, prev_corr_reason)
    return _entry(fields)


def _regime(vix_pctile, curve_bps, fed_stance) -> str:
    """Computed regime label (MARKET_GROUNDING sec.9) -- rule-based, never
    free text. Tokens:
      risk appetite : VIX pctile_2y <=33 risk-on | <=66 risk-mixed | risk-off
      curve         : 2s10s >0 curve-positive | =0 curve-flat | <0 curve-inverted
      policy        : 'policy-' + lead word of facts.json fed_stance, lowercased
    Any unavailable input -> '<leg>-unknown'."""
    if vix_pctile is None:
        risk = "risk-unknown"
    elif vix_pctile <= 33:
        risk = "risk-on"
    elif vix_pctile <= 66:
        risk = "risk-mixed"
    else:
        risk = "risk-off"
    if curve_bps is None:
        curve = "curve-unknown"
    elif curve_bps > 0:
        curve = "curve-positive"
    elif curve_bps == 0:
        curve = "curve-flat"
    else:
        curve = "curve-inverted"
    lead = None
    if isinstance(fed_stance, str):
        m = re.match(r"[A-Za-z]+", fed_stance.strip())
        if m:
            lead = m.group(0).lower()
    policy = "policy-" + (lead or "unknown")
    return "%s / %s / %s" % (risk, curve, policy)


def _cash_2y_fields(pts: Dict[str, float], as_of: str,
                    history_problem: Optional[str]) -> dict:
    """The three US2Y fields, with reasons that say what is actually absent.

    The generic text ("no weekly file dated ...") would be wrong here: the
    file usually exists, and holds a futures mark the deriver will not read.
    """
    def gap(week):
        history = history_problem or "no %s entry" % US2Y_HISTORY_FILE
        return ("no Treasury 2-year for %s (no treasury-sourced rates.US2Y "
                "in that week's file, and %s); the 2YY=F future is never "
                "substituted" % (week, history))

    lvl = _level(pts, as_of)
    d1w = _rate_delta_bps(pts, as_of)
    pct = _pctile_2y(pts, as_of)
    if as_of not in pts:
        lvl = d1w = pct = (None, gap(as_of))
    elif d1w[0] is None:
        prior = (datetime.strptime(as_of, "%Y-%m-%d").date()
                 - timedelta(weeks=1)).isoformat()
        d1w = (None, gap(prior))
    if pct[0] is not None and history_problem:
        # Without the history the window holds only the weeks since the
        # cutover, and a rank among a handful of weeks is not a 2y percentile.
        pct = (None, "%s: the Treasury 2-year history before the cutover "
                     "is unavailable" % history_problem)
    return {"lvl": lvl, "d1w_bps": d1w, "pctile_2y": pct}


def _derive_from_files(docs: List[Tuple[str, dict]], facts: Optional[dict],
                       prev_market_state: Optional[dict],
                       us2y: Optional[Tuple[Dict[str, float],
                                            Optional[str]]] = None,
                       commodity: Optional[Tuple[Dict[str, dict],
                                                 Optional[str]]] = None
                       ) -> dict:
    """Core derivation over an explicit (date, doc) list -- the pure core
    shared by derive_market_state() and rederive_and_compare().

    us2y: the load_us2y_history() result, (history, problem).
    commodity: the load_commodity_history() result, (history, problem)."""
    if not docs:
        raise ValueError("no weekly files to derive from")
    as_of = docs[-1][0]
    facts = facts if isinstance(facts, dict) else {}
    us2y_history, us2y_problem = us2y if us2y is not None else (
        {}, "no Treasury 2-year history supplied")
    commodity_history, commodity_problem = (
        commodity if commodity is not None
        else ({}, "no commodity settlement history supplied"))

    spy = _close_series(docs, "SPY", None)

    def series_pts(t):
        return _close_series(docs, t, None)

    # -- index ---------------------------------------------------------------
    index = {}
    for t in INDEX_TICKERS:
        index[t] = _px_entry(series_pts(t), spy, as_of, None, None, with_corr=False)

    # -- vol -------------------------------------------------------------------
    vol = {}
    for t in VOL_TICKERS:
        pts = _close_series(docs, t, "vol")
        vol[t] = _entry({
            "lvl": _level(pts, as_of),
            "d1w": _pct_delta(pts, as_of, 1),
            "pctile_2y": _pctile_2y(pts, as_of),
        })

    # -- rates -----------------------------------------------------------------
    rates = {}
    for t in RATE_TICKERS:
        if t == CASH_2Y:
            # The history matters only if some week has to come from it. A
            # panel whose every week carries its own Treasury 2-year is
            # whole without the file.
            needs_history = any(
                not is_treasury_sourced(doc, "rates", CASH_2Y)
                for _, doc in docs)
            rates[t] = _entry(_cash_2y_fields(
                cash_2y_series(docs, us2y_history), as_of,
                us2y_problem if needs_history else None))
            continue
        pts = _close_series(docs, t, "rates")
        rates[t] = _entry({
            "lvl": _level(pts, as_of),
            "d1w_bps": _rate_delta_bps(pts, as_of),
            "pctile_2y": _pctile_2y(pts, as_of),
        })
    lvl10 = rates.get("US10Y", {}).get("lvl")
    lvl2 = rates.get("US2Y", {}).get("lvl")
    if lvl10 is not None and lvl2 is not None:
        rates["curve_2s10s_bps"] = int(round((lvl10 - lvl2) * 100.0))
    else:
        rates["curve_2s10s_bps"] = None
        rates["curve_2s10s_bps_reason"] = (
            "requires US10Y and US2Y closes for %s" % as_of)

    # -- sectors (with SPY correlation + last week's corr) ---------------------
    prev_sectors = (prev_market_state or {}).get("sectors") or {}
    sectors = {}
    for t in SECTOR_TICKERS:
        if prev_market_state is None:
            prev_corr, prev_reason = None, "no prev_market_state supplied"
        else:
            prev_rec = prev_sectors.get(t) or {}
            prev_corr = prev_rec.get("corr_spy_4w")
            prev_reason = (None if prev_corr is not None
                           else "prev_market_state has no corr_spy_4w for %s" % t)
        sectors[t] = _px_entry(series_pts(t), spy, as_of,
                               prev_corr, prev_reason, with_corr=True)

    # -- commodities / fx -------------------------------------------------------
    commodities = {}
    for t in COMMODITY_TICKERS:
        commodities[t] = _entry(_commodity_fields(
            t, docs, commodity_history, commodity_problem, as_of))
    fx = {}
    for t in FX_TICKERS:
        fx[t] = _px_entry(_close_series(docs, t, "fx"),
                          spy, as_of, None, None, with_corr=False)

    # -- policy / macro / upcoming from facts.json ------------------------------
    def fact(*path):
        node = facts
        for p in path:
            if not isinstance(node, dict) or p not in node:
                return None
            node = node[p]
        return node.get("value") if isinstance(node, dict) else node

    def fact_asof(*path):
        node = facts
        for p in path:
            if not isinstance(node, dict) or p not in node:
                return None
            node = node[p]
        return node.get("as_of") if isinstance(node, dict) else None

    policy = {}
    for field, path in (("fed_stance", ("policy", "fed_stance")),
                        ("fed_funds_range", ("policy", "fed_funds_range")),
                        ("next_macro_gate", ("policy", "next_macro_gate"))):
        val = fact(*path)
        policy[field] = val
        if val is None:
            policy[field + "_reason"] = "facts.json missing policy.%s" % path[-1]
        ao = fact_asof(*path)
        policy[field + "_as_of"] = ao
        if ao is None:
            policy[field + "_as_of_reason"] = "facts.json missing policy.%s as_of" % path[-1]

    macro = facts.get("macro_prints")
    macro_reason = None
    if macro is None:
        macro_reason = ("facts.json has no macro_prints block "
                        "(schema %s)" % facts.get("schema", "unknown"))
    upcoming = facts.get("upcoming")
    upcoming_reason = None
    if upcoming is None:
        gate = policy.get("next_macro_gate")
        if gate is not None:
            upcoming = [{"event": gate,
                         "when": policy.get("next_macro_gate_as_of"),
                         "binary": None}]
            upcoming_reason = None
        else:
            upcoming_reason = ("facts.json has no upcoming block and no "
                               "policy.next_macro_gate to fall back on")

    # -- regime (computed, never asked) -----------------------------------------
    regime = _regime(vol.get("VIX", {}).get("pctile_2y"),
                     rates.get("curve_2s10s_bps"),
                     policy.get("fed_stance"))

    state = {
        "schema": "market-state/v1",
        "as_of": as_of,
        "weekly_files_read": len(docs),
        "index": index,
        "vol": vol,
        "rates": rates,
        "sectors": sectors,
        "commodities": commodities,
        "fx": fx,
        "policy": policy,
        "regime": regime,
        "upcoming": upcoming,
        "macro": macro,
    }
    if macro_reason:
        state["macro_reason"] = macro_reason
    if upcoming_reason:
        state["upcoming_reason"] = upcoming_reason
    return state


def derive_market_state(weekly_dir: str, facts_path: str,
                        prev_market_state: Optional[dict] = None,
                        us2y_path: Optional[str] = None,
                        commodity_path: Optional[str] = None) -> dict:
    """Derive the MARKET_GROUNDING sec.1 snapshot from committed weekly
    files + facts.json + the two history files. PURE: no network, no
    clocks; as_of is the newest weekly file's date. Identical inputs ->
    byte-identical output.

    prev_market_state: last week's derived state (dict), used only for
    corr_prev. Pass None for the earliest week (corr_prev -> null+reason).
    us2y_path, commodity_path: the history files; they default to
    us2y_treasury.json and commodity_settlements.json beside weekly_dir, so
    existing callers need no change.
    """
    docs = _load_weekly_files(weekly_dir)
    facts = None
    try:
        with open(facts_path, "r", encoding="utf-8") as f:
            facts = json.load(f)
    except Exception:
        facts = None  # every facts-fed field degrades to null+reason
    us2y = load_us2y_history(us2y_path or us2y_history_path(weekly_dir))
    commodity = load_commodity_history(
        commodity_path or commodity_history_path(weekly_dir))
    return _derive_from_files(docs, facts, prev_market_state, us2y, commodity)


def write_market_state(weekly_dir: str, facts_path: str, out_path: str,
                       prev_market_state: Optional[dict] = None,
                       us2y_path: Optional[str] = None,
                       commodity_path: Optional[str] = None) -> str:
    """Convenience writer around derive_market_state (canonical bytes)."""
    state = derive_market_state(weekly_dir, facts_path, prev_market_state,
                                us2y_path, commodity_path)
    return _write_json(out_path, state)


def derive_chain(weekly_dir: str, facts_path: str,
                 us2y_path: Optional[str] = None,
                 commodity_path: Optional[str] = None) -> dict:
    """Derive the newest week's state through the WHOLE chain, earliest
    weekly file forward -- each week's state feeds the next as
    prev_market_state, so corr_prev is reproduced rather than supplied.

    This is the state rederive_and_compare() checks the committed file
    against, so it is also the one to write when the committed file has to
    be regenerated from scratch (a purity repair, a deriver change, a week
    added to either history file). scripts/rederive_market_state.py is that
    writer."""
    docs = _load_weekly_files(weekly_dir)
    facts = None
    try:
        with open(facts_path, "r", encoding="utf-8") as f:
            facts = json.load(f)
    except Exception:
        facts = None
    us2y = load_us2y_history(us2y_path or us2y_history_path(weekly_dir))
    commodity = load_commodity_history(
        commodity_path or commodity_history_path(weekly_dir))

    prev = None
    state = None
    for i in range(len(docs)):
        state = _derive_from_files(docs[: i + 1], facts, prev, us2y,
                                   commodity)
        prev = state
    if state is None:
        raise ValueError("no weekly files to derive from")
    return state


def write_market_state_chain(weekly_dir: str, facts_path: str, out_path: str,
                             us2y_path: Optional[str] = None,
                             commodity_path: Optional[str] = None) -> str:
    """Write market_state.json through the whole chain (canonical bytes).

    write_market_state takes last week's state from its caller, which is
    right only while the caller has written exactly one week since. A run
    that catches up on a week the writer refused earlier (section 1b) can
    write two, and the committed state it holds is then two weeks back:
    corr_prev would come from the wrong week and truth_check --derive would
    fail it. The chain needs no previous state and is what that check
    compares against, so it is right for one new week, for several, and for
    none."""
    state = derive_chain(weekly_dir, facts_path, us2y_path, commodity_path)
    return _write_json(out_path, state)


# ---------------------------------------------------------------------------
# 4. Purity self-check (Wave 2 truth gate)
# ---------------------------------------------------------------------------
def _first_diff(a, b, path: str = "$") -> Optional[str]:
    """First differing JSON path in sorted-key order; None if equal."""
    if type(a) is not type(b):
        return path
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                return "%s.%s (only in committed)" % (path, k)
            if k not in b:
                return "%s.%s (only in rederived)" % (path, k)
            sub = _first_diff(a[k], b[k], "%s.%s" % (path, k))
            if sub:
                return sub
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return "%s (len %d != %d)" % (path, len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            sub = _first_diff(x, y, "%s[%d]" % (path, i))
            if sub:
                return sub
        return None
    return None if a == b else path


def rederive_and_compare(weekly_dir: str, facts_path: str,
                         market_state_path: str,
                         us2y_path: Optional[str] = None,
                         commodity_path: Optional[str] = None
                         ) -> Tuple[bool, Optional[str]]:
    """Purity self-check for the truth gate.

    Re-derives the WHOLE chain from the earliest weekly file forward -- each
    week's derived state feeds the next as prev_market_state, so corr_prev is
    reproduced rather than skipped -- then compares the final state (as_of =
    newest weekly file) against the committed file, both semantically and as
    canonical bytes.

    Returns (match, first_differing_path). match=True iff canonical bytes
    are identical; first_differing_path is a JSON path like
    '$.sectors.SMH.d1w' or None when matched.
    """
    with open(market_state_path, "r", encoding="utf-8") as f:
        committed_raw = f.read()
    committed = json.loads(committed_raw)

    state = derive_chain(weekly_dir, facts_path, us2y_path, commodity_path)

    if canonical_json(state) == canonical_json(committed):
        return True, None
    return False, (_first_diff(state, committed) or "<bytes differ>")


# ---------------------------------------------------------------------------
# 5. Universe build (DATA_FEED.md sec.3)
# ---------------------------------------------------------------------------
def _grep_wiki_refs(wiki_dir: str, tickers: List[str]) -> Dict[str, List[str]]:
    """Whole-word, case-sensitive grep of each wiki/*.md for each ticker.
    An empty array is the NAKED flag -- correct, not an error."""
    pages: List[Tuple[str, str]] = []
    for path in sorted(glob.glob(os.path.join(wiki_dir, "*.md"))):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            pages.append(("wiki/" + os.path.basename(path), f.read()))
    refs: Dict[str, List[str]] = {}
    for t in tickers:
        pat = re.compile(r"\b" + re.escape(t) + r"\b")
        refs[t] = [name for name, text in pages if pat.search(text)]
    return refs


def _cap_tier(market_cap) -> Optional[str]:
    if market_cap is None:
        return None
    try:
        mc = float(market_cap)
    except (TypeError, ValueError):
        return None
    if mc >= CAP_MEGA:
        return "MEGA"
    if mc >= CAP_LARGE:
        return "LARGE"
    if mc >= CAP_MID:
        return "MID"
    return "SMALL"


def _enrich_one(ticker: str) -> Tuple[str, dict]:
    """yfinance .info for one ticker, fully defensive."""
    import yfinance as yf
    info = yf.Ticker(ticker).info
    if not isinstance(info, dict):
        raise ValueError("no info dict")
    return ticker, {
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "sub": info.get("industry"),
        "marketCap": info.get("marketCap"),
        "averageVolume": info.get("averageVolume"),
    }


def _batch_latest_closes(tickers: List[str]) -> Dict[str, float]:
    """Latest available close per ticker via one date-windowed batch download
    (last bar in a trailing 10-day window; enrichment only -- this value is
    never committed as a weekly observation)."""
    import yfinance as yf
    end = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    start = (datetime.now(timezone.utc).date() - timedelta(days=10)).isoformat()
    out: Dict[str, float] = {}
    df = yf.download(tickers, start=start, end=end, interval="1d",
                     group_by="ticker", auto_adjust=True,
                     progress=False, threads=True)
    for t in tickers:
        try:
            import pandas as pd
            sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
            closes = sub["Close"].dropna()
            if len(closes):
                out[t] = float(closes.iloc[-1])
        except Exception:
            pass
    return out


def build_universe(wiki_dir: str, out_path: str, enrich: bool = True,
                   md_path: Optional[str] = None,
                   tickers: Optional[List[str]] = None) -> dict:
    """Build universe.json (DATA_FEED.md sec.3) and optionally the human
    mirror universe.md.

    wiki_refs are grepped live from wiki_dir so they cannot drift from
    reality; an empty array is the NAKED flag. added/removed stay null --
    this is a legacy universe and we do NOT fabricate dates. With
    enrich=False every enrichment field is null with a '<field>_reason'
    sibling (never invented). as_of/next_review use the real build clock:
    universe.json is a build artifact, not a pure derivation.
    """
    # Not equity_universe(), on purpose. universe.json mirrors
    # wiki/universe.md, which lists stocks. The feed is wider by the sixteen
    # index and sector ETFs and by the Council watchlist's BTC and GLD, and
    # none of those is a universe row.
    tickers = sorted(set(tickers)) if tickers else sorted(
        set(STOCK_UNIVERSE) | set(BACKFILL_44_TICKERS))
    refs = _grep_wiki_refs(wiki_dir, tickers)

    info_map: Dict[str, dict] = {}
    close_map: Dict[str, float] = {}
    enrich_errors: Dict[str, str] = {}
    if enrich:
        try:
            close_map = _batch_latest_closes(tickers)
        except Exception as exc:
            enrich_errors["*closes*"] = "batch close fetch failed: %s" % exc
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futs = {pool.submit(_enrich_one, t): t for t in tickers}
            for fut in as_completed(futs):
                t = futs[fut]
                try:
                    _, info = fut.result()
                    info_map[t] = info
                except Exception as exc:
                    enrich_errors[t] = str(exc)

    entries = []
    for t in tickers:
        info = info_map.get(t, {})
        close = close_map.get(t)
        avg_vol = info.get("averageVolume")
        adv = None
        if avg_vol is not None and close is not None:
            try:
                adv = int(float(avg_vol) * close)
            except (TypeError, ValueError):
                adv = None

        entry = {
            "t": t,
            "name": info.get("name"),
            "sector": info.get("sector"),
            "sub": info.get("sub"),
            "cap": _cap_tier(info.get("marketCap")),
            "adv_usd": adv,
            "added": None,
            "removed": None,
            "wiki_refs": refs.get(t, []),
        }
        if not enrich:
            reason = "enrichment disabled (enrich=False)"
            for f_ in ("name", "sector", "sub", "cap", "adv_usd"):
                entry[f_ + "_reason"] = reason
        else:
            err = enrich_errors.get(t)
            for f_ in ("name", "sector", "sub"):
                if entry[f_] is None:
                    entry[f_ + "_reason"] = ("yfinance info failed: " + err) if err \
                        else "yfinance info field absent"
            if entry["cap"] is None:
                entry["cap_reason"] = (("yfinance info failed: " + err) if err
                                       else "marketCap absent")
            if entry["adv_usd"] is None:
                entry["adv_usd_reason"] = (
                    "averageVolume or latest close unavailable")
        entries.append(entry)

    today = datetime.now(timezone.utc).date()
    # quarterly review convention: next_review is the first day of the next
    # calendar quarter; additions/removals land only at review
    q_next_month = ((today.month - 1) // 3 + 1) * 3 + 1
    if q_next_month > 12:
        next_review = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_review = today.replace(month=q_next_month, day=1)

    doc = {
        "as_of": today.isoformat(),
        "next_review": next_review.isoformat(),
        "source": PROVIDER,
        "tickers": entries,
    }
    _write_json(out_path, doc)

    if md_path:
        _write_universe_md(md_path, doc)
    return doc


def _write_universe_md(md_path: str, doc: dict) -> str:
    """Human mirror wiki/universe.md: dated table of all tickers with
    sector/cap/wiki_refs count, headed by the quarterly review convention."""
    lines = [
        "# Universe",
        "",
        "As of %s. Machine mirror: `data/universe.json`." % doc["as_of"],
        "",
        "Reviewed **quarterly**; next review %s. Tickers enter or leave the"
        % doc["next_review"],
        "universe only at a quarterly review, recorded with a dated note in"
        " this file.",
        "`added` / `removed` dates are never back-filled for the legacy"
        " universe.",
        "",
        "`refs = 0` is the **NAKED** flag -- the wikis never mention the"
        " ticker, so the",
        "council has no narrative coverage for it. NAKED is a state to fix,"
        " not an error.",
        "",
        "| Ticker | Name | Sector | Cap | Refs |",
        "| --- | --- | --- | --- | --- |",
    ]
    for e in doc["tickers"]:
        lines.append("| %s | %s | %s | %s | %d |" % (
            e["t"],
            e.get("name") or "-",
            e.get("sector") or "-",
            e.get("cap") or "-",
            len(e.get("wiki_refs") or []),
        ))
    lines.append("")
    os.makedirs(os.path.dirname(os.path.abspath(md_path)), exist_ok=True)
    with open(md_path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))
    return md_path
