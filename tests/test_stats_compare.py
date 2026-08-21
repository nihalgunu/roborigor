import pytest

pytest.importorskip("scipy")

from helpers import make_record as rec

from roborigor.stats.compare import (
    PairedCounts,
    benjamini_hochberg,
    boschloo,
    fisher,
    holm,
    mcnemar_exact,
    pair_records,
)


def test_pairing_and_counts():
    a = [rec(init_id=i, success=i < 3) for i in range(5)]
    b = [rec(init_id=i, success=i < 2, policy_id="other") for i in range(5)]
    b.append(rec(init_id=99, policy_id="other"))  # unmatched in b
    pc = pair_records(a, b)
    assert pc.n_pairs == 5
    assert pc.both_succeed == 2 and pc.a_only == 1 and pc.both_fail == 2
    assert pc.n_unmatched_b == 1 and pc.n_unmatched_a == 0


def test_pairing_duplicate_raises():
    a = [rec(init_id=0), rec(init_id=0)]
    with pytest.raises(ValueError, match="duplicate"):
        pair_records(a, [rec(init_id=0)])


def test_mcnemar_reference():
    # 15 vs 5 discordant: binom.test(15, 20, 0.5) two-sided p = 0.04139
    p = mcnemar_exact(PairedCounts(both_succeed=50, a_only=15, b_only=5, both_fail=30))
    assert abs(p - 0.041389) < 1e-4
    # no discordance: p = 1
    assert mcnemar_exact(PairedCounts(10, 0, 0, 10)) == 1.0


def test_unpaired_exact_tests():
    # a clear gap
    pb = boschloo(95, 100, 75, 100)
    pf = fisher(95, 100, 75, 100)
    assert pb < 0.01 and pf < 0.01
    assert pb <= pf + 1e-9  # Boschloo at least as powerful
    # 3-pt gap at n=500 and ~95%: the literature's typical undetectable claim
    assert fisher(475, 500, 460, 500) > 0.05


def test_holm_reference():
    # classic example
    ps = [0.01, 0.04, 0.03, 0.005]
    adj = holm(ps)
    assert adj == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_bh_monotone_and_bounded():
    ps = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205]
    adj = benjamini_hochberg(ps)
    assert all(0 <= a <= 1 for a in adj)
    assert all(a >= p for a, p in zip(adj, ps))
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    assert all(adj[order[i]] <= adj[order[i + 1]] + 1e-12 for i in range(len(ps) - 1))
