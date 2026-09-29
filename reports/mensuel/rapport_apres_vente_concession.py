#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rapport « Opérations fixes » par concession — Groupe Automax.

Pour chaque concession : résultats des départements Service, Pièces et
Carrosserie ; bons de travail (BT) par type — client, garantie, interne,
esthétique — avec dollars et heures par BT ; positionnement dans le Groupe ;
détail mois par mois comparé à l'an passé ; atelier ; pièces par canal ;
tendances sur 24 mois.

    python rapport_apres_vente_concession.py --data ../../data/data.json --mois 2026-08 --sortie sortie
    python rapport_apres_vente_concession.py --data ../../data/data.json --mois 2026-08 --concession vw
"""
import argparse
import os
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import rapport_commun as rc
from rapport_commun import key, tile, Book, wrap_html, to_pdf, LOGO_DARK
from kpi_data import Store, DEALERS, DEALER_SHORT, MOIS, pkey, split, prior_year, label_period, ratios
from kpi_analyse import money, kmoney, num, pct, pts, var_pct, de, NBSP
from kpi_svg import _text, nice_ticks, INK, MUTED, GRID, AXIS, PREV, CUR
import kpi_apres_vente as fo
from kpi_apres_vente import TYPES, MAIN_TYPES, type_metrics, atelier_metrics, div, types_for
from rapport_apres_vente import (FO, GROUP, METRIC_COLS, TYPE_NOTES, DEALER_COLOR, PC_SHORT, fv, fd, cell,
                                 type_rows_table, lines_chart, month_labels, dl)

FILE_NAMES = {"bmw": "BMW_Sherbrooke", "vw": "Volkswagen", "stm": "STM", "hyundai": "Hyundai", "hawks": "HAWKS"}
SOURCE_LABELS = {"gabarit": "Réalisé (gabarit du Groupe)", "etat_gm": "état financier GM Canada",
                 "etat_hyundai": "état financier Hyundai Canada", "etat_vw": "état financier Volkswagen Canada"}
DEPTS = (("Service", "Service"), ("Pièces", "Pièces"), ("Carrosserie", "Carrosserie"))


# ------------------------------------------------------------------ données
def dept_kv(F, d, mode, dep, k):
    """(réel, an passé) d'une ligne de département ; an passé : colonne du
    Réalisé, sinon le même mois de l'an passé."""
    def get(p, field):
        rec = F.s.raw.get(d, {}).get("periods", {}).get(p)
        x = ((((rec or {}).get("sections") or {}).get(mode) or {}).get("departments") or {}).get(dep) or {}
        v = (x.get(k) or {}).get(field) if isinstance(x.get(k), dict) else None
        return v if isinstance(v, (int, float)) else None
    r = get(F.P, "real")
    a = get(F.P, "prior_year")
    if a is None:
        a = get(prior_year(F.P), "real")
    return r, a


def rank_of(F, d, typ, k, mode="ytd"):
    vals = {}
    for x in F.dealers:
        v = F.tm(F.flat(x, mode), typ).get(k)
        if v is not None:
            vals[x] = v
    if d not in vals:
        return None, len(vals), None, None
    order = sorted(vals, key=lambda x: -vals[x])
    return order.index(d) + 1, len(vals), min(vals.values()), max(vals.values())


