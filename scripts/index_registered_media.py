#!/usr/bin/env python3
"""Index and optionally download all registered public radio/TV sources."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def run(command: list[str]) -> bool:
    print("+ " + " ".join(command), flush=True)
    return subprocess.run(command, check=False).returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/acquisition.yaml")
    )
    parser.add_argument(
        "--group", choices=["all", "sveriges_radio", "nrk_series"], default="all"
    )
    parser.add_argument("--sources", nargs="+")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--jobs", type=int, default=3)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    groups = (
        ["sveriges_radio", "nrk_series"] if args.group == "all" else [args.group]
    )
    selected = set(args.sources or [])
    failures = []

    for group in groups:
        for name, source in config.get(group, {}).items():
            if selected and name not in selected:
                continue
            index = Path("data/index") / f"{name}.jsonl"
            if group == "sveriges_radio":
                command = [
                    sys.executable,
                    "scripts/index_sveriges_radio.py",
                    "--program-id",
                    str(source["program_id"]),
                    "--language",
                    source["language"],
                    "--candidate-languages",
                    *source["candidate_languages"],
                    "--source",
                    name,
                    "--out",
                    str(index),
                ]
                downloader = [
                    sys.executable,
                    "scripts/download_url_index.py",
                    str(index),
                    "--jobs",
                    str(args.jobs),
                ]
            else:
                command = [
                    sys.executable,
                    "scripts/index_nrk_series.py",
                    "--series",
                    source["slug"],
                    "--language",
                    source["language"],
                    "--out",
                    str(index),
                ]
                downloader = [
                    sys.executable,
                    "scripts/download_nrk_index.py",
                    str(index),
                    "--jobs",
                    str(args.jobs),
                ]
            if not run(command):
                failures.append(f"{name}: index")
                continue
            if args.download and not run(downloader):
                failures.append(f"{name}: download")

    if failures:
        raise SystemExit("Failed tasks: " + ", ".join(failures))


if __name__ == "__main__":
    main()
