# Sources audio/vidéo extérieures aux jeux de données

## Ordre de priorité

### Niveau A — audio avec texte humain horodaté

1. Sous-titres WebVTT de NRK TV/Radio, Yle Areena et SVT Play.
2. Vidéos institutionnelles YouTube/Vimeo avec sous-titres manuels.
3. Discours et auditions dont le texte officiel est publié séparément.
4. Livres audio ou lectures avec texte intégral disponible.

Ces données peuvent rejoindre l’entraînement après alignement forcé et contrôle
automatique des coupures.

### Niveau B — sous-titres automatiques

YouTube et Filmot sont utiles pour la **découverte**. Filmot permet de chercher
des mots caractéristiques dans les sous-titres et de récupérer les identifiants
des vidéos. Le téléchargement final est fait avec `yt-dlp`, en conservant :

- l’audio original ;
- les sous-titres manuels ;
- la piste automatique originale `*-orig` ;
- le JSON de métadonnées.

Une traduction automatique YouTube ne doit jamais être prise pour une
transcription. Les sous-titres automatiques sont ré-alignés avec l’audio et ne
sont conservés que si leur accord avec les modèles enseignants est suffisant.

### Niveau C — audio sans texte

- chaînes d’interviews et podcasts ;
- archives municipales ;
- canaux d’interprétation du Parlement sámi ;
- collections d’histoire orale et muséales.

Ces fichiers servent au préentraînement auto-supervisé ou au pseudo-étiquetage
par consensus, jamais à l’évaluation.

## Sources prioritaires identifiées

### Kvène

- YouTube **Ruijan Kaiku** : 21 vidéos indexées.
- YouTube **Halti kvenkultursenter / Haltiin kväänisentteri** : 79 vidéos.
- Série de podcasts **Praatikas** : longs entretiens de plusieurs régions.
- Vimeo Ruijan Kaiku et Anstein Mikkelsen : récits, sketchs, documentaires et
  petites lectures en kvène.
- **NRK Kvääni** : reportages, radio et podcasts.
- **Kaffipraatti** (NRK) : six épisodes du premier podcast en kvène, environ
  1,7 h. L’audio kvène est accompagné de sous-titres norvégiens traduits :
  excellents repères temporels, mais pas des transcriptions ASR directes.
- **DigitaltMuseum** et archives locales du Troms/Finnmark.
- **Meänraatio** (Sveriges Radio) : 1 066 épisodes téléchargeables, environ
  493 h / 27,8 Go, en meänkieli, langue proche du kvène. À utiliser pour
  transfert acoustique, jamais comme texte kvène sans conversion contrôlée.
- **Meänraatiopodden**, **Meän Kläpit** et **Finnmix** : environ 76 h
  supplémentaires, avec filtrage audio obligatoire pour les émissions mixtes.
- À terme, Ruija reste la source de référence supervisée.

### Sámi

- Archives KommuneTV du Parlement sámi : 762 h nord, 686 h lule et 725 h sud.
- YouTube **Sámediggi Sametinget** : 80 vidéos indexées.
- YouTube **NRK Sámi oahpahallit** : 40 vidéos.
- NRK Sápmi, Yle Sápmi et SVT Sápmi/Ođđasat.
- **Ođđasat TV** et **Ju-Ká** via l’API de lecture publique NRK.
- Sveriges Radio : **Sameradion**, **Sameradiopodden**, **Mánáidrádio**,
  **Magiska skrinet** et **Politikpodden Sápmi**, environ 576 h indexables.
- Chaînes d’apprentissage et contenus GiellaLT/Oahpa!.

### Norvégien et dialectes

- NRK, émissions locales et podcasts avec WebVTT.
- Stortinget et KommuneTV de communes : discours longs avec région connue.
- Cours et conférences d’universités sur Kaltura/Panopto/YouTube.
- Histoire orale de la Bibliothèque nationale et de DigitaltMuseum.
- Livres audio publics et lectures alignables avec leurs textes.

## Classification et contrôle

1. Détection parole/musique et segmentation VAD en blocs de 2–30 s.
2. Détection de langue audio avec `facebook/mms-lid-4017` pour `nob`, `nno`
   et `sme`; un classifieur spécifique devra être entraîné pour `fkv`, `smj`
   et `sma`.
3. Dialecte norvégien avec
   `scribe-project/nb-whisper-dialect-id-5dialect` :
   est, ouest, centre, nord, sud. Le modèle atteint 92,63 % sur son test
   parlementaire, mais son résultat doit rester une étiquette souple hors
   domaine.
4. Transcription par deux enseignants indépendants.
5. Conservation des segments si sous-titre et enseignants s’accordent, avec
   un poids plus faible pour les sous-titres automatiques.
6. Déduplication acoustique et textuelle avant toute séparation train/test.

Un dialecte oral n’est pas équivalent à une norme écrite. Le classifieur
dialectal sert à équilibrer les accents; le choix bokmål/nynorsk vient du texte
de référence ou d’un normalisateur orthographique séparé.

## Ce qui n’est pas automatisé

- aucune tentative de contourner DRM, géoblocage, paywall ou authentification ;
- Vimeo privé et les collections de bibliothèque restreintes sont seulement
  répertoriés ;
- Filmot sert à découvrir des identifiants YouTube, pas à constituer une
  vérité terrain ;
- Yle et SVT demandent encore un indexeur dédié et une validation des pistes
  de sous-titres avant un téléchargement massif.
