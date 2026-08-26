import json, base64, html, os

WORKDIR = os.environ.get('KPI_WORKDIR', '.')

D = json.load(open(os.path.join(WORKDIR, 'report_data.json')))
SC = json.load(open(os.path.join(WORKDIR, 'scorecard.json')))
MIX = json.load(open(os.path.join(WORKDIR, 'mix_data.json')))
G = D['group']
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

DEPT_CHART_B64 = base64.b64encode(open(os.path.join(WORKDIR, 'chart_dept_mix.png'), 'rb').read()).decode()
EXP_CHART_B64 = base64.b64encode(open(os.path.join(WORKDIR, 'chart_expense_mix.png'), 'rb').read()).decode()

# ---------- formatting helpers (fr-CA house style, matching the KPI dashboard) ----------

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

def money_k(v):
    if v is None:
        return '—'
    return f"{v/1000:,.0f}".replace(',', ' ') + " k$"

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

# ---------- CSS ----------

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
.cover h1 { font-size: 30pt; letter-spacing: 3px; margin: 0 0 4px 0; font-weight: 800; }
.cover .sub1 { font-size: 12.5pt; margin: 24px 0 2px 0; }
.cover .sub2 { color: #c1622f; font-size: 10.5pt; margin: 0 0 26px 0; }
.cover .rule { border-top: 1px solid rgba(255,255,255,0.25); margin: 20px 0; }
.cover .period { font-size: 10.5pt; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px; }
.cover .prepared { color: #c9c4ba; font-size: 9.5pt; }
.confidential-band { background: #ece4d3; text-align: center; padding: 10px; font-size: 8.5pt; letter-spacing: 2px; font-weight: 700; color: #21201d; }
.cover-org { margin-top: 60px; font-size: 13pt; font-weight: 700; color: #21201d; text-align: center; }

.grid2 { display: flex; gap: 22px; }
.grid2 > div { flex: 1; }

.nd-box { background: #f8f6f0; border: 1.5px dashed #c9c2b4; border-radius: 4px; padding: 22px; text-align: center; color: #8a8371; font-size: 9.5pt; margin: 16px 0; }
.nd-box .nd-title { font-weight: 700; color: #6b7280; margin-bottom: 6px; font-size: 10pt; }

.status-tag { font-size: 7.6pt; font-weight: 800; letter-spacing: 0.4px; padding: 3px 7px; border-radius: 3px; white-space: nowrap; }
.status-croissance { background: #e3f1e8; color: #2f6b46; }
.status-stable { background: #eef1f5; color: #445; }
.status-focus { background: #fbeee0; color: #9c5a2e; }
.status-priorite { background: #f7e2de; color: #a5372b; }

.chart-block { text-align: center; margin: 8px 0; }
.chart-block img { width: 100%; max-width: 6.6in; }
.legend-note { font-size: 8pt; color: #6b7280; margin-top: 4px; }

.two-col-note { columns: 2; column-gap: 24px; font-size: 8.3pt; color: #6b7280; }
"""

def footer(pageno):
    return f"""<div class="footer"><div class="logo">GROUPEAUTOMAX</div><div class="pageno">Page {pageno}</div></div>"""

pages = []

# ============================================================ COVER
pages.append(f"""
<div class="page">
  <div class="cover">
    <div class="cover-inner">
      <h1>GROUPEAUTOMAX</h1>
      <div class="sub1">Rapport de performance</div>
      <div class="sub2">Analyse des résultats d'exploitation &amp; supplément de données</div>
      <div class="rule"></div>
      <div class="period">RÉSULTATS CUMULATIFS ANNÉE À CE JOUR (YTD)</div>
      <div class="period" style="color:#c1622f;">({esc(D['period_label_cur'])})</div>
      <div class="prepared">Préparé en {PREP_LABEL} &middot; à partir du tableau de bord KPI Groupeautomax</div>
    </div>
  </div>
  <div class="confidential-band">CONFIDENTIEL &nbsp;—&nbsp; USAGE INTERNE &nbsp;—&nbsp; DIRECTION SEULEMENT</div>
  <div class="cover-org">Groupe Automax</div>
  <div class="small" style="text-align:center; margin-top:80px;">
    Concessionnaires couverts&nbsp;: BMW Sherbrooke &middot; Volkswagen &middot; STM (Ste-Marie Automobiles) &middot; Hyundai &middot; HAWKS
  </div>
</div>
""")

# ============================================================ SECTION 1
pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 1</div>
  <h1 class="section-title">Introduction et base de présentation</h1>
  <hr class="rule">
  <p>Ce rapport présente une analyse des résultats d'exploitation du Groupeautomax pour la période de {NB_MOIS_TXT} mois
  terminée le {DATE_FIN_CUR}, comparée à la période correspondante terminée le {DATE_FIN_PRIOR}. L'analyse couvre
  les cinq concessions actives dans le tableau de bord KPI du Groupe&nbsp;: BMW Sherbrooke, Volkswagen, STM
  (Ste-Marie Automobiles), Hyundai et HAWKS. Chaque concession conserve son propre format d'état financier
  source, ce qui explique pourquoi certaines mesures (budget, année précédente, EBITDA) ne sont pas disponibles
  pour toutes les concessions — chaque écart de ce type est identifié dans le rapport plutôt que d'être estimé.</p>

  <div class="callout">
    <h3>YTD {Y_CUR} en un coup d'œil — Trois observations</h3>
    <ol>
      <li><strong>Les ventes progressent, la rentabilité recule.</strong> Les ventes nettes du Groupe ont
      augmenté de {pct(G['ventes_nettes_delta_pct'], signed=True)} à {money_m(G['ventes_nettes_cur'])}, mais le
      profit brut a reculé de {pct(abs(G['pb_total_delta_pct']))} à {money_m(G['pb_total_cur'])} et la marge
      brute a cédé {bps(G['gross_margin_cur']-G['gross_margin_prior'])} à {pct(G['gross_margin_cur'])}.</li>
      <li><strong>Les dépenses ont mieux résisté que le profit brut, mais absorbent une part croissante du profit.</strong>
      Les dépenses totales ont reculé de {pct(abs(G['opex_delta_pct']))}, mais comme le profit brut a reculé
      davantage, les dépenses représentent maintenant {pct(G['expenses_pct_gp_cur'])} du profit brut,
      contre {pct(G['expenses_pct_gp_prior'])} il y a un an.</li>
      <li><strong>La concentration des profits demeure élevée mais commence à se rééquilibrer.</strong>
      {esc(SC['concentration'][0]['display_name'])} demeure la plus grande source de profit avant impôt du Groupe
      ({pct(SC['concentration'][0]['share_cur'])} du total), en baisse par rapport à
      {pct(SC['concentration'][0]['share_prior'])} l'an dernier.</li>
    </ol>
  </div>

  <h2 class="sub">Base de présentation</h2>
  <p style="margin-bottom:4px;"><strong>Périodes visées.</strong> YTD {Y_CUR} = janvier–{MOIS_CUR} {Y_CUR};
  YTD {Y_PRIOR} = janvier–{MOIS_CUR} {Y_PRIOR} (période comparable extraite des états financiers de {MOIS_CUR} {Y_PRIOR} de
  chaque concession).</p>
  <p style="margin-bottom:4px;"><strong>Portée.</strong> Les cinq concessions présentées sont celles actuellement
  suivies dans le tableau de bord KPI du Groupe. Aucune acquisition n'a été complétée durant la période — la
  section 5 (Acquisitions) est donc sans objet pour ce rapport.</p>
  <p style="margin-bottom:4px;"><strong>Mesures de profit.</strong> L'EBT déclaré (« Profit net avant impôt »)
  provient directement des états financiers de chaque concession. L'EBITDA de BMW Sherbrooke, Volkswagen, STM et
  Hyundai est une ligne native de leur état financier (« BAIIA Opérationnel »). HAWKS (format GM
  Canada) n'a pas cette ligne, mais son état financier détaille l'amortissement sur trois postes distincts; son
  EBITDA YTD {Y_CUR} est donc calculé (EBT + amortissement) plutôt que lu directement — une comparaison contre
  {MOIS_CUR} {Y_PRIOR} n'est pas encore possible pour HAWKS, le fichier source de cette période n'ayant pas été retraité
  avec ce calcul. Voir la note à la section 2.</p>
  <p><strong>Portefeuille immobilier, acquisitions et pipeline stratégique.</strong> Ce rapport ne contient pas de
  données financières sur l'immobilier, les acquisitions en cours ou un pipeline de développement — ces
  informations ne font pas partie des données extraites dans le tableau de bord KPI actuel. Les sections
  correspondantes (5, 6, 7) sont incluses pour respecter la structure standard du rapport, mais indiquent
  clairement l'absence de données.</p>
</div>
""")

# ============================================================ SECTION 2 — Group performance
def stat_cell(label, value, delta_str, cls):
    return f"""<div class="stat-cell"><div class="label">{esc(label)}</div><div class="value">{value}</div><div class="delta {cls}">{delta_str}</div></div>"""

stats = f"""
<div class="stat-strip">
  {stat_cell('Ventes nettes', money_m(G['ventes_nettes_cur']), delta_pct_str(G['ventes_nettes_delta_pct'])+f' vs YTD{YY_PRIOR}', delta_class(G['ventes_nettes_delta_pct']))}
  {stat_cell('Profit brut', money_m(G['pb_total_cur']), delta_pct_str(G['pb_total_delta_pct'])+f' vs YTD{YY_PRIOR}', delta_class(G['pb_total_delta_pct']))}
  {stat_cell('Marge brute', pct(G['gross_margin_cur']), bps(G['gross_margin_cur']-G['gross_margin_prior'])+f' vs YTD{YY_PRIOR}', delta_class(G['gross_margin_cur']-G['gross_margin_prior']))}
  {stat_cell('EBT déclaré', money_m(G['ebt_cur']), delta_pct_str(G['ebt_delta_pct'])+f' vs YTD{YY_PRIOR}', delta_class(G['ebt_delta_pct']))}
  {stat_cell('EBT % des ventes', pct(G['ebt_pct_revenue_cur']), bps(G['ebt_pct_revenue_cur']-G['ebt_pct_revenue_prior'])+f' vs YTD{YY_PRIOR}', delta_class(G['ebt_pct_revenue_cur']-G['ebt_pct_revenue_prior']))}
</div>
"""

def fin_row(label, cur, prior, is_money=True, is_pct=False, total=False, invert=False, decimals=1):
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

fin_summary_rows = "".join([
    fin_row('Ventes nettes', G['ventes_nettes_cur'], G['ventes_nettes_prior']),
    fin_row('Profit brut', G['pb_total_cur'], G['pb_total_prior']),
    fin_row('Marge brute', G['gross_margin_cur'], G['gross_margin_prior'], is_pct=True),
    fin_row('Dépenses totales', G['opex_cur'], G['opex_prior'], invert=True),
    fin_row('Profit d’exploitation', G['operating_profit_cur'], G['operating_profit_prior']),
    fin_row('Autres revenus (net)', G['autres_revenus_cur'], G['autres_revenus_prior']),
    fin_row('EBT déclaré', G['ebt_cur'], G['ebt_prior'], total=True),
    fin_row('EBT % des ventes', G['ebt_pct_revenue_cur'], G['ebt_pct_revenue_prior'], is_pct=True),
    fin_row('EBT % du profit brut', G['ebt_pct_gp_cur'], G['ebt_pct_gp_prior'], is_pct=True),
    fin_row('Dépenses % du profit brut', G['expenses_pct_gp_cur'], G['expenses_pct_gp_prior'], is_pct=True, invert=True),
])

pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 2</div>
  <h1 class="section-title">Performance du Groupe</h1>
  <hr class="rule">
  <p>Vue consolidée des cinq concessions du Groupe pour les {NB_MOIS_TXT} premiers mois de {Y_CUR}, comparée à la même
  période en {Y_PRIOR}.</p>
  {stats}
  <h2 class="sub">Sommaire financier — Groupe (5 concessions)</h2>
  <table>
    <tr><th>Indicateur financier</th><th>YTD {Y_PRIOR}</th><th>YTD {Y_CUR}</th><th>Δ</th></tr>
    {fin_summary_rows}
  </table>
  <p class="small">Périmètre&nbsp;: cinq concessions (BMW Sherbrooke, Volkswagen, STM, Hyundai, HAWKS). Le profit
  d'exploitation est calculé comme le profit brut moins les dépenses totales, avant autres revenus. Toutes les
  valeurs proviennent directement des états financiers extraits par le tableau de bord KPI.</p>
</div>
""")

# ============================================================ EBT per dealer + EBITDA reconciliation
ebt_rows = ""
for k in ORDER:
    dd = DEALERS[k]
    ebt_rows += f'<tr><td>{esc(dd["display_name"])}</td><td>{money(dd["ebt_prior"])}</td><td>{money(dd["ebt_cur"])}</td></tr>'
ebt_rows += f'<tr class="total-row"><td>Total — 5 concessions</td><td>{money(G["ebt_prior"])}</td><td>{money(G["ebt_cur"])}</td></tr>'

ebitda_all5 = [k for k in ORDER if DEALERS[k]['ebitda_cur'] is not None]
ebitda_yoy_avail = [k for k in ORDER if DEALERS[k]['ebitda_cur'] is not None and DEALERS[k]['ebitda_prior'] is not None]
ebitda_5_cur = sum(DEALERS[k]['ebitda_cur'] for k in ebitda_all5)
ebitda_yoy_cur = sum(DEALERS[k]['ebitda_cur'] for k in ebitda_yoy_avail)
ebitda_yoy_prior = sum(DEALERS[k]['ebitda_prior'] for k in ebitda_yoy_avail)
ebitda_yoy_names = ", ".join(DEALERS[k]['display_name'] for k in ebitda_yoy_avail)
hawks_ebitda_only = [k for k in ebitda_all5 if k not in ebitda_yoy_avail]

if hawks_ebitda_only:
    _pending_names = ", ".join(DEALERS[k]['display_name'] for k in hawks_ebitda_only)
    ebitda_reconciliation_note = (
        f'<p class="small"><strong>Note&nbsp;:</strong> une comparaison annuelle de l\'EBITDA n\'est présentée que pour '
        f'{esc(ebitda_yoy_names)}, les {len(ebitda_yoy_avail)} concessions dont {MOIS_CUR} {Y_PRIOR} est déjà retraité avec ce calcul. '
        f'L\'EBITDA YTD {Y_CUR} de {esc(_pending_names)} figure dans le tableau ci-dessus, mais son fichier source de '
        f'{MOIS_CUR} {Y_PRIOR} n\'a pas encore été retraité avec la même méthode — sa comparaison annuelle sera disponible '
        f'dans un prochain rapport. {esc(_pending_names)} est néanmoins inclus dans toutes les autres mesures du rapport '
        f'(EBT, profit brut, dépenses, volumes) pour les deux années.</p>'
    )
else:
    ebitda_reconciliation_note = (
        f'<p class="small">EBT et EBITDA déclarés proviennent directement des états financiers de chaque concession, '
        f'tels qu\'extraits par le tableau de bord KPI, pour les {len(ebitda_yoy_avail)} concessions du Groupe.</p>'
    )

pages.append(f"""
<div class="page">
  <div class="section-label">Section 2 (suite)</div>
  <h2 class="sub" style="margin-top:0;">EBT déclaré par concession</h2>
  <table>
    <tr><th>Concession</th><th>EBT YTD {Y_PRIOR}</th><th>EBT YTD {Y_CUR}</th></tr>
    {ebt_rows}
  </table>
  <p class="small">EBT = profit net avant impôt, tel que déclaré dans les états financiers de chaque concession.
  Aucun ajustement de normalisation (éléments non récurrents) n'est appliqué — les données sources extraites par
  le tableau de bord ne distinguent pas les éléments ponctuels d'aucune des cinq concessions.</p>

  <h2 class="sub">EBITDA — YTD {Y_CUR} ({len(ebitda_all5)} concessions)</h2>
  <table>
    <tr><th>Concession</th><th>EBITDA YTD {Y_CUR}</th></tr>
    {"".join(f'<tr><td>{esc(DEALERS[k]["display_name"])}</td><td>{money(DEALERS[k]["ebitda_cur"])}</td></tr>' for k in ORDER)}
    <tr class="total-row"><td>Total — {len(ebitda_all5)} concessions</td><td>{money(ebitda_5_cur)}</td></tr>
  </table>
  <p class="small">Pour BMW Sherbrooke, Volkswagen, STM et Hyundai, l'EBITDA est une ligne native de leur état
  financier (« BAIIA Opérationnel »). Pour HAWKS, il est calculé (EBT + amortissement, à partir des trois postes
  d'amortissement détaillés dans son état financier){" -- voir la note ci-dessous." if hawks_ebitda_only else "."}</p>

  <h2 class="sub">Rapprochement EBITDA — variation annuelle ({esc(ebitda_yoy_names)})</h2>
  <table>
    <tr><th>Rapprochement EBITDA</th><th>YTD {Y_PRIOR}</th><th>YTD {Y_CUR}</th><th>Δ</th></tr>
    {fin_row(f'EBT déclaré ({len(ebitda_yoy_avail)} concessions)', sum(DEALERS[k]['ebt_cur'] for k in ebitda_yoy_avail), sum(DEALERS[k]['ebt_prior'] for k in ebitda_yoy_avail))}
    {fin_row(f'EBITDA ({len(ebitda_yoy_avail)} concessions)', ebitda_yoy_cur, ebitda_yoy_prior, total=True)}
    {fin_row(f'EBITDA % des ventes ({len(ebitda_yoy_avail)} concessions)', ebitda_yoy_cur / sum(DEALERS[k]['ventes_nettes_cur'] for k in ebitda_yoy_avail), ebitda_yoy_prior / sum(DEALERS[k]['ventes_nettes_prior'] for k in ebitda_yoy_avail), is_pct=True)}
  </table>
  {ebitda_reconciliation_note}
</div>
""")

pages.append(f"""
<div class="page">
  <div class="section-label">Section 2 (suite)</div>
  <div class="callout" style="margin-top:0;">
    <h3>Pourquoi la rentabilité recule malgré la croissance des ventes</h3>
    <p style="margin:0;">La marge brute du Groupe a cédé {bps(G['gross_margin_cur']-G['gross_margin_prior'])} à
    {pct(G['gross_margin_cur'])} — le profit brut neuf a reculé de {pct(abs(G['pb_neuf_delta_pct']))} et le profit
    brut usagé de {pct(abs(G['pb_usage_delta_pct']))}, alors que le volume neuf a diminué de
    {pct(abs(G['unites_neuf_delta_pct']))} ({num(G['unites_neuf_prior'])} → {num(G['unites_neuf_cur'])} unités).
    Le volume usagé a toutefois progressé de {pct(G['unites_usage_delta_pct'], signed=True)}
    ({num(G['unites_usage_prior'])} → {num(G['unites_usage_cur'])} unités). Les dépenses totales ont reculé de
    {pct(abs(G['opex_delta_pct']))} en dollars absolus, mais représentent une part plus élevée d'un profit brut
    plus faible.</p>
  </div>
</div>
""")

# ============================================================ Operating KPIs
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

op_rows = "".join([
    '<tr class="section-row"><td colspan="4">Volume</td></tr>',
    vol_row('Unités neuves (détail)', G['unites_neuf_cur'], G['unites_neuf_prior']),
    vol_row('Unités usagées (détail)', G['unites_usage_cur'], G['unites_usage_prior']),
    f'<tr class="total-row"><td>Total unités détail</td><td>{num(G["total_retail_units_prior"])}</td><td>{num(G["total_retail_units_cur"])}</td><td class="{delta_class(G["total_retail_units_delta_pct"])}">{delta_pct_str(G["total_retail_units_delta_pct"])}</td></tr>',
    ratio_row('Ratio neuf : usagé', G['new_used_ratio_cur'], G['new_used_ratio_prior']),
    vol_row('Unités flottes', G['unites_flottes_cur'], G['unites_flottes_prior']),
    '<tr class="section-row"><td colspan="4">Profit brut par unité</td></tr>',
    money_unit_row('Profit brut par unité — neuf', G['gpa_neuf_cur'], G['gpa_neuf_prior']),
    money_unit_row('Profit brut par unité — usagé', G['gpa_usage_cur'], G['gpa_usage_prior']),
    '<tr class="section-row"><td colspan="4">Profit brut par département</td></tr>',
    fin_row('Véhicules neufs', G['pb_neuf_cur'], G['pb_neuf_prior']),
    fin_row('Véhicules usagés', G['pb_usage_cur'], G['pb_usage_prior']),
    fin_row('Service', G['pb_service_cur'], G['pb_service_prior']),
    fin_row('Carrosserie', G['pb_carrosserie_cur'], G['pb_carrosserie_prior']),
    fin_row('Pièces', G['pb_pieces_cur'], G['pb_pieces_prior']),
    fin_row('Total profit brut', G['pb_total_cur'], G['pb_total_prior'], total=True),
])

pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 2 (suite)</div>
  <h1 class="section-title">Indicateurs opérationnels clés</h1>
  <hr class="rule">
  <table>
    <tr><th>Indicateur opérationnel</th><th>YTD {Y_PRIOR}</th><th>YTD {Y_CUR}</th><th>Δ</th></tr>
    {op_rows}
  </table>
  <p class="small">Les profits bruts par département n'incluent pas de ligne « revenus » distincte pour Service,
  Carrosserie et Pièces&nbsp;: le tableau de bord KPI ne suit que le profit brut de ces départements, pas leur
  chiffre d'affaires — la marge en % des ventes de ces trois départements n'est donc pas présentée ici.</p>
</div>
""")

# ============================================================ SECTION 3 — Operational analysis
# NOTE: depenses_* fields are stored as negative (expense outflow); flip to
# positive magnitudes here so $ values and Δ% both read intuitively (more
# spend = positive %, shown in red via invert=True).
exp_total_prior = -(G["depenses_variables_prior"]+G["depenses_personnel_prior"]+G["depenses_semifixes_prior"])
exp_total_cur = -(G["depenses_variables_cur"]+G["depenses_personnel_cur"]+G["depenses_semifixes_cur"])
exp_rows = "".join([
    fin_row('Dépenses variables', -G['depenses_variables_cur'], -G['depenses_variables_prior'], invert=True),
    fin_row('Dépenses de personnel', -G['depenses_personnel_cur'], -G['depenses_personnel_prior'], invert=True),
    fin_row('Dépenses semi-fixes', -G['depenses_semifixes_cur'], -G['depenses_semifixes_prior'], invert=True),
    fin_row('Total — 3 catégories suivies', exp_total_cur, exp_total_prior, invert=True, total=True),
])

pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 3</div>
  <h1 class="section-title">Analyse opérationnelle</h1>
  <hr class="rule">
  <p><strong>La composition du profit brut s'est déplacée vers les usagés, le service et les pièces.</strong>
  Le profit brut neuf recule de {pct(abs(G['pb_neuf_delta_pct']))} et pèse désormais
  {pct(MIX['dept_mix_cur']['Neuf']/MIX['dept_total_cur'])} du profit brut total, contre
  {pct(MIX['dept_mix_prior']['Neuf']/MIX['dept_total_prior'])} il y a un an. Le service ({money_m(G['pb_service_cur'])})
  et les pièces ({money_m(G['pb_pieces_cur'])}) demeurent les lignes les plus stables du Groupe.</p>

  <p><strong>Les dépenses de personnel demeurent la plus grande catégorie de dépenses suivie</strong>, à
  {pct(-G['depenses_personnel_cur']/exp_total_cur)}
  des trois catégories suivies, en légère baisse par rapport à
  {pct(-G['depenses_personnel_prior']/exp_total_prior)}
  l'an dernier. Les dépenses variables ont progressé de {pct(G['depenses_variables_delta_pct'], signed=True)}.</p>

  <h2 class="sub">Dépenses par catégorie — Groupe</h2>
  <table>
    <tr><th>Dépenses par catégorie</th><th>YTD {Y_PRIOR}</th><th>YTD {Y_CUR}</th><th>Δ</th></tr>
    {exp_rows}
  </table>
  <p class="small">Ces trois catégories ne représentent pas la totalité des dépenses d'exploitation&nbsp;: une
  portion « frais fixes » (loyer, amortissement, taxes foncières, assurances) n'est pas isolée comme indicateur
  distinct dans le tableau de bord KPI actuel pour l'ensemble des concessions et apparaît donc comme un solde
  résiduel dans le graphique de répartition ci-dessous plutôt que comme une catégorie mesurée directement.</p>

  <h2 class="sub">Répartition du profit brut par département</h2>
  <div class="chart-block"><img src="data:image/png;base64,{DEPT_CHART_B64}"></div>
</div>
""")

pages.append(f"""
<div class="page">
  <div class="section-label">Section 3 (suite)</div>
  <h2 class="sub" style="margin-top:0;">Répartition des dépenses d'exploitation</h2>
  <div class="chart-block"><img src="data:image/png;base64,{EXP_CHART_B64}"></div>
  <p class="legend-note">Part des dépenses totales du Groupe. « Fixes / non ventilées » est un solde calculé
  (dépenses totales moins les trois catégories suivies) et non une mesure extraite directement des états
  financiers — voir la note à la page précédente.</p>

  <div class="callout" style="margin-top:26px;">
    <h3>Ce que montrent les deux graphiques</h3>
    <p style="margin:0;">Le profit brut s'est diversifié hors du neuf pendant que le mix de dépenses est resté
    relativement stable d'une année à l'autre. Cela signifie que le recul de la rentabilité du Groupe est porté
    presque entièrement par la compression du profit brut (surtout neuf et usagé), et non par une dérive des
    dépenses suivies.</p>
  </div>
</div>
""")

# ============================================================ SECTION 4 — Scorecard
score_rows = ""
for r in SC['scorecard']:
    tag_class = {'EN CROISSANCE': 'status-croissance', 'STABLE': 'status-stable',
                 'SOUS FOCUS': 'status-focus', 'PRIORITE H2': 'status-priorite'}.get(r['status'], 'status-stable')
    dcls = delta_class(r['ebt_delta_pct'])
    score_rows += (f'<tr><td>{esc(r["display_name"])}</td><td>{money(r["rev_prior"])}</td><td>{money(r["rev_cur"])}</td>'
                   f'<td>{money(r["ebt_prior"])}</td><td>{money(r["ebt_cur"])}</td>'
                   f'<td class="{dcls}">{money(r["ebt_delta_abs"])}</td>'
                   f'<td><span class="status-tag {tag_class}">{esc(r["status"])}</span></td></tr>')
score_rows += (f'<tr class="total-row"><td>Total — 5 concessions</td><td>{money(G["ventes_nettes_prior"])}</td>'
               f'<td>{money(G["ventes_nettes_cur"])}</td><td>{money(G["ebt_prior"])}</td><td>{money(G["ebt_cur"])}</td>'
               f'<td class="{delta_class(G["ebt_delta_pct"])}">{money(G["ebt_delta_abs"])}</td><td>{delta_pct_str(G["ebt_delta_pct"])}</td></tr>')

best = SC['scorecard'][0]
worst = SC['scorecard'][-1]

pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 4</div>
  <h1 class="section-title">Tableau de bord par concession</h1>
  <hr class="rule">
  <p>Les cinq concessions sont classées par variation en dollars de l'EBT déclaré, du plus fort gain à la plus
  forte baisse.</p>
  <table>
    <tr><th>Concession</th><th>Ventes YTD{YY_PRIOR}</th><th>Ventes YTD{YY_CUR}</th><th>EBT YTD{YY_PRIOR}</th><th>EBT YTD{YY_CUR}</th><th>Δ EBT $</th><th>Statut</th></tr>
    {score_rows}
  </table>
  <p class="small">EBT = profit net avant impôt déclaré. Statut basé sur la variation en % de l'EBT&nbsp;:
  Croissance ≥ +10&nbsp;%, Stable entre -5&nbsp;% et +10&nbsp;%, Sous focus entre -20&nbsp;% et -5&nbsp;%,
  Priorité H2 &lt; -20&nbsp;%. Ces seuils sont une convention de présentation de ce rapport, pas une politique
  officielle du Groupe.</p>

  <h2 class="sub">Là où l'EBT a bougé</h2>
  <p><strong>{esc(best['display_name'])} affiche le plus fort gain du Groupe</strong>, avec un EBT en hausse de
  {money(best['ebt_delta_abs'])} ({delta_pct_str(best['ebt_delta_pct'])}) à {money_m(best['ebt_cur'])}.</p>
  <p><strong>{esc(worst['display_name'])} accuse le recul le plus marqué</strong>, avec un EBT en baisse de
  {money(abs(worst['ebt_delta_abs']))} ({delta_pct_str(worst['ebt_delta_pct'])}) à {money_m(worst['ebt_cur'])}.</p>
</div>
""")

# ---- earnings concentration
top = SC['concentration'][0]
rest_cur = G['ebt_cur'] - top['ebt_cur']
rest_prior = G['ebt_prior'] - top['ebt_prior']
rest_share_cur = rest_cur / G['ebt_cur']
rest_share_prior = rest_prior / G['ebt_prior']
rest_delta_pct = (rest_cur - rest_prior) / abs(rest_prior) if rest_prior else None

pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 4 (suite)</div>
  <h1 class="section-title">Concentration des profits</h1>
  <hr class="rule">
  <table>
    <tr><th>Concentration des profits</th><th>YTD {Y_PRIOR}</th><th>YTD {Y_CUR}</th><th>Δ</th></tr>
    <tr class="section-row"><td colspan="4">{esc(top['display_name'])}</td></tr>
    {fin_row('EBT', top['ebt_cur'], top['ebt_prior'])}
    {fin_row('% de l’EBT du Groupe', top['share_cur'], top['share_prior'], is_pct=True)}
    <tr class="section-row"><td colspan="4">Solde du Groupe — 4 autres concessions</td></tr>
    {fin_row('EBT', rest_cur, rest_prior)}
    {fin_row('% de l’EBT du Groupe', rest_share_cur, rest_share_prior, is_pct=True)}
    <tr class="section-row"><td colspan="4">Total</td></tr>
    {fin_row('EBT — 5 concessions', G['ebt_cur'], G['ebt_prior'], total=True)}
  </table>

  <div class="callout">
    <h3>Pourquoi cela compte</h3>
    <p style="margin:0;">{esc(top['display_name'])} demeure la plus grande source de profit avant impôt du
    Groupe, mais sa part a reculé de {bps(top['share_cur']-top['share_prior'])} à {pct(top['share_cur'])}, pendant
    que les quatre autres concessions combinées ont vu leur EBT {'progresser' if (rest_delta_pct or 0) >= 0 else 'reculer'}
    de {pct(abs(rest_delta_pct)) if rest_delta_pct is not None else '—'} à {money_m(rest_cur)}.</p>
  </div>
</div>
""")

# ============================================================ SECTIONS 5-7 — N/D
def nd_page(section_no, title, note):
    return f"""
<div class="page">
  <div class="eyebrow">Section {section_no}</div>
  <h1 class="section-title">{esc(title)}</h1>
  <hr class="rule">
  <div class="nd-box">
    <div class="nd-title">Données non disponibles</div>
    {note}
  </div>
</div>
"""

pages.append(nd_page(5, "Acquisitions",
    "<p style=\"margin:0;\">Aucune acquisition n'a été complétée par le Groupe durant la période visée par ce "
    f"rapport (janvier–{MOIS_CUR} {Y_CUR}). Cette section est incluse pour respecter la structure standard du rapport "
    "et sera renseignée si une acquisition est complétée dans une période future.</p>"))

pages.append(nd_page(6, "Portefeuille immobilier",
    "<p style=\"margin:0;\">Le tableau de bord KPI du Groupe ne suit pas actuellement les données immobilières "
    "(valeur marchande des propriétés, loyer payé, loyer théorique normalisé). Cette section pourra être "
    "renseignée si ces données sont un jour extraites d'une source distincte.</p>"))

pages.append(nd_page(7, "Pipeline et opportunités stratégiques",
    "<p style=\"margin:0;\">Aucun pipeline d'acquisition ou de développement n'est suivi dans le tableau de bord "
    "KPI actuel. Cette information relève de la direction du Groupe et n'est pas dérivable des états financiers "
    "des concessions.</p>"))

# ============================================================ SECTION 8 — Outlook
pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 8</div>
  <h1 class="section-title">Perspectives</h1>
  <hr class="rule">
  <div class="callout">
    <h3>Ce que les données suggèrent pour le reste de l'année {Y_CUR}</h3>
    <ul>
      <li><strong>Absorption des dépenses.</strong> Les dépenses représentent {pct(G['expenses_pct_gp_cur'])} du
      profit brut du Groupe, contre {pct(G['expenses_pct_gp_prior'])} il y a un an — un ratio à surveiller si le
      profit brut neuf continue de reculer.</li>
      <li><strong>Profit brut neuf.</strong> Le profit brut neuf a reculé de {pct(abs(G['pb_neuf_delta_pct']))}
      malgré une baisse de volume plus faible ({pct(abs(G['unites_neuf_delta_pct']))}) — l'écart suggère une
      compression du profit brut par unité neuve (GPA neuf en baisse de
      {pct(abs(G['gpa_neuf_delta_pct']))} à {money(G['gpa_neuf_cur'])}/unité).</li>
      <li><strong>Les deux concessions sous priorité.</strong> {esc(SC['scorecard'][-1]['display_name'])} et
      {esc(SC['scorecard'][-2]['display_name'])} affichent les plus fortes baisses d'EBT du Groupe et méritent une
      attention particulière au second semestre.</li>
    </ul>
  </div>
  <div class="nd-box">
    <div class="nd-title">Priorités de gestion et objectifs H2 — Données non disponibles</div>
    <p style="margin:0;">Les priorités stratégiques officielles du second semestre (plans d'action nommés,
    objectifs de clôture d'acquisitions, financement, etc.) relèvent de la direction du Groupe et ne sont pas
    dérivables des données financières du tableau de bord KPI. Les observations ci-dessus sont des constats basés
    uniquement sur les chiffres YTD et ne remplacent pas la planification de la direction.</p>
  </div>
</div>
""")

# ============================================================ SECTION 9 — Store-by-store appendix
def appendix_table(period_key, title):
    metrics = [
        ('Ventes nettes', 'ventes_nettes', 'money'),
        ('Profit brut', 'pb_total', 'money'),
        ('Dépenses variables', 'depenses_variables', 'money_abs'),
        ('Dépenses de personnel', 'depenses_personnel', 'money_abs'),
        ('Dépenses semi-fixes', 'depenses_semifixes', 'money_abs'),
        ('Autres revenus', 'autres_revenus', 'money'),
        ('EBT déclaré', 'ebt', 'money'),
        ('Unités neuves', 'unites_neuf', 'num'),
        ('Unités usagées', 'unites_usage', 'num'),
    ]
    header = "<tr><th>($)</th>" + "".join(f"<th>{esc(DEALERS[k]['display_name'])}</th>" for k in ORDER) + "<th>Total</th></tr>"
    rows_html = ""
    for label, field, kind in metrics:
        cells = ""
        total = 0
        any_val = False
        for k in ORDER:
            v = DEALERS[k].get(f'{field}_{period_key}')
            if v is None:
                cells += "<td>—</td>"
                continue
            any_val = True
            disp = abs(v) if kind == 'money_abs' else v
            total += disp if kind != 'num' else v
            cells += f"<td>{num(v) if kind=='num' else money(disp)}</td>"
        total_disp = num(total) if kind == 'num' else money(total)
        rows_html += f"<tr><td>{esc(label)}</td>{cells}<td><strong>{total_disp if any_val else '—'}</strong></td></tr>"
    return f'<table><caption style="caption-side:top;text-align:left;font-weight:800;font-size:9.5pt;margin-bottom:4px;">{esc(title)}</caption>{header}{rows_html}</table>'

def appendix_change_table():
    metrics = [
        ('Ventes nettes', 'ventes_nettes'),
        ('Profit brut', 'pb_total'),
        ('Dépenses variables', 'depenses_variables'),
        ('Dépenses de personnel', 'depenses_personnel'),
        ('Dépenses semi-fixes', 'depenses_semifixes'),
        ('Autres revenus', 'autres_revenus'),
        ('EBT déclaré', 'ebt'),
        ('Unités neuves', 'unites_neuf'),
        ('Unités usagées', 'unites_usage'),
    ]
    header = f"<tr><th>Δ % vs YTD{YY_PRIOR}</th>" + "".join(f"<th>{esc(DEALERS[k]['display_name'])}</th>" for k in ORDER) + "<th>Total — 5</th></tr>"
    rows_html = ""
    for label, field in metrics:
        cells = ""
        for k in ORDER:
            dp = DEALERS[k].get(f'{field}_delta_pct')
            cells += f'<td class="{delta_class(dp)}">{delta_pct_str(dp)}</td>'
        gdp = G.get(f'{field}_delta_pct')
        rows_html += f'<tr><td>{esc(label)}</td>{cells}<td class="{delta_class(gdp)}"><strong>{delta_pct_str(gdp)}</strong></td></tr>'
    return f'<table><caption style="caption-side:top;text-align:left;font-weight:800;font-size:9.5pt;margin-bottom:4px;">Variation annuelle (%)</caption>{header}{rows_html}</table>'

pages.append(f"""
<div class="page">
  <div class="eyebrow">Section 9</div>
  <h1 class="section-title">Résultats détaillés par concession</h1>
  <hr class="rule">
  <p>Les tableaux ci-dessous donnent les mêmes mesures pour chacune des cinq concessions, d'abord pour YTD {Y_CUR},
  puis YTD {Y_PRIOR}, puis la variation annuelle. Ce sont les données sous-jacentes derrière les chiffres consolidés
  des sections 2 à 4. Les dépenses sont affichées en valeur absolue (montants dépensés).</p>
  {appendix_table('cur', f'YTD {Y_CUR} — Janvier à {MOIS_CUR} {Y_CUR}')}
</div>
""")

pages.append(f"""
<div class="page">
  <div class="section-label">Section 9 (suite)</div>
  {appendix_table('prior', f'YTD {Y_PRIOR} — Janvier à {MOIS_CUR} {Y_PRIOR}')}
  <div style="margin-top:26px;"></div>
  {appendix_change_table()}
  <p class="small" style="margin-top:16px;">EBT et dépenses détaillées proviennent directement des états financiers
  de chaque concession tels qu'extraits par le tableau de bord KPI. HAWKS (format GM Canada) — la comparaison
  YTD {Y_PRIOR} provient du fichier de {MOIS_CUR} {Y_PRIOR} de HAWKS plutôt que d'une colonne « année précédente » intégrée,
  ce format ne portant pas cette colonne nativement. Préparé pour usage interne. Non audité — confidentiel.</p>
</div>
""")

# ============================================================ ASSEMBLE
n = len(pages)
body = ""
for i, p in enumerate(pages, start=1):
    # insert footer before closing </div> of each .page, skip footer on cover (page 1)
    if i == 1:
        body += p
    else:
        body += p[:p.rfind('</div>')] + footer(i) + p[p.rfind('</div>'):]

html_doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Groupeautomax — Rapport de performance YTD {Y_CUR}</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>"""

open(os.path.join(WORKDIR, 'report.html'), 'w').write(html_doc)
print("HTML written,", len(pages), "pages,", len(html_doc), "chars")

