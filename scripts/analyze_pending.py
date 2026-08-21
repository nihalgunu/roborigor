"""Landing analyses for the three in-flight runs. Idempotent; run anytime."""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from roborigor.core.schema import read_records
from roborigor.stats.compare import PairedCounts, mcnemar_exact
from roborigor.stats.intervals import clopper_pearson, newcombe_diff

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/paper-data"


def load(d):
    return [r for f in sorted(Path(d).glob("records_*.jsonl")) for r in read_records(str(f))]


def reseed():
    recs = load(ROOT / "results/reseed")
    if len(recs) < 5000:
        print(f"reseed: {len(recs)}/5000, skipping")
        return
    by_seed = defaultdict(lambda: [0, 0])
    for r in recs:
        by_seed[r.sampling_seed][0] += r.success
        by_seed[r.sampling_seed][1] += 1
    rates = {s: 100 * k / n for s, (k, n) in sorted(by_seed.items())}
    vals = list(rates.values())
    pair_d = [abs(a - b) for a, b in combinations(vals, 2)]
    rep = {
        "protocol": "libero_10 standard: 10 tasks x 50 inits, env seed 7, ns=10 eh=5",
        "n_per_seed": {str(s): n for s, (k, n) in sorted(by_seed.items())},
        "rates_pct": {str(s): round(v, 2) for s, v in rates.items()},
        "spread_max_minus_min": round(max(vals) - min(vals), 2),
        "sd": round((sum((v - sum(vals)/len(vals))**2 for v in vals)/(len(vals)-1))**0.5, 2),
        "mean_abs_pairwise_delta": round(sum(pair_d)/len(pair_d), 2),
    }
    json.dump(rep, open(OUT / "reseed_std_protocol.json", "w"), indent=1)
    print("reseed:", json.dumps(rep)[:240])


def suites():
    recs = load(ROOT / "results/suite_scan")
    if len(recs) < 600:
        print(f"suite_scan: {len(recs)}/600, skipping")
        return
    per = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in recs:
        per[r.suite][r.task_id][0] += r.success
        per[r.suite][r.task_id][1] += 1
    rep = {}
    for suite, tasks in sorted(per.items()):
        rates = {t: k / n for t, (k, n) in sorted(tasks.items())}
        mid = [t for t, p in rates.items() if 0.5 <= p <= 0.95]
        rep[suite] = {"per_task": {str(t): round(p, 3) for t, p in rates.items()},
                      "informative_band_tasks": mid}
    json.dump(rep, open(OUT / "suite_saturation_scan.json", "w"), indent=1)
    for s, v in rep.items():
        print(f"{s}: informative tasks = {v['informative_band_tasks']}")


def fusion():
    base = ROOT / "results/fusion"
    data = {}
    for ns in (1, 2, 10):
        recs = load(base / f"ns{ns}")
        if len(recs) < 688:
            print(f"fusion ns{ns}: {len(recs)}/688, skipping all")
            return
        data[ns] = recs
    rep = {"per_axis": {}, "equivalence_vs_ns10": {}}
    for axis in ("Camera Viewpoints", "Objects Layout"):
        rep["per_axis"][axis] = {}
        for ns, recs in data.items():
            sub = [r for r in recs if r.perturbation_axis == axis]
            k = sum(r.success for r in sub)
            lo, hi = clopper_pearson(k, len(sub))
            rep["per_axis"][axis][f"ns{ns}"] = {
                "sr": round(k / len(sub), 4), "n": len(sub),
                "ci95": [round(lo, 4), round(hi, 4)]}
    def key(r):
        return (r.task_id, r.init_id)
    for ns in (1, 2):
        a = {key(r): r.success for r in data[ns]}
        b = {key(r): r.success for r in data[10]}
        ks = set(a) & set(b)
        n10 = sum(a[k2] and not b[k2] for k2 in ks)
        n01 = sum(not a[k2] and b[k2] for k2 in ks)
        n11 = sum(a[k2] and b[k2] for k2 in ks)
        n00 = len(ks) - n10 - n01 - n11
        p = mcnemar_exact(PairedCounts(n11, n10, n01, n00))
        ka, kb = sum(a[k2] for k2 in ks), sum(b[k2] for k2 in ks)
        ci = newcombe_diff(ka, len(ks), kb, len(ks))
        rep["equivalence_vs_ns10"][f"ns{ns}"] = {
            "pairs": len(ks), "mcnemar_p": round(p, 4),
            "diff_pct_ci95": [round(ci[0]*100, 2), round(ci[1]*100, 2)],
            "tost_pm5": bool(ci[0] > -0.05 and ci[1] < 0.05)}
    json.dump(rep, open(OUT / "fusion_shift.json", "w"), indent=1)
    print("fusion:", json.dumps(rep["equivalence_vs_ns10"]))


if __name__ == "__main__":
    reseed()
    suites()
    fusion()
