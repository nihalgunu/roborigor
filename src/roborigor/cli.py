"""roborigor command line.

Core commands (validate-config, plan, summarize, integrity) run anywhere,
including the py3.8 client venvs. Stats commands (power) import scipy
lazily and need the [stats] extra on 3.11+.

Python 3.8 compatible at import time.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EPISODES_PER_MINUTE = 20.0  # measured: 2,000 eps / 100 min, 6 workers, one A100
DOLLARS_PER_HOUR = 1.99  # Lambda gpu_1x_a100_sxm4


def _cmd_validate(args) -> int:
    from roborigor.core.config import load_campaign

    load_campaign(args.config)
    print(f"{args.config}: valid")
    return 0


def _cmd_plan(args) -> int:
    from roborigor.campaign.manifest import build_manifest, save_manifest
    from roborigor.core.config import load_campaign, to_dict
    from roborigor.rollout.worklist import expand_campaign

    cfg = load_campaign(args.config)
    items = expand_campaign(cfg, all_task_ids=list(range(args.n_tasks)))
    minutes = len(items) / EPISODES_PER_MINUTE
    print(f"campaign {cfg.campaign}: {len(items)} episodes across {len(cfg.arms)} arms")
    print(
        f"single-box estimate: {minutes:.0f} min, "
        f"${minutes / 60 * DOLLARS_PER_HOUR:.2f} at {EPISODES_PER_MINUTE:.0f} eps/min"
    )
    per_arm = {}
    for i in items:
        per_arm[i.arm] = per_arm.get(i.arm, 0) + 1
    for arm, n in sorted(per_arm.items()):
        print(f"  arm {arm}: {n}")
    if args.out:
        manifest = build_manifest(cfg.campaign, to_dict(cfg), items, n_boxes=args.boxes)
        save_manifest(manifest, args.out)
        print(f"manifest ({args.boxes} boxes) -> {args.out}")
    return 0


def _records(paths):
    from roborigor.core.schema import read_records

    files = []
    for p in paths:
        path = Path(p)
        files.extend(sorted(path.glob("records_*.jsonl")) if path.is_dir() else [path])
    return [r for f in files for r in read_records(str(f))]


def _cmd_summarize(args) -> int:
    from roborigor.core.schema import summarize

    print(json.dumps(summarize(_records(args.records)), indent=1))
    return 0


def _cmd_integrity(args) -> int:
    from roborigor.campaign.integrity import box_outliers, check
    from roborigor.campaign.manifest import load_manifest

    records = _records(args.records)
    items = load_manifest(args.manifest).items if args.manifest else None
    report = check(records, items)
    report.pop("_resolved")
    report["box_outliers"] = box_outliers(records)
    print(json.dumps(report, indent=1, default=str))
    return 0 if report["ok"] else 1


def _cmd_run_shard(args) -> int:
    from roborigor.campaign.manifest import load_manifest
    from roborigor.campaign.resume import completed_keys, remaining
    from roborigor.rollout.runner import run_work_items

    manifest = load_manifest(args.manifest)
    items = manifest.items_for_box(args.box_id)
    if args.arm:
        items = [i for i in items if i.arm in set(args.arm)]
    items = [i for n, i in enumerate(items) if n % args.n_workers == args.worker_index]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(out_dir.glob("records_*.jsonl"))
    if existing:
        items = remaining(items, completed_keys(map(str, existing)))
    out_path = out_dir / f"records_{args.box_id}_w{args.worker_index}.jsonl"

    if args.env == "mock":
        from roborigor.testing import MockEnv, MockPolicy

        env, policy = MockEnv(), MockPolicy()
    else:
        from roborigor.policies.ws_client import WsPolicyClient

        resize = None if args.obs_resize == 0 else args.obs_resize
        if args.env == "libero":
            from roborigor.envs.libero import LiberoAdapter

            env = LiberoAdapter(resize_size=resize)
        elif args.env == "libero_plus":
            from roborigor.envs.libero_plus import LiberoPlusAdapter

            env = LiberoPlusAdapter(args.classification, resize_size=resize)
            env.verify_fork()
        else:
            raise SystemExit(f"unknown env {args.env!r}")
        policy = WsPolicyClient(
            policy_id=manifest.config.get("policy", {}).get("policy_id", ""),
            host=args.host,
            port=args.port,
        )

    import datetime

    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    n = run_work_items(
        items, env, policy, str(out_path),
        worker_id=f"w{args.worker_index}", box_id=args.box_id, started_at=started,
    )
    print(f"{args.box_id}/w{args.worker_index}: {n} episodes -> {out_path}")
    return 0


def _cmd_verify_seeding(args) -> int:
    """Same obs + same seed twice must give identical actions; different
    seeds must differ. Run against a live seeded server before any
    reported episode. Pilot 2b's gate."""
    import numpy as np

    from roborigor.policies.base import PredictRequest
    from roborigor.policies.ws_client import WsPolicyClient

    client = WsPolicyClient(policy_id="verify", host=args.host, port=args.port)
    req = PredictRequest(
        images={
            "agentview": np.zeros((224, 224, 3), dtype=np.uint8),
            "wrist": np.zeros((224, 224, 3), dtype=np.uint8),
        },
        state=np.zeros(8, dtype=np.float32),
        prompt="verify seeding",
        sampling_seed=args.seed,
    )
    a1 = np.asarray(client.predict(req).actions)
    a2 = np.asarray(client.predict(req).actions)
    req_other = PredictRequest(
        images=req.images, state=req.state, prompt=req.prompt,
        sampling_seed=args.seed + 1,
    )
    b = np.asarray(client.predict(req_other).actions)
    same = np.array_equal(a1, a2)
    close = np.allclose(a1, a2, atol=1e-5)
    differs = not np.allclose(a1, b, atol=1e-5)
    print(f"fixed seed bitwise identical: {same}")
    print(f"fixed seed allclose(1e-5):    {close}")
    print(f"different seed differs:       {differs}")
    if close and differs:
        print("PASS" + ("" if same else " (allclose only; note XLA determinism flag)"))
        return 0
    print("FAIL: seed control is not working; use one-server-per-seed fallback")
    return 1


