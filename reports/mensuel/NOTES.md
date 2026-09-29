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
- `Rapport_Operations_fixes_AAAA-MM.pdf` — analyse approfondie de l'après-vente (environ 13 pages) : bons de travail par
  type (client, garantie, interne, esthétique), $ et heures par BT, atelier, pièces par canal, carrosserie, tendances 24 mois.
  `python rapport_apres_vente.py --data ../../data/data.json --mois AAAA-MM --sortie sortie`
- `Rapport_Operations_fixes_<Concession>_AAAA-MM.pdf` — un rapport opérations fixes par concession (environ 10 pages) : départements
  Service / Pièces / Carrosserie, BT par type, positionnement dans le Groupe, détail mensuel vs an passé, tendances, atelier, pièces.
  `python rapport_apres_vente_concession.py --data ../../data/data.json --mois AAAA-MM --sortie sortie`
- Le rapport du Groupe contient 2 pages « Après-vente : bons de travail » ; chaque rapport de concession, 1 page.
- Code : `rapport_kpi.py` (Groupe), `rapport_concession.py` (concessions), `rapport_apres_vente.py` (opérations fixes),
  `rapport_commun.py` (mise en page commune), `kpi_data.py`, `kpi_apres_vente.py`, `kpi_analyse.py`, `kpi_svg.py`, `rapport.css`.

## Opérations fixes (bons de travail) — règles

- Données : `sections.<month|ytd>.apres_vente` de data.json, lues par `src/apres_vente.py` (Réalisé : blocs Service,
  Pièces, Carrosserie, colonne # = BT ; état GM : Page 6 par compte ; état Hyundai : Pages 4 et 6 ; état VW : Pages 5 et 6).
- Types : client (atelier, service rapide, contrats, prépayé ; service mobile de STM inclus, détail « mobile »), garantie,
  interne (inspection des véhicules neufs de l'état GM incluse, détail « inspection »), esthétique (Réalisé BMW/VW).
- Montants = ventes ; profit brut à part. Ratios par BT : seulement les montants des concessions qui ont des BT pour le
  type (l'esthétique VW a des ventes sans BT). Groupe recalculé à partir des sommes, écarts à périmètre comparable.
- Heures : seulement VW (état VW Canada) et Hyundai (état Hyundai Canada). Quand le Réalisé VW est retenu, ses heures
  viennent de l'état VW du même mois si les nombres de BT concordent (écart ≤ 3 %). BMW, STM et HAWKS : pas d'heures dans
  leurs fichiers (à demander : rapport DMS mensuel des heures vendues par type).
- Heures à 0 avec de la main-d'œuvre = donnée absente (jamais zéro). Techniciens de l'état GM non utilisés (STM incohérent).

## Profit véhicule, F&I et gros — règles (28 septembre 2026, refait le 29)

- Chaque département véhicules (neufs, usagés) est séparé en trois : **profit véhicule détail** (lignes véhicules de
  l'état ou du Réalisé ; neufs : démos et flottes inclus), **F&I** (ligne « Total F&I » ; état GM : le transfert F&A des
  autres revenus est ramené dans le département) et **gros, encan, export et autres** = profit brut du département −
  profit véhicule − F&I. Clés data.json : `pbv_neuf`, `fi_neuf`, `pbv_usage`, `fi_usage` (fonction `vehicle_split_kpis`
  de `src/extract.py`, appelée après chaque calcul des indicateurs).
- Par unité : profit véhicule et F&I divisés par les unités détail ; « profit brut du département par unité » garde
  l'ancienne définition (avec F&I et gros). Sans séparation disponible : profit véhicule = profit brut, F&I = 0.
- Pont d'écart : par famille neufs / usagés = volume (écart d'unités × (véhicule + F&I) par unité de l'an passé), marge
  véhicule par unité, F&I par unité, non décomposé ; famille « Gros et encan » = écart du montant (jamais divisé par les
  unités détail). Le pont du Groupe additionne ceux des concessions (pas d'effet de mix).
- Ces clés ne vont pas dans le gabarit budgets.csv (pas de budget par composante).

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

### Opérations fixes — 29 septembre 2026
- Demande du client : approfondir les résultats des opérations fixes ($ par BT client, garantie, interne ; heures par BT).
- Le travail du 28 septembre sur ce sujet (zip `depot-github-kpi.zip`) n'avait jamais été déposé sur GitHub : refait.
- Ajouts : `src/apres_vente.py` (lecteurs), `src/fo_dashboard.js` (onglet « Opérations fixes » du tableau de bord :
  Bons de travail, Atelier et heures, Pièces, Tendances), `reports/mensuel/kpi_apres_vente.py`, `rapport_apres_vente.py`,
  `rapport_apres_vente_concession.py` (un rapport par concession, demandé le 29 septembre).
- `src/extract.py` : lecture des opérations fixes pour chaque fichier ; règles du 28 septembre refaites (classeur vide
  jamais retenu seul ; deux copies d'un même fichier : seule la plus récemment modifiée dans Drive est classée) ;
  fonction `main()` (même appel qu'avant en ligne de commande).
- Même jour : séparation profit véhicule / F&I / gros refaite (perdue avec le zip du 28 sept.) ; chiffres identiques
  à la version du 28 (cumul août 2026 : profit véhicule usagé Groupe 1 609 $/u, F&I usagé 1 318 $/u, véhicule neuf
  1 604 $/u, F&I neuf 590 $/u, F&I total 2,87 M$, gros 2,90 M$). EBT inchangé (août 578 670 $, cumul 6 436 502 $).
- Tableau de bord : résumé des filtres tronqué sur téléphone (débordait de 64 px).
