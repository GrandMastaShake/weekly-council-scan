# Weekly Council Synthesis — Week Ending Friday, September 25, 2026

> ⚠️ **DATA FRESHNESS — TRUTH LAYER: ALL 15 WIKIS FRESH AND facts.json FRESH, BUT LAST WEEK'S OIL BASE STILL DISTORTS THE WEEKLY CHANGES, AND THE DATA FEED'S 2-YEAR IS 40 BP OFF**
>
> - `macro/facts.json` generated **2026-09-25**. It is **0 days old and FRESH**, regenerated from the same fetch as Canary Watch (commit e8cedef). DXY, the 2Y and credit are live, and no field is flagged stale.
> - `data/market_state.json` `as_of` **2026-09-25**. Its index and vol blocks are current and feed the README Index Check. **Its policy block is repaired** (3.75–4.00%, "Hike", regime "risk-on / curve-positive / policy-hike"), which closes that part of issue #110. **Its rates block is still wrong:** a 2Y of **4.47%** and a **71 bp** 2s10s, against facts.json's **4.87%** and **+31 bp** (Section 7).
> - **All 15 wikis are FRESH, every one stamped 2026-09-25.** That is the third clean sweep in a row, and **the Monday Watchlist carries no staleness caveat.**
> - **Schedule note, not a failure.** The whole crew ran by hand on Friday night, after the close: the data feed at 18:13 ET, semis and the economic calendar 18:19–18:31, Grids A/B/C 20:13–22:45, Earnings Surveillance 22:42–22:50, and Canary Watch plus facts.json 23:01–23:07, followed by a live breadth refresh. Every upstream job logged END before this job started at 23:30 ET. This job's first pass stopped at a usage limit after STEP 0 and all fifteen reads (END INCOMPLETE at 23:37 ET). This document comes from the resumed pass, which started at 07:16 ET Saturday. No commit touched a wiki between the two passes.
>
> **This week's Truth Layer problem is last week's oil dispute carried forward into every weekly change.** The *level* of oil is no longer in doubt: every source sits within 0.5% of $92.44. The *change* is in doubt:
>
> | Source | WTI Fri 9/25 | W/W | Base |
> |---|---|---|---|
> | **`macro/facts.json` + Canary Watch (canonical)** | **$92.44** | **-7.84%** | **$100.30**, last week's canonical close |
> | communication-services | $92.92 | "-$7.4" | $100.30 |
> | energy | $92.92 spot ("futures closed $92.44") | "-$7.38" **and** "-2.7%" in the same row | both |
> | tech, financials, industrials, healthcare, materials, utilities, consumer-staples, consumer-discretionary | $92.92 | -2.7% | Fair Value newsletter, i.e. off $95.47 |
> | semiconductors, economic-calendar, `market_state.json` | $92.44 | -3.2% | the feed's $95.47 bar |
>
> **Resolution: $92.44, -7.84% (facts.json).** Last week's synthesis showed that no contract reproduces $95.47 (issue #110). The restatement it asked for has not happened, so the bad base keeps producing a weekly change that is 4.6–5.1 points too small. A Saturday re-pull settled a smaller question too. The Grid A/B Friday closes for XLK ($196.79), XLV ($170.55), XLF ($54.81) and XLP ($82.12) were taken from same-day bars around 20:00 ET. The settled bars match facts.json exactly: **XLK $196.27, XLV $170.70, XLF $54.84, XLP $82.06.**

---

## 1. CECIL'S SYNTHESIS — Fundamentalist Lens

**Every dividend spread on the board widened to the worst reading in the data, and this was the week the fundamentalist started spending.** With the 10Y at **5.184%**, utilities' 2.83% SEC yield sits **235 bps** below the risk-free rate, staples' ~2.59% sits **259 bps** below, and real estate's ~3.19% sits **199 bps** below. The single-name spreads moved against their owners. **VZ's ~5.9% cushion is down to ~70 bps**, from about 90 a week ago. **T's ~4.4% is now ~78 bps under** the ten-year. **CCI's ~6.2%**, about 100 bps over and the widest carry the stock has ever printed as a pure tower company, made a new 52-week low anyway (-7.15%). **O's ~5.5%** (about 30 bps over) printed capitulation volume at RSI 17.4. **GIS's ~6.0%** lost 7.1% in the week it beat, and **UPS's 7.13%** is priced for a payout cut. The yields the market still paid for had pricing power behind them: **MO (~6.4%) -1.0%, PM green, PFE (6.2%) +3.6%.**

**The lesson of the week: the market stopped paying for yield and started charging for costs.** GIS beat ($0.75 vs $0.72) and sold off on "higher costs weigh on profits," and CPB and STZ followed to fresh lows with no news of their own. COST beat and was paid +3.0%. Earnings Surveillance saw the same grading in every sector. **SNX beat by 20.8% and fell -9.9% on negative free cash flow**, SFIX beat and fell -21.6% on its guide, and PAYX beat and fell -8.8%. Cash flow, the guide and input costs now outrank the EPS line.

**Cecil bought in eight sectors in the week the ten-year made a 19-year high.** Every purchase was a broken price on intact earnings, not a bet on duration:

- **BAC**, a quarter position at 10.7x forward, a 21% gap to target and RSI 25.4.
- **CAT**, a starter at ~$821 and 25x forward with the order book inflecting, plus an add to **GE** at ~$327.
- **PPG** at ~$107.50 and 15.1x, on input-cost relief as oil broke.
- **MPC**, a quarter position at $393.52 and 14.7x, with the crack still above $55.
- **NFLX**, a half position at ~18.8x forward once the downgrade stabilized.
- **AEO**, a half position at 8.6x forward with a 3.1% yield.
- A small **AMGN** starter at 16.2x forward and 2.5%.
- **KDP** in staples, "the closest thing to a toll road in beverages."

At the other end he harvested: **a third of INTC at 59.8x trailing, half of AMD above its own mean target ($630.99 vs $618.51), and AAPL, above target for a fourth week.**

**The value shelf and the trap shelf, updated.** Still waiting for a price:

