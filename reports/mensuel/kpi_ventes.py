# -*- coding: utf-8 -*-
"""Ventes de véhicules (neufs et usagés) : vue normalisée pour les rapports
« Ventes » (demande de Maxime Allard, 29 septembre 2026 : « fais un rapport
détaillé pour les ventes comme tu as fait pour les fixes »).

Source : data.json, déjà extrait par src/extract.py — indicateurs (unités,
profit brut, profit véhicule, F&I, gros) et lignes des départements
« Véhicules neufs » et « Véhicules usagés » (ventes, modèles, F&I par produit,
commissions, publicité, intérêts sur stocks, préparation, dépenses, autres
revenus, profit départemental). Les libellés diffèrent d'un format à l'autre
(Réalisé du Groupe, état GM, état Hyundai Canada, état Volkswagen Canada) :
LINE_RULES les ramène à des clés communes.

Chaque vue = {"neuf": {...}, "usage": {...}} pour une concession, un mois, un
mode (month | ytd) et une base (real | ap | budget). Groupe = somme des
concessions ; ratios recalculés à partir des sommes, seulement sur les
concessions qui ont le numérateur et le dénominateur.
"""
import re
import unicodedata

from kpi_data import DEALERS, prior_year, GPA_PLAUSIBLE_MAX

DEPT_NAMES = {"neuf": "Véhicules neufs", "usage": "Véhicules usagés"}
GROUP = "groupe"


def _sa(s):
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("’", "'").replace("œ", "oe")
    return re.sub(r"\s+", " ", s.lower()).strip()


# (clé, départements, expression) : montants additionnés sur les lignes non totales.
LINE_RULES = [
    ("ventes", ("neuf", "usage"), r"^ventes nettes$"),
    ("comm_vend", ("neuf", "usage"), r"^comm\.? vendeurs|^remuneration vendeurs|^salaires et commissions - personnel de ventes"),
    ("comm_fi", ("neuf", "usage"), r"^comm\.? f ?& ?i|^salaires et commissions - bureau commercial"),
    ("pub", ("neuf", "usage"), r"^publicite|ristournes de publicite|coop rabais publicite|commerce electronique"),
    ("int_stocks", ("neuf", "usage"), r"^interet de gros|^interet-financement des stocks|^interet-credit financement des stocks|^frais de financement$"),
    ("prep", ("neuf", "usage"), r"^frais de livraison|^preparation a la route|^service gratuit|travaux a titre gracieux|^pratiques de garantie|^entretien stock"),
    ("fi_fin", ("neuf", "usage"), r"^rev\.? finances"),
    ("fi_prot", ("neuf", "usage"), r"^rev\.? protections"),
    ("fi_aut", ("neuf", "usage"), r"^rev\.? autres"),
    ("gros_ligne", ("neuf", "usage"), r"^ventes au gros"),
    ("demos", ("neuf",), r"^ex-demos|^demos"),
    ("flottes_ligne", ("neuf",), r"^flottes$"),
    ("rachat_bail", ("neuf", "usage"), r"^rachat bail"),
]
# Lignes de modèles (profit brut et unités au détail)
MIX_RULES = {
    "neuf": [("Autos", r"^autos detail"), ("Camions et VUS", r"^camions detail"), ("Véhicules électriques", r"^vehicules electriques"),
             ("Modèles fin de série", r"^modeles fin de serie"), ("Sprinter", r"^sprinter"), ("Motos", r"^moto")],
    "usage": [("Certifiés", r"^certifie"), ("Non certifiés", r"^non certifie"), ("Autres marques", r"^autres marques")],
}
UNIT_KEYS = ("gros_ligne", "demos", "flottes_ligne")     # lignes dont on garde aussi les unités


