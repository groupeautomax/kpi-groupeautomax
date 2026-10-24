# -*- coding: utf-8 -*-
"""Envoie les chiffres du tableau de bord KPI à ScanAutomax (22 octobre 2026).

Les chiffres viennent des Drive partagés des concessions (Réalisés, états
financiers des constructeurs) : src/drive_sync.py les tire dans sources/,
src/extract.py les lit dans data/data.json. Ce script prend data/data.json,
en garde l'essentiel (indicateurs du mois et du cumul, réel / budget / année
précédente, sommaire des départements, fichier source de chaque mois) et le
POSTE au script Apps Script de ScanAutomax (action kpiImporter). ScanAutomax
le garde derrière sa connexion : le site l'affiche dans Vente › KPI, avec la
portée de chaque compte (un directeur ne voit que sa concession).

Composite (24 octobre 2026, demande de Maxime : « les comparables avec le
composite du groupe comme dans le rapport de Mustafa doivent être dans les KPI,
comme le budget et l'année précédente ») : pour VW Brossard et Hyundai
Longueuil, chaque mois dont l'état du groupe constructeur est dans le Drive
reçoit un bloc « x » : la concession et le concessionnaire moyen de son groupe
(VW Canada groupe A, Hyundai Canada Est A), lus aux mêmes lignes de l'état
financier constructeur par reports/mensuel/analyse_composite.py — les chiffres
du rapport de Mustafa. Sans ce module (ou en cas d'erreur), l'envoi part sans
composite.

Rien n'est écrit dans le dépôt (il est public) : le fichier compact n'existe
que le temps de l'envoi.

Variables d'environnement (secrets GitHub Actions) :
  SCANAUTOMAX_KPI_JETON  jeton créé par KPI_genererJeton() dans l'éditeur
                         Apps Script de ScanAutomax (obligatoire ; absent =
                         rien n'est envoyé, le workflow continue).
  SCANAUTOMAX_URL        adresse /exec de ScanAutomax (facultatif).

Usage : python src/export_scanautomax.py [data/data.json] [--sortie fichier.json] [--essai]
  --sortie : écrit aussi le fichier compact (pour vérifier, pas dans le dépôt)
  --essai  : n'envoie rien
"""
import datetime
import json
import os
import sys
import urllib.request

URL_DEFAUT = ("https://script.google.com/macros/s/"
              "AKfycbwZsbAEELfW5Ce80l3v39unBI6L3js8IQ3iYilrGDNK2zUzlv16XxkoZYZuf4t3tgfX/exec")

# Clés du tableau de bord → codes de compagnie de ScanAutomax
CODES = {"bmw": "BMW", "stm": "STM", "hawks": "HAWKS", "vw": "VW", "hyundai": "HYUNDAI"}
NOMS = {"BMW": "BMW Sherbrooke", "STM": "Ste Marie Automobiles Ltée", "HAWKS": "Hawkesbury Chevrolet Buick Cadillac",
        "VW": "VW Brossard", "HYUNDAI": "Hyundai Longueuil"}
DEPT_METRIQUES = ["units", "units_flottes", "profit_brut", "total_variables", "total_personnel",
                  "total_semifixes", "total_depenses", "autres_revenus", "profit_departemental"]
CHAMPS = ("real", "budget", "prior_year")

# Composite : indicateur du tableau de bord → valeur d'analyse_composite (mêmes définitions pour la
# concession et le groupe). Les ratios sont recalculés ici comme sur le site (numérateur ÷ dénominateur).
COMPOSITE_INDICATEURS = {
    "pb_neuf": "pb_neuf", "pb_usage": "pb_occasion", "pb_service": "pb_service", "pb_pieces": "pb_pieces",
    "unites_neuf": "u_neuf", "unites_usage": "u_occ", "pb_total": "pb_total", "depenses": "frais_total",
    "profit_net": "pn", "ebt": "pn", "ventes_nettes": "ventes_total",
    "pbv_neuf": "pbav_neuf", "fi_neuf": "fi_neuf", "pbv_usage": "pbdet_occ", "fi_usage": "fi_occ", "gros_usage": "pb_gros",
}
COMPOSITE_RATIOS = {
    "ros": ("profit_net", "ventes_nettes"), "ebt_pct_profit_brut": ("profit_net", "pb_total"),
    "gpa_neuf": ("pb_neuf", "unites_neuf"), "gpa_usage": ("pb_usage", "unites_usage"),
    "pbv_unite_neuf": ("pbv_neuf", "unites_neuf"), "fi_unite_neuf": ("fi_neuf", "unites_neuf"),
    "pbv_unite_usage": ("pbv_usage", "unites_usage"), "fi_unite_usage": ("fi_usage", "unites_usage"),
}
COMPOSITE_NEGATIFS = {"depenses"}          # gardées négatives, comme dans le tableau de bord
COMPOSITE_DEPTS = {"neuf": "Véhicules neufs", "occasion": "Véhicules usagés", "service": "Service", "pieces": "Pièces"}
COMPOSITE_UNITES = {"neuf": "u_neuf", "occasion": "u_occ"}