def bars_ap(values, ap_values, labels, fmt, width=318, height=112):
    """Barres mensuelles (année en cours, bleu) + trait gris de l'an passé."""
    ml, mr, mt, mb = 40, 4, 10, 16
    pw, ph = width - ml - mr, height - mt - mb
    allv = [v for v in values + ap_values if v is not None]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">']
    if not allv:
        out.append(_text(width / 2, height / 2, "n/d", 9, "middle", MUTED))
        out.append("</svg>")
        return "".join(out)
    ticks = nice_ticks(0, max(allv), 3)
    y1 = ticks[-1] or 1
    Y = lambda v: mt + ph - v / y1 * ph
    for t in ticks:
        out.append(f'<line x1="{ml}" x2="{width-mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{AXIS if t == 0 else GRID}" stroke-width="0.8"/>')
        lab = (num(t) + NBSP + "$") if fmt == "$" else (num(t, 1) if fmt == "h" else num(t))
        out.append(_text(ml - 4, Y(t) + 2.5, lab, 6.4, "end", MUTED))
    n = len(labels)
    slot = pw / n
    bw = slot * 0.56
    for i, lab in enumerate(labels):
        x = ml + slot * i + (slot - bw) / 2
        v = values[i]
        if v is not None:
            out.append(f'<rect x="{x:.1f}" y="{Y(v):.1f}" width="{bw:.1f}" height="{max(Y(0) - Y(v), 1):.1f}" rx="1.5" fill="{CUR}"/>')
        a = ap_values[i]
        if a is not None:
            ya = Y(a)
            out.append(f'<line x1="{x-2:.1f}" x2="{x+bw+2:.1f}" y1="{ya:.1f}" y2="{ya:.1f}" stroke="#ffffff" stroke-width="4.4" stroke-linecap="round"/>')
            out.append(f'<line x1="{x-2:.1f}" x2="{x+bw+2:.1f}" y1="{ya:.1f}" y2="{ya:.1f}" stroke="{PREV}" stroke-width="2.4" stroke-linecap="round"/>')
        if i % 2 == (n - 1) % 2:
            out.append(_text(x + bw / 2, height - 4, lab, 6.6, "middle", MUTED))
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ pages
def p_cover(F, d):
    y, m = F.y, F.m
    r, a = F.comp_pair(d, "ytd")
    pb_r = ratios(r).get("apres_vente") if r else None
    pb_a = ratios(a).get("apres_vente") if a else None
    fr, fa = F.pair(d, "ytd")
    tr, ta = F.tm(fr, "all"), F.tm(fa, "all")
    cr, ca = F.tm(fr, "client"), F.tm(fa, "client")

    def dtxt(x, b, f="$"):
        t, _ = fd(x, b, f)
        return f"{t} vs {y-1}" if t else f"{y-1} : n/d"
    return f"""
      <div class="logo cv-logo">{LOGO_DARK}</div>
      <div class="cv-mid">
        <div class="cv-kicker">Opérations fixes · {escape(label_period(F.P))}</div>
        <div class="cv-title cv-dealer">{escape(DEALERS[d])}</div>
        <div class="cv-sub">Service, pièces et carrosserie : résultats des départements, bons de travail par type (client, garantie, interne),
        dollars et heures par bon, atelier, pièces et tendances. Mois {de(m)} et cumul {MOIS[1]}–{MOIS[m]} {y}, comparés à {y-1}.</div>
        <div class="cv-kpis">
          <div><div class="cv-kl">PB après-vente cumulatif</div><div class="cv-kv">{kmoney(pb_r)}</div><div class="cv-kd">{escape(dtxt(pb_r, pb_a))}</div></div>
          <div><div class="cv-kl">Bons de travail {y}</div><div class="cv-kv">{num(tr.get('bt'))}</div><div class="cv-kd">{escape(dtxt(tr.get('bt'), ta.get('bt'), 'n'))}</div></div>
          <div><div class="cv-kl">Total par BT client</div><div class="cv-kv">{money(cr.get('tot_bt'))}</div><div class="cv-kd">{escape(dtxt(cr.get('tot_bt'), ca.get('tot_bt')))}</div></div>
        </div>
      </div>
      <div class="cv-foot">
        <div>Une concession du Groupe Automax</div>
        <div>Préparé le {rc.PREPARED} à partir du tableau de bord KPI · Source d'{MOIS[m]} : {escape(SOURCE_LABELS.get(F.s.source_format(d, F.P), '—'))} · Non audité</div>
        <div class="cv-conf">Confidentiel — usage interne — direction seulement</div>
      </div>"""


def dealer_findings(F, d):
    y = F.y
    out = []
    r, a = F.comp_pair(d, "ytd")
    if r and a:
        rr, ra = ratios(r), ratios(a)
        parts = []
        for k, lab in (("pb_service", "service"), ("pb_pieces", "pièces"), ("pb_carrosserie", "carrosserie")):
            if r[k] or a[k]:
                parts.append(f"{lab} {kmoney(r[k] - a[k], sign=True)}")
        out.append(f"<b>Profit brut après-vente : {kmoney(rr['apres_vente'])}</b> depuis janvier, {kmoney(rr['apres_vente'] - ra['apres_vente'], sign=True)} "
                   f"({pct(var_pct(rr['apres_vente'], ra['apres_vente']), 0, sign=True)}) vs {y-1} — " + ", ".join(parts)
                   + f". Il couvre <b>{pct(rr['absorption'], 0)}</b> des frais fixes ({pts(rr['absorption'] - ra['absorption'], 1)}).")
    fr, fa = F.pair(d, "ytd")
    for typ in MAIN_TYPES:
        c, ca = F.tm(fr, typ), F.tm(fa, typ)
        if not c.get("bt"):
            continue
        txt = f"<b>{escape(TYPES[typ])}</b> : {num(c['bt'])} BT"
        if ca.get("bt"):
            txt += f" ({pct(var_pct(c['bt'], ca['bt']), 0, sign=True)})"
        txt += f", <b>{money(c.get('tot_bt'))}</b> par BT"
        if ca.get("tot_bt"):
            dm = (c.get("mo_bt") or 0) - (ca.get("mo_bt") or 0)
            dp = (c.get("pc_bt") or 0) - (ca.get("pc_bt") or 0)
            txt += (f" ({pct(var_pct(c['tot_bt'], ca['tot_bt']), 0, sign=True)} : main-d'œuvre {money(dm, sign=True)}, "
                    f"pièces {money(dp, sign=True)} par BT)")
        rk, n, _, _ = rank_of(F, d, typ, "tot_bt")
        if rk:
            txt += f" ; {rk}{'er' if rk == 1 else 'e'} sur {n} concessions du Groupe"
        if c.get("h_bt"):
            txt += f" ; {num(c['h_bt'], 2)} h vendue par BT, taux effectif {money(c.get('elr'))}"
        out.append(txt + ".")
    at, aa = atelier_metrics(fr), atelier_metrics(fa)
    if at.get("productivite"):
        t = (f"<b>Atelier</b> : {num(at['vendues'])} h vendues sur {num(at['disp'])} h disponibles ; productivité {pct(at['productivite'], 0)}, "
             f"efficacité {pct(at['efficacite'], 0)}")
        if aa.get("productivite"):
            t += f" ({y-1} : {pct(aa['productivite'], 0)} et {pct(aa['efficacite'], 0)})"
        out.append(t + ".")
    return out


