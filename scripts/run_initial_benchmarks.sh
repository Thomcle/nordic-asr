#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/nordic-asr}"
PY="$HOME/miniconda3/envs/nordic-asr/bin/python"
MANIFEST="${1:-$ROOT/data/eval/fleurs_nb/test.jsonl}"

mkdir -p "$ROOT/runs/baselines"

"$PY" "$ROOT/scripts/baseline_transcribe.py" "$MANIFEST" \
  --model openai/whisper-large-v3 \
  --revision 06f233fe06e710322aca913c1bc4249a0d71fce1 \
  --language norwegian \
  --batch-size 8 \
  --out "$ROOT/runs/baselines/whisper-large-v3_fleurs-nb.jsonl"

"$PY" "$ROOT/scripts/baseline_transcribe.py" "$MANIFEST" \
  --model NbAiLab/nb-whisper-large \
  --revision 8c6249fdeeb4dcd05e5735a4c39640607eb6e4ac \
  --language norwegian \
  --batch-size 8 \
  --out "$ROOT/runs/baselines/nb-whisper-large_fleurs-nb.jsonl"
