# Nordic ASR

Projet de reconnaissance vocale pour :

- norvégien bokmål (`nob`) et nynorsk (`nno`) ;
- sámi du Nord (`sme`) en priorité, puis lule (`smj`) et sud (`sma`) si les
  données sont suffisantes ;
- kvène (`fkv`).

Le dépôt est conçu pour une machine disposant de deux NVIDIA L4. Les données,
modèles et expériences restent hors Git dans `data/`, `models/` et `runs/`.

## Stratégie

Nous ne déclarons pas un modèle « SOTA » avant une évaluation indépendante.
Deux familles sont comparées :

1. **Whisper large-v3 / NB-Whisper** : excellente ponctuation, robustesse et
   intégration produit ; adaptation LoRA puis dégel partiel.
2. **wav2vec2 sámi 22k / OmniASR CTC** : très bon point de départ acoustique
   pour les langues minoritaires et inférence rapide.

Le champion sera choisi sur le **macro-WER par langue**, le CER, la robustesse
au bruit, les noms propres, le débit et la mémoire. Aucun corpus d’entraînement
ne doit contaminer les jeux de test.

## Arborescence

```text
configs/       paramètres et registre des sources
scripts/       acquisition, validation, entraînement et évaluation
src/           normalisation et métriques partagées
data/raw/      archives sources
data/manifests manifests JSONL normalisés
data/eval/     jeux de test gelés
models/        poids téléchargés et modèles produits
runs/          journaux et checkpoints
```

## Démarrage sur la VM

```bash
cd ~/nordic-asr
bash scripts/bootstrap_vm.sh
conda activate nordic-asr

# Inventaire sans téléchargement
python scripts/download_sprakbanken.py --list

# Corpus norvégiens sélectionnés
python scripts/download_sprakbanken.py \
  --datasets npsc nbsamtale nbtale nst \
  --download --jobs 4

# Contrôle d'un manifest
python scripts/validate_manifest.py data/manifests/train.jsonl
```

## Contrat d’un manifest

Une ligne JSON par segment :

```json
{"id":"source:segment","audio":"/abs/path.wav","text":"...","language":"sme","split":"train","duration":8.4,"speaker_id":"...","source":"..."}
```

Les séparations sont faites par locuteur, émission ou séance, jamais au hasard
par segment. Les transcriptions faibles sont marquées `supervision="weak"` et
ne sont pas utilisées dans les jeux de test.

## Critère de sortie

Un modèle est prêt pour un pilote seulement si :

- le WER/CER est publié séparément pour `nob`, `nno`, `sme` et `fkv` ;
- un test hors domaine, bruité et conversationnel est conservé ;
- le taux d’hallucination sur silence et audio hors langue est mesuré ;
- l’inférence de fichiers longs est testée avec VAD et timestamps ;
- le résultat est reproductible depuis les manifests et la configuration.

