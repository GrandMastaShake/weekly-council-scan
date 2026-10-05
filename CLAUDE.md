# CLAUDE.md - weekly-council-scan

Monday-morning automated scan producing sector wikis, agent picks, a market
synthesis and performance tracking. Multiple agents write here; Kimi handles
cron execution.

## Environment

Windows. The Council's Monday scheduling is external (Kimi's cron), not GitHub
Actions. The workflows are the manual backfill (2026-08-25), CI, the daily
observation of one closed session into `data/daily/` (21:45 UTC weekdays,
tried again at 09:15 UTC the next morning),
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
- **An instrument close is the bar dated `as_of`, a stand-in the file names,
  or `missing`.** Never "the last bar on or before", and never a futures or
  dollar-index bar read before the exchange settled it. `DATA_FEED.md` sec.1b.
- **No SPY bar, no weekly file.** The series are one session's: SPY's bar
  dated `as_of`, or, only once a later SPY bar proves the Friday was skipped,
  the last session of that week, named in `session_note`. With neither,
  `write_weekly` raises `NoSessionWitness` and writes nothing. Never an empty
  `series`, never an unproven Thursday. `DATA_FEED.md` sec.1c.

## The correction trap

A correction is a *full copy* of its base, so it is a snapshot and goes stale
the moment the base changes. `backfill_weekly.py` writes new tickers into the
base file, but readers prefer the correction -- so backfilled names become
silently invisible for that week, permanently, with no error anywhere.

**After any backfill touching a corrected week, run:**

    python scripts/rebuild_corrections.py

Two weeks are corrected. `2026-08-21.corrected.json` drops AVB and should
carry ~330 series entries; if it still says 286, this did not run.
`2026-08-28.corrected.json` restates three instrument closes and records what
they replaced in `restated`. The script re-applies each recorded edit only
while the base still holds what the correction replaced -- a dropped ticker
still at volume 0, a restated close still at its old value. Otherwise it
prints ABORT, leaves the file alone and exits 1, so the backfill workflow
stops before its commit step. (It used to exit 0.)

`tests/test_instrument_sessions.py` fails if any committed correction is not
what a rebuild would write, so a stale one no longer gets past CI.

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
`scripts/daily_observe.py`, scheduled weekdays 21:45 UTC with a second
attempt at 09:15 UTC the next morning (UTC Tue-Sat) for the same session.

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
  it shares one anchor. Per-date runs would give each file its own. It skips
  sessions already on file and never runs past the last close.
- **The session is picked by the US/Eastern clock, never the runner's UTC
  date.** The default is the latest weekday whose 16:00 ET close has passed.
  GitHub starts the evening schedule hours late; read off UTC, a start after
  00:00 asked for a date that had not traded and never looked at the session
  that had closed. A date still in session is refused before any fetch: SPY
  has a bar for it all day, and it is the forming one.
- **The provider blanks the just-closed bar for an hour or more each
  evening.** From 00:00 UTC (20:00 ET in summer, the end of the post-market
  session) until its end-of-day roll the row is there with a NULL close: on
  this feed the bar was served through 23:59:53 UTC, gone at 00:10 and 00:45,
  back by 01:38. Which clock the window follows in winter is not known.
  yfinance turns it into "no bar" silently, so the gate refuses -- correctly
  -- and the refusal now says which it was: not a session, not settled, or no
  answer. It is not the `end` date; the provider appends its newest row
  whatever the window says. The morning attempt exists for this.
- **A refusal is green by design, so it can never be the alarm.** The alarm
  is the workflow's last step: `daily_observe.py --audit` asks the witness
  which sessions exist and exits 1 when a settled one, other than the newest,
  has no file. It names the `--since` command that recovers them. Offline,
  `truth_check --feed` WARNs when the newest daily file is two or more
  weekdays old; it knows no holidays, so it never fails.
