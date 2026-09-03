"""Serve an openpi flow policy with per-request sampling-seed control.

The ONE documented touch of openpi internals, isolated here and pinned to
the openpi commit recorded in run metadata. Everything else is public API:
create_trained_policy(sample_kwargs={"num_steps": N}) exactly as the
verified microbenchmark server does.

Factor handling:
- sampling seed: per request. The wrapper reseeds the policy's JAX PRNG
  before delegating. VERIFY-ON-BOX (pilot 2b): the RNG attribute name is
  asserted at startup and the whole mechanism is validated by
  `roborigor verify-seeding` before any reported episode runs.
- num_steps: per server process (--num_steps). It varies only across arms;
  campaign_box.sh restarts the server between arms, which avoids
  per-request JIT recompiles. A request carrying a different
  roborigor/num_steps than the server's is REJECTED so a misconfigured
  campaign fails loudly instead of silently running the wrong cell.

The client sends canonical observations under roborigor/ keys; this
wrapper maps them to openpi's LIBERO element format server-side.

Run inside the openpi py3.11 env:
  uv run scripts/serve_openpi.py --config pi05_libero \
      --checkpoint gs://openpi-assets/checkpoints/pi05_libero --num_steps 10
"""

import argparse
import logging


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="pi05_libero")
    ap.add_argument("--checkpoint", default="gs://openpi-assets/checkpoints/pi05_libero")
    ap.add_argument("--num_steps", type=int, default=10)
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO)

    import jax
    from openpi.policies import policy_config as _policy_config
    from openpi.serving import websocket_policy_server
    from openpi.shared import download
    from openpi.training import config as _config

    config = _config.get_config(args.config)
    checkpoint_dir = download.maybe_download(args.checkpoint)
    policy = _policy_config.create_trained_policy(
        config, checkpoint_dir, sample_kwargs={"num_steps": args.num_steps}
    )

    # VERIFY-ON-BOX: locate the policy's PRNG attribute. Fail at startup,
    # not mid-campaign, if openpi moved it.
    rng_attr = None
    for cand in ("_rng", "rng", "_sample_rng"):
        if hasattr(policy, cand):
            rng_attr = cand
            break
    if rng_attr is None:
        raise RuntimeError(
            f"no PRNG attribute found on {type(policy).__name__}; "
            f"attrs: {list(vars(policy))}; update serve_openpi.py "
            "for this openpi commit or fall back to one server per seed"
        )
    logging.info(f"seed control via policy.{rng_attr}")

    class SeededPolicy:
        """Delegates to the openpi policy; handles roborigor/ request keys."""

        def __init__(self, inner):
            self._inner = inner
            self.metadata = getattr(inner, "metadata", {})

        def infer(self, obs: dict) -> dict:
            obs = dict(obs)
            requested_steps = obs.pop("roborigor/num_steps", None)
            if requested_steps is not None and requested_steps != args.num_steps:
                raise ValueError(
                    f"request wants num_steps={requested_steps} but this server "
                    f"runs num_steps={args.num_steps}; restart the server for that arm"
                )
            seed = obs.pop("roborigor/sampling_seed", None)
            if seed is not None:
                setattr(self._inner, rng_attr, jax.random.key(int(seed)))
            if "roborigor/images" in obs:
                images = obs.pop("roborigor/images")
                obs = {
                    "observation/image": images["agentview"],
                    "observation/wrist_image": images["wrist"],
                    "observation/state": obs.pop("roborigor/state"),
                    "prompt": obs.pop("roborigor/prompt"),
                }
            return self._inner.infer(obs)

    logging.info(
        f"Serving {args.config} num_steps={args.num_steps} on port {args.port}"
    )
    server = websocket_policy_server.WebsocketPolicyServer(
        policy=SeededPolicy(policy),
        host="0.0.0.0",
        port=args.port,
        metadata=getattr(policy, "metadata", {}),
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
