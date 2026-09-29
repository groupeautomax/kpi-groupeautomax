# -*- coding: utf-8 -*-
"""
Opérations fixes (après-vente) : lecture et calculs à partir de data.json.

Chaque période de data.json porte, dans sections.<mois|cumul>.apres_vente, le
détail lu par src/apres_vente.py (BT par type, main-d'œuvre, pièces, heures,
atelier). Ce module en tire, par concession et pour le Groupe :

  - par type de BT (client, garantie, entretien BMW, interne, esthétique) : nombre de BT,
    main-d'œuvre par BT, pièces par BT, total par BT, profit brut par BT,
    heures vendues par BT, taux effectif (M-O ÷ heures), marges ;
  - atelier : heures disponibles, pointées, vendues, productivité, efficacité ;
  - pièces par canal, carrosserie ;
  - comparaison à l'an passé : colonnes « an passé » du Réalisé si présentes,
    sinon le même mois de l'an passé (même règle que le reste du rapport).

Ratios du Groupe recalculés à partir des sommes ; heures : seulement les
concessions qui en ont (périmètre indiqué).
"""
from collections import OrderedDict

from kpi_data import DEALERS, prior_year, split, pkey

TYPES = OrderedDict([
    ("client", "Client (détail)"),
    ("garantie", "Garantie"),
    ("entretien", "Entretien BMW"),
    ("interne", "Interne"),
    ("esthetique", "Esthétique"),
])
MAIN_TYPES = ("client", "garantie", "interne")
# Types qui portent des pièces ; « entretien » : BMW seulement (état BMW Canada,
# pages 8 et 9 : entretien payé par BMW, BMW Service Inclus).
PC_TYPES = ("client", "garantie", "entretien", "interne")


def types_for(f, types=PC_TYPES):
    """Types principaux + entretien quand la concession en a (BMW)."""
    return [t for t in types if t in MAIN_TYPES or (((f or {}).get("types") or {}).get(t) or {}).get("bt")]

DETAIL_LABELS = {"mobile": "dont service mobile", "inspection": "dont inspection des neufs"}
MEAS = (("bt", "bt"), ("mo_ventes", "mo_v"), ("mo_pb", "mo_pb"), ("pc_ventes", "pc_v"),
        ("pc_pb", "pc_pb"), ("heures", "h"))
PC_CHANNELS = OrderedDict([
    ("client", "BT client"), ("garantie", "BT garantie"), ("entretien", "BT entretien BMW"), ("interne", "BT interne"),
    ("carrosserie", "Carrosserie"), ("comptoir", "Comptoir (détail)"), ("accessoires", "Accessoires"),
    ("gros", "Gros"), ("pneus", "Pneus"), ("huile", "Huiles et graisse"), ("divers", "Divers"),
])


