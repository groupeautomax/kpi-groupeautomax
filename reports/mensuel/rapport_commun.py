# -*- coding: utf-8 -*-
"""Éléments communs de mise en page des rapports KPI (Groupe et concessions)."""
import base64
import calendar
import datetime as dt
import os
from html import escape

from kpi_data import DEALERS, MOIS, split, label_period, ratios, bridge_families, GPA_PLAUSIBLE_MAX
from kpi_analyse import kmoney, num, pct, pts, var_pct, NBSP
from kpi_svg import icon, donut, CAT, CAT_OTHER

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    p = os.path.join(HERE, "logo", name)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


LOGO_DARK = _load("logo-automax.svg")
LOGO_LIGHT = _load("logo-automax-blanc.svg")

SEC = "sec"
FAMILY_LABELS = {
    "PB neufs": "PB\nneufs", "PB usagés": "PB\nusagés", "Après-vente": "Après-\nvente",
    "Autres PB": "Autres\nPB", "Autres revenus": "Autres\nrevenus", "Dépenses variables": "Dépenses\nvariables",
    "Personnel": "Personnel", "Semi-fixes et autres": "Semi-fixes\net autres", "Amortissement": "Amort. et\nautres",
}
FAMILY_SHORT = {
    "PB neufs": "PB neufs", "PB usagés": "PB usagés", "Après-vente": "Après-vente", "Autres PB": "Autres PB",
    "Autres revenus": "Autres revenus", "Dépenses variables": "Dép. variables", "Personnel": "Personnel",
    "Semi-fixes et autres": "Semi-fixes et autres", "Amortissement": "Amort.",
}
LEVEL_LABEL = {"critique": "Critique", "eleve": "Élevé", "attention": "À surveiller", "positif": "Positif",
               "erreur": "Erreur", "manque": "Manquant", "valider": "À valider", "info": "Info"}

# état de mise en page (fixé par setup)
PERIOD_LABEL = ""
PREPARED = ""
FOOTER_LABEL = ""
ACTIVE = list(DEALERS)


def setup(s, P):
    global PERIOD_LABEL, PREPARED, ACTIVE
    ACTIVE = [d for d in DEALERS if s.comp(d, P, "month", "real") and s.comp(d, P, "ytd", "real")]
    PERIOD_LABEL = label_period(P)
    t = dt.date.today()
    PREPARED = f"{t.day}{'er' if t.day == 1 else ''} {MOIS[t.month]} {t.year}"


def last_day(P):
    y, m = split(P)
    return f"{calendar.monthrange(y, m)[1]} {MOIS[m]} {y}"


def mois_court(m):
    w = MOIS[m]
    return w[:4] + "." if len(w) > 4 else w


# ------------------------------------------------------------ valeurs et écarts
def val(c, key):
    if not c:
        return None
    if key == "profit_expl":
        return c["pb"] - c["dep"]
    if key in c:
        return c[key]
    return ratios(c).get(key)


def better_high(kind):
    return kind not in ("exp", "ratio_inv")


def cls_delta(d, kind, eps=0.0005):
    if d is None or abs(d) < eps or kind in ("ratio_x", "neutral"):
        return ""
    return "pos" if (d > 0) == better_high(kind) else "neg"


def fmt_val(v, kind):
    if v is None:
        return "—"
    if kind in ("money", "exp"):
        return num(v / 1000)
    if kind in ("ratio", "ratio_inv"):
        return pct(v, 1)
    if kind == "ratio_x":
        return num(v, 2)
    return num(v)


def fmt_delta(r, b, kind):
    """(écart, écart %, classe)"""
    if r is None or b is None:
        return "—", "", ""
    d = r - b
    if kind in ("ratio", "ratio_inv"):
        return pts(d, 1), "", cls_delta(d, kind)
    if kind == "ratio_x":
        return num(d, 2, sign=True), "", ""
    t = num(d / 1000, sign=True) if kind in ("money", "exp") else num(d, sign=True)
    vp = var_pct(r, b)
    tp = pct(vp, 0, sign=True) if vp is not None and abs(vp) < 10 else ("n.s." if b <= 0 else "")
    return t, tp, cls_delta(d / 1000 if kind in ("money", "exp") else d, kind, 0.5)


