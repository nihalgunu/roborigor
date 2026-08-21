# Stage-1 gate package (owner review, ~90 min)

Everything the methodology freeze covers, with the exact commands.

STATUS: signed off 2026-08-19 by owner go-ahead in session; the
independent spot-check (sections 1-2) remains open and recommended.
Reported-grid GPU runs and audit extraction are unblocked.

## 1. Reproduce (20 min)
    uv venv && uv pip install -e ".[dev,stats]"
    .venv/bin/pytest -q                       # 77 tests
    .venv/bin/python scripts/replay_baseline_stats.py \
        ../flowhelm-lab/results/baseline-2026-08-15
    # expect MDE 18.3 / 4.6 / 2.5 points at n=50/500/1500

    .venv/bin/roborigor plan configs/pilot_smolvla_libero10.yaml --out /tmp/m.json
    .venv/bin/roborigor run-shard --manifest /tmp/m.json --box-id box0 \
        --out-dir /tmp/rec --env mock
    .venv/bin/roborigor integrity /tmp/rec --manifest /tmp/m.json

## 2. Spot-check (30 min)
- clopper_pearson(461, 500) vs scipy.stats.beta.ppf by hand.
- mcnemar_exact on a 2x2 you construct vs statsmodels.
- One glance at rollout/runner.py::chunk_seed and its tests
  (test_chunk_seed_schedule_semantics): the seed-schedule fix.

## 3. Decisions to freeze (sign-off list)
1. Comparison methodology: paired exact McNemar primary, Boschloo/Fisher
   unpaired for the audit; Holm confirmatory family, BH exploratory.
2. Intervals: CP primary, Wilson alongside, Newcombe for differences.
3. V1 design: configs/v1_varcomp_pi05.yaml (2,176 eps, ~$4): 4 qualifying
   tasks + 4 saturated-exhibit tasks, task 8 concentrated (40 inits),
   S=10 sampling seeds, residual block 4 replicates at off-grid seeds.
4. V2 design: configs/v2_knobs_pi05.yaml (5,760 eps, ~$19 with eh1 3x).
5. Go/no-go thresholds (registered 2026-08-17): tau <= 2/3 with null-sim
   p < .05 on >= 1 axis, OR >= 1/3 audited gaps fail at stated n.
6. Prereg freeze: docs/audit-preregistration.md (amendments of 2026-08-19
   applied: stratified N=50, unit tags, iid caveat, average-claims rule).
7. Seed schedule semantics: episode seed = noise stream id via
   chunk_seed (owner-reviewed 2026-08-19, implemented same day).

## 4. Already verified on GPU (2026-08-19, session 1, $2)
- verify-seeding: PASS bitwise (policy._rng per request).
- Paired smoke: 10/10 agreement vs baseline on identical cells.
