"""Direct estimate of the system-nondeterminism variance component.

The replicate block repeats episodes at a fully fixed factor tuple (task, init,
environment seed, sampling seed, dials), so within-cell variance is system
nondeterminism by construction. Earlier drafts reported only the pooled
disagreement rate as a loose upper bound; pooling hides that the disagreement is
concentrated on the tasks that are not saturated. This estimates the component
directly, per task and pooled, with a cluster bootstrap over cells.

Logged as Entry 18 of the deviations log.
Writes docs/paper-data/nondeterminism.json.
"""

import json
import random
from collections import defaultdict
from pathlib import Path

from roborigor.core.schema import read_records

ROOT = Path(__file__).resolve().parents[1]
N_BOOT = 10000
INFORMATIVE_TASK = 8


def replicate_cells():
    """Cells repeated at a fully fixed factor tuple, keyed by every factor."""
    cells = defaultdict(list)
    for path in sorted((ROOT / "results/v1_varcomp").glob("*.jsonl")):
        for r in read_records(str(path)):
            if "residual_block" not in (r.run_id or ""):
                continue
            key = (r.policy_id, r.task_id, r.init_id, r.seed, r.sampling_seed,
                   r.num_steps, r.exec_horizon)
            cells[key].append(r.success)
    return {k: v for k, v in cells.items() if len(v) > 1}


def component(groups):
    """Unbiased mean within-cell variance, E[p(1-p)]."""
    vals = []
    for v in groups:
        m = len(v)
        p = sum(v) / m
        vals.append(p * (1 - p) * m / (m - 1))
    return sum(vals) / len(vals)


def boot_ci(groups, seed=0):
    rng = random.Random(seed)
    draws = sorted(component([rng.choice(groups) for _ in groups]) for _ in range(N_BOOT))
    return draws[int(0.025 * N_BOOT)], draws[int(0.975 * N_BOOT)]


def main():
    cells = replicate_cells()
    by_task = defaultdict(list)
    for (_pol, task, *_rest), v in cells.items():
        by_task[task].append(v)

    per_task = {}
    for task, groups in sorted(by_task.items()):
        disagree = sum(1 for v in groups if len(set(v)) > 1)
        per_task[str(task)] = {
            "n_cells": len(groups),
            "n_disagreeing": disagree,
            "disagreement_rate": round(disagree / len(groups), 4),
            "component": round(component(groups), 4),
        }

    all_groups = [v for g in by_task.values() for v in g]
    pooled_disagree = sum(1 for v in all_groups if len(set(v)) > 1)

    inf = by_task[INFORMATIVE_TASK]
    inf_pt = component(inf)
    inf_lo, inf_hi = boot_ci(inf)

    v1 = json.load(open(ROOT / "docs/paper-data/v1_varcomp_report.json"))["tasks"]
    t = v1[f"libero_10/task{INFORMATIVE_TASK}"]
    total = t["var_init"] + t["e_pq_sampling"]

    out = {
        "pooled": {
            "n_cells": len(all_groups),
            "n_disagreeing": pooled_disagree,
            "disagreement_rate": round(pooled_disagree / len(all_groups), 4),
            "component": round(component(all_groups), 4),
        },
        "per_task": per_task,
        "informative_task": {
            "task_id": INFORMATIVE_TASK,
            "total_variance": round(total, 4),
            "var_init": round(t["var_init"], 4),
            "within_init": round(t["e_pq_sampling"], 4),
            "nondeterminism": round(inf_pt, 4),
            "nondeterminism_ci95": [round(inf_lo, 4), round(inf_hi, 4)],
            "sampler_net": round(t["e_pq_sampling"] - inf_pt, 4),
            "pct_init": round(100 * t["var_init"] / total, 1),
            "pct_within_init": round(100 * t["e_pq_sampling"] / total, 1),
            "pct_nondeterminism": round(100 * inf_pt / total, 1),
            "pct_nondeterminism_ci95": [round(100 * inf_lo / total),
                                        round(100 * inf_hi / total)],
            "pct_sampler_net": round(100 * (t["e_pq_sampling"] - inf_pt) / total, 1),
            "pct_sampler_net_ci95": [round(100 * (t["e_pq_sampling"] - inf_hi) / total),
                                     round(100 * (t["e_pq_sampling"] - inf_lo) / total)],
            "sampler_net_exceeds_init": bool(t["e_pq_sampling"] - inf_pt > t["var_init"]),
        },
        "note": ("Measured on pi0.5 only; the replicate block is the sole source of "
                 "fully-fixed-factor repeats in the released record."),
    }
    dest = ROOT / "docs/paper-data/nondeterminism.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    print(f"\nwrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
