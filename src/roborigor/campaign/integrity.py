"""Integrity checks over a campaign's records.

Duplicates are resolved deterministically (keep earliest started_at, ties
broken by worker_id) and always reported, never silently dropped. A box
whose success rate is an extreme outlier against its siblings on shared
work gets flagged: that is how a silent llvmpipe box or a wrong-checkpoint
box shows up in the data.

Python 3.8 compatible.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from roborigor.core.schema import EpisodeRecord, cell_key
from roborigor.rollout.worklist import WorkItem


def check(
    records: Sequence[EpisodeRecord],
    items: Sequence[WorkItem] | None = None,
) -> dict:
    by_key: dict[tuple, list[EpisodeRecord]] = defaultdict(list)
    for r in records:
        by_key[cell_key(r)].append(r)

    duplicates = {k: v for k, v in by_key.items() if len(v) > 1}
    keep = {}
    for k, recs in by_key.items():
        keep[k] = sorted(recs, key=lambda r: (r.started_at, r.worker_id))[0]

    report = {
        "n_records": len(records),
        "n_cells": len(by_key),
        "n_duplicate_cells": len(duplicates),
        "duplicate_keys": sorted(duplicates)[:20],
    }
    if items is not None:
        planned = {i.key() for i in items}
        observed = set(by_key)
        report["n_planned"] = len(planned)
        report["n_missing"] = len(planned - observed)
        report["missing_keys"] = sorted(planned - observed)[:20]
        report["n_unplanned"] = len(observed - planned)
        report["unplanned_keys"] = sorted(
            observed - planned, key=repr
        )[:20]
    report["ok"] = report["n_duplicate_cells"] == 0 and (
        items is None or (report["n_missing"] == 0 and report["n_unplanned"] == 0)
    )
    report["_resolved"] = keep  # deduplicated records for downstream analysis
    return report


def box_outliers(records: Sequence[EpisodeRecord], z_threshold: float = 5.0) -> dict:
    """Flag boxes whose success rate is a z_threshold-sigma outlier vs the rest."""
    by_box: dict[str, list[bool]] = defaultdict(list)
    for r in records:
        by_box[r.box_id].append(bool(r.success))
    flagged = {}
    for box, outcomes in by_box.items():
        others = [o for b, v in by_box.items() if b != box for o in v]
        if len(outcomes) < 20 or len(others) < 20:
            continue
        p = sum(others) / len(others)
        se = (p * (1 - p) / len(outcomes)) ** 0.5
        if se == 0:
            continue
        z = (sum(outcomes) / len(outcomes) - p) / se
        if abs(z) >= z_threshold:
            flagged[box] = round(z, 2)
    return {"flagged_boxes": flagged, "n_boxes": len(by_box)}