def unreliable_ap(s, P, mode, dealers, key):
    pb, u = ("pb_neuf", "u_neuf") if key == "gpa_neuf" else ("pb_usage", "u_usage")
    bad = []
    for d in dealers:
        a = s.comp(d, P, mode, "ap")
        if a and a[u] and abs(a[pb] / a[u]) > GPA_PLAUSIBLE_MAX:
            bad.append(d)
    return bad


# ------------------------------------------------------------ blocs HTML
def chip(label, cls):
    return f'<span class="chip {cls}">{escape(label)}</span>'


def level_chip(level):
    return f'<span class="lvl lvl-{level}">{icon(level, 10)}<span>{LEVEL_LABEL[level]}</span></span>'


def key(text, label="À retenir"):
    return f'<div class="key"><span class="kl">{escape(label)}</span>{text}</div>'


def tile(label, value, lines, strong=False):
    ls = "".join(f'<div class="tl {c}">{t}</div>' for t, c in lines)
    return f'<div class="tile{" strong" if strong else ""}"><div class="tlab">{escape(label)}</div><div class="tval">{value}</div>{ls}</div>'


def delta_line(r, b, ref, kind="money"):
    if r is None or b is None:
        return (f"{ref} : n/d", "muted")
    d = r - b
    if kind in ("ratio", "ratio_inv"):
        return (f"{pts(d, 1)} vs {ref}", cls_delta(d, kind))
    vp = var_pct(r, b)
    vtxt = f" ({pct(vp, 0, sign=True)})" if vp is not None and abs(vp) < 10 else ""
    if kind == "unit":
        return (f"{num(d, sign=True)}{vtxt} vs {ref}", cls_delta(d, kind))
    return (f"{kmoney(d, sign=True)}{vtxt} vs {ref}", cls_delta(d / 1000, kind, 0.5))


def page(content, n, cover=False):
    if cover:
        return f'<section class="page cover">{content}</section>'
    label = FOOTER_LABEL or ("Rapport mensuel de performance · " + PERIOD_LABEL)
    return (f'<section class="page">{content}'
            f'<div class="footer"><span class="ft-left"><span class="logo ft-logo">{LOGO_DARK}</span>{escape(label)}</span>'
            f'<span>Page {n}</span></div></section>')


def comp_table(rows, cols, heads=None, cls="", foot=None, getter=val):
    """Tableau comparatif.
    rows : [(clé, libellé, type, style)] ou (SEC, titre).
    cols : [{"h": entête, "t": "v"|"d"|"p", "c": comp (t=v) ou (réel, base) (t=d/p), "cls": classe}]
    heads : entêtes groupés optionnels [(libellé, nb colonnes, classe)]."""
    foot = foot or {}
    th2 = "".join(f'<th class="{c.get("cls", "")}">{c["h"]}</th>' for c in cols)
    if heads:
        th1 = "".join(f'<th colspan="{n}" class="{c}">{escape(h)}</th>' for h, n, c in heads)
        head = f'<thead><tr><th rowspan="2" class="lab">k$ sauf indication</th>{th1}</tr><tr>{th2}</tr></thead>'
    else:
        head = f'<thead><tr><th class="lab">k$ sauf indication</th>{th2}</tr></thead>'
    body = []
    for r in rows:
        if r[0] == SEC:
            body.append(f'<tr class="sec"><td colspan="{len(cols) + 1}">{escape(r[1])}</td></tr>')
            continue
        k, lab, kind, style = r
        tds = ""
        for c in cols:
            ccls = c.get("cls", "")
            if c["t"] == "v":
                comp = c["c"]
                if comp is None:
                    tds += f'<td class="{ccls} muted">n/d</td>'
                else:
                    tds += f'<td class="{ccls} {c.get("vcls", "")}">{fmt_val(getter(comp, k), kind)}</td>'
            else:
                rr, bb = c["c"]
                if bb is None:
                    tds += f'<td class="{ccls} muted">{"n/d" if c["t"] == "d" else ""}</td>'
                    continue
                if c.get("nc") and k in c["nc"]:
                    tds += f'<td class="{ccls} muted">{"n.c." if c["t"] == "d" else ""}</td>'
                    continue
                t, p_, dc = fmt_delta(getter(rr, k), getter(bb, k), kind)
                tds += f'<td class="{ccls} {dc}{" pc" if c["t"] == "p" else ""}">{t if c["t"] == "d" else p_}</td>'
        body.append(f'<tr class="{style}"><td class="lab">{escape(lab)}{foot.get(k, "")}</td>{tds}</tr>')
    return f'<table class="t num {cls}">{head}<tbody>{"".join(body)}</tbody></table>'


