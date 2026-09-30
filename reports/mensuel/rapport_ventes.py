#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rapport « Ventes » — Groupe Automax (analyse approfondie des ventes de véhicules).

Demande de Maxime Allard (29 septembre 2026) : « fais un rapport détaillé pour
les ventes comme tu as fait pour les fixes ». Même principe que le rapport
« Opérations fixes » : neufs et usagés de chaque concession — unités, profit
véhicule et F&I par unité, gros / encan / export, F&I par produit, frais de
vente (commissions, publicité, intérêts sur stocks), profit départemental,
mix des modèles, comparaison aux composites, tendances sur 24 mois.

    python rapport_ventes.py --data ../../data/data.json --mois 2026-08 --sortie sortie
"""
import argparse
import os
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import rapport_commun as rc
from rapport_commun import key, tile, Book, wrap_html, to_pdf, LOGO_DARK
from kpi_data import Store, DEALERS, DEALER_SHORT, MOIS, pkey, split, prior_year, label_period
from kpi_analyse import money, kmoney, num, pct, pts, var_pct, de
from rapport_apres_vente import paired_bars, lines_chart, month_labels, DEALER_COLOR
import kpi_ventes as kv
from kpi_ventes import GROUP, metrics, both

DLAB = {"neuf": "Véhicules neufs", "usage": "Véhicules usagés"}
DSHORT = {"neuf": "neufs", "usage": "usagés"}
SOURCE_LABELS = {"gabarit": "Réalisé (gabarit du Groupe)", "etat_gm": "état financier GM Canada",
                 "etat_hyundai": "état financier Hyundai Canada", "etat_vw": "état financier Volkswagen Canada"}


# ------------------------------------------------------------------ formats
def fv(v, f):
    if v is None:
        return "—"
    if f == "$":
        return money(v)
    if f == "k":
        return kmoney(v)
    if f == "%":
        return pct(v, 1)
    if f == "x":
        return num(v, 2)
    return num(v)


def fdx(r, b, f, sens=1):
    """Écart (texte, classe) : % pour montants et volumes, points pour les % ; sens -1 = coût."""
    if r is None or b is None:
        return "", ""
    if f == "%":
        d = r - b
        return pts(d, 1), ("" if abs(d) < 0.0005 or sens == 0 else ("pos" if d * sens > 0 else "neg"))
    if f == "$" and (b <= 0 or r < 0):      # montants négatifs (crédits nets) : écart en dollars
        d = r - b
        return money(d, sign=True), ("" if abs(d) < 0.5 or sens == 0 else ("pos" if d * sens > 0 else "neg"))
    vp = var_pct(r, b)
    if vp is None:
        return "", ""
    return pct(vp, 0, sign=True), ("" if abs(vp) < 0.005 or sens == 0 else ("pos" if vp * sens > 0 else "neg"))


def cellv(r, b, f, sens=1, strong=False):
    t, c = fdx(r, b, f, sens)
    sub = f'<div class="dsub {c}">{t}</div>' if t else '<div class="dsub muted">&nbsp;</div>'
    return f'<td class="{"strong" if strong else ""}"><div>{fv(r, f)}</div>{sub}</td>'


def dl(d):
    return "Groupe" if d == GROUP else DEALERS[d]


def ds(d):
    return "Groupe" if d == GROUP else DEALER_SHORT[d]


class VS:
    """Accès commun des rapports Ventes (Groupe et concessions)."""

    def __init__(self, s, P):
        self.s = s
        self.V = kv.VStore(s)
        self.P = P
        self.y, self.m = split(P)
        self.dealers = self.V.dealers(P, "ytd")

    def pair(self, d, mode="ytd", P=None):
        P = P or self.P
        if d == GROUP:
            return (self.V.group(P, mode, "real", self.dealers, require="ap"),
                    self.V.group(P, mode, "ap", self.dealers, require="real"))
        return self.V.view(d, P, mode, "real"), self.V.view(d, P, mode, "ap")

    def real(self, d, mode="ytd", P=None):
        P = P or self.P
        if d == GROUP:
            return self.V.group(P, mode, "real", self.dealers)
        return self.V.view(d, P, mode, "real")

    def m2(self, d, suf, mode="ytd"):
        """(indicateurs réels, indicateurs an passé) d'un département."""
        r, a = self.pair(d, mode)
        return metrics((r or {}).get(suf)), metrics((a or {}).get(suf))

    def budget(self, d, mode="ytd"):
        return self.V.view(d, self.P, mode, "budget") if d != GROUP else None


