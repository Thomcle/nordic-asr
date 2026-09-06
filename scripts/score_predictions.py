#!/usr/bin/env python3
"""Score a JSONL file containing language, reference and hypothesis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nordic_asr.metrics import bootstrap_scores, score_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--group-by", default="language")
    parser.add_argument("--cluster-by", default="speaker_id")
    parser.add_argument("--bootstrap", type=int, default=0)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    with args.predictions.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    scores = score_rows(rows, group_by=args.group_by)
    if args.bootstrap:
        scores["confidence_95"] = bootstrap_scores(
            rows,
            group_by=args.group_by,
            cluster_by=args.cluster_by,
            samples=args.bootstrap,
            seed=args.seed,
        )
    rendered = json.dumps(scores, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
