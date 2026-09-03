"""Pairwise policy comparisons.

Paired by init state is the default design: every policy sees identical
(suite, task_id, init_id, seed) episodes, so the exact McNemar test on
discordant pairs is both the most powerful and the most honest comparison.
Unpaired exact tests (Boschloo primary, Fisher reported for familiarity)
exist for the literature audit, where published numbers are never paired.

Multiple-comparison correction: Holm for the confirmatory suite-level
family (strong FWER control, no dependence assumptions), Benjamini-Hochberg
for the exploratory per-task family.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from scipy import stats as _st

from roborigor.core.schema import EpisodeRecord


def default_pair_key(rec: EpisodeRecord) -> tuple:
    """Pairing identity across policies: same episode apart from the policy."""
    return (rec.benchmark, rec.suite, rec.task_id, rec.init_id, rec.seed,
            rec.perturbation_axis, rec.perturbation_level)


@dataclass
class PairedCounts:
    """2x2 concordance table for one policy pair over matched episodes."""

    both_succeed: int
    a_only: int  # A succeeded, B failed (discordant)
    b_only: int  # B succeeded, A failed (discordant)
    both_fail: int
    n_unmatched_a: int = 0
    n_unmatched_b: int = 0

    @property
    def n_pairs(self) -> int:
        return self.both_succeed + self.a_only + self.b_only + self.both_fail

    @property
    def n_discordant(self) -> int:
        return self.a_only + self.b_only


def pair_records(
    recs_a: Iterable[EpisodeRecord],
    recs_b: Iterable[EpisodeRecord],
    key: Callable[[EpisodeRecord], tuple] = default_pair_key,
) -> PairedCounts:
    """Match episodes across two policies and tabulate concordance.

    Duplicate keys within one side are an integrity failure upstream and
    raise here rather than silently averaging.
    """
    a_by_key: dict = {}
    for r in recs_a:
        k = key(r)
        if k in a_by_key:
            raise ValueError(f"duplicate pairing key in first record set: {k}")
        a_by_key[k] = r
    seen_b = set()
    counts = {"both_succeed": 0, "a_only": 0, "b_only": 0, "both_fail": 0}
    n_b = 0
    n_matched = 0
    for r in recs_b:
        k = key(r)
        if k in seen_b:
            raise ValueError(f"duplicate pairing key in second record set: {k}")
        seen_b.add(k)
        n_b += 1
        ra = a_by_key.get(k)
        if ra is None:
            continue
        n_matched += 1
        if ra.success and r.success:
            counts["both_succeed"] += 1
        elif ra.success:
            counts["a_only"] += 1
        elif r.success:
            counts["b_only"] += 1
        else:
            counts["both_fail"] += 1
    return PairedCounts(
        **counts,
        n_unmatched_a=len(a_by_key) - n_matched,
        n_unmatched_b=n_b - n_matched,
    )


def mcnemar_exact(paired: PairedCounts) -> float:
    """Two-sided exact McNemar p-value: binomial test on discordant pairs."""
    m = paired.n_discordant
    if m == 0:
        return 1.0
    return float(_st.binomtest(paired.a_only, m, 0.5, alternative="two-sided").pvalue)


def boschloo(successes_a: int, n_a: int, successes_b: int, n_b: int) -> float:
    """Two-sided Boschloo exact p-value (uniformly more powerful than Fisher)."""
    table = [[successes_a, n_a - successes_a], [successes_b, n_b - successes_b]]
    return float(_st.boschloo_exact(table, alternative="two-sided").pvalue)


def fisher(successes_a: int, n_a: int, successes_b: int, n_b: int) -> float:
    """Two-sided Fisher exact p-value, reported for reader familiarity."""
    table = [[successes_a, n_a - successes_a], [successes_b, n_b - successes_b]]
    return float(_st.fisher_exact(table, alternative="two-sided")[1])


def holm(pvalues: list[float]) -> list[float]:
    """Holm step-down adjusted p-values (strong FWER control)."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvalues[i])
        adjusted[i] = min(1.0, running)
    return adjusted


def benjamini_hochberg(pvalues: list[float]) -> list[float]:
    """BH step-up adjusted p-values (FDR control; exploratory families only)."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i], reverse=True)
    adjusted = [0.0] * m
    running = 1.0
    for rank, i in enumerate(order):
        running = min(running, pvalues[i] * m / (m - rank))
        adjusted[i] = running
    return adjusted
