# -*- coding: utf-8 -*-
"""
Couche de données du rapport mensuel KPI — Groupe Automax.

Lit data/data.json (produit par src/extract.py du tableau de bord) et expose,
pour chaque concession / période / mode (mois ou cumul) / base (réel, budget,
année précédente), un jeu de composantes normalisées :

  - dépenses en montants POSITIFS (le fichier les stocke négatives);
  - AP (année précédente) native du fichier source, sinon reconstituée à partir
    du même mois de l'an passé déjà en mémoire (même règle que le tableau de bord);
  - budget natif, sinon lu dans budgets.csv (facultatif), sinon absent;
  - mois manquants reconstitués quand les cumuls le permettent (ex. Hyundai mai).

Chaque valeur reconstituée est tracée dans Store.notes pour la page
« Qualité et couverture des données ».
"""
import csv
import json
import os
from collections import OrderedDict

DEALERS = OrderedDict([
    ("bmw", "BMW Sherbrooke"),
    ("vw", "Volkswagen"),
    ("stm", "STM (Ste-Marie)"),
    ("hyundai", "Hyundai"),
    ("hawks", "HAWKS"),
])
DEALER_SHORT = {"bmw": "BMW", "vw": "VW", "stm": "STM", "hyundai": "Hyundai", "hawks": "HAWKS"}

MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]

DEPTS = ["neuf", "usage", "service", "carrosserie", "pieces"]

# Indicateurs lus dans le fichier (clé data.json -> clé interne)
BASE_KEYS = [
    "ventes_nettes", "pb_total", "pb_neuf", "pb_usage", "pb_service",
    "pb_carrosserie", "pb_pieces", "autres_revenus", "depenses",
    "depenses_variables", "depenses_personnel", "depenses_semifixes",
    "ebitda", "ebt", "unites_neuf", "unites_usage", "unites_flottes",
]
# Indicateurs acceptés dans budgets.csv (mêmes clés, dépenses en positif)
BUDGET_CSV_KEYS = [k for k in BASE_KEYS if k != "ebitda"]
EXPENSE_KEYS = {"depenses", "depenses_variables", "depenses_personnel", "depenses_semifixes"}


def pkey(y, m):
    return f"{y:04d}-{m:02d}"


def split(p):
    y, m = p.split("-")
    return int(y), int(m)


def prev_month(p):
    y, m = split(p)
    return pkey(y, m - 1) if m > 1 else pkey(y - 1, 12)


def next_month(p):
    y, m = split(p)
    return pkey(y, m + 1) if m < 12 else pkey(y + 1, 1)


def prior_year(p):
    y, m = split(p)
    return pkey(y - 1, m)


def label_period(p, cap=False):
    y, m = split(p)
    s = f"{MOIS[m]} {y}"
    return s[0].upper() + s[1:] if cap else s


def _num(x):
    return x if isinstance(x, (int, float)) else None


