# CLAUDE.md - weekly-council-scan

Monday-morning automated scan producing sector wikis, agent picks, a market
synthesis and performance tracking. Multiple agents write here; Kimi handles
cron execution.

## Environment

Windows. The Council's Monday scheduling is external (Kimi's cron), not GitHub
Actions. The workflows are the manual backfill (2026-08-25), CI, the daily
observation of one closed session into `data/daily/` (21:45 UTC weekdays),
and the owner's screen, the Butterfly Net (`screen/daily_screen.py`), run on
weekday evenings after the close for the next session and committed to
`screen/reports/` with a run log in `runs.json` (2026-09-23, evenings since
2026-09-24; see `screen/README.md`). Since 2026-09-30 the owner's scheduled
task `crew-9-butterfly-net` dispatches it at about 5:15 PM ET; GitHub's own
schedules (23:17 UTC, retry 01:43 UTC) start hours late and are the backstop.
It refuses to run while the US session is open.

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

- `PRICE_FEED_UNIVERSE` -- what `data/weekly` and `data/daily` commit.
  `STOCK_UNIVERSE | BACKFILL_44_TICKERS`.
- `STOCK_UNIVERSE` -- what the **engines scan**. Deliberately narrower than the
  feed so Monday fetch time is unchanged; the backfilled names are fed and
  stored but not scanned.
- `SECTOR_FOCUS_110` / `FOCUS_TICKERS` -- the **analysis universe**, the Seven
  Orbs watchlist, cap-descending, for the heatmap's sector baskets. The
  engines do not scan it; Council v2 moves them onto the 111 once the Testing
  Room has checked each job. Authoritative copy lives in
  sector-regime-heatmap at `config/watchlist_110.csv`; this copy is a
  transcription and the CSV wins any disagreement.
- `get_sector` (`scan_pipeline/utils/data_utils.py`) reads `SECTOR_MAP`, which
  covers `STOCK_UNIVERSE` in full, and for any other name folds the Council
  CSV's GICS label onto the eight engine buckets via `GICS_FOLD`
  (2026-09-22). A no-op on the live path; it exists so a widened universe
  never lands 46 names in one "Unknown" bucket that can win Ophelia's
  rotation and abort a Monday on sanity check 4. `tests/test_sectors.py` pins it.

Counts are asserted in code and by `truth_check --config`, not written here.
A number in prose is a third copy of a fact and it drifts.

**Restored 2026-09-12 after a two-week drift.** `009f7f6` added the focus set
and two asserts; `7cf7025` deleted both and left the feed at 277 while this
file kept describing 321. The assert that broke was
`FOCUS_TICKERS <= STOCK_UNIVERSE`, which cannot hold once the focus set is
wider than the engine set -- so the block was deleted rather than the bound
corrected. It is now bound against `PRICE_FEED_UNIVERSE`, which is the set it
always meant. Nothing caught it at the time because this repo had no
config-drift gate; `truth_check --config` is that gate now.

**Do not shrink the feed to the focus set.** It would drop 211 tickers
including 22 actively held or traded. C, MRK and SIDU are in the current Arena
book at 56% of it by weight, and Arena scores entry and exit against these
prices. A feed costs one call per name and must never be narrower than the
positions scored against it.

## The daily observation feed

`data/daily/<session>.json`, DATA_FEED.md sec.4. Written by
`scripts/daily_observe.py`, scheduled weekdays 21:45 UTC.

The weekly files commit Friday closes because that is the cadence the council
reads. The bars behind them were never weekly -- `fetch_weekly_bars` pulls
daily bars over a ranged window and keeps one. This feed keeps the rest.

- **It is an observation, not a forecast.** It scores nothing. The heatmap's
  two judgment components have no daily source; a daily file carrying them
  would be inventing them.
- **SPY is the session witness.** No SPY bar dated exactly `as_of` and the run
  refuses with exit 2 -- the date was not a session, or it has not settled. A
  half-formed session is indistinguishable from a settled one once committed.
  Holidays produce no file; 2026-09-07 is absent by design.
- **Never splice daily and weekly files into one calculation.** They carry
  different adjustment anchors and the gap is real: on 2026-08-28 the two
  agree on SPY to the penny and disagree ~1% across 57 dividend payers, and
  50% on APH. Treat `data/daily/` as its own panel.
- Bootstrap a range with `--since`: one ranged download, so every session in
  it shares one anchor. Per-date runs would give each file its own.

## Known data defects

- **The mirror backfill script.** `scan_pipeline/scripts/backfill_weekly.py`
  is a faithful copy of Kimi's runner and has diverged from
  `scripts/backfill_weekly.py`: it has no `--merge`, so the only way it can add
  tickers to an existing week is the `--only ... --force` combination that
  emptied the panel. Nothing invokes it and a test fails if anything starts to.
  Use `scripts/backfill_weekly.py`. The real fix is upstream in the runner.
- **AVB 2026-08-21**: close 65.9005 behind volume 0, corrected. It was in
  `series` and not in `missing`, so it flowed through as real. Three
  independent sources agree it is junk. `metric_definitions.md` already
  required flagging zero-volume records; this one got past.
