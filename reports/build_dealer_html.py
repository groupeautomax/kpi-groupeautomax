import json, base64, html, sys, os

WORKDIR = os.environ.get('KPI_WORKDIR', '.')

D = json.load(open(os.path.join(WORKDIR, 'report_data.json')))
MIX = json.load(open(os.path.join(WORKDIR, 'per_dealer_mix.json')))
DEALERS = D['dealers']
ORDER = D['dealer_order']

# ---------- period tokens (computed once per quarter by period.py, merged into report_data.json) ----------
Y_CUR, Y_PRIOR = D['year_cur'], D['year_prior']
YY_CUR, YY_PRIOR = D['yy_cur'], D['yy_prior']
MOIS_CUR, MOIS_CUR_CAP = D['mois_cur'], D['mois_cur_cap']
DATE_FIN_CUR, DATE_FIN_PRIOR = D['date_fin_cur'], D['date_fin_prior']
NB_MOIS_TXT = D['nb_mois_txt']
PREP_LABEL = D['prep_label']
QUARTER_LABEL = D['quarter_label']

# ---------- formatting helpers (same house style as the group report) ----------

def money(v, decimals=0):
    if v is None:
        return '—'
    sign = '-' if v < 0 else ''
    v = abs(v)
    s = f"{v:,.{decimals}f}".replace(',', ' ').replace('.', ',')
    return f"{sign}{s} $"

def money_m(v):
    if v is None:
        return '—'
    return f"{v/1_000_000:,.2f}".replace(',', 'X').replace('.', ',').replace('X', ' ') + " M$"

def num(v):
    if v is None:
        return '—'
    return f"{v:,.0f}".replace(',', ' ')

def pct(v, decimals=1, signed=False):
    if v is None:
        return '—'
    s = f"{v*100:.{decimals}f}".replace('.', ',')
    if signed and v > 0:
        s = '+' + s
    return s + ' %'

def bps(v):
    if v is None:
        return '—'
    b = v * 10000
    sign = '+' if b >= 0 else ''
    return f"{sign}{b:,.0f}".replace(',', ' ') + ' pdb'

def delta_class(v, invert=False):
    if v is None:
        return 'flat'
    if invert:
        v = -v
    if v > 0.0001:
        return 'pos'
    if v < -0.0001:
        return 'neg'
    return 'flat'

def delta_pct_str(v):
    if v is None:
        return '—'
    sign = '+' if v >= 0 else ''
    return f"{sign}{v*100:.1f}".replace('.', ',') + ' %'

def ratio(v):
    if v is None:
        return '—'
    return f"{v:.2f}".replace('.', ',') + ' : 1'

def esc(s):
    return html.escape(str(s))

CSS = """
@page { size: Letter; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Helvetica Neue', Arial, sans-serif; color: #21201d; font-size: 10.5pt; }
.page { width: 8.5in; min-height: 11in; padding: 0.55in 0.65in 0.7in 0.65in; position: relative; page-break-after: always; }
.page:last-child { page-break-after: auto; }
.eyebrow { font-size: 8.5pt; letter-spacing: 2px; font-weight: 700; color: #c1622f; text-transform: uppercase; margin-bottom: 4px; }
h1.section-title { font-size: 19pt; color: #21201d; margin: 0 0 10px 0; font-weight: 800; }
hr.rule { border: none; border-top: 1.5px solid #c1622f; margin: 0 0 16px 0; }
p { line-height: 1.5; margin: 0 0 10px 0; }
.small { font-size: 8.3pt; color: #6b7280; line-height: 1.4; }
.footer { position: absolute; bottom: 0.35in; left: 0.65in; right: 0.65in; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e4dfd2; padding-top: 8px; }
.footer .logo { font-weight: 800; color: #21201d; font-size: 10pt; letter-spacing: 1px; }
.footer .pageno { font-size: 8.5pt; color: #9ca3af; }

table { width: 100%; border-collapse: collapse; margin: 10px 0 16px 0; font-size: 9pt; }
th { background: #21201d; color: white; text-align: right; padding: 7px 9px; font-size: 8pt; letter-spacing: 0.4px; text-transform: uppercase; font-weight: 700; }
th:first-child { text-align: left; }
td { padding: 6px 9px; border-bottom: 1px solid #ece7db; text-align: right; }
td:first-child { text-align: left; }
tr.total-row td { background: #f2ece0; font-weight: 800; border-top: 1.5px solid #c1622f; border-bottom: 1.5px solid #c1622f; }
tr.section-row td { background: #ece4d3; font-weight: 700; color: #9c5a2e; text-transform: uppercase; font-size: 8pt; letter-spacing: 0.5px; }
tr:nth-child(even):not(.total-row):not(.section-row) td { background: #fbfaf6; }
.pos { color: #2f6b46; font-weight: 700; }
.neg { color: #a5372b; font-weight: 700; }
.flat { color: #6b7280; }

.callout { background: #f2ece0; border-left: 4px solid #c1622f; padding: 14px 18px; margin: 14px 0; }
.callout h3 { margin: 0 0 8px 0; font-size: 10.5pt; }
.callout ol, .callout ul { margin: 0; padding-left: 18px; }
.callout li { margin-bottom: 7px; line-height: 1.45; }

.stat-strip { display: flex; background: #21201d; border-radius: 4px; overflow: hidden; margin: 14px 0; }
.stat-cell { flex: 1; padding: 14px 10px; text-align: center; border-right: 1px solid rgba(255,255,255,0.15); }
.stat-cell:last-child { border-right: none; }
.stat-cell .label { color: #c9c4ba; font-size: 7.3pt; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 5px; }
.stat-cell .value { color: white; font-size: 15pt; font-weight: 800; }
.stat-cell .delta { font-size: 8pt; margin-top: 3px; }
.stat-cell .delta.pos { color: #8fd6a6; }
.stat-cell .delta.neg { color: #f0a89e; }

h2.sub { font-size: 11pt; text-transform: uppercase; letter-spacing: 0.5px; color: #21201d; margin: 18px 0 4px 0; font-weight: 800; }
.section-label { font-size: 8pt; letter-spacing: 1.5px; color: #c1622f; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; }

.cover { background: #21201d; color: white; padding: 70px 60px; margin: -0.55in -0.65in 0 -0.65in; width: calc(8.5in + 0px); height: 6.6in; }
.cover-inner { max-width: 6.5in; }
.cover h1 { font-size: 26pt; letter-spacing: 1.5px; margin: 0 0 4px 0; font-weight: 800; }
.cover .sub1 { font-size: 12.5pt; margin: 24px 0 2px 0; }
.cover .sub2 { color: #c1622f; font-size: 10.5pt; margin: 0 0 26px 0; }
.cover .rule { border-top: 1px solid rgba(255,255,255,0.25); margin: 20px 0; }
.cover .period { font-size: 10.5pt; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px; }
.cover .prepared { color: #c9c4ba; font-size: 9.5pt; }
.confidential-band { background: #ece4d3; text-align: center; padding: 10px; font-size: 8.5pt; letter-spacing: 2px; font-weight: 700; color: #21201d; }
.cover-org { margin-top: 60px; font-size: 13pt; font-weight: 700; color: #21201d; text-align: center; }

.chart-block { text-align: center; margin: 8px 0; }
.chart-block img { width: 100%; max-width: 6.6in; }
.legend-note { font-size: 8pt; color: #6b7280; margin-top: 4px; }
"""

def footer(pageno):
    return f"""<div class="footer"><div class="logo">GROUPEAUTOMAX</div><div class="pageno">Page {pageno}</div></div>"""

def stat_cell(label, value, delta_str, cls):
    return f"""<div class="stat-cell"><div class="label">{esc(label)}</div><div class="value">{value}</div><div class="delta {cls}">{delta_str}</div></div>"""

