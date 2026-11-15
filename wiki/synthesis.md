# Weekly Council Synthesis — Week Ending Friday, November 13, 2026

> ✅ **DATA FRESHNESS (STEP 0, checked first). ALL FIFTEEN WIKIS ARE FRESH AND THE TRUTH LAYER IS CURRENT. THIS JOB RAN ON SCHEDULE (Saturday 2026-11-14, ~20:29 ET).**
>
> - **Fresh, stamped 2026-11-13 (Friday-night runs, settled Friday bars):** tech, financials, healthcare, industrials (Grid A); consumer-discretionary, consumer-staples, materials, real-estate (Grid B); utilities, energy, communication-services (Grid C). **Fresh, stamped 2026-11-14:** semiconductors, economic-calendar, earnings-surveillance, canary-watch. `logs/cron.log` shows a START and an END for every upstream job this week. **No wiki is over the 7-day line. No stale page.**
> - **`macro/facts.json` generated 2026-11-14** (Canary Watch, commit e57f0b8), carrying the Fri Nov 13 closes. **WTI ($88.56, CLZ26) and gold ($3,879.70, GCX26) come from the feed (`data/market_state.json`, as_of 2026-11-13) and are not flagged stale.** One field is a day old by design: the **2Y (4.86%) is FRED's Thursday Nov 12 print**, so facts.json's **10Y–2Y +29** pairs Friday's 10Y with Thursday's 2Y. Every macro number below equals facts.json: 10Y **5.154%**, 5Y **4.981%**, 2Y **4.86%**, 3M **4.122%**, 10Y–3M **+103**, VIX **19.30**, SPY **$754.37**, DXY **103.41**, EUR/USD 1.105, USD/JPY 159.875, copper **$6.0795**, BTC **$68,249**, HYG **$76.94**, LQD **$102.81**, fed funds **3.75–4.00%**, stance **Hike**.
> - **What the sector pages could not see.** FRED timed out for the Friday-night grids, so tech and financials wrote "HY OAS not re-sourced; last read 3.48%" and kept Ophelia's "no adds until HY is back under 3.40%" gate shut. Canary fetched FRED through a second path on Saturday: **HY OAS 320 bps, HY–IG 231 bps (Thu Nov 12)**. The gate the Grid A desks were waiting on has already opened. Section 7 and the issue filed this run carry it.

---

## 1. CECIL'S SYNTHESIS — Fundamentalist Lens

**The numbers held and a person left.** Nothing in this week's prints said the AI buildout is short of money or orders. **Applied Materials** posted a record **$10.41B (+53%)** and guided FQ1 to **~$11.1B / $4.35** against ~$10.83B / $4.23; **CoreWeave** raised its 2026 forecast and rose **24.7%** in a day; **Constellation** earned **$5.06** against ~$3.89, raised 2026 to **$12.50–12.80** and took a conditional **$5B DOE** uprate loan; **Cisco** beat and raised its FY27 revenue to **$74.8–75.8B**. Then NVIDIA's founder resigned under allegations with a China-security angle, and the stock lost **12.75%** to **$162.85**, a 52-week closing low. Cecil's line on the tech page is the week: *"NVDA at 10.3x is cheaper than when I said I'd start it, and I'm not starting it. The estimate belongs to a CEO who's gone."* He waits for Kress's first guide on Tuesday.

**Where the value is.** **MSFT at 21.7x** fell 1.3% in an up week and he keeps adding. **NVDA at 20.6x trailing / 10.3x forward** is on the list after the print, not before. **TXN and ADI**, back over their 50-day, **AMAT** after its guide and **TSM** once it closes over its 200-day are the semis list. **BKNG at 13.0x** with a 35% gap; **SYY at 14.3x** (18% gap) and **STZ at 12.0x**; **SRE at 14.4x** (22% gap) first in utilities, then **NWN**; **DLR** 24% under its target before EQIX; **NUE 11.4x / STLD 10.6x**, still blocked by the dollar restriction; **CMCSA at 7.1x** and 5.3%; **ETN** after JPMorgan's target cut, waiting for a quarter that shows data-center orders converting.

**Traps, in his words.** **Costco at 44.2x**, +5.0% on no news and over its mean target: "a momentum trade, not a value one." **Berkshire at 26.0x**, a two-year high on operating earnings **-5.8%** and buybacks doubled to **$9.6B**: "I do not pay 26x and 5% over target to join it." **Tesla at 180.7x**, +8.9% "on a production line it is ending and a merger nobody has filed." **Corteva** at ~10x after a guidance cut on Brazil: "a falling knife." **Skydance**, with ~$87B of gross debt, stopping subscriber disclosure. **GIS at 7.3%**: "a dividend the market doesn't believe." Over target now: JNJ, AMGN, KO, MO, PEP, COST, WEC, ED, SPG, CB, TRV, PGR.

