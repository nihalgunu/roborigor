"""Minimal websocket policy server, wire-compatible with openpi-client.

Protocol (mirrors openpi's WebsocketPolicyServer): on connect the server
sends msgpack-numpy-packed metadata; then each received message is an
unpacked observation dict, answered with the packed infer() result. Used
by serve scripts in policy venvs (lerobot, openvla-oft) where openpi's
own server module is absent; those venvs do have openpi-client installed,
whose msgpack-numpy codec guarantees an identical wire format.

Adapted from the WebsocketPolicyServer in Physical Intelligence's openpi
(Apache-2.0); vendored so non-openpi policy venvs need no openpi install.

Requires: websockets >= 12 (sync server API), openpi_client.

Python 3.8 compatible.
"""

from __future__ import annotations

import logging
import traceback


class WebsocketPolicyServer:
    def __init__(self, policy, host: str = "0.0.0.0", port: int = 8000, metadata=None):
        self._policy = policy
        self._host = host
        self._port = port
        self._metadata = metadata or {}

    def serve_forever(self) -> None:
        from openpi_client import msgpack_numpy
        from websockets.sync.server import serve

        packer = msgpack_numpy.Packer()

        def handler(ws):
            ws.send(packer.pack(self._metadata))
            while True:
                try:
                    obs = msgpack_numpy.unpackb(ws.recv())
                except Exception:  # connection closed
                    return
                try:
                    ws.send(packer.pack(self._policy.infer(obs)))
                except Exception:
                    err = traceback.format_exc()
                    logging.error(err)
                    ws.send(packer.pack({"error": err}))
                    return

        with serve(handler, self._host, self._port, max_size=None) as server:
            logging.info(f"listening on {self._host}:{self._port}")
            server.serve_forever()
