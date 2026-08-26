# Pipeline de rapports trimestriels — Groupeautomax

Génère les 6 documents de performance (1 rapport de groupe + 5 rapports individuels
par concession) directement à partir des données du tableau de bord KPI
(`data/data.json` de ce même dépôt), pour une période "cumulatif année à ce jour"
(YTD) se terminant à la fin d'un trimestre (mars / juin / septembre / décembre),
comparée à la même période l'année précédente.

## Utilisation

```bash
pip install playwright matplotlib numpy
# Chromium doit être disponible; sur le bac à sable Claude il est déjà installé à
# /opt/pw-browsers/chromium. Ailleurs: `playwright install chromium`.

python3 run_quarter.py --outdir ./sortie
```

Par défaut, `run_quarter.py` détecte automatiquement le trimestre le plus
récemment terminé (aujourd'hui même) et télécharge les données en direct depuis
GitHub. Options utiles :

- `--period 2026-09` — force un trimestre précis (doit être un mois de fin de
  trimestre : 03, 06, 09 ou 12).
- `--data-file chemin.json` — utilise un instantané local de `data.json` au lieu
  de le télécharger (utile pour tester après un correctif d'extraction avant
  qu'il soit déployé en production).
- `--keep-work` — conserve le dossier de travail intermédiaire
  (`<outdir>/_work/`, JSON intermédiaires + HTML) pour du débogage.

Sortie : 6 PDF dans `--outdir`, nommés
`Groupeautomax_Rapport_Performance_T<N>-<année>.pdf` et
`Rapport_<Concession>_T<N>-<année>.pdf`.

## Architecture

```
period.py              → calcule les libellés/dates de la période (trimestre visé)
extract_summary.py      → extrait les KPI par concession depuis data.json (live_data.json)
build_report_data.py    → additionne les 5 concessions, calcule marges/ratios/deltas
scorecard.py             → classement des concessions par variation d'EBT, concentration des profits
mix_data.py              → répartition du profit brut / des dépenses (Groupe)
per_dealer_mix.py        → idem, par concession
make_charts.py           → 2 graphiques en anneau (Groupe)
make_dealer_charts.py    → 2 graphiques en anneau par concession (10 au total)
build_html.py            → assemble le rapport de Groupe (16 pages) en HTML
build_dealer_html.py     → assemble les 5 rapports individuels (7 pages chacun) en HTML
run_quarter.py           → orchestrateur : lie tout, rend les PDF via Playwright/Chromium
```

Chaque script (sauf `period.py` et `run_quarter.py`) lit/écrit ses fichiers dans
le répertoire pointé par la variable d'environnement `KPI_WORKDIR` (par défaut
`.`) — `run_quarter.py` la fixe automatiquement à un sous-dossier `_work/` de
`--outdir` pour chaque exécution.

Le HTML des deux générateurs de rapport (`build_html.py`, `build_dealer_html.py`)
utilise des jetons de période calculés une seule fois par `period.py` et fusionnés
dans `report_data.json` (`Y_CUR`, `Y_PRIOR`, `MOIS_CUR`, `DATE_FIN_CUR`,
`NB_MOIS_TXT`, `PREP_LABEL`, etc.) plutôt que du texte codé en dur — un nouveau
trimestre ne demande aucune modification de ces deux fichiers.

## Cadence et automatisation

Un déclencheur planifié ("scheduled task") relance ce pipeline environ 5 jours
ouvrables après la fin de chaque trimestre civil et livre les 6 PDF. Voir
`NOTES.md` pour l'historique des exécutions, les limites connues et les pistes
d'amélioration retenues pour les prochaines exécutions — chaque exécution
planifiée démarre une session sans mémoire des précédentes; `NOTES.md` sert de
mémoire persistante entre les trimestres.

## Style / conventions

- Formatage fr-CA : séparateur de milliers = espace, décimale = virgule, suffixe
  " $" (ex. "35 113 964 $"). Deltas de ratios en points de base ("pdb").
- Couleurs de marque : charbon `#21201d`, rouille `#c1622f`, sable `#f2ece0`
  (choisies pour se distinguer du gabarit d'exemple client "Horizon" —
  voir `NOTES.md` § Décisions de conception avant de les changer).
- Les champs `depenses_*` sont stockés en négatif dans data.json (sorties de
  caisse) — `build_report_data.py` calcule les variations sur la magnitude
  (`MAGNITUDE_FIELDS`) pour que le signe affiché corresponde à l'intuition
  (dépenses en hausse = delta positif, affiché en rouge).
- Toute section sans donnée disponible affiche un encadré "Données non
  disponibles" plutôt que d'être omise ou estimée — ne jamais fabriquer de
  chiffre.
