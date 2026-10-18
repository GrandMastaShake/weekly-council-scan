# Weekly Council Synthesis — Week Ending Friday, October 16, 2026

> ⚠️ **DATA FRESHNESS (STEP 0, checked first). ALL 15 WIKIS ARE FRESH. THE TRUTH LAYER IS 0 DAYS OLD. THIS JOB RAN A DAY LATE.**
>
> - **Wiki stamps:** the eleven Kimi sector pages and tech/financials/healthcare/industrials are stamped **2026-10-16** (Friday-evening Grid A/B/C runs covering the week ended Fri Oct 16); semiconductors, economic-calendar, earnings-surveillance and canary-watch are stamped **2026-10-18**. **No wiki is older than 7 days. No wiki is stale.** The Monday Watchlist carries no staleness caveat.
> - **Schedule failure, logged and not papered over.** This job is scheduled Saturday 20:26 ET and ran **Sunday 2026-10-18 at 18:36 ET**, about 22 hours late. The Claude-side upstream jobs also fired late (Semis + Calendar, Earnings Surveillance and Canary Watch all started 03:55–03:58 ET Sunday). All four had END lines in `logs/cron.log` before this job's START, so nothing was waited on and nothing was missing.
> - `macro/facts.json`: generated **2026-10-18** (Canary Watch, commit fa6f74c, `truth_check --facts` 28 ok / 0 warn / 0 fail). **Not older than 8 days, so the "Canary missed its facts step" warning does not apply.** All values are Fri 2026-10-16 closes except the 2-year (FRED DGS2, Thu Oct 15, FRED's one-day lag). Canonical values used on this page: 10Y **5.098%**, 5Y **4.899%**, 2Y **4.77%**, 3M bill **4.07%** (^IRX), 10Y–2Y **+33 bps**, 10Y–3M **+103 bps**, VIX **19.99**, SPY **$763.25**, DXY **101.84**, WTI **$101.41** (CLX26 settlement), gold **$4,159.50** (GCV26 settlement), copper **$6.5735** (HG=F), BTC **$81,501**, HYG **$76.86**, LQD **$103.40**, fed funds **3.75–4.00%**, stance **Hike**. Every sector-ETF close and week-over-week change in facts.json equals the figure on its sector page (twelve of twelve).
> - `data/market_state.json` (`as_of` **2026-10-16**) is fresh and feeds the README Index Check (SPY $763.25 -2.0%, QQQ $709.80 -5.5%, DIA $519.10 +0.6%, IWM $270.44 -3.0%, VIX 19.99). **Two stale fields inside it:** its `policy.next_macro_gate` and `upcoming` block are as of 2026-10-11 and still describe September CPI as a future event; its 2Y (4.74%) and 2s10s (36 bps) are the Treasury-par Friday basis, not facts.json's. Facts.json wins on this page (Section 7.A).
> - **The disagreement that matters, resolved in Section 7.A:** nine sector pages carry WTI at **$99.04** ("Fri evening, CL=F, provisional"). That quote was the **December** contract after Friday's roll. The November contract (CLX26) **settled $101.41, +10.4%** — through the materials desk's ±10% commodity line, which that page called "not met." Issue #169's provisional trigger is confirmed at **+$9.56**, not +$7.19.

---

## 1. CECIL'S SYNTHESIS — Fundamentalist Lens

**The carry gaps narrowed for the second week and the value got repriced before he could reach it.** With the 10-year at **5.098%** (from 5.244%), utilities' 3.07% sits **203 bps** under the risk-free rate (from 217), real estate's 3.53% **157 bps** under (from 171), staples' ~2.73% **237 bps** under (from 250). The single-name yields that clear the Treasury are a short list: **VZ 6.4%** (about 127 bps over, down from 155 because the stock rose 7.5%), **CMCSA 6.1%**, **EIX 6.3%**, **O 5.9%**, **AVA 5.4%**, **GIS 7.4%**, **UVV 8.2%**. His rule from last week — a yield is a price only when what produced it is a headline rather than a verdict — gave him two buys this week and two refusals. **Bought: Realty Income at $56.08** (starter, 5.9%, 17% under target; the condition he wrote down — a second lower weekly 10-year close — was met by 14 bps) and **Vistra at $152.02** (14.7x forward, 38% to target, the DOE loan and the Meta and uprate contracts unchanged; "the market sold the pair because it sold AI; the contracts did not get worse"). **Refused:** GIS at 7.4% ("still a no") and VZ at 6.4% ("I keep it and do not add").

**The cheapest list on the board is now the AI supply chain, and he will not touch it until a buyer speaks.** SMH ~29x trailing, **TSM 26.7x**, **MU 11.8x trailing / 4.2x forward**, LRCX 22x forward with a 42% gap to target, MSFT 22.3x after a -1.1% week in a -7.7% fund ("still the quiet leader and still the add"). TSMC beat and raised (Q4 guide **$52.3–54.3B**, +14% Q/Q) and ASML said it cannot meet 2027–28 demand, and the stocks fell 9% and 8%. His reading: "this is not an earnings problem at the supplier level; it is the market marking down the probability that the people paying for the chips can keep borrowing." The lesson he takes against himself: **MU at 5.0x forward last week cost him 14.6%** — "a low multiple on peak earnings is not a margin of safety." The gate is **Meta on Wednesday**. The same funding question sits under **CAT** (22.4x, 30% to target, -8.7%, held to Oct 29), **GEV/ETN** (-8% to -9%), **EQIX** (lowest close since March) and **PLD** (beat, raised, fell to its lowest close since January, 24% under target — "on my list now the print is behind it").

**What got expensive is the shelter.** **KO 26.6x and 1% from its target, PG 1.4% away, MO above its own; ED above its target, SO with 5.6% left; TRV 7.4% above target, CB within 2%; AMGN, ABBV and PFE over theirs; AAPL 36x and above its target "where the money hid"; MAR above its target; V and MA at records with RSI 73–75 into their Oct 27/29 prints.** The refiners are cheap on earnings (MPC 8.5x, VLO 9.4x) and 4–9% above targets that keep chasing them; XOM closed above its target. He trims, he does not add, anywhere the safety trade has reached the Street's number.

**Value against traps.** Value with a reason he can name: **UNH** at 17.3x with an 18.8% gap after a beat and a raised year; **REGN** 12.8x; **J&J under $250** (the talc charge "ends a liability rather than starting one"); **BKNG** 13.2x with a 43% gap; **TMUS** 11x with 49% to target, the carrier that recovered least; **GOOGL** at 22.3x on its 200-day, an add under $335; **STZ** 10.9x and **SYY** 15.4x on the staples list; **CRH** 13x off a 52-week low "when the mortgage rate moves." Traps: **ALB at 8.5x** (cheap and broken, under the dollar restriction), **SKYD** ($80B of net debt), **BAC at 9.9x** (a $1.2B penalty is a one-off "only after a quarter without one"), **AMZN at 23.9x** "the first mega-cap price on this page that is starting to interest me," with its print Oct 29.

**Credit is the line he is watching most.** HY OAS made a cycle peak of **325** on CPI day and finished Thursday at 323; HY–IG reached **241**, then **239**, eleven under the 250 trigger; CCC widened to **1,278**, another 52-week high. HYG fell 0.48% in a week the 10-year fell 15 bps, and LQD rose 0.97%: duration was bought, credit risk was sold. CoreWeave's 2032s near 15% put the AI-capex financing story on the high-yield tape. If Friday's FRED print (posted Monday) shows HY–IG at 250 or wider, he wants the Council's high-yield exposure at zero.

**His scorecard, honestly.** Working: **VZ** (+7.5% from the $41.65 add), **EOG** (added $150.51 Monday, $158.01 Friday — the last add), **MPC** (held; trim line raised to $454.51), **DTE** (+1.2%). Losing: **MU** (-14.6%), **CAT** (-8.7%), **PPG** (11 cents under his $107.50 cost). New: **O**, **VST**. And the book he does not run: Cecil has had **no name in the Council's own book for three weeks**.

---

## 2. MARKY'S SYNTHESIS — Technician Lens

**The index broke its 50-day and the leaders distributed. That is the tape.** SPY fell **-1.97% to $763.25**, its worst week since late June, and closed under its 50-day (~$768.50) for the first time since the rotation began; Wednesday's -1.08% on CPI was the worst day since July. QQQ **-5.5%**, IWM **-3.0%** (a sixth straight down week on last week's brief's count), DIA **+0.6%**. Under it: **SMH -10.53% to $539.79** on volume that rose every session (**6.3M → 8.0M → 11.9M → 15.1M → 18.4M**, the last 2.4x its 20-day), SOX down **eight straight sessions**, its longest streak since 2008. **XLK -7.70% to $183.47** on the same signature (**5.2M → 15.3M**), five closes under the $198.73 old high, through the 20-day and the 50-day, Friday on its low. "Volume rose every day: that is distribution, not a shakeout." RSIs: SMH 31.4, XLK 33.4 — near oversold, not there.

**The defensives broke out on risk-off days, which is the pattern you want.** **XLV** made a 52-week closing high ($177.19 Thursday) and holds over the $176.60 August high; **XLE** closed on a 52-week closing high ($68.24) on its heaviest volume of the week; **XLP** tagged $88.48 through its $88.31 closing high and closed $87.62 at RSI **73.0**; **XLU** reclaimed its 50-day on a day SPY fell 1.1%; **XLB** cleared its 200-day on Thursday's 14.9M. The failed breakouts are as telling: **XLY** gapped over its 50-day Friday and closed $1.95 off the open on 16.2M (2.3x average); **XLC** made its fourth one-day 50-day reclaim in four weeks and lost it again; **XLRE** stalled at $42.49, eight cents under the $42.57 trapdoor; **XLI**'s $166.18 line held on every close while the intraday lows went $166.56 → $165.69 → $164.66 — "wear, not defence."

**Breadth, by the Grid's own count: seven up, one flat, four down.** Above the 50-day: **four of twelve** (XLE, XLV, XLP, XLU) — XLK and SMH lost it, XLP and XLU took it back (Canary's count agrees exactly). Above the 200-day: **seven of twelve** (XLK, SMH, XLF, XLE, XLV, XLP, and **XLB**, reclaimed Thursday), up from six. Still below: XLC, XLU (twelfth weekly close below), XLY, XLI (fifth), XLRE (fifth). Canary's constituent count says the average stock improved while the index fell: **44.9%** of S&P members above their 50-day (35.0% last week), off the 40% red line for the first time in four weeks; RSP **+0.49%** vs SPY **-1.97%**. Outside the S&P it got worse: market-wide 26.5% above the 50-day, new lows 410 against 111 highs.

