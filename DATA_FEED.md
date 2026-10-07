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
- **`missing` is required and never empty-by-omission.** A ticker that could not be fetched is listed with a reason. A silently absent ticker is indistinguishable from a ticker that didn't exist, and that ambiguity is what the agents fill in from priors. A file is valid in itself without a name that is simply not there, so `truth_check --feed` asks the panel: it warns when a week has neither a bar nor a `missing` entry for one of the sixteen index and sector ETFs, or for a name with a bar in an earlier and in a later week (sec.1c, "A name left out"). It also reads the list itself (2026-10-06): `missing` is a list of `{"ticker": <name>, "reason": <why>}` entries, both strings that say something, and anything else is a FAIL, in every weekly and daily file, bases and corrections, with no date before which a file is excused: every entry committed that day is well-formed and no writer here produces anything else. An entry with no reason records nothing, and it is read: `sector-regime-heatmap` prints the reason on its daily tape, and `scripts/rebuild_corrections.py` and `backfill_weekly.py --merge` end in a traceback on an entry that is not an object. It accounts for no name either. The gate's checks that ask whether a name has a bar or an entry (the names rule and `--config` for the newest week, the panel check above for the rest) read it as no entry, so a name typed in with nothing beside it, the cheapest way past them, fails under its own line and under theirs. The text `None` is not a reason: both writers pass the field through `str()`, and that is what an entry that reached them without one is committed as. The FAIL stops whatever ran the gate: the weekly job, and the Monday Council's fallback build, before the push; the daily job before its commit, so no session is committed while one stands on main; the backfill before its commit; and CI. It has to stop there, because little clears it afterwards. A base is never edited. A `--merge` backfill that finds a bar for the name an entry lists puts the bar in its place, and one that finds none leaves the entry as it is. A correction cannot carry a repair of its base's list, which `rebuild_corrections.py` copies. Past that the repair is the owner's to decide, and the failure line says so; it also says to look at main first, since on the runner the file may be a copy of one main already holds. What the rule cannot catch is a typed entry that does give a reason; it reads like the writer's own, and the names rule's failure line says not to write one ("Where the week is written", below).
- **`fetched_at` is UTC and real.** It is how you detect a scan that ran against a stale cache.
- **Never edit.** If a provider restates, write `<date>.corrected.json` with the same shape plus `"corrects": "2026-08-08.json"` and `"reason": "..."`. Readers prefer the correction; the original stays. A corrected week is still one week: a reader lists weeks, not files, and reads each once, from its correction where it has one (`snapshot._load_weekly_files`; `scan_pipeline/panel_source.py` listed `*.json` for itself until 2026-10-06 and read both). A correction that *replaces* a close, rather than dropping a bar, also carries `restated`: the record of what it replaced (sec.1b).
- **What a file held, it still holds, and that is checked.** `scripts/panel_guard.py` compares the panel as it was with the panel as it is. For every file of `data/weekly` and `data/daily` that was there: the file is still there; every entry in `series`, `rates`, `vol`, `commodities` and `fx` is still there, with the same bar and the same label (its `provenance.<block>.<ticker>`, or none); and the file's `source`, `fetched_at` and `session_note` are unchanged. A file may gain entries and the panel may gain files. Values are compared, not bytes. Two things may change what a file held, and each is on record. A correction may change an instrument it newly lists in `restated` (sec.1b). A whole-universe rewrite, declared when the backfill is dispatched, may change the weekly files of the range it names, and may not remove an entry from them (CLAUDE.md, "The backfill"). The comparison runs around the backfill's write, in CI against the commit a push replaced or a pull request's base (whether or not the tests before it passed), and in the daily job before its commit. It compares a file with what that file held, so a correction that is new is not compared with its base: that its series are its base's is the test suite's to say, for `data/weekly` only. Until 2026-10-06 the check was a count of `series` per file, which does not move when a bar is written over (amended 2026-10-06). The weekly writer is held to it at the source as well: `snapshot.write_weekly` does not write a week that has its file (sec.1c, "A week is written once").
- **A close is the session's own, settled, or it is not in the file.** For `rates` / `vol` / `commodities` / `fx`: the bar dated `as_of`, or the instrument is in `missing`. An earlier session stands in only where the provider shows the instrument skipped `as_of`, and then the file says which session it is. A futures or dollar-index bar is not read until the exchange has settled it. Sec.1b has the rules and what the files written before them hold (amended 2026-10-05). `series` is held to the bar dated the file's session (sec.1c) by the weekly job, and since 2026-10-07 by the backfill writer, ticker by ticker; what it let through before is in sec.1b, "The equity series".
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

`truth_check --config` fails when `equity_universe()` leaves out a name of `PRICE_FEED_UNIVERSE`, and when the newest weekly file has neither a bar nor a `missing` entry for a name the writer fetches. So a name that joins the feed is merged into the panel in the same change, with `scripts/backfill_weekly.py --only <names> --merge`, which writes a `missing` entry where the provider has no bar. A renamed name is the one exception: the week that holds its old symbol's bar accounts for it, and that merge is refused ("One company, one symbol a week", below). One limit. It holds the newest week and no other: `BNY`, `MRSH`, `DOC` and `VMRK` joined on 2026-09-21, had bars from 2026-09-25, and for two weeks were in neither `series` nor `missing` of the 111 weeks before, with nothing failing (decided since: "Four renamed names", below). For the same reason a failure clears by itself once a later week is whole, with the hole still behind it. A week on main without a name stops more than CI. `.github/workflows/daily-observe.yml` runs `--feed --config` and the whole suite before it commits a session, so no daily file is committed until the week is merged, and the sessions skipped meanwhile are recovered by hand (sec.4, "Completeness"). A `--merge` of the names into that week is the repair.

**Where the week is written (2026-10-06).** `--config` reads the constants, and it cannot run where the weekly job runs its gate. That line is `--feed --derive`, from a check dir holding a copy of the runner's data, `macro/facts.json` and `scripts/truth_check.py` fetched fresh: no `scan_pipeline/`, and the copy within reach is the runner's own, synced by hand, which is the one in doubt. Nothing in the line knew which names a week should hold: the two builds without `BTC` and `GLD` passed it and were pushed, and so would any week from a runner whose only fault is its list of names. The gate carries the names now. `EQUITY_UNIVERSE` in `scripts/truth_check.py` is a copy of `snapshot.equity_universe()`, and `truth_check --feed` asks the newest weekly file for a bar or a `missing` entry for each. `tests/test_feed_names.py` pins the copy to the function and prints the replacement, and `--config` fails on the same difference, so a name joins or leaves both in one commit. It is the question `--config` asks of the same file, the newest week and no other, at the end of the panel that the warning of sec.1c ("A name left out") cannot judge.