def p_essentiel(F, d):
    y, m = F.y, F.m
    fr, fa = F.pair(d, "ytd")
    tiles = []
    for typ in MAIN_TYPES:
        r, a = F.tm(fr, typ), F.tm(fa, typ)
        if not r.get("bt"):
            continue
        t, c = fd(r.get("tot_bt"), a.get("tot_bt"), "$")
        lines = [(f"M-O {money(r.get('mo_bt'))} + pièces {money(r.get('pc_bt'))}", "muted"),
                 (f"{t} vs {y-1}" if t else f"{y-1} : n/d", c),
                 (f"{num(r.get('bt'))} BT depuis janvier", "muted")]
        tiles.append(tile(f"Total par BT — {TYPES[typ].lower()}", money(r.get("tot_bt")), lines, typ == "client"))
    items = dealer_findings(F, d)
    return f"""
      <div class="eyebrow">Sommaire</div>
      <h1>{escape(DEALERS[d])} : l'essentiel des opérations fixes</h1>
      {key(f"Cumul {MOIS[1]}–{MOIS[m]} {y} comparé à la même période {y-1}. Total par BT = main-d'œuvre + pièces vendues sur les bons de travail du type.")}
      <div class="band-lab">Dollars par bon de travail <span>cumul {y}</span></div>
      <div class="tiles">{''.join(tiles)}</div>
      <h2>Ce qu'il faut retenir</h2>
      <ul class="retenir">{''.join(f'<li>{t}</li>' for t in items)}</ul>"""


def p_departements(F, d):
    y, m = F.y, F.m
    blocks = ""
    for mode, title in (("ytd", f"Cumul {MOIS[1]}–{MOIS[m]} {y}"), ("month", f"Mois {de(m)} {y}")):
        body = ""
        tot = {"pb": [0, 0], "dep": [0, 0], "pd": [0, 0]}
        ok = {"pb": True, "dep": True, "pd": True}
        for dep, lab in DEPTS:
            pb_r, pb_a = dept_kv(F, d, mode, dep, "profit_brut")
            de_r, de_a = dept_kv(F, d, mode, dep, "total_depenses")
            pd_r, pd_a = dept_kv(F, d, mode, dep, "profit_departemental")
            if not (pb_r or de_r):
                continue
            for kk, (x, b) in (("pb", (pb_r, pb_a)), ("dep", (de_r, de_a)), ("pd", (pd_r, pd_a))):
                tot[kk][0] += x or 0
                if b is None:
                    ok[kk] = False
                else:
                    tot[kk][1] += b
            de_cell = cell(de_r, de_a, "k").replace('class="dsub pos"', 'class="dsub TMP"').replace('class="dsub neg"', 'class="dsub pos"').replace('class="dsub TMP"', 'class="dsub neg"')
            body += (f'<tr><td class="lab">{escape(lab)}</td>' + cell(pb_r, pb_a, "k") + de_cell + cell(pd_r, pd_a, "k", True)
                     + cell(div(de_r, pb_r), div(de_a, pb_a), "%").replace('dsub pos', 'dsub XX').replace('dsub neg', 'dsub pos').replace('dsub XX', 'dsub neg')
                     + "</tr>")
        de_tot = cell(tot["dep"][0], tot["dep"][1] if ok["dep"] else None, "k", True)
        de_tot = de_tot.replace('dsub pos', 'dsub XX').replace('dsub neg', 'dsub pos').replace('dsub XX', 'dsub neg')
        body += (f'<tr class="strong"><td class="lab">Après-vente</td>' + cell(tot["pb"][0], tot["pb"][1] if ok["pb"] else None, "k", True)
                 + de_tot + cell(tot["pd"][0], tot["pd"][1] if ok["pd"] else None, "k", True)
                 + cell(div(tot["dep"][0], tot["pb"][0]), div(tot["dep"][1], tot["pb"][1]) if ok["dep"] and ok["pb"] else None, "%", True)
                 .replace('dsub pos', 'dsub XX').replace('dsub neg', 'dsub pos').replace('dsub XX', 'dsub neg') + "</tr>")
        blocks += f"""<div class="band-lab">{escape(title)} <span>sous chaque valeur : écart vs {y-1}</span></div>
          <table class="t num fo"><thead><tr><th class="lab">Département</th><th>Profit brut</th><th>Dépenses du département</th>
          <th>Profit départemental</th><th>Dépenses % du PB</th></tr></thead><tbody>{body}</tbody></table>"""
    r, a = F.comp_pair(d, "ytd")
    rr, ra = (ratios(r), ratios(a)) if r and a else ({}, {})
    msg = "Résultats des départements après-vente."
    if rr:
        msg = (f"Après-vente : <b>{kmoney(rr['apres_vente'])}</b> de profit brut depuis janvier ({pct(var_pct(rr['apres_vente'], ra['apres_vente']), 0, sign=True)} vs {y-1}), "
               f"<b>{pct(rr['absorption'], 0)}</b> des frais fixes de la concession couverts ({pts(rr['absorption'] - ra['absorption'], 1)}) ; "
               f"part de l'après-vente dans le profit brut total : {pct(rr['part_apres_vente'], 0)}.")
    return f"""
      <div class="eyebrow">Départements</div>
      <h1>Service, pièces et carrosserie</h1>
      {key(msg)}
      {blocks}
      <div class="note">Montants en k$. Dépenses : un écart <span class="pos">vert</span> veut dire des dépenses plus basses. Profit départemental = profit brut
      − dépenses du département (+ transferts entre départements à l'état GM). Absorption = profit brut service + pièces + carrosserie ÷ (dépenses
      totales − dépenses variables).</div>"""


