#!/usr/bin/env python3
"""Validate an ASR JSONL manifest and report its composition."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

REQUIRED = {"id", "audio", "text", "language", "split", "duration", "source"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--check-audio", action="store_true")
    args = parser.parse_args()

    ids: set[str] = set()
    counts: Counter[tuple[str, str, str]] = Counter()
    hours: dict[tuple[str, str, str], float] = defaultdict(float)
    errors: list[str] = []

    with args.manifest.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            missing = REQUIRED - row.keys()
            if missing:
                errors.append(f"line {line_number}: missing {sorted(missing)}")
                continue
            if row["id"] in ids:
                errors.append(f"line {line_number}: duplicate id {row['id']}")
            ids.add(row["id"])
            duration = float(row["duration"])
            if not 0.0 < duration <= 40.0:
                errors.append(f"line {line_number}: invalid duration {duration}")
            if not str(row["text"]).strip():
                errors.append(f"line {line_number}: empty text")
            if args.check_audio and not Path(row["audio"]).is_file():
                errors.append(f"line {line_number}: missing audio {row['audio']}")
            key = (row["language"], row["split"], row["source"])
            counts[key] += 1
            hours[key] += duration / 3600

    for key in sorted(counts):
        print(f"{key}: {counts[key]:8d} segments, {hours[key]:9.2f} h")
    print(f"Total: {len(ids)} unique segments")
    if errors:
        for error in errors[:100]:
            print("ERROR", error)
        raise SystemExit(f"{len(errors)} validation error(s)")


if __name__ == "__main__":
    main()

