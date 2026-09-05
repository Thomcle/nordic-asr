# Architecture et protocole expérimental

## Pourquoi deux branches au départ

Les besoins sont contradictoires : le norvégien dispose de milliers d’heures,
alors que le kvène exige une adaptation à très peu d’exemples. Une seule
expérience ne permet pas de savoir si un décodeur génératif ou un modèle CTC
sera le meilleur compromis.

### Branche générative

- Point de départ : `openai/whisper-large-v3`.
- Référence norvégienne : `NbAiLab/nb-whisper-large-v0.8`.
- Référence sámi : `NbAiLab/whisper-large-sme`.
- Première passe : LoRA rang 32 sur attention et projections.
- Deuxième passe : dégel des six derniers blocs de l’encodeur si le gain de
  validation le justifie.
- Atouts : ponctuation, code-switching, fichiers longs, écosystème
  `faster-whisper`.
- Risque principal : hallucinations ; une épreuve silence/bruit est obligatoire.

### Branche CTC

- Point de départ sámi : `GetmanY1/wav2vec2-large-sami-cont-pt-22k`.
- Point de départ universel : `omniASR_CTC_1B_v2`.
- Nouveau vocabulaire Unicode partagé entre les quatre langues.
- Décodage glouton pour le débit, puis beam search avec modèles de langue
  KenLM séparés par langue.
- Atouts : vitesse, absence quasi totale d’hallucinations.
- Risque principal : ponctuation et segmentation moins naturelles.

## Données

1. **Or** : transcriptions manuelles, poids 1.
2. **Argent** : alignements de confiance élevée, poids 0,5.
3. **Pseudo-labels** : accord entre au moins deux modèles et confiance élevée,
   poids 0,2.
4. **Non annoté** : seulement pour préentraînement auto-supervisé.

Le mélange suit une température `alpha=0.5`. Les langues ne partagent jamais
un identifiant ambigu : `nob`, `nno`, `sme`, `smj`, `sma`, `fkv`.

## Évaluation

- séparation stricte par locuteur et session ;
- jeux propres, conversationnels, bruités et hors domaine ;
- WER et CER normalisés, mais aussi WER exact ;
- macro-moyenne des langues comme métrique de sélection ;
- intervalles bootstrap ;
- hallucination sur silence, musique et langues non cibles ;
- facteur temps réel et mémoire sur L4.

Le jeu kvène Ruija est la dépendance la plus importante. Une partie doit être
gelée avant tout entraînement. Sans test kvène indépendant, aucune affirmation
« SOTA kvène » n’est défendable.

