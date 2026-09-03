import json

import pytest

from roborigor.cli import main
from roborigor.envs.libero import MAX_STEPS, _quat2axisangle
from roborigor.envs.libero_plus import load_classification, task_ids_for_axis

CONFIG = """
campaign: clitest
benchmark: libero
policy: {policy_id: mock, checkpoint: none}
suite: libero_10
output_dir: results/x
base:
  seeds: [7]
  n_trials_per_task: 5
arms:
  - name: control
  - name: ns2
    num_steps: 2
"""


def test_max_steps_verbatim():
    assert MAX_STEPS == {
        "libero_spatial": 220, "libero_object": 280, "libero_goal": 300,
        "libero_10": 520, "libero_90": 400,
    }


def test_quat2axisangle_zero_rotation():
    import numpy as np

    assert np.allclose(_quat2axisangle(np.array([0.0, 0.0, 0.0, 1.0])), 0.0)
    # 180-degree rotation about z
    aa = _quat2axisangle(np.array([0.0, 0.0, 1.0, 0.0]))
    assert np.allclose(np.linalg.norm(aa), np.pi, atol=1e-6)


def test_classification_loader_both_shapes(tmp_path):
    flat = {"task_a": {"category": "Camera Viewpoints", "level": "l2"},
            "task_b": {"axis": "Light Conditions", "difficulty": "l1"}}
    p = tmp_path / "flat.json"
    p.write_text(json.dumps(flat))
    out = load_classification(str(p))
    assert out["task_a"] == {"axis": "Camera Viewpoints", "level": "l2"}
    assert out["task_b"] == {"axis": "Light Conditions", "level": "l1"}

    inverted = {"Camera Viewpoints": {"l1": ["task_c"], "l2": ["task_d"]}}
    p2 = tmp_path / "inv.json"
    p2.write_text(json.dumps(inverted))
    out2 = load_classification(str(p2))
    assert out2["task_d"] == {"axis": "Camera Viewpoints", "level": "l2"}

    ids = task_ids_for_axis(out2, ["task_c", "task_x", "task_d"], "Camera Viewpoints")
    assert ids == [0, 2]
    assert task_ids_for_axis(out2, ["task_c", "task_d"], "Camera Viewpoints", "l2") == [1]


def test_classification_loader_real_fork_shape(tmp_path):
    # the shape actually shipped by sylvestf/LIBERO-plus (verified on box)
    real = {"libero_spatial": [
        {"id": 1, "name": "task_table_1", "category": "Background Textures", "difficulty_level": 2},
        {"id": 2, "name": "task_camera_3", "category": "Camera Viewpoints", "difficulty_level": 1},
    ]}
    p = tmp_path / "real.json"
    p.write_text(json.dumps(real))
    out = load_classification(str(p))
    assert out["task_table_1"] == {"axis": "Background Textures", "level": "2"}
    assert out["task_camera_3"] == {"axis": "Camera Viewpoints", "level": "1"}
    assert task_ids_for_axis(out, ["task_table_1", "task_camera_3"], "Camera Viewpoints") == [1]


def test_classification_loader_rejects_junk(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"a": "b"}')
    with pytest.raises(ValueError):
        load_classification(str(p))


def test_cli_validate_and_plan(tmp_path, capsys):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(CONFIG)
    assert main(["validate-config", str(cfg)]) == 0
    manifest_path = tmp_path / "m.json"
    assert main(["plan", str(cfg), "--boxes", "2", "--out", str(manifest_path)]) == 0
    out = capsys.readouterr().out
    assert "100 episodes" in out  # 2 arms x 10 tasks x 5 inits x 1 seed
    assert manifest_path.exists()


def test_cli_summarize_and_integrity(tmp_path, capsys):
    from helpers import MockEnv, MockPolicy

    from roborigor.core.config import load_campaign
    from roborigor.rollout.runner import run_work_items
    from roborigor.rollout.worklist import expand_campaign

    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(CONFIG)
    items = expand_campaign(load_campaign(str(cfg_path)), all_task_ids=[0, 1])
    out = tmp_path / "records_test.jsonl"
    run_work_items(items, MockEnv(n_tasks=2), MockPolicy(), str(out))
    assert main(["summarize", str(tmp_path)]) == 0
    s = json.loads(capsys.readouterr().out)
    assert s["n_total"] == len(items)
    assert main(["integrity", str(tmp_path)]) == 0


def test_cli_power(capsys):
    pytest.importorskip("scipy")
    assert main(["power", "--mde-at", "50", "--gap", "0.05"]) == 0
    out = capsys.readouterr().out
    assert "18.3 points" in out
    assert "424" in out


def test_cli_end_to_end_mock_campaign(tmp_path, capsys):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(CONFIG)
    manifest = tmp_path / "m.json"
    assert main(["plan", str(cfg), "--boxes", "1", "--out", str(manifest)]) == 0
    out_dir = tmp_path / "records"
    for w in range(2):
        assert main([
            "run-shard", "--manifest", str(manifest), "--box-id", "box0",
            "--out-dir", str(out_dir), "--env", "mock",
            "--n-workers", "2", "--worker-index", str(w),
        ]) == 0
    # rerun: resume finds nothing to do, appends zero new episodes
    assert main([
        "run-shard", "--manifest", str(manifest), "--box-id", "box0",
        "--out-dir", str(out_dir), "--env", "mock",
        "--n-workers", "2", "--worker-index", "0",
    ]) == 0
    capsys.readouterr()
    assert main(["integrity", str(out_dir), "--manifest", str(manifest)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] and report["n_cells"] == 100 and report["n_records"] == 100


def test_run_shard_arm_filter(tmp_path, capsys):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(CONFIG)
    manifest = tmp_path / "m.json"
    main(["plan", str(cfg), "--out", str(manifest)])
    out_dir = tmp_path / "records"
    assert main(["run-shard", "--manifest", str(manifest), "--box-id", "box0",
                 "--out-dir", str(out_dir), "--env", "mock", "--arm", "ns2"]) == 0
    from roborigor.core.schema import read_records
    recs = read_records(str(next(out_dir.glob("*.jsonl"))))
    assert len(recs) == 50 and all(r.num_steps == 2 for r in recs)
