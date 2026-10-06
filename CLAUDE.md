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

CI runs all three on every push and PR, plus the panel check:
`scripts/panel_guard.py --against <commit>` fails when a file of
`data/weekly` or `data/daily` no longer holds what it held -- a file or a bar
gone, a bar changed, a label or a file stamp changed ("The backfill", below,
has the rule). A pull request is compared with its base and a push with the
tip it replaced, so every commit of a push is covered and not only the last.
New weeks and new names pass. The step runs whether or not the tests before
it passed: a push is compared once, by its own run, and the next push starts
from the new tip. On 2026-09-25 the push of that week's file failed at Tests
and the panel step was skipped with the feed gate; nothing came back for it.

Three limits. CI does not run on what a workflow pushes (a push made with the
workflow token starts none), so the backfill and the daily job each run the
guard themselves before they commit. A run that is cancelled, or never
starts, compares nothing, and no later run makes up for it. And `main` is not
protected: a red run reports, it does not block.

The suite needs no network: `tests/conftest.py` stubs the market-data
provider, because a test suite that needs a provider to run is a test suite
that does not get run. `tests/test_panel_guard.py` runs the workflow steps
that call the guard under bash (on Windows, the one that ships with Git) and
skips those tests where there is none.

**Do not run the suite from a git hook or `git rebase --exec` and trust what
git puts in the environment.** There git exports `GIT_DIR`, and in a linked
worktree no work tree with it. Several tests build throwaway repositories
with `git init`, `git add -A` and `git commit`; with `GIT_DIR` inherited they
did that to the repository being rebased, and `panel_guard --against` read
the wrong tree and passed having compared nothing. `conftest.py` and the
guard both drop those variables now, and a test fails if either stops.

## The data contract

`DATA_FEED.md` governs `data/weekly/`. Read it before touching anything there.
The parts that get violated:

- **Weekly files are append-only. Never edit one.** If a provider restates,
  write `<date>.corrected.json` with the same shape plus `corrects` and
  `reason`. Readers prefer the correction; the original stays. The writer
  will not write a week a second time: `write_weekly` raises `WeekOnFile`.
- **`missing` is required and never empty-by-omission.** A ticker that could
  not be fetched is listed with a reason. A silently absent ticker is
  indistinguishable from one that never existed, and that ambiguity is exactly
  what the agents fill in from priors. `truth_check --feed` warns where the
  panel itself can tell: a week with neither a bar nor a `missing` entry for
  an index or sector ETF, or for a name an earlier and a later week both
  carry. And it fails a `missing` that is not a list of `{"ticker",
  "reason"}` entries, both strings that say something (2026-10-06), in every
  weekly and daily file. An entry with no reason records nothing and
  accounts for no name: the checks that ask for a bar or an entry read it as
  no entry, so a name typed in to get past them fails under its own line and
  under theirs. The FAIL stops whatever ran the gate, the daily job's commits
  included, and little clears it once it is on main (`DATA_FEED.md` sec.1).
  It is stopped before the push.
- **`fetched_at` is UTC and real.** It is also the adjustment anchor: adjusted
  closes are back-adjusted to the fetch date, so downstream consumers use it to
  detect stale splices.
- **Closes only.** No intraday, no derived fields. The file is an observation.
- **An instrument close is the bar dated `as_of`, a stand-in the file names,
  or `missing`.** Never "the last bar on or before", and never a futures or
  dollar-index bar read before the exchange settled it. `DATA_FEED.md` sec.1b.
- **A commodity close names its contract month**, in
  `provenance.commodities`. One with no label is a continuous symbol's bar
  of a month nobody named, which is every file through 2026-10-02.
  `DATA_FEED.md` sec.1d.
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
carry one series fewer than its base: 336 since the two merges of 2026-10-06
(BTC and GLD, then BNY, MRSH, DOC and VMRK). If it says 332, 330, or still
286, this did not run.
`2026-08-28.corrected.json` restates three instrument closes and records what
they replaced in `restated`. The script re-applies each recorded edit only
while the base still holds what the correction replaced -- a dropped ticker
still at volume 0, a restated close still at its old value. Otherwise it
prints ABORT, leaves the file alone and exits 1, so the backfill workflow
stops before its commit step. (It used to exit 0.)

`tests/test_instrument_sessions.py` fails if any committed correction is not
what a rebuild would write, so a stale one no longer gets past CI.

**A corrected week is two files and one week.** A reader that lists
`data/weekly/*.json` reads it twice. `scan_pipeline/panel_source.py` did
until 2026-10-06: every name got a second row for 2026-08-21 and for
2026-08-28 with its open equal to its close, twelve rows covered ten weeks,
and the AVB bar the first correction drops was read from the base. It is
opt-in (`COUNCIL_SCAN_SOURCE=panel`) and was off, so no book was built on
it. A reader goes through `snapshot._load_weekly_files`: each week once,
from its correction where it has one. `truth_check` spells the same rule
for itself, because its feed checks are pure stdlib and run where there is
no `scan_pipeline/`. The feed gate, the two audits, `panel_guard` and CI's
panel step list every file under its own name on purpose: they check
files, not weeks.