**His book, marked.** GE **+16%** from $285.64; LMT **+5.1%** on the third he started at $567.08; TMUS **+16.0%**, VZ **+11.3%**; CVS third **+6.6%**, UNH back to even, ELV **+2.3%**; DTE **+9.0%**; O **+5%**; PPG **+14%**; EOG **+5.2%**; LRCX third back to **-1.8%** (from -12.9%). Still red: VST **-12.5%** from $152.02 (held until Austin speaks to existing contracts), NFLX half **-12.6%**, SLB **-1.5%**.

**Dividend spreads that matter.** Against facts.json's **10Y 5.154%**: utilities' **2.79%** yield sits **-236 bps** under (from -207), staples' **2.46%** **-269 bps**, real estate's **3.34%** **-181 bps** (from -152). All three gaps widened about 29 bps in a week, and **all three funds rose anyway** (XLU +2.11%, XLP +2.52% to a 52-week closing high, XLRE +0.84%). That is the week's valuation puzzle: the bond proxies were bought as cash flows, not as bonds. Yields that still clear the 10-year: **UVV 8.8%**, **BRT 7.9%**, **CTO 7.5%**, **GIS 7.3%**, **SAFE 7.2%**, **GTY 7.1%**, **VZ 6.1%** (about **+95 bps**, from ~125), **EIX 5.9%**, **NOMD 5.8%**, **MO 5.7%**, **O 5.6%**, **CMCSA 5.3%**. SAFE closed at a two-year low and UVV at its lowest close in two years: yield is not the screen, the balance sheet under it is.

---

## 2. MARKY'S SYNTHESIS — Technician Lens

**Everything rose, and almost nothing confirmed.** SPY **+2.59% to $754.37**, ending a four-week losing streak; QQQ **+3.6%** to $679.89; DIA **+2.1%**; IWM **+1.4%**. VIX closed under 20 every day (**19.92 / 19.46 / 17.49 / 18.70 / 19.30**) and VIX/VIX3M went back to **0.936**, contango all week. **All twelve sector funds rose.** But the lines that matter mostly printed intraday and failed on the close.

**Breadth by the Grid's own count.** Up on the week: **12 of 12** (XLE +5.42%, SMH +4.91%, XLI +3.76%, XLC +3.72%, XLK +3.36%, XLF +2.66%, XLP +2.52%, XLV +2.19%, XLU +2.11%, XLY +2.04%, XLRE +0.84%, XLB +0.54%). **Above the 50-day: 8 of 12** on the sector pages' own levels (XLY, XLF, XLB, XLRE, XLV, XLU, XLP, and XLE by five cents), up from 7. **Above the 200-day: 8 of 12**, up from 7: **XLU** made its first Friday close over the 200-day since Jul 24, ending sixteen straight rejections. Below both: **XLK, SMH, XLC, XLI**.

**The near-misses, all four of them.**
- **XLK** closed over its 200-day Monday ($170.88) and Wednesday ($174.36) and finished **$0.26 under it** ($170.28 vs $170.54): "a whipsaw, not a reclaim." Small size, stop on a close under **$169.35**; add over **$174.36** on volume over 12.8M.
- **SMH** ran to **$516.65** Wednesday, **$7 under the 200-day ($523.89)**, and closed Friday at $486.75 after all ten top holdings fell. "Failed test from below, no trade, no loss." In over $523.89 on volume above 11.7M; under **$462.88** opens $443–446.
- **XLI** traded to **$171.60**, $1.17 under the 200-day ($172.80), a **ninth** straight Friday close below it, every day under average volume. Starter third on the 50-day closes, stop **$165.44**.
- **XLC** stopped at **$109.26** against a **$109.31** 50-day. The short is closed ($108.97 in; out at $105.03, $99.90, $107.36). A close over $109.31 buys a starter, stop $106.22.

Two more closed **on** their lines rather than over: **XLE $64.96** against Marky's $64.96/$64.97 rule (no fill) and **XLU $44.04** against a $44.09/$44.14 buy line (high $44.14, no close). **XLV** pushed to $190.66 Thursday and closed $187.83 under its $189.66 re-add line: a four-day flag on falling volume.

**What held and paid.** **XLP** closed on its high at **$92.35**, a 52-week closing high, six up weeks, full size, stop the 20-day **$89.48**. **XLF** six straight up weeks, 16 of 17 names up; warning moves up to the 20-day **$57.06**. **XLRE** absorbed a 29 bp 10-year move in an 80-cent range. **XLY** long from $118.16 is up $1.82, but closed lower four days running. **XLB** sat on its 20-day ($52.23).

