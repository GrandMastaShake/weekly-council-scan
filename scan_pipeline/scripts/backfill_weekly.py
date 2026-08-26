"""
DO NOT RUN THIS COPY. (Repo-side annotation, 2026-08-26. Everything below
this block is the runner's file, unchanged.)

This is the mirror of Kimi's external runner, kept so the public repo shows
what the runner does. It has DIVERGED from scripts/backfill_weekly.py, which
is the copy this repository actually uses and the only one that is safe here.

The difference is not cosmetic. This copy has no `--merge`, so the only way it
can add tickers to an existing week is `--only ... --force`, and that writes a
WHOLE file from the ticker set it was given -- deleting every series outside
it. On 2026-08-26 that turned 287 series into 44 across 107 weekly files while
reporting success. scripts/backfill_weekly.py refuses the combination outright
and adds names with `--merge` instead.

Its root-resolution also assumes it lives at scan_pipeline/scripts/, which is
true here and is why this copy still imports while the other one had to be
fixed.

Nothing in this repository invokes this file, and a test
(tests/test_corrections_and_feed.py) fails if anything starts to. The real fix
is upstream in the runner; until that lands, use scripts/backfill_weekly.py.

backfill_weekly.py -- one-time 104-week price backfill for weekly-council-scan.

Job B (Wave 2). Reads NO live per-week equity calls: one ranged daily-bar
download per ticker (batched ~50 tickers per yf.download call), then slices
each Friday's bar locally. Special instruments (rates/vol/commodities/fx) go
through scan_pipeline.snapshot_macro.fetch_special_instruments per Friday
(Job V contract; it carries its own per-instrument holiday notes).

Output (DATA_FEED.md sec.1, as amended by the owner):
  <out>/weekly/<YYYY-MM-DD>.json   one file per Friday, append-only.

Per-file conventions (byte-stability contract inherited from snapshot.py):
  * Written via snapshot.write_weekly() then post-processed in place:
      "source"     -> "yahoo-backfill"  (PROVIDER + "-backfill")
      "fetched_at" -> one shared UTC timestamp for the whole backfill run
      "session_note" (top-level, additive, only on holiday Fridays):
                     "Friday holiday; bars from <actual date>"
  * Closes are split/dividend-adjusted (yfinance auto_adjust=True), rounded
    to 4dp by snapshot._normalize_block; volume int or None (never invented).
  * "missing" is REQUIRED: a ticker with no bar in the Monday..Friday week
    (pre-IPO, halted, delisted) is ABSENT from "series" (no nulls) and listed
    in "missing" with reason "no bar for week of <date> (likely pre-IPO or
    not trading)". No interpolation, ever.

CLI:
  python backfill_weekly.py --out <data-root> [--start 2024-08-09]
         [--end 2026-08-07] [--only TICKER,TICKER] [--dry-run] [--force]

  --out is the DATA ROOT; files land at <out>/weekly/<date>.json (matching
  snapshot.write_weekly semantics). For the canonical run:
  --out C:\\Users\\alexa\\Documents\\kimi\\workspace\\truth_layer\\sweep\\data

  Existing files are never overwritten without --force (append-only
  discipline, even for the backfill). Skipped files still feed the summary
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

# Repo root = MarketStockPicker/ (this file lives in scan_pipeline/scripts/).
_PIPELINE_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, _PIPELINE_ROOT)

from scan_pipeline import snapshot          # noqa: E402
from scan_pipeline import snapshot_macro    # noqa: E402

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
    'last trading day <= Friday' rule) and ends the day after the last
    Friday. Tickers that never return data get empty histories and land in
    'missing' for every week -- never fabricated."""
    start_iso = (first_friday - timedelta(days=10)).isoformat()
    end_iso = (last_friday + timedelta(days=1)).isoformat()
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
                    out_dir: str) -> dict:
    """Slice one Friday, fetch specials, write via snapshot.write_weekly,
    then stamp backfill identity (source / fetched_at / session_note)."""
    monday = friday - timedelta(days=4)
    bars: dict = {}
    missing: list = []
    actual_dates = set()
    for t in tickers:
        bar, actual = slice_week(history.get(t, ([], [], [])),
                                 monday, friday)
        if bar is None:
            missing.append({"ticker": t,
                            "reason": MISSING_REASON % friday.isoformat()})
        else:
            bars[t] = bar
            actual_dates.add(actual)

    session_note = None
    if actual_dates and friday not in actual_dates:
        session_note = ("Friday holiday; bars from %s"
                        % max(actual_dates).isoformat())

    special = snapshot_macro.fetch_special_instruments(friday.isoformat())
    time.sleep(FRIDAY_SLEEP_S)

    path = snapshot.write_weekly(
        friday.isoformat(), {"bars": bars, "missing": missing},
        special, out_dir=out_dir)

    # Backfill identity: write_weekly stamps PROVIDER ("yahoo") and the write
    # clock; restamp with the backfill source and the shared run timestamp so
    # backfilled files are distinguishable from live scans forever.
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    doc["source"] = BACKFILL_SOURCE
    doc["fetched_at"] = RUN_TS
    if session_note:
        doc["session_note"] = session_note
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(snapshot.canonical_json(doc))
    return {"path": path, "doc": doc, "session_note": session_note}


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
                    help="allow overwriting existing weekly files")
    args = ap.parse_args()

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
        log("%d files already exist (%s)"
            % (len(existing),
               "will OVERWRITE (--force)" if args.force else "will SKIP"))
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

    written = skipped = 0
    missing_counts: list = []
    ticker_missing: dict = {t: 0 for t in tickers}
    notes: list = []
    for n, friday in enumerate(fridays, 1):
        path = os.path.join(weekly_dir, friday.isoformat() + ".json")
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
        rec = build_and_write(friday, tickers, history, args.out)
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
    print("SUMMARY: files_written=%d files_skipped=%d fridays=%d "
          "missing_per_file[min=%d median=%d max=%d] "
          "chronic_missing(>50%%)=%d %s"
          % (written, skipped, len(fridays),
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
