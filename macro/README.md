# Truth Layer — macro/facts.json + scripts/truth_check.py

> **Purpose:** one canonical fact table for every macro number the grid publishes,
> plus automated checks that catch stale pages, fabricated numbers, and arithmetic
> that doesn't add up. Born from the 2026-07-28 swarm audit (Repo audit: FAIL,
> 5 critical / 8 high findings) and the 2026-08-03 fabricated-P/E incident.

## The rule

**Wikis and reports CITE macro numbers; they never restate their own.** If a wiki
needs the 10Y yield, VIX, WTI, SPY, a sector ETF close, or the fed funds range, the
value comes from `macro/facts.json`. A number that appears in two places must be
the same number. When a fresh fetch legitimately disagrees with the table (market
moved since Saturday), the wiki says so explicitly — it never silently diverges.

## facts.json (schema macro-facts/v1)

- Written **every Saturday by the Canary Watch job**, from the SAME data fetch that
  produces `wiki/canary-watch.md` — one fetch, two outputs, zero contradiction risk.
- Sections: `policy` (fed funds range, stance, next macro gate), `rates`,
  `volatility`, `cross_asset`, `sector_etf` (all 12 sector ETFs: close + WoW %).
- Every verifiable field carries `source: "yahoo:<SYMBOL>"`, `as_of`, and
  `tolerance_pct`. Fields from external feeds we cannot re-fetch carry
  `stale: true` and are treated as directional only.
- Computed fields (`curve_10y_3m_bps` etc.) must recompute from their inputs.

## quarantine.json (phantom-anomaly bans)

- A ban list for **known-fabricated values** from past data outages — numbers that
  were never real and must never reappear in any wiki or report.
- Schema: `[{"ticker": "GOOGL", "banned": "9.11", "reason": "...", "added": "..."}]`.
  A wiki line containing BOTH the ticker and the banned string = FAIL.
- Seed entry: the GOOGL `$9.11` ghost EPS from the 2026-07-21 data outage.
- Any agent that confirms a fabricated number ADDs a ban entry here (with reason
  and date) instead of just fixing the row — fixing without banning leaves the
  ghost free to re-enter next week.
- `truth_check.py --quarantine` also runs a generic net: a `$X EPS` claim inside a
  table row is flagged when X exceeds 20% of the share price in the same row.

## truth_check.py (scripts/)

Stdlib-only validators. The cron jobs download repo files to a local temp dir and
run it there — the workspace is NOT a repo clone (never run it against a checkout).

```
python scripts/truth_check.py --repo <dir> [--staleness] [--facts] [--lint]
       [--quarantine] [--warn-days 7] [--fail-days 14] [--max-fetch 60]
```

(no mode flag = run everything; exit 1 on any FAIL)

| Check | WARN | FAIL |
|---|---|---|
| **Staleness TTL** — every `wiki/*.md` "Last updated" stamp | > 7 days old; stamp missing | > 14 days old |
| **Facts freshness** — facts.json `generated` date | — | > 8 days old |
| **Facts accuracy** — each yahoo-sourced field vs live close | fetch failed | deviation > `tolerance_pct` |
| **Spread arithmetic** — computed curve spreads recompute | — | off by > 3 bps |
| **Holdings lint** — (TICKER, $price) rows in wiki tables vs live closes | dev > 3% | dev > 15% (price ≥ $10) or > 35% (micro-cap < $10) = impossible row |
| **WoW arithmetic** — weekly-change columns recomputed | sign flip or off by > 2 pts | — |
| **YTD arithmetic** — YTD columns located by table header, recomputed from the prior-year final close | sign flip or off by > 3 pts | — |
| **Weight sums** — any table whose Weight column totals past 100% (bad carry / double-counted row) | — | sum > 100.5% = impossible table |
| **Quarantine** — banned (ticker, value) pairs from quarantine.json; phantom-EPS net | quarantine.json missing | any ban hit; EPS claim > 20% of same-row price |

Lint scope note (v4, 2026-08-11): the linter is fully table-structure aware.
Prices come ONLY from tables with a Price/Close/Last column — narrative tables
(debate rows, watchlists, event calendars) are never price sources. A leading
Ticker/Symbol header cell is the ticker even when it collides with a macro
stopword (WTI the stock vs WTI the oil benchmark). WoW/YTD/Weight values are
matched to their columns by header name. Sections are tracked by sticky `##`
parent so `###` day-headers inside skippable sections (earnings, surprises,
implied moves, analyst targets) stay skipped. First full-grid sweep: 48 raw
FAILs triaged to 1 real anomaly (CEVA post-earnings — correctly surfaced).

## Who runs what, when (folded into EXISTING jobs — cron grid is full)

