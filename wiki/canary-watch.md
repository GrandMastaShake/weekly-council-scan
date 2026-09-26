# Wiki — Canary Watch

> **The Early Warning System for the Market Consciousness Orchestra**
>
> *"The canary does not predict the mine collapse. It simply dies first. Watch the canary."* — Marky

> **Truth layer:** every macro number on this page equals `macro/facts.json` (generated 2026-09-25, same fetch, commit e8cedef). Week ending Friday 2026-09-25 closes.

---

## VOLATILITY REGIME

| Metric | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| VIX | 14.87 | 14.81 | 15.21 | 🟢 **Normal** |
| VIX 20-Day MA | ~15.68 | — | — | — |
| VIX Trend | Flat (+0.41% WoW); intraweek high 16.57 Thu 9/24, low 14.12 Wed 9/23 | — | — | — |
| VIX3M (term structure) | 17.93 (VIX/VIX3M 0.83, contango) | 18.24 | 17.99 | 🟢 **Contango held all week (peak ratio 0.85 on 9/24)** |
| Implied SPY Move (30D) | ~±4.3% | ~±4.3% | — | — |
| VVIX (VIX of VIX) | 87.84 | 87.38 | 85.24 | 🟢 **Steady (intraweek 92.94)** |
| Put/Call Ratio | n/a | — | — | ⚪ **CBOE feed not wired — requires external update** |

> *Source note: VIX prints vary by vendor — discrepancies of ~2–3 pts are common across quote sources (delayed feeds, spot vs. VX futures, stale prints). Canonical reference: CBOE official close / FRED VIXCLS. This week the Friday close was cross-checked directly against the **CBOE official daily history file (VIX_History.csv): Fri 2026-09-25 close 14.87**, an exact match for Yahoo ^VIX (14.87). The CBOE file also matches Yahoo on the week's high (16.57, Thu 9/24). FRED VIXCLS had posted through Mon 9/22 at fetch time (9/21 14.87, 9/22 14.21), both exact matches for Yahoo; it also now confirms last week's published Friday close (2026-09-18: 14.81).*

**Marky Interpretation:** The 10Y put in its first weekly close above 5.00% and the VIX finished the week **up six cents**. VIX closed Friday at **14.87 (+0.41% WoW)**, below its 20-day average (~15.68) and under where it sat a month ago (15.21). It did try: the Thursday spike to **16.57** was the **third straight week that 16.50 was breached intraday and not held on a close**. VIX3M eased to 17.93, the VIX/VIX3M ratio peaked at **0.85** on Thursday and ended at **0.83**, and the term structure never came close to inverting. VVIX held at **87.84**. Implied 30-day SPY move is unchanged at **~±4.3%**. My lines are unchanged: 16.50 is the tell on a close, 20 is the regime question, 25 is the alarm. Last week I said the worry was the options market being calm while bonds sat at 5.00%. This week bonds went to **5.18%** and the options market stayed calm. That gap is now the single largest disagreement on this board.

---

## YIELD CURVE

| Maturity | Yield | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| 13-Week (T-Bill) | 4.070% | +0.092% | +0.380% | Front end leaning further into an October hike |
| 2-Year | 4.87% (FRED DGS2, Thu 9/24 — 1 business day lag) | +0.20% (vs. FRED Thu 9/17 4.67%) | +0.68% (vs. 4.19% on 8/26) | **+68 bps in a month — the front end is doing the hiking** |
| 5-Year | 5.007% | +0.151% | +0.626% | **Belly through 5.00% (closes 5.025% Thu, 5.007% Fri)** |
| **10-Year** | **5.184%** | **+0.186%** | **+0.520%** | **Three straight closes above 5.00% (5.114 / 5.162 / 5.184); intraweek high 5.230% Fri** |
| **10Y–2Y Spread** | **~+31 bps** (Fri 10Y vs. Thu 2Y; same-day FRED Thu: 5.18 − 4.87 = +31 bps) | -2 bps (was ~+33) | — | **Positive, flat** |
| **10Y–5Y Spread** | **~+17.7 bps** | +3.5 bps (was +14.2) | — | **Long end re-steepening — term premium back** |
| **10Y–3M Spread** | **~+111 bps** | +9 bps (was +102) | — | **Positive, widening** |

