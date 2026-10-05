# Weekly Council Synthesis — Week Ending Friday, October 2, 2026

> ⚠️ **DATA FRESHNESS — SECOND PASS (Sunday Oct 4, evening). ALL 15 WIKIS AND facts.json ARE FRESH. THE CREDIT GAUGE IS NO LONGER BLIND, AND IT MOVED: HIGH-YIELD SPREADS ARE THROUGH 300 BPS.**
>
> - `macro/facts.json` generated **2026-10-04**, **0 days old and FRESH** (commit 554a0f2), all values as of the Fri 2026-10-02 close. A re-pull on Sunday evening matched every yahoo-sourced field inside its tolerance.
> - **All 15 wikis are FRESH** (fourteen stamped 2026-10-03, Canary Watch 2026-10-04). **The Monday Watchlist carries no staleness caveat.**
> - **Schedule failure, caught by this check.** The evening crew ran about seven hours late (no commit between 19:15 Saturday and 02:53 Sunday). This job missed its 20:26 ET slot and ran at 03:17 ET Sunday, after every upstream page had landed.
> - **What the second pass filled in (verified first-hand Sunday evening):**
>   - **Credit.** FRED answered through a second network path. **HY OAS closed above 300 bps on Mon Sep 28 for the first time since April 7 and reached 324 bps on Thu Oct 1**, after eight straight daily widenings from 266 on Sep 21. IG OAS is 86 bps, HY–IG **238 bps** (Canary's trigger is 250), CCC spreads **1,215 bps**, a 52-week high. The 10Y breakeven is 2.36% (2.34% a week earlier). Friday's OAS prints post Monday. None of this is in facts.json; it is cited to FRED.
>   - **OPEC+ (Sun Oct 4): November targets held at September's level**, as expected. The seven core members review again Nov 1.
>   - **Treasury auctions confirmed** (TreasuryDirect, announced Oct 1): **$58B 3-year Tue Oct 6, $39B 10-year reopening Wed Oct 7, $22B 30-year reopening Thu Oct 8**, each at 1:00 PM ET.
>   - **The disagreements listed in the first pass are resolved in Section 7**: copper (two contract months), the 2-year, the size of the curve steepening, the dollar's streak (three weeks, not nine) and AZZ's report date (Oct 13). Six streak counts carried on sector pages were wrong and are corrected there and here.
> - **Corrections to this page's own first pass:** it repeated "first up week in seven" for utilities (it was the first in four), "sixth" and "seventh" red weeks for staples and discretionary (seventh and eighth), four weeks under the 200-day for real estate (three) and seven for utilities (ten). It said a 52-week high of 102.10 on the dollar could not sit below a 102.21 high; both are right (closing and intraday, both Thursday). It called the data feed's 2-year "wrong"; the feed reports the 2-year yield *future* by design (Section 7).
> - `data/market_state.json` (`as_of` 2026-10-02) feeds the README Index Check. It was **re-derived on Sunday evening** with the pipeline's own pure derivation so its policy gate matches the current facts.json; nothing else in it changed.

---

## 1. CECIL'S SYNTHESIS — Fundamentalist Lens

**The carry gaps widened to new extremes, and for the first time single-name yields crossed back above the Treasury.** With the 10Y at **5.277%**, utilities' 2.83% sits **245 bps** under the risk-free rate, staples' ~2.59% sits **269 bps** under, and real estate's ~3.19% sits **209 bps** under. Below the fund level the arithmetic is turning: **O at 6.0%** is about 70 bps over the ten-year and **CCI at 6.4%** about 110 over, **VZ's 6.2%** clears it by ~90, **GIS yields 7.6%**, **UVV 7.9%**, **UPS 7.05%**. T's 4.6% is ~70 bps *under*. Cecil's verdict on the high numbers is not uniform: O and CCI are "the beginning of a price, not yet a floor"; GIS is "a liquidation in installments" (sales falling in all three U.S. units); UPS is still a payout question; EIX at 8.3x and 6.5% is "a courtroom."

**What the week made cheap.** The regulated utilities are, in his words, finally prices: **EXC 13.4x forward, ES 13.1x, SRE 14.1x, DTE 14.9x**, with the Street 17–28% above the tape. Banks: money centers at 10–13x forward with 20–26% gaps, **SCHW 12.4x** with a 28% gap. Healthcare "gave me a list": **REGN 12.0x** on its 200-day, **ABT 16.1x** at RSI 29.7, **UNH 16.4x** with a +29.5% gap, **PFE 6.2%**. Housing: **LOW 13.9x, HD 17.7x**, both at 52-week lows with ~3% yields. **PEP 14.1x** with a 4.7% yield at RSI 26, **BKNG 12.9x**, **EOG 9.3x**, **CSCO 20x** ("the one name that got cheaper to own as it went up"). He bought almost none of it. The condition in every case is a dated receipt: PEP's guide Thursday, the bank reserve lines Oct 13–15, the GLOBE number on the pharma calls, a week in which the 10-year closes lower.

**The scorecard on last week's purchases is honest and mixed.** Working: **MPC** ($393.52 → $422.33, +7.3%), **CAT** ($821 → $845.42), **AEO** ($16.59 → $17.71). Under water: **BAC** (added at the fund's 200-day, now half size near $55 vs $53.75), **GE** ($327 → $309.56, "I bought the defense bid the week it left"), **NFLX** ($71.15 → $67.06, a new low), **AMGN** ($414.80 → $403.04), **PPG** (~$107.50 → $105.15), **KDP** (gave back the whole prior week). Three of nine. None is being added to before its print.