def fin_row(label, cur, prior, is_pct=False, total=False, invert=False):
    cls = 'total-row' if total else ''
    if is_pct:
        c, p = pct(cur), pct(prior)
        d = bps(cur - prior) if (cur is not None and prior is not None) else '—'
        dcls = delta_class((cur - prior) if (cur is not None and prior is not None) else None, invert=invert)
    else:
        c, p = money(cur), money(prior)
        dpct = None
        if cur is not None and prior is not None and prior != 0:
            dpct = (cur - prior) / abs(prior)
        d = delta_pct_str(dpct)
        dcls = delta_class(dpct, invert=invert)
    return f'<tr class="{cls}"><td>{esc(label)}</td><td>{p}</td><td>{c}</td><td class="{dcls}">{d}</td></tr>'

def vol_row(label, cur, prior):
    dpct = None
    if cur is not None and prior is not None and prior != 0:
        dpct = (cur - prior) / abs(prior)
    dcls = delta_class(dpct)
    return f'<tr><td>{esc(label)}</td><td>{num(prior)}</td><td>{num(cur)}</td><td class="{dcls}">{delta_pct_str(dpct)}</td></tr>'

def ratio_row(label, cur, prior):
    dpct = None
    if cur is not None and prior:
        dpct = (cur - prior) / abs(prior)
    dcls = delta_class(dpct)
    return f'<tr><td>{esc(label)}</td><td>{ratio(prior)}</td><td>{ratio(cur)}</td><td class="{dcls}">{delta_pct_str(dpct)}</td></tr>'

def money_unit_row(label, cur, prior):
    dpct = None
    if cur is not None and prior:
        dpct = (cur - prior) / abs(prior)
    dcls = delta_class(dpct)
    return f'<tr><td>{esc(label)}</td><td>{money(prior)}</td><td>{money(cur)}</td><td class="{dcls}">{delta_pct_str(dpct)}</td></tr>'


