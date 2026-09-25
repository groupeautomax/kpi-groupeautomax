# -*- coding: utf-8 -*-
"""
Analyse du rapport mensuel KPI : regroupements, alertes, contrôle de qualité
des données, commentaires automatiques (en français).
"""
import statistics
from collections import OrderedDict

from kpi_data import (DEALERS, DEALER_SHORT, DEPTS, MOIS, BRIDGE_ITEMS, GPA_PLAUSIBLE_MAX,
                      add_comps, bridge, bridge_sum, bridge_families, bridge_label, ratios,
                      pkey, split, prev_month, prior_year, label_period)

NNBSP = " "   # espace fine insécable (milliers)
NBSP = " "
MINUS = "−"

# ------------------------------------------------------------ seuils
SEUILS = {
    "ebt_cumul_ap_pct": -0.15,     # EBT cumulatif sous l'AP de plus de 15 %…
    "ebt_cumul_ap_abs": -100000,   # …et de plus de 100 k$
    "ebt_cumul_budget_pct": -0.10, # EBT cumulatif sous le budget de plus de 10 %
    "ebt_mois_ap_pct": -0.25,      # EBT du mois sous l'AP de plus de 25 %…
    "ebt_mois_ap_abs": -50000,     # …et de plus de 50 k$
    "gpa_neuf_pct": -0.15,         # profit par unité neuve (cumul) en baisse de plus de 15 %
    "gpa_usage_pct": -0.20,        # profit par unité usagée (cumul) en baisse de plus de 20 %
    "pers_pct_pb_pts": 0.03,       # personnel % PB (cumul) en hausse de plus de 3 points
    "positif_ap_pct": 0.15,        # EBT cumulatif au-dessus de l'AP de plus de 15 %
    "positif_budget_pct": 0.05,    # EBT cumulatif au-dessus du budget de plus de 5 %
}
STATUTS = [  # (seuil minimum de variation EBT cumul vs AP, libellé, classe)
    (0.10, "En croissance", "good"),
    (-0.05, "Stable", "neutral"),
    (-0.20, "À surveiller", "warn"),
    (-9e9, "Prioritaire", "bad"),
]


# ------------------------------------------------------------ formats
def _grp(n):
    s = f"{abs(int(round(n))):,}".replace(",", NNBSP)
    return s


def money(x, sign=False, dash="—"):
    if x is None:
        return dash
    s = _grp(x) + NBSP + "$"
    if x < 0 and round(x) != 0:
        return MINUS + s
    if sign and round(x) > 0:
        return "+" + s
    return s


def kmoney(x, sign=False, dash="—", dec=None):
    """Montant compact : 12 k$, 1,32 M$."""
    if x is None:
        return dash
    a = abs(x)
    if a >= 1e6:
        s = f"{a/1e6:.2f}".replace(".", ",") + NBSP + "M$"
    elif a >= 1e3:
        d = 0 if dec is None else dec
        s = f"{a/1e3:,.{d}f}".replace(",", NNBSP).replace(".", ",") + NBSP + "k$"
    else:
        s = f"{a:.0f}" + NBSP + "$"
    if x < 0 and round(a) != 0:
        return MINUS + s
    if sign and round(a) != 0:
        return "+" + s
    return s


def num(x, dec=0, sign=False, dash="—"):
    if x is None:
        return dash
    if dec == 0:
        s = _grp(x)
    else:
        s = f"{abs(x):,.{dec}f}".replace(",", NNBSP).replace(".", ",")
    if x < 0 and round(abs(x), dec) != 0:
        return MINUS + s
    if sign and round(x, dec) > 0:
        return "+" + s
    return s


def pct(x, dec=1, sign=False, dash="—"):
    if x is None:
        return dash
    return num(x * 100, dec, sign) + NBSP + "%"


def pts(x, dec=1, sign=True, dash="—"):
    """Écart en points de pourcentage."""
    if x is None:
        return dash
    return num(x * 100, dec, sign) + NBSP + "pts"


