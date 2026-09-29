# -*- coding: utf-8 -*-
"""Pages « Comparaison au composite » des rapports (demande de Maxime Allard,
29 septembre 2026 : « il faut que les comparaisons soient ajoutées au
rapport » ; BMW et GM suivront).

Sources (data.json["composites"], construit par src/extract.py à partir de
sources/composites/*.json, lus dans les PDF par src/composites.py) :
  - Hyundai : eComposite « ÉF ‐ Sommaire » et « P&P » = moyennes du groupe de
    comparaison (ex. Est A (850+), 16 concessions) ; chiffres de Hyundai
    Longueuil aux mêmes définitions, calculés à partir de l'état Hyundai
    Canada du mois (clé « concession »).
  - Volkswagen : « Dealer Report Card » = chiffres de VW Brossard, moyennes
    nationale et Québec, objectifs, points et rangs.

Pages :
  pages_concession(s, P, d)     rapport mensuel de la concession
  pages_fo_concession(s, P, d)  rapport Opérations fixes de la concession
  page_groupe(s, P)             rapport mensuel du Groupe
  page_fo_groupe(s, P)          rapport Opérations fixes du Groupe
"""
from html import escape

import rapport_commun as rc
from rapport_commun import key, chip
from kpi_data import DEALERS, MOIS, split, pkey
from kpi_analyse import money, kmoney, num, pct, pts, de

# Concessions et constructeur attendu (pour la page du Groupe)
ATTENDUS = [("hyundai", "Hyundai Canada (eComposite)"), ("vw", "Volkswagen Canada (bulletin de la concession)"),
            ("bmw", "BMW Canada"), ("hawks", "GM Canada"), ("stm", "GM Canada")]


def comp_of(s, d, P):
    return ((getattr(s, "composites", None) or {}).get(d) or {}).get(P) or {}


# ============================================================ Hyundai
DEPT_LAB = {"total": "Concession", "neuf": "Véhicules neufs", "occasion": "Véhicules d'occasion",
            "service": "Service", "pieces": "Pièces", "carrosserie": "Carrosserie", "location": "Location"}


class HyComp:
    """Moyennes du groupe (composite) et chiffres de Hyundai Longueuil."""

    def __init__(self, entry):
        self.ef = (entry.get("hyundai_ef") or {})
        self.pp = (entry.get("hyundai_pp") or {})
        self.ar = (entry.get("hyundai_ar") or {})
        self.conc = entry.get("concession") or {}
        self.groupe = self.ef.get("groupe") or self.pp.get("groupe") or self.ar.get("groupe") or "groupe de comparaison"
        self.n = self.ef.get("n") or self.pp.get("n")
        self.ok = bool(self.conc and (self.ef or self.pp))
        self._pp, self._ar = {}, {}
        if self.pp or self.ar:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
            import composites as C
            self.C = C
            for dept, rows in (self.pp.get("pages") or {}).items():
                self._pp[dept] = C.pp_canon(rows)
            for page, k, prefix, _, _ in C.AR_LINES:
                it = C.ar_item(self.ar, page, prefix) if self.ar else None
                if it:
                    self._ar[k] = it

    @property
    def label(self):
        return f"{self.groupe}" + (f", {self.n} concessions" if self.n else "")

    # ---- valeurs de base
    def g(self, dept, k, mode):
        """Moyenne du groupe (composite)."""
        col = "mad" if mode == "month" else "pad"
        if k in ("marge", "frais_pct_pb", "pb_unite", "emploi_pct_pb"):
            return self._derived(dept, k, mode, self.g)
        v = (((self.ef.get("lignes") or {}).get(dept) or {}).get(k) or {}).get(col)
        if v is None and k in ("ventes", "pb", "frais"):
            first = {"ventes": 0, "pb": 1}.get(k)
            rows = (self.pp.get("pages") or {}).get(dept) or []
            if first is not None and len(rows) > first:
                v = rows[first].get(col)
            elif k == "frais":
                r = self._pp.get(dept, {}).get("total_frais")
                v = r.get(col) if r else None
        return v

    def c(self, dept, k, mode):
        """Hyundai Longueuil, mêmes définitions."""
        if k in ("marge", "frais_pct_pb", "pb_unite", "emploi_pct_pb"):
            return self._derived(dept, k, mode, self.c)
        return (((self.conc.get(mode) or {}).get("ef") or {}).get(dept) or {}).get(k)

    def _derived(self, dept, k, mode, f):
        pb = f(dept, "pb", mode)
        if k == "marge":
            v = f(dept, "ventes", mode)
            return pb / v if pb is not None and v else None
        if k == "frais_pct_pb":
            fr = f(dept, "frais", mode)
            return fr / pb if fr is not None and pb and pb > 0 else None
        if k == "pb_unite":
            u = f(dept, "unites", mode)
            return pb / u if pb is not None and u else None
        if k == "emploi_pct_pb":
            e = self.pp_g(dept, "emploi", mode) if f == self.g else self.pp_c(dept, "emploi", mode)
            return e / pb if e is not None and pb and pb > 0 else None

    # ---- postes P&P
    def pp_g(self, dept, pid, mode):
        r = self._pp.get(dept, {}).get(pid)
        return r.get("mad" if mode == "month" else "pad") if r else None

    def pp_c(self, dept, pid, mode):
        return (((self.conc.get(mode) or {}).get("pp") or {}).get(dept) or {}).get(pid)

    # ---- analyse des revenus (service et pièces par type) : champ n, ventes ou pb
    def ar_g(self, k, field, mode):
        r = (self._ar.get(k) or {}).get(field)
        return r.get("mad" if mode == "month" else "pad") if r else None

    def ar_c(self, k, field, mode):
        return (((self.conc.get(mode) or {}).get("ar") or {}).get(k) or {}).get(field)

    @property
    def ar_ok(self):
        return bool(self._ar) and bool(((self.conc.get("ytd") or {}).get("ar")))

    def pp_sum(self, who, dept, ids, mode, minus=()):
        f = self.pp_g if who == "g" else self.pp_c
        vals = [f(dept, i, mode) for i in ids]
        if all(v is None for v in vals):
            return None
        tot = sum(v or 0 for v in vals)
        for i in minus:
            tot -= f(dept, i, mode) or 0
        return tot


# lignes du sommaire : (département, clé, libellé, type, sens) ; type : k (k$), pct, u (unités), d ($ par unité)
HY_ROWS = [
    ("sec", "Concession"),
    ("total", "ventes", "Ventes totales", "k", 0),
    ("total", "pb", "Profit brut", "k", 0),
    ("total", "marge", "Marge brute (% des ventes)", "pct", 1),
    ("total", "frais_pct_pb", "Dépenses totales (% du profit brut)", "pct", -1),
    ("total", "pn_avant_bonis", "Profit net avant bonis et impôts", "k", 1),
    ("total", "pn_pct_pb", "Profit net avant bonis (% du profit brut)", "pct", 1),
    ("total", "absorption", "Absorption", "pct", 1),
    ("sec", "Véhicules neufs"),
    ("neuf", "unites", "Unités au détail", "u", 1),
    ("neuf", "pb_unite", "Profit brut du département par unité (avec F&I et gros)", "d", 1),
    ("neuf", "fi_unite", "F&I (bureau commercial) par unité", "d", 1),
    ("neuf", "frais_pct_pb", "Dépenses (% du profit brut)", "pct", -1),
    ("neuf", "profit_op", "Profit d'opération", "k", 1),
    ("neuf", "profit_op_pct_pb", "Profit d'opération (% du profit brut)", "pct", 1),
    ("sec", "Véhicules d'occasion"),
    ("occasion", "unites", "Unités au détail", "u", 1),
    ("occasion", "pb_unite", "Profit brut du département par unité (avec F&I et gros)", "d", 1),
    ("occasion", "fi_unite", "F&I (bureau commercial) par unité", "d", 1),
    ("occasion", "frais_pct_pb", "Dépenses (% du profit brut)", "pct", -1),
    ("occasion", "profit_op", "Profit d'opération", "k", 1),
    ("occasion", "profit_op_pct_pb", "Profit d'opération (% du profit brut)", "pct", 1),
]
HY_FO_ROWS = [
    ("sec", "Après-vente"),
    ("total", "absorption", "Absorption", "pct", 1),
]
for _d, _lab in (("service", "Service"), ("pieces", "Pièces"), ("carrosserie", "Carrosserie")):
    HY_FO_ROWS += [
        ("sec", _lab),
        (_d, "ventes", "Ventes", "k", 0),
        (_d, "marge", "Marge brute (% des ventes)", "pct", 1),
        (_d, "emploi_pct_pb", "Frais d'emploi (% du profit brut)", "pct", -1),
        (_d, "frais_pct_pb", "Dépenses totales (% du profit brut)", "pct", -1),
        (_d, "profit_op", "Profit d'opération", "k", 1),
        (_d, "profit_op_pct_pb", "Profit d'opération (% du profit brut)", "pct", 1),
    ]


