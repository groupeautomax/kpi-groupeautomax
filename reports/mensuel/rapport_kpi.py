#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rapport mensuel de performance KPI — Groupe Automax (rapport du Groupe).

Une idée par page : message clé en tête, un tableau ou un graphique, une explication.

    python rapport_kpi.py --mois 2026-08 --data ../../data/data.json --sortie sortie/Rapport_KPI_Groupe_Automax_2026-08.pdf
    python rapport_kpi.py --gabarit-budget budgets.csv --annee 2026

Dépendance : playwright (Chromium).
"""
import argparse
import csv
import datetime as dt
import os
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import rapport_commun as rc
from rapport_commun import (SEC, FAMILY_SHORT, val, fmt_val, fmt_delta, cls_delta, chip, level_chip, key, tile, delta_line,
                            comp_table, donut_block, heat_color, fam_items, chunks, unreliable_ap, Book, wrap_html, to_pdf,
                            mois_court, last_day, LOGO_DARK)
from kpi_data import (Store, DEALERS, DEALER_SHORT, MOIS, BRIDGE_ITEMS, BRIDGE_FAMILIES, BUDGET_CSV_KEYS, bridge,
                      bridge_families, ratios, pkey, split, prior_year, prev_month, label_period)
from kpi_analyse import (money, kmoney, num, pct, pts, var_pct, group_pair, group_bridge, statut, commentaire_ecart,
                         top_facteurs, alertes, controle_donnees, r12_ebt, rank, SEUILS, STATUTS, de)
from kpi_svg import waterfall, monthly_bars, paired_hbars, donut, icon, CAT, CAT_OTHER

# ------------------------------------------------------------ lignes des tableaux
KEY_ROWS = [
    (SEC, "Ventes et profit brut"),
    ("ventes", "Ventes nettes", "money", ""),
    ("pb", "Profit brut", "money", ""),
    ("marge_brute", "Marge brute (% des ventes)", "ratio", ""),
    (SEC, "Dépenses et résultat"),
    ("ar", "Autres revenus", "money", ""),
    ("dep", "Dépenses totales", "exp", ""),
    ("baiia", "BAIIA", "money", ""),
    ("ebt", "EBT (profit net avant impôt)", "money", "total strong"),
    ("ros", "EBT % des ventes", "ratio", ""),
    ("dep_pct_pb", "Dépenses % du profit brut", "ratio_inv", ""),
    (SEC, "Véhicules"),
    ("u_neuf", "Unités neuves", "unit", ""),
    ("u_usage", "Unités usagées", "unit", ""),
    ("gpa_neuf", "Profit brut par unité neuve ($)", "gpa", ""),
    ("gpa_usage", "Profit brut par unité usagée ($)", "gpa", ""),
]
BUDGET_ROWS = [("ventes", "Ventes nettes", "money", ""), ("pb", "Profit brut", "money", ""),
               ("dep", "Dépenses totales", "exp", ""), ("ebt", "EBT", "money", "total strong")]
PB_ITEMS = [("Véhicules neufs", "pb_neuf"), ("Véhicules usagés", "pb_usage"), ("Service", "pb_service"),
            ("Carrosserie", "pb_carrosserie"), ("Pièces", "pb_pieces"), ("Autres sources (gros, F&I)", "pb_autres")]
DEP_ITEMS = [("Variables", "dep_var"), ("Personnel", "dep_pers"), ("Semi-fixes", "dep_semi"), ("Autres (fixes non ventilées)", "dep_autres")]
IND_ROWS = [
    ("marge_brute", "Marge brute", "ratio"),
    ("gpa_neuf", "Profit brut / unité neuve ($)", "gpa"),
    ("gpa_usage", "Profit brut / unité usagée ($)", "gpa"),
    ("ratio_usage_neuf", "Usagés vendus par neuf", "ratio_x"),
    ("part_apres_vente", "Part de l'après-vente dans le PB", "ratio"),
    ("absorption", "Taux d'absorption après-vente", "ratio"),
    ("dep_pct_pb", "Dépenses % du PB", "ratio_inv"),
    ("pers_pct_pb", "Personnel % du PB", "ratio_inv"),
    ("ebt_pct_pb", "EBT % du PB", "ratio"),
    ("ros", "EBT % des ventes", "ratio"),
    ("ebt_unite", "EBT par unité détail ($)", "gpa"),
]
FAM_PHRASE = {
    "PB neufs": "le profit brut des neufs", "PB usagés": "le profit brut des usagés", "Après-vente": "l'après-vente",
    "Autres PB": "les autres sources de profit brut", "Autres revenus": "les autres revenus",
    "Dépenses variables": "les dépenses variables", "Personnel": "les dépenses de personnel",
    "Semi-fixes et autres": "les dépenses semi-fixes et autres", "Amortissement": "l'amortissement",
}


def phrase_familles(b, n=2):
    fam = bridge_families(b)
    neg = sorted([(k, v) for k, v in fam.items() if v <= -1000], key=lambda kv: kv[1])[:n]
    posf = sorted([(k, v) for k, v in fam.items() if v >= 1000], key=lambda kv: -kv[1])[:n]
    fmt = lambda lst: " et ".join(f"{FAM_PHRASE[k]} ({kmoney(v, sign=True)})" for k, v in lst)
    parts = []
    if neg:
        parts.append(f"en défaveur, {fmt(neg)}")
    if posf:
        parts.append(f"en faveur, {fmt(posf)}")
    return " ; ".join(parts)


def gpa_notes(s, P, dealers, mode="ytd"):
    y, _ = split(P)
    foot, notes, nc = {}, [], set()
    for k, lab in (("gpa_neuf", "neuves"), ("gpa_usage", "usagées")):
        bad = unreliable_ap(s, P, mode, dealers, k)
        if bad:
            foot[k] = "<sup>1</sup>"
            nc.add(k)
            notes.append(f"<sup>1</sup> Les unités {lab} {y-1} de {', '.join(DEALERS[b] for b in bad)} semblent incomplètes : "
                         f"le profit par unité {y-1} n'est pas comparable (n.c.).")
    return foot, " ".join(dict.fromkeys(notes)), nc


# ============================================================== pages
def p_cover(s, P, toc):
    gm, gmb, _ = group_pair(s, P, "month", "ap")
    gy, gyb, _ = group_pair(s, P, "ytd", "ap")
    y, m = split(P)
    toc_html = "".join(f'<div class="toc-row"><span>{escape(t)}</span><span class="toc-dots"></span><span>{p}</span></div>' for t, p in toc)
    missing = [DEALERS[d] for d in DEALERS if d not in rc.ACTIVE]
    return f"""
      <div class="logo cv-logo">{LOGO_DARK}</div>
      <div class="cv-mid">
        <div class="cv-kicker">Rapport mensuel de performance</div>
        <div class="cv-title">{escape(label_period(P, True))}</div>
        <div class="cv-sub">Résultats {de(m)} et cumul {MOIS[1]}–{MOIS[m]} {y}, comparés à l'an passé et au budget</div>
        <div class="cv-kpis">
          <div><div class="cv-kl">EBT du groupe — {escape(MOIS[m])}</div><div class="cv-kv">{kmoney(gm['ebt'])}</div>
               <div class="cv-kd">{kmoney(gm['ebt']-gmb['ebt'], sign=True)} ({pct(var_pct(gm['ebt'], gmb['ebt']), 0, sign=True)}) vs {escape(MOIS[m])} {y-1}</div></div>
          <div><div class="cv-kl">EBT cumulatif {y}</div><div class="cv-kv">{kmoney(gy['ebt'])}</div>
               <div class="cv-kd">{kmoney(gy['ebt']-gyb['ebt'], sign=True)} ({pct(var_pct(gy['ebt'], gyb['ebt']), 0, sign=True)}) vs {y-1}</div></div>
          <div><div class="cv-kl">Ventes nettes cumulées</div><div class="cv-kv">{kmoney(gy['ventes'])}</div>
               <div class="cv-kd">{pct(var_pct(gy['ventes'], gyb['ventes']), 1, sign=True)} vs {y-1}</div></div>
        </div>
      </div>
      <div class="cv-toc"><div class="cv-toc-h">Dans ce rapport</div>{toc_html}</div>
      <div class="cv-foot">
        <div>Concessions : {' · '.join(escape(DEALERS[d]) for d in rc.ACTIVE)}{(' — sans données ce mois : ' + ', '.join(missing)) if missing else ''}</div>
        <div>Préparé le {rc.PREPARED} à partir du tableau de bord KPI · Non audité</div>
        <div class="cv-conf">Confidentiel — usage interne — direction seulement</div>
      </div>"""


def retenir(s, P, marks):
    y, m = split(P)
    out = []
    gm, gmb, _ = group_pair(s, P, "month", "ap")
    out.append(f"<b>{MOIS[m].capitalize()} : EBT du groupe de {kmoney(gm['ebt'])}</b>, {kmoney(gm['ebt']-gmb['ebt'], sign=True)} "
               f"({pct(var_pct(gm['ebt'], gmb['ebt']), 0, sign=True)}) par rapport à {MOIS[m]} {y-1} — {phrase_familles(group_bridge(s, P, 'month', 'ap'))}.")
    gy, gyb, _ = group_pair(s, P, "ytd", "ap")
    by = group_bridge(s, P, "ytd", "ap")
    out.append(f"<b>Depuis janvier : EBT de {kmoney(gy['ebt'])}</b>, {kmoney(gy['ebt']-gyb['ebt'], sign=True)} "
               f"({pct(var_pct(gy['ebt'], gyb['ebt']), 0, sign=True)}) par rapport à {y-1} — {phrase_familles(by)}.")
    du = sum(s.comp(d, P, "ytd", "real")["u_usage"] - s.comp(d, P, "ytd", "ap")["u_usage"] for d in rc.ACTIVE if s.comp(d, P, "ytd", "ap"))
    out.append(f"<b>Véhicules usagés :</b> {num(du, sign=True)} unités par rapport à {y-1} (effet volume {kmoney(by['usage_vol'], sign=True)}), "
               f"mais un profit par unité plus bas ({kmoney(by['usage_marge'], sign=True)}). <b>Neufs :</b> volume {kmoney(by['neuf_vol'], sign=True)}, "
               f"profit par unité {kmoney(by['neuf_marge'], sign=True)}.")
    deltas = {}
    for d in rc.ACTIVE:
        r, a = s.comp(d, P, "ytd", "real"), s.comp(d, P, "ytd", "ap")
        if a:
            deltas[d] = (r["ebt"] - a["ebt"], var_pct(r["ebt"], a["ebt"]))
    if deltas:
        best, worst = max(deltas, key=lambda k: deltas[k][0]), min(deltas, key=lambda k: deltas[k][0])
        out.append(f"<b>{escape(DEALERS[best])}</b> progresse le plus ({kmoney(deltas[best][0], sign=True)}, {pct(deltas[best][1], 0, sign=True)} sur l'année) ; "
                   f"<b>{escape(DEALERS[worst])}</b> recule le plus ({kmoney(deltas[worst][0], sign=True)}, {pct(deltas[worst][1], 0, sign=True)}).")
    rbud, bbud, inc = group_pair(s, P, "ytd", "budget")
    if inc:
        out.append(f"<b>Budget ({' + '.join(DEALER_SHORT[x] for x in inc)}) :</b> EBT cumulatif {kmoney(rbud['ebt']-bbud['ebt'], sign=True)} "
                   f"({pct(var_pct(rbud['ebt'], bbud['ebt']), 0, sign=True)}) par rapport au budget. Les autres concessions n'ont pas encore de budget {y} "
                   f"(p. {marks.get('qualite', '—')}).")
    return out


def p_essentiel(s, P, marks):
    y, m = split(P)
    gm, gmb, _ = group_pair(s, P, "month", "ap")
    gy, gyb, _ = group_pair(s, P, "ytd", "ap")
    bm, bmb, inc = group_pair(s, P, "month", "budget")
    byr, byb, _ = group_pair(s, P, "ytd", "budget")
    ref_b = "budget¹"
    t1 = "".join([
        tile(f"EBT — {MOIS[m]}", kmoney(gm["ebt"]), [delta_line(gm["ebt"], gmb["ebt"], f"{MOIS[m]} {y-1}"),
                                                     delta_line(bm["ebt"] if bm else None, bmb["ebt"] if bmb else None, ref_b)], True),
        tile(f"Ventes nettes — {MOIS[m]}", kmoney(gm["ventes"]), [delta_line(gm["ventes"], gmb["ventes"], f"{MOIS[m]} {y-1}")]),
        tile(f"Profit brut — {MOIS[m]}", kmoney(gm["pb"]), [delta_line(gm["pb"], gmb["pb"], f"{MOIS[m]} {y-1}")]),
    ])
    t2 = "".join([
        tile("EBT cumulatif", kmoney(gy["ebt"]), [delta_line(gy["ebt"], gyb["ebt"], str(y - 1)),
                                                  delta_line(byr["ebt"] if byr else None, byb["ebt"] if byb else None, ref_b)], True),
        tile("Ventes nettes cumulées", kmoney(gy["ventes"]), [delta_line(gy["ventes"], gyb["ventes"], str(y - 1))]),
        tile("Profit brut cumulatif", kmoney(gy["pb"]), [delta_line(gy["pb"], gyb["pb"], str(y - 1))]),
    ])
    bullets = "".join(f"<li>{b}</li>" for b in retenir(s, P, marks))
    return f"""
      <div class="eyebrow">Sommaire</div>
      <h1>L'essentiel {de(m)} {y}</h1>
      <div class="band-lab">Le mois <span>{MOIS[m]} {y} comparé à {MOIS[m]} {y-1}</span></div>
      <div class="tiles">{t1}</div>
      <div class="band-lab">Depuis janvier <span>cumul {MOIS[1]}–{MOIS[m]} {y} comparé à la même période {y-1}</span></div>
      <div class="tiles">{t2}</div>
      <h2>Ce qu'il faut retenir</h2>
      <ul class="retenir">{bullets}</ul>
      <div class="note">¹ Budget : {' + '.join(DEALERS[x] for x in inc) if inc else 'aucune concession'} seulement (seules concessions qui ont un budget {y}).</div>"""


def p_alertes(s, P, part, idx):
    rows = "".join(f'<tr><td class="lvlc">{level_chip(lv)}</td><td class="dn">{escape(DEALERS[d])}</td><td>{escape(t)}</td></tr>' for d, lv, t in part)
    legend = " ".join(level_chip(l) for l in ("critique", "eleve", "attention", "positif"))
    return f"""
      <div class="eyebrow">Sommaire</div>
      <h1>Alertes du mois{f' ({idx[0]}/{idx[1]})' if idx[1] > 1 else ''}</h1>
      {key("Les alertes signalent les écarts qui dépassent les seuils du Groupe (voir la page Méthode). Elles sont classées de la plus grave à la plus positive.", "Comment lire")}
      <div class="legend-lvl">{legend}</div>
      <table class="t alerts"><tbody>{rows}</tbody></table>"""


def p_resultats(s, P, mode):
    y, m = split(P)
    r, b, inc = group_pair(s, P, mode, "ap")
    foot, note, nc = gpa_notes(s, P, inc, mode)
    d = r["ebt"] - b["ebt"]
    lab_r = f"{mois_court(m)} {y}" if mode == "month" else f"Cumul {y}"
    lab_b = f"{mois_court(m)} {y-1}" if mode == "month" else f"Cumul {y-1}"
    table = comp_table(KEY_ROWS, [{"h": lab_r, "t": "v", "c": r}, {"h": lab_b, "t": "v", "c": b, "vcls": "muted"},
                                  {"h": "Écart", "t": "d", "c": (r, b), "cls": "sep", "nc": nc}, {"h": "%", "t": "p", "c": (r, b), "nc": nc}], foot=foot)
    titre = f"Résultats du groupe — {MOIS[m]} {y}" if mode == "month" else f"Résultats cumulatifs — {MOIS[1]} à {MOIS[m]} {y}"
    ref = f"{MOIS[m]} {y-1}" if mode == "month" else f"la même période de {y-1}"
    k = (f"L'EBT du groupe est de <b>{kmoney(r['ebt'])}</b>, soit <b>{kmoney(d, sign=True)}</b> ({pct(var_pct(r['ebt'], b['ebt']), 0, sign=True)}) "
         f"par rapport à {ref}. Le profit brut varie de {kmoney(r['pb'] - b['pb'], sign=True)} et les dépenses de {kmoney(r['dep'] - b['dep'], sign=True)}.")
    extra = ""
    if mode == "ytd":
        br, bb, incb = group_pair(s, P, "ytd", "budget")
        if incb:
            bt = comp_table(BUDGET_ROWS, [{"h": "Réel", "t": "v", "c": br}, {"h": "Budget", "t": "v", "c": bb, "vcls": "muted"},
                                          {"h": "Écart", "t": "d", "c": (br, bb), "cls": "sep"}, {"h": "%", "t": "p", "c": (br, bb)}])
            extra = (f"<h2>Comparaison au budget — {' + '.join(DEALERS[x] for x in incb)}</h2>{bt}"
                     f"<div class='note'>Seules ces concessions ont un budget {y}. Les autres s'ajouteront dès que leur budget sera saisi dans budgets.csv.</div>")
    rec = [DEALERS[x] for x in inc if s.ap_source(x, P, mode) == "reconstitue"]
    rec_note = f" L'an passé de {', '.join(rec)} est reconstitué à partir de ses fichiers {y-1}." if rec else ""
    return f"""
      <div class="eyebrow">Performance du groupe</div>
      <h1>{escape(titre)}</h1>
      {key(k)}
      {table}
      <div class="note">Vert = favorable ; pour les dépenses, vert = plus basses.{rec_note} {note}</div>
      {extra}"""


def p_pont(s, P, mode):
    y, m = split(P)
    r, b, _ = group_pair(s, P, mode, "ap")
    br = group_bridge(s, P, mode, "ap")
    st = f"EBT\n{mois_court(m)} {y-1}" if mode == "month" else f"EBT cumul\n{y-1}"
    en = f"EBT\n{mois_court(m)} {y}" if mode == "month" else f"EBT cumul\n{y}"
    svg = waterfall((st, b["ebt"]), fam_items(br), (en, r["ebt"]), width=672, height=300)
    top = sorted([(k, v) for k, v in br.items() if abs(v) >= 1000], key=lambda kv: -abs(kv[1]))[:6]
    labels = dict((k, l) for k, l, _ in BRIDGE_ITEMS)
    rows = "".join(f'<tr><td class="lab">{escape(labels[k].replace("¹", ""))}</td><td class="{"pos" if v > 0 else "neg"}">{kmoney(v, sign=True)}</td>'
                   f'<td class="lab muted">{"favorable" if v > 0 else "défavorable"}</td></tr>' for k, v in top)
    titre = f"D'où vient l'écart d'EBT — {MOIS[m]} {y}" if mode == "month" else f"D'où vient l'écart d'EBT — cumul {y}"
    ref = f"{MOIS[m]} {y-1}" if mode == "month" else str(y - 1)
    return f"""
      <div class="eyebrow">Analyse des écarts</div>
      <h1>{escape(titre)}</h1>
      {key(escape(commentaire_ecart('Le groupe', r, b, br, 'ap', P, mode)))}
      <div class="chart-sub">Chaque barre montre ce qu'un poste ajoute (vert) ou retire (rouge) à l'EBT par rapport à {ref}.
      La somme des barres égale l'écart. Des dépenses plus basses apparaissent en vert.</div>
      <div class="chart">{svg}</div>
      <h2>Les postes qui pèsent le plus</h2>
      <table class="t num"><thead><tr><th class="lab">Poste</th><th>Effet sur l'EBT</th><th class="lab"></th></tr></thead><tbody>{rows}</tbody></table>
      <div class="note">Effet volume = écart d'unités × profit par unité de l'an passé ; effet profit par unité = écart de profit par unité × unités vendues.
      Le pont du groupe additionne ceux des concessions, ce qui neutralise l'effet de mix entre concessions.</div>"""