# ------------------------------------------------------------------ constats
def findings(S, d=GROUP):
    """Constats chiffrés (cumul vs an passé), du plus important au moins important."""
    y = S.y
    out = []
    for suf in ("neuf", "usage"):
        r, a = S.m2(d, suf)
        if r.get("u") is None:
            continue
        t = f"<b>{DLAB[suf]} : {num(r['u'])} unités</b> au détail depuis janvier"
        if a.get("u"):
            t += f" ({num(r['u'] - a['u'], sign=True)}, {pct(var_pct(r['u'], a['u']), 0, sign=True)} vs {y-1})"
        if r.get("tot_u") is not None:
            t += (f" ; <b>{money(r['tot_u'])}</b> de profit par unité (véhicule {money(r.get('pbv_u'))} + F&I {money(r.get('fi_u'))})")
            if a.get("tot_u"):
                t += f", {money(r['tot_u'] - a['tot_u'], sign=True)} par unité vs {y-1}"
        out.append(t + ".")
    if d == GROUP:
        # concessions qui bougent le plus (unités neuves et usagées)
        for suf in ("neuf", "usage"):
            mv = []
            for x in S.dealers:
                r, a = S.m2(x, suf)
                if r.get("u") is not None and a.get("u"):
                    mv.append((r["u"] - a["u"], x))
            if mv:
                mv.sort()
                parts = ", ".join(f"{escape(DEALER_SHORT[x])} {num(dd, sign=True)}" for dd, x in mv)
                out.append(f"<b>Écart d'unités {DSHORT[suf]} par concession</b> : {parts}.")
    rn, an = S.m2(d, "neuf")
    ru, au = S.m2(d, "usage")
    gr = (rn.get("gros") or 0) + (ru.get("gros") or 0)
    ga = (an.get("gros") or 0) + (au.get("gros") or 0) if an.get("gros") is not None or au.get("gros") is not None else None
    if rn.get("gros") is not None or ru.get("gros") is not None:
        t = f"<b>Gros, encan, export et autres : {kmoney(gr)}</b> de profit brut depuis janvier"
        if ga is not None:
            t += f", {kmoney(gr - ga, sign=True)} vs {y-1}"
        out.append(t + " (montant à part : jamais divisé par les unités au détail).")
    if rn.get("comm_u") is not None or ru.get("comm_u") is not None:
        t = "<b>Commissions des vendeurs par unité</b> : "
        bits = []
        for suf, r, a in (("neufs", rn, an), ("usagés", ru, au)):
            if r.get("comm_u") is not None:
                b = f"{suf} {money(r['comm_u'])}"
                if a.get("comm_u"):
                    b += f" ({money(r['comm_u'] - a['comm_u'], sign=True)})"
                if r.get("comm_pct_pbv") is not None and r["comm_pct_pbv"] > 0:
                    b += f", soit {pct(r['comm_pct_pbv'], 0)} du profit véhicule"
                bits.append(b)
        out.append(t + " ; ".join(bits) + ".")
    return out


# ------------------------------------------------------------------ pages
def p_cover(S):
    y, m = S.y, S.m
    rn, an = S.m2(GROUP, "neuf")
    ru, au = S.m2(GROUP, "usage")
    r, a = S.pair(GROUP)
    br, ba = both(r), both(a)

    def dtxt(x, b, f="n"):
        t, _ = fdx(x, b, f)
        return f"{t} vs {y-1}" if t else f"{y-1} : n/d"
    return f"""
      <div class="logo cv-logo">{LOGO_DARK}</div>
      <div class="cv-mid">
        <div class="cv-kicker">Analyse approfondie · {escape(label_period(S.P))}</div>
        <div class="cv-title">Ventes de véhicules</div>
        <div class="cv-sub">Véhicules neufs et usagés des {len(S.dealers)} concessions : unités, profit véhicule et F&I par unité, gros, encan et
        export, F&I par produit, frais de vente, profit des départements, mix des modèles et tendances. Mois {de(m)} et cumul
        {MOIS[1]}–{MOIS[m]} {y}.</div>
        <div class="cv-kpis">
          <div><div class="cv-kl">Véhicules neufs {y}</div><div class="cv-kv">{num(rn.get('u'))}</div><div class="cv-kd">{escape(dtxt(rn.get('u'), an.get('u')))}</div></div>
          <div><div class="cv-kl">Véhicules usagés {y}</div><div class="cv-kv">{num(ru.get('u'))}</div><div class="cv-kd">{escape(dtxt(ru.get('u'), au.get('u')))}</div></div>
          <div><div class="cv-kl">Profit + F&I par unité</div><div class="cv-kv">{money(br.get('tot_u'))}</div><div class="cv-kd">{escape(dtxt(br.get('tot_u'), ba.get('tot_u'), '$'))}</div></div>
        </div>
      </div>
      <div class="cv-foot">
        <div>Groupe Automax · BMW Sherbrooke, Volkswagen Brossard, Sainte-Marie Automobile, Hyundai Longueuil, Hawkesbury Chevrolet Cadillac</div>
        <div>Préparé le {rc.PREPARED} à partir du tableau de bord KPI (Réalisés et états financiers des constructeurs) · Non audité</div>
        <div class="cv-conf">Confidentiel — usage interne — direction seulement</div>
      </div>"""


