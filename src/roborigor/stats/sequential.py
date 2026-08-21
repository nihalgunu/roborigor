"""Anytime-valid sequential comparison of two policies on paired episodes.

Machinery: a mixture e-process (Robbins-style) on the discordant-pair
stream. Under H0 (no difference) each discordant pair is Bernoulli(1/2);
the e-value after b pairs won by A and c by B against a Beta(a0, b0)
mixture over the alternative is

    E = B(a0 + b, b0 + c) / (B(a0, b0) * 0.5**(b + c))

and by Ville's inequality rejecting when E >= 1/alpha controls the type-I
error at alpha under ANY data-dependent stopping rule. This is the same
family of anytime-valid guarantees as STEP (Snyder et al., arXiv
2503.10966) and its follow-up (arXiv 2603.13616), specialized to the
paired-by-init design; those works are the citation anchors.

Used only for the perturbed and RoboCasa grids; headline clean-grid
numbers stay fixed-n by pre-registration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class SequentialPairedTest:
    """Accumulates discordant pairs; query e_value / decision at any time."""

    alpha: float = 0.05
    prior_a: float = 1.0  # Beta mixture over the alternative; (1,1) = uniform
    prior_b: float = 1.0
    a_wins: int = 0
    b_wins: int = 0
    _log_e_history: list = field(default_factory=list)

    def update(self, a_wins: int = 0, b_wins: int = 0) -> None:
        """Feed newly observed discordant pairs (concordant pairs carry no signal)."""
        if a_wins < 0 or b_wins < 0:
            raise ValueError("counts must be non-negative")
        self.a_wins += a_wins
        self.b_wins += b_wins
        self._log_e_history.append(self.log_e_value)

    @property
    def log_e_value(self) -> float:
        b, c = self.a_wins, self.b_wins
        return (
            _betaln(self.prior_a + b, self.prior_b + c)
            - _betaln(self.prior_a, self.prior_b)
            + (b + c) * math.log(2.0)
        )

    @property
    def e_value(self) -> float:
        return math.exp(self.log_e_value)

    @property
    def p_value(self) -> float:
        """Anytime-valid p-value: inverse of the running-max e-value."""
        peak = max(self._log_e_history, default=self.log_e_value)
        peak = max(peak, self.log_e_value)
        return min(1.0, math.exp(-peak))

    @property
    def decision(self) -> str:
        """'reject_null' once E >= 1/alpha, else 'continue'. Rejection is sticky."""
        threshold = math.log(1.0 / self.alpha)
        if any(le >= threshold for le in self._log_e_history) or (
            self.log_e_value >= threshold
        ):
            return "reject_null"
        return "continue"


def _betaln(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