def var_pct(r, b):
    """Variation relative ; None si la base est nulle ou négative (non significatif)."""
    if r is None or b is None or b <= 0:
        return None
    return r / b - 1


def de(m):
    """« de mars », « d'avril »."""
    w = MOIS[m]
    return ("d'" if w[0] in "aeiouéè" else "de ") + w


# ------------------------------------------------------------ regroupements
def group_real(s, period, mode):
    inc = [d for d in DEALERS if s.comp(d, period, mode, "real")]
    return add_comps([s.comp(d, period, mode, "real") for d in inc]), inc


def group_pair(s, period, mode, base):
    """Réel et base du groupe à périmètre comparable (seules les concessions
    qui ont la base entrent dans la comparaison)."""
    inc = [d for d in DEALERS if s.comp(d, period, mode, "real") and s.comp(d, period, mode, base)]
    if not inc:
        return None, None, []
    return (add_comps([s.comp(d, period, mode, "real") for d in inc]),
            add_comps([s.comp(d, period, mode, base) for d in inc]), inc)


def group_bridge(s, period, mode, base):
    """Pont du groupe = somme des ponts des concessions (tient compte du mix)."""
    bs = []
    for d in DEALERS:
        r, b = s.comp(d, period, mode, "real"), s.comp(d, period, mode, base)
        if r and b:
            bs.append(bridge(r, b))
    return bridge_sum(bs)


def statut(v):
    if v is None:
        return ("n/d", "neutral")
    for seuil, lab, cls in STATUTS:
        if v >= seuil:
            return (lab, cls)
    return STATUTS[-1][1:]


# ------------------------------------------------------------ série mensuelle
def monthly_series(s, dealer, year, last_month, base="real"):
    out = []
    for m in range(1, last_month + 1):
        p = pkey(year, m)
        c = s.comp(dealer, p, "month", base)
        out.append((p, c["ebt"] if c else None))
    return out


def r12_ebt(s, dealer, period):
    """EBT des 12 derniers mois (somme des mois ; None s'il en manque un)."""
    tot, p = 0.0, period
    for _ in range(12):
        c = s.comp(dealer, p, "month", "real")
        if not c:
            return None
        tot += c["ebt"]
        p = prev_month(p)
    return tot


def rank(values):
    """{clé: rang} (1 = plus grande valeur), valeurs None ignorées."""
    items = sorted([(k, v) for k, v in values.items() if v is not None], key=lambda kv: -kv[1])
    return {k: i + 1 for i, (k, _) in enumerate(items)}


# ------------------------------------------------------------ commentaires
FAMILLE_PB = {"neuf_vol", "neuf_marge", "neuf_nd", "usage_vol", "usage_marge", "usage_nd", "service", "carrosserie", "pieces", "pb_autres", "ar"}


def phrase_poste(key, val, b, real=None, base=None):
    """Formulation d'un facteur d'écart, ex. « recul du profit par unité neuve (−52 k$) »."""
    km = kmoney(val, sign=True)
    nd = getattr(b, "non_decompose", set())
    if key == "neuf_vol" and real and base:
        du = real["u_neuf"] - base["u_neuf"]
        return f"{'hausse' if du > 0 else 'baisse'} du volume de neufs ({num(du, sign=True)} unités, {km})"
    if key == "usage_vol" and real and base:
        du = real["u_usage"] - base["u_usage"]
        return f"{'hausse' if du > 0 else 'baisse'} du volume d'usagés ({num(du, sign=True)} unités, {km})"
    if key == "neuf_marge":
        return f"profit par unité neuve {'en hausse' if val > 0 else 'en recul'} ({km})"
    if key == "usage_marge":
        return f"profit par unité usagée {'en hausse' if val > 0 else 'en recul'} ({km})"
    if key == "neuf_nd":
        return f"profit brut des neufs {'en hausse' if val > 0 else 'en recul'} ({km})"
    if key == "usage_nd":
        return f"profit brut des usagés {'en hausse' if val > 0 else 'en recul'} ({km})"
    if key in ("service", "carrosserie", "pieces"):
        lab = {"service": "du service", "carrosserie": "de la carrosserie", "pieces": "des pièces"}[key]
        return f"profit brut {lab} {'en hausse' if val > 0 else 'en recul'} ({km})"
    if key == "pb_autres":
        return f"autres sources de profit brut {'en hausse' if val > 0 else 'en recul'} ({km})"
    if key == "ar":
        return f"autres revenus {'en hausse' if val > 0 else 'en recul'} ({km})"
    lab = {"dep_var": "dépenses variables", "dep_pers": "dépenses de personnel",
           "dep_semi": "dépenses semi-fixes", "dep_autres": "autres dépenses",
           "sous_baiia": "amortissement et éléments sous le BAIIA"}[key]
    return f"{lab} {'plus basses' if val > 0 else 'plus élevées'} ({km})"