def dept_tiles(S, d, suf):
    r, a = S.m2(d, suf)
    y = S.y

    def lines(x, b, f, extra=None):
        t, c = fdx(x, b, f)
        out = [(f"{t} vs {y-1}" if t else f"{y-1} : n/d", c)]
        if extra:
            out.append((extra, "muted"))
        return out
    return "".join([
        tile(f"{DLAB[suf]} — unités", num(r.get("u")), lines(r.get("u"), a.get("u"), "n", f"{y-1} : {num(a.get('u'))}"), True),
        tile("Profit véhicule par unité", money(r.get("pbv_u")), lines(r.get("pbv_u"), a.get("pbv_u"), "$", f"{y-1} : {money(a.get('pbv_u'))}")),
        tile("F&I par unité", money(r.get("fi_u")), lines(r.get("fi_u"), a.get("fi_u"), "$", f"{y-1} : {money(a.get('fi_u'))}")),
    ])


def p_essentiel(S):
    y, m = S.y, S.m
    return f"""
      <div class="eyebrow">Sommaire</div>
      <h1>L'essentiel des ventes — {MOIS[m]} {y}</h1>
      {key(f"Cumul {MOIS[1]}–{MOIS[m]} {y} comparé à la même période {y-1}, concessions comparables. Unités au détail (neufs : avec démos et "
           "flottes) ; profit véhicule et F&I divisés par ces unités ; gros, encan et export à part.")}
      <div class="band-lab">Véhicules neufs <span>cumul {y}</span></div>
      <div class="tiles">{dept_tiles(S, GROUP, 'neuf')}</div>
      <div class="band-lab">Véhicules usagés <span>cumul {y}</span></div>
      <div class="tiles">{dept_tiles(S, GROUP, 'usage')}</div>
      <h2>Ce qu'il faut retenir</h2>
      <ul class="retenir">{''.join(f'<li>{t}</li>' for t in findings(S))}</ul>"""


def _dealer_rows(S, fn):
    rows = ""
    for d in S.dealers + [GROUP]:
        tds = fn(d)
        if tds is None:
            continue
        rows += f'<tr class="{"strong" if d == GROUP else ""}"><td class="lab">{escape(dl(d))}</td>{tds}</tr>'
    return rows


def p_overview(S):
    y, m = S.y, S.m

    def fn(d):
        rn, an = S.m2(d, "neuf")
        ru, au = S.m2(d, "usage")
        gr = None if rn.get("gros") is None and ru.get("gros") is None else (rn.get("gros") or 0) + (ru.get("gros") or 0)
        ga = None if an.get("gros") is None and au.get("gros") is None else (an.get("gros") or 0) + (au.get("gros") or 0)
        pbr = None if rn.get("pb") is None else (rn.get("pb") or 0) + (ru.get("pb") or 0)
        pba = None if an.get("pb") is None else (an.get("pb") or 0) + (au.get("pb") or 0)
        return (cellv(rn.get("u"), an.get("u"), "n") + cellv(rn.get("tot_u"), an.get("tot_u"), "$")
                + cellv(ru.get("u"), au.get("u"), "n") + cellv(ru.get("tot_u"), au.get("tot_u"), "$")
                + cellv(gr, ga, "k") + cellv(pbr, pba, "k", strong=True))
    rn, an = S.m2(GROUP, "neuf")
    ru, au = S.m2(GROUP, "usage")
    msg = (f"Depuis janvier, le Groupe a vendu <b>{num(rn.get('u'))}</b> véhicules neufs ({pct(var_pct(rn.get('u'), an.get('u')), 0, sign=True)}) et "
           f"<b>{num(ru.get('u'))}</b> usagés ({pct(var_pct(ru.get('u'), au.get('u')), 0, sign=True)}) au détail.")
    return f"""
      <div class="eyebrow">Vue d'ensemble</div>
      <h1>Ventes par concession — cumul {MOIS[1]}–{MOIS[m]} {y}</h1>
      {key(msg)}
      <table class="t num fo comp"><thead>
      <tr><th rowspan="2" class="lab">Concession</th><th colspan="2">Véhicules neufs</th><th colspan="2" class="sep">Véhicules usagés</th>
      <th rowspan="2" class="sep">Gros, encan,<br>export (k$)</th><th rowspan="2">Profit brut<br>véhicules (k$)</th></tr>
      <tr><th>Unités</th><th>Profit + F&I / u</th><th class="sep">Unités</th><th>Profit + F&I / u</th></tr></thead>
      <tbody>{_dealer_rows(S, fn)}</tbody></table>
      <div class="note">Sous chaque valeur : écart par rapport à {MOIS[1]}–{MOIS[m]} {y-1}. Profit + F&I par unité = (profit véhicule au détail + F&I) ÷ unités
      au détail. Profit brut véhicules = profit brut des départements neufs et usagés (détail, F&I, gros et autres). Groupe : concessions
      qui ont les chiffres de l'an passé.</div>"""


