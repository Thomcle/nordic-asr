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

Les sources non conventionnelles (YouTube, Vimeo, NRK, Sveriges Radio,
KommuneTV) sont documentées dans `docs/EXTERNAL_SOURCES.md` et déclarées dans
`configs/external_sources.yaml` et `configs/acquisition.yaml`.

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

## Acquisition publique et reprise

Tous les téléchargements sont atomiques et reprenables. Les index JSONL
conservent l’URL, l’identifiant, la durée et la provenance sans placer les
médias dans Git.

```bash
# Parlement sámi : quatre canaux audio
python scripts/index_sami_parliament.py
python scripts/download_sami_parliament.py \
  --languages sme smj sma nob --jobs 3

# Radios sámi et meänkieli de Sveriges Radio
python scripts/index_registered_media.py \
  --group sveriges_radio --download --jobs 3

# Séries NRK explicitement enregistrées (kvène et sámi)
python scripts/index_registered_media.py \
  --group nrk_series --download --jobs 2

# Chaînes vidéo autorisées par la configuration
python scripts/download_external_media.py \
  --sources ruijan_kaiku halti_kven samediggi nrk_sami_oahpahallit kven_seed

python scripts/acquisition_status.py

# Métadonnées des vidéos publiques des titres de presse régionaux
python scripts/index_amedia_video.py
```

Un échec réseau isolé n’interrompt pas toute une collection. Relancer la même
commande reprend les fichiers incomplets. Les pages nécessitant un compte, un
contournement géographique ou un DRM sont laissées de côté.

## Benchmark reproductible

Les révisions de FLEURS et des modèles sont figées dans
`configs/benchmarks.yaml`.

```bash
python scripts/prepare_fleurs.py
bash scripts/run_initial_benchmarks.sh
```

Pour un test dialectal équilibré :

```bash
python scripts/select_benchmark.py data/eval/nbtale12/test.jsonl \
  --group-by dialect --minutes-per-group 60 \
  --out data/eval/nbtale12/dialect_balanced.jsonl
```

Résultats initiaux sur FLEURS norvégien, 357 segments et environ 1,25 h :

| Modèle | WER | CER |
|---|---:|---:|
| NbAiLab/nb-whisper-large | 5,44 % | 2,05 % |
| openai/whisper-large-v3 | 7,76 % | 2,39 % |
| omniASR CTC 1B v2 | 13,24 % | 3,52 % |

Les prédictions et métriques sont versionnées dans `runs/baselines/`. Les
poids, checkpoints et données restent ignorés.

Le protocole détaillé, incluant comparaison cloud et résultats par dialecte,
est dans [`docs/BENCHMARK.md`](docs/BENCHMARK.md).

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

## Limites du dépôt

Le dépôt contient le code et les petites sorties de benchmark, jamais les
corpus, cookies, jetons, clés SSH ou poids privés. Les droits et conditions de
chaque média restent ceux de sa source.
