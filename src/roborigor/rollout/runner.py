"""The episode loop: observe, predict, execute, record.

Protocol mirrors the verified flowhelm-lab runner: the full chunk is
requested every replan, the first exec_horizon actions are executed, and
the episode ends on success, done, or the step budget. One JSONL line per
episode, flushed immediately, so a killed worker loses at most one line.

Python 3.8 compatible: this is the code that runs inside the benchmark
client process.
"""

from __future__ import annotations

import hashlib
import time

from roborigor.core.schema import EpisodeRecord, write_record
from roborigor.envs.base import EnvAdapter
from roborigor.policies.base import PolicyClient, PredictRequest
from roborigor.rollout.worklist import WorkItem


def chunk_seed(sampling_seed: int | None, chunk_index: int) -> int | None:
    """Deterministic per-chunk seed schedule.

    "Fixed sampling seed" is an EPISODE-level identity: it names a noise
    stream, not one noise draw. Sending the same seed to every replan would
    give every action chunk identical noise, a degenerate policy nobody
    deploys, and the measured "sampling variance" would be an artifact.
    Instead each chunk gets a seed derived from (episode seed, chunk index):
    a replicate with the same episode seed reproduces the whole trajectory's
    noise sequence bit for bit, two episode seeds give unrelated sequences,
    and consecutive chunks within one episode always draw fresh noise.

    blake2b keeps the schedule stable across platforms and Python versions
    (hash() is salted per process and unusable here).
    """
    if sampling_seed is None:
        return None
    digest = hashlib.blake2b(
        f"{sampling_seed}:{chunk_index}".encode(), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") >> 1  # 63-bit non-negative


def run_episode(
    env: EnvAdapter,
    policy: PolicyClient,
    item: WorkItem,
    max_steps: int,
    task_description: str,
    started_at: str = "",
    worker_id: str = "",
    box_id: str = "",
) -> EpisodeRecord:
    exec_horizon = item.exec_horizon  # concrete since expansion
    handle = env.open_episode(
        item.suite, item.task_id, item.init_id, item.seed,
        perturbation_axis=item.perturbation_axis,
        perturbation_level=item.perturbation_level,
    )
    t0 = time.monotonic()
    success = False
    n_chunks = 0
    n_env_steps = 0
    client_s = 0.0
    server_s = 0.0
    policy.reset()
    try:
        while n_env_steps < max_steps:
            images, state, prompt = handle.observe()
            result = policy.predict(
                PredictRequest(
                    images=images, state=state, prompt=prompt,
                    sampling_seed=chunk_seed(item.sampling_seed, n_chunks),
                    num_steps=item.num_steps,
                )
            )
            n_chunks += 1
            client_s += result.client_infer_s
            server_s += result.server_infer_s
            done = False
            for action in list(result.actions)[:exec_horizon]:
                step = handle.step(action)
                n_env_steps += 1
                if step.success:
                    success = True
                if step.done or step.success or n_env_steps >= max_steps:
                    done = True
                    break
            if done and (success or step.done):
                break
    finally:
        handle.close()
    return EpisodeRecord(
        suite=item.suite,
        task_id=item.task_id,
        task_description=task_description,
        init_id=item.init_id,
        seed=item.seed,
        success=success,
        wall_s=time.monotonic() - t0,
        n_chunks=n_chunks,
        n_env_steps=n_env_steps,
        client_infer_s_total=client_s,
        server_infer_s_total=server_s,
        replan_steps=exec_horizon,
        max_steps=max_steps,
        policy_id=item.policy_id,
        checkpoint=item.checkpoint,
        benchmark=item.benchmark,
        sampling_seed=item.sampling_seed,
        num_steps=item.num_steps,
        chunk_len=policy.chunk_len or None,
        exec_horizon=exec_horizon,
        perturbation_axis=item.perturbation_axis,
        perturbation_level=item.perturbation_level,
        replicate=item.replicate,
        run_id=item.run_id,
        worker_id=worker_id,
        box_id=box_id,
        started_at=started_at,
    )


def run_work_items(
    items,
    env: EnvAdapter,
    policy: PolicyClient,
    out_path: str,
    default_max_steps: int = 300,
    max_steps_override: int | None = None,
    worker_id: str = "",
    box_id: str = "",
    started_at: str = "",
) -> int:
    """Run items sequentially, appending one JSONL line per episode. Returns count."""
    task_meta = {}
    n = 0
    for item in items:
        key = (item.suite,)
        if key not in task_meta:
            task_meta[key] = {t.task_id: t for t in env.tasks(item.suite)}
        spec = task_meta[key].get(item.task_id)
        if spec is None:
            raise ValueError(f"unknown task {item.task_id} in suite {item.suite}")
        max_steps = max_steps_override or spec.max_steps or default_max_steps
        record = run_episode(
            env, policy, item, max_steps, spec.description,
            started_at=started_at, worker_id=worker_id, box_id=box_id,
        )
        write_record(out_path, record)
        n += 1
    return n
