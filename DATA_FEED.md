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

**Rules**

- **Closes only.** No intraday, no bid/ask, no derived fields. This file is an observation.
- **`missing` is required and never empty-by-omission.** A ticker that could not be fetched is listed with a reason. A silently absent ticker is indistinguishable from a ticker that didn't exist, and that ambiguity is what the agents fill in from priors.
- **`fetched_at` is UTC and real.** It is how you detect a scan that ran against a stale cache.
- **Never edit.** If a provider restates, write `<date>.corrected.json` with the same shape plus `"corrects": "2026-08-08.json"` and `"reason": "..."`. Readers prefer the correction; the original stays.
- **`provenance` is optional and records per-series anchors.** Adding a ticker to a past week (a targeted backfill) fetches it *now*, so its adjusted closes are back-adjusted to a different date than the rest of the file. The file-level `source` / `fetched_at` still describe the majority of the series and are never restamped by a merge -- restamping would relabel every untouched series with a fetch that never happened to it. The added names are listed individually instead:

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
- **`provenance.<block>` names an instrument that did not come from the file's provider.** The file-level `source` stays `yahoo`: it describes every series and every other instrument, and `sector-regime-heatmap` refuses a week whose file-level source it does not know. The one instrument Yahoo cannot supply says so beside itself (amended 2026-10-04):

```json
"rates": {
  "US10Y":    { "close": 5.277, "volume": null },
  "US2Y":     { "close": 4.83,  "volume": null },
  "US2Y_FUT": { "close": 4.635, "volume": null }
},
"provenance": {
  "rates": { "US2Y": { "source": "treasury", "fetched_at": "2026-10-10T01:13:42Z" } }
}
```

  `<block>` is one of `rates`, `vol`, `commodities`, `fx`; today only `rates.US2Y` is ever named. An instrument absent from `provenance.<block>` carries the file-level `source`. Every key must exist in its block. `observed` is added when the value was published for an earlier day of the same week: Treasury skipped `as_of`, and a later row proves it (sec.1a, "The fetch"). The Friday job never writes it, because that proof does not exist on the night; a later rewrite of a holiday week does. `write_weekly` is the only writer, from what `snapshot_macro.fetch_special_instruments` reports.

  **This label is load-bearing.** It is the only thing that separates a Treasury 2-year from the futures mark that every earlier file holds under the same key (sec.1a). A reader that ignores it differences two instruments.

**Size.** ~300 series entries + 8 instruments ≈ 15–18KB per file. 104 files per two years ≈ 1.7MB. No pruning, no rotation, ever.

**Ticker set (amended 2026-08-11, owner decision — supersedes the original charted-set-only text).** The FULL scan universe is committed: every ticker in `STOCK_UNIVERSE` (277; 274 after the 2026-09-21 out-of-cycle review, see wiki/universe.md) plus SPY, QQQ, DIA, IWM, SMH and the 11 sector ETFs in `series`; US10Y/US2Y/US2Y_FUT in `rates`; VIX in `vol`; WTI/GOLD/SILVER in `commodities`; DXY in `fx`. Rationale: the pipeline already fetches the whole universe at scan time, so the marginal cost is zero, and the file becomes the complete record of what the Council could have seen — not just what the app happened to chart. Instrument notes: US2Y is the U.S. Treasury par yield curve 2-year (column `2 Yr`), the one instrument that is not Yahoo's, named as such in `provenance.rates` (amended 2026-10-04; through 2026-10-02 this key held the 2YY=F future, see sec.1a); US2Y_FUT is that future, kept under a name that says what it is and never a stand-in for US2Y; US10Y is ^TNX, which current Yahoo serves as a plain yield (a legacy ×10 guard divides only if a raw value >20 ever appears); volumes are null for indexes/rates, never invented.

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

**The fetch.** One CSV per calendar year, columns read by name (the 2024 file has no `1.5 Month` column, so `2 Yr` moves). The row dated `as_of` is the observation, and a missing row is not evidence of a holiday: if Treasury posts late or a stale copy comes back, the row on top is yesterday's, and the Friday job always runs after the day has ended, so no clock can tell the two apart. No row dated `as_of` therefore means `US2Y` goes to `missing` with the reason. Another day stands in only on proof: when the file already holds a row dated after `as_of`, Treasury skipped that day, and the last row of the same Mon..Fri week is used with `observed` recording which. That proof never exists on the night itself. So a holiday Friday is always a gap in its own weekly file and is filled afterwards by `backfill_us2y.py`, once the next session's row is up; until then `market_state` shows the 2-year as `null`. Daily files follow the same rule.

**The gate.** `truth_check --feed` fails when `market_state.json` shows a `US2Y` level that is not the Treasury 2-year for its week, or anything but `null` where none exists. Three weekly syntheses found this defect by reading two files side by side; nothing mechanical did. It also fails when the weekly change or the percentile is `null` although the values it needs are in the tree, and when `us2y_treasury.json` is absent from a tree where `market_state.json` was derived. Those are the two ways a runner gets this wrong: the Friday job runs its own copy of `scan_pipeline/` against its own copy of `data/`, and it does not write the history file, so both have to be put there by hand. That job fetches `truth_check.py` fresh and stops on a FAIL, so either mistake is caught before it pushes. `python scripts/rederive_market_state.py` regenerates `market_state.json` through the whole chain when an input changed outside the weekly job.

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
| `regime` | Rule-based, from VIX percentile + ISM + curve + policy odds |

Two rules that matter more than the contents:

- **Every field present, always.** Unavailable values are `null` with a sibling `_reason`. Never omitted.
- **Derivation is pure.** Given the weekly files, `data/us2y_treasury.json` (sec.1a; found beside `data/weekly/`, so naming one names the other) and `macro/facts.json` (macro prints, policy fields, and the upcoming-events gate live there, not in prices), regenerating `market_state.json` produces a byte-identical file. If it doesn't, something is reading live data it shouldn't be. Enforced by `truth_check.py --derive` every Monday.

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
`snapshot.fetch_weekly_bars` downloads daily bars over a ranged window and
keeps one. This file keeps the other four sessions instead of discarding them.

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
- [x] `data/weekly/<date>.json` writer in the scan, with `missing` populated
- [x] Correction-file path handled by readers (prefer `.corrected.json`)
- [x] `market_state.json` generator, pure, reproducible from weekly files + `macro/facts.json`
- [x] `universe.json` generator with `wiki_refs` grepped from the wikis
- [x] Backfill run, 104 weeks (2024-08-16 → 2026-08-07), labelled commit
- [x] Provider on the runner only; nothing reachable from any client build (Yahoo needs no key at all)
- [x] Purity check: `truth_check.py --derive` regenerates `market_state.json` from scratch and diffs against live (wired into the Monday gate)
- [x] Cash 2-year from the Treasury par curve, labelled per instrument; the 113 futures-era weeks covered by `data/us2y_treasury.json` (2026-10-04, sec.1a)
