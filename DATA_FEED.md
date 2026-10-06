# Data Feed Spec

What the scan writes, what the app reads, and what never gets committed.

One fetch per scan, four outputs. Three are committed and permanent; one is cached and disposable.

```
weekly-council-scan/
├── data/
│   ├── weekly/
│   │   ├── 2026-08-08.json          committed · closes the council saw
│   │   └── 2026-08-08.corrected.json  committed · only if a provider restates
│   ├── us2y_treasury.json           committed · Treasury 2-year for weeks whose file cannot supply it (sec.1a)
│   ├── commodity_settlements.json   committed · WTI / GOLD / SILVER settlements for weeks whose file cannot supply them (sec.1d)
│   ├── market_state.json            committed · derived snapshot, overwritten each scan
│   └── universe.json                committed · machine-readable mirror of wiki/universe.md
└── (not in the repo)
    └── live quotes                  fetched, cached, discarded
```

---

## 1. `data/weekly/<YYYY-MM-DD>.json`

One file per scan, named for the **Friday close** the scan reads. Append-only. Never edited after commit.

```json
{
  "as_of": "2026-08-07",
  "source": "yahoo",
  "fetched_at": "2026-08-07T21:14:03Z",
  "session": "close",
  "series": {
    "SPY":  { "close": 773.26, "volume": 43586300 },
    "SMH":  { "close": 582.70, "volume": 6505000 },
    "XLK":  { "close": 271.08, "volume": 6014900 },
    "NVDA": { "close": 223.96, "volume": 105669400 }
  },
  "rates":       { "US10Y": { "close": 4.66, "volume": null }, "US2Y": { "close": 4.17, "volume": null } },
  "vol":         { "VIX": { "close": 14.90, "volume": null } },
  "commodities": { "WTI": { "close": 78.18, "volume": 241222 }, "GOLD": { "close": 4340.70, "volume": 422 }, "SILVER": { "close": 63.33, "volume": 461 } },
  "fx":          { "DXY": { "close": 99.60, "volume": null } },
  "missing":     [ { "ticker": "PLTK", "reason": "delisted 2026-07-31" } ]
}
```

This is a file from before 2026-10-04, and its `US2Y` of 4.17 is not the 2-year yield: it is the 2YY=F future, 2 bp off that day and 36 bp off six weeks later. Files written since carry the Treasury 2-year under `US2Y`, the future under `US2Y_FUT`, and a `provenance.rates` label that tells the two kinds of file apart. Sec.1a has the whole story; read it before using `US2Y` from any weekly file.

Its `WTI`, `GOLD` and `SILVER` are the provider's continuous symbols, and nothing in the file says which contract month each close is. That `GOLD` is the August 2026 contract's settlement; the provider's own `GC=F` now shows 4399.70 for the same day, which is December's. Files written since 2026-10-05 read a named contract and say which in `provenance.commodities`. Sec.1d has that story; read it before using a commodity from any weekly file.

**Rules**

- **Closes only.** No intraday, no bid/ask, no derived fields. This file is an observation.
- **`missing` is required and never empty-by-omission.** A ticker that could not be fetched is listed with a reason. A silently absent ticker is indistinguishable from a ticker that didn't exist, and that ambiguity is what the agents fill in from priors.
- **`fetched_at` is UTC and real.** It is how you detect a scan that ran against a stale cache.
- **Never edit.** If a provider restates, write `<date>.corrected.json` with the same shape plus `"corrects": "2026-08-08.json"` and `"reason": "..."`. Readers prefer the correction; the original stays. A correction that *replaces* a close, rather than dropping a bar, also carries `restated`: the record of what it replaced (sec.1b).
- **A close is the session's own, settled, or it is not in the file.** For `rates` / `vol` / `commodities` / `fx`: the bar dated `as_of`, or the instrument is in `missing`. An earlier session stands in only where the provider shows the instrument skipped `as_of`, and then the file says which session it is. A futures or dollar-index bar is not read until the exchange has settled it. Sec.1b has the rules and what the files written before them hold (amended 2026-10-05). `series` is held to the bar dated the file's session (sec.1c) by the weekly job and not yet, ticker by ticker, by the backfill writer; what that let through is in sec.1b, "The equity series".
- **The series are one session's, and `SPY` is its witness.** A weekly file is written only with an `SPY` bar: the one dated `as_of`, or, where a later `SPY` bar proves the Friday was not a session, the last session of that week, which the file names in a top-level `session_note` (`"Friday holiday; bars from 2026-07-02"`). No witness, no file, and never an empty `series`. Sec.1c has the rule, what the writer did before it, and who comes back for a week it refused (amended 2026-10-06).
- **`provenance` is optional and records per-series anchors.** Adding a ticker to a past week (a targeted backfill) fetches it *now*, so its adjusted closes are back-adjusted to a different date than the rest of the file. The file-level `source` / `fetched_at` still describe the majority of the series and are never restamped by a merge -- restamping would relabel every untouched series with a fetch that never happened to it. A merge only adds: a ticker the week already holds is left exactly as committed, bar and label, and nothing is written over it (since 2026-10-06; until then `--merge` wrote the fresh bar over it, which the two merge runs on the panel never did, checked commit by commit). The added names are listed individually instead:

```json
"provenance": {
  "series": {
    "PLTR": { "source": "yahoo-backfill", "fetched_at": "2026-08-26T04:08:06Z" },
    "VST":  { "source": "yahoo-backfill", "fetched_at": "2026-08-26T04:08:06Z" }
  }
}
```

  A series absent from `provenance.series` carries the file-level `source` and `fetched_at`. Every key in `provenance.series` must exist in `series`. Consumers that care about the adjustment anchor -- `sector-regime-heatmap` refuses a window whose anchors span more than 180 days -- must resolve the anchor **per ticker**, not per file, or a merged week silently reports one anchor for two.

  This block exists because the alternative is writing two adjustment bases under one timestamp and calling it a fact. `--merge` in `scripts/backfill_weekly.py` is the only writer.
- **`provenance.<block>` names an instrument the file-level stamp does not describe.** The file-level `source` stays `yahoo`: it describes every series and every other instrument, and `sector-regime-heatmap` refuses a week whose file-level source it does not know. An instrument is named for one of four reasons, and a file from before 2026-10-04 names none:
  - **It came from another publisher.** `US2Y` is Treasury's, the one instrument Yahoo cannot supply (amended 2026-10-04, sec.1a).
  - **Its value is a stand-in.** The instrument printed nothing on `as_of`, a later bar proves it, and `observed` is the earlier session of the same week that the value belongs to (amended 2026-10-05, sec.1b).
  - **A correction restated it** from a later fetch. The label carries that fetch's time and the `-backfill` source (sec.1b).
  - **It is a commodity.** `contract` is the contract month the close belongs to, in every file written since 2026-10-05 (sec.1d).

  An ordinary week names `US2Y` and the four commodities. The commodity closes here are the settlements of 2026-10-02:

```json
"rates": {
  "US10Y":    { "close": 5.277, "volume": null },
  "US2Y":     { "close": 4.83,  "volume": null },
  "US2Y_FUT": { "close": 4.635, "volume": null }
},
"commodities": {
  "WTI":      { "close": 91.11,     "volume": 337181 },
  "WTI_NEXT": { "close": 89.43,     "volume": 209718 },
  "GOLD":     { "close": 4133.7002, "volume": 348 },
  "SILVER":   { "close": 59.977,    "volume": 229 }
},
"provenance": {
  "rates": { "US2Y": { "source": "treasury", "fetched_at": "2026-10-10T13:20:07Z" } },
  "commodities": {
    "WTI":      { "source": "yahoo", "fetched_at": "2026-10-10T13:20:09Z", "contract": "CLX26" },
    "WTI_NEXT": { "source": "yahoo", "fetched_at": "2026-10-10T13:20:09Z", "contract": "CLZ26" },
    "GOLD":     { "source": "yahoo", "fetched_at": "2026-10-10T13:20:10Z", "contract": "GCV26" },
    "SILVER":   { "source": "yahoo", "fetched_at": "2026-10-10T13:20:10Z", "contract": "SIV26" }
  }
}
```

  Good Friday 2026-04-03, as a rewrite of that week would commit it. The Cboe index and the future printed nothing and carry Thursday's close, each saying so; Treasury published, so its 2-year is the day's own:

```json
"rates": {
  "US10Y":    { "close": 4.313, "volume": null },
  "US2Y":     { "close": 3.84,  "volume": null },
  "US2Y_FUT": { "close": 3.806, "volume": null }
},
"provenance": {
  "rates": {
    "US10Y":    { "source": "yahoo",    "fetched_at": "2026-10-05T04:40:45Z", "observed": "2026-04-02" },
    "US2Y":     { "source": "treasury", "fetched_at": "2026-10-05T04:40:45Z" },
    "US2Y_FUT": { "source": "yahoo",    "fetched_at": "2026-10-05T04:40:46Z", "observed": "2026-04-02" }
  }
}
```

  `<block>` is one of `rates`, `vol`, `commodities`, `fx`. An instrument absent from `provenance.<block>` carries the file-level `source` and is the bar dated `as_of`. A commodity absent from it is a continuous symbol's bar of an unnamed month, which is every file through 2026-10-02 (sec.1d). Every key must exist in its block. `observed` is always an earlier day of the same Mon..Fri week, and it is written only with proof: the publisher skipped `as_of`, and a later row or bar shows it (sec.1a "The fetch", sec.1b). That proof does not exist on the night. Where the equity market traded the Friday and one instrument did not, the instrument stays in that file's `missing` (a `US2Y` gap is filled beside it, sec.1a); where the equity market was closed too, no file is written that night at all (sec.1c), and the run that writes the week afterwards has the proof and commits every stand-in with its date. `write_weekly` is the only writer of these labels in a weekly file, from what `snapshot_macro.fetch_special_instruments` reports, and `scripts/restate_instruments.py` the only writer in a correction.

  **Does `sector-regime-heatmap` tolerate it? Yes, checked 2026-10-05 against its `a8363de`.** `check_basis()` reads the file-level `source` and each `provenance.series.<ticker>.source`, and refuses either if it is not `yahoo` or `yahoo-backfill`. `anchor_of()` reads `provenance.series` and nothing else, the daily tape checks only the file-level `source` and `cadence`, and nothing in that repo reads `provenance.rates`, `.vol`, `.commodities` or `.fx`. So a label under `provenance.<block>` is invisible to it whatever its `source`. Two things would break it and are therefore fixed points: a new file-level `source`, and a new source string under `provenance.series`.

  **This label is load-bearing.** It is the only thing that separates a Treasury 2-year from the futures mark that every earlier file holds under the same key (sec.1a). A reader that ignores it differences two instruments.

**Size.** ~300 series entries + 9 instruments ≈ 15–18KB per file. 104 files per two years ≈ 1.7MB. No pruning, no rotation, ever.

**Ticker set (amended 2026-08-11, owner decision — supersedes the original charted-set-only text).** The FULL scan universe is committed: every ticker in `STOCK_UNIVERSE` (277; 274 after the 2026-09-21 out-of-cycle review, see wiki/universe.md) plus SPY, QQQ, DIA, IWM, SMH and the 11 sector ETFs in `series`; US10Y/US2Y/US2Y_FUT in `rates`; VIX in `vol`; WTI/WTI_NEXT/GOLD/SILVER in `commodities`; DXY in `fx`. Rationale: the pipeline already fetches the whole universe at scan time, so the marginal cost is zero, and the file becomes the complete record of what the Council could have seen — not just what the app happened to chart. Instrument notes: US2Y is the U.S. Treasury par yield curve 2-year (column `2 Yr`), the one instrument that is not Yahoo's, named as such in `provenance.rates` (amended 2026-10-04; through 2026-10-02 this key held the 2YY=F future, see sec.1a); US2Y_FUT is that future, kept under a name that says what it is and never a stand-in for US2Y; US10Y is ^TNX, which current Yahoo serves as a plain yield (a legacy ×10 guard divides only if a raw value >20 ever appears); WTI, GOLD and SILVER are the nearest-expiry futures contract, read under its own symbol and named in `provenance.commodities`, and WTI_NEXT is the contract after WTI's (amended 2026-10-05; through 2026-10-02 these keys held the continuous symbols CL=F, GC=F and SI=F, see sec.1d); volumes are null for indexes/rates, never invented.

**The equity set (amended 2026-10-06, owner decision 2026-10-05).** `series` commits `PRICE_FEED_UNIVERSE` (`scan_pipeline/config/tickers.py`) and the sixteen index and sector ETFs. That union is `snapshot.equity_universe()`, the one function the weekly job, a full backfill and `scripts/daily_observe.py` all fetch. The constant is three sets: `STOCK_UNIVERSE`, which the engines scan; the 44 names backfilled on 2026-08-26; and since 2026-09-21 the owner's Council watchlist, which is the focus set's stocks and two macro ETFs, `BTC` (Grayscale Bitcoin Mini Trust) and `GLD`. The paragraph above names the first of the three.

For the two builds after that date the weekly writer fetched the first two. `equity_universe()` spelled the union out for itself and did not have the watchlist, so `BTC` and `GLD` were in the daily files from 2026-09-22 and in no weekly file, in `series` or in `missing`: the silent absence the `missing` rule above exists to prevent. Nothing failed, because `truth_check --config` held the newest weekly file to the focus names and neither is one. The function reads the constant now. Both names were merged into all 113 weeks on 2026-10-06 and are labelled in `provenance.series`. Every one of the 226 bars is dated its file's session (the Thursday, in the five holiday weeks) and matched a fresh fetch on close and on volume. Neither pays a distribution, so their adjusted and raw closes are equal and do not depend on the fetch date; `BTC` had a 1:5 reverse split on 2024-11-20, and one fetch puts every week on the basis after it.

`truth_check --config` fails when `equity_universe()` leaves out a name of `PRICE_FEED_UNIVERSE`, and when the newest weekly file has neither a bar nor a `missing` entry for a name the writer fetches. So a name that joins the feed is merged into the panel in the same change, with `scripts/backfill_weekly.py --only <names> --merge`, which writes a `missing` entry where the provider has no bar. Two limits. It holds the newest week and no other: `BNY`, `MRSH`, `DOC` and `VMRK` joined on 2026-09-21, have bars from 2026-09-25, and are in neither `series` nor `missing` of the 111 weeks before, which is not decided and not changed here. For the same reason a failure clears by itself once a later week is whole, with the hole still behind it. And it does not run on the runner: the weekly job's gate line is `--feed --derive`, so a week written by a stale copy of `scan_pipeline/` passes there, is pushed, and fails on main. That stops more than CI. `.github/workflows/daily-observe.yml` runs `--feed --config` and the whole suite before it commits a session, so from the Monday no daily file is committed until the week is merged, and the sessions skipped meanwhile are recovered by hand (sec.4, "Completeness"). A `--merge` of the names into that week is the repair. The way not to need one: after any change to the feed, the runner's `scan_pipeline/config/` is copied before the next Saturday build.

Nothing reads either name from a weekly file yet. `market_state` reads the sixteen ETFs. `sector-regime-heatmap` (checked 2026-10-06 against its `86446b6`) takes `series.GLD` and `series.BTC` from `data/daily`, for two comparison rows on its daily tape, and builds no such row from the weekly panel. Computed on the panel before the merge and after it, its weekly metrics are byte-identical for each of the 109 weeks it can compute, and it refuses the first four, which have too few weeks behind them, the same way on both. `scan_pipeline/panel_source.py`, off by default, keeps both out of the engines' scan set. They are stored for Council v2, where Ophelia's third pass weighs both every week (`lab/council_v2.md`). The 19 daily files before 2026-09-22 hold neither, and daily files are not backfilled (sec.4).

---

## 1a. `US2Y` and `data/us2y_treasury.json`

**`US2Y` is the Treasury 2-year, and for 113 weeks it was not.** Through 2026-10-02 the feed committed Yahoo's `2YY=F` (CME 2-Year Yield futures) under this key, on the belief that a front-month yield future tracks the cash 2-year within a few bp. The contract is not traded: volume 0 on 51 of the 54 sessions from 2026-07-20 to 2026-10-02, open interest 4, last trade 2026-09-22. What Yahoo serves is an exchange mark that can sit still for weeks (4.170 on 16 consecutive sessions in August) and meets the cash yield only when the contract cash-settles on the last business day of the month.

| Session | `2YY=F` | Treasury `2 Yr` | Gap |
| --- | --- | --- | --- |
| 2026-09-18, weekly file | 4.404 | 4.76 | -36 bp |
| 2026-09-25, weekly file | 4.472 | 4.81 | -34 bp |
| 2026-09-29 | 4.548 | 4.89 | -34 bp |
| 2026-09-30, settlement | 4.885 | 4.88 | +0.5 bp |
| 2026-10-01, next contract | 4.610 | 4.78 | -17 bp |
| 2026-10-02, weekly file | 4.635 | 4.83 | -20 bp |