def _fmt(v, t):
    if v is None:
        return "—"
    if t == "k":
        return num(v / 1000)
    if t == "pct":
        return pct(v, 1)
    if t == "d":
        return num(v)
    return num(v)


def _gap(v, g, t, sens):
    """(texte, classe) de l'écart concession − groupe."""
    if v is None or g is None:
        return "—", "muted"
    d = v - g
    if t == "pct":
        txt = pts(d, 1)
        cls = "" if sens == 0 or abs(d) < 0.0005 else ("pos" if d * sens > 0 else "neg")
    elif t == "d":
        txt = num(d, sign=True)
        cls = "" if sens == 0 or abs(d) < 0.5 else ("pos" if d * sens > 0 else "neg")
    else:
        if not g:
            return "n.s.", "muted"
        r = v / g - 1 if g > 0 else None
        if r is None:
            txt = num((v - g) / 1000, sign=True) + " k$" if t == "k" else num(d, sign=True)
            cls = "" if sens == 0 else ("pos" if d * sens > 0 else "neg")
        else:
            txt = pct(r, 0, sign=True)
            cls = "" if sens == 0 or abs(r) < 0.005 else ("pos" if r * sens > 0 else "neg")
    return txt, cls


def _hy_table(H, rows, cls="small"):
    body = []
    for r in rows:
        if r[0] == "sec":
            body.append(f'<tr class="sec"><td colspan="7">{escape(r[1])}</td></tr>')
            continue
        dept, k, lab, t, sens = r
        vals = [(H.c(dept, k, m), H.g(dept, k, m)) for m in ("month", "ytd")]
        if all(v is None for v, _ in vals):
            continue
        tds = ""
        for i, (v, g) in enumerate(vals):
            gt, gc = _gap(v, g, t, sens)
            tds += (f'<td class="{"sep" if i else ""}">{_fmt(v, t)}</td><td class="muted">{_fmt(g, t)}</td>'
                    f'<td class="{gc}">{gt}</td>')
        body.append(f'<tr><td class="lab">{escape(lab)}</td>{tds}</tr>')
    return body


def _hy_head(P, first="k$ sauf indication"):
    y, m = split(P)
    return (f'<thead><tr><th rowspan="2" class="lab">{first}</th><th colspan="3">{MOIS[m].capitalize()} {y}</th>'
            f'<th colspan="3" class="sep">Cumul {MOIS[1]}–{MOIS[m]} {y}</th></tr>'
            f'<tr><th>Hyundai Longueuil</th><th>Groupe (moy.)</th><th>Écart</th>'
            f'<th class="sep">Hyundai Longueuil</th><th>Groupe (moy.)</th><th>Écart</th></tr></thead>')


def _rel(v, g, t, sens):
    """Écart relatif signé dans le sens favorable (> 0 = mieux que le groupe)."""
    if v is None or g is None or sens == 0:
        return None
    if t in ("pct",):
        base = abs(g) if abs(g) > 0.02 else 0.02
        return (v - g) / base * sens
    if not g or g <= 0:
        return None
    return (v / g - 1) * sens


def _bravo(H, rows, mode="ytd", n=2):
    """(meilleurs, moins bons) : [(texte)] — écarts relatifs les plus grands."""
    cand = []
    for r in rows:
        if r[0] == "sec":
            continue
        dept, k, lab, t, sens = r
        if (t == "k" and k not in ("profit_op", "pn_avant_bonis")) or k == "pb_unite":
            continue
        v, g = H.c(dept, k, mode), H.g(dept, k, mode)
        rel = _rel(v, g, t, sens)
        if rel is None:
            continue
        if t == "k" and (g is None or g <= 0):
            continue
        dl = "" if dept == "total" else DEPT_LAB[dept].replace("Véhicules ", "").lower() + " — "
        txt = f"{dl}{lab[0].lower() + lab[1:]} : <b>{_fmt(v, t)}{'' if t in ('pct', 'u') else (' k$' if t == 'k' else ' $')}</b> contre {_fmt(g, t)}{'' if t in ('pct', 'u') else (' k$' if t == 'k' else ' $')} ({_gap(v, g, t, sens)[0]})"
        cand.append((rel, txt[0].upper() + txt[1:], (dept, k.replace("_pct_pb", ""))))
    def pick(lst, keep):
        out, fams = [], set()
        for r, t, fam in lst:
            if keep(r) and fam not in fams:
                out.append(t)
                fams.add(fam)
            if len(out) == n:
                break
        return out
    good = pick(sorted(cand, key=lambda x: -x[0]), lambda r: r > 0.02)
    bad = pick(sorted(cand, key=lambda x: x[0]), lambda r: r < -0.02)
    return good, bad


def bravo_box(good, bad, ref):
    if not good and not bad:
        return ""
    g = "".join(f"<li>{t}</li>" for t in good) or "<li class='muted'>—</li>"
    b = "".join(f"<li>{t}</li>" for t in bad) or "<li class='muted'>—</li>"
    return (f'<div class="two bravo">'
            f'<div class="callout"><div class="ch">Bravo — mieux que {escape(ref)}</div><ul>{g}</ul></div>'
            f'<div class="callout"><div class="ch">À améliorer — sous {escape(ref)}</div><ul>{b}</ul></div></div>')


def _hy_key(H, P):
    y, m = split(P)
    v, g = H.c("total", "pn_pct_pb", "ytd"), H.g("total", "pn_pct_pb", "ytd")
    a, ag = H.c("total", "absorption", "ytd"), H.g("total", "absorption", "ytd")
    parts = []
    if v is not None and g is not None:
        parts.append(f"Depuis janvier, profit net avant bonis de <b>{pct(v, 1)}</b> du profit brut, contre <b>{pct(g, 1)}</b> "
                     f"pour le groupe {escape(H.label)} ({pts(v - g, 1)})")
    if a is not None and ag is not None:
        parts.append(f"absorption de <b>{pct(a, 1)}</b> (groupe : {pct(ag, 1)})")
    return (" ; ".join(parts) + ".") if parts else "Comparaison au composite Hyundai."


def hy_page_sommaire(s, P, d, H):
    y, m = split(P)
    body = _hy_table(H, HY_ROWS)
    good, bad = _bravo(H, HY_ROWS)
    tr = (H.ef.get("lignes") or {}).get("total", {})
    trend = ""
    if tr.get("ventes", {}).get("pad_ecart") is not None:
        trend = (f" Le groupe lui-même, depuis janvier par rapport à {y-1} : ventes {pct(tr['ventes']['pad_ecart'], 1, sign=True)}, "
                 f"profit brut {pct(tr['pb']['pad_ecart'], 1, sign=True)}, profit net avant bonis {pct(tr['pn_avant_bonis']['pad_ecart'], 1, sign=True)}.")
    return f"""
      <div class="eyebrow">Comparaison au composite Hyundai</div>
      <h1>Hyundai Longueuil face au groupe {escape(H.groupe)}</h1>
      {key(_hy_key(H, P))}
      <table class="t num fo small">{_hy_head(P)}<tbody>{''.join(body)}</tbody></table>
      {bravo_box(good, bad, "le groupe")}
      <div class="note">Groupe : eComposite Hyundai Canada (« ÉF ‐ Sommaire »). Hyundai Longueuil : état Hyundai Canada, mêmes définitions.
      Montants : écart en % de la moyenne ; ratios : écart en points. Absorption = PB pièces + service + carrosserie ÷ (dépenses − frais de vente des véhicules).{trend}</div>"""


