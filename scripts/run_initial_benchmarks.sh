#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/nordic-asr}"
PY="$HOME/miniconda3/envs/nordic-asr/bin/python"
MANIFEST="${1:-$ROOT/data/eval/fleurs_nb/test.jsonl}"

mkdir -p "$ROOT/runs/baselines"

"$PY" "$ROOT/scripts/baseline_transcribe.py" "$MANIFEST" \
  --model openai/whisper-large-v3 \
  --language norwegian \
  --batch-size 8 \
  --out "$ROOT/runs/baselines/whisper-large-v3_fleurs-nb.jsonl"

"$PY" "$ROOT/scripts/baseline_transcribe.py" "$MANIFEST" \
  --model NbAiLab/nb-whisper-large-v0.8 \
  --language norwegian \
  --batch-size 8 \
  --out "$ROOT/runs/baselines/nb-whisper-large-v0.8_fleurs-nb.jsonl"

