#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rapport « Opérations fixes » — Groupe Automax (analyse approfondie de l'après-vente).

Bons de travail (BT) par type — client, garantie, interne, esthétique — :
nombre de BT, main-d'œuvre par BT, pièces par BT, total par BT, profit brut
par BT, heures vendues par BT, taux effectif ; atelier (heures disponibles,
pointées, vendues) ; pièces par canal ; carrosserie ; tendances sur 24 mois.

    python rapport_apres_vente.py --data ../../data/data.json --mois 2026-08 --sortie sortie
"""
import argparse
import os
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import rapport_commun as rc
from rapport_commun import key, tile, Book, wrap_html, to_pdf, LOGO_DARK, last_day
from kpi_data import Store, DEALERS, DEALER_SHORT, MOIS, pkey, split, prior_year, label_period, ratios
from kpi_analyse import money, kmoney, num, pct, pts, var_pct, de, NBSP
from kpi_svg import _text, nice_ticks, INK, MUTED, GRID, AXIS, CAT, PREV, CUR
import kpi_apres_vente as fo
from kpi_apres_vente import TYPES, MAIN_TYPES, type_metrics, atelier_metrics, div

DEALER_COLOR = {"bmw": CAT[0], "vw": CAT[1], "stm": CAT[2], "hyundai": CAT[3], "hawks": CAT[4], "groupe": INK}
GROUP = "groupe"

METRIC_COLS = [  # (clé, en-tête, format)
    ("bt", "BT", "n"),
    ("mo_bt", "M-O / BT", "$"),
    ("pc_bt", "Pièces / BT", "$"),
    ("tot_bt", "Total / BT", "$"),
    ("pb_bt", "PB / BT", "$"),
    ("h_bt", "Heures / BT", "h"),
    ("elr", "Taux effectif", "$"),
]
TYPE_NOTES = {
    "client": "BT payés par le client : atelier, service rapide, contrats de service et entretien prépayé. À STM, le service mobile est inclus.",
    "garantie": "Travaux remboursés par le constructeur (main-d'œuvre et pièces de garantie).",
    "interne": "Travaux facturés aux autres départements : reconditionnement des usagés, préparation des neufs. À l'état GM, l'inspection des véhicules neufs est incluse.",
    "esthetique": "BT d'esthétique inscrits au Réalisé (BMW, VW).",
}


# ------------------------------------------------------------------ formats
def fv(v, f):
    if v is None:
        return "—"
    if f == "$":
        return money(v)
    if f == "k":
        return kmoney(v)
    if f == "h":
        return num(v, 2)
    if f == "%":
        return pct(v, 1)
    if f == "x":
        return num(v, 2)
    return num(v)


def fd(r, b, f):
    """Écart (texte, classe) : % pour les montants et volumes, points pour les %."""
    if r is None or b is None:
        return "", ""
    if f == "%":
        d = r - b
        return pts(d, 1), ("pos" if d > 0.0005 else "neg" if d < -0.0005 else "")
    vp = var_pct(r, b)
    if vp is None:
        return "", ""
    return pct(vp, 0, sign=True), ("pos" if vp > 0.005 else "neg" if vp < -0.005 else "")


def cell(r, b, f, strong=False):
    t, c = fd(r, b, f)
    sub = f'<div class="dsub {c}">{t}</div>' if t else '<div class="dsub muted">&nbsp;</div>'
    return f'<td class="{"strong" if strong else ""}"><div>{fv(r, f)}</div>{sub}</td>'


# ------------------------------------------------------------------ données
class FO:
    def __init__(self, s, P):
        self.s = s
        self.av = fo.AVStore(s)
        self.P = P
        self.y, self.m = split(P)
        self.dealers = [d for d in DEALERS if self.av.get(d, P, "ytd") or self.av.get(d, P, "month")]

    def flat(self, d, mode, base="real", P=None):
        P = P or self.P
        if d == GROUP:
            return self.av.group(self.dealers, P, mode, base)
        return self.av.get(d, P, mode, base)

    def pair(self, d, mode, typ=None):
        """(réel, AP) ; Groupe à périmètre comparable (pour le type si donné)."""
        if d == GROUP:
            if typ:
                return self.av.comparable(self.dealers, self.P, mode, typ)
            return (self.av.group(self.dealers, self.P, mode, "real", require_ap=True),
                    self.av.group(self.dealers, self.P, mode, "ap", require_ap=True))
        return self.av.get(d, self.P, mode, "real"), self.av.get(d, self.P, mode, "ap")

    def tm(self, f, typ):
        if not f:
            return {}
        if typ == "all":
            return type_metrics(all_types(f))
        return type_metrics((f.get("types") or {}).get(typ))

    def comp(self, d, mode, base="real"):
        if d == GROUP:
            from kpi_data import add_comps
            cs = [self.s.comp(x, self.P, mode, base) for x in self.dealers]
            if base != "real":
                cs = [c for x, c in zip(self.dealers, cs) if c and self.s.comp(x, self.P, mode, "real")]
            cs = [c for c in cs if c]
            return add_comps(cs) if cs else None
        return self.s.comp(d, self.P, mode, base)

    def comp_pair(self, d, mode):
        if d == GROUP:
            from kpi_data import add_comps
            inc = [x for x in self.dealers if self.s.comp(x, self.P, mode, "real") and self.s.comp(x, self.P, mode, "ap")]
            if not inc:
                return None, None
            return (add_comps([self.s.comp(x, self.P, mode, "real") for x in inc]),
                    add_comps([self.s.comp(x, self.P, mode, "ap") for x in inc]))
        return self.s.comp(d, self.P, mode, "real"), self.s.comp(d, self.P, mode, "ap")

    def hours_dealers(self, mode="ytd"):
        return self.av.dealers_with_hours(self.dealers, self.P, mode)


def all_types(f):
    """Somme des types d'une vue à plat (tous les BT mécaniques)."""
    acc = {"h_bt_base": 0.0, "h_mo_base": 0.0}
    has_h = False
    for t in (f.get("types") or {}).values():
        for _, m in fo.MEAS:
            if t.get(m) is not None:
                acc[m] = (acc.get(m) or 0) + t[m]
        for m in fo.BT_BASED:
            v = t.get(m + "_b", t.get(m) if t.get("bt") else None)
            if v is not None:
                acc[m + "_b"] = (acc.get(m + "_b") or 0) + v
        if t.get("h"):
            has_h = True
            acc["h_bt_base"] += t.get("h_bt_base", t.get("bt") or 0) or 0
            acc["h_mo_base"] += t.get("h_mo_base", t.get("mo_v") or 0) or 0
    if not has_h:
        acc["h"] = None
    return acc


def dl(d):
    return "Groupe" if d == GROUP else DEALERS[d]


def ds(d):
    return "Groupe" if d == GROUP else DEALER_SHORT[d]


