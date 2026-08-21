"""Rollout-budget calculator: exact power analysis for success-rate comparisons.

The single most useful thing this package hands another researcher: given a
minimum detectable effect and a confidence level, how many rollouts do you
need? Or inverted: at the n you ran, what gap could you even have detected?

Unpaired power is computed exactly by enumerating the two independent
binomials against the rejection region of the two-proportion score test
(exact evaluation of the test actually recommended for large families,
where per-cell Boschloo enumeration is too slow; at the paper's sample
sizes the score test's size is verified in tests). Paired power is the
exact McNemar decomposition: discordant count M ~ Bin(n, delta), and given
M = m the conditional test is an exact binomial test at m trials.
"""

from __future__ import annotations

import math

from scipy import stats as _st


def _score_test_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided two-proportion score (pooled z) test p-value."""
    p1, p2 = k1 / n1, k2 / n2
    pooled = (k1 + k2) / (n1 + n2)
    var = pooled * (1 - pooled) * (1 / n1 + 1 / n2)
    if var == 0:
        return 1.0
    z = (p1 - p2) / math.sqrt(var)
    return float(2 * _st.norm.sf(abs(z)))


def _binom_support(n: int, p: float, tail: float = 1e-10) -> range:
    """Central support of Bin(n, p) covering all but `tail` probability."""
    lo = int(_st.binom.ppf(tail / 2, n, p))
    hi = int(_st.binom.ppf(1 - tail / 2, n, p))
    return range(lo, hi + 1)


def power_unpaired(n: int, p1: float, p2: float, alpha: float = 0.05) -> float:
    """Exact power of the two-proportion score test at n per arm.

    Vectorized over the joint binomial support; exact up to the 1e-10
    support truncation. The scalar reference implementation is kept in
    tests as a cross-check on small n.
    """
    import numpy as np

    k1 = np.asarray(list(_binom_support(n, p1)), dtype=float)
    k2 = np.asarray(list(_binom_support(n, p2)), dtype=float)
    pmf1 = _st.binom.pmf(k1, n, p1)
    pmf2 = _st.binom.pmf(k2, n, p2)
    K1 = k1[:, None]
    K2 = k2[None, :]
    pooled = (K1 + K2) / (2 * n)
    var = pooled * (1 - pooled) * (2 / n)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(var > 0, np.abs(K1 / n - K2 / n) / np.sqrt(var), 0.0)
    reject = 2 * _st.norm.sf(z) < alpha
    return float(pmf1 @ reject @ pmf2)


def _power_exact_binom(m: int, p: float, alpha: float) -> float:
    """Power of the two-sided exact binomial test of 0.5 at m trials, truth p."""
    if m == 0:
        return 0.0
    ks = range(m + 1)
    reject = [
        _st.binomtest(k, m, 0.5, alternative="two-sided").pvalue < alpha for k in ks
    ]
    pmf = _st.binom.pmf(list(ks), m, p)
    return float(sum(w for w, r in zip(pmf, reject) if r))


def power_paired(
    n_pairs: int, p_a_only: float, p_b_only: float, alpha: float = 0.05
) -> float:
    """Exact power of the exact McNemar test.

    p_a_only / p_b_only are the discordance probabilities: P(A succeeds, B
    fails) and vice versa. Their sum delta is the total discordance rate;
    the smaller delta is, the more pairing buys over the unpaired test.
    """
    delta = p_a_only + p_b_only
    if delta == 0:
        return 0.0
    cond = p_a_only / delta
    power = 0.0
    for m in _binom_support(n_pairs, delta):
        if m == 0:
            continue
        power += float(_st.binom.pmf(m, n_pairs, delta)) * _power_exact_binom(m, cond, alpha)
    return power


def _invert_n(power_fn, target_power: float, n_max: int) -> int:
    """Smallest n with power >= target, by doubling then bisection."""
    lo, hi = 1, 2
    while hi <= n_max and power_fn(hi) < target_power:
        lo, hi = hi, hi * 2
    if hi > n_max:
        raise ValueError(f"target power not reached by n = {n_max}")
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if power_fn(mid) >= target_power:
            hi = mid
        else:
            lo = mid
    return hi


def required_n_unpaired(
    p1: float, p2: float, alpha: float = 0.05, power: float = 0.8, n_max: int = 200_000
) -> int:
    """Rollouts per arm for the unpaired comparison of p1 vs p2."""
    if p1 == p2:
        raise ValueError("p1 == p2 has no detectable effect")
    return _invert_n(lambda n: power_unpaired(n, p1, p2, alpha), power, n_max)


def required_n_paired(
    p_a_only: float,
    p_b_only: float,
    alpha: float = 0.05,
    power: float = 0.8,
    n_max: int = 200_000,
) -> int:
    """Matched pairs needed given the two discordance probabilities."""
    if p_a_only == p_b_only:
        raise ValueError("equal discordance probabilities has no detectable effect")
    return _invert_n(lambda n: power_paired(n, p_a_only, p_b_only, alpha), power, n_max)


def mde_unpaired(
    n: int, p_base: float, alpha: float = 0.05, power: float = 0.8, tol: float = 1e-4
) -> float:
    """Minimum detectable effect at n per arm against baseline rate p_base.

    Returns the smallest downward gap d such that p_base vs p_base - d is
    detected with the target power. (Downward, because the interesting case
    at LIBERO-like rates is a challenger below a near-saturated baseline.)
    """
    lo, hi = tol, p_base - tol
    if power_unpaired(n, p_base, p_base - hi, alpha) < power:
        raise ValueError(f"no gap up to {hi:.3f} is detectable at n = {n}")
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if power_unpaired(n, p_base, p_base - mid, alpha) >= power:
            hi = mid
        else:
            lo = mid
    return hi