def build_dealer_report(key):
    dd = DEALERS[key]
    m = MIX[key]
    name = dd['display_name']
    dept_chart_b64 = base64.b64encode(open(os.path.join(WORKDIR, f'chart_{key}_dept_mix.png'), 'rb').read()).decode()
    exp_chart_b64 = base64.b64encode(open(os.path.join(WORKDIR, f'chart_{key}_expense_mix.png'), 'rb').read()).decode()

    is_hawks = key == 'hawks'
    has_budget = any(DEALERS[key].get(f) is not None for f in [])  # not used, budget omitted throughout

    pages = []

    # ---- Cover
    pages.append(f"""
<div class="page">
  <div class="cover">
    <div class="cover-inner">
      <h1>{esc(name).upper()}</h1>
      <div class="sub1">Rapport de performance</div>
      <div class="sub2">Analyse des résultats d'exploitation &amp; supplément de données</div>
      <div class="rule"></div>
      <div class="period">RÉSULTATS CUMULATIFS ANNÉE À CE JOUR (YTD)</div>
      <div class="period" style="color:#c1622f;">({esc(D['period_label_cur'])})</div>
      <div class="prepared">Préparé en {PREP_LABEL} &middot; à partir du tableau de bord KPI Groupeautomax</div>
    </div>
  </div>
  <div class="confidential-band">CONFIDENTIEL &nbsp;—&nbsp; USAGE INTERNE &nbsp;—&nbsp; DIRECTION SEULEMENT</div>
  <div class="cover-org">{esc(name)}</div>
  <div class="small" style="text-align:center; margin-top:80px;">
    Une concession du Groupeautomax
  </div>
</div>
""")

    # ---- Section 1: intro
    fmt_note_block = (
        f'<p style="margin-bottom:4px;"><strong>Format source.</strong> HAWKS transmet un état financier '
        f'standardisé GM Canada (format « Composite Financial Statement »), sans colonnes budget ni année '
        f'précédente intégrées à la même feuille. La comparaison YTD {Y_PRIOR} de ce rapport provient donc du '
        f'fichier source de {MOIS_CUR} {Y_PRIOR} de HAWKS plutôt que d\'une colonne « année précédente » native.</p>'
    ) if is_hawks else ''

    pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 1</div>
  <h1 class="section-title">Introduction et base de présentation</h1>
  <hr class="rule">
  <p>Ce rapport présente une analyse des résultats d'exploitation de {esc(name)} pour la période de {NB_MOIS_TXT} mois
  terminée le {DATE_FIN_CUR}, comparée à la période correspondante terminée le {DATE_FIN_PRIOR}.</p>

  <div class="callout">
    <h3>YTD {Y_CUR} en un coup d'œil</h3>
    <ul>
      <li><strong>Ventes nettes&nbsp;:</strong> {money_m(dd['ventes_nettes_cur'])}
      ({delta_pct_str(dd['ventes_nettes_delta_pct'])} vs YTD {Y_PRIOR}).</li>
      <li><strong>Profit brut&nbsp;:</strong> {money_m(dd['pb_total_cur'])}
      ({delta_pct_str(dd['pb_total_delta_pct'])} vs YTD {Y_PRIOR}), marge brute de {pct(dd['gross_margin_cur'])}.</li>
      <li><strong>EBT déclaré&nbsp;:</strong> {money_m(dd['ebt_cur'])}
      ({delta_pct_str(dd['ebt_delta_pct'])} vs YTD {Y_PRIOR}).</li>
    </ul>
  </div>

  <h2 class="sub">Base de présentation</h2>
  <p style="margin-bottom:4px;"><strong>Périodes visées.</strong> YTD {Y_CUR} = janvier–{MOIS_CUR} {Y_CUR};
  YTD {Y_PRIOR} = janvier–{MOIS_CUR} {Y_PRIOR}.</p>
  {fmt_note_block}
  <p style="margin-bottom:4px;"><strong>Portée.</strong> Ce rapport porte uniquement sur {esc(name)}. Pour une vue
  consolidée des cinq concessions du Groupe, voir le rapport de performance du Groupe.</p>
  <p><strong>Portefeuille immobilier, acquisitions et pipeline stratégique.</strong> Ce rapport ne contient pas de
  données financières sur l'immobilier, les acquisitions ou un pipeline de développement — ces informations ne
  font pas partie des données extraites dans le tableau de bord KPI actuel et ne sont donc pas incluses ici.</p>
</div>
""")

    # ---- Section 2: performance
    stats = f"""
<div class="stat-strip">
  {stat_cell('Ventes nettes', money_m(dd['ventes_nettes_cur']), delta_pct_str(dd['ventes_nettes_delta_pct'])+f' vs YTD{YY_PRIOR}', delta_class(dd['ventes_nettes_delta_pct']))}
  {stat_cell('Profit brut', money_m(dd['pb_total_cur']), delta_pct_str(dd['pb_total_delta_pct'])+f' vs YTD{YY_PRIOR}', delta_class(dd['pb_total_delta_pct']))}
  {stat_cell('Marge brute', pct(dd['gross_margin_cur']), bps(dd['gross_margin_cur']-dd['gross_margin_prior'])+f' vs YTD{YY_PRIOR}', delta_class(dd['gross_margin_cur']-dd['gross_margin_prior']))}
  {stat_cell('EBT déclaré', money_m(dd['ebt_cur']), delta_pct_str(dd['ebt_delta_pct'])+f' vs YTD{YY_PRIOR}', delta_class(dd['ebt_delta_pct']))}
  {stat_cell('EBT % des ventes', pct(dd['ebt_pct_revenue_cur']), bps(dd['ebt_pct_revenue_cur']-dd['ebt_pct_revenue_prior'])+f' vs YTD{YY_PRIOR}', delta_class(dd['ebt_pct_revenue_cur']-dd['ebt_pct_revenue_prior']))}