# Indicateurs par unité et par bon de travail (24 octobre 2026, Maxime : « ne pas oublier les indicateurs clés par
# unité, par exemple par $ de vente de bon de travail »). Calculés ici à partir de sections.<mode>.apres_vente
# (src/apres_vente.py) et des indicateurs du mois, pour le réel, le budget et l'année précédente. Les sommes « cachées »
# (groupe « cache ») servent au site à recalculer les ratios du groupe : numérateurs ÷ dénominateurs, jamais une moyenne.
# Mêmes règles que l'onglet Opérations fixes du tableau de bord (src/fo_dashboard.js) : seuls les types de BT qui ont un
# nombre de BT entrent dans les ratios « par BT » ; heures : seulement les types qui en ont.
TYPES_BT = ("client", "garantie", "entretien", "interne", "esthetique")
INDICATEURS_UNITE = [
    # clé, libellé, groupe, format, (numérateur, dénominateur) ou None
    ("u_total", "Unités vendues (neuf + usagé)", "unite", "volume", None),
    ("pb_unite_total", "Profit brut par unité vendue (neuf + usagé, avec F&I et gros)", "unite", None, ("vh_pb", "u_total")),
    ("pn_unite", "Profit net par unité vendue", "unite", None, ("profit_net", "u_total")),
    ("dep_unite", "Dépenses par unité vendue", "unite", None, ("dep_abs", "u_total")),
    ("av_bt", "Bons de travail (tous types)", "apv", "volume", None),
    ("av_mo", "Ventes M-O sur les BT", "apv", None, None),
    ("av_pc", "Ventes de pièces sur les BT", "apv", None, None),
    ("av_tot_bt", "Vente par BT (M-O + pièces)", "apv", None, ("av_tot", "av_bt")),
    ("av_mo_bt", "Main-d'œuvre par BT", "apv", None, ("av_mo", "av_bt")),
    ("av_pc_bt", "Pièces par BT", "apv", None, ("av_pc", "av_bt")),
    ("av_pb_bt", "Profit brut par BT", "apv", None, ("av_pb", "av_bt")),
    ("av_pb_dollar", "Profit brut par $ de vente de BT", "apv", "percent", ("av_pb", "av_tot")),
    ("av_marge_mo", "Marge brute M-O", "apv", "percent", ("av_mopb", "av_mo")),
    ("av_pc_mo", "Pièces vendues par $ de M-O", "apv", "dec2", ("av_pc", "av_mo")),
    ("av_bt_client", "Bons de travail client", "apv", "volume", None),
    ("av_tot_bt_client", "Vente par BT client (M-O + pièces)", "apv", None, ("av_tot_client", "av_bt_client")),
    ("av_mo_bt_client", "Main-d'œuvre par BT client", "apv", None, ("av_mo_client", "av_bt_client")),
    ("av_pb_bt_client", "Profit brut par BT client", "apv", None, ("av_pb_client", "av_bt_client")),
    ("av_h", "Heures vendues sur les BT", "apv", "volume", None),
    ("av_h_bt", "Heures vendues par BT", "apv", "dec2", ("av_h", "av_h_n")),
    ("av_elr", "Taux effectif (M-O ÷ heure vendue)", "apv", None, ("av_h_mo", "av_h")),
    ("av_marge_pieces", "Marge brute du département Pièces", "apv", "percent", ("av_pieces_pb", "av_pieces_v")),
    ("av_carr_bt", "Vente carrosserie par BT", "apv", None, ("av_carr_v", "av_carr_n")),
]
CACHES_UNITE = ("vh_pb", "dep_abs", "av_tot", "av_pb", "av_mopb", "av_tot_client", "av_mo_client", "av_pb_client",
                "av_h_n", "av_h_mo", "av_pieces_v", "av_pieces_pb", "av_carr_v", "av_carr_n")


