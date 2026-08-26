# CLAUDE.md - weekly-council-scan

Monday-morning automated scan producing sector wikis, agent picks, a market
synthesis and performance tracking. Multiple agents write here; Kimi handles
cron execution.

## Environment

Windows. ASCII in anything new. Scheduling is external (Kimi's cron), not
GitHub Actions -- the only workflow is the manual backfill added 2026-08-25.

## The data contract

`DATA_FEED.md` governs `data/weekly/`. Read it before touching anything there.
The parts that get violated:

- **Weekly files are append-only. Never edit one.** If a provider restates,
  write `<date>.corrected.json` with the same shape plus `corrects` and
  `reason`. Readers prefer the correction; the original stays.
- **`missing` is required and never empty-by-omission.** A ticker that could
  not be fetched is listed with a reason. A silently absent ticker is
  indistinguishable from one that never existed, and that ambiguity is exactly
  what the agents fill in from priors.
- **`fetched_at` is UTC and real.** It is also the adjustment anchor: adjusted
  closes are back-adjusted to the fetch date, so downstream consumers use it to
  detect stale splices.
- **Closes only.** No intraday, no derived fields. The file is an observation.

## The correction trap

A correction is a *full copy* of its base, so it is a snapshot and goes stale
the moment the base changes. `backfill_weekly.py` writes new tickers into the
base file, but readers prefer the correction -- so backfilled names become
silently invisible for that week, permanently, with no error anywhere.

**After any backfill touching a corrected week, run:**

    python scripts/rebuild_corrections.py

`2026-08-21.corrected.json` should carry ~330 series entries. If it still says
286, this did not run. The script aborts rather than guessing if a dropped
ticker no longer has volume 0, since that means the provider restated.

## Universe vs focus set

`scan_pipeline/config/tickers.py`:

- `STOCK_UNIVERSE` (321) -- the **price feed**. Deliberately wide.
- `SECTOR_FOCUS_110` -- the **analysis universe**, the Seven Orbs watchlist,
  cap-descending. Authoritative copy lives in sector-regime-heatmap at
  `config/watchlist_110.csv`; keep them in sync.

**Do not shrink the feed to the focus set.** It would drop 211 tickers
including 22 actively held or traded. C, MRK and SIDU are in the current Arena
book at 56% of it by weight, and Arena scores entry and exit against these
prices. A feed costs one call per name and must never be narrower than the
positions scored against it.

## Known data defects

- **AVB 2026-08-21**: close 65.9005 behind volume 0, corrected. It was in
  `series` and not in `missing`, so it flowed through as real. Three
  independent sources agree it is junk. `metric_definitions.md` already
  required flagging zero-volume records; this one got past.
- **SPCX** listed 2026-06-12. It correctly appears in `missing` for every
  earlier week. Not a failure.
- Holiday weeks use the nominal Friday as the filename with `session_note`
  recording the actual session.

## The backfill

Actions -> "Backfill weekly panel". Manual dispatch, defaults to `dry_run`
because it rewrites committed files with `--force`. It chains
`rebuild_corrections.py` and `truth_check.py` and prints series counts before
and after.

The 44 names added 2026-08-25 still need filling. Command and rationale in
`BACKFILL_44.md`.

## Do not

- Splice external price data into `data/weekly/`. The supplied
  `Watchlist_110_Weekly_History_1Year.xlsx` is price-only where this panel is
  total-return adjusted (`yfinance auto_adjust=True`). It is useful as an
  independent cross-check and unusable as a source.
- Edit a committed weekly file.
- Invent a close to fill a gap. Use `missing` with a reason.