</div>
"""
    fin_rows = "".join([
        fin_row('Ventes nettes', dd['ventes_nettes_cur'], dd['ventes_nettes_prior']),
        fin_row('Profit brut', dd['pb_total_cur'], dd['pb_total_prior']),
        fin_row('Marge brute', dd['gross_margin_cur'], dd['gross_margin_prior'], is_pct=True),
        fin_row('Dépenses totales', dd['opex_cur'], dd['opex_prior'], invert=True),
        fin_row('Profit d’exploitation', dd['operating_profit_cur'], dd['operating_profit_prior']),
        fin_row('Autres revenus (net)', dd['autres_revenus_cur'], dd['autres_revenus_prior']),
        fin_row('EBT déclaré', dd['ebt_cur'], dd['ebt_prior'], total=True),
        fin_row('EBT % des ventes', dd['ebt_pct_revenue_cur'], dd['ebt_pct_revenue_prior'], is_pct=True),
        fin_row('EBT % du profit brut', dd['ebt_pct_gp_cur'], dd['ebt_pct_gp_prior'], is_pct=True),
        fin_row('Dépenses % du profit brut', dd['expenses_pct_gp_cur'], dd['expenses_pct_gp_prior'], is_pct=True, invert=True),
    ])

    pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 2</div>
  <h1 class="section-title">Performance financière</h1>
  <hr class="rule">
  {stats}
  <h2 class="sub">Sommaire financier</h2>
  <table>
    <tr><th>Indicateur financier</th><th>YTD {Y_PRIOR}</th><th>YTD {Y_CUR}</th><th>Δ</th></tr>
    {fin_rows}
  </table>
  <p class="small">Le profit d'exploitation est calculé comme le profit brut moins les dépenses totales, avant
  autres revenus. Toutes les valeurs proviennent directement des états financiers extraits par le tableau de bord
  KPI.</p>
</div>
""")

    # ---- EBITDA note
    if dd['ebitda_cur'] is not None:
        if dd['ebitda_prior'] is not None:
            ebitda_rows = "".join([
                fin_row('EBITDA', dd['ebitda_cur'], dd['ebitda_prior'], total=True),
                fin_row('EBITDA % des ventes', dd['ebitda_pct_revenue_cur'], dd['ebitda_pct_revenue_prior'], is_pct=True),
            ])
            ebitda_note = ("EBITDA = profit brut + autres revenus − dépenses, avant amortissement.") if not is_hawks else (
                "EBITDA calculé (EBT + amortissement, à partir des trois postes d'amortissement détaillés dans "
                "l'état financier HAWKS) plutôt que lu directement, le format GM Canada n'ayant pas de ligne "
                "« BAIIA Opérationnel » native.")
            ebitda_block = f"""
  <h2 class="sub">EBITDA</h2>
  <table>
    <tr><th>EBITDA</th><th>YTD {Y_PRIOR}</th><th>YTD {Y_CUR}</th><th>Δ</th></tr>
    {ebitda_rows}
  </table>
  <p class="small">{ebitda_note}</p>
"""
        else:
            ebitda_block = f"""
  <h2 class="sub">EBITDA</h2>
  <table>
    <tr><th>EBITDA</th><th>YTD {Y_CUR}</th></tr>
    <tr class="total-row"><td>EBITDA</td><td>{money(dd['ebitda_cur'])}</td></tr>
  </table>
  <p class="small">EBITDA calculé (EBT + amortissement, à partir des trois postes d'amortissement détaillés dans
  l'état financier HAWKS) plutôt que lu directement. La comparaison YTD {Y_PRIOR} n'est pas encore disponible pour
  HAWKS — son fichier source de {MOIS_CUR} {Y_PRIOR} n'a pas été retraité avec ce calcul.</p>
"""
    else:
        ebitda_block = """
  <div class="nd-box" style="background:#f8f6f0;border:1.5px dashed #c9c2b4;border-radius:4px;padding:18px;text-align:center;color:#8a8371;font-size:9.5pt;">
    EBITDA — Données non disponibles pour cette concession.
  </div>
"""

    pages.append(f"""
<div class="page">
  <div class="section-label">Section 2 (suite)</div>
  {ebitda_block}
  <h2 class="sub">Indicateurs opérationnels clés</h2>
  <table>
    <tr><th>Indicateur opérationnel</th><th>YTD {Y_PRIOR}</th><th>YTD {Y_CUR}</th><th>Δ</th></tr>
    <tr class="section-row"><td colspan="4">Volume</td></tr>
    {vol_row('Unités neuves (détail)', dd['unites_neuf_cur'], dd['unites_neuf_prior'])}
    {vol_row('Unités usagées (détail)', dd['unites_usage_cur'], dd['unites_usage_prior'])}
    <tr class="total-row"><td>Total unités détail</td><td>{num(dd["total_retail_units_prior"])}</td><td>{num(dd["total_retail_units_cur"])}</td><td class="{delta_class(dd["total_retail_units_delta_pct"])}">{delta_pct_str(dd["total_retail_units_delta_pct"])}</td></tr>
    {ratio_row('Ratio neuf : usagé', dd['new_used_ratio_cur'], dd['new_used_ratio_prior'])}
    {vol_row('Unités flottes', dd['unites_flottes_cur'], dd['unites_flottes_prior'])}
    <tr class="section-row"><td colspan="4">Profit brut par unité</td></tr>
    {money_unit_row('Profit brut par unité — neuf', dd['gpa_neuf_cur'], dd['gpa_neuf_prior'])}
    {money_unit_row('Profit brut par unité — usagé', dd['gpa_usage_cur'], dd['gpa_usage_prior'])}
    <tr class="section-row"><td colspan="4">Profit brut par département</td></tr>
    {fin_row('Véhicules neufs', dd['pb_neuf_cur'], dd['pb_neuf_prior'])}
    {fin_row('Véhicules usagés', dd['pb_usage_cur'], dd['pb_usage_prior'])}
    {fin_row('Service', dd['pb_service_cur'], dd['pb_service_prior'])}
    {fin_row('Carrosserie', dd['pb_carrosserie_cur'], dd['pb_carrosserie_prior'])}
    {fin_row('Pièces', dd['pb_pieces_cur'], dd['pb_pieces_prior'])}
    {fin_row('Total profit brut', dd['pb_total_cur'], dd['pb_total_prior'], total=True)}
  </table>
</div>
""")

    # ---- Section 3: operational analysis
    exp_total_prior = -(dd["depenses_variables_prior"]+dd["depenses_personnel_prior"]+dd["depenses_semifixes_prior"])
    exp_total_cur = -(dd["depenses_variables_cur"]+dd["depenses_personnel_cur"]+dd["depenses_semifixes_cur"])
    exp_rows = "".join([
        fin_row('Dépenses variables', -dd['depenses_variables_cur'], -dd['depenses_variables_prior'], invert=True),
        fin_row('Dépenses de personnel', -dd['depenses_personnel_cur'], -dd['depenses_personnel_prior'], invert=True),
        fin_row('Dépenses semi-fixes', -dd['depenses_semifixes_cur'], -dd['depenses_semifixes_prior'], invert=True),
        fin_row('Total — 3 catégories suivies', exp_total_cur, exp_total_prior, invert=True, total=True),
    ])
    fixed_note = ("Pour HAWKS, ces trois catégories couvrent la quasi-totalité des dépenses (le poste « fixe » du "
                  "format GM Canada est déjà regroupé dans les dépenses semi-fixes ci-dessus).") if is_hawks else (
                  "Ces trois catégories ne représentent pas la totalité des dépenses d'exploitation — une portion "
                  "« frais fixes » (loyer, amortissement, taxes foncières, assurances) n'est pas isolée comme "
                  "indicateur distinct et apparaît comme un solde résiduel dans le graphique de répartition.")

    pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 3</div>
  <h1 class="section-title">Analyse opérationnelle</h1>
  <hr class="rule">
  <h2 class="sub">Dépenses par catégorie</h2>
  <table>
    <tr><th>Dépenses par catégorie</th><th>YTD {Y_PRIOR}</th><th>YTD {Y_CUR}</th><th>Δ</th></tr>
    {exp_rows}
  </table>
  <p class="small">{fixed_note}</p>

  <h2 class="sub">Répartition du profit brut par département</h2>
  <div class="chart-block"><img src="data:image/png;base64,{dept_chart_b64}"></div>
