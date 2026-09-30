# -*- coding: utf-8 -*-
"""« 3 étoiles et 3 points à améliorer » : une page par rapport, juste après
le sommaire (demande de Maxime Allard, 29 septembre 2026 : « je veux dans
chaque rapport 3 étoiles pour les meilleures stats et trois points à
améliorer »).

Candidats (cumul depuis janvier) :
  - chaque indicateur comparé à la même période de l'an passé ;
  - l'EBT comparé au budget quand il y en a un ;
  - les comparaisons aux composites des constructeurs (Hyundai : moyenne du
    groupe ; VW : moyenne nationale), fournies par rapport_composite.

Score = écart relatif dans le sens favorable (plafonné à ±CAP) × poids de
l'indicateur. Un seul indicateur par famille (ex. une seule étoile « neufs »),
au plus MAX_COMP comparaisons au composite de chaque côté. Seuils de
matérialité : les petits écarts (quelques milliers de dollars, quelques
unités, moins d'un demi-point) ne sont jamais retenus.

Pages :
  page_concession(s, P, d)      rapport mensuel de la concession
  page_fo_concession(F, s, P, d) rapport Opérations fixes de la concession
  page_groupe(s, P)             rapport mensuel du Groupe
  page_fo_groupe(F, s, P)       rapport Opérations fixes du Groupe
"""
from html import escape

from kpi_data import DEALERS, MOIS, split, ratios, GPA_PLAUSIBLE_MAX
from kpi_analyse import money, kmoney, num, pct, pts, var_pct, group_pair, group_real
from rapport_commun import key

CAP = 1.5          # écart relatif plafonné (une hausse de 400 % sur une petite base ne domine pas)
RELAX = [1.0]      # facteur des seuils : 1 = strict ; 2e passe à 0,25 pour compléter à 3 (voir pick_all)
MAX_COMP = 2       # au plus 2 comparaisons au composite parmi les 3
MIN_SCORE = 0.02   # en deçà : écart jugé non significatif


# ------------------------------------------------------------ candidats
def cand(score, fam, title, value, comp, src="an", kind="an"):
    return {"score": score, "fam": fam, "title": title, "value": value, "comp": comp, "src": src, "kind": kind}


def _rel_amount(r, a):
    if r is None or a is None or not a:
        return None
    return (r - a) / abs(a)


def _cap(x):
    return max(-CAP, min(CAP, x))


def c_money(title, r, a, fam, w, ref, min_abs):
    """Montant (k$) comparé à l'an passé."""
    rel = _rel_amount(r, a)
    if rel is None or abs(r - a) < min_abs * RELAX[0]:
        return None
    vp = var_pct(r, a)
    return cand(_cap(rel) * w, fam, title, kmoney(r),
                f"{kmoney(r - a, sign=True)}" + (f" ({pct(vp, 0, sign=True)})" if vp is not None else "") + f" par rapport {ref}")


def c_pct(title, r, a, fam, w, ref, sens=1, floor=0.10, min_pts=0.005):
    """Ratio (%) comparé à l'an passé : écart en points ÷ max(|base|, floor)."""
    if r is None or a is None or abs(r - a) < min_pts * RELAX[0]:
        return None
    rel = (r - a) / max(abs(a), floor) * sens
    return cand(_cap(rel) * w, fam, title, pct(r, 1), f"{pts(r - a, 1)} par rapport {ref} ({pct(a, 1)})")


def c_unit(title, r, a, fam, w, ref, n_r, n_a, min_n=20, min_rel=0.03):
    """Montant par unité ($) : seulement avec assez d'unités des deux côtés."""
    if r is None or a is None or not a or (n_r or 0) < min_n * RELAX[0] or (n_a or 0) < min_n * RELAX[0]:
        return None
    if a <= 0 or abs(a) > GPA_PLAUSIBLE_MAX:
        return None
    rel = (r - a) / abs(a)
    if abs(rel) < min_rel * RELAX[0]:
        return None
    return cand(_cap(rel) * w, fam, title, money(r), f"{money(r - a, sign=True)} ({pct(rel, 0, sign=True)}) par rapport {ref} ({money(a)})")