- **Canary Watch (Sat 3:39 PM):** regenerates `macro/facts.json` from its own fetch
  and pushes it alongside `wiki/canary-watch.md`.
- **Synthesis (Sat 4:56 PM):** reads facts.json FIRST; every macro number in
  synthesis.md and the README Market Brief must match it. Runs
  `truth_check.py --staleness` and names any stale wiki in the synthesis.
- **Monday Council Scan (9:03 AM):** STEP 0c Truth Gate — runs
  `truth_check.py --staleness --facts --lint --quarantine` every week before the
  pipeline (mandatory, not time-permitting). Staleness/facts WARN = note it in the
  report and prefer fresh fetches over the stale page. FAIL (any wiki > 14d, or
  facts.json missing/stale/contradicted by market data) = ENGINE ABORT path:
  publish the report with the abort banner, book no positions, log to shadow-book.
  Lint/quarantine hits are repaired in place (with a note) or queued for the next
  Saturday crew prompt; confirmed fabrications get a ban entry added to
  `macro/quarantine.json` the same session.

## instrument_audit.json (which session a committed close is)

- The reviewed list of differences between the committed `rates` / `vol` /
  `commodities` / `fx` closes in `data/weekly` and `data/daily` and the provider's
  own history: a prior session's close under the file's date, a holiday stand-in
  the file does not mark, a futures bar read before it settled, a contract month
  the provider no longer serves. `DATA_FEED.md` sec.1b is the contract.
- An entry is a statement that the difference was **looked at, not that it was
  fixed**. The files are observations and are never edited; one week
  (2026-08-28) is corrected. Each finding carries the session its committed close
  actually is, where it is one, and a `cause`; the `causes` say what each is, the
  evidence, and what was decided.
- `python scripts/audit_instruments.py` re-runs it and prints only what is new,
  changed or gone against the list. `--write` replaces the findings and carries a
  cause forward only while its finding is unchanged, so anything new lands
  unreviewed until someone gives it one by hand. It needs the network and
  yfinance, so it is not a `truth_check` mode and not in CI.
- For `WTI`, `GOLD` and `SILVER` the list compares a file from before
  2026-10-05 with the provider's continuous symbol, because that is what the
  file read. It does not say whether a close is the nearest-expiry contract's
  settlement, which is what those keys mean (`DATA_FEED.md` sec.1d): 104 gold
  closes differ from `GC=F` and are right. Which weeks are off the rule, and
  what stands in for them, is `data/commodity_settlements.json`, written by
  `scripts/backfill_commodities.py`. A file that names its contract is
  compared with that contract's own history while the provider still serves
  it, and left out once the contract has expired.

## series_audit.json (which session a committed equity bar is)

- The same question for `series` in `data/weekly`, and the same kind of list.
  `scripts/backfill_weekly.py::slice_week` takes the last bar on or before the
  Friday and marks nothing per ticker, so a name with no Friday bar carries an
  earlier session under the Friday date. `DATA_FEED.md` sec.1b, "The equity
  series", has what was found.
- It is not a list of differences from the provider. An equity close is
  adjusted to its fetch date and is supposed to differ from a fresh fetch;
  `_method` in the file says how the session is told instead (volume, and the
  close with the provider's own adjustment factor divided out). `audited` also
  records the audit's reach: how often it names the session before, when that
  bar is put in place of one that passed.
- Most entries are `unverified`: the provider keeps only the last bar of a
  delisted symbol, so AVB's and EA's weeks cannot be checked. That is not an
  ok, and each carries a `cause` saying what else is known about it.
- `python scripts/audit_series.py` re-runs it, with the same `--write` and the
  same rule for causes. Network and yfinance, not a `truth_check` mode, not in
  CI.

## Canonical earnings calendar

`wiki/earnings-surveillance.md` is the ONLY page that states earnings dates.
Sector wikis link to it (`see wiki/earnings-surveillance.md`) instead of restating
dates — two pages stating the same date differently is how the 7/28 audit found
"verified" catalysts that were off by a week. Sector wikis may list THEIR names'
catalysts, but the date column defers to surveillance.

## What this killed

- Stale holdings presented as current (5 critical / 8 high audit findings)
- Fantasy macro numbers (the "Fed regime" that wasn't)
- Fabricated valuations (hash-fallback P/Es — see shadow-book 2026-08-03)
- Silent Saturday failures (2026-08-08: three wikis missed their runs and nobody
  knew until a human diffed commit history — the TTL check makes that automatic)
- Arithmetic that doesn't survive a calculator (T carry +52 vs −10 bps)
- Phantom values with no tombstone (GOOGL $9.11 ghost EPS — now banned, and the
  ban itself is machine-checked every Monday)
