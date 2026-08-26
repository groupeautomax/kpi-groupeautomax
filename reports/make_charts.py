import json
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

WORKDIR = os.environ.get('KPI_WORKDIR', '.')

mix = json.load(open(os.path.join(WORKDIR, 'mix_data.json')))
d = json.load(open(os.path.join(WORKDIR, 'report_data.json')))
Y_CUR, Y_PRIOR = d['year_cur'], d['year_prior']

INK = '#21201d'
ACCENT = '#c1622f'
CREAM = '#f2ece0'
MUTED = '#6b7280'

# Fixed categorical order + colors, validated against the dataviz skill's
# accessibility checks (scripts/validate_palette.js -- lightness band, chroma
# floor, CVD adjacent-pair separation, normal-vision floor): all PASS for both
# 6-slot (dept mix) and the first-3-slot (expense mix) sequences. The trailing
# neutral gray ("Autres" / "Fixes / non ventilées") is a deliberate residual
# bucket, not a tracked category, so it is exempt by design from the chroma
# check -- it is meant to read as "uncategorized", not as an identity color.
DEPT_COLORS = {
    'Neuf': '#2a78d6', 'Usagé': '#eb6834', 'Service': '#1baf7a',
    'Carrosserie': '#eda100', 'Pièces': '#e87ba4', 'Autres': '#c9c2b4',
}
EXP_COLORS = {
    'Variables': '#2a78d6', 'Personnel': '#eb6834', 'Semi-fixes': '#1baf7a',
    'Fixes / non ventilées': '#c9c2b4',
}
# Per-hue label text color (white vs. ink), chosen by WCAG contrast against
# each wedge fill rather than assumed -- only the two darkest hues (blue,
# and pure green, unused here) read better with white text; the rest read
# better with the report's dark ink.
LABEL_ON_DARK = {'Neuf', 'Variables'}  # slot 1 (blue) -- only hue dark enough for white text

plt.rcParams['font.family'] = 'DejaVu Sans'


def donut_pair(mix_prior, mix_cur, total_prior, total_cur, colors, title_prior, title_cur, fname, fmt_total):
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 5.2))
    for ax, mx, total, subtitle in zip(axes, [mix_prior, mix_cur], [total_prior, total_cur], [title_prior, title_cur]):
        labels = list(mx.keys())
        values = [max(v, 0) for v in mx.values()]  # guard negatives for wedge sizing
        cols = [colors[l] for l in labels]
        wedges, _ = ax.pie(values, colors=cols, startangle=90, counterclock=False,
                            wedgeprops=dict(width=0.42, edgecolor='white', linewidth=2))
        for w, l, v in zip(wedges, labels, mx.values()):
            ang = (w.theta2 + w.theta1) / 2
            x = 0.78 * np.cos(np.radians(ang))
            y = 0.78 * np.sin(np.radians(ang))
            pct = v / total * 100 if total else 0
            if pct >= 4:
                ax.text(x, y, f"{pct:.1f}%", ha='center', va='center', fontsize=9.5,
                        color='white' if l in LABEL_ON_DARK else INK, fontweight='bold')
        ax.set_title(subtitle, fontsize=11, color=INK, fontweight='bold', pad=14)
        ax.text(0, 0, fmt_total(total), ha='center', va='center', fontsize=12.5, color=INK, fontweight='bold')
    labels = list(mix_cur.keys())
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[l]) for l in labels]
    fig.legend(handles, labels, loc='lower center', ncol=len(labels), frameon=False,
               fontsize=9.5, bbox_to_anchor=(0.5, -0.02))
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(fname, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()


def fmt_m(v):
    return f"${v/1_000_000:.2f}M"


donut_pair(mix['dept_mix_prior'], mix['dept_mix_cur'], mix['dept_total_prior'], mix['dept_total_cur'],
           DEPT_COLORS, f'YTD {Y_PRIOR} · ' + fmt_m(mix['dept_total_prior']), f'YTD {Y_CUR} · ' + fmt_m(mix['dept_total_cur']),
           os.path.join(WORKDIR, 'chart_dept_mix.png'), fmt_m)

donut_pair(mix['expense_mix_prior'], mix['expense_mix_cur'], mix['expense_total_prior'], mix['expense_total_cur'],
           EXP_COLORS, f'YTD {Y_PRIOR} · ' + fmt_m(mix['expense_total_prior']), f'YTD {Y_CUR} · ' + fmt_m(mix['expense_total_cur']),
           os.path.join(WORKDIR, 'chart_expense_mix.png'), fmt_m)

print('group charts done')
