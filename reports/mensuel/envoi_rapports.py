#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Envoi mensuel des rapports aux directeurs des concessions (demande de Maxime
Allard, 29 septembre 2026).

Le 20 de chaque mois (workflow GitHub « Rapports mensuels par courriel ») :
  1. vise le mois civil précédent (ou --mois / variable MOIS) ;
  2. pour chaque concession dont le fichier de ce mois est dans data.json,
     produit son rapport mensuel, son rapport Opérations fixes et son rapport
     Ventes de véhicules (ajouté le 29 septembre 2026) ;
  3. envoie les trois PDF au script Apps Script de Maxime (web app), qui
     les expédie par courriel au directeur de la concession, Maxime en copie ;
  4. envoie à Maxime un résumé : concessions envoyées, concessions sans
     données du mois (non envoyées), avertissements.

Les adresses des directeurs ne sont PAS dans ce dépôt (public) : elles sont
dans le script Apps Script. Rien n'est écrit dans le journal à part les codes
de concession et les statuts (le journal des Actions est public).

Variables d'environnement :
  APPS_SCRIPT_URL  adresse /exec de la web app Apps Script (secret GitHub)
  RAPPORTS_TOKEN   jeton partagé avec le script (secret GitHub)
  MOIS             AAAA-MM (facultatif ; défaut : mois précédent)
  ESSAI            « oui » : tout part à Maxime seulement, rien n'est marqué envoyé
  FORCER           « oui » : renvoie même si le mois a déjà été envoyé
"""
import argparse
import base64
import datetime as dt
import json
import os
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kpi_data import Store, DEALERS, label_period  # noqa: E402


def mois_precedent(today=None):
    t = today or dt.date.today()
    y, m = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
    return f"{y}-{m:02d}"


def post(url, payload, timeout=180):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    # Apps Script répond par une redirection 302 ; urllib la suit en GET (comportement attendu).
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
    try:
        return json.loads(body)
    except ValueError:
        return {"ok": False, "erreur": "réponse non JSON du script (déploiement ou accès « Tout le monde » à vérifier)"}


# Libellé de chaque rapport dans le courriel (le script Apps Script l'affiche tel quel).
LIBELLES = {
    "mensuel": "Rapport mensuel de performance",
    "fo": "Rapport Opérations fixes (service, pièces, carrosserie, bons de travail)",
    "ventes": "Rapport Ventes de véhicules (neufs et usagés, F&I, frais de vente, gros et encan)",
}


def fichier(path, genre):
    with open(path, "rb") as f:
        return {"nom": os.path.basename(path), "libelle": LIBELLES[genre],
                "contenu_b64": base64.b64encode(f.read()).decode("ascii")}


def main():
    ap = argparse.ArgumentParser(description="Envoi mensuel des rapports aux concessions")
    ap.add_argument("--data", default=os.path.join(HERE, "..", "..", "data", "data.json"))
    ap.add_argument("--mois", default=os.environ.get("MOIS") or None)
    ap.add_argument("--concession", choices=list(DEALERS), help="une seule concession")
    ap.add_argument("--sans-envoi", action="store_true", help="produire les PDF sans rien envoyer")
    a = ap.parse_args()

    url = os.environ.get("APPS_SCRIPT_URL", "").strip()
    token = os.environ.get("RAPPORTS_TOKEN", "").strip()
    essai = os.environ.get("ESSAI", "non").strip().lower() in ("oui", "yes", "true", "1")
    forcer = os.environ.get("FORCER", "non").strip().lower() in ("oui", "yes", "true", "1")
    if not a.sans_envoi and (not url or not token):
        print("Secrets APPS_SCRIPT_URL et RAPPORTS_TOKEN absents : rien n'est envoyé.")
        return 2

    P = (a.mois or mois_precedent()).strip()
    s = Store(a.data)
    import rapport_commun as rc
    import rapport_concession as rcon
    import rapport_apres_vente_concession as rfo
    import kpi_apres_vente as kav
    import rapport_ventes_concession as rve
    import kpi_ventes as kv

    rc.setup(s, P)
    av = kav.AVStore(s)
    vs = kv.VStore(s)
    dealers = [a.concession] if a.concession else list(DEALERS)
    out = tempfile.mkdtemp(prefix="rapports_")
    envoyes, manquants, avert, erreurs = [], [], [], []

    for d in dealers:
        # « à jour avec les données du mois précédent » : le fichier du mois doit être là
        if P not in s.periods(d) or d not in rc.ACTIVE:
            manquants.append(d)
            print(f"{d} : pas de données pour {P} — non envoyé")
            continue
        pdfs = []
        try:
            for fp, n, over in rcon.generate(s, P, out, [d]):
                pdfs.append((fp, "mensuel"))
                if over:
                    avert.append(f"{DEALERS[d]} : rapport mensuel, contenu qui déborde (pages {', '.join(str(o['page']) for o in over)})")
            if av.get(d, P, "ytd"):
                for fp, n, over in rfo.generate(s, P, out, [d]):
                    pdfs.append((fp, "fo"))
                    if over:
                        avert.append(f"{DEALERS[d]} : rapport Opérations fixes, contenu qui déborde")
            else:
                avert.append(f"{DEALERS[d]} : pas de détail des opérations fixes pour {P} (rapport Opérations fixes non joint)")
            if vs.view(d, P, "ytd"):
                for fp, n, over in rve.generate(s, P, out, [d]):
                    pdfs.append((fp, "ventes"))
                    if over:
                        avert.append(f"{DEALERS[d]} : rapport Ventes de véhicules, contenu qui déborde")
            else:
                avert.append(f"{DEALERS[d]} : pas de détail des ventes de véhicules pour {P} (rapport Ventes non joint)")
        except Exception as exc:  # noqa: BLE001
            erreurs.append(f"{DEALERS[d]} : production des PDF impossible ({type(exc).__name__})")
            print(f"{d} : erreur de production ({type(exc).__name__})")
            continue
        if a.sans_envoi:
            print(f"{d} : {len(pdfs)} PDF produits (sans envoi)")
            envoyes.append(d)
            continue
        rep = post(url, {"token": token, "type": "rapport", "concession": d, "mois": P,
                         "mois_label": label_period(P), "essai": essai, "forcer": forcer,
                         "fichiers": [fichier(p, g) for p, g in pdfs]})
        if rep.get("ok"):
            statut = rep.get("statut", "envoye")
            print(f"{d} : {statut}")
            if statut == "deja_envoye":
                avert.append(f"{DEALERS[d]} : déjà envoyé pour {P}, pas renvoyé")
            else:
                envoyes.append(d)
        else:
            erreurs.append(f"{DEALERS[d]} : envoi refusé par le script ({rep.get('erreur', 'erreur inconnue')})")
            print(f"{d} : envoi refusé")

    if not a.sans_envoi:
        rep = post(url, {"token": token, "type": "resume", "mois": P, "mois_label": label_period(P), "essai": essai,
                         "envoyes": envoyes, "manquants": manquants, "avertissements": avert, "erreurs": erreurs})
        print("résumé :", "envoyé" if rep.get("ok") else "non envoyé")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
