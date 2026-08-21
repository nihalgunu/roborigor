#!/usr/bin/env python3
"""Build the release artifact/ directory from the repo's real state.

Layout produced (default: <repo>/artifact):

    artifact/
      <campaign>/records_*.jsonl   one dir per results/ campaign, subdirs kept
      paper-data/*.json            copies of docs/paper-data/*.json
      audit/                       extraction.jsonl, intake_*.log, RESULTS.md,
                                   recompute_final_50papers.json
      README.md                    schema description (field list from
                                   roborigor.core.schema.EpisodeRecord)
      MANIFEST.txt                 per-file sha256 and line counts

Usage:
    python scripts/package_artifact.py [--out DIR]
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

AUDIT_FILES = ["extraction.jsonl", "RESULTS.md", "recompute_final_50papers.json"]
AUDIT_GLOBS = ["intake_*.log"]


def sha256_and_lines(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    lines = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            lines += chunk.count(b"\n")
    return h.hexdigest(), lines


def copy_records(out: Path) -> list[Path]:
    copied = []
    results = REPO / "results"
    for src in sorted(results.rglob("records_*.jsonl")):
        rel = src.relative_to(results)  # <campaign>/[subdir/]records_*.jsonl
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def copy_paper_data(out: Path) -> list[Path]:
    copied = []
    dst_dir = out / "paper-data"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted((REPO / "docs" / "paper-data").glob("*.json")):
        dst = dst_dir / src.name
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def copy_audit(out: Path) -> list[Path]:
    copied = []
    src_dir = REPO / "docs" / "audit"
    dst_dir = out / "audit"
    dst_dir.mkdir(parents=True, exist_ok=True)
    sources = [src_dir / name for name in AUDIT_FILES]
    for pattern in AUDIT_GLOBS:
        sources.extend(sorted(src_dir.glob(pattern)))
    for src in sources:
        if not src.exists():
            raise FileNotFoundError(f"expected audit file missing: {src}")
        dst = dst_dir / src.name
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def episode_record_fields():
    """Import the schema straight from the repo so the README never drifts."""
    sys.path.insert(0, str(REPO / "src"))
    from roborigor.core.schema import SCHEMA_VERSION, EpisodeRecord  # noqa: E402

    return SCHEMA_VERSION, dataclasses.fields(EpisodeRecord)


def write_readme(out: Path) -> Path:
    version, fields = episode_record_fields()
    lines = [
        "# RoboRigor release artifact",
        "",
        "Per-episode evaluation records and derived reports for the RoboRigor",
        "paper. Records are the source of truth; every aggregate is recomputed",
        "from them, never carried separately.",
        "",
        "## Layout",
        "",
        "- `<campaign>/records_*.jsonl`: one JSON object per line, one line per",
        "  evaluation episode, append-only, grouped by campaign as run.",
        "- `paper-data/*.json`: derived reports (variance decomposition, knob",
        "  table, rank analysis) recomputable from the records.",
        "- `audit/`: the 50-paper literature audit: extraction rows, intake",
        "  logs, recomputed significance, and RESULTS.md.",
        "- `MANIFEST.txt`: sha256 and line count for every file above.",
        "",
        f"## Episode record schema (version {version})",
        "",
        "The first thirteen fields are name-compatible with the flowhelm-lab",
        "baseline records (baseline-2026-08-15). All v2 fields default, so v1",
        "records promote silently on read. Every latency number is tagged with",
        "the machine it was measured on via the run's metadata.",
        "",
        "| Field | Type |",
        "|---|---|",
    ]
    for f in fields:
        t = f.type if isinstance(f.type, str) else getattr(f.type, "__name__", str(f.type))
        t = t.replace(" | ", " or ")  # keep the markdown table intact
        lines.append(f"| `{f.name}` | `{t}` |")
    lines += [
        "",
        "Two records are the same planned episode exactly when they agree on",
        "(policy_id, benchmark, suite, task_id, init_id, seed, sampling_seed,",
        "num_steps, exec_horizon, perturbation_axis, perturbation_level,",
        "replicate). This cell key drives resume, duplicate detection, and",
        "pairing. Read the files with `roborigor.core.schema.read_records`,",
        "which tolerates newer writers' extra fields and a torn final line",
        "from an interrupted worker.",
        "",
    ]
    dst = out / "README.md"
    dst.write_text("\n".join(lines))
    return dst


def write_manifest(out: Path, files: list[Path]) -> Path:
    rows = []
    for path in sorted(files, key=lambda p: str(p.relative_to(out))):
        digest, n_lines = sha256_and_lines(path)
        rows.append(f"{digest}  {n_lines:>8}  {path.relative_to(out)}")
    dst = out / "MANIFEST.txt"
    dst.write_text("sha256  lines  path\n" + "\n".join(rows) + "\n")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(REPO / "artifact"), help="output directory")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    files = []
    files += copy_records(out)
    files += copy_paper_data(out)
    files += copy_audit(out)
    files.append(write_readme(out))
    manifest = write_manifest(out, files)

    total = sum(p.stat().st_size for p in files) + manifest.stat().st_size
    print(f"artifact: {out}")
    print(f"files:    {len(files) + 1} (incl. MANIFEST.txt)")
    print(f"size:     {total / 1e6:.1f} MB ({total} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
