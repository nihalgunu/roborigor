"""Three-part report for a no-loss (equivalence) claim between two settings.

A no-loss verdict on a saturated benchmark is supplied largely by episodes
both settings solve, which tighten an absolute-difference interval without
saying anything about episodes where either can fail. The report therefore
gives, for paired records of settings A and B:

  (i)   discordant pairs and the exact conditional odds-ratio interval, which
        pairs both settings solve cannot move;
  (ii)  the paired Newcombe interval for the difference, on all tasks and on a
        declared subset of informative tasks;
  (iii) the failure-rate ratio (A failures / B failures) with an
        initial-state cluster bootstrap interval, against a declared bound.

Records are paired on their cell key with the dial fields removed, so the
two record sets must differ only in the settings being compared.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from roborigor.core.schema import EpisodeRecord
from roborigor.stats.compare import PairedCounts, mcnemar_exact
from roborigor.stats.intervals import clopper_pearson, newcombe_paired_diff


def pair_key(rec: EpisodeRecord) -> tuple:
    """Episode identity apart from policy and inference dials."""
    return (rec.benchmark, rec.suite, rec.task_id, rec.init_id, rec.seed, rec.sampling_seed,
            rec.perturbation_axis, rec.perturbation_level, rec.replicate)


@dataclass
class Contrast:
    n_pairs: int
    rate_a: float
    rate_b: float
    diff_pts: float
    a_only: int
    b_only: int
    mcnemar_p: float
    ci_pts: tuple
    odds_ratio_ci: tuple
    verdict: str


@dataclass
class NoLossReport:
    margin_pts: float
    ratio_bound: float
    all_tasks: Contrast
    informative: Optional[Contrast]
    failure_ratio: float
    failure_ratio_ci: tuple
    failure_ratio_within_bound: bool
    informative_tasks: list = field(default_factory=list)

    def lines(self) -> list:
        def row(name, c):
            return (f"{name:<18} n={c.n_pairs:<5} {100 * c.rate_a:5.1f}% vs {100 * c.rate_b:5.1f}%  "
                    f"diff {c.diff_pts:+5.1f} [{c.ci_pts[0]:+.1f}, {c.ci_pts[1]:+.1f}]  "
                    f"b-c {c.a_only}-{c.b_only}  p={c.mcnemar_p:.3g}  "
                    f"OR [{c.odds_ratio_ci[0]:.2f}, {c.odds_ratio_ci[1]:.2f}]  -> {c.verdict}")
        out = [f"no-loss report (margin +/-{self.margin_pts:g} pts, failure-ratio bound {self.ratio_bound:g})",
               row("all tasks", self.all_tasks)]
        if self.informative is not None:
            out.append(row(f"informative {self.informative_tasks}", self.informative))
        lo, hi = self.failure_ratio_ci
        out.append(f"failure ratio A/B {self.failure_ratio:.2f} [{lo:.2f}, {hi:.2f}]  "
                   f"-> {'within' if self.failure_ratio_within_bound else 'not within'} bound")
        if self.informative is not None and self.all_tasks.verdict == "EQUIVALENT" \
                and self.informative.verdict != "EQUIVALENT":
            out.append("warning: equivalence on all tasks does not hold on the informative tasks; "
                       "the certificate is supplied by tasks both settings solve")
        return out


def _index(records: Iterable[EpisodeRecord]) -> dict:
    out = {}
    for r in records:
        k = pair_key(r)
        if k in out:
            raise ValueError(f"duplicate episode in one record set: {k}")
        out[k] = r
    return out


def _contrast(a: dict, b: dict, units: Sequence, margin_pts: float) -> Contrast:
    n = len(units)
    if n == 0:
        raise ValueError("no matched pairs")
    both = sum(1 for u in units if a[u].success and b[u].success)
    a_only = sum(1 for u in units if a[u].success and not b[u].success)
    b_only = sum(1 for u in units if b[u].success and not a[u].success)
    neither = n - both - a_only - b_only
    p = mcnemar_exact(PairedCounts(both, a_only, b_only, neither))
    lo, hi = newcombe_paired_diff(both, a_only, b_only, neither)
    if a_only + b_only:
        qlo, qhi = clopper_pearson(a_only, a_only + b_only)
        odds = (qlo / (1 - qlo) if qlo < 1 else float("inf"),
                qhi / (1 - qhi) if qhi < 1 else float("inf"))
    else:
        odds = (0.0, float("inf"))
    if p < 0.05:
        verdict = "DIFFERENT"
    elif 100 * lo > -margin_pts and 100 * hi < margin_pts:
        verdict = "EQUIVALENT"
    else:
        verdict = "INCONCLUSIVE"
    return Contrast(n, (both + a_only) / n, (both + b_only) / n, 100 * (a_only - b_only) / n,
                    a_only, b_only, p, (100 * lo, 100 * hi), odds, verdict)


def noloss_report(records_a: Iterable[EpisodeRecord], records_b: Iterable[EpisodeRecord],
                  informative_tasks: Optional[Sequence[int]] = None, margin_pts: float = 5.0,
                  ratio_bound: float = 1.5, n_boot: int = 4000, seed: int = 0) -> NoLossReport:
    a, b = _index(records_a), _index(records_b)
    units = sorted(set(a) & set(b), key=str)
    all_c = _contrast(a, b, units, margin_pts)
    inf_c = None
    if informative_tasks:
        keep = set(informative_tasks)
        inf_c = _contrast(a, b, [u for u in units if u[2] in keep], margin_pts)

    fa = sum(1 for u in units if not a[u].success)
    fb = sum(1 for u in units if not b[u].success)
    clusters = defaultdict(list)
    for u in units:
        clusters[(u[1], u[2], u[3], u[6], u[7])].append((not a[u].success, not b[u].success))
    keys = list(clusters)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        xa = xb = 0
        for k in (rng.choice(keys) for _ in keys):
            for pa, pb in clusters[k]:
                xa += pa
                xb += pb
        boots.append((xa + 0.5) / (xb + 0.5))
    boots.sort()
    ci = (boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1])
    ratio = fa / fb if fb else float("inf")
    return NoLossReport(margin_pts, ratio_bound, all_c, inf_c, ratio, ci, ci[1] < ratio_bound,
                        list(informative_tasks or []))
