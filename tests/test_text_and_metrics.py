from nordic_asr.metrics import bootstrap_scores, score_rows
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


def test_scores_can_group_by_dialect():
    scores = score_rows(
        [
            {
                "language": "nob",
                "dialect": "north",
                "reference": "god dag",
                "hypothesis": "god dag",
            },
            {
                "language": "nob",
                "dialect": "west",
                "reference": "god dag",
                "hypothesis": "dag",
            },
        ],
        group_by="dialect",
    )
    assert scores["per_dialect"]["north"]["wer"] == 0
    assert scores["per_dialect"]["west"]["wer"] > 0


def test_cluster_bootstrap_is_deterministic():
    rows = [
        {
            "id": "1",
            "language": "nob",
            "speaker_id": "a",
            "reference": "god dag",
            "hypothesis": "god dag",
        },
        {
            "id": "2",
            "language": "nob",
            "speaker_id": "b",
            "reference": "hei verden",
            "hypothesis": "hei",
        },
    ]
    first = bootstrap_scores(rows, samples=20, seed=7)
    assert first == bootstrap_scores(rows, samples=20, seed=7)
    assert len(first["micro_wer"]) == 2
