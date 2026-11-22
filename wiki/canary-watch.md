# Wiki — Canary Watch

> **The Early Warning System for the Market Consciousness Orchestra**
>
> *"The canary does not predict the mine collapse. It simply dies first. Watch the canary."* — Marky

> **Truth layer:** every macro number on this page equals `macro/facts.json` (generated 2026-11-21, same fetch, commit 534cfed, pushed ~19:58 ET ahead of Synthesis). Week ending Friday 2026-11-20 closes. `truth_check --facts` before push: **28 ok / 0 warn / 0 fail**. Bitcoin's Friday UTC bar ($58,799) is the value of record; Yahoo's live Sunday-UTC bar read $60,069 at check time (+2.2%, inside the 5% tolerance).

> **Run note: on time.** Saturday run from 19:46 ET. **WTI and gold are from the 2026-11-20 feed** (`data/market_state.json`), not stale. **FRED timed out from the runner's own connection again** (eighth week, Python and curl both); all nine series were fetched through a second network path and the values used are the ones that path returned. FRED is posted through **Thu 2026-11-19** (one-day lag) and T10YIE through Fri 11/20, so **the credit and 2-year rows do not include Friday**, the largest day of the week. **No row on this page is stale.** Finviz Elite breadth ran cleanly and matches the constituent compute.

---

## VOLATILITY REGIME

| Metric | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| VIX | **35.89** | 19.30 | 19.45 | 🔴 **Every close over 22, three over 25: 22.91 / 25.46 / 24.56 / 28.44 / 35.89; intraday high 40.03 Fri. Highest close of the fetch (since Aug 2025)** |
| VIX 20-Day MA | ~21.70 | ~19.38 | — | — |
| VIX Trend | **+86.0% WoW** | — | — | — |
| VIX3M (term structure) | 30.94 (VIX/VIX3M **1.160**) | 20.62 (0.936) | 20.48 (0.950) | 🔴 **Backwardation from Tuesday: 0.995 / 1.019 / 1.011 / 1.052 / 1.160** |
| Implied SPY Move (30D) | ~±10.4% | ~±5.6% | — | — |
| VVIX (VIX of VIX) | **138.03** | 101.53 | 109.70 | 🔴 **114.23 / 121.28 / 118.37 / 127.10 / 138.03; fetch high is 140.44 (Mar 6)** |
| Total Put/Call Ratio (CBOE) | 1.13 (5D avg 1.02) | 0.85 (5D avg 0.90) | 0.93 | 🔴 **0.95 / 0.98 / 1.05 / 1.01 / 1.13; three closes over 1.00** |
| Equity Put/Call Ratio (CBOE) | 0.77 (5D avg 0.71) | 0.63 (5D avg 0.65) | 0.67 | 🟡 **0.73 / 0.71 / 0.72 / 0.62 / 0.77** |

> *Source note: VIX prints vary by vendor — discrepancies of ~2–3 pts are common across quote sources (delayed feeds, spot vs. VX futures, stale prints). Canonical reference: CBOE official close / FRED VIXCLS. This week the Friday close was cross-checked against the **CBOE official daily history file (VIX_History.csv): Fri 2026-11-20 close 35.89, high 40.03, low 26.94**, an exact match for Yahoo ^VIX on all five closes. **FRED VIXCLS** is posted through Thu 11/19 (28.44) and agrees. **Put/call ratios** are from CBOE's official daily market statistics file (cdn.cboe.com daily_options), Fri 2026-11-20 vs. Fri 2026-11-13 and Fri 2026-10-23 (20 sessions back); 5D averages are Mon–Fri of each week. Index put/call 1.27 Friday (5D avg 1.12, from 1.01). SPX + SPXW + SPXO 1.41 Friday (5D avg 1.26, from 1.12).*

**Marky Interpretation:** Last week I said the alarm had not survived Monday. This week it came back on Monday and never left. VIX closed over 20 on all five days and ended at **35.89**, the highest close in this fetch, after touching 40.03 on Friday. The curve inverted on Tuesday and the ratio ended at **1.160**, which is deeper than the 1.042 two weeks ago. VVIX is at 138, two points under the March high. The options market caught up late: total put/call did not close over 1.00 until Wednesday and ended at 1.13, and equity put/call is only 0.77. That is hedging through index products, not yet capitulation in single names. The catalysts were not macro (wiki/economic-calendar.md: a reported SEC probe of NVIDIA, a new chip export rule, a failed IPO pop), and the biggest day had one second-tier release.