</div>
""")

    pages.append(f"""
<div class="page">
  <div class="section-label">Section 3 (suite)</div>
  <h2 class="sub" style="margin-top:0;">Répartition des dépenses d'exploitation</h2>
  <div class="chart-block"><img src="data:image/png;base64,{exp_chart_b64}"></div>
  <p class="legend-note">Part des dépenses totales de la concession.</p>
</div>
""")

    # ---- Perspectives
    biggest_dept_delta = max(
        [('Véhicules neufs', dd['pb_neuf_delta_pct']), ('Véhicules usagés', dd['pb_usage_delta_pct']),
         ('Service', dd['pb_service_delta_pct']), ('Carrosserie', dd['pb_carrosserie_delta_pct']),
         ('Pièces', dd['pb_pieces_delta_pct'])],
        key=lambda t: abs(t[1]) if t[1] is not None else -1
    )
    ebt_trend = "s'est améliorée" if (dd['ebt_delta_pct'] or 0) >= 0 else "a reculé"

    pages.append(f"""
<div class="page">
  <div class="eyebrow">Perspectives</div>
  <h1 class="section-title">Ce que les données montrent</h1>
  <hr class="rule">
  <div class="callout">
    <h3>Constats — YTD {Y_CUR} vs YTD {Y_PRIOR}</h3>
    <ul>
      <li><strong>Rentabilité.</strong> L'EBT déclaré {ebt_trend} de {pct(abs(dd['ebt_delta_pct']))} à
      {money_m(dd['ebt_cur'])}, soit {pct(dd['ebt_pct_revenue_cur'])} des ventes (contre
      {pct(dd['ebt_pct_revenue_prior'])} il y a un an).</li>
      <li><strong>Volume.</strong> Les unités neuves sont passées de {num(dd['unites_neuf_prior'])} à
      {num(dd['unites_neuf_cur'])} ({delta_pct_str(dd['unites_neuf_delta_pct'])}), les unités usagées de
      {num(dd['unites_usage_prior'])} à {num(dd['unites_usage_cur'])} ({delta_pct_str(dd['unites_usage_delta_pct'])}).</li>
      <li><strong>Département le plus mouvementé.</strong> {esc(biggest_dept_delta[0])} affiche la plus forte
      variation de profit brut du département ({delta_pct_str(biggest_dept_delta[1])}).</li>
      <li><strong>Dépenses.</strong> Les dépenses totales représentent {pct(dd['expenses_pct_gp_cur'])} du profit
      brut, contre {pct(dd['expenses_pct_gp_prior'])} il y a un an.</li>
    </ul>
  </div>
  <div class="nd-box" style="background:#f8f6f0;border:1.5px dashed #c9c2b4;border-radius:4px;padding:18px;text-align:center;color:#8a8371;font-size:9.5pt;">
    Priorités de gestion et plans d'action — Données non disponibles. Les observations ci-dessus sont des
    constats basés uniquement sur les chiffres YTD et ne remplacent pas la planification de la direction.
  </div>
</div>
""")

    # ---- assemble
    body = ""
    for i, p in enumerate(pages, start=1):
        if i == 1:
            body += p
        else:
            body += p[:p.rfind('</div>')] + footer(i) + p[p.rfind('</div>'):]

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{esc(name)} — Rapport de performance YTD {Y_CUR}</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>""", len(pages)


if __name__ == '__main__':
    keys = sys.argv[1:] or ORDER
    for key in keys:
        html_doc, n = build_dealer_report(key)
        out_path = os.path.join(WORKDIR, f'report_{key}.html')
        open(out_path, 'w').write(html_doc)
        print(key, '->', out_path, n, 'pages')
