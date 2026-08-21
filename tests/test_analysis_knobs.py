import pytest

pytest.importorskip("scipy")

from helpers import make_record as rec

from roborigor.analysis.knobs import control_latency_ms, knob_table, pareto_frontier


def test_latency_model():
    assert control_latency_ms(10, 5) == pytest.approx((53.2 + 27.9) / 5)
    assert control_latency_ms(1, 1) > control_latency_ms(1, 10)


def test_knob_table_and_frontier():
    records = []
    for ns, eh, p in [(1, 5, 0.6), (10, 5, 0.9), (10, 1, 0.92), (2, 10, 0.7)]:
        for i in range(50):
            records.append(rec(init_id=i, num_steps=ns, exec_horizon=eh,
                               success=(i < p * 50)))
    t = knob_table(records)
    assert len(t["cells"]) == 4
    cell = next(c for c in t["cells"] if c["num_steps"] == 10 and c["exec_horizon"] == 5)
    assert cell["success_rate"] == 0.9 and cell["ci95"][0] < 0.9 < cell["ci95"][1]
    fr = pareto_frontier(t["cells"])
    # (10,1) has highest success but highest latency; (2,10) cheapest
    assert fr[0]["num_steps"] == 2 and fr[-1]["exec_horizon"] == 1
    lats = [c["control_latency_ms_per_step"] for c in fr]
    srs = [c["success_rate"] for c in fr]
    assert lats == sorted(lats) and srs == sorted(srs)
