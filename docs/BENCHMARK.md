# Protocole de benchmark

## Deux résultats distincts

### Benchmark principal

Ce benchmark permet une comparaison techniquement défendable :

- norvégien : cinq groupes dialectaux (`east`, `west`, `mid`, `north`,
  `south`), au moins 60 minutes et 20 locuteurs par groupe ;
- sámi du Nord : au moins 60 minutes ;
- sámi de Lule et du Sud : au moins 30 minutes chacun ;
- kvène : au moins 30 minutes dès qu’une référence humaine est disponible ;
- séparation stricte des locuteurs, émissions et sources par rapport à
  l’entraînement.

NB Tale fournit des références manuelles et une région pour le norvégien. Une
fois matérialisé, son sous-ensemble de test doit rester gelé. Les évaluations
sámi utilisent des corpus humains indépendants des flux KommuneTV
pseudo-étiquetés. Une affirmation sur le kvène reste provisoire sans référence
humaine Ruija ou équivalente.

```bash
python scripts/prepare_hf_dataset.py scribe-project/nbtale12 \
  --split train --output-split test \
  --language nob --audio-column utterance_audio_file \
  --text-column standardized_text --id-column utterance_id \
  --speaker-column speaker_id --dialect-column region \
  --metadata-columns gender original_data_split \
  --out data/eval/nbtale12
python scripts/select_benchmark.py data/eval/nbtale12/test.jsonl \
  --groups east west mid north south --minutes-per-group 60 \
  --out data/eval/nbtale12/dialect_balanced.jsonl
```

### Démonstration courte

Un paquet de trois extraits de 5 à 8 minutes reste sous 25 minutes :

1. journalisme local norvégien, avec dialecte et bruit réel ;
2. sámi du Nord ;
3. kvène.

Cette démonstration est adaptée aux crédits gratuits, mais trois extraits ne
suffisent pas pour une affirmation statistique. Chaque transcription doit être
corrigée par un locuteur compétent avant calcul du WER.

Pour les médias sans transcription, une première sortie locale peut être
exportée comme feuille de correction :

```bash
python scripts/export_review_csv.py \
  data/eval/amedia_candidates/candidates.jsonl \
  runs/benchmarks/nb-whisper-large_amedia.jsonl \
  --out data/eval/amedia_candidates/human_review.csv
```

## Fournisseurs

Les paramètres non secrets et les liens de référence figurent dans
`configs/cloud_providers.yaml`. Le premier passage compare :

- ElevenLabs Scribe v2 ;
- Deepgram Nova-3 ;
- Google Speech-to-Text `latest_short` ;
- NB-Whisper, Whisper large-v3 et OmniASR ;
- les modèles spécialisés sámi pour les tests sámi.

Deepgram, Google, Azure et AWS documentent le norvégien, mais pas le sámi ou le
kvène dans leurs tableaux de langues actuels. Leurs sorties sur ces langues
doivent donc être présentées comme des tests hors support, et non comme une
comparaison parfaitement équitable. Speechmatics documente le norvégien
bokmål et une sortie nynorsk.

## Mesures

- WER et CER, exacts et normalisés ;
- résultats par langue, dialecte, source et condition acoustique ;
- taux de sortie vide et hallucinations sur silence/musique ;
- rappel des noms propres et termes locaux ;
- ponctuation et casse dans une mesure séparée ;
- temps de traitement, facteur temps réel et coût ;
- intervalles bootstrap par locuteur ou émission.

La configuration fournisseur est identique pour tous les extraits : aucune
liste de vocabulaire, diarisation désactivée et un essai avec langue imposée
plus un essai avec détection automatique.

## Exécution cloud

Les clés sont lues exclusivement dans l’environnement et ne doivent jamais
figurer dans un manifest, une commande versionnée ou Git :

```bash
python -m pip install -e ".[cloud]"
python scripts/benchmark_cloud.py data/eval/customer/test.jsonl \
  --providers elevenlabs deepgram google \
  --max-minutes 25
```

Le script est reprenable : un segment réussi n’est pas facturé une seconde
fois. Les réponses brutes, prédictions et métriques restent dans `runs/`, hors
Git.

## Données journalistiques

`index_amedia_video.py` inventorie uniquement les pages et métadonnées
publiques. Les indicateurs dialectaux sont géographiques et doivent être
confirmés par un humain. Les sous-titres marqués `Auto` ne constituent pas une
référence de test avant correction.

## Résultats norvégiens du 6 septembre 2026

Le test cloud court contient 116 segments NB Tale, 15,43 minutes et environ
trois minutes par région. Son SHA-256 est
`642e7f266e89db1eecfdf0f9701aad0fb074bdc75adcab6cb54cdfb8bfb7d9fc`.
Il sert à comparer les fournisseurs à coût réduit, pas à établir seul une
supériorité statistique.

| Système | East | Mid | North | South | West | Macro-WER | RTF API |
|---|---:|---:|---:|---:|---:|---:|---:|
| NbAiLab/nb-whisper-large (local) | 10,07 % | 4,85 % | 6,60 % | 7,47 % | 3,73 % | **6,54 %** | — |
| ElevenLabs Scribe v2 | 9,40 % | 5,83 % | 7,99 % | 7,83 % | 4,41 % | 7,09 % | 0,120 |
| Deepgram Nova-3 | 20,13 % | 15,53 % | 19,44 % | 14,95 % | 12,20 % | 16,45 % | 0,119 |
| Google `latest_short` | 20,81 % | 11,65 % | 22,92 % | 11,74 % | 17,97 % | 17,02 % | 0,169 |
| openai/whisper-large-v3 (local) | 23,15 % | 18,12 % | 17,71 % | 18,15 % | 16,61 % | 18,75 % | — |
| OmniASR CTC 1B v2 (local) | 27,18 % | 20,71 % | 25,35 % | 18,86 % | 22,37 % | 22,89 % | — |

Tous les 116 appels ont réussi. Les intervalles bootstrap à 95 % sont
enregistrés dans les sorties métriques. Le RTF mesure ici le temps de réponse
API cumulé divisé par la durée audio ; il n’inclut pas une éventuelle file
d’attente applicative. Les intervalles macro-WER de NB-Whisper
(`4,91–8,38 %`) et d’ElevenLabs (`5,24–9,03 %`) se chevauchent : ce test court
les place au même niveau statistique plutôt qu’il ne prouve un vainqueur.

Le test dialectal local long contient 2 104 segments et 4 h 45 d’audio. Son
SHA-256 est
`01cdf2ef9a6139bf6beff6144e30ec959ef6ec5326ccf95f963b2840b4e3f49d`.

| Modèle local | East | Mid | North | South | West | Macro-WER |
|---|---:|---:|---:|---:|---:|---:|
| NbAiLab/nb-whisper-large | 7,26 % | 7,24 % | 8,83 % | 8,28 % | 8,54 % | **8,03 %** |
| openai/whisper-large-v3 | 15,17 % | 15,42 % | 16,15 % | 18,50 % | 17,01 % | 16,45 % |
| OmniASR CTC 1B v2 | 21,09 % | 21,52 % | 24,16 % | 24,68 % | 26,50 % | 23,59 % |

Le premier tableau constitue la comparaison directe cloud/local, sur les mêmes
segments. Le second, beaucoup plus long, est la mesure principale de robustesse
dialectale locale.
