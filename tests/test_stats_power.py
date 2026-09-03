import pytest

pytest.importorskip("scipy")

from roborigor.stats.power import (
    mde_unpaired,
    power_paired,
    power_unpaired,
    required_n_paired,
    required_n_unpaired,
)


def test_power_monotone_in_n():
    p = [power_unpaired(n, 0.95, 0.85) for n in (50, 100, 200)]
    assert p[0] < p[1] < p[2]


def test_required_n_reference_scale():
    # 0.85 vs 0.95: normal-approx arithmetic says ~140 per arm at 80% power
    n = required_n_unpaired(0.95, 0.85)
    assert 100 <= n <= 200
    # 5-pt gap at higher rates needs several hundred
    n5 = required_n_unpaired(0.95, 0.90)
    assert 350 <= n5 <= 550
    assert n5 > n


def test_required_n_is_minimal():
    n = required_n_unpaired(0.95, 0.85)
    assert power_unpaired(n, 0.95, 0.85) >= 0.8
    assert power_unpaired(n - 1, 0.95, 0.85) < 0.8


def test_mde_headline_claim():
    # At n=50 (the field's per-task default) and base ~0.95 the MDE is huge:
    # nothing much under ~15-20 points is detectable.
    d = mde_unpaired(50, 0.95)
    assert 0.13 <= d <= 0.22
    # at n=500 it drops to a few points
    d500 = mde_unpaired(500, 0.95)
    assert 0.03 <= d500 <= 0.07
    assert d500 < d


def test_paired_beats_unpaired_at_low_discordance():
    # Same marginal gap (5 pts), low discordance: pairing needs fewer episodes
    n_paired = required_n_paired(0.08, 0.03)
    n_unpaired = required_n_unpaired(0.95, 0.90)
    assert n_paired < n_unpaired


def test_paired_power_monotone():
    assert power_paired(200, 0.08, 0.03) < power_paired(400, 0.08, 0.03)


def test_degenerate_inputs_raise():
    with pytest.raises(ValueError):
        required_n_unpaired(0.9, 0.9)
    with pytest.raises(ValueError):
        required_n_paired(0.05, 0.05)


def test_vectorized_power_matches_scalar_reference():
    import numpy as np
    from scipy import stats as st

    from roborigor.stats.power import _binom_support, _score_test_p

    n, p1, p2, alpha = 60, 0.9, 0.7, 0.05
    ref = 0.0
    s1, s2 = list(_binom_support(n, p1)), list(_binom_support(n, p2))
    pm1, pm2 = st.binom.pmf(s1, n, p1), st.binom.pmf(s2, n, p2)
    for i, k1 in enumerate(s1):
        for j, k2 in enumerate(s2):
            if _score_test_p(k1, n, k2, n) < alpha:
                ref += pm1[i] * pm2[j]
    assert np.isclose(power_unpaired(n, p1, p2, alpha), ref, atol=1e-10)
