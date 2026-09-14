"""V1 analysis: records to the variance-component table.

Every number recomputes from raw per-episode records; nothing is carried.
Decomposition arms feed the nested beta-binomial (plus MoM cross-check and
init-cluster bootstrap); the residual arm feeds the replicate-disagreement
estimate; the whole-campaign protocol spread comes free by marginalizing
sampling seeds over the decomposition arms.
"""

from __future__ import annotations

from roborigor.core.schema import EpisodeRecord
from roborigor.stats.variance import (
    cluster_bootstrap_icc,
    fit_betabinom,
    fit_mom,
    init_table,
    protocol_spread,
    residual_disagreement,
)


def varcomp_report(records: list[EpisodeRecord], residual_run_substr: str = "residual") -> dict:
    """Full V1 report from one campaign's records."""
    decomp = [r for r in records if residual_run_substr not in r.run_id]
    resid = [r for r in records if residual_run_substr in r.run_id]

    tasks = {}
    for key, counts in sorted(init_table(decomp).items()):
        suite, task_id = key
        draws = [len(v) for v in counts.values()]
        n_succ = sum(sum(v) for v in counts.values())
        entry = {"suite": suite, "task_id": task_id,
                 "n_inits": len(counts), "n_episodes": sum(draws),
                 # observed rate, the saturation criterion; `mu` below is the
                 # beta-binomial fitted mean and can straddle the threshold
                 "sr_observed": round(n_succ / sum(draws), 4)}
        try:
            bb = fit_betabinom(counts)
            mm = fit_mom(counts)
            lo, hi = cluster_bootstrap_icc(counts, n_boot=1000, seed=task_id)
            entry.update({
                "mu": round(bb.mu, 4),
                "icc": round(bb.icc, 4),
                "icc_ci95": [round(lo, 4), round(hi, 4)],
                "var_init": round(bb.var_init, 5),
                "e_pq_sampling": round(bb.e_pq, 5),
                "icc_mom": round(mm.icc, 4),
                "mom_agrees": abs(bb.icc - mm.icc) < 0.1,
            })
        except ValueError as e:
            entry["error"] = str(e)
        tasks[f"{suite}/task{task_id}"] = entry

    spread = protocol_spread(decomp)
    return {
        "n_records": len(records),
        "tasks": tasks,
        "protocol_spread": {
            "n_sampling_seeds": len(spread["rates_by_sampling_seed"]),
            "rates": {str(k): round(v, 4) for k, v in spread["rates_by_sampling_seed"].items()},
            "max_minus_min_points": round(100 * spread["spread_max_minus_min"], 2)
            if spread["spread_max_minus_min"] is not None else None,
            "sd_points": round(100 * spread["spread_sd"], 2)
            if spread["spread_sd"] is not None else None,
        },
        "residual": residual_disagreement(resid),
    }