**Correlations broke in a way that matters.** The matrix split in two: **XLK 0.861, XLY 0.804, SMH 0.765, XLC 0.543** tightened to the index; **XLP -0.303 and XLE -0.462** went meaningfully negative, **XLV 0.059** is next. The 10-year and XLU traded the classic way for the first time in a month (10Y -14 bps, XLU +1.9%). **Gold fell -0.8% with real yields down ~16 bps** — a deleveraging signature, not a hedge bid. Volatility's own term structure is the warning: **VIX/VIX3M 0.975** (from 0.835), **VVIX 109.91** (121 intraday), SPX put/call **1.46**. One more Friday like this one inverts it.

**The map of two numbers:**

| Sector | Close | Below | Above | Read |
|---|---|---|---|---|
| SMH | $539.79 | **$539.07** → $518–530 → 200D $511.35 | $564.74, then 50D $579.03 | Flat; "not short into $511–530"; starter over $564.74 on a Meta hold |
| XLK | $183.47 | **$182.82** → 200D $167.18 | $189.80 (50D) / $190 on volume | Flat; distribution on rising volume |
| XLC | $110.32 | **$109.66** → $105.03 | $112.89 (200D) holding a day | Flat; a coil that breaks on Meta |
| XLY | $112.46 | **$110.67** → $109.41 | **$114.68** → 200D $115.46 | Flat after a failed gap |
| XLI | $167.76 | **$166.18** on a close | $170.06, then 200D $172.18 | Line worn three days running |
| XLF | $55.52 | **$54.46** (add off), $52.81 stop | **$56.16** (50D) | Long the add; breadth inside is ugly |
| XLB | $50.92 | **$50.48** (200D) | $51.03 (50D), target $53.42 | Long from Thursday |
| XLRE | $42.16 | **$41.47** (20D) | $42.63 (200D) | Half off; rebuy over $42.63 |
| XLU | $42.21 | **$41.09** | $42.42–42.77, then $43.77 | Long; target one paid |
| XLV | $176.71 | **$176.60** | next leg | Long, no add at RSI 66 |
| XLP | $87.62 | **$86.06**, then $85.43 | $88.31 / $88.48 weekly | Trim half into $88.31 |
| XLE | $68.24 | **$65.54** weekly close | no overhead on the 1Y chart | Long, no add at RSI 69.7 |

