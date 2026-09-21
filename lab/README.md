# The Testing Room

Where Council designs are tried against the weeks the real Council actually ran,
before anything changes in production.

## Rules

1. **Only weeks the Council ran.** A week is in scope if it has a Monday/Tuesday
   report and has closed. Every week therefore has a real Council book to compare
   against (an abort week counts, scored as the cash the Council actually held).
   The set grows by one each Monday.
2. **Point-in-time.** For the week opening Monday W, nothing dated W or later may
   reach a variant. Anything production reads "as of today" is replaced with what
   was knowable then. See the docstring in `engine_lab.py` for the full table.
3. **One scoring basis.** Monday open (first session on or after Monday) to Friday
   close, dividend-adjusted total return, cash earns zero. This is the same basis
   as the fixed `portfolio/tracker.py` and `scripts/arena_ingest.py`.
4. **Beat random first.** Every variant is scored against 200 random books drawn
   from the same universe at the same weights. A variant that cannot beat random
   picks has no selection signal, however good its reasoning reads.
5. **LLM passes stay after the training cutoff.** The Council's weeks (July 2026
   on) postdate the model's May 2026 training cutoff, so no LLM variant can
   recall how they went. Never extend an LLM pass to earlier weeks.
6. **Nine weeks is small.** Look for large, consistent effects and for failures
   with a clear mechanism. Do not tune parameters to these weeks and then
   report the same weeks as proof.

## Rooms

- **Engine Lab** -- `engine_lab.py`. The numeric engines, replayed as pure code.
- **Council Room** -- (Pass 2) the LLM layer: brief-first, separate passes,
  research-led, each fed the exact repo snapshot from Monday 08:50 of its week.

## Faithfulness of the Engine Lab replay

| Engine  | Faithful? | Why |
|---------|-----------|-----|
| Ophelia | yes | price-only; the lab differs from production only by the wiki nudge (at most +/-7 points) |
| Marky   | yes | price-only, same caveat; the 10Y gate reads that week's ^TNX |
| Cecil   | **no** | no point-in-time P/E or fundamentals, so only his safety leg is live |

## Run

    python lab/engine_lab.py            # Pass 2: variants + diagnostics
    python lab/engine_lab.py --pass 1   # Pass 1 baseline only

Price data is cached in `lab/cache/` (gitignored). Results go to `lab/results/`.

## Pass 1 -- engines as configured 2026-09-21 (9 Council weeks, 2026-07-20 .. 2026-09-14)

| | Mean alpha / wk | Beat SPY | vs random picks | Invested | Cumulative |
|---|---|---|---|---|---|
| Replayed engines | -1.32% (t -2.11) | 2 of 9 | -1.13%/wk, 37th pctile | 97% | -9.2% |
| Real Council | -0.92% (t -2.04) | 2 of 9 | -- | 57% | -5.7% |
| SPY | | | | | +2.4% |
| Equal-weight universe | | | | | +0.9% |

Contribution vs SPY by sponsor, replayed book: Ophelia -7.80%, Marky -2.34%,
Cecil -1.56%. Two names are 6.85 of Ophelia's 7.80 points: TPR (-20.1%, held
through its 8/13 earnings) and TER (-11.6%). The 2026-08-10 book TPR sank lost
4.75%, worse than all 200 random draws; the real Council aborted that week and
held cash.

*Corrected in Pass 2.* This paragraph first blamed a "last week's top sector"
anchor chasing one-week winners into a reversal. The anchor actually reads the
week before last, and the Pass 2 diagnostics do not support the reversal story.

## Pass 2 -- registered before any variant was run

**Question.** Do the two fixes proposed after Pass 1 stop the engines losing
to random picks: Ophelia reading multi-week relative strength instead of a
single week, and Marky putting less weight on a calm tape?

| Variant | Change (knobs in the production engines; defaults unchanged) |
|---|---|
| baseline | engines as configured 2026-09-21 -- reproduces Pass 1 exactly |
| O-rs | Ophelia's sector anchor and flow term read each sector's 12-1 relative strength (weekly-equivalent return over the up-to-12-week window, skipping the latest week) instead of one week's return |
| O-rs+ | O-rs, and her risk-adjusted leg reads each name's own 12-1 return instead of last week's |
| M-15 | Marky's low-volatility leg 30 -> 15 points |
| M-0 | Marky's low-volatility leg off |
| O-rs+M-15 | the two headline changes together |
| no-Ophelia | Ophelia's proposal removed -- a reference point, not a candidate |

Nothing is tuned to these weeks. The 12-1 window is the standard momentum
construction, it is kept on a per-week scale so every existing constant reads
it the way it read one week, and the low-vol ladder (30 / 15 / 0) is fixed in
advance so the response to the dose is visible.

**Diagnostics.** Every scoring input's rank IC with the following week's
return, across the whole eligible universe (about 270 names a week, one IC per
week), and the same test at the sector level (8 sectors a week). The IC is the
bigger sample; the five-name book is the practical consequence.

