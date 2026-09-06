#!/usr/bin/env python3
"""Summarize downloaded media metadata and available caption tracks."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("data/raw/external"))
    args = parser.parse_args()

    by_source: dict[str, dict] = {}
    for source_dir in sorted(path for path in args.root.iterdir() if path.is_dir()):
        infos = []
        for path in source_dir.glob("*.info.json"):
            try:
                infos.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        manual = Counter()
        automatic_original = Counter()
        duration = 0.0
        for info in infos:
            duration += float(info.get("duration") or 0)
            manual.update((info.get("subtitles") or {}).keys())
            automatic_original.update(
                key for key in (info.get("automatic_captions") or {}) if key.endswith("-orig")
            )
        by_source[source_dir.name] = {
            "items": len(infos),
            "hours": round(duration / 3600, 2),
            "manual_subtitles": dict(manual),
            "automatic_original": dict(automatic_original),
        }
    print(json.dumps(by_source, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