def p_dept(S, suf):
    y, m = S.y, S.m

    def fn(d):
        r, a = S.m2(d, suf)
        if r.get("u") is None:
            return None
        extra = (cellv(r.get("u_fl"), a.get("u_fl"), "n") if suf == "neuf" else cellv(r.get("gros"), a.get("gros"), "k"))
        return (cellv(r.get("u"), a.get("u"), "n") + cellv(r.get("pbv_u"), a.get("pbv_u"), "$") + cellv(r.get("fi_u"), a.get("fi_u"), "$")
                + cellv(r.get("tot_u"), a.get("tot_u"), "$", strong=True) + extra + cellv(r.get("pb"), a.get("pb"), "k"))
    bars = []
    for d in S.dealers + [GROUP]:
        r, a = S.m2(d, suf)
        bars.append((ds(d), a.get("tot_u"), r.get("tot_u")))
    r, a = S.m2(GROUP, suf)
    msg = (f"{DLAB[suf]} : <b>{money(r.get('tot_u'))}</b> de profit par unité depuis janvier (véhicule {money(r.get('pbv_u'))}, F&I "
           f"{money(r.get('fi_u'))}), contre {money(a.get('tot_u'))} en {y-1}.")
    col5 = "Dont flottes<br>(unités)" if suf == "neuf" else "Gros, encan,<br>export (k$)"
    return f"""
      <div class="eyebrow">{DLAB[suf]}</div>
      <h1>{DLAB[suf]} : volumes et profit par unité</h1>
      {key(msg)}
      <table class="t num fo comp"><thead><tr><th class="lab">Concession</th><th>Unités au détail</th><th>Profit véhicule / u</th>
      <th>F&I / u</th><th>Profit + F&I / u</th><th>{col5}</th><th>Profit brut du département (k$)</th></tr></thead>
      <tbody>{_dealer_rows(S, fn)}</tbody></table>
      <div class="chart-title">Profit + F&I par unité — {y-1} et {y}, cumul {MOIS[1]}–{MOIS[m]}</div>
      <div class="chart">{paired_bars(bars, "$", prev_label=str(y-1), cur_label=str(y))}</div>
      <div class="note">{"Neufs : unités au détail avec démos et flottes (profit véhicule des neufs : démos et flottes inclus). " if suf == "neuf" else
      "Usagés : unités au détail ; les ventes en gros, à l'encan et à l'export sont à part. "}Sous chaque valeur : écart par rapport à {y-1}.</div>"""


