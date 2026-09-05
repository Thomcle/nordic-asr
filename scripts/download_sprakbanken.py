#!/usr/bin/env python3
"""Discover and download public Norwegian Language Bank archives."""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import re
import urllib.request
from pathlib import Path

CATALOGUE = {
    "npsc": "84",
    "ssc": "91",
    "nst": "54",
    "nbtale": "31",
    "nbsamtale": "85",
}


def discover(name: str) -> list[tuple[str, int]]:
    dataset_id = CATALOGUE[name]
    url = f"https://www.nb.no/SPRAKBANKEN/ressurskatalog/oai-nb-no-sbr-{dataset_id}/"
    request = urllib.request.Request(url, headers={"User-Agent": "nordic-asr/0.1"})
    page = urllib.request.urlopen(request, timeout=60).read().decode(errors="replace")
    links: list[str] = []
    for link in re.findall(r"""href=["']([^"']+)""", page, flags=re.IGNORECASE):
        link = html.unescape(link)
        if not any(ext in link.lower() for ext in (".tar.gz", ".tgz", ".zip")):
            continue
        if link.startswith("//"):
            link = "https:" + link
        elif link.startswith("/"):
            link = "https://www.nb.no" + link
        if link not in links:
            links.append(link)

    output = []
    for link in links:
        try:
            head = urllib.request.Request(
                link, method="HEAD", headers={"User-Agent": "nordic-asr/0.1"}
            )
            size = int(urllib.request.urlopen(head, timeout=60).headers.get("Content-Length") or 0)
        except Exception:
            size = 0
        output.append((link, size))
    return output


def selected(name: str, url: str) -> bool:
    """Avoid duplicated microphone channels in NST while keeping annotations."""

    filename = url.rsplit("/", 1)[-1].lower()
    if name != "nst":
        return True
    return "begge" in filename or "metadata" in filename or filename.startswith("adb_")


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    existing = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "nordic-asr/0.1"}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(url, headers=headers)
    mode = "ab" if existing else "wb"
    response = urllib.request.urlopen(request, timeout=300)
    if existing and getattr(response, "status", None) != 206:
        # The server ignored Range; restart instead of appending a second archive.
        mode = "wb"
    with response, partial.open(mode) as handle:
        while chunk := response.read(8 * 1024 * 1024):
            handle.write(chunk)
    partial.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", choices=CATALOGUE, default=list(CATALOGUE))
    parser.add_argument("--out", type=Path, default=Path("data/raw/spraakbanken"))
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()

    jobs: list[tuple[str, str, int]] = []
    for name in args.datasets:
        for url, size in discover(name):
            mark = "*" if selected(name, url) else " "
            print(f"{mark} {name:10s} {size / 2**30:8.2f} GiB  {url}", flush=True)
            if selected(name, url):
                jobs.append((name, url, size))

    total = sum(size for _, _, size in jobs)
    print(f"Selected: {len(jobs)} archives, {total / 2**30:.2f} GiB", flush=True)
    if args.list or not args.download:
        return

    def run(item: tuple[str, str, int]) -> str:
        name, url, _ = item
        target = args.out / name / url.rsplit("/", 1)[-1]
        if target.exists():
            return f"exists {target}"
        download(url, target)
        return f"done   {target}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for result in pool.map(run, jobs):
            print(result, flush=True)


if __name__ == "__main__":
    main()
