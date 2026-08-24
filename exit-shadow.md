# Exit Shadow Log

> **Living Document (created 2026-08-10). SHADOW ONLY -- no enforcement for ~4 cycles.** For each booked pick, log the exit template it WOULD trade under: stop (default -8% SPEC / -5% CORE from entry), thesis invalidation (the pick's Trigger line), time stop (default 6 weeks, or a named catalyst with a date window), trim plan (default: trim 1/3 at +15%, remainder rides a hard trailing stop at -15% from the high-water mark). The template never alters the book; it exists to generate the evidence base that tunes the numbers before enforcement. Newest entries on top, tagged with the week's Monday date, marked `outcome: to be computed` until scored at the following Monday close.

## Entries

### Week of 2026-08-17

Book: TER 20.4% / ALL 15.1% / HIG 15.1% / VICI 9.8% / cash 39.6%. Entry prices = Monday 2026-08-17 (tracker, portfolio/current.yaml).

| Pick | Tag | Stop | Thesis Invalidation (Trigger line) | Time Stop | Trim Plan |
|---|---|---|---|---|---|
| TER @ $432.26 (Ophelia) | **SPEC** -- NVDA-chain semi-test name, catalyst-gated by the Aug 26 print | -8% = $397.68 | XLK loses its 50D $182.80, or NVDA < $210 pre-print, or 10Y closes > 4.75% | Named catalyst overrides the clock: NVDA reports Wed Aug 26 AMC -- reassess the morning after; no carry into September without a confirmed beat | Trim 1/3 at +15% ($497.10); remainder trails -15% from high-water mark |
| ALL @ $261.63 (Cecil) | **CORE** -- mega-cap P&C insurer, liquid, broad institutional sponsorship | -5% = $248.55 | XLF weekly close < $58.00 (breakout fakeout) | 6 weeks (Sep 28) | Trim 1/3 at +15% ($300.87); remainder trails -15% from HWM |
| HIG @ $138.66 (Cecil) | **CORE** -- large-cap P&C insurer, same steepening-curve thesis as ALL | -5% = $131.73 | 10Y-3M curve inverts, or 10Y >= 4.75%, or XLF weekly close < $58.00 | 6 weeks (Sep 28) | Trim 1/3 at +15% ($159.46); remainder trails -15% from HWM |
| VICI @ $26.11 (Cecil) | **CORE** -- net-lease REIT, bond-proxy equity | -5% = $24.80 | XLRE loses its 50D $44.67, or 10Y closes > 4.75% | 6 weeks (Sep 28) | Trim 1/3 at +15% ($30.02); remainder trails -15% from HWM |

outcome (scored 2026-08-24, date-pinned daily bars 2026-08-17 -> 2026-08-21):

| Pick | Stop Touched? | +15% Trim Reached? | Would-Have Return | Actual Booked Return | Verdict |
|---|---|---|---|---|---|
| TER @ $432.26 (stop $397.68) | **YES -- Tue 2026-08-18 low $392.18** | No (week high $444.17) | -8.00% (stopped Tue) | -13.07% | **STOP SAVED ~5.1pp** -- the week's worst pick would have been cut Tuesday |
| ALL @ $261.63 (stop $248.55) | No (week low $252.83) | No | -2.98% (held) | -2.98% | no difference |
| HIG @ $138.66 (stop $131.73) | No (week low $136.00) | No | -1.85% (held) | -1.85% | no difference |
| VICI @ $26.11 (stop $24.80) | No (week low $25.81) | No (week high $26.83) | +1.55% (held) | +1.55% | no difference |

Cycle tally: stops helped 1 (TER, +5.1pp vs actual), hurt 0, untouched 3. The -8% SPEC stop would have cut the book's worst pick two days early.

Scored cycles to date: 1 of 4. The stop-calibration summary block appears after 4 scored cycles.

---

### Week of 2026-08-10 -- NO BOOK (ENGINE ABORT)

No exit templates: the sanity gate blocked the book (see shadow-book.md, week of 2026-08-10). The shadow book's five would-be picks (VSAT/AXON/PPG/VRTX/ACN) are tracked for counterfactual P&L in the Shadow Book only -- they were never booked, so no stops/trims attach. Scored cycles to date: 0 of 4; the stop-calibration summary block appears after 4 scored cycles.

---
