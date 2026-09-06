#!/usr/bin/env python3
"""Create a human-review sheet by joining a manifest with draft predictions."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifest = {row["id"]: row for row in load(args.manifest)}
    predictions = {row["id"]: row for row in load(args.predictions)}
    fields = [
        "id",
        "audio",
        "language",
        "dialect",
        "source",
        "title",
        "draft_transcript",
        "reference_transcript",
        "reviewer",
        "approved",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for item_id, row in manifest.items():
            prediction = predictions.get(item_id, {})
            writer.writerow(
                {
                    "id": item_id,
                    "audio": row["audio"],
                    "language": row.get("language"),
                    "dialect": row.get("dialect"),
                    "source": row.get("source"),
                    "title": row.get("title"),
                    "draft_transcript": prediction.get("hypothesis", ""),
                    "reference_transcript": row.get("text", ""),
                    "reviewer": "",
                    "approved": "false",
                }
            )
    print(f"Wrote {len(manifest)} rows to {args.out}")


if __name__ == "__main__":
    main()