def donut_block(items, ca, cb, lab_a, lab_b, unit_caption="profit brut"):
    """Deux anneaux (an passé / année en cours) + tableau-légende.
    items : [(libellé, clé)] dans l'ordre fixe ; les couleurs suivent l'ordre (dernier « Autres… » en gris)."""
    cols = []
    for i, (lab, k) in enumerate(items):
        is_other = lab.lower().startswith("autres")
        cols.append(CAT_OTHER if is_other else CAT[min(i, len(CAT) - 1)])
    va = [(ca[k] if ca else None) for _, k in items]
    vb = [cb[k] for _, k in items]
    tot_a = sum(v for v in va if v is not None and v > 0)
    tot_b = sum(v for v in vb if v is not None and v > 0)
    sa = [(lab, v if (v or 0) > 0 else 0, col) for (lab, _), v, col in zip(items, va, cols)]
    sb = [(lab, v if (v or 0) > 0 else 0, col) for (lab, _), v, col in zip(items, vb, cols)]
    d1 = donut(sa, kmoney(tot_a), lab_a) if ca else "<p class='muted'>n/d</p>"
    d2 = donut(sb, kmoney(tot_b), lab_b)
    rows = ""
    neg = []
    for (lab, _), a, b, col in zip(items, va, vb, cols):
        pa = (a / tot_a) if (a is not None and a > 0 and tot_a) else None
        pb = (b / tot_b) if (b is not None and b > 0 and tot_b) else None
        if (a is not None and a < 0) or (b is not None and b < 0):
            neg.append(lab.lower())
        d = (b - a) if a is not None else None
        rows += (f'<tr><td class="lab"><span class="sw" style="background:{col}"></span>{escape(lab)}</td>'
                 f'<td class="muted">{fmt_val(a, "money")}</td><td class="muted">{pct(pa, 0) if pa is not None else "—"}</td>'
                 f'<td class="sep">{fmt_val(b, "money")}</td><td>{pct(pb, 0) if pb is not None else "—"}</td>'
                 f'<td class="sep">{num(d / 1000, sign=True) if d is not None else "—"}</td></tr>')
    table = (f'<table class="t num legtab"><thead><tr><th class="lab">k$</th><th>{lab_a}</th><th>% du total</th>'
             f'<th class="sep">{lab_b}</th><th>% du total</th><th class="sep">Écart</th></tr></thead><tbody>{rows}</tbody></table>')
    note = (f'<div class="note">Montant négatif (crédit net) pour : {", ".join(neg)}. Un montant négatif ne peut pas être dessiné dans un anneau : '
            f'il figure au tableau, et les pourcentages portent sur les montants positifs.</div>') if neg else ""
    return (f'<div class="donuts"><div><div class="donut-cap">{lab_a}</div>{d1}</div><div><div class="donut-cap">{lab_b}</div>{d2}</div></div>'
            f'{table}{note}')