- **Corporate actions the panel straddles.** Adjusted closes are anchored to
  the FETCH date, so a split between two fetches lands in the panel as a step:
  the earlier file is on the pre-split basis, the later one is not, and the
  week-over-week return across them is the ratio rather than a market move.
  Two are known: **APH** (2:1, 2026-09-03) and **MNST** (2:1, 2026-08-11).
  Neither is in the 110-name analysis set, so heatmap sector scores are
  untouched -- `market_state` and Arena, which derive over the full universe,
  are not.

  **The panel is not edited for these.** A weekly file is an observation and
  `2026-08-28.json` correctly records APH as it stood that day; rewriting it
  onto the post-split basis would falsify the log to flatter a consumer. Both
  are recorded in `macro/known_corporate_actions.json` with that reasoning.

  `truth_check --splits` finds them. It scans every consecutive pair in both
  panels for moves matching a split ratio, then **verifies each against the
  provider's split history** -- a ratio alone is not evidence, because a 3:2
  split is -33.3% and so is an ordinary crash. The first draft flagged SOUN,
  IONQ and QUBT for the same week of 2025-01-10, which was the quantum-stock
  selloff, not three simultaneous splits. Of 12 ratio candidates in the live
  panel, 2 are real. A failed fetch reports UNVERIFIED, never "no split".
- **`US2Y` through 2026-10-02 is a futures mark, not the 2-year.** The feed
  committed Yahoo's `2YY=F` under that key, on the belief that a front-month
  yield future tracks the cash 2-year within a few bp. Nobody trades the
  contract (volume 0 on 51 of 54 sessions, open interest 4), so the mark sat
  still for weeks and met the cash yield only at month-end settlement. 24 of
  the 113 weeks are more than 10 bp from the Treasury 2-year, the worst -36 bp
  on 2026-09-18, and `market_state` carried a 2s10s 20 to 36 bp too steep for
  three weeks (#110, #119, #129). Yahoo has no cash 2-year, so since
  2026-10-04 `US2Y` comes from the Treasury par yield curve and the future is
  kept as `US2Y_FUT`. Treasury is the one exception to "one provider";
  `DATA_FEED.md` sec.1a and its Provider section carry the reasoning.

  **The old files are not edited and not corrected.** They are right about
  what they observed, and 113 corrections would be 113 full copies of the
  panel behind the correction trap. What changed is the reader. A weekly
  file's `US2Y` is the Treasury 2-year only where `provenance.rates.US2Y`
  names `treasury`; for every other week the value is in
  `data/us2y_treasury.json`. `snapshot.cash_2y_series` is that rule. A week
  with neither derives as null with a reason, never from `US2Y_FUT`.

  `truth_check --feed` fails when `market_state.json` shows a 2-year that is
  not the Treasury 2-year for its week, or anything but null where none
  exists; when its weekly change or percentile is null although the values
  are in the tree; and when `data/us2y_treasury.json` is missing from a tree
  that derived a `market_state.json`. It warns for any week with no Treasury
  2-year. All of these are what a Friday looks like on a runner that is
  behind: the writer is the runner's copy of `scan_pipeline/` against the
  runner's copy of `data/`, both synced by hand, and the weekly job does not
  write the history file.

  **A missing row is not a holiday.** The fetch takes the row dated `as_of`
  or lists `US2Y` in `missing`; it stands another day in only when a later
  row proves Treasury skipped that one, and on the night there is never a
  later row. So a late Treasury post and a holiday Friday both leave a gap,
  and the gap is filled afterwards:

      python scripts/backfill_us2y.py

  It adds weeks from Treasury's archive, never rewrites one, and re-derives
  `market_state.json`, which the new entry makes stale. For a holiday Friday
  run it after the next session. `--check` compares what is committed against
  the archive. To regenerate `market_state.json` through the whole chain for
  any other reason (a change to the deriver, say):

      python scripts/rederive_market_state.py
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

## dad-kit/

A starter kit for the owner's dad's Claude account (2026-10-03): two
claude.ai skills, project instructions, his guide, and `build_kit.py`, which
builds the upload zips and three workbooks into `dad-kit/dist/` (not
committed). He mostly runs a golf league, so the golf skill leads with it. Not part of the pipeline; nothing in it touches `data/`. ASCII
throughout, and `tests/test_dad_kit.py` checks each skill against claude.ai's
upload rules.

The stock skill reads this repo's public files by raw GitHub URL when he
asks: `README.md`, `wiki/synthesis.md`, `wiki/economic-calendar.md`,
`scoreboard.md`, `screen/reports/latest.html` and `runs.json`. Renaming or
moving one breaks his skill silently; update
`dad-kit/skills/stock-research/references/council-and-market.md` with it.

## Do not

- Splice external price data into `data/weekly/`. The supplied
  `Watchlist_110_Weekly_History_1Year.xlsx` is price-only where this panel is
  total-return adjusted (`yfinance auto_adjust=True`). It is useful as an
  independent cross-check and unusable as a source.
- Edit a committed weekly file.
- Invent a close to fill a gap. Use `missing` with a reason.
- Read `rates.US2Y` straight from a weekly file, or let `US2Y_FUT` stand in
  for it. Go through `snapshot.cash_2y_series`; a gap stays a gap.
