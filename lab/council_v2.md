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

**Marky -- the chart.** He answers one question: is the stock in a confirmed
uptrend near its highs? From the last 52 weekly closes he scores three things.
Where it sits in its 52-week range is worth 40 points. How close it is to the
52-week high is worth 30. Closing above its 40-week average earns 20, and 10
more if that average is rising. He looks at nothing about sectors, valuation or
how calm the tape is. `marky.MARKY_MODE = "52w"`; production must fetch a year
of prices before it flips.

**Cecil -- value.** His scoring is unchanged: valuation, quality and
balance-sheet safety. He moves to the 111's stocks. He skips BTC and GLD
because an ETF has no fundamentals to value. The 46 names that are new to him
need P/E and fundamentals fetched.

Each member proposes 5. The earnings blackout applies to all three.

## The book

The book is drawn from the union of the three fives, up to 15 names. A name that
two members reach for different reasons is the strongest signal on the page. The
Council's debate books from the union under the existing rules: 5-30% per name,
the earnings blackout, and cash allowed.

## Before it goes live

| Piece | Where it is tested | Status |
|---|---|---|
| Marky v2 | Engine Lab, Pass 4: 96 pre-Council weeks on the frozen universe, plus the Council's weeks on the 111 | registered |
| Cecil on the 111 | No lab test is possible (no point-in-time P/E) and his scoring does not change, so he switches when the universe switches | -- |
| Ophelia v2 | Council Room: three passes for each Council week, fresh agents confined to that Monday's snapshot | to build |
| The union book | Council Room, once all three members exist | to build |

Everything lands on the forward record once it is live.

## Caveat on the universe

The 111 was drawn up in 2026, and it holds names that ran (RGTI, SOUN, RKLB,
OKLO, PLTR, HIMS). Any replay on it before the list existed flatters designs
that chase strength. Judge a mechanism on the frozen universe's history, and on
the 111 compare only against random picks from the same 111.