- **EOG at 11.2x**, to add at $136; **XOM**, at $156–157.
- **GOOGL at 17.5x**; the Oct 2 judgment is "a formality risk."
- **SCHW at 12.6x forward**, sitting on its 200D.
- **MU at 6.8x forward**, with nothing added before Wednesday's print.
- **VST near $134**, on the utilities desk's 10Y signal.
- **O, then WELL**, on the real-estate list.
- **FCX at 17.2x forward**, blocked by his own DXY rule (#115).

The traps:

- **CHTR at ~3.0x** ("a falling knife wearing a value costume").
- **CMCSA at ~7x and 5.8%**, below its old low.
- **EXC at 15.5x** ("the value trap that keeps proving it's a trap").
- **UPS at 7.1%** and **SAFE at 7.6x**.
- **MCD** at a fresh low ("Jefferies is right").
- The entire branded-food row.

**Where the Street's targets are already reached:** AMD, INTC and AAPL trade above their mean targets. **AMGN ($414.80) is now above its $389 target** after +7.6% of Lp(a) hope-buying. **TMO is above its $653 target** at a new high. **MPC, VLO and PSX are still ~6%, ~9% and ~1% above target even after falling 6–7%.** GPRK sits above its $10.85 target.

**The cost of holding leadership went up.** SMH at ~41x trailing earns about 2.4%, roughly **280 bps below** the ten-year. XLK at ~34.7x earns about 2.9%. Scarcity still earns a premium, but that premium is now paid against a 5.184% risk-free rate. **In credit, Cecil's trigger moved a third of the way.** HY OAS rose 10 bps to **280** and HY–IG crossed **200 bps (201)**, while IG barely moved (79). His posture: extend in IG, and stay away from HY until two more prints say whether this was noise.

---

## 2. MARKY'S SYNTHESIS — Technician Lens

**The index rose and the average stock fell, and for the first time this cycle the board can measure the gap on live data.** SPY snapped a three-week losing streak, **+1.27% to $771.35**. The equal-weight RSP fell **-0.56%**, a **-1.82-point** gap in a week and **-5.64 points** in a month, both wider than last week's (-0.86 / -3.45). Canary Watch's first live breadth read since July shows **26.5% of S&P 500 members above their 50-day (54.2% a month ago)**, **46.4% above their 200-day**, and **31 new lows against 3 new highs** on Friday. The page had been carrying a ~68% figure from a July snapshot, while the real number fell for a month. Marky's line: an index can rise on two sectors for a long time, but it is not a healthy way to do it with a 10Y at 5.18%.

**The moving-average map.** Five of twelve ETFs are above their 50-day, up from four: **XLK, SMH, XLV, XLE (by 38 cents), and XLC, which reclaimed it this week.** Five are above their 200-day, the same five as last week: **XLK, SMH, XLV, XLE, XLF.** Six are below both: **XLI, XLB, XLU, XLP, XLRE, XLY.**

**Three breakouts held:**

- **SMH passed its retest.** It cleared last week's **$580.81** high on Monday (+4.02% to $596.03) and closed above $600 on Tuesday for the first time since July 14. Thursday's bond-selloff low of **$588.92** held above the breakout line. It closed at **$606.56**, just under a **$608.67–$609.66** double top. The caveat is volume: Friday's 4.59M shares were 27% below the prior Friday's.
- **XLK closed about 1% under its $198.73 June high** with RSI 63.5, having ignored the 5.11% and 5.18% closes. Marky won't chase the high on this breadth; the retest zone is **$190–$191.75**.
- **XLC reclaimed its 50-day (~$111.00–$111.32)** and stalled one dollar under its 200-day (**~$113.96**).

**Five breaks confirmed:**

- **XLE failed its breakout a second time**, with a weekly close below **$63.46**. The 50-day (**$61.66**) was tagged to the penny twice and held.
- **XLU went through $40** for the first time since 2024. It traded as low as $39.13 and closed at $39.51 (RSI 25.2), its sixth straight down week, on the correction's heaviest Friday volume (30.3M shares).
- **XLRE's trapdoor fired.** It closed the week under **$42.50** (at $41.56), its third close below the 200-day and its fifth straight red session. **$40.00** is now the magnet, and **$41.33** is the last shelf.
- **XLB's reclaim died at $50.64.** It spent one day above its 200-day (~$50.5) and then closed back below. **$47.00** is live under **$49.57**.
- **XLI closed a second week below its 200-day ($171.95) with no distribution**; volume was below average in all five sessions. That makes it the year's best bear-trap setup, and ISM on Oct 1 decides whether it springs.

**The oversold defenses held by dimes:**

- **XLY** defended its **$109.41** gap for the second time in three weeks: by 21 cents on the 5.18% day, after 22 cents on FOMC day.
- **XLP**'s Thursday flush ($81.70) held above Monday's low ($81.73), forming a double bottom.
- **XLF** based at **$54.50** after Tuesday's 70M-share distribution day, with RSI 30.6 and BAC at 25.4.
- **XLV** spent eight straight sessions above its 50-day ($167.53) and sits 3.4% under its all-time high.

**Springs and redlines.** Springs: **O 17.4 (on 2.5x capitulation volume), DTE 17.8, WAFD ~18.5, GTY 20.7, MGEE 25, XLU 25.2, BAC 25.4, RTX ~27, CMCSA 27.5, XLRE 29.3.** Redlines: **AMD 73.0 (25% above its 50-day), SDGR 72, META 71.4, and CEVA 70.2 on no news.**

**Both remaining diversifiers are losing money.** **XLP's correlation flipped negative (0.105 → -0.034; issue #118)**, and **XLE's inverse re-deepened (-0.095 → -0.356)**. Both sectors fell while SPY rose, so neither is a hedge a book can rely on in a down week. **XLRE jumped from 0.446 to 0.621**: real estate now moves with the index as rate beta. XLK (0.784) and XLY (0.745) rose again.

**Volatility ignored the bond market for a third week.** The VIX closed at **14.87 (+0.41%)** after breaching 16.50 intraday for the third straight week (16.57 on Thursday) without a single close above it. Contango held (VIX/VIX3M peaked at 0.85), VVIX sat at 87.84, and the **equity put/call ratio averaged 0.51**: traders bought calls, not protection, in the week the 10Y broke out. Marky's lines: the VIX at **16.50** on a close, the 10Y at **5.23%** (Friday's intraweek high), and **XLK -5% vs SPY** as the leadership-break signal.

---

## 3. OPHELIA'S SYNTHESIS — Macro Lens