def c_count(title, r, a, fam, w, ref, min_abs=5, min_rel=0.03, unit=""):
    if r is None or a is None or not a or abs(r - a) < min_abs * RELAX[0]:
        return None
    rel = (r - a) / abs(a)
    if abs(rel) < min_rel * RELAX[0]:
        return None
    u = f" {unit}" if unit else ""
    return cand(_cap(rel) * w, fam, title, num(r) + u, f"{num(r - a, sign=True)}{u} ({pct(rel, 0, sign=True)}) par rapport {ref} ({num(a)})")


def _keep(lst):
    return [c for c in lst if c]


def concession_cands(r, a, ref, min_abs=20000, prefix="", famp=""):
    """Indicateurs d'une concession (ou du Groupe) : réel r vs base a (composantes)."""
    if not r or not a:
        return []
    rr, ra = ratios(r), ratios(a)
    p = prefix
    out = [
        c_money(f"{p}EBT (profit net avant impôt)", r["ebt"], a["ebt"], famp + "ebt", 1.0, ref, min_abs),
        c_money(f"{p}Profit brut total", r["pb"], a["pb"], famp + "pb", 0.8, ref, min_abs),
        c_money(f"{p}Ventes nettes", r["ventes"], a["ventes"], famp + "ventes", 0.5, ref, min_abs * 5),
        c_pct(f"{p}Marge brute (% des ventes)", rr["marge_brute"], ra["marge_brute"], famp + "pb", 0.6, ref, floor=0.10),
        c_pct(f"{p}Dépenses (% du profit brut)", rr["dep_pct_pb"], ra["dep_pct_pb"], famp + "dep", 0.9, ref, sens=-1, floor=0.5),
        c_pct(f"{p}Dépenses de personnel (% du profit brut)", rr["pers_pct_pb"], ra["pers_pct_pb"], famp + "dep", 0.7, ref, sens=-1, floor=0.3),
        c_count(f"{p}Véhicules neufs vendus au détail", r["u_neuf"], a["u_neuf"], famp + "neuf", 0.7, ref, unit="unités"),
        c_count(f"{p}Véhicules usagés vendus au détail", r["u_usage"], a["u_usage"], famp + "usage", 0.7, ref, unit="unités"),
        c_unit(f"{p}Profit véhicule par unité neuve", rr["gpa_neuf"], ra["gpa_neuf"], famp + "neuf", 0.7, ref, r["u_neuf"], a["u_neuf"]),
        c_unit(f"{p}Profit véhicule par unité usagée", rr["gpa_usage"], ra["gpa_usage"], famp + "usage", 0.7, ref, r["u_usage"], a["u_usage"]),
        c_unit(f"{p}F&I par unité neuve", rr["fi_unite_neuf"], ra["fi_unite_neuf"], famp + "fi", 0.6, ref, r["u_neuf"], a["u_neuf"]),
        c_unit(f"{p}F&I par unité usagée", rr["fi_unite_usage"], ra["fi_unite_usage"], famp + "fi", 0.6, ref, r["u_usage"], a["u_usage"]),
        c_money(f"{p}Profit brut du service", r["pb_service"], a["pb_service"], famp + "service", 0.7, ref, min_abs),
        c_money(f"{p}Profit brut des pièces", r["pb_pieces"], a["pb_pieces"], famp + "pieces", 0.7, ref, min_abs),
        c_money(f"{p}Profit brut de la carrosserie", r["pb_carrosserie"], a["pb_carrosserie"], famp + "carrosserie", 0.5, ref, min_abs),
        c_pct(f"{p}Absorption (après-vente ÷ frais fixes)", rr["absorption"], ra["absorption"], famp + "absorption", 0.8, ref, floor=0.5),
        c_money(f"{p}Gros, encan et export (profit brut)", rr["gros_total"], ra["gros_total"], famp + "gros", 0.4, ref, min_abs),
    ]
    return _keep(out)