def p_bt(F, d):
    y, m = F.y, F.m
    fr, fa = F.pair(d, "ytd")
    c, ca = F.tm(fr, "client"), F.tm(fa, "client")
    msg = f"Depuis janvier : <b>{num(c.get('bt'))}</b> BT client à <b>{money(c.get('tot_bt'))}</b> par BT (main-d'œuvre {money(c.get('mo_bt'))}, pièces {money(c.get('pc_bt'))})"
    t, _ = fd(c.get("tot_bt"), ca.get("tot_bt"), "$")
    if t:
        msg += f", {t} vs {y-1}"
    msg += "."
    notes = " ".join(escape(TYPE_NOTES[t_]) for t_ in types_for(fr))
    return f"""
      <div class="eyebrow">Bons de travail</div>
      <h1>Bons de travail par type : dollars et heures par BT</h1>
      {key(msg)}
      <div class="band-lab">Cumul {MOIS[1]}–{MOIS[m]} {y} <span>sous chaque valeur : écart vs {y-1}</span></div>
      {type_rows_table(F, d, "ytd")}
      <div class="band-lab">Mois {de(m)} {y} <span>vs {MOIS[m]} {y-1}</span></div>
      {type_rows_table(F, d, "month")}
      <div class="note">{notes} M-O et pièces = ventes ; PB / BT = profit brut M-O + pièces ÷ BT ; taux effectif = ventes de M-O ÷ heures vendues.</div>"""


def p_position(F, d):
    y, m = F.y, F.m
    specs = [("tot_bt", "Total / BT", "$"), ("mo_bt", "M-O / BT", "$"), ("pc_bt", "Pièces / BT", "$"),
             ("pb_bt", "PB / BT", "$"), ("h_bt", "Heures / BT", "h"), ("marge_mo", "Marge M-O", "%")]
    body = ""
    for typ in MAIN_TYPES:
        if not F.tm(F.flat(d, "ytd"), typ).get("bt"):
            continue
        body += f'<tr class="sec"><td colspan="6">{escape(TYPES[typ])}</td></tr>'
        g = F.tm(F.flat(GROUP, "ytd"), typ)
        for k, lab, f in specs:
            v = F.tm(F.flat(d, "ytd"), typ).get(k)
            rk, n, lo, hi = rank_of(F, d, typ, k)
            if v is None and k == "h_bt":
                continue
            gd = ""
            if v is not None and g.get(k):
                if f == "%":
                    gd = pts(v - g[k], 1)
                else:
                    gd = pct(v / g[k] - 1, 0, sign=True)
            body += (f'<tr><td class="lab">{escape(lab)}</td><td class="strong">{fv(v, f)}</td><td>{fv(g.get(k), f)}</td>'
                     f'<td>{gd}</td><td>{f"{rk} / {n}" if rk else "—"}</td><td>{fv(lo, f)} – {fv(hi, f)}</td></tr>')
    return f"""
      <div class="eyebrow">Positionnement</div>
      <h1>{escape(DEALERS[d])} dans le Groupe</h1>
      {key(f"Chaque indicateur du cumul {y} comparé au Groupe (calculé à partir des sommes des {len(F.dealers)} concessions) et rang parmi les concessions "
           "(1 = la plus élevée). Les écarts de marque, de clientèle et de mix des BT expliquent une partie des différences : c'est un repère, pas une cible.")}
      <table class="t num fo"><thead><tr><th class="lab">Indicateur</th><th>{escape(DEALER_SHORT[d])}</th><th>Groupe</th><th>Écart au Groupe</th>
      <th>Rang</th><th>Plage du Groupe</th></tr></thead><tbody>{body}</tbody></table>
      <div class="note">Heures / BT : seulement les concessions dont les fichiers donnent les heures (Volkswagen, Hyundai).</div>"""


def p_mensuel(F, d):
    y, m = F.y, F.m
    months = list(range(1, m + 1))
    head = "".join(f"<th>{escape(MOIS[i][:4] + '.' if len(MOIS[i]) > 4 else MOIS[i])}</th>" for i in months) + '<th class="sep">Cumul</th>'
    has_h = any(t.get("h") for t in (F.flat(d, "ytd") or {"types": {}})["types"].values())
    specs = [("bt", "BT", "n"), ("mo_bt", "M-O / BT", "$"), ("tot_bt", "Total / BT", "$")] + ([("h_bt", "Heures / BT", "h")] if has_h else [])
    body = ""
    for typ in types_for(F.flat(d, "ytd")):
        if not F.tm(F.flat(d, "ytd"), typ).get("bt"):
            continue
        body += f'<tr class="sec"><td colspan="{len(months) + 2}">{escape(TYPES[typ])}</td></tr>'
        for k, lab, f in specs:
            for yy, cls in ((y, ""), (y - 1, "muted")):
                tds = ""
                for i in months:
                    fl = F.av.get(d, pkey(yy, i), "month")
                    v = F.tm(fl, typ).get(k) if fl else None
                    tds += f'<td class="{cls}">{fv(v, "h" if f == "h" else "n") if v is not None else "—"}</td>'
                fy = F.av.get(d, pkey(yy, m), "ytd")
                vy = F.tm(fy, typ).get(k) if fy else None
                tds += f'<td class="sep {cls} {"strong" if not cls else ""}">{fv(vy, "h" if f == "h" else "n") if vy is not None else "—"}</td>'
                body += f'<tr><td class="lab {cls}">{escape(lab)} {yy}</td>{tds}</tr>'
    return f"""
      <div class="eyebrow">Mois par mois</div>
      <h1>Détail mensuel {y} comparé à {y-1}</h1>
      {key(f"Chaque mois de {y} (noir) au-dessus du même mois de {y-1} (gris). Dollars par BT en $. Les pointes de BT client d'avril–mai et "
           "d'octobre–novembre coïncident avec la saison des changements de pneus (beaucoup de petits BT, moins de dollars par BT).")}
      <table class="t num trend fo small"><thead><tr><th class="lab">Indicateur</th>{head}</tr></thead><tbody>{body}</tbody></table>"""


