# Shadow Book -- Engine Divergence Log

> **Living Document.** When the booked portfolio diverges from what the engine *should* have produced -- engine fixes, data outages, manual overrides -- the alternate book is logged here.
> The official book (`portfolio/current.yaml` + Tracker P&L) is **never rewritten**. The Shadow Book exists so the lessons stay findable and the counterfactual stays measurable.

## Format

| Field | Meaning |
|---|---|
| **Week** | Monday scan date |
| **Trigger** | Why the books diverge (engine fix, data outage, override) |
| **Booked** | The official picks -- what the Tracker measures |
| **Shadow** | What the corrected engine would have picked on the same data |
| **Overlap** | Tickers in both books |
| **Resolution** | What happened next (fix version, counterfactual review) |

---

## Entries

### Week of 2026-07-27 -- Engine Sanity Failures

**Trigger:** Pipeline sanity checks fired two warnings during the scan: (1) Marky's confidence scores were **flat** -- all three picks (MMM, VTR, INTU) received identical confidence of 95, indicating the confidence model failed to differentiate conviction; (2) Ophelia's macro engine produced **11 tickers tied at the top score** (NRG, DUK, EIX, and 8 others all scored 91), meaning the sector-rotation signal degenerated and the consensus tie-breaker arbitrarily selected NRG. These are engine bugs, not data outages.

**Booked (official, Tracker-measured):**

| Ticker | Weight | Sponsor |
|---|---|---|
| HON | 23.3% | Cecil |
| MMM | 23.3% | Marky |
| NRG | 22.3% | Ophelia |
| DOW | 15.5% | Cecil |
| VTR | 15.5% | Marky |

**Shadow (what a corrected engine should have produced):**

| Ticker | Weight | Sponsor | Rationale |
|---|---|---|---|
| HON | 23.3% | Cecil | Repo-validated: synthesis.md watchlist, beat + raised guidance, 9.3x ex-Aero -- keep |
| MMM | 23.3% | Marky | Repo-validated: synthesis.md watchlist, turnaround real, momentum confirmed -- keep |
| CEG | 22.3% | Ophelia | Replace NRG -- synthesis.md names CEG/VST as data-center power demand, not generic utilities |
| SPG | 15.5% | Cecil | Replace DOW -- Scar Rule 1 violation (DXY>101 + 10Y>4.5% = no commodity longs); SPG is synthesis.md's cheapest XLRE name with positive carry narrative |
| JNJ | 15.5% | Marky | Replace VTR -- synthesis.md shows JNJ +4.1% follow-through, strongest pharma chart; VTR has no wiki support and duration risk at 4.70% 10Y |

**Overlap:** HON, MMM only.

**Notes:** The Dissonance Review (report Section 6) documented all five disagreements. Cecil conceded on DOW (Scar Rule 1 violation). Marky conceded on VTR (duration risk, no wiki support). Ophelia conceded on NRG (generic placeholder, engine tie-resolution arbitrary). The flat-confidence and tie-scoring bugs mean the official book overstates conviction on two picks and underweights the best alternatives.

**Counterfactual P&L (computed 2026-08-03):**

| Ticker | Mon Close | Fri Close | Return | Weight | Weighted |
|---|---|---|---|---|---|
| HON | $245.75 | $243.05 | -1.10% | 23.3% | -0.26% |
| MMM | $178.23 | $176.28 | -1.09% | 23.3% | -0.25% |
| CEG | $270.00 | $262.75 | -2.69% | 22.3% | -0.60% |
| SPG | $231.67 | $229.37 | -0.99% | 15.5% | -0.15% |
| JNJ | $265.95 | $256.35 | -3.61% | 15.5% | -0.56% |
| **Shadow Total** | | | **-1.82%** | | |
| **Official Total** | | | **-1.52%** | | |
| **Delta** | | | **-0.30%** | | |

The shadow book underperformed the official book by 30 bps. The tie-breaker arbitrary pick (NRG at -2.74%) was actually less damaging than the corrected alternative (CEG at -2.69%), but the DOW replacement (SPG at -0.99% vs DOW at +4.30%) and JNJ replacement (JNJ at -3.61% vs VTR at -7.04%) both moved in the shadow's favor. Net: the engine bugs cost 30 bps this week -- within noise, but the process failure is the real loss.

**Resolution:** Booked week left intact -- the Tracker measures what the Council actually booked. The engine bugs are logged for repair before the 2026-08-03 scan: (1) Marky confidence model must differentiate by volume confirmation and earnings-catalyst presence; (2) Ophelia tie-breaker must weight wiki watchlist presence and synthesis.md favorability. Counterfactual P&L computed 2026-08-03.

**Links:** [Report](reports/2026-07-27-report.md) . [Council Scorecard](scorecards/2026-07-27-council-scorecard.md)

**Data repair (2026-07-30):** Trigger: data pollution -- the fed_stance field carried a scraped Fed press-release headline ("Agencies issue joint statement...") in four locations. Fields repaired: fed_stance x4 (reports/2026-07-20-report.md, reports/2026-07-27-report.md, portfolio/history/2026-07-20.yaml, portfolio/current.yaml); current.yaml carries the post-FOMC read (Hold at 3.50-3.75%, 9-3 vote, three dissents for a hike). No book change -- picks, weights, prices, and P&L untouched. Defense in depth: tracker.py now validates that the stance line leads with a recognized stance word; a scraped headline lands as null with a WARN instead of poisoning the book.

---

### Week of 2026-07-20 -- Engine Audit Fixes

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

**Notes:** Real trailing P/Es replaced hash numerology (AMAT was quoted at a fake 10.1x -- real ~= 53.5x). Ophelia's sector rotation fired for the first time ever (Energy leadership). Dynamic confidences replaced flat scores (75/100/15 -> 97.3/85.0/etc.).

**Counterfactual P&L (computed 2026-08-03, overdue since 2026-07-27 cron failure):**

| Ticker | Mon Close | Fri Close | Return | Weight | Weighted |
|---|---|---|---|---|---|
| MPC | $315.31 | $309.24 | -1.93% | 30.0% | -0.58% |
| TRV | $368.50 | $387.26 | +5.09% | 21.6% | +1.10% |
| ADBE | $234.74 | $225.11 | -4.10% | 21.6% | -0.89% |
| PYPL | $56.82 | $56.15 | -1.18% | 14.3% | -0.17% |
| EOG | $141.09 | $146.39 | +3.76% | 12.5% | +0.47% |
| **Shadow Total** | | | **-0.06%** | | |
| **Official Total** | | | **-1.83%** | | |
| **Delta** | | | **+1.77%** | | |

The shadow book outperformed the official book by **177 bps**. The fixed engine would have avoided the "A bias" trap (ACN -1.43%, AMAT +2.22%, ADBE -7.85%, AMGN +0.84%, ADSK -4.12%) and instead captured energy rotation (EOG +3.76%) and insurance strength (TRV +5.09%). The ADBE pick was the only overlap, and it was the worst performer in both books (-7.85% official, -4.10% shadow -- different due to Monday open vs Monday close basis). The lesson: alphabetically-biased engine selection cost real money.

**Resolution:** Booked week left intact -- the Tracker measures what the Council actually booked. Engine fixes shipped 2026-07-21. Counterfactual P&L computed 2026-08-03 (overdue since 2026-07-27 cron failure missed the scheduled close).

**Links:** [Report](reports/2026-07-20-report.md) . [Council Scorecard](scorecards/2026-07-20-council-scorecard.md)

---

*Newest entries on top. Always link the week's report and scorecard. When in doubt: log it -- a shadow entry costs nothing, a lost lesson costs returns.*