def budget_cands(r, b, prefix="", famp=""):
    if not r or not b:
        return []
    return _keep([c_money(f"{prefix}EBT par rapport au budget", r["ebt"], b["ebt"], famp + "ebt_budget", 0.9, "au budget", 20000)])


def fo_type_cands(cr, ca, typ_lab, fam, ref):
    """Un type de BT (client, garantie, interne)."""
    return _keep([
        c_count(f"BT {typ_lab} : nombre de bons de travail", cr.get("bt"), ca.get("bt"), fam, 0.6, ref, min_abs=20),
        c_unit(f"BT {typ_lab} : total par BT (main-d'œuvre + pièces)", cr.get("tot_bt"), ca.get("tot_bt"), fam, 0.8, ref,
               cr.get("bt"), ca.get("bt"), min_n=50),
        c_unit(f"BT {typ_lab} : main-d'œuvre par BT", cr.get("mo_bt"), ca.get("mo_bt"), fam, 0.6, ref, cr.get("bt"), ca.get("bt"), min_n=50),
        c_unit(f"BT {typ_lab} : pièces par BT", cr.get("pc_bt"), ca.get("pc_bt"), fam, 0.6, ref, cr.get("bt"), ca.get("bt"), min_n=50),
        c_unit(f"BT {typ_lab} : taux effectif de main-d'œuvre", cr.get("elr"), ca.get("elr"), fam, 0.6, ref, cr.get("bt"), ca.get("bt"), min_n=50),
    ])


def fo_cands(F, d, ref, famp=""):
    """Opérations fixes d'une concession (ou du Groupe) : cumul vs an passé."""
    from kpi_apres_vente import MAIN_TYPES, TYPES, atelier_metrics
    out = []
    r, a = F.comp_pair(d, "ytd")
    if r and a:
        rr, ra = ratios(r), ratios(a)
        out += _keep([
            c_money("Profit brut après-vente", rr["apres_vente"], ra["apres_vente"], famp + "apv", 1.0, ref, 20000),
            c_money("Profit brut du service", r["pb_service"], a["pb_service"], famp + "service", 0.7, ref, 15000),
            c_money("Profit brut des pièces", r["pb_pieces"], a["pb_pieces"], famp + "pieces", 0.7, ref, 15000),
            c_money("Profit brut de la carrosserie", r["pb_carrosserie"], a["pb_carrosserie"], famp + "carrosserie", 0.5, ref, 15000),
            c_pct("Absorption (après-vente ÷ frais fixes)", rr["absorption"], ra["absorption"], famp + "absorption", 0.9, ref, floor=0.5),
        ])
    fr, fa = F.pair(d, "ytd")
    for typ in MAIN_TYPES:
        cr, ca = F.tm(fr, typ), F.tm(fa, typ)
        if cr.get("bt") and ca.get("bt"):
            out += fo_type_cands(cr, ca, TYPES[typ].lower(), famp + "bt_" + typ, ref)
    at, aa = atelier_metrics(fr), atelier_metrics(fa)
    if at.get("productivite") and aa.get("productivite"):
        out += _keep([c_pct("Productivité de l'atelier (heures pointées ÷ disponibles)", at["productivite"], aa["productivite"],
                            famp + "atelier", 0.6, ref, floor=0.5),
                      c_pct("Efficacité de l'atelier (heures vendues ÷ pointées)", at["efficacite"], aa["efficacite"],
                            famp + "atelier", 0.6, ref, floor=0.5)])
    return out


