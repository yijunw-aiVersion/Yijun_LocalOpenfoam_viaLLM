#!/usr/bin/env bash
# Start Colima (QEMU) + run CFD simulation in Docker.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR="$(cd "$PROJECT_DIR/.." && pwd)/test"
CONDA_ENV="${CONDA_ENV:-cfd-agent-test}"
ENV_BIN="${CONDA_PREFIX:-$HOME/miniforge3/envs/$CONDA_ENV}/bin"
export PATH="$ENV_BIN:$PATH"

if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -x /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi

PROMPT="${1:-圆柱直径0.1米，雷诺数100，来流速度1米每秒。}"

echo "==> [1/3] Colima setup (QEMU)"
if ! command -v qemu-img >/dev/null 2>&1; then
  echo "ERROR: qemu-img not found. Install QEMU first:"
  echo "  brew install qemu"
  exit 1
fi

rm -f "$HOME/.colima/_lima/_disks/colima/in_use_by" 2>/dev/null || true
export LIMA_HOME="$HOME/.colima/_lima"

if colima status 2>/dev/null | grep -q "running"; then
  echo "    Colima already running"
else
  echo "    Reset + start Colima (QEMU)..."
  colima delete -f 2>/dev/null || true
  colima start --cpu 4 --memory 8 --disk 40 --vm-type qemu --mount-type 9p
fi

export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
docker version
echo ""

echo "==> [2/3] Pull OpenFOAM image (first run only)"
docker pull opencfd/openfoam-default:2412
echo ""

echo "==> [3/3] Run CFD workflow"
cd "$PROJECT_DIR"
export MPLCONFIGDIR="$TEST_DIR/.matplotlib"
mkdir -p "$MPLCONFIGDIR"
nl-cfd-solver --docker \
  "$PROMPT" \
  --output-dir "$TEST_DIR"

echo ""
echo "==> Done. Check latest run under: $TEST_DIR"
