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
  --split train --output-split test --where original_data_split=test \
  --language nob --audio-column utterance_audio_file \
  --text-column standardized_text --id-column utterance_id \
  --speaker-column speaker_id --dialect-column region \
  --metadata-columns gender original_data_split \
  --out data/eval/nbtale12
```

### Démonstration courte

Un paquet de trois extraits de 5 à 8 minutes reste sous 25 minutes :

1. journalisme local norvégien, avec dialecte et bruit réel ;
2. sámi du Nord ;
3. kvène.

Cette démonstration est adaptée aux crédits gratuits, mais trois extraits ne
suffisent pas pour une affirmation statistique. Chaque transcription doit être
corrigée par un locuteur compétent avant calcul du WER.

## Fournisseurs

Les paramètres non secrets et les liens de référence figurent dans
`configs/cloud_providers.yaml`. Le premier passage compare :

- ElevenLabs Scribe v2 ;
- Deepgram Nova-3 ;
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
  --providers elevenlabs deepgram \
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
