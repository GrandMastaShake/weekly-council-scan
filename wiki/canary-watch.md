# Wiki — Canary Watch

> **The Early Warning System for the Market Consciousness Orchestra**
>
> *"The canary does not predict the mine collapse. It simply dies first. Watch the canary."* — Marky

> **Truth layer:** every macro number on this page equals `macro/facts.json` (generated 2026-10-31, same fetch, commit f9cd1ca; `truth_check --facts` 28 ok / 0 warn / 0 fail / 0 skip before push). Week ending Friday 2026-10-30 closes.

> **Run note:** this update ran on schedule (Saturday 2026-10-31 ~19:46 ET). **WTI and gold are from the 2026-10-30 feed** (`data/market_state.json`), not stale. **FRED timed out from the runner's own connection for a fifth week**, and the in-app browser refused the site. All nine series were downloaded in one fredgraph request through a second network path during the same run, so **no FRED row is stale**: DGS2 / DGS10 / DGS3MO, the four OAS series and VIXCLS are posted through Thu 2026-10-29 (FRED's usual one-day lag), the 10Y breakeven through Fri 2026-10-30. Finviz Elite breadth ran cleanly.

---

## VOLATILITY REGIME

| Metric | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| VIX | **19.42** | 19.45 | 16.39 | 🟡 **Under 20 on every close; 23.93 intraday Fri** |
| VIX 20-Day MA | ~17.00 | ~16.54 | — | — |
| VIX Trend | **-0.15% WoW**; closes 18.39 / 17.52 / 16.91 / 17.20 / 19.42; low 16.21, high **23.93 Fri** | — | — | — |
| VIX3M (term structure) | 20.78 (VIX/VIX3M **0.935**) | 20.48 (0.950) | 18.58 (0.882) | 🟡 **Contango thin: 0.922 → 0.895 → 0.880 → 0.888 → 0.935** |
| Implied SPY Move (30D) | ~±5.6% | ~±5.6% | — | — |
| VVIX (VIX of VIX) | **106.43** | 109.70 | 92.01 | 🔴 **124.06 intraday Fri; 98.02 was Thursday's high** |
| Total Put/Call Ratio (CBOE) | 0.90 (5D avg 0.89) | 0.93 (5D avg 0.90) | 0.90 | 🟡 **Five-day average just off last week's high** |
| Equity Put/Call Ratio (CBOE) | 0.66 (5D avg 0.59) | 0.67 (5D avg 0.60) | 0.57 | 🟡 **0.54 Wed, 0.66 Fri** |

> *Source note: VIX prints vary by vendor — discrepancies of ~2–3 pts are common across quote sources (delayed feeds, spot vs. VX futures, stale prints). Canonical reference: CBOE official close / FRED VIXCLS. This week the Friday close was cross-checked against the **CBOE official daily history file (VIX_History.csv): Fri 2026-10-30 close 19.42, high 23.93**, an exact match for Yahoo ^VIX, and the CBOE file matches Yahoo on all five closes. **FRED VIXCLS** is posted through Thu 10/29 (17.20) and agrees. **Put/call ratios** are from CBOE's official daily market statistics file (cdn.cboe.com daily_options), Fri 2026-10-30 vs. Fri 2026-10-23 and Thu 2026-10-01 (21 sessions back); 5D averages are Mon–Fri of each week. Index put/call was 1.03 Friday (5D avg 1.01); SPX + SPXW 1.25 (5D avg 1.15, from 1.20 the week before).*

**Marky Interpretation:** The Friday close is the same as last Friday's, and that hides the week. VIX fell four straight sessions to a low of **16.21**, ratio 0.880, VVIX under 100. Then on Friday it printed **23.93** intraday, with Intel down 28.6% and SOX down 7.20% (#183, #190), and closed at **19.42**. VVIX hit **124.06** and closed 106.43. So the fear came and most of it left the same day, the same fade as Oct 16. What it left behind is a ratio back at **0.935** and VIX3M at 20.78, up 1.46% on the week. My lines stay where they were: a close above 20 is the regime question, 25 is the alarm, a ratio above 1.00 is the tell. Next week carries Apple, AMD, the midterms and payrolls.

---

## YIELD CURVE

