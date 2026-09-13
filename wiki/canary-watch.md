# Wiki — Canary Watch

> **The Early Warning System for the Market Consciousness Orchestra**
>
> *"The canary does not predict the mine collapse. It simply dies first. Watch the canary."* — Marky

---

## VOLATILITY REGIME

| Metric | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| VIX | 15.84 | 14.53 | 15.28 | 🟢 **Normal** |
| VIX 20-Day MA | ~15.45 | — | — | — |
| VIX Trend | Up (+9.0% WoW) | — | — | — |
| Implied SPY Move (30D) | ~±4.5% | — | — | — |
| VVIX (VIX of VIX) | 91.28 | 84.42 | 90.90 | 🟡 **Yahoo ^VVIX live** |

> *Source note: VIX prints vary by vendor — discrepancies of ~2–3 pts are common across quote sources (delayed feeds, spot vs. VX futures, stale prints). Canonical reference: CBOE official close / FRED VIXCLS. FRED's most recently posted print at fetch time was 2026-09-10 (17.84), which matches the Yahoo ^VIX 2026-09-10 close (17.84) exactly — the two vendors are in lockstep through Thursday. FRED had not yet posted the Friday 2026-09-11 official close at fetch time (its usual one-business-day publish lag); the 15.84 close used throughout this dashboard is Yahoo Finance ^VIX (Fri 2026-09-11), and the Thu/Fri vendor agreement gives high confidence in the read.*

**Marky Interpretation:** Vol actually did something this week instead of round-tripping. VIX opened at 15.30, ground higher through the week's data flow, and **spiked to 17.84 on Wednesday** — a genuine breach of the 16.50 first-crack line I've had on this board for over a month, and the highest print since early August. Then it did what it's done all summer: gave most of it back, closing Friday at **15.84, +9.0% on the week** but well off the highs. VVIX told the same story louder — **91.28, +8.1% on the week**, with an intraweek spike to **102.66 Wednesday** that's the highest vol-of-vol reading on this dashboard in months. The driver is legible: hot core CPI (Thursday, September 11, +0.3% vs. +0.2% consensus) sealed September hike odds at **~87–90%**, the 10Y is sitting 2.5 bps under its own 5.00% psychological line, and WTI just printed its first-ever $100+ settle. That's three genuine macro stress inputs converging in one week, and vol still only spent one session above its own first-crack line before retreating. Implied 30-day SPY move ticked up to **~±4.5%** from ~±4.2%. My lines are unchanged: 16.50 was tagged and breached intraweek for the first time this cycle (still closed back under it), 20 is the regime question, 25 is the alarm. This is the closest the vol market has come to confirming the stress building everywhere else on this board — it's not there yet, but it flinched.

---

## YIELD CURVE

| Maturity | Yield | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| 13-Week (T-Bill) | 3.913% | +0.153% | +0.183% | Front end pricing in a near-certain hike |
| 2-Year | 4.20% (FRED DGS2, Thu 8/27 — **stale, 15 days**; desk composites reading meaningfully higher post-CPI) | — (stale) | — | Hike repricing far ahead of the stale proxy |
| 5-Year | 4.791% | +0.241% | +0.406% | Medium-term rates at a fresh cycle high |
| **10-Year** | **4.975%** | **+0.185%** | **+0.291%** | **Fresh 52-week high, 2.5 bps from the 5.00% psychological line** |
| **10Y–2Y Spread** | **~+78 bps** (stale 2Y — treat as a ceiling, real spread is almost certainly narrower) | — | — | **Positive, likely much narrower live** |
| **10Y–5Y Spread** | **~+18.4 bps** | — | — | **Positive, narrowing (was +24.0 bps)** |
| **10Y–3M Spread** | **~+106 bps** | — | — | **Positive / widened from +103** |