# ------------------------------------------------------------------ graphiques
def paired_bars(items, fmt, width=660, label_w=120, prev_label="2025", cur_label="2026"):
    """[(libellé, an passé, courant)] — barres appariées, valeurs formatées."""
    row = 27
    height = row * len(items) + 22
    vmax = max([abs(v) for _, a, b in items for v in (a, b) if v is not None] + [1])
    val_w = 62
    pw = width - label_w - val_w - 6
    sc = pw / vmax
    x0 = label_w + 2
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">']
    out.append(f'<rect x="{label_w}" y="3" width="9" height="7" rx="1.5" fill="{PREV}"/>')
    out.append(_text(label_w + 13, 9.5, prev_label, 7, "start", MUTED))
    out.append(f'<rect x="{label_w + 52}" y="3" width="9" height="7" rx="1.5" fill="{CUR}"/>')
    out.append(_text(label_w + 65, 9.5, cur_label, 7, "start", MUTED))
    out.append(f'<line x1="{x0:.1f}" x2="{x0:.1f}" y1="16" y2="{height-2}" stroke="{AXIS}" stroke-width="1"/>')
    for i, (lab, a, b) in enumerate(items):
        y = 18 + i * row
        out.append(_text(0, y + 12, lab, 7.8, "start", INK, 600 if lab == "Groupe" else 400))
        for j, (v, col) in enumerate(((a, PREV), (b, CUR))):
            if v is None:
                continue
            by = y + 2 + j * 10.5
            w = max(abs(v) * sc, 0.8)
            out.append(f'<rect x="{x0:.1f}" y="{by:.1f}" width="{w:.1f}" height="8.6" rx="1.5" fill="{col}"/>')
            out.append(_text(x0 + w + 4, by + 7, fv(v, fmt), 7, "start", INK if j else MUTED, 600 if j else 400))
    out.append("</svg>")
    return "".join(out)


def lines_chart(series, fmt, labels, width=318, height=150, title=None):
    """series : [(clé concession, [valeurs])] ; labels : libellés des mois."""
    ml, mr, mt, mb = 44, 6, 10, 18
    pw, ph = width - ml - mr, height - mt - mb
    allv = [v for _, vs in series for v in vs if v is not None]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">']
    if not allv:
        out.append(_text(width / 2, height / 2, "n/d", 9, "middle", MUTED))
        out.append("</svg>")
        return "".join(out)
    lo, hi = min(allv), max(allv)
    lo = max(0, lo - (hi - lo) * 0.2) if lo >= 0 else lo
    ticks = nice_ticks(lo, hi, 3)
    y0, y1 = ticks[0], ticks[-1]
    Y = lambda v: mt + ph - (v - y0) / ((y1 - y0) or 1) * ph
    n = len(labels)
    X = lambda i: ml + (pw * i / (n - 1) if n > 1 else 0)
    for t in ticks:
        out.append(f'<line x1="{ml}" x2="{width-mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{GRID}" stroke-width="0.8"/>')
        lab = (num(t) + NBSP + "$") if fmt == "$" else (num(t, 1) if fmt == "h" else num(t))
        out.append(_text(ml - 4, Y(t) + 2.5, lab, 6.4, "end", MUTED))
    for i, lab in enumerate(labels):
        if i % 3 == (n - 1) % 3:
            out.append(_text(X(i), height - 5, lab, 6.4, "middle", MUTED))
    for d, vs in series:
        col = DEALER_COLOR.get(d, INK)
        segs, cur = [], []
        for i, v in enumerate(vs):
            if v is None:
                if cur:
                    segs.append(cur)
                cur = []
            else:
                cur.append((X(i), Y(v)))
        if cur:
            segs.append(cur)
        for sg in segs:
            if len(sg) == 1:
                out.append(f'<circle cx="{sg[0][0]:.1f}" cy="{sg[0][1]:.1f}" r="1.6" fill="{col}"/>')
                continue
            dpath = " ".join(("M" if k == 0 else "L") + f"{x:.1f},{y:.1f}" for k, (x, y) in enumerate(sg))
            out.append(f'<path d="{dpath}" fill="none" stroke="{col}" stroke-width="{2.2 if d == GROUP else 1.5}" stroke-linejoin="round"/>')
        last = next(((X(i), Y(v)) for i, v in reversed(list(enumerate(vs))) if v is not None), None)
        if last:
            out.append(f'<circle cx="{last[0]:.1f}" cy="{last[1]:.1f}" r="2" fill="{col}"/>')
    out.append("</svg>")
    return "".join(out)


def legend(keys):
    return '<div class="legend">' + "".join(
        f'<span class="lgd"><span class="sw" style="background:{DEALER_COLOR.get(k, INK)}"></span>{escape(ds(k))}</span>' for k in keys) + "</div>"


# ------------------------------------------------------------------ pages
def p_cover(F):
    y, m = F.y, F.m
    ry, ay = F.comp_pair(GROUP, "ytd")
    pb_r = ratios(ry).get("apres_vente") if ry else None
    pb_a = ratios(ay).get("apres_vente") if ay else None
    fr, fa = F.pair(GROUP, "ytd", "client")
    cr, ca = F.tm(fr, "client"), F.tm(fa, "client")
    gr, ga = F.flat(GROUP, "ytd"), F.flat(GROUP, "ytd", "ap")
    bt_r = F.tm(gr, "all").get("bt")
    gcr, gca = F.pair(GROUP, "ytd")
    bt_cr, bt_ca = F.tm(gcr, "all").get("bt"), F.tm(gca, "all").get("bt")

    def dtxt(r, b, f="$"):
        t, _ = fd(r, b, f)
        return f"{t} vs {y-1}" if t else f"{y-1} : n/d"
    return f"""
      <div class="logo cv-logo">{LOGO_DARK}</div>
      <div class="cv-mid">
        <div class="cv-kicker">Analyse approfondie · {escape(label_period(F.P))}</div>
        <div class="cv-title">Opérations fixes</div>
        <div class="cv-sub">Service, pièces et carrosserie des {len(F.dealers)} concessions : bons de travail par type (client, garantie, interne),
        dollars et heures par bon, atelier, pièces et tendances. Mois {de(m)} et cumul {MOIS[1]}–{MOIS[m]} {y}.</div>
        <div class="cv-kpis">
          <div><div class="cv-kl">PB après-vente cumulatif</div><div class="cv-kv">{kmoney(pb_r)}</div><div class="cv-kd">{escape(dtxt(pb_r, pb_a))}</div></div>
          <div><div class="cv-kl">Bons de travail {y}</div><div class="cv-kv">{num(bt_r)}</div><div class="cv-kd">{escape(dtxt(bt_cr, bt_ca, "n"))}</div></div>
          <div><div class="cv-kl">Total par BT client</div><div class="cv-kv">{money(cr.get('tot_bt'))}</div><div class="cv-kd">{escape(dtxt(cr.get('tot_bt'), ca.get('tot_bt')))}</div></div>
        </div>
      </div>
      <div class="cv-foot">
        <div>Groupe Automax · BMW Sherbrooke, Volkswagen Brossard, Sainte-Marie Automobile, Hyundai Longueuil, Hawkesbury Chevrolet Cadillac</div>
        <div>Préparé le {rc.PREPARED} à partir du tableau de bord KPI (Réalisés et états financiers des constructeurs) · Non audité</div>
        <div class="cv-conf">Confidentiel — usage interne — direction seulement</div>
      </div>"""