# ------------------------------------------------------------ sélection
def _sel(lst, good, n, max_ext, out=None):
    """Choisit dans lst (déjà trié) : familles distinctes, au plus max_ext
    candidats « externes » (composite ou concession nommée dans un rapport du Groupe)."""
    out = list(out or [])
    fams = {c["fam"] for c in out}
    n_ext = sum(c["kind"] != "an" for c in out)
    for c in lst:
        if len(out) >= n:
            break
        if (c["score"] > 0) != good or abs(c["score"]) <= MIN_SCORE or c["fam"] in fams:
            continue
        if c["kind"] != "an" and n_ext >= max_ext:
            continue
        out.append(c)
        fams.add(c["fam"])
        n_ext += c["kind"] != "an"
    return out


def pick_all(build, n=3, max_ext=MAX_COMP, fill=None):
    """build() → candidats. 1re passe aux seuils normaux ; s'il en manque, 2e
    passe aux seuils relâchés (écarts plus petits) ; s'il en manque encore,
    fill() : comparaisons à l'ensemble du Groupe (même familles exclues)."""
    RELAX[0] = 1.0
    c1 = sorted(build(), key=lambda c: -c["score"])
    good, bad = _sel(c1, True, n, max_ext), _sel(list(reversed(c1)), False, n, max_ext)
    if len(good) < n or len(bad) < n:
        RELAX[0] = 0.25
        try:
            c2 = sorted(build(), key=lambda c: -c["score"])
        finally:
            RELAX[0] = 1.0
        good = _sel(c2, True, n, max_ext, good)
        bad = _sel(list(reversed(c2)), False, n, max_ext, bad)
    c3 = []
    if fill and (len(good) < n or len(bad) < n):
        c3 = sorted(fill(), key=lambda c: -c["score"])
        good = _sel(c3, True, n, n, good)
        bad = _sel(list(reversed(c3)), False, n, n, bad)
    if len(bad) < n:
        # presque tout progresse : les plus faibles progressions deviennent les points à améliorer
        RELAX[0] = 0.25
        try:
            pool = sorted(build() + c3, key=lambda c: c["score"])
        finally:
            RELAX[0] = 1.0
        used = {c["fam"] for c in good + bad}
        for c in pool:
            if len(bad) >= n:
                break
            if c["fam"] in used or c["score"] <= 0:
                continue
            bad.append(dict(c, weak=True))
            used.add(c["fam"])
    return good, bad


# ------------------------------------------------------------ vs l'ensemble du Groupe (complément)
SRC_GRP = "vs ensemble du Groupe"


def c_vs(title, v, g, fam, w, t, sens=1, n_v=None, min_n=20):
    """Ratio de la concession comparé à celui de l'ensemble du Groupe."""
    if v is None or g is None or (n_v is not None and (n_v or 0) < min_n):
        return None
    if t == "pct":
        if abs(v - g) < 0.005:
            return None
        rel = (v - g) / max(abs(g), 0.10) * sens
        val, comp = pct(v, 1), f"{pct(g, 1)} pour l'ensemble du Groupe ({pts(v - g, 1)})"
    else:
        if not g or g <= 0:
            return None
        rel = (v / g - 1) * sens
        if abs(rel) < 0.03:
            return None
        val, comp = money(v), f"{money(g)} pour l'ensemble du Groupe ({pct(v / g - 1, 0, sign=True)})"
    return cand(_cap(rel) * w, fam, title, val, comp, src=SRC_GRP, kind="grp")


