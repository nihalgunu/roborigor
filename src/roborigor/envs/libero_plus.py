"""LIBERO-Plus adapter (arXiv 2510.13626).

LIBERO-Plus ships as a fork that installs itself AS the `libero` package
(same import paths, version 0.1.0), so this adapter reuses the stock
adapter mechanics unchanged. The operational consequences:

1. The fork must live in its OWN venv. Importing `libero` in an env where
   the fork is installed silently swaps the benchmark; machine metadata
   records libero.__version__ plus the git commit, and verify_fork()
   refuses to run if the expected marker is absent.
2. Perturbation identity is intrinsic to the task variant, not an env
   knob. The fork's task_classification.json maps variants to one of the
   7 axes (Objects Layout, Camera Viewpoints, Robot Initial States,
   Language Instructions, Light Conditions, Background Textures, Sensor
   Noise) and a difficulty level. We load that mapping, stamp axis/level
   into every record, and validate the campaign's declared axis/level
   against it, so a config can never mislabel a variant.

The exact JSON schema is verified on the box (VERIFY-ON-BOX below); the
loader accepts the two plausible shapes and fails loudly otherwise.

Python 3.8 compatible.
"""

from __future__ import annotations

import json
from pathlib import Path

from roborigor.envs.base import EpisodeHandle, TaskSpec
from roborigor.envs.libero import LiberoAdapter


def load_classification(path: str) -> dict[str, dict]:
    """Normalize task_classification.json to {task_key: {axis, level}}.

    Accepts either {task_key: {...axis..., ...level...}} or the inverted
    {axis: {level: [task_key, ...]}}. Axis and level key names vary across
    forks ("category"/"axis"/"perturbation", "level"/"difficulty"), so
    both are probed. VERIFY-ON-BOX: assert the loaded axis set matches the
    7 published axes before any campaign runs.
    """
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{path}: expected a non-empty mapping")
    out: dict[str, dict] = {}
    first = next(iter(raw.values()))
    if isinstance(first, list):
        # VERIFIED-ON-BOX 2026-08-20: the fork's real shape is
        # {suite: [{id, name, category, difficulty_level}, ...]}
        for suite, entries in raw.items():
            for e in entries:
                if not isinstance(e, dict) or "name" not in e:
                    raise ValueError(f"{path}: malformed entry under {suite!r}: {e!r}")
                axis = e.get("category") or e.get("axis")
                level = e.get("difficulty_level", e.get("level"))
                if axis is None:
                    raise ValueError(f"{path}: no category in entry {e.get('name')!r}")
                out[str(e["name"])] = {"axis": str(axis), "level": str(level)}
        return out
    if isinstance(first, dict) and any(
        k in first for k in ("axis", "category", "perturbation", "level", "difficulty")
    ):
        for task_key, meta in raw.items():
            axis = meta.get("axis") or meta.get("category") or meta.get("perturbation")
            level = meta.get("level") or meta.get("difficulty")
            if axis is None:
                raise ValueError(f"{path}: no axis field in entry {task_key!r}")
            out[str(task_key)] = {"axis": str(axis), "level": str(level)}
    elif isinstance(first, dict):
        for axis, levels in raw.items():
            if not isinstance(levels, dict):
                raise ValueError(f"{path}: unrecognized structure under {axis!r}")
            for level, task_keys in levels.items():
                for task_key in task_keys:
                    out[str(task_key)] = {"axis": str(axis), "level": str(level)}
    else:
        raise ValueError(f"{path}: unrecognized classification structure")
    return out


def task_ids_for_axis(
    classification: dict[str, dict],
    task_names_in_suite: list[str],
    axis: str,
    level: str | None = None,
) -> list[int]:
    """Variant task ids (indices into the suite) for one axis, optionally one level."""
    ids = []
    for task_id, name in enumerate(task_names_in_suite):
        meta = classification.get(str(name))
        if meta is None:
            continue
        if meta["axis"] == axis and (level is None or meta["level"] == level):
            ids.append(task_id)
    return ids


class LiberoPlusAdapter(LiberoAdapter):
    """LIBERO-Plus suites; validates declared perturbation against the fork's map."""

    benchmark = "libero_plus"

    def __init__(self, classification_path: str, default_max_steps: int = 520,
                 resize_size=224):
        super().__init__(resize_size=resize_size)
        self._classification = load_classification(classification_path)
        self._default_max_steps = default_max_steps

    def verify_fork(self) -> None:
        """Refuse to run against stock LIBERO. VERIFY-ON-BOX: marker choice."""
        from libero.libero import benchmark

        suites = set(benchmark.get_benchmark_dict())
        if suites == {"libero_spatial", "libero_object", "libero_goal", "libero_10", "libero_90"}:
            raise RuntimeError(
                "stock LIBERO is installed in this venv, not the LIBERO-Plus fork; "
                "refusing to run a libero_plus campaign against the wrong benchmark"
            )

    def perturbation_for(self, suite: str, task_id: int) -> dict:
        ts = self._suite(suite)
        name = str(ts.get_task(task_id).name)
        meta = self._classification.get(name)
        if meta is None:
            raise KeyError(f"task {name!r} (id {task_id}) missing from classification map")
        return meta

    def tasks(self, suite: str) -> list[TaskSpec]:
        ts = self._suite(suite)
        out = []
        for task_id in range(ts.n_tasks):
            task = ts.get_task(task_id)
            out.append(
                TaskSpec(
                    task_id=task_id,
                    description=str(task.language),
                    max_steps=self._default_max_steps,
                    n_inits=len(ts.get_task_init_states(task_id)),
                )
            )
        return out

    def open_episode(
        self,
        suite: str,
        task_id: int,
        init_id: int,
        seed: int,
        perturbation_axis: str | None = None,
        perturbation_level: str | None = None,
    ) -> EpisodeHandle:
        meta = self.perturbation_for(suite, task_id)
        if perturbation_axis is not None and perturbation_axis != meta["axis"]:
            raise ValueError(
                f"campaign declares axis {perturbation_axis!r} but task {task_id} "
                f"in {suite} is classified {meta['axis']!r}"
            )
        if perturbation_level is not None and perturbation_level != meta["level"]:
            raise ValueError(
                f"campaign declares level {perturbation_level!r} but task {task_id} "
                f"in {suite} is classified level {meta['level']!r}"
            )
        # mechanics identical to stock: the variant IS the perturbation
        return LiberoAdapter.open_episode(self, suite, task_id, init_id, seed)
