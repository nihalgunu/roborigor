# Paper outline v2 (frame set by owner 2026-08-18: three dials, Pareto spine)

Title territory (final in week 4): "Three Dials of Flow-Policy Inference:
What Actually Moves VLA Success Rates". Not the audit-flavored provocation.

Frame: flow-VLA inference has three dials everyone sets by folklore:
denoising steps, execution horizon, sampling seed. This paper
characterizes all three under a significance-first protocol. Two (steps,
horizon) have sharp Pareto structure the field leaves on the table; the
third (seed) is not a dial at all but contributes spread comparable to
the field's median claimed improvement. Tone: the data says the field's
rankings are MORE trustworthy than assumed; its efficiency and its
uncertainty reporting are what need work. Good news, delivered rigorously.

8 pages TOTAL incl. references (ICRA 2027, CFP-verified).

## I. Introduction (~0.9 pp)
- Folklore dials: num_steps=10, replan=5, seed unreported. Nobody
  measures what they cost or buy.
- One motivating audit figure: 34.4% of highlighted comparisons in 50
  recent papers carry no usable rollout count; at the common n=50/task,
  the MDE is ~18 points (measured). So the dials are set blind AND the
  measurements are underpowered.
- Contributions: (1) the (steps x horizon) Pareto map with exact CIs:
  a single Euler step at horizon 10 matches or beats the 10-step default
  at 3x lower control latency; (2) the seed decomposition: sampling
  spread 7.5 points, at parity with the field's median claimed gap of
  7.2; (3) the significance-first protocol + budget calculator + logs
  artifact that makes (1)-(2) trustworthy; (4) honest negative: under
  perturbation, RANKINGS are stable (0 inversions, null-sim) even as
  gaps explode 3-10 pts -> 46-50 pts; the field's ordering is sound, its
  robustness margins are not.

## II. Related work (~0.6 pp)
RTC (2506.07339) as the deployment-side counterpart of the horizon dial;
SnapFlow/FlowPRO (steps-as-improvement-lever; we measure steps-as-
evaluation-variable); Jiang et al. audit (motivation, extended); STEP +
Beyond Binary Success (testing machinery we build on); LIBERO-Plus (we
run), LIBERO-PRO (cite-only); PhAIL.

## III. Protocol (~0.9 pp)
Paired-by-init design, CP-primary intervals, exact tests + corrections,
seed schedule semantics (episode seed = noise stream, chunk-derived),
determinism audit (bitwise per-request; 7.6% closed-loop residual),
harness architecture in one figure. Pre-registration + deviations log
referenced openly.

## IV. Dial 1 and 2: the Pareto map (~1.5 pp) [SPINE]
- 12-cell grid, n=480/cell, CP CIs; frontier = (ns=1, eh=10): 0.965 @
  5.6ms vs default (10,5): 0.950 @ 16.2ms. 5-10x per-chunk inference cut
  essentially free ON THIS BENCHMARK.
- Interaction: at eh=1 steps matter (0.64->0.85); at eh=10 they invert.
- SCOPE PARAGRAPH (owner-mandated): LIBERO is quasi-static; tight
  closed-loop control exists for reactivity (cite RTC as the deployment
  counterpart). The claim is benchmark-conditional by construction and
  stated so.
- Fusion result (Sec 4.4): does the cheap-steps frontier survive
  distribution shift? ns in {1,2,10} at eh=10 under Camera Viewpoints +
  Objects Layout perturbations (identical variant sets). [running]
- Variance interaction: sampling share rises as steps fall at eh=1
  (0.117 -> 0.058), flattens/inverts at eh=10: the dials couple.

## V. Dial 3: the seed (~1.2 pp) [SECOND ACT]
- Not a dial: an unreported random factor. Protocol spread 7.5 pts
  (sd 2.4) across 10 seeds of the standard 500-episode protocol; the
  field's median highlighted gap is 7.2 pts.
- Nested decomposition (beta-binomial + MoM + bootstrap): flow noise
  dominates at fixed inits on informative tasks (task 8: 0.204/0.25);
  saturation exhibit (3 of 4 suites have no task in p [0.5,0.95]).
- What this costs the field: required-n table; budget calculator; DEFF
  for sequential testing.

## VI. Honest negatives and the audit figure (~0.7 pp)
- Rank stability under perturbation: 3 policies x 688 variants, 0
  inversions (tau=1.0, null-sim p=1.0); magnitudes collapse. Ordering
  trustworthy; robustness margins not. Registered thresholds and their
  honest misses reported (32.6% vs 1/3), deviations log cited.
- Audit: one figure (non-reporting + MDE-vs-gap scatter); neutrality
  rules; full table in repo.

## VII. Limitations + release (~0.4 pp)
Sim-only; LIBERO-family scope; single env seed in V1; SmolVLA weakness
on long-horizon tasks (10/10 spatial vs 3/10 libero_10) as a caution on
suite-pooled rankings. Release: pip roborigor, logs artifact, one-script
figures.

## Figures (6)
1. Pareto map: SR vs control-latency, 12 cells + frontier (hero).
2. Steps x horizon interaction panel (+ sampling-share overlay).
3. Seed-spread strip: 10 protocol replicates vs median claimed gap line.
4. Variance stacks per task (saturated tasks greyed).
5. Perturbation: gap explosion + stable ordering (3 policies, 2 axes).
6. MDE/audit motivating figure.
