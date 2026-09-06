#!/usr/bin/env python3
"""Resumably download direct audio URLs from a JSONL index."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path


def download_once(row: dict, root: Path) -> str:
    suffix = Path(urllib.parse.urlparse(row["audio_url"]).path).suffix or ".audio"
    filename = row["id"].replace(":", "_") + suffix
    target = root / row["source"] / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return f"exists {target}"
    partial = target.with_suffix(target.suffix + ".part")
    existing = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "nordic-asr/0.1"}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(row["audio_url"], headers=headers)
    response = urllib.request.urlopen(request, timeout=300)
    mode = "ab" if existing and getattr(response, "status", None) == 206 else "wb"
    with response, partial.open(mode) as output:
        while chunk := response.read(8 * 1024 * 1024):
            output.write(chunk)
    partial.replace(target)
    return f"done {target}"


def download(row: dict, root: Path, retries: int) -> str:
    for attempt in range(retries + 1):
        try:
            return download_once(row, root)
        except Exception as error:
            if attempt == retries:
                return f"error {row['id']}: {type(error).__name__}: {error}"
            time.sleep(min(60, 2**attempt) + random.random())
    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/raw/external"))
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--retries", type=int, default=8)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    with args.index.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    if args.limit is not None:
        rows = rows[: args.limit]
    print(
        f"Selected {len(rows)} files, "
        f"{sum(float(row.get('duration') or 0) for row in rows) / 3600:.2f} h",
        flush=True,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for result in pool.map(
            lambda row: download(row, args.out, args.retries),
            rows,
        ):
            print(result, flush=True)


if __name__ == "__main__":
    main()
