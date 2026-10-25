# Weekly Council Synthesis — Week Ending Friday, October 23, 2026

> ⚠️ **DATA FRESHNESS (STEP 0, checked first). ALL 15 WIKIS ARE FRESH. THE TRUTH LAYER IS 0 DAYS OLD. THIS JOB RAN ABOUT 21 HOURS LATE, AND SO DID EVERY JOB UPSTREAM OF IT.**
>
> - **Wiki stamps:** the eleven sector pages (Grid A: tech, financials, healthcare, industrials; Grid B: consumer-discretionary, consumer-staples, materials, real-estate; Grid C: utilities, energy, communication-services) are stamped **2026-10-23** (Friday-evening runs covering the week ended Fri Oct 23). Semiconductors, economic-calendar, earnings-surveillance and canary-watch are stamped **2026-10-25**. **No wiki is older than 7 days. No wiki is stale.** The Monday Watchlist carries no staleness caveat.
> - **Schedule failure, logged and not papered over.** This job is scheduled Saturday 20:26 ET. Its first session began Sunday 2026-10-25 ~09:20 ET (START line in `logs/cron.log`) and the writing ran Sunday afternoon, after the upstream jobs finished: Semis + Calendar END and Earnings Surveillance END landed ~17:10 ET Sunday, Canary Watch END at 09:20 ET Sunday. All upstream END lines were in the log before this file was written.
> - **The data feed was late too, and recovered.** At this job's START, `data/market_state.json` was still `as_of` **2026-10-16** (the Universe & Data Feed Builder logged START Saturday 09:24 with no END). It committed at **17:04 ET Sunday** (`as_of` **2026-10-23**, commit 842a5ab; END SUCCESS fbcb4bc). The README Index Check uses it; no escalation issue was needed. **Side effect:** `macro/facts.json` (generated 2026-10-25 09:16 ET, commit 262e30b, `truth_check` 26 ok / 0 warn / 0 fail / 2 skip) was built *before* the feed rolled, so it carries **WTI $101.41 (CLX26) and gold $4,159.50 (GCV26) as of 2026-10-16, flagged `stale: true`**. Per the truth-layer rule those are the canonical values on this page; the feed's newer settlements (Dec WTI **$103.27**, gold **$3,991.10**) are shown beside them, labelled, and reconciled in Section 7.A.
> - `macro/facts.json` is **not older than 8 days**, so the "Canary missed its facts step" warning does not apply. Canonical values used on this page: 10Y **4.988%**, 5Y **4.805%**, 2Y **4.65%** (FRED DGS2, Thu Oct 22), 3M bill **4.032%** (^IRX), 10Y–2Y **+34 bps**, 10Y–3M **+96 bps**, VIX **19.45**, SPY **$759.97**, DXY **101.81**, EUR/USD 1.1204, USD/JPY 156.814, copper **$6.5075**, BTC **$81,074**, HYG **$77.05**, LQD **$103.85**, WTI **$101.41 (stale)**, gold **$4,159.50 (stale)**, fed funds **3.75–4.00%**, stance **Hike**. **All twelve sector-ETF closes and week-over-week changes in facts.json equal the figures on their sector pages (twelve of twelve).**
> - **The disagreement that matters most, resolved in Section 7.A:** the eleven Grid pages restate a Treasury-par curve (10Y 5.00%, 2Y 4.69%, 3M 4.22%, 2s10s **+31**) and Friday-evening futures quotes; facts.json has 10Y 4.988%, 2Y 4.65% and 2s10s **+34**. The financials desk's "+30 bp line, one more week and it breaks" is three points further from breaking on the canonical numbers.

---

## 1. CECIL'S SYNTHESIS — Fundamentalist Lens

**The quarter beat almost everywhere and the market sold the beats. That is the week, and it is the week a value investor waits for.** Earnings Surveillance counts it: seven of eight tracked reporters beat on an operating basis and six fell on the day. Outside the tracked list it was the same — **AXP** +20% surprise, -3.7%; **ELV** +48%, -1.4%; **RTX** +27%, +0.6%; **NOK** +44%, -14.8%; **BE** +36%, -11.2%. Inside the sector pages: **Lam Research** printed a record $8.22B quarter with a 40.2% operating margin and fell 12.8%; **GE Aerospace** beat, raised to $8.00–8.10 and fell 9.0%; **Valero** earned $23.90 and fell 5.7%; **CBRE** beat and closed at a 52-week low; **Chubb** printed a record and fell 1.3%; **Thermo Fisher** beat, the Street raised its target 9% to $750.92, and the stock fell 2.3%. Cecil's rule — "forward line over EPS line" — explains most of them (Netflix's Q4 guide, GM's narrowed range, GE's free cash flow, Lam's $300–400M supply slip). It does not explain TMO or CBRE, and those are the ones he is buying or studying.

