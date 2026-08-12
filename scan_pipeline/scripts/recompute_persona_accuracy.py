#!/usr/bin/env python3
"""One-time correction: recompute persona picksAccuracy from realized history.

Backs up state/personas.json to personas.json.bak-20260811, then recomputes
each persona's picksAccuracy using ONLY closed StockApp/portfolio/history
YAMLs.

Formula (hit-rate-based EMA replay):
  - Start from the neutral prior picksAccuracy = 0.5.
  - For each closed week (chronological), a persona's week accuracy is its
    realized hit rate: positions with pnl_pct > 0 / booked positions.
  - Weeks where the persona booked zero positions are skipped (shutout rule).
  - EMA: acc = acc * (1 - alpha) + week_hit_rate * alpha, alpha = 0.3
    (same alpha as the runtime updater in engines/personality.py).
  - stats.last_scored_week is set to the newest closed week so the runtime
    idempotency guard never re-applies these weeks.

Run from anywhere:
    python scan_pipeline/scripts/recompute_persona_accuracy.py
"""

import json
import os
import shutil
import sys

# MarketStockPicker root on path for the scan_pipeline package import.
_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scan_pipeline.engines.personality import (  # noqa: E402
    ACCURACY_EMA_ALPHA,
    DEFAULT_HISTORY_DIR,
    load_closed_weeks,
)

STATE_PATH = os.path.join(_ROOT, "scan_pipeline", "state", "personas.json")
BACKUP_PATH = STATE_PATH + ".bak-20260811"
PRIOR = 0.5
PERSONA_NAMES = ["Cecil", "Marky", "Ophelia"]


def main() -> None:
    weeks = load_closed_weeks(DEFAULT_HISTORY_DIR)
    closed_dates = sorted(weeks)
    if not closed_dates:
        print("No closed history weeks found; nothing to recompute.")
        return
    newest_closed = closed_dates[-1]
    print(f"Closed weeks found: {', '.join(closed_dates)}")
    print(f"History dir: {DEFAULT_HISTORY_DIR}")

    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)

    # Back up before touching state. Never overwrite an existing backup.
    if os.path.exists(BACKUP_PATH):
        print(f"Backup already exists, keeping it: {BACKUP_PATH}")
    else:
        shutil.copy2(STATE_PATH, BACKUP_PATH)
        print(f"Backup written: {BACKUP_PATH}")

    personas = state.get("personas", {})
    print(f"\nFormula: prior={PRIOR}, alpha={ACCURACY_EMA_ALPHA}, "
          "week accuracy = realized hit rate, shutout weeks skipped\n")

    for name in PERSONA_NAMES:
        persona = personas.get(name)
        if not persona:
            print(f"{name}: NOT FOUND in personas.json, skipped")
            continue
        stats = persona.setdefault("stats", {})
        before = stats.get("picksAccuracy")

        acc = PRIOR
        applied = []
        for week_date in closed_dates:
            entry = weeks[week_date].get(name)
            if not entry or entry["total"] == 0:
                continue  # shutout: zero booked positions, no update
            week_hit_rate = entry["hits"] / entry["total"]
            acc = acc * (1 - ACCURACY_EMA_ALPHA) + week_hit_rate * ACCURACY_EMA_ALPHA
            applied.append(f"{week_date}:{week_hit_rate:.2f}")

        stats["picksAccuracy"] = acc
        stats["last_scored_week"] = newest_closed
        print(f"{name}: picksAccuracy {before} -> {acc:.4f} "
              f"(weeks applied: {', '.join(applied) or 'none'}; "
              f"last_scored_week={newest_closed})")

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"\nCorrected state written: {STATE_PATH}")


if __name__ == "__main__":
    main()
