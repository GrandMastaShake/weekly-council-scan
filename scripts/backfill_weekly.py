"""
backfill_weekly.py -- one-time 104-week price backfill for weekly-council-scan.

Job B (Wave 2). Reads NO live per-week equity calls: one ranged daily-bar
download per ticker (batched ~50 tickers per yf.download call), then slices
each Friday's bar locally. Special instruments (rates/vol/commodities/fx) go
through scan_pipeline.snapshot_macro.fetch_special_instruments per Friday
(Job V contract; it carries its own per-instrument holiday notes). Since
2026-10-05 a commodity is read by contract name, and the provider drops a
contract once it has expired: a rewrite of a week older than a month or so
lists WTI, WTI_NEXT, GOLD and SILVER in "missing". Their settlements for
such a week are data/commodity_settlements.json's to hold (DATA_FEED.md
sec.1d).

Output (DATA_FEED.md sec.1, as amended by the owner):
  <out>/weekly/<YYYY-MM-DD>.json   one file per Friday, append-only.

Per-file conventions (byte-stability contract inherited from snapshot.py):
  * Written via snapshot.write_weekly() then post-processed in place:
      "source"     -> "yahoo-backfill"  (PROVIDER + "-backfill")
      "fetched_at" -> one shared UTC timestamp for the whole backfill run
    write_weekly itself records "session_note" (top-level, only on holiday
    Fridays): "Friday holiday; bars from <actual date>".
  * A week is written only with its session witness (2026-10-06, DATA_FEED.md
    sec.1c): SPY's bar dated the Friday, or -- only once a SPY bar dated
    after the Friday proves it was skipped -- the last session of that week.
    A Friday with neither is REFUSED and the run exits 2. Before that date
    a run on the night wrote Thursday's bars as a "Friday holiday" whenever
    no ticker had a Friday bar, which is also what a late post looks like.
  * Closes are split/dividend-adjusted (yfinance auto_adjust=True), rounded
    to 4dp by snapshot._normalize_block; volume int or None (never invented).
  * "missing" is REQUIRED: a ticker with no bar in the Monday..Friday week
    (pre-IPO, halted, delisted) is ABSENT from "series" (no nulls) and listed
    in "missing" with reason "no bar for week of <date> (likely pre-IPO or
    not trading)". No interpolation, ever.
  * --merge only adds (2026-10-06). A ticker named with --only goes into
    each week on file that lacks it, stamped in "provenance.series" with
    this run's fetch time. One a week already holds is left exactly as
    committed and reported; a merge never writes over it, with or without
    --force. A run that changes no file for that reason exits 2, and when
    the files alone show there is nothing to add it stops before any
    download, a dry run included. Before that date a named ticker was
    re-fetched over its committed bar and the run exited 0.
  * --merge never puts one company in the panel under two symbols
    (2026-10-06). The provider serves a renamed company's whole history
    under the new symbol, so a merge that named VMRK over the weeks that
    hold EQR added EQR's own bars a second time, exited 0, and passed every
    gate; a bar added to a week is never taken out. Two refusals, each for
    the whole run, exit 2, with nothing written:
      - a rename on record (RENAMED, scan_pipeline/config/tickers.py): the
        old symbol is never merged, and the new one is not added to any
        week up to the old symbol's last bar. Read off every week on file,
        so it stops before the download, a dry run included.
      - a rename nobody recorded: after the download, a named ticker that
        would share a non-zero volume with one other key in
        SAME_BARS_WEEKS weeks or more, counting the weeks the two already
        share, is that key's history under another symbol.

CLI:
  python backfill_weekly.py --out <data-root> [--start 2024-08-09]
         [--end 2026-08-07] [--only TICKER,TICKER] [--dry-run] [--force]

  --out is the DATA ROOT; files land at <out>/weekly/<date>.json (matching
  snapshot.write_weekly semantics). For the canonical run:
  --out C:\\Users\\alexa\\Documents\\kimi\\workspace\\truth_layer\\sweep\\data

  Existing files are never overwritten without --force (append-only
  discipline, even for the backfill). The writer holds every caller to
  that since 2026-10-06: snapshot.write_weekly raises WeekOnFile for a week
  that has its file, and --force is the one thing here that tells it to
  write anyway. Skipped files still feed the summary
  statistics. --only restricts the equity set (for filling slices); it does
  not restrict the special-instrument blocks.

NOTE on the window: the owner spec says "every Friday from 2024-08-09
through 2026-08-07 inclusive (104 weeks)". 2024-08-09..2026-08-07 inclusive
is actually 105 Fridays; the canonical 104-file run ending on the 2026-08-07
anchor uses --start 2024-08-16. The defaults reproduce the spec text; pass
--start explicitly for the canonical file count.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone

# Repo root = the nearest ancestor directory holding the scan_pipeline package.
# This file exists at two paths -- scripts/ and scan_pipeline/scripts/ -- so a
# fixed number of parent hops is correct for only one of them. Two hops from
# scripts/ lands ABOVE the repo, and the import below dies with
# ModuleNotFoundError; that is why the backfill workflow could never start.
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

from scan_pipeline import snapshot          # noqa: E402
from scan_pipeline import snapshot_macro    # noqa: E402
from scan_pipeline.config import tickers as feed_tickers    # noqa: E402

RUN_TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
BACKFILL_SOURCE = snapshot.PROVIDER + "-backfill"   # "yahoo-backfill"

CHUNK_SIZE = 50
CHUNK_RETRIES = 3
FRIDAY_SLEEP_S = 0.1        # politeness between per-Friday special fetches

MISSING_REASON = "no bar for week of %s (likely pre-IPO or not trading)"


def log(msg: str) -> None:
    print("[%s] %s" % (datetime.now(timezone.utc).strftime("%H:%M:%S"), msg),
          flush=True)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def fridays_in_range(start: str, end: str) -> list:
    """All Fridays in [start, end]. start must itself be a Friday."""
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    if d0.weekday() != 4:
        raise ValueError("--start %s is not a Friday" % start)
    if d1 < d0:
        raise ValueError("--end %s precedes --start %s" % (end, start))
    out = []
    d = d0
    while d <= d1:
        out.append(d)
        d += timedelta(days=7)
    return out


# ---------------------------------------------------------------------------
# Equity history: one ranged download per ticker, batched
# ---------------------------------------------------------------------------
def _subframe(df, ticker: str):
    """Extract one ticker's frame from a yf.download result (MultiIndex or
    plain columns for single-ticker downloads)."""
    import pandas as pd  # yfinance hard-depends on pandas
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        if ticker in df.columns.get_level_values(0):
            return df[ticker]
        if ticker in df.columns.get_level_values(-1):
            return df.xs(ticker, axis=1, level=-1)
        return None
    return df


def _frame_to_history(sub) -> tuple:
    """DataFrame -> (dates, closes, volumes) sorted by date, NaN closes
    dropped. Dates are datetime.date for bisect slicing."""
    dates, closes, vols = [], [], []
    if sub is None:
        return dates, closes, vols
    for idx, row in sub.iterrows():
        try:
            c = row["Close"]
        except Exception:
            continue
        try:
            if c != c:      # NaN
                continue
            c = float(c)
        except (TypeError, ValueError):
            continue
        v = None
        try:
            v = row["Volume"]
            if v == v:
                v = int(v)
            else:
                v = None
        except Exception:
            v = None
        d = idx.date() if hasattr(idx, "date") else idx
        dates.append(d)
        closes.append(c)
        vols.append(v)
    order = sorted(range(len(dates)), key=lambda i: dates[i])
    return ([dates[i] for i in order],
            [closes[i] for i in order],
            [vols[i] for i in order])


def _download_chunk(chunk: list, start_iso: str, end_iso: str):
    """yf.download one chunk with bounded backoff. Returns the frame or None."""
    import yfinance as yf
    for attempt in range(1, CHUNK_RETRIES + 1):
        try:
            df = yf.download(chunk, start=start_iso, end=end_iso,
                             interval="1d", group_by="ticker",
                             auto_adjust=True, progress=False, threads=True)
            if df is not None and len(df) > 0:
                return df
            log("    chunk returned empty (attempt %d/%d)"
                % (attempt, CHUNK_RETRIES))
        except Exception as exc:
            log("    chunk download raised (attempt %d/%d): %s"
                % (attempt, CHUNK_RETRIES, exc))
        if attempt < CHUNK_RETRIES:
            time.sleep(5 * attempt)     # back off rather than hammer
    return None


def download_equity_history(tickers: list, first_friday: date,
                            last_friday: date) -> dict:
    """{ticker: (dates, closes, vols)} for the whole backfill window.

    One ranged call per ticker, batched CHUNK_SIZE at a time. Fetch window
    starts 10 days before the first Friday (holiday/halt headroom for the
    'last trading day <= Friday' rule) and runs eight days past the last
    Friday. Nothing after a Friday is ever sliced into its week; a bar dated
    after it is there because it is the only proof that a Friday with no
    bars was a holiday (build_and_write). Tickers that never return data get
    empty histories and land in 'missing' for every week -- never
    fabricated."""
    start_iso = (first_friday - timedelta(days=10)).isoformat()
    end_iso = (last_friday + timedelta(days=9)).isoformat()
    history: dict = {}
    chunks = [tickers[i:i + CHUNK_SIZE]
              for i in range(0, len(tickers), CHUNK_SIZE)]
    log("equity download: %d tickers in %d chunks of <=%d, window %s..%s"
        % (len(tickers), len(chunks), CHUNK_SIZE, start_iso, end_iso))
    for ci, chunk in enumerate(chunks, 1):
        log("  chunk %d/%d: %d tickers (%s .. %s)"
            % (ci, len(chunks), len(chunk), chunk[0], chunk[-1]))
        df = _download_chunk(chunk, start_iso, end_iso)
        if df is None:
            # Whole chunk failed after retries: per-ticker fallback so one
            # throttled batch does not poison 50 tickers.
            log("    chunk %d failed %d times; falling back to per-ticker"
                % (ci, CHUNK_RETRIES))
            import yfinance as yf
            for t in chunk:
                try:
                    df1 = yf.download(t, start=start_iso, end=end_iso,
                                      interval="1d", auto_adjust=True,
                                      progress=False, threads=False)
                    history[t] = _frame_to_history(df1)
                except Exception as exc:
                    log("    per-ticker %s failed: %s" % (t, exc))
                    history[t] = ([], [], [])
                time.sleep(0.3)
        else:
            for t in chunk:
                try:
                    history[t] = _frame_to_history(_subframe(df, t))
                except Exception as exc:
                    log("    parse failed for %s: %s" % (t, exc))
                    history[t] = ([], [], [])
        if ci < len(chunks):
            time.sleep(2.0)             # short sleep between chunks
    empty = [t for t in tickers if not history.get(t, ([],))[0]]
    if empty:
        log("  %d tickers returned no bars at all: %s"
            % (len(empty), ", ".join(sorted(empty))))
    return history


def slice_week(hist: tuple, monday: date, friday: date):
    """Last bar on/before friday, provided it is inside the Mon..Fri week.
    Returns ({"close","volume"}, actual_date) or (None, None)."""
    dates, closes, vols = hist
    i = bisect_right(dates, friday) - 1
    if i < 0:
        return None, None
    d = dates[i]
    if d < monday:
        return None, None     # did not trade this week
    return {"close": closes[i], "volume": vols[i]}, d


# ---------------------------------------------------------------------------
# Weekly file assembly
# ---------------------------------------------------------------------------
def build_and_write(friday: date, tickers: list, history: dict,
                    out_dir: str, *, overwrite: bool = False) -> dict:
    """Slice one Friday, fetch specials, write via snapshot.write_weekly,
    then stamp backfill identity (source / fetched_at).

    Raises snapshot.NoSessionWitness, before anything is fetched or written,
    for a Friday the witness cannot answer for. Raises snapshot.WeekOnFile
    the same way for a week that already has its file, unless `overwrite`
    is set. That is --force, the declared rewrite, and nothing else."""
    if overwrite is not True:
        snapshot.refuse_week_on_file(friday.isoformat(), out_dir)
    # Which session the file is: the weekly writer's rule, asked of the
    # witness's own history. This used to be read off the slices below --
    # "no ticker has a Friday bar, so it was a holiday" -- which is true of
    # a holiday and equally true of a Friday the provider has not posted.
    if snapshot.WITNESS not in tickers:
        raise snapshot.NoSessionWitness(
            "REFUSED, nothing written for %s: this run does not fetch %s, "
            "and a week is not written without its session witness."
            % (friday.isoformat(), snapshot.WITNESS))
    session, why = snapshot.week_session(
        set(history.get(snapshot.WITNESS, ([], [], []))[0]), friday)
    if session is not None and session != friday:
        # The history drops a row with no close, so a Friday whose close
        # has not been posted looks like one that never traded. Ask the
        # provider's own listing before Thursday stands in for it.
        unconfirmed = snapshot.confirm_stand_in(friday)
        if unconfirmed is not None:
            session, why = None, unconfirmed
    if session is None:
        raise snapshot.NoSessionWitness(
            "REFUSED, nothing written for %s: %s. Run that week again "
            "later; the writer takes the Friday's bars if they are there by "
            "then, or the last session of the week once the Friday is "
            "proven to have been skipped." % (friday.isoformat(), why))

    # Sliced up to the file's session, not the Friday: a file that says
    # "bars from Thursday" cannot then hold a bar dated after it. For an
    # ordinary week the two are the same day and nothing changes.
    monday = friday - timedelta(days=4)
    bars: dict = {}
    missing: list = []
    for t in tickers:
        bar, _actual = slice_week(history.get(t, ([], [], [])),
                                  monday, session)
        if bar is None:
            missing.append({"ticker": t,
                            "reason": MISSING_REASON % friday.isoformat()})
        else:
            bars[t] = bar

    special = snapshot_macro.fetch_special_instruments(friday.isoformat())
    time.sleep(FRIDAY_SLEEP_S)

    # write_weekly turns a session that is not the Friday into session_note.
    path = snapshot.write_weekly(
        friday.isoformat(),
        {"bars": bars, "missing": missing, "session": session.isoformat()},
        special, out_dir=out_dir, overwrite=overwrite)

    # Backfill identity: write_weekly stamps PROVIDER ("yahoo") and the write
    # clock; restamp with the backfill source and the shared run timestamp so
    # backfilled files are distinguishable from live scans forever.
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    doc["source"] = BACKFILL_SOURCE
    doc["fetched_at"] = RUN_TS
    # A stand-in's label names the file's own provider (it exists to carry
    # "observed", the session the value is really from). It was fetched in
    # this run like everything else, so it takes the same identity; left as
    # "yahoo" it would be the one live-looking stamp in a backfilled file.
    # Another publisher's label (US2Y from Treasury) is not ours to restamp.
    for block in snapshot.SPECIAL_BLOCKS:
        for label in ((doc.get("provenance") or {}).get(block) or {}).values():
            if label.get("source") == snapshot.PROVIDER:
                label["source"] = BACKFILL_SOURCE
                label["fetched_at"] = RUN_TS
    # Whole or not at all, as the writer wrote it: a restamp that died
    # part-way would leave a file no later run may write over.
    snapshot._write_json(path, doc, whole=True)
    return {"path": path, "doc": doc,
            "session_note": doc.get("session_note")}


# ---------------------------------------------------------------------------
def read_week(path: str, friday: date) -> dict:
    """One weekly file, refused unless it is the week its name says it is.

    Both readers of a week on file come through here: the merge, and the
    plan that says what a merge will leave alone. Read without the check, a
    file under another week's name answers for a week it is not, and the
    plan would call a merge finished on the strength of the wrong bars."""
    with open(path, "r", encoding="utf-8") as f:
        try:
            doc = json.load(f)
        except ValueError as exc:
            raise SystemExit(
                "backfill: %s does not parse as JSON (%s) -- refusing to "
                "merge into a file that cannot be read" % (path, exc))
    as_of = doc.get("as_of") if isinstance(doc, dict) else None
    if as_of != friday.isoformat():
        raise SystemExit(
            "backfill: %s has as_of %r, expected %s -- refusing to merge "
            "into a file that is not the week it claims to be"
            % (path, as_of, friday.isoformat()))
    return doc


def merge_into_existing(friday: date, tickers: list, history: dict,
                        path: str) -> dict:
    """Add tickers to an existing week without disturbing what is there.

    A weekly file is an observation log. On 2026-08-26 a targeted backfill
    called write_weekly() with only the --only set, which writes a WHOLE
    file: 287 series became 44 across 107 weeks. Merging is the operation
    that was actually wanted.

    A merge adds, and that is all it does. A named ticker the week already
    holds is left exactly as it is: its bar, its `provenance.series` stamp
    if it has one, and `missing`. It comes back under "present". Until
    2026-10-06 it was fetched again and written over the committed bar,
    which the run logged as "refreshed". A fresh fetch is adjusted to a
    later date, so it is another close for any name that has paid a
    dividend or split since; the count of series does not move, and the
    count was all panel_guard and CI compared then (they compare bars
    since). No committed bar was hit: the
    two merge runs before that date (3a099f6, 5f0d596) named no ticker a
    week already held. A close the provider has restated is a correction's
    to carry (<date>.corrected.json, DATA_FEED.md sec.1), never this file's.

    Every other series, the special-instrument blocks, and the file-level
    source / fetched_at are left exactly as they were too. Each ticker that
    is added is stamped in `provenance.series` because it was fetched now
    and is therefore back-adjusted to a different date than the rest of the
    file. The file-level anchor still describes the majority of the series;
    the overrides describe the rest. Restamping the file-level anchor would
    relabel every untouched series with a fetch that never happened to it.

    With nothing to add and no new `missing` entry the file is not written
    at all, and "changed" is False: its bytes stay the commit's.

    A retired symbol, and a ticker whose company the week holds under an
    earlier one (RENAMED), is not added and not listed in `missing`. It
    comes back under "renamed". main() refuses such a run before it reaches
    a week, and for more weeks than this function can see
    (renamed_refusals); this is what stands in the way of a caller that
    does not come through main().
    """
    doc = read_week(path, friday)
    series = doc.setdefault("series", {})

    monday = friday - timedelta(days=4)
    present: list = []
    absent: list = []
    renamed: list = []
    fresh: dict = {}
    for t in tickers:
        if t in series:
            # Held already, so not this run's to touch. It is not sliced
            # either: the provider keeps one bar of a delisted symbol, the
            # last (AVB, EA), so such a name comes back with no bar for the
            # week and would be listed in `missing` beside the bar the week
            # still has for it.
            present.append(t)
            continue
        other = other_symbol_held(t, series)
        if other is not None:
            renamed.append((t, other))
            continue
        bar, _actual = slice_week(history.get(t, ([], [], [])),
                                  monday, friday)
        if bar is None:
            absent.append(t)
            continue
        fresh[t] = bar

    # Route through the same normalizer write_weekly uses, so a merged bar is
    # indistinguishable in shape and rounding from a scanned one. Writing the
    # raw slice instead lands full float precision (179.94000244140625) beside
    # the panel's rounded closes.
    merged = snapshot._normalize_block(fresh)

    listed = {m.get("ticker") for m in doc.get("missing", [])}
    unlisted = [t for t in absent if t not in listed]

    rec = {"path": path, "doc": doc, "added": list(merged),
           "present": present, "absent": absent, "renamed": renamed,
           "changed": bool(merged or unlisted)}
    if not rec["changed"]:
        return rec

    if merged:
        # Made only when there is a bar to stamp, and only its series part
        # is touched: the block can also name the source of a rates
        # instrument (US2Y from Treasury), which a merge must not erase.
        prov = doc.setdefault("provenance", {}).setdefault("series", {})
        for t, bar in merged.items():
            series[t] = bar
            prov[t] = {"source": BACKFILL_SOURCE, "fetched_at": RUN_TS}

    # `missing` stays honest in both directions: a ticker we just filled is
    # no longer missing, and one we could not fetch is listed with a reason
    # rather than silently absent.
    missing = [m for m in doc.get("missing", [])
               if m.get("ticker") not in merged]
    for t in unlisted:
        missing.append({"ticker": t,
                        "reason": MISSING_REASON % friday.isoformat()})
    doc["missing"] = sorted(missing, key=lambda m: m.get("ticker") or "")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(snapshot.canonical_json(doc))

    return rec


def held_already(weekly_dir: str, fridays: list, tickers: list) -> dict:
    """{ticker: [the Fridays whose file already holds a bar for it]}, read
    off the files as they stand. No network.

    A --merge leaves exactly these alone (merge_into_existing). Reading them
    first is what lets a dry run say so, and what stops a run that has
    nothing to add before it downloads anything. A Friday with no file is
    not looked at, and a file that is not its week is refused here as the
    merge refuses it (read_week)."""
    held: dict = {}
    for friday in fridays:
        path = os.path.join(weekly_dir, friday.isoformat() + ".json")
        if not os.path.exists(path):
            continue
        series = read_week(path, friday).get("series") or {}
        for t in tickers:
            if t in series:
                held.setdefault(t, []).append(friday)
    return held


def describe_held(held: dict, n_weeks: int) -> list:
    """What a merge will leave alone, as lines for the log: tickers grouped
    by how many of the n_weeks hold them, widest first. A ticker in only
    some of the weeks is shown with its first and last, which is where a
    name that joined the feed part-way begins."""
    def span(t: str) -> str:
        first, last = held[t][0], held[t][-1]
        return ("%s (%s)" % (t, first) if first == last
                else "%s (%s..%s)" % (t, first, last))

    by_count: dict = {}
    for t in sorted(held):
        by_count.setdefault(len(held[t]), []).append(t)
    lines = []
    for count in sorted(by_count, reverse=True):
        names = by_count[count]
        if count == n_weeks:
            lines.append("  in all %d week(s): %s"
                         % (n_weeks, ", ".join(names)))
        else:
            lines.append("  in %d of %d week(s): %s"
                         % (count, n_weeks, ", ".join(map(span, names))))
    return lines


# What a merge has to say for itself when it left a named ticker alone and
# changed no file. It exits 2: until 2026-10-06 the same command re-fetched
# that ticker over its committed bar and exited 0, so the run that now does
# nothing instead must not read as one that did something. (A run that left
# nothing alone and found nothing to add -- a pre-IPO name over weeks that
# already list it in `missing` -- exits 0, as it always has.)
#
# The last line is for a name its base file holds and its correction does
# not. It is not a way to restate a close: a correction is rebuilt from its
# base, so an equity close changed in one by hand does not survive.
NOTHING_MERGED_NEXT = (
    "  --merge adds a ticker to a week that lacks it. A ticker a week\n"
    "  already holds is left exactly as committed; nothing is written "
    "over it.\n"
    "  A close the provider has restated is never written over the bar in\n"
    "  the weekly file. It is a correction's to carry (DATA_FEED.md sec.1),\n"
    "  and no tool writes one for an equity bar yet.\n"
    "  If a week's correction lacks a name its base file holds, the\n"
    "  correction is stale: python scripts/rebuild_corrections.py")


# ---------------------------------------------------------------------------
# One company, one symbol a week
# ---------------------------------------------------------------------------
# The provider serves a renamed company's whole history under the symbol it
# trades by now, and of the retired symbol it keeps at most the last session.
# Each made a merge write what it must not, on copies of the panel on
# 2026-10-06, with exit 0 and every gate passing:
#
#   --only VMRK over the weeks that hold EQR   EQR's own bars a second time:
#                                              105 weeks holding both
#   --only EQR over 2026-08-21                 EQR's close of Monday
#                                              2026-08-17 under the Friday,
#                                              and EQR struck from `missing`
#
# A bar added to a week is never taken out, so each rule below stops the
# whole run before it writes, and none has a flag.

# How many weeks two keys must share a volume in before a run takes them for
# one history. Measured on the panel of 2026-10-06 (113 weeks, some 56,000
# pairs of keys a week): 59 pairs share a non-zero volume in a week, every
# one of them in exactly one week. EQR and VMRK, merged over each other on a
# copy, share it in 105.
SAME_BARS_WEEKS = 3

RENAMED_REFUSED = (
    "REFUSED, nothing downloaded and nothing written: this run would put "
    "one company in the panel under two symbols, or a retired symbol's last "
    "session under a Friday (RENAMED, scan_pipeline/config/tickers.py). "
    "Nothing overrides this, because a bar added to a week is never taken "
    "out.")

SAME_BARS_REFUSED = (
    "REFUSED, nothing written: the bars this run would add are already in "
    "the panel under another symbol. Nothing overrides this, because a bar "
    "added to a week is never taken out.")

SAME_BARS_NEXT = (
    "  Two companies do not trade the same number of shares week after\n"
    "  week: on the panel of 2026-10-06 no two tickers shared a volume in\n"
    "  more than one week. The provider is serving one history under both\n"
    "  symbols, as it does for a renamed company.\n"
    "  If one was renamed into the other, record it in RENAMED\n"
    "  (scan_pipeline/config/tickers.py) and in RENAMED_SYMBOLS\n"
    "  (scripts/truth_check.py), and name only the weeks after the old\n"
    "  symbol's last bar. If not, this wants a person before any week is\n"
    "  written.")


def real_bar(bar) -> bool:
    """A bar with trades behind it. A close on volume 0 or none is a print:
    AVB's two under a dead symbol are that (2026-08-21, 2026-08-28), and so
    is what a feed that still asks for a renamed company's old symbol may be
    handed. A print holds no week for a company and is not a symbol's last
    bar."""
    return isinstance(bar, dict) and bool(bar.get("volume"))


def panel_weeks(weekly_dir: str, must_read=None):
    """(Friday, document) for every week on file, oldest first. No network.

    The rules below are read off the whole panel and not a run's range:
    whether VMRK may go into 2024-08-09 depends on EQR's weeks after it.
    Corrections are not read. They are rebuilt from their bases, and the
    base is what a merge writes into.

    A week that cannot be read stops the run when the answer depends on it:
    every week, or with `must_read` the Fridays named there, the rest being
    stepped over."""
    for name in sorted(os.listdir(weekly_dir)):
        stem, ext = os.path.splitext(name)
        path = os.path.join(weekly_dir, name)
        if ext != ".json" or not os.path.isfile(path):
            continue
        try:
            friday = date.fromisoformat(stem)
        except ValueError:
            continue
        try:
            doc = read_week(path, friday)
        except SystemExit as unreadable:
            if must_read is not None and friday not in must_read:
                continue
            raise SystemExit(
                "%s\nbackfill: what a merge may add is read off every week "
                "on file, and that one cannot be read. Nothing was written."
                % unreadable)
        yield friday, doc


def other_symbol_held(ticker: str, series: dict):
    """The symbol that keeps `ticker` out of a week, or None (RENAMED,
    scan_pipeline/config/tickers.py): the one a retired symbol was renamed
    to, whatever the week holds, or an earlier symbol of the company that
    has a bar in `series`."""
    later = feed_tickers.later_symbols(ticker)
    if later:
        return later[0]
    for other in feed_tickers.earlier_symbols(ticker):
        if real_bar(series.get(other)):
            return other
    return None


def symbol_spans(weekly_dir: str, symbols) -> dict:
    """{symbol: (first Friday, last Friday)} whose file holds a bar for it,
    over every week on file."""
    spans: dict = {}
    for friday, doc in panel_weeks(weekly_dir):
        series = doc.get("series") or {}
        for s in symbols:
            if real_bar(series.get(s)):
                spans[s] = (spans.get(s, (friday, friday))[0], friday)
    return spans


def renamed_refusals(weekly_dir: str, on_file: list, tickers: list,
                     held: dict) -> list:
    """What a merge must not add because RENAMED says OLD became NEW:
    [(ticker, other, "retired" | "earlier", bound, weeks)], read off the
    files before anything is fetched.

      * OLD is never merged, into any week. The provider keeps at most its
        last session, and slice_week files that under the Friday of its
        week. Rehearsed on a copy, `--only EQR --merge` over 2026-08-21
        wrote EQR's close of Monday 2026-08-17 beside VMRK's Friday bar and
        struck EQR from that week's `missing`. Before VMRK was in that week
        the same run would have left the Monday bar there alone, and the
        week could never have taken its Friday one.
      * NEW is not added to any week up to OLD's last bar. In the weeks that
        hold OLD it would be OLD's own bar from a later fetch. In a week
        before them that holds neither (2024-08-09.json, for VMRK) it would
        be a bar with OLD's weeks after it, and the symbols of one company
        do not interleave.

    A pair the week already holds is not listed. It is left alone like any
    other bar a week holds (held_already)."""
    if not on_file:
        return []
    earlier = {t: feed_tickers.earlier_symbols(t) for t in tickers}
    wanted = {s for symbols in earlier.values() for s in symbols}
    spans = symbol_spans(weekly_dir, wanted) if wanted else {}
    out = []
    for t in tickers:
        have = set(held.get(t, ()))
        later = feed_tickers.later_symbols(t)
        if later:
            weeks = [f for f in on_file if f not in have]
            if weeks:
                out.append((t, later[0], "retired", None, weeks))
            continue
        for other in earlier[t]:
            if other in spans:
                bound = spans[other][1]
                weeks = [f for f in on_file if f <= bound and f not in have]
                if weeks:
                    out.append((t, other, "earlier", bound, weeks))
    return out


def _weeks(weeks: list) -> str:
    return (weeks[0].isoformat() if len(weeks) == 1
            else "%s..%s" % (weeks[0], weeks[-1]))


def describe_renamed(refusals: list) -> list:
    """renamed_refusals as lines for the log: what is refused, why, and for
    the new symbol the range that is not."""
    lines = []
    for t, other, which, bound, weeks in refusals:
        if which == "retired":
            lines.append(
                "  %s was renamed %s and is not merged into any week: %d "
                "week(s) named, %s. The provider serves that company's "
                "history under %s. Of a retired symbol it keeps at most the "
                "last session, and this script would file it under a Friday "
                "it did not trade on."
                % (t, other, len(weeks), _weeks(weeks), other))
        else:
            lines.append(
                "  %s is %s renamed. %s has bars through %s, so %s is not "
                "added to that week or any before it: %d of the week(s) "
                "named, %s. In the weeks that hold %s it would be %s's own "
                "bar a second time; in one that holds neither it would "
                "stand before %s's weeks. To add %s where the panel has no "
                "bar for the company, name only weeks after %s (--start "
                "%s)."
                % (t, other, other, bound, t, len(weeks), _weeks(weeks),
                   other, other, other, t, bound,
                   bound + timedelta(days=7)))
    return lines


def same_bars_refusals(weekly_dir: str, fridays: list, tickers: list,
                       history: dict) -> list:
    """Named tickers whose fresh bars are bars the panel already holds under
    another key: [(ticker, other, the weeks this run would add, the weeks
    the panel already holds both)], after the download and before anything
    is written.

    This is the rule for a rename nobody recorded, and it needs no map. The
    volume is the witness, as it is for audit_series.py: a close is adjusted
    to its fetch date, a volume is not. A named ticker that would come to
    share a non-zero volume with one other key in SAME_BARS_WEEKS weeks or
    more is that key's history under a second symbol. One other key: a name
    that meets three different tickers once each has met three coincidences
    (CI and ELV do, on the real panel).

    The count is the pair's, over every week on file, so the weeks a run
    would add are counted with the ones the pair already shares, and a
    doubling cannot be brought in two weeks at a time. Two names of one run
    are held against each other as well as against the panel.

    What it cannot see:

      * a pair that shares fewer weeks than that in all. The newest-week
        merge of a name that has just joined the feed is one week;
      * a week whose committed volume the provider has restated since. It
        restates many: the audit finds no session for the volume of 1,720
        of the weekly job's 3,181 bars (macro/series_audit.json). The files
        the backfill wrote are older and hold still;
      * a pair with a split between the two fetches, which moves the volume;
      * a retired symbol's last session, which is another day's volume;
      * anything at all in a dry run, which downloads nothing.

    RENAMED covers every one of those for a rename that is on record."""
    in_run = set(fridays)
    adding: dict = {}      # (ticker, other) -> the weeks this run would add
    already: dict = {}     # (ticker, other) -> the weeks the panel holds both
    for friday, doc in panel_weeks(weekly_dir, must_read=in_run):
        series = doc.get("series") or {}
        by_volume: dict = {}
        for other, bar in series.items():
            if real_bar(bar):
                by_volume.setdefault(bar["volume"], []).append(other)
        monday = friday - timedelta(days=4)
        fresh: dict = {}       # volume -> the named tickers it would arrive on
        for t in tickers:
            if t in series:
                if real_bar(series[t]):
                    for other in by_volume[series[t]["volume"]]:
                        if other != t:
                            already.setdefault((t, other), []).append(friday)
                continue
            if friday not in in_run:
                continue
            bar, _actual = slice_week(history.get(t, ([], [], [])),
                                      monday, friday)
            if bar is None or not bar["volume"]:
                continue
            for other in by_volume.get(bar["volume"], ()):
                adding.setdefault((t, other), []).append(friday)
            fresh.setdefault(bar["volume"], []).append(t)
        for names in fresh.values():
            names.sort()
            for i, t in enumerate(names):
                for other in names[i + 1:]:
                    adding.setdefault((t, other), []).append(friday)
    return sorted((t, other, weeks, already.get((t, other), []))
                  for (t, other), weeks in adding.items()
                  if len(weeks) + len(already.get((t, other), []))
                  >= SAME_BARS_WEEKS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="One-time 104-week weekly-file backfill "
                    "(weekly-council-scan data feed).")
    ap.add_argument("--out", required=True,
                    help="data root; files land at <out>/weekly/<date>.json")
    ap.add_argument("--start", default="2024-08-09",
                    help="first Friday, YYYY-MM-DD (default 2024-08-09)")
    ap.add_argument("--end", default="2026-08-07",
                    help="last Friday, YYYY-MM-DD (default 2026-08-07)")
    ap.add_argument("--only", default=None,
                    help="comma-separated equity tickers to restrict the run")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan; no network, no writes")
    ap.add_argument("--force", action="store_true",
                    help="allow overwriting existing weekly files WHOLE "
                         "(full-universe runs only; see --merge)")
    ap.add_argument("--merge", action="store_true",
                    help="add --only tickers into existing weekly files, "
                         "preserving every other series and the file-level "
                         "adjustment anchor; a ticker a week already holds "
                         "is left alone, never written over, and a run that "
                         "changes no file for that reason exits 2. So does "
                         "a run that would put one company in the panel "
                         "under two symbols (RENAMED, or the same volumes "
                         "under another key): it is refused whole")
    args = ap.parse_args()

    # The combination that emptied the panel on 2026-08-26. --force writes a
    # whole file from the ticker set it was given, so with --only it deletes
    # every name outside that set. Adding names to an existing week is
    # --merge; --force is for a full-universe rewrite and nothing else.
    if args.only and args.force and not args.merge:
        ap.error("--only with --force replaces each week with just those "
                 "tickers, deleting every other series (this emptied 107 "
                 "files on 2026-08-26). Use --merge to add them, or drop "
                 "--only for a full-universe rewrite.")
    if args.merge and not args.only:
        ap.error("--merge adds specific tickers to existing weeks; pass "
                 "--only with the tickers to add.")

    fridays = fridays_in_range(args.start, args.end)
    universe = snapshot.equity_universe()
    if args.only:
        only = sorted({t.strip().upper()
                       for t in args.only.split(",") if t.strip()})
        unknown = [t for t in only if t not in universe]
        if unknown:
            log("WARNING: --only tickers not in equity_universe(): %s"
                % ", ".join(unknown))
        tickers = only
    else:
        tickers = universe

    weekly_dir = os.path.join(args.out, "weekly")
    existing = {f for f in fridays
                if os.path.exists(os.path.join(
                    weekly_dir, f.isoformat() + ".json"))}

    log("backfill plan: %d Fridays %s..%s, %d equity tickers, out=%s"
        % (len(fridays), fridays[0], fridays[-1], len(tickers), weekly_dir))
    log("run timestamp (fetched_at for every file): %s" % RUN_TS)
    if existing:
        if args.merge:
            mode = ("will MERGE %d ticker(s) in (--merge); every other "
                    "series is preserved" % len(tickers))
        elif args.force:
            mode = "will OVERWRITE WHOLE (--force)"
        else:
            mode = "will SKIP"
        log("%d files already exist (%s)" % (len(existing), mode))

    # A merge adds and never replaces, so what it will leave alone is known
    # from the files, before anything is fetched. Said here, in the plan,
    # because the workflow's default is a dry run and this is what it shows.
    if args.merge:
        on_file = sorted(existing)
        held = held_already(weekly_dir, on_file, tickers)
        held_bars = sum(len(weeks) for weeks in held.values())
        named = len(tickers) * len(on_file)
        # One company, one symbol a week. Read off the files like the rest
        # of the plan, and not counted among what a fetch could add: for
        # VMRK over the whole panel this line answered "106 pair(s)", every
        # one of them a week VMRK must not go into.
        renamed = renamed_refusals(weekly_dir, on_file, tickers, held)
        barred = len({(r[0], week) for r in renamed for week in r[4]})
        if held_bars:
            log("already in the week, left alone: %d of the %d (ticker, "
                "week) pair(s) named" % (held_bars, named))
            for line in describe_held(held, len(on_file)):
                log(line)
            log("could be added, if the provider has a bar: %d pair(s)"
                % (named - held_bars - barred))
        if args.force:
            log("--force has no effect with --merge: a merge never rewrites "
                "a week, and never a bar the week already holds")
        if held_bars and held_bars == named:
            # Nothing a fetch could add. Refused before the download, and in
            # a dry run too: a plan that cannot do anything must not print
            # as one. A Friday in the range with no file does not change
            # that, since a run restricted with --only starts no week.
            print("NOTHING TO MERGE: all %d named ticker(s) already have a "
                  "bar in all %d week(s) on file from %s to %s. Nothing was "
                  "downloaded and nothing was written."
                  % (len(tickers), len(on_file), on_file[0], on_file[-1]))
            no_file = [f.isoformat() for f in fridays if f not in existing]
            if no_file:
                shown = ", ".join(no_file[:5])
                if len(no_file) > 5:
                    shown += " and %d more" % (len(no_file) - 5)
                print("  %d Friday(s) in the range have no file (%s). A run "
                      "restricted with --only adds to weeks that exist and "
                      "cannot start one." % (len(no_file), shown))
            print(NOTHING_MERGED_NEXT)
            return 2
        # Refused before the download, and in a dry run too, like the plan
        # with nothing to add above. The whole run: the weeks it could have
        # written are for a command that names only those.
        if renamed:
            print(RENAMED_REFUSED)
            for line in describe_renamed(renamed):
                print(line)
            return 2
    if args.dry_run:
        log("dry-run: no downloads, no writes. First 3 Fridays: %s; "
            "last 3: %s"
            % (", ".join(f.isoformat() for f in fridays[:3]),
               ", ".join(f.isoformat() for f in fridays[-3:])))
        log("dry-run OK")
        return 0

    os.makedirs(weekly_dir, exist_ok=True)
    history = download_equity_history(
        tickers, fridays[0], fridays[-1])

    if args.merge:
        # The same rule for a rename nobody recorded, which only the bars
        # can show. Asked before the first week is written.
        same = same_bars_refusals(weekly_dir, fridays, tickers, history)
        if same:
            print(SAME_BARS_REFUSED)
            for t, other, weeks, shared in same:
                print("  %s has the same non-zero volume as %s in %d week(s) "
                      "this run would add, %s%s."
                      % (t, other, len(weeks), _weeks(weeks),
                         ", and in %d the panel already holds, %s"
                         % (len(shared), _weeks(shared)) if shared else ""))
            print(SAME_BARS_NEXT)
            return 2

    written = skipped = unchanged = left_alone = 0
    missing_counts: list = []
    ticker_missing: dict = {t: 0 for t in tickers}
    notes: list = []
    refused: list = []
    for n, friday in enumerate(fridays, 1):
        path = os.path.join(weekly_dir, friday.isoformat() + ".json")
        if os.path.exists(path) and args.merge:
            rec = merge_into_existing(friday, tickers, history, path)
            doc = rec["doc"]
            n_missing = len(doc.get("missing", []))
            for m in doc.get("missing", []):
                if m.get("ticker") in ticker_missing:
                    ticker_missing[m["ticker"]] += 1
            missing_counts.append(n_missing)
            # A week with nothing to add is not rewritten, so it is not
            # counted as written either.
            if rec["changed"]:
                written += 1
            else:
                unchanged += 1
            left_alone += len(rec["present"])
            for t, other in rec["renamed"]:
                refused.append("%s: %s not added, it is one company with %s "
                               "(RENAMED)"
                               % (friday.isoformat(), t, other))
            log("  (%3d/%d) %s merged +%d new, %d already present (left "
                "alone), %d absent -> series=%d%s"
                % (n, len(fridays), friday, len(rec["added"]),
                   len(rec["present"]), len(rec["absent"]),
                   len(doc.get("series", {})),
                   "" if rec["changed"] else " [file unchanged]"))
            continue
        if os.path.exists(path) and not args.force:
            skipped += 1
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            for m in doc.get("missing", []):
                if m.get("ticker") in ticker_missing:
                    ticker_missing[m["ticker"]] += 1
            missing_counts.append(len(doc.get("missing", [])))
            log("  (%3d/%d) %s SKIP (exists)" % (n, len(fridays), friday))
            continue
        if args.only:
            # A restricted run has no week here to add to, and written as a
            # new file its few names would BE the week: every other ticker
            # in neither `series` nor `missing`. That is how 2024-08-09.json
            # was started, and naming SPY among them does not change it.
            refusal = ("REFUSED, nothing written: no weekly file for %s to "
                       "add to, and a run restricted with --only cannot "
                       "start one. A new week is one session of the whole "
                       "universe: run that Friday without --only first."
                       % friday.isoformat())
            refused.append("%s: %s" % (friday.isoformat(), refusal))
            log("  (%3d/%d) %s %s" % (n, len(fridays), friday, refusal))
            continue
        try:
            # Reached for a week on file only under --force (it was skipped
            # above otherwise), and --force is what tells the writer so.
            rec = build_and_write(friday, tickers, history, args.out,
                                  overwrite=args.force)
        except snapshot.NoSessionWitness as refusal:
            # Not a week this run can write. Say so and go on: the weeks
            # after it may be ordinary ones, and the exit code carries it.
            refused.append("%s: %s" % (friday.isoformat(), refusal))
            log("  (%3d/%d) %s %s" % (n, len(fridays), friday, refusal))
            continue
        doc = rec["doc"]
        n_missing = len(doc.get("missing", []))
        for m in doc.get("missing", []):
            if m.get("ticker") in ticker_missing:
                ticker_missing[m["ticker"]] += 1
        missing_counts.append(n_missing)
        written += 1
        if rec["session_note"]:
            notes.append("%s: %s" % (friday.isoformat(),
                                     rec["session_note"]))
        log("  (%3d/%d) %s wrote series=%d missing=%d%s"
            % (n, len(fridays), friday, len(doc.get("series", {})),
               n_missing,
               " [%s]" % rec["session_note"] if rec["session_note"] else ""))

    mc = sorted(missing_counts)
    median = mc[len(mc) // 2] if mc else 0
    chronic = sorted(t for t, c in ticker_missing.items()
                     if c > len(fridays) / 2)
    print("SUMMARY: files_written=%d files_unchanged=%d files_skipped=%d "
          "fridays=%d missing_per_file[min=%d median=%d max=%d] "
          "chronic_missing(>50%%)=%d %s"
          % (written, unchanged, skipped, len(fridays),
             mc[0] if mc else 0, median, mc[-1] if mc else 0,
             len(chronic),
             ("-> " + ", ".join(chronic)) if chronic else ""))
    if notes:
        print("SESSION_NOTES:")
        for s in notes:
            print("  " + s)
    if chronic:
        print("CHRONIC_MISSING (absent in >50%% of %d weeks):" % len(fridays))
        for t in chronic:
            print("  %s: missing %d/%d weeks"
                  % (t, ticker_missing[t], len(fridays)))
    if left_alone:
        print("ALREADY PRESENT: %d bar(s) named in --only were in their "
              "week already and were left alone (listed in the plan above)."
              % left_alone)
    # The fetch found nothing to add either. That is what running a finished
    # backfill's command a second time looks like: BACKFILL_44.md's has 43
    # names in every week and SPCX, which has no bar before its IPO.
    nothing_merged = bool(left_alone) and not written
    if nothing_merged:
        print("NOTHING MERGED: no file was changed. In every week on file, "
              "each named ticker was there already, or has no bar for the "
              "week and is in `missing` already.")
        print(NOTHING_MERGED_NEXT)
    if refused:
        # A refusal is a correct outcome and still not "done": exit 2, so a
        # run that left a week unwritten never reads as one that wrote it.
        print("REFUSED (%d week(s) not written):" % len(refused))
        for s in refused:
            print("  " + s)
        return 2
    return 2 if nothing_merged else 0


if __name__ == "__main__":
    sys.exit(main())
