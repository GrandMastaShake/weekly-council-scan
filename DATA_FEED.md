# Data Feed Spec

What the scan writes, what the app reads, and what never gets committed.

One fetch per scan, four outputs. Three are committed and permanent; one is cached and disposable.

```
weekly-council-scan/
├── data/
│   ├── weekly/
│   │   ├── 2026-08-08.json          committed · closes the council saw
│   │   └── 2026-08-08.corrected.json  committed · only if a provider restates
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

**Rules**

- **Closes only.** No intraday, no bid/ask, no derived fields. This file is an observation.
- **`missing` is required and never empty-by-omission.** A ticker that could not be fetched is listed with a reason. A silently absent ticker is indistinguishable from a ticker that didn't exist, and that ambiguity is what the agents fill in from priors.
- **`fetched_at` is UTC and real.** It is how you detect a scan that ran against a stale cache.
- **Never edit.** If a provider restates, write `<date>.corrected.json` with the same shape plus `"corrects": "2026-08-08.json"` and `"reason": "..."`. Readers prefer the correction; the original stays.

**Size.** ~300 series entries + 7 instruments ≈ 15–18KB per file. 104 files per two years ≈ 1.7MB. No pruning, no rotation, ever.

**Ticker set (amended 2026-08-11, owner decision — supersedes the original charted-set-only text).** The FULL scan universe is committed: every ticker in `STOCK_UNIVERSE` (277) plus SPY, QQQ, DIA, IWM, SMH and the 11 sector ETFs in `series`; US10Y/US2Y in `rates`; VIX in `vol`; WTI/GOLD/SILVER in `commodities`; DXY in `fx`. Rationale: the pipeline already fetches the whole universe at scan time, so the marginal cost is zero, and the file becomes the complete record of what the Council could have seen — not just what the app happened to chart. Instrument notes: US2Y is sourced from the 2-year yield future (2YY=F), honestly labeled; US10Y is ^TNX, which current Yahoo serves as a plain yield (a legacy ×10 guard divides only if a raw value >20 ever appears); volumes are null for indexes/rates, never invented.

---

## 2. `data/market_state.json`

Derived, not fetched. Overwritten every scan — this one *is* a snapshot of now, and history lives in the weekly files. Full shape is in `MARKET_GROUNDING.md` §1; the generation rules:

| Field | Computed from |
| --- | --- |
| `d1w` / `d4w` / `d13w` / `d52w` | The weekly files. Never re-fetched. |
| `pctile_2y` | Rank of the current level within the trailing 104 weekly files |
| `corr_spy_4w` | Trailing 4 weekly returns vs SPY's |
| `corr_prev` | The same figure from last week's `market_state.json` |
| `regime` | Rule-based, from VIX percentile + ISM + curve + policy odds |

Two rules that matter more than the contents:

- **Every field present, always.** Unavailable values are `null` with a sibling `_reason`. Never omitted.
- **Derivation is pure.** Given the weekly files plus `macro/facts.json` (macro prints, policy fields, and the upcoming-events gate live there, not in prices), regenerating `market_state.json` produces a byte-identical file. If it doesn't, something is reading live data it shouldn't be. Enforced by `truth_check.py --derive` every Monday.

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

## 4. Not committed

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
