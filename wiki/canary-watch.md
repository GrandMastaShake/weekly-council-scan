# Wiki — Canary Watch

> **The Early Warning System for the Market Consciousness Orchestra**
>
> *"The canary does not predict the mine collapse. It simply dies first. Watch the canary."* — Marky

> **Truth layer:** every macro number on this page equals `macro/facts.json` (generated 2026-09-19, same fetch). Week ending Friday 2026-09-18 closes.

---

## VOLATILITY REGIME

| Metric | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| VIX | 14.81 | 15.84 | 14.89 | 🟢 **Normal** |
| VIX 20-Day MA | ~15.71 | — | — | — |
| VIX Trend | Down (-6.5% WoW); intraweek high 18.94 Wed 9/16 (FOMC day) | — | — | — |
| VIX3M (term structure) | 18.24 (VIX/VIX3M 0.81, contango) | 18.60 | 18.57 | 🟢 **Contango held all week (peak ratio 0.90 on 9/16)** |
| Implied SPY Move (30D) | ~±4.3% | ~±4.6% | — | — |
| VVIX (VIX of VIX) | 87.38 | 91.28 | 86.53 | 🟢 **Cooling (intraweek 99.71 Wed)** |
| Put/Call Ratio | n/a | — | — | ⚪ **CBOE feed not wired — requires external update** |

> *Source note: VIX prints vary by vendor — discrepancies of ~2–3 pts are common across quote sources (delayed feeds, spot vs. VX futures, stale prints). Canonical reference: CBOE official close / FRED VIXCLS. FRED's latest posted print at fetch time was Thu 2026-09-17 (15.44), which matches the Yahoo ^VIX 2026-09-17 close (15.44) exactly; Wed 9/16 also matches (17.71 both). FRED has also now confirmed last week's published Friday close (2026-09-11: 15.84). FRED had not yet posted Fri 2026-09-18 at fetch time (its usual one-business-day lag); the 14.81 close used throughout this dashboard and in macro/facts.json is Yahoo Finance ^VIX (Fri 2026-09-18), and the Wed/Thu vendor agreement gives high confidence in the read.*

**Marky Interpretation:** The Fed hiked, the 10Y closed above 5.00%, and vol went *down* on the week. VIX spiked to **18.94 intraday on FOMC Wednesday**, a new high for this cycle above last week's 17.84, and then fell for two straight sessions to close Friday at **14.81, -6.5% on the week**, below its 20-day average (~15.71) and basically back where it was a month ago (14.89). VVIX told the same story: **99.71 intraday Wednesday**, then **87.38 Friday, -4.3% WoW**. The term structure never inverted. VIX3M stayed well above spot all week, and the VIX/VIX3M ratio peaked at **0.90** on the day of the hike before easing back to **0.81**. The options market treated a +25 bp hike (12-0, the first since July 2023) as a known event, and the event came and went. Implied 30-day SPY move eased to **~±4.3%**. My lines are unchanged: 16.50 was breached intraweek for the second straight week and again did not hold on a close; 20 is the regime question; 25 is the alarm. The worry is not the VIX level. It is that the options market is calm while the bond market is at 5.00%.

---

## YIELD CURVE

| Maturity | Yield | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| 13-Week (T-Bill) | 3.978% | +0.065% | +0.278% | Front end repriced for the hike and now leaning toward October |
| 2-Year | 4.67% (FRED DGS2, Thu 9/17 — **refreshed, 1 business day lag**) | +0.04% (vs. FRED Fri 9/11 4.63%) | +0.48% (vs. 4.19% on 8/19) | **Last week's stale 4.20% proxy was ~43 bps too low** |
| 5-Year | 4.856% | +0.065% | +0.503% | Belly still leading the selloff; fresh cycle high |
| **10-Year** | **4.998%** | **+0.023%** | **+0.345%** | **First close above 5.00% on FOMC day (5.006% Wed 9/16), Friday 0.2 bps under** |
| **10Y–2Y Spread** | **~+33 bps** (Fri 10Y vs. Thu 2Y; same-day FRED Thu print: 4.94 − 4.67 = +27 bps) | ~0 (FRED Fri 9/11: +33) | — | **Positive but flat: bear-flattening confirmed** |
| **10Y–5Y Spread** | **~+14.2 bps** | -4.2 bps (was +18.4) | — | **Long end compressing further** |
| **10Y–3M Spread** | **~+102 bps** | -4 bps (was +106) | — | **Positive, narrowing slightly** |

