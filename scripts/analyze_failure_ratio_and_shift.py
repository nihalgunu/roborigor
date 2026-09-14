"""Failure-rate ratios, camera cost by shift level, and supporting checks, from released records.

  * failure-rate ratio (one step / ten steps) with an init-cluster bootstrap
    interval for every Table I contrast, and verdicts at an illustrative
    non-inferiority bound of 1.5;
  * SmolVLA horizon contrast (h=1 vs h=10) with the paired Newcombe interval;
  * census breakdown of significant differences by contrast kind and the rank
    of the informative half among the 70 four-task subsets;
  * the camera cost by LIBERO-Plus perturbation level;
  * failure timing on discordant pairs (task 8 and camera); note LIBERO ends
    episodes early only on success, so every failure runs to max_steps and
    this field is uninformative by construction (not used in the paper);
  * per-task discordant counts for environment seeds 7 and 8.

Writes docs/paper-data/failure_ratio_and_shift.json.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from roborigor.core.schema import read_records
from roborigor.stats.compare import PairedCounts, mcnemar_exact
from roborigor.stats.intervals import newcombe_paired_diff

ROOT = Path(__file__).resolve().parents[1]
RATIO_BOUND = 1.5
N_BOOT = 4000


def load(*dirs):
    return [r for d in dirs for f in sorted((ROOT / "results" / d).rglob("records_*.jsonl"))
            for r in read_records(str(f))]


def arm(recs, policy, steps, horizon, seed=7, axis=None):
    out = {}
    for r in recs:
        if (r.policy_id, r.seed, r.num_steps, r.exec_horizon, r.perturbation_axis) != \
                (policy, seed, steps, horizon, axis):
            continue
        key = (r.task_id, r.init_id, r.sampling_seed, r.perturbation_level, r.replicate)
        out.setdefault(key, r)
    return out


def failure_ratio(a, b, tasks=None):
    units = sorted((u for u in set(a) & set(b) if tasks is None or u[0] in tasks), key=str)
    fa = sum(1 for u in units if not a[u].success)
    fb = sum(1 for u in units if not b[u].success)
    clusters = defaultdict(list)
    for u in units:
        clusters[(u[0], u[1], u[3])].append((not a[u].success, not b[u].success))
    keys = list(clusters)
    rng = random.Random(0)
    boots = []
    for _ in range(N_BOOT):
        xa = xb = 0
        for k in (rng.choice(keys) for _ in keys):
            for pa, pb in clusters[k]:
                xa += pa
                xb += pb
        boots.append((xa + 0.5) / (xb + 0.5))
    boots.sort()
    lo, hi = boots[int(0.025 * N_BOOT)], boots[int(0.975 * N_BOOT) - 1]
    return {"fail_a": fa, "fail_b": fb, "ratio": round(fa / fb, 3) if fb else None,
            "ci": [round(lo, 3), round(hi, 3)], "noninferior_at_1_5": hi < RATIO_BOUND}


def main():
    grid, rep = load("v2_knobs"), load("replication")
    cam, lay = load("camconf"), load("fusion")
    smol = load("smolgrid", "gapfill", "eh1")
    informative = {0, 2, 8, 9}

    rows = {
        "pi05_battery": failure_ratio(arm(grid, "pi05_libero", 1, 10), arm(grid, "pi05_libero", 10, 10)),
        "pi05_informative": failure_ratio(arm(grid, "pi05_libero", 1, 10), arm(grid, "pi05_libero", 10, 10),
                                          informative),
        "pi05_envseed8": failure_ratio(arm(rep, "pi05_libero", 1, 10, 8), arm(rep, "pi05_libero", 10, 10, 8)),
        "pi05_layout_shift": failure_ratio(arm(lay, "pi05_libero", 1, 10, axis="Objects Layout"),
                                           arm(lay, "pi05_libero", 10, 10, axis="Objects Layout")),
        "pi05_camera_confirmatory": failure_ratio(arm(cam, "pi05_libero", 1, 10, axis="Camera Viewpoints"),
                                                  arm(cam, "pi05_libero", 10, 10, axis="Camera Viewpoints")),
        "smolvla_battery": failure_ratio(arm(smol, "smolvla_libero", 1, 10), arm(smol, "smolvla_libero", None, 10)),
        "pi0_battery": failure_ratio(arm(rep, "pi0_libero", 1, 10), arm(rep, "pi0_libero", 10, 10)),
    }

    # SmolVLA horizon, paired.
    h1, h10 = arm(smol, "smolvla_libero", None, 1), arm(smol, "smolvla_libero", None, 10)
    units = [u for u in set(h1) & set(h10)]
    both = sum(1 for u in units if h1[u].success and h10[u].success)
    a1 = sum(1 for u in units if h1[u].success and not h10[u].success)
    a10 = sum(1 for u in units if h10[u].success and not h1[u].success)
    lo, hi = newcombe_paired_diff(both, a10, a1, len(units) - both - a1 - a10)
    smol_h = {"n": len(units), "h10_only": a10, "h1_only": a1,
              "diff_pts": round(100 * (a10 - a1) / len(units), 2),
              "ci_pts": [round(100 * lo, 2), round(100 * hi, 2)],
              "p": mcnemar_exact(PairedCounts(both, a10, a1, len(units) - both - a1 - a10))}

    # Camera cost by perturbation level.
    ca, cb = arm(cam, "pi05_libero", 1, 10, axis="Camera Viewpoints"), arm(cam, "pi05_libero", 10, 10, axis="Camera Viewpoints")
    by_level = {}
    for lev in sorted({u[3] for u in ca}):
        us = [u for u in set(ca) & set(cb) if u[3] == lev]
        s1 = sum(ca[u].success for u in us)
        s10 = sum(cb[u].success for u in us)
        w1 = sum(1 for u in us if ca[u].success and not cb[u].success)
        w10 = sum(1 for u in us if cb[u].success and not ca[u].success)
        by_level[lev] = {"n": len(us), "sr_s1": round(s1 / len(us), 3), "sr_s10": round(s10 / len(us), 3),
                         "s1_only": w1, "s10_only": w10}

    # Camera contrast pooled over the benchmark's easier (1-3) and harder (4-5) levels.
    from roborigor.stats.report import noloss_report
    cam_recs = [r for r in cam if r.perturbation_axis == "Camera Viewpoints"]
    camera_groups = {}
    for name, levels in (("levels_1_3", {"1", "2", "3"}), ("levels_4_5", {"4", "5"})):
        rep_ = noloss_report([r for r in cam_recs if r.num_steps == 1 and r.perturbation_level in levels],
                             [r for r in cam_recs if r.num_steps == 10 and r.perturbation_level in levels],
                             n_boot=1000)
        c_ = rep_.all_tasks
        camera_groups[name] = {"n": c_.n_pairs, "rate_s1": round(c_.rate_a, 4), "rate_s10": round(c_.rate_b, 4),
                               "diff_pts": round(c_.diff_pts, 2), "ci_pts": [round(x, 2) for x in c_.ci_pts],
                               "s1_only": c_.a_only, "s10_only": c_.b_only, "p": c_.mcnemar_p,
                               "verdict": c_.verdict}

    # Failure timing on discordant pairs: does the losing arm time out or fail early?
    def timing(a, b):
        out = {"loser_timeouts": 0, "loser_early": 0, "winner_steps_median": None}
        losers, winners = [], []
        for u in set(a) & set(b):
            if a[u].success != b[u].success:
                lose = a[u] if not a[u].success else b[u]
                win = b[u] if not a[u].success else a[u]
                losers.append(lose)
                winners.append(win.n_env_steps)
        out["n_discordant"] = len(losers)
        out["loser_timeouts"] = sum(1 for r in losers if r.n_env_steps >= r.max_steps)
        out["loser_early"] = len(losers) - out["loser_timeouts"]
        winners.sort()
        out["winner_steps_median"] = winners[len(winners) // 2] if winners else None
        return out

    g1 = {u: r for u, r in arm(grid, "pi05_libero", 1, 10).items() if u[0] == 8}
    g10 = {u: r for u, r in arm(grid, "pi05_libero", 10, 10).items() if u[0] == 8}
    timing_out = {"pi05_task8": timing(g1, g10), "pi05_camera": timing(ca, cb)}

    # Per-task discordants for env seeds 7 and 8.
    def per_task(a, b):
        d = defaultdict(lambda: [0, 0])
        for u in set(a) & set(b):
            if a[u].success and not b[u].success:
                d[u[0]][0] += 1
            elif b[u].success and not a[u].success:
                d[u[0]][1] += 1
        return {str(t): v for t, v in sorted(d.items())}
    seeds = {"seed7": per_task(arm(grid, "pi05_libero", 1, 10), arm(grid, "pi05_libero", 10, 10)),
             "seed8": per_task(arm(rep, "pi05_libero", 1, 10, 8), arm(rep, "pi05_libero", 10, 10, 8))}

    # Census: differences by kind, rank of informative half.
    cen = json.load(open(ROOT / "docs/paper-data/dilution_census.json"))
    kept = sorted(row["kept"] for row in cen["size_control"]["equiv_kept_by_subset"])
    inf_kept = cen["size_control"]["equiv_kept_informative_half"]
    sat_kept = cen["size_control"]["equiv_kept_saturated_half"]
    census = {
        "informative_half_is_unique_min": kept.count(inf_kept) == 1 and inf_kept == kept[0],
        "n_subsets_at_or_below_informative": sum(1 for k in kept if k <= inf_kept),
        "n_subsets_above_saturated": sum(1 for k in kept if k > sat_kept),
        "n_subsets_at_or_above_saturated": sum(1 for k in kept if k >= sat_kept),
        "diff_by_kind": {k: {"diff_full": v["diff_full"], "diff_kept_informative": v["diff_kept_informative"]}
                         for k, v in cen["by_contrast_kind"].items()},
    }

    lat = {(c["num_steps"], c["exec_horizon"]): c for c in
           json.load(open(ROOT / "docs/paper-data/v2_knob_table.json"))["cells"]}
    latency = {"step_only_ratio_h10": round(lat[(10, 10)]["measured_latency_ms_per_step"]
                                            / lat[(1, 10)]["measured_latency_ms_per_step"], 2),
               "chunk_ms_s1_h10": round(lat[(1, 10)]["measured_chunk_ms"]),
               "chunk_ms_s10_h10": round(lat[(10, 10)]["measured_chunk_ms"])}

    out = {"ratio_bound": RATIO_BOUND, "failure_ratio": rows, "smolvla_horizon_paired": smol_h,
           "camera_by_level": by_level, "camera_level_groups": camera_groups, "failure_timing": timing_out, "seed_per_task_discordants": seeds,
           "census": census, "latency": latency}
    dest = ROOT / "docs/paper-data/failure_ratio_and_shift.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
