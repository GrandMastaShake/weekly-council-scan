# The slow book

Cecil's engine picks on the frozen S&P 500 list, equal weight, bought Monday and held four weeks; no stop,
no exits (Pass 35). `lab/forward_slow.py` regenerates this page each Monday from `lab/slow_ledger.json`,
which is append-only; edits by hand are overwritten.

Last run: 2026-11-23 12:17. Prices through 2026-11-23.

**Status: too early (0 closed cohorts; 12 across three quarters are needed).** Closed cohorts: 0. Mean edge per week of holding: --.

Confirmed needs 12 closed cohorts in three quarters, a mean edge of +0.15% a week of holding, t of 2 and two positive
quarters; rejected at zero or below with 12, or t at -1 or lower with 8. Before that this page shows direction, not proof.

| Monday | Picks | Status | Exit | Picks | Pool | SPY | Edge / wk | First week's edge |
|---|---|---|---|---|---|---|---|---|
| 2026-11-16 (late) | AES, EG, VTRS | open | 2026-12-11 | -2.50% | -3.80% | -3.53% | +0.324% | +3.59% |
| 2026-11-23 (late) | EG, PRU, ACGL | open | 2026-12-18 | +0.95% | +0.07% | -0.16% | +0.221% | +0.88% |

Open cohorts are marked to the latest close. "Late" means the row was logged after that Monday's open, which is how this
job runs; the picks use only data from before the Monday.