**A short week, or a copy that is behind.** The runner's `data/` is synced by hand, and a name merged into a week on main does not reach its copy. So a short newest file in the job's check dir is not always a short week. It is either a week the stale writer has just written, which must not be pushed, or the runner's copy of a week main already holds whole, which must not be rewritten: opposite handling, and the gate cannot see main to tell which. Two things follow. Both of its lines tell the reader to look at main before anything else. And the rule is a FAIL only for a file fetched on or after 2026-10-06, the day it began (`NAMES_RULE_SINCE`): no run that had this check wrote an older file. On that day every weekly file on the runner was older, committed, and without `BTC` and `GLD`, which had been merged into main's copies that day; those are warned about. The date is a fact about the rule and does not move. It is read off `fetched_at` and not the week's own date, because a holiday week is written a week late (sec.1c), and a stamp that cannot be read is not taken for an old one.

**What the FAIL leaves to do.** The job's prompt says only that a FAIL is fixed before it pushes, so the line carries the rest, in this order. The file is not pushed, and the names are not added to `missing` by hand: an entry there is the writer's record that it asked and the provider had no bar. Then main is looked at. If main already holds the week, it is committed and is never written again: where main's copy has the names it replaces the runner's, and where it lacks them too they join it through `--merge` first. If main does not hold it, `scan_pipeline/` is synced on the runner, the file is removed from its `data/weekly`, the week is written again, and `market_state.json` is re-derived through the chain (`snapshot.write_market_state_chain`): the state the discarded week left behind is not last week's, and a deriver handed it takes `corr_prev` from the wrong week. A short file left in place is worse than none. The job takes a week it finds on disk for a committed one, so it is neither pushed nor rewritten, and the week after it lands on main beside a hole (sec.1c). Written again days later, the week may also have lost a contract that has since expired (sec.1d).

**What it does not reach.** `--derive` is as it was, and without `--pipeline` judges with the runner's deriver. The Monday Council's fallback build (STEP 1d of its task card) is a second writer: the same calls, into the same `data/`, gated with the same flags. Its card named `scripts/truth_check.py`, which its workspace does not hold, and no check dir; that one sentence was clarified on 2026-10-06 (owner sign-off) to the copy of `truth_check.py` it downloads that morning, run from a check dir built as the weekly job builds its own. It is a card, and nothing in this repo checks that it is followed. When a name next joins and is merged into the newest week on main, the runner's copy of that week is short of it and was fetched after the rule began, so a Saturday that writes no week fails on the copy until main's replaces it: the line says so, and copying that week with the config avoids it. The weekly job's prompt and task card were not changed. And the runner still has to be synced: after any change to the feed, its `scan_pipeline/` is brought up to the repo's before the next Saturday build, `config/` for a change of names and `snapshot.py` where it is behind.

Nothing reads either name from a weekly file yet. `market_state` reads the sixteen ETFs. `sector-regime-heatmap` (checked 2026-10-06 against its `86446b6`) takes `series.GLD` and `series.BTC` from `data/daily`, for two comparison rows on its daily tape, and builds no such row from the weekly panel. Computed on the panel before the merge and after it, its weekly metrics are byte-identical for each of the 109 weeks it can compute, and it refuses the first four, which have too few weeks behind them, the same way on both. `scan_pipeline/panel_source.py`, off by default, keeps both out of the engines' scan set. They are stored for Council v2, where Ophelia's third pass weighs both every week (`lab/council_v2.md`). The 19 daily files before 2026-09-22 hold neither, and daily files are not backfilled (sec.4).

**Four renamed names (owner decision 2026-10-06).** `BNY`, `MRSH`, `DOC` and `VMRK` are `BK`, `MMC`, `PEAK` and `EQR` under the symbols they trade by now: renamed 2026-05-21, 2026-01-14, 2024-03-04 and, for `EQR` as it absorbed `AVB`, 2026-08-18. The provider serves a renamed company's whole history under the new symbol and at most its last bar under the old one. Asked on 2026-10-06 it returned 548 daily bars from 2024-07-30 for each of the four, none for `BK`, `MMC` or `PEAK`, and one for `EQR`, its last. The first three were renamed before the panel's first fetch on 2026-08-12, so no fetch ever returned a bar for them: the 111 weeks through 2026-09-18 list `BK`, `MMC` and `PEAK` in `missing` and held those companies under no key. `EQR` was renamed six days after it, so its bars are in 105 weeks, 2024-08-16 to 2026-08-14, under `EQR`.

Merged on 2026-10-06 with `--merge`, each bar labelled in `provenance.series`:

- **`BNY`, `MRSH` and `DOC` into all 111 weeks**, 2024-08-09 to 2026-09-18: 333 bars.
- **`VMRK` into five more weeks, the ones before 2026-09-25 in which it traded under that symbol**, 2026-08-21 to 2026-09-18: 5 bars. In those weeks `EQR` is in `missing`, and all the panel held for the company was two prints under the dead `AVB` symbol: 65.9005 on no volume in 2026-08-21.json, which the correction drops, and 68.14 in 2026-08-28.json, which is this company's Monday close (sec.1b). Its Friday closes are beside them now.
- **`VMRK` into no week before that.** What the provider serves under `VMRK` there is `EQR`'s bar. Merged into a copy of the panel, it had `EQR`'s volume in all 105 weeks that hold `EQR` and a close 0.98824 of `EQR`'s in every one: the dividend that went ex on 2026-10-05. That is one history under two keys on two adjustment anchors, and a bar added to a week is never taken out.

