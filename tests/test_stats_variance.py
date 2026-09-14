import numpy as np
import pytest

pytest.importorskip("scipy")

from helpers import make_record as rec

from roborigor.stats.variance import (
    cluster_bootstrap_icc,
    fit_betabinom,
    fit_mom,
    init_table,
    protocol_spread,
    residual_disagreement,
)


def synth_counts(rng, n_inits=40, s=10, a=6.0, b=2.0):
    """Simulate the nested model: p_i ~ Beta(a, b), k_i ~ Bin(s, p_i)."""
    ps = rng.beta(a, b, size=n_inits)
    return {i: list(rng.random(s) < p) for i, p in enumerate(ps)}


def test_betabinom_recovers_truth():
    rng = np.random.default_rng(42)
    # average fits over replicates to beat simulation noise
    iccs, mus = [], []
    for _ in range(20):
        c = fit_betabinom(synth_counts(rng, n_inits=60, s=10, a=6.0, b=2.0))
        iccs.append(c.icc)
        mus.append(c.mu)
    assert abs(np.mean(mus) - 0.75) < 0.02  # a/(a+b)
    assert abs(np.mean(iccs) - 1 / 9) < 0.03  # 1/(a+b+1)


def test_mom_agrees_with_betabinom():
    rng = np.random.default_rng(7)
    c = synth_counts(rng, n_inits=200, s=10)
    bb = fit_betabinom(c)
    mm = fit_mom(c)
    assert abs(bb.icc - mm.icc) < 0.05
    assert abs(bb.e_pq - mm.e_pq) < 0.02


def test_no_init_effect_gives_small_icc():
    rng = np.random.default_rng(3)
    # constant p across inits: all variance is sampling
    c = {i: list(rng.random(10) < 0.7) for i in range(100)}
    assert fit_betabinom(c).icc < 0.05
    assert fit_mom(c).icc < 0.05


def test_pure_init_effect_gives_high_icc():
    # p_i is 0 or 1: no sampling variance at all
    c = {i: [i % 2 == 0] * 10 for i in range(40)}
    assert fit_betabinom(c).icc > 0.9
    assert fit_mom(c).icc > 0.9


def test_bootstrap_ci_covers_point():
    rng = np.random.default_rng(11)
    c = synth_counts(rng, n_inits=40, s=10)
    point = fit_betabinom(c).icc
    lo, hi = cluster_bootstrap_icc(c, n_boot=200, seed=1)
    assert lo <= point <= hi
    assert hi - lo < 0.5


def test_init_table_and_mixed_knobs():
    records = [rec(init_id=i, sampling_seed=s) for i in range(3) for s in range(4)]
    table = init_table(records)
    assert set(table) == {("libero_10", 0)}
    assert all(len(v) == 4 for v in table[("libero_10", 0)].values())
    with pytest.raises(ValueError, match="mixed factor"):
        init_table(records + [rec(init_id=9, num_steps=2)])


def test_residual_disagreement():
    reps = [rec(success=True), rec(success=True), rec(init_id=1, success=True),
            rec(init_id=1, success=False)]
    out = residual_disagreement(reps)
    assert out["n_replicated_cells"] == 2
    assert out["disagreement_rate"] == 0.5
    assert residual_disagreement([rec()])["disagreement_rate"] is None


def test_protocol_spread():
    records = []
    for s, p in [(0, 1.0), (1, 0.8), (2, 0.9)]:
        for i in range(10):
            records.append(rec(init_id=i, sampling_seed=s, success=(i < p * 10)))
    out = protocol_spread(records)
    assert out["spread_max_minus_min"] == pytest.approx(0.2)
    assert out["rates_by_sampling_seed"][1] == pytest.approx(0.8)
