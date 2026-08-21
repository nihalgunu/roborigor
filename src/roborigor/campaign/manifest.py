"""Shard a worklist across boxes, deterministically.

Assignment hashes (policy_id, suite, task_id) so one task's episodes stay
together (paired arms land on the same box) and re-running build_manifest
with the same inputs yields byte-identical assignments. Python's builtin
hash() is salted per process, so crc32 is used instead.

Python 3.8 compatible.
"""

from __future__ import annotations

import dataclasses
import json
import zlib
from pathlib import Path

from roborigor.rollout.worklist import WorkItem

MANIFEST_VERSION = 1


@dataclasses.dataclass
class Manifest:
    campaign: str
    config: dict  # echo of the CampaignConfig
    items: list[WorkItem]
    assignments: dict[str, list[int]]  # box_id -> indices into items
    manifest_version: int = MANIFEST_VERSION

    def items_for_box(self, box_id: str) -> list[WorkItem]:
        return [self.items[i] for i in self.assignments[box_id]]


def _shard_hash(item: WorkItem) -> int:
    key = f"{item.policy_id}|{item.suite}|{item.task_id}".encode()
    return zlib.crc32(key)


def build_manifest(
    campaign: str, config: dict, items: list[WorkItem], n_boxes: int
) -> Manifest:
    if n_boxes < 1:
        raise ValueError("n_boxes must be >= 1")
    boxes = [f"box{i}" for i in range(n_boxes)]
    assignments: dict[str, list[int]] = {b: [] for b in boxes}
    for idx, item in enumerate(items):
        assignments[boxes[_shard_hash(item) % n_boxes]].append(idx)
    return Manifest(campaign=campaign, config=config, items=items, assignments=assignments)


def save_manifest(manifest: Manifest, path: str) -> None:
    payload = {
        "manifest_version": manifest.manifest_version,
        "campaign": manifest.campaign,
        "config": manifest.config,
        "items": [dataclasses.asdict(i) for i in manifest.items],
        "assignments": manifest.assignments,
    }
    Path(path).write_text(json.dumps(payload, indent=1, sort_keys=True))


def load_manifest(path: str) -> Manifest:
    raw = json.loads(Path(path).read_text())
    if raw["manifest_version"] != MANIFEST_VERSION:
        raise ValueError(
            f"manifest version {raw['manifest_version']} != {MANIFEST_VERSION}"
        )
    return Manifest(
        campaign=raw["campaign"],
        config=raw["config"],
        items=[WorkItem(**i) for i in raw["items"]],
        assignments={b: list(v) for b, v in raw["assignments"].items()},
    )
