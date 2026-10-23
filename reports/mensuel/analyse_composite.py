# -*- coding: utf-8 -*-
"""Analyse au composite, au format du rapport « Analyse des états financiers »
de Mustafa Bhaloo (Hyundai Longueuil et VW Brossard, septembre 2026).

Demande de Maxime Allard (22 octobre 2026) : « garder les éléments de
comparaison avec le composite et combiner le mien ». Ces pages remplacent,
dans le rapport mensuel de la concession, les anciennes pages « Comparaison au
composite » (sommaire et dépenses) de rapport_composite.py.

Pour chaque département (véhicules neufs, véhicules d'occasion, service,
pièces, vue globale), une page pour le mois puis une pour le cumul :
  - tableau : la concession et la moyenne du groupe, année en cours et an
    passé, variation d'une année à l'autre, écart avec le groupe ;
  - six indicateurs avancés, concession contre groupe ;
  - trois constats, chacun avec son impact estimé par rapport au groupe ;
puis une page « Trois constats et analyses à faire » sur le mois.

Hyundai : groupe Est A (850+) de l'eComposite Hyundai Canada (P&P, analyse des
revenus, ÉF ‐ Sommaire : colonnes MAD, PAD et, pour l'an passé, MMAP, MPAD).
La concession aux mêmes définitions, lue dans l'état Hyundai Canada du mois et
du même mois l'an passé (src/composites.py : hyundai_statement_lines, clé « x »
pour les unités, la retenue, les incitatifs HACC, les heures et le personnel).
Vérifié sur septembre 2026 contre le rapport de Mustafa (Longueuil : profit net
166 125 $, PB neuf 220,5 k$, F&A 78,0 k$, 76 unités, retenue et HACC 90,6 k$).

Les indicateurs qui demandent le « mémo stats » du composite (mois
d'inventaire, techniciens et employés du groupe) s'affichent dès que ces
chiffres sont lus ; sans eux, l'indicateur n'est pas montré.

VW : groupe de volume A (≥675) de VW Canada, lu dans ses « états financiers
standard » (le concessionnaire moyen du groupe, même gabarit que l'état de la
concession) ; VW Brossard aux mêmes lignes dans son propre état VW Canada, du
mois et du même mois l'an passé (src/composites.py : vw_statement_lines).
Vérifié sur septembre 2026 contre le rapport de Mustafa (Brossard : profit net
avant impôts 215 186 $, groupe A 110 799 $ ; neufs 49 unités contre 70).
"""
from html import escape

import rapport_commun as rc
from kpi_data import MOIS, split
from kpi_analyse import kmoney, money, num, pct, pts

DEPTS = [("neuf", "Véhicules neufs", "VÉHICULES NEUFS"), ("occasion", "Véhicules d'occasion", "VÉHICULES D'OCCASION"),
         ("service", "Service", "APRÈS-VENTE"), ("pieces", "Pièces", "APRÈS-VENTE"),
         ("global", "Vue globale", "PERFORMANCE FINANCIÈRE")]