def top_facteurs(b, n=3, real=None, base=None):
    items = sorted(b.items(), key=lambda kv: -abs(kv[1]))
    return [(k, v, phrase_poste(k, v, b, real, base)) for k, v in items[:n] if abs(v) >= 1000]


def base_label(base, period=None, mode=None):
    if base == "budget":
        return "le budget"
    if period:
        y, m = split(period)
        return f"{MOIS[m]} {y-1}" if mode == "month" else f"l'an passé"
    return "l'an passé"


def commentaire_ecart(nom, real, basec, b, base, period, mode, n=3):
    """Une à deux phrases : niveau, écart, trois principaux facteurs."""
    if not (real and basec and b):
        return None
    d = real["ebt"] - basec["ebt"]
    vp = var_pct(real["ebt"], basec["ebt"])
    quand = f"en {MOIS[split(period)[1]]}" if mode == "month" else "depuis janvier"
    ref = "au budget" if base == "budget" else ("à " + (f"{MOIS[split(period)[1]]} {split(period)[0]-1}" if mode == "month" else "la même période l'an passé"))
    vtxt = f" ({pct(vp, 0, sign=True)})" if vp is not None else ""
    t = f"EBT de {kmoney(real['ebt'])} {quand}, soit {kmoney(d, sign=True)}{vtxt} par rapport {ref}."
    f = top_facteurs(b, n, real, basec)
    fav = [x[2] for x in f if x[1] > 0]
    dfav = [x[2] for x in f if x[1] < 0]
    parts = []
    if dfav:
        parts.append("En défaveur : " + " ; ".join(dfav) + ".")
    if fav:
        parts.append("En faveur : " + " ; ".join(fav) + ".")
    return t + " " + " ".join(parts)


# ------------------------------------------------------------ alertes
NIVEAUX = {"critique": 0, "eleve": 1, "attention": 2, "positif": 3}