def p_tendances(F, d):
    y, m = F.y, F.m
    labels12 = month_labels(F.P, 12)
    lab_short = [l for _, l in labels12]
    specs = [("client", "tot_bt", "$", "Total par BT client"), ("client", "bt", "n", "Nombre de BT client"),
             ("garantie", "tot_bt", "$", "Total par BT garantie"), ("interne", "tot_bt", "$", "Total par BT interne")]
    has_h = any(t.get("h") for t in (F.flat(d, "ytd") or {"types": {}})["types"].values())
    if has_h:
        specs += [("client", "h_bt", "h", "Heures vendues par BT client"), ("client", "elr", "$", "Taux effectif client")]
    else:
        specs += [("client", "mo_bt", "$", "Main-d'œuvre par BT client"), ("client", "pc_bt", "$", "Pièces par BT client")]
    blocks = ""
    for typ, k, f, title in specs:
        vals, aps = [], []
        for p, _ in labels12:
            fl = F.av.get(d, p, "month")
            vals.append(F.tm(fl, typ).get(k) if fl else None)
            fa = F.av.get(d, prior_year(p), "month")
            aps.append(F.tm(fa, typ).get(k) if fa else None)
        blocks += f'<div class="sm"><div class="smh">{escape(title)}</div>{bars_ap(vals, aps, lab_short, f)}</div>'
    # 24 mois vs Groupe
    labels24 = month_labels(F.P, 24)
    ser_d, ser_g = [], []
    for p, _ in labels24:
        fl = F.av.get(d, p, "month")
        ser_d.append(F.tm(fl, "client").get("tot_bt") if fl else None)
        if all(F.av.get(x, p, "month") for x in F.dealers):
            ser_g.append(F.tm(F.av.group(F.dealers, p, "month"), "client").get("tot_bt"))
        else:
            ser_g.append(None)
    long = lines_chart([(d, ser_d), (GROUP, ser_g)], "$", [l for _, l in labels24], width=660, height=132)
    return f"""
      <div class="eyebrow">Tendances</div>
      <h1>Tendances : 12 derniers mois et 24 mois</h1>
      {key(f"Barres bleues : 12 derniers mois ; trait gris : même mois un an plus tôt. En bas : total par BT client de {escape(DEALER_SHORT[d])} "
           "comparé au Groupe sur 24 mois.")}
      <div class="smgrid">{blocks}</div>
      <div class="chart-title">Total par BT client — {escape(DEALER_SHORT[d])} et Groupe, 24 mois</div>
      <div class="legend"><span class="lgd"><span class="sw" style="background:{DEALER_COLOR[d]}"></span>{escape(DEALER_SHORT[d])}</span>
      <span class="lgd"><span class="sw" style="background:{INK}"></span>Groupe (mois où les 5 concessions ont des données)</span></div>
      <div class="chart">{long}</div>"""


