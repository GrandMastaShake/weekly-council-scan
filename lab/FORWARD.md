# Forward record

Every design registered in the Testing Room, scored on Council weeks that closed
after it was registered -- weeks it could not have been tuned on. `lab/forward.py`
regenerates this page each Monday (scheduled task 8); edits by hand are overwritten.
Scoring is the lab's: Monday open to Friday close, dividend-adjusted, cash earns zero.

Last run: 2026-10-12 12:09. Forward weeks: 3 (2026-09-21, 2026-09-28, 2026-10-05).

| Design | Source | Weeks | Alpha / wk | At exposure | Invested | vs production | Better / differed | vs random | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| **Real Council** (official book) | engines + LLM layer | 3 | -1.36% | -1.17% | 71% | -0.29% | 2/3 | -- | -2.1% | -2.5% |
| production | engines as live | 3 | -1.07% | -1.05% | 97% | -- | -- | -0.66% (37%) | -1.3% | -2.3% |
| no-screen | Pass 3, H3 | 3 | -1.07% | -1.05% | 97% | +0.00% | 0/0 | -0.66% (37%) | -1.3% | -2.3% |
| O-last | Pass 3, H2 | 3 | -0.72% | -0.72% | 99% | +0.35% | 2/3 | -0.32% (40%) | -0.2% | -1.7% |
| M-skip | Pass 3, H1 | 3 | -1.40% | -1.37% | 96% | -0.32% | 1/3 | -1.01% (30%) | -2.2% | -2.2% |
| O-last+M-skip | Pass 3 | 3 | -0.68% | -0.67% | 99% | +0.40% | 2/3 | -0.30% (42%) | -0.1% | -1.4% |
| O-rs | Pass 2 | 3 | -1.75% | -1.71% | 95% | -0.67% | 1/2 | -1.32% (20%) | -3.2% | -3.9% |
| O-rs+ | Pass 2 | 3 | -0.49% | -0.47% | 97% | +0.59% | 2/3 | -0.09% (44%) | +0.4% | -3.6% |
| M-15 | Pass 2 | 3 | -1.08% | -1.05% | 97% | -0.00% | 0/0 | -0.66% (37%) | -1.3% | -2.3% |
| M-0 | Pass 2 | 3 | +0.06% | +0.07% | 98% | +1.13% | 1/1 | +0.45% (60%) | +2.2% | +0.0% |
| O-rs+M-15 | Pass 2 | 3 | -2.01% | -1.98% | 95% | -0.94% | 1/2 | -1.60% (16%) | -4.0% | -4.6% |
| no-Ophelia | Pass 2, reference | 3 | -1.35% | -1.30% | 94% | -0.28% | 2/3 | -0.95% (29%) | -2.1% | -2.8% |
| Ophelia-solo | Pass 9b, the engine alone | 2 | -0.01% | -0.01% | 100% | +1.41% | 1/2 | -0.18% (47%) | +1.2% | -2.9% |
| Ophelia-solo-ownmap | Pass 10, the owner's map (weekly clusters) | 2 | -2.80% | -2.80% | 100% | -1.38% | 1/2 | -2.96% (12%) | -4.2% | -4.2% |
| Cecil-solo | Pass 11, the engine alone with a point-in-time P/E | 2 | -0.73% | -0.73% | 100% | +0.69% | 1/2 | -0.90% (36%) | -0.2% | -2.5% |
| Union-equal | Pass 13, every engine's five, equal over the union | 2 | -0.91% | -0.91% | 100% | +0.51% | 1/2 | -0.97% (28%) | -0.5% | -2.4% |

## By week (book return)

| Week | SPY | Real Council | production | no-screen | O-last | M-skip | O-last+M-skip | O-rs | O-rs+ | M-15 | M-0 | O-rs+M-15 | no-Ophelia | Ophelia-solo | Ophelia-solo-ownmap | Cecil-solo | Union-equal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-21 | +0.67% | +0.41% | +0.28% | +0.28% | +1.49% | -0.11% | +1.34% | -2.38% | -2.35% | +0.28% | +0.28% | -3.18% | -1.24% | -- | -- | -- | -- |
| 2026-09-28 | +0.17% | -1.15% | -2.25% | -2.25% | -1.63% | -2.06% | -1.35% | -1.51% | -1.25% | -2.25% | +1.53% | -1.48% | -1.58% | -2.89% | -1.95% | -2.53% | -2.36% |
| 2026-10-05 | +1.15% | -1.36% | +0.74% | +0.74% | -0.05% | -0.04% | -0.03% | +0.64% | +4.11% | +0.73% | +0.35% | +0.60% | +0.75% | +4.19% | -2.32% | +2.39% | +1.86% |

A five-name weekly book moves about 1.7 points a week against SPY, so a design needs
roughly 40 forward weeks before its mean says much (lab/README.md, "What nine weeks
can and cannot say"). Read this page for direction and for designs that break, not
for proof. "production" is today's engine code replayed, so it follows every
change to production; the Real Council row is what was actually booked.

"At exposure" is the book's return less its invested share of SPY's: cash earns
zero, so a book half in cash is held to half of SPY's week. "Better / differed"
counts the weeks a design beat production out of the weeks its names differed
from production's; a week with the same names is a tie, not a loss.
