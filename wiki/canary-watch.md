# Wiki — Canary Watch

> **The Early Warning System for the Market Consciousness Orchestra**
>
> *"The canary does not predict the mine collapse. It simply dies first. Watch the canary."* — Marky

> **Truth layer:** every macro number on this page equals `macro/facts.json` (generated 2026-10-12, same fetch, commit 1ec0837). Week ending Friday 2026-10-09 closes.

> **Run note:** this update ran late (Monday 2026-10-12 ~00:15–01:10 ET; scheduled Saturday 2026-10-10 19:39 ET), after the rest of the Saturday crew, which also ran late tonight. **FRED timed out from the runner's own connection again** (nine series, two attempts each, 25-second read timeouts), as it did on 2026-10-04. Every FRED series was then downloaded through a second network path during the same run, so **nothing on this page is carried stale**: DGS2 / DGS10 / DGS3MO and the four OAS series are posted through Thu 2026-10-08 (FRED's usual one-day lag), the 10Y breakeven through Fri 2026-10-09, VIXCLS through Thu 2026-10-08. WTI and gold are the committed feed's settlements from `data/market_state.json` (as_of 2026-10-09), with their contract months written beside them, per the 2026-10-06 owner decision. The feed's d1w is the week's change for both.

---

## VOLATILITY REGIME

| Metric | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| VIX | 14.84 | 15.31 | 17.84 | 🟢 **Normal** |
| VIX 20-Day MA | ~15.65 | — | — | — |
| VIX Trend | Down (-3.07% WoW); closes 15.52 / 15.01 / 15.08 / 15.41 / 14.84; intraweek high 16.46 Thu 10/8, low 14.77 Fri 10/9; **no close above 16.00** (four last week) | — | — | — |
| VIX3M (term structure) | 17.77 (VIX/VIX3M 0.835, contango) | 18.01 (0.85) | 19.73 | 🟢 **Contango held all week (ratio range 0.835–0.862)** |
| Implied SPY Move (30D) | ~±4.3% | ~±4.4% | — | — |
| VVIX (VIX of VIX) | 84.88 | 87.02 | 102.66 | 🟢 **Lowest Friday since the September hike (intraweek 92.18 Thu)** |
| Total Put/Call Ratio (CBOE) | 0.82 (5D avg 0.85) | 0.78 (5D avg 0.84) | 0.83 | 🟡 **Index hedging steady; 0.89 Thu on the semis selloff** |
| Equity Put/Call Ratio (CBOE) | 0.56 (5D avg 0.59) | 0.58 (5D avg 0.53) | 0.60 | 🟡 **Less complacent than last week (no day below 0.56; 0.38 on 9/29 was the low)** |

> *Source note: VIX prints vary by vendor — discrepancies of ~2–3 pts are common across quote sources (delayed feeds, spot vs. VX futures, stale prints). Canonical reference: CBOE official close / FRED VIXCLS. This week the Friday close was cross-checked against the **CBOE official daily history file (VIX_History.csv): Fri 2026-10-09 close 14.84**, an exact match for Yahoo ^VIX (14.84), and the CBOE file matches Yahoo on all five closes (15.52 / 15.01 / 15.08 / 15.41 / 14.84) and on the week's high (16.46, Thu 10/8). **FRED VIXCLS** is posted through Thu 10/8 (15.41) and agrees with both. **Put/call ratios** are from CBOE's official daily market statistics file (cdn.cboe.com daily_options), Fri 2026-10-09 vs. Fri 2026-10-02 and Thu 2026-09-10 (21 sessions back); 5D averages are Mon–Fri of each week. Index put/call was 1.13 Friday (5D avg 0.98) and SPX + SPXW 1.24 (5D avg 1.12), the highest Friday SPX reading in the 18 sessions this run fetched.*

**Marky Interpretation:** Vol went back to sleep, and it did so through a week with a 10-year auction, FOMC minutes that promised another hike, and a Thursday in which the Nasdaq fell 1.24% and SMH 2.85% on the OpenAI-funding story (wiki/economic-calendar.md, wiki/semiconductors.md). VIX closed Friday at **14.84 (-3.07% WoW)**, its lowest Friday close since the week before the September hike, and **did not close above 16.00 once** after four such closes last week. Thursday's **16.46** high was the week's only test of the 16.50 line, and it failed by four cents. VIX3M is 17.77 and the ratio finished at **0.835**, so the curve steepened back out as the front end fell. VVIX finished at **84.88**, the first Friday below 85 since August in this fetch. Implied 30-day SPY move is **~±4.3%**. The put/call tape split the other way from last week: **total put/call averaged 0.85** (0.84), unchanged, while **equity put/call rose to 0.59 from 0.53** and the lowest day was 0.56, so the single-stock call buying that marked September eased a little. Index traders bought SPX puts on Friday (SPX + SPXW 1.24) into a CPI week. My lines are unchanged: 16.50 on a Friday close is the tell, 20 is the regime question, 25 is the alarm. None of them was close this week.

---

## YIELD CURVE