def p_compo(s, P, what):
    y, m = split(P)
    r, b, _ = group_pair(s, P, "ytd", "ap")
    items = PB_ITEMS if what == "pb" else DEP_ITEMS
    k = rc.compo_message(r, b, items, y, "du profit brut" if what == "pb" else "des dépenses")
    titre = "Composition du profit brut" if what == "pb" else "Composition des dépenses"
    return f"""
      <div class="eyebrow">Analyse opérationnelle</div>
      <h1>{titre} — cumul {MOIS[1]} à {MOIS[m]}</h1>
      {key(k)}
      {donut_block(items, b, r, f"Cumul {y-1}", f"Cumul {y}")}"""


def p_concessions(s, P):
    y, m = split(P)
    ebt_y = {d: s.comp(d, P, "ytd", "real")["ebt"] for d in rc.ACTIVE}
    rk_y = rank(ebt_y)
    rows = ""
    for d in sorted(rc.ACTIVE, key=lambda x: rk_y[x]):
        r, a, bb = s.comp(d, P, "ytd", "real"), s.comp(d, P, "ytd", "ap"), s.comp(d, P, "ytd", "budget")
        vp = var_pct(r["ebt"], a["ebt"]) if a else None
        vb = var_pct(r["ebt"], bb["ebt"]) if bb else None
        lab, cls = statut(vp)
        da = (r["ebt"] - a["ebt"]) if a else None
        rows += (f'<tr><td class="c">{rk_y[d]}</td><td class="lab"><b>{escape(DEALERS[d])}</b></td><td>{num(r["ebt"]/1000)}</td>'
                 f'<td class="{cls_delta((da or 0)/1000, "money", 0.5)}">{num(da/1000, sign=True) if da is not None else "—"}</td>'
                 f'<td class="{cls_delta(vp, "money")}">{pct(vp, 0, sign=True) if vp is not None else "—"}</td>'
                 f'<td class="{cls_delta(vb, "money") if vb is not None else "muted"}">{pct(vb, 0, sign=True) if vb is not None else "n/d"}</td>'
                 f'<td class="c">{chip(lab, cls)}</td></tr>')
    pos = [(DEALERS[d], ebt_y[d]) for d in rc.ACTIVE if ebt_y[d] > 0]
    tot = sum(v for _, v in pos) or 1
    sl = [(lab, v, CAT[i % len(CAT)]) for i, (lab, v) in enumerate(pos)]
    dn = donut(sl, kmoney(tot), f"EBT cumul {y}", 250)
    leg = "".join(f'<div><span class="sw" style="background:{c}"></span>{escape(l)} — {pct(v / tot, 0)}</div>' for l, v, c in sl)
    bars = paired_hbars([(DEALERS[d], (s.comp(d, P, "ytd", "ap") or {}).get("ebt"), ebt_y[d], None) for d in rc.ACTIVE], 320, 108, str(y - 1), str(y))
    best = max(rc.ACTIVE, key=lambda d: ebt_y[d])
    neg = [DEALERS[d] for d in rc.ACTIVE if ebt_y[d] <= 0]
    k = (f"{escape(DEALERS[best])} génère la plus grande part de l'EBT cumulatif du groupe ({pct(ebt_y[best] / tot, 0)}). "
         f"Le statut compare l'EBT cumulatif à celui de {y-1}.")
    return f"""
      <div class="eyebrow">Concessions</div>
      <h1>Résultats par concession — cumul {y}</h1>
      {key(k)}
      <table class="t num rank"><thead><tr><th class="c">Rang</th><th class="lab">Concession</th><th>EBT cumul (k$)</th><th>vs {y-1} (k$)</th>
        <th>vs {y-1}</th><th>vs budget</th><th class="c">Statut</th></tr></thead><tbody>{rows}</tbody></table>
      <div class="note">Statut : En croissance ≥ +10 % · Stable −5 % à +10 % · À surveiller −20 % à −5 % · Prioritaire &lt; −20 %.</div>
      <div class="two" style="margin-top:16px">
        <div><div class="chart-title">Part de l'EBT cumulatif du groupe</div>{dn}<div class="note">{leg}{('Non représentées (EBT négatif) : ' + ', '.join(neg)) if neg else ''}</div></div>
        <div><div class="chart-title">EBT cumulatif {y-1} et {y}</div>{bars}</div>
      </div>"""