**Correlations.** Canary's 30-day matrix has **all twelve sectors positive vs SPY** for the first time in weeks; XLE (0.026) and XLP (0.043) crossed back from negative, XLU is 0.072. And bonds stopped hedging: **TLT -3.10%, LQD -1.65%** in a +2.6% week for stocks. The one correlation that broke the textbook way: utilities, staples and real estate rose while the 10-year rose 29.5 bps. Inside the market, **RSP lagged SPY by 0.22 pts** for the first time in six weeks, and market-wide breadth (Finviz) stayed red: **40.0%** of stocks over their 50-day, **453 new lows vs 75 highs**, while the S&P's own read **71.3%** over the 50-day.

---

## 3. OPHELIA'S SYNTHESIS — Macro Lens

**The regime moved one notch hawkish and the equity market did not care.** October CPI ran **+0.4%** headline and **+0.3% core** against +0.3% / +0.2%, the third straight hot core (Tue Nov 10). PPI was cooler on the headline (+0.3% vs +0.4%) but its annual rate hit **6.5%**, the highest since 2022. December hike odds went from ~72–79% to **~88–89%** (CME FedWatch, per the calendar and semis pages), with a 9–14% tail for 50 bp; Waller said the Fed "ought to" hike; BofA now calls December **and** January. The bond market answered with a bear flattener led by the belly: **5Y +33 bps to 4.981%**, **10Y +29.5 bps to 5.154%** (over 5.00% Thursday for the first time since the flag cleared), the **2Y +40 bps to 4.86%** (FRED, Thursday). The 10Y breakeven barely moved (2.24%), so the whole 10-year move was **real yield, now ~2.91%**. The dollar made a **52-week closing high at 103.41**; USD/JPY is 159.875.

**The rotation story.** Last week money ran from AI and oil into media, real estate and staples on an election shock. This week **everything rose**, and the order reversed: the three that lagged last week (XLE, SMH, XLK) are three of the top five. But the month still belongs to the shelters: **XLV +8.84, XLP +8.80, XLF +8.43** points ahead of SPY over 21 sessions; **SMH -10.64, XLK -7.74** behind. Inside tech, the money did not leave AI, it left one company: NVDA -12.75% while **AMD +18.9%, AVGO +18.2%, MU +12.8%, LRCX +12.7%, AMAT +11.4%**. Utilities, staples and communication services each write that part of the chip money went to "steady cash flow." Both are true, and they are not the same trade.

