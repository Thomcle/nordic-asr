"""ASR metrics with language-level reporting."""

from __future__ import annotations

from collections import defaultdict
import random
from typing import Iterable

from jiwer import cer, wer

from .text import normalize_text


def score_rows(rows: Iterable[dict], *, group_by: str = "language") -> dict:
    """Compute micro and macro WER/CER grouped by a manifest field."""

    grouped: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"references": [], "hypotheses": []}
    )
    for row in rows:
        group = str(row.get(group_by) or "unknown")
        grouped[group]["references"].append(normalize_text(row["reference"]))
        grouped[group]["hypotheses"].append(normalize_text(row["hypothesis"]))

    if not grouped:
        raise ValueError("Cannot score an empty prediction set")
    per_group = {}
    all_references: list[str] = []
    all_hypotheses: list[str] = []
    for group, values in sorted(grouped.items()):
        references = values["references"]
        hypotheses = values["hypotheses"]
        nonempty = sum(bool(x) for x in hypotheses)
        per_group[group] = {
            "wer": wer(references, hypotheses),
            "cer": cer(references, hypotheses),
            "empty_rate": 1.0 - nonempty / len(hypotheses),
            "utterances": len(references),
        }
        all_references.extend(references)
        all_hypotheses.extend(hypotheses)

    macro_wer = sum(x["wer"] for x in per_group.values()) / len(per_group)
    macro_cer = sum(x["cer"] for x in per_group.values()) / len(per_group)
    per_key = "per_language" if group_by == "language" else f"per_{group_by}"
    return {
        "micro_wer": wer(all_references, all_hypotheses),
        "micro_cer": cer(all_references, all_hypotheses),
        "macro_wer": macro_wer,
        "macro_cer": macro_cer,
        per_key: per_group,
    }


def bootstrap_scores(
    rows: Iterable[dict],
    *,
    group_by: str = "language",
    cluster_by: str = "speaker_id",
    samples: int = 1000,
    seed: int = 17,
) -> dict:
    """Return stratified cluster-bootstrap 95% intervals for WER and CER."""

    materialized = list(rows)
    if not materialized:
        raise ValueError("Cannot bootstrap an empty prediction set")
    grouped_clusters: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in materialized:
        group = str(row.get(group_by) or "unknown")
        cluster = str(row.get(cluster_by) or row["id"])
        grouped_clusters[group][cluster].append(row)

    rng = random.Random(seed)
    observations: dict[str, list[float]] = defaultdict(list)
    for _ in range(samples):
        sample_rows = []
        for clusters in grouped_clusters.values():
            names = sorted(clusters)
            for name in rng.choices(names, k=len(names)):
                sample_rows.extend(clusters[name])
        score = score_rows(sample_rows, group_by=group_by)
        observations["micro_wer"].append(score["micro_wer"])
        observations["micro_cer"].append(score["micro_cer"])
        observations["macro_wer"].append(score["macro_wer"])
        observations["macro_cer"].append(score["macro_cer"])
        per_key = "per_language" if group_by == "language" else f"per_{group_by}"
        for group, values in score[per_key].items():
            observations[f"{group}.wer"].append(values["wer"])
            observations[f"{group}.cer"].append(values["cer"])

    def interval(values: list[float]) -> list[float]:
        values = sorted(values)
        low = values[int(0.025 * (len(values) - 1))]
        high = values[int(0.975 * (len(values) - 1))]
        return [low, high]

    return {key: interval(values) for key, values in sorted(observations.items())}