---

## YIELD CURVE

| Maturity | Yield | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| 13-Week (T-Bill) | 4.122% | 0.000% | +0.090% (vs. 4.032% on 10/23) | **Closes 4.125 / 4.138 / 4.145 / 4.147 / 4.122; December hike ~95–96% (wiki/economic-calendar.md)** |
| 2-Year | **4.76%** (FRED DGS2, Thu 11/19 — see note) | **-0.10%** (vs. 4.86% Thu 11/12) | +0.11% (vs. 4.65% Thu 10/22) | **4.88 / 4.83 / 4.80 / 4.80 / 4.76 from last Friday; Friday 11/20 not yet posted** |
| 5-Year | 4.701% | -0.280% | -0.104% | Closes 4.935 / 4.900 / 4.884 / 4.866 / 4.701 |
| **10-Year** | **4.912%** | **-0.242%** | -0.076% (vs. 4.988%) | 🟢 **Back under 5.00%: closes 5.121 / 5.103 / 5.066 / 5.052 / 4.912; -14.0 bps Friday alone** |
| **10Y–2Y Spread** | **~+15 bps** (Fri 10Y vs. Thu 2Y — see note) | -14 bps vs. last week's +29 | — | **Overstated flattening: pairs Friday's 10Y with Thursday's 2Y; same-day Thursday basis +28** |
| **10Y–5Y Spread** | **~+21.1 bps** | +3.8 bps (was +17.3) | — | Steeper: the belly rallied more |
| **10Y–3M Spread** | **~+79 bps** | -24 bps (was +103) | — | **Flatter: the long end fell, bills did not move** |

