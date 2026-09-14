# RoboRigor

**Evaluating VLA policies at scale: a harness, 31,858 released episodes, and what they show about "no loss" claims.**

VLA acceleration papers (fewer denoising steps, caching, token pruning, quantization) justify their speedups by showing no loss against the base policy on LIBERO, where base policies typically succeed in more than 90% of episodes. Using this toolkit on released pi0.5, pi0, and SmolVLA checkpoints, we find that such no-loss verdicts are supplied largely by tasks both settings already solve:

- One denoising step is equivalent to ten within +/-5 points for pi0.5 on an eight-task LIBERO-10 battery, but inconclusive on the four tasks classified as informative before the experiment ([-2.0, +7.1] points).
- Across all 79 paired comparisons in our grids, 18 certify equivalence on the battery. At equal episode counts the four saturated tasks keep 17 of those certificates and the four informative tasks keep 1, while the informative tasks keep 57 of 59 significant differences.
- Where failures are common, the verdicts diverge: one step costs pi0 7.9 points (p=0.00025) and pi0.5 4.7 points under large camera-viewpoint shifts (p=0.0008).
- Among 86 VLA efficiency papers claiming parity on LIBERO, 76% compare against a base policy at or above 90% success, and 15 report any uncertainty, per-task result, or paired analysis.

## Outputs

| | What | Where |
|---|---|---|
| Paper | *Certified by the Ceiling: Saturated Benchmarks Supply the No-Loss Claims Behind VLA Acceleration* | [`paper/`](paper/) |
| Toolkit | Paired evaluation harness, exact statistics, and the `roborigor report` check for no-loss claims | [`src/roborigor/`](src/roborigor/) |
| Data | Per-episode records for every experiment, with a datasheet | [`artifact/`](artifact/), [`docs/DATASHEET.md`](docs/DATASHEET.md) |
| Audits | 86 efficiency papers' no-loss claims; reporting practice in 50 VLA papers | [`docs/efficiency_audit/`](docs/efficiency_audit/), [`docs/audit/`](docs/audit/) |

## Check a no-loss claim on your own results

```bash
pip install -e ".[stats]"

roborigor report \
  --a artifact/v2_knobs --a-where num_steps=1,exec_horizon=10 \
  --b artifact/v2_knobs --b-where num_steps=10,exec_horizon=10 \
  --informative-tasks 0,2,8,9
```

```
no-loss report (margin +/-5 pts, failure-ratio bound 1.5)
all tasks          n=480    96.5% vs  94.6%  diff  +1.9 [-0.7, +4.5]  b-c 23-14  p=0.188  OR [0.81, 3.45]  -> EQUIVALENT
informative [0, 2, 8, 9] n=240    94.2% vs  91.7%  diff  +2.5 [-2.0, +7.1]  b-c 17-11  p=0.345  OR [0.68, 3.65]  -> INCONCLUSIVE
failure ratio A/B 0.65 [0.31, 1.21]  -> within bound
warning: equivalence on all tasks does not hold on the informative tasks; the certificate is supplied by tasks both settings solve
```

The report gives the discordant pairs with an exact conditional odds-ratio interval (which solved tasks cannot move), the paired Newcombe interval on all tasks and on tasks declared informative in advance, and a failure-rate ratio against a declared bound. Absolute margins are lenient when failures are rare and relative margins when failures are common, so it reports both.

## Run your own evaluation

```bash
# Plan a campaign: expand a YAML config into an episode manifest.
roborigor plan configs/pilot_smolvla_libero10.yaml --out /tmp/m.json

# Dry-run the runner against the built-in mock environment (no GPU, no sim).
roborigor run-shard --manifest /tmp/m.json --box-id box0 --out-dir /tmp/rec --env mock

# Check the records for duplicates, gaps, and outliers against the manifest.
roborigor integrity /tmp/rec --manifest /tmp/m.json
```

The same commands drive real campaigns: point `--env` at `libero` or `libero_plus`, serve a policy behind the websocket interface (`scripts/serve_openpi.py`, `scripts/serve_smolvla.py`), and shard the manifest across GPU boxes (`scripts/setup_gpu_box.sh`, `scripts/campaign_box.sh`). A killed worker loses at most one episode; resume is exact at episode granularity via each record's cell key.

## CLI

| Command | What it does |
|---|---|
| `roborigor report` | Three-part report for a no-loss claim between two settings. |
| `roborigor validate-config` | Validate a campaign YAML. |
| `roborigor plan` | Expand a campaign; print episode count and cost; write a manifest. |
| `roborigor run-shard` | Run this box's share of a manifest (libero, libero_plus, or mock env). |
| `roborigor summarize` | Aggregate records into summary JSON with Wilson intervals. |
| `roborigor integrity` | Duplicate, missing-episode, and outlier checks against a manifest. |
| `roborigor verify-seeding` | Check that per-request seed control works on a policy server. |
| `roborigor varcomp` | Variance components (initial state vs. within-init) from records. |
| `roborigor knobs` | Success and latency table over denoising steps x execution horizon. |
| `roborigor audit` | Recompute significance of extracted literature comparisons. |
| `roborigor power` | Rollout-budget calculator: MDE at a given n, or required n for a gap. |

## Reproducing the paper

Every number in the paper regenerates from the per-episode records:

```bash
python scripts/analyze_step_transfer.py      # one-step contrasts, dilution curve
python scripts/analyze_dilution_census.py    # all 79 paired comparisons, subset controls
python scripts/analyze_failure_ratio_and_shift.py    # failure ratios, camera levels, per-task seeds
python scripts/analyze_efficiency_audit.py   # outcomes of the efficiency-paper audit
python scripts/make_figures.py               # figures
python scripts/check_paper_numbers.py        # pins every number in paper/main.tex to the data
```

See [`scripts/README.md`](scripts/README.md) for the full index.

## Repository layout

| Path | Contents |
|---|---|
| `src/roborigor/` | The pip-installable package: schema and config (py3.8-safe), stats, rollout runner, campaign tools, env adapters, policy server. |
| `paper/` | Paper source, generated tables, and figures. |
| `artifact/` | Released per-episode records and derived reports (`python scripts/package_artifact.py`). |
| `docs/` | Datasheet, audits, paper data, release checklist. |
| `scripts/` | Serving, provisioning, analysis, figures, packaging. |
| `configs/` | Campaign YAMLs. |
| `tests/` | 92 tests including Monte-Carlo coverage checks and golden-value pins. |

## License

[Apache-2.0](LICENSE).