def _n(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _div(a, b):
    a, b = _n(a), _n(b)
    return a / b if a is not None and b else None


def _sum(*vals):
    vals = [_n(v) for v in vals]
    return None if any(v is None for v in vals) else sum(vals)


def _norm(s):
    import unicodedata
    import re
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    s = s.replace("﴾", "(").replace("﴿", ")").replace("’", "'").replace("œ", "oe")
    s = re.sub(r"\s*-\s*", " - ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


# ======================================================================= Hyundai
class Hyundai:
    """Valeurs de base, concession (« c ») ou groupe (« g »), année en cours
    (an = 0) ou an passé (an = 1), mois ou cumul."""
    COL = {(0, "month"): "mad", (0, "ytd"): "pad", (1, "month"): "mmap", (1, "ytd"): "mpad"}

    def __init__(self, entry, prec=None):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
        import composites as C
        pp = entry.get("hyundai_pp") or {}
        ef = entry.get("hyundai_ef") or {}
        self.pages_pp = pp.get("pages") or {}
        self.canon = {d: C.pp_canon(rows) for d, rows in self.pages_pp.items()}
        self.ar = ((entry.get("hyundai_ar") or {}).get("pages")) or {}
        self.ef = ef.get("lignes") or {}
        self.conc = {0: entry.get("concession") or {}, 1: entry.get("concession_prec") or {}}
        # Composite du même mois l'an passé (groupe de cette année-là : 14 concessions en 2025 contre 16 en 2026,
        # comme dans le rapport de Mustafa) ; sans lui, colonnes MMAP / MPAD du composite de l'année.
        prec = prec or {}
        self.pages_pp_prec = (prec.get("hyundai_pp") or {}).get("pages") or {}
        self.canon_prec = {d: C.pp_canon(rows) for d, rows in self.pages_pp_prec.items()}
        self.ar_prec = ((prec.get("hyundai_ar") or {}).get("pages")) or {}
        self.n_prec = (prec.get("hyundai_pp") or prec.get("hyundai_ar") or {}).get("n")
        self.memo = {0: (entry.get("hyundai_memo") or {}).get("sections") or {},
                     1: (prec.get("hyundai_memo") or {}).get("sections") or {}}
        per = pp.get("period") or ((entry.get("hyundai_ar") or {}).get("period")) or "2000-12"
        self.nmois = int(per[5:7])
        self.groupe = ef.get("groupe") or pp.get("groupe") or "groupe de comparaison"
        self.n = ef.get("n") or pp.get("n")
        self.ok = bool(self.conc[0] and self.pages_pp and self.ar)
        self.nom, self.court = "Hyundai Longueuil", "Longueuil"
        g = self.groupe.split("(")[0].strip() if self.groupe else "groupe"
        self.grp_court = self.grp_barre = g or "groupe"
        self.grp_long = f"{self.groupe} Hyundai" if self.groupe else "groupe"
        self.g_nom, self.g_de, self.g_a = self.grp_court, _de(self.grp_court), f"à {self.grp_court}"
        self.source = "eComposite Hyundai Canada"
        self.marque = "hyundai"
        self.LIGNES, self.INDICATEURS, self.DEPT_PROFITS, self.VAR_DE = LIGNES, INDICATEURS, DEPT_PROFITS, VAR_DE
        self.DERIVEES, self.ANALYSES = DERIVEES, ANALYSES
        self.TITRE_PROFITS = "PROFIT APRÈS RETENUE ET HACC PAR DÉPARTEMENT"
        self.RETENIR = {"neuf": ("profit_neuf", "Profit avec la retenue et les incitatifs HACC"),
                        "occasion": ("po_occasion", "Profit d'opération net"), "service": ("po_service", "Profit d'opération net"),
                        "pieces": ("po_pieces", "Profit d'opération net"), "global": ("pn", "Profit net avant impôts")}
        self.VOL = {"neuf": ("u_neuf", "unités vendues"), "occasion": ("u_occ", "unités au détail"), "service": ("br_client", "BT client")}

    # ---- groupe
    def _pp_row(self, dept, an, mode, idx=None, cid=None, prefix=None):
        col = self.COL[(an, mode)]
        pages, canon = self.pages_pp, self.canon
        if an == 1 and self.pages_pp_prec:
            pages, canon, col = self.pages_pp_prec, self.canon_prec, self.COL[(0, mode)]
        if cid:
            r = (canon.get(dept) or {}).get(cid)
            return _n(r.get(col)) if r else None
        rows = pages.get(dept) or []
        if idx is not None:
            return _n(rows[idx].get(col)) if len(rows) > idx else None
        pre = _norm(prefix)
        for r in rows:
            if _norm(r.get("label")).startswith(pre):
                return _n(r.get(col))
        return None

    def _ar(self, page, prefix, field, an, mode, need=None):
        col = self.COL[(an, mode)]
        ar = self.ar
        if an == 1 and self.ar_prec:
            ar, col = self.ar_prec, self.COL[(0, mode)]
        rows = ar.get(page) or []
        pre = _norm(prefix)
        for it in rows:
            if not _norm(it.get("label")).startswith(pre):
                continue
            sous = {_norm(k): v for k, v in (it.get("sous") or {}).items()}
            if need and need not in sous:
                continue
            if field == "tete":
                t = it.get("tete")
                return _n(t.get(col)) if isinstance(t, dict) else None
            if field in sous:
                return _n((sous[field] or {}).get(col))
            for k, v in sous.items():
                if k.startswith(field):
                    return _n((v or {}).get(col))
            return None
        return None

    def _g_pn(self, an, mode):
        # « Profit net (perte nette) avant réserve pour impôt » de la page Total des opérations (après le salaire et
        # les primes des propriétaires, comme le rapport de Mustafa : Est A septembre 2026 = 119 150 $)
        v = self._pp_row("total", an, mode, prefix="profit net (perte nette) avant")
        if v is not None:
            return v
        if an == 0:
            r = (self.ef.get("total") or {}).get("pn_avant_bonis")
            if r and _n(r.get("mad" if mode == "month" else "pad")) is not None:
                return r.get("mad" if mode == "month" else "pad")
        pb, fr = self._pp_row("total", an, mode, idx=1), self._pp_row("total", an, mode, cid="total_frais")
        ar, ad = self._ar("Autres revenus", "autres revenus hyundai", "tete", an, mode), self._ar("Autres déductions", "autres depenses hyundai", "tete", an, mode)
        return _sum(pb, -(fr or 0) if fr is not None else None, ar, -(ad or 0) if ad is not None else None)

    def g(self, k, an, mode):
        P, A = self._pp_row, self._ar
        if k == "u_neuf":
            return A("Neuf ‐ Ventes", "total depart. veh. neuf", "tete", an, mode)
        if k == "pb_neuf":
            return P("neuf", an, mode, idx=1)
        if k == "fi_neuf":
            return A("F et A Neuf", "bureau commercial - neuf", "pb", an, mode, need="pb")
        if k in ("frais_neuf", "frais_occasion", "frais_service", "frais_pieces", "frais_total"):
            return P(k.split("_")[1], an, mode, cid="total_frais")
        if k in ("po_neuf", "po_occasion", "po_service", "po_pieces", "po_carrosserie"):
            return P(k.split("_")[1], an, mode, prefix="profit d'operation net")
        if k == "ret_hacc":
            return _sum(A("Autres revenus", "retenue", "tete", an, mode), A("Autres revenus", "incitatif hacc", "tete", an, mode))
        if k in ("comm_neuf", "comm_occasion"):
            return P(k.split("_")[1], an, mode, cid="sal_comm")
        if k == "fin_neuf":
            return P("neuf", an, mode, cid="financement")
        if k == "u_occ":
            return A("Occasion ‐ Ventes", "total ventes au detail", "tete", an, mode)
        if k == "pbdet_occ":
            return _sum(*[x for x in [self._prod(A("Occasion ‐ PB", "total ventes au detail", "pb par unite", an, mode), self.g("u_occ", an, mode))]])
        if k == "fi_occ":
            return A("F et A Occasion", "total gp bureau d'affaires", "tete", an, mode)
        if k == "u_gros":
            return A("Occasion ‐ Ventes", "ventes en gros", "tete", an, mode)
        if k == "pb_gros":
            return self._prod(A("Occasion ‐ PB", "ventes en gros", "pb par unite", an, mode), self.g("u_gros", an, mode))
        if k in ("pb_occasion", "pb_service", "pb_pieces", "pb_total"):
            return P(k.split("_")[1], an, mode, idx=1)
        if k in ("ventes_service", "ventes_pieces", "ventes_total"):
            return P(k.split("_")[1], an, mode, idx=0)
        for t, lab in (("mo_client", "main-d'oeuvre - bons de reparation au client"), ("mo_garantie", "main-d'oeuvre - garantie"),
                       ("mo_interne", "main-d'oeuvre - interne")):
            if k == t:
                return A("Service ‐ Vente et PB", lab, "ventes", an, mode)
            if k == "pb_" + t:
                return A("Service ‐ Vente et PB", lab, "pb", an, mode)
        if k == "br_total":
            return A("Service ‐ Vente et PB", "total depart. service", "tete", an, mode)
        if k == "br_client":
            return A("Service ‐ Vente et PB", "main-d'oeuvre - bons de reparation au client", "tete", an, mode)
        if k == "pc_br":
            return _sum(*[A("Pièces ‐ Vente et PB", p, "ventes", an, mode) for p in ("bons de reparation au client", "garantie", "interne")])
        if k == "pc_client":
            return A("Pièces ‐ Vente et PB", "bons de reparation au client", "ventes", an, mode)
        if k == "pb_pc_client":
            return A("Pièces ‐ Vente et PB", "bons de reparation au client", "pb", an, mode)
        if k == "pc_gros":
            return A("Pièces ‐ Vente et PB", "ventes en gros", "ventes", an, mode)
        if k == "pn":
            return self._g_pn(an, mode)
        if k == "autres_net":
            ar, ad = A("Autres revenus", "autres revenus hyundai", "tete", an, mode), A("Autres déductions", "autres depenses hyundai", "tete", an, mode)
            rh = self.g("ret_hacc", an, mode)
            prop = (P("total", an, mode, prefix="salaire - proprietaires") or 0) + (P("total", an, mode, prefix="primes - proprietaires") or 0)
            return None if None in (ar, ad, rh) else ar - rh - ad - prop
        if k == "emploi":
            ids = ("sal_directeurs", "sal_comm", "sal_fi", "emploi")
            return _sum(*[P("total", an, mode, cid=i) for i in ids])
        if k == "directs_hors_emploi":
            return _sum(P("total", an, mode, cid="total_directs"), -(P("total", an, mode, cid="emploi") or 0))
        if k in ("techniciens", "employes_pieces", "mois_inv_neuf", "mois_inv_occ"):
            return self._memo(k, an)
        return None

    def _memo(self, k, an):
        """Mémo stats du composite (Moy. MAD : un instantané à la fin du mois, le même pour le cumul)."""
        secs = {_norm(f): {_norm(t): {_norm(l): v for l, v in lignes.items()} for t, lignes in sec.items()}
                for f, sec in (self.memo.get(an) or {}).items()}
        def lit(feuille, section, ligne):
            for f, sec in secs.items():
                if not f.startswith(feuille):
                    continue
                for t, lignes in sec.items():
                    if t.startswith(section):
                        for l, v in lignes.items():
                            if l.startswith(ligne):
                                return _n(v)
            return None
        if k == "techniciens":
            return lit("employes", "service", "techniciens")
        if k == "employes_pieces":
            return lit("employes", "pieces", "nombre total")
        j = lit("inventaire neufs" if k == "mois_inv_neuf" else "occasions", "analyse d'inventaire", "jours d'approvisionnement")
        return j / 30.4 if j is not None else None     # jours d'approvisionnement → mois

    @staticmethod
    def _prod(a, b):
        return a * b if _n(a) is not None and _n(b) is not None else None

    # ---- concession (état Hyundai Canada)
    def c(self, k, an, mode):
        e = (self.conc.get(an) or {}).get(mode) or {}
        ef, pp, ar, x = e.get("ef") or {}, e.get("pp") or {}, e.get("ar") or {}, e.get("x") or {}
        if not e:
            return None
        if k == "u_neuf":
            return x.get("u_neuf")
        if k in ("pb_neuf", "pb_occasion", "pb_service", "pb_pieces", "pb_total"):
            return (ef.get(k.split("_")[1]) or {}).get("pb")
        if k in ("ventes_service", "ventes_pieces", "ventes_total"):
            return (ef.get(k.split("_")[1]) or {}).get("ventes")
        if k in ("frais_neuf", "frais_occasion", "frais_service", "frais_pieces", "frais_total"):
            return (ef.get(k.split("_")[1]) or {}).get("frais")
        if k in ("po_neuf", "po_occasion", "po_service", "po_pieces", "po_carrosserie"):
            return (ef.get(k.split("_")[1]) or {}).get("profit_op")
        if k == "fi_neuf":
            return (ef.get("neuf") or {}).get("fi")
        if k == "fi_occ":
            return (ef.get("occasion") or {}).get("fi")
        if k == "ret_hacc":
            return _sum(x.get("retenue"), x.get("hacc"))
        if k in ("comm_neuf", "comm_occasion"):
            return (pp.get(k.split("_")[1]) or {}).get("sal_comm")
        if k == "fin_neuf":
            return (pp.get("neuf") or {}).get("financement")
        if k == "u_occ":
            return x.get("u_occ_det")
        if k == "pbdet_occ":
            return x.get("pb_occ_det")
        if k in ("u_gros", "pb_gros"):
            return x.get(k)
        for t in ("mo_client", "mo_garantie", "mo_interne"):
            if k == t:
                return (ar.get(t) or {}).get("ventes")
            if k == "pb_" + t:
                return (ar.get(t) or {}).get("pb")
        if k in ("br_total", "br_client", "techniciens", "employes_pieces", "heures_client"):
            return x.get(k)
        if k in ("mois_inv_neuf", "mois_inv_occ"):
            stock, u = (x.get("stock_neuf"), x.get("u_neuf")) if k == "mois_inv_neuf" else (x.get("stock_occ"), x.get("u_occ_det"))
            if mode == "ytd" and u:
                u = u / self.nmois           # ventes moyennes par mois depuis janvier
            return _div(stock, u)
        if k == "pc_br":
            return _sum(*[(ar.get(t) or {}).get("ventes") for t in ("pc_client", "pc_garantie", "pc_interne")])
        if k == "pc_client":
            return (ar.get("pc_client") or {}).get("ventes")
        if k == "pb_pc_client":
            return (ar.get("pc_client") or {}).get("pb")
        if k == "pc_gros":
            return (ar.get("pc_gros") or {}).get("ventes")
        prop = (ef.get("total") or {}).get("remuneration_proprietaires") or 0
        if k == "pn":
            pn = (ef.get("total") or {}).get("pn_avant_bonis")
            return None if pn is None else pn - prop
        if k == "autres_net":
            rh = self.c("ret_hacc", an, mode)
            return None if None in (x.get("autres_revenus"), x.get("autres_depenses"), rh) else x["autres_revenus"] - rh - x["autres_depenses"] - prop
        if k == "emploi":
            t = pp.get("total") or {}
            return _sum(*[t.get(i) for i in ("sal_directeurs", "sal_comm", "sal_fi", "emploi")])
        if k == "directs_hors_emploi":
            t = pp.get("total") or {}
            return _sum(t.get("total_directs"), -(t.get("emploi") or 0) if t.get("emploi") is not None else None)
        return None

    def v(self, who, k, an, mode):
        """Valeur de base ou dérivée."""
        f = self.c if who == "c" else self.g
        D = self.DERIVEES.get(k)
        if D:
            return D(lambda kk: self.v(who, kk, an, mode))
        return _n(f(k, an, mode))


# Valeurs dérivées, mêmes définitions pour la concession et le groupe
DERIVEES = {
    "pbav_neuf": lambda V: _sum(V("pb_neuf"), -(V("fi_neuf") or 0) if V("fi_neuf") is not None else None),
    "pbav_u": lambda V: _div(V("pbav_neuf"), V("u_neuf")),
    "fi_u": lambda V: _div(V("fi_neuf"), V("u_neuf")),
    "profit_neuf": lambda V: _sum(V("po_neuf"), V("ret_hacc")),
    "super_neuf": lambda V: _sum(V("pbav_neuf"), V("ret_hacc")),
    "super_u": lambda V: _div(V("super_neuf"), V("u_neuf")),
    "super_fi_u": lambda V: _div(_sum(V("super_neuf"), V("fi_neuf")), V("u_neuf")),
    "comm_super": lambda V: _div(V("comm_neuf"), V("super_neuf")),
    "fin_u": lambda V: _div(V("fin_neuf"), V("u_neuf")),
    "pbdet_u": lambda V: _div(V("pbdet_occ"), V("u_occ")),
    "fio_u": lambda V: _div(V("fi_occ"), V("u_occ")),
    "det_fi_u": lambda V: _div(_sum(V("pbdet_occ"), V("fi_occ")), V("u_occ")),
    "comm_occ": lambda V: _div(V("comm_occasion"), _sum(V("pbdet_occ"), V("fi_occ"))),
    "neuf_occ": lambda V: _div(V("super_neuf"), V("pbdet_occ")),
    "marge_service": lambda V: _div(V("pb_service"), V("ventes_service")),
    "absorption": lambda V: _div(_sum(V("pb_service"), V("pb_pieces")), V("frais_total")),
    "mo_br": lambda V: _div(V("mo_client"), V("br_client")),
    "marge_mo": lambda V: _div(V("pb_mo_client"), V("mo_client")),
    "pb_tech": lambda V: _div(V("pb_mo_client"), V("techniciens")),
    "pb_br_client": lambda V: _div(_sum(V("pb_mo_client"), V("pb_pc_client")), V("br_client")),
    "po_ventes_service": lambda V: _div(V("po_service"), V("ventes_service")),
    "marge_pieces": lambda V: _div(V("pb_pieces"), V("ventes_pieces")),
    "pc_mo": lambda V: _div(V("pc_client"), V("mo_client")),
    "pc_br_client": lambda V: _div(V("pc_client"), V("br_client")),
    "marge_pc_client": lambda V: _div(V("pb_pc_client"), V("pc_client")),
    "pb_employe": lambda V: _div(V("pb_pieces"), V("employes_pieces")),
    "po_ventes_pieces": lambda V: _div(V("po_pieces"), V("ventes_pieces")),
    "marge_total": lambda V: _div(V("pb_total"), V("ventes_total")),
    "pexpl": lambda V: _sum(V("pb_total"), -(V("frais_total") or 0) if V("frais_total") is not None else None),
    "ros": lambda V: _div(V("pn"), V("ventes_total")),
    "super_total": lambda V: _sum(V("pb_total"), V("ret_hacc")),
    "emploi_super": lambda V: _div(V("emploi"), V("super_total")),
    "directs_super": lambda V: _div(V("directs_hors_emploi"), V("super_total")),
}

# ======================================================================= définitions des pages
# Lignes du tableau : (clé, libellé, type). Types : n (nombre), u ($ par unité), k (k$), p (pourcentage)
LIGNES = {
    "neuf": [("u_neuf", "Unités vendues", "n"), ("pbav_u", "Profit brut avant (véhicule) par unité ($)", "u"),
             ("pbav_neuf", "Profit brut avant total (k$)", "k"), ("fi_u", "Profit brut arrière (F&A) par unité ($)", "u"),
             ("fi_neuf", "Profit brut arrière total (k$)", "k"), ("pb_neuf", "Profit brut total (k$)", "k"),
             ("frais_neuf", "Dépenses (k$)", "k-"), ("po_neuf", "Profit d'opération net (k$)", "k"),
             ("ret_hacc", "Autres revenus : retenue et incitatifs HACC (k$)", "k"),
             ("profit_neuf", "Profit avec retenue et HACC (k$)", "kb")],
    "occasion": [("u_occ", "Unités au détail", "n"), ("pbdet_u", "Profit brut détail par unité ($)", "u"),
                 ("pbdet_occ", "Profit brut détail total (k$)", "k"), ("fio_u", "Profit brut arrière (F&A) par unité ($)", "u"),
                 ("fi_occ", "Profit brut arrière total (k$)", "k"), ("u_gros", "Unités vendues en gros", "n"),
                 ("pb_gros", "Profit brut vente en gros (k$)", "k"), ("pb_occasion", "Profit brut total (k$)", "k"),
                 ("frais_occasion", "Dépenses (k$)", "k-"), ("po_occasion", "Profit d'opération net (k$)", "kb")],
    "service": [("mo_client", "Ventes main-d'œuvre : client (k$)", "k"), ("mo_garantie", "Ventes main-d'œuvre : garantie (k$)", "k"),
                ("mo_interne", "Ventes main-d'œuvre : interne (k$)", "k"), ("ventes_service", "Ventes totales (k$)", "k"),
                ("pb_service", "Profit brut (k$)", "k"), ("marge_service", "Marge brute", "p"),
                ("frais_service", "Dépenses totales (k$)", "k-"), ("po_service", "Profit d'opération net (k$)", "kb"),
                ("br_total", "Bons de réparation (total)", "n"), ("br_client", "BT client", "n")],
    "pieces": [("pc_br", "Ventes : BR service (k$)", "k"), ("pc_gros", "Ventes : en gros (k$)", "k"),
               ("ventes_pieces", "Ventes totales (k$)", "k"), ("pb_pieces", "Profit brut total (k$)", "k"),
               ("marge_pieces", "Marge brute", "p"), ("frais_pieces", "Dépenses totales (k$)", "k-"),
               ("po_pieces", "Profit d'opération net (k$)", "kb")],
    "global": [("ventes_total", "Ventes (k$)", "k"), ("pb_total", "Profit brut (k$)", "k"), ("marge_total", "Marge brute", "p"),
               ("frais_total", "Dépenses totales (k$)", "k-"), ("pexpl", "Profit d'exploitation (k$)", "k"),
               ("ret_hacc", "Retenue et incitatifs HACC (k$)", "k"), ("autres_net", "Autres revenus moins déductions (k$)", "k"),
               ("pn", "Profit net avant impôts (k$)", "kb")],
}
DEPT_PROFITS = [("profit_neuf", "Neufs (k$)"), ("po_occasion", "Occasion (k$)"), ("po_service", "Service (k$)"),
                ("po_pieces", "Pièces (k$)"), ("po_carrosserie", "Carrosserie (k$)")]

# Indicateurs : (clé, titre, définition, type, sens) — sens +1 : plus haut = mieux ; −1 : plus bas = mieux
INDICATEURS = {
    "neuf": [("super_u", "Super profit brut / unité", "(profit brut avant + retenue et HACC) ÷ unités", "u", 1),
             ("fi_u", "Profit arrière / unité", "profit brut F&A ÷ unités vendues", "u", 1),
             ("mois_inv_neuf", "Mois d'inventaire", "unités en stock ÷ unités vendues (bas = mieux)", "m", -1),
             ("comm_super", "Commissions ÷ super PB", "rémunération des vendeurs (bas = mieux)", "p", -1),
             ("var_u_neuf", "Unités vendues, var. a/a", "{per} vs {per1}", "v", 1),
             ("fin_u", "Intérêts / unité vendue", "plan de financement ÷ unités (bas = mieux)", "u", -1)],
    "occasion": [("pbdet_u", "Profit brut détail / unité", "net de la remise à neuf ÷ unités au détail", "u", 1),
                 ("fio_u", "Profit arrière / unité", "profit brut F&A ÷ unités au détail", "u", 1),
                 ("mois_inv_occ", "Mois d'inventaire", "unités en stock ÷ unités au détail (bas = mieux)", "m", -1),
                 ("comm_occ", "Commissions ÷ PB détail + F&A", "rémunération des vendeurs (bas = mieux)", "p", -1),
                 ("neuf_occ", "Super PB neuf ÷ occasion", "en dollars totaux (en fois)", "x", -1),
                 ("var_u_occ", "Unités au détail, var. a/a", "{per} vs {per1}", "v", 1)],
    "service": [("absorption", "Taux d'absorption", "profit brut après-vente ÷ dépenses totales", "p", 1),
                ("mo_br", "M-O client / BT client", "ventes main-d'œuvre client ÷ BT client", "u", 1),
                ("marge_mo", "Marge M-O client", "profit brut ÷ ventes main-d'œuvre client", "p", 1),
                ("pb_tech", "Profit brut client / technicien", "main-d'œuvre client ÷ techniciens", "u", 1),
                ("var_br_client", "BT client, var. a/a", "{per} vs {per1}", "v", 1),
                ("po_ventes_service", "Profit d'opération ÷ ventes", "profit d'opération net ÷ ventes du service", "p", 1)],
    "pieces": [("pc_mo", "Pièces/BT ÷ M-O/BT (client)", "pièces client ÷ main-d'œuvre client", "x", 1),
               ("marge_pieces", "Marge brute des pièces", "profit brut ÷ ventes totales du département", "p", 1),
               ("pb_employe", "Profit brut / employé pièces", "profit brut ÷ employés aux pièces", "u", 1),
               ("marge_pc_client", "Marge des pièces client", "profit brut ÷ ventes de pièces client", "p", 1),
               ("pc_br_client", "Pièces et acc. / BT client", "ventes de pièces client ÷ BT client", "u", 1),
               ("po_ventes_pieces", "Profit net ÷ ventes", "profit d'opération ÷ ventes du département", "p", 1)],
    "global": [("ros", "Rendement sur les ventes (ROS)", "profit net ÷ ventes totales", "p", 1),
               ("var_pn", "Profit net, var. a/a", "{per} vs {per1}", "v", 1),
               ("var_super_total", "Super profit brut, var. a/a", "(PB + retenue et HACC), {an} vs {an1}", "v", 1),
               ("emploi_super", "Coûts d'emploi ÷ super PB", "salaires des ventes, du bureau commercial et frais d'emploi (bas = mieux)", "p", -1),
               ("directs_super", "Frais directs hors emploi ÷ super PB", "frais directs moins frais d'emploi (bas = mieux)", "p", -1)],
}
VAR_DE = {"var_u_neuf": "u_neuf", "var_u_occ": "u_occ", "var_br_client": "br_client", "var_pn": "pn", "var_super_total": "super_total"}

ANALYSES = {
    "var_u_neuf": "commandes du mois suivant contre l'allocation; âge de l'inventaire neuf par modèle; atteinte des objectifs de bonis.",
    "super_u": "prix de vente et rabais par modèle; part des ventes à marge réduite (flotte, démos).",
    "fi_u": "pénétration des produits F&A par conseiller; part des transactions au comptant.",
    "comm_super": "plan de rémunération des vendeurs contre le profit généré.",
    "fin_u": "âge de l'inventaire et coût du plan de financement par modèle.",
    "neuf_occ": "sourcing des véhicules d'occasion (reprises, encan); prix et rotation; part d'occasion par vendeur.",
    "pbdet_u": "prix affichés contre le marché; remise à neuf par véhicule.",
    "fio_u": "pénétration F&A sur l'occasion par conseiller.",
    "var_u_occ": "inventaire d'occasion disponible et délai de remise à neuf.",
    "comm_occ": "rémunération des vendeurs d'occasion.",
    "absorption": "dépenses fixes contre le profit brut de l'après-vente.",
    "mo_br": "taux de main-d'œuvre, inspections multipoints et travaux recommandés par BT.",
    "marge_mo": "taux affiché, rabais et rémunération des techniciens.",
    "pb_tech": "productivité et efficacité des techniciens.",
    "var_br_client": "rendez-vous, relances de service et clients perdus.",
    "po_ventes_service": "dépenses du service contre les ventes.",
    "pc_mo": "vente de pièces sur les BT client (recommandations, pneus, accessoires).",
    "marge_pieces": "matrice de prix des pièces; part des ventes en gros à faible marge.",
    "pb_employe": "effectif des pièces contre le volume.",
    "marge_pc_client": "matrice de prix des pièces client.",
    "pc_br_client": "vente de pièces et accessoires par BT client.",
    "po_ventes_pieces": "marge et dépenses des pièces.",
    "ros": "marge brute et dépenses de l'ensemble des départements.",
    "var_pn": "départements qui expliquent le recul (pages précédentes).",
    "var_super_total": "volume et profit par unité des véhicules.",
    "emploi_super": "effectif et rémunération contre le profit généré.",
    "directs_super": "détail des frais directs (logiciels, véhicules de service, divers).",
}


# ======================================================================= Volkswagen
class VW:
    """VW Brossard (« c ») et le groupe de volume A de VW Canada (« g »), lus aux mêmes lignes de l'état
    financier VW Canada : p2 [total, neuf, occasion], p3 [service, carrosserie, pièces], p4 [unités, ventes,
    PB], p5 [BR, ventes, PB], p6 (heures). an = 0 : année en cours ; an = 1 : même mois l'an passé (état du
    groupe de cette année-là)."""

    def __init__(self, entry, prec=None):
        prec = prec or {}
        g0, g1 = entry.get("vw_groupe") or {}, prec.get("vw_groupe") or {}
        self.L = {("g", 0): g0.get("lignes") or {}, ("g", 1): g1.get("lignes") or {},
                  ("c", 0): entry.get("concession") or {}, ("c", 1): entry.get("concession_prec") or {}}
        per = g0.get("period") or "2000-12"
        self.nmois = int(per[5:7])
        self.groupe = g0.get("groupe") or "Groupe A"
        self.n = self.n_prec = None
        self.ok = bool(self.L[("g", 0)] and self.L[("c", 0)])
        self.nom, self.court = "Volkswagen Brossard", "Brossard"
        lettre = self.groupe.split("(")[0].replace("Groupe", "").strip() or "A"
        self.grp_court, self.grp_barre = f"groupe {lettre}", f"Groupe {lettre}"
        self.grp_long = f"{self.groupe} VW"
        self.g_nom, self.g_de, self.g_a = f"le groupe {lettre}", f"du groupe {lettre}", f"au groupe {lettre}"
        self.source = "états financiers standard du groupe de volume de VW Canada"
        self.marque = "vw"
        self.LIGNES, self.INDICATEURS, self.DEPT_PROFITS, self.VAR_DE = LIGNES_VW, INDICATEURS_VW, DEPT_PROFITS_VW, VAR_DE_VW
        self.DERIVEES, self.ANALYSES = DERIVEES_VW, {**ANALYSES, **ANALYSES_VW}
        self.TITRE_PROFITS = "PROFIT APRÈS INCITATIFS PAR DÉPARTEMENT"
        self.RETENIR = {"neuf": ("profit_neuf", "Profit net après incitatifs"), "occasion": ("profit_occ", "Profit net"),
                        "service": ("po_service", "Profit d'exploitation"),
                        "pieces": ("profit_pieces", "Profit après l'escompte de commande de stock"),
                        "global": ("pn", "Profit net avant impôts")}
        self.VOL = {"neuf": ("u_neuf", "unités vendues"), "occasion": ("u_occ", "unités au détail"),
                    "service": ("heures_vendues", "heures vendues")}

    def base(self, who, k, an, mode):
        L = self.L.get((who, an)) or {}
        m = L.get(mode) or {}
        if not m:
            return None

        def p(page, ligne, i):
            row = (m.get(page) or {}).get(str(ligne))
            return _n(row[i]) if row and len(row) > i else None

        def somme(*v):
            return _sum(*v)
        T, N, O = 0, 1, 2          # page 2 : total, neufs, occasion
        SV, CA, PC = 0, 1, 2       # page 3 : service, carrosserie, pièces
        U, V, PB = 0, 1, 2         # pages 4 et 5 : unités (ou BR), ventes, profit brut
        tab = {
            "u_neuf": lambda: p("p4", 29, U),
            "pbav_neuf": lambda: somme(p("p4", 21, PB), p("p4", 22, PB) or 0),
            "fi_neuf": lambda: p("p4", 27, PB),
            "pb_neuf": lambda: p("p2", 2, N), "frais_neuf": lambda: p("p2", 63, N), "po_neuf": lambda: p("p2", 64, N),
            "profit_neuf": lambda: p("p2", 73, N), "comm_neuf": lambda: p("p2", 4, N), "fin_neuf": lambda: p("p2", 7, N),
            "u_occ": lambda: p("p4", 40, U),
            "pbav_occ": lambda: somme(p("p4", 31, PB), p("p4", 34, PB), p("p4", 37, PB)),
            "pbdet_occ": lambda: p("p4", 40, PB), "fi_occ": lambda: p("p4", 45, PB),
            "u_gros": lambda: p("p4", 46, U), "pb_gros": lambda: p("p4", 46, PB),
            "pb_occasion": lambda: p("p2", 2, O), "frais_occasion": lambda: p("p2", 63, O),
            "profit_occ": lambda: p("p2", 73, O), "comm_occasion": lambda: p("p2", 4, O),
            "mo_client": lambda: p("p5", 1, V), "mo_garantie": lambda: p("p5", 3, V), "mo_interne": lambda: p("p5", 4, V),
            "pb_mo_client": lambda: p("p5", 1, PB), "pb_mo_total": lambda: p("p5", 18, PB),
            "br_total": lambda: p("p5", 22, U), "br_client": lambda: p("p5", 1, U),
            "ventes_service": lambda: p("p3", 1, SV), "pb_service": lambda: p("p3", 2, SV),
            "frais_service": lambda: p("p3", 63, SV), "po_service": lambda: p("p3", 64, SV),
            "profit_service": lambda: p("p3", 73, SV), "profit_carrosserie": lambda: p("p3", 73, CA),
            "pc_br": lambda: p("p5", 41, V), "pc_carr": lambda: p("p5", 52, V), "pc_comptoir": lambda: p("p5", 53, V),
            "pc_gros": lambda: p("p5", 54, V), "pc_client": lambda: p("p5", 29, V), "pb_pc_client": lambda: p("p5", 29, PB),
            "ajust_pieces": lambda: somme(p("p5", 62, PB) or 0, p("p5", 63, PB) or 0),
            "ventes_pieces": lambda: p("p3", 1, PC), "pb_pieces": lambda: p("p3", 2, PC),
            "frais_pieces": lambda: p("p3", 63, PC), "po_pieces": lambda: p("p3", 64, PC), "profit_pieces": lambda: p("p3", 73, PC),
            "ventes_total": lambda: p("p2", 1, T), "pb_total": lambda: p("p2", 2, T), "frais_total": lambda: p("p2", 63, T),
            "pexpl": lambda: p("p2", 64, T), "pn": lambda: p("p2", 76, T), "emploi": lambda: p("p2", 27, T),
            "semi": lambda: p("p2", 47, T),
            "incit_neuf": lambda: _sum(p("p2", 73, N), -(p("p2", 64, N) or 0)) if p("p2", 64, N) is not None else None,
            "incit_total": lambda: _sum(p("p2", 73, T), -(p("p2", 64, T) or 0)) if p("p2", 64, T) is not None else None,
            "autres_net": lambda: _sum(p("p2", 74, T), -(p("p2", 75, T) or 0)) if p("p2", 75, T) is not None else None,
        }
        if k in tab:
            return tab[k]()
        if k in ("heures_vendues", "heures_client", "heures_dispo", "heures_prod"):
            return _n((m.get("p6") or {}).get(k))
        if k in ("techniciens", "employes_pieces"):
            return _n(L.get(k))
        if k in ("mois_inv_neuf", "mois_inv_occ"):
            stock = _n(L.get("stock_neuf" if k == "mois_inv_neuf" else "stock_occ"))
            u = self.base(who, "u_neuf" if k == "mois_inv_neuf" else "u_occ", an, mode)
            if mode == "ytd" and u:
                u = u / self.nmois           # ventes moyennes par mois depuis janvier
            return _div(stock, u)
        return None

    def v(self, who, k, an, mode):
        D = DERIVEES_VW.get(k)
        if D:
            return D(lambda kk: self.v(who, kk, an, mode))
        return _n(self.base(who, k, an, mode))


DERIVEES_VW = {
    "pbav_u": lambda V: _div(V("pbav_neuf"), V("u_neuf")),
    "fi_u": lambda V: _div(V("fi_neuf"), V("u_neuf")),
    "super_neuf": lambda V: _sum(V("pbav_neuf"), V("incit_neuf")),
    "super_u": lambda V: _div(V("super_neuf"), V("u_neuf")),
    "super_fi_u": lambda V: _div(_sum(V("super_neuf"), V("fi_neuf")), V("u_neuf")),
    "comm_super": lambda V: _div(V("comm_neuf"), V("super_neuf")),
    "fin_u": lambda V: _div(V("fin_neuf"), V("u_neuf")),
    "pbav_occ_u": lambda V: _div(V("pbav_occ"), V("u_occ")),
    "recon_occ": lambda V: _sum(V("pbav_occ"), -(V("pbdet_occ") or 0) if V("pbdet_occ") is not None else None),
    "recon_u": lambda V: _div(V("recon_occ"), V("u_occ")),
    "pbdet_u": lambda V: _div(V("pbdet_occ"), V("u_occ")),
    "fio_u": lambda V: _div(V("fi_occ"), V("u_occ")),
    "pbocc_u": lambda V: _div(V("pb_occasion"), V("u_occ")),
    "comm_occ": lambda V: _div(V("comm_occasion"), V("pbav_occ")),
    "neuf_occ": lambda V: _div(V("super_neuf"), V("pbav_occ")),
    "marge_service": lambda V: _div(V("pb_service"), V("ventes_service")),
    "pb_apv": lambda V: _sum(V("pb_total"), -(V("pb_neuf") or 0), -(V("pb_occasion") or 0)) if None not in (V("pb_neuf"), V("pb_occasion")) else None,
    "absorption": lambda V: _div(V("pb_apv"), V("frais_total")),
    "productivite": lambda V: _div(V("heures_prod"), V("heures_dispo")),
    "efficacite": lambda V: _div(V("heures_vendues"), V("heures_prod")),
    "h_br": lambda V: _div(V("heures_client"), V("br_client")),
    "pb_heure": lambda V: _div(V("pb_mo_total"), V("heures_vendues")),
    "pb_tech": lambda V: _div(V("pb_mo_client"), V("techniciens")),
    "pb_br_client": lambda V: _div(_sum(V("pb_mo_client"), V("pb_pc_client")), V("br_client")),
    "pbav_pieces": lambda V: _sum(V("pb_pieces"), -(V("ajust_pieces") or 0)),
    "marge_pieces": lambda V: _div(V("pb_pieces"), V("ventes_pieces")),
    "pc_mo": lambda V: _div(V("pc_client"), V("mo_client")),
    "pc_br_client": lambda V: _div(V("pc_client"), V("br_client")),
    "mo_br_client": lambda V: _div(V("mo_client"), V("br_client")),
    "pc_heure": lambda V: _div(V("pc_client"), V("heures_client")),
    "marge_pc_client": lambda V: _div(V("pb_pc_client"), V("pc_client")),
    "pb_employe": lambda V: _div(V("pb_pieces"), V("employes_pieces")),
    "pn_ventes_pieces": lambda V: _div(V("profit_pieces"), V("ventes_pieces")),
    "marge_total": lambda V: _div(V("pb_total"), V("ventes_total")),
    "ros": lambda V: _div(V("pn"), V("ventes_total")),
    "super_total": lambda V: _sum(V("pb_total"), V("incit_total")),
    "emploi_super": lambda V: _div(V("emploi"), V("super_total")),
    "semi_super": lambda V: _div(V("semi"), V("super_total")),
}

LIGNES_VW = {
    "neuf": [("u_neuf", "Unités vendues", "n"), ("pbav_u", "Profit brut avant (véhicule) par unité ($)", "u"),
             ("pbav_neuf", "Profit brut avant total (k$)", "k"), ("fi_u", "Profit brut arrière (F&A) par unité ($)", "u"),
             ("fi_neuf", "Profit brut arrière total (k$)", "k"), ("pb_neuf", "Profit brut total (k$)", "k"),
             ("frais_neuf", "Dépenses (k$)", "k-"), ("po_neuf", "Profit après dépenses (k$)", "k"),
             ("incit_neuf", "Autres revenus : incitatifs VW, frais de documentation, réserve (k$)", "k"),
             ("profit_neuf", "Profit net (k$)", "kb")],
    "occasion": [("u_occ", "Unités au détail", "n"), ("pbav_occ_u", "Profit brut avant par unité, avant remise à neuf ($)", "u"),
                 ("recon_u", "Remise à neuf par unité ($)", "u-"),
                 ("pbdet_u", "Profit brut avant par unité, après remise à neuf ($)", "u"),
                 ("pbdet_occ", "Profit brut avant total, après remise à neuf (k$)", "k"),
                 ("fio_u", "Profit brut arrière (F&A) par unité ($)", "u"), ("fi_occ", "Profit brut arrière total (k$)", "k"),
                 ("u_gros", "Unités vendues en gros", "n"), ("pb_gros", "Profit brut vente en gros (k$)", "k"),
                 ("pb_occasion", "Profit brut total (k$)", "k"), ("frais_occasion", "Dépenses (k$)", "k-"),
                 ("profit_occ", "Profit net (k$)", "kb")],
    "service": [("mo_client", "Ventes main-d'œuvre : client (k$)", "k"), ("mo_garantie", "Ventes main-d'œuvre : garantie (k$)", "k"),
                ("mo_interne", "Ventes main-d'œuvre : interne (k$)", "k"), ("ventes_service", "Ventes totales (k$)", "k"),
                ("pb_service", "Profit brut (k$)", "k"), ("marge_service", "Marge brute", "p"),
                ("frais_service", "Dépenses totales (k$)", "k-"), ("po_service", "Profit d'exploitation (k$)", "kb"),
                ("br_total", "Bons de réparation", "n"), ("heures_vendues", "Heures vendues", "n")],
    "pieces": [("pc_br", "Ventes : BR service (k$)", "k"), ("pc_carr", "Ventes : BR carrosserie (k$)", "k"),
               ("pc_comptoir", "Ventes : comptoir détail (k$)", "k"), ("pc_gros", "Ventes : comptoir en gros (k$)", "k"),
               ("ventes_pieces", "Ventes totales (k$)", "k"), ("pbav_pieces", "Profit brut avant ajust. d'inventaire (k$)", "k"),
               ("ajust_pieces", "Ajustements d'inventaire (k$)", "k"), ("pb_pieces", "Profit brut total (k$)", "k"),
               ("frais_pieces", "Dépenses totales (k$)", "k-"), ("po_pieces", "Profit d'exploitation (k$)", "k"),
               ("profit_pieces", "Profit après escompte de commande de stock (k$)", "kb")],
    "global": [("ventes_total", "Ventes (k$)", "k"), ("pb_total", "Profit brut (k$)", "k"), ("marge_total", "Marge brute", "p"),
               ("frais_total", "Dépenses totales (k$)", "k-"), ("pexpl", "Profit d'exploitation (k$)", "k"),
               ("incit_total", "Incitatifs VW, frais et réserve (k$)", "k"), ("autres_net", "Autres revenus moins déductions (k$)", "k"),
               ("pn", "Profit net avant impôts (k$)", "kb")],
}
DEPT_PROFITS_VW = [("profit_neuf", "Neufs (k$)"), ("profit_occ", "Occasion (k$)"), ("profit_service", "Service (k$)"),
                   ("profit_pieces", "Pièces (k$)"), ("profit_carrosserie", "Carrosserie (k$)")]
INDICATEURS_VW = {
    "neuf": [("super_u", "Super profit brut / unité", "(profit brut avant + autres revenus) ÷ unités", "u", 1),
             ("fi_u", "Profit arrière / unité", "profit brut F&A ÷ unités vendues", "u", 1),
             ("mois_inv_neuf", "Mois d'inventaire", "unités en stock ÷ unités vendues (bas = mieux)", "m", -1),
             ("comm_super", "Commissions ÷ super PB", "rémunération des vendeurs (bas = mieux)", "p", -1),
             ("var_u_neuf", "Unités vendues, var. a/a", "{per} vs {per1}", "v", 1),
             ("fin_u", "Intérêts / unité vendue", "plan de financement ÷ unités (bas = mieux)", "u", -1)],
    "occasion": [("pbav_occ_u", "Super profit brut / unité", "avant remise à neuf ÷ unités au détail", "u", 1),
                 ("fio_u", "Profit arrière / unité", "profit brut F&A ÷ unités au détail", "u", 1),
                 ("mois_inv_occ", "Mois d'inventaire", "unités en stock ÷ unités au détail (bas = mieux)", "m", -1),
                 ("comm_occ", "Commissions ÷ super PB", "rémunération des vendeurs (bas = mieux)", "p", -1),
                 ("neuf_occ", "Super PB neuf ÷ occasion", "en dollars totaux (en fois)", "x", -1),
                 ("var_u_occ", "Unités au détail, var. a/a", "{per} vs {per1}", "v", 1)],
    "service": [("absorption", "Taux d'absorption", "profit brut après-vente ÷ dépenses totales", "p", 1),
                ("productivite", "% productivité", "heures travaillées ÷ disponibles", "p", 1),
                ("efficacite", "% efficacité", "heures vendues ÷ travaillées", "p", 1),
                ("h_br", "Heures vendues / BT client", "heures client ÷ bons de travail client", "x", 1),
                ("pb_tech", "Profit brut client / technicien", "main-d'œuvre client ÷ techniciens service", "u", 1),
                ("var_br_client", "BT client, var. a/a", "{per} vs {per1}", "v", 1)],
    "pieces": [("pc_mo", "Pièces/BT ÷ M-O/BT (client)", "pièces client ÷ main-d'œuvre client", "x", 1),
               ("marge_pieces", "Marge brute des pièces", "profit brut ÷ ventes totales du département", "p", 1),
               ("pb_employe", "Profit brut / employé pièces", "profit brut ÷ employés aux pièces", "u", 1),
               ("pc_heure", "Pièces client / heure vendue", "ventes de pièces client ÷ heures client", "u", 1),
               ("pc_br_client", "Pièces et acc. / BT client", "ventes de pièces client ÷ BT client", "u", 1),
               ("pn_ventes_pieces", "Profit net ÷ ventes", "profit après escompte ÷ ventes du département", "p", 1)],
    "global": [("ros", "Rendement sur les ventes (ROS)", "profit net ÷ ventes totales", "p", 1),
               ("var_pn", "Profit net, var. a/a", "{per} vs {per1}", "v", 1),
               ("var_super_total", "Super profit brut, var. a/a", "(PB + incitatifs VW), {an} vs {an1}", "v", 1),
               ("emploi_super", "Coûts d'emploi ÷ super PB", "dépenses d'emploi totales (bas = mieux)", "p", -1),
               ("semi_super", "Semi-fixes ÷ super PB", "dépenses semi-fixes totales (bas = mieux)", "p", -1)],
}
VAR_DE_VW = {"var_u_neuf": "u_neuf", "var_u_occ": "u_occ", "var_br_client": "br_client", "var_pn": "pn",
             "var_super_total": "super_total"}
ANALYSES_VW = {
    "var_u_neuf": "commandes du mois suivant contre l'allocation; âge de l'inventaire neuf par modèle; atteinte des objectifs de bonis VW.",
    "pbav_occ_u": "prix affichés contre le marché; coût d'acquisition des véhicules d'occasion.",
    "comm_occ": "rémunération des vendeurs d'occasion contre le profit généré.",
    "productivite": "horaire des techniciens et heures disponibles non pointées.",
    "efficacite": "temps pointé contre temps facturé; travaux à taux fixe.",
    "h_br": "travaux recommandés et inspections multipoints par BT client.",
    "pc_heure": "vente de pièces par heure de main-d'œuvre client.",
    "pn_ventes_pieces": "marge et dépenses des pièces; escompte de commande de stock.",
    "semi_super": "détail des dépenses semi-fixes (divers, DMS, véhicules de service).",
}


# ======================================================================= calculs
def _de(nom):
    """« de Est A » → « d'Est A »."""
    return ("d'" if nom[:1].lower() in "aeiouyéèêàâîô" else "de ") + nom


def _que(nom):
    return ("qu'" if nom[:1].lower() in "aeiouyéèêàâîô" else "que ") + nom


def _pv(v):
    """Variation en % : une décimale sous 1 % (+0,8 %), sinon entier."""
    return pct(v, 1 if abs(v) < 0.01 else 0, sign=True)


def _per(P, mode):
    y, m = split(P)
    return (f"{MOIS[m][:4]}. {y}", f"{MOIS[m][:4]}. {y - 1}") if mode == "month" else (f"cumul {y}", f"cumul {y - 1}")


def valeur_ind(S, k, who, mode):
    if k in S.VAR_DE:
        b = S.VAR_DE[k]
        a0, a1 = S.v(who, b, 0, mode), S.v(who, b, 1, mode)
        return _div(_sum(a0, -(a1 or 0) if a1 is not None else None), a1) if a1 else None
    return S.v(who, k, 0, mode)


def constats(S, dept, mode):
    """Écarts avec le groupe, chiffrés en dollars (comme le rapport de Mustafa) :
    [{cle, sens: +1/-1, texte, impact}] du plus grand au plus petit impact."""
    V = lambda who, k, an=0: S.v(who, k, an, mode)
    c, g = S.court, S.g_nom
    out = []

    def add(cle, impact, texte):
        if impact is None:
            return
        out.append({"cle": cle, "impact": impact, "sens": 1 if impact >= 0 else -1, "texte": texte})

    def per_unit(cle, lab, u_key, sens=1, base_lab="unités", apres=""):
        a, b, u = V("c", cle), V("g", cle), V("c", u_key)
        if None in (a, b, u):
            return
        add(cle, (a - b) * u * sens, f"{lab} : {money(a)} contre {money(b)}{apres}; écart de {money(a - b, sign=True)} par unité sur {num(u)} {base_lab}.")

    def ratio_bas(cle, lab, base_key, base_lab):
        a, b, base = V("c", cle), V("g", cle), V("c", base_key)
        if None in (a, b, base):
            return
        add(cle, (b - a) * base, f"{lab} : {pct(a)} contre {pct(b)}; {kmoney(a * base, dec=1)} au lieu de {kmoney(b * base, dec=1)} au ratio {S.g_de}."
            if S.marque == "vw" else
            f"{lab} : {pct(a)} contre {pct(b)}; au taux {S.g_de}, {kmoney(b * base, dec=1)} au lieu de {kmoney(a * base, dec=1)}.")

    def ratio_haut(cle, lab, base_key, base_lab):
        a, b, base = V("c", cle), V("g", cle), V("c", base_key)
        if None in (a, b, base):
            return
        add(cle, (a - b) * base, f"{lab} : {pct(a)} contre {pct(b)} sur {kmoney(base, dec=1)} de {base_lab}.")

    def var_vol(cle, lab, u_key, prof_key, unite, nom, quoi="profit brut", chacun="chacun"):
        a0, a1, b0, b1, prof = V("c", u_key), V("c", u_key, 1), V("g", u_key), V("g", u_key, 1), V("c", prof_key)
        if None in (a0, a1, b0, b1, prof) or not a1 or not b1:
            return
        va, vb = a0 / a1 - 1, b0 / b1 - 1
        si = a1 * (1 + vb)
        aurait = f"aurait {unite} " if unite else "aurait "
        add(cle, (a0 - si) * prof, f"{lab} : {_pv(va)} contre {_pv(vb)} pour {g}. "
                                   f"À {_pv(vb)} comme {g}, {c} {aurait}{num(si)} {nom} au lieu de {num(a0)}, "
                                   f"à {money(prof)} de {quoi} {chacun}.")

    def abso():
        a, b, fr = V("c", "absorption"), V("g", "absorption"), V("c", "frais_total")
        if None not in (a, b, fr):
            add("absorption", (a - b) * fr, f"Taux d'absorption : {pct(a)} contre {pct(b)}; au taux {S.g_de}, l'après-vente couvrirait "
                                            f"{kmoney(b * fr, dec=1)} de dépenses au lieu de {kmoney(a * fr, dec=1)}.")

    def pc_mo():
        a, b, mo, mp = V("c", "pc_mo"), V("g", "pc_mo"), V("c", "mo_client"), V("c", "marge_pc_client")
        if None not in (a, b, mo, mp):
            add("pc_mo", (a - b) * mo * mp, f"Pièces ÷ M-O client : {num(a, 2)} contre {num(b, 2)}. Au ratio {S.g_de} : "
                                            f"{kmoney((b - a) * mo, dec=1)} de pièces client de plus, à {pct(mp)} de marge.")

    def pb_employe():
        a, b, e = V("c", "pb_employe"), V("g", "pb_employe"), V("c", "employes_pieces")
        if None not in (a, b, e):
            add("pb_employe", (a - b) * e, f"Profit brut par employé : {money(a)} contre {money(b)} sur {num(e, 1)} employés.")

    def pb_tech():
        a, b, t = V("c", "pb_tech"), V("g", "pb_tech"), V("c", "techniciens")
        if None not in (a, b, t):
            add("pb_tech", (a - b) * t, f"Profit brut client / technicien : {money(a)} contre {money(b)} sur {num(t)} techniciens.")

    def ros():
        a, b, v = V("c", "ros"), V("g", "ros"), V("c", "ventes_total")
        if None not in (a, b, v):
            add("ros", (a - b) * v, f"Rendement sur les ventes : {pct(a)} contre {pct(b)}; au ROS {S.g_de}, le profit net serait de "
                                    f"{kmoney(b * v, dec=1)} au lieu de {kmoney(a * v, dec=1)}.")

    def fin_u():
        a, b, u = V("c", "fin_u"), V("g", "fin_u"), V("c", "u_neuf")
        if None not in (a, b, u):
            credit = "; un crédit net ce mois-ci chez " + c if a < 0 and mode == "month" else f"; sur {num(u)} unités"
            add("fin_u", (b - a) * u, f"Intérêts du plan de financement : {money(a)} par unité contre {money(b)}{credit}.")

    def neuf_occ(base_key, quoi):
        a, b, sn, pd = V("c", "neuf_occ"), V("g", "neuf_occ"), V("c", "super_neuf"), V("c", base_key)
        if None not in (a, b, sn, pd) and b:
            cible = sn / b
            add("neuf_occ", pd - cible, f"Super PB neuf ÷ occasion : {num(a, 2)} contre {num(b, 2)}. Même ratio {_que(g)} = "
                                        f"{kmoney(cible, dec=1)} de {quoi} au lieu de {kmoney(pd, dec=1)}"
                                        + (" (volume ou par unité)." if S.marque == "vw" else "."))

    if S.marque == "vw":
        if dept == "neuf":
            var_vol("var_u_neuf", "Unités vendues", "u_neuf", "super_fi_u", "vendu", "unités", "super profit brut + F&A", "chacune")
            per_unit("super_u", "Super profit brut par unité", "u_neuf")
            per_unit("fi_u", "Profit arrière par unité", "u_neuf")
            ratio_bas("comm_super", "Commissions ÷ super profit brut", "super_neuf", "super PB")
            fin_u()
        elif dept == "occasion":
            neuf_occ("pbav_occ", "super PB d'occasion")
            var_vol("var_u_occ", "Unités au détail", "u_occ", "pbocc_u", "vendu", "unités", "profit brut", "chacune")
            a, b, u = V("c", "pbav_occ_u"), V("g", "pbav_occ_u"), V("c", "u_occ")
            if None not in (a, b, u):
                add("pbav_occ_u", (a - b) * u, f"Super profit brut par unité : {money(a)} contre {money(b)}, avant remise à neuf, sur {num(u)} unités.")
            per_unit("fio_u", "Profit arrière par unité", "u_occ", base_lab="unités au détail")
            ratio_bas("comm_occ", "Commissions ÷ super PB", "pbav_occ", "super PB")
        elif dept == "service":
            abso()
            for cle, lab, base in (("efficacite", "Efficacité", "heures_prod"), ("productivite", "Productivité", "heures_dispo")):
                a, b, h, ph = V("c", cle), V("g", cle), V("c", base), V("c", "pb_heure")
                if None not in (a, b, h, ph):
                    quoi = "heures travaillées" if base == "heures_prod" else "heures disponibles"
                    add(cle, (a - b) * h * ph, f"{lab} : {pct(a)} contre {pct(b)} sur {num(h)} {quoi}, à {money(ph)} de profit brut par heure.")
            var_vol("var_br_client", "BT client", "br_client", "pb_br_client", "", "BT client", "profit brut (M-O + pièces)")
            pb_tech()
        elif dept == "pieces":
            pc_mo()
            ratio_haut("pn_ventes_pieces", "Profit net ÷ ventes", "ventes_pieces", "ventes")
            ratio_haut("marge_pieces", "Marge brute des pièces", "ventes_pieces", "ventes")
            pb_employe()
        else:
            ros()
            ratio_bas("emploi_super", "Coûts d'emploi ÷ super PB", "super_total", "super PB")
            ratio_bas("semi_super", "Semi-fixes ÷ super PB", "super_total", "super PB")
    elif dept == "neuf":
        var_vol("var_u_neuf", "Unités vendues", "u_neuf", "super_fi_u", "vendu", "unités")
        per_unit("super_u", "Super profit brut par unité", "u_neuf")
        per_unit("fi_u", "Profit arrière par unité", "u_neuf")
        ratio_bas("comm_super", "Commissions ÷ super profit brut", "super_neuf", "super PB")
        a, b, u = V("c", "fin_u"), V("g", "fin_u"), V("c", "u_neuf")
        if None not in (a, b, u):
            add("fin_u", (b - a) * u, f"Intérêts du plan de financement : {money(a)} par unité contre {money(b)}; sur {num(u)} unités.")
    elif dept == "occasion":
        var_vol("var_u_occ", "Unités au détail", "u_occ", "det_fi_u", "vendu", "unités")
        per_unit("pbdet_u", "Profit brut détail par unité", "u_occ", base_lab="unités au détail")
        per_unit("fio_u", "Profit arrière par unité", "u_occ", base_lab="unités au détail")
        ratio_bas("comm_occ", "Commissions ÷ PB détail + F&A", "pbdet_occ", "PB")
        neuf_occ("pbdet_occ", "profit brut détail d'occasion")
    elif dept == "service":
        abso()
        a, b, n, m = V("c", "mo_br"), V("g", "mo_br"), V("c", "br_client"), V("c", "marge_mo")
        if None not in (a, b, n, m):
            add("mo_br", (a - b) * n * m, f"M-O client par BT client : {money(a)} contre {money(b)} sur {num(n)} BT client, à {pct(m)} de marge.")
        ratio_haut("po_ventes_service", "Profit d'opération ÷ ventes", "ventes_service", "ventes de service")
        var_vol("var_br_client", "BT client", "br_client", "pb_br_client", "eu", "BT client")
        pb_tech()
    elif dept == "pieces":
        ratio_haut("marge_pieces", "Marge brute des pièces", "ventes_pieces", "ventes")
        ratio_haut("po_ventes_pieces", "Profit net ÷ ventes", "ventes_pieces", "ventes")
        pc_mo()
        pb_employe()
    else:
        ros()
        ratio_bas("emploi_super", "Coûts d'emploi ÷ super PB", "super_total", "super PB")
        ratio_bas("directs_super", "Frais directs hors emploi ÷ super PB", "super_total", "super PB")
    out.sort(key=lambda o: -abs(o["impact"]))
    return out


# ======================================================================= mise en page
CSS = """
<style>
.ac-tab { width: 100%; border-collapse: collapse; font-size: 7.9pt; margin: 4px 0 10px; }
.ac-tab th { font-size: 7pt; font-weight: 700; color: var(--muted); text-align: right; padding: 3px 4px; border-bottom: 1px solid var(--line2); white-space: nowrap; }
.ac-tab th.grp { text-align: center; color: var(--ink); border-bottom: 1px solid var(--line); }
.ac-tab th.lab, .ac-tab td.lab { text-align: left; }
.ac-tab td { text-align: right; padding: 2px 4px; border-bottom: 1px solid var(--line); white-space: nowrap; font-variant-numeric: tabular-nums; }
.ac-tab td.lab { white-space: normal; padding-right: 8px; }
.ac-tab tr.b td { font-weight: 700; border-top: 1px solid var(--line2); }
.ac-tab td.sep, .ac-tab th.sep { border-left: 1px solid var(--line2); }
.ac-tab td.var { color: var(--muted); }
.ac-ind { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px 12px; margin: 6px 0 10px; }
.ac-ic { border: 1px solid var(--line); border-radius: 5px; padding: 7px 9px 6px; background: var(--tint2); }
.ac-it { font-size: 8pt; font-weight: 700; }
.ac-id { font-size: 6.9pt; color: var(--muted); margin-bottom: 4px; line-height: 1.3; }
.ac-bar { display: grid; grid-template-columns: 52px 1fr 54px; align-items: center; gap: 5px; font-size: 7.4pt; margin: 2px 0; }
.ac-bar .tr { height: 7px; background: #e9eae6; border-radius: 3px; overflow: hidden; }
.ac-bar .fl { height: 7px; border-radius: 3px; }
.ac-bar .v { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
.ac-cst { margin: 4px 0 0; padding: 0; list-style: none; }
.ac-cst li { display: grid; grid-template-columns: 14px 1fr 62px; gap: 6px; font-size: 8.4pt; line-height: 1.42; padding: 4px 0; border-top: 1px solid var(--line); }
.ac-cst .s { font-weight: 700; }
.ac-cst .imp { text-align: right; font-weight: 700; white-space: nowrap; }
.ac-cst .pos, .ac-tab .pos { color: var(--pos); }
.ac-cst .neg, .ac-tab .neg { color: var(--neg); }
.ac-cap { font-size: 7.6pt; color: var(--muted); margin: 2px 0 4px; }
.ac-h { font-size: 9pt; font-weight: 700; margin: 10px 0 2px; }
.ac-act { border: 1px solid var(--line); border-radius: 5px; padding: 9px 12px; margin: 8px 0; font-size: 8.8pt; line-height: 1.5; }
.ac-act .t { font-weight: 700; margin-bottom: 3px; }
.ac-act .r { color: var(--muted); margin-top: 4px; }
</style>
"""


def _fmt(v, t):
    if v is None:
        return "—"
    if t == "n":
        return num(v)
    if t in ("u", "u-"):
        return num(v)
    if t in ("k", "k-", "kb"):
        return num(v / 1000, 1)
    if t == "p":
        return pct(v, 1)
    return num(v, 2)


def _var(a, b, t):
    """Variation d'une année à l'autre (ou écart avec le groupe) : % ou points."""
    if a is None or b is None:
        return "—"
    if t == "p":
        return pts(a - b, 1)
    if not b or abs(b) < 1e-9:
        return "—"
    r = (a - b) / abs(b)
    return "—" if abs(r) > 9.99 else pct(r, 0, sign=True)


def _cls(a, b, t):
    if a is None or b is None or a == b:
        return ""
    bon = (a < b) if t in ("k-", "u-") else (a > b)
    return "pos" if bon else "neg"


def table(S, dept, mode, P):
    an0, an1 = split(P)[0], split(P)[0] - 1
    head = (f'<thead><tr><th class="lab" rowspan="2">k$ sauf indication</th><th class="grp" colspan="3">{escape(S.nom)}</th>'
            f'<th class="grp sep" colspan="3">{escape(S.grp_long)}</th><th class="grp sep" colspan="2">{escape(S.court)} vs {escape(S.grp_court)}</th></tr>'
            f'<tr><th>{an0}</th><th>{an1}</th><th>Var. a/a</th><th class="sep">{an0}</th><th>{an1}</th><th>Var. a/a</th>'
            f'<th class="sep">{an0}</th><th>{an1}</th></tr></thead>')
    body = ""
    for k, lab, t in S.LIGNES[dept]:
        c0, c1, g0, g1 = (S.v(w, k, an, mode) for w, an in (("c", 0), ("c", 1), ("g", 0), ("g", 1)))
        if c0 is None and g0 is None:
            continue
        body += (f'<tr class="{"b" if t == "kb" else ""}"><td class="lab">{escape(lab)}</td>'
                 f'<td>{_fmt(c0, t)}</td><td>{_fmt(c1, t)}</td><td class="var {_cls(c0, c1, t)}">{_var(c0, c1, t)}</td>'
                 f'<td class="sep">{_fmt(g0, t)}</td><td>{_fmt(g1, t)}</td><td class="var">{_var(g0, g1, t)}</td>'
                 f'<td class="sep {_cls(c0, g0, t)}">{_var(c0, g0, t)}</td><td class="{_cls(c1, g1, t)}">{_var(c1, g1, t)}</td></tr>')
    if dept == "global":
        body += f'<tr><td class="lab" colspan="9" style="font-weight:700;padding-top:7px">{S.TITRE_PROFITS}</td></tr>'
        for k, lab in S.DEPT_PROFITS:
            c0, c1, g0, g1 = (S.v(w, k, an, mode) for w, an in (("c", 0), ("c", 1), ("g", 0), ("g", 1)))
            if c0 is None and g0 is None:
                continue
            body += (f'<tr><td class="lab">{escape(lab)}</td><td>{_fmt(c0, "k")}</td><td>{_fmt(c1, "k")}</td><td class="var {_cls(c0, c1, "k")}">{_var(c0, c1, "k")}</td>'
                     f'<td class="sep">{_fmt(g0, "k")}</td><td>{_fmt(g1, "k")}</td><td class="var">{_var(g0, g1, "k")}</td>'
                     f'<td class="sep {_cls(c0, g0, "k")}">{_var(c0, g0, "k")}</td><td class="{_cls(c1, g1, "k")}">{_var(c1, g1, "k")}</td></tr>')
    return f'<table class="ac-tab">{head}<tbody>{body}</tbody></table>'


def _ind_val(v, t):
    if v is None:
        return "—"
    if t == "u":
        return money(v)
    if t in ("p", "v"):
        return pct(v, 1, sign=(t == "v"))
    if t == "m":
        return num(v, 1)
    return num(v, 2)


def indicateurs(S, dept, mode, P):
    y = split(P)[0]
    per, per1 = _per(P, mode)
    cards = ""
    for k, titre, defi, t, sens in S.INDICATEURS[dept]:
        a, b = valeur_ind(S, k, "c", mode), valeur_ind(S, k, "g", mode)
        if a is None and b is None:
            continue          # ex. techniciens ou employés du groupe : mémo stats du composite pas encore lu
        top = max(abs(a or 0), abs(b or 0)) or 1
        bon = None if a is None or b is None else ((a >= b) if sens > 0 else (a <= b))
        col_c = "#008848" if bon else ("#c0392b" if bon is False else "#9b9a93")
        bars = ""
        for lab, val, col in ((S.court, a, col_c), (S.grp_barre, b, "#9b9a93")):
            w = 0 if val is None else max(2, abs(val) / top * 100)
            bars += (f'<div class="ac-bar"><span>{escape(lab)}</span><span class="tr"><span class="fl" style="display:block;width:{w:.0f}%;background:{col}"></span></span>'
                     f'<span class="v">{_ind_val(val, t)}</span></div>')
        d = defi.format(per=per, per1=per1, an=y, an1=y - 1)
        cards += f'<div class="ac-ic"><div class="ac-it">{escape(titre)}</div><div class="ac-id">{escape(d)}</div>{bars}</div>'
    return f'<div class="ac-ind">{cards}</div>'


def bloc_constats(S, dept, mode):
    cs = constats(S, dept, mode)[:3]
    if not cs:
        return '<p class="muted">Pas assez de chiffres du groupe pour chiffrer les écarts.</p>'
    li = ""
    for o in cs:
        cls = "pos" if o["sens"] > 0 else "neg"
        li += (f'<li><span class="s {cls}">{"▲" if o["sens"] > 0 else "▼"}</span><span>{escape(o["texte"])}</span>'
               f'<span class="imp {cls}">{kmoney(o["impact"], sign=True, dec=1)}</span></li>')
    quoi = "mensuel" if mode == "month" else "cumulatif"
    return (f'<div class="ac-cap">Impact {quoi} estimé par rapport {escape(S.g_a)} : vert = ce que l\'écart vous rapporte; '
            f'rouge = ce qu\'il faut aller chercher.</div><ul class="ac-cst">{li}</ul>')


def _retenir(S, dept, mode, P):
    k, lab = S.RETENIR[dept]
    c0, c1, g0, g1 = S.v("c", k, 0, mode), S.v("c", k, 1, mode), S.v("g", k, 0, mode), S.v("g", k, 1, mode)
    s = f"{lab} de <b>{money(c0)}</b>"
    if c1:
        s += f" ({_var(c0, c1, 'k')} par rapport à l'an passé)"
    if g0 is not None:
        s += f", contre {money(g0)} pour {escape(S.g_nom)}"
        if g1:
            s += f" ({_var(g0, g1, 'k')})"
    vol = S.VOL.get(dept)
    if vol:
        a, b = S.v("c", vol[0], 0, mode), S.v("g", vol[0], 0, mode)
        if a is not None:
            s += f"; {num(a)} {vol[1]}" + (f" contre {num(b)}" if b is not None else "")
    return s + "."


def page_dept(S, dept, mode, P):
    titre, eyebrow = next((t, e) for d, t, e in DEPTS if d == dept)
    y, m = split(P)
    per = f"{MOIS[m]} {y}" if mode == "month" else f"cumul janvier–{MOIS[m]} {y}"
    return (f'<div class="eyebrow">{eyebrow} · COMPARAISON AU COMPOSITE</div><h2>{escape(titre)} — {per}</h2>'
            + rc.key(_retenir(S, dept, mode, P))
            + table(S, dept, mode, P)
            + f'<div class="ac-h">Indicateurs avancés — {per}</div>'
            + f'<div class="ac-cap">{escape(S.nom)} contre {escape(S.grp_long)} (moyenne du groupe{", " + str(S.n) + " concessions" if S.n else ""}). '
              f'Vert : {escape(S.court)} fait mieux que le groupe; rouge : moins bien.</div>'
            + indicateurs(S, dept, mode, P)
            + f'<div class="ac-h">3 constats</div>' + bloc_constats(S, dept, mode))


def page_intro(S, P):
    y, m = split(P)
    if S.marque == "vw":
        t = (f"Les pages qui suivent comparent {escape(S.nom)} au <b>{escape(S.grp_long)}</b>, soit le concessionnaire moyen du "
             f"groupe de volume {escape(S.groupe.replace('Groupe ', ''))} de VW Canada, pour {MOIS[m]} {y} et {MOIS[m]} {y - 1}. "
             "Chaque département a deux pages : le mois, puis le cumul depuis janvier, dans le même format.")
        dep = ("<li>Les profits des départements sont ceux de l'état financier VW Canada : véhicules neufs et d'occasion après "
               "les incitatifs VW, les frais de documentation et la réserve (ligne 73); service au profit d'exploitation; pièces "
               "après l'escompte de commande de stock. Le profit net avant impôts est avant la rémunération des propriétaires.</li>")
        src = (f"Sources : états financiers VW Canada de la concession ({MOIS[m]} {y} et {MOIS[m]} {y - 1}) et {escape(S.source)} "
               f"({escape(S.groupe)}, {MOIS[m]} {y} et {MOIS[m]} {y - 1}). Format repris du rapport « Analyse des états financiers » "
               "de Mustafa Bhaloo.")
    else:
        compo = (f"{S.n} concessionnaires en {y} et {S.n_prec} en {y - 1} : la composition du groupe change d'une année à l'autre, "
                 "ce qui influence ses variations" if S.n and S.n_prec and S.n_prec != S.n else
                 (f"{S.n} concessionnaires" if S.n else ""))
        t = (f"Les pages qui suivent comparent {escape(S.nom)} au <b>{escape(S.grp_long)}</b>, soit le concessionnaire moyen du groupe "
             f"du {escape(S.source)} ({compo}), pour {MOIS[m]} {y} et {MOIS[m]} {y - 1}. "
             "Chaque département a deux pages : le mois, puis le cumul depuis janvier, dans le même format.")
        dep = ("<li>Les profits des départements sont après frais indirects (profit d'opération net), comme dans l'état financier Hyundai. "
               "La retenue et les incitatifs HACC, inscrits en autres revenus, sont attribués aux véhicules neufs (super profit brut).</li>")
        src = (f"Sources : état financier Hyundai Canada de la concession ({MOIS[m]} {y} et {MOIS[m]} {y - 1}) et {escape(S.source)} "
               f"du groupe {escape(S.groupe)} : P&P, analyse des revenus et mémo stats. Format repris du rapport « Analyse des états "
               "financiers » de Mustafa Bhaloo.")
    defs = ("<ul class='retenir'>"
            "<li>Le premier tableau présente le résultat du département, la variation d'une année à l'autre et l'écart en % avec le groupe "
            "(en points pour les marges). Un écart vert est favorable, rouge défavorable; pour les dépenses, vert veut dire plus bas.</li>"
            + dep +
            "<li>Les trois constats de chaque page sont les écarts qui pèsent le plus, chiffrés en dollars par rapport au groupe. "
            "Pour une variation d'une année à l'autre, l'impact applique à la concession la variation du groupe.</li>"
            "<li>La dernière page reprend, pour le mois, le plus grand écart défavorable de chaque département et les analyses à faire.</li></ul>")
    return (f'<div class="eyebrow">COMPARAISON AU COMPOSITE</div><h2>{escape(S.nom)} contre {escape(S.grp_long)}</h2>'
            + rc.key(t, "Base de présentation") + defs + f'<div class="note">{src}</div>')


def page_perspectives(S, P):
    y, m = split(P)
    rows = []
    for dept, titre, _ in DEPTS:
        cs = [o for o in constats(S, dept, "month") if o["sens"] < 0]
        if cs:
            rows.append((titre, cs[0]))
    rows.sort(key=lambda r: r[1]["impact"])
    if not rows:
        return None
    top = "; ".join(f"{t.lower()} ({kmoney(-o['impact'], dec=1)})" for t, o in rows[:3])
    tab = "".join(f'<tr><td class="lab">{escape(t)}</td><td class="lab">{escape(o["texte"].split(";")[0].split(". ")[0])}</td>'
                  f'<td class="neg">{kmoney(o["impact"], dec=1)}</td></tr>' for t, o in rows)
    acts = ""
    for i, (t, o) in enumerate(rows[:3], 1):
        acts += (f'<div class="ac-act"><div class="t">{i}. {escape(t)} : {escape(o["texte"].split(";")[0].split(". ")[0])}</div>'
                 f'{escape(o["texte"])}<div><b>Analyse à faire :</b> {escape(S.ANALYSES.get(o["cle"], "à préciser."))}</div>'
                 f'<div class="r">Responsable / échéance : [nom, date]</div></div>')
    return (f'<div class="eyebrow">PERSPECTIVES · COMPARAISON AU COMPOSITE</div><h2>Trois constats et analyses à faire</h2>'
            + rc.key(f"Par rapport {escape(S.g_a)}, les écarts qui pèsent le plus sur le résultat de {MOIS[m]} : {top} par mois.")
            + f'<div class="ac-h">Le plus grand écart défavorable de chaque département</div>'
            + f'<table class="ac-tab"><thead><tr><th class="lab">Département</th><th class="lab">Constat</th><th>Impact / mois</th></tr></thead><tbody>{tab}</tbody></table>'
            + acts)


def pages_hyundai(s, P, entry, prec=None):
    """entry : composite du mois (avec la concession) ; prec : composite du même mois l'an passé."""
    S = Hyundai(entry, prec)
    if not S.ok:
        return []
    out = [CSS + page_intro(S, P)]
    for dept, _, _ in DEPTS:
        for mode in ("month", "ytd"):
            out.append(page_dept(S, dept, mode, P))
    pp = page_perspectives(S, P)
    if pp:
        out.append(pp)
    return out


def pages_vw(s, P, entry, prec=None):
    """entry : composite VW du mois (état standard du groupe de volume, avec la concession) ;
    prec : composite du même mois l'an passé (état du groupe de cette année-là)."""
    S = VW(entry, prec)
    if not S.ok:
        return []
    out = [CSS + page_intro(S, P)]
    for dept, _, _ in DEPTS:
        for mode in ("month", "ytd"):
            out.append(page_dept(S, dept, mode, P))
    pp = page_perspectives(S, P)
    if pp:
        out.append(pp)
    return out