So that company's history is `series.EQR` through 2026-08-14 and `series.VMRK` from 2026-08-21, never both in one week. `VMRK` is in neither `series` nor `missing` of the 106 weeks before, by decision and not by omission: `missing` would say the provider had no bar, and it has one. `RENAMED` in `scan_pipeline/config/tickers.py` is where the join is written down. 2024-08-09.json holds neither key and stays so: it was started on 2026-08-26, after the symbol died, and lists `EQR` in `missing`. A `VMRK` bar there would stand before all of `EQR`'s weeks.

**One company, one symbol a week (owner decision 2026-10-06).** For some hours nothing mechanical kept to that. Rehearsed on copies of the panel, each of these exited 0 and passed `rebuild_corrections`, `panel_guard` and every `truth_check` gate:

- `--only VMRK --merge` over the weeks that hold `EQR` added `EQR`'s own bars a second time: 105 weeks holding both. A dry run for `VMRK` over all 113 weeks, from the backfill workflow's default start, had answered "could be added, if the provider has a bar: 106 pair(s)".
- `--only EQR --merge` over 2026-08-21 filed `EQR`'s close of Monday 2026-08-17 under the Friday beside `VMRK`'s own bar, struck `EQR` from that week's `missing`, and wrote a new `missing` entry for it into two later weeks. What the provider keeps of a retired symbol is its last session.

A bar added to a week is never taken out, so each rule below stops a whole run before it writes, and none has a flag.

- **The map.** `RENAMED` holds the four renames, old symbol to new: `BK` to `BNY`, `MMC` to `MRSH`, `PEAK` to `DOC`, `EQR` to `VMRK`. `scripts/backfill_weekly.py` and `scripts/audit_series.py` read it. `scripts/truth_check.py` repeats it as `RENAMED_SYMBOLS`, because its feed checks run where there is no `scan_pipeline/`, and a test holds the two equal. One old symbol to one new one: a merger of two listed companies is not a rename, and `AVB` is not in the map. A rename goes into both copies when it goes into the ticker list.
- **A bar, for all of this, has volume behind it.** A close on volume 0 or none is a print. `AVB`'s two under a dead symbol are the pattern (2026-08-21 and 2026-08-28), and a feed that still asks for a renamed company's old symbol can be handed the same. A print does not hold a week for a company, and it is not a symbol's last bar.
- **A rename on record.** `--merge` never adds the old symbol, to any week. It does not add the new symbol to any week up to the old symbol's last bar, so the symbols of one company never interleave. The bound is read off every week on file, not the run's range, so the run is refused before the download, and in a dry run, with exit 2, and the plan no longer counts those weeks as something a fetch could add. For `VMRK` that is every week through 2026-08-14, 2024-08-09 with them. For `BNY`, `MRSH` and `DOC` it refuses nothing, since the panel holds no `BK`, `MMC` or `PEAK` bar. The old symbol is refused everywhere, and not only in the new one's weeks, because of the weeks between: with `VMRK` in the panel from 2026-09-25, as it was that morning, `EQR`'s Monday bar could still be filed under 2026-08-21, and `VMRK` would then have been refused that week for good.
- **A rename nobody recorded: the bars say so.** After the download and before the first write, a named ticker that would share a non-zero volume with one other key in three weeks or more is refused as that key's history under a second symbol. The count is the pair's over every week on file, so the weeks a pair already shares are counted with the ones the run would add, and two names of one run are held against each other. The volume is the witness, as it is for `audit_series.py`: a close is adjusted to its fetch date, a volume is not. Measured on the panel of 2026-10-06, 113 weeks and some 56,000 pairs of keys a week: 59 pairs share a non-zero volume in some week, every one of them in exactly one week, and `EQR` and `VMRK`, merged over each other on a copy, share it in 105. With the rename taken off the record for one run, the provider's `VMRK` was refused on that count.
- **What the volume rule cannot see.** A pair that shares fewer than three weeks in all, and the newest-week merge of a name that has just joined the feed is one week. A week whose committed volume the provider has restated since: it restates many, and `macro/series_audit.json` finds no session for the volume of 1,720 of the weekly job's 3,181 bars, so the rule is at its weakest in the weeks that job wrote and at its strongest in the backfilled ones. A pair with a split between the two fetches. A retired symbol's last session, which is another day's volume. And anything at all in a dry run, which downloads nothing. Recording the rename covers each of those. Where the volumes still match, an unrecorded rename can put one bar under a second key in two weeks at most before the third is refused.
- **The gate.** `truth_check --feed` FAILs when a weekly file's `series` holds two symbols of one rename, each with volume behind it, a correction counted under its own name, with one line a company. This is for every writer that is not `scripts/backfill_weekly.py`: its mirror under `scan_pipeline/`, which nothing invokes, a file built by hand, a tool that does not exist yet. It runs in the backfill workflow ahead of the commit step, in CI on the pull request, in the daily job before it commits a session, and in the weekly job's gate on the runner. No committed week holds both symbols of a rename, and the weekly job cannot write one, because its universe holds the new symbols only: on a copy of the runner's own tree the gate gains one OK line and nothing else. The message is written for an agent whose other instruction is that any FAIL is fixed before pushing. It says not to delete a bar, edit a file or push one, then to look at main, and then what to do where main's copy holds both symbols, where it holds one, and where main has no such file.
- **Symbols that interleave without sharing a week are a WARN.** A `VMRK` bar in 2024-08-09.json is not a doubled bar, and a committed file is not edited, so nothing mends it and nothing is stopped: one line names the week. A merge does not write that state. A whole-week write from today's universe can, since it carries `VMRK` where an older writer carried `EQR`, and for a week on file that is a rewrite, which has to be declared (CLAUDE.md, "The backfill").
- **A week that holds a company under one symbol is not asked for another.** Three checks asked. The "name left out" warning (sec.1c): with a `VMRK` bar in 2024-08-09.json it named each of the 105 weeks that hold `EQR` and printed the `--merge` command for it. And the two that hold the newest week to the feed, `--config`'s (above) and `--feed`'s ("Where the week is written", below): in the week a rename is recorded the newest file still holds the old symbol's bar, the cure both print is a merge, and that merge is refused. So that week needs no merge, and the next Saturday's file holds the new symbol.

Not covered here: the daily files, which nothing merges into.