def p_fi(S):
    y, m = S.y, S.m

    def fn(d):
        rn, an = S.m2(d, "neuf")
        ru, au = S.m2(d, "usage")
        if rn.get("u") is None:
            return None
        fr = None if rn.get("fi") is None else (rn.get("fi") or 0) + (ru.get("fi") or 0)
        fa = None if an.get("fi") is None else (an.get("fi") or 0) + (au.get("fi") or 0)
        cf_r = None if rn.get("comm_fi") is None or not fr else ((rn.get("comm_fi") or 0) + (ru.get("comm_fi") or 0)) / fr
        cf_a = None if an.get("comm_fi") is None or not fa else ((an.get("comm_fi") or 0) + (au.get("comm_fi") or 0)) / fa
        return (cellv(rn.get("fi_u"), an.get("fi_u"), "$") + cellv(ru.get("fi_u"), au.get("fi_u"), "$")
                + cellv(fr, fa, "k", strong=True) + cellv(cf_r, cf_a, "%", sens=-1))
    # détail par produit (Réalisé du Groupe)
    prod = ""
    for d in S.dealers:
        r, a = S.pair(d)
        cells, ok = "", False
        for k in ("fi_fin", "fi_prot", "fi_aut"):
            vr = sum((metrics((r or {}).get(s_)).get(k) or 0) for s_ in ("neuf", "usage"))
            va = sum((metrics((a or {}).get(s_)).get(k) or 0) for s_ in ("neuf", "usage"))
            has = any(metrics((r or {}).get(s_)).get(k) is not None for s_ in ("neuf", "usage"))
            ok = ok or has
            has_a = any(metrics((a or {}).get(s_)).get(k) is not None for s_ in ("neuf", "usage"))
            cells += cellv(vr if has else None, va if has_a else None, "k")
        if ok:
            tot = sum((metrics((r or {}).get(s_)).get("fi_detail") or 0) for s_ in ("neuf", "usage"))
            prot = sum((metrics((r or {}).get(s_)).get("fi_prot") or 0) for s_ in ("neuf", "usage"))
            prod += (f'<tr><td class="lab">{escape(DEALERS[d])}</td>{cells}<td>{pct(prot / tot, 0) if tot else "—"}</td></tr>')
    rn, an = S.m2(GROUP, "neuf")
    ru, au = S.m2(GROUP, "usage")
    msg = (f"F&I par unité depuis janvier : <b>{money(rn.get('fi_u'))}</b> sur les neufs ({money((rn.get('fi_u') or 0) - (an.get('fi_u') or 0), sign=True)}) "
           f"et <b>{money(ru.get('fi_u'))}</b> sur les usagés ({money((ru.get('fi_u') or 0) - (au.get('fi_u') or 0), sign=True)}) vs {y-1}.")
    prod_tbl = (f'<div class="band-lab" style="margin-top:24px">F&I par produit <span>neufs + usagés, cumul {y} ; concessions dont le Réalisé détaille le F&I</span></div>'
                f'<table class="t num fo comp"><thead><tr><th class="lab">Concession</th><th>Financement (k$)</th><th>Protections (k$)</th>'
                f'<th>Autres produits (k$)</th><th>Part des protections</th></tr></thead><tbody>{prod}</tbody></table>') if prod else ""
    return f"""
      <div class="eyebrow">F&I</div>
      <h1>Financement et assurances (F&I)</h1>
      {key(msg)}
      <table class="t num fo comp"><thead><tr><th class="lab">Concession</th><th>F&I par unité neuve</th><th>F&I par unité usagée</th>
      <th>F&I total (k$)</th><th>Commissions F&I (% du F&I)</th></tr></thead>
      <tbody>{_dealer_rows(S, fn)}</tbody></table>
      {prod_tbl}
      <div class="note">F&I = revenus du bureau commercial (réserve de financement, protections, autres produits) ; état GM : transfert F&A ramené dans les
      départements. Commissions F&I : directeurs commerciaux (Réalisé : « Comm. F&I » ; état Hyundai : bureau commercial) ; non détaillées à l'état GM.
      Vert = commissions plus basses en % du F&I.</div>"""


FRAIS_COLS = [("comm_u", "Commissions vendeurs / u", "$", -1), ("pub_u", "Publicité nette / u", "$", -1),
              ("int_u", "Intérêts sur stocks nets / u", "$", -1), ("dep_pct_pb", "Dépenses (% du PB)", "%", -1),
              ("profit", "Profit du département (k$)", "k", 1)]


def frais_table(S, suf, dealers, label_fn=dl):
    rows = ""
    for d in dealers:
        r, a = S.m2(d, suf)
        if r.get("u") is None:
            continue
        tds = "".join(cellv(r.get(k), a.get(k), f, sens, strong=(k == "profit")) for k, _, f, sens in FRAIS_COLS)
        rows += f'<tr class="{"strong" if d == GROUP else ""}"><td class="lab">{escape(label_fn(d))}</td>{tds}</tr>'
    head = "".join(f"<th>{lab}</th>" for _, lab, _, _ in FRAIS_COLS)
    return f'<table class="t num fo comp"><thead><tr><th class="lab">Concession</th>{head}</tr></thead><tbody>{rows}</tbody></table>'


