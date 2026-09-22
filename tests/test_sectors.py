"""get_sector's fallback for names outside SECTOR_MAP (2026-09-22).

The engines' map covers STOCK_UNIVERSE and nothing else; 46 of the 111
Council names resolved to "Unknown", which on any widened universe becomes
one 46-name bucket that can win Ophelia's rotation and trip sanity check 4.
The fallback folds the Council CSV's GICS label onto the eight engine
buckets. These pin: no Unknown on the Council list, a no-op on the live
universe, every CSV label has a fold, and the fold agrees with SECTOR_MAP
wherever both cover a name.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scan_pipeline.config.tickers import (  # noqa: E402
    BACKFILL_44_TICKERS, COUNCIL_SECTORS, COUNCIL_WATCHLIST, STOCK_UNIVERSE)
from scan_pipeline.utils.data_utils import GICS_FOLD, SECTOR_MAP, get_sector  # noqa: E402

ENGINE_BUCKETS = {"Consumer", "Energy", "Financials", "Healthcare", "Industrials",
                  "Real Estate", "Technology", "Utilities"}


def test_every_council_name_resolves_to_a_bucket():
    bad = {t: get_sector(t) for t in COUNCIL_WATCHLIST
           if get_sector(t) not in ENGINE_BUCKETS | {"Macro Assets"}}
    assert not bad, f"Council names without an engine bucket: {bad}"


def test_the_backfill_44_are_no_longer_unknown():
    unknown = [t for t in BACKFILL_44_TICKERS if get_sector(t) == "Unknown"]
    assert not unknown, unknown


def test_fallback_is_a_no_op_on_the_live_universe():
    assert all(get_sector(t) == SECTOR_MAP[t] for t in STOCK_UNIVERSE)


def test_every_csv_label_has_a_fold():
    missing = sorted(set(COUNCIL_SECTORS.values()) - set(GICS_FOLD))
    assert not missing, f"CSV sector labels without a fold entry: {missing}"


def test_fold_agrees_with_sector_map_where_both_cover_a_name():
    disagree = {t: (SECTOR_MAP[t], GICS_FOLD[COUNCIL_SECTORS[t]])
                for t in COUNCIL_SECTORS if t in SECTOR_MAP and SECTOR_MAP[t] != GICS_FOLD[COUNCIL_SECTORS[t]]}
    assert not disagree, disagree


def test_a_stranger_is_still_unknown():
    assert get_sector("NOT-A-TICKER") == "Unknown"
