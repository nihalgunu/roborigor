"""V2 analysis: success vs denoising budget and execution horizon.

Latency axis is derived from the measured cost model (uncontended A100
reference): per-chunk inference = prefix + per_step * num_steps; control
latency per env step amortizes the chunk over exec_horizon and adds the
env step itself. Constants are the flowhelm-lab measured values; the
paper reports them as machine-tagged.
"""

from __future__ import annotations

from collections import defaultdict

PREFIX_MS = 53.2
PER_STEP_MS = 2.79
ENV_STEP_MS = 23.5


def control_latency_ms(num_steps: int, exec_horizon: int) -> float:
    """Amortized policy-side latency per executed env step."""
    return (PREFIX_MS + PER_STEP_MS * num_steps) / exec_horizon


def knob_table(records) -> dict:
    from roborigor.stats.intervals import clopper_pearson

    cells = defaultdict(lambda: [0, 0])
    for r in records:
        ns = r.num_steps if r.num_steps is not None else 10
        cells[(ns, r.exec_horizon)][0] += r.success
        cells[(ns, r.exec_horizon)][1] += 1
    out = []
    for (ns, eh), (k, n) in sorted(cells.items()):
        lo, hi = clopper_pearson(k, n)
        out.append({
            "num_steps": ns, "exec_horizon": eh, "n": n,
            "success_rate": round(k / n, 4),
            "ci95": [round(lo, 4), round(hi, 4)],
            "control_latency_ms_per_step": round(control_latency_ms(ns, eh), 2),
        })
    return {"cells": out}


def pareto_frontier(cells: list) -> list:
    """Cells not dominated in (lower latency, higher success)."""
    frontier = []
    for c in cells:
        dominated = any(
            o["control_latency_ms_per_step"] <= c["control_latency_ms_per_step"]
            and o["success_rate"] >= c["success_rate"]
            and (o["control_latency_ms_per_step"], -o["success_rate"])
            != (c["control_latency_ms_per_step"], -c["success_rate"])
            for o in cells
        )
        if not dominated:
            frontier.append(c)
    return sorted(frontier, key=lambda c: c["control_latency_ms_per_step"])
