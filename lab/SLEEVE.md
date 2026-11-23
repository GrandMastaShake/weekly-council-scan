# Four-week earnings-drift sleeve: forward record

Registered 2026-10-12 as Pass 29 (`lab/README.md`, 85714da). A paper ledger, not a Council member. Every Monday the routine runs, the five highest-surprise names among last week's S&P 500 reporters are bought at the open and held to the Friday of week W+3, if at least 15 candidates exist. `lab/forward_sleeve.py` rewrites this page from `lab/sleeve_ledger.json` (append-only) and the bars; edits by hand are overwritten.

Last run: 2026-11-23 12:16. Latest bar: 2026-11-23. Mondays logged: 7; active: 4.

**Status: too early (2 closed cohorts; 12 across three seasons are needed).** Closed cohorts: 2; mean edge over the tradeable pool +0.01% a week of holding; ahead in 50% of cohorts.

By season: 2026Q4 +0.01%.

| Monday | Status | Candidates | Picks (surprise %) | Exit Friday | Four-week return | Pool | SPY | Edge / wk of holding | After 0.10% round trip | Over candidates, /wk |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-12 | inactive | 2 | -- | | | | | | | |
| 2026-10-19 late | closed | 25 | GS (+30), TRV (+24), UNH (+13), BLK (+11), RF (+11) | 2026-11-13 | +4.50% | +2.83% | -1.68% | +0.42% | +0.39% | -0.11% |
| 2026-10-26 late | closed | 75 | HAS (+57), ELV (+49), DECK (+29), RTX (+27), COF (+22) | 2026-11-20 | -6.35% | -4.74% | -9.50% | -0.40% | -0.43% | -0.72% |
| 2026-11-02 late | open | 175 | CNC (+100), COIN (+100), WY (+100), OKE (+42), KIM (+39) | 2026-11-27 | -8.27% | -3.21% | -4.71% | -1.27% | -1.29% | -1.45% |
| 2026-11-09 late | open | 135 | CPT (+100), ECHO (+100), MRNA (+100), UDR (+100), DOC (+54) | 2026-12-04 | -7.40% | -2.45% | -2.46% | -1.24% | -1.26% | -1.28% |
| 2026-11-16 late | inactive | 11 | -- | | | | | | | |
| 2026-11-23 late | inactive | 13 | -- | | | | | | | |

Open cohorts are marked to the latest close and do not count toward the status. Rule: confirmed at 12 or more closed cohorts across three seasons with a mean edge of at least +0.20% a week of holding, a Newey-West t of 2 or more and a positive mean in two seasons; rejected at 12 or more with a mean of 0 or below, or at 8 or more with t of -1 or lower; otherwise it keeps running, to 24 cohorts. Pass 23's backtest, for reference: +0.404% a week of holding over 34 active weeks (t 3.02).
