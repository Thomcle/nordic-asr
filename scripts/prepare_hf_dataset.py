#!/usr/bin/env python3
"""Materialize a Hugging Face speech dataset into audio files and a manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from datasets import Audio, load_dataset


def audio_array(value: object) -> tuple[np.ndarray, int]:
    if isinstance(value, dict):
        return np.asarray(value["array"], dtype=np.float32), int(value["sampling_rate"])
    samples = value.get_all_samples()
    array = samples.data
    if hasattr(array, "numpy"):
        array = array.numpy()
    array = np.asarray(array, dtype=np.float32).squeeze()
    return array, int(samples.sample_rate)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("--config")
    parser.add_argument("--split", default="test")
    parser.add_argument("--language", required=True)
    parser.add_argument("--source")
    parser.add_argument("--audio-column", default="audio")
    parser.add_argument("--text-column", default="transcription")
    parser.add_argument("--id-column", default="id")
    parser.add_argument("--speaker-column")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--streaming", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    dataset = load_dataset(
        args.dataset,
        args.config,
        split=args.split,
        streaming=args.streaming,
    )
    try:
        dataset = dataset.cast_column(args.audio_column, Audio(sampling_rate=16000))
    except AttributeError:
        pass

    source = args.source or args.dataset.replace("/", "_")
    audio_dir = args.out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / f"{args.split}.jsonl"
    count = 0
    seconds = 0.0
    with manifest_path.open("w", encoding="utf-8") as manifest:
        for index, row in enumerate(dataset):
            if args.limit is not None and index >= args.limit:
                break
            samples, sample_rate = audio_array(row[args.audio_column])
            if samples.ndim > 1:
                samples = samples.mean(axis=0)
            original_id = str(row.get(args.id_column, index)).replace("/", "_")
            # Some datasets (including FLEURS) reuse their `id` field, so the
            # row index is part of the storage and manifest identity.
            item_id = f"{index:09d}_{original_id}"
            path = (audio_dir / f"{item_id}.flac").resolve()
            sf.write(path, samples, sample_rate, format="FLAC")
            duration = len(samples) / sample_rate
            output = {
                "id": f"{source}:{args.split}:{item_id}",
                "audio": str(path),
                "text": str(row[args.text_column]),
                "language": args.language,
                "split": args.split,
                "duration": duration,
                "speaker_id": (
                    str(row.get(args.speaker_column, "")) if args.speaker_column else ""
                ),
                "source": source,
                "supervision": "manual",
                "original_id": original_id,
            }
            manifest.write(json.dumps(output, ensure_ascii=False) + "\n")
            count += 1
            seconds += duration
    print(f"Wrote {count} segments ({seconds / 3600:.2f} h) to {manifest_path}")


if __name__ == "__main__":
    main()