> *2Y and 10Y–2Y correction: last week's page carried a 15-day-stale 2Y (4.20%) and flagged the resulting ~+78 bps 10Y–2Y as "a ceiling, not a read." The refreshed FRED series shows the real spread was ~+33 bps on 2026-09-11 and is ~+27–33 bps now. The 10Y–2Y regime was materially flatter than this page showed for at least two weeks. Note also that ^IRX is a discount-basis T-bill yield. FRED's constant-maturity 3M (DGS3MO 4.12% Thu) runs about 15 bps higher, so a CMT-basis 10Y–3M would read ~+82 bps. This page and facts.json use ^IRX for series continuity.*

**Ophelia Interpretation:** The 5.00% line finally broke. On **Wednesday, September 16**, the FOMC raised rates **25 bp to 3.75–4.00% (12-0)**. It was the first hike since July 2023, and the dots show **16 of 18 participants expecting another 2026 hike**. The 10Y closed at **5.006%** the same day, its first close above the level our real-estate desk has called "the crisis line." Thursday gave back 6 bps (4.947%). Friday took almost all of it back (**4.998%**), so the week ends 0.2 bps under the line with an intraweek high of **5.016%**. The more important news this week is the 2Y. With a live FRED print for the first time in three weeks, **the 2Y is 4.67%, up 48 bps in a month**. The curve I described last week as "positive with a stale ceiling of +78" is really **~+30 bps and bear-flattening**. The 10Y–5Y compressed again to **+14.2 bps**. The front end and belly are doing the hiking, and the long end is only being dragged along. The **BOJ also hiked, to 1.25% (7-2)** on Friday, the highest since 1995. The yen *fell* on it, which removes the "BOJ saves the carry unwind" story from the other side of the ledger.

**Yield Curve Regime:** 🟡 **Positive but flattening under a live hiking cycle.** No inversion anywhere. But 10Y–2Y is ~30 bps, not ~80, and the Fed has told us it intends to keep going. The next gates are **August PCE (Sep 30)** and the **Oct 27–28 FOMC**.

---

## CREDIT SPREADS

> *Credit spreads are now **live from FRED** (ICE BofA OAS series, latest posted print Thu 2026-09-17, one business day lag). This replaces the 2026-07-15 external snapshot this page carried for 58+ days. HYG/LQD Friday closes remain the real-time proxy.*

| Spread | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| HY OAS (ICE BofA US HY, BAMLH0A0HYM2) | 270 bps | 265 bps | 273 bps | 🟡 **Above 250 all year (2026 range 260–346), no fresh widening** |
| IG OAS (ICE BofA US Corp, BAMLC0A0CM) | 78 bps | 80 bps | 81 bps | 🟢 **Tight, near YTD lows (range 73–94)** |
| **HY–IG Spread** | **192 bps** | 185 bps | 192 bps | 🟢 **Below the 250 bps trigger** |
| EM Corporate OAS (BAMLEMCBPIOAS) | 137 bps | 132 bps | 141 bps | 🟢 **Contained** |
| **HYG Price** | **$78.53** | **$78.60** | **$79.71** | 🟡 **Third straight red week (-0.09%, marginal)** |
| **LQD Price** | **$104.70** | **$104.32** | **$106.57** | 🟢 **First green week in three (+0.36%)** |

**Cecil Interpretation:** We finally have the number we have been missing for two months, and it is reassuring. **HY OAS is 270 bps, IG OAS 78 bps, HY–IG 192 bps.** That is *below* the ~220 bps the stale snapshot implied, and well under our 250 bps HY–IG trigger. HY OAS has not been below 260 bps all year, so being above 250 is normal for this cycle and not a widening event. Week over week HY widened 5 bps and IG *tightened* 2. In a week with a Fed hike, a 5.00% 10Y and a Bank of Japan hike, the credit market barely moved. The proxy tape agrees. HYG's "third red week" was **-0.09%**, a rounding error, and LQD posted **+0.36%**, its first green week in three, as duration buyers stepped in near 5%. The two red weeks of HYG/LQD that worried me were rate-duration pain, not a credit-risk repricing. The live OAS series now shows that directly. I am closing the "58-day blind spot" item that sat at the top of my list last week.

