import pytest

pytest.importorskip("scipy")

from roborigor.core.schema import wilson_ci95
from roborigor.stats.intervals import clopper_pearson, newcombe_diff, wilson


def test_cp_reference_value():
    # Cross-validated against direct inversion of the exact binomial test
    # (test_cp_matches_test_inversion below); baseline libero_10 cell.
    lo, hi = clopper_pearson(461, 500)
    assert abs(lo - 0.8949122736) < 1e-9
    assert abs(hi - 0.9439488262) < 1e-9


def test_cp_matches_test_inversion():
    # The definition: CP bounds are where the exact binomial test is
    # marginal at alpha/2. Independent of the beta-quantile identity.
    from scipy import optimize, stats

    for k, n in [(461, 500), (492, 500), (7, 50), (49, 50)]:
        lo, hi = clopper_pearson(k, n)
        lo2 = optimize.brentq(
            lambda p, k=k, n=n: stats.binom.sf(k - 1, n, p) - 0.025, 1e-9, 1 - 1e-9, xtol=1e-12
        )
        hi2 = optimize.brentq(
            lambda p, k=k, n=n: stats.binom.cdf(k, n, p) - 0.025, 1e-9, 1 - 1e-9, xtol=1e-12
        )
        assert abs(lo - lo2) < 1e-9 and abs(hi - hi2) < 1e-9


def test_cp_edges():
    assert clopper_pearson(0, 20)[0] == 0.0
    assert clopper_pearson(20, 20)[1] == 1.0
    lo, hi = clopper_pearson(0, 20)
    # rule of three neighborhood: hi close to 1 - (alpha/2)^(1/n)
    assert 0.13 < hi < 0.18


def test_cp_contains_wilson_at_high_rates():
    # CP is conservative: at least as wide as Wilson here
    for k, n in [(461, 500), (492, 500), (1935, 2000)]:
        cp = clopper_pearson(k, n)
        wi = wilson(k, n)
        assert cp[0] <= wi[0] + 1e-12
        assert cp[1] >= wi[1] - 1e-12


def test_wilson_matches_core():
    assert wilson(461, 500) == pytest.approx(wilson_ci95(461, 500), abs=1e-12)


def test_newcombe_sane():
    lo, hi = newcombe_diff(95, 100, 90, 100)
    assert lo < 0.05 < hi
    assert -1 <= lo < hi <= 1
    # zero-gap case straddles 0
    lo, hi = newcombe_diff(90, 100, 90, 100)
    assert lo < 0 < hi


def test_invalid_counts_raise():
    with pytest.raises(ValueError):
        clopper_pearson(5, 4)


def test_newcombe_paired_reference():
    # Worked example in Newcombe (1998b), Stat Med 17:2635, Table II:
    # cells 36/12/2/0 give method 10 interval 0.0569 to 0.3404.
    from roborigor.stats.intervals import newcombe_paired_diff

    lo, hi = newcombe_paired_diff(36, 12, 2, 0)
    assert abs(lo - 0.0569) < 5e-4 and abs(hi - 0.3404) < 5e-4


def test_newcombe_paired_narrower_under_positive_correlation():
    from roborigor.stats.intervals import newcombe_paired_diff

    # Mostly concordant pairs: the paired interval must be narrower than the
    # unpaired one built from the same marginals.
    a, b, c, d = 420, 23, 14, 23
    n = a + b + c + d
    plo, phi = newcombe_paired_diff(a, b, c, d)
    ulo, uhi = newcombe_diff(a + b, n, a + c, n)
    assert plo <= (b - c) / n <= phi
    assert phi - plo < uhi - ulo


def test_newcombe_paired_coverage_near_nominal():
    import numpy as np

    from roborigor.stats.intervals import newcombe_paired_diff

    rng = np.random.default_rng(1)
    probs = [0.85, 0.06, 0.04, 0.05]  # true difference 0.02
    truth = probs[1] - probs[2]
    hits = 0
    draws = 3000
    for cells in rng.multinomial(200, probs, size=draws):
        lo, hi = newcombe_paired_diff(*map(int, cells))
        hits += lo <= truth <= hi
    assert 0.93 <= hits / draws <= 0.975
