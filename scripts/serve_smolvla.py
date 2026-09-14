"""Serve SmolVLA (lerobot) behind the roborigor wire protocol.

Runs in the lerobot venv (py3.10). Receives canonical observations under
roborigor/ keys, maps them onto the checkpoint's declared input features,
and returns a full action chunk. SmolVLA has a flow-matching action head,
so roborigor/sampling_seed reseeds torch per request with the same
episode-level schedule semantics as the openpi wrapper.

VERIFY-ON-BOX (pilot 2c): the feature-name mapping below is introspected
from the checkpoint config and logged at startup; eyeball it before
trusting any episode. num_steps control for SmolVLA is NOT wired yet
(lerobot's denoising step count lives in the policy config); requests
carrying roborigor/num_steps are rejected so a V2-style campaign cannot
silently run unconfigured.

  ~/lerobot-venv/bin/python serve_smolvla.py \
      --checkpoint lerobot/smolvla_libero --port 8001
"""

import argparse
import logging
import time


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default="lerobot/smolvla_libero")
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--num_steps", type=int, default=None,
                    help="override the flow head's denoising steps (per server process)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO)

    import numpy as np
    import torch
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy

    policy = SmolVLAPolicy.from_pretrained(args.checkpoint)
    if args.num_steps is not None:
        policy.config.num_steps = args.num_steps
        logging.info(f"flow num_steps overridden to {args.num_steps}")
    policy.to(args.device).eval()

    # lerobot runs observations through checkpoint-shipped processors before
    # the policy (language tokenization, normalization) and un-normalizes
    # actions after (session-c probe: predict_action_chunk KeyErrors on
    # observation.language.tokens without them). Import path varies by
    # lerobot version; probe surfaces whichever this box has.
    preprocessor = postprocessor = None
    for modpath in ("lerobot.processor", "lerobot.policies.factory", "lerobot.processor.factory"):
        try:
            mod = __import__(modpath, fromlist=["make_pre_post_processors"])
            make = mod.make_pre_post_processors
            try:
                preprocessor, postprocessor = make(policy.config, pretrained_path=args.checkpoint)
            except TypeError:
                preprocessor, postprocessor = make(policy.config, args.checkpoint)
            logging.info(f"processors via {modpath}")
            break
        except (ImportError, AttributeError) as e:
            logging.info(f"no processors via {modpath}: {e}")
    if preprocessor is None:
        raise RuntimeError("could not build lerobot pre/post processors; inspect lerobot version")

    image_features = [k for k in policy.config.input_features if "image" in k]
    state_features = [k for k in policy.config.input_features if "state" in k]
    logging.info(f"image features: {image_features}")
    logging.info(f"state features: {state_features}")
    if not image_features or not state_features:
        raise RuntimeError("checkpoint declares no image/state features; wrong model?")

    # canonical -> feature mapping: wrist-named feature gets the wrist camera,
    # first remaining feature gets agentview. Logged; verify on box.
    wrist_feats = [k for k in image_features if "wrist" in k.lower()]
    main_feats = [k for k in image_features if k not in wrist_feats]
    mapping = {}
    if wrist_feats:
        mapping[main_feats[0]] = "agentview"
        mapping[wrist_feats[0]] = "wrist"
    else:
        # lerobot/smolvla_libero declares generic camera1/2/3: positional
        # convention is camera1=agentview, camera2=wrist (VERIFY-ON-BOX by
        # smoke success rate; a swapped mapping tanks it visibly)
        ordered = sorted(main_feats)
        mapping[ordered[0]] = "agentview"
        if len(ordered) > 1:
            mapping[ordered[1]] = "wrist"
    unfed = [k for k in image_features if k not in mapping]
    logging.info(f"camera mapping: {mapping}; unfed features (omitted): {unfed}")

    class SmolVLAServed:
        metadata = {"policy_id": "smolvla", "checkpoint": args.checkpoint}

        def infer(self, obs: dict) -> dict:
            req_ns = obs.pop("roborigor/num_steps", None)
            if req_ns is not None and int(req_ns) != policy.config.num_steps:
                raise ValueError(
                    f"request num_steps {req_ns} != server num_steps "
                    f"{policy.config.num_steps}; per-request override is not "
                    "wired for SmolVLA -- start a server per num_steps value"
                )
            seed = obs.pop("roborigor/sampling_seed", None)
            if seed is not None:
                torch.manual_seed(int(seed))
            images = obs["roborigor/images"]
            batch = {}
            # feed ONLY mapped cameras: lerobot omits absent cameras and
            # SmolVLA skips missing keys; a zero-filled camera3 is consumed
            # as a real (black) view and tanks the policy (0/10 clean smoke)
            for feat, cam in mapping.items():
                img = images[cam]
                t = torch.from_numpy(np.ascontiguousarray(img)).float() / 255.0
                batch[feat] = t.permute(2, 0, 1).unsqueeze(0).to(args.device)
            batch[state_features[0]] = (
                torch.from_numpy(np.asarray(obs["roborigor/state"], dtype=np.float32))
                .unsqueeze(0)
                .to(args.device)
            )
            batch["task"] = obs["roborigor/prompt"]
            t0 = time.monotonic()
            with torch.no_grad():
                processed = preprocessor(batch)
                chunk = policy.predict_action_chunk(processed)
                try:
                    chunk = postprocessor(chunk)
                except Exception:
                    chunk = postprocessor({"action": chunk})["action"]
                chunk = chunk[0]
            infer_ms = (time.monotonic() - t0) * 1000.0
            return {
                "actions": chunk.float().cpu().numpy(),
                "server_timing": {"infer_ms": infer_ms},
            }

    from roborigor.serve.ws_server import WebsocketPolicyServer

    server = WebsocketPolicyServer(
        policy=SmolVLAServed(), host="0.0.0.0", port=args.port,
        metadata=SmolVLAServed.metadata,
    )
    logging.info(f"Serving SmolVLA on port {args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
