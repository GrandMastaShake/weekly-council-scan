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

## Rooms

- **Engine Lab** -- `engine_lab.py`. The numeric engines, replayed as pure code.
- **Council Room** -- `council_room.py`. The LLM layer: one fresh agent per week,
  fed only the repo as it stood before that Monday's Council report.
- **Forward record** -- `forward.py` and [FORWARD.md](FORWARD.md). Every
  registered design, scored each Monday on weeks it never saw.

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
