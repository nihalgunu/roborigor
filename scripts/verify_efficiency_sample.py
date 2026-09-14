"""Re-verify a seeded 20% sample of included efficiency-audit papers against
their PDFs by direct text search (protocol Section 5).

For each sampled paper: the claim quote, the base and method success rates
(as percentages or fractions, common formattings), and the episode-count
evidence quote must each appear in the pdftotext output. Writes
docs/efficiency_audit/verification_sample.json.
"""

from __future__ import annotations

import json
import random
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs/efficiency_audit/extraction.jsonl"
SEED = 20260913
SHARE = 0.20


def norm(s: str) -> str:
    """Lowercase alphanumerics only: robust to line breaks, hyphenation, and spacing."""
    return re.sub(r"[^a-z0-9.%]+", "", s.lower())


def fragments_found(needle: str, hay: str, size: int = 24) -> bool:
    """A quote counts as found when at least two of three fragments (start,
    middle, end) occur, tolerating two-column interleaving within a quote."""
    n = norm(needle)
    if len(n) <= size:
        return n in hay
    mid = len(n) // 2 - size // 2
    parts = [n[:size], n[mid:mid + size], n[-size:]]
    return sum(part in hay for part in parts) >= 2


def pdf_text(arxiv_id: str, cache: Path) -> str:
    txt = cache / f"{arxiv_id}.txt"
    if not txt.exists():
        pdf = cache / f"{arxiv_id}.pdf"
        for attempt in range(4):
            subprocess.run(["curl", "-sL", "-o", str(pdf), f"https://arxiv.org/pdf/{arxiv_id}"], check=False)
            if pdf.exists() and pdf.read_bytes()[:4] == b"%PDF":
                break
            time.sleep(10 * (attempt + 1))
        subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=False)
    return txt.read_text(errors="ignore") if txt.exists() else ""


def rate_forms(rate: float) -> set[str]:
    """Specific renderings of a rate; a bare integer only when the rate is a whole percent."""
    pct = 100 * rate
    forms = {f"{pct:.1f}", f"{pct:.2f}", f"{rate:.3f}"}
    if abs(pct - round(pct)) < 1e-6:
        forms.add(f"{pct:.0f}")
    return forms


def main():
    rows = [json.loads(line) for line in open(SRC) if line.strip()]
    inc = [r for r in rows if r["screen"]["include"]]
    rng = random.Random(SEED)
    k = max(1, round(SHARE * len(inc)))
    sample = rng.sample(inc, k)
    cache = Path(tempfile.gettempdir()) / "roborigor_effaudit_verify"
    cache.mkdir(exist_ok=True)
    results = []
    for r in sample:
        text = pdf_text(r["id"], cache)
        flat = norm(text)
        c = r["claim"]
        quote_ok = fragments_found(c["quote"], flat) if c.get("quote") else False
        rb = any(f in text for f in rate_forms(c["rate_base"])) if c.get("rate_base") is not None else None
        rm = any(f in text for f in rate_forms(c["rate_method"])) if c.get("rate_method") is not None else None
        if c.get("n_evidence") and c.get("n_source") != "NOT-REPORTED":
            n_ok = fragments_found(c["n_evidence"], flat)
        else:
            n_ok = None
        results.append({"id": r["id"], "quote_found": quote_ok, "rate_base_found": rb,
                        "rate_method_found": rm, "n_evidence_found": n_ok, "text_chars": len(text)})
        print(results[-1])
    checks = [v for res in results for key, v in res.items()
              if key.endswith("_found") and v is not None]
    out = {"seed": SEED, "n_included": len(inc), "n_sampled": k,
           "fields_checked": len(checks), "fields_confirmed": sum(checks),
           "agreement": round(sum(checks) / len(checks), 3) if checks else None,
           "papers_fully_confirmed": sum(1 for res in results
                                         if all(v for key, v in res.items() if key.endswith("_found") and v is not None)),
           "results": results}
    dest = ROOT / "docs/efficiency_audit/verification_sample.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print({k_: v for k_, v in out.items() if k_ != "results"})


if __name__ == "__main__":
    main()