**His credit line was crossed while he could not see it.** On the Canary page Cecil said he had no spread data and would not pretend to: the last print he could stand behind was HY OAS at 280 bps on Sep 24, and 300 "would be the first real credit signal of this cycle." The refresh shows **300 was crossed on Sep 28 and the spread was 324 bps on Oct 1**, the widest since March 31. One caveat keeps it in proportion: HY OAS was also above 300 in February to April (peak 346 on Mar 30) and in October and November of last year, so this is the first crossing of the current hiking cycle, not of the year. What is new is where the pressure sits. **CCC spreads are 1,215 bps, a 52-week high and well above March's 1,020**, and they have ended every month wider since May. That is the refinancing wall, not a market-wide panic, and it is the number to hold against "10x forward with a 26% gap is cheap if reserves are flat."

**Above-target names are the trap shelf now.** **MPC, VLO and PSX** trade 9.5%, 10.5% and 2.9% above their mean targets at near-record prices into a G-7 release aimed at their margin. **AMD, INTC and AAPL** are still above target; **LRCX** has 7.9% left after a 10% week at 59x trailing; **VYLR** trades 33% above a four-analyst target; **AMGN and TMO** sit at or above theirs. **CHTR at 2.3x forward** "is a verdict, not a valuation."

**Leadership got more expensive against the bond.** SMH at ~43.1x trailing earns about 2.3%, roughly **295 bps under** the ten-year; XLK at ~35.4x earns about 2.8%. And Micron is the cleanest test of "priced in" the Council has had: revenue $54.23B, an 87% gross margin, a guide of $61.5B, and the stock closed the week **-0.7%**. Earnings Surveillance logged fourteen beats last week and eight closed lower on the reaction day (JBL +8% beat, -10%; CAG +45%, -4.9%; AIR +15.5%, -7.2%). **The forward number is the print.**

**Fund composition was wrong on six pages and is now corrected** — a fundamental fact, not housekeeping: refiners are **15.8%** of XLE (carried ~8%); AMZN + TSLA are **41.7%** of XLY; Welltower, not Prologis, is XLRE's largest holding at 11.4% and towers are the tail; Newmont is **7.8%** of XLB; WBD is 4.7% of XLC and leaves when its merger closes, expected Oct 6; Target is XLP's #6. Two top-ten holdings the pages had never priced are filled in: **KMI $31.07 (+1.0%)** and **ETR $100.91 (+2.4%)**.

---

## 2. MARKY'S SYNTHESIS — Technician Lens

**Two sectors made new highs, and eight closed lower. The tape is a record index on a quarter of its members.** SPY slipped 0.22% to **$769.64**, still above its 50-day ($763.70) and about 1% under its Aug 13 record close ($777.88). **The Nasdaq 100 made a record close on Friday** (QQQ $749.58); the Nasdaq Composite made an intraday record but closed under its Sep 22 high. **XLK** made a record close at $199.81, its sixth straight weekly gain, through the June peak ($198.73), but sold its own payrolls gap (open $201.16, close under $200). **SMH** closed $630.60, the highest since June 30 and a fifth straight weekly gain, through the $609.66 double top on 57% more volume, leaving an open gap at $620.91–$628.55. Canary's breadth: **24.7%** of S&P 500 members above their 50-day (20.9% Wednesday, the low of the 30 sessions tabulated), **42.3%** above their 200-day, new lows beating new highs every day (40 to 3 on Thursday), the equal-weight index lower for seven straight weeks.

**The sector map by moving average.** Above the 50-day: **three of twelve** — XLK, SMH, XLE — down from five (XLV and XLC both lost theirs). Above the 200-day: **five** on the sector pages' numbers — XLK, SMH, XLV, XLE, and XLF by seventeen cents. **That fifth one depends on the chart.** The pages compute averages on dividend-adjusted closes, which puts XLF's 200-day at $53.32. On raw price closes, the way most brokerage charts draw it, the 200-day is **$53.71** and XLF has closed under it three days running. No other sector changes sides. Weekly closes under the 200-day: XLI three, XLB three, XLP three, XLRE three, XLY five, XLU ten, XLC eighteen.

**Losing streaks, recounted from the closes.** XLY has fallen **eight** straight weeks, XLP **seven**, XLRE **seven**, XLF **four**. XLU's gain was its first up week in **four** (it also rose the week of Sep 4). HYG has fallen five straight weeks and the 10-year yield has risen five. Several sector pages carried counts one or more weeks off; they are corrected (Section 7).

**Stops were hit and Marky took them.** Out of XLC (Wednesday closed $110.97, under the $111 stop on double volume), out of the XLP range long (close under $81.00), out of buy-the-dip in XLV (50-day lost at $168.02), and by the letter out of the XLI bear-trap (kill line $167.49 hit on a close). He owns a small XLF piece from Thursday's reclaim with a stop under **$52.81**. He stopped selling XLRE rallies with forty cents of target left.

**Every sector is now two numbers:**

| Sector | Below | Above | Read |
|---|---|---|---|
| XLK | $198.73 / $194.50 | $200.00 | Breakout with an asterisk; add on a gap fill that holds $198.73 |
| SMH | $609.66 | $640–650 | Confirmed breakout, extended (RSI 68.6); buy near $621, not $631 |
| XLF | $52.81 | $54.46 | RSI 27.5, 17 of 17 names under the 50-day; Oct 13 sizes it |
| XLV | $164.50–165.00 | $168.02 | Second test of the September floor; next is $155.50 |
| XLI | $166.18 | $171.48 | RSI divergence at the 200-day; one more look |
| XLB | $47.81 | $49.57 | Map target $47.00 missed by 81 cents |
| XLE | $60.95 | $63.46 | Range, both edges tested; refiners repaired in five sessions |
| XLU | $39.03 | $40.21 | New low reversed same day on doubled volume |
| XLP | $80.13 | $81.00 | No named support below until the low $70s |
| XLRE | $40.40 | $41.33 | RSI 25.7, third week under 30 |
| XLY | $107.99 | $111.10 | Four closes under $109.41, reclaimed Friday on Tesla |
| XLC | $109.66 | $111.19 | Flat; five names at lows report inside ten days |