**Cross-currents.** (1) **Rates vs proxies:** a 5.15% 10-year and a priced hike, and XLU broke over its 200-day, XLP made a high, XLRE made a sixth up week. (2) **Iran vs the barrel:** Trump posted the U.S. "does not need" a deal, the IRGC said two supertankers were stopped by explosions, and **December WTI still fell 2.5% to $88.56**, while XLE rose **5.42%** (#207). Energy's own read: "That is positioning, not fundamentals." (3) **Dollar vs metals:** DXY 103.41 → gold **-4.5%** to **$3,879.70**, under $4,000; silver about -6%; copper **$6.0795**, the lowest close of Canary's fetch; NEM -6.4%; the materials restriction stays ON. (4) **Credit vs duration:** spreads tightened every print (HY OAS **348 → 320**, HY–IG **255 → 231**), and IG bond prices fell anyway because rates did the damage.

**What the Economic Calendar revealed.** Its thesis was "sticky inflation, a December hike, and a financial-conditions growth scare." **The first two were confirmed in full; the third reversed.** VIX cleared its 22 flag on Monday's close and never came back, even through a CEO resignation at a top-three S&P company. The flags are still two, but the mix changed: **CPI MoM > 0.3% carried, 10Y > 5.00% raised; VIX > 22 cleared.** Four triggers hit: core CPI ≥ +0.3%, December > 85%, the 10-year back over 5.00%, and **existing home sales 3.75M** under the 3.85M line. Housing is the soft spot (builders have missed four straight releases; mortgages 7.11–7.21%). The calendar's sentence for Monday: **"The risk is no longer a growth scare that cuts the Fed's legs out. It is a Fed that hikes into a 10-year already over 5%."** The 10-year is **9.6 bps under the 5.25% crisis line**, and Warsh speaks Monday.

---

## 4. CONSENSUS SYNTHESIS

**Where all three agree.**

1. **Rates are the gate now, not fear.** Every desk that writes a macro verdict names the 5.15% 10-year and the priced hike: tech "reduced, no adds," financials "neutral, no upgrade," healthcare "the macro turned," real estate cut to **half size**, utilities **half size**, materials restriction on, discretionary "underweight the index." The calendar: no duration adds until a close back under 5.00% after the minutes. Canary: "rates, dollar and policy, not volatility or credit."
2. **Hedges come down to standard size.** VIX under 20 every close with VIX/VIX3M under 1.00: Marky takes his extra hedge off and keeps the base; the calendar says the same.
3. **NVIDIA is a governance event, not a demand event.** Tech, semis and earnings all say the supply chain answered with numbers (AMAT, CoreWeave, AMD, CSCO's AI target to $9B) and that Tuesday's print is about whether Kress affirms a Huang-era outlook. Nobody buys NVDA before it; Marky "would rather buy NVDA after the print over its 200D than before it at a 52W low with no CEO."
4. **The relief rallies have not earned full size.** XLK, SMH, XLI, XLC, XLE and XLU all touched or reached their lines and none closed decisively over them, all on light volume. Starters at most.
5. **Oil does not get bought on posts.** Energy holds the reduce until Nov 29 or a signature; Canary leaves energy out "on headlines."

**Where they disagree.**

- **Bond proxies.** Marky is long XLRE (three pieces) and full size XLP, and wants XLU over $44.14; Ophelia halves XLRE and XLU and won't add to XLP; Cecil "sells safety, does not buy it" at WEC/ED and COST at 44x.
- **Credit.** Grid A (tech, financials) is still waiting for "HY under 3.40%" it could not read; Canary prints **3.20%**. Cecil keeps zero high yield anyway because **CCC (1,314) did not tighten** with the rest.
- **Cash.** Canary's Ophelia keeps **25–30%**; the Council book holds **16.2%** (83.8% invested).
- **Defense and AI power.** Cecil holds LMT and lists ETN; Ophelia keeps defense neutral and power/electrical cautious after JPMorgan's ETN/GEV cuts.

**The single biggest risk: a Fed that hikes into a 10-year already over 5%, with nothing left to hedge it.** The 10-year is 9.6 bps from 5.25%; Warsh (Mon) and the minutes plus a 20-year auction (Wed) can carry it there before any data does. Stocks and bonds fell together this week (TLT -3.1%), no sector is negatively correlated with SPY, and the dollar and real yields are tightening conditions before the Fed acts. NVDA's print (Tue) lands in the middle of that, at 15% of XLK and 20% of SMH.

**The single biggest opportunity: the credit gate opened while the desks weren't looking.** HY OAS **320** and HY–IG **231** meet Ophelia's own Grid A condition for tech and financials. If NVDA's call is clean and the 10-year holds under 5.25%, the AI-chain names that cleared on numbers (AMAT, TXN/ADI, TSM over its 200D, MSFT, and NVDA itself at 20.6x trailing) are the first buys, and the XLK/SMH 200-day lines are the trigger.

---

## 5. MONDAY WATCHLIST

*All fifteen wikis fresh. Levels are Friday Nov 13 closes from the sector pages; macro from facts.json. Arena: week of Nov 16 is open on #203 (lock Mon 8:50 AM ET).*

**Macro gates (these outrank every ticker line):**

| Gate | Level now | Trigger | Action |
|---|---|---|---|
| **Warsh, Mon 12:00 PM** | Dec hike ~88–89%; 50 bp ~9–14% | Opens the door to 50 bp or "more than one" | 10Y toward **5.25%**; proxies and long-duration growth hit first. Pushback on December: 10Y back under **5.00%**, duration case reopens |
| **10Y** | **5.154%** | Close **over 5.25%** / back **under 5.00%** | Over: crisis line; XLRE "defensive over 5.30%." Under: XLRE back to normal size; the calendar's duration add |
| **NVDA, Tue AMC** | $162.85; straddle ±8.6% (earnings page) vs ±10.8% implied (semis page) | Clean guide under Kress / guide cut, write-down, China enforcement | ±2% on SMH from one name before anything else trades |
| **Retail sales, Tue 8:30** | cons **0.0%**, ex autos +0.4% | **< -0.1%** fires the retail flag; > +0.5% with control > +0.4% lifts 50 bp odds | HD/LOW/TJX/TGT/WMT all read it the same week |
| **FOMC minutes + 20Y, Wed** | prior 20Y 5.469% | "Many/most" saw a December hike; 20Y tail > 2 bp | December locked; long-end supply stress |
| **Credit** | HY OAS **320**, HY–IG **231**, CCC 1,314 | HY–IG back **over 250** | Grid A's gate shuts again |
| **VIX** | **19.30**; VIX/VIX3M 0.936 | Close over 20 with ratio over 1.00 | Extra hedge back on |
| **DXY** | **103.41** | Weekly close **< 99** / **> 105** | Under 99 lifts the materials restriction; over 105 is Canary's red line |

**Sector funds:**

| Ticker | Close | Trigger | Stop / invalidation |
|---|---|---|---|
| **XLK** | $170.28 | Small. Add on a close over **$174.36**, volume > 12.8M | Close under **$169.35**; $165.30, $162.14 |
| **SMH** | $486.75 | Flat. In on a close over the **200D $523.89**, volume > 11.7M | Under **$462.88** → $443–446 |
| **XLC** | $108.69 | Flat. Starter on a close over **$109.31** (50D); target 200D $111.86 | **$106.22** |
| **XLF** | $58.68 | Both adds held; third add over **$59.20** | Close under the **20D $57.06** = warning; $56.67, $55.75; **$55.03** Council line |
| **XLI** | $168.78 | Starter third; full size over the **200D $172.80** on volume > 8.8M | Close under **$165.44** |
| **XLB** | $52.23 | Two-thirds long; add on a weekly close over **$53.90** | Close under **$51.21** |
| **XLE** | $64.96 | Flat. Half on a close over **$64.97**; first targets $66.17, $66.29 | **$62.21**; a close under $63.37 = short-covering week |
| **XLV** | $188.85 | Long; re-add over **$189.66** | **$185.36**; two closes under $181.30 or one under $177.07: half off |
| **XLU** | $44.04 | Flat. Starter on a close over **$44.14** | **$43.79** (Monday gap) |
| **XLP** | $92.35 | Full size; no adds at the high; Ophelia's zone $89–90 | Close under the **20D $89.48**: sell half |
| **XLRE** | $44.37 | Long (Ophelia half size); add on a weekly close over **$45.63** | Close under **$43.09** |
| **XLY** | $119.98 | Long from $118.16; add over **$122.92** | Close under the **200D $115.08** |

**Names:**

| Ticker | Close | Trigger | Stop / note |
|---|---|---|---|
| **NEE / D** (Council book, CORE) | $85.12 / $67.66 | **Virginia SCC evidentiary hearing on NEE–D, Tue Nov 17**; staff recommends denial as proposed | CORE -5% stops **$83.23 / $65.72** (2.2% and 2.9% away) |
| **ALL / UPS / PGR** (Council book) | $267.64 / $112.40 / $235.78 | Held | Stops $243.81 / $104.28 / $217.59 |
| **NVDA** | $162.85 | Cecil after Kress's guide; Marky after the print over its 200D (~$204) | 52-week closing low |
| **MSFT** | $523.88 | Cecil keeps adding at 21.7x | — |
| **HD / DIS** | $348.69 / $118.97 | Report Tue BMO; whispers $3.89 / $1.74 | HD straddle 2.5x norm on 9 open calls: ignore it |
| **TGT / LOW / TJX / WMT / ROST** | $161.45 / $227.73 / $134.37 / $128.09 / $231.68 | Wed / Wed / Wed / Thu / Thu | TGT whisper +6.4%, the widest gap |
| **TTWO / CHTR** | $227.82 / $138.39 | GTA VI Thu Nov 19; Charter tender expires Nov 17 | — |
| **TXN / ADI / AMAT / TSM** | $303.60 / $397.97 / $370.50 / $398.73 | Cecil's chip list; TSM once over its 200D ($403.05) | ADI reports Nov 24 |
| **LLY** | $1,443.50 | Two-year closing high, 1.4% under target | Cycle-3 Medicare prices by **Nov 30** |
| **VST / SRE / CEG** | $133.01 / $79.54 / $280.20 | CEG back over its 200D; VST under its 20D | VST $112.89, SRE $76.89 (52W lows) |
| **MPC / EOG / XOM** | $414.65 / $158.32 / $170.59 | Held; Exxon only after a signature | OPEC+ Nov 29 |
| **DE / MDT** | $673.54 / $102.86 | Nov 25 / Nov 24 | DE into a 103 dollar and the FTC/USDA inquiry |

**Council book (provisional; Monday Nov 9 opens from `portfolio/current.yaml` to Friday Nov 13 closes from `data/weekly/2026-11-13.json`; the official close is Monday's tracker run):** ALL $256.64 → $267.64 (**+4.29%**), PGR $229.04 → $235.78 (+2.94%), UPS $109.77 → $112.40 (+2.40%), D $69.18 → $67.66 (**-2.20%**), NEE $87.61 → $85.12 (**-2.84%**). At 83.8% invested, about **+0.9%** against SPY **+1.67%** from Monday's open ($741.95). No stop hit; the two utilities are the closest, and they share Tuesday's hearing.

**Last week's board, scored.** Fired: CPI hot (core +0.3%); 10Y over 5.00%; **VIX under 20** (hedges off); **HY back under 3.40%** (found by Canary, missed by Grid A); XLC's last third covered over $105.03 ($107.36 Mon); XLI's first sign over $165.44 (Mon); XLK over its 200D (Mon, Wed; lost Fri). Not fired: XLU over $44.09 on a close; XLE over $64.96 (closed on it); XLV re-add $189.66; XLY add $122.92; XLB add $53.90; XLRE add $45.63; every stop held. CEG reported Monday but said nothing on Texas.

---

## 6. CROSS-SECTOR CONNECTIONS — The Hidden Wires

**Wire 1 — The rate-sensitivity chain, running backwards.** Hot core CPI → 2Y +40 bps, 5Y +33, 10Y +29.5 to 5.154% (calendar) → 2s10s flattens to **+27 bps on par** (under financials' +30 line), so the regionals stall (KRE +0.75%, WAFD/HOPE/BANR flat to down) while the dealers rise on the Anthropic IPO → mortgages had fallen a fourth week to **7.11%**, but Freddie's survey predates Thursday (RE, discretionary) → **existing home sales 3.75M** miss → HD/LOW report into it Tuesday/Wednesday → SAFE (pure duration) two-year low, XBI a tenth Friday under its 50-day (healthcare). And the proxies went the other way: XLU over its 200-day, XLP a 52-week high. The chain is live; this week the rotation overpowered it.

**Wire 2 — The AI supply chain loses its face, keeps its orders.** NVDA CEO exit (#205) → NVDA -12.75%, Baird to Neutral with a **$200** target and a possible **$5B** inventory write-down → money moves to AMD (+18.9%), AVGO (+18.2%), MU, LRCX, AMAT → CoreWeave's raise and AMAT's guide answer last week's permitting fear with numbers → Constellation beats and buys a plant, NRG +10.3% (earnings) → utilities' CEG +12.1%, data-center REITs EQIX +4.1% and DLR +3.3% → but JPMorgan cuts ETN/GEV and Baird puts 2027 hyperscaler capex growth at "~40% or less" (industrials, semis) → and TrendForce's Q4 DRAM contract call (**+10–15%**, from ~+20%) is the first slower number on the semis page. Demand held this week; the second derivative turned.

**Wire 3 — The geopolitical energy loop that the barrel ignored.** Trump: the U.S. "does not need" a deal; IRGC tanker blasts; Houthi claims on Saudi facilities (energy) → XLE +5.42%, all thirteen large caps up, refiners on a ~$92 diesel crack → but **WTI -2.5% to $88.56** and Brent under $90 intraday for the first time since August → discretionary and staples keep cheap fuel and freight as a tailwind; industrials' rails fight "stubborn diesel" (IBD) → Canary's geopolitics light stays yellow with oil under $90. The stocks priced the risk of a deal failing; the barrel priced supply.

**Wire 4 — The dollar-and-real-yield squeeze.** Real 10-year ~2.91% (+28 bps) and DXY 103.41 → gold **-4.5%**, silver ~-6%, copper lowest close of the fetch, Bitcoin **-9.9%** and ~$63,450 over the weekend (Canary) → NEM -6.4%, ALB -5.8%, the materials restriction holds → exporters CAT and DE carry a translation headwind (industrials); healthcare's 102 translation line is now crossed for real; staples flag PG/KO/PM/MDLZ overseas sales → TLT -3.1%, LQD -1.65%: the hedge assets fell with the risk assets.

**Wire 5 — The consumer stress triangle.** Food at home **+0.4%** (staples) and card debt a record **$1.29T** with household debt **$19.1T** (financials) → retail sales consensus **0.0%**, 0.1 point from the flag (calendar) → XLY's gain was ~85% Tesla, on news "that isn't about selling cars" → GIS to a 7.3% yield, KDP -7.4% in a day with no cause → DoorDash and Lululemon -4.5% → the holiday fortnight (HD, LOW, TJX, TGT, WMT, ROST, BJ) reads it next week with the 10-year over 5%.

**Wire 6 — Washington's China file.** The Huang allegations and a reported FBI inquiry (semis) → Bessent: whether Nvidia "knew its client" (tech) → MarketWatch's "short-lived U.S.-China trade war" scenario (tech, industrials) → Chinese tech fell on the exit; BIDU, JD, BABA, PDD report next week (earnings) → ACMR is the small-cap export-control name; the truce expires **Jan 10, 2027**.

---

## 7. SECTOR CONTRADICTIONS — Where the Wikis Disagree

### A. Truth Layer — facts.json against the sector pages

facts.json wins on every row; the sector pages' numbers are recorded here, not restated elsewhere.

| Item | facts.json (gen. Nov 14) | What the pages say | Resolution |
|---|---|---|---|
| 2Y | **4.86%** (FRED DGS2, Thu Nov 12) | Grid A **4.88%** (Treasury par, Fri), "+37 bp"; Canary "+40 bp" vs Thu Nov 5 | Different day and basis. facts.json's value is Thursday's |
| 10Y–2Y | **+29** (Fri 10Y vs Thu 2Y) | Grid A **+27** (same-day Fri par); Canary +24 same-day Thursday | Mixed-day pairing; all three agree the curve flattened |
| 3M / 10Y–3M | **4.122% / +103** (^IRX, discount basis) | Grid A 3M **4.32%**, 10s–3M **+83** (par / CMT) | Basis. Canary notes CMT 3M ~20 bps higher |
| WTI | **$88.56** (CLZ26 settle) | Grids A/B/C **$88.92** (CL=F Fri evening, "provisional"); energy also cites **$88.74** Thursday settle and "~-$1.91" on the week | Feed settlement supersedes. Weekly move is **-$2.27 (-2.5%)**; #207's "~-$1.91" was provisional; under $5 either way |
| Gold | **$3,879.70** (GCX26) | Tech **$3,887.60**, materials **~$3,888** (GC=F Fri evening), "about -4.4%" | Feed: **-4.5%** |
| Copper | **$6.0795** | Tech/materials **$6.06** | Evening read vs facts |
| HY OAS | not a facts.json field | **Grid A: "not re-sourced, last 3.48% (Nov 5)"**; Canary **320 bps (Nov 12)** | **Canary is current.** Grid A's posture rests on a reading two weeks old |
| Fed hike odds | next_macro_gate ~88–89% | Grid A **~85%** (secondary coverage, Nov 10); semis/calendar/utilities/energy/comm **~88–89%** | Use 88–89% (CME, later read) |

### B. Same factor, opposite reads

1. **The 10-year over 5%: bearish verdicts, bullish tapes.** Real estate files #206 and cuts to half size; utilities and healthcare call the macro "turned"; staples says "rates finally bite" is 25%. On the same week, XLU broke its 200-day, XLP made a 52-week high, XLRE made a sixth up week, and the carriers (VZ +1.5%, T +2.5%) rose. Every proxy desk writes the same disclaimer: "the bid isn't about rates." Nobody has said what it *is* about besides "not chips."
2. **Credit: gate shut vs gate open.** Tech and financials hold "no adds until HY < 3.40%" on a 3.48% print; Canary's live HY OAS is **3.20%**, HY–IG **231**, "back under the line." Cecil's counterpoint (CCC flat at 1,314; LQD -1.65%) means the healing is in the middle of the credit stack, not the bottom.
3. **Where the NVDA money went.** Tech and semis: "the money did not leave AI; it moved from Nvidia to its rivals." Utilities, staples and comm services: chip money rotated "into steady earners." Both can be true; neither page measures the split.
4. **Iran: re-escalation vs falling oil.** Energy's trigger (#207) reads the week as re-escalation and XLE +5.4%; the feed has WTI -2.5% and Canary rates oil "under $90 despite the Iran re-escalation." Discretionary and staples still count cheap fuel as a tailwind.
5. **The dollar.** Materials keeps the commodity restriction ON (52-week high); healthcare's translation line is crossed; industrials flags exporters; comm services rates the week "risk-on." Same 103.41.
6. **Data-center demand, a fifth week.** CEG's raise, CoreWeave, AMAT and real estate's EQIX/DLR bounce read as demand intact; JPMorgan's ETN/GEV cuts, Baird's capex call and TrendForce's slower DRAM number read as the peak rate of change passing. Open across #193, #199.

### C. Counts, bases and dates the pages differ on

- **October CPI date:** Tue **Nov 10** (calendar, tech, semis, financials, staples/discretionary/real estate citing CNBC Nov 10) vs "Wed Nov 11" (utilities, comm services, energy's calendar row). **Nov 10 is correct**; Nov 11 was Veterans Day.
- **XLE vs its 50-day:** energy **$64.91** (closed 5 cents over) vs Canary **$64.99** (3 cents under). The breadth count above uses the sector page; on Canary's basis it is 7 of 12.
- **10Y 52-week high:** 5.36% (tech, healthcare) vs 5.31% (utilities).
- **NVDA:** consensus $2.47 (tech, yfinance) vs ~$2.49 (semis, EW); implied move ±10.8% (semis) vs ±8.6% straddle (earnings); 200-day $203.92 (tech) vs ~$204.19 (semis).
- **30Y:** 5.47% (Grid A par) vs 5.48% / 5.481% (Grids B/C, ^TYX).
- **VZ spread to the 10Y:** ~93 bp (comm) vs +95 bp on facts.json's 5.154%.
- **Cisco:** semis "results not retrieved"; tech carries the full print.
- **Weights:** Yahoo funds_data unchanged on every page for a second week; concentration math rests on Nov 6 snapshots.

---

## 8. MACRO CALENDAR IMPACT — Hot Core, a Priced Hike, and a Fed-Communication Week

**What this week's data did to the posture.** It removed the ambiguity. Last week the data said hike and the ballot said fear; this week **CPI said hike, the bond market agreed, and the fear left.** Core CPI +0.3% for the third month, headline +0.4%, PPI 6.5% y/y with September revised up; claims ended their run at 200K; existing home sales fell 5.5%; GDPNow 3.5%; NY Fed 1-year expectations 3.9%. Auctions cleared lower than their priors (3Y 4.627%, 10Y 5.020%, 30Y 5.441%) but the secondary market rose through them. The October budget deficit was **$404B** against ~$299B. Every desk moved toward caution on rates while the tape moved up, which is why so many lines printed intraday and failed on the close.

**Next week is a Fed-communication week, not a data week** (calendar Gauntlet):

| Date | Event | What it decides |
|---|---|---|
| **Mon Nov 16** | **Warsh 12:00 PM** (first remarks since CPI); Empire State; Williams, Barr, Barkin | 25 vs 50 bp. An opening to 50 bp or "more than one" = 10Y toward 5.25%; pushback = under 5.00% |
| **Tue Nov 17** | **Retail sales** (cons 0.0%); import prices; IP (+0.1%); NAHB; **HD, DIS** BMO; **NVDA** AMC; Charter tender expiry; **NEE–D Virginia hearing** | Retail < -0.1% fires a third flag; NVDA's call decides the XLK/SMH 200-day lines |
| **Wed Nov 18** | **FOMC minutes 2:00 PM**; housing starts (cons 1.23M); **20Y auction**; STB UP–NS comments; **TGT, LOW, TJX** BMO; PANW AMC | "Many/most" = December locked; starts < 1.15M = housing breaking |
| **Thu Nov 19** | Claims (cons 200K); Philly Fed; 10Y TIPS; **WMT** BMO; ROST, INTU AMC; **GTA VI** | Claims > 215K = layoffs; Philly prices > 50 = pipeline inflation |
| **Fri Nov 20** | UMich final (51.0; 5-yr 3.4%); Waller, Cook | 5-yr ≥ 3.6% = expectations unanchoring, the 50 bp case |
| **Nov 23–27** | Thanksgiving week: ADI, MDT, DELL, HPE (AI-server read-through), DE Nov 25; October PCE and Q3 GDP second estimate (dates unconfirmed) | — |
| **Late Nov – Dec** | OPEC+ Nov 29; Cycle-3 Medicare prices by Nov 30; ISM Dec 1; payrolls Dec 4; **FOMC Dec 8–9** (AVGO Dec 9); November CPI Dec 10 | The last hard prints before the decision |

**The Council's posture into it.** **Cash: the book holds 16.2%** (83.8% invested in ALL, NEE, UPS, PGR and D since Monday's open), under the 20% the book held last week and well under Canary's 25–30% preference. That is the gap to watch, not to force: 31% of the book is in two utilities (NEE, D) that share a regulatory hearing Tuesday and a -236 bp carry gap if the 10-year keeps rising. The desks' postures: **no duration adds while the 10-year is over 5.00%**; hedges back to standard size; tech and semis reduced/flat into NVDA; real estate and utilities half size; staples hold, no adds; energy reduce held to Nov 29; materials restriction on; financials neutral (and its HY gate is, on Canary's numbers, open). Short paper pays **4.12%** on the 3-month bill. The one level that changes all of it: **10Y 5.25%.**

---

*Last updated by Saturday Research Crew: 2026-11-14 (Synthesis Agent, single-agent sequential run, on schedule, Saturday ~20:29 ET; all market data as of Fri 2026-11-13 closes)*
*Inputs: all 15 wikis (stamps 2026-11-13 ×11, 2026-11-14 ×4; **none stale**), macro/facts.json (generated 2026-11-14), data/market_state.json (as_of 2026-11-13), data/weekly/2026-11-13.json, portfolio/current.yaml*
*Next update: Every Saturday 8:26 PM ET*