class Store:
    def __init__(self, data_path, budget_csv=None):
        with open(data_path, encoding="utf-8") as f:
            self.raw = json.load(f)["dealers"]
        self.notes = []          # (concession, période, texte) des valeurs reconstituées
        self._note_keys = set()
        self.budget_csv = {}     # (dealer, period, key) -> valeur (dépenses positives)
        if budget_csv and os.path.exists(budget_csv):
            self._load_budget_csv(budget_csv)
        self._cache = {}

    # ------------------------------------------------------------------ notes
    def note(self, dealer, period, text):
        k = (dealer, period, text)
        if k not in self._note_keys:
            self._note_keys.add(k)
            self.notes.append(k)

    # ------------------------------------------------------------ budget CSV
    def _load_budget_csv(self, path):
        """Format large (recommandé) : concession, indicateur, libelle, AAAA-01 … AAAA-12.
        Format long accepté aussi : concession, periode, indicateur, budget.
        Dépenses saisies en montants positifs."""
        def to_f(v):
            v = (v or "").strip().replace("\u00a0", "").replace("\u202f", "").replace(" ", "").replace("$", "").replace(",", ".")
            try:
                return float(v) if v else None
            except ValueError:
                return None
        with open(path, encoding="utf-8-sig") as f:
            rd = csv.DictReader(f)
            cols = rd.fieldnames or []
            long_fmt = "periode" in cols
            for row in rd:
                d = (row.get("concession") or "").strip().lower()
                k = (row.get("indicateur") or "").strip()
                if not (d and k):
                    continue
                if long_fmt:
                    p, v = (row.get("periode") or "").strip(), to_f(row.get("budget"))
                    if p and v is not None:
                        self.budget_csv[(d, p, k)] = v
                else:
                    for c in cols:
                        if len(c) == 7 and c[4] == "-" and c[:4].isdigit():
                            v = to_f(row.get(c))
                            if v is not None:
                                self.budget_csv[(d, c, k)] = v

    # ----------------------------------------------------------- raw access
    def periods(self, dealer):
        return sorted(self.raw.get(dealer, {}).get("periods", {}).keys())

    def source_format(self, dealer, period):
        """Format du fichier source d'un mois : « gabarit » (Réalisé du Groupe),
        « etat_gm » (état financier GM : HAWKS, STM) ou « etat_hyundai » (état
        financier Hyundai Canada). Les anciens enregistrements n'ont pas le
        champ : HAWKS = état GM, les autres = gabarit."""
        p = self.raw.get(dealer, {}).get("periods", {}).get(period)
        if not p:
            return None
        return p.get("source_format") or ("etat_gm" if dealer == "hawks" else "gabarit")

    def _native_section(self, dealer, period, mode):
        p = self.raw.get(dealer, {}).get("periods", {}).get(period)
        if not p:
            return None
        sec = p.get("sections", {}).get(mode)
        if not sec:
            return None
        kp = sec.get("kpis", {})
        if _num((kp.get("pb_total") or {}).get("real")) is None:
            return None
        return sec

    def section_kv(self, dealer, period, mode):
        """{clé: {'real','budget','prior_year'}} pour une concession/période/mode,
        avec reconstitution des mois manquants. None si indisponible."""
        ck = ("kv", dealer, period, mode)
        if ck in self._cache:
            return self._cache[ck]
        out = None
        sec = self._native_section(dealer, period, mode)
        if sec is not None:
            out = {k: {f: _num((sec["kpis"].get(k) or {}).get(f)) for f in ("real", "budget", "prior_year")}
                   for k in BASE_KEYS}
        else:
            out = self._derive(dealer, period, mode)
        self._cache[ck] = out
        return out

    def _derive(self, dealer, period, mode):
        y, m = split(period)
        if mode == "month":
            # Janvier : le mois = le cumul
            if m == 1:
                ytd = self._native_section(dealer, period, "ytd")
                if ytd is not None:
                    self.note(dealer, period, "Mois reconstitué à partir du cumul (janvier : mois = cumul)")
                    return {k: {f: _num((ytd["kpis"].get(k) or {}).get(f)) for f in ("real", "budget", "prior_year")}
                            for k in BASE_KEYS}
            # Mois manquant : cumul(M+1) − cumul(M−1) − mois(M+1)
            if 1 < m < 12:
                a = self._native_section(dealer, next_month(period), "ytd")
                b = self._native_section(dealer, prev_month(period), "ytd")
                c = self._native_section(dealer, next_month(period), "month")
                if a is not None and b is not None and c is not None:
                    out = {}
                    for k in BASE_KEYS:
                        out[k] = {}
                        for f in ("real", "prior_year"):
                            va = _num((a["kpis"].get(k) or {}).get(f))
                            vb = _num((b["kpis"].get(k) or {}).get(f))
                            vc = _num((c["kpis"].get(k) or {}).get(f))
                            out[k][f] = None if None in (va, vb, vc) else va - vb - vc
                        out[k]["budget"] = None
                    self.note(dealer, period, f"Mois absent des fichiers : reconstitué (cumul {label_period(next_month(period))} − cumul {label_period(prev_month(period))} − mois de {MOIS[m+1]})")
                    return out
        else:
            # Cumul manquant : cumul(M−1) + mois(M)
            if m > 1:
                b = self._native_section(dealer, prev_month(period), "ytd")
                c = self.section_kv(dealer, period, "month")
                if b is not None and c is not None:
                    out = {}
                    for k in BASE_KEYS:
                        out[k] = {}
                        for f in ("real", "prior_year"):
                            vb = _num((b["kpis"].get(k) or {}).get(f))
                            vc = c[k][f]
                            out[k][f] = None if None in (vb, vc) else vb + vc
                        out[k]["budget"] = None
                    return out
        return None

    # ------------------------------------------------------------- bases
    def has_native_budget(self, dealer, period, mode):
        kv = self.section_kv(dealer, period, mode)
        if not kv:
            return False
        b1, b2 = kv["pb_total"]["budget"], kv["ebt"]["budget"]
        return bool(b1) or bool(b2)   # 0 = non saisi (Hyundai 2026)

    def has_native_ap(self, dealer, period, mode):
        kv = self.section_kv(dealer, period, mode)
        return bool(kv and kv["pb_total"]["prior_year"])

    def budget_source(self, dealer, period, mode):
        if self.has_native_budget(dealer, period, mode):
            return "natif"
        if self._csv_budget_complete(dealer, period, mode):
            return "csv"
        return None

    def ap_source(self, dealer, period, mode):
        if self.has_native_ap(dealer, period, mode):
            return "natif"
        if self.section_kv(dealer, prior_year(period), mode):
            return "reconstitue"
        return None

    def _csv_months(self, period, mode):
        y, m = split(period)
        return [period] if mode == "month" else [pkey(y, i) for i in range(1, m + 1)]

    def _csv_budget_complete(self, dealer, period, mode):
        if not self.budget_csv:
            return False
        return all((dealer, p, "pb_total") in self.budget_csv and (dealer, p, "ebt") in self.budget_csv
                   for p in self._csv_months(period, mode))

    def value(self, dealer, period, mode, key, base):
        """Valeur brute (signe du fichier : dépenses négatives)."""
        kv = self.section_kv(dealer, period, mode)
        if not kv:
            return None
        if base == "real":
            return kv[key]["real"]
        if base == "budget":
            src = self.budget_source(dealer, period, mode)
            if src == "natif":
                return kv[key]["budget"]
            if src == "csv":
                tot = 0.0
                for p in self._csv_months(period, mode):
                    v = self.budget_csv.get((dealer, p, key))
                    if v is None:
                        return None
                    tot += -v if key in EXPENSE_KEYS else v
                return tot
            return None
        if base == "ap":
            src = self.ap_source(dealer, period, mode)
            if src == "natif":
                return kv[key]["prior_year"]
            if src == "reconstitue":
                pkv = self.section_kv(dealer, prior_year(period), mode)
                return pkv[key]["real"]
            return None
        raise ValueError(base)

    # -------------------------------------------------------- composantes
    def comp(self, dealer, period, mode, base):
        ck = ("comp", dealer, period, mode, base)
        if ck in self._cache:
            return self._cache[ck]
        v = lambda k: self.value(dealer, period, mode, k, base)
        out = None
        if v("pb_total") is not None and v("ebt") is not None:
            c = {}
            c["ventes"] = v("ventes_nettes") or 0.0
            c["pb"] = v("pb_total")
            for d in DEPTS:
                c["pb_" + d] = v("pb_" + d) or 0.0
            c["pb_autres"] = c["pb"] - sum(c["pb_" + d] for d in DEPTS)
            c["ar"] = v("autres_revenus") or 0.0
            c["dep"] = -(v("depenses") or 0.0)
            c["dep_var"] = -(v("depenses_variables") or 0.0)
            c["dep_pers"] = -(v("depenses_personnel") or 0.0)
            c["dep_semi"] = -(v("depenses_semifixes") or 0.0)
            c["dep_autres"] = c["dep"] - c["dep_var"] - c["dep_pers"] - c["dep_semi"]
            c["ebt"] = v("ebt")
            # éléments sous le BAIIA (amortissement, etc.) : PB + AR − dépenses − EBT
            c["sous_baiia"] = c["pb"] + c["ar"] - c["dep"] - c["ebt"]
            e = v("ebitda")
            c["baiia"] = e if e is not None else c["pb"] + c["ar"] - c["dep"]
            c["u_neuf"] = v("unites_neuf") or 0.0
            c["u_usage"] = v("unites_usage") or 0.0
            c["u_flottes"] = v("unites_flottes") or 0.0
            out = c
        self._cache[ck] = out
        return out


