#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rapport mensuel détaillé par concession — Groupe Automax.

Même esprit que l'ancien rapport individuel (couverture, coup d'œil, résultats, indicateurs, composition en anneaux,
constats), en plus aéré : une idée par page, message clé en tête de page.

    python rapport_concession.py --mois 2026-08 --data ../../data/data.json --sortie sortie
    python rapport_concession.py --mois 2026-08 --concession vw
"""
import argparse
import os
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import rapport_commun as rc
from rapport_commun import (SEC, val, fmt_val, cls_delta, chip, level_chip, key, tile, delta_line, comp_table, donut_block,
                            fam_items, chunks, unreliable_ap, Book, wrap_html, to_pdf, mois_court, last_day, LOGO_DARK)
from kpi_data import Store, DEALERS, MOIS, pkey, split, prior_year, label_period, bridge, ratios, BRIDGE_ITEMS, GPA_PLAUSIBLE_MAX
from kpi_analyse import money, kmoney, num, pct, pts, var_pct, statut, commentaire_ecart, alertes, controle_donnees, r12_ebt, de
from kpi_svg import waterfall, monthly_bars
from rapport_kpi import KEY_ROWS, PB_ITEMS, DEP_ITEMS, issues_html

FILE_NAMES = {"bmw": "BMW_Sherbrooke", "vw": "Volkswagen", "stm": "STM", "hyundai": "Hyundai", "hawks": "HAWKS"}
SOURCE_LABELS = {
    "etat_gm": "état financier standardisé de GM Canada",
    "etat_hyundai": "état financier standardisé de Hyundai Canada",
    "gabarit": "gabarit financier standard du Groupe (Réalisé)",
}

OPS_ROWS = [
    (SEC, "Volume"),
    ("u_neuf", "Unités neuves", "unit", ""),
    ("u_usage", "Unités usagées", "unit", ""),
    ("u_detail", "Total unités détail", "unit", "total"),
    ("ratio_usage_neuf", "Usagés vendus par neuf", "ratio_x", ""),
    ("u_flottes", "Unités flottes", "unit", ""),
    (SEC, "Profit brut par unité ($)"),
    ("gpa_neuf", "Par unité neuve", "gpa", ""),
    ("gpa_usage", "Par unité usagée", "gpa", ""),
    ("pb_vehicules_unite", "Véhicules (neufs + usagés) par unité", "gpa", ""),
    (SEC, "Indicateurs de gestion"),
    ("absorption", "Taux d'absorption après-vente", "ratio", ""),
    ("part_apres_vente", "Part de l'après-vente dans le PB", "ratio", ""),
    ("pers_pct_pb", "Personnel % du profit brut", "ratio_inv", ""),
    ("ebt_unite", "EBT par unité détail ($)", "gpa", ""),
]


def format_source(s, P, d):
    """Source des chiffres de la période, mois par mois quand elle varie."""
    y, m = split(P)
    fmts = {}
    for i in range(1, m + 1):
        f = s.source_format(d, pkey(y, i))
        if f:
            fmts.setdefault(f, []).append(i)
    main = s.source_format(d, P) or "gabarit"
    if main == "gabarit":
        txt = ("Gabarit financier standard du Groupe, qui comprend les colonnes réel, budget et année précédente."
               if s.has_native_budget(d, P, "ytd") else
               "Gabarit financier standard du Groupe (colonnes réel et année précédente) ; le budget n'y est pas saisi.")
    else:
        txt = (SOURCE_LABELS[main][0].upper() + SOURCE_LABELS[main][1:] + ". Ce format ne contient ni colonne budget "
               "ni colonne « année précédente » : la comparaison avec l'an passé est reconstituée à partir des "
               "fichiers de l'an passé déjà versés au tableau de bord.")
    if len(fmts) > 1:
        parts = []
        for f, months in fmts.items():
            runs = []
            for i in months:
                if runs and runs[-1][1] == i - 1:
                    runs[-1][1] = i
                else:
                    runs.append([i, i])
            lab = ", ".join(MOIS[a] if a == b else f"{MOIS[a]} à {MOIS[b]}" for a, b in runs)
            parts.append(f"{lab} : {SOURCE_LABELS[f]}")
        txt += f" Sources par mois en {y} — " + " ; ".join(parts) + "."
    return txt


def comps(s, P, d):
    return ({b: s.comp(d, P, "month", b) for b in ("real", "ap", "budget")},
            {b: s.comp(d, P, "ytd", b) for b in ("real", "ap", "budget")})


def gpa_nc(s, P, d, mode):
    foot, nc, notes = {}, set(), []
    y, _ = split(P)
    for k, lab in (("gpa_neuf", "neuves"), ("gpa_usage", "usagées")):
        if unreliable_ap(s, P, mode, [d], k):
            foot[k] = "<sup>1</sup>"
            nc |= {k, "pb_vehicules_unite", "ebt_unite"} if k == "gpa_usage" else {k}
            notes.append(f"<sup>1</sup> Les unités {lab} {y-1} semblent incomplètes : le profit par unité {y-1} n'est pas comparable (n.c.).")
    return foot, nc, " ".join(notes)


# ============================================================== pages
def p_cover(s, P, d):
    y, m = split(P)
    M, Y = comps(s, P, d)
    vp = var_pct(Y["real"]["ebt"], Y["ap"]["ebt"]) if Y["ap"] else None
    st_lab, _ = statut(vp)
    dm = (f"{kmoney(M['real']['ebt'] - M['ap']['ebt'], sign=True)} ({pct(var_pct(M['real']['ebt'], M['ap']['ebt']), 0, sign=True)}) vs {MOIS[m]} {y-1}"
          if M["ap"] else "an passé : n/d")
    dy = f"{kmoney(Y['real']['ebt'] - Y['ap']['ebt'], sign=True)} ({pct(vp, 0, sign=True)}) vs {y-1}" if Y["ap"] else "an passé : n/d"
    return f"""
      <div class="logo cv-logo">{LOGO_DARK}</div>
      <div class="cv-mid">
        <div class="cv-kicker">Rapport mensuel de performance · {escape(label_period(P))}</div>
        <div class="cv-title cv-dealer">{escape(DEALERS[d])}</div>
        <div class="cv-sub">Résultats {de(m)} et cumul {MOIS[1]}–{MOIS[m]} {y} · analyse des écarts, indicateurs de gestion et données à régler</div>
        <div class="cv-kpis">
          <div><div class="cv-kl">EBT — {escape(MOIS[m])}</div><div class="cv-kv">{kmoney(M['real']['ebt'])}</div><div class="cv-kd">{escape(dm)}</div></div>
          <div><div class="cv-kl">EBT cumulatif {y}</div><div class="cv-kv">{kmoney(Y['real']['ebt'])}</div><div class="cv-kd">{escape(dy)}</div></div>
          <div><div class="cv-kl">Statut</div><div class="cv-kv">{escape(st_lab)}</div><div class="cv-kd">EBT cumulatif vs {y-1}</div></div>
        </div>
      </div>
      <div class="cv-foot">
        <div>Une concession du Groupe Automax</div>
        <div>Préparé le {rc.PREPARED} à partir du tableau de bord KPI · Non audité</div>
        <div class="cv-conf">Confidentiel — usage interne — direction seulement</div>
      </div>"""


def p_coup_doeil(s, P, d):
    y, m = split(P)
    M, Y = comps(s, P, d)
    rm, am, bm = M["real"], M["ap"], M["budget"]
    ry, ay, by = Y["real"], Y["ap"], Y["budget"]
    t1 = "".join([
        tile(f"EBT — {MOIS[m]}", kmoney(rm["ebt"]), [delta_line(rm["ebt"], am["ebt"] if am else None, f"{MOIS[m]} {y-1}"),
                                                     delta_line(rm["ebt"], bm["ebt"] if bm else None, "budget")], True),
        tile(f"Ventes nettes — {MOIS[m]}", kmoney(rm["ventes"]), [delta_line(rm["ventes"], am["ventes"] if am else None, f"{MOIS[m]} {y-1}")]),
        tile(f"Profit brut — {MOIS[m]}", kmoney(rm["pb"]), [delta_line(rm["pb"], am["pb"] if am else None, f"{MOIS[m]} {y-1}")]),
    ])
    t2 = "".join([
        tile("EBT cumulatif", kmoney(ry["ebt"]), [delta_line(ry["ebt"], ay["ebt"] if ay else None, str(y - 1)),
                                                  delta_line(ry["ebt"], by["ebt"] if by else None, "budget")], True),
        tile("Ventes nettes cumulées", kmoney(ry["ventes"]), [delta_line(ry["ventes"], ay["ventes"] if ay else None, str(y - 1))]),
        tile("Profit brut cumulatif", kmoney(ry["pb"]), [delta_line(ry["pb"], ay["pb"] if ay else None, str(y - 1))]),
    ])
    vp = var_pct(ry["ebt"], ay["ebt"]) if ay else None
    st_lab, st_cls = statut(vp)
    r12 = r12_ebt(s, d, P)
    bul = []
    if am:
        bul.append(f"<b>{MOIS[m].capitalize()} :</b> " + escape(commentaire_ecart(DEALERS[d], rm, am, bridge(rm, am), "ap", P, "month", 2)))
    if ay:
        bul.append("<b>Depuis janvier :</b> " + escape(commentaire_ecart(DEALERS[d], ry, ay, bridge(ry, ay), "ap", P, "ytd", 2)))
    if by:
        bul.append("<b>Budget :</b> " + escape(commentaire_ecart(DEALERS[d], ry, by, bridge(ry, by), "budget", P, "ytd", 2)))
    return f"""
      <div class="eyebrow">Sommaire</div>
      <h1>{escape(DEALERS[d])} en un coup d'œil</h1>
      <div class="band-lab">Le mois <span>{MOIS[m]} {y} comparé à {MOIS[m]} {y-1}</span></div>
      <div class="tiles">{t1}</div>
      <div class="band-lab">Depuis janvier <span>cumul {MOIS[1]}–{MOIS[m]} {y} comparé à la même période {y-1}</span></div>
      <div class="tiles">{t2}</div>
      <p style="margin-top:6px">Statut : {chip(st_lab, st_cls)} <span class="muted">(EBT cumulatif vs {y-1}){f' · EBT des 12 derniers mois : {kmoney(r12)}' if r12 is not None else ''}</span></p>
      <h2>Ce qu'il faut retenir</h2>
      <ul class="retenir">{''.join(f'<li>{b}</li>' for b in bul)}</ul>"""


def p_base(s, P, d):
    y, m = split(P)
    src_ap = {"natif": "colonne « année précédente » du fichier source", "reconstitue": f"reconstituée à partir des fichiers {y-1} de la concession",
              None: "non disponible"}[s.ap_source(d, P, "ytd")]
    src_b = {"natif": "budget du fichier source", "csv": "budget saisi dans budgets.csv", None: f"aucun budget {y} n'est disponible pour cette concession"}[s.budget_source(d, P, "ytd")]
    return f"""
      <div class="eyebrow">Introduction</div>
      <h1>Base de présentation</h1>
      <p class="lead">Ce rapport présente les résultats d'exploitation de {escape(DEALERS[d])} pour le mois {de(m)} {y} et pour la période de {m} mois terminée
      le {last_day(P)}, comparés aux mêmes périodes de {y-1}.</p>
      <h2>Périodes</h2>
      <p>Mois : {MOIS[m]} {y} comparé à {MOIS[m]} {y-1}.<br>Cumul : {MOIS[1]} à {MOIS[m]} {y} comparé à {MOIS[1]} à {MOIS[m]} {y-1}.</p>
      <h2>Sources</h2>
      <p><b>Format du fichier.</b> {escape(format_source(s, P, d))}</p>
      <p><b>An passé.</b> {escape(src_ap).capitalize()}.</p>
      <p><b>Budget.</b> {escape(src_b).capitalize()}.</p>
      <h2>Comment lire ce rapport</h2>
      <ul class="retenir">
        <li>Chaque page commence par un encadré vert qui résume ce qu'il faut retenir.</li>
        <li>Montants en k$ (milliers de dollars) sauf indication.</li>
        <li>Un écart <span class="pos"><b>vert</b></span> est favorable, un écart <span class="neg"><b>rouge</b></span> est défavorable. Pour les dépenses, vert veut dire plus bas.</li>
        <li>Les définitions et les seuils d'alerte sont les mêmes que dans le rapport mensuel du Groupe.</li>
      </ul>"""


def p_resultats(s, P, d, mode):
    y, m = split(P)
    M, Y = comps(s, P, d)
    C = M if mode == "month" else Y
    r, a, b = C["real"], C["ap"], C["budget"]
    foot, nc, note = gpa_nc(s, P, d, mode)
    cols = [{"h": f"{mois_court(m)} {y}" if mode == "month" else f"Cumul {y}", "t": "v", "c": r},
            {"h": f"{mois_court(m)} {y-1}" if mode == "month" else f"Cumul {y-1}", "t": "v", "c": a, "vcls": "muted"},
            {"h": "Écart", "t": "d", "c": (r, a), "cls": "sep", "nc": nc}, {"h": "%", "t": "p", "c": (r, a), "nc": nc}]
    heads = None
    if b:
        cols += [{"h": "Budget", "t": "v", "c": b, "cls": "sep", "vcls": "muted"}, {"h": "Écart", "t": "d", "c": (r, b)}]
        heads = [(f"vs {y-1}", 4, ""), ("vs budget", 2, "sep")]
    table = comp_table(KEY_ROWS, cols, heads=heads, foot=foot)
    if a:
        k = (f"EBT de <b>{kmoney(r['ebt'])}</b>, soit <b>{kmoney(r['ebt'] - a['ebt'], sign=True)}</b> ({pct(var_pct(r['ebt'], a['ebt']), 0, sign=True)}) "
             f"par rapport à {MOIS[m] + ' ' + str(y-1) if mode == 'month' else 'la même période de ' + str(y-1)}"
             + (f", et {kmoney(r['ebt'] - b['ebt'], sign=True)} par rapport au budget" if b else "") + ".")
    else:
        k = f"EBT de <b>{kmoney(r['ebt'])}</b> ; aucune comparaison avec l'an passé n'est disponible."
    titre = f"Résultats {de(m)} {y}" if mode == "month" else f"Résultats cumulatifs — {MOIS[1]} à {MOIS[m]} {y}"
    return f"""
      <div class="eyebrow">Performance financière</div>
      <h1>{escape(titre)}</h1>
      {key(k)}
      {table}
      <div class="note">Vert = favorable ; pour les dépenses, vert = plus basses.{'' if b else f' Aucun budget {y} disponible pour cette concession.'} {note}</div>"""


def p_operations(s, P, d):
    y, m = split(P)
    _, Y = comps(s, P, d)
    r, a = Y["real"], Y["ap"]
    foot, nc, note = gpa_nc(s, P, d, "ytd")
    rows = [x for x in OPS_ROWS if x[0] == SEC or any(v not in (None, 0) for v in (val(r, x[0]), val(a, x[0])))]
    table = comp_table(rows, [{"h": f"Cumul {y}", "t": "v", "c": r}, {"h": f"Cumul {y-1}", "t": "v", "c": a, "vcls": "muted"},
                              {"h": "Écart", "t": "d", "c": (r, a), "cls": "sep", "nc": nc}, {"h": "%", "t": "p", "c": (r, a), "nc": nc}], foot=foot)
    rr, ra = ratios(r), ratios(a) if a else {}
    k = f"Taux d'absorption après-vente de <b>{pct(rr['absorption'], 1)}</b>"
    if ra.get("absorption") is not None:
        k += f" ({pts(rr['absorption'] - ra['absorption'], 1)} vs {y-1})"
    k += f" et <b>{num(rr['u_detail'])}</b> unités détail vendues depuis janvier"
    if a:
        k += f" ({num(rr['u_detail'] - ra['u_detail'], sign=True)} vs {y-1})"
    k += "."
    return f"""
      <div class="eyebrow">Indicateurs opérationnels</div>
      <h1>Véhicules et indicateurs de gestion — cumul {y}</h1>
      {key(k)}
      {table}
      <div class="note">{note} Absorption = profit brut service + pièces + carrosserie ÷ (dépenses totales − dépenses variables).</div>"""


def p_compo(s, P, d, what):
    y, m = split(P)
    _, Y = comps(s, P, d)
    r, a = Y["real"], Y["ap"]
    items = [x for x in (PB_ITEMS if what == "pb" else DEP_ITEMS) if abs(r[x[1]]) > 0.5 or (a and abs(a[x[1]]) > 0.5)]
    k = rc.compo_message(r, a, items, y, "du profit brut" if what == "pb" else "des dépenses")
    titre = "Composition du profit brut" if what == "pb" else "Composition des dépenses"
    return f"""
      <div class="eyebrow">Analyse opérationnelle</div>
      <h1>{titre} — cumul {MOIS[1]} à {MOIS[m]}</h1>
      {key(k)}
      {donut_block(items, a, r, f"Cumul {y-1}", f"Cumul {y}")}"""


def p_pont(s, P, d, mode):
    y, m = split(P)
    M, Y = comps(s, P, d)
    C = M if mode == "month" else Y
    r, a, b = C["real"], C["ap"], C["budget"]
    titre = f"D'où vient l'écart d'EBT — {MOIS[m]} {y}" if mode == "month" else f"D'où vient l'écart d'EBT — cumul {y}"
    if not a:
        return f'<div class="eyebrow">Analyse des écarts</div><h1>{escape(titre)}</h1>{key("Aucune comparaison avec l’an passé n’est disponible.")}'
    br = bridge(r, a)
    st = f"EBT\n{mois_court(m)} {y-1}" if mode == "month" else f"EBT cumul\n{y-1}"
    en = f"EBT\n{mois_court(m)} {y}" if mode == "month" else f"EBT cumul\n{y}"
    svg = waterfall((st, a["ebt"]), fam_items(br), (en, r["ebt"]), width=672, height=300)
    labels = dict((k, l) for k, l, _ in BRIDGE_ITEMS)
    top = sorted([(k, v) for k, v in br.items() if abs(v) >= 1000], key=lambda kv: -abs(kv[1]))[:5]
    rows = "".join(f'<tr><td class="lab">{escape(labels[k].replace("¹", ""))}</td><td class="{"pos" if v > 0 else "neg"}">{kmoney(v, sign=True)}</td>'
                   f'<td class="lab muted">{"favorable" if v > 0 else "défavorable"}</td></tr>' for k, v in top)
    extra = ""
    if mode == "ytd" and b:
        extra = f'<div class="callout"><b>Par rapport au budget :</b> {escape(commentaire_ecart(DEALERS[d], r, b, bridge(r, b), "budget", P, "ytd"))}</div>'
    ref = f"{MOIS[m]} {y-1}" if mode == "month" else str(y - 1)
    return f"""
      <div class="eyebrow">Analyse des écarts</div>
      <h1>{escape(titre)}</h1>
      {key(escape(commentaire_ecart(DEALERS[d], r, a, br, 'ap', P, mode)))}
      <div class="chart-sub">Chaque barre montre ce qu'un poste ajoute (vert) ou retire (rouge) à l'EBT par rapport à {ref}. La somme des barres égale l'écart.</div>
      <div class="chart">{svg}</div>
      <h2>Les postes qui pèsent le plus</h2>
      <table class="t num"><thead><tr><th class="lab">Poste</th><th>Effet sur l'EBT</th><th class="lab"></th></tr></thead><tbody>{rows}</tbody></table>
      {extra}"""


def p_tendances(s, P, d):
    y, m = split(P)
    labels = [MOIS[i][0].upper() for i in range(1, m + 1)]
    ebt, ebt_ap, pb, pb_ap, partial = [], [], [], [], set()
    for i in range(1, m + 1):
        p = pkey(y, i)
        c, a = s.comp(d, p, "month", "real"), s.comp(d, p, "month", "ap")
        ebt.append(c["ebt"] if c else None)
        ebt_ap.append(a["ebt"] if a else None)
        pb.append(c["pb"] if c else None)
        pb_ap.append(a["pb"] if a else None)
        if c and s._native_section(d, p, "month") is None:
            partial.add(i - 1)
    ok = [(v, i) for i, v in enumerate(ebt) if v is not None]
    best, worst = max(ok), min(ok)
    k = f"Meilleur mois de l'année : <b>{MOIS[best[1] + 1]}</b> ({kmoney(best[0])}) ; mois le plus faible : <b>{MOIS[worst[1] + 1]}</b> ({kmoney(worst[0])})."
    return f"""
      <div class="eyebrow">Tendances</div>
      <h1>Mois par mois — {y}</h1>
      {key(k)}
      <div class="legend"><span class="lg-bar"></span> {y} <span class="lg-tick"></span> {y-1}, même mois <span class="lg-hatch"></span> mois reconstitué</div>
      <div class="chart-title">EBT mensuel</div><div class="chart">{monthly_bars(ebt, ebt_ap, labels, 672, 230, partial=partial)}</div>
      <div class="chart-title">Profit brut mensuel</div><div class="chart">{monthly_bars(pb, pb_ap, labels, 672, 230, partial=partial)}</div>"""


def p_tendances_table(s, P, d):
    y, m = split(P)
    rows_def = [("ventes", "Ventes nettes", "money"), ("pb", "Profit brut", "money"), ("dep", "Dépenses totales", "exp"),
                ("ebt", "EBT", "money"), ("u_neuf", "Unités neuves", "unit"), ("u_usage", "Unités usagées", "unit")]
    ab = (lambda i: mois_court(i)) if m <= 8 else (lambda i: MOIS[i][:3] + ("." if len(MOIS[i]) > 3 else ""))
    head = "".join(f"<th>{ab(i)}</th>" for i in range(1, m + 1))
    ry, ay = s.comp(d, P, "ytd", "real"), s.comp(d, P, "ytd", "ap")
    body = ""
    for k, lab, kind in rows_def:
        tds = ""
        for i in range(1, m + 1):
            p = pkey(y, i)
            c = s.comp(d, p, "month", "real")
            v = val(c, k) if c else None
            star = "*" if (c and s._native_section(d, p, "month") is None) else ""
            tds += f'<td class="{"neg" if (v is not None and k == "ebt" and v < 0) else ""}">{fmt_val(v, kind) if v is not None else "n/d"}{star}</td>'
        body += (f'<tr class="{"total strong" if k == "ebt" else ""}"><td class="lab">{lab}</td>{tds}'
                 f'<td class="sep"><b>{fmt_val(val(ry, k), kind)}</b></td><td class="muted">{fmt_val(val(ay, k), kind) if ay else "—"}</td></tr>')
    r12, r12p = r12_ebt(s, d, P), r12_ebt(s, d, prior_year(P))
    r12_txt = ((f"EBT des 12 derniers mois : <b>{kmoney(r12)}</b>" + (f", {kmoney(r12 - r12p, sign=True)} par rapport aux 12 mois précédents." if r12p is not None else "."))
               if r12 is not None else "EBT des 12 derniers mois : historique mensuel incomplet.")
    return f"""
      <div class="eyebrow">Tendances</div>
      <h1>Détail mensuel {y}</h1>
      {key(r12_txt)}
      <table class="t num trend{' wide' if m > 8 else ''}"><thead><tr><th class="lab">k$ sauf unités</th>{head}<th class="sep">Cumul {y}</th><th>Cumul {y-1}</th></tr></thead><tbody>{body}</tbody></table>
      <div class="note">* mois reconstitué à partir des cumuls. Le cumul peut différer de la somme des mois quand des révisions sont passées sur des mois antérieurs.</div>"""


def constats(s, P, d):
    y, m = split(P)
    M, Y = comps(s, P, d)
    rm, am = M["real"], M["ap"]
    ry, ay, by = Y["real"], Y["ap"], Y["budget"]
    out = []
    if ay:
        rr, ra = ratios(ry), ratios(ay)
        out.append(f"<b>Rentabilité.</b> L'EBT cumulatif atteint {kmoney(ry['ebt'])}, {kmoney(ry['ebt'] - ay['ebt'], sign=True)} "
                   f"({pct(var_pct(ry['ebt'], ay['ebt']), 0, sign=True)}) par rapport à {y-1}, soit {pct(rr['ros'], 1)} des ventes (contre {pct(ra['ros'], 1)}).")
        out.append(f"<b>Volume.</b> Unités neuves : {num(ay['u_neuf'])} → {num(ry['u_neuf'])} ({num(ry['u_neuf'] - ay['u_neuf'], sign=True)}) ; "
                   f"unités usagées : {num(ay['u_usage'])} → {num(ry['u_usage'])} ({num(ry['u_usage'] - ay['u_usage'], sign=True)}).")
        g = []
        for k, lab in (("gpa_neuf", "neuve"), ("gpa_usage", "usagée")):
            if rr.get(k) and ra.get(k) and abs(ra[k]) <= GPA_PLAUSIBLE_MAX:
                g.append(f"par unité {lab} {money(ra[k])} → {money(rr[k])} ({pct(rr[k] / ra[k] - 1, 0, sign=True)})")
        if g:
            out.append("<b>Profit par unité.</b> " + " ; ".join(g).capitalize() + ".")
        deps = [("pb_neuf", "véhicules neufs"), ("pb_usage", "véhicules usagés"), ("pb_service", "service"), ("pb_carrosserie", "carrosserie"), ("pb_pieces", "pièces")]
        big = max(deps, key=lambda t: abs(ry[t[0]] - ay[t[0]]))
        vp = var_pct(ry[big[0]], ay[big[0]])
        out.append(f"<b>Département le plus mouvementé.</b> {big[1].capitalize()} : {kmoney(ry[big[0]] - ay[big[0]], sign=True)}"
                   + (f" ({pct(vp, 0, sign=True)})" if vp is not None else "") + " de profit brut sur l'année.")
        out.append(f"<b>Dépenses.</b> Les dépenses représentent {pct(rr['dep_pct_pb'], 1)} du profit brut, contre {pct(ra['dep_pct_pb'], 1)} il y a un an"
                   + (" : au-delà de 100 %, l'EBT repose sur les autres revenus." if rr['dep_pct_pb'] > 1 else "."))
    if by:
        out.append(f"<b>Budget.</b> EBT cumulatif {kmoney(ry['ebt'] - by['ebt'], sign=True)} ({pct(var_pct(ry['ebt'], by['ebt']), 0, sign=True)}) par rapport au budget.")
    if am:
        out.append(f"<b>Le mois.</b> EBT {de(m)} de {kmoney(rm['ebt'])}, {kmoney(rm['ebt'] - am['ebt'], sign=True)} par rapport à {MOIS[m]} {y-1}.")
    return out


def p_constats(s, P, d):
    y, m = split(P)
    return f"""
      <div class="eyebrow">Perspectives</div>
      <h1>Ce que les données montrent</h1>
      {key(f"Constats tirés uniquement des chiffres {de(m)} {y} et du cumul, comparés à {y-1}.", "Comment lire")}
      <ul class="retenir">{''.join(f'<li>{b}</li>' for b in constats(s, P, d))}</ul>
      <div class="nodata">Priorités de gestion et plans d'action — à compléter par la direction. Les constats ci-dessus reposent uniquement sur les chiffres
      du tableau de bord KPI et ne remplacent pas la planification de la direction.</div>"""


def p_points(s, P, d, al, part, idx, first):
    alerts = ""
    if first:
        my_al = [a for a in al if a[0] == d]
        rows = "".join(f'<tr><td class="lvlc">{level_chip(lv)}</td><td>{escape(t)}</td></tr>' for _, lv, t in my_al) \
            or '<tr><td class="muted" colspan="2">Aucune alerte ce mois-ci.</td></tr>'
        alerts = f'<h2>Alertes</h2><table class="t alerts"><tbody>{rows}</tbody></table>'
    issues = issues_html(part, with_dealer=False) if part else '<p class="muted">Aucun point de données à régler.</p>'
    return f"""
      <div class="eyebrow">Perspectives</div>
      <h1>Points d'attention{f' ({idx[0]}/{idx[1]})' if idx[1] > 1 else ''}</h1>
      {alerts}
      <h2>Données à régler pour les prochains mois</h2>
      {issues}"""


def build_book(s, P, d):
    al = alertes(s, P)
    _, anomalies = controle_donnees(s, P)
    my_an = [a for a in anomalies if a[0] == d]
    bk = Book()
    bk.add_cover(p_cover(s, P, d))
    bk.add(p_coup_doeil(s, P, d))
    bk.add(p_base(s, P, d))
    bk.add(p_resultats(s, P, d, "month"))
    bk.add(p_resultats(s, P, d, "ytd"))
    bk.add(p_operations(s, P, d))
    bk.add(p_compo(s, P, d, "pb"))
    bk.add(p_compo(s, P, d, "dep"))
    bk.add(p_pont(s, P, d, "month"))
    bk.add(p_pont(s, P, d, "ytd"))
    bk.add(p_tendances(s, P, d))
    bk.add(p_tendances_table(s, P, d))
    bk.add(p_constats(s, P, d))
    n_al = len([a for a in al if a[0] == d])
    first_size = max(1, 6 - n_al)             # moins de points sur la page qui porte aussi les alertes
    parts = [my_an[:first_size]] + chunks(my_an[first_size:], 7) if len(my_an) > first_size else [my_an]
    parts = [p for p in parts if p] or [[]]
    for i, part in enumerate(parts):
        bk.add(p_points(s, P, d, al, part, (i + 1, len(parts)), i == 0))
    return bk


def build_dealer_html(s, P, d):
    rc.setup(s, P)
    rc.FOOTER_LABEL = f"{DEALERS[d]} · Rapport mensuel de performance · {rc.PERIOD_LABEL}"
    bk = build_book(s, P, d)
    rc.FOOTER_LABEL = ""
    return wrap_html(f"{DEALERS[d]} — Rapport mensuel {rc.PERIOD_LABEL}", bk.pages), len(bk.pages)


def generate(s, P, outdir, dealers=None):
    os.makedirs(outdir, exist_ok=True)
    rc.setup(s, P)
    res = []
    for d in (dealers or rc.ACTIVE):
        fp = os.path.join(outdir, f"Rapport_{FILE_NAMES.get(d, d)}_{P}.pdf")
        hp = os.path.splitext(fp)[0] + ".html"
        html, n = build_dealer_html(s, P, d)
        with open(hp, "w", encoding="utf-8") as f:
            f.write(html)
        over = to_pdf(hp, fp)
        os.remove(hp)
        res.append((fp, n, over))
    return res


def main():
    ap = argparse.ArgumentParser(description="Rapports mensuels par concession — Groupe Automax")
    ap.add_argument("--mois")
    ap.add_argument("--data", default=os.path.join(HERE, "data.json"))
    ap.add_argument("--budget", default=os.path.join(HERE, "budgets.csv"))
    ap.add_argument("--concession", choices=list(DEALERS))
    ap.add_argument("--sortie", default=HERE, help="Dossier de sortie")
    a = ap.parse_args()
    s = Store(a.data, a.budget)
    P = a.mois or max(set.intersection(*[set(s.periods(d)) for d in DEALERS]))
    for fp, n, over in generate(s, P, a.sortie, [a.concession] if a.concession else None):
        print(f"PDF : {fp} ({n} pages)" + (f" — ATTENTION débordement {over}" if over else ""))


if __name__ == "__main__":
    main()
