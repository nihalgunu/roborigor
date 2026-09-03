# RoboRigor release artifact

Per-episode evaluation records and derived reports for the RoboRigor
paper. Records are the source of truth; every aggregate is recomputed
from them, never carried separately.

## Layout

- `<campaign>/records_*.jsonl`: one JSON object per line, one line per
  evaluation episode, append-only, grouped by campaign as run.
- `paper-data/*.json`: derived reports (variance decomposition, knob
  table, rank analysis) recomputable from the records.
- `audit/`: the 50-paper literature audit: extraction rows, intake
  logs, recomputed significance, and RESULTS.md.
- `MANIFEST.txt`: sha256 and line count for every file above.

## Episode record schema (version 2)

The first thirteen fields are name-compatible with an earlier internal
baseline records (baseline-2026-08-15). All v2 fields default, so v1
records promote silently on read. Every latency number is tagged with
the machine it was measured on via the run's metadata.

| Field | Type |
|---|---|
| `suite` | `str` |
| `task_id` | `int` |
| `task_description` | `str` |
| `init_id` | `int` |
| `seed` | `int` |
| `success` | `bool` |
| `wall_s` | `float` |
| `n_chunks` | `int` |
| `n_env_steps` | `int` |
| `client_infer_s_total` | `float` |
| `server_infer_s_total` | `float` |
| `replan_steps` | `int` |
| `max_steps` | `int` |
| `policy_id` | `str` |
| `checkpoint` | `str` |
| `benchmark` | `str` |
| `sampling_seed` | `int or None` |
| `num_steps` | `int or None` |
| `chunk_len` | `int or None` |
| `exec_horizon` | `int or None` |
| `perturbation_axis` | `str or None` |
| `perturbation_level` | `str or None` |
| `replicate` | `int` |
| `run_id` | `str` |
| `worker_id` | `str` |
| `box_id` | `str` |
| `started_at` | `str` |

Two records are the same planned episode exactly when they agree on
(policy_id, benchmark, suite, task_id, init_id, seed, sampling_seed,
num_steps, exec_horizon, perturbation_axis, perturbation_level,
replicate). This cell key drives resume, duplicate detection, and
pairing. Read the files with `roborigor.core.schema.read_records`,
which tolerates newer writers' extra fields and a torn final line
from an interrupted worker.
