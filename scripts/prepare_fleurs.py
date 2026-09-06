#!/usr/bin/env python3
"""Materialize a pinned FLEURS split as the project's JSONL manifest format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import soundfile as sf
from datasets import load_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", default="nb_no")
    parser.add_argument("--split", default="test")
    parser.add_argument("--language", default="nob")
    parser.add_argument(
        "--revision", default="70bb2e84b976b7e960aa89f1c648e09c59f894dd"
    )
    parser.add_argument("--out", type=Path, default=Path("data/eval/fleurs_nb"))
    args = parser.parse_args()

    dataset = load_dataset(
        "google/fleurs",
        args.subset,
        split=args.split,
        revision=args.revision,
    )
    audio_dir = args.out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    manifest = args.out / f"{args.split}.jsonl"
    with manifest.open("w", encoding="utf-8") as output:
        for index, row in enumerate(dataset):
            audio = row["audio"]
            path = audio_dir / f"{index:06d}.wav"
            sf.write(path, audio["array"], audio["sampling_rate"], subtype="PCM_16")
            output.write(
                json.dumps(
                    {
                        "id": f"fleurs:{args.subset}:{args.split}:{index}",
                        "audio": str(path.resolve()),
                        "text": row["transcription"],
                        "language": args.language,
                        "split": args.split,
                        "duration": len(audio["array"]) / audio["sampling_rate"],
                        "speaker_id": str(row.get("speaker_id") or ""),
                        "source": "google_fleurs",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"Wrote {len(dataset)} rows to {manifest}")


if __name__ == "__main__":
    main()