Two things about that reader as it stands. A weekly file it cannot parse
stops it (`PanelUnreadable`), wherever in the panel the file is; it used to
step over one. And **not decided**: a row opens at the last close a name
has, so a name with no bar in a week gets a next row that spans the gap
under a one-week date. The panel holds two, AVB 2026-08-28 and EA
2026-08-07, on names no engine scans.

## Universe vs focus set

`scan_pipeline/config/tickers.py`:

- `PRICE_FEED_UNIVERSE` -- what `data/weekly` and `data/daily` commit, beside
  the sixteen index and sector ETFs the writers add.
  `STOCK_UNIVERSE | BACKFILL_44_TICKERS | COUNCIL_WATCHLIST`.
- `COUNCIL_WATCHLIST` -- the owner's own list, from `council_watchlist.csv`:
  the focus set's stocks and two macro ETFs, BTC (Grayscale Bitcoin Mini
  Trust) and GLD. Council v2's universe, in the feed since 2026-09-21 and not
  yet scanned. BTC and GLD are fed and stored; no engine scores them, and
  `panel_source` keeps both out of the scan set when it is on.
- `snapshot.equity_universe()` -- what both writers **fetch**: the feed and
  the sixteen ETFs, read from the constant. The weekly job, a full backfill
  and `daily_observe.py` all call it.
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

**BTC and GLD were in no weekly file until 2026-10-06.** `8ef6f33` put the
watchlist into `PRICE_FEED_UNIVERSE` on 2026-09-21, "so data accrues from
Friday's build". `daily_observe.py` read the constant and has carried both
since 2026-09-22. `equity_universe()` spelled the union out for itself,
without the watchlist, so the weekly writer never asked for them: neither
`series` nor `missing` in any week, the two built after that date included.
Nothing failed, because `--config` held the newest weekly file to the focus
names and neither is one.

Owner decision 2026-10-05: the weekly feed carries them. The function reads
the constant now. Both names were merged into all 113 weeks with `--merge`
and are stamped in `provenance.series`; each bar is its file's session, and
since neither pays a distribution their closes do not depend on the fetch
date. `--config` fails when `equity_universe()` leaves out a feed name, and
when the newest weekly file has neither a bar nor a `missing` entry for a
name the writer fetches, the sixteen ETFs included.

**So a name added to the feed is merged in the same change.** The gate fails
until the newest week accounts for it, and `backfill_weekly.py --only
<names> --merge` does that: a bar, or a `missing` entry where the provider
has none. Only the newest week is held, so the weeks behind it are a
decision somebody has to make. For four names it was made two weeks late.

**BNY, MRSH and DOC are in every week; VMRK begins 2026-08-21.** The four
joined on 2026-09-21 and had bars from 2026-09-25: neither `series` nor
`missing` in the 111 weeks before. Owner decision 2026-10-06, merged that day
with `--merge`: 338 bars, each stamped in `provenance.series`, each the bar
of its file's session.

- **BNY, MRSH and DOC went into all 111 weeks.** They are BK, MMC and PEAK
  under the symbols they trade by now. The provider serves a renamed
  company's history under the new symbol and at most its last bar under the
  old, and all three were renamed before the panel's first fetch: three
  companies that traded throughout had no bar in 111 weeks under either
  symbol.
- **BK, MMC and PEAK stay in `missing` in those weeks, beside the bars.** The
  entry is true: the symbol was asked for and not served. In the 105 weeks
  the backfill wrote, its reason is a guess and wrong for them: "likely
  pre-IPO or not trading", that writer's one text for a ticker with no bar.
  No file is edited to mend a reason. `DATA_FEED.md` sec.1, "Four renamed
  names", is the record.
- **VMRK went into five more weeks, 2026-08-21 to 2026-09-18, and no
  earlier.** It is EQR, renamed on 2026-08-18 with AVB absorbed, and EQR is
  in `series` under its own key in 105 weeks, 2024-08-16 to 2026-08-14. What
  the provider serves under VMRK for those weeks is the same bar: merged
  into a copy of the panel, it had EQR's volume in all 105 and a close
  0.98824 of EQR's in each, the one dividend gone ex since. In the five
  weeks after, all the panel held for the company was two prints under the
  dead AVB symbol (Known data defects, below).
- **So that history is EQR through 2026-08-14 and VMRK from 2026-08-21**,
  never both in one week, and VMRK is in neither block of the 106 weeks
  before on purpose. `audit_series.SUCCESSORS` is where the join is written
  down.
- **`2024-08-09.json` holds neither key, and stays so.** It was started
  after EQR's symbol died and lists EQR in `missing`. A VMRK bar there would
  be a bar in an earlier and in a later week, and `truth_check --feed`
  would then warn about each of the 105 weeks between, printing the
  `--merge` command that doubles them.
