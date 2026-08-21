"""Per-episode results schema, version 2.

The first thirteen fields are name-compatible with the flowhelm-lab baseline
records (baseline-2026-08-15) so that dataset loads through this reader
unchanged. All v2 fields default, so v1 records promote silently on read.

Per-episode JSONL records are the source of truth; aggregates are always
recomputed from records, never carried separately. Every latency number is
tagged with the machine it was measured on via RunMetadata.machine.

Python 3.8 compatible: imported in the LIBERO client process.
"""

from __future__ import annotations

import dataclasses
import json
import math
import platform
import subprocess
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 2


@dataclasses.dataclass
class EpisodeRecord:
    """One evaluation episode. Written as one JSON line, append-only."""

    suite: str
    task_id: int
    task_description: str
    init_id: int
    seed: int  # environment seed passed to env.seed() before set_init_state
    success: bool
    wall_s: float
    n_chunks: int
    n_env_steps: int
    # Latency split across the policy-server websocket. client_infer includes
    # the socket hop; server_infer is what a co-located deployment would see.
    # Which one is the headline is a recorded design decision, not a default.
    client_infer_s_total: float
    server_infer_s_total: float
    replan_steps: int
    max_steps: int
    # v2 fields. All defaulted so v1 baseline records promote on read.
    policy_id: str = ""  # registry id, e.g. "pi05_libero"
    checkpoint: str = ""
    benchmark: str = "libero"  # "libero" | "libero_plus" | "robocasa"
    sampling_seed: int | None = None  # EPISODE-level noise-stream id; each chunk's
    # request seed is derived from (this, chunk_index) by rollout.runner.chunk_seed.
    # None = uncontrolled (server default RNG).
    num_steps: int | None = None  # denoising steps; None = policy default
    chunk_len: int | None = None  # actions per forward pass (pi0.5 LIBERO: 10)
    exec_horizon: int | None = None  # steps executed before replanning; canonical name
    perturbation_axis: str | None = None  # None = clean
    perturbation_level: str | None = None
    replicate: int = 0  # residual-nondeterminism repeats: same factors, distinct planned episode
    run_id: str = ""
    worker_id: str = ""
    box_id: str = ""
    started_at: str = ""  # ISO 8601

    def __post_init__(self) -> None:
        # exec_horizon is the canonical name; replan_steps is kept for
        # baseline compatibility and fills exec_horizon when absent.
        if self.exec_horizon is None:
            self.exec_horizon = self.replan_steps

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), separators=(",", ":"))


def cell_key(rec: EpisodeRecord) -> tuple[Any, ...]:
    """The identity of one episode's experimental cell.

    Single source of truth for resume, duplicate detection, and pairing.
    Two records with equal cell_key are the same planned episode.
    """
    return (
        rec.policy_id,
        rec.benchmark,
        rec.suite,
        rec.task_id,
        rec.init_id,
        rec.seed,
        rec.sampling_seed,
        rec.num_steps,
        rec.exec_horizon,
        rec.perturbation_axis,
        rec.perturbation_level,
        rec.replicate,
    )


@dataclasses.dataclass
class RunMetadata:
    """Written once per run as metadata.json alongside the record files."""

    schema_version: int
    config: dict  # echo of the full CampaignConfig
    machine: dict
    roborigor_version: str
    git_commits: dict  # repo name -> commit sha (roborigor, openpi, libero, ...)
    started_at: str  # ISO 8601, caller-supplied
    gl_renderer: str = ""  # exact GL_RENDERER string asserted on the box
    serve_cmdlines: list = dataclasses.field(default_factory=list)


def collect_machine_info() -> dict:
    """Best-effort machine fingerprint; GPU names via nvidia-smi when present."""
    info: dict = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "gpus": [],
    }
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            info["gpus"] = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return info


def wilson_ci95(successes: int, n: int) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion.

    Kept in core (stdlib math, 3.8 safe) for parity with the baseline
    summaries. Headline intervals use Clopper-Pearson from roborigor.stats,
    which requires scipy and reports Wilson alongside.
    """
    if n == 0:
        return (0.0, 1.0)
    z = 1.959963984540054
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def summarize(records: Iterable[EpisodeRecord]) -> dict:
    """Aggregate episode records into the summary.json structure.

    Field names and semantics match the flowhelm-lab baseline summary so the
    2026-08-15 dataset reproduces to the digit. duplicate_inits reports the
    number of records sharing a cell_key with an earlier record (null when
    zero, matching the baseline convention).
    """
    by_suite: dict = {}
    for r in records:
        by_suite.setdefault(r.suite, []).append(r)

    suites = {}
    total_n = 0
    total_succ = 0
    for suite, recs in sorted(by_suite.items()):
        n = len(recs)
        succ = sum(r.success for r in recs)
        total_n += n
        total_succ += succ
        seen = set()
        dups = 0
        for r in recs:
            k = cell_key(r)
            if k in seen:
                dups += 1
            seen.add(k)
        suites[suite] = {
            "n": n,
            "successes": succ,
            "success_rate": succ / n,
            "ci95_wilson": list(wilson_ci95(succ, n)),
            "seeds": sorted({r.seed for r in recs}),
            "mean_episode_wall_s": sum(r.wall_s for r in recs) / n,
            "duplicate_inits": dups if dups else None,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "suites": suites,
        "n_total": total_n,
        "overall": {
            "n": total_n,
            "successes": total_succ,
            "success_rate": total_succ / total_n if total_n else None,
            "ci95_wilson": list(wilson_ci95(total_succ, total_n)) if total_n else None,
        },
    }


def write_record(path: str, rec: EpisodeRecord) -> None:
    """Append one record and flush, so a killed worker loses at most one line."""
    with open(path, "a") as f:
        f.write(rec.to_json() + "\n")
        f.flush()


def read_records(path: str) -> list:
    """Read one records_*.jsonl file.

    Tolerates extra fields from newer writers (dropped) and a torn final line
    from a killed worker (skipped; that episode reruns via resume).
    """
    known = {f.name for f in dataclasses.fields(EpisodeRecord)}
    out = []
    lines = Path(path).read_text().splitlines()
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            if i == len(lines) - 1:
                continue  # torn final line from an interrupted writer
            raise
        out.append(EpisodeRecord(**{k: v for k, v in raw.items() if k in known}))
    return out
