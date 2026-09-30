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
- `Rapport_Ventes_AAAA-MM.pdf` — analyse approfondie des ventes de véhicules du Groupe (environ 16 pages) :
  `python rapport_ventes.py --data ../../data/data.json --mois AAAA-MM --sortie sortie`
- `Rapport_Ventes_<Concession>_AAAA-MM.pdf` — un rapport Ventes par concession (environ 11 à 13 pages) :
  `python rapport_ventes_concession.py --data ../../data/data.json --mois AAAA-MM --sortie sortie`
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
- BMW (demande du client, 29 septembre 2026) : types de BT pris dans l'état BMW Canada (« AAAA-MM MANUF BMW Sher.xlsm »,
  dossier « b) États financiers » de BMW, synchronisé par `drive_sync.py`), feuille « FS Data » (code = page × 100 000 +
  ligne × 100 + colonne) : page 8 (retours inscrits = BT, ventes, bénéfice brut ; mois col. 12/14/16, cumul 22/24/26),
  page 9 (pièces), page 10 (taux affichés, « taux de main-d'œuvre en vigueur » = taux effectif déclaré, techniciens,
  jours de service). Types : client (460A/B/D), **entretien BMW** (461D/E/G, BMW Service Inclus + 478A), garantie
  (461A/B/H), interne (462A/B/D), esthétique = programme SPA (459A). Format `etat_bmw` (rang −2 : jamais la source du
  mois) ; repris dans le Réalisé retenu par `merge_manufacturer_fixed_ops` (état dont la M-O client concorde à ± 2 %).
  Le reste du Réalisé (sous-traitance, pièces par canal, P&L) est gardé. Budget du Réalisé gardé pour client et
  esthétique seulement ; « an passé » = état BMW de l'an passé. État de décembre 2025 : colonnes « cumul » = décembre
  seulement → cumul refait (cumul de novembre + décembre). Pas d'heures vendues dans l'état : page Atelier = taux affichés,
  taux effectif déclaré et heures estimées (M-O ÷ taux effectif).

## Composites des constructeurs — règles (29 septembre 2026)

- Demande du client : « il faut que les comparaisons [au composite] soient ajoutées au rapport » ; composites reçus :
  Hyundai (eComposite « ÉF ‐ Sommaire », « P&P » et « Analyse des revenus ») et Volkswagen (« Dealer Report Card ») ;
  BMW et GM à venir. Le client dépose les PDF dans les dossiers Drive des concessions, avec le Réalisé et les états.