- **Nothing mechanical refuses that merge.** Rehearsed on a copy, a
  `--merge` that named VMRK over all 111 weeks exited 0, and every gate,
  the audit and the suite passed the result. The rule is this entry and the
  "Do not" below.

All four pay dividends, so unlike BTC and GLD their merged closes are the
merge day's and the seam shows. MRSH went ex on 2026-10-01 and VMRK on
2026-10-05, after 2026-09-25.json was fetched: the panel reads MRSH's week to
2026-09-25 as -1.65% where the price moved -2.22%, and VMRK's as +1.67% for
+0.47%. BNY and DOC had no ex-date in between and read true. A reader across
merged and committed weeks resolves the anchor per ticker, as for the 44.
BNY's closes also carry two 0.051 distributions that are not the bank's:
0.08% on the level through 2026-01-16 (`DATA_FEED.md` sec.1).

The runner's copy of `data/weekly` is the old one until it is synced, and it
is synced whole or not at all. Left alone it fails nothing and warns of
nothing new: there the four still begin on 2026-09-25, and the job pushes
only the newest week. One file by itself is another matter. With only
`2024-08-09.json` copied over, BNY, MRSH and DOC have a bar in an earlier
and in a later week, and the gate there warns about the 110 between.

Nobody reads BTC or GLD from a weekly file yet. `market_state` reads the
sixteen ETFs. The heatmap takes both from `data/daily`, as comparison rows
on its daily tape, and its weekly metrics come out byte-identical with and
without them in the panel. They are stored for Council v2.

**What a week without a feed name stops.** On main, CI and the daily job.
The daily job runs `--feed --config` and the whole suite before it commits a
session, so it commits nothing until the week is merged, and the sessions it
skipped are recovered by hand afterwards (the audit step prints the
command). Only the newest week is asked, so the failure also clears by
itself once a later week is whole, with the hole still behind it.

**The weekly job is asked before it pushes (2026-10-06).** Its gate line is
`--feed --derive`, run from a check dir that holds a copy of the runner's
data, `macro/facts.json` and `truth_check.py` fetched fresh. No
`scan_pipeline/` is in it, so `--config` cannot import there, and the
constants within reach are the runner's own. Nothing in that line knew which
names a week should hold: the two builds without BTC and GLD passed it and
were pushed, and so would any week from a runner whose only fault is its
list of names. So the gate carries the names. `EQUITY_UNIVERSE` in
`scripts/truth_check.py` is a copy of `snapshot.equity_universe()`, pinned
by `tests/test_feed_names.py`, which prints the replacement, and by
`--config`. `--feed` asks the newest weekly file for a bar or a `missing`
entry for each.

**A short newest file on the runner is not always a short week.** Its
`data/` is synced by hand, and a name merged into a week on main does not
reach its copy. So the file is either a week the stale writer has just
written, which must not be pushed, or the runner's copy of a week main holds
whole, which must not be rewritten, and the gate cannot see main to tell
which. Both of its lines say to look at main first. **A week that is on main
is never written again to add a name.** And it is a FAIL only for a file
fetched on or after 2026-10-06, the day the rule began: no run that had it
wrote an older one. On that day every weekly file on the runner was older,
committed, and without BTC and GLD, and those only warn.

**What a FAIL there leaves to do.** Not pushed, and not patched: a `missing`
entry is the writer's record that it asked, and is never added by hand. If
main does not hold the week, sync `scan_pipeline/` on the runner, remove the
file from its `data/weekly`, write the week again, and re-derive
`market_state.json` through the chain, because the state the discarded week
left behind is not last week's. A short file left in place is worse than
none: the job takes a week it finds on disk for a committed one, so it is
neither pushed nor rewritten, and the week after it lands on main beside a
hole.

Rehearsed on main's data with the runner's own `2026-10-02.json` as the
newest week, which has neither BTC nor GLD, with a current deriver and no
pandas or yfinance. `--feed --derive` exited 0 on it before and said
nothing. It warns now, because that file was fetched on 2026-10-03; the same
file stamped as written on the 10th exits 1 naming both. The runner as it
stood that day did not get that far: its own line failed on the two history
files it lacked and on the futures mark its deriver still writes under
`US2Y`.

Three things this does not reach. `--derive` is as it was: with no
`--pipeline` it judges with the runner's deriver. The Monday Council's
fallback build (STEP 1d of its task card) is a second writer: the same
calls, into the same `data/`, gated with the same flags. Its card named
`scripts/truth_check.py`, which its workspace does not hold, and no check
dir. That one sentence was clarified on 2026-10-06 (owner sign-off): the
copy of `truth_check.py` it downloads that morning, from a check dir built
as the weekly job builds its own. It is a card, and nothing in this repo
checks that it is followed. And when a name next joins and is merged into
the newest week on main, the runner's copy of that week is short of it: a
Saturday that writes no week fails on the copy until main's replaces it.
The weekly job's prompt and task card were not changed.

