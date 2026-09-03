"""Campaign configuration: one YAML fully specifies a rollout campaign.

A campaign is a base cell plus an explicit list of arms. Each arm names the
factor settings it overrides; everything else inherits from base. Explicit
arms, not blind cross-products: variance-decomposition designs and one-factor
sweeps are both expressible, and the episode count is always inspectable
before anything runs.

Unknown keys are a hard error at every level. validate() returns a list of
human-readable problems rather than raising, and the loader joins them.

Python 3.8 compatible: imported in the LIBERO client process.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import yaml

KNOWN_BENCHMARKS = ("libero", "libero_plus", "robocasa")
KNOWN_LIBERO_SUITES = ("libero_spatial", "libero_object", "libero_goal", "libero_10")


@dataclasses.dataclass
class PolicyConfig:
    """Which policy server to evaluate."""

    policy_id: str  # registry id, e.g. "pi05_libero", "smolvla_libero"
    checkpoint: str  # path, hf id, or gs:// URI
    server_host: str = "127.0.0.1"
    server_port: int = 8000


@dataclasses.dataclass
class Cell:
    """Factor settings shared by every episode in an arm.

    None means "inherit" in an arm override, and "policy or benchmark default"
    in the resolved cell (num_steps, exec_horizon, task_ids, init_ids).
    sampling_seeds of [None] means the flow noise seed is left uncontrolled.
    """

    seeds: list[int] | None = None  # environment seeds
    sampling_seeds: list[int | None] | None = None
    num_steps: int | None = None  # denoising steps
    exec_horizon: int | None = None  # env steps executed per chunk before replan
    task_ids: list[int] | None = None  # None = all tasks in the suite
    init_ids: list[int] | None = None  # None = first n_trials_per_task inits
    n_trials_per_task: int | None = None
    perturbation_axis: str | None = None  # None = clean
    perturbation_level: str | None = None
    replicates: int | None = None  # repeats at identical factors, for residual estimation


@dataclasses.dataclass
class Arm:
    """A named point in the design: base cell with these overrides applied."""

    name: str
    overrides: Cell = dataclasses.field(default_factory=Cell)


@dataclasses.dataclass
class CampaignConfig:
    campaign: str  # short name; prefixes run_id
    benchmark: str
    policy: PolicyConfig
    suite: str
    output_dir: str
    base: Cell
    arms: list[Arm] = dataclasses.field(default_factory=list)
    max_steps: int | None = None  # None = benchmark default per task
    notes: str = ""

    def validate(self) -> list[str]:
        """Return a list of human-readable problems; empty list means valid."""
        problems = []
        if not self.campaign:
            problems.append("campaign name must be non-empty")
        if self.benchmark not in KNOWN_BENCHMARKS:
            problems.append(
                f"unknown benchmark {self.benchmark!r}; expected one of {KNOWN_BENCHMARKS}"
            )
        if self.benchmark == "libero" and self.suite not in KNOWN_LIBERO_SUITES:
            problems.append(
                f"unknown libero suite {self.suite!r}; expected one of {KNOWN_LIBERO_SUITES}"
            )
        if not self.base.seeds:
            problems.append("base.seeds must be non-empty; headline numbers require >= 3 seeds")
        elif len(set(self.base.seeds)) != len(self.base.seeds):
            problems.append(f"duplicate seeds: {self.base.seeds}")
        n = self.base.n_trials_per_task
        if n is not None and n <= 0:
            problems.append("base.n_trials_per_task must be positive")
        if not self.arms:
            problems.append("arms must be non-empty; a single control arm is the minimum")
        names = [a.name for a in self.arms]
        if len(set(names)) != len(names):
            problems.append(f"duplicate arm names: {names}")
        for arm in self.arms:
            if not arm.name:
                problems.append("every arm needs a non-empty name")
            cell = resolve_cell(self.base, arm)
            if (cell.perturbation_axis is None) != (cell.perturbation_level is None):
                problems.append(
                    f"arm {arm.name!r}: perturbation_axis and perturbation_level "
                    "must be set together or not at all"
                )
            if cell.num_steps is not None and cell.num_steps <= 0:
                problems.append(f"arm {arm.name!r}: num_steps must be positive or null")
            if cell.exec_horizon is not None and cell.exec_horizon <= 0:
                problems.append(f"arm {arm.name!r}: exec_horizon must be positive or null")
        return problems


def resolve_cell(base: Cell, arm: Arm) -> Cell:
    """base with the arm's non-None overrides applied."""
    merged = dataclasses.replace(base)
    for f in dataclasses.fields(Cell):
        v = getattr(arm.overrides, f.name)
        if v is not None:
            setattr(merged, f.name, v)
    return merged


def _check_unknown(raw: dict, cls: type, where: str) -> None:
    known = {f.name for f in dataclasses.fields(cls)}
    unknown = raw.keys() - known
    if unknown:
        raise ValueError(f"{where}: unknown keys: {sorted(unknown)}")


def _cell_from(raw: dict, where: str) -> Cell:
    _check_unknown(raw, Cell, where)
    return Cell(**raw)


def load_campaign(path: str) -> CampaignConfig:
    """Load and structurally validate a YAML campaign config. Raises ValueError."""
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: top level must be a mapping")

    required = {"campaign", "benchmark", "policy", "suite", "output_dir", "base"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"{path}: missing required keys: {sorted(missing)}")
    _check_unknown(raw, CampaignConfig, path)
    _check_unknown(raw["policy"], PolicyConfig, f"{path}: policy")

    arms_raw = raw.get("arms") or [{"name": "control"}]
    arms = []
    for i, a in enumerate(arms_raw):
        if not isinstance(a, dict) or "name" not in a:
            raise ValueError(f"{path}: arms[{i}] must be a mapping with a 'name'")
        overrides = {k: v for k, v in a.items() if k != "name"}
        arms.append(Arm(name=a["name"], overrides=_cell_from(overrides, f"{path}: arms[{i}]")))

    cfg = CampaignConfig(
        campaign=raw["campaign"],
        benchmark=raw["benchmark"],
        policy=PolicyConfig(**raw["policy"]),
        suite=raw["suite"],
        output_dir=raw["output_dir"],
        base=_cell_from(raw["base"], f"{path}: base"),
        arms=arms,
        max_steps=raw.get("max_steps"),
        notes=raw.get("notes", ""),
    )
    problems = cfg.validate()
    if problems:
        raise ValueError(f"{path}: invalid config:\n  - " + "\n  - ".join(problems))
    return cfg


def to_dict(cfg: CampaignConfig) -> dict[str, Any]:
    """Config as a plain dict, for echoing into results metadata."""
    return dataclasses.asdict(cfg)