def findings(F):
    """Constats chiffrés (cumul vs an passé), du plus important au moins important."""
    y = F.y
    out = []
    # 1. PB après-vente du Groupe
    ry, ay = F.comp_pair(GROUP, "ytd")
    if ry and ay:
        r, a = ratios(ry), ratios(ay)
        d = r["apres_vente"] - a["apres_vente"]
        out.append((1e9, f"<b>Profit brut après-vente du Groupe : {kmoney(r['apres_vente'])}</b> depuis janvier, "
                            f"{kmoney(d, sign=True)} ({pct(var_pct(r['apres_vente'], a['apres_vente']), 0, sign=True)}) vs {y-1} "
                            f"à périmètre comparable ; il couvre <b>{pct(r['absorption'], 0)}</b> des frais fixes "
                            f"({pts(r['absorption'] - a['absorption'], 1)})."))
    # 2. Total par BT client : meilleure et pire concession
    rows = []
    for d in F.dealers:
        fr, fa = F.pair(d, "ytd")
        cr, ca = F.tm(fr, "client"), F.tm(fa, "client")
        if cr.get("tot_bt") and ca.get("tot_bt"):
            rows.append((d, cr, ca, var_pct(cr["tot_bt"], ca["tot_bt"])))
    if rows:
        rows.sort(key=lambda t: t[3])
        lo, hi = rows[0], rows[-1]
        out.append((1e6, f"<b>Total par BT client</b> (main-d'œuvre + pièces) : de <b>{money(min(r[1]['tot_bt'] for r in rows))}</b> à "
                         f"<b>{money(max(r[1]['tot_bt'] for r in rows))}</b> selon la concession. Plus forte hausse : "
                         f"{escape(DEALERS[hi[0]])} ({pct(hi[3], 0, sign=True)}, {money(hi[1]['tot_bt'])}) ; "
                         f"plus forte baisse : {escape(DEALERS[lo[0]])} ({pct(lo[3], 0, sign=True)}, {money(lo[1]['tot_bt'])})."))
    # 3. Volumes de BT client
    vol = []
    for d in F.dealers:
        fr, fa = F.pair(d, "ytd")
        cr, ca = F.tm(fr, "client"), F.tm(fa, "client")
        if cr.get("bt") and ca.get("bt"):
            vol.append((d, cr["bt"] - ca["bt"], var_pct(cr["bt"], ca["bt"])))
    if vol:
        vol.sort(key=lambda t: t[1])
        parts = [f"{escape(DEALER_SHORT[d])} {num(dd, sign=True)} ({pct(vp, 0, sign=True)})" for d, dd, vp in vol]
        tot = sum(dd for _, dd, _ in vol)
        out.append((abs(tot) * 50, f"<b>Nombre de BT client depuis janvier : {num(tot, sign=True)}</b> vs {y-1} — " + ", ".join(parts) + "."))
    # 4. Interne
    ints = []
    for d in F.dealers:
        fr, fa = F.pair(d, "ytd")
        cr, ca = F.tm(fr, "interne"), F.tm(fa, "interne")
        if cr.get("mo_v") and ca.get("mo_v"):
            ints.append((d, cr["mo_v"] - ca["mo_v"], cr, ca))
    if ints:
        tot = sum(t[1] for t in ints)
        big = max(ints, key=lambda t: abs(t[1]))
        out.append((abs(tot), f"<b>Main-d'œuvre interne</b> (reconditionnement et préparation) : {kmoney(tot, sign=True)} vs {y-1} ; "
                              f"plus grand écart à {escape(DEALERS[big[0]])} ({kmoney(big[1], sign=True)}, {num(big[2]['bt'])} BT contre {num(big[3]['bt'])})."))
    # 5. Heures (concessions qui en ont)
    hd = F.hours_dealers("ytd")
    for d in hd:
        fr, fa = F.pair(d, "ytd")
        cr, ca = F.tm(fr, "client"), F.tm(fa, "client")
        at = atelier_metrics(fr)
        if cr.get("h_bt"):
            t = (f"<b>{escape(DEALERS[d])}</b> : {num(cr['h_bt'], 2)} h vendue par BT client"
                 + (f" ({num(cr['h_bt'] - ca['h_bt'], 2, sign=True)} h vs {y-1})" if ca.get("h_bt") else "")
                 + f", taux effectif client {money(cr.get('elr'))}"
                 + (f" ({pct(var_pct(cr['elr'], ca['elr']), 0, sign=True)})" if ca.get("elr") else "")
                 + (f" ; productivité {pct(at['productivite'], 0)}, efficacité {pct(at['efficacite'], 0)}" if at.get("productivite") else "")
                 + ".")
            out.append((5e4, t))
    missing = [d for d in F.dealers if d not in hd]
    if missing:
        out.append((1, f"<span class='muted'>Heures vendues absentes des fichiers de {escape(', '.join(DEALERS[d] for d in missing))} : "
                       f"heures par BT et taux effectif non calculés pour {'ces concessions' if len(missing) > 1 else 'cette concession'}.</span>"))
    return [t for _, t in sorted(out, key=lambda x: -x[0])]


def p_essentiel(F):
    y, m = F.y, F.m
    items = findings(F)
    g = F.flat(GROUP, "ytd")
    tiles = []
    for typ in MAIN_TYPES:
        fr, fa = F.pair(GROUP, "ytd", typ)
        r, a = F.tm(fr, typ), F.tm(fa, typ)
        allr = F.tm(g, typ)
        lines = [(f"M-O {money(r.get('mo_bt'))} + pièces {money(r.get('pc_bt'))}", "muted")]
        t, c = fd(r.get("tot_bt"), a.get("tot_bt"), "$")
        lines.append((f"{t} vs {y-1}" if t else f"{y-1} : n/d", c))
        lines.append((f"{num(allr.get('bt'))} BT depuis janvier", "muted"))
        tiles.append(tile(f"Total par BT — {TYPES[typ].lower()}", money(r.get("tot_bt")), lines, typ == "client"))
    return f"""
      <div class="eyebrow">Sommaire</div>
      <h1>L'essentiel des opérations fixes</h1>
      {key("Les chiffres ci-dessous portent sur le cumul " + MOIS[1] + "–" + MOIS[m] + " " + str(y) + ", comparé à la même période " + str(y-1) + ". "
           "Le Groupe est calculé à partir des sommes (jamais une moyenne des concessions) et, pour les écarts, à périmètre comparable.")}
      <div class="band-lab">Dollars par bon de travail — Groupe <span>cumul {y}, périmètre comparable</span></div>
      <div class="tiles">{''.join(tiles)}</div>
      <h2>Ce qu'il faut retenir</h2>
      <ul class="retenir">{''.join(f'<li>{t}</li>' for t in items[:7])}</ul>"""


