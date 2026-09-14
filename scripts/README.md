# scripts index

## Running evaluations
| Script | Purpose |
|---|---|
| `setup_gpu_box.sh`, `setup_box_extras.sh` | Provision a Lambda A100 box for openpi + LIBERO (and LIBERO-Plus). |
| `serve_openpi.py`, `serve_smolvla.py` | Serve a policy behind the websocket interface the runner speaks. |
| `campaign_box.sh` | Per-box entrypoint: run a manifest shard with N workers. |

## Paper analyses (inputs: `results/` or `artifact/` records; outputs: `docs/paper-data/`)
| Script | Output |
|---|---|
| `analyze_step_transfer.py` | `step_transfer.json`: one-step vs ten-step contrasts everywhere they are measured, dilution curve, certification budget. |
| `analyze_dilution_census.py` | `dilution_census.json`: all 79 paired dial comparisons, four-task subset controls, interval and margin sensitivity. |
| `analyze_failure_ratio_and_shift.py` | `failure_ratio_and_shift.json`: failure-rate ratios, camera cost by perturbation level, per-task seed comparison, latency. |
| `analyze_efficiency_audit.py` | `efficiency_audit.json`: outcomes of the efficiency-paper audit. |
| `verify_efficiency_sample.py` | `docs/efficiency_audit/verification_sample.json`: PDF text check of a seeded 20% sample. |
| `efficiency_audit_search.sh`, `efficiency_audit_search_s2.sh` | Fixed literature searches for the efficiency audit (arXiv API; Semantic Scholar). |

## Figures, checks, packaging
| Script | Purpose |
|---|---|
| `make_figures.py` | All figures. |
| `check_paper_numbers.py` | Regenerates `paper/numbers.tex` and tables; fails if any number in the paper drifts from the data. |
| `package_artifact.py` | Builds `artifact/` (records, reports, audits, datasheet) with a sha256 manifest. |
| `build_named.sh` | Builds the non-anonymized PDF. |

## Additional analyses
| Script | Output |
|---|---|
| `analyze_nondeterminism.py` | `nondeterminism.json`: replicate-block estimate of closed-loop nondeterminism. |
| `analyze_anchor_seed_sensitivity.py` | `anchor_seed_sensitivity.json`: seed band of the clean anchors. |
| `analyze_equivalence_subsets.py` | `restricted_factorial.json`: frontier vs. shipped default on task subsets. |
| `analyze_pending.py` | Seed-rerun protocol spread and other landing analyses. |
| `replay_baseline_stats.py` | Re-derives statistics from the pre-harness baseline records. |
