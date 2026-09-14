# Datasheet: RoboRigor per-episode records

## Motivation
Released so that every aggregate in the accompanying report can be recomputed from individual episodes, and so others can study paired VLA evaluation (the same episodes under different policies, inference settings, and perturbations) without re-running simulation.

## Composition
- **31,858 episode records** (one JSON line each), schema version 2; fields listed in `artifact/README.md`.
- **Policies:** released openpi checkpoints `pi05_libero` and `pi0_libero`, and SmolVLA (LIBERO fine-tune), each served unmodified.
- **Benchmarks:** LIBERO (libero_10, plus a 20-init scan of the goal, object, and spatial suites) and LIBERO-Plus (camera viewpoints, object layout, light conditions, robot initial states), on fixed variant sets shared across policies.
- **Factors recorded per episode:** task, initial state, environment seed, flow-sampling seed, denoising steps, execution horizon, perturbation axis and level, replicate, and server- and client-side inference time.
- **Campaigns (directories under `artifact/`):**

| Directory | Episodes | Contents |
|---|---|---|
| `v2_knobs` | 5,760 | pi0.5, 4 denoising-step x 3 execution-horizon settings, 8 tasks x 20 inits x 3 seeds |
| `replication` | 3,840 | pi0.5 at environment seed 8; pi0 at five step/horizon settings |
| `v1_varcomp` | 2,176 | pi0.5 variance study: up to 40 inits x 10 seeds per task, plus a replicate block |
| `reseed` | 5,000 | pi0.5 standard 500-episode LIBERO-10 protocol at 10 sampling seeds |
| `camconf`, `campow`, `fusion` | 4,252 | pi0.5 one step vs. ten (and two) under camera and layout shift |
| `plus_pilot*`, `clean_anchors`, `armor` | 5,828 | Three policies on identical LIBERO-Plus variant sets; clean anchors; light and robot-state axes; pi0.5 env seeds 8 and 9 |
| `smolgrid`, `eh1`, `gapfill` | 4,386 | SmolVLA horizon and step settings; pi0 and SmolVLA variance cells; SmolVLA extra axes |
| `suite_scan`, `pilot2a`, smoke runs | 616 | Suite saturation scan and harness pilots |

Some directories overlap in design (for example the SmolVLA default-steps cell appears in more than one campaign); analyses deduplicate on the cell key. A truncated 26-episode SmolVLA cell is kept alongside its completed 480-episode version.

## Collection
Episodes ran on Lambda A100 (40 GB) boxes, 6 workers per box, August to September 2026, using the harness in this repository. Pairing is by construction: settings compared on "identical episodes" share task, initial state, environment seed, sampling seed (or variant and draw), and replicate. Fixed-request inference was verified bitwise deterministic; closed-loop rollouts are not, and replicate cells quantify that.

## Known limitations
- Simulation only; LIBERO-family benchmarks.
- LIBERO ends an episode early only on success, so every failure runs to the step limit and step counts carry no failure-mode information.
- Latency fields are measured under 6-worker GPU contention on one hardware type.
- SmolVLA's served default step count is not recorded in its reference-arm records.

## Uses
Intended for evaluation-methodology research, re-analysis of the paper, and benchmarking statistical procedures on real paired robot-policy outcomes. Not a training dataset: records contain outcomes and timings, not observations or actions.

## Maintenance and license
Records are append-only and released under Apache-2.0 with the code. `artifact/MANIFEST.txt` gives a sha256 for every file.
