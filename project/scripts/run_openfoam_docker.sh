#!/usr/bin/env bash
# Run OpenFOAM Allrun inside opencfd/openfoam-default Docker image.
set -euo pipefail

CASE_DIR="${1:?Usage: run_openfoam_docker.sh /path/to/case [image]}"
IMAGE="${2:-opencfd/openfoam-default:2412}"
CASE_DIR="$(cd "$CASE_DIR" && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker CLI not found. Install colima + docker-cli or Docker Desktop." >&2
  exit 1
fi

if [[ -z "${DOCKER_HOST:-}" && -S "$HOME/.colima/default/docker.sock" ]]; then
  export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
fi

echo "Using image: $IMAGE"
echo "Case dir:    $CASE_DIR"
docker pull "$IMAGE"

docker run --rm --platform linux/amd64 \
  -v "${CASE_DIR}:/case" \
  -w /case \
  "$IMAGE" \
  bash -c '
    set -e
    cd /case
    chmod +x Allrun
    ./Allrun
  '

echo "Done. Logs and VTK output are in: $CASE_DIR"
