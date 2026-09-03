"""Stage-0 gate: the full 2026-08-15 baseline round-trips and re-summarizes.

Needs the private baseline dataset, so it is skipped unless
HARNESS_BASELINE_DIR points at it. Never hardcode a local path here.
"""
import json
import os
from pathlib import Path

import pytest

from roborigor.core.schema import read_records, summarize

BASELINE = os.environ.get("HARNESS_BASELINE_DIR")

pytestmark = pytest.mark.skipif(
    not BASELINE, reason="HARNESS_BASELINE_DIR not set"
)


def test_full_baseline_roundtrip_and_summary():
    base = Path(BASELINE)
    files = sorted(base.glob("records_*.jsonl"))
    assert len(files) == 40
    records = [r for f in files for r in read_records(str(f))]
    assert len(records) == 2000

    ours = summarize(records)
    target = json.loads((base / "summary.json").read_text())

    assert ours["n_total"] == target["n_total"] == 2000
    for suite, tgt in target["suites"].items():
        got = ours["suites"][suite]
        for key, val in tgt.items():
            assert key in got, f"{suite}: missing {key}"
            if isinstance(val, float):
                assert abs(got[key] - val) < 1e-9, f"{suite}.{key}"
            elif isinstance(val, list) and val and isinstance(val[0], float):
                assert all(abs(a - b) < 1e-9 for a, b in zip(got[key], val)), f"{suite}.{key}"
            else:
                assert got[key] == val, f"{suite}.{key}"
    for key in ("n", "successes", "success_rate"):
        assert ours["overall"][key] == target["overall"][key]
