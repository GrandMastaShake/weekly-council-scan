# Forward record

Every design registered in the Testing Room, scored on Council weeks that closed
after it was registered -- weeks it could not have been tuned on. `lab/forward.py`
regenerates this page each Monday (scheduled task 8); edits by hand are overwritten.
Scoring is the lab's: Monday open to Friday close, dividend-adjusted, cash earns zero.

Last run: 2026-09-28 11:44. Forward weeks: 1 (2026-09-21).

| Design | Source | Weeks | Alpha / wk | vs production | Weeks better | vs random | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|
| **Real Council** (official book) | engines + LLM layer | 1 | -0.26% | +0.13% | 1/1 | -- | +0.4% | +0.0% |
| production | engines as live | 1 | -0.39% | -- | -- | +0.83% (70%) | +0.3% | +0.0% |
| no-screen | Pass 3, H3 | 1 | -0.39% | +0.00% | 0/1 | +0.83% (70%) | +0.3% | +0.0% |
| O-last | Pass 3, H2 | 1 | +0.82% | +1.21% | 1/1 | +2.07% (86%) | +1.5% | +0.0% |
| M-skip | Pass 3, H1 | 1 | -0.78% | -0.39% | 0/1 | +0.43% (60%) | -0.1% | -0.1% |
| O-last+M-skip | Pass 3 | 1 | +0.68% | +1.06% | 1/1 | +1.91% (83%) | +1.3% | +0.0% |
| O-rs | Pass 2 | 1 | -3.05% | -2.66% | 0/1 | -1.81% (14%) | -2.4% | -2.4% |
| O-rs+ | Pass 2 | 1 | -3.01% | -2.63% | 0/1 | -1.78% (14%) | -2.3% | -2.3% |
| M-15 | Pass 2 | 1 | -0.39% | -0.00% | 0/1 | +0.82% (70%) | +0.3% | +0.0% |
| M-0 | Pass 2 | 1 | -0.39% | -0.00% | 0/1 | +0.82% (70%) | +0.3% | +0.0% |
| O-rs+M-15 | Pass 2 | 1 | -3.84% | -3.46% | 0/1 | -2.61% (4%) | -3.2% | -3.2% |
| no-Ophelia | Pass 2, reference | 1 | -1.91% | -1.52% | 0/1 | -0.74% (38%) | -1.2% | -1.2% |

## By week (book return)

| Week | SPY | Real Council | production | no-screen | O-last | M-skip | O-last+M-skip | O-rs | O-rs+ | M-15 | M-0 | O-rs+M-15 | no-Ophelia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-21 | +0.67% | +0.41% | +0.28% | +0.28% | +1.49% | -0.11% | +1.34% | -2.38% | -2.35% | +0.28% | +0.28% | -3.18% | -1.24% |

A five-name weekly book moves about 1.7 points a week against SPY, so a design needs
roughly 40 forward weeks before its mean says much (lab/README.md, "What nine weeks
can and cannot say"). Read this page for direction and for designs that break, not
for proof. "production" is today's engine code replayed, so it follows every
change to production; the Real Council row is what was actually booked.