def p_heat(s, P):
    y, m = split(P)
    rows = []
    for d in rc.ACTIVE:
        r, b = s.comp(d, P, "ytd", "real"), s.comp(d, P, "ytd", "ap")
        rows.append((DEALERS[d], bridge(r, b) if b else None, (r["ebt"] - b["ebt"]) if b else None, False))
    gr, gb, _ = group_pair(s, P, "ytd", "ap")
    rows.append(("Groupe", group_bridge(s, P, "ytd", "ap"), gr["ebt"] - gb["ebt"], True))
    vmax = max([abs(v) for _, b, _, _ in rows if b for v in bridge_families(b).values()] + [1])
    tmax = max([abs(t) for _, _, t, _ in rows if t is not None] + [1])
    head = "".join(f"<th>{escape(FAMILY_SHORT[f])}</th>" for f in BRIDGE_FAMILIES) + "<th class='tot'>Écart d'EBT</th>"
    body = ""
    for name, b, tot, is_g in rows:
        if not b:
            body += f'<tr><td class="lab">{escape(name)}</td>' + "<td class='muted'>—</td>" * (len(BRIDGE_FAMILIES) + 1) + "</tr>"
            continue
        tds = "".join(f'<td style="{heat_color(v, vmax)}">{num(v/1000, sign=True)}</td>' for v in bridge_families(b).values())
        tds += f'<td class="tot" style="{heat_color(tot, tmax)}"><b>{num(tot/1000, sign=True)}</b></td>'
        body += f'<tr class="{"total strong" if is_g else ""}"><td class="lab">{escape(name)}</td>{tds}</tr>'
    return f"""
      <div class="eyebrow">Concessions</div>
      <h1>D'où viennent les écarts, concession par concession</h1>
      {key(f"Chaque case montre ce qu'un poste ajoute (vert) ou retire (rouge) à l'EBT cumulatif de la concession par rapport à {y-1}, en k$. "
           f"Plus la couleur est foncée, plus l'effet est grand. La dernière colonne est l'écart total.", "Comment lire")}
      <table class="t num heat"><thead><tr><th class="lab">Cumul {y} vs {y-1} (k$)</th>{head}</tr></thead><tbody>{body}</tbody></table>
      <div class="note">Le détail du mois, poste par poste, se trouve dans le rapport de chaque concession.</div>"""


