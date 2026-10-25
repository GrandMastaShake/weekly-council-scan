# Wiki — Canary Watch

> **The Early Warning System for the Market Consciousness Orchestra**
>
> *"The canary does not predict the mine collapse. It simply dies first. Watch the canary."* — Marky

> **Truth layer:** every macro number on this page equals `macro/facts.json` (generated 2026-10-25, same fetch, commit 262e30b; `truth_check --facts` 26 ok / 0 warn / 0 fail / 2 skip before push; the two skips are WTI and gold, carried stale). Week ending Friday 2026-10-23 closes.

> **Run note:** this update ran late (Sunday 2026-10-25 ~08:56–09:50 ET; scheduled Saturday 2026-10-24 19:39 ET). **FRED timed out from the runner's own connection for a fourth week** (nine series, two attempts each, plus a 30-second curl test). All nine series were downloaded in one fredgraph request through a second network path during the same run, so **no FRED row is stale**: DGS2 / DGS10 / DGS3MO, the four OAS series and VIXCLS are posted through Thu 2026-10-22 (FRED's usual one-day lag), the 10Y breakeven through Fri 2026-10-23. **WTI and gold are STALE:** `data/market_state.json` is still as_of 2026-10-16 (the Universe & Data Feed Builder logged START on Saturday but committed no file for 10/23), so per the feed contract this page and facts.json carry last week's feed settlements with their own as_of and `stale: true`. Directional contract prints are shown beside them, labelled. Finviz Elite breadth ran cleanly.

---

## VOLATILITY REGIME

| Metric | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| VIX | **19.45** | 19.99 | 15.67 | 🟡 **Under 20 on every close; 20.31 intraday Thu, 20.66 intraday Fri** |
| VIX 20-Day MA | ~16.54 | ~15.73 | — | — |
| VIX Trend | **-2.7% WoW**; closes 18.44 / 17.31 / 16.68 / 19.03 / 19.45; low 16.51, high **20.66 Fri**; all five closes above 16.50 | — | — | — |
| VIX3M (term structure) | 20.48 (VIX/VIX3M **0.950**) | 20.50 (0.975) | 18.43 (0.850) | 🟡 **Contango thin: 0.941 → 0.912 → 0.891 → 0.946 → 0.950** |
| Implied SPY Move (30D) | ~±5.6% | ~±5.8% | — | — |
| VVIX (VIX of VIX) | **109.70** | 109.91 | 90.57 | 🔴 **Held at 110; 118.17 intraweek high** |
| Total Put/Call Ratio (CBOE) | 0.93 (5D avg 0.90) | 0.92 (5D avg 0.87) | 0.80 | 🟡 **Five-day average the highest in this fetch** |
| Equity Put/Call Ratio (CBOE) | 0.67 (5D avg 0.60) | 0.65 (5D avg 0.61) | 0.55 | 🟡 **0.69 Thu on the SOX selloff** |

> *Source note: VIX prints vary by vendor — discrepancies of ~2–3 pts are common across quote sources (delayed feeds, spot vs. VX futures, stale prints). Canonical reference: CBOE official close / FRED VIXCLS. This week the Friday close was cross-checked against the **CBOE official daily history file (VIX_History.csv): Fri 2026-10-23 close 19.45, high 20.66**, an exact match for Yahoo ^VIX, and the CBOE file matches Yahoo on all five closes. **FRED VIXCLS** is posted through Thu 10/22 (19.03) and agrees. **Put/call ratios** are from CBOE's official daily market statistics file (cdn.cboe.com daily_options), Fri 2026-10-23 vs. Fri 2026-10-16 and Thu 2026-09-24 (21 sessions back); 5D averages are Mon–Fri of each week. Index put/call was 1.10 Friday (5D avg 1.03); SPX + SPXW 1.25 (5D avg 1.20, from 1.24 the week before; Friday 10/16's 1.46 remains the high of the fetch).*

