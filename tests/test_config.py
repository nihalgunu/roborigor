
import pytest

from roborigor.core.config import Arm, Cell, load_campaign, resolve_cell, to_dict

VALID = """
campaign: pilot
benchmark: libero
policy:
  policy_id: pi05_libero
  checkpoint: gs://openpi-assets/checkpoints/pi05_libero
suite: libero_10
output_dir: results/pilot
base:
  seeds: [7, 8, 9]
  sampling_seeds: [0]
  n_trials_per_task: 10
arms:
  - name: control
  - name: ns2
    num_steps: 2
  - name: perturbed
    perturbation_axis: camera
    perturbation_level: l1
"""


def write(tmp_path, text):
    p = tmp_path / "c.yaml"
    p.write_text(text)
    return str(p)


def test_valid_loads(tmp_path):
    cfg = load_campaign(write(tmp_path, VALID))
    assert cfg.policy.policy_id == "pi05_libero"
    assert [a.name for a in cfg.arms] == ["control", "ns2", "perturbed"]
    assert to_dict(cfg)["campaign"] == "pilot"


def test_arm_override_resolution(tmp_path):
    cfg = load_campaign(write(tmp_path, VALID))
    control = resolve_cell(cfg.base, cfg.arms[0])
    ns2 = resolve_cell(cfg.base, cfg.arms[1])
    assert control.num_steps is None and ns2.num_steps == 2
    assert ns2.seeds == [7, 8, 9]  # inherited


def test_missing_required(tmp_path):
    with pytest.raises(ValueError, match="missing required"):
        load_campaign(write(tmp_path, "campaign: x\nbenchmark: libero\n"))


def test_unknown_key_rejected(tmp_path):
    with pytest.raises(ValueError, match="unknown keys"):
        load_campaign(write(tmp_path, VALID + "\ngradient_scale: 2\n"))


def test_unknown_arm_key_rejected(tmp_path):
    bad = VALID.replace("num_steps: 2", "num_stepz: 2")
    with pytest.raises(ValueError, match="unknown keys"):
        load_campaign(write(tmp_path, bad))


def test_perturbation_needs_both(tmp_path):
    bad = VALID.replace("    perturbation_level: l1\n", "")
    with pytest.raises(ValueError, match="must be set together"):
        load_campaign(write(tmp_path, bad))


def test_default_control_arm(tmp_path):
    text = VALID.split("arms:")[0]
    cfg = load_campaign(write(tmp_path, text))
    assert [a.name for a in cfg.arms] == ["control"]


def test_duplicate_seeds_rejected(tmp_path):
    bad = VALID.replace("[7, 8, 9]", "[7, 7]")
    with pytest.raises(ValueError, match="duplicate seeds"):
        load_campaign(write(tmp_path, bad))


def test_resolve_cell_does_not_mutate_base():
    base = Cell(seeds=[7], num_steps=10)
    resolve_cell(base, Arm(name="a", overrides=Cell(num_steps=2)))
    assert base.num_steps == 10