| Maturity | Yield | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| 13-Week (T-Bill) | 3.973% | -0.059% | -0.009% (vs. 3.982% on 10/1) | **Closes 4.025 / 4.040 / 3.995 / 3.998 / 3.973; the Fed held, December odds slipped** |
| 2-Year | 4.61% (FRED DGS2, Thu 10/29 — see note) | **-0.04%** (vs. 4.65% Thu 10/22) | -0.17% (vs. 4.78% on 10/1) | **4.69 / 4.68 / 4.70 / 4.67 / 4.61 from last Friday; Friday 10/30 not yet posted** |
| 5-Year | 4.721% | -0.084% | -0.284% | Closes 4.824 / 4.840 / 4.871 / 4.801 / 4.721 |
| **10-Year** | **4.929%** | **-0.059%** | **-0.308%** | **Second weekly close under 5.00%; closes 4.986 / 4.993 / 5.045 / 4.989 / 4.929** |
| **10Y–2Y Spread** | **~+32 bps** (Fri 10Y vs. Thu 2Y) | -2 bps vs. last week's +34 | — | **Positive; same-day Thursday basis +37 (see note)** |
| **10Y–5Y Spread** | **~+20.8 bps** | +2.5 bps (was +18.3) | — | Slightly steeper |
| **10Y–3M Spread** | **~+96 bps** | Flat (+96 last week) | — | **Positive, stopped flattening** |

> *2Y source: FRED DGS2, Thu 2026-10-29 (FRED's one-day lag), so the 10Y–2Y spread pairs Friday's 10Y with Thursday's 2Y and understates the week's steepening. On a same-day Thursday basis (FRED DGS10 4.98% vs. DGS2 4.61%) the spread is +37, from +31 a week earlier. The feed (`data/market_state.json`) carries a Friday 2Y of 4.56% and a 2s10s of +37; that number comes from a Friday source this job does not use, so macro/facts.json carries 4.61 with as_of 2026-10-29 and source fred:DGS2. ^IRX is a discount-basis T-bill yield; FRED's constant-maturity 3M (DGS3MO) was 4.18% Thursday, about 18 bps higher, so a CMT-basis 10Y–3M would read ~+80 bps. This page and facts.json use ^IRX for series continuity. FRED's DGS10 for Thu 10/29 is 4.98%, consistent with ^TNX's 4.989% Thursday close.*

**Ophelia Interpretation:** The 10-year closed at **4.929%**, down 6 bps, and the path mattered more than the level. It went over 5.00% on one close, **5.045% on Wednesday** after a 10-2 FOMC hold with two dissents for a hike, then fell 11.6 bps in two sessions as Amazon, Intel and Alphabet took the tape down (wiki/economic-calendar.md). The data did not help the rally: GDP 3.4%, core PCE +0.3% and 3.1%, claims 194K, Conference Board confidence 91.7. The bond rally came from equity stress again and not from a print. The feed's Friday 2Y of 4.56% is 13 bps lower on the week, against 4 bps on FRED's Thursday-to-Thursday print, so the curve steepened by more than the +32 shows. The breakeven was flat (**T10YIE 2.34%**), so the fall was real yield again: about **2.59%**, from 2.65%. Net: **10Y–2Y +32** on the mixed basis, **10Y–3M +96** (unchanged). No inversion anywhere.

**Yield Curve Regime:** 🟡 **Positive, rate relief borrowed from equities.** 10Y 7.1 bps under 5.00%. Next gates: **ISM Mon Nov 2, refunding and ISM Services Wed Nov 4, payrolls Fri Nov 6, CPI Nov 10.**

---

## CREDIT SPREADS

> *OAS rows are FRED's **Thu 2026-10-29** prints (FRED's one-day lag), with Thu 10/22 as the week-ago column and Thu 10/1 as the month-ago column. Friday Oct 23's prints, flagged last week as the confirmation test, posted this week: HY 338, IG 91, HY–IG **247**. Friday Oct 30's OAS posts Monday. HYG and LQD are live Friday closes.*

| Spread | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| HY OAS (ICE BofA US HY, BAMLH0A0HYM2) | **326 bps** (Thu 10/29) | 340 bps | 324 bps | 🟡 **Off the 340 peak; 338 / 330 / 318 / 314 / 326 since last Friday** |
| IG OAS (ICE BofA US Corp, BAMLC0A0CM) | 89 bps (Thu 10/29) | 89 bps | 86 bps | 🟡 **Flat; 91 last Friday, 86 Wednesday** |
| **HY–IG Spread** | **237 bps** (Thu 10/29) | 251 bps | 238 bps | 🟢 **BACK UNDER 250: 247 / 240 / 230 / 228 / 237; the 251 was one print, not confirmed** |
| EM Corporate OAS (BAMLEMCBPIOAS) | 173 bps (Thu 10/29) | 173 bps | 161 bps | 🟡 **Flat, holding last week's jump** |
| CCC & Lower OAS (ICE BofA, BAMLH0A3HYC) | **1,325 bps** (Thu 10/29) | 1,340 bps | 1,215 bps | 🟡 **1,356 on Fri 10/23, the high of this fetch; +110 on the month** |
| **HYG Price** | **$77.43** | **$77.05** | **$76.90** | 🟢 **+0.49%** |
| **LQD Price** | **$104.27** | **$103.85** | **$102.03** | 🟢 **+0.40% on the 6 bp 10Y rally** |

