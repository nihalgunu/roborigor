import dataclasses
import json
from pathlib import Path

import pytest

from roborigor.core.schema import (
    SCHEMA_VERSION,
    EpisodeRecord,
    cell_key,
    read_records,
    summarize,
    wilson_ci95,
    write_record,
)

DATA = Path(__file__).parent / "data" / "baseline_sample.jsonl"


from helpers import make_record as rec  # noqa: E402


def test_v1_baseline_records_promote():
    records = read_records(str(DATA))
    assert len(records) == 10
    r = records[0]
    assert r.suite == "libero_10" and r.seed == 7
    # v2 defaults filled in
    assert r.policy_id == "" and r.sampling_seed is None
    assert r.exec_horizon == r.replan_steps == 5


def test_roundtrip(tmp_path):
    p = tmp_path / "records.jsonl"
    r = rec(policy_id="pi05_libero", sampling_seed=3, num_steps=2,
            perturbation_axis="camera", perturbation_level="l1")
    write_record(str(p), r)
    write_record(str(p), rec(init_id=1))
    out = read_records(str(p))
    assert out[0] == r
    assert out[1].init_id == 1


def test_torn_final_line_skipped(tmp_path):
    p = tmp_path / "records.jsonl"
    write_record(str(p), rec())
    with open(p, "a") as f:
        f.write('{"suite": "libero_10", "task_id": ')  # killed mid-write
    assert len(read_records(str(p))) == 1


def test_torn_middle_line_raises(tmp_path):
    p = tmp_path / "records.jsonl"
    with open(p, "w") as f:
        f.write("not json\n")
        f.write(rec().to_json() + "\n")
    with pytest.raises(json.JSONDecodeError):
        read_records(str(p))


def test_unknown_fields_tolerated(tmp_path):
    p = tmp_path / "records.jsonl"
    raw = json.loads(rec().to_json())
    raw["from_the_future"] = 42
    p.write_text(json.dumps(raw) + "\n")
    assert read_records(str(p))[0].suite == "libero_10"


def test_cell_key_pairing():
    a = rec(policy_id="a")
    b = rec(policy_id="b")
    assert cell_key(a) != cell_key(b)
    assert cell_key(a)[3:] == cell_key(b)[3:]  # same cell apart from policy: pairable
    assert cell_key(rec()) == cell_key(rec())


def test_exec_horizon_defaults_to_replan():
    assert rec(replan_steps=3).exec_horizon == 3
    assert rec(exec_horizon=1).exec_horizon == 1


def test_wilson_matches_baseline_summary():
    # 492/500 on libero_goal from the 2026-08-15 baseline summary.json
    lo, hi = wilson_ci95(492, 500)
    assert abs(lo - 0.9687488913091183) < 1e-9
    assert abs(hi - 0.9918707470085563) < 1e-9


def test_summarize_shape_and_duplicates():
    records = [rec(init_id=i) for i in range(4)] + [rec(init_id=0)]  # one duplicate
    s = summarize(records)
    assert s["schema_version"] == SCHEMA_VERSION
    suite = s["suites"]["libero_10"]
    assert suite["n"] == 5 and suite["successes"] == 5
    assert suite["duplicate_inits"] == 1
    assert s["overall"]["n"] == 5
    clean = summarize([rec(init_id=i) for i in range(3)])
    assert clean["suites"]["libero_10"]["duplicate_inits"] is None


def test_record_field_order_backward_compatible():
    # The 13 baseline field names come first and keep their names.
    names = [f.name for f in dataclasses.fields(EpisodeRecord)][:13]
    assert names == [
        "suite", "task_id", "task_description", "init_id", "seed", "success",
        "wall_s", "n_chunks", "n_env_steps", "client_infer_s_total",
        "server_infer_s_total", "replan_steps", "max_steps",
    ]
