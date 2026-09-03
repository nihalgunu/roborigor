"""V2 analysis: success vs denoising budget and execution horizon.

Two latency axes are reported per cell. The modeled one comes from the
uncontended A100 cost model: per-chunk inference = prefix + per_step *
num_steps, amortized over exec_horizon. The measured one is the
server-side inference time actually recorded in the episodes, pooled
per cell and amortized the same way; it runs under the six-worker
contention of the real campaign, so it is the conservative of the two.
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

    cells = defaultdict(lambda: [0, 0, 0.0, 0, 0])
    for r in records:
        ns = r.num_steps if r.num_steps is not None else 10
        c = cells[(ns, r.exec_horizon)]
        c[0] += r.success
        c[1] += 1
        c[2] += r.server_infer_s_total or 0.0
        c[3] += r.n_env_steps or 0
        c[4] += r.n_chunks or 0
    out = []
    for (ns, eh), (k, n, srv_s, steps, chunks) in sorted(cells.items()):
        lo, hi = clopper_pearson(k, n)
        out.append({
            "num_steps": ns, "exec_horizon": eh, "n": n,
            "success_rate": round(k / n, 4),
            "ci95": [round(lo, 4), round(hi, 4)],
            "control_latency_ms_per_step": round(control_latency_ms(ns, eh), 2),
            "measured_latency_ms_per_step": round(1000 * srv_s / steps, 2) if steps else None,
            "measured_chunk_ms": round(1000 * srv_s / chunks, 2) if chunks else None,
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
