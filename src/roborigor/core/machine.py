"""On-box environment checks.

The silent failure mode this guards against: MuJoCo EGL initializing on the
llvmpipe software renderer instead of the GPU. Everything runs, just far
slower, and any latency number recorded is garbage. Always assert on the
actual GL_RENDERER string, never on successful initialization.

Python 3.8 compatible: imported in the LIBERO client process.
"""

from __future__ import annotations

import os

REQUIRED_ENV = {
    "MUJOCO_GL": "egl",
    "MUJOCO_EGL_DEVICE_ID": "0",  # 0 = the GPU on the reference box; 3 = llvmpipe
}


def check_renderer(gl_renderer: str) -> None:
    """Raise unless the renderer string names a real GPU."""
    if not gl_renderer:
        raise RuntimeError("empty GL_RENDERER string; renderer probe failed")
    if "llvmpipe" in gl_renderer.lower() or "softpipe" in gl_renderer.lower():
        raise RuntimeError(
            f"software renderer in use: {gl_renderer!r}. "
            "Check MUJOCO_EGL_DEVICE_ID; latency numbers would be garbage."
        )


def check_env() -> list[str]:
    """Return problems with the MuJoCo-related environment; empty means fine."""
    problems = []
    for key, expected in REQUIRED_ENV.items():
        got = os.environ.get(key)
        if got != expected:
            problems.append(f"{key}={got!r}, expected {expected!r}")
    return problems