def p_atelier(F, d):
    y, m = F.y, F.m
    fr = F.flat(d, "ytd")
    at = atelier_metrics(fr)
    if at.get("disp"):
        body = ""
        for mode, lab in (("ytd", f"Cumul {y}"), ("month", f"{MOIS[m].capitalize()} {y}")):
            r, a = atelier_metrics(F.flat(d, mode)), atelier_metrics(F.flat(d, mode, "ap"))
            body += (f'<tr><td class="lab">{escape(lab)}</td>' + cell(r["disp"], a["disp"], "n") + cell(r["pointees"], a["pointees"], "n")
                     + cell(r["vendues"], a["vendues"], "n") + cell(r["productivite"], a["productivite"], "%")
                     + cell(r["efficacite"], a["efficacite"], "%") + cell(r["h_tech"], a["h_tech"], "n") + "</tr>")
        tb = ""
        for mode, lab in (("ytd", f"Cumul {y}"), ("month", f"{MOIS[m].capitalize()} {y}")):
            fr_, fa_ = F.flat(d, mode), F.flat(d, mode, "ap")
            tb += f'<tr class="sec"><td colspan="7">{escape(lab)}</td></tr>'
            for typ in MAIN_TYPES:
                r, a = F.tm(fr_, typ), F.tm(fa_, typ)
                if not r.get("h"):
                    continue
                tb += (f'<tr><td class="lab">{escape(TYPES[typ])}</td>' + cell(r.get("h"), a.get("h"), "n") + cell(r.get("bt"), a.get("bt"), "n")
                       + cell(r.get("h_bt"), a.get("h_bt"), "h") + cell(r.get("mo_v"), a.get("mo_v"), "k") + cell(r.get("elr"), a.get("elr"), "$") + "</tr>")
        cr = F.tm(fr, "client")
        msg = (f"Depuis janvier : <b>{num(at['vendues'])} h</b> vendues sur {num(at['disp'])} h disponibles — productivité <b>{pct(at['productivite'], 0)}</b>, "
               f"efficacité <b>{pct(at['efficacite'], 0)}</b> ; {num(cr.get('h_bt'), 2)} h par BT client à {money(cr.get('elr'))} l'heure.")
        content = f"""<div class="band-lab">Atelier mécanique <span>écart vs {y-1}</span></div>
          <table class="t num fo small"><thead><tr><th class="lab">Période</th><th>Heures disponibles</th><th>Heures pointées</th><th>Heures vendues</th>
          <th>Productivité</th><th>Efficacité</th><th>Heures vendues / tech.</th></tr></thead><tbody>{body}</tbody></table>
          <div class="band-lab">Heures vendues et taux effectif par type <span>écart vs {y-1}</span></div>
          <table class="t num fo"><thead><tr><th class="lab">Type</th><th>Heures vendues</th><th>BT</th><th>Heures / BT</th><th>Ventes M-O</th><th>Taux effectif</th></tr></thead>
          <tbody>{tb}</tbody></table>
          <div class="note">Productivité = heures pointées sur les BT ÷ heures disponibles ; efficacité = heures vendues ÷ heures pointées (au-dessus de 100 % :
          les techniciens battent le temps facturé). Taux effectif = ventes de main-d'œuvre ÷ heures vendues. Source : état {"Volkswagen" if d == "vw" else "Hyundai"} Canada, Page 6.</div>"""
    else:
        ta = at.get("taux_affiche") or {}
        est = ""
        if ta.get("client"):
            rows = ""
            for typ in MAIN_TYPES:
                r = F.tm(fr, typ)
                rate = ta.get(typ)
                if r.get("mo_bt") and rate:
                    rows += (f'<tr><td class="lab">{escape(TYPES[typ])}</td><td>{money(rate)}</td><td>{money(r["mo_bt"])}</td>'
                             f'<td>{num(div(r["mo_bt"], rate), 2)}</td></tr>')
            est = f"""<div class="band-lab">Heures estimées au taux affiché <span>taux horaires affichés de l'état {"BMW Canada (page 10)" if d == "bmw" else "GM (Page 4)"}</span></div>
              <table class="t num fo" style="width:75%"><thead><tr><th class="lab">Type</th><th>Taux affiché</th><th>M-O par BT {y}</th><th>≈ heures au taux affiché</th></tr></thead>
              <tbody>{rows}</tbody></table>
              <div class="note">Estimation seulement : main-d'œuvre par BT ÷ taux affiché ; les escomptes et le temps offert la font baisser.</div>"""
        if not est:
            return None
        cr = F.tm(fr, "client")
        msg = (f"Taux affiché client <b>{money(ta.get('client'))}</b> ; main-d'œuvre de <b>{money(cr.get('mo_bt'))}</b> par BT client, "
               f"soit environ <b>{num(div(cr.get('mo_bt'), ta.get('client')), 2)} h</b> par BT au taux affiché.")
        elr = at.get("taux_effectif_declare")
        if elr:
            mo_all = sum((t.get("mo_v") or 0) for k_, t in fr["types"].items())
            bt_all = sum((t.get("bt") or 0) for k_, t in fr["types"].items())
            h_est = div(mo_all, elr)
            msg += (f"<br>Taux de main-d'œuvre en vigueur déclaré à BMW Canada : <b>{num(elr, 2)} $</b> l'heure ; à ce taux, la main-d'œuvre "
                    f"de {kmoney(mo_all)} depuis janvier représente environ <b>{num(h_est)} h</b> vendues, soit {num(div(h_est, bt_all), 2)} h par BT.")
            tech = at.get("techs_declares") or {}
            est += (f'<div class="note">Taux de main-d\'œuvre en vigueur : état BMW Canada, page 10 (fin {de(m)} {y}). Heures estimées = main-d\'œuvre de tous '
                    f'les types ÷ ce taux (l\'état ne donne pas les heures vendues).'
                    + (f" Techniciens déclarés : {num(tech.get('mecanique'))} + {num(tech.get('apprentis'))} apprentis." if tech.get("mecanique") else "")
                    + "</div>")
        content = est
        return f"""
      <div class="eyebrow">Atelier</div>
      <h1>Atelier : taux horaires affichés</h1>
      {key(msg)}
      {content}"""
    return f"""
      <div class="eyebrow">Atelier</div>
      <h1>Atelier : heures vendues et productivité</h1>
      {key(msg)}
      {content}"""


