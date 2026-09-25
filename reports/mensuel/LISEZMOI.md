# Rapport mensuel KPI — Groupe Automax

Génère le rapport mensuel de performance du Groupe (PDF, environ 20 pages) et un rapport détaillé par concession
(environ 14 pages chacun), à partir de `data/data.json` du tableau de bord KPI.

## Installation (une fois)

    pip install playwright
    python -m playwright install chromium

## Utilisation

    # dernier mois où toutes les concessions ont des données
    python rapport_kpi.py --data ../data/data.json

    # un mois précis, PDF à un endroit donné
    python rapport_kpi.py --data ../data/data.json --mois 2026-09 --sortie ./sortie/Rapport_KPI_Groupe_Automax_2026-09.pdf

    # rapports détaillés par concession (toutes, ou une seule avec --concession vw)
    python rapport_concession.py --data ../data/data.json --mois 2026-09 --sortie ./sortie

    # gabarit de budget à remplir (concessions sans budget dans leurs fichiers)
    python rapport_kpi.py --data ../data/data.json --gabarit-budget budgets.csv --annee 2026

Le fichier `budgets.csv` (s'il est à côté du script, ou passé avec `--budget`) complète les budgets manquants :
une ligne par concession × indicateur, une colonne par mois (`2026-01` … `2026-12`), dépenses en montants positifs.
Un mois n'est comparé au budget que si `pb_total` et `ebt` sont saisis pour tous les mois du cumul.

## Fichiers

- `kpi_data.py` : lecture de data.json, année précédente reconstituée, mois manquants reconstitués, budget CSV.
- `kpi_analyse.py` : regroupements, pont d'écart, alertes (seuils dans `SEUILS`), contrôle de qualité des données.
- `kpi_svg.py` : graphiques (pont d'écart, anneaux, barres, tendances).
- `rapport_commun.py` : mise en page commune (couverture, tableaux, anneaux, pagination, production des PDF).
- `rapport_kpi.py` + `rapport.css` : rapport du Groupe.
- `rapport_concession.py` : rapports détaillés par concession.
- `logo/` : logo Groupe Automax (version foncée et version blanche), couleurs anthracite #1D1D1B et vert #008848.
- `fonts/` : police Inter (intégrée au PDF).

Le dépôt GitHub du tableau de bord est public : ne pas y déposer les PDF générés.
