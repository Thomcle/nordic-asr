#!/usr/bin/env python3
"""Score a JSONL file containing language, reference and hypothesis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nordic_asr.metrics import score_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with args.predictions.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    scores = score_rows(rows)
    rendered = json.dumps(scores, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

