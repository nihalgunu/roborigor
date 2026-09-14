import numpy as np
import pytest

pytest.importorskip("scipy")

from roborigor.stats.sequential import SequentialPairedTest


def test_no_signal_no_rejection():
    t = SequentialPairedTest()
    t.update(a_wins=10, b_wins=10)
    assert t.decision == "continue"
    assert t.p_value > 0.5


def test_strong_signal_rejects():
    t = SequentialPairedTest()
    t.update(a_wins=30, b_wins=2)
    assert t.decision == "reject_null"
    assert t.p_value < 0.05


def test_rejection_is_sticky():
    t = SequentialPairedTest()
    t.update(a_wins=30, b_wins=2)
    assert t.decision == "reject_null"
    t.update(b_wins=40)  # later data cannot un-reject
    assert t.decision == "reject_null"


def test_type_i_error_under_continuous_peeking():
    # The core anytime-valid guarantee: peek after EVERY discordant pair,
    # reject if ever E >= 1/alpha. Under H0 the rejection rate stays <= alpha.
    rng = np.random.default_rng(0)
    n_sims, horizon, alpha = 400, 300, 0.05
    false_rejects = 0
    for _ in range(n_sims):
        t = SequentialPairedTest(alpha=alpha)
        for _ in range(horizon):
            if rng.random() < 0.5:
                t.update(a_wins=1)
            else:
                t.update(b_wins=1)
            if t.decision == "reject_null":
                false_rejects += 1
                break
    rate = false_rejects / n_sims
    # binomial slack on 400 sims: alpha + 3*sqrt(alpha(1-alpha)/400) ~ 0.083
    assert rate <= 0.083, f"type-I {rate} exceeds anytime-valid bound"


def test_power_against_real_gap():
    # theta = 0.75 in favor of A: should usually reject within 200 pairs
    rng = np.random.default_rng(1)
    rejects = 0
    for _ in range(100):
        t = SequentialPairedTest()
        for _ in range(200):
            t.update(a_wins=int(rng.random() < 0.75), b_wins=int(rng.random() >= 0.75))
            if t.decision == "reject_null":
                rejects += 1
                break
    assert rejects >= 80


def test_negative_counts_raise():
    with pytest.raises(ValueError):
        SequentialPairedTest().update(a_wins=-1)
