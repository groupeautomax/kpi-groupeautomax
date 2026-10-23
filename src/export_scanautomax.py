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


def compacter(data, drive=None):
    drive = drive or {}
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
    compact = compacter(data, drive)
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
