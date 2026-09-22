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