| Maturity | Yield | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| 13-Week (T-Bill) | 4.057% | +0.064% | +0.212% (vs. 3.845% on 9/10) | **Front end rose every day (4.018 → 4.057): a December hike is being priced back in** |
| 2-Year | 4.75% (FRED DGS2, Thu 10/8 — see note) | -0.08% (vs. 4.83% Fri 10/2) | +0.19% (vs. 4.56% on 9/10) | **Lower on the week: 4.84 Mon, then 4.79 / 4.77 / 4.75** |
| 5-Year | 5.021% | -0.034% | +0.288% | Belly closes 5.066 / 5.028 / 5.021 / 4.991 / 5.021; first close below 5.00% since 9/28 on Thursday |
| **10-Year** | **5.244%** | **-0.033%** | **+0.300%** | **Third weekly close above 5.00%; closes 5.311 / 5.269 / 5.277 / 5.231 / 5.244; Monday's 5.311% was a new cycle-high close, 5.364% intraday a new cycle high** |
| **10Y–2Y Spread** | **~+49 bps** (Fri 10Y vs. Thu 2Y) | +4 bps vs. last week's +45 | — | **Positive; a touch steeper because the 2Y fell more than the 10Y** |
| **10Y–5Y Spread** | **~+22.3 bps** | +0.1 bps (was +22.2) | — | **Unchanged — the long end did not extend** |
| **10Y–3M Spread** | **~+119 bps** | -9 bps (was +128) | — | **Positive, flatter: bills up, 10Y down** |

> *2Y source: FRED DGS2, back to normal this week (last week the 2Y was read from Treasury.gov because FRED was unreachable; Treasury's Fri 10/2 print of 4.83% is the same series). FRED posts with a one-day lag, so the 2Y is as of Thu 2026-10-08, and the 10Y–2Y spread pairs Friday's 10Y with Thursday's 2Y. On a same-day Thursday basis (FRED DGS10 5.22% vs. DGS2 4.75%) the spread is +47. macro/facts.json carries 4.75 with as_of 2026-10-08 and source fred:DGS2. ^IRX is a discount-basis T-bill yield; FRED's constant-maturity 3M (DGS3MO) was 4.23% Thursday, about 18 bps higher, so a CMT-basis 10Y–3M would read ~+99 bps. This page and facts.json use ^IRX for series continuity. FRED's DGS10 for Thu 10/8 is 5.22%, consistent with ^TNX's 5.231% Thursday close within rounding.*

**Ophelia Interpretation:** The long end stopped. Last week I said a cool PCE print and weak payrolls had not fixed a term-premium move and that Wednesday's 10-year auction was the test. The auction cleared at 5.300% with the strongest cover and indirect share in the series (2.77, 80.3%, per wiki/economic-calendar.md), the 30-year cleared at 5.618% without incident, and the **10Y finished the week 3.3 bps lower at 5.244%**, having set a **cycle-high close of 5.311% on Monday and a cycle-high print of 5.364% intraweek** before the auction. So the term-premium leg made its high and then held, which is not the same as reversing. What moved was the short end, in the opposite direction from last week: the **13-week bill rose 6.4 bps to 4.057%** and climbed every day, as the September minutes (most participants see another hike by year-end) and Waller (more hikes needed, pace flexible) put December back into the price. The 2Y fell 8 bps to 4.75%, which looks contradictory until you notice that it had already priced a hike it now expects two months later. Net: **10Y–3M flattened +128 → +119 bps** while **10Y–2Y steepened +45 → +49**. The curve is positive at every tenor, the belly is back under 5.00% on some closes, and the next test is not an auction. It is Wednesday's CPI, with a +0.6% headline consensus and the bond market closed Monday.

**Yield Curve Regime:** 🟡 **Positive, flattening from the bill end (bills up, 2Y and 10Y down).** No inversion anywhere. The long end held its cycle high (5.364% intraday) rather than extending it. Next gates: **September CPI Oct 14 (consensus headline +0.6%, core +0.2%), PPI / retail sales / Fed Chair Warsh Oct 15, FOMC Oct 27–28**.

---

## CREDIT SPREADS

> *OAS rows are FRED's **Thu 2026-10-08** prints (FRED's one-day lag), with Thu 10/1 as the week-ago column and Thu 9/10 as the month-ago column. Friday Oct 9's OAS posts Monday. HYG and LQD are live Friday closes.*

| Spread | Current | 1W Ago | 1M Ago | Regime |
|---|---|---|---|---|
| HY OAS (ICE BofA US HY, BAMLH0A0HYM2) | **315 bps** (Thu 10/8) | 324 bps | 270 bps | 🟡 **Nine straight sessions above 300 (since 9/28); off the 10/1 peak of 324 but higher every day since Tuesday's 303** |
| IG OAS (ICE BofA US Corp, BAMLC0A0CM) | 82 bps (Thu 10/8) | 86 bps | 80 bps | 🟡 **Tightened 4 bps; still 5 wider than a month ago** |
| **HY–IG Spread** | **233 bps** (Thu 10/8) | 238 bps | 190 bps | 🟢 **Below the 250 bps trigger by 17; narrowed 5 on the week after +37 the week before** |
| EM Corporate OAS (BAMLEMCBPIOAS) | 158 bps (Thu 10/8) | 161 bps | 131 bps | 🟡 **Holding the late-September widening (2026 high 182 on Mar 30)** |
| CCC & Lower OAS (ICE BofA, BAMLH0A3HYC) | **1,252 bps** (Thu 10/8) | 1,215 bps | 1,070 bps | 🔴 **New 52-week high; +37 bps in a week when the HY index tightened 9 — the bottom tier is decoupling** |
| **HYG Price** | **$77.23** | **$76.91** | **$78.62** | 🟡 **First up week after five down (+0.42%)** |
| **LQD Price** | **$102.41** | **$101.83** | **$104.36** | 🟡 **+0.57% on a 3 bp rally in the 10Y; still -1.87% over a month** |