**Cecil Interpretation:** The trigger did not confirm. **HY–IG printed 247 on Friday Oct 23**, then 240, 230 and 228, before ticking back to **237 on Thursday**. HY OAS came off its 340 peak to 326; the worst of it was **CCC at 1,356** on Oct 23, and it is 1,325 now. That is a single print above 250, which is what I said it might be. Now the caution. Every print in that table is from before Friday. Thursday's move was already wider by 9 bps on a day SPY fell only 0.38%, and Friday was the day SPY fell 1.77% and VIX hit 23.93. The month-ago column shows the point: HY–IG is back where it was on Oct 1, but CCC is 110 wider. **CCC-minus-HY is about 1,000 bps** (999), unchanged from last week.

**Credit Regime:** 🟢 **Back under the line, one print pending.** HY–IG 237 on Oct 29; HY OAS 326; CCC 1,325. The crossing on #177 did not confirm. Next: Friday Oct 30's prints, posted Monday.

---

## MARKET BREADTH

> *S&P 500 rows are computed from the daily closes of all 503 constituents with a Fri 2026-10-30 print (Yahoo, list from Wikipedia's S&P 500 table; 50D/200D = simple MA of closes; a new high/low means the day's high/low reached the trailing 252-session extreme). They are cross-checked against **Finviz Elite** (`finviz_elite breadth`, S&P 500 universe, 503 members), which agrees exactly on advancers/decliners (226 / 277), new highs/lows (42 / 5) and names above each average (302 and 296), giving 60.04% vs. 60.2% here on % above 50D and 58.85% vs. 59.2% on % above 200D; the gaps are denominators, members with a full 50D/200D history here against all 503 there. Market-wide rows are Finviz's NYSE + Nasdaq + AMEX stock totals for Friday (5,602 stocks, ETFs and funds excluded). The 1W and 1M comparisons are recomputed from this fetch on the current 503-member list; 1M is Thu 10/1, 21 sessions back.*

| Metric | Current | 5D Avg | 20D Avg | Regime |
|---|---|---|---|---|
| S&P 500 Advance/Decline (Fri) | **0.82** (226 up / 277 down) | 1.66 | 1.62 | 🟢 **On a -1.77% SPY day; advancers 289 / 245 / 247 / 406 / 226** |
| Market-wide Advance/Decline (Fri, Finviz) | 0.37 (1,455 up / 3,938 down) | — | — | 🔴 **Worse than last Friday's 0.64** |
| S&P 500 New 52-Week Highs | **42** | 20.0 | 18.5 | 🟢 **Ties Oct 22, the most in the last 30 sessions** |
| S&P 500 New 52-Week Lows | **5** | 7.4 | 6.5 | 🟢 **14 Wednesday; highs beat lows every day** |
| Market-wide New Highs / Lows (Fri, Finviz) | 162 / 448 | — | — | 🔴 **Lows still 73% of the total** |
| **S&P 500 % Above 50D MA** | **60.2%** (1W 58.0%, 1M 22.9%) | 60.6% | 46.2% | 🟢 **Above 50%; 64.9% Thursday** |
| **S&P 500 % Above 200D MA** | **59.2%** (1W 55.8%, 1M 41.0%) | 59.5% | 52.4% | 🟢 **63.6% Thursday** |
| Market-wide % Above 50D / 200D (Fri, Finviz) | 36.4% / 38.9% | — | — | 🔴 **Improved from 33.7% / 38.2%, still under 40%** |
| Equal-Weight (RSP) vs. Cap-Weight (SPY), 1W | **+1.38 pts** (RSP +0.82% vs. SPY -0.56%) | — | 1M: **+5.53 pts** | 🟢 **Fourth week ahead** |
| Sector ETFs above own 50D MA | **8 of 12** (XLY, XLF, XLB, XLRE, XLU, XLV, XLE, XLP) | — | — | 🟢 **XLY, XLF and XLRE regained it; XLK, SMH, XLC, XLI below** |

