# Exit Shadow Log

> **Living Document (created 2026-08-10). SHADOW ONLY -- no enforcement for ~4 cycles.** For each booked pick, log the exit template it WOULD trade under: stop (default -8% SPEC / -5% CORE from entry), thesis invalidation (the pick's Trigger line), time stop (default 6 weeks, or a named catalyst with a date window), trim plan (default: trim 1/3 at +15%, remainder rides a hard trailing stop at -15% from the high-water mark). The template never alters the book; it exists to generate the evidence base that tunes the numbers before enforcement. Newest entries on top, tagged with the week's Monday date, marked `outcome: to be computed` until scored at the following Monday close.

## Stop-Calibration Summary (7 scored cycles, 2026-08-17 -> 2026-09-28)

> **This block is the evidence base the log was built to produce.** Re-written 2026-10-05 after the revisit trigger was met (first CORE close below -5%, HIG, week of 2026-09-21). It replaces the 4-cycle block of 2026-09-14; that block's numbers are all carried in the tables below. Read it as evidence, not yet as enforcement.

**Sample:** 21 position-weeks across 7 booked cycles (2026-08-10 was an ENGINE ABORT -- no book, no templates). 20 CORE (-5%), 1 SPEC (-8%).

| Metric | CORE (-5%) | SPEC (-8%) | All |
|---|---|---|---|
| Position-weeks scored | 20 | 1 | 21 |
| Stops fired | 1 (HIG, 2026-09-21) | 1 (TER, 2026-08-17) | 2 |
| Stop helped (saved money) | 1 (+0.66pp) | 1 (+5.1pp) | 2 |
| Stop hurt (cut a winner) | 0 | 0 | 0 |
| Untouched | 19 | 0 | 19 |
| +15% trim reached | 0 | 0 | 0 |

**Deepest intraweek drawdown from entry, CORE names (the number that decides the stop):**

| Rank | Position | Week | Low vs Entry | Stop Fired? | Week Finished |
|---|---|---|---|---|---|
| 1 | HIG | 2026-09-21 | -5.77% | **Yes** (Fri) | -5.66% |
| 2 | META | 2026-09-28 | -4.96% | No (held by $0.29) | -2.93% |
| 3 | AMD | 2026-09-28 | -4.61% | No | **+1.44% (green)** |
| 4 | AAPL | 2026-09-28 | -4.28% | No | -1.96% |
| 5 | HIG | 2026-09-14 | -3.81% | No | -3.28% |
| 6 | ETN | 2026-09-08 | -3.66% | No | **+1.01% (green)** |
| 7 | VICI | 2026-08-24 | -3.45% | No | -3.00% |
| 8 | ALL | 2026-08-17 | -3.36% | No | -2.98% |
| 9 | XOM | 2026-09-21 | -3.17% | No | -0.23% |
| 10 | ALL | 2026-09-14 | -2.34% | No | -1.53% |
| 11 | PSX | 2026-09-14 | -2.34% | No | **+5.26% (green)** |
| 12 | HIG | 2026-08-17 | -1.92% | No | -1.85% |
| 13 | HIG | 2026-08-31 | -1.59% | No | -0.08% |
| 14 | DE | 2026-09-14 | -1.52% | No | **+1.22% (green)** |
| 15 | VICI | 2026-08-17 | -1.15% | No | +1.55% |
| 16 | ALL | 2026-08-31 | -1.06% | No | -0.21% |
| 17 | LMT | 2026-09-08 | -0.83% | No | -0.39% |
| 18 | HIG | 2026-08-24 | -0.63% | No | +0.87% |
| 19 | AMD | 2026-09-21 | -0.29% | No | +8.00% |
| 20 | ALL | 2026-08-24 | never below entry | No | +2.54% |

**What each alternative CORE stop would have done to this sample** (sum of per-position differences vs the actual week-end result, in points of the position, not of the book; a fired stop is assumed filled at the stop level):

| CORE stop | Fires on | Net vs holding to Friday |
|---|---|---|
| -6.0% | nothing (HIG's low was -5.77%) | 0.00 -- gives back the one saving on record |
| **-5.0% (current)** | HIG 09-21 | **+0.66** |
| -4.5% | HIG, META, AMD (09-28) | +1.16 - 1.57 - 5.94 = **-6.35** |
| -4.0% | the above + AAPL | +1.66 - 1.07 - 5.44 - 2.04 = **-6.89** |
| -3.5% | the above + HIG 09-14, ETN | +2.16 - 0.57 - 4.94 - 1.54 - 0.22 - 4.51 = **-9.62** |

**What the data says:**

1. **-5% CORE is the only level in the table that made money.** It fired once, on the one position that kept falling. Every tighter level fires on AMD's week of 2026-09-28, which traded 4.61% under entry on Monday and finished +1.44%. A looser level misses HIG.
2. **The margin is thin and should be said so.** The gap between "best level in the sample" and "fires on META" was $0.29 on a $750 stock. One more tick on 2026-09-28 and the -5% row would read +0.66 - 2.07 = -1.41. The finding is that -5% is not worse than its neighbours, not that it is tuned.
3. **Entry day does the damage, not the week.** All three CORE names in the 2026-09-28 book made their deep lows inside the first four sessions from a Monday-open entry; from Monday's close the same book was +0.98%. A stop measured from the open is partly measuring the entry basis. Worth one more cycle of evidence before reading anything into it.
4. **The -8% SPEC stop still has one observation** (TER, saved 5.1pp). No SPEC name has been booked since 2026-08-17. Keep -8%.
5. **Thesis-invalidation legs have fired four times** (ALL and DE 2026-09-14, XOM 2026-09-21, META 2026-09-28). Only META's fired mid-week on a daily-close line, and exiting on it would have cost 0.38pp (fired by three cents, stock drifted up). The other three fired on weekly closes, where the exit and the Friday close are the same price. The thesis leg has earned its keep as a re-entry block -- the books that ignored the fired lines lost to the booked ones by 1.41pp and 0.62pp in the two weeks scored like-for-like (shadow-book.md) -- not yet as an intraweek exit.
6. **The trim plan is still untested.** Zero of 21 position-weeks reached +15%. The best intraweek high on record is AMD's +9.43% (2026-09-21).

**Promotion recommendation: NOT YET -- stay in shadow, with a narrower question.** The stop numbers no longer need defending against tightening; the sample answers that. What it cannot answer is whether enforcing -5% CORE helps a book that is now 80% invested in five correlated leadership names, because the three deepest non-firing drawdowns all came from that kind of book in a single week. Revisit at 10 scored cycles, or the first week two CORE stops fire together, whichever comes first.

---

## Entries

### Week of 2026-10-05

Book: SNPS 21.3% / JCI 17.3% / NDSN 14.8% / AMAT 13.6% / LRCX 13.0% / cash 20.0%. **Entry prices = validated Monday 2026-10-05 opens** (tracker.py --open run ~10:05 ET by the post-open booking task; every price sits inside the day's 1-minute range so far, entry_price_source: open for all five; SPY $769.69 open). Three of five names (SNPS, JCI, NDSN) are in no wiki, and the book rests on two sector lines (XLI for JCI/NDSN, SMH for AMAT/LRCX) plus XLK for SNPS -- a single sector break can fire several thesis legs at once.

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| SNPS @ $496.25 (Ophelia) | **SPEC** -- not in any wiki; +15.06% last week at RSI 74.1 (chase), tightest trigger (0.5% headroom) | -8% = $456.55 | XLK close under $198.73 (failed-breakout line, wiki/synthesis.md Section 5 XLK row; XLK $199.81 at booking per macro/facts.json) | Named catalyst: Wed Oct 7 $39B 10Y auction 1:00 PM + FOMC minutes 2:00 PM (wiki/synthesis.md Section 8); no dated next print on the Yahoo calendar (unverified); 6-week backstop Nov 16 | Trim 1/3 at +15% ($570.69); remainder trails -15% from HWM |
| JCI @ $155.72 (Marky) | **CORE** -- large-cap building technology, broad sponsorship; not in any wiki | -5% = $147.93 | XLI close below $166.18 (Thursday's reversal low, wiki/industrials.md; XLI $169.95 at booking) | Named catalyst: JCI FQ4 print Oct 27 (Yahoo calendar, unverified); 6-week backstop Nov 16 | Trim 1/3 at +15% ($179.08); remainder trails -15% from HWM |
| NDSN @ $333.54 (Marky) | **CORE** -- low-volatility uptrend (vol 2.8%), liquid mid/large-cap; not in any wiki; shares JCI's XLI line | -5% = $316.86 | XLI close below $166.18 (shared with JCI; wiki/industrials.md; XLI $169.95 at booking) | No dated next print (last reported Aug 19, unverified); 6-week backstop Nov 16 | Trim 1/3 at +15% ($383.57); remainder trails -15% from HWM |
| AMAT @ $540.82 (Ophelia) | **CORE** -- large-cap semis equipment, broad sponsorship; +11.3% last week on the MU read-through | -5% = $513.78 | SMH close below $609.66 (double-top line, wiki/semiconductors.md; wiki/synthesis.md Section 5 SMH row; SMH $630.60 at booking) | Named catalyst: Oct 7 auction/minutes gate on a 43x semis sector; AMAT print Nov 12 (wiki/earnings-surveillance.md); 6-week backstop Nov 16 | Trim 1/3 at +15% ($621.94); remainder trails -15% from HWM |
| LRCX @ $346.88 (Ophelia) | **CORE** -- large-cap semis equipment; +10.2% last week; shares AMAT's SMH line | -5% = $329.53 | SMH close below $609.66 (shared with AMAT; wiki/semiconductors.md; SMH $630.60 at booking) | Named catalyst: LRCX print Oct 21 inside the holding window; 6-week backstop Nov 16 | Trim 1/3 at +15% ($398.91); remainder trails -15% from HWM |

outcome: to be computed

---

### Week of 2026-09-28

Book: AAPL 30.0% / META 29.4% / AMD 20.6% / cash 20.0%. **Entry prices = validated Monday 2026-09-28 opens** (tracker.py --open run ~11:35 ET by the post-open booking task; each price equals the 09:30 ET 5-minute bar open and sits inside the day's range so far; entry_price_source: open for all three; SPY $768.35 open). Opens sat just under Friday's closes (AAPL -0.21%, META -0.16%, AMD -0.91%) -- no gap to discount this week. First book since the log opened that is 100% CORE mega-cap tech/comm.

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| AAPL @ $340.37 (Marky) | **CORE** -- mega-cap, the deepest liquidity in the market | -5% = $323.35 | XLK close under $190.00 (bottom of the $190-$191.75 retest zone, wiki/tech.md; XLK $196.27 at booking per macro/facts.json) | Named catalyst: AAPL FQ4 print Oct 29 (wiki/earnings-surveillance.md); 6-week backstop Nov 9 | Trim 1/3 at +15% ($391.43); remainder trails -15% from HWM |
| META @ $750.42 (Ophelia) | **CORE** -- mega-cap comm services, broad sponsorship | -5% = $712.90 | XLC close under $111.00 (the 50D, wiki/communication-services.md; wiki/synthesis.md Section 5 XLC row; XLC $112.96 at booking) | Named catalyst: META Q3 print Oct 28; 6-week backstop Nov 9 | Trim 1/3 at +15% ($862.99); remainder trails -15% from HWM |
| AMD @ $624.90 (Ophelia) | **CORE** -- mega-cap semis, broad sponsorship; carries last week's +8.00% run into the MU gate | -5% = $593.65 | SMH close under $578.51 (failed-breakout line, wiki/semiconductors.md; wiki/synthesis.md Section 5 SMH row; SMH $606.56 at booking) | Named catalysts: core PCE Wed Sep 30 8:30 AM + MU FQ4 Wed Sep 30 AMC (the week's single gate, wiki/synthesis.md Section 4); AMD Q3 print Nov 3; 6-week backstop Nov 9 | Trim 1/3 at +15% ($718.63); remainder trails -15% from HWM |

Note: ALL and HIG (Cecil) were TRIGGER-BLOCKED at booking (XLF $54.84 < 50D $57.08; HIG's curve line ruled mis-specified and replaced with the shared XLF-50D line) and VICI was blocked as a promotion (XLRE trapdoor); TMO was declined as a chase. No exit template attaches; their counterfactuals live in shadow-book.md / rejections.md.

**Template stress note (observed at booking, ~11:36 ET, NOT a score):** day one already tests two of the three templates. META traded to $717.65 (-4.37% from entry, $4.75 above its $712.90 stop) and AMD to $596.07 (-4.61%, $2.42 above its $593.65 stop) inside the first two hours -- both already deeper than any CORE drawdown in the 4-cycle summary block except HIG's week of 09-21. XLC printed $111.14 intraday against META's $111.00 close line (0.13% headroom) and SMH $591.92 vs AMD's $578.51 line (2.3%). AAPL is flat (low -0.31%). Correlation warning for the calibration record: all three thesis lines are tech-leadership lines and moved together on day one; a single leadership break can fire all three legs in the same session. Scoring at the 2026-10-05 Monday close will tell whether -5% CORE survives a same-day -4.4/-4.6% open-to-low.

outcome (scored 2026-10-05 against date-pinned daily OHLC 2026-09-28 -> 2026-10-02): **0/3 stops fired -- the -5% CORE stop survived its hardest week by 29 cents.**
- **META: stop untouched, by $0.29** -- Monday low $713.19 (-4.96% from entry) vs the $712.90 stop; Tuesday low $715.10 (-4.71%). The deepest CORE drawdown that did NOT fire in the log (previous: HIG -3.81%, ETN -3.66%). **THESIS-INVALIDATION LEG FIRED Wed 9/30** -- XLC closed $110.97 < $111.00, then $109.94 Thu and $110.32 Fri. Would-have exit at Wednesday's close $725.18 = -3.36% vs actual -2.98% (Friday close $728.08, booked-entry basis; Tracker -2.93% on the adjusted entry): **the thesis exit would have COST 0.38pp** -- the line fired by three cents and META drifted up after it.
- **AMD: stop untouched** -- Monday low $596.07 (-4.61%), $2.42 above the $593.65 stop; lows of -3.1% to -4.0% Tue-Thu, then Friday's gap to $635.95 on the MU read-through (AMAT +11.3% / LRCX +10.2% on the week). Finished +1.44%. A -4.5% CORE stop would have turned +1.44% into -4.5% (a ~5.9pp self-inflicted loss on a 20.6% sleeve = 1.2pp of book). Thesis leg intact: SMH low close $600.01 vs $578.51. Best high +3.29% -- no trim.
- **AAPL: stop untouched** -- deepest Thursday low $325.81 (-4.28%), $2.46 above the $323.35 stop; finished -1.96%. Thesis leg intact: XLK low close $194.50 vs $190.00 (week low $192.68). Never above +0.77% -- no trim.
- Trims: 0/3. Time stops: none due. Actual book -1.15% (Tracker). With META's thesis exit the weighted return would have been about -1.26% (-0.11pp).
- **Calibration read (the question the stress note asked):** all three CORE names traded between -4.3% and -5.0% from entry inside the week and none fired; two finished better than their lows by 2-6 points. The summary block's finding holds under its first real test -- every tightening of -5% makes this week worse (a -4.5% stop fires on META and AMD; a -4.0% stop fires on all three). Scored cycles now 7 (20 CORE / 1 SPEC position-weeks; 2 stops fired, both helped, 0 hurt). The day-one correlation warning was correct in kind: all three bottomed within four sessions on the same tape.

---

### Week of 2026-09-21

Book: XOM 19.7% / AMD 16.8% / HIG 15.7% / cash 47.8%. **Entry prices = validated Monday 2026-09-21 opens** (each bar checked low <= open <= high before the tracker was run at ~10:36 ET; SPY $766.25). First week since the log opened that the Council and the Arena share the same entry basis. Note AMD gapped **+4.3%** at the open ($583.94 vs Friday's $559.82 close), so its levels below sit well above the Friday chart.

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| XOM @ $160.96 (Marky) | **CORE** -- mega-cap integrated major, deepest liquidity in the sector | -5% = $152.91 | XLE weekly close below $63.46 (breakout line, wiki/energy.md; wiki/synthesis.md Section 5) | Named catalysts: OPEC+ meets Oct 4; XOM Q3 print Oct 30 (wiki/earnings-surveillance.md); 6-week backstop Nov 2 | Trim 1/3 at +15% ($185.10); remainder trails -15% from HWM |
| AMD @ $583.94 (Ophelia) | **CORE** -- mega-cap semis, broad sponsorship; flagged hot (RSI 65.4 at Friday close, then a +4.3% gap) | -5% = $554.74 | SMH close below $560.28 (wiki/semiconductors.md Near Support; wiki/synthesis.md Section 5 SMH row) | Named catalyst: MU FQ4 Wed Sep 30 AMC is the leadership trade's verdict; 6-week backstop Nov 2 | Trim 1/3 at +15% ($671.53); remainder trails -15% from HWM |
| HIG @ $131.69 (Cecil) | **CORE** -- large-cap P&C insurer | -5% = $125.11 | 10Y-3M curve inverts (macro/facts.json rates.curve_10y_3m_bps = +102 at booking) | Named gates: $192B 2/5/7-year auctions Sep 22-24; P&C Q3 prints late October; 6-week backstop Nov 2 | Trim 1/3 at +15% ($151.44); remainder trails -15% from HWM |

Note: ALL (Cecil) and DE (Marky) were TRIGGER-BLOCKED at booking -- their 2026-09-14 invalidations fired on 9/18 -- and VICI was blocked as a promotion; no exit template attaches. Their counterfactual lives in shadow-book.md.

**Template stress note:** AMD's stop ($554.74) sits ABOVE SMH's $560.28 invalidation in price terms for AMD itself -- the gap means the stop leg may fire before the thesis leg for the first time in this log. HIG's -3.81% intraweek low last week (closest CORE call on record) is the reference for whether -5% is still dead-zone.

outcome (scored 2026-09-28 against date-pinned daily OHLC 2026-09-21 -> 2026-09-25): **1/3 stops fired -- THE FIRST CORE STOP IN THE LOG.**
- **HIG: CORE -5% STOP FIRED Fri 9/25** -- Thu low $125.52 held $125.11 by 41 cents, Fri opened $125.46 and traded to $124.09 (-5.77% from entry). Would-have exit $125.11 = -5.00% vs actual -5.66% (Friday close $124.23): **the stop SAVED 0.66pp**. HIG made a lower low every day of the week (-0.74 / -2.35 / -3.96 / -4.69 / -5.77%); last week's -3.81% 'closest CORE call' was the warning shot. Thesis leg (10Y-3M inversion) did NOT fire -- curve +111bp at Friday close (macro/facts.json) -- so the stop caught a loss the thesis line could not see, the scar Cecil was flagged for.
- **XOM: stop untouched** (deepest -3.17% Tue low $155.85). **THESIS-INVALIDATION LEG FIRED** -- XLE closed $62.04 < $63.46 (failed breakout #2, wiki/energy.md 2026-09-25). XOM finished -0.23% (Monday-open basis); the line fired on a near-flat week.
- **AMD: stop untouched** -- the stress note's fear did not materialise; the Monday low $582.27 (-0.29%) was the week's deepest print, and AMD closed every later session above entry. Best intraweek high +9.43% ($639.00, Fri) -- **no trim** (+15% = $671.53). SMH low close $596.03, nowhere near $560.28.
- Trims: 0/3. Time stops: none due. Actual book +0.41% (Tracker); with HIG's shadow stop the weighted return would have been +0.51% (+0.10pp).

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