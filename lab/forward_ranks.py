#!/usr/bin/env python3
"""Pass 34 B -- each desk's ranked ten, with probabilities, scored forward.

lab/ranks/<MONDAY>.json is written by the Monday Council session before the
open: for each desk ten distinct names in rank order, each with p, the desk's
probability (whole percent, 1-99) that the name beats SPY from Monday's open
to Friday's close. This script validates a file (`check`) and, each Monday,
scores every closed week: rank IC, Brier score and skill, calibration, ranks
1-5 against 6-10, engine names against the desk's additions. A file committed
at or after 09:30 ET on its Monday, or edited after, is listed as late and not
scored. Rewrites lab/RANKS.md and lab/results/ranks.json.

Registered in lab/README.md (Pass 34) before the first file.

    python lab/forward_ranks.py
    python lab/forward_ranks.py check lab/ranks/2026-11-23.json
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

RANKS = lab.LAB / "ranks"
PAGE = lab.LAB / "RANKS.md"
OUT = lab.RESULTS / "ranks.json"
DESKS = ("Cecil", "Marky", "Ophelia")
ET = ZoneInfo("America/New_York")
BUCKETS = ((1, 44), (45, 54), (55, 64), (65, 99))


def validate(d, name=None):
    """Problems with a ranks file, as a list of strings (empty = valid)."""
    bad = []
    if not isinstance(d, dict):
        return ["not a JSON object"]
    wk = d.get("week")
    if not isinstance(wk, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", wk):
        bad.append("week must be YYYY-MM-DD")
    elif name and name != wk + ".json":
        bad.append(f"file name {name} does not match week {wk}")
    if not isinstance(d.get("model"), str) or not d.get("model"):
        bad.append("model (the model that wrote the file) is missing")
    desks = d.get("desks")
    if not isinstance(desks, dict) or set(desks) != set(DESKS):
        return bad + [f"desks must be exactly {', '.join(DESKS)}"]
    for desk in DESKS:
        rows = desks[desk]
        if not isinstance(rows, list) or len(rows) != 10:
            bad.append(f"{desk}: needs exactly 10 rows")
            continue
        tick, last_p = set(), 100
        for i, r in enumerate(rows, 1):
            t, p = r.get("ticker"), r.get("p")
            if r.get("rank") != i:
                bad.append(f"{desk} row {i}: rank must be {i}")
            if not isinstance(t, str) or not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,6}", t):
                bad.append(f"{desk} row {i}: bad ticker {t!r}")
            elif t in tick:
                bad.append(f"{desk} row {i}: {t} listed twice")
            tick.add(t)
            if not isinstance(p, int) or isinstance(p, bool) or not 1 <= p <= 99:
                bad.append(f"{desk} row {i}: p must be a whole number 1-99")
            else:
                if p > last_p:
                    bad.append(f"{desk} row {i}: p rises as rank falls ({last_p} -> {p})")
                last_p = p
            if not isinstance(r.get("engine"), bool):
                bad.append(f"{desk} row {i}: engine must be true or false")
        if not any(r.get("engine") is True for r in rows):
            bad.append(f"{desk}: no row is flagged engine: true")
    return bad


def commit_times(path):
    out = subprocess.run(["git", "-C", str(lab.ROOT), "log", "--format=%aI", "--", str(path.relative_to(lab.ROOT)).replace("\\", "/")],
                         capture_output=True, text=True, check=True).stdout.split()
    return [datetime.fromisoformat(x) for x in out]


def spearman(a, b):
    def rk(x):
        order = np.argsort(x)
        r = np.empty(len(x))
        i = 0
        while i < len(x):
            j = i
            while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
                j += 1
            r[order[i:j + 1]] = (i + j) / 2.0
            i = j + 1
        return r
    ra, rb = rk(np.asarray(a, float)), rk(np.asarray(b, float))
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def tstat(xs):
    xs = np.asarray([x for x in xs if x == x], float)
    if len(xs) < 3 or xs.std(ddof=1) == 0:
        return float("nan")
    return float(xs.mean() / (xs.std(ddof=1) / math.sqrt(len(xs))))


def score_file(d):
    wk = d["week"]
    day = date.fromisoformat(wk)
    mon = (day - timedelta(days=day.weekday())).isoformat()
    names = sorted({r["ticker"] for desk in DESKS for r in d["desks"][desk]} | {"SPY"})
    start = (date.fromisoformat(mon) - timedelta(days=5)).isoformat()
    end = (date.fromisoformat(mon) + timedelta(days=8)).isoformat()
    bars = {t: lab.Series(rows) for t, rows in lab.bars_by_ticker(lab.download(names, True, end, start=start)).items()}
    spy = bars["SPY"].week_return(mon) if "SPY" in bars else None
    if spy is None:
        return None
    res = {"week": wk, "model": d["model"], "spy": spy, "desks": {}}
    for desk in DESKS + ("pooled",):
        rows = [dict(r, desk=k) for k in DESKS for r in d["desks"][k]] if desk == "pooled" else d["desks"][desk]
        got, missing = [], []
        for r in rows:
            x = bars[r["ticker"]].week_return(mon) if r["ticker"] in bars else None
            (got if x is not None else missing).append(dict(r, excess=None if x is None else x - spy))
        if len(got) < 4:
            res["desks"][desk] = {"n": len(got), "missing": [m["ticker"] for m in missing]}
            continue
        ex = np.array([g["excess"] for g in got])
        p = np.array([g["p"] / 100.0 for g in got])
        y = (ex > 0).astype(float)
        brier = float(((p - y) ** 2).mean())
        top = [g["excess"] for g in got if g["rank"] <= 5]
        bot = [g["excess"] for g in got if g["rank"] > 5]
        eng = [g["excess"] for g in got if g["engine"]]
        add = [g["excess"] for g in got if not g["engine"]]
        m = lambda v: float(np.mean(v)) if v else None  # noqa: E731
        res["desks"][desk] = {
            "n": len(got), "missing": [x["ticker"] for x in missing],
            "ic": spearman([-g["rank"] for g in got] if desk != "pooled" else [g["p"] for g in got], ex),
            "brier": brier, "skill": 1.0 - brier / 0.25, "hit": float(y.mean()), "mean_p": float(p.mean()),
            "mean_excess": float(ex.mean()), "top5": m(top), "bottom5": m(bot), "engine": m(eng), "added": m(add),
            "rows": [{"ticker": g["ticker"], "rank": g["rank"], "p": g["p"], "engine": g["engine"], "excess": g["excess"]} for g in got],
        }
    return res


def page(scored, late, pending):
    P = lambda x: "--" if x is None or x != x else f"{100 * x:+.2f}%"  # noqa: E731
    F = lambda x: "--" if x is None or x != x else f"{x:+.2f}"  # noqa: E731
    out = ["# Desk ranks", "",
           "Each desk's ranked ten with a probability of beating SPY, written before Monday's open and scored after",
           "Friday's close (Pass 34 B). `lab/forward_ranks.py` regenerates this page each Monday; edits by hand are",
           "overwritten. Nothing reads the ranks but this scorer.", "",
           f"Scored weeks: {len(scored)}. Waiting on their close: {len(pending)}. Late or edited after the open (not scored): {len(late)}.", ""]
    if not scored:
        out += ["No week has been scored yet. The first file is due before the open on 2026-11-23.", ""]
    for model in sorted({s["model"] for s in scored}):
        ws = [s for s in scored if s["model"] == model]
        out += [f"## Model: {model} ({len(ws)} weeks)", "",
                "| Desk | Weeks | Mean rank IC (t) | Brier | Brier skill | Mean p | Beat SPY | Ranks 1-5 | Ranks 6-10 | 1-5 minus 6-10 (t) | Engine names | Added names |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for desk in DESKS + ("pooled",):
            ds = [s["desks"][desk] for s in ws if "ic" in s["desks"].get(desk, {})]
            if not ds:
                continue
            ic = [x["ic"] for x in ds]
            diff = [x["top5"] - x["bottom5"] for x in ds if x["top5"] is not None and x["bottom5"] is not None]
            rows = [r for x in ds for r in x["rows"]]
            brier = float(np.mean([(r["p"] / 100.0 - (r["excess"] > 0)) ** 2 for r in rows]))
            mm = lambda k: float(np.mean([x[k] for x in ds if x[k] is not None])) if any(x[k] is not None for x in ds) else None  # noqa: E731
            out.append(f"| {desk} | {len(ds)} | {F(np.nanmean(ic))} ({F(tstat(ic))}) | {brier:.3f} | {F(1 - brier / 0.25)} | "
                       f"{100 * np.mean([r['p'] for r in rows]) / 100:.0f}% | {100 * np.mean([r['excess'] > 0 for r in rows]):.0f}% | "
                       f"{P(mm('top5'))} | {P(mm('bottom5'))} | {P(np.mean(diff) if diff else None)} ({F(tstat(diff))}) | {P(mm('engine'))} | {P(mm('added'))} |")
        allrows = [r for s in ws for k in DESKS if "rows" in s["desks"].get(k, {}) for r in s["desks"][k]["rows"]]
        out += ["", "Calibration, all desks:", "", "| p | Names | Mean p | Beat SPY |", "|---|---|---|---|"]
        for lo, hi in BUCKETS:
            b = [r for r in allrows if lo <= r["p"] <= hi]
            if b:
                out.append(f"| {lo}-{hi} | {len(b)} | {np.mean([r['p'] for r in b]):.0f}% | {100 * np.mean([r['excess'] > 0 for r in b]):.0f}% |")
        out += ["", "| Week | SPY | " + " | ".join(f"{k} IC / skill / 1-5 minus 6-10" for k in DESKS) + " |", "|---|---|" + "---|" * len(DESKS)]
        for s in ws:
            cells = []
            for k in DESKS:
                x = s["desks"].get(k, {})
                cells.append("--" if "ic" not in x else f"{F(x['ic'])} / {F(x['skill'])} / {P(x['top5'] - x['bottom5'])}")
            out.append(f"| {s['week']} | {P(s['spy'])} | " + " | ".join(cells) + " |")
        out.append("")
    if late:
        out += ["## Not scored", ""] + [f"- {w}: {why}" for w, why in late] + [""]
    out += ["The registered reading waits for 40 scored weeks: a desk shows ranking skill if its mean IC has t >= 1.64 and its",
            "Brier skill is above zero; four rows are four looks, so a lone pass needs t >= 2.24. Before that this page shows",
            "direction, not proof."]
    return "\n".join(out) + "\n"


def main(argv):
    if len(argv) > 2 and argv[1] == "check":
        path = Path(argv[2])
        with open(path, encoding="utf-8") as fh:
            bad = validate(json.load(fh), path.name)
        print("VALID" if not bad else "INVALID:\n  " + "\n  ".join(bad))
        return 1 if bad else 0
    scored, late, pending = [], [], []
    for path in sorted(RANKS.glob("*.json")) if RANKS.exists() else []:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        bad = validate(d, path.name)
        if bad:
            late.append((path.stem, "invalid file: " + "; ".join(bad[:3])))
            continue
        open_at = datetime.combine(date.fromisoformat(d["week"]), datetime.min.time(), ET).replace(hour=9, minute=30)
        times = commit_times(path)
        if not times:
            late.append((d["week"], "not committed"))
            continue
        if min(times) >= open_at:
            late.append((d["week"], f"first committed {min(times).astimezone(ET):%Y-%m-%d %H:%M} ET, at or after the open"))
            continue
        if max(times) >= open_at:
            late.append((d["week"], f"edited {max(times).astimezone(ET):%Y-%m-%d %H:%M} ET, after the open"))
            continue
        fri = date.fromisoformat(d["week"]) + timedelta(days=4 - date.fromisoformat(d["week"]).weekday())
        if datetime.now(ET) < datetime.combine(fri, datetime.min.time(), ET).replace(hour=18):
            pending.append(d["week"])          # not closed: no download, so no half-week cache
            continue
        r = score_file(d)
        (scored.append(r) if r else pending.append(d["week"]))
    text = page(scored, late, pending)
    with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    lab.RESULTS.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"scored": scored, "late": late, "pending": pending}, fh, indent=1, default=float)
        fh.write("\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
