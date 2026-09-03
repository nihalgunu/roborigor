#!/usr/bin/env bash
# RoboRigor additions on top of the base openpi/LIBERO provisioning.
# Run from ~/openpi AFTER the base setup script has completed and verified.
#
#   HARNESS_WHEEL=~/roborigor-*.whl bash setup_box_extras.sh      # wheel only
#   SETUP_LIBERO_PLUS=1 ... bash setup_box_extras.sh                # + fork venv
#   SETUP_LEROBOT=1     ... bash setup_box_extras.sh                # + SmolVLA venv
#
# Rules learned the hard way (sessions 2-4):
#   - uv-created venvs ship WITHOUT pip: every install goes through
#     `uv pip install --python <venv-python>`; never `source activate` + pip.
#   - non-interactive shells miss ~/.local/bin, where uv lives.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
log() { printf '\n=== %s ===\n' "$*"; }

HARNESS_WHEEL=${HARNESS_WHEEL:-}

if [[ -n "$HARNESS_WHEEL" ]]; then
  log "roborigor wheel into the LIBERO client venv"
  uv pip install --quiet --python examples/libero/.venv/bin/python "$HARNESS_WHEEL" numpy
  examples/libero/.venv/bin/python -c "import roborigor; print('roborigor', roborigor.__version__)"
fi

if [[ "${SETUP_LIBERO_PLUS:-0}" == "1" ]]; then
  log "LIBERO-Plus fork (SEPARATE venv: the fork installs itself as 'libero')"
  # apt deps documented in the fork's README (wand needs MagickWand's .so)
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    libmagickwand-dev libexpat1 libfontconfig1-dev libpython3-stdlib
  mkdir -p third_party
  if [[ ! -d third_party/libero-plus ]]; then
    git clone --quiet https://github.com/sylvestf/LIBERO-plus third_party/libero-plus
  fi
  uv venv --quiet --python 3.8 third_party/libero-plus/.venv
  VP=$PWD/third_party/libero-plus/.venv/bin/python
  # same dependency base as the PROVEN stock LIBERO client venv (torch cu113
  # et al.), then the fork on top; the fork's own requirements files vary
  uv pip install --quiet --python "$VP" \
    -r examples/libero/requirements.txt -r third_party/libero/requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cu113 --index-strategy unsafe-best-match
  uv pip install --quiet --python "$VP" -e third_party/libero-plus
  if [[ -f third_party/libero-plus/extra_requirements.txt ]]; then
    uv pip install --quiet --python "$VP" -r third_party/libero-plus/extra_requirements.txt \
      --extra-index-url https://download.pytorch.org/whl/cu113 --index-strategy unsafe-best-match
  else
    echo "NOTE: fork has no extra_requirements.txt (relying on stock base deps)"
  fi
  uv pip install --quiet --python "$VP" -e packages/openpi-client huggingface_hub
  if [[ -n "$HARNESS_WHEEL" ]]; then
    uv pip install --quiet --python "$VP" "$HARNESS_WHEEL"
  fi
  "$VP" -c "import huggingface_hub; print('huggingface_hub', huggingface_hub.__version__)"
  log "LIBERO-Plus assets (zip is rooted at the authors' internal path, not assets/)"
  "$VP" - <<'PY'
from huggingface_hub import hf_hub_download
import zipfile, pathlib, shutil
z = hf_hub_download("Sylvest/LIBERO-plus", "assets.zip", repo_type="dataset")
staging = pathlib.Path("third_party/libero-plus/_assets_staging")
if not staging.exists():
    zipfile.ZipFile(z).extractall(staging)
dest = pathlib.Path("third_party/libero-plus/libero/libero/assets")
dest.mkdir(parents=True, exist_ok=True)
roots = sorted(p for p in staging.rglob("assets") if p.is_dir())
print("asset roots found in archive:", [str(r) for r in roots][:3])
for root in roots:
    for item in root.iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        elif not target.exists():
            shutil.copy2(item, target)
