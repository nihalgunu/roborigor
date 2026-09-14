#!/usr/bin/env bash
# Per-box campaign entrypoint. Run from ~/openpi on a provisioned box.
#
#   bash campaign_box.sh <manifest.json> <box_id> <out_dir> [n_workers] [env]
#
# Assumes: setup_gpu_box.sh (+ setup_box_extras.sh when env=libero_plus) has
# run, the policy server for this arm is already listening on :8000, and
# roborigor is installed in the client venv. Workers split the box's items
# by stride; each appends to its own records file, so a killed worker loses
# at most one episode (resume re-runs the residue).
#
# Optional: RSYNC_TARGET=user@host:path syncs records home every 5 minutes.
set -euo pipefail

MANIFEST=$1; BOX_ID=$2; OUT_DIR=$3; N_WORKERS=${4:-6}; ENV_NAME=${5:-libero}

export MUJOCO_GL=egl
export MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH=${PYTHONPATH:-}:$PWD/third_party/libero

# refuse to run on a software renderer; latency numbers would be garbage
source examples/libero/.venv/bin/activate
python - <<'PY'
import mujoco, OpenGL.GL as gl
m = mujoco.MjModel.from_xml_string(
    '<mujoco><worldbody><light pos="0 0 3"/>'
    '<geom type="box" size=".2 .2 .2" rgba="1 0 0 1"/></worldbody></mujoco>')
r = mujoco.Renderer(m, 64, 64); mujoco.mj_forward(m, mujoco.MjData(m))
renderer = gl.glGetString(gl.GL_RENDERER).decode()
print("GL renderer:", renderer)
assert "llvmpipe" not in renderer.lower(), "software renderer; aborting"
PY

if [[ -n "${RSYNC_TARGET:-}" ]]; then
  ( while true; do rsync -a "$OUT_DIR/" "$RSYNC_TARGET/" || true; sleep 300; done ) &
  SYNC_PID=$!
  trap 'kill $SYNC_PID 2>/dev/null; rsync -a "$OUT_DIR/" "$RSYNC_TARGET/" || true' EXIT
fi

CLASSIFICATION_ARG=""
if [[ "$ENV_NAME" == "libero_plus" ]]; then
  CLASSIFICATION_ARG="--classification $PWD/third_party/libero-plus/libero/libero/benchmark/task_classification.json"
  export PYTHONPATH=$PYTHONPATH:$PWD/third_party/libero-plus
fi

pids=()
for ((w = 0; w < N_WORKERS; w++)); do
  roborigor run-shard \
    --manifest "$MANIFEST" --box-id "$BOX_ID" --out-dir "$OUT_DIR" \
    --env "$ENV_NAME" $CLASSIFICATION_ARG \
    --n-workers "$N_WORKERS" --worker-index "$w" &
  pids+=($!)
done
fail=0
for pid in "${pids[@]}"; do wait "$pid" || fail=1; done
exit $fail
