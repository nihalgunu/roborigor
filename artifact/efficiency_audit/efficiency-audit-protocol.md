# Efficiency-claim audit protocol (written 2026-09-13 17:35 PDT, before any extraction)

Purpose: measure whether "no loss" claims made by VLA inference-efficiency
papers on LIBERO rest on the ceiling regime that the main analysis shows
can certify parity without evidence. Exploratory and post-freeze relative
to docs/audit-preregistration.md; logged as its Entry 21. This file is not
edited after extraction begins; changes are appended below as dated notes.

## 1. Sampling frame

- arXiv v1 between 2024-01-01 and 2026-09-12.
- Source A (primary, deterministic): the arXiv API query in
  `scripts/efficiency_audit_search.sh`, run once; its raw output is saved.
- Source B (snowball): papers named in the related-work or baseline tables
  of included papers that meet the criteria. Recorded with the citing paper.
- Source C (search engines): Semantic Scholar and web keyword searches for
  VLA acceleration methods evaluated on LIBERO; every query string and the
  candidates it returned are logged in docs/efficiency_audit/sourceC_log.md.
- Sources are unioned and deduplicated by arXiv id before screening. A
  candidate's source does not affect whether it is included.
- No cap on N: every candidate meeting the criteria is included. Coverage
  limits are reported, not managed by selection.

## 2. Inclusion

All of:
1. The paper's primary contribution reduces inference cost (latency, FLOPs,
   memory, parameters, denoising steps, visual or action tokens, bit width)
   of an existing VLA policy: step reduction or distillation, caching or
   reuse, token pruning or merging, quantization, early exit or layer
   skipping, speculative or parallel decoding, adaptive chunking for speed.
2. It reports task success on LIBERO (any suite) in simulation for both the
   accelerated method and its own base policy (same backbone).
3. It asserts parity or acceptable loss for the method against the base on
   LIBERO in the abstract, introduction, results, or conclusion
   ("comparable", "maintains", "without/negligible/minimal loss",
   "preserves", "on par", "no degradation", or a stated loss described as
   small). Papers claiming only strict improvement are counted separately
   and excluded from outcomes O1-O8.

Exclusion: new small policies trained from scratch without a same-backbone
base; real-robot-only evaluation; surveys; workshop abstracts under 4 pages.

## 3. Unit and extraction

One primary claim per paper: the method configuration the abstract
highlights, against its base, on the LIBERO aggregate the paper highlights
(suite average if so). For the within-paper analysis, every other benchmark
on which the same configuration is compared to the same base is also
recorded. Per claim: base policy; method family; quote and location; base
and method success rates; episodes per suite and per task (with source
rule as in the main audit: explicit, derived, code, NOT-REPORTED);
per-task results shown (y/n); any uncertainty reported (CI, SD, seeds,
test; y/n and which); evaluation seeds stated; pairing or discordant pairs
reported; speedup claimed. Extraction reads full text including
appendices, with verbatim evidence for every non-null field.

## 4. Outcomes (fixed now)

- O1: share of parity claims whose base rate is >= 0.90.
- O2: share reporting any uncertainty for the claim.
- O3: share reporting per-task results for the claim benchmark.
- O4: share with a usable episode count.
- O5: share reporting paired or discordant-pair information.
- O6: median absolute gap (method minus base, points) and median
  failure-rate ratio (method failures / base failures).
- O7: among claims with usable n, share whose unpaired Newcombe interval
  for the difference lies within +/-5 points (certifiable at the suite
  level) and, of those, share whose failure-rate ratio 95% interval (Katz
  log) has an upper bound >= 1.5 (cannot rule out 50% more failures).
- O8: within papers reporting the same method-vs-base comparison on
  LIBERO and on a benchmark with base rate < 0.80: sign test of whether
  the absolute loss is larger on the lower-base benchmark, and the same
  for failure-rate ratio.

## 5. Rater

Screening and extraction are LLM-assisted over full text. Before any number
is reported, a seeded random sample of at least 20% of included papers is
re-verified by direct text search of the PDFs for every extracted rate and
episode count, and the disagreement rate is reported. A human spot-check of
the same sample is required before submission.

## Amendment 1 (2026-09-13, before any extraction)

The arXiv API returned "Rate exceeded" on all eight scheduled attempts
(log in the session; scripts/efficiency_audit_search.sh unchanged). Source A
is therefore replaced by one fixed Semantic Scholar bulk-search query,
`scripts/efficiency_audit_search_s2.sh`, whose raw JSON output is saved to
docs/efficiency_audit/s2_raw.json. Sources B and C are unchanged. No
candidate had been screened or extracted when this amendment was made.
Screening is two-stage: (1) title and abstract against Section 2, keeping
any candidate that might qualify; (2) full text for the survivors, where
Section 2 is applied strictly and Section 3 is extracted. Both stages are
logged per candidate with a reason.

## Amendment 2 (2026-09-13, after extraction of Sources A and C)

Source B was run in a limited form: extractors recorded, while reading each
full text, any cited paper that appeared to meet Section 2; those not already
in the candidate set were screened in a final batch (batch_7). A systematic
walk of every included paper's related-work and baseline tables was not done;
coverage is reported as a limitation. Separately, batch files built for
extraction attached a wrong abstract to candidates without an arXiv id; the
extractors detected this and screened those candidates on title or on the
correct abstract from s2_raw.json, as recorded in their notes.

## Amendment 3 (2026-09-13, public release)

The design documents referenced in the header (the earlier audit's
pre-registration and its log) are not part of the public release. Nothing
in the protocol's rules, outcomes, or results depends on them.
