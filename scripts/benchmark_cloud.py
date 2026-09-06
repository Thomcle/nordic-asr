#!/usr/bin/env python3
"""Run a small, resumable and auditable benchmark against cloud ASR APIs."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from nordic_asr.metrics import bootstrap_scores, score_rows
from nordic_asr.providers import PROVIDERS


def safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in value)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def select_rows(rows: list[dict], max_minutes: float | None) -> list[dict]:
    selected = []
    seconds = 0.0
    limit = max_minutes * 60 if max_minutes is not None else None
    for row in rows:
        duration = float(row.get("duration") or 0)
        if limit is not None and selected and seconds + duration > limit:
            continue
        selected.append(row)
        seconds += duration
        if limit is not None and seconds >= limit:
            break
    return selected


def write_metrics(
    path: Path,
    provider: str,
    rows: list[dict],
    metadata_by_id: dict[str, dict],
) -> None:
    for row in rows:
        metadata = metadata_by_id.get(str(row.get("id")), {})
        row.setdefault("speaker_id", metadata.get("speaker_id"))
    successful = [
        row for row in rows if row.get("status") == "ok" and row.get("reference")
    ]
    result = {
        "provider": provider,
        "successful": len(successful),
        "failed": sum(row.get("status") == "error" for row in rows),
        "audio_minutes": round(
            sum(float(row.get("duration") or 0) for row in successful) / 60, 3
        ),
    }
    if successful:
        result["by_language"] = score_rows(successful, group_by="language")
        result["by_language_confidence_95"] = bootstrap_scores(
            successful,
            group_by="language",
            samples=1000,
        )
        if any(row.get("dialect") for row in successful):
            result["by_dialect"] = score_rows(successful, group_by="dialect")
            result["by_dialect_confidence_95"] = bootstrap_scores(
                successful,
                group_by="dialect",
                samples=1000,
            )
        latencies = [float(row["latency_seconds"]) for row in successful]
        result["mean_latency_seconds"] = sum(latencies) / len(latencies)
        result["total_latency_seconds"] = sum(latencies)
        audio_seconds = sum(float(row.get("duration") or 0) for row in successful)
        result["realtime_factor"] = (
            sum(latencies) / audio_seconds if audio_seconds else None
        )
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--providers", nargs="+", choices=sorted(PROVIDERS), required=True
    )
    parser.add_argument("--out", type=Path, default=Path("runs/cloud"))
    parser.add_argument("--max-minutes", type=float, default=25)
    parser.add_argument("--languages", nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(args.manifest)
    if args.languages:
        rows = [row for row in rows if row.get("language") in args.languages]
    rows = select_rows(rows, args.max_minutes)
    metadata_by_id = {str(row["id"]): row for row in rows}
    missing = [
        str(row["audio"]) for row in rows if not Path(row["audio"]).is_file()
    ]
    if missing:
        raise SystemExit(f"{len(missing)} audio files are missing; first: {missing[0]}")
    minutes = sum(float(row.get("duration") or 0) for row in rows) / 60
    print(f"Selected {len(rows)} files ({minutes:.2f} minutes)", flush=True)
    if args.dry_run:
        return

    args.out.mkdir(parents=True, exist_ok=True)
    raw_root = args.out / "raw"
    for provider in args.providers:
        output_path = args.out / f"{provider}.jsonl"
        previous = load_jsonl(output_path)
        done = {row["id"] for row in previous if row.get("status") == "ok"}
        with output_path.open("a", encoding="utf-8") as output:
            for index, row in enumerate(rows, start=1):
                if row["id"] in done:
                    continue
                started = time.monotonic()
                result = {
                    "id": row["id"],
                    "provider": provider,
                    "language": row["language"],
                    "dialect": row.get("dialect"),
                    "source": row.get("source"),
                    "duration": row.get("duration"),
                    "reference": row.get("text", ""),
                }
                try:
                    hypothesis, raw = PROVIDERS[provider](Path(row["audio"]), row)
                    result.update(
                        status="ok",
                        hypothesis=hypothesis,
                        latency_seconds=time.monotonic() - started,
                    )
                    raw_dir = raw_root / provider
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    (raw_dir / f"{safe_name(row['id'])}.json").write_text(
                        json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                except Exception as error:
                    result.update(
                        status="error",
                        error=f"{type(error).__name__}: {error}",
                        latency_seconds=time.monotonic() - started,
                    )
                output.write(json.dumps(result, ensure_ascii=False) + "\n")
                output.flush()
                print(
                    f"{provider}: {index}/{len(rows)} {row['id']} {result['status']}",
                    flush=True,
                )
        write_metrics(
            args.out / f"{provider}.metrics.json",
            provider,
            load_jsonl(output_path),
            metadata_by_id,
        )


if __name__ == "__main__":
    main()
