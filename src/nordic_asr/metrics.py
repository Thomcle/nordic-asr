"""ASR metrics with language-level reporting."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from jiwer import cer, wer

from .text import normalize_text


def score_rows(rows: Iterable[dict]) -> dict:
    """Compute micro and macro WER/CER from reference/hypothesis rows."""

    grouped: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"references": [], "hypotheses": []}
    )
    for row in rows:
        language = row["language"]
        grouped[language]["references"].append(normalize_text(row["reference"]))
        grouped[language]["hypotheses"].append(normalize_text(row["hypothesis"]))

    per_language = {}
    all_references: list[str] = []
    all_hypotheses: list[str] = []
    for language, values in sorted(grouped.items()):
        references = values["references"]
        hypotheses = values["hypotheses"]
        nonempty = sum(bool(x) for x in hypotheses)
        per_language[language] = {
            "wer": wer(references, hypotheses),
            "cer": cer(references, hypotheses),
            "empty_rate": 1.0 - nonempty / len(hypotheses),
            "utterances": len(references),
        }
        all_references.extend(references)
        all_hypotheses.extend(hypotheses)

    macro_wer = sum(x["wer"] for x in per_language.values()) / len(per_language)
    macro_cer = sum(x["cer"] for x in per_language.values()) / len(per_language)
    return {
        "micro_wer": wer(all_references, all_hypotheses),
        "micro_cer": cer(all_references, all_hypotheses),
        "macro_wer": macro_wer,
        "macro_cer": macro_cer,
        "per_language": per_language,
    }

