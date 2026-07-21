# Shadow Book — Engine Divergence Log

> **Living Document.** When the booked portfolio diverges from what the engine *should* have produced — engine fixes, data outages, manual overrides — the alternate book is logged here.
> The official book (`portfolio/current.yaml` + Tracker P&L) is **never rewritten**. The Shadow Book exists so the lessons stay findable and the counterfactual stays measurable.

## Format

| Field | Meaning |
|---|---|
| **Week** | Monday scan date |
| **Trigger** | Why the books diverge (engine fix, data outage, override) |
| **Booked** | The official picks — what the Tracker measures |
| **Shadow** | What the corrected engine would have picked on the same data |
| **Overlap** | Tickers in both books |
| **Resolution** | What happened next (fix version, counterfactual review) |

---

## Entries

### Week of 2026-07-20 — Engine Audit Fixes

**Trigger:** Full pipeline audit after every pick clustered alphabetically (the "A" bias). Root causes: snake/camel key mismatch in 3 files, sector rotation that could never fire (Friday-labeled bars vs Monday exact-match), hash-based fake P/Es, bucketed scores with alphabetical tie-breaks, leaky consensus cap, free volatility points on missing data. Six fixes shipped 2026-07-21.

**Booked (official, Tracker-measured):**

| Ticker | Weight | Sponsor |
|---|---|---|
| ACN | 30.2% | Marky |
| AMAT | 23.3% | Cecil |
| ADBE | 20.7% | Marky |
| AMGN | 15.5% | Cecil |
| ADSK | 10.3% | Marky |

**Shadow (fixed engine, same 2026-07-20 data):**

| Ticker | Weight | Sponsor |
|---|---|---|
| MPC | 30.0% | Ophelia |
| TRV | 21.6% | Cecil |
| ADBE | 21.6% | Marky |
| PYPL | 14.3% | Cecil |
| EOG | 12.5% | Ophelia |

**Overlap:** ADBE only.

**Notes:** Real trailing P/Es replaced hash numerology (AMAT was quoted at a fake 10.1x — real ≈ 53.5x). Ophelia's sector rotation fired for the first time ever (Energy leadership). Dynamic confidences replaced flat scores (75/100/15 → 97.3/85.0/etc.).

**Resolution:** Booked week left intact — the Tracker measures what the Council actually booked. At the 2026-07-27 close, compute the Shadow Book's counterfactual P&L (Monday 7/20 closes → Friday 7/24 closes for MPC/TRV/ADBE/PYPL/EOG) and compare against the official week before archiving.

**Links:** [Report](reports/2026-07-20-report.md) · [Council Scorecard](scorecards/2026-07-20-council-scorecard.md)

---

*Newest entries on top. Always link the week's report and scorecard. When in doubt: log it — a shadow entry costs nothing, a lost lesson costs returns.*