def p_pieces_carrosserie(F, d):
    y, m = F.y, F.m
    fr, fa = F.flat(d, "ytd"), F.flat(d, "ytd", "ap")
    parts = ""
    cr = {c: (v, pb) for c, v, pb in fo.pieces_channels(fr)}
    ca = {c: (v, pb) for c, v, pb in fo.pieces_channels(fa)}
    tv, tpb = fo.pieces_total(fr)
    av_, apb = fo.pieces_total(fa)
    body = ""
    for c in fo.PC_CHANNELS:
        if c not in cr or not cr[c][0]:
            continue
        v, pb = cr[c]
        va, pba = ca.get(c) or (None, None)
        body += (f'<tr><td class="lab">{escape(fo.PC_CHANNELS[c])}</td>' + cell(v, va, "k") + f'<td><div>{pct(div(v, tv), 0)}</div><div class="dsub">&nbsp;</div></td>'
                 + cell(pb, pba, "k") + cell(div(pb, v), div(pba, va), "%") + "</tr>")
    body += (f'<tr class="strong"><td class="lab">Total du département Pièces</td>' + cell(tv, av_, "k", True) + '<td class="strong"><div>100 %</div><div class="dsub">&nbsp;</div></td>'
             + cell(tpb, apb, "k", True) + cell(div(tpb, tv), div(apb, av_), "%", True) + "</tr>")
    parts += f"""<div class="band-lab">Pièces par canal <span>cumul {y} · écart vs {y-1}</span></div>
      <table class="t num fo small"><thead><tr><th class="lab">Canal</th><th>Ventes</th><th>Part des ventes</th><th>Profit brut</th><th>Marge</th></tr></thead>
      <tbody>{body}</tbody></table>"""
    rr = []
    for typ in types_for(fr):
        a_, b_ = F.tm(fr, typ).get("pc_mo"), F.tm(fa, typ).get("pc_mo")
        if a_ is not None:
            rr.append(f"{escape(TYPES[typ][0].lower() + TYPES[typ][1:])} <b>{num(a_, 2)} $</b>" + (f" ({y-1} : {num(b_, 2)} $)" if b_ is not None else ""))
    if rr:
        parts += f'<p class="note" style="font-size:8.6pt;color:var(--ink2)">Pièces vendues par dollar de main-d\'œuvre, cumul {y} : ' + " ; ".join(rr) + ".</p>"
    car = (fr or {}).get("carrosserie") or {}
    tot = car.get("total") or {}
    if tot.get("v") or tot.get("pb"):
        cta = ((fa or {}).get("carrosserie") or {}).get("total") or {}
        rows = ""
        for k, lab in (("client", "Main-d'œuvre client"), ("garantie", "Garantie"), ("interne", "Interne"), ("concessions", "Autres concessions"),
                       ("esthetique", "Esthétique"), ("peinture", "Peinture et matériel"), ("sous_traitance", "Sous-traitance")):
            x = car.get(k) or {}
            xa = ((fa or {}).get("carrosserie") or {}).get(k) or {}
            if x.get("v") or x.get("pb"):
                rows += (f'<tr><td class="lab">{escape(lab)}</td>' + cell(x.get("v"), xa.get("v"), "k") + cell(x.get("pb"), xa.get("pb"), "k")
                         + cell(div(x.get("pb"), x.get("v")), div(xa.get("pb"), xa.get("v")), "%") + "</tr>")
        rows += (f'<tr class="strong"><td class="lab">Total carrosserie</td>' + cell(tot.get("v"), cta.get("v"), "k", True) + cell(tot.get("pb"), cta.get("pb"), "k", True)
                 + cell(div(tot.get("pb"), tot.get("v")), div(cta.get("pb"), cta.get("v")), "%", True) + "</tr>")
        parts += f"""<div class="band-lab">Carrosserie <span>cumul {y} · écart vs {y-1}</span></div>
          <table class="t num fo small"><thead><tr><th class="lab">Poste</th><th>Ventes</th><th>Profit brut</th><th>Marge</th></tr></thead><tbody>{rows}</tbody></table>"""
    msg = (f"Pièces : <b>{kmoney(tv)}</b> de ventes depuis janvier ({pct(var_pct(tv, av_), 0, sign=True) if av_ else 'n/d'} vs {y-1}), marge "
           f"<b>{pct(div(tpb, tv), 1)}</b>" + (f" ; carrosserie : {kmoney(tot.get('v'))} de ventes, marge {pct(div(tot.get('pb'), tot.get('v')), 1)}." if tot.get("v") else "."))
    return f"""
      <div class="eyebrow">Pièces et carrosserie</div>
      <h1>Pièces et carrosserie</h1>
      {key(msg)}
      {parts}
      <div class="note">Montants en k$. Pièces sur BT client / garantie / interne{" / entretien BMW" if d == "bmw" else ""} : pièces facturées sur ces bons de travail ; le total comprend aussi
      les ajustements (escomptes, allocations d'achat, rectifications d'inventaire).</div>"""