Across the 113 committed weeks the mark is more than 10 bp from the Treasury 2-year in 24, and more than 20 bp in 13. `US10Y` (^TNX) over the same weeks is within 2 bp of the Treasury 10-year in 108. `market_state.json` derived its 2-year, its 2s10s and the curve leg of `regime` from the mark, and for the three weeks to 2026-10-02 carried a 2s10s 20 to 36 bp too steep (issues #110, #119, #129).

Yahoo has no cash 2-year: its yield indices are ^IRX, ^FVX, ^TNX and ^TYX. So since 2026-10-04 `US2Y` is read from the U.S. Treasury daily par yield curve, column `2 Yr`, and the future is kept as `US2Y_FUT`. That makes Treasury a second publisher for exactly one instrument; the Provider section states the trade.

**What `US2Y` means in a given file**

| File | `rates.US2Y` | How to tell |
| --- | --- | --- |
| Every weekly file through 2026-10-02; the daily files that carry rates at all (2026-09-11 to 2026-09-23) | the 2YY=F mark | no `provenance.rates.US2Y` |
| Files written by the Treasury-aware writer | Treasury par curve 2-year | `provenance.rates.US2Y.source` is exactly `treasury` |

The old files are not edited and are not corrected. They are right about what they observed, and a correction is a full copy of its week: restating one number in 113 weeks would add 113 copies of the panel and put every one of them behind the correction trap (CLAUDE.md). The label is the test, not the date, because the writer that runs on Fridays is the runner's copy of `scan_pipeline/` and changes only when that copy is synced.

**`data/us2y_treasury.json`** holds the Treasury 2-year for the weeks whose own file cannot supply it: all 113 through 2026-10-02, and any later week whose Treasury fetch failed.

```json
{
  "schema": "us2y-treasury/v1",
  "instrument": "US2Y",
  "source": "treasury-backfill",
  "column": "2 Yr",
  "session": "close",
  "series": {
    "2026-06-26": { "close": 4.07, "fetched_at": "2026-10-05T02:35:18Z" },
    "2026-07-03": { "close": 4.14, "fetched_at": "2026-10-05T02:35:18Z", "observed": "2026-07-02" }
  }
}
```

- **Keyed by the weekly file's `as_of`.** An entry for a week with no weekly file is refused by `truth_check --feed`.
- **Append-only by week.** A week that has an entry keeps it. `scripts/backfill_us2y.py` adds weeks and never rewrites one. CI compares the file with the previous commit and fails if an entry that was there changed or disappeared; like the panel check beside it, that sees the head of a push against its parent, not every commit in between. The stronger audit is `backfill_us2y.py --check`, which compares every committed Treasury 2-year against the archive and reports a difference without writing.
- **`observed` is the session the value was published for** when that is not `as_of`. 2025-04-18, 2025-07-04, 2026-06-19 and 2026-07-03 were bond-market holidays and carry the last row of their week. 2026-04-03 is the opposite case: equities were closed for Good Friday but Treasury published, so that entry is the day's own row (3.84) while the rest of that weekly file is Thursday's session.
- **A late fill reads the same number.** Treasury publishes one par curve per business day and keeps it, so a week filled afterwards gets the value a fetch that night would have. That is why a failed Friday is repairable here and a missed equity bar is not.

**Reading the 2-year.** For week `d`: the weekly file's `US2Y` if `provenance.rates.US2Y.source` is `treasury`; otherwise this file's entry for `d`; otherwise nothing. `snapshot.cash_2y_series()` is that rule and is the only reader `market_state` uses. A week's own value wins over an entry here, and the gate fails if the two disagree. `US2Y_FUT` is never a fallback: a week with no Treasury value derives as `null` with a `_reason`, and `truth_check --feed` warns until `backfill_us2y.py` fills it. That script re-derives `market_state.json` after a fill, because the history is one of its inputs.

**The fetch.** One CSV per calendar year, columns read by name (the 2024 file has no `1.5 Month` column, so `2 Yr` moves). The row dated `as_of` is the observation, and a missing row is not evidence of a holiday: if Treasury posts late or a stale copy comes back, the row on top is yesterday's, and the Friday job always runs after the day has ended, so no clock can tell the two apart. No row dated `as_of` therefore means `US2Y` goes to `missing` with the reason. Another day stands in only on proof: when the file already holds a row dated after `as_of`, Treasury skipped that day, and the last row of the same Mon..Fri week is used with `observed` recording which. That proof never exists on the night itself. So a Friday the bond market skipped and the equity market did not is a gap in its own weekly file, filled afterwards by `backfill_us2y.py` once the next session's row is up; until then `market_state` shows the 2-year as `null`. A Friday both markets skipped has no weekly file that night (sec.1c). The run that writes it afterwards reads Treasury under this same rule, and where the next row is up by then the file carries the week's last row itself, with `observed`. Daily files follow the same rule.

**The gate.** `truth_check --feed` fails when `market_state.json` shows a `US2Y` level that is not the Treasury 2-year for its week, or anything but `null` where none exists. Three weekly syntheses found this defect by reading two files side by side; nothing mechanical did. It also fails when the weekly change or the percentile is `null` although the values it needs are in the tree, and when `us2y_treasury.json` is absent from a tree where `market_state.json` was derived. Those are the two ways a runner gets this wrong: the Friday job runs its own copy of `scan_pipeline/` against its own copy of `data/`, and it does not write the history file, so both have to be put there by hand. That job fetches `truth_check.py` fresh and stops on a FAIL, so either mistake is caught before it pushes. `python scripts/rederive_market_state.py` regenerates `market_state.json` through the whole chain when an input changed outside the weekly job.

---

## 1b. Which session a close is

**Until 2026-10-05 nothing in a file said which session an instrument's close was read from.** The writer took the bar dated `as_of` when the provider had one and "the last bar on or before" when it did not; the note it attached to the second case was dropped before the file was written. `scripts/audit_instruments.py` asked the provider again for every committed instrument. Of the 789 closes in the 113 weekly files, 151 are not the provider's close for the file's date:

| What the file holds | Closes | Where |
| --- | --- | --- |
| A prior session's close, on a day the instrument traded | 6 | `US10Y`, `VIX` and `DXY` in 2026-08-28; `US2Y` in 2026-09-11, 09-18, 09-25 |
| A holiday stand-in the file does not mark | 28 | the five holiday Fridays; 2025-07-04 mixes two sessions in one file |
| A futures or dollar-index close that is not the provider's settled one | 10 | `WTI`, `SILVER`, `DXY` in 2026-09-11, 09-18, 09-25, read on the evening; `SILVER` in 2026-08-28, the December contract's settlement |
| `GOLD` that is not the provider's `GC=F` close | 107 | every week but six: 104 on a contract month the provider no longer serves, 3 read on the evening |

and `VIX` is absent from two more. The eight daily files written by the evening job are worse: 39 of their 56. The 2026-09-18 `WTI` is the 95.47 of issue #110, the November contract's last trade under a date whose settled front month was 100.30.

**Three rules, since 2026-10-05.** They are the Treasury path's (sec.1a), applied to every Yahoo instrument, and `snapshot_macro._fetch_one` is where they live.

- **The bar dated `as_of` is the observation, and a missing bar is not evidence of a holiday.** 2026-08-28.json was fetched on the Saturday at 14:10 UTC and holds Thursday's 10-year, VIX and dollar index under Friday's date. All three are the provider's index symbols, the futures in the same file are Friday's, and `macro/facts.json` generated later that Saturday has the Friday values, so the likely cause is that no usable Friday bar existed yet and the fallback took Thursday's. No bar dated `as_of` and none after it: the instrument is in `missing` with the reason. What this rule cannot stop is a bar dated `as_of` that carries the wrong day's values, which would have left the same file; no single fetch can tell, and only the audit finds it afterwards.
- **A stand-in needs proof, and is written down.** A bar dated after `as_of` shows the instrument skipped `as_of`; the last bar of the same Mon..Fri week stands in, never one from an earlier week, and its date is committed as `provenance.<block>.<ticker>.observed`. On the night itself that proof does not exist. If the equity market traded that Friday, the instrument is in `missing`, in a file that cannot be completed afterwards. If it did not, there is no file that night (sec.1c), and the instruments stand in, dated, in the one written later.
- **A bar the exchange has not settled is not a close.** `WTI`, `WTI_NEXT`, `GOLD`, `SILVER`, `US2Y_FUT` and `DXY` trade past the cash close. Until the provider loads the settlement, the bar dated `as_of` is a quote: the last trade (for a continuous symbol, which the commodities were through 2026-10-02, of whichever contract month is most active), and on a weekday evening the first trades of the *next* session. Read on the evening of the session, `WTI`, `GOLD`, `SILVER` and `DXY` were wrong in all 11 files that tried and the future in 10; read from 13:07 UTC the next day, `WTI` was right in five of five. They are not read before **13:00 UTC on the day after `as_of`**, and earlier than that they are in `missing`. `US10Y` and `VIX` are Cboe indices, final by evening, and do not wait.

**So the weekly job runs on Saturday, after 13:00 UTC.** Run on Friday night it commits a file with no commodities, no dollar index and no `US2Y_FUT`, and a weekly file cannot be completed afterwards. The daily job's two attempts, 21:45 UTC and 09:15 UTC the next morning, are both earlier than that, so it lists those six in `missing` every session (sec.4); `sector-regime-heatmap` reads `fx.DXY` from the daily files for one comparison row and shows it as missing meanwhile.

**The files written before the rules are not edited.** `macro/instrument_audit.json` lists every difference the audit found, the session each committed close actually is where it is one, and for each a cause and what was decided. `python scripts/audit_instruments.py` re-runs it against the provider and prints only what is new, changed or gone against that list; `--write` replaces the list and carries a cause forward only while its finding is unchanged.

**A correction that restates.** One file has been corrected. 2026-08-28.corrected.json replaces the three prior-session closes with Friday's (owner sign-off 2026-10-05); Cboe's own history and the Treasury par curve confirm the VIX and the 10-year, and the dollar index rests on the provider alone. A restating correction has two things the AVB one does not:

```json
"rates": { "US10Y": { "close": 4.72, "volume": null } },
"provenance": {
  "rates": { "US10Y": { "source": "yahoo-backfill", "fetched_at": "2026-10-05T04:27:45Z" } }
},
"restated": [
  { "block": "rates", "ticker": "US10Y", "was": { "close": 4.672, "volume": null } }
],
"corrects": "2026-08-28.json",
"reason": "..."
```

- **`restated` is the record of the edit**: which close, and what the base held. `scripts/rebuild_corrections.py` re-applies it to the current base only while the base still holds `was`, and otherwise aborts and fails the run.
- **The replacement is labelled.** It was fetched later than the file, so `provenance.<block>.<ticker>` carries its own `fetched_at`; the file-level stamp goes on describing everything that was not restated.
- `scripts/restate_instruments.py --date <as_of> --instrument rates.US10Y --reason "..."` writes one, through the writer's own fetch, so a stand-in or an unsettled bar is refused there too. Only special instruments, and only replacing a close that is there: adding or dropping one is not something a rebuild can re-apply, and the gate refuses it.

**The gate.** `truth_check --feed` fails a file dated 2026-10-05 or later that carries one of the six late-settling instruments with a fetch time before 13:00 UTC on the day after its session; the file's own `fetched_at` is the evidence, so a runner still on the old writer is caught before it pushes. It fails a correction whose instrument closes differ from its base without a matching `restated` entry and label. The eleven evening files from before the rule are exempt by date and on record in the audit list.

**What this did not fix: which contract.** Reading after settlement makes the bar a settlement; it does not make it a particular contract month. Through 2026-10-02 `WTI`, `GOLD` and `SILVER` were the provider's continuous symbols, nothing in a file says which month a close belongs to, and the provider rebuilt its `GC=F` history onto the active contract in September 2026, so the panel's gold is the nearest-expiry contract through 2026-09-04 (2026-08-28 excepted) and the active one after, up to 1.7% apart. That was a decision about the instrument, as Treasury was for `US2Y`. It was made on 2026-10-05 and is sec.1d: the contract is named, and the weeks from before are answered beside the panel.

**The equity series.** The audit above stopped at the special blocks. `series` has the same habit in one writer: `scripts/backfill_weekly.py::slice_week` takes the last bar on or before the Friday, anywhere in the Mon..Fri week, and the only note it can leave is file-level, written when NO ticker has a Friday bar. It wrote the 105 backfilled files and every name merged into a week afterwards (`provenance.series`): 34,980 of the 38,161 equity bars in the panel's 115 files, the two corrections counted as files of their own because they are what readers see. `scan_pipeline/scripts/backfill_weekly.py`, the mirror nothing invokes, has the same function. A ticker with no Friday bar -- halted, delisted mid-week, a gap at the provider -- got an earlier session's close under the Friday date with nothing to show it. The Friday job does not do this: `snapshot.fetch_weekly_bars` takes the bar dated the file's session (the Friday, or the session a holiday file names: sec.1c) or lists the ticker in `missing`.

`scripts/audit_series.py` asked the provider about every bar (2026-10-05). It cannot ask by comparing levels. A committed close is an adjusted close as of the day it was fetched, so it is supposed to differ from a fresh fetch for every name that has paid a dividend or split since: level against level, 19,916 of the bars counted as right below would be reported wrong. Two things do not move, and each bar is asked both. Volume is never dividend-adjusted: the committed volume is the volume of one session, times any split since. And the committed close over today's adjusted close for the same session is one factor per ticker and fetch date, which the provider states itself as its `Adj Close` over its `Close` on the fetch date. A bar is the named session's when its close is that session's on that basis and its volume does not name another.

| What the file holds | Bars | Where |
| --- | --- | --- |
| The bar of the session the file names | 34,774 | 33,122 the Friday's; 1,652 the Thursday's in the five holiday files, which say so in `session_note` |
| An earlier session's close under the Friday date | 1 | `EA` in 2026-08-07.json: 209.70 on volume 0. It is EA's close of Tuesday 2026-08-04, its last session before it was taken private |
| Cannot be checked | 205 | `AVB` (104 weeks) and `EA` (101). The provider keeps one bar of a delisted symbol, the last. The owner's spreadsheet agrees with 50 of the AVB bars, session by session; nothing covers the other 155 |

So it happened once, to a name on its way out of the market. "None found" among the rest is worth what the audit could have found, and it measures that on every run: with the session before it put in place of each of the 37,947 bars that passed and have one, that session is named 37,947 times. The close alone would pass 138 of those, where the close did not change; the volume names them.

The 3,181 bars the Friday job wrote were asked the same question, because the claim that it is date-pinned is a claim about this repo's copy of the writer. One file was not written by it. On Saturday 2026-08-29 the provider's daily closes for the Friday were all null, and 2026-08-28.json was built by a one-off script on the runner that took each close from the provider's `1wk` bar. For 330 names that is the Friday close. For `AVB`, merged away ten days before, it is 68.14 from Monday 2026-08-24, with a null volume, and it is the successor's price printed under the dead symbol; the correction of that week is a full copy and carries it. Three closes in 2026-09-25.json, read at 18:14 ET on the day, are half a cent under the close the provider settled on. And 1,665 of the job's bars rest on the close alone, because the provider has revised their volume since they were read; 13 of those closed at the same price as another session of their week, and for those nothing says which of the two bars the file holds. None of the backfilled or merged bars is in that position. `macro/series_audit.json` lists all of it with causes, the way `macro/instrument_audit.json` does. It was run again on 2026-10-06, after `BTC` and `GLD` were merged into every week (sec.1, "The equity set"): 230 more merged bars, each the session its file names by close and by volume, and no finding new, changed or gone. The counts in this section are the 2026-10-05 run's. The list's own `audited` block is the later run's, and differs where the provider has revised more volumes since: 1,720 of the job's bars on the close alone, 15 of them tied.

**Who reads `series`.** Less than the files hold. `market_state.json` derives from sixteen names in it and no others: `SPY`, `QQQ`, `DIA`, `IWM` and the twelve sector ETFs. All 1,824 of their bars are the named session's. `sector-regime-heatmap` reads three files a run (the end week, and one and four weeks back) for the focus set and `SPY`; none of the focus set's 12,439 bars is a wrong session, and `AVB`, in its Real Estate basket until 2026-09-21, was never scored (dropped at the end week of the first run, missing at every one after). `scripts/arena_ingest.py` and `portfolio/tracker.py` fetch their own date-pinned bars and do not open `data/weekly` at all. `scan_pipeline/panel_source.py` would read every equity in it, and is opt-in and off. No Council, Arena or portfolio book ever held `EA`, `AVB` or `EQR`. So no derived number has been wrong on this account. What was wrong is the record.

**Not decided: how a bar that is not the Friday's should be recorded.** The committed files are not edited, so for them the record is the audit list. For the next file `slice_week` writes there are two ways, and neither is in the code yet. (One half of the first no longer waits on this: since 2026-10-06 the file's session is decided by `SPY`, with proof, in both writers. Sec.1c. What is open is the ticker that did not trade on that session.)