def _field(x, f):
    if isinstance(x, dict):
        v = x.get(f)
    else:
        v = x if f == "real" else None
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def canon_dept(dep, f, suf):
    """Clés communes d'un département (dict de data.json) pour le champ f."""
    if not dep:
        return {}
    out = {}
    items = dep.get("line_items") or []
    for it in items:
        if it.get("is_total"):
            continue
        lab = _sa(it.get("label"))
        mv = _field(it.get("money"), f)
        uv = _field(it.get("units"), f)
        for k, depts, rx in LINE_RULES:
            if suf in depts and re.search(rx, lab):
                if mv is not None:
                    out[k] = (out.get(k) or 0.0) + mv
                if k in UNIT_KEYS and uv is not None:
                    out[k + "_u"] = (out.get(k + "_u") or 0.0) + uv
                break
        for name, rx in MIX_RULES[suf]:
            if re.search(rx, lab) and (mv is not None or uv is not None):
                mix = out.setdefault("mix", {})
                cur = mix.setdefault(name, {"pb": 0.0, "u": 0.0})
                cur["pb"] += mv or 0.0
                cur["u"] += uv or 0.0
                break
    for k, dk in (("dep", "total_depenses"), ("pers", "total_personnel"), ("var", "total_variables"),
                  ("ar", "autres_revenus"), ("profit", "profit_departemental")):
        v = _field(dep.get(dk), f)
        if v is not None:
            out[k] = v
    # mix sans unités ni profit : inutile
    if out.get("mix"):
        out["mix"] = {k: v for k, v in out["mix"].items() if v["u"] or v["pb"]}
    return out


class VStore:
    def __init__(self, s):
        self.s = s
        self.raw = s.raw
        self._c = {}

    def _depts(self, d, p, mode):
        sec = self.s._native_section(d, p, mode)
        return (sec or {}).get("departments") or {}

    def _lines(self, d, P, mode, base):
        """(départements, champ) selon la base ; None si indisponible."""
        if base == "real":
            return self._depts(d, P, mode), "real"
        if base == "ap":
            src = self.s.ap_source(d, P, mode)
            if src == "natif":
                return self._depts(d, P, mode), "prior_year"
            if src == "reconstitue":
                return self._depts(d, prior_year(P), mode), "real"
            return None, None
        if base == "budget":
            if self.s.budget_source(d, P, mode) == "natif":
                return self._depts(d, P, mode), "budget"
            return None, None
        raise ValueError(base)

    def view(self, d, P, mode, base="real"):
        ck = (d, P, mode, base)
        if ck in self._c:
            return self._c[ck]
        if d == GROUP:
            raise ValueError("utiliser group()")
        c = self.s.comp(d, P, mode, base)
        out = None
        if c:
            deps, f = self._lines(d, P, mode, base)
            if base == "ap" and not self.same_format(d, P, mode):
                deps = None      # lignes de formats différents (ex. Réalisé 2025 / état 2026) : non comparées
            out = {}
            for suf, dn in DEPT_NAMES.items():
                v = {"u": c["u_" + suf], "pb": c["pb_" + suf], "pbv": c["pbv_" + suf], "fi": c["fi_" + suf],
                     "gros": c["gros_" + suf]}
                if suf == "neuf":
                    v["u_fl"] = c.get("u_flottes")
                if deps and f:
                    v.update(canon_dept(deps.get(dn), f, suf))
                out[suf] = v
            out["ventes_tot"] = c["ventes"]
        self._c[ck] = out
        return out

    def same_format(self, d, P, mode="ytd"):
        """Les lignes de l'an passé viennent-elles du même format de fichier ?"""
        if self.s.ap_source(d, P, mode) == "natif":
            return True
        return self.s.source_format(d, P) == self.s.source_format(d, prior_year(P))

    def dealers(self, P, mode="ytd"):
        return [d for d in DEALERS if self.view(d, P, mode)]

    def group(self, P, mode, base="real", dealers=None, require=None):
        """Somme des concessions. require : base qui doit aussi exister
        (périmètre comparable, ex. 'ap')."""
        ds = [d for d in (dealers or DEALERS) if self.view(d, P, mode, base)
              and (require is None or self.view(d, P, mode, require))]
        if not ds:
            return None
        out = {"_dealers": ds}
        for suf in DEPT_NAMES:
            views = [self.view(d, P, mode, base)[suf] for d in ds]
            out[suf] = {"_parts": views}
        return out

    def pair(self, d, P, mode):
        if d == GROUP:
            return self.group(P, mode, "real", require="ap"), self.group(P, mode, "ap", require="real")
        return self.view(d, P, mode, "real"), self.view(d, P, mode, "ap")


