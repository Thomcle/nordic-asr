#!/usr/bin/env python3
"""Build train/dev manifests from extracted NPSC sentence metadata and audio."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

LANGUAGES = {
    "nb": "nob",
    "nb-no": "nob",
    "no": "nob",
    "nn": "nno",
    "nn-no": "nno",
}


def normalized_split(value: str, session: str, validation_percent: float) -> str:
    value = value.strip().lower()
    if value in {"dev", "development", "valid", "validation"}:
        return "validation"
    if value == "test":
        return "test"
    if value == "train" and validation_percent:
        bucket = int(hashlib.sha256(session.encode()).hexdigest()[:8], 16) % 10_000
        if bucket < round(validation_percent * 100):
            return "validation"
    return "train"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="Directory containing extracted NPSC data")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--validation-percent",
        type=float,
        default=5.0,
        help="Move this percentage of train sessions to validation (default: 5).",
    )
    parser.add_argument("--min-seconds", type=float, default=0.5)
    parser.add_argument("--max-seconds", type=float, default=30.0)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    handles = {
        split: (args.out / f"npsc_{split}.jsonl").open("w", encoding="utf-8")
        for split in ("train", "validation", "test")
    }
    counts: Counter[tuple[str, str]] = Counter()
    hours: dict[tuple[str, str], float] = defaultdict(float)
    skipped: Counter[str] = Counter()
    seen: set[str] = set()
    try:
        metadata_files = sorted(args.root.rglob("*_sentence_data.json"))
        if not metadata_files:
            raise SystemExit(f"No NPSC metadata found below {args.root}")
        for metadata_path in metadata_files:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
            session = str(metadata.get("meeting_date") or metadata_path.parent.name)
            split = normalized_split(
                str(metadata.get("data_split") or "train"),
                session,
                args.validation_percent,
            )
            for sentence in metadata.get("sentences", []):
                language_code = str(sentence.get("sentence_language_code") or "").lower()
                language = LANGUAGES.get(language_code)
                if not language:
                    skipped["language"] += 1
                    continue
                text = str(
                    sentence.get("sentence_text")
                    or sentence.get("nonverbatim_text")
                    or ""
                ).strip()
                if not text:
                    skipped["empty_text"] += 1
                    continue
                audio_name = str(sentence.get("audio_file") or "")
                audio = (metadata_path.parent / "audio" / audio_name).resolve()
                if not audio.is_file():
                    skipped["missing_audio"] += 1
                    continue
                start = float(sentence.get("start_time") or 0)
                end = float(sentence.get("end_time") or 0)
                duration = (end - start) / 1000
                if not args.min_seconds <= duration <= args.max_seconds:
                    skipped["duration"] += 1
                    continue
                sentence_id = str(sentence.get("sentence_id") or audio.stem)
                item_id = f"npsc:{session}:{sentence_id}"
                if item_id in seen:
                    skipped["duplicate"] += 1
                    continue
                seen.add(item_id)
                row = {
                    "id": item_id,
                    "audio": str(audio),
                    "text": text,
                    "language": language,
                    "split": split,
                    "duration": duration,
                    "speaker_id": str(sentence.get("speaker_id") or ""),
                    "dialect": str(sentence.get("speaker_dialect") or ""),
                    "source": "npsc_v2",
                    "supervision": "manual",
                    "session_id": session,
                    "gender": str(sentence.get("speaker_gender") or ""),
                }
                handles[split].write(json.dumps(row, ensure_ascii=False) + "\n")
                counts[(split, language)] += 1
                hours[(split, language)] += duration / 3600
    finally:
        for handle in handles.values():
            handle.close()

    for key in sorted(counts):
        print(f"{key}: {counts[key]} segments, {hours[key]:.2f} h")
    print(f"Skipped: {dict(skipped)}")


if __name__ == "__main__":
    main()
