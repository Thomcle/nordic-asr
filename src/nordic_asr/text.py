"""Unicode-safe text normalization for Nordic ASR evaluation."""

from __future__ import annotations

import re
import unicodedata

_PUNCTUATION = re.compile(r"[^\w\s'’-]", flags=re.UNICODE)
_SPACE = re.compile(r"\s+")


def normalize_text(text: str, *, keep_apostrophe: bool = True) -> str:
    """Normalize text without destroying Sámi/Kven diacritics.

    This intentionally does not transliterate characters such as č, đ, ŋ, š,
    ŧ and ž. Numbers are left untouched until a language-specific verbalizer
    has been validated.
    """

    value = unicodedata.normalize("NFC", text).casefold()
    value = value.replace("’", "'")
    if keep_apostrophe:
        value = _PUNCTUATION.sub(" ", value)
    else:
        value = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
    value = value.replace("_", " ")
    return _SPACE.sub(" ", value).strip()


def character_inventory(texts: list[str]) -> list[str]:
    """Return a stable non-whitespace character inventory."""

    return sorted({char for text in texts for char in normalize_text(text) if not char.isspace()})

