"""Seed sensitivity of the clean anchors used for the perturbation gaps.

The anchors and the perturbed runs are single draws at an uncontrolled
sampling seed. This recomputes the same anchor configuration across the ten
sampling seeds of the reseed sweep, so the paper can report where the anchor
sits in its own seed band. Logged as Entry 15 of the deviations log.

Writes docs/paper-data/anchor_seed_sensitivity.json.
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path

from roborigor.core.schema import read_records

ROOT = Path(__file__).resolve().parents[1]
ANCHOR_HORIZON = 5
ANCHOR_INITS = 20


def main():
    anchors = defaultdict(lambda: [0, 0])
    for path in sorted((ROOT / "results/clean_anchors").glob("*.jsonl")):
        for r in read_records(str(path)):
            anchors[r.policy_id][0] += r.success
            anchors[r.policy_id][1] += 1

    per_seed = defaultdict(lambda: [0, 0])
    for path in sorted((ROOT / "results/reseed").glob("*.jsonl")):
        for r in read_records(str(path)):
            if r.exec_horizon == ANCHOR_HORIZON and r.init_id is not None \
                    and r.init_id < ANCHOR_INITS:
                per_seed[r.sampling_seed][0] += r.success
                per_seed[r.sampling_seed][1] += 1

    rates = [100 * k / n for k, n in (per_seed[s] for s in sorted(per_seed))]
    anchor_pi05 = 100 * anchors["pi05_libero"][0] / anchors["pi05_libero"][1]
    anchor_pi0 = 100 * anchors["pi0_libero"][0] / anchors["pi0_libero"][1]

    out = {
        "anchors": {p: round(k / n, 4) for p, (k, n) in sorted(anchors.items())},
        "anchor_sampling_seed": "uncontrolled (null) in every anchor episode",
        "pi05_seed_band": {
            "rates_pct": [round(x, 1) for x in rates],
            "mean_pct": round(statistics.mean(rates), 2),
            # sample SD (ddof=1), matching every other seed-band SD reported
            "sd_pct": round(statistics.stdev(rates), 2),
            "min_pct": round(min(rates), 1),
            "max_pct": round(max(rates), 1),
            "anchor_pct": round(anchor_pi05, 1),
            "anchor_is_band_max": abs(max(rates) - anchor_pi05) < 0.05,
        },
        "clean_gap_pi05_minus_pi0": {
            "at_anchor_pts": round(anchor_pi05 - anchor_pi0, 1),
            "at_seed_mean_pts": round(statistics.mean(rates) - anchor_pi0, 1),
        },
    }
    dest = ROOT / "docs/paper-data/anchor_seed_sensitivity.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    print(f"\nwrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
