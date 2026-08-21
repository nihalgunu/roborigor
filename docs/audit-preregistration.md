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
