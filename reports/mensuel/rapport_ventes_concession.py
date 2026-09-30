#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rapport « Ventes de véhicules » par concession — Groupe Automax.

Même principe que le rapport « Opérations fixes » de la concession : neufs et
usagés (unités, profit véhicule et F&I par unité, gros, ventes nettes, profit
du département), mix des modèles, F&I par produit, frais de vente,
positionnement dans le Groupe, comparaison au composite du constructeur,
détail mois par mois et tendances.

    python rapport_ventes_concession.py --data ../../data/data.json --mois 2026-08 --sortie sortie
    python rapport_ventes_concession.py --data ../../data/data.json --mois 2026-08 --concession vw
"""
import argparse
import os
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import rapport_commun as rc
from rapport_commun import key, Book, wrap_html, to_pdf, LOGO_DARK
from kpi_data import Store, DEALERS, DEALER_SHORT, MOIS, pkey, prior_year, label_period
from kpi_analyse import money, kmoney, num, pct, pts, var_pct, de
from kpi_svg import INK
from rapport_apres_vente import lines_chart, month_labels, DEALER_COLOR
from rapport_apres_vente_concession import bars_ap
import kpi_ventes as kv
from kpi_ventes import GROUP, metrics, both
from rapport_ventes import VS, DLAB, DSHORT, SOURCE_LABELS, fv, fdx, findings, dept_tiles

FILE_NAMES = {"bmw": "BMW_Sherbrooke", "vw": "Volkswagen", "stm": "STM", "hyundai": "Hyundai", "hawks": "HAWKS"}


def _td(v, f, cls=""):
    return f'<td class="{cls}">{fv(v, f)}</td>'


def _gap(r, a, f, sens=1):
    t, c = fdx(r, a, f, sens)
    return f'<td class="{c}">{t or "—"}</td>'


# ------------------------------------------------------------------ pages
def p_cover(S, d):
    y, m = S.y, S.m
    rn, an = S.m2(d, "neuf")
    ru, au = S.m2(d, "usage")
    r, a = S.pair(d)
    br, ba = both(r), both(a)

    def dtxt(x, b, f="n"):
        t, _ = fdx(x, b, f)
        return f"{t} vs {y-1}" if t else f"{y-1} : n/d"
    return f"""
      <div class="logo cv-logo">{LOGO_DARK}</div>
      <div class="cv-mid">
        <div class="cv-kicker">Ventes de véhicules · {escape(label_period(S.P))}</div>
        <div class="cv-title cv-dealer">{escape(DEALERS[d])}</div>
        <div class="cv-sub">Véhicules neufs et usagés : unités, profit véhicule et F&I par unité, gros, encan et export, F&I par produit, frais de
        vente, profit des départements, mix des modèles, position dans le Groupe et tendances. Mois {de(m)} et cumul {MOIS[1]}–{MOIS[m]} {y},
        comparés à {y-1}.</div>
        <div class="cv-kpis">
          <div><div class="cv-kl">Véhicules neufs {y}</div><div class="cv-kv">{num(rn.get('u'))}</div><div class="cv-kd">{escape(dtxt(rn.get('u'), an.get('u')))}</div></div>
          <div><div class="cv-kl">Véhicules usagés {y}</div><div class="cv-kv">{num(ru.get('u'))}</div><div class="cv-kd">{escape(dtxt(ru.get('u'), au.get('u')))}</div></div>
          <div><div class="cv-kl">Profit + F&I par unité</div><div class="cv-kv">{money(br.get('tot_u'))}</div><div class="cv-kd">{escape(dtxt(br.get('tot_u'), ba.get('tot_u'), '$'))}</div></div>
        </div>
      </div>
      <div class="cv-foot">
        <div>Une concession du Groupe Automax</div>
        <div>Préparé le {rc.PREPARED} à partir du tableau de bord KPI · Source d'{MOIS[m]} : {escape(SOURCE_LABELS.get(S.s.source_format(d, S.P), '—'))} · Non audité</div>
        <div class="cv-conf">Confidentiel — usage interne — direction seulement</div>
      </div>"""


def p_essentiel(S, d):
    y, m = S.y, S.m
    return f"""
      <div class="eyebrow">Sommaire</div>
      <h1>{escape(DEALERS[d])} : l'essentiel des ventes</h1>
      {key(f"Cumul {MOIS[1]}–{MOIS[m]} {y} comparé à la même période {y-1}. Unités au détail (neufs : avec démos et flottes) ; profit véhicule "
           "et F&I divisés par ces unités ; gros, encan et export à part.")}
      <div class="band-lab">Véhicules neufs <span>cumul {y}</span></div>
      <div class="tiles">{dept_tiles(S, d, 'neuf')}</div>
      <div class="band-lab">Véhicules usagés <span>cumul {y}</span></div>
      <div class="tiles">{dept_tiles(S, d, 'usage')}</div>
      <h2>Ce qu'il faut retenir</h2>
      <ul class="retenir">{''.join(f'<li>{t}</li>' for t in findings(S, d))}</ul>"""


def dept_rows(suf):
    rows = [("u", "Unités au détail", "n", 1)]
    if suf == "neuf":
        rows.append(("u_fl", "  dont flottes", "n", 0))
    rows += [("ventes", "Ventes nettes du département", "k", 1), ("pbv", "Profit véhicule au détail", "k", 1),
             ("pbv_u", "  par unité", "$", 1), ("fi", "F&I", "k", 1), ("fi_u", "  par unité", "$", 1),
             ("tot_u", "Profit + F&I par unité", "$", 1), ("gros", "Gros, encan, export et autres", "k", 1)]
    if suf == "usage":
        rows += [("gros_ligne_u", "  unités vendues en gros", "n", 0), ("gros_pb_u", "  profit par unité en gros", "$", 1)]
    rows.append(("pb", "Profit brut du département", "k", 1))
    return rows


def p_dept(S, d, suf):
    y, m = S.y, S.m
    rm, am = S.m2(d, suf, "month")
    ry, ay = S.m2(d, suf, "ytd")
    bv = S.budget(d, "ytd")
    by = metrics(bv[suf]) if bv else {}
    has_b = bool(by.get("pb"))
    body = ""
    for k, lab, f, sens in dept_rows(suf):
        if all(not x.get(k) for x in (rm, ry, am, ay)):
            continue      # ligne vide ou à 0 partout
        sub = lab.startswith("  ")
        strong = k in ("tot_u", "pb")
        tds = (_td(rm.get(k), f) + _td(am.get(k), f, "muted") + _gap(rm.get(k), am.get(k), f, sens)
               + _td(ry.get(k), f, "sep") + _td(ay.get(k), f, "muted") + _gap(ry.get(k), ay.get(k), f, sens))
        if has_b:
            tds += _td(by.get(k), f, "sep muted") + _gap(ry.get(k), by.get(k), f, sens)
        body += f'<tr class="{"sub" if sub else ("strong" if strong else "")}"><td class="lab">{escape(lab.strip())}</td>{tds}</tr>'
    bh = '<th colspan="2" class="sep">Budget cumul</th>' if has_b else ""
    bh2 = '<th class="sep">Budget</th><th>Écart</th>' if has_b else ""
    head = (f'<thead><tr><th rowspan="2" class="lab">{DLAB[suf]}</th><th colspan="3">{MOIS[m].capitalize()} {y}</th>'
            f'<th colspan="3" class="sep">Cumul {MOIS[1]}–{MOIS[m]} {y}</th>{bh}</tr>'
            f'<tr><th>{y}</th><th>{y-1}</th><th>Écart</th><th class="sep">{y}</th><th>{y-1}</th><th>Écart</th>{bh2}</tr></thead>')
    # mix des modèles
    mix, mixa = ry.get("mix") or {}, ay.get("mix") or {}
    mrows = ""
    for name, v in mix.items():
        if not v["u"]:
            continue
        va = mixa.get(name) or {}
        pu = v["pb"] / v["u"]
        pa = va["pb"] / va["u"] if va.get("u") else None
        mrows += (f'<tr><td class="lab">{escape(name)}</td>{_td(v["u"], "n")}{_td(va.get("u"), "n", "muted")}{_gap(v["u"], va.get("u"), "n")}'
                  f'{_td(pu, "$", "sep")}{_td(pa, "$", "muted")}{_gap(pu, pa, "$")}</tr>')
    mix_tbl = (f'<div class="band-lab" style="margin-top:22px">Par ligne de produits <span>cumul {y} · profit du véhicule au détail (sans F&I)</span></div>'
               f'<table class="t num fo comp"><thead><tr><th class="lab">Ligne</th><th>Unités {y}</th><th>{y-1}</th><th>Écart</th>'
               f'<th class="sep">Profit / u {y}</th><th>{y-1}</th><th>Écart</th></tr></thead><tbody>{mrows}</tbody></table>') if mrows else ""
    msg = (f"Depuis janvier : <b>{num(ry.get('u'))}</b> {DSHORT[suf]} au détail ({pct(var_pct(ry.get('u'), ay.get('u')), 0, sign=True)} vs {y-1}) et "
           f"<b>{money(ry.get('tot_u'))}</b> de profit + F&I par unité ({money((ry.get('tot_u') or 0) - (ay.get('tot_u') or 0), sign=True) if ay.get('tot_u') is not None else 'n/d'}).")
    note = ("Neufs : unités au détail avec démos et flottes ; profit véhicule des neufs avec démos et flottes. " if suf == "neuf" else
            "Usagés : unités au détail ; ventes en gros, à l'encan et à l'export à part. ")
    return f"""
      <div class="eyebrow">{DLAB[suf]}</div>
      <h1>{DLAB[suf]} : volumes et profit</h1>
      {key(msg)}
      <table class="t num fo comp{' dep' if has_b else ''}">{head}<tbody>{body}</tbody></table>
      {mix_tbl}
      <div class="note">{note}Gros, encan, export et autres = profit brut du département − profit véhicule − F&I.{'' if S.V.same_format(d, S.P) else f' An passé : fichier {y-1} d’un autre format — lignes de modèles comparées quand elles existent dans les deux fichiers.'}</div>"""


def _two_dept_table(S, d, rows, head_lab):
    r = {suf: S.m2(d, suf) for suf in ("neuf", "usage")}
    body = ""
    for k, lab, f, sens in rows:
        if all(not r[suf][i].get(k) for suf in r for i in (0, 1)):
            continue      # ligne vide ou à 0 partout
        sub = lab.startswith("  ")
        tds = ""
        for i, suf in enumerate(("neuf", "usage")):
            x, a = r[suf]
            tds += _td(x.get(k), f, "sep" if i else "") + _td(a.get(k), f, "muted") + _gap(x.get(k), a.get(k), f, sens)
        body += f'<tr class="{"sub" if sub else ("strong" if k in ("fi", "profit") else "")}"><td class="lab">{escape(lab.strip())}</td>{tds}</tr>'
    y = S.y
    return (f'<table class="t num fo comp"><thead><tr><th rowspan="2" class="lab">{head_lab}</th><th colspan="3">Véhicules neufs</th>'
            f'<th colspan="3" class="sep">Véhicules usagés</th></tr><tr><th>{y}</th><th>{y-1}</th><th>Écart</th>'
            f'<th class="sep">{y}</th><th>{y-1}</th><th>Écart</th></tr></thead><tbody>{body}</tbody></table>')


FI_ROWS = [("fi", "F&I (k$)", "k", 1), ("fi_u", "  par unité", "$", 1), ("fi_fin", "Financement (k$)", "k", 1),
           ("fi_prot", "Protections (k$)", "k", 1), ("fi_aut", "Autres produits (k$)", "k", 1),
           ("comm_fi", "Commissions F&I (k$)", "k", -1), ("comm_fi_pct", "  en % du F&I", "%", -1)]
FRAIS_ROWS = [("comm_vend", "Commissions des vendeurs (k$)", "k", -1), ("comm_u", "  par unité", "$", -1),
              ("comm_pct_pbv", "  en % du profit véhicule", "%", -1), ("pub_u", "Publicité nette par unité", "$", -1),
              ("int_u", "Intérêts sur stocks nets par unité", "$", -1), ("prep_u", "Préparation et livraison par unité", "$", -1),
              ("pers", "Frais de personnel (k$)", "k", -1), ("dep", "Dépenses du département (k$)", "k", -1),
              ("dep_pct_pb", "  en % du profit brut", "%", -1), ("ar", "Autres revenus du département (k$)", "k", 1),
              ("profit", "Profit du département (k$)", "k", 1)]


def p_fi(S, d):
    y, m = S.y, S.m
    rn, an = S.m2(d, "neuf")
    ru, au = S.m2(d, "usage")
    msg = (f"F&I par unité depuis janvier : <b>{money(rn.get('fi_u'))}</b> sur les neufs et <b>{money(ru.get('fi_u'))}</b> sur les usagés "
           f"({y-1} : {money(an.get('fi_u'))} et {money(au.get('fi_u'))}).")
    return f"""
      <div class="eyebrow">F&I</div>
      <h1>Financement et assurances (F&I)</h1>
      {key(msg)}
      {_two_dept_table(S, d, FI_ROWS, f"Cumul {MOIS[1]}–{MOIS[m]}")}
      <div class="note">F&I = revenus du bureau commercial. Détail par produit : Réalisé du Groupe (« Rev. Finances », « Rev. Protections », « Rev. Autres ») ;
      les états des constructeurs ne le détaillent pas. Commissions F&I : directeurs commerciaux (état Hyundai : salaires et commissions du bureau
      commercial ; non détaillées à l'état GM). Vert = coût plus bas.</div>"""


def p_frais(S, d):
    y, m = S.y, S.m
    rn, _ = S.m2(d, "neuf")
    ru, _ = S.m2(d, "usage")
    msg = (f"Commissions des vendeurs depuis janvier : <b>{money(rn.get('comm_u'))}</b> par unité neuve et <b>{money(ru.get('comm_u'))}</b> par unité usagée ; "
           f"profit des départements : <b>{kmoney(rn.get('profit'))}</b> (neufs) et <b>{kmoney(ru.get('profit'))}</b> (usagés).")
    fmt_note = "" if S.V.same_format(d, S.P) else (f" An passé : fichier {y-1} d’un autre format — commissions, publicité et intérêts comparés "
                                                     "(mêmes montants dans les deux formats) ; dépenses totales et profit du département non comparés.")
    return f"""
      <div class="eyebrow">Frais de vente</div>
      <h1>Frais de vente et profit des départements</h1>
      {key(msg)}
      {_two_dept_table(S, d, FRAIS_ROWS, f"Cumul {MOIS[1]}–{MOIS[m]}")}
      <div class="note">Par unité au détail. Publicité nette des ristournes du constructeur ; intérêts sur stocks nets des crédits du constructeur (négatif =
      le crédit dépasse l'intérêt) ; préparation et livraison : livraison, préparation, service gratuit, travaux gracieux et entretien des stocks
      (net des crédits). Dépenses et profit du département selon la répartition des frais du fichier source.{fmt_note}</div>"""


POS_SPECS = [("neuf", "u_var", "Unités neuves : écart vs l'an passé", "%p"), ("neuf", "pbv_u", "Neufs : profit véhicule / u", "$"),
             ("neuf", "fi_u", "Neufs : F&I / u", "$"), ("neuf", "comm_u", "Neufs : commissions / u", "$-"),
             ("usage", "u_var", "Unités usagées : écart vs l'an passé", "%p"), ("usage", "pbv_u", "Usagés : profit véhicule / u", "$"),
             ("usage", "fi_u", "Usagés : F&I / u", "$"), ("usage", "comm_u", "Usagés : commissions / u", "$-"),
             ("mix", "ratio_uv", "Usagés vendus par véhicule neuf", "x")]


def _pos_val(S, d, suf, k):
    if suf == "mix":
        rn, _ = S.m2(d, "neuf")
        ru, _ = S.m2(d, "usage")
        return ru.get("u") / rn.get("u") if rn.get("u") and ru.get("u") is not None else None
    r, a = S.m2(d, suf)
    if k == "u_var":
        return var_pct(r.get("u"), a.get("u"))
    return r.get(k)


def p_position(S, d):
    y, m = S.y, S.m
    body = ""
    for suf, k, lab, f in POS_SPECS:
        vals = {x: _pos_val(S, x, suf, k) for x in S.dealers}
        vals = {x: v for x, v in vals.items() if v is not None}
        v = vals.get(d)
        if v is None:
            continue
        g = _pos_val(S, GROUP, suf, k)
        low_good = f == "$-"
        order = sorted(vals, key=lambda x: vals[x] if low_good else -vals[x])
        rk = order.index(d) + 1
        ff = "$" if f.startswith("$") else ("%" if f == "%p" else "x")
        show = (lambda z: pct(z, 0, sign=True)) if f == "%p" else (lambda z: fv(z, ff))
        gd = ""
        if g is not None:
            if f == "%p":
                gd = pts(v - g, 0)
            elif g:
                gd = pct(v / g - 1, 0, sign=True)
        body += (f'<tr><td class="lab">{escape(lab)}</td><td class="strong">{show(v)}</td><td>{show(g) if g is not None else "—"}</td>'
                 f'<td>{gd}</td><td>{rk} / {len(vals)}</td><td>{show(min(vals.values()))} – {show(max(vals.values()))}</td></tr>')
    return f"""
      <div class="eyebrow">Positionnement</div>
      <h1>{escape(DEALERS[d])} dans le Groupe</h1>
      {key(f"Chaque indicateur du cumul {y} comparé au Groupe (sommes des {len(S.dealers)} concessions) et rang (1 = le meilleur : le plus élevé, "
           "ou le plus bas pour les commissions). Marques, clientèles et mix différents : un repère, pas une cible.")}
      <table class="t num fo comp"><thead><tr><th class="lab">Indicateur</th><th>{escape(DEALER_SHORT[d])}</th><th>Groupe</th><th>Écart au Groupe</th>
      <th>Rang</th><th>Plage du Groupe</th></tr></thead><tbody>{body}</tbody></table>
      <div class="note">Écart des unités : variation en % par rapport à {MOIS[1]}–{MOIS[m]} {y-1} ; écart au Groupe en points. Commissions : par unité au détail.</div>"""


def p_mensuel(S, d):
    y, m = S.y, S.m
    months = list(range(1, m + 1))
    head = "".join(f"<th>{escape(MOIS[i][:4] + '.' if len(MOIS[i]) > 4 else MOIS[i])}</th>" for i in months) + '<th class="sep">Cumul</th>'
    body = ""
    for suf in ("neuf", "usage"):
        body += f'<tr class="sec"><td colspan="{len(months) + 2}">{DLAB[suf]}</td></tr>'
        for k, lab in (("u", "Unités"), ("pbv_u", "Profit véhicule / u"), ("fi_u", "F&I / u")):
            for yy, cls in ((y, ""), (y - 1, "muted")):
                tds = ""
                for i in months:
                    v = S.V.view(d, pkey(yy, i), "month")
                    x = metrics(v[suf]).get(k) if v else None
                    tds += f'<td class="{cls}">{num(x) if x is not None else "—"}</td>'
                vy = S.V.view(d, pkey(yy, m), "ytd")
                x = metrics(vy[suf]).get(k) if vy else None
                tds += f'<td class="sep {cls} {"strong" if not cls else ""}">{num(x) if x is not None else "—"}</td>'
                body += f'<tr><td class="lab {cls}">{escape(lab)} {yy}</td>{tds}</tr>'
    return f"""
      <div class="eyebrow">Mois par mois</div>
      <h1>Détail mensuel {y} comparé à {y-1}</h1>
      {key(f"Chaque mois de {y} (noir) au-dessus du même mois de {y-1} (gris) ; montants par unité en $. Un mois isolé varie beaucoup (ajustements, "
           "bonis de fin de trimestre) : le cumul est plus stable.", "Comment lire")}
      <table class="t num trend fo"><thead><tr><th class="lab">Indicateur</th>{head}</tr></thead><tbody>{body}</tbody></table>"""


def p_tendances(S, d):
    y, m = S.y, S.m
    labels12 = month_labels(S.P, 12)
    lab_short = [l for _, l in labels12]
    specs = [("neuf", "u", "n", "Unités neuves au détail"), ("usage", "u", "n", "Unités usagées au détail"),
             ("neuf", "pbv_u", "$", "Profit véhicule par unité neuve"), ("neuf", "fi_u", "$", "F&I par unité neuve"),
             ("usage", "pbv_u", "$", "Profit véhicule par unité usagée"), ("usage", "fi_u", "$", "F&I par unité usagée")]
    blocks = ""
    for suf, k, f, title in specs:
        vals, aps = [], []
        for p, _ in labels12:
            v = S.V.view(d, p, "month")
            x = metrics(v[suf]).get(k) if v else None
            vals.append(x if x is None or x >= 0 else 0)
            va = S.V.view(d, prior_year(p), "month")
            xa = metrics(va[suf]).get(k) if va else None
            aps.append(xa if xa is None or xa >= 0 else 0)
        blocks += f'<div class="sm"><div class="smh">{escape(title)}</div>{bars_ap(vals, aps, lab_short, "$" if f == "$" else "n")}</div>'
    labels24 = month_labels(S.P, 24)
    ser_d, ser_g = [], []
    for p, _ in labels24:
        v = S.V.view(d, p, "month")
        ser_d.append(both(v).get("tot_u") if v else None)
        g = S.V.group(p, "month", "real", S.dealers)
        if g and len(g["_dealers"]) == len(S.dealers):
            n, u = metrics(g["neuf"]), metrics(g["usage"])
            den = (n.get("u") or 0) + (u.get("u") or 0)
            ser_g.append(((n.get("pbv") or 0) + (n.get("fi") or 0) + (u.get("pbv") or 0) + (u.get("fi") or 0)) / den if den else None)
        else:
            ser_g.append(None)
    long = lines_chart([(d, ser_d), (GROUP, ser_g)], "$", [l for _, l in labels24], width=660, height=132)
    return f"""
      <div class="eyebrow">Tendances</div>
      <h1>Tendances : 12 derniers mois et 24 mois</h1>
      {key(f"Barres bleues : 12 derniers mois ; trait gris : même mois un an plus tôt. En bas : profit + F&I par unité (neufs et usagés) de "
           f"{escape(DEALER_SHORT[d])} comparé au Groupe sur 24 mois.", "Comment lire")}
      <div class="smgrid">{blocks}</div>
      <div class="chart-title">Profit + F&I par unité — {escape(DEALER_SHORT[d])} et Groupe, 24 mois</div>
      <div class="legend"><span class="lgd"><span class="sw" style="background:{DEALER_COLOR[d]}"></span>{escape(DEALER_SHORT[d])}</span>
      <span class="lgd"><span class="sw" style="background:{INK}"></span>Groupe (mois où les 5 concessions ont des données)</span></div>
      <div class="chart">{long}</div>"""


def p_methode(S, d):
    y, m = S.y, S.m
    src, src_a = S.s.source_format(d, S.P), S.s.source_format(d, prior_year(S.P))
    ap = S.s.ap_source(d, S.P, "ytd")
    lim = {
        "stm": "État GM : le F&I (transfert F&A) est ramené dans les départements ; les intérêts sur stocks sont nets des crédits de GM (souvent négatifs) ; "
               "le gros, l'encan et l'export (dont l'export aux États-Unis) sont à part. Commissions F&I non détaillées.",
        "hawks": "État GM : le F&I (transfert F&A) est ramené dans les départements ; intérêts sur stocks nets des crédits de GM ; ventes en gros (882 unités "
                 "usagées depuis janvier) et export à part. Commissions F&I non détaillées.",
        "hyundai": f"{y} : état Hyundai Canada ; cumul {y-1} : Réalisé du Groupe (pas d'état Hyundai Canada d'août {y-1} dans Drive). Unités, profit "
                   "véhicule, F&I, gros, commissions, publicité, intérêts sur stocks et lignes de modèles se comparent (mêmes montants dans les deux "
                   "formats) ; les dépenses totales et le profit du département non : l'état répartit le loyer et les frais indirects entre départements.",
        "vw": "Réalisé VW : F&I détaillé par produit, autres revenus du département (programmes du constructeur, retenues, frais d'administration).",
        "bmw": "Réalisé BMW : F&I détaillé par produit, autres revenus du département (programmes BMW, retenues, frais d'administration).",
    }[d]
    return f"""
      <div class="eyebrow">Méthode</div>
      <h1>Sources et définitions</h1>
      <h2>Sources de {escape(DEALERS[d])}</h2>
      <ul class="retenir compact">
        <li><b>Fichier d'{MOIS[m]} {y}</b> : {escape(SOURCE_LABELS.get(src, '—'))}.</li>
        <li><b>An passé</b> : {"colonnes « année précédente » du Réalisé" if ap == "natif" else ("fichiers " + str(y-1) + " de la concession (" + escape(SOURCE_LABELS.get(src_a, '—')) + ")" if ap else "non disponible")}.</li>
        <li><b>À savoir</b> : {escape(lim)}</li>
      </ul>
      <h2>Définitions</h2>
      <dl class="defs">
        <dt>Unités au détail</dt><dd>Neufs : avec démos et flottes ; usagés : au détail. Les ventes en gros ne sont pas comptées.</dd>
        <dt>Profit véhicule, F&I, gros</dt><dd>Profit brut des lignes véhicules ; revenus du bureau commercial ; profit brut du département − profit véhicule − F&I.
        Par unité : ÷ unités au détail (jamais le gros).</dd>
        <dt>Frais de vente</dt><dd>Commissions des vendeurs, publicité nette, intérêts sur stocks nets, préparation et livraison, par unité au détail.</dd>
        <dt>Profit du département</dt><dd>Profit brut − dépenses du département (+ autres revenus du département au Réalisé), selon la répartition du fichier.</dd>
        <dt>Groupe</dt><dd>Sommes des concessions ; ratios recalculés à partir des sommes.</dd>
      </dl>
      <p class="note">Rapport tiré du tableau de bord KPI (data.json). Même méthode que le rapport « Ventes de véhicules » du Groupe.</p>"""


def build_book(s, P, d):
    rc.setup(s, P)
    rc.FOOTER_LABEL = f"{DEALERS[d]} · Ventes de véhicules · {rc.PERIOD_LABEL}"
    S = VS(s, P)
    bk = Book()
    bk.add_cover(p_cover(S, d))
    bk.add(p_essentiel(S, d))
    import rapport_etoiles as ret        # 3 étoiles et 3 points à améliorer
    bk.add(ret.page_ventes_concession(S, s, P, d))
    for suf in ("neuf", "usage"):
        bk.add(p_dept(S, d, suf))
    bk.add(p_fi(S, d))
    bk.add(p_frais(S, d))
    bk.add(p_position(S, d))
    import rapport_composite as rcomp   # comparaison au composite du constructeur (neufs et occasion)
    for pg in rcomp.pages_ventes_concession(s, P, d):
        bk.add(pg)
    bk.add(p_mensuel(S, d))
    bk.add(p_tendances(S, d))
    bk.add(p_methode(S, d))
    return bk


def generate(s, P, outdir, dealers=None, keep_html=False):
    os.makedirs(outdir, exist_ok=True)
    V = kv.VStore(s)
    res = []
    for d in (dealers or [x for x in DEALERS if V.view(x, P, "ytd")]):
        bk = build_book(s, P, d)
        html = wrap_html(f"{DEALERS[d]} — Ventes de véhicules {rc.PERIOD_LABEL}", bk.pages)
        rc.FOOTER_LABEL = ""
        fp = os.path.join(outdir, f"Rapport_Ventes_{FILE_NAMES[d]}_{P}.pdf")
        hp = os.path.splitext(fp)[0] + ".html"
        with open(hp, "w", encoding="utf-8") as f:
            f.write(html)
        over = to_pdf(hp, fp)
        if not keep_html:
            os.remove(hp)
        res.append((fp, len(bk.pages), over))
    return res


def main():
    ap = argparse.ArgumentParser(description="Rapports Ventes de véhicules par concession — Groupe Automax")
    ap.add_argument("--mois")
    ap.add_argument("--data", default=os.path.join(HERE, "data.json"))
    ap.add_argument("--budget", default=os.path.join(HERE, "budgets.csv"))
    ap.add_argument("--concession", choices=list(DEALERS))
    ap.add_argument("--sortie", default=HERE)
    a = ap.parse_args()
    s = Store(a.data, a.budget)
    if a.mois:
        P = a.mois
    else:
        common = set.intersection(*[set(s.periods(d)) for d in DEALERS])
        P = max(common)
    for fp, n, over in generate(s, P, a.sortie, [a.concession] if a.concession else None):
        print(f"PDF : {fp} ({n} pages)" + (f" — ATTENTION débordement {over}" if over else ""))


if __name__ == "__main__":
    main()