**The old symbols stay in `missing`, beside the bars.** Each of the 111 weeks still lists `BK`, `MMC` and `PEAK`, with the reason its writer gave: "no bar for week of <date> (likely pre-IPO or not trading)" in the 105 the backfill wrote, "no bar dated ..." or "no usable close ..." in the six written since by the weekly job. The entry is true: the symbol was asked for and not served. The guess in the first reason is wrong for these three, which traded in every week of the panel. A committed file is not edited to say so, and `--merge` removes a `missing` entry only for the ticker it has just filled. So in a week that holds `BNY`, `MRSH` or `DOC`, a `missing` entry for `BK`, `MMC` or `PEAK` is that company's retired symbol, and this paragraph is the record of it. The same guess sits on `HES` in those 105 weeks, a company that traded until it was acquired on 2025-07-18 and for which the provider now returns nothing, and in 2024-08-09.json on `EQR`, `AVB` and `EA`, whose symbols were dead when that file was started.

Every one of the 338 bars, and of the 8 the two rebuilt corrections carry, is dated its file's session: the Friday, or the Thursday in the five holiday weeks (15 bars). `scripts/audit_series.py` passed each on close and on volume, with no finding new, changed or gone. Unlike `BTC` and `GLD` these four pay dividends, and that shows in three ways.

- **The fourth decimal.** A merged close is the provider's adjusted close as served that minute, and its fourth decimal does not come back the same twice (sec.1c saw closes 0.0002 apart): the same command run six minutes earlier against a copy differed by 0.0001 in 19 of the 338 closes, and in no volume.
- **The seam.** The merged weeks are adjusted to 2026-10-06 where 2026-09-25.json and 2026-10-02.json are adjusted to their own fetch. `MRSH` went ex on 2026-10-01 and `VMRK` on 2026-10-05, so the panel reads `MRSH`'s week to 2026-09-25 as -1.65% where the price moved -2.22%, and `VMRK`'s as +1.67% for +0.47%; across the join, `EQR` on 2026-08-14 to `VMRK` on 2026-08-21 reads +0.05% for +1.24%. `BNY` and `DOC` had no ex-date in between and read true. `provenance.series` is what tells a reader: it resolves the anchor per ticker, or it does not difference across the seam.
- **Two distributions under `BNY` that are not the bank's.** The provider's dividend list for the symbol holds 0.051 ex 2026-01-20 and 0.051 ex 2026-02-06, beside the bank's own quarterly 0.47, 0.53 and 0.63, and it adjusts for both. The 76 merged `BNY` closes through 2026-01-16 are 0.084% lower than the bank's dividends alone make them, the next two 0.042%, and the week to 2026-02-06 reads +3.71% where the price moved +3.67% with no ex-date of the bank's in it. They look like distributions of whatever held the symbol before the bank took it on 2026-05-21, which is not established. `MRSH`, `DOC` and `VMRK` have none: every step in their adjustment is a dividend on their own schedule. `audit_series.py` cannot see this, because it divides the provider's own factor out. Nothing was changed for it: the close is what the provider serves, and the file is an observation of that.

Nothing reads any of the four from a weekly file today. None is in the focus set or on the Council watchlist, and `market_state` reads the sixteen ETFs. `sector-regime-heatmap` at its `86446b6` computes byte-identical weekly metrics on the panel before this merge and after it for each of the 109 weeks it can, and refuses the first four the same way. `scan_pipeline/panel_source.py`, off by default, would read them: all four are in the engines' set, and with it switched on they were outside the scan until 2026-10-23.json gave them four weeks behind them. On a tree that holds these files they are inside it now.

The runner's tree does not hold them: its copy of `data/weekly` is the old one until it is synced, and it is synced whole or not at all. Left as it is, it fails nothing and warns of nothing new, since there the four still begin on 2026-09-25 and the job pushes only the newest week. With 2024-08-09.json alone copied over, `BNY`, `MRSH` and `DOC` have a bar in an earlier and in a later week, and the gate there warns about each of the 110 between.

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
- **Append-only by week.** A week that has an entry keeps it. `scripts/backfill_us2y.py` adds weeks and never rewrites one. CI compares the file with what the branch held before the push, or with a pull request's base, and fails if an entry that was there changed or disappeared. That is the commit the panel check in the same step uses (sec.1, "What a file held"); until 2026-10-06 both took the last commit's parent, and so saw only the last commit of a push. The stronger audit is `backfill_us2y.py --check`, which compares every committed Treasury 2-year against the archive and reports a difference without writing.
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

**The equity series.** The audit above stopped at the special blocks. `series` had the same habit in one writer. Until 2026-10-07 `scripts/backfill_weekly.py::slice_week` took the last bar on or before the Friday, anywhere in the Mon..Fri week, and the only note it could leave was file-level, written when NO ticker had a Friday bar. It wrote the 105 backfilled files and every name merged into a week afterwards (`provenance.series`): 34,980 of the 38,161 equity bars in the panel's 115 files, the two corrections counted as files of their own because they are what readers see. `scan_pipeline/scripts/backfill_weekly.py`, the mirror nothing invokes, has the same function. A ticker with no Friday bar -- halted, delisted mid-week, a gap at the provider -- got an earlier session's close under the Friday date with nothing to show it. The Friday job does not do this: `snapshot.fetch_weekly_bars` takes the bar dated the file's session (the Friday, or the session a holiday file names: sec.1c) or lists the ticker in `missing`.

`scripts/audit_series.py` asked the provider about every bar (2026-10-05). It cannot ask by comparing levels. A committed close is an adjusted close as of the day it was fetched, so it is supposed to differ from a fresh fetch for every name that has paid a dividend or split since: level against level, 19,916 of the bars counted as right below would be reported wrong. Two things do not move, and each bar is asked both. Volume is never dividend-adjusted: the committed volume is the volume of one session, times any split since. And the committed close over today's adjusted close for the same session is one factor per ticker and fetch date, which the provider states itself as its `Adj Close` over its `Close` on the fetch date. A bar is the named session's when its close is that session's on that basis and its volume does not name another.

| What the file holds | Bars | Where |
| --- | --- | --- |
| The bar of the session the file names | 34,774 | 33,122 the Friday's; 1,652 the Thursday's in the five holiday files, which say so in `session_note` |
| An earlier session's close under the Friday date | 1 | `EA` in 2026-08-07.json: 209.70 on volume 0. It is EA's close of Tuesday 2026-08-04, its last session before it was taken private |
| Cannot be checked | 205 | `AVB` (104 weeks) and `EA` (101). The provider keeps one bar of a delisted symbol, the last. The owner's spreadsheet agrees with 50 of the AVB bars, session by session; nothing covers the other 155 |

