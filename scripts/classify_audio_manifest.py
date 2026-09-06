#!/usr/bin/env python3
"""Add language-ID or Norwegian dialect probabilities to an audio manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import librosa
import numpy as np
import torch
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

MODELS = {
    "language": "facebook/mms-lid-4017",
    "dialect": "scribe-project/nb-whisper-dialect-id-5dialect",
}
RELEVANT_LANGUAGE_LABELS = {"nob", "nno", "sme", "smn", "fin", "swe", "dan"}


def windows(audio: np.ndarray, size: int, maximum: int) -> list[np.ndarray]:
    if len(audio) <= size:
        return [audio]
    starts = np.linspace(0, len(audio) - size, num=min(maximum, len(audio) // size + 1))
    return [audio[int(start) : int(start) + size] for start in starts]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--task", choices=MODELS, required=True)
    parser.add_argument("--model")
    parser.add_argument("--window-seconds", type=int, default=30)
    parser.add_argument("--max-windows", type=int, default=10)
    args = parser.parse_args()

    model_id = args.model or MODELS[args.task]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    feature_extractor = AutoFeatureExtractor.from_pretrained(model_id)
    model = AutoModelForAudioClassification.from_pretrained(model_id).to(device).eval()
    sample_rate = feature_extractor.sampling_rate
    window_size = sample_rate * args.window_seconds

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open(encoding="utf-8") as source, args.out.open(
        "w", encoding="utf-8"
    ) as destination:
        for line in source:
            row = json.loads(line)
            audio, _ = librosa.load(row["audio"], sr=sample_rate, mono=True)
            probabilities = []
            for chunk in windows(audio, window_size, args.max_windows):
                inputs = feature_extractor(
                    chunk, sampling_rate=sample_rate, return_tensors="pt"
                )
                inputs = {key: value.to(device) for key, value in inputs.items()}
                with torch.inference_mode():
                    logits = model(**inputs).logits
                probabilities.append(torch.softmax(logits, dim=-1).cpu())
            scores = torch.cat(probabilities).mean(dim=0)
            best = int(scores.argmax())
            label = model.config.id2label[best]
            prefix = "audio_language" if args.task == "language" else "dialect"
            row[prefix] = label
            row[f"{prefix}_confidence"] = float(scores[best])
            if args.task == "language":
                row["audio_language_relevant_scores"] = {
                    model.config.id2label[index]: float(score)
                    for index, score in enumerate(scores)
                    if model.config.id2label[index] in RELEVANT_LANGUAGE_LABELS
                }
                # MMS-LID has no fkv label. `fin` is therefore retained as a
                # Kven candidate, not accepted as a final language decision.
                row["kven_candidate"] = label == "fin"
            else:
                row["dialect_scores"] = {
                    model.config.id2label[index]: float(score)
                    for index, score in enumerate(scores)
                }
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(row["id"], label, float(scores[best]), flush=True)


if __name__ == "__main__":
    main()