def _champ(kv, f):
    if not isinstance(kv, dict):
        return None
    v = kv.get(f)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v else None


def _somme(*vals):
    v = [x for x in vals if x is not None]
    return sum(v) if v else None


def par_unite(sec, f):
    """{ clé: valeur } pour un champ (real | budget | prior_year) d'une section (mois ou cumul)."""
    k = sec.get("kpis") or {}
    av = sec.get("apres_vente") or {}
    o = {}
    un, uu = _champ(k.get("unites_neuf"), f), _champ(k.get("unites_usage"), f)
    if un is not None or uu is not None:
        o["u_total"] = (un or 0) + (uu or 0)
    o["vh_pb"] = _somme(_champ(k.get("pb_neuf"), f), _champ(k.get("pb_usage"), f))
    dep = _champ(k.get("depenses"), f)
    o["dep_abs"] = abs(dep) if dep is not None else None
    o["profit_net"] = _champ(k.get("profit_net"), f)
    acc = {"bt": None, "mo": None, "pc": None, "mopb": None, "pcpb": None, "h": None, "h_n": None, "h_mo": None}
    cli = {}
    for typ in TYPES_BT:
        t = (av.get("types") or {}).get(typ) or {}
        bt = _champ(t.get("bt"), f)
        if not bt:
            continue
        mo, pc = _champ(t.get("mo_ventes"), f), _champ(t.get("pc_ventes"), f)
        mopb, pcpb = _champ(t.get("mo_pb"), f), _champ(t.get("pc_pb"), f)
        for cle, v in (("bt", bt), ("mo", mo), ("pc", pc), ("mopb", mopb), ("pcpb", pcpb)):
            acc[cle] = _somme(acc[cle], v)
        h = _champ(t.get("heures"), f)
        if h:
            acc["h"], acc["h_n"], acc["h_mo"] = _somme(acc["h"], h), _somme(acc["h_n"], bt), _somme(acc["h_mo"], mo)
        if typ == "client":
            cli = {"bt": bt, "mo": mo, "tot": _somme(mo, pc), "pb": _somme(mopb, pcpb)}
    o.update({"av_bt": acc["bt"], "av_mo": acc["mo"], "av_pc": acc["pc"], "av_mopb": acc["mopb"],
              "av_tot": _somme(acc["mo"], acc["pc"]), "av_pb": _somme(acc["mopb"], acc["pcpb"]),
              "av_h": acc["h"], "av_h_n": acc["h_n"], "av_h_mo": acc["h_mo"],
              "av_bt_client": cli.get("bt"), "av_mo_client": cli.get("mo"), "av_tot_client": cli.get("tot"), "av_pb_client": cli.get("pb")})
    pt = (av.get("pieces") or {}).get("total") or {}
    o["av_pieces_v"], o["av_pieces_pb"] = _champ(pt.get("ventes"), f), _champ(pt.get("pb"), f)
    ct = (av.get("carrosserie") or {}).get("total") or {}
    o["av_carr_v"], o["av_carr_n"] = _champ(ct.get("ventes"), f), _champ(ct.get("bt"), f)
    for cle, _l, _g, _f, rat in INDICATEURS_UNITE:
        if rat:
            o[cle] = _div(o.get(rat[0]), o.get(rat[1]))
    return o


def ajouter_par_unite(sec, k, libelles):
    """Ajoute à k (indicateurs compacts d'une section) les indicateurs par unité et par BT, avec leurs sommes cachées."""
    vals = [par_unite(sec, f) for f in CHAMPS]
    for cle, lib, grp, fmt, _rat in INDICATEURS_UNITE:
        t = [arrondi(v.get(cle)) for v in vals]
        if any(x is not None for x in t):
            k[cle] = t
            libelles.setdefault(cle, {"l": lib, "g": grp, "f": fmt})
    for cle in CACHES_UNITE:
        t = [arrondi(v.get(cle)) for v in vals]
        if any(x is not None for x in t) and cle not in k:
            k[cle] = t
            libelles.setdefault(cle, {"l": cle, "g": "cache", "f": None})


def arrondi(v):
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v != v:
        return None
    a = abs(v)
    if a < 10:
        return round(v, 4)
    if a < 1000:
        return round(v, 2)
    return int(round(v))


def triplet(kv):
    if not isinstance(kv, dict):
        return None
    t = [arrondi(kv.get(f)) for f in CHAMPS]
    return None if all(x is None for x in t) else t