- **`missing`, as the Friday job does.** A ticker's bar is the one dated the file's session or the ticker is listed with a reason that names its last bar. The file's session is the Friday, or on a market holiday the last session of the week, named in `session_note` as now, and decided by `SPY` as the daily feed decides it, not by whether any one ticker printed. No new key. A gap stays a gap, and every reader already handles one.
- **`provenance.series.<ticker>.observed`**, the instruments' key. Checked against `sector-regime-heatmap` at `a8363de`: `check_basis()` reads only `.source` and `anchor_of()` only `.fetched_at`, so an extra key beside them is ignored, and `truth_check --feed` already validates an `observed` under `provenance.series`. It would pass both gates today with the file's own `source` and `fetched_at`. But nothing reads it, so the heatmap would go on scoring a stand-in as a Friday close with a label nobody looks at; `provenance.series` would stop meaning "merged later"; and `merge_into_existing` rewrites the entry whole. It needs a reader before it is a record.

A close behind no volume is the other half of it. `truth_check --feed` accepts volume 0, the heatmap refuses it, and a null volume passes both.

---

## 1c. Which session a weekly file is

**Run on a market holiday, the weekly writer committed an empty panel.** `snapshot.fetch_weekly_bars` kept only bars dated the Friday. Run for 2026-07-03 (on 2026-10-05) it came back with no bars and "no bar dated 2026-07-03 in window 2026-06-23..2026-07-04" for every ticker; `write_weekly` wrote `series: {}` with no `session_note`; and `truth_check --feed` passed the file. It had not happened in production. The five holiday weeks in the panel (2025-04-18, 2025-07-04, 2026-04-03, 2026-06-19, 2026-07-03) were written by the backfill, under its own rule: the last bar of the week, noted file-level. The weekly job started on 2026-08-14 and has not yet run on a holiday. The next two are 2026-12-25 and 2027-01-01, Fridays running, and a Friday closure comes round two to four times a year.

**What a reader makes of such a week.** Measured 2026-10-05 on the committed panel cut off at 2026-07-31, with 2026-07-03 as it is committed, as the writer would have left it, and absent; `sector-regime-heatmap` at its `a8363de`.

| | `series: {}` | No file |
| --- | --- | --- |
| `market_state.json` that week | `as_of` the holiday, every index and sector field `null` | stays at the Friday before, whole |
| `market_state.json` afterwards | `d1w` null the week after, `corr_spy_4w` null for four weeks, `d4w` null at the fourth | the same, until the week is written |
| The heatmap that week | every sector scored on 0 constituents, `SPY` missing | `stage_run` refuses a research snapshot more than 7 days past the newest close, and the Monday snapshot is 10 (read from its code, not run) |
| The heatmap afterwards | 0 constituents again one week on (the week window) and four weeks on (the month window) | **reads its windows by position, so the week after a missing one is scored over two weeks and called one.** Communication Services against `SPY`: +0.733 where the week itself was -1.276, 10 of 10 constituents, no warning |

An empty file is the worst of the three, and a week that was refused has to be written before the next one lands.

**The rule, since 2026-10-06** (owner decision 2026-10-05: nothing until proven, and the weekly job comes back for the week). It is sec.1a's and sec.1b's, with `SPY` as the witness for the whole equity panel, as it is for the daily feed (sec.4). `snapshot.week_session` is where it lives; `fetch_weekly_bars` asks it first and `write_weekly` enforces it, and since everything that starts a weekly file goes through `write_weekly` there is no way round. (`--merge` and the correction tools write files too, but only for a week that already has one.)

