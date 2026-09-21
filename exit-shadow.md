# Exit Shadow Log

> **Living Document (created 2026-08-10). SHADOW ONLY -- no enforcement for ~4 cycles.** For each booked pick, log the exit template it WOULD trade under: stop (default -8% SPEC / -5% CORE from entry), thesis invalidation (the pick's Trigger line), time stop (default 6 weeks, or a named catalyst with a date window), trim plan (default: trim 1/3 at +15%, remainder rides a hard trailing stop at -15% from the high-water mark). The template never alters the book; it exists to generate the evidence base that tunes the numbers before enforcement. Newest entries on top, tagged with the week's Monday date, marked `outcome: to be computed` until scored at the following Monday close.

## Stop-Calibration Summary (4 scored cycles, 2026-08-17 -> 2026-09-08)

> **This block is the evidence base the log was built to produce.** It appears after 4 scored cycles, per the STEP 3b doctrine. Read it as evidence, not yet as enforcement.

**Sample:** 11 position-weeks across 4 booked cycles (2026-08-10 was an ENGINE ABORT -- no book, no templates). 10 CORE (-5%), 1 SPEC (-8%).

| Metric | CORE (-5%) | SPEC (-8%) | All |
|---|---|---|---|
| Position-weeks scored | 10 | 1 | 11 |
| Stops fired | 0 | 1 | 1 |
| Stop helped (saved money) | 0 | 1 (TER, +5.1pp) | 1 |
| Stop hurt (cut a winner) | 0 | 0 | 0 |
| Untouched | 10 | 0 | 10 |
| +15% trim reached | 0 | 0 | 0 |

**Deepest intraweek drawdown from entry, CORE names (the number that decides the stop):**

| Rank | Position | Week | Low vs Entry | Headroom Left Above Stop | Week Finished |
|---|---|---|---|---|---|
| 1 | ETN | 2026-09-08 | -3.66% | 1.41% | **+1.01% (green)** |
| 2 | VICI | 2026-08-24 | -3.45% | 1.62% | -3.00% |
| 3 | ALL | 2026-08-17 | -3.36% | 1.72% | -2.98% |
| 4 | HIG | 2026-08-17 | -1.92% | 3.24% | -1.85% |
| 5 | HIG | 2026-08-31 | -1.59% | 3.59% | -0.08% |
| 6 | VICI | 2026-08-17 | -1.15% | 4.07% | +1.55% |
| 7 | ALL | 2026-08-31 | -1.06% | 4.15% | -0.21% |
| 8 | LMT | 2026-09-08 | -0.83% | 4.39% | -0.39% |
| 9 | HIG | 2026-08-24 | -0.63% | 4.60% | +0.87% |
| 10 | ALL | 2026-08-24 | never below entry | 5.79% | +2.54% |

**What the data says, stated against the hypothesis it could have supported:**

1. **The -8% SPEC stop is the only one with a firing, and it earned its keep.** TER (2026-08-17) hit it Tuesday and saved 5.1pp against a -13.07% actual. One observation is not a mandate, but it is the only direct evidence in the file and it points one way: keep -8% on SPEC.
2. **The -5% CORE stop has never fired in 10 position-weeks, and tightening it would have COST money, not saved it.** The deepest CORE drawdown on record is ETN's -3.66% -- and ETN closed the week GREEN at +1.01%. A -3.5% CORE stop would have fired on ETN and VICI: ETN would have turned +1.01% into roughly -4% (a ~5pp self-inflicted loss), VICI would have turned -3.00% into -3.5% (another small loss). **Every tightening this sample permits makes the book worse.** The naive read of "the CORE stop never fires, so it must be too loose" is exactly backwards.
3. **Implied best stop from the data: leave both numbers where they are.** CORE -5% sits in a genuine dead zone -- far enough below the -3.66% worst observed drawdown to avoid whipsaw, and no CORE position has come near a loss deep enough to need it. There is no number in this sample that improves on -5% CORE / -8% SPEC.
4. **The trim plan is completely untested.** Zero of 11 position-weeks reached +15%; the best week on record is ALL's +2.54%. The trim leg of the template has produced no evidence at all and should not be promoted on the strength of the stop leg.

**Promotion recommendation: NOT YET -- stay in shadow.** The sample is 11 position-weeks with exactly one firing, drawn almost entirely from a book carrying 60-73% cash, and it is CORE-dominated 10:1. The one number with real support (-8% SPEC) has a single observation. The honest reading is that the template has not yet been tested by a losing week deep enough to matter -- the book's worst pick since the log opened was cut by the one stop that fired. Continue shadow logging; revisit at 8 scored cycles or after the first week a CORE position closes below -5%, whichever comes first.

---

## Entries

### Week of 2026-09-21

Book: XOM 19.7% / AMD 16.8% / HIG 15.7% / cash 47.8%. **Entry prices = validated Monday 2026-09-21 opens** (each bar checked low <= open <= high before the tracker was run at ~10:36 ET; SPY $766.25). First week since the log opened that the Council and the Arena share the same entry basis. Note AMD gapped **+4.3%** at the open ($583.94 vs Friday's $559.82 close), so its levels below sit well above the Friday chart.

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| XOM @ $160.96 (Marky) | **CORE** -- mega-cap integrated major, deepest liquidity in the sector | -5% = $152.91 | XLE weekly close below $63.46 (breakout line, wiki/energy.md; wiki/synthesis.md Section 5) | Named catalysts: OPEC+ meets Oct 4; XOM Q3 print Oct 30 (wiki/earnings-surveillance.md); 6-week backstop Nov 2 | Trim 1/3 at +15% ($185.10); remainder trails -15% from HWM |
| AMD @ $583.94 (Ophelia) | **CORE** -- mega-cap semis, broad sponsorship; flagged hot (RSI 65.4 at Friday close, then a +4.3% gap) | -5% = $554.74 | SMH close below $560.28 (wiki/semiconductors.md Near Support; wiki/synthesis.md Section 5 SMH row) | Named catalyst: MU FQ4 Wed Sep 30 AMC is the leadership trade's verdict; 6-week backstop Nov 2 | Trim 1/3 at +15% ($671.53); remainder trails -15% from HWM |
| HIG @ $131.69 (Cecil) | **CORE** -- large-cap P&C insurer | -5% = $125.11 | 10Y-3M curve inverts (macro/facts.json rates.curve_10y_3m_bps = +102 at booking) | Named gates: $192B 2/5/7-year auctions Sep 22-24; P&C Q3 prints late October; 6-week backstop Nov 2 | Trim 1/3 at +15% ($151.44); remainder trails -15% from HWM |

Note: ALL (Cecil) and DE (Marky) were TRIGGER-BLOCKED at booking -- their 2026-09-14 invalidations fired on 9/18 -- and VICI was blocked as a promotion; no exit template attaches. Their counterfactual lives in shadow-book.md.

**Template stress note:** AMD's stop ($554.74) sits ABOVE SMH's $560.28 invalidation in price terms for AMD itself -- the gap means the stop leg may fire before the thesis leg for the first time in this log. HIG's -3.81% intraweek low last week (closest CORE call on record) is the reference for whether -5% is still dead-zone.

outcome: to be computed (score Monday 2026-09-28 against date-pinned daily bars 2026-09-21 -> 2026-09-25).

---

### Week of 2026-09-14

Book: ALL 18.3% / PSX 16.7% / HIG 14.8% / DE 10.0% / cash 40.2%. **Entry prices = Friday 2026-09-11 closes**, not Monday opens: yfinance had not yet published the 2026-09-14 daily bar when the tracker ran at 09:53 ET, and tracker.py took its documented close-based fallback (warning emitted for all five symbols including SPY). Recorded here because the entry basis changes every level below it.

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| ALL @ $253.71 (Cecil) | **CORE** -- mega-cap P&C insurer, liquid, broad institutional sponsorship | -5% = $241.02 | XLF weekly close below its 50D at $57.11 (wiki/financials.md: "THE line -- Friday closed 14 cents above it") | 6 weeks (Oct 26); named gates inside the window: FOMC Sep 15-16, BOJ Sep 17-18 | Trim 1/3 at +15% ($291.77); remainder trails -15% from HWM |
| PSX @ $259.47 (Marky) | **CORE** -- mega-cap refiner, liquid; flagged crowded (complex trades 8.1-15.0% above freshly raised targets) | -5% = $246.50 | XLE weekly close below $63.46 (failed-breakout-#2 line, wiki/synthesis.md Section 5) | Named catalyst overrides the clock: refiner Q3 prints late October are the verdict on record diesel cracks; 6-week backstop (Oct 26) | Trim 1/3 at +15% ($298.39); remainder trails -15% from HWM |
| HIG @ $136.36 (Cecil) | **CORE** -- large-cap P&C insurer, same carry thesis as ALL | -5% = $129.54 | 10Y-3M curve inverts (macro/facts.json rates.curve_10y_3m_bps = +106 at booking) | 6 weeks (Oct 26); same named gates | Trim 1/3 at +15% ($156.81); remainder trails -15% from HWM |
| DE @ $675.74 (Marky) | **CORE** -- mega-cap industrial, liquid | -5% = $641.95 | XLI weekly close below its 200D at $170.68 (wiki/synthesis.md Section 5; XLI $172.37 at booking) | Named catalyst: FDX prints Thu Sep 17, the first live report from the oil front; 6-week backstop (Oct 26) | Trim 1/3 at +15% ($777.10); remainder trails -15% from HWM |

Note: EVRG (Ophelia) and AES (Cecil) were TRIGGER-BLOCKED at booking under the DOW rule (XLU $42.39 inside wiki/utilities.md's own "bearish below $43.00, full-stop" zone) and are not booked; no exit template attaches. Their counterfactuals are tracked through shadow-book.md instead.

**Template stress note for the calibration record:** ALL's stop ($241.02) and DE's stop ($641.95) both sit further from entry than any drawdown in the 11-position-week sample above, but ALL's *trigger* (XLF 50D, 0.24% headroom) is by far the tightest invalidation this log has ever carried. This is the first week where the thesis-invalidation leg is overwhelmingly more likely to fire than the stop leg -- exactly the asymmetry the summary block says is untested.

outcome (scored 2026-09-21 against date-pinned daily bars 2026-09-14 -> 2026-09-18, entry = Fri 2026-09-11 close):

| Pick | Week Low (day) | Low vs Entry | Headroom Above Stop | Stop Fired? | Week High (day) | High vs Entry | +15% Trim? | Fri Close | Actual | Trigger Status at Fri Close |
|---|---|---|---|---|---|---|---|---|---|---|
| ALL | $247.78 (Fri) | -2.34% | 2.80% | No | $258.76 (Mon) | +1.99% | No | $249.83 | -1.53% | **FIRED** -- XLF closed $55.86, below the $57.11 50D line (first closed below it Mon 9/14 at $57.03) |
| PSX | $253.41 (Mon) | -2.34% | 2.80% | No | $277.12 (Fri) | +6.80% | No | $273.13 | +5.26% | Intact -- XLE $64.31 vs $63.46 line (tested $63.46 to the penny Thu intraday, held) |
| HIG | $131.16 (Fri) | -3.81% | 1.25% | No | $138.65 (Mon) | +1.68% | No | $131.89 | -3.28% | Intact -- 10Y-3M curve +102bp (macro/facts.json 2026-09-19), not inverted |
| DE | $665.45 (Wed) | -1.52% | 3.66% | No | $689.37 (Tue) | +2.02% | No | $683.99 | +1.22% | **FIRED** -- XLI closed $169.75, below the $170.68 200D line (below it every session from Mon 9/14) |

Verdict: stop leg -- 0 of 4 fired, 0 saved, 0 cost; HIG's -3.81% low (1.25% headroom, Fri) is the closest CORE call in the log history, beating ETN's -3.66% -- and unlike ETN it closed near its low (-3.28%). A tighter ~-3.5% CORE stop would have fired Friday and exited near -3.5% vs the actual -3.28% close: a small cost (~0.2pp), not a save. Tightening still has zero support in the data. Trim leg -- untested again; PSX's +6.80% is the best intraweek high on record, still less than half the +15% trim. Thesis-invalidation leg -- FIRED ON 2 OF 4 for the first time in the log: ALL (fired, lost -1.53%) and DE (fired, finished GREEN +1.22%). One right, one wrong; the invalidation leg is now the most active part of the template, as last week's stress note predicted. Running sample: 15 position-weeks, 1 stop firing (TER), 2 invalidation firings, 0 trims.

---

### Week of 2026-09-08

Book: LMT 13.3% / ETN 13.3% / cash 73.4%. Entry prices = Tuesday 2026-09-08 live morning prints at booking (week open shifted from Monday 9/7 -- Labor Day; tracker, portfolio/current.yaml).

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| LMT @ $526.23 (Cecil) | **CORE** -- large-cap defense prime, real beat + target hike, pure multiple compression | -5% = $499.92 | XLI weekly close below its 200D (~$170-171, hard floor $168.00), or 10Y close > 4.85% | 6 weeks (Oct 20); named gates inside the window: CPI Sep 11, FOMC Sep 15-16, BOJ Sep 17-18 | Trim 1/3 at +15% ($605.16); remainder trails -15% from HWM |
| ETN @ $421.11 (Cecil) | **CORE** -- AI data-center power buildout, real 65% YoY growth, but 26x forward | -5% = $400.05 | Same XLI 200D backstop, or a hyperscaler capex cut materially undercutting the AI-power thesis | 6 weeks (Oct 20); same named gates | Trim 1/3 at +15% ($484.28); remainder trails -15% from HWM |

outcome (scored 2026-09-14, date-pinned daily bars 2026-09-08 -> 2026-09-11):

| Pick | Stop Touched? | +15% Trim Reached? | Would-Have Return | Actual Booked Return | Verdict |
|---|---|---|---|---|---|
| LMT @ $526.23 (stop $499.92) | No (week low $521.87, Fri 2026-09-11 -- 4.39% above the stop) | No (week high $543.59, Wed 2026-09-09) | -0.39% (held) | -0.39% | no difference |
| ETN @ $421.11 (stop $400.05) | No (week low $405.70, Thu 2026-09-10 -- **1.41% above the stop, the closest call in the log's history**) | No (week high $430.25, Tue 2026-09-08) | +1.01% (held) | +1.01% | no difference -- **but the near-miss is the finding** |

Cycle tally: stops helped 0, hurt 0, untouched 2. The entry worth reading twice is ETN: it drew down -3.66% from entry on Thursday, came within $5.65 of its -5% CORE stop, and then closed the week at +1.01%. Any stop tighter than -3.66% would have converted the book's only winner into a roughly -4% loss. That is the first hard evidence in this log that the CORE stop can be too tight, and it arrives in the same week the stop was never actually hit.

Scored cycles to date: **4 of 4 -- the stop-calibration summary block is now live at the top of this file.**

---

### Week of 2026-08-31

Book: ALL 13.3% / HIG 13.3% / cash 73.4%. Entry prices = Monday 2026-08-31 live morning prints at booking (tracker, portfolio/current.yaml).

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| ALL @ $260.12 (Cecil) | **CORE** -- mega-cap P&C insurer, liquid, broad institutional sponsorship | -5% = $247.11 | XLF weekly close < $55.00, or 10Y close > 4.85% | 6 weeks (Oct 12); named gates inside the window: jobs report Fri Sep 4 and FOMC Sep 15-16 | Trim 1/3 at +15% ($299.14); remainder trails -15% from HWM |
| HIG @ $138.48 (Cecil) | **CORE** -- large-cap P&C insurer, same carry thesis as ALL | -5% = $131.56 | 10Y-3M curve inverts, or 10Y close > 4.85%, or XLF weekly close < $55.00 | 6 weeks (Oct 12); named gates inside the window: jobs report Fri Sep 4 and FOMC Sep 15-16 | Trim 1/3 at +15% ($159.25); remainder trails -15% from HWM |

Note: AES (Cecil, engine #3) was TRIGGER-BLOCKED at booking (DOW rule -- 10Y 4.72% vs the 4.60% bond-proxy line; see the 2026-08-31 report, Council Deliberation #1) and is not booked; no exit template attaches. Its counterfactual is tracked through the shadow-book.md entry instead.

outcome (scored 2026-09-08, date-pinned daily bars 2026-08-31 -> 2026-09-04):

| Pick | Stop Touched? | +15% Trim Reached? | Would-Have Return | Actual Booked Return | Verdict |
|---|---|---|---|---|---|
| ALL @ $260.12 (stop $247.11) | No (week low $257.37, Tue 2026-09-01) | No (week high $266.45, Thu 2026-09-03) | -0.21% (held) | -0.21% | no difference |
| HIG @ $138.48 (stop $131.56) | No (week low $136.28, Tue 2026-09-01) | No (week high $140.41, Thu 2026-09-03) | -0.08% (held) | -0.08% | no difference |

Cycle tally: stops helped 0, hurt 0, untouched 2. Neither position traded within 4% of its -5% CORE stop, and neither reached the +15% trim -- a quiet week for the template, consistent with the book's own -0.04% weighted return.

Scored cycles to date: 3 of 4. The stop-calibration summary block appears after 4 scored cycles (one more cycle to go).

---

### Week of 2026-08-24

Book: ALL 13.3% / HIG 13.3% / VICI 13.3% / cash 60.1%. Entry prices = Monday 2026-08-24 opens (tracker, portfolio/current.yaml).

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| ALL @ $254.13 (Cecil) | **CORE** -- mega-cap P&C insurer, liquid, broad institutional sponsorship | -5% = $241.42 | XLF weekly close < $55.00, or 10Y > 4.85% | 6 weeks (Oct 5) | Trim 1/3 at +15% ($292.25); remainder trails -15% from HWM |
| HIG @ $137.36 (Cecil) | **CORE** -- large-cap P&C insurer, same carry thesis as ALL | -5% = $130.49 | 10Y-3M curve inverts, or 10Y >= 4.85% | 6 weeks (Oct 5) | Trim 1/3 at +15% ($157.96); remainder trails -15% from HWM |
| VICI @ $26.67 (Cecil) | **CORE** -- net-lease REIT, bond-proxy equity | -5% = $25.34 | XLRE weekly-closes below its 50D $44.82, or 10Y closes > 4.75% | 6 weeks (Oct 5) | Trim 1/3 at +15% ($30.67); remainder trails -15% from HWM |

outcome (scored 2026-08-31, date-pinned daily bars 2026-08-24 -> 2026-08-28):

| Pick | Stop Touched? | +15% Trim Reached? | Would-Have Return | Actual Booked Return | Verdict |
|---|---|---|---|---|---|
| ALL @ $254.13 (stop $241.42) | No (week low $255.41, Mon 2026-08-24) | No (week high $262.19) | +2.54% (held) | +2.54% | no difference |
| HIG @ $137.36 (stop $130.49) | No (week low $136.49, Thu 2026-08-27) | No (week high $140.31) | +0.87% (held) | +0.87% | no difference |
| VICI @ $26.67 (stop $25.34) | No (week low $25.75, Thu 2026-08-27 -- $0.41 above the stop) | No (week high $27.15) | -3.00% (held) | -3.00% | no difference -- the -5% CORE stop stayed clear of a losing but orderly grind-down |

Cycle tally: stops helped 0, hurt 0, untouched 3. VICI lost -3.00% on the week but never traded closer than $0.41 (1.6%) to its $25.34 stop; the template rides unchanged.

Scored cycles to date: 2 of 4. The stop-calibration summary block appears after 4 scored cycles.

---

### Week of 2026-08-17

Book: TER 20.4% / ALL 15.1% / HIG 15.1% / VICI 9.8% / cash 39.6%. Entry prices = Monday 2026-08-17 (tracker, portfolio/current.yaml).

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| TER @ $432.26 (Ophelia) | **SPEC** -- NVDA-chain semi-test name, catalyst-gated by the Aug 26 print | -8% = $397.68 | XLK loses its 50D $182.80, or NVDA < $210 pre-print, or 10Y closes > 4.75% | Named catalyst overrides the clock: NVDA reports Wed Aug 26 AMC -- reassess the morning after; no carry into September without a confirmed beat | Trim 1/3 at +15% ($497.10); remainder trails -15% from high-water mark |
| ALL @ $261.63 (Cecil) | **CORE** -- mega-cap P&C insurer, liquid, broad institutional sponsorship | -5% = $248.55 | XLF weekly close < $58.00 (breakout fakeout) | 6 weeks (Sep 28) | Trim 1/3 at +15% ($300.87); remainder trails -15% from HWM |
| HIG @ $138.66 (Cecil) | **CORE** -- large-cap P&C insurer, same steepening-curve thesis as ALL | -5% = $131.73 | 10Y-3M curve inverts, or 10Y >= 4.75%, or XLF weekly close < $58.00 | 6 weeks (Sep 28) | Trim 1/3 at +15% ($159.46); remainder trails -15% from HWM |
| VICI @ $26.11 (Cecil) | **CORE** -- net-lease REIT, bond-proxy equity | -5% = $24.80 | XLRE loses its 50D $44.67, or 10Y closes > 4.75% | 6 weeks (Sep 28) | Trim 1/3 at +15% ($30.02); remainder trails -15% from HWM |

outcome (scored 2026-08-24, date-pinned daily bars 2026-08-17 -> 2026-08-21):

| Pick | Stop Touched? | +15% Trim Reached? | Would-Have Return | Actual Booked Return | Verdict |
|---|---|---|---|---|---|
| TER @ $432.26 (stop $397.68) | **YES -- Tue 2026-08-18 low $392.18** | No (week high $444.17) | -8.00% (stopped Tue) | -13.07% | **STOP SAVED ~5.1pp** -- the week's worst pick would have been cut Tuesday |
| ALL @ $261.63 (stop $248.55) | No (week low $252.83) | No | -2.98% (held) | -2.98% | no difference |
| HIG @ $138.66 (stop $131.73) | No (week low $136.00) | No | -1.85% (held) | -1.85% | no difference |
| VICI @ $26.11 (stop $24.80) | No (week low $25.81) | No (week high $26.83) | +1.55% (held) | +1.55% | no difference |

Cycle tally: stops helped 1 (TER, +5.1pp vs actual), hurt 0, untouched 3. The -8% SPEC stop would have cut the book's worst pick two days early.

Scored cycles to date: 1 of 4. The stop-calibration summary block appears after 4 scored cycles.

---

### Week of 2026-08-10 -- NO BOOK (ENGINE ABORT)

No exit templates: the sanity gate blocked the book (see shadow-book.md, week of 2026-08-10). The shadow book's five would-be picks (VSAT/AXON/PPG/VRTX/ACN) are tracked for counterfactual P&L in the Shadow Book only -- they were never booked, so no stops/trims attach. Scored cycles to date: 0 of 4; the stop-calibration summary block appears after 4 scored cycles.

---