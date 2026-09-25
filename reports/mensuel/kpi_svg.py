# -*- coding: utf-8 -*-
"""Petits graphiques SVG (impression) pour le rapport mensuel KPI."""
import math
from html import escape

from kpi_analyse import kmoney, NBSP, MINUS

INK = "#1D1D1B"
MUTED = "#6d6d68"
GRID = "#e4e6e2"
AXIS = "#b9bcb6"
FAV = "#008848"
DEFAV = "#c8412f"
TOTAL = "#5f6b73"   # barres de total du pont (ardoise, pas de noir)
SERIE = "#2a78d6"   # série de l'année en cours (bleu, plus léger que l'anthracite)
AP_TICK = "#9b9a93"
SURFACE = "#ffffff"


def nice_ticks(lo, hi, n=4):
    if hi == lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if step >= raw:
            break
    start = math.floor(lo / step) * step
    ticks, t = [], start
    while t <= hi + step * 0.001:
        ticks.append(t)
        t += step
    if ticks[-1] < hi:
        ticks.append(ticks[-1] + step)
    return ticks


def axis_label(v):
    a = abs(v)
    if a >= 1e6:
        s = f"{a/1e6:.1f}".replace(".", ",").replace(",0", "") + NBSP + "M$"
    elif a >= 1e3:
        s = f"{a/1e3:.0f}" + NBSP + "k$"
    else:
        s = f"{a:.0f}" + NBSP + "$"
    return (MINUS + s) if v < 0 else s


def _text(x, y, s, size=7.5, anchor="middle", fill=INK, weight=400, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{fill}" font-weight="{weight}" {extra}>{escape(s)}</text>')


def waterfall(start, items, end, width=700, height=235, start_label="", end_label=""):
    """start/end : (libellé, valeur). items : [(libellé, delta)]. Barres verticales.
    Les libellés peuvent contenir '\n' (2 lignes max)."""
    ml, mr, mt, mb = 46, 6, 20, 34
    pw, ph = width - ml - mr, height - mt - mb
    n = len(items) + 2
    slot = pw / n
    bw = slot * 0.6
    run = start[1]
    levels = [0, start[1]]
    for _, v in items:
        run += v
        levels.append(run)
    levels.append(end[1])
    lo, hi = min(levels), max(levels)
    ticks = nice_ticks(min(0, lo), max(0, hi), 4)
    y0, y1 = ticks[0], ticks[-1]
    Y = lambda v: mt + ph - (v - y0) / (y1 - y0) * ph
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">']
    for t in ticks:
        y = Y(t)
        out.append(f'<line x1="{ml}" x2="{width-mr}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID if t else AXIS}" stroke-width="{1 if t else 1.2}"/>')
        out.append(_text(ml - 6, y + 2.6, axis_label(t), 7, "end", MUTED))

    def bar(i, a, b, color, label, vtxt, vpos_top, bold=False):
        x = ml + slot * i + (slot - bw) / 2
        top, bot = Y(max(a, b)), Y(min(a, b))
        h = max(bot - top, 1.2)
        out.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2" fill="{color}"/>')
        cx = x + bw / 2
        if vpos_top:
            out.append(_text(cx, top - 4, vtxt, 7.4, "middle", INK, 700 if bold else 600))
        else:
            out.append(_text(cx, bot + 9.5, vtxt, 7.4, "middle", INK, 600))
        lines = label.split("\n")
        for j, ln in enumerate(lines[:2]):
            out.append(_text(cx, height - mb + 12 + j * 9.2, ln, 7.1, "middle", MUTED if not bold else INK, 600 if bold else 400))
        return x

    # départ
    xprev = bar(0, 0, start[1], TOTAL, start[0], kmoney(start[1]), True, True)
    run = start[1]
    for i, (lab, v) in enumerate(items, start=1):
        # connecteur
        yc = Y(run)
        x = ml + slot * i + (slot - bw) / 2
        out.append(f'<line x1="{xprev + bw:.1f}" x2="{x:.1f}" y1="{yc:.1f}" y2="{yc:.1f}" stroke="{AXIS}" stroke-width="0.8" stroke-dasharray="2 2"/>')
        new = run + v
        color = FAV if v >= 0 else DEFAV
        xprev = bar(i, run, new, color, lab, kmoney(v, sign=True) if abs(v) >= 500 else "0", v >= 0)
        run = new
    yc = Y(run)
    x = ml + slot * (n - 1) + (slot - bw) / 2
    out.append(f'<line x1="{xprev + bw:.1f}" x2="{x:.1f}" y1="{yc:.1f}" y2="{yc:.1f}" stroke="{AXIS}" stroke-width="0.8" stroke-dasharray="2 2"/>')
    bar(n - 1, 0, end[1], TOTAL, end[0], kmoney(end[1]), True, True)
    out.append("</svg>")
    return "".join(out)


def hbars(items, width=330, row=19, label_w=118):
    """Barres horizontales centrées sur zéro : [(libellé, valeur)] (positif = favorable)."""
    height = row * len(items) + 8
    vmax = max([abs(v) for _, v in items] + [1])
    val_w = 50
    pw = width - label_w - 2 * val_w
    cx = label_w + val_w + pw / 2
    sc = (pw / 2) / vmax
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">']
    out.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="2" y2="{height-4}" stroke="{AXIS}" stroke-width="1"/>')
    for i, (lab, v) in enumerate(items):
        y = 4 + i * row
        bh = row - 7
        w = abs(v) * sc
        x = cx if v >= 0 else cx - w
        if w >= 0.5:
            out.append(f'<rect x="{x:.1f}" y="{y+2:.1f}" width="{max(w,1):.1f}" height="{bh:.1f}" rx="2" fill="{FAV if v >= 0 else DEFAV}"/>')
        out.append(_text(0, y + bh / 2 + 4.6, lab, 7.4, "start", INK))
        tx = (cx + w + 4) if v >= 0 else (cx - w - 4)
        out.append(_text(tx, y + bh / 2 + 4.6, kmoney(v, sign=True) if abs(v) >= 500 else "0", 7.4, "start" if v >= 0 else "end", INK, 600))
    out.append("</svg>")
    return "".join(out)


def monthly_bars(values, ap_values, labels, width=330, height=128, title_max=True, partial=None):
    """Barres mensuelles (réel) + trait de l'an passé. values/ap_values : listes (None = absent).
    partial : indices de mois reconstitués (hachurés)."""
    partial = partial or set()
    ml, mr, mt, mb = 40, 4, 12, 16
    pw, ph = width - ml - mr, height - mt - mb
    allv = [v for v in values + ap_values if v is not None]
    lo, hi = (min(allv + [0]), max(allv + [0])) if allv else (0, 1)
    ticks = nice_ticks(lo, hi, 3)
    y0, y1 = ticks[0], ticks[-1]
    Y = lambda v: mt + ph - (v - y0) / (y1 - y0) * ph
    n = len(labels)
    slot = pw / n
    bw = slot * 0.56
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
           '<defs><pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           f'<rect width="4" height="4" fill="#d6e4f7"/><line x1="0" y1="0" x2="0" y2="4" stroke="{SERIE}" stroke-width="1.3"/></pattern></defs>']
    for t in ticks:
        y = Y(t)
        out.append(f'<line x1="{ml}" x2="{width-mr}" y1="{y:.1f}" y2="{y:.1f}" stroke="{AXIS if t == 0 else GRID}" stroke-width="{1.1 if t == 0 else 0.8}"/>')
        out.append(_text(ml - 5, y + 2.5, axis_label(t), 6.6, "end", MUTED))
    for i, lab in enumerate(labels):
        x = ml + slot * i + (slot - bw) / 2
        v = values[i]
        if v is not None:
            top, bot = Y(max(v, 0)), Y(min(v, 0))
            fill = "url(#hatch)" if i in partial else SERIE
            out.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(bot-top,1):.1f}" rx="1.5" fill="{fill}"/>')
        else:
            out.append(_text(x + bw / 2, Y(0) - 3, "n/d", 6, "middle", MUTED))
        a = ap_values[i]
        if a is not None:
            ya = Y(a)
            out.append(f'<line x1="{x-2:.1f}" x2="{x+bw+2:.1f}" y1="{ya:.1f}" y2="{ya:.1f}" stroke="#ffffff" stroke-width="4.4" stroke-linecap="round"/>')
            out.append(f'<line x1="{x-2:.1f}" x2="{x+bw+2:.1f}" y1="{ya:.1f}" y2="{ya:.1f}" stroke="{AP_TICK}" stroke-width="2.4" stroke-linecap="round"/>')
        out.append(_text(x + bw / 2, height - 4, lab, 6.8, "middle", MUTED))
    out.append("</svg>")
    return "".join(out)


def icon(level, size=9):
    """Icône + couleur par niveau (jamais la couleur seule : libellé à côté)."""
    c = {"critique": "#b3261e", "eleve": "#d9541e", "attention": "#b27c00", "positif": "#008848",
         "erreur": "#b3261e", "manque": "#d9541e", "valider": "#b27c00", "info": "#5a6f8c"}[level]
    s = size
    if level in ("critique", "erreur"):
        shape = f'<rect x="1" y="1" width="{s-2}" height="{s-2}" rx="1.5" fill="{c}"/>'
    elif level in ("eleve", "manque"):
        shape = f'<path d="M{s/2} 0.6 L{s-0.4} {s-0.8} L0.4 {s-0.8} Z" fill="{c}"/>'
    elif level in ("attention", "valider"):
        shape = f'<circle cx="{s/2}" cy="{s/2}" r="{s/2-0.6}" fill="{c}"/>'
    elif level == "positif":
        shape = f'<path d="M1.2 {s*0.55} L{s*0.4} {s-1.4} L{s-1} 1.6" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    else:
        shape = f'<circle cx="{s/2}" cy="{s/2}" r="{s/2-1}" fill="none" stroke="{c}" stroke-width="1.6"/>'
    return f'<svg class="ico" width="{s}" height="{s}" viewBox="0 0 {s} {s}">{shape}</svg>'


PREV = "#b9b8b1"   # an passé (gris)
CUR = SERIE        # année en cours (bleu)


def paired_hbars(items, width=330, label_w=112, prev_label="2025", cur_label="2026"):
    """Barres horizontales appariées : [(libellé, valeur an passé, valeur courante, part courante ou None)].
    Gère les valeurs négatives (axe zéro). Libellé de valeur en k$ au bout de chaque barre."""
    row = 30
    height = row * len(items) + 22
    vals = [abs(v) for _, a, b, _ in items for v in (a, b) if v is not None] + [1]
    vmax = max(vals)
    has_neg = any((v or 0) < 0 for _, a, b, _ in items for v in (a, b))
    val_w = 46
    pw = width - label_w - val_w - (val_w if has_neg else 4)
    x0 = label_w + ((val_w + pw * 0.25) if has_neg else 2)
    span = pw * (0.75 if has_neg else 1.0)
    sc = span / vmax
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">']
    # légende
    out.append(f'<rect x="{label_w}" y="3" width="9" height="7" rx="1.5" fill="{PREV}"/>')
    out.append(_text(label_w + 13, 9.5, prev_label, 7, "start", MUTED))
    out.append(f'<rect x="{label_w + 48}" y="3" width="9" height="7" rx="1.5" fill="{CUR}"/>')
    out.append(_text(label_w + 61, 9.5, cur_label, 7, "start", MUTED))
    out.append(f'<line x1="{x0:.1f}" x2="{x0:.1f}" y1="16" y2="{height-2}" stroke="{AXIS}" stroke-width="1"/>')
    for i, (lab, a, b, share) in enumerate(items):
        y = 18 + i * row
        out.append(_text(0, y + 13.5, lab, 7.4, "start", INK))
        if share is not None:
            out.append(_text(0, y + 22.5, f"{share*100:.0f} % du total".replace(".", ","), 6.3, "start", MUTED))
        for j, (v, col) in enumerate(((a, PREV), (b, CUR))):
            if v is None:
                continue
            by = y + 3 + j * 11
            w = abs(v) * sc
            x = x0 if v >= 0 else x0 - w
            out.append(f'<rect x="{x:.1f}" y="{by:.1f}" width="{max(w, 0.8):.1f}" height="9" rx="1.5" fill="{col}"/>')
            tx = (x0 + w + 3) if v >= 0 else (x0 - w - 3)
            out.append(_text(tx, by + 7.3, kmoney(v), 6.8, "start" if v >= 0 else "end", INK if j else MUTED, 600 if j else 400))
    out.append("</svg>")
    return "".join(out)


CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]   # palette catégorielle validée (skill dataviz)
CAT_OTHER = "#b9b8b1"                                            # « autres » / résiduel


def donut(slices, center_value, center_caption, size=236):
    """Anneau : slices = [(libellé, valeur ≥ 0, couleur)]. Écart de 2 px entre les parts,
    pourcentage affiché à l'extérieur de chaque part (≥ 3 %), total au centre."""
    total = sum(v for _, v, _ in slices if v and v > 0)
    cx = cy = size / 2
    R = size / 2 - 30
    r = R * 0.6
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img">']
    if total <= 0:
        out.append(_text(cx, cy, "n/d", 10, "middle", MUTED))
        out.append("</svg>")
        return "".join(out)
    ang = -math.pi / 2
    for lab, v, col in slices:
        if not v or v <= 0:
            continue
        frac = v / total
        a0, a1 = ang, ang + frac * 2 * math.pi
        if frac >= 0.9999:
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{(R + r) / 2:.2f}" fill="none" stroke="{col}" stroke-width="{R - r:.2f}"/>')
        else:
            large = 1 if (a1 - a0) > math.pi else 0
            p = lambda rad, a: (cx + rad * math.cos(a), cy + rad * math.sin(a))
            x0, y0 = p(R, a0); x1, y1 = p(R, a1); x2, y2 = p(r, a1); x3, y3 = p(r, a0)
            out.append(f'<path d="M{x0:.2f} {y0:.2f} A{R:.2f} {R:.2f} 0 {large} 1 {x1:.2f} {y1:.2f} L{x2:.2f} {y2:.2f} '
                       f'A{r:.2f} {r:.2f} 0 {large} 0 {x3:.2f} {y3:.2f} Z" fill="{col}" stroke="#ffffff" stroke-width="2" stroke-linejoin="round"/>')
        if frac >= 0.03:
            am = (a0 + a1) / 2
            lx, ly = cx + (R + 13) * math.cos(am), cy + (R + 13) * math.sin(am)
            anchor = "start" if math.cos(am) > 0.25 else ("end" if math.cos(am) < -0.25 else "middle")
            out.append(_text(lx, ly + 3.2, f"{frac * 100:.0f} %".replace(".", ","), 8.6, anchor, INK, 700))
        ang = a1
    out.append(_text(cx, cy + 1, center_value, 12.5, "middle", INK, 700))
    out.append(_text(cx, cy + 15, center_caption, 7.6, "middle", MUTED))
    out.append("</svg>")
    return "".join(out)
