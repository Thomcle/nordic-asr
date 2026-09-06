#!/usr/bin/env python3
"""Create a deterministic duration-balanced evaluation subset."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def stable_rank(seed: int, item_id: str) -> str:
    return hashlib.sha256(f"{seed}:{item_id}".encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--group-by", default="dialect")
    parser.add_argument("--groups", nargs="+")
    parser.add_argument("--minutes-per-group", type=float, default=60)
    parser.add_argument("--max-minutes-per-speaker", type=float, default=5)
    parser.add_argument("--seed", type=int, default=20260906)
    args = parser.parse_args()

    grouped: dict[str, list[dict]] = defaultdict(list)
    with args.manifest.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            group = str(row.get(args.group_by) or "unknown")
            if args.groups and group not in args.groups:
                continue
            grouped[group].append(row)
    if not grouped:
        raise SystemExit("No matching rows")

    target = args.minutes_per_group * 60
    speaker_cap = args.max_minutes_per_speaker * 60
    selected = []
    summary = {}
    for group, rows in sorted(grouped.items()):
        rows.sort(key=lambda row: stable_rank(args.seed, str(row["id"])))
        seconds = 0.0
        by_speaker: dict[str, float] = defaultdict(float)
        chosen = []
        for row in rows:
            duration = float(row.get("duration") or 0)
            speaker = str(row.get("speaker_id") or row["id"])
            if by_speaker[speaker] + duration > speaker_cap:
                continue
            chosen.append(row)
            seconds += duration
            by_speaker[speaker] += duration
            if seconds >= target:
                break
        selected.extend(chosen)
        summary[group] = {
            "items": len(chosen),
            "minutes": round(seconds / 60, 2),
            "speakers": len(by_speaker),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as output:
        for row in selected:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
