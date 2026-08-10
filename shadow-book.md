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

### Week of 2026-08-10 -- ENGINE ABORT: Sanity Gate Blocked the Book (4-Way Tie at 108.00)

**Trigger:** The pre-publication sanity gate (hard block, 2026-07-30 doctrine) fired during the 9:03 AM scan: Ophelia's engine produced **4 tickers tied at exactly 108.00** (MSFT, NOW, ORCL, AVGO -- identical base scores plus identical +6 wiki nudges), exceeding the 3-tie limit. Root causes, found same-session: (1) **SPY alias bug** -- `resolve_ticker_alias` maps SPY -> 'S&P 500' but the live price cache keys 'SPY', so every SPY history lookup silently returned []; Ophelia's market-regime term was flat-15 for all names, her volatility discount was zeroed, and her regime theses mislabeled a +3.2% SPY week 'bearish'. (2) **Clamp saturation** -- with Technology up +7.3% on the week, rotation 40 + flow 12 + regime 30 + momentum 12 + rel 8 all pinned at their ceilings for every strong Tech name, making exact ties arithmetically certain.

**Engine repairs shipped same-session (local scan_pipeline):** (1) `get_price_history` now falls back to the raw ticker when the alias resolves to an uncached key; (2) Ophelia Fix 5 de-saturation -- vol band widened 1x -> 4x SPY vol, weekly-momentum clamp +5% -> +12%, relative-momentum clamp +5pp -> +15pp. The repaired engine differentiates cleanly (Ophelia: VSAT 86.9 / ZS 79.0 / HPE 75.6; Marky: AXON 88.4 / VRTX 83.9 / VSAT 81.7; Cecil: PPG 77.0 / ACN 76.1 / SMCI 70.7) and passes the gate.

**Booked (official, Tracker-measured):** NOTHING. The hard rule is explicit -- a failed gate means no book, and a mid-session repair does not un-fire the gate. Cash is a position. This is the first abort in the Council's history.

**Shadow (what the repaired engine would have booked):**

| Ticker | Weight | Sponsor | Rationale |
|---|---|---|---|
| VSAT | 26.0% | Ophelia | Technology rotation anchor; macro score 111; also Marky's #3 (breakout, score 99) |
| AXON | 25.0% | Marky | Strongest tape: +16.0% 4W return, breakout above 4-week MA |
| PPG | 20.0% | Cecil | Deep value at a REAL 16.9x (pe_source: real); score 87 |
| VRTX | 15.8% | Marky | Low-vol uptrend, 2.3% weekly vol, score 99 |
| ACN | 13.2% | Cecil | Quality at a real 14.0x; booked last week at 27.4% and returned +3.46% |

**Overlap:** n/a (no official book).

**Notes:** The shadow book would have run 100% allocated into a week with 3+ regime flags raised (NFP -23K broken threshold, DXY <100 second week, VIX 14.90 complacency) and the July CPI binary on Tuesday 8/12 -- the 10% cash floor (2026-08-09 doctrine) would have forced a trim of ACN or VRTX to ~90% had this book been eligible. Also note the abort killed a genuinely differentiated Cecil/Marky signal to punish an Ophelia engine defect; the repair, not the abort, is the fix. Second Ophelia tie in three weeks (11-way 2026-07-27, 4-way today) -- her harness revision is now on the table per scoreboard escalation rule 5.

**Counterfactual P&L:** to be computed (next Monday close: VSAT/AXON/PPG/VRTX/ACN Monday 2026-08-10 closes -> Friday 2026-08-14 closes, weights above; vs official book = cash = 0.00%).

**Resolution:** Abort honored. Repairs shipped local-only (scan_pipeline is not in the repo). Next Monday's gate is the test of Fix 5. Logged 2026-08-10.

**Links:** [Report](reports/2026-08-10-report.md)

---

### Week of 2026-08-03 -- Data-Integrity Incident: Fabricated P/E on a Booked Pick

**Trigger:** Post-session review found Cecil's #2 position SYM (23.6% weight) carried the thesis "Deep value at 11.3x earnings." SYM (Symbotic) is GAAP loss-making -- trailing P/E deeply negative (~-423), forward P/E ~85. The 11.3x was a hash-based deterministic fallback, not data: the weekly yfinance refresh sources no trailing P/E for negative-EPS names, and `get_pe()` silently substituted a fabricated multiple (the 7/20 audit's "hash numerology," resurfacing through the fallback path).

**Also affected (retro):** DOW's 2026-07-27 thesis quoted "P/E: 13.7" -- same fallback (DOW was in the 24-ticker unavailable list). It won +4.30% anyway; the thesis was still fabricated. 24 of 277 universe tickers had no real P/E on the 2026-08-03 refresh (SYM, DOW, COIN, MRNA, BK, INTC, ZS, and 17 others).

**Engine repair (local, 2026-08-03):** (1) refresh failures are now recorded (`PE_UNAVAILABLE`) and `get_pe()` returns None for them -- fabrication banned; (2) negative trailing P/Es are kept as real data and score ZERO value (a negative multiple is not deep value); (3) theses print no multiple unless the P/E is real and positive; (4) every pick carries `pe_source` (real/none/synthetic) and the pre-publication sanity gate BLOCKS any booked pick with synthetic provenance or a quoted multiple on negative EPS.

**Booked exposure at risk:** SYM 23.6% of the Council book, booked on a fabricated value anchor, and Symbotic reported earnings Wednesday 2026-08-05. The official book is never rewritten -- the position stands -- but the entry is recorded here as a model-risk flag.

**Outcome (logged 2026-08-08):** the risk fired. SYM closed 46.52 on earnings day (8/05), then gapped down to close 39.60 on 8/06 (-14.9% overnight) and finished the week at 40.18. From the Monday 43.21 entry: **-7.0% on the week for a quarter-of-the-book position** -- the single worst pick of the week, sized on a fabricated multiple. The paper trail warned about exactly this three days before the print. Counterfactual (engine-repaired) book: SYM's value leg scores 15 neutral instead of ~30 deep-value, and no "deep value" thesis exists to justify the weight; whether SYM still makes top-3 on quality/safety alone is a live question for next Monday's scan.

**Resolution:** Engine fixed same-day (see above). Counterfactual P&L not computable -- the repair changes thesis text and score composition, not just prices. SYM earnings outcome logged above (2026-08-08).

**Links:** [Report](reports/2026-08-03-report.md)

---

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
