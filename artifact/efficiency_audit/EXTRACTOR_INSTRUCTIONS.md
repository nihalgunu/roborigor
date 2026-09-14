# Instructions for screening and extraction (efficiency-claim audit)

Read docs/efficiency-audit-protocol.md first; it governs. Do not modify any
file except your own output file.

For EVERY candidate in your batch file (one JSON per line), write exactly one
output line (JSON) to your output file, in the batch's order.

## Stage 1: title/abstract screen
If the abstract is missing, fetch it from https://arxiv.org/abs/<id> (or find
the paper by title if no id). Exclude at stage 1 only when it clearly fails
Section 2 (e.g. not about reducing inference cost of an existing VLA; no
simulation evaluation; survey). When unsure, go to stage 2.

## Stage 2: full text
Download with `curl -sL -o <scratch>/pdf/<id>.pdf https://arxiv.org/pdf/<id>`
then `pdftotext -layout`. Use the scratch dir given in your prompt. Search the
full text including appendices (grep for LIBERO, success, episodes, trials,
rollouts, seeds, "per task", comparable, maintain, negligible, degradation,
drop, loss, speedup, std, ±, confidence).

Apply Section 2 strictly:
- primary contribution reduces inference cost of an existing VLA policy;
- LIBERO success reported for BOTH the method and its own same-backbone base;
- the paper asserts parity or acceptable loss vs the base on LIBERO (quote it).
If the paper only claims strict improvement over its base on LIBERO, set
include=false and strict_improvement_only=true.

## Output schema (one line per candidate)
{
 "cid": <int from batch>, "id": "<arxiv id or null>", "title": "...",
 "version": "v1/v2/...", "screen": {"stage": 1 or 2, "include": true/false,
   "strict_improvement_only": true/false, "reason": "short"},
 "method_family": "steps|distillation|caching|token_pruning|quantization|early_exit|speculative|chunking|compression|other|null",
 "base_policy": "e.g. pi0.5 (openpi), OpenVLA-OFT, ...",
 "claim": null OR {
   "quote": "verbatim parity/acceptable-loss sentence (<= 40 words)",
   "location": "abstract|intro|results|conclusion + section",
   "suites": "e.g. LIBERO avg of Spatial/Object/Goal/Long",
   "rate_base": 0.971, "rate_method": 0.969,          # fractions, the highlighted config and aggregate
   "episodes_per_task": 50 or null, "episodes_per_suite": 500 or null,
   "n_total_base": 2000 or null, "n_total_method": 2000 or null,  # episodes behind the aggregate compared
   "n_source": "explicit|derived|code|NOT-REPORTED", "n_evidence": "verbatim quote",
   "per_task_results": true/false,       # per-task success for this comparison shown anywhere
   "uncertainty_reported": true/false, "uncertainty_kind": "std over seeds|CI|test|null",
   "seeds_stated": true/false, "paired_info": true/false,   # discordant pairs / paired test
   "speedup": "e.g. 2.1x latency"
 },
 "other_benchmarks": [ {"benchmark": "VLABench", "rate_base": 0.388, "rate_method": 0.068,
    "n_total_base": 800 or null, "n_total_method": 800 or null, "evidence": "Table X"} ],
 "notes": "anything ambiguous"
}

Rules for n_total: episodes behind the compared aggregate. LIBERO "average over
4 suites at 500 episodes per suite" -> 2000. "50 trials per task, 10 tasks per
suite, 4 suites" -> 2000 (source "derived"). If only a per-suite count is given
for a 4-suite average, multiply and mark "derived". Never guess; use null and
"NOT-REPORTED" when not stated in paper or linked README.

"other_benchmarks": only benchmarks where THE SAME method configuration and THE
SAME base are both reported (e.g. LIBERO-Plus, SimplerEnv, RoboCasa, VLABench,
CALVIN, real robot success rates). Omit if none.

Be conservative and consistent; put judgement calls in notes. At the end,
reply with: counts of stage-1 excluded, stage-2 excluded, included,
strict_improvement_only, and a list of uncertain calls (cid + one line).