- Lecture : `src/composites.py` (PDF → JSON). Les PDF ne vont JAMAIS dans le dépôt : seuls les chiffres, dans
  `sources/composites/<concession>_<AAAA-MM>_<type>.json` (types `hyundai_ef`, `hyundai_pp`, `hyundai_ar`,
  `vw_report_card`). `drive_sync.py` télécharge les PDF des Drive des concessions dont le nom contient « composite »,
  « report card », « scorecard », « dealer report » ou « ÉF ‐ Sommaire » (pas « sommaire » seul : sommaires de relevés
  et de TPS-TVQ), les lit dans un fichier temporaire et écrit le JSON. PDF non reconnu : noté dans le manifeste avec
  `parser_version` ; relu seulement s'il change sur Drive ou si `PARSER_VERSION` de `src/composites.py` augmente
  (l'augmenter à chaque amélioration de la lecture). À la main : `python src/composites.py fichier.pdf …`.
- Libellés : `norm()` ramène « œ » à « oe » (« Main‐d'œuvre » du composite = « MAIN-D'OEUVRE » de l'état).
- `extract.py` (`load_composites`) → `data.json["composites"][concession][mois][type]`. Hyundai : le composite ne donne
  que les moyennes du groupe (ex. « Est A (850+) », 16 concessions) ; les chiffres de Hyundai Longueuil aux mêmes
  définitions sont calculés à partir de l'état Hyundai Canada du mois (`composites.hyundai_statement_lines`, clé
  `concession`). Définitions vérifiées sur les moyennes d'août 2026 : profit net avant bonis = profit net avant impôt +
  salaire et bonis des propriétaires ; absorption = PB pièces + service + carrosserie ÷ (frais total − frais de vente des
  véhicules) ; publicité = publicité véhicules + publicité pièces-service ; PVND / PVOD = bureau commercial ÷ unités
  détail. Lubrifiants laissés au service (comme l'état), contrairement au reste du rapport.
- Postes P&P : table `PP_LINES` (composite ↔ état, même ordre de lignes). Postes comparés en % du profit brut ; « effet »
  = écart de ratio × PB de la concession. Page des dépenses : postes comparés au total de la concession (frais fixes
  répartis entre départements à la façon de chaque concession : Hyundai Longueuil met le loyer en parts égales) ; frais
  d'emploi en sous-total (Hyundai Longueuil inscrit les charges sociales dans les avantages sociaux).
- Pages (`reports/mensuel/rapport_composite.py`) : rapport de Hyundai (sommaire vs groupe + dépenses en % du PB), de VW
  (bulletin : classement, indicateurs et points ; ventes, F&I et CEM), rapports Opérations fixes de Hyundai et de VW
  (service et pièces), rapport du Groupe (« Nos concessions face à leur réseau », avec l'état des composites reçus) et
  rapport Opérations fixes du Groupe (« Après-vente face aux composites »). Plus d'encadrés « Bravo / À améliorer » sur ces
  pages : leurs meilleurs et pires écarts alimentent la page « 3 étoiles et 3 points à améliorer » (voir plus bas). Pages
  aérées (classe `comp` : police 9 pt, rangées de 6 px ; pages denses scindées en deux).
  Analyse des revenus (`hyundai_ar`, postes `AR_LINES`) : page « Main-d'œuvre et pièces par type de travail » du
  rapport Opérations fixes de Hyundai (BT client / garantie / interne : nombre, $ par BT, marge ; pièces par type) ;
  Hyundai Longueuil : page 4 de l'état (colonnes unités / ventes / PB). Pièces « par BT » = ventes de pièces du type ÷
  BT de main-d'œuvre du même type. Écart de PB = PB réel − PB au ratio du groupe (PB par BT, sinon marge). Escompte /
  boni pour ventes en gros : hors marge des ventes en gros (comme le composite), compris dans le total pièces.
  Aucun composite pour le mois : aucune page, et l'entrée est retirée du sommaire du Groupe.
- Vérification d'août 2026 : 1 724 valeurs du composite Hyundai et 256 du bulletin VW relues par un 2e lecteur
  (pdftotext), 486 valeurs de Hyundai Longueuil relues cellule par cellule dans l'état : 0 écart. Analyse des revenus :
  674 lignes (4 colonnes chacune) relues par pdftotext, 0 écart.

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

## Envoi aux directeurs le 20 du mois (demande du client, 29 septembre 2026)

- Workflow GitHub « Rapports mensuels par courriel » (`.github/workflows/rapports-mensuels.yml`), le 20 à 14 h 07 UTC :
  `envoi_rapports.py` vise le mois précédent et, pour chaque concession dont le fichier du mois est dans data.json,
  produit `Rapport_<Concession>_AAAA-MM.pdf`, `Rapport_Operations_fixes_<Concession>_AAAA-MM.pdf` et
  `Rapport_Ventes_<Concession>_AAAA-MM.pdf` (ajouté le 29 septembre 2026, accord du client), puis les envoie au
  script Apps Script « Envoi rapports KPI » de Maxime (web app, compte mallard@groupeautomax.com), qui les expédie au
  directeur de la concession, Maxime en copie, puis envoie à Maxime un résumé (envoyés, en attente, avertissements).
- Chaque directeur reçoit seulement les rapports de sa concession (3 PDF) ; les rapports du Groupe restent pour Maxime.
- Chaque fichier envoyé porte son `libelle` (dictionnaire `LIBELLES` d'`envoi_rapports.py`), affiché tel quel dans le
  courriel par le script Apps Script (version 3 du déploiement, 29 septembre 2026) : un nouveau rapport n'exige plus de
  modifier le script.
- Concession sans données du mois : pas d'envoi, signalée dans le résumé. Relance manuelle (Actions → Run workflow) :
  seules les concessions pas encore envoyées partent ; `essai = oui` : tout part à Maxime seulement ; `forcer = oui` : renvoi.
- Secrets GitHub : `APPS_SCRIPT_URL`, `RAPPORTS_TOKEN`. Les adresses des directeurs sont dans le script Apps Script,
  jamais dans ce dépôt (public) ; le journal des Actions n'affiche que les codes de concession et les statuts.

## Limites connues

- Le rapport détecte et affiche lui-même (page « Qualité et couverture des données ») les budgets absents, les mois
  manquants, l'an passé reconstitué, les révisions de cumul et les anomalies de postes : ne pas les corriger à la main.
- Un `budgets.csv` (gabarit : `python rapport_kpi.py --gabarit-budget budgets.csv --annee 2026`) peut compléter les
  budgets manquants. Il contient des données confidentielles : il ne va jamais dans ce dépôt public (le garder dans Google Drive).
- Le dépôt est public : ne jamais y déposer les PDF ni les HTML générés.

## 3 étoiles et 3 points à améliorer — règles (29 septembre 2026)

- Demande du client : « je veux dans chaque rapport 3 étoiles pour les meilleures stats et trois points à améliorer ;
  aussi c'est trop condensé ». Une page par rapport, juste après le sommaire (`reports/mensuel/rapport_etoiles.py`) :
  rapport mensuel et Opérations fixes de chaque concession, rapport du Groupe et Opérations fixes du Groupe.
- Candidats, cumul depuis janvier : chaque indicateur vs la même période de l'an passé ; EBT vs budget s'il existe ;
  comparaisons au composite (`rapport_composite.etoiles_*` : Hyundai vs moyenne du groupe, VW vs moyenne nationale,
  rang national VW). Score = écart relatif dans le sens favorable, plafonné à ±150 %, × poids (EBT 1 ; composite 0,6).
- Sélection : 3 + 3, une seule fois chaque famille (neufs, usagés, F&I, dépenses, un type de BT…), au plus 2
  comparaisons au composite ; rapports du Groupe : au plus 2 éléments propres à une concession. Seuils de matérialité
  (20 k$ par concession, 50 k$ Groupe, ½ point, 5 unités, 20 unités pour un montant par unité) ; s'il en manque, 2e passe
  aux seuils × 0,25, puis comparaison à l'ensemble du Groupe, puis « progression la plus faible » (points à améliorer
  seulement, affichés en gris).
- Exclus : frais d'emploi du composite (classement des charges sociales), profit d'opération nul (frais répartis
  jusqu'à l'équilibre).
- Vérification d'août 2026 : EBT, ventes, unités et montants par unité des étoiles recalculés à partir de data.json
  (sans kpi_data) : identiques.

## Rapports « Ventes de véhicules » — règles (29 septembre 2026)

- Demande du client : « fais un rapport détaillé pour les ventes comme tu as fait pour les fixes ». Deux scripts, même
  principe que les Opérations fixes : `rapport_ventes.py` (Groupe, ~16 pages, `Rapport_Ventes_AAAA-MM.pdf`) et
  `rapport_ventes_concession.py` (une par concession, 11 à 13 pages, `Rapport_Ventes_<concession>_AAAA-MM.pdf`).
  Données : `kpi_ventes.py`, qui lit data.json tel quel (aucune nouvelle extraction) : indicateurs (unités, profit
  véhicule, F&I, gros) et lignes des départements « Véhicules neufs » / « Véhicules usagés ».
- Lignes ramenées à des clés communes (`LINE_RULES`, `MIX_RULES`) : ventes nettes, commissions vendeurs et F&I,
  publicité nette (ristournes, coop), intérêts sur stocks nets (crédits du constructeur : souvent négatifs à l'état GM),
  préparation et livraison, F&I par produit (Réalisé seulement), ventes au gros (unités), lignes de modèles (autos,
  camions et VUS, électriques, fin de série ; usagés certifiés / non certifiés / autres marques).
- An passé : lignes comparées seulement si le fichier de l'an passé a le même format (`VStore.same_format`) ; Hyundai
  (Réalisé 2025, état Hyundai 2026) : unités, profit véhicule, F&I et gros comparés, frais, profit du département et
  modèles non. Groupe : sommes des concessions ; ratios sur les concessions qui ont numérateur et dénominateur.
- Pages : sommaire, 3 étoiles / 3 points (`rapport_etoiles.page_ventes_*`, candidats `ventes_cands`), neufs et usagés
  (volumes, profit par unité, budget BMW / VW), F&I, frais de vente et profit du département, positionnement (rang),
  composite (Hyundai : page véhicules ; VW : indicateurs ventes et page ventes du bulletin ; Groupe :
  `rapport_composite.page_ventes_groupe`), mix, gros / encan / export, détail mensuel, tendances 12 et 24 mois, méthode.
- Vérification d'août 2026 : commissions, intérêts, publicité, ventes, unités en gros, unités et F&I relus directement
  dans les lignes de data.json pour les 5 concessions : identiques.

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
- Soir : mention « heures vendues absentes » retirée des rapports et du tableau de bord (décision du client) ; état
  BMW Canada branché comme source des types de BT de BMW (voir « Opérations fixes — règles »). Effet sur le cumul
  d'août 2026 de BMW : garantie 885 BT (au lieu de 1 689, entretien à part : 804 BT), interne 1 138 BT à 458 $ par BT
  (au lieu de 1 437 BT à 365 $) ; client et SPA inchangés.
- Soir : composites des constructeurs ajoutés aux rapports (voir « Composites des constructeurs — règles ») :
  Hyundai (eComposite, groupe Est A (850+)) et VW (Dealer Report Card) d'août 2026 ; BMW et GM à venir. Ajout de
  l'« Analyse des revenus » Hyundai (déposée sur Drive) : page par type de travail au rapport Opérations fixes.
- Soir (2) : page « 3 étoiles et 3 points à améliorer » dans chaque rapport ; pages de comparaison aux composites aérées
  et scindées ; encadrés « Bravo / À améliorer » retirés de ces pages (repris dans la page des étoiles).
- Soir (3) : rapports « Ventes de véhicules » (Groupe et concessions) ; workflow « Update dashboard » : `git pull
  --rebase --autostash` avant le push (échec du 29 septembre : un commit était arrivé pendant la reconstruction).
- Soir (4) : le rapport Ventes de chaque concession part aussi aux directeurs le 20 (3 PDF par concession) ; libellés
  des rapports envoyés par `envoi_rapports.py`, script Apps Script mis à jour (version 3).
