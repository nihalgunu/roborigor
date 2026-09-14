"""The predict-action interface every policy client implements.

Every policy runs as a serve script in its own venv speaking the websocket
wire protocol; the client side is deliberately tiny so it can live inside
whatever Python the benchmark pins (LIBERO: 3.8). Controlled factors ride
the request; the server wrapper pops them before delegating to the policy.

Python 3.8 compatible: imported in benchmark client processes.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any


@dataclasses.dataclass
class PredictRequest:
    """Canonical observation plus the controlled factors for one chunk."""

    images: dict[str, Any]  # canonical keys: "agentview", "wrist"; uint8 HWC arrays
    state: Any  # proprioceptive vector (np.ndarray; Any keeps core numpy-free)
    prompt: str
    sampling_seed: int | None = None  # flow noise seed; None = server default
    num_steps: int | None = None  # denoising steps; None = policy default


@dataclasses.dataclass
class PredictResult:
    actions: Any  # (chunk_len, action_dim) array; runner slices to exec horizon
    server_infer_s: float
    client_infer_s: float


class PolicyClient(abc.ABC):
    """One policy behind the wire. Implementations: ws_client, test mocks."""

    policy_id: str = ""
    chunk_len: int = 0
    action_dim: int = 0
    real_action_dims: int = 0  # pi0.5 LIBERO: actions are (10, 32), first 7 real

    @abc.abstractmethod
    def predict(self, req: PredictRequest) -> PredictResult:
        ...

    def reset(self) -> None:  # noqa: B027 (optional hook)
        """Per-episode hook; no-op for stateless servers."""
