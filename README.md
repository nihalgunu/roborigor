# RoboRigor

RoboRigor is a statistical rigor toolkit for evaluating vision-language-action policies. It provides exact confidence intervals and paired policy comparisons with multiple-comparison correction, a rollout-budget (power) calculator, a variance decomposition that separates initial-state effects from flow-sampling noise, and a campaign runner with episode-granular resume that treats per-episode JSONL records as the single source of truth. It exists to answer the question robot-learning evaluations usually skip: how many rollouts do you need before a claimed improvement means anything?

## 60-second quickstart

```bash
pip install roborigor

# Plan a campaign: expand a YAML config into an episode manifest.
roborigor plan configs/pilot_smolvla_libero10.yaml --out /tmp/m.json

# Dry-run the runner against the built-in mock environment (no GPU, no sim).
roborigor run-shard --manifest /tmp/m.json --box-id box0 --out-dir /tmp/rec --env mock

# Check the records for duplicates, gaps, and outliers against the manifest.
roborigor integrity /tmp/rec --manifest /tmp/m.json
```

The same three commands drive real campaigns: point `--env` at `libero` or `libero_plus`, serve a policy behind the websocket interface, and shard the manifest across boxes. A killed worker loses at most one episode; resume is exact at episode granularity via each record's cell key.

## Headline results

Measured with this toolkit on LIBERO / LIBERO-Plus (pi0.5, pi0, SmolVLA) plus a pre-registered audit of 50 VLA papers (131 highlighted comparisons):

| Finding | Number |
|---|---|
| Minimum detectable effect at the field-standard n=50 per task (base rate 0.95, 80% power, exact test) | 18.3 points |
| Episodes needed to resolve 4.6 points / 2.5 points at that base rate | 500 / 1,500 |
| Spread in measured success rate from the flow-sampling seed alone (pi0.5, LIBERO-10, 10 seeds, 160 episodes each) | 7.5 points max minus min (SD 2.4) |
| On the one informative task (base rate 0.59), sampling-noise variance vs initial-state share | 0.204 of a possible 0.25 vs ICC 0.16 |
| Denoising-steps x execution-horizon sweep (12 cells, 480 episodes each): the entire Pareto frontier is one cell, (num_steps=1, exec_horizon=10) | 96.5% success at 5.6 ms/step |
| Audited highlighted comparisons with unusable n (not reported or ambiguous) | 34.4% (45/131) |
| Recomputable comparisons that fail an exact test at the paper's own n | 32.6% (28/86) |
| Recomputable gaps below their own protocol's MDE | 47.7% (41/86) |
| Spread of the field-standard 500-episode protocol from the sampling seed alone (10 seeds, 5,000 episodes) | 2.2 points, containing 27% of audited claimed improvements |
| Pairwise margin for the same policy pair across four perturbation axes (identical frozen variant sets) | 9.6 to 67.0 points from one 16.5-point clean gap |
| Rank inversions across four LIBERO-Plus axes and three policies | 1, only in the floor regime (SmolVLA over pi0 under robot-state shift, exact p=0.0022) |
| Robustness cost of the single-step frontier under camera-viewpoint shift (632 paired draws) | about 4 points (McNemar p=0.017); free under layout shift |

Full data behind the table: `docs/paper-data/` (JSON reports) and `docs/audit/RESULTS.md` (audit vs pre-registered outcomes). Every number regenerates from per-episode records: `python scripts/check_paper_numbers.py` verifies the paper against the data and emits the generated tables and macros; `python scripts/make_figures.py` rebuilds every figure.

## Repository layout

| Path | Contents |
|---|---|
| `src/roborigor/` | The pip-installable package: core schema and config (py3.8-safe), stats, rollout runner, campaign tools, env adapters, vendored policy server. |
| `scripts/` | Serve scripts for openpi and SmolVLA policies, box provisioning, figure and table generation, the paper drift test, artifact packaging. |
| `configs/` | Campaign YAMLs (base cell plus named arms). |
| `docs/audit-preregistration.md` | The frozen pre-registration with its append-only deviations log. |
| `docs/audit/` | The 50-paper literature audit: intake logs, extraction, recomputation. |
| `docs/paper-data/` | JSON reports each paper number is pinned against. |
| `paper/` | ICRA 2027 submission source (double-anonymous; author field intentionally blank). |
| `tests/` | 77+ tests including Monte-Carlo coverage checks and golden-value pins. |

## CLI

| Command | What it does |
|---|---|
| `roborigor validate-config` | Validate a campaign YAML. |
| `roborigor plan` | Expand a campaign; print episode count and cost; write a manifest. |
| `roborigor run-shard` | Run this box's share of a manifest (libero, libero_plus, or mock env). |
| `roborigor summarize` | Aggregate records into summary JSON with Wilson intervals. |
| `roborigor integrity` | Duplicate, missing-episode, and outlier checks against a manifest. |
| `roborigor verify-seeding` | Gate check that per-request seed control works on a policy server. |
| `roborigor varcomp` | Variance-component report (init ICC vs sampling noise) from records. |
| `roborigor knobs` | Knob table and Pareto frontier (denoising steps x exec horizon). |
| `roborigor audit` | Recompute significance of extracted literature comparisons. |
| `roborigor power` | Rollout-budget calculator: MDE at a given n, or required n for a gap. |

## License

[Apache-2.0](LICENSE).