def concession_vs_groupe(r, G):
    if not r or not G:
        return []
    rr, rg = ratios(r), ratios(G)
    return _keep([
        c_vs("Marge brute (% des ventes)", rr["marge_brute"], rg["marge_brute"], "pb", 0.5, "pct"),
        c_vs("Dépenses (% du profit brut)", rr["dep_pct_pb"], rg["dep_pct_pb"], "dep", 0.5, "pct", sens=-1),
        c_vs("EBT (% du profit brut)", rr["ebt_pct_pb"], rg["ebt_pct_pb"], "ebt", 0.5, "pct"),
        c_vs("Absorption (après-vente ÷ frais fixes)", rr["absorption"], rg["absorption"], "absorption", 0.5, "pct"),
        c_vs("Profit véhicule par unité neuve", rr["gpa_neuf"], rg["gpa_neuf"], "neuf", 0.4, "d", n_v=r["u_neuf"]),
        c_vs("Profit véhicule par unité usagée", rr["gpa_usage"], rg["gpa_usage"], "usage", 0.4, "d", n_v=r["u_usage"]),
        c_vs("F&I par unité neuve", rr["fi_unite_neuf"], rg["fi_unite_neuf"], "fi", 0.4, "d", n_v=r["u_neuf"]),
    ])


def fo_vs_groupe(F, d):
    from kpi_apres_vente import MAIN_TYPES, TYPES
    out = []
    r, _ = F.comp_pair(d, "ytd")
    G, _ = F.comp_pair("groupe", "ytd")
    if r and G:
        out.append(c_vs("Absorption (après-vente ÷ frais fixes)", ratios(r)["absorption"], ratios(G)["absorption"], "absorption", 0.5, "pct"))
    fr, _ = F.pair(d, "ytd")
    fg, _ = F.pair("groupe", "ytd")
    for typ in MAIN_TYPES:
        cr, cg = F.tm(fr, typ), F.tm(fg, typ)
        out.append(c_vs(f"BT {TYPES[typ].lower()} : total par BT (main-d'œuvre + pièces)", cr.get("tot_bt"), cg.get("tot_bt"),
                        "bt_" + typ, 0.4, "d", n_v=cr.get("bt"), min_n=50))
    return _keep(out)


# ------------------------------------------------------------ rendu
STAR = ('<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" '
        'd="M12 2.6l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.4l-5.9 3.3 1.3-6.6L2.5 9.5l6.6-.8z"/></svg>')
ARROW = ('<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="none" stroke="currentColor" '
         'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" d="M12 19V5M5.5 11.5L12 5l6.5 6.5"/></svg>')


def _card(c, good):
    src = "" if c["src"] == "an" else f'<span class="st-src">{escape(c["src"])}</span>'
    return (f'<div class="st-card {"good" if good else "bad"}"><div class="st-ico">{STAR if good else ARROW}</div>'
            f'<div class="st-body"><div class="st-t">{escape(c["title"])}{src}</div>'
            f'<div class="st-row"><span class="st-v">{c["value"]}</span>'
            f'<span class="st-c {"pos" if good else ("muted" if c.get("weak") else "neg")}">{c["comp"]}'
            f'{" — progression la plus faible" if c.get("weak") else ""}</span></div></div></div>')


def page(title, lead, good, bad, note):
    g = "".join(_card(c, True) for c in good) or '<p class="muted">Aucun écart favorable marquant ce mois-ci.</p>'
    b = "".join(_card(c, False) for c in bad) or '<p class="muted">Aucun écart défavorable marquant ce mois-ci.</p>'
    return f"""
      <div class="eyebrow">Sommaire</div>
      <h1>{escape(title)}</h1>
      {key(lead, "Comment lire")}
      <h2 class="st-h good">{STAR}<span>Les {len(good) or 3} étoiles</span></h2>
      <div class="st-list">{g}</div>
      <h2 class="st-h bad">{ARROW}<span>Les {len(bad) or 3} points à améliorer</span></h2>
      <div class="st-list">{b}</div>
      <div class="note">{note}</div>"""


def _lead(P):
    y, m = split(P)
    return (f"Les meilleurs résultats et les points à améliorer depuis janvier ({MOIS[1]}–{MOIS[m]} {y}), choisis parmi tous les "
            f"indicateurs du rapport : comparaison à la même période {y-1} et, quand il est reçu, au composite du constructeur.")


