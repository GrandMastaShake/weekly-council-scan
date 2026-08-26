# CLAUDE.md - weekly-council-scan

Monday-morning automated scan producing sector wikis, agent picks, a market
synthesis and performance tracking. Multiple agents write here; Kimi handles
cron execution.

## Environment

Windows. Scheduling is external (Kimi's cron), not GitHub Actions -- the only
workflow is the manual backfill added 2026-08-25.

**ASCII in anything new, with one exception: human-facing markdown.** The
README may use symbols; `scripts/render_heatmap_dashboard.py` emits them. Data
under `data/weekly/` stays strictly ASCII -- `truth_check.py --feed` decodes
every weekly file as ASCII and fails otherwise, because a content hash has to
be byte-identical on Windows and in CI. All file I/O stays explicit
`encoding="utf-8"`.

The README heatmap chart is aligned by padding, so everything inside its fenced
block must be single-width. Emoji are double-width and shear the bars; they
belong in the markdown table.

## Before anything

    pip install -r requirements-dev.txt
    python -m pytest -q                          # the whole suite, green
    python scripts/truth_check.py --repo . --feed

CI runs all three on every push and PR, plus a panel-regression check that
fails if any weekly file lost series against the previous commit. The suite
needs no network: `tests/conftest.py` stubs the market-data provider, because
a test suite that needs a provider to run is a test suite that does not get
run.

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

- **The mirror backfill script.** `scan_pipeline/scripts/backfill_weekly.py`
  is a faithful copy of Kimi's runner and has diverged from
  `scripts/backfill_weekly.py`: it has no `--merge`, so the only way it can add
  tickers to an existing week is the `--only ... --force` combination that
  emptied the panel. Nothing invokes it and a test fails if anything starts to.
  Use `scripts/backfill_weekly.py`. The real fix is upstream in the runner --
  `RUNNER_BACKFILL_FIX.md` is the write-up to send them.
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
because it writes committed files. It chains `rebuild_corrections.py`,
`panel_guard.py --compare` and `truth_check.py --repo . --feed`, and any of the
three failing stops the run before the commit step.

**Named tickers are ADDED with `--merge`, never `--force`.** `--force` writes a
whole file from the ticker set it was given, so with `--only` it deletes every
other series: on 2026-08-26 that emptied 107 files, 287 series down to 44, and
the job reported success. The script refuses that combination now. `--force` is
for a full-universe rewrite and nothing else.

A merged week carries two adjustment anchors -- the names added later were
fetched later -- so it records them per series in `provenance.series` rather
than restamping one timestamp over two bases. See `DATA_FEED.md` sec.1.

The 44 names were backfilled 2026-08-26: the panel is 35,571 series, 332 a
week, corrections at 330. Rationale and the corrected commands are in
`BACKFILL_44.md`.

## Do not

- Splice external price data into `data/weekly/`. The supplied
  `Watchlist_110_Weekly_History_1Year.xlsx` is price-only where this panel is
  total-return adjusted (`yfinance auto_adjust=True`). It is useful as an
  independent cross-check and unusable as a source.
- Edit a committed weekly file.
- Invent a close to fill a gap. Use `missing` with a reason.