**Ophelia Interpretation:** The stress line this dashboard flagged breaking last week didn't just hold — it kept climbing. The 10Y closed **4.975% Friday**, a fresh 52-week high and now sitting **just 2.5 bps under the 5.00% level** our own real-estate desk called "the crisis line" in Saturday's real-estate.md update. The proximate cause is the same one driving vol and oil: **August core CPI printed +0.3% against a +0.2% consensus** — hot enough to push September FOMC hike odds to **~87–90%** (up from ~60% just last week) and keep BOJ odds pinned at **~84–87%** into their own meeting three days later. That's the fastest back-to-back repricing this dashboard has tracked all year: NFP moved the market from ~49% to ~60% two weeks ago, and CPI just moved it another ~27–30 points in a single session. The curve shape is still healthy — no inversion anywhere, 10Y–3M widened again to +106 bps — but the 10Y–5Y spread compressed to +18.4 bps from +24.0, a genuine bear-flattening signal at the long end even as the front end races to catch up. The 2Y proxy (FRED DGS2, 4.20%) is now **fifteen days stale** and increasingly detached from reality; treat the 10Y–2Y spread of ~78 bps as a hard ceiling, not a usable read — it is almost certainly overstating curve steepness by a wide margin at this point.

**Yield Curve Regime:** 🟡 **Positive but stressed** — shape intact, but the level conversation this dashboard opened last week just escalated. The 10Y is one ordinary session away from a round number with real psychological weight, and the September 15–16 FOMC is now the decision point, not a distant gate.

---

## CREDIT SPREADS

> *Credit spread data is sourced from external market data feeds (Bloomberg, ICE, FRED). Live spreads are not available via Yahoo Finance. Values below are last known (as of 2026-07-15 — now **58 days old**) and require external feed updates. HYG/LQD price action provides a real-time proxy.*

| Spread | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| HY–IG Spread | ~+220 bps (stale) | — | — | 🟡 **Unconfirmed — cannot verify vs. the 250 bps trigger** |
| EM Sovereign | ~+380 bps (stale) | — | — | 🟡 **Elevated but stable (stale)** |
| Investment Grade CDS | ~+55 bps (stale) | — | — | 🟡 **Last known tight (stale)** |
| **HYG Price** | **$78.60** | **$79.16** | **$79.51** | **🔴 Second straight red week** |

**Cecil Interpretation:** Credit kept moving in the direction it started last week, and the pace didn't accelerate — which is itself informative. HYG closed **-0.71% to $78.60** and LQD closed **-1.10% to $104.32**, both **second straight red weeks**, arriving in the same week the 10Y closed within spitting distance of 5.00% and hike odds jumped another ~27–30 points on hot CPI. A cumulative ~1.4% pullback in HYG and ~1.9% in LQD across two weeks of the sharpest rate repricing this cycle is still a scratch by any historical standard — nothing here resembles spread widening that would confirm the 250 bps trigger. But I can no longer make that call with a straight face: **the external HY–IG snapshot is now 58 days old**. In that window we have watched the 10Y break 4.75%, then close in on 5.00%; oil clear $90, then print its first $100+ settle; a yen carry unwind; and now a hawkish CPI surprise on top of a hawkish NFP surprise. Two consecutive proxy-implied red weeks in exactly the conditions that should widen spreads is the closest thing to a real signal this dashboard has had in two months, and we are reading it through a two-month-old lens.

**Credit Regime:** 🟡 **Watch, unconfirmed** — the proxy has now cracked for two straight weeks in a rate-stress environment. The external gauge behind it is 58 days stale and is the single largest blind spot left on this board.

---

## MARKET BREADTH

> *Breadth data (advance/decline, new highs/lows) is sourced from external market data feeds (NYSE, NASDAQ). Live breadth is not available via Yahoo Finance. Values below are last known (as of 2026-07-15 — now **58 days old**) and require external feed updates.*

