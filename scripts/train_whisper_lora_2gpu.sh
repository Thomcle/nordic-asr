#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/nordic-asr}"
PY="$HOME/miniconda3/envs/nordic-asr/bin/python"

"$PY" -m torch.distributed.run --standalone --nproc_per_node=2 \
  "$ROOT/scripts/train_whisper_lora.py" \
  --train "$ROOT/data/manifests/npsc_train.jsonl" \
  --validation "$ROOT/data/manifests/npsc_validation.jsonl" \
  --model "NbAiLab/nb-whisper-large" \
  --output "$ROOT/runs/nb-whisper-large-npsc-lora" \
  --steps "${STEPS:-2000}" \
  --eval-steps "${EVAL_STEPS:-1000}" \
  --save-steps "${SAVE_STEPS:-1000}"
