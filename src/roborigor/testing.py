"""Deterministic mock env and policy, for dry runs and tests.

`roborigor run-shard --env mock` exercises the full campaign pipeline
(manifest, resume, records, integrity) with no benchmark or GPU, which is
also how users can validate a campaign config end to end before spending.

Python 3.8 compatible.
"""

from __future__ import annotations

from roborigor.core.schema import EpisodeRecord
from roborigor.envs.base import EnvAdapter, EpisodeHandle, StepResult, TaskSpec
from roborigor.policies.base import PolicyClient, PredictResult


def make_record(**kw) -> EpisodeRecord:
    """Factory for a valid EpisodeRecord with sensible defaults."""
    base = {
        "suite": "libero_10", "task_id": 0, "task_description": "t", "init_id": 0,
        "seed": 7, "success": True, "wall_s": 1.0, "n_chunks": 2, "n_env_steps": 10,
        "client_infer_s_total": 0.5, "server_infer_s_total": 0.4,
        "replan_steps": 5, "max_steps": 520,
    }
    base.update(kw)
    return EpisodeRecord(**base)


class MockPolicy(PolicyClient):
    """Constant zero-action policy; the mock env scripts the outcomes."""

    policy_id = "mock"
    chunk_len = 10
    action_dim = 7
    real_action_dims = 7

    def __init__(self):
        self.n_predicts = 0

    def predict(self, req) -> PredictResult:
        import numpy as np

        self.n_predicts += 1
        return PredictResult(
            actions=np.zeros((self.chunk_len, self.action_dim)),
            server_infer_s=0.001,
            client_infer_s=0.002,
        )


class MockHandle(EpisodeHandle):
    def __init__(self, succeed_at):
        self.succeed_at = succeed_at  # env step at which success fires; None = never
        self.steps = 0

    def observe(self):
        import numpy as np

        return {"agentview": np.zeros((4, 4, 3))}, np.zeros(8), "do the task"

    def step(self, action) -> StepResult:
        self.steps += 1
        success = self.succeed_at is not None and self.steps >= self.succeed_at
        return StepResult(done=success, success=success)


class MockEnv(EnvAdapter):
    """Scripted env: episode fails iff (task_id + init_id) % fail_every == 0."""

    benchmark = "libero"

    def __init__(self, n_tasks: int = 10, fail_every: int = 4, succeed_at: int = 7):
        self.n_tasks = n_tasks
        self.fail_every = fail_every
        self.succeed_at = succeed_at

    def tasks(self, suite):
        return [
            TaskSpec(task_id=t, description=f"task {t}", max_steps=30, n_inits=50)
            for t in range(self.n_tasks)
        ]

    def open_episode(self, suite, task_id, init_id, seed,
                     perturbation_axis=None, perturbation_level=None):
        fails = (task_id + init_id) % self.fail_every == 0
        return MockHandle(succeed_at=None if fails else self.succeed_at)
