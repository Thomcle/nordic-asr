#!/usr/bin/env python3
"""Evaluate a released OmniASR checkpoint on a JSONL manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

from nordic_asr.metrics import score_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--model", default="omniASR_CTC_1B_v2")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--group-by", default="language")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    with args.manifest.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    if args.limit:
        rows = rows[: args.limit]

    recognizer = ASRInferencePipeline(model_card=args.model)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    scored_rows = []
    with args.out.open("w", encoding="utf-8") as output:
        for start in range(0, len(rows), args.batch_size):
            batch = rows[start : start + args.batch_size]
            predictions = recognizer.transcribe(
                [row["audio"] for row in batch],
                batch_size=args.batch_size,
            )
            for row, hypothesis in zip(batch, predictions):
                scored = {
                    "id": row["id"],
                    "language": row["language"],
                    "dialect": row.get("dialect"),
                    "source": row.get("source"),
                    "speaker_id": row.get("speaker_id"),
                    "reference": row.get("text", ""),
                    "hypothesis": hypothesis,
                }
                scored_rows.append(scored)
                output.write(json.dumps(scored, ensure_ascii=False) + "\n")
            print(f"{min(start + args.batch_size, len(rows))}/{len(rows)}", flush=True)

    metrics_path = args.out.with_suffix(".metrics.json")
    evaluated_rows = [row for row in scored_rows if row["reference"].strip()]
    metrics = (
        score_rows(evaluated_rows, group_by=args.group_by)
        if evaluated_rows
        else {
            "warning": "No human references; predictions are unscored.",
            "utterances": len(scored_rows),
        }
    )
    metrics_path.write_text(
        json.dumps(
            metrics,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(metrics_path)


if __name__ == "__main__":
    main()
