# Weekly Council Synthesis — Week Ending Friday, November 20, 2026

> ✅ **DATA FRESHNESS (STEP 0a INPUT GUARD, then STEP 0, both checked first). ALL FIVE GUARD CHECKS PASSED AT FIRST LOOK; NO WAIT. ALL FIFTEEN WIKIS ARE FRESH AND THE TRUTH LAYER IS CURRENT. THIS JOB RAN ON SCHEDULE (Saturday 2026-11-21, ~20:29 ET).**
>
> - **Input guard (first run of the 2026-11-16 rule).** (1) `data/market_state.json` as_of **2026-11-20**, the week's last session. (2) `macro/facts.json` generated **2026-11-21** (Canary Watch, commit 534cfed). (3) No `stale: true` on WTI or gold: both are the feed's Nov 20 contract settlements. (4) All fifteen wikis stamped on or after Nov 20. (5) `logs/cron.log` shows a START and an END for Grids A, B and C, the feed builder, Semis + Economic Calendar, Earnings Surveillance and Canary Watch; nothing was in flight. Canary's END landed 20:03 ET, 26 minutes before this job started.
> - **Fresh, stamped 2026-11-20 (Friday-night runs, Friday bars):** tech, financials, healthcare, industrials (Grid A); consumer-discretionary, consumer-staples, materials, real-estate (Grid B); utilities, energy, communication-services (Grid C). **Fresh, stamped 2026-11-21:** semiconductors, economic-calendar, earnings-surveillance, canary-watch. **No wiki is over the 7-day line. No stale page.**
> - **Every macro number below equals facts.json:** 10Y **4.912%**, 5Y **4.701%**, 2Y **4.76%**, 3M **4.122%**, 10Y–2Y **+15**, 10Y–3M **+79**, VIX **35.89**, SPY **$689.81**, DXY **103.81**, EUR/USD 1.097, USD/JPY 159.707, WTI **$83.98** (CLZ26), gold **$3,512.30** (GCX26), copper **$5.477**, BTC **$58,799**, HYG **$76.33**, LQD **$103.69**, fed funds **3.75–4.00%**, stance **Hike**. All twelve sector ETF closes and week changes on the sector pages match facts.json to the cent.
> - **One field is a day old by design, and this week it matters.** The **2Y (4.76%) is FRED's Thursday Nov 19 print**, so the **10Y–2Y of +15** pairs Friday's 10-year with Thursday's 2-year. The 10-year fell 14 bps on Friday alone; Treasury's Friday par curve, used by Grid A, the calendar and the feed, reads the 2Y at 4.63% and the spread near +29. facts.json stays the number of record here; the gap is logged in section 7 and it changes how financials' "+30" curve gate should be read.
> - **What the Friday-night pages could not see.** They wrote Friday-evening futures reads and called them provisional. The settlements are now in: WTI **-5.2%** (-$4.58, under the $5 line, as the energy page expected), gold **-9.5%** (the pages said about -8.8%), silver -16.3%, and **copper -9.91%, which is under the 10% line** the materials page said it had crossed (#219). Section 7 carries it.

---

## 1. CECIL'S SYNTHESIS — Fundamentalist Lens

**The estimates went up and the multiples became unreadable.** NVIDIA reported **$115.8B** of revenue, guided **$130B** against about $125B and raised its fiscal-2028 growth view to 75%. It then fell **22.9%** to **$125.53** on a reported SEC probe of its disclosures. Cecil's line is the same on two pages: *"an accounting question is the one thing that makes a forward multiple unreadable, because the E is what is being questioned."* NVDA is **7.6x forward** (tech) and **13.5x trailing** (semis), the cheapest either page has shown, and he does not start it. That logic runs down the whole chain, because every supplier's guide is built on NVIDIA's orders.

**Where he sees value.** **MSFT at 20.0x** is the one thing he actually buys this week: "no probe, no founder risk, down 7.3% with everything else." On the list, not in the book: **ETN at 18.9x** and a 52-week low ("first in line", two resets done), **JPM at 12.1x**, **XOM at 12.8x** after the Nov 29 OPEC+ meeting, **DIS at 13.8x** after a beat, a 33% dividend raise and a $3B savings target, **CMCSA at 7.1x**, **SYY at 14.5x**, **STZ at 11.7x**, **SRE at 13.8x** (a 52-week low: "a list item, not a buy"), **CCI** at a 5.2% yield, **TXN and ADI** as the only two chip names within reach of their 200-day (ADI reports Tuesday), and **BKNG at 11.8x** at a 52-week low, watched and not added.

**Traps, in his words.** **Memory**: MU at 8.0x trailing and SK hynix at 5.7x, "the market telling me the earnings are going down" (TrendForce's first negative NAND call). **Citi at 8.5x**: "a controls failure, and I do not buy a controls failure at any multiple until the regulator has spoken." **The miners**: FCX 10.9x and NEM 9.5x "on estimates that are a week out of date", written with copper over $6 and gold near $3,900. **Managed care**: UNH 14.5x, CI 8.1x, "cheap if the past earnings were real", after CMS proposed audits reaching back to 2018 worth about $9B a year. **Corteva** at 9x, "still a falling knife." **Skydance**, "a debt story." **Target's beat is $2.15, not $2.65**, once the tariff refund comes out. **Costco at 44x** is still over its target. **UVV's 10.1% yield** "is a price the market does not trust."

**His book, marked.** Up: TMUS **+13.0%**, VZ **+11.6%**, PPG **+9%**, GE **+8.4%**, DTE **+6.0%**, O **+3.5%**. Down: VST **-24.2%** (he stops defending it under $112.89), LRCX third **-20.4%**, NFLX half **-20.3%**, UNH **-16.5%**, SLB **-12.5%** ("I bought a service company before the customers' budgets were known"), ELV **-6.1%**, CVS **-3.6%**, EOG -1.3%, LMT -0.3%. AXP fell 5.9% and is held. He adds to nothing but Microsoft and averages down nowhere: "a price falling is not a number changing."

**Dividend spreads that matter.** Against facts.json's **10Y 4.912%**: utilities' **2.79%** sits **-212 bps** under (from -236), staples' **2.46%** **-245 bps** (from -269), real estate's **3.34%** **-157 bps** (from -181). All three gaps narrowed 24 bps and **all three funds fell anyway**, the mirror of last week, when the gaps widened and the funds rose. The proxies are still not trading as bonds. Yields that clear the 10-year: **UVV 10.1%**, **BRT 7.8%**, **CTO 7.7%**, **SAFE 7.6%**, **GIS 7.1%**, **GTY 7.1%**, **VZ 6.2%** (about **+128 bps**, from ~93), **MO 6.0%**, **NOMD 6.0%**, **O 5.7%**, **EIX 5.6%**, **CMCSA 5.3%**, **CCI 5.2%**, **T 5.1%**, **AVA 5.0%**. SAFE and UVV both closed at two-year lows with yields falling, so yield is still not the screen. What paid was plainer: GIS at 11x and CPB at 13x rose 4%, VZ and T rose, O lost 1.3% in an 8.6% week.

---

## 2. MARKY'S SYNTHESIS — Technician Lens

**Every stop that could fire, fired.** SPY **-8.56% to $689.81**, the second-worst week on two years of bars, through its 200-day ($732.76) and to its lowest close since April 13. QQQ **-10.5%** to $608.45, DIA **-8.0%**, IWM **-7.5%**. VIX closed over 22 every day (**22.91 / 25.46 / 24.56 / 28.44 / 35.89**, 40.03 intraday Friday) and VIX/VIX3M went into backwardation Tuesday and ended at **1.160**. **All twelve sector funds fell.**

**Breadth by the Grid's own count.** Down on the week: **12 of 12** (SMH -17.81%, XLK -12.49%, XLC -7.97%, XLB -7.45%, XLI -7.35%, XLF -7.00%, XLE -6.85%, XLY -6.27%, XLV -6.15%, XLRE -4.30%, XLU -3.07%, XLP -2.05%). **Above the 50-day: 3 of 12** (XLP, XLV by 80 cents, XLU by 78 cents), from 8. **Above the 200-day: 4 of 12** (XLP, XLV, XLF by 1.5%, XLE by $1.28), from 8. Lost this week: XLU's 200-day after one Friday over it, XLB's and XLRE's, XLY's on Friday's close. Canary's index count agrees: **42.7%** of S&P members over their 50-day, from 71.3%, and no session with more advancers than decliners.

**The stop ledger.** Marky came in long eight funds and leaves long three, all reduced.
- **XLK**: stopped Monday at $164.76 on the gap under $169.35. The fund then lost another $15.75.
- **XLI**: starter stopped Tuesday at $164.75. "A rally on volume under the average is not a signal."
- **XLB**: two-thirds stopped Tuesday at $50.84, the day it lost the 200-day.
- **XLRE**: stopped Thursday at $42.88, about flat on three entries.
- **XLY**: stopped Friday at $112.46, **-$5.70** from $118.16, on the close under the 200-day.
- **XLP**: second half sold Thursday at $89.86; the half from $81.70 stays.
- **XLV**: half off on two closes under $181.30; "I called a coil and got a break."
- **XLF**: second add off on Friday's close under **$55.03**, which is also the Council's sector stop; the first add held $54.46 by 11 cents.
- Never filled, by pennies: **XLC** (high $109.11 vs a $109.31 line), **XLU** (Monday close $44.12 vs $44.14), **XLE** (never over $64.97), **SMH** (flat: "the rule kept me out, not foresight").

**Levels that matter now.** Funds sitting on a single shelf: **XLI $155.81** (the March closing low; Friday traded 11 cents through it), **XLC $99.90** (the 52-week closing low; held by 13 cents), **SMH $396.85–399.90** ("under that there is no shelf on my chart until $315–325"), **XLB $48.05**, **XLE's 200-day $59.23** (untested), **XLV's three levels inside 80 cents** ($177.07 / $176.60 / $176.44), **XLF $54.46** then the 200-day $53.75. Gaps left overhead: **XLK $160.69**, **SMH $443–447**. RSI: SPY 24.9, XLK 25.4, SMH 26.1, NVDA 15.0, XLB 30.7, XLI 30.8; only XLP (54.8) is over 50.

**Volume went the wrong way.** Friday was the heaviest day since February for XLK (36.4M), since March for XLF (81.8M), and twice the average for SMH (23.4M), all closing near the lows. The one constructive print: **XLV closed -0.1% on a -3.6% day** on 18.0M shares with UNH, JNJ, ABBV and MRK green, and **XLP rose 0.7% on 34.4M**. The insurers (CB, PGR, TRV) and the integrated oils (XOM, CVX, COP) were also up Friday.

**Correlations breaking.** (1) **Yields and the proxies**: three weeks, three answers for XLU; this week the 10-year fell 24 bps and XLU, XLRE and XLV all fell. (2) **Gold and real yields**: gold -9.5% while the real 10-year fell about 15 bps. (3) **Gas and gas producers**: gas up 5–7% on the same contract, CRK -22.5%. (4) **Beats and prices**: $10B+ reporters averaged +3.0% on the day Monday to Wednesday and -3.5% Thursday and Friday. (5) Every one of the twelve sector correlations with SPY rose; utilities went from 0.072 to 0.345.

---

## 3. OPHELIA'S SYNTHESIS — Macro Lens

**The rotation story is that there was no rotation.** Canary's phrase is "liquidation, not rotation into havens." All twelve sectors fell; ten fell less than SPY only because the index is two sectors (**SMH -17.81%, XLK -12.49%**). Under them the order was the textbook defensive one: staples -2.05%, utilities -3.07%, real estate -4.30%, then every cyclical between -6% and -8%. Equal weight lost less (**RSP -6.20%**), so the largest names did the most damage, but 6% for the average stock is not narrow. Outside equities the havens split: **Treasuries worked** (10Y **-24.2 bps to 4.912%**, TLT +2.61%), and **gold (-9.5% to $3,512.30), Bitcoin (-13.85% to $58,799), copper (-9.91%) and WTI (-5.2% to $83.98)** all fell with stocks. The dollar held its 52-week high area at **103.81** with no yen bid.

**Three shocks, none of them macro.** (1) **Trust in the AI base**: a reported SEC civil probe of NVIDIA's disclosures, a BIS remote-access rule that took effect Thursday and has TSMC and Samsung pausing some China shipments, a short report on AMD, the first negative NAND forecast, a reported Google cut at Broadcom, and Anthropic's record $81.3B IPO sliding on day two. (2) **Policy in the shelter**: CMS's Medicare Advantage audit proposal took 8–17% off managed care in the same five days. (3) **Controls at the banks**: Citi's reported $35B asset undercount and a customer-data leak at Visa, Mastercard and JPMorgan.

**The cross-currents.** The Fed did not blink. The October minutes said higher rates are needed in December and probably early next year; December is **~95–96% priced** and J.P. Morgan now calls three hikes. The 3-month bill did not move (**4.122%** both Fridays). So the long end priced lower growth and lower inflation (the 10-year breakeven fell 9 bps to 2.15%) while the front end kept the hike: 10Y–3M lost 24 bps to **+79**. Credit followed equities and did not lead them: **HY OAS 352, HY–IG 258** (three straight prints over 250), **CCC 1,361**, the widest of the fetch, all as of Thursday, with Friday's print still to come.

**What the Economic Calendar revealed.** For the first time the activity data leaned the same way as the tape: **Empire 7.8** against 18, **Philly Fed 6.3** against 20 (capex intentions 18.9 from 34.9), industrial production **-0.4%**, the leading index -0.3%, claims missing twice (203K), permits and pending home sales missing, NAHB 25. That is **five straight regional-survey misses**, a flagged bias. Inflation stayed hot in the pipeline: import prices **+1.1%**, Philly prices paid **58.2**. The consumer held: retail sales +0.2% in line, control **+0.6%**. The only cool read was households' own: UMich one-year expectations **3.7%** from 4.7%.

**Her posture, desk by desk.** Tech and semis: reduced, no adds; "I want credit to stop moving first." Financials: neutral, "a second week of HY widening would take me to cautious." Industrials: **machinery to negative**, transports down to neutral. Healthcare: **managed care to cautious**; "I don't size up a shelter with its own weather." Materials: restriction on new commodity longs stays ON. Energy: reduce held, no new longs before Nov 29. Real estate: half size, and **she declines the Friday close under 5% she asked for**. Utilities: regulated wires at half size, avoid the merchant pair. Discretionary: underweight. Staples: defensive-lean, and the one desk where she adds. Her calendar note sets the frame: bills first, hedges back to full size, no new gross equity exposure while VIX closes over 30, and no selling into a 36 VIX.

---

## 4. CONSENSUS SYNTHESIS

**Where all three agree.**
1. **Nobody buys the AI complex on price.** Cecil cannot value earnings under a disclosure probe; Marky needs gaps filled on volume ($160.69 on XLK, $447.48 on SMH); Ophelia wants a scope on the SEC matter, BIS licences flowing, or a named CEO. Three different tests, one answer: wait.
2. **The 10-year under 5% is not the signal it was meant to be.** Semis, real estate and the calendar had each named it as an add condition. All three got it Friday and all three declined it: "people bought bonds to hide." A second weekly close under 5% is the new bar.
3. **Credit is the tell.** Tech's Ophelia wants HY to stop widening before anything else; financials' moves to cautious on a second week; Cecil stays at zero in high yield. Friday's HY–IG print, posted Monday, is the first number of the week.
4. **Plain beat clever.** Regulated wires over merchant power, Verizon and AT&T over Meta and Alphabet, General Mills and Campbell's over Costco, insurers over dealers, Exxon over the service names, Realty Income over the data centers.
5. **Cash and bills.** The 3-month pays over 4.1% with the hike priced. Nobody is asking for more risk.

**Where they disagree.**
- **Add or stand still.** Cecil adds to MSFT. Staples' Ophelia adds a first piece of XLP at the 20-day. The calendar's Ophelia says no new gross equity exposure while VIX closes over 30. All three positions are written for the same Monday.
- **Sell or hold.** Marky's stops sold eight funds, several within a few percent of where the week ended. The calendar says "do not sell into a 36 VIX... forced selling at that reading is usually late." The rule and the regime note point opposite ways, and XLY's stop fired on the exact close of the worst day.
- **Is AI demand intact?** The semis page says "the demand data are fine" (NVIDIA and AMAT guided up). Industrials, utilities and real estate say the market is marking the demand down "from the buyer's side," and Philly capex intentions halved. Cecil calls ETN and CAT "a gift" if the orders are real and financed.
- **Is the shelter safe?** Staples and utilities say the defensives did their job. Healthcare says its shelter leaked. The utilities wild card and staples' own Ophelia both warn that in a third week of liquidation the liquid, profitable holdings are sold to meet redemptions.

**The single biggest risk: a Fed hike into a correction with only one hedge left.** December is 95% priced, the S&P is 11.5% under its high, VIX is 36 and backwardated, and gold and Bitcoin failed. The Treasury is the last diversifier, and it rallied on fear. A hot core PCE on Wednesday (≥ +0.4%) or a relief rally in stocks puts the 10-year back over 5.00% in a session and takes that hedge away while credit's Friday print is still unread and the tape is a holiday tape.

**The single biggest opportunity: a narrow answer on NVIDIA.** The probe is reported, not confirmed, and nothing is charged. Bessent asked the board for answers "in the next 10 days," which lands about Nov 27–30. If the matter is disclosure format and not revenue recognition, the page's own words are "13.5x is a gift," and the same answer re-rates the suppliers (ETN, CAT, GEV), the merchant power pair and the data-center REITs that fell on no news of their own. Until then the quieter version is already paying: the plain defensives and Friday's first bids in XLV and XLP.

---

## 5. MONDAY WATCHLIST

*All fifteen wikis fresh. Levels are Friday Nov 20 closes from the sector pages; macro from facts.json. Holiday week: closed Thursday, 1:00 PM close Friday. Arena: week of Nov 23 is open on #211 (lock Mon 8:50 AM ET).*

**Macro gates (these outrank every ticker line):**

| Gate | Level now | Trigger | Action |
|---|---|---|---|
| **VIX** | **35.89**; VIX/VIX3M **1.160** | Close **under 30** (size line) / **under 22** (flag clears); ratio back under 1.00 | Over 30: no new gross equity exposure, hedges full size (calendar). Marky adds nothing until the ratio is under 1.00 and a day has more advancers than decliners |
| **Credit, Mon** | HY OAS **352**, HY–IG **258**, CCC **1,361** (Thu) | Friday's HY–IG print: 260 or 280; HY OAS through **375** | Financials to cautious on a second wider week; tech and semis stay "no adds" |
| **10Y** | **4.912%** | Back **over 5.00%** / second weekly close under it; 4.75% below | Over 5.00% with stocks still falling removes the last hedge (Canary). A second Friday under 5.00% reopens the duration add and XLRE's size |
| **Core PCE, Wed 8:30** | cons **+0.3%**, 3.2% y/y | **≥ +0.4%** / **≤ +0.2%** | Hot: 50 bp December odds over 25%, 10Y back over 5.00%. Cool: 10Y under 4.85%, the calendar's duration add |
| **GDP, durables, claims, Wed** | cons 3.5% / ex-transport +0.5% / 200K | GDP **< 3.0%**; durables ex-transport **< 0.0%**; claims **> 215K** | Growth scare in hard data; capex rolling over with the AI trade; labor flag at risk |
| **2Y / 5Y / 7Y auctions** | priors 4.708% / 4.845% / 4.894% | 2Y stop over 4.70% vs under 4.55%; 5Y under 4.65% | Whether the front end still prices hikes through the selloff |
| **SPY** | **$689.81**; 200D $732.76, 50D $760.18 | Close under **$686.10** (Apr 13 close) / bounce toward the 200-day | Ophelia raises cash on a bounce toward $732.76, not into the low |
| **Breadth** | S&P **42.7%** over the 50-day | Under **40%** | Canary's red line; the verdict moves again |
| **NVIDIA / SEC** | $125.53; RSI 15.0 | Any SEC, board or outside-counsel statement (Bessent's "10 days" ≈ Nov 27–30) | Narrow: Marky's NVDA line is **$145.98**. Wider: no multiple to anchor on |
| **DXY** | **103.81** | Weekly close **< 99** / **> 105** | Under 99 lifts the materials restriction; over 105 is Canary's red line |

**Sector funds:**

| Ticker | Close | Trigger | Stop / invalidation |
|---|---|---|---|
| **XLK** | $149.01 | Flat. Close over **$160.69** plus a top-half close on volume over 15.2M | Below: $145.27, then $141.36–142.28; 52-week low $126.38 |
| **SMH** | $400.06 | Flat. Buy a close over **$447.48** on more than 12.6M | Close under **$396.85**: no shelf until $315–325 |
| **XLC** | $100.03 | Flat. Close under **$99.90** shorts half; a long needs **$104.39** back | Short's stop over $102.76 |
| **XLF** | $54.57 | Core plus one add. Nothing back on under the 50-day **$55.85** | Close under **$54.46** takes the first add; then the 200-day $53.75. Council sector stop $55.03 already lost |
| **XLI** | $156.37 | Flat. Close over **$161.74** on volume over 9.2M; full size needs the 200-day ($172.69) | Close under **$155.81** is the low of 2026; 52-week low $145.48 |
| **XLB** | $48.34 | Flat. Back on a close over the 200-day **$50.93**. Commodity longs restricted (DXY) | Under **$48.05** no closing support until $41.48 |
| **XLE** | $60.51 | Flat. Long: hold **$59.23** then close over $61.29. Short half on a close under $59.23 | Short's stop over $61.29. OPEC+ Nov 29 |
| **XLV** | $177.24 | Half size. Re-add only over **$181.30** | Close under **$176.44** (50-day) takes the rest off |
| **XLU** | $42.69 | Flat. Close over the 200-day **$43.90** buys a starter | Starter stop $42.63; under the 50-day **$41.91** turns bearish |
| **XLP** | $90.46 | Half from $81.70. Re-buy the second half over **$92.60**. Ophelia adds at the 20-day ($90.25), more at the 50-day | Close under the 50-day **$86.34** |
| **XLRE** | $42.46 | Flat. Back on a close over the 200-day **$43.04** | Under **$42.13** the next mark is $40 |
| **XLY** | $112.46 | Flat. Back on a close over the 200-day **$115.01** | Under **$111.50** the October range is gone; then $105.22 |

**Single names and events:**

| Ticker | Level | Trigger | Note |
|---|---|---|---|
| **HPE / DELL** | $40.91 / $278.02 | Mon AMC / Tue AMC; straddles ±14.1% / ±16.4% | First AI-server prints since NVDA. DELL whisper $7.25, 7.1% over the street; no lean |
| **ADI / MDT** | $345.92 / $99.94 | Tue BMO; ±9.7% / ±4.4% | ADI is Cecil's reachable chip name; MDT tests medtech after ISRG -10% |
| **DE** | $609.25 | Wed 6:20 AM; EPS $4.01, whisper $4.30; ±7.6% | The Council's one tracked print; down five straight days; FY27 guide |
| **MSFT** | $484.52 (20.0x) | Cecil's only add | Trump's overseas data-center tax threat is the new policy risk |
| **CEG / VST** | $237.41 / $115.25 | 52-week closing lows $235.78 / $112.89 | Cecil stops defending VST under $112.89 |
| **UNH** | $339.85 | RSI 29.7; TD Cowen upgrade Friday | Held, no add; Cycle-3 drug prices due by Nov 30 |
| **CAT / ETN / GEV** | $510.45 / $311.33 / $699.33 | No company news; they trade with NVDA | ETN first on Cecil's list; nothing started this week |
| **META / GOOGL** | $560.84 / $265.29 | META's 52-week closing low $524.82; GOOGL at its low | No add until the 2027 capex bill is known |
| **C / JPM** | $110.62 / $310.53 | Any regulator statement on Citi's UK asset count | JPM on the list, not in the book, while credit widens |
| **XOM** | $159.99 (12.8x) | After Nov 29 | Up Friday with CVX and COP |

**The Council's own book (week of Nov 16, `portfolio/current.yaml`; closes from a fresh Yahoo pull this run; official scoring is Monday's tracker close).** ALL $267.00 (stop $256.50, intact), COST $1,102.15 (stop $1,054.94, intact), AES $15.02 (SPEC, no stop). **TDG traded under its $1,157.63 stop on Thursday (low $1,155.91) and closed Friday at $1,121.22; FAST closed Friday at $50.61, under its -5% stop (about $52.51).** Marked from Monday's opens the book is roughly **-1.8%** if both stops are booked at their levels and **-2.7%** at Friday's closes, against **-8.0%** for SPY from Monday's open; provisional. The book was 82.7% invested, 17.3% cash.

---

## 6. CROSS-SECTOR CONNECTIONS — The Hidden Wires

**Wire 1 — The trust chain: one probe, eight sectors.** WSJ reports an SEC civil probe of NVIDIA's disclosures (Tuesday evening) and Friday's headlines widen it to accounting → NVDA -22.9%, SMH -17.81%, XLK -12.49% (#214, #223) → the capex buyers re-rate with no news of their own: META -12.6%, GOOGL -10.3% (about 60% of XLC's loss), AMZN -7.4% and TSLA -11.4% (3.7 of XLY's 6.3 points) → the suppliers of power and steel to the build: CAT -15.0%, GEV -12.9%, ETN -11.8% (industrials), PRIM -22.7% → merchant power: CEG -15.1%, VST -13.4%, ETR -6.1% (one point of XLU's 3.1) → the landlords: DLR -9.7%, EQIX -7.7% → the financiers: GS -13.7%, MS -13.1% after pricing Anthropic's $81.3B IPO on Wednesday → even copper, where SMM tied Monday's four-month LME low to the AI selloff. Not one of these companies reported anything. Tech's wild card names the wire: "cheap multiples are only cheap if the denominator is right."

**Wire 2 — The rate chain, running on fear.** Equities break → the 10-year falls 24.2 bps to 4.912% and the 5-year 28 → every rate-sensitive desk gets the level it asked for → and none of them is paid: XLRE -4.30%, XLU -3.07%, XBI -6.9% to under its 200-day, SAFE at a two-year low ("a duration asset that falls when yields fall is being sold for credit or liquidity reasons"). Freddie Mac's mortgage rate went **up** to 7.28% because the survey caught last week's yields → NAHB 25, permits -7.4%, pending home sales -4.7% → Home Depot and Lowe's beat on comps and gave up margin. The only winners on the wire are the plain payers: VZ, T, DUK, SO, O. Meanwhile the bill at 4.122% says the Fed has not moved, so the fall in long yields is a loan from the equity market, repayable on the first relief rally.

**Wire 3 — The liquidation triangle: gold, crypto, credit.** Gold -9.5% in a week real yields fell; silver -16.3%; Bitcoin -13.85% to within $240 of the fetch's low close, with a record one-day IBIT outflow → BlackRock -9.9% (financials) → NEM -16.3%, FCX -22.4% (materials) → CCC spreads to 1,361 and HYG to a 52-week closing low (Canary). The materials page could not source a reason for gold and calls it forced selling; Canary reads it as selling to raise cash. The utilities page draws the forward version: "in a third week of liquidation the liquid, profitable holdings are the ones that get sold." That is the risk to XLP and XLV, the two funds still over their 50-day.

**Wire 4 — Washington in the shelter.** The midterms keep paying out in policy: CMS's audit rule (UNH -16.6%, CVS -9.5%, CI -8.8%, ELV -8.2%) → Cycle-3 negotiated drug prices due by Nov 30 → a Medicare-for-All push in the coverage → the BIS export rule (TSM -20.1%) → Trump's vow to tax data centers built abroad (MSFT, ORCL) → Bessent's ten-day demand of NVIDIA's board → the SEC taking direct control of the audit trail → Virginia's NEE–Dominion hearing and Montana's court challenge to the now-closed Black Hills merger. Healthcare's line covers all of it: "In a week when investors needed the shelter, the landlord raised the rent."

**Wire 5 — Factory surveys, the barrel and the capex budget.** Empire 7.8 and Philly 6.3 with capex intentions halved → industrial production -0.4% → EIA crude +3.4M barrels against +58k expected, distillates building → the diesel crack narrows about $9 → VLO -12.0%, MPC -11.2% → then the market leg takes the service names (SLB -11.2%, BKR -9.4%), which sell into customers' budgets exactly as ETN and CAT do → Deere reports Wednesday into a 103.81 dollar, the ISM lands Dec 1, OPEC+ meets Nov 29 with inventories rising. The stocks that depend on someone else's spending plan fell hardest in every sector this week.

---

## 7. SECTOR CONTRADICTIONS — Where the Wikis Disagree

### A. Truth Layer — facts.json against the sector pages

facts.json wins on every row; the sector pages' numbers are recorded here, not restated elsewhere.

| Item | facts.json (gen. Nov 21) | What the pages say | Resolution |
|---|---|---|---|
| **2Y** | **4.76%** (FRED, Thu Nov 19) | Grid A, the calendar and the feed: **4.63%** (Treasury par, Fri) | Basis and day. facts.json is Thursday's print; Friday's is not posted. Canary says so on its own page |
| **10Y–2Y** | **+15** (mixed-day) | Tech, financials: **+29** (par, Fri); Canary same-day Thursday: +28; feed: 28 | facts.json's +15 pairs Friday's 10Y with Thursday's 2Y and is "probably too low" (Canary). Financials' Ophelia is "1 bp short" of her +30 gate on the par basis; on facts.json she is 15 short. Same curve, two readings of one gate |
| **3M / 10Y–3M** | **4.122% / +79** (^IRX, discount basis) | Grid A: 3M **4.32%**, 10s–3M **+60** (par) | Basis. Both show the same thing: the long end fell, bills did not |
| **10Y** | **4.912%** | Grid A 4.92% (par); Grids B, C 4.91% | Rounding and basis; no conflict |
| **WTI** | **$83.98** (CLZ26 settle), -5.2%, -$4.58 | Grid A, B: $83.62 (CL=F), "about -$4.9, provisional"; energy: -$3.67 to -$4.47 same-contract | Settlement confirms energy's call: under the $5 line, no WTI trigger |
| **Gold** | **$3,512.30** (GCX26), -9.5% | Tech, materials: ~$3,539, "about -8.8%, provisional" | The settle is worse than the Friday-evening read |
| **Copper** | **$5.477**, -9.91% (Canary) | Industrials, materials: $5.47, "about -10.1%"; materials' trigger line says copper "crossed the 10% commodity line" (#219) | **On the settled number copper did not cross 10%.** Silver did (feed: -16.3%). #219's price trigger (XLB -7.45%) stands; its copper leg does not |
| **DXY** | **103.81** | Grids A, B: 103.84 (Fri evening); Grid C, semis, calendar: 103.81 | Three cents; the restriction rule reads the same either way |
| **Sector closes / W/W** | 12 rows | All twelve pages | **12 of 12 match** |
| **HY OAS** | not in facts.json | Grid A: 3.52% (Nov 19); Canary: 352 bps (Nov 19) | **Match.** Last week's stale-credit gap (#210) is closed: Grid A re-sourced FRED |

### B. Same factor, opposite reads

1. **AI capex: "the demand data are fine" vs "marked down from the buyer's side."** Semis points at NVIDIA's $130B guide and AMAT's. Industrials, utilities, real estate and comm services all record the buyers and suppliers being repriced, Philly's capex index halved, and Zacks' "cracks in the AI cap-ex boom." Financials adds the financing question: how much of the Anthropic, SpaceX and data-center paper is still on dealer balance sheets. Bull and bear on one factor; the issue filed this run carries it.
2. **Monday's posture: add, hold, or stand still.** Cecil adds MSFT (tech). Ophelia adds XLP at the 20-day (staples). Ophelia's calendar note: no new gross equity exposure while VIX closes over 30. Tech's Ophelia: "reduced, no adds."
3. **Stops vs "nobody sells into a 36 VIX."** Marky's rules sold XLK, XLI, XLB, XLRE, XLY and halves of XLP and XLV; the calendar tells the Council not to sell at RSI 24.9 and to raise cash on a bounce. XLY's stop booked -$5.70 on the low close of the week.
4. **The shelter.** Staples: "that is the job." Utilities: "the plain utilities did their job." Healthcare: "it did not protect" and "I don't size up a shelter with its own weather." Canary: only XLP and XLE still have low correlation to SPY, "and neither is negative."
5. **Credit: orderly or the next shoe.** Canary: "credit followed equities down; it did not lead them," HYG only -0.79%. Financials' wild card and tech both treat widening credit as the condition for everything else, and CCC is the widest of the fetch. Financials' Ophelia waits for "a second week of HY widening"; on Canary's series HY–IG was already over 250 two weeks ago (255, Nov 6) before last week's dip.
6. **The consumer.** Discretionary and the calendar: "the consumer is the one part of the data that held" (control +0.6%, HD and LOW comps beat). Same pages: both housing retailers guided margin lower, Nike guided sales down through fiscal 2028, pending home sales -4.7%, and "a VIX of 36 closes wallets as well as positions."

### C. Counts, bases and dates the pages differ on

- **When the probe was reported.** Tech, financials and discretionary: Reuters, Friday. Semis and the calendar: the Wall Street Journal on Tuesday evening (a civil probe of disclosures, including Asian sales reporting), with Friday's headlines adding "accounting practices." The semis version explains Wednesday's -2.9% on a beat; the tech version does not. No page read either article first-hand; **neither the SEC nor NVIDIA has confirmed it.**
- **AMD's -7.7% Thursday.** Tech: "cause not sourced." Semis: Hunterbrook's short report.
- **December hike odds.** ~95% (AP, semis and calendar), 96% to 99.6% (Grid A, secondary). facts.json: ~95–96%.
- **Home Depot's quarter.** Discretionary: $3.86 "vs $3.74", a beat. Earnings page: $3.86 vs $3.84–3.86, in line, "missed the whisper, mixed guidance."
- **Target.** Staples and yfinance: $2.65 vs ~$2.07 (+27%). Earnings Whispers' basis: about $2.15, a 0.9% miss of the whisper.
- **Walmart and TJX.** Staples and discretionary: "not re-sourced." The earnings page has both: WMT $0.65 vs $0.64, raised; TJX $1.34, in line, +8.05% on the day.
- **Natural gas.** Materials and utilities: +17% on NG=F, "probably a roll." Energy: +5–7% on the same contract.
- **Brent.** Tech: $89.87 (the February contract). Semis and calendar: $92.57 (January).
- **SPY's 200-day.** Discretionary: $730.29. Canary and calendar: $732.76.
- **XLRE's 50-day.** Real estate: $42.54 (8 cents under). Canary: $42.58 (12 cents under). Below either way.
- **NVDA's next report.** Feb 17 (Finviz, semis), Feb 24 (yfinance), Feb 16 (Earnings Whispers).

---

## 8. MACRO CALENDAR IMPACT — A Hike Into a Correction, and One Real Day Next Week

**What this week's data did to the posture.** It brought the growth scare back and left the hike in place. The calendar's regime line: "sticky inflation, a December hike priced, and a financial-conditions shock that is now large." Triggers hit: **Empire under 10, import prices over +0.5%, minutes lock December, Philly prices paid over 50.** Not hit: retail sales under -0.1% (they rose 0.2%, control +0.6%), claims over 215K (203K), housing starts under 1.15M (1.309M, though permits fell 7.4%). The 20-year auction cleared at 5.459% and the 10-year TIPS at 2.903%. GDPNow slipped to 3.2%. **Flags: two up for a third week, and the mix flipped again.** VIX over 22 is raised (35.89); CPI over 0.3% is carried; **the 10-year over 5.00% cleared Friday** after six closes above it, "the weakest kind of clear, a flight to quality one session old." Oil, payrolls and DXY flags stay cleared or resolved. One bias to acknowledge on Monday: **five straight regional-survey misses, "consensus may be too optimistic."**

**How the Council's posture moved.** Toward cash, without selling the lows. Canary's verdict went from HIGH CAUTION to **ELEVATED** with two of four strict criteria met (VIX over 20 all five days; HY–IG over 250 for three prints) and issue #225. Every sector desk but staples, utilities and real estate filed a price trigger (#214 to #221). The calendar's cash note: new cash to bills at 4.12–4.16%; hedges to full size; no duration until a second weekly close under 5.00% or core PCE at +0.2% or less; no new gross equity exposure while VIX closes over 30; cyclicals and manufacturing-linked risk down a notch; housing-linked risk stays reduced; staples stay.

**Next week is a holiday week with one real day** (calendar Gauntlet; earnings page):
- **Mon Nov 23** — Chicago Fed National Activity (prior +0.07; under **-0.35** says the regional weakness is national). **2-year auction** 1:00 PM (prior 4.708%). Friday's HY–IG print posts. HPE after the close. Montana's reconsideration window on the Black Hills merger closes. First question: does VIX close under 30.
- **Tue Nov 24** — Conference Board confidence (cons 92; under **88** says the selloff reached households). Richmond Fed (cons 2; any miss is a sixth in a row). 5-year auction. ADI, Medtronic, Best Buy before the open; **Dell** after.
- **Wed Nov 25** — **Core PCE** (cons +0.3%; **≥ +0.4%** brings 50 bp talk and the 10-year back over 5.00%; **≤ +0.2%** is a cool core against three hot CPI cores). Q3 GDP second estimate (cons 3.5%; under 3.0% is a hard-data scare). Durables (ex-transport under 0.0% says capex is rolling over with the AI trade). **Claims** (cons 200K; over 215K). 7-year auction. Beige Book. **Deere** at 6:20 AM.
- **Thu Nov 26** — Thanksgiving, closed. **Fri Nov 27** — advance goods trade; stocks close 1:00 PM; Black Friday. VIX still over 30 on a half-day close carries the flag into payrolls week "at crisis size."
- **After it:** Bessent's ten days (~Nov 27–30), OPEC+ Nov 29, Cycle-3 drug prices by Nov 30, ISM Dec 1, CRM Dec 2, **payrolls Dec 4, FOMC Dec 8–9 (with Broadcom the same day), CPI Dec 10.**

**The posture into Monday.** Defensive and still. Bills over 4.1%, hedges at full size, three funds held at half size on tight stops, a list of names that got cheaper and no trigger to buy them. Ophelia's sign-off is the summary: "nobody sells into a thirty-six VIX. Wednesday morning is the whole week."

---

*Last updated by Saturday Research Crew: 2026-11-21 (Synthesis Agent, single-agent sequential run, on schedule, Saturday ~20:29 ET; STEP 0a input guard passed 5 of 5 at first look, no wait; all market data as of Fri 2026-11-20 closes)*
*Next update: Every Saturday 8:26 PM ET*
*Data sources: macro/facts.json (canonical macro, generated 2026-11-21), data/market_state.json (as_of 2026-11-20), the fifteen wikis in wiki/, portfolio/current.yaml, a Yahoo pull of the Council book's five names for the provisional mark*