def ind_table(s, P, deltas=False):
    y, m = split(P)
    cols = list(rc.ACTIVE) + ["groupe"]
    gy, gyb, _ = group_pair(s, P, "ytd", "ap")
    comps = {d: (s.comp(d, P, "ytd", "real"), s.comp(d, P, "ytd", "ap")) for d in rc.ACTIVE}
    comps["groupe"] = (gy, gyb)
    body = ""
    for k, lab, kind in IND_ROWS:
        tds = ""
        for c in cols:
            r, a = comps[c]
            rv = ratios(r).get(k)
            av = ratios(a).get(k) if a else None
            unrel = k in ("gpa_neuf", "gpa_usage", "ebt_unite", "ratio_usage_neuf") and \
                bool(unreliable_ap(s, P, "ytd", [c] if c != "groupe" else rc.ACTIVE, "gpa_neuf" if k == "gpa_neuf" else "gpa_usage"))
            g = "g " if c == "groupe" else ""
            if not deltas:
                tds += f'<td class="{g}">{fmt_val(rv, kind)}</td>'
                continue
            if unrel or av is None or rv is None:
                tds += f'<td class="{g}muted">{"n.c.¹" if unrel else "—"}</td>'
                continue
            if kind in ("ratio", "ratio_inv"):
                t, cl = pts(rv - av, 1), cls_delta(rv - av, kind)
            elif kind == "ratio_x":
                t, cl = num(rv - av, 2, sign=True), ""
            else:
                vp = var_pct(rv, av)
                t, cl = (pct(vp, 0, sign=True) if vp is not None else "—"), cls_delta(vp, "money")
            tds += f'<td class="{g}{cl}">{t}</td>'
        body += f'<tr><td class="lab">{escape(lab)}</td>{tds}</tr>'
    heads = "".join(f"<th>{escape(DEALER_SHORT[d])}</th>" for d in rc.ACTIVE) + '<th class="g">Groupe</th>'
    return f'<table class="t num ind"><thead><tr><th class="lab">Cumul {mois_court(1)}–{mois_court(m)} {y}</th>{heads}</tr></thead><tbody>{body}</tbody></table>'


