# scan_pipeline — the Council engine

This is a mirror of the live pipeline that runs the Monday Council session.
The EXECUTION copy lives on the scan runner at
`MarketStockPicker/scan_pipeline/`; this repo copy is the public,
versioned mirror the app and any external system should import or read.

## Sync rule

Engine edits land on the runner first (that is what the cron executes),
then get mirrored here. If you are reading this repo copy to reason about
behavior, check the commit date of the last mirror before trusting a line
number. The mirror must never be edited directly on GitHub — fixes made
only here would not run on Monday.

## Layout

- `run_scan.py` — Monday orchestrator: engines, sanity gates (pick-drop
  doctrine), cash floor, consensus.
- `engines/` — cecil (fundamentalist), marky (momentum), ophelia
  (rotation), consensus (weighting + risk caps), personality (journals +
  realized-accuracy feed from `portfolio/history/`).
- `fetch_market_data.py` / `fetch_context.py` — date-pinned yfinance
  fetches; P/E provenance (PE_UNAVAILABLE ledger; no fabricated
  multiples); macro context.
- `snapshot.py` / `snapshot_macro.py` — the committed data feed:
  `data/weekly/` writer (append-only, mandatory `missing[]`), the pure
  `market_state.json` deriver, and the `universe.json` builder. Spec:
  `DATA_FEED.md` at repo root.
- `scripts/` — `backfill_weekly.py` (one-time 104w backfill),
  `recompute_persona_accuracy.py` (one-time 2026-08-11 correction).
- `state/personas.json` — Council persona state (accuracy EMA fed only
  from realized tracker P&L; `last_scored_week` idempotency guard).

Mirrored 2026-08-12 (post engine-repair tranche + data feed launch).