**His own line, honestly.** "I said if SMH was under $600 and breadth was under 40, I cut the leadership. Breadth was 44.9, so half the condition was met. I cut it anyway on the board's rule: XLK finished 5.73 points behind the index." If VIX closes above 20 with VIX/VIX3M above 1.00, he hedges the book, not a sector.

---

## 3. OPHELIA'S SYNTHESIS — Macro Lens

**The rotation paid for a second week, but the reason changed from rotation to fear.** Ten of twelve sectors beat SPY. The two that did not are the two that carry it: XLK (-5.73 pts vs SPY) and SMH (-8.56). The money went to **XLP +5.02%, XLE +4.86%, XLV +3.45%, XLB +3.01%, XLU +1.93%, XLF +1.44%, XLRE +1.32%**. Over 21 sessions the board has inverted: last week SMH and XLK were the only two sectors ahead of the index over a month; this week they are the two furthest behind, and XLE (+5.75), XLP (+4.86) and XLV (+4.59) lead. Her verdict on Canary: "Last week it was rotation; this week it was fear."

**The macro cross-current is the hardest one the Fed can get: sticky inflation and a growth scare from financial conditions.** The inflation half confirmed: September CPI **3.7% Y/Y** (3.6% expected), **core +0.3% M/M** (0.2%) and 2.6% Y/Y; PPI **+1.3%** with core **+0.7%**; Philly Fed prices received at a 17-month high; gasoline +9.1% M/M. On those numbers the thesis said yields up and October priced. Instead the 10-year spiked to 5.33% on CPI morning and closed the week at **5.098%, -14.6 bps**, all of it real yield (the 10-year breakeven rose 2 bps to 2.35%). The 2-year did not join (4.77%, FRED Thursday), so **10Y–2Y flattened 16 bps to +33** and **10Y–3M to +103**. October hike odds went ~22% → ~50% on Wednesday → ~28% Thursday (CME) / ~14% Friday (Polymarket) after **Fed Chair Warsh** declined to signal a move in Bangkok. December stays **~79–90%**. The Fed is in blackout to Oct 28. "The bond market looked at hot inflation and a 10.5% fall in semiconductors and priced growth risk, not a hawkish break."

**Oil went through $100 and reached the inflation data in the same week.** WTI's November contract settled up every day to **$101.41 (+10.4%)**; Brent $109.86. Hormuz flows were ~11.6 mb/d against a 17.2 mb/d baseline (Kpler), a crude tanker was struck in the strait on Friday, and the EIA showed an 8.6M-barrel draw on hurricane shut-ins. The IEA's answer finished a pledge already counted. The December contract ($99.02) becomes the front month this week, so the flag needs two December closes over $100. Meanwhile **the dollar fell for the first time in five weeks** (101.84), still above the 101 restriction line (#115).

**What the Economic Calendar revealed.** Three triggers hit — **core PPI > +0.4%**, **retail sales headline > +0.6%** (energy-inflated: gas stations were ~71% of the +0.8% gain; control group **+0.1%** against +0.3%), and **claims under 200K a fifth week** (199K). Industrial production **+0.7%** with utility output +3.5% and the Empire State index at **25.5**, a four-year high; Philly Fed **20.9** (from 37.8). The activity data did not justify a growth scare; the equity and credit tape did: SOX eight days down, CoreWeave's bonds near 15%, VIX **22.31** intraday on an unconfirmed AI hedge-fund rumor. Three regime flags stay up (NFP < 150K carried, 10Y's fourth weekly close above 5.00%, CPI M/M confirmed hot); oil and VIX each touched their line without a qualifying close.