# regroupements de postes pour la page des dépenses
HY_DEP_ROWS = [
    ("Frais de vente des véhicules", ("total_vente",), ()),
    ("  dont salaires et commissions", ("sal_directeurs", "sal_comm", "sal_fi"), ()),
    ("  dont publicité nette", ("publicite", "coop"), ()),
    ("  dont financement", ("financement",), ()),
    ("Frais d'emploi", ("emploi",), ()),
    ("Autres frais directs", ("total_directs",), ("emploi",)),
    ("Facteur location", ("facteur_location",), ()),
    ("Autres frais indirects", ("total_indirects",), ("facteur_location",)),
    ("Total des dépenses", ("total_frais",), ()),
]
DEP_SHORT = {"total": "Concession", "neuf": "Neufs", "occasion": "Occasion", "service": "Service", "pieces": "Pièces"}
HY_DEP_DEPTS = ("total", "neuf", "occasion", "service", "pieces")
# postes examinés un à un (sous-total d'emploi : le classement des charges sociales varie d'une concession à l'autre)
HY_TOP_IDS = [("sal_directeurs",), ("sal_comm",), ("sal_fi",), ("livraison",), ("pratiques_garantie",), ("publicite", "coop"),
              ("demo",), ("entretien_inventaire",), ("financement",), ("emploi",), ("formation",), ("fournitures",), ("outils",),
              ("nettoyage",), ("conciergerie",), ("ajustements",), ("pub_ps",), ("entretien_equipement",),
              ("vehicules_entreprise",), ("location_equipement",), ("logiciel",), ("voyages",), ("telephone",), ("transport",),
              ("divers",), ("loyer",), ("amort_ameliorations",), ("entretien_propriete",), ("impots_fonciers",),
              ("assurance_immeubles",), ("amort_immeubles",), ("taxes",), ("amort_equipement",), ("assurance_generale",),
              ("chauffage",), ("honoraires",), ("adhesions",), ("dons",)]


def _ratio(H, who, dept, ids, minus, mode):
    tot = H.pp_sum(who, dept, ids, mode, minus)
    pb = (H.g if who == "g" else H.c)(dept, "pb", mode)
    if tot is None or not pb or pb <= 0:
        return None
    return tot / pb


def hy_top_gaps(H, depts, mode="ytd", blocs=None):
    """[(effet $, département, libellé, ratio concession, ratio groupe)] : effet
    = (ratio concession − ratio groupe) × profit brut de la concession ;
    positif = la concession dépense plus que le groupe."""
    out = []
    for dept in depts:
        pb = H.c(dept, "pb", mode)
        if not pb or pb <= 0:
            continue
        for ids in HY_TOP_IDS:
            if not all(i in H._pp.get(dept, {}) for i in ids):
                continue
            if blocs and H.C.PP_BY_ID[ids[0]][1] not in blocs:
                continue
            rc_, rg = _ratio(H, "c", dept, ids, (), mode), _ratio(H, "g", dept, ids, (), mode)
            if rc_ is None or rg is None:
                continue
            lab = "Publicité nette (après coop)" if ids == ("publicite", "coop") else H.C.PP_BY_ID[ids[0]][2]
            out.append(((rc_ - rg) * pb, dept, lab, rc_, rg))
    return out


def _top_table(rows, title):
    if not rows:
        return ""
    show_dept = len({dp for _, dp, *_ in rows}) > 1 or rows[0][1] != "total"
    tr = "".join(f'<tr>{"<td class=lab>" + escape(DEPT_LAB[dp]) + "</td>" if show_dept else ""}<td class="lab">{escape(lab)}</td><td>{pct(a, 1)}</td>'
                 f'<td class="muted">{pct(b, 1)}</td><td class="{"neg" if eff > 0 else "pos"}">{num(eff / 1000, sign=True)}</td></tr>'
                 for eff, dp, lab, a, b in rows)
    return (f'<table class="t num fo small"><thead><tr>{"<th class=lab>Département</th>" if show_dept else ""}<th class="lab">{escape(title)}</th>'
            f'<th>Hyundai Longueuil (% PB)</th><th>Groupe (% PB)</th><th>Effet (k$)</th></tr></thead><tbody>{tr}</tbody></table>')


def hy_page_depenses(s, P, d, H):
    y, m = split(P)
    mode = "ytd"
    head = ('<thead><tr><th rowspan="2" class="lab">% du profit brut</th>'
            + "".join(f'<th colspan="2" class="{"sep" if i else ""}">{escape(DEP_SHORT[dp])}</th>' for i, dp in enumerate(HY_DEP_DEPTS))
            + "</tr><tr>" + "".join(f'<th class="{"sep" if i else ""}">H. L.</th><th>Grp</th>' for i, _ in enumerate(HY_DEP_DEPTS))
            + "</tr></thead>")
    body = ""
    for lab, ids, minus in HY_DEP_ROWS:
        sub = lab.startswith("  ")
        tds = ""
        for i, dp in enumerate(HY_DEP_DEPTS):
            if not all(x in H._pp.get(dp, {}) for x in ids):
                tds += f'<td class="{"sep" if i else ""} muted">—</td><td class="muted">—</td>'
                continue
            a, b = _ratio(H, "c", dp, ids, minus, mode), _ratio(H, "g", dp, ids, minus, mode)
            cls = "" if a is None or b is None or abs(a - b) < 0.005 else ("pos" if a < b else "neg")
            tds += f'<td class="{"sep" if i else ""} {cls}">{pct(a, 1)}</td><td class="muted">{pct(b, 1)}</td>'
        body += f'<tr class="{"sub" if sub else ("strong" if lab.startswith("Total") else "")}"><td class="lab">{escape(lab.strip())}</td>{tds}</tr>'
    # postes au niveau de la concession : les frais fixes sont répartis entre départements selon des clés
    # propres à chaque concession (Hyundai Longueuil : loyer en parts égales), la comparaison se fait donc au total
    gaps = hy_top_gaps(H, ("total",), mode)
    worst = sorted([g for g in gaps if g[0] > 1000], key=lambda g: -g[0])[:5]
    best = sorted([g for g in gaps if g[0] < -1000], key=lambda g: g[0])[:4]
    tot_a, tot_b = _ratio(H, "c", "total", ("total_frais",), (), mode), _ratio(H, "g", "total", ("total_frais",), (), mode)
    pbt = H.c("total", "pb", mode)
    msg = "Dépenses comparées au profit brut, département par département."
    if tot_a is not None and tot_b is not None and pbt:
        eff = (tot_a - tot_b) * pbt
        msg = (f"Depuis janvier, les dépenses de Hyundai Longueuil représentent <b>{pct(tot_a, 1)}</b> du profit brut, contre "
               f"<b>{pct(tot_b, 1)}</b> pour le groupe, soit <b>{kmoney(abs(eff))}</b> de dépenses {'en moins' if eff < 0 else 'en trop'} "
               f"par rapport au ratio du groupe.")
        if worst:
            msg += f" Poste le plus au-dessus du groupe : {escape(worst[0][2].lower())} ({kmoney(worst[0][0], sign=True)})."
    return f"""
      <div class="eyebrow">Comparaison au composite Hyundai</div>
      <h1>Dépenses en % du profit brut — cumul {MOIS[1]}–{MOIS[m]} {y}</h1>
      {key(msg)}
      <table class="t num fo small">{head}<tbody>{body}</tbody></table>
      <div class="band-lab">Postes où Hyundai Longueuil dépense plus que le groupe <span>concession ; effet = écart de ratio × profit brut de Hyundai Longueuil</span></div>
      {_top_table(worst, "Poste") or '<p class="muted">Aucun poste au-dessus du groupe de plus de 1 k$.</p>'}
      <div class="band-lab">Postes où Hyundai Longueuil dépense moins que le groupe</div>
      {_top_table(best, "Poste") or '<p class="muted">Aucun.</p>'}
      <div class="note">H. L. = Hyundai Longueuil, Grp = moyenne du groupe (vert = ratio plus bas que le groupe). Groupe : eComposite Hyundai Canada (« P&P »), {escape(H.label)}.
      Salaires et commissions : directeurs, vendeurs et F&I. Facteur location : loyer ou intérêt hypothécaire, taxes foncières, entretien et assurance des
      bâtiments. Postes comparés au total de la concession (chaque concession répartit ses frais fixes entre départements à sa façon) ; frais d'emploi
      en sous-total (charges sociales classées différemment d'une concession à l'autre).</div>"""


