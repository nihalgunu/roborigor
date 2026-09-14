#!/usr/bin/env bash
# Source A (Amendment 1) of docs/efficiency-audit-protocol.md: one fixed
# Semantic Scholar bulk query. Output: docs/efficiency_audit/s2_raw.json.
set -euo pipefail
OUT="$(dirname "$0")/../docs/efficiency_audit/s2_raw.json"
Q='("vision-language-action" | VLA) + (efficient | efficiency | acceleration | accelerating | latency | cache | caching | pruning | quantization | distillation | "early exit" | speculative | speedup | "one-step" | "denoising steps") + LIBERO'
URL="https://api.semanticscholar.org/graph/v1/paper/search/bulk"
for attempt in 1 2 3 4 5 6; do
  curl -sG "$URL" --data-urlencode "query=$Q" \
    --data-urlencode "fields=title,externalIds,publicationDate,abstract" \
    --data-urlencode "publicationDateOrYear=2024-01-01:2026-09-12" -o "$OUT"
  if python3 -c "import json,sys; d=json.load(open('$OUT')); sys.exit(0 if 'data' in d else 1)" 2>/dev/null; then
    python3 -c "import json; d=json.load(open('$OUT')); print('saved', len(d['data']), 'of total', d.get('total'), 'token', d.get('token'))"
    exit 0
  fi
  echo "attempt $attempt: $(head -c 80 "$OUT")"; sleep $((attempt * 20))
done
exit 1
