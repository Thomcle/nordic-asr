#!/usr/bin/env python3
"""Download indexed Sámi Parliament HLS audio without generation loss."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
from pathlib import Path


def download(row: dict, root: Path) -> str:
    target = root / row["language"] / f"{row['id'].replace(':', '_')}.m4a"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return f"exists {target}"
    partial = target.with_suffix(".m4a.part")
    command = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        row["audio_url"],
        "-map",
        "0:a:0",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        "-f",
        "mp4",
        str(partial),
    ]
    subprocess.run(command, check=True)
    partial.replace(target)
    return f"done {target}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--index", type=Path, default=Path("data/index/sami_parliament.jsonl")
    )
    parser.add_argument(
        "--out", type=Path, default=Path("data/raw/sami_parliament")
    )
    parser.add_argument("--languages", nargs="+", default=["sme"])
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    with args.index.open(encoding="utf-8") as handle:
        rows = [
            json.loads(line)
            for line in handle
            if json.loads(line)["language"] in args.languages
        ]
    if args.limit is not None:
        rows = rows[: args.limit]
    print(
        f"Selected {len(rows)} streams, "
        f"{sum(float(row['duration']) for row in rows) / 3600:.2f} h",
        flush=True,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for result in pool.map(lambda row: download(row, args.out), rows):
            print(result, flush=True)


if __name__ == "__main__":
    main()