def p_overview(F):
    y, m = F.y, F.m
    parts = []
    for mode, title in (("month", f"Mois {de(m)} {y} vs {MOIS[m]} {y-1}"), ("ytd", f"Cumul {MOIS[1]}–{MOIS[m]} {y} vs {y-1}")):
        body = ""
        for d in F.dealers + [GROUP]:
            r, a = F.comp_pair(d, mode)
            rr, ra = (ratios(r) if r else {}), (ratios(a) if a else {})
            fr, fa = F.pair(d, mode)
            tr, ta = F.tm(fr, "all"), F.tm(fa, "all")
            strong = d == GROUP
            body += (f'<tr class="{"strong" if strong else ""}"><td class="lab">{escape(dl(d))}</td>'
                     + cell(r["pb_service"] if r else None, a["pb_service"] if a else None, "k", strong)
                     + cell(r["pb_pieces"] if r else None, a["pb_pieces"] if a else None, "k", strong)
                     + cell(r["pb_carrosserie"] if r else None, a["pb_carrosserie"] if a else None, "k", strong)
                     + cell(rr.get("apres_vente"), ra.get("apres_vente"), "k", True)
                     + cell(rr.get("absorption"), ra.get("absorption"), "%", strong)
                     + cell(rr.get("part_apres_vente"), ra.get("part_apres_vente"), "%", strong)
                     + cell(tr.get("bt"), ta.get("bt"), "n", strong)
                     + "</tr>")
        parts.append(f"""<div class="band-lab">{escape(title)}</div>
          <table class="t num fo small"><thead><tr><th class="lab">Concession</th><th>PB service</th><th>PB pièces</th><th>PB carrosserie</th>
          <th>PB après-vente</th><th>Absorption</th><th>Part du PB total</th><th>Nombre de BT</th></tr></thead><tbody>{body}</tbody></table>""")
    ry, ay = F.comp_pair(GROUP, "ytd")
    msg = ""
    if ry and ay:
        r, a = ratios(ry), ratios(ay)
        msg = (f"Depuis janvier, l'après-vente du Groupe dégage <b>{kmoney(r['apres_vente'])}</b> de profit brut "
               f"({pct(var_pct(r['apres_vente'], a['apres_vente']), 0, sign=True)} vs {y-1}) et couvre <b>{pct(r['absorption'], 0)}</b> "
               f"des frais fixes du Groupe ({pts(r['absorption'] - a['absorption'], 1)}).")
    return f"""
      <div class="eyebrow">Vue d'ensemble</div>
      <h1>Profit brut de l'après-vente par concession</h1>
      {key(msg)}
      {''.join(parts)}
      <div class="note">Montants en k$. Sous chaque valeur : écart vs l'an passé (% ; en points pour les ratios). Absorption = profit brut service + pièces +
      carrosserie ÷ (dépenses totales − dépenses variables). Groupe : écarts à périmètre comparable (concessions qui ont l'an passé).</div>"""


def type_table(F, typ, mode):
    body = ""
    for d in F.dealers + [GROUP]:
        fr, fa = F.pair(d, mode, typ if d == GROUP else None)
        r, a = F.tm(fr, typ), F.tm(fa, typ)
        if d != GROUP and not r.get("bt") and not r.get("mo_v"):
            continue
        if d == GROUP:
            # valeurs du Groupe : toutes les concessions ; écarts : périmètre comparable
            g = F.tm(F.flat(GROUP, mode), typ)
            hr, ha = F.av.comparable_hours(F.dealers, F.P, mode, typ)
            hr, ha = F.tm(hr, typ), F.tm(ha, typ)
            strong = True
            tds = ""
            for k, _, f in METRIC_COLS:
                if k in ("h_bt", "elr"):
                    t, c = fd(hr.get(k), ha.get(k), f)
                else:
                    t, c = fd(r.get(k), a.get(k), f)
                sub = f'<div class="dsub {c}">{t}</div>' if t else '<div class="dsub muted">&nbsp;</div>'
                tds += f'<td class="strong"><div>{fv(g.get(k), f)}</div>{sub}</td>'
            body += f'<tr class="strong"><td class="lab">Groupe</td>{tds}</tr>'
            continue
        tds = "".join(cell(r.get(k), a.get(k), f) for k, _, f in METRIC_COLS)
        body += f'<tr><td class="lab">{escape(dl(d))}</td>{tds}</tr>'
        for dk, dlab in fo.DETAIL_LABELS.items():
            if (dk == "mobile" and typ != "client") or (dk == "inspection" and typ != "interne"):
                continue
            det_r = (fr or {}).get("detail", {}).get(dk)
            if det_r and det_r.get("bt"):
                det_a = (fa or {}).get("detail", {}).get(dk)
                mr, ma = type_metrics(det_r), type_metrics(det_a)
                tds2 = (cell(mr.get("bt"), ma.get("bt"), "n") + cell(mr.get("mo_bt"), ma.get("mo_bt"), "$")
                        + '<td class="muted">—</td>' * (len(METRIC_COLS) - 2))
                body += f'<tr class="sub"><td class="lab">{escape(dlab)}</td>{tds2}</tr>'
    heads = "".join(f"<th>{h}</th>" for _, h, _ in METRIC_COLS)
    return f'<table class="t num fo"><thead><tr><th class="lab">Concession</th>{heads}</tr></thead><tbody>{body}</tbody></table>'


def type_message(F, typ):
    y = F.y
    rows = []
    for d in F.dealers:
        fr, fa = F.pair(d, "ytd")
        r, a = F.tm(fr, typ), F.tm(fa, typ)
        if r.get("tot_bt"):
            rows.append((d, r, a))
    if not rows:
        return "Aucune donnée pour ce type de bon de travail."
    fr, fa = F.pair(GROUP, "ytd", typ)
    gr, ga = F.tm(fr, typ), F.tm(fa, typ)
    hi = max(rows, key=lambda t: t[1]["tot_bt"])
    lo = min(rows, key=lambda t: t[1]["tot_bt"])
    txt = (f"Groupe : <b>{money(gr.get('tot_bt'))}</b> par BT {TYPES[typ].lower()} depuis janvier "
           f"(main-d'œuvre {money(gr.get('mo_bt'))}, pièces {money(gr.get('pc_bt'))})")
    t, _ = fd(gr.get("tot_bt"), ga.get("tot_bt"), "$")
    if t:
        txt += f", {t} vs {y-1} à périmètre comparable"
    txt += (f". Écart entre concessions : {escape(DEALER_SHORT[hi[0]])} {money(hi[1]['tot_bt'])}, "
            f"{escape(DEALER_SHORT[lo[0]])} {money(lo[1]['tot_bt'])}.")
    return txt


def p_type(F, typ):
    y, m = F.y, F.m
    return f"""
      <div class="eyebrow">Bons de travail · {escape(TYPES[typ])}</div>
      <h1>{escape(TYPES[typ])} : dollars et heures par BT</h1>
      {key(type_message(F, typ) + "<br><span class='kn'>" + escape(TYPE_NOTES[typ]) + "</span>")}
      <div class="band-lab">Cumul {MOIS[1]}–{MOIS[m]} {y} <span>sous chaque valeur : écart vs {y-1}</span></div>
      {type_table(F, typ, "ytd")}
      <div class="band-lab">Mois {de(m)} {y} <span>vs {MOIS[m]} {y-1}</span></div>
      {type_table(F, typ, "month")}
      <div class="note">M-O et pièces = ventes. PB / BT = profit brut M-O + pièces ÷ BT. Heures / BT et taux effectif (M-O ÷ heures vendues) :
      seulement les concessions dont les fichiers donnent les heures. Groupe : valeur de toutes les concessions ; écart à périmètre comparable
      (pour les heures : concessions qui ont les heures les deux années).</div>"""