**The contradictions she sees across her own desks.** On the real-estate page she called the term premium "turned, provisionally" and allowed new duration in the yield names; on the calendar page she said "do not chase the bond rally into long duration" because a sloppy 20-year auction on Wednesday could reverse it. On semis she says the chip selloff was not about rates; on tech she waits for the Oct 28 Fed. On healthcare a hike is "the scenario where defensives keep their bid"; on utilities a hike makes the three-week rally "a bounce in a downtrend." Section 7.B lays them out and an issue is filed. Her net posture: **keep the reduced exposure and 25–30% desk cash, keep energy and staples, add IG duration at the margin rather than high yield, and add AI-funding-dependent tech only on a Meta capex confirmation.**

---

## 4. CONSENSUS SYNTHESIS

**Where all three agree.**

1. **Nothing in the AI chain gets bought before Meta's capex guide on Wednesday after the close.** Cecil wants "one buyer to say the budget is intact." Marky is flat and will take a starter only over $564.74 on a Meta hold. Ophelia is "not adding, and not covering the hedges before Meta." The same evening brings Lam Research, Texas Instruments and Tesla.
2. **The defensive bid is real and partly borrowed.** Every defensive page says it in its own words: healthcare ("some of the bid is borrowed from tech and goes back when tech stops falling"), utilities ("that bid lasts as long as the tech selloff"), staples ("the sector broke its five-percent trigger on a flow, not on fundamentals"), energy ("if tech bounces Monday and XLE gives back half, it was the hedge"). Nobody adds to overbought shelter: XLP RSI 73, XLE 69.7, XLV 66, CI 73, ABBV 72, V 73.6, MA 75.3.
3. **Oil above $100 is now an inflation input, not a futures quote.** All three keep energy, none chase it into the November expiry, and all three read the December hike as priced.
4. **The supplier fundamentals are the strongest data in the market and the stocks are the weakest.** TSMC beat and raised, ASML is supply-constrained through 2028, memory is sold out through 2027 — and SMH fell 10.5%.
5. **Keep the cash and the hedges.** VIX at 19.99 makes hedges no longer cheap, "but they are cheaper than they will be if the rumor is real."

**Where they disagree.**

- **Duration.** Cecil bought O and Ophelia's real-estate desk allows new duration in the yield names; Ophelia's calendar desk says the long-end rally is a growth-scare bid that the 20-year auction can reverse, and wants short paper at 4.07%. Marky trades it with stops (XLRE half off at $42.49).
- **The AI-power dip.** Cecil bought VST and holds CAT ("a stock that falls on someone else's news is not broken"); Ophelia's industrials desk keeps power overweight in thesis; her semis desk calls the funding problem "a capital constraint arriving from both ends." Marky does not trade either side until CAT and GEV report Oct 28–29.
- **What fired the chip selloff.** Tech and financials pages attribute it to CPI and hike fears; semis and the calendar say rates were not the driver for a second week. The answer decides whether the Oct 28 FOMC or Wednesday's Meta print is the relief valve.

**The single biggest risk: Wednesday evening turns the financing story into a credit story.** A Meta capex cut or "discipline" language on Oct 21, after a 20-year auction that tails, lands on a tape with VIX/VIX3M at 0.975, HY–IG eleven bps from its trigger, CCC at a 52-week high and CoreWeave paper at 15%. SMH's next map is $518–530 and the 200-day at $511; CAT, GEV, VRT, STX, KLAC and INTC report into it the following week; and the shelter trade is overbought enough to sell to meet margin, as gold already was.

**The single biggest opportunity: a Meta capex hold on an oversold, short-crowded chip complex.** SMH at RSI 31.4 after eight straight SOX losses, short sellers sitting on ~$32B of paper profit (Bloomberg, via the semis page), Friday's close on the September 15 low, and supplier fundamentals that have not cracked. A hold or raise is the first buyer-side answer to the funding question. Marky's targets are $564.74, then the 50-day at $579.03; Cecil's list is TSM at 26.7x and MU at 11.8x trailing, then the equipment names once Lam has spoken.

---

## 5. MONDAY WATCHLIST