def p_ind(s, P, deltas):
    y, m = split(P)
    if not deltas:
        return f"""
      <div class="eyebrow">Indicateurs de gestion</div>
      <h1>Indicateurs de gestion — cumul {y}</h1>
      {key("Les mêmes ratios pour chaque concession, calculés sur le cumul de l'année. La colonne Groupe est recalculée à partir des sommes.", "Comment lire")}
      {ind_table(s, P, False)}
      <h2>Définitions</h2>
      <dl class="defs">
        <dt>Taux d'absorption après-vente</dt><dd>Profit brut service + pièces + carrosserie ÷ (dépenses totales − dépenses variables). Plus il est haut, plus l'après-vente couvre les frais fixes.</dd>
        <dt>Part de l'après-vente dans le PB</dt><dd>Profit brut service + pièces + carrosserie ÷ profit brut total.</dd>
        <dt>Dépenses % du PB</dt><dd>Dépenses totales ÷ profit brut. Au-delà de 100 %, l'EBT repose sur les autres revenus.</dd>
        <dt>EBT par unité détail</dt><dd>EBT ÷ (unités neuves + unités usagées).</dd>
      </dl>"""
    return f"""
      <div class="eyebrow">Indicateurs de gestion</div>
      <h1>Indicateurs de gestion — variation vs {y-1}</h1>
      {key(f"Écart de chaque indicateur par rapport au cumul {y-1} : en points (pts) pour les pourcentages, en % pour les montants par unité. Vert = amélioration.", "Comment lire")}
      {ind_table(s, P, True)}
      <div class="note">¹ n.c. : non comparable, les unités de l'an passé semblent incomplètes (voir la page Qualité des données).</div>"""


