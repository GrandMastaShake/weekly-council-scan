# Council v2 -- three jobs, one universe

Decided with the owner on 2026-09-21. Nothing here is live yet: each new job goes
through the Testing Room first, and the switch happens once all three are ready.

## Why

The three engines were doing the same thing with small changes. All three
rewarded calm stocks and recent strength (Pass 2 diagnostics), so the Council's
"debate" was three versions of one view. Three passes of the Testing Room found
no input among them that predicts next week. v2 gives each member one job the
others don't do, on one universe the owner chose.

## Universe

The owner's watchlist, `scan_pipeline/config/council_watchlist.csv`: 111 names.
That is 10 stocks in each of 10 sectors, 9 in Real Estate, and two macro assets,
BTC (Grayscale Bitcoin Mini Trust) and GLD (SPDR Gold). Stocks carry the sector
the wikis use. Today's engine universe reaches only 65 of the 111; the other 46
are already in the price feed.

## The jobs

**Ophelia -- sector rotation, in three lean passes.** Each pass is a fresh agent
with only its own inputs, so her context stays clean.

1. *Sectors from the synthesis.* She reads the README Market Brief and picks her
   top 4 of the 10 stock sectors.
2. *Confirm.* She reviews the canary watch, the economic calendar and a light
   read of the four contending sector wikis, then confirms the four or swaps one.
3. *Names.* She gets the 40 stocks in her four sectors, plus BTC and GLD, which
   she always considers because they have no sector. She picks the 5 that look
   strongest. The five need not span the sectors: if one sector looks
   overwhelmingly attractive she may take up to 4 from it.

**Marky -- the chart: the pullback in an uptrend** (the owner's revision). He
looks for stocks near the bottom of a rising channel, with MACD turning up. The
channel is fitted to the last 26 weekly closes: a least-squares line through the
log prices, with the residuals' spread as its width. Only names whose channel
slopes up and whose 40-week average is rising qualify, and a close more than 2.5
widths below the line counts as a broken channel, not a pullback. Being below
the line is worth up to 50 points, full at 1.5 widths down. The channel's slope
is worth up to 20, full at +30% a year. Weekly MACD (12, 26, 9) is worth up to
30: 20 when the histogram rose this week, 10 when the MACD line is above zero.
He looks at nothing about sectors, valuation or how calm the tape is.
`marky.MARKY_MODE = "channel"`; production must fetch a year of prices before
it flips. The first chart job the lab tested, buying near 52-week highs
(`"52w"`, Pass 4), was replaced by this one.

**Cecil -- value, read against the synthesis.** His scoring is unchanged:
valuation, quality and balance-sheet safety, computed for the 111's stocks. He
chooses his 5 by reading `wiki/synthesis.md` alongside that value table. The
synthesis says where the week's risks and openings are; his numbers say what is
cheap and sound. He skips BTC and GLD because an ETF has no fundamentals to
value. The 46 names that are new to him need P/E and fundamentals fetched.

The inputs do not overlap. Ophelia starts from the README brief and the sector
wikis, Cecil from the full synthesis and his value table, and Marky from the
chart alone.

Each member proposes 5. The earnings blackout applies to all three.

## The book: a debate, then a synthesis, then approval

1. **Each member's five, with its reasoning.** These are the debate logs. Each
   member works alone, in its own passes and with its own inputs, so the
   disagreements are real.
2. **A synthesis agent drafts the book.** It reads the three logs and picks up
   to 5 names from their union, 5-30% each, with the book at least 80% invested
   (cash capped at 20%). A name that two members reach for different reasons is
   the strongest signal it has. It also names two alternates.
3. **The Council approves.** Each member, in a fresh pass that sees only its own
   lens and the draft, approves or objects to each name, with a reason.
4. **The synthesis agent finalizes.** A name that two of the three members
   object to is swapped for the first alternate. Every objection that didn't
   carry goes into the report as a dissent.

The earnings blackout applies throughout. The 20% cash cap is for market calls:
an ENGINE ABORT on broken data still holds the whole book in cash.

## Before it goes live

| Piece | Where it is tested | Status |
|---|---|---|
| Marky v2 | Engine Lab, Pass 4: 96 pre-Council weeks on the frozen universe, plus the Council's weeks on the 111 | registered |
| Cecil v2 | Council Room: one pass for each Council week, `synthesis.md` plus his value table. Fundamentals have no point-in-time history, so the table is rebuilt from what can be dated: P/E from the reported EPS of the four quarters before that Monday, and safety from prices. Quality stays out rather than being filled with today's numbers | to build |
| Ophelia v2 | Council Room: three passes for each Council week, fresh agents confined to that Monday's snapshot | to build |
| Marky v3, the pullback | Engine Lab, Pass 5: same samples as Pass 4, against classic and 52w | registered |
| The debate: synthesis, approval, final | Council Room, once the members' fives are in: one synthesis agent and three approvers for each week | to build |

Everything lands on the forward record once it is live.

## Caveat on the universe

The 111 was drawn up in 2026, and it holds names that ran (RGTI, SOUN, RKLB,
OKLO, PLTR, HIMS). Any replay on it before the list existed flatters designs
that chase strength. Judge a mechanism on the frozen universe's history, and on
the 111 compare only against random picks from the same 111.
