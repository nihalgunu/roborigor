"""Replay a baseline record set through the stats core.

Produces the Stage-1 gate review numbers: CP vs Wilson intervals per suite,
the MDE table, required-n reference points, and per-task rates for
variance-decomposition task selection.

Usage: python scripts/replay_baseline_stats.py <records_dir>
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from roborigor.core.schema import read_records
from roborigor.stats.intervals import clopper_pearson, wilson
from roborigor.stats.power import mde_unpaired, required_n_unpaired


def main() -> int:
    base = Path(sys.argv[1])
    records = [r for f in sorted(base.glob("records_*.jsonl")) for r in read_records(str(f))]
    if not records:
        print(f"no records under {base}", file=sys.stderr)
        return 1

    by_suite = defaultdict(list)
    for r in records:
        by_suite[r.suite].append(r)

    print(f"== intervals ({len(records)} episodes) ==")
    for suite, recs in sorted(by_suite.items()):
        k, n = sum(r.success for r in recs), len(recs)
        cp = clopper_pearson(k, n)
        wi = wilson(k, n)
        print(
            f"{suite:16s} {k}/{n} = {k / n:.3f}  "
            f"CP [{cp[0]:.4f},{cp[1]:.4f}]  Wilson [{wi[0]:.4f},{wi[1]:.4f}]"
        )

    print("\n== MDE at base rate 0.95 ==")
    for n in (50, 100, 500, 1500):
        print(f"n={n:5d}: {mde_unpaired(n, 0.95) * 100:.1f} points")

    print("\n== required n per arm (80% power) ==")
    for p1, p2 in [(0.95, 0.85), (0.95, 0.90), (0.95, 0.92), (0.20, 0.10)]:
        print(f"{p1:.2f} vs {p2:.2f}: {required_n_unpaired(p1, p2)}")

    print("\n== per-task rates (variance-decomposition selection: p in [0.5, 0.95]) ==")
    for suite, recs in sorted(by_suite.items()):
        per_task = defaultdict(lambda: [0, 0])
        for r in recs:
            per_task[r.task_id][0] += r.success
            per_task[r.task_id][1] += 1
        mid = [t for t, (k, n) in sorted(per_task.items()) if 0.5 <= k / n <= 0.95]
        rates = {t: round(k / n, 2) for t, (k, n) in sorted(per_task.items())}
        print(f"{suite}: {rates}  mid-rate: {mid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