**He opened four positions this week, all in names the tape punished on good numbers.** **LRCX** at $230.10, 18.9x forward with a 58% gap to its cut target, sized at a third "because I was wrong about MU for the same reason two weeks ago." **GE** at $285.64, 30.8x, small: "the market is pricing a cash problem from one quarter." **TMUS** at $146.54, 10.2x with 62% to target, a starter into its Oct 28 print, after a 7.9% fall "on a report about towers SpaceX does not yet own." **TMO**, a little. He holds **CAT** ($687.00, 21.1x, 38% gap, -14% in two weeks: "I have been early twice and I do not add"), **VST** ($140.16 from $152.02: "the stock is trading Meta's budget, not Vistra's contracts"), **MU** (4.2x forward), **Netflix** (17.5x, "I was wrong about the floor"), **O** ($56.89 from $56.08), **PPG** (back above his $107.50 basis), **MPC** (holds his $454.51 trim line by $2.71). **MSFT at 22.1x is still the core add into Wednesday.**

**The carry gaps narrowed for a third week.** Against the 10-year at **4.988%**: utilities' 3.07% sits **192 bps** under (from 203), real estate's 3.53% **146 bps** under (from 157), staples' 2.73% **226 bps** under (from 237). The yields that clear the Treasury: **UVV 8.4%** (+341 bps, at 52-week lows — a broken chart), **GIS 6.9%** (+191, "still a no"), **VZ 6.3%** (+131, held from $41.65, +7.2%), **EIX 6.1%** (+111), **MO 5.8%** and **CMCSA 5.8%** (+81), **O 5.7%** (+71), **AVA 5.2%** (+21, "the cheapest yield on the list for the same reason"). AT&T's 4.9% now equals the 10-year after an 11% fall, and he still passes.