def heat_color(v, vmax):
    if v is None or vmax == 0:
        return ""
    a = min(abs(v) / vmax, 1) * 0.5 + (0.06 if abs(v) >= 1000 else 0)
    rgb = "0,136,72" if v > 0 else "200,65,47"
    return f"background: rgba({rgb},{a:.2f});"


def fam_items(b):
    return [(FAMILY_LABELS[k], v) for k, v in bridge_families(b).items()]


def shares(comp, items):
    """Part de chaque poste dans la somme des postes positifs (même base que l'anneau)."""
    if not comp:
        return {}
    tot = sum(comp[k] for _, k in items if comp[k] > 0)
    return {k: (comp[k] / tot if tot and comp[k] > 0 else None) for _, k in items}


def compo_message(r, a, items, y, what_lab):
    sa, sr = shares(a, items), shares(r, items)
    diffs = [(sr[k] - sa[k], lab, sa[k], sr[k]) for lab, k in items if sa.get(k) is not None and sr.get(k) is not None]
    if not diffs:
        return "Répartition du cumul de l'année."
    diffs.sort(key=lambda t: -abs(t[0]))
    dd, lab, x, z = diffs[0]
    return (f"La part « {lab.lower()} » {what_lab} passe de <b>{pct(x, 1)}</b> à <b>{pct(z, 1)}</b> ({pts(dd, 1)}), "
            f"le plus grand changement de composition depuis {y-1}.")


def chunks(lst, n):
    """Découpe en pages équilibrées d'au plus n éléments (15 → 8 + 7 plutôt que 7 + 7 + 1)."""
    if not lst:
        return [[]]
    import math
    pages = math.ceil(len(lst) / n)
    size = math.ceil(len(lst) / pages)
    return [lst[i:i + size] for i in range(0, len(lst), size)]


# ------------------------------------------------------------ assemblage
class Book:
    """Pages numérotées dans l'ordre ; `marks` retient le numéro de page d'une section."""
    def __init__(self):
        self.pages = []
        self.marks = {}

    def mark(self, name):
        self.marks[name] = len(self.pages) + 1

    def add(self, content):
        self.pages.append(page(content, len(self.pages) + 1))

    def add_cover(self, content):
        self.pages.append(page(content, 1, cover=True))


def font_css():
    out = []
    for w in (400, 500, 600, 700, 800):
        p = os.path.join(HERE, "fonts", f"inter-latin-{w}-normal.woff2")
        if os.path.exists(p):
            b64 = base64.b64encode(open(p, "rb").read()).decode()
            out.append(f"@font-face{{font-family:'Inter';font-weight:{w};src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
    return "\n".join(out)


def wrap_html(title, pages):
    css = open(os.path.join(HERE, "rapport.css"), encoding="utf-8").read()
    return (f'<!doctype html><html lang="fr-CA"><head><meta charset="utf-8"><title>{escape(title)}</title>'
            f'<style>{font_css()}\n{css}</style></head><body>{"".join(pages)}</body></html>')


def to_pdf(html_path, pdf_path):
    """Rend le HTML en PDF ; renvoie la liste des pages dont le contenu déborde en hauteur."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto("file://" + os.path.abspath(html_path))
        pg.wait_for_timeout(300)
        over = pg.evaluate("""() => [...document.querySelectorAll('section.page')].map((e,i)=>{
                                  const R = e.getBoundingClientRect(); let wide = 0;
                                  e.querySelectorAll('table, svg, .tiles').forEach(t => { const r = t.getBoundingClientRect();
                                      wide = Math.max(wide, r.right - (R.right - 0.75*96)); });
                                  return {page:i+1, sh:e.scrollHeight, ch:e.clientHeight, wide: Math.round(wide)}; })
                              .filter(o => o.sh > o.ch + 1 || o.wide > 4)""")
        pg.pdf(path=pdf_path, format="Letter", print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
               prefer_css_page_size=True)
        b.close()
    return over