**The 5.00% line became a floor, and the bond market put it there without the Fed.** The 10Y closed at **4.963%** Monday and **4.968%** Tuesday. It broke through on Wednesday (**5.114%**, +14.6 bps, its biggest one-day move in about 18 months) and then printed **5.162%** and **5.184%**. That is **+18.6 bps on the week**, with an intraweek high of **5.230%**, and the first *weekly* close above 5.00% since July 2007 (issue #113).

The canonical curve: **3M 4.07%, 2Y 4.87% (FRED, Thursday), 5Y 5.007%, 10Y 5.184%; 10Y–2Y +31 bps, 10Y–3M +111 bps.** Last week the curve bear-*flattened*, with the dots doing the hiking at the front end. This week the long end led. **10Y–5Y re-steepened from +14.2 to +17.7 bps**, 10Y–3M widened from +102 to +111, and the 30Y ran from 5.331% to **5.504%** (economic calendar). The evidence that this is term premium rather than inflation fear sits on three screens:

- The **$70B 5-year auction tailed 3.1 bps** at 5.033%, the second-largest tail on record for the tenor, and indirect bidders fell to 54.3%.
- The **7-year was soft again**: a 0.7 bp tail, graded C-.
- **10-year breakevens were flat at 2.34%** while oil fell 7.84%.

In other words, buyers want more to hold duration, and a Fed pause does not fix that. Governor Barr added that "further policy adjustments are likely to be needed," and CME odds of an October 28 hike rose from ~58% to **~73–76%**.

**The data said "no landing."**

- **Business surveys ran hot.** The S&P flash composite PMI jumped to **58.4** (consensus 55.2), its fastest in more than five years, with manufacturing at **57.0** (vs 53.6). Input costs rose at the steepest rate in four years.
- **Orders, hiring and housing beat.** The KC Fed survey printed **14**. **Core capital-goods orders rose +1.6%** against +0.5%. Claims stayed under 200K for a second week (**197K**). New home sales came in at **684K** against 615K, though that was bought with price cuts (median price -5.8% YoY).
- **The lone miss was Richmond** (-2).
- **The consumer file was the exception.** Final UMich came in at **48.1**, a four-month low that beat its whisper, but **1-year inflation expectations rose to 4.6%**, the highest since June.

**The rotation story: scarcity kept winning, but "scarce" changed meaning.** Last week it meant memory. This week it meant:

- **Server CPUs**: INTC +13.2%, and AMD +12.7% through a $1T market cap on Meta's Muse agent.
- **Electricity that already exists**: CEG +3.4% in a fund down 3.87%, after Oracle declared force majeure over power.
- **Grid equipment**: ETN +3.6%.
- **Copper**: +2.48% into a rising dollar.
- **Natural gas**: up about 10–12% to ~$3.25 on AI-power demand.

Everything priced off a discount rate was sold, and **seven of twelve sectors were in outflow for a second week.**

**Four cross-currents the Council cannot yet resolve:**

- **Oil fell and rates rose anyway.** WTI dropped **-7.84% to $92.44** (low $88.71 on Wednesday) after a three-hour U.S.–Iran meeting at the UN, and Brent broke $100. The 10Y still gained 19 bps, so this week's oil relief never reached the discount rate.
- **The dollar broke its trip wire.** **DXY 101.04 (+0.81%)** closed above 101 for three straight sessions, which switches materials' restriction on commodity longs back ON (#115). **USD/JPY 157.185** touched 158.996 on Thursday, close to the 158–160 zone where Japan's Ministry of Finance tends to speak. Gold fell 2.36%.
- **China is status quo, with a date attached.** The Trump–Xi summit extended the truce to **January 10** and deferred chips, while Beijing's **80–99% duties on Japanese dichlorosilane**, a chip feedstock (#114), tightened the supply chain.
- **Credit turned.** HY OAS rose to **280** (+10) and HY–IG to 201 in the same week the 10Y broke out. That is still inside the cycle's range, but it is the combination Cecil said would matter.

**What the Economic Calendar revealed:**

- The crisis-line flag moved from "crossed" to **confirmed on a weekly close**.
- CPI MoM > 0.3% is carried.
- The DXY and oil flags stay resolved.
- **NFP < 150K will fire on an in-line print**, because consensus (+100K) already sits below the threshold.

The calendar keeps the regime call at **hiking cycle** and adds a sub-flag: **term-premium expansion**.

---

## 4. CONSENSUS SYNTHESIS

**Where all three agree.**

**5.00% is now a floor, and the next line is 5.25%.** The tech desk redrew Ophelia's line at 5.25% and changed what kind of line it is: "a ceiling for breadth, not for tech." The calendar names 5.25% as the next line, and Marky's marker is Friday's 5.230% high. No desk calls the move over. The relief line most desks name is a **weekly 10Y close under 4.90%**.

**Scarcity pays, while duration and costs are punished, and the market now grades the quality of earnings.** CPUs, power, copper and gas were bought. Bond proxies, towers and branded food were sold. Beats with weak cash flow (SNX), weak guides (SFIX) or rising costs (GIS) were sold, while value with pricing power (COST, CBRL, AZO) was paid.

**The index is two sectors deep, and hedges are cheap.** SMH and XLK carried SPY while RSP fell. A VIX of 14.87 and an equity put/call of 0.52 price none of the bond move. No desk adds duration before PCE.

**Where they disagree.**

- **Is strong growth data good news?** Industrials, materials and semis read core capex +1.6% and PMI 58.4 as cycle confirmation. The calendar, utilities and real estate read the same prints as the reason the 10Y broke out. Thursday's ISM is where the two readings collide (Section 7, Contradiction 1).
- **Is oil's drop relief or a mispricing?** Discretionary, healthcare, communication services and materials' coatings row priced it as relief. Energy answers that "the price of oil is pricing peace; the market for moving oil is pricing war": VLCCs still earn **$1.10M a day**, the Houthis hold Mokha and Perim Island, and Aramco's October cancellation stands (#109).
- **Has credit turned?** Financials calls the credit scare "aging without evidence," reading HY OAS at ~273. Canary's live FRED series shows 270 → **280**: the level is fine, but the direction changed.
- **How much cash?** Canary's Ophelia holds **25–30% cash**, and the calendar says "hold the reduced-exposure posture." **From this Monday, the book may hold at most 20% cash outside an abort** (owner's rule, commit e72d8af). The research posture now asks for more cash than the book is allowed to hold, so the gap has to be covered with hedges, or the owner has to rule.

