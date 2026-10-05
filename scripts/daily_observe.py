"""daily_observe.py -- one completed US session, committed as an observation.

The weekly feed commits Friday closes because that is the cadence the council
reads. The bars behind it were never weekly: `snapshot.fetch_session_bars`
downloads daily bars over a ranged window and selects one. This script keeps
the other four sessions instead of discarding them.

It asks for the bar dated `as_of` and nothing else. The weekly writer lets
an earlier session stand in for a Friday that a later bar proves was skipped
(`snapshot.fetch_weekly_bars`); a daily file is named for the session it
holds, so here a date with no bar is a date with no file.

Output: <out>/daily/<YYYY-MM-DD>.json, the same shape as DATA_FEED.md sec.1
plus a `cadence` discriminator. Append-only, exactly like the weekly files.

What this is NOT
----------------
An observation, not a forecast. Nothing here scores a sector, and no consumer
of this file may treat it as a forecast artifact: the two judgment components
in sector-regime-heatmap (`regime_fit`, `macro_catalyst`) have no daily
source, and a daily file that carried them would be inventing them. This file
records what traded. That is the whole contract.

The session-witness gate
------------------------
The failure this script exists to avoid is committing a bar that is still
forming. `truth_check` v6.1 had to learn the same lesson from the other
direction (a weekday run comparing a Friday close against overnight futures).
A partial session is indistinguishable from a settled one once it is written
to disk, so the gate is up front:

    SPY is the session witness. No SPY bar dated exactly `as_of` means the
    session did not happen or has not settled, and the run refuses.

That is deliberately stricter than "some tickers returned data" -- on a
half-formed session a handful of names will always come back.

The witness has one blind spot and the clock covers it: while a session is
open SPY already has a bar dated today, and it is the forming one. So a date
whose 16:00 US/Eastern close has not passed is refused before anything is
fetched.

What the witness does not speak for
-----------------------------------
SPY settling says nothing about the futures. WTI, GOLD, SILVER, DXY and
US2Y_FUT trade past the cash close, and for two weeks their "bar dated
as_of" went into these files as a quote: on a weekday evening, the next
session's opening trades (WTI 89.63 against a settled 94.59 on 2026-09-22).
snapshot_macro now refuses such a bar until 13:00 UTC the next day, which is
later than either scheduled attempt, so those five are listed in `missing`
with the reason (DATA_FEED.md sec.1b).

The clock is US/Eastern, never UTC
----------------------------------
A session is a US/Eastern thing and the runner's clock is UTC. From 00:00 UTC
(20:00 ET in summer) the two name different dates, and that is about when
GitHub gets round to starting an evening schedule. Reading the date off UTC
made a late run ask for tomorrow, be refused, and never look at the session
that had just closed: six sessions between 2026-09-21 and 2026-10-01, every
run green.

The null-close window
---------------------
For an hour or more each evening the provider serves the just-closed
session's bar with a NULL close -- the row is there, volume and all, and the
price is not -- until its end-of-day roll fills it in. On this feed the bar
was served through 23:59:53 UTC, was gone at 00:10 and 00:45, and was back by
01:38. It starts at 00:00 UTC, which in summer is 20:00 ET, the end of the
post-market session; which of those two clocks it follows in winter has not
been observed. It is not the request: the provider appends its newest row
whatever `end` says, and a null close comes back null on every window and
range.

yfinance turns that row into "no bar" without a word, so the gate refuses,
correctly. What was wrong is that nothing asked again -- 2026-09-25 and
2026-10-02 were each refused once, at 00:10 and 00:45 UTC, and lost. Hence a
second scheduled attempt the next morning, and `explain_no_witness`, which
asks the provider directly so a refusal says which of the three it was: not
a session, a session not settled yet, or a provider that did not answer.

CLI:
  python scripts/daily_observe.py [--date YYYY-MM-DD] [--out data]
         [--dry-run] [--force] [--no-special] [--since YYYY-MM-DD]
  python scripts/daily_observe.py --audit [--out data]

  --date defaults to the most recent weekday whose US/Eastern close has
  passed. The gate above, not the calendar, decides whether that date is
  actually writable.

  --audit writes nothing. It asks the witness which sessions exist and exits
  1 if a settled one, other than the newest, has no file -- the check that
  makes a feed that has stopped writing fail somewhere a person will see.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone

# Repo root = the nearest ancestor holding the scan_pipeline package. Copied
# from scripts/backfill_weekly.py deliberately: a fixed number of parent hops
# is correct for exactly one of the two paths this pattern lives at, and that
# is the bug that kept the backfill workflow from ever starting.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PIPELINE_ROOT = _SCRIPT_DIR
while not os.path.isdir(os.path.join(_PIPELINE_ROOT, "scan_pipeline")):
    _parent = os.path.dirname(_PIPELINE_ROOT)
    if _parent == _PIPELINE_ROOT:
        raise RuntimeError(
            "cannot locate the scan_pipeline package above " + _SCRIPT_DIR)
    _PIPELINE_ROOT = _parent
if _PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, _PIPELINE_ROOT)

from scan_pipeline.config.tickers import PRICE_FEED_UNIVERSE  # noqa: E402
from scan_pipeline.snapshot import (  # noqa: E402
    INDEX_TICKERS,
    SECTOR_TICKERS,
    WITNESS,
    canonical_json,
    fetch_session_bars,
    get_special_instruments,
    special_provenance,
    _normalize_block,
)

# The daily file carries its own source label so a downstream adjustment-basis
# check cannot silently treat it as the weekly feed. Both are yfinance
# auto_adjust=True and therefore total-return; the label distinguishes
# provenance, not basis.
SOURCE = "yahoo-daily"

CADENCE = "daily"

# SPY is the session witness (see module docstring). It is also the benchmark
# every relative-momentum calculation downstream divides by, so a file without
# it is useless even if it were complete. WITNESS is snapshot's: the weekly
# writer gates on the same name, and one definition cannot drift from itself.

# The regular US close, US/Eastern wall time. An early close (13:00) is
# earlier, so a session is never taken as closed before it is.
CLOSE_ET = (16, 0)

_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"
_UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
_SESSION_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


class SessionNotSettled(RuntimeError):
    """The requested date is not a completed, settled US trading session."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def eastern(utc: datetime) -> datetime:
    """US/Eastern wall time for a UTC instant, by rule: EDT from the second
    Sunday of March (02:00 local) to the first Sunday of November (02:00
    local), EST otherwise.

    By rule rather than zoneinfo because the standard library ships no tz
    database on Windows, and this has to give one answer on the owner's
    machine and on a UTC runner. The same rule as screen/daily_screen.py.
    """
    if utc.tzinfo is not None:
        utc = utc.astimezone(timezone.utc).replace(tzinfo=None)

    def sunday(month: int, n: int) -> datetime:
        first = datetime(utc.year, month, 1)
        return first + timedelta(days=(6 - first.weekday()) % 7, weeks=n - 1)

    dst = (sunday(3, 2) + timedelta(hours=7)
           <= utc < sunday(11, 1) + timedelta(hours=6))
    return utc - timedelta(hours=4 if dst else 5)


