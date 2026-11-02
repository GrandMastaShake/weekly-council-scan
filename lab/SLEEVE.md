# Four-week earnings-drift sleeve: forward record

Registered 2026-10-12 as Pass 29 (`lab/README.md`, 85714da). A paper ledger, not a Council member. Every Monday the routine runs, the five highest-surprise names among last week's S&P 500 reporters are bought at the open and held to the Friday of week W+3, if at least 15 candidates exist. `lab/forward_sleeve.py` rewrites this page from `lab/sleeve_ledger.json` (append-only) and the bars; edits by hand are overwritten.

Last run: 2026-11-02 12:24. Latest bar: 2026-11-02. Mondays logged: 4; active: 3.

**Status: too early (0 closed cohorts; 12 across three seasons are needed).** Closed cohorts: 0.

| Monday | Status | Candidates | Picks (surprise %) | Exit Friday | Four-week return | Pool | SPY | Edge / wk of holding | After 0.10% round trip | Over candidates, /wk |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-12 | inactive | 2 | -- | | | | | | | |
| 2026-10-19 late | open | 25 | GS (+30), TRV (+24), UNH (+13), BLK (+11), RF (+11) | 2026-11-13 | +2.81% | +2.46% | -1.03% | +0.09% | +0.06% | -0.01% |
| 2026-10-26 late | open | 75 | HAS (+57), ELV (+49), DECK (+29), RTX (+27), COF (+22) | 2026-11-20 | +1.51% | +1.85% | -0.39% | -0.08% | -0.11% | -0.46% |
| 2026-11-02 late | open | 175 | CNC (+100), COIN (+100), WY (+100), OKE (+42), KIM (+39) | 2026-11-27 | -0.42% | +0.60% | -0.02% | -0.25% | -0.28% | -0.31% |

Open cohorts are marked to the latest close and do not count toward the status. Rule: confirmed at 12 or more closed cohorts across three seasons with a mean edge of at least +0.20% a week of holding, a Newey-West t of 2 or more and a positive mean in two seasons; rejected at 12 or more with a mean of 0 or below, or at 8 or more with t of -1 or lower; otherwise it keeps running, to 24 cohorts. Pass 23's backtest, for reference: +0.404% a week of holding over 34 active weeks (t 3.02).
