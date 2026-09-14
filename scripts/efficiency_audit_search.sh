#!/usr/bin/env bash
# Source A of docs/efficiency-audit-protocol.md: one fixed arXiv API query.
# Output: docs/efficiency_audit/arxiv_raw.xml (saved once, not re-run).
set -euo pipefail
OUT="$(dirname "$0")/../docs/efficiency_audit/arxiv_raw.xml"
VLA='(abs:%22vision-language-action%22+OR+abs:%22vision+language+action%22+OR+abs:VLA)'
EFF='(abs:efficient+OR+abs:efficiency+OR+abs:accelerat*+OR+abs:acceleration+OR+abs:latency+OR+abs:cache+OR+abs:caching+OR+abs:pruning+OR+abs:quantization+OR+abs:quantized+OR+abs:distillation+OR+abs:%22early+exit%22+OR+abs:speculative+OR+abs:%22inference+speed%22+OR+abs:%22denoising+steps%22+OR+abs:%22one-step%22+OR+abs:speedup)'
BENCH='abs:LIBERO'
DATE='submittedDate:%5B202401010000+TO+202609122359%5D'
URL="https://export.arxiv.org/api/query?search_query=${VLA}+AND+${EFF}+AND+${BENCH}+AND+${DATE}&start=0&max_results=500&sortBy=submittedDate&sortOrder=descending"
for attempt in 1 2 3 4 5 6 7 8; do
  curl -sL -A "roborigor-audit/1.0" "$URL" -o "$OUT"
  if head -c 5 "$OUT" | grep -q "<?xml"; then echo "saved $OUT (attempt $attempt)"; exit 0; fi
  echo "attempt $attempt: $(head -c 60 "$OUT")"; sleep $((attempt * 30))
done
echo "arXiv API unavailable" >&2; exit 1
