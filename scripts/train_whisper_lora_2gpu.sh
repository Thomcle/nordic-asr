#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/nordic-asr}"
PY="$HOME/miniconda3/envs/nordic-asr/bin/python"

"$PY" -m torch.distributed.run --standalone --nproc_per_node=2 \
  "$ROOT/scripts/train_whisper_lora.py" \
  --train "$ROOT/data/manifests/train_balanced.jsonl" \
  --validation "$ROOT/data/manifests/validation.jsonl" \
  --output "$ROOT/runs/whisper-large-v3-lora"

