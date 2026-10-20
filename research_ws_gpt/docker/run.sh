#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
kind="${1:-ros}"
if [[ "$#" -gt 0 ]]; then shift; fi
case "$kind" in ros|garlio_gpt|analysis) ;; *) echo "Usage: $0 {ros|garlio_gpt|analysis} [command ...]" >&2; exit 2 ;; esac
command -v docker >/dev/null || { echo 'Docker is required on the execution host.' >&2; exit 1; }
dataset="${DATASET_ROOT:-$HOME/datasets/NTU4DRadLM}"
[[ -d "$dataset" ]] || { echo "Missing dataset directory: $dataset (set DATASET_ROOT)." >&2; exit 1; }
mkdir -p "$root/results"
args=(run --rm --init --shm-size=1g -v "$dataset:/data:ro" -v "$root:/work:ro" -v "$root/results:/results" -w /work)
if [[ -t 0 && -t 1 ]]; then args+=(-it); fi
if [[ "${WITH_X11:-0}" == 1 ]]; then
  : "${DISPLAY:?Set DISPLAY for optional X11 forwarding}"
  args+=(-e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:ro)
  if [[ -n "${XAUTHORITY:-}" ]]; then args+=(-v "$XAUTHORITY:/tmp/xauthority:ro" -e XAUTHORITY=/tmp/xauthority); fi
fi
commit="$(git -C "$root" rev-parse HEAD 2>/dev/null || echo unknown)"
dirty="$(git -C "$root" status --porcelain 2>/dev/null || true)"
args+=(-e "RESEARCH_GIT_COMMIT=$commit" -e "RESEARCH_GIT_DIRTY=$dirty")
image_kind="$kind"
if [[ "$kind" == garlio_gpt ]]; then
  image_kind=ros
  args+=(-e RESEARCH_GARLIO_VARIANT=fork -e RESEARCH_FORK_SOURCE=/repo -v "$root/..:/repo:ro")
fi
if [[ "$#" -eq 0 ]]; then set -- bash; fi
exec docker "${args[@]}" "radar-point-lio-${image_kind}:phase0-gpt" "$@"