- **`SPY`'s bar dated `as_of` is the session, and a missing bar is not evidence of a holiday.** On Saturday 2026-08-29 the provider's daily closes for an ordinary Friday were all null, and 2026-08-28.json exists only because a one-off script on the runner built it from `1wk` bars (sec.1b). No `SPY` bar dated `as_of` and none after it: **no file.** `write_weekly` raises `NoSessionWitness` and writes nothing. Not an empty `series`, and not Thursday's.
- **A stand-in needs proof, and is written down.** An `SPY` bar dated after `as_of` shows the Friday was skipped, and the last session of the same Mon..Fri week stands in, never one from an earlier week. Every ticker's bar is then the one dated that session, a ticker without one is in `missing`, and the file says which session it holds: `"session_note": "Friday holiday; bars from 2026-12-24"`. That is the note the five backfilled holiday weeks already carry and `scripts/audit_series.py` already reads the date out of, so it is not a new key and its form is fixed.
- **The proof is checked against the provider's own listing.** A later bar proves a holiday only if the Friday really has no row, and the bars the writers read cannot say: a session whose close has not been posted has a row with a null close, and a row with no close is no bar to any reader here, exactly like a day that never traded. Left there, a Friday that traded, re-run on the Monday while its close was still null, would go in as Thursday's bars under a holiday note. So before an earlier session stands in, the writer asks the raw chart for that row, as the daily feed does (sec.4). A holiday is not listed there (checked for 2026-07-03, Labor Day 2026 and Christmas 2025). A session with a null close is: at 00:07 UTC on 2026-10-06 the raw chart, and yfinance with it, showed the row for 2026-10-05 with its volume and no close. That Friday is refused however many bars follow it; so is one the listing cannot be asked about.
- **On the night the proof does not exist.** The job runs on the Saturday and `SPY`'s next bar is Monday's, so a holiday week is never written by the run that first meets it. It is written by the first run after a later session, and it is written whole. That is the reason to refuse rather than write the equities at once on the strength of an exchange calendar: the instruments cannot stand in that night under sec.1b, and a weekly file cannot be completed afterwards. None of the eight printed on Christmas Day 2025 or New Year's Day 2026, so on 2026-12-25 and 2027-01-01 a file written that night would have empty `rates`, `vol`, `commodities` and `fx` for good.

2026-07-03 as the writer answers it now (run 2026-10-05 into a scratch directory; that week has its file and it is not replaced). One session throughout, each instrument saying so for itself:

```json
{
  "as_of": "2026-07-03",
  "source": "yahoo",
  "fetched_at": "2026-10-05T22:44:49Z",
  "session": "close",
  "session_note": "Friday holiday; bars from 2026-07-02",
  "series": { "SPY": { "close": 742.9352, "volume": 57447800 } },
  "rates": { "US10Y": { "close": 4.485, "volume": null }, "US2Y": { "close": 4.14, "volume": null } },
  "vol":   { "VIX": { "close": 16.15, "volume": null } },
  "provenance": {
    "rates": {
      "US10Y": { "source": "yahoo",    "fetched_at": "2026-10-05T22:44:30Z", "observed": "2026-07-02" },
      "US2Y":  { "source": "treasury", "fetched_at": "2026-10-05T22:44:48Z", "observed": "2026-07-02" }
    },
    "vol": { "VIX": { "source": "yahoo", "fetched_at": "2026-10-05T22:44:48Z", "observed": "2026-07-02" } }
  },
  "missing": []
}
```

Its `SPY` volume is the committed file's to the share. Its close is not, 742.9352 against 744.78: the two were fetched eight weeks apart and each is adjusted to its own fetch date (sec.1b, "The equity series").

**Who comes back for it.** A refusal is a correct outcome, so nothing fails on the night and nothing asks again by itself. The daily feed lost eight sessions that way with every run green (sec.4). Two things do the asking.

- **The weekly job writes every Friday the panel owes a file for, oldest first, and stops at the first one refused.** `snapshot.unwritten_fridays` is the list. 2026-12-25 is written on 2027-01-02, from the 24th; 2027-01-01 on 2027-01-09, from the 31st, and then 2027-01-08 itself. A run that wrote more than one week, or none, derives `market_state.json` through the chain (`snapshot.write_market_state_chain`) or leaves it alone: the committed state is "last week's" only after exactly one new week, and handed any other the deriver takes `corr_prev` from the wrong week and `truth_check --derive` fails the file.
- **`truth_check --feed` fails when a Friday between two weekly files has no file**, which is a job that went on past a week it had refused, and warns from the Sunday while the newest Friday is still owed one. It cannot tell a refusal from a job that did not run; either way the next run writes the oldest first.

Until then every reader has last week's `market_state.json`, dated as what it is. The holiday week's sessions are in `data/daily/` from the evening of each (sec.4), which is not a reason to splice them into a weekly calculation.

**The gate.** `truth_check --feed` fails a file whose `series` is empty, whatever its date, and a file dated 2026-10-06 or later that holds no `SPY` bar. That is what a runner still on the old writer produces on a holiday, and the job stops on it before it pushes. It fails a `session_note` that is not `Friday holiday; bars from <date>` with an earlier day of the same week. One committed file predates the witness rule and has no `SPY`: 2024-08-09.json was started by a backfill run restricted to 44 names, had 270 more merged in, and never got the four index or twelve sector ETFs, none of which it lists in `missing`. Nothing current derives from that week. It is warned about, not failed and not edited; a `--merge` backfill of the sixteen names is what adds them.

**The backfill writer.** `scripts/backfill_weekly.py` decided "holiday" from its own slices, by no ticker having a Friday bar, which is just as true of a Friday the provider has not posted: run on the night, it wrote Thursday's bars under a `session_note`. It asks the witness's history now, under the same rule and with the same check against the listing, and refuses the week otherwise (exit 2, which stops the workflow before its commit step); its download runs eight days past the last Friday so that a later bar is in it. A run restricted with `--only` can no longer start a week, whether or not `SPY` is among the names, which is how 2024-08-09.json came to be: `--only` adds to weeks that exist and is refused for one that does not. And each ticker's slice now stops at the file's session, so a file that says "bars from Thursday" holds nothing dated after it. What it still does not do is hold each ticker to that session: `slice_week` itself is unchanged, a ticker with no bar on the session still gets its last one before it, and that is the open question of sec.1b. `scan_pipeline/scripts/backfill_weekly.py`, the mirror nothing invokes, is unchanged too. It reaches `write_weekly` like everything else, so it cannot write a file without `SPY`, and it can still call an unposted Friday a holiday.

**Outside this repo, by hand.** The weekly job is a scheduled agent running the runner's copy of `scan_pipeline/`. Until that copy is synced it writes the empty file on a holiday, and the gate, fetched fresh, stops it there. And its prompt asks for the most recent Friday only: the catch-up above has to be put into the task and its task card, or the first Saturday after a refused week ends at the gate's FAIL instead of at a written file.

---

## 1d. `WTI`, `GOLD`, `SILVER` and `data/commodity_settlements.json`

**They are named contracts, and for 113 weeks nothing said which.** Through 2026-10-02 the feed committed the provider's continuous symbols under these keys: `CL=F`, `GC=F`, `SI=F`. A continuous symbol is the provider's choice of which contract month to show, and the provider does not hold it still.

| Symbol | Its settled history | Its live quote | What that put in the panel |
| --- | --- | --- | --- |
| `GC=F` | The nearest-expiry contract when the panel was backfilled on 2026-08-12 (median committed volume 491 contracts). The active contract now, for the whole history (median 185,701) | The active contract | 107 of 113 weeks no longer equal `GC=F`: lower by the carry between the two months, up to 59.00 or 1.7%. 2026-08-28 and 2026-10-02 hold December's settlement instead |
| `SI=F` | Still the nearest-expiry contract | The active contract, December | 2026-08-28 holds December's settlement, 67.786, where the history has 66.995. The three evening files hold December's last trade |
| `CL=F` | The front month, through its last trade date | Moves to the next month some days earlier | 2026-09-18 holds 95.47, November's last trade, where October settled 100.30 (issue #110) |

The gold rebuild can be dated from the repo's own files. 2026-09-04.json, read on Saturday 2026-09-05 at 14:05 UTC, has 4429.80 on 16 contracts, the September contract. `macro/facts.json` for the same Friday (generated 2026-09-05, committed the next day) has 4476.60 from the same symbol, which is December.

Three more findings of 2026-10-05, none of which a rule about *when* to read can fix:

- **Reading after the settlement does not pick the month.** 2026-08-28.json was read at 14:10 UTC on the Saturday, an hour past the rule of sec.1b, and got December for gold and for silver, where the Saturday reads before and after it (2026-08-22, 2026-09-05) got the nearest contract.
- **`GC=F`'s roll day is not constant.** On the first-notice-day Fridays 2024-11-29, 2025-01-31 and 2025-05-30 its close is the outgoing month's. On 2025-11-28, 2026-01-30, 2026-05-29 and 2026-07-31 it is the incoming month's.
- **Volume is not a tell.** On a contract's last day the continuous bar is the expiring month's close beside the next month's volume: `CL=F` for 2026-09-22 is 94.59 on 422,683, and 422,683 is `CLX26`'s volume that day. The provider also shows one volume for both 2026-10-01 and 2026-10-02 on every contract probed.

**The decision (owner, 2026-10-05): the nearest-expiry contract, read by name.** The individual contracts do not move. `GCV26.CMX` is the October 2026 gold contract on every request, with history back to its listing. So the writer reads the contract and commits its name, and the rule for which contract is one line: *the listed contract with the earliest last trade date on or after the session.* It is held through its last trade date and replaced the next session.

