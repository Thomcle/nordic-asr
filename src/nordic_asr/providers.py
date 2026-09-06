"""Small, secret-safe adapters for cloud ASR benchmark providers."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path

import requests


def provider_language(provider: str, row: dict) -> str | None:
    """Return an explicit provider language only when support is known."""

    override = (row.get("provider_languages") or {}).get(provider)
    if override:
        return str(override)
    if row.get("language") in {"nob", "nno"}:
        return "nor" if provider == "elevenlabs" else "no"
    return None


def elevenlabs(audio: Path, row: dict, timeout: int = 3600) -> tuple[str, dict]:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    data = {
        "model_id": "scribe_v2",
        "tag_audio_events": "false",
        "diarize": "false",
        "timestamps_granularity": "word",
        "seed": "17",
    }
    language = provider_language("elevenlabs", row)
    if language:
        data["language_code"] = language
    with audio.open("rb") as handle:
        response = requests.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": key},
            data=data,
            files={"file": (audio.name, handle, mimetypes.guess_type(audio)[0])},
            timeout=(30, timeout),
        )
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("text") or ""), payload


def deepgram(audio: Path, row: dict, timeout: int = 3600) -> tuple[str, dict]:
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        raise RuntimeError("DEEPGRAM_API_KEY is not set")
    params = {
        "model": "nova-3",
        "smart_format": "true",
        "punctuate": "true",
        "utterances": "true",
    }
    language = provider_language("deepgram", row)
    if language:
        params["language"] = language
    else:
        params["detect_language"] = "true"
    with audio.open("rb") as handle:
        response = requests.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {key}",
                "Content-Type": mimetypes.guess_type(audio)[0]
                or "application/octet-stream",
            },
            params=params,
            data=handle,
            timeout=(30, timeout),
        )
    response.raise_for_status()
    payload = response.json()
    channels = payload.get("results", {}).get("channels", [])
    alternatives = channels[0].get("alternatives", []) if channels else []
    text = alternatives[0].get("transcript", "") if alternatives else ""
    return str(text), payload


PROVIDERS = {
    "elevenlabs": elevenlabs,
    "deepgram": deepgram,
}