# --------------------------------------------------------------- ratios
def ratios(c):
    """Indicateurs dérivés à partir des composantes (réel, budget ou AP)."""
    if not c:
        return {}
    div = lambda a, b: (a / b) if b else None
    apres_vente = c["pb_service"] + c["pb_carrosserie"] + c["pb_pieces"]
    frais_fixes = c["dep"] - c["dep_var"]
    u_detail = c["u_neuf"] + c["u_usage"]
    return {
        "marge_brute": div(c["pb"], c["ventes"]),
        "gpa_neuf": div(c["pb_neuf"], c["u_neuf"]),
        "gpa_usage": div(c["pb_usage"], c["u_usage"]),
        "pb_vehicules_unite": div(c["pb_neuf"] + c["pb_usage"], u_detail),
        "ratio_usage_neuf": div(c["u_usage"], c["u_neuf"]),
        "absorption": div(apres_vente, frais_fixes),
        "part_apres_vente": div(apres_vente, c["pb"]),
        "dep_pct_pb": div(c["dep"], c["pb"]),
        "pers_pct_pb": div(c["dep_pers"], c["pb"]),
        "ebt_pct_pb": div(c["ebt"], c["pb"]),
        "ros": div(c["ebt"], c["ventes"]),
        "ebt_unite": div(c["ebt"], u_detail),
        "u_detail": u_detail,
        "apres_vente": apres_vente,
    }


def add_comps(comps):
    comps = [c for c in comps if c]
    if not comps:
        return None
    out = {}
    for k in comps[0]:
        out[k] = sum(c[k] for c in comps)
    return out


