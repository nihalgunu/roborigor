"""Websocket policy client speaking the openpi-client wire protocol.

Sends the CANONICAL observation (images/state/prompt) plus the controlled
factors under reserved "roborigor/" keys; every serve script maps canonical
keys to its policy's expected format server-side. The client is therefore
policy-agnostic, and lives happily in the py3.8 LIBERO venv.

openpi_client is imported lazily: present in client venvs on the box,
absent on the dev machine.

Python 3.8 compatible.
"""

from __future__ import annotations

import time

from roborigor.policies.base import PolicyClient, PredictRequest, PredictResult


class WsPolicyClient(PolicyClient):
    def __init__(
        self,
        policy_id: str,
        host: str = "127.0.0.1",
        port: int = 8000,
        chunk_len: int = 10,
        action_dim: int = 7,
        real_action_dims: int = 7,
    ):
        from openpi_client import websocket_client_policy

        self.policy_id = policy_id
        self.chunk_len = chunk_len
        self.action_dim = action_dim
        self.real_action_dims = real_action_dims
        self._client = websocket_client_policy.WebsocketClientPolicy(host, port)

    def predict(self, req: PredictRequest) -> PredictResult:
        element = {
            "roborigor/images": req.images,
            "roborigor/state": req.state,
            "roborigor/prompt": req.prompt,
        }
        if req.sampling_seed is not None:
            element["roborigor/sampling_seed"] = req.sampling_seed
        if req.num_steps is not None:
            element["roborigor/num_steps"] = req.num_steps
        t0 = time.monotonic()
        result = self._client.infer(element)
        client_s = time.monotonic() - t0
        if "error" in result:
            raise RuntimeError(
                f"policy server error for {self.policy_id}: {str(result['error'])[:3000]}"
            )
        server_ms = result.get("server_timing", {}).get("infer_ms", float("nan"))
        return PredictResult(
            actions=result["actions"],
            server_infer_s=server_ms / 1000.0,
            client_infer_s=client_s,
        )