def p_type_charts(F):
    y, m = F.y, F.m
    blocks = ""
    for typ in MAIN_TYPES:
        items = []
        for d in F.dealers + [GROUP]:
            fr, fa = F.pair(GROUP, "ytd", typ) if d == GROUP else F.pair(d, "ytd")
            r, a = F.tm(fr, typ), F.tm(fa, typ)
            if r.get("tot_bt") or a.get("tot_bt"):
                items.append((ds(d), a.get("tot_bt"), r.get("tot_bt")))
        blocks += (f'<div class="chart-title">{escape(TYPES[typ])}</div>'
                   f'<div class="chart">{paired_bars(items, "$", prev_label=f"{y-1}", cur_label=f"{y}")}</div>')
    return f"""
      <div class="eyebrow">Bons de travail</div>
      <h1>Total par BT : {y} comparé à {y-1}</h1>
      {key(f"Main-d'œuvre + pièces par bon de travail, cumul {MOIS[1]}–{MOIS[m]}. Barre grise : {y-1} ; barre bleue : {y}. "
           "Groupe : à périmètre comparable.")}
      {blocks}"""


def p_mix(F):
    y, m = F.y, F.m
    body = ""
    for d in F.dealers + [GROUP]:
        fr, fa = F.flat(d, "ytd"), F.flat(d, "ytd", "ap")
        if not fr:
            continue
        tot_r = sum((t.get("bt") or 0) for t in fr["types"].values())
        tot_a = sum((t.get("bt") or 0) for t in (fa or {"types": {}})["types"].values()) if fa else 0
        mo_r = sum((t.get("mo_v") or 0) for t in fr["types"].values())
        tds = ""
        for typ in TYPES:
            b = (fr["types"].get(typ) or {}).get("bt") or 0
            ba = ((fa or {}).get("types", {}).get(typ) or {}).get("bt") or 0 if fa else None
            sh = div(b, tot_r)
            sha = div(ba, tot_a) if fa and tot_a else None
            t, c = fd(sh, sha, "%")
            tds += f'<td><div>{pct(sh, 0) if b else "—"}</div><div class="dsub {c}">{t if b else ""}</div></td>'
        for typ in MAIN_TYPES:
            v = (fr["types"].get(typ) or {}).get("mo_v") or 0
            tds += f'<td class="{"sep" if typ == "client" else ""}"><div>{pct(div(v, mo_r), 0)}</div><div class="dsub">&nbsp;</div></td>'
        body += f'<tr class="{"strong" if d == GROUP else ""}"><td class="lab">{escape(dl(d))}</td><td><div>{num(tot_r)}</div><div class="dsub">&nbsp;</div></td>{tds}</tr>'
    heads = "".join(f"<th>{escape(TYPES[t])}</th>" for t in TYPES) + "".join(
        f'<th class="{"sep" if t == "client" else ""}">{escape(TYPES[t].split(" ")[0])}</th>' for t in MAIN_TYPES)
    # carrosserie
    cbody = ""
    for d in F.dealers:
        for mode in ("ytd",):
            fr, fa = F.flat(d, mode), F.flat(d, mode, "ap")
            car = (fr or {}).get("carrosserie") or {}
            tot = car.get("total") or {}
            if not (tot.get("v") or tot.get("pb")):
                continue
            ca = ((fa or {}).get("carrosserie") or {}).get("total") or {}
            st = car.get("sous_traitance") or {}
            sta = ((fa or {}).get("carrosserie") or {}).get("sous_traitance") or {}
            cbody += (f'<tr><td class="lab">{escape(DEALERS[d])}</td>'
                      + cell(tot.get("v"), ca.get("v"), "k") + cell(tot.get("pb"), ca.get("pb"), "k")
                      + cell(div(tot.get("pb"), tot.get("v")), div(ca.get("pb"), ca.get("v")), "%")
                      + cell(tot.get("bt") or None, ca.get("bt") or None, "n")
                      + cell(st.get("v"), sta.get("v"), "k") + "</tr>")
    ctable = (f"""<div class="band-lab">Carrosserie <span>cumul {y}</span></div>
      <table class="t num fo"><thead><tr><th class="lab">Concession</th><th>Ventes</th><th>Profit brut</th><th>Marge</th>
      <th>Nombre de BT</th><th>dont sous-traitance</th></tr></thead><tbody>{cbody}</tbody></table>
      <div class="note">Carrosserie : main-d'œuvre, peinture et matériel, sous-traitance (ventes). VW confie sa carrosserie en sous-traitance ;
      HAWKS et STM ont leur propre atelier (à l'état GM, seuls les BT de peinture et les BT internes sont comptés).</div>""" if cbody else "")
    return f"""
      <div class="eyebrow">Composition</div>
      <h1>Mix des bons de travail et carrosserie</h1>
      {key("Le mix des BT explique une bonne partie des écarts de dollars par BT entre concessions : un atelier chargé de BT internes "
           "(reconditionnement) ou de garanties n'a pas le même profil qu'un atelier surtout client.")}
      <div class="band-lab">Part de chaque type <span>cumul {y} · nombre de BT puis ventes de main-d'œuvre · écart de la part vs {y-1} en points</span></div>
      <table class="t num fo"><thead><tr><th class="lab" rowspan="2">Concession</th><th rowspan="2">BT</th>
      <th colspan="{len(TYPES)}">Part des BT</th><th colspan="3" class="sep">Part des ventes M-O</th></tr><tr>{heads}</tr></thead><tbody>{body}</tbody></table>
      {ctable}"""