def p_frais(S, suf):
    y, m = S.y, S.m
    r, a = S.m2(GROUP, suf)
    msg = (f"{DLAB[suf]} : commissions des vendeurs de <b>{money(r.get('comm_u'))}</b> par unité depuis janvier"
           + (f" ({pct(r['comm_pct_pbv'], 0)} du profit véhicule)" if r.get("comm_pct_pbv") and r["comm_pct_pbv"] > 0 else "")
           + f" ; dépenses du département : <b>{pct(r.get('dep_pct_pb'), 0)}</b> du profit brut.")
    return f"""
      <div class="eyebrow">Frais de vente</div>
      <h1>{DLAB[suf]} : frais de vente et profit du département</h1>
      {key(msg)}
      {frais_table(S, suf, S.dealers + [GROUP])}
      <div class="note">Montants par unité au détail, cumul {MOIS[1]}–{MOIS[m]} {y} ; sous chaque valeur : écart vs {y-1} (vert = coût plus bas). Publicité nette des
      ristournes du constructeur ; intérêts sur stocks nets des crédits du constructeur (négatif = le crédit dépasse l'intérêt, fréquent à l'état GM).
      Dépenses et profit du département : chaque format répartit différemment les frais fixes (l'état Hyundai répartit loyer et frais indirects
      entre départements, l'état GM inscrit le loyer au département) — comparer une concession à elle-même d'une année à l'autre. Hyundai : an passé
      au Réalisé, lignes non comparées.</div>"""


def p_mix(S, suf):
    y, m = S.y, S.m
    blocks = ""
    for suf in (suf,):
        rows = ""
        for d in S.dealers:
            r, a = S.m2(d, suf)
            mix, mixa = r.get("mix") or {}, a.get("mix") or {}
            for i, (name, v) in enumerate(mix.items()):
                if not v["u"]:
                    continue
                va = mixa.get(name) or {}
                pu = v["pb"] / v["u"] if v["u"] else None
                pa = va.get("pb") / va.get("u") if va.get("u") else None
                rows += (f'<tr><td class="lab">{escape(DEALER_SHORT[d]) if i == 0 else ""}</td><td class="lab">{escape(name)}</td>'
                         f'{cellv(v["u"], va.get("u"), "n")}{cellv(pu, pa, "$")}</tr>')
        if rows:
            blocks += (f'<div class="band-lab" style="margin-top:14px">{DLAB[suf]} <span>cumul {y} · profit du véhicule au détail par ligne (sans F&I)</span></div>'
                       f'<table class="t num fo comp"><thead><tr><th class="lab">Concession</th><th class="lab">Ligne</th><th>Unités</th>'
                       f'<th>Profit véhicule / u</th></tr></thead><tbody>{rows}</tbody></table>')
    return f"""
      <div class="eyebrow">Mix</div>
      <h1>Mix des ventes au détail — {DSHORT[suf]}</h1>
      {key("Unités et profit véhicule par ligne de produits, tels que les fichiers les détaillent (autos, camions et VUS, électriques ; usagés certifiés ou non).", "Comment lire")}
      {blocks}
      <div class="note">Lignes des Réalisés et des états (état Hyundai : autos, camions, véhicules électriques, modèles fin de série). Les démos, flottes et
      échanges entre concessionnaires ne sont pas dans ces lignes. Sous chaque valeur : écart vs {y-1} quand la même ligne existe l'an passé.</div>"""


def p_gros(S):
    y, m = S.y, S.m

    def fn(d):
        rn, an = S.m2(d, "neuf")
        ru, au = S.m2(d, "usage")
        if rn.get("u") is None:
            return None
        tr = (rn.get("gros") or 0) + (ru.get("gros") or 0)
        ta = None if an.get("gros") is None and au.get("gros") is None else (an.get("gros") or 0) + (au.get("gros") or 0)
        return (cellv(rn.get("gros"), an.get("gros"), "k") + cellv(ru.get("gros"), au.get("gros"), "k")
                + cellv(tr, ta, "k", strong=True) + cellv(ru.get("gros_ligne_u"), au.get("gros_ligne_u"), "n")
                + cellv(ru.get("gros_pb_u"), au.get("gros_pb_u"), "$"))
    rn, an = S.m2(GROUP, "neuf")
    ru, au = S.m2(GROUP, "usage")
    tr = (rn.get("gros") or 0) + (ru.get("gros") or 0)
    ta = (an.get("gros") or 0) + (au.get("gros") or 0)
    return f"""
      <div class="eyebrow">Gros, encan et export</div>
      <h1>Gros, encan, export et autres</h1>
      {key(f"Depuis janvier : <b>{kmoney(tr)}</b> de profit brut hors détail, {kmoney(tr - ta, sign=True)} par rapport à {y-1}.")}
      <table class="t num fo comp"><thead><tr><th class="lab">Concession</th><th>Neufs (k$)</th><th>Usagés (k$)</th><th>Total (k$)</th>
      <th>Usagés vendus en gros (unités)</th><th>Profit par unité en gros</th></tr></thead>
      <tbody>{_dealer_rows(S, fn)}</tbody></table>
      <div class="note">Gros, encan, export et autres = profit brut du département − profit véhicule au détail − F&I : ventes en gros et à l'encan, export
      (STM, HAWKS), rachats de location, rectifications et rabais. Unités en gros : ligne « Ventes au gros » des fichiers (le profit par unité porte sur
      cette ligne seulement). Sous chaque valeur : écart vs {y-1}.</div>"""