def p_tendances(s, P):
    y, m = split(P)
    labels = [MOIS[i][0].upper() for i in range(1, m + 1)]
    cards = []
    gv, ga = [], []
    for i in range(1, m + 1):
        p = pkey(y, i)
        cs = [s.comp(d, p, "month", "real") for d in rc.ACTIVE]
        ca = [s.comp(d, p, "month", "ap") for d in rc.ACTIVE]
        gv.append(sum(c["ebt"] for c in cs) if all(cs) else None)
        ga.append(sum(c["ebt"] for c in ca) if all(cs) and all(ca) else None)
    cards.append((f"Groupe ({len(rc.ACTIVE)} concessions)", monthly_bars(gv, ga, labels, 322, 140), "Mois où toutes les concessions ont des données."))
    for d in rc.ACTIVE:
        vals, aps, partial = [], [], set()
        for i in range(1, m + 1):
            p = pkey(y, i)
            c, a = s.comp(d, p, "month", "real"), s.comp(d, p, "month", "ap")
            vals.append(c["ebt"] if c else None)
            aps.append(a["ebt"] if a else None)
            if c and s._native_section(d, p, "month") is None:
                partial.add(i - 1)
        ok = [(v, i) for i, v in enumerate(vals) if v is not None]
        best, worst = max(ok), min(ok)
        txt = f"Meilleur mois : {MOIS[best[1]+1]} ({kmoney(best[0])}) · plus faible : {MOIS[worst[1]+1]} ({kmoney(worst[0])})"
        cards.append((DEALERS[d], monthly_bars(vals, aps, labels, 322, 140, partial=partial), txt))
    grid = "".join(f'<div class="sm"><div class="smh">{escape(t)}</div>{svg}<div class="smn">{escape(tx)}</div></div>' for t, svg, tx in cards)
    return f"""
      <div class="eyebrow">Tendances</div>
      <h1>EBT mois par mois — {y}</h1>
      <div class="legend"><span class="lg-bar"></span> EBT {y} <span class="lg-tick"></span> EBT {y-1}, même mois <span class="lg-hatch"></span> mois reconstitué</div>
      <div class="smgrid">{grid}</div>
      <div class="note">Chaque graphique a sa propre échelle.</div>"""


def p_tendances_table(s, P):
    y, m = split(P)
    ab = (lambda i: mois_court(i)) if m <= 8 else (lambda i: MOIS[i][:3] + ("." if len(MOIS[i]) > 3 else ""))
    head = "".join(f"<th>{ab(i)}</th>" for i in range(1, m + 1))
    out = ""
    g, _, _ = group_pair(s, P, "ytd", "ap")
    for k, titre in (("ebt", "EBT mensuel"), ("pb", "Profit brut mensuel")):
        trs, tot, ok = "", [0.0] * m, [True] * m
        for d in rc.ACTIVE:
            tds = ""
            for i in range(1, m + 1):
                p = pkey(y, i)
                c = s.comp(d, p, "month", "real")
                if c:
                    tot[i - 1] += c[k]
                    star = "*" if s._native_section(d, p, "month") is None else ""
                    tds += f'<td class="{"neg" if c[k] < 0 else ""}">{num(c[k]/1000)}{star}</td>'
                else:
                    ok[i - 1] = False
                    tds += '<td class="muted">n/d</td>'
            r = s.comp(d, P, "ytd", "real")
            trs += f'<tr><td class="lab">{escape(DEALER_SHORT[d])}</td>{tds}<td class="sep"><b>{num(r[k]/1000)}</b></td></tr>'
        gtd = "".join(f"<td>{num(t/1000) if o else '—'}</td>" for t, o in zip(tot, ok))
        trs += f'<tr class="total strong"><td class="lab">Groupe</td>{gtd}<td class="sep">{num(g[k]/1000)}</td></tr>'
        out += (f'<h2>{titre} {y} (k$)</h2><table class="t num trend{" wide" if m > 8 else ""}"><thead><tr><th class="lab"></th>{head}'
                f'<th class="sep">Cumul</th></tr></thead><tbody>{trs}</tbody></table>')
    return f"""
      <div class="eyebrow">Tendances</div>
      <h1>Détail mensuel {y}</h1>
      {out}
      <div class="note">* mois reconstitué à partir des cumuls. Le cumul peut différer de la somme des mois quand des révisions sont passées sur des mois antérieurs.
      Groupe : « — » quand une concession n'a pas de données ce mois-là.</div>"""


def p_couverture(s, P, couverture):
    y, m = split(P)
    ok = lambda b: f'<span class="ok">{icon("positif", 10)} Oui</span>' if b else f'<span class="no">{icon("manque", 10)} Non</span>'
    rows = ""
    for d, c in couverture.items():
        bsrc = {"natif": ok(True), "csv": '<span class="ok">budgets.csv</span>', None: ok(False)}[c["budget"]]
        asrc = {"natif": ok(True), "reconstitue": f'<span class="rec">{icon("info", 10)} Reconstituée</span>', None: ok(False)}[c["ap"]]
        runs = []
        for p in c["mois_manquants"]:
            i = split(p)[1]
            if runs and runs[-1][1] == i - 1:
                runs[-1][1] = i
            else:
                runs.append([i, i])
        mtxt = ", ".join(mois_court(a) if a == b else f"{mois_court(a)}–{mois_court(b)}" for a, b in runs) or "Aucun"
        rev = c["revisions"]
        rtxt = kmoney(rev["ebt"], sign=True) if rev and abs(rev["ebt"]) >= 1000 else ("—" if rev is None else "Aucune")
        rows += (f'<tr><td class="lab"><b>{escape(DEALERS[d])}</b></td><td class="c">{ok(c["reel_mois"] and c["reel_cumul"])}</td>'
                 f'<td class="c">{asrc}</td><td class="c">{bsrc}</td><td class="c">{mtxt}</td><td class="c">{rtxt}</td></tr>')
    derived = "".join(f"<li>{escape(DEALERS[d])} — {escape(label_period(p))} : {escape(t)}</li>" for d, p, t in s.notes)
    return f"""
      <div class="eyebrow">Qualité des données</div>
      <h1>Couverture des données — {escape(label_period(P))}</h1>
      {key("Ce tableau indique, pour chaque concession, ce que le rapport a pu comparer. Les points à régler sont listés aux pages suivantes.", "Comment lire")}
      <table class="t cov"><thead><tr><th class="lab">Concession</th><th class="c">Résultats du mois</th><th class="c">An passé</th>
        <th class="c">Budget {y}</th><th class="c">Mois {y} absents</th><th class="c">Révision du cumul (EBT)</th></tr></thead><tbody>{rows}</tbody></table>
      <div class="note">Révision du cumul = cumul {de(m)} − cumul {de(m - 1) if m > 1 else ''} − mois {de(m)} : écritures passées sur des mois antérieurs.</div>
      {('<h2>Valeurs reconstituées dans ce rapport</h2><ul class="retenir">' + derived + '</ul>') if derived else ''}"""