**Marky Interpretation:** For the fourth straight week the average stock beat the index. **SPY fell -0.56% to $755.72**, its third down week, and closed back under its 50-day ($767.49) after three closes over it; **RSP rose +0.82%**. On Friday, with SPY down 1.77% and SMH down 6.98%, the S&P had **226 advancers and 42 new 52-week highs**, level with the most in the last 30 sessions. That is not what a broad selloff looks like. **60.2% of members are above the 50-day** and 59.2% above the 200-day. Thursday's 406 advancers and 64.9% above the 50-day were the highs of the last 30 sessions. Finviz Elite agrees name for name.

The caution is outside the index. Market-wide A/D on Friday was 0.37 against 0.82 for the S&P 500, new lows are 448 against 162 highs, and only 36.4% of all stocks are above their 50-day. The sector ETFs at closing highs this week are healthcare and energy (#186, #185).

**Breadth Regime:** 🟢 **Clear.** S&P 500 % above 50D (60.2%) is above the 50% yellow line. Market-wide gauges remain red.

---

## SECTOR CORRELATION MATRIX

*30-day rolling correlation of daily returns vs. SPY (30-calendar-day window, 22 sessions 2026-10-01 → 2026-10-30; same convention as prior weeks; the 1W-ago column is last week's published window ending 2026-10-23, which this fetch reproduces exactly)*

| Sector | ETF | vs. SPY Correlation | 1W Ago | Regime |
|---|---|---|---|---|
| 🖥️ Technology | XLK | **0.919** | 0.836 | 🔥 **High beta (rising)** |
| 💻 Semiconductors | SMH | **0.879** | 0.765 | 🔥 **High beta (rising, +11 pts)** |
| 🛍️ Consumer Discretionary | XLY | **0.697** | 0.727 | 🔥 **High beta** |
| ⚙️ Industrials | XLI | **0.650** | 0.603 | 🔥 **High beta** |
| 📡 Communication Services | XLC | **0.423** | 0.440 | 🟡 **Moderate** |
| 🏦 Financials | XLF | **0.205** | 0.275 | 🟡 **Low (easing)** |
| ⛏️ Materials | XLB | **0.117** | 0.262 | 🟡 **Low (next flip candidate)** |
| 🏠 Real Estate | XLRE | **-0.049** | 0.111 | 🔴 **FLIPPED positive → negative (issue #192)** |
| ⚡ Utilities | XLU | **-0.126** | 0.024 | 🔴 **FLIPPED positive → negative (issue #192)** |
| 🏥 Healthcare | XLV | **-0.162** | -0.071 | 🔴 **Inverse (second week)** |
| ⛽ Energy | XLE | **-0.396** | -0.263 | 🔴 **Inverse, deepened** |
| 🍞 Consumer Staples | XLP | **-0.558** | -0.371 | 🔴 **Inverse, deepened** |

**Ophelia Interpretation:** Last week's page named utilities as the next flip at 0.024. It flipped, and real estate went with it: **XLU -0.126 and XLRE -0.049**, both strict positive-to-negative crossings. **Five of twelve sectors are now below zero**, every one of them defensive or energy, and staples deepened to -0.558. The other end tightened: **XLK 0.919 and SMH 0.879**, up 8 and 11 points. Financials and materials slid to 0.205 and 0.117. This is one trade with two sides, and Friday showed it: SMH -6.98%, XLP +1.41%, XLE +1.91%.

**The key insight:** the index now moves with four sectors. Being diversified paid this week, and a cap-weighted book is more of a single semiconductor and software bet than it was a month ago.

**Alert:** Strict-criterion flips — **XLU (+0.024 → -0.126)** and **XLRE (+0.111 → -0.049)**, issue #192. No sector is left between 0 and 0.1; XLB at 0.117 is next.

---

## SECTOR ROTATION FLOW

*1-Day / 1-Week / 1-Month performance vs. SPY (1D = Fri 10/30 vs. Thu 10/29; 1W = Fri-to-Fri; 1M = 21 sessions from 2026-10-01). SPY: -1.77% / -0.56% / -1.08%.*

| Sector | ETF | 1D vs. SPY | 1W vs. SPY | 1M vs. SPY | Rotation Signal |
|---|---|---|---|---|---|
| 🏥 Healthcare | XLV | +2.22% | +3.68% | +12.32% | 🟢 **Inflow (leader: +3.12%; two-year closing high, #186)** |
| ⛏️ Materials | XLB | +2.17% | +3.35% | +9.74% | 🟢 **Inflow (+2.79%)** |
| ⚡ Utilities | XLU | +2.45% | +2.60% | +10.53% | 🟢 **Inflow (+2.04%)** |
| 🛍️ Consumer Discretionary | XLY | +1.07% | +2.58% | +7.12% | 🟢 **Inflow (+2.02%)** |
| ⚙️ Industrials | XLI | +0.17% | +2.25% | +0.35% | 🟢 **Inflow (+1.69%; still under its 50D and 200D, #188)** |
| 🏠 Real Estate | XLRE | +2.03% | +1.97% | +7.20% | 🟢 **Inflow (+1.41%)** |
| 🍞 Consumer Staples | XLP | +3.18% | +1.87% | +12.40% | 🟢 **Inflow (+1.31%; +1.41% Friday)** |
| 🏦 Financials | XLF | +1.02% | +1.65% | +6.79% | 🟢 **Inflow (+1.09%)** |
| ⛽ Energy | XLE | +3.68% | +1.55% | +12.76% | 🟢 **Inflow (+1.00%; 52-week closing high, #185)** |
| 💻 Semiconductors | SMH | -5.20% | -0.33% | -14.35% | 🔴 **Outflow on the day (-0.89% W/W; -6.98% Friday, #190)** |
| 🖥️ Technology | XLK | -3.12% | -1.47% | -8.17% | 🔴 **Outflow (-2.03%; -4.89% Friday, #183)** |
| 📡 Communication Services | XLC | +0.48% | -4.76% | -8.05% | 🔴 **Outflow (-5.32%; 52-week closing low, #187)** |

**Ophelia Interpretation:** **Ten of twelve sectors beat SPY**, and the two that did not were the ones that matter to it. **XLC fell -5.32%** to a 52-week closing low on Alphabet (#187), XLK fell -2.03% with -4.89% on Friday alone (#183), and SMH fell -0.89% only because it had rallied into Friday: it lost 6.98% that day, and its low of $511.63 went through the 200-day ($519.50) before it closed $2.99 above (#190). **Healthcare led** (+3.12%, a two-year closing high at $184.87, #186), with materials +2.79% and utilities +2.04% behind it. The board's leadership trigger (**XLK -5% vs. SPY in a week**) did not fire at -1.47 pts. Over a month the split widened from last week's 23 points: **XLE +12.76, XLP +12.40, XLV +12.32** pts ahead of SPY; **SMH -14.35, XLK -8.17, XLC -8.05** behind.

**The risk:** the one-month spread between the best and worst sector is 27 points. Apple Monday and AMD Tuesday decide whether Friday was Intel's problem or the sector's.

---

## CROSS-ASSET SIGNALS

| Asset | Level | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| DXY (US Dollar Index) | **101.88** (Yahoo DX-Y.NYB) | +0.07% | -0.22% | 🟢 **Friday close under 102 after three closes over it: 101.96 / 102.32 / 102.19 / 102.04 / 101.88; high 102.49** |
| EUR/USD | 1.1183 | -0.34% | -1.27% | 🟡 **Range 1.1110–1.1227 (see note)** |
| USD/JPY | 157.804 | +0.84% | +0.16% | 🟡 **Gave back last week's firming (see note)** |
| WTI Crude | **$104.12 (CLZ26 settle, as_of 2026-10-30)** | **+0.8%** (same contract; Oct 23 $103.27) | **+14.3%** (feed, 4W) | 🔴 **Four of five closes over $100: 101.76 / 99.90 / 102.78 / 102.00 / 104.12** |
| Brent Crude | $117.64 | +0.79% | +14.98% | 🔴 **Directional only (see note)** |
| Gold | **$3,885.70 (GCX26 settle, as_of 2026-10-30)** | **-2.6%** (feed; Oct 23 $3,991.10 on GCV26) | **-6.0%** (feed, 4W) | 🟡 **Fell $132.00 on the same contract Friday; GCZ26 $3,898.90** |
| Copper | $6.4585/lb (HG=F front month) | -0.27% | -0.36% | 🟡 **-1.86% Friday; range $6.43–6.64 (see note)** |
| Bitcoin | $77,198 (Fri 10/30 UTC close) | -4.78% | -9.02% | 🔴 **Lost $80K after three weeks over it; range $76,190–$81,890** |
| HY Bonds (HYG) | $77.43 | +0.49% | +0.69% | 🟢 **Up with spreads tighter, unlike last week** |
| IG Bonds (LQD) | $104.27 | +0.40% | +2.20% | 🟢 **Duration relief on -6 bps 10Y** |
| TIPS Breakeven (10Y) | 2.34% (FRED T10YIE, Fri 10/30) | 0.00 pts | -0.02 pts | 🟡 **Flat; the 10Y's fall was real yield again (about 2.59%, from 2.65%)** |

> *DXY from Yahoo's ICE DXY series (DX-Y.NYB), carried in macro/facts.json at 101.88 (tolerance 1%). 1W changes use this run's Yahoo fetch for both endpoints. Three Yahoo series revised last Friday's bar since last week's run: **EUR/USD** 10/23 now 1.1221 (published 1.1204; vs. the published value the week is -0.19%), **USD/JPY** 10/23 now 156.494 (published 156.814; vs. the published value the week is +0.63%), and **HG=F** 10/23 now 6.4760 (published 6.5075; vs. the published value the week is -0.75%). **FX daily bars:** per macro/README.md, Yahoo's daily bar for a pair closes near its open until the provider replaces it. facts.json carries the daily bars (157.804, 1.1183); the last hourly closes of the session were 157.519 and 1.1166, inside the 1% tolerance. **WTI and gold (feed contract):** facts.json carries WTI $104.12 (CLZ26, yahoo:CLZ26.NYM) and gold $3,885.70 (GCX26, yahoo:GCX26.CMX), as_of 2026-10-30, from `data/market_state.json`; both verified against the contracts' own bars by `truth_check --facts`. Gold's spot month rolled from GCV26 to GCX26; on GCX26 alone the week is -2.71% ($3,993.80 → $3,885.70). The continuous symbols CL=F and GC=F were not used. GCZ26 ($3,898.90) is shown for direction only and is not in facts.json. **Brent (BZ=F)** is a continuous series, shown for direction only; its 10/23 bar now reads $116.72, where last week's page published $111.70, so last week's level is not comparable. **Bitcoin:** the Fri 10/30 UTC daily bar is present ($77,198, same value and as_of in facts.json).*

**Ophelia Interpretation:** **Oil stayed above $100 and the risk premium is still building.** December WTI closed over $100 on four of five days and finished at **$104.12**, the highest close of the week, with December Brent at $117.64 and the Hormuz claims widening (#185, wiki/energy.md; OPEC+ meets Sunday). **Gold fell again**, -2.6% to **$3,885.70**, with $132.00 of it on Friday, while real yields fell another 6 bps. That is the third straight week of gold falling with real yields, and silver settled -8.6%. On a day equities sold off hard, gold, silver, copper and Bitcoin all fell, which fits a deleveraging, not a flight to safety. **Bitcoin lost $80K**, -4.78% to $77,198. **The dollar was flat** (101.88), and bonds were bought: TLT +0.61%, LQD +0.40%.

**The risk:** oil at $104 and hike odds falling at the same time. The tape is pricing the growth scare and the Fed's dissents are pricing the inflation, and both cannot be right by December.

---

## CANARY WATCH TRIGGER BOARD

| Signal | Status | Trend | Trigger Level |
|---|---|---|---|
| VIX Regime | 🟡 **Under 20 on the close; 23.93 intraday Fri** | -0.15% WoW to 19.42; VVIX 106.43 (124.06 high); VIX/VIX3M 0.935 | 🟡 >20 | 🔴 >25 |
| Yield Curve | 🟡 Positive, rally borrowed from equities | 10Y 4.929% (-6 bps; 5.045% Wed); 10Y–2Y ~+32 (+37 same-day Thu), 10Y–3M +96 (flat) | 🟡 <0 (inverted) | 🔴 <-50 bps |
| Credit Spreads | 🟢 **Back under the line; Friday's print pending** | HY–IG **237 bps** Thu 10/29 (251 on 10/22; 247 on 10/23, so unconfirmed); HY OAS 326; CCC 1,325; HYG +0.49% | 🟡 HY–IG >250 bps | 🔴 >350 bps |
| Market Breadth | 🟢 **Clear** | S&P 500 60.2% above 50D (58.0% last week), 59.2% above 200D; new highs/lows 42 / 5; RSP +1.38 pts vs. SPY WoW; market-wide 36.4% above 50D | 🟡 <50% above 50D MA | 🔴 <40% |
| Sector Rotation | 🟡 **No leadership trigger; XLC, XLK and SMH the only laggards** | XLK -2.03% (-1.47 vs. SPY); XLC -5.32%, SMH -0.89%; ten of twelve beat SPY; XLV leads | 🟡 XLK -5% vs. SPY | 🔴 XLK -10% |
| Sector Correlation | 🔴 **TWO FLIPS: XLU +0.024 → -0.126, XLRE +0.111 → -0.049** | Five sectors below zero; XLP -0.558, XLE -0.396, XLV -0.162; XLK 0.919, SMH 0.879 | 🔴 positive → negative flip | — |
| DXY | 🟢 **Under 102 on the Friday close** | 101.88 (+0.07% WoW); three closes over 102, high 102.49 | 🟡 >102 | 🔴 >105 |
| Geopolitics | 🔴 **Oil above $100** | WTI $104.12 (CLZ26, Fri settle; facts.json); Brent $117.64; Hormuz (#185) | 🟡 Oil >$90 | 🔴 Oil >$100 |
| Credit Risk | 🟡 CCC off its high, still 110 wider on the month (CDS not sourced) | XLF +1.09% to $56.51; EM OAS flat; CCC -15 bps W/W | 🟡 CDS widening | 🔴 Bank stress |
| Policy | 🔴 **Live hiking cycle; 10-2 hold** | Fed 3.75–4.00% (held 10/28, Cook and Hammack dissented for a hike); December ~73–76%; payrolls Fri 11/6, CPI 11/10 | — | — |
| Overall Risk | 🟡 **HIGH CAUTION (correlation trigger crossed; credit cleared, one print pending)** | — | — | — |

**Weekly Narrative — Overall Assessment:** The index fell on its largest members, and on the week ten of twelve sectors did better than it did. The ledger: (1) **SPY fell -0.56% to $755.72**, a third down week, and closed back under its 50-day ($767.49), all of it on Friday's -1.77%; (2) **S&P 500 breadth stayed clear**: 60.2% of members above the 50-day, 59.2% above the 200-day, 42 new highs on Friday, RSP +0.82%, ten of twelve sectors ahead of SPY; (3) **HY–IG did not confirm**: 247 on Oct 23, then 228 Wednesday and 237 Thursday, with HY OAS 326, off its 340 peak; (4) **two more correlations flipped negative** (XLU -0.126, XLRE -0.049), so five sectors are below zero while XLK reached 0.919; (5) **the 10Y fell 6 bps to 4.929%** after one close at 5.045% on the 10-2 FOMC hold; (6) **VIX hit 23.93 intraday Friday** and closed 19.42, VIX/VIX3M 0.935, VVIX 124.06 high; (7) **XLC fell -5.32%** to a 52-week closing low, XLK -2.03%, SMH -6.98% on Friday with a pierced 200-day; healthcare (+3.12%) led; (8) **December WTI settled $104.12**, four of five closes over $100; (9) **gold fell -2.6% to $3,885.70** and **Bitcoin lost $80K**; (10) the data stayed hot: GDP 3.4%, core PCE 3.1%, claims 194K, confidence 91.7 (wiki/economic-calendar.md).

The fragilities: (1) Friday's OAS print is the first read of credit after the selloff, and every credit number on this page predates it; (2) the index is now a concentrated bet, with XLK 0.919 and five sectors negative, so a growth break lands on it with little offset inside the cap-weighted book; (3) the bond rally is still coming from equity stress, with oil at $104 and two Fed dissents for a hike; (4) market-wide breadth is still red while S&P breadth is green, so the strength is in large defensive names; (5) gold falling with real yields for a third week, and Bitcoin under $80K, are deleveraging signatures; (6) VIX/VIX3M went from 0.880 to 0.935 in two sessions, so the curve has little room before backwardation.

**The Canary Watch verdict:** 🟡 **HIGH CAUTION**, the tenth straight week of caution and the third at this level. Composition changes: **Credit Spreads** goes from red to green (one print pending); **Sector Correlation** stays red with two new flips; **Market Breadth**, **Sector Rotation**, **VIX**, **Yield Curve**, **DXY**, **Geopolitics** and **Policy** unchanged. Of the four strict criteria, **one was met**: sector correlations flipped from positive to negative (XLU, XLRE). VIX touched above 20 intraday but did not close there; the curve is positive at every tenor; credit is under 250 on every print posted this week. **Issue #192** opened this run; related: #177 (last week's crossing), #183, #187, #190. Watch: (1) Friday Oct 30's OAS on Monday: HY–IG above 250 would make the Oct 22 print a pattern; (2) Apple Monday and AMD Tuesday; (3) SMH's 200-day ($519.50) on a close; (4) ISM Monday and refunding Wednesday; (5) midterms Tuesday; (6) payrolls Friday; (7) VIX 20 on a close and VIX/VIX3M above 1.00; (8) XLB at 0.117, the next correlation flip; (9) 10Y 5.00% on a close.

---

## COUNCIL READ — What This Means for Monday

*(Updated this week: credit went back under its trigger, two more correlations flipped negative, and VIX printed 23.93 intraday.)*

**Ophelia:** *"The Fed held with two dissents for a hike, GDP was 3.4%, core PCE did not cool, and the ten-year still fell, because Intel fell twenty-eight percent. The bond market took its rally from the equity market again. I said last week I would stop adding duration, and I have. Cash stays at 25–30%. Energy stays, with December at $104. The board did what I said it might: utilities and real estate went negative, so five sectors now move against the index. A diversified book beat the index on a week SPY fell. I keep it. A cap-weighted book is a growth bet and it knows it."*

**Marky:** *"Forty-two new highs on a day SMH fell seven percent. Last week I said the market was rotating, not breaking, and this is the same read with a bigger number. I am not calling Friday nothing: VIX printed 23.93 and VVIX 124 before the close took most of it back. I keep the hedge on through AMD, the midterms and payrolls, and I am not adding to it. If VIX closes above 20 with the ratio above one, that changes. Until then, the equal-weight index is still the trade, not the cap-weight one, and it has now been the trade for four weeks."*

**Cecil:** *"I said high yield to zero, and to keep it there until the spread printed back under 240. It printed 230 on Tuesday and 237 on Thursday. The rule I set is met, so the zero is no longer a rule, and I will not pretend otherwise. But I am not buying on Monday morning either. Everything I have is from before Friday, and Friday's print comes out Monday. CCC is a hundred and ten wider than it was on the first of October with HY–IG unchanged, so the bottom of the market has not healed. IG duration I keep. The trade is still the same: own the duration, not the credit."*

---

## SOURCES & REFERENCES

- Yahoo Finance (yfinance 1.6.0, single fetch 2026-10-31 ~19:47 ET): VIX, VIX3M, VVIX, SPY, RSP, QQQ, IWM, 12 sector ETFs, Treasury yield proxies (^IRX/^FVX/^TNX), DXY (DX-Y.NYB), FX (EURUSD=X, JPY=X, GBPUSD=X, CNY=X), copper (HG=F), Bitcoin (BTC-USD), bond ETFs (HYG, LQD, TLT), Brent (BZ=F, direction only); CLZ26.NYM, GCX26.CMX and GCZ26.CMX for checking and direction only
- data/market_state.json (Universe & Data Feed Builder): as_of 2026-10-30. WTI $104.12 (CLZ26) and gold $3,885.70 (GCX26) in facts.json are taken from it; CL=F and GC=F were not used
- CBOE: official VIX daily history (cdn.cboe.com VIX_History.csv), Fri 2026-10-30 close 19.42, high 23.93, exact match on all five closes; daily options market statistics (cdn.cboe.com daily_options) for total / equity / index / SPX put/call ratios, 9/21–10/30
- FRED (St. Louis Fed): the runner's own connection timed out on every series (two attempts, 20 and 50 seconds); all nine were downloaded in one fredgraph request through a second network path during the run. Live on this page: DGS2 (4.61%, Thu 10/29; source of the 2Y row and facts.json ust_2y), DGS10 / DGS3MO (cross-checks), BAMLH0A0HYM2 / BAMLC0A0CM / BAMLEMCBPIOAS / BAMLH0A3HYC through Thu 10/29, T10YIE through Fri 10/30, VIXCLS through Thu 10/29
- Federal Reserve: fed funds range and stance in facts.json unchanged (the Oct 28 meeting held the range); `next_macro_gate` rolled forward to ISM, the midterms, refunding, payrolls, CPI and the December FOMC from wiki/economic-calendar.md (updated 2026-10-31)
- Breadth: S&P 500 constituent closes via Yahoo (503 of 503 members with a Fri print; constituent list from Wikipedia's S&P 500 table), cross-checked against Finviz Elite (`finviz_elite breadth --json`, S&P 500 and market universes, fetched 2026-10-31 23:50 UTC); market-wide NYSE + Nasdaq + AMEX counts from the same Finviz Elite run. Only derived counts and percentages are published
- Internal desk cross-references, used for every news item on this page; none was re-sourced by this run: wiki/economic-calendar.md (FOMC, GDP, PCE, claims, confidence, hike odds, SOX, silver, WTI settles, December Brent, next week's calendar), wiki/energy.md
- GitHub issues cross-referenced this run: #177, #183, #185, #186, #187, #190. **One new issue opened this run: #192** (XLU and XLRE correlation flips; VIX intraday; HY–IG back under 250)

---

*Last updated by Saturday Research Crew: 2026-10-31 (single-agent run, on schedule; all market data as of Fri 2026-10-30 closes; macro/facts.json regenerated from the same fetch; breadth live from S&P 500 constituents with a Finviz Elite cross-check; put/call live from CBOE; FRED series live via a second network path after the runner's connection timed out; WTI and gold from the 2026-10-30 feed)*
*Next update: Every Saturday 7:39 PM ET*
*Data sources: Yahoo Finance (yfinance), data/market_state.json (feed), CBOE, FRED, Finviz Elite, Federal Reserve*
