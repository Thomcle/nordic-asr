#!/usr/bin/env python3
"""Build an intake manifest from yt-dlp/Vimeo downloads."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

AUDIO_EXTENSIONS = (".webm", ".m4a", ".opus", ".mp3", ".ogg", ".wav")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("data/raw/external"))
    parser.add_argument(
        "--config", type=Path, default=Path("configs/external_sources.yaml")
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    source_config = {**config.get("youtube", {}), **config.get("vimeo", {})}
    rows = []
    for source_dir in sorted(path for path in args.root.iterdir() if path.is_dir()):
        candidates = source_config.get(source_dir.name, {}).get("candidate_languages", [])
        for info_path in source_dir.glob("*.info.json"):
            info = json.loads(info_path.read_text(encoding="utf-8"))
            media_id = str(info.get("id") or "")
            duration = float(info.get("duration") or 0)
            if not media_id or duration <= 0:
                continue
            audio = next(
                (
                    source_dir / f"{media_id}{extension}"
                    for extension in AUDIO_EXTENSIONS
                    if (source_dir / f"{media_id}{extension}").exists()
                ),
                None,
            )
            if audio is None:
                continue
            subtitles = sorted(str(path.resolve()) for path in source_dir.glob(f"{media_id}*.vtt"))
            rows.append(
                {
                    "id": f"{source_dir.name}:{media_id}",
                    "audio": str(audio.resolve()),
                    "duration": duration,
                    "title": info.get("title"),
                    "channel": info.get("channel") or info.get("uploader"),
                    "source": source_dir.name,
                    "webpage_url": info.get("webpage_url"),
                    "candidate_languages": candidates,
                    "detected_language": info.get("language"),
                    "subtitle_files": subtitles,
                    "supervision": "candidate",
                }
            )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} items to {args.out}")


if __name__ == "__main__":
    main()