def p_methode(F, d):
    y, m = F.y, F.m
    src = F.s.source_format(d, F.P)
    ap = F.av.ap_source(d, F.P, "ytd")
    has_h = any(t.get("h") for t in (F.flat(d, "ytd") or {"types": {}})["types"].values())
    hs = (F.av.native(d, F.P, "ytd") or {}).get("heures_source") == "etat"
    lim = {
        "stm": "Service mobile (compte 460D) compté dans les BT client ; ses pièces sont inscrites avec celles des BT client. Le compte 460D n'est utilisé "
               "qu'à partir de l'état d'août 2026 (cumul retraité) : le total client se compare d'une année à l'autre, pas le détail « mobile ». "
               "L'inspection des véhicules neufs (464) est comptée dans les BT internes.",
        "hawks": "L'inspection des véhicules neufs (compte 464) est comptée dans les BT internes. Carrosserie : seuls les BT de peinture et les BT internes sont comptés à l'état GM.",
        "hyundai": "Les états de septembre et octobre 2025 (« FFS Hyundai F 09-2026 » et « 10-2026 ») reprennent les BT et heures d'août 2026 : retirés pour ces deux mois. "
                   "Août 2025 vient du Réalisé (pas d'état Hyundai Canada) : pas d'heures ce mois-là.",
        "vw": "Le Réalisé VW reste la source retenue (règle du 25 septembre) ; ses heures viennent de l'état Volkswagen Canada du même mois quand les BT concordent (± 3 %).",
        "bmw": "Types de BT de l'état BMW Canada (pages 8 et 9) : client, entretien payé par BMW (BMW Service Inclus), garantie, interne, "
               "programme SPA (esthétique). Budget des BT garantie et interne retiré (définition du Réalisé différente). Pas de carrosserie à la concession.",
    }[d]
    return f"""
      <div class="eyebrow">Méthode</div>
      <h1>Sources et définitions</h1>
      <h2>Sources de {escape(DEALERS[d])}</h2>
      <ul class="retenir compact">
        <li><b>Fichier d'{MOIS[m]} {y}</b> : {escape(SOURCE_LABELS.get(src, '—'))}.</li>
        {"<li><b>Types de BT</b> : état BMW Canada (pages 8 à 10), " + MOIS[m] + " " + str(y) + " et " + str(y - 1) + ".</li>" if (F.av.native(d, F.P, "ytd") or {}).get("source_types") == "etat_bmw" else ""}
        <li><b>An passé</b> : {"colonnes « année précédente » du Réalisé" if ap == "natif" else ("fichiers " + str(y-1) + " de la concession" if ap else "non disponible")}.</li>
        {("<li><b>Heures vendues</b> : état " + ("Volkswagen Canada" if d == "vw" else "Hyundai Canada") + (" (repris dans le Réalisé)" if hs else "") + ".</li>") if has_h else ""}
        <li><b>À savoir</b> : {escape(lim)}</li>
      </ul>
      <h2>Définitions</h2>
      <dl class="defs">
        <dt>Bon de travail (BT)</dt><dd>Compté par type : un BT qui a des lignes client et garantie compte dans les deux types. Client : payé par le client
        (atelier, service rapide, contrats, prépayé). Garantie : remboursé par le constructeur. Interne : facturé aux autres départements.</dd>
        <dt>Main-d'œuvre, pièces, total, profit brut par BT</dt><dd>Ventes de M-O, pièces facturées sur ces BT, ou profit brut M-O + pièces, ÷ BT du type.</dd>
        <dt>Heures par BT, taux effectif</dt><dd>Heures vendues ÷ BT ; ventes de M-O ÷ heures vendues.</dd>
        <dt>Productivité, efficacité</dt><dd>Heures pointées ÷ heures disponibles ; heures vendues ÷ heures pointées.</dd>
        <dt>Groupe</dt><dd>Calculé à partir des sommes des concessions (jamais une moyenne de ratios).</dd>
      </dl>
      <p class="note">Rapport tiré du tableau de bord KPI (data.json, lu par src/apres_vente.py). Même méthode que le rapport « Opérations fixes » du Groupe.</p>"""


def build_book(s, P, d):
    rc.setup(s, P)
    rc.FOOTER_LABEL = f"{DEALERS[d]} · Opérations fixes · {rc.PERIOD_LABEL}"
    F = FO(s, P)
    bk = Book()
    bk.add_cover(p_cover(F, d))
    bk.add(p_essentiel(F, d))
    bk.add(p_departements(F, d))
    bk.add(p_bt(F, d))
    bk.add(p_position(F, d))
    import rapport_composite as rcomp   # comparaison au composite du constructeur
    for pg in rcomp.pages_fo_concession(s, P, d):
        bk.add(pg)
    bk.add(p_mensuel(F, d))
    bk.add(p_tendances(F, d))
    pa = p_atelier(F, d)
    if pa:
        bk.add(pa)
    bk.add(p_pieces_carrosserie(F, d))
    bk.add(p_methode(F, d))
    return bk


def generate(s, P, outdir, dealers=None, keep_html=False):
    os.makedirs(outdir, exist_ok=True)
    av = fo.AVStore(s)
    res = []
    for d in (dealers or [x for x in DEALERS if av.get(x, P, "ytd")]):
        bk = build_book(s, P, d)
        html = wrap_html(f"{DEALERS[d]} — Opérations fixes {rc.PERIOD_LABEL}", bk.pages)
        rc.FOOTER_LABEL = ""
        fp = os.path.join(outdir, f"Rapport_Operations_fixes_{FILE_NAMES[d]}_{P}.pdf")
        hp = os.path.splitext(fp)[0] + ".html"
        with open(hp, "w", encoding="utf-8") as f:
            f.write(html)
        over = to_pdf(hp, fp)
        if not keep_html:
            os.remove(hp)
        res.append((fp, len(bk.pages), over))
    return res


def main():
    ap = argparse.ArgumentParser(description="Rapports Opérations fixes par concession — Groupe Automax")
    ap.add_argument("--mois")
    ap.add_argument("--data", default=os.path.join(HERE, "data.json"))
    ap.add_argument("--budget", default=os.path.join(HERE, "budgets.csv"))
    ap.add_argument("--concession", choices=list(DEALERS))
    ap.add_argument("--sortie", default=HERE)
    a = ap.parse_args()
    s = Store(a.data, a.budget)
    av = fo.AVStore(s)
    if a.mois:
        P = a.mois
    else:
        common = set.intersection(*[set(s.periods(d)) for d in DEALERS])
        P = max(p for p in common if all(av.get(d, p, "ytd") for d in DEALERS))
    for fp, n, over in generate(s, P, a.sortie, [a.concession] if a.concession else None):
        print(f"PDF : {fp} ({n} pages)" + (f" — ATTENTION débordement {over}" if over else ""))


if __name__ == "__main__":
    main()