def index_drive(chemin_manifeste):
    """Fichier source → (id Drive, date de modification), d'après sources/.drive_manifest.json
    (écrit par src/drive_sync.py). Un fichier absent du manifeste a été déposé à la main."""
    idx = {}
    try:
        with open(chemin_manifeste, encoding="utf-8") as f:
            man = json.load(f)
    except (OSError, ValueError):
        return idx
    for fid, v in man.items():
        if not isinstance(v, dict):
            continue
        for k in (os.path.basename(v.get("local_path") or ""), v.get("name") or ""):
            if k and k not in idx:
                idx[k] = (fid, v.get("modifiedTime") or "")
    return idx


def _paire(c, g):
    c, g = arrondi(c), arrondi(g)
    return None if c is None and g is None else [c, g]


def _div(a, b):
    return a / b if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None


def composites(data, racine):
    """{ cle du tableau de bord: { période: bloc } } — la concession et la moyenne de son groupe constructeur,
    comme dans l'analyse au composite du rapport mensuel. {} si le module du rapport n'est pas lisible."""
    comp = data.get("composites") or {}
    if not comp:
        return {}
    try:
        for d in (os.path.join(racine, "reports", "mensuel"), os.path.join(racine, "src")):
            if d not in sys.path:
                sys.path.insert(0, d)
        import analyse_composite as A
    except Exception as e:                                   # le KPI part quand même, sans composite
        print("Composite non exporté (analyse_composite illisible) : " + repr(e))
        return {}
    classes = {"vw": A.VW, "hyundai": A.Hyundai}
    out = {}
    for cle, Cls in classes.items():
        mois = comp.get(cle) or {}
        for per, entree in sorted(mois.items()):
            if not isinstance(entree, dict):
                continue
            try:
                prec = mois.get(f"{int(per[:4]) - 1}-{per[5:]}")
                S = Cls(entree, prec)
                if not S.ok:
                    continue
                bloc = {"g": S.groupe, "gl": S.grp_long, "src": S.source, "f": entree.get("concession_source") or ""}
                if S.n:
                    bloc["n"] = S.n
                for mode, court in (("month", "m"), ("ytd", "c")):
                    k = {}
                    for dk, ck in COMPOSITE_INDICATEURS.items():
                        c, g = S.v("c", ck, 0, mode), S.v("g", ck, 0, mode)
                        if dk in COMPOSITE_NEGATIFS:
                            c, g = (-c if c is not None else None), (-g if g is not None else None)
                        t = _paire(c, g)
                        if t:
                            k[dk] = t
                    for rk, (a, b) in COMPOSITE_RATIOS.items():
                        na, nb_ = k.get(a) or [None, None], k.get(b) or [None, None]
                        t = _paire(_div(na[0], nb_[0]), _div(na[1], nb_[1]))
                        if t:
                            k[rk] = t
                    if k:
                        bloc[court] = k
                    deps, libs = {}, {}
                    for dept, nom in COMPOSITE_DEPTS.items():
                        m = {}
                        u = COMPOSITE_UNITES.get(dept)
                        prof, lib = (S.RETENIR.get(dept) or (None, None))
                        for met, ck in (("units", u), ("profit_brut", "pb_" + dept), ("total_depenses", "frais_" + dept),
                                        ("profit_departemental", prof)):
                            if not ck:
                                continue
                            t = _paire(S.v("c", ck, 0, mode), S.v("g", ck, 0, mode))
                            if t:
                                m[met] = t
                        if m:
                            deps[nom] = m
                            if lib:
                                libs[nom] = lib
                    if deps:
                        bloc["d" + court] = deps
                        bloc["pl"] = libs
                if "m" in bloc or "c" in bloc:
                    out.setdefault(cle, {})[per] = bloc
            except Exception as e:                           # un mois illisible n'arrête pas les autres
                print(f"Composite {cle} {per} ignoré : {e!r}")
    return out


