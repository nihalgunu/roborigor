"""Stock LIBERO adapter.

The eval protocol is duplicated from the verified flowhelm-lab runner
(itself a faithful derivative of openpi examples/libero/main.py @ 15a9616):
same MAX_STEPS table, 256px render, 10 settle steps with the dummy action,
180 degree image rotation, resize_with_pad to 224, eef state layout,
env.seed(seed) before set_init_state (seed affects object positions even
with fixed init states), and success = env's done flag.

One deliberate bookkeeping deviation, for the record: n_env_steps in our
records counts executed policy actions only; the 10 settle steps happen
inside open_episode and are excluded (the upstream runner included them in
its step count). Success semantics are identical.

libero / openpi_client / numpy imports are lazy: this module must import
on the dev Mac (for tests and planning) but only runs inside the LIBERO
python 3.8 venv on the box.

Python 3.8 compatible.
"""

from __future__ import annotations

import math

from roborigor.envs.base import EnvAdapter, EpisodeHandle, StepResult, TaskSpec

LIBERO_DUMMY_ACTION = [0.0] * 6 + [-1.0]
LIBERO_ENV_RESOLUTION = 256  # resolution used to render training data
RESIZE_SIZE = 224
NUM_STEPS_WAIT = 10  # steps for objects to stabilize after set_init_state

MAX_STEPS = {  # verbatim from upstream main.py
    "libero_spatial": 220,
    "libero_object": 280,
    "libero_goal": 300,
    "libero_10": 520,
    "libero_90": 400,
}


def _quat2axisangle(quat):
    """Copied from robosuite transform_utils (as upstream does)."""
    import numpy as np

    if quat[3] > 1.0:
        quat[3] = 1.0
    elif quat[3] < -1.0:
        quat[3] = -1.0
    den = np.sqrt(1.0 - quat[3] * quat[3])
    if math.isclose(den, 0.0):
        return np.zeros(3)
    return (quat[:3] * 2.0 * math.acos(quat[3])) / den


class LiberoEpisode(EpisodeHandle):
    def __init__(self, env, task_description: str, resize_size: int | None = RESIZE_SIZE):
        self._env = env
        self._prompt = str(task_description)
        self._resize = resize_size  # None = send native frames (policy resizes itself)
        self._obs = None  # set by adapter after settle steps

    def observe(self):
        import numpy as np

        obs = self._obs
        # IMPORTANT: rotate 180 degrees to match train preprocessing
        img = np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])
        wrist = np.ascontiguousarray(obs["robot0_eye_in_hand_image"][::-1, ::-1])
        if self._resize is not None:
            from openpi_client import image_tools

            img = image_tools.convert_to_uint8(
                image_tools.resize_with_pad(img, self._resize, self._resize)
            )
            wrist = image_tools.convert_to_uint8(
                image_tools.resize_with_pad(wrist, self._resize, self._resize)
            )
        state = np.concatenate(
            (
                obs["robot0_eef_pos"],
                _quat2axisangle(obs["robot0_eef_quat"]),
                obs["robot0_gripper_qpos"],
            )
        )
        return {"agentview": img, "wrist": wrist}, state, self._prompt

    def step(self, action) -> StepResult:
        import numpy as np

        obs, _reward, done, _info = self._env.step(np.asarray(action).tolist())
        self._obs = obs
        # upstream counts an episode successful exactly when done fires
        return StepResult(done=bool(done), success=bool(done))

    def close(self) -> None:
        # env is owned and cached by the adapter; nothing to free per episode
        pass


class LiberoAdapter(EnvAdapter):
    """Stock LIBERO suites. Caches one live env per (task_id, seed)."""

    benchmark = "libero"

    def __init__(self, resolution: int = LIBERO_ENV_RESOLUTION,
                 resize_size: int | None = RESIZE_SIZE):
        self._resolution = resolution
        self._resize_size = resize_size
        self._suite_cache = {}
        self._env_cache_key = None
        self._env = None

    def _suite(self, suite: str):
        from libero.libero import benchmark

        if suite not in self._suite_cache:
            self._suite_cache[suite] = benchmark.get_benchmark_dict()[suite]()
        return self._suite_cache[suite]

    def tasks(self, suite: str) -> list[TaskSpec]:
        ts = self._suite(suite)
        out = []
        for task_id in range(ts.n_tasks):
            task = ts.get_task(task_id)
            out.append(
                TaskSpec(
                    task_id=task_id,
                    description=str(task.language),
                    max_steps=MAX_STEPS[suite],
                    n_inits=len(ts.get_task_init_states(task_id)),
                )
            )
        return out

    def _get_env(self, suite: str, task_id: int, seed: int):
        import pathlib

        from libero.libero import get_libero_path
        from libero.libero.envs import OffScreenRenderEnv

        key = (suite, task_id, seed)
        if self._env_cache_key != key:
            if self._env is not None:
                self._env.close()
            ts = self._suite(suite)
            task = ts.get_task(task_id)
            bddl = (
                pathlib.Path(get_libero_path("bddl_files"))
                / task.problem_folder
                / task.bddl_file
            )
            env = OffScreenRenderEnv(
                # str() required: the LIBERO-Plus fork substring-matches on
                # this argument and rejects Path objects
                bddl_file_name=str(bddl),
                camera_heights=self._resolution,
                camera_widths=self._resolution,
            )
            # IMPORTANT: seed affects object positions even with fixed init states
            env.seed(seed)
            self._env = env
            self._env_cache_key = key
        return self._env, str(self._suite(suite).get_task(task_id).language)

    def open_episode(
        self,
        suite: str,
        task_id: int,
        init_id: int,
        seed: int,
        perturbation_axis: str | None = None,
        perturbation_level: str | None = None,
    ) -> EpisodeHandle:
        if perturbation_axis is not None or perturbation_level is not None:
            raise ValueError(
                "stock LIBERO has no perturbations; use the libero_plus benchmark"
            )
        env, description = self._get_env(suite, task_id, seed)
        env.reset()
        init_states = self._suite(suite).get_task_init_states(task_id)
        obs = env.set_init_state(init_states[init_id])
        handle = LiberoEpisode(env, description, resize_size=self._resize_size)
        # settle: objects drop for the first steps after set_init_state
        for _ in range(NUM_STEPS_WAIT):
            obs, _r, _d, _i = env.step(LIBERO_DUMMY_ACTION)
        handle._obs = obs
        return handle

    def close(self) -> None:
        if self._env is not None:
            self._env.close()
            self._env = None
            self._env_cache_key = None
