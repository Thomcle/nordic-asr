#!/usr/bin/env python3
"""Download an explicitly selected set of public Amedia benchmark videos."""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("--ids", nargs="+", required=True)
    parser.add_argument("--out", type=Path, default=Path("data/eval/amedia_candidates"))
    parser.add_argument("--manifest-out", type=Path)
    args = parser.parse_args()

    wanted = set(args.ids)
    with args.index.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    rows = [row for row in rows if row["id"] in wanted]
    found = {row["id"] for row in rows}
    if missing := sorted(wanted - found):
        raise SystemExit(f"Unknown IDs: {', '.join(missing)}")

    args.out.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for row in rows:
        if row.get("premium"):
            print(f"skip premium {row['id']}", flush=True)
            continue
        stem = row["id"].replace(":", "_")
        audio = args.out / f"{stem}.flac"
        if not audio.exists():
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    row["audio_url"],
                    "-map",
                    "0:a:0",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-c:a",
                    "flac",
                    str(audio),
                ],
                check=True,
            )
        for number, track in enumerate(row.get("subtitles") or []):
            subtitle = args.out / f"{stem}.{track.get('lang', 'und')}.{number}.vtt"
            if not subtitle.exists():
                urllib.request.urlretrieve(track["src"], subtitle)
        manifest_rows.append(
            {
                **row,
                "audio": str(audio.resolve()),
                "text": "",
                "split": "test",
                "reference_status": "needs_human_review",
            }
        )
        print(audio, flush=True)
    manifest_out = args.manifest_out or args.out / "candidates.jsonl"
    with manifest_out.open("w", encoding="utf-8") as output:
        for row in manifest_rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(manifest_rows)} candidates to {manifest_out}")


if __name__ == "__main__":
    main()
