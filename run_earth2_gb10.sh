#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ $# -lt 1 ]]; then
  echo 'Usage: bash run_earth2_gb10.sh YYYY-MM-DDTHH:00:00Z [six-hour-steps]' >&2
  exit 2
fi
# GB10 uses unified memory. This conservative gate is not a peak-memory guarantee.
available_kib=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
if (( available_kib < 60 * 1024 * 1024 )); then
  echo 'Earth-2 not started: less than 60 GiB available. Leave existing services running and arrange a free GPU window.' >&2
  exit 3
fi
docker image inspect sanantonio-earth2:0.18.0 >/dev/null
mkdir -p earth2-results earth2-cache
model_mount=()
model_args=()
if [[ -f preloaded-models/provenance.json ]]; then
  model_mount=(-v "$PWD/preloaded-models:/models")
  model_args=(--model-directory /models)
fi
docker run --rm --gpus all --shm-size=2g \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e EARTH2STUDIO_CACHE=/cache \
  -v "$PWD/earth2-results:/results" -v "$PWD/earth2-cache:/cache" \
  "${model_mount[@]}" \
  sanantonio-earth2:0.18.0 --initial-time "$1" --steps "${2:-1}" \
  --output /results/earth2_rainfall.csv "${model_args[@]}"
