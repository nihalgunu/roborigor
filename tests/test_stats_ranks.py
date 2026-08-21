import pytest

pytest.importorskip("scipy")

from helpers import make_record as rec

from roborigor.stats.ranks import (
    bootstrap_tau,
    kendall_tau,
    null_rank_test,
    pairwise_flips,
    success_rates,
)


def test_pairwise_flips_identity_and_reversal():
    clean = {"a": 0.9, "b": 0.8, "c": 0.7, "d": 0.6}
    same = pairwise_flips(clean, clean)
    assert same["flips"] == 0 and same["tau"] == 1.0
    reversed_ = {"a": 0.6, "b": 0.7, "c": 0.8, "d": 0.9}
    rev = pairwise_flips(clean, reversed_)
    assert rev["flips"] == 6 and rev["tau"] == -1.0


def test_one_flip_tau():
    clean = {"a": 0.9, "b": 0.8, "c": 0.7, "d": 0.6}
    pert = {"a": 0.9, "b": 0.7, "c": 0.8, "d": 0.6}  # b and c swap
    out = pairwise_flips(clean, pert)
    assert out["flips"] == 1
    assert out["tau"] == pytest.approx(1 - 2 / 6)
    assert kendall_tau(clean, pert) == pytest.approx(out["tau"])


def test_null_rank_test_detects_real_flip():
    # big rates, big n: a genuine inversion should be significant
    clean = {"a": 0.9, "b": 0.7}
    pert = {"a": 0.3, "b": 0.8}
    n = {"a": 500, "b": 500}
    out = null_rank_test(clean, pert, n, n_sims=2000, seed=0)
    assert out["p_value"] < 0.01


def test_null_rank_test_accepts_noise():
    # same ordering, small wobble at small n: not significant
    clean = {"a": 0.9, "b": 0.7}
    pert = {"a": 0.72, "b": 0.68}
    n = {"a": 30, "b": 30}
    out = null_rank_test(clean, pert, n, n_sims=2000, seed=0)
    assert out["p_value"] > 0.05


def test_success_rates_and_bootstrap():
    def make(pid, rate, n=40, axis=None, level=None):
        return [
            rec(policy_id=pid, init_id=i, success=(i < rate * n),
                perturbation_axis=axis, perturbation_level=level)
            for i in range(n)
        ]

    clean = {"a": make("a", 0.9), "b": make("b", 0.6)}
    pert = {"a": make("a", 0.5, axis="camera", level="l1"),
            "b": make("b", 0.8, axis="camera", level="l1")}
    assert success_rates(clean)["a"] == pytest.approx(0.9)
    out = bootstrap_tau(clean, pert, n_boot=200, seed=0)
    assert out["tau"] == -1.0  # 2 policies, 1 pair, flipped
    lo, hi = out["tau_ci95"]
    assert lo <= out["tau"] <= hi


def test_mismatched_policies_raise():
    with pytest.raises(ValueError):
        pairwise_flips({"a": 0.5}, {"b": 0.5})