# ------------------------------------------------------------ pont d'écart
BRIDGE_ITEMS = [
    # clé, libellé, famille (pour le graphique condensé)
    ("neuf_vol", "Véhicules neufs — volume", "PB neufs"),
    ("neuf_marge", "Véhicules neufs — profit par unité", "PB neufs"),
    ("neuf_nd", "Véhicules neufs — non décomposé¹", "PB neufs"),
    ("usage_vol", "Véhicules usagés — volume", "PB usagés"),
    ("usage_marge", "Véhicules usagés — profit par unité", "PB usagés"),
    ("usage_nd", "Véhicules usagés — non décomposé¹", "PB usagés"),
    ("service", "Service", "Après-vente"),
    ("carrosserie", "Carrosserie", "Après-vente"),
    ("pieces", "Pièces", "Après-vente"),
    ("pb_autres", "Autres sources de PB (gros, F&I, divers)", "Autres PB"),
    ("ar", "Autres revenus", "Autres revenus"),
    ("dep_var", "Dépenses variables", "Dépenses variables"),
    ("dep_pers", "Dépenses de personnel", "Personnel"),
    ("dep_semi", "Dépenses semi-fixes", "Semi-fixes et autres"),
    ("dep_autres", "Autres dépenses (fixes non ventilées)", "Semi-fixes et autres"),
    ("sous_baiia", "Amortissement et éléments sous le BAIIA", "Amortissement"),
]
BRIDGE_FAMILIES = ["PB neufs", "PB usagés", "Après-vente", "Autres PB", "Autres revenus",
                   "Dépenses variables", "Personnel", "Semi-fixes et autres", "Amortissement"]


GPA_PLAUSIBLE_MAX = 15000.0   # $/unité au-delà duquel le nombre d'unités de référence est jugé incomplet


def split_fiable(pb_b, u_b, u_r):
    """La décomposition volume / profit par unité n'a de sens que si la base
    compte assez d'unités et un profit par unité plausible."""
    if not u_b or u_b < 5:
        return False
    if abs(pb_b / u_b) > GPA_PLAUSIBLE_MAX:
        return False
    if u_r > 2.5 * u_b or u_r < 0.4 * u_b:
        return False
    return True


def _vol_marge(pb_r, u_r, pb_b, u_b):
    """Décompose Δ PB en effet volume (au profit/unité de référence) et effet
    profit par unité (au volume réel). Somme = Δ PB exactement. Si la
    décomposition n'est pas fiable, tout l'écart va dans une 3e composante
    « non décomposé »."""
    if split_fiable(pb_b, u_b, u_r):
        vol = (u_r - u_b) * (pb_b / u_b)
        return vol, (pb_r - pb_b) - vol, 0.0, True
    return 0.0, 0.0, pb_r - pb_b, False


class Bridge(OrderedDict):
    """Pont d'écart : postes -> contribution à l'écart d'EBT. `non_decompose`
    liste les familles (neuf/usage) dont l'effet volume n'a pas été isolé."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.non_decompose = set()


def bridge(real, base):
    """Contribution de chaque poste à l'écart d'EBT (réel − base). Positif = favorable."""
    if not real or not base:
        return None
    b = Bridge()
    b["neuf_vol"], b["neuf_marge"], b["neuf_nd"], ok_n = _vol_marge(real["pb_neuf"], real["u_neuf"], base["pb_neuf"], base["u_neuf"])
    b["usage_vol"], b["usage_marge"], b["usage_nd"], ok_u = _vol_marge(real["pb_usage"], real["u_usage"], base["pb_usage"], base["u_usage"])
    if not ok_n:
        b.non_decompose.add("neuf")
    if not ok_u:
        b.non_decompose.add("usage")
    for k in ("service", "carrosserie", "pieces"):
        b[k] = real["pb_" + k] - base["pb_" + k]
    b["pb_autres"] = real["pb_autres"] - base["pb_autres"]
    b["ar"] = real["ar"] - base["ar"]
    for k in ("dep_var", "dep_pers", "dep_semi", "dep_autres", "sous_baiia"):
        b[k] = -(real[k] - base[k])
    return b


def bridge_sum(bridges):
    bridges = [x for x in bridges if x]
    if not bridges:
        return None
    out = Bridge()
    for k in bridges[0]:
        out[k] = sum(x[k] for x in bridges)
    for x in bridges:
        out.non_decompose |= getattr(x, "non_decompose", set())
    return out


def bridge_label(key, b=None):
    """Libellé d'un poste du pont, adapté quand la décomposition n'est pas faite."""
    return dict((k, l) for k, l, _ in BRIDGE_ITEMS)[key]


def bridge_families(b):
    fam = OrderedDict((f, 0.0) for f in BRIDGE_FAMILIES)
    for key, _, f in BRIDGE_ITEMS:
        fam[f] += b[key]
    return fam