**Decision rule.** A variant replaces the configured engine only if all three
hold:

1. *Mechanism* -- the input it removes has a negative mean IC with next week's
   return over the Council's weeks, and the input it adds does not.
2. *Book* -- its replayed book beats the baseline's on the paired weekly
   comparison and does no worse against random picks.
3. *Not one week* -- the paired improvement stays positive with its single
   best week removed.

A variant that passes goes live as a forward test: the lab reruns each Monday
as the set grows, and a variant that stops passing is reverted.

## Pass 2 results -- Engine Lab

Run after the registration commit (8a2ea49); `results/pass2_variants.json`.

| Variant | Alpha / wk | vs random | Pctile | vs baseline, paired | Weeks better | Without best week | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|
| baseline | -1.32% | -1.13% | 37% | -- | -- | -- | -9.2% | -10.3% |
| O-rs | -0.20% | -0.01% | 50% | +1.12% (t 2.13) | 7/9 | +0.64% | +0.6% | -3.4% |
| O-rs+ | -0.76% | -0.56% | 36% | +0.56% (t 1.02) | 6/9 | +0.08% | -4.4% | -6.5% |
| M-15 | -1.27% | -1.07% | 36% | +0.06% (t 0.23) | 4/9 | -0.10% | -8.7% | -10.5% |
| M-0 | -1.59% | -1.41% | 31% | -0.27% (t -0.92) | 2/9 | -0.47% | -11.3% | -11.4% |
| O-rs+M-15 | -0.23% | -0.04% | 46% | +1.09% (t 1.75) | 6/9 | +0.60% | +0.3% | -4.6% |
| no-Ophelia (reference) | -0.72% | -0.52% | 40% | +0.60% (t 1.18) | 6/9 | +0.12% | -4.0% | -6.0% |

**Under the registered rule, nothing ships.**

- **O-rs** passes the book tests (2, 3) and fails the mechanism test (1). The
  input it removes is not negative: Ophelia's rotation score has a stock-level
  IC of +0.005, and the week-before-last sector return a sector-level IC of
  +0.063. The input it adds ranks sectors no better (sector-level IC -0.069).
  The book improves because 12-1 strength parked Ophelia in Healthcare for 8 of
  the 9 weeks, and its top sector beat the universe by 0.90%/wk: one sector
  call that paid, not a better method. Its single best week (+4.98
  points) is the week it happened to miss TPR's earnings collapse.
- **O-rs+** adds nothing: the stock-level 12-1 return is itself negative (IC
  -0.034).
- **M-15 / M-0**: less weight on a calm tape does nothing, and none at all
  hurts. Marky's low-vol leg is not his problem (IC -0.002).

**What the diagnostics show instead.** These came out of the same nine weeks,
so they are hypotheses to test forward, not findings:

1. *Short-horizon stock momentum ran backwards.* A name's return over the prior
   three weeks had a negative rank IC with its next week in 8 of 9 weeks (mean
   -0.053, t -1.90), and more volatile names beat calmer ones (IC +0.08 to
   +0.10). Both engines lean on that input: Marky's momentum leg (IC -0.040,
   t -2.17) and Ophelia's relative-momentum leg (IC -0.055, t -1.80). It is the
   textbook short-term reversal in single stocks, which is a reason to take it
   seriously, not proof that it will persist.
2. *Ophelia's anchor is a week stale.* It reads the week before last, a lag
   inherited from the original app (`getPriorWeekDate`). Last week's top sector
   beat the universe the following week in 8 of 9 weeks (+0.72%/wk); the
   week-before-last's, which is what she uses, in 5 of 9 (-0.29%/wk).
3. *Earnings screening covers one engine.* Only Cecil's picks are checked for
   earnings proximity; TPR was Ophelia's, held through its print.

## Council Room V1 -- brief-first (registered before any agent ran)

One fresh agent per Council week, with no memory of the others, reads only
that week's snapshot: the repo as it stood just before the real Council's
report commit that Monday (README, scoreboard, wikis, journals), the previous
report, and a price table that ends at the prior Friday's close. It starts
from the brief (Market Brief, the journals' latest entries, earnings, canary
watch, last week's run), goes deeper only if it wants to, and books 0-5 names
from the universe at 5-30% each, the rest cash. No web, no code, no files
outside its folder; the prompt is `council_room_v1_prompt.md`, identical
every week apart from dates and paths. The agents run on a model whose
training ends in May 2026, so none can recall how its week went -- and the
person running the room, who has seen these weeks' returns, writes no picks.

**What counts.** Primary: V1 beats random picks at its own weights (mean
vs-random above zero, mean percentile above 50%). Secondary: the paired
comparison with the engine replay and with the real Council. One draw per week
cannot prove skill on its own. If V1 clears random, the next step is a forward
shadow: the brief-first Council books every Monday alongside the real one and
both are scored. If it does not, the research layer is not adding selection
either.

    python lab/council_room.py snapshot DIR   # build the week folders
    python lab/council_room.py score DIR      # score each folder's book.json
