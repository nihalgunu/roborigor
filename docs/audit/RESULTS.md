# Audit results (N=50)

Sample: 16 (2026) + 17 (2025) + 17 (2024) papers, 131 highlighted
comparisons, walked newest-first per the intake rule in candidates.md.

## Outcomes

1. Share of recomputable highlighted comparisons with exact-test p > 0.05
   at the papers' own stated n: 27/86 = 31.4% (Boschloo's exact test up to
   min(n) <= 2000, Fisher above).
2. Share of recomputable gaps below their own protocol's MDE (80% power):
   41/86 = 47.7%.
3. Median |highlighted gap| 7.2 points; median MDE 4.3 points.
4. Non-reporting: 34.4% of highlighted comparisons (45/131) have unusable n
   (NOT-REPORTED or AMBIGUOUS). Per paper: 13/50 = 26% [CP95 15-40%] have no
   usable n on any extracted comparison (two further papers publish rates only
   as figures and yielded no extractable comparisons); 42% [CP95 28-57%] have
   at least one unusable comparison. Evaluation seed counts stated for 31/131.
5. Per-task n where derivable (n=85 comparisons, suite and benchmark counts
   normalized by task count): median 50, IQR [20, 50], range [2.4, 450].

## Structural findings from extraction (all quoted, all sourced)

- Asymmetric evidence: 11 comparisons pit the authors' own method at
  known n against baseline rates copied from other papers at unknown n.
- Two included papers publish success rates only as bar charts.
- pi0 (2410.24164) and RDT-1B (2410.07864) v1s are real-robot-only: the
  two most-benchmarked-against policies have no in-scope simulation evaluation
  in their own first versions.
- No audited paper states LIBERO-Plus trial counts.
- Arithmetic and consistency flags: a relative-improvement claim matching
  the wrong baseline; abstract vs table discrepancies; a best-of-10-
  checkpoints selection compared against cited single-run baselines;
  baselines quoted from other papers after the authors' own reproduction
  scored lower.