| Key | Product | Which contract | Read as, on 2026-10-09 | Last trade date |
| --- | --- | --- | --- | --- |
| `WTI` | NYMEX light sweet crude, `CL` | The front month | `CLX26.NYM` | The third business day before the 25th of the month before the contract month; before the business day preceding the 25th, when the 25th is not one |
| `WTI_NEXT` | The same | The month after `WTI`'s | `CLZ26.NYM` | |
| `GOLD` | COMEX gold, `GC` | The spot month | `GCV26.CMX` | The third last business day of the contract month |
| `SILVER` | COMEX silver, `SI` | The spot month | `SIV26.CMX` | The same |

That rule is what 327 of the 339 committed closes already follow (`WTI` 110 of 113, `SILVER` 109, `GOLD` 108), and for crude it is EIA's definition of "Contract 1". For the metals the alternative was the active month, December now, which is the number in a headline. It was not chosen, for four reasons:

- **The spot month is the price of the metal.** It is deliverable now, so it sits within days of carry of spot. The active month sits up to four months of carry above it and steps at each of five rolls a year: in the week to 2025-08-01 the active series rose 1.9% and the spot month 0.4%.
- **Its closes are settlements, thin as it is.** On the 91 committed gold weeks that are ten days or more from the active month's first notice day, the gap to the active contract implies a carry of 3.3 to 5.9% a year, in step with short rates, including the weeks that traded 2, 12 and 16 contracts. A stale last trade would scatter.
- **It is what the panel holds.** Choosing the active month would have meant replacing 111 gold weeks from the series the provider rebuilt, with no contract name to check any week before 2026-07-31 against.
- **Silver could not follow.** The provider's `SI=F` history is the spot month and the expired active months return nothing, so an active-month `SILVER` would have begun on 2026-09-04.

`WTI_NEXT` exists for one calculation, the one-week change in a week the front month changes (sec.2). Crude stops trading a month before delivery, so its front month and the next are claims a month apart: 100.30 against 96.08 on 2026-09-18. The metals need no second contract. Both of their spot months are deliverable, and the step from one to the next is a few days of carry.

**The roll calendar** is `snapshot_macro.last_trade_date` and `contract_for`: the rulebook dates above, counted in business days of the exchange. That is not the bond market's calendar. Columbus Day and Veterans Day are ordinary sessions; Good Friday is not. It reproduces what the provider's chains did: all 32 crude expiries from `CLH24` to `CLV26` show in `CL=F`'s volume, which collapses for two sessions and then carries the next month's on the last day; by name, `CLQ26.NYM`'s last bar is 2026-07-21, `CL=F` becomes `CLX26` on 2026-09-23 and `SI=F` becomes `SIV26` on 2026-09-29; and in the committed panel, 13 of the 14 Fridays one or two sessions ahead of a crude last trade date are the only weeks with `WTI` under 130,000 contracts, and the 14th is 2026-09-18, which holds November's quote. One entry in the holiday table is a judgment: New Year's Day on a Saturday is not observed on the Friday, which next matters in 2028. If the table is ever a day out, a file is still right about itself, because the contract that was read is the one it names.

**What a file says.** Each commodity is named in `provenance.commodities` (sec.1, where an ordinary week is shown):

```json
"commodities": { "GOLD": { "close": 4133.7002, "volume": 348 } },
"provenance": {
  "commodities": { "GOLD": { "source": "yahoo", "fetched_at": "2026-10-10T13:20:10Z", "contract": "GCV26" } }
}
```

`contract` is the exchange's own name for the month: product, month letter, two-digit year. A stand-in for a holiday carries `observed` beside it and stays inside one contract: if the week's last session belongs to another month than the date asked for, nothing stands in. **This label is load-bearing**, as the Treasury one is. A commodity with no `contract` is a continuous symbol's bar of a month nobody named, and it is every file through 2026-10-02.

**Does `sector-regime-heatmap` read any of this? No, checked 2026-10-05 against its `a8363de`.** Its comparison rows are `series.GLD`, `fx.DXY` and `series.BTC` (`src/macro_comparisons.py`), and it says why: the `commodities` block carries a gold futures close, which is a different instrument from the one it shows. Nothing in that repo reads `commodities` or `provenance.commodities`. It checks the file-level `source` and each `provenance.series` source, and it globs `data/weekly/*.json`, so a label under `provenance.commodities` and a file beside `data/weekly/` are both invisible to it. The file-level `source` is still `yahoo`: a named contract is the same provider.

**`data/commodity_settlements.json`** answers for the weeks whose own file cannot. Those files are not edited and not corrected, for the reason in sec.1a, and one more: a correction can replace a close but cannot drop one, and four gold weeks have nothing to replace it with.

```json
{
  "schema": "commodity-settlements/v1",
  "rule": "nearest-expiry",
  "session": "close",
  "instruments": {
    "WTI": {
      "root": "CL", "continuous": "CL=F",
      "audited_through": "2026-10-02",
      "series": {
        "2026-09-18": { "close": 100.3, "volume": 112698, "contract": "CLV26", "symbol": "CL=F",
                        "source": "yahoo-backfill", "fetched_at": "2026-10-05T22:59:30Z",
                        "replaces": { "close": 95.47, "volume": 300567 }, "reason": "..." }
      },
      "unavailable": {}
    }
  }
}
```

- **`audited_through`** is the last week whose committed close may be read without a label. The audit of 2026-10-05 (`macro/instrument_audit.json`) is what earns that: up to this week a close with no label is the nearest-expiry contract's settlement unless it is listed below. After it, a close with no label is a month nobody checked and is never read.
- **`series`** supersedes a committed close, or supplies one a file lacks. It is keyed by the weekly file's `as_of`, and an entry for a week with no file is refused. `replaces` is what the file holds. `symbol` is the provider symbol that answered: a contract, or a continuous symbol where the contract had expired, in which case `contract` is the month the calendar gives and could not be confirmed by name.
- **`unavailable`** is a week with no settlement of the rule's contract to be had, with the reason and the evidence. It is a gap that is declared, like `missing`.
- **Append-only.** An entry on file stays as it is, and so does `audited_through`: moving it re-admits or drops committed closes for every reader at once. CI compares the file with the previous commit, with the same limits as the check beside it (sec.1a). `backfill_commodities.py --check` asks the provider again and reports a difference without writing; a continuous symbol that has since moved is the thing this file exists to survive.

Twelve closes were off the rule, in five weeks. `WTI_NEXT` has no history: no file written before contracts were named carries it.

