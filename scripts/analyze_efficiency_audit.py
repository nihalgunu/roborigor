"""Outcomes O1-O8 of docs/efficiency-audit-protocol.md.

Reads docs/efficiency_audit/extraction.jsonl (one object per screened
candidate) and writes docs/paper-data/efficiency_audit.json.

Rates are fractions. Counts use the episodes stated for each arm; claims
without a usable count are excluded from O7 only.
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

from scipy import stats as st

from roborigor.stats.intervals import newcombe_diff

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs/efficiency_audit/extraction.jsonl"
MARGIN = 0.05


def failure_ratio_ci(rate_m, n_m, rate_b, n_b):
    """Katz log interval for (method failures / base failures), 0.5-corrected at zero."""
    x_m, x_b = (1 - rate_m) * n_m, (1 - rate_b) * n_b
    if x_m == 0 or x_b == 0:
        x_m, x_b, n_m, n_b = x_m + 0.5, x_b + 0.5, n_m + 0.5, n_b + 0.5
    ratio = (x_m / n_m) / (x_b / n_b)
    se = math.sqrt(max(1 / x_m - 1 / n_m + 1 / x_b - 1 / n_b, 0.0))
    return ratio, ratio * math.exp(-1.96 * se), ratio * math.exp(1.96 * se)


def main():
    rows = [json.loads(line) for line in open(SRC) if line.strip()]
    inc = [r for r in rows if r["screen"]["include"]]
    strict = [r for r in rows if r["screen"].get("strict_improvement_only")]
    claims_all = [r["claim"] for r in inc]
    # Claims whose rates appear only in figures are counted but excluded from rate-based outcomes.
    claims = [c for c in claims_all if c and c.get("rate_base") is not None and c.get("rate_method") is not None]

    def share(pred, pool):
        k = sum(1 for c in pool if pred(c))
        return {"k": k, "n": len(pool), "pct": round(100 * k / len(pool), 1) if pool else None}

    gaps = [100 * (c["rate_method"] - c["rate_base"]) for c in claims]
    ratios = [failure_ratio_ci(c["rate_method"], 1, c["rate_base"], 1)[0]
              for c in claims if c["rate_base"] < 1]

    usable = [c for c in claims if c.get("n_total_base") and c.get("n_total_method")]
    o7 = []
    for c in usable:
        n_b, n_m = int(c["n_total_base"]), int(c["n_total_method"])
        k_b, k_m = round(c["rate_base"] * n_b), round(c["rate_method"] * n_m)
        lo, hi = newcombe_diff(k_m, n_m, k_b, n_b)
        ratio, rlo, rhi = failure_ratio_ci(k_m / n_m, n_m, k_b / n_b, n_b)
        o7.append({"certifiable_pm5": lo > -MARGIN and hi < MARGIN, "ratio": ratio,
                   "ratio_hi": rhi, "diff_ci_pts": [100 * lo, 100 * hi]})
    cert = [x for x in o7 if x["certifiable_pm5"]]

    # O8: within-paper, LIBERO vs a lower-base benchmark for the same comparison.
    pairs = []
    for r in inc:
        c = r["claim"]
        if not c or c.get("rate_base") is None or c.get("rate_method") is None:
            continue
        for ob in r.get("other_benchmarks") or []:
            if ob.get("rate_base") is None or ob.get("rate_method") is None:
                continue
            if ob["rate_base"] < 0.80 and ob["rate_base"] < c["rate_base"]:
                loss_lib = c["rate_base"] - c["rate_method"]
                loss_other = ob["rate_base"] - ob["rate_method"]
                fr_lib = failure_ratio_ci(c["rate_method"], 1, c["rate_base"], 1)[0] if c["rate_base"] < 1 else None
                fr_other = failure_ratio_ci(ob["rate_method"], 1, ob["rate_base"], 1)[0]
                pairs.append({"paper": r["id"], "benchmark": ob["benchmark"],
                              "loss_libero_pts": round(100 * loss_lib, 2),
                              "loss_other_pts": round(100 * loss_other, 2),
                              "fr_libero": fr_lib, "fr_other": fr_other})
                break  # one lower-base benchmark per paper: the first reported
    larger = sum(1 for p in pairs if p["loss_other_pts"] > p["loss_libero_pts"])
    smaller = sum(1 for p in pairs if p["loss_other_pts"] < p["loss_libero_pts"])
    sign_p = (st.binomtest(larger, larger + smaller, 0.5).pvalue if larger + smaller else None)

    out = {
        "n_screened": len(rows),
        "n_included": len(inc),
        "n_strict_improvement_only": len(strict),
        "n_included_without_rates": len(claims_all) - len(claims),
        "O1_base_ge_090": share(lambda c: c["rate_base"] >= 0.90, claims),
        "O2_uncertainty": share(lambda c: c.get("uncertainty_reported") is True, claims_all),
        "O3_per_task": share(lambda c: c.get("per_task_results") is True, claims_all),
        "O4_usable_n": share(lambda c: bool(c.get("n_total_base") and c.get("n_total_method")), claims_all),
        "O5_paired": share(lambda c: c.get("paired_info") is True, claims_all),
        "O1b_base_ge_095": share(lambda c: c["rate_base"] >= 0.95, claims),
        "any_uncertainty_or_per_task_or_paired": share(
            lambda c: c.get("uncertainty_reported") is True or c.get("per_task_results") is True
            or c.get("paired_info") is True, claims_all),
        "O6_median_gap_pts": round(statistics.median(gaps), 2) if gaps else None,
        "O6_median_failure_ratio": round(statistics.median(ratios), 3) if ratios else None,
        "O7": {"n_usable": len(o7), "n_certifiable_pm5": len(cert),
               "n_certifiable_but_ratio_hi_ge_1_5": sum(1 for x in cert if x["ratio_hi"] >= 1.5)},
        "O8": {"n_papers_with_lower_base_benchmark": len(pairs), "loss_larger_on_lower_base": larger,
               "loss_smaller_on_lower_base": smaller, "sign_test_p": sign_p, "pairs": pairs},
        "method_families": sorted({r.get("method_family") for r in inc if r.get("method_family")}),
    }
    dest = ROOT / "docs/paper-data/efficiency_audit.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "O8"}, indent=1))
    print("O8", {k: v for k, v in out["O8"].items() if k != "pairs"})
    print(f"wrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
