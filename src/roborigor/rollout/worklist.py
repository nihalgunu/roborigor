"""Expand a CampaignConfig into the flat list of planned episodes.

One WorkItem is one planned episode; its key() matches core.schema.cell_key
field for field, which is what makes resume and integrity exact.

Python 3.8 compatible.
"""

from __future__ import annotations

import dataclasses

from roborigor.core.config import CampaignConfig, resolve_cell

DEFAULT_N_TRIALS = 50
DEFAULT_EXEC_HORIZON = 5


@dataclasses.dataclass(frozen=True)
class WorkItem:
    policy_id: str
    checkpoint: str
    benchmark: str
    suite: str
    task_id: int
    init_id: int
    seed: int
    sampling_seed: int | None
    num_steps: int | None
    exec_horizon: int  # always concrete: resolved at expansion so plan and record keys match
    perturbation_axis: str | None
    perturbation_level: str | None
    replicate: int
    arm: str
    run_id: str

    def key(self) -> tuple:
        """Identical field order to core.schema.cell_key over EpisodeRecord."""
        return (
            self.policy_id, self.benchmark, self.suite, self.task_id,
            self.init_id, self.seed, self.sampling_seed, self.num_steps,
            self.exec_horizon, self.perturbation_axis, self.perturbation_level,
            self.replicate,
        )


def expand_campaign(
    cfg: CampaignConfig,
    all_task_ids: list[int],
    default_exec_horizon: int = DEFAULT_EXEC_HORIZON,
) -> list[WorkItem]:
    """All planned episodes, deterministic order: arm, task, init, seed, sampling seed.

    all_task_ids is the benchmark's full task list for the suite; a cell's
    task_ids/init_ids override it when set. Duplicate keys across arms are
    a design error (two arms with identical factors) and raise here, before
    anything runs.
    """
    items: list[WorkItem] = []
    seen = set()
    for arm in cfg.arms:
        cell = resolve_cell(cfg.base, arm)
        n_trials = cell.n_trials_per_task or DEFAULT_N_TRIALS
        task_ids = cell.task_ids if cell.task_ids is not None else list(all_task_ids)
        init_ids = cell.init_ids if cell.init_ids is not None else list(range(n_trials))
        sampling_seeds = cell.sampling_seeds if cell.sampling_seeds is not None else [None]
        n_replicates = cell.replicates or 1
        for task_id in task_ids:
            for init_id in init_ids:
                for seed in cell.seeds:
                    for s_seed in sampling_seeds:
                      for rep in range(n_replicates):
                        item = WorkItem(
                            policy_id=cfg.policy.policy_id,
                            checkpoint=cfg.policy.checkpoint,
                            benchmark=cfg.benchmark,
                            suite=cfg.suite,
                            task_id=task_id,
                            init_id=init_id,
                            seed=seed,
                            sampling_seed=s_seed,
                            num_steps=cell.num_steps,
                            exec_horizon=cell.exec_horizon or default_exec_horizon,
                            perturbation_axis=cell.perturbation_axis,
                            perturbation_level=cell.perturbation_level,
                            replicate=rep,
                            arm=arm.name,
                            run_id=f"{cfg.campaign}/{arm.name}",
                        )
                        k = item.key()
                        if k in seen:
                            raise ValueError(
                                f"arms {arm.name!r} and an earlier arm plan the "
                                f"identical episode {k}; differentiate the arms"
                            )
                        seen.add(k)
                        items.append(item)
    return items