*All 15 wikis fresh; levels are Friday Oct 16 closes. Macro levels equal macro/facts.json; index levels are data/market_state.json. **There is no first-tier US data this week and the Fed is in blackout** — the tape is earnings, oil and the 20-year auction. Arena entries lock **Mon 8:50 AM ET** (#163).*

**Macro gates (these outrank every ticker line below):**

| Gate | Level now | Trigger | Action |
|---|---|---|---|
| **Meta capex (Wed Oct 21, after close)** | 2026 capex cited $130–145B; EPS bases $6.76 / $5.70 / $6.54 (EW) | Cut or "discipline" / hold or raise | Cut: SMH tests $511, AI-power names follow, hedges stay. Hold: SMH squeeze to $564.74 → $579; Marky's starter, Cecil's TSM/MU list opens |
| **20-Year auction (Wed 1:00 PM, $13B)** | 10Y **5.098%**, 30Y 5.436% | Tail > 1 bp or stop-out above 5.50% | Term premium back after a growth-scare rally: take the duration adds (O, WELL, XLU, XLRE) off first |
| **10Y yield** | **5.098%** | Weekly close under **5.00%** / back over 5.24% | Under 5.00% clears the flag on a growth scare, not on inflation; over 5.24% fails the defensive breakouts |
| **WTI (November expiry; December the front month)** | **$101.41** (CLX26); CLZ26 $99.02 | Two December closes **> $100** / **< $92** | Above: the oil flag fires (sustained) and October CPI starts with another energy push. Below: the CPI energy push fades |
| **VIX** | **19.99** (22.31 intraday); VIX/VIX3M 0.975 | Close > 20 with VIX/VIX3M > 1.00; 25 is the alarm | Hedge the book, not a sector |
| **HY credit** | HY OAS 323 bps, HY–IG **239 bps** (Thu Oct 15); CCC 1,278 | HY–IG **≥ 250** on Friday's print (posts Monday) | Council high-yield exposure to zero; IG duration stays |
| **China Q3 GDP (Sun night)** | Cons 4.4% Y/Y | < 4.0% | A global demand scare added to the AI scare; materials' metals leg weakens further |
| **Housing (Mon NAHB, Tue starts)** | NAHB 32 (cons 31); starts 1.275M (cons 1.30–1.31M) | NAHB ≤ 28; starts < 1.20M | The rate-sensitive rallies (HD/LOW +6%, aggregates) lose their floor — the mortgage is still 7.40% |
| **Claims (Thu) / Flash PMIs + UMich (Fri)** | 199K; Sep composite 58.4; UMich 46.3, 5-yr 3.5% | Claims > 215K; composite < 55; UMich 5-yr ≥ 3.6% | Layoffs following the freeze / the growth scare confirmed / expectations de-anchoring |
| **DXY** | **101.84** | Weekly settle < 101, then < 99 | The commodity restriction (#115) lifts only below 99 |

**Tickers, levels, triggers, stops:**

| Ticker | Close | Trigger | Stop / invalidation |
|---|---|---|---|
| **SMH** | $539.79 | Starter over **$564.74** after Meta holds; then the 50D $579.03 | Close under **$539.07** → $518–530 → 200D $511.35. Not short into $511–530 |
| **XLK** | $183.47 | Close back over **$190** on volume (50D $189.80) | Close under **$182.82** → 200D $167.18 |
| **XLC** | $110.32 | Long over **$112.89** (200D) holding a day; NFLX Tue, META/T Wed, CMCSA Thu | Close under **$109.66** → $105.03 (short) |
| **XLY** | $112.46 | Long over **$114.68**; TSLA Wed (whisper $0.40 under the $0.44–0.45 street) | Close under **$110.67** → $109.41 (short) |
| **XLF** | $55.52 | Add on a close over **$56.16** (50D); CB Tue, AXP Fri | Close under **$54.46** takes the add off; $52.81 is the stop |
| **XLI** | $167.76 | Buy back over **$170.06**; GE/RTX/MMM Tue, HON/LMT/UNP Thu | Close under **$166.18** → low $160s |
| **XLB** | $50.92 | Add over **$51.03** (50D), target $53.42; CLF/STLD Mon, DOW/NEM Thu | Close under **$50.48** (200D) |
| **XLE** | $68.24 | Hold; no add at RSI 69.7; VLO Thu, SLB Fri | Weekly close under **$65.54** |
| **XLV** | $176.71 | Hold; ISRG Tue, TMO/ABT/DHR/ELV Wed | Close under **$176.60** → $171.87 |
| **XLU** | $42.21 | Target two **$42.42–42.77**, then 200D $43.77; NEE Wed, PCG Thu | Close under **$41.09** |
| **XLP** | $87.62 | Trim half into **$88.31**; rebuy a weekly close over $88.48; PM Wed, PG Thu | Close under **$86.06** on the rest; under $85.43 the rotation is over |
| **XLRE** | $42.16 | Rebuy the half over **$42.63** (200D); CCI Wed, CBRE Thu | Close under **$41.47** (20D) |
| **LRCX** | $263.94 | Cecil waits for the print (Wed AMC; straddle ±8.2%) | — |
| **MSFT** | $529.05 | Cecil's add; reports Oct 28 two hours after the FOMC | — |
| **VST / CEG** | $152.02 / $271.37 | VST bought at the close; CEG under **$265** | CEG under $267.61 = the Google gap is gone |
| **O** | $56.08 | Bought (starter); WELL on a pullback | A 20-year tail Wednesday |
| **UNH / JNJ** | $401.43 / $255.56 | UNH is the widest gap Cecil would own; JNJ start under **$250** | — |
| **TMUS / GOOGL** | $159.10 / $340.59 | TMUS before its Oct 28 print; GOOGL add under **$335** | GOOGL's 200D $340.56 |
| **MPC / EOG** | $478.07 / $158.01 | EOG: last add done | MPC trim on a weekly close under **$454.51** |

**Council book (provisional, from `data/weekly/2026-10-16.json` against the Monday opens; the official close is Monday's tracker run):** ZS $207.38 (-12.6%), JCI $145.47 (-7.3%), HCA $458.84 (+1.8%), BIIB $232.65 (-0.7%), FTNT $169.13 (-14.0%). Weighted, about **-5.3%** for the book against SPY **-2.0%** open-to-close (alpha about **-3.3 pts**). **Three of five names closed Friday below their exit-shadow stop levels** (ZS $218.24 SPEC, JCI $149.12, FTNT $186.89 CORE), and **the XLK thesis line under ZS and FTNT ($196.48) broke on Monday's close**. The shadow stops are not enforced (owner decision pending since the Oct 12 addendum); this is the strongest week yet for the case to enforce them. All five booked names remain outside every sector wiki.

---

## 6. CROSS-SECTOR CONNECTIONS — The Hidden Wires

**Wire 1 — The AI funding chain, one sentence at a time.** Broadcom's CEO tells a Singapore conference that capital, not chips, is the binding constraint (semis) → CoreWeave's 2032 bonds trade near **15%** and CCC spreads hit **1,278** (Canary) → SMH **-10.53%**, equipment worst (AMAT -19.3%, LRCX -17.2%, KLAC -15.3%) → in industrials, **CAT -8.7%, ETN -8.9%, GEV -8.3%** and PRIM -12.4% while the Empire index hit a four-year high → in utilities, **CEG -9.0% and VST -5.9%** in the same week NiSource signed Microsoft for 1,100 MW, the fourth hyperscaler-funded deal in two weeks → in real estate, **EQIX -3.9%** (lowest since March), DLR -1.6%, PLD sold after a beat → in energy, **WMB -1.9%**, the one decliner, on the CEG/VST days. Every node fell on no company news. The market priced the buyer, not the supplier. One node resolves it: Meta on Wednesday, then MSFT/GOOGL (Oct 28) and AMZN (Oct 29).

**Wire 2 — The rate-sensitivity chain, with a break in it.** The 10-year falls **14.6 bps**, all of it real yield → LQD **+0.97%**, HYG **-0.48%** → the bond proxies rally: utilities' regulated book (SO and ED +5.8%), REIT yield names (WELL +4.2%, VTR +4.7%, O +3.5%), staples (21 of 21 rose) → HD **+6.5%** and LOW **+6.1%**, MLM/CRH off 52-week lows → and then the wire breaks: **Freddie Mac's 30-year mortgage held at 7.40%**. Discretionary, materials and real estate all say the same thing: the Treasury move has not reached property financing. On the financials page the same curve **flattened 16 bps from the long end**, the shape least kind to net interest margins (Schwab guided NIM to the low end). The proxies are trading the bond, not the borrower.

**Wire 3 — The geopolitical energy → inflation → Fed loop.** Hormuz a third short, a tanker hit, an 8.6M-barrel draw (energy) → WTI **+10.4% to $101.41** → gasoline +9.1% M/M was about half of September's CPI (calendar) → retail sales' headline beat was ~71% gas stations, control +0.1% (discretionary) → UAL and ALK **-10.6% / -10.7%** into their prints (earnings surveillance) → December hike ~79–90% priced → the front end holds while the long end prices growth risk → back to Wire 2. XLE's correlation to SPY went to **-0.462**: energy is now the index's hedge. And the refiners' crack narrowed from ~$107 to ~$99 as crude caught up, so the producers took the leadership.

**Wire 4 — The consumer stress triangle.** The pump takes the spending (control group +0.1%) → trade-down wins: TJX +6.2%, ROST +6.5%, WMT +6.7%, KO at its highest close on file; food CPI flat helps the grocers' volumes → the two mega-caps that are 41% of XLY fall into their prints (TSLA -7.3%, AMZN -4.7%) → labor demand cracks quietly: ManpowerGroup -15.8% on an in-line print; claims 199K, no layoffs yet → the small end breaks: IWM -3.0%, XBI -6.2%, UVV and SAFE at 52-week lows. UMich's final reading (Fri) and Conference Board (Oct 27) close the triangle.

**Wire 5 — The spectrum wire, a week later.** SpaceX's purchase took 9–13% out of the carriers on Oct 9 → this week VZ recovered **79%** of it, AT&T 52%, TMUS 46%, CHTR and CMCSA closed above their pre-announcement levels (communication services) → the towers kept their surge (AMT +1.7%, CCI +3.3% to RSI 73; real estate) → no FCC action found → CCI reports Wed, T Wed, VZ Oct 26, TMUS Oct 28. The first carrier call decides whether the tower premium is rent or hope.

**Wire 6 — The dollar-and-metals wire.** DXY's first down week in five (101.84) did not lift the commodity restriction (#115) → copper back under the $6.60 rail ($6.5735) → FCX -5.4%, ALB -5.7% (lowest since Nov 2025), CLF -6.6% → XLB still rose 3.0% on gases, chemicals and aggregates → gold -0.8% with real yields falling. A soft dollar plus falling metals plus falling gold is a deleveraging week, not a reflation week.

---

## 7. SECTOR CONTRADICTIONS — Where the Wikis Disagree

### A. Truth Layer — facts.json against the pages

| Item | facts.json (canonical) | What the pages carry | Resolution |
|---|---|---|---|
| **WTI** | **$101.41** (CLX26 settlement, +10.4%) | **$99.04 "Fri evening, CL=F, provisional"** on tech, financials, industrials, healthcare, materials, energy, utilities, staples, discretionary; $101.41 on semis, calendar, Canary | CL=F rolled to December (CLZ26 $99.02) on Friday; the grid pages' $99.04 is the **December** contract. Facts.json wins. **Energy's #169 trigger is confirmed at +$9.56, not +$7.19. Materials' "WTI +7.8%, under the 10% line, no trigger" is wrong on the settled number: +10.4% crosses the materials ±10% commodity line** (no new commodity long is possible anyway under #115) |
| **2-Year** | **4.77%** (FRED DGS2, Thu Oct 15) | **4.74%** on tech, financials, semis, calendar (Treasury par, Fri) and in market_state.json; Canary 4.77% | Different day and publisher. Facts.json stands |
| **10Y–2Y** | **+33 bps** | **+35** (tech, financials), **+36** (semis, calendar, market_state.json) | Follows from the 2Y basis. Every page agrees on direction: flattened sharply from the long end |
| **3-month bill** | **4.07%** (^IRX, discount basis) | **4.26%** (tech, financials: Treasury par CMT); FRED DGS3MO 4.28% Thu; 4.07% elsewhere | Two bases; facts.json uses ^IRX for continuity |
| **10Y–3M** | **+103 bps** | **+83** (tech, financials, par CMT) | Basis again; like-for-like the curve flattened 16 bps |
| **10-Year** | **5.098%** | 5.09% (par) / 5.10% on every page | Agrees |
| **DXY** | **101.84** | **101.78** "Fri evening" on the grid pages | Inside tolerance; no rule changes on either number |
| **Gold** | **$4,159.50** (GCV26 settlement, -0.8%) | **$4,187 / $4,186.70** (GC=F) on tech, materials | Settlement is canonical; the materials page correctly declined to compute a weekly change |
| **Copper** | **$6.5735** (HG=F) | $6.56 Friday-evening last trade (materials, tech, industrials) | Inside tolerance; both readings are under the $6.60 rail |
| **VIX / SPY** | **19.99 / $763.25** | Same on every page | Agree |
| **Sector ETFs** | twelve closes and W/W % | Same on every sector page | Agree, all twelve |
| **HYG / LQD / BTC** | **$76.86 / $103.40 / $81,501** | Canary only | Agree |
| **October hike odds** | ~28% CME Thu / ~14% Polymarket Fri (`next_macro_gate`) | **~42–52%** on tech, financials, industrials, healthcare and earnings surveillance | The grid pages captured Wednesday's post-CPI peak before Warsh spoke on Friday. Facts.json wins; December ~79–90% is common to every page |
| **market_state.json `next_macro_gate`** | rolled to FOMC Oct 27–28 | market_state.json still carries the Oct 11 text (CPI described as upcoming) | The feed builder ran before Canary regenerated facts.json; refreshes on the next build |
| **HY OAS (not in facts.json)** | — | 325 peak Wed, 323 Thu (Canary, FRED); 3.25% / 3.23% (financials) | Agree |

### B. Same factor, opposite reads

1. **The 10-year rally: bull trigger and bear warning at once.** Real estate: "the term premium turned this week, provisionally… I allow new duration in the yield names"; Cecil buys O. Utilities: "constructive" above $41.83. Staples: "defensive-lean" because the 10Y reached 5.10%. **Economic calendar: "do not chase the bond rally into long duration… a sloppy 20-year auction on Wednesday could reverse it… do not add new rate-sensitive positions without a stop."** Canary: the bid is "fear," not rotation. Same factor, opposite instruction. Resolution for Monday: the duration adds already made carry stops (O on a 20-year tail; XLRE under $41.47; XLU under $41.09); no new ones before Wednesday's auction. **Issue filed.**
2. **What drove the chip selloff.** Tech, financials, industrials and earnings surveillance tie it to CPI and hike fears ("the market was grading the September CPI"). **Semis and the calendar say rates were not the driver for a second week** — the 10-year fell 15 bps while SMH fell 10.5%, so the equity risk premium on the AI build-out is what repriced. The two readings point at different relief valves: a hold on Oct 28 (tech) versus Meta's capex on Oct 21 (semis). The tape sides with semis: yields fell and the stocks fell harder.
3. **A Fed hike and the defensives.** Healthcare: "a hike is the scenario where defensives keep their bid." Utilities: "the FOMC hikes Oct 28 → the sector's three-week rally is a bounce in a downtrend." Real estate: a 10-year back at 5.24% fails the fund at the 200-day a third time. Health care is long duration only through its multiple; utilities and REITs are long it through their carry. Both can be right, and a hike would split the defensive basket.
4. **The AI-power dip.** Utilities (Cecil): VST bought at $152.02, "the contracts did not get worse." Industrials: power overweight in thesis, market-weight in size; CAT held. **Semis (Ophelia): "a capital constraint arriving from both ends… I am not adding."** Canary (Cecil): stress is going "to the AI-capex financing chain." The contracts are signed by hyperscalers who pay; the market is pricing whether the hyperscalers' own customers can.
5. **Breadth.** Canary: S&P breadth improved for a second week (44.9% above the 50-day, RSP +2.46 pts vs SPY). Canary again, and industrials: the market outside the S&P got worse (26.5% above the 50-day; 410 new lows), and XLI's breadth was good while the fund fell. Both true; the improvement is a large-cap defensive rotation.

### C. Counts, bases and dates the pages differ on

| Item | Pages | Resolution |
|---|---|---|
| **Meta Q3 EPS** | $6.76 (Yahoo calendar; communication services, earnings surveillance), $5.70 (`earnings_dates`), $6.54 (Earnings Whispers), ~$6.11 (semis, calendar) | Grade against EW's $6.54 per the earnings page; the date (Wed Oct 21 AMC, company-confirmed) is agreed everywhere |
| **Tesla EPS** | $0.45 (yfinance; discretionary, earnings), $0.44 non-GAAP (EW), "$0.21 vs ~$0.43 conflict" (semis, calendar) | Basis resolved on the earnings page: $0.22 was GAAP. Whisper $0.40 is under the street |
| **Lilly Q3 EPS** | $7.16 (healthcare), $7.11 (earnings surveillance), $5.38 (EW) | Unresolved, likely an IPR&D charge; healthcare calls it "the most important number on this page" — 15% of XLV |
| **JPMorgan EPS** | $5.57 (financials, Finviz) vs $5.75 (yfinance, earnings surveillance) | Both pages call it a miss on fixed-income trading; the figure is unresolved |
| **Netflix layoffs** | ~1,000 jobs / ~6%, company-confirmed (communication services) vs "the reported 5% workforce cut" (earnings surveillance table) | Communication services is current; the earnings table carries last week's Puck figure |
| **PPI** | +1.3% M/M, core +0.7% (calendar, Canary); "one source, not checked against BLS" (materials, staples, real estate); "figures conflict — not reported" (utilities) | The calendar's figure stands, with its consensus (+0.5% / +0.3%) |
| **Philly Fed** | 20.9 "single source, not verified" (industrials) vs 20.9 with consensus 26.5–30.0 (calendar) | Agree on the number; the calendar sourced it |
| **XLK 50-day** | $189.80 (tech) vs $189.93 (Canary) | Rounding / window; immaterial to the $190 line |
| **Brent** | $109.69 Friday evening (grid pages) vs $109.86 (semis, calendar, Canary) | Continuous series; directional only |
| **Fund weights** | Every sector page: Yahoo `funds_data` returned weights identical to last week | Carried, not re-measured; read concentration as approximate (XLC platforms 43.1%, XLY AMZN+TSLA 41.1%) |
| **Still unverified** | The AI hedge-fund blowup rumor; the Kospi circuit breaker; the cause of the hurricane shut-ins; Meta's reported plan to lease AI capacity; the Oct 8 Eaton Fire continuance | Carried as unverified on every page |

---

## 8. MACRO CALENDAR IMPACT — The Data Confirmed Inflation, the Market Priced Growth

**This week's data moved the Council's posture in one direction and the market moved it in the other.** The calendar page's thesis — "a Fed that will hike again, a labor market that has stopped hiring, and an oil shock that is not yet in the core" — got its inflation leg confirmed and then some: core CPI hot for a second month, PPI core +0.7%, Philly prices received at a 17-month high, the front-month WTI over $100. The rates leg failed: the 10-year fell 14.6 bps to 5.098% and October odds collapsed back to 14–30% after Warsh. The labor and activity legs held (claims 199K for a fifth week under 200K; IP +0.7%; Empire 25.5). The calendar's new regime label is the right one: **"sticky inflation, a Fed that will hike in December, and a growth scare that is coming from financial conditions rather than the economy."** Three flags stay up; oil and VIX are each one qualifying print from making it five.

**What it did to the posture.** The inflation-sensitive holdings were right again (XLE +4.86%, XLP +5.02%); the AI-funding-dependent names were wrong again; the rate-sensitive adds worked on a bond rally whose reason every desk distrusts. So: **keep the cash and the hedges, keep energy and staples with stops, take the duration trades as trades (with stops), and add AI exposure only on a buyer's confirmation.** The surprise log adds a bias warning for Monday: core CPI and PPI have each come in hot two months running and the consensus has under-called both, so inflation forecasts are too low and hiring and confidence forecasts too high.

**Next week has no first-tier US data and the Fed in blackout, so the calendar is a market calendar.**

- **Sun night / Mon 10/19:** China Q3 GDP (cons 4.4%; < 4.0% adds a global demand scare); **NAHB** 10:00 AM (cons 31; ≤ 28 says 7.40% mortgages have broken builders). CLF and STLD report; FITB, ZION, WAL. Arena locks 8:50 AM.
- **Tue 10/20:** housing starts (cons 1.30–1.31M; < 1.20M is a housing-recession print), pending home sales; GE, RTX, NOC, MMM, GM before the open; **Netflix** after (straddle ±9.5%); ISRG, COF, CB, UAL.
- **Wed 10/21 — the day that matters.** **20-year auction** at 1:00 PM ($13B; a tail over 1 bp or a stop-out above 5.50% says term premium is back). After the close: **Meta, Tesla, Texas Instruments, Lam Research, IBM**; earlier AT&T, Abbott, Thermo Fisher, NextEra, Philip Morris, Elevance. A Meta capex cut sends SMH to its 200-day; a raise ends the funding scare.
- **Thu 10/22:** claims (cons 200K; > 215K is layoffs following the freeze); KC Fed; P&G, Lockheed, Union Pacific, Honeywell, Valero, Comcast, Dow, Newmont; Western Digital after the close.
- **Fri 10/23:** **flash PMIs** (composite < 55 confirms the growth scare) and **UMich final** (5-year ≥ 3.6% de-anchors; < 45 a new low); AmEx, SLB.
- **All week:** WTI's November contract expires; two December closes over $100 fire the oil flag.

**The week after decides the quarter.** **FOMC Oct 27–28** (October odds 14–30%, December 79–90%), with **MSFT and GOOGL reporting the same evening** and **AMZN, CAT, LLY, MRK, MA and INTC on Oct 29**, XOM and CVX on Oct 30; September PCE and Q3 GDP in late October (dates unconfirmed); midterms Nov 3; October payrolls Nov 6. Earnings surveillance calls it "the heaviest week of the quarter, with the Fed in the middle of it," and the option board agrees: XOM priced at 4.4x its realized move, MRK 2.9x, KLAC and FCX 2.2x. **Council posture into it:** research-desk cash 25–30% against the book's 20% cap, the rest of the protection in hedges; no new rate-sensitive position without a stop before Wednesday's auction; no AI add before Meta; and an owner decision owed on the exit-shadow stops, which three of the five booked names closed below on Friday.

---

*Last updated by Saturday Research Crew: 2026-10-18 (Synthesis Agent, single-agent sequential run; scheduled Sat 2026-10-17 20:26 ET, ran Sun 2026-10-18 18:36 ET; all 15 wikis read in group order, all fresh; truth layer macro/facts.json generated 2026-10-18; index levels from data/market_state.json as of 2026-10-16; Council book marks provisional from data/weekly/2026-10-16.json)*
*Next update: Every Saturday 8:26 PM ET*