def issues_html(items, with_dealer=True):
    out = ""
    for d, lv, t, a in items:
        out += (f'<div class="issue"><div>{level_chip(lv)}</div><div class="dn">{escape(DEALERS[d]) if with_dealer else ""}</div>'
                f'<div><div class="what">{escape(t)}</div><div class="act">Action : {escape(a)}</div></div></div>')
    return out


def p_points(part, idx):
    return f"""
      <div class="eyebrow">Qualité des données</div>
      <h1>Points à régler{f' ({idx[0]}/{idx[1]})' if idx[1] > 1 else ''}</h1>
      {key("Chaque point décrit un manque ou une anomalie dans les fichiers sources et l'action qui le règle pour les prochains mois.", "Comment lire") if idx[0] == 1 else ''}
      {issues_html(part)}"""


def p_methode(part):
    if part == 1:
        return """
      <div class="eyebrow">Annexe</div>
      <h1>Méthode</h1>
      <h2>Sources</h2>
      <p>Toutes les valeurs viennent du tableau de bord KPI, qui lit les fichiers « Réalisé » de chaque concession (gabarit financier standard du Groupe ;
      relevé GM Canada pour HAWKS). Montants en k$ (milliers de dollars) sauf indication. Non audité.</p>
      <h2>Comparaisons</h2>
      <p><b>An passé.</b> Colonne « année précédente » du fichier. Quand elle manque (HAWKS), le rapport prend le même mois — ou le même cumul — dans les fichiers
      de l'an passé déjà versés au tableau de bord.</p>
      <p><b>Budget.</b> Colonne budget du fichier ; un budget à zéro est considéré comme non saisi. Un budget peut être ajouté dans budgets.csv ; le cumul budgété
      est alors la somme des mois.</p>
      <p><b>Périmètre comparable.</b> Un écart du groupe n'additionne que les concessions qui ont la base de comparaison. Les ratios du groupe sont recalculés
      à partir des sommes, jamais additionnés.</p>
      <h2>Écart d'EBT</h2>
      <p>EBT = profit brut + autres revenus − dépenses − éléments sous le BAIIA (amortissement, etc.). L'écart d'EBT est réparti entre ces postes ; la somme des barres
      du graphique égale exactement l'écart. Pour les véhicules, l'écart de profit brut est séparé en effet volume (écart d'unités × profit par unité de l'an passé)
      et effet profit par unité (écart de profit par unité × unités vendues).</p>
      <p>Chez HAWKS, l'amortissement est compris dans les dépenses du relevé GM ; son poste « amortissement » est donc nul.</p>
      <h2>Graphiques en anneau</h2>
      <p>Chaque part montre le poids d'un département ou d'une catégorie dans le total. Un montant négatif (crédit net) ne peut pas être dessiné : il figure dans
      le tableau sous l'anneau, et les pourcentages portent alors sur les montants positifs.</p>"""
    st = " · ".join(f"{lab} : {'≥ ' + pct(sv, 0, sign=True) if sv > -1 else '< ' + pct(STATUTS[-2][0], 0, sign=True)}" for sv, lab, _ in STATUTS)
    return f"""
      <div class="eyebrow">Annexe</div>
      <h1>Définitions et seuils</h1>
      <h2>Indicateurs</h2>
      <dl class="defs">
        <dt>Marge brute</dt><dd>Profit brut ÷ ventes nettes.</dd>
        <dt>Profit brut par unité</dt><dd>Profit brut du département ÷ unités vendues (neuves ou usagées).</dd>
        <dt>Autres sources de profit brut</dt><dd>Profit brut total − somme des cinq départements (gros, F&amp;I, divers).</dd>
        <dt>Taux d'absorption après-vente</dt><dd>Profit brut service + pièces + carrosserie ÷ (dépenses totales − dépenses variables).</dd>
        <dt>Dépenses % du profit brut</dt><dd>Dépenses totales ÷ profit brut.</dd>
        <dt>EBT des 12 derniers mois</dt><dd>Somme des 12 derniers EBT mensuels (n/d s'il manque un mois).</dd>
      </dl>
      <h2>Statuts</h2>
      <p>Selon l'EBT cumulatif vs l'an passé : {escape(st)}.</p>
      <h2>Seuils des alertes</h2>
      <dl class="defs">
        <dt>{level_chip('critique')}</dt><dd>EBT du mois négatif.</dd>
        <dt>{level_chip('eleve')}</dt><dd>EBT cumulatif sous l'an passé de plus de {pct(-SEUILS['ebt_cumul_ap_pct'], 0)} et de {kmoney(-SEUILS['ebt_cumul_ap_abs'])}, ou sous le budget de plus de {pct(-SEUILS['ebt_cumul_budget_pct'], 0)}.</dd>
        <dt>{level_chip('attention')}</dt><dd>EBT du mois sous l'an passé de plus de {pct(-SEUILS['ebt_mois_ap_pct'], 0)} et de {kmoney(-SEUILS['ebt_mois_ap_abs'])} ; dépenses supérieures au profit brut ;
        profit par unité neuve en baisse de plus de {pct(-SEUILS['gpa_neuf_pct'], 0)} ou usagée de plus de {pct(-SEUILS['gpa_usage_pct'], 0)} ; personnel % du PB en hausse de plus de {num(SEUILS['pers_pct_pb_pts'] * 100)} pts.</dd>
        <dt>{level_chip('positif')}</dt><dd>EBT cumulatif au-dessus de l'an passé de plus de {pct(SEUILS['positif_ap_pct'], 0)} ou du budget de plus de {pct(SEUILS['positif_budget_pct'], 0)}.</dd>
      </dl>
      <p class="note">Ces seuils sont des conventions de présentation (réglables dans kpi_analyse.py), pas une politique du Groupe.</p>"""


