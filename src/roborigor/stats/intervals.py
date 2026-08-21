"""Binomial confidence intervals.

Clopper-Pearson is the headline interval: guaranteed >= nominal coverage,
which is the right default for a paper arguing that reported intervals are
too optimistic. Wilson is reported alongside in every table for continuity
with prior baselines and to show conclusions are interval-choice-invariant.

CI overlap is never used as a hypothesis test anywhere in this package;
comparisons go through roborigor.stats.compare.
"""

from __future__ import annotations

from scipy import stats as _st


def clopper_pearson(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Clopper-Pearson) two-sided CI for a binomial proportion."""
    if not 0 <= successes <= n:
        raise ValueError(f"need 0 <= successes <= n, got {successes}/{n}")
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if successes == 0 else float(_st.beta.ppf(alpha / 2, successes, n - successes + 1))
    hi = 1.0 if successes == n else float(_st.beta.ppf(1 - alpha / 2, successes + 1, n - successes))
    return (lo, hi)


def wilson(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval at arbitrary alpha (alpha=0.05 matches core.schema.wilson_ci95)."""
    if not 0 <= successes <= n:
        raise ValueError(f"need 0 <= successes <= n, got {successes}/{n}")
    if n == 0:
        return (0.0, 1.0)
    z = float(_st.norm.ppf(1 - alpha / 2))
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (max(0.0, center - half), min(1.0, center + half))


def newcombe_diff(
    successes_a: int, n_a: int, successes_b: int, n_b: int, alpha: float = 0.05
) -> tuple[float, float]:
    """Newcombe score-based CI for the difference p_a - p_b (unpaired).

    Newcombe (1998) method 10: combines the two Wilson intervals. Better
    small-sample behavior than the Wald difference interval.
    """
    pa = successes_a / n_a
    pb = successes_b / n_b
    la, ua = wilson(successes_a, n_a, alpha)
    lb, ub = wilson(successes_b, n_b, alpha)
    d = pa - pb
    lo = d - ((pa - la) ** 2 + (ub - pb) ** 2) ** 0.5
    hi = d + ((ua - pa) ** 2 + (pb - lb) ** 2) ** 0.5
    return (max(-1.0, lo), min(1.0, hi))
