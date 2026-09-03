"""Exploratory robustness checks on the (1,10) vs (10,5) equivalence verdict.

Reports (a) an init-cluster bootstrap of the *paired* difference, since the
registered interval is Newcombe's unpaired one, and (b) the same comparison
restricted to tasks that still have headroom at the reference condition.
Both are logged as Entry 13 of the deviations log.

Writes docs/paper-data/restricted_factorial.json.
"""

import json
import random
from collections import defaultdict
from pathlib import Path

from roborigor.core.schema import read_records
from roborigor.stats.compare import PairedCounts, mcnemar_exact
from roborigor.stats.intervals import clopper_pearson, newcombe_diff

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CELL = (10, 5)
FRONTIER_CELL = (1, 10)
STEPS = [1, 2, 5, 10]
HORIZONS = [1, 5, 10]
N_BOOT = 4000


def load_grid():
    """Map (num_steps, exec_horizon, task, init, seed) -> success, first wins."""
    cell = {}
    for path in sorted((ROOT / "results/v2_knobs").glob("records_*.jsonl")):
        for r in read_records(str(path)):
            key = (r.num_steps, r.exec_horizon, r.task_id, r.init_id, r.sampling_seed)
            cell.setdefault(key, r.success)
    return cell


def rate(cell, steps, horizon, tasks):
    hits = [
        ok
        for (s, h, t, _i, _sd), ok in cell.items()
        if (s, h) == (steps, horizon) and t in tasks
    ]
    return sum(hits), len(hits)


def compare(cell, cell_a, cell_b, tasks):
    """Paired comparison of two grid cells over the given tasks."""
    units = sorted(
        {(t, i, sd) for (s, h, t, i, sd) in cell if (s, h) == cell_a and t in tasks}
        & {(t, i, sd) for (s, h, t, i, sd) in cell if (s, h) == cell_b and t in tasks}
    )
    pairs = [(cell[(*cell_a, *u)], cell[(*cell_b, *u)]) for u in units]
    n = len(pairs)
    k_a = sum(a for a, _ in pairs)
    k_b = sum(b for _, b in pairs)
    a_only = sum(1 for a, b in pairs if a and not b)
    b_only = sum(1 for a, b in pairs if b and not a)
    p = mcnemar_exact(
        PairedCounts(
            both_succeed=sum(1 for a, b in pairs if a and b),
            a_only=a_only,
            b_only=b_only,
            both_fail=sum(1 for a, b in pairs if not a and not b),
        )
    )
    lo, hi = newcombe_diff(k_a, n, k_b, n)

    # Cluster bootstrap of the paired difference, resampling (task, init) clusters.
    rng = random.Random(0)
    clusters = defaultdict(list)
    for (t, i, _sd), pair in zip(units, pairs):
        clusters[(t, i)].append(pair)
    keys = list(clusters)
    diffs = []
    for _ in range(N_BOOT):
        drawn = [p for k in (rng.choice(keys) for _ in keys) for p in clusters[k]]
        m = len(drawn)
        diffs.append(100 * (sum(a for a, _ in drawn) - sum(b for _, b in drawn)) / m)
    diffs.sort()
    k_lo = diffs[int(0.025 * N_BOOT)]
    k_hi = diffs[int(0.975 * N_BOOT) - 1]

    return {
        "n": n,
        "rate_a": 100 * k_a / n,
        "rate_b": 100 * k_b / n,
        "diff_pts": 100 * (k_a - k_b) / n,
        "discordant_a_only": a_only,
        "discordant_b_only": b_only,
        "mcnemar_p": p,
        "newcombe_ci": [100 * lo, 100 * hi],
        "cluster_ci": [k_lo, k_hi],
        "equivalent_at_5": bool(k_lo > -5 and k_hi < 5),
    }


def main():
    cell = load_grid()

    by_task = defaultdict(list)
    for (s, h, t, _i, _sd), ok in cell.items():
        if (s, h) == DEFAULT_CELL:
            by_task[t].append(ok)
    default_rate = {t: sum(v) / len(v) for t, v in by_task.items()}

    print(f"per-task success at the shipped default {DEFAULT_CELL}:")
    for t in sorted(default_rate):
        head = 100 * (1 - default_rate[t])
        print(f"  task {t}: {default_rate[t]:.3f}   headroom {head:5.1f} pts")

    informative = sorted(t for t in default_rate if default_rate[t] < 0.95)
    non_ceiling = sorted(t for t in default_rate if default_rate[t] < 1.0)
    full = sorted(default_rate)

    print("\nexploratory restricted factorial (informative tasks only):")
    for s in STEPS:
        row = f"  s={s:<3}"
        for h in HORIZONS:
            k, n = rate(cell, s, h, informative)
            lo, hi = clopper_pearson(k, n)
            row += f"  h={h:<2} {100 * k / n:5.1f} [{100 * lo:4.1f},{100 * hi:4.1f}]"
        print(row)

    subsets = {
        "informative": informative,
        "non_ceiling": non_ceiling,
        "full_battery": full,
    }
    out = {"default_task_rates": {str(k): round(v, 4) for k, v in default_rate.items()}}
    for label, tasks in subsets.items():
        r = compare(cell, FRONTIER_CELL, DEFAULT_CELL, tasks)
        r["tasks"] = tasks
        out[label] = r
        print(
            f"\n{label}: n={r['n']} tasks={tasks}\n"
            f"  {r['rate_a']:.1f}% vs {r['rate_b']:.1f}%  diff {r['diff_pts']:+.1f} pts  "
            f"disc {r['discordant_a_only']}/{r['discordant_b_only']}  p={r['mcnemar_p']:.3f}\n"
            f"  Newcombe [{r['newcombe_ci'][0]:+.2f}, {r['newcombe_ci'][1]:+.2f}]  "
            f"init-cluster [{r['cluster_ci'][0]:+.2f}, {r['cluster_ci'][1]:+.2f}]  "
            f"equiv+/-5 {'HOLDS' if r['equivalent_at_5'] else 'FAILS'}"
        )

    out["restricted_grid"] = {
        f"s{s}_h{h}": list(rate(cell, s, h, informative)) for s in STEPS for h in HORIZONS
    }
    dest = ROOT / "docs/paper-data/restricted_factorial.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(f"\nwrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