def observation_universe(weekly_dir: str | None = None) -> list:
    """Every ticker the weekly feed commits, and never fewer.

    Deliberately the full universe, not the 110-name analysis focus. The rule
    in CLAUDE.md -- do not shrink the feed to the focus set -- applies with
    more force here: a daily file is the finest-grained record this repo
    keeps, and re-fetching a name later means fetching it against a different
    adjustment anchor, which is the divergence sec.4 warns about.

    `STOCK_UNIVERSE` alone is NOT enough and the first build of this script
    got it wrong: it is the ENGINE set, 277 names covering only 66 of the
    110-name watchlist, and it left Communication Services with 2 usable
    constituents. `PRICE_FEED_UNIVERSE` (320 since 2026-09-21) is the feed.

    The union with the newest weekly file's series is the self-healing part:
    if the panel grows again, the daily feed follows automatically instead of
    silently staying narrow.
    """
    universe = (set(PRICE_FEED_UNIVERSE)
                | set(INDEX_TICKERS) | set(SECTOR_TICKERS))
    if weekly_dir and os.path.isdir(weekly_dir):
        newest = sorted(f for f in os.listdir(weekly_dir)
                        if f.endswith(".json") and "corrected" not in f)
        if newest:
            path = os.path.join(weekly_dir, newest[-1])
            with open(path, encoding="utf-8") as f:
                universe |= set(json.load(f).get("series") or {})
    return sorted(universe)