> *2Y source: FRED DGS2, Thu 2026-11-19 (FRED's one-day lag), so the 10Y–2Y spread pairs Friday's 10Y with Thursday's 2Y. That matters more than usual this week: the 10-year fell 14.0 bps on Friday and the 5-year 16.5, and the 2-year almost certainly fell with them, so the +15 in facts.json is a mixed-day number and probably too low. Same-day Thursday (FRED DGS10 5.04% vs. DGS2 4.76%) the spread is +28. Friday 11/13's DGS2 has since posted at 4.88%. ^IRX is a discount-basis T-bill yield; FRED's constant-maturity 3M (DGS3MO) was 4.34% Thursday, about 20 bps higher, so a CMT-basis 10Y–3M read +70 bps on Thursday. This page and facts.json use ^IRX for series continuity.*

**Ophelia Interpretation:** Bonds went back to being a hedge. The 10-year fell **24.2 bps to 4.912%**, back under 5.00%, and 14 of those came on Friday with stocks down 3.6%. It was not the Fed backing off: the October minutes said higher rates are needed in December, FedWatch went to about 95–96% (wiki/economic-calendar.md), and the 3-month bill did not move at all (4.122% both Fridays). The split of the move: the 10Y breakeven fell **9 bps to 2.15%** (T10YIE) and the real yield about 15 bps, to **~2.76%** from 2.91%. So the long end priced lower growth and lower inflation while the front end kept pricing a hike. That is why the 10Y–3M spread lost 24 bps to **+79**. There is no inversion at any maturity. The 10-year is now 33.8 bps under the 5.25% crisis line.

**Yield Curve Regime:** 🟡 **Positive; bull flattening on a flight to safety, front end pinned by the Fed.** 10Y 4.912%, 8.8 bps under 5.00%. Next gates: **2Y auction Mon Nov 23; core PCE, Q3 GDP revision, durables, claims and the Beige Book all Wed Nov 25; November payrolls Dec 4; FOMC Dec 9; November CPI Dec 10.**

---

## CREDIT SPREADS

> *OAS rows are FRED's **Thu 2026-11-19** prints (one-day lag), with Thu 11/12 as the week-ago column and Thu 10/22 as the month-ago column. **Friday Nov 20 is not in these rows**; that was the -3.64% day, so the next print is likely wider. Friday Nov 13's prints have since posted at HY 323, IG 89, HY–IG 234. HYG and LQD are live Friday closes.*

| Spread | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| HY OAS (ICE BofA US HY, BAMLH0A0HYM2) | **352 bps** (Thu 11/19) | 320 bps | 340 bps | 🟡 **Wider every print: 323 / 334 / 343 / 347 / 352 since last Friday; widest since this fetch began (Oct 5)** |
| IG OAS (ICE BofA US Corp, BAMLC0A0CM) | 94 bps (Thu 11/19) | 89 bps | 89 bps | 🟡 **89 / 90 / 92 / 93 / 94** |
| **HY–IG Spread** | **258 bps** (Thu 11/19) | 231 bps | 251 bps | 🟡 **OVER 250 for three prints: 234 / 244 / 251 / 254 / 258** |
| EM Corporate OAS (BAMLEMCBPIOAS) | 184 bps (Thu 11/19) | 167 bps | 173 bps | 🟡 **+17 on the week, back to the Nov 5 level** |
| CCC & Lower OAS (ICE BofA, BAMLH0A3HYC) | **1,361 bps** (Thu 11/19) | 1,314 bps | 1,340 bps | 🔴 **1,316 / 1,310 / 1,329 / 1,353 / 1,361; widest since this fetch began** |
| **HYG Price** | **$76.33** | **$76.94** | **$77.05** | 🟡 **-0.79%; five closes 76.73 / 76.63 / 76.65 / 76.53 / 76.33** |
| **LQD Price** | **$103.69** | **$102.81** | **$103.85** | 🟢 **+0.86% on the -24.2 bp 10Y** |

**Cecil Interpretation:** Two weeks ago one print over 250 came and went and I said a second would make it a pattern. This week there were **three in a row: 251, 254, 258**, and none of them includes Friday. HY OAS widened 32 bps to **352** and every print was wider than the one before. This time the bottom tier moved with it: **CCC went to 1,361**, the widest of the fetch, and **CCC-minus-HY is about 1,009 bps**, from 994. The move is still orderly for an 8.6% equity week. HY–IG at 258 is 92 bps from the red line, HYG lost only 0.79%, and LQD rose 0.86% because the rate rally was larger than the IG widening. Credit followed equities down; it did not lead them.

**Credit Regime:** 🟡 **Over the line.** HY–IG 258 on Nov 19, the third straight print over 250; HY OAS 352; CCC 1,361. Friday's prints post Monday and decide whether this is 260 or 280.

---

## MARKET BREADTH

> *S&P 500 rows are computed from the daily closes of the 502 constituents with a Fri 2026-11-20 print (Yahoo, list from Wikipedia's S&P 500 table, 503 members; 50D/200D = simple MA of closes; a new high/low means the day's high/low reached the trailing 252-session extreme). They are cross-checked against **Finviz Elite** (`finviz_elite breadth`, S&P 500 universe, 503 members), which agrees exactly on advancers (123), members above the 50-day (214) and the 200-day (228), new highs (1) and new lows (25), and within one name on decliners (377 vs. 376 here), giving 42.54% vs. 42.7% here on % above 50D and 45.33% vs. 45.7% on % above 200D; the gaps are denominators (501 / 499 members with full history here, 503 there). Market-wide rows are Finviz's NYSE + Nasdaq + AMEX stock totals for Friday (5,564 stocks, ETFs and funds excluded). The 1W and 1M comparisons are recomputed from this fetch on the current member list; 1M is Fri 10/23, 20 sessions back.*

| Metric | Current | 5D Avg | 20D Avg | Regime |
|---|---|---|---|---|
| S&P 500 Advance/Decline (Fri) | **0.33** (123 up / 376 down) | 0.38 | 1.35 | 🔴 **Advancers 145 / 75 / 237 / 38 / 123; no day with more up than down** |
| Market-wide Advance/Decline (Fri, Finviz) | 0.19 (875 up / 4,488 down) | — | — | 🔴 **Five decliners for every advancer** |
| S&P 500 New 52-Week Highs | **1** | 5.8 | 19.2 | 🔴 **21 / 4 / 3 / 0 / 1** |
| S&P 500 New 52-Week Lows | **25** | 12.6 | 6.4 | 🔴 **7 / 9 / 6 / 16 / 25; lows beat highs from Tuesday** |
| Market-wide New Highs / Lows (Fri, Finviz) | 38 / 1,137 | — | — | 🔴 **Lows 97% of the total; one stock in five at a 52-week low** |
| **S&P 500 % Above 50D MA** | **42.7%** (1W 71.3%, 1M 58.0%) | 54.1% | 62.6% | 🟡 **Under 50%: 64.9 / 57.8 / 56.2 / 49.0 / 42.7; -28.6 pts in a week** |
| **S&P 500 % Above 200D MA** | **45.7%** (1W 63.6%, 1M 55.8%) | 53.1% | 59.1% | 🟡 **-17.9 pts on the week; under half from Thursday** |
| Market-wide % Above 50D / 200D (Fri, Finviz) | 24.4% / 29.3% | — | — | 🔴 **From 40.0% / 39.1%** |
| Equal-Weight (RSP) vs. Cap-Weight (SPY), 1W | **+2.36 pts** (RSP -6.20% vs. SPY -8.56%) | — | 1M: **+5.03 pts** | 🟡 **The damage is cap-weighted** |
| Sector ETFs above own 50D MA | **3 of 12** (XLV, XLP, XLU) | — | — | 🔴 **From 7; XLRE 12 cents under ($42.46 vs. $42.58)** |

**Marky Interpretation:** Last Friday the S&P's breadth was the best of the fetch. One week later **42.7% of members are above the 50-day**, down 28.6 points, and **45.7% above the 200-day**. There was no day this week with more advancers than decliners, and Thursday had 38 up against 464 down. New lows passed new highs on Tuesday and reached 25 on Friday. **SPY fell -8.56% to $689.81**, through both averages: it is 9.3% under its 50-day ($760.18), 5.9% under its 200-day ($732.76), 11.5% under the October 6 closing high and at its lowest close since April 13. Equal weight lost less (**RSP -6.20%**), so the largest names did the most damage, but 6% for the average stock is not a narrow selloff. Finviz Elite agrees on every count within one name.

Outside the index it is worse. Market-wide, **24.4%** of stocks are above their 50-day, there were **1,137 new lows against 38 highs**, and Friday's A/D was 0.19.

**Breadth Regime:** 🟡 **Triggered (yellow).** S&P 500 % above 50D (42.7%) is under the 50% line and 2.7 points over the 40% red line. Market-wide gauges are deep red.

---

## SECTOR CORRELATION MATRIX

*30-day rolling correlation of daily returns vs. SPY (30-calendar-day window, 22 sessions 2026-10-22 → 2026-11-20; the 1W-ago column is last week's published window ending 2026-11-13, which this fetch reproduces to three decimals for all twelve)*

| Sector | ETF | vs. SPY Correlation | 1W Ago | Regime |
|---|---|---|---|---|
| 🖥️ Technology | XLK | **0.921** | 0.912 | 🔥 **High beta** |
| 💻 Semiconductors | SMH | **0.871** | 0.849 | 🔥 **High beta** |
| ⚙️ Industrials | XLI | **0.856** | 0.785 | 🔥 **High beta** |
| 🛍️ Consumer Discretionary | XLY | **0.814** | 0.769 | 🔥 **High beta** |
| ⛏️ Materials | XLB | **0.696** | 0.560 | 🟡 **Moderate, rising** |
| 🏦 Financials | XLF | **0.691** | 0.601 | 🟡 **Moderate, rising** |
| 📡 Communication Services | XLC | **0.667** | 0.527 | 🟡 **Moderate, rising** |
| 🏠 Real Estate | XLRE | **0.559** | 0.402 | 🟡 **Moderate, rising** |
| 🏥 Healthcare | XLV | **0.544** | 0.535 | 🟡 **Moderate** |
| ⚡ Utilities | XLU | **0.345** | 0.072 | 🟡 **No longer near zero (+0.273)** |
| ⛽ Energy | XLE | **0.123** | 0.026 | 🟡 **Low** |
| 🍞 Consumer Staples | XLP | **0.117** | 0.043 | 🟡 **Low** |

**Ophelia Interpretation:** **Every one of the twelve correlations rose this week**, which is what a selloff does. The largest change is utilities, from 0.072 to **0.345**: a sector that was moving on its own news a week ago fell 3% with everything else. Materials, communication services and real estate each gained 0.14–0.16. Only staples and energy are still low (0.117 and 0.123), and staples is the one sector that rose on Friday (+0.67% with SPY -3.64%).

**The key insight:** the diversifiers inside equities are down to two sectors, and neither is negative. The diversifier that did work this week was outside equities: TLT rose 2.61% and the 10-year fell 24 bps. That is the reverse of last week, when bonds fell with stocks rising.

**Alert:** No strict-criterion flip (positive → negative) this week. All twelve are positive and all twelve moved up.

---

## SECTOR ROTATION FLOW

*1-Day / 1-Week / 1-Month performance vs. SPY (1D = Fri 11/20 vs. Thu 11/19; 1W = Fri-to-Fri; 1M = 21 sessions from 2026-10-22). SPY: -3.64% / -8.56% / -9.71%.*

| Sector | ETF | 1D vs. SPY | 1W vs. SPY | 1M vs. SPY | Rotation Signal |
|---|---|---|---|---|---|
| 🍞 Consumer Staples | XLP | +4.31% | **+6.51%** | +10.23% | 🟢 **Shelter (-2.05%; 52-week closing high Mon, up Friday)** |
| ⚡ Utilities | XLU | +2.90% | +5.49% | +9.29% | 🟢 **Shelter (-3.07%; back under the 200D)** |
| 🏠 Real Estate | XLRE | +2.66% | +4.25% | +9.56% | 🟢 **Shelter (-4.30%; 10Y back under 5%)** |
| 🏥 Healthcare | XLV | +3.52% | +2.41% | +7.47% | 🟡 **Ahead, but -6.15% (#216)** |
| 🛍️ Consumer Discretionary | XLY | +0.69% | +2.29% | +7.49% | 🟡 **Ahead, but -6.27%; closes under the 200D (#218)** |
| ⛽ Energy | XLE | +3.02% | +1.71% | -0.74% | 🟡 **-6.85%; last week's lead erased (#220)** |
| 🏦 Financials | XLF | +1.82% | +1.55% | +6.03% | 🟡 **-7.00% (#215)** |
| ⚙️ Industrials | XLI | +0.55% | +1.21% | +3.49% | 🟡 **-7.35% (#217)** |
| ⛏️ Materials | XLB | +1.45% | +1.11% | +3.23% | 🟡 **-7.45% (#219)** |
| 📡 Communication Services | XLC | +0.98% | +0.59% | +2.83% | 🟡 **-7.97%; 13 cents over its 52-week closing low (#221)** |
| 🖥️ Technology | XLK | -3.63% | **-3.93%** | -8.57% | 🔴 **Outflow (-12.49%; -7.27% Friday; #214)** |
| 💻 Semiconductors | SMH | -6.96% | **-9.25%** | -13.85% | 🔴 **Outflow (-17.81%; -10.60% Friday; 40% under its June closing high)** |

**Ophelia Interpretation:** **All twelve sectors fell.** Ten of them fell less than SPY, which only says that the index is two sectors: **XLK -12.49%** and **SMH -17.81%**, with SMH down 10.6% on Friday alone. The desks attribute it to a reported SEC accounting probe of NVIDIA and a new export rule (#214, #223; wiki/semiconductors.md). The order below that is the classic defensive one: **staples -2.05%, utilities -3.07%, real estate -4.30%**, then everything cyclical between -6% and -8%. Energy gave back all of last week's 5.42%. **The XLK leadership trigger was not crossed on the week** (-3.93 vs. SPY against a -5 line), but over a month XLK is -8.57 and SMH -13.85 behind an index that itself fell 9.71%.

**The risk:** "outperforming" this week meant losing 2–7%. Only three sectors are still above their 50-day, and one of them (XLU) is under its 200-day.

---

## CROSS-ASSET SIGNALS

| Asset | Level | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| DXY (US Dollar Index) | **103.81** (Yahoo DX-Y.NYB) | +0.39% | +1.96% | 🟡 **52-week closing high 103.90 Thursday; closes 103.55 / 103.49 / 103.86 / 103.90 / 103.81** |
| EUR/USD | 1.0970 | -0.73% | -2.24% | 🟡 **Lower every day** |
| USD/JPY | 159.707 | -0.11% | +2.05% | 🟡 **Flat under 160; no yen bid in the selloff** |
| GBP/USD | 1.3086 | -1.10% | -2.37% | 🟡 — |
| WTI Crude | **$83.98 (CLZ26 settle, as_of 2026-11-20)** | **-5.2%** (feed, same contract; Nov 13 $88.56) | **-18.7%** (feed, 4W) | 🟢 **Under $85; no close over $87 all week** |
| Gold | **$3,512.30 (GCX26 settle, as_of 2026-11-20)** | **-9.5%** (feed; Nov 13 $3,879.70) | **-12.0%** (feed, 4W) | 🔴 **No haven bid: sold with stocks as real yields fell** |
| Copper | $5.4770/lb (HG=F front month) | -9.91% | -15.43% | 🔴 **Lowest close of the fetch again; -5.3% Wednesday** |
| Bitcoin | $58,799 (Fri 11/20 UTC close) | -13.85% | -27.48% | 🔴 **$240 over the fetch's low close ($58,559, Jun 30); ~$60,070 on the weekend (see note)** |
| HY Bonds (HYG) | $76.33 | -0.79% | -0.93% | 🟡 **Spreads wider, rates lower** |
| IG Bonds (LQD) | $103.69 | +0.86% | -0.15% | 🟢 **Duration gain** |
| Long Treasuries (TLT) | $81.45 | +2.61% | +0.14% | 🟢 **The hedge worked: +1.37% Friday** |
| TIPS Breakeven (10Y) | 2.15% (FRED T10YIE, Fri 11/20) | -0.09 pts | — | 🟡 **Lowest of the fetch (from Oct 5); real 10Y ~2.76%, from 2.91%** |

> *DXY from Yahoo's ICE DXY series (DX-Y.NYB), carried in macro/facts.json at 103.81 (tolerance 1%). 1W changes use this run's Yahoo fetch for both endpoints; 1M is vs. Fri 10/23. **FX daily bars:** per macro/README.md, Yahoo's daily bar for a pair closes near its open until the provider replaces it; facts.json carries the daily bars (159.707, 1.0970). **WTI and gold (feed contract):** facts.json carries WTI $83.98 (CLZ26, yahoo:CLZ26.NYM) and gold $3,512.30 (GCX26, yahoo:GCX26.CMX), as_of 2026-11-20, from `data/market_state.json`; both passed `truth_check --facts` against the contracts' own bars. The continuous symbols CL=F and GC=F were not used. Weekly and 4-week changes are the feed's own (d1w / d4w). CLZ26 was in its last trading days; wiki/economic-calendar.md records the January contract (CLF27) at $83.41. **Bitcoin:** the Fri 11/20 UTC daily bar is present ($58,799, same value and as_of in facts.json). `truth_check --facts` read $60,069 on Yahoo's Sunday-UTC bar at check time, 2.2% over the Friday value and inside the 5% tolerance. The Friday close is the value of record.*

**Ophelia Interpretation:** **This was liquidation, not rotation into havens.** The things people own for protection did not all work. **Treasuries did**: TLT +2.61%, the 10-year -24 bps. **Gold did not**: **-9.5% to $3,512.30**, in a week when real yields fell, which is the opposite of what the real-yield relationship says and reads as selling to raise cash. **Bitcoin -13.85%** to $58,799, almost exactly at the low close of the fetch. **Copper -9.91%** and **WTI -5.2% to $83.98** point the same way as the regional surveys in wiki/economic-calendar.md: weaker growth. **The dollar held its 52-week high area** (103.81) without a yen bid; USD/JPY did not move.

**The risk:** gold, copper, oil, Bitcoin and equities all fell together. When the only asset that rises is the Treasury, and the Fed is 95% priced to hike in three weeks, the hedge depends on the Fed not pushing the long end back up.

---

## CANARY WATCH TRIGGER BOARD

| Signal | Status | Trend | Trigger Level |
|---|---|---|---|
| VIX Regime | 🔴 **Alarm: 35.89, five closes over 20** | +86.0% WoW; VVIX 138.03; VIX/VIX3M **1.160** (backwardation from Tuesday); total put/call 1.13 | 🟡 >20 | 🔴 >25 |
| Yield Curve | 🟡 Positive, long end rallied | 10Y 4.912% (-24.2 bps; back under 5.00%); 2Y 4.76% Thu (-10 bps); 10Y–2Y ~+15 mixed-day (+28 same-day Thu), 10Y–3M +79 (-24) | 🟡 <0 (inverted) | 🔴 <-50 bps |
| Credit Spreads | 🟡 **Over the line, three prints** | HY–IG **258 bps** Thu 11/19 (251 on 11/17, 254 on 11/18); HY OAS 352; CCC 1,361; Friday not yet posted | 🟡 HY–IG >250 bps | 🔴 >350 bps |
| Market Breadth | 🟡 **Triggered** | S&P 500 42.7% above 50D (71.3% last week), 45.7% above 200D (63.6%); new highs/lows 1 / 25; RSP +2.36 pts vs. SPY WoW; market-wide 24.4% above 50D | 🟡 <50% above 50D MA | 🔴 <40% |
| Sector Rotation | 🟡 **XLK -3.93 vs. SPY on the week, short of the line; -8.57 over a month** | All twelve down; XLP, XLU, XLRE lose least; SMH -17.81%, XLK -12.49% | 🟡 XLK -5% vs. SPY | 🔴 XLK -10% |
| Sector Correlation | 🟡 **No flip; all twelve positive and all higher** | XLP 0.117, XLE 0.123 the only low readings; XLU 0.345 (from 0.072); XLK 0.921 | 🔴 positive → negative flip | — |
| DXY | 🟡 **At the 52-week high** | 103.81 (+0.39% WoW); 103.90 Thursday | 🟡 >102 | 🔴 >105 |
| Geopolitics | 🟢 **Oil under the line** | WTI $83.98 (CLZ26, Fri settle; facts.json), -5.2%; XLE -6.85% (#220); no geopolitical item sourced by this run | 🟡 Oil >$90 | 🔴 Oil >$100 |
| Credit Risk | 🟡 Spreads wider, CCC widest of the fetch (CDS not sourced) | XLF -7.00% to $54.57 (#215); EM OAS +17 bps W/W | 🟡 CDS widening | 🔴 Bank stress |
| Policy | 🔴 **Live hiking cycle; December odds ~95–96%** | Fed 3.75–4.00%; October minutes: higher rates needed in December; core PCE 11/25, payrolls 12/4, FOMC 12/9 | — | — |
| Overall Risk | 🔴 **ELEVATED: volatility, credit and breadth all triggered in one week** | — | — | — |

**Weekly Narrative — Overall Assessment:** The week took back more than the whole recovery. The ledger: (1) **SPY fell -8.56% to $689.81**, the worst week of this fetch and, per wiki/economic-calendar.md, the second-worst on two years of bars; it is under its 50-day and its 200-day, 11.5% under the October 6 closing high and at its lowest close since April 13; (2) **VIX closed over 20 every day** and ended at **35.89** (40.03 intraday), the highest close of the fetch, with VIX/VIX3M at **1.160**; (3) **HY–IG printed over 250 three days running** (251 / 254 / 258) with HY OAS at 352 and CCC at 1,361, and Friday is not in those numbers; (4) **the 10-year fell 24.2 bps to 4.912%**, back under 5.00%, while the 3-month bill did not move and December hike odds rose to about 95–96%; (5) **S&P 500 breadth went from 71.3% to 42.7% above the 50-day**, with no day of more advancers than decliners; (6) **all twelve sectors fell**, from staples -2.05% to SMH -17.81%; (7) **every sector correlation with SPY rose**; (8) **gold -9.5%** to $3,512.30, **copper -9.91%**, **Bitcoin -13.85%**, **WTI -5.2%** to $83.98; (9) **TLT +2.61%** was the one hedge that paid; (10) the dollar held its 52-week high area at 103.81.

The fragilities: (1) the Fed is priced to hike on December 9 into a market in correction; (2) credit's Friday prints are still to come, and CCC is already the widest of the fetch; (3) breadth is 2.7 points from the red line; (4) backwardation at 1.16 means the market is paying more for this month's protection than for three months'; (5) gold and Bitcoin fell with stocks, so the only diversifier left is the Treasury; (6) next week is a holiday week with core PCE, the GDP revision, durables, claims and the Beige Book all on Wednesday, then a half day.

**The Canary Watch verdict:** 🔴 **ELEVATED**, up from HIGH CAUTION. Composition changes: **VIX Regime** goes from green to red; **Credit Spreads** from green to yellow; **Market Breadth** from green to yellow; **Sector Rotation** from green to yellow; **Geopolitics** from yellow to green (oil under $85); **Yield Curve**, **Sector Correlation**, **DXY**, **Credit Risk** stay yellow; **Policy** stays red. Of the four strict criteria, **two were met**: VIX closed above 20 (all five days), and HY–IG widened above 250 bps (three prints). The curve is positive at every maturity, and no correlation flipped from positive to negative. **Issue #225 opened this run.** Related: #214–#221 (the sector desks' triggers), #223 (regime flags), #224 (earnings). Watch: (1) Friday's HY–IG print on Monday; (2) VIX/VIX3M back under 1.00; (3) S&P 500 % above 50D under 40%, the red line; (4) core PCE Wednesday; (5) SPY's 200-day ($732.76) from below; (6) the 10-year turning back up through 5.00% while stocks are still falling, which would take away the last hedge.

---

## COUNCIL READ — What This Means for Monday

*(Updated this week: VIX, credit and breadth all triggered, and the 10-year went back under 5%.)*

**Ophelia:** *"Last week the problem was rates and I said I would not add duration because bonds fell with stocks. This week bonds were the only thing that worked, and I did not own enough of them. I am not chasing that now: the minutes say December is a hike, and the 10-year fell on fear, not on the Fed. Cash stays at the top of my range. The number I watch is no longer 5.25% on the 10-year. It is whether the 10-year can stay under 5% through core PCE on Wednesday."*

**Marky:** *"I took the extra hedge off last week because VIX closed under 20 with the ratio under one. Both conditions failed by Tuesday. That is on me, and the rule cuts the other way now: with VIX at 36 and the ratio at 1.16 I do not add risk, and I do not buy protection at these prices either. Breadth went from the best of the fetch to 42.7% in five days. I wait for the ratio to go back under one and for a day with more advancers than decliners. This week had none."*

**Cecil:** *"I said a second print over 250 would make it a pattern. There were three, and Friday is still to come. CCC is the widest of the fetch, so this time the bottom tier is moving. I stay at zero in high yield. IG duration finally paid: LQD up 0.86% in a week stocks lost 8.6%. I keep it, and I do not add, because the Fed meets in under three weeks and the bill market has not moved an inch."*

---

## SOURCES & REFERENCES

- Yahoo Finance (yfinance, single fetch 2026-11-21 ~19:50 ET): VIX, VIX3M, VVIX, SPY, RSP, 12 sector ETFs, Treasury yield proxies (^IRX/^FVX/^TNX), DXY (DX-Y.NYB), FX (EURUSD=X, JPY=X, GBPUSD=X, AUDUSD=X, CNY=X), copper (HG=F), Bitcoin (BTC-USD), bond ETFs (HYG, LQD, TLT, IEF). "The fetch" for highs and lows means daily bars from 2025-08-01
- data/market_state.json (Universe & Data Feed Builder, run 2026-11-21 09:26–09:31 ET): as_of 2026-11-20. WTI $83.98 (CLZ26) and gold $3,512.30 (GCX26) in facts.json are taken from it, with their d1w / d4w changes; CL=F and GC=F were not used
- CBOE: official VIX daily history (cdn.cboe.com VIX_History.csv), Fri 2026-11-20 close 35.89, high 40.03, exact match on all five closes; daily options market statistics (cdn.cboe.com daily_options) for total / equity / index / SPX put/call ratios, 10/19–10/23 and 11/9–11/20
- FRED (St. Louis Fed): the runner's own connection timed out (Python urllib and curl, 20–25 second limits, one retry). All nine series were fetched through a second network path during the run. Live on this page: DGS2 (4.76%, Thu 11/19; source of the 2Y row and facts.json ust_2y), DGS10 / DGS3MO (cross-checks), BAMLH0A0HYM2 / BAMLC0A0CM / BAMLEMCBPIOAS / BAMLH0A3HYC through Thu 11/19 (series read from Oct 5), T10YIE through Fri 11/20, VIXCLS through Thu 11/19
- Federal Reserve: fed funds range and stance in facts.json unchanged; `next_macro_gate` rolled forward to the holiday-week auctions, core PCE / GDP / durables / claims / Beige Book on Nov 25, ISM, November payrolls, the December FOMC and November CPI from wiki/economic-calendar.md (updated 2026-11-21)
- Breadth: S&P 500 constituent closes via Yahoo (502 of 503 members with a Fri print; constituent list from Wikipedia's S&P 500 table), cross-checked against Finviz Elite (`finviz_elite breadth --json`, S&P 500 and market universes, fetched 2026-11-22 00:53 UTC); market-wide NYSE + Nasdaq + AMEX counts from the same Finviz Elite run. Only derived counts and percentages are published
- Internal desk cross-references, used for every news item on this page; none was re-sourced by this run: wiki/economic-calendar.md (minutes, hike odds, regional surveys, NVIDIA / export-rule / IPO attributions, two-year weekly ranking, next week's schedule), wiki/semiconductors.md, and the sector desks' trigger issues
- GitHub issues cross-referenced this run: #214, #215, #216, #217, #218, #219, #220, #221, #223, #224. **Issue #225 opened this run** for the two strict criteria met (VIX above 20; HY–IG above 250 bps)

---

*Last updated by Saturday Research Crew: 2026-11-21 (single-agent run, Saturday evening; all market data as of Fri 2026-11-20 closes; macro/facts.json regenerated from the same fetch; breadth live from S&P 500 constituents with a Finviz Elite cross-check; put/call live from CBOE; FRED series live via a second network path after the runner's connection timed out; WTI and gold from the 2026-11-20 feed)*
*Next update: Every Saturday 7:39 PM ET*
*Data sources: Yahoo Finance (yfinance), data/market_state.json (feed), CBOE, FRED, Finviz Elite, Federal Reserve*