| Week | `WTI` | `GOLD` | `SILVER` |
| --- | --- | --- | --- |
| 2026-08-28 | stands | none: the file holds December's settlement | 66.995, was 67.786 (December's settlement) |
| 2026-09-11 | 100.05, was 99.99 (an evening last trade) | none | 64.554, was 65.02 (December's last trade) |
| 2026-09-18 | 100.30, was 95.47 (November's last trade) | none | 66.556, was 66.785 |
| 2026-09-25 | 92.41, was 92.44, by name | none | 64.245, was 64.71 |
| 2026-10-02 | 91.11, confirmed by name | 4133.70, was 4162.30 (December), by name | 59.977, confirmed by name |

Two of the eight replacements were read by contract name (`GCV26`, `CLX26`). The other six are from `CL=F` and `SI=F`, whose settled history could be shown to be the nearest-expiry chain at that roll (below); their contracts, `CLV26` and `SIU26`, had expired. The four gold weeks have no settlement: the September contract expired on 2026-09-28, the provider serves nothing for it, and `GC=F` is December. The two confirmations are there so that the first week written with named contracts has a named week before it.

**Reading a commodity.** For week `d`, in this order: the weekly file's close, if `provenance.commodities` names its contract; else this file's `series` entry for `d`; else nothing, if `d` is in `unavailable`; else the weekly file's unlabelled close, if `d` is not after `audited_through`; else nothing. `snapshot.commodity_series()` is that rule and is the only reader `market_state` uses. A week's own named close wins over an entry here, and the gate fails if the two disagree. A gap derives as `null` with a `_reason`. The continuous symbols are never a fallback, in the reader or in the writer: no bar for the named contract means the instrument is in `missing`.

**Filling it.** `python scripts/backfill_commodities.py` reads by contract name, through the writer's own fetch, for any week after `audited_through` that has no named close: a Friday the fetch failed, or one written by a runner still on the old writer. It adds entries, never rewrites one, and re-derives `market_state.json`. Two things it does only when told, for one named week, with `--reason`:

- **`--from-continuous`** lets the continuous symbol answer for a contract that has expired, on proof: on every settled session in the seven days after that contract's last trade, and on at least two, the continuous symbol's close is the next contract's, read by name. That shows its history was the nearest-expiry chain at that roll, which is all that makes its earlier bar the expired month's. `CL=F` and `SI=F` pass it today. `GC=F` fails it (4179.70 on 2026-09-29 where `GCV26` settled 4147.70), which is why it cannot stand in for gold.
- **`--unavailable`** records that there is no settlement, after showing it: the provider answers with nothing for the contract, and the continuous symbol fails the proof. A provider that does not answer is not evidence, and the tool refuses.

An expired contract is the ordinary case, not the exception. The provider drops a contract within days of its last trade, so a rewrite of an old week lists its commodities in `missing`, and a Friday that *is* a last trade date is read on the Saturday, after the contract has expired: if the provider has dropped it by then, that week is `missing` and is filled here. The first such Friday is 2026-11-20 (`CLZ26`). `WTI_NEXT` is read from a contract with a month to run, so the following week's change survives it.

A holiday week is the hard case. It is written a week late, from the Thursday (sec.1c), and a spot-month metal can stop trading in between: 2026-12-25 is written on 2027-01-02, four days after `GCZ26` and `SIZ26` trade for the last time on 2026-12-29. If the provider has dropped them by then, that week has no gold settlement at all, because `GC=F` cannot stand in, and silver has one only while `SI=F` still passes the proof.

**The gate.** `truth_check --feed` validates the `contract` label (the instrument's product, and a month that can be its nearest contract on that session, which refuses December gold under `GOLD` in October) and this file (weeks that exist, `replaces` equal to what the file holds, no week both an entry and unavailable). It warns for a week after `audited_through` with no named settlement. And it fails when `market_state.json`'s `WTI`, `GOLD` or `SILVER` is not what this rule derives: `px`, `contract` and each of the four changes, by value. That is what a deriver from before 2026-10-05 gets wrong, and the Friday job runs the runner's copy. It also fails when this file is absent from a tree that derived a `market_state.json`, because the weekly job does not write it.

**What this costs, and what it does not fix.**

- **`GOLD` is not the number under `GC=F`.** On 2026-10-02 it is 4133.70 where `GC=F` shows 4162.30. `macro/facts.json` (Canary Watch) and the sector grids pull `GC=F` themselves, so the repo holds two gold numbers about 0.7% apart, each labelled, until those prompts cite the feed's contract. Their prompts are outside this repo.
- **Four gold weeks are gaps.** `GOLD`'s `d1w` is null for 2026-10-02, `d4w` for the three weeks after it, `d13w` for four weeks from 2026-11-27 and `d52w` for four in 2027.
- **A holiday session is not a settlement.** 2025-07-04.json holds `WTI` and `SILVER` from the abbreviated July 4 session; the exchange settled nothing that day. The writer still takes a bar dated `as_of` when the provider has one.
- **The daily files carry no commodity** while both attempts run before 13:00 UTC (sec.4), and this file is keyed by week.

---

## 2. `data/market_state.json`

Derived, not fetched. Overwritten every scan — this one *is* a snapshot of now, and history lives in the weekly files. Full shape is in `MARKET_GROUNDING.md` §1; the generation rules:

| Field | Computed from |
| --- | --- |
| `d1w` / `d4w` / `d13w` / `d52w` | The weekly files. Never re-fetched. |
| `pctile_2y` | Rank of the current level within the trailing 104 weekly files |
| `corr_spy_4w` | Trailing 4 weekly returns vs SPY's |
| `corr_prev` | The same figure from last week's `market_state.json` |
| `rates.US2Y`, `curve_2s10s_bps` | The Treasury 2-year per sec.1a: the weekly file where it is labelled `treasury`, else `us2y_treasury.json`. Never `US2Y_FUT`. |
| `commodities.WTI`, `.GOLD`, `.SILVER` | The nearest-expiry contract's settlements per sec.1d: the weekly file where it names the contract, else `commodity_settlements.json`. Never a close with no label from after the audit, and never a continuous symbol. |
| `commodities.*.contract` | The contract month `px` is. Null, with the reason, where the week predates named contracts and was not confirmed by name. |
| `commodities.*.px`, `d4w`, `d13w`, `d52w`, `pctile_2y` | The nearest-expiry contract on one date against the nearest-expiry contract on another: the level then and the level now. |
| `commodities.WTI.d1w` | The change in the `as_of` contract itself, from last week's `WTI` or `WTI_NEXT`, whichever is that contract. In the week the front month changes, the level comparison is mostly the spread between two months: -7.9% front to front for 2026-09-25, -3.8% on the November contract. Null where last week holds no settlement of it. `GOLD` and `SILVER` use the level: their step from one spot month to the next is a few days of carry. |
| `regime` | Rule-based, from VIX percentile + ISM + curve + policy odds |

Two rules that matter more than the contents:

- **Every field present, always.** Unavailable values are `null` with a sibling `_reason`. Never omitted.
- **Derivation is pure.** Given the weekly files, `data/us2y_treasury.json` and `data/commodity_settlements.json` (sec.1a, sec.1d; both found beside `data/weekly/`, so naming one names the others) and `macro/facts.json` (macro prints, policy fields, and the upcoming-events gate live there, not in prices), regenerating `market_state.json` produces a byte-identical file. If it doesn't, something is reading live data it shouldn't be. Enforced by `truth_check.py --derive` every Monday.

---

## 3. `data/universe.json`

Machine-readable mirror of `wiki/universe.md`. The wiki is for humans and agents; this is for the app's Universe screen.

```json
{
  "as_of": "2026-07-01",
  "next_review": "2026-10-01",
  "tickers": [
    { "t": "NVDA", "name": "NVIDIA", "sector": "Technology", "sub": "Semiconductors",
      "cap": "MEGA", "adv_usd": 28400000000,
      "added": "2024-01-06", "removed": null,
      "wiki_refs": ["wiki/technology.md", "wiki/semiconductors.md"] },
    { "t": "SYM", "name": "Symbotic", "sector": "Industrials", "sub": null,
      "cap": "MID", "adv_usd": 214000000,
      "added": "2026-05-04", "removed": null,
      "wiki_refs": [] }
  ]
}
```

`wiki_refs` is the whole point — **an empty array is the naked-signal flag.** The app's NAKED count is `tickers.filter(t => !t.removed && !t.wiki_refs.length).length`, not a hand-maintained number. Generate `wiki_refs` by grepping the wikis for each ticker at build time so it cannot drift from reality.

Removed tickers stay in the array with a `removed` date and a `removed_reason`. The Universe screen's EXITED state reads them.

---

## 4. `data/daily/<YYYY-MM-DD>.json`

One file per **completed US trading session**, same shape as sec.1 plus a
`cadence` discriminator. Append-only, never edited, same correction rule.

```json
{
  "as_of": "2026-09-10",
  "cadence": "daily",
  "source": "yahoo-daily",
  "fetched_at": "2026-09-12T01:44:10Z",
  "session": "close",
  "series": { "SPY": { "close": 771.02, "volume": 41233100 } },
  "rates": {}, "vol": {}, "commodities": {}, "fx": {},
  "missing": [ { "ticker": "AVB", "reason": "no bar dated 2026-09-10 ..." } ]
}
```

**Why this exists.** The weekly files commit Friday closes because that is the
cadence the council reads. The bars behind them were never weekly --
`snapshot.fetch_session_bars`, under both feeds, downloads daily bars over a
ranged window and keeps one. This file keeps the other four sessions instead
of discarding them.

**Rules.** Everything in sec.1 applies unchanged: closes only, `missing`
required and never empty-by-omission, `fetched_at` real UTC and the adjustment
anchor, never edit, corrections as `<date>.corrected.json`. Two differences:

- **`cadence` is required and is `"daily"`.** It is the discriminator that
  stops a consumer treating this file as the weekly feed.
- **`source` is `"yahoo-daily"`.** Same provider and same basis as the weekly
  feed (yfinance `auto_adjust=True`, total-return); the distinct label records
  provenance so a downstream basis check cannot silently conflate the two.

`rates.US2Y` follows sec.1a here too. The daily files that carry rates at all
(2026-09-11 to 2026-09-23; the bootstrap files before them have empty blocks)
hold the 2YY=F future under that key. Later ones hold the Treasury 2-year and
say so in `provenance.rates`, or list `US2Y` in `missing` when Treasury had no
row for that session at run time: the day's curve was not posted yet, or the
bond market was closed. The daily files are not backfilled: nothing derives
from their rates, and `data/us2y_treasury.json` is keyed by week.

Sec.1b applies here too, and bites harder. Neither of the daily job's two
attempts is late enough: 21:45 UTC and 09:15 UTC the next morning are both
before the 13:00 UTC at which `WTI`, `WTI_NEXT`, `GOLD`, `SILVER`, `DXY` and
`US2Y_FUT` may be read, so a daily file written since 2026-10-05 lists all
of them in `missing` with the reason, whichever attempt wrote it. The eight files from
2026-09-11 to 2026-09-23 hold them anyway, and on the six that are not
Fridays the number is the first ninety minutes of the *next* session (`WTI`
on a volume of 593 to 2,923; 89.63 against a settled 94.59 on 2026-09-22).
`US10Y` and `VIX` in those files are right. An attempt after 13:00 UTC, with
no evening write ahead of it, would bring them back, each commodity naming
its contract as a weekly file does (sec.1d). Whether 09:15 UTC
is in fact late enough is not known: no committed read falls between 02:58
and 13:07 UTC.

**The session-witness gate.** `scripts/daily_observe.py` refuses to write a
file unless **SPY has a bar dated exactly `as_of`**. No witness bar means the
date was not a session, or the session has not settled with the provider. A
half-formed session is indistinguishable from a settled one once committed,
so the gate is up front rather than a later lint. Holidays simply produce no
file -- 2026-09-07 (Labor Day) is absent by design, not missing.

The witness has one blind spot: while a session is open SPY already has a bar
dated today, the forming one. The clock covers it. `as_of` is chosen and
judged in **US/Eastern**, never on the runner's UTC date -- the default is the
latest weekday whose 16:00 ET close has passed -- and a date still in session
is refused before anything is fetched.

**The null-close window.** For an hour or more each evening, from 00:00 UTC
(20:00 ET in summer, the end of the post-market session) until its end-of-day
roll, the provider serves the just-closed session's row with a null close:
the row exists, with volume, and the price does not. On this feed the bar was
served through 23:59:53 UTC, was gone at 00:10 and 00:45, and was back by
01:38. That is "not settled" in the gate's sense and the run refuses; it is
the reason each session gets a second attempt the next morning. It does not
depend on the request -- the provider appends its newest row whatever `end`
says, and a null close is null on every window and range.

**Completeness.** A refusal is a correct outcome and exits clean, so a feed
that has stopped writing looks the same as one that declined once. The panel
is therefore audited against the witness on every run
(`daily_observe.py --audit`): every session the provider lists with a settled
close, from the first daily file to the last close, must have a file. A
missing one that is not the newest fails the run. A range is recovered with
`--since <first> --date <last>`, which cuts every missing session from one
ranged download, stamps them with one `fetched_at`, and leaves existing files
alone. Those files carry no rates/vol/commodities/fx; `missing` says so.

**Never splice daily and weekly files into one calculation.** They carry
different adjustment anchors and the divergence is real, not theoretical: on
2026-08-28 the weekly file (anchor 2026-08-29) and the daily file (anchor
2026-09-12) agree on SPY to the penny but disagree by ~1% on 57 dividend
payers, and by 50% on APH, which split 2:1 on 2026-09-03. A consumer reading
both is reading two bases. `sector-regime-heatmap` treats `data/daily/` as its
own panel for exactly this reason.

**Size.** ~20KB per session, ~252 sessions per year, ~5MB/year. Same rule as
sec.1: no pruning, no rotation, ever.

---

## 5. Not committed

| Data | Where it lives | Lifetime |
| --- | --- | --- |
| Intraday quotes | App-side cache | Minutes |
| Live P&L during an open week | App-side cache | Until Friday close |
| Arena lock-time prices | Server, written into the entry record | Permanent, but in the entry — not as a price file |

Rule of thumb: **if it will be different in an hour, it does not go in git.**

---

## The backfill job

One-time, before the app ships. Turns every chart on day one instead of accumulating history slowly.

1. Take the charted ticker set (~40).
2. Pull 104 weekly closes from the provider — one call per ticker with a date range, not 104 calls.
3. Write one file per Friday, using the provider's stated close date, not a computed one.
4. Set `"source": "<provider>-backfill"` and `"fetched_at"` to the backfill run time so backfilled files are distinguishable from live ones forever.
5. Regenerate `market_state.json` from the earliest week forward and confirm the final output matches the current live one. **If it doesn't, the derivation is impure — fix that before shipping.**
6. Commit as a single labelled commit, e.g. `backfill: 104w closes, 41 tickers`.

Gaps: a ticker that did not trade for part of the window gets `null` for those weeks and an entry in `missing`. Do not interpolate. A drawn line through invented points is exactly the kind of plausible-looking fiction this project exists to avoid — the sparkline should break.

---

## Provider

**Yahoo (yfinance)** for EOD, as of launch (2026-08-11 — owner decision; the original draft named Tiingo). The scan pipeline already runs on yfinance with date-pinned fetches, so the feed inherits a proven path and needs no new key at all. Weekly cadence means EOD is sufficient.

- One provider, on the scan runner, server-side. **Nothing shipped in the app.**
- Rate limits are irrelevant at ~300 tickers a week (six batched ranged calls).
- The provider name lives in one constant (`PROVIDER` in `scan_pipeline/snapshot.py`). Switching providers must not require touching any file shape above.

**One exception (2026-10-04): the cash 2-year comes from the U.S. Treasury.** Yahoo does not carry one, and the future that stood in for it was wrong by up to 36 bp (sec.1a). The cost is real and was taken on purpose: a second host the Friday job has to reach, a second way for a run to come back incomplete, and a file whose `source` no longer covers every number in it. It is contained three ways.

- **One instrument, named in one place.** `INSTRUMENTS` in `scan_pipeline/snapshot_macro.py` marks `US2Y` as Treasury's, and `TREASURY_SOURCE` sits beside `PROVIDER`. Everything else is still Yahoo, and a test fails if a second exception appears.
- **The file says which number is whose.** `provenance.rates.US2Y` names `treasury`; the file-level `source` stays `yahoo` and stays true for everything it claims.
- **A Treasury failure costs one number.** `US2Y` goes to `missing` for that week with the reason. The equity panel is unaffected, the future is never substituted, and the week is filled later from Treasury's archive (sec.1a).

No key is needed, nothing ships in the app, and a provider swap for the equities is still one constant.

**No second publisher for the commodities (2026-10-05).** Naming the contract did not need one: `CLX26.NYM` is Yahoo's, read through the same accessor, and the file-level `source` covers it (sec.1d). A settlement series from another publisher was looked at, and there is no Treasury among them. EIA's NYMEX futures series ended on 2024-04-05. Its WTI spot series is a different instrument (85.23 on 2026-09-25, where the futures settled 92.41), and Friday's value is published the following Wednesday, so it could never be in the Saturday file. CME and LBMA, who publish the settlements and the London benchmarks, refused a script on 2026-10-05 (connection reset, HTTP 403); their redistribution terms were not read, and a public repository would have to. Another vendor's continuous series is the same ambiguity under a second name.

If a provider swap ever happens (Tiingo remains the designated successor), keep the old files as they are — `"source"` records who said what, and re-fetching history from a new provider to overwrite committed observations would be rewriting the record.

---

## What the app reads

| Screen | File |
| --- | --- |
| Sector sparklines | last 13 `data/weekly/*.json` |
| 24-week return strip | `portfolio/history` + the weekly files |
| Correlation slopes | `market_state.json` (`corr_spy_4w`, `corr_prev`) |
| Brief stat pair | `market_state.json` |
| Universe screen | `universe.json` |
| Agent context | `market_state.json` + last 4 weekly files |

All of it over the GitHub contents API, cached locally on the device. **No market-data vendor in the mobile client at all** — one key, one place, and every chart is provably the same data the council reasoned from.

---

## Checklist

- [x] Ticker set agreed (full 277-name universe + indexes + sector ETFs + rates/VIX/commodities/DXY — amended 2026-08-11) and written down where the scan reads it (`scan_pipeline/snapshot.py::equity_universe` + `snapshot_macro.INSTRUMENTS`)
- [x] `series` commits `PRICE_FEED_UNIVERSE` and the sixteen ETFs through one function, `snapshot.equity_universe()`; `BTC` and `GLD` merged into all 113 weeks; `truth_check --config` holds the writer and the newest weekly file to every name (2026-10-06, sec.1, "The equity set")
- [ ] Runner's `scan_pipeline/snapshot.py` synced, so the Saturday build fetches `BTC` and `GLD` (sec.1, "The equity set")
- [ ] Whether `BNY`, `MRSH`, `DOC` and `VMRK` are merged into the weeks before 2026-09-25 decided (sec.1, "The equity set")
- [x] `data/weekly/<date>.json` writer in the scan, with `missing` populated
- [x] Correction-file path handled by readers (prefer `.corrected.json`)
- [x] `market_state.json` generator, pure, reproducible from weekly files + `macro/facts.json`
- [x] `universe.json` generator with `wiki_refs` grepped from the wikis
- [x] Backfill run, 104 weeks (2024-08-16 → 2026-08-07), labelled commit
- [x] Provider on the runner only; nothing reachable from any client build (Yahoo needs no key at all)
- [x] Purity check: `truth_check.py --derive` regenerates `market_state.json` from scratch and diffs against live (wired into the Monday gate)
- [x] Cash 2-year from the Treasury par curve, labelled per instrument; the 113 futures-era weeks covered by `data/us2y_treasury.json` (2026-10-04, sec.1a)
- [x] Every instrument close is the bar dated `as_of`, a recorded stand-in, or `missing`; nothing unsettled is read; the files from before are audited in `macro/instrument_audit.json` (2026-10-05, sec.1b)
- [ ] Weekly job moved from Friday 9:13 PM ET to Saturday after 13:00 UTC, and the runner's `scan_pipeline/` synced, so the file still carries commodities and the dollar index (sec.1b)
- [x] Contract month and roll rule for `WTI` / `GOLD` / `SILVER` decided: the nearest-expiry contract, named per close; the weeks from before answered by `data/commodity_settlements.json` (2026-10-05, sec.1d)
- [ ] Runner's `scan_pipeline/` synced and `data/commodity_settlements.json` copied beside its `data/weekly/`, before the first Saturday run that names contracts (sec.1d, "The gate")
- [ ] `macro/facts.json` and the sector grids cite the feed's contract for gold instead of `GC=F` (sec.1d, "What this costs")
- [x] Every committed equity bar asked which session it is; the answers are in `macro/series_audit.json` (2026-10-05, sec.1b, "The equity series")
- [ ] How an equity bar that is not the Friday's is recorded decided, and `slice_week` changed to match in both copies of `backfill_weekly.py` (sec.1b, "Not decided")
- [x] A weekly file is written only with its session witness: `SPY`'s bar dated `as_of`, or a proven, named stand-in; no witness, no file; `truth_check --feed` fails an empty `series` and a week missing between two files (2026-10-06, sec.1c)
- [ ] The weekly job's prompt and task card changed to write every Friday the panel owes, oldest first, and the runner's `scan_pipeline/` synced (sec.1c, "Outside this repo")
- [ ] The sixteen index and sector ETFs merged into 2024-08-09.json (sec.1c, "The gate")
