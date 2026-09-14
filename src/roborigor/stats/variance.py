"""Variance decomposition for flow-matching action heads.

The nested model: for a fixed task, each init state i has a latent success
probability p_i over the flow-sampling noise; sampling seeds are draws from
that distribution, not reusable treatment levels (a seed has no identity
across inits). The exact decomposition of the binary outcome's variance is

    Var(y) = Var_i(p_i) + E_i[p_i (1 - p_i)]

with the first term the init-state component and the second the
flow-sampling component. The intraclass correlation rho = Var_i(p_i)/Var(y)
is the init-attributable share.

Primary estimator: per-task beta-binomial maximum likelihood, where
rho = 1 / (alpha + beta + 1) in closed form. Cross-checks: method of
moments (assumption-free), and a cluster bootstrap over inits for CIs.
Residual (system-level nondeterminism, never "physics nondeterminism") is
estimated separately from replicates at fixed full cell_key.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from roborigor.core.schema import EpisodeRecord, cell_key


def init_table(records: Iterable[EpisodeRecord]) -> dict:
    """Group records into {(suite, task_id): {init_id: [successes...]}}.

    Only the sampling-seed dimension may vary within an init here; mixed
    num_steps or exec_horizon in one table is a design error and raises.
    """
    tasks: dict = defaultdict(lambda: defaultdict(list))
    fixed: dict = {}
    for r in records:
        knob = (r.num_steps, r.exec_horizon, r.perturbation_axis, r.perturbation_level)
        prev = fixed.setdefault((r.suite, r.task_id), knob)
        if prev != knob:
            raise ValueError(
                f"mixed factor settings within one variance table for "
                f"({r.suite}, task {r.task_id}): {prev} vs {knob}"
            )
        tasks[(r.suite, r.task_id)][r.init_id].append(bool(r.success))
    return {k: dict(v) for k, v in tasks.items()}


def _betabinom_negll(params: np.ndarray, ks: np.ndarray, ns: np.ndarray) -> float:
    from scipy import special
    a, b = np.exp(params)
    ll = (
        special.betaln(ks + a, ns - ks + b)
        - special.betaln(a, b)
        + special.gammaln(ns + 1)
        - special.gammaln(ks + 1)
        - special.gammaln(ns - ks + 1)
    )
    return float(-np.sum(ll))


@dataclass
class TaskComponents:
    """Variance components for one task."""

    n_inits: int
    draws_per_init: float  # mean seeds per init
    mu: float  # mean success probability
    var_init: float  # Var_i(p_i)
    e_pq: float  # E_i[p_i(1-p_i)], the flow-sampling component
    icc: float  # init share of total variance
    method: str  # "betabinom" or "mom"


def fit_betabinom(counts: dict) -> TaskComponents:
    from scipy import optimize
    """Beta-binomial ML fit for one task's {init_id: [successes...]} table."""
    ks = np.array([sum(v) for v in counts.values()], dtype=float)
    ns = np.array([len(v) for v in counts.values()], dtype=float)
    if len(ks) < 2:
        raise ValueError("need >= 2 inits to decompose variance")
    res = optimize.minimize(
        _betabinom_negll, x0=np.log([2.0, 2.0]), args=(ks, ns), method="Nelder-Mead",
        options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000},
    )
    a, b = np.exp(res.x)
    mu = a / (a + b)
    icc = 1.0 / (a + b + 1.0)
    total = mu * (1 - mu)
    return TaskComponents(
        n_inits=len(ks),
        draws_per_init=float(ns.mean()),
        mu=float(mu),
        var_init=float(total * icc),
        e_pq=float(total * (1 - icc)),
        icc=float(icc),
        method="betabinom",
    )


def fit_mom(counts: dict) -> TaskComponents:
    """Method-of-moments cross-check, no distributional assumption.

    Within-init w_i = p_hat_i(1-p_hat_i) * S/(S-1) is unbiased for
    p_i(1-p_i); the between-init sample variance overshoots Var(p_i) by
    E[p(1-p)]/S and is corrected. Estimates clip at zero.
    """
    phat = np.array([sum(v) / len(v) for v in counts.values()])
    ss = np.array([len(v) for v in counts.values()], dtype=float)
    if len(phat) < 2:
        raise ValueError("need >= 2 inits to decompose variance")
    if (ss < 2).any():
        raise ValueError("method of moments needs >= 2 draws per init")
    w = phat * (1 - phat) * ss / (ss - 1)
    e_pq = float(w.mean())
    var_between = float(phat.var(ddof=1))
    var_init = max(0.0, var_between - e_pq / float(ss.mean()))
    mu = float(phat.mean())
    total = var_init + e_pq
    return TaskComponents(
        n_inits=len(phat),
        draws_per_init=float(ss.mean()),
        mu=mu,
        var_init=var_init,
        e_pq=e_pq,
        icc=var_init / total if total > 0 else 0.0,
        method="mom",
    )


def cluster_bootstrap_icc(
    counts: dict, n_boot: int = 1000, seed: int = 0, estimator=fit_betabinom
) -> tuple[float, float]:
    """Percentile 95% CI on the ICC by resampling inits with replacement.

    Resamples whole inits (all their seed draws together); resampling raw
    episodes would break the nesting and understate uncertainty.
    """
    rng = np.random.default_rng(seed)
    inits = list(counts.values())
    stats = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(inits), size=len(inits))
        sample = {i: inits[j] for i, j in enumerate(idx)}
        try:
            stats.append(estimator(sample).icc)
        except ValueError:
            continue  # degenerate resample (all-identical); skip
    if not stats:
        raise ValueError("all bootstrap resamples degenerate")
    return (float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5)))


def residual_disagreement(records: Sequence[EpisodeRecord]) -> dict:
    """System-level nondeterminism from replicates at identical cell_key.

    Groups records by full cell_key; among keys with >= 2 replicates,
    reports the fraction whose outcomes disagree. Zero means outcome-level
    determinism held in this dataset.
    """
    by_key: dict = defaultdict(list)
    for r in records:
        by_key[cell_key(r)[:-1]].append(bool(r.success))  # identity minus replicate
    replicated = {k: v for k, v in by_key.items() if len(v) >= 2}
    if not replicated:
        return {"n_replicated_cells": 0, "disagreement_rate": None}
    mixed = sum(1 for v in replicated.values() if len(set(v)) > 1)
    return {
        "n_replicated_cells": len(replicated),
        "disagreement_rate": mixed / len(replicated),
    }


def protocol_spread(records: Iterable[EpisodeRecord]) -> dict:
    """Spread of the standard-protocol headline number across sampling seeds.

    Marginalizes the records by sampling_seed: each seed column is one run
    of the literature-standard protocol. Returns per-seed success rates and
    their spread; the paper's headline sentence comes from here.
    """
    by_seed: dict = defaultdict(lambda: [0, 0])
    for r in records:
        by_seed[r.sampling_seed][0] += bool(r.success)
        by_seed[r.sampling_seed][1] += 1
    rates = {s: k / n for s, (k, n) in sorted(by_seed.items(), key=lambda x: str(x[0]))}
    vals = np.array(list(rates.values()))
    return {
        "rates_by_sampling_seed": rates,
        "spread_max_minus_min": float(vals.max() - vals.min()) if len(vals) else None,
        "spread_sd": float(vals.std(ddof=1)) if len(vals) > 1 else None,
    }
