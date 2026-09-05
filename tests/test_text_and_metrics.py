from nordic_asr.metrics import score_rows
from nordic_asr.text import normalize_text


def test_normalization_preserves_diacritics():
    assert normalize_text("Čáppa, Kainuun! Ž") == "čáppa kainuun ž"


def test_scores_are_per_language():
    scores = score_rows(
        [
            {"language": "sme", "reference": "buorre beaivi", "hypothesis": "buorre beaivi"},
            {"language": "fkv", "reference": "hyvvää päivää", "hypothesis": "hyvää päivää"},
        ]
    )
    assert set(scores["per_language"]) == {"sme", "fkv"}
    assert scores["per_language"]["sme"]["wer"] == 0
    assert scores["macro_wer"] > 0
