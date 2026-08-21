"""Literature-audit recomputation, per the frozen pre-registration section 4.

For every comparison with recoverable n: two-sided Boschloo exact p (Fisher
alongside) at the reported rates and stated n, and the MDE at 80 percent
power for that comparison's n and baseline rate. Comparisons whose n is
NOT-REPORTED or AMBIGUOUS are excluded from recomputation and counted in
the non-reporting and ambiguity rates, which are primary outcomes.

When only one side's n is known (X author-run, Y copied from another
paper), the comparison is recomputed at the known n for both sides and
flagged asymmetric_n: generous to the claim if the unknown side ran fewer.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_extractions(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def recompute(rows: list[dict], alpha: float = 0.05) -> dict:
    from roborigor.stats.compare import boschloo, fisher
    from roborigor.stats.intervals import newcombe_diff
    from roborigor.stats.power import mde_unpaired

    results = []
    n_unusable = 0
    n_total = 0
    for row in rows:
        for c in row["comparisons"]:
            n_total += 1
            if c["n_unit"] in ("NOT-REPORTED", "AMBIGUOUS"):
                n_unusable += 1
                continue
            n_x, n_y = c["n_x"], c["n_y"]
            n = n_x or n_y
            n_other = n_y or n_x
            if n is None:
                n_unusable += 1
                continue
            k_x = round(c["rate_x"] * n)
            k_y = round(c["rate_y"] * n_other)
            p_fisher = fisher(k_x, n, k_y, n_other)
            # Deviations log entry 1 (2026-08-19): Boschloo enumerated
            # exactly only when min(n) <= 200; beyond that it is
            # computationally infeasible and coincides with Fisher to
            # numerical precision, so Fisher is primary there and flagged.
            if min(n, n_other) <= 200:
                p_primary = boschloo(k_x, n, k_y, n_other)
                primary_test = "boschloo"
            else:
                p_primary = p_fisher
                primary_test = "fisher_large_n"
            out = {
                "paper": row["paper"],
                "idx": c["idx"],
                "benchmark": c["benchmark"],
                "gap_points": round(100 * (c["rate_x"] - c["rate_y"]), 1),
                "n": n,
                "asymmetric_n": (n_x is None) != (n_y is None),
                "p_primary": round(p_primary, 5),
                "primary_test": primary_test,
                "p_fisher": round(p_fisher, 5),
            }
            out["significant_05"] = out["p_primary"] < alpha
            base = max(c["rate_x"], c["rate_y"])
            try:
                out["mde_points"] = round(100 * mde_unpaired(min(n, n_other), min(base, 0.999)), 1)
                out["gap_below_mde"] = abs(out["gap_points"]) < out["mde_points"]
            except ValueError:
                out["mde_points"] = None
                out["gap_below_mde"] = None
            ci = newcombe_diff(k_x, n, k_y, n_other)
            out["diff_ci95"] = [round(ci[0], 4), round(ci[1], 4)]
            results.append(out)

    n_recomputed = len(results)
    n_nonsig = sum(1 for r in results if not r["significant_05"])
    n_below_mde = sum(1 for r in results if r["gap_below_mde"])
    return {
        "n_papers": len(rows),
        "n_comparisons": n_total,
        "n_unusable_n": n_unusable,
        "unusable_rate": round(n_unusable / n_total, 3) if n_total else None,
        "n_recomputed": n_recomputed,
        "n_not_significant": n_nonsig,
        "share_not_significant": round(n_nonsig / n_recomputed, 3) if n_recomputed else None,
        "n_gap_below_mde": n_below_mde,
        "share_below_mde": round(n_below_mde / n_recomputed, 3) if n_recomputed else None,
        "comparisons": results,
    }