**Correlations breaking — and one that formed.** (1) **Utilities vs the 10-year**: the 10Y rose 9 bps to a 24-year intraday high (5.342%) and XLU *rose* 0.8% on 52.6M shares a day against 24.7M. (2) **Data centers vs bonds**: EQIX +1.8% and DLR flat while towers made lows — "leaders turn before laggards." (3) **The stock vs the metal**: copper lost $6.60 and FCX closed above $71.54; Shanghai reopens Oct 8. (4) **Crude vs energy equities**: WTI down, XLE up, refiners +3.5% to +7.3%. (5) **Regionals vs money centers**: KRE beat XLF a third week, which is not how a loan-book scare usually trades. (6) What formed: **all twelve sector correlations to SPY rose** (XLY to 0.888, XLRE to 0.737); only XLE is negative (-0.242). One factor is driving the tape, and it is the long bond.

**Vol and credit.** VIX closed **15.31** after four closes above 16.00 and a 17.59 high; contango held (VIX/VIX3M 0.85). Equity put/call printed 0.38 on Tuesday. Bank straddles into Oct 13–15 price 1.6–2.5x their realized norms. The equity vol market stayed calm through a week in which **HY spreads widened eight sessions in a row**. His lines: VIX 16.50 on a Friday close, 10Y 5.342%, XLK -5% vs SPY.

---

## 3. OPHELIA'S SYNTHESIS — Macro Lens

**The Fed stepped back and the bond market did not. That sentence is the week, and it appears in some form on eleven of fifteen pages.** Core PCE printed +0.2% (3.0% YoY against 3.3% expected). Payrolls printed **+29K** against roughly 85–90K, with 60K of downward revisions, unemployment 4.2% and wages +0.1%. Jefferson and Williams said there is "no need for urgency." October-hike odds fell from roughly two-thirds to about one in five (the pages carry ~16–18%; CME FedWatch readings after the print ran from about 17% to 23% depending on the source). And the 10-year closed **5.277%, +9.3 bps**, after a cycle-high close of 5.293% on the day PCE cooled and a 5.342% intraday high Thursday; the 30-year closed 5.63%. The 3-month bill fell to **3.993%**. The 2-year closed at 4.92% on Monday and ended the week at **4.83%**, two basis points above the prior Friday. The curve steepened: **10Y–2Y +45 bps** (36 a week earlier, 26 on Sep 23), **10Y–3M +128 bps**. Ophelia's wording changed accordingly — from "no landing with a hawkish Fed" to **"hiking cycle on pause, bear steepening."** Term premium moved "from the footnote to the headline."

**The refresh confirms her read of the bond move.** She could not see breakevens on Saturday and guessed the move was real yields. It was: the 10-year breakeven is **2.36%**, against 2.34% a week earlier, so about seven of the nine basis points were real yield. Inflation expectations did not move. The price of lending did.

**Three regime flags are up, from two:** NFP < 150K **fired** (and the "< 50K = regime-change candidate" line with it), the 10Y is through 5.25% on a weekly close, and CPI > 0.3% is carried into Oct 14. Issue #127 is open.

**The rotation story is that there was no defensive rotation.** The textbook response to a labor crack and a 12-year low in confidence (Conference Board 81.9) is money into staples and healthcare. Instead XLP fell 1.86% on above-average volume with no company reporting, and XLV fell 2.65%. Her stance changes run almost entirely one way:

- **Downgrades:** staples defensive-lean → **neutral** ("a defensive that does not defend is a bond proxy with equity risk"); financials neutral → **cautious**; big pharma → neutral and Part B biologics → neutral-negative; platforms overweight → market-weight and telecom yield → underweight; defense overweight → market-weight; consumer discretionary stays **bearish** with last week's concession withdrawn.
- **Upgrades:** machinery and power → **overweight** (ISM 54.5 cleared her 52 gate; CAT, GEV); utilities defensive → **neutral**, "and it is the tape and not my framework that earned it"; managed care → neutral into UNH.
- **Unchanged:** energy hold-add-nothing; semis held as a momentum position, not added; commodity-long restriction **ON** (#115).

**What she asked for and did not have: credit.** On the financials page she wrote that HY spreads were "the one confirmation still missing" and told the Council to check before acting on anything she said. Checked: **HY OAS 324 bps on Oct 1, above 300 since Sep 28; IG 86, the widest since April 7; HY–IG 238 against Canary's 250 trigger.** That moves the financials question. Regionals outperforming money centers still argues for rate shock over loan losses. Eight straight days of wider junk spreads, and CCC paper at a 52-week high, argue that the weakest borrowers are being repriced at the same time.

**Cross-currents she names and cannot resolve.** Output is strong (Dallas production 29.5, Chicago PMI 58.8, ISM new orders 55.3, Q2 GDP revised to 2.2%, claims 197K) while hiring has stopped (JOLTS 7.08M, ADP beat and BLS missed in the same week). **ISM prices paid jumped to 77.9** while core PCE cooled. The dollar rose a third straight week to **101.93**, and closed above 102 on Thursday (102.10), in a week the front end fell — "the bid is not about October." Gold fell to **$4,162.30** (-3.68%). Her summary of the mix: "stagflation-adjacent."

**Two frames she retired in her own words.** In real estate: "I told you there was no third path that did not run through PCE and the Fed. There was one." The relief condition is restated as **a week in which the 10-year closes lower**, not a data print. In healthcare: "I had the wrong variable" — the sector traded two federal pricing actions in 48 hours (Section 232 pharma tariffs Sep 29, CMS's GLOBE Part B reference-pricing rule Sep 30), not rates.

**What the Economic Calendar revealed:** the next week has no CPI, payrolls or PCE and is still the most dangerous rates week of the month, because the supply arrives. Treasury has confirmed it: **$58B of 3-years Tuesday, $39B of 10-years Wednesday at 1:00 PM with FOMC minutes an hour later, $22B of 30-years Thursday.** OPEC+ took one variable off the table by holding November targets on Sunday. Cash stays at 25–30% on her desk; nothing rate-sensitive is added before Wednesday's auction without a stop.

---

## 4. CONSENSUS SYNTHESIS

**Where all three agree.**

1. **The long end, not the Fed, sets prices now.** Cecil measures it in carry gaps (-245, -269, -209 bps), Marky in twelve rising correlations, Ophelia in a bear steepener that the breakeven data shows was almost all real yield. All three name Wednesday's 10-year auction as the event of the week.
2. **Leadership is two sectors deep and both are extended.** SMH is +13.97 points and XLK +8.24 points ahead of SPY in a month. Nobody is adding at these prices: Cecil will not chase equipment up 10%, Marky wants the gap fills ($621 in SMH, $198.73 held in XLK), Ophelia holds semis "as a momentum position."
3. **Good results no longer move stocks; forward numbers do.** Micron, Jabil, Conagra, McCormick, AAR and Nike all beat and fell. Accenture and Carnival raised the forward number and rose 13–16%.
4. **Do nothing before the dated receipt.** PEP (Oct 8) for staples, JPM/WFC/C/GS/UNH/JNJ (Oct 13) for banks and healthcare, Shanghai (Oct 8) for copper, CPI (Oct 14) for the flag that can clear.
5. **Own machinery and power inside industrials (CAT, GEV, ETN); stand aside in aerospace and defense until Oct 20.**
6. **XLY is not the consumer.** Six names set 52-week closing lows inside an ETF that lost 0.47%, because two stocks are 41.7% of it.

**Where they disagree.**

- **Utilities.** Marky buys a close over $40.21 and Cecil "starts" there; the utilities-page Ophelia went to neutral. The Canary-page Ophelia says one week is not a turn and adds nothing rate-sensitive. Same analyst, two pages. The corrected count weakens the bull case a little: this was the first up week in four, not in seven, and the fund has spent ten weeks under its 200-day.
- **Micron vs its suppliers.** Cecil on the tech page added to MU post-print at 5.2x forward; Cecil on the semis page would "rather own what Micron buys than Micron"; Marky wants equipment (AMAT, LRCX); tech-page Cecil will not chase equipment. Section 7.
- **What +29K means.** Rate relief on the tech and semis pages; "the first hard datapoint that argues for the credit scare" on financials; "a demand story" on discretionary. This is the week's formal contradiction (#129).
- **Financials.** Marky is long small against $52.81; Ophelia wants no new money above the 200-day until the prints; Cecil holds half-size BAC and trusts the regionals-over-money-centers pattern ("rates and marks, not loans"). The credit refresh is new evidence for Ophelia's side of that argument.
- **Oversold bond proxies.** Marky stopped selling XLRE and sees the snap-back asymmetry; Ophelia upgrades nothing; Cecil waits for the 10-year.

**The single biggest risk: a failed long-bond auction with the Fed on hold, into a tape with no diversifier and credit starting to confirm.** The 10-year rose on a week of cool inflation and stalled hiring. If Wednesday's $39B auction tails more than 2 bps or the 10Y closes above **5.342%**, the next line is 5.50%, and it lands on a 43x semis sector 10.7% above its 50-day, an index with 24.7% of members above theirs, and twelve sector correlations that all just rose. Energy is the only negative correlation on the board. On Saturday this paragraph said credit was the gauge that would confirm the risk and that it was unmeasured. It is measured now: **HY OAS widened eight sessions in a row to 324 bps, HY–IG is 12 bps from Canary's 250 trigger, and CCC spreads are at a 52-week high.** That is not a credit event. It is the first sign that the bond selloff is reaching borrowers.

**The single biggest opportunity: the Oct 13 bank prints from RSI 27.5 on the 200-day — with a harder test than it looked on Saturday.** XLF sits on its 200-day (seventeen cents above on the pages' math, twenty-two below on a price chart) with all seventeen tracked names under their 50-day, money centers at 10–13x forward with 20–28% gaps to target. If reserve lines are flat, four weeks of selling was positioning and the snap-back is large. The spread data raises the bar: flat reserves now have to be reported against junk spreads at a six-month high. The runner-up is the same shape in healthcare: JNJ at RSI 32.6 and UNH with the widest gap on the board report the same morning — though UNH's whisper ($4.60 vs $4.12) sets a bar an in-line print will miss.

---

## 5. MONDAY WATCHLIST

*All 15 wikis fresh; levels are Friday Oct 2 closes. Macro levels are facts.json; credit is FRED through Thu Oct 1. No staleness caveat. OPEC+ held on Sunday, so no supply surprise lands at the open.*

**Macro gates (these outrank every ticker line below):**

| Gate | Level now | Trigger | Action |
|---|---|---|---|
| **10Y yield** | **5.277%** | Close above **5.342%** or a tail > 2 bps at the **$39B 10-year auction (Wed 1:00 PM)** | Term-premium break extends; next line 5.50%. Cut rate-sensitive adds, keep hedges. A stop-through and a close below **5.20%** = relief; bond proxies get their first green light |
| **HY credit** | HY OAS **324 bps**, HY–IG **238 bps** (Thu Oct 1); HYG **$76.91** | **HY–IG > 250 bps** (Friday's print posts Monday); HYG below $76.39 | Canary's credit row goes yellow for the first time since March. No high-yield adds; read the bank reserve lines on Oct 13 against it |
| **DXY** | **101.93** | A second close above **102** (Thursday closed 102.10, the 52-week closing high) | Canary trigger; commodity-long restriction stays ON (#115); re-opens below 99 |
| **VIX** | **15.31** | Friday close above **16.50**; then 20 | First is the tell, second is the regime question. Hedges are cheap now |
| **WTI** | **$91.11** | Below **$88.06** or above **$96.54** (last week's range) | OPEC+ held, so the producer side is unchanged; $100 is the flag |
| **ISM Services** (Mon 10:00) | prior 55.4 | **> 57** with prices rising / **< 53** | Reflation and a 5.342% retest / growth scare confirming +29K |
| **Jobless claims** (Thu) | 197K | **< 200K** a 4th week / **> 225K** | "Consensus stale" streak flag / layoffs confirm payrolls |

**Tickers, levels, triggers, stops:**

| Ticker | Close | Trigger | Stop / invalidation |
|---|---|---|---|
| **SMH** | $630.60 | Add on a gap fill toward **$621** that holds; target $640–650 | Close below **$609.66** → $591.92 |
| **XLK** | $199.81 | Add on a gap fill ($198.54–$199.35) holding **$198.73**; not on a first print over $200 | Close under $198.73 = failed breakout → $194.50, then $192.6 |
| **XLF** | $53.49 | Add only on a close over **$54.46**; Oct 13 prints size it | Close below **$52.81** → $50.42–$51.58 |
| **XLV** | $166.18 | Long against the September floor for a reclaim of **$168.02** | Close below **$164.50** → 200D $155.50 |
| **XLU** | $39.83 | Buy a close above **$40.21** for $40.66–$40.81 | Close below **$39.03** voids it |
| **XLRE** | $40.81 | Trade a close above **$41.33** toward $42.50 | Close below **$40.40** → $40.00, then $39.12 |
| **XLP** | $80.53 | Buy a reclaim of **$81.00** only; PEP Thursday decides | Close below **$80.13** → no support to the low $70s |
| **XLI** | $169.95 | Close above **$171.48** = failed breakdown → $176.46 | Close below **$166.18** → low $160s |
| **XLB** | $48.86 | Flat between; long only on a reclaim of **$49.57** | Close below **$47.81** → $47.00 and likely overshoot |
| **XLE** | $62.82 | Weekly close over **$63.46** un-fails the breakout → $65.93 | Close under **$60.95** → 200D $55.88 |
| **XLY** | $110.04 | Long above **$111.10** for $113.29 | Short on a close below **$107.99** → $105.45 |
| **XLC** | $110.32 | Long on a close over **$111.19** that is not just Alphabet | Close under **$109.66** → $105.38 |
| **PEP** | $125.89 | Thu Oct 8 before the open, cons $2.30, whisper $2.32; buy post-print **if the guide holds** | 52W closing low $125.60; a guide cut = no trade |
| **STZ** | $112.87 | Tue Oct 6 after the close; the only whisper *below* consensus ($3.55 vs $3.62) | Low $112.77 |
| **FCX** | $72.04 | Long only if copper reclaims **$6.60** after Shanghai reopens Oct 8 (December copper **$6.549**) | Loses **$71.54** = the metal was right |
| **CAT / GEV** | $845.42 / $988.70 | Hold; the machinery-and-power longs | CAT 50D $823.45 |
| **MPC / VLO** | $422.33 / $406.30 | Hold, do not add (above targets into the G-7 diesel release) | Weekly distillate data; VLO prints Oct 22 |
| **JNJ / UNH** | $256.03 / $371.90 | Tue Oct 13 before the open; JNJ RSI 32.6; UNH whisper $4.60 vs $4.12 | JNJ consensus basis unresolved ($2.48 vs $2.90) |
| **BAC** | $53.75 | No adds before Oct 14 | RSI 22.3, below its 200D ($54.81) |
| **AZZ** | $139.39 | **Tue Oct 13 after the close** (company-confirmed; call Oct 14), cons $1.84. First machinery-adjacent print after ISM | 200D $135.57 |
| **EQIX** | $1,025.72 | The tell for real estate: does it hold its gain on the next push in yields | — |
| **DAL** | $84.09 | Fri Oct 9 before the open; Yahoo consensus cut $2.02 → $1.88 in a week (other tallies run higher) | — |

**Also on the tape Monday and Tuesday:** WBD is expected to leave XLC on **Tue Oct 6** when its merger with Paramount Skydance closes (4.7% of the fund gets replaced).

---

## 6. CROSS-SECTOR CONNECTIONS — The Hidden Wires

**Wire 1 — The term-premium chain: one bond, eight sectors.** The 10-year at 5.277% with the Fed on hold runs straight through the pages. Mortgage rates jumped to **7.28%** (largest weekly rise in four years) → **HD and LOW** to 52-week closing lows (discretionary) → **SHW, PPG, VMC, MLM, CRH** at or near lows (materials: "no new positions in construction materials while the 30-year makes highs") → **XLRE** to $40.40. The same bond sets the carry gap that sold **XLP** and the telecom sleeve (**T -4.3%** in a week the hike was priced out), marks the securities books at **BAC, GS, MS, C** (financials), and is the discount rate on a **43x SMH**. Canary measured the result: all twelve correlations rose. The wire's one loose end is utilities, which held.

**Wire 2 — Micron's capex bill is everyone else's revenue.** More than $45B of FY27 capex ($25B in the first half, construction-heavy) left MU -0.7% and travelled: **AMAT +11.35%, LRCX +10.24%, KLA +10.1%, ASML +7.07%** (semis) → **CAT +2.9% and GEV +3.2%** on data-center power generation (industrials: "fab and data-center construction is industrial demand") → **EQIX +1.8%, DLR flat** while every other REIT fell (real estate: "traded with tech, not rates") → construction spending +0.9% against 0.0% expected, carried by data centers and power (calendar). The same wire carries the single point of failure the industrials page names: if the only parts of XLI that work are an AI-infrastructure trade, a paused build takes the "cyclical" index with it. And it is contested inside comm services, where a Goldman note on what AI capex must earn cost **META -4.8%** in a session.

**Wire 3 — The diesel loop: from Hormuz to the pump to policy.** A diesel crack reported above $100/bbl (energy) → refiners **MPC +7.3%, VLO +4.9%, PSX +3.5%**, now 15.8% of XLE → **ISM prices paid 77.9** (calendar, industrials, materials) → the G-7's 100M-barrel release with diesel front-loaded in the first 20 days → claimed as relief by rails and parcels (**UNP, CSX, FDX** up 1.4–1.6%), by food distribution (**SYY, CHEF**), and as a flip condition by discretionary (oil under $90 is "a dollar away"). The energy desk doubts the release closes a gap made by shipping, strikes and an export ban. **OPEC+ held November targets on Sunday**, so nothing from the producer side changes the loop. If the energy desk is right, every downstream claim of fuel relief is wrong at once — and the refiners, priced above their targets, have "a government aiming at its margin."

**Wire 4 — The consumer stress triangle: confidence, jobs, mortgages.** Conference Board 81.9 (lowest since 2014; more respondents call their finances bad than good, a first) + payrolls +29K + a 7.28% mortgage → **Nike** guides FY27 revenue down high-single digits with Greater China -26% → **V, MA, AXP** fall 1.8–2.7% (financials: "payments broke rank") → **CAG, MKC, GIS** beat and are sold on falling volume (staples, earnings) → comm services flags ad budgets as the next shoe (**no cut found yet**) → **SPG** on its 200-day, **CARG** at RSI 32. Against it: **Carnival** printed a record and raised, **TJX and MAR** rose two weeks running. People are paying for the cruise and trading down at the grocery store.

**Wire 5 — Washington reprices margins in three sectors in one week.** CMS finalized Part B reference pricing and the pharma tariffs took effect (**REGN -6.7%, JNJ -5.6%**); FERC accepted and suspended PJM's reliability backstop for five months (**CEG -2.2%**, the only utility loser); the G-7 targeted diesel (refiners). A court kept Edison International in the Eaton Fire case. In each case the size was small and the precedent was the trade. The healthcare page says it plainly: the right dashboard is "the Federal Register," not the 10-year.

**Wire 6 — The dollar wire.** DXY **101.93**, up a third straight week and seven hundredths under the Canary trigger after a Thursday close above it → gold **-3.68%**, **NEM -4.8%**, **ALB -4.7%** (materials) → translation drag named on six pages into Q3 prints: **PEP, KO, PG, MDLZ, CL** (staples), **LLY, MRK, ABBV, JNJ** (healthcare), **META, GOOGL** (comm), **CAT, DE** (industrials), **AMT** (real estate), **MSFT, AAPL** (tech). PepsiCo on Thursday is the first company to put a number on it.

**Wire 7 — The weakest-borrower wire (new, from the credit refresh).** CCC spreads at a 52-week high (1,215 bps) and HY OAS through 300 connect items that sat on separate pages as footnotes: **Mercer International** skipped a $25.8M coupon on Oct 1 (materials, #99); **Cogent** trades as a distressed $0.43B cap (comm services); **AAR** beat by 15.5% and fell 13% in three sessions on a debt-funded deal (earnings, #128); **Trepp's September CMBS delinquency rate rose to 8.02%**, with multifamily at 8.04% and above the overall rate for the first time since the Covid shutdowns (real estate; published Oct 4); **HYG** fell a fifth straight week (canary). None of these is large. Together they say the cost of a 5.28% ten-year is being paid first by whoever has to refinance, which is the question the banks answer on Oct 13.

---

## 7. SECTOR CONTRADICTIONS — Where the Wikis Disagree, and What the Second Pass Found

### A. Truth Layer — checked first-hand on Sunday evening (facts.json values stand)

| Item | facts.json / verified | What disagreed | Resolution |
|---|---|---|---|
| **Copper** | **$6.549** (facts.json) | tech, industrials, materials: ~$6.49, -3.0%; Canary: -2.19% | **Two contract months, both real.** $6.549 is the December contract's Friday settle; $6.492 is the expiring October contract, which Yahoo's front-month series shows for Friday. Like-for-like, December fell **3.2%** on the week and October **3.0%**. Canary's -2.19% compared December with last week's October close. Either way copper is under $6.60. Canary's row is corrected; facts.json is unchanged |
| **2-Year** | **4.83%** Fri (Treasury) | financials: 4.78% "from 4.905%"; feed: 4.63% | Treasury and FRED agree: 4.87% Thu Sep 24, 4.81% Fri Sep 25, 4.92% Mon, 4.78% Thu Oct 1, **4.83% Fri Oct 2**. The financials page is corrected. **The feed is not broken:** `market_state.json` reports the 2-year yield *future* (Yahoo 2YY=F, 4.635), as DATA_FEED.md specifies. On Sep 30, the day the expiring contract settled, it printed 4.885, in line with cash (4.88); the next contract has run about 20 bps under the cash 2-year since. It is a weak proxy, not a derivation error |
| **10Y–2Y** | **+45 bps** | "~20 bp steeper in a week" (financials, #123, earnings page); feed: 65 | On the Treasury curve: 26 bps Wed Sep 23, 36 Fri Sep 25, 46 Thu Oct 1, **45 Fri Oct 2**. That is **+9 bps Friday to Friday** and about +20 from the Sep 23 close. The feed's 65 follows from its futures-based 2-year |
| **DXY streak** | 101.93 | Sector pages: "ninth straight weekly gain" | **Third.** Friday closes: 99.16, 99.12, 100.22, 100.97, 101.93. The weeks of Sep 4 and Sep 11 were down. Sixteen mentions on eight pages are corrected |
| **DXY high** | — | "52W high 102.10" vs "traded 102.21" | **Both right.** 102.10 was Thursday's close, the 52-week closing high; 102.21 was Thursday's intraday high. The first pass of this page was wrong to call them inconsistent |
| **Silver** | not in facts | materials -6.6%; feed -7.3% | -6.64% on settled bars ($64.245 → $59.977). The feed's figure uses the Sep 25 value captured before Yahoo revised that bar |
| **Brent** | not canonical | $102.25 on eight pages | Contract-roll artifact in the continuous series (flagged by Canary and energy). WTI is the oil number |
| **Feed policy gate** | Oct 7 auction + minutes, CPI Oct 14 | `market_state.json` carried the Sep 19 text | Fixed: the file was re-derived against the current facts.json and now passes the purity check |
| **Credit** | not in facts | Canary, tech, financials, materials: stale or not sourced | Refreshed from FRED: HY OAS 324, IG 86, HY–IG 238, CCC 1,215, EM 161 (Thu Oct 1); 10Y breakeven 2.36% (Fri Oct 2). Canary and financials rows updated |

### B. Counts and bases the sector pages had wrong (corrected on the pages)

| Claim on the page | Verified from Friday closes |
|---|---|
| XLU "first up week in seven / after six down"; "seven weeks below" the 200-day | First up week in **four** (it rose 0.8% the week of Sep 4); **ten** straight weekly closes under the 200-day |
| XLY "seventh straight red week" | **Eighth** ($119.86 on Aug 7 to $110.04) |
| XLP "sixth straight red week" | **Seventh** (the first, the week of Aug 21, was -0.1%) |
| XLF "third straight weekly loss" | **Fourth** (flat the week of Sep 4, then four down) |
| XLK "fourth straight weekly gain" | **Sixth** |
| XLRE "fourth straight week under the 200-day" | **Third** (it closed above on Sep 11) |
| XLF "$0.17 above its 200-day" | True on dividend-adjusted closes ($53.32). On raw price closes the 200-day is **$53.71** and XLF is $0.22 **below** it. All sector-page moving averages are on the adjusted basis; XLF is the only sector where the basis changes the answer |
| "The Nasdaq made a record" Friday | The **Nasdaq 100** made a record close (30,807.93). The Composite set an intraday record and closed at 27,190.86, under its Sep 22 close of 27,244.28 |
| SMH one-year return "~+89%" | **About +87%** (total return from the Oct 2, 2025 close; +87.9% from Oct 3). The other eleven sector figures check out as total returns |
| CSCO "+5.6%" | +5.2% in price; +5.6% includes Friday's dividend |

### C. Cross-sector — same factor, opposite reads

1. **🚨 Payrolls +29K is a bull trigger and a bear trigger at once.** Tech and semis: the October hike died, a record close, "everything they could have asked for from the Fed." Financials: "the first hard datapoint that argues *for* the credit scare." Discretionary: "a Fed that pauses because the consumer is slowing is not a bull case." Calendar: labor flag **fired**, regime-change candidate. Utilities calls it "the classic defensive bid" and got one; staples and healthcare expected one and did not. **Issue #129.**
2. **ISM 54.5: gate cleared or headline miss.** Industrials upgraded machinery to overweight on it ("the arbiter ruled"); materials says it "did not matter"; the calendar logs it as a **MISS** against 55.0 consensus, with prices paid (77.9) the hawkish detail.
3. **Is the defensive bid alive?** Utilities: reversal on doubled volume, stance up. Staples: "the shelter was sold on the week it should have been bought," stance down. Healthcare: sold on policy, stance down. Canary: one week is not a turn.
4. **AI power.** Industrials: GEV and CAT power generation are the longs. Real estate: data centers decoupled upward. Utilities: the scarcity pair lost its catalyst for five months (CEG -2.2%, nat gas -5%). Same demand, three verdicts depending on who gets paid when.
5. **Micron or its suppliers — Cecil against Cecil.** Tech page: "I add to MU here, post-print… I do not chase equipment." Semis page: "I'd rather own what Micron buys than Micron." Marky (semis): "Equipment is the group I want."
6. **Does the G-7 diesel release work?** Industrials, staples and discretionary book it as fuel relief. Energy: "I do not think 0.8 mb/d for four months closes a gap created by shipping, strikes and an export ban."
7. **Credit scare or rate shock — now with data on both sides.** Financials' wild card (regionals outperforming three weeks running, which checks out) says rates and marks. The spread refresh says junk borrowers are being repriced too: HY OAS +58 bps in eight sessions, CCC at a 52-week high. Both can be true. The bank reserve lines on Oct 13 decide which one matters.
8. **Cash.** The desks sit at **25–30%**; the Council's own book has been capped at **20%** since Sep 28. Carried from last week (#119), still unruled.

### D. Dates and consensus

- **AZZ: resolved.** Results Tue **Oct 13 after the close**, call Oct 14 (company release; yfinance agrees). The industrials page's Oct 7 is corrected.
- **PepsiCo Thu Oct 8 and Delta Fri Oct 9, both before the open:** confirmed on the yfinance calendar. Delta's consensus differs by source ($1.88 on Yahoo; other week-ahead tallies run higher).
- **October-hike odds:** a week ago ~70% (sector pages), 64% (Yahoo), 73–76% (CME as previously carried); now about 17–23% depending on the source and the hour.
- **Micron consensus EPS:** $31.16 (tech, +7.3% surprise) vs $31.82 (Earnings Surveillance, +5.0%).
- **JNJ consensus:** $2.48 (yfinance) vs $2.90 (Earnings Whispers) — different bases; do not compute a surprise.
- **MSFT / AMZN / AAPL dates** differ between yfinance and Earnings Whispers by one to four days.
- **Still not verified:** whether the Google ad-tech proposed final judgment was filed on Oct 2 (it was due); the VMRK symbol Yahoo attributes to AvalonBay; TSMC's September revenue date.

---

## 8. MACRO CALENDAR IMPACT — The Quietest Data Week Is the Loudest Rates Week

**What last week's data did to the posture.** The Council went into the week with two flags up and a stated plan: PCE on Wednesday and payrolls on Friday would decide whether 5.25% was next. Both came in on the dovish side — core PCE **+0.2%**, payrolls **+29K** — the Fed's leadership talked October down, and 5.25% broke anyway. The calendar page owns the miss: it told the Monday scan the payrolls consensus looked too low, and it was too high by about 60K with another 60K of revisions. The corrected read for Monday is specific: **consensus is too low on output and too high on hiring and confidence.** Chicago PMI 58.8 vs 51.0, ISM new orders, construction, ADP and claims beat; payrolls, JOLTS, Conference Board and the ISM headline missed.

**The posture effect is a tightening, not a pivot.** The temptation after Friday is to read +29K as permission to buy duration and rate-sensitive equities. The tape refused: with hike odds collapsing, the 10-year closed higher and XLP, XLRE, XLV and XLF all made new lows for their moves. The credit refresh adds a second refusal: junk spreads widened every day of the week. So the posture is: **hold reduced exposure, add no duration, and move the caution one notch toward consumer cyclicals and credit-sensitive names** (confidence at a 12-year low, Nike's guide, zero net hiring, HY OAS through 300). The front end is the exception — with the bill at 3.993% and October off the table, short paper pays without price risk. Three flags are up: **NFP fired, the 10-year is broken through 5.25%, CPI is carried.**

**This week's gauntlet, in order of consequence:**

- **Sun Oct 4 — OPEC+: done. November targets held**, as priced. Nothing changes for the one negatively correlated sector on the board.
- **Mon Oct 5 — ISM Services (10:00, cons 55.1–55.7); Friday's credit-spread prints post.** Read prices paid and employment before the headline. **> 57** with rising prices firms December and retests 5.342%; **< 53** turns a soft jobs number into a growth scare; employment under 50 confirms the labor flag. HY–IG above 250 would turn Canary's credit row yellow.
- **Tue Oct 6 — Trade balance, $58B 3-year auction (1:00), STZ after the close, WBD merger close.** A 3-year tail > 1 bp says front-end demand is weak even with October priced out.
- **Wed Oct 7 — the day that matters: $39B 10-year auction 1:00 PM, FOMC minutes 2:00 PM.** A tail > 2 bps or a close above **5.342%** extends the break toward 5.50%. The minutes predate the PCE and payrolls prints and will sound more hawkish than the Fed does now. **No new rate-sensitive positions before 1:00 PM without a stop.**
- **Thu Oct 8 — claims, $22B 30-year auction (30Y at 5.63%, cycle high 5.691%), PepsiCo before the open, Shanghai reopens.** A fourth sub-200K claims print fires the "consensus may be stale" streak flag; above 225K confirms payrolls with layoffs.
- **Fri Oct 9 — UMich preliminary (cons 48.1), Delta before the open.** One-year inflation expectations at or above 4.8% is the de-anchoring line.

**The week after is where the posture can actually change:** bank and healthcare prints **Tue Oct 13** (JPM, WFC, C, GS, UNH, JNJ on one morning; AZZ after the close), **September CPI Wed Oct 14 at 8:30** (the one flag that can clear), **TSMC and Prologis Oct 15**, then the FOMC **Oct 27–28** with MSFT, META, GOOGL and TMUS reporting that evening.

**Net Council posture into Monday:**

- **Regime:** hiking cycle on pause, bear steepening; three flags raised; Council Review (#127).
- **Canary Watch:** 🟡 **CAUTION (rates-led, now with a growth scare)**, sixth straight week. Breadth red (24.7%), correlation row off red, DXY at its trigger. **Credit: widening and now measured** — HY–IG 238 bps, 12 under the 250 trigger, so none of Canary's four strict criteria is met and its no-issue call stands.
- **Exposure:** keep the leadership (semis, tech, machinery and power) with stops at $609.66 / $198.73; no new duration; nothing new in high yield, construction materials, branded food, broadband or aerospace and defense before their receipts.
- **Hedges:** cheap, with VIX at 15.31 and equity put/call at 0.58. The thing to hedge is a 10Y move to 5.50%.
- **Cash:** desks at 25–30% against a book capped at 20%; until the owner rules, the difference has to come from hedges.

---

> *Synthesis compiled by the Saturday Research Crew — Synthesis Agent*
> *Timestamp: 2026-10-04T21:55:00-04:00 (second pass, owner-requested; first pass 2026-10-04T03:45:00-04:00, itself a late run of the Sat 2026-10-03 20:26 ET slot)*
> *Data as of: Friday, October 2, 2026 closes — all 15 wikis + macro/facts.json (generated 2026-10-04) + data/market_state.json (as_of 2026-10-02, re-derived Oct 4). Second-pass sources: Yahoo daily bars re-pulled Oct 4; U.S. Treasury par yield curve; a direct FRED download (credit OAS through Thu Oct 1, breakeven through Fri Oct 2); TreasuryDirect auction schedule; OPEC+ decision of Oct 4; company releases (AZZ, Paramount Skydance / Warner Bros. Discovery); Trepp September delinquency via Yield PRO.*
> *Wiki freshness: 15 of 15 fresh, 0 stale. Truth Layer: facts.json fresh and consistent with a Sunday re-pull. Still open: Friday Oct 2's OAS prints (post Monday); the feed's 2-year is a futures proxy about 20 bps under cash; Google ad-tech filing and the VMRK symbol unverified; the 25–30% desk cash vs 20% book cap is the owner's call.*

*Last updated by Saturday Research Crew: 2026-10-04*