def alertes(s, period):
    out = []
    for d, nom in DEALERS.items():
        rm, am = s.comp(d, period, "month", "real"), s.comp(d, period, "month", "ap")
        ry, ay = s.comp(d, period, "ytd", "real"), s.comp(d, period, "ytd", "ap")
        by = s.comp(d, period, "ytd", "budget")
        if not rm or not ry:
            continue
        fired_month = False
        if rm["ebt"] < 0:
            out.append((d, "critique", f"EBT du mois négatif ({kmoney(rm['ebt'])})."))
            fired_month = True
        if ay:
            dv, vp = ry["ebt"] - ay["ebt"], var_pct(ry["ebt"], ay["ebt"])
            if vp is not None and vp <= SEUILS["ebt_cumul_ap_pct"] and dv <= SEUILS["ebt_cumul_ap_abs"]:
                out.append((d, "eleve", f"EBT cumulatif {kmoney(dv, sign=True)} ({pct(vp, 0, sign=True)}) par rapport à l'an passé."))
            elif vp is not None and vp >= SEUILS["positif_ap_pct"]:
                out.append((d, "positif", f"EBT cumulatif {kmoney(dv, sign=True)} ({pct(vp, 0, sign=True)}) par rapport à l'an passé."))
        if by:
            dv, vp = ry["ebt"] - by["ebt"], var_pct(ry["ebt"], by["ebt"])
            if vp is not None and vp <= SEUILS["ebt_cumul_budget_pct"]:
                out.append((d, "eleve", f"EBT cumulatif {kmoney(dv, sign=True)} ({pct(vp, 0, sign=True)}) sous le budget."))
            elif vp is not None and vp >= SEUILS["positif_budget_pct"]:
                out.append((d, "positif", f"EBT cumulatif {kmoney(dv, sign=True)} ({pct(vp, 0, sign=True)}) au-dessus du budget."))
        if am and not fired_month:
            dv, vp = rm["ebt"] - am["ebt"], var_pct(rm["ebt"], am["ebt"])
            if vp is not None and vp <= SEUILS["ebt_mois_ap_pct"] and dv <= SEUILS["ebt_mois_ap_abs"]:
                out.append((d, "attention", f"EBT du mois {kmoney(dv, sign=True)} ({pct(vp, 0, sign=True)}) par rapport à {MOIS[split(period)[1]]} {split(period)[0]-1}."))
        rr = ratios(rm)
        if rr.get("dep_pct_pb") and rr["dep_pct_pb"] > 1:
            out.append((d, "attention", f"Dépenses du mois supérieures au profit brut ({pct(rr['dep_pct_pb'], 0)} du PB) : l'EBT repose sur les autres revenus."))
        if ay:
            ry_r, ay_r = ratios(ry), ratios(ay)
            for k, lab, seuil in (("gpa_neuf", "neuve", SEUILS["gpa_neuf_pct"]), ("gpa_usage", "usagée", SEUILS["gpa_usage_pct"])):
                a, r = ay_r.get(k), ry_r.get(k)
                if a and r and abs(a) <= GPA_PLAUSIBLE_MAX:
                    vp = r / a - 1
                    if vp <= seuil:
                        out.append((d, "attention", f"Profit brut par unité {lab} (cumul) de {money(r)}, {pct(vp, 0, sign=True)} vs l'an passé ({money(a)})."))
            a, r = ay_r.get("pers_pct_pb"), ry_r.get("pers_pct_pb")
            if a is not None and r is not None and r - a >= SEUILS["pers_pct_pb_pts"]:
                out.append((d, "attention", f"Personnel à {pct(r, 0)} du profit brut (cumul), {pts(r - a, 0)} vs l'an passé."))
    out.sort(key=lambda x: (NIVEAUX[x[1]], list(DEALERS).index(x[0])))
    return out


