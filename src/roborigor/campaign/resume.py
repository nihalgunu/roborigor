"""Episode-granular resume from the JSONL records themselves.

No separate progress state: an episode is done iff its cell key appears in
the records. Torn final lines are skipped by the tolerant reader, so a
killed worker's in-flight episode simply reruns.

Python 3.8 compatible.
"""

from __future__ import annotations

from typing import Iterable

from roborigor.core.schema import cell_key, read_records
from roborigor.rollout.worklist import WorkItem


def completed_keys(record_paths: Iterable[str]) -> set[tuple]:
    done: set[tuple] = set()
    for path in record_paths:
        for rec in read_records(str(path)):
            done.add(cell_key(rec))
    return done


def remaining(items: list[WorkItem], done: set[tuple]) -> list[WorkItem]:
    return [i for i in items if i.key() not in done]
