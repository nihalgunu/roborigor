#!/usr/bin/env bash
# Build the named (arXiv / camera-ready) PDF and source tarball.
#
# The tracked paper source carries no author identity: it holds AUTHORNAME,
# AUTHORAFFIL and AUTHOREMAIL placeholders and is built anonymous by default.
# This script injects the real values into a scratch copy only, so the
# repository stays safe to mirror anonymously no matter how the mirror's
# term list is configured.
set -euo pipefail

AUTHOR_NAME="${AUTHOR_NAME:-Nihal Gunukula}"
AUTHOR_AFFIL="${AUTHOR_AFFIL:-Purdue University}"
AUTHOR_EMAIL="${AUTHOR_EMAIL:-ngunukul@purdue.edu}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/build/named}"
rm -rf "$OUT" && mkdir -p "$OUT/figures"

cp "$ROOT"/paper/{main.tex,refs.bib,numbers.tex,table_grid.tex,table_power.tex} "$OUT/"
cp "$ROOT"/paper/figures/*.pdf "$OUT/figures/"

python3 - "$OUT/main.tex" "$AUTHOR_NAME" "$AUTHOR_AFFIL" "$AUTHOR_EMAIL" <<'PY'
import sys
path, name, affil, email = sys.argv[1:5]
s = open(path).read()
before = s
s = s.replace("\\anontrue % set \\anonfalse for arXiv/camera-ready",
              "\\anonfalse % named build")
s = s.replace("AUTHORNAME", name).replace("AUTHORAFFIL", affil).replace("AUTHOREMAIL", email)
assert s != before, "no substitutions made: placeholders missing?"
for token in ("AUTHORNAME", "AUTHORAFFIL", "AUTHOREMAIL"):
    assert token not in s, f"{token} left unsubstituted"
open(path, "w").write(s)
PY

cd "$OUT"
tectonic -X compile --keep-intermediates main.tex >/dev/null 2>&1
rm -f main.aux main.log main.blg main.out
tar czf arxiv_source.tar.gz main.tex main.bbl refs.bib numbers.tex \
    table_grid.tex table_power.tex figures/

# the named build must contain the identity; the tracked source must not
grep -q "$AUTHOR_EMAIL" main.tex || { echo "FAIL: email missing from build"; exit 1; }
grep -q "$AUTHOR_EMAIL" "$ROOT/paper/main.tex" && { echo "FAIL: identity leaked into tracked source"; exit 1; }
echo "named build ready: $OUT/main.pdf and $OUT/arxiv_source.tar.gz"
