#!/usr/bin/env python3
"""Index an NRK series using the public playback API."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://psapi.nrk.no"


def get_json(path: str, retries: int = 4) -> dict:
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            API + path,
            headers={"Accept": "application/json", "User-Agent": "nordic-asr/0.1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except (OSError, urllib.error.HTTPError) as error:
            if attempt == retries:
                raise error
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--series", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    series = get_json(f"/tv/catalog/series/{args.series}")
    season_links = series["_links"]["seasons"]
    rows = []
    skipped = 0
    for season_link in season_links:
        try:
            season = get_json(season_link["href"])
        except Exception as error:
            print(f"Warning: failed season {season_link['href']}: {error}", flush=True)
            skipped += 1
            continue
        embedded = season.get("_embedded") or {}
        episodes = embedded.get("episodes") or embedded.get("instalments") or []
        for episode in episodes:
            program_id = episode["prfId"]
            try:
                playback = get_json(f"/playback/manifest/program/{program_id}")
            except Exception as error:
                print(f"Warning: failed program {program_id}: {error}", flush=True)
                skipped += 1
                continue
            playable = playback.get("playable") or {}
            assets = playable.get("assets") or []
            if not assets:
                skipped += 1
                continue
            subtitles = playable.get("subtitles") or []
            rows.append(
                {
                    "id": f"nrk:{program_id}",
                    "program_id": program_id,
                    "series": args.series,
                    "season": (
                        season.get("sequenceNumber")
                        or season_link.get("name")
                        or season_link.get("title")
                    ),
                    "episode": episode.get("sequenceNumber"),
                    "title": episode["titles"]["title"],
                    "description": episode["titles"].get("subtitle"),
                    "language": args.language,
                    "duration": float(episode.get("durationInSeconds") or 0),
                    "audio_url": assets[0]["url"],
                    "subtitles": subtitles,
                    "source": "nrk",
                    "supervision": (
                        "translation"
                        if any("translated" in item.get("webVtt", "") for item in subtitles)
                        else "unknown"
                    ),
                }
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "series": args.series,
                "episodes": len(rows),
                "hours": round(sum(row["duration"] for row in rows) / 3600, 2),
                "skipped_unavailable": skipped,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
