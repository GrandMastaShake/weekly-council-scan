# Four-week earnings-drift sleeve: forward record

Registered 2026-10-12 as Pass 29 (`lab/README.md`, 85714da). A paper ledger, not a Council member. Every Monday the routine runs, the five highest-surprise names among last week's S&P 500 reporters are bought at the open and held to the Friday of week W+3, if at least 15 candidates exist. `lab/forward_sleeve.py` rewrites this page from `lab/sleeve_ledger.json` (append-only) and the bars; edits by hand are overwritten.

Last run: 2026-10-20 22:58. Latest bar: 2026-10-20. Mondays logged: 2; active: 1.

**Status: too early (0 closed cohorts; 12 across three seasons are needed).** Closed cohorts: 0.

| Monday | Status | Candidates | Picks (surprise %) | Exit Friday | Four-week return | Pool | SPY | Edge / wk of holding | After 0.10% round trip | Over candidates, /wk |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-12 | inactive | 2 | -- | | | | | | | |
| 2026-10-19 late | open | 25 | GS (+30), TRV (+24), UNH (+13), BLK (+11), RF (+11) | 2026-11-13 | +1.59% | +0.69% | +0.24% | +0.23% | +0.20% | +0.17% |

Open cohorts are marked to the latest close and do not count toward the status. Rule: confirmed at 12 or more closed cohorts across three seasons with a mean edge of at least +0.20% a week of holding, a Newey-West t of 2 or more and a positive mean in two seasons; rejected at 12 or more with a mean of 0 or below, or at 8 or more with t of -1 or lower; otherwise it keeps running, to 24 cohorts. Pass 23's backtest, for reference: +0.404% a week of holding over 34 active weeks (t 3.02).