So it happened once, to a name on its way out of the market. "None found" among the rest is worth what the audit could have found, and it measures that on every run: with the session before it put in place of each of the 37,947 bars that passed and have one, that session is named 37,947 times. The close alone would pass 138 of those, where the close did not change; the volume names them.

The 3,181 bars the Friday job wrote were asked the same question, because the claim that it is date-pinned is a claim about this repo's copy of the writer. One file was not written by it. On Saturday 2026-08-29 the provider's daily closes for the Friday were all null, and 2026-08-28.json was built by a one-off script on the runner that took each close from the provider's `1wk` bar. For 330 names that is the Friday close. For `AVB`, merged away ten days before, it is 68.14 from Monday 2026-08-24, with a null volume, and it is the successor's price printed under the dead symbol; the correction of that week is a full copy and carries it. Three closes in 2026-09-25.json, read at 18:14 ET on the day, are half a cent under the close the provider settled on. And 1,665 of the job's bars rest on the close alone, because the provider has revised their volume since they were read; 13 of those closed at the same price as another session of their week, and for those nothing says which of the two bars the file holds. None of the backfilled or merged bars is in that position. `macro/series_audit.json` lists all of it with causes, the way `macro/instrument_audit.json` does. It was run again on 2026-10-06, after `BTC` and `GLD` were merged into every week (sec.1, "The equity set"): 230 more merged bars, each the session its file names by close and by volume, and no finding new, changed or gone. And once more that day, after the sixteen index and sector ETFs were merged into 2024-08-09.json (sec.1c): 16 more, with the same result. And a fourth time, after the four renamed names were merged (sec.1, "Four renamed names"): 346 more, with the same result. The counts in this section are the 2026-10-05 run's. The list's own `audited` block is the latest run's, and differs where the provider has revised more volumes since: 1,720 of the job's bars on the close alone, 15 of them tied.

**Who reads `series`.** Less than the files hold. `market_state.json` derives from sixteen names in it and no others: `SPY`, `QQQ`, `DIA`, `IWM` and the twelve sector ETFs. All 1,824 of their bars are the named session's, and so are the sixteen that 2024-08-09.json has held since 2026-10-06 (sec.1c), which makes 1,840. `sector-regime-heatmap` reads three files a run (the end week, and one and four weeks back) for the focus set and `SPY`; none of the focus set's 12,439 bars is a wrong session, and `AVB`, in its Real Estate basket until 2026-09-21, was never scored (dropped at the end week of the first run, missing at every one after). `scripts/arena_ingest.py` and `portfolio/tracker.py` fetch their own date-pinned bars and do not open `data/weekly` at all. `scan_pipeline/panel_source.py` would read every equity in it, and is opt-in and off. No Council, Arena or portfolio book ever held `EA`, `AVB` or `EQR`. So no derived number has been wrong on this account. What was wrong is the record.

**Decided 2026-10-06 (owner): `missing`, as the Friday job does.** The committed files are not edited, so for them the record is the audit list. For the next file the backfill writes, a ticker's bar is the one dated the file's session, or the ticker is listed in `missing`. `slice_week` returns that bar or nothing, in both copies of the script (2026-10-07), and the entry says what was asked for and what the download holds: `no bar dated 2026-08-07; its last bar before that is dated 2026-08-04`, or `no bar dated 2026-08-07, and none before it in the download`. It guesses at no cause. The text the earlier files carry, "likely pre-IPO or not trading", was wrong for three companies in every week it was written into (sec.1, "The old symbols stay in `missing`").

The file's session is the Friday, or on a market holiday the last session of the week, named in `session_note` and decided by `SPY` (sec.1c). A whole-week write knows it from the witness. A merge reads it off the file it adds to (`file_session`): the note's day, or the Friday where there is none, and a week whose note cannot be read is refused rather than taken for a Friday, since every name merged into a holiday week would then be listed in `missing` beside a session it traded on. So a name merged into 2026-07-03.json gets its bar of 2026-07-02 or an entry, and a retired symbol's last session, which the old slice filed under the Friday of its week (sec.1, "One company, one symbol a week"), is handed over only where it is the file's own session, a merge `RENAMED` refuses before it starts.

No new key, a gap stays a gap, and every reader already handles one. The other way was `provenance.series.<ticker>.observed`, the instruments' key: it would have passed both gates and `sector-regime-heatmap` (checked at `a8363de`: `check_basis()` reads only `.source` and `anchor_of()` only `.fetched_at`), but nothing reads it, so the heatmap would have gone on scoring a stand-in as a Friday close under a label nobody looks at.

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

**The gate.** `truth_check --feed` fails a file whose `series` is empty, whatever its date, and a file dated 2026-10-06 or later that holds no `SPY` bar. That is what a runner still on the old writer produces on a holiday, and the job stops on it before it pushes. It fails a `session_note` that is not `Friday holiday; bars from <date>` with an earlier day of the same week. One committed file predated the witness rule and had no `SPY`: 2024-08-09.json was started by a backfill run restricted to 44 names, had 270 more merged in, and never got the four index or twelve sector ETFs, none of which it listed in `missing`. It was warned about, not failed and not edited, and a `--merge` backfill added the sixteen on 2026-10-06 (below). The warning stays in the gate for a tree that still holds the old copy, which the runner's does until it is synced.

**2024-08-09.json and its sixteen.** Merged in with `--merge` on 2026-10-06 (owner sign-off), fetched at 01:48:08 UTC and labelled so in `provenance.series`. Nothing else in the file moved. Each of the sixteen is Friday 2024-08-09's bar by close and by volume (`scripts/audit_series.py`, run again on the merged panel: no finding new, changed or gone). Three fetches inside four hours agreed on every volume and on every close to within 0.0002, which is as far as an adjusted close comes back the same twice.

No committed number had depended on the gap, and none moved when it was filled. `market_state` skips a week that lacks a name, and when the file was written (2026-08-26) its week was already outside every window of the newest state: the last `as_of` whose percentile window reaches 2024-08-09 is 2026-07-31. Whatever closes the sixteen take, `market_state.json` re-derives byte-identical.

