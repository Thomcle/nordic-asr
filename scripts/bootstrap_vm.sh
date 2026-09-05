#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/nordic-asr}"
ENV_NAME="${ENV_NAME:-nordic-asr}"

mkdir -p "$ROOT"/{data/{raw,manifests,eval},models,runs,logs}

if ! "$HOME/miniconda3/bin/conda" env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  if "$HOME/miniconda3/bin/conda" env list | awk '{print $1}' | grep -qx "Omnilingual"; then
    # Reuse the tested CUDA/PyTorch stack already present on this VM.
    "$HOME/miniconda3/bin/conda" create -y -n "$ENV_NAME" --clone Omnilingual
  else
    "$HOME/miniconda3/bin/conda" create -y -n "$ENV_NAME" python=3.11 pip
  fi
fi

"$HOME/miniconda3/envs/$ENV_NAME/bin/python" -m pip install --upgrade pip
"$HOME/miniconda3/envs/$ENV_NAME/bin/python" -m pip install -e "$ROOT[quality,dev]"

echo "Environment ready: conda activate $ENV_NAME"
