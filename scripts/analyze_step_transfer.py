"""Does the single-step result transfer? Ceiling dilution and the step effect
across policies, seeds, and shifts.

Every row is the same paired contrast, one Euler step vs ten at execution
horizon 10, so rows differ only in where the contrast is measured. Rows:
pi0.5 on the LIBERO-10 battery (full, headroom-only, one task), at a second
environment seed, under two LIBERO-Plus shifts, and on pi0 and SmolVLA.

Also reports:
  * per-task discordant pairs and the dilution curve (interval vs tasks
    admitted in order of headroom), since concordant pairs shrink a
    difference interval as 1/n while carrying no evidence about the dials;
  * the conditional (discordant-pair) odds ratio with an exact interval,
    which concordant pairs cannot move;
  * paired pairs needed to certify +/-5 points on the pre-declared
    informative tasks (0, 2, 8, 9; configs/v1_varcomp_pi05.yaml).

Writes docs/paper-data/step_transfer.json.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

from roborigor.core.schema import read_records
from roborigor.stats.compare import PairedCounts, mcnemar_exact
from roborigor.stats.intervals import clopper_pearson, newcombe_diff, newcombe_paired_diff

ROOT = Path(__file__).resolve().parents[1]
N_BOOT = 4000
MARGIN = 5.0


def load(*dirs):
    recs = []
    for d in dirs:
        for f in sorted((ROOT / "results" / d).rglob("records_*.jsonl")):
            recs.extend(read_records(str(f)))
    return recs


def unit_key(r):
    """Everything that identifies the episode apart from the dials."""
    return (r.seed, r.task_id, r.init_id, r.sampling_seed, r.perturbation_axis,
            r.perturbation_level, r.replicate)


def cluster_key(r):
    """Resampling cluster: the initial scene (task, init, variant)."""
    return (r.task_id, r.init_id, r.perturbation_axis, r.perturbation_level)


def arm(recs, policy, steps, horizon, seed=7, axis=None, tasks=None):
    """unit -> (success, cluster, task), first record per unit wins."""
    out = {}
    for r in recs:
        if r.policy_id != policy or r.seed != seed or r.exec_horizon != horizon:
            continue
        if r.num_steps != steps or r.perturbation_axis != axis:
            continue
        if tasks is not None and r.task_id not in tasks:
            continue
        out.setdefault(unit_key(r), (bool(r.success), cluster_key(r), r.task_id))
    return out


def contrast(a, b):
    """Paired a-minus-b comparison over matched units."""
    units = sorted(set(a) & set(b), key=str)
    pairs = [(a[u][0], b[u][0], a[u][1], a[u][2]) for u in units]
    n = len(pairs)
    k_a = sum(p[0] for p in pairs)
    k_b = sum(p[1] for p in pairs)
    a_only = sum(1 for p in pairs if p[0] and not p[1])
    b_only = sum(1 for p in pairs if p[1] and not p[0])
    counts = PairedCounts(
        both_succeed=sum(1 for p in pairs if p[0] and p[1]),
        a_only=a_only, b_only=b_only,
        both_fail=sum(1 for p in pairs if not p[0] and not p[1]),
    )
    lo, hi = newcombe_paired_diff(counts.both_succeed, a_only, b_only, counts.both_fail)
    ulo, uhi = newcombe_diff(k_a, n, k_b, n)

    rng = random.Random(0)
    clusters = defaultdict(list)
    for p in pairs:
        clusters[p[2]].append(p[0] - p[1])
    keys = list(clusters)
    boots = []
    for _ in range(N_BOOT):
        drawn = [d for k in (rng.choice(keys) for _ in keys) for d in clusters[k]]
        boots.append(100 * sum(drawn) / len(drawn))
    boots.sort()
    c_lo, c_hi = boots[int(0.025 * N_BOOT)], boots[int(0.975 * N_BOOT) - 1]

    # Conditional odds ratio a_only/b_only: depends on discordant pairs only.
    m = a_only + b_only
    if m:
        q_lo, q_hi = clopper_pearson(a_only, m)
        odds = [q_lo / (1 - q_lo) if q_lo < 1 else float("inf"),
                q_hi / (1 - q_hi) if q_hi < 1 else float("inf")]
    else:
        odds = [0.0, float("inf")]

    per_task = defaultdict(lambda: [0, 0, 0, 0])  # n, k_b(reference), a_only, b_only
    for p in pairs:
        t = per_task[p[3]]
        t[0] += 1
        t[1] += p[1]
        t[2] += p[0] and not p[1]
        t[3] += p[1] and not p[0]

    return {
        "n_pairs": n,
        "rate_a": round(k_a / n, 4),
        "rate_b": round(k_b / n, 4),
        "diff_pts": round(100 * (k_a - k_b) / n, 2),
        "a_only": a_only,
        "b_only": b_only,
        "mcnemar_p": mcnemar_exact(counts),
        "ci_pts": [round(100 * lo, 2), round(100 * hi, 2)],
        "ci_method": "Newcombe paired (method 10)",
        "newcombe_unpaired_ci_pts": [round(100 * ulo, 2), round(100 * uhi, 2)],
        "cluster_ci_pts": [round(c_lo, 2), round(c_hi, 2)],
        "equivalent_at_5": bool(100 * lo > -MARGIN and 100 * hi < MARGIN),
        "equivalent_at_5_unpaired": bool(100 * ulo > -MARGIN and 100 * uhi < MARGIN),
        "equivalent_at_5_cluster": bool(c_lo > -MARGIN and c_hi < MARGIN),
        "cond_odds_ratio": round(a_only / b_only, 3) if b_only else None,
        "cond_odds_ratio_ci": [round(x, 3) for x in odds],
        "per_task": {str(t): {"n": v[0], "ref_rate": round(v[1] / v[0], 4),
                              "a_only": v[2], "b_only": v[3]}
                     for t, v in sorted(per_task.items())},
    }


def dilution_curve(a, b):
    """Admit tasks from most to least headroom at the reference arm."""
    ref = defaultdict(list)
    for _u, (ok, _c, t) in b.items():
        ref[t].append(ok)
    order = sorted(ref, key=lambda t: sum(ref[t]) / len(ref[t]))
    curve = []
    for i in range(1, len(order) + 1):
        keep = set(order[:i])
        sub_a = {u: v for u, v in a.items() if v[2] in keep}
        sub_b = {u: v for u, v in b.items() if v[2] in keep}
        r = contrast(sub_a, sub_b)
        both = sum(1 for u in set(sub_a) & set(sub_b) if sub_a[u][0] and sub_b[u][0])
        n_ = r["n_pairs"]
        lo90, hi90 = newcombe_paired_diff(both, r["a_only"], r["b_only"], n_ - both - r["a_only"] - r["b_only"], 0.10)
        curve.append({
            "ci90_pts": [round(100 * lo90, 2), round(100 * hi90, 2)],
            "tasks": order[:i],
            "added_task": order[i - 1],
            "added_task_ref_rate": round(sum(ref[order[i - 1]]) / len(ref[order[i - 1]]), 4),
            "n_pairs": r["n_pairs"],
            "discordant": r["a_only"] + r["b_only"],
            "diff_pts": r["diff_pts"],
            "ci_pts": r["ci_pts"],
            "cluster_ci_pts": r["cluster_ci_pts"],
        })
    return curve


def pairs_to_certify(p_disc, p_both_fail, margin_pts=MARGIN, power=0.8, n_sim=2000, seed=0):
    """Smallest n (on a 20-pair grid) at which the paper's rule certifies: the
    paired Newcombe 95% interval lies inside +/-margin with the target
    probability. True difference zero; discordance rate p_disc and both-fail
    rate p_both_fail as observed; pairs independent (clustering by initial
    state would raise the requirement)."""
    rng = np.random.default_rng(seed)
    probs = [1 - p_disc - p_both_fail, p_disc / 2, p_disc / 2, p_both_fail]
    for n in range(20, 4001, 20):
        draws = rng.multinomial(n, probs, size=n_sim)
        ok = 0
        for a, b, c, d in draws:
            lo, hi = newcombe_paired_diff(int(a), int(b), int(c), int(d))
            ok += (100 * lo > -margin_pts) and (100 * hi < margin_pts)
        if ok / n_sim >= power:
            return n
    return None


def main():
    grid = load("v2_knobs")
    rep = load("replication")
    shift = load("fusion", "camconf")
    smol = load("smolgrid", "gapfill")

    tasks_all = sorted({r.task_id for r in grid})
    a = arm(grid, "pi05_libero", 1, 10)
    b = arm(grid, "pi05_libero", 10, 10)
    battery = contrast(a, b)
    ref_rate = {int(t): v["ref_rate"] for t, v in battery["per_task"].items()}
    # Pre-declared informative tasks (development-scan success in [0.5, 0.95]),
    # fixed in configs/v1_varcomp_pi05.yaml before any grid episode was run.
    headroom = [0, 2, 8, 9]
    non_perfect = sorted(t for t in tasks_all if ref_rate[t] < 1.0)

    def sub(tasks):
        keep = set(tasks)
        return contrast({u: v for u, v in a.items() if v[2] in keep},
                        {u: v for u, v in b.items() if v[2] in keep})

    rows = {
        "pi05_battery": battery,
        "pi05_non_perfect_tasks": sub(non_perfect),
        "pi05_headroom_tasks": sub(headroom),
        "pi05_envseed8": contrast(arm(rep, "pi05_libero", 1, 10, seed=8),
                                  arm(rep, "pi05_libero", 10, 10, seed=8)),
        "pi05_layout_shift": contrast(arm(shift, "pi05_libero", 1, 10, axis="Objects Layout"),
                                      arm(shift, "pi05_libero", 10, 10, axis="Objects Layout")),
        "pi05_camera_confirmatory": contrast(
            arm(load("camconf"), "pi05_libero", 1, 10, axis="Camera Viewpoints"),
            arm(load("camconf"), "pi05_libero", 10, 10, axis="Camera Viewpoints")),
        "pi0_battery": contrast(arm(rep, "pi0_libero", 1, 10), arm(rep, "pi0_libero", 10, 10)),
        "smolvla_battery": contrast(arm(smol, "smolvla_libero", 1, 10),
                                    arm(smol, "smolvla_libero", None, 10)),
    }
    # Robustness: define headroom on the shipped-default arm (10, 5), which is
    # not part of the contrast, so subset choice cannot select on its outcomes.
    shipped_arm = arm(grid, "pi05_libero", 10, 5)
    by_t = defaultdict(list)
    for _u, (ok, _c, t) in shipped_arm.items():
        by_t[t].append(ok)
    shipped_rate = {t: sum(v) / len(v) for t, v in by_t.items()}
    alt_non_perfect = sorted(t for t in tasks_all if shipped_rate[t] < 1.0)
    alt_headroom = sorted(t for t in tasks_all if shipped_rate[t] <= 1 - MARGIN / 100)
    alt = {"non_perfect_tasks": sub(alt_non_perfect), "headroom_tasks": sub(alt_headroom)}
    alt["non_perfect_tasks"]["tasks"] = alt_non_perfect
    alt["headroom_tasks"]["tasks"] = alt_headroom
    rows["pi05_non_perfect_tasks"]["tasks"] = non_perfect
    rows["pi05_headroom_tasks"]["tasks"] = headroom

    # The practical comparison (frontier vs shipped default), kept alongside.
    shipped = contrast(a, arm(grid, "pi05_libero", 10, 5))

    disc = rows["pi05_headroom_tasks"]
    p_disc = (disc["a_only"] + disc["b_only"]) / disc["n_pairs"]
    per_task_n = disc["n_pairs"] // max(1, len(headroom))
    hard = battery["per_task"][str(min(ref_rate, key=ref_rate.get))]
    hard_disc = (hard["a_only"] + hard["b_only"]) / hard["n"]

    def both_fail_rate(tasks):
        units = [u for u in set(a) & set(b) if a[u][2] in tasks]
        return sum(1 for u in units if not a[u][0] and not b[u][0]) / len(units)
    bf_head = both_fail_rate(set(headroom))
    bf_hard = both_fail_rate({min(ref_rate, key=ref_rate.get)})

    # Does the environment seed change rollouts beyond closed-loop nondeterminism?
    def lengths(recs, seed, steps, horizon):
        out_ = {}
        for r in recs:
            if (r.policy_id, r.seed, r.num_steps, r.exec_horizon, r.perturbation_axis) == \
                    ("pi05_libero", seed, steps, horizon, None):
                out_.setdefault((r.task_id, r.init_id, r.sampling_seed), r.n_env_steps)
        return out_
    seed_diff = {}
    for steps, horizon in ((1, 10), (10, 10)):
        l7, l8 = lengths(grid, 7, steps, horizon), lengths(rep, 8, steps, horizon)
        common = set(l7) & set(l8)
        seed_diff[f"s{steps}_h{horizon}"] = round(sum(l7[u] != l8[u] for u in common) / len(common), 4)
    reps = defaultdict(set)
    for r in load("v1_varcomp"):
        if r.sampling_seed in (100, 101, 102):
            reps[(r.task_id, r.init_id, r.sampling_seed)].add(r.n_env_steps)
    replicate_diff = round(sum(len(v) > 1 for v in reps.values()) / len(reps), 4)

    out = {
        "contrast": "num_steps 1 minus num_steps 10 at exec_horizon 10, paired",
        "envseed_length_differs_share": seed_diff,
        "replicate_cells_length_differs_share": replicate_diff,
        "margin_pts": MARGIN,
        "rows": rows,
        "pi05_vs_shipped_default_10_5": shipped,
        "pi05_reference_task_rates": {str(t): ref_rate[t] for t in tasks_all},
        "pi05_subsets_by_shipped_default_arm": {
            "shipped_task_rates": {str(t): round(shipped_rate[t], 4) for t in tasks_all},
            **alt,
        },
        "dilution_curve_pi05": dilution_curve(a, b),
        "certify": {
            "headroom_tasks": headroom,
            "observed_discordance_rate": round(p_disc, 4),
            "pairs_per_task_in_battery": per_task_n,
            "pairs_needed_true_diff_0_power80": pairs_to_certify(p_disc, bf_head),
            "hardest_task": min(ref_rate, key=ref_rate.get),
            "hardest_task_discordance_rate": round(hard_disc, 4),
            "hardest_task_pairs_needed_true_diff_0_power80": pairs_to_certify(hard_disc, bf_hard),
            "method": "Monte Carlo, paired Newcombe 95% interval inside the margin, independent pairs, 2000 draws per n",
        },
        "smolvla_default_steps_note": "SmolVLA reference arm is the served default (num_steps unrecorded)",
    }
    dest = ROOT / "docs/paper-data/step_transfer.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")

    for name, r in rows.items():
        print(f"{name:28s} n={r['n_pairs']:4d} {100*r['rate_a']:5.1f} vs {100*r['rate_b']:5.1f} "
              f"d={r['diff_pts']:+5.1f} disc {r['a_only']}-{r['b_only']} p={r['mcnemar_p']:.4f} "
              f"NC{r['ci_pts']} CL{r['cluster_ci_pts']} OR{r['cond_odds_ratio_ci']}")
    print("shipped", shipped["diff_pts"], shipped["ci_pts"], shipped["a_only"], shipped["b_only"])
    print("ref rates", ref_rate, "headroom", headroom)
    for c in out["dilution_curve_pi05"]:
        print("  +task", c["added_task"], c["added_task_ref_rate"], "n", c["n_pairs"], "D", c["discordant"],
              c["diff_pts"], c["ci_pts"], c["cluster_ci_pts"])
    print("certify", out["certify"])
    for k, v in alt.items():
        print("alt", k, v["tasks"], v["n_pairs"], v["a_only"], v["b_only"], v["ci_pts"], v["cluster_ci_pts"])
    print(f"wrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