**So after any change to the feed, sync `scan_pipeline/` on the runner
before the next Saturday build**, and copy the week the name was merged into
with it: `config/` for a change of names, and `snapshot.py` where it is
behind. Of the feed modules on the runner on 2026-10-06, `tickers.py` held
the repo's names, `snapshot.py` was the repo's of 2026-09-21, with the old
list in it, and `snapshot_macro.py` the repo's of 2026-08-12.

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
reads. The bars behind them were never weekly -- `fetch_session_bars`, under
both feeds, pulls daily bars over a ranged window and keeps one. This feed
keeps the rest.

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
- **The job adds a file and changes none, and checks that before it
  commits.** `panel_guard.py --against HEAD` compares the files on disk with
  the commit the run started from, first of its gates: a new session passes,
  and a file already committed that the run changed, relabelled or removed
  fails it. CI cannot do this for it, because CI never runs on this job's
  commit. The script refuses a session that is on file unless it is given
  `--force`, which the workflow never passes; this step is what says so if
  that ever stops being true. A failure means no commit, and the session is
  recovered like any other the audit names.
- **Neither attempt is late enough for the futures.** WTI, WTI_NEXT, GOLD,
  SILVER, DXY and US2Y_FUT trade past the cash close and are not read before
  13:00 UTC on the day after the session (Known data defects, below). 21:45
  UTC and 09:15 UTC are both earlier, so every daily file written since
  2026-10-05 lists all of them in `missing` with the reason, whichever
  attempt wrote it. US10Y and VIX are final by evening and are read. The
  eight files from 2026-09-11 to 2026-09-23 hold evening quotes for the five
  they carry. The heatmap's daily tape reads `fx.DXY` and shows it missing
  meanwhile. An attempt after 13:00 UTC, with no evening write ahead of it,
  would bring them back, each commodity naming its contract. Whether 09:15
  UTC is in fact late enough is not known: no committed read falls between
  02:58 and 13:07 UTC.

Eight sessions were lost between 2026-09-21 and 2026-10-02 with every run
green: six to the UTC date, two (the Fridays) to the null-close window, each
refused once with nothing asking again.

## Known data defects

