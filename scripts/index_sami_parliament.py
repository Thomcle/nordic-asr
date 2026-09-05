#!/usr/bin/env python3
"""Index public Sámi Parliament interpretation channels exposed by KommuneTV."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

BASE_URL = "https://sametinget.kommunetv.no"
CHANNEL_LANGUAGES = {
    "Norsk": "nob",
    "Davvisámegiella": "sme",
    "Julevsámegiella": "smj",
    "Åarjelsaemien gïele": "sma",
}


def get_json(path: str) -> object:
    request = urllib.request.Request(
        BASE_URL + path,
        headers={"Accept": "application/json", "User-Agent": "nordic-asr/0.1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def duration_from_url(url: str, fallback: float) -> float:
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    milliseconds = query.get("wowzaplayduration", [None])[0]
    return float(milliseconds) / 1000 if milliseconds else fallback


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("data/index/sami_parliament.jsonl"))
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args()

    first = get_json(f"/api/search?type=Archive&page=1&pageSize={args.page_size}")
    total = int(first["total"])
    meetings = list(first["data"])
    for page in range(2, (total + args.page_size - 1) // args.page_size + 1):
        response = get_json(
            f"/api/search?type=Archive&page={page}&pageSize={args.page_size}"
        )
        meetings.extend(response["data"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    hours: dict[str, float] = defaultdict(float)
    rows = 0
    with args.out.open("w", encoding="utf-8") as output:
        for meeting in meetings:
            playlists = get_json(
                f"/api/streams/playlists?streamType=1&id={meeting['id']}"
            )
            for channel in playlists:
                language = CHANNEL_LANGUAGES.get(channel["cameraName"])
                if language is None:
                    continue
                for item_index, item in enumerate(channel["playlist"]):
                    duration = duration_from_url(item["file"], float(channel["duration"]))
                    row = {
                        "id": (
                            f"sami_parliament:{meeting['id']}:{channel['cameraId']}:"
                            f"{item.get('bookmarkId', item_index)}"
                        ),
                        "meeting_id": meeting["id"],
                        "date": meeting["date"],
                        "title": item.get("title") or meeting["title"],
                        "language": language,
                        "channel": channel["cameraName"],
                        "duration": duration,
                        "audio_url": item["file"],
                        "source": "sami_parliament",
                        "supervision": "unlabeled",
                    }
                    output.write(json.dumps(row, ensure_ascii=False) + "\n")
                    hours[language] += duration / 3600
                    rows += 1

    print(json.dumps({"meetings": len(meetings), "streams": rows, "hours": hours}, indent=2))


if __name__ == "__main__":
    main()