def p_atelier(F):
    y, m = F.y, F.m
    hd = F.hours_dealers("ytd")
    body = ""
    for mode, lab in (("month", f"{MOIS[m].capitalize()} {y}"), ("ytd", f"Cumul {y}")):
        body += f'<tr class="sec"><td colspan="11">{escape(lab)}</td></tr>'
        for d in hd:
            fr, fa = F.flat(d, mode), F.flat(d, mode, "ap")
            r, a = atelier_metrics(fr), atelier_metrics(fa)
            cr, ca = F.tm(fr, "client"), F.tm(fa, "client")
            gr, ga = F.tm(fr, "garantie"), F.tm(fa, "garantie")
            ir, ia = F.tm(fr, "interne"), F.tm(fa, "interne")
            body += (f'<tr><td class="lab">{escape(DEALERS[d])}</td>'
                     + cell(r["disp"], a["disp"], "n") + cell(r["vendues"], a["vendues"], "n")
                     + cell(r["productivite"], a["productivite"], "%") + cell(r["efficacite"], a["efficacite"], "%")
                     + cell(r["h_tech"], a["h_tech"], "n")
                     + cell(cr.get("h_bt"), ca.get("h_bt"), "h") + cell(gr.get("h_bt"), ga.get("h_bt"), "h") + cell(ir.get("h_bt"), ia.get("h_bt"), "h")
                     + cell(cr.get("elr"), ca.get("elr"), "$") + cell(gr.get("elr"), ga.get("elr"), "$")
                     + "</tr>")
    missing = [d for d in F.dealers if d not in hd]
    rates = ""
    for d in F.dealers:
        at = (F.flat(d, "ytd") or {}).get("atelier") or {}
        ta = at.get("taux_affiche") or {}
        fr = F.flat(d, "ytd")
        cr = F.tm(fr, "client")
        if ta.get("client"):
            rates += (f"<tr><td class='lab'>{escape(DEALERS[d])}</td><td>{money(ta.get('client'))}</td><td>{money(ta.get('garantie'))}</td>"
                      f"<td>{money(ta.get('interne'))}</td><td>{money(cr.get('mo_bt'))}</td>"
                      f"<td>{num(div(cr.get('mo_bt'), ta.get('client')), 2) if ta.get('client') else '—'}</td></tr>")
    rtable = (f"""<div class="band-lab">Taux horaires affichés (état GM) <span>sans heures vendues, une piste : M-O par BT client ÷ taux affiché ≈ heures facturées par BT au plein tarif</span></div>
      <table class="t num fo"><thead><tr><th class="lab">Concession</th><th>Client</th><th>Garantie</th><th>Interne</th><th>M-O / BT client {y}</th><th>≈ heures au taux affiché</th></tr></thead>
      <tbody>{rates}</tbody></table>""" if rates else "")
    msg = []
    for d in hd:
        r = atelier_metrics(F.flat(d, "ytd"))
        cr = F.tm(F.flat(d, "ytd"), "client")
        if r["productivite"]:
            msg.append(f"{escape(DEALERS[d])} : {num(r['vendues'])} h vendues depuis janvier sur {num(r['disp'])} h disponibles "
                       f"(productivité {pct(r['productivite'], 0)}, efficacité {pct(r['efficacite'], 0)}), {num(cr.get('h_bt'), 2)} h par BT client")
    return f"""
      <div class="eyebrow">Atelier</div>
      <h1>Heures vendues et productivité de l'atelier</h1>
      {key(("<br>".join(msg) + ".") if msg else "Aucune heure vendue dans les fichiers de la période.")}
      <table class="t num fo small"><thead><tr><th class="lab" rowspan="2">Concession</th><th rowspan="2">Heures disponibles</th><th rowspan="2">Heures vendues</th>
      <th rowspan="2">Productivité</th><th rowspan="2">Efficacité</th><th rowspan="2">Heures vendues / tech.</th>
      <th colspan="3" class="sep">Heures par BT</th><th colspan="2" class="sep">Taux effectif</th></tr>
      <tr><th class="sep">Client</th><th>Garantie</th><th>Interne</th><th class="sep">Client</th><th>Garantie</th></tr></thead><tbody>{body}</tbody></table>
      <div class="note">Sources : état Volkswagen Canada (Page 6) et état Hyundai Canada (Page 6). Productivité = heures pointées sur les BT ÷ heures disponibles ;
      efficacité = heures vendues ÷ heures pointées (au-dessus de 100 % : les techniciens battent le temps facturé). Taux effectif = ventes de main-d'œuvre ÷ heures vendues.
      Sous chaque valeur : écart vs {y-1}.</div>
      {"<div class='callout'><div class='ch'>Heures manquantes</div>" + escape(", ".join(DEALERS[d] for d in missing)) + " : ni le Réalisé ni l'état financier GM ne donnent les heures vendues. Pour les suivre, il faut un rapport mensuel du système de gestion (DMS) : heures vendues par type de BT (client, garantie, interne) et heures disponibles des techniciens.</div>" if missing else ""}
      {rtable}"""


PC_SHORT = {"client": "BT client", "garantie": "BT garantie", "interne": "BT interne", "carrosserie": "Carros.",
            "comptoir": "Comptoir", "accessoires": "Access.", "gros": "Gros", "pneus": "Pneus", "huile": "Huiles", "divers": "Divers"}


def p_pieces(F):
    y, m = F.y, F.m
    used = set()
    data = {}
    for d in F.dealers:
        fr, fa = F.flat(d, "ytd"), F.flat(d, "ytd", "ap")
        cr = {c: (v, pb) for c, v, pb in fo.pieces_channels(fr)}
        ca = {c: (v, pb) for c, v, pb in fo.pieces_channels(fa)}
        data[d] = (fr, fa, cr, ca)
        used |= {c for c, (v, _) in cr.items() if v}
    chans = [c for c in fo.PC_CHANNELS if c in used]
    heads = "".join(f"<th>{escape(PC_SHORT[c])}</th>" for c in chans)
    rows = mrows = rrows = ""
    for d in F.dealers:
        fr, fa, cr, ca = data[d]
        tv, tpb = fo.pieces_total(fr)
        av_, apb = fo.pieces_total(fa)
        tds = mtds = ""
        for c in chans:
            v, pb = cr.get(c) or (None, None)
            va, pba = ca.get(c) or (None, None)
            tds += f'<td><div>{kmoney(v) if v else "—"}</div><div class="dsub muted">{pct(div(v, tv), 0) if v and tv else "&nbsp;"}</div></td>'
            t, cl = fd(div(pb, v), div(pba, va), "%")
            mtds += f'<td><div>{pct(div(pb, v), 0) if v else "—"}</div><div class="dsub {cl}">{t if v else "&nbsp;"}</div></td>'
        t, cl = fd(tv, av_, "k")
        tds += f'<td class="sep strong"><div>{kmoney(tv)}</div><div class="dsub {cl}">{t}</div></td>'
        t2, c2 = fd(div(tpb, tv), div(apb, av_), "%")
        mtds += f'<td class="sep strong"><div>{pct(div(tpb, tv), 1)}</div><div class="dsub {c2}">{t2}</div></td>'
        rows += f'<tr><td class="lab">{escape(DEALERS[d])}</td>{tds}</tr>'
        mrows += f'<tr><td class="lab">{escape(DEALERS[d])}</td>{mtds}</tr>'
        rtds = ""
        for typ in MAIN_TYPES:
            a_, b_ = F.tm(fr, typ).get("pc_mo"), F.tm(fa, typ).get("pc_mo")
            t3, c3 = fd(a_, b_, "x")
            rtds += f'<td><div>{num(a_, 2)}</div><div class="dsub {c3}">{t3}</div></td>'
        rrows += f'<tr><td class="lab">{escape(DEALERS[d])}</td>{rtds}</tr>'
    g = F.flat(GROUP, "ytd")
    gv, gpb = fo.pieces_total(g)
    rheads = "".join(f"<th>{escape(TYPES[t])}</th>" for t in MAIN_TYPES)
    return f"""
      <div class="eyebrow">Pièces</div>
      <h1>Pièces : ventes et marge par canal</h1>
      {key(f"Depuis janvier : <b>{kmoney(gv)}</b> de ventes de pièces, marge brute <b>{pct(div(gpb, gv), 1)}</b>. "
           "Le gros pèse lourd dans les ventes, à faible marge ; les pièces des BT client ont la meilleure marge.")}
      <div class="band-lab">Ventes par canal <span>cumul {y} · sous la valeur : part du total ; total : écart vs {y-1}</span></div>
      <table class="t num fo small"><thead><tr><th class="lab">Concession</th>{heads}<th class="sep">Total</th></tr></thead><tbody>{rows}</tbody></table>
      <div class="band-lab">Marge brute par canal <span>cumul {y} · écart vs {y-1} en points</span></div>
      <table class="t num fo small"><thead><tr><th class="lab">Concession</th>{heads}<th class="sep">Total</th></tr></thead><tbody>{mrows}</tbody></table>
      <div class="band-lab">Dollars de pièces par dollar de main-d'œuvre <span>cumul {y} · écart vs {y-1}</span></div>
      <table class="t num fo small" style="width:62%"><thead><tr><th class="lab">Concession</th>{rheads}</tr></thead><tbody>{rrows}</tbody></table>
      <div class="note">Pièces facturées sur les BT client / garantie / interne. Total : y compris les ajustements (escomptes, allocations d'achat, rectifications d'inventaire).</div>"""