- **Neither attempt is late enough for the futures.** WTI, GOLD, SILVER, DXY
  and US2Y_FUT trade past the cash close and are not read before 13:00 UTC on
  the day after the session (Known data defects, below). 21:45 UTC and 09:15
  UTC are both earlier, so every daily file written since 2026-10-05 lists
  those five in `missing` with the reason, whichever attempt wrote it. US10Y
  and VIX are final by evening and are read. The eight files from 2026-09-11
  to 2026-09-23 hold evening quotes for the five. The heatmap's daily tape
  reads `fx.DXY` and shows it missing meanwhile. An attempt after 13:00 UTC,
  with no evening write ahead of it, would bring the five back. Whether 09:15
  UTC is in fact late enough is not known: no committed read falls between
  02:58 and 13:07 UTC.

Eight sessions were lost between 2026-09-21 and 2026-10-02 with every run
green: six to the UTC date, two (the Fridays) to the null-close window, each
refused once with nothing asking again.

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
  untouched. Nothing else in this repo derives across them either:
  `market_state` reads only the four index and twelve sector ETFs from
  `series`, and Arena and the Tracker fetch their own bars. (Until 2026-10-05
  this said both derive over the full universe. Neither does.) A reader over
  every name would hit the step: `panel_source.py` when it is on, or a chart.

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
- **Instrument closes from the wrong session, or read before they settled.**
  Nothing in a file said which session a `rates` / `vol` / `commodities` /
  `fx` close was read from. The writer took "the last bar on or before" the
  date and its note was dropped before the file was written. An audit of
  every committed close against the provider (2026-10-05) found 151 of the
  789 in the weekly files are not the provider's close for the file's date:

  - **2026-08-28 holds Thursday's US10Y, VIX and DXY** (4.672 / 14.51 / 99.16
    for 4.72 / 14.43 / 99.70). Fetched Saturday 14:10 UTC. Most likely Yahoo
    had no usable Friday bar for its index symbols yet and the fallback took
    Thursday's; a Friday bar carrying Thursday's values would have left the
    same file, and it cannot say which. Corrected, owner sign-off 2026-10-05.
  - **Three Friday-evening files hold quotes, not settlements**: WTI, GOLD,
    SILVER, DXY and the 2-year future in 2026-09-11, 09-18 and 09-25. The
    2026-09-18 WTI is the 95.47 of #110: the November contract's last trade,
    where the settled front month was 100.30. The eight daily files from the
    evening job are the same or worse; on a weekday the bar dated today at
    19:40 ET is the *next* session's first trades.
  - **28 holiday stand-ins are unmarked** per instrument, and 2025-07-04 has
    WTI and SILVER from a July 4 holiday bar beside rates from July 3.
  - **VIX is absent from 2025-03-14 and 2026-03-13.** The fetch window opened
    on the Sunday the clocks went forward, and Yahoo returns nothing at all
    for `^VIX` when it does. Friday minus five days is that Sunday once a year.

  **None of those files is edited**, and only 2026-08-28 is corrected.
  `macro/instrument_audit.json` lists every finding with the session it
  actually is, a cause and what was decided. Re-run it with

      python scripts/audit_instruments.py

  which prints only what is new, changed or gone against that list (network
  and yfinance needed; the tests need neither). Give anything new a cause in
  the JSON by hand, then `--write`.

  The writer now follows the Treasury path's rules: the bar dated `as_of` or
  `missing`; a stand-in only when a later bar proves the date was skipped,
  recorded as `provenance.<block>.<ticker>.observed`; and the five
  late-settling instruments are not read before 13:00 UTC on the day after
  `as_of`. None of that catches a bar dated `as_of` with the wrong day's
  values in it; the audit is what finds that, so run it. `truth_check --feed` fails a file dated 2026-10-05 or later that
  carries one read earlier, which is what a runner still on the old writer
  produces.

  **So the weekly job has to run on Saturday after 13:00 UTC**, not Friday at
  9:13 PM ET where it has been since 2026-09-12. On Friday night the new
  writer commits a file with no commodities and no dollar index, and a weekly
  file cannot be completed afterwards. The schedule and the runner's copy of
  `scan_pipeline/` are both outside this repo and are changed by hand.

  To restate a close in a file that is already committed, with sign-off:

      python scripts/restate_instruments.py --date <as_of> \
          --instrument rates.US10Y --reason "..."

  It writes `<date>.corrected.json` through the writer's own fetch, records
  what it replaced, and labels the replacement. Never by hand: an unrecorded
  change is one the next rebuild erases and the feed gate refuses.
