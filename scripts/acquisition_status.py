#!/usr/bin/env python3
"""Report completion of indexed public-media downloads."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def human_bytes(value: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def progress(name: str, rows: list[dict], target_for: object) -> dict:
    complete = []
    total_bytes = 0
    for row in rows:
        target = target_for(row)
        if target.exists() and target.stat().st_size > 0:
            complete.append(row)
            total_bytes += target.stat().st_size
    return {
        "source": name,
        "files": len(complete),
        "expected": len(rows),
        "hours": round(sum(float(row.get("duration") or 0) for row in complete) / 3600, 2),
        "expected_hours": round(
            sum(float(row.get("duration") or 0) for row in rows) / 3600, 2
        ),
        "bytes": total_bytes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    results = []

    sami_index = root / "data/index/sami_parliament.jsonl"
    sami_rows = load_rows(sami_index)
    for language in ("sme", "smj", "sma", "nob"):
        rows = [row for row in sami_rows if row["language"] == language]
        results.append(
            progress(
                f"sami_parliament_{language}",
                rows,
                lambda row, language=language: (
                    root
                    / "data/raw/sami_parliament"
                    / language
                    / f"{row['id'].replace(':', '_')}.m4a"
                ),
            )
        )

    for index in sorted((root / "data/index").glob("*.jsonl")):
        if index == sami_index:
            continue
        rows = load_rows(index)
        if not rows:
            continue
        if all(row.get("source") == "nrk" for row in rows):
            results.append(
                progress(
                    index.stem,
                    rows,
                    lambda row: (
                        root
                        / "data/raw/external/nrk"
                        / row["series"]
                        / f"{row['program_id']}.m4a"
                    ),
                )
            )
        elif all(row.get("audio_url") and row.get("source") for row in rows):
            def direct_target(row: dict) -> Path:
                suffix = (
                    Path(urllib.parse.urlparse(row["audio_url"]).path).suffix
                    or ".audio"
                )
                return (
                    root
                    / "data/raw/external"
                    / row["source"]
                    / f"{row['id'].replace(':', '_')}{suffix}"
                )

            results.append(progress(index.stem, rows, direct_target))

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    print(f"{'source':30} {'files':>13} {'hours':>17} {'disk':>10}")
    for item in results:
        print(
            f"{item['source']:30} "
            f"{item['files']:>6}/{item['expected']:<6} "
            f"{item['hours']:>7.2f}/{item['expected_hours']:<7.2f} "
            f"{human_bytes(item['bytes']):>10}"
        )


if __name__ == "__main__":
    main()