def month_labels(P, n):
    y, m = split(P)
    out = []
    for i in range(n - 1, -1, -1):
        yy, mm = y, m - i
        while mm <= 0:
            mm += 12
            yy -= 1
        out.append((pkey(yy, mm), f"{MOIS[mm][:3]}. {str(yy)[2:]}" if len(MOIS[mm]) > 4 else f"{MOIS[mm]} {str(yy)[2:]}"))
    return out


def trend(F, typ, k, n=24):
    labels = month_labels(F.P, n)
    series = []
    for d in F.dealers:
        vals = []
        for p, _ in labels:
            f = F.av.get(d, p, "month")
            vals.append(F.tm(f, typ).get(k) if f else None)
        if any(v is not None for v in vals):
            series.append((d, vals))
    return series, [l for _, l in labels]


def p_tendances(F):
    specs = [
        ("client", "mo_bt", "$", "Main-d'œuvre par BT client"),
        ("client", "tot_bt", "$", "Total par BT client (M-O + pièces)"),
        ("client", "bt", "n", "Nombre de BT client par mois"),
        ("client", "h_bt", "h", "Heures vendues par BT client"),
        ("garantie", "tot_bt", "$", "Total par BT garantie"),
        ("interne", "mo_bt", "$", "Main-d'œuvre par BT interne"),
    ]
    blocks = ""
    keys = set()
    for typ, k, f, title in specs:
        series, labels = trend(F, typ, k)
        keys |= {d for d, _ in series}
        blocks += f'<div class="sm"><div class="smh">{escape(title)}</div>{lines_chart(series, f, labels)}</div>'
    return f"""
      <div class="eyebrow">Tendances</div>
      <h1>Tendances sur 24 mois</h1>
      {key("Chaque trait est une concession, mois par mois. Les pointes de BT client d'avril–mai et d'octobre–novembre coïncident avec la saison "
           "des changements de pneus : beaucoup de petits BT, donc moins de dollars par BT ces mois-là. C'est la pente sur plusieurs mois qui compte. "
           "Heures : Volkswagen et Hyundai seulement.")}
      {legend([d for d in F.dealers if d in keys])}
      <div class="smgrid">{blocks}</div>"""


def p_detail_mensuel(F, typ="client"):
    y, m = F.y, F.m
    labels = month_labels(F.P, 12)
    head = "".join(f"<th>{escape(l)}</th>" for _, l in labels)
    body = ""
    for k, lab, f in (("bt", "BT", "n"), ("mo_bt", "M-O / BT", "$"), ("tot_bt", "Total / BT", "$")):
        body += f'<tr class="sec"><td colspan="{len(labels) + 1}">{escape(lab)} — {escape(TYPES[typ].lower())}</td></tr>'
        for d in F.dealers:
            tds = ""
            for p, _ in labels:
                fl = F.av.get(d, p, "month")
                v = F.tm(fl, typ).get(k) if fl else None
                tds += f"<td>{num(v) if v is not None else '—'}</td>"
            body += f'<tr><td class="lab">{escape(DEALER_SHORT[d])}</td>{tds}</tr>'
    return f"""
      <div class="eyebrow">Tendances</div>
      <h1>Détail mensuel des BT client — 12 derniers mois</h1>
      {key("Les mêmes chiffres que les tendances, en tableau, pour repérer un mois atypique (dollars par BT en $).")}
      <table class="t num trend wide"><thead><tr><th class="lab">Concession</th>{head}</tr></thead><tbody>{body}</tbody></table>"""


def p_couverture(F):
    y, m = F.y, F.m
    labels = {"gabarit": "Réalisé", "etat_gm": "État GM", "etat_hyundai": "État Hyundai", "etat_vw": "État VW"}
    rows = ""
    for d in F.dealers:
        fr = F.flat(d, "ytd")
        has_h = any(t.get("h") for t in (fr or {"types": {}})["types"].values())
        src = F.s.source_format(d, F.P)
        ap = F.av.ap_source(d, F.P, "ytd")
        bud = F.av.get(d, F.P, "ytd", "budget")
        hs = ((F.av.native(d, F.P, "ytd") or {}).get("heures_source") == "etat")
        rows += (f"<tr><td class='lab'>{escape(DEALERS[d])}</td><td class='c'>{escape(labels.get(src, src or '—'))}</td>"
                 f"<td class='c'><span class='ok'>Oui</span></td>"
                 f"<td class='c'>{'<span class=ok>Oui</span>' + (' (état ' + ('VW' if d == 'vw' else 'Hyundai') + ')' if hs else '') if has_h else '<span class=no>Non</span>'}</td>"
                 f"<td class='c'>{'<span class=ok>Colonnes du Réalisé</span>' if ap == 'natif' else ('<span class=rec>Fichiers ' + str(y-1) + '</span>' if ap else '<span class=no>Non</span>')}</td>"
                 f"<td class='c'>{'<span class=ok>Oui</span>' if bud else '<span class=muted>Non</span>'}</td></tr>")
    return f"""
      <div class="eyebrow">Méthode</div>
      <h1>Sources, définitions et limites</h1>
      <table class="t cov"><thead><tr><th class="lab">Concession</th><th>Source de {MOIS[m]} {y}</th><th>BT par type</th><th>Heures vendues</th><th>An passé</th><th>Budget des BT</th></tr></thead>
      <tbody>{rows}</tbody></table>
      <h2>D'où viennent les chiffres</h2>
      <ul class="retenir compact">
        <li><b>Réalisé</b> : blocs Service (« M/O Client / Garantie / Interne / Esthétique », colonne # = BT), Pièces et Carrosserie ; colonnes réel, budget, an passé.</li>
        <li><b>État GM</b> (HAWKS, STM) : Page 6, B.R., ventes et profit brut par compte (460A client, 460D mobile, 462 garantie, 463 interne, 464 inspection).</li>
        <li><b>État Hyundai Canada</b> : Page 4 (B.R., ventes, profit brut par compte) et Page 6 (heures disponibles, poinçonnées, facturées par type).</li>
        <li><b>État Volkswagen Canada</b> : Pages 5 et 6. Quand le Réalisé VW est retenu, ses heures viennent de l'état du même mois si les BT concordent (± 3 %).</li>
      </ul>
      <h2>Définitions</h2>
      <dl class="defs">
        <dt>Bon de travail (BT)</dt><dd>Compté par type : un BT qui a des lignes client et garantie compte dans les deux types.</dd>
        <dt>Main-d'œuvre, pièces, total, profit brut par BT</dt><dd>Ventes de M-O (ou de pièces facturées sur ces BT, ou profit brut M-O + pièces) ÷ BT du type. Total = M-O + pièces.</dd>
        <dt>Heures par BT, taux effectif</dt><dd>Heures vendues ÷ BT ; ventes de M-O ÷ heures vendues (seulement quand la source donne les heures).</dd>
        <dt>Groupe</dt><dd>Ratios recalculés à partir des sommes ; écarts à périmètre comparable.</dd>
      </dl>
      <h2>Limites connues</h2>
      <ul class="retenir compact">
        <li>STM : service mobile (460D) compté dans les BT client ; ses pièces sont inscrites avec celles des BT client (467D vide). Le compte 460D
        n'est utilisé qu'à partir de l'état d'août 2026 (cumul retraité) : le total client se compare d'une année à l'autre, pas le détail « mobile ».
</li>
        <li>Techniciens de l'état GM (Page 7) non utilisés : incohérents pour STM.
        Hyundai sept. et oct. 2025 : les états « FFS Hyundai F 09-2026 » et « 10-2026 » reprennent les BT et heures d'août 2026 ; retirés (montants gardés).</li>
      </ul>"""