**The single biggest risk is Wednesday, September 30, and it has two halves twelve hours apart.**

1. **Core PCE at 8:30 AM.** Consensus is +0.3% MoM and 3.4% YoY. **A print of +0.4% or more, or 3.5% YoY or more, locks October and starts pricing December.**
2. **Micron after the close.** The estimate range runs **$28.04–$37.44**, and options imply about ±10% (unverified).

Both land on a board where the index is two sectors deep, **SMH trades at 41x with a 2x beta**, AMD sits at RSI 73, and the 10Y just proved it can rise on supply alone. The semis desk names the breaking combination: **a hot PCE plus a soft Micron guide takes SMH through $580.** Payrolls follow on Friday, with consensus already below the NFP flag. Under all of it sits the financials desk's own warning that "10s3M above +1.00% with XLF under $54" has preceded every credit event of the last 20 years. On the canonical series the curve half is already true (**+111 bps**; Canary notes a constant-maturity basis reads about +94), and XLF closed **84 cents** above $54.

**The single biggest opportunity is the same Wednesday, read the other way.** A core PCE at or below +0.2% unwinds the ~73–76% October pricing, and the springs are more compressed than a week ago:

- **Real estate and utilities:** O at RSI 17.4 on capitulation volume, DTE at 17.8, XLU at 25.2, XLRE at 29.3.
- **Financials:** BAC at 25.4, XLF at 30.6.
- **Discretionary:** XLY coiled at $109.41 after two defenses.
- **Industrials:** XLI's bear-trap checklist needs only a $171.95 reclaim and an ISM of 52 or better.

The utilities desk has already named the relief trade's leaders: **CEG and VST, which broke away from the rate tape this week.** Communication services adds a sleeper: if the Iran truce verifies and oil breaks $90, the October odds fall without any data print.

---

## 5. MONDAY WATCHLIST

> **No staleness caveat this week.** Every level below comes from a wiki stamped 2026-09-25, against Friday 2026-09-25 closes. ETF closes and macro levels are facts.json values. Where a wiki drew its level map off a provisional Friday bar (XLK, XLV, XLF, XLP), the map is kept and the close is restated.
>
> **Book constraint:** from Monday 2026-09-28 the book may hold at most **20% cash** outside an abort (commit e72d8af). Desks asking for 25–30% cash are recommending more cash than the book can hold, so hedges have to carry the difference (Section 4).

