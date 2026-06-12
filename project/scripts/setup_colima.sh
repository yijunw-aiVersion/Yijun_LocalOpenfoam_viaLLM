#!/usr/bin/env bash
# Start Colima Docker runtime (QEMU backend — no vz entitlement needed).
set -euo pipefail

CONDA_ENV="${CONDA_ENV:-cfd-agent-test}"
ENV_BIN="${CONDA_PREFIX:-$HOME/miniforge3/envs/$CONDA_ENV}/bin"
export PATH="$ENV_BIN:$PATH"

# Homebrew qemu (if installed)
if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -x /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi

echo "==> Colima / Docker setup (QEMU)"
echo "    PATH includes: $ENV_BIN"

if ! command -v colima >/dev/null 2>&1; then
  echo "ERROR: colima not found. Run:"
  echo "  conda activate $CONDA_ENV"
  echo "  conda install -c conda-forge colima docker-cli -y"
  exit 1
fi

if ! command -v qemu-img >/dev/null 2>&1; then
  echo "ERROR: qemu-img not found. Colima QEMU mode requires QEMU:"
  echo "  brew install qemu"
  echo "Then re-run this script."
  exit 1
fi

if colima status 2>/dev/null | grep -q "running"; then
  echo "==> Colima already running"
else
  echo "==> Resetting broken Colima instance (if any)..."
  colima delete -f 2>/dev/null || true
  rm -f "$HOME/.colima/_lima/_disks/colima/in_use_by" 2>/dev/null || true
  echo "==> Starting Colima (QEMU)..."
  colima start --cpu 4 --memory 8 --disk 40 --vm-type qemu --mount-type 9p
fi

export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
docker version
echo ""
echo "==> Ready. Run simulation with:"
echo "  conda activate $CONDA_ENV"
echo "  cd $(cd "$(dirname "$0")/.." && pwd)"
echo "  export MPLCONFIGDIR=../test/.matplotlib"
echo "  PYTHONPATH=src python -m cfd_workflow.cli --docker \\"
echo "    \"圆柱直径0.1米，雷诺数100，来流速度1米每秒。\" \\"
echo "    --output-dir ../test"