def p_tendances(S):
    y, m = S.y, S.m
    labels = month_labels(S.P, 24)
    lab = [l for _, l in labels]
    charts = ""
    for suf, k, f, title in (("neuf", "u", "n", "Unités neuves au détail par mois"), ("usage", "u", "n", "Unités usagées au détail par mois"),
                             ("neuf", "tot_u", "$", "Profit + F&I par unité neuve"), ("usage", "tot_u", "$", "Profit + F&I par unité usagée")):
        series = []
        for d in S.dealers:
            vals = []
            for p, _ in labels:
                v = S.V.view(d, p, "month")
                vals.append(metrics(v[suf]).get(k) if v else None)
            series.append((d, vals))
        charts += f'<div class="sm"><div class="smh">{escape(title)}</div>{lines_chart(series, f, lab, width=318, height=150)}</div>'
    return f"""
      <div class="eyebrow">Tendances</div>
      <h1>Tendances sur 24 mois</h1>
      {key("Chaque concession mois par mois sur 24 mois : unités au détail et profit + F&I par unité. Les montants par unité d'un mois isolé varient "
           "beaucoup (ajustements de fin de mois, bonis) : lire la tendance, pas un point.", "Comment lire")}
      <div class="legend">{"".join(f'<span class="lgd"><span class="sw" style="background:{DEALER_COLOR[d]}"></span>{escape(DEALER_SHORT[d])}</span>' for d in S.dealers)}</div>
      <div class="smgrid">{charts}</div>"""


def p_detail_mensuel(S):
    y, m = S.y, S.m
    months = list(range(1, m + 1))
    head = "".join(f"<th>{escape(MOIS[i][:4] + '.' if len(MOIS[i]) > 4 else MOIS[i])}</th>" for i in months) + '<th class="sep">Cumul</th>'
    body = ""
    for suf in ("neuf", "usage"):
        body += f'<tr class="sec"><td colspan="{len(months) + 2}">{DLAB[suf]}</td></tr>'
        for k, lab, f in (("u", "Unités", "n"), ("pbv_u", "Profit véhicule / u", "$"), ("fi_u", "F&I / u", "$")):
            for yy, cls in ((y, ""), (y - 1, "muted")):
                tds = ""
                for i in months:
                    g = S.V.group(pkey(yy, i), "month", "real", S.dealers)
                    ok = g and len(g["_dealers"]) == len(S.dealers)
                    v = metrics(g[suf]).get(k) if ok else None
                    tds += f'<td class="{cls}">{num(v) if v is not None else "—"}</td>'
                gy = S.V.group(pkey(yy, m), "ytd", "real", S.dealers)
                vy = metrics(gy[suf]).get(k) if gy and len(gy["_dealers"]) == len(S.dealers) else None
                tds += f'<td class="sep {cls} {"strong" if not cls else ""}">{num(vy) if vy is not None else "—"}</td>'
                body += f'<tr><td class="lab {cls}">{escape(lab)} {yy}</td>{tds}</tr>'
    return f"""
      <div class="eyebrow">Mois par mois</div>
      <h1>Détail mensuel du Groupe — {y} comparé à {y-1}</h1>
      {key(f"Chaque mois de {y} (noir) au-dessus du même mois de {y-1} (gris), pour les {len(S.dealers)} concessions ; montants par unité en $. "
           "« — » : mois où une concession n'a pas de données.", "Comment lire")}
      <table class="t num trend fo"><thead><tr><th class="lab">Indicateur</th>{head}</tr></thead><tbody>{body}</tbody></table>"""