probe = dest / "scenes/kitchen250/kitchen_table_FabricCanvas001_COL_VAR1_4K.xml"
n_scenes = len(list((dest / "scenes").rglob("*.xml"))) if (dest / "scenes").exists() else 0
print(f"scene xmls in place: {n_scenes}; probe exists: {probe.exists()}")
assert n_scenes > 0, "no scene xmls after merge; inspect staging layout"
shutil.rmtree(staging)
PY
  log "LIBERO-Plus config: repoint global ~/.libero at the fork tree"
  # The fork ignores LIBERO_CONFIG_PATH and reads ~/.libero/config.yaml
  # (session-9 finding). A plus box never runs the stock client at the same
  # time, so the global config is repointed; stock copy kept as backup.
  [[ -f "$HOME/.libero/config.yaml" ]] && cp "$HOME/.libero/config.yaml" "$HOME/.libero/config.stock.yaml"
  mkdir -p "$HOME/.libero" third_party/libero-plus/libero/datasets
  "$VP" - <<'PY'
import os, yaml
root = os.path.abspath("third_party/libero-plus/libero/libero")
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
print("wrote", path, "->", root)
PY

  log "LIBERO-Plus fork sanity"
  # the fork's editable install does not register the package (same quirk as
  # stock LIBERO); PYTHONPATH is upstream's documented mechanism
  PYTHONPATH="${PYTHONPATH:-}:$PWD/third_party/libero-plus" "$VP" - <<'PY'
import pathlib
from libero.libero import benchmark
suites = set(benchmark.get_benchmark_dict())
stock = {"libero_spatial", "libero_object", "libero_goal", "libero_10", "libero_90"}
assert suites != stock, "this venv resolves to stock LIBERO, not the fork"
p = pathlib.Path("third_party/libero-plus/libero/libero/benchmark/task_classification.json")
assert p.exists(), f"classification map missing at {p}"
from roborigor.envs.libero_plus import load_classification
axes = {m["axis"] for m in load_classification(str(p)).values()}
print("fork OK; suites:", len(suites), "axes:", sorted(axes))
PY
fi

if [[ "${SETUP_LEROBOT:-0}" == "1" ]]; then
  log "lerobot venv for SmolVLA serving (py3.10)"
  uv venv --quiet --python 3.10 "$HOME/lerobot-venv"
  LP=$HOME/lerobot-venv/bin/python
  uv pip install --quiet --python "$LP" "lerobot[libero]" || {
    echo "lerobot[libero] extra failed; falling back to plain lerobot (VERIFY-ON-BOX)"
    uv pip install --quiet --python "$LP" lerobot
  }
  # SmolVLM's processor hard-requires num2words at runtime (session-4 finding)
  uv pip install --quiet --python "$LP" num2words
  # openpi-client pins numpy<2 but lerobot needs numpy>=2: install the client
  # without deps; the wire codec is verified below on the venv's numpy
  uv pip install --quiet --python "$LP" --no-deps -e packages/openpi-client
  uv pip install --quiet --python "$LP" msgpack websockets
  # the serve script imports roborigor.serve.ws_server (session finding:
  # serving died at import when the wheel was missing from this venv)
  if [[ -n "$HARNESS_WHEEL" ]]; then
    uv pip install --quiet --python "$LP" "$HARNESS_WHEEL"
  fi
  "$LP" -c "from roborigor.serve.ws_server import WebsocketPolicyServer; print('ws_server import OK')"
  "$LP" -c "from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy; print('SmolVLA import OK')"
  "$LP" -c "import numpy, msgpack; from openpi_client import msgpack_numpy; a=numpy.zeros((2,3)); assert (msgpack_numpy.unpackb(msgpack_numpy.Packer().pack({'x': a}))['x']==a).all(); print('wire codec OK on numpy', numpy.__version__)"
fi

log "extras complete"
