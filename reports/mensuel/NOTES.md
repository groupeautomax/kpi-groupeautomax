# Rapport mensuel KPI — notes entre les exécutions

La tâche planifiée « Rapports mensuels KPI Groupe Automax » démarre chaque mois dans une session sans mémoire.
Ce fichier sert de mémoire : décisions à respecter, limites connues, historique.

## Décisions de conception (ne pas revenir en arrière sans demande explicite du client)

- **Couleurs et logo Groupe Automax** (demande du client, 25 septembre 2026) : anthracite `#1D1D1B`, vert `#008848`,
  logo officiel dans `logo/` (version foncée pour fond clair, version blanche pour la couverture). Remplace la palette
  charbon/rouille du pipeline trimestriel. Vert = favorable, rouge = défavorable, gris = année précédente.
- **Aucune mention de « Quotus »** dans les rapports. On parle du « gabarit financier standard du Groupe » ; le relevé
  GM Canada de HAWKS est nommé, car il explique pourquoi son an passé est reconstitué.
- **Pas de pages vides** (Acquisitions, Immobilier, Pipeline) : retirées du rapport mensuel.
- **Règles de calcul du tableau de bord** : périmètre comparable, ratios du groupe recalculés à partir des sommes,
  dépenses en positif (vert = plus bas), budget à 0 = non saisi.
- Structure des rapports par concession calquée sur l'ancien « Rapport_Volkswagen_YTD2026 » demandé par le client :
  couverture, introduction et coup d'œil, performance financière, indicateurs opérationnels, écarts, analyse
  opérationnelle, tendances, « Ce que les données montrent ».
- **Mise en page aérée, fonds blancs** (demande du client, 25 septembre 2026 : « trop condensé », « pas de fond noir ») :
  couverture blanche avec bandeau vert, en-têtes de tableau clairs (filet vert), une idée par page, encadré
  « À retenir » en tête de page. Les parts (profit brut, dépenses) sont en **graphiques en anneau** (demande du
  client) ; les montants négatifs (crédits nets) sont exclus de l'anneau et signalés sous le tableau, et les
  pourcentages portent sur la somme des postes positifs. Série de l'année en cours en bleu, an passé en trait gris.

## Sources des chiffres (tableau de bord)

- Le rapport lit `data/data.json`, construit par `src/extract.py` à partir de `sources/` (synchronisé depuis Drive par
  `src/drive_sync.py`). Chaque mois de data.json porte `source_format` : `gabarit` (Réalisé du Groupe), `etat_gm` (état
  financier GM Canada : HAWKS, STM), `etat_hyundai` (état financier Hyundai Canada : Hyundai Longueuil) ou `etat_vw`
  (état financier Volkswagen Canada).
- Règles de choix (demande du client, 25 septembre 2026) : les Réalisés qui se terminent par V0 ou V1 sont toujours ignorés ;
  on prend celui qui se termine par le nom de la concession (ex. « 2025-07_Réalisé_VW.xlsx ») ; l'état financier du
  constructeur l'emporte sur le Réalisé pour un même mois ; les fichiers de verrouillage « ~$ » sont ignorés.
- Exception VW (décision du client, 25 septembre 2026) : le Réalisé reste la source par défaut (il contient le budget).
  Si l'EBT du mois du Réalisé diffère de plus de 1 000 $ de l'état Volkswagen Canada, on prend un autre Réalisé du même
  mois qui concorde avec l'état (il garde le budget), sinon l'état lui-même (plus de budget mensuel pour ce mois). Un
  état incohérent (cumul − cumul du mois précédent ≠ mois, p. ex. l'état d'avril 2025 qui contient les chiffres de mai)
  n'est jamais retenu. Mois touchés en 2026 : janvier, février, juin, juillet.
- Un état constructeur n'a ni budget ni année précédente : l'an passé est reconstitué à partir des mois de l'an passé.
  La page « Base de présentation » de chaque concession indique la source mois par mois quand elle varie.

## Contenu produit chaque mois

- `Rapport_KPI_Groupe_Automax_AAAA-MM.pdf` — environ 20 pages (le nombre varie avec les alertes et les points à régler).
- `Rapport_<Concession>_AAAA-MM.pdf` — environ 14 à 15 pages chacun, pour chaque concession qui a des données ce mois-là.
- Contrôle : le script signale « ATTENTION — contenu qui déborde » si une page déborde en hauteur ou en largeur ;
  aucun avertissement ne doit rester.
- Code : `rapport_kpi.py` (Groupe), `rapport_concession.py` (concessions), `rapport_commun.py` (mise en page commune),
  `kpi_data.py`, `kpi_analyse.py`, `kpi_svg.py`, `rapport.css`.

## Limites connues

- Le rapport détecte et affiche lui-même (page « Qualité et couverture des données ») les budgets absents, les mois
  manquants, l'an passé reconstitué, les révisions de cumul et les anomalies de postes : ne pas les corriger à la main.
- Un `budgets.csv` (gabarit : `python rapport_kpi.py --gabarit-budget budgets.csv --annee 2026`) peut compléter les
  budgets manquants. Il contient des données confidentielles : il ne va jamais dans ce dépôt public (le garder dans Google Drive).
- Le dépôt est public : ne jamais y déposer les PDF ni les HTML générés.

## Historique

### Août 2026 — première version (25 septembre 2026)
- Rapport mensuel du Groupe (mois + cumul, pont d'écart, nouveaux indicateurs, qualité des données) et rapports
  détaillés par concession, aux couleurs et au logo Groupe Automax.
- Vérification : 107 valeurs du PDF recalculées indépendamment à partir de data.json, 0 écart ; cumul à juin
  identique à l'ancien rapport T2 (EBT 5 199 561 $).
- Remplace la tâche trimestrielle (ancien pipeline `reports/`, conservé tel quel mais plus appelé).
- Même jour, 2e version : mise en page aérée, fonds blancs, graphiques en anneau ; Groupe 20 pages, concessions
  14–15 pages. Vérification : 100 valeurs recalculées indépendamment, 0 écart ; identité du pont vérifiée.
- Même jour : lecteur de l'état financier Hyundai Canada et prise en charge de l'état GM de STM dans `src/extract.py` ;
  correctifs de `src/drive_sync.py` (fichiers « ~$ » qui écrasaient les vrais classeurs, chemins en double, dossier des
  états financiers de STM). Conséquence : les mois de VW 2025 tirés jusque-là des brouillons V0/V1 sont corrigés.
- Même jour : lecteur de l'état financier Volkswagen Canada (`etat_vw`) et règle VW ci-dessus (commit b5a1a07). Le
  cumul d'août de VW ne change pas (833 482 $, identique dans le Réalisé et l'état) ; les mois de janvier, février, juin
  et juillet 2026 prennent les chiffres de l'état.
