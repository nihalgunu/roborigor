from pathlib import Path

import pytest

pytest.importorskip("scipy")

from helpers import make_record  # noqa: E402
from roborigor.stats.report import noloss_report  # noqa: E402


def _grid(outcomes_a, outcomes_b):
    """outcomes: {task_id: [bool per init]} for two settings on identical episodes."""
    a, b = [], []
    for t, row in outcomes_a.items():
        for i, ok in enumerate(row):
            a.append(make_record(task_id=t, init_id=i, success=ok, num_steps=1))
            b.append(make_record(task_id=t, init_id=i, success=outcomes_b[t][i], num_steps=10))
    return a, b


def test_saturated_tasks_certify_but_informative_do_not():
    n = 120
    outcomes_a = {t: [True] * n for t in range(6)}
    outcomes_b = {t: [True] * n for t in range(6)}
    # one informative task where the settings disagree often and evenly
    outcomes_a[8] = [i % 3 == 0 for i in range(n)]
    outcomes_b[8] = [i % 3 == 1 for i in range(n)]
    a, b = _grid(outcomes_a, outcomes_b)
    rep = noloss_report(a, b, informative_tasks=[8], n_boot=500)
    assert rep.all_tasks.verdict == "EQUIVALENT"
    assert rep.informative.verdict == "INCONCLUSIVE"
    assert rep.all_tasks.a_only == rep.informative.a_only  # solved tasks add no discordance
    assert any("supplied by tasks both settings solve" in line for line in rep.lines())


def test_real_cost_is_different():
    n = 200
    outcomes_a = {0: [i % 2 == 0 for i in range(n)]}
    outcomes_b = {0: [i % 10 != 0 for i in range(n)]}
    a, b = _grid(outcomes_a, outcomes_b)
    rep = noloss_report(a, b, n_boot=500)
    assert rep.all_tasks.verdict == "DIFFERENT"
    assert rep.failure_ratio > 1.5 and not rep.failure_ratio_within_bound


def test_duplicate_episodes_rejected():
    r = make_record(task_id=0, init_id=0)
    with pytest.raises(ValueError):
        noloss_report([r, r], [r])


def test_reproduces_paper_battery_contrast_when_records_present():
    root = Path(__file__).resolve().parents[1] / "artifact" / "v2_knobs"
    if not root.exists():
        pytest.skip("released records not present")
    from roborigor.core.schema import read_records

    recs = [r for f in sorted(root.glob("records_*.jsonl")) for r in read_records(str(f))]

    def pick(steps):
        seen, out = set(), []
        for r in recs:
            if r.num_steps == steps and r.exec_horizon == 10:
                key = (r.task_id, r.init_id, r.sampling_seed)
                if key not in seen:
                    seen.add(key)
                    out.append(r)
        return out

    rep = noloss_report(pick(1), pick(10), informative_tasks=[0, 2, 8, 9], n_boot=300)
    assert (rep.all_tasks.a_only, rep.all_tasks.b_only) == (23, 14)
    assert rep.all_tasks.verdict == "EQUIVALENT"
    assert rep.informative.verdict == "INCONCLUSIVE"
