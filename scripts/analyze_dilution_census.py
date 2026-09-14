"""Ceiling-dilution census over every paired comparison in the released grids.

For each pair of dial settings measured on the same episodes, compare the
verdict on the full eight-task battery with the verdict on the four tasks the
V1 design pre-classified as informative (development-scan success in
[0.5, 0.95]: tasks 0, 2, 8, 9; configs/v1_varcomp_pi05.yaml, 2026-08-18),
a classification fixed before any grid episode was run.

Verdicts per subset: EQUIV (Newcombe interval inside +/-5 points), DIFF
(exact McNemar p < 0.05), or INCONCLUSIVE.
Writes docs/paper-data/dilution_census.json.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

from roborigor.core.schema import read_records
from roborigor.stats.compare import PairedCounts, mcnemar_exact
from roborigor.stats.intervals import clopper_pearson, newcombe_diff, newcombe_paired_diff

ROOT = Path(__file__).resolve().parents[1]
INFORMATIVE = (0, 2, 8, 9)
MARGIN = 5.0


def load(d):
    return [r for f in sorted((ROOT / "results" / d).glob("records_*.jsonl"))
            for r in read_records(str(f))]


def cells(recs, policy, seed):
    """(steps, horizon) -> {(task, init, sampling_seed): success}, first wins."""
    out = {}
    for r in recs:
        if r.policy_id != policy or r.seed != seed or r.perturbation_axis is not None:
            continue
        cell = out.setdefault((r.num_steps, r.exec_horizon), {})
        cell.setdefault((r.task_id, r.init_id, r.sampling_seed), bool(r.success))
    return out


def verdict(a, b, tasks=None, margin=MARGIN, alpha=0.05):
    units = [u for u in set(a) & set(b) if tasks is None or u[0] in tasks]
    n = len(units)
    ka = sum(a[u] for u in units)
    kb = sum(b[u] for u in units)
    ao = sum(1 for u in units if a[u] and not b[u])
    bo = sum(1 for u in units if b[u] and not a[u])
    p = mcnemar_exact(PairedCounts(both_succeed=sum(1 for u in units if a[u] and b[u]),
                                   a_only=ao, b_only=bo,
                                   both_fail=sum(1 for u in units if not a[u] and not b[u])))
    both = sum(1 for u in units if a[u] and b[u])
    lo, hi = (100 * x for x in newcombe_paired_diff(both, ao, bo, n - both - ao - bo, alpha))
    ulo, uhi = (100 * x for x in newcombe_diff(ka, n, kb, n))
    if ao + bo:
        qlo, qhi = clopper_pearson(ao, ao + bo)
        odds = [round(qlo / (1 - qlo), 3) if qlo < 1 else None,
                round(qhi / (1 - qhi), 3) if qhi < 1 else None]
    else:
        odds = [None, None]
    # Paired Wald interval, the standard error written out in Sec. IV.
    d = (ao - bo) / n
    se = max((ao + bo) / n - d * d, 0.0) ** 0.5 / n ** 0.5
    plo, phi = 100 * (d - 1.96 * se), 100 * (d + 1.96 * se)

    def classify(l, h):
        if p < 0.05:
            return "DIFF"
        if l > -margin and h < margin:
            return "EQUIV"
        return "INCONCLUSIVE"
    v = classify(lo, hi)
    v_wald = classify(plo, phi)
    v_unpaired = classify(ulo, uhi)
    return {"n": n, "rate_a": round(ka / n, 4), "rate_b": round(kb / n, 4),
            "diff_pts": round(100 * (ka - kb) / n, 2), "a_only": ao, "b_only": bo,
            "p": p, "ci_pts": [round(lo, 2), round(hi, 2)], "odds_ci": odds, "verdict": v,
            "wald_ci_pts": [round(plo, 2), round(phi, 2)], "verdict_wald": v_wald,
            "unpaired_ci_pts": [round(ulo, 2), round(uhi, 2)], "verdict_unpaired": v_unpaired}


def census(grid, label):
    rows = []
    for ca, cb in combinations(sorted(grid, key=lambda c: (c[0] or 0, c[1])), 2):
        full = verdict(grid[ca], grid[cb])
        inf = verdict(grid[ca], grid[cb], INFORMATIVE)
        rows.append({"grid": label, "a": list(ca), "b": list(cb), "full": full, "informative": inf})
    return rows


def main():
    rows = []
    rows += census(cells(load("v2_knobs"), "pi05_libero", 7), "pi05_seed7")
    rows += census(cells(load("replication"), "pi05_libero", 8), "pi05_seed8")
    rows += census(cells(load("replication"), "pi0_libero", 7), "pi0_seed7")

    def tally(sel):
        from collections import Counter
        return Counter(f"{r['full']['verdict']}->{r['informative']['verdict']}" for r in sel)

    equiv_full = [r for r in rows if r["full"]["verdict"] == "EQUIV"]
    lost = [r for r in equiv_full if r["informative"]["verdict"] != "EQUIV"]
    diff_full = [r for r in rows if r["full"]["verdict"] == "DIFF"]
    out = {
        "informative_tasks": list(INFORMATIVE),
        "classification_source": "configs/v1_varcomp_pi05.yaml (2026-08-18), before any grid episode",
        "n_pairs": len(rows),
        "transitions": dict(tally(rows)),
        "n_equiv_full": len(equiv_full),
        "n_equiv_full_not_equiv_informative": len(lost),
        "n_equiv_full_diff_informative": sum(1 for r in equiv_full if r["informative"]["verdict"] == "DIFF"),
        "n_diff_full": len(diff_full),
        "n_diff_full_still_diff_informative": sum(1 for r in diff_full if r["informative"]["verdict"] == "DIFF"),
        "median_ci_width_full": sorted(r["full"]["ci_pts"][1] - r["full"]["ci_pts"][0] for r in rows)[len(rows) // 2],
        "median_ci_width_informative": sorted(r["informative"]["ci_pts"][1] - r["informative"]["ci_pts"][0] for r in rows)[len(rows) // 2],
        "by_grid": {g: dict(tally([r for r in rows if r["grid"] == g])) for g in sorted({r["grid"] for r in rows})},
        "rows": rows,
    }
    # Control for sample size: the informative subset is half the battery, so
    # compare it with the saturated half and with every other 4-of-8 task subset.
    grids = {"pi05_seed7": cells(load("v2_knobs"), "pi05_libero", 7),
             "pi05_seed8": cells(load("replication"), "pi05_libero", 8),
             "pi0_seed7": cells(load("replication"), "pi0_libero", 7)}
    all_tasks = (0, 1, 2, 3, 4, 6, 8, 9)
    saturated = tuple(t for t in all_tasks if t not in INFORMATIVE)
    subsets = list(combinations(all_tasks, 4))
    control = {"saturated_half": saturated, "n_four_task_subsets": len(subsets)}
    kept_sat, kept_by_subset = 0, []
    for sub in subsets:
        kept = 0
        for r in equiv_full:
            g = grids[r["grid"]]
            if verdict(g[tuple(r["a"])], g[tuple(r["b"])], sub)["verdict"] == "EQUIV":
                kept += 1
        kept_by_subset.append((sub, kept))
        if sub == saturated:
            kept_sat = kept
    ks = sorted(k for _, k in kept_by_subset)
    control.update({
        "equiv_kept_informative_half": sum(1 for r in equiv_full if r["informative"]["verdict"] == "EQUIV"),
        "equiv_kept_saturated_half": kept_sat,
        "equiv_kept_median_over_subsets": ks[len(ks) // 2],
        "equiv_kept_by_subset": [{"tasks": list(t), "kept": k} for t, k in kept_by_subset],
        "subsets_keeping_none": sum(1 for _, k in kept_by_subset if k == 0),
        "subsets_containing_task8_keeping_any": sum(1 for t, k in kept_by_subset if 8 in t and k > 0),
        "subsets_without_task8_median_kept": sorted(k for t, k in kept_by_subset if 8 not in t)[17],
        "subsets_with_task8_median_kept": sorted(k for t, k in kept_by_subset if 8 in t)[17],
    })
    out["size_control"] = control
    def sens(key, margin=MARGIN, alpha=0.05):
        eq = [r for r in rows
              if verdict(grids[r["grid"]][tuple(r["a"])], grids[r["grid"]][tuple(r["b"])],
                         None, margin, alpha)[key] == "EQUIV"]
        def kept(sub):
            return sum(1 for r in eq
                       if verdict(grids[r["grid"]][tuple(r["a"])], grids[r["grid"]][tuple(r["b"])],
                                  sub, margin, alpha)[key] == "EQUIV")
        return {"n_equiv_full": len(eq), "kept_informative": kept(INFORMATIVE),
                "kept_saturated": kept(saturated)}
    out["sensitivity"] = {
        "wald_pm5": sens("verdict_wald"),
        "unpaired_newcombe_pm5": sens("verdict_unpaired"),
        "paired_newcombe_pm3": sens("verdict", 3.0),
        "paired_newcombe_pm7": sens("verdict", 7.0),
        "paired_newcombe_90pct_pm5": sens("verdict", MARGIN, 0.10),
    }
    # Symmetric control for differences, multiplicity, and dependence of the certificates.
    diff_kept_sat = sum(
        1 for r in diff_full
        if verdict(grids[r["grid"]][tuple(r["a"])], grids[r["grid"]][tuple(r["b"])], saturated)["verdict"] == "DIFF")
    from roborigor.stats.compare import holm
    adj = holm([r["full"]["p"] for r in rows])
    cells_in_certs = {(r["grid"], tuple(r["a"])) for r in equiv_full} | {(r["grid"], tuple(r["b"])) for r in equiv_full}
    out["diff_kept_saturated_half"] = diff_kept_sat
    out["n_diff_full_holm"] = sum(1 for q in adj if q < 0.05)
    out["certificates_by_grid"] = {g: sum(1 for r in equiv_full if r["grid"] == g) for g in grids}
    out["certificates_distinct_cells"] = len(cells_in_certs)
    print("diff kept saturated", diff_kept_sat, "holm diff", out["n_diff_full_holm"],
          "certs by grid", out["certificates_by_grid"], "distinct cells", len(cells_in_certs))
    def kind(r):
        (sa, ha), (sb, hb) = r["a"], r["b"]
        if ha == hb:
            return "steps"
        if sa == sb:
            return "horizon"
        return "both"
    from collections import Counter
    out["by_contrast_kind"] = {
        k: {"n": sum(1 for r in rows if kind(r) == k),
            "equiv_full": sum(1 for r in equiv_full if kind(r) == k),
            "equiv_kept_informative": sum(1 for r in equiv_full if kind(r) == k
                                          and r["informative"]["verdict"] == "EQUIV"),
            "diff_full": sum(1 for r in diff_full if kind(r) == k),
            "diff_kept_informative": sum(1 for r in diff_full if kind(r) == k
                                         and r["informative"]["verdict"] == "DIFF")}
        for k in ("steps", "horizon", "both")}
    print("sensitivity", out["sensitivity"])
    print("by kind", out["by_contrast_kind"])
    print("control", {k: v for k, v in control.items() if k != "equiv_kept_by_subset"})
    dest = ROOT / "docs/paper-data/dilution_census.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    for k in ("n_pairs", "transitions", "n_equiv_full", "n_equiv_full_not_equiv_informative",
              "n_equiv_full_diff_informative", "n_diff_full", "n_diff_full_still_diff_informative",
              "median_ci_width_full", "median_ci_width_informative", "by_grid"):
        print(k, out[k])
    for r in equiv_full:
        print(r["grid"], r["a"], r["b"], r["full"]["ci_pts"], "->", r["informative"]["verdict"],
              r["informative"]["ci_pts"], r["informative"]["a_only"], r["informative"]["b_only"])
    print(f"wrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