| Metric | Current | 5D Avg | 20D Avg | Regime |
|---|---|---|---|---|
| Advance/Decline Ratio | ~1.15 (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| New 52-Week Highs | ~185 (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| New 52-Week Lows | ~42 (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| S&P 500 % Above 50D MA | ~68% (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| S&P 500 % Above 200D MA | ~72% (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| Equal-Weight SPY vs. Cap-Weight SPY | -0.3% (stale) | — | — | 🟡 **Neutral (stale)** |

**Marky Interpretation:** Still flying on a **58-day-old snapshot**, and the live tape is giving fewer reasons for comfort than last week's. SPY closed **-0.77% to $764.29**, its second straight down week, and participation narrowed further: only **four of twelve sectors beat the index** this week (XLE +2.45 vs. SPY, XLC +1.27, SMH +1.03, XLK +0.97) versus five last week. Healthcare's reversal is the tell — XLV was flat-to-positive vs. SPY last week and is this week's **worst relative performer** (-2.79% vs. SPY) on a genuine fundamentals shock (drug-trial failure cluster, our own issue #98 today), while the rate-sensitive complex (XLI, XLB, XLY, XLU) all stayed in outflow for a second week running. That is a narrowing-leadership tape with real fundamental and rate-driven casualties on both sides, sitting on top of a bond market within 2.5 bps of a round-number ceiling. I do not need the real breadth print to tell you this doesn't look like a healthy-breadth week; I need it to tell me whether "narrow" has become "fragile."

**Breadth Regime:** 🟡 **Neutral, deteriorating bias** (stale) — second red index week, narrower live leadership than last week, and the two sectors that flipped (healthcare into outflow, energy staying inflow on the commodity not the equity) both carry real catalysts. Confirmation is now 58 days overdue.

---

## SECTOR CORRELATION MATRIX

*30-day rolling correlation of daily returns vs. SPY*

| Sector | ETF | vs. SPY Correlation | 1W Ago | Regime |
|---|---|---|---|---|
| 🛍️ Consumer Discretionary | XLY | **0.637** | 0.526 | 🔥 **High beta (rising)** |
| 🖥️ Technology | XLK | **0.646** | 0.795 | 🔥 **High beta (falling)** |
| ⚙️ Industrials | XLI | **0.611** | 0.777 | 🔥 **High beta (falling)** |
| 🏦 Financials | XLF | **0.602** | 0.571 | 🔥 **High beta** |
| 📡 Communication Services | XLC | **0.522** | 0.261 | 🟢 **Pro-cyclical (re-coupling fast)** |
| 🏠 Real Estate | XLRE | **0.503** | 0.121 | 🟢 **Pro-cyclical (re-coupling fast)** |
| ⛏️ Materials | XLB | **0.422** | 0.331 | 🟡 **Moderate** |
| 💻 Semiconductors | SMH | **0.422** | 0.682 | 🟡 **Moderate (decoupling)** |
| 🏥 Healthcare | XLV | **0.250** | -0.028 | 🟡 **Sign flip: defensive → pro-cyclical** |
| 🍞 Consumer Staples | XLP | **0.173** | -0.109 | 🟡 **Sign flip: defensive → pro-cyclical** |
| ⚡ Utilities | XLU | **0.070** | 0.076 | 🟡 **Weakly coupled (flat)** |
| ⛽ Energy | XLE | **-0.426** | -0.353 | 🔴 **Inverse (deepening)** |

**Ophelia Interpretation:** Two sectors crossed zero this week — **Healthcare (-0.028 → 0.250)** and **Consumer Staples (-0.109 → 0.173)** — both moving from negative to positive correlation with the index. That is the *opposite* direction of this dashboard's formal alert criterion (a flip from positive to negative), so it does not trigger a new issue, but it is the more interesting story: **the two classic defensive sectors both lost their diversification benefit in the same week**, for two different reasons. Healthcare's flip is fundamentals-driven — the drug-trial-failure and medtech-execution cluster (issue #98) hit XLV hard enough that it started moving with the broad tape's stress rather than against it. Staples' flip is more likely a rates story — a defensive sector with long-duration-like valuation characteristics re-coupling to a market where one variable (the front end) is increasingly setting the tone for everyone. Meanwhile the **high-beta trio that led correlation last week — XLK, XLI, SMH — all fell** (0.795→0.646, 0.777→0.611, 0.682→0.422): mega-cap tech and industrials didn't decouple from the market's direction so much as decouple from each other's magnitude, consistent with the idiosyncratic name-level dispersion inside tech and semis this week (AMD/INTC up double digits, NVDA/MU down) even as the sector-level story stayed intact. **XLE remains the board's sole clean inverse** and deepened further to -0.426 — oil's equities still are not trading the commodity's move.

**The key insight:** correlation dispersion is not narrowing uniformly anymore — it's **redistributing**. Defensive sectors are gaining beta (bad for diversification) while some high-beta names are losing correlation to each other (idiosyncratic stock-picking opportunity inside a macro-dominated tape). Both can be true at once, and both point toward a market where rates are the organizing variable but stock selection inside sectors still matters.

**Alert:** None on the strict flip criterion — no sector crossed from positive to negative this week (Energy's more-negative move doesn't count; it was already negative). Watch item: Healthcare's and Staples' flips from negative to positive correlation both reduce the number of true diversifiers left on this board to effectively one (XLU, barely) plus Energy's inverse.

---

## SECTOR ROTATION FLOW

*1-Day / 1-Week / 1-Month performance vs. SPY*

| Sector | ETF | 1D vs. SPY | 1W vs. SPY | 1M vs. SPY | Rotation Signal |
|---|---|---|---|---|---|
| ⛽ Energy | XLE | -0.53% | +2.45% | +7.72% | 🟢 **Inflow** |
| 📡 Communication Services | XLC | +0.13% | +1.27% | +2.01% | 🟢 **Inflow** |
| 💻 Semiconductors | SMH | +0.62% | +1.03% | +0.05% | 🟢 **Inflow** |
| 🖥️ Technology | XLK | +0.47% | +0.97% | +1.66% | 🟢 **Inflow** |
| 🏦 Financials | XLF | -0.18% | -0.70% | -0.14% | 🟡 **Neutral** |
| 🍞 Consumer Staples | XLP | -0.50% | -0.65% | -0.73% | 🟡 **Neutral** |
| 🏠 Real Estate | XLRE | +0.01% | -0.39% | -0.68% | 🟡 **Neutral** |
| ⚡ Utilities | XLU | -1.16% | -0.84% | -2.03% | 🔴 **Outflow** |
| 🛍️ Consumer Discretionary | XLY | +0.04% | -0.93% | -4.45% | 🔴 **Outflow** |
| ⚙️ Industrials | XLI | +0.21% | -0.89% | -6.36% | 🔴 **Outflow** |
| ⛏️ Materials | XLB | -0.48% | -2.08% | -3.49% | 🔴 **Outflow** |
| 🏥 Healthcare | XLV | -1.03% | -2.79% | -0.76% | 🔴 **Outflow** |

**Ophelia Interpretation:** The flow board reshuffled its worst performer without changing its overall shape. **Healthcare is this week's clearest outflow** (-2.79% 1W), a sharp reversal from last week's neutral read, driven entirely by the drug-trial-failure/medtech cluster rather than by rates — a genuine fundamentals story sitting inside a macro-dominated tape. **Energy remains the clearest inflow** (+2.45% 1W, +7.72% 1M) on WTI's move to a first-ever $100+ settle, even as its correlation to SPY deepens further negative — the sector is still being bought for the commodity, not for beta, exactly as it has been for a month. **Communication Services, Semiconductors, and Technology all posted mild inflows**, consistent with growth's continued resilience into a hawkish rate backdrop. The rate-sensitive trio that has been in outflow for weeks — **Industrials (-6.36% 1M), Consumer Discretionary (-4.45% 1M), Materials (-3.49% 1M)** — stayed there, joined this week by **Utilities (-2.03% 1M)**, which lost its reclaimed floor and posted a mini death-cross per today's utilities.md update.

**The risk:** the 1M column is now showing five sectors with clearly negative multi-week trends (XLI, XLY, XLB, XLU, and now XLV) against only four with clearly positive ones (XLE, XLC, XLK, and marginally SMH) — a rotation board that has stopped being "growth vs. rate-sensitives" and started including a fundamentals-driven defensive-sector casualty as well. If the September 15–16 FOMC delivers the hike now priced at ~87–90%, the rate-sensitive outflow has every reason to extend; if healthcare's binary risk (the Olpasiran OCEAN(a)-Outcomes readout flagged by today's healthcare.md) resolves negatively too, this board could see its first six-sector outflow cluster of the cycle.

---

## CROSS-ASSET SIGNALS

| Asset | Level | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| DXY (US Dollar Index) | ~99.60 (stale — external feed, 58 days; other desks reading ~99.12 informally this week) | — | — | 🟡 **Needs refresh — likely lower than the stale print** |
| EUR/USD | 1.1601 | -0.24% | +0.47% | 🟡 **Flat, holding the range** |
| USD/JPY | 153.554 | -1.35% | -3.52% | 🔴 **Extending below 160 — carry unwind continuing** |
| WTI Crude | $100.05 | +9.37% | +20.25% | 🔴 **First-ever $100+ settle — RED trigger crossed** |
| Gold | $4,408.90 | -0.47% | +0.59% | 🟡 **Flat, debasement bid still paused** |
| Copper | $6.548/lb | -0.74% | -0.97% | 🟡 **Growth signal softening slightly** |
| Bitcoin | $77,174 (Fri close) | -3.14% | +21.43% | 🟡 **Extending the pullback from the August melt-up** |
| HY Bonds (HYG) | $78.60 | -0.71% | -1.14% | 🔴 **Second straight red week** |
| IG Bonds (LQD) | $104.32 | -1.10% | -1.58% | 🔴 **Second straight red week, duration pain building** |
| TIPS Breakeven (10Y) | ~2.45% (stale — external feed) | — | — | 🟡 **Inflation expectations stable (stale)** |

> *DXY index not available via Yahoo Finance; EUR/USD and USD/JPY used as cross-asset proxies. DXY last known ~99.60 (est., 2026-07-15, now 58 days stale); this week's sector desks (materials.md) informally cited ~99.12 from their own sourcing — that figure is NOT yahoo-verified and is not carried into macro/facts.json, but it is directionally consistent with continued dollar softness. Bitcoin row uses the Friday 2026-09-11 close ($77,174) for the Friday-to-Friday convention.*

**Ophelia Interpretation:** The board's most dangerous line finally crossed. **WTI closed at $100.05, +9.37% on the week** — this dashboard's own $90 trigger, cleared a week ago, is now a memory; the **$100 RED trigger line** is crossed outright, on the back of Houthi advances toward a second Bab el-Mandeb chokepoint position and no OPEC+ supply response (they held October policy unchanged on schedule September 6). **USD/JPY extended its break** to **153.554, -1.35% on the week and -3.52% on the month**, continuing the carry-unwind move this dashboard flagged two weeks ago rather than stabilizing — the pair is now nearly 6.5 points below the 160 intervention line it held for months. Credit confirmed its own trend: **HYG and LQD both posted second straight red weeks**, now down a cumulative ~1.4%/1.9% since the rate breakout began. Gold and copper both went flat-to-slightly-down — neither the debasement trade nor the growth-commodity trade is adding conviction into a week that gave the hawks a CPI beat, an oil shock, and a fresh 52-week high in the 10Y simultaneously. Bitcoin's pullback (-3.1% on the week) continues to look like digestion of the August melt-up rather than a new signal.

**The risk:** this board is now stacking **three** genuinely dangerous inputs at once instead of two — a yen carry unwind that has not found a floor, an oil shock that just cleared its red trigger, and a bond market camped 2.5 bps under a round-number ceiling — against a credit market now confirmed red for two straight weeks. The September 15–16 FOMC arrives with hike odds at ~87–90%, already close to fully priced; the actual risk into that meeting is less "will they hike" and more "what happens to oil, the yen, and the 10Y if they hike AND signal more to come."

---

## CANARY WATCH TRIGGER BOARD

| Signal | Status | Trend | Trigger Level |
|---|---|---|---|
| VIX Regime | 🟢 Normal (breached 16.50 intraweek, closed back under) | Up (+9.0% WoW), 17.84 intraweek high | 🟡 >20 | 🔴 >25 |
| Yield Curve | 🟡 Positive but level-stressed | 10Y 4.975%, 2.5 bps from 5.00% (10Y–3M +106) | 🟡 <0 (inverted) | 🔴 <-50 bps |
| Credit Spreads | 🟡 Watch, unconfirmed (stale, 58d) | HYG/LQD 2nd straight red week | 🟡 HY–IG >250 bps | 🔴 >350 bps |
| Market Breadth | 🟡 Neutral, deteriorating bias (stale, 58d) | 2nd red index week, narrower 4/12 leadership | 🟡 <50% above 50D MA | 🔴 <40% |
| Sector Rotation | 🟡 Rate-sensitives + healthcare in outflow | XLI/XLY/XLB/XLU/XLV all negative 1M vs. SPY | 🟡 XLK -5% vs. SPY | 🔴 XLK -10% |
| DXY | 🟡 Needs refresh | USD/JPY extending below 160; desk read stale | 🟡 >102 | 🔴 >105 |
| Geopolitics | 🔴 **Oil >$100 RED trigger crossed** | WTI $100.05 (+9.4% WoW); Bab el-Mandeb 2nd chokepoint, carry unwind live | 🟡 Oil >$90 | 🔴 Oil >$100 |
| Credit Risk | 🟡 Softening, 2nd week | HYG/LQD both red again | 🟡 CDS widening | 🔴 Bank stress |
| Overall Risk | 🟡 **CAUTION (escalating)** | — | — | — |

**Weekly Narrative — Overall Assessment:** This was the week the board's dashboard-native trigger lines started crossing outright, even as the formal alert criteria for a new GitHub issue stayed unmet. The ledger: (1) **WTI printed its first-ever $100+ settle**, closing +9.37% on the week to $100.05 — the board's own $100 RED geopolitics trigger, carried as "the next stop" for a month, is now crossed (already covered by today's issue #100 from the energy desk); (2) the **10Y closed at 4.975%, a fresh 52-week high just 2.5 bps under the 5.00% psychological line**, on the back of hot August core CPI (+0.3% vs. +0.2% consensus) that pushed September hike odds to ~87–90%; (3) **VIX breached its own 16.50 first-crack line intraweek for the first time this cycle** (17.84 Wednesday) before closing back under it at 15.84, +9.0% on the week; (4) **credit confirmed a trend rather than a one-off** — HYG and LQD both posted second straight red weeks; (5) **USD/JPY extended its carry-unwind break**, falling another 1.35% to 153.554, now nearly 6.5 points clear of the old 160 line; (6) **two defensive sectors flipped from negative to positive correlation with SPY** — Healthcare and Consumer Staples both lost their diversification benefit, for different reasons (a fundamentals shock in healthcare's case, likely a rates story in staples'); (7) **healthcare became the week's clearest sector outflow** (-2.79% vs. SPY) after a drug-trial-failure and medtech-execution cluster, a genuinely idiosyncratic addition to what has otherwise been a rates-driven rotation story; (8) growth held up — Technology, Semiconductors, and Communication Services all posted mild inflows, and the correlation-matrix dispersion inside tech (AMD/INTC sharply up, NVDA/MU down) suggests stock-picking is still alive underneath the macro trade; (9) market breadth narrowed further (4 of 12 sectors beat SPY vs. 5 last week) on a second straight red index week; (10) the credit and breadth external gauges are now **58 days stale**, a governance gap that has now persisted through three consecutive weeks of genuine regime escalation.

The fragilities: (1) the 10Y is one ordinary up-day away from testing 5.00% outright, and the September 15–16 FOMC is the next scheduled catalyst with hike odds already near-fully priced — the tail risk is a hike *plus* hawkish forward guidance, not the hike itself; (2) a yen carry unwind that has now extended for three straight weeks without finding a floor raises the odds of a disorderly move, not an orderly one; (3) oil above $100 with the 10Y near 5.00% simultaneously removes two of the market's few remaining "this isn't that bad yet" arguments; (4) credit's second consecutive red week is still small in absolute terms, but the trend, not the level, is now the story, and the stale external gauge means the market is flying blind on the one number that would confirm or deny a real credit event; (5) VIX's continued failure to sustainably confirm the stress building in rates, credit, oil, and FX — despite an intraweek breach of its own first-crack line — is either a genuinely calm equity options market or a market that has not yet been forced to price the full CPI-plus-oil-plus-FOMC combination; (6) two defensive-sector correlation flips in one week reduce the diversification value of this book at almost the same moment cross-asset stress is rising, a bad combination for anyone using sector rotation as a hedge.

**The Canary Watch verdict:** 🟡 **CAUTION, escalating** — held for a third straight week, but the internal trigger board just logged its first RED cross (Oil >$100) since this dashboard began tracking it, and two of the three yellow lines (10Y near 5.00%, VIX's 16.50 breach) both moved closer to their own red thresholds. None of the four strict criteria for a new Canary Watch issue were met this run (VIX stayed under 20, the curve remains positive-sloped, credit widening above 250 bps cannot be confirmed on stale data, and no sector correlation flipped from positive to negative — Healthcare and Staples flipped the other direction). The oil, CPI, and consumer-confidence catalysts behind this week's moves are already tracked under issues #97, #98, #99, and #100 opened by today's sector desks; this run adds no new issue to avoid duplicating that coverage. Watch: (1) September FOMC September 15–16 — hike odds ~87–90%, the highest conviction level this dashboard has recorded all year; (2) BOJ September 17–18, hike odds 84–87%, directly relevant to the ongoing yen unwind; (3) whether the 10Y tests or breaks 5.00% before or immediately after the FOMC; (4) WTI — does $100 hold as support or does the next leg test $105+; (5) USD/JPY — does the carry unwind stabilize near 150 or accelerate through it; (6) the credit and breadth external refresh, now 58 days overdue and the single largest remaining blind spot on this board; (7) whether Healthcare's correlation flip and outflow reverse once the binary trial-readout risk (Olpasiran OCEAN(a)-Outcomes) resolves.

---

## COUNCIL READ — What This Means for Monday

**Ophelia:** *"Three lines moved against us in the same week: the 10Y closed within 2.5 bps of 5.00%, oil crossed its own $100 red trigger, and the yen carry unwind extended for a third straight week without stabilizing. My stance holds at 'defensive and confirmed' — cash allocation stays at 25–30%, and I am not adding rate-sensitive exposure into a live FOMC where hike odds are already north of 87%. The new wrinkle is healthcare: it flipped from a defensive, negatively-correlated sector to a positively-correlated one in a single week, on a genuine fundamentals shock rather than a rates story. That reduces the number of true portfolio diversifiers left on this board to effectively Utilities (barely) and Energy's inverse — everything else is now moving with the tape to varying degrees. The 2Y proxy is fifteen days stale and increasingly useless for reading the real curve shape; I want that refreshed before I trust any 10Y–2Y number on this dashboard again. Credit's second red week is still small, but it is now a trend, and the 58-day-stale gauge behind it is no longer a caveat, it's a liability heading into FOMC week."*

**Marky:** *"The tape gave vol every reason to break and it took the bait for exactly one session. VIX tagged 17.84 Wednesday — a real breach of my 16.50 line for the first time this cycle — then handed almost all of it back to close at 15.84. That's either genuine conviction that the Fed has this handled, or a market that hasn't yet processed CPI-plus-oil-plus-FOMC as one combined story. What I trust more than the VIX print: growth kept working. XLK, SMH, and XLC all posted inflows this week even as the rate-sensitive complex extended its outflow and healthcare joined it on a totally separate catalyst. Inside tech, the dispersion is wide — AMD and INTC ripping, NVDA and MU fading — which tells me stock-picking still matters underneath the macro trade. My triggers: VIX 16.50 (breached intraweek, held on a closing basis — watching for a second, sustained test), 10Y 5.00% (the next real line, 2.5 bps away), oil $100 (cleared — next stop is a genuine supply-shock read above $105). Plan: keep the growth/energy inflow trade on, size down further ahead of the FOMC, and treat any 10Y close above 5.00% as the signal to de-risk hard."*

**Cecil:** *"The accountant's ledger: credit did exactly what it should when the discount rate keeps climbing and oil adds a second inflation input — it went red for a second straight week. HYG -0.71%, LQD -1.10%, cumulative moves of roughly -1.4% and -1.9% since the rate breakout began seven weeks ago. Still not a crisis. Still directionally correct. What's changed is my patience with the 58-day-stale external gauge: we have now lived through an oil trigger crossing from yellow to red, a yield-curve level stress deepening toward a round number, a persistent carry unwind, and two consecutive hawkish macro surprises (NFP, then CPI) — all on a credit read from before any of it happened. This is no longer a footnote for the dashboard header; it's the single biggest open item on this desk heading into the busiest macro week of the quarter. Own quality, keep the margin of safety, and remember that bonds moved first on the way into this stress and credit is historically the last market to admit what the others already know."*

---

## SOURCES & REFERENCES

- Yahoo Finance (yfinance): VIX, VVIX, SPY, sector ETFs, Treasury yield proxies (^IRX/^FVX/^TNX), FX (EURUSD=X, JPY=X), crude (CL=F), gold (GC=F), copper (HG=F), Bitcoin (BTC-USD), bond ETFs (HYG, LQD)
- FRED (St. Louis Fed): VIXCLS (VIX cross-check, confirmed matching Yahoo through Thu 2026-09-10; Fri 2026-09-11 not yet posted at fetch time), DGS2 (2-Year cross-check, 15 days stale)
- CBOE: VIX methodology, VIX futures term structure
- Federal Reserve: Yield curve data, Fed funds rate, FOMC statements and minutes
- CME FedWatch: September FOMC hike pricing (~60% last week -> ~87–90% post-CPI)
- ICE/BofA: Credit spread indices (ICE BofA US Corporate, High Yield) — 58 days stale, refresh overdue
- NYSE/NASDAQ: Advance/decline data, new highs/lows — 58 days stale, refresh overdue
- Internal desk cross-references: wiki/tech.md, wiki/industrials.md, wiki/real-estate.md, wiki/energy.md, wiki/healthcare.md, wiki/consumer-discretionary.md, wiki/materials.md, wiki/utilities.md (all 2026-09-12 Grid A/B/C updates) for CPI/FOMC framing, the 5.00% "crisis line" flag, the WTI $100 print, and the healthcare trial-failure cluster
- GitHub issues cross-referenced this run: #97 (hot core CPI / macro catalyst), #98 (drug trial failure + medtech cluster), #99 (UMich consumer-confidence shock), #100 (WTI $100.05 first-ever settle) — no new issue opened by this run to avoid duplicating coverage

---

*Last updated by Saturday Research Crew: 2026-09-12 (single-agent run; all market data as of Fri 2026-09-11 closes)*
*Next update: Every Saturday 7:39 PM ET*
*Data sources: Yahoo Finance (yfinance), CBOE, Federal Reserve, FRED, market data feeds*
