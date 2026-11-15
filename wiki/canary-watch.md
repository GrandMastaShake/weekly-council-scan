# Wiki — Canary Watch

> **The Early Warning System for the Market Consciousness Orchestra**
>
> *"The canary does not predict the mine collapse. It simply dies first. Watch the canary."* — Marky

> **Truth layer:** every macro number on this page equals `macro/facts.json` (generated 2026-11-14, same fetch, commit e57f0b8, pushed ~20:00 ET ahead of Synthesis). Week ending Friday 2026-11-13 closes. `truth_check --facts` before push: 27 ok / 0 warn / **1 fail**: Bitcoin. Its Friday UTC bar ($68,249) is the value of record, but BTC kept falling over the weekend (Yahoo's live Sunday-UTC bar read $63,452, -7.0%, outside the 5% tolerance). That is a weekend market move, not a data error; see the cross-asset note.

> **Run note: on time.** Saturday run from 19:50 ET. **WTI and gold are from the 2026-11-13 feed** (`data/market_state.json`), not stale. **FRED timed out from the runner's own connection again** (seventh week); all nine series were fetched through a second network path and the raw CSV bytes were checked against the values used. FRED is posted through **Thu 2026-11-12** (one-day lag; 11/11 Veterans Day blank for Treasury series) and T10YIE through Fri 11/13. **No row on this page is stale.** Finviz Elite breadth ran cleanly and matches the constituent compute.

---

## VOLATILITY REGIME

| Metric | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| VIX | **19.30** | 25.64 | 19.99 | 🟢 **Every close under 20: 19.92 / 19.46 / 17.49 / 18.70 / 19.30; intraday high 25.08 Mon, 20.92 Fri** |
| VIX 20-Day MA | ~19.38 | ~18.83 | — | — |
| VIX Trend | **-24.7% WoW** | — | — | — |
| VIX3M (term structure) | 20.62 (VIX/VIX3M **0.936**) | 24.60 (1.042) | 20.50 (0.975) | 🟢 **Back in contango all week: 0.955 / 0.943 / 0.909 / 0.932 / 0.936** |
| Implied SPY Move (30D) | ~±5.6% | ~±7.4% | — | — |
| VVIX (VIX of VIX) | **101.53** | 121.94 | 109.91 | 🟡 **90.47 low Wed; up into Friday** |
| Total Put/Call Ratio (CBOE) | 0.85 (5D avg 0.90) | 0.95 (5D avg 0.91) | 0.92 | 🟢 **0.88 / 0.95 / 0.92 / 0.89 / 0.85** |
| Equity Put/Call Ratio (CBOE) | 0.63 (5D avg 0.65) | 0.59 (5D avg 0.64) | 0.65 | 🟢 **0.77 Tue (CPI day) the high** |

> *Source note: VIX prints vary by vendor — discrepancies of ~2–3 pts are common across quote sources (delayed feeds, spot vs. VX futures, stale prints). Canonical reference: CBOE official close / FRED VIXCLS. This week the Friday close was cross-checked against the **CBOE official daily history file (VIX_History.csv): Fri 2026-11-13 close 19.30, high 20.92, low 17.64**, an exact match for Yahoo ^VIX on all five closes. **FRED VIXCLS** is posted through Thu 11/12 (18.70) and agrees. **Put/call ratios** are from CBOE's official daily market statistics file (cdn.cboe.com daily_options), Fri 2026-11-13 vs. Fri 2026-11-06 and Fri 2026-10-16 (20 sessions back); 5D averages are Mon–Fri of each week. Index put/call 0.96 Friday (5D avg 1.01). CBOE renamed the SPX row to "SPX + SPXW + SPXO" from Nov 9: 1.19 Friday (5D avg 1.12, vs. SPX + SPXW 1.18 the week before).*

**Marky Interpretation:** Last week's alarm did not survive Monday. VIX opened at 25.08 and closed **19.92**; it has not closed over 20 since. The ratio went back under one on Monday and stayed there (**0.936** Friday), so the curve is back in contango. That happened in a week with a hot CPI (+0.4% headline, +0.3% core) and the 10-year over 5%: the equity market did not treat higher yields as a volatility event. VVIX came down from 122 to 90 by Wednesday and then rose to 101.5 into Friday, when VIX touched 20.92 intraday. Put/call stayed calm (total 0.85 Friday). Next week is Warsh on Monday and the FOMC minutes on Wednesday.

---

## YIELD CURVE

| Maturity | Yield | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| 13-Week (T-Bill) | 4.122% | +0.122% | +0.052% (vs. 4.070% on 10/16) | **Closes 4.035 / 4.115 / 4.115 / 4.128 / 4.122; December hike ~88–89% (wiki/economic-calendar.md)** |
| 2-Year | **4.86%** (FRED DGS2, Thu 11/12 — see note) | **+0.40%** (vs. 4.46% Thu 11/05) | +0.06% (vs. 4.80% Fri 10/09) | **4.51 / 4.56 / 4.73 / — / 4.86 from last Friday; Friday 11/13 not yet posted** |
| 5-Year | 4.981% | +0.333% | +0.082% | Closes 4.659 / 4.807 / 4.827 / 4.945 / 4.981 |
| **10-Year** | **5.154%** | **+0.295%** | +0.056% (vs. 5.098%) | 🔴 **Back over 5.00%: closes 4.864 / 4.983 / (holiday) / 5.103 / 5.154; issue #206** |
| **10Y–2Y Spread** | **~+29 bps** (Fri 10Y vs. Thu 2Y) | -11 bps vs. last week's +40 | — | **Flatter: the front end rose more; same-day Thursday basis +24** |
| **10Y–5Y Spread** | **~+17.3 bps** | -3.8 bps (was +21.1) | — | Flatter |
| **10Y–3M Spread** | **~+103 bps** | +17 bps (was +86) | — | **Steeper on the long end** |

> *2Y source: FRED DGS2, Thu 2026-11-12 (FRED's one-day lag; Wed 11/11 Veterans Day has no print), so the 10Y–2Y spread pairs Friday's 10Y with Thursday's 2Y. Same-day Thursday (FRED DGS10 5.10% vs. DGS2 4.86%) the spread is +24. Friday 11/06's DGS2 has since posted at 4.51%. ^TNX prints a Veterans Day value (4.998) that is not a cash-market close and is excluded above. ^IRX is a discount-basis T-bill yield; FRED's constant-maturity 3M (DGS3MO) was 4.32% Thursday, about 20 bps higher, so a CMT-basis 10Y–3M would read ~+78 to +83 bps. This page and facts.json use ^IRX for series continuity.*

**Ophelia Interpretation:** This week the rise came through real yields. The 10-year rose **29.5 bps to 5.154%** and the 10Y breakeven barely moved (**T10YIE 2.24%**, from 2.23%), so the real 10-year is about **2.91%**, up from 2.63%. The 2-year rose more, **+40 bps to 4.86%** on FRED's Thursday print, after a hot October CPI (+0.4% headline, +0.3% core, the third straight hot core) and Fed hike talk took December odds to about 88–89% (wiki/economic-calendar.md). Bills rose 12 bps. The 2s10s flattened to about +29 while the 10Y–3M steepened to +103. There is no inversion at any maturity, but the 10-year is now **9.6 bps under the 5.25% crisis line** (wiki/economic-calendar.md).

**Yield Curve Regime:** 🟡 **Positive; bear move led by the front end, real yields up.** 10Y 5.154%, 15.4 bps over 5.00%. Next gates: **Warsh Mon Nov 16; FOMC minutes and the 20Y auction Wed Nov 18; November payrolls Dec 4; FOMC Dec 9; November CPI Dec 10.**

---

## CREDIT SPREADS

> *OAS rows are FRED's **Thu 2026-11-12** prints (one-day lag; the ICE series have no 11/10 row), with Thu 11/05 as the week-ago column and Fri 10/09 as the month-ago column. Friday Nov 6's prints, flagged last week as the confirming read, posted at HY 342, IG 93, **HY–IG 249**: just under the line, so the Nov 5 crossing (255) was not confirmed. HYG and LQD are live Friday closes.*

| Spread | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| HY OAS (ICE BofA US HY, BAMLH0A0HYM2) | **320 bps** (Thu 11/12) | 348 bps | 311 bps | 🟢 **Tighter every print: 342 / 334 / 330 / 320 since last Friday** |
| IG OAS (ICE BofA US Corp, BAMLC0A0CM) | 89 bps (Thu 11/12) | 93 bps | 83 bps | 🟢 **93 / 91 / 90 / 89** |
| **HY–IG Spread** | **231 bps** (Thu 11/12) | 255 bps | 228 bps | 🟢 **BACK UNDER 250: 249 / 243 / 240 / 231** |
| EM Corporate OAS (BAMLEMCBPIOAS) | 167 bps (Thu 11/12) | 184 bps | 155 bps | 🟢 **-17 on the week** |
| CCC & Lower OAS (ICE BofA, BAMLH0A3HYC) | **1,314 bps** (Thu 11/12) | 1,320 bps | 1,253 bps | 🟡 **Barely moved; 1,330 Wednesday** |
| **HYG Price** | **$76.94** | **$77.23** | **$76.86** | 🟡 **-0.38% (duration hit)** |
| **LQD Price** | **$102.81** | **$104.53** | **$103.40** | 🟡 **-1.65% on the +29.5 bp 10Y** |

**Cecil Interpretation:** Last week I said a second print over 250 would make it the pattern. It did not come: Friday Nov 6 posted **249**, and every print since has been tighter, ending at **231** on Thursday, with HY OAS down 28 bps to **320**. The spread move is equity-led: it widened on the 4.4% day and tightened as stocks recovered. Two things did not move with it. **CCC stayed at about 1,314**, so the bottom tier is not tightening with the rest (**CCC-minus-HY is about 994 bps**, from 972), and the bond prices fell: **LQD -1.65%, HYG -0.38%**, because the rate move was larger than the spread move.

**Credit Regime:** 🟢 **Back under the line.** HY–IG 231 on Nov 12; HY OAS 320; CCC 1,314. The Nov 5 crossing (issue #202) was not confirmed by a second print. The risk in credit this week is duration, not spread.

---

## MARKET BREADTH

> *S&P 500 rows are computed from the daily closes of all 503 constituents with a Fri 2026-11-13 print (Yahoo, list from Wikipedia's S&P 500 table; 50D/200D = simple MA of closes; a new high/low means the day's high/low reached the trailing 252-session extreme). They are cross-checked against **Finviz Elite** (`finviz_elite breadth`, S&P 500 universe, 503 members), which agrees exactly on advancers/decliners (315 / 185) and new lows (1), and on new highs (8), and within one name on members above each average (359 vs. 358 here above the 50D; 319 vs. 318 above the 200D), giving 71.37% vs. 71.3% here on % above 50D and 63.42% vs. 63.6% on % above 200D; the gaps are denominators (502 / 500 members with full history here, 503 there). Market-wide rows are Finviz's NYSE + Nasdaq + AMEX stock totals for Friday (5,582 stocks, ETFs and funds excluded). The 1W and 1M comparisons are recomputed from this fetch on the current 503-member list; 1M is Fri 10/16, 20 sessions back.*

| Metric | Current | 5D Avg | 20D Avg | Regime |
|---|---|---|---|---|
| S&P 500 Advance/Decline (Fri) | **1.70** (315 up / 185 down) | 2.08 | 1.67 | 🟢 **Advancers 423 / 247 / 332 / 124 / 315** |
| Market-wide Advance/Decline (Fri, Finviz) | 0.85 (2,456 up / 2,899 down) | — | — | 🟡 **Worse than the S&P on Friday** |
| S&P 500 New 52-Week Highs | **8** | 13.2 | 23.7 | 🟡 **16 / 7 / 17 / 18 / 8; well under 65–77 a week earlier** |
| S&P 500 New 52-Week Lows | **1** | 2.0 | 4.1 | 🟢 **Highs beat lows every day** |
| Market-wide New Highs / Lows (Fri, Finviz) | 75 / 453 | — | — | 🔴 **Lows 86% of the total** |
| **S&P 500 % Above 50D MA** | **71.3%** (1W 61.4%, 1M 45.0%) | 70.1% | 62.5% | 🟢 **Above 50%; 71.7% Wed, the high of the fetch** |
| **S&P 500 % Above 200D MA** | **63.6%** (1W 55.8%, 1M 51.8%) | 62.8% | 59.4% | 🟢 **+7.8 pts on the week** |
| Market-wide % Above 50D / 200D (Fri, Finviz) | 40.0% / 39.1% | — | — | 🔴 **At the 40% line on the 50D, under it on the 200D** |
| Equal-Weight (RSP) vs. Cap-Weight (SPY), 1W | **-0.22 pts** (RSP +2.37% vs. SPY +2.59%) | — | 1M: **+5.13 pts** | 🟡 **First week behind after five ahead** |
| Sector ETFs above own 50D MA | **7 of 12** (XLY, XLF, XLB, XLRE, XLV, XLU, XLP) | — | — | 🟡 **XLE 3 cents under ($64.96 vs. $64.99); XLK, SMH, XLC, XLI below** |

**Marky Interpretation:** The S&P's average member had its best week of the fetch: **71.3% above the 50-day** and **63.6% above the 200-day**, up 10 and 8 points, with new highs beating new lows every day. **SPY rose +2.59% to $754.37**, back $22 over its 200-day ($731.92) but still 1.3% under its 50-day ($764.43). Two things hold the read back. New highs did not expand (8 Friday, against 65–77 the week before), and **RSP lagged SPY for the first time in six weeks**, because the bounce came from the large-cap tech names that led the drop. Finviz Elite agrees within one name.

Outside the index it is still weak. Market-wide, only **40.0%** of stocks are above their 50-day, there were **453 new lows against 75 highs**, and Friday's market-wide A/D was 0.85 while the S&P's was 1.70.

**Breadth Regime:** 🟢 **Clear on the trigger.** S&P 500 % above 50D (71.3%) is well above the 50% yellow line. Market-wide gauges remain red.

---

## SECTOR CORRELATION MATRIX

*30-day rolling correlation of daily returns vs. SPY (30-calendar-day window, 22 sessions 2026-10-15 → 2026-11-13; the 1W-ago column is last week's published window ending 2026-11-06)*

| Sector | ETF | vs. SPY Correlation | 1W Ago | Regime |
|---|---|---|---|---|
| 🖥️ Technology | XLK | **0.912** | 0.906 | 🔥 **High beta** |
| 💻 Semiconductors | SMH | **0.849** | 0.809 | 🔥 **High beta** |
| ⚙️ Industrials | XLI | **0.785** | 0.777 | 🔥 **High beta** |
| 🛍️ Consumer Discretionary | XLY | **0.769** | 0.832 | 🔥 **High beta** |
| 🏦 Financials | XLF | **0.601** | 0.692 | 🟡 **Moderate** |
| ⛏️ Materials | XLB | **0.560** | 0.586 | 🟡 **Moderate** |
| 🏥 Healthcare | XLV | **0.535** | 0.473 | 🟡 **Moderate** |
| 📡 Communication Services | XLC | **0.527** | 0.454 | 🟡 **Moderate** |
| 🏠 Real Estate | XLRE | **0.402** | 0.482 | 🟡 **Moderate** |
| ⚡ Utilities | XLU | **0.072** | 0.089 | 🟡 **Near zero** |
| 🍞 Consumer Staples | XLP | **0.043** | -0.015 | 🟡 **Back positive (negative → positive), barely** |
| ⛽ Energy | XLE | **0.026** | -0.108 | 🟡 **Back positive (negative → positive), barely** |

> *Recompute note: this fetch reproduces last week's window (2026-10-08 → 11-06) close to the published values for the high-beta sectors but lower for several others: XLY 0.775 (published 0.832), XLF 0.605 (0.692), XLC 0.390 (0.454), XLRE 0.415 (0.482), XLU -0.007 (0.089), XLP -0.052 (-0.015), XLE -0.072 (-0.108). Yahoo's bars for these funds were revised, most likely for distributions. The 1W column keeps the published values. On either basis, no sector crossed from positive to negative this week.*

**Ophelia Interpretation:** For the first time in weeks, **all twelve sectors correlate positively with SPY**. Energy and staples crossed back above zero, though only to 0.026 and 0.043, and utilities are at 0.072. These three are the only sectors still moving mostly on their own news: energy on Iran (#207), utilities on Constellation's quarter and the 10-year, staples on a sixth straight up week. Everything else moves with the index, and tech and semis are the most tied to it (0.912 and 0.849).

**The key insight:** the book has three near-zero sectors left as diversifiers, and none is negative. When yields rose 30 bps this week, bonds fell too (TLT -3.10%), so duration did not offset equity risk either.

**Alert:** No strict-criterion flip (positive → negative) this week. Two sectors went the other way, negative → positive (XLP, XLE).

---

## SECTOR ROTATION FLOW

*1-Day / 1-Week / 1-Month performance vs. SPY (1D = Fri 11/13 vs. Thu 11/12; 1W = Fri-to-Fri; 1M = 21 sessions from 2026-10-15). SPY: -0.36% / +2.59% / -2.26%.*

| Sector | ETF | 1D vs. SPY | 1W vs. SPY | 1M vs. SPY | Rotation Signal |
|---|---|---|---|---|---|
| ⛽ Energy | XLE | +1.34% | **+2.83%** | -0.14% | 🟢 **Inflow (leader: +5.42%; Iran re-escalation, #207)** |
| 💻 Semiconductors | SMH | -2.63% | +2.32% | -10.64% | 🟡 **Bounce (+4.91%; -2.99% Friday; still under the 200D)** |
| ⚙️ Industrials | XLI | -0.03% | +1.17% | +2.79% | 🟢 **Inflow (+3.76%)** |
| 📡 Communication Services | XLC | +1.41% | +1.13% | -1.08% | 🟢 **Inflow (+3.72%; CHTR +17.2%)** |
| 🖥️ Technology | XLK | -1.65% | +0.77% | -7.74% | 🟡 **Bounce (+3.36%; -2.01% Friday)** |
| 🏦 Financials | XLF | +1.17% | +0.07% | +8.43% | 🟡 **In line (+2.66%)** |
| 🍞 Consumer Staples | XLP | +1.78% | -0.07% | +8.80% | 🟡 **In line (+2.52%; 52-week closing high Fri)** |
| 🏥 Healthcare | XLV | +0.90% | -0.40% | +8.84% | 🟡 **In line (+2.19%)** |
| ⚡ Utilities | XLU | +0.88% | -0.48% | +8.00% | 🟡 **In line (+2.11%; first Friday over the 200D since Jul 24)** |
| 🛍️ Consumer Discretionary | XLY | -0.04% | -0.55% | +8.05% | 🟡 **In line (+2.04%)** |
| 🏠 Real Estate | XLRE | +0.38% | -1.75% | +7.93% | 🔴 **Lagging (+0.84%; 10Y over 5%, #206)** |
| ⛏️ Materials | XLB | +0.15% | **-2.05%** | +5.56% | 🔴 **Lagging (+0.54%; DXY 52-week high, gold -4.5%)** |

**Ophelia Interpretation:** **All twelve sectors rose**, and the order reversed from last week. The three that lagged then (XLE, SMH, XLK) are three of the top five now. **Energy led** at +5.42% on the Iran re-escalation (#207), even though December WTI fell 2.5% on the week. **SMH +4.91% and XLK +3.36%** bounced, but both fell 2–3% on Friday and SMH is still about 13% under its 50-day. The rate-sensitive and commodity sectors lagged: **XLRE +0.84%** with the 10-year over 5%, **XLB +0.54%** with the dollar at a 52-week high and gold down 4.5%. **The XLK leadership trigger cleared** (+0.77 vs. SPY on the week). Over a month the split is still wide: **XLV +8.84, XLP +8.80, XLF +8.43** ahead of SPY; **SMH -10.64, XLK -7.74** behind.

**The risk:** the defensive sectors kept pace in a rising market only because everything rose. Their month-long lead was built when the index was falling.

---

## CROSS-ASSET SIGNALS

| Asset | Level | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| DXY (US Dollar Index) | **103.41** (Yahoo DX-Y.NYB) | +1.09% | +1.54% | 🟡 **52-week closing high; five higher closes: 101.65 / 102.23 / 102.91 / 103.17 / 103.41** |
| EUR/USD | 1.1050 | -1.59% | -1.45% | 🟡 **Down four of five days** |
| USD/JPY | 159.875 | +1.51% | +1.10% | 🟡 **Approaching 160** |
| GBP/USD | 1.3231 | -1.67% | -0.31% | 🟡 — |
| WTI Crude | **$88.56 (CLZ26 settle, as_of 2026-11-13)** | **-2.5%** (feed, same contract; Nov 6 $90.83) | **-12.7%** (feed, 4W) | 🟢 **Under $90 despite the Iran re-escalation (#207)** |
| Gold | **$3,879.70 (GCX26 settle, as_of 2026-11-13)** | **-4.5%** (feed; Nov 6 $4,064.50) | **-6.7%** (feed, 4W) | 🔴 **Back under $4,000 as real yields rose 28 bps** |
| Copper | $6.0795/lb (HG=F front month) | -2.23% | -6.91% | 🟡 **Lowest close of the fetch** |
| Bitcoin | $68,249 (Fri 11/13 UTC close) | -9.90% | -16.26% | 🔴 **Four lower closes from $75,223; ~$63,450 on the weekend (see note)** |
| HY Bonds (HYG) | $76.94 | -0.38% | +0.10% | 🟡 **Spreads tighter, rates higher** |
| IG Bonds (LQD) | $102.81 | -1.65% | -0.57% | 🔴 **Duration loss** |
| Long Treasuries (TLT) | $79.38 | -3.10% | -0.84% | 🔴 **Bonds fell with stocks rising** |
| TIPS Breakeven (10Y) | 2.24% (FRED T10YIE, Fri 11/13) | +0.01 pts | — | 🔴 **Flat: the whole 10Y move was real yield (~2.91%, from 2.63%)** |

> *DXY from Yahoo's ICE DXY series (DX-Y.NYB), carried in macro/facts.json at 103.41 (tolerance 1%). 1W changes use this run's Yahoo fetch for both endpoints; 1M is vs. Fri 10/16. **FX daily bars:** per macro/README.md, Yahoo's daily bar for a pair closes near its open until the provider replaces it; facts.json carries the daily bars (159.875, 1.1050). **WTI and gold (feed contract):** facts.json carries WTI $88.56 (CLZ26, yahoo:CLZ26.NYM) and gold $3,879.70 (GCX26, yahoo:GCX26.CMX), as_of 2026-11-13, from `data/market_state.json`; both passed `truth_check --facts` against the contracts' own bars. The continuous symbols CL=F and GC=F were not used. Weekly and 4-week changes are the feed's own (d1w / d4w). **Bitcoin:** the Fri 11/13 UTC daily bar is present ($68,249, same value and as_of in facts.json). Bitcoin trades through the weekend, and `truth_check --facts` read $63,452 on Yahoo's Sunday-UTC bar at check time, 7.0% under the Friday value, outside the 5% tolerance: a live market move after the Friday close, not a data error. The Friday close is the value of record.*

**Ophelia Interpretation:** **Real yields took over this week.** The 10-year rose 29.5 bps and the breakeven did not move, so the real yield rose about 28 bps to **~2.91%**. Everything that competes with real yield fell: **gold -4.5%** to **$3,879.70** (back under $4,000), **Bitcoin -9.90%** to $68,249 and lower again on the weekend, **TLT -3.10%**, **LQD -1.65%**. **The dollar made a 52-week closing high** at 103.41, and USD/JPY is near 160. **Oil did not add a premium**: December WTI fell 2.5% to $88.56 in a week of renewed Iran headlines (#207), while energy equities rose 5.42%. **Copper fell to its lowest close of the fetch.**

**The risk:** with real yields near 2.9% and the dollar at a 52-week high, financial conditions are tightening on their own before the Fed's December meeting.

---

## CANARY WATCH TRIGGER BOARD

| Signal | Status | Trend | Trigger Level |
|---|---|---|---|
| VIX Regime | 🟢 **Clear: every close under 20** | -24.7% WoW to 19.30; VVIX 101.53; VIX/VIX3M **0.936** (contango all week) | 🟡 >20 | 🔴 >25 |
| Yield Curve | 🟡 Positive, front end higher | 10Y 5.154% (+29.5 bps; over 5.00%, #206); 2Y 4.86% Thu (+40 bps); 10Y–2Y ~+29 (+24 same-day Thu), 10Y–3M +103 (+17) | 🟡 <0 (inverted) | 🔴 <-50 bps |
| Credit Spreads | 🟢 **Back under the line** | HY–IG **231 bps** Thu 11/12 (249 on 11/06, 255 on 11/05); HY OAS 320; CCC 1,314; LQD -1.65% | 🟡 HY–IG >250 bps | 🔴 >350 bps |
| Market Breadth | 🟢 **Clear, strongest of the fetch** | S&P 500 71.3% above 50D (61.4% last week), 63.6% above 200D (55.8%); new highs/lows 8 / 1; RSP -0.22 pts vs. SPY WoW; market-wide 40.0% above 50D | 🟡 <50% above 50D MA | 🔴 <40% |
| Sector Rotation | 🟢 **Leadership trigger cleared: XLK +0.77 vs. SPY** | All twelve up; XLE leads (+5.42%); XLRE, XLB lag; XLK -7.74 vs. SPY over a month | 🟡 XLK -5% vs. SPY | 🔴 XLK -10% |
| Sector Correlation | 🟡 **No flip; all twelve positive** | XLE 0.026, XLP 0.043, XLU 0.072 the only near-zero readings; XLK 0.912 | 🔴 positive → negative flip | — |
| DXY | 🟡 **52-week closing high** | 103.41 (+1.09% WoW) | 🟡 >102 | 🔴 >105 |
| Geopolitics | 🟡 **Iran re-escalation, oil not following** | WTI $88.56 (CLZ26, Fri settle; facts.json), -2.5%; XLE +5.42% (#207) | 🟡 Oil >$90 | 🔴 Oil >$100 |
| Credit Risk | 🟡 Spreads tighter, CCC flat (CDS not sourced) | XLF +2.66% to $58.68; EM OAS -17 bps W/W | 🟡 CDS widening | 🔴 Bank stress |
| Policy | 🔴 **Live hiking cycle; December odds ~88–89%** | Fed 3.75–4.00%; Oct CPI +0.4% / core +0.3%; Warsh 11/16, minutes 11/18, FOMC 12/9 | — | — |
| Overall Risk | 🟡 **HIGH CAUTION: rates, dollar and policy, not volatility or credit** | — | — | — |

**Weekly Narrative — Overall Assessment:** The equity market recovered and the bond market did not. The ledger: (1) **SPY rose +2.59% to $754.37**, back $22 over its 200-day, still under its 50-day; (2) **VIX closed under 20 every day**, ending at **19.30**, with VIX/VIX3M back to **0.936**, so last week's alarm and backwardation are gone; (3) **HY–IG tightened to 231**, and Friday Nov 6 posted at 249, so the Nov 5 crossing was never confirmed; (4) **the 10-year rose 29.5 bps to 5.154%**, back over 5.00% (#206), the 2-year rose 40 bps, and the breakeven did not move, so the real 10-year rose to about 2.91%; (5) **October CPI was hot** (+0.4% headline, +0.3% core) and December hike odds rose to about 88–89%; (6) **S&P 500 breadth was the strongest of the fetch**: 71.3% above the 50-day, 63.6% above the 200-day; (7) **all twelve sectors rose**, led by energy (+5.42%) on the Iran re-escalation (#207), and the XLK leadership trigger cleared; (8) **every sector now correlates positively with SPY**; (9) **the dollar made a 52-week closing high** (103.41), and **gold fell -4.5%** to $3,879.70, **Bitcoin -9.90%**, **TLT -3.10%**; (10) December WTI fell 2.5% to $88.56.

The fragilities: (1) the 10-year is 9.6 bps under the 5.25% crisis line, with Warsh and the minutes next week; (2) bonds and stocks no longer offset each other: rates up 30 bps and TLT -3.1% in an up week for stocks; (3) no sector is negatively correlated with the index; (4) the dollar and real yields are tightening conditions before the Fed acts; (5) market-wide breadth is still red (453 new lows, 40% above the 50-day) while the S&P's is green; (6) the tech bounce faded on Friday (XLK -2.01%, SMH -2.99%).

**The Canary Watch verdict:** 🟡 **HIGH CAUTION**, down from ELEVATED. Composition changes: **VIX Regime** goes from red to green; **Credit Spreads** from yellow to green; **Sector Rotation** from yellow to green (leadership trigger cleared); **Geopolitics** stays yellow on #207 although oil is under $90; **Yield Curve**, **Sector Correlation**, **DXY**, **Credit Risk** stay yellow; **Policy** stays red; **Market Breadth** stays green. Of the four strict criteria, **none was met**: VIX did not close above 20, the curve is positive at every maturity, HY–IG is 231, and no correlation flipped from positive to negative. **No new issue this run.** Related: #202 (last week's VIX/credit alarm, now cleared), #206 (10Y over 5%), #207 (energy/Iran), #208, #209. Watch: (1) a 10Y close over 5.25%; (2) Warsh Monday and the FOMC minutes Wednesday; (3) DXY at 105, the red line; (4) VIX back over 20 with VIX/VIX3M over 1.00; (5) SPY's 50-day ($764.43) on a close; (6) XLE, XLP and XLU turning negative, which would be a strict flip.

---

## COUNCIL READ — What This Means for Monday

*(Updated this week: the VIX alarm and the credit crossing both cleared, and the 10-year went back over 5%.)*

**Ophelia:** *"Last week I was worried about volatility and credit. Both cleared. This week the problem is rates. The 10-year rose thirty basis points with the breakeven unchanged, so it is real yield, and December is close to 90%. I keep cash at 25–30%. I do not add duration, because bonds fell with stocks this week and did not protect anything. Energy I left out last week on the oil trigger, and oil is still under $90, so I do not buy the 5% energy week on headlines. The level I am watching is 5.25% on the 10-year."*

**Marky:** *"I said I would take the extra hedge off if VIX closed back under 20 with the ratio under one after CPI. It did both, every day. I take it off and keep the base hedge. The S&P's breadth is the best of the fetch, but new highs did not expand and equal weight lagged for the first time in six weeks. The tech bounce gave back part of it on Friday. I want a close over the 50-day before I add."*

**Cecil:** *"Spreads tightened every day, and the crossing at 255 was never confirmed. That is good for credit and I do not dispute it. But LQD lost 1.65% and HYG 0.38% in a week when spreads tightened, because rates did the damage. CCC did not tighten with the rest. I stay at zero in high yield and I keep IG duration, but I keep it sized for a 10-year at 5.25%, not 5.00%."*

---

## SOURCES & REFERENCES

- Yahoo Finance (yfinance, single fetch 2026-11-14 ~19:47 ET): VIX, VIX3M, VVIX, SPY, RSP, 12 sector ETFs, Treasury yield proxies (^IRX/^FVX/^TNX), DXY (DX-Y.NYB), FX (EURUSD=X, JPY=X, GBPUSD=X, AUDUSD=X, CNY=X), copper (HG=F), Bitcoin (BTC-USD), bond ETFs (HYG, LQD, TLT, IEF)
- data/market_state.json (Universe & Data Feed Builder, run 2026-11-14 09:25–09:52 ET): as_of 2026-11-13. WTI $88.56 (CLZ26) and gold $3,879.70 (GCX26) in facts.json are taken from it, with their d1w / d4w changes; CL=F and GC=F were not used
- CBOE: official VIX daily history (cdn.cboe.com VIX_History.csv), Fri 2026-11-13 close 19.30, high 20.92, exact match on all five closes; daily options market statistics (cdn.cboe.com daily_options) for total / equity / index / SPX put/call ratios, 10/15–10/16 and 11/2–11/13
- FRED (St. Louis Fed): the runner's own connection timed out (15-second probe and repeated attempts). All nine series were fetched through a second network path during the run, and the saved raw CSV bytes were checked against every value used. Live on this page: DGS2 (4.86%, Thu 11/12; source of the 2Y row and facts.json ust_2y), DGS10 / DGS3MO (cross-checks), BAMLH0A0HYM2 / BAMLC0A0CM / BAMLEMCBPIOAS / BAMLH0A3HYC through Thu 11/12, T10YIE through Fri 11/13, VIXCLS through Thu 11/12
- Federal Reserve: fed funds range and stance in facts.json unchanged; `next_macro_gate` rolled forward to Warsh, the FOMC minutes and 20Y auction, Thanksgiving week, November payrolls, the December FOMC and November CPI from wiki/economic-calendar.md (updated 2026-11-14)
- Breadth: S&P 500 constituent closes via Yahoo (503 of 503 members with a Fri print; constituent list from Wikipedia's S&P 500 table), cross-checked against Finviz Elite (`finviz_elite breadth --json`, S&P 500 and market universes, fetched 2026-11-15 00:52 UTC); market-wide NYSE + Nasdaq + AMEX counts from the same Finviz Elite run. Only derived counts and percentages are published
- Internal desk cross-references, used for every news item on this page; none was re-sourced by this run: wiki/economic-calendar.md (CPI, PPI, hike odds, Warsh, minutes, 5.25% line), wiki/energy.md, wiki/utilities.md, wiki/consumer-staples.md, wiki/materials.md, wiki/real-estate.md, wiki/communication-services.md
- GitHub issues cross-referenced this run: #202, #206, #207, #208, #209. **No new issue opened this run** (none of the four strict criteria met)

---

*Last updated by Saturday Research Crew: 2026-11-14 (single-agent run, Saturday evening; all market data as of Fri 2026-11-13 closes; macro/facts.json regenerated from the same fetch; breadth live from S&P 500 constituents with a Finviz Elite cross-check; put/call live from CBOE; FRED series live via a second network path after the runner's connection timed out; WTI and gold from the 2026-11-13 feed)*
*Next update: Every Saturday 7:39 PM ET*
*Data sources: Yahoo Finance (yfinance), data/market_state.json (feed), CBOE, FRED, Finviz Elite, Federal Reserve*
