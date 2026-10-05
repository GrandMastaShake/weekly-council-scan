# Forward record

Every design registered in the Testing Room, scored on Council weeks that closed
after it was registered -- weeks it could not have been tuned on. `lab/forward.py`
regenerates this page each Monday (scheduled task 8); edits by hand are overwritten.
Scoring is the lab's: Monday open to Friday close, dividend-adjusted, cash earns zero.

Last run: 2026-10-05 18:18. Forward weeks: 2 (2026-09-21, 2026-09-28).

| Design | Source | Weeks | Alpha / wk | At exposure | Invested | vs production | Better / differed | vs random | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| **Real Council** (official book) | engines + LLM layer | 2 | -0.79% | -0.61% | 66% | +0.62% | 2/2 | -- | -0.7% | -1.2% |
| production | engines as live | 2 | -1.40% | -1.40% | 99% | -- | -- | -0.56% (40%) | -2.0% | -2.3% |
| no-screen | Pass 3, H3 | 2 | -1.40% | -1.40% | 99% | +0.00% | 0/0 | -0.56% (40%) | -2.0% | -2.3% |
| O-last | Pass 3, H2 | 2 | -0.49% | -0.49% | 100% | +0.92% | 2/2 | +0.38% (52%) | -0.2% | -1.6% |
| M-skip | Pass 3, H1 | 2 | -1.50% | -1.48% | 96% | -0.10% | 1/2 | -0.67% (36%) | -2.2% | -2.2% |
| O-last+M-skip | Pass 3 | 2 | -0.42% | -0.42% | 99% | +0.98% | 2/2 | +0.43% (53%) | -0.0% | -1.4% |
| O-rs | Pass 2 | 2 | -2.36% | -2.36% | 97% | -0.96% | 1/2 | -1.52% (16%) | -3.9% | -3.9% |
| O-rs+ | Pass 2 | 2 | -2.21% | -2.21% | 97% | -0.81% | 1/2 | -1.37% (20%) | -3.6% | -3.6% |
| M-15 | Pass 2 | 2 | -1.40% | -1.40% | 99% | +0.00% | 0/0 | -0.56% (40%) | -2.0% | -2.3% |
| M-0 | Pass 2 | 2 | +0.49% | +0.49% | 99% | +1.89% | 1/1 | +1.33% (78%) | +1.8% | +0.0% |
| O-rs+M-15 | Pass 2 | 2 | -2.75% | -2.74% | 96% | -1.34% | 1/2 | -1.91% (12%) | -4.6% | -4.6% |
| no-Ophelia | Pass 2, reference | 2 | -1.83% | -1.80% | 95% | -0.42% | 1/2 | -1.02% (29%) | -2.8% | -2.8% |
| Ophelia-solo | Pass 9b, the engine alone | 1 | -3.05% | -3.05% | 100% | -0.63% | 0/1 | -2.65% (9%) | -2.9% | -2.9% |
| Ophelia-solo-ownmap | Pass 10, the owner's map (weekly clusters) | 1 | -2.12% | -2.12% | 100% | +0.30% | 1/1 | -1.72% (18%) | -2.0% | -2.0% |
| Cecil-solo | Pass 11, the engine alone with a point-in-time P/E | 1 | -2.70% | -2.70% | 100% | -0.28% | 0/1 | -2.30% (12%) | -2.5% | -2.5% |
| Union-equal | Pass 13, every engine's five, equal over the union | 1 | -2.53% | -2.53% | 100% | -0.11% | 0/1 | -2.05% (2%) | -2.4% | -2.4% |

## By week (book return)

| Week | SPY | Real Council | production | no-screen | O-last | M-skip | O-last+M-skip | O-rs | O-rs+ | M-15 | M-0 | O-rs+M-15 | no-Ophelia | Ophelia-solo | Ophelia-solo-ownmap | Cecil-solo | Union-equal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-21 | +0.67% | +0.41% | +0.28% | +0.28% | +1.49% | -0.11% | +1.34% | -2.38% | -2.35% | +0.28% | +0.28% | -3.18% | -1.24% | -- | -- | -- | -- |
| 2026-09-28 | +0.17% | -1.15% | -2.25% | -2.25% | -1.63% | -2.06% | -1.35% | -1.51% | -1.25% | -2.25% | +1.53% | -1.48% | -1.58% | -2.89% | -1.95% | -2.53% | -2.36% |

A five-name weekly book moves about 1.7 points a week against SPY, so a design needs
roughly 40 forward weeks before its mean says much (lab/README.md, "What nine weeks
can and cannot say"). Read this page for direction and for designs that break, not
for proof. "production" is today's engine code replayed, so it follows every
change to production; the Real Council row is what was actually booked.

"At exposure" is the book's return less its invested share of SPY's: cash earns
zero, so a book half in cash is held to half of SPY's week. "Better / differed"
counts the weeks a design beat production out of the weeks its names differed
from production's; a week with the same names is a tie, not a loss.
