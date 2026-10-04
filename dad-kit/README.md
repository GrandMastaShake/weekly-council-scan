# Dad's Claude kit

A starter setup for Dad's Claude account: two Projects, two Skills, three
spreadsheets, and a plain-English guide. He mostly runs a golf league and
helps around the course besides, so the golf side is built around the
league's weekly cycle. Built from what the Council taught
us about numbers, records and plans, and pointed at the Council's own
weekly brief, which already has "Dad Translation" boxes in it.

This folder is not part of the scan pipeline. Nothing in the Council reads
it, and it reads nothing from the Council except the public README and wiki
files, and only when Dad asks.

## What's here

| File | What it is | Where it goes |
|---|---|---|
| `START_HERE.md` | Dad's guide: what Claude is good at, what to watch for, first things to try | Print it, or send it to him |
| `profile-preferences.txt` | Account-wide instructions (bottom line first, plain English, no invented numbers) | Settings -> Instructions for Claude |
| `projects/stocks/instructions.md` | Stocks project instructions | Stocks project -> instructions |
| `projects/stocks/my-investing-profile.md` | His goals, limits and style, to fill in with him | Stocks project -> files |
| `projects/golf-course/instructions.md` | Golf project instructions | Golf project -> instructions |
| `projects/golf-course/about-the-league.md` | The league's rule book: format, points, handicaps, absences, rain, money. Claude computes from it and asks instead of guessing | Golf project -> files |
| `projects/golf-course/about-the-course.md` | The course, his role, who's who, other events, to fill in with him | Golf project -> files |
| `skills/stock-research/` | Stock briefs, earnings checks, trade plans, portfolio check-ups, market read, weekly review, and the Council's lessons | Uploaded as `dist/stock-research.zip` |
| `skills/golf-course-ops/` | The league (pairings, scorecard photos, standings, handicaps, subs, skins, the weekly email, season schedule), plus task lists, schedules, events, maintenance, notices, budgets | Uploaded as `dist/golf-course-ops.zip` |
| `build_kit.py` | Builds the two skill zips and the three workbooks into `dist/` | Run it on your machine |

## Build

    pip install openpyxl
    python dad-kit/build_kit.py

That writes to `dad-kit/dist/` (not committed; it is all derived):

- `stock-research.zip`, `golf-course-ops.zip`
- `Investing Journal.xlsx` -- Holdings (with formulas for value, gain and
  weight), Trade Plans, Watchlist, Limit Orders, Weekly Review
- `League Manager.xlsx` -- Roster, Schedule, Weekly Scores (net filled in),
  Standings and Team Standings (add themselves up from Weekly Scores),
  Subs (counts their rounds), Money (running balance)
- `Golf Course Organizer.xlsx` -- Tasks, Schedule, Events, Sponsors,
  Maintenance Log, Equipment, Inventory, Contacts

The zips build without openpyxl; only the workbooks need it. The script
checks each skill against claude.ai's upload rules first and refuses to
build if one would be rejected. `tests/test_dad_kit.py` runs the same checks
in CI, plus ASCII on every kit file.

## Set it up with him (about 30 minutes)

Do this sitting next to him, on his account. Menus move around; if one is
not where this says, ask Claude "where do I find [setting]?"

1. **Instructions for Claude.** Click his initials (bottom left) ->
   Settings -> "Instructions for Claude". Paste `profile-preferences.txt`
   and fix the [Windows PC / Mac / iPhone / Android] bracket.
2. **Capabilities.** Settings -> Capabilities: make sure "Code execution
   and file creation" is on (the skills and spreadsheets need it). Memory and
   web search are on by default on every plan, Free included; check nobody
   turned them off.
3. **Skills.** Customize -> Skills -> "+" -> Create skill -> Upload a
   skill. Upload `stock-research.zip`, then `golf-course-ops.zip`. Make sure
   both show as enabled.
4. **Stocks project.** Projects -> New project, name it "Stocks". Paste
   `projects/stocks/instructions.md` into the project instructions. Fill in
   `my-investing-profile.md` with him (his limits matter most: max loss per
   idea, max position size, cash target) and add it to the project files.
5. **Golf project.** New project "Golf". Paste
   `projects/golf-course/instructions.md`. Fill in `about-the-league.md`
   with him first; it is the file he will lean on every week. Gaps are
   fine: the first thing to try in START_HERE is asking Claude what is
   missing or unclear in it. Then `about-the-course.md`, and add both.
6. **Spreadsheets.** Put the three workbooks somewhere he can find them
   (Documents, or his Google Drive / OneDrive). They are not project files:
   project files are read-only to Claude. He attaches the current copy to a
   chat when he wants it updated and saves the copy Claude hands back.
7. **Phone.** Install the Claude app on his phone and sign in. Show him the
   microphone button and how to attach a photo.
8. **Optional connectors.** If the course runs on Google (Drive, Gmail,
   Calendar) or he keeps his records there, Settings -> Connectors lets
   Claude read them. Leave this for week two.
9. **First run.** In the Golf project, start with "Read my league rules and
   tell me what's missing or unclear", and add his answers to
   `about-the-league.md`. Then one stock prompt from `START_HERE.md`.

## Free first, then Pro

He is starting on Free. Everything in this kit works there: projects (Free
allows five; this uses two), skills, file creation and code, web search,
memory and connectors. What Free limits is volume: usage refills on a
rolling five-hour window, and making files or reading a stack of scorecard
photos uses more of it than a plain question. START_HERE tells him how to
stretch it (a new chat per job, attach only what the job needs).

Pro ($20 a month in the US) adds more usage per window, priority at busy
times, more room for project files, and Claude Code. Same account, same
projects and skills; nothing here needs redoing when he upgrades. The test
that tells you it is time: he hits the limit entering scores on league
night.

## Updating

Edit the files here, run `build_kit.py`, and re-upload the changed skill on
his account (remove the old version in Customize -> Skills first). Project
instructions and files are edited in the project itself; keep the copies
here in step so the next rebuild does not undo a fix.

If the upload complains about the file name, rename `SKILL.md` to
`skill.md` in the zip. claude.ai's help page spells it lowercase; the
Agent Skills standard and Anthropic's own examples use `SKILL.md`, which is
what claude.ai has accepted so far.

## What it deliberately does not do

- No brokerage logins, account numbers or trading. Claude helps him decide;
  he places the order.
- No chemical rates for the course. The product label is the law, and the
  skill says so.
- No copy of the Council's data. The stock skill reads the public README
  and wiki when he asks, and says how old they are.
