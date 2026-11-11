# Four-week earnings-drift sleeve: forward record

Registered 2026-10-12 as Pass 29 (`lab/README.md`, 85714da). A paper ledger, not a Council member. Every Monday the routine runs, the five highest-surprise names among last week's S&P 500 reporters are bought at the open and held to the Friday of week W+3, if at least 15 candidates exist. `lab/forward_sleeve.py` rewrites this page from `lab/sleeve_ledger.json` (append-only) and the bars; edits by hand are overwritten.

Last run: 2026-11-11 17:21. Latest bar: 2026-11-11. Mondays logged: 5; active: 4.

**Status: too early (0 closed cohorts; 12 across three seasons are needed).** Closed cohorts: 0.

| Monday | Status | Candidates | Picks (surprise %) | Exit Friday | Four-week return | Pool | SPY | Edge / wk of holding | After 0.10% round trip | Over candidates, /wk |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-12 | inactive | 2 | -- | | | | | | | |
| 2026-10-19 late | open | 25 | GS (+30), TRV (+24), UNH (+13), BLK (+11), RF (+11) | 2026-11-13 | +4.21% | +3.56% | -0.97% | +0.16% | +0.14% | -0.06% |
| 2026-10-26 late | open | 75 | HAS (+57), ELV (+49), DECK (+29), RTX (+27), COF (+22) | 2026-11-20 | +2.47% | +2.81% | -0.32% | -0.08% | -0.11% | -0.35% |
| 2026-11-02 late | open | 175 | CNC (+100), COIN (+100), WY (+100), OKE (+42), KIM (+39) | 2026-11-27 | -0.62% | +1.39% | +0.05% | -0.50% | -0.53% | -0.58% |
| 2026-11-09 late | open | 135 | CPT (+100), ECHO (+100), MRNA (+100), UDR (+100), DOC (+54) | 2026-12-04 | +0.32% | +2.28% | +2.41% | -0.49% | -0.51% | -0.58% |

Open cohorts are marked to the latest close and do not count toward the status. Rule: confirmed at 12 or more closed cohorts across three seasons with a mean edge of at least +0.20% a week of holding, a Newey-West t of 2 or more and a positive mean in two seasons; rejected at 12 or more with a mean of 0 or below, or at 8 or more with t of -1 or lower; otherwise it keeps running, to 24 cohorts. Pass 23's backtest, for reference: +0.404% a week of holding over 34 active weeks (t 3.02).