def _n(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def div(a, b):
    return (a / b) if (a is not None and b) else None


def _field(kv, field):
    return _n((kv or {}).get(field)) if isinstance(kv, dict) else None


def flat(av, field="real"):
    """Vue « à plat » d'un bloc apres_vente pour une base (real, prior_year, budget)."""
    if not av:
        return None
    out = {"types": {}, "detail": {}, "pieces": {}, "service": {}, "carrosserie": {}, "atelier": {}}
    for typ, m in (av.get("types") or {}).items():
        out["types"][typ] = {k2: _field(m.get(k1), field) for k1, k2 in MEAS}
    for typ, m in (av.get("detail") or {}).items():
        out["detail"][typ] = {k2: _field(m.get(k1), field) for k1, k2 in MEAS}
    for ch, m in (av.get("pieces") or {}).items():
        out["pieces"][ch] = {"v": _field(m.get("ventes"), field), "pb": _field(m.get("pb"), field)}
    for k, m in (av.get("service") or {}).items():
        out["service"][k] = {"v": _field(m.get("ventes"), field), "pb": _field(m.get("pb"), field),
                             "bt": _field(m.get("bt"), field)}
    for k, m in (av.get("carrosserie") or {}).items():
        out["carrosserie"][k] = {"v": _field(m.get("ventes"), field), "pb": _field(m.get("pb"), field),
                                 "bt": _field(m.get("bt"), field)}
    if field == "real":
        out["atelier"] = dict(av.get("atelier") or {})
    # heures à 0 alors qu'il y a de la main-d'œuvre : donnée absente, pas zéro
    for t in list(out["types"].values()) + list(out["detail"].values()):
        if not t.get("h") and t.get("h") is not None:
            t["h"] = None
        _set_bt_base(t)
    # sans aucun BT ni montant pour cette base : rien
    has = any(v for t in out["types"].values() for v in t.values() if v)
    return out if has else None


BT_BASED = ("mo_v", "mo_pb", "pc_v", "pc_pb")


def _set_bt_base(t):
    """Montants qui servent aux ratios « par BT » : seulement si le type a des
    BT (ex. esthétique VW : ventes sans nombre de BT, exclues des ratios)."""
    for m in BT_BASED:
        t[m + "_b"] = t.get(m) if t.get("bt") else None


def type_metrics(t):
    """Indicateurs d'un type de BT (dict bt, mo_v, mo_pb, pc_v, pc_pb, h)."""
    if not t:
        return {}
    bt, mo, pc = t.get("bt"), t.get("mo_v"), t.get("pc_v")
    mo_pb, pc_pb, h = t.get("mo_pb"), t.get("pc_pb"), t.get("h")
    tot = (mo or 0) + (pc or 0) if (mo is not None or pc is not None) else None
    pb = (mo_pb or 0) + (pc_pb or 0) if (mo_pb is not None or pc_pb is not None) else None
    # montants des seules concessions qui ont des BT pour ce type (ratios par BT)
    g = lambda m: t.get(m + "_b", t.get(m) if bt else None)
    mob, pcb, mopbb, pcpbb = g("mo_v"), g("pc_v"), g("mo_pb"), g("pc_pb")
    totb = (mob or 0) + (pcb or 0) if (mob is not None or pcb is not None) else None
    pbb = (mopbb or 0) + (pcpbb or 0) if (mopbb is not None or pcpbb is not None) else None
    hb = t.get("h_bt_base", bt)   # BT des concessions qui ont des heures (Groupe)
    hm = t.get("h_mo_base", mo)
    return {
        "bt": bt, "mo_v": mo, "pc_v": pc, "tot_v": tot, "pb": pb, "h": h,
        "mo_bt": div(mob, bt), "pc_bt": div(pcb, bt), "tot_bt": div(totb, bt), "pb_bt": div(pbb, bt),
        "h_bt": div(h, hb) if h else None, "elr": div(hm, h) if h else None,
        "marge_mo": div(mo_pb, mo), "marge_pc": div(pc_pb, pc), "pc_mo": div(pc, mo),
    }


def sum_flats(flats):
    """Somme de vues à plat (Groupe). Heures : BT et M-O de référence limités
    aux concessions qui ont des heures pour ce type."""
    flats = [f for f in flats if f]
    if not flats:
        return None
    out = {"types": {}, "detail": {}, "pieces": {}, "service": {}, "carrosserie": {}, "atelier": {}}
    for grp in ("types", "detail"):
        keys = {k for f in flats for k in f[grp]}
        for k in keys:
            acc = {}
            hb = hm = 0.0
            for f in flats:
                t = f[grp].get(k)
                if not t:
                    continue
                for _, m in MEAS:
                    if t.get(m) is not None:
                        acc[m] = (acc.get(m) or 0) + t[m]
                for m in BT_BASED:
                    v = t.get(m + "_b", t.get(m) if t.get("bt") else None)
                    if v is not None:
                        acc[m + "_b"] = (acc.get(m + "_b") or 0) + v
                if t.get("h"):
                    hb += t.get("bt") or 0
                    hm += t.get("mo_v") or 0
            acc["h_bt_base"], acc["h_mo_base"] = hb, hm
            out[grp][k] = acc
    for grp in ("pieces", "service", "carrosserie"):
        keys = {k for f in flats for k in f[grp]}
        for k in keys:
            acc = {}
            for f in flats:
                for m, v in (f[grp].get(k) or {}).items():
                    if v is not None:
                        acc[m] = (acc.get(m) or 0) + v
            out[grp][k] = acc
    for k in ("heures_disponibles", "heures_pointees", "heures_vendues"):
        vals = [f["atelier"].get(k) for f in flats if f["atelier"].get("heures_disponibles")]
        vals = [v for v in vals if v is not None]
        if vals:
            out["atelier"][k] = sum(vals)
    return out


def atelier_metrics(f):
    a = (f or {}).get("atelier") or {}
    disp, pt, vend = a.get("heures_disponibles"), a.get("heures_pointees"), a.get("heures_vendues")
    techs = (a.get("techniciens") or {}).get("mecanique")
    return {
        "disp": disp, "pointees": pt, "vendues": vend,
        "productivite": div(pt, disp), "efficacite": div(vend, pt), "rendement": div(vend, disp),
        "techs": techs, "h_tech": div(vend, techs) if techs and techs >= 2 else None,
        "taux_affiche": a.get("taux_affiche") or {},
        # état BMW Canada, page 10 : « taux de main-d'œuvre en vigueur »
        "taux_effectif_declare": a.get("taux_effectif_declare"),
        "techs_declares": a.get("techniciens_declares") or {},
    }


def pieces_total(f):
    p = (f or {}).get("pieces") or {}
    tot = p.get("total") or {}
    return tot.get("v"), tot.get("pb")


def pieces_channels(f):
    """[(canal, ventes, pb)] : BT client/garantie/interne (sur les types),
    puis les canaux du département Pièces."""
    if not f:
        return []
    out = []
    for typ in PC_TYPES:
        t = f["types"].get(typ) or {}
        if t.get("pc_v") or t.get("pc_pb"):
            out.append((typ, t.get("pc_v"), t.get("pc_pb")))
    for ch in PC_CHANNELS:
        if ch in PC_TYPES:
            continue
        m = f["pieces"].get(ch) or {}
        if m.get("v") or m.get("pb"):
            out.append((ch, m.get("v"), m.get("pb")))
    return out


class AVStore:
    """Accès aux opérations fixes d'un kpi_data.Store."""

    def __init__(self, store):
        self.s = store
        self.raw = store.raw
        self._c = {}

    def native(self, d, p, mode):
        rec = self.raw.get(d, {}).get("periods", {}).get(p)
        if not rec:
            return None
        return ((rec.get("sections") or {}).get(mode) or {}).get("apres_vente")

    def source_format(self, d, p):
        return self.s.source_format(d, p)

    def has_native_ap(self, d, p, mode):
        av = self.native(d, p, mode)
        if not av:
            return False
        for t in (av.get("types") or {}).values():
            if _field(t.get("bt"), "prior_year") or _field(t.get("mo_ventes"), "prior_year"):
                return True
        return False

    def get(self, d, p, mode, base="real"):
        """Vue à plat pour base real | ap | budget (None si indisponible)."""
        ck = (d, p, mode, base)
        if ck in self._c:
            return self._c[ck]
        av = self.native(d, p, mode)
        out = None
        if base == "real":
            out = flat(av, "real")
        elif base == "ap":
            if self.has_native_ap(d, p, mode):
                out = flat(av, "prior_year")
            else:
                out = self.get(d, prior_year(p), mode, "real")
            # heures : jamais dans les colonnes AP du Réalisé ; prises du fichier de l'an passé
            prev = self.get(d, prior_year(p), mode, "real")
            if out and prev and self.has_native_ap(d, p, mode):
                out = _with_hours(out, prev)
        elif base == "budget":
            f = flat(av, "budget")
            if f and any((t.get("bt") or t.get("mo_v")) for t in f["types"].values()):
                out = f
        self._c[ck] = out
        return out

    def ap_source(self, d, p, mode):
        if self.has_native_ap(d, p, mode):
            return "natif"
        if self.get(d, prior_year(p), mode, "real"):
            return "reconstitue"
        return None

    def group(self, dealers, p, mode, base="real", require_ap=False, typ=None):
        """Somme du Groupe. require_ap : seulement les concessions qui ont
        aussi l'an passé (pour le type donné si typ)."""
        fl = []
        for d in dealers:
            f = self.get(d, p, mode, base)
            if not f:
                continue
            if require_ap:
                a = self.get(d, p, mode, "ap") if base == "real" else self.get(d, p, mode, "real")
                if not a:
                    continue
                if typ and not ((a["types"].get(typ) or {}).get("bt") and (f["types"].get(typ) or {}).get("bt")):
                    continue
            fl.append(f)
        return sum_flats(fl)

    def comparable_hours(self, dealers, p, mode, typ):
        """(réel, AP) du Groupe limité aux concessions qui ont des heures pour
        le type les deux années (heures par BT, taux effectif)."""
        inc = []
        for d in dealers:
            r, a = self.get(d, p, mode, "real"), self.get(d, p, mode, "ap")
            if typ == "all":
                ok = r and a and any(t.get("h") for t in r["types"].values()) and any(t.get("h") for t in a["types"].values())
            else:
                ok = r and a and (r["types"].get(typ) or {}).get("h") and (a["types"].get(typ) or {}).get("h")
            if ok:
                inc.append(d)
        return (sum_flats([self.get(d, p, mode, "real") for d in inc]),
                sum_flats([self.get(d, p, mode, "ap") for d in inc]))

    def comparable(self, dealers, p, mode, typ):
        """(réel, AP) du Groupe à périmètre comparable pour un type."""
        return (self.group(dealers, p, mode, "real", require_ap=True, typ=typ),
                self.group(dealers, p, mode, "ap", require_ap=True, typ=typ))

    def series(self, d, end, n, typ, key, mode="month"):
        """Série mensuelle (n mois jusqu'à end) d'un indicateur de type ; d = code ou liste (Groupe)."""
        y, m = split(end)
        out = []
        for i in range(n - 1, -1, -1):
            yy, mm = y, m - i
            while mm <= 0:
                mm += 12
                yy -= 1
            pp = pkey(yy, mm)
            if isinstance(d, (list, tuple)):
                f = self.group(d, pp, mode) if all(self.get(x, pp, mode) for x in d) else None
            else:
                f = self.get(d, pp, mode)
            v = type_metrics((f or {}).get("types", {}).get(typ)).get(key) if f else None
            out.append((pp, v))
        return out

    def dealers_with_hours(self, dealers, p, mode):
        return [d for d in dealers
                if any((t.get("h") for t in ((self.get(d, p, mode) or {}).get("types") or {}).values()))]


def _with_hours(base, prev):
    """Copie de `base` où les heures (et l'atelier) viennent de `prev`."""
    import copy
    out = copy.deepcopy(base)
    for grp in ("types", "detail"):
        for k, t in out[grp].items():
            pt = (prev.get(grp) or {}).get(k) or {}
            t["h"] = pt.get("h")
    out["atelier"] = dict(prev.get("atelier") or {})
    return out