def hy_page_fo(s, P, d, H):
    y, m = split(P)
    rows = [r for r in HY_FO_ROWS if r[0] == "sec" or r[0] != "carrosserie" or (H.c("carrosserie", "pb", "ytd") or 0) != 0]
    if not (H.c("carrosserie", "pb", "ytd") or 0):
        rows = [r for r in rows if not (r[0] == "sec" and r[1] == "Carrosserie")]
    body = _hy_table(H, rows)
    good, bad = _bravo(H, rows)
    gaps = hy_top_gaps(H, ("service", "pieces"), "ytd", blocs=("vente", "directs"))
    worst = sorted([g for g in gaps if g[0] > 1000], key=lambda g: -g[0])[:3]
    sv, pc_ = (H.ef.get("lignes") or {}).get("service", {}), (H.ef.get("lignes") or {}).get("pieces", {})
    trend = ""
    if sv.get("ventes", {}).get("pad_ecart") is not None and pc_.get("ventes", {}).get("pad_ecart") is not None:
        trend = (f"Le groupe, depuis janvier par rapport à {y-1} : ventes de service {pct(sv['ventes']['pad_ecart'], 1, sign=True)}, "
                 f"ventes de pièces {pct(pc_['ventes']['pad_ecart'], 1, sign=True)}. ")
    a, ag = H.c("service", "profit_op_pct_pb", "ytd"), H.g("service", "profit_op_pct_pb", "ytd")
    b, bg = H.c("pieces", "profit_op_pct_pb", "ytd"), H.g("pieces", "profit_op_pct_pb", "ytd")
    msg = []
    if a is not None and ag is not None:
        msg.append(f"Service : profit d'opération de <b>{pct(a, 1)}</b> du profit brut depuis janvier (groupe : {pct(ag, 1)})")
    if b is not None and bg is not None:
        msg.append(f"pièces : <b>{pct(b, 1)}</b> (groupe : {pct(bg, 1)})")
    carros = "" if (H.c("carrosserie", "pb", "ytd") or 0) else \
        f" Pas de carrosserie à Hyundai Longueuil (groupe : {kmoney(H.g('carrosserie', 'ventes', 'ytd'))} de ventes moyennes depuis janvier)."
    return f"""
      <div class="eyebrow">Comparaison au composite Hyundai</div>
      <h1>Service et pièces face au groupe {escape(H.groupe)}</h1>
      {key(" ; ".join(msg) + "." if msg else "Service et pièces comparés au composite Hyundai.")}
      <table class="t num fo small">{_hy_head(P)}<tbody>{''.join(body)}</tbody></table>
      {bravo_box(good, bad, "le groupe")}
      {('<div class="band-lab">Postes où l’écart pèse le plus <span>cumul, frais directs ; effet = écart de ratio × profit brut du département</span></div>' + _top_table(worst, "Poste")) if worst else ''}
      <div class="note">{trend}Groupe : eComposite Hyundai Canada ({escape(H.label)}) ; Hyundai Longueuil : état Hyundai Canada, mêmes définitions.{carros}</div>"""


# Analyse des revenus : (clé, libellé, clé des BT pour « par BT » ou None)
AR_MO_ROWS = [("mo_client", "BT client", "mo_client"), ("mo_garantie", "BT garantie", "mo_garantie"),
              ("mo_interne", "BT interne", "mo_interne"), ("mo_total", "Total main-d'œuvre", "mo_total"),
              ("sous_traitance", "Sous-traitance (par travail)", "sous_traitance")]
AR_PC_ROWS = [("pc_client", "Pièces sur BT client", "mo_client"), ("pc_garantie", "Pièces sur BT garantie", "mo_garantie"),
              ("pc_interne", "Pièces sur BT interne", "mo_interne"), ("pc_comptoir", "Comptoir — pièces", None),
              ("pc_accessoires", "Comptoir — accessoires", None), ("pc_gros", "Ventes en gros", None),
              ("pc_pneus", "Roues et pneus", None), ("pc_total", "Total pièces", None)]


def ar_row(H, k, per, mode="ytd"):
    """Valeurs d'un poste : BT, ventes, $ par BT, marge et écart de profit brut
    (PB réel − PB au ratio du groupe : PB par BT si per, sinon marge)."""
    out = {}
    for who, f in (("c", H.ar_c), ("g", H.ar_g)):
        n = f(per, "n", mode) if per else None
        v, pb = f(k, "ventes", mode), f(k, "pb", mode)
        out[who] = {"n": n, "ventes": v, "pb": pb,
                    "par": (v / n) if per and v is not None and n else None,
                    "marge": (pb / v) if pb is not None and v else None,
                    "pb_par": (pb / n) if per and pb is not None and n else None}
    c, g = out["c"], out["g"]
    eff = None
    if per and c["n"] and g["pb_par"] is not None and c["pb"] is not None:
        eff = c["pb"] - g["pb_par"] * c["n"]
    elif not per and c["ventes"] and g["marge"] is not None and c["pb"] is not None:
        eff = c["pb"] - g["marge"] * c["ventes"]
    out["effet"] = eff
    return out


def _ar_table(H, rows, first, vol):
    body = []
    for k, lab, per in rows:
        R = ar_row(H, k, per)
        c, g = R["c"], R["g"]
        if c["ventes"] is None and g["ventes"] is None:
            continue
        pt, pc_ = _gap(c["par"], g["par"], "k", 1) if per else ("", "")
        mt, mc = _gap(c["marge"], g["marge"], "pct", 1)
        e = R["effet"]
        et = "—" if e is None else num(e / 1000, sign=True)
        ec = "" if e is None or abs(e) < 500 else ("pos" if e > 0 else "neg")
        if vol == "n":
            v1, v2 = num(c["n"]) if c["n"] is not None else "—", num(g["n"]) if g["n"] is not None else "—"
        else:
            v1, v2 = _fmt(c["ventes"], "k"), _fmt(g["ventes"], "k")
        par = (f'<td class="sep">{num(c["par"]) if c["par"] is not None else "—"}</td><td class="muted">{num(g["par"]) if g["par"] is not None else "—"}</td>'
               f'<td class="{pc_}">{pt}</td>') if per else '<td class="sep muted">—</td><td class="muted">—</td><td></td>'
        tot = ' class="total"' if k in ("mo_total", "pc_total") else ""
        body.append(f'<tr{tot}><td class="lab">{escape(lab)}</td><td>{v1}</td><td class="muted">{v2}</td>{par}'
                    f'<td class="sep">{_fmt(c["marge"], "pct")}</td><td class="muted">{_fmt(g["marge"], "pct")}</td><td class="{mc}">{mt}</td>'
                    f'<td class="sep {ec}">{et}</td></tr>')
    vh = "BT" if vol == "n" else "Ventes (k$)"
    ph = "M-O par BT ($)" if vol == "n" else "Pièces par BT ($)"
    head = (f'<thead><tr><th rowspan="2" class="lab">{first}</th><th colspan="2">{vh}</th><th colspan="3" class="sep">{ph}</th>'
            f'<th colspan="3" class="sep">Marge brute</th><th rowspan="2" class="sep">Écart de PB<br>(k$)</th></tr>'
            f'<tr><th>H. L.</th><th>Grp</th><th class="sep">H. L.</th><th>Grp</th><th>Écart</th>'
            f'<th class="sep">H. L.</th><th>Grp</th><th>Écart</th></tr></thead>')
    return f'<table class="t num fo small">{head}<tbody>{"".join(body)}</tbody></table>'


def _ar_bravo(H, n=3):
    cand = []
    for rows, dom in ((AR_MO_ROWS, "M-O"), (AR_PC_ROWS, "pièces")):
        for k, lab, per in rows:
            if k in ("mo_total", "pc_total"):
                continue
            R = ar_row(H, k, per)
            c, g, e = R["c"], R["g"], R["effet"]
            if e is None or abs(e) < 5000:
                continue
            if per:
                what = "M-O" if dom == "M-O" else "pièces"
                unit = "BT" if k != "sous_traitance" else "travail"
                txt = (f"{lab} : <b>{num(c['par'])} $</b> de {what} par {unit} contre {num(g['par'])} $ "
                       f"(marge {pct(c['marge'], 1)} contre {pct(g['marge'], 1)}) — {num(e / 1000, sign=True)} k$ de PB")
            else:
                txt = (f"{lab} : marge de <b>{pct(c['marge'], 1)}</b> contre {pct(g['marge'], 1)} sur "
                       f"{kmoney(c['ventes'])} de ventes — {num(e / 1000, sign=True)} k$ de PB")
            cand.append((e, txt))
    bad = [t for e, t in sorted(cand, key=lambda x: x[0]) if e < 0][:n]
    # Bravo : ratios et volumes au-dessus du groupe (écart relatif)
    pos = []
    for rows in (AR_MO_ROWS, AR_PC_ROWS):
        for k, lab, per in rows:
            R = ar_row(H, k, per)
            c, g = R["c"], R["g"]
            if k == "mo_total":
                r = _rel(c["marge"], g["marge"], "pct", 1)
                if r is not None:
                    pos.append((r, k, f"Marge brute de la main-d'œuvre : <b>{pct(c['marge'], 1)}</b> contre {pct(g['marge'], 1)}"))
                continue
            if k == "pc_total":
                continue
            if per and k.startswith("mo_"):
                r = _rel(c["n"], g["n"], "u", 1)
                if r is not None:
                    pos.append((r, k, f"{lab} : <b>{num(c['n'])}</b> BT depuis janvier contre {num(g['n'])} en moyenne"))
            if per:
                r = _rel(c["par"], g["par"], "d", 1)
                if r is not None:
                    pos.append((r, k, f"{lab} : <b>{num(c['par'])} $</b> par BT contre {num(g['par'])} $"))
            else:
                r = _rel(c["ventes"], g["ventes"], "k", 1)
                if r is not None:
                    pos.append((r, k, f"{lab} : <b>{kmoney(c['ventes'])}</b> de ventes contre {kmoney(g['ventes'])}"))
            if not k.startswith("mo_"):
                r = _rel(c["marge"], g["marge"], "pct", 1)
                if r is not None:
                    pos.append((r, k, f"{lab} : marge de <b>{pct(c['marge'], 1)}</b> contre {pct(g['marge'], 1)}"))
    good, seen = [], set()
    for r, k, t in sorted(pos, key=lambda x: -x[0]):
        if r > 0.02 and k not in seen:
            good.append(t)
            seen.add(k)
        if len(good) == n:
            break
    return good, bad