def compacter(data, drive=None, comp=None):
    drive = drive or {}
    comp = comp or {}
    libelles = {}
    concessions = {}
    for cle, dv in (data.get("dealers") or {}).items():
        code = CODES.get(cle)
        if not code:
            continue
        periodes = {}
        for pk, pv in sorted((dv.get("periods") or {}).items()):
            fichier = pv.get("source_file") or ""
            out = {"f": fichier, "t": pv.get("source_format") or ""}
            if fichier in drive:
                out["di"], out["dt"] = drive[fichier]   # id Drive, date de modification ("dm"/"dc" = départements)
            for mode, court in (("month", "m"), ("ytd", "c")):
                sec = (pv.get("sections") or {}).get(mode)
                if not sec:
                    continue
                k = {}
                for key, kv in (sec.get("kpis") or {}).items():
                    t = triplet(kv)
                    if t is None:
                        continue
                    k[key] = t
                    if key not in libelles and isinstance(kv, dict):
                        libelles[key] = {"l": kv.get("label") or key, "g": kv.get("group") or "other", "f": kv.get("format")}
                try:
                    ajouter_par_unite(sec, k, libelles)
                except Exception as e:                       # un mois illisible n'empêche pas l'envoi
                    print(f"Indicateurs par unité {cle} {pk} {mode} ignorés : {e!r}")
                if k:
                    out[court] = k
                deps = {}
                for nom, dd in (sec.get("departments") or {}).items():
                    m = {}
                    for met in DEPT_METRIQUES:
                        t = triplet(dd.get(met))
                        if t is not None:
                            m[met] = t
                    if m:
                        deps[nom] = m
                if deps:
                    out["d" + court] = deps
            if (comp.get(cle) or {}).get(pk):
                out["x"] = comp[cle][pk]                 # composite du groupe constructeur
            if "m" in out or "c" in out:
                periodes[pk] = out
        if periodes:
            concessions[code] = {"cle": cle, "nom": NOMS.get(code, dv.get("display_name") or code),
                                 "fichier": dv.get("display_name") or "", "periodes": periodes}
    return {"v": 1, "source": "kpi-groupeautomax",
            "genereLe": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "libelles": libelles, "concessions": concessions}


def poster(url, charge, timeout=240):
    corps = json.dumps(charge, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=corps, headers={"Content-Type": "text/plain;charset=utf-8"}, method="POST")
    # Apps Script répond par une redirection 302 ; urllib la suit en GET (comportement attendu).
    with urllib.request.urlopen(req, timeout=timeout) as r:
        texte = r.read().decode("utf-8", "replace")
    try:
        return json.loads(texte)
    except ValueError:
        return {"ok": False, "erreur": "réponse illisible : " + texte[:200]}


def main(argv):
    chemin = "data/data.json"
    sortie = None
    essai = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--sortie":
            sortie = argv[i + 1]; i += 2; continue
        if a == "--essai":
            essai = True; i += 1; continue
        chemin = a; i += 1
    with open(chemin, encoding="utf-8") as f:
        data = json.load(f)
    manifeste = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(chemin))), "sources", ".drive_manifest.json")
    drive = index_drive(manifeste)
    racine = os.path.dirname(os.path.dirname(os.path.abspath(chemin)))
    comp = composites(data, racine)
    compact = compacter(data, drive, comp)
    avec = [f"{c} {p}" for c, v in compact["concessions"].items() for p, x in sorted(v["periodes"].items()) if "x" in x]
    print("Composite : " + (", ".join(avec) if avec else "aucun mois"))
    hors = [f"{c} {p}" for c, v in compact["concessions"].items() for p, x in v["periodes"].items() if "di" not in x]
    if drive and hors:
        print("Mois dont le fichier n'est pas dans le Drive (déposé à la main) : " + ", ".join(hors))
    texte = json.dumps(compact, separators=(",", ":"), ensure_ascii=False)
    resume = ", ".join(f"{c} {len(v['periodes'])} mois (dernier {max(v['periodes'])})" for c, v in compact["concessions"].items())
    print(f"KPI compacts : {len(texte) // 1024} Ko — {resume}")
    if sortie:
        with open(sortie, "w", encoding="utf-8") as f:
            f.write(texte)
        print("Écrit : " + sortie)
    if essai:
        print("Essai : rien n'est envoyé.")
        return 0
    jeton = os.environ.get("SCANAUTOMAX_KPI_JETON", "").strip()
    if not jeton:
        print("SCANAUTOMAX_KPI_JETON absent : rien n'est envoyé à ScanAutomax.")
        return 0
    url = os.environ.get("SCANAUTOMAX_URL", "").strip() or URL_DEFAUT
    rep = poster(url, {"action": "kpiImporter", "jeton": jeton, "kpi": compact})
    if rep.get("ok"):
        print(f"ScanAutomax : reçu ({rep.get('concessions', '?')} concessions, {rep.get('periodes', '?')} mois).")
        return 0
    print("ScanAutomax a refusé l'envoi : " + str(rep.get("erreur") or rep))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