**Cecil Interpretation:** I have the prints this week, and they say two things at once. The **HY index tightened 9 bps to 315**, so the eight-session widening that took it from 266 to 324 has stopped, and **HY–IG came in to 233**, seventeen under the trigger. **HYG rose for the first time in six weeks** (+0.42%), LQD rose more (+0.57%), and the 10Y fell 3 bps, so the ETFs did roughly what rates told them to. That is the calm reading. The other reading is the **CCC tier at 1,252 bps, a new 52-week high**, up 37 bps in the same week the index tightened. When the broad high-yield index narrows and the weakest third of it widens, the index is being carried by BB paper and the stress is concentrating where it always goes first. HY has now spent nine straight sessions above 300. In February–April it spent weeks there and the economy did not break, so the level alone is not a signal. The composition is what I am watching: **HY–IG against 250 is the trigger, but CCC-minus-HY is the leading indicator**, and it widened to about 937 bps from 891. Bank earnings start Tuesday; provisions and charge-offs are the first real read on whether the +29K payrolls print has reached credit.

**Credit Regime:** 🟡 **Wide and stable at the index, widening at the bottom.** HY OAS 315 bps, above 300 for nine sessions. HY–IG 233 bps, under the 250 bps trigger. CCC at a 52-week high. HYG's losing streak ended at five weeks. Next: Friday Oct 9's prints (posted Monday) and bank provisions Oct 13–14.

---

## MARKET BREADTH

> *S&P 500 rows are computed from the daily closes of all 503 constituents with a Fri 2026-10-09 print (Yahoo, list from Wikipedia's S&P 500 table; 50D/200D = simple MA of closes; a new high/low means the day's high/low reached the trailing 252-session extreme). They are cross-checked against the **Finviz S&P 500 screener**, which agrees within one name on every row: 35.2% above 50D (177/503) vs. 35.0% here (176), 47.5% above 200D (239) vs. 47.3% (238), 319 up / 184 down, 15 new highs / 5 new lows (all exact). Market-wide rows are Finviz's NYSE + Nasdaq + AMEX totals for Friday. The 1W and 1M comparisons are recomputed from this fetch on the current 503-member list, so last Friday reads 42.1% above 200D here against 42.3% published.*