def _cmd_varcomp(args) -> int:
    from roborigor.analysis.varcomp import varcomp_report

    print(json.dumps(varcomp_report(_records(args.records)), indent=1))
    return 0


def _cmd_audit(args) -> int:
    from roborigor.analysis.audit import load_extractions, recompute

    report = recompute(load_extractions(args.extraction))
    if not args.full:
        report.pop("comparisons")
    print(json.dumps(report, indent=1))
    return 0


def _cmd_knobs(args) -> int:
    from roborigor.analysis.knobs import knob_table, pareto_frontier

    t = knob_table(_records(args.records))
    t["pareto_frontier"] = pareto_frontier(t["cells"])
    print(json.dumps(t, indent=1))
    return 0


def _cmd_power(args) -> int:
    from roborigor.stats.power import mde_unpaired, required_n_unpaired

    if args.mde_at:
        d = mde_unpaired(args.mde_at, args.base)
        print(f"MDE at n={args.mde_at}, base {args.base}: {d * 100:.1f} points")
    if args.gap:
        n = required_n_unpaired(args.base, args.base - args.gap)
        print(f"n per arm for {args.gap * 100:.0f}-point gap at base {args.base}: {n}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="roborigor")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate-config", help="validate a campaign YAML")
    p.add_argument("config")
    p.set_defaults(fn=_cmd_validate)

    p = sub.add_parser("plan", help="expand a campaign; print episode count and cost")
    p.add_argument("config")
    p.add_argument("--n-tasks", type=int, default=10, help="tasks in the suite")
    p.add_argument("--boxes", type=int, default=1)
    p.add_argument("--out", help="write a manifest JSON here")
    p.set_defaults(fn=_cmd_plan)

    p = sub.add_parser("summarize", help="aggregate records to summary JSON")
    p.add_argument("records", nargs="+", help="record files or directories")
    p.set_defaults(fn=_cmd_summarize)

    p = sub.add_parser("integrity", help="duplicate/missing/outlier checks")
    p.add_argument("records", nargs="+")
    p.add_argument("--manifest")
    p.set_defaults(fn=_cmd_integrity)

    p = sub.add_parser("run-shard", help="run this box's share of a manifest")
    p.add_argument("--manifest", required=True)
    p.add_argument("--box-id", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--env", default="libero", choices=["libero", "libero_plus", "mock"])
    p.add_argument("--classification", help="task_classification.json (libero_plus)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--n-workers", type=int, default=1)
    p.add_argument("--worker-index", type=int, default=0)
    p.add_argument("--arm", action="append", default=None,
                   help="restrict to these arm names (repeatable); e.g. per-num_steps groups")
    p.add_argument("--obs-resize", type=int, default=224,
                   help="client-side resize-with-pad (openpi protocol); 0 = native frames")
    p.set_defaults(fn=_cmd_run_shard)

    p = sub.add_parser("verify-seeding", help="gate: per-request seed control works")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=_cmd_verify_seeding)

    p = sub.add_parser("varcomp", help="V1 variance-component report from records")
    p.add_argument("records", nargs="+")
    p.set_defaults(fn=_cmd_varcomp)

    p = sub.add_parser("audit", help="recompute significance of extracted literature comparisons")
    p.add_argument("extraction", help="extraction.jsonl path")
    p.add_argument("--full", action="store_true", help="include per-comparison rows")
    p.set_defaults(fn=_cmd_audit)

    p = sub.add_parser("knobs", help="V2 knob table and Pareto frontier from records")
    p.add_argument("records", nargs="+")
    p.set_defaults(fn=_cmd_knobs)

    p = sub.add_parser("power", help="rollout-budget calculator")
    p.add_argument("--base", type=float, default=0.95)
    p.add_argument("--mde-at", type=int, help="report MDE at this n")
    p.add_argument("--gap", type=float, help="report required n for this gap")
    p.set_defaults(fn=_cmd_power)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
