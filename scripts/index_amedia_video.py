#!/usr/bin/env python3
"""Index public Amedia video pages and their public player metadata."""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

USER_AGENT = "nordic-asr/0.1"
PLAYER_CONFIG = "https://ljsp.lwcdn.com/web/public/native/config/{player}/{media}"


def get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode(errors="replace")


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def attributes(tag: str) -> dict[str, str]:
    return {
        key.lower(): html.unescape(value)
        for key, value in re.findall(r'([\w-]+)="([^"]*)"', tag)
    }


def discover(site: str, url: str, dialect_hint: str) -> list[dict]:
    page = get_text(url)
    rows = []
    for match in re.finditer(
        r'<brick-teaser[^>]+data-teaser-type="video"[^>]*>', page, re.I
    ):
        teaser_attributes = attributes(match.group(0))
        end = page.find("</brick-teaser", match.end())
        body = page[match.end() : end]
        link = re.search(r'<a[^>]+href="([^"]+)"', body, re.I)
        title = re.search(r'itemprop="titleText">(.*?)</span>', body, re.I | re.S)
        if not link:
            continue
        rows.append(
            {
                "id": f"amedia:{teaser_attributes.get('data-id', len(rows))}",
                "site": site,
                "page_url": urllib.parse.urljoin(url, html.unescape(link.group(1))),
                "title": (
                    html.unescape(re.sub("<[^>]+>", " ", title.group(1))).strip()
                    if title
                    else ""
                ),
                "premium": teaser_attributes.get("data-premium") == "true",
                "language": "nob",
                "dialect": dialect_hint,
                "dialect_supervision": "geographic_hint",
                "source": f"amedia_{site}",
                "supervision": "unlabeled",
            }
        )
    return rows


def enrich(row: dict) -> dict:
    try:
        article = get_text(row["page_url"])
        player_tag = re.search(r"<brick-player[^>]*>", article, re.I)
        if not player_tag:
            return {**row, "index_error": "player_not_found"}
        player_attributes = attributes(player_tag.group(0))
        media_id = player_attributes.get("mediaid")
        player_id = player_attributes.get("playerid")
        if not media_id or not player_id:
            return {**row, "index_error": "player_ids_not_found"}
        config = get_json(PLAYER_CONFIG.format(player=player_id, media=media_id))
        subtitles = (config.get("subtitles") or {}).get("tracks") or []
        return {
            **row,
            "media_id": media_id,
            "player_id": player_id,
            "duration": float((config.get("metadata") or {}).get("duration") or 0),
            "audio_url": next(iter(config.get("src") or []), None),
            "subtitles": subtitles,
            "supervision": "automatic_caption" if subtitles else "unlabeled",
        }
    except Exception as error:
        return {**row, "index_error": f"{type(error).__name__}: {error}"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/amedia_sources.yaml")
    )
    parser.add_argument("--out", type=Path, default=Path("data/index/amedia_video.jsonl"))
    parser.add_argument("--sites", nargs="+")
    parser.add_argument("--include-premium-metadata", action="store_true")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))["sites"]
    selected = set(args.sites or config)
    rows = []
    for name, site in config.items():
        if name not in selected:
            continue
        discovered = discover(name, site["url"], site["dialect_hint"])
        rows.extend(
            row
            for row in discovered
            if args.include_premium_metadata or not row["premium"]
        )
        time.sleep(0.25)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(enrich, rows))
    rows.sort(key=lambda row: (row["site"], row["id"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "items": len(rows),
                "hours": round(
                    sum(float(row.get("duration") or 0) for row in rows) / 3600, 2
                ),
                "with_subtitles": sum(bool(row.get("subtitles")) for row in rows),
                "errors": sum(bool(row.get("index_error")) for row in rows),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