# ------------------------------------------------------------ qualité des données
def controle_donnees(s, period):
    """Couverture par concession + liste d'anomalies et d'actions."""
    y, m = split(period)
    couverture = OrderedDict()
    anomalies = []   # (concession, gravité, constat, action)
    for d, nom in DEALERS.items():
        row = {}
        row["reel_mois"] = s._native_section(d, period, "month") is not None
        row["reel_cumul"] = s._native_section(d, period, "ytd") is not None
        row["budget"] = s.budget_source(d, period, "ytd")
        row["ap"] = s.ap_source(d, period, "ytd")
        manquants = [pkey(y, i) for i in range(1, m + 1) if s._native_section(d, pkey(y, i), "month") is None]
        row["mois_manquants"] = manquants
        # révisions : cumul(M) − cumul(M−1) − mois(M)
        rev = None
        if m > 1:
            a = s._native_section(d, period, "ytd")
            b = s._native_section(d, prev_month(period), "ytd")
            c = s._native_section(d, period, "month")
            if a and b and c:
                rev = {}
                for k in ("ventes_nettes", "pb_total", "ebt"):
                    rev[k] = a["kpis"][k]["real"] - b["kpis"][k]["real"] - c["kpis"][k]["real"]
        row["revisions"] = rev
        couverture[d] = row

        # --- anomalies
        if not row["budget"]:
            fmt = s.source_format(d, period)
            why = {"etat_gm": "l'état financier GM ne contient aucune colonne budget",
                   "etat_hyundai": "l'état financier Hyundai Canada ne contient aucune colonne budget"}.get(fmt) or \
                {"hyundai": "les colonnes budget du fichier sont à zéro",
                 "stm": "le fichier ne contient pas de budget"}.get(d, "aucun budget dans le fichier")
            anomalies.append((d, "manque", f"Budget {y} absent : {why}.",
                              f"Obtenir le budget mensuel {y} et le saisir dans budgets.csv (gabarit fourni)."))
        if not row["ap"]:
            anomalies.append((d, "manque", "Aucune comparaison possible avec l'an passé.", "Téléverser les fichiers de l'an passé."))
        # mois manquants, regroupés en plages consécutives
        runs = []
        for p in manquants:
            yy, mm = split(p)
            if runs and runs[-1][1] == mm - 1:
                runs[-1][1] = mm
            else:
                runs.append([mm, mm])
        for a_, b_ in runs:
            if a_ == b_:
                p = pkey(y, a_)
                file_exists = s._native_section(d, p, "ytd") is not None
                deriv = s.comp(d, p, "month", "real") is not None
                if file_exists:
                    anomalies.append((d, "valider", f"Fichier {de(a_)} {y} : section « mois » vide ; le mois est repris du cumul.",
                                      "Aucune action si le fichier est complet ; sinon le remplacer."))
                else:
                    anomalies.append((d, "manque", f"Réalisé {de(a_)} {y} absent" + (" — mois reconstitué à partir des cumuls voisins pour les tendances." if deriv else "."),
                                      f"Téléverser le Réalisé {de(a_)} {y} dans sources/."))
            else:
                anomalies.append((d, "manque", f"Réalisés {de(a_)} à {MOIS[b_]} {y} absents (le cumul annuel les inclut ; seules les tendances mensuelles sont incomplètes).",
                                  f"Téléverser les Réalisés {de(a_)} à {MOIS[b_]} {y} si disponibles."))
        if rev:
            if abs(rev["ebt"]) >= 25000 or abs(rev["pb_total"]) >= 50000:
                parts = [f"{lab} {kmoney(rev[k], sign=True)}" for k, lab in (("ventes_nettes", "ventes"), ("pb_total", "PB"), ("ebt", "EBT")) if abs(rev[k]) >= 1000]
                anomalies.append((d, "info", f"Le cumul {de(m)} intègre des révisions aux mois antérieurs : " + ", ".join(parts) + ".",
                                  "Normal en comptabilité ; les mois déjà publiés ne sont pas retraités."))

        # historique : doublons de mois, cumul = mois hors janvier
        ps = s.periods(d)
        for p in ps:
            yy, mm = split(p)
            if yy < y - 1:
                continue
            sec_m, sec_y = s._native_section(d, p, "month"), s._native_section(d, p, "ytd")
            nxt = s._native_section(d, pkey(yy, mm + 1), "month") if mm < 12 else None
            if sec_m and nxt:
                a, b = sec_m["kpis"]["ventes_nettes"]["real"], nxt["kpis"]["ventes_nettes"]["real"]
                ya = sec_y and sec_y["kpis"]["ventes_nettes"]["real"]
                yb_sec = s._native_section(d, pkey(yy, mm + 1), "ytd")
                yb = yb_sec and yb_sec["kpis"]["ventes_nettes"]["real"]
                if a and b and ya and yb and abs(ya - yb) / abs(yb) < 0.002:
                    anomalies.append((d, "erreur", f"Le fichier {de(mm)} {yy} contient les données {de(mm+1)} {yy} (cumuls identiques).",
                                      f"Remplacer le Réalisé {de(mm)} {yy} dans sources/. Seules les tendances sont touchées : les comparaisons {de(mm)} {y} utilisent la colonne AP du fichier {y}."))
            if sec_m and sec_y and mm > 1:
                a, ya = sec_m["kpis"]["ventes_nettes"]["real"], sec_y["kpis"]["ventes_nettes"]["real"]
                if a and ya and abs(a - ya) < 1:
                    anomalies.append((d, "erreur", f"Fichier {de(mm)} {yy} : le cumul annuel est égal au mois seul.",
                                      f"Vérifier le fichier {de(mm)} {yy} ; son cumul annuel n'est pas utilisé."))

        # anomalies de postes (année en cours), regroupées par type
        credits, pb_neg = [], []
        for i in range(1, m + 1):
            p = pkey(y, i)
            c = s.comp(d, p, "month", "real")
            if not c:
                continue
            if c["dep_var"] < -5000:
                credits.append(f"{MOIS[i]} ({kmoney(-c['dep_var'])})")
            if c["pb_usage"] < 0:
                pb_neg.append(f"{MOIS[i]} ({kmoney(c['pb_usage'])})")
        if credits:
            anomalies.append((d, "valider", f"Dépenses variables nettes créditrices en {' et '.join(credits)} {y}.",
                              "Valider avec le contrôleur (crédit du fabricant ou reclassement?)."))
        if pb_neg:
            anomalies.append((d, "valider", f"Profit brut des usagés négatif en {' et '.join(pb_neg)} {y}.",
                              "Valider (dévaluation d'inventaire ou écriture de fin de période?)."))
        pers = [s.comp(d, pkey(y, i), "month", "real") for i in range(1, m + 1)]
        pers_vals = [c["dep_pers"] for c in pers if c]
        if len(pers_vals) >= 4:
            med = statistics.median(pers_vals)
            for i in range(1, m + 1):
                c = s.comp(d, pkey(y, i), "month", "real")
                if c and med > 0 and c["dep_pers"] < 0.4 * med:
                    anomalies.append((d, "valider", f"{MOIS[i].capitalize()} {y} : dépenses de personnel anormalement basses ({kmoney(c['dep_pers'])} contre une médiane de {kmoney(med)}).",
                                      "Valider (renversement de provision?)."))
        # reclassement probable entre variables et personnel (cumul vs AP)
        ry, ay = s.comp(d, period, "ytd", "real"), s.comp(d, period, "ytd", "ap")
        if ry and ay:
            dv, dp = ry["dep_var"] - ay["dep_var"], ry["dep_pers"] - ay["dep_pers"]
            if abs(dv) > 200000 and abs(dp) > 200000 and dv * dp < 0:
                anomalies.append((d, "valider", f"Écarts opposés sur l'année : dépenses variables {kmoney(dv, sign=True)}, personnel {kmoney(dp, sign=True)} vs l'an passé — probable reclassement de postes.",
                                  "Lire le total des dépenses plutôt que les catégories ; confirmer avec le contrôleur."))
            for k, lab in (("u_neuf", "neuves"), ("u_usage", "usagées")):
                pbk = "pb_neuf" if k == "u_neuf" else "pb_usage"
                if ay[k] and abs(ay[pbk] / ay[k]) > GPA_PLAUSIBLE_MAX:
                    anomalies.append((d, "valider", f"Unités {lab} de l'an passé probablement incomplètes : profit par unité de {money(ay[pbk]/ay[k])} en {y-1}.",
                                      "Le pont d'écart ne sépare pas volume et profit par unité pour ce poste."))
    ordre = {"erreur": 0, "manque": 1, "valider": 2, "info": 3}
    anomalies.sort(key=lambda a: (ordre[a[1]], list(DEALERS).index(a[0])))
    return couverture, anomalies