- **The mirror backfill script.** `scan_pipeline/scripts/backfill_weekly.py`
  is a faithful copy of Kimi's runner and has diverged from
  `scripts/backfill_weekly.py`. It has had `--merge` and the refusal of
  `--only ... --force` since 2026-08-26 (`7cf7025`; until 2026-10-06 this
  entry said it had no `--merge`) and nothing since: it can still call an
  unposted Friday a holiday (`DATA_FEED.md` sec.1c), and its `--merge` still
  writes a fresh fetch over a bar the week already holds (The backfill,
  below). Nothing invokes it and a test fails if anything starts to.
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
  recorded as `provenance.<block>.<ticker>.observed`; and the six
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
  named every time (37,947 of 37,947 on 2026-10-05; the list's `reach` has
  the latest run's). Give anything new a cause in the JSON by hand, then
  `--write`. Network and yfinance needed; the tests need neither. EQR is
  audited as VMRK, which carries its history.

  The same audit covers the Friday job's files, and one of them this repo's
  writer did not write. **2026-08-28.json took every equity close from the
  provider's `1wk` bar**: a one-off script on the runner, on the Saturday the
  provider's daily closes were null. For 330 names that is the Friday close.
  AVB's is 68.14 from Monday 2026-08-24, null volume, the successor's price
  under a dead symbol, and `2026-08-28.corrected.json` carries it too. Not
  corrected. (BTC, GLD, BNY, MRSH, DOC and VMRK in that file are daily
  bars, merged in on 2026-10-06. VMRK's is the successor's own Friday close,
  65.54, adjusted to the merge: 64.7694.)

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
  `audit_series.py` reads. The later bar is checked against the provider's
  raw chart first, as the daily feed checks: a session whose close is not
  posted has a row with a null close, every writer here reads a row with no
  close as no bar, and a Friday the raw chart lists is never a holiday.

  **So a holiday week lands a week late, on purpose.** The job runs on the
  Saturday and SPY's next bar is Monday's, so the proof is never there on the
  night. Writing the equities at once on the strength of a calendar would
  lose the instruments for good: they cannot stand in that night, and a
  weekly file cannot be completed afterwards. Written by the next run the
  file is whole, each instrument with its `observed` date. Until then every
  reader has last week's `market_state.json`, dated as what it is.

  **A refusal is green, so the panel is what gets asked.** The weekly job
  writes every Friday `snapshot.unwritten_fridays` lists, oldest first, and
  stops at the first one refused. It derives `market_state.json` through the
  chain (`snapshot.write_market_state_chain`): the committed state is "last
  week's" only after exactly one new week, and after two, or none, the
  deriver handed it takes `corr_prev` from the wrong week. `truth_check
  --feed` fails an empty `series`, a new file with no SPY bar, a
  `session_note` it cannot read a session out of, and a Friday missing
  between two weekly files; it warns from the Sunday while the newest Friday
  is still owed. A hole matters more than it looks: `market_state` nulls the
  windows that reach it, but sector-regime-heatmap counts weeks by position
  and scores the week after a hole over two weeks, calling it one.

  `scripts/backfill_weekly.py` called a week a holiday whenever no ticker had
  a Friday bar, which is every Friday on the night. It asks the witness under
  the same rule now and exits 2 on a week it cannot write, and `--only` can no
  longer start a week, with or without SPY among its names: it adds to weeks
  that exist. That is how `2024-08-09.json` came to hold no index
  or sector ETF at all, SPY among them, with none listed in `missing`. The
  sixteen were merged in on 2026-10-06 (next entry).

  Both of these are outside this repo and changed by hand: the runner's copy
  of `scan_pipeline/`, which writes the empty file until it is synced (the
  gate stops it), and the job's prompt, which asks for the most recent Friday
  only and so needs the catch-up put into it.
- **`2024-08-09.json` went six weeks without its sixteen ETFs.** The
  44-ticker merge of 2026-08-26 ran from 2024-08-09 and the panel began on
  2024-08-16, so `--merge` started the week from its list; the next day the
  277 of `STOCK_UNIVERSE` were merged in. Neither list had an index or
  sector ETF in it. The file held 313 series and none of the sixteen, with
  none listed in `missing`, and every other week had all of them.

  **No committed number was touched.** `market_state` skips a week that
  lacks a name, and when the file was written its week was already outside
  every window of the newest state: whatever closes the sixteen take,
  `market_state.json` re-derives byte-identical. What was wrong is the
  record.

  Merged in on 2026-10-06 with `--merge` (owner sign-off), fetched at
  01:48:08 UTC and stamped so in `provenance.series`. Each is Friday
  2024-08-09's bar by close and by volume (`audit_series.py`, run again on
  the merged panel: nothing new, changed or gone). **That stamp matters.**
  The same names in `2024-08-16.json` are anchored to 2026-08-12, before
  the September distributions, so a return read across the two files is
  overstated by 0.26 points for SPY and by up to 0.84 (XLRE; SMH, which
  pays yearly, by nothing). Nothing committed reads across that pair.

  `truth_check --feed` now warns when a week has neither a bar nor a
  `missing` entry for one of the sixteen, or for a name an earlier and a
  later week both carry. Earlier and later, not the weeks either side: a
  rule that needs both neighbours cannot see the first file, and the two
  corrected weeks are adjacent and would hide each other. It cannot see a
  stock missing from the first file, which reads as a name that joined a
  week later. BNY, MRSH and DOC read so for two weeks, with bars from
  2026-09-25 only, until they were merged into every week; VMRK does join
  late, on 2026-08-21, by decision. The newest file is `--config`'s to hold
  (Universe vs focus set, above).

  The runner's copy of the file is the old one until it is synced, and the
  weekly job's gate warns about it meanwhile. Nothing else follows: the job
  pushes only the newest week, and its `market_state` does not depend on
  this one. Sync it with the rest of `data/weekly`, never by itself: the
  repo's copy has held BNY, MRSH and DOC since later that day, and alone on
  the runner it turns the one warning into 110 (Universe vs focus set,
  above).
