#!/usr/bin/env python3
"""Index downloadable episodes from the public Sveriges Radio API."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.sr.se/api/v2/episodes/index"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-id", type=int, required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--candidate-languages", nargs="+")
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    query = urllib.parse.urlencode(
        {
            "programid": args.program_id,
            "format": "json",
            "pagination": "false",
        }
    )
    request = urllib.request.Request(
        f"{API}?{query}",
        headers={"Accept": "application/json", "User-Agent": "nordic-asr/0.1"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        episodes = json.load(response)["episodes"]

    rows = []
    for episode in episodes:
        audio = episode.get("downloadpodfile") or episode.get("listenpodfile")
        if not audio:
            broadcast_files = (episode.get("broadcast") or {}).get("broadcastfiles") or []
            audio = broadcast_files[0] if broadcast_files else None
        if not audio or not audio.get("url"):
            continue
        rows.append(
            {
                "id": f"{args.source}:{episode['id']}",
                "episode_id": episode["id"],
                "title": episode.get("title"),
                "description": episode.get("description"),
                "language": args.language,
                "candidate_languages": args.candidate_languages or [args.language],
                "duration": float(audio.get("duration") or 0),
                "bytes": int(audio.get("filesizeinbytes") or 0),
                "audio_url": audio["url"],
                "webpage_url": episode.get("url"),
                "source": args.source,
                "supervision": "unlabeled",
            }
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "episodes": len(rows),
                "hours": round(sum(row["duration"] for row in rows) / 3600, 2),
                "gigabytes": round(sum(row["bytes"] for row in rows) / 1e9, 2),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