The label is not a formality. The same sixteen names in 2024-08-16.json carry that file's anchor, 2026-08-12, which is before the September distributions; the ones in 2024-08-09.json are adjusted to 2026-10-06, after them. A return read across the two files is overstated by the distribution:

| | SPY | QQQ | DIA | IWM | SMH | XLB | XLC | XLE | XLF | XLI | XLK | XLP | XLRE | XLU | XLV | XLY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| points | 0.26 | 0.11 | 0.32 | 0.27 | 0.00 | 0.47 | 0.33 | 0.60 | 0.37 | 0.27 | 0.13 | 0.67 | 0.84 | 0.74 | 0.39 | 0.23 |

Nothing committed reads across that pair, and a reader that does resolves the anchor per ticker (sec.1, `provenance`).

**A name left out.** The witness rule asks a file for one name, and for a bar. `missing` is never empty by omission (sec.1), so the gate also asks each week, as readers see it (a correction in place of its base), for a bar or a `missing` entry for every name the panel shows it should hold:

- each of the sixteen index and sector ETFs, which every full write of a week carries and which are all that `market_state` reads from `series`;
- any name with a bar in an earlier and in a later week.

Earlier and later, not the weeks either side. A rule that needs both neighbours cannot see the first file, and 2024-08-09.json is the first file. And the panel's two corrected weeks are adjacent, so two corrections gone stale together (CLAUDE.md, "The correction trap") would each hide the other. It is a WARN: the fix is a fetch, and the file cannot be edited meanwhile. It stops nothing anywhere it runs. CI and the daily job (`--feed --config`), the backfill workflow (`--feed`) and the weekly job's gate on the runner (`--feed --derive`) print it and go on, and no test fails on it. That is deliberate: a week the runner writes on stale config fails `--config` only until a later week is whole (sec.1, "The equity set"), and from then on is a hole that this warning alone reports. The suite runs before the daily job commits a session, and an old hole is not worth a daily one. The warning prints the `--merge` command with only the names the week's base lacks. A name the base holds and only a stale correction is missing is sent to `rebuild_corrections.py`, since a merge has nothing to add there.

What the panel cannot say, the check does not claim. A name that joins the universe has no earlier week and one that leaves has no later week, so neither is expected: `VMRK` has bars from 2026-08-21 and `EQR` through 2026-08-14, and nothing here asks for either beyond that (sec.1, "Four renamed names"). `BNY`, `MRSH` and `DOC` were the same case for two weeks, with bars from 2026-09-25 only, until they were merged into every week before it. The rule cuts the other way too: one bar out of place asks for many. The repo's copy of 2024-08-09.json alone on a tree without the merge sets this warning on every week between, for `BNY`, `MRSH` and `DOC`. One case is excused: a week that holds a company under another of its symbols (`RENAMED_SYMBOLS`) is not asked for this one. Asked, it was handed the merge that doubles the history: a `VMRK` bar in 2024-08-09.json drew this warning, and its `--merge` command, for each of `EQR`'s 105 weeks. That bar now draws one line of another warning, which names it and prints no command (sec.1, "One company, one symbol a week"). By the same rule a stock missing from the first file reads as one that joined a week later, and nothing knows what the first week should have held. The newest week is `truth_check --config`'s, which knows the feed. Weekly only: daily sessions are recovered out of order, each with the universe of the day it was recovered.

**The backfill writer.** `scripts/backfill_weekly.py` decided "holiday" from its own slices, by no ticker having a Friday bar, which is just as true of a Friday the provider has not posted: run on the night, it wrote Thursday's bars under a `session_note`. It asks the witness's history now, under the same rule and with the same check against the listing, and refuses the week otherwise (exit 2, which stops the workflow before its commit step); its download runs eight days past the last Friday so that a later bar is in it. A run restricted with `--only` can no longer start a week, whether or not `SPY` is among the names, which is how 2024-08-09.json came to be: `--only` adds to weeks that exist and is refused for one that does not. And each ticker's slice now stops at the file's session, so a file that says "bars from Thursday" holds nothing dated after it. Since 2026-10-07 it holds each ticker to that session as well: `slice_week` returns the bar dated it or nothing, and a ticker without one is in `missing` (sec.1b, "Decided"). `scan_pipeline/scripts/backfill_weekly.py`, the mirror nothing invokes, has the same slice and the same reasons, and no longer lists a name in `missing` that the week holds a bar for. It is otherwise as it was: its `--merge` still fetches a held name again and writes over its bar. It reaches `write_weekly` like everything else, so it cannot write a file without `SPY`, and it can still call an unposted Friday a holiday: it finds a week's session from its own slices, not from the witness.

**A week is written once (2026-10-06).** `write_weekly` started a week's file and, until that date, also replaced one: called for a Friday that had its file, it wrote the new fetch over it and returned as usual. Every close became another fetch's, adjusted to a later date, `fetched_at` was restamped, and a name the second fetch lacked left the file without a `missing` entry. It raises `WeekOnFile` now and writes nothing. That is asked first, before the witness and before any instrument is fetched, and again just before the write. The refusal says what to do instead: leave the file; if it never reached the repository, push it as it stands; names it lacks are merged in afterwards; a close the provider has restated is a correction's (sec.1). What is at the path is not always the week: a zero-byte file, the first bytes of a write that died, another week's file. That is refused too, in other words (it is not a weekly file, it is not pushed, it is removed by hand), because a run told to push it would push a file the gate fails, under a name `unwritten_fridays` no longer owes. The writer cannot leave one itself: a week is written beside its path and moved into place. One caller passes `overwrite=True`: `scripts/backfill_weekly.py --force`, which the workflow reaches only when it is dispatched with `rewrite` (sec.1, "What a file held"). The mirror script's `--force` is unchanged by decision and passes nothing, so it stops at the writer for a week that is on file. A correction is not the week's file and is not looked at, as in `unwritten_fridays`.

