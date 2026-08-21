"""Rank stability of policy orderings under perturbation.

A Kendall tau over 4-6 policies is nearly information-free on its own, so
the headline statistic is the pairwise-flip count (the same information,
honest about granularity), backed by a null-simulation test: is the
observed rank disagreement more than binomial measurement noise would
produce if the true ordering were preserved? Bootstrap CIs resample shared
variants, never raw episodes, because identical variant subsets across
policies are what make comparisons paired (and therefore correlated).
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy import stats as _st

from roborigor.core.schema import EpisodeRecord


def success_rates(records_by_policy: dict) -> dict:
    """{policy_id: success rate} from {policy_id: [EpisodeRecord]}."""
    out = {}
    for pid, recs in records_by_policy.items():
        recs = list(recs)
        if not recs:
            raise ValueError(f"no records for policy {pid!r}")
        out[pid] = sum(r.success for r in recs) / len(recs)
    return out


def pairwise_flips(clean_rates: dict, perturbed_rates: dict) -> dict:
    """Count pairwise-order inversions between two rate dicts.

    Ties (exactly equal rates) count as half a flip against a strict order
    on the other side, mirroring Kendall tau-a handling.
    """
    pids = sorted(clean_rates)
    if sorted(perturbed_rates) != pids:
        raise ValueError("policy sets differ between clean and perturbed")
    flips = 0.0
    n_pairs = 0
    for i in range(len(pids)):
        for j in range(i + 1, len(pids)):
            a, b = pids[i], pids[j]
            dc = clean_rates[a] - clean_rates[b]
            dp = perturbed_rates[a] - perturbed_rates[b]
            n_pairs += 1
            if dc * dp < 0:
                flips += 1.0
            elif (dc == 0) != (dp == 0):
                flips += 0.5
    tau = 1 - 2 * flips / n_pairs if n_pairs else float("nan")
    return {"n_pairs": n_pairs, "flips": flips, "tau": tau}


def kendall_tau(clean_rates: dict, perturbed_rates: dict) -> float:
    """Kendall tau-b between the two orderings (scipy), for reporting."""
    pids = sorted(clean_rates)
    tau, _ = _st.kendalltau(
        [clean_rates[p] for p in pids], [perturbed_rates[p] for p in pids]
    )
    return float(tau)


def _variant_key(r: EpisodeRecord) -> tuple:
    return (r.benchmark, r.suite, r.task_id, r.init_id, r.seed,
            r.perturbation_axis, r.perturbation_level)


def _rates_over_keys(records_by_policy: dict, keys: list) -> dict:
    rates = {}
    for pid, by_key in records_by_policy.items():
        succ = 0
        n = 0
        for k in keys:
            for s in by_key[k]:
                succ += s
                n += 1
        rates[pid] = succ / n
    return rates


def _index_by_variant(records_by_policy: dict) -> tuple:
    indexed = {}
    shared: set | None = None
    for pid, recs in records_by_policy.items():
        by_key: dict = defaultdict(list)
        for r in recs:
            by_key[_variant_key(r)].append(bool(r.success))
        indexed[pid] = by_key
        shared = set(by_key) if shared is None else shared & set(by_key)
    if not shared:
        raise ValueError("no shared variants across policies")
    return indexed, sorted(shared)


def bootstrap_tau(
    clean_by_policy: dict,
    perturbed_by_policy: dict,
    n_boot: int = 1000,
    seed: int = 0,
) -> dict:
    """Percentile 95% CI on tau by resampling shared perturbed variants.

    Clean rates are recomputed per resample of clean variants likewise, so
    both sides carry their measurement noise. Requires the same policy ids
    on both sides; each side's variants are the keys shared by all policies.
    """
    if sorted(clean_by_policy) != sorted(perturbed_by_policy):
        raise ValueError("policy sets differ between clean and perturbed")
    rng = np.random.default_rng(seed)
    c_idx, c_keys = _index_by_variant(clean_by_policy)
    p_idx, p_keys = _index_by_variant(perturbed_by_policy)
    taus = []
    for _ in range(n_boot):
        ck = [c_keys[i] for i in rng.integers(0, len(c_keys), size=len(c_keys))]
        pk = [p_keys[i] for i in rng.integers(0, len(p_keys), size=len(p_keys))]
        taus.append(
            pairwise_flips(_rates_over_keys(c_idx, ck), _rates_over_keys(p_idx, pk))["tau"]
        )
    point = pairwise_flips(
        _rates_over_keys(c_idx, c_keys), _rates_over_keys(p_idx, p_keys)
    )
    return {
        **point,
        "tau_ci95": (float(np.percentile(taus, 2.5)), float(np.percentile(taus, 97.5))),
        "n_clean_variants": len(c_keys),
        "n_perturbed_variants": len(p_keys),
    }


def null_rank_test(
    clean_rates: dict,
    perturbed_rates: dict,
    n_per_policy_perturbed: dict,
    n_sims: int = 10_000,
    seed: int = 0,
) -> dict:
    """Is the observed rank disagreement more than noise would produce?

    H0: the true perturbed ordering equals the clean ordering; observed
    disagreement is binomial measurement noise. Simulation: keep the
    perturbed rate magnitudes but force their assignment to policies to
    follow the clean ordering, then redraw observed rates binomially and
    recompute tau. p = P(tau_sim <= tau_obs). Small p means the ranking
    truly moved. Assumes independent binomial noise per policy under H0,
    which is conservative for positively correlated paired designs.
    """
    pids = sorted(clean_rates)
    obs_tau = pairwise_flips(clean_rates, perturbed_rates)["tau"]
    clean_order = sorted(pids, key=lambda p: clean_rates[p], reverse=True)
    mags = sorted((perturbed_rates[p] for p in pids), reverse=True)
    null_true = dict(zip(clean_order, mags))  # order preserved, magnitudes kept
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_sims):
        sim = {
            p: rng.binomial(n_per_policy_perturbed[p], null_true[p])
            / n_per_policy_perturbed[p]
            for p in pids
        }
        if pairwise_flips(clean_rates, sim)["tau"] <= obs_tau:
            hits += 1
    return {"tau_obs": obs_tau, "p_value": (hits + 1) / (n_sims + 1)}
