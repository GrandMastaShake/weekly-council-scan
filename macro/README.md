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

## truth_check.py (scripts/)

Stdlib-only validators. The cron jobs download repo files to a local temp dir and
run it there — the workspace is NOT a repo clone (never run it against a checkout).

```
python scripts/truth_check.py --repo <dir> [--staleness] [--facts] [--lint]
       [--warn-days 7] [--fail-days 14] [--max-fetch 60]
```

(no mode flag = run everything; exit 1 on any FAIL)

| Check | WARN | FAIL |
|---|---|---|
| **Staleness TTL** — every `wiki/*.md` "Last updated" stamp | > 7 days old | > 14 days old |
| **Facts freshness** — facts.json `generated` date | — | > 8 days old |
| **Facts accuracy** — each yahoo-sourced field vs live close | fetch failed | deviation > `tolerance_pct` |
| **Spread arithmetic** — computed curve spreads recompute | — | off by > 3 bps |
| **Holdings lint** — (TICKER, $price) rows in wiki tables vs live closes | dev > 3% | dev > 15% = impossible row |
| **WoW arithmetic** — weekly-change columns recomputed | sign flip or off by > 2 pts | — |

## Who runs what, when (folded into EXISTING jobs — cron grid is full)

- **Canary Watch (Sat 3:39 PM):** regenerates `macro/facts.json` from its own fetch
  and pushes it alongside `wiki/canary-watch.md`.
- **Synthesis (Sat 4:56 PM):** reads facts.json FIRST; every macro number in
  synthesis.md and the README Market Brief must match it. Runs
  `truth_check.py --staleness` and names any stale wiki in the synthesis.
- **Monday Council Scan (9:03 AM):** STEP 0c Truth Gate — runs
  `truth_check.py --staleness --facts` before the pipeline. WARN = note it in the
  report and prefer fresh fetches over the stale page. FAIL (any wiki > 14d, or
  facts.json missing/stale/contradicted by market data) = ENGINE ABORT path:
  publish the report with the abort banner, book no positions, log to shadow-book.
- **Weekly lint:** Monday job also runs `--lint` when time permits; impossible rows
  get flagged in the report and repaired in place (with a note) or queued for the
  next Saturday crew prompt.

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