def hy_page_ar(s, P, d, H):
    """Rapport Opérations fixes : main-d'œuvre et pièces par type de travail
    (eComposite « Analyse des revenus »)."""
    y, m = split(P)
    good, bad = _ar_bravo(H)
    msg = []
    c = ar_row(H, "mo_client", "mo_client")
    cm = ar_row(H, "mo_client", "mo_client", "month")
    if c["c"]["par"] and c["g"]["par"]:
        msg.append(f"Depuis janvier, <b>{num(c['c']['par'])} $</b> de main-d'œuvre par BT client contre <b>{num(c['g']['par'])} $</b> "
                   f"pour le groupe ({pct(c['c']['par'] / c['g']['par'] - 1, 0, sign=True)})"
                   + (f" ; {MOIS[m]} : {num(cm['c']['par'])} $ (groupe {num(cm['g']['par'])} $)" if cm["c"]["par"] and cm["g"]["par"] else ""))
    p = ar_row(H, "pc_client", "mo_client")
    if p["c"]["par"] and p["g"]["par"]:
        msg.append(f"pièces par BT client : <b>{num(p['c']['par'])} $</b> (groupe {num(p['g']['par'])} $)")
    tot = [ar_row(H, k, per)["effet"] for k, _, per in AR_MO_ROWS + AR_PC_ROWS if k not in ("mo_total", "pc_total")]
    tot = sum(e for e in tot if e is not None)
    bc, bg = H.ar_c("pc_boni_gros", "pb", "ytd"), H.ar_g("pc_boni_gros", "pb", "ytd")
    boni = (f" Escompte / boni pour ventes en gros (hors marge des ventes en gros, compris dans le total) : {kmoney(bc)} depuis janvier"
            f" (groupe : {kmoney(bg)}).") if bc is not None and bg is not None else ""
    return f"""
      <div class="eyebrow">Comparaison au composite Hyundai</div>
      <h1>Main-d'œuvre et pièces par type de travail</h1>
      {key(" ; ".join(msg) + "." if msg else "Service et pièces par type, comparés au composite Hyundai.")}
      <div class="band-lab">Main-d'œuvre <span>cumul {MOIS[1]}–{MOIS[m]} {y} · BT = bons de travail</span></div>
      {_ar_table(H, AR_MO_ROWS, "Type de travail", "n")}
      <div class="band-lab">Pièces <span>cumul {MOIS[1]}–{MOIS[m]} {y} · par BT = ventes de pièces ÷ BT du même type</span></div>
      {_ar_table(H, AR_PC_ROWS, "Type de vente", "k")}
      {bravo_box(good, bad, "le groupe")}
      <div class="note">H. L. = Hyundai Longueuil, Grp = moyenne du groupe {escape(H.label)} (eComposite Hyundai Canada, « Analyse des revenus ») ;
      Hyundai Longueuil : page 4 de l'état Hyundai Canada. Écart de PB = profit brut réel − profit brut au ratio du groupe (PB par BT pour les
      lignes par BT, marge pour les autres) ; somme des lignes : {num(tot / 1000, sign=True)} k$. BT internes : surtout la remise en état des
      véhicules d'occasion. Ventes en gros et pneus : selon la clientèle de chaque concession.{boni}</div>"""


# ============================================================ Volkswagen
VW_SUM_ROWS = [
    ("sec", "Ventes de véhicules neufs"),
    ("nv_bpv", "Ventes neuves vs objectif (BPV)", "pct", 1),
    ("nv_aged", "Inventaire neuf de plus de 90 jours", "pct", -1),
    ("ms_total", "Part de marché (segments concurrents)", "pct", 1),
    ("ms_car", "  autos", "pct", 1),
    ("ms_truck", "  camions et VUS", "pct", 1),
    ("reg_eff", "Efficacité des immatriculations", "pct", 1),
    ("sales_eff", "Efficacité des ventes", "pct", 1),
    ("sec", "Véhicules d'occasion"),
    ("cpo_bpv", "Ventes de VO certifiés vs objectif", "pct", 1),
    ("sec", "Pièces et accessoires"),
    ("parts_obj", "Achats de pièces vs objectif (sans accessoires)", "pct", 1),
    ("parts_loyalty", "Fidélité pièces", "pct", 1),
    ("parts_turns", "Rotation de l'inventaire de pièces", "x", 0),
    ("acc_pnvr", "Accessoires achetés par véhicule neuf ($)", "d", 1),
    ("sec", "Service"),
    ("ppm", "Entretien prépayé vendu (PPM, véhicules neufs)", "pct", 1),
    ("mlc", "Conversion des pistes d'entretien", "pct", 1),
    ("sec", "Expérience client (CEM)"),
    ("cem_sales", "Ventes — moyenne des 3 questions clés", "pct", 1),
    ("cem_service", "Service — moyenne des 3 questions clés", "pct", 1),
]
VW_COMP_LAB = {
    "new": [("nv_sales", "Ventes neuves (unités, cumul)", "u", 1), ("nv_bpv", "Ventes neuves vs objectif", "pct", 1),
            ("vwfs_pen", "Pénétration VW Crédit (contrats)", "pct", 1), ("lease_loyalty", "Fidélité — fin de location", "pct", 1),
            ("loan_loyalty", "Fidélité — fin de financement", "pct", 1), ("fi_pnv", "F&I par véhicule neuf ($)", "d", 1),
            ("ms_brand", "Part de marché de la marque VW (industrie)", "pct", 1)],
    "used": [("cpo_sales", "VO certifiés vendus (unités)", "u", 1), ("cpo_new", "VO certifiés par véhicule neuf", "x2", 1),
             ("noncpo_sales", "VO VW non certifiés vendus", "u", 0), ("fi_puvr", "F&I par véhicule d'occasion ($)", "d", 1)],
    "service": [("absorption", "Absorption", "pct", 1), ("cp_hours_ro", "Heures vendues par BT client", "x", 1),
                ("parts_cp_ro", "Pièces par BT client ($)", "d", 1), ("tech_eff", "Efficacité des techniciens", "pct", 1),
                ("tech_prod", "Productivité des techniciens", "pct", 1), ("mix_cp", "Main-d'œuvre : client", "pct", 0),
                ("mix_warranty", "Main-d'œuvre : garantie", "pct", 0), ("mix_internal", "Main-d'œuvre : interne", "pct", 0),
                ("ppm_new", "Entretien prépayé — neufs", "pct", 1), ("ppm_cpo", "Entretien prépayé — VO certifiés", "pct", 1),
                ("mlc", "Conversion des pistes d'entretien", "pct", 1), ("car_park", "Parc actif (clients revenus)", "pct", 1),
                ("service_cert", "Certification du personnel de service", "pct", 1)],
    "parts": [("parts_loyalty", "Fidélité pièces", "pct", 1), ("parts_turns", "Rotation de l'inventaire (fois par an)", "x", 0),
              ("parts_obj", "Achats de pièces vs objectif", "pct", 1), ("parts_cp_ro", "Pièces par BT client ($)", "d", 1),
              ("acc_pnvr", "Accessoires par véhicule neuf ($)", "d", 1), ("retail_vio", "Pièces au détail par véhicule du parc ($)", "d", 1)],
}
VW_CEM_LAB = [("cem_sales_osat", "Ventes — satisfaction globale (sur 5)", "x2", 1),
              ("cem_sales_top3", "Ventes — moyenne des 3 questions clés", "pct", 1),
              ("cem_service_osat", "Service — satisfaction globale (sur 5)", "x2", 1),
              ("cem_service_top3", "Service — moyenne des 3 questions clés", "pct", 1),
              ("cem_cpo_top3", "VO certifiés — moyenne des 3 questions clés", "pct", 1)]