NOTE = ("Classement : écart relatif dans le sens favorable (dépenses : une baisse est favorable), un seul indicateur par famille, "
        "au plus deux comparaisons au composite. Les petits écarts ne sont pas retenus.")


# ------------------------------------------------------------ pages
def page_concession(s, P, d):
    import rapport_composite as rcomp
    y, m = split(P)
    ref = f"à {MOIS[1]}–{MOIS[m]} {y-1}"
    r, a, b = (s.comp(d, P, "ytd", base) for base in ("real", "ap", "budget"))
    good, bad = pick_all(lambda: concession_cands(r, a, ref) + budget_cands(r, b) + rcomp.etoiles_concession(s, P, d),
                         fill=lambda: concession_vs_groupe(r, group_real(s, P, "ytd")[0]))
    return page(f"{DEALERS[d]} : 3 étoiles et 3 points à améliorer", _lead(P), good, bad, NOTE)


def page_fo_concession(F, s, P, d):
    import rapport_composite as rcomp
    y, m = split(P)
    ref = f"à {MOIS[1]}–{MOIS[m]} {y-1}"
    good, bad = pick_all(lambda: fo_cands(F, d, ref) + rcomp.etoiles_fo(s, P, d), fill=lambda: fo_vs_groupe(F, d))
    return page(f"{DEALERS[d]} : 3 étoiles et 3 points à améliorer — après-vente", _lead(P), good, bad, NOTE)


def _dealer_cands(s, P, ref):
    """Une concession par famille : EBT cumulatif de chaque concession vs l'an passé."""
    out = []
    for d in DEALERS:
        r, a = s.comp(d, P, "ytd", "real"), s.comp(d, P, "ytd", "ap")
        if r and a:
            c = c_money(f"{DEALERS[d]} : EBT", r["ebt"], a["ebt"], "d:" + d, 0.8, ref, 25000)
            if c:
                out.append(dict(c, kind="dealer"))
    return out


def page_groupe(s, P):
    import rapport_composite as rcomp
    y, m = split(P)
    ref = f"à {MOIS[1]}–{MOIS[m]} {y-1}"
    r, a, _ = group_pair(s, P, "ytd", "ap")
    rb, b, _ = group_pair(s, P, "ytd", "budget")
    # au plus 2 éléments propres à une concession : au moins une étoile et un point du Groupe lui-même
    good, bad = pick_all(lambda: concession_cands(r, a, ref, min_abs=50000, prefix="Groupe — ") + budget_cands(rb, b, "Groupe — ")
                         + _dealer_cands(s, P, ref) + rcomp.etoiles_groupe(s, P), max_ext=2)
    return page("Le Groupe : 3 étoiles et 3 points à améliorer", _lead(P), good, bad,
                NOTE + " Groupe : concessions comparables (celles qui ont les chiffres de l'an passé).")


def page_fo_groupe(F, s, P):
    import rapport_composite as rcomp
    from kpi_apres_vente import TYPES
    y, m = split(P)
    ref = f"à {MOIS[1]}–{MOIS[m]} {y-1}"

    def build():
        cands = [dict(c, title="Groupe — " + c["title"]) for c in fo_cands(F, "groupe", ref)]
        for d in F.dealers:     # total par BT client de chaque concession
            fr, fa = F.pair(d, "ytd")
            cr, ca = F.tm(fr, "client"), F.tm(fa, "client")
            c = c_unit(f"{DEALERS[d]} : total par BT {TYPES['client'].lower()}", cr.get("tot_bt"), ca.get("tot_bt"),
                       "d:" + d, 0.7, ref, cr.get("bt"), ca.get("bt"), min_n=50)
            if c:
                cands.append(dict(c, kind="dealer"))
        return cands + rcomp.etoiles_fo_groupe(s, P)
    good, bad = pick_all(build, max_ext=2)
    return page("Opérations fixes : 3 étoiles et 3 points à améliorer", _lead(P), good, bad,
                NOTE + " Groupe : concessions comparables.")