**Outside this repo, by hand.** The weekly job is a scheduled agent running the runner's copy of `scan_pipeline/`. Until that copy is synced it writes the empty file on a holiday, and the gate, fetched fresh, stops it there. Until then it also writes over a week that is on file if it is called for one, and no gate sees that before the push; step 2 of its prompt is what says not to. Synced or not, the writer and that step both look at the runner's own copy of `data/weekly`: a week the repository has and the copy lacks, one a backfill wrote from this side, is a week the job would write and push over when it is the Friday it runs for, and CI reports it only once it is on main. The copy has every base week today and has to keep up (checklist). And on the path the prompt prescribes, the refusal is never reached: step 2 routes a week on file around the writer and step 7 pushes the weekly file only "if newly written". A run that died between writing and pushing, as on 2026-08-15 and 2026-08-22, leaves a week its next run neither rewrites nor pushes, and `unwritten_fridays`, reading the runner's directory, no longer owes it: the repository is left with a hole the runner's gate passes. Step 7 has to push a week the repository lacks whether or not that run wrote it. Where the refusal will be met is a second attempt inside one run, which the 2026-08-28 run made; after the sync the first local write is final. And its prompt asks for the most recent Friday only: the catch-up above has to be put into the task and its task card, or the first Saturday after a refused week ends at the gate's FAIL instead of at a written file.

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
- **Append-only.** An entry on file stays as it is, and so does `audited_through`: moving it re-admits or drops committed closes for every reader at once. CI compares the file with what the branch held before, as it does the Treasury history (sec.1a). `backfill_commodities.py --check` asks the provider again and reports a difference without writing; a continuous symbol that has since moved is the thing this file exists to survive.

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

The daily job holds itself to "never edit" before it commits.
`scripts/panel_guard.py --against HEAD` compares the files on disk with the
commit the run started from, and a session already on file that the run
changed, relabelled or removed fails it (sec.1, "What a file held"). CI
cannot do that for it: a push made with the workflow token starts no
workflow, so no CI run has this job's commit at its head.

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

**The half-posted session (2026-10-07).** The roll that ends that window is
not one step, and the witness is early in it. The evening attempt for
2026-10-06 was started at 01:00 UTC on the 7th (run 37554944269) and found
`SPY` posted and 59 of the 336 names without a bar, in the batch and again
when each was asked for alone. The witness gate passed, every gate after it
passed, the file was committed with 277 series, and the audit was green. By
02:41 UTC the provider had a bar for all 336.

What the 59 have in common is their age. 57 of them are every name of the
feed that the provider dates (`firstTradeDate`) from 2012-04-12 on. The
other two, `GOOG` and `QUBT`, it dates 2004 and 2007, and `GOOG` at least is
a symbol younger than the history filed under it (the class C shares took it
in 2014). No name it had posted was first listed after 2011-10-13. So the
roll works from the oldest listing to the newest and the names it reaches
last are the same ones every night, `SPCX` and `BTC` today. It has been seen
on that one night.

A fetch is therefore held against the panel before it is written
(`assert_session_posted` in `scripts/daily_observe.py`). A name is
*expected* if it is in the feed and has a bar in one of the last sessions on
file before the one being written (`RECENT_SESSIONS` of them), and an
expected name with no bar is *gone*. The feed is `PRICE_FEED_UNIVERSE` and
the sixteen ETFs, which is fewer names than a run fetches: it also fetches
whatever the newest weekly file holds, so a name taken out of the feed goes
on being fetched until a week is written without it, and is not waited for
from the day it is taken out (`waited_for`).

- **Until `ROLL_HOURS` after the close, which is 02:00 US/Eastern, one name
  gone refuses the run.** The provider may still be posting, nothing on the
  night tells a name not yet posted from one that did not trade, and a bound
  above none would let the roll's last names drop out of the panel night
  after night. The refusal is exit 2, like the witness's, and the morning
  attempt writes the session.
- **After that hour a name still gone is listed in `missing`**, as a
  delisted or renamed symbol always was, up to `MAX_GONE` of them. More is a
  provider that did not answer for part of the panel, and is refused at any
  hour and by every attempt. A session short by that many is not written by
  this script at all: it stays the hole the audit reports until the provider
  has the bars or the names leave the feed, and leaving the feed works that
  day.
- **Several sessions, not the one before.** The newest file can be the short
  one. Held against 2026-10-06.json alone, the same roll caught at the same
  point the next night loses nothing.
- **`--since` holds each session of its range to the same**, against the
  sessions before it on file and in the same download. A range usually runs
  long after any roll, but it may end at the last close, and in the small
  hours that session is cut from the download a single run would have read.
  One it refuses is left for a later run and the rest are written; the exit
  is 2 only when nothing was.
- **`--dry-run` reports the refusal as a real run would, and `--force` does
  not override it.** `--force` is the append-only guard's key and nothing
  else, and a half-posted fetch written over a whole file is the worse loss.
  So it is refused as well wherever the fetch lacks a name the file on disk
  holds a bar for, at any hour. A file that does not read, which is what a
  write that died leaves and what `--force` is for, holds nothing to lose.
- **With no earlier session on file nothing is compared**, and the witness
  is all that speaks for the file, as it was for every file before this
  rule.
- **The audit calls the state a declined attempt leaves PENDING.** The
  newest settled session with no file is a note, not a warning, while the
  provider may still be posting it (`ROLL_HOURS`). Past that hour it is the
  warning it was, and names the `--date` command, because no scheduled
  attempt after the morning one aims at that session. One behind the newest
  with no file fails the run at any hour ("Completeness", below).

The refusal also asks the provider's raw chart what it lists for the first
few of the names, as the witness's refusal does, and prints the answer. It
decides nothing. What a name looks like there while the roll has not reached
it has not been seen: on 2026-10-07 all 59 were posted before anyone asked.

What this costs, and what it does not cover:

- After a name really stops trading, the evening attempt declines for as
  long as its last bar is among the sessions compared with, and each of
  those sessions is written the next morning instead. Taking the name out of
  the feed ends that the same day.
- Every session the evening attempt declines rests on the morning one. Its
  cron is 09:15 UTC and GitHub started the first of them at 15:56 UTC
  (2026-10-06). It aims at the session that closed until the next close
  passes; started later than that, it writes nothing for it and the audit
  reports the hole.
- The morning attempt has to stay later than `ROLL_HOURS` after the close.
  Inside it, a name that is gone for good would be waited for by both
  attempts and no session written. A test reads the cron and holds the two
  apart.