def _vf(v, t):
    if v is None:
        return "—"
    if isinstance(v, str):
        return escape(v.replace(" to ", " à "))
    if t == "pct":
        return pct(v, 1)
    if t == "d":
        return money(v)
    if t == "x":
        return num(v, 1) if abs(v) < 100 else num(v)
    if t == "x2":
        return num(v, 2)
    return num(v)


def _vcls(v, ref, sens, t):
    if v is None or ref is None or sens == 0 or isinstance(ref, str):
        return ""
    tol = 0.0005 if t == "pct" else 0.05
    if abs(v - ref) < tol:
        return ""
    return "pos" if (v - ref) * sens > 0 else "neg"


def vw_key(R):
    rk = R.get("classement") or {}
    na, ge, p = rk.get("national") or {}, rk.get("geo") or {}, rk.get("points") or {}
    parts = []
    if na:
        parts.append(f"Rang national <b>{na['rang']}</b> sur {na['n']} ({num(na['mom'], sign=True)} places ce mois-ci, "
                     f"{num(na['yoy'], sign=True)} vs l'an passé)")
    if ge:
        parts.append(f"rang au Québec <b>{ge['rang']}</b> sur {ge['n']}")
    if p.get("total"):
        parts.append(f"<b>{num(p['total'][0], 1)}</b> points sur {num(p['total'][1])}")
    return (" ; ".join(parts) + ".") if parts else "Bulletin Volkswagen Canada."


def vw_missed(R, n=4):
    """Points manqués les plus importants : [(points manqués, libellé, obtenus, possibles)]."""
    lab = {k: l for k, l, *_ in [r for r in VW_SUM_ROWS if r[0] != "sec"]}
    out = []
    for k, rec in (R.get("sommaire") or {}).items():
        if k.startswith("_") or rec.get("points_max") is None or rec.get("points") is None:
            continue
        miss = rec["points_max"] - rec["points"]
        if miss > 0:
            out.append((miss, lab.get(k, k).strip(), rec["points"], rec["points_max"]))
    return sorted(out, key=lambda x: -x[0])[:n]


def vw_page_bulletin(s, P, d, R):
    y, m = split(P)
    rk = R.get("classement") or {}
    p = rk.get("points") or {}
    nd, gd = rk.get("national_dept") or {}, rk.get("geo_dept") or {}
    na, ge = rk.get("national") or {}, rk.get("geo") or {}

    rk_rows = ""
    if na or ge:
        rk_rows = (f'<table class="t num fo small"><thead><tr><th class="lab">Classement</th><th>Global</th><th>Ventes</th><th>Après-vente</th>'
                   f'<th class="sep">Variation du mois</th><th>vs l\'an passé</th></tr></thead><tbody>'
                   + (f'<tr><td class="lab">National ({na["n"]} concessions)</td><td><b>{na["rang"]}</b></td><td>{nd.get("ventes", "—")}</td>'
                      f'<td>{nd.get("apres_vente", "—")}</td><td class="sep">{num(na["mom"], sign=True)}</td><td>{num(na["yoy"], sign=True)}</td></tr>' if na else "")
                   + (f'<tr><td class="lab">Québec ({ge["n"]} concessions)</td><td><b>{ge["rang"]}</b></td><td>{gd.get("ventes", "—")}</td>'
                      f'<td>{gd.get("apres_vente", "—")}</td><td class="sep">{num(ge["mom"], sign=True)}</td><td>{num(ge["yoy"], sign=True)}</td></tr>' if ge else "")
                   + (f'<tr><td class="lab">Points obtenus</td><td><b>{num(p["total"][0], 1)}</b> / {num(p["total"][1])}</td>'
                      f'<td>{num(p["ventes"][0], 1)} / {num(p["ventes"][1])}</td><td>{num(p["apres_vente"][0], 1)} / {num(p["apres_vente"][1])}</td>'
                      f'<td class="sep" colspan="2">expérience client : {num(p["experience"][0], 1)} / {num(p["experience"][1])}</td></tr>' if p.get("total") else "")
                   + "</tbody></table>")
    summ = R.get("sommaire") or {}
    body = ""
    for r in VW_SUM_ROWS:
        if r[0] == "sec":
            body += f'<tr class="sec"><td colspan="8">{escape(r[1])}</td></tr>'
            continue
        k, lab, t, sens = r
        rec = summ.get(k)
        if not rec:
            continue
        star = "*" if rec.get("donnees_juillet") else ""
        v = rec.get("ytd")
        pts_ = (f"{num(rec['points'], 1)} / {num(rec['points_max'])}" if rec.get("points_max") is not None else "—")
        body += (f'<tr class="{"sub" if lab.startswith("  ") else ""}"><td class="lab">{escape(lab.strip())}{star}</td>'
                 f'<td class="{_vcls(v, rec.get("national"), sens, t)}"><b>{_vf(v, t)}</b></td><td class="muted">{_vf(rec.get("ytd_ap"), t)}</td>'
                 f'<td class="muted">{_vf(rec.get("mois"), t)}</td>'
                 f'<td class="sep">{_vf(rec.get("national"), t)}</td><td>{_vf(rec.get("geo"), t)}</td>'
                 f'<td class="sep">{pts_}</td><td>{escape(rec.get("rang_national") or "—")}</td></tr>')
    missed = vw_missed(R, 3)
    miss_txt = ""
    if missed:
        miss_txt = ('<div class="callout compact"><div class="ch">Où sont les points manqués</div><ul>' +
                    "".join(f"<li>{escape(l)} : {num(a, 1)} sur {num(b)} ({num(mi, 1)} point{'s' if mi >= 2 else ''} manqué{'s' if mi >= 2 else ''})</li>"
                            for mi, l, a, b in missed) + "</ul></div>")
    return f"""
      <div class="eyebrow">Comparaison au composite Volkswagen</div>
      <h1>Bulletin Volkswagen Canada — {MOIS[m]} {y}</h1>
      {key(vw_key(R))}
      {rk_rows}
      <table class="t num fo small"><thead><tr><th class="lab">Indicateur</th><th>{y} cumul</th><th>{y-1} cumul</th><th>{MOIS[m].capitalize()}</th>
      <th class="sep">National</th><th>Québec</th><th class="sep">Points</th><th>Rang national</th></tr></thead><tbody>{body}</tbody></table>
      {miss_txt}
      <div class="note">Source : « Dealer Report Card » de Volkswagen Canada, {MOIS[m]} {y}. Vert / rouge : cumul {y} au-dessus / au-dessous de la moyenne
      nationale. * données de juillet. Rangs et points : classement préliminaire du programme Wolfsburg Crest Club.</div>"""


def _vw_comp_table(R, sections, with_obj=True):
    comp = R.get("comparateurs") or {}
    y = int((R.get("period") or "0000")[:4])
    body = ""
    for sec_key, title in sections:
        rows = VW_COMP_LAB[sec_key]
        recs = comp.get(sec_key) or {}
        if not recs:
            continue
        body += f'<tr class="sec"><td colspan="6">{escape(title)}</td></tr>'
        for k, lab, t, sens in rows:
            rec = recs.get(k)
            if not rec:
                continue
            v = rec.get("ytd")
            body += (f'<tr><td class="lab">{escape(lab)}</td><td class="{_vcls(v, rec.get("national"), sens, t)}"><b>{_vf(v, t)}</b></td>'
                     f'<td class="muted">{_vf(rec.get("ytd_ap"), t)}</td><td class="sep">{_vf(rec.get("national"), t)}</td>'
                     f'<td>{_vf(rec.get("geo"), t)}</td><td class="sep muted">{_vf(rec.get("objectif"), t)}</td></tr>')
    return (f'<table class="t num fo small"><thead><tr><th class="lab">Indicateur</th><th>{y} cumul</th><th>{y-1} cumul</th>'
            f'<th class="sep">National</th><th>Québec</th><th class="sep">Objectif VW</th></tr></thead><tbody>{body}</tbody></table>')