> *2Y source: FRED DGS2 (latest posted print Thu 2026-09-24, one business day lag), carried in macro/facts.json as `fred:DGS2` with its own as_of. ^IRX is a discount-basis T-bill yield; FRED's constant-maturity 3M (DGS3MO 4.24% Thu) runs ~17 bps higher, so a CMT-basis 10Y–3M would read ~+94 bps. This page and facts.json use ^IRX for series continuity.*

**Ophelia Interpretation:** Last week's watch item was "whether the 10Y posts a *second* close above 5.00% and holds it." It posted three. The 10Y spent Monday and Tuesday just under the line (4.963%, 4.968%), then broke through on Wednesday (**5.114%**) and kept going (**5.162%** Thu, **5.184%** Fri), with an intraweek high of **5.230%** on Friday. That is **+18.6 bps on the week and +52 bps in a month**, and it is the first *weekly* close above 5.00% of this cycle (issue #113 tracks the regime trigger and the 5Y auction tail). The shape of the move matters more than the level. Last week was bear-*flattening*: the front end and belly doing the hiking, the long end dragged along. This week the long end led. **10Y–5Y re-steepened from +14.2 to +17.7 bps** and **10Y–3M widened from +102 to +111 bps**, while 10Y–2Y was roughly flat (~+31). The 2Y is still climbing (**4.87%, +20 bps WoW, +68 bps in a month**), so this is not the market pricing cuts. It is the market demanding more term premium to hold duration during a hiking cycle. The **5Y also closed above 5.00%** (5.025% Thu, 5.007% Fri).

**Yield Curve Regime:** 🟡 **Positive, bear-steepening at the long end under a live hiking cycle.** No inversion anywhere. The next gates are unchanged: **August PCE (Sep 30)** and the **Oct 27–28 FOMC**.

---

## CREDIT SPREADS

> *Credit spreads are **live from FRED** (ICE BofA OAS series, latest posted print Thu 2026-09-24, one business day lag). HYG/LQD Friday closes remain the real-time proxy.*

| Spread | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| HY OAS (ICE BofA US HY, BAMLH0A0HYM2) | 280 bps | 270 bps | 267 bps | 🟡 **Above 250 all year; +10 bps WoW — first real widening since this series went live on the page** |
| IG OAS (ICE BofA US Corp, BAMLC0A0CM) | 79 bps | 78 bps | 80 bps | 🟢 **Tight, near YTD lows** |
| **HY–IG Spread** | **201 bps** | 192 bps | 187 bps | 🟢 **Below the 250 bps trigger, drifting up** |
| EM Corporate OAS (BAMLEMCBPIOAS) | 134 bps | 137 bps | 140 bps | 🟢 **Contained** |
| **HYG Price** | **$77.86** | **$78.53** | **$79.90** | 🟡 **Fourth straight red week (-0.85%)** |
| **LQD Price** | **$103.21** | **$104.70** | **$106.78** | 🟡 **Duration pain (-1.42% WoW, -3.34% 1M)** |

**Cecil Interpretation:** Last week I said the thing that would change my mind was HY OAS moving from 270 toward 300 bps. It moved **10 bps in that direction, to 280**, and the HY–IG gap crossed **200 bps (201)** for the first time since this page went back to live data. IG barely moved (**78 → 79 bps**) and EM actually tightened (137 → 134). So this is a *high-yield* move, not a broad credit repricing, and 280 is still inside this cycle's range. HYG's fourth straight red week (**-0.85%**) is now more than a rounding error, and LQD gave back last week's duration bid and more (**-1.42%**) as the 10Y rose 19 bps. Most of LQD's loss is rate duration; with IG OAS +1 bp, the credit component is close to zero. My read: credit is still fine, but the direction changed this week, and I want to see the next two prints before I call it noise.

**Credit Regime:** 🟢 **Contained, widening at the margin in HY.** HY–IG 201 bps against a 250 bps trigger. The watch question: does HY OAS keep climbing toward 300 into PCE and the October FOMC?

---

## MARKET BREADTH

> *Breadth data (advance/decline, new highs/lows, % of S&P members above MAs) is sourced from external feeds (NYSE, NASDAQ) not available via Yahoo Finance. Values marked stale are last known as of 2026-07-15 — now **72 days old** — and require external feed updates. Rows marked live are computed from this run's Yahoo fetch as proxies.*