**Value against traps.** Value he can name: **BAC** at 9.7x with a 24.5% gap at a May low and RSI 26 ("I watch it daily; I wait for a clean quarter"); **AXP** at 15.5x after a raise and a 5% job cut ("the one I would add on Friday's fall"); **BKNG** at 12.6x with 49% to target ("early three weeks running; I size it small"); **PLD** a starter if $123.43 holds; **SLB** at its 50-day ($52.40), not after a 7% day; **SYY** 15.2x and **STZ** 11.5x on the staples list; **CRH** 13.4x with a 45% gap. Traps: **GM at 5.1x** ("management would not raise after a beat; that is information about margins"), **NEM at 10.8x** (raised cost guidance in a week gold fell 4%; restricted by #115), **ALB 8.7x**, **KALU** (missed by 50 cents, -26.7%). What got expensive is the shelter: **ED 7% over its target, TRV 6% over, AMGN 9.7% over, XOM over, CVX and COP at target, KO/MO/KVUE at or above, LMT within 5%.** He trims ED and does not chase LMT.

**Credit, the line he set before the print.** HY–IG printed **251 bps** on Thursday (Canary, FRED), HY OAS **340**, a cycle peak, CCC **1,340**. "I set the rule before the print and I am not moving it after": his recommendation for Monday is **Council high-yield exposure to zero until the spread prints back under 240**. Own the duration, not the credit.

---

## 2. MARKY'S SYNTHESIS — Technician Lens

**The index fell a second week; the average stock rose a third.** SPY **-0.43% to $759.97**, still under its 50-day ($767.81). QQQ -0.8%, DIA +0.4%, IWM **+2.0%** (feed). Canary's constituent count is the best breadth this board has measured live: **58.0%** of S&P members above their 50-day (45.0% last week, 25.5% a month ago), 55.8% above the 200-day, **42 new highs on Thursday — the day SOX fell 6.7%**. RSP +1.14% against SPY -0.43%, a third week ahead. Outside the S&P it is still red (33.7% above the 50-day, new lows 443 against 147 highs). "That is a market rotating, not one breaking."

**Four lines were tested this week. Two failed, two held.**
- **XLI broke.** The $166.18 line held four closes and gave way Friday: **$164.62**, lowest close since Apr 7, a sixth weekly close under the 200-day, and the 50-day ($172.00) crossed under the 200-day ($172.41). Stop fired; Marky is out.
- **XLC broke.** Wednesday's $108.97 on Netflix's print went through the $109.66 floor on the week's heaviest volume; Thursday and Friday were trend days, Friday closing on its low at **$105.51**, 48 cents over the 52-week closing low. Short from $108.97; cover a third at $105.03.
- **SMH held — for now.** Thursday's -5.99% (15.3M shares, the only distribution day) went through last week's $539 line onto the July shelf; the low **$520.53** held $518.25 and Friday bounced on half the volume. **$527.20, 2.3% above a 200-day ($515.44) not tested since spring.** "A pause, not a bottom." He buys a test of $515 that holds on a close.
- **XLV held.** Monday closed $175.65, under the $176.60 line, and Tuesday took it back; Thursday made a two-year closing high ($181.30) on the heaviest volume. He kept the line and added a condition: two closes under $176.60, or one under $175.27.

**The pattern under all four: Friday failures at moving averages.** XLY's long fired Tuesday at $115.50, sat on the 200-day Wednesday and was gone Friday ($113.10, 21 cents under the 50-day) — a second Friday failure in two weeks. XLRE gapped to $43.21 on the SpaceX tower report and closed $42.57, **13 cents under its 200-day for a sixth week**. XLF closed over its 50-day once (Thursday $56.65; the add fired) and slipped eight cents under it Friday on AXP. XLP closed on its high Thursday ($89.99, a new 52-week closing high) and faded 1.9% Friday on 19.9M shares. XLK failed under its 50-day a second time ($189.11 vs $189.53) and closed Thursday under his $182.82 line.

**Breadth by the Grid's own count: eight up, one flat, three down.** Above the 50-day: **five of twelve** (XLE, XLV, XLP, XLB, XLU) — XLB regained it; Canary agrees exactly. Above the 200-day: **seven of twelve** (XLK, SMH, XLF, XLE, XLV, XLP, XLB), unchanged. Below: XLC, XLI (sixth week), XLU (thirteenth), XLRE (sixth, by 13 cents), XLY.

**Correlations kept breaking.** Canary's 30-day matrix: **XLV flipped negative** (+0.059 → **-0.071**, issue #177); XLU **0.024** is next; XLRE fell 29 points to 0.111. Three sectors now trade against the index (XLP -0.371, XLE -0.263, XLV -0.071) and two near zero, while the growth bloc tightened (XLK 0.836, SMH 0.765, XLY 0.727, XLI rising to 0.603). The volatility structure did not relax with the close: **VIX 19.45** but 20.31 and 20.66 intraday, **VIX/VIX3M 0.950**, **VVIX 109.70**, equity put/call 0.69 Thursday. Gold fell 4% with real yields down 10 bps — "a deleveraging signature for a second week."

**His rule for the book.** If VIX closes above 20 with VIX/VIX3M above 1.00, he hedges the book, not a sector. Until then, "the equal-weight index is the trade, not the cap-weight one." Seven of his twelve sector stops are live; none is new-long except XLB's add.

---

## 3. OPHELIA'S SYNTHESIS — Macro Lens

**The rotation is three weeks old and has a new motive: the market is punishing spending, not just fearing it.** Eight of twelve sectors beat SPY. Energy led (+1.60%, a 52-week closing high on Hormuz), then healthcare (+1.45%), real estate (+0.97%), utilities (+0.83%), materials (+0.77%), staples (+0.73%), financials (+0.68%) and discretionary (+0.57%). The losers were the AI-spending bloc: **XLC -4.36%** (Meta -9.4%, Netflix -6.6%, AT&T -10.7%), **SMH -2.33%**, **XLI -1.87%** (GEV -11.5%, GE -9.0%, CAT -6.0%). Over a month the board is split 23 points wide: XLE +11.69, XLU +9.07, XLP +8.97 points ahead of SPY; SMH -11.27, XLC -6.50, XLK -4.96 behind.

**The new read is Meta.** Last week every desk said Meta's capex guide was the answer. It held its budget — 2026 capex narrowed to **$135–145B**, the low end raised — beat on revenue by $1.3B, and fell 9.4%, because its Q3 capex ($34.9B) outran operating cash flow for the first time since 2012 and free cash flow went to -$2.1B. The buyer said yes and the market said "show me the cash." The suppliers (LRCX, KLAC, AMAT, ASML), the power names (GEV, VST, CEG, ETN, PRIM, BE) and the neoclouds (CoreWeave -11.6%, CDS at a record 1,194.5 bps) all fell the same Thursday. Her utilities desk calls it the new regime: "spending itself is being sold."

**The macro cross-current is unchanged and sharper: hot data, a growth-scare bond rally.** The Economic Calendar's week: claims **194K** (a sixth week under 200K), flash PMI composite **57.6** with manufacturing at a **53-month high** and output prices the **fastest since August 2022**, UMich **48.0** above every estimate, China **4.5%**. Housing broke: starts **1.221M** (1.30M expected), single-family permits the lowest since March 2023, NAHB **29**. And yet the 10-year fell **11 bps to 4.988%**, its first weekly close under 5.00% in five weeks — **19 bps of it on Thursday, the SOX -6.7% day**. The breakeven barely moved (2.34%), so it was real yield again. October hike odds drifted to ~10% in the blackout; **December stays ~84%**. The 20-year auction cleared at a record **5.469%** with a 0.9 bp tail — soft, not failed. Her calendar desk's verdict: "I side with the data."

**Oil is one close from firing the flag.** The November contract expired at a premium; **December WTI settled $103.27** Friday on unverified IRGC tanker-and-mine claims near Hormuz (#175), its first settle above $100; Brent's December contract reached a war high near $117 intraday. Kpler had flows at ~14 mb/d, 82% of pre-war, *better* than last week. The U.S. barrel moved ~$4.40 like-for-like and the Gulf barrel ~$7: "the risk is to Gulf supply, not U.S. tightness." GM named energy and logistics costs when it would not raise; PG warned of rising costs. **The dollar was flat at 101.81**, so the commodity restriction (#115) stays on.

**Where she contradicts herself, and says so.** On real estate she called the rate turn "a trend" and allowed new duration in the yield names in normal size; on utilities she is "constructive" and 9 bps from her 4.90% condition; on the calendar and Canary pages she says "stay in short paper; do not extend duration into the FOMC and PCE" and holds 25–30% cash. On financials she is "neutral" with credit unread; on Canary, credit crossed its trigger. Section 7.B lays it out; an issue is filed. **Net posture:** hold the reduced exposure and the hedges through Wednesday night, keep energy and pricing-power staples, keep IG duration already added but do not extend it, high yield to zero on Cecil's rule, and no AI-chain adds until Microsoft and Alphabet show capex *and* cash flow.

---

## 4. CONSENSUS SYNTHESIS

**Where all three agree.**

1. **Nothing in the AI chain gets added before Wednesday evening.** FOMC at 2:00 PM, Microsoft and Alphabet after the close, Amazon and Intel Thursday. Ophelia: "no adds before Wednesday." Marky: flat in XLK and XLI, buys only a held test of SMH's $515. Cecil: "I want Microsoft and Alphabet to repeat Meta's budget before I add" — though he has already started LRCX and GE small.
2. **Good news is being sold, so size every print small.** Every desk names the same tell: Lam, GE, Valero, AXP, CBRE, Meta, AT&T, Chubb, TMO all beat and fell. The beats that were paid (LMT +9.4%, PG +5.6%, DOW +9.0%, CUBI +13.1%, CLF +16.3%, SLB +7.1%) had a clean revenue line or a hard asset behind them.
3. **The defensive bid has a print behind it now, and it is still crowded.** PG's volume-led quarter, ISRG and DHR, ELV's raise and NEE's beat gave the shelter trade fundamentals. But ED, AMGN, TRV, KO, MO and XOM are at or over their targets, XLP faded 1.9% from its high, and nobody adds to overbought shelter.
4. **Oil above $100 is an inflation input into Thursday's PCE.** All three keep energy, none add above $69 on an unverified headline.
5. **Keep the hedges through Wednesday.** VIX 19.45 is cheaper than last week, VVIX 110 and VIX/VIX3M 0.950 say the cushion is thin.

**Where they disagree.**

- **Buying the punished beats.** Cecil starts LRCX, GE, TMUS and TMO into a falling tape; Marky's stops fired in XLI and he is short XLC; Ophelia moved platforms and telecom to underweight on the same names.
- **Duration.** The real-estate and utilities desks allow it; the calendar and Canary desks forbid extending it before PCE. Cecil owns O and wants IG duration; Marky trades XLRE and XLU with stops.
- **Breadth versus credit.** Marky "believes the breadth anyway"; Cecil sees HY–IG through 250 and CCC at 1,340. Canary's own line: "breadth healed and credit broke — those two do not usually last together."

**The single biggest risk: a hawkish 19 hours.** Wednesday 2:00 PM to Thursday 8:30 AM: an FOMC hold with explicit December language, Microsoft or Alphabet sold on capex the way Meta was, then core PCE at +0.4% M/M. The bond rally that cushioned three weeks of chip selling is equity-stress money 1.2 bps under 5.00%; if rates and AI funding hit the sector the same day, SMH loses its 200-day ($515.44) for the first time this year, the HY–IG trigger confirms on a second print, and the crowded shelter trade becomes the place to raise cash.

**The single biggest opportunity: a hyperscaler that shows the cash.** If Microsoft or Alphabet holds capex *and* shows cash flow covering it, the "who pays" question gets its first answer on an oversold complex: LRCX and KLAC at RSI 24–25, SMH 2.3% over its 200-day, GOOGL already 6% lower without reporting, CAT and GEV at multi-month lows into their own prints the next morning. Marky's map is $548.46, then $556.70–558.84 on SMH; Cecil's list is MSFT, TSM, MU, then LRCX and KLAC.

---

## 5. MONDAY WATCHLIST

*All 15 wikis fresh; levels are Friday Oct 23 closes. Macro levels equal macro/facts.json; index levels are data/market_state.json (as_of 2026-10-23). WTI and gold in facts.json are stale (Oct 16); the December contract settlement is shown as the live line, labelled. Arena: the week of Oct 26 is open on #174.*

**Macro gates (these outrank every ticker line below):**

| Gate | Level now | Trigger | Action |
|---|---|---|---|
| **December WTI settle (Mon)** | facts.json $101.41 (CLX26, stale); **Dec CLZ26 $103.27** | Second Dec settle **> $100** / **< $97** | Above: the oil flag fires (three flags before the FOMC). Below: Friday was a headline spike |
| **HY credit (Fri Oct 23 print posts Mon)** | HY–IG **251 bps**, HY OAS 340, CCC 1,340 (Thu) | Second print **≥ 250** | Trigger confirmed: Council high yield to zero until < 240 (Cecil's rule) |
| **Durables + Conference Board (Tue)** | Confidence 81.9 (Sep); cons 80.5 | Confidence **< 78**; durables ex-transport < -0.5% | Consumer at a new cycle low / business capex rolling over |
| **FOMC (Wed 2:00 PM) + MSFT/GOOGL (AMC)** | Fed 3.75–4.00%; Oct hike ~10%, Dec ~84% | Explicit December language; hyperscaler sold on capex | Hold + "further firming": 10Y back over 5.00%, take duration adds off. Capex sold: SMH tests $515.44 |
| **Q3 GDP + September PCE (Thu 8:30 AM)** | Core PCE cons +0.3% M/M, 3.1% Y/Y; GDP cons 3.2% | Core **≥ +0.4%** or **≥ 3.2% Y/Y** | Hawkish re-acceleration; December locked |
| **10Y** | **4.988%** | Weekly close back over **5.00%** / under **4.90%** | Over: the flag returns. Under 4.90%: Ophelia's utilities condition met |
| **VIX** | **19.45**; VIX/VIX3M 0.950; VVIX 109.70 | Close **> 20** with VIX/VIX3M **> 1.00**; 25 alarm | Hedge the book, not a sector |
| **DXY** | **101.81** | Weekly settle < 99 | The only thing that lifts the commodity restriction (#115) |

**Tickers, levels, triggers, stops:**

| Ticker | Close | Trigger | Stop / invalidation |
|---|---|---|---|
| **SMH** | $527.20 | Buy a test of the **200D $515.44** that holds on a close; reclaim **$548.46**, then $556.70–558.84 | Close under **$515** → $504.22 (Jul 29 close) |
| **XLK** | $183.23 | Close over the **50D $189.53** | Close under **$181.50** → $172.50 → 200D $168.19 |
| **XLC** | $105.51 | Short from $108.97; **cover a third at $105.03**; do not carry the full short into GOOGL (Wed) | Close over **$109.66** |
| **XLY** | $113.10 | Long over **$116.22**; AMZN Thu is the gate | Short under **$111.97** → $110.67 → $109.41 |
| **XLF** | $55.90 | Breakout confirmed over **$56.67**; V Tue, MA Thu | Under **$55.03** second add off; under $54.46 first; **$52.81** stop |
| **XLI** | $164.62 | Flat; back in over **$168.89** on a close; GEV Wed, CAT Thu | Low $160s on follow-through |
| **XLB** | $51.31 | Long; add over **$51.71**, target $53.42; FCX/SHW/PPG Tue, LIN Thu | Close under the **200D $50.62** |
| **XLE** | $69.33 | Hold; no add above $69; **$68.24** must hold on the first dip; XOM/CVX Fri, OPEC+ Sun | Weekly close under **$65.54** |
| **XLV** | $179.28 | Next leg over **$181.30**; LLY/MRK/BMY/GILD Thu, ABBV/REGN Fri | Two closes under **$176.60**, or one under **$175.27** |
| **XLU** | $42.56 | Take a third off in **$42.42–42.77**; rest targets the **200D $43.77** | Close under **$41.28** |
| **XLP** | $88.26 | Rebuy the trimmed half on a weekly close over **$89.99**; KO Tue | Under **$87.11** tighten to it; stop **$86.06** |
| **XLRE** | $42.57 | Rebuy the half on a **weekly close over $42.70**; WELL/PSA Mon, AMT Tue, EQIX Wed, DLR Thu | Close under the **20D $41.52** |
| **MSFT** | $524.51 | Cecil's core add; reports Wed AMC, straddle ±5.3% vs ±7.0% realized | — |
| **LRCX / GE** | $230.10 / $285.64 | Cecil's new starters (a third / small) | LRCX at its lowest since Apr 6; GE RSI 25.9 |
| **TMUS / VZ** | $146.54 / $44.66 | TMUS starter into Wed's print; VZ reports Mon BMO | TMUS at a two-year low; a SpaceX confirmation |
| **CAT / GEV** | $687.00 / $815.00 | CAT held into Thu's print (no add); GEV Wed | — |
| **VST / CEG** | $140.16 / $253.45 | VST held (Nov 6); CEG waits for Nov 9 | 52W closing lows $134.30 / $236.14 |
| **TMO / UNH** | $673.82 / $418.09 | Cecil adds a little to TMO; UNH the widest gap he owns | — |
| **O / PLD** | $56.89 / $126.45 | O held from $56.08; PLD starter if **$123.43** holds | A hawkish FOMC / hot PCE |
| **SLB / MPC** | $53.06 / $457.22 | SLB on a pullback to the **50D $52.40**; MPC held | MPC weekly close under **$454.51** |
| **AXP / BAC** | $313.22 / $50.56 | AXP Cecil's add; BAC daily watch at a May low | — |
| **FCX / NEM** | $65.18 / $108.87 | Watch only (restriction #115); FCX reports Tue | — |

**Council book (provisional, Monday Oct 19 opens to Friday Oct 23 closes from `portfolio/current.yaml` and `data/weekly/2026-10-23.json`; the official close is Monday's tracker run):** VICI $23.48 → $23.76 (+1.2%), MNST $45.42 → $46.19 (+1.7%), COST $986.00 → $1,003.32 (+1.8%), BIIB $231.81 → $250.69 (**+8.1%**), AES $14.95 → $15.00 (+0.3%). Weighted at 83.7% invested, about **+2.1%** for the book against SPY **-0.95%** open-to-close (alpha about **+3.1 pts**), the book's first clearly positive week in three. **No exit-shadow stop is near** (all five are above entry; CORE -5%, AES SPEC -8%). VICI and BIIB report inside the window (Oct 28). BIIB's +8.1% has no cause on the healthcare page. Three of the five booked names still appear in no sector wiki.

---

## 6. CROSS-SECTOR CONNECTIONS — The Hidden Wires

**Wire 1 — The AI financing chain, one Thursday.** Meta holds its 2026 budget but its Q3 capex passes operating cash flow and FCF goes to -$2.1B (communication services) → META -7.0% Thursday, GOOGL -6.0% on the week without reporting → Lam's $300–400M supply slip the same night, and **SOX -6.72%, all 30 members down** (semis) → LRCX -12.8%, KLAC -12.2%, AMAT -7.8%; ICHR -9.9% on the bench → **GEV -10.6%, PH -6.8%, ETN -6.3%, CAT -4.9%** that day, PRIM -11.2% on the week (industrials) → **VST -9.8%, CEG -5.7%** that day, CEG at its lowest since Jul 20 (utilities) → **EQIX and DLR at their lowest since March and February** (real estate) → BE -11.2% on a 36% beat (earnings) → CoreWeave -11.6%, CDS at a record → **HY–IG 251, CCC 1,340, EM +10 bps — on Thursday** (Canary). Every node beat or had no news. The buyer was graded on cash, and the grade travelled down the chain into credit.

**Wire 2 — The rate chain, borrowed from Wire 1.** The same Thursday the 10-year fell **19 bps**, all real yield (breakeven 2.34%) → first weekly close under 5.00% in five weeks (4.988%) → Freddie's 30-year finally moves, 7.40% → **7.32%** → HD +3.3% and LOW +1.3% close over their 50-days, VMC/MLM/CRH +1.3–1.6%, PSA +3.9%, SPG +3.0%, O +1.4%, ED a 52-week closing high, XLP +3.3% that day → carry gaps narrow a third week (XLU -192, XLRE -146, XLP -226) → and then the wire breaks twice: XLRE fails its 200-day by 13 cents, and housing itself broke (starts 1.221M, NAHB 29). The proxies trade the bond; the borrower is still stuck. On the financials page the flatter curve keeps the money-center banks falling (C -2.9%, JPM -2.4%, BAC at a May low) while the regionals rally.

**Wire 3 — The geopolitical energy → inflation → Fed loop.** IRGC tanker and mine claims (unverified) → Brent December +~$7, December WTI **$103.27**, its first settle over $100 (energy, calendar) → producers to 52-week highs (XOM, CVX, COP, EOG) while the refiners sell on Valero's $23.90 beat as the gasoline crack narrows ~$5 → GM narrows its guide naming energy and logistics costs (-9.6%), PG warns of rising costs, CSX's record revenue is half fuel surcharge, WFRD +7.8% → the flash PMI's output prices are the fastest since August 2022 → core PCE Thursday, December ~84% → back to Wire 2: one hot print takes the bond rally away. Energy's correlation to SPY is -0.263: still the book's hedge.

**Wire 4 — The SpaceX wire: one private company, three sectors.** SpaceX's first public-company profit (+161% surprise, +7.8%; earnings) → Bloomberg's Friday report of talks for ~80,000 tower sites → **AT&T -8.0%, TMUS -7.7%** that day, TMUS at a two-year low (communication services) → **CCI opens +15.5%, closes +9.1%; AMT +4.1%**, and the tower gap decides XLRE's week high and its 200-day failure (real estate) → Tesla-combination talk unconfirmed, and **TSLA's +4.9% is ~0.9 points of XLY's +0.57%** (discretionary). Nothing is signed. VZ (Mon), AMT (Tue) and TMUS (Wed) are the first three calls to answer it.

**Wire 5 — The consumer split.** The pump and the guide: GM -9.6%, F -6.7% to a May low; AMZN -4.6% Thursday with no sourced cause; BKNG at a May low; DASH -5.2% → but the trade-down and staples names were paid: PG's volume +2.4, KR +4.9%, STZ +5.6% → the labor tape is still firm (claims 194K) and sentiment beat (UMich 48.0) → AXP beat and cut 5% of jobs; Netflix cut its own ad forecast. The Conference Board (Tue) and AMZN/SBUX (Thu) close the triangle.

**Wire 6 — The dollar, metals and gold.** DXY flat at 101.81 keeps #115 on → copper under the $6.60 rail ($6.5075) → NEM -8.2% (cost guide raised), FCX -6.3% (one unexplained Thursday), KALU -26.7%, CENX -10.3% → yet XLB +0.77% on Dow's beat and the gases → gold's spot month **under $4,000** (feed $3,991.10) in a week real yields fell. A flat dollar, falling metals and falling gold together is the second deleveraging week in a row.

---

## 7. SECTOR CONTRADICTIONS — Where the Wikis Disagree

### A. Truth Layer — facts.json against the pages (facts.json wins on this page)

| Item | facts.json (canonical) | What the pages say | Resolution |
|---|---|---|---|
| **10Y** | **4.988%** (^TNX, Fri) | Tech, financials, healthcare, industrials: **5.00%** (Treasury par, Fri); others 4.99%; feed 4.99 | Basis difference (par vs ^TNX). The Grid A pages' "5.00%" reads as *not* under 5% on a weekly close; on the canonical number it is under by 1.2 bps |
| **2Y** | **4.65%** (FRED DGS2, Thu Oct 22) | Grid A pages: 4.69% (par Fri); feed: 4.69% | Day and basis. facts.json pairs Fri 10Y with Thu 2Y |
| **10Y–2Y** | **+34 bps** | Grid A: **+31**; feed `curve_2s10s_bps`: **+30** | **The financials desk's "+30 bp line, one more week and it breaks" is 4 bps from breaking on canonical numbers, not 1** |
| **3M / 10Y–3M** | **4.032%** (^IRX, discount) / **+96** | Grid A: 4.22% (CMT) / +78 | Discount vs constant-maturity basis (~20 bps); Canary documents it |
| **WTI** | **$101.41 (CLX26, as_of 10-16, `stale: true`)** | Nine pages: $103.44 (CL=F Fri evening); semis/calendar/Canary/feed: **$103.27 (CLZ26 settle)** | facts.json was generated (09:16 ET) before the feed rolled (17:04 ET). The canonical value is last week's expired contract. **Live line on this page: Dec $103.27, labelled.** Canary's next run must regenerate facts.json from the rolled feed |
| **Gold** | **$4,159.50 (GCV26, 10-16, stale)** | Pages: $4,010 (GC=F Fri evening); feed: **$3,991.10** (GCV26 settle) | Same cause. Directional: under $4,000 on the spot month, -4.0% |
| **DXY** | **101.81** | Eight pages: 101.75 (Fri evening) | Settle vs evening quote; immaterial, both above 101 |
| **Fed odds** | Oct hike **~10%**, Dec **~84%** (CME, via calendar) | Grid A: Oct ~7–8%, Dec "near 80% on one account"; Grid C: Oct ~7%, Dec 71–78%; staples/RE/discretionary/materials: "not re-sourced" | Source and date spread; facts.json used |
| **Credit** | (Canary) HY OAS 340, HY–IG 251 | Financials: "not re-sourced; last reading HY 3.25%" | **The financials page's credit line is a week old and missed the trigger.** Its "HY under 3.00%" condition is 40 bps away |
| **Correlations** | Canary 30-day: XLU 0.024, XLV -0.071, XLC 0.440 | Feed `corr_spy_4w`: XLU **0.529**, XLV -0.168, XLC **0.015** | Different windows and conventions; XLU's sign of "decoupling" depends entirely on which one you read. Canary's matrix is the board's convention |
| **1Y returns** | Feed `d52w`: XLK +25.3%, XLE +61.0%, XLC -7.9% | Pages: XLK +29.0%, XLE +60.3%, XLC -7.3% | Window/adjustment basis; the README scorecard uses the feed |
| Sector ETF closes and W/W | 12 of 12 | 12 of 12 match | — |

### B. Same factor, opposite reads

1. **The 10-year under 5%: buy duration or don't.** Real estate: "the rate turn is a trend… new duration is allowed in the yield names in normal size." Utilities: "constructive, unchanged," 4.90% is 9 bps away. Calendar: "stay in short paper; **do not extend duration** into the FOMC and PCE." Canary: "I am not extending duration into Wednesday and Thursday." Staples: add only on a pullback. **All five are Ophelia.** The same split was filed last week (#173) and widened, because two desks upgraded on a rally the other two call borrowed from the chip selloff.
2. **Meta's capex: a raise, a hold, or a cash problem?** Tech and utilities: Meta "raised its capex forecast" and the market "punished spending." Semis and calendar: capex "narrowed" with the low end up — "the buyer held its budget," the "raise" branch "nominally hit." Communication services: capex passed operating cash flow and FCF went negative. Each read implies a different fix: a lower multiple on the whole chain (tech), a buy once MSFT/GOOGL repeat the budget (semis Cecil), or an underweight until cash covers capex (comm Ophelia).
3. **Breadth versus credit.** Canary's breadth trigger cleared yellow (58.0% above the 50-day) the same week its credit trigger crossed (HY–IG 251). Marky: "a market rotating, not breaking." Cecil: "high yield to zero." Financials, the sector most exposed to credit, could not read it and stayed neutral.
4. **Is the economy slowing?** Calendar: "hot economy, broken housing… I side with the data" (PMI manufacturing a 53-month high). Industrials: Philly Fed new orders collapsed to **4.3** — "a warning I note." Semis, utilities and tech read the 10-year's fall as growth risk. Two manufacturing surveys, opposite directions, one week.
5. **The SpaceX tower report.** Communication services: Ophelia moves telecom to underweight ("it goes straight at the main objection"), while Cecil on the same page buys a TMUS starter on it. Real estate: the towers rose 4–9% on it, and Cecil there "doesn't pay for talks." One headline, a bullish read on the landlords and a bearish read on the tenants, and the value desk on opposite sides of it on two pages.
6. **Energy's Friday.** Energy files a provisional geopolitical trigger (#175) but holds it "loosely" (flows *rose* to 14 mb/d; Trump called the claims fake). The calendar treats one more December settle over $100 as a regime flag. Discretionary and staples already price the cost line. If Monday's headline is denied, energy's trigger and the calendar's flag disagree about what happened.

### C. Counts, bases and dates the pages differ on

- **Apple's report date:** tech and earnings surveillance: **Nov 2** (Earnings Whispers confirmed); semis: "Oct 29 (one calendar; provisional)." Use Nov 2.
- **Q3 GDP / PCE:** financials says "next week, exact dates not confirmed"; calendar and semis: **Thu Oct 29, 8:30 AM**.
- **Lilly's consensus:** healthcare $6.67 (Yahoo, -18% in two weeks); earnings surveillance shows three bases ($6.67 / $7.11 EW / $5.70 Finviz) and a $8.71 whisper. The healthcare page's "why did it fall 18%?" and earnings' "unconfirmed" flag are the same open question.
- **FedEx Oct 28:** industrials lists FDX on a Yahoo date; it is not on the earnings-surveillance calendar. Treat as unverified.
- **Hike odds:** see 7.A — "~7%" and "~10%" in the same week from the same CME source family.
- **Weights:** every sector page says Yahoo's funds_data top-ten weights are identical for a **third week**; concentration figures (XLY's 41.1%, XLC's 43.1%) are approximate.

---

## 8. MACRO CALENDAR IMPACT — Hot Data, a Borrowed Rally, and 19 Hours That Decide It

**What this week's data did to the Council's posture.** It confirmed the inflation half of the regime and argued with the growth half. Claims **194K** (a sixth week under 200K), the flash PMI composite **57.6** with manufacturing at a 53-month high and output prices the fastest since August 2022, UMich **48.0** above every estimate, China **4.5%**. Housing broke where the Fed's hikes always work first: starts **1.221M**, single-family permits the lowest since March 2023, NAHB **29** (one point above the ≤ 28 break line). The bond market looked past all of it and rallied 11 bps on Thursday's chip selloff. **Regime, per the calendar desk: sticky inflation, a December hike, and a growth scare that comes from equity and credit stress rather than the economy.**

**Flags.** Two up — **NFP < 150K** (carried, +29K; next print Nov 6) and **CPI M/M > 0.3%** (carried; September +0.6% headline, +0.3% core). **The 10Y > 5.00% flag cleared** at 4.988%, on a growth scare, not falling inflation; the 10-year is still above the 4.75% stress line for a ninth week. **Oil > $100 sustained is one close from firing**: Dec WTI settled $103.27 once. If Monday settles above $100, it is a three-flag week again before the FOMC — and the flag that cleared was a market flag while the one about to fire feeds both inflation flags. Issue #179 carries the board.

**Next week's gauntlet and what each print does to the posture.**

| When | Event | Posture change if… |
|---|---|---|
| **Mon Oct 26** | No first-tier data; **Dec WTI settle**; VZ (BMO); Friday's OAS posts | WTI > $100: oil flag fires. HY–IG ≥ 250 again: high yield to zero is confirmed |
| **Tue Oct 27** | Durable goods (8:30), **Conference Board** (cons 80.5), Richmond Fed; BA, FCX, V, KO, SK Hynix | Confidence < 78 = new cycle low, consumer cracking; durables ex-transport < -0.5% = capex rolling over |
| **Wed Oct 28** | **FOMC 2:00 PM, Warsh 2:30 PM**; **MSFT, GOOGL** after the close; GEV, TMUS, EQIX, VICI, BIIB | Hold + December language: 10Y back over 5.00%, take the duration adds off. Hold + "data dependent": the growth-scare pivot. MSFT/GOOGL capex sold: SMH to $515 |
| **Thu Oct 29** | **Q3 GDP (cons 3.2%) + September PCE (core cons +0.3% / 3.1%)** 8:30 AM; claims; LLY, MRK, MA, CAT, LIN; **AMZN, INTC** after the close | Core ≥ +0.4% or ≥ 3.2%: December locked, bond rally reverses. GDP > 3.5%: the bond rally was wrong. GDP < 2.0%: the scare is real |
| **Fri Oct 30** | Daly, Musalem; XOM, CVX, ABBV; UMich and Conference Board already in | "December is likely" from either = odds > 90% |
| **Nov 1–6** | OPEC+ (Sun), ISM Mfg (Nov 2), AAPL (Nov 2), **midterms (Nov 3)**, refunding (Nov 4), AMD/QCOM, **October payrolls (Nov 6)** | The election and payrolls make the following week a second gauntlet |

**The Council's posture into it.** **Cash stays where the desks want it (25–30%) and where the owner caps the book (20%; the book is at 16.3%).** Short paper over long duration until PCE; IG duration kept, not extended; **high yield to zero on Cecil's rule if the spread confirms**. Hedges on through Wednesday night; they are cheaper with VIX at 19.45 than they were a week ago. Keep energy (Dec WTI $103.27) and pricing-power staples; cut housing-sensitive names (the 10-year rally reached mortgages by 8 bps and starts broke anyway). **AI-chain adds wait for the stocks to hold after Microsoft and Alphabet — not just the numbers.** Meta proved the numbers are not enough.

---

*Last updated by Saturday Research Crew: 2026-10-25 (Synthesis Agent, single-agent sequential run; scheduled Sat 2026-10-24 20:26 ET, ran Sun 2026-10-25 — START ~09:20 ET, written after the upstream END lines and the 17:04 ET feed commit; all market data as of Fri 2026-10-23 closes)*
*Inputs: all 15 wikis (stamps 2026-10-23 ×11, 2026-10-25 ×4), macro/facts.json (2026-10-25, 262e30b), data/market_state.json (as_of 2026-10-23, 842a5ab), data/weekly/2026-10-23.json, portfolio/current.yaml*
*Next update: Every Saturday 8:26 PM ET*