| Metric | Current | 5D Avg | 20D Avg | Regime |
|---|---|---|---|---|
| S&P 500 Advance/Decline (Fri) | **1.73** (319 up / 184 down) | 1.60 | 1.09 | 🟢 **Four up-days of five (317 / 338 / 138 / 339 / 319 advancers); 5D and 20D both above 1 for the first time since August** |
| Market-wide Advance/Decline (Fri, Finviz) | 1.04 (2,732 up / 2,629 down) | — | — | 🟡 **Barely positive across all listings** |
| S&P 500 New 52-Week Highs | **15** | 12.6 | 10.2 | 🟡 **Low but rising; 23 on Tuesday (SPY's record close)** |
| S&P 500 New 52-Week Lows | **5** | 10.2 | 21.8 | 🟢 **Highs beat lows four days of five; 2 lows on Tuesday** |
| Market-wide New Highs / Lows (Fri, Finviz) | 86 / 274 | — | — | 🔴 **Lows still 76% of the total outside the S&P 500** |
| **S&P 500 % Above 50D MA** | **35.0%** (1W 24.7%, 1M 33.9%) | 30.3% | 28.8% | 🔴 **Below the 40% red trigger for a third week, but up 10 points from last Friday and 14 from the 9/30 low (20.9%)** |
| **S&P 500 % Above 200D MA** | **47.3%** (1W 42.1%, 1M 54.8%) | 45.5% | 46.7% | 🟡 **Under 50%, rising for the first time in five weeks** |
| Market-wide % Above 50D / 200D (Fri, Finviz) | 28.7% / 39.4% | — | — | 🔴 **The average listed stock is still below both** |
| Equal-Weight (RSP) vs. Cap-Weight (SPY), 1W | **+0.42 pts** (RSP +1.58% vs. SPY +1.16%) | — | 1M: **-2.80 pts** | 🟡 **RSP's first up week since Aug 14 and its first week ahead of SPY since mid-August; the 1M gap narrowed from -4.65** |
| Sector ETFs above own 50D MA | **4 of 12** (XLK, SMH, XLE, XLV) | — | — | 🔴 **Up from 3 (XLV regained it)** |

**Marky Interpretation:** This is the first week since August in which breadth got better, and it got better in the week the leaders fell. SPY rose **+1.16% to $778.57**, with a **record close of $779.09 on Tuesday** (wiki/economic-calendar.md; the highest close in this fetch, which runs from June), and finished 1.4% above its 50-day ($767.57). Under it, **35.0% of S&P 500 members are above their 50-day**, up from 24.7% a week ago and from the 30-session low of 20.9% on Sep 30. **47.3% are above their 200-day**, up five points. New highs beat new lows on four days of five and the Friday count was **15 to 5**, after 10 to 19 last week and 3 to 40 on Oct 1. **RSP rose +1.58%**, its first up week since Aug 14, and beat SPY for the first time since then. The 5-day advance/decline average is 1.60 and the 20-day crossed back above 1.

Hold the applause. **35.0% is still five points under this board's 40% red trigger**, and the improvement came from the average stock rising while **SMH fell 4.32% and XLK 0.52%**. That is rotation, not expansion: the index made a record on Tuesday with 23 new highs out of 503 members. The market-wide picture outside the S&P 500 barely moved, with new lows still 76% of the total and only 28.7% of all listed stocks above their 50-day. Wednesday was the one broad down-day (138 up / 361 down) and it came on a 10-year auction that cleared well.

**Breadth Regime:** 🔴 **Below the red trigger for a third week, improving.** S&P 500 % above 50D (35.0%) needs 40% to come off red and 50% to come off yellow; 20.9% (Sep 30) is the low to hold.

---

## SECTOR CORRELATION MATRIX

*30-day rolling correlation of daily returns vs. SPY (30-calendar-day window, 22 sessions 2026-09-10 → 2026-10-09; same convention as prior weeks; the 1W-ago column is recomputed from this fetch for the window ending 2026-10-02)*

| Sector | ETF | vs. SPY Correlation | 1W Ago | Regime |
|---|---|---|---|---|
| 🖥️ Technology | XLK | **0.847** | 0.843 | 🔥 **High beta (flat — index leader again)** |
| 🛍️ Consumer Discretionary | XLY | **0.838** | 0.888 | 🔥 **High beta (eased)** |
| 💻 Semiconductors | SMH | **0.672** | 0.595 | 🔥 **High beta (rose — see note on the feed's 4-week measure)** |
| 🏠 Real Estate | XLRE | **0.569** | 0.737 | 🔥 **High beta (largest drop on the board)** |
| ⚙️ Industrials | XLI | **0.547** | 0.621 | 🔥 **High beta (falling)** |
| 🏦 Financials | XLF | **0.490** | 0.623 | 🟡 **Moderate (fell 13 pts)** |
| ⛏️ Materials | XLB | **0.439** | 0.394 | 🟡 **Moderate (rising)** |
| ⚡ Utilities | XLU | **0.428** | 0.373 | 🟡 **Moderate (rising — rate beta)** |
| 📡 Communication Services | XLC | **0.369** | 0.494 | 🟡 **Decoupling (fell 12 pts)** |
| 🏥 Healthcare | XLV | **0.231** | 0.307 | 🟡 **Low** |
| 🍞 Consumer Staples | XLP | **-0.009** | 0.095 | 🔴 **FLIPPED positive → negative (second flip in three weeks; see Alert)** |
| ⛽ Energy | XLE | **-0.171** | -0.242 | 🔴 **Inverse, easing for a second week** |

**Ophelia Interpretation:** Last week every one of the twelve correlations rose and I said the tape was trading one factor. This week **eight of twelve fell**, and the dispersion came back. The sectors that uncoupled are the ones that outperformed: **XLRE fell from 0.737 to 0.569, XLF from 0.623 to 0.490, XLC from 0.494 to 0.369**, while XLK held at 0.847 and **SMH rose to 0.672**. That last number needs a word. The committed feed's 4-week measure in data/market_state.json has SMH at **-0.144**, a flip from 0.883, because it is built on a shorter window in which SMH fell 4.3% in a week SPY rose 1.2%. On this page's 30-calendar-day daily-return window SMH still moves with the index on most days; it moved against it on three. The two measures disagree because they measure different things, and this page's number is the one its trigger uses. **Consumer Staples is the strict flip: +0.095 to -0.009.** It is the second time in three weeks (0.105 → -0.034 on Sep 25, back to +0.095 on Oct 2, now -0.009), and both readings are within a hair of zero. Statistically that is a sector with no relationship to the index, not a hedge against it. The rule on this board does not make that distinction, so the alert fires. **Energy's inverse eased again** (-0.242 → -0.171) and for a second week it worked the right way round: XLE rose +3.60% in a week SPY also rose.

**The key insight:** when correlations fall together while the index rises, money is moving between sectors rather than in or out of the market. That is what this week was. The place to look for trouble is not the matrix but the rotation table beneath it, where the two sectors that carried the index for a month were the two that lagged it this week.

**Alert:** 🔴 **Strict-criterion flip: Consumer Staples (XLP) crossed from +0.095 to -0.009.** A GitHub issue is opened this run (see Sources) and cross-referenced to #118, which recorded the Sep 25 flip. No other sector crossed from positive to negative; XLE remains negative and eased.

---

## SECTOR ROTATION FLOW

*1-Day / 1-Week / 1-Month performance vs. SPY (1D = Fri 10/9 vs. Thu 10/8; 1W = Fri-to-Fri; 1M = 21 sessions from 2026-09-10). SPY: +0.60% / +1.16% / +2.74%.*

| Sector | ETF | 1D vs. SPY | 1W vs. SPY | 1M vs. SPY | Rotation Signal |
|---|---|---|---|---|---|
| ⚡ Utilities | XLU | +0.23% | +2.81% | -5.35% | 🟢 **Inflow (leader this week: +3.97%; second up week; CEG/VST nuclear PPAs, wiki/utilities.md, #158)** |
| ⛽ Energy | XLE | -0.85% | +2.44% | -2.51% | 🟢 **Inflow (second week; Hormuz, wiki/energy.md)** |
| 🍞 Consumer Staples | XLP | -0.59% | +2.44% | -2.33% | 🟢 **Inflow (back from outflow: +3.60%)** |
| 🏥 Healthcare | XLV | +0.98% | +1.63% | +0.37% | 🟢 **Inflow (from worst on the board to above its 50-day)** |
| 🛍️ Consumer Discretionary | XLY | +0.42% | +1.39% | -1.95% | 🟢 **Inflow (despite UMich 46.3, #156)** |
| 🏦 Financials | XLF | +0.32% | +1.16% | -6.50% | 🟡 **Inflow on the week, worst on the board over a month; bank earnings Oct 13** |
| 🏠 Real Estate | XLRE | +1.26% | +0.80% | -6.08% | 🟡 **Neutral (best 1D on Friday's 10Y dip)** |
| ⛏️ Materials | XLB | -0.28% | +0.01% | -5.36% | 🟡 **Neutral (matched the index)** |
| 📡 Communication Services | XLC | -2.11% | -1.11% | -3.74% | 🔴 **Outflow (flat week, -1.51% Friday)** |
| ⚙️ Industrials | XLI | -0.10% | -1.57% | -3.50% | 🔴 **Outflow (only non-tech sector down on the week)** |
| 🖥️ Technology | XLK | -0.09% | -1.68% | +4.58% | 🔴 **Outflow this week, still +4.6 pts ahead over the month** |
| 💻 Semiconductors | SMH | -1.25% | -5.48% | +4.94% | 🔴 **Outflow (leadership break: -4.32% on the OpenAI-funding story, wiki/semiconductors.md, #159)** |

**Ophelia Interpretation:** **The rotation table inverted.** Last week six sectors were in outflow and the two inflows were SMH and XLK. This week **four are in outflow and SMH and XLK are two of them**: SMH **-5.48% vs. SPY** after a -2.85% Thursday on the report that OpenAI's revenue runs about $20B under estimates and Broadcom is raising $50B+ to finance its chips (wiki/economic-calendar.md), XLK -1.68%. The money went to the sectors that had been left behind: **XLU +3.97%, XLE +3.60%, XLP +3.60%, XLV +2.79%, XLY +2.55%, XLF +2.32%**. Nine of twelve sectors beat SPY on the week; last week it was four. Over a month the picture has not changed: **SMH and XLK are still the only two ahead of the index (+4.94 and +4.58 pts)**, and XLF (-6.50), XLRE (-6.08), XLB (-5.36) and XLU (-5.35) are still more than five points behind. One week of rotation does not undo five weeks of concentration; it does say the concentration is no longer being added to.

**The risk:** the board's leadership trigger is XLK at -5% vs. SPY in a week. XLK was -1.68%, so it did not fire. The semis trigger is not on this board, and SMH did -5.48%. If the pattern of this week holds into CPI, the index can hold its level while its two carriers keep falling, and that is the configuration in which the % above 50D improves while the cap-weighted index stops. Watch SMH $600.32 (the week's low, wiki/economic-calendar.md) and XLK against its 50-day, which it still holds.

---

## CROSS-ASSET SIGNALS

| Asset | Level | 1W Change | 1M Change | Implication |
|---|---|---|---|---|
| DXY (US Dollar Index) | **102.21** (Yahoo DX-Y.NYB) | +0.27% | +3.15% | 🟡 **Through the 102 trigger on a close: four of five closes above it (102.17 / 101.83 / 102.24 / 102.14 / 102.21); high 102.54; fourth straight weekly gain** |
| EUR/USD | 1.1213 | -0.33% | -3.62% | 🟡 **Euro lower for a fourth week** |
| USD/JPY | 158.063 | +0.09% | +2.92% | 🟡 **Flat; range 157.45–158.49 (see note)** |
| WTI Crude | **$91.85 (CLX26)** | +0.8% (feed d1w, same contract) | -6.66% (CLX26 vs. its 9/10 close $98.40) | 🟡 **Above $90; settles $89.43 / $89.44 / $88.28 / $91.49 / $91.85; range $86.86–$93.20** |
| Brent Crude | $104.72 | +2.42% | -2.70% | 🟡 **Above $100 while WTI is not; directional only (see note)** |
| Gold | **$4,191.00 (GCV26)** | +1.4% (feed d1w) | -4.18% (GCV26 vs. its 9/10 close $4,373.70) | 🟢 **First up week after two down; Friday's $4,191 was the week's high close** |
| Copper | $6.6425/lb (HG=F front month) | +2.32% (vs. HG=F's 10/2 bar $6.492) | +2.71% | 🟡 **Recovered last week's loss; December HGZ26 $6.692, +2.18% / +2.21% like-for-like (see note)** |
| Bitcoin | $82,546 (Fri 10/9 UTC close) | -2.31% | +7.81% | 🟡 **Fell with semis Wed–Thu (low $80,337 Thu); held $80K** |
| HY Bonds (HYG) | $77.23 | +0.42% | -1.77% | 🟡 **First up week after five down** |
| IG Bonds (LQD) | $102.41 | +0.57% | -1.87% | 🟡 **Duration relief on -3 bps 10Y** |
| TIPS Breakeven (10Y) | 2.33% (FRED T10YIE, Fri 10/9) | -0.03 pts | -0.07 pts | 🟢 **The 10Y's 3 bp fall was all breakeven; 10Y real yield about 2.91%, unchanged** |

> *DXY from Yahoo's ICE DXY series (DX-Y.NYB), carried in macro/facts.json at 102.21 (tolerance 1%). 1W changes use this run's Yahoo fetch for both endpoints; this run fetched about 55 hours after the Friday close, so the Friday bars had settled, and last Friday's bars match last week's published values on every row (DXY 101.93, EUR/USD 1.1257, USD/JPY 157.927, copper HG=F 6.492 as noted last week, Bitcoin $84,497). **WTI and gold** are the committed feed's settlements (data/market_state.json, as_of 2026-10-09): WTI is the **November contract (CLX26)**, gold the **October contract (GCV26)**, and the feed's d1w is measured on the same contract so that a roll is not read as a move. The continuous symbols are not used: GC=F printed $4,216.30 Friday, the active December month, $25 above the spot-month settlement the feed commits. The 1M columns for both compare each contract with its own 9/10 close from this fetch. **Brent (BZ=F)** is a continuous series and last week's page recorded a roll artifact in it; it is shown for direction only. **Copper:** macro/facts.json carries HG=F ($6.6425), which is Yahoo's front-month quote and the series truth_check verifies; its 1W change is against HG=F's own Fri 10/2 bar ($6.492), which last week's page identified as the expiring October contract. The December contract (HGZ26), which last week's table carried at $6.549, settled $6.692, so like-for-like December rose 2.18% on the week and 2.21% on the month. **Bitcoin:** the Fri 10/9 UTC daily bar is present ($82,546, same value and as_of in facts.json); 1W is against the 10/2 UTC close ($84,497). **USD/JPY and EUR/USD:** Yahoo's daily bar for a currency pair closes near its open (macro/README.md, 2026-10-06); the values here are the daily bars, within tolerance of the session's end.*

**Ophelia Interpretation:** The dollar did what last week's page said to watch for: **DXY closed above 102 on four of five days and finished at 102.21**, its fourth straight weekly gain (99.12 → 100.22 → 100.97 → 101.93 → 102.21). The one close below, Tuesday's 101.83, came on a record trade deficit; the move back above came on Wednesday's minutes and Thursday's Waller remarks (wiki/economic-calendar.md), so this leg of the dollar's rise is a rate-differential move again, not the growth scare of last week. **Gold rose +1.4% to $4,191.00 (GCV26)**, its first up week in three, with breakevens falling 3 bps and the 10Y real yield flat at about 2.91%; that is a dollar-and-real-yield gold that rose anyway, which usually means hedging demand. **Copper +2.3%** recovered last week's loss with Shanghai back from holiday (wiki/materials.md). **WTI +0.8% to $91.85** hides a $6 range: it settled $88.28 on Wednesday, then Kpler's report that Hormuz crude flows fell from 12.3M to 2.7M barrels a day in three days and a Gulf hurricane shutting in ~72% of Gulf of Mexico output took it to $91.85 by Friday (wiki/energy.md). **Brent is $104.72, above $100, while WTI is not**: a $12.87 spread, up from $11.14 last week, which is the Hormuz premium measured directly. **Bitcoin fell -2.31%** on the same two days semis did. **Credit ETFs rose for the first time in six weeks.**

**The risk:** the three-way tightening is two legs tight and one leg mixed. The dollar is through its trigger, the 10Y is at a cycle high even after a 3 bp week, and oil is $8 under $100 on WTI with Brent already over it and the physical flow through Hormuz down three-quarters. The bond market is closed Monday, so if oil moves on the Hormuz headlines, Treasuries cannot confirm it until Tuesday and CPI lands Wednesday.

---

## CANARY WATCH TRIGGER BOARD

| Signal | Status | Trend | Trigger Level |
|---|---|---|---|
| VIX Regime | 🟢 Normal (no close above 16.00; 16.46 intraweek high Thu, the 16.50 line held) | -3.07% WoW to 14.84; VVIX 84.88; contango 0.835 | 🟡 >20 | 🔴 >25 |
| Yield Curve | 🟡 Positive, flattening from the bill end | 10Y 5.244% (-3.3 bps; cycle-high close 5.311% Mon, 5.364% intraday); 10Y–2Y ~+49, 10Y–3M +119 (was +128) | 🟡 <0 (inverted) | 🔴 <-50 bps |
| Credit Spreads | 🟢 **Below trigger by 17 bps; index tightened, CCC widened** | HY–IG 233 bps Thu 10/8 (238 on 10/1); HY OAS 315, ninth session above 300; CCC 1,252, a new 52-week high; HYG +0.42%, first up week in six | 🟡 HY–IG >250 bps | 🔴 >350 bps |
| Market Breadth | 🔴 **Below the red trigger (3rd week), improving** | S&P 500 35.0% above 50D (24.7% last week, 20.9% low on 9/30), 47.3% above 200D; new highs/lows 15 / 5; RSP +0.42 pts vs. SPY WoW, -2.80 pts 1M | 🟡 <50% above 50D MA | 🔴 <40% |
| Sector Rotation | 🟡 4 of 12 sectors in outflow (was 6) — and the two leaders are among them | SMH -5.48% and XLK -1.68% vs. SPY; XLU / XLE / XLP / XLV / XLY / XLF inflow | 🟡 XLK -5% vs. SPY | 🔴 XLK -10% |
| Sector Correlation | 🔴 **XLP flipped positive → negative (+0.095 → -0.009); 8 of 12 correlations fell** | Second XLP flip in three weeks, both within 0.04 of zero; XLE -0.171; issue opened | 🔴 positive → negative flip | — |
| DXY | 🟡 **Through the 102 trigger on a close** | 102.21 (+0.27% WoW); four of five closes above 102; 102.54 intraweek; fourth weekly gain | 🟡 >102 | 🔴 >105 |
| Geopolitics | 🟡 Oil above $90; Brent above $100 | WTI $91.85 (CLX26, +0.8%); Brent $104.72; Hormuz crude flows -78% in three days (Kpler via wiki/economic-calendar.md); Gulf hurricane shut-ins | 🟡 Oil >$90 | 🔴 Oil >$100 |
| Credit Risk | 🟡 Index spreads stable, CCC at a 52-week high (CDS not sourced) | XLF +2.32% to $54.73 ahead of JPM / GS / C / WFC Oct 13; HY OAS -9 bps, IG -4 bps, CCC +37 bps since 10/1 | 🟡 CDS widening | 🔴 Bank stress |
| Policy | 🔴 **Live hiking cycle; October hold, December priced** | Fed 3.75–4.00% (hiked 9/16); Sep minutes: most see another hike by year-end; Waller: more hikes, flexible pace; October odds ~20% (wiki/economic-calendar.md) | — | — |
| Overall Risk | 🟡 **CAUTION (rates-led; leadership rotating, dollar at trigger)** | — | — | — |

**Weekly Narrative — Overall Assessment:** The index made a record and its leaders fell. The ledger: (1) **SPY rose +1.16% to $778.57 with a record close of $779.09 on Tuesday**, and finished 1.4% above its 50-day; (2) **SMH fell -4.32% and XLK -0.52%**, the first week since early September in which both lagged the index, on Thursday's OpenAI-funding story (Nasdaq -1.24%, SMH -2.85% that day; #159); (3) **nine of twelve sectors beat SPY**, led by XLU +3.97%, XLE +3.60%, XLP +3.60% and XLV +2.79%, after four of twelve last week; (4) **breadth improved for the first time since August**: 35.0% of S&P 500 members above their 50-day (24.7% last week, 20.9% at the Sep 30 low), 47.3% above their 200-day, new highs 15 to new lows 5, RSP +1.58% for its first up week since Aug 14; (5) **the 10Y set a cycle-high close of 5.311% Monday and a cycle-high print of 5.364%, then the 10-year auction cleared with record cover and the 10Y finished -3.3 bps at 5.244%**, its third weekly close above 5.00%; (6) **the bill rose 6.4 bps to 4.057%** as the September minutes and Waller put December back into the price (wiki/economic-calendar.md), so 10Y–3M flattened to +119 while 10Y–2Y steepened to +49 on a lower 2Y (4.75%, Thu); (7) **VIX fell to 14.84 with no close above 16**, VVIX 84.88, equity put/call up to a 0.59 average; (8) **HY OAS tightened 9 bps to 315 and HY–IG to 233**, while **CCC widened 37 bps to a 52-week high of 1,252**; HYG's five-week losing streak ended; (9) **eight of twelve sector correlations fell** and **XLP flipped negative** (+0.095 → -0.009) for the second time in three weeks; (10) **DXY closed above 102 on four of five days** and finished at 102.21, a fourth weekly gain; (11) **gold +1.4% to $4,191.00 (GCV26)** and copper +2.3% with the 10Y real yield flat; (12) **WTI +0.8% to $91.85 (CLX26) after an $86.86 low**, with Brent $104.72 and Hormuz crude flows down three-quarters.

The fragilities: (1) the index is at a record with 35% of its members above their 50-day and its two month-long carriers in outflow. If the rotation of this week continues, the average stock can keep improving while the cap-weighted index stalls, and the breadth gauge will read better as the index reads worse; (2) the Fed is back. A hike by year-end is the median participant's view, the bill is pricing it, and the dollar is through 102 on it. The long end held its cycle high rather than extending it, which is a pause and not a reversal; (3) CPI on Wednesday carries a +0.6% headline consensus with the bond market closed Monday and oil moving on Hormuz; the first Treasury trade after the Monday oil session is the day before the print; (4) the weakest credit tier is widening while the index tightens. CCC at 1,252 bps with HY at 315 is a 937 bp gap, and bank provisions on Tuesday are the first hard read on whether +29K payrolls has reached loan books; (5) the two sectors at zero correlation to the index, staples and energy, are the two that worked this week, which says the diversification that exists is in the defensives and the oil hedge and nowhere else; (6) Bitcoin fell with semis, so the risk asset that used to be uncorrelated is now the AI trade with leverage.

**The Canary Watch verdict:** 🟡 **CAUTION (rates-led, now with a leadership rotation)**, held for a seventh straight week. Composition changes: **Sector Correlation** goes back to red on the strict XLP flip; **DXY** moves to yellow, through its 102 trigger on a close; **Credit** stays green at the index with the CCC warning in the text; **Breadth** stays red but is the one row that improved; **Sector Rotation** moves from red to yellow on count (4 of 12 in outflow) with the note that the outflows are the leaders. Of the four strict criteria, **one was met**: a sector correlation flipped from positive to negative (XLP), and a GitHub issue is opened this run. VIX closed 14.84 (high 16.46, never near 20); the curve is positive at every tenor; HY–IG was 233 bps on Oct 8 against the 250 trigger. The week's other catalysts are already tracked under **#156** (UMich 46.3), **#158** (utilities nuclear PPAs), **#159** (regime flags; SMH loses $609.66), **#160** (earnings), **#113** (10Y weekly close >5.00%), **#115** (DXY >101), **#118** (the Sep 25 XLP flip) and **#127** (payrolls). Watch: (1) September CPI, Wed Oct 14, 08:30 ET: core above +0.3% is the hawkish case, headline above +0.8% is the oil-broadening case; (2) 10Y 5.364% (Monday's high) on a close, with the bond market closed Monday; (3) DXY 102 as support now that it is through, 105 the next line; (4) HY–IG against 250 and CCC against 1,252; Friday's OAS posts Monday; (5) bank provisions and NII guidance Oct 13–14 (JPM, GS, C, WFC, then BAC, MS); (6) SMH $600.32 (the week's low) and XLK's 50-day: the leadership-break confirmation is SMH below $600 with XLK losing its average; (7) S&P 500 % above 50D: 40% takes the row off red, 20.9% is the low to hold; (8) WTI $95 on Monday with bonds closed (wiki/economic-calendar.md), Brent–WTI spread above $12.87.

---

## COUNCIL READ — What This Means for Monday

*(Updated this week: the leadership rotated out of semis and tech into defensives and energy while the index made a record; the dollar closed through 102; the Fed's December hike came back into the price; credit spreads were measured and are under the trigger.)*

**Ophelia:** *"Last week I told you the long end had stopped responding to the data and that Wednesday's auction was the test. The auction was strong, the ten-year ended lower, and I was wrong about which half of the curve mattered. The bill rose every day because the minutes and Waller put December back on the schedule, and the dollar went through 102 on the same thing. So the regime is a Fed that will hike again into a labor market that has stopped hiring, with oil flows through Hormuz down three-quarters and a CPI consensus of plus point six. Cash stays at 25–30%. The one thing I will say for the week is that the money that left semis went into utilities, staples, energy and healthcare, which are four of the five things I own, so the rotation paid me without my doing anything. I am not adding rate-sensitives before Wednesday at 8:30. Energy I keep: Brent is through $100 and the Hormuz premium is $12.87 and rising."*

**Marky:** *"Breadth got better and I don't trust it yet. Thirty-five percent above the 50-day is a bounce off twenty-one, not a trend, and it happened in the week the index's two carriers fell four and a half points behind it. That is money moving sideways, not in. I kept the leadership and the hedge last week; this week the leadership cost me and the hedge did nothing because VIX fell to fourteen-eighty-four on a semis selloff. That tells you the market has decided the AI-funding story is a sector story and not an index story. Maybe. My lines are the same: VIX 16.50 on a Friday close, 10Y 5.364%, XLK -5% vs. SPY as the leadership break, and I am adding SMH $600 to the list because it did -5.48 and the board only watches XLK. If SMH is under $600 Wednesday night and breadth is still under 40, I cut the leadership."*

**Cecil:** *"I have the numbers this week. High yield tightened nine to 315, HY–IG is 233, seventeen under my trigger, and HYG finally had an up week. I am not relieved. The CCC tier widened thirty-seven basis points to a new fifty-two-week high in a week when the index tightened, and that pattern, index in, bottom tier out, is how every real credit cycle I have watched began. It is not yet a signal; it is a composition. Tuesday the four big banks report and I want provisions and net charge-offs, not the EPS beat. If two of the four raise provisions, the labor flag has reached credit and I move HY–IG's trigger down to 240 in my own book. Until then: no new high yield, IG duration stays where it is, and the CPI print on Wednesday matters more to LQD than anything a bank will say."*

---

## SOURCES & REFERENCES

- Yahoo Finance (yfinance 1.6, single fetch 2026-10-12 ~00:20 ET): VIX, VIX3M, VVIX, SPY, RSP, 12 sector ETFs, Treasury yield proxies (^IRX/^FVX/^TNX), DXY (DX-Y.NYB), FX (EURUSD=X, JPY=X), copper (HG=F, with HGZ26.CMX for the December like-for-like), Bitcoin (BTC-USD), bond ETFs (HYG, LQD), Brent (BZ=F, direction only); CLX26.NYM and GCV26.CMX were fetched only to confirm the feed's settlements (both match: $91.85 and $4,191.00)
- data/market_state.json (Universe & Data Feed Builder, as_of 2026-10-09): WTI $91.85 (CLX26, d1w +0.8%), gold $4,191.00 (GCV26, d1w +1.4%). These are the canonical oil and gold numbers in facts.json (source yahoo:CLX26.NYM / yahoo:GCV26.CMX), per the 2026-10-06 owner decision; CL=F and GC=F were not used
- CBOE: official VIX daily history (cdn.cboe.com VIX_History.csv), Fri 2026-10-09 close 14.84, exact match on all five closes; daily options market statistics (cdn.cboe.com daily_options) for total / equity / index / SPX put/call ratios, 9/28–10/9 and 9/9–9/11
- FRED (St. Louis Fed): the runner's own connection timed out on every series (two attempts each); all nine were downloaded through a second network path during the run. Live on this page: DGS2 (4.75%, Thu 10/8; source of the 2Y row and facts.json ust_2y), DGS10 / DGS3MO (cross-checks), BAMLH0A0HYM2 / BAMLC0A0CM / BAMLEMCBPIOAS / BAMLH0A3HYC through Thu 10/8, T10YIE through Fri 10/9, VIXCLS through Thu 10/8
- Federal Reserve: FOMC 2026 calendar (next meeting Oct 27–28). Fed funds range and stance in facts.json unchanged (no policy event); the stance source note adds the Sep minutes (released Oct 7); `next_macro_gate` rolled forward to CPI Oct 14 / Oct 15 prints and Warsh / FOMC Oct 27–28, from wiki/economic-calendar.md (updated 2026-10-11)
- Breadth: S&P 500 constituent closes via Yahoo (503 of 503 members with a Fri print; constituent list from Wikipedia's S&P 500 table), cross-checked against the Finviz S&P 500 screener (idx_sp500 with ta_sma50_pa / ta_sma200_pa / ta_change_u / ta_change_d / ta_highlow52w_nh / nl), agreement within one name on the MA rows and exact on the rest; market-wide NYSE + Nasdaq + AMEX advance/decline, new highs/lows and % above SMA50/SMA200 from the Finviz homepage market-stats panel (Fri 2026-10-09)
- Internal desk cross-references (2026-10-11 Grid A/B/C and calendar updates), used for every news item on this page; none was re-sourced by this run: wiki/economic-calendar.md (ISM services prices paid, trade deficit, 10Y and 30Y auctions, FOMC minutes, Waller, claims, UMich, Hormuz flows, Gulf hurricane, OpenAI/Broadcom, CPI consensus, Columbus Day bond closure), wiki/semiconductors.md (SMH), wiki/utilities.md (nuclear PPAs), wiki/energy.md (Hormuz), wiki/materials.md (copper, Shanghai). Sector closes on this page equal facts.json.
- GitHub issues cross-referenced this run: #113, #115, #118, #127, #156, #158, #159, #160. **One new issue opened this run** for the strict-criterion XLP correlation flip (positive → negative), cross-referenced to #118.

---

*Last updated by Saturday Research Crew: 2026-10-12 (single-agent run, late: scheduled Sat 2026-10-10 19:39 ET, ran Mon 2026-10-12 ~00:15 ET; all market data as of Fri 2026-10-09 closes; macro/facts.json regenerated from the same fetch; breadth and put/call live from S&P 500 constituents / Finviz / CBOE; FRED series live via a second network path after the runner's connection timed out; WTI and gold from the committed feed with contract months)*
*Next update: Every Saturday 7:39 PM ET*
*Data sources: Yahoo Finance (yfinance), data/market_state.json (feed), CBOE, FRED, Finviz, Federal Reserve*