**Credit Regime:** 🟢 **Contained (live, first refresh since 2026-07-15).** Spreads are stable-to-tight across HY, IG and EM, with no confirmation of stress. The watch shifts from "is credit breaking?" to "does a second hike in October finally move the OAS series?"

---

## MARKET BREADTH

> *Breadth data (advance/decline, new highs/lows, % of S&P members above MAs) is sourced from external feeds (NYSE, NASDAQ) not available via Yahoo Finance. Values marked stale are last known as of 2026-07-15 — now **66 days old** — and require external feed updates. Rows marked live are computed from this run's Yahoo fetch as proxies.*

| Metric | Current | 5D Avg | 20D Avg | Regime |
|---|---|---|---|---|
| Advance/Decline Ratio | ~1.15 (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| New 52-Week Highs | ~185 (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| New 52-Week Lows | ~42 (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| S&P 500 % Above 50D MA | ~68% (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| S&P 500 % Above 200D MA | ~72% (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| Equal-Weight (RSP) vs. Cap-Weight (SPY), 1W | **-0.86 pts** (RSP -1.20% vs. SPY -0.34%) — live | — | 1M: **-3.45 pts** | 🔴 **Narrow — cap-weight carrying the index** |
| Sector ETFs above own 50D MA (live proxy) | **4 of 12** (XLK, XLE, XLV, SMH) | — | — | 🔴 **Weak participation** |

**Marky Interpretation:** The live proxies say what the stale snapshot cannot: **this is a narrow tape.** SPY closed **-0.34% to $761.69**, its third straight down week, but the equal-weight RSP fell **-1.20%**. The average stock is doing roughly three and a half times worse than the index this week, and **3.45 points worse over the month**. Only **three of twelve sectors beat SPY** (XLV, XLK, SMH), down from four last week and five the week before. Only **four of twelve sector ETFs sit above their own 50-day** (XLK, XLE, XLV, SMH). Every rate-sensitive group (XLU, XLRE, XLI, XLY, XLB, XLF) is below it. SPY itself is just **+0.26% above its 50-day**, held up by tech and semis. Cap-weighted strength is masking equal-weighted erosion. The 66-day-old A/D snapshot is now older than the entire hiking-cycle repricing.

**Breadth Regime:** 🔴 **Narrowing (live proxies), official gauges stale 66d.** I am downgrading from "neutral, deteriorating" because two live measures (RSP/SPY and sectors-above-50D) now confirm the deterioration directly.

---

## SECTOR CORRELATION MATRIX

*30-day rolling correlation of daily returns vs. SPY (30-calendar-day window, 21 sessions 2026-08-20 → 2026-09-18; same convention as prior weeks)*

| Sector | ETF | vs. SPY Correlation | 1W Ago | Regime |
|---|---|---|---|---|
| 🖥️ Technology | XLK | **0.702** | 0.646 | 🔥 **High beta (rising — index leader)** |
| 🛍️ Consumer Discretionary | XLY | **0.696** | 0.637 | 🔥 **High beta (rising)** |
| ⚙️ Industrials | XLI | **0.631** | 0.611 | 🔥 **High beta** |
| 🏦 Financials | XLF | **0.599** | 0.602 | 🔥 **High beta (flat)** |
| ⛏️ Materials | XLB | **0.463** | 0.422 | 🟡 **Moderate** |
| 💻 Semiconductors | SMH | **0.462** | 0.422 | 🟡 **Moderate** |
| 🏠 Real Estate | XLRE | **0.446** | 0.503 | 🟡 **Moderate (easing)** |
| 🏥 Healthcare | XLV | **0.324** | 0.250 | 🟡 **Pro-cyclical (rising)** |
| 📡 Communication Services | XLC | **0.224** | 0.522 | 🟡 **Decoupling fast** |
| ⚡ Utilities | XLU | **0.198** | 0.070 | 🟡 **Re-coupling (rate beta)** |
| 🍞 Consumer Staples | XLP | **0.105** | 0.173 | 🟡 **Weakly coupled — nearest to a negative flip** |
| ⛽ Energy | XLE | **-0.095** | -0.426 | 🔴 **Inverse, collapsing toward zero** |

**Ophelia Interpretation:** The main move this week is **Energy's inverse collapsing, from -0.426 to -0.095**. For a month XLE has been the board's one reliable hedge, bought for the commodity and moving against the tape. This week WTI round-tripped from **$106.75 intraday Tuesday to $100.30**, and XLE posted its first red week in four. It now moves roughly independently of SPY rather than against it. That is not a strict alert: a negative-to-less-negative move is not the positive-to-negative flip our criterion watches for. But it removes most of what Energy was contributing as a diversifier. **Communication Services decoupled sharply (0.522 → 0.224)**, which fits the desk's read of a bull-trap 200-day reclaim followed by an idiosyncratic week (Brinkema ruling, NFLX downgrade, broadband rout). **Utilities re-coupled (0.070 → 0.198)** as the 10Y crossing 5.00% turned XLU into a rate-beta trade. At the top, **XLK (0.702) and XLY (0.696) both rose**, so the index is increasingly a tech-and-discretionary-beta story, consistent with the narrow breadth read.

**The key insight:** the diversifier pool keeps shrinking. Energy's inverse is almost gone, Utilities is gaining rate beta, and Healthcare's correlation (0.324) kept rising after last week's sign flip. Staples (0.105) is now the only sector with a weak enough coupling to flip negative, and that would help a hedged book.

**Alert:** None on the strict flip criterion. No sector crossed from positive to negative. The closest candidates are XLP (0.105, could flip negative) and XLE (-0.095, could flip *positive*, which would leave the board with no inverse sector at all).

---

## SECTOR ROTATION FLOW

*1-Day / 1-Week / 1-Month performance vs. SPY (1D = Fri 9/18 vs. Thu 9/17; 1W = Fri-to-Fri; 1M = 21 sessions from 2026-08-19)*

| Sector | ETF | 1D vs. SPY | 1W vs. SPY | 1M vs. SPY | Rotation Signal |
|---|---|---|---|---|---|
| 🏥 Healthcare | XLV | -0.13% | +2.17% | -3.19% | 🟢 **Inflow (1W rebound, 1M still negative)** |
| 🖥️ Technology | XLK | +0.94% | +1.37% | +4.20% | 🟢 **Inflow** |
| 💻 Semiconductors | SMH | +2.33% | +1.13% | +3.11% | 🟢 **Inflow** |
| 🍞 Consumer Staples | XLP | -0.71% | -0.36% | -3.36% | 🟡 **Neutral (1M outflow)** |
| ⛽ Energy | XLE | -0.14% | -0.93% | +2.11% | 🟡 **Neutral (first red week in four)** |
| ⚙️ Industrials | XLI | +0.56% | -1.18% | -5.75% | 🔴 **Outflow** |
| 📡 Communication Services | XLC | -1.25% | -1.25% | +0.50% | 🔴 **Outflow** |
| 🛍️ Consumer Discretionary | XLY | -0.20% | -1.37% | -5.42% | 🔴 **Outflow** |
| ⛏️ Materials | XLB | -1.30% | -1.54% | -3.86% | 🔴 **Outflow** |
| 🏠 Real Estate | XLRE | -0.84% | -1.71% | -4.51% | 🔴 **Outflow** |
| 🏦 Financials | XLF | +0.08% | -2.09% | -1.86% | 🔴 **Outflow** |
| ⚡ Utilities | XLU | -1.30% | -2.70% | -5.68% | 🔴 **Outflow (52-week closing low)** |

**Ophelia Interpretation:** **Seven of twelve sectors are in outflow**, the widest outflow cluster this dashboard has recorded this cycle. Last week I warned of a possible first six-sector outflow cluster; it came in at seven. The composition changed. **Healthcare swung from worst to best** (-2.79% → +2.17% vs. SPY), a mean-reversion bounce after the trial-failure week, though its 1M column (-3.19%) says the damage is not repaired. Joining the outflow side: **Financials (-2.09%)**, which did not benefit from the hike, consistent with a flattening curve compressing the carry story, and **Communication Services (-1.25%)**, which moved from last week's inflow list to outflow. **Utilities (-2.70%) is the week's worst**, with XLU posting a 52-week closing low as the 10Y crossed 5.00% (issue #108). **Energy cooled to neutral** as WTI round-tripped and XLE lost its 1W lead, though its 1M (+2.11%) is still positive. The only clean inflows are **Technology and Semiconductors**, the same two names carrying cap-weighted SPY while RSP lags.

**The risk:** a two-sector inflow list (plus a Healthcare bounce) under a live hiking cycle is a concentration risk. If tech's leadership cracks, there is no sector left to rotate *into* except cash. The 1M column shows **five sectors below -3.3% vs. SPY** (XLU, XLI, XLY, XLRE, XLB) plus XLP and XLV close behind. The rate-sensitive outflow has gone from a trend to the default.

---

## CROSS-ASSET SIGNALS

| Asset | Level | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| DXY (US Dollar Index) | **100.22** (Yahoo DX-Y.NYB — **now live**) | +1.11% | +1.41% | 🟡 **Back above 100, dollar bid on the hike** |
| EUR/USD | 1.1490 | -1.03% | -0.77% | 🟡 **Euro broke lower out of the range** |
| USD/JPY | 156.129 | +1.07% | -2.14% | 🔴 **Carry unwind reversed: yen fell despite the BOJ hike** |
| WTI Crude | $100.30 | +0.25% | +16.86% | 🔴 **Held $100 after a $106.75 Tuesday spike** |
| Brent Crude | $103.87 | -0.71% | +13.37% | 🔴 **Above $100** |
| Gold | $4,424.90 | +0.36% | -2.65% | 🟡 **Flat — debasement bid still paused** |
| Copper | $6.615/lb | +2.25% | +1.97% | 🟢 **Growth metal firming** |
| Bitcoin | $80,901 (Fri close) | +4.83% | +16.80% | 🟢 **Back above $80K — pullback over** |
| HY Bonds (HYG) | $78.53 | -0.09% | -1.48% | 🟡 **Third red week, marginal** |
| IG Bonds (LQD) | $104.70 | +0.36% | -1.75% | 🟢 **Duration buyers at 5%** |
| TIPS Breakeven (10Y) | 2.33% (FRED T10YIE, Fri 9/18 — **now live**) | -0.03% | +0.03% | 🟢 **Inflation expectations anchored post-hike** |

> *DXY is now fetched from Yahoo's ICE DXY series (DX-Y.NYB) and carried un-stale in macro/facts.json (`yahoo:DX-Y.NYB`, tolerance 1%). It replaces the 2026-07-15 external composite (99.60) this page carried for 58+ days. Last week's informal desk figure (~99.12) matches the Yahoo 2026-09-11 close exactly (99.12). FX 1W changes use this run's Yahoo fetch for both endpoints. Yahoo's JPY=X bar for Fri 2026-09-11 now reads 154.482, not the 153.554 published last week (vendor bar revision), so the +1.07% USD/JPY move is measured on this fetch's own series. Bitcoin uses the Fri 2026-09-18 daily close ($80,901) for the Friday-to-Friday convention.*

**Ophelia Interpretation:** The dollar was the week's cleanest macro read. **DXY closed at 100.22 (+1.11%)**, back above 100 on a verified live print for the first time since this board lost its feed. The hawkish Fed was the driver, and it was reinforced by the market's reaction to the BOJ. **USD/JPY rose to 156.129 (+1.07%)** and touched **157.998** Friday, even though the **BOJ hiked to 1.25%** that morning. A split 7-2 vote read as "one and done," the yen sold off, and the three-week carry unwind this page tracked since USD/JPY broke 160 has reversed. **EUR/USD fell -1.03% to 1.1490.** Oil held its line. **WTI spiked to $106.75 intraday Tuesday** on the Petroline/Aramco escalation (issue #109), then gave it back to settle **$100.30, +0.25% on the week**. It is still above the $100 red trigger, but the spike didn't hold. **Brent $103.87.** **TIPS breakevens slipped to 2.33%.** With a Fed hike and a firm dollar, the market is not pricing an inflation-expectations breakout even with oil at $100. **Copper (+2.25%) and Bitcoin (+4.83%, back above $80K)** both firmed, which pushes back against a pure risk-off read.

**The risk:** a stronger dollar, a 5% 10Y and $100 oil at the same time tighten financial conditions from three directions, while the Fed has pre-announced its intention to keep hiking. The carry unwind that was de-risking the yen trade has reversed into a carry re-build at 156+. That is a fresh long-USD/JPY position building under a BOJ that just showed it is split.

---

## CANARY WATCH TRIGGER BOARD

| Signal | Status | Trend | Trigger Level |
|---|---|---|---|
| VIX Regime | 🟢 Normal (breached 16.50 intraweek for the 2nd week, closed back under) | Down (-6.5% WoW) to 14.81; 18.94 intraweek high on FOMC day; contango intact | 🟡 >20 | 🔴 >25 |
| Yield Curve | 🟡 Positive but flattening | 10Y 4.998% (first close >5.00% on 9/16); 10Y–2Y ~+33, 10Y–3M +102 | 🟡 <0 (inverted) | 🔴 <-50 bps |
| Credit Spreads | 🟢 Contained (live FRED OAS) | HY–IG 192 bps (HY 270 / IG 78); HY +5 bps WoW | 🟡 HY–IG >250 bps | 🔴 >350 bps |
| Market Breadth | 🔴 Narrowing (live proxies; official gauges stale 66d) | RSP -0.86 pts vs. SPY WoW, -3.45 pts 1M; 4/12 sectors above 50D | 🟡 <50% above 50D MA | 🔴 <40% |
| Sector Rotation | 🔴 7 of 12 sectors in outflow | Only XLK/SMH (+XLV bounce) inflow | 🟡 XLK -5% vs. SPY | 🔴 XLK -10% |
| DXY | 🟢 Below trigger, rising | 100.22 (+1.11% WoW), live | 🟡 >102 | 🔴 >105 |
| Geopolitics | 🔴 **Oil >$100 RED trigger — held 2nd week** | WTI $100.30 (spike to $106.75 Tue); Aramco October cutoff (#109) | 🟡 Oil >$90 | 🔴 Oil >$100 |
| Credit Risk | 🟢 Stable | IG OAS tightened 2 bps; LQD green | 🟡 CDS widening | 🔴 Bank stress |
| Policy | 🔴 **Live hiking cycle** | Fed +25 bp to 3.75–4.00% (12-0); 16/18 dots see another 2026 hike; BOJ +25 bp to 1.25% | — | — |
| Overall Risk | 🟡 **CAUTION (escalating, rates-led)** | — | — | — |

**Weekly Narrative — Overall Assessment:** The macro gate this dashboard has been counting down to arrived, and it resolved hawkish on both sides of the Pacific. The ledger: (1) **the Fed hiked 25 bp to 3.75–4.00% (12-0)** on Wednesday, the first hike since July 2023, with **16 of 18 dots expecting another 2026 increase** and year-end projections of 4.1–4.4%; (2) **the 10Y closed above 5.00% for the first time (5.006% on 9/16)** and ended the week at 4.998%, with an intraweek high of 5.016%; (3) **the BOJ hiked to 1.25% (7-2)** on Friday, the highest since 1995, and **the yen fell anyway**: USD/JPY +1.07% to 156.129 reversed the three-week carry unwind; (4) **the dollar reclaimed 100** (DXY 100.22, +1.11%) on the first live DXY print this board has had since July; (5) **VIX spiked to 18.94 intraday on FOMC day and then fell to 14.81 (-6.5% WoW)**, with contango intact all week, so the options market treated the hike as a known event; (6) **credit spreads, live from FRED for the first time since July 15, are contained**: HY–IG 192 bps (below the stale ~220 estimate and the 250 trigger), IG OAS 78 bps near YTD tights; (7) **the refreshed 2Y (4.67%, +48 bps in a month) shows a ~+30 bps 10Y–2Y curve**, far flatter than the ~+78 this page showed on stale data, and bear-flattening is now confirmed; (8) **breadth deteriorated on live proxies**: RSP lagged SPY by 0.86 pts on the week and 3.45 pts on the month, and only 4 of 12 sector ETFs are above their 50-day; (9) **seven of twelve sectors are in outflow**, the widest cluster this cycle, with only Technology and Semiconductors (plus a Healthcare mean-reversion bounce) in inflow; (10) **Energy's inverse correlation collapsed (-0.426 → -0.095)** as WTI round-tripped from $106.75 to $100.30, removing the board's most reliable diversifier; (11) three of this dashboard's long-running blind spots (credit OAS, 2Y, DXY) are now refreshed from live sources. Official breadth gauges (A/D, highs/lows, % above MAs) remain 66 days stale.

The fragilities: (1) the Fed has pre-committed to more hikes with the 10Y already at 5.00%, so the **Sep 30 August PCE** print and the **Oct 27–28 FOMC** are now live-fire events, not distant gates; (2) index strength rests on two sectors (XLK/SMH), and the equal-weight index is falling 3–4x faster than the cap-weight one; (3) the diversifier pool is almost empty: Energy's inverse is gone, Utilities is trading as rate beta, and Healthcare and Staples lost their defensive correlation last week; (4) USD/JPY back above 156 on a split BOJ rebuilds the carry trade the market just spent three weeks unwinding, which raises the risk of a disorderly second unwind; (5) oil at $100 plus a firm dollar plus a 5% 10Y tightens financial conditions from three directions at once; (6) calm vol (VIX 14.81) sitting on top of all of the above is complacency risk, not reassurance.

**The Canary Watch verdict:** 🟡 **CAUTION, escalating (rates-led)**, held for a fourth straight week. The composition changed. Credit moved from "unconfirmed watch" to **green on live data**, and DXY was refreshed below its trigger. Breadth and rotation moved from yellow to **red on live proxies**, and a new **Policy** row is red (live hiking cycle). None of the four strict criteria for a new Canary Watch issue were met: VIX closed 14.81 (intraweek high 18.94, never above 20); the curve is positive at every tenor; HY–IG is 192 bps (HY OAS has been above 250 bps all year with no fresh widening); and no sector correlation flipped from positive to negative. The week's catalysts are already tracked under **#106** (Fed hike / 10Y 5.00% regime), **#108** (utilities, 10Y >5.00%, XLU 52-week low) and **#109** (Aramco October European cutoff), so this run adds no new issue. Watch: (1) August PCE, Sep 30; (2) whether the 10Y posts a *second* close above 5.00% and holds it; (3) USD/JPY into 158–160 and any MoF intervention language; (4) WTI: does $100 hold after the $106.75 failed spike; (5) HY OAS on the next hike: a move from 270 toward 300 bps would be the first real credit signal of this cycle; (6) XLP correlation (0.105) and XLE (-0.095) crossing zero; (7) the official breadth feed, 66 days overdue.

---

## COUNCIL READ — What This Means for Monday

*(Updated this week: major regime shift. Fed hiking cycle live, 10Y first close above 5.00%, BOJ hike, DXY back above 100, curve shown to be ~45 bps flatter than the stale data suggested.)*

**Ophelia:** *"The event I've been positioning for happened, and it was worse in the details than the headline. The hike itself was priced. What was not priced: 16 of 18 dots see another one this year, the 2Y is really 4.67% and not the 4.20% we were reading, and the curve is ~30 bps, not ~80. That changes how I read every rate-sensitive position on this board. I'm keeping cash at 25–30% and adding nothing rate-sensitive before August PCE on September 30. The diversifier problem is now my biggest concern. Energy stopped hedging this week (correlation -0.426 to -0.095), Utilities trades as rate beta, and Healthcare and Staples lost their defensive coupling last week. If I want protection against a second leg in rates, the book has to hold it in duration or cash, not in sectors. The one good news item: credit is fine. Live HY–IG at 192 bps takes a real tail off the table."*

**Marky:** *"Vol spiked to 18.94 on the hike and closed the week at 14.81. That is the options market saying 'priced in.' I half believe it. What I trust less is what sits under the index. RSP is down 3.45 points relative to SPY over the month, and only four sector ETFs are above their 50-day. XLK and SMH are carrying everything. That setup can keep working, and it did again this week (SMH +2.33% vs. SPY on Friday alone). But if either one breaks, there is no rotation destination and VIX 14.81 won't stay here. My triggers: 10Y 5.00% (tagged and closed above once, so a second close above it is the signal to de-risk hard), VIX 16.50 (breached intraweek two weeks running; a close above it is the tell), oil $106.75 (Tuesday's failed-spike high). Plan: keep the tech/semis leadership trade but hedge it, size down across the rate-sensitives, and don't mistake a calm VIX for a calm market."*

**Cecil:** *"For the first time in two months I can read credit on current data, and credit is not stressed. HY OAS 270 bps, IG 78 bps, HY–IG 192. Spreads barely moved through a Fed hike, a 5% 10Y and a BOJ hike. LQD had a green week because buyers see value in investment-grade duration at 5%, and so do I. Quality credit at these yields is the most attractive margin of safety this board has shown all year. What would change my mind: HY OAS moving toward 300 bps after the October meeting. That would mean the hiking cycle is starting to hit refinancing math, and credit tends to be the last market to admit it. Until then: own quality, extend IG duration at the margin, and leave the equity multiple to the people who need it to go higher."*

---

## SOURCES & REFERENCES

- Yahoo Finance (yfinance 1.x, single fetch 2026-09-19): VIX, VIX3M, VVIX, SPY, RSP, 12 sector ETFs, Treasury yield proxies (^IRX/^FVX/^TNX), DXY (DX-Y.NYB), FX (EURUSD=X, JPY=X), crude (CL=F, BZ=F), gold (GC=F), copper (HG=F), Bitcoin (BTC-USD), bond ETFs (HYG, LQD)
- FRED (St. Louis Fed): VIXCLS (VIX cross-check, matched Yahoo on Wed 9/16 and Thu 9/17; Fri 9/18 not yet posted), DGS2 (2Y, Thu 9/17), DGS10/DGS3MO (CMT cross-checks), BAMLH0A0HYM2 / BAMLC0A0CM / BAMLEMCBPIOAS (ICE BofA HY / IG / EM corporate OAS, Thu 9/17), T10YIE (10Y breakeven, Fri 9/18)
- Federal Reserve: FOMC statement 2026-09-16 (federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm), Summary of Economic Projections; FOMC 2026 calendar (next meeting Oct 27–28)
- Bank of Japan: Statement on Monetary Policy 2026-09-18 (boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918a.pdf) — policy rate 1.25%, 7-2 vote
- BEA: PCE release schedule (August PCE, Sep 30 08:30 ET)
- CBOE: VIX methodology, VIX3M term structure; put/call ratio feed not wired (requires external update)
- NYSE/NASDAQ: advance/decline, new highs/lows, % above MAs — 66 days stale, refresh overdue
- Internal desk cross-references (2026-09-19 Grid A/B/C updates): wiki/utilities.md (XLU 52-week closing low, 10Y first close >5.00%), wiki/energy.md (WTI $106.75 spike, Aramco October cutoff), wiki/communication-services.md (XLC bull-trap / Brinkema), wiki/consumer-discretionary.md — sector closes cross-checked, exact match on XLU/XLE/XLC/XLY
- GitHub issues cross-referenced this run: #106 (Fed hike / 10Y 5.00% regime), #108 (utilities — 10Y >5.00%, XLU 52W low), #109 (energy — Aramco October European allocations cancelled) — no new issue opened by this run (no strict criterion met)

---

*Last updated by Saturday Research Crew: 2026-09-19 (single-agent run; all market data as of Fri 2026-09-18 closes; macro/facts.json regenerated from the same fetch)*
*Next update: Every Saturday 7:39 PM ET*
*Data sources: Yahoo Finance (yfinance), FRED, CBOE, Federal Reserve, Bank of Japan, BEA*
