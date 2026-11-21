# The Testing Room

Where Council designs are tried against the weeks the real Council actually ran,
before anything changes in production.

## Rules

1. **Only weeks the Council ran -- except engine-only tests.** A week is in scope
   if it has a Monday/Tuesday report and has closed. Every week therefore has a
   real Council book to compare against (an abort week counts, scored as the
   cash the Council actually held). The set grows by one each Monday. The
   numeric engines read only prices, so a test of the engines alone may also use
   the weeks before the Council existed (approved 2026-09-21; Pass 3), with one
   caveat: today's universe holds names that are in it because they later ran.
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
7. **A risk design is judged against cash.** Anything that lowers a book's
   swings (sizing, caps, exposure dials) is compared with the plain book held
   at the constant exposure that gives the same weekly SD: return per unit of
   risk, which cash-scaling cannot change. Lower risk alone proves nothing;
   cash does that for free (Pass 8, where the Warden's registered rule lacked
   this and passed a design that plain exposure beats).

## Rooms

- **Engine Lab** -- `engine_lab.py`. The numeric engines, replayed as pure code.
- **Council Room** -- `council_room.py`. The LLM layer: one fresh agent per week,
  fed only the repo as it stood before that Monday's Council report.
- **Forward record** -- `forward.py` and [FORWARD.md](FORWARD.md). Every
  registered design, scored each Monday on weeks it never saw.
- **Scorecard** -- [SCORECARD.md](SCORECARD.md). Every test so far, and how
  each member did in it, on one page (as of 2026-09-22).
- **The Butterfly Net** -- `screen/` (the owner's small and mid-cap setup
  finder, 2026-09-23, named 2026-09-24; see `screen/README.md`). Its
  committed reports are a point-in-time record, each the list for the
  session it is dated, on closes through the session before;
  `screen/reports/runs.json` says when each ran. The Room scores them once
  there are enough days (entry at the session's open, the owner's exits
  beside, against random names from the same screened universe); the
  2026-09-24 report ran mid-session and is not scored. Nothing in the lab
  reads them yet.

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

## Council Room V1 results

Nine fresh agents, one per week. The audit is clean: every agent used only
Read, Grep and Glob, and every file it lists is inside its own folder. Books,
theses and risks are in `results/room_v1_books/`; the snapshot commits are in
`results/room_v1_manifest.json`.

| Week | V1 book | V1 | vs SPY | Pctile vs random | Real Council | Engine replay | SPY |
|---|---|---|---|---|---|---|---|
| 2026-07-20 | UNH 20, PLD 15, SPG 15, MSFT 15, BAC 15 | -0.60% | +0.49 | 32% | -0.36% | +0.21% | -1.09% |
| 2026-07-27 | RTX 20, JNJ 20, JPM 18, NVDA 15, LMT 12 | -1.22% | -1.51 | 18% | -1.52% | +0.61% | +0.28% |
| 2026-08-03 | JPM 16, BMY 16, GOOGL 14, MSFT 12, AMZN 12 | -0.16% | -3.34 | 17% | -0.63% | +0.48% | +3.18% |
| 2026-08-10 | AMGN 20, JPM 20, NVDA 15, ETN 15, AMZN 15 | +0.02% | -0.46 | 20% | +0.00% | -4.75% | +0.48% |
| 2026-08-17 | JPM 20, MRK 20, MSFT 20, LMT 10, CVX 10 | +1.41% | +2.76 | 73% | -2.81% | -2.30% | -1.35% |
| 2026-08-24 | LLY 20, JNJ 20, XOM 15, MSFT 15, NVDA 10 | -1.04% | -1.63 | 24% | -0.05% | -1.33% | +0.60% |
| 2026-08-31 | MSFT 25, JPM 20, MRK 20, AMZN 15, CRM 10 | -0.03% | -0.40 | 56% | +0.02% | -1.09% | +0.37% |
| 2026-09-08 | GILD 16, MDT 14, CVX 14, NVDA 13, WFC 13 | -1.23% | -0.61 | 36% | -0.14% | -1.25% | -0.62% |
| 2026-09-14 | XOM 20, LLY 17, JPM 15, MSFT 15, NVDA 13 | -0.07% | -0.67 | 72% | -0.31% | -0.02% | +0.60% |

| | Mean alpha / wk | vs random | Avg pctile | vs real Council | vs engine replay | Invested | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|
| V1 | -0.60% (t -1.08) | -0.44% (t -1.52) | 39% | +0.32%/wk (5/9) | +0.73%/wk (5/9) | 80% | -2.9% | -2.9% |

**V1 fails the primary test**: it did not beat random picks at its own
weights. By the registered rule it does not earn a forward shadow, and reading
the research this way is not adding selection either.

What it did differently from the engines and the real Council:

- It stayed out of binary events. It held nothing through its own earnings
  except one deliberate NVDA position sized near its SPY weight, and its worst
  week was -1.23%. That, plus five-name diversification, is why its drawdown
  (-2.9%) is a fraction of the replay's (-10.3%) and the
  real Council's (-5.7%). It is risk control, not skill.
- It lived in the megacaps. The median pick ranks 24th of about 270 by dollar
  volume; MSFT and JPM are in 6 of 9 books and NVDA in 5. That is the big-name
  habit the live Council has too.
- *Exploratory, not registered:* against random books drawn only from the 60
  most liquid names, V1 averages the 33rd percentile, so the shortfall is not
  just the megacap style -- its picks within that style lagged as well.

## What nine weeks can and cannot say

V1's weekly alpha has a standard deviation of 1.7 points. With nine
weeks, the standard error of a mean is about 0.6 points a week, so
the room can catch a design that is broken (the replayed engines at -1.32%/wk,
the single-name blowups) but cannot certify a winner. An edge worth having,
+0.5%/wk, needs about 44 weeks to reach t = 2. Until then, what can be
fixed with confidence is what does not need proof of skill: binary-event and
concentration risk.

## Pass 3 -- the leads on weeks the Council never ran (registered before the run)

**Why these weeks.** The three Pass 2 leads came out of the Council's nine
weeks, so those weeks cannot test them. The numeric engines read only prices,
so they can be replayed on any week: here, the 96 weeks before the Council
existed, 2024-09-09 .. 2026-07-06. The Council Room stays on Council weeks,
because an LLM cannot be replayed on weeks it might remember.

**The base is production as of 116300d**, which added the earnings blackout
for all three engines. Every variant runs on top of it, fed the dates the
companies actually reported (announced weeks ahead, so known on the Monday;
BK and PEAK have no dates and, as in production, are never excluded). The
usual caveats apply more strongly over two years: today's universe (names that
left the index are missing), Cecil's value and quality legs neutral (no
point-in-time P/E), wikis neutral.

| Variant | Change |
|---|---|
| base | production as of 116300d, earnings blackout on |
| no-screen | base with the earnings calendar withheld, so the blackout cannot fire (H3) |
| O-last | Ophelia's sector anchor and flow term read the latest completed week instead of the week before it (H2) |
| M-skip | Marky's momentum leg reads his 12-week window up to the close four weeks before the latest, skipping the most recent month, instead of the latest three weeks (H1) |
| O-last+M-skip | both |

**Tests**, computed by `pass3_tests()` rather than judged by eye:

- *H1, short-horizon reversal:* the 3-week return's mean rank IC with the next
  week's return is negative with t <= -2, and the skip-a-month return's IC is
  not negative.
- *H2, the stale anchor:* last week's top sector beats the universe the
  following week on average with t >= 2, and by more than the week-before-last's
  top sector does.
- *H3, the earnings blackout:* reported, not gated -- it is a risk control
  already in production. How often it changed the book, the mean effect, the
  worst week and the drawdown, with and without it.

**Decision rule.** A variant becomes production's default only if all three
hold: its mechanism test passes; its book beats base on the paired weekly
comparison and does no worse against random picks; and the paired improvement
is positive in both halves of the window. Otherwise it stays in the lab.
Everything registered here is also scored forward, each Monday, on weeks that
did not exist when it was registered.

    python lab/engine_lab.py --pass 3

## Pass 3 results

Run after the registration commit (cc501f2); `results/pass3_history.json`.
96 weeks, 2024-09-09 .. 2026-07-06.

| Variant | Alpha / wk | vs random | Pctile | vs base, paired | 1st half | 2nd half | Max DD |
|---|---|---|---|---|---|---|---|
| base | +0.62% | +0.59% | 52% | -- | -- | -- | -14.3% |
| no-screen | +0.52% | +0.49% | 51% | -0.09% (t -0.83) | -0.07% | -0.11% | -15.2% |
| O-last | +0.25% | +0.22% | 45% | -0.37% (t -0.77) | -0.16% | -0.59% | -11.5% |
| M-skip | +0.72% | +0.68% | 52% | +0.10% (t +0.98) | +0.05% | +0.15% | -13.7% |
| O-last+M-skip | +0.35% | +0.31% | 46% | -0.27% (t -0.57) | -0.13% | -0.42% | -9.4% |

**Under the registered rule, no engine change ships.**

- **H1 fails.** The 3-week return's rank IC is -0.013 (t -0.79), negative only in
  the second half (+0.009 / -0.035); the skip-a-month return is flat (+0.002).
  The reversal that ran 8 of 9 Council weeks is not a stable feature of these
  names. M-skip's small, steady book edge (+0.10%/wk, both halves) has no
  mechanism under it, so it stays in the lab and is scored forward.
- **H2 fails.** Last week's top sector lagged the universe the following week
  (-0.10%/wk; it beat the universe 44 of 96 times), and did no better than the
  week-before-last's. The 8-of-9 run in the Council's weeks was chance. O-last
  is worse than base in both halves.
- **H3, the earnings blackout, holds up as the risk control it was shipped as.**
  It changed the book in 53 of 96 weeks, added +0.09%/wk (t +0.83) and trimmed
  the maximum drawdown from -15.2% to -14.3%. On the Council's own weeks it does
  more: the replay's alpha goes from -1.32% to -0.94%/wk and its drawdown from
  -10.3% to -6.2%, mostly by passing over TPR.

**Read the absolute numbers with care.** base shows +0.62%/wk against SPY and
+0.59%/wk against random picks, but the median week is +0.15%, and the best
week (+28.9%, 2024-11-18) came from QUBT and IONQ. Today's universe holds
IONQ, QUBT and RGTI (RGTI is the replay's most-held name) because they ran; a
universe built in 2024 would not have. That flatters any engine that chases
strength, over any window before the universe was drawn up. The registered
tests compare variants and inputs on the same universe, so they are far less
exposed -- and the bias would, if anything, have helped the two momentum leads,
which still failed. BK, MMC, PEAK, AVB, EQR and EA return no price history over
the window and sit out.

**Where this leaves the engines.** Nothing in three passes has found a numeric
input that reliably predicts next week's winners in this universe; what has
held up is risk control -- keeping binary events out of the book. The designs
registered so far keep running forward (below).

## Forward record

`lab/forward.py` scores every registered design on each Council week that
closes after it was registered, next to the real Council's book, and rewrites
[FORWARD.md](FORWARD.md) from scratch. Scheduled task 8 runs it every Monday
after the Council session and commits the result.

    python lab/forward.py

## Pass 4 -- Marky v2, the chart (registered before the run)

Part of Council v2 ([council_v2.md](council_v2.md)): all three members work
from the owner's 111, each with one job. This pass tests Marky's.

**v2** (`marky.MARKY_MODE = "52w"`) reads the last 52 weekly closes (at least
40) and scores three things. Position in the 52-week range is worth 40 points.
Nearness to the 52-week high is worth 30, with none at 80% of the high or
below. Closing above the 40-week average earns 20, plus 10 when that average
is rising. **classic** is today's Marky.

**What is scored.** Each week, Marky's own top five after the earnings
blackout, equal-weighted, against 200 random fives drawn from the same
tradeable names. Also each input's rank IC with the next week's return.

- *history:* the 96 pre-Council weeks on the frozen universe -- the mechanism
  test.
- *council:* the Council's closed weeks on the owner's 111 -- the universe v2
  will use. Informational only: nine weeks, and the list itself has look-ahead.
- *leans:* each mode's rank correlation with a stock's 12-week volatility (a
  preference for a calm tape is Cecil's job) and with its 3-week return (the
  input that ran backwards in Pass 2).

**Decision rule: non-inferiority.** v2 is a design choice -- distinct jobs --
not a claim that it predicts better, and neither mode has shown selection skill.
So v2 replaces classic in Council v2 unless the history shows it is worse:
either its nearness-to-high IC is negative with t <= -2, or its top five trail
classic's on the paired weekly comparison with t <= -2.

    python lab/pass4_marky.py

## Pass 4 results -- Marky v2

Run after the registration commit (6f10700); `results/pass4_marky.json`. Marky's
own top five each week, equal-weighted.

| | Weeks | classic: alpha / wk | vs random (pctile) | 52w: alpha / wk | vs random (pctile) | 52w minus classic |
|---|---|---|---|---|---|---|
| History, frozen universe | 96 | -0.37% | -0.42% (t -2.05; 42%) | +0.13% | +0.07% (t +0.21; 51%) | +0.50%/wk (t +1.43), 54/96, both halves positive |
| Council weeks, the 111 | 9 | -0.82% | -0.57% (38%) | -1.96% | -1.70% (t -2.90; 23%) | -1.14%/wk (t -1.57), 2/9 |

**Under the registered rule, Marky v2 goes into Council v2.** Neither harm
condition is met: nearness to the high has an IC of -0.009 (t -0.42), not
significantly negative, and v2's five beat classic's over the 96 weeks.

**What this does and does not show.**

- *Neither mode predicts next week.* Every input's IC is within noise of zero
  in both samples. Classic's own five trailed random picks over 96 weeks (t
  -2.05); v2's matched random.
- *The history result is flattered.* v2's most-picked names over 2024-26 were
  MU, AVGO, GEV and NVDA: stocks that sat near their highs and are in today's
  universe because they kept running. A 52-week-high rule profits most from
  that look-ahead.
- *The Council's weeks point the other way.* On the owner's 111, v2's picks
  were large caps near their highs (JPM, CRWD, VLO, KO, SCHW) that pulled back.
  That is the same pattern that sank short-term momentum in Pass 2.
- *v2 is more distinct but not fully.* Its link to the 3-week return halves
  (+0.81 -> +0.43), so it chases short-term strength far less. It still leans
  toward calmer stocks (-0.19, the same as classic's -0.17), because stocks near
  their highs tend to be calmer.

So the case for v2 is the job it gives Marky, not better picks. The forward
record will keep scoring both.

## Council Room v2 -- Ophelia's passes and Cecil's (registered before any agent ran)

These are the Council v2 jobs that need reading ([council_v2.md](council_v2.md)),
tested on the Council's closed weeks. Each pass is a fresh agent that sees only
its own folder, which `council_room_v2.py` builds from the repo as it stood
before that Monday's report. It gets the previous pass's answer in its prompt.
The prompts are in `council_room_v2_prompts.md`; they are identical every week
apart from dates, paths and that previous answer.

- **Ophelia.** Pass 1 turns the Market Brief into 4 sectors. Pass 2 reads the
  canary watch, the economic calendar and the light sector reads, and settles a
  final 4. Pass 3 takes the 40 stocks plus BTC and GLD and picks 5.
- **Cecil.** He reads `synthesis.md` and his value table and picks 5.
- **Marky.** His five come from Pass 4 (52w).

**What is scored.** Each member's five, equal-weighted, against random fives
drawn from the 111's tradeable names. Ophelia's sector call on its own: her
final four sectors' stocks against all the 111's stocks, the next week. And how
often the members pick the same names.

**What counts.** The jobs are the owner's design, so this is a check for
breakage, not proof; nine weeks cannot prove skill. A member whose five trail
random picks with t <= -2 is flagged to the owner, with its cause, before
Council v2 goes live. By that standard Marky v2's Council weeks (t -2.90 in
Pass 4) are already flagged. Everything else goes live as designed and onto the
forward record.

    python lab/council_room_v2.py build DIR     # the week folders
    python lab/council_room_v2.py pass3 DIR     # after pass 2
    python lab/council_room_v2.py score DIR

## Pass 5 -- Marky v3, the pullback (registered before the run)

The owner revised Marky's job: buy stocks near the bottom of a rising channel,
with MACD insight (`marky.MARKY_MODE = "channel"`, specified in
[council_v2.md](council_v2.md)). A 26-week least-squares channel through log
closes; only names whose channel slopes up and whose 40-week average is rising
qualify, and a close more than 2.5 widths below the line is a broken channel,
not a pullback. Position below the line is worth 50 points (full at 1.5 widths
down), slope 20 (full at +30% a year), weekly MACD(12, 26, 9) 30 (20 for a
rising histogram, 10 for the MACD line above zero). The constants were set
before the run and none was tuned.

Scored exactly as Pass 4, on the same two samples, with classic and 52w
alongside:

    python lab/pass4_marky.py --modes classic,52w,channel --target channel \
        --signal position_score --out pass5_marky.json

**Decision rule: the same non-inferiority as Pass 4.** The channel mode is
Council v2's Marky unless the history shows it is worse: either its position
signal's IC is negative with t <= -2, or its top five trail classic's on the
paired weekly comparison with t <= -2. Its Council weeks get the Council Room v2
breakage check: trailing random picks with t <= -2 is flagged to the owner with
its cause.

Why it might work, stated before the run: it buys short-term weakness inside a
longer uptrend, which is the shape of the one pattern the diagnostics kept
finding -- recent winners falling back (Pass 2, 8 of 9 weeks) -- while
refusing names whose trend has broken. Pass 3 found that reversal weak over 96
weeks (IC -0.013), so a large effect is not expected.

## Pass 5 results -- Marky v3, the pullback

Run after the registration commit (8c1241c); `results/pass5_marky.json`. Marky's
own top five each week, equal-weighted.

| | Weeks | classic | 52w | channel | channel minus classic |
|---|---|---|---|---|---|
| History, frozen universe: alpha / wk | 96 | -0.37% | +0.13% | +0.27% (t +1.07) | +0.64%/wk (t +1.69), 55/96, both halves positive |
| History: vs random (pctile) | | -0.42% (42%) | +0.07% (51%) | +0.21% (t +0.79; 53%) | |
| History: worst drawdown | | -13.7% | -19.8% | **-28.0%** | |
| Council weeks, the 111: alpha / wk | 9 | -0.82% | -1.96% | +1.35% (t +1.83) | +2.18%/wk (t +1.77), 8/9 |
| Council weeks: vs random (pctile) | | -0.57% (38%) | -1.70% (23%) | **+1.61% (t +2.10; 75%)** | |

**Under the registered rule, the channel mode is Council v2's Marky.** Neither
harm condition is met, and it leads classic in both samples. It is also the
first design in any pass to beat random picks on the Council's own weeks.

**Read it with four caveats.**

- *The idea partly came from these weeks.* The pullback job buys the pattern the
  Pass 2 diagnostics found in these same nine weeks: recent winners falling back.
  Its Council-week result is flattered accordingly.
- *Over 96 weeks its edge over random is small and not significant*
  (+0.21%/wk, t +0.79), and no input predicts the next week (every IC within
  +/-0.01).
- *It is the most volatile of the three.* Its worst history drawdown is -28%,
  against classic's -14%: pullbacks in steep uptrends are often in volatile
  names.
- *The MACD leg has not earned its 30 points.* On the Council weeks its score
  ran against the next week's return (IC -0.119, t -2.37); the depth of the
  pullback did the work. It stays as specified -- re-weighting it on these weeks
  would be tuning to them -- and the forward record will show whether it helps.

It is genuinely a different job. Its ranking has no preference for a calm tape
(+0.05, against classic's -0.17), and it leans away from short-term strength
(-0.31, against classic's +0.81).

## Council Room v2 -- the debate (registered before any debate agent ran)

The owner's design for how three separate jobs become one book
([council_v2.md](council_v2.md)): the members' fives and reasoning (the debate
logs) go to a synthesis agent. It drafts the book: up to 5 names, 5-30% each,
at least 80% invested, plus two alternates. Each member then approves or
objects to each name in its own fresh pass, seeing only its own lens. A name
two of the three object to is swapped for an alternate. Prompts are in
`council_room_v2_prompts.md`.

**What is scored.** The final book at its weights, against random books drawn
at the same weights from the 111's tradeable names. Alongside it: the draft
before approval (did the vote help?), the real Council's book, and SPY.

**What counts.** The same breakage standard as the members: a final book that
trails random picks with t <= -2 is flagged to the owner with its cause before
Council v2 goes live. Nine weeks cannot prove the debate adds skill; the
forward record will.

    python lab/council_room_v2.py debate DIR
    python lab/council_room_v2.py approve DIR
    python lab/council_room_v2.py final DIR

## Council Room v2 results -- the members

Run after the registration commit; `results/room_v2_members.json`. Every agent
output is in `results/room_v2/`, one folder per week, with the `files_read`
paths shortened to the week folder. By their own reports, all 72 agents in this
room (36 member passes, 9 drafts, 27 votes) used only Read and opened nothing
outside their own folder.

One departure from the registration: Marky's five are the channel mode's
(Pass 5), not Pass 4's 52w. The owner replaced the 52w job before this ran, and
the channel mode passed its own registered rule.

| Member | Weeks | Alpha / wk | vs random (t) | Pctile |
|---|---|---|---|---|
| Ophelia | 9 | -0.45% | -0.27% (t -0.41) | 45% |
| Cecil | 9 | +0.10% | +0.41% (t +0.56) | 57% |
| Marky (channel) | 9 | +1.35% | +1.61% (t +1.91) | 75% |

Ophelia's four sectors, against all the 111's stocks the next week: -0.18%/wk
(t -0.59), ahead in 3 of 9. No member trails random picks with t <= -2, so none
is flagged.

The jobs are distinct. Over the nine weeks Ophelia and Cecil picked the same
name 7 times, Ophelia and Marky twice (both on 09-14), and Cecil and Marky
never.

## Council Room v2 results -- the debate

Run after the registration commit; `results/room_v2_debate.json`, with each
week's draft, votes and final book in `results/room_v2/`.

| | Weeks | Alpha / wk | vs random (t; pctile) | Invested | Cumulative | Worst DD |
|---|---|---|---|---|---|---|
| Draft, before the vote | 9 | -1.15% (t -1.99) | -0.94% (t -1.43; 40%) | 95% | -7.7% | -8.9% |
| Final, after the vote | 9 | -1.14% (t -1.98) | -0.89% (t -1.40; 40%) | 95% | -7.6% | -8.8% |

Against the real Council's book, the final book returned -0.86%/wk (t -1.72)
and did better in 3 of 9 weeks.

| Week | Final book | Book | SPY | Council |
|---|---|---|---|---|
| 07-20 | UNH 30, JPM 25, MA 15, SPG 15, VLO 10 | +0.20% | -1.09% | 0.00% |
| 07-27 | LMT 30, JNJ 25, JPM 20, LNG 15, TMO 10 | -0.75% | +0.28% | -0.14% |
| 08-03 | JPM 30, REGN 25, KO 20, SCHW 15, PEP 10 (swapped in for UNH) | +0.58% | +3.18% | +0.34% |
| 08-10 | NVDA 25, GOOGL 20, ETN 20, FCX 15, LLY 15 | -1.17% | +0.48% | 0.00% |
| 08-17 | NVDA 20, AMD 20, LMT 20, GS 20, COP 15 | -2.97% | -1.35% | +0.13% |
| 08-24 | REGN 30, LLY 20, COP 20, PGR 15, PEP 15 | -3.91% | +0.60% | -0.40% |
| 08-31 | JPM 30, PM 20, V 15, UNH 15, REGN 10 | -0.16% | +0.37% | 0.00% |
| 09-08 | JNJ 25, JPM 25, VLO 15, PGR 15, NVDA 10 | -0.70% | -0.62% | -0.14% |
| 09-14 | XOM 30, LLY 20, AMD 15, JPM 15, PGR 10 | +1.06% | +0.60% | +0.16% |

**Under the registered standard, the final book is not flagged**: it trails
random picks with t -1.40, and the line is -2. It is negative on every
measure, though, and on average it did worse than each member's five on their
own.

**The vote barely acts.** Of 135 votes, 21 were objections (Marky 11, Cecil 8,
Ophelia 2). Two members objected to the same name only once: UNH on 08-03,
by Cecil and Marky. It was swapped for PEP, which added +0.10% that week; the
other 19 objections stand as dissents. Each member objects through its own
lens, and the lenses rarely coincide, which is the other side of giving them
distinct jobs.

Cash ran 0-10% (5% on average), well inside the owner's 20% cap.

**What went wrong -- post hoc, not a registered test.**

- *The synthesis gave the best member here almost no say.* On average,
  Ophelia's five made up 67% of the final book, Cecil's 47% and Marky's 8%
  (a name two members picked counts for both). Each member's five returned, on
  average, -0.17%/wk (Ophelia), +0.38% (Cecil) and +1.63% (Marky). The drafts
  dropped Marky's names for failing the other members' tests ("not in
  Ophelia's sectors", "not cheap by Cecil's measures"), and Marky writes no
  prose to argue back.
- *The objections did not pick losers.* Names a member objected to returned
  +0.12%/wk against SPY; names it approved returned -1.27%. A stronger veto
  would have hurt.
- *None of this identifies a better way to combine them.* It is nine weeks, and
  Marky's lead is partly in-sample (Pass 5's first caveat); over 96 weeks his
  edge over random is +0.21%/wk (t +0.79).

**Open for the owner:** whether the synthesis step goes live as designed, or
with a fixed share of the book for each member so every job counts. The forward
record will score whichever goes live.

## Council Room v2.1 -- every job holds a seat (registered before any agent ran)

The owner handed this call to the lab. Three things in v2's book step leaned
against Marky, and none of them needs the members to change:

- *The logs.* Ophelia's and Cecil's fives came with their own reasoning;
  Marky's were introduced as "a numeric screen" that "writes no prose".
- *No rule about whose test applies.* The drafts dropped his pullbacks for
  failing Ophelia's sectors or Cecil's prices.
- *No rule that every job counts.* One job could be shut out entirely, and one
  nearly was.

v2.1 changes the book step only. The members' fives are v2's, unchanged.

- **Fair logs.** Every member's section states its job. Marky's five carry his
  case in words, from his own numbers: how far below the channel line, how
  steep the channel, what weekly MACD is doing. His method is written out.
- **Judge each name by its backer's job.** A value pick on whether it is cheap
  and sound, a sector pick on whether it expresses the call, a chart pick on
  whether it is a pullback in a rising channel. No name is dropped for failing
  another member's test.
- **Every job holds a seat** (variant C only). Each member's picks hold at least
  20% of the book; a name two members picked counts for both. The synthesis
  names one alternate per member. A name two members vote down is replaced by
  an alternate from a member who picked it, so the vote can change a job's name
  but not silence the job. If no alternate keeps every member at 20%, the name
  stays and the objections become dissents.

Two variants, each a fresh synthesis agent per week on the same logs, in
separate folders so neither can see the other's answer:

- **B, fair framing only** -- a draft, no vote. Does the framing alone give each
  job a fair share?
- **C, v2.1** -- a draft, the three members' votes (v2's approval prompt, word
  for word), and the final book by rule. The design proposed for go-live.

**What is scored.** Each member's share of every book: v2's, B's and C's. B's
draft, C's draft and C's final book, as v2's were: against random books at the
same weights, against SPY and against the real Council. And C's final against
v2's final, paired by week.

**What counts.**

- *v2.1 replaces v2's book step* unless its final book trails random picks
  with t <= -2, or more than one of its nine drafts breaks a rule: more than 5
  names, a weight outside 5-30%, under 80% invested, a member under 20%, a name
  reporting that week, or alternates that are not one per member.
- *The framing alone fixed it* if under B every member holds 20% or more on
  average, and all three do in at least 7 of the 9 weeks. Either way C goes
  live, with the floor as a backstop.
- *Returns decide nothing here.* The tweak was designed after seeing Marky's
  five do best on these weeks, so B's and C's returns are flattered, and they
  are reported only for completeness. The shares are a fair measurement: the
  agents are fresh and cannot see outcomes. The forward record decides whether
  v2.1 earns its place.

    python lab/council_room_v2.py debate21 DIR
    python lab/council_room_v2.py approve21 DIR
    python lab/council_room_v2.py final21 DIR

## Council Room v2.1 results -- every job holds a seat

Run after the registration commit (2d9179d); `results/room_v21_debate.json`,
with every v2.1 draft, vote and final book in `results/room_v2/`. By their own
reports, all 117 agents in the room (v2's 72 and v2.1's 45) used only Read and
opened nothing outside their folders. One draft (B, 09-14) came back with a
stray closing brace; it was removed, and the file notes the repair.

**Under the registered rule, v2.1 replaces v2's book step.** None of the 18
drafts broke a rule, and the final book trails random picks with t -0.53, well
clear of the -2 line.

**The shares -- the clean measure.** Each member's picks as a share of the
book. A name two members picked counts for both, so a row can add to more than
100%.

| Book | Ophelia | Cecil | Marky | All three at 20%+ |
|---|---|---|---|---|
| v2, final | 67% | 47% | 8% | 2 of 9 weeks |
| B, fair framing only | 54% | 49% | 22% | 4 of 9 |
| C, v2.1, final | 51% | 47% | 23% | 9 of 9 |

**The framing alone did not fix it.** Fair logs and the backer's-job rule
nearly tripled Marky's average share, but in 5 of the 9 weeks a member still
held under 20%. The floor does real work; it is not just a backstop.

**The vote now acts, and it cannot silence a job.** Of 135 votes, 22 were
objections (Marky 10, Cecil 9, Ophelia 3). Three names drew two: CAT on 07-20
(Ophelia, Cecil) went to Marky's alternate EQIX; PGR on 08-10 (Ophelia, Marky)
to Cecil's alternate JPM; UNH on 08-24 (Ophelia, Cecil) to Marky's alternate
D. The floor blocked none, and 16 objections stand as dissents. The swaps
added +0.13%/wk on average. As in v2, the names objected to did not do worse
than the names approved: -0.47%/wk against SPY, against -0.74%.

| Week | v2.1 final book | Book | v2 book | SPY |
|---|---|---|---|---|
| 07-20 | UNH 30, JPM 20, EQIX 20 (for CAT), VLO 15, SPG 10 | +1.05% | +0.20% | -1.09% |
| 07-27 | LMT 30, CAT 20, JNJ 20, PGR 20, COP 10 | -1.91% | -0.75% | +0.28% |
| 08-03 | JPM 30, REGN 25, UNH 20, PEP 15, SCHW 10 | +0.25% | +0.58% | +3.18% |
| 08-10 | NVDA 25, CAT 25, GOOGL 20, JPM 15 (for PGR), FCX 10 | -0.37% | -1.17% | +0.48% |
| 08-17 | VLO 22, PGR 22, MOD 20, NVDA 18, GS 18 | -0.72% | -2.97% | -1.35% |
| 08-24 | REGN 30, D 20 (for UNH), LLY 15, PGR 15, COP 10 | -3.24% | -3.91% | +0.60% |
| 08-31 | JPM 30, UNH 20, PGR 15, META 15, PM 10 | +1.05% | -0.16% | +0.37% |
| 09-08 | JNJ 25, PGR 20, CAT 20, CVX 15, LMT 15 | -0.57% | -0.70% | -0.62% |
| 09-14 | XOM 30, AMD 20, LLY 15, PGR 15, CAT 10 | +2.15% | +1.06% | +0.60% |

**Returns -- flattered, and reported only for completeness.**

| | Alpha / wk | vs random (t; pctile) | Cumulative | Worst DD |
|---|---|---|---|---|
| v2, final | -1.14% (t -1.98) | -0.89% (t -1.40; 40%) | -7.6% | -8.8% |
| B, draft | -0.53% (t -0.75) | -0.29% (t -0.46; 45%) | -2.4% | -4.9% |
| C, v2.1 draft | -0.66% (t -1.08) | -0.43% (t -0.69; 44%) | -3.5% | -6.0% |
| C, v2.1 final | -0.53% (t -0.77) | -0.36% (t -0.53; 47%) | -2.4% | -5.9% |

v2.1's final book beat v2's in 7 of 9 weeks (+0.61%/wk, t +1.88). It trailed
the real Council's book by 0.25%/wk (t -0.50), ahead in 3 of 9. The
registration said this comparison decides nothing: v2.1 was designed after
seeing Marky's five do best on these weeks, so moving weight toward him was
bound to help here. What survives that caveat is narrower. v2.1 is no worse,
it seats every job every week, and its book is still indistinguishable from
random picks, as every design in this lab has been. The forward record
decides whether it earns more.

## Spot check -- do the picks keep working after their week? (registered before computing)

The owner's questions: how did a week's picks do a month later, and the
following week? They test an idea from the lab's list: the members' jobs are
slow signals (value over months, sector rotation over weeks to months, a
pullback over several weeks), so judging and replacing them every week may
measure mostly noise.

`hold_check.py` scores every set of Council Room picks -- each member's five,
all fifteen together, the v2.1 book and the real Council's book -- over three
windows: the week it was picked for (Monday open to Friday close), the
following week (still holding: Friday close to the next Friday close), and the
month (Monday open to the fourth Friday's close). Each is measured against SPY
and against random books of the same size and weights from the 111, as in the
Room. The following week has closed for eight Council weeks (07-20 to 09-08),
the month for six (07-20 to 08-24).

**The prediction, if the jobs are slow signals:** holding on does not give the
edge back. Across the sets, the following week's edge over random is not
negative on average, and the month's edge per week is at least the first
week's.

**What counts.** This is a spot check, not a test. Eight start weeks, and six
months that overlap by three weeks each -- about one and a half independent
months -- cannot confirm anything. They can embarrass the idea: if the picks
clearly give back their gains the following week, or the month runs well
behind the first week, weekly re-picking is not the problem, and the 96-week
history test should come before any change to how long the Council holds.

    python lab/hold_check.py

## Spot check results -- the picks do not keep working

Run after the registration commit (b4b215f); `results/hold_check.json`, with
every pick's three returns. Edge over random picks of the same size and
weights, averaged over the weeks each window has closed:

| Picks | Week 1 | Week 2, still holding | Month, per week |
|---|---|---|---|
| Ophelia's five | -0.29% (5 of 9 ahead) | +0.44% (5 of 8) | -0.05% (1 of 6) |
| Cecil's five | +0.36% (5 of 9) | +0.26% (5 of 8) | -0.05% (3 of 6) |
| Marky's five | +1.56% (8 of 9) | -1.51% (3 of 8) | -0.40% (1 of 6) |
| All fifteen | +0.57% (5 of 9) | -0.30% (4 of 8) | -0.08% (3 of 6) |
| v2.1 book | -0.32% (4 of 9) | -0.30% (4 of 8) | -0.38% (1 of 6) |
| Real Council | -0.02% (3 of 6) | -0.12% (2 of 5) | -0.33% (1 of 4) |

**Under the registered reading, the idea is embarrassed.** The following
week's edge is negative for four of the six sets, and the month's edge per week
trails the first week's for five of the six. Weekly re-picking is not what
holds the picks back, and nothing here says the Council should hold longer.

**Marky's edge is a bounce, not a trend.** His five beat random by 1.56% in
their week and gave back 1.51% the next. On 08-10, MOD, AMD and DDOG rose 6-11%
and then fell 6-8%. If his screen works at all, it works for a week, and
holding his picks longer would hurt.

**The month's big winners belonged to the market, not the picks.** From 07-27,
NEM (+38.7%) and COP (+15.8%) look like proof on their own. Random books from
the same 111 rose too, and the picks as a whole ended the month behind them.

**One pattern held in every window:** all fifteen names together did at least
as well as the five-name v2.1 book (week 1 +0.57% against -0.32%, week 2 level,
month -0.08%/wk against -0.38%/wk). Six to nine weeks prove nothing, but it
points the same way as the noise measurement: cutting fifteen names to five has
not earned its keep.

## Spot check 2 -- Ophelia a week late, and the bottom three (registered before computing)

Two what-ifs from the owner:

- **Ophelia a week late.** Hold her five in the week after she picks them. On
  the Council weeks this is her week-2 result, already seen above (+0.44%/wk
  against random), so these weeks cannot test it; only the forward record can.
  It is scored here only so that the combined book can be.
- **The bottom three.** Each member's three lowest-ranked picks, nine in all,
  become the candidates for the final five. Marky ranks by score. Ophelia and
  Cecil were never asked to rank, so the order they listed their picks stands
  in, a rough proxy. The nine are scored equal-weighted, which is what picking
  five of them at random would earn on average.

**Measured.** On the eight Council weeks that have a week before them (07-27
to 09-14): each member's bottom three against its top two, and the nine-name
pool (Ophelia's bottom three from the week before, Cecil's and Marky's from the
week itself) against random nine-name books and against all fifteen. On
history, the one part that can be tested properly: Marky's #3-#5 against his
#1-#2 over Pass 5's 96 pre-Council weeks, paired by week, since his ranking is
mechanical.

**The prediction:** the ordering carries no information. Marky's score
predicted nothing over 96 weeks (every IC within +/-0.01 in Pass 5), and the
other two never ranked. The bottom three should do about as well as the top
two, and the pool about as well as random.

**What counts.** Only the 96-week Marky comparison is a test: his bottom three
beat his top two only if the paired gap has t >= 2. The Council-week numbers
are a spot check, as above.

    python lab/whatif_check.py

## Spot check 2 results

Run after the registration commit (614ee92); `results/whatif_check.json`.
Council weeks (07-27 to 09-14), edge over random books of the same size:

| Picks | Per week | Weeks ahead of random |
|---|---|---|
| Ophelia: top two / bottom three | -0.73% / -0.44% | 2 / 3 of 8 |
| Cecil: top two / bottom three | +0.29% / -0.02% | 4 / 4 of 8 |
| Marky: top two / bottom three | +3.64% / +0.12% | 6 / 6 of 8 |
| Ophelia a week late, all five | +0.36% | 5 of 8 |
| The nine: her bottom three a week late, the others' bottom three | +0.52% (t +1.08) | 6 of 8 |
| All fifteen | +0.34% (t +1.40) | 4 of 8 |

**The one real test says the order means nothing.** Over Pass 5's 96 history
weeks, Marky's #3-#5 minus his #1-#2 came to -0.11%/wk (t -0.31), with the
bottom three ahead in 43 of 96 weeks. As predicted, where a name sits in his
five carries no information, in either direction.

**The nine post the best number any design has on these weeks, and have the
least claim to it.** Half of the pool is Ophelia a week late, the very result
the idea was read off. The bottom-three half does not hold on history, and on
the Council weeks Cecil's and Marky's bottom three trailed their top two.
Nothing here separates the nine from luck.

**Ophelia a week late costs nothing to keep score of.** Her five exist every
week, so holding last week's five is a book the forward record can score
without running anything new. That is the only fair test it can get.

## Live week 2026-09-21 -- the fifteen, recorded before the week closed

The owner's first live run of Council v2's members, with Ophelia a week late.
Every input ends at Friday 2026-09-18's close. Cecil read the repo as it
stood before Monday's Council report, and Marky's screen ran on prices capped
at that Friday. The picks were committed Monday at 19:08 ET, after that day's
session had closed. Nothing that chose them could see Monday, but a clean
forward test should start after the record. So `live_week.py score` scores
two windows to Friday 09-25's close: from Monday's open, like every other
score in the lab, and from Tuesday's open. The record is
`results/live/2026-09-21.json`.

| Member | This week's five |
|---|---|
| Ophelia (her 09-14 run, held a week late) | XOM, COP, VLO, AMD, LLY |
| Cecil | GOOGL, PGR, GS, LNG, REGN |
| Marky (channel, as registered) | GS, LYV, GE, JPM, WELL |
| Marky with MACD turning up (the owner's reading, a variant) | CAT, CRWD, AMD, TSM, MTCH |

GS was picked twice, so the fifteen are fourteen names. No name reports
earnings this week. Marky's registered five are all deep pullbacks whose weekly
MACD has not turned. The owner expected crossovers, but only three of 108
stocks crossed their weekly MACD signal line on 09-18 (RGTI, OKLO, TSLA), all
inside falling channels. The variant therefore takes the qualifying names
whose histogram turned up. For comparison, the real Council booked XOM, AMD
and HIG with 47.8% cash.

**The owner's picks**, added Monday evening: RGTI, OKLO and TSLA, the three
crossovers. All three sit in falling channels (-16%, -67% and -23% a year), so
they fail Marky's rising-channel test and would be a different job: buying the
bounce in a downtrend. They were named after the session by someone who could
have seen it, so they count only from Tuesday's open.

**Does Ophelia weigh BTC, GLD and COIN?** BTC and GLD are on her pass-3 sheet
every week, and she discussed both in all nine weeks and passed each time,
always with a reason: both in 12-week downtrends, gold "stretched after a +7%
week", a one-week +22.5% bitcoin jump "that none of my sectors explain", or a
Fed hike ahead. COIN was on her sheet in the five weeks Financials made her
four, and she never mentioned it.

## Nuggets A -- four cheap questions (registered before computing)

From the owner's ranked review. All four use data already on hand, and no
agent runs. `nuggets_a.py`.

1. **Separate member books.** Each member keeps a third of the book, split
   equally over its own five, and nothing is blended; a name two members picked
   gets both slices. Scored like the spot check (week 1, week 2, month) against
   random books of the same weights, beside the v2 and v2.1 books, all fifteen
   and the real Council. *Prediction:* close to all fifteen, and ahead of the v2
   and v2.1 books at week 1, as all fifteen was. That is the same nine seen
   weeks, so it decides nothing here. It is a candidate for the forward record.
2. **Shapley credit.** For each week, the value of a coalition of members is
   its separate-books book's edge over random. With three members that is
   seven books, and each member's Shapley value is its average marginal
   contribution; the three values add up to the full book's edge. Reported at
   week 1 and week 2. *Prediction:* Marky carries the largest share at week 1
   and gives it back at week 2. This is credit assignment on seen weeks, a
   description rather than a test.
3. **Does a member's edge carry over?** On the 96 pre-Council weeks, the
   engine-era members (Cecil, Marky and Ophelia as the engines ran them, from
   a fresh baseline replay with capture) and Marky's channel mode (Pass 5):
   each week's edge over the equal-weighted universe, its lag-1
   autocorrelation, and whether the trailing 8 weeks' mean edge predicts the
   next week's. The same two for each member's weekly hit rate, the share of
   its picks that rose, which is what the live consensus weights its votes by.
   *Prediction:* no persistence (every r within +/-0.2, every t within +/-2).
   *What counts:* persistence is real for a member only if a correlation
   reaches t >= 2. If none does, weighting members by their track record has
   nothing to work with, and the live consensus should weight them equally.
4. **The strikes, both ways.** Both vote rounds (v2 and v2.1, 270 votes): for
   each member's objections, the week-1 return of the names it objected to
   minus the names it approved in the same draft, per week, pooled and by
   member. *Prediction:* no signal either way. *What counts:* a veto signal
   needs the gap at t <= -2, a contrarian one at t >= 2. The two rounds share
   most of their names, so they are not independent.

    python lab/nuggets_a.py

## Nuggets A results

Run after the registration commit (7089a8d); `results/nuggets_a.json`.

**1. Separate member books behave like all fifteen, as predicted.** Edge over
random, per week (weeks ahead of random):

| | Week 1 | Week 2 | Month, per week |
|---|---|---|---|
| Separate books | +0.58% (5 of 9) | -0.23% (4 of 8) | -0.18% (2 of 6) |
| All fifteen | +0.53% (5 of 9) | -0.22% (4 of 8) | -0.10% (3 of 6) |
| v2 book | -0.91% (3 of 9) | +0.25% (7 of 8) | -0.55% (1 of 6) |
| v2.1 book | -0.37% (4 of 9) | -0.35% (4 of 8) | -0.34% (1 of 6) |
| Real Council | +0.01% (3 of 6) | -0.14% (2 of 5) | -0.33% (1 of 4) |

They beat both synthesis books at week 1 and over the month. These are the
same nine seen weeks, so the design goes to the forward record, not live.

**2. Shapley credit puts a number on the dilution.** At week 1, the full
separate book's +0.53%/wk splits as Ophelia -0.37%, Cecil +0.02% and Marky
+0.89%: the member v2's synthesis gave 8% of the book produced more than all
of the edge. Week 2 turns it around: Ophelia +0.42%, Cecil +0.36%, Marky
-0.99%.

**3. No member's edge carries over, so weighting by track record has nothing
to work with.** Over the 96 weeks, each member's weekly edge has a lag-1
autocorrelation between -0.16 and +0.02, and the trailing eight weeks predict
the next week with r between -0.18 and -0.03. No t reaches +2. Hit rates, which
the live consensus weights its votes by, are no better. The one significant
correlation is negative: Cecil's trailing-8 hit rate against the next week,
r -0.30 (t -2.94, overstated because the windows overlap), so a good stretch
was followed by a worse week. Under the registered rule, the live consensus
should weight the members equally.

A number that looks like an edge and is not: the engine-era Ophelia averaged
+1.56%/wk against the equal-weighted universe (t +2.05). Ten names carry 110%
of it, led by RGTI, QUBT, IONQ and QBTS, quantum names that exploded and sit
on the frozen list because they did. Without those ten it is -0.21%/wk. This
is the universe's hindsight, the caveat on every history result here, at full
strength.

**4. The strikes carry no signal either way.** Objected minus approved across
35 member votes: +0.75% (t +0.96), with the objected names ahead in 19 of 35.
By member: Marky +1.17% (t +1.15), Ophelia +0.66%, Cecil +0.36%. As in the
earlier reads, the objections lean the wrong way for a veto, but none reaches
the line.

## Pass 7 -- combos and a fourth chair (registered before any run)

The owner asked for creative combinations, a fourth chair, or new jobs. Five
designs follow, all mechanical so that the 96 pre-Council weeks can judge
them, and each grounded in something the lab found today. `pass7_combos.py`
has the exact rules.

- **Dash, a fourth chair: post-earnings drift.** Dash buys names whose
  market-adjusted earnings reaction (from the close before the report to the
  close of the next session) was in the top fifth of the reactions in the six
  weeks before the hold, largest first. It is the mirror image of the
  earnings blackout, the one control that held up here, and the
  best-documented short-horizon effect in the research. Tested alone, against
  random.
- **Quality pullback, Cecil as gatekeeper.** Marky's pullback ranking, keeping
  only names that pass a value screen: positive and growing trailing EPS, and
  P/E at or below the week's median. Two jobs combined rather than blended.
  Against Marky alone.
- **Relay.** Half the book is Marky's five in their own week, and half is
  Ophelia's five from the week before, so each signal runs at the horizon
  where it seemed to live (Marky's edge was a one-week bounce; Ophelia's picks
  did better in the following week). Against the same two members held in the
  same week.
- **Four chairs.** Separate books with a quarter each for Ophelia, Cecil,
  Marky and Dash. Against three chairs with a third each. Does a fourth,
  unrelated job add anything?
- **The Warden, a chair that sizes instead of picking.** It takes the four
  chairs' names, weights them by inverse 12-week volatility, allows at most
  two a sector, and books 80% invested (the cash cap's floor) when SPY closed
  below its 40-week average. This is nuggets 6, 7 and 8 as one job. Against
  four chairs.

On history, Ophelia and Cecil are the engines as they ran (from a baseline
replay), and Marky is the channel screen with its full ranking recomputed. On
the Council weeks, Ophelia and Cecil are the Council Room v2 agents' fives,
and the universe is the 111.

**The guard against hindsight.** The frozen list holds names that are on it
because they ran; ten of them carried the engine-era Ophelia's whole history
edge. So the primary measure clips each name's weekly return to +/-20%, and
the raw measure is reported beside it.

**Predictions.** Dash: positive but short of t 2, since the drift has faded in
large caps. Quality pullback: close to Marky alone, with a calmer book.
Relay: close to its baseline, since the lag effect was read off seen weeks.
Four chairs: close to three. The Warden: a lower weekly SD and a shallower
drawdown by construction, with about the same edge.

**What counts** (history only; the Council weeks are reported and decide
nothing):
- Dash, Quality pullback, Relay and Four chairs are *promising*, meaning
  candidates for the next quarterly change, only if the clipped edge (over
  random for Dash, over its baseline for the others, paired by week) is
  positive with t >= 2 and both halves are positive.
- The Warden is promising if it cuts the weekly SD of the book by at least 10%
  and the worst drawdown against four chairs, while its paired edge stays
  above t -2.
- Deflation (nugget 11): with four designs at the t >= 2 line, a pass by luck
  somewhere is about a one-in-ten chance. Anything promising goes to the
  forward record before it touches the live book, and the change freeze
  applies.

    python lab/pass7_combos.py

## Pass 7 results

Run after the registration commit (345bfcd); `results/pass7_combos.json`. The
recomputed Marky ranking matched Pass 5's picks in every week. History, 96
weeks, clipped edge over random per week:

| Book | Edge (t) | Weeks ahead | Weekly SD | Worst drawdown | Against its baseline |
|---|---|---|---|---|---|
| Dash alone | -0.10% (-0.29) | 45 of 96 | 4.54% | -30.1% | (random) |
| Quality pullback | +0.13% (+0.65) | 55 | 2.83% | -23.9% | -0.08%/wk (t -0.33) |
| Relay | +0.39% (+1.40) | 58 of 94 | 4.40% | -22.8% | -0.20%/wk (t -0.74) |
| Four chairs | +0.23% (+1.31) | 44 | 3.06% | -18.3% | -0.10%/wk (t -1.19) |
| The Warden | -0.07% (-0.58) | 40 | 1.58% | -8.7% | -0.30%/wk (t -1.67) |
| *Marky alone* | +0.22% (+0.87) | 51 | 3.55% | -28.0% | |
| *Three chairs* | +0.33% (+1.74) | 47 | 3.16% | -16.2% | |
| *Marky + Ophelia, same week* | +0.61% (+2.21) | 50 | 4.49% | -24.0% | |

- **Dash: no.** There is no drift to buy here; the edge is slightly negative.
  My prediction (positive, short of t 2) had the wrong sign, within noise.
- **Quality pullback: no by the edge rule, as predicted.** It matches Marky
  alone, and it cuts his weekly SD by a fifth and his worst drawdown from -28%
  to -24%. As a gatekeeper, Cecil lowers the risk but does not add return.
- **Relay: no.** On history, holding Ophelia a week late cost 0.20%/wk against
  holding both in the same week. The lag effect was a seen-week pattern.
- **Four chairs: no.** Dash dilutes the book.
- **The Warden: promising under its registered rule.** It halves the weekly
  SD (1.58% against 3.06%) and cuts the worst drawdown from -18.3% to -8.7%,
  while its paired edge, -0.30%/wk (t -1.67), stays inside the -2 line. That
  is a real trade-off: a third of a point a week of edge, not significant,
  for half the risk. It is a candidate for the next quarterly change and goes
  to the forward record first.

**The best number on history is a baseline, and it is not real.** "Marky +
Ophelia, same week" posted +0.61%/wk (t +2.21), and 90% of its clipped edge
comes from ten of the engine-era Ophelia's names, led by RGTI, IONQ and QBTS.
Those are the hindsight names again, rising steadily enough to pass under the
20% clip. Trimming any book's top contributors lowers its edge; the tell is who
those ten are.

On the Council weeks (seen, decide nothing), Relay posted +0.87%/wk (ahead in
7 of 8) and Marky alone +1.40%, while the Warden had the calmest book (weekly
SD 0.85%) at -0.24%/wk.

*Erratum (found registering Pass 8):* the Warden's sector cap used the
engines' `get_sector`, which has no entry for 46 of the 111 and calls them
"Unknown", so on the Council weeks the cap treated those 46 as one sector.
The history rows are unaffected (the frozen list is fully mapped); the Council
rows above for the Warden are as computed, and decided nothing. Pass 8 looks
names up in the owner's list's GICS sectors first.

## Pass 8 -- the Warden taken apart (registered before any run)

Pass 7's one keeper was a chair that sizes instead of picking. Before it goes
anywhere near the live book, three questions, all mechanical, on the same 96
history weeks with the nine Council weeks beside them. `pass8_warden.py` has
the exact rules; the names, blackouts and members' fives come from Pass 7's
code path unchanged, and Pass 7's Warden and Four chairs are rebuilt as a
regression check that must reproduce Pass 7's history numbers exactly.

1. **Which lever does the work?** Eight books on the three chairs' names
   (Ophelia, Cecil, Marky; Dash flopped and is dismissed), one for every
   subset of the Warden's three levers: *No lever* (the union, equal weights,
   fully invested), *Sizing only*, *Cap only*, *Dial only*, *All but sizing*,
   *All but cap*, *All but dial*, and *Warden, three chairs* (all three). The
   cap keeps the two calmest names a sector; sizing is inverse 12-week
   volatility; the dial books 80% when SPY closed below its 40-week average.
   For each lever: its *alone share* of the Warden's weekly-SD cut (No lever
   minus lever only, over No lever minus the Warden) and its *removed share*
   (all-but-lever minus the Warden, over the same cut). A lever **carries**
   the Warden if both shares are at least 50%, is **dead weight** if both are
   at most 15%, and **helps** otherwise. The **cheapest rule** is the book
   with the fewest levers whose SD is within 80% of the full cut, ties to the
   higher paired edge over No lever.
2. **Does the Warden hold over the three live chairs?** *Warden, three
   chairs* against *Three chairs* (a third each), under Pass 7's rule: weekly
   SD at least 10% lower, a shallower worst drawdown, paired edge above t -2.
   This is the book the forward record would carry.
3. **Does Cecil's gate stack with it?** *Warden, quality* is the Warden over
   Ophelia, Cecil and Quality pullback (Cecil's value screen on Marky's
   ranking). Against Warden, three chairs, same rule: SD at least 10% lower,
   drawdown not deeper, paired edge above t -2.

**Predictions.** Sizing carries the Warden (both shares above 50%); the cap is
dead weight (fifteen names across ten sectors rarely reach a third in one);
the dial helps but under 25%, since it only bites in the risk-off weeks. The
cheapest rule is Sizing only. Warden, three chairs is promising, with about
the same cut as Pass 7's (near half the SD) and an edge cost near -0.25%/wk.
Warden, quality is not: the Warden already sizes, so the gate cuts less than
10% more.

**What counts.** The lever roles and the cheapest rule are computed by the
thresholds above and reported as found. If Warden, three chairs is promising,
`live_week.py warden` adds it to the live record for 2026-09-21 as a weighted
variant scored from Tuesday's open (added on the week's Monday after the
session, like the owner's picks; its weights use nothing after 2026-09-18),
and each later live week carries it from Monday's open. The cheapest rule is
a candidate for the next quarterly change, not a live change now (nugget 10).
Seen Council weeks are reported and decide nothing.

    python lab/pass8_warden.py
    python lab/live_week.py warden 2026-09-21

## Pass 8 results -- sizing is the Warden, and cash does it for free

Run after the registration commit (0f6299e); `results/pass8_warden.json`. The
rebuilt Pass 7 Warden and Four chairs reproduced Pass 7's history numbers
exactly. History, 96 weeks, clipped edge over random; the paired column is
against No lever:

| Book | Edge (t) | Return / wk | Weekly SD | Return per unit of SD | Worst drawdown | Paired vs No lever |
|---|---|---|---|---|---|---|
| *Three chairs* (a third each) | +0.33% (+1.74) | +0.88% | 3.16% | 0.28 | -16.2% | |
| No lever (the union, equal) | +0.29% (+1.69) | +0.82% | 3.02% | 0.27 | -18.4% | |
| Sizing only | +0.01% (+0.09) | +0.38% | 1.76% | 0.21 | -10.5% | -0.28%/wk (t -2.06) |
| Cap only | +0.30% (+1.96) | +0.77% | 2.95% | 0.26 | -16.6% | +0.01%/wk (t +0.12) |
| Dial only | +0.28% (+1.66) | +0.79% | 2.91% | 0.27 | -17.0% | -0.01%/wk (t -0.48) |
| All but sizing | +0.28% (+1.84) | +0.74% | 2.79% | 0.26 | -15.0% | -0.01%/wk (t -0.09) |
| All but cap | +0.01% (+0.06) | +0.36% | 1.68% | 0.21 | -9.9% | -0.28%/wk (t -2.17) |
| All but dial | +0.08% (+0.51) | +0.40% | 1.81% | 0.22 | -9.6% | -0.21%/wk (t -1.32) |
| **Warden, three chairs** | +0.02% (+0.12) | +0.37% | 1.73% | 0.22 | -9.0% | -0.27%/wk (t -1.73) |
| Warden, quality | +0.02% (+0.12) | +0.37% | 1.70% | 0.22 | -9.0% | +0.00%/wk vs the Warden (t +0.01) |

**Which lever does the work: sizing, alone.** The Warden cuts No lever's
weekly SD by 1.29 points (43%). Inverse-volatility sizing delivers 97% of
that cut on its own and 83% of it is lost when sizing is removed: it
*carries* the Warden. The sector cap (5% alone, -3% removed) and the regime
dial (9%, 7%) are *dead weight* by the registered thresholds; SPY was below
its 40-week average in only 12 of the 96 weeks. The cheapest rule is Sizing
only. Sizing is also the whole edge cost: -0.28%/wk against No lever, t
-2.06, at the significance line; the cap costs nothing, and the dial's
-0.06%/wk (t -2.54, tiny but consistent) is the mechanical 20% haircut of a
positive edge in the risk-off weeks.

**Registered verdicts.** Warden, three chairs: *promising* under Pass 7's
rule (SD 1.73% against 3.16%, drawdown -9.0% against -16.2%, paired edge
-0.32%/wk at t -1.86 against Three chairs). Warden, quality: *no*; the gate
cuts 2% more SD, not 10%. Both as predicted, as were the sizing and cap
roles and the cheapest rule; the dial I called a small help, and it is dead
weight.

**The cash null, not registered, and the finding that matters.** The
return-per-unit-of-SD column says the Warden makes the book worse, not
safer: 0.22 against 0.28. Holding the plain three-chair book at a constant
55% exposure gives the Warden's SD (1.73%) and its drawdown (-9.0%) exactly,
with more return: +0.48%/wk against +0.37% (Warden minus the scaled book
-0.11%/wk, t -0.71, ahead in 49 of 96). Clipped returns say the same (70%
exposure; -0.12%/wk, t -0.90). On the Council weeks (seen, decide nothing)
the gap is wider: Three chairs at 68% made +0.42%/wk to the Warden's -0.05%.
So the Warden is a volatility dial, and a plain cash position is the same
dial without the cost. `python lab/pass8_warden.py cash-null` reproduces
this from the results file; it is now rule 7.

**What this changes.** Pass 7's read of the Warden as "half the risk for a
third of a point" was the wrong comparison; the right one is "half the risk
for nothing", which cash already offers, and which the live pipeline's 20%
cash cap already is. The Warden is not a candidate for the live book, and
neither is sizing on its own. It stays on the live record as registered
(`results/live/2026-09-21.json`, "Warden, three chairs": 11 names, fully
invested with SPY above its 40-week average, scored from Tuesday's open), so
the forward weeks judge it against "all 15" per unit of risk with no
hindsight in the universe.

## Pass 9 -- the universe: the 111, the feed, and the S&P 500 (registered before any run)

The owner asked for the tests to run on the proper 111, and whether the team
has enough to choose from ("maybe our 111 isn't enough for the team"). The
live engines have never scored 44 of the 111 (`BACKFILL_44_TICKERS`; a
deliberate split, per the 2026-09-21 proposal, with the Council v2 switch as
the planned route), and every history pass so far ran on the frozen 277.
`pass9_universe.py` replays the mechanical team (the Ophelia and Cecil
engines from a baseline replay, Marky's channel five) on the 96 history weeks
and the nine Council weeks over four universes:

| Universe | Names | What it is |
|---|---|---|
| the 277 | 277 | the frozen engine list Passes 1-8 used (reference) |
| the 111 | 109 | the owner's Council list; the engines do not score BTC or GLD |
| the feed | 318 | the 274 the engines scan live plus the 44 they never see |
| the S&P 500 | 503 | today's constituents (`universe_sp500_2026-09-22.csv`, Wikipedia, fetched 2026-09-22 06:48 ET) |

Books per universe: each chair's five and three chairs (a third each), scored
against random books of the same weights from the week's tradeable names in
the *same* universe (production's earnings blackout), clipped +/-20% primary,
raw beside. Per universe: the equal-weighted tradeable universe against SPY
(the base rate) and the cross-sectional SD of clipped weekly returns (the
dispersion a screen has to work in). Ophelia's rotation needs a sector for
every name, so a name the engines' map lacks takes its GICS sector from the
Council CSV or the S&P table, folded onto the engines' eight buckets
(proposal A), in the lab only.

**Hindsight, stated up front.** The 111 was drawn up in September 2026 with
2025's winners on it; the 277 holds names because they ran; today's S&P 500
holds names because they rose into it. Every base rate on history is
flattered by this, the curated lists' most. Edges are within-universe (the
picks against random names from the same list), which is fair; base rates
are descriptive and decide nothing.

**Predictions.**
1. No chair on any universe beats random (t >= 2, both halves positive).
   Sixteen tests make one false pass about a one-in-six chance; a lone pass
   is noted, not adopted.
2. Base rates: the 111 well above SPY, the 277 and the feed above, the S&P
   500 near or below (equal weight has lagged cap weight in these years).
3. Three chairs' edge stays within 0.2%/wk of its edge on the 111 on every
   universe, paired t under 2: the team is not starved, the signals are weak.
4. Dispersion: the 111 highest, the S&P 500 lowest.
5. Marky's channel five near zero everywhere.

**What counts** (history only; Council weeks are reported and decide
nothing):
- A wider universe *feeds the team* if Three chairs' clipped edge on it beats
  the same book's edge on the 111, paired by week, with t >= 2, a positive
  mean and both halves positive. If neither the feed nor the S&P 500 does,
  **the 111 is enough for this team**: widening waits for a better team, not
  the other way round.
- A chair *beats random* on a universe under the usual rule (t >= 2, positive
  edge, both halves positive), reported with the deflation note; anything
  that passes goes to the forward record before it touches anything.
- The LLM Council on a wider universe is not in this pass. If a wider
  universe feeds the mechanical team, that is the next Room run; if not,
  there is nothing for the agents to gain from more names either.

    python lab/fetch_sp500.py
    python lab/pass9_universe.py

## Pass 9 results -- the 111 is enough for this team

Run after the registration commit (b31cf1a); `results/pass9_universe.json`.
History, 96 weeks, clipped edge over random books from the same universe:

| Universe | Book | Edge (t) | Weeks ahead | Return / wk | Weekly SD | Worst drawdown | vs the 111, paired |
|---|---|---|---|---|---|---|---|
| the 277 | Ophelia | **+1.04% (+2.01)** | 54 | +1.93% | 7.72% | -28.6% | +0.78%/wk (t +1.48) |
| | Cecil | -0.22% (-0.96) | 45 | +0.11% | 2.06% | -9.3% | +0.10% (+0.55) |
| | Marky | +0.20% (+0.81) | 50 | +0.60% | 3.55% | -28.0% | -0.07% (-0.31) |
| | Three chairs | +0.33% (+1.75) | 46 | +0.88% | 3.16% | -16.2% | +0.27% (+1.26) |
| the 111 | Ophelia | +0.26% (+0.61) | 50 | +0.97% | 5.73% | -25.2% | |
| | Cecil | -0.32% (-1.35) | 41 | +0.18% | 2.08% | -11.0% | |
| | Marky | +0.27% (+0.94) | 45 | +0.85% | 4.00% | -27.6% | |
| | Three chairs | +0.06% (+0.31) | 44 | +0.67% | 2.87% | -18.2% | |
| the feed | Ophelia | +0.99% (+1.99) | 57 | +1.83% | 7.14% | -23.0% | +0.72% (+1.53) |
| | Cecil | -0.20% (-0.87) | 42 | +0.17% | 2.06% | -9.6% | +0.12% (+0.72) |
| | Marky | +0.37% (+1.31) | 51 | +0.83% | 4.00% | -29.8% | +0.09% (+0.47) |
| | Three chairs | **+0.40% (+2.08)** | 54 | +0.94% | 3.12% | -15.0% | +0.34% (+1.76) |
| the S&P 500 | Ophelia | +0.69% (+1.86) | 56 | +1.14% | 4.57% | -13.8% | +0.42% (+0.83) |
| | Cecil | -0.40% (-1.74) | 38 | -0.05% | 2.02% | -16.6% | -0.08% (-0.37) |
| | Marky | -0.01% (-0.05) | 53 | +0.35% | 3.06% | -28.9% | -0.28% (-1.04) |
| | Three chairs | +0.10% (+0.63) | 46 | +0.48% | 2.36% | -14.3% | +0.04% (+0.19) |

| Universe | Tradeable names / wk | Equal-weight vs SPY, raw (t) | clipped (t) | Dispersion |
|---|---|---|---|---|
| the 277 | 249 | +0.05% (+0.44) | -0.00% (-0.05) | 4.01% |
| the 111 | 100 | **+0.24% (+2.40)** | +0.14% (+1.50) | 4.73% |
| the feed | 293 | +0.10% (+1.06) | +0.03% (+0.36) | 4.31% |
| the S&P 500 | 461 | +0.01% (+0.13) | +0.00% (+0.01) | 3.74% |

**Registered verdicts.** Wider feeds the team: *none*. The feed's three
chairs beat the 111's by +0.34%/wk, t +1.76, short of the line; the S&P 500's
by +0.04%. **The 111 is enough for this team**; widening waits for a better
team. Beats random: *Ophelia on the 277* and *Three chairs on the feed*.
Both are noted, not adopted, and the diagnostic below says why.

**Where Ophelia's edge lives (unregistered diagnostic, from the results and
the cached prices).** On every universe her ten biggest contributors are her
whole edge; without them she is at or below zero:

| Universe | Ophelia | Without her ten biggest | Their share | The ten |
|---|---|---|---|---|
| the 277 | +1.04%/wk | -0.05% (t -0.12) | 107% | RGTI, IONQ, QBTS, INTC, PANW, ZS, BFLY, QUBT, CVS, MU |
| the 111 | +0.26% | -0.61% (t -1.44) | 301% | RGTI, CRWD, RKLB, OKLO, INOD, AMD, ORA, NUE, JNJ, AWK |
| the feed | +0.99% | -0.18% (t -0.39) | 100% | RGTI, IONQ, QBTS, INTC, OKLO, PANW, BFLY, QUBT, EIX, CVS |
| the S&P 500 | +0.69% | -0.03% (t -0.12) | 110% | INTC, SNDK, PANW, QCOM, MU, RDDT, BE, EIX, CIEN, ED |

The 277 and the feed are the quantum names again (RGTI, IONQ, QBTS, QUBT),
so those two passes are the hindsight file, as in Nuggets A and Pass 7. The
S&P 500's ten hold four names that joined the index after the history began
(SNDK, RDDT, BE, CIEN): today's constituents include 40 names added since
2024-09-09 because they ran, which is the additions bias that flatters a
momentum screen. Pass 9b below takes them out.

**The rest.** The 111's base rate is what its hindsight predicts: +0.24%/wk
over SPY (t +2.40), the only universe whose equal weight beats the index, and
the widest dispersion (4.73%). On the seen Council weeks it is the *worst*:
-0.26%/wk under SPY, and the engine Ophelia on it made -1.66%/wk with a
-14.9% drawdown. The list's edge lives in its past. Marky's channel five is
near zero on every universe (-0.01% to +0.37%), as predicted. Cecil is
negative on all four (-0.20% to -0.40%/wk, 38 to 45 weeks ahead of 96); the
lab's Cecil runs without point-in-time P/E, so this is his momentum-and-
sector remainder, not the value job as designed. Predictions: 1 wrong (two
passes, both Ophelia's ten names), 2 and 4 and 5 right, 3 right on t and
wrong on size for the 277 and the feed.

## Pass 9b -- the S&P 500 as it stood (registered after Pass 9's results, before this run)

Ophelia's +0.69%/wk on today's S&P 500 (t +1.86) is the one Pass 9 number
without quantum names in it, and four of her ten contributors there joined
the index after the history began. `fetch_sp500.py dates` adds the index's
"Date added" (`universe_sp500_added_2026-09-22.csv`); `pass9_universe.py
asof` replays the team on today's constituents whose recorded date is before
2024-09-09, 463 of the 503 (the 40 taken out: APO, APP, ARES, BE, CASY, CIEN,
COHR, COIN, CRH, CVNA, DASH, DDOG, DELL, ECHO, EME, ERIE, EXE, FDXF, FERG,
FIX, FLEX, HONA, HOOD, IBKR, ILMN, LII, LITE, MRVL, P, PLTR, Q, RDDT, SNDK,
TKO, TPL, VEEV, VRT, WDAY, WSM, XYZ). Removals since then are still missing,
which flatters the base rate but not a screen's edge over random names from
the same list. Scored as in Pass 9, paired against Pass 9's 111 and against
today's S&P 500.

**Prediction.** Ophelia's edge on the as-of list falls under t 1, and the
paired difference (today's list minus as-of) is positive: the additions carry
her.

**What counts.** If Ophelia beats random on the as-of list under the usual
rule (t >= 2, positive edge, both halves positive), she is the first
non-control signal in this lab with legs on a list that has no hindsight
additions, and her own book goes to the forward record. Otherwise her S&P
number joins the hindsight file with the rest.

    python lab/fetch_sp500.py dates
    python lab/pass9_universe.py asof

## Pass 9b results -- not the additions, not momentum, one regime

Run after the registration commit (b6c1bbd); `results/pass9b_sp500_asof.json`.
On the 463 names already in the index on 2024-09-09 (427 tradeable a week),
Ophelia's clipped edge over random is **+0.67%/wk (t +1.86)**, 55 of 96
weeks ahead, halves +0.44 / +0.91, against +0.69% on today's list; the
additions' share is -0.01%/wk (t -0.05). Marky +0.04%, Cecil -0.29%, three
chairs +0.14% (t +0.90). The registered verdict is **no** (t under 2), and my
prediction that the additions carried her was **wrong**: they carried
nothing.

**What she is** (unregistered diagnostics, from the results and the cached
prices):
- *One regime.* By half-year: 2024H2 -0.92%/wk (5 of 17 weeks ahead); 2025H1
  +0.99% (18 of 26); 2025H2 +0.33% (15 of 26); 2026H1 **+2.05%** (17 of 26).
  2026H1 is 83% of the two-year total, and two weeks of it (2026-04-27
  +9.6%, 2026-05-04 +19.6%) are 45%. In those weeks she held three names,
  all semiconductors (MCHP, INTC, ON; then INTC +26%, MU +33%, QCOM +24%
  raw): the rotation anchor had her all in one sector during its melt-up.
- *Not plain momentum.* A 12-1 relative-strength top five on the same names
  each week makes +0.09%/wk (t +0.23, 49 of 96 ahead). The two share 3% of
  their names a week and their weekly edges correlate +0.14; her engine is a
  sector bet, not a stock screen.
- *Not survivorship the other way either.* Removals since 2024-09 are absent
  from the list, which if anything raises the random baseline she is scored
  against.

**Reading.** A concentrated sector-rotation bet that paid in one half-year on
a broad list and lost in another, ahead in 57% of weeks. It is the strongest
lead this lab has produced on a list with no hindsight additions, and it is
still not an edge by the registered line. It stays in the file, and the
forward record is its judge. The cheap next step, the owner's call: put the
engine Ophelia *alone* on the forward record (a `solo` knob in
`engine_lab.run` and one line in `forward.py`'s registry), so her weeks
accrue from now on the live universe without another history run. Pass 9's
verdict stands: the 111 is enough for this team, and the S&P 500 does not
rescue it either.

*Done 2026-09-22 (the owner delegated both):* `Ophelia-solo` is in
`forward.py`'s registry (a `solo` knob in `engine_lab.run`; first forward
week 2026-09-28), and her five for the live week of 2026-09-21 are on the
live record on both the 274 and the 111, recorded and committed before
Tuesday's open. The sector fallback shipped as proposal A: `GICS_FOLD` and
the `get_sector` fallback in `scan_pipeline/utils/data_utils.py`, pinned by
`tests/test_sectors.py`, a no-op on the live universe. The Monday task
(crew-8) now also runs `live_week.py score-pending`.

## Pass 10 -- Ophelia's map: whose sectors? (registered before any run)

The owner asked whether Ophelia should treat semiconductors as a sector of
their own, and whether the standard sectors are the problem ("would be
interesting if we made our own"). Her rotation is the part of her that
showed up in Pass 9b (a 40-point anchor for the top sector by prior-week
average, 20 for the second, a flow term, up to 30 points of regime credit
for offensive or defensive sectors), so the map it reads is a fair question.
`pass10_sectors.py` replays the engine Ophelia's five under five maps on the
S&P 500 as of 2024-09-09 (463 names, the clean list) with the 111 beside it,
96 history weeks and the nine Council weeks, scored as in Pass 9:

| Map | What it is |
|---|---|
| engine 8 | the eight engine buckets, Pass 9b's map (baseline) |
| engine 8+Semis | the eight, with the GICS sub-industries "Semiconductors" and "Semiconductor Materials & Equipment" (20 of today's S&P; NVDA, AMD, TSM on the 111) as a ninth, offensive bucket |
| GICS 11 | the index's eleven GICS sectors, each offensive or defensive by the bucket it folds onto |
| GICS 11+Semis | GICS 11 with the semiconductor sub-industries as a twelfth, offensive sector |
| our own 11 | point-in-time: each week, names with at least 40 of the trailing 52 weekly returns, average-linkage clustering on 1 - correlation, cut into eleven clusters; a cluster is offensive or defensive by the majority engine bucket of its members |

The regime credit's sector lists became module constants of the engine on
2026-09-22 (behavior-preserving; the smoke replay's books are identical), so
every map keeps the credit. The sub-industries come from
`universe_sp500_full_2026-09-22.csv` (Wikipedia, fetched 2026-09-22).

**Predictions.** Semis as a ninth bucket: paired against engine 8 on the
clean list, positive but short of t 2 (it concentrates her further into
semiconductors in 2026H1 and costs elsewhere), with a higher weekly SD. GICS
11: within 0.15%/wk of engine 8, t under 1. GICS 11+Semis: like the ninth
bucket. Our own 11: below engine 8 (paired negative, t between -2 and 0):
clusters that change weekly make noisy sector averages. On the 111 the
semiconductor sector has three names and nothing is significant.

**What counts** (history, the S&P 500 as of 2024-09; the 111 and the
Council weeks are reported and decide nothing): a map *helps* if its paired
clipped edge over engine 8 is positive with t >= 2 and both halves positive.
Four maps at the line: about one in six that one passes by luck. A map that
helps goes to the forward record as a solo variant before it touches the
live engine; the change freeze applies.

    python lab/fetch_sp500.py full
    python lab/pass10_sectors.py

## Pass 10 results -- the coarse map wins on the clean list; the owner's map is the steady one

Run after the registration commit (4ecc389); `results/pass10_sectors.json`.
The S&P 500 as of 2024-09 (463 names, 18 semiconductors), history, 96 weeks,
the engine Ophelia's five under each map, clipped edge over random:

| Map | Edge (t) | Weeks ahead | Weekly SD | Worst drawdown | Paired vs engine 8 | Same five |
|---|---|---|---|---|---|---|
| engine 8 | +0.68% (+1.87) | 54 | 4.30% | -14.0% | | |
| engine 8+Semis | +0.26% (+0.57) | 51 | 5.26% | -35.0% | -0.42%/wk (t -1.14) | 60% |
| GICS 11 | +0.19% (+0.46) | 48 | 4.65% | -19.2% | -0.49%/wk (t -1.85) | 42% |
| GICS 11+Semis | -0.34% (-0.74) | 44 | 5.20% | -35.0% | **-1.02%/wk (t -2.49)** | 25% |
| our own 11 | +0.08% (+0.21) | 53 | 4.28% | -27.7% | -0.60%/wk (t -1.34) | 0% |

By half-year (clipped edge/wk): engine 8 goes -0.91, +1.00, +0.34, **+2.04**
(2024H2 to 2026H1); engine 8+Semis -0.30, +0.48, +0.52, +0.44; GICS 11
-0.49, +0.31, -0.59, +1.56; GICS 11+Semis +0.25, -0.54, -0.53, -0.07; our
own 11 **+0.77**, -0.45, -0.56, +0.83.

**Registered verdicts: no map helps.** Every finer map is worse than the
eight coarse buckets on the clean list, and GICS 11+Semis is significantly
worse. The mechanism is in the "same five" column and the half-years: the
anchor reads *one week's* average return per sector, so a big bucket
averages the noise out and holds the anchor on the leading group through a
run (that is the 2026H1 +2.04), while a small bucket, semiconductors above
all, flips in and out of the top spot week to week and drags her picks with
it (drawdown -35% for both semiconductor maps). Splitting semiconductors out
did not concentrate her further into the melt-up; it made her chase.

**Predictions.** Semis and GICS 11+Semis: wrong sign (I said a small help,
they hurt). GICS 11: wrong (I said a wash, it cost 0.49%/wk). Our own 11:
right (below the base, t -1.34). The 111: right (nothing significant), but
there the direction reversed, the finer maps all ahead of engine 8 by
+0.48% to +0.66%/wk (t 1.6 to 1.7) on a list whose semiconductor sector is
three names. A map effect that flips sign between two universes is noise or
regime, not a rule.

**The owner's map is the one worth watching.** "Our own 11" (each week's
correlation clusters, no human labels) has the lowest 96-week mean but the
steadiest profile: the only map positive in 2024H2, no 2026H1 spike, weekly
SD equal to the base, and on the nine seen Council weeks it is the best book
in the pass, +2.51%/wk (t +2.72, ahead 7 of 9; +3.51%/wk paired against
engine 8, t +2.46). Seen weeks decide nothing and nine of them prove less,
but a design that fails on history and wins on the only weeks nobody could
tune is exactly what the forward record exists for. Done, 2026-09-22:
`Ophelia-solo-ownmap` in `forward.py`'s registry (a `sector_map_builder`
knob in `engine_lab.run` swaps the map for that replay only) from
2026-09-28, and on the live record for 2026-09-21 from Tuesday's open:
under her cluster map on the 111 she holds AMD, CRWD, INOD, one four-name
cluster (`live_ownmap.py`).

On the 111 (history), engine 8 +0.27% (t +0.62), engine 8+Semis +0.75%
(+1.58), GICS 11 +0.85% (+1.68), GICS 11+Semis +0.92% (+1.68), our own 11
+0.12% (+0.26); on its seen Council weeks every map beat engine 8's -1.71%,
none significantly.

## Pass 11 -- Cecil with a P/E, and the owner's themes (registered before any run)

Two requests from the owner. `pass11_cecil_themes.py` has the exact rules.

**A. Cecil, properly.** Every history pass so far replayed Cecil without a
P/E (production reads today's multiple, which is not point in time), so his
value leg sat at its neutral 15 and what got scored was his safety leg: a
low-volatility screen, which is why he has been mildly negative on every
universe. This pass hands him a point-in-time P/E, the last close before
the Monday over the trailing four quarters' reported EPS as known by then
(the EPS cache the Council Room's Cecil reads; prices and reported EPS are
both split-adjusted by the source), through a `pe_builder` knob in
`engine_lab.run` that lasts one replay. His quality leg stays neutral; there
are no point-in-time fundamentals. Books, his five each week, on the 111
and on the S&P 500 as of 2024-09 (the clean list, which decides):

| Book | |
|---|---|
| Cecil, no P/E | the lab's Cecil of Passes 1-9 (baseline) |
| Cecil, P/E | the same engine with the point-in-time multiple |
| Cheapest five | the five lowest positive P/E among the week's tradeable names: the multiple alone, no engine |

**B. The owner's themes.** Ophelia's rotation under `themes_111.csv`, twelve
themes drawn by the owner's lights (semiconductors; AI power and data
centers; AI software and data; frontier tech: space, defense, robotics,
quantum; biotech and health; crypto and fintech; financials; energy; metals
and industrial core; consumer and media; staples; real estate and regulated
utilities), every one of the 109 in exactly one, on the 111 beside engine 8,
GICS 11 and our own 11 replayed with Pass 10's seeds (they must reproduce
Pass 10's 111 numbers). A theme is offensive or defensive by the majority
engine bucket of its members. **Stated up front:** the map was drawn on
2026-09-22 knowing what ran in 2025-26. The test is of the grouping (which
theme led last week sets the anchor), not a discovery, and the 111 already
carries that hindsight in its membership; a pass here would still have to
earn its way on the forward record.

**Predictions.** A: on the clean list, Cecil with a P/E lands between -0.2%
and +0.2%/wk against random, t under 1 (value lagged in a growth market),
and the paired difference against no-P/E is inside t 2 either way; the
cheapest five is negative (t between -2 and 0); his book changes in most
weeks (same five under half the time). B: the themes come in above engine 8
on the 111, like every finer map did there, but under t 2; the three
reruns reproduce Pass 10 exactly.

**What counts** (history; the Council weeks are reported and decide
nothing): *Cecil with a P/E beats random* on a universe if t >= 2, positive
edge, both halves positive; *the P/E helps him* if the paired edge over
no-P/E is positive with t >= 2 and both halves positive; *the cheapest five
beats random* under the same rule; *the owner's themes help* if their paired
edge over engine 8 on the 111 is positive with t >= 2 and both halves
positive. Seven tests at the line: about one in four that one passes by
luck. A Cecil that works with a P/E is the case for a point-in-time P/E in
production, through the Testing Room and the freeze; a theme map that helps
goes to the forward record as a solo variant.

    python lab/pass11_cecil_themes.py
    python lab/pass11_cecil_themes.py themes     # part B only, after editing themes_111.csv

## Pass 11 results -- the P/E turns Cecil around on the clean list; the themes are a wash

Run after the registration commit (3af8a17); `results/pass11_cecil_themes.json`.
The three Pass 10 reruns reproduced its 111 numbers exactly.

**A. Cecil.** History, 96 weeks, his five, clipped edge over random; the
P/E was known for 99 of 100 tradeable names a week on the 111 and 425 of
427 on the S&P 500 as of 2024-09:

| Universe | Book | Edge (t) | Weeks ahead | Weekly SD | Worst drawdown | Paired vs no P/E |
|---|---|---|---|---|---|---|
| the S&P 500 as of 2024-09 | Cecil, no P/E | -0.28% (-1.25) | 40 | 2.04% | -13.4% | |
| | **Cecil, P/E** | **+0.30% (+1.35)** | 52 | 2.67% | -11.5% | **+0.58%/wk (t +1.91, 61 of 96)** |
| | Cheapest five | +0.21% (+0.93) | 54 | 2.96% | -19.0% | +0.48%/wk (t +1.48, 63 of 96) |
| the 111 | Cecil, no P/E | -0.29% (-1.20) | 40 | 2.08% | -11.0% | |
| | Cecil, P/E | -0.23% (-0.95) | 42 | 2.54% | -20.7% | +0.05%/wk (t +0.21, 48 of 96) |
| | Cheapest five | -0.01% (-0.04) | 53 | 2.32% | -18.5% | +0.28%/wk (t +1.03, 46 of 96) |

By half-year on the clean list, Cecil with a P/E: 2024H2 -0.23, 2025H1
+0.34, 2025H2 +0.21, 2026H1 +0.67 (no P/E: -0.85, -0.08, -0.39, -0.02). The
multiple changed his five in every single week (same five 0%).

**Registered verdicts: none.** But the one that matters missed by a hair:
*the P/E helps Cecil* on the clean list at t +1.91 against the line of 2,
ahead in 61 of 96 weeks, positive in three of four half-years. What the
multiple does is turn the lab's Cecil from a low-volatility screen (mildly
negative on every list since Pass 1) into a value-and-safety screen that is
mildly positive on a broad list, steadily rather than in one regime. The
cheapest five alone carries about the same (+0.21%, t +0.93), so most of it
is the multiple. On the 111 it does nothing: that list is growth names, and
its cheap names are its laggards. Predictions: his edge came in above my
range (+0.30 against -0.2..+0.2), the paired difference inside t 2 as
predicted, the cheapest five positive rather than negative (wrong), and his
book changed far more than "most weeks" (every week).

**What this changes.** Nothing in production: the live Cecil already reads
a live multiple, which for the live week *is* point in time. What was wrong
was the lab: every history verdict on "Cecil" since Pass 1 was his safety
leg alone, and so was the forward record's *production* replay. Fixed
2026-09-22, before any forward week was scored: `forward.py` feeds every
design the point-in-time P/E (`pe_builder`), refreshing the EPS cache
weekly, and registers `Cecil-solo` from 2026-09-22. On the live record for
2026-09-21, from Tuesday's open: the engine Cecil with a P/E holds AES, ALL,
PRU on the 274 and VICI, MTCH, STZ on the 111 (`live_week.py cecil`).

**B. The owner's themes**, Ophelia's five on the 111, history, 96 weeks:

| Map | Edge (t) | Weeks ahead | Weekly SD | Worst drawdown | Paired vs engine 8 | Same five |
|---|---|---|---|---|---|---|
| engine 8 | +0.27% (+0.62) | 51 | 5.73% | -25.2% | | |
| GICS 11 | +0.85% (+1.68) | 52 | 7.15% | -26.1% | +0.59%/wk (t +1.63) | 35% |
| our own 11 | +0.12% (+0.26) | 51 | 7.20% | -43.2% | -0.14%/wk (t -0.32) | 0% |
| the owner's themes | +0.63% (+1.18) | 47 | 7.00% | -33.7% | +0.37%/wk (t +0.78) | 7% |

**Verdict: no**, as predicted (above engine 8, under t 2). The themes land
between the eight buckets and plain GICS 11, and change her book in 93% of
weeks. On the seen Council weeks they are the best of the four maps
(+0.49%/wk, ahead 6 of 9, t +0.46), which decides nothing. The map is the
owner's to edit (`themes_111.csv`, then `pass11_cecil_themes.py themes`);
the lab's read is that on a 109-name list any twelve-way split runs into
Pass 10's lesson, small groups chase, and that the data's own grouping (our
own 11, on the forward record) treats quantum, space, nuclear, crypto and
biotech as one risk-on basket rather than five themes.

## Pass 12 -- Cecil's legs (registered before any run)

Pass 11's one live lead was Cecil with a point-in-time P/E: +0.30%/wk over
random on the clean list, steady by half-year. His score is three legs,
value (40; P/E 5 to 40 points, 25 to 8, above 25 or negative to 0, unknown
to 15), quality (30; a neutral 15 in the lab, since there are no
point-in-time fundamentals) and safety (30; 20 for low realized volatility,
10 for a shallow drawdown). So the real dial is value against safety, and
the one quality input that is point in time, EPS growth from the quarterly
history we cache, is missing. `pass12_cecil_legs.py` captures his per-name
legs once a week from the engine's own table (the lab's tap on `log_ties`,
P/E in) and re-ranks them under other weights offline, with the engine's
own tie-breaks; "as is" must reproduce Pass 11's Cecil, P/E five.

| Variant | Value | Safety | Growth leg |
|---|---|---|---|
| as is | x1 | x1 | none (Pass 11's Cecil, P/E) |
| value 60:40 | x1.5 | x1.333 | none |
| value 70:30 | x1.75 | x1 | none |
| value only | x1 | x0 | none |
| safety only | x0 | x1 | none (the old lab Cecil) |
| + growth 20 | x1 | x1 | 20 points |
| + growth 30 | x1 | x1 | 30 points |

Growth is the trailing four quarters' EPS against the four before, as known
by the Monday: 0 at or below zero growth, full at +30%, neutral (half) when
unknown. Quality stays at weight 1 throughout (the engine's tie-break).
Scored as in Passes 9-11 on the S&P 500 as of 2024-09 (which decides) and
the 111 (reported); 96 history weeks and the nine Council weeks.

**Predictions.** More value weight raises his mean and his weekly SD (cheap
names are the volatile ones on this list); value only lands near the
cheapest five's +0.21%; safety only lands near the old Cecil's -0.28%. The
growth leg is a small help, +0.1% to +0.3%/wk over as is, under t 2. Nothing
passes.

**What counts** (history, the clean list): a variant *helps* if its paired
clipped edge over as is is positive with t >= 2 and both halves positive.
Six variants at the line: about one in four that one passes by luck. A
variant that helps is the case for changing Cecil's weights in production,
through the freeze; it goes to the forward record first.

    python lab/pass12_cecil_legs.py

## Pass 12 results -- his legs are right as they are

Run after the registration commit (690c8a1); `results/pass12_cecil_legs.json`.
The regression check: the re-ranked "as is" order begins with the engine's
own proposal in 100% of weeks on both lists; the file's "0% reproduced"
line is book size (the engine proposes three names, this pass books five),
not ranking. History, 96 weeks, five names, clipped edge over random:

| Variant | S&P 500 as of 2024-09: edge (t) | paired vs as is | same five | the 111: edge (t) | paired |
|---|---|---|---|---|---|
| as is | +0.25% (+1.34) | | | -0.03% (-0.13) | |
| value 60:40 | +0.13% (+0.71) | -0.12%/wk (t -1.87) | 57% | -0.10% | -0.07% (t -0.98) |
| value 70:30 | +0.25% (+1.33) | +0.01%/wk (t +0.08) | 16% | -0.07% | -0.04% |
| value only | +0.26% (+1.12); SD 3.06%, drawdown -17% | +0.01%/wk (t +0.05) | 0% | -0.06% | -0.04% |
| safety only | -0.26% (-1.41) | **-0.51%/wk (t -2.16)** | 0% | -0.28% | -0.26% (t -1.19) |
| + growth 20 | +0.16% (+0.94) | -0.08%/wk (t -0.55) | 0% | -0.06% | -0.03% |
| + growth 30 | +0.16% (+0.98) | -0.08%/wk (t -0.55) | 0% | +0.01% | +0.04% |

**Registered verdicts: none helps.** The one significant number runs the
other way: take the value leg out and he loses 0.51%/wk (t -2.16), the
mirror of Pass 11's +0.58 for putting the multiple in. Tilting further
toward value adds nothing on the clean list (60:40 is worse, 70:30 flat,
value only the same mean with a quarter more volatility and a deeper
drawdown), and the EPS-growth leg costs a little. The half-years explain the
blend: value only made its money in 2024-25 (+0.51, +0.28, +0.53) and lost
in the 2026H1 growth melt-up (-0.13), while as is did the opposite (+0.07,
+0.26, +0.06, +0.51); the two legs offset, which is why as is was the
steady one in Pass 11. On the 111 every variant is zero.

**Predictions.** Value only near the cheapest five (right, +0.26 against
+0.21); safety only near the old Cecil (right, -0.26 against -0.28); more
value weight raising the mean (wrong, it lowered or left it) and the SD
(right); the growth leg a small help (wrong, a small cost). On the seen
Council weeks of the 111, value only (+1.42%/wk) and + growth 20 (+1.33%,
t 2.95, 7 of 9) were the best books, which nine seen weeks cannot make
into anything.

**What this changes.** Nothing. Cecil with a point-in-time P/E and his legs
as designed (value 40, quality 30, safety 30) is the honed Cecil; the value
leg is the part that works, the safety leg is the part that keeps him
steady, and neither a heavier value tilt nor an earnings-growth leg improves
him. He is on the forward record as Cecil-solo from 2026-09-22.

## Pass 13 -- holding on, and managing the week (registered before any run)

Two of the owner's questions, on the engine members' fives (Ophelia, Cecil
with a point-in-time P/E, Marky's channel) and all fifteen together, on the
S&P 500 as of 2024-09 (which decides) and the 111 (reported), 96 history
weeks. `pass13_hold_manage.py` has the exact rules.

**A. Holding on.** The nine-week hold check found that nothing accumulates,
and the owner is not optimistic; this is the same question with 96 weeks
and a cost. Each pick is held 1, 2, 4 and 8 weeks, Monday's open of the pick
week to Friday's close of week k, against random books of the same size
from the pick week's tradeable names held the same way. The edge is per
week of holding, clipped per name at +/-20% a week of horizon, and reported
net of a round-trip cost of 0.10% spread over the hold. The t for horizon k
uses every k-th pick week so the windows do not overlap. Holding k weeks
*helps* a book if its net per-week edge beats hold-1's, paired by pick
week, with t >= 2.

**B. Managing the week**, on daily bars. Entry at Monday's open; the
decision at the second session's close ("Tuesday"); everything held to
Friday's close. Five rules, each against the plain hold, paired by week:

| Rule | What happens at Tuesday's close |
|---|---|
| stop | a name below its entry is sold; cash for the rest of the week |
| stop vs SPY | a name trailing SPY since entry is sold |
| rotate | the owner's rule: the worst two (worst 40% of a bigger book) are sold and the cash goes equally into the best three (best 60%) |
| rotate Wed | the same, at the third session's close |
| reverse | the mirror: the best two sold into the worst three |

Costs: 0.05% a side on the weight moved (a stop pays one side, a rotation
two). Each rule is also applied to the random books, so a rule that helps
random picks as much as the members' is read as *mechanical* (an intra-week
momentum or reversal effect anyone could harvest), not skill. Part B is
scored raw and paired, since the same names sit on both sides. A rule
*helps* a book if its net paired edge over the plain hold is positive with
t >= 2 and both halves positive.

**Predictions.** A: no horizon beats hold-1 for any book (the edges do not
persist); Marky's per-week edge falls with the horizon (his bounce
reverses); after cost, longer holds look *less* bad than hold-1 only
because hold-1 pays the round trip every week. B: the stops hurt (selling
Tuesday's losers forfeits the reversal the smoke weeks already showed on
random picks, about a point a week); the owner's rotation is about zero
gross and negative net, with most of whatever it shows also on random
books; the reverse rule is a small positive gross, about zero net. Nothing
passes. Twenty-eight tests at the line: two or three false passes would not
be a surprise, so a lone pass is noted, not adopted.

    python lab/pass13_hold_manage.py

## Pass 13 results -- do nothing during the week; Cecil keeps

Run after the registration commit (4a28376); `results/pass13_hold_manage.json`.
The engine members' fives here are the engine's own proposals (three names
for Ophelia and Cecil, five for Marky's channel), Cecil with the P/E.

**A. Holding on**, the S&P 500 as of 2024-09, edge per week of holding
(clipped, gross; net of a 0.10% round trip in the second column):

| Book | hold 1 | hold 2 | hold 4 | hold 8 | net, hold 1 / 2 / 4 |
|---|---|---|---|---|---|
| Ophelia | +0.66% (1.82) | +0.51% (1.18) | -0.21% | -0.02% | +0.56 / +0.46 / -0.24 |
| **Cecil** | +0.34% (1.52) | +0.30% (1.44) | +0.21% (0.94) | +0.25% (1.49) | +0.24 / +0.25 / +0.19 |
| Marky | +0.02% | +0.10% | +0.08% | -0.07% | -0.08 / +0.05 / +0.06 |
| all 15 | +0.27% (2.16) | +0.26% (1.67) | +0.04% | +0.05% | +0.17 / +0.21 / +0.02 |

**Verdicts: no horizon beats hold-1 for any book** (paired, net; the
closest is Cecil at four weeks, +0.51%/wk over hold-1, t 1.54). The owner's
doubt was right and the nine-week check holds at 96: the members' edges do
not accumulate. But they decay differently. Ophelia's is a one-to-two-week
thing and is gone by four; Marky's never existed on history; **Cecil's
keeps**: +0.34, +0.30, +0.21, +0.25 per week at one, two, four and eight
weeks, so a Cecil held a month costs a quarter of the turnover for the same
edge per week. That is what a value signal should look like, and it is the
first member whose picks are worth holding past Friday.

**B. Managing the week**, the S&P 500 as of 2024-09, net of 0.05% a side,
paired against the plain hold; "on random" is the same rule on random
books:

| Book | stop | stop vs SPY | rotate (the owner's) | rotate Wed | reverse |
|---|---|---|---|---|---|
| Ophelia | -0.29%/wk (t -1.50) | -0.19% (-0.95) | -0.16% (-1.15) | -0.01% | +0.00% |
| Cecil | -0.14% (-1.07) | -0.16% (-1.14) | **-0.21% (t -2.52)** | **-0.19% (t -2.96)** | +0.03% |
| Marky | -0.03% | -0.03% | +0.01% | -0.12% (-1.35) | -0.07% |
| all 15 | -0.13% (-1.38) | -0.11% (-1.01) | -0.04% | -0.04% | -0.02% |
| on random books | -0.03 to -0.05% | -0.01 to -0.03% | +0.01 to +0.03% | -0.01 to -0.03% | -0.02 to -0.04% |

**Verdicts: nothing helps; every rule that acts costs.** The stops cost
every book, and more than they cost random books: the members' Tuesday
losers recover more than random Tuesday losers do, so selling them
forfeits the recovery. The owner's rotation is about zero on random books
(no intra-week momentum to harvest) and significantly negative on Cecil's
picks in both its forms, which is the same fact from the other side: his
Tuesday laggards are the ones that come back. The reverse rule, the
mirror, is a rounding error. On the 111 the picture is the same with wider
numbers (stop vs SPY on all fifteen -0.35%/wk, t -2.39; the rotation
-0.29%, t -2.18; Ophelia's reverse +0.55%, t 1.63, the one positive, on
the list where she is weakest). On the seen Council weeks the stops helped
Ophelia (+0.8%/wk, she was losing those weeks) and hurt Marky (-0.6%, t
-2.67), which nine weeks cannot turn into a rule.

**Predictions.** A: right that no horizon beats hold-1, right that Marky
has nothing to hold, wrong in one respect that matters: I said no edge
persists, and Cecil's does. B: all four right (the stops hurt, the rotation
is zero gross and negative net, the reverse is a small gross positive,
nothing passes), and one nuance the registration did not foresee: the
rotation's harm is not mechanical (random books show none); it is specific
to these picks.

**An unregistered observation, handled as such (Pass 13).** The union of the three
engines' picks, equal-weighted with Cecil's P/E in ("all 15", about eleven
names), makes +0.27%/wk over random at the one-week hold on the clean list,
t 2.16, both halves positive (+0.07, +0.47), ahead 53 of 96. That crosses
the usual line, and Part A was not registered to judge it; 82% of the edge
sits in 2026H1 (Ophelia's regime), and net of the round trip it is t 1.35.
It is the three uncorrelated weak signals adding, as section 3 of the
scorecard said they would. It goes to the forward record as `Union-equal`
(a `union` knob in `engine_lab.run`: each engine's top five, equal weights
over the union) from 2026-09-22, and to the live record for 2026-09-21 as
"Union of engines, the 111" from Wednesday's open, and it decides nothing
until the weeks say so.

## Pass 14 -- the weekly screen as Marky's chair, and his universe (registered before any run)

The owner's daily screen (`screen/daily_screen.py`, 2026-09-23: a rising
120-day channel, a pullback into its lower half, the MACD histogram
crossing up or turning, and "clean air" above) is Marky's job done daily on
small and mid caps. Two of the owner's questions, on 96 history weeks with
the nine Council weeks beside them. `pass14_screen_marky.py` has the rules;
it imports the screen's own `analyze()` and `tier()`, so what is tested is
what runs each morning.

1. **Run weekly on Friday's close, is it a better Marky than the channel
   five?** Books each week: *Screen A* (Tier A, up to five, in the screen's
   order: least overhead first, nearest exit first), *Screen A+B* (up to
   five across A then B), *Screen C*, and *Marky channel* (Pass 5's five on
   the same universe, the baseline). Scored as in Passes 9-13, clipped edge
   over random books of the same size from the week's tradeable names in the
   same universe. Plus the screen's own trade: entry at Monday's open, exit
   at the first close below the name's 40-day low as of the signal, else
   week 8's Friday close, against random names traded the same way with
   their own 40-day lows; the edge per trade and per week held, with the t
   on every eighth pick week so trades do not overlap.
2. **Should Marky have a bigger universe than the 111?** Three universes,
   each against its own random books: the 111 (109 stocks; no cap or
   liquidity rule), the S&P 500 as of 2024-09 (463), and *the screen's
   list*: today's listing at $300M to $10B and $3 or more
   (`universe_smid_2026-09-23.csv`, 2,627 names before the screen's
   rate-sensitive exclusion), with the screen's $5M-a-day rule applied point
   in time from the trailing 20 sessions. **Stated up front:** the names are
   on that list because they are that size today, so it carries
   survivorship; its base rate is flattered and only within-universe
   comparisons count. The across-universe number is the screen's edge on
   its list minus its edge on the 111, week by week.

**Predictions.** On the 111 the screen fires about once a week (the smoke
run: 0.3 Tier A, 0.7 Tier B), so Screen A+B there is a thin book near zero,
like Marky's channel. On the clean list, near zero. On the screen's list,
positive at one week but under t 2 after the clip (the bounce is bigger in
small caps, and the list is survivors), and the swing trade positive gross
per trade with about half the names stopped out before week 8. Tier A and
A+B do not differ significantly (too few A names). The across-universe
difference is positive but under t 2. Nothing passes.

**What counts** (history): the screen *is a better Marky* on a universe if
Screen A+B beats Marky channel, paired by week, with t >= 2, a positive
mean and both halves positive. *The bigger universe pays for Marky's job*
if Screen A+B on the screen's list beats random with t >= 2 and both
halves positive **and** its edge exceeds its own edge on the 111, week by
week, with t >= 2; both are needed, since a bigger list that does not beat
random is more names, not more edge. Seen Council weeks decide nothing.
Anything that passes goes to the forward record first: the Monday report
in `screen/reports/` is already the weekly screen, point in time from
today.

    python lab/fetch_smid.py
    python lab/pass14_screen_marky.py

## Pass 14 results -- not a better Marky, and the bigger universe is more signals, not more edge

Run after the registration commit (eecc199); `results/pass14_screen_marky.json`.
The screen's list came to 2,195 names after its rate-sensitive exclusion
(2,185 with prices), and its liquidity rule, the blackout and the two-year
history left a pool of about 1,300 a week. History, 96 weeks, clipped edge
over random from the same universe; "names" is the book's average size:

| Universe | Signals / wk (A, B, C) | Screen A | Screen A+B | Screen C | Marky channel | A+B vs channel, paired |
|---|---|---|---|---|---|---|
| the 111 | 2.4 (0.4, 1.9, 0.1) | -0.53% (-0.98), 1.2 names, 31 wks | +0.31% (+0.81), 2.6 names, 76 wks | -1.07%, 11 wks | +0.40% (+1.42) | -0.24%/wk (t -0.50) |
| the S&P 500 as of 2024-09 | 8.4 (1.2, 6.3, 0.8) | -0.18% (-0.57) | -0.23% (-1.05), 4.2 names | -0.22% | +0.04% (+0.22) | -0.25%/wk (t -1.06) |
| the screen's list | 34.6 (2.8, 24.9, 7.0) | +0.38% (+0.75), 2.7 names | -0.11% (-0.36), 4.9 names | -0.07% | +0.18% (+0.57) | -0.29%/wk (t -0.73) |

**Across universes**, Screen A+B on the screen's list minus on the 111,
week by week: **-0.56%/wk (t -1.26)**; Marky channel the same way,
-0.22%/wk. The bigger list gives the screen fourteen times the signals and
none of the edge.

**The screen's own trade** (entry Monday's open, exit at the signal's
40-day low or week 8; against random names traded the same way with their
own 40-day lows) is negative for every book on every list: on the screen's
list, Screen A -1.54% a trade (-1.81%/wk held), A+B -0.49% (-0.55%/wk), C
-1.37%, Marky channel -0.15%; 52% to 64% of names are stopped out before
week 8, on the 111 and the clean list 59% to 68%. The mechanism is the
setup itself: a name picked 8% to 30% off its high with the MACD just
turning is, by construction, sitting close to its 40-day low, so the stop
is tight and gets hit; random names carry the same stop but sit further
from it.

**Registered verdicts: no, four times.** The screen is not a better Marky
on any universe (paired against the channel five it is behind on all three,
none significantly), and the bigger universe does not pay for Marky's job:
Screen A+B does not beat random on the screen's list, and its edge there is
below its edge on the 111. One thin-book artifact: on the 111 Tier A trails
A+B by 1.29%/wk (t -2.38) over 31 weeks with 1.2 names a week; on the
screen's list, where Tier A is 2.7 names a week, it is +0.29% ahead (t
+0.91). "Clean air" neither helps nor hurts at this sample.

**Predictions.** The 111 and the clean list near zero (right, and the 111's
book is as thin as the smoke run said: 2.4 signals a week). The screen's
list positive under t 2 (wrong: Screen A +0.38%, A+B -0.11%). The swing
trade positive gross (wrong: negative everywhere) with about half stopped
out (right). Tier A and A+B not significantly different (right on the
list that has A names, wrong on the 111's thin book). The across-universe
difference positive under t 2 (wrong in sign). Nothing passes (right).

**What this changes.** Nothing in the Council, and one thing in how the
screen should be read. Marky keeps the 111: Pass 9 said the team gains
nothing from a wider list, and this says the same for his job alone, on the
list the screen was built for. The screen stays what its own page says it
is, a daily watchlist for a human who checks the catalyst and the chart,
not a mechanical weekly book; run mechanically on Friday closes it does
not beat random, and its 40-day-low exit is a losing rule against random
names with the same exit. The one test this pass cannot run is the screen
as it is actually used, daily and traded the next morning: the committed
reports in `screen/reports/` supply exactly that from 2026-09-23 on, and
the Room scores them once there are weeks of them.

## Pass 15 -- exits: the owner's selling rules (registered before the full run)

The owner's rules for a multi-week position, as he wrote them on
2026-09-23: take profits a third at +10%, a third at +20% and a third at
+30%; sell everything at -8%; once the first third is sold, sell the rest
if it trails back to +5%; and sell whatever has not moved more than 5%
either way in two weeks. Every pass so far exited on a schedule (the
Council sells every Friday; Passes 13 and 14 held fixed windows or stopped
at a 40-day low), so this is the first test of managing a position.
`pass15_exits.py` has the exact rules.

**Setup.** Each pick is bought at its week's Monday open and given one
quarter (13 weeks). A rule decides when to sell, and whatever it sells goes
into SPY until the quarter ends: a rule is judged only on whether leaving
the pick beats staying in it, with the owner's benchmark as the place the
money waits. Fills on daily adjusted bars: resting orders (a stop or target
inside the day's range fills at its price, an open through it fills at the
open, and a stop and a target on the same day count the stop first);
signals read on closes (stagnation, trailing) sell at the next open; the
stop moved to +5% after the first third takes effect the next session.
0.05% a side on every purchase and sale of the pick; SPY is free.

| Rule | What sells |
|---|---|
| plain | nothing until the quarter ends (the baseline) |
| stop -8% | everything, at -8% |
| ladder | a third at +10%, +20% and +30% |
| ladder + stops | the ladder; -8% before the first third, +5% after it |
| stagnation | everything, when the last ten closes stayed within 5% either way of the close ten sessions before |
| the owner's set | ladder + stops + stagnation |
| trailing 10% | *added*: everything, at the next open after a close 10% below the highest close since entry (lets winners run) |
| stop 2 weekly SDs | *added*: a stop scaled to the name, 2 x its weekly SD (60-day daily SD x sqrt 5); a fixed 8% is a normal week for a biotech and a crash for a utility |
| earnings exit | *added*: everything, at the close before the next earnings report (extends the blackout, the one control that held) |
| the owner's set + earnings | *added* |

**Books**, as earlier passes recorded them: Ophelia (Passes 9 and 9b),
Cecil with a point-in-time P/E (Pass 11), Marky's channel five and the
owner's screen, Tier A then B (Pass 14), and the union of the three
members. The S&P 500 as of 2024-09 decides for the members; the screen's
own list decides for the screen; the 111 is reported. Random picks from the
same week's pool under the same rule (a seeded sample of up to 300) show
what a rule does to any stock. Quarters must end by 2026-09-18: 94 pick
weeks. Consecutive quarters overlap, so t is Newey-West with 12 lags.
Quarter returns are not clipped, because a rule's value lives in the tails;
one +500% name can carry a mean (the smoke run found the 111's quantum names
doing exactly that to random picks), so a rule helps only if the median
week agrees. **Survivorship, stated:** the screen's list is today's small
and mid caps, which includes names that grew into it, so the plain
quarter's right tail is flattered there and the cost of taking profits is
overstated; the clean list is the fairer judge of profit-taking.

**Predictions** (formed before a six-week smoke run on the 111, which
decides nothing here, and kept as formed):
1. No rule helps any deciding book.
2. Stagnation acts as a two-to-four-week time stop on large caps (most
   clean-list trades end by week four: a 25%-volatility stock stays inside
   a 5% band for two weeks about four times in ten) and fires on under a
   third of the screen's small caps. It costs Cecil, whose edge keeps (Pass
   13), and is within +/-1% a quarter elsewhere.
3. The stops (-8%, trailing 10%, 2 weekly SDs) close half or more of the
   clean list's trades and most of the screen's, and each costs 0% to 2% a
   quarter against the plain quarter, on the picks and on random picks
   alike: the reversal Passes 13 and 14 found.
4. The ladder rarely reaches its second third on the clean list (a +20%
   quarter is uncommon for a large cap) and moves its mean by under 1% a
   quarter; on the screen's list it sells the big winners early and costs
   1% to 4% a quarter.
5. The owner's set wins more often and loses less: a win rate above 65%
   everywhere (against about 50% to 55% for the plain quarter), under four
   weeks in the stock on the clean list, and a mean 0.5% to 3% a quarter
   below the plain quarter on every deciding book.
6. The earnings exit: within +/-1% a quarter of the plain quarter, with a
   smaller spread of outcomes.

**What counts.** A rule *helps* a book if its paired value over the plain
quarter is positive with t >= 2, both halves positive and the median week
positive. Nine rules on five deciding books are 45 tests: two or three
false passes by luck would not be a surprise, so a lone pass goes to the
forward record, not the live book. The random column is reported beside
every rule: a rule that helps random picks as much is a property of how
stocks move, usable with any picks, not a property of these.

    python lab/pass15_exits.py

## Pass 15 results -- the rules reshape the outcome, not the return

Run after the registration commit (ee414cd); `results/pass15_exits.json`.
Each cell is the rule's value over the plain quarter, per quarter, paired by
pick week (Newey-West t); the members' books on the S&P 500 as of 2024-09,
the screen on its own list:

| Rule | Ophelia | Cecil | Marky | Union | Screen A+B |
|---|---|---|---|---|---|
| *the plain quarter, vs SPY* | +0.25% | -0.26% | +0.85% | +0.40% | +0.73% |
| stop -8% | +0.68% (0.75) | +1.57% (1.48) | **-1.60% (-2.39)** | -0.12% | +0.55% (0.77) |
| ladder 10/20/30 | -0.57% | -0.70% | -0.75% (-1.85) | -0.69% (-1.94) | -1.39% (-1.17) |
| ladder + stops | -0.09% | +0.42% | **-1.75% (-2.09)** | -0.72% | -1.08% |
| stagnation | +0.55% | +0.81% | -1.04% | -0.12% | +1.11% (1.03) |
| the owner's set | +0.57% | +0.56% | -1.46% | -0.37% | -0.69% |
| trailing 10% | +0.18% | +1.66% (1.54) | -1.19% (-1.51) | -0.05% | -0.91% |
| stop 2 weekly SDs | +0.38% | +1.48% (1.28) | **-1.28% (-2.57)** | -0.09% | +0.91% (1.46) |
| earnings exit | +0.45% | -0.38% | -0.95% | -0.41% | -0.83% |
| the owner's set + earnings | +0.56% | +0.48% | -1.36% | -0.34% | -0.64% |

**Registered verdicts: no rule helps any deciding book.** The significant
numbers all run the other way, on Marky.

**What the rules actually do.** They turn a quarter into a two-to-three-week
trade and trade return for comfort. The stagnation rule ends 95% to 100% of
the clean list's trades (2.8 to 3.6 weeks in the stock) and 88% of the
screen's (5.1 weeks). The owner's set holds the pick 2.2 to 2.4 weeks on the
clean list, lifts the win rate from 54-62% to 68-73%, and halves the spread
of outcomes (the quarter's SD from 16-20% to 8.5-9.3%; the screen's from 35%
to 11%). The ladder fires more than a large-cap quarter would suggest: about
half the clean list's trades reach +10%, a quarter reach +20%, and one in
eight +30%.

**The waiting place matters.** In 2024-26 the average clean-list stock
trailed SPY by 1.01% a quarter (t -1.04): megacap leadership. So any rule
that gets out early and waits in SPY picks up part of that gap, on random
picks as much as on ours (random picks: stagnation +0.99% a quarter, the
owner's set +0.63%, the earnings exit +0.56%). Net of it (value minus the
same rule on random picks), every rule is flat to negative on the members'
picks: the owner's set -0.06% (Ophelia), -0.07% (Cecil), -2.09% (Marky),
-1.00% (Union), and +0.12% for the screen on its own list. That gap is a
regime, not a property of the rules. By rule 7 the halved spread is not
free either: it is mostly time spent in SPY, 11 weeks of the 13, which
holding SPY does without the trades.

**Stops and pullback buys do not mix.** On Marky's picks the -8% stop
cost 1.60% a quarter (t -2.39), the volatility stop 1.28% (t -2.57), and the
ladder with stops 1.75% (t -2.09), while random picks show nothing (+0.01%).
Buying a dip and then selling the next dip sells the names that were about
to bounce; Pass 13 found the same on Tuesday stops. On Cecil the stops ran
the other way, about +1.5% a quarter, all of it in the first half, and not
significant.

**The earnings exit** stays within +/-1% of the plain quarter on every
book and cuts the spread of outcomes by a fifth to a third: the cheapest
risk control here.

**The one pass anywhere, on a list that decides nothing.** Stagnation on the
screen's picks on the 111: +2.53% a quarter, t 2.78, halves +3.43% and
+1.64%, median +2.16%, and +2.87% net of random picks. It is one of about
ninety tests, on the list the screen was not built for, and on its own list
it made +1.11% (t 1.03). The screen's committed daily reports are its
forward test.

**Predictions.** 1 (nothing helps) and 6 (the earnings exit near zero with
a smaller spread) right. 2 wrong in part: stagnation fired on 88% of the
screen's trades, not under a third (volatility clusters, and 55 rolling
windows add up), and it did not cost Cecil against the plain quarter (it
did, a little, net of random picks). 3 wrong in part: the stops closed 40%
to 49% of the clean list's trades rather than half or more, and they cost
random picks nothing. 4 half right: the mean effect was under 1% a quarter,
but a quarter of the trades reached the second third. 5 half right: under
four weeks in the stock and a 68-73% win rate on the clean list, but 59% on
the screen's list, and the owner's set beat the plain quarter slightly for
Ophelia and Cecil.

**What this changes.** Nothing for the Council, whose weekly sell is
already close to where these rules converge: about two weeks in the stock.
For the owner's own positions the file supports the earnings exit and warns
against tight stops on pullback entries. Pass 16, registered before these
numbers were read, asks whether each stock's own levels do better than
generic percentages.

## Pass 16 -- exits built on each stock's own levels (registered before Pass 15's results were read)

The owner's refinements, written on 2026-09-23 while Pass 15 was running and
registered before any of its output was read, so nothing here is tuned on
it: hold while the daily MACD is positive and sell when it turns; take
profits at each stock's own resistance levels instead of a generic
10/20/30% ("honestly 9.3/18.6/27.9% would probably do better"); put the
stop under a clear support level when one sits within a reasonable range,
and scale it to the stock when none does; avoid earnings; cap the hold at a
quarter. Market direction is a cash-versus-invested question, not an exit
(the Warden's dial agrees, Pass 8). `pass16_exits.py` has the exact rules.
It reuses Pass 15's setup: a quarter per pick, sold money parked in SPY,
resting-order fills on daily bars, 0.05% a side, random picks under the
same rule, Newey-West t with 12 lags, and the median week must agree.

**Levels**, point in time, found the way the owner's screen finds its
ceilings. A swing high (low) is a close that is the highest (lowest) of the
21 closes centred on it. It counts only once the 10 closes after it exist,
so no level uses a price after the entry.
- *Resistance:* swing highs of the last two years between 4% and 50% above
  the entry, with levels within 3% of each other merged; the nearest three.
  Each target sits 1% under its level.
- *Support:* the nearest swing low of the last year between 2% and 15%
  below the entry. The stop sits 1% under it. With none in that range, the
  stop is 2 weekly SDs (Pass 15's volatility stop).

| Rule | What sells |
|---|---|
| MACD exit | everything, at the next open after the daily MACD histogram (12, 26, 9) crosses from positive to negative; a name bought with a negative histogram is held until it turns up and then down |
| support stop | everything, at the support stop (or 2 weekly SDs) |
| resistance ladder | a third at each of the nearest three resistance levels; a stock with fewer levels holds the rest |
| ladder 9.3/18.6/27.9 | a third at +9.3%, +18.6% and +27.9% |
| the owner's plan | the support stop; the resistance ladder; after the first third, a breakeven stop and a trail 2 weekly SDs under the highest close; the MACD exit; the earnings exit |
| the owner's plan, no MACD | the plan without the MACD exit |
| the owner's plan, generic ladder | the plan with 10/20/30% targets |

Pass 15's plain quarter, -8% stop, 10/20/30 ladder, trailing 10%, earnings
exit and owner's set are rerun beside these and must reproduce Pass 15's
numbers; they are reported, not re-judged.

**Predictions.**
1. No new rule helps any deciding book.
2. The MACD exit ends most trades within four weeks (a daily histogram
   runs a cycle in about a month), so it acts as a short time stop, within
   +/-1.5% a quarter of the plain quarter.
3. The support stop finds a clear support on most trades (a pullback entry
   usually sits above a recent swing low) and behaves like Pass 15's fixed
   stops: it closes about half the clean list's trades and costs 0% to 2% a
   quarter.
4. The resistance ladder lands within +/-1% a quarter of the generic
   10/20/30 ladder on every deciding book, and 9.3/18.6/27.9 within +/-0.3%
   a quarter of 10/20/30.
5. The owner's plan wins more than 60% of trades, averages under four
   weeks in the stock, lands within +/-2% a quarter of the plain quarter,
   and is not significantly different from Pass 15's owner's set.

**What counts**: as in Pass 15. A rule helps a book if its paired value
over the plain quarter is positive with t >= 2, both halves positive and
the median week positive. Seven new rules on five deciding books are 35
tests.

    python lab/pass16_exits.py

## Pass 16 results -- sell at resistance, not round numbers; the plan is the set again

Run after the registration (27806f8) and the code commit (eabf121);
`results/pass16_exits.json`. Pass 15's rules, rerun beside the new ones,
reproduced its numbers exactly. The levels were found on most trades: a
clear support on 85% of the clean list's book trades and 74% of the
screen's; resistance levels 0/1/2/3 on 20/36/21/23% of the clean list's and
6/48/30/16% of the screen's. Each cell is the rule's value over the plain
quarter, per quarter (Newey-West t):

| Rule | Ophelia | Cecil | Marky | Union | Screen A+B |
|---|---|---|---|---|---|
| MACD exit | -0.13% | -0.08% | -2.27% (-1.99) | -1.10% (-1.04) | -1.19% (-0.82) |
| support stop | +0.23% | +1.29% (1.06) | **-1.60% (-2.46)** | -0.32% | +1.23% (1.90) |
| resistance ladder | -0.44% (-1.14) | +0.29% | -0.07% | -0.08% | -1.12% (-1.02) |
| ladder 9.3/18.6/27.9 | -0.62% | -0.72% | -0.68% | -0.67% | -1.50% |
| the owner's plan | +0.21% | +0.45% | -1.78% (-1.52) | -0.64% | -1.08% |
| the plan, no MACD | +0.24% | +0.64% | -1.56% | -0.49% | -0.89% |
| the plan, generic ladder | +0.35% | +0.26% | -1.89% (-1.64) | -0.71% | -0.87% |

**Registered verdicts: no new rule helps any deciding book.**

**The owner's plan is his Pass 15 set again, a little worse.** Paired
against the set, the plan trails on every deciding book, by 0.11% to 0.39%
a quarter (significantly only on the union, -0.28%, t -2.22). It is the same
two-week trade (1.7 to 2.6 weeks in the stock) with the same 67-75% win
rate on the clean list, and the MACD exit adds nothing to it (the plan
against the plan without it: -0.03% to -0.22%, none significant). The
extra machinery ends trades before most targets and levels come into play.

**Resistance beats round numbers.** This was not a registered verdict.
Prediction 4 put the two ladders within +/-1% of each other, which held,
but did not name a direction. Paired against the 10/20/30 ladder, the
resistance ladder is ahead on all five deciding books and significantly on
three:

| Book | resistance minus 10/20/30 | Share of the position sold at targets (resistance / 10/20/30) |
|---|---|---|
| Cecil | **+1.00% a quarter (t 2.84)** | 40% / 30% |
| Marky | **+0.67% (t 2.71)** | 31% / 29% |
| Union | **+0.61% (t 3.25)** | 30% / 30% |
| Ophelia | +0.13% (t 0.31) | 18% / 33% |
| Screen A+B | +0.28% (t 0.52) | 27% / 44% |

Selling less is not the explanation where it counts. On the three
significant books the resistance ladder sold as much of the position as the
generic ladder, or more (Cecil), and still did better; on Ophelia and the
screen, where it sold less, the gain is small and not significant. The
owner's intuition holds: a level the stock has already turned at is a better
place to take profits than a round number. It is still a way to take
profits, though, and no ladder beat holding the quarter (the resistance
ladder against the plain quarter: +0.29%, -0.07%, -0.08% on those three).
The owner's 9.3/18.6/27.9 is 10/20/30 (within -0.11% to +0.07% on every
book).

**Stops depend on the setup.** The support stop helps the screen's own
picks: +1.23% a quarter over the plain quarter, t 1.90, both halves +1.2%,
the median week +1.37%, +1.52% net of the same stop on random picks, and
+0.68% (t 1.92) over the fixed -8% stop. That is just under the line and
the closest any exit came to passing for the screen: the classic trend
trader's profile, 46% winners at +23.9% against losers at -9.3%. On Marky's
large-cap pullbacks the same stop costs 1.60% a quarter (t -2.46), like
every stop in Pass 15. The screen's small-cap setups and Marky's large-cap
dips respond to stops in opposite ways.

**The MACD exit** is a two-to-four-week time stop (2.2 to 4.3 weeks in the
stock), flat for Ophelia and Cecil and a cost for Marky (-2.27% a quarter,
t -1.99). The indicator that times his entry does not time his exit.

**Predictions.** 1 right (nothing helps). 2 right on duration, wrong on
size for Marky. 3 right that support is found on most trades and closes
about half of them, wrong that it costs everywhere (it helped Cecil and the
screen). 4 right on both sizes, silent on the direction that turned out to
be consistent. 5 right on the win rate (60% on the screen's list, 67-75%
on the clean list), the time in the stock and the size, and right that the
plan does not differ significantly from the set, except on the union.

**What this changes.** Nothing for the Council: holding the quarter beat
every exit design on the members' picks in 2024-26. For the owner's own
trading, Passes 15 and 16 leave three rules with evidence behind them: if
you take profits, take them 1% under a real resistance level rather than at
a round number; exit before earnings (neutral in return, a smaller spread);
and put stops under real support on the screen's small-cap setups (a lead,
t 1.90) but not on large-cap dip-buys (a cost, t -2.4 to -2.6). The
screen's committed daily reports are the forward test for the support stop.

## Pass 17 -- a fourth chair: the Insider (registered before any run)

The owner approved a fourth member that reads what the other three cannot
see (2026-09-23). The three read the price tape, and Cecil adds the P/E. The
Insider reads what the people running each company do with their own
money: open-market purchases by officers and directors, from their SEC Form
4 filings. `fetch_insiders.py` freezes them in
`insider_purchases_2024q3_2026q2.csv` (29,174 purchases in 3,099 tickers,
from the SEC's quarterly Form 3/4/5 data sets). A row is an original Form 4
(amendments skipped), transaction code P, acquired, priced, not a 10b5-1
plan trade, with a director or officer among the reporting owners. A
purchase counts from its filing date: EDGAR's day closes at 10 pm ET, so a
filing dated the Friday before a Monday is public by that Monday.
`pass17_insider.py` has the rules.

**The Insider's two books**, up to five names from the week's tradeable
names (the usual earnings blackout):
- *Insider clusters*: names where two or more distinct directors or
  officers bought in the 30 days before the Monday; most buyers first, then
  the largest total purchase.
- *Insider buys*: names with director and officer purchases of $100,000 or
  more in total in those 30 days; the largest total first.

**Where.** The S&P 500 as of 2024-09 decides for large caps; the screen's
small and mid-cap list decides for them (survivorship as stated in Pass
14); the 111 is reported. 96 history weeks. The Council weeks are not in
this pass: the 2026 Q3 data set is published in October, so the latest
filings are June 30's, and the last history week (2026-07-06) misses three
days of filings.

**Scored as every member**: the weekly clipped edge over random books of the
same size from the same universe's tradeable names. The same books held 4
and 13 weeks (edge per week of holding, Pass 13's method) are reported
beside and decide nothing, since insider buying is known to act over
months.

**Does it look at something new?** The Insider's weekly edges against
Ophelia's, Cecil's (with a P/E) and Marky's on the clean list, scored in the
same run, and the names it shares with them. **Does it add to the team?**
Four chairs (a quarter each to Ophelia, Cecil with a P/E, Marky and the
Insider's buys; a week with no buys is three chairs) against three chairs
(a third each), weekly, on the clean list, as in Pass 7.

**Predictions.**
1. Coverage: clusters are rare on the clean list (under two names a week on
   average, none in many weeks) and commoner on the screen's list (two to
   six a week). The buys book holds three to eight qualifying names a week
   on the clean list and fills its five most weeks on the screen's list.
2. The buys book is positive on both lists and larger on the screen's
   list, under t 2 on both at one week. The clusters book is positive but
   thin, and under t 2 everywhere. Nothing passes at one week.
3. Held 13 weeks, the Insider's edge per week keeps, like Cecil's (Pass 13),
   rather than fading like Ophelia's.
4. Its weekly edges correlate with each member's between -0.2 and +0.2,
   and it shares under one name a week with any member, the most with Cecil
   (insiders buy after declines, when multiples are low).
5. Four chairs land within +/-0.1%/wk of three chairs, not significantly.

**What counts** (history). The Insider beats random with a book on a
deciding list if its clipped edge has t >= 2, is positive and both halves
are positive: two books on two lists, four tests. The fourth chair adds to
the team if four chairs beat three on the clean list, paired by week, with
t >= 2, a positive mean and both halves positive. Anything that passes goes
to the forward record first; a live Insider would read EDGAR's Form 4 feed
each Monday, since EDGAR publishes every filing the day it is filed.

    python lab/fetch_insiders.py
    python lab/pass17_insider.py

## Pass 17 results -- the Insider is Cecil by other means

Run after the registration (7f5781b) and the code commit (6f2b38d);
`results/pass17_insider.json`. History, 96 weeks, clipped edge over random
books from the same universe (Newey-West not needed: one-week books):

| List | Book | Edge (t) | Halves | Names a week | Held 4 / 13 weeks (per week) |
|---|---|---|---|---|---|
| S&P 500 as of 2024-09 | Insider clusters | +0.30% (1.33) | +0.52 / +0.08 | 3.4 | +0.11% / -0.13% |
| | Insider buys | +0.13% (0.65) | +0.27 / -0.01 | 4.8 | +0.04% / +0.04% |
| the screen's list | Insider clusters | **+0.61% (1.72)** | **+0.54 / +0.68** | 4.8 | +0.34% / -0.09% |
| | Insider buys | -0.16% (-0.48) | -0.51 / +0.20 | 5.0 | +0.08% / +0.02% |

**Registered verdicts: no, five times.** Neither book beats random on either
deciding list, and four chairs do not beat three (-0.05%/wk, t -0.86). The
nearest is the classic signal where it is supposed to work: two or more
insiders buying a small cap, +0.61%/wk with both halves positive, short of
the line.

**It is not the independent eye it was meant to be.** On the clean list its
buys correlate +0.34 with Cecil's weekly edges and -0.27 with Ophelia's (the
clusters +0.25 and -0.19). Insiders buy what is cheap and has been falling,
so the Insider is largely Cecil's value signal read through people instead
of ratios, and a contrarian against Ophelia's momentum. It shares almost no
names with any member (0.00 to 0.03 a week): the same kind of bet on
different stocks.

**It is not a slow signal here.** Held a quarter, its edge per week is gone
(-0.13% to +0.04%), unlike Cecil's (Pass 13).

**Coverage was far larger than I expected.** On the clean list, 21.6
tradeable names had director or officer purchases in any 30 days, 4.5 of
them clusters and 16.5 over $100,000; on the screen's list 70, 22 and 48.
Insider buying in large caps is common.

**Predictions.** 1 wrong (coverage, both lists' clusters and the clean
list's buys). 2 half right: nothing passes, and the clusters stay under t
2, but the buys book on the screen's list is negative, not the stronger of
the two. 3 wrong: the edge does not keep over a quarter. 4 half right:
under one shared name a week and the closest tie to Cecil, but three
correlations fall outside +/-0.2. 5 right: four chairs within 0.1%/wk of
three.

**The side result, not registered here.** In this run the three current
members in separate equal books (Ophelia, Cecil with a P/E, Marky's
channel; a third each) beat random on the clean list: **+0.34%/wk, t 2.51,
halves +0.13 and +0.55, ahead in 58 of 96 weeks**. It is not new evidence,
since it uses the same weeks and picks as Pass 13's union (+0.27%/wk, t 2.16,
equal over names), but it recurs under a second weighting. It is the
combination the lab keeps pointing to. It has been on the forward record
as Union-equal since 2026-09-22, and the forward weeks decide.

**What this changes.** The Insider does not join the Council. If the owner
wants a fourth eye, the lab's lesson is that it has to read something no
member reads *and* bet on a different kind of stock. The Insider read new
information and bet like Cecil. Its clusters book on small caps is the one
lead, and the screen's watchlist is where it could be watched.

## Pass 18 -- how much to sell at each level: overhead supply (registered before any run)

The owner's question after Passes 15 and 16 (2026-09-23): the exit rules won
more often without making more, so does the overhead above a stock tell us
how much of it to sell at each level? The diagnosis behind it: a ladder
sells the same share at every level, so it banks the stocks that stall there
and cuts the ones about to run, and the lost tails pay for the extra small
wins. If the supply sitting at a level predicts whether the stock stalls
there, the share sold should follow it. The mechanism has support: holders
who bought near a level and sit underwater sell as the price returns to
break even (overhead supply; in the literature, the capital-gains overhang
and its mirror, the 52-week-high effect). `pass18_overhead.py` has the
rules. It reuses Pass 16's levels, fills and setup: a quarter per pick,
with sold money waiting in SPY.

**Supply at a level**, point in time: of the shares traded in the two years
before the entry at closes between 4% and 50% above the entry (the overhead
zone), the share traded within +/-3% of the level, each day assigned to its
nearest level. A stock with no volume in the zone has no overhead.

**Part A, the correlation.** Every first touch of one of the nearest three
resistance levels during the quarter, with the return from the fill (1%
under the level, or the open if it gapped above) to the quarter's end minus
SPY's over the same days. The slope of that excess return on the level's
supply share, with standard errors clustered by pick week. It is measured on
random picks from each week's pool, which show how stocks behave at a level,
with the members' picks reported beside.

**Part B, two rules**, on the members' picks (the clean list decides) and the
screen's picks (its own list decides):
- *supply-weighted ladder*: at each level, sell that level's supply share of
  the original position; clean air sells nothing; the rest is held to the
  quarter's end.
- *supply-shaped thirds*: sell the same total as Pass 16's resistance ladder
  (a third per level found) but split it across the levels in proportion to
  their supply (equal thirds when none has any).

Supply-shaped thirds against Pass 16's resistance ladder isolate *where* to
sell; the weighted ladder against the shaped thirds isolates *how much*.
The 111 is not run this time.

**Predictions.**
1. The slope is negative on both lists (more supply, weaker continuation
   after the touch): clustered t <= -2 on the screen's list, weaker on the
   clean list (t between -2 and 0).
2. Supply-shaped thirds beat equal thirds on most deciding books, by +0.1%
   to +0.5% a quarter, under t 2.
3. The supply-weighted ladder sells less than the thirds and lands between
   them and the plain quarter; neither rule beats holding the quarter.

**What counts.** The correlation is real on a list if the slope is negative
with clustered t <= -2: two tests. A rule helps a book if it beats the plain
quarter under Pass 15's rule (t >= 2, both halves and the median week
positive), and supply-shaped thirds improve on the resistance ladder if
their paired difference passes the same rule: two rules against the plain
quarter and one pairing, on five deciding books, fifteen tests.

    python lab/pass18_overhead.py

## Pass 18 results -- overhead predicts the stall; sizing the sale on it barely pays

Run after the registration (42d2901) and the code commit (715f95b);
`results/pass18_overhead.json`.

**Part A: the correlation is real, on both lists (registered verdicts: yes,
twice).** Every first touch of a level by random picks, with the stock's
return over the rest of the quarter minus SPY's, by the level's supply share:

| List | Touches | Low supply | Mid | High supply | Slope per 100% supply (clustered t) |
|---|---|---|---|---|---|
| S&P 500 as of 2024-09 | 25,633 in 94 weeks | 14%: **+0.77%** | 29%: +0.32% | 71%: **-0.80%** | -1.97 points (**t -3.38**) |
| the screen's list | 30,293 in 94 weeks | 11%: **+2.20%** | 21%: +1.93% | 51%: **-0.15%** | -3.80 points (**t -3.78**) |

A stock that reaches a level where little stock changed hands keeps beating
SPY; one that reaches a level carrying most of its overhead volume stalls
there. It is the owner's "clean air" seen from the exit side, and the
capital-gains overhang in the literature. On the members' own picks the
sample is small and it is not there on the clean list (1,229 touches, slope
+0.62, t +0.37); on the screen's list it has the same sign and more size
(877 touches, -5.72, t -1.39).

**Part B: the rules barely move (registered verdicts: no, fifteen times).**
Per quarter, against the plain quarter:

| Book | resistance ladder (thirds) | supply-weighted ladder | supply-shaped thirds | shaped minus thirds | weighted minus shaped |
|---|---|---|---|---|---|
| Ophelia | -0.44% | -1.12% (-1.80) | -0.45% | -0.01% | -0.67% (-1.60) |
| Cecil | +0.29% | +0.67% (0.72) | +0.18% | -0.11% | +0.49% (1.66) |
| Marky | -0.07% | -0.05% | +0.01% | +0.08% | -0.06% |
| Union | -0.08% | -0.17% | -0.08% | +0.00% | -0.09% |
| Screen A+B (its list) | -1.12% | -0.88% | -1.13% | -0.01% | +0.25% |
| *random picks, clean list* | -0.05% | +0.10% | -0.03% | +0.01% | +0.13% |
| *random picks, screen's list* | -0.58% | -0.25% | -0.60% | -0.02% | +0.35% |

*Where* to sell does not matter once the total is fixed: splitting the thirds
by supply changed nothing (within 0.11% on every book), because most
positions reach only their first level, which usually holds most of the
zone's volume. *How much* matters a little: selling each level's supply
share, which sells more than the thirds (22% to 49% of the position against
18% to 40%) and sells heavily only into heavy levels, beats the shaped
thirds on random picks by +0.13% a quarter on the clean list and +0.35% on
the screen's list, and on the books by amounts inside the noise in both
directions. No rule beats holding the quarter.

**Why the correlation does not pay more.** The stall at a heavy level is
worth about a point and a half against a light one, spread over the rest of
the quarter, and only the part of a position actually sold at a level can
use it. Selling into a heavy level saves the -0.8%; the lost upside at light
levels, where stocks keep running, is what every ladder pays for, and the
supply-weighted ladder still sells a little there.

**Predictions.** 1 half right: negative on both lists, but significant on
the clean list too (t -3.38, not between -2 and 0). 2 wrong: shaped thirds
equal thirds. 3 wrong in part: the supply-weighted ladder sells more than the
thirds, not less, and does not land between them and the plain quarter on
three books; right that nothing beats holding.

**What this changes.** It answers the owner's question: yes, the overhead at
a level tells you whether the stock will stall there, strongly enough to
measure on 25,000 to 30,000 touches, and it points the same way as his
screen's clean-air rule. As a selling rule it is worth a tenth to a third of
a point a quarter on random stocks, and nothing measurable on the members'
picks. For his own positions the rule of thumb has evidence behind it: sell
into a level where most of the overhead volume sits, and hold through a
level with little. For the Council, holding the quarter still wins.

## Pass 19 -- Cecil's value trap (registered before any run)

The live pattern behind it (2026-09-29): ALL or HIG sat in five of the six
official books from 08-17 to 09-21, while ALL fell 12.9% and HIG 10.0%
from the 08-14 close to the 09-25 close (SPY -0.6%; the weekly panel). On
09-21 and 09-28 the Council's
trigger check blocked his names on lines that had already fired (XLF under
its 50-day average, XLRE under a set level), and on 09-28 it blocked all
three, so he had no weight in the book. His cheap-and-steady screen keeps
landing on P&C insurers at peak earnings, and the Council removes them after
the fact. The question: would a mechanical rule inside his engine do that job
better? Skip names already under their sell line, and stop stacking one
sector.

`pass19_cecil_trap.py` captures his scored table each week as Pass 12 does
(the engine's legs, point-in-time P/E) and re-ranks it offline. Each rule
removes names and gives the slot to the next-ranked name that passes; "as is"
must reproduce Pass 12's as-is five.

| Variant | Rule |
|---|---|
| as is | Pass 12's as-is Cecil: the top five of the tradeable pool |
| own 50-day gate | skip a name whose last close before the Monday is under the average of its last 50 daily closes |
| sector 50-day gate | skip a name whose sector's SPDR ETF (XLK, XLC, XLY, XLP, XLV, XLF, XLI, XLE, XLB, XLU, XLRE) last closed under its own 50-day average: the kind of line the Council's triggers used |
| one per sector | at most one name per GICS sector |
| own gate + one per sector | both |

Sectors are GICS from the S&P table, else the Council CSV, else the engine's
bucket; a name whose only label is the folded "Consumer" bucket or "Macro
Assets" has no ETF, so the sector gate never removes it. Closes are the
lab's raw daily closes (split-adjusted), as known by the Monday; a name or
ETF with fewer than 50 closes is not gated. The clean list (the S&P 500 as
of 2024-09) decides, as in Passes 11 and 12. The 111 and the 277 (the
engines' frozen list, nearest to Monday's 274, where ALL, HIG and VICI come
from) are reported. 96 history weeks; the Council weeks are reported and
decide nothing.

**Diagnostics** (reported, no verdicts):
1. *The trap.* The share of his as-is name-weeks under their own line, and
   under their sector's; and how those names do against the rest of his
   five, in excess of the pool's average: next week (clipped at +/-20%) and
   over four weeks (Monday's open to the fourth Friday's close, clipped at
   +/-40%, Newey-West t with 3 lags for the overlap).
2. *Stacking.* The share of weeks his five holds two or more names in one
   sector.
3. *Block or replace.* Three chairs (Ophelia's engine five, Cecil's,
   Marky's channel five; a third each) with the names the sector gate
   removes (a) dropped, his remaining names keeping his third and the other
   two chairs taking the book when none remain, which is roughly what the
   Council's trigger check does now, against (b) replaced by his next names.

**Predictions.**
1. His five sits under its own line in a minority of name-weeks, 20% to 35%
   (the safety leg rewards a shallow drawdown).
2. At one week the names under the line do no worse than the rest (the
   lab's short-horizon reversal: the members' losers recover more than
   random ones, Passes 13 and 15), so neither gate helps: paired within
   +/-0.1%/wk, |t| under 1.5. Over four weeks the names under the line
   trail, which a weekly verdict does not reward.
3. One per sector barely moves him (within +/-0.05%/wk) and trims his
   weekly SD a little.
4. Nothing passes.
5. Replace beats block by a little (a fuller team book), under t 2.

**What counts** (history, the clean list): a variant *helps* if its paired
clipped edge over as is is positive with t >= 2 and both halves positive
(Pass 12's rule), and replace *beats* block on the same rule: five tests,
about one in ten that one passes by luck. A variant that helps goes on the
forward record first, as Cecil-solo plus the rule; a change to his engine
goes through the freeze with the owner's yes. If nothing helps, the trigger
check stays where it is, in the Council's hands after the engines, and
diagnostic 1 says whether the insurer streak was a trap or a bad stretch.

    python lab/pass19_cecil_trap.py

## Pass 19 results -- no trap to catch, and his stacking is his edge

Run after the registration (be5e232) and the code (44d3203). The first full
run crashed before printing anything: in three weeks all eleven sector ETFs
sat under their 50-day lines, the sector gate removed every name, and the
scorer skips an empty book. The registration did not say what an empty book
is; it is scored as cash (aec3abb). `results/pass19_cecil_trap.json`. "As is"
reproduces Pass 12's five in all 96 weeks on the clean list and in 94 on the
111 (one week's fifth name, HON for PGR, and one week's order; the EPS cache
was refreshed on 09-28, after Pass 12 ran). History, 96 weeks, five names,
clipped edge over random, with the paired return difference beside it:

| Variant | clean list: edge (t) | paired vs as is (t) | same five | paired returns (t) | the 111: paired (t) | the 277: paired (t) |
|---|---|---|---|---|---|---|
| as is | +0.23% (+1.23) | | | | edge -0.01% | edge -0.09% |
| own 50-day gate | +0.05% (+0.27) | -0.18% (-1.21) | 14% | -0.20% (-1.41) | -0.11% (-0.67) | -0.09% (-0.57) |
| sector 50-day gate | +0.24% (+1.01) | +0.01% (+0.06) | 26% | -0.11% (-0.62) | +0.01% (+0.05) | +0.16% (+0.86) |
| one per sector | -0.03% (-0.15) | **-0.25% (-2.07)** | 3% | **-0.30% (-2.55)** | -0.06% (-1.01) | +0.05% (+0.46) |
| own gate + one per sector | -0.08% (-0.46) | -0.31% (-1.87) | 0% | **-0.35% (-2.13)** | -0.15% (-1.03) | +0.15% (+0.91) |
| three chairs, as is | +0.32% (+2.33) | | | | edge +0.19% | edge +0.36% |
| three chairs, block | +0.32% (+2.27) | +0.00% (+0.05) | 26% | +0.02% (+0.48) | +0.09% (+1.09) | +0.00% (+0.04) |
| three chairs, replace (vs block) | +0.32% (+2.24) | +0.00% (+0.02) | 29% | -0.02% (-0.37) | -0.11% (-1.85) | +0.06% (+0.98) |

**Registered verdicts: no rule helps, and replace does not beat block.**

**There is no trap in his history.** On the clean list 36% of his name-weeks
sit under their own 50-day line and 34% under their sector's, and those
names do no worse than the rest of his five. Against the pool's average,
the names under their own line made +0.40% the next week and +1.31% over
four weeks, the names above it +0.16% and +0.83% (paired by week +0.09%,
t 0.32; +0.30%, t 0.36). Under the sector line: +0.18% and +0.38% against
+0.28% and +1.32% (+0.02%, t 0.06; -0.30%, t -0.32). The 111 and the 277
say the same, nothing near t 2. For his kind of stock, cheap and steady,
the 50-day line does not tell a falling name from a recovering one. The
sector gate's three all-cash weeks show the other side: 2025-01-13, 04-07
and 04-14, when every ETF was under its line and his five made +3.21%,
+2.81% and +1.44%, rebounds sat out. Its drawdown was deeper than as is
(-18.0% against -10.1%).

**His stacking is his edge.** His five holds two or more names in one
sector in 97% of the clean list's weeks (90% on the 277, 38% on the 111).
One name per sector costs him 0.25%/wk (t -2.07; -0.30%, t -2.55, in
returns), his whole edge, while trimming his weekly SD from 2.45% to 2.17%;
with his own gate added, -0.31% (t -1.87). Five tests at the line leave
about one chance in five that one crosses it in either direction by luck,
so read it as strong, not proven. The mechanism is plain: his value signal
works across a sector, cheap sectors are cheap together, and a cap pushes
him down his list into worse names. Diversifying Cecil himself is the wrong
fix. The team book is where his concentration gets offset: three chairs
made +0.32%/wk (t 2.33) here, the same picks as Pass 13's union and Pass
17's side result, so not new evidence.

**Block or replace comes out the same.** Dropping the names the sector gate
flags, as the Council's trigger check does now, or letting him replace
them, gives the same three-chair book to within 0.02%/wk on the clean list
and within 0.11% on the others.

**The live episode, through the gates** (Council weeks, seen, deciding
nothing). On the clean list both gates look good over these ten weeks
(+0.58%/wk his own, +0.46% the sector's): that is the slide that motivated
the test, and a rule written after an episode fits that episode. The lines
were late even there. On the 277, the list nearest Monday's, the lab's
Cecil held ALL in nine of the ten weeks; his own-line gate first dropped it
on 09-14, and the sector gate dropped his financials only on 09-21, when
XLF closed under its 50-day. The Council's trigger check blocked ALL on
09-21 and all three of his names on 09-28: a week after his own gate would
have, and the same week as the sector gate.

**Predictions.** 1 near: a minority on the clean list, but 36% (above
20-35%), and half of his names on the 111. 2 right at one week (no worse,
and no gate helps; |t| under 1.5), wrong at four: the names under the line
do not trail there either. 3 wrong on the mean: one per sector costs him a
quarter point a week, not nothing; right that it trims the SD. 4 right:
nothing passes. 5 wrong: replace and block tie.

**What this changes.** Nothing in his engine, and no rule goes on the
forward record. The insurer slide was a real loss, but not a pattern the
price line picks out in 96 weeks of his picks. His habit of stacking one
cheap sector is where his edge comes from, so the fix for a concentrated
Cecil is the team, not a cap on him: he is one chair of three, and the
three-chair book is the best number on this list. The trigger check can
stay where it is, in the Council's hands after the engines, since blocking
and replacing come out the same; when it blocks all his names, as on 09-28,
his empty seat costs nothing on average.

## Pass 20 -- regime and event splits of the weekly edges (registered before any run)

From the 2026-10-05 deep dive of the owner's drive (private report, not in the repo). The Council's rulebooks and persona journals obey regime rules in prose that the lab never tested: a complacency trap (VIX under 16 with weak breadth), a count of risk flags, macro-event gates (CPI, FOMC), and a commodity gate (dollar over 101 and the 10-year over 4.5%). The lab has 96 weekly edges for every member and no split of them by anything the engines do not see. `pass20_regimes.py` splits them. It replays nothing: it takes each week's three fives from Pass 19's cached rows (Ophelia's engine five, Cecil's as-is five with the point-in-time P/E, Marky's channel five) and scores them again under one tag, so the members and the team are on one footing. The S&P 500 as of 2024-09 decides, the 111 is reported, and the nine Council weeks are reported and decide nothing.

**Inputs, all point in time (the last close before the week's Monday).** VIX (^VIX), the 10-year yield (^TNX), the dollar index (DX-Y.NYB), WTI (CL=F); breadth = the share of the universe's names (at least 50 closes) whose last close is above their own 50-day average. Event dates: scheduled FOMC decision days (2024-09-18, 11-07, 12-18; 2025-01-29, 03-19, 05-07, 06-18, 07-30, 09-17, 10-29, 12-10; 2026-01-28, 03-18, 04-29, 06-17; the Fed's calendar; one "unscheduled" 2025-08-22 line from the page is not used, unverified) and CPI release dates (the BLS archive, whose list starts at the September 2024 reference month, plus 2024-09-11, the August 2024 release, added by hand: 2024-09-11, then 2024-10-10, 11-13, 12-11; 2025-01-15, 02-12, 03-12, 04-10, 05-13, 06-11, 07-15, 08-12, 09-11, 10-24, 12-18; 2026-01-13, 02-13, 03-11, 04-10, 05-12, 06-10). The jobs, retail-sales and CPI-surprise flags in the owner's seven-flag rule are not used: the revised FRED series are not point in time.

**Part A, six splits** (a week is flagged or not; the Council's thresholds as written, not tuned):

| Split | Flagged week |
|---|---|
| S1 complacency | VIX under 16 and breadth under 40% |
| S2 fear | VIX over 22 |
| S3 weak breadth | breadth under 40% |
| S4 flags | three or more of: dollar under 100, 10-year under 4.3%, VIX over 22, WTI over 100 |
| S5 event week | a CPI release or an FOMC decision falls in the week, Monday to Friday |
| S6 commodity gate | dollar over 101 and the 10-year over 4.5% |

The decisive book is the team (Ophelia, Cecil, Marky, a third each). A split *matters* if the flagged weeks' mean clipped edge differs from the other weeks' by Welch |t| of 2 or more, the difference has the same sign in both halves of the 96 weeks, and the two groups' medians differ the same way. A split with fewer than 8 flagged weeks has no verdict (it is reported as untestable). The three members' rows are reported and decide nothing.

**Part B, three dials, judged by the lab's rule 7.** A dial holds the team book in unflagged weeks and cash in flagged ones: D1 on S1, D2 on S4, D3 on S5. Each is measured against the same book at a constant exposure equal to the dial's average (the rest cash): the statistic is the mean weekly difference between the dial and that exposure-matched book, with its t. A dial *helps* if t is 2 or more and both halves are positive. D2 is not run if S4 is untestable.

**Part C, the commodity gate on index history** (2003 to 2026-07, daily data, Friday to Friday). Weeks with the S6 gate on against off: the average weekly return over the next four weeks of an equal-weight basket of XLB, XLE and GLD (GLD from 2004-11) minus SPY, overlapping windows, Newey-West t with 3 lags. The gate *matters* if the gate-on weeks trail by 0.3% a week or more, |t| is 2 or more, the sign holds in 2003-2014 and 2015-2026, and the gate is on in no more than 60% of weeks.

**Predictions.**
1. No Part A split matters on the team book. With 96 weeks and a weekly SD near 2.3%, a split of 20 flagged weeks needs a gap of about 1.2 points to reach t 2.
2. S1 flags fewer than 12 weeks and its flagged weeks look worse than the rest, not significantly.
3. S5 shows no difference in mean edge.
4. No dial beats its exposure-matched book (Pass 8: cash is free and timing is not).
5. The commodity gate is on in more than a third of weeks and the basket does not trail by 0.3% a week at t 2.

Ten decisive tests (six splits, three dials, one gate), which leaves about one chance in four that one passes by luck. A pass goes to the forward record as a regime filter before anything is changed; the Council's prose rules stay as they are until then.

    python lab/pass20_regimes.py

## Pass 21 -- beat-then-fall: earnings surprise and the next days (registered before any run)

The deep dive found a hypothesis in the owner's logs and a dataset (`earnings_pull.json`, 692 quarters on 63 Council names) too small and too hand-picked to test it. This pass uses every reporter on the S&P 500 as of 2024-09 (463 names, today's survivors, survivorship stated) instead. Events come from `yfinance.Ticker.get_earnings_dates` (consensus estimate, reported EPS and surprise as of each report), report dates 2024-09-09 to 2026-07-03, with the name's prior quarters from the same table for its beat streak. `pass21_beat_fall.py` has the rules.

**Event timing.** A timestamp before 12:00 ET is a pre-market report and the reaction day is the report date; otherwise after the close and the reaction day is the next session. Pre-event close = the last close before the reaction day. Returns are dividend-adjusted and market-adjusted (minus SPY over the same days): **R1** = reaction day close over the pre-event close; **R5** = the close four sessions after the reaction day over the pre-event close; **D20** = the close 20 sessions after the reaction day over the reaction-day close (the drift). Clipped at +/-40%. Surprise is the table's percent, clipped at +/-100%; an event with no estimate or no reported figure is dropped and counted. Streak = consecutive prior quarters with a strictly positive surprise.

**Four tests**, each by reaction week (weeks with fewer than 15 events dropped), Newey-West t over weeks (4 lags), both halves, the median week:
- **V1 reaction.** The mean weekly Spearman correlation of surprise with R5. It *holds* if positive with t of 2 or more in both halves.
- **V2 beat-then-fall.** Events with a streak of 8 or more and a positive surprise, against the other events of the same reaction week, on R5. It *holds* if the gap is -0.3% or lower with t of -2 or lower, both halves negative.
- **V3 drift chair.** The top quintile of surprise in each reaction week, long from the reaction-day close for 20 sessions: D20 over random draws of the same count from that week's reporters. It *passes* if t is 2 or more, both halves are positive and the median week is positive. A pass is a candidate chair with new information, as Pass 17 asked for.
- **V4 big beat, then fall.** Surprise over +10% and a streak of 4 or more, on D20 against random same-week reporters. It *holds* if t is -2 or lower, both halves negative.

The 111 is reported beside the clean list; the clean list decides.

**Predictions.** 1: V1 holds (the announcement reaction follows the surprise; the literature's one robust result, IC near 0.1). 2: V2 does not. 3: V3 does not pass (the post-earnings drift has faded in large caps; a weak positive mean under t 2). 4: V4 does not hold. Four tests leave about one chance in five that one of V2 to V4 passes by luck.

    python lab/pass21_beat_fall.py

## Pass 22 -- the frozen 2025 lists, scored forward against random (registered before any run)

The deep dive found dated lists the 2025 bot stack wrote before any outcome existed and nobody scored. `pass22_frozen.py` scores them once, to close the book, against random draws from the same file. Expect a null. The files and their scores:

| Cohort | File and date | Score | Cohort |
|---|---|---|---|
| threshold | `threshold_analysis_20250727_211832.csv`, 2,209 names | `weighted_score` | the top decile |
| sentinel | `universe_sentinel_full_analysis_20250919_213629.json`, 2,500 names | `overall_score` | the top decile |
| jensen | `jensen_elite_discoveries_20250919_231123.json`, 2,350 names | `bagbagger_score` | the top decile |
| elizabet | `elizabet_universe_convergence_report_20250925_032815.json`, 1,968 names | `converging_strategies` | all names at or above the 90th percentile value |
| cecil v1 | `cecil_ai_council_referrals_complete.json`, 2025-09-25 | its 20 stored recommendations (the file reports 27 buys; seven are not stored) | the 20 names; random draws of 20 from the sentinel pool |
| overlap | names in the top decile of two or more of sentinel, jensen and elizabet | | random draws of the same size from the names all three cover |

**Prices.** Daily dividend-adjusted bars from Yahoo; entry at the open of the first session after the file's timestamp, exit at the close of the Friday that ends week h of 4, 13, 26 and 52. A name with no price at entry is dropped from the pool (counted); a name that stops trading before the exit is held at its last close (counted); the jensen file's own recorded price must be within 15% of the entry close or the name is dropped (it parsed English words as tickers). Returns are winsorized at the pool's 1st and 99th percentile at each horizon.

**Measure.** The cohort's mean return minus the mean of 2,000 random draws of the same size from the same pool, reported as the cohort's percentile among the draws, for the mean and for the median. A second set of draws, **matched**, takes each pick's replacement from the same pool within its cell of trailing-60-day volatility tercile and price bucket (under 5, 5 to 20, over 20 dollars). A cohort *beats random* at a horizon if its percentile is 97.5 or higher on both the mean and the median, uncontrolled and matched. It *passes* if it beats random at two or more horizons including 26 or 52 weeks.

**Predictions.** No cohort passes. The jensen and elizabet scores favor cheap volatile small caps, so against unmatched draws they will swing either way and lose their edge when matched. Six cohorts at four horizons leave about one chance in two that one horizon crosses by luck, which is why a pass needs two, including a long one. The October 2025 rubric lists (the 250-day window closes about 2026-10-22) are not in this pass; they get their own once the window has closed.

    python lab/pass22_frozen.py

## Pass 20 results -- the regime rules fire too rarely to test, and the splits that can be tested are flat

Run after the registration (d1ba76f) and the code (c7bdf18); `results/pass20_regimes.json`. The rescored team book equals Pass 19's
"three chairs, as is" to 1e-12 in all 96 weeks on both lists (the script asserts it), and the inputs were spot-checked against known
closes (2024-09-06: VIX 22.38, 10-year 3.71%). Team = Ophelia, Cecil with the P/E, Marky, a third each; clipped edge over random;
the S&P 500 as of 2024-09, 96 weeks, mean team edge +0.31%/wk.

| Split | Flagged weeks (of 96) | Team edge, flagged | other weeks | Difference (Welch t) | Halves | Median | Matters |
|---|---|---|---|---|---|---|---|
| S1 complacency (VIX under 16, breadth under 40%) | **1** | | | untestable | | | |
| S2 fear (VIX over 22) | 14 | +0.19% | +0.33% | -0.15% (-0.48) | +0.16 / -0.48 | +0.14 | no |
| S3 weak breadth (under 40%) | 18 | -0.01% | +0.39% | -0.40% (-1.40) | -0.47 / -0.19 | -0.02 | no |
| S4 flags (3 or more of 4) | **2** | | | untestable | | | |
| S5 event week (CPI or FOMC) | 36 | +0.33% | +0.30% | +0.04% (+0.14) | -0.15 / +0.26 | +0.07 | no |
| S6 commodity gate (dollar over 101, 10-year over 4.5%) | **7** | | | untestable | | | |

The 111 says the same: S2 +0.03% (t 0.07), S3 -0.21% (t -0.47), S5 +0.43% (t +1.14; halves -0.05 and +0.98), the rest untestable.

**The Council's regime rules barely fire on the history we have.** VIX was under 16 in 26 of the 96 weeks, but breadth was under 40% in
only one of them, so the "complacency trap" as the swarm rulebook states it (low VIX with weak breadth) is one week in two years. The
four market flags reached three at once in two weeks and never four. The commodity gate is on in 7 weeks of the 96 and in 18 of 1,222
weeks since 2003 (1.5%), all of them in 2023-2026. A rule that fires once or twice in two years cannot be tested on two years; its record
will be the forward one. The ten Council weeks add little: S1 and S3 flag two of them, S6 one, and S2 and S4 none. (The registered CPI
and FOMC lists end with the history window, so the Council-weeks S5 row, "0 flagged", is an artifact of the lists and means nothing.)

**What can be tested is flat.** Fear weeks, weak-breadth weeks and event weeks do not separate the team's edge by anything near t 2, in
either half, on either list. The cash dial fares no better. Skipping the 36 event weeks (D3, 62% invested) has a timing value of
+0.025%/wk (t +0.24; halves -0.07 and +0.12) against the same book at 62% exposure on the clean list, and -0.154%/wk (t -1.20) on the 111;
the exposure-matched book had the better Sharpe both times (1.94 against 1.48, and 1.89 against 0.92) and the shallower drawdown (7.7%
against 12.8%; 11.8% against 20.1%). Rule 7 again: cash does the risk reduction for free, and a calendar does not pick the weeks.
D1 and D2 had too few flagged weeks to run.

**The index leg.** With the gate on, XLB, XLE and GLD against SPY averaged -0.28%/wk over the next four weeks, against +0.01% with it off:
slope -0.29%/wk, Newey-West t -0.77, from 18 gate weeks in one decade. The size is what the rule claimed; eighteen overlapping weeks
cannot tell it from noise.

**Members (decide nothing; 18 cells a list, three at |t| of 2 or more where about one in twenty is expected by chance).** Marky in event
weeks +1.12%/wk better than other weeks (t +2.9, clean list; +0.87, t +1.5, the 111); Marky in fear weeks +0.64 (t +1.2) and +2.66 (t
+3.2, the 111); Cecil in fear weeks -0.99 (t -2.1) and -1.28 (t -1.9). The two lists agree on the signs, the sizes rest on 14 and 36
weeks, and Marky's dips bouncing and Cecil's cheap names falling further when the tape is volatile is a story that needs no new
mechanism. It is a lead to register as its own forward test, with the thresholds fixed first, not a finding.

**Predictions.** 1 right: no split matters on the team book. 2 right on the count (one week), and one week cannot show a direction. 3
right: event weeks are the same to four hundredths of a point. 4 right where it could be run. 5 half wrong: the commodity gate is not on
in more than a third of weeks, it is on in 1.5%; right that the basket's gap does not reach t 2.

**What this changes.** Nothing in the engines or the Council's rules. The Council's prose regime rules stay as they are: they have not
been shown to help, and on this history they cannot be shown, because the regimes they describe are too rare in it. The cheap test
that remains is forward: log the flags on every Monday from now (the Monday pipeline already reads VIX, the 10-year and the dollar) next to
each member's edge, and read the split after the flags have fired often enough. The Marky and Cecil volatility leads go on that list.

## Pass 21 results -- the surprise predicts the reaction, there is no beat-then-fall, and the drift after it passes

Run after the registration (d1ba76f) and the code (4c81f3e); `results/pass21_beat_fall.json`. 494 tickers, 11,626 reported quarters from
yfinance's earnings tables; 3,235 events on the S&P 500 as of 2024-09 with prices through the window (reports 2024-09-09 to 2026-07-03),
in 90 reaction weeks, 35 of them with 15 or more events (the earnings-season weeks; the rest are too thin for a cross-section).
Report timestamps split cleanly: after-close (hour 16) and pre-market (hours 5 to 9) account for nearly all of them.

| Test (S&P 500 as of 2024-09) | Result | Both halves | Verdict |
|---|---|---|---|
| V1 reaction: weekly rank correlation of surprise with R5 | mean IC **+0.234**, NW t +10.0 | +0.221 / +0.247 | **holds** |
| V2 beat-then-fall: streak of 8+ and a beat vs the rest of the week, R5 | +0.39% (t +1.08), 940 flagged events | +0.58 / +0.22 | no (and the sign is the other way) |
| V3 drift chair: top quintile of surprise, D20, vs the week's reporters | **+1.21%** per 20-session cohort (t **+2.81**), median +1.42% | +0.45 / +1.93 | **passes** |
| V4 big beat then fall: surprise over 10% and a streak of 4+, D20 | +0.70% (t +2.23), 467 events | +0.72 / +0.69 | no (a drift up, not a fall) |

Pooled by decile of surprise, returns rise from the bottom to the top at every horizon: the lowest decile (median surprise -11%) made
-2.97% on the reaction day, -3.29% over five days and -0.91% over the next twenty sessions; the top decile (+40%) +1.86%, +1.59% and
+0.87%. On the 111 (21 reaction weeks of 15+ events; a hindsight list): V1 holds (IC +0.141, t +2.68; halves +0.188 and +0.099), the
other three do not (V2 -0.11%, V3 +0.53% at t +0.40, V4 +0.60% at t +0.59).

**Checks run after reading V3 (not registered; they test the pass, they do not replace it).** The 35 weeks cluster in seven earnings
seasons and their 20-session windows overlap, which the Newey-West t only partly covers, so:

| Check | Result |
|---|---|
| Edge by season (reaction quarter) | 2024-Q4 +1.16%, 2025-Q1 **-0.52%**, 2025-Q2 +0.85%, 2025-Q3 +1.31%, 2025-Q4 +2.12%, 2026-Q1 +1.12%, 2026-Q2 +3.27%: positive in 6 of 7 |
| Season-blocked bootstrap of the weekly edges | 95% interval **+0.35% to +2.18%**; P(mean of 0 or less) 0.001 |
| Shuffle null (surprise ranks shuffled within each week) | p = 0.001 |
| After 0.10% round-trip costs | +1.11% per cohort |
| Top quintile minus bottom quintile | +2.08% over the 20 sessions |
| Correlation of its weekly edge with the weekly edges of | Ophelia +0.18, Cecil -0.06, Marky +0.15, the team +0.16 (35 weeks) |

**Predictions.** 1: V1 holds, right, but the rank correlation is +0.23, more than twice the "near 0.1" I wrote. 2: V2 does not hold,
right. 3: **V3 does not pass: wrong.** I expected the post-earnings drift to have faded in large caps to a weak positive under t 2; here it
is +1.2% a cohort at t 2.8 with the sign steady across seasons. 4: V4 does not hold, right, though not because nothing is there: the big
beats with long streaks drift up too.

**What this does not show.** One regime (2024-09 to 2026-07, a rising market with a sharp April 2025 break that is the one negative
season). Survivors only: today's S&P members that were in the index in 2024-09; names since removed or acquired are missing. The
estimates are the ones yfinance stores today. The cohort enters at the reaction-day close, which a weekly clock cannot do: a Monday-open
chair buying last week's top-surprise names gives up some days of the move. The 111, a hindsight list, does not show the drift (21 weeks,
t 0.4), which says it is not a big-cap, big-name effect, only that the data there are too thin to say more. It is a within-week
comparison, so it says nothing about whether earnings weeks are good weeks to be invested.

**What this changes.** It is the first registered result in the lab that passes its rule and reads information (earnings) that none of
the three engines reads, and its weekly edges are close to uncorrelated with theirs, which is what Pass 17 said a fourth chair has to be.
It is not yet a chair: it needs the Council's clock (Pass 23, registered next) and a forward record. Nothing in production changes.

## Pass 23 -- the drift chair on the Council's clock (registered before any run)

Pass 21's V3 passed its rule: the top surprise quintile of each earnings-season week beat that week's reporters by +1.21% over the next 20
sessions (t 2.8, six of seven seasons positive, weekly edge nearly uncorrelated with the three chairs'). But it entered at the
reaction-day close, which the Council cannot do: the Monday scan sees last week's reports and buys at Monday's open, days after the
largest part of the move. This pass asks the question that decides whether it is a chair. `pass23_drift_chair.py`; the S&P 500 as of
2024-09 decides. The 111 has too few reporters a week to run it, and the Council weeks (from 2026-07-20) fall after the last event the
earnings table covers for this window, so neither is scored.

**The chair.** Every Monday W, among names whose reaction day fell in the look-back window and that are tradeable that Monday (the same
pool the other chairs use: enough history, no report inside the coming week), rank by the table's surprise percent (clipped at +/-100%,
ties by ticker) and propose the top five, equal weight, bought at W's open. The chair abstains (the team book is then the three
chairs unchanged) when fewer than 15 tradeable candidates exist (variant A) or 30 (variant B).

| Variant | Look-back window |
|---|---|
| A, last week | reaction days in the previous Monday-to-Friday week |
| B, three weeks | reaction days in the previous 15 sessions |

**Scoring**, in the lab's way. *Hold 1:* W's open to its Friday close, the book's clipped edge over random five-name picks from the whole
tradeable pool (the lab's standard), 200 draws; also reported against random picks from the candidate set alone (which isolates the
surprise ranking). *Hold 4:* W's open to the Friday of week W+3, clipped at +/-40%, the same two comparisons, quoted as an edge per week
of holding (the four-week edge over 4). *The team:* four chairs (Ophelia, Cecil with the P/E, Marky and the drift chair, a quarter each)
against Pass 19's three chairs, by the paired difference in the books' clipped weekly returns over all 96 weeks (the chair's inactive
weeks contribute zero by construction; returns, not edges, because each book's random baseline is seeded by its name).

**What counts.** The chair *has an edge* on its active weeks if the hold-1 edge over the whole tradeable pool is positive with a
Newey-West t (4 lags) of 2 or more, both halves of the active weeks positive and the median active week positive. It *adds to the team*
if the paired four-minus-three return difference has t of 2 or more over the 96 weeks with both halves positive. Six decisive tests
(A and B on hold 1 and hold 4, and the team comparison for each of A and B on hold 1), which leaves about one chance in four that one
passes by luck; the prior is not neutral, since V3 passed, and a pass here still goes to the forward record before it is wired in.

**Predictions.**
1. Variant A, hold 1: an edge of +0.15% to +0.40% a week over the pool on 30 to 40 active weeks, t between 0.8 and 2: it does not pass.
   Most of the effect sits in the first days after the report.
2. Variant B has about twice the active weeks; its hold-4 edge is +0.3% to +0.6% a week of holding with t of 1.5 to 2.5, about even odds of
   passing.
3. Against the candidate set alone the edges are close to the full-pool ones (the pool of recent reporters is not special).
4. Four chairs minus three: +0.02% to +0.10% a week, t under 2.

    python lab/pass23_drift_chair.py

## Pass 23 results -- on the Council's weekly clock the drift chair loses; as a four-week hold it passes

Run after the registration (0400fdb) and the code (8f24fcd); `results/pass23_drift_chair.json`. The S&P 500 as of 2024-09, 96 history
weeks. Variant A was active in 34 weeks (15 or more tradeable names that reported last week), variant B in 53. Edges are clipped,
per active week; the hold-4 rows are the four-week edge divided by four.

| Test | Active weeks | Edge per week | NW t | Halves | Median | Registered verdict |
|---|---|---|---|---|---|---|
| A, last week's reporters, hold 1, vs the pool | 34 | **-0.344%** | -0.79 | -1.24 / +0.55 | -0.15 | no |
| A, hold 1, vs the candidate set | 34 | -0.336% | -0.93 | -1.03 / +0.36 | -0.06 | no |
| A, hold 4, vs the pool (per week of holding) | 34 | **+0.404%** | **+3.02** | +0.15 / +0.66 | +0.31 | **has an edge** |
| A, hold 4, vs the candidate set | 34 | +0.277% | +1.88 | -0.01 / +0.57 | +0.13 | (secondary) no |
| B, three weeks of reporters, hold 1, vs the pool | 53 | +0.179% | +0.59 | -0.15 / +0.50 | -0.04 | no |
| B, hold 4, vs the pool | 53 | +0.204% | +1.21 | +0.01 / +0.39 | +0.06 | no |
| **Four chairs minus three**, A, by clipped weekly return | 96 | **-0.094%** | **-2.10** | -0.12 / -0.07 | | no (it hurts) |
| Four chairs minus three, B | 96 | -0.042% | -1.10 | -0.07 / -0.02 | | no |

**What it says.** A name that reported last week and beat by the most, bought at Monday's open, did *worse* than the tradeable pool over
that week (-0.34%, the sign in 34 weeks flipping between halves) and then made it back and more: over four weeks +1.6% against the pool
(+0.40% a week held, t 3.0, positive in both halves). Pass 21's cohorts, which bought at the reaction-day close, showed the effect
from the first day; bought a few days later it arrives after a week of giving some back. On the Council's own clock, which re-books every
Monday and judges each week, that is a drag: adding the chair at a quarter weight lowers the team's weekly return by 0.09% a week (t
-2.10, negative in both halves). So the chair registered here is **not** a chair for the weekly Council, and the four-week result is a
different product: a separate multi-week earnings sleeve, held for a month, that the weekly scorer cannot judge.

**How much to believe the four-week pass.** It is one of six decisive tests, which leaves about one chance in four that one passes by
luck, and it is the same signal as Pass 21's V3, tested again in a different form, so the two are not independent evidence. Against
the candidate set alone (recent reporters) it falls to t 1.9, which says part of the +0.40% is that last week's reporters as a group
did better than the pool over the next month, not only that the high-surprise ones did better than the other reporters. Thirty-four
active weeks inside seven earnings seasons, one regime.

**Predictions.** 1 wrong: variant A hold 1 was a small loss, not a small gain. 2 wrong: variant B's hold-4 edge was +0.20%, below the
+0.3% to +0.6% I gave, and not close to t 2. 3 partly right: against the candidate set the edges are close to the full-pool ones at hold
1 and 0.13 points lower at hold 4. 4 wrong: four chairs minus three was negative and, for A, significantly so.

**What this changes.** The drift chair does not go into the weekly Council. If the four-week effect is worth chasing it is as a forward
record of a one-month sleeve (buy each earnings-season Monday the five highest-surprise names of the week before, hold four weeks), which
needs a scorer for four-week windows the lab does not have yet; registering that is the next step if the owner wants it. Pass 21's
reading stands: the earnings surprise carries information the three engines do not read, and what is missing is a design that uses it on
a clock where it pays.

## Pass 24 -- the heatmap's mechanical sector score against Ophelia's anchor (registered before any run)

The sector-regime-heatmap computes three of its five components by arithmetic (breadth, relative momentum, volume confirmation) and
nobody has asked whether they rank sectors better than the one input Ophelia's rotation uses. `pass24_sector_score.py`. The score, as the
heatmap defines it for the week horizon: **breadth** = the percent of the sector's names with a positive week; **relative momentum** =
the sector basket's week minus SPY's, as a rank score 0 to 100 among the eleven; **volume confirmation** = the percent of the basket's
week volume that traded in names that rose; **mechanical score** = (0.20 breadth + 0.20 momentum + 0.15 volume) / 0.55, the heatmap's
week weights without its two judgment components. Weeks run Friday close to Friday close on dividend-adjusted closes, baskets are equal
weight, and a sector needs 8 names. **Ophelia's anchor** is the basket's mean week return, in two forms: *stale*, the week before the
latest completed week, which is what the production engine reads (ophelia.py), and *fresh*, the latest completed week.

**Target.** For each Monday W, the eleven sectors' Monday-open to Friday-close basket returns minus SPY's, scored with the information
available at the preceding Friday's close. **Measure:** the weekly Spearman rank correlation across the sectors (the IC) of a score with
the target; its mean over the 96 history weeks, Newey-West t (4 lags), the two halves. Baskets: the S&P 500 as of 2024-09 by GICS sector
(decides) and the 111 by its own sector labels (the heatmap's baskets; reported).

**What counts.** The mechanical score *has signal* if its mean IC is positive with t of 2 or more and both halves positive. It *beats
the production anchor* if the paired IC difference against the stale anchor has t of 2 or more with both halves positive. Two decisive
tests; the three components alone and the fresh anchor are reported.

**Predictions.** The mean IC of the score is between -0.03 and +0.04 with t under 1.5; it does not beat the stale anchor; the fresh
anchor's IC is slightly negative (a week's sector winners give back a little); the three components are highly correlated with each
other and with last week's return, so they add no information to one another.

    python lab/pass24_sector_score.py

## Pass 25 -- the sector anchor on 27 years of ETFs (registered before any run)

Pass 9b found Ophelia's two-year edge was a regime (83% of it in 2026H1). The anchor itself, last week's best sector, can be tested on
the nine SPDR sector ETFs from 1999 (XLRE from 2015-10, XLC from 2018-06), which spans 2000-02, 2008 and 2022, none of which the 96
weeks contain. Data: dividend-adjusted daily bars from Yahoo (the 26-symbol database on the drive is raw, unadjusted and ends 2025-06,
so it is not used). `pass25_sector_history.py`. **Signals:** fresh (last completed week's return) and stale (the week before it), as in
Pass 24. **Target:** each sector's Monday-open to Friday-close return minus the equal-weight mean of the available sectors. **Measure:**
the weekly rank IC across the sectors and the top-three minus bottom-three spread; mean, Newey-West t (4 lags); and the same in three
eras (1999-2008, 2009-2017, 2018-2026) and in four windows (2000-2002, 2007-2009, 2020, 2022).

**What counts.** A signal *holds* if its mean IC is positive with t of 2 or more and the IC is positive in all three eras. Two decisive
tests (fresh, stale). **Predictions:** neither holds; the fresh anchor's IC is slightly negative over the whole sample (short-term sector
reversal) and the stale anchor's is within +/-0.01 of zero.

    python lab/pass25_sector_history.py

## Pass 26 -- Cecil's value net of rate exposure (registered before any run)

Cecil's journal says six weeks of his screen bought only rate carry (insurers, a REIT, a utility) and that he owes a duration-adjusted
measure of cheapness. `pass26_cecil_rates.py` replays his table on the S&P 500 as of 2024-09 as in Pass 12 (point-in-time P/E) and
adds each name's **rate beta**: the slope of its weekly returns on the weekly change in the 10-year yield (^TNX, in percentage points)
over the trailing 52 weeks before the Monday (at least 40 observations). **Variants:** *as is* (Pass 12's five); *residual* (each
week, regress the tradeable names' total score on rate beta and take the five largest residuals, so a name must be cheap or steady
beyond what its rate exposure explains); *capped* (the five highest scores among names whose absolute rate beta is below the
cross-section's median).

**What counts.** A variant *helps* if its paired clipped edge over as is is at least +0.10%/wk with t of 2 or more and both halves
positive. Two decisive tests. Reported, not decisive: the same difference in weeks that follow a 4-week rise of the 10-year of 20 basis
points or more (the weeks the journal is about) and the variants' weekly SD and drawdown. **Predictions:** neither helps; the capped
variant lowers his SD and costs some mean (Pass 19: his sector stacking is his edge and the rate-sensitive sectors are a large part of
it); in rising-rate weeks the residual variant is ahead of as is by a few tenths, under t 2.

    python lab/pass26_cecil_rates.py

## Pass 27 -- two of the owner's own ideas, tested as he stated them (registered before any run)

**(a) Pattern DNA: "every stock follows a pattern, unique to that stock."** `pass27_owner_ideas.py`. For each name on the S&P 500 as of
2024-09, daily bars 2023-08 to 2026-09-26, rules in one family list: long on days after which the next close-to-close return is
measured, conditioned on: each weekday (5); RSI(14) under 30; RSI(14) over 70; volume over 1.5 times its 20-day average; a gap down of
more than 1%; a gap up of more than 1%; the close within 3% of its 52-week high; the close below its 20-day average. A rule is eligible
for a name with at least 20 firing days in a window. On the first 60% of each name's days pick its best rule (the largest in-sample
mean next-day return on firing days minus the name's overall mean); on the last 40% measure that rule the same way. **Null:** assign
each name a random eligible rule instead and repeat, 2,000 times. The idea *holds* if the mean out-of-sample statistic across names is
positive and above 97.5% of the null draws, in both halves of the out-of-sample period.

**(b) The Breakfast Indicator: "food commodity collapses lead Fed pivots and flip growth leadership."** R = DBA / QQQ; its 6-month rate of
change below -10% marks a collapse. At each month-end from 2007-07 to 2026-06 (DBA lists 2007-01) compare QQQ's next three months'
return after flagged month-ends with the unflagged ones, with a block bootstrap (blocks of three months, 5,000 draws) for the
difference. The idea *holds* if the difference is positive with a bootstrap two-sided p under 0.05 and positive in each of 2008-2012,
2013-2019 and 2020-2026, each with at least three flagged months; otherwise it is reported as untestable if fewer than 12 flagged
months exist or they fall in fewer than three separate episodes.

**Predictions.** (a) Does not hold: the in-sample best rule of 20 or more is mostly noise and the mean out-of-sample statistic is within
+/-0.02%/day of the null's. (b) The flagged months cluster in a handful of episodes (2008-09, 2014-15, 2022), so the test cannot support
a verdict either way; if it can, the difference is not distinguishable from zero.

    python lab/pass27_owner_ideas.py

Eight decisive tests across the four passes (two each for Passes 24, 25 and 26; one each for 27a and 27b), which leaves about one chance
in three that one passes by luck.

## Pass 22 results -- none of the frozen 2025 lists beats random at any horizon, and the first four weeks went against all six

Run after the registration (d1ba76f) and the code (4c81f3e, 677e788, fff41c3); `results/pass22_frozen.json`; prices to 2026-10-09 from
Yahoo (dividend-adjusted). Entry at the first open after each file's stamp, exit at the close of the Friday that ends week 4, 13, 26 or
52. Returns winsorized at the pool's 1st and 99th percentile at each horizon; 2,000 random draws and 2,000 matched draws per cell.

**One deviation, made before any threshold outcome was read (fff41c3).** In the threshold file 2,088 of the 2,209 scores are exactly 0,
so "the top decile" is the whole list and every percentile was 50.0. The cohort is the 121 names whose score is above the cutoff (112
priced); the sentinel (251), jensen (298 listed; 266 after the price check), elizabet (476) and cecil v1 (20) cohorts are as registered.
The Jensen price check dropped 158 of the 2,304 names that carried a recorded price (the file parsed English words as tickers).

| Cohort (entry; priced of listed) | Horizon | Picks | Random | Matched | Picks minus random | Percentile, mean / median | Matched, mean / median |
|---|---|---|---|---|---|---|---|
| threshold (2025-07-28; 112 of 121) | 4w | -0.42% | +1.95% | +2.10% | -2.37 | 0.9 / 53.4 | 0.7 / 42.6 |
|  | 13w | +2.68% | +5.00% | +5.51% | -2.32 | 10.2 / 64.9 | 7.7 / 72.7 |
|  | 26w | +5.70% | +11.06% | +11.77% | -5.36 | 3.7 / 52.3 | 2.2 / 48.4 |
|  | 52w | +13.01% | +16.97% | +18.51% | -3.96 | 18.6 / 78.5 | 12.7 / 53.2 |
| sentinel (2025-09-22; 240 of 251) | 4w | -2.16% | -1.44% | -1.24% | -0.72 | 8.9 / 30.2 | 1.8 / 7.5 |
|  | 13w | +2.26% | +1.46% | +1.78% | +0.80 | 75.5 / 93.5 | 69.3 / 70.0 |
|  | 26w | +1.17% | +0.63% | +1.80% | +0.55 | 62.3 / 53.9 | 34.8 / 13.0 |
|  | 52w | +10.76% | +11.78% | +12.80% | -1.01 | 35.0 / 95.5 | 20.4 / 72.9 |
| jensen (2025-09-22; 240 of 266) | 4w | -2.30% | -1.64% | -1.75% | -0.66 | 11.4 / 0.0 | 25.4 / 6.4 |
|  | 13w | -1.16% | +1.03% | +0.42% | -2.19 | 2.0 / 0.2 | 15.6 / 35.0 |
|  | 26w | +0.04% | -0.47% | -1.70% | +0.51 | 61.9 / 0.0 | 76.7 / 11.2 |
|  | 52w | +14.73% | +10.65% | +9.97% | +4.08 | 95.1 / 22.4 | 91.3 / 76.5 |
| elizabet (2025-09-25; 443 of 476) | 4w | -1.46% | -0.79% | -0.75% | -0.67 | 1.6 / 0.0 | 2.9 / 0.0 |
|  | 13w | +2.38% | +1.59% | +1.91% | +0.79 | 86.7 / 99.6 | 71.8 / 95.6 |
|  | 26w | -1.15% | -0.55% | -0.22% | -0.60 | 29.4 / 36.4 | 24.9 / 47.4 |
|  | 52w | +12.14% | +10.61% | +11.94% | +1.53 | 82.2 / 99.8 | 54.4 / 93.7 |
| cecil v1 (2025-09-25; 20 of 20) | 4w | -1.36% | -0.85% | -0.63% | -0.52 | 39.5 / 42.5 | 31.8 / 33.1 |
|  | 13w | +0.59% | +2.06% | +2.41% | -1.47 | 36.2 / 11.9 | 29.2 / 6.5 |
|  | 26w | -0.76% | +0.85% | +2.33% | -1.61 | 41.7 / 48.0 | 28.5 / 35.6 |
|  | 52w | +4.93% | +12.64% | +13.61% | -7.71 | 22.4 / 27.0 | 15.1 / 12.7 |
| overlap (2025-09-25; 79 of 87) | 4w | -2.17% | -1.18% | -1.41% | -1.00 | 11.8 / 0.5 | 20.9 / 3.2 |
|  | 13w | +2.07% | +1.52% | +1.30% | +0.56 | 62.3 / 86.5 | 65.4 / 78.7 |
|  | 26w | -1.10% | -0.67% | -0.82% | -0.43 | 44.5 / 40.0 | 47.0 / 55.3 |
|  | 52w | +13.10% | +10.91% | +11.64% | +2.19 | 70.8 / 99.2 | 61.8 / 96.3 |

Registered verdicts: threshold no, sentinel no, jensen no, elizabet no, cecil v1 no, overlap no. No cell of the 24 reaches the 97.5 line
on the mean and the median together, uncontrolled and matched. The closest are jensen at 52 weeks (mean percentile 95.1, +4.1 points,
but the median pick sits at the 22nd percentile: a few lottery winners, which is what a "bagger" score selects) and elizabet at 13 and
52 weeks (median percentile 99.6 and 99.8, mean 86.7 and 82.2).

**What it says.** The lists are not informative about the next year, and one of them is informative in the wrong direction: the July
threshold file's 121 names with a nonzero score made 2 to 5 points less than random at every horizon (mean percentile 0.9, 10.2, 3.7
and 18.6; 2.2 matched at 26 weeks), the signature of a score that ranks what has already run. The jensen list lost to random at 13
weeks by 2.2 points (percentile 2.0). Cecil's first-generation list of 20 returned +4.9% over the year against +12.6% for random names
from the same pool, the 22nd percentile, which at 20 names is not distinguishable from luck but is not a result to defend either. All
six cohorts trailed random over the first four weeks (-0.5 to -2.4 points), but five of the six enter within four days of each other
(the threshold list entered two months earlier) and share the same four weeks, in which the random draws themselves lost 0.8% to 1.6%,
so those five are one market episode seen five times, not five findings.

**Predictions.** 1 right: no cohort passes. 2 half right: elizabet lost its 52-week edge when matched (mean percentile 82.2 to 54.4,
+0.2 points against the matched draws), but jensen did not (95.1 to 91.3 on the mean, and the matched benchmark was lower, so the gap
grew to +4.8 points), which means the volatility-and-price cell does not explain jensen's one good horizon; its median does.

**What this does not show.** Survivors: a name Yahoo has no bars for is out of the pool and the picks alike (119 to 253 per file), so
failures that delisted are missing from both sides. The lists were scored once, at fixed entry dates, in one rising market. The
October 2025 rubric lists, whose 250-day window closes about 2026-10-22, are not in this pass.

**What this changes.** Nothing. The 2025 bot lists are closed as scored: no input from them goes into the engines, and the next dated
lists to grade are the forward ones.

## Pass 24 results -- the heatmap's arithmetic ranks the sectors no better than last week's return, and neither ranks them at all

Run after the registration (cebc16e) and the code (144c6d4); `results/pass24_sector_score.json`. 96 history weeks, eleven GICS sectors
on the S&P 500 as of 2024-09 (decides; 19 to 75 names a sector) and nine to ten names a sector on the 111. IC is the weekly rank
correlation across sectors between each Friday-close score and the next week's Monday-open to Friday-close basket return minus SPY's;
the table is its mean, Newey-West t (4 lags) and the two halves.

| Score | S&P 500 as of 2024-09: mean IC (t), halves | Paired with the stale anchor | The 111: mean IC (t), halves |
|---|---|---|---|
| Mechanical (0.20 breadth + 0.20 momentum + 0.15 volume) | **-0.037** (-1.06), -0.048 / -0.025 | -0.052 (t -0.92) | +0.018 (+0.45), +0.080 / -0.045 |
| Breadth | -0.029 (-0.93), -0.017 / -0.041 | -0.044 (t -0.81) | -0.006 (-0.16), +0.066 / -0.078 |
| Relative momentum = fresh anchor | -0.020 (-0.54), -0.053 / +0.013 | -0.036 (t -0.60) | +0.027 (+0.68), +0.055 / -0.002 |
| Volume confirmation | -0.049 (-1.54), -0.020 / -0.079 | -0.065 (t -1.19) | -0.021 (-0.46), +0.069 / -0.110 |
| **Stale anchor (what production reads)** | **+0.016** (+0.38), -0.034 / +0.065 | | +0.044 (+1.06), +0.038 / +0.050 |

Registered verdicts: the mechanical score has signal **no**; it beats the stale anchor **no**. Neither side of the comparison is
worth anything: the stale anchor's IC is +0.016, t 0.4, negative in the first half; no score has |t| above 1.6 on either list.

**The three components are one signal.** The relative-momentum component ranks the sectors exactly as the fresh anchor does (SPY is
subtracted from every sector alike), so their IC rows are identical by construction. The mean weekly rank correlation of the mechanical
score with that ranking is +0.97 on the clean list and +0.93 on the 111, with breadth at +0.85 and +0.75 and volume confirmation at
+0.74 and +0.67: a week in which most of a sector's names rose, with the volume in the risers, is a week the sector's basket rose.
The stale anchor is nearly independent of all of them (correlations -0.03 to +0.06), because a week-old return and last week's carry
no common ranking.

**Predictions.** 1 right on the verdict, a hair wrong on the band: the mechanical IC is -0.037, below the -0.03 I gave as the floor,
with t -1.06 (inside the t 1.5 I gave). 2 right: it does not beat the stale anchor, and is behind it by 0.05. 3 right: the fresh
anchor is slightly negative (-0.020, t -0.54) on the clean list, though +0.027 on the 111. 4 right: the components are heavily
overlapping and with last week's return (+0.97 and +0.85).

**What this does not show.** It is a test of the sector-ranking arithmetic over two years and eleven cross-sectional units a week, a
small cross-section: one IC value has a standard error of about 0.3, so a sector signal of the size that would matter (an IC of
0.05) needs the 96 weeks to reach t of roughly 1.6 if it were real; it did not get there in either direction. It does not test the
heatmap's two judgment components (news and the yield-curve overlay), which are not arithmetic, or its five-day and month horizons. It is
not Ophelia's production use of the anchor (her top two sectors on the engine's eight-bucket map): that is Pass 10's ground and Pass
9b's regime finding.

**What this changes.** The heatmap's mechanical sector score does not go into Ophelia. The heatmap is a map of the week just past; for the week to come it
ranks sectors no better than a coin, which is also what the week-old anchor does here.

## Pass 25 results -- on 27 years of sector ETFs Ophelia's anchor has no signal, and last week's winners lose slightly the next

Run after the registration (cebc16e) and the code (5e262a9); `results/pass25_sector_history.json`. The SPDR sector ETFs, dividend-adjusted
daily bars from Yahoo: nine from 1998-12-22, XLRE from 2015-10-08, XLC from 2018-06-19. 1,446 weekly cross-sections from 1999-01-11 to
2026-09-21, nine to eleven sectors each. (The first download came back with XLV empty and cached the gap; the script now refuses an empty
ETF, and the cache was cleared and refetched before any number was read.) Target: each ETF's Monday-open to Friday-close return minus the
equal-weight mean of the sectors then listed. IC is the weekly rank correlation across sectors; the spread is the mean target of the
top three sectors by the signal minus the bottom three.

| Signal | Mean IC | NW t | Halves | Top 3 minus bottom 3 | 1999-2008 | 2009-2017 | 2018-2026 | Holds |
|---|---|---|---|---|---|---|---|---|
| Fresh (the week that just closed) | **-0.025** | **-2.25** | -0.013 / -0.036 | -0.120%/wk (t -2.28) | -0.011 (t -0.62) | -0.025 (t -1.25) | -0.039 (t -2.17) | **no** |
| Stale (the week before; what production reads) | **-0.005** | -0.48 | -0.006 / -0.004 | -0.048%/wk (t -0.97) | -0.014 (t -0.76) | -0.010 (t -0.57) | +0.010 (t +0.54) | **no** |

By window (IC; weekly t), fresh: 2000-2002 -0.031 (-0.92), 2007-2009 +0.009 (+0.26), 2020 -0.042 (-0.78), 2022 -0.059 (-1.53).
Stale: 2000-2002 **-0.078 (-2.73)**, 2007-2009 -0.017 (-0.49), 2020 +0.016 (+0.50), 2022 -0.021 (-0.45).

**What it says.** Neither signal holds. The stale anchor, the one Ophelia's rotation reads, ranks the next week's sector returns at
-0.005 across 27 years and 1,446 weeks (t -0.5), and it is negative in two of the three eras; the one window where it is significant
(2000-2002, t -2.7, one of eight window cells) is significantly *wrong*. Pass 9b found her two-year edge was 83% in the first half of
2026; this puts the anchor itself on 27 years of regimes it has not seen (2000-02, 2008, 2022) and finds nothing in it. The fresh signal is the surprise:
last week's winning sectors do slightly worse the following week (IC -0.025, t -2.25, the top three trailing the bottom three by
0.12% a week, negative in all three eras and growing across them). That is a weekly sector reversal, small, in the direction opposite to the
rotation's momentum premise, and it was not what the anchor was built on. It is the only one of the two decisive tests to reach |t| 2,
and in the wrong direction for the question that was registered, so nothing is claimed beyond what is stated here.

**Predictions.** 1 right: neither signal holds. 2 right on both counts: fresh is slightly negative over the whole sample (-0.025), and stale
is within 0.01 of zero (-0.005). I did not predict that the fresh reversal would clear t 2 by itself or that it would deepen from era to era.

**What this does not show.** The reversal is a sector-ETF result with the target beginning at Monday's open; it says nothing about
stock picks inside a sector, which is what the Council buys, and a reversal of 0.12% a week gross across the top and bottom three has not
been put through costs, a sector-ETF trading rule or a forward record. It is not a registered strategy. The Council's own history (Pass 24,
96 weeks) shows the same sign on the clean list (fresh -0.020) and the opposite on the 111 (+0.027); neither is distinguishable from zero.
XLRE and XLC enter the cross-section late, so the early sample is nine sectors against eleven in the last decade.

**What this changes.** Nothing in the engines. Ophelia's sector anchor has no support in the long history, which matches Pass 9b's finding
that her edge is the regime she was tested in; it stays in her rotation until a forward record says otherwise, and the question of
whether it should is the owner's. A reversal rule on weekly sector returns is the one new lead: if it is worth a test it needs its own
registration, with costs and a tradeable instrument named first.

## Pass 26 results -- netting Cecil's value for rate exposure changes nothing he can use

Run after the registration (cebc16e) and the code (0659ddb); `results/pass26_cecil_rates.json`. The S&P 500 as of 2024-09, 96 history weeks.
The as-is five equals Pass 19's in every week (the script asserts it). Rate beta is each name's slope of weekly return on the weekly change
in the 10-year yield (percentage points) over the trailing 52 weeks; every tradeable name had one in every week. "Rising-rate weeks" are
the 17 weeks that follow a four-week rise of the 10-year of 20 basis points or more.

| Variant | Edge/wk | t | Return/wk | Weekly SD | Max DD | Mean abs. beta of the five | Same five as as-is |
|---|---|---|---|---|---|---|---|
| As is | +0.231% | +1.27 | +0.527% | 2.45% | -10.1% | 0.03 | |
| Residual (largest residuals of score on rate beta) | +0.308% | +1.55 | +0.606% | 2.54% | -11.9% | 0.05 | 11% |
| Capped (best scores among names with below-median absolute beta) | +0.151% | +0.85 | +0.433% | 2.24% | -10.4% | 0.02 | 25% |

| Paired against as is | Mean | t | Halves | Returns, paired | Rising-rate weeks (17) | Registered verdict |
|---|---|---|---|---|---|---|
| Residual | **+0.077%/wk** | +0.61 | +0.101 / +0.054 | +0.080% (t +0.64) | +0.381% (t +1.37) | no |
| Capped | **-0.080%/wk** | -0.93 | -0.136 / -0.023 | -0.094% (t -1.09) | -0.178% (t -1.03) | no |

**What it says.** Neither variant clears the +0.10%/wk and t 2 bars; the residual is ahead by +0.08 and the capped five behind by 0.08, both
well inside noise on 96 weeks. The capped five does what it was built to: it holds less rate exposure (mean absolute beta 0.02 against
0.03) and the lowest weekly SD (2.24% against 2.45%), at a cost of 0.08% a week of edge and a drawdown about the same as his. The
residual variant is the surprise: the "rate-beta-neutral" ranking did not pick a lower-beta book, its five carries *more* absolute beta
than as-is (0.05 against 0.03), because the table's total score is only weakly related to rate beta and the residual rewards names whose
score is high for any reason, including the rate-sensitive ones. So the idea in his journal, a measure of cheapness net of duration,
is not what this regression delivers. In the 17 rising-rate weeks, the weeks his journal is about, the residual variant is +0.38% ahead
(t 1.4) and the capped five 0.18% behind: the right sign for the first, small, from 17 overlapping weeks.

**Predictions.** 1 right: neither helps. 2 right: the capped variant lowers his SD and costs some mean (-0.08 a week). 3 right: in rising-rate
weeks the residual is ahead by a few tenths (+0.38) under t 2 (1.37). I did not predict that the residual five would carry more rate
beta than as-is.

**What this does not show.** The registration said Cecil's journal "owes" a duration-adjusted measure; this is one version of it
(an OLS on the table's total score, trailing weekly betas to the ^TNX change), with 96 weeks and one rate regime (a 10-year between roughly
3.6% and 4.8%). A measure built on the earnings yield less the 10-year, or on a bond-proxy flag by sector, is a different test and was
not registered. Cecil's as-is edge here (+0.23%/wk, t 1.27) is Pass 19's, not a new measurement.

**A data hazard found on the way.** The first smoke run of this pass came back with a different as-is five from Pass 19's, through a
single name: CTVA. The cause is not the code: `lab.run` downloads its own unadjusted price bars when its window is not already in the
cache, and a fresh Yahoo download of CTVA now returns a close of $8.30 for 2024-09-06, where the bars cached on 2026-09-22 (Pass 19's, and
the ones this pass reads) have $55.33. That is a split-like adjustment of about 0.15, consistent with the company's announced 2026
separation, though I have not confirmed the corporate action itself. It turns CTVA's point-in-time P/E from 21 into 3 and puts it second
in his ranking every week. So any replay that asks `lab.run` for a window it has not cached will now quietly re-price CTVA, and could re-price
any other name with a corporate action since September. The script captures the full 96 weeks so the cached bars are read, and asserts
the as-is five against Pass 19's in every week; that assertion catches a change that reaches his five, not one that stays below it.

**What this changes.** Nothing in Cecil. The journal's open item (duration-adjusted cheapness) has one registered test and it says no.

## Pass 27 results -- neither of the owner's two ideas holds as he stated them, and the registered Breakfast flag fires in 42% of months

Run after the registration (cebc16e) and the code (7bda4c8); `results/pass27_owner_ideas.json`.

### (a) Pattern DNA

The S&P 500 as of 2024-09, daily dividend-adjusted bars 2023-08 to 2026-09-25, twelve rules (five weekdays, RSI under 30, RSI over 70,
volume over 1.5 times its 20-day average, a gap down or up of more than 1%, within 3% of the 52-week high, below the 20-day average).
**One reading of "eligible" to state:** a rule is eligible for a name when it fires on at least 20 days in *both* the first 60% and the last
40% of the name's days, so a rule picked in-sample can be measured out of sample; all 463 names had at least one. The statistic is the
mean next-day return on firing days minus the name's own mean next-day return in the same window. The null assigns each name a random
eligible rule (2,000 draws).

| | Chosen rule, per day | Random eligible rule, per day (SD) | Percentile among the draws | Names positive |
|---|---|---|---|---|
| In sample, the best of the rules (selection) | +0.351% | | | |
| Out of sample, all | **+0.028%** | +0.010% (0.014) | 91.3 | 53% of 463 |
| Out of sample, first half | **-0.011%** | +0.014% (0.019) | 9.4 | 47% of 441 |
| Out of sample, second half | **+0.065%** | +0.017% (0.020) | 99.1 | 51% of 457 |

Registered verdict: **does not hold** (it needs the 97.5 line in both halves; the first half is below its null). The rules picked most
were the +1% gap (143 names), Friday (99) and the volume surge (84). The best rule on the first 60% averaged +0.35% a day above the name's
own mean and kept 0.03% of it on the last 40%: 92% of the in-sample edge was the selection of the maximum of twelve noisy means.

**What it says.** A name's best rule in sample is not a pattern that persists. Over the whole out-of-sample window the chosen rule is
ahead of a random one by 0.018% a day, about 1.3 SD of the null, and that gain is the second half alone (+0.065%, the 99th percentile)
with the sign reversed in the first (-0.011%). A gap-up and volume-surge rule making money in 2026 is what a rising tape with momentum
produces whichever stock the rule was assigned to, and the first half says it did not follow the stock. **Prediction 1 right:** it does not
hold, and the all-window gap to the null (+0.018) is inside the +/-0.02%/day band I gave.

### (b) The Breakfast Indicator

DBA and QQQ month-ends 2007-07 to 2026-06 (228 months); QQQ's next three months; block bootstrap, blocks of three months, 5,000 draws,
two-sided about the bootstrap's own centre.

| Flag | Flagged months (episodes) | QQQ next 3 months, flagged vs other | Difference (95% bootstrap) | p | 2008-12 / 2013-19 / 2020-26 | Verdict |
|---|---|---|---|---|---|---|
| **Registered:** DBA/QQQ six-month change under -10% | **96 of 228** (13) | +3.78% vs +4.60% | **-0.81%** (-3.68 to +2.38) | 0.61 | -3.61 / -2.19 / +1.26 | **no** |
| Not registered: DBA's own six-month change under -10% | 34 (9) | +3.34% vs +4.41% | -1.07% (-7.41 to +4.61) | 0.72 | -1.82 / -3.79 / +11.70 (4 months) | no |

**What it says.** The flag as the idea is written does not mean what the idea says. DBA divided by QQQ falls more than 10% in six months
whenever QQQ rallies, and QQQ rallied through most of these 19 years, so the ratio rule is on in 42% of month-ends and the test
compares most months with the rest. It is testable by the registered rule (96 flagged months in 13 episodes) and the answer is no, with
the difference negative in two of three eras. The second row, which I added after seeing the first and which is not registered, asks the
question the sentence asks, a food-commodity collapse by itself, and finds 34 months in 9 episodes with the same sign: -1.07% against
other months, p 0.72, and a +11.7% positive era resting on four flagged months. **Prediction 2 half right:** I said the flagged months would cluster in two or three episodes and leave the test unable to give a verdict, which
was wrong (96 flagged months in 13 episodes make it testable), and that if it could, the difference would not be distinguishable from
zero, which was right (p 0.61).

**What this does not show.** Pattern DNA is tested in a family of twelve simple daily rules over about 2.3 years, which is a thin account
of "a pattern unique to that stock"; a richer family, longer bars, or intraday data are different tests. The Breakfast Indicator's
other half, "lead Fed pivots", is not tested at all: no pivot dates were registered, and the first half of the claim (flip growth
leadership) is read here only as QQQ's three-month return. No test of either idea was run on the Council's own picks.

**Pass 24-27 count.** Eight decisive tests (two each in Passes 24, 25 and 26, and one each for 27a and 27b): none reached its rule. One
unregistered extra (27b2) and the long-history reversal in Pass 25 are noted as such and decide nothing.

**What this changes.** Nothing in the engines. The two ideas have an honest "not on this evidence" from a registered test; if he wants
either pursued, the next step is a forward test whose rule he writes down first.

## Pass 28 -- grading the dated forward predictions already on the drive (registered before any record is read or priced)

The deep dive found falsifiable calls written before their outcomes that nobody scored. This pass reads them into a fixed record, then grades
them by rules fixed here. **Extraction first, prices never:** the agents that read the documents record what a document says and when it was
written and look at no price; grading is a script that runs after the records are frozen (`pass28_grade.py`, records stored outside this
public repo; only the counts, rules and results are published, and nothing from personal or family accounts is read or kept).

**What counts as a prediction.** A statement in a document dated before the outcome that a named instrument, index or sector will do something
checkable over a stated or default horizon: a *direction* ("SPX closes higher Friday"), a *level* ("SMH holds 600", "stays above"), a *ranking or
rating* of sectors, or a *pick* ("buy X"). Not: commentary on what already happened, a description of a position, a conditional whose
condition is not stated checkably, or a statement with no instrument. Each record carries: source, the date and (if the document says it)
the time of day it was written, the instrument, the kind, direction or level, the horizon as written, any stated confidence, and the
sentence quoted verbatim. A record whose date cannot be established from the document or its filename is dropped and counted.

**Entry and horizon.** A call written before the open (a pre-market brief) enters at that day's open; any other call at the next session's
open after its date; for the day-count and the benchmark, the instrument's adjusted closes. Horizon: as written; if none, 5 sessions for a
sector, stock or pick and 1 session for an index direction or level call. A call whose horizon has not closed by 2026-10-09 is not graded.

**Grading, by kind.**
- *Direction* (absolute): a hit if the sign of the return from entry to horizon end matches; a call of "flat" or "range" is not graded. The
  null is the base rate: the share of all windows of the same length in the instrument's own history (2018-01 to 2026-10) that went the
  stated way. Per source and kind, with 20 or more graded calls, the calls *beat the base rate* if the one-sided binomial p against that
  base rate is 0.05 or less; fewer than 20 are reported and decide nothing.
- *Level*: "holds" or "stays above X" is a hit if no close in the window is below X; "breaks below X" a hit if some close is; "reclaims" a
  hit if a close is above. Base rate: the same condition at the same distance from the entry price (in percent) over all windows of the
  same length in the instrument's own history.
- *Ranking or rating of sectors* (as the heatmap's): the weekly rank correlation of the scores with the realized excess return over SPY of the
  sector's basket, and the heatmap's own hit, partial and miss rule (its 1.0% track band) from `src/evaluate.py`; the null is 10,000 shuffles
  of the scores across the sectors in each cycle; the cycles *beat chance* if the mean IC is positive and the shuffle p is 0.05 or less
  with 8 or more cycles (so the heatmap's five cycles and their month horizons are reported and decide nothing).
- *Pick* (buy or avoid a named stock): excess return over SPY from entry to horizon end, a buy as written and an avoid with the sign flipped;
  the null is 2,000 random draws of the same number of names from the S&P 500 as of 2024-09 over the same window; with 20 or more picks the
  list *beats random* at the 97.5th percentile on the mean and the median.
- *Pre-registrations that carry their own grading rules* (the 2026-08-23 AI-capex forward test): graded as the document says, once, and
  nothing else is read into it.

**Multiple tests.** There is one decisive test per source and kind with enough calls; the count is stated in the results. Everything with
fewer than the minimum is a forward record, not a finding.

**Predictions.** (1) Direction calls beat the base rate nowhere: the hit rate on the daily index calls is within 5 points of the share
of up days. (2) The heatmap's five cycles show a mean IC between -0.15 and +0.15. (3) The AI-capex test's P1 and P2 are still "passing" and
P3 and P4 not triggered, because SPY has not closed 10% under its peak. (4) Picks lists, where there are 20 or more, do not beat random.

    python lab/pass28_grade.py

## Pass 29 -- the four-week earnings-drift sleeve, a forward record (registered 2026-10-12 before its first cohort)

The owner asked for the sleeve Pass 23 found to be registered as a forward record. It is a separate paper ledger, not a Council member and not
wired into any engine: nothing here changes what the Council buys. Origin, with the doubts on the table: Pass 21's V3 (the top surprise quintile
beat that week's reporters over the next 20 sessions, +1.21%, t 2.81) and Pass 23's variant A at hold 4 (+0.404% a week of holding over the
tradeable pool, t +3.02, both halves positive, 34 active weeks in seven seasons, one rising market). It is one of six decisive tests in Pass 23, it
is the same signal Pass 21 found, tested again, and against the candidate set alone (last week's reporters) the edge falls to +0.277% (t 1.88),
so part of it is that recent reporters as a group beat the pool.

**The rule (fixed).** Every Monday W the routine runs, in this order:
1. The universe is the S&P 500 list of 2026-09-22 (`lab/universe_sp500_2026-09-22.csv`, 503 names), frozen for the record.
2. The candidates are the names that reported in the previous Monday-to-Friday week, by the reaction day of Pass 21 (a report stamped before 12:00
   ET reacts that day, otherwise the next session; a Friday after-close report reacts on W itself and is not a candidate), that are tradeable on W
   (the Council's pool: at least four weeks of bars, no report inside the coming week) and have a surprise percent in the earnings table.
3. The sleeve is **active** only if at least 15 candidates exist. An inactive Monday is logged as inactive and buys nothing.
4. The picks are the five candidates with the highest surprise percent (clipped at +/-100, ties by ticker), one row per ticker (its best-surprise
   report in the window), equal weight, bought at W's open, sold at the close of the Friday of week W+3 (twenty-five calendar days after W).
Cohorts overlap by construction (up to four live at once); each is scored on its own.

**Data.** Dividend-adjusted daily bars from Yahoo; earnings tables from `yfinance` `get_earnings_dates` (estimate, reported EPS, surprise percent,
timestamp), fetched fresh on the run; the earnings calendar for the blackout is the lab's cache, refreshed when older than six days. Everything the
choice used is stored in the ledger on the day (the candidate set with each surprise and its timestamp, the tradeable pool), so a later revision of
Yahoo's table cannot change a logged cohort.

**The ledger.** `lab/sleeve_ledger.json` is append-only: one row per Monday the routine runs, active or not, written before any exit price exists; the
script refuses to overwrite a Monday that is already there. A row logged after that Monday's open is flagged `late` (still a valid cohort, since the
choice uses only data from before W, but the flag stays on the page). A Monday with no row is a gap and is reported as one; a gap is not
repaired afterwards. `lab/SLEEVE.md` and `lab/results/sleeve.json` are regenerated from the ledger and the bars each run.

**Scoring.** For a closed cohort, each name's return is open of W to close of the Friday of W+3, clipped at +/-40%. The cohort's *edge* is the mean of
its five minus the mean of the whole tradeable pool on the same clipped basis (random five-name draws from the pool have exactly that expectation), quoted per
week of holding (the four-week edge divided by 4), as in Pass 23. Also reported, never decisive: the edge over the candidate set, the excess over SPY, the
edge after a 0.10% round trip (0.025% a week), and the open cohorts marked to the latest close.

**Reading rules (fixed now).** Nothing is concluded before 12 closed cohorts spanning at least three earnings seasons (a season is the calendar quarter of
the cohort's Monday); a cohort is the unit, and the Newey-West t uses 3 lags because neighbouring cohorts share weeks.
- **Confirmed** if, with 12 or more closed cohorts in at least three seasons, the mean edge is at least +0.20% a week of holding (half of Pass 23's), the t is
  2 or more, and the mean is positive in at least two of the seasons.
- **Rejected** if, with 12 or more closed cohorts, the mean edge is 0 or below, or the t is -1 or lower at any count of 8 or more.
- Otherwise **keep running**, to at most 24 closed cohorts, when it is judged on the same rules and the answer is final.
A single decisive test, so no multiple-test correction. Twelve cohorts can confirm only an effect close to its historical size; a smaller true one will read
"keep running", which is the right answer. Confirmation would earn the sleeve a registration as an addition to the Council's money, not a place in it.

**Predictions.** (1) The forward edge is smaller than +0.404%: the first completed season's mean is between -0.30% and +0.50% a week of holding. (2) Of the
three outcomes, "keep running" at 12 cohorts is the likeliest (about one in two), confirmed and rejected about one in four each. (3) The edge over the
candidate set is lower than the edge over the pool in more cohorts than not. (4) The first Monday, 2026-10-12, is inactive: few S&P 500 names reported in the
week of 2026-10-05.

    python lab/forward_sleeve.py            # log this Monday (if it is not logged yet), then score every closed cohort and rewrite SLEEVE.md
    python lab/forward_sleeve.py score      # rescore only
    python lab/forward_sleeve.py smoke      # plumbing: log to a scratch ledger

### Pass 29 -- first row (2026-10-12)

The first Monday was logged at 09:07 ET, before the open (not late): 2 candidates (STZ, PEP) of 474 tradeable names, so the sleeve is inactive and bought
nothing. Prediction 4 right. Ledger `lab/sleeve_ledger.json`, page `lab/SLEEVE.md`. A smoke run of the code on the Monday of 2026-07-27 (a past week, into a scratch
ledger that is not part of the record) was plumbing only; its one cohort is not counted and decides nothing. The routine is run by hand for now: wiring it into
the Monday task needs `lab/sleeve_ledger.json`, `lab/SLEEVE.md` and `lab/results/sleeve.json` added to that task's commit list, which is the owner's call.

### Pass 29 -- wired into the Monday task (2026-10-12)

At the owner's word the sleeve now runs with the Monday forward scorer (scheduled task 8): a separate step after `forward.py` and `live_week.py`, so a failure in one does
not stop the others. Task 8 logs the Monday's row, scores every closed cohort, and commits `lab/sleeve_ledger.json`, `lab/SLEEVE.md` and `lab/results/sleeve.json` with its
other files. It runs after 11:30 AM ET, so every row will carry the `late` flag under the registered definition (a row logged after the Monday open); that is expected and does
not change a cohort's validity, since the choice uses only data from before the Monday. `forward.py` is untouched.

### Pass 29 -- erratum (2026-10-12, found by an independent audit the same day, before any active cohort)

The sleeve's registered pool is "the Council's pool: at least four weeks of bars, no report inside the coming week". The code reused `p10.pool`, which looks for the first report
on or after the previous Friday, so a name that reported on that Friday reads as reporting in zero days and is blacked out. That removes the Friday pre-market reporters the sleeve is
built from, which the registration did not intend (a name that reported last Friday is not reporting in the coming week). `forward_sleeve.py` now uses its own `sleeve_pool`, whose
first report must be strictly after that Friday (fix in the commit that carries this note). The ledger row of 2026-10-12 was logged with the old pool and stays as logged (append-only):
it had 2 candidates; with the corrected pool it would have had 3 (DAL joins), still inactive, so nothing about that row changes. Pass 23's backtest, which used the same pool, is rerun
on the corrected pool in the Pass 23 erratum below; the sleeve's thresholds are not moved. The same quirk is in `p10.pool` for every earlier pass; it matters most where the signal
is built from last week's reporters (Passes 21 and 23 and this sleeve).

## Audit errata for Passes 20-27 (2026-10-12): nothing registered flips, and four results are restated

After Passes 20-27 were written up, an independent audit read each pass's code against its registration: 8 readers (one per pass) hunting look-ahead, undisclosed
deviations, arithmetic and statistical errors, and for every finding two skeptics, one trying to refute it from the code and cached data and one sizing its effect. 31 findings
were raised; 7 were refuted as defects; 24 were confirmed. **No registered verdict flips.** Four findings change numbers or sentences materially and are restated here; the rest are prose
or disclosure corrections. Numbers marked (audit) are the audit's own reruns on the cached bars; the Pass 23 numbers I reran myself (`pass23_drift_chair.py fixed`,
`results/pass23_drift_chair_fixed.json`). The original sections above stand as written; where they differ, this section governs.

### The four that change numbers

**1. Pass 23 (and Pass 29): last Friday's reporters were blacked out of the pool.** `p10.pool` reads the first report on or after the previous Friday, so a name that reported on that
Friday counts as reporting in zero days and is excluded. The drift chair's candidate window includes that Friday's pre-market reporters, so the chair never saw them (29 of the 34 active
A weeks lost at least one; in 7 one would have made the top five). The pool for every earlier pass has the same quirk (a few names a week in season weeks, signal-independent there).
Corrected run (pool first report strictly after the Friday; draws over sorted lists, since the published hold-4 draws depended on set order and 12 reruns of the old code give +0.366% to
+0.390%, so +0.404% was a high draw; variant B as the previous 15 sessions):

| Test | As published | Corrected |
|---|---|---|
| A, hold 1 vs the pool | -0.344% (t -0.79), 34 weeks | **-0.106%** (t -0.26), 35 weeks |
| A, hold 1 vs candidates | -0.336% (t -0.93) | -0.091% (t -0.28) |
| A, hold 4 vs the pool, per week | +0.404% (t +3.02), halves +0.15 / +0.66 | **+0.512%** (t **+4.36**), halves +0.32 / +0.70 |
| A, hold 4 vs candidates | +0.277% (t +1.88), no | **+0.416% (t +3.22), has an edge** |
| A, four chairs minus three | -0.094% (t -2.10), both halves negative | **-0.075%** (t **-1.68**), both halves negative |
| B (previous 15 sessions), hold 1 / hold 4 vs the pool / team | 53 weeks: +0.179% / +0.204% (t 1.21) / -0.042% | 58 weeks: +0.203% (t 0.73) / +0.216% (t 1.58) / -0.036% (t -0.95) |

The six registered booleans are unchanged (only A hold 4 has an edge). What changes in the prose: the first-week loss is small and not significant (-0.11%, t -0.26), so "did *worse* than the
pool over that week" is withdrawn; the four-week edge is larger and clears the candidate-set comparison too (the part of the edge that was "recent reporters as a group" is now smaller);
adding the chair to the team costs 0.075% a week and is no longer significant (t -1.68), so prediction 4's "for A, significantly so" is not supported (my prediction of +0.02% to +0.10% was
still wrong in sign). This is still one test of six, the same signal as Pass 21's V3, in one rising market. The sleeve (Pass 29) keeps its registered thresholds; the corrected backtest
reference is +0.51% a week of holding (t 4.36), the as-run +0.40% (t 3.02) being the figure the thresholds were set from. The ledger row of 2026-10-12 stays as logged (see the Pass 29 erratum).

**2. Pass 22: the Jensen price check was not the registered rule.** The registration says the file's recorded price must be within 15% of the entry close. The code compared it with the
dividend-adjusted close of 2025-09-19, adjusted through 2026-10, so a name's eligibility depended on dividends paid and splits after entry. Of the 158 names it dropped, only 35 are gross
mismatches (ratio outside 0.5 to 2, the mis-parses the text described); about 123 are real tickers (high-yield names at ratios 0.72 to 0.85; SOFI, MRVL and others at 1.15 to 1.4; later reverse splits).
The sentence "the file parsed English words as tickers" is wrong for most of them. Sensitivity of the Jensen 52-week row (audit): the check as run 95.1 / 22.4 (mean / median percentile); the registered wording
on the 9/22 adjusted close 87.2 / 0.7; gross mismatches only 96.8 / 9.0; no check 94.5 / 0.9. The 13-week mean percentile is 0.6 to 11.7 (2.0 as run). **Verdict "no" in every variant**
(the median percentile never approaches 97.5). "The median pick sits at the 22nd percentile" is not stable (0.6 to 24 across variants). Separately, pools and picks are Python sets, so a rerun's percentiles move by about
1 to 4 points with the hash seed (no cell is within 25 points of the line); pick means and medians do not move.

**3. Pass 27: the half-window statistic used an undisclosed 5-firing-day minimum.** The registration's "at least 20 firing days in a window" was applied to the 60% and 40% windows; the two out-of-sample
halves used 5. At 20 per half: first half -0.042% a day (percentile 0.7, 266 names), second half +0.025% (percentile 82.5, 336 names); at 10: 25.4 and 98.9 (audit). So "the gain is the second half alone, the 99th percentile"
is not robust; the registered verdict **does not hold** is unchanged at every setting because the first half fails. Also: the real draw and the null average over different name sets (a rare chosen rule drops out more often
than the weekday rules the null picks); the "names positive" shares in the half rows used 463 as the denominator (first half 49.7% of 441, not 47%; second half 51.2% of 457); and the Breakfast test's last month-end (2026-06) gets a
three-month return that stops on 2026-09-25: without it the difference is -0.79% (p 0.62) instead of -0.81% (0.61).

**4. Pass 21: V2 could hardly say yes, and V4 and the bootstrap carry unregistered choices.** The registered V2 contrast sets long-streak beats against *every other event of the week*, misses included (27% of the pool, mean R5 -2.7%), so with no
streak effect at all it would read about +0.99% (t +8.5); the observed +0.39% sits below that. Against the other beats of the same week the gap is **-0.59% (t -1.90, halves -0.36 / -0.82; six of seven seasons negative; R1 -0.73%, t -2.46; D20 ~0)**,
which meets the size and both-halves parts of V2's rule and misses t by 0.10 (an exploratory split by surprise band puts it in the narrow beats: 0 to 5% beats -1.82%, t -5.03, four bands, post hoc). The registered verdict stays **no**, but the heading "there is no beat-then-fall"
overstated it: the registered contrast could not see it, and the corrected contrast, on data already seen, is near the line in the owner's direction. It would be a new test and needs a forward season to settle. Also: V4 used an unregistered floor of 3 flagged events a week (31 weeks, +0.70%, t +2.23; at the registered no-floor rule 35 weeks, +1.11%, t +2.77,
still positive, still "does not hold"); the event counts quoted (940 for V2, 467 for V4) were counted over all 90 reaction weeks, not the weeks tested (801 and 415); V3 compares with the week's pool mean (same expectation as the registered draws);
the season-blocked bootstrap rests on 7 clusters and is too narrow (a t on the seven season means is 3.03 on 6 df, p about 0.02, so the 0.001 and the interval's lower bound of +0.35% are overstated); and the one negative season is 2025-Q1 (reaction weeks 2025-01-13 to 02-24, windows ending before the April break), so "a sharp April 2025 break" was the wrong explanation.

### The smaller ones

- **Pass 20.** The power sentence used the SD of the weekly *return* (2.3%) where the test runs on the *edge* (1.3%): a gap of 0.7 points, not 1.2, reaches t 2. The cash dial was matched to the plain book on average exposure, which the text called "rule 7" (equal weekly SD);
  under the SD-matched rule D3's timing value is -0.122% a week (t -1.14) on the clean list and -0.266% (t -1.97) on the 111, the matched book's drawdown 10.6% and 14.8% (still shallower than the dial's), the Sharpe comparison unchanged; verdict unchanged. The member leads: 9 testable cells a list, not 18, so about 0.45
  hits at |t| of 2 are expected a list against 3 seen, and the two lists share the same weeks and names, so "the lists agree" is weak corroboration.
- **Pass 24.** The "stale anchor" is Friday-to-Friday on adjusted closes, as registered; production reads Monday-open to Friday-close on stocks. On the open-to-close basis the stale IC is +0.009 (t +0.23) on the clean list and +0.053 (t +1.32) on the 111: same verdicts. The power sentence should read "an IC of 0.05 reaches t of about 1.3" (the observed weekly IC SD is 0.35 to 0.40, not 0.3).
  The 463 names are survivors of the index (today's members added before 2024-09), which the Pass 24 text did not say (an effect on the rank IC of about 0.01 or less). `lab.download` names its cache by the ticker count only; a different list of the same length would load the wrong pickle (the Pass 24 caches were checked and match).
- **Pass 25.** The registered spread by era and window was not computed. Fresh top-3 minus bottom-3, % a week (NW t): 1999-2008 -0.138 (-1.34), 2009-2017 -0.079 (-1.13), 2018-2026 -0.141 (-1.50); windows 2000-02 -0.183 (-0.83), 2007-09 -0.171 (-0.78), 2020 -0.328 (-0.79), 2022 -0.063 (-0.27); stale 1999-2008 -0.142 (-1.63), 2009-2017 -0.011 (-0.16),
  2018-2026 +0.022 (+0.23) (audit). "Negative in all three eras and growing across them" is withdrawn as to "growing" (a trend slope of -0.0011 a year, t -0.87; era 3 minus era 1 t -1.08): the eras are not distinguishable from a constant. "Stale, what production reads" is a Friday-to-Friday ETF series, not her stock baskets on open-to-close bars
  (re-based to open-to-close the fresh IC is -0.029, t -2.63).
- **Pass 26.** 17 weeks had one or two tradeable names without a rate beta (the text said none); no as-is pick was affected. The "capped five holds less rate exposure" is measured on the same trailing betas it selects on, so it is true by construction. Ex post, the slope of each book's weekly return on the weekly change in the 10-year during its holding week is as is -0.007 (se 0.023), residual -0.003 (0.024),
  capped -0.016 (0.021): the three cannot be told apart, so out of sample the capped book is not less rate-exposed.
- **Pass 23 variant B** was three calendar weeks, not the previous 15 sessions (corrected in the rerun above).

Seven findings were refuted as defects, though several describe true limitations: the "S&P 500 as of 2024-09" list is a survivors list (today's members added before 2024-09; Pass 9b says so, and the texts of Passes 20, 24 and 27 do not repeat it, so read every result on that list with that in mind);
V4's "drifts up too" is the surprise drift of V3 rather than a streak effect (flagged beats against other surprises above 10% are about -0.9%, t -0.9, not significant); the Pass 21 market adjustment subtracts SPY as registered (a beta-adjusted version leaves V3's verdict where it is);
the Pass 22 overlap cohort covers only names all three lists contain (130 become 87, mostly names missing from the Jensen file) and that is disclosed; 294 of the 2,986 Pass 22 symbols have no Yahoo bars and are out of the pools and the picks alike; and Pass 26's as-is edge (+0.231%) is redrawn against different random baselines than Pass 19's (+0.226%), the lab's known per-book seeding.
The audit did not rerun the 2,000-draw nulls or re-derive the price data; the earnings tables and prices are Yahoo's as stored on the run dates.

## Pass 30 -- beat-then-fall, the corrected contrast, as a forward test (registered 2026-10-12 before any event after 2026-07-03 is read)

The owner asked for this after the audit of Pass 21 (see the audit errata). Pass 21's V2 set long-streak beats against every other event of the week, misses included, so it could
hardly say yes; against the other beats of the same week the gap was -0.59% (t -1.90, halves -0.36 / -0.82, six of seven seasons negative) on data that had already been seen. This pass
tests that corrected contrast on reports Pass 21 never read: every report whose reaction day falls on or after **2026-07-06** (Pass 21's events end 2026-07-03). I have not computed
anything on those events. The July to September 2026 season is already closed but unread; the October to November season and later ones are forward.

**The contrast (fixed).** Universe: the S&P 500 list of 2026-09-22 (`lab/universe_sp500_2026-09-22.csv`, 503 names). Events, reaction day, surprise (the table's percent, clipped at +/-100)
and the market-adjusted five-day return **R5** (close four sessions after the reaction day over the close before it, minus SPY over the same days, clipped at +/-40%) are Pass 21's. An event is a
**flagged beat** if its surprise is positive and the name's streak of consecutive prior quarters with a strictly positive surprise is 8 or more; an **other beat** if its surprise is positive and the
streak is under 8. Misses and zero surprises are in neither group. For each reaction week (Monday to Friday of the reaction day) with at least 15 events, at least 3 flagged beats and at least
3 other beats, the week's value is the mean R5 of the flagged beats minus the mean R5 of the other beats. A week that does not meet those floors is not counted and is listed as skipped.
Events enter an append-only ledger (`lab/beatfall_events.json`) once their five-session window has closed and are never edited; the page `lab/BEATFALL.md` and `lab/results/beatfall.json` are rebuilt
from it. Earnings tables are fetched fresh and, since Yahoo can revise them, the surprise and streak are frozen in the ledger at first sighting.

**Reading rules (fixed now).** Nothing is concluded before 12 qualifying weeks. At 12 or more: **confirmed** if the mean is -0.3% or lower, the Newey-West t (4 lags) is -2 or lower, both halves of the weeks are
negative and the median week is negative; **rejected** if the mean is 0 or higher; otherwise it keeps running, to at most 24 qualifying weeks, where the same confirm rule gives the final answer. One decisive test.
Reported, never decisive: R1, the 20-session drift D20, the contrast within bands of surprise (0 to 5%, 5 to 10%, 10 to 20%, 20% and over: the exploratory result in the audit was the 0 to 5% band), the
count of flagged beats a week, the same contrast against the registered Pass 21 V2 baseline (all other events). Two seasons, about 12 qualifying weeks, is the likely first reading, around December 2026.

**Predictions.** (1) At 12 qualifying weeks the mean is between -1.0% and +0.2% and the t between -2.5 and +0.5: the corrected contrast keeps its sign but loses most of its size (a negative mean found after
looking at seen data shrinks on new data). (2) The 0 to 5% band stays the most negative band. (3) Odds at the final reading: confirmed about one in four, rejected about two in five, the rest keeps running.

    python lab/forward_beatfall.py          # log newly closed events, then score the ledger and rewrite BEATFALL.md

### Pass 30 -- first run (2026-10-12): the unread July-August season came in the other way

The first run logged 495 events with reaction days from 2026-07-06 to 2026-09-28 whose five-session windows had closed (the July to August season was closed but unread; nothing from it
had been looked at before this run). Five reaction weeks qualify (15+ events, 3+ flagged beats, 3+ other beats); eight were skipped for the floors, and none is open. The weekly R5 gap, flagged beats minus other
beats: 2026-07-13 +1.01%, 07-20 +2.60%, 07-27 +4.30%, 08-03 +3.69%, 08-24 +1.59%: mean **+2.64%**, every week positive, the sign opposite to beat-then-fall. Reported, not decisive: R1 gap +2.92%
(flagged beats reacted better on the day itself), D20 gap -1.48%, versus all other events +2.82%, and by surprise band the gap is +5.35% in the 0 to 5% band (four weeks), +1.60%, +0.89%
and +0.06% in the higher bands (five weeks each). As a check on the pipeline, the weekly rank correlation of surprise with R5 on the same events is +0.09, +0.02, +0.28, +0.14 and +0.17, in line with
Pass 21's +0.23, and the correlation of the streak itself with R5 is positive in all five weeks (+0.29, +0.08, +0.29, +0.16, +0.37). Status: **too early** (5 of the 12 qualifying weeks the rule needs;
the October to November season is the forward part). Predictions: (1) already outside its range (a mean between -1.0% and +0.2% was predicted; five weeks read +2.64%, though the registered reading is at 12);
(2) wrong (the 0 to 5% band is the most positive, not the most negative: the exploratory in-sample result of the audit, -1.82% in that band, does not survive a new season). One season of five weeks says
little in either direction, but it is the second look in which a habitual beater did better, not worse, after a beat.

## Pass 28 results -- none of the dated forward calls on the drive beats its null, the Oracle's levels pass the registered rule on three documents, and the Perplexity longs lagged

Run after the registration (517e4b7) and the code (`pass28_grade.py`, `pass28_records.py`; the final grader is e627ce6); `results/pass28_capex_heatmap.json` and `results/pass28_records.json`. The per-call records and rows stay
outside this public repo; only counts, rules and aggregates are here, and nothing from the family-account document series was read.

**Extraction.** 72 agents (an extractor and a verifier for each of 36 sources) read three Market Direction Oracle forecasts of 2026-06-12, 06-22 and 06-26; ten Four-Sector Watchlist documents, local and Drive; 21 daily Pre-/Post-Bell pairs, 2026-09-11 to 10-09; the Kimi swarm journal;
and the Perplexity reports of October to December 2025, and looked at no price. 1,567 records came out; a second agent per source re-opened it and checked every quote, date and reading: 158 dropped, a few dates and levels fixed where the quote made the right value unambiguous, and 247 calls the extractors missed were counted and not added.
After the duplicates between the local and Drive copies (168), 1,241 records were graded by the registered rules: **959 graded**, 49 still open (window not closed by 2026-10-09), 98 with a conditional or open-ended horizon, 54 on an instrument that maps to no ticker (composites, pair calls, "precious metals"),
46 flat, hold or no-direction calls, 22 whose ticker has no bars, 7 whose level is on another scale than the instrument, 6 levels with no rule.

**Two plumbing corrections after the first partial run, disclosed.** (1) Levels read relation and direction together ("above" with direction up is a call to get above; "above" or "holds" with no direction is a call to stay above): the first read graded the Kimi journal's price targets as floors, a 0% base rate.
(2) The calls inside one document are not independent, so each test also carries a by-document check (an unregistered check, reported beside the registered rule). The random-draw universe was also extended back to 2025-09 for the Perplexity picks. None was tuned on a hit rate.

| Family and kind | Graded | Hit rate | Null | Registered test | By document |
|---|---|---|---|---|---|
| **Oracle levels** (holds/breaks, indices) | 55 | 75% | base rate 65% | **beats the base rate, p 0.031** | **3 of 3 documents above; sign test p 0.125** |
| Oracle directions | 12 | 58% | 54% | reported only (under 20) | |
| Pre-/Post-Bell levels | 79 | 53% | 57% | no (p 0.81) | 9 of 19 days above |
| Pre-/Post-Bell directions, picks, rankings | 6 / 11 / 4 | | | reported only | |
| Four-Sector levels | 34 | 32% | 36% | no (p 0.85) | 2 of 9 |
| Four-Sector sector ratings (outperform or lag SPY) | 31 | 48% | 51% | no (p 0.67) | 3 of 7 |
| Four-Sector picks (buy, avoid, trim, add) | 89 | 48% | random S&P names | no: mean **-0.84%**, median -0.19% over 5 sessions, percentile 3.2 / 25.1 | 2 of 6 documents |
| Kimi journal levels (targets) | 31 | 6% | 2% | no (p 0.16) | |
| Kimi journal picks | 37 | 43% | random S&P names | no: mean +0.83% (percentile 99.5) but median -1.22% (91.1) | 2 of 3 |
| Perplexity directions | 21 | 62% | 52% | no (p 0.25) | 4 of 6 |
| Perplexity sector/stock ratings | 139 | 53% | 50% | no (p 0.34) | 10 of 16 |
| **Perplexity picks** (day-trade longs and shorts, Oct-Dec 2025) | 393 | 47% | random S&P names | no: mean **-0.23%**, median -0.26%, percentile **0.2 / 0.2** | 12 of 26 dates |
| AI-capex pre-registration, 2026-08-23 | | | its own rules | SPY 778.57 on 10-09, +22.8% since 03-27, peak 779.09, no 5% or 10% drawdown: **P1 and P2 passing; P3 and P4 not triggered** | |
| sector-regime-heatmap manual cycles (its own grader) | 4 weekly cycles, 2 monthly | | shuffle | week IC -0.02 / +0.65 / -0.15 / -0.15, mean +0.08 (shuffle p 0.31); decides nothing (fewer than 8 cycles) | |

**Ten decisive tests** (a family and kind with 20 or more graded calls): Oracle levels, Pre-/Post-Bell levels, Four-Sector levels, ratings and picks, Kimi levels and picks, Perplexity directions, ratings and picks. Nine fail their rule. One, the Oracle's levels, passes it, and the passing is thin: its 55 calls
are four indices' support and resistance levels from **three forecasts** (29 on June 12, 10 on June 22, 16 on June 26), so the binomial over calls counts one day's market as many independent hits; each of the three documents beat its own base rate (+6, +16 and +11 points), but a sign test on three
documents cannot reach p 0.05 (0.125), and a t on the three differences (3.87, 2 degrees of freedom) has no real power. With ten decisive tests the chance of at least one pass by luck is about 40%. It is a lead for the forward record (the Oracle was built in June, before the Council), not a finding.

**What the Perplexity picks say.** The sign-adjusted mean is -0.23% a five-session window against random S&P 500 draws, the 0.2nd percentile, and the null deserves care: it is a draw of random S&P 500 names with the pick's own sign. I did not print the null's mean, but if the average S&P name lagged the cap-weighted SPY over those weeks, which the picks' own numbers suggest, random *shorts* would start ahead of SPY by default and drag the percentile down for any book with shorts in it, so the 0.2 likely overstates how bad the picks were. Split by side: 319 longs hit 43.6% (mean -0.75% against SPY), 74 shorts hit 63.5% (the short side made about +2.0%). So the longs lagged SPY and the shorts worked; 328 of the 393 calls are from November 2025 on 26 dates, one regime. No evidence of skill, and no
reason to read the 0.2 as skill in the wrong direction.

**Predictions.** 1 mostly right: direction calls do not beat the base rate anywhere; the Oracle (58% against 54%) is inside the 5 points I gave, the Perplexity directions (62% against 52%) are not, though at p 0.25. 2 right: the heatmap's mean IC is +0.08. 3 right: P1 and P2 passing, P3 and P4 not triggered. 4 right: no picks list of 20 or more beats random (Kimi's mean percentile of
99.5 fails on the median).

**What this does not show.** The extractors coded judgement calls (a lean label mapped to up or down; support and resistance mapped to holds and below; paired range bounds dropped where true by construction), and the verifiers counted 247 calls they missed. The grader's instrument map and horizon parser are fixed rules on names and phrases, but an unmapped, conditional or open-ended call is simply absent
(about 22% of the records). The Oracle forecasts are LLM-written, the Four-Sector and Pre-/Post-Bell documents are his own and his father's process in prose, and the Kimi and Perplexity files are LLM research. None of this reads the Council's own picks, and one season, mostly rising, is all there is.

**What this changes.** Nothing in the engines. Two things go on the list to watch forward: the Oracle's level calls (a handful more forecasts would test them properly) and the heatmap's grader, which needs 8 cycles to decide; at one cycle a week that is early November.

### Pass 30 -- wired into the Monday task (2026-10-12)

At the owner's word `forward_beatfall.py` now runs as step 3d of the Monday forward-scorer task (scheduled task 8), after the sleeve so it reuses the earnings tables the sleeve just fetched, and the task commits
`lab/beatfall_events.json`, `lab/BEATFALL.md` and `lab/results/beatfall.json` with its other files. The event ledger is append-only; the task reports the status, the new events, the qualifying weeks and the
band rows each Monday and concludes nothing before 12 qualifying weeks. Budget 50 minutes.

## Pass 31 -- ten years of earnings events from Finviz: the surprise tests again, two definitions of surprise (registered 2026-10-12 before any return or correlation is computed)

The owner connected Finviz Elite and asked for the earnings work to be redone on a longer, definition-consistent history. Two reasons it is worth a registered pass rather than a swap.
(1) The seven earnings seasons behind Passes 21, 23 and 30 are all there is on the yfinance table (24 quarters a ticker); Finviz's earnings calendar reaches back to at least 2012 with the
estimate, the actual, the surprise percent, revenue and the report's timestamp. (2) Finviz's surprise is not yfinance's: on one large bank's July 2026 report the two surprises differed by more than thirty points (the reported figure differs between the vendors), and consensus estimates differ for others
(individual vendor figures removed from this public text on 2026-10-12: the repo is public and the data is licensed for the owner's own use; the earlier commits still carry them). So this is also the test of whether the findings belong to the data vendor.

**Data (private).** `lab/finviz_history.py fetch` walks the calendar in 12-week windows (a call returns about 13 weeks) from 2015-10 to 2026-10 into `lab/cache/finviz_earnings_calendar.json`,
which is gitignored: Finviz data is for the owner's own use and this repo is public, so only counts and aggregate results are committed. Prices are Yahoo's dividend-adjusted daily bars for the same names.

**Universe, and the look-ahead it must avoid.** The S&P 500 list of 2026-09-22 (503 names) with an event counted only if the name's `date_added` (`lab/universe_sp500_added_2026-09-22.csv`) is before the
event's reaction day (blank means long-standing). That removes the bias of testing 2016 on names that joined the index later, the way the 2024-09 list did not need to. Removed and delisted names are
still absent (survivors only, stated), and the calendar's own "Market Cap" is today's, not point in time, so it is not used for membership.

**Events, as in Pass 21.** A report stamped before 12:00 ET reacts that day, otherwise the next session; R1, R5 and D20 are market-adjusted (SPY) dividend-adjusted returns clipped at +/-40%; surprise is the
calendar's "EPS Surprise" percent clipped at +/-100 (an event with no surprise is dropped and counted, about 14% of rows in the sample probed). **Streak** (for T4) is the number of consecutive prior quarters with a
strictly positive surprise in the same table. Reaction weeks with fewer than 15 events are dropped. **Samples:** S1, reaction days 2016-01-04 to 2026-07-03 (Pass 21's last event is 2026-07-03, and everything from 2026-07-06
is Pass 30's forward sample, left alone). S2, the part of S1 that overlaps the yfinance table, 2020-10-01 to 2026-07-03, on the 2024-09 list's cached yfinance events. T4 uses S1 from 2018-01-02, when eight prior quarters exist.

**Decisive tests, each with the rule its earlier pass registered (Newey-West t, 4 lags, both halves, the median week).**
- **T1, the reaction (Pass 21 V1).** The weekly rank correlation of surprise with R5 on S1: holds if the mean is positive with t of 2 or more and both halves positive.
- **T2, the drift chair (Pass 21 V3).** The top quintile of surprise in each reaction week, long from the reaction-day close for 20 sessions, D20 against the week's pool mean: passes if t is 2 or more, both halves and the median week positive.
- **T3, the sleeve on the Monday clock (Pass 23 variant A, hold 4, as the sleeve runs it).** Each Monday, last week's reporters tradeable that Monday (at least four weeks of bars; no report inside the coming week, the first report taken strictly after the previous Friday; the 15-candidate floor), the five highest surprises, equal weight, Monday's open to the Friday of week W+3,
  clipped at +/-40%, against the mean of the tradeable pool, per week of holding: has an edge if t is 2 or more, both halves positive, the median positive.
- **T4, beat-then-fall, the corrected contrast (Pass 30's rule on history).** Flagged beats (positive surprise after a streak of 8 or more) against the other beats of the same reaction week on R5, weeks with 3 or more of each: holds if the mean is -0.3% or lower, t is -2 or lower, both halves and the median week negative, with at least 12 weeks.
  The forward test of Pass 30 keeps running unchanged; this reads the same contrast on 2018 to 2026-07, and does not touch its rule or its record.

**Reported, never decisive.** The same T1 and T2 on yfinance's surprise over S2, so the two definitions are read on the same events; the share of overlapping events whose two surprises have the same sign and the weekly rank correlation between them; T2 and T3 by calendar year and by half-decade; a season-blocked bootstrap of T2; and T2 with revenue surprise in place of EPS surprise.
Four decisive tests; the chance that a rule-free signal passes one of them is about one in five, and T1 is expected to hold.

**Predictions.** (1) T1 holds (a weekly IC of +0.1 to +0.3). (2) T2 passes, with a smaller mean than Pass 21's +1.21% per cohort (between +0.3% and +1.0%): the effect is real but was flattered by the seven seasons that found it. (3) T3 has an edge weaker than the corrected backtest's +0.51% a week of holding
(between +0.1% and +0.4%), a coin-flip whether t reaches 2. (4) T4 does not hold: the mean is above -0.3% (the in-sample -0.59% on seen data is mostly the sample). (5) The two definitions agree in sign on at least 80% of overlapping events, and give the same verdict on T1 and T2.

    python lab/finviz_history.py fetch      # the private data build (no returns)
    python lab/finviz_history.py            # the four tests and the comparisons

## Pass 31 results -- the surprise predicts the reaction as before, but the drift is a recent-regime effect, and beat-then-fall holds by a hair

Run after the registration (7b6c4d7) and the code (`finviz_history.py`, committed before the run); `results/pass31_finviz_history.json` (aggregates only; the calendar and every event row stay in the gitignored cache).
The calendar gave 20,845 rows for 502 of the 503 names on the 2026-09-22 list (PSKY, the renamed Paramount, is absent), with a surprise on over 98% of them; 17,041 events from reaction days 2016-01-04 to 2026-07-03 have a surprise, Yahoo
prices and index membership at the time (214 reaction weeks with 15 or more events, 42 earnings seasons against the seven behind Passes 21 and 23). A 40-name smoke run was read for plumbing, and after the full run I replayed the pipeline on the
window Passes 21 and 23 had measured (below). Delisted names are still absent: survivors only.

| Test (S1: 2016 to 2026-07-03) | Result | Halves | Median | Registered rule | Verdict |
|---|---|---|---|---|---|
| **T1** reaction: weekly rank IC of surprise with R5 | mean **+0.207**, t +15.7 (214 weeks) | +0.218 / +0.196 | +0.221 | positive, t 2+, both halves | **holds** |
| **T2** drift: top surprise quintile, D20 vs the week | **+0.18%** per cohort, t **+0.80** | +0.11% / +0.25% | +0.07% | t 2+, both halves and median positive | **no** |
| **T3** the sleeve on the Monday clock (hold 4, per week of holding) | **+0.096%**, t **+1.18** (214 weeks) | +0.07% / +0.12% | +0.01% | t 2+, both halves and median positive | **no** |
| **T4** beat-then-fall, flagged beats minus other beats, R5 (2018 on) | **-0.310%**, t **-2.05** (171 weeks) | -0.25% / -0.37% | -0.56% | mean -0.3% or lower, t -2 or lower, both halves and median negative | **holds** (by 0.01 point and 0.05 of t) |

**Drift.** The season-blocked bootstrap of T2 over 42 seasons gives a 95% interval of -0.22% to +0.63% and P(mean 0 or less) 0.20. By year, the weekly top-quintile edge reads -0.21, +0.33, -0.39, -0.62, -0.11, +1.24, -0.16, -0.09, +0.51, +0.50, +1.48%
(2016 to 2026, the last eleven weeks only); by period, 2016-19 -0.24%, 2020-23 +0.22%, 2024 to mid-2026 +0.70%. The +1.21% of Pass 21 sat in the part of the sample where the effect is largest, and it does not generalize back: **the post-earnings drift
here is a recent-regime result, not a decade-long edge.** The sleeve's Monday-clock backtest tells the same story: +0.096% a week of holding over ten years (t 1.18), below its own +0.20% confirm threshold, against +0.32% (t 3.01) on 2024-09 to 2026-07 in this pipeline.
Revenue surprise carries the reaction (T1 IC +0.168) and no drift (T2 -0.04%, t -0.21).

**Beat-then-fall.** The corrected contrast is negative in seven of nine years (2018 -0.23%, 2019 +0.21, 2020 -0.52, 2021 -0.63, 2022 -0.08, 2023 -0.84, 2024 +0.11, 2025 -0.41, 2026 to July -0.51), so it is not one regime's accident, and it is small: a
habitual beater's beat trails other beats by about 0.3% over five sessions. It clears the registered rule by a hair on both numbers, one of four decisive tests, and the forward test of Pass 30 (reports from 2026-07-06) read +2.64% in its first five weeks, the other way: the
two together say "small and not settled", and Pass 30 keeps running on its own rule.

**The two definitions of surprise agree.** On the 2020-10 to 2026-07 overlap with the yfinance tables (9,998 events on both): the surprises have the same sign on 95%, and the weekly rank correlation between them averages 0.90. On that sample T1 holds under both (IC +0.199 Finviz, +0.203 yfinance) and
T2 passes under both (+0.63%, t 2.04 and +0.60%, t 2.08), so **no finding in Passes 21 to 30 belongs to the data vendor**, and the JPM-sized disagreements are the tail. (T2 passes on this half-decade and fails on the decade, which is the point above.)

**Pipeline check against the old windows.** On Pass 21's window (2024-09-09 to 2026-07-03) the new pipeline gives T1 IC +0.219 (published +0.234), T2 +0.80% over 38 weeks (published +1.21%, 35 weeks, t 2.37 against 2.81); on Pass 23's window the Monday-clock sleeve gives +0.32% a week (t 3.01) against the
corrected +0.51% (t 4.36). Same signs and shapes at about 60 to 65% of the size, from the definition, the larger universe (503 names, with membership dates, against 463) and the week count; not a bug of the kind the audit found.

**Predictions.** 1 right: T1 holds, IC +0.21. 2 wrong: T2 does not pass; I expected a smaller positive effect that still cleared t 2 and got +0.18% at t 0.80. 3 wrong, narrowly: the sleeve's ten-year edge is +0.096% a week, just under the +0.1% to +0.4% I gave, and t is 1.18. 4 wrong: T4 holds, by the thinnest margin.
5 right: 95% sign agreement and the same verdicts under both definitions.

**What this does not show.** Survivors only (delisted and removed names are not in the universe); the calendar's estimates and actuals are Finviz's as stored today; membership uses the current members' `date_added`, which removes the look-ahead of later additions but not the survivorship
of removals; the sample ends 2026-07-03, so the unread July to September 2026 season belongs to the forward tests. Four decisive tests, two pass: T1, which was expected to, and T4, which passes by the margin of rounding.

**What this changes.** The earnings-drift story weakens: the one signal that passed its rule in Passes 21 to 23 does not hold across ten years, and the sleeve (Pass 29) rests on the recent regime; it keeps running as registered, and "keep running" or "rejected" is the likelier outcome. The reaction signal (surprise to R5) is solid and
the feed can move to Finviz without changing any conclusion. Beat-then-fall gets a small, near-threshold historical support and a conflicting first forward look; both keep accumulating.

## Pass 31 audit errata (2026-10-12): the numbers reproduce; beat-then-fall's "holds" is on the line, and the vendor claim is narrowed

An independent audit (six readers, two skeptics per finding, 104 agents) read the Pass 31 code and the new Finviz connector modules. It reproduced every registered number exactly from the cached calendar and bars (T1 IC +0.2070, t 15.66; T2 +0.179% per cohort, t 0.80;
T3 +0.0960% a week, t 1.18; T4 -0.3100%, t -2.048, 171 weeks) and found no look-ahead (streaks use only earlier rows; a truncation test on 3,000 events left every streak unchanged; membership is strict; the blackout's use of 2026-dated report dates is immaterial: +0.0960%
with it, +0.0951% with no blackout, +0.0962% from past-only dates). It raised 49 findings: 24 confirmed as defects, 25 refuted as defects, several of the refuted ones true as robustness facts. **No registered verdict is changed; one is restated.**

**T4 is on the line, not passed.** It clears its bar by 0.00996 points of mean (0.066 standard errors) and 0.048 of t. A season-block bootstrap gives the full registered rule a 51% chance of passing on a resample; across 29 one-at-a-time readings of the specification (floors, streak thresholds, start date, dropping a year, the dedupe) 13 hold and 16 fail;
removing one week flips it in 44 of 171, one calendar year in 5 of 9. Two data corrections each flip it to "no". (a) The calendar's time field is a bucket, not a clock: 08:30 is before the open, 16:30 after the close, and **12:00 is during the session**; the registered rule (hour 12 or later means the next session, as in Pass 21)
puts those 28 events a session late, and Finviz's own one-day reaction matches the same-day return for 26 of 26 of them: with 12:00 reacting the same day T4 is -0.300%, t -1.98. (b) A streak counted across a missing calendar quarter joins non-adjacent quarters (44 flagged events, 10 tickers): with the streak reset across a gap of over 150 days, T4 is -0.289%, t -1.89.
Both together: **-0.281%, t -1.83, median -0.36%, both halves negative, negative in 7 of 9 years.** The registered verdict stays "holds" because the registered rule was applied as written; read plainly, the contrast is a negative of about 0.3% over five sessions whose size sits on its bar, and its sign is the steady part (104 of 171 weeks negative, sign test p 0.003; P(mean below 0) 0.987 in the bootstrap).
By session: reports before the open alone -0.456% (t -2.76), after the close alone -0.359% (t -1.02). The forward test of Pass 30 keeps its own rule and record; its first look (+2.64% over five weeks) and this one point opposite ways, so "small and not settled" is the reading. Where the results and the scorecard say "holds by a hair", read "meets the letter of its rule by a hair".

**The vendor claim is narrowed.** "No finding belongs to the data vendor" rests on T1 and T2 over S2 only, and T2's S2 pass is itself marginal (t 2.04 and 2.08; the audit found it does not survive more Newey-West lags or dropping Pass 21's own window). On Pass 23's identical 463 names and 35 weeks, the sleeve's clock gives +0.474% a week (t 4.24) with yfinance's surprise and
+0.348% (t 3.44) with Finviz's, and the weekly edges correlate 0.74 (the difference has t 1.15, and goes the other way in other windows); T2 there is +1.169% against +0.97%; T4 over the 77 weeks both sources cover is -0.41% (t -2.21) with Finviz and -0.27% (t -1.31) with yfinance. So the **verdicts of T1 and T2 match across vendors, and sizes move by up to a quarter.**

**The pipeline check, corrected.** On Pass 23's window the old numbers are reproduced with the old definition (T2 +1.169% against the published +1.21%; T3 +0.474% against +0.512%), so there is no pipeline bug; the shrinkage I attributed to "the definition, the larger universe and the week count" is mainly the Finviz definition (about -17% on T2, -27% on T3). The "60 to 65% of the size" applied to T1 is wrong (IC +0.219 against +0.234 is 94%).

**"A recent-regime result" is a reading, not a finding.** The periods I quoted (2016-19, 2020-23, 2024-26) are not the registered half-decades and came from a replay script that is not in the repo; the by-year table in the results file shows T2 positive in 2017, 2021 and 2024-26 and negative or flat in the other years. The decade does not support the drift as a stable edge; whether the recent years are a regime or noise is not established.

**Disclosures the registration lacked.** The event builder dedupes calendar rows within 20 days of the previous quarter (31 rows, 8 events; no verdict moves) and ends a streak at a quarter with no surprise; T3 needs 20 bars before a name enters its pool; S2's yfinance side was built from all 503 names with a live fetch for tickers missing from the cache, not from the 2024-09 list's cached events. The "about 14% of rows without a surprise" came from the all-market probe; for the S&P list it is 0.9% (185 of 20,845 rows).
WBD (44 calendar rows) has no Yahoo bars and PSKY's history sits under PARA; DOC's calendar rows before 2024-03 belong to another company (a reused ticker); share-class twins (GOOG and GOOGL, FOX and FOXA, NWS and NWSA) enter every window twice; the join in the S2 agreement drops 429 events. None changes a verdict. Newey-West with 4 lags and an iid season bootstrap understate the dependence between overlapping windows (no registered verdict flips on more lags).
The Finviz values quoted as examples in the registration were removed from this public text (the repo is public; Finviz data is for the owner's use).

**The connector's new modules (private repo).** The audit found real bugs there and they are fixed (`ae2879b`): the `finviz_breadth` and `finviz_enrich` MCP tools crashed on every call (the CLI the routines use was unaffected); `pe-cache` checked that rows came back, not that their fields were filled, so one lost Finviz column would have been written as a whole missing input and moved Cecil's third pick in a replay (it now refuses on a missing header, a column
below its fill floor, or under 90% coverage, and leaves yfinance to run); its earnings window started on the Monday where the pipeline counts from the Friday, so a name that reported after the close that Friday would have escaped the blackout (the window now starts on the Friday); and a cache that already existed was reported without saying who wrote it (the summary now carries the source and counts, and the Monday task logs from it). The enrich news count is marked as a floor when the 100-row cap binds.

## Pass 32 -- the -5% stop on random fives, twenty years of weeks (registered 2026-11-16 before any run)

**Why.** The owner enforced the -5% CORE stop on 2026-11-02 on the strength of
exit-shadow.md: 37 CORE position-weeks, five fires. A web scan of the published
evidence (2026-11-16) says tight stops on single stocks tend to cost return
unless returns trend within the holding period, and found nothing that tests a
one-week hold in large caps. Pass 13 B tested a different rule (sell on
Tuesday's close) on 96 weeks. This pass asks the mechanical question only:
on names nobody picked, what does the tracker's own stop rule do to a
five-name week? It involves no LLM and no engine, so history is admissible
(rule 1's engine-only exception, with its caveat).

**Data.** Daily auto-adjusted bars (Open, High, Low, Close) for today's S&P 500
list (`universe_sp500_added_2026-09-22.csv`) and SPY, from 2006-06-01. Weeks:
every Monday from 2007-01-01 through 2026-11-09; a week runs from the first
session on or after Monday to the last session on or before Friday. A name is
eligible in week W if its index "Date added" is blank or before W, it has a bar
on every session SPY traded that week, and it has 60 sessions before the entry.
**Caveat, stated before the run:** names that left the index (the failures
above all) are missing, so the left tail is understated and a stop's benefit
with it; read the result as a ceiling on the damage a stop avoids being wrong
about, not a floor.

**The rule, exactly as `portfolio/tracker.py` runs it.** Entry at the first
session's Open. The stop sits x% under the entry. On each held bar in order
(the entry bar included): if Low <= stop, the name is sold -- at the bar's Open
if the Open is at or under the stop (a gap, entry bar excepted by
construction), else at the stop level -- and the weight sits in cash to Friday.
Otherwise the name is held to Friday's Close.

**Arms.** plain (no stop); fixed stops at -3%, **-5% (the enforced rule)**,
-8% (the SPEC shadow level), -10%; two stops scaled to each name's own
volatility, at 1.5 and 2.0 weekly standard deviations (the SD of the 60 daily
close-to-close returns before the entry, times root 5).

**Books.** 200 random equal-weight fives per week from that week's eligible
names (seed 20261116), every arm on the same draws. Also every eligible
name-week on its own, which needs no sampling.

**What is reported, per arm.** Mean weekly book return and its paired
difference from plain (t over weeks, one number per week: the mean of the 200
draws); weekly SD, the mean of the worst 5% of book-weeks, and the worst
book-week, over all book-weeks; per name-week: how often the stop fires, the
share of fires filled at a gap open, and the share of stopped names that close
Friday above their fill. Splits: first and second half of the weeks, weeks SPY
rose and fell, and the 37 weeks of 2008-09-01..2009-03-31 on their own.
Sensitivity: a 0.10% slip on every fill at the stop level.

**The registered test (rule 7: a risk design is judged against cash).** For a
stop arm, let c = its weekly SD over the plain book's. The cash-matched book is
the plain book held at exposure c. Two numbers decide:
- D_ret = mean(stop arm) - c x mean(plain), t over weeks on the weekly series
  (stop - c x plain).
- D_tail = (mean of the stop arm's worst 5% of book-weeks) - c x (mean of the
  plain book's worst 5%). Positive is a shallower tail than cash gives.

**Rule for the -5% stop.** *Earns its place* if D_ret >= 0 with the same sign
in both halves, or if D_tail > 0 by at least a tenth of the cash-matched tail
while D_ret's t is above -2. *Fails* if D_ret < 0 with t <= -2 and the same
sign in both halves, and D_tail is not positive by that tenth. Anything else is
*a cash dial*: it does what holding less would do, no more and no less. The
other arms are reported on the same two numbers and judged by the same rule,
six arms at once, so a lone |t| near 2 among them is read as chance.

**What this cannot say.** It is random names, not the Council's CORE picks; a
stop can suit one picker's names and not another's (Marky's dips, Passes 15
and 16). Whatever comes out, the enforced rule stays the owner's ruling until
he changes it.

    python lab/pass32_stop_random.py
    python lab/pass32_stop_random.py smoke

## Pass 33 -- where the Council's gap to SPY sits: cash, beta, sector, selection, and a dartboard (registered 2026-11-16 before any run)

**Why.** Sixteen closed weeks, book about -9.6% against SPY -2.9%. The book
held cash and defensive names, lagged in rising weeks and led in falling ones.
The same web scan suggests measuring before changing anything: is the gap
exposure, sector calls, or the names? This pass is arithmetic on the booked
record; nothing is tuned and no rule follows from it.

**Scope.** Every closed week in `portfolio/history/` (16 at registration). Per
position, the official booked `pnl_pct`, weight and sponsor; per week, the
official `weighted_return` and `spy_return`. Abort weeks have no file and are
not in scope here.

**A. Regression.** Weekly book return on SPY's same-window return, OLS:
alpha, beta, their standard errors, R squared. Again on the invested part alone
(book return over invested weight).

**B. Attribution, exact by construction.** For each position i with weight
w_i, booked return r_i, sector fund S(i) (the SPDR fund of its GICS sector in
`universe_sp500_full_2026-09-22.csv`; names outside that file are mapped by
hand and listed), and betas b_i and b_S estimated point-in-time from the 52
weekly Friday-to-Friday returns before the entry (fewer than 26 weeks: beta 1,
listed):
- cash      = -(1 - sum w) x r_SPY
- beta      = sum w_i (b_i - 1) r_SPY
- sector    = sum w_i (r_S - b_S r_SPY)
- selection = sum w_i [(r_i - b_i r_SPY) - (r_S - b_S r_SPY)]
- booking   = official weighted_return - sum w_i r_i (rounding, restatements)
The five add to the week's official alpha. Sector-fund returns are the lab's
basis (Monday open to Friday close, adjusted). Reported per week, summed, and
by sponsor (the beta, sector and selection terms carry a sponsor; cash does
not). Per pick: the selection residual by sponsor, mean and t.

**C. Dartboard.** For each week, 2,000 random books with the Council's own
number of names, weights and cash (seed 20261116), scored on the lab's basis:
(1) from the lab's frozen universe (`universe_2026-09-21.txt`), as rule 4
does; (2) sector-matched, each pick replaced by a random S&P 500 name from its
own GICS sector. The official book's percentile in each; the mean percentile
over weeks with z = (mean - 0.5) x root(12 n).

**How it will be read (stated now).** Sixteen weeks decide nothing about
skill; the web scan's own arithmetic puts the gap inside one standard error.
The pass answers a narrower question: of the cumulative gap, what share is the
cash and beta terms (exposure the Council chose), what share sector, what share
names. A selection term per pick with |t| >= 2 for a sponsor would be worth a
forward test; anything less is a description. The dartboard percentile is the
skill benchmark from here on and is meant to be carried forward weekly; that
wiring, and asking each desk to rank its whole list with probabilities, change
the live prompts and wait on the owner.

    python lab/pass33_attribution.py

## Pass 32 results -- the -5% stop costs return like cash and trims the tail better than cash; it passes the registered rule on the tail clause only

1,037 weeks (2007-01-01 .. 2026-11-09), 200 random fives a week, 503 names
with bars (352 eligible in an average week), about 365,000 name-weeks.

| Arm | Mean / wk | vs plain (t) | Weekly SD | Worst 5% of weeks | Worst week | Fires | D_ret (t) | D_tail | Registered verdict |
|---|---|---|---|---|---|---|---|---|---|
| plain | +0.267% | | 2.98% | -6.57% | -29.0% | | | | |
| -3% | +0.172% | -0.095% (-2.40) | 2.21% | -3.23% | -10.7% | 33.3% | -0.026% (-0.94) | +1.63% | earns its place |
| **-5% (enforced)** | **+0.209%** | **-0.058% (-2.10)** | 2.56% | -4.66% | -11.4% | 15.6% | -0.020% (-0.89) | +0.98% | **earns its place** |
| -8% | +0.233% | -0.034% (-2.22) | 2.80% | -5.82% | -11.8% | 5.7% | -0.018% (-1.27) | +0.34% | a cash dial |
| -10% | +0.238% | -0.029% (-2.66) | 2.88% | -6.21% | -13.4% | 3.2% | -0.020% (-1.91) | +0.13% | a cash dial |
| 1.5 SD | +0.244% | -0.023% (-1.73) | 2.87% | -5.94% | -23.7% | 11.1% | -0.013% (-1.03) | +0.39% | a cash dial |
| 2.0 SD | +0.249% | -0.018% (-2.05) | 2.93% | -6.30% | -25.8% | 5.3% | -0.013% (-1.59) | +0.16% | a cash dial |

- **Every stop lowers the raw return.** The -5% rule gives up 0.058% a week
  against holding (t -2.10), about three points a year, on random names. It
  fires on 15.6% of name-weeks, 13% of those at a gap open, and 54% of the
  stopped names close Friday above their fill.
- **Against cash it is a wash on return.** Held at the exposure that gives the
  same weekly SD (0.86), the plain book earns 0.020% a week more than the -5%
  book (t -0.89; first half -0.044%, second half +0.004%, so the sign does not
  even hold). The stop is not worse than holding 14% less.
- **Against cash it is better on the tail.** The worst 5% of weeks average
  -4.66% with the stop and -5.64% for the cash-matched plain book, 17%
  shallower, and the worst single week is -11.4% against -29.0%. That is the
  clause it passes on: tail improvement of more than a tenth with D_ret's t
  above -2.
- **Where it pays and costs.** Weeks SPY rose: -0.249% a week. Weeks SPY fell:
  +0.197%. September 2008 to March 2009: +0.092% a week.
- **Fixed against volatility-scaled.** The two volatility stops cost the least
  return and protect the least: their worst weeks (-23.7%, -25.8%) are close
  to the plain book's. A fixed level is what cuts the deep week. The -3% stop
  trims the tail most and costs the most, firing on a third of name-weeks.
- **With a 0.10% slip on level fills:** -5% is -0.072% a week against plain,
  D_ret -0.034% (t -1.49), same verdict. The -3% stop's D_ret goes to t -2.01.
- **Six arms, one sample.** No arm's D_ret reaches t -2 before slippage; the
  raw differences against plain are all negative with t between -1.7 and -2.7,
  which is one finding (stops cost raw return), not six.

**Reading.** On random large caps the enforced stop is insurance with a fair
premium: it costs about what the equivalent cash would and buys a shallower
bad week than cash does. It does not add return and nothing here says it
should be expected to. Two things this pass cannot settle: the missing
delisted names (which should flatter the plain hold), and Yahoo's daily Lows
over twenty years, where a bad tick fires a stop that never traded (which
counts against the stop). And it is random names: the Council's own record
is still the 37 CORE position-weeks in exit-shadow.md.

**Erratum to the registration:** the 2008-09-01..2009-03-31 window holds 31
Mondays, not 37.

Result file: `lab/results/pass32_stop_random.json`.

## Pass 33 results -- the gap is in the names, not the exposure; against a dartboard the book is ordinary

16 closed weeks (2026-07-20 .. 2026-11-09). Book -9.58% against SPY -2.86%
compounded; the weekly alphas sum to -7.05 points.

**A. Regression.** Book on SPY: beta 0.21 (se 0.32), alpha -0.58% a week
(se 0.46), R squared 0.03. Invested part alone: beta 0.32 (se 0.42), alpha
-0.70% a week (se 0.60). Mean invested weight 71%. The book barely moved with
SPY; with sixteen points the alpha is 1.3 standard errors from zero.

**B. Attribution** (sums over the sixteen weeks, points of alpha):

| Term | Sum | Mean / wk (t) | Weeks SPY rose | Weeks SPY fell |
|---|---|---|---|---|
| cash | +1.10 | +0.07% (0.89) | -1.39 | +2.49 |
| beta | +2.98 | +0.19% (1.03) | -2.24 | +5.22 |
| sector | +1.55 | +0.10% (0.31) | -1.53 | +3.08 |
| **selection** | **-12.67** | **-0.79% (-1.56)** | -6.46 | -6.21 |
| booking | -0.01 | | | |
| **alpha** | **-7.05** | | | |

- **Exposure helped.** Cash and low beta together added about four points,
  because SPY fell over the period: they cost 3.6 points in rising weeks and
  gave back 7.7 in falling ones. Sector calls added about 1.5.
- **The names lost it.** Selection inside the sectors is -12.7 points, and it
  is the same size in rising and falling weeks, so it is not an exposure
  effect in disguise. It is concentrated: four weeks (2026-08-03 -5.87,
  2026-10-12 -4.25, 2026-08-17 -2.52, 2026-07-20 -2.23) carry more than the
  whole sum. Weekly t -1.56: large, not established.
- **Betas in this stretch are unusual** and the split between the beta and
  sector terms leans on them: over the trailing year XLK ran at 1.6 to SPY,
  XLF 0.6, XLI 0.65, staples and utilities near zero or below, energy -0.8.
  The names' weighted trailing beta averaged 0.42. No name lacked the history
  for a beta. SYM and ZS were mapped to a sector by hand.

| Sponsor | Picks | Mean trailing beta | vs SPY per pick (t) | Sector term per pick (t) | Selection per pick (t) | Selection, summed |
|---|---|---|---|---|---|---|
| Cecil | 27 | 0.28 | +0.24% (0.35) | +0.13% (0.41) | -0.28% (-0.33) | -2.65 |
| Marky | 21 | 0.17 | -0.16% (-0.18) | +0.64% (1.55) | -1.16% (-1.34) | -4.97 |
| Ophelia | 18 | 0.89 | -2.33% (-1.63) | -0.50% (-0.90) | -1.81% (-1.80) | -5.05 |

No sponsor's selection reaches |t| 2, so by the registration these are
descriptions. Ophelia is the nearest, and hers is the only sector term that
is negative; Marky's sectors were right and his names inside them were not.

**C. Dartboard.** The official book's mean percentile among 2,000 random
books at its own weights and cash: 44th against the lab's frozen universe
(z -0.84), 46th sector-matched (z -0.49). Mean weekly return: book -0.61%,
frozen dartboard +0.17%, sector-matched +0.15%. The percentiles sit near the
middle while the means sit far apart because a few weeks were at the very
bottom (2nd, 2nd, 3rd percentile) and the rest were unremarkable.

**Reading.** The web scan's guess that the gap was cash and low beta is not
what the record shows: exposure was a net help over a falling stretch, and
the shortfall is stock selection inside the sectors, mostly in four weeks.
Against random books the Council is indistinguishable from a dartboard, which
is also not evidence of a selection problem that will persist. Sixteen weeks
cannot separate a bad picker from four bad weeks.

Not done here, and waiting on the owner because they change live prompts:
carrying the dartboard percentile forward each Monday, and asking each desk to
rank its whole candidate list with probabilities.

Result file: `lab/results/pass33_attribution.json`.

## Pass 34 -- two forward records: the dartboard, and each desk's ranked ten with probabilities (registered 2026-11-16 before the first row of either)

The owner asked for both on 2026-11-16, after Pass 33. Both are records, kept
forward; neither changes the book, the engines or a vote.

**A. The dartboard, weekly.** `lab/forward_dartboard.py`, run by the Monday
forward task. For every closed week in `portfolio/history/` not yet in
`lab/dartboard_ledger.json` it logs the official book's percentile among 2,000
random books at the book's own number of names, weights and cash, on the lab's
basis: against the frozen universe, and sector-matched (each pick replaced by
a random S&P 500 name of its GICS sector). The first sixteen rows are Pass
33's, copied as computed there; later weeks use the seed 20261116 plus the
week's date as a number. The ledger is append-only. A pick with no sector in
the S&P 500 file and no hand mapping leaves that week's sector-matched cell
empty and is named. The page (`lab/DARTBOARD.md`) carries the mean percentile
and z = (mean - 0.5) x root(12 n) for each. **Reading:** z at or above +1.64
over at least 40 weeks would be the first evidence of selection skill this
project has had; z at or below -1.64 would say the selection step does worse
than chance; anything between is a dartboard.

**B. Each desk's ten, ranked, with a probability.** From the Council run of
2026-11-23, before the open, the Monday session writes
`lab/ranks/<MONDAY>.json`: for Cecil, Marky and Ophelia, ten distinct names
from the scan universe in rank order (1 = best), each with `p`, the desk's
probability in whole percent (1-99) that the name beats SPY from Monday's open
to Friday's close. The desk's engine proposals as the report prints them must
be among the ten and are flagged `engine: true`; the rest are the desk's own
next-best names by its own lens. `p` may not rise as rank falls. The file
names the model that wrote it. It must be committed before 09:30 ET that
Monday and never edited after; `lab/forward_ranks.py` reads the file's commit
times and refuses to score a week that fails either test (it is listed as
late). No file is written for an abort week. Nothing reads the file but the
scorer: the ranks do not feed the consensus, the weights or the report.

**Scored each Monday** (`lab/forward_ranks.py`, lab basis), per desk and
pooled: the rank IC (Spearman of rank against the week's return over SPY);
the Brier score of `p` against beat-or-not, with skill = 1 - Brier / 0.25
(0.25 is what always saying 50% scores); calibration by bucket of `p`; mean
excess return of ranks 1-5 against ranks 6-10; engine names against the
desk's own additions.

**The registered reading, at 40 scored weeks and not before.** A desk shows
ranking skill if its mean weekly IC is above zero with t >= 1.64 **and** its
Brier skill is above zero. The selection step adds nothing if mean IC has
t < 1.64, Brier skill is at or under zero, and ranks 6-10 do as well as ranks
1-5 (the paired weekly difference has t < 1.64). Three desks and a pooled row
are four looks, so one lone pass among them is read as chance unless its t
clears 2.24. A change of model starts a new record for B; the page splits by
model.

**What it cannot say.** One session writes all three desks, so the lists are
not independent of each other or of the report it has just written. The ten
are chosen, not sampled: a rank IC inside a hand-picked ten says whether the
desk can order its own shortlist, not whether the shortlist beats the
universe; the dartboard in A is the check on that.

    python lab/forward_dartboard.py
    python lab/forward_ranks.py
    python lab/forward_ranks.py check lab/ranks/2026-11-23.json

## Pass 36 A -- the runoff: do a screaming stock's neighbours drift? (registered 2026-11-16 before any run)

**The owner's idea (2026-11-16).** When a headline is screaming one stock, do
not buy that stock: find the one that handles its runoff, a step away, before
attention gets there. This pass is the half of it that history can answer
without hindsight: prices and the index's own sub-industry table, no LLM. The
other half (an LLM mapping suppliers and customers, forward only) is a draft
with the owner and is not registered here. Pass 35 is a draft too and its
number is held.

**Data.** The 2006-2026 daily auto-adjusted bars Pass 32 cached (today's S&P
500 list and SPY), with Pass 32's survivorship caveat. GICS sector and
sub-industry and the index "Date added" from
`universe_sp500_full_2026-09-22.csv`; a name counts from its date added (blank
= long-standing). The sub-industry table is today's, applied to the past.

**Trigger.** Day D, 2007-01-01 onward: a member whose close-to-close return
minus SPY's is at least +8% or at most -8%, on volume at least twice its mean
of the 20 sessions before. A name that triggered in the previous 20 sessions
does not trigger again. When several names of one sub-industry trigger the
same day in the same direction, the largest move is the trigger and the rest
are its linked names.

**Linked names.** Every other member of the trigger's sub-industry on D.
*Priced*: its own day-D return over SPY, in the trigger's direction, is at
least a third of the trigger's. *Unpriced* (the runoff): the rest. Thresholds
are the registration's guesses, fixed here: one set, no search.

**Measure.** Each linked name from the open of D+1 to the close of D+5, and
to the close of D+20, minus SPY over the same window, clipped at +/-50%.
Against two controls: (i) the mean of the members of the same GICS sector
outside the sub-industry over the same window; (ii) the name's own mean over
every day it was a member (its ordinary 5- and 20-session excess). An event's
value is the mean over its unpriced linked names of (name minus control i).
Events are averaged within their calendar month and the t is over months.

**Decisive tests: four.** Unpriced neighbours after an up-trigger, 5 sessions
and 20; after a down-trigger, 5 and 20; each against control (i). The idea
*passes* a test if the neighbours move in the trigger's direction with |t| of
2.5 or more (four looks) and the same sign in both halves of the months. It
*fails* that test with |t| under 1.64 or the wrong sign. Between is "a lead".

**Reported, never decisive.** The same against control (ii); the priced
neighbours; the trigger itself over the same windows (does the screaming
stock keep going); 2007-2016 against 2017-2026; counts of events and links.

**What it cannot say.** A sub-industry is a crude link, and these are large
caps, where a neighbour is likeliest to be priced the same day. A fail here
says large-cap sub-industry neighbours are not slow. It does not test
suppliers, customers or small names. Windows of events close together in one
sub-industry overlap; the monthly clustering only partly answers that.

**Prediction, stated before the run.** Little or nothing at 5 sessions; if
anything shows, it is at 20 sessions after down-triggers.

    python lab/pass36_runoff.py
    python lab/pass36_runoff.py smoke

## Pass 36 A results -- no runoff to buy among large-cap neighbours; after a crash the neighbours keep slipping, a lead and not a pass

2007-01-03 .. 2026-10-15, 503 names. 1,985 up-triggers and 2,040
down-triggers (378 had no neighbour to score); about 15,000 unpriced links
and 2,300 priced ones. Monthly clusters, 227 to 230 months.

| Trigger | Sessions | Unpriced neighbours vs sector (t) | Halves | vs their own ordinary (t) | Verdict |
|---|---|---|---|---|---|
| up | 5 | +0.05% (+0.66) | +0.09% / +0.01% | +0.00% (+0.06) | fail |
| up | 20 | -0.02% (-0.12) | -0.13% / +0.09% | +0.00% (+0.02) | fail |
| down | 5 | -0.15% (-1.51) | -0.15% / -0.14% | -0.11% (-1.11) | fail |
| down | 20 | **-0.37% (-2.31)** | -0.23% / -0.50% | -0.30% (-1.67) | a lead |

- **The idea as stated fails.** After a stock screams upward, the
  sub-industry neighbours that had not moved do nothing over the next week or
  the next month: +0.05% and -0.02% against the rest of the sector. There is
  no runoff to buy.
- **The other direction is a lead.** After a stock collapses, the neighbours
  that had not moved slip a further 0.37% over 20 sessions against their
  sector (t -2.31, same sign in both halves, -0.48% with t -2.37 in
  2017-2026). It does not reach the registered 2.5, and against the names' own
  ordinary excess it is t -1.67. It is on the selling side: for a long-only
  book it is a reason not to buy the neighbour of a fresh collapse, not a
  trade.
- **The screaming stock itself** does not keep going either way: +0.22% and
  +0.35% after an up day (t 1.36 and 1.17), -0.21% and -0.13% after a down day
  (t -1.10, -0.49). The neighbours that *did* move with it show nothing.
- **The prediction held:** nothing at 5 sessions, the only thing showing at
  20 sessions after down-triggers.

**Reading.** Large-cap sub-industry neighbours are priced by the next open,
as expected. This says nothing about suppliers, customers or small names,
which is where the idea would live if it lives anywhere; that half is forward
only and stays a draft with the owner. If it is built, this pass argues for
two changes to the draft: score down-triggers as "avoid" signals as well as
up-triggers as buys, and expect the up side to need names well under the S&P
500 in size.

Result file: `lab/results/pass36_runoff.json`.

## Pass 36 B -- the runoff, forward: from a story to the names several steps away (registered 2026-11-16 before the first map)

**The owner's idea, in his words (2026-11-16).** "Seven degrees of
separation": not the stock in the headline and not its neighbours, but "the
companies affected by the companies that are affected by the companies that
are affected by the story ... the 'duh' trades after the fact. Like generator
sellers during a massive flood." Pass 36 A tested same-sub-industry
neighbours, which was the lab's reduction and not this idea; it does not bear
on it. This is the idea itself, and it can only be tested forward: asked what
followed from a 2023 story, a model already knows (rule 5).

**Triggers, fixed so nothing is cherry-picked.** Each weekend:
- *Stories:* every row of the "What's Moving Markets -- The Big Stories"
  table in that Saturday's README Market Brief (the Synthesis Agent writes
  three to five). All of them, none skipped, none added.
- *Stock moves:* the two largest triggers of the week by Pass 36 A's rule (an
  S&P 500 name up or down 8% against SPY on twice its 20-day volume), one up
  and one down when both exist, as `lab/forward_runoff.py detect` prints them.

**The map.** For each trigger one file, `lab/runoff/<DAY>_<KEY>.json`,
written by one session: two to eight linked US-listed names. Each link
carries `chain`, the causal steps from the story to the name, one line a
step; `degree`, the number of steps (1 = the obvious name, up to 4);
`type` (supplier, customer, competitor, complement, substitute, demand,
cost); `expected` (+1 the name should beat its benchmark, -1 lag it); and
`exposure_source`, the filing or company page showing the name is in that
business (no source, no link). At least one link in every map is two or more
steps out. The session does not look up the linked names' prices. The file is
committed before the next open and never edited; the scorer reads the commit
times.

**Scored** by `lab/forward_runoff.py`, run with the Monday forward task.
Entry is the first open after the file's commit. Each link: entry open to
the close 5 and 20 sessions on, minus its benchmark (SPY for an S&P 500 name,
IWM otherwise), clipped at +/-50%, times `expected`. A trigger's value is the
mean of its links; the t is over triggers. Recorded mechanically at scoring,
not by the session: whether the name is in the S&P 500, and its run-up over
the benchmark from the story's day to the entry (3% or more its expected way
= already run).

**One decisive test.** Links two or more steps out, 20 sessions. Nothing is
read before 60 such links from at least 20 triggers. *Confirmed* at a mean of
+1.0% or more with t of 2 or more. *Rejected* at zero or below once there are
100 links. Otherwise it keeps running to 200 links and is judged once, final.

**Reported, never decisive.** By degree (1, 2, 3 or 4): the owner's claim is
that the far names are the slow ones, so the page shows whether the signed
return rises or falls with distance. Story triggers against stock triggers;
buys against avoids (Pass 36 A's lead was on the avoid side); inside and
outside the S&P 500; run already or not; 5 sessions.

**What can fool it, stated now.** (1) One session writes the chain and the
sign, and a good story is not a cash flow: far links are where the reasoning
is thinnest. (2) The benchmark is crude for small names; a small-cap rally
lifts every non-member link at once, which is why the t is over triggers and
IWM is the benchmark there. (3) "After the fact" is the point of the idea and
also its weakness: by Monday's open the obvious part may be done, which the
run-up split is there to show. (4) A change of model starts a new record.

**Predictions.** Degree 1 is flat (priced). If anything shows it is at degree
2 in names outside the S&P 500. Degree 3 and 4 will be too few and too noisy
to read for months. "Keep running" is the likeliest state at 60 links.

    python lab/forward_runoff.py detect
    python lab/forward_runoff.py check lab/runoff/<file>.json
    python lab/forward_runoff.py

## Pass 35 -- the slow book: Cecil's engine picks held four weeks, a forward record (registered 2026-11-16 before its first cohort)

The owner asked for this on 2026-11-16 (the number was held while Pass 36 ran
first). A separate paper ledger, not a Council member: nothing here changes
what the Council buys.

**Why.** The weekly book is where the lab keeps finding nothing, and two of
its own results point at a slower clock. Cecil with a point-in-time P/E is
the one steady signal (+0.30% a week over random on the clean S&P 500 list,
Pass 11), and his picks kept it when held longer (+0.2 to +0.3 a week of
holding at one, two, four and eight weeks, Pass 13). The earnings surprise
pays over four weeks and loses on the weekly clock (Passes 21 and 23); that
one is already the Pass 29 sleeve. And three results say what to leave out:
managing the week costs (Pass 13), exits reshape the outcome and not the
return (Pass 16), and a stop costs raw return about as cash would (Pass 32).

**What this is not.** It has no small-cap leg. The lab's one test of a wider,
smaller universe went against it (Pass 14), and the Butterfly Net's reports
are not scored yet.

**The rule (fixed).** Every Monday W the routine runs:
1. Universe: the S&P 500 list of 2026-09-22, frozen (the Pass 29 universe).
2. The picks: the Cecil-solo engine's book on that universe for week W, as
   `lab.run` computes it with Pass 11's point-in-time P/E and the engine's own
   earnings blackout, from data before W. **The engine returns three names**
   (it has since 2026-09-21, so the lab's "five" for Cecil in Passes 11 to 13
   was three); this record takes what the engine returns and does not pad it.
3. Equal weight, bought at W's open, sold at the close of the Friday of W+3.
   No stop, no trim, no exit rule, no cash.
4. Cohorts overlap (up to four live); each is scored on its own.

**Ledger.** `lab/slow_ledger.json`, append-only, one row per Monday, written
before any exit price exists, with the picks and the whole tradeable pool
(Pass 29's pool: enough history, no report inside the coming week). The
routine runs with the Monday forward task, after the open, so every row is
flagged late, as the sleeve's are: valid, since the picks use only data from
before W. A Monday with no row is a gap and is not repaired.

**Scoring.** As Pass 29: each name open of W to close of the Friday of W+3,
clipped at +/-40%; the cohort's edge is the mean of its picks minus the mean
of the tradeable pool on the same basis, per week of holding (the four-week
edge over 4). Reported, never decisive: the excess over SPY, the edge after a
0.10% round trip, and the same picks' edge in their first week alone, so the
page shows whether the slower clock adds anything.

**Reading rules (fixed now).** Nothing before 12 closed cohorts across at
least three calendar quarters; a cohort is the unit; Newey-West t, 3 lags.
- *Confirmed*: mean edge at least +0.15% a week of holding (half the
  history's), t of 2 or more, positive in at least two quarters.
- *Rejected*: mean edge 0 or below at 12 cohorts, or t -1 or lower at 8.
- Otherwise keep running to 24 closed cohorts, judged once, final.
This is the second decisive forward test of a four-week hold (the sleeve is
the first), so a lone pass among the two needs t 2.24.

**Predictions.** (1) A forward edge between -0.30% and +0.40% a week of
holding in the first twelve cohorts: the history is one rising two-year
stretch on a list with survivorship in it, and three names are noisy.
(2) "Keep running" is the likeliest state at 12 cohorts. (3) Consecutive
cohorts hold the same names more often than not (Cecil stacks one cheap
sector, Pass 19), so the cohorts are far from independent; the Newey-West t
is there for that and still flatters it.

**Left for the owner, not registered:** eight weeks in place of four; a
ten-name arm (needs the engine to return more than three); a combined book
with the drift sleeve.

    python lab/forward_slow.py          # log this Monday if it is not logged, score, rewrite SLOW.md
    python lab/forward_slow.py score    # rescore only

## Pass 37 -- the pinned-price screen: pass over a name whose price is not being set by the business (registered 2026-11-20 before any run)

The owner asked for this on 2026-11-20. Unlike Passes 34 to 36 it changes
production, so it arrives as a pull request; nothing is live until he merges.

**The defect.** AES has closed between $14.80 and $15.05 on every session
since at least 2026-09-21, which is how a stock under a pending cash offer
trades (the terms are not sourced here). Cecil's engine ranked it second on
2026-11-16 with a score of 89: near-full value points from a trailing P/E of
6, and near-full safety points because a pinned price has almost no
volatility and no drawdown. He proposed it in four reports (08-31, 09-14,
10-19, 11-16) and the Council booked it twice (10-19 and 11-16, about 13% of
the book each time). It earns nothing either way: hidden cash, inside a book
that reports itself 83% invested. No gate catches it.

**The rule (fixed).** A name is *pinned* when its weekly history holds at
least 8 bars and the annualized volatility of its weekly returns (the number
Cecil's safety leg already uses, `realized_vol`) is under 5%. All three
engines pass over a pinned name at ranking and propose their next-best name,
exactly as the earnings blackout does, and the scan logs it under the gate
`pinned-price`. A name with no history count or no volatility is never
excluded.

**How the number was chosen, plainly.** After seeing the case. On the frozen
S&P 500 list on 2026-11-20, two names stood apart on 60-session daily
volatility: TECH at 1.9% and AES at 2.6% a year; the next quietest was 13%.
5% sits in that gap. That is a threshold fitted to two names, so this pass
does not ask whether it catches them. It asks whether it does harm anywhere
else.

**Measurement A, false positives over history.** The frozen S&P 500 list,
every Monday from 2007-01-08, the rule computed on the 13 weeks before each
Monday as production computes it. Reported: flagged name-weeks, their share
of all name-weeks, the distinct names with their spans, and the median
absolute return of flagged names over the following week beside the same
median for all names. The list is today's members, so targets that were
bought and delisted are absent: this measures wrong flags on live companies,
not how many real deals the rule would have caught.
- *Harmless* if the flagged share is under 0.5% of name-weeks **and** the
  flagged names' median absolute next-week return is under half of all
  names'. Otherwise the rule is catching ordinary quiet stocks and fails.

**Measurement B, the Council weeks.** The production replay (`lab.run`, the
live universe) over every Council week, with the screen on and off (off is
the threshold set to zero). Reported: the weeks whose books differ, the
names passed over, and the change in mean weekly alpha. Never decisive: a
handful of weeks.

**Predictions.** (1) A: a flagged share under 0.05%, most of it a few
names in long runs. (2) B: books differ in two to five weeks, every one a
week AES ranked in Cecil's three, and the mean alpha moves by less than
0.15% a week either way. (3) The screen will not improve returns in any way
the record can show; its case is that the book's stated exposure is true.

**What it changes downstream, if merged.** `production` on the forward page
is today's code replayed, so its past weeks move with this. The slow book
(Pass 35) and Cecil-solo take what the engine returns, so their picks change
from the first Monday after the merge; rows already in the slow ledger are
not touched, and its first cohort keeps AES to 2026-12-11. Reruns of earlier
passes can differ in any week a pinned name ranked in an engine's three.

**Not covered.** A deal announced within the last eight weeks, a stock-for-
stock deal (the target moves with the buyer), and a halted name. This is a
tape test for one failure, not a merger feed.

    python lab/pass37_pinned.py          # both measurements
    python lab/pass37_pinned.py smoke    # plumbing: 2024 on, 60 names, last four Council weeks

## Pass 37 results -- harmless by the registered test; and the replay had AES in the book far more often than the Council did

Run 2026-11-20, `lab/results/pass37_pinned.json`.

**A, false positives: harmless.** 1,036 Mondays, 503 names, 475,103
name-weeks. The rule flags 226 of them, **0.048%** (the line was 0.5%), on
32 names. The flagged names' median absolute move over the next week is
**0.39% against 2.16%** for all names, 18% of it (the line was half).

What the 226 flags are, read from the spans:

| Kind | Names | Name-weeks |
|---|---|---|
| A price that really was pinned | VRT 2018-11 to 2019-12 (57), NXPI 2017-06 to 2018-02 (34), AES 2026-06 on (21), TECH 2026-09 on (7) | 119 |
| A flat or stale series in the data, volatility 0.0% | AMCR (27), SW (13), FERG (7) | 47 |
| An ordinary quiet stock in a very calm market | 25 names, none for more than 14 weeks: KMB, JNJ, UPS, CB, MCD, KO and others, mostly 2012, 2014 and 2017 | 60 |

The last row is the rule's real cost: 60 name-weeks in twenty years, 0.013%
of the total, when a staple or a utility went through a quarter so calm its
weekly volatility dipped under 5%. Those names would have been passed over
for a week or two. The kinds are my reading of the spans; they are not
sourced deal by deal.

**B, the Council weeks: prediction 2 was wrong.** 17 weeks. The production
replay's book differs in **14** of them, not two to five. Today's engine
code, replayed, ranks AES in Cecil's three in 13 of the 17 weeks and books
it; the live Council booked it twice. The live book is the engines plus
the LLM layer on that week's inputs, and the replay is today's code on
the lab's inputs, so the two were never the same book.
The names that take its place: PRU five times, ALL three, and PFE, CI, COST
and UPS once each.

| | Screen off | Screen on | Change |
|---|---|---|---|
| Mean weekly alpha, 17 weeks | -0.21% | -0.25% | -0.04% |

Inside the registered +/-0.15%, and it says nothing either way: in 13
weeks AES left the book: seven came out better, five worse, and in one
(2026-10-26) nothing replaced it and the alpha moved 0.02.

**Scored against the predictions.** (1) Held, barely: 0.048% against a
predicted "under 0.05%". (2) Missed on the count (14 weeks against two to
five); held on the size. (3) Held: nothing here shows better returns.

**What it means.**
1. The screen does what it was built for and costs almost nothing. The
   case for it is unchanged from the registration: the book's stated
   exposure should be true.
2. The `production` row on the forward page has carried a dead position in
   most of its weeks. After the merge that row is replayed without it, so
   its history moves; the same holds for every design built on production.
3. Cecil's engine has wanted AES since June. That is the more useful
   finding: a value screen with a volatility-rewarding safety leg will
   always reach for whatever is not moving, and a pinned price is only the
   extreme case. The 60 quiet-stock flags are the same pull seen from the
   other side. Not tested here.
4. Not covered, as registered: a deal younger than eight weeks, stock
   deals, halts.

## Pass 38 -- the chart stack: market, sector and stock channels, nothing else (registered 2026-11-20 before any run)

The owner's idea, 2026-11-20, in his words: plot a channel up and "it is
really easy to pick what sectors are worth investing in", and when they
break it, avoid them until the pattern shows again; "same with stocks";
read "the general market trend, sector trend and then stock trend" and
ignore the rest as noise, "as long as the company is reasonably stable".
This pass builds exactly that as a mechanical book and asks whether it
beats luck. No LLM, no wiki, no valuation, no earnings data. Lab only:
nothing in production changes.

**The channel (fixed, and not new).** Marky's `channel_facts` in
`scan_pipeline/engines/marky.py`, called as it stands: a least-squares line
through the last 26 weekly log closes, the residuals' standard deviation as
its width. A chart is *in a rising channel* when the line slopes up, the
40-week average is higher than it was ten weeks earlier, and the latest
close is no more than 2.5 widths below the line. It *breaks* when any of
the three fails. The same reading is applied to SPY, to the eleven sector
funds and to every stock. Needs 40 weekly closes.

**The book (fixed).** Decided on each Friday's close, traded at the next
Monday's open, 0.10% a side.
- Ten slots of 10% each, at most three names in one sector; an empty slot
  is cash and cash earns zero.
- *Entry:* a stock in a rising channel, at or below its centre line (the
  pullback), ranked by the production channel score without the wiki
  adjustment (position 50, slope 20, MACD 30).
- *Exit:* the stock's channel breaks. It is held otherwise, for as long as
  that takes. A sold name can come back when it qualifies again.
- *Sector layer:* the stock's sector fund must be in a rising channel to
  enter; when the fund breaks, the sector's names are sold.
- *Market layer:* SPY must be in a rising channel to enter; when it
  breaks, the whole book goes to cash.
- *Reasonably stable:* the frozen S&P 500 list (a name counts from the date
  it joined the index), and not pinned by the Pass 37 screen.

**Arms.** The primary arm is **full** (stock + sector + market, break at
2.5). The rest are there to say which part does the work:

| Arm | What it is |
|---|---|
| SPY | bought and held |
| SPY gated | SPY while its own channel is rising, cash otherwise |
| list | every eligible name, equal weight |
| stock | stock channel only |
| stock+sector | the sector layer added |
| **full** | the market layer added |
| full, 2.0 / full, 3.0 | the break line moved |
| full, beta | the break line at 2.5 times the stock's beta (52 weekly returns against SPY, held between 0.75 and 1.5): the owner's point that a jumpier stock needs more room |
| full, no pullback | enters anywhere inside the channel, ranked by slope over width (the cleanest channel first) |

On the beta arm, said before the run: the width is already each stock's own
noise around its own line, so 2.5 widths is already wider for a jumpier
stock. Beta adds its sensitivity to the market on top.

**Data.** The frozen S&P 500 list of 2026-09-22 and SPY, daily adjusted
bars from 2006-06, weeks from 2007-03 (the first with 40 weekly closes) to
2026-11-13. Sector funds XLB XLE XLF XLI XLK XLP XLU XLV XLY from the
start; Real Estate is read from XLF until XLRE has 40 weeks (it was inside
XLF until 2016) and Communication Services from XLK until XLC does.

**Basis, and where it departs from the lab's.** A held name is marked
Friday close to Friday close, because this book holds over weekends; an
entry earns Monday open to Friday close and an exit earns Friday close to
Monday open. Every held name is counted at 10% each week (the drift
between rebalances is ignored).

**The control that matters.** The list is today's index members, so it is
full of companies that went on to do well: any picker drawn from it looks
good against SPY, and none of these numbers is a return anyone could have
had. So each arm is measured against **random books at the same
exposure**: every week, 200 draws of as many names as the arm held, from
the names eligible that week, 10% each, no costs. The arm's place among
those 200 is the result. SPY and the list are shown for scale.

**Verdict lines (fixed).**
- *Beats luck:* the full arm's mean weekly return is at or above the 95th
  percentile of its random books over the whole period, and at or above
  the 75th in each half (2007-2016, 2017-2026).
- *Better ride:* its Sharpe ratio (weekly, cash at zero) is above SPY's
  and its largest drawdown is smaller.
- *Each layer earns its place:* Sharpe rises from stock to stock+sector to
  full.
Seven strategy arms are run; only the full arm is scored against the
lines, and the others are reported as sensitivity, not as second chances.

**Predictions.** (1) The full arm's largest drawdown is under 60% of
SPY's. (2) It does **not** beat luck: its place among random books lands
between the 40th and 80th percentile, and its compound return is below the
list's. (3) The market layer does most of the work: it raises Sharpe more
than the sector layer, which moves it by less than 0.05. (4) The beta arm
lands within 0.05 Sharpe of the full arm. (5) "SPY gated" has a smaller
drawdown than SPY and a lower compound return.

**Not covered.** Earnings dates (no history of them back to 2007), taxes,
names that left the index, intraday stops, and the eye: a person drawing a
channel picks its start and its touches, and this fits one fixed window.
If the rule fails, that is the first thing to vary, in a new pass.

    python lab/pass38_chart_stack.py          # every arm, 2007 on
    python lab/pass38_chart_stack.py smoke    # plumbing: 2022 on, 80 names, 20 draws

## Pass 38 results -- the stack fails every line: it picks worse than luck, and only the market layer does anything

Run 2026-11-20, `lab/results/pass38_chart_stack.json`. 1,028 weeks,
2007-03-09 to 2026-11-13, 503 names.

| Arm | Compound a year | Sharpe | Largest drawdown | Invested | Place among random books | First half | Second half | Median hold |
|---|---|---|---|---|---|---|---|---|
| SPY | 10.9% | 0.67 | -54.6% | 100% | | | | |
| SPY gated | 5.8% | 0.57 | -22.1% | 68% | | | | |
| list | 13.4% | 0.74 | -52.2% | 100% | | | | |
| stock | 6.2% | 0.44 | -57.8% | 97% | 0th | 0th | 13th | 9 wk |
| stock+sector | 3.9% | 0.33 | -30.6% | 84% | 0th | 8th | 0th | 6 wk |
| **full** | **5.5%** | **0.48** | **-21.4%** | 68% | **9th** | 67th | 2nd | 7 wk |
| full, 2.0 | 4.0% | 0.37 | -25.6% | 68% | 0th | 30th | 0th | 5 wk |
| full, 3.0 | 6.5% | 0.56 | -22.2% | 68% | 30th | 78th | 14th | 7 wk |
| full, beta | 4.6% | 0.40 | -24.3% | 68% | 3rd | 29th | 2nd | 6 wk |
| full, no pullback | 5.9% | 0.48 | -25.3% | 68% | 20th | 30th | 23rd | 7 wk |

**Against the lines.**
- *Beats luck:* **no.** The full arm earned 0.119% a week; random books
  holding the same number of names earned 0.150%. It sits at the 9th
  percentile overall and the 2nd since 2017.
- *Better ride:* **no.** The drawdown is far smaller (-21.4% against
  -54.6%) but the Sharpe ratio is lower than SPY's (0.48 against 0.67).
- *Each layer earns its place:* **no.** Sharpe goes 0.44, 0.33, 0.48: the
  sector layer makes it worse and the market layer rescues it.

**What each layer did.**
1. *Stock channels pick worse than chance.* Fully invested, the stock arm
   compounds 6.2% against the list's 13.4%, and no random book in 200 did
   as badly. Costs are about 0.6% a year of that. The rest is the rule
   itself: it sells a name after it has fallen through its channel, and in
   this list fallen names came back.
2. *The sector layer subtracts.* It sells whole sectors after they have
   fallen and waits about half a year of evidence before going back.
3. *The market layer is the only one that works, and it works as a brake,
   not an engine.* The full arm sat wholly in cash in 331 of 1,028 weeks.
   It lost 0.4% in 2008 against SPY's 39.4%. It also made 5.6% in 2019
   against 32.8% and 3.1% in 2023 against 26.2%: the channel needs months
   of recovery before it calls the trend up again, and the recovery is
   where the year's return is. Holding SPY under the same gate does the
   same thing more cheaply (5.8% a year, -22.1%).
4. *More room is better; beta is not the way to give it.* The break at 3.0
   beats 2.5 beats 2.0 on every measure, and median holds are five to
   seven weeks, so the rule is being shaken out constantly. Scaling the
   line by beta did worse than leaving it alone.

**Scored against the predictions.** (1) Held: the drawdown is 39% of
SPY's. (2) Half held: it does not beat luck and compounds below the list,
but I predicted the 40th to 80th percentile and it landed at the 9th. I
expected noise and got a rule that is reliably wrong. (3) Half held: the
market layer does the work (+0.15 Sharpe), but the sector layer did not
move it by under 0.05, it cost 0.11. (4) Missed: beta is 0.08 below the
full arm. (5) Held.

**The caution that cuts in the rule's favour.** The list is the index's
members today. A stock that broke its channel and never came back is not
in it, so every breakdown in this data was followed by a survivor's
recovery. That biases the test against any rule that sells breakdowns, by
an amount this pass cannot measure. It does not explain the failure since
2017 in names that were already members, and it does not touch the SPY
gated row, which has no stock selection in it.

**What it means.**
1. Do not put this rule in front of the Council. As written it would have
   taken about a third of a point a year less than throwing darts at the
   same exposure, for a smoother ride that SPY-and-cash delivers alone.
2. Marky's `channel` mode in Council v2 is this same reading on a one-week
   hold. This pass does not test that hold, but it is no support for it.
3. The owner's eye and this formula are not the same thing. The formula
   fits one fixed 26-week window and waits for a 40-week average; a person
   drawing a channel chooses where it starts and what counts as a touch,
   and sees it after the fact. Whether a rule that draws channels the way
   he does can be written down, and whether it then works on data it has
   not seen, is a separate pass. The honest way to find out is forward:
   he marks charts on a date, the marks are logged, and they are scored
   later.
4. The one transferable piece is the market brake, and its cost is
   stated above: it halves the drawdown and roughly halves the return.

## Pass 39 -- the straight line: trade inside the channel, buy the bottom, sell the top (registered 2026-11-20 before any run)

The owner's answer to Pass 38, 2026-11-20, in his words: "maybe the width
tightens or expands for the stock depending on the trend of the sector and
then the trend of the general market"; trend strength matters "over 5 hr,
1 day, 1 week, 1 month, 1 year", and "a nice linear bottom left corner to
top right corner is the ideal graph for any time frame"; "nearing the
bottom of the channel presents buying opportunity but risk", "nearing the
top of the channel presents selling opportunities". This pass encodes
those three things. Lab only.

**How it differs from Pass 38.** That book bought a pullback and held until
the channel broke, with the sector and the market as on/off gates. This one
trades *inside* the channel: in at the bottom, out at the top. The sector
and the market no longer switch the book off; they set how much room a
stock gets. And a name must be a straight line on several time frames, not
only rising on one.

**Straightness (fixed).** On daily closes, a least-squares line through the
log closes of the last 21, 63, 126 and 252 sessions (a month, a quarter,
half a year, a year). Each frame gives a slope and an R-squared: 1.0 is a
ruler from bottom left to top right. A name is *lined up* when all four
slopes are positive; its straightness is the mean of the four R-squareds.
The lab holds daily bars only, so the 5-hour and intraday frames he named
are not tested.

**The channel (fixed).** The 126-session line; width is the residuals'
standard deviation; z is how many widths the latest close sits above or
below the line.

**The book (fixed).** Decided on each Friday's close, traded at Monday's
open, 0.10% a side. Ten slots of 10%, at most three names a sector, cash
earns zero. Frozen S&P 500 list, a name counted from the date it joined,
not pinned (Pass 37).
- *Buy:* lined up, and at least one width below its line (z <= -1), but
  not through the break line. Straightest first.
- *Sell at the top:* z >= +1.
- *Sell on a break:* z below the break line, or the 126-session slope no
  longer positive.
- *The break line moves with the backdrop:* 2.0 widths, plus 0.5 when the
  stock's sector fund is trending up, plus 0.5 when SPY is (trending up:
  its 126- and 252-session slopes both positive). So 3.0 widths of room in
  a strong sector in a strong market, 2.0 in neither. This direction is my
  reading of "tightens or expands"; the opposite reading is an arm.

**Arms.** The primary arm is **line+width**. Six are run; only the primary
is scored against the lines.

| Arm | What it is |
|---|---|
| line | break fixed at 2.5, no backdrop |
| **line+width** | the break line moves with sector and market, as above |
| reversed | the opposite reading: 3.0 widths, minus 0.5 for each of sector and market trending up |
| no top | the primary, without the sale at the top (held until a break) |
| any channel | the primary, without the lined-up rule (126-session slope positive is enough) |
| council names | the primary, drawn only from the Council's live universe where it overlaps the list |

**Data, basis, control.** As Pass 38: weeks from the first with 252
sessions of history to 2026-11-13; held names marked Friday close to
Friday close; each arm placed among 200 random books a week holding the
same number of names from the same pool. SPY and the list for scale.

**Verdict lines (fixed, the same as Pass 38).**
- *Beats luck:* mean weekly return at or above the 95th percentile of its
  random books overall, and at or above the 75th in each half (to 2016,
  from 2017).
- *Better ride:* Sharpe above SPY's and a smaller largest drawdown.

**This is the second try at one idea, and it counts as that.** Pass 38
failed. Every revision after a failure is another draw, and enough draws
will pass a 95th-percentile line by chance. So a pass here earns a place
on the forward page, scored on weeks nobody has seen, and nothing more. A
fail is not softened by pointing at whichever arm did best.

**Predictions.** (1) The primary does better against luck than Pass 38's
9th percentile, because selling the top and buying the bottom harvests
the short-term reversal that large caps do show: between the 50th and
90th percentile overall. (2) It still fails the beats-luck line. (3) "No
top" places below the primary. (4) The moving break line lands within
0.05 Sharpe of the fixed one, and "reversed" within 0.05 of both: the
backdrop will not matter much through the width. (5) "Any channel" places
within 15 percentile points of the primary: straightness adds little.
(6) Median hold under six weeks.

    python lab/pass39_straight_line.py          # every arm
    python lab/pass39_straight_line.py smoke    # plumbing: 2022 on, 80 names, 20 draws

## Pass 39 results -- worse than Pass 38: every arm sits in the bottom two percent of random books

Run 2026-11-20, `lab/results/pass39_straight_line.json`. 1,015 weeks,
2007-06-08 to 2026-11-13, 503 names (258 of them in the Council's
universe).

| Arm | Compound a year | Sharpe | Largest drawdown | Invested | Place among random books | First half | Second half | Median hold | Sold at the top | Sold on a break |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 10.5% | 0.64 | -54.6% | 100% | | | | | | |
| list | 13.0% | 0.72 | -52.3% | 100% | | | | | | |
| line | 5.7% | 0.43 | -39.7% | 83% | 1st | 7th | 2nd | 5 wk | 438 | 816 |
| **line+width** | **3.6%** | **0.30** | **-50.9%** | 83% | **0th** | 2nd | 0th | 6 wk | 422 | 640 |
| reversed | 6.0% | 0.45 | -36.1% | 82% | 2nd | 2nd | 22nd | 4 wk | 458 | 1,166 |
| no top | 5.3% | 0.40 | -37.3% | 89% | 0th | 8th | 2nd | 11 wk | 0 | 523 |
| any channel | 8.3% | 0.51 | -58.6% | 98% | 2nd | 12th | 6th | 6 wk | 448 | 840 |
| council names | 5.7% | 0.45 | -33.4% | 77% | 2nd | 0th | 12th | 7 wk | 411 | 565 |

**Against the lines.** *Beats luck:* **no**, and not close: no random book
in 200 did as badly as the primary. *Better ride:* **no**: Sharpe 0.30
against 0.64, and a drawdown (-50.9%) nearly as deep as SPY's.

**What happened.**
1. *The book sells its winners and keeps its losers.* A name bought at the
   bottom of its channel is sold a width above the line, which caps the
   gain at about two widths. A name that keeps falling is held until the
   break line, two to three widths down, and the primary gives the most
   room exactly when the backdrop looked strongest. Of 1,062 closed
   positions, 422 left at the top and 640 on a break.
2. *More room made it worse here, the opposite of Pass 38.* The moving
   break line (0.30 Sharpe) lost to the fixed 2.5 (0.43) and to the
   reversed reading (0.45). With the top sale capping gains, room only
   lets losses run.
3. *Straightness did not select.* Dropping the lined-up rule ("any
   channel") gave the best compound return of the six, at nearly full
   exposure and the deepest drawdown.
4. *No brake.* With the market only adjusting the width, the book lost
   29.6% in 2008 and 24.6% in 2020, a year SPY made 18.0%.

**Scored against the predictions.** (1) Missed badly: I predicted the
50th to 90th percentile and got the 0th. I thought buying the bottom and
selling the top would harvest short-term reversal; the break exits gave
back more than that. (2) Held. (3) Not shown: "no top" and the primary are
both at the bottom, and "no top" has the better Sharpe. (4) Missed: the
moving line is 0.13 Sharpe below the fixed one. (5) Held: "any channel" is
within two points of the primary. (6) Missed by a hair: median hold is
six weeks, not under six.

**Two passes, thirteen arms, one pattern.** Every channel rule tried here
places in the bottom tenth of random books in this data, most at the very
bottom. Being that reliably wrong is information, and it has two readings
that this data cannot separate:
- The survivor list. Every name that broke down in this data later
  recovered, because the ones that did not are gone from the index. A
  rule that sells breakdowns is penalised by construction.
- Large caps mean-revert at these horizons. A stock that has fallen
  through its channel is, on average, nearer a bounce than a collapse,
  and a stock that looks like a ruler has already been bid.
Either way the tempting conclusion, "do the opposite", is not supported:
buying breakdowns in a list of survivors is the same bias with the sign
flipped.

**What it means.**
1. Neither pass supports a channel book, and Pass 39's revisions did not
   rescue Pass 38. As registered, nothing here goes to the forward page.
2. Further revisions on this data are not worth running. The list cannot
   tell a bad rule from a biased test, and each new variant is another
   draw. The two things that could settle it are a point-in-time index
   membership file (names that left, with their prices) and a forward
   record.
3. A forward record costs nothing: the owner marks charts on a date, the
   marks are logged before the week trades, and they are scored against
   random books from the same universe. That tests his eye, which no
   formula here has matched, and it cannot be flattered by hindsight.

## Pass 40 -- hold until it breaks: a wider channel, drawn once (registered 2026-11-20 before any run)

The owner on the Pass 39 results, 2026-11-20: "the width of the channel
probably needs to be larger than you are thinking. This is more a hold
until it breaks strategy." Pass 38 already leaned that way (the break at
3.0 beat 2.5 beat 2.0). Lab only.

**Two changes from Pass 38, nothing else.**
1. *Wider.* Break lines at 3, 4, 5 and 6 widths.
2. *Drawn once.* Passes 38 and 39 refit the channel every week, so the
   line follows the stock down and a slow fade never "breaks" it, while
   the slope and 40-week tests sell on their own schedule. A person draws
   the channel once and watches for the break. The **anchored** arms do
   that: the 26-week line and its width are fixed on the day of entry and
   extended forward at the same slope; the name is sold on the first
   Friday close below that line by more than the break width, and for no
   other reason.

Entry is Pass 38's, unchanged: a rising channel by `channel_facts`, at or
below the centre line, ranked by the channel score; ten slots of 10%,
three a sector, the frozen S&P 500 list, not pinned, Friday decision,
Monday open, 0.10% a side. No sector layer (it subtracted in Pass 38).

| Arm | Exit |
|---|---|
| refit 3 / refit 4 / refit 5 | Pass 38's rule (line refit weekly; also sold when the slope or the 40-week average turns) with a wider break |
| anchored 2.5 | the entry-day line, 2.5 widths |
| **anchored 4** | the entry-day line, 4 widths -- the primary |
| anchored 6 | the entry-day line, 6 widths |
| anchored 4, market brake | the primary, and the whole book to cash while SPY's channel is broken (Pass 38's market layer) |

**Control and verdict lines.** As Passes 38 and 39: place among 200 random
books a week at the same exposure; beats luck at the 95th percentile
overall and the 75th in each half; better ride on Sharpe and drawdown
against SPY. Only **anchored 4** is scored.

**Read this before the result.** This is the third draw at one idea. And
a wider break has a floor it cannot fall through: as the width grows the
book stops selling and becomes "buy ten survivors and hold them", which
sits near the middle of random books by construction. So rising from the
bottom toward the 50th percentile as the width grows is the rule doing
*less*, not the rule working. Only a place well above the middle says the
channel picks anything.

**Predictions.** (1) The place among random books rises with the width in
both families. (2) Anchored 4 lands between the 20th and 60th percentile
and fails the beats-luck line. (3) Its median hold is over 20 weeks. (4)
The market brake cuts the largest drawdown by more than a third and
lowers the compound return.

    python lab/pass40_hold_break.py          # every arm
    python lab/pass40_hold_break.py smoke    # plumbing: 2022 on, 80 names, 20 draws

## Pass 40 results -- wider did not fix it: the primary sits below every random book again

Run 2026-11-20, `lab/results/pass40_hold_break.json`. 1,028 weeks,
2007-03-09 to 2026-11-13, 503 names.

| Arm | Compound a year | Sharpe | Largest drawdown | Invested | Place among random books | First half | Second half | Median hold | Longest hold |
|---|---|---|---|---|---|---|---|---|---|
| SPY | 10.9% | 0.67 | -54.6% | 100% | | | | | |
| list | 13.4% | 0.74 | -52.2% | 100% | | | | | |
| refit 3 | 7.0% | 0.48 | -53.4% | 97% | 0th | 0th | 11th | 9 wk | 159 wk |
| refit 4 | 8.4% | 0.54 | -46.7% | 97% | 2nd | 0th | 28th | 10 wk | 156 wk |
| refit 5 | 8.4% | 0.54 | -46.7% | 97% | 2nd | 0th | 28th | 10 wk | 156 wk |
| anchored 2.5 | 6.3% | 0.45 | -59.7% | 98% | 0th | 0th | 6th | 4 wk | 402 wk |
| **anchored 4** | **6.9%** | **0.49** | **-62.0%** | 98% | **0th** | 0th | 26th | 12 wk | 417 wk |
| anchored 6 | 5.8% | 0.41 | -56.0% | 98% | 0th | 0th | 2nd | 23 wk | 507 wk |
| anchored 4, market brake | 5.3% | 0.48 | -22.2% | 68% | 10th | 19th | 16th | 9 wk | 67 wk |

**Against the lines.** *Beats luck:* **no.** Anchored 4 earned 0.154% a
week; random books of ten earned 0.257%. *Better ride:* **no**: Sharpe
0.49 against 0.67 and a deeper drawdown than SPY (-62.0%).

**What happened.**
1. *Wider helped the refit rule a little and the anchored rule not at
   all.* Refit goes 7.0% to 8.4% from 3 to 4 widths and then stops: 4 and
   5 are the same book to the trade, because past 4 widths the break line
   is never reached and the slope and 40-week tests do all the selling.
2. *A channel drawn once breaks fast or never.* A steep entry-day line is
   broken within weeks because no stock keeps that slope: half of anchored
   4's closed positions lasted twelve weeks or less. A shallow, wide one is
   never broken: the open book holds SJM, CLX and DGX from 2008 and 2009,
   over 900 weeks each. So the ten slots silt up with whichever quiet
   names happened to be bought early, and the rule stops choosing.
3. *Nothing protected it in 2008.* Fully invested with four widths of
   room, anchored 4 lost 52.9% that year against SPY's 39.4%.
4. *The market brake did what it did in Pass 38*: drawdown -22.2%, at the
   cost of return, and still the 10th percentile of its random books.

**Scored against the predictions.** (1) Half: the place rises with width
for refit (0th, 2nd, 2nd) and not for anchored (0th throughout). (2)
Missed: I predicted the 20th to 60th percentile; it is the 0th. I expected
a wide rule to drift up toward "hold ten survivors"; the ten it got stuck
with were worse than a random ten. (3) Missed: the median hold is 12
weeks, not over 20 (the mean is 20). (4) Held: the brake cut the
drawdown from -62.0% to -22.2% and the return from 6.9% to 5.3%.

**Three passes, twenty arms.** None reaches the 31st percentile of random
books over the whole period; eighteen sit at or below the 10th. Tight or
wide, refit or drawn once, sold at the top or held to the break, with or
without sector and market layers. The two readings from Pass 39 stand
(the survivor list; large caps snapping back), and this data cannot
separate them.

**What it means.** The line for this family on this data is drawn here:
no more variants. What is left is what the Pass 39 results named: a
point-in-time membership file, or a forward record of the owner's own
marks.

## Pass 41 -- the owner's channel: drawn from the swing low along the lows, held until a weekly close breaks it (registered 2026-11-20 before any run)

Passes 38 to 40 closed "this family" and this reopens it, for one reason:
the owner showed his charts, and they are not what those passes drew. He
sent UVE and GRDN on weekly bars as the ideal ("weekly charts are the most
reliable"), and CAT with his own channel drawn on it as a break: anchored
at the April 2025 low, the lower line run along the lows since, the upper
line parallel through the highs, about a year and a half long, broken when
the weekly bars went through the lower line. Against that:
- I fitted 26 weeks. He reads one to two years. On GRDN the last 26 weeks
  have a straightness of 0.11 and the two-year view 0.87.
- I drew a best-fit line with a band of 2.5 times the wobble. He draws
  support through the lows; on UVE that channel is about twice as wide.
- I ranked by the deepest pullback. He picks the straightest long line.
So this pass draws his channel. It is still the fourth draw at the idea
and is counted as that.

**The channel (fixed).** On weekly bars, at each Friday close:
- *Anchor:* the lowest weekly low of the last 104 weeks. It must be 26 to
  100 weeks back, so there is a channel to speak of and it is not the
  stock's whole history.
- *Lower line:* from the anchor's low, the steepest straight line (on a
  log scale) that stays at or under every weekly low since. This is the
  support line a person draws under the lows.
- *Upper line:* parallel, through the weekly high furthest above it.
- *A channel worth owning:* the lower line rises at 10% a year or more,
  and the weekly closes since the anchor have a straightness (R-squared
  against their own best-fit line) of 0.80 or more. UVE and GRDN both
  clear that today.

**The book (fixed).** Decided at Friday's close, traded at Monday's open,
0.10% a side; ten slots of 10%, three a sector; the frozen S&P 500 list
from the date a name joined; not pinned (Pass 37); cash earns zero.
- *Buy:* a name with a channel worth owning, straightest first.
- *The channel is drawn once.* Its lower line on the day of entry is
  extended forward at the same slope.
- *Sell:* the first weekly close below that line. Nothing else sells.

| Arm | What it is |
|---|---|
| **owner's channel** | as above -- the primary |
| lower half | buys only in the lower half of the channel |
| 3% buffer | sells on a weekly close more than 3% below the line |
| straighter | straightness of 0.90 or more |
| market brake | the primary, and the book in cash while SPY's own channel (Pass 38's reading) is broken |

**What it is not.** His examples UVE and GRDN are small caps and this runs
on the S&P 500, because that is the list the lab holds twenty years of
prices for. The small and mid cap list has prices from August 2023 only,
which leaves no room for a two-year channel. A small cap run needs a
download first and is a separate pass. CAT is in this list.

**Control and verdict lines.** As Passes 38 to 40: place among 200 random
books a week at the same exposure; beats luck at the 95th percentile
overall and the 75th in each half; better ride on Sharpe and drawdown
against SPY. Only the primary is scored.

**Predictions.** (1) This does better against luck than anything in
Passes 38 to 40, because a long straight rise is momentum with a
smoothness filter, and that has support in the published record: the
primary lands between the 30th and 75th percentile. (2) It fails the
beats-luck line. (3) The lower line is broken sooner than a chart reader
would expect, because a trend that slows without falling still crosses a
rising line: median hold under 30 weeks. (4) The 3% buffer and the
primary land within 0.05 Sharpe of each other. (5) The market brake cuts
the largest drawdown by more than a third.

    python lab/pass41_owner_channel.py          # every arm
    python lab/pass41_owner_channel.py smoke    # plumbing: 2022 on, 80 names, 20 draws

## Pass 41 results -- the first channel book that is not broken: SPY's return with a shallower fall, and still behind random books

Run 2026-11-20, `lab/results/pass41_owner_channel.json`. 1,041 weeks,
2006-12-08 to 2026-11-13, 503 names. A name had a channel worth drawing in
47% of name-weeks; a typical week offered 62 candidates.

| Arm | Compound a year | Sharpe | Largest drawdown | Invested | Place among random books | First half | Second half | Median hold | Closed at a gain | Mean closed gain |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 10.8% | 0.66 | -54.6% | 100% | | | | | | |
| list | 13.3% | 0.74 | -52.2% | 100% | | | | | | |
| **owner's channel** | **10.5%** | **0.69** | **-37.7%** | 97% | **11th** | 10th | 26th | 10 wk | 42% | +9.9% |
| lower half | 9.3% | 0.59 | -39.5% | 97% | 3rd | 0th | 45th | 4 wk | 41% | +3.1% |
| 3% buffer | 11.0% | 0.70 | -40.8% | 98% | 20th | 21st | 31st | 18 wk | 43% | +15.9% |
| straighter | 10.9% | 0.74 | -32.7% | 96% | 9th | 4th | 32nd | 16 wk | 49% | +11.1% |
| market brake | 6.8% | 0.57 | -25.6% | 67% | 36th | 15th | 66th | 8 wk | 53% | +3.0% |

**Against the lines.**
- *Better ride:* **yes, narrowly.** Sharpe 0.69 against SPY's 0.66, and
  the largest drawdown -37.7% against -54.6%. The first line any channel
  book here has passed.
- *Beats luck:* **no.** 0.219% a week against 0.261% for random books of
  ten from the same list: the 11th percentile, 10th and 26th by half.

**How to hold both.** Against SPY, which is what a person can actually
buy, this book earned the same return (10.5% against 10.8%; the weekly
difference has a t of -0.2, nothing) with about two thirds of the worst
fall. Against ten random names from the list it loses, because the list
is today's survivors and any ten of them compounded 13% and more. The
truth about the rule sits between those two and this data cannot place
it: the first is too kind (the book picks from survivors too), the second
too harsh (it penalises every sale, since everything sold later
recovered).

**What changed from Passes 38 to 40.** The owner's drawing, not a tweak:
a channel one to two years long, from the swing low, with support under
the lows. Compound return went from 5.5%, 3.6% and 6.9% to 10.5% at the
same full exposure. The shape of the trades is what a trend rule should
look like: 42% of closed positions made money, the median one lost 1.8%,
and the mean one made 9.9%. Many small losses, a few long winners (COR
held 854 weeks, V 735).

**What the arms say.**
1. *Buying the lower half of the channel is worse*, as in Pass 38. A name
   near its support line is one bad week from a sale: median hold four
   weeks, 62 trades a year.
2. *A little room helps.* The 3% buffer nearly doubles the median hold
   and adds half a point a year.
3. *Straighter is a better ride, not a better return*: Sharpe 0.74 and
   the shallowest unbraked drawdown (-32.7%).
4. *The market brake costs more than it saves here*: 6.8% a year for a
   -25.6% drawdown. The channel's own exits already got the book through
   2008 at -35.8% against -39.4%, and the brake then sat out recoveries.

**Scored against the predictions.** (1) Missed: I predicted the 30th to
75th percentile and it is the 11th, and Pass 38's 3.0 arm placed higher
(30th) on a far lower return. (2) Held. (3) Held: median hold ten weeks.
(4) Held: the buffer is 0.01 Sharpe from the primary. (5) Missed by a
hair: the brake cut the drawdown by 32%, not more than a third.

**What it means.**
1. Three wrong drawings and one right one. The owner's picture was worth
   encoding properly, and the earlier passes say nothing about it.
2. It is not a way to beat the S&P 500 on this evidence. It is, at best,
   the index's return with a shallower fall, measured on a list that
   flatters it. It does not go to the forward page: it failed the line
   that page requires.
3. His examples were small caps and this is not a test of them. That run
   needs twenty years of prices for the small and mid cap list, and a
   membership history, or the survivor problem is far worse than here.
4. The cheap honest next step is unchanged: a forward record. The rule
   is now mechanical and matches his drawing on CAT (straightness 0.98
   through the spring of 2026, at the lower line by late August), so the
   weekly list can be logged before each Monday and scored, on any
   universe, with no survivor problem at all.

## Pass 42 -- who breaks first: the stock, its sector or the market (registered 2026-11-20 before any run)

The owner's questions on the Pass 41 results, 2026-11-20: "Does the
individual stock's sector generally break trend first? Assume the strong
often hang on the longest. If the tides are fighting you with the general
market and sector near the bottom of the channel you might get swept
away." Three measurements, no book and no verdict on a strategy. Lab only.

**Channels and breaks (fixed).** Pass 41's drawing on weekly bars, for
every stock on the frozen S&P 500 list, the eleven sector funds and SPY.
A *channel episode* opens the first week a series has a channel worth
owning (lower line rising 10% a year or more, straightness 0.80 or more)
and none is open; its lower line is fixed that week and extended. The
episode *breaks* on the first weekly close below the line. A new one can
open afterwards.

**A. Does the sector break first?** For every stock break: did its sector
fund break in the 13 weeks before, in the same week, or in the 13 weeks
after? The same for SPY. Each share is set beside its base rate: the same
share over all weeks the stock was inside a channel and did not break.
Also the median gap, in weeks, between a stock's break and the nearest
fund break within 26 weeks either side.

**B. Do the strong hang on longest?** At every sector fund break, the
stocks of that sector that are inside a channel, sorted into thirds by
their 52-week return over the fund's. Per third: the share still unbroken
13 weeks later, and the 13-week return.

**C. Are you swept away when the tide is against you?** Every name-week
with a channel worth owning, sorted by where the sector fund and SPY sit
that week: no rising channel, the bottom third of their channel, the
middle, the top. *Against* means both sector and market are in "none" or
"bottom"; *with* means both are in "middle" or "top". Per group: the share
of stock lines (fixed that week) broken within 13 weeks, and the 13-week
return over the list's average for the same weeks. Differences are tested
on weekly means with errors that allow for the overlapping windows.

**Caution carried from the earlier passes.** The list is survivors, so the
13-week returns after a break or a bad backdrop are flattered: everything
here came back. The timing in A is much less exposed to that than the
returns in B and C.

**Predictions.** (A) A sector break in the 13 weeks before is more common
at a stock's break than its base rate, but still the minority: under 40%
of stock breaks. Most stock breaks happen with the sector's channel
intact or absent. The median gap is within two weeks of zero: they break
together more than one leads. (B) The strongest third survives the next
13 weeks more often than the weakest, by at least five points. (C) Lines
drawn against the tide break more often within 13 weeks than lines drawn
with it, by at least five points; the 13-week return over the list is
not lower against the tide, because in this list falls are followed by
bounces.

    python lab/pass42_who_breaks_first.py          # the three measurements
    python lab/pass42_who_breaks_first.py smoke    # plumbing: 80 names

## Pass 42 results -- they break together, not in order; the strong break sooner, not later; and a low tide does shake you out

Run 2026-11-20, `lab/results/pass42_who_breaks_first.json`. 1,068 weeks to
2026-11-13, 503 names: 7,355 stock breaks (5,474 while an index member,
with 13 weeks either side), 238 sector fund breaks, 29 SPY breaks.

**A. Does the sector break first? No. They break together.**

| At a stock's break, the other broke... | Sector fund | Base rate | SPY | Base rate |
|---|---|---|---|---|
| in the 13 weeks before | 33.8% | 18.8% | 41.5% | 23.4% |
| the same week | 16.7% | 2.7% | 20.1% | 3.6% |
| in the 13 weeks after | 35.4% | 20.2% | 44.7% | 24.8% |
| not within 13 weeks either side | 52.6% | | 42.6% | |

Breaks cluster: a sector break is nearly twice as likely as usual near a
stock's break, and six times as likely the same week. But it is as likely
after as before. Among the 3,093 stock breaks with a sector break within
26 weeks, the stock went first in 39.0%, the same week in 29.5%, and the
sector first in 31.5%; the median gap is zero weeks. SPY reads the same
(38.5%, 28.7%, 32.8%). If anything the stock leads, which is what an
index made of stocks has to show: the fund breaks when enough of its
members have. And about half of all stock breaks happen with no sector
break anywhere near: the stock's own business.

**B. Do the strong hang on longest? No, the reverse.** At 223 sector
breaks, the stocks of that sector still inside a channel, by their
52-week return over the fund's:

| Third | Names | Still unbroken 13 weeks later | 13-week return |
|---|---|---|---|
| weakest | 1,605 | 72.0% | +4.3% |
| middle | 1,792 | 59.7% | +3.3% |
| strongest | 1,605 | 61.0% | +3.9% |

The strongest third broke more often than the weakest, by 10.4 points
(t -3.9). Their returns over the 13 weeks did not differ (t 0.9). The
reading: the strongest names have the steepest lines, and a steep line is
the easiest to cross. They do not fall more; they stop climbing at that
rate, which under a fixed line is a break.

**C. Does a low tide sweep you out? Yes on breaks, no on returns.** The
share of stock lines broken within 13 weeks, by where the backdrop sat
the week the line was drawn:

| Backdrop that week | Sector fund | SPY |
|---|---|---|
| top third of its channel | 30.0% | 24.0% |
| middle | 32.7% | 37.2% |
| bottom third | 44.6% | 48.6% |
| no rising channel | 31.4% | 32.0% |

With SPY in the bottom third of its channel a stock's line is twice as
likely to be broken within a quarter as with SPY in the top third. For
the sector, measured inside the same weeks, bottom third against top
third is +9.0 points (t 3.8). The registered "against" group (both low
or none, 36.8%) against "with" (both middle or top, 31.3%) is +5.5 points
and not significant (t 1.4), because "no rising channel" behaves like an
ordinary week and dilutes it: the danger is a channel that exists and is
being tested, not the absence of one.

Returns do not follow. Names bought with the sector in its bottom third
made 1.68% over the list in 13 weeks, the best of the four; against-minus-
with is +0.20% (t 0.3). In this list, being shaken out near a low was
usually being shaken out before a bounce. The survivor caution applies
in full to that sentence.

**Scored against the predictions.** (A) Held: before is above its base
rate, under 40%, and the median gap is zero. (B) Missed, and in the wrong
direction: I predicted the strongest third would survive more by five
points; it survived less by ten. (C) Held on the letter (5.5 points, the
line was five; returns not lower) but the registered grouping is weak
evidence. The clean result is the bottom-third rows, which I did not
single out beforehand.

**What it means for the rule.**
1. The sector is not an early warning. Waiting for it to break tells you
   nothing your own stock's line has not told you by the same week.
2. Where the market and sector sit in their own channels is real
   information about how soon a stock's line will be tested. It argues
   for *when to draw a new line* (not while the tide is at its lower
   line), not for when to sell.
3. A fixed straight line under a steep climber is a hair trigger. That
   is the same finding as Pass 41's 3% buffer and Pass 40's quick breaks,
   from a third direction.
4. Items 2 and 3 are suggestions read off this table after the fact. As
   rules they are untested, and adding them to Pass 41's book would be a
   fifth draw.

## Pass 43 -- the owner's channel by size: mega, large, mid, small (registered 2026-11-20 before any run)

The owner, 2026-11-20: "can you check if any particular caps are most
reliable for the strategy? Mega, mid, small, etc." His own examples (UVE,
GRDN) are small caps and Passes 38 to 42 ran on the S&P 500 only. This
pass runs Pass 41's channel and book inside each size tier. Lab only.

**Universe.** Today's full US listing from the Nasdaq screener at $300M
and up and $3 and up, frozen to `lab/universe_all_<date>.csv` with each
name's market cap and sector. Weekly bars from Yahoo, 2006-06 on,
adjusted, cached locally.

**Size, point in time.** A name's size in a past week is today's market
cap scaled by its adjusted price then over now. That ignores share
issuance and buybacks and is otherwise known at the time. Each week the
names with a price are ranked by it and cut into tiers by rank, the way
the indexes are: **mega** the top 100, **large** the next 400, **mid** the
next 600, **small** the next 1,000, **smaller** everything below. Rank
tiers, not dollar lines, so 2008 and 2026 are comparable.

**Tradeable.** A name counts in a week when its adjusted close is $3 or
more and its median weekly dollar volume over the past year is $5M or
more. Costs a side: 0.10% mega and large, 0.20% mid, 0.30% small, 0.50%
smaller. These are guesses and are low for the bottom tiers.

**Per tier, four numbers.**
1. *How often the picture appears:* the share of name-weeks with a
   channel worth owning (Pass 41's definition, unchanged).
2. *How long it lasts:* the share of lines broken within 13 weeks of the
   week they were drawn.
3. *Whether it pays:* the 13-week return of channel names over their own
   tier's average for the same weeks, with errors that allow for the
   overlap.
4. *The book:* Pass 41's primary (ten slots, straightest first, the line
   fixed at entry, sold on the first weekly close below it), choosing
   only from that tier at entry and keeping a name that later changes
   tier. Scored against 200 random books a week of the same size drawn
   from the same tier, and shown beside the tier's equal-weight average.
   No sector cap (the listing's sectors are coarse) and no index
   membership rule (there is none for this list).
Each is reported for the whole period and for 2017 on.

**"Most reliable" means, fixed now:** the tier where the book places
highest among its own tier's random books in both halves. A tier is only
called reliable if that place is at or above the 75th percentile in both.
Five tiers are five chances, so one tier clearing the line is weak
evidence and is said so.

**The survivor problem is worse here than in any earlier pass, and it is
not the same in every tier.** Every name is alive and at least $300M
today. The small tiers of 2010 are therefore made of two kinds of name:
ones that stayed small, and ones that grew into today's large caps. The
small companies that failed are absent. That inflates every small-tier
return and it inflates the random books equally, so the place among
random books is the only number that means much, and it still carries
the bias from Pass 41 (everything sold later recovered). 2017 on is
less exposed than the full period.

**Predictions.** (1) The picture is most common in the mega and large
tiers and lasts longest there. (2) The 13-week return over the tier's
average is positive in the three lower tiers and near zero in mega and
large: momentum is stronger in smaller stocks in the published record.
(3) The book places higher among its random books in mid, small and
smaller than in mega and large. (4) No tier clears the 75th percentile in
both halves.

**Amended 2026-11-20, before any run.** The Nasdaq listing refused the
request (HTTP 403), so the universe is the lab's two frozen lists instead:
the small and mid cap list ($300M to $10B, caps of 2026-09-23) and the
S&P 500 list (caps read from Yahoo on the day). Names above $10B that are
not in the S&P 500 are therefore absent, which thins the mega and large
tiers a little. A name's size is scaled from the week its cap is dated.
Nothing else changes.

    python lab/pass43_channel_by_size.py fetch    # the universe file and the weekly bars -> lab/cache (prices are not committed)
    python lab/pass43_channel_by_size.py          # the four numbers per tier
    python lab/pass43_channel_by_size.py smoke    # plumbing: 400 names

## Pass 43 results -- no size tier is reliable by the registered test; large caps come closest and small caps come last

Run 2026-11-20, `lab/results/pass43_channel_by_size.json`. 3,004 names
with weekly bars, 1,068 weeks to 2026-11-13. The "smaller" tier holds
almost no tradeable names in this universe (a median of none a week, a
book averaging three positions) and is left out of the reading below.

**The picture, by tier, whole period.**

| Tier (rank by size that week) | Tradeable names a week | Has a channel worth owning | Line broken within 13 weeks | 13-week return over the tier's average | t |
|---|---|---|---|---|---|
| mega (top 100) | 94 | 21.3% | 32.9% | +1.41% | 2.9 |
| large (next 400) | 385 | 19.2% | 36.0% | +0.80% | 2.4 |
| mid (next 600) | 552 | 15.5% | 36.2% | +0.62% | 1.9 |
| small (next 1,000) | 454 | 12.2% | 36.0% | +1.38% | 2.7 |

**The book, by tier.** Place among 200 random books a week from the same
tier:

| Tier | Book, compound a year | Tier average | Place, whole period | To 2016 | 2017 on | Median hold |
|---|---|---|---|---|---|---|
| mega | 7.9% | 8.6% | 45th | 61st | 38th | 8 wk |
| **large** | **11.2%** | 9.5% | **86th** | 30th | **98th** | 11 wk |
| mid | 7.3% | 8.6% | 43rd | 14th | 78th | 11 wk |
| small | 10.3% | 17.7% | 10th | 12th | 24th | 13 wk |

**Against the registered meaning of "most reliable".** No tier is at or
above the 75th percentile in both halves, so **none is called reliable**.
Large caps come closest: the only tier whose book beat its own average
over the whole period, 86th percentile overall and 98th since 2017, but
30th before 2017. Mid caps show the same shape more weakly (14th, then
78th). Small caps are last in every column.

**What the tiers say.**
1. *The picture is more common the bigger the company*: one name-week in
   five among mega caps, one in eight among small caps. Once drawn, the
   line is broken at the same rate everywhere, about 36% within a
   quarter. Size does not make a channel last longer.
2. *Being in a channel has paid a little in every tier, and only
   recently.* Channel names beat their own tier's average over the next
   13 weeks by 0.6% to 1.4%. All of it is from 2017 on (mega +2.26%,
   large +1.45%, mid +0.99%, small +2.05%); before 2017 it is 0.1% to
   0.6% and indistinguishable from nothing. That is a decade in which
   what had been rising kept rising.
3. *The book does worse than the picture.* Measure 3 holds every channel
   name for a fixed 13 weeks; the book picks the ten straightest and
   sells on the first close under a fixed line. In three tiers of four
   the book places below what the plain picture would suggest, which
   points at the choosing and the selling, not at the channel.
4. *Small caps are where the survivor problem bites.* The small tier's
   average compounds 17.7% a year, an impossible number for small caps
   as a class: the tier is full of names that were small then and are
   large now, and a random draw gets them for free. A channel rule,
   which sells whatever dips, cannot keep up with a pool like that. So
   the 10th percentile there is the least trustworthy number on this
   page, in either direction.

**Scored against the predictions.** (1) Half: the picture is most common
in mega and large; it does not last longer there. (2) Missed: the 13-week
edge is not confined to the smaller tiers; mega is as strong as small.
(3) Missed, reversed: the book places highest in large and lowest in
small. (4) Held: no tier clears the line in both halves.

**What it means.** If the channel book is used anywhere, the evidence
leans to large caps (roughly the S&P 500 below its top hundred), and
leans only: one tier in four doing well in one half in two is what
chance looks like too. The owner's own examples are small caps, the tier
this data is least able to judge. A forward record on small caps is the
only clean test of them.

## Pass 44 -- the owner's marks, forward: his own channels, logged before they trade (registered 2026-11-20 with the first marks)

Passes 38 to 43 tried to write the owner's chart reading as a formula and
test it on history. Every one of them carries the survivor problem, and
none draws exactly what he draws (his channels run up to four years, he
anchors a new one at the low after the last break, and he accepts
choppier ones than the 0.80 straightness rule does). This pass skips the
formula. He marks charts; the marks are written down with the date before
the next session opens; they are scored later against prices nobody had
seen. No history, no survivors, no hindsight.

**The ledger.** `lab/owner_marks.json`. One row per mark: the date he
sent it, the ticker, the last close, and his call, one of:
- `potential`: a channel he reads as forming or intact and worth owning.
- `ideal`: shown as an example of the picture, not called a buy.
- `broken`: a channel he reads as broken, to be avoided until a new
  pattern shows.
Rows are never edited or removed. A changed mind is a new row.
- `withdrawn` (added 2026-11-20, before any mark had traded): a mark he
  takes back before its entry session opens. The earlier row stays; the
  name is left out of scoring. A mark taken back after it has traded is
  not withdrawn: it is scored, and his new view is a new row.

**Scoring (fixed).** Each mark is entered at the open of the first
session after its date. At 4, 13 and 26 weeks: the name's return, SPY's
over the same days, and the name's place (0 to 100) among the returns of
every name in its size tier of `lab/universe_all_2026-11-20.csv` (Pass
43's tiers, by rank that week). Dividends included, no costs.
- `potential` should place above 50 on average. `broken` should place
  below 50. `ideal` is reported and not judged.
- Nothing is concluded from fewer than 40 marks of one call with a
  13-week score. Until then the page shows the rows and says "too few".

**The mechanical shadow.** Beside each `potential` mark, the lab draws
the lower line from the anchor low he used (read off his picture to the
month) as the steepest straight line under every weekly low since, fixed
on the mark date, and records the first weekly close below it. That is a
record of where the rule would have sold, not a part of the score.

**Predictions.** (1) `broken` names place below 50 at 13 weeks: his
breaks came late in Pass 41's overlay but the five that had already
broken all kept falling. (2) `potential` names place between 45 and 60:
a real edge here, if there is one, is small. (3) Forty marks of one call
will take months, so the first honest read is in 2027.

The scorer is written and committed before the first 4-week score is due
(2026-12-18).

## Pass 45 -- the channel rule, frozen: what the owner's marks taught, tested on history it has not seen (registered 2026-11-20 before any run)

The owner, 2026-11-20: "It should mostly be mathematical now, although I
think we should sell when it breaks the bottom of the channel rather than
limit the top." And on testing it: "pick some random day in history and
put an AI entity in a windowless box". A formula is that box: it cannot
know what came next. What it cannot escape is the list of names it is
shown, which is survivors (Pass 43). This pass freezes the rule as the
evening's 66 marks shaped it and runs it over twenty years.

**What changed from Pass 41, and where each change came from.**
1. *The anchor.* Pass 41 anchored at the lowest low of two years. His
   pictures (Agilent's six channels, AZN, ATO, ABT, AMPH) anchor at the
   low that started the current move, and after a break at the low that
   followed it; his AGX and ACLS channels ran three and four years. So:
   the look-back is tried at 52, 104, 156 and 208 weeks and the first one
   whose lowest low is a real swing low (not within the window's first
   four weeks) is used; after a break, no anchor may predate the break.
2. *Age.* 13 weeks or more since the anchor (Pass 41: 26). He marked
   channels as young as seven weeks; 13 is my compromise, not his number.
3. *Straightness.* 0.70 or more (Pass 41: 0.80). He accepts choppier
   channels than 0.80 allowed (ACLS, ABCB, ANET, AIR).
4. *Not already broken.* The last close is no more than 4.7 of the
   stock's own weekly swings below its 52-week high close (a swing is the
   standard deviation of its weekly log returns over two years). Fitted
   tonight to his calls on 32 A names, where it matched 30; his own
   explanation of ANRO and AMLX ("big quick run ups") is why it is in
   swings and not percent.
5. *A real stock.* Weekly swing of 1.5% or more, which drops the notes
   and preferred shares that passed Pass 41's rule.
6. *The exit, his instruction.* The lower line is fixed at entry and
   extended; the name is sold at the next open after the first weekly
   close below it. Nothing sells at the top. No buffer.
Unchanged: the lower line is the steepest straight line under every
weekly low since the anchor, it must rise 10% a year or more, weekly
bars, Friday decision, Monday open.

**Why history is a fair test of it.** Items 1 to 5 were shaped on names
beginning with A as they stood on 2026-11-20. Nothing before that date
was looked at in choosing them. Passes 38 to 43 did look at this history
for the earlier drawings, so this is not the first visit, and it is
counted as the seventh draw at the idea.

**The basket (primary).** Every tradeable name that qualifies is bought
(Pass 43's universe and rules: $3 or more, $5M median weekly dollar
volume, costs by size tier) and held until its line breaks; the book is
split equally among whatever is held. No slots and no ranking, because
Pass 43 showed the ten-slot book doing worse than the picture itself.
Scored against 200 random baskets a week of the same number of names from
the same tradeable pool.

**The windowless view.** Every entry is a card: a name and a date. Per
card, the return over the next 13 and 26 weeks minus the average of every
tradeable name over the same weeks, and the return and length of the
hold to its break. Reported overall, by size tier and by half.

| Arm | What it is |
|---|---|
| **basket** | as above -- the primary |
| no pullback rule | item 4 removed: what the swing rule adds |
| older only | 26 weeks or more since the anchor: what the young channels add |
| ten straightest | ten slots, straightest first, as Passes 41 and 43 |

**Verdict lines (fixed).** *Beats luck:* the basket at or above the 95th
percentile of its random baskets overall and the 75th in each half (to
2016, from 2017). *Better ride:* Sharpe above SPY's and a smaller largest
drawdown. *The cards:* a 13-week excess that is positive in both halves.

**The bias, stated before the result.** Survivors, as in Pass 43, worst
in the small tiers. It inflates the basket and the random baskets alike;
it still penalises selling, because every sold name here came back. A
pass on these lines would earn a forward page, where there are no
survivors. It would not be proof.

**Predictions.** (1) The cards' 13-week excess is positive overall and
since 2017, and near zero before 2017 (Pass 43's pattern). (2) The
basket places between the 40th and 85th percentile overall and fails the
beats-luck line on the first half. (3) The pullback rule helps: the
basket places higher with it than without. (4) Median hold between 10
and 25 weeks; fewer than half of holds end at a gain; the mean hold gains
more than 5%.

    python lab/pass45_channel_frozen.py          # every arm (slow: tens of minutes)
    python lab/pass45_channel_frozen.py smoke    # plumbing: 300 names

## Pass 45 results -- the frozen rule owns a third of the market and earns a little less than the market

Run 2026-11-20, `lab/results/pass45_channel_frozen.json`. 3,004 names,
1,001 weeks, 2007-09-14 to 2026-11-13. "Pool" is every tradeable name,
equal weight.

| | Compound a year | Sharpe | Largest drawdown | Place among random baskets | Cards | 13-week return over the pool | t | Cards beating the pool |
|---|---|---|---|---|---|---|---|---|
| SPY | 10.9% | 0.66 | -54.6% | | | | | |
| pool | 11.7% | 0.60 | -56.9% | | | | | |
| **basket** | **9.6%** | **0.58** | **-50.9%** | **0th** | 16,206 | +0.13% | -0.3 | 46% |
| no pullback rule | 9.8% | 0.59 | -53.3% | 0th | 17,169 | +0.02% | -0.5 | 46% |
| older only | 9.8% | 0.59 | -53.7% | 0th | 11,738 | +0.49% | 0.6 | 47% |
| ten straightest | 8.3% | 0.48 | -56.5% | 12th | 165 | +0.61% | -0.4 | 50% |

| Basket by half | Compound a year | Pool | SPY | Sharpe | Pool | SPY | 13-week card excess |
|---|---|---|---|---|---|---|---|
| to 2016 | 7.0% | 10.7% | 6.9% | 0.45 | 0.55 | 0.45 | -0.09% |
| 2017 on | 12.2% | 12.7% | 14.8% | 0.71 | 0.66 | 0.89 | +0.27% |

**Against the lines.**
- *Beats luck:* **no.** Below every random basket, overall and in both
  halves. (A basket of 600 names leaves random baskets almost no spread,
  so any shortfall reads as the 0th percentile; the plain fact is 9.6% a
  year against the pool's 11.7%.)
- *Better ride:* **no.** Sharpe 0.58 against SPY's 0.66; the drawdown is
  a little smaller (-50.9% against -54.6%).
- *The cards:* **no.** The 13-week excess is +0.13% over 16,206 cards,
  indistinguishable from zero, negative before 2017, and 46% of cards
  beat the pool.

**What it shows.**
1. *The rule is not picky.* The basket holds 614 names on an average
   week, about a third of everything tradeable. The owner marked roughly
   one A name in eight. A rule that says yes this often is describing a
   rising market, not choosing within it, and a book that owns a third of
   the market and sells the dips earns the market less the dips.
2. *A card tells you nothing about the next quarter.* A name qualifying
   on a random day did as well over the next 13 weeks as any other
   tradeable name, to a tenth of a percent. That is the windowless-box
   answer for this rule on this list.
3. *The trade shape is still a trend rule's:* 36% of holds end at a gain,
   the median loses 3.4%, the mean makes 3.6%, median hold twelve weeks.
   The winners do not pay for the losers by enough.
4. *The pullback rule did nothing here.* It matched his eye on tonight's
   names and moved the result by 0.2 points a year the wrong way. It
   keeps names out at entry; it says nothing once a name is held.
5. *Older channels were slightly better cards* (+0.49% against +0.13%),
   still nothing. That is the opposite direction from the owner's next
   idea (channels of four to eight weeks) and is noted for that pass.

**A flaw in what I registered.** The cards by size tier were measured
against the whole pool, and the pool's small names are the survivors
that inflate it (Pass 43). So the tier rows in the JSON (large caps
-0.25%, small +0.79%) compare each tier with a biased average and should
not be read as "small is better". Pass 43's within-tier comparison is
the fair one and it pointed at large caps.

**Scored against the predictions.** (1) Not shown: the sign is as
predicted in each half but every number is within noise of zero. (2)
Missed: I predicted the 40th to 85th percentile; it is the 0th. (3)
Missed: the pullback rule did not help. (4) Two of three: median hold 12
weeks and 36% of holds at a gain, but the mean hold gained 3.6%, not over
5%.

**What it means.** Seven draws at this idea on history, and the answer
has not changed since Pass 41: about the market's return, a little less
of its fall, no evidence of picking. Writing the owner's eye down more
faithfully made the rule match his marks better and did not make it
earn more. Either his eye adds something the formula still lacks (he is
far pickier than it is), or the picture does not predict. History with
this list cannot say which. Pass 44's ledger can: 42 of his own marks go
in at Monday's open.

## Pass 46 -- the Heikin-Ashi channel: starting candle, first decent pullback, and two ways to treat a break (registered 2026-11-20 before any run)

After Pass 45 the owner described how he actually draws, 2026-11-20: "I
usually use the first decent pullback as the channel angle from the
starting candle"; "the first candle's low is the auto sell price probably
until that is established"; "it needs a solid 4-8 weeks of trending up
before it is considered"; "I use Heikin-Ashi candles too". Asked whether a
broken line is a sale or gets flattened through the new low: "I guess it
should be dynamic as it goes up with some cushion. We should test both
though, you never know! If there are enough opportunities might work
better this way." Checked against nine of his pictures first: a line
from the starting candle through the first red run reproduces his AGX,
ACMR, AMPH, ABT and Agilent channels; it does not reproduce ADM or CAT,
whose drawn lines pass through pullbacks that came a year later.

**Candles.** Weekly Heikin-Ashi from adjusted bars. A candle is red when
its Heikin-Ashi close is under its open. Every line, low and break below
is read on these candles; trades are at the next week's real open.

**The channel (fixed).**
- *Starting candle:* the lowest Heikin-Ashi low since the last break (or
  of the last 104 weeks).
- *First decent pullback:* the first run of two or more red candles that
  begins four or more weeks after the starting candle. It is established
  on the first green candle after it.
- *The line:* from the starting candle's low through that run's lowest
  low, on a log scale, extended. It must rise 10% a year or more, or the
  run is passed over and the next one is used.

**Two entries.**
- *At the bounce:* bought the week the pullback is established.
- *Early:* bought six weeks after the starting candle if that candle is
  green and at least four of the six since the start are; until the line
  exists it is sold on a Heikin-Ashi close under the starting candle's
  low. If those conditions are not met it is bought at the bounce.

**Two exits (his "test both").**
- *Sell and restart:* sold on the first Heikin-Ashi close under the line.
  The next channel starts from the low after that break.
- *Dynamic with cushion:* when a later red run ends with its low under
  the line, the line is flattened to run through that low. The name is
  sold only on a Heikin-Ashi close more than a cushion under the line as
  it stood before the run began, or when the flattened line no longer
  rises 10% a year. The cushion is one of the stock's own weekly swings
  (and two, as a second arm).

| Arm | Entry | Exit |
|---|---|---|
| restart, bounce | at the bounce | sell and restart |
| restart, early | early | sell and restart |
| **dynamic 1, bounce** | at the bounce | dynamic, one swing -- the primary |
| dynamic 1, early | early | dynamic, one swing |
| dynamic 2, bounce | at the bounce | dynamic, two swings |
| dynamic 2, early | early | dynamic, two swings |

The primary is the owner's own guess ("I guess it should be dynamic").
"Sell and restart" is reported beside it on equal terms and is not a
second chance at the verdict.

**Universe and book.** Pass 43's names and tradeable rule. Two sets, both
reported: the **top 500** by size that week (the tier the earlier passes
leaned to, and the one this data judges most fairly), and **every
tradeable name**. Every signal is bought and the book is split equally
among what is held (cash when nothing is). Costs by size tier. Scored
against 200 random baskets a week of the same number of names from the
same set, and against SPY.

**Cards.** Per entry, the return over the next 13 and 26 weeks minus the
average of the same set over the same weeks.

**Verdict lines (fixed, for the primary on the top 500).** *Beats luck:*
at or above the 95th percentile of its random baskets overall and the
75th in each half. *Better ride:* Sharpe above SPY's and a smaller
largest drawdown. *The cards:* a positive 13-week excess in both halves.

**This is the eighth draw.** Same list, same survivors, same caution as
Pass 45: a pass earns a forward page, not a conclusion.

**Predictions.** (1) "Sell and restart" trades several times as often as
"dynamic" and has the shorter median hold by half or more. (2) "Dynamic"
has the higher compound return of the two. (3) No arm beats luck on the
top 500. (4) Early entry is worse than entry at the bounce: it buys
before there is a channel. (5) The 13-week card excess is within 0.5% of
zero for every arm on the top 500.

    python lab/pass46_ha_channel.py          # every arm, both sets
    python lab/pass46_ha_channel.py smoke    # plumbing: 300 names

## Pass 46 results -- both exits fail the same way; the Heikin-Ashi rule is in a "channel" on half of all large caps at once

Run 2026-11-20, `lab/results/pass46_ha_channel.json`. 3,004 names, 1,001
weeks to 2026-11-13. SPY over the same weeks: 10.9% a year, Sharpe 0.66,
largest drawdown -54.6%.

**Top 500 by size (a median of 472 tradeable names a week; the pool compounds 9.6%).**

| Arm | Compound a year | Sharpe | Largest drawdown | Place among random baskets | To 2016 | 2017 on | Names held | Entries a year | Median hold | Holds ending at a gain | Mean gain | 13-week card excess |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| restart, bounce | 8.4% | 0.56 | -51.0% | 2nd | 10th | 2nd | 190 | 496 | 6 wk | 37% | +2.8% | -0.28% |
| restart, early | 9.0% | 0.58 | -53.8% | 2nd | 6th | 6th | 272 | 578 | 13 wk | 43% | +4.2% | -0.27% |
| **dynamic 1, bounce** | **8.6%** | **0.57** | **-55.5%** | **0th** | 3rd | 0th | 240 | 383 | 10 wk | 37% | +5.1% | -0.30% |
| dynamic 1, early | 9.2% | 0.59 | -55.2% | 2nd | 13th | 2nd | 302 | 443 | 16 wk | 42% | +6.2% | -0.32% |
| dynamic 2, bounce | 8.8% | 0.58 | -56.2% | 0th | 3rd | 2nd | 272 | 303 | 14 wk | 38% | +7.9% | -0.36% |
| dynamic 2, early | 9.5% | 0.61 | -54.5% | 9th | 20th | 6th | 321 | 349 | 19 wk | 41% | +8.7% | -0.31% |

On every tradeable name the picture is the same with larger numbers: 8.8%
to 10.2% a year against a pool at 11.7%, every arm at or near the bottom
of its random baskets, card excess -0.17% to -0.31%.

**Against the lines (primary: dynamic 1, bounce, top 500).** *Beats
luck:* **no** (0th percentile, 3rd and 0th by half). *Better ride:*
**no** (Sharpe 0.57 against SPY's 0.66, drawdown no smaller). *The
cards:* **no** (-0.30% overall; +0.25% before 2017, -0.89% since).

**The two exits, as he asked.**
- *Dynamic earns a little more than sell-and-restart*: 8.6% against 8.4%
  at one swing of cushion, 8.8% at two. Wider cushion, longer holds,
  bigger average win (7.9% against 2.8%), slightly more money.
- *Sell-and-restart does find more opportunities*: 496 entries a year
  against 383, median hold six weeks against ten. They are not better
  opportunities; each one earns less.
- *Neither changes the verdict.* The gap between the best and worst arm
  (9.5% against 8.4%) is about half the gap between any of them and SPY.

**What the pass shows that the others had not made this plain.**
1. *The rule is in a channel almost everywhere.* The arms hold 190 to
   320 of 472 large caps at once. The owner marked about one name in
   eight. Passes 45 and 46 wrote down how he draws a line; neither wrote
   down how he chooses which lines to care about, and that choosing is
   most of what he does.
2. *A card is slightly worse than a random name*: about -0.3% over 13
   weeks in every arm, and in three arms that is distinguishable from
   zero (t near -3). The buy fires after a bounce or after six green
   weeks, which in large caps is on average a little late.
3. *Buying early beat waiting for the bounce* in every pair, by about
   0.6 points a year. Waiting for the pullback to establish the angle
   costs more than the angle is worth.

**Scored against the predictions.** (1) Half: sell-and-restart trades
1.3 to 1.6 times as often, not several times; its median hold is about
half. (2) Held, narrowly. (3) Held. (4) Missed: early entry is better
than the bounce. (5) Held: every card excess is within 0.5% of zero.

**What it means.** Eight draws. The drawing has gone from a 26-week
best-fit band to his own Heikin-Ashi construction, the exit from a fixed
break to a cushioned dynamic line, the universe from 500 names to 3,000,
and the answer has stayed where it was: a little under the market, with
no sign that a qualifying chart predicts the next quarter. More history
passes on the line and the exit will not move it. What has not been
written down or tested is his selection, and the only fair test of that
is Pass 44.

## Pass 47 -- choosing: only add names in the four strongest sectors (registered 2026-11-20 before any run)

Pass 46 ended on the point that the rule draws the owner's line and does
none of his choosing: it sat in a channel on half of all large caps. His
answer, 2026-11-20: "What if they only consider adding stocks in the top
four trending channel sectors? So they don't go nuts adding everything."
And on timing: "If you wait 9 weeks or so to buy a stock the second
weekly low candle is usually lower than the one you mark off of so I
would go off of the lowest in the watch window." Lab only.

**What does not change.** Pass 46's Heikin-Ashi channel and its dynamic
exit with one weekly swing of cushion. The starting candle is already the
lowest Heikin-Ashi low of the watch window and moves down if a later
candle undercuts it, which is his second point; nothing to change there.

**What changes.**
- *The wait:* the early entry moves from six weeks after the starting
  candle to **nine**, with at least six of the nine candles green. (A
  name that misses it is bought at the bounce, as before.)
- *The sector rule:* a name is only **added** in a week its sector is one
  of the four strongest. A name already held is kept whatever its sector
  does; the exit is the channel's alone.

**"Strongest", two ways.**
- *By channels (the primary, his words):* the share of the sector's
  top-500 names that the rule itself has in a channel that week. Sectors
  with fewer than ten names are not ranked.
- *By the fund:* the sector fund's return over the last 26 weeks.

| Arm | Adds allowed in |
|---|---|
| no sector rule | every sector (the nine-week entry alone) |
| **top four by channels** | the four sectors with the largest share of names in a channel -- the primary |
| top four by fund | the four sector funds with the best 26-week return |
| bottom four by channels | the four with the smallest share: the check that "four sectors" is not doing the work by itself |

**Universe, book, control, verdict lines.** As Pass 46 on the top 500 by
size (every tradeable name is reported beside it): every allowed signal
bought, the book split equally, costs by tier, 200 random baskets a week
of the same number of names from the same set, SPY. Beats luck at the
95th percentile overall and the 75th in each half; better ride on Sharpe
and drawdown against SPY; cards positive in both halves.

**Why this is a fairer question than the last two.** Passes 38 and 42
found that a sector's own channel is no gate and no early warning. This
is different: it ranks sectors against each other and takes the leaders,
which is sector momentum, and that has support in the published record.
It is also the ninth draw, and a rule that is right about sectors and
wrong about stocks would still show up here as a pass.

**Predictions.** (1) The sector rule cuts the names held by more than
half. (2) Top four by channels compounds more than no sector rule, by
less than one point a year. (3) Top beats bottom, by less than one and a
half points. (4) The primary does not beat luck. (5) Ranking by the fund
does about as well as ranking by channels (within half a point).

    python lab/pass47_sector_choice.py          # every arm, both sets
    python lab/pass47_sector_choice.py smoke    # plumbing: 400 names

## Pass 47 results -- the sector rule stops it adding everything, and does not make it earn more

Run 2026-11-20, `lab/results/pass47_sector_choice.json`. Top 500 by size;
the pool compounds 9.6% and SPY 10.9% (Sharpe 0.66, drawdown -54.6%).

| Arm | Compound a year | To 2016 | 2017 on | Sharpe | Largest drawdown | Place among random baskets | To 2016 | 2017 on | Names held | Entries a year | 13-week card excess |
|---|---|---|---|---|---|---|---|---|---|---|---|
| no sector rule | 8.4% | 6.3% | 10.5% | 0.55 | -55.7% | 0th | 1st | 0th | 284 | 411 | -0.42% |
| **top four by channels** | **7.9%** | 4.4% | 11.3% | **0.52** | **-58.6%** | **2nd** | 0th | 34th | 116 | 170 | -0.71% |
| top four by fund | 8.7% | 6.3% | 10.9% | 0.58 | -52.4% | 8th | 14th | 24th | 111 | 153 | -0.12% |
| bottom four by channels | 6.9% | 4.0% | 9.7% | 0.47 | -64.3% | 7th | 17th | 3rd | 87 | 121 | -0.28% |

On every tradeable name: 9.4%, 9.1%, 10.4% and 9.9% in the same order,
against a pool at 11.7%.

**Against the lines (primary: top four by channels).** *Beats luck:*
**no** (2nd percentile; 0th and 34th by half). *Better ride:* **no**
(Sharpe 0.52 against 0.66, a deeper drawdown than SPY). *The cards:*
**no** (-0.71%; negative in both halves).

**What the sector rule did.**
1. *It did what he asked of it.* Names held fall from 284 to 116, entries
   from 411 a year to 170. The book no longer adds everything.
2. *It did not help, and by channels it hurt.* 7.9% a year against 8.4%
   with no sector rule, and a deeper drawdown.
3. *Strong sectors do beat weak ones, modestly*: top four by channels
   7.9% against bottom four 6.9%. So the ranking carries some
   information. Being selective is not the same as selecting well: both
   are below the book that takes everything.
4. *Counting channels ranks the quiet sectors first.* The sector chosen
   most often by channel count is Utilities (half of all weeks), then
   Health Care. A utility stays inside a channel because it barely
   moves, not because it is leading. Ranking by the fund's 26-week
   return chooses Information Technology most (58% of weeks) and is the
   better of the two by 0.8 points a year with a shallower drawdown. It
   is the same pull found in Cecil's safety leg (Pass 37) and in Pass
   42's "weakest survive longest": a channel test rewards stillness.

**Scored against the predictions.** (1) Held: names held more than
halve. (2) Missed: the channel-count rule compounds less than no rule,
not more. (3) Held: top beats bottom by 1.0 point. (4) Held. (5) Missed:
the fund ranking is 0.8 points ahead of the channel ranking, not within
half a point.

**What it means.** Nine draws. Cutting the list by sector makes the book
smaller and leaves it where it was. If a sector layer is ever used, rank
by the fund's return and not by how many of its names are in a channel.
The standing conclusion from Pass 46 is unchanged: no version of the
line, the exit or now the sector cut has shown a qualifying chart to be
worth more than a random one, on a list that cannot be fully trusted,
and the forward ledger (Pass 44) is where the question goes next.

## Pass 48 -- the screen as the book: hold what the screen flags, and only that (registered 2026-11-20 before any run)

The owner caught a gap, 2026-11-20: "you said every formula picked half
the market, why didn't it pick the ones you flagged? That wasn't half the
A names for sure that we chose." He is right, and the gap is in the
lab's harness.

**What he reviewed and what was tested were different things.**
- The list he went through on the A names was a *snapshot*: the names
  that, that week, had a channel worth owning by Pass 41's rule (a
  two-year look-back, 26 weeks old or more, straightness 0.80). It
  flagged 46 of 303 A names, about one in seven, and he agreed with
  about two thirds of them.
- The *books* in Passes 45 to 47 held a third to a half of the market for
  two reasons. They buy a name once and keep it until its line breaks,
  so the holdings are everything that ever qualified and has not broken
  yet, far more than qualify in any one week. And Passes 46 and 47
  dropped the straightness test altogether: any name with a starting
  low, a few green weeks and a red run got a line.
- So the picky screen, the one thing checked against his eye, has never
  been tested as a portfolio. The nearest measurement is Pass 43's third
  number: name-weeks on that screen beat their own size tier over the
  next 13 weeks by 0.6% to 1.4%, all of it since 2017. That was the one
  positive finding of the evening and nothing was built on it.

**The screen (fixed).** A name is on it in a week when it is tradeable
(Pass 43's rule), its weekly swing is 1.5% or more, it has a Pass 41
channel worth owning (look-back 104 weeks, anchor 26 to 100 weeks back,
lower line rising 10% a year or more, straightness 0.80 or more), and it
is no more than 4.7 of its own weekly swings under its 52-week high (the
rule fitted to his calls on the A names).

**The books.**

| Arm | What it holds |
|---|---|
| **the screen, weekly** | exactly the names on the screen each week, equal weight; a name is sold the week it drops off -- the primary |
| the screen, 13 weeks | a name is bought when it appears and held 13 weeks, then kept only if it is still on the screen |
| screen in, break out | bought when it appears, sold only on a weekly close under the line fixed at entry (his stated exit) |
| no pullback rule | the primary without the 4.7-swing rule |

The primary sells a name when it stops looking like the picture, which is
not the same as waiting for the bottom of the channel to break; the third
arm is his exit, for the comparison.

**Universe, control, verdict lines.** The top 500 by size (primary) and
every tradeable name, costs by tier, 200 random baskets a week of the
same number of names from the same set, SPY. Beats luck at the 95th
percentile overall and the 75th in each half; better ride on Sharpe and
drawdown against SPY.

**Counted honestly.** This is the tenth draw at the idea, and the 4.7-
swing rule was fitted on 32 names tonight. But it is the first draw that
tests the object the owner actually agreed with, and it is aimed at the
one place a positive number has already been seen. Pass 43 also says
where that number will fail: before 2017.

**Predictions.** (1) The primary holds between a tenth and a quarter of
the top 500 on an average week. (2) It compounds more than the pool since
2017 and no more than the pool before 2017. (3) Overall it places
between the 60th and 95th percentile of its random baskets and fails the
75th in the first half. (4) "Screen in, break out" compounds less than
the primary: the hold-until-break rule is where the earlier books lost
what the screen had. (5) Weekly turnover makes the primary's costs the
largest of the four.

    python lab/pass48_screen_book.py          # every arm, both sets (slow: about ten minutes)
    python lab/pass48_screen_book.py smoke    # plumbing: 300 names

## Pass 48 results -- the screen itself: better than a random large cap since 2017, far worse before, and under SPY in both halves

Run 2026-11-21, `lab/results/pass48_screen_book.json`. 957 weeks from
2008-07. Top 500 by size: the pool compounds 10.8% (10.1% to 2016, 11.4%
since); SPY 12.3% (9.5%, 14.8%), Sharpe 0.73, largest drawdown -46.3%.

| Arm | Compound a year | To 2016 | 2017 on | Sharpe | Largest drawdown | Place among random baskets | To 2016 | 2017 on | Names held | Median hold |
|---|---|---|---|---|---|---|---|---|---|---|
| **the screen, weekly** | **9.2%** | 6.5% | 11.5% | **0.61** | **-33.3%** | **12th** | 9th | 36th | 90 | 6 wk |
| the screen, 13 weeks | 8.7% | 2.7% | 14.1% | 0.54 | -58.1% | 8th | 2nd | 100th | 117 | 13 wk |
| screen in, break out | 8.5% | 4.1% | 12.5% | 0.54 | -56.6% | 5th | 0th | 98th | 221 | 7 wk |
| no pullback rule | 9.7% | 4.8% | 14.1% | 0.62 | -46.2% | 29th | 10th | 98th | 94 | 6 wk |

On every tradeable name all four are worse: 6.2% to 9.4% against a pool
at 13.2%, at the bottom of their random baskets overall.

**Against the lines (primary, top 500).** *Beats luck:* **no** (12th
percentile; 9th and 36th by half). *Better ride:* **no** on Sharpe (0.61
against 0.73); the drawdown is much smaller (-33.3% against -46.3%).

**What the screen does, now that it has been tested as itself.**
1. *It is the size he expected.* 90 names of about 470, one in five.
2. *Since 2017 it chooses better than chance, in three forms of four.*
   Held 13 weeks, held to the break, or held weekly without the pullback
   rule, it sits at the 98th to 100th percentile of random baskets of
   large caps and compounds 12.5% to 14.1% against the pool's 11.4%.
   That is a real result for those ten years and it is the owner's
   picture doing it.
3. *Before 2017 it is as bad as it is good after.* 2.7% to 6.5% a year
   against the pool's 10.1%, at the 0th to 10th percentile. 2009, 2011,
   2014 to 2016 are years of sharp reversals, and a rule that owns what
   has been rising straight is on the wrong side of each one.
4. *It does not beat SPY in either half.* Since 2017 the best arm makes
   14.1% and SPY 14.8%. SPY is weighted by size and that decade belonged
   to the largest companies; an equal-weight book of ninety large caps
   gave up three points a year to that before it chose anything (the
   pool's 11.4% against SPY's 14.8%).
5. *The pullback rule earns its keep only on the ride*: with it the
   drawdown is -33.3% and without it -46.2%, for half a point less
   return.
6. *His exit is not what cost the earlier books.* "Screen in, break out"
   is 0.7 points behind the weekly screen over the whole period and
   ahead of it since 2017.

**Scored against the predictions.** (1) Held: 19% of the top 500. (2)
Held: ahead of the pool since 2017 (barely, for the primary), behind it
before. (3) Half: it fails the first half as predicted, but overall it
places 12th, not between the 60th and 95th. I underestimated how bad the
first half was. (4) Held. (5) Held: 763 trades a year, the most.

**What it means.** The owner was right that the lab had not tested what
he agreed with, and testing it changed the picture in one respect: the
screen does pick, in the last ten years. It did not change the answer to
his question. Over twenty years, in either half, in any of four ways of
holding it, the screen does not beat the S&P 500. What it is, on this
evidence, is a momentum screen: good while trends persist, costly when
they reverse, and so far unable to tell which kind of year it is in.
That last sentence is where the next real idea would have to be, and it
is not a tweak to the line.

## Pass 49 -- the channel screen as the Council's universe (registered 2026-11-21 before any run)

The owner on the Pass 48 results, 2026-11-21: "our market regime and
weekly analysis has been solid. I think these picks plus the council
could produce some solid stuff. Use it as their universe or something
each week." So: the three engines keep doing what they do, but each
Monday they may only choose among the names the channel screen flags.
Lab only; nothing in production changes.

**The filter (fixed).** Each Monday, from weekly bars that end before it:
a name of the Council's live universe passes when it has a Pass 41
channel worth owning (look-back 104 weeks, anchor 26 to 100 weeks back,
lower line rising 10% a year or more, straightness 0.80 or more), its
weekly swing is 1.5% or more, and it is no more than 4.7 swings under its
52-week high: Pass 48's screen, unchanged. If fewer than ten names pass,
the engines scan the whole universe that week and the week is counted as
a fallback.

**Two things are measured.**
1. *History, as far as the engine replay reaches.* Production's engine
   code replayed on every Monday from 2024-06-03 to the last closed week,
   with and without the filter, on the lab's usual basis (Monday open to
   Friday close, dividend-adjusted, cash at zero, the earnings blackout
   fed). This is the engines without the LLM layer, as `production` is on
   the forward page. Beside them: every screen name held equal weight,
   and the whole universe equal weight.
2. *Forward.* A design named `channel-universe` joins the forward page
   from the week of 2026-11-23, replayed each Monday beside `production`.

**Verdict line for the history (fixed).** The filter *helps the engines*
if the weekly alpha of filtered-minus-unfiltered is positive with a t of
2 or more over the whole window, and positive in each half of it.

**Read this before the result.** The window is two and a half years,
all of it inside the stretch where Pass 48 found the screen works (2017
on) and none of it inside the stretch where it failed. A pass here says
the filter helps in the kind of market it was already known to like. It
cannot say what happens in a 2011 or a 2015. And on the forward record so
far, `production` trails SPY, so "solid" is the owner's read of the
Council, not the record's; the filter is being asked to improve engines
that have not yet shown an edge of their own.

**Predictions.** (1) The filter leaves 30 to 70 names of the universe on
a typical Monday and falls back in fewer than one week in ten. (2)
Filtered-minus-unfiltered is positive, between 0 and +0.15% a week, with
a t under 2: it helps a little and does not clear the line. (3) Every
screen name held equal weight does about as well as the filtered engines
(within 0.05% a week): the screen does the work and the engines add
little on top.

    python lab/pass49_council_channel.py          # the history
    python lab/pass49_council_channel.py smoke    # plumbing: the last eight weeks

## Pass 49 results -- the channel universe makes the engines worse, in both halves

Run 2026-11-21, `lab/results/pass49_council_channel.json`. 129 Mondays,
2024-06-03 to 2026-11-16, the Council's 274 names. SPY made +0.21% a week
on the lab's basis. The screen passed a median of 44 names (15 to 88) and
never fell back.

| | Weekly alpha, all 129 weeks | t | First 64 weeks | Last 65 weeks | Compounded over the window |
|---|---|---|---|---|---|
| engines, whole universe | +0.42% | 1.3 | +0.06% | +0.78% | +106.7% |
| **engines, channel universe** | **-0.15%** | -0.7 | -0.28% | -0.02% | **+3.5%** |
| every screen name, equal weight | -0.07% | | -0.18% | +0.05% | |
| every name, equal weight | +0.08% | | -0.01% | +0.17% | +41.7% |
| SPY | | | | | +27.3% |

Filtered minus unfiltered: **-0.57% a week (t -1.8)**, -0.34% in the
first half and -0.80% in the second; the filtered book was the better one
in 60 weeks of 129.

**Against the line.** The filter does not help the engines. It hurts
them, in both halves, by an amount just short of the usual bar for
calling a difference real.

**Why, as far as this shows.**
1. *On this universe and in these years the screen's names lagged.* Held
   equal weight they made -0.07% a week against +0.08% for the whole
   list. The Council's list is already hand-picked growth and theme
   names; inside it, the smooth steady climbers were the slower ones.
2. *The engines do not want what the screen offers.* Marky ranks on the
   last three weeks, Ophelia on sector rotation, Cecil on a low multiple.
   Their picks are movers and cheap names, and a name within 4.7 swings
   of its high in a straight two-year channel is rarely either. Taking
   those away removed the picks that carried the unfiltered replay.

**Do not read the first row as proof the Council works.** +0.42% a week
would be remarkable, and it is not established: its t is 1.3, the book
is five names, and above all the universe is the one the owner curated
in 2026, replayed back to 2024. Names are on that list partly because
they did well in those years, so every row here is flattered (the plain
equal-weight list beats SPY by 0.08% a week doing nothing). This is why
the forward page counts only from 2026-09-21, where `production` has
made about +0.2% a week over eight weeks. What the table can say is the
comparison between its rows, which share the flattery: on the same
names and weeks, the filter subtracted.

**Scored against the predictions.** (1) Held: a median of 44 names, no
fallback weeks. (2) Missed, wrong sign: I predicted the filter would
help by up to 0.15% a week and it cost 0.57%. (3) Missed narrowly: the
screen's names held equally (-0.07%) did somewhat better than the
filtered engines (-0.15%), not the same.

**What it means.** The channel screen and the Council's engines are
different ideas that do not stack. One owns smooth, established
climbers; the others pick movers, rotations and cheap names. Forcing the
second to choose from the first's list gives it less of what it uses.
The `channel-universe` design stays on the forward page as registered,
from the week of 2026-11-23, so the comparison continues on weeks nobody
has seen; on this evidence it is not a candidate for production.

## Pass 50 -- how much and when: sizing and staged buying and selling (registered 2026-11-21 before any run)

The owner, 2026-11-21: "We have been vague and loose about our buying and
selling rules too, they are currently all or nothing portion sizing with
super basic trading rules." Asked whether he meant how much goes into a
pick or when to get in and out: "I was talking about both." And on the
screen: it is "more like a Cecil picks and holds til they break type
thing", and "some of these stocks held the channels for years." Lab only.

Exits inside a one-week hold have been tested and are not repeated:
managing the week adds no return (Pass 13), his selling rules reshape
outcomes and not the return (Pass 15), the -5% stop costs like cash and
trims the tail (Pass 32). What has never been tested is sizing, and
buying or selling in pieces.

**Part A: the channel-hold book.** Pass 48's "screen in, break out" on the
top 500 by size: a name is bought when it appears on the screen and sold
on a weekly close under the line fixed at entry. Eight books, every
combination of:
- *How much:* **equal dollars** in every name, or **equal risk** (dollars
  in proportion to one over the stock's weekly swing, so a calm name
  gets more and a jumpy one less).
- *Buying:* **all at once**, or **in two halves**: half at entry, the
  other half four weeks later only if the name is still held and its
  close is above the close of its entry week (adding to what is working).
- *Selling:* **all at once** on the first weekly close under the line, or
  **in two halves**: half on the first close under the line, the rest on
  the next weekly close under it, whenever that comes.
The book is always fully invested across what it holds, so a half
position is a half weight relative to the others, not cash. Costs are
charged on every change of weight at the tier's rate.

**Part B: the weekly Council.** The engine replay of Pass 49 (129
Mondays from 2024-06-03, the whole universe), the five names it books
each week, total invested left as production has it. Nine books:
- *How much:* **production's weights**, **equal dollars**, or **equal
  risk**.
- *Buying:* **all on Monday's open**; or half on Monday and the other
  half at Wednesday's open **only if the name is above** its Monday open
  (add on strength); or the other half only if it is **below** (add on
  weakness). The half not bought is cash.
Everything is sold at Friday's close, as now.

**Verdict lines (fixed).** A rule *earns its place* if, against the same
book without it, it raises the Sharpe ratio by 0.05 or more **and** does
not lower the compound return by more than half a point a year (Part A),
or raises mean weekly alpha per unit of its weekly standard deviation by
a tenth or more without lowering mean alpha by more than 0.05% a week
(Part B). Sizing and timing are judged separately, and a rule has to
earn its place in both halves of its window.

**What this can and cannot show.** Both books are ones that did not beat
the S&P 500 on their own evidence (Pass 48), or whose record is flattered
by a hand-picked universe (Pass 49). This pass asks whether better rules
improve them, compared with themselves; it is not another attempt at the
market. Part B is two and a half years.

**Predictions.** (1) Equal risk lowers the book's swings more than its
return and earns its place in Part A on Sharpe; in Part B it lowers both
and does not. (2) Buying in halves on strength does not earn its place in
either part: the second half is bought higher. (3) Selling in halves in
Part A lowers return a little and does not earn its place. (4) Adding on
weakness in Part B is worse than adding on strength.

    python lab/pass50_size_and_time.py          # both parts
    python lab/pass50_size_and_time.py smoke    # plumbing: 300 names, eight weeks

## Pass 50 results -- no rule clears the line; equal risk suits the channel book and wrecks the Council's, and buying in pieces helps neither

Run 2026-11-21, `lab/results/pass50_size_and_time.json`.

**Part A, the channel-hold book** (top 500, 957 weeks from 2008-07, about
225 names held).

| How much | Buying | Selling | Compound a year | Sharpe | To 2016 | 2017 on | Largest drawdown |
|---|---|---|---|---|---|---|---|
| equal dollars | at once | at once | 8.6% | 0.53 | 0.26 | 0.79 | -61.4% |
| equal dollars | at once | in halves | 9.0% | 0.55 | 0.31 | 0.78 | -58.9% |
| equal dollars | in halves | at once | 8.9% | 0.54 | 0.28 | 0.79 | -60.4% |
| equal dollars | in halves | in halves | 8.9% | 0.54 | 0.29 | 0.78 | -60.1% |
| equal risk | at once | at once | 9.0% | 0.58 | 0.34 | 0.82 | -56.8% |
| equal risk | at once | in halves | 9.5% | 0.61 | 0.40 | 0.80 | -53.7% |
| equal risk | in halves | at once | 9.2% | 0.59 | 0.36 | 0.82 | -55.9% |
| equal risk | in halves | in halves | 9.4% | 0.60 | 0.38 | 0.81 | -54.7% |

- *Equal risk:* +0.05 Sharpe and +0.4 points a year overall, with a
  shallower drawdown. By half it is +0.08 and then +0.03, so it clears
  the line overall and in the first half and **not in the second**.
- *Selling in halves:* +0.02 Sharpe, +0.4 points a year. Helps a little
  everywhere; under the line.
- *Buying in halves:* +0.01. Nothing.
- The best book has both of the first two: 9.5% a year, Sharpe 0.61,
  drawdown -53.7%, against 8.6%, 0.53 and -61.4%. A real improvement in
  the ride, and still a book that trails SPY.

**Part B, the weekly Council** (129 Mondays from 2024-06-03).

| How much | Buying | Mean weekly alpha | Its weekly SD | Alpha per unit of SD | Worst week | Against production (t) |
|---|---|---|---|---|---|---|
| production's weights | all on Monday | +0.42% | 3.72% | 0.114 | -11.5% | |
| production's weights | half, add on strength | +0.20% | 2.61% | 0.077 | -7.9% | -0.22% (-1.5) |
| production's weights | half, add on weakness | +0.22% | 3.22% | 0.068 | -8.4% | -0.20% (-1.8) |
| equal dollars | all on Monday | +0.46% | 3.64% | 0.127 | -9.6% | +0.04% (0.8) |
| equal dollars | half, add on strength | +0.22% | 2.67% | 0.083 | -7.8% | -0.20% (-1.2) |
| equal dollars | half, add on weakness | +0.25% | 3.06% | 0.080 | -6.9% | -0.18% (-1.5) |
| equal risk | all on Monday | +0.02% | 2.29% | 0.010 | -6.6% | -0.40% (-2.0) |
| equal risk | half, add on strength | -0.06% | 2.02% | -0.029 | -7.9% | -0.48% (-1.9) |
| equal risk | half, add on weakness | -0.09% | 2.00% | -0.043 | -5.6% | -0.51% (-2.2) |

- *Equal risk removes the Council's alpha altogether* (+0.42% to +0.02%).
  In this replay the return came from the jumpiest names in the five, and
  sizing by risk gives those the least.
- *Buying in halves halves the alpha and cuts the swings by less.* The
  week is too short to buy in pieces: the half that waits until Wednesday
  misses the two days where much of the move is.
- *Equal dollars is as good as production's weights* (+0.46% against
  +0.42%, a slightly milder worst week). The confidence-and-merit
  weighting is not adding anything measurable over splitting the book
  five ways.
- Adding on strength and adding on weakness are indistinguishable.

**Against the lines.** No sizing rule and no timing rule earns its place
in both halves of either part.

**Scored against the predictions.** (1) Half: equal risk helps the
channel book as predicted but misses the line in the second half; on the
Council it does not earn its place, as predicted, and is far worse than I
expected. (2) Held. (3) Half: selling in halves does not earn its place,
but it raised the return a little instead of lowering it. (4) Not shown:
strength and weakness are the same.

**What it means.**
1. The two books want opposite sizing. The slow channel book holds
   hundreds of names for months, and tilting it to the calm ones smooths
   it at no cost. The weekly book holds five names for five days, and
   its edge, such as it is, is in the volatile ones. One sizing rule for
   both would be wrong for one of them.
2. For the weekly Council the cheap, defensible change is to drop the
   weighting scheme for equal dollars. It is not better by any margin
   that matters, but it is simpler and no worse. Not a candidate for
   production without the owner's say, and the universe caveat of Pass 49
   applies to every number in Part B.
3. Buying in pieces is not worth building for either book.
4. None of this moves either book past the S&P 500. Rules of this kind
   shape the ride. They were never likely to be where a missing edge
   was, and this pass does not change that.

## Pass 50 note -- the channel-hold book's drawdown is a start-up artifact of the test (2026-11-21)

The owner asked how a book that sells on a break can fall 54% to 61%.
A diagnostic of the baseline arm (same rule, same data, more printed; not
a new test) shows the figure is the whole book in 2008-09, and that three
choices of mine produced it.

1. *The book starts nearly empty.* Channels need two years of bars and
   the bars start in 2006, so the book opens in July 2008 with 24 names,
   not 225. It holds fewer than 50 names in 60 of 957 weeks, all at the
   start, and first reaches 100 in September 2009.
2. *There is no cash.* Money from a sold name is spread over what is
   left. The book went from 32 names in September 2008 to 2 in February
   2009, still fully invested: the trough (week ending 2009-03-06) is two
   stocks, and those two then missed 2009's rebound (+10% against +32%
   for SPY).
3. *The line is fixed at entry and can be far under the price.* Over all
   5,391 sales the line sat a median 6.2% under the entry close, but more
   than 28% under for a tenth of them, and the sale came a median 7.5%
   under the name's high while held (27% for the worst tenth). A name
   bought high above an old line can fall most of the way to nothing
   before it is sold (NVAX 2020-23, -98% from its high). The weekly-close
   trigger adds a median 2.1% of overshoot under the line.

**What this changes.** The -61.4% and -53.7% drawdowns, and the "to
2016" half of every hold-until-break book in Passes 48 and 50, are
dominated by a book of 2 to 32 names in the first year. From the saved
Pass 48 by-year figures, the top-500 "screen in, break out" book made
12.4% a year from 2010 on against 11.9% for the random pool and 13.8%
for SPY; before costs its largest fall from July 2009 on is -32.6%.
2010 is a cut chosen after seeing the result, so this is a reading, not
a verdict: without the start-up the book is a little ahead of luck and
still about a point and a half behind the S&P 500, on a list with
survivor bias in its favour.

**What a fair test of the owner's rule needs** (not yet registered):
sold slots go to cash, with a cap on any one name's weight; the line
moves up with the price ("dynamic as it goes up with some cushion",
which Pass 46 tested but Passes 48 and 50 did not carry over); and a
start no earlier than the week the book can hold a full set of names.

## Pass 51 -- the channel-hold book with cash, and the owner's 20% rule (registered 2026-11-21 before any run)

The owner, 2026-11-21, on seeing that the Pass 50 book held names through
falls of 50% and more: "I wouldn't hold anything 20% or more from its
high in the channel." This pass adds that rule and repairs the two faults
of construction the Pass 50 note found. Lab only.

**The book.** Pass 48's screen for entries (channel worth owning, weekly
swing of 1.5% or more, close within 4.7 swings of the 52-week high
close), bought at the next Monday's open. Every held name gets the same
weight, **one over the number held or one hundredth, whichever is
smaller; the rest is cash** earning nothing. So a book of 24 names is 24%
invested, and money from a sold name is not piled onto the survivors. A
sold name may come back when it is on the screen again. Decisions on the
weekly close, sold at the next Monday's open, costs at the tier's rate.

**Four exits.**
- *line*: a weekly close under the line fixed at entry (Passes 48, 50).
- *20% off the high*: a weekly close 20% or more under the name's high,
  the high being its 52-week high close at entry or any higher weekly
  close since. The owner's rule, alone.
- *line or 20%*: whichever comes first. The owner's rule as he would run
  it.
- *line or 4.7 swings*: the same with the distance scaled to the stock's
  own weekly swing in place of a flat 20% (his point on ANRO and AMLX,
  that a jumpy name sits further from its high without being broken).

Two universes as in Pass 48: the top 500 by size (the one that counts)
and every tradeable name.

**Control.** 200 random books a week holding the same number of names
from the same pool at the same weights, so with the same cash.

**Windows.** All (from 2008-07), to 2016, 2017 on, as before; and, named
here in advance because the Pass 50 note used it after the fact, **2010
on**, the years in which the book can hold a full set.

**Verdict lines (fixed).** *Beats luck*: mean weekly return at or above
the 95th percentile of the random books overall and the 75th in each
half. *Better ride*: Sharpe above SPY's and a largest drawdown shallower
than SPY's, overall. *Beats the S&P 500*: compound return above SPY's in
all, in both halves, and in 2010 on. The 20% rule *earns its place* if
"line or 20%" against "line" raises Sharpe by 0.05 or more without
lowering the compound return by more than half a point a year, in both
halves.

**Limits.** The list holds only names alive today, which hides the worst
breakdowns and so understates what a selling rule saves. Cash earns
nothing, and in 2008-09 a part-empty book is flattered against SPY by
its cash, which is why the random books carry the same cash.

**Predictions.** (1) "Line or 20%" has a shallower largest drawdown than
"line" and a higher Sharpe; I expect it to earn its place overall and am
unsure of the second half. (2) Its compound return is within half a
point of "line" either way. (3) "20% off the high" alone is the worst of
the four on return: with no line it holds slow decliners too long. (4)
The swing-scaled version does about as well as the flat 20%, not
clearly better. (5) No arm beats luck in both halves, and none beats the
S&P 500 on every window; the best is within two points a year of SPY in
2010 on.

    python lab/pass51_cash_and_twenty.py          # full run
    python lab/pass51_cash_and_twenty.py smoke    # plumbing: 300 names