def default_date(now: datetime | None = None) -> str:
    """The most recent weekday whose regular close has passed, US/Eastern.

    Takes an instant, not a date: 01:17 UTC on a Tuesday is 21:17 on Monday
    in New York, and Monday is the session that closed.

    A calendar guess only -- it knows weekends and the close, not holidays.
    Whether that session actually settled is decided by the witness gate,
    which is the part that cannot be wrong.
    """
    et = eastern(now or _utcnow())
    d = et.date()
    if (et.hour, et.minute) < CLOSE_ET:
        d -= timedelta(days=1)
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d -= timedelta(days=1)
    return d.isoformat()


def _stamp(now: datetime | None = None) -> str:
    return (now or _utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_document(as_of: str, fetched: dict, special: dict | None,
                   fetched_at: str | None = None) -> dict:
    """Assemble the daily document. Pure: no network, no clock except
    fetched_at, which is the adjustment anchor and must be real.

    `fetched_at` is passed in by the bootstrap, which stamps one download
    once: files cut from a single ranged download share its anchor exactly,
    not to within however long the loop took."""
    bars = fetched.get("bars") or {}
    missing = list(fetched.get("missing") or [])

    if special is None:
        special = {"rates": {}, "vol": {}, "commodities": {}, "fx": {},
                   "missing": [{"ticker": "*",
                                "reason": "special instruments not requested "
                                          "(--no-special)"}]}
    missing.extend(special.get("missing") or [])

    # dedupe + sort, matching write_weekly so the two files diff the same way
    seen = set()
    uniq = []
    for m in missing:
        key = (str(m.get("ticker")), str(m.get("reason")))
        if key not in seen:
            seen.add(key)
            uniq.append({"ticker": key[0], "reason": key[1]})
    uniq.sort(key=lambda m: (m["ticker"], m["reason"]))

    doc = {
        "as_of": as_of,
        "cadence": CADENCE,
        "source": SOURCE,
        "fetched_at": fetched_at or _stamp(),
        "session": "close",
        "series": _normalize_block(bars),
        "rates": _normalize_block(special.get("rates")),
        "vol": _normalize_block(special.get("vol")),
        "commodities": _normalize_block(special.get("commodities")),
        "fx": _normalize_block(special.get("fx")),
        "missing": uniq,
    }
    # US2Y comes from Treasury, not from this file's provider, and says so
    # per instrument exactly as the weekly file does (DATA_FEED.md sec.1).
    prov = special_provenance(special, doc)
    if prov:
        doc["provenance"] = prov
    return doc


def assert_session_closed(as_of: str, now: datetime | None = None) -> None:
    """Refuse a date whose session cannot have closed yet, by the clock alone.

    Needs no fetch, so it runs before one. It is the one call the witness
    cannot make: during a session SPY has a bar dated today, and it is the
    forming one.
    """
    et = eastern(now or _utcnow())
    d = date.fromisoformat(as_of)
    if d > et.date():
        raise SessionNotSettled(
            "as_of " + as_of + " is in the future (US/Eastern today is "
            + et.date().isoformat() + "). There is no bar to observe.")
    if d == et.date() and (et.hour, et.minute) < CLOSE_ET:
        raise SessionNotSettled(
            "as_of " + as_of + " is today and the regular session has not "
            "closed (" + et.strftime("%H:%M") + " US/Eastern, close 16:00). "
            "Any bar the provider shows for it is still forming. Re-run after "
            "the close.")


def assert_session_settled(as_of: str, bars: dict,
                           now: datetime | None = None) -> None:
    """Refuse anything but a completed session. See module docstring."""
    assert_session_closed(as_of, now)
    if WITNESS not in bars:
        raise SessionNotSettled(
            "No " + WITNESS + " bar dated " + as_of + ". Either that date was "
            "not a US trading session, or the session has not settled with the "
            "provider yet. Refusing to write a file whose bars may still be "
            "forming -- a partial session is indistinguishable from a settled "
            "one once committed. Re-run after the close, or pass --date for a "
            "session known to be complete.")


def _fetch_chart(symbol: str, start: date, end: date):
    """The provider's raw daily rows for [start, end], or None. Stdlib only."""
    import urllib.request

    def epoch(d: date) -> int:
        return int(datetime(d.year, d.month, d.day,
                            tzinfo=timezone.utc).timestamp())

    # Two days of slack past `end`: the bounds are UTC and the rows are
    # stamped in exchange time. The provider appends its newest row whatever
    # period2 says, so the slack costs nothing and the caller filters by date.
    url = (_CHART + symbol + "?period1=" + str(epoch(start)) + "&period2="
           + str(epoch(end + timedelta(days=2)))
           + "&interval=1d&includePrePost=false")
    for pause in (2, 4, 0):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception:
            time.sleep(pause)
    return None


def witness_rows(start: str, end: str, fetch=None):
    """What the provider itself lists for the witness over [start, end]:
    {session date: close, or None where the close is null}.

    Asked of the raw chart endpoint rather than through yfinance, because the
    distinction this exists to draw is one yfinance erases: a session whose
    row is present with a null close (ended, not settled) comes back from
    yfinance looking exactly like a date with no row at all (not a session).

    Returns None when the provider could not be asked or answered something
    unreadable. "Unknown" must never read as "no session".
    """
    payload = (fetch or _fetch_chart)(WITNESS, date.fromisoformat(start),
                                      date.fromisoformat(end))
    rows: dict = {}
    try:
        result = payload["chart"]["result"][0]
        stamps = result.get("timestamp") or []
        closes = result["indicators"]["quote"][0].get("close") or []
        for stamp, close in zip(stamps, closes):
            day = eastern(datetime.fromtimestamp(stamp, timezone.utc)).date()
            day = day.isoformat()
            if not start <= day <= end:
                continue
            if close is None or close != close:      # null, or NaN
                # Never overwrite a price: while a session is live its own
                # row is null and the close rides on a second row stamped at
                # the last trade, same date.
                rows.setdefault(day, None)
            else:
                rows[day] = float(close)
    except (KeyError, IndexError, TypeError, AttributeError, ValueError,
            OverflowError, OSError):
        return None
    return dict(sorted(rows.items()))


def explain_no_witness(as_of: str, rows) -> str:
    """Why the batch had no witness bar, in the provider's own terms.

    The gate's refusal is the same sentence for a holiday, a wrong target
    date and an unsettled session, which is how a run that asked for the
    wrong day every night looked healthy for two weeks.
    """
    if rows is None:
        return ("Could not ask the provider what it lists for " + WITNESS
                + ", so this refusal cannot be narrowed down.")
    if as_of in rows:
        if rows[as_of] is None:
            return ("The provider lists " + as_of + " as a session with a NULL "
                    "close: the session ended and its bar has not settled. "
                    "It does this for an hour or more from 00:00 UTC; the "
                    "next scheduled attempt picks it up.")
        return ("The provider does list a settled " + WITNESS + " close for "
                + as_of + ", so the batch download dropped it: a transient "
                "provider failure. Re-run.")
    if not rows:
        return ("The provider lists no session on or just before " + as_of
                + ".")
    latest = max(rows)
    state = "close still null" if rows[latest] is None else "settled"
    return ("The provider lists no session on " + as_of + " (a market "
            "holiday, or a date that has not traded). The latest session it "
            "lists is " + latest + " (" + state + ").")


def fetch_session_range(tickers: list, start: str, end: str) -> dict:
    """One ranged download, sliced into per-session bar maps.

    The bootstrap path. Fetching N sessions with N date-pinned calls costs N
    round trips and, worse, N different fetch timestamps -- so the files would
    carry N adjustment anchors for bars that a single download would have put
    on one. One ranged call gives every session the same anchor, which is what
    a consumer comparing two sessions needs.

    Returns {session_date: {ticker: {"close", "volume"}}} for every date in
    range that has a witness bar. Non-sessions simply do not appear.
    """
    import yfinance as yf

    tickers = sorted(set(tickers))
    end_excl = (date.fromisoformat(end) + timedelta(days=1)).isoformat()
    df = yf.download(tickers, start=start, end=end_excl, interval="1d",
                     group_by="ticker", auto_adjust=True,
                     progress=False, threads=True)

    sessions: dict = {}
    for ts in df.index:
        day = ts.date().isoformat()
        day_bars = {}
        for t in tickers:
            try:
                row = df[t].loc[ts]
            except Exception:
                continue
            close = row.get("Close")
            if close is None or close != close:      # NaN
                continue
            vol = row.get("Volume")
            volume = None
            try:
                if vol is not None and vol == vol and int(vol) > 0:
                    volume = int(vol)
            except (TypeError, ValueError):
                volume = None
            day_bars[t] = {"close": float(close), "volume": volume}
        if WITNESS in day_bars:
            sessions[day] = day_bars
    return sessions


def missing_for(tickers: list, day_bars: dict, as_of: str) -> list:
    """Every requested ticker without a bar, with a reason. Never omitted."""
    return [{"ticker": t,
             "reason": "no bar dated " + as_of + " in the ranged download"}
            for t in sorted(set(tickers)) if t not in day_bars]


def document_path(out_dir: str, as_of: str) -> str:
    return os.path.join(out_dir, "daily", as_of + ".json")


def _exists_message(path: str, as_of: str) -> str:
    return (path + " already exists. Daily files are append-only, exactly like "
            "the weekly ones: if the provider restated, write a "
            + as_of + ".corrected.json rather than editing this. "
            "--force is for re-running a failed write, nothing else.")


def write_document(doc: dict, out_dir: str, force: bool = False) -> str:
    path = document_path(out_dir, doc["as_of"])
    if os.path.exists(path) and not force:
        raise FileExistsError(_exists_message(path, doc["as_of"]))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(canonical_json(doc))
    return path


def panel_sessions(daily_dir: str) -> list:
    """Session dates that have a committed file, oldest first.

    A correction is not counted: it restates a base file and cannot stand in
    for one.
    """
    if not os.path.isdir(daily_dir):
        return []
    return sorted(m.group(1)
                  for m in map(_SESSION_FILE.match, os.listdir(daily_dir)) if m)


def weekdays_after(after: str, through: str) -> list:
    """Weekdays d with after < d <= through. A calendar count, not a session
    count: it cannot see a market holiday."""
    out = []
    d = date.fromisoformat(after) + timedelta(days=1)
    stop = date.fromisoformat(through)
    while d <= stop:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _listing(days: list, limit: int = 12) -> str:
    shown = ", ".join(days[:limit])
    if len(days) > limit:
        shown += ", ... and " + str(len(days) - limit) + " more"
    return shown


def audit_feed(have: list, rows, now: datetime | None = None) -> tuple:
    """Is the panel complete and current? Returns (level, lines).

    `have` is panel_sessions(); `rows` is witness_rows() from the first file
    through the last closed session. The sessions counted are therefore the
    provider's, not a calendar's -- a holiday is never a hole.

      FAIL     a settled session other than the newest has no file. Every
               scheduled attempt aims at the latest session, so nothing will
               ever write it: the panel stays incomplete until someone
               recovers it. This is the state the feed sat in, green, from
               2026-09-24.
      WARN     only the newest settled session is unwritten -- one attempt
               missed and the next has not run -- or the witness could not
               be asked.
      OK       every settled session has a file.
      PENDING  a note, not a level: a session has closed and its close is
               still null with the provider. Expected of any evening run
               that lands in the null-close window.
    """
    last_closed = default_date(now)
    if not have:
        return "WARN", ["WARN: no daily files to audit."]
    first, newest = have[0], have[-1]
    on_file = set(have)

    closed = {d: c for d, c in (rows or {}).items()
              if first <= d <= last_closed}
    settled = [d for d in sorted(closed) if closed[d] is not None]

    # A witness that confirms none of the sessions already on file answered
    # for something else, or with nothing. Treat it as no answer rather than
    # as "nothing is missing".
    if rows is None or not on_file.intersection(settled):
        behind = weekdays_after(newest, last_closed)
        if len(behind) >= 2:
            return "FAIL", [
                "FAIL: the witness could not be asked, and by the weekday "
                "calendar the newest daily file (" + newest + ") is "
                + str(len(behind)) + " weekdays behind the last close ("
                + last_closed + "): " + _listing(behind) + ". Weekdays are "
                "not sessions, but two or more in a row with no file is a "
                "feed that has stopped, not a holiday."]
        return "WARN", [
            "WARN: audit unverified -- the witness could not be asked which "
            "sessions it lists. Newest daily file " + newest + "; last close "
            "by the weekday calendar " + last_closed + "."]

    missing = [d for d in settled if d not in on_file]
    lines = []
    if [d for d in missing if d != settled[-1]]:
        level = "FAIL"
        lines.append(
            "FAIL: " + str(len(missing)) + " settled session(s) the witness "
            "lists have no daily file: " + _listing(missing) + ". No "
            "scheduled attempt will write them; the panel is incomplete "
            "until they are recovered.")
        if len(missing) == 1:
            lines.append("  Recover it:")
            lines.append("  python scripts/daily_observe.py --date "
                         + missing[0])
        else:
            lines.append("  Recover them from ONE ranged download, so they "
                         "share an adjustment anchor (DATA_FEED.md sec.4):")
            lines.append("  python scripts/daily_observe.py --since "
                         + missing[0] + " --date " + missing[-1])
    elif missing:
        level = "WARN"
        lines.append(
            "WARN: " + missing[0] + " is settled with the provider and has no "
            "daily file. One attempt missed it; the next scheduled attempt "
            "should write it. Unwritten after that, it is a hole.")
    else:
        level = "OK"
        lines.append(
            "OK: daily feed complete -- " + str(len(settled)) + " settled "
            "session(s) from " + first + " through " + settled[-1]
            + ", each with a file.")
    for d in sorted(closed):
        if closed[d] is None and d not in on_file:
            lines.append(
                "PENDING: " + d + " has closed and the provider has not "
                "settled its bar (null close). The next scheduled attempt "
                "retries it.")
    return level, lines


def _run_audit(a) -> int:
    """--audit: report, write nothing, exit 1 on a hole."""
    have = panel_sessions(os.path.join(a.out, "daily"))
    rows = witness_rows(have[0], default_date()) if have else None
    level, lines = audit_feed(have, rows)
    for line in lines:
        print(line)
    return 1 if level == "FAIL" else 0


def _run_backfill(a, as_of: str, tickers: list) -> int:
    """Bootstrap every settled session in [--since, --date] from one download."""
    # Never past the last close. A range that ran into a session still open
    # would pick up its forming bar, and the witness could not tell.
    last_closed = default_date()
    if as_of > last_closed:
        print("Range end " + as_of + " is past the last close ("
              + last_closed + " US/Eastern); stopping there.")
        as_of = last_closed
    print("Bootstrapping " + a.since + " .. " + as_of + " over "
          + str(len(tickers)) + " tickers (one ranged download)")
    sessions = {day: day_bars for day, day_bars
                in fetch_session_range(tickers, a.since, as_of).items()
                if a.since <= day <= as_of}
    fetched_at = _stamp()        # one download, one anchor, every file
    if not sessions:
        print("REFUSED: no settled session found in that range (no "
              + WITNESS + " bar on any date).")
        return 2

    special_note = {"rates": {}, "vol": {}, "commodities": {}, "fx": {},
                    "missing": [{"ticker": "*",
                                 "reason": "bootstrap backfill: special "
                                           "instruments not fetched"}]}
    written, skipped = 0, 0
    for day in sorted(sessions):
        day_bars = sessions[day]
        fetched = {"bars": day_bars,
                   "missing": missing_for(tickers, day_bars, day)}
        doc = build_document(day, fetched, special_note, fetched_at)
        if a.dry_run:
            # Say what a real run would do with each day, or the preview of
            # a recovery cannot be told from a rewrite of the whole range.
            if os.path.exists(document_path(a.out, day)) and not a.force:
                print("  " + day + ": exists, would be skipped (append-only)")
                skipped += 1
                continue
            print("  " + day + ": " + str(len(doc["series"])) + " series, "
                  + str(len(doc["missing"])) + " missing (dry run)")
            written += 1
            continue
        try:
            write_document(doc, a.out, force=a.force)
        except FileExistsError:
            print("  " + day + ": exists, skipped (append-only)")
            skipped += 1
            continue
        print("  " + day + ": " + str(len(doc["series"])) + " series, "
              + str(len(doc["missing"])) + " missing")
        written += 1
    if a.dry_run:
        print("DRY RUN: nothing written. A real run would write "
              + str(written) + " session file(s) and skip " + str(skipped)
              + " existing.")
        return 0
    print("Wrote " + str(written) + " session file(s), skipped "
          + str(skipped) + " existing.")
    return 0


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", default=None,
                   help="session date YYYY-MM-DD (default: the latest weekday "
                        "whose US/Eastern close has passed)")
    p.add_argument("--out", default="data", help="data root (default: data)")
    p.add_argument("--dry-run", action="store_true",
                   help="fetch and report, write nothing")
    p.add_argument("--force", action="store_true",
                   help="overwrite an existing file (re-running a failed write only)")
    p.add_argument("--no-special",
                   action="store_true",
                   help="skip rates/vol/commodities/fx (equities only)")
    p.add_argument("--since", default=None,
                   help="bootstrap: write every settled session from this date "
                        "through --date in one ranged download")
    p.add_argument("--audit", action="store_true",
                   help="write nothing: check the panel against the sessions "
                        "the witness lists, exit 1 if one is missing")
    a = p.parse_args(argv)

    if a.audit:
        return _run_audit(a)

    as_of = a.date or default_date()
    tickers = observation_universe(os.path.join(a.out, "weekly"))

    if a.since:
        return _run_backfill(a, as_of, tickers)

    # Neither refusal below needs a fetch, so neither pays for one. The
    # second is the common case now that a session gets two attempts.
    try:
        assert_session_closed(as_of)
    except SessionNotSettled as exc:
        print("REFUSED: " + str(exc))
        return 2
    path = document_path(a.out, as_of)
    if os.path.exists(path) and not (a.force or a.dry_run):
        print("REFUSED: " + _exists_message(path, as_of))
        return 2

    print("Observing " + as_of + " over " + str(len(tickers)) + " tickers")

    fetched = fetch_session_bars(tickers, as_of)
    bars = fetched.get("bars") or {}

    try:
        assert_session_settled(as_of, bars)
    except SessionNotSettled as exc:
        print("REFUSED: " + str(exc))
        probe_from = (date.fromisoformat(as_of)
                      - timedelta(days=10)).isoformat()
        print("  " + explain_no_witness(as_of,
                                        witness_rows(probe_from, as_of)))
        return 2

    special = None if a.no_special else get_special_instruments(as_of)
    doc = build_document(as_of, fetched, special)

    got = len(doc["series"])
    print("  series " + str(got) + "/" + str(len(tickers))
          + ", missing " + str(len(doc["missing"])))
    for m in doc["missing"][:10]:
        print("    missing " + m["ticker"] + ": " + m["reason"])
    if len(doc["missing"]) > 10:
        print("    ... and " + str(len(doc["missing"]) - 10) + " more")

    if a.dry_run:
        print("DRY RUN: nothing written")
        return 0

    try:
        path = write_document(doc, a.out, force=a.force)
    except FileExistsError as exc:
        print("REFUSED: " + str(exc))
        return 2
    print("Wrote " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
