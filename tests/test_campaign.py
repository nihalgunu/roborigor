from helpers import MockEnv, MockPolicy

from roborigor.campaign.integrity import box_outliers, check
from roborigor.campaign.manifest import build_manifest, load_manifest, save_manifest
from roborigor.campaign.resume import completed_keys, remaining
from roborigor.core.config import load_campaign
from roborigor.core.schema import read_records
from roborigor.rollout.runner import run_work_items
from roborigor.rollout.worklist import expand_campaign

CONFIG = """
campaign: mockcamp
benchmark: libero
policy:
  policy_id: mock
  checkpoint: none
suite: libero_10
output_dir: results/mock
base:
  seeds: [7]
  sampling_seeds: [0, 1]
  n_trials_per_task: 5
arms:
  - name: control
  - name: ns2
    num_steps: 2
"""


def load(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(CONFIG)
    return load_campaign(str(p))


def test_expansion_count_and_determinism(tmp_path):
    cfg = load(tmp_path)
    items = expand_campaign(cfg, all_task_ids=list(range(10)))
    # 2 arms x 10 tasks x 5 inits x 1 seed x 2 sampling seeds
    assert len(items) == 200
    assert items == expand_campaign(cfg, all_task_ids=list(range(10)))
    assert len({i.key() for i in items}) == 200


def test_manifest_roundtrip_and_partition(tmp_path):
    cfg = load(tmp_path)
    items = expand_campaign(cfg, all_task_ids=list(range(10)))
    m = build_manifest("mockcamp", {}, items, n_boxes=4)
    idx = sorted(i for v in m.assignments.values() for i in v)
    assert idx == list(range(200))  # exact partition
    # one task's episodes never split across boxes
    task_to_box = {}
    for box, ids in m.assignments.items():
        for i in ids:
            t = m.items[i].task_id
            assert task_to_box.setdefault(t, box) == box
    path = tmp_path / "manifest.json"
    save_manifest(m, str(path))
    m2 = load_manifest(str(path))
    assert m2.items == m.items and m2.assignments == m.assignments


def test_mock_campaign_kill_and_resume(tmp_path):
    """The Stage-1 gate scenario: 4 boxes, one dies mid-episode, resume to
    exactly-once coverage with integrity green."""
    cfg = load(tmp_path)
    items = expand_campaign(cfg, all_task_ids=list(range(10)))
    manifest = build_manifest("mockcamp", {}, items, n_boxes=4)
    env, policy = MockEnv(), MockPolicy()

    paths = []
    for box_id, box_items in ((b, manifest.items_for_box(b)) for b in manifest.assignments):
        out = tmp_path / f"records_{box_id}.jsonl"
        paths.append(out)
        if box_id == "box2":
            # box2 dies: only half its work lands, plus a torn final line
            done = box_items[: len(box_items) // 2]
            run_work_items(done, env, policy, str(out), box_id=box_id, worker_id="w0")
            with open(out, "a") as f:
                f.write('{"suite": "libero_10", "task_id"')
        else:
            run_work_items(box_items, env, policy, str(out), box_id=box_id, worker_id="w0")

    done = completed_keys(map(str, paths))
    todo = remaining(items, done)
    assert 0 < len(todo) < len(items)

    # re-provisioned box picks up exactly the residue
    out2 = tmp_path / "records_box2_retry.jsonl"
    run_work_items(todo, env, policy, str(out2), box_id="box2b", worker_id="w0")
    paths.append(out2)

    records = [r for p in paths for r in read_records(str(p))]
    report = check(records, items)
    assert report["ok"], report
    assert report["n_records"] == len(items) == report["n_cells"]

    # outcomes are deterministic in the mock: success pattern matches script
    rate = sum(r.success for r in records) / len(records)
    assert 0.5 < rate < 0.9


def test_integrity_flags_duplicates_and_missing(tmp_path):
    cfg = load(tmp_path)
    items = expand_campaign(cfg, all_task_ids=[0])
    env, policy = MockEnv(n_tasks=1), MockPolicy()
    out = tmp_path / "r.jsonl"
    run_work_items(items, env, policy, str(out))
    run_work_items(items[:3], env, policy, str(out))  # duplicate 3 episodes
    records = read_records(str(out))
    report = check(records, items[:-2])  # also pretend 2 cells were unplanned
    assert not report["ok"]
    assert report["n_duplicate_cells"] == 3
    assert report["n_unplanned"] == 2
    assert len(report["_resolved"]) == report["n_cells"]


def test_box_outlier_detection(tmp_path):
    from helpers import make_record as rec

    good = [rec(init_id=i, box_id="box0", success=(i % 10 != 0)) for i in range(100)]
    bad = [rec(init_id=i, seed=8, box_id="box1", success=(i % 10 == 0)) for i in range(100)]
    out = box_outliers(good + bad)
    assert "box1" in out["flagged_boxes"] or "box0" in out["flagged_boxes"]
    assert box_outliers(good)["flagged_boxes"] == {}


def test_runner_records_are_faithful(tmp_path):
    cfg = load(tmp_path)
    items = expand_campaign(cfg, all_task_ids=[3])[:2]
    env, policy = MockEnv(), MockPolicy()
    out = tmp_path / "r.jsonl"
    n = run_work_items(items, env, policy, str(out), worker_id="w7", box_id="boxX",
                       started_at="2026-08-18T00:00:00Z")
    assert n == 2
    recs = read_records(str(out))
    r = recs[0]
    assert r.policy_id == "mock" and r.worker_id == "w7" and r.box_id == "boxX"
    assert r.task_description == "task 3"
    assert r.n_chunks >= 1 and r.n_env_steps >= 1
    assert r.exec_horizon == 5  # default when cell leaves it None
    assert r.chunk_len == 10
    assert r.client_infer_s_total > r.server_infer_s_total > 0


def test_chunk_seed_schedule_semantics():
    """The gate question: fixed episode seed must NOT mean fixed noise.

    Consecutive chunks in one episode get different derived seeds; the same
    episode seed reproduces the identical schedule; different episode seeds
    give disjoint schedules; None passes through uncontrolled."""
    from roborigor.rollout.runner import chunk_seed

    sched0 = [chunk_seed(0, k) for k in range(60)]
    assert len(set(sched0)) == 60  # every chunk draws fresh noise
    assert sched0 == [chunk_seed(0, k) for k in range(60)]  # replicable
    sched1 = [chunk_seed(1, k) for k in range(60)]
    assert set(sched0).isdisjoint(sched1)  # streams do not collide
    assert all(0 <= s < 2**63 for s in sched0)
    assert chunk_seed(None, 5) is None


def test_runner_sends_scheduled_seeds():
    """The wire actually carries the schedule, not the raw episode seed."""
    from helpers import MockEnv, MockPolicy

    from roborigor.rollout.runner import chunk_seed, run_episode
    from roborigor.rollout.worklist import WorkItem

    class RecordingPolicy(MockPolicy):
        def __init__(self):
            super().__init__()
            self.seen_seeds = []

        def predict(self, req):
            self.seen_seeds.append(req.sampling_seed)
            return super().predict(req)

    item = WorkItem(
        policy_id="mock", checkpoint="none", benchmark="libero",
        suite="libero_10", task_id=1, init_id=0, seed=7, sampling_seed=3,
        num_steps=None, exec_horizon=5, perturbation_axis=None,
        perturbation_level=None, replicate=0, arm="control", run_id="t/control",
    )
    env, policy = MockEnv(fail_every=1000, succeed_at=9), RecordingPolicy()
    run_episode(env, policy, item, max_steps=30, task_description="t")
    assert len(policy.seen_seeds) >= 2
    assert policy.seen_seeds == [chunk_seed(3, k) for k in range(len(policy.seen_seeds))]
    assert len(set(policy.seen_seeds)) == len(policy.seen_seeds)


def test_replicates_expand_distinct_and_group_for_residual():
    from roborigor.core.config import Arm, CampaignConfig, Cell, PolicyConfig
    from roborigor.stats.variance import residual_disagreement

    cfg = CampaignConfig(
        campaign="rep", benchmark="libero",
        policy=PolicyConfig(policy_id="p", checkpoint="c"),
        suite="libero_10", output_dir="x",
        base=Cell(seeds=[7], sampling_seeds=[0], task_ids=[8], init_ids=[0],
                  replicates=4),
        arms=[Arm(name="control")],
    )
    items = expand_campaign(cfg, all_task_ids=[8])
    assert len(items) == 4  # replicates are distinct planned episodes
    assert len({i.key() for i in items}) == 4
    from helpers import make_record as rec
    recs = [rec(task_id=8, sampling_seed=0, replicate=r, success=(r < 3)) for r in range(4)]
    out = residual_disagreement(recs)
    assert out["n_replicated_cells"] == 1 and out["disagreement_rate"] == 1.0
