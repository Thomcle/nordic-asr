# Nordic ASR

Speech recognition project for:

- Norwegian Bokmål (`nob`) and Nynorsk (`nno`);
- Northern Sámi (`sme`) first, followed by Lule (`smj`) and Southern Sámi
  (`sma`) when sufficient data is available;
- Kven (`fkv`).

The repository targets a machine equipped with two NVIDIA L4 GPUs. Data,
models, and experiment artifacts remain outside Git in `data/`, `models/`, and
`runs/`.

## Strategy

We do not claim that a model is state of the art before an independent
evaluation. Two model families are compared:

1. **Whisper large-v3 / NB-Whisper**: strong punctuation, robustness, and
   product integration; adapted with LoRA followed by partial unfreezing.
2. **Sámi wav2vec2 22k / OmniASR CTC**: strong acoustic initialization for
   minority languages and fast inference.

The winning model will be selected using **macro WER by language**, CER,
robustness to noise, proper nouns, throughput, and memory usage. Training data
must never contaminate the test sets.

## Repository layout

```text
configs/       parameters and source registry
scripts/       acquisition, validation, training, and evaluation
src/           shared normalization and metrics
data/raw/      source archives
data/manifests normalized JSONL manifests
data/eval/     frozen evaluation sets
models/        downloaded weights and trained models
runs/          logs and checkpoints
```

Non-traditional sources such as YouTube, Vimeo, NRK, Sveriges Radio, and
KommuneTV are documented in `docs/EXTERNAL_SOURCES.md` and declared in
`configs/external_sources.yaml` and `configs/acquisition.yaml`.

## VM setup

```bash
cd ~/nordic-asr
bash scripts/bootstrap_vm.sh
conda activate nordic-asr

# List available resources without downloading them
python scripts/download_sprakbanken.py --list

# Selected Norwegian corpora
python scripts/download_sprakbanken.py \
  --datasets npsc nbsamtale nbtale nst \
  --download --jobs 4

# Validate a manifest
python scripts/validate_manifest.py data/manifests/train.jsonl
```

The first reproducible Norwegian training pipeline extracts only NPSC
segments, creates a session-level validation split, runs a distributed smoke
test, and then starts a two-GPU LoRA adaptation of NB-Whisper:

```bash
nohup scripts/run_npsc_training_pipeline.sh \
  > logs/npsc_training_pipeline.log 2>&1 &
```

The NB Tale test set is strictly excluded from this training run.

## Public and resumable data acquisition

All downloads are atomic and resumable. JSONL indexes retain the URL,
identifier, duration, and provenance without committing media files to Git.

```bash
# Sámi Parliament: four audio channels
python scripts/index_sami_parliament.py
python scripts/download_sami_parliament.py \
  --languages sme smj sma nob --jobs 3

# Sámi and Meänkieli radio from Sveriges Radio
python scripts/index_registered_media.py \
  --group sveriges_radio --download --jobs 3

# Explicitly registered NRK series in Kven and Sámi
python scripts/index_registered_media.py \
  --group nrk_series --download --jobs 2

# Video channels authorized by the configuration
python scripts/download_external_media.py \
  --sources ruijan_kaiku halti_kven samediggi nrk_sami_oahpahallit kven_seed

python scripts/acquisition_status.py

# Metadata for public videos from regional news outlets
python scripts/index_amedia_video.py
```

An isolated network failure does not stop an entire collection. Running the
same command again resumes incomplete files. Pages requiring an account,
geographic circumvention, or DRM bypass are skipped.

## Reproducible benchmarks

FLEURS and model revisions are pinned in `configs/benchmarks.yaml`.

```bash
python scripts/prepare_fleurs.py
bash scripts/run_initial_benchmarks.sh
```

To create a balanced dialect evaluation set:

```bash
python scripts/select_benchmark.py data/eval/nbtale12/test.jsonl \
  --group-by dialect --minutes-per-group 60 \
  --out data/eval/nbtale12/dialect_balanced.jsonl
```

Initial results on Norwegian FLEURS, with 357 segments and approximately
1.25 hours of audio:

| Model | WER | CER |
|---|---:|---:|
| NbAiLab/nb-whisper-large | 5.44% | 2.05% |
| openai/whisper-large-v3 | 7.76% | 2.39% |
| omniASR CTC 1B v2 | 13.24% | 3.52% |

Predictions and metrics are stored in `runs/baselines/`. Weights, checkpoints,
and data remain ignored by Git.

The detailed protocol, including cloud comparisons and per-dialect results, is
available in [`docs/BENCHMARK.md`](docs/BENCHMARK.md).

## Manifest contract

Each segment is represented by one JSON line:

```json
{"id":"source:segment","audio":"/abs/path.wav","text":"...","language":"sme","split":"train","duration":8.4,"speaker_id":"...","source":"..."}
```

Splits are made by speaker, program, or session, never randomly by segment.
Weak transcriptions are marked with `supervision="weak"` and are not used in
test sets.

## Release criteria

A model is ready for a pilot only when:

- WER and CER are reported separately for `nob`, `nno`, `sme`, and `fkv`;
- an out-of-domain, noisy, conversational test set is retained;
- hallucination rates on silence and out-of-language audio are measured;
- long-form inference is tested with VAD and timestamps;
- the result can be reproduced from the manifests and configuration.

## Repository limitations

The repository contains code and small benchmark outputs, never corpora,
cookies, tokens, SSH keys, or private weights. Each media item remains subject
to the rights and terms of its original source.