**Marky Interpretation:** Last week VIX closed one cent under 20. This week it never closed above it either, but it touched it twice: **20.31 on Thursday**, the day SOX fell 6.7% after Lam's supply comment and Meta's reversal, and **20.66 on Friday**, when December crude settled above $103 on Hormuz headlines (wiki/economic-calendar.md, #175). The close was 19.45. What did not relax is the structure. VIX3M stayed at 20.48, so the ratio finished at **0.950** and never got back under 0.89; VVIX held **109.70**; equity put/call printed 0.69 on Thursday and the total 5-day average rose to 0.90, the highest in this fetch. The low of the week was 16.51, above every close from the first half of October. My lines stay where they were: a close above 20 is the regime question, 25 is the alarm, a ratio above 1.00 is the tell. Wednesday has the FOMC and Microsoft/Alphabet inside four hours.

---

## YIELD CURVE

| Maturity | Yield | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| 13-Week (T-Bill) | 4.032% | -0.038% | -0.036% (vs. 4.068% on 9/24) | **Closes 4.075 / 4.080 / 4.063 / 4.022 / 4.032; October priced out, December still on** |
| 2-Year | 4.65% (FRED DGS2, Thu 10/22 — see note) | **-0.12%** (vs. 4.77% Thu 10/15) | -0.22% (vs. 4.87% on 9/24) | **4.74 / 4.77 / 4.79 / 4.81, then -16 bps Thursday** |
| 5-Year | 4.805% | -0.094% | -0.220% | Closes 4.929 / 4.935 / 4.972 / 4.768 / 4.805 |
| **10-Year** | **4.988%** | **-0.110%** | **-0.174%** | **First weekly close under 5.00% in five weeks; closes 5.136 / 5.117 / 5.146 / 4.953 / 4.988** |
| **10Y–2Y Spread** | **~+34 bps** (Fri 10Y vs. Thu 2Y) | +1 bp vs. last week's +33 | — | **Positive; Thursday's rally moved both ends together** |
| **10Y–5Y Spread** | **~+18.3 bps** | -1.6 bps (was +19.9) | — | Flat to slightly flatter |
| **10Y–3M Spread** | **~+96 bps** | -7 bps (was +103) | — | **Positive, flatter for a third week** |

> *2Y source: FRED DGS2, Thu 2026-10-22 (FRED's one-day lag), so the 10Y–2Y spread pairs Friday's 10Y with Thursday's 2Y. On a same-day Thursday basis (FRED DGS10 4.96% vs. DGS2 4.65%) the spread is +31. macro/facts.json carries 4.65 with as_of 2026-10-22 and source fred:DGS2. ^IRX is a discount-basis T-bill yield; FRED's constant-maturity 3M (DGS3MO) was 4.22% Thursday, about 20 bps higher, so a CMT-basis 10Y–3M would read ~+77 bps. This page and facts.json use ^IRX for series continuity. FRED's DGS10 for Thu 10/22 is 4.96%, consistent with ^TNX's 4.953% Thursday close.*

**Ophelia Interpretation:** The 10-year closed the week at **4.988%**, down 11 bps and under 5.00% on a weekly close for the first time in five weeks. It did not come from the data. Claims printed 194K, the flash PMI composite 57.6 with manufacturing at a 53-month high and output prices the fastest since August 2022, and UMich beat every estimate (wiki/economic-calendar.md). The 10-year was **5.146% on Wednesday** after a record 5.469% 20-year auction stop, then fell **19 bps on Thursday** when SOX fell 6.7%. The 2-year fell with it (-16 bps Thursday to 4.65%), which is new: last week the front end held while the long end rallied. With October hike odds drifting to ~10% in the blackout, the market took a little of December out too. The breakeven barely moved (**T10YIE 2.34%**, -1 bp), so the fall was real yield again: about **2.65%**, from 2.75%. Net: **10Y–2Y +34** (unchanged), **10Y–3M +96** (-7). No inversion anywhere.

**Yield Curve Regime:** 🟡 **Positive, rallying in parallel on equity stress.** 10Y under 5.00%, 1.2 bps below the line. Next gates: **FOMC Wed Oct 28 (2:00 PM), Q3 GDP and September PCE Thu Oct 29**.

---

## CREDIT SPREADS

> *OAS rows are FRED's **Thu 2026-10-22** prints (FRED's one-day lag), with Thu 10/15 as the week-ago column and Thu 9/24 as the month-ago column. Friday Oct 16's prints, flagged last week as the rumor-day watch, posted this week: HY 331, IG 85, HY–IG **246**. Friday Oct 23's OAS posts Monday. HYG and LQD are live Friday closes.*

| Spread | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| HY OAS (ICE BofA US HY, BAMLH0A0HYM2) | **340 bps** (Thu 10/22) | 323 bps | 280 bps | 🔴 **New cycle peak; 331 / 329 / 333 / 327 / 340 since last Friday** |
| IG OAS (ICE BofA US Corp, BAMLC0A0CM) | 89 bps (Thu 10/22) | 84 bps | 79 bps | 🟡 **+5 bps; wider every session this week** |
| **HY–IG Spread** | **251 bps** (Thu 10/22) | 239 bps | 201 bps | 🔴 **TRIGGER CROSSED: above 250 for the first time (246 / 242 / 246 / 239 / 251) — issue #177** |
| EM Corporate OAS (BAMLEMCBPIOAS) | 173 bps (Thu 10/22) | 159 bps | 134 bps | 🟡 **+14 bps, +10 of it on Thursday** |
| CCC & Lower OAS (ICE BofA, BAMLH0A3HYC) | **1,340 bps** (Thu 10/22) | 1,278 bps | 1,112 bps | 🔴 **Another 52-week high; +62 bps on the week, +228 on the month** |
| **HYG Price** | **$77.05** | **$76.86** | **$77.89** | 🟡 **+0.25%; has not confirmed the index print** |
| **LQD Price** | **$103.85** | **$103.40** | **$103.15** | 🟢 **+0.44% on the 11 bp 10Y rally** |

**Cecil Interpretation:** The trigger I have been eleven basis points from for a week went on Thursday. **HY–IG printed 251 bps**, the first print above 250 on this board, with **HY OAS at a new cycle peak of 340** and **CCC at 1,340**, up 62 in a week and 228 in a month. Friday Oct 16's rumor-day print came in at 246, so the trigger did not fire on the rumor; it fired on Thursday's semiconductor selloff, the same day the 10-year fell 19 bps. That is the configuration I warned about: Treasuries rally, spreads widen, and the AI-capex financing chain is the part of the market widening. EM corporate spreads also jumped 10 bps on Thursday. The ETFs disagree: HYG rose 0.25% and LQD 0.44%, because the Treasury rally carried the price. One print above 250 is a trigger, not a trend; Friday's print on Monday tells me whether it holds. **CCC-minus-HY is about 1,000 bps** (955 last week).

**Credit Regime:** 🔴 **Trigger crossed (one print).** HY–IG 251 bps on Oct 22, HY OAS 340 (cycle peak), CCC 1,340 (52-week high). Issue #177. Next: Friday Oct 23's prints, posted Monday.

---

## MARKET BREADTH

> *S&P 500 rows are computed from the daily closes of all 503 constituents with a Fri 2026-10-23 print (Yahoo, list from Wikipedia's S&P 500 table; 50D/200D = simple MA of closes; a new high/low means the day's high/low reached the trailing 252-session extreme). They are cross-checked against **Finviz Elite** (`finviz_elite breadth`, S&P 500 universe, 503 members), which agrees on advancers/decliners (135 / 367), new highs/lows (19 / 8) and % above 50D (292 names, 58.05% vs. 58.0% here), and within 0.2 pts on % above 200D (55.67% vs. 55.8%). Market-wide rows are Finviz's NYSE + Nasdaq + AMEX stock totals for Friday (5,601 stocks, ETFs and funds excluded). The 1W and 1M comparisons are recomputed from this fetch on the current 503-member list (1W 45.0% here vs. 44.9% published last week, a recompute difference of one name).*

| Metric | Current | 5D Avg | 20D Avg | Regime |
|---|---|---|---|---|
| S&P 500 Advance/Decline (Fri) | **0.37** (135 up / 367 down) | 1.13 | 1.12 | 🟡 **Weak Friday after a strong week; advancers 176 / 404 / 281 / 336 / 135** |
| Market-wide Advance/Decline (Fri, Finviz) | 0.64 (2,075 up / 3,251 down) | — | — | 🟡 **Better than last Friday's 0.46** |
| S&P 500 New 52-Week Highs | **19** | 23.6 | 15.2 | 🟢 **42 on Thursday, the most in this fetch** |
| S&P 500 New 52-Week Lows | **8** | 3.6 | 11.8 | 🟢 **Highs beat lows every day** |
| Market-wide New Highs / Lows (Fri, Finviz) | 147 / 443 | — | — | 🔴 **Lows still 75% of the total** |
| **S&P 500 % Above 50D MA** | **58.0%** (1W 45.0%, 1M 25.5%) | 53.9% | 36.9% | 🟢 **Above 50%: yellow cleared; 60.6% Thursday** |
| **S&P 500 % Above 200D MA** | **55.8%** (1W 51.8%, 1M 44.8%) | 54.2% | 48.0% | 🟢 **Highest in this fetch** |
| Market-wide % Above 50D / 200D (Fri, Finviz) | 33.7% / 38.2% | — | — | 🔴 **Improved from 26.5% / 36.7%, still under 40%** |
| Equal-Weight (RSP) vs. Cap-Weight (SPY), 1W | **+1.57 pts** (RSP +1.14% vs. SPY -0.43%) | — | 1M: **+3.93 pts** | 🟢 **Third week ahead** |
| Sector ETFs above own 50D MA | **5 of 12** (XLE, XLV, XLP, XLB, XLU) | — | — | 🟡 **XLB regained it; XLK, SMH, XLC, XLF, XLI, XLY, XLRE below** |

**Marky Interpretation:** For the third straight week the average stock beat the index. **SPY fell -0.43% to $759.97** and stayed under its 50-day ($767.81); **RSP rose +1.14%**. **58.0% of S&P 500 members are above their 50-day**, up from 45.0% and from 25.5% a month ago, and 55.8% are above their 200-day, the best in this fetch. Thursday, the day SOX fell 6.7%, had **42 new highs**. Finviz Elite agrees name for name. The breadth trigger cleared yellow for the first time since the board started measuring it live.

The caution is the same as last week, smaller. The market outside the S&P 500 improved (33.7% above the 50-day, from 26.5%) but is still red, with new lows at 443 against 147 highs. Friday was weak: 135 advancers. And the cap-weighted index is below its 50-day because its largest members are the ones falling (XLC -4.36%, SMH -2.33%).

**Breadth Regime:** 🟢 **Clear.** S&P 500 % above 50D (58.0%) is above the 50% yellow line. Market-wide gauges remain red.

---

## SECTOR CORRELATION MATRIX

*30-day rolling correlation of daily returns vs. SPY (30-calendar-day window, 22 sessions 2026-09-24 → 2026-10-23; same convention as prior weeks; the 1W-ago column is last week's published window ending 2026-10-16, which this fetch reproduces exactly)*

| Sector | ETF | vs. SPY Correlation | 1W Ago | Regime |
|---|---|---|---|---|
| 🖥️ Technology | XLK | **0.836** | 0.861 | 🔥 **High beta** |
| 💻 Semiconductors | SMH | **0.765** | 0.765 | 🔥 **High beta (unchanged)** |
| 🛍️ Consumer Discretionary | XLY | **0.727** | 0.804 | 🔥 **High beta (easing)** |
| ⚙️ Industrials | XLI | **0.603** | 0.470 | 🔥 **High beta (rising, +13 pts)** |
| 📡 Communication Services | XLC | **0.440** | 0.543 | 🟡 **Moderate (falling)** |
| 🏦 Financials | XLF | **0.275** | 0.305 | 🟡 **Low** |
| ⛏️ Materials | XLB | **0.262** | 0.235 | 🟡 **Low** |
| 🏠 Real Estate | XLRE | **0.111** | 0.396 | 🟡 **Near zero (fell 29 pts)** |
| ⚡ Utilities | XLU | **0.024** | 0.210 | 🟡 **Near zero (next flip candidate)** |
| 🏥 Healthcare | XLV | **-0.071** | 0.059 | 🔴 **FLIPPED positive → negative (issue #177)** |
| ⛽ Energy | XLE | **-0.263** | -0.462 | 🔴 **Inverse (less so)** |
| 🍞 Consumer Staples | XLP | **-0.371** | -0.303 | 🔴 **Inverse, deepened** |

**Ophelia Interpretation:** Last week's page named healthcare as the row to watch at 0.059. It crossed: **XLV -0.071**, a strict positive-to-negative flip. Utilities (**0.024**) and real estate (**0.111**) fell toward zero behind it. The board now has **three sectors below zero and two within 0.11 of it**, all defensives. The growth side held together: XLK 0.836, SMH 0.765, XLY 0.727, and industrials rose to 0.603. **The index is moving with five sectors and against or apart from five.** That is the hedge working again: XLV +1.45% and XLE +1.60% in a week SPY fell.

**The key insight:** the defensive bloc is not only uncorrelated, it is now the larger share of the board. When SPY falls on a semiconductor day, half the sectors do not follow.

**Alert:** Strict-criterion flip — **XLV (+0.059 → -0.071)**. XLU at 0.024 is next.

---

## SECTOR ROTATION FLOW

*1-Day / 1-Week / 1-Month performance vs. SPY (1D = Fri 10/23 vs. Thu 10/22; 1W = Fri-to-Fri; 1M = 21 sessions from 2026-09-24). SPY: -0.52% / -0.43% / -0.94%.*

| Sector | ETF | 1D vs. SPY | 1W vs. SPY | 1M vs. SPY | Rotation Signal |
|---|---|---|---|---|---|
| ⛽ Energy | XLE | +3.12% | **+2.03%** | **+11.69%** | 🟢 **Inflow (leader: +1.60%; 52-week closing high, Hormuz, #175)** |
| 🏥 Healthcare | XLV | -0.59% | +1.88% | +6.48% | 🟢 **Inflow (+1.45%; fourth week)** |
| 🏠 Real Estate | XLRE | +0.64% | +1.40% | +3.15% | 🟢 **Inflow (+0.97% on the 10Y rally)** |
| ⚡ Utilities | XLU | -0.20% | +1.26% | +9.07% | 🟢 **Inflow (+0.83%)** |
| ⛏️ Materials | XLB | -0.22% | +1.20% | +4.22% | 🟢 **Inflow (+0.77%; back above its 50-day)** |
| 🍞 Consumer Staples | XLP | -1.40% | +1.16% | +8.97% | 🟢 **Inflow (+0.73%; +3.3% Thursday)** |
| 🏦 Financials | XLF | -0.80% | +1.11% | +3.45% | 🟢 **Inflow (+0.68%)** |
| 🛍️ Consumer Discretionary | XLY | -1.14% | +1.00% | +3.46% | 🟡 **Neutral (+0.57%)** |
| 🖥️ Technology | XLK | +1.01% | +0.30% | -4.96% | 🟡 **Flat (-0.13%) after last week's -7.70%** |
| ⚙️ Industrials | XLI | -0.75% | -1.44% | -1.55% | 🟡 **Lagging (-1.87%)** |
| 💻 Semiconductors | SMH | +1.26% | -1.90% | **-11.27%** | 🔴 **Outflow (-2.33%; SOX -6.7% Thursday)** |
| 📡 Communication Services | XLC | -1.26% | **-3.93%** | -6.50% | 🔴 **Outflow (-4.36%; Netflix guide, Meta -9.4%, #176)** |

**Ophelia Interpretation:** **Eight of twelve sectors beat SPY again**, and this week the laggard was **communication services, -4.36%**: Netflix's guidance miss and ad-forecast cut, then Meta's reversal after it held its capex budget (#176, wiki/economic-calendar.md). SMH fell another 2.33% to $527.20 after Thursday's 6.7% SOX drop on Lam's supply comment; it closed 8.3% under its 50-day ($575.09), and the calendar desk's next line is its 200-day near $515. XLK was flat (-0.13%), so the board's leadership trigger (**XLK -5% vs. SPY in a week**) did not fire again. **Energy led** (+1.60%, +2.03 pts vs. SPY) on Friday's Hormuz headlines. Over a month the board is now sharply split: **XLE +11.69, XLU +9.07, XLP +8.97 pts** ahead of SPY; **SMH -11.27, XLC -6.50, XLK -4.96** behind.

**The risk:** the one-month spread between the best and worst sector is 23 points. Wednesday's Microsoft and Alphabet reports decide whether the growth bloc keeps falling.

---

## CROSS-ASSET SIGNALS

| Asset | Level | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| DXY (US Dollar Index) | **101.81** (Yahoo DX-Y.NYB) | -0.03% | +0.51% | 🟢 **Flat under 102: closes 101.98 / 101.73 / 101.78 / 101.61 / 101.81; high 102.08** |
| EUR/USD | 1.1204 | -0.08% | -1.56% | 🟡 **Flat; range 1.1188–1.1259** |
| USD/JPY | 156.814 | -0.84% | -0.92% | 🟢 **Yen firmer on the Thursday rally (see note)** |
| WTI Crude | **$101.41 (CLX26) — STALE, as_of 2026-10-16** | — (feed not rebuilt for 10/23) | — | 🔴 **Feed carry. Directional: December (CLZ26) settled $103.27 Fri, +4.29% on the same contract (98.54 / 97.82 / 97.15 / 99.47 / 103.27)** |
| Brent Crude | $111.70 | +1.67% | +4.78% | 🔴 **$113.49 intraweek; directional only (see note)** |
| Gold | **$4,159.50 (GCV26) — STALE, as_of 2026-10-16** | — (feed not rebuilt for 10/23) | — | 🟡 **Feed carry. Directional: GCV26 settled $3,991.10 Fri (-4.05%), GCZ26 $4,007.90 (-4.14%): under $4,000 on the spot month** |
| Copper | $6.5075/lb (HG=F front month) | -0.36% | -3.14% | 🟡 **+2.28% Friday; range $6.36–6.58 (see note)** |
| Bitcoin | $81,074 (Fri 10/23 UTC close) | -0.52% | -3.92% | 🟡 **Range $80,422–$84,840; held $80K a third week** |
| HY Bonds (HYG) | $77.05 | +0.25% | -1.08% | 🟡 **Duration beat the spread this week** |
| IG Bonds (LQD) | $103.85 | +0.44% | +0.68% | 🟢 **Duration relief on -11 bps 10Y** |
| TIPS Breakeven (10Y) | 2.34% (FRED T10YIE, Fri 10/23) | -0.01 pts | +0.01 pts | 🟡 **The 10Y's fall was real yield again (about 2.65%, from 2.75%)** |

> *DXY from Yahoo's ICE DXY series (DX-Y.NYB), carried in macro/facts.json at 101.81 (tolerance 1%). 1W changes use this run's Yahoo fetch for both endpoints. Two Yahoo series revised last Friday's bar since last week's run: **USD/JPY** 10/16 now 158.143 (published 157.987; vs. the published value the week is -0.74%), and **HG=F** 10/16 now 6.5310 (published 6.5735; vs. the published value the week is -1.00%). **WTI and gold (feed contract):** `data/market_state.json` is still as_of 2026-10-16, so facts.json carries WTI $101.41 (CLX26, yahoo:CLX26.NYM) and gold $4,159.50 (GCV26, yahoo:GCV26.CMX) with as_of 2026-10-16 and `stale: true`. The November WTI contract (CLX26) expired 10/20, so the stale value is of a contract that no longer trades. The continuous symbols CL=F and GC=F were not used. The contract prints in the Implication column (CLZ26.NYM, GCV26.CMX, GCZ26.CMX) were fetched in this run for direction only and are not in facts.json; CLZ26's $103.27 matches wiki/economic-calendar.md. **Brent (BZ=F)** is a continuous series, shown for direction only. **Bitcoin:** the Fri 10/23 UTC daily bar is present ($81,074, same value and as_of in facts.json).*

**Ophelia Interpretation:** **Oil held above $100 on the contract that now matters.** November expired on Tuesday at a premium; December, the new front month, dipped to $97.15 midweek and then settled **$103.27** on Friday on IRGC tanker and mine claims near Hormuz, with Brent at **$111.70** (#175, wiki/energy.md). Our feed did not roll this week, so the canonical number is last week's $101.41 marked stale; the direction is the same. **Gold broke $4,000 on the spot contract** (GCV26 $3,991.10, -4.05%) in a week real yields fell another 10 bps. That is the second straight week gold fell with real yields, and the deleveraging read from last week gets stronger. **The dollar was flat** (101.81), **the yen firmed 0.8%** on Thursday's rally, and **Bitcoin held $80K**. Bonds were bought: TLT +1.61%, LQD +0.44%.

**The risk:** oil above $100 on December with the flash PMI's output prices at a three-year high and PCE on Thursday. A second December settle above $100 on Monday fires the calendar desk's sustained-oil flag.

---

## CANARY WATCH TRIGGER BOARD

| Signal | Status | Trend | Trigger Level |
|---|---|---|---|
| VIX Regime | 🟡 **At the line: 19.45 close; 20.31 Thu and 20.66 Fri intraday** | -2.7% WoW from 19.99; VVIX 109.70; VIX/VIX3M 0.950 | 🟡 >20 | 🔴 >25 |
| Yield Curve | 🟡 Positive, parallel rally | 10Y 4.988% (-11 bps; first weekly close under 5.00% in five weeks); 10Y–2Y ~+34, 10Y–3M +96 (was +103) | 🟡 <0 (inverted) | 🔴 <-50 bps |
| Credit Spreads | 🔴 **TRIGGER CROSSED (one print)** | HY–IG **251 bps** Thu 10/22 (239 on 10/15; 246 on 10/16); HY OAS 340, cycle peak; CCC 1,340, a 52-week high; HYG +0.25% | 🟡 HY–IG >250 bps | 🔴 >350 bps |
| Market Breadth | 🟢 **Cleared yellow** | S&P 500 58.0% above 50D (45.0% last week), 55.8% above 200D; new highs/lows 19 / 8; RSP +1.57 pts vs. SPY WoW; market-wide 33.7% above 50D | 🟡 <50% above 50D MA | 🔴 <40% |
| Sector Rotation | 🟡 **No new leadership trigger; XLC and SMH the outflows** | XLK -0.13% (+0.30 vs. SPY); XLC -4.36%, SMH -2.33%; eight of twelve beat SPY; XLE leads | 🟡 XLK -5% vs. SPY | 🔴 XLK -10% |
| Sector Correlation | 🔴 **FLIP: XLV +0.059 → -0.071** | XLP -0.371, XLE -0.263; XLU 0.024 and XLRE 0.111 next; growth bloc 0.73–0.84 | 🔴 positive → negative flip | — |
| DXY | 🟢 **Under 102** | 101.81 (-0.03% WoW); 102.08 intraweek | 🟡 >102 | 🔴 >105 |
| Geopolitics | 🔴 **Oil above $100** | Feed WTI $101.41 (CLX26) stale from 10/16; December (CLZ26) $103.27 Fri, direction only; Brent $111.70; Hormuz (#175) | 🟡 Oil >$90 | 🔴 Oil >$100 |
| Credit Risk | 🟡 Index and CCC both widening (CDS not sourced) | XLF +0.68% to $55.90; EM OAS +14 bps; CCC +62 bps W/W | 🟡 CDS widening | 🔴 Bank stress |
| Policy | 🔴 **Live hiking cycle; FOMC Wednesday** | Fed 3.75–4.00% (hiked 9/16); October hike ~10%, December ~84%; PCE and GDP Thu 10/29 | — | — |
| Overall Risk | 🟡 **HIGH CAUTION (credit and correlation triggers crossed; breadth cleared)** | — | — | — |

**Weekly Narrative — Overall Assessment:** Breadth healed and credit broke. The ledger: (1) **SPY fell -0.43% to $759.97**, a second down week, and stayed under its 50-day ($767.81); (2) **S&P 500 breadth cleared the yellow line**: 58.0% of members above the 50-day (45.0% last week, 25.5% a month ago), 55.8% above the 200-day, 42 new highs on Thursday, RSP +1.14%; (3) **HY–IG crossed 250 bps for the first time on this board (251 on Thursday)**, with HY OAS at a 340 cycle peak and CCC at 1,340; (4) **healthcare's correlation with SPY flipped negative** (+0.059 → -0.071), and utilities (0.024) and real estate (0.111) are close behind; (5) **the 10Y fell 11 bps to 4.988%**, its first weekly close under 5.00% in five weeks, almost all of it on Thursday's 19 bp drop when SOX fell 6.7%; the 2Y fell 12 bps with it, so the curve did not change shape (10Y–2Y +34); (6) **VIX touched 20 twice intraday** (20.31, 20.66) and closed 19.45; VIX/VIX3M 0.950, VVIX 110; (7) **XLC fell -4.36%** on Netflix and Meta, SMH -2.33%, XLK flat; energy (+1.60%) and healthcare (+1.45%) led; (8) **December WTI settled $103.27** on Hormuz headlines after November's expiry; our feed did not roll, so WTI and gold are carried stale; (9) **gold's spot month broke $4,000** (-4.05%) while real yields fell; (10) the data did not show a slowdown: claims 194K, flash PMI 57.6, UMich 48.0 (wiki/economic-calendar.md).

The fragilities: (1) credit is now through its trigger while the equity tape is improving underneath, and those two do not usually last together; (2) the bond rally is coming from equity stress, not from inflation, and Thursday's PCE can reverse it from 1.2 bps under 5.00%; (3) the defensive bloc is decoupling from the index (three negative correlations, two near zero), which protects a diversified book but says the index is a growth bet; (4) VIX/VIX3M has stayed above 0.89 for two weeks, so the curve has little room before backwardation; (5) gold falling with real yields for a second week is a deleveraging signature; (6) oil above $100 on the December contract arrives in the week of PCE.

**The Canary Watch verdict:** 🟡 **HIGH CAUTION**, the ninth straight week of caution and the second at this level. Composition changes: **Credit Spreads** goes from green to red (trigger crossed); **Sector Correlation** goes from yellow to red (new flip); **Market Breadth** goes from yellow to green; **Sector Rotation** stays yellow with no new trigger; **VIX**, **Yield Curve**, **DXY**, **Geopolitics** and **Policy** unchanged. Of the four strict criteria, **two were met**: credit spreads widened above 250 bps (HY–IG 251) and a sector correlation flipped from positive to negative (XLV). VIX touched above 20 intraday but did not close there; the curve is positive at every tenor. **Issue #177** opened this run; related: #175 (energy, Hormuz), #176 (comm services), #172 (last week's VIX spike). Watch: (1) Friday Oct 23's OAS on Monday: HY–IG above 250 on a second print confirms the trigger; (2) Monday's December WTI settle (a second close above $100); (3) FOMC Wednesday 2:00 PM and Microsoft / Alphabet after the close; (4) Q3 GDP and core PCE Thursday 8:30 AM; (5) VIX 20 on a close and VIX/VIX3M above 1.00; (6) XLU at 0.024, the next correlation flip; (7) SMH's 200-day near $515; (8) 10Y 5.00% on a close.

---

## COUNCIL READ — What This Means for Monday

*(Updated this week: credit crossed its trigger, healthcare's correlation flipped negative, and breadth cleared its yellow line.)*

**Ophelia:** *"The data this week was hot and the bond market rallied anyway. Claims 194, PMI 57.6 with output prices at a three-year high, UMich above every estimate. The ten-year fell eleven basis points because semis fell seven percent on Thursday. That rally is borrowed from the equity market, and Thursday's PCE can take it back. I am not extending duration into Wednesday and Thursday: I said last week I would add IG at the margin, and I did; I stop there. Cash stays at 25–30%. Energy stays, with December above a hundred. What changed for me is the correlation board: healthcare, staples and energy all move against the index now, and utilities are at zero. A diversified book is better hedged than it has been all year. A cap-weighted one is a growth bet.\"*

**Marky:** *"Last week I said I wanted SPY back over its 50-day before I believed the breadth. It isn't, and I believe the breadth anyway: 58% of the S&P above the 50-day, 42 new highs on the day semis fell almost seven percent. That is a market rotating, not one breaking. VIX touched 20 twice and closed under it both times, and the low of the week was 16.5. I keep the hedge on through Wednesday because VVIX is 110 and the ratio is 0.95, but I am not adding to it. If VIX closes above 20 with the ratio above one, that changes. Until then, the equal-weight index is the trade, not the cap-weight one.\"*

**Cecil:** *"Two hundred fifty-one. I said if HY–IG printed 250 or wider the trigger fires and I want the council's high-yield exposure at zero. It printed 251 on Thursday, so that is my recommendation for Monday: high yield to zero, and keep it there until the spread prints back under 240. One print is not a trend, and Friday's number comes out Monday, but I set the rule before the print and I am not moving it after. CCC is out another sixty-two basis points to 1,340 and EM jumped ten on Thursday. HYG went up this week only because Treasuries rallied; the spread did not. IG duration I keep. The trade is still the same: own the duration, not the credit.\"*

---

## SOURCES & REFERENCES

- Yahoo Finance (yfinance 1.6.0, single fetch 2026-10-25 ~09:00 ET): VIX, VIX3M, VVIX, SPY, RSP, QQQ, IWM, 12 sector ETFs, Treasury yield proxies (^IRX/^FVX/^TNX), DXY (DX-Y.NYB), FX (EURUSD=X, JPY=X, GBPUSD=X, CNY=X), copper (HG=F), Bitcoin (BTC-USD), bond ETFs (HYG, LQD, TLT), Brent (BZ=F, direction only); CLZ26.NYM, GCV26.CMX and GCZ26.CMX for direction only (not in facts.json)
- data/market_state.json (Universe & Data Feed Builder): **as_of 2026-10-16, not rebuilt for 2026-10-23** (cron.log shows UNIVERSE & DATA FEED BUILDER START on 2026-10-24 with no new file committed). WTI $101.41 (CLX26) and gold $4,159.50 (GCV26) carried stale in facts.json with their own as_of; CL=F and GC=F were not used
- CBOE: official VIX daily history (cdn.cboe.com VIX_History.csv), Fri 2026-10-23 close 19.45, high 20.66, exact match on all five closes; daily options market statistics (cdn.cboe.com daily_options) for total / equity / index / SPX put/call ratios, 9/21–10/23
- FRED (St. Louis Fed): the runner's own connection timed out on every series (two attempts each); all nine were downloaded in one fredgraph request through a second network path during the run. Live on this page: DGS2 (4.65%, Thu 10/22; source of the 2Y row and facts.json ust_2y), DGS10 / DGS3MO (cross-checks), BAMLH0A0HYM2 / BAMLC0A0CM / BAMLEMCBPIOAS / BAMLH0A3HYC through Thu 10/22, T10YIE through Fri 10/23, VIXCLS through Thu 10/22
- Federal Reserve: FOMC 2026 calendar (decision Wed Oct 28). Fed funds range and stance in facts.json unchanged (no policy event; blackout); `next_macro_gate` rolled forward to the FOMC and Thursday's GDP / PCE from wiki/economic-calendar.md (updated 2026-10-25)
- Breadth: S&P 500 constituent closes via Yahoo (503 of 503 members with a Fri print; constituent list from Wikipedia's S&P 500 table), cross-checked against Finviz Elite (`finviz_elite breadth --json`, S&P 500 and market universes, fetched 2026-10-25 13:07 UTC); market-wide NYSE + Nasdaq + AMEX counts from the same Finviz Elite run. Only derived counts and percentages are published
- Internal desk cross-references, used for every news item on this page; none was re-sourced by this run: wiki/economic-calendar.md (claims, PMIs, UMich, housing, 20Y auction, Meta, Lam, Netflix, SOX, Hormuz, CLZ26 settles, hike odds, next week's calendar), wiki/energy.md
- GitHub issues cross-referenced this run: #172, #175, #176. **One new issue opened this run: #177** (HY–IG above 250; XLV correlation flip; VIX intraday touches)

---

*Last updated by Saturday Research Crew: 2026-10-25 (single-agent run, late: scheduled Sat 2026-10-24 19:39 ET, ran Sun 2026-10-25 ~09:00 ET; all market data as of Fri 2026-10-23 closes; macro/facts.json regenerated from the same fetch; breadth live from S&P 500 constituents with a Finviz Elite cross-check; put/call live from CBOE; FRED series live via a second network path after the runner's connection timed out; WTI and gold carried stale from the 2026-10-16 feed)*
*Next update: Every Saturday 7:39 PM ET*
*Data sources: Yahoo Finance (yfinance), data/market_state.json (feed), CBOE, FRED, Finviz Elite, Federal Reserve*