def _vw_cem_table(R, only=None):
    cem = R.get("experience") or {}
    y = int((R.get("period") or "0000")[:4])
    body = ""
    for k, lab, t, sens in VW_CEM_LAB:
        if only and k not in only:
            continue
        rec = cem.get(k)
        if not rec:
            continue
        v = rec.get("ytd")
        body += (f'<tr><td class="lab">{escape(lab)}</td><td class="{_vcls(v, rec.get("national"), sens, t)}"><b>{_vf(v, t)}</b></td>'
                 f'<td class="muted">{_vf(rec.get("ytd_ap"), t)}</td><td class="muted">{_vf(rec.get("r3"), t)}</td>'
                 f'<td class="sep">{_vf(rec.get("national"), t)}</td><td>{_vf(rec.get("geo"), t)}</td>'
                 f'<td class="sep muted">{_vf(rec.get("cible"), t)}</td></tr>')
    if not body:
        return ""
    return (f'<table class="t num fo small"><thead><tr><th class="lab">Expérience client (CEM)</th><th>{y} cumul</th><th>{y-1} cumul</th>'
            f'<th>3 derniers mois</th><th class="sep">National</th><th>Québec</th><th class="sep">Cible</th></tr></thead><tbody>{body}</tbody></table>')


def _vw_bravo(R, sections):
    """Écarts les plus favorables / défavorables vs la moyenne nationale."""
    comp = R.get("comparateurs") or {}
    cand = []
    for sec_key in sections:
        for k, lab, t, sens in VW_COMP_LAB[sec_key]:
            rec = (comp.get(sec_key) or {}).get(k)
            if not rec or sens == 0 or rec.get("ytd") is None or not rec.get("national"):
                continue
            v, n_ = rec["ytd"], rec["national"]
            rel = (v - n_) / abs(n_) * sens
            cand.append((rel, f"{lab} : <b>{_vf(v, t)}</b> contre {_vf(n_, t)} au national"))
    cand.sort(key=lambda x: -x[0])
    good = [t for r, t in cand if r > 0.03][:2]
    bad = [t for r, t in sorted(cand, key=lambda x: x[0]) if r < -0.03][:2]
    return good, bad


def vw_page_ventes(s, P, d, R):
    y, m = split(P)
    good, bad = _vw_bravo(R, ("new", "used"))
    comp = R.get("comparateurs") or {}
    ns = (comp.get("new") or {}).get("nv_sales") or {}
    msg = "Ventes, F&I et expérience client comparés aux moyennes de Volkswagen Canada."
    if ns.get("ytd") is not None:
        msg = (f"<b>{num(ns['ytd'])}</b> véhicules neufs depuis janvier (objectif {num(ns.get('objectif'))}, {y-1} : {num(ns.get('ytd_ap'))}) ; "
               f"moyenne nationale : {num(ns.get('national'))} par concession.")
    return f"""
      <div class="eyebrow">Comparaison au composite Volkswagen</div>
      <h1>Ventes, F&I et expérience client — bulletin VW</h1>
      {key(msg)}
      {_vw_comp_table(R, [("new", "Véhicules neufs et financement"), ("used", "Véhicules d'occasion")])}
      {_vw_cem_table(R)}
      {bravo_box(good, bad, "la moyenne nationale")}
      <div class="note">Source : « Dealer Report Card » de Volkswagen Canada. Vert / rouge : cumul {y} au-dessus / au-dessous de la moyenne nationale.
      Certains indicateurs portent sur juillet ou sur 12 mois (fidélité : fins de contrat de mai 2025 à avril 2026), comme dans le bulletin.</div>"""


def vw_page_fo(s, P, d, R):
    y, m = split(P)
    good, bad = _vw_bravo(R, ("service", "parts"))
    sv = (R.get("comparateurs") or {}).get("service") or {}
    ab, hr = sv.get("absorption") or {}, sv.get("cp_hours_ro") or {}
    msg = "Service et pièces comparés aux moyennes de Volkswagen Canada."
    if ab.get("ytd") is not None:
        msg = (f"Absorption de <b>{pct(ab['ytd'], 0)}</b> depuis janvier (national {pct(ab.get('national'), 0)}, Québec {pct(ab.get('geo'), 0)}, "
               f"objectif {pct(ab.get('objectif'), 0)})")
        if hr.get("ytd") is not None:
            msg += f" ; <b>{num(hr['ytd'], 1)} h</b> vendues par BT client (national {num(hr.get('national'), 1)} h)"
        msg += "."
    return f"""
      <div class="eyebrow">Comparaison au composite Volkswagen</div>
      <h1>Service et pièces — bulletin Volkswagen Canada</h1>
      {key(msg)}
      {_vw_comp_table(R, [("service", "Service"), ("parts", "Pièces et accessoires")])}
      {_vw_cem_table(R, only=("cem_service_osat", "cem_service_top3"))}
      {bravo_box(good, bad, "la moyenne nationale")}
      <div class="note">Source : « Dealer Report Card » de Volkswagen Canada, {MOIS[m]} {y} (données de juillet pour le service et les pièces).
      Vert / rouge : cumul {y} au-dessus / au-dessous de la moyenne nationale ; rotation des pièces et répartition de la main-d'œuvre : sans couleur.</div>"""


# ============================================================ assemblage
def pages_concession(s, P, d):
    e = comp_of(s, d, P)
    out = []
    if d == "hyundai":
        H = HyComp(e)
        if H.ok and H.ef:
            out.append(hy_page_sommaire(s, P, d, H))
        if H.ok and H.pp:
            out.append(hy_page_depenses(s, P, d, H))
    elif d == "vw" and e.get("vw_report_card"):
        out += [vw_page_bulletin(s, P, d, e["vw_report_card"]), vw_page_ventes(s, P, d, e["vw_report_card"])]
    return out


def pages_fo_concession(s, P, d):
    e = comp_of(s, d, P)
    if d == "hyundai":
        H = HyComp(e)
        out = [hy_page_fo(s, P, d, H)] if H.ok and H.ef else []
        if H.ar_ok:
            out.append(hy_page_ar(s, P, d, H))
        return out
    if d == "vw" and e.get("vw_report_card"):
        return [vw_page_fo(s, P, d, e["vw_report_card"])]
    return []


def _status_rows(s, P):
    rows = ""
    for d, src in ATTENDUS:
        e = comp_of(s, d, P)
        got = [k for k in e if k in ("hyundai_ef", "hyundai_pp", "hyundai_ar", "vw_report_card")]
        st = chip("reçu", "good") if got else chip("en attente", "neutral")
        rows += f'<tr><td class="lab">{escape(DEALERS.get(d, d))}</td><td class="lab">{escape(src)}</td><td class="lab">{st}</td></tr>'
    return rows