- After the roll hour up to `MAX_GONE` names are believed without the
  provider being asked again. A fetch that failed for one of them at that
  hour is written as `missing` for good. A `--since` range is the more
  exposed: its one download has no second try per name, and every session
  of it is cut from that download.
- It compares names in `series`, not values and not the other blocks. A bar
  dated `as_of` that held another day's numbers would pass, and an index
  close (`US10Y`, `VIX`) not yet posted goes to `missing` as before. Neither
  happened on the night: all 277 bars of 2026-10-06.json are the bars a
  fetch at 02:41 UTC returned, close and volume, and so are the three
  instrument closes it holds.
- A name with no bar in any of the sessions compared with is not waited
  for. That is right for a symbol long dead and wrong for a new listing in
  its first days in the feed, which is the youngest instrument and so the
  last the roll reaches. It is waited for from the first file that holds it.
- The weekly writer has no such check. It runs on Saturday after 13:00 UTC,
  some seventeen hours after the close.

**2026-10-06.json is short by 59 and is not edited.** It lists them in
`missing` as "no bar dated 2026-10-06 in window ...", which was true of the
minute it was fetched and reads like 59 names that did not trade. Among them
are `XLC` and `XLRE`, two of the sixteen ETFs, `BTC`, and 23 of the focus
names. One of the 277 bars it does hold is a print and not a trade: `BLFS`
at 38.61 on volume 0, the close of 2026-10-05, on a day the provider lists
no trade for it. That is the provider's row and not the roll's doing: the
later fetch returned the same.

`sector-regime-heatmap` built its tape for the session from this file half
an hour after it was committed (its `79ef7e7`): six of eleven baskets "too
thin to characterise the sector" and an empty bitcoin row. A tape there is
never rewritten. While the file stands, the two later tapes that have
2026-10-06 at the far end of a window, 2026-10-07 over one session and
2026-10-13 over five, are short of the same names. Whether the file is
repaired, and how, is the owner's decision and has not been made.

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
| Sector sparklines | the last 13 weeks of `data/weekly/`, each from its correction where it has one (sec.1) |
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
- [x] The weekly job's own gate line holds the newest week to every name: `truth_check --feed` carries the list, pinned to `snapshot.equity_universe()`, and fails a short week fetched since the rule began (2026-10-06, sec.1, "Where the week is written")
- [x] The Monday Council's task card says which `truth_check.py` its fallback build gates with: the copy it downloads that morning, from a check dir of its own (clarified 2026-10-06, owner sign-off; sec.1, "What it does not reach")
- [ ] Runner's `scan_pipeline/snapshot.py` synced, so the Saturday build fetches `BTC` and `GLD` (sec.1, "The equity set")
- [x] `BNY`, `MRSH` and `DOC` merged into the 111 weeks before 2026-09-25, and `VMRK` into the five of them it traded in; `EQR` stays the key for the weeks before those, and the old symbols' `missing` entries are on record (2026-10-06, sec.1, "Four renamed names")
- [x] A merge that would put a renamed symbol's bars beside its old symbol's is refused by the writer, on the record and on the bars, and failed by the gate (2026-10-06, sec.1, "One company, one symbol a week")
- [x] `data/weekly/<date>.json` writer in the scan, with `missing` populated
- [x] `truth_check --feed` fails a `missing` that is not a list of `{"ticker", "reason"}` entries, both strings that say something, in every weekly and daily file (2026-10-06, sec.1)
- [x] Correction-file path handled by readers (prefer `.corrected.json`; `scan_pipeline/panel_source.py` since 2026-10-06, sec.1)
- [ ] Runner's `scan_pipeline/panel_source.py` replaced with this repo's; until then it reads a corrected week from both files (sec.1, "Never edit")
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
- [x] How an equity bar that is not the Friday's is recorded decided: `missing`, as the Friday job does (owner, 2026-10-06), and `slice_week` changed to match in both copies of `backfill_weekly.py` (2026-10-07, sec.1b, "Decided"). The runner's copy of the mirror is the old one until it is copied over by hand
- [x] A weekly file is written only with its session witness: `SPY`'s bar dated `as_of`, or a proven, named stand-in; no witness, no file; `truth_check --feed` fails an empty `series` and a week missing between two files (2026-10-06, sec.1c)
- [ ] The weekly job's prompt and task card changed to write every Friday the panel owes, oldest first, and the runner's `scan_pipeline/` synced (sec.1c, "Outside this repo")
- [x] The sixteen index and sector ETFs merged into 2024-08-09.json, labelled and audited (2026-10-06, sec.1c, "2024-08-09.json and its sixteen")
- [x] `truth_check --feed` warns when a week has neither a bar nor a `missing` entry for an index or sector ETF, or for a name carried by an earlier and a later week (2026-10-06, sec.1c, "A name left out")
- [ ] Runner's copy of `data/weekly/` brought up to the repo's: every file that differs, both corrections included, in one go and never 2024-08-09.json by itself (sec.1c, "The gate"; sec.1, "Four renamed names")
- [x] What a committed panel file held is compared bar by bar and label by label: around the backfill's write, in CI against the whole push, and in the daily job before its commit. A rewrite is declared at dispatch and may not remove a bar (2026-10-06, sec.1, "What a file held")
- [x] `snapshot.write_weekly` refuses a week that already has its file (`WeekOnFile`); only the backfill's declared rewrite may write one again (2026-10-06, sec.1c, "A week is written once")
- [ ] Runner's `scan_pipeline/snapshot.py` synced, so that refusal exists where the weekly job runs. Until then its writer overwrites a week it is called for, and CI sees the push after it is on main (sec.1c, "Outside this repo")
- [ ] Step 7 of the weekly job's prompt and task card changed to push a week the repository lacks whether or not that run wrote it. Today a run that died before its push leaves a week nothing pushes (sec.1c, "Outside this repo")
- [ ] A new correction's series held to its base by a gate and not only by the test suite, and for `data/daily` at all (sec.1, "What a file held")
- [x] A daily session is written only once the provider has posted it for the panel: a fetch is held against the last sessions on file, one name gone refuses the run while the roll may still be running, and more than a few refuse it at any hour (2026-10-07, sec.4, "The half-posted session")
- [ ] 2026-10-06.json, written half way through the provider's roll and short by 59: whether it is repaired, and how (sec.4)
