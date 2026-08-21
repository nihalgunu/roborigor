#!/usr/bin/env bash
# Duplicated into roborigor from the author's flowhelm-lab provisioning script
# (validated 2026-08-15), per the no-dependency rule between the projects.
# Provision a fresh Lambda Labs GPU box for openpi + LIBERO evaluation.
#
# Validated 2026-08-15 on: Lambda gpu_1x_a100_sxm4 (A100-SXM4-40GB), us-east-1,
# Ubuntu 22.04.5, kernel 6.8.0-60-generic.
#
# Idempotent: safe to re-run. Reboots once if the NVIDIA driver needs it.
#
# Cold-provision verified 2026-08-15: fresh us-east-1 A100 SXM4 box to passing
# verification in 3m43s of script wall-time (one automatic reboot, no manual
# intervention). Excludes Lambda instance boot (~5-10 min) and the pi05_libero
# checkpoint download, which happens on first serve (6.2 GiB, ~6 s from GCS).
#
# Usage:  bash setup_gpu_box.sh
set -euo pipefail

OPENPI_DIR="${OPENPI_DIR:-$HOME/openpi}"
OPENPI_REPO="https://github.com/Physical-Intelligence/openpi.git"

log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. Rendering + NVIDIA GL stack
#
# Lambda's A100 image ships the *compute-only* driver variant
# (libnvidia-compute-570-server). It provides CUDA but deliberately omits the
# GL/EGL userspace libs, so there is no libEGL_nvidia.so and no
# /usr/share/glvnd/egl_vendor.d/10_nvidia.json. Without those, MuJoCo either
# fails to create an EGL context or silently falls back to llvmpipe (CPU
# software rasterisation), which is dramatically slower for rollouts.
#
# Installing libnvidia-gl-<branch>-server also upgrades libnvidia-compute and
# the DKMS package to the newest point release in the branch. Userspace then
# outruns the *running* kernel module and nvidia-smi fails with
# "Driver/library version mismatch". DKMS has already rebuilt the matching
# module at that point, so a single reboot resolves it.
# ---------------------------------------------------------------------------
log "Installing rendering libraries"
sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  libegl1 libegl-mesa0 libosmesa6 libosmesa6-dev libgl1-mesa-glx \
  libglew-dev libglfw3 patchelf

DRIVER_BRANCH="$(dpkg -l | grep -oE 'libnvidia-compute-[0-9]+-server' | head -1 | grep -oE '[0-9]+' || true)"
if [[ -n "$DRIVER_BRANCH" ]] && ! ls /usr/share/glvnd/egl_vendor.d/10_nvidia.json >/dev/null 2>&1; then
  log "Installing NVIDIA GL/EGL userspace for driver branch ${DRIVER_BRANCH}"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "libnvidia-gl-${DRIVER_BRANCH}-server"
fi

# Reboot only if userspace and the loaded kernel module disagree.
if ! nvidia-smi >/dev/null 2>&1; then
  log "NVIDIA userspace/kernel version mismatch — rebooting to load the rebuilt module"
  echo "Re-run this script after the box comes back up."
  sudo reboot
  exit 0
fi

# ---------------------------------------------------------------------------
# 2. uv + openpi
# ---------------------------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

if [[ ! -d "$OPENPI_DIR" ]]; then
  log "Cloning openpi"
  git clone --recurse-submodules "$OPENPI_REPO" "$OPENPI_DIR"
fi
cd "$OPENPI_DIR"
git submodule update --init --recursive

log "Syncing openpi environment (Python 3.11)"
GIT_LFS_SKIP_SMUDGE=1 uv sync
GIT_LFS_SKIP_SMUDGE=1 uv pip install -e .

# ---------------------------------------------------------------------------
# 3. LIBERO environment
#
# LIBERO pins Python 3.8 and an old torch (cu113), which cannot coexist with
# openpi's Python 3.11 environment. That incompatibility is the reason openpi
# splits inference across a websocket policy server and a client process.
# ---------------------------------------------------------------------------
log "Creating LIBERO environment (Python 3.8)"
uv venv --python 3.8 examples/libero/.venv
# shellcheck disable=SC1091
source examples/libero/.venv/bin/activate
uv pip sync examples/libero/requirements.txt third_party/libero/requirements.txt \
  --extra-index-url https://download.pytorch.org/whl/cu113 --index-strategy=unsafe-best-match
uv pip install -e packages/openpi-client
uv pip install -e third_party/libero

# ---------------------------------------------------------------------------
# 4. Pre-seed the LIBERO config
#
# libero/libero/__init__.py calls input() at import time when ~/.libero/config.yaml
# is absent, which deadlocks any non-interactive run (CI, Docker, nohup, a sweep).
# Writing the default config up front avoids the prompt entirely.
# ---------------------------------------------------------------------------
log "Writing ~/.libero/config.yaml"
mkdir -p "$HOME/.libero"
python - <<'PY'
import os, yaml
root = os.path.abspath("third_party/libero/libero/libero")
cfg = {
    "benchmark_root": root,
    "bddl_files": os.path.join(root, "./bddl_files"),
    "init_states": os.path.join(root, "./init_files"),
    "datasets": os.path.join(root, "../datasets"),
    "assets": os.path.join(root, "./assets"),
}
path = os.path.expanduser("~/.libero/config.yaml")
with open(path, "w") as f:
    yaml.dump(cfg, f)
print("wrote", path)
PY
deactivate

# ---------------------------------------------------------------------------
# 5. Verify
# ---------------------------------------------------------------------------
log "Verifying"
uv run python -c "import jax; assert jax.default_backend()=='gpu'; print('JAX GPU:', jax.devices())"

# shellcheck disable=SC1091
source examples/libero/.venv/bin/activate
MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=0 python - <<'PY'
import mujoco, OpenGL.GL as gl
m = mujoco.MjModel.from_xml_string(
    '<mujoco><worldbody><light pos="0 0 3"/>'
    '<geom type="box" size=".2 .2 .2" rgba="1 0 0 1"/></worldbody></mujoco>')
d = mujoco.MjData(m)
r = mujoco.Renderer(m, 128, 128)
mujoco.mj_forward(m, d); r.update_scene(d); r.render()
renderer = gl.glGetString(gl.GL_RENDERER).decode()
print("MuJoCo GL renderer:", renderer)
assert "llvmpipe" not in renderer.lower(), \
    "Software rendering! Check MUJOCO_EGL_DEVICE_ID — see docs/gpu-box-setup.md"
PY

# LIBERO itself must import (needs PYTHONPATH — its editable install does not
# register the package; this is upstream's documented mechanism).
PYTHONPATH="$PWD/third_party/libero" python -c \
  "from libero.libero import benchmark; print('LIBERO import OK:', len(benchmark.get_benchmark_dict()), 'suites')"
deactivate

cat <<'EOF'

Setup complete.

Always export these before running LIBERO:

    export MUJOCO_GL=egl
    export MUJOCO_EGL_DEVICE_ID=0     # 0 = the A100; other indices are Mesa/llvmpipe
    export PYTHONPATH=$PYTHONPATH:$PWD/third_party/libero

Run an evaluation (two shells):

    uv run scripts/serve_policy.py --env LIBERO
    source examples/libero/.venv/bin/activate && python examples/libero/main.py

EOF
