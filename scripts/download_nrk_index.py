#!/usr/bin/env python3
"""Download audio and subtitle tracks from an NRK index."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import subprocess
import time
import urllib.request
from pathlib import Path


def download_row_once(row: dict, root: Path) -> str:
    program_id = row["program_id"]
    target_dir = root / row["series"]
    target_dir.mkdir(parents=True, exist_ok=True)
    audio = target_dir / f"{program_id}.m4a"
    if not audio.exists():
        partial = audio.with_suffix(".m4a.part")
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
        partial.replace(audio)
    for subtitle in row.get("subtitles", []):
        language = subtitle.get("language") or subtitle.get("type") or "und"
        path = target_dir / f"{program_id}.{language}.vtt"
        if not path.exists() and subtitle.get("webVtt"):
            urllib.request.urlretrieve(subtitle["webVtt"], path)
    (target_dir / f"{program_id}.info.json").write_text(
        json.dumps(row, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return str(audio)


def download_row(row: dict, root: Path, retries: int) -> str:
    for attempt in range(retries + 1):
        try:
            return download_row_once(row, root)
        except Exception as error:
            if attempt == retries:
                return f"error {row['id']}: {type(error).__name__}: {error}"
            time.sleep(min(60, 2**attempt) + random.random())
    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/raw/external/nrk"))
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--retries", type=int, default=5)
    args = parser.parse_args()

    with args.index.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for result in pool.map(
            lambda row: download_row(row, args.out, args.retries),
            rows,
        ):
            print(result, flush=True)


if __name__ == "__main__":
    main()