def page_groupe(s, P):
    y, m = split(P)
    eh, ev = comp_of(s, "hyundai", P), comp_of(s, "vw", P)
    H = HyComp(eh) if eh else None
    R = ev.get("vw_report_card")
    if not ((H and H.ok) or R):
        return None
    blocks = ""
    if H and H.ok:
        rows = [("total", "pn_pct_pb", "Profit net avant bonis (% du profit brut)", "pct", 1),
                ("total", "frais_pct_pb", "Dépenses totales (% du profit brut)", "pct", -1),
                ("total", "absorption", "Absorption", "pct", 1),
                ("neuf", "unites", "Neufs : unités au détail", "u", 1),
                ("neuf", "pb_unite", "Neufs : profit brut par unité ($)", "d", 1),
                ("neuf", "fi_unite", "Neufs : F&I par unité ($)", "d", 1),
                ("occasion", "unites", "Occasion : unités au détail", "u", 1),
                ("occasion", "fi_unite", "Occasion : F&I par unité ($)", "d", 1),
                ("service", "profit_op_pct_pb", "Service : profit d'opération (% du PB)", "pct", 1),
                ("pieces", "profit_op_pct_pb", "Pièces : profit d'opération (% du PB)", "pct", 1)]
        tr = ""
        for dept, k, lab, t, sens in rows:
            v, g = H.c(dept, k, "ytd"), H.g(dept, k, "ytd")
            if v is None and g is None:
                continue
            gt, gc = _gap(v, g, t, sens)
            tr += f'<tr><td class="lab">{escape(lab)}</td><td>{_fmt(v, t)}</td><td class="muted">{_fmt(g, t)}</td><td class="{gc}">{gt}</td></tr>'
        blocks += (f'<div class="band-lab">Hyundai Longueuil <span>cumul {MOIS[1]}–{MOIS[m]} {y} · composite Hyundai Canada, groupe {escape(H.label)}</span></div>'
                   f'<table class="t num fo small"><thead><tr><th class="lab">Indicateur</th><th>Hyundai Longueuil</th><th>Moyenne du groupe</th>'
                   f'<th>Écart</th></tr></thead><tbody>{tr}</tbody></table>')
    if R:
        rk = R.get("classement") or {}
        na, ge, p = rk.get("national") or {}, rk.get("geo") or {}, rk.get("points") or {}
        summ = R.get("sommaire") or {}
        pick = [("nv_bpv", "Ventes neuves vs objectif", "pct", 1), ("nv_aged", "Inventaire neuf de plus de 90 jours", "pct", -1),
                ("ms_total", "Part de marché", "pct", 1), ("cpo_bpv", "VO certifiés vs objectif", "pct", 1),
                ("ppm", "Entretien prépayé vendu (neufs)", "pct", 1), ("cem_sales", "Satisfaction ventes (3 questions clés)", "pct", 1),
                ("cem_service", "Satisfaction service (3 questions clés)", "pct", 1)]
        tr = ""
        for k, lab, t, sens in pick:
            rec = summ.get(k)
            if not rec:
                continue
            v = rec.get("ytd")
            tr += (f'<tr><td class="lab">{escape(lab)}</td><td class="{_vcls(v, rec.get("national"), sens, t)}">{_vf(v, t)}</td>'
                   f'<td class="muted">{_vf(rec.get("national"), t)}</td><td class="muted">{_vf(rec.get("geo"), t)}</td>'
                   f'<td>{escape(rec.get("rang_national") or "—")}</td></tr>')
        head = (f"rang national {na.get('rang', '—')} sur {na.get('n', '—')} · Québec {ge.get('rang', '—')} sur {ge.get('n', '—')}"
                + (f" · {num(p['total'][0], 1)} points sur {num(p['total'][1])}" if p.get("total") else ""))
        blocks += (f'<div class="band-lab">Volkswagen Brossard <span>bulletin Volkswagen Canada · {escape(head)}</span></div>'
                   f'<table class="t num fo small"><thead><tr><th class="lab">Indicateur</th><th>VW Brossard</th><th>National</th>'
                   f'<th>Québec</th><th>Rang national</th></tr></thead><tbody>{tr}</tbody></table>')
    msg_parts = []
    if H and H.ok:
        v, g = H.c("total", "pn_pct_pb", "ytd"), H.g("total", "pn_pct_pb", "ytd")
        if v is not None and g is not None:
            msg_parts.append(f"Hyundai Longueuil : profit net avant bonis de <b>{pct(v, 1)}</b> du profit brut, contre {pct(g, 1)} pour son groupe")
    if R and (R.get("classement") or {}).get("national"):
        na = R["classement"]["national"]
        msg_parts.append(f"VW Brossard : <b>{na['rang']}<sup>e</sup></b> sur {na['n']} au Canada")
    return f"""
      <div class="eyebrow">Comparaison aux composites des constructeurs</div>
      <h1>Nos concessions face à leur réseau</h1>
      {key(" ; ".join(msg_parts) + ".")}
      {blocks}
      <div class="band-lab">Composites du mois</div>
      <table class="t fo small"><thead><tr><th class="lab">Concession</th><th class="lab">Source</th><th class="lab">{MOIS[m].capitalize()} {y}</th></tr></thead>
      <tbody>{_status_rows(s, P)}</tbody></table>
      <div class="note">Détail : pages « Comparaison au composite » des rapports de Hyundai Longueuil et de Volkswagen Brossard (et de leurs rapports
      Opérations fixes). Les composites de BMW Canada et de GM Canada seront ajoutés dès réception des fichiers.</div>"""


def page_fo_groupe(s, P):
    """Page du rapport Opérations fixes du Groupe : service et pièces face aux composites."""
    y, m = split(P)
    eh, ev = comp_of(s, "hyundai", P), comp_of(s, "vw", P)
    H = HyComp(eh) if eh else None
    R = ev.get("vw_report_card")
    if not ((H and H.ok) or R):
        return None
    blocks, msg = "", []
    if H and H.ok:
        rows = [("total", "absorption", "Absorption", "pct", 1)]
        for dp, lb in (("service", "Service"), ("pieces", "Pièces")):
            rows += [(dp, "marge", f"{lb} : marge brute (% des ventes)", "pct", 1),
                     (dp, "emploi_pct_pb", f"{lb} : frais d'emploi (% du PB)", "pct", -1),
                     (dp, "profit_op_pct_pb", f"{lb} : profit d'opération (% du PB)", "pct", 1)]
        tr = ""
        for dept, k, lab, t, sens in rows:
            v, g = H.c(dept, k, "ytd"), H.g(dept, k, "ytd")
            gt, gc = _gap(v, g, t, sens)
            tr += f'<tr><td class="lab">{escape(lab)}</td><td>{_fmt(v, t)}</td><td class="muted">{_fmt(g, t)}</td><td class="{gc}">{gt}</td></tr>'
        if H.ar_ok:
            for k, per, lab in (("mo_client", "mo_client", "Main-d'œuvre par BT client ($)"), ("pc_client", "mo_client", "Pièces par BT client ($)")):
                A = ar_row(H, k, per)
                v, g = A["c"]["par"], A["g"]["par"]
                gt, gc = _gap(v, g, "k", 1)
                tr += (f'<tr><td class="lab">{escape(lab)}</td><td>{num(v) if v is not None else "—"}</td>'
                       f'<td class="muted">{num(g) if g is not None else "—"}</td><td class="{gc}">{gt}</td></tr>')
        blocks += (f'<div class="band-lab">Hyundai Longueuil <span>cumul · composite Hyundai Canada, groupe {escape(H.label)}</span></div>'
                   f'<table class="t num fo small"><thead><tr><th class="lab">Indicateur</th><th>Hyundai Longueuil</th><th>Moyenne du groupe</th>'
                   f'<th>Écart</th></tr></thead><tbody>{tr}</tbody></table>')
        a, ag = H.c("total", "absorption", "ytd"), H.g("total", "absorption", "ytd")
        if a is not None and ag is not None:
            msg.append(f"Hyundai Longueuil : absorption de <b>{pct(a, 1)}</b> (groupe {pct(ag, 1)})")
    if R:
        sv = (R.get("comparateurs") or {}).get("service") or {}
        pa = (R.get("comparateurs") or {}).get("parts") or {}
        tr = ""
        for rec, lab, t, sens in ((sv.get("absorption"), "Absorption", "pct", 1), (sv.get("cp_hours_ro"), "Heures vendues par BT client", "x", 1),
                                  (sv.get("parts_cp_ro"), "Pièces par BT client ($)", "d", 1), (sv.get("tech_eff"), "Efficacité des techniciens", "pct", 1),
                                  (sv.get("tech_prod"), "Productivité des techniciens", "pct", 1), (pa.get("parts_loyalty"), "Fidélité pièces", "pct", 1),
                                  (sv.get("ppm_new"), "Entretien prépayé vendu (neufs)", "pct", 1)):
            if not rec:
                continue
            v = rec.get("ytd")
            tr += (f'<tr><td class="lab">{escape(lab)}</td><td class="{_vcls(v, rec.get("national"), sens, t)}">{_vf(v, t)}</td>'
                   f'<td class="muted">{_vf(rec.get("national"), t)}</td><td class="muted">{_vf(rec.get("geo"), t)}</td>'
                   f'<td class="muted">{_vf(rec.get("objectif"), t)}</td></tr>')
        blocks += (f'<div class="band-lab">Volkswagen Brossard <span>bulletin Volkswagen Canada (données de juillet)</span></div>'
                   f'<table class="t num fo small"><thead><tr><th class="lab">Indicateur</th><th>VW Brossard</th><th>National</th>'
                   f'<th>Québec</th><th>Objectif VW</th></tr></thead><tbody>{tr}</tbody></table>')
        ab = sv.get("absorption") or {}
        if ab.get("ytd") is not None:
            msg.append(f"VW Brossard : absorption de <b>{pct(ab['ytd'], 0)}</b> (national {pct(ab.get('national'), 0)})")
    return f"""
      <div class="eyebrow">Comparaison aux composites des constructeurs</div>
      <h1>Après-vente face aux composites</h1>
      {key(" ; ".join(msg) + "." if msg else "Après-vente comparé aux composites des constructeurs.")}
      {blocks}
      <div class="note">Les définitions de l'absorption diffèrent d'un constructeur à l'autre (Hyundai : profit brut après-vente ÷ dépenses hors frais
      de vente des véhicules ; VW : définition du bulletin) : comparer chaque concession à son propre réseau, pas les concessions entre elles.
      Composites de BMW Canada et de GM Canada : à venir.</div>"""
