#!/usr/bin/env python3
"""Run a Hugging Face ASR model on a manifest and save scored predictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from transformers import pipeline

from nordic_asr.metrics import score_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--chunk-seconds", type=float, default=30)
    parser.add_argument("--language", help="Whisper language name/code; omit for CTC")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    with args.manifest.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    if args.limit:
        rows = rows[: args.limit]

    recognizer = pipeline(
        "automatic-speech-recognition",
        model=args.model,
        device=0 if torch.cuda.is_available() else -1,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        chunk_length_s=args.chunk_seconds,
    )
    options = {}
    if args.language:
        options["generate_kwargs"] = {"language": args.language, "task": "transcribe"}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    scored_rows = []
    with args.out.open("w", encoding="utf-8") as output:
        for start in range(0, len(rows), args.batch_size):
            batch = rows[start : start + args.batch_size]
            predictions = recognizer(
                [row["audio"] for row in batch],
                batch_size=args.batch_size,
                **options,
            )
            for row, prediction in zip(batch, predictions):
                scored = {
                    "id": row["id"],
                    "language": row["language"],
                    "reference": row["text"],
                    "hypothesis": prediction["text"],
                }
                scored_rows.append(scored)
                output.write(json.dumps(scored, ensure_ascii=False) + "\n")
            print(f"{min(start + args.batch_size, len(rows))}/{len(rows)}", flush=True)

    metrics_path = args.out.with_suffix(".metrics.json")
    metrics_path.write_text(
        json.dumps(score_rows(scored_rows), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(metrics_path)


if __name__ == "__main__":
    main()