# ============================================================== assemblage
def build_book(s, P, marks):
    al = alertes(s, P)
    couverture, anomalies = controle_donnees(s, P)
    bk = Book()
    toc = [("L'essentiel du mois", marks.get("essentiel", "")), ("Alertes", marks.get("alertes", "")),
           ("Résultats du groupe", marks.get("resultats", "")), ("Analyse des écarts", marks.get("pont", "")),
           ("Composition du profit brut et des dépenses", marks.get("compo", "")), ("Résultats par concession", marks.get("concessions", "")),
           ("Indicateurs de gestion", marks.get("ind", "")), ("Tendances", marks.get("tend", "")),
           ("Qualité des données", marks.get("qualite", "")), ("Méthode", marks.get("methode", ""))]
    bk.add_cover(p_cover(s, P, toc))
    bk.mark("essentiel"); bk.add(p_essentiel(s, P, marks))
    parts = chunks(al, 16)
    bk.mark("alertes")
    for i, part in enumerate(parts):
        bk.add(p_alertes(s, P, part, (i + 1, len(parts))))
    bk.mark("resultats"); bk.add(p_resultats(s, P, "month")); bk.add(p_resultats(s, P, "ytd"))
    bk.mark("pont"); bk.add(p_pont(s, P, "month")); bk.add(p_pont(s, P, "ytd"))
    bk.mark("compo"); bk.add(p_compo(s, P, "pb")); bk.add(p_compo(s, P, "dep"))
    bk.mark("concessions"); bk.add(p_concessions(s, P)); bk.add(p_heat(s, P))
    bk.mark("ind"); bk.add(p_ind(s, P, False)); bk.add(p_ind(s, P, True))
    bk.mark("tend"); bk.add(p_tendances(s, P)); bk.add(p_tendances_table(s, P))
    bk.mark("qualite"); bk.add(p_couverture(s, P, couverture))
    iparts = chunks(anomalies, 8)
    for i, part in enumerate(iparts):
        bk.add(p_points(part, (i + 1, len(iparts))))
    bk.mark("methode"); bk.add(p_methode(1)); bk.add(p_methode(2))
    return bk


def build_html(s, P):
    rc.setup(s, P)
    rc.FOOTER_LABEL = ""
    marks = build_book(s, P, {}).marks          # 1re passe : numéros de page
    bk = build_book(s, P, marks)                 # 2e passe : renvois exacts
    return wrap_html(f"Groupe Automax — Rapport mensuel {rc.PERIOD_LABEL}", bk.pages), len(bk.pages)


# ============================================================== budget
BUDGET_LABELS = {
    "ventes_nettes": "Ventes nettes", "pb_total": "Profit brut total", "pb_neuf": "Profit brut — véhicules neufs",
    "pb_usage": "Profit brut — véhicules usagés", "pb_service": "Profit brut — service", "pb_carrosserie": "Profit brut — carrosserie",
    "pb_pieces": "Profit brut — pièces", "autres_revenus": "Autres revenus", "depenses": "Dépenses totales (positif)",
    "depenses_variables": "Dépenses variables (positif)", "depenses_personnel": "Dépenses de personnel (positif)",
    "depenses_semifixes": "Dépenses semi-fixes (positif)", "ebt": "EBT (profit net avant impôt)",
    "unites_neuf": "Unités neuves", "unites_usage": "Unités usagées", "unites_flottes": "Unités flottes",
}


def gabarit_budget(s, path, year):
    """Gabarit : une ligne par concession × indicateur, une colonne par mois (concessions sans budget natif)."""
    months = [pkey(year, i) for i in range(1, 13)]
    rows = []
    for d in DEALERS:
        if any(s.has_native_budget(d, p, "month") for p in s.periods(d) if p.startswith(str(year))):
            continue
        for k in BUDGET_CSV_KEYS:
            row = {"concession": d, "indicateur": k, "libelle": BUDGET_LABELS.get(k, k)}
            row.update({mm: "" for mm in months})
            rows.append(row)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["concession", "indicateur", "libelle"] + months)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description="Rapport mensuel KPI — Groupe Automax")
    ap.add_argument("--mois", help="AAAA-MM (défaut : dernier mois où toutes les concessions ont des données)")
    ap.add_argument("--data", default=os.path.join(HERE, "data.json"))
    ap.add_argument("--budget", default=os.path.join(HERE, "budgets.csv"))
    ap.add_argument("--sortie", help="Chemin du PDF")
    ap.add_argument("--garder-html", action="store_true")
    ap.add_argument("--gabarit-budget", help="Écrit un gabarit budgets.csv à remplir puis quitte")
    ap.add_argument("--annee", type=int, default=dt.date.today().year)
    a = ap.parse_args()
    s = Store(a.data, a.budget)
    if a.gabarit_budget:
        print(f"Gabarit écrit : {a.gabarit_budget} ({gabarit_budget(s, a.gabarit_budget, a.annee)} lignes)")
        return
    P = a.mois or max(set.intersection(*[set(s.periods(d)) for d in DEALERS]))
    out_pdf = a.sortie or os.path.join(HERE, f"Rapport_KPI_Groupe_Automax_{P}.pdf")
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    html, npages = build_html(s, P)
    html_path = os.path.splitext(out_pdf)[0] + ".html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    over = to_pdf(html_path, out_pdf)
    if not a.garder_html:
        os.remove(html_path)
    print(f"PDF : {out_pdf} ({npages} pages)")
    if over:
        print("ATTENTION — contenu qui déborde :", over)


if __name__ == "__main__":
    main()