def p_methode(S):
    y, m = S.y, S.m
    src = "".join(f"<li><b>{escape(DEALERS[d])}</b> : {escape(SOURCE_LABELS.get(S.s.source_format(d, S.P), '—'))} ({MOIS[m]} {y}) ; an passé : "
                  f"{escape(SOURCE_LABELS.get(S.s.source_format(d, prior_year(S.P)), '—'))}"
                  f"{'' if S.V.same_format(d, S.P) else ' — frais, profit du département et mix non comparés à l’an passé'}.</li>" for d in S.dealers)
    return f"""
      <div class="eyebrow">Méthode</div>
      <h1>Sources et définitions</h1>
      <h2>Sources</h2>
      <ul class="retenir compact">{src}</ul>
      <h2>Définitions</h2>
      <dl class="defs">
        <dt>Unités au détail</dt><dd>Neufs : véhicules vendus au détail, avec démos et flottes ; usagés : véhicules vendus au détail. Les ventes en gros ne sont
        pas comptées.</dd>
        <dt>Profit véhicule, F&I</dt><dd>Profit brut des lignes véhicules du département ; F&I = revenus du bureau commercial. Par unité : ÷ unités au détail.</dd>
        <dt>Gros, encan, export et autres</dt><dd>Profit brut du département − profit véhicule − F&I (jamais divisé par les unités au détail).</dd>
        <dt>Frais de vente</dt><dd>Commissions des vendeurs, publicité nette des ristournes, intérêts sur stocks nets des crédits du constructeur, par unité au
        détail. Dépenses du département : total des frais inscrits au département (selon le format du fichier).</dd>
        <dt>Groupe</dt><dd>Sommes des concessions ; ratios recalculés à partir des sommes, seulement sur les concessions qui ont les deux chiffres.</dd>
      </dl>
      <p class="note">Rapport tiré du tableau de bord KPI (data.json : indicateurs et lignes des départements Véhicules neufs et Véhicules usagés).
      Même méthode que les rapports mensuels (profit véhicule / F&I / gros, 28 septembre 2026).</p>"""


def build_book(s, P):
    rc.setup(s, P)
    rc.FOOTER_LABEL = f"Ventes de véhicules · Analyse approfondie · {rc.PERIOD_LABEL}"
    S = VS(s, P)
    bk = Book()
    bk.add_cover(p_cover(S))
    bk.add(p_essentiel(S))
    import rapport_etoiles as ret        # 3 étoiles et 3 points à améliorer
    bk.add(ret.page_ventes_groupe(S, s, P))
    bk.add(p_overview(S))
    for suf in ("neuf", "usage"):
        bk.add(p_dept(S, suf))
    bk.add(p_fi(S))
    for suf in ("neuf", "usage"):
        bk.add(p_frais(S, suf))
    for suf in ("neuf", "usage"):
        bk.add(p_mix(S, suf))
    bk.add(p_gros(S))
    import rapport_composite as rcomp   # ventes face aux composites des constructeurs
    pg = rcomp.page_ventes_groupe(s, P)
    if pg:
        bk.add(pg)
    bk.add(p_tendances(S))
    bk.add(p_detail_mensuel(S))
    bk.add(p_methode(S))
    return bk


def generate(s, P, out_pdf, keep_html=False):
    bk = build_book(s, P)
    html = wrap_html(f"Ventes de véhicules — {rc.PERIOD_LABEL}", bk.pages)
    rc.FOOTER_LABEL = ""
    hp = os.path.splitext(out_pdf)[0] + ".html"
    with open(hp, "w", encoding="utf-8") as f:
        f.write(html)
    over = to_pdf(hp, out_pdf)
    if not keep_html:
        os.remove(hp)
    return out_pdf, len(bk.pages), over


def main():
    ap = argparse.ArgumentParser(description="Rapport Ventes de véhicules du Groupe — Groupe Automax")
    ap.add_argument("--mois")
    ap.add_argument("--data", default=os.path.join(HERE, "data.json"))
    ap.add_argument("--budget", default=os.path.join(HERE, "budgets.csv"))
    ap.add_argument("--sortie", default=HERE)
    a = ap.parse_args()
    s = Store(a.data, a.budget)
    if a.mois:
        P = a.mois
    else:
        common = set.intersection(*[set(s.periods(d)) for d in DEALERS])
        P = max(common)
    out = a.sortie if a.sortie.endswith(".pdf") else os.path.join(a.sortie, f"Rapport_Ventes_{P}.pdf")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fp, n, over = generate(s, P, out)
    print(f"PDF : {fp} ({n} pages)" + (f" — ATTENTION débordement {over}" if over else ""))


if __name__ == "__main__":
    main()
