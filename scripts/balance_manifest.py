#!/usr/bin/env python3
"""Create a deterministic temperature-sampled multilingual training manifest."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--samples", type=int, required=True)
    parser.add_argument("--temperature", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=20260905)
    args = parser.parse_args()

    groups: dict[str, list[dict]] = defaultdict(list)
    seen: set[str] = set()
    for path in args.inputs:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if row["id"] in seen:
                    continue
                seen.add(row["id"])
                groups[row["language"]].append(row)
    if not groups:
        raise SystemExit("No examples found")

    languages = sorted(groups)
    probabilities = [len(groups[language]) ** args.temperature for language in languages]
    rng = random.Random(args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = defaultdict(int)
    with args.out.open("w", encoding="utf-8") as output:
        for index in range(args.samples):
            language = rng.choices(languages, weights=probabilities, k=1)[0]
            row = dict(rng.choice(groups[language]))
            row["sample_index"] = index
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            counts[language] += 1
    print(json.dumps({"samples": args.samples, "by_language": counts}, indent=2))


if __name__ == "__main__":
    main()