# ------------------------------------------------------------------ indicateurs
def _sum(parts, k, need=None):
    """Somme de k sur les parties (et, si need, seulement celles où need existe aussi)."""
    tot, ok = 0.0, False
    for p in parts:
        v = p.get(k)
        if v is None or (need and p.get(need) is None):
            continue
        tot += v
        ok = True
    return tot if ok else None


def _ratio(v, num, den):
    """Ratio num / den ; au Groupe, seulement sur les concessions qui ont les deux."""
    parts = v.get("_parts")
    if parts is None:
        a, b = v.get(num), v.get(den)
        return a / b if a is not None and b else None
    a = _sum([p for p in parts if p.get(den) is not None], num)
    b = _sum([p for p in parts if p.get(num) is not None], den)
    return a / b if a is not None and b else None


def get(v, k):
    """Valeur d'une vue de département (concession ou Groupe)."""
    if v is None:
        return None
    if "_parts" in v:
        if k == "mix":
            mix = {}
            for p in v["_parts"]:
                for name, m in (p.get("mix") or {}).items():
                    cur = mix.setdefault(name, {"pb": 0.0, "u": 0.0})
                    cur["pb"] += m["pb"]
                    cur["u"] += m["u"]
            return mix or None
        return _sum(v["_parts"], k)
    return v.get(k)


def metrics(v):
    """Indicateurs d'un département : volumes, montants et par unité."""
    if v is None:
        return {}
    g = lambda k: get(v, k)
    m = {k: g(k) for k in ("u", "u_fl", "pb", "pbv", "fi", "gros", "ventes", "comm_vend", "comm_fi", "pub", "int_stocks",
                           "prep", "fi_fin", "fi_prot", "fi_aut", "gros_ligne", "gros_ligne_u", "demos", "demos_u",
                           "flottes_ligne", "flottes_ligne_u", "dep", "pers", "ar", "profit", "rachat_bail")}
    per = lambda k: _ratio(v, k, "u")
    m.update({
        "pbv_u": per("pbv"), "fi_u": per("fi"), "comm_u": per("comm_vend"), "pub_u": per("pub"),
        "int_u": per("int_stocks"), "prep_u": per("prep"), "profit_u": per("profit"),
        "comm_fi_pct": _ratio(v, "comm_fi", "fi"), "comm_pct_pbv": _ratio(v, "comm_vend", "pbv"),
        "dep_pct_pb": _ratio(v, "dep", "pb"),
        "gros_pb_u": _ratio(v, "gros_ligne", "gros_ligne_u"),
    })
    if m["comm_pct_pbv"] is not None and (not m["pbv"] or m["pbv"] <= 0 or m["comm_pct_pbv"] > 1.5):
        m["comm_pct_pbv"] = None     # profit véhicule nul ou très faible : ratio sans signification
    if m["pbv_u"] is not None and m["fi_u"] is not None:
        m["tot_u"] = m["pbv_u"] + m["fi_u"]
    else:
        m["tot_u"] = None
    # montants par unité invraisemblables (unités de référence incomplètes) : écartés
    for k in ("pbv_u", "fi_u", "tot_u"):
        if m[k] is not None and abs(m[k]) > GPA_PLAUSIBLE_MAX:
            m[k] = None
    fi_parts = [m["fi_fin"], m["fi_prot"], m["fi_aut"]]
    m["fi_detail"] = None if all(x is None for x in fi_parts) else sum(x or 0 for x in fi_parts)
    m["mix"] = g("mix")
    return m


def both(view):
    """Neufs + usagés (unités détail, profit véhicule, F&I)."""
    if not view:
        return {}
    n, u = metrics(view.get("neuf")), metrics(view.get("usage"))
    s = lambda k: None if n.get(k) is None and u.get(k) is None else (n.get(k) or 0) + (u.get(k) or 0)
    out = {k: s(k) for k in ("u", "pb", "pbv", "fi", "gros")}
    out["tot_u"] = (out["pbv"] + out["fi"]) / out["u"] if out["u"] and out["pbv"] is not None and out["fi"] is not None else None
    return out
