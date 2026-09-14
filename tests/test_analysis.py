import numpy as np
import pytest

pytest.importorskip("scipy")

from helpers import make_record as rec

from roborigor.analysis.varcomp import varcomp_report


def test_varcomp_report_end_to_end():
    rng = np.random.default_rng(0)
    records = []
    # decomposition arm: task 8, strong init effect
    for i in range(30):
        p = rng.beta(6, 2)
        for s in range(10):
            records.append(rec(task_id=8, init_id=i, sampling_seed=s,
                               success=bool(rng.random() < p), run_id="v1/qualifying"))
    # residual arm: replicates, deterministic outcomes
    for i in range(6):
        for s in (100, 101):
            for r in range(3):
                records.append(rec(task_id=8, init_id=i, sampling_seed=s,
                                   replicate=r, success=(i % 2 == 0),
                                   run_id="v1/residual_block"))
    out = varcomp_report(records)
    task = out["tasks"]["libero_10/task8"]
    assert task["n_inits"] == 30 and task["n_episodes"] == 300
    assert 0 < task["icc"] < 1 and task["mom_agrees"]
    assert task["icc_ci95"][0] <= task["icc"] <= task["icc_ci95"][1]
    assert out["residual"]["n_replicated_cells"] == 12
    assert out["residual"]["disagreement_rate"] == 0.0  # deterministic replicates
    assert out["protocol_spread"]["n_sampling_seeds"] == 10
