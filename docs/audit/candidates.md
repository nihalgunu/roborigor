# Audit candidate lists (intake enumeration, 2026-08-19)

Produced per frozen prereg section 1, BEFORE any inclusion decisions or
extraction. Sources: (1) arXiv abstract search for the four benchmarks,
v1-windowed, plus Semantic Scholar cited-by of LIBERO/OpenVLA/pi0;
(2) LIBERO-Plus and RoboCasa leaderboards. Source 3 (conference sweeps)
spot-checked as redundant with 1-2, not independently exhausted (noted).
Full harvest with abstracts and v1 dates: harvest_kept.json (570+ rows),
harvest_s2_citations.json. v1 dates from the arXiv API published field.

Supply: 2026 = 414 candidates, 2025 = 143, 2024 = 38 (thinnest; still
comfortably above the 17 quota after attrition; two seeds likely fail
inclusion for lacking own-paper eval on target benchmarks).

Boundary rulings already made at intake: ATM (2401.00025) EXCLUDED,
v1 2023-12-28 outside window despite the 2401 id. Two distinct papers
named UniVLA (2505.06111, 2506.19850): both stay candidates.

The auditor walks each stratum newest-first from harvest_kept.json,
applying the frozen inclusion criteria; the first 17/17/16 included
papers form the sample. Extraction record schema (per comparison):
paper id | benchmark | suite(s) | rate X | rate Y | n per side +
unit tag {per-task, per-suite, per-benchmark, AMBIGUOUS, NOT-REPORTED} |
n-source rung (1-5) | paired? | seeds stated? | claim quote location.
Extraction results land in docs/audit/extraction.jsonl.