- **WTI, GOLD and SILVER are named contracts since 2026-10-05; the 113
  weeks before name nothing.** Those files hold Yahoo's continuous symbols
  (`CL=F`, `GC=F`, `SI=F`), and Yahoo does not hold them still. It rebuilt
  `GC=F` from the nearest-expiry contract onto the active one around
  2026-09-05, for its whole history: 107 of 113 weeks no longer match it, by
  up to 59.00 or 1.7%. `SI=F`'s live quote is a different month from its
  history. And 2026-09-18.json holds the November crude contract's last
  trade, 95.47, where October settled 100.30 (#110). Reading after the
  settlement does not pick the month: 2026-08-28, read at 14:10 UTC on the
  Saturday, got December gold and silver. Volume is not a tell either: on a
  contract's last day the continuous bar is the expiring month's close on
  the next month's volume.

  **Owner decision 2026-10-05: the nearest-expiry contract, read by name.**
  WTI is the NYMEX front month, GOLD and SILVER the COMEX spot month, each
  held through its last trade date. `WTI_NEXT` is the crude contract after
  WTI's. The writer reads `CLX26.NYM`, `GCV26.CMX`, `SIV26.CMX` off a roll
  calendar in `snapshot_macro` and commits the month as
  `provenance.commodities.<T>.contract`. The continuous symbols are never a
  fallback: no bar for the named contract means `missing`. The rule is what
  327 of the 339 committed closes already hold. It is the spot month and not
  the active one because that is the price of the metal and the panel's own
  history; so GOLD reads about 0.7% under `GC=F`, which `facts.json` and the
  sector grids still pull.

  **The old files are not edited and not corrected.** Twelve closes in five
  weeks are off the rule, and `data/commodity_settlements.json` answers for
  them: eight superseded, and four gold weeks (2026-08-28, 09-11, 09-18,
  09-25) recorded as having no settlement, because the September contract
  expired and nothing serves it. `audited_through` in that file is what lets
  a committed close with no label be read at all; one from after it never
  is. `snapshot.commodity_series` is that rule and the only reader
  `market_state` uses. It also measures WTI's `d1w` on one contract, from
  last week's `WTI` or `WTI_NEXT`: in a roll week front against front is
  mostly the spread (-7.9% for 2026-09-25, where November fell 3.8%).

  `truth_check --feed` fails when `market_state.json`'s WTI, GOLD or SILVER
  is not what that derives (px, contract, each change); when a `contract`
  label cannot be right for its session; and when the settlement file is
  missing from a tree that derived a state. It warns for a week after the
  audit with no named settlement. All of these are what a runner that is
  behind produces. It needs `scan_pipeline/` AND
  `data/commodity_settlements.json`, and the weekly job writes neither.

  **An expired contract cannot be read.** Yahoo drops one within days of its
  last trade. So a rewrite of an old week lists its commodities in
  `missing`, and a Friday that is a last trade date (the first is
  2026-11-20, CLZ26) may lose its WTI on the Saturday. A holiday week is the
  hard case: it is written a week late, and 2026-12-25 is written on
  2027-01-02, four days after GCZ26 and SIZ26 last trade. `GC=F` cannot stand
  in, so that week may have no gold settlement at all. Fill what can be
  filled with

      python scripts/backfill_commodities.py

  which reads by contract name, only adds, and re-derives
  `market_state.json`. For one named week it can take the continuous
  symbol's bar instead (`--week <as_of> --instrument WTI --from-continuous
  --reason "..."`), but only on proof that the symbol was the nearest-expiry
  chain at that roll; `GC=F` fails that today. `--unavailable` records a
  week nothing can supply, and `--check` compares what is committed with the
  provider. `DATA_FEED.md` sec.1d has all of it.
- **Bars that were changed in place.** Four commits on main changed what a
  panel file held, all from before the guard compared bars (2026-10-06).
  `87dba89` (2026-08-16) changed three volumes in 2026-08-14.json (ALL, LOW,
  PGR) and `0bcb75f` (2026-08-29) one in 2026-08-28.json (VTR, 1916834 to
  1916830), each a hand transcription put right against the runner's copy.
  `6260495` is the 2026-08-26 incident and `2a0f0dd` its revert. No close
  was changed by any of them, and every other commit that touched a file on
  main through 2026-10-06 only added to it, the five merges into existing
  weeks among them.
  `5e04b91` rewrote the 13 daily files 17 minutes after `b3def63` first
  wrote them, on the branch of #93, so main never held the earlier form.
  Found by comparing every commit that touched `data/weekly` or `data/daily`
  with its parent. Nothing is undone: the files as they stand are what every
  reader has had since. The guard has no memory of this; it compares a push
  with the tip it replaced.
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

**What a week on file gets depends on what was dispatched.** Named tickers
are added to it (`--merge`). With `tickers` blank it is skipped, and only the
weeks that have no file are written. It is rewritten whole (`--force`) only
when `rewrite` is ticked, which is off by default and refused beside a ticker
list. Until 2026-10-06 a blank `tickers` meant `--force` by itself, so the one
way to write a missing week was also the way to rewrite every other.

**What a panel file held, it still holds.** `scripts/panel_guard.py` records
every file's bars before the write and compares after it. For each file of
`data/weekly` and `data/daily` that was there: the file is still there; every
entry it had in `series`, `rates`, `vol`, `commodities` and `fx` is still
there with the same close and volume; each still has the label it had
(`provenance.<block>.<ticker>`, or none); and the file's `source`,
`fetched_at` and `session_note` are unchanged. New weeks and new names pass.
Values are compared, not bytes. Corrections are held to it too, with one
allowance: an instrument a correction newly records in `restated` may change
there, which is what a restatement is.

The first guard counted series per file, and CI carried its own copy of the
count. A count does not move when a bar is written over or when one name
replaces another, and CI's copy, which looped over the files still there,
passed a deleted file as well. The rehearsal below, run again on 2026-10-06
(the 4,612 bars changed and restamped on a copy of the panel, corrections
rebuilt), fails the guard now: 4,656 bars and as many labels in 108 files,
the 2026-08-21 correction's copies among them.

**A rewrite is declared, and may not lose a bar.** Dispatched with `rewrite`,
the workflow passes `--force` to the backfill and `--rewrite <start> <end>`
to the guard. Inside that range a weekly file's bars, labels and stamps may
change, and the guard prints how many did. Outside it the rule holds, and an
entry that vanished fails either way. The commit is titled REWRITE. On
today's panel a rewrite of the history would stop there:
`equity_universe()` no longer fetches AVB, EA and EQR, which hold 314 bars in
the weekly files, and a commodity whose contract has expired is listed in
`missing` instead (`DATA_FEED.md` sec.1d). No flag lets a bar go.

**The same comparison runs in CI and in the daily job**, as
`panel_guard.py --against <commit>`, and takes no `--rewrite` there: a commit
that changes what the panel held fails CI whatever it says about itself, a
revert of a bad write included. So do two things a correction can need: one
more zero-volume drop in a correction that exists, and withdrawing one. Each
goes in over a red check, by someone who has read why. What it does not reach
is the runner: the weekly job's gate line is `truth_check --feed --derive`,
and CI sees its push only once it is on main. What stands there instead is
the writer (below).

**What the guard does not say.** It compares a file with what that same file
held. A new file held nothing, so a NEW correction is not compared with its
base: that its series are its base's, bar for bar, is
`tests/test_instrument_sessions.py`'s to say, for `data/weekly` only, and
nothing says it for a daily correction (there is none). And a "before" with
no panel file in it is refused, not passed: `--against` on a scratch copy the
commit does not track used to print "0 file(s) before" and OK. A copy of the
panel is rehearsed with `--snapshot` and `--compare`.

**A week is written once.** `snapshot.write_weekly` raises `WeekOnFile` and
writes nothing when the Friday already has its file. Until 2026-10-06 it
wrote over it without a word: another fetch's closes over every bar,
`fetched_at` restamped, and any name the second fetch lacked gone and listed
nowhere. Only the weekly job's prompt said not to. The question is asked
first, before the witness and before any instrument is fetched, and again
just before the write. The refusal says what to do instead: leave the file;
push one that never reached the repository as it stands; add the names it
lacks afterwards, with a merge; take a restated close to a correction.
`overwrite=True` is `scripts/backfill_weekly.py --force` and nothing else,
and the workflow reaches that only with `rewrite` ticked.

What is at the week's path is not always the week. A zero-byte file, the
first bytes of a write that died, another week's file: the writer refuses
those too, because nothing here writes over a file, and says it in other
words. It is not a weekly file; do not push it; remove that one file and run
again. Told to push it instead, a run would have pushed a file the feed gate
fails, under a name `unwritten_fridays` no longer owes. The writer cannot
leave one itself any more: a week is written beside its path and moved into
place.

The mirror script is left as it is (owner decision 2026-10-06). It passes no
`overwrite`, so its `--force` on a week that is on file stops at the writer,
and a test that runs it into a tmp directory fails if that changes. Its
`--merge` does not go through the writer and still overwrites; the guard is
what catches that.

**Where the runner is not held to it.** Three things, all outside this repo.

- Its copy of `scan_pipeline/` predates the witness rule. Until the sync it
  is already owed, its writer overwrites as before.
- The refusal, and step 2 of the job's prompt, look at the runner's own copy
  of `data/weekly`. A week the repository has and that copy lacks, one a
  backfill wrote from this side, is one the job would write and push over
  when it is the Friday it runs for, and CI reports that only afterwards.
  Not the case today: the copy has every base week. Keep it so.
- On the path the prompt prescribes the refusal is never reached. Step 2
  routes a week on file around the writer, and step 7 pushes the weekly
  file only "if newly written". A run that died between writing and
  pushing, as on 2026-08-15 and 2026-08-22, leaves a week its next run
  neither rewrites nor pushes; a week later `unwritten_fridays`, reading the
  runner's directory, does not owe it, and the repository has a hole that
  the runner's gate passes and CI fails after the push. Step 7 has to push
  a week the repository lacks whether or not that run wrote it.

Where the refusal will be met is a second attempt inside one run, which the
2026-08-28 run made (`step3_weekly.py`, then `step3_weekly_v2.py`). After
the sync the first local write is final: a thin first fetch is pushed as it
stands and mended by a merge, or the owner removes the file by hand.

**Named tickers are ADDED with `--merge`, never `--force`.** `--force` writes a
whole file from the ticker set it was given, so with `--only` it deletes every
other series: on 2026-08-26 that emptied 107 files, 287 series down to 44, and
the job reported success. The script refuses that combination now. `--force` is
for a full-universe rewrite and nothing else.

**`--merge` adds; it never replaces.** A named ticker a week already holds is
left exactly as committed -- its bar, its `provenance.series` stamp and
`missing` -- and the plan says which and how many, in a dry run too: it is
read off the files, not the provider. Until 2026-10-06 such a ticker was
fetched again and written over the committed bar, and the run logged it as
"refreshed" and exited 0. A fresh fetch is adjusted to a later date, so it is
another close for any name that has paid a dividend or split since, and the
count of series does not move, which was all `panel_guard` and CI compared
until then.

**No merge run has hit a committed bar.** Every commit that touched
`data/weekly` was compared with its parent: the two merge runs (`3a099f6`,
`5f0d596`) put 4,839 bars into base files that existed and replaced none,
and all 4,883 `provenance.series` stamps then in the panel (44 are the
2026-08-21 correction's copy) are on a name the file did not hold before.
The three merges of 2026-10-06 that followed (BTC and GLD, the sixteen ETFs
of `2024-08-09.json`, the four renamed names) were compared the same way:
592 bars added, corrections included, and none replaced. The panel holds
5,475 stamps.
`BACKFILL_44.md`'s command run again would have fetched over every bar the
44 have in the 107 base files, 4,612 of them. Rehearsed on a copy of the
panel with the provider stubbed (2026-10-06), it wrote over all of them and
exited 0, and `rebuild_corrections`, `panel_guard` and `truth_check --feed`
all passed the result. The guard was the count then.

A merge run that changes no file and left a named ticker alone exits 2,
which stops the workflow before its commit step: before any download when
every named ticker is already in every week on file in the range, and after
the fetch otherwise. The 44 are the second kind, because SPCX has no bar
before its IPO and only the fetch shows there is nothing to add. A week with
nothing to add is not rewritten. No flag makes a merge replace a bar:
`--force` beside `--merge` does nothing, and the plan says so. A close the
provider has restated is a correction's to carry. `restate_instruments.py`
writes one for a special instrument and nothing writes one for an equity
bar: a correction is rebuilt from its base, so a close changed in one by
hand does not survive.

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

BTC and GLD were merged the same way on 2026-10-06, into all 113 weeks:
226 bars, and the two corrections rebuilt (Universe vs focus set, above).

BNY, MRSH and DOC followed that day, into the 111 weeks before 2026-09-25,
and VMRK into five of them: 338 bars in two runs, and the corrections
rebuilt again. VMRK had a run of its own because `--start` and `--end` are
the only way to keep a name out of a week: one run over the four would have
given it the 106 weeks it must not have.

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
- Edit a committed weekly or daily file. `panel_guard.py` fails a bar, a
  label or a file stamp that changed, and a bar or a file that is gone: in
  the backfill, in CI and in the daily job.
- Write a fresh fetch over a bar a week already holds. `--merge` leaves it
  alone and says so; a restated close goes in `<date>.corrected.json`.
- Merge a renamed symbol into a week that holds its old one. For VMRK that
  is every week before 2026-08-21 but the first: EQR holds that history
  under its own key, the provider serves the same bars under VMRK, so
  `--merge` adds them without a word, and a bar added to a week is never
  taken out. The first, `2024-08-09.json`, holds neither and takes no VMRK
  either (Universe vs focus set).
- Tick `rewrite` on the backfill to add names or to fill a week that has no
  file. It writes every week on file in the range again, whole. Leave it
  off: named tickers are merged, and a blank list writes only what is
  missing.
- Invent a close to fill a gap. Use `missing` with a reason.
- Read `rates.US2Y` straight from a weekly file, or let `US2Y_FUT` stand in
  for it. Go through `snapshot.cash_2y_series`; a gap stays a gap.
- Run the weekly feed job before 13:00 UTC on the Saturday, or bring back
  "the last bar on or before" for an instrument with no bar on the date.
- Change a close in a correction by hand. Use `restate_instruments.py`, so
  the change is recorded in `restated` and survives the next rebuild.
- Read `commodities.*` straight from a weekly file, or let `CL=F`, `GC=F` or
  `SI=F` stand in for a named contract. Go through
  `snapshot.commodity_series`; a gap stays a gap.
- Rewrite an entry in `data/commodity_settlements.json`, or move its
  `audited_through`. `backfill_commodities.py` only adds.
- Call a committed equity close wrong because a fresh fetch disagrees. It is
  adjusted to its fetch date. `scripts/audit_series.py` is the comparison.
- Build a weekly file the writer refused: by hand, from `1wk` bars, or from
  Thursday's. No file is the right outcome of that run, and the next one
  writes it.
- Delete a weekly file to get `write_weekly` past `WeekOnFile`, or pass
  `overwrite=True` from anywhere but the backfill's `--force`. A week on
  file stays as written. One that never reached the repository is pushed as
  it stands. The one file that is removed is the one the refusal itself
  says is not a weekly file: it does not parse, or it is another week's.
- Step over a week that was refused. Write the Fridays
  `snapshot.unwritten_fridays` lists, oldest first, before the newest.
- Give the weekly or the daily writer its own list of names, or add a name
  to the feed without merging it into the newest week in the same change.
  `snapshot.equity_universe()` reads `PRICE_FEED_UNIVERSE`, and
  `truth_check --config` holds the writer and the newest file to it. The
  one other list is the gate's own, `EQUITY_UNIVERSE` in `truth_check.py`,
  for the weekly job's check dir. It changes in the same commit as the feed.
  (`build_universe` keeps a narrower set on purpose: `universe.json` mirrors
  `wiki/universe.md`, which lists stocks.)
- List `data/weekly/*.json` to read the panel. A corrected week is two of
  those. Go through `snapshot._load_weekly_files`: each week once, from its
  correction where it has one.