| Ticker / ETF | Sector | Trigger / Level | Stop / Invalidation | Rationale |
|---|---|---|---|---|
| **10Y Treasury** | Macro | 5.184%. **5.25%** is the next line (Friday's intraweek high was 5.230%) | Weekly close **< 4.90%** = the relief signal most desks name | First weekly close above 5.00% since 2007, led by term premium (5Y tail 3.1 bps; breakevens flat at 2.34%). No coupon supply this week, so any move has to come from the data |
| **Core PCE / NFP** | Macro | Wed 8:30: core **≥ +0.4% MoM or ≥ 3.5% YoY** locks October; **≤ +0.2%** is the first dovish print. Fri 8:30: NFP consensus +100K | NFP **≥ 175K with UR ≤ 4.1%** → 10Y tests 5.25%; **< 150K** fires the labor flag | The calendar's rule: no new positions into Wednesday 8:30 AM without a stop |
| **SMH** | Semis | $606.56. Add on a close through **$609.66–$610** (double top) → $620s, then $640–650 | Close under **$578.51** = failed breakout; 50D **$565.89** | Breakout-and-retest held ($588.92 on Thursday). Volume asterisk: Friday's volume was 27% lighter |
| **MU** | Semis | **FQ4 Wed Sep 30 AMC.** Consensus ~$31.45–31.59 (range $28.04–37.44), revenue ~$50.8–51.2B; FQ1 guide vs ~$35 / $56.6B | A guide to slowing DRAM price gains (Citi cut its target to $1,150 from $1,400) | $1,082.28, +6.5% into the print. Beat 8 of 8, average move ±9.1%, options ~±10% (unverified). Size it as an event |
| **AMD / INTC** | Semis / Tech | AMD $630.63 at RSI 73, 25% above its 50D ($504.71) and above its mean target. INTC $123.00 at ~59.8x, above its target | — | Harvested by Cecil (half of AMD, a third of INTC). Hold, don't add |
| **XLK** | Tech | $196.27. A close through the **$198.73** June high on Micron-beat volume opens $200+ | Under **$194.70** warns; under **$190–$191.75** the breakout is a bull trap → 50D **$184.10** | With 26.5% of the S&P above its 50D, Marky won't chase. Watch for a second ORCL-style power delay |
| **XLC / META / GOOGL** | Comm Svcs | XLC $112.96: a close over **$114.08** confirms the 200D ($113.96) reclaim → $115–116. GOOGL $343.92 is the add-on-strength name (50D $344.14; final judgment ~Oct 2) | Close under **$111.00** (50D) → $110, then **$105.38** | META ($751.66, RSI 71.4) is a hold, not a chase; it added ~2.3 points to a +1.94% fund on its own. Broadband is untouchable until the late-October prints |
| **PPLI** | Comm Svcs (SMID) | $40.00. MGM bid reportedly "days away" (WSJ); 6.8x trailing, $56.80 target | No bid by the next check | Event-driven. Size small, because a reported bid is not a bid |
| **XLF / BAC / SCHW** | Financials | XLF $54.84. Shelf **$54.46–$54.55**; first proof **$55.66–$55.90**; repair = 50D **$57.08** | Buy a test of the 200D **$53.72**; don't short an RSI-30 fund into it | BAC $56.75 (10.7x fwd, RSI 25.4; Cecil quarter position). SCHW $99.38 sits on its 200D ($98.26). JEF reports Monday after the close |
| **XLI / ETN / GE** | Industrials | XLI $170.43. Bear-trap checklist: daily close over **$171.13–$171.95** + **ISM ≥ 52** + volume → 50D **~$178** | Below **$167.49** the checklist burns → low $160s | ETN $439.98 and GE $326.86 are the only longs being pressed. UPS/FDX untouchable; FDX's date is unconfirmed (Oct 12 vs Oct 28) |
| **XLB / FCX / PPG** | Materials | XLB $49.80: over **$50.64** → $51.7. FCX $72.31 must hold **$71.54**; copper **$6.60** | Under **$49.57** → **$47.00**. No new commodity longs while DXY ≥ 101 (#115); the rule re-opens under 99 | Copper decoupled for a second week (+2.48%). PPG (~$107.50, 15.1x) bought on input-cost relief; reports Oct 27 |
| **XLE / MPC / EOG** | Energy | XLE $62.04: a weekly close back over **$63.46** un-fails the breakout → $65.93 | Close under **$61.42** → 200D **$56.06** | MPC $393.52 (Cecil quarter position): a crack above $55 means de-rating, below $45 means top. EOG add at $136; XOM at $156–157 |
| **WTI crude** | Energy / Macro | **$92.44** (facts.json); week low $88.71 | A verified truce → mid-$80s; a failed one → back over $100 | VLCC rates at $1.10M/day disagree with the price. OPEC+ meets Oct 4; Aramco's November letters follow |
| **XLV / LLY / AMGN** | Healthcare | XLV $170.70: through **$171.02–$171.54** on volume → the **$176.60** ATH | Close under the 50D **$167.53**; then $164–165 | LLY is 14.87% of the fund (Zepbound CVS formulary Oct 1). AMGN above its target after +7.6% is a symmetric binary. XBI needs $158–160 |
| **XLU / CEG / VST** | Utilities | Bearish below **$40.66**; $39.13 is the last support, then the 2024 lows (~$38) | Relief = a weekly close back over $40.66, or a 10Y weekly close under 4.90% | CEG ($263.27) and VST ($138.46) broke away from the rate tape and lead any relief (hold lines $254 / $134). DTE RSI 17.8 |
| **XLP / PEP** | Staples | XLP $82.06: double bottom **$81.70–$81.73**; a reclaim of the 200D (~$83.6) is the repair | Daily close under **$81.00** → $74.06 | GIS beat and sold off on costs. CAG/MKC report this week, STZ Oct 6, and **PEP Oct 8** (cons $2.30) shows whether the cost problem is industry-wide |
| **XLRE / O / CCI** | Real Estate | Trapdoor fired: sell rallies against **$42.50**; a reclaim needs **$43.19** (200D) | Under **$41.33** → **$40.00** within days | O $55.54 at RSI 17.4 on 2.5x volume goes first on the list, but only after a cool PCE or a 10Y week under 4.90%. CCI made a new low at a ~6.2% yield. Trepp's September print lands early October |
| **XLY / NKE / AEO** | Cons. Disc. | XLY $110.56: close over **$113.29** on volume → $114.90–116.70 | Weekly close under **$109.41** → **$105.45–105.66** | **NKE reports Thu Oct 1 after the close** (cons $0.44; stock $35.79; 4.5% yield; ±8.1% average move). AEO $16.59 (Cecil half position). MCD, LOW and CMCSA at fresh lows |
| **VIX** | Macro (vol) | 14.87. A close above **16.50** is the tell (three intraweek breaches, no closes); **20** is the regime question | — | Hedging a 10Y break through 5.25% is cheap |
| **DXY / USD-JPY** | Macro (FX) | DXY 101.04: at **101** the materials restriction is ON; **102** is Canary's yellow. USD/JPY 157.185 (158.996 intraweek) | — | 158–160 is where Japan's Ministry of Finance tends to start talking |
| **HY OAS** | Credit | **280 bps** (FRED, Thursday); HY–IG 201 | **300 bps** = the first real credit signal of the cycle; HY–IG 250 = Canary's trigger | Turned up in the same week the 10Y broke out |

---

## 6. CROSS-SECTOR CONNECTIONS — The Hidden Wires

**Wire 1: the Rate-Sensitivity Chain moved to the long end, and it moved through the auction room, not the Fed.** Last week the front end did the damage ("dots don't get bought back"). This week the transmission ran through Treasury supply: the 5-year's 3.1 bp tail, a soft 7-year, the 30Y from 5.331% to 5.504%, and 10Y–5Y re-steepening. Real estate named the consequence: the long end "defected" from the buyback defense, so there is no segment of the curve left to hide duration in. One move did at least nine jobs:

- XLU went through $40 (carry gap -235 bps).
- The REIT trapdoor fired, and the towers fell 7% (CCI, SBAC).
- SAFE had a third disaster week, to an all-time low.
- Staples' carry gap widened to -259 bps.
- Mortgage rates reached 7.03%, freezing HD and LOW at fresh lows; new home sales rose only on price cuts.
- KBH beat by 16.7% and still fell 3.0% the next session.
- SCHW fell -5.6% onto its 200D on deposit-cost math.
- LQD lost 1.42%.
- VZ's cushion narrowed to ~70 bps.

One sector absorbed it: healthcare, whose "level versus acceleration" doctrine is now two-for-two. The correlation matrix recorded the rest: XLRE jumped to 0.621 as rate beta that moves with the index. The implication for Wednesday is that a cool PCE can lower the front end, but it cannot force buyers back into the 5-year auction.

**Wire 2: the AI supply chain moved from memory to CPUs and electricity, and it filed its first confessions.** The chain ran through four sectors:

- **Semis.** Meta's Muse agent created a bet on x86 orchestration workloads. INTC rose +13.2% (+46% in September; its CEO says Intel supplies ~50% of server-CPU demand), AMD +12.7% to a $1T market cap, and ARM +17% and QCOM +9.3% on Monday alone. The equipment makers (AMAT, LRCX) gained about 9% as core capex printed +1.6%, the first hard capex data since the Sep 14 scare.
- **Communication services.** The same agent lifted the platform most exposed to it: **META +12.99%** (+36% in September), the single stock that carried XLC.
- **Utilities and industrials.** Oracle's force majeure on Project Jupiter (~$18B, Blue Owl-financed) came down to power it could not secure. CEG rose +3.4% while its fund fell 3.87% (the utilities "inversion"), ETN rose +3.6%, and GE Vernova entered XLI's top 10.
- **Commodities.** Natural gas rose about 10–12% to ~$3.25 despite a 53 Bcf storage build, and CRK rotated into energy's small-cap sleeve. Copper rose +2.48% on data-center electrical demand.

**The confessions landed the same week:**

- ORCL could not get the electrons.
- **SNX beat by 20.8% and fell -9.9%** because it is financing AI-server inventory with its own working capital.
- ARM fell -7.9% on a CFO share sale.
- Citi cut MU's target to $1,150 on slowing pricing momentum.
- The data-center landlords bent again (EQIX -1.3%, DLR -1.9%).

The chain now pays whoever owns the constraint (CPUs, power, copper) and charges whoever finances the buildout on its own balance sheet or cannot secure power. Earnings Surveillance counts three AI-infrastructure warnings in under two weeks, and Micron lands on that fault line on Wednesday.

**Wire 3: the Geopolitical Energy Loop reversed and split into two prices.** A three-hour U.S.–Iran meeting at the UN took **WTI -7.84% to $92.44** and Brent through $100. The transmission reached six sectors:

- **Energy.** XLE's breakout failed a second time (-3.53%). The refiners resolved their RSI-90 verticals through price (MPC -7.38%, VLO -6.32%, PSX -6.36%), and small-cap crude torque broke (GTE -6.6%, AMPY -4.9%).
- **Materials.** The coatings row had its first green week since the siege began: ECL +3.72%, IFF +3.29%, PPG +2.86%, SHW +2.61%.
- **Discretionary.** The travel pair flipped: BKNG +4.5% on Friday, MAR +4.4% to a recovery high.
- **Industrials.** DAL rose +6.7% into its Oct 9 print.
- **Staples.** SYY and CHEF got diesel relief.
- **Dashboards and desks.** Canary downgraded geopolitics from red to yellow, and communication services called peace its "sleeper macro bull."

**But the loop never reached the 10Y**: breakevens stayed flat and the 10Y rose 19 bps. **And the physical market filed its dissent:**

- VLCC rates held at $1.10M/day.
- The Houthis hold Mokha and Perim Island at Bab el-Mandeb.
- France is deploying to Yanbu, and six missiles were intercepted over Saudi Arabia.
- Aramco's October European cancellation still stands.
- Saudi output is 6.24 mb/d, and the SPR sits near 1983 lows.

The crude price is pricing peace, and the freight rate is pricing war. OPEC+ on Oct 4 and Aramco's November letters decide which is wrong.

**Wire 4: the Consumer Stress Triangle grew a fourth corner, inflation expectations.** The first three corners:

- **Sentiment:** 48.1, a four-month low that still beat its whisper.
- **Spending:** COST's adjusted comps rose +6.7% (U.S. +7.2%), CBRL gained 15% on $7.99 value menus, DRI came in line with Olive Garden only +1.1%, and claims held at 197K.
- **Housing:** mortgages at 7.03%, LOW and HD at fresh lows, and new home sales up only on price cuts.

Parcels are the signal between them: UPS -5.2% (-12% in September) and FDX -5.8%, which industrials reads as "the household half rolling over." The new corner is **1-year inflation expectations at 4.6%, with households naming grocery and gas prices**, and it wires the consumer straight to the Fed by keeping October priced near 73–76%. It hit three sectors three different ways:

- **Staples:** input costs now trump beats. GIS fell -7.1%, and CPB and STZ hit fresh lows.
- **Discretionary:** the rate hostages (MCD, LOW, CMCSA, F) hit new lows while the rate-immune names (MAR, TJX, DG, TSLA) rallied.
- **Communication services:** CHTR had its third straight -12% week.

The trade-down shopper is the bull case's last hard-data pillar. Earnings Surveillance's verdict: consumers are "trading down, not collapsing."

**Wire 5: the dollar wire tightened through 101.** DXY rose +0.81% to **101.04**. That triggered materials' rule, switching the restriction on new commodity longs back ON (#115), and it hit five more desks through translation:

- **Healthcare:** Q3 pharma drag on LLY, MRK and ABBV (40–55% international revenue).
- **Staples:** KO, PG, PEP, PM and MDLZ.
- **Industrials:** CAT and DE exports, going into Q3 prints.
- **Communication services:** international ad revenue.
- **Real estate:** AMT's international book.

Gold (-2.36%) paid too. USD/JPY at 157.185 (158.996 intraweek) means the carry-trade rebuild since the BOJ's split-vote hike is nearing the Ministry of Finance's zone. Only copper and the semis' offshore-revenue names shrugged it off.

**Wire 6: beat-and-sold went cross-sector.** Last week the market repriced categories. This week it repriced the quality of earnings, and the same rule showed up in five sectors at once:

- **Tech hardware:** SNX, on cash flow.
- **Discretionary:** SFIX, on its guide.
- **Services:** PAYX, on one segment.
- **Staples:** GIS, on input costs.
- **Homebuilders:** KBH, which beat by more than 15% and still fell.

The rewarded prints all sold value with pricing power: COST, CBRL, AZO. That sets the frame for this week's reports:

- **JBL**, Wednesday morning: read it for cash.
- **MU**: the guide, not EPS.
- **ACN**: its last beat fell 18%.
- **NKE**: a beat streak built on lowered bars.
- **PEP**: whether GIS's cost problem is industry-wide.

---

## 7. SECTOR CONTRADICTIONS — Where the Wikis Disagree

**Contradiction 1 (MOST SEVERE: bull and bear on the same macro factor, strong growth).** Industrials calls core capex +1.6% "THE cycle-confirmation" and will restore the cyclical core to overweight on **ISM ≥ 52**. Materials says the fundamental bull case improved in the same week the FX regime got worse. Semis calls it the sector's "best macro input." The economic calendar reads the same week as "no landing with a hawkish Fed" confirmed, and treats **ISM > 56 with prices paid rising** as a hawkish reflation signal. Utilities and real estate say the rates this data produces are the only thing setting their prices. Thursday's ISM is where the readings collide:

- **A print between 52 and 56** springs industrials' bear trap without the reflation flag.
- **A print above 56 with prices paid rising fires both at once**: the cyclical re-upgrade, and the hawkish flag that pushes the 10Y toward 5.25% and hits utilities, real estate, staples and a semis complex at 41x.

The Council has no rule for netting a print that is a sector bull trigger and a macro bear trigger at the same time. **Issue opened.**

**Contradiction 2 (oil: relief or mispricing?).** The level is agreed; the meaning is not. Four desks priced relief:

- Healthcare: "the disinflation channel stayed open a third week."
- Discretionary: "the fuel tax is deflating."
- Communication services: "peace is the sector's hidden macro bull."
- Materials: "the stagflation corner dissolves."

Energy says one of the two oil markets is wrong: VLCCs at $1.10M/day against ~$93 WTI is "a $15–20/bbl disagreement about the world." Canary's cross-asset read also undercuts the relief chain that communication services and discretionary rely on (lower oil → lower October odds). Oil fell 7.84%, and the 10Y still rose 19 bps with breakevens flat.

**Contradiction 3 (Truth Layer: the WTI weekly change).** The header table has the detail: -7.84% (canonical, off $100.30), -2.7% (eight wikis, via the Fair Value newsletter) and -3.2% (semis, the calendar, `market_state.json`). The last two both descend from the $95.47 bar that no contract reproduces (#110). **Resolution: -7.84%.** Minor siblings:

- **Gold:** materials quotes "-0.7% to $4,328"; canonical is **$4,320.50, -2.36%**.
- **Silver:** materials quotes "+2.3% to $64.95"; `market_state.json` has $64.71, -3.1%.

**Contradiction 4 (Truth Layer: the `market_state.json` rates block).**

| Field | `market_state.json` | facts.json |
|---|---|---|
| 2Y | **4.47%** (+7 bps) | **4.87%** |
| 2s10s | **71 bps** | **+31 bps** |

The 2Y auction stop (4.787%), MarketWatch's Friday 2Y (4.905%) and FRED all put the 2Y near 4.9%, so the feed's series is about 40 bps low. Its policy block and regime string are now correct. Anything that reads `rates.US2Y` or `curve_2s10s_bps` sees a curve 40 bps steeper than the real one.

**Contradiction 5 (the 10Y path, the 2Y and the curve).**

| | Grid A/B/C wikis | facts.json, Canary, semis, calendar |
|---|---|---|
| 10Y Thursday | 5.18% (FRED DGS10) | 5.162% |
| 10Y Friday | ~5.15% | **5.184%** |
| 2Y | 4.905% (Friday) | **4.87%** |
| 2s10s | ~+25 bps | **+31 bps** |
| 10s3M | +0.92% | **+111 bps** |

The gap comes from sources: FRED constant-maturity versus Yahoo ^TNX/^IRX, plus MarketWatch's intraday 2Y. **Resolution: facts.json.** On the canonical series the 10Y did not ease on Friday; it posted its highest close of the week. One consequence matters: the financials desk's credit-event combination is half-armed on canonical numbers, not unarmed as its +0.92% implies (Canary notes a constant-maturity 10Y–3M reads about +94 bps).

**Contradiction 6 (the University of Michigan number).** Industrials writes "Michigan sentiment final **51.7** (weak)," twice. 51.7 was **August's** final. September's final is **48.1** (discretionary, staples, communication services, real estate, the calendar). The desk's conclusion that the household half is weakening survives on the right number.

**Contradiction 7 (General Mills, and Costco's one-time item).**

- **GIS guide:** staples calls it a "beat-and-raise." General Mills' own release is titled "Reaffirms Full-year Outlook," and Earnings Surveillance records the guide as reaffirmed.
- **GIS date:** staples dates it "Tuesday Sep 23," but **September 23, 2026 was a Wednesday** (before the open). This is the second straight week staples has mis-dated GIS.
- **COST's one-time item:** staples calls it "a $184M tax item"; Earnings Surveillance calls it a **$0.15 IEEPA tariff refund**, leaving about +1.1% of underlying beat.
- **Smaller splits:** GIS's week is -7.1% (staples) or -7.4% (Earnings Surveillance), and COST's consensus is $6.54 or $6.53.

**Contradiction 8 (credit spreads).** Tech and financials cite HY OAS at **~273 bps** and IG at 77 (Fair Value, "from 270"). Canary's live FRED series shows **280**, IG **79** and HY–IG **201**. Financials builds "benign, aging without evidence" on the smaller number; Canary builds "the direction changed" on the primary source. **Resolution: Canary (FRED BAMLH0A0HYM2, Thursday print).**

**Contradiction 9 (breadth and the Dow).** Tech says "only 29% of the S&P above its 50-day" (Fair Value); Canary's live count is **26.5%** (Finviz cross-check 26.4%). Tech also says "the Dow fell a fourth straight week"; the committed feed has **DIA +0.3%** ($515.88 → $517.49).

**Contradiction 10 (the 30Y and new home sales).** The Grid wikis cite the 30Y at **5.40%, "highest since 2004"**; the calendar's week totals put it at **5.504%** on Friday, with 5.40% as Wednesday's print. The Grid wikis also report new home sales **+12.7%**, while the calendar reports **+6.4%** because July was revised up to 643K. The Grid figure uses the unrevised base.

**Contradiction 11 (hike odds and the dollar rules).**

- **Hike odds:** Grids A/B/C cite **~71%** for October (Octagon); semis and the calendar cite **~73–76%** (CME FedWatch). Both call October the base case.
- **The dollar:** materials' **101** trip wire snapped (restriction ON), while Canary's DXY row stays **green** below its **102** trigger. That is two rules for one variable, and they disagree about 101.04.

**Contradiction 12 (the cash posture vs the book).** Canary's Ophelia: "I'm keeping cash at 25–30%." The calendar: "hold the reduced-exposure posture." The Monday pipeline, from **2026-09-28**: "at most 20% cash outside an abort" (owner's rule, commit e72d8af). This is not a data dispute. It is a policy gap the Council has to close on Monday.

**Contradiction 13 (minor, but checkable).**

- **Natural gas:** "+5.3% to $3.18" (tech, industrials, materials, real estate; spot) vs "~+10% to $3.25" (utilities) vs "+11.6% to $3.25 front-month" (energy).
- **Brent:** $98.58 (Grid wikis) vs $97.47 (Canary; possibly a contract-roll artifact).
- **MU consensus:** $31.35 (tech), $31.45 (semis, calendar), $31.59 (Earnings Surveillance).
- **MSFT:** $517.89 and +4.9% (tech) vs $516.17 and +4.53% (Earnings Surveillance).
- **CMCSA:** $21.91 (XLC) vs $22.00 (XLY). **DIS:** $106.15 vs $105.53.
- **Durable goods consensus:** -0.3% (industrials) vs -0.4% (semis, calendar); core capex +0.6% vs +0.5%.
- **Dates:** materials says Canada's bans go live "tomorrow (Sep 29)," but Sep 29 is a Tuesday. Healthcare's Cecil puts Zepbound's formulary restoration on "Monday"; it is Oct 1, a Thursday.
- **ETF closes:** the Grid A/B Friday closes came from provisional bars (header).

**Resolved since last week:**

- Micron's date: every desk now says Sep 30, including tech.
- `market_state.json`'s policy block now reads "Hike."
- The 10Y weekly-close question is settled at 5.184%.
- The oil *level* agrees within 0.5% everywhere.

**Still open:**

- FedEx's date: yfinance says Oct 12, TipRanks Oct 28, and FedEx IR has confirmed neither. Last week industrials had FDX reporting on Sep 17.
- The feed restatement of the $95.47 bar (#110).

---

## 8. MACRO CALENDAR IMPACT — The Week the Bond Market Stopped Waiting for the Fed

**This week's data made the bond market's case, and the bond market acted on it before the Fed did.**

- **Monday** brought the Chicago Fed index (-0.08, reported but unconfirmed) and a chip rally on Meta's agent.
- **Tuesday** brought **Richmond -2** against 5, the week's only soft print, and a **2-year auction at 4.787%**, above the 4.75% line that means the front end is pricing an October hike.
- **Wednesday** did the damage: **flash PMIs at 58.4 composite, 57.0 manufacturing and 58.7 services**, input costs rising at the steepest rate in four years, Governor Barr's "further policy adjustments," and a **5-year auction that tailed 3.1 bps** with indirects at 54.3%. The 10Y rose **14.6 bps** that day.
- **Thursday** brought **claims of 197K**, **new home sales of 684K**, a **KC Fed survey at 14**, and a soft **7-year** (0.7 bp tail, graded C-). The Trump–Xi summit extended the truce to **January 10** and changed nothing else.
- **Friday** brought **durable goods at 0.0%** against -0.4%, **core capex +1.6%** against +0.5% (with July revised up), and **UMich at 48.1** with **1-year inflation expectations at 4.6%**.

Eight of ten consensus readings beat. October hike odds rose from ~58% to **~73–76%**.

**The flag board.** The calendar counts **two flags**:

- **The 10Y crisis line, now confirmed on a weekly close** (5.184%).
- **CPI MoM > 0.3%**, carried until Oct 14.

The DXY < 100, oil > $100 and retail-sales flags stay resolved. On canonical data the count agrees this week: WTI at $92.44 is below $100 on every source, so last week's oil-flag dispute is closed. **NFP < 150K will fire on an in-line print** (consensus +100K). The calendar also adds a regime sub-flag: **term-premium expansion.**

**Next week holds two red-rated events in three days, with Micron between them, and no Treasury coupon supply**, so any 10Y move has to come from the data:

- **Mon 9/28:** Dallas Fed manufacturing. Production **above 15** means the regional boom is broad (hawkish); **below 0** means Richmond's contraction is spreading. Jefferies reports after the close.
- **Tue 9/29:**
  - **JOLTS:** openings **above 7.5M** mean labor is too tight for the Fed to pause; **below 7.0M** is the first labor-demand crack.
  - **Conference Board confidence:** Expectations **below 65** deepens the recession-signal zone.
  - Carnival and CarMax report before the open, and U.S. bans on Canadian motorcycles, dairy and alcohol take effect.
- **Wed 9/30, the stacked gate:**
  - **August PCE and the Q2 GDP third estimate at 8:30.** Headline consensus is +0.4% / 3.7%, core +0.3% / 3.4%. **Core ≥ +0.4% or ≥ 3.5% YoY locks October and starts pricing December; ≤ +0.2% is the first dovish print Ophelia would respect.**
  - ADP and Chicago PMI.
  - Jabil and Conagra before the open, and **Micron after the close.**
- **Thu 10/1:**
  - **ISM manufacturing.** The prior was 54.6 and the proxies point higher. Industrials' bear trap is at **≥ 52**; the calendar's reflation flag is at **> 56 with prices paid rising**.
  - **Claims:** **under 200K** a third week means re-tightening; **over 225K** is the first crack.
  - Accenture and McCormick before the open, **Nike after the close**, and Zepbound's CVS formulary restoration.
- **Fri 10/2:** **September payrolls** (consensus +100K, UR 4.2%, AHE +0.3%). **Under 150K** fires the flag; **175K or more with UR ≤ 4.1%** sends the 10Y to test 5.25%; a negative print is a regime-change candidate. Google's final judgment is due around the same day.
- **After that:** OPEC+ (Oct 4), PepsiCo (Oct 8), Delta (Oct 9), Q3 bank earnings (Oct 13–14), September CPI (Oct 14) and the FOMC (Oct 27–28).

**The Council's posture.**

- **Stance:** defensive and hedged, deployed only where earnings are physical or crash-priced. No new duration.
- **Wednesday:** no new positions into 8:30 AM without a stop.
- **Hedges:** cheap, with the VIX at 14.87 and an equity put/call of 0.52. The thing to hedge is a 10Y break through 5.25%.
- **Canary Watch:** **CAUTION, escalating (rates-led)** for a fifth week. Breadth is now **confirmed red on live gauges**, the correlation row is red on the XLP flip, geopolitics is downgraded to yellow, and credit is green but turned.
- **Cash:** the desks' 25–30% posture meets a book capped at 20% from Monday. Until the owner rules, the rest of the defense has to come from hedges, not cash.

---

> *Synthesis compiled by the Saturday Research Crew — Synthesis Agent*
> *Timestamp: 2026-09-26T07:21:27-04:00 (resumed pass; the first pass started 2026-09-25T23:30:14-04:00 and stopped at a usage limit after STEP 0 and the fifteen reads)*
> *Data as of: Friday, September 25, 2026 closes — all 15 wikis + macro/facts.json (generated 2026-09-25) + data/market_state.json (as_of 2026-09-25); a Saturday re-pull confirmed the settled XLK/XLV/XLF/XLP closes*
> *Wiki freshness: 15 of 15 fresh, 0 stale. Truth Layer: facts.json fresh and complete. Open defects: market_state.json 2Y/2s10s (~40 bps off); WTI's weekly change still computed off $95.47 in the feed, the calendar and eight Grid wikis (#110).*

*Last updated by Saturday Research Crew: 2026-09-26*