- **Equity closes: the backfill writer takes the last bar on or before the
  Friday.** `backfill_weekly.py::slice_week` keeps a ticker's last bar inside
  the Mon..Fri week and can mark nothing per ticker, so a name with no Friday
  bar -- halted, delisted mid-week, a gap at the provider -- carries an
  earlier session under the Friday date. It wrote the 105 backfilled files
  and every name merged in afterwards. An audit of every committed equity bar
  against the provider (2026-10-05) found it happened once: **EA in
  2026-08-07.json is its close of Tuesday 2026-08-04**, the last session
  before it was taken private, on volume 0. Of the other backfilled and
  merged bars, 34,774 are the session their file names (the Thursday, in the
  five holiday files) and 205 cannot be checked: the provider keeps only the
  last bar of a delisted symbol (AVB 104 weeks, EA 101).

  **A committed equity close cannot be compared with a fresh fetch.** It is
  adjusted to its fetch date, so it differs for every name that has paid a
  dividend or split since. `scripts/audit_series.py` tells the session from
  the volume, which is never dividend-adjusted, and from the close once the
  provider's own factor for the fetch date (its Adj Close over its Close) is
  divided out. Re-run it with

      python scripts/audit_series.py

  It prints only what is new, changed or gone against
  `macro/series_audit.json`, and how much it could have found: with the
  session before it put in place of each bar that passed, that session is
  named every time (37,947 of 37,947). Give anything new a cause in the JSON
  by hand, then `--write`. Network and yfinance needed; the tests need
  neither. EQR is audited as VMRK, which carries its history.

  The same audit covers the Friday job's files, and one of them this repo's
  writer did not write. **2026-08-28.json took every equity close from the
  provider's `1wk` bar**: a one-off script on the runner, on the Saturday the
  provider's daily closes were null. For 330 names that is the Friday close.
  AVB's is 68.14 from Monday 2026-08-24, null volume, the successor's price
  under a dead symbol, and `2026-08-28.corrected.json` carries it too. Not
  corrected.

  **None of this reached a derived number.** `market_state` reads sixteen
  names from `series` (SPY, QQQ, DIA, IWM, the twelve sector ETFs) and every
  one of their bars is right. The heatmap never scored AVB or EA. Arena and
  the Tracker fetch their own bars (`scripts/arena_ingest.py`,
  `portfolio/tracker.py`) and do not read `data/weekly`.

  **Not fixed.** `slice_week` is unchanged, in both copies of the script, so
  the next backfill or `--merge` that meets such a name does it again. How
  that bar should be recorded -- `missing`, as the Friday job does, or a
  per-ticker `observed` -- is not decided (`DATA_FEED.md` sec.1b, "The equity
  series"). Run the audit after any backfill.
- **The weekly writer on a market holiday.** `fetch_weekly_bars` kept only
  bars dated the Friday, so run for a holiday it committed `series: {}`:
  every ticker in `missing`, no `session_note`, and `truth_check --feed`
  passed it (run for 2026-07-03 on 2026-10-05). It never happened in
  production. The five holiday weeks in the panel came from the backfill, and
  the weekly job, running since 2026-08-14, has not met a holiday. The next
  are 2026-12-25 and 2027-01-01, Fridays running.

  Since 2026-10-06 SPY is the witness for the whole file, under the rule the
  Treasury and instrument paths already follow. Its bar dated the Friday is
  the session. With no such bar and none after it, nothing is written: a
  missing bar is not evidence of a holiday, and on Saturday 2026-08-29 the
  provider's closes for an ordinary Friday were all null. Once a later SPY
  bar proves the Friday was skipped, the last session of that week stands in
  for every ticker and the file says so: `"Friday holiday; bars from
  <date>"`, the note the backfilled holiday weeks carry and
  `audit_series.py` reads.

  **So a holiday week lands a week late, on purpose.** The job runs on the
  Saturday and SPY's next bar is Monday's, so the proof is never there on the
  night. Writing the equities at once on the strength of a calendar would
  lose the instruments for good: they cannot stand in that night, and a
  weekly file cannot be completed afterwards. Written by the next run the
  file is whole, each instrument with its `observed` date. Until then every
  reader has last week's `market_state.json`, dated as what it is.

  **A refusal is green, so the panel is what gets asked.** The weekly job
  writes every Friday `snapshot.unwritten_fridays` lists, oldest first, and
  stops at the first one refused; after writing more than one it derives
  through the chain (`snapshot.write_market_state_chain`). `truth_check
  --feed` fails an empty `series`, a new file with no SPY bar, a
  `session_note` it cannot read a session out of, and a Friday missing
  between two weekly files; it warns from the Sunday while the newest Friday
  is still owed. A hole matters more than it looks: `market_state` nulls the
  windows that reach it, but sector-regime-heatmap counts weeks by position
  and scores the week after a hole over two weeks, calling it one.

  `scripts/backfill_weekly.py` called a week a holiday whenever no ticker had
  a Friday bar, which is every Friday on the night. It asks the witness under
  the same rule now and exits 2 on a week it cannot write, and `--only` can no
  longer start a week. That is how `2024-08-09.json` came to hold no index
  or sector ETF at all, SPY among them, with none listed in `missing`. Not
  edited; the gate warns, and a `--merge` backfill of those names adds them.

  Both of these are outside this repo and changed by hand: the runner's copy
  of `scan_pipeline/`, which writes the empty file until it is synced (the
  gate stops it), and the job's prompt, which asks for the most recent Friday
  only and so needs the catch-up put into it.
- **GOLD is two contract months, and nothing in a file says which.** WTI,
  GOLD and SILVER are Yahoo's continuous symbols. Between 2026-09-05 and
  2026-10-03 Yahoo rebuilt `GC=F` from the nearest-expiry contract onto the
  active one, for its whole history. The panel's gold is therefore the old
  basis through 2026-09-04 (2026-08-28 excepted) and the new one from
  2026-10-02: 107 of 113 weeks no longer match the provider, by up to 59.00
  or 1.7%, and any `market_state` GOLD change that spans the boundary
  includes that spread. Committed volume is the only tell (median 491
  contracts against 185,701). Not corrected -- neither series is wrong and it
  would be 104 full copies of the panel -- and not fixed: which contract and
  which roll rule is a decision nobody has made. `SI=F` and `CL=F` have the
  same weakness in smaller doses; the audit list has the cases.
- **SPCX** listed 2026-06-12. It correctly appears in `missing` for every
  earlier week. Not a failure.
- Holiday weeks use the nominal Friday as the filename with `session_note`
  recording the actual session. That note is about the equity series, its
  form is fixed, and the weekly job writes one only with proof (above). Which
  session each instrument is from is in `provenance.<block>` for files
  written since 2026-10-05, and in `macro/instrument_audit.json` for the five
  written before.

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

**A week is written only with its session witness.** A Friday SPY has no bar
for is refused until a later SPY bar proves it was a holiday, and the run
exits 2, which stops the workflow before its commit step. `--only` adds names
to a week that exists; it cannot start one (`DATA_FEED.md` sec.1c).

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
- Run the weekly feed job before 13:00 UTC on the Saturday, or bring back
  "the last bar on or before" for an instrument with no bar on the date.
- Change a close in a correction by hand. Use `restate_instruments.py`, so
  the change is recorded in `restated` and survives the next rebuild.
- Call a committed equity close wrong because a fresh fetch disagrees. It is
  adjusted to its fetch date. `scripts/audit_series.py` is the comparison.
- Build a weekly file the writer refused: by hand, from `1wk` bars, or from
  Thursday's. No file is the right outcome of that run, and the next one
  writes it.
- Step over a week that was refused. Write the Fridays
  `snapshot.unwritten_fridays` lists, oldest first, before the newest.
