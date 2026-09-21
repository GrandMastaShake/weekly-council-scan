#!/usr/bin/env python3
"""Council Room -- the research-reading layer, tested on the Council's own weeks.

V1 (brief-first): one fresh agent per week reads ONLY that week's snapshot --
the repo as it stood just before the real Council's report commit that
Monday -- starting from the brief and going deeper only if it wants to, and
books up to five names from the universe. The agent never sees prices or
news from the week it is picking for; its model's training ends months
before the first Council week, so it cannot remember how the week went.

Books are scored on the Engine Lab's basis (Monday open -> Friday close,
dividend-adjusted, cash = 0) against random picks at the same weights, the
engine replay (Pass 2 baseline) and the real Council.

    python lab/council_room.py snapshot DIR   # one folder per week, for the agents
    python lab/council_room.py score DIR      # score the book.json each agent wrote
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

ROOT = lab.ROOT
MAX_POSITIONS = 5
MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.30          # ENGINE_CONFIG["max_position_size"]
BRIEF_FILES = ["README.md", "scoreboard.md"]
BRIEF_DIRS = ["wiki", "journals"]


def _git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                           capture_output=True).stdout


def snapshot_commit(label):
    """Parent of the commit that first added that week's Council report."""
    added = _git("log", "--diff-filter=A", "--format=%H", "--",
                 f"reports/{label}-report.md").decode().split()
    if not added:
        raise SystemExit(f"no report commit for {label}")
    return _git("rev-parse", added[-1] + "^").decode().strip()


def _weeks_and_data():
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
    last_friday = date.today() - timedelta(days=(date.today().weekday() - 4) % 7 or 7)
    weeks = lab.council_weeks(last_friday.strftime("%Y-%m-%d"))
    universe = sorted(set(STOCK_UNIVERSE))
    council_names = sorted({t for _, _, b in weeks if b for t, _ in b})
    tickers = sorted(set(universe + council_names)) + lab.EXTRA
    end = lab._plus(last_friday.strftime("%Y-%m-%d"), 1)
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end)).items()}
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end)).items()}
    return weeks, universe, raw, adj


def _eligible(universe, raw, W):
    from scan_pipeline.fetch_market_data import _aggregate_weekly
    out = {}
    for t in universe:
        s = raw.get(t)
        if s:
            hist = _aggregate_weekly(s.before(W, lab.LOOKBACK_DAYS))
            if len(hist) >= lab.MIN_WEEKS:
                out[t] = hist
    return out


def _price_rows(universe, raw, adj, W):
    """Point-in-time table: everything ends at the last close before W."""
    from scan_pipeline.fetch_market_data import _aggregate_weekly
    from scan_pipeline.utils.data_utils import get_sector
    rows = []
    for t, hist_raw in sorted(_eligible(universe, raw, W).items()):
        hist = _aggregate_weekly(adj[t].before(W, lab.LOOKBACK_DAYS)) if t in adj else []
        if len(hist) < lab.MIN_WEEKS:
            continue
        closes = [h.close for h in hist]

        def back(n):
            return closes[-1] / closes[-1 - n] - 1 if len(closes) > n else None
        wk = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))][-12:]
        vol = statistics.pstdev(wk) if len(wk) >= 2 else None
        dollar = [h.close * h.volume for h in hist_raw[-4:] if h.volume]
        rows.append({
            "ticker": t, "sector": get_sector(t), "close": round(hist_raw[-1].close, 2),
            "ret_1w_pct": None if back(1) is None else round(back(1) * 100, 2),
            "ret_4w_pct": None if back(4) is None else round(back(4) * 100, 2),
            "ret_12w_pct": None if back(12) is None else round(back(12) * 100, 2),
            "weekly_vol_pct": None if vol is None else round(vol * 100, 2),
            "avg_daily_dollar_vol_musd": round(statistics.fmean(dollar) / 1e6, 1) if dollar else None,
        })
    return rows


def snapshot(out_dir):
    weeks, universe, raw, adj = _weeks_and_data()
    out_dir = Path(out_dir)
    manifest = []
    for label, W, _ in weeks:
        commit = snapshot_commit(label)
        d = out_dir / label
        d.mkdir(parents=True, exist_ok=True)
        names = _git("ls-tree", "-r", "--name-only", commit, "--", *BRIEF_DIRS).decode().split()
        names += [f for f in BRIEF_FILES
                  if _git("ls-tree", "--name-only", commit, "--", f).decode().strip()]
        reports = sorted(n for n in _git("ls-tree", "-r", "--name-only", commit, "--", "reports")
                         .decode().split() if n.endswith("-report.md") and n[8:18] < label)
        written = []
        for name in names + reports[-1:]:
            target = d / ("last-week-report.md" if name.startswith("reports/") else name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(_git("show", f"{commit}:{name}").decode("utf-8", "replace").replace("\r\n", "\n"))
            written.append(str(target.relative_to(d)).replace("\\", "/"))
        rows = _price_rows(universe, raw, adj, W)
        with open(d / "prices.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        friday = raw["SPY"].rows[lab.bisect.bisect_left(raw["SPY"].dates, W) - 1]["date"]
        manifest.append({"label": label, "monday": W, "last_close": friday, "commit": commit,
                         "commit_time": _git("log", "-1", "--format=%ad",
                                             "--date=format-local:%Y-%m-%d %H:%M", commit).decode().strip(),
                         "files": sorted(written) + ["prices.csv"], "universe": len(rows)})
        print(f"  {label}  snapshot {commit[:7]} ({manifest[-1]['commit_time']})  "
              f"{len(written)} files + prices.csv ({len(rows)} names, last close {friday})")
    with open(out_dir / "manifest.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")


def _validate(book, eligible):
    """Enforce the room's rules; anything outside them is dropped to cash."""
    problems, kept = [], []
    for p in (book.get("positions") or [])[:MAX_POSITIONS]:
        t, w = str(p.get("ticker", "")).upper(), float(p.get("weight", 0) or 0)
        if t not in eligible:
            problems.append(f"{t} not in the universe -> cash")
        elif not (MIN_WEIGHT - 1e-9 <= w <= MAX_WEIGHT + 1e-9):
            problems.append(f"{t} weight {w:.2f} outside {MIN_WEIGHT}-{MAX_WEIGHT} -> clipped")
            kept.append((t, min(max(w, MIN_WEIGHT), MAX_WEIGHT)))
        else:
            kept.append((t, w))
    if len(book.get("positions") or []) > MAX_POSITIONS:
        problems.append("more than five positions -> first five kept")
    total = sum(w for _, w in kept)
    if total > 1.0 + 1e-6:
        kept = [(t, w / total) for t, w in kept]
        problems.append(f"invested {total:.2f} > 1 -> scaled to 1")
    return kept, problems


def score(in_dir, variant="V1"):
    weeks, universe, raw, adj = _weeks_and_data()
    in_dir = Path(in_dir)
    base = {}
    p2 = lab.RESULTS / "pass2_variants.json"
    if p2.exists():
        with open(p2, encoding="utf-8") as fh:
            base = {r["week"]: r["book_ret"] for r in json.load(fh)["books"]["baseline"]}
    rows = []
    for label, W, council_book in weeks:
        f = in_dir / label / "book.json"
        if not f.exists():
            print(f"  {label}  no book.json -- skipped")
            continue
        with open(f, encoding="utf-8") as fh:
            book = json.load(fh)
        eligible = sorted(_eligible(universe, raw, W))

        def ret(t):
            s = adj.get(t)
            r = s.week_return(W) if s else None
            return 0.0 if r is None else r
        kept, problems = _validate(book, set(eligible))
        book_ret = sum(w * ret(t) for t, w in kept)
        spy = adj["SPY"].week_return(W) or 0.0
        weights = sorted((w for _, w in kept), reverse=True)
        rng = random.Random(f"{lab.SEED}-{W}-room")
        draws = ([sum(w * ret(t) for t, w in zip(rng.sample(eligible, len(weights)), weights))
                  for _ in range(lab.RANDOM_DRAWS)] if weights else [0.0])
        council_ret = sum(w * ret(t) for t, w in council_book) if council_book else 0.0
        rows.append({
            "week": label, "book": [{"ticker": t, "weight": round(w, 4), "ret": round(ret(t), 6)}
                                    for t, w in kept],
            "invested": sum(weights), "problems": problems,
            "book_ret": book_ret, "spy_ret": spy, "alpha": book_ret - spy,
            "rand_mean": statistics.fmean(draws), "vs_random": book_ret - statistics.fmean(draws),
            "pctile_vs_random": sum(1 for x in draws if x < book_ret) / len(draws),
            "council_ret": council_ret, "replay_ret": base.get(label),
        })
        r = rows[-1]
        replay = "--" if r["replay_ret"] is None else f"{r['replay_ret'] * 100:+6.2f}%"
        held = ", ".join(f"{t} {w:.0%}" for t, w in kept) or "ALL CASH"
        print(f"  {label}  {variant} {book_ret*100:+6.2f}% (a {r['alpha']*100:+5.2f}, inv {r['invested']:4.0%}, "
              f"pctile {r['pctile_vs_random']:4.0%})  council {council_ret*100:+6.2f}%  replay {replay}  "
              f"SPY {spy*100:+5.2f}%  {held}" + (f"  [{'; '.join(problems)}]" if problems else ""))
    if not rows:
        return None
    n = len(rows)
    al = [r["alpha"] for r in rows]
    vr = [r["vs_random"] for r in rows]
    vc = [r["book_ret"] - r["council_ret"] for r in rows]
    vp = [r["book_ret"] - r["replay_ret"] for r in rows if r["replay_ret"] is not None]
    cum, dd = lab._curve([r["book_ret"] for r in rows])
    summary = {
        "weeks": n, "mean_alpha": statistics.fmean(al), "alpha_t": lab._tstat(al),
        "weeks_beating_spy": sum(1 for x in al if x > 0),
        "mean_vs_random": statistics.fmean(vr), "vs_random_t": lab._tstat(vr),
        "mean_pctile_vs_random": statistics.fmean(r["pctile_vs_random"] for r in rows),
        "mean_vs_council": statistics.fmean(vc), "weeks_beating_council": sum(1 for x in vc if x > 0),
        "mean_vs_replay": statistics.fmean(vp) if vp else None,
        "weeks_beating_replay": sum(1 for x in vp if x > 0),
        "mean_invested": statistics.fmean(r["invested"] for r in rows),
        "cumulative": cum, "max_drawdown": dd,
    }
    s = summary
    print(f"\n  {variant}: mean alpha {s['mean_alpha']*100:+.2f}%/wk (t {s['alpha_t']:+.2f}), beat SPY "
          f"{s['weeks_beating_spy']}/{n}; vs random {s['mean_vs_random']*100:+.2f}%/wk (t {s['vs_random_t']:+.2f}, "
          f"avg pctile {s['mean_pctile_vs_random']:.0%}); vs real Council {s['mean_vs_council']*100:+.2f}%/wk "
          f"({s['weeks_beating_council']}/{n}); vs engine replay "
          f"{(s['mean_vs_replay'] or 0)*100:+.2f}%/wk ({s['weeks_beating_replay']}/{len(vp)}); invested "
          f"{s['mean_invested']:.0%}; cumulative {cum*100:+.1f}%, max DD {dd*100:.1f}%")
    lab.RESULTS.mkdir(parents=True, exist_ok=True)
    with open(lab.RESULTS / f"room_{variant.lower()}.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"variant": variant, "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "summary": summary, "weeks": rows}, fh, indent=1, default=float)
        fh.write("\n")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("snapshot", "score"))
    ap.add_argument("dir")
    ap.add_argument("--variant", default="V1")
    a = ap.parse_args(argv)
    if a.command == "snapshot":
        snapshot(a.dir)
    else:
        score(a.dir, a.variant)


if __name__ == "__main__":
    main()
