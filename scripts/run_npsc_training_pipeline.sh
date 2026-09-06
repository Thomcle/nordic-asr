#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/nordic-asr}"
PY="$HOME/miniconda3/envs/nordic-asr/bin/python"
ARCHIVES="$ROOT/data/raw/spraakbanken/npsc"
EXTRACTED="$ROOT/data/processed/npsc"
MANIFESTS="$ROOT/data/manifests"

mkdir -p "$EXTRACTED" "$MANIFESTS" "$ROOT/runs"

if [[ ! -f "$EXTRACTED/.complete" ]]; then
  for archive in "$ARCHIVES"/NPSC_{1..5}.tar.gz; do
    echo "Extracting $(basename "$archive")"
    tar -xzf "$archive" -C "$EXTRACTED" \
      --wildcards --no-anchored \
      '*_sentence_data.json' 'audio/*.wav'
  done
  touch "$EXTRACTED/.complete"
fi

"$PY" "$ROOT/scripts/prepare_npsc.py" "$EXTRACTED" \
  --out "$MANIFESTS" \
  --validation-percent 5
"$PY" "$ROOT/scripts/validate_manifest.py" \
  "$MANIFESTS/npsc_train.jsonl" --check-audio
"$PY" "$ROOT/scripts/validate_manifest.py" \
  "$MANIFESTS/npsc_validation.jsonl" --check-audio
head -n 64 "$MANIFESTS/npsc_validation.jsonl" \
  > "$MANIFESTS/npsc_validation_smoke.jsonl"

echo "Waiting for the baseline jobs to release both GPUs"
while pgrep -f 'python scripts/baseline_(transcribe|omniasr)\.py' >/dev/null; do
  sleep 30
done

echo "Running a five-step distributed smoke test"
"$PY" -m torch.distributed.run --standalone --nproc_per_node=2 \
  "$ROOT/scripts/train_whisper_lora.py" \
  --train "$MANIFESTS/npsc_train.jsonl" \
  --validation "$MANIFESTS/npsc_validation_smoke.jsonl" \
  --model "NbAiLab/nb-whisper-large" \
  --output "$ROOT/runs/nb-whisper-large-npsc-lora-smoke" \
  --steps 5 \
  --eval-steps 5 \
  --save-steps 5 \
  --warmup-steps 1 \
  --batch-size 1 \
  --gradient-accumulation 1

echo "Starting the full Norwegian LoRA run"
STEPS="${STEPS:-2000}" ROOT="$ROOT" \
  "$ROOT/scripts/train_whisper_lora_2gpu.sh"
