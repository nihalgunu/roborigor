"""Environment adapter interface.

An adapter owns benchmark mechanics: task enumeration, deterministic init
states by init_id, environment seeding, observation preprocessing to the
canonical PredictRequest inputs, and success detection. The rollout runner
never touches benchmark internals.

Python 3.8 compatible: imported in benchmark client processes.
"""

from __future__ import annotations

import abc
import dataclasses


@dataclasses.dataclass
class TaskSpec:
    task_id: int
    description: str
    max_steps: int
    n_inits: int


@dataclasses.dataclass
class StepResult:
    done: bool
    success: bool


class EpisodeHandle(abc.ABC):
    """One live episode: observe, step, close."""

    @abc.abstractmethod
    def observe(self):  # -> (images, state, prompt) for PredictRequest
        ...

    @abc.abstractmethod
    def step(self, action) -> StepResult:
        ...

    def close(self) -> None:  # noqa: B027 (optional hook)
        ...


class EnvAdapter(abc.ABC):
    benchmark: str = ""

    @abc.abstractmethod
    def tasks(self, suite: str) -> list[TaskSpec]:
        ...

    @abc.abstractmethod
    def open_episode(
        self,
        suite: str,
        task_id: int,
        init_id: int,
        seed: int,
        perturbation_axis: str | None = None,
        perturbation_level: str | None = None,
    ) -> EpisodeHandle:
        ...
