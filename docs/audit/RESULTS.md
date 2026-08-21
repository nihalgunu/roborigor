# Audit results vs pre-registered outcomes (final, N=50, 2026-08-17)

Sample complete: 16 (2026) + 17 (2025) + 17 (2024) papers, 131 highlighted
comparisons, walked newest-first per the frozen intake rule.

## Registered outcomes

1. Share of recomputable highlighted comparisons with exact-test p > 0.05
   at the papers' own stated n: 28/86 = 32.6%.
2. Share of recomputable gaps below their own protocol's MDE (80% power):
   41/86 = 47.7%.
3. Median |highlighted gap| 7.2 points; median MDE 4.3 points.
4. Non-reporting (headline): 34.4% of highlighted comparisons (45/131)
   have unusable n (NOT-REPORTED or AMBIGUOUS). Per paper: 13/50 = 26%
   [CP95 15-40%] have no usable n on any EXTRACTED comparison (two
   further papers publish rates only as figures and yielded no
   extractable comparisons at all); 42% [CP95 28-57%] have at least one
   unusable comparison. Eval seed counts stated for only 31/131.
5. Registered outcome 3 (computed 2026-08-19 from the frozen
   extraction): per-task n where derivable (n=85 comparisons, suite and
   benchmark counts normalized by task count): median 50, IQR [20, 50],
   range [2.4, 450]. The phrase "the field's default of 50 per task" is
   licensed by this measurement.

## Go/no-go condition (b), read against the frozen thresholds

Clause 1 (>= 1/3 fail exact tests): 32.6% < 33.3%. NOT MET (marginal).
Clause 2 (median MDE > median gap): 4.3 < 7.2. NOT MET.
Condition (b) therefore does NOT carry the paper alone. The gate now
rides on condition (a), clean-vs-perturbed rank instability, which awaits
the LIBERO-Plus pilot. The variance decomposition (co-headline) is
independent of the gate conditions and unaffected.

## Structural findings banked during extraction (all quoted, all sourced)

- Asymmetric evidence: 11 comparisons pit the authors' own method at
  known n against baseline rates copied from other papers at unknown n.
- Two included papers publish success rates ONLY as bar charts.
- pi0 (2410.24164) and RDT-1B (2410.07864) v1s are real-robot-only: the
  two most-benchmarked-against policies have no in-scope sim eval in
  their own first versions.
- No audited paper states LIBERO-Plus trial counts.
- Arithmetic and consistency flags: a relative-improvement claim matching
  the wrong baseline; abstract vs table discrepancies; a best-of-10-
  checkpoints selection compared against cited single-run baselines;
  baselines quoted from other papers after the authors' own reproduction
  scored lower.