| Metric | Current | 5D Avg | 20D Avg | Regime |
|---|---|---|---|---|
| Advance/Decline Ratio | ~1.15 (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| New 52-Week Highs | ~185 (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| New 52-Week Lows | ~42 (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| S&P 500 % Above 50D MA | ~68% (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| S&P 500 % Above 200D MA | ~72% (stale) | — | — | 🟡 **Unconfirmed (stale)** |
| Equal-Weight (RSP) vs. Cap-Weight (SPY), 1W | **-1.82 pts** (RSP -0.56% vs. SPY +1.27%) — live | — | 1M: **-5.64 pts** | 🔴 **Narrower than last week (-0.86 / -3.45)** |
| Sector ETFs above own 50D MA (live proxy) | **5 of 12** (XLK, XLE, XLV, XLC, SMH) | — | — | 🔴 **Weak participation** |

**Marky Interpretation:** SPY snapped a three-week losing streak, **+1.27% to $771.35**, and the average stock went down. **RSP fell -0.56%**, so the equal-weight index lagged cap-weight by **1.82 points in a week** and **5.64 points in a month**, both wider than last week's -0.86 / -3.45. That is the whole week in one line: **SMH +5.86%, XLK +3.52%**, and most of the rest red. Sectors above their own 50-day ticked up to **5 of 12** (XLC reclaimed; XLK, SMH, XLV and XLE held), but every rate-sensitive group (XLU, XLRE, XLF, XLY, XLB, XLI, XLP) is below it. SPY sits **+1.28% above its 50-day**. An index can rise on two sectors for a long time. It is not a healthy way to do it with a 10Y at 5.18%.

**Breadth Regime:** 🔴 **Narrowing (live proxies), official gauges stale 72d.**

---

## SECTOR CORRELATION MATRIX

*30-day rolling correlation of daily returns vs. SPY (30-calendar-day window, 21 sessions 2026-08-27 → 2026-09-25; same convention as prior weeks)*

| Sector | ETF | vs. SPY Correlation | 1W Ago | Regime |
|---|---|---|---|---|
| 🖥️ Technology | XLK | **0.784** | 0.702 | 🔥 **High beta (rising — index leader)** |
| 🛍️ Consumer Discretionary | XLY | **0.745** | 0.696 | 🔥 **High beta (rising)** |
| 🏠 Real Estate | XLRE | **0.621** | 0.446 | 🔥 **High beta (jumped — rate beta)** |
| 💻 Semiconductors | SMH | **0.593** | 0.462 | 🔥 **High beta (rising)** |
| ⚙️ Industrials | XLI | **0.584** | 0.631 | 🔥 **High beta (easing)** |
| 🏦 Financials | XLF | **0.556** | 0.599 | 🔥 **High beta (easing)** |
| 📡 Communication Services | XLC | **0.413** | 0.224 | 🟡 **Re-coupling** |
| ⛏️ Materials | XLB | **0.351** | 0.463 | 🟡 **Moderate (easing)** |
| ⚡ Utilities | XLU | **0.302** | 0.198 | 🟡 **Re-coupling (rate beta)** |
| 🏥 Healthcare | XLV | **0.260** | 0.324 | 🟡 **Pro-cyclical (easing)** |
| 🍞 Consumer Staples | XLP | **-0.034** | 0.105 | 🔴 **FLIPPED NEGATIVE** |
| ⛽ Energy | XLE | **-0.356** | -0.095 | 🔴 **Inverse, re-deepening** |

**Ophelia Interpretation:** The flip I flagged last week happened. **Consumer Staples moved from +0.105 to -0.034**, crossing from positive to negative correlation with SPY. That meets this dashboard's strict alert criterion, and an issue has been opened. It is a small number in absolute terms: -0.034 means Staples is effectively uncorrelated rather than a true hedge. But it means the board has a second sector moving independently of or against the tape. That sector is also in outflow (-2.16% vs. SPY), so the "hedge" is working by falling while SPY rises. **Energy's inverse came back, -0.095 → -0.356**, and not in the way a hedge should work: XLE fell -3.53% on a week SPY rose, as WTI dropped on U.S.–Iran de-escalation (issue #116). At the top of the table, **XLK (0.784) and XLY (0.745) rose again**, and **XLRE jumped 0.446 → 0.621**. With the 10Y moving the whole tape, real estate has become rate beta that moves with the index.

**The key insight:** correlation is concentrating at the top (six sectors at 0.55 or higher) and the two sectors below zero (XLP, XLE) are both *losing* money. Negative correlation that only shows up as underperformance in up-weeks is not protection a book can rely on in a down-week.

**Alert:** 🔴 **Strict criterion met: XLP flipped positive → negative (0.105 → -0.034).** GitHub issue opened by this run. No other sector crossed zero.

---

## SECTOR ROTATION FLOW

*1-Day / 1-Week / 1-Month performance vs. SPY (1D = Fri 9/25 vs. Thu 9/24; 1W = Fri-to-Fri; 1M = 21 sessions from 2026-08-26)*

| Sector | ETF | 1D vs. SPY | 1W vs. SPY | 1M vs. SPY | Rotation Signal |
|---|---|---|---|---|---|
| 💻 Semiconductors | SMH | +0.46% | +4.59% | +8.45% | 🟢 **Inflow (leader)** |
| 🖥️ Technology | XLK | +0.26% | +2.25% | +6.66% | 🟢 **Inflow** |
| 📡 Communication Services | XLC | -1.45% | +0.67% | -0.38% | 🟢 **Inflow (first green week in five, per wiki/communication-services.md)** |
| 🏥 Healthcare | XLV | -0.05% | +0.10% | -2.32% | 🟡 **Neutral** |
| ⚙️ Industrials | XLI | +0.40% | -0.87% | -6.18% | 🟡 **Neutral (1M outflow)** |
| ⛏️ Materials | XLB | -0.30% | -1.65% | -7.90% | 🔴 **Outflow** |
| 🛍️ Consumer Discretionary | XLY | -0.33% | -1.69% | -6.32% | 🔴 **Outflow** |
| 🍞 Consumer Staples | XLP | -0.10% | -2.16% | -5.57% | 🔴 **Outflow** |
| 🏦 Financials | XLF | +0.02% | -3.09% | -6.56% | 🔴 **Outflow** |
| 🏠 Real Estate | XLRE | -0.76% | -3.55% | -8.52% | 🔴 **Outflow** |
| ⛽ Energy | XLE | -1.44% | -4.80% | -1.31% | 🔴 **Outflow (1M flipped negative)** |
| ⚡ Utilities | XLU | -0.16% | -5.14% | -9.88% | 🔴 **Outflow (worst on the board)** |

**Ophelia Interpretation:** **Seven of twelve sectors are in outflow for the second straight week.** The membership changed: **Energy joined** (-4.80% vs. SPY, its 1M relative now negative too) as oil fell below $100, and **Industrials and Healthcare moved to neutral**. **Communication Services crossed back to inflow** (+0.67%). The leadership got narrower and stronger: **SMH +4.59% and XLK +2.25% vs. SPY**, now +8.45% and +6.66% over the month. The bottom of the table is the rate-sensitive group, as it has been for a month. **Utilities (-5.14%) is the worst again**, with XLU closing at $39.51, its lowest close in this fetch's six-month window (wiki/utilities.md: through $40 for the first time since 2024, issue #108). **Real Estate (-3.55%)** and **Financials (-3.09%)** follow. Financials continue to get no benefit from higher rates, which fits a curve steepening for term-premium reasons rather than growth reasons.

**The risk:** the 1M column has **eight sectors worse than -2% vs. SPY** and four worse than -6.5% (XLU, XLRE, XLB, XLF). The index is tech and semis. If that pair cracks there is nowhere to rotate to except cash and duration, and duration just lost 1.4% in a week.

---

## CROSS-ASSET SIGNALS

| Asset | Level | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| DXY (US Dollar Index) | **101.04** (Yahoo DX-Y.NYB) | +0.81% | +1.88% | 🟡 **Above 101 (materials trip wire, #115); below our 102 trigger** |
| EUR/USD | 1.1392 | -0.73% | -2.42% | 🟡 **Euro lower for a second week** |
| USD/JPY | 157.185 | +0.68% | -1.28% | 🔴 **Carry rebuild continuing (intraweek 158.996)** |
| WTI Crude | $92.44 | -7.84% | +12.42% | 🟡 **Back below $100 on U.S.–Iran de-escalation (#116); low $88.71 Wed** |
| Brent Crude | $97.47 | -6.16% | +10.96% | 🟡 **Through $100 (see note)** |
| Gold | $4,320.50 | -2.36% | -7.15% | 🔴 **Losing ground to real yields** |
| Copper | $6.779/lb | +2.48% | +2.80% | 🟢 **Growth metal firming (2nd week)** |
| Bitcoin | $83,987 (latest print, see note) | +3.81% | +6.28% | 🟢 **Extending above $80K** |
| HY Bonds (HYG) | $77.86 | -0.85% | -2.55% | 🟡 **Fourth red week** |
| IG Bonds (LQD) | $103.21 | -1.42% | -3.34% | 🟡 **Duration hit by +19 bps 10Y** |
| TIPS Breakeven (10Y) | 2.34% (FRED T10YIE, Fri 9/25) | +0.01% | +0.02% | 🟢 **Inflation expectations anchored — the 10Y move is real yield/term premium** |

> *DXY from Yahoo's ICE DXY series (DX-Y.NYB), carried in macro/facts.json at 101.04 (tolerance 1%). FX 1W changes use this run's Yahoo fetch for both endpoints (EUR/USD Fri 9/18 bar now reads 1.1476 vs. 1.149 published last week, a vendor bar revision). **Bitcoin:** Yahoo has no 2026-09-25 UTC daily bar in this fetch; the figure is the latest print (2026-09-26 UTC bar, captured ~23:00 ET Friday), and 1W/1M are measured against the 9/18 ($80,901) and 8/26 ($79,027) daily closes. facts.json carries the same $83,987 with as_of 2026-09-26. **Brent (BZ=F)** printed 106.60 Thu → 97.47 Fri (-8.6%) against WTI -2.3% the same day. That gap is possibly a front-month contract-roll artifact in the continuous series, so treat Brent's 1D/1W figures as directional. WTI (CL=F) is the canonical oil number (facts.json).*

**Ophelia Interpretation:** Oil and rates did opposite things, and that tells you what drove the 10Y. **WTI fell -7.84% to $92.44** (low **$88.71** Wednesday) on U.S.–Iran de-escalation at the UN General Assembly, back below the $100 red trigger it held for two weeks. Yet the **10Y rose 19 bps** and **10Y breakevens were flat at 2.34%**. Falling oil, flat inflation expectations and a sharply higher 10Y means real yields and term premium did the work, not inflation fear. **Gold (-2.36%, -7.15% in a month)** is behaving the way it should when real yields rise. **The dollar kept climbing, DXY 101.04 (+0.81%)**, above the materials desk's 101 trip wire (#115) and still under this board's 102 trigger. **USD/JPY 157.185 (+0.68%)** touched **158.996** Thursday. The carry rebuild after the split BOJ hike is continuing, and the 158–160 zone where MoF language tends to appear is now close. **Copper (+2.48%) and Bitcoin (+3.81%)** firmed again, so the cross-asset tape is not risk-off. It is a rates shock that equities outside tech are absorbing badly.

**The risk:** the three-way tightening from last week (strong dollar, 5% 10Y, $100 oil) lost its oil leg, but the rates leg got 19 bps stronger and the dollar leg got stronger too. Lower oil is the only real relief on the board this week, and it rests on a diplomatic process.

---

## CANARY WATCH TRIGGER BOARD

| Signal | Status | Trend | Trigger Level |
|---|---|---|---|
| VIX Regime | 🟢 Normal (breached 16.50 intraweek for the 3rd week, closed back under) | Flat (+0.41% WoW) to 14.87; 16.57 intraweek high Thu; contango intact | 🟡 >20 | 🔴 >25 |
| Yield Curve | 🟡 Positive, long end re-steepening | 10Y 5.184% (first weekly close >5.00%, #113); 10Y–2Y ~+31, 10Y–3M +111 | 🟡 <0 (inverted) | 🔴 <-50 bps |
| Credit Spreads | 🟢 Contained (live FRED OAS), HY widening at the margin | HY–IG 201 bps (HY 280 / IG 79); HY +10 bps WoW | 🟡 HY–IG >250 bps | 🔴 >350 bps |
| Market Breadth | 🔴 Narrowing (live proxies; official gauges stale 72d) | RSP -1.82 pts vs. SPY WoW, -5.64 pts 1M (was -0.86 / -3.45); 5/12 sectors above 50D | 🟡 <50% above 50D MA | 🔴 <40% |
| Sector Rotation | 🔴 7 of 12 sectors in outflow (2nd week) | Inflow only SMH/XLK (+XLC) | 🟡 XLK -5% vs. SPY | 🔴 XLK -10% |
| Sector Correlation | 🔴 **XLP flipped negative (0.105 → -0.034)** | XLE inverse re-deepened to -0.356 | 🔴 positive → negative flip | — |
| DXY | 🟢 Below trigger, rising | 101.04 (+0.81% WoW) | 🟡 >102 | 🔴 >105 |
| Geopolitics | 🟡 **Oil back below $100 — downgraded from red** | WTI $92.44 (-7.84%) on U.S.–Iran de-escalation (#116) | 🟡 Oil >$90 | 🔴 Oil >$100 |
| Credit Risk | 🟢 Stable | IG OAS +1 bp; LQD loss is duration, not spread | 🟡 CDS widening | 🔴 Bank stress |
| Policy | 🔴 **Live hiking cycle** | Fed 3.75–4.00% (hiked 9/16); 16/18 dots see another 2026 hike; BOJ 1.25% | — | — |
| Overall Risk | 🟡 **CAUTION (escalating, rates-led)** | — | — | — |

**Weekly Narrative — Overall Assessment:** The week after the Fed hike was a bond-market week. The ledger: (1) **the 10Y closed above 5.00% three days running and finished at 5.184% (+18.6 bps)**, its first weekly close above 5.00% of the cycle, with an intraweek high of 5.230% (#113); (2) **the curve re-steepened at the long end**: 10Y–5Y from +14.2 to +17.7 bps and 10Y–3M from +102 to +111, while 10Y–2Y held ~+31, so after a week of bear-flattening the market started charging term premium; (3) **the 2Y kept climbing to 4.87% (+68 bps in a month)** and the **5Y closed above 5.00%**; (4) **10Y breakevens were flat (2.34%) and oil fell 7.84%**, so the move was real yield and term premium, not inflation expectations; (5) **WTI dropped back below $100 to $92.44** on U.S.–Iran de-escalation (#116), downgrading the geopolitics row from red to yellow after two weeks at red; (6) **VIX finished flat at 14.87** (CBOE-verified), with a third straight intraweek breach of 16.50 that did not hold; (7) **HY OAS widened 10 bps to 280** and HY–IG crossed 200 bps (201), still well under the 250 trigger, while IG was flat; (8) **SPY rose +1.27% while RSP fell -0.56%**, equal-weight gaps of -1.82 / -5.64 pts, up from -0.86 / -3.45 last week; (9) **SMH (+5.86%) and XLK (+3.52%) carried the index**, and seven of twelve sectors were in outflow for the second week; (10) **Consumer Staples' correlation to SPY flipped negative (0.105 → -0.034)**, meeting this dashboard's strict alert criterion; (11) **the dollar extended to 101.04** and USD/JPY to 157.19, with gold down 2.36%.

The fragilities: (1) a 5.18% 10Y driven by term premium rather than inflation is harder for the Fed to talk down, and the **Sep 30 August PCE** print now lands on a bond market that has already moved; (2) the equity index is two sectors deep, and the equal-weight gap widened again; (3) both negatively-correlated sectors (XLP, XLE) are losing money, so the board has no working diversifier in sectors; (4) HY OAS turned upward in the same week the 10Y broke out, which is the combination Cecil has said would matter; (5) USD/JPY near 158–159 on a split BOJ is a disorderly-unwind risk; (6) VIX 14.87 under a 5.18% 10Y is complacency risk.

**The Canary Watch verdict:** 🟡 **CAUTION, escalating (rates-led)**, held for a fifth straight week. Composition changes: geopolitics improved (red → yellow as oil fell below $100); a **Sector Correlation** row turned red on the XLP flip; credit stays green but its direction turned. Of the four strict criteria, **one was met this week: a sector correlation flipped from positive to negative (XLP)**, and this run opened a Canary Watch issue for it. The others were not: VIX closed 14.87 (intraweek high 16.57, never above 20); the curve is positive at every tenor; HY–IG is 201 bps (HY OAS itself has been above 250 bps all year). The rates, dollar and oil catalysts are already tracked under **#113** (10Y weekly close >5.00%), **#115** (DXY >101), **#116** (WTI de-escalation drop) and **#108** (utilities). Watch: (1) August PCE, Sep 30; (2) 10Y 5.23% (Friday's intraweek high) and whether 10Y–5Y keeps steepening; (3) HY OAS 280 → 300; (4) USD/JPY 159–160 and MoF language; (5) WTI $88.71 (the week's low) and whether the diplomatic track holds; (6) XLP staying below zero and XLE's inverse; (7) the official breadth feed, 72 days overdue.

---

## COUNCIL READ — What This Means for Monday

*(Updated this week: regime shift in rates. First weekly 10Y close above 5.00%, driven by term premium rather than inflation expectations, while oil fell back below $100.)*

**Ophelia:** *"Last week the curve flattened and I read that as the Fed doing the work at the front. This week the long end did the work by itself: 10Y up 19 bps, 10Y–5Y up 3.5, breakevens flat, oil down 8%. That is the market charging more to hold duration, and it is the harder kind of rate move to reverse because a softer PCE print doesn't fix it. I'm keeping cash at 25–30% and still adding nothing rate-sensitive before PCE on September 30. Oil falling below $100 is real relief, but it rests on a diplomatic track. The Staples flip gets a note in the book and no more: a -0.03 correlation in a sector that lost 2% against the index is not a hedge I will pay for. Sector diversifiers are not doing the job, so protection stays in cash."*

**Marky:** *"I said a second close above 5.00% on the 10Y was my signal to de-risk hard. We got three, and a weekly close at 5.18%. So I'm de-risking. Not out of the tech/semis leadership, which keeps working (SMH +5.86% this week), but hedged harder and sized down everywhere else. RSP is 5.6 points behind SPY in a month. VIX 14.87 is not pricing any of this, which makes vol cheap to own. My lines: 10Y 5.23% (Friday's high), VIX 16.50 on a close (three intraweek breaches, zero closes), and XLK -5% vs. SPY as the leadership-break signal."*

**Cecil:** *"For the first time since I got live spreads back, HY moved the wrong way: 270 to 280, HY–IG over 200. IG didn't move, and 280 is still ordinary for this cycle, so I'm not calling stress. But I said 300 would be the first real credit signal of this cycle, and we covered a third of that distance in a week the 10Y broke out. LQD's -1.4% was almost all duration, and at 5.18% on the 10Y, quality duration is still the best margin of safety on this board. I'd extend in IG and stay away from HY until the next two prints tell me whether this week was noise."*

---

## SOURCES & REFERENCES

- Yahoo Finance (yfinance 1.x, single fetch 2026-09-25 ~23:00 ET): VIX, VIX3M, VVIX, SPY, RSP, 12 sector ETFs, Treasury yield proxies (^IRX/^FVX/^TNX), DXY (DX-Y.NYB), FX (EURUSD=X, JPY=X), crude (CL=F, BZ=F), gold (GC=F), copper (HG=F), Bitcoin (BTC-USD), bond ETFs (HYG, LQD)
- CBOE: official VIX daily history (cdn.cboe.com VIX_History.csv), Fri 2026-09-25 close 14.87, exact match; VIX3M term structure; put/call ratio feed not wired (requires external update)
- FRED (St. Louis Fed): VIXCLS (posted through Mon 9/22, matches Yahoo), DGS2 (2Y, Thu 9/24), DGS10/DGS3MO (CMT cross-checks, Thu 9/24), BAMLH0A0HYM2 / BAMLC0A0CM / BAMLEMCBPIOAS (ICE BofA HY / IG / EM corporate OAS, Thu 9/24), T10YIE (10Y breakeven, Fri 9/25)
- Federal Reserve: FOMC statement 2026-09-16, Summary of Economic Projections; FOMC 2026 calendar (next meeting Oct 27–28). Policy block in facts.json unchanged this week (no policy event).
- BEA: PCE release schedule (August PCE, Sep 30 08:30 ET)
- NYSE/NASDAQ: advance/decline, new highs/lows, % above MAs — 72 days stale, refresh overdue
- Internal desk cross-references (2026-09-25 Grid A/B/C updates): wiki/utilities.md (XLU through $40), wiki/energy.md (U.S.–Iran UNGA de-escalation), wiki/communication-services.md (XLC first green week in five). Sector closes on this page equal facts.json.
- GitHub issues cross-referenced this run: #108 (utilities), #113 (10Y weekly close >5.00%), #115 (DXY >101), #116 (WTI de-escalation). New issue opened by this run: XLP correlation flip (strict criterion).

---

*Last updated by Saturday Research Crew: 2026-09-25 (single-agent run; all market data as of Fri 2026-09-25 closes; macro/facts.json regenerated from the same fetch)*
*Next update: Every Saturday 7:39 PM ET*
*Data sources: Yahoo Finance (yfinance), CBOE, FRED, Federal Reserve, BEA*