# ------------------------------------------------------------------ pages pour les rapports mensuels
def type_rows_table(F, d, mode):
    """Une concession (ou le Groupe) : une ligne par type de BT + total."""
    body = ""
    fr, fa = F.pair(d, mode)
    for typ in list(TYPES) + ["all"]:
        r, a = F.tm(fr, typ), F.tm(fa, typ)
        if typ != "all" and not r.get("bt") and not r.get("mo_v"):
            continue
        strong = typ == "all"
        lab = "Tous les BT" if strong else TYPES[typ]
        body += f'<tr class="{"strong" if strong else ""}"><td class="lab">{escape(lab)}</td>' + "".join(
            cell(r.get(k), a.get(k), f, strong) for k, _, f in METRIC_COLS) + "</tr>"
        if typ in ("client", "interne"):
            dk = "mobile" if typ == "client" else "inspection"
            det = (fr or {}).get("detail", {}).get(dk)
            if det and det.get("bt"):
                mr, ma = type_metrics(det), type_metrics(((fa or {}).get("detail") or {}).get(dk))
                body += (f'<tr class="sub"><td class="lab">{escape(fo.DETAIL_LABELS[dk])}</td>' + cell(mr.get("bt"), ma.get("bt"), "n")
                         + cell(mr.get("mo_bt"), ma.get("mo_bt"), "$") + '<td class="muted">—</td>' * (len(METRIC_COLS) - 2) + "</tr>")
    heads = "".join(f"<th>{h}</th>" for _, h, _ in METRIC_COLS)
    return f'<table class="t num fo"><thead><tr><th class="lab">Type de BT</th>{heads}</tr></thead><tbody>{body}</tbody></table>'


def page_concession(s, P, d):
    """Page « Après-vente : bons de travail » du rapport d'une concession."""
    F = FO(s, P)
    y, m = F.y, F.m
    fr, fa = F.pair(d, "ytd")
    if not fr:
        return None
    c, ca = F.tm(fr, "client"), F.tm(fa, "client")
    msg = (f"Depuis janvier : <b>{num(c.get('bt'))}</b> BT client à <b>{money(c.get('tot_bt'))}</b> par BT "
           f"(main-d'œuvre {money(c.get('mo_bt'))}, pièces {money(c.get('pc_bt'))})")
    t, _ = fd(c.get("tot_bt"), ca.get("tot_bt"), "$")
    if t:
        msg += f", {t} vs {y-1}"
    if c.get("h_bt"):
        msg += f" ; {num(c['h_bt'], 2)} h vendue par BT client, taux effectif {money(c.get('elr'))}"
    msg += "."
    at = atelier_metrics(fr)
    at_line = ""
    if at.get("productivite"):
        aa = atelier_metrics(fa)
        at_line = (f'<div class="band-lab">Atelier <span>cumul {y}</span></div><p>{num(at["vendues"])} h vendues sur {num(at["disp"])} h disponibles '
                   f'(productivité {pct(at["productivite"], 0)}, efficacité {pct(at["efficacite"], 0)}'
                   + (f' ; {y-1} : {pct(aa["productivite"], 0)} et {pct(aa["efficacite"], 0)}' if aa.get("productivite") else "") + ").</p>")
    no_h = "" if any(t.get("h") for t in fr["types"].values()) else (
        '<div class="callout"><div class="ch">Heures manquantes</div>Les fichiers de cette concession ne donnent pas les heures vendues : '
        "heures par BT et taux effectif non calculés. Il faut un rapport mensuel du système de gestion (heures vendues par type de BT).</div>")
    return f"""
      <div class="eyebrow">Après-vente</div>
      <h1>Bons de travail : dollars et heures par BT</h1>
      {key(msg)}
      <div class="band-lab">Cumul {MOIS[1]}–{MOIS[m]} {y} <span>sous chaque valeur : écart vs {y-1}</span></div>
      {type_rows_table(F, d, "ytd")}
      <div class="band-lab">Mois {de(m)} {y} <span>vs {MOIS[m]} {y-1}</span></div>
      {type_rows_table(F, d, "month")}
      {at_line}{no_h}
      <div class="note">M-O et pièces = ventes. PB / BT = profit brut M-O + pièces ÷ BT. Taux effectif = ventes de M-O ÷ heures vendues.
      Détail complet (Groupe, atelier, pièces, tendances) : rapport « Opérations fixes ».</div>"""


def pages_groupe(s, P):
    """Pages après-vente du rapport du Groupe : vue d'ensemble et BT client."""
    F = FO(s, P)
    return [p_overview(F), p_type(F, "client")]


def build_book(s, P):
    rc.setup(s, P)
    rc.FOOTER_LABEL = f"Opérations fixes · Analyse approfondie · {rc.PERIOD_LABEL}"
    F = FO(s, P)
    bk = Book()
    bk.add_cover(p_cover(F))
    bk.add(p_essentiel(F))
    bk.add(p_overview(F))
    for typ in MAIN_TYPES:
        bk.add(p_type(F, typ))
    bk.add(p_type_charts(F))
    bk.add(p_mix(F))
    bk.add(p_atelier(F))
    bk.add(p_pieces(F))
    bk.add(p_tendances(F))
    bk.add(p_detail_mensuel(F))
    bk.add(p_couverture(F))
    return bk





def generate(s, P, out_pdf):
    bk = build_book(s, P)
    html = wrap_html(f"Opérations fixes — {rc.PERIOD_LABEL}", bk.pages)
    rc.FOOTER_LABEL = ""
    hp = os.path.splitext(out_pdf)[0] + ".html"
    with open(hp, "w", encoding="utf-8") as f:
        f.write(html)
    over = to_pdf(hp, out_pdf)
    return len(bk.pages), over, hp


def main():
    ap = argparse.ArgumentParser(description="Rapport Opérations fixes — Groupe Automax")
    ap.add_argument("--mois")
    ap.add_argument("--data", default=os.path.join(HERE, "data.json"))
    ap.add_argument("--budget", default=os.path.join(HERE, "budgets.csv"))
    ap.add_argument("--sortie", default=HERE)
    ap.add_argument("--garder-html", action="store_true")
    a = ap.parse_args()
    s = Store(a.data, a.budget)
    av = fo.AVStore(s)
    if a.mois:
        P = a.mois
    else:
        common = set.intersection(*[set(s.periods(d)) for d in DEALERS])
        P = max(p for p in common if all(av.get(d, p, "ytd") for d in DEALERS))
    os.makedirs(a.sortie, exist_ok=True)
    fp = os.path.join(a.sortie, f"Rapport_Operations_fixes_{P}.pdf")
    n, over, hp = generate(s, P, fp)
    if not a.garder_html:
        os.remove(hp)
    print(f"PDF : {fp} ({n} pages)" + (f" — ATTENTION débordement {over}" if over else ""))


if __name__ == "__main__":
    main()
