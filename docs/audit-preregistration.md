# Literature audit pre-registration

Status: FROZEN 2026-08-17 (21:27 local, per repository commit history), on owner instruction in review session (owner
amendments of 2026-08-19 applied first: stratified N=50 intake, unit tags,
iid caveat, benchmark-average rule). From this point sections 1-7 are
immutable; every change is a dated Deviations entry, reported in the paper.

Purpose: measure, rather than assert, (a) the rollout counts the VLA
literature actually uses, and (b) what share of highlighted performance
gaps are statistically distinguishable at those counts. The phrase
"n=50 per task is the field's default" appears nowhere in the paper unless
this audit's data supports it.

## 1. Sampling frame and inclusion criteria

Frozen before any paper is opened.

- Date range: first arXiv submission (v1) between 2024-01-01 and 2026-08-31.
  PINNED 2026-08-17, before any extraction; the window and the N = 50
  target below cannot change after freeze without a Deviations entry.
  (Pre-freeze amendment 2026-08-17, owner review: N raised from 30 to 50;
  intake stratified by year; both changed before any paper was opened.)
- Sources, searched in this order until the target count is reached:
  1. Papers with reported evaluation tables citing any of: LIBERO (Liu et
     al. 2023), OpenVLA, pi0, found via Semantic Scholar cited-by listings.
  2. Entries on the LIBERO-Plus and RoboCasa public leaderboards that link
     a paper.
  3. Accepted papers at CoRL 2024/2025, RSS 2024/2025/2026, ICRA 2025/2026,
     IROS 2024/2025 whose title or abstract names a VLA or manipulation
     policy evaluated in simulation.
- Inclusion: the paper reports task-success rates for at least two policies
  (its own method and at least one baseline) on LIBERO (any suite),
  LIBERO-Plus, RoboCasa, or SimplerEnv.
- Exclusion: real-robot-only evaluations; papers whose only quantitative
  comparison is on a bespoke benchmark; surveys; workshop abstracts under
  4 pages.
- Ordering rule to prevent cherry-picking, stratified so the realized
  sample cannot silently collapse onto mid-2026 papers while the claim
  scope says 2024-2026: the target is N = 50 included papers (floor for
  reporting: N >= 40), split across v1 calendar years as 17 (2024),
  17 (2025), 16 (2026). Within each year stratum, candidates are
  processed in reverse-chronological order of v1 submission and accepted
  or excluded strictly by the criteria above. If a stratum's candidate
  supply is exhausted before its quota fills, the shortfall moves to the
  adjacent year and the imbalance is reported. Regardless, the realized
  v1-date distribution of the sample is reported alongside the outcomes,
  and every claim's stated scope matches the realized sample, not the
  intended window. No paper is skipped for any reason not written here.

## 2. Unit of audit: the highlighted comparison

A highlighted comparison is a pairwise gap the paper itself asserts, not a
table cell we choose. Operational definition, all of:

1. A sentence in the abstract, introduction, or results section claims
   method X outperforms, improves on, or surpasses baseline Y, with or
   without a number, on one of the included benchmarks; and
2. The corresponding success rates and benchmark are recoverable from the
   paper's tables or text.

Benchmark-average claims ("we improve 4.2 points on LIBERO", averaged
over suites) are the most common highlighted form and are IN scope: one
such claim is one comparison, recomputed at the pooled n across the
averaged suites when that n is recoverable (unit tag per-benchmark);
per-suite claims from the same paper count separately only if separately
highlighted. That an average pools suites of unequal difficulty is noted
in extraction but not adjudicated.

Per paper we extract at most the first 3 highlighted comparisons in
reading order (abstract first), to prevent long papers from dominating.
Each comparison record: paper id, benchmark, suite(s), rate X, rate Y,
n per side (see section 3), paired or unpaired protocol as described,
seeds if stated.

## 3. Identifying n (and counting its absence)

Applied in order; the first rule that fires is recorded as the n-source:

1. Explicit rollouts per task and task count stated: n = product, per suite.
2. Explicit total episodes per suite or per benchmark stated: use directly.
3. Trials x seeds stated separately: n = trials x seeds x tasks.
4. Stated only in released code or README: use it, record source as "code".
5. Not recoverable from paper plus code within 15 minutes of search:
   record as NOT REPORTED. The paper stays in the sample; its comparisons
   are excluded from recomputation but counted in the non-reporting rate,
   which is a primary outcome of the audit, not a data-quality footnote.

Per-task versus per-suite disambiguation: every extracted n is recorded
with an explicit unit tag, one of {per-task, per-suite, per-benchmark},
plus the task count used for any conversion. "50 per task" and "500
total over 10 tasks" are the same protocol and must normalize to the
same record; a paper saying only "500 rollouts" with no unit gets unit
AMBIGUOUS, is excluded from recomputation, and is counted in a reported
ambiguity rate alongside the non-reporting rate. Statistical tests use
the n at the granularity of the compared rate (suite-level rates use
suite-level n, never the per-task n).

If X and Y use different n, both are recorded; recomputation uses each
side's own n.

## 4. Recomputation

For every comparison with recoverable n:

- Two-sided Boschloo exact test at the reported rates and stated n
  (unpaired: published numbers are never paired across papers' baselines);
  Fisher reported alongside.
- MDE at 80 percent power and alpha 0.05 for that comparison's n and
  baseline rate, from roborigor.stats.power.
- Independence caveat, pre-registered: recomputation treats pooled
  rollouts as iid binomial, while this paper's own variance decomposition
  shows rollouts are clustered by task, seed, and init state, which makes
  iid-based intervals anti-conservative. The direction is deliberate: iid
  treatment is GENEROUS to the published claims, so the reported share of
  non-significant gaps is a lower bound on the true share. The audit's
  weakest assumption therefore fortifies, not undermines, the finding.
- Where the gap is non-significant AND the Newcombe CI on the difference
  lies within plus or minus 5 points, a TOST equivalence note is recorded;
  "indistinguishable" is claimed only in that case, never from a bare
  non-significant p.

## 5. Pre-registered outcomes

1. Share of highlighted comparisons with exact-test p > 0.05 at stated n
   (also reported uncorrected and Holm-corrected within paper families).
2. Share of highlighted gaps smaller than their own protocol's MDE.
3. Distribution of per-task n across the sample (median, IQR). Scope of
   any claim built on it is the sampled population, stated as "recent
   simulation-benchmark VLA papers (2024-2026, LIBERO-family, RoboCasa,
   SimplerEnv)", never "the field's default" unless the sample
   demonstrably licenses it.
4. Non-reporting rate: share of included papers where n was NOT REPORTED
   under section 3, plus the unit-ambiguity rate from section 3. This is
   a standalone headline statistic of the audit ("X% of papers do not
   state their rollout count"), reported with a CP interval like every
   other proportion in the paper; it is likely less contestable than any
   median.
5. Go/no-go input (registered 2026-08-17, unchanged): claim 1 is viable if
   at least 1/3 of recomputed highlighted gaps fail the exact test at
   stated n, or the median MDE exceeds the median highlighted gap.

## 6. Neutrality rules

- Comparisons are indexed anonymously in the main text ("Gap #14"); the
  full citation table ships in the repo and appendix. Suppressing
  citations entirely would itself be non-neutral.
- Our own baseline reproduction is included as a sample row.
- Comparisons that ARE significant are reported with the same prominence
  as those that are not; the RoboCasa contrast is expected to supply them.
- No author, lab, or method is named in the main text in connection with a
  negative finding.

## 7. Relation to prior audits

Jiang et al. (arXiv 2606.04233) report a LIBERO significance audit. This
audit extends theirs: broader benchmark set, MDE and power analysis per
comparison, non-reporting as an outcome, and equivalence testing. Their
finding is cited as the starting point, and any overlap in sampled papers
is disclosed.

## 8. Deviations log

APPEND-ONLY after freeze: sections 1 through 7 are never edited once the
owner freezes this document; every post-freeze change is expressed solely
as a dated entry here (what changed, why), and the paper reports the log.
A pre-registration that can be quietly edited is not one.

Entry 1 (2026-08-17, post-freeze same evening): Boschloo's exact test is computationally infeasible
for tables with min(n) > 200 in the scipy implementation (minutes to
hours per table). For such comparisons the primary p-value is Fisher
exact, flagged per comparison as fisher_large_n; at these n the tests
agree closely and Fisher is the conservative choice. Boschloo remains
primary for min(n) <= 200. Reason: feasibility; the cap was set (and once
lowered from a first guess of 1000) before any recomputation result was
inspected.
Entry 2 (2026-08-18): Direction chosen AFTER the gate result, per the
registered pivot rule ("no-go: pivot immediately to the denoising-budget
and chunk-horizon study; do not rescue"). Both registered go conditions
failed honestly (rank inversion: 0 flips, null-sim p = 1.0; audit share
32.6% vs the >= 1/3 threshold; median gap 7.2 > median MDE 4.3). The
owner selected a hybrid: the denoising-budget x execution-horizon Pareto
study (the registered pivot) as the paper's spine, the variance
decomposition as its second act, the audit reduced to motivation. NO
CLAIM in the paper rests on either failed gate condition; the negative
rank-inversion result is reported as a finding (rankings stable,
magnitudes not). Recorded here so the post-hoc structure of the paper is
explicit rather than reconstructed.

Entry 3 (2026-08-19): Date normalization. In-document dates written as
2026-08-19 during an overnight session were wrong relative to the
repository's commit timestamps, which are authoritative: the window pin
and freeze occurred 2026-08-17 (commits 20:46 and 21:27), Entry 1 the
same evening (22:29), Entry 2 on 2026-08-18 (20:28). Dates above are
corrected to match; no substantive content changed. Extraction began after the freeze: freeze commit 21:27, first
extraction batch committed 21:59, final batch 22:48, all 2026-08-17.

### Entry 4 (2026-08-21, post-gate armor wave; additive only)
After the draft review, four experiment groups were ADDED beyond the
frozen designs. None alter a registered analysis; all use the frozen
methodology (paired designs, exact tests, CP intervals) on new data:
(a) decomposition replication at environment seeds 8 and 9 (V1
instrument cells, pi0.5); (b) two additional LIBERO-Plus axes (Light
Conditions, Robot Initial States) on frozen per-level variant sets for
all three policies; (c) SmolVLA grid cells (h in {1,5,10} at default
steps, plus the (1,10) frontier cell with num_steps recorded
explicitly); (d) an independent second draw of the camera variant set
at s in {1,10} to power up the registered s=1 vs s=10 camera
comparison (376 -> 632 pairs), which resolved the pre-registered
ambiguity (p=0.076 -> p=0.017, deficit real). The 26-episode h=1
SmolVLA cell was truncated from its planned 160 episodes on cost
grounds after 0/25 successes; its CP upper bound is reported instead
of a point estimate.

### Entry 5 (2026-08-21, two analysis clarifications; no data changes)
(a) Equivalence margin provenance: the +/-5-point TOST margin used for
all equivalence claims was fixed at the 2026-08-18 design reframe,
anchored to the audited median protocol MDE (4.3 points). It predates
the fusion, replication, and camera data but postdates the V2 grid
whose frontier cell it was first applied to; we record it here rather
than claim it was in the original freeze.
(b) Camera analysis correction: Entry 4(d) described the second camera
draw as resolving an ambiguous p=0.076. Subsequent review identified
that p=0.076 was the axes-POOLED equivalence screen; the camera-only
paired test on draw one was already significant (p=0.015, 21-41
discordants). The second draw (predetermined size, 256 variants)
therefore served as replication (22-17), with the pooled two-look
Bonferroni-corrected result p=0.033. The paper reports this corrected
history.

### Entry 6 (2026-08-21, declared before launch)
The SmolVLA h=1 cell (Entry 4(c), truncated at 26 episodes) will be
completed to its DESIGNED size: the original 480-item manifest
(8 tasks x 20 inits x 3 sampling seeds) rerun with episode-granular
resume from the existing 26 records, stopping at manifest completion.
The stop rule is the manifest, fixed before this extension; the final
cell is reported at full n with no interim look.

### Entry 7 (2026-08-21, declared before launch: confirmatory camera sample)
All camera-viewpoint analyses to date (Entries 4(d), 5(b)) are
reclassified as EXPLORATORY. One confirmatory sample is declared now,
before launch: all 376 Camera Viewpoints variants of the fork
libero_10 suite, s in {1, 10} at h=10, TWO fresh replicate draws per
(variant, s) cell with unseeded sampling (1,504 episodes). Stop rule:
manifest completion, no interim look. Single pre-declared analysis:
exact McNemar on discordant pairs pooled over the two draws (paired
within variant and draw), reported with the Newcombe difference
interval. Whatever this sample shows is reported as the confirmatory
camera result; the exploratory draws remain in the artifact.

Entry 7 correction (2026-08-21, before any data): the first launch
failed on a config bug (replicates list vs int) with ZERO episodes
produced. The fork classification counts 419 Camera Viewpoints
variants in libero_10, not 376 (the earlier exploratory draws used a
smaller capped subset). The declared design is unchanged in substance:
ALL camera variants (419), s in {1,10}, two fresh draws, single
analysis at manifest completion; 1,676 episodes.

### Entry 8 (2026-08-21, narrative correction to Entry 4(c))
Entry 4(c) described the SmolVLA h=1 truncation as "after 0/25
successes." The shipped records contradict that narrative: the cell
contains 26 episodes with 2 successes (456 and 321 steps; the other
24 at the 520-step cap). The 0/25 figure came from an interim console
read during the run and was recorded here without re-verification
against the records; the records are authoritative. The truncation
itself (26 episodes, cost grounds) and the Entry 6 completion plan
stand. An adversarial review pass caught this; the paper text now
states the record-backed history.

### Entry 9 (2026-08-21, before confirmatory relaunch)
(a) The first Entry 7 launch attempt after the config-bug fix ran with
num_steps and exec_horizon UNSET in the campaign config: 433 episodes
were collected at the stock default (h=5, server-side steps applied
but unrecorded) instead of the declared s in {1,10} at h=10. These
records are quarantined unanalyzed (no outcome was inspected before
the factor check that caught this); the campaign configs now set both
factors explicitly and the confirmatory sample restarts from zero.
(b) Convention note for Entry 5(b): its "(22-17)" listed the second
camera draw's discordants s=10-wins first. The paper and all data
files report s=1-wins first; the second draw is 17-22 under that
convention. Same data, transposed presentation.

### Entry 10 (2026-08-22, Entry 6 completion executed as declared)
The SmolVLA h=1 cell was completed to its designed n=480 under the
Entry 6 stop rule (manifest completion, no interim look). Result:
266/480 = 0.554, paired every-step cost 9.4 points vs h=10
(CI [3.2, 15.5], p < 1e-4). The truncated 26-episode read (Entry
4(c)) is hereby superseded: those 26 episodes were all task 0, whose
full-cell rate is 9/60; the truncated 2/26 was a task-composition
artifact and the "collapse" reading it suggested was wrong. Paper
text updated accordingly; both the truncated and full records ship
in the artifact as a truncation-bias exhibit.


### Entry 11 (2026-08-22, header date correction per Entry 3)
The Status header dated the pre-freeze owner amendments "2026-08-19";
Entry 3 established commit timestamps as authoritative (freeze and
amendments both 2026-08-17). The header now reads 2026-08-17. Section 1
already carried the correct date. No analysis content changed.

### Entry 12 (2026-08-22, gate-statistic reading disclosed)
Section 5 item 5 states the go/no-go condition as "at least 1/3 of
recomputed highlighted gaps fail the exact test at stated n"; it names
the test but not a multiplicity adjustment, while pre-registered
outcome 1 registers the share "also reported uncorrected and
Holm-corrected within paper families". The statistic computed and
logged when the gate was called is recorded in Entry 2 (2026-08-18):
the uncorrected share, 32.6% vs the >= 1/3 threshold (31.4% after the
Entry 16 recomputation; the gate outcome is unchanged and the margin
widens). We therefore
read the gate as evaluated on the uncorrected rate and report the
Holm-corrected rate (33.7%, computed 2026-08-22) as the registered
secondary outcome. We note explicitly that the corrected rate would
cross the threshold and that adopting it now would convert a failed
gate into a passed one after seeing both numbers; we decline that and
record the reading here instead.

### Entry 13 (2026-08-23, exploratory subset restrictions on the equivalence claim)

The registered comparison of the frontier cell (s=1, h=10) against the
shipped default (s=10, h=5) is fixed-n on the full eight-task battery,
and that is what the paper reports as its confirmatory result. Two
additional analyses were run after seeing that result and are labeled
exploratory wherever they appear:

(a) An init-cluster bootstrap of the *paired* difference, added because
the registered interval is Newcombe's (unpaired) and clustering could
in principle widen it enough to break the +/-5 margin. It does not:
[-1.04, +3.96] against Newcombe's [-1.16, +4.14]. A task-cluster
bootstrap is narrower still, [+0.21, +3.33], because task difficulty
cancels in a paired difference; we report the init-cluster interval as
the conservative one and do not claim the task-cluster result.

(b) The same comparison restricted to tasks with headroom at the
reference condition. Seven of eight tasks score above 0.96 at the
default and two score 1.000, leaving six non-ceiling tasks; the two ceiling tasks contribute 120
concordant pairs and zero discordant pairs. On the six non-ceiling
tasks the interval is [-1.11, +5.56]; on task 8, the only task with at
least five points of headroom, it is [-10.00, +23.33] at n=60. The
+/-5 equivalence verdict therefore holds on the battery as registered
but is not established on the informative subset, and the paper now
says so. The point estimate favors the frontier in all three subsets
(+1.5, +1.9, +6.7 points).

Neither analysis changes a registered outcome; (b) is reported because
withholding it would leave the registered verdict looking stronger
than the data support.

### Entry 14 (2026-08-23, latency reported as measured rather than modeled)

The Pareto axis and the latency figures in the paper were originally
the uncontended per-component cost model (prefix 53.2 ms, 2.79 ms per
ODE step, amortized over the execution horizon). Those are now
replaced by the server-side inference time actually recorded in the
5,760 released grid episodes, pooled per cell and amortized the same
way. The change was made because the modeled numbers are a claim about
hardware while the recorded ones are a measurement of the runs the
paper reports, and the paper should not model what it already
measured.

The two agree within 10%: the shipped default is 17.81 ms per executed
step measured against 16.22 modeled, and the frontier cell is 6.72
against 5.60, so the reduction is 2.65x measured against 2.90x
modeled. The paper now reports 2.7x and names the model as the
cross-check. The measured figures run under the campaign's six-worker
GPU contention and are therefore the conservative of the two. The
Pareto frontier is the single cell (1,10) under both axes, so no
conclusion changes; only the numerals do.

### Entry 15 (2026-08-24, clean-anchor seed provenance disclosed)

The clean anchors used as the unperturbed reference in the perturbation
section (pi0.5 0.960, pi0 0.795, SmolVLA 0.645; 200 paired episodes
each) were collected with the sampling seed left uncontrolled, as were
the perturbed runs they are compared against. The comparison is
therefore internally consistent, but each anchor is a single draw and
carries the seed noise this paper measures elsewhere.

Rerunning the pi0.5 anchor configuration across the ten sampling seeds
of the reseed sweep, restricted to the anchor's own inits 0-19, gives
96.0, 94.0, 92.5, 92.5, 94.0, 93.5, 94.0, 93.0, 94.0, 92.5 (mean 93.6,
SD 1.02). The anchor equals the maximum of that band. On the ten-seed
mean the clean pi0.5-pi0 gap is 14.1 points rather than 16.5.

No seed-replicated data exist at the anchor configuration for pi0 or
SmolVLA, so an all-policy seed-averaged anchor cannot be constructed
from the released record and we do not report one. The paper now states
the provenance, the band, and the gap under the seed mean, rather than
presenting 16.5 as a point value. The two-regime conclusion of that
section turns on gaps moving by tens of points and is unaffected.
scripts/analyze_anchor_seed_sensitivity.py regenerates these numbers and
the drift checker pins them.

### Entry 16 (2026-08-24, Boschloo cap raised; Entry 1 justification corrected)

Entry 1 set the Boschloo cap at min(n) <= 200 on the stated grounds that
the test is "computationally infeasible" above it and that "at these n
the tests agree closely". Re-measuring on the reference machine, both
claims were wrong. Boschloo terminates in 0.3 s at n = 216, 1.1 s at
n = 400, 9.3 s at n = 900 and 74 s at n = 2000, and the two tests do not
agree closely: at n = 216 with a 3-point gap Boschloo gives 0.571
against Fisher's 0.630, a difference large enough to change a
significance verdict at alpha = 0.05.

The cap is therefore raised to min(n) <= 2000, which covers 54 of the 64
comparisons Entry 1 had routed to Fisher, and the audit is recomputed.
Above 2000 the runtime is genuinely prohibitive (superlinear; the
largest comparison in the corpus is n = 10030) and Fisher remains
primary there, flagged per comparison as before. Fisher is the
conservative direction: it returns the larger p-value, so a remaining
substitution can only push a comparison from significant to failing,
never the reverse, and therefore cannot deflate the reported failure
rate.

This correction moves a headline number after the fact. We record that
explicitly: the pre-registered primary test was always Boschloo, Entry 1
was a feasibility deviation from it, and this entry narrows that
deviation rather than widening it. The recomputed figures replace the
earlier ones throughout the paper.

### Entry 17 (2026-08-24, second adversarial pass; claims narrowed to what is computed)

A second red-team pass over the revised draft confirmed fourteen
defects, all of which are corrected here. Four are worth recording as
substantive rather than editorial.

(a) Variance mechanism withdrawn. Sec. VI previously read a mechanism
off the per-cell sampling components ("rises as steps fall at h=1 and
flattens at h=10, so frequent replanning re-exposes the trajectory to
the noise"). The beta-binomial sampling component is mu(1-mu)(1-ICC),
so across grid cells whose success rates run 0.642 to 0.965 it largely
tracks the base rate. The base-rate-free share stays within 0.45-0.55
across the h=1 column with no monotone trend, which is not a
mechanism, and at h=10 the raw
component falls 0.052 to 0.023 rather than flattening, so the original
sentence was also wrong on its own terms. The claim is withdrawn and
replaced with an explicit statement of why we decline to read a
mechanism from these cells. The coupling itself, which is an
empirical fact about success rates, is unaffected.

(b) "Design-effect correction" withdrawn as a contribution. The paper
claimed one in the abstract, the contributions list, and four body
locations, but no design effect is defined or computed anywhere and no
such code ships. What the study actually measures is the paired-design
relative efficiency (1.4-2.3x, docs/paper-data/pairing_efficiency.json).
Every occurrence now names that quantity instead.

(c) Anytime-validity claim corrected in the other direction. Entry 16's
predecessor fix removed a mischaracterization of STEP as anytime-valid,
but replaced it with a claim that our own paired e-process is
anytime-valid "instead". That was doubly wrong: the STEP successor is
explicitly built on safe anytime-valid inference, so the property is
prior art in the very reference being distinguished, and this paper
reports no e-process anywhere (a single e-value sits in the released
JSON and is not analyzed). Related Work now credits the successor with
anytime-valid inference and claims no sequential theory of our own.

(d) Artifact staleness gated. The shipped artifact/ tree carried an
audit file with the pre-Entry-16 failure rate, contradicting the
paper's own headline at the location reviewers are pointed to. It is
regenerated, and check_paper_numbers.py now fails if any shipped
artifact file diverges byte-for-byte from its source.

Also corrected: the first author of the LIBERO benchmarking audit
(Tianchong Jiang, previously miscited as "Ying Jiang"); OpenVLA-OFT
described as autoregressive when its contribution is parallel decoding;
the anchor seed-band SD computed with the population rather than the
sample estimator (1.0 -> 1.1), now pinned to the paper's convention;
layout figures attributed to the 376-variant camera set when the layout
set is 312; and an overstated "the saturated tasks stay degenerate" in
the environment-seed replication, where the replicated set contains one
saturated task that falls below the threshold at the second seed.

### Entry 18 (2026-08-24, nondeterminism estimated directly; headline reattributed)

Entries 1 through 17 reported system nondeterminism as a single pooled
replicate-disagreement rate, 7.6% over 144 cells, and used it as a
loose upper bound on the nondeterminism share of the within-init
variance component. Disaggregating by task shows the pooled figure is
not a bound for the task the decomposition is measured on:

  task0 0.0%   task1 0.0%   task2 16.7%   task3 0.0%
  task4 0.0%   task6 0.0%   task8 38.9%   task9  5.6%

Five of eight tasks contribute zero disagreement because they are
saturated and cannot flip, so pooling over them understates the rate
on the informative task by roughly a factor of five. This is the
aggregation error the paper criticizes elsewhere, committed in the
paper's own instrument, and we record it as such.

The replicate block fixes every factor (task, initial state,
environment seed, sampling seed, dials), so within-cell variance is
system nondeterminism by construction and can be estimated directly
rather than bounded. On the informative task the component is 0.111
with a 10,000-draw cluster bootstrap 95% interval of [0.046, 0.176].
The resulting three-way split of that task's 0.242 total variance is
initial state 15.5%, flow sampler 38.5% [12, 65], system
nondeterminism 46.0% [19, 73].

Consequences for the paper's claims, stated plainly:

(a) The 61-84% figure is unchanged and is now attributed correctly. It
is the share of outcome variance that survives fixing the initial
state, which is what a rollout budget must buy regardless of whether
the noise originates in the sampler or the machine. Every budget,
power, and design-efficiency result is unaffected.

(b) The comparative claim in the title holds at the point estimate:
the sampler's 38.5% exceeds the initial state's 15.5% by 2.5x. It does
not hold at the upper end of the nondeterminism interval, where the
sampler falls to 12% against the initial state's 15.5%. The paper now
states this rather than asserting the ordering unconditionally.

(c) The earlier claim that charging the whole bound against the
sampler "still leaves it 43-69%, above the initial state in every
case" is withdrawn. It rested on the pooled bound.

(d) The split is measured on pi0.5 only. The replicate block is the
sole source of fully-fixed-factor repeats in the released record;
pi0 and SmolVLA have none, so for those two policies only the combined
within-init share is reported, and Fig. 1(a) marks them as such. A
seed-and-replicate block on the other two policies is the obvious next
measurement and we do not claim their split.

scripts/analyze_nondeterminism.py regenerates every number here and
the drift checker pins them, including a guard that fails the build if
the sampler share ever stops exceeding the initial state.

### Entry 19 (2026-09-03, manuscript structure returned to the Entry 2 spine; title changed)

Entry 2 recorded the paper's structure after the gate: the
denoising-budget x execution-horizon Pareto study as the spine, the
variance decomposition as the second act, the audit reduced to
motivation. Between Entries 12 and 18 the manuscript drifted from that
structure: its title ("Same Scene, Different Answer: Variance and
Rollout Budgets for Flow-Policy Evaluation"), abstract, introduction,
and section order came to lead with the variance decomposition, with
the Pareto study in the sixth section and a conclusion that did not
mention it.

The submitted manuscript is returned to the Entry 2 structure. The
title is now "The Shipped Default Is Dominated: Powered Equivalence for
Flow-Policy Inference Dials from a Decomposition of Evaluation
Variance". The abstract, introduction, contributions list, and
conclusion lead with the factorial result and its scope (the +/-5
equivalence margin, the near-ceiling battery, the camera-viewpoint
cost, pi0's refusal of the cut) and present the decomposition as what
makes that result a certificate rather than an anecdote. The Pareto
section now precedes the variance and budget sections; the Pareto
figure is Figure 1 and the decomposition figure opens the variance
section.

What did not change: every analysis, number, interval, p-value,
figure, table, exploratory/confirmatory label, and scope statement.
Body paragraphs were moved, not rewritten; the only new prose is the
abstract, the introduction, two section headings, one lead-in sentence
in the variance section, the pointer to this entry in the protocol
section, and the conclusion. scripts/check_paper_numbers.py passes
unchanged on the reordered source. Recorded so that the submitted
structure matches the registered one and the change of emphasis is
visible in the log rather than reconstructed from it.

Same-day addendum (2026-09-03): the title above was shortened to "The Shipped Default Is Dominated: Powered Equivalence for Flow-Policy Inference Dials" before submission; the decomposition clause moved from the title to the abstract's fourth sentence. No other change.
