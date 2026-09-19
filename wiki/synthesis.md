# Weekly Council Synthesis — Week Ending Friday, September 18, 2026

> ⚠️ **DATA FRESHNESS — TRUTH LAYER: WIKIS CLEAN, facts.json REPAIRED, BUT THE BOARD DISAGREES ABOUT THE PRICE OF OIL**
>
> - `macro/facts.json` generated **2026-09-19**. It is **0 days old and FRESH**, and it is **repaired**. DXY is now a live Yahoo series (**100.22**, `DX-Y.NYB`), the 2Y is refreshed from FRED (**4.67%**, Thu 9/17), and credit OAS is live from FRED. The three Truth Layer defects the last two syntheses flagged (issues #92 and #103: a 59-day-stale DXY, a 16-day-stale 2Y, and a curve derived from both) are **fixed at the source**.
> - `data/market_state.json` `as_of` **2026-09-18**. The index and vol blocks are current and are used for the README Index Check. **Its `policy` block is stale and wrong:** it still reads fed funds **3.50–3.75 / Hold** as of **2026-07-29**, its regime string says **"policy-hold"**, its rates block carries 2Y **4.4** and a **60 bp** curve, and it carries WTI **95.47**. Read it for index levels and VIX only (see Section 7).
> - **All 15 wikis are FRESH. Zero stale, the second clean sweep in a row.** Nine carry a **2026-09-19** stamp (communication-services, materials, energy, utilities, consumer-staples, real-estate, consumer-discretionary, canary-watch, earnings-surveillance). Six carry **2026-09-18** (tech, semiconductors, financials, industrials, healthcare, economic-calendar). **The Monday Watchlist carries no staleness caveat.**
> - **Schedule note, not a failure:** this run fired at **2026-09-19T14:48-04:00**, about five and a half hours before its 8:26 PM ET slot. Every upstream job had already logged END in `logs/cron.log`, with Canary Watch finishing last at 14:45 ET, so the dependency order held.
>
> **This week's problem is a single number that splits the Council's story in half: WTI crude.**
>
> | Source | WTI Fri 9/18 | W/W | Story built on it |
> |---|---|---|---|
> | **`macro/facts.json` (canonical)** | **$100.30** | **+0.25%** | — |
> | canary-watch, energy, materials, utilities, consumer-staples, consumer-discretionary, real-estate, communication-services | $100.30 | +0.25% | "Siege plateau." Aramco cancelled October European allocations; the Oil > $100 RED trigger held for a second week |
> | tech, financials, industrials, healthcare, semiconductors, economic-calendar, `market_state.json` | **$95.47** | **-4.6%** | "Oil broke." Disinflation relief carried tech and healthcare; the calendar marked the Oil > $100 flag **RESOLVED** |
>
> This synthesis re-pulled Yahoo on Saturday to find the source of the gap. **`CL=F` and the October contract (`CLV26`) both settle $100.30 on Friday. November (`CLX26`) settles $96.08. No contract prints $95.47.** The $95.47 figure comes from the Friday **22:40 ET** data-feed snapshot (`data/weekly/2026-09-18.json`, fetched `2026-09-19T02:40Z`), which recorded a bar Yahoo has since revised. Grid A's supporting claim, "Brent -5.7% to $98.87 Thursday", also fails to reproduce: Yahoo's `BZ=F` shows **$104.82** Thursday and **$103.87** Friday. **facts.json wins: WTI is $100.30.** That means the economic calendar's flag count is really **three, not two**, and the "oil broke" pillar under the tech, healthcare and industrials theses rests on a number that does not reproduce. **A GitHub issue has been opened.**

---

## 1. CECIL'S SYNTHESIS — Fundamentalist Lens

The hike made the arithmetic worse everywhere the Council holds income, and the negative yield spreads are now the widest of the cycle on all three dividend sectors at once. **Utilities' 2.83% SEC yield sits ~217 bps under a 4.998% ten-year. Staples' ~2.59% sits ~241 bps under. Real estate's ~3.19% sits ~181 bps under.** None of the three dividend ETFs clears the risk-free rate, and the dots say the discount rate is not finished rising. The individual names that still clear it are the spreads that matter this week, and every one of them sold off anyway. **VZ at 5.88%** has a cushion of about 90 bps, down from about 140 a week ago, and fell -4.98%. **O at 5.68%**, 68 honest basis points over the ten-year, fell -4.77% to RSI 10.0. **CCI at 5.76%** made no new low. **MO at ~6.4%** was staples' best major (+2.39%). **GIS at ~6.7%** reports Wednesday. **AVA at 5.43%** closed at its 52-week low. **T at 4.37% is now below the ten-year** and needs its growth story to justify it. EIX's 6.35% is still a litigation coupon, not income.

**The value shelf got longer and cheaper, and the desks bought almost nothing.** Cecil's list across the book: **GOOGL at ~17.5x** with the divestiture tail removed by a benign Brinkema opinion ("the cleanest megacap value in the sector"); **EOG at 11.2x**; **BAC at 8.4x** Street 2026 earnings with a 19% gap to target, and **GS at ~11x** with 21%; **PEP at 17.5x yielding 4.4%** at a fresh 52-week low; **CMCSA at 7.3x yielding 5.8%**; **LOW at 16.4x**; **EXC at 15.5x** at a 52-week low; **FCX at 17.2x forward** with copper rising into a dollar rally; **PPG at 15.1x**; **SPG at 14.4x** with a 4.35% yield (green on the week); **NFLX at ~18.8x forward**, a buy-the-downgrade candidate after Wells Fargo cut it to Underweight; and **GILD at ~14x forward**.

**The traps share a rhyme again: cheap is not a catalyst.** **CHTR at ~3.3x** is priced for terminal decline, and the late-October subscriber print grades that price. **KMB at 19.4x yielding 5.2%** stays a balance-sheet question tied to the ~$40B Kenvue deal. **BA** fell -5.82% with no headline and the weakest balance sheet in industrials; Cecil will "watch, not catch." **CVS -6.15% on no news** could be someone knowing something about medical-cost trends.

**Where the Street is harvested:** **AAPL at $336.13 still sits above its $327.84 mean target.** **MPC, VLO and PSX close 14.8%, 16.3% and 8.4% above** targets raised again this week, with MPC at RSI 90. **GPRK trades above its $10.85 target.** TRV is above its target again. When analysts are chasing vertically, the easy money has been made.

**The one earnings stream the market paid a defensible multiple for is physical scarcity, and it showed up with receipts in four sectors.** Micron guided ~$50B revenue at an 86% gross margin, with HBM4 ramping twice as fast as HBM3. Intel's CEO said it can meet only about half of customer CPU demand. Apple raised the iPhone 18 Pro price by $100 on memory costs. The 3-2-1 crack held above $60 behind cancelled Aramco allocation letters. **Generac won a $2.4B Amazon backup-power contract (+30%).** Shortage economics are real earnings. Everything that merely yields or merely carries a multiple got repriced.

**Cecil's single new conviction is in credit, not equity.** With live FRED data for the first time since July, **HY OAS is 270 bps, IG 78 bps and HY–IG 192 bps**, and IG *tightened* through a hike, a 5% ten-year and a BOJ hike. **LQD rose +0.36% to $104.70.** "Quality credit at these yields is the most attractive margin of safety this board has shown all year." His equity buy lists are written and conditional: PPG then FCX, both only after XLB reclaims $50.17; BLK if XLF's 200D holds; PEP only after GIS prints. The tech desk holds **30% cash**.

---

## 2. MARKY'S SYNTHESIS — Technician Lens

**Four sector ETFs lost their 200-day moving average on a weekly close in the same week, and three of them did it by less than a quarter.** **XLI $169.75 vs $171.14**, which Marky's rulebook says converts a correction into a break, and he is flat the index. **XLB $49.99 vs $50.17**, eighteen cents, the first weekly close below the 200D this cycle. **XLP $82.80 vs $82.97**, seventeen cents, the first since the February breakout. **XLRE $42.53 vs $42.78**, twenty-five cents, ending the average's perfect 2026 record. **The count of sectors above their 200D fell from nine to five in a single week.** Only four of twelve sector ETFs sit above their 50D: XLK, SMH, XLE and XLV.

**All four breaks came at the lows, on hike-week flow, at oversold RSIs**, which is the highest false-break risk there is. XLB printed **RSI 25.5** (its most oversold of 2026), XLRE **25.6**, XLP **30.5**, XLI **34.4**. That is why the reclaim lines are the whole map this week: **$50.17, $42.78, $82.97, $171.14.** A fast reclaim marks the break as hike-week noise; a second weekly close below confirms it.

**The rest of the damage was distribution, not panic.** **XLU closed at a 52-week closing low of $41.10**, through its entire $41.15–$41.31 support band, on the correction's heaviest Friday volume (22.3M). **XLF fell all five sessions** ($57.03 → $55.86), lost its 50D ($57.18) on hike day and closed on the week's low with RSI 37. **XLC's Monday close above its 200D ($115.07) was a bull trap**: four straight lower closes followed, and the 50D ($111.19) went on Friday's heaviest volume. **XLY printed RSI 28.5**, oversold at the ETF level for the first time in a five-week losing streak, and its FOMC-day low stopped **22 cents above the $109.41 gap support**.

**Two V-reversals in the growth complex.** **SMH gapped from $568.53 to a $541.50 close Monday** (SOX -5.9%) on the Amodei essay, then reclaimed its 50D ($564.78) Thursday and Friday to close at **$573.00**. It faded from a **$580.81** intraday high, which is still supply. **XLK held its 50D ($183.12) by 62 cents on Tuesday**, the day the 10Y first tagged 5.00%, which Marky calls "the tell of the week." **XLE tested its $63.46 breakout line to the penny on Thursday and held**, but RSI is in its third week of bearish divergence and both heavy-volume days were red. **XLV reclaimed its 50D ($166.75) on Monday** and voided last week's trap call.

**The spring shelf and the redlines are both more extreme than last week.** Springs: **JBSS 7.5, SAFE 9.2, O 10.0, SBUX 10.8, PEP 12.1, BKNG 12.7, GIS 13.4, CMCSA 17.1, LIN 17.3, MGEE 17.3, DTE 22.2.** Redlines: **MPC 90.0, VLO 86.7, PSX 83.0, the 10Y's own RSI at 78.3, META 77.9, SDGR 77.**

**The correlations are shedding the last diversifiers.** **XLE's inverse collapsed from -0.426 to -0.095** as crude round-tripped. **XLC decoupled from 0.522 to 0.224. XLU re-coupled from 0.070 to 0.198** as a pure rate-beta trade. At the top, **XLK (0.702) and XLY (0.696) both rose**. **XLP at 0.105 is the only sector left that could flip negative.** Breadth confirms the narrowing: **RSP -1.20% vs SPY -0.34%** on the week and -3.45 points on the month, with **seven of twelve sectors in outflow**, the widest cluster this cycle.

**The vol market treated the hike as a known event.** VIX spiked to **18.94 intraday Wednesday**, then fell to **14.81 (-6.5% W/W)** with contango intact all week (VIX/VIX3M peaked at 0.90). VVIX went from 99.71 to 87.38. Marky's warning is the whole regime in one line: "the options market is calm while the bond market is at 5.00%."

---

## 3. OPHELIA'S SYNTHESIS — Macro Lens

**The regime changed on Wednesday at 2:00 PM.** The FOMC hiked **+25 bps to 3.75–4.00%, 12-0**. It was the first hike since July 2023 and the first of the Warsh chairmanship. The statement said "inflation remains elevated," and Chair Warsh framed the move as a "timelier return to 2%" with no dot and no forward guidance. The dots were the hawkish part: **16 of 18 participants see another 2026 hike**, the end-2026 median is **4.1%**, the end-2027 median rose to **4.1% from 3.6%**, and 2026 core PCE rose to 3.4%. **The 10Y closed at 5.006% that day, its first close above 5.00% since July 2007.** It ended the week at **4.998%**, 0.2 bps under the line. The rest of the curve per facts.json: **2Y 4.67%** (FRED, Thursday), **5Y 4.856%**, **3M 3.978%**, **10Y–2Y +33 bps**, **10Y–3M +102 bps**. The curve is bear-flattening, and the front end and belly are doing the hiking. **The BOJ hiked to 1.25% (7-2) on Friday and the yen fell anyway.** USD/JPY rose to **156.129**, reversing a three-week carry unwind, EUR/USD fell to **1.149**, and **DXY rose +1.11% to 100.22**, its first weekly close above 100 in eight weeks. Every desk now reads a hiking-cycle regime, not an insurance hike.

**The rotation story is that there is almost nowhere left to rotate.** Only three sectors rose (**XLV +1.83%, XLK +1.03%, SMH +0.79%**), and seven of twelve are in outflow. The real rotation happened *inside* sectors, along one line: **physical scarcity against duration.** Memory and CPU names (AMD +8.46%, INTC +5.50%, MU +4.16%), refiners on contractual molecule scarcity (MPC +7.31%), backup power (Generac +30%, ETN +3.74% Friday), and copper (+2.25% into a rising dollar) got paid. Everything priced off a discount rate got sold, including assets sold as scarcity: **CEG -10.55%** ("the scarcity premium itself is duration"), EQIX and DLR on duration math with no leasing news, and AMT, whose one-week 200D reclaim failed.

**Three macro cross-currents that the Council cannot yet resolve:**

- **The consumer is three people.** UMich sits at 47.8, near a record low. **August retail sales beat at +1.2%** (control +1.4%, the strongest since September 2024). Housing is cracking: **Lennar's orders fell 9%** and its CEO said the environment "has deteriorated," **PMMS jumped +19 bps to 6.95%**, NAHB fell to 32, and permits fell to 1.394M. PLAY's -244% miss and games revenue down ~9% say experience spending is rolling first.
- **The goods economy split.** Philly Fed came in at 37.8 (a beat, with prices paid rising), but Empire printed 7.6 against 14.0, industrial production was flat, and the LEI fell -0.1%. Claims fell to 196K.
- **Bonds, equities and credit are pricing three different worlds.** Bonds price restrictive-for-longer. Equities price Goldilocks, with VIX at 14.81. Credit prices nothing at all: HY OAS 270, IG 78 and tightening. Meanwhile bank stocks fell 3.7–4% Thursday on "credit-cycle anxiety" that the credit market itself does not share.

**The oil contradiction runs through all of it.** Half the board believes oil broke and cut the fuel line to the next hike; the other half, and the canonical file, say WTI held **$100.30** while Aramco cancelled all October European allocations, Petroline lost three pumping stations, and Saudi output printed **6.24 mb/d, the lowest since 1990.** Ophelia's read is the energy desk's: every escalation now gets an engineering answer within days, and each answer is thinner than the last.

**What the Economic Calendar revealed:** the 10Y crisis line was crossed on a daily close, retail sales and the dollar flags resolved, and October hike odds rose to **~57–58%** from 42%. The calendar counts two flags, down from five. On canonical oil at $100.30, **the Oil > $100 flag is still raised, so the true count is three.** Fewer flags than last week, but the ones left are rates, inflation and the oil that feeds both.

---

## 4. CONSENSUS SYNTHESIS

**Where all three agree.**

**The 10Y at 5.00% is the regime, and the Fed has pre-announced more.** All twelve sector desks and all three dashboards now describe a hiking cycle, not an insurance hike. Ophelia redrew her lines (5.05% confirmation on the calendar, 5.10% break on the tech desk, 4.90% relief on real estate, 4.80% relief on utilities), but nobody is calling the move over.

**Physical scarcity beats duration, inside every sector, in the same week.** This was the organizing rule in semis (MU/AMD/INTC over the capex-sentiment names), tech (memory over software and networking), energy (refiners on molecules over SLB on activity), industrials (Generac/ETN over rails and aerospace), materials (copper/FCX/CLF over VMC/MLM), utilities (and here scarcity lost to duration: CEG -10.55%), real estate (PSA/SPG value over towers and data centers) and healthcare (LLY and the medtech springs over managed care).

**No new duration, cash elevated, and hedges are cheap.** Canary Watch holds **25–30% cash**, Cecil's tech desk **30%**, and the calendar says "keep the reduced-exposure posture." With VIX at 14.81, every desk that mentions insurance calls it inexpensive.

**Where they disagree.**

**Oil: relief, siege, or recession?** Tech and healthcare read the week as "oil broke," a disinflation gift that let long-duration growth rally through a 5% ten-year. Financials read the same move as **demand destruction**, pointing to energy and banks falling together on Thursday as an early-cycle recession signature. Energy, materials and utilities say oil did not fall at all ($100.30) and the conflict graduated to supply action. That is three incompatible readings of one macro factor, and the canonical price supports only the third.

**Credit.** Financials priced a credit cycle: GS -8.47%, BAC -7.91%, five straight down days. Canary Watch's live OAS says credit is contained and IG tightened. The SMID regional banks refused to follow the money centers down.

**Whether defensives defend.** Healthcare calls itself "the fortress that absorbed the hike" (XLV +1.83%). Staples, utilities and real estate all broke their 200-day or their support band in the same week.

**The single biggest risk is 10Y acceptance above 5.00%, delivered by supply rather than data.** **$192B of 2-, 5- and 7-year notes** land Tuesday through Thursday, into a 10Y at 4.998%. The calendar's trigger is a 5Y or 7Y tail of 2 bps or more with a 10Y close above 5.05%. That would land on a board where **four sectors just lost the 200D by 17–25 cents**, index strength rests on two sectors (XLK and SMH), the diversifier pool is nearly empty, and **MU on September 30 is the only thing holding up the leadership trade.** If tech cracks, there is no rotation destination except cash.

**The single biggest opportunity is the same auction week, read the other way.** The springs have never been this compressed on this board (O at RSI 10, SAFE 9.2, SBUX 10.8, PEP 12.1, BKNG 12.7), and four marginal 200D breaks at oversold RSIs are the classic false-break setup. A strong auction week, or a 10Y weekly close back under **4.90%**, and the reclaim lines ($50.17, $42.78, $82.97, $171.14) become the entries. Real estate, utilities and discretionary each describe that rally with the same word: violent.

---

## 5. MONDAY WATCHLIST

> **No staleness caveat this week.** Every level below comes from a wiki stamped 2026-09-18 or 2026-09-19, against Friday 2026-09-18 closes. Macro levels are facts.json values.
>
> **Oil levels use the canonical $100.30.** Levels that tech, healthcare and industrials wrote around a "$95.47 oil break" are flagged below.

| Ticker / ETF | Sector | Trigger / Level | Stop / Invalidation | Rationale |
|---|---|---|---|---|
| **10Y Treasury** | Macro | 4.998%. **5.05% weekly close = crisis-line break confirmed**; 5.10% is the tech desk's break level | Weekly close **< 4.90%** = first relief signal (< 4.80% for utilities) | First close above 5.00% on 9/16 (5.006%). The yield's own RSI is 78.3, more overbought than the sectors are oversold |
| **2Y / 5Y / 7Y auctions** | Macro | Tue $78B 2Y · Wed $70B 5Y · Thu $44B 7Y, all 1:00 PM ET | A 5Y or 7Y **tail ≥ 2 bps** with the 10Y > 5.05% | Can push the 10Y through the line without any macro print |
| **XLK** | Tech | $189.60. Through **$190–$191.75** (double top) opens the **$198.73** June high | Close under the 50D **$183.12** → $178.82–$180.00 | Held the 50D by 62 cents on Tuesday. Part of the desk's case rests on a "$95.47 oil break" that does not reproduce |
| **SMH** | Semis | $573.00. Close above **$580.81** → high-$590s | Lose **$560.28–$560.61** → retest **$537.73** (Monday's AI-slowdown low); 200D $487.31 | V-reversal. The 50D ($564.78) is reclaimed and is now first support |
| **MU** | Semis | **FQ4 Wed Sep 30 AMC** (confirmed by Micron IR). Consensus **$31.35** ($28.04–$37.44), revenue **$50.97B** | Any sign customers changed ordering on the "pace the frontier" essay | $1,015.80. Not Sep 22, whatever the tech desk says (Section 7). Size it like an event: ±9.1% average reaction |
| **AMD / INTC** | Semis | AMD $559.82, 4.3% under its **$584.73** high, RSI 65.4. INTC +5.5% on SK Hynix–Intel Ohio memory talks | — | Scarcity leaders. INTC's CEO is now the sector's voice on supply |
| **AMAT / LRCX** | Semis | Friday's +6.51% / +6.98% was a bounce. Trend change needs the 50Ds: **$501.12 / $307.38** | Failure back under Monday's lows ($415.38 / $269.23) | Money rotating into oversold capex names; the small caps did not join |
| **XLC / GOOGL** | Comm Svcs | XLC $110.81. Fast reclaim of the 50D **$111.19** repairs it; GOOGL above its 50D (~$345.58) is the only add-on-strength | XLC weekly close **< $110.00** → **$105.38** | Monday's 200D reclaim was a bull trap. Google's final judgment is due Oct 2. CCOI's lead-plaintiff deadline is Monday 9/21 |
| **VZ / T** | Comm Svcs | VZ 5.88% vs a 4.998% 10Y is about a 90 bps cushion; T's 4.37% is now below it | 10Y acceptance above 5.00% turns the cushion negative | The telecom yield bid only works while the 10Y stays under the yield |
| **XLF** | Financials | $55.86. **$55.00–$55.44** is the shelf; a reclaim of the 50D **$57.18** is required before any rally counts | Close below $55.00 → 200D **$53.45**, which is Marky's buy zone, not a short | Five down days. Own the float, not the loan book: CB was green, TRV above target, V and MA near flat |
| **GS / BAC** | Financials | GS ~11x (+21% to target), BAC 8.4x (+19%) | RSI ~33 / ~30. Falling knives until the mid-October Q3 prints | Cecil's "best entry of the year IF the credit fear is phantom." Live credit spreads say it may be |
| **XLI / ETN** | Industrials | XLI $169.75. Weekly close back above **$171–$172** = bear trap | Below **$167.49** → low $160s | 200D lost on a weekly close. ETN above **$415** is the only long Marky would press (Generac read-through) |
| **BA** | Industrials | $198.20, $1 above its **$197.00** three-month support | Break of $197 | -5.82% with no headline. Cecil and Marky both avoid |
| **XLB / FCX / CLF** | Materials | XLB reclaim of **$50.17** kills the break. FCX must hold **$71**; copper must hold **$6.60** | XLB failure at $50.17 → **$47.00** target; DXY weekly close > **101** snaps the commodity-long restriction back on | Copper $6.615 (+2.25%) rose into a dollar rally. CLF (RSI 61) is the only major above 50 |
| **VMC / MLM** | Materials | Avoid. VMC $240.83 in fresh 52-week-low territory | No map line until the low $230s | The hike's cleanest victims: long-duration, capex-financed models |
| **XLE** | Energy | $64.31. Weekly close above **$66.17** opens **$70** | Weekly close below **$63.46** = failed breakout #2; 50D **$61.18** | The breakout line held to the penny on Thursday. RSI shows a three-week bearish divergence |
| **WTI crude** | Energy / Macro | **$100.30** (facts.json). A weekly close above **$105.83** (Tuesday's spike close) changes the math | UNGA-week diplomacy that verifies a corridor → low $90s | The price is itself disputed (Section 7). OPEC+ meets Oct 4 |
| **MPC / VLO / PSX** | Energy | Own the crack (> $60), don't chase: RSI **90.0 / 86.7 / 83.0**, 8–16% above raised targets | One crack-spread downtick | Leadership this vertical resolves through time or price |
| **SLB / EOG** | Energy | SLB $51.12, RSI 30.3, above its 200D ($49.89). EOG at 11.2x is the cheapest quality barrel | SLB loses its 200D; the Vostok Oil exposé becomes sanctions action | "Looks stupid to open, expensive to have skipped" (Cecil) |
| **XLV / LLY** | Healthcare | $168.39. The 50D **$166.75** is the floor; add through **$169.71**; target the **$176.60** ATH | Close under $164–$165 | Trap voided. LLY at ATHs (~$1.03T): hold, don't add. The desk's "oil broke" macro read is disputed |
| **XBI** | Healthcare | A weekly close above **$158–$160** restores the truce | Lost its 50D ($157.57) again on Friday | IOVA +19% and SDGR +52.6%: dispersion replaced de-grossing |
| **XLU / CEG / VST** | Utilities | Bearish below **$41.31**. The floor hunt is **$41.00**, then **$40.00** | Relief needs a weekly close back inside the $41.15–$41.31 band, or 10Y < 4.80% | 52-week closing low. CEG -10.55% and VST both lost their 50Ds |
| **XLP** | Staples | Reclaim **$82.97** (200D) = false break | Any daily close under **$82.00** → **$81.00** | **GIS Wed Sep 23 BMO** (cons $0.72) and **COST Thu Sep 24 AMC** (cons $6.53, RSI 21, ~45x): the double gate |
| **PEP / MO** | Staples | PEP $129.75, 17.5x, 4.4%, RSI 12.1 at a 52-week low on no news. MO is the only trend intact | PEP prints Oct 8 | The FX tailwind flipped: DXY +1.11% hit the multinationals |
| **XLRE / PSA / O** | Real Estate | Reclaim **$42.78** = head-fake. PSA must hold its 200D **$295.23** | A second weekly close below, or any close < **$42.50** → **$40.00** | O at RSI 10.0 yields 5.68%. Springs, not signals |
| **XLY** | Cons. Disc. | $111.03, RSI 28.5. Hold **$109.41** → oversold rip toward **$113–$114** | Weekly close below $109.41 → **$105.45–$105.66** | NKE Thu Oct 1 AMC (cons $0.45) at a fresh 52-week low. **DRI Thu Sep 24 BMO** is the PLAY read-across |
| **VIX** | Macro (vol) | 14.81. A close above **16.50** is the tell; **20** is the regime question | — | Cheap insurance into auction week with the 10Y at the line |
| **DXY / USD-JPY** | Macro (FX) | DXY 100.22; **101** is materials' trip wire, **102** Canary's yellow. USD/JPY 156.129; watch **158–160** and MoF language | — | The carry trade is rebuilding under a split BOJ |
| **HY OAS** | Credit | 270 bps live. **300 bps** is the first real credit signal of the cycle | — | Watch it on the next hike. Not moving yet |

---

## 6. CROSS-SECTOR CONNECTIONS — The Hidden Wires

**Wire 1: the Rate-Sensitivity Chain moved from the long end to the front end, and that makes it harder to fix.** Real estate caught the composition change. The **30Y eased to 5.331%** after the FOMC, which is the Treasury buybacks finally showing up at the long end, while the **2Y jumped +13.4 bps on hike day**. The damage now comes from the Fed's own dots, and "dots don't get bought back." The same front-end repricing did at least nine jobs at once. It broke four 200-day lines (XLI, XLB, XLP, XLRE). It put XLU at a 52-week low and repriced CEG's scarcity premium as duration (-10.55%). It squeezed VZ's cushion to about 90 bps. It liquidated the REIT small caps (GTY -8.15%, SAFE -6.34%, on no news). It de-rated SHAK -13.78% on no news. It flattened the curve under the banks. It widened staples' carry gap to -241 bps. And it put **PMMS at 6.95%**, freezing HD, LOW and Lennar's order book. **One number is setting the internal dispersion of at least eight sectors**, and the correlation matrix proves it: XLU re-coupled to SPY as rate beta in the same week XLE decoupled.

**Wire 2: the AI supply chain moved from GPUs to memory, CPUs and electricity.** The chain now runs like this. **Monday's Amodei essay ("We Must Pace the Frontier")** knocked SOX -5.9%, but no hyperscaler cut a capex line. **Intel's CEO said it can meet about half of CPU demand**, and SK Hynix–Intel talks on U.S. memory production at the idle Ohio fab surfaced. Nebius raised GPU-rental prices. **Apple put a $100 memory surcharge on the iPhone 18 Pro**, so DRAM cost has reached a consumer list price. That lifted **MU, AMD and INTC** in semis and tech. In industrials, it lit **Generac's +30%** on a **$2.4B Amazon backup-power deal**, lifted **ETN +3.74% Friday**, and drew **Crusoe's $3.9B raise** for factory-built data centers. In materials, **copper rose all five sessions into a dollar rally** on EV and data-center demand. In healthcare, it produced **Novo Nordisk adopting Anthropic's Claude across R&D** and **SDGR +52.6%**. **But the wire stopped paying at the landlords:** EQIX, DLR, CEG and VST all fell. The market pays for the equipment that relieves the shortage, not for the contracted real estate that houses it.

**Wire 3: the Geopolitical Energy Loop became a supply action, and a data dispute.** **Petroline lost three pumping stations. Aramco cancelled all October crude allocations to European buyers. Saudi August output was 6.24 mb/d, the lowest since 1990. Hormuz transits fell to four vessels Thursday.** From there: a 3-2-1 crack above $60 (peak $64.58) pushed **MPC, VLO and PSX to record closes**, while capex-deferral math at 5% money took **SLB -8.81%**. Materials' coatings complex *stabilized* at the $100 plateau. Discretionary's **BKNG (-3.46%, RSI 12.7)** kept paying the fuel tax, as did staples' logistics names (SYY -5.0%). Utilities carried "$100 oil" as its stagflation leg. Energy's inverse correlation to SPY collapsed. **And the loop split the Council itself**: six sources recorded a -4.6% oil break that the canonical file does not show, so half the board priced relief that the other half priced as siege.

**Wire 4: the Consumer Stress Triangle has a hard-data corner that refuses to crack.** **Sentiment:** UMich 47.8. **Spending:** retail sales +1.2%, claims 196K. **Housing:** Lennar's orders -9%, NAHB 32, PMMS 6.95%. **Experience spending:** PLAY -244%, games revenue down ~9%. The triangle priced itself across four sectors. **HD, LOW, MCD and NKE** printed 52-week lows in discretionary. **SHAK** fell -13.78%. **CVS** fell -6.15% in healthcare. **CMCSA and CHTR** fell -9.76% and -12.07% in comm services and discretionary. On the other side, **SPG's green week** in real estate and **MO's** in staples show the trade-down shopper. **Thursday Sep 24 adjudicates it:** DRI before the open says whether casual dining is going PLAY's way, and COST after the close says whether the value trade is catching the spending.

**Wire 5: the dollar wire, reconnected after eight silent weeks.** **DXY +1.11% to 100.22** hit five sectors through translation and one through a trading rule. Staples' multinationals bled (**PEP -4.82%, SYY -5.00%, EL -3.80%, MDLZ -2.55%**) while domestic MO rose. Healthcare flagged big-pharma translation drag for Q3. Industrials added an export tax on CAT and DE. Semis flagged TSM and ASML offshore revenue. Real estate blamed part of AMT's failed reclaim on it. **Materials put a hard 101 trip wire on its commodity-long restriction.** Then **USD/JPY at 156.129** after a split BOJ means the carry trade is rebuilding under a central bank that just showed its hand.

**Wire 6: the equity market priced a credit cycle that the credit market did not.** Thursday: **GS, USB, PNC, TFC and AXP fell 3.7–4% while OXY fell -6.5% and COP -6.2%**, the "energy and banks together" signature financials calls an early-cycle recession vote. Same week, per live FRED: **HY OAS 270 (+5), IG 78 (-2), EM 137, LQD +0.36%.** The SMID regionals (CUBI -1.61%, BANR -0.80%, HOPE +0.14%) held, and private equity's EverBank mark held. The equity selloff was about trading revenue (Moynihan's double-digit Q3 markets warning) and duration, not defaults. Financials' own wild card is where this wire could snap: UBS's chair warned about insurer-held private credit, and a mark-to-market event there with the curve flat at 5% is the tail nobody is pricing.

---

## 7. SECTOR CONTRADICTIONS — Where the Wikis Disagree

**Contradiction 1 (MOST SEVERE: a factual dispute about the week's key commodity price).** Six wikis (tech, financials, industrials, healthcare, semiconductors, economic-calendar) plus `market_state.json` report **WTI $95.47, -4.6% W/W**, with Friday "-6.3%" and Brent "-5.7% to $98.87 Thursday on Saudi East-West pipeline restart hopes." Eight wikis (canary-watch, energy, materials, utilities, consumer-staples, consumer-discretionary, real-estate, communication-services) and **facts.json** report **WTI $100.30, +0.25%**, with Brent $103.87. The synthesis re-pull found that **`CL=F` and `CLV26` settled at $100.30, `CLX26` at $96.08, and `BZ=F` at $104.82 Thursday and $103.87 Friday.** Nothing reproduces $95.47 or $98.87. The $95.47 comes from the data-feed snapshot taken Friday 22:40 ET (`data/weekly/2026-09-18.json`); the Brent figure comes from a newsletter source Grid A cited. **Resolution: $100.30 (facts.json).** Consequences: the economic calendar's **"Oil > $100 RESOLVED"** flag directly contradicts Canary Watch's **"Oil > $100 RED trigger held 2nd week"**; the "oil broke" pillar under the tech, healthcare and industrials theses is unsupported; and the weekly data file is append-only, so its $95.47 needs a restatement under `DATA_FEED.md` rules, not an edit. **Issue opened.**

**Contradiction 2 (genuine bull-versus-bear on the same macro factor).** Even setting the price aside, the same oil move is read three ways. **Tech and healthcare call it relief**: "the stagflation tail broke," "the disinflation channel reopened," the single biggest gift to long-duration healthcare. **Financials calls it recession**: "banks don't sell off on lower oil; they sell off when loan losses are coming." **Energy and materials call it a siege plateau**, with the transmission shifting from cost-push to demand destruction. This is the textbook case this section exists for.

**Contradiction 3 (Truth Layer: `market_state.json`'s policy block is pre-hike).** It reads fed funds **3.50–3.75, stance "Hold", as of 2026-07-29**, next gate "FOMC Sep 15–16," and regime **"risk-on / curve-positive / policy-hold."** Every wiki and facts.json report a **hike to 3.75–4.00%** on Sep 16. Its rates block (2Y **4.4**, curve **60 bps**) also disagrees with facts.json (**4.67%, 33 bps**). The README Index Check uses only its index and vol blocks, which are fine. Any downstream consumer of the regime string is reading a Fed that no longer exists.

**Contradiction 4 (the curve, still three values).** facts.json reports **+33 bps**, but that mixes Friday's 10Y (4.998%) with Thursday's FRED 2Y (4.67%). Canary Watch's own same-day Thursday figure is **+27 bps**. Tech, financials, industrials, healthcare and utilities report **~+26 bps** using a **4.74%** 2Y (Wednesday close / Barron's Friday 3 PM). `market_state.json` reports **60**. Per the rule, **33 bps is the number of record**. It is far better than last week's 78, but a same-day derivation would remove the remaining ~6 bps.

**Contradiction 5 (did the 10Y close the week at 5.00%?).** Tech, financials, industrials and healthcare write "the first weekly close AT the line." Semiconductors and the economic calendar write that it "narrowly did not." **facts.json: 4.998%.** The daily close above 5.00% (5.006%, Wednesday) is real. The *weekly* confirmation has not happened, which matters because Ophelia's own confirmation rule is a weekly close.

**Contradiction 6 (the dot plot).** facts.json and most wikis report **16 of 18** participants seeing another 2026 hike. Semiconductors and the economic calendar report **16 of 19**. Tech, financials, industrials and Canary Watch describe year-end dots as **"4.1–4.4%"**; materials, staples, discretionary and real estate give a **4.1% median**. **Resolution: 16 of 18 (facts.json); median 4.1%.**

**Contradiction 7 (hike odds, and a likely misread).** Grid A (financials, industrials, healthcare) writes **"~47% odds of one more by December,"** citing CME FedWatch at **47.1% (+25 bps) / 42.4% (+50 bps)**. Those are two points of a probability distribution, and together they imply **~89% odds of at least one more hike by December**. Grid B and the calendar report **October at ~57–58%**. Grid A's framing understates the market's hawkishness by roughly 40 points.

**Contradiction 8 (MU's print date, second week running).** Tech again lists **"Tue Sep 22"** and builds its bull and bear cases around it. Semiconductors (citing Micron IR) and Earnings Surveillance (consensus $31.35) list **Wed Sep 30 AMC**. **Resolution: September 30.** The last synthesis resolved this identical error, and it recurred.

**Contradiction 9 (did FedEx report?).** Industrials says FDX "reported Thursday Sep 17 AMC" with a "muted -0.73%" reaction, but gives no EPS or revenue. Earnings Surveillance says yfinance lists the next report as **Oct 28**, unconfirmed. **Unresolved. Treat the FDX print as unverified** until someone checks FedEx IR.

**Contradiction 10 (minor, but checkable).** **SPY's week** is -0.34% (Canary, calendar, semis, comm services; market_state -0.3%), -0.09% (Grid B, on a dividend-adjusted basis) and "~+0.2%" (healthcare). **Lennar's FY delivery guide** is 80–81K (financials, industrials) versus 82–83K (Earnings Surveillance). **GIS** is dated "Tuesday Sep 23" by staples, but September 23, 2026 is a **Wednesday** (Earnings Surveillance: Wed BMO). **Gold** is $4,424.90 in facts.json versus $4,415.90 in market_state; facts.json wins.

**Resolved since last week:** all fifteen wikis now name **Chair Warsh**, which closes the Warsh-versus-Powell item in #103. The DXY, 2Y and curve staleness from #92 and #103 is fixed in facts.json.

---

## 8. MACRO CALENDAR IMPACT — The Week That Changed the Regime, and the Supply Week That Tests It

**This week's data made the Fed's case for it.** Monday brought the AI-slowdown essay and no macro data. Tuesday: **Empire 7.6 against 14.0** and **NAHB 32 against 34**. Wednesday: **retail sales +1.2%** against ~+0.8–0.9% (control +1.4%, ex-autos +1.4%), then **industrial production flat against +0.3%**, then the **12-0 hike with hawkish dots** at 2:00 PM. Thursday: **claims 196K** (continuing 1.730M), **housing starts 1.275M with permits falling to 1.394M**, **Philly Fed 37.8 against 28.7** with prices paid rising, and pending home sales +0.3%. Friday: **the BOJ hiked to 1.25%** and the **LEI fell -0.1%**, its first decline since March. The pattern is what a working hiking cycle looks like early: demand-side data (consumer, labor) beat while rate-sensitive supply (housing, regional factories, production) cooled first. **The one-and-done thesis the market held into Wednesday did not survive the week.** October hike odds went from 42% to ~57–58%.

**The flag board.** The calendar resolved three flags (retail sales, DXY and oil) and counts two: **the 10Y crisis line, crossed on a daily close, and CPI MoM > 0.3%, carried.** On facts.json's WTI of $100.30, **Oil > $100 is still raised**, so the Council should be working from **three flags**. That is fewer than last week's five, but more concentrated, because all three set the discount rate.

**Next week has no red-rated release, and the risk is supply.**
- **Mon 9/21:** Chicago Fed National Activity Index (below -0.35 means hikes are biting broadly). CCOI and PRIM lead-plaintiff deadlines. UNGA week opens, with Trump meeting Gulf leaders and Iran's delegation in the building.
- **Tue 9/22:** Richmond Fed. **$78B 2-year auction** (a stop above 4.75% means the front end is pricing October as done). AZO before the open, KBH after the close (the first homebuilder with the 10Y above 5%).
- **Wed 9/23:** **S&P flash PMIs** (composite below 53 is the first dovish signal Ophelia would respect). **$70B 5-year auction.** GIS, PAYX and CTAS before the open.
- **Thu 9/24:** Claims (consensus 207K; under 200K for a second week makes October the base case) and new home sales (consensus 615K; below 580K confirms NAHB's 32). **$44B 7-year auction.** The reported **Xi Jinping White House visit**, which is export-control headline risk for semis. **DRI before the open, COST after the close.**
- **Fri 9/25:** **Durable goods** (consensus -0.3%; negative core capex orders would mean the AI scare reached real orders). **UMich final** (consensus 47.8; one-year inflation expectations at or above 4.8% means de-anchoring and locks in October).

**Then the stacked gate:** **Wed Sep 30** brings August PCE and the Q2 GDP third estimate at 8:30 AM, and **Micron after the close**. ISM follows Oct 1 (above 52 with the 10Y at 5% is industrials' bear-trap case), NFP Oct 2, OPEC+ Oct 4, CPI Oct 14, and the **FOMC Oct 27–28**. The Canada ban on motorcycles, dairy and alcohol takes effect Sep 29.

**The Council's posture:** defensive, undeployed, and hedged. **Cash stays at 25–30%.** No new duration. Deploy only into physical-scarcity earnings (memory, power equipment, refiners on a pullback). Keep regulated utilities, long-dated REITs and the 40x staples shelf underweight. Canary Watch holds its verdict at **CAUTION, escalating (rates-led)** for a fourth week, with breadth, rotation and policy now red on live data and credit green. The auctions will show whether 5.00% on the 10Y was a spike or a floor.

---

> *Synthesis compiled by the Saturday Research Crew — Synthesis Agent*
> *Timestamp: 2026-09-19T14:48:00-04:00 (Saturday 2026-09-19; ran ahead of the 8:26 PM ET slot after all upstream jobs had logged END)*
> *Data as of: Friday, September 18, 2026 closes — all 15 wikis + macro/facts.json (generated 2026-09-19) + data/market_state.json (as_of 2026-09-18)*
> *Wiki freshness: 15 of 15 fresh, 0 stale. Truth Layer: facts.json repaired (DXY, 2Y, credit live). Open defects: market_state.json policy/rates blocks pre-hike; WTI $95.47 in the weekly feed vs $100.30 canonical.*

*Last updated by Saturday Research Crew: 2026-09-19*
