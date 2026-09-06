#!/usr/bin/env python3
"""Download allow-listed YouTube/Vimeo audio, subtitles and metadata."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import yaml


def run_source(name: str, urls: list[str], output_root: Path, yt_dlp: str) -> None:
    destination = output_root / name
    destination.mkdir(parents=True, exist_ok=True)
    command = [
        yt_dlp,
        "--ignore-errors",
        "--no-overwrites",
        "--continue",
        "--retries",
        "10",
        "--fragment-retries",
        "10",
        "--concurrent-fragments",
        "3",
        "--sleep-requests",
        "0.5",
        "--js-runtimes",
        "node",
        "--match-filter",
        "duration > 5 & duration < 14400",
        "--download-archive",
        str(destination / "downloaded.txt"),
        "--write-info-json",
        "--write-subs",
        # This first pass intentionally downloads only human-created tracks.
        "--sub-langs",
        "no,nb,nn,se,sme,smj,sma,smn,sms,fkv,fi",
        "--sub-format",
        "vtt",
        "-f",
        "bestaudio/best",
        "-o",
        str(destination / "%(id)s.%(ext)s"),
        *urls,
    ]
    result = subprocess.run(command, check=False)
    if result.returncode:
        print(f"Warning: yt-dlp reported partial failures for {name}", flush=True)
    auto_command = [
        yt_dlp,
        "--ignore-errors",
        "--skip-download",
        "--write-auto-subs",
        "--sub-langs",
        ".*-orig",
        "--sub-format",
        "vtt",
        "--js-runtimes",
        "node",
        "-o",
        str(destination / "%(id)s.%(ext)s"),
        *urls,
    ]
    result = subprocess.run(auto_command, check=False)
    if result.returncode:
        print(f"Warning: automatic-caption pass had partial failures for {name}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/external_sources.yaml")
    )
    parser.add_argument("--sources", nargs="+", required=True)
    parser.add_argument(
        "--out", type=Path, default=Path("data/raw/external")
    )
    parser.add_argument("--yt-dlp", default="yt-dlp")
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    available = {**config.get("youtube", {}), **config.get("vimeo", {})}
    for name in args.sources:
        if name not in available:
            raise SystemExit(f"Unknown source {name!r}; choose from {sorted(available)}")
        source = available[name]
        urls = source.get("urls") or [source["url"]]
        print(f"Downloading {name}: {len(urls)} URL(s)", flush=True)
        run_source(name, urls, args.out, args.yt_dlp)


if __name__ == "__main__":
    main()
