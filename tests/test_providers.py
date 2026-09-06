from nordic_asr.providers import provider_language


def test_provider_language_uses_safe_defaults():
    assert provider_language("elevenlabs", {"language": "nob"}) == "nor"
    assert provider_language("deepgram", {"language": "nno"}) == "no"
    assert provider_language("google", {"language": "nob"}) == "nb-NO"
    assert provider_language("deepgram", {"language": "sme"}) is None


def test_provider_language_allows_manifest_override():
    row = {
        "language": "sme",
        "provider_languages": {"deepgram": "multi"},
    }
    assert provider_language("deepgram", row) == "multi"
