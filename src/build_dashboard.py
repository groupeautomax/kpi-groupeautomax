import json, sys, os, datetime
from pathlib import Path

FR_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]


def default_generated_at_label():
    """Today's date, formatted in French, without depending on the system
    locale being installed (e.g. a fresh GitHub Actions runner won't have
    fr_CA.UTF-8 available)."""
    today = datetime.date.today()
    return f"{today.day} {FR_MONTHS[today.month - 1]} {today.year}"

GROUP_LABELS = {
    "volume": "Volume (unités)",
    "profit": "Profit brut",
    "revenue_expense": "Revenus & dépenses",
    "net": "Profit net",
    "ebitda": "EBITDA / EBT",
    "other": "Autres indicateurs"
}
GROUP_ORDER = ["volume", "profit", "revenue_expense", "net", "ebitda", "other"]

# Fixed 5-dealer roster for Groupeautomax (must mirror extract.py's
# CANONICAL_DEALERS keys) -- this is the permanent column/row/color order in
# the dashboard, always rendered even before a dealer's first file arrives.
DEALER_ROSTER = [
    {"key": "bmw", "label": "BMW Sherbrooke"},
    {"key": "stm", "label": "STM (Ste-Marie Auto)"},
    {"key": "hawks", "label": "HAWKS"},
    {"key": "vw", "label": "Volkswagen"},
    {"key": "hyundai", "label": "Hyundai"},
]

PALETTE = {
    "light": {
        "surface1": "#fcfcfb", "page": "#f9f9f7", "textPrimary": "#0b0b0b",
        "textSecondary": "#52514e", "muted": "#898781", "grid": "#e1e0d9",
        "baseline": "#c3c2b7", "good": "#006300", "critical": "#d03b3b",
        "border": "rgba(11,11,11,0.10)"
    },
    "dark": {
        "surface1": "#1a1a19", "page": "#0d0d0d", "textPrimary": "#ffffff",
        "textSecondary": "#c3c2b7", "muted": "#898781", "grid": "#2c2c2a",
        "baseline": "#383835", "good": "#0ca30c", "critical": "#e66767",
        "border": "rgba(255,255,255,0.10)"
    }
}

SERIES_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SERIES_DARK  = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]


def build_roster(store):
    roster = list(DEALER_ROSTER)
    known_keys = {d["key"] for d in roster}
    # Any dealer key present in the data but outside the fixed 5 (shouldn't
    # normally happen) still gets shown rather than silently dropped.
    for key, dealer in store["dealers"].items():
        if key not in known_keys:
            roster.append({"key": key, "label": dealer.get("display_name", key)})
    return roster


def build_dealer_color_map(roster):
    return {d["key"]: i for i, d in enumerate(roster)}


def build_period_list(store):
    """Union of every period_key across all dealers, sorted chronologically,
    each with a human label -- this becomes the single reference period the
    whole dashboard locks to, so June and July are never compared as if they
    were the same month."""
    labels = {}
    for dealer in store["dealers"].values():
        for period_key, pdata in dealer["periods"].items():
            labels[period_key] = f"{pdata['month_name']} {pdata['year']}"
    return [{"key": k, "label": labels[k]} for k in sorted(labels.keys())]


def build_html(store, generated_at_label):
    roster = build_roster(store)
    dealer_colors = build_dealer_color_map(roster)
    periods = build_period_list(store)
    data_json = json.dumps(store, ensure_ascii=False)
    colors_json = json.dumps(dealer_colors, ensure_ascii=False)
    roster_json = json.dumps(roster, ensure_ascii=False)
    periods_json = json.dumps(periods, ensure_ascii=False)
    series_light_json = json.dumps(SERIES_LIGHT)
    series_dark_json = json.dumps(SERIES_DARK)
    group_labels_json = json.dumps(GROUP_LABELS, ensure_ascii=False)
    group_order_json = json.dumps(GROUP_ORDER)

    html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Comparateur KPI — Groupeautomax</title>
<style>
  :root {
    color-scheme: light;
    --surface-1: #fcfcfb; --page: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --muted: #898781; --grid: #e1e0d9;
    --baseline: #c3c2b7; --good: #006300; --critical: #d03b3b;
    --border: rgba(11,11,11,0.10);
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) {
      color-scheme: dark;
      --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff;
      --text-secondary: #c3c2b7; --muted: #898781; --grid: #2c2c2a;
      --baseline: #383835; --good: #0ca30c; --critical: #e66767;
      --border: rgba(255,255,255,0.10);
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff;
    --text-secondary: #c3c2b7; --muted: #898781; --grid: #2c2c2a;
    --baseline: #383835; --good: #0ca30c; --critical: #e66767;
    --border: rgba(255,255,255,0.10);
  }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--page); color: var(--text-primary); }
  .app { max-width: 1180px; margin: 0 auto; padding: 24px 20px 64px; }
  header.top { display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; margin-bottom: 20px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .subtitle { color: var(--text-secondary); font-size: 13px; }
  .theme-toggle { border:1px solid var(--border); background:var(--surface-1); color:var(--text-primary); border-radius:8px; padding:6px 12px; font-size:12px; cursor:pointer; }

  .legend-row { display:flex; flex-wrap:wrap; gap:14px; margin-bottom:18px; }
  .legend-item { display:flex; align-items:center; gap:6px; font-size:13px; color: var(--text-secondary); }
  .swatch { width:10px; height:10px; border-radius:2px; flex-shrink:0; }
  .legend-item.pending { opacity: 0.55; font-style: italic; }
  .swatch.pending { border: 1.5px dashed var(--muted); background: transparent; }

  .controls { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-bottom: 20px; padding: 12px; background: var(--surface-1); border:1px solid var(--border); border-radius: 12px; }
  .control-group { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
  .control-label { font-size:11px; text-transform:uppercase; letter-spacing:0.04em; color: var(--muted); margin-right:4px; }
  .pill { border:1px solid var(--border); background:transparent; color:var(--text-secondary); border-radius:999px; padding:5px 12px; font-size:12.5px; cursor:pointer; }
  .pill.active { background: var(--text-primary); color: var(--page); border-color: var(--text-primary); }
  .month-select { border:1px solid var(--border); background: var(--page); color: var(--text-primary); border-radius:8px; padding:6px 10px; font-size:12.5px; cursor:pointer; min-width:160px; }
  .month-select:focus { outline: 1px solid var(--text-secondary); }
  .dropdown-multi { position: relative; }
  .dropdown-multi summary { border:1px solid var(--border); background: var(--page); color: var(--text-primary); border-radius:8px; padding:6px 10px; font-size:12.5px; cursor:pointer; min-width:160px; list-style:none; }
  .dropdown-multi summary::-webkit-details-marker { display:none; }
  .dropdown-multi summary::after { content: ' \\25BE'; color: var(--muted); }
  .dropdown-multi[open] summary::after { content: ' \\25B4'; }
  .dropdown-multi .dropdown-panel { position:absolute; z-index:20; top: calc(100% + 6px); left:0; background: var(--surface-1); border:1px solid var(--border); border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:6px; min-width:220px; box-shadow: 0 6px 18px rgba(0,0,0,0.12); }
  .dealer-check { display:flex; align-items:center; gap:5px; font-size:12.5px; border:1px solid var(--border); border-radius:999px; padding:4px 10px 4px 8px; cursor:pointer; color: var(--text-secondary); }
  .dealer-check input { accent-color: currentColor; }
  .dealer-check.pending { opacity: 0.55; font-style: italic; border-style: dashed; }
  .spacer { flex: 1 1 auto; }
  .view-toggle { display:flex; gap:4px; }

  .group-tabs { display:flex; gap:6px; margin-bottom: 18px; flex-wrap:wrap; }

  .layout { display:flex; gap:20px; align-items:flex-start; }
  .sidebar { width:220px; flex-shrink:0; background:var(--surface-1); border:1px solid var(--border); border-radius:12px; padding:10px; position:sticky; top:16px; }
  .main-pane { flex:1 1 auto; min-width:0; }
  .nav-section { margin-bottom:6px; }
  .nav-parent { display:block; width:100%; text-align:left; background:none; border:none; border-radius:8px; padding:9px 10px; font-size:13px; font-weight:600; color:var(--text-primary); cursor:pointer; }
  .nav-parent:hover { background:var(--grid); }
  .nav-parent.active { background:var(--text-primary); color:var(--page); }
  .nav-sub { display:flex; flex-direction:column; margin:2px 0 8px; padding-left:8px; border-left:2px solid var(--border); }
  .nav-item { display:block; width:100%; text-align:left; background:none; border:none; padding:7px 10px; font-size:12.5px; color:var(--text-secondary); cursor:pointer; border-radius:6px; }
  .nav-item:hover { background:var(--grid); color:var(--text-primary); }
  .nav-item.active { background:var(--grid); color:var(--text-primary); font-weight:600; }
  @media (max-width: 780px) {
    .layout { flex-direction:column; }
    .sidebar { width:100%; position:static; }
  }
  .nav-section-upload { margin-top:10px; padding-top:10px; border-top:1px solid var(--border); }
  .nav-parent-upload { color: var(--text-secondary); }

  .upload-steps { margin-top:14px; font-size:12.5px; color: var(--text-secondary); line-height:1.8; }
  .upload-mailto-btn { display:inline-block; text-decoration:none; margin-top:14px; }
  .upload-note { margin-top:18px; font-size:11.5px; color: var(--muted); line-height:1.6; }
  .upload-note code { background: var(--grid); border-radius:4px; padding:1px 5px; font-size:11px; }

  .chart-card { background: var(--surface-1); border:1px solid var(--border); border-radius:12px; padding:16px 18px; margin-bottom:14px; }
  .chart-title { font-size:14px; font-weight:600; margin:0 0 2px; }
  .chart-meta { font-size:11.5px; color: var(--muted); margin-bottom:10px; }
  .bar-row { display:grid; grid-template-columns: 168px 1fr 140px 68px; align-items:center; gap:10px; padding:5px 0; }
  .bar-row .dealer-name { font-size:12.5px; color: var(--text-secondary); display:flex; align-items:center; flex-wrap:wrap; gap:2px 6px; overflow:hidden; }
  .bar-row .dealer-name > span:first-of-type + span { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .period-badge { flex-basis:100%; font-size:10px; color: var(--muted); font-style:italic; margin-left:16px; }
  .bar-track { position:relative; height:22px; background: var(--grid); border-radius: 3px; overflow:visible; }
  .bar-fill { position:absolute; top:1px; bottom:1px; border-radius:4px; }
  .bar-baseline { position:absolute; top:-3px; bottom:-3px; width:1px; background: var(--baseline); }
  .bar-value { font-size:12px; font-variant-numeric: tabular-nums; color: var(--text-secondary); text-align:right; }
  .delta-badge { font-size:10.5px; font-variant-numeric: tabular-nums; white-space:normal; line-height:1.35; }
  .delta-badge.good { color: var(--good); }
  .delta-badge.critical { color: var(--critical); }
  .delta-pct { font-weight:400; opacity:0.85; }
  .dept-pct-line { font-size:10px; color: var(--muted); text-align:right; font-variant-numeric: tabular-nums; margin-top:1px; }
  .no-data { color: var(--muted); font-size: 12.5px; font-style: italic; padding: 4px 0; }
  .sparkline-wrap { display:flex; justify-content:center; align-items:center; }
  .sparkline-wrap .no-data { font-size:10px; padding:0; text-align:center; }
  .chart-title-row { display:flex; align-items:baseline; justify-content:space-between; gap:10px; }
  .sparkline-col-label { font-size:9.5px; color: var(--muted); text-transform:uppercase; letter-spacing:0.03em; white-space:nowrap; }

  table.kpi-table { width:100%; border-collapse: collapse; font-size:12.5px; }
  table.kpi-table caption { text-align:left; font-weight:600; font-size:14px; margin-bottom:8px; }
  table.kpi-table th, table.kpi-table td { text-align:right; padding:6px 8px; border-bottom:1px solid var(--grid); font-variant-numeric: tabular-nums; }
  table.kpi-table th:first-child, table.kpi-table td:first-child { text-align:left; font-variant-numeric: normal; }
  table.kpi-table thead th { color: var(--muted); font-weight:500; font-size:11px; text-transform:uppercase; letter-spacing:0.03em; }
  table.kpi-table tbody tr:hover { background: var(--grid); }

  .detail-toggle-link { background:none; border:none; cursor:pointer; padding:0; margin:-6px 0 8px; font-size:11px; color: var(--text-secondary); text-decoration:underline; text-underline-offset:2px; }
  .detail-toggle-link:hover { color: var(--text-primary); }
  .detail-toggle { background:none; border:none; cursor:pointer; padding:0; color: var(--muted); font-size:10px; vertical-align:middle; }
  .detail-toggle:hover { color: var(--text-primary); }
  .line-item-detail { margin-top:12px; padding-top:12px; border-top:1px dashed var(--border); }
  table.detail-table { font-size:11px; }
  table.detail-table th, table.detail-table td { padding:4px 6px; }

  footer.notes { margin-top: 28px; font-size:12px; color: var(--muted); line-height:1.6; border-top:1px solid var(--border); padding-top:14px; }

  .lock-screen { position:fixed; inset:0; background: var(--page); display:flex; align-items:center; justify-content:center; z-index:1000; padding:20px; }
  .lock-card { width:100%; max-width:340px; background: var(--surface-1); border:1px solid var(--border); border-radius:14px; padding:28px 26px; text-align:center; }
  .lock-card h1 { font-size:17px; margin:0 0 4px; }
  .lock-card p { font-size:12.5px; color: var(--text-secondary); margin:0 0 18px; }
  .lock-input { width:100%; box-sizing:border-box; padding:10px 12px; border-radius:8px; border:1px solid var(--border); background: var(--page); color: var(--text-primary); font-size:14px; margin-bottom:10px; }
  .lock-btn { width:100%; padding:10px 12px; border-radius:8px; border:none; background: var(--text-primary); color: var(--page); font-size:13.5px; font-weight:600; cursor:pointer; }
  .lock-error { color: var(--critical); font-size:12px; margin-top:10px; min-height:16px; }
</style>
</head>
<body>
<div class="lock-screen" id="lockScreen">
  <div class="lock-card">
    <h1>Comparateur KPI — Groupeautomax</h1>
    <p>Ce tableau de bord contient des données financières confidentielles. Entrez le mot de passe pour continuer.</p>
    <input type="password" id="lockInput" class="lock-input" placeholder="Mot de passe" autocomplete="off">
    <button type="button" id="lockBtn" class="lock-btn">Déverrouiller</button>
    <div class="lock-error" id="lockError"></div>
  </div>
</div>
<div class="viz-root" id="vizRoot" style="display:none;">
<div class="app">
  <header class="top">
    <div>
      <h1>Comparateur KPI — Groupeautomax</h1>
      <div class="subtitle" id="subtitle">Mis à jour le __GENERATED_AT__</div>
    </div>
    <button class="theme-toggle" id="themeToggle" type="button">Mode sombre</button>
  </header>

  <div class="legend-row" id="legendRow"></div>

  <div class="controls">
    <div class="control-group">
      <span class="control-label">Concessionnaires</span>
      <details class="dropdown-multi" id="dealerDropdown">
        <summary id="dealerDropdownSummary">Concessionnaires</summary>
        <div class="dropdown-panel">
          <div id="dealerFilter"></div>
          <label class="dealer-check" id="combinedToggleWrap" style="border-style:dashed;">
            <input type="checkbox" id="combinedToggle" checked>
            <span>Total (combiné)</span>
          </label>
        </div>
      </details>
    </div>
    <div class="control-group">
      <span class="control-label">Mois de référence</span>
      <select id="refPeriodSelect" class="month-select"></select>
    </div>
    <div class="control-group">
      <span class="control-label">Période</span>
      <select id="periodSelect" class="month-select"></select>
    </div>
    <div class="control-group">
      <span class="control-label">Comparer vs</span>
      <select id="basisSelect" class="month-select"></select>
    </div>
    <div class="control-group">
      <span class="control-label">Vue</span>
      <select id="viewSelect" class="month-select"></select>
    </div>
  </div>

  <div class="layout">
    <nav class="sidebar" id="sidebarNav"></nav>
    <div class="main-pane">
      <div id="content"></div>
    </div>
  </div>

  <footer class="notes">
    Concessionnaires suivis : BMW Sherbrooke, Ste-Marie Auto (STM), HAWKS, Volkswagen, Hyundai.
    Pour ajouter un mois : déposez le fichier « Réalisé » du concessionnaire dans la conversation avec Claude —
    les données se compilent automatiquement dans ce tableau de bord, mois après mois, sans perdre l'historique déjà chargé.
  </footer>
</div>
</div>

<script id="kpi-data" type="application/json">__DATA_JSON__</script>
<script>
const STORE = JSON.parse(document.getElementById('kpi-data').textContent);
const DEALER_COLOR_INDEX = __COLORS_JSON__;
const SERIES_LIGHT = __SERIES_LIGHT_JSON__;
const SERIES_DARK = __SERIES_DARK_JSON__;
const GROUP_LABELS = __GROUP_LABELS_JSON__;
const GROUP_ORDER = __GROUP_ORDER_JSON__;
const DEALER_ROSTER = __ROSTER_JSON__; // [{key, label}, ...] fixed order, always 5 slots
const PERIOD_LIST = __PERIODS_JSON__; // [{key: "2026-07", label: "Juillet 2026"}, ...] chronological
// Synthetic pseudo-dealer representing the sum of every currently-checked
// dealer -- "concessions combinées" -- shown as an extra leading
// column/bar, never part of the roster/checkbox filter itself.
const COMBINED_KEY = '__combined__';
// Where a new monthly source file actually needs to land for the automated
// GitHub Actions pipeline to pick it up and rebuild this site -- see
// renderUploadView() and .github/workflows/update-dashboard.yml.
const GITHUB_SOURCES_URL = 'https://github.com/groupeautomax/kpi-groupeautomax/upload/main/sources';
function dealerLabel(key) {
  if (key === COMBINED_KEY) return 'Total (combiné)';
  const d = DEALER_ROSTER.find(x => x.key === key);
  return d ? d.label : key;
}
function periodLabel(periodKey) {
  const p = PERIOD_LIST.find(x => x.key === periodKey);
  return p ? p.label : periodKey;
}
// Every chart/table reads a single globally-selected reference period
// (state.refPeriod) for every dealer -- a dealer without that exact period
// shows n/d rather than silently substituting a different month. This badge
// just confirms, next to each dealer's name, that its figures really are
// from the selected period (helpful once a dealer has several months on file).
function periodBadge(dealerKey) {
  const period = resolvedPeriod(dealerKey);
  if (!period) return '';
  return periodLabel(period);
}
function orderedKeys(keys) {
  const set = new Set(keys);
  return DEALER_ROSTER.map(d => d.key).filter(k => set.has(k));
}

function isDark() {
  const stamp = document.documentElement.getAttribute('data-theme');
  if (stamp === 'dark') return true;
  if (stamp === 'light') return false;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}
function seriesColor(dealer) {
  if (dealer === COMBINED_KEY) return isDark() ? '#ffffff' : '#0b0b0b';
  const idx = DEALER_COLOR_INDEX[dealer] ?? 0;
  const arr = isDark() ? SERIES_DARK : SERIES_LIGHT;
  return arr[idx % arr.length];
}

const state = {
  dealers: new Set(DEALER_ROSTER.map(d => d.key)), // all 5 slots shown by default
  refPeriod: PERIOD_LIST.length ? PERIOD_LIST[PERIOD_LIST.length - 1].key : null, // which month, e.g. "2026-07" -- same for every dealer, never mixed
  period: 'month', // month | ytd | quarter_latest -- which slice of that one reference month
  basis: 'budget', // budget | prior_year
  scope: 'overview', // overview | departments
  group: 'volume',
  dept: null, // selected department name when scope === 'departments'
  view: 'chart', // chart | table
  showCombined: true // whether the synthetic "Total (combiné)" pseudo-dealer is shown
};

// Canonical department order + French labels for the "Détail par
// département" view. Extra/unexpected department names found in the data
// (a dealer-specific line like STM's "Wholesale autres") are appended after
// these, so nothing is silently dropped.
const DEPARTMENT_ORDER = ['Véhicules neufs', 'Véhicules usagés', 'Service', 'Carrosserie', 'Pièces'];
// Explicitly excluded from the department list (not a real department for
// these dealers) even if a block of that name turns up in a source file.
const HIDDEN_DEPARTMENTS = new Set(['Boutique']);
const DEPARTMENT_METRICS = [
  { key: 'units', label: 'Unités', group: 'volume' },
  { key: 'profit_brut', label: 'Profit brut (avant dépenses du département)', group: 'money' },
  { key: 'total_variables', label: 'Dépenses variables', group: 'money' },
  { key: 'total_personnel', label: 'Dépenses de personnel', group: 'money' },
  { key: 'total_semifixes', label: 'Dépenses semi-fixes', group: 'money' },
  { key: 'total_depenses', label: 'Total des dépenses du département', group: 'money' },
  { key: 'autres_revenus', label: 'Autres revenus du département', group: 'money' },
  { key: 'profit_departemental', label: 'Profit départemental (net)', group: 'money' },
];
// Which line_items section(s) (tagged by extract.py) back the detail behind
// each top-line department metric -- e.g. clicking "Unités" or "Profit brut"
// reveals the same underlying sales rows (Autos détail / Camions détail /
// Total Neufs / Ex-Démos et courtoisies / Flottes / ...), just read from a
// different column set.
const METRIC_LINE_ITEM_SECTIONS = {
  units: ['ventes'],
  profit_brut: ['ventes'],
  total_variables: ['variables'],
  total_personnel: ['personnel'],
  total_semifixes: ['semifixes'],
  total_depenses: ['variables', 'personnel', 'semifixes'],
  autres_revenus: ['autres'],
  profit_departemental: ['autres'],
};
// Which metric card/row is currently expanded to show its line-item detail,
// keyed "dept::metricKey" -- a plain object rather than per-department state
// so the expansion persists across re-renders triggered by other controls.
const expandedMetrics = {};

function fmtMoney(v) {
  if (v === null || v === undefined) return '—';
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 }).format(v);
}
function fmtNum(v) {
  if (v === null || v === undefined) return '—';
  return new Intl.NumberFormat('fr-CA', { maximumFractionDigits: 0 }).format(v);
}
function fmtPercent(v) {
  if (v === null || v === undefined) return '—';
  return (v * 100).toFixed(1) + '%';
}
function fmtValue(group, v) {
  if (group === 'volume') return fmtNum(v);
  if (group === 'percent') return fmtPercent(v);
  return fmtMoney(v);
}
// Ratio-type KPIs (EBT % of gross profit, ROS) already show their delta as a
// point-difference via fmtValue itself -- appending the usual relative-%
// variance on top (a % change of a %) would be a confusing double
// percentage, so it's skipped for that format.
function deltaAnnotation(kpi, group) {
  if (group === 'percent') return '';
  return fmtDeltaPct(deltaPct(kpi));
}
// A KPI's own `.format` field (currently only set on the two EBT ratio KPIs)
// overrides the tab-level group for value formatting -- format is a property
// of the KPI itself (dollars vs. a ratio), not of the tab it happens to be
// grouped under, so mixing $ and % KPIs in one "EBITDA / EBT" tab still
// renders each one correctly. Looked up from whichever real dealer carries
// the value (the combined pseudo-dealer's own copy already sets `.format`
// too, via ratioFromCombined, but a real dealer is checked first so this
// also works before any dealer data has loaded for the combined total).
function kpiFormat(key, fallbackGroup) {
  for (const dealer of orderedKeys(state.dealers)) {
    const period = resolvedPeriod(dealer);
    const sec = period ? sectionFor(dealer, period, state.period) : undefined;
    const kpi = sec ? sec.kpis[key] : undefined;
    if (kpi && kpi.format) return kpi.format;
  }
  return fallbackGroup;
}

function availablePeriodsForDealer(dealer) {
  return Object.keys(STORE.dealers[dealer]?.periods || {}).sort();
}

// Every dealer is read at the SAME globally-selected reference period
// (state.refPeriod) -- never each dealer's own latest, which is how June and
// July ended up compared side by side as if they were the same month. A
// dealer with no data for that exact period returns undefined (shows n/d),
// it never falls back to a different month.
function resolvedPeriod(dealer) {
  if (dealer === COMBINED_KEY) {
    // The combined total is meaningful only if at least one real, currently
    // checked dealer actually has data for the selected reference period.
    const hasAny = orderedKeys(state.dealers).some(k => STORE.dealers[k]?.periods?.[state.refPeriod]);
    return hasAny ? state.refPeriod : undefined;
  }
  const periods = STORE.dealers[dealer]?.periods || {};
  return periods[state.refPeriod] ? state.refPeriod : undefined;
}

function quarterKeyFor(dealer, period) {
  const sections = STORE.dealers[dealer]?.periods?.[period]?.sections || {};
  const qKeys = Object.keys(sections).filter(k => k.startsWith('quarter_')).sort();
  return qKeys[qKeys.length - 1];
}

function sectionFor(dealer, period, periodMode) {
  const sections = STORE.dealers[dealer]?.periods?.[period]?.sections || {};
  if (periodMode === 'month') return sections['month'];
  if (periodMode === 'ytd') return sections['ytd'];
  if (periodMode === 'quarter') {
    const qk = quarterKeyFor(dealer, period);
    return qk ? sections[qk] : undefined;
  }
  return undefined;
}

// Same calendar month one year earlier, e.g. "2026-07" -> "2025-07" -- used
// to compare a period against our own historical data when the source file
// itself carries no prior-year column.
function priorYearPeriodKey(periodKey) {
  const m = /^(\d{4})-(\d{2})$/.exec(periodKey || '');
  if (!m) return null;
  return `${parseInt(m[1], 10) - 1}-${m[2]}`;
}

// HAWKS' and STM's GM "Composite Financial Statement" .xlsm months carry no
// budget/prior-year columns at all, so extract.py always leaves kv.prior_year
// null for them -- previously that meant no year-over-year comparison could
// ever show for those months, even once a full calendar year of history was
// on file. Now that HAWKS in particular has 2025 loaded alongside 2026, the
// dashboard can compute that comparison itself: look up the same
// dealer/metric/month a year earlier in our own store and use its real value
// as the comparison base. `lookupSameMetric(section)` re-runs the same
// sec -> value path the caller used (sec.kpis[key], or
// sec.departments[dept][metricKey]) against the prior year's section, so this
// works for both top-line KPIs and department metrics without duplicating
// that lookup logic here. An explicit prior_year already provided by a
// source file (the xlsx dealers) is always left untouched.
function withSynthesizedPriorYear(dealer, period, periodMode, kv, lookupSameMetric) {
  if (!kv) return kv;
  if (kv.prior_year !== null && kv.prior_year !== undefined) return kv;
  if (kv.real === null || kv.real === undefined) return kv;
  const pyPeriod = priorYearPeriodKey(period);
  if (!pyPeriod || !STORE.dealers[dealer]?.periods?.[pyPeriod]) return kv;
  const pySec = sectionFor(dealer, pyPeriod, periodMode);
  const pyKv = pySec ? lookupSameMetric(pySec) : undefined;
  if (!pyKv || pyKv.real === null || pyKv.real === undefined) return kv;
  return Object.assign({}, kv, { prior_year: pyKv.real, delta_prior_year: kv.real - pyKv.real });
}

function collectKpiKeys(group) {
  const keys = new Map(); // key -> label
  orderedKeys(state.dealers).forEach(dealer => {
    const period = resolvedPeriod(dealer);
    if (!period) return;
    const sec = sectionFor(dealer, period, state.period);
    if (!sec) return;
    Object.entries(sec.kpis).forEach(([key, kpi]) => {
      if (kpi.group === group) keys.set(key, kpi.label);
    });
  });
  return keys;
}

function collectDepartmentNames() {
  const found = new Set();
  orderedKeys(state.dealers).forEach(dealer => {
    const period = resolvedPeriod(dealer);
    if (!period) return;
    const sec = sectionFor(dealer, period, state.period);
    if (!sec || !sec.departments) return;
    Object.keys(sec.departments).forEach(name => { if (!HIDDEN_DEPARTMENTS.has(name)) found.add(name); });
  });
  const ordered = DEPARTMENT_ORDER.filter(n => found.has(n));
  const extra = Array.from(found).filter(n => !DEPARTMENT_ORDER.includes(n)).sort();
  return ordered.concat(extra);
}

// --- "Concessions combinées" -- a synthetic pseudo-dealer summing every
// currently-checked real dealer, mirroring Quotus's "Totals" row/column. It
// is never part of the roster/checkbox filter (renderDealerFilter never
// lists it) -- it's an extra leading column/bar computed on the fly. -------

// Sums real/budget/prior_year across a list of kv-objects, skipping entries
// with no numeric value at that field (so one dealer missing a budget
// doesn't zero out the combined budget). Deltas are recomputed from the
// summed real/budget/prior_year rather than summing each dealer's own delta,
// so rounding stays consistent with the combined totals actually shown.
function sumKv(items) {
  const fields = ['real', 'budget', 'prior_year'];
  const sums = {}, any = {};
  fields.forEach(f => { sums[f] = 0; any[f] = false; });
  items.forEach(it => {
    if (!it) return;
    fields.forEach(f => {
      const v = it[f];
      if (typeof v === 'number' && isFinite(v)) { sums[f] += v; any[f] = true; }
    });
  });
  const out = {
    real: any.real ? sums.real : null,
    budget: any.budget ? sums.budget : null,
    prior_year: any.prior_year ? sums.prior_year : null,
  };
  out.delta_budget = (out.real !== null && out.budget !== null) ? out.real - out.budget : null;
  out.delta_prior_year = (out.real !== null && out.prior_year !== null) ? out.real - out.prior_year : null;
  return out;
}

// Combined figure for a top-level overview KPI, summed across every
// currently-checked dealer with data for the resolved reference period.
// Percent-format KPIs (EBT % of gross profit, ROS) are never summed or
// averaged here -- averaging ratios across dealers of very different sizes
// would overweight the smaller ones -- they're recomputed properly from
// combined numerator/denominator via ratioFromCombined() instead.
function combinedKpiFor(key) {
  if (key === 'ebt_pct_profit_brut') return ratioFromCombined('ebt', 'pb_total');
  if (key === 'ros') return ratioFromCombined('ebt', 'ventes_nettes');
  const items = [];
  orderedKeys(state.dealers).forEach(dealer => {
    const period = resolvedPeriod(dealer);
    const sec = period ? sectionFor(dealer, period, state.period) : undefined;
    let kpi = sec ? sec.kpis[key] : undefined;
    if (kpi) kpi = withSynthesizedPriorYear(dealer, period, state.period, kpi, (pySec) => pySec.kpis[key]);
    if (kpi) items.push(kpi);
  });
  if (!items.length) return null;
  return sumKv(items);
}

// Recomputes a ratio KPI (e.g. EBT % of Gross Profit = EBT / Profit brut)
// from the COMBINED numerator and denominator, not from averaging each
// dealer's own percentage -- this is the mathematically correct way to
// combine a "% of X" figure across dealers of different sizes.
function ratioFromCombined(numKey, denKey) {
  const num = combinedKpiFor(numKey);
  const den = combinedKpiFor(denKey);
  if (!num || !den) return null;
  const out = { real: null, budget: null, prior_year: null, delta_budget: null, delta_prior_year: null, format: 'percent' };
  ['real', 'budget', 'prior_year'].forEach(f => {
    out[f] = (typeof num[f] === 'number' && typeof den[f] === 'number' && den[f]) ? num[f] / den[f] : null;
  });
  out.delta_budget = (out.real !== null && out.budget !== null) ? out.real - out.budget : null;
  out.delta_prior_year = (out.real !== null && out.prior_year !== null) ? out.real - out.prior_year : null;
  return out;
}

// Department metric keys that carry a nested "% of profit brut" sub-field
// (read verbatim from the source sheet for a single dealer) -- for the
// combined total this sub-field must be recomputed from combined expense $
// over combined department profit_brut $, not averaged per-dealer.
const DEPT_PCT_KEYS_JS = new Set(['total_variables', 'total_personnel', 'total_semifixes', 'total_depenses']);

function combinedDeptMetricFor(deptName, metricKey) {
  const items = [];
  const pbItems = [];
  orderedKeys(state.dealers).forEach(dealer => {
    const period = resolvedPeriod(dealer);
    const sec = period ? sectionFor(dealer, period, state.period) : undefined;
    const dept = sec && sec.departments ? sec.departments[deptName] : undefined;
    if (!dept) return;
    let metric = dept[metricKey];
    if (metric) {
      metric = withSynthesizedPriorYear(dealer, period, state.period, metric,
        (pySec) => pySec.departments && pySec.departments[deptName] ? pySec.departments[deptName][metricKey] : undefined);
      items.push(metric);
    }
    let pb = dept.profit_brut;
    if (pb) {
      pb = withSynthesizedPriorYear(dealer, period, state.period, pb,
        (pySec) => pySec.departments && pySec.departments[deptName] ? pySec.departments[deptName].profit_brut : undefined);
      pbItems.push(pb);
    }
  });
  if (!items.length) return null;
  const combined = sumKv(items);
  if (DEPT_PCT_KEYS_JS.has(metricKey) && pbItems.length) {
    const combinedPb = sumKv(pbItems);
    const ratioAt = (num, den) => (typeof num === 'number' && typeof den === 'number' && den) ? num / den : null;
    const pctReal = ratioAt(combined.real, combinedPb.real);
    const pctBudget = ratioAt(combined.budget, combinedPb.budget);
    const pctPriorYear = ratioAt(combined.prior_year, combinedPb.prior_year);
    combined.pct = {
      real: pctReal,
      delta_budget: (pctReal !== null && pctBudget !== null) ? pctReal - pctBudget : null,
      delta_prior_year: (pctReal !== null && pctPriorYear !== null) ? pctReal - pctPriorYear : null,
    };
  }
  return combined;
}

// The dealer keys to actually display, in order -- the combined pseudo-dealer
// (when enabled) is prepended as a leading column/bar, ahead of the real
// dealers, but only when at least one real dealer is checked.
function displayDealerKeys() {
  const keys = orderedKeys(state.dealers);
  return (state.showCombined && keys.length > 0) ? [COMBINED_KEY].concat(keys) : keys;
}

function buildRowsForDept(deptName, metricKey) {
  const rows = [];
  displayDealerKeys().forEach(dealer => {
    if (dealer === COMBINED_KEY) {
      const combined = combinedDeptMetricFor(deptName, metricKey);
      rows.push(combined ? Object.assign({ dealer }, combined) : { dealer, real: null, budget: null, delta_budget: null, prior_year: null, delta_prior_year: null });
      return;
    }
    const period = resolvedPeriod(dealer);
    const sec = period ? sectionFor(dealer, period, state.period) : undefined;
    const dept = sec && sec.departments ? sec.departments[deptName] : undefined;
    const metric = dept ? dept[metricKey] : undefined;
    if (metric) {
      rows.push(Object.assign({ dealer }, metric));
    } else {
      rows.push({ dealer, real: null, budget: null, delta_budget: null, prior_year: null, delta_prior_year: null });
    }
  });
  return rows;
}

// --- Historical trend (sparkline) -------------------------------------
// Every period a dealer has ever sent in is already sitting in STORE, so a
// month-over-month (or AAD-over-AAD, depending on state.period) trend line
// needs no new extraction work -- just walking the periods a card's own
// `key` (company KPI) or deptName+key (department metric) already resolves
// against, chronologically. Capped to the trailing 12 points so the line
// stays readable as years of history accumulate, and never reaches past the
// currently selected reference period (no showing the reader a "trend" that
// dips into months they haven't selected yet).
const TREND_MAX_POINTS = 12;

function metricValueFromSection(sec, key, detailOpts) {
  if (!sec) return undefined;
  if (detailOpts) {
    const dept = sec.departments ? sec.departments[detailOpts.deptName] : undefined;
    return dept ? dept[key] : undefined;
  }
  return sec.kpis ? sec.kpis[key] : undefined;
}

function trailingPeriodKeys(periodKeys) {
  const keys = periodKeys.filter(p => !state.refPeriod || p <= state.refPeriod).sort();
  return keys.slice(-TREND_MAX_POINTS);
}

function historyFor(dealer, key, detailOpts) {
  const periods = trailingPeriodKeys(Object.keys(STORE.dealers[dealer]?.periods || {}));
  const points = [];
  periods.forEach(periodKey => {
    const sec = sectionFor(dealer, periodKey, state.period);
    const val = metricValueFromSection(sec, key, detailOpts);
    if (val && typeof val.real === 'number') points.push({ period: periodKey, value: val.real });
  });
  return points;
}

function historyForCombined(key, detailOpts) {
  const dealers = orderedKeys(state.dealers);
  const allPeriods = new Set();
  dealers.forEach(d => Object.keys(STORE.dealers[d]?.periods || {}).forEach(p => allPeriods.add(p)));
  const periods = trailingPeriodKeys(Array.from(allPeriods));
  const points = [];
  periods.forEach(periodKey => {
    const vals = [];
    dealers.forEach(d => {
      const sec = sectionFor(d, periodKey, state.period);
      const val = metricValueFromSection(sec, key, detailOpts);
      if (val && typeof val.real === 'number') vals.push(val.real);
    });
    if (vals.length) points.push({ period: periodKey, value: vals.reduce((a, b) => a + b, 0) });
  });
  return points;
}

// 12-point sparkline in the muted/de-emphasis ink, current period picked out
// as a filled dot in the dealer's own accent color -- trend shape carries
// the "up or down lately" read, the dot ties it back to the bar it sits
// beside. A native SVG <title> stands in for a full crosshair here (a
// sparkline is a compact glance, not its own interactive chart).
function renderSparkline(points, color, group) {
  const wrap = document.createElement('div');
  wrap.className = 'sparkline-wrap';
  if (!points || points.length < 2) {
    const nd = document.createElement('span');
    nd.className = 'no-data';
    nd.textContent = 'n/d';
    wrap.appendChild(nd);
    return wrap;
  }
  const w = 56, h = 22, pad = 3;
  const vals = points.map(p => p.value);
  const min = Math.min(...vals), max = Math.max(...vals);
  const range = (max - min) || Math.abs(max) || 1;
  const stepX = points.length > 1 ? (w - pad * 2) / (points.length - 1) : 0;
  const xy = points.map((p, i) => {
    const x = pad + i * stepX;
    const y = h - pad - ((p.value - min) / range) * (h - pad * 2);
    return [x, y];
  });
  const path = xy.map(([x, y], i) => (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1)).join(' ');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', String(w));
  svg.setAttribute('height', String(h));
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('role', 'img');
  const titleEl = document.createElementNS('http://www.w3.org/2000/svg', 'title');
  titleEl.textContent = points.map(p => `${p.period}: ${fmtValue(group, p.value)}`).join(' · ');
  svg.appendChild(titleEl);
  const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  line.setAttribute('d', path);
  line.setAttribute('fill', 'none');
  line.setAttribute('stroke', 'var(--muted)');
  line.setAttribute('stroke-width', '1.5');
  line.setAttribute('stroke-linecap', 'round');
  line.setAttribute('stroke-linejoin', 'round');
  svg.appendChild(line);
  const [lastX, lastY] = xy[xy.length - 1];
  const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  dot.setAttribute('cx', String(lastX));
  dot.setAttribute('cy', String(lastY));
  dot.setAttribute('r', '2.3');
  dot.setAttribute('fill', color);
  svg.appendChild(dot);
  wrap.appendChild(svg);
  return wrap;
}

function renderLegend() {
  const el = document.getElementById('legendRow');
  el.innerHTML = '';
  DEALER_ROSTER.forEach(({ key, label }) => {
    const has = !!STORE.dealers[key];
    const item = document.createElement('div');
    item.className = 'legend-item' + (has ? '' : ' pending');
    const sw = document.createElement('span');
    sw.className = 'swatch' + (has ? '' : ' pending');
    if (has) sw.style.background = seriesColor(key);
    item.appendChild(sw);
    const span = document.createElement('span');
    span.textContent = has ? label : label + ' (à venir)';
    item.appendChild(span);
    el.appendChild(item);
  });
}

// Dealer selection stays multi-select (several dealers can be shown at once),
// so a plain <select> doesn't fit -- instead the checkboxes live inside a
// <details>/<summary> dropdown panel, which is the closest compact
// "menu déroulant" equivalent for a multi-choice control. The summary label
// itself is kept in sync so the collapsed button always shows what's picked.
function updateDealerDropdownSummary() {
  const summary = document.getElementById('dealerDropdownSummary');
  if (!summary) return;
  const total = DEALER_ROSTER.length;
  const n = state.dealers.size;
  summary.textContent = n === total ? 'Tous les concessionnaires' : `Concessionnaires (${n}/${total})`;
}

function renderDealerFilter() {
  const el = document.getElementById('dealerFilter');
  el.innerHTML = '';
  DEALER_ROSTER.forEach(({ key, label }) => {
    const has = !!STORE.dealers[key];
    const wrap = document.createElement('label');
    wrap.className = 'dealer-check' + (has ? '' : ' pending');
    wrap.style.borderColor = seriesColor(key);
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = state.dealers.has(key);
    cb.addEventListener('change', () => {
      if (cb.checked) state.dealers.add(key); else state.dealers.delete(key);
      updateDealerDropdownSummary();
      renderContent();
    });
    wrap.appendChild(cb);
    const span = document.createElement('span');
    span.textContent = has ? label : label + ' (à venir)';
    wrap.appendChild(span);
    el.appendChild(wrap);
  });
  updateDealerDropdownSummary();
}

// Close the dealer dropdown when clicking anywhere outside it -- <details>
// only toggles on its own <summary> natively, which would otherwise leave it
// stuck open while browsing the rest of the page.
document.addEventListener('click', (e) => {
  const dd = document.getElementById('dealerDropdown');
  if (dd && dd.open && !dd.contains(e.target)) dd.removeAttribute('open');
});

function makeSelect(container, options, activeKey, onSelect) {
  container.innerHTML = '';
  options.forEach(opt => {
    const o = document.createElement('option');
    o.value = opt.key;
    o.textContent = opt.label;
    if (opt.key === activeKey) o.selected = true;
    container.appendChild(o);
  });
  container.onchange = () => { onSelect(container.value); };
}

function renderRefPeriodSelect() {
  const el = document.getElementById('refPeriodSelect');
  el.innerHTML = '';
  // Chronological list can now span 15-20+ months across all dealers combined
  // (e.g. HAWKS' full historical year) -- a dropdown keeps this compact
  // instead of wrapping a huge row of pill buttons. Most recent month first
  // so the common case (current month) doesn't require scrolling the list.
  PERIOD_LIST.slice().reverse().forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.key;
    opt.textContent = p.label;
    if (p.key === state.refPeriod) opt.selected = true;
    el.appendChild(opt);
  });
  el.onchange = () => { state.refPeriod = el.value; renderAll(); };
}

function renderTopControls() {
  renderRefPeriodSelect();

  makeSelect(document.getElementById('periodSelect'), [
    { key: 'month', label: 'Mois courant' },
    { key: 'ytd', label: 'Cumulatif annuel' },
    { key: 'quarter', label: 'Trimestre' }
  ], state.period, (k) => { state.period = k; renderAll(); });

  makeSelect(document.getElementById('basisSelect'), [
    { key: 'budget', label: 'Budget' },
    { key: 'prior_year', label: 'Année précédente' }
  ], state.basis, (k) => { state.basis = k; renderTopControls(); renderContent(); });

  makeSelect(document.getElementById('viewSelect'), [
    { key: 'chart', label: 'Graphiques' },
    { key: 'table', label: 'Tableau' }
  ], state.view, (k) => { state.view = k; renderTopControls(); renderContent(); });

  renderSidebar();
}

// Left-hand navigation (Quotus-style): "Aperçu global" with its KPI-group
// sub-items, and "Détail par département" with one sub-item per department
// -- replaces the old horizontal scope/group pill rows.
function renderSidebar() {
  const nav = document.getElementById('sidebarNav');
  nav.innerHTML = '';

  const overviewSection = document.createElement('div');
  overviewSection.className = 'nav-section';
  const overviewBtn = document.createElement('button');
  overviewBtn.type = 'button';
  overviewBtn.className = 'nav-parent' + (state.scope === 'overview' ? ' active' : '');
  overviewBtn.textContent = 'Aperçu global';
  overviewBtn.addEventListener('click', () => { state.scope = 'overview'; renderTopControls(); renderContent(); });
  overviewSection.appendChild(overviewBtn);
  if (state.scope === 'overview') {
    const sub = document.createElement('div');
    sub.className = 'nav-sub';
    GROUP_ORDER.filter(g => g !== 'other' || hasOtherKpis()).forEach(g => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'nav-item' + (state.group === g ? ' active' : '');
      b.textContent = GROUP_LABELS[g];
      b.addEventListener('click', () => { state.group = g; renderTopControls(); renderContent(); });
      sub.appendChild(b);
    });
    overviewSection.appendChild(sub);
  }
  nav.appendChild(overviewSection);

  const deptSection = document.createElement('div');
  deptSection.className = 'nav-section';
  const deptBtn = document.createElement('button');
  deptBtn.type = 'button';
  deptBtn.className = 'nav-parent' + (state.scope === 'departments' ? ' active' : '');
  deptBtn.textContent = 'Détail par département';
  deptBtn.addEventListener('click', () => {
    state.scope = 'departments';
    const deptNames = collectDepartmentNames();
    if (!state.dept || !deptNames.includes(state.dept)) state.dept = deptNames[0] || null;
    renderTopControls(); renderContent();
  });
  deptSection.appendChild(deptBtn);
  if (state.scope === 'departments') {
    const deptNames = collectDepartmentNames();
    if (!state.dept || !deptNames.includes(state.dept)) state.dept = deptNames[0] || null;
    const sub = document.createElement('div');
    sub.className = 'nav-sub';
    deptNames.forEach(n => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'nav-item' + (state.dept === n ? ' active' : '');
      b.textContent = n;
      b.addEventListener('click', () => { state.dept = n; renderTopControls(); renderContent(); });
      sub.appendChild(b);
    });
    deptSection.appendChild(sub);
  }
  nav.appendChild(deptSection);

  const uploadSection = document.createElement('div');
  uploadSection.className = 'nav-section nav-section-upload';
  const uploadBtn = document.createElement('button');
  uploadBtn.type = 'button';
  uploadBtn.className = 'nav-parent nav-parent-upload' + (state.scope === 'upload' ? ' active' : '');
  uploadBtn.textContent = '+ Déposer un fichier';
  uploadBtn.addEventListener('click', () => { state.scope = 'upload'; renderTopControls(); renderContent(); });
  uploadSection.appendChild(uploadBtn);
  nav.appendChild(uploadSection);
}

function hasOtherKpis() {
  let found = false;
  Object.keys(STORE.dealers).forEach(dealer => {
    const period = resolvedPeriod(dealer);
    if (!period) return;
    ['month','ytd'].forEach(pm => {
      const sec = sectionFor(dealer, period, pm);
      if (sec) Object.values(sec.kpis).forEach(k => { if (k.group === 'other') found = true; });
    });
  });
  return found;
}

function deltaFieldForBasis() {
  return state.basis === 'budget' ? 'delta_budget' : 'delta_prior_year';
}
function compareValueFieldForBasis() {
  return state.basis === 'budget' ? 'budget' : 'prior_year';
}
function compareLabel() {
  return state.basis === 'budget' ? 'budget' : 'année préc.';
}
// A budget of exactly 0 in this dataset generally means "not entered" (blank
// treated as zero by the source spreadsheet's formulas) rather than a real
// target of zero — so we hide the comparison rather than show a misleading 100%+ delta.
function hasCompareData(kpi) {
  if (!kpi) return false;
  const base = kpi[compareValueFieldForBasis()];
  if (base === null || base === undefined) return false;
  if (state.basis === 'budget' && base === 0) return false;
  return true;
}

// Variance in % vs the comparison basis (budget or prior year), same sign as
// the $ delta so the arrow direction and the percentage always agree. Uses
// |base| as the denominator so a negative comparison base (e.g. a budgeted
// loss) doesn't flip the sign of the percentage relative to the $ delta.
function deltaPct(kpi) {
  if (!hasCompareData(kpi)) return null;
  const base = kpi[compareValueFieldForBasis()];
  const delta = kpi[deltaFieldForBasis()];
  if (base === null || base === undefined || base === 0) return null;
  if (delta === null || delta === undefined) return null;
  const pct = (delta / Math.abs(base)) * 100;
  return isFinite(pct) ? pct : null;
}
function fmtDeltaPct(pct) {
  if (pct === null || pct === undefined) return '';
  return ' (' + (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%)';
}
// "% of department gross profit" figure that rides alongside the four
// expense-total department metrics (total_variables/personnel/semifixes/depenses),
// read directly from the source sheet's own % column -- not derived here.
function deptPctLineText(kpi) {
  if (!kpi || !kpi.pct || kpi.pct.real === null || kpi.pct.real === undefined) return null;
  let text = (kpi.pct.real * 100).toFixed(0) + '% du profit brut';
  const basisKey = state.basis === 'budget' ? 'delta_budget' : 'delta_prior_year';
  const ptDelta = kpi.pct[basisKey];
  if (ptDelta !== null && ptDelta !== undefined) {
    const pts = ptDelta * 100;
    text += ' (' + (pts >= 0 ? '+' : '') + pts.toFixed(1) + ' pt)';
  }
  return text;
}

// --- Line-item drill-down: the individual source-sheet rows (Autos détail,
// Camions détail, Total Neufs, Ex-Démos et courtoisies, Flottes, Comm.
// vendeurs, Salaires cadres, ...) behind a rolled-up department metric,
// revealed on demand rather than shown everywhere at once. ---------------

function collectLineItemLabels(deptName, sections) {
  const seen = [];
  const seenSet = new Set();
  orderedKeys(state.dealers).forEach(dealer => {
    const period = resolvedPeriod(dealer);
    const sec = period ? sectionFor(dealer, period, state.period) : undefined;
    const dept = sec && sec.departments ? sec.departments[deptName] : undefined;
    const items = dept ? dept.line_items : undefined;
    if (!items) return;
    items.filter(it => sections.includes(it.section)).forEach(it => {
      if (!seenSet.has(it.label)) { seenSet.add(it.label); seen.push(it.label); }
    });
  });
  return seen;
}

function lineItemFor(dealer, deptName, label, sections) {
  const period = resolvedPeriod(dealer);
  const sec = period ? sectionFor(dealer, period, state.period) : undefined;
  const dept = sec && sec.departments ? sec.departments[deptName] : undefined;
  const items = dept ? dept.line_items : undefined;
  if (!items) return null;
  return items.find(it => it.label === label && sections.includes(it.section)) || null;
}

// Money is the more universally meaningful figure for a line item; a unit
// count on its own only exists for the sales rows.
function lineItemPrimary(item) {
  if (item.money) return item.money;
  if (item.units) return item.units;
  return item.pct;
}
function lineItemGroup(item) {
  return item.money ? 'other' : 'volume';
}
// Only annotate a unit count alongside the $ value for genuine vehicle-sales
// rows ("ventes" section) -- elsewhere a populated units column is actually
// a rate (e.g. a commission %), not a count, and would mislead as "X un.".
function lineItemUnitsNote(item) {
  if (item.section === 'ventes' && item.money && item.units && item.units.real !== null && item.units.real !== undefined) {
    return fmtNum(item.units.real) + ' un.';
  }
  return null;
}

function buildLineItemRow(deptName, label, sections, dealerKeys) {
  const tr = document.createElement('tr');
  let isTotal = false;
  let cells = '';
  dealerKeys.forEach(dealer => {
    const item = lineItemFor(dealer, deptName, label, sections);
    if (item && item.is_total) isTotal = true;
    if (!item) {
      cells += '<td>—</td><td>—</td>';
      return;
    }
    const primary = lineItemPrimary(item);
    const group = lineItemGroup(item);
    const real = primary ? primary.real : null;
    const delta = primary && hasCompareData(primary) ? primary[deltaFieldForBasis()] : null;
    const note = lineItemUnitsNote(item);
    const valueText = fmtValue(group, real) + (note ? ` <span style="font-weight:400;color:var(--muted);font-size:10px;">(${note})</span>` : '');
    const deltaText = (delta === null || delta === undefined) ? '—' : fmtValue(group, delta) + deltaAnnotation(primary, group);
    cells += `<td>${valueText}</td>`;
    cells += `<td style="color:${delta === null || delta === undefined ? 'inherit' : (delta >= 0 ? 'var(--good)' : 'var(--critical)')}">${deltaText}</td>`;
  });
  tr.innerHTML = `<td style="${isTotal ? 'font-weight:600;' : 'padding-left:18px;color:var(--text-secondary);'}">${label}</td>` + cells;
  if (isTotal) tr.style.borderTop = '1px solid var(--border)';
  return tr;
}

function renderLineItemDetailTable(deptName, sections) {
  const labels = collectLineItemLabels(deptName, sections);
  const wrap = document.createElement('div');
  wrap.className = 'line-item-detail';
  if (!labels.length) {
    const nd = document.createElement('div');
    nd.className = 'no-data';
    nd.textContent = 'Aucun détail disponible pour la sélection actuelle.';
    wrap.appendChild(nd);
    return wrap;
  }
  const table = document.createElement('table');
  table.className = 'kpi-table detail-table';
  const dealerKeys = orderedKeys(state.dealers);
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  headRow.innerHTML = '<th>Poste (détail source)</th>' + dealerKeys.map(k =>
    `<th>${dealerLabel(k)}<br><span style="font-weight:400;text-transform:none;">Réel</span></th>` +
    `<th><span style="font-weight:400;text-transform:none;">vs ${compareLabel()}</span></th>`
  ).join('');
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = document.createElement('tbody');
  labels.forEach(label => tbody.appendChild(buildLineItemRow(deptName, label, sections, dealerKeys)));
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

function renderChartCard(key, label, rows, detailOpts) {
  const card = document.createElement('div');
  card.className = 'chart-card';
  const titleRow = document.createElement('div');
  titleRow.className = 'chart-title-row';
  const title = document.createElement('p');
  title.className = 'chart-title';
  title.textContent = label;
  titleRow.appendChild(title);
  const trendLabel = document.createElement('span');
  trendLabel.className = 'sparkline-col-label';
  trendLabel.textContent = 'Tendance (12 derniers)';
  titleRow.appendChild(trendLabel);
  card.appendChild(titleRow);
  const meta = document.createElement('div');
  meta.className = 'chart-meta';
  meta.textContent = 'Comparaison par concessionnaire · vs ' + compareLabel();
  card.appendChild(meta);

  let metaKey = null;
  if (detailOpts) {
    metaKey = detailOpts.deptName + '::' + key;
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'detail-toggle-link';
    toggle.textContent = (expandedMetrics[metaKey] ? '▾ ' : '▸ ') + 'Voir le détail des postes';
    toggle.addEventListener('click', () => {
      expandedMetrics[metaKey] = !expandedMetrics[metaKey];
      renderContent();
    });
    card.appendChild(toggle);
  }

  const vals = rows.map(r => r.real).filter(v => v !== null && v !== undefined);
  const compVals = rows.map(r => r[compareValueFieldForBasis()]).filter(v => v !== null && v !== undefined);
  const allVals = vals.concat(compVals, [0]);
  const maxAbs = Math.max(...allVals.map(Math.abs), 1);

  if (rows.length === 0) {
    const nd = document.createElement('div');
    nd.className = 'no-data';
    nd.textContent = 'Aucune donnée pour la sélection actuelle.';
    card.appendChild(nd);
    if (detailOpts && metaKey && expandedMetrics[metaKey]) {
      card.appendChild(renderLineItemDetailTable(detailOpts.deptName, detailOpts.sections));
    }
    return card;
  }

  rows.forEach(r => {
    const row = document.createElement('div');
    row.className = 'bar-row';

    const nameEl = document.createElement('div');
    nameEl.className = 'dealer-name';
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = seriesColor(r.dealer);
    nameEl.appendChild(sw);
    const nameText = document.createElement('span');
    nameText.textContent = dealerLabel(r.dealer);
    nameEl.appendChild(nameText);
    const badge = periodBadge(r.dealer);
    if (badge) {
      const badgeEl = document.createElement('span');
      badgeEl.className = 'period-badge';
      badgeEl.textContent = badge;
      nameEl.appendChild(badgeEl);
    }
    row.appendChild(nameEl);

    const track = document.createElement('div');
    track.className = 'bar-track';
    if (r.real === null || r.real === undefined) {
      const nd = document.createElement('span');
      nd.className = 'no-data';
      nd.textContent = 'n/d';
      track.appendChild(nd);
    } else {
      const zeroPct = 50 - (0 / maxAbs) * 50; // baseline centered handling below
      const range = maxAbs;
      const centerPct = 50;
      const valuePct = (r.real / range) * 50;
      const fill = document.createElement('div');
      fill.className = 'bar-fill';
      fill.style.background = seriesColor(r.dealer);
      if (r.real >= 0) {
        fill.style.left = centerPct + '%';
        fill.style.width = Math.abs(valuePct) + '%';
      } else {
        fill.style.left = (centerPct + valuePct) + '%';
        fill.style.width = Math.abs(valuePct) + '%';
      }
      track.appendChild(fill);
      const baseline = document.createElement('div');
      baseline.className = 'bar-baseline';
      baseline.style.left = centerPct + '%';
      track.appendChild(baseline);
    }
    row.appendChild(track);

    const valueWrap = document.createElement('div');
    const valEl = document.createElement('div');
    valEl.className = 'bar-value';
    valEl.textContent = fmtValue(rows.__group, r.real);
    valueWrap.appendChild(valEl);
    const delta = r[deltaFieldForBasis()];
    if (hasCompareData(r)) {
      const badge = document.createElement('div');
      badge.className = 'delta-badge ' + (delta >= 0 ? 'good' : 'critical');
      badge.style.textAlign = 'right';
      const pctSpan = deltaAnnotation(r, rows.__group);
      badge.innerHTML = (delta >= 0 ? '▲ ' : '▼ ') + fmtValue(rows.__group, Math.abs(delta)) +
        (pctSpan ? `<span class="delta-pct">${pctSpan}</span>` : '');
      valueWrap.appendChild(badge);
    } else if (r.real !== null && r.real !== undefined) {
      // Real figure exists but this dealer's source file has no budget /
      // prior-year columns at all (e.g. HAWKS' and STM's GM "Composite
      // Financial Statement" .xlsm months) -- make that explicit instead of
      // silently omitting the comparison line, which read as a bug.
      const ndBadge = document.createElement('div');
      ndBadge.className = 'delta-badge';
      ndBadge.style.textAlign = 'right';
      ndBadge.style.color = 'var(--muted)';
      ndBadge.textContent = `n/d vs ${compareLabel()}`;
      valueWrap.appendChild(ndBadge);
    }
    const deptPct = deptPctLineText(r);
    if (deptPct) {
      const pctLine = document.createElement('div');
      pctLine.className = 'dept-pct-line';
      pctLine.textContent = deptPct;
      valueWrap.appendChild(pctLine);
    }
    row.appendChild(valueWrap);

    const sparkPoints = r.dealer === COMBINED_KEY
      ? historyForCombined(key, detailOpts)
      : historyFor(r.dealer, key, detailOpts);
    row.appendChild(renderSparkline(sparkPoints, seriesColor(r.dealer), rows.__group));

    card.appendChild(row);
  });

  if (detailOpts && metaKey && expandedMetrics[metaKey]) {
    card.appendChild(renderLineItemDetailTable(detailOpts.deptName, detailOpts.sections));
  }

  return card;
}

function buildRowsForKpi(key) {
  const rows = [];
  displayDealerKeys().forEach(dealer => {
    if (dealer === COMBINED_KEY) {
      const combined = combinedKpiFor(key);
      rows.push(combined ? Object.assign({ dealer }, combined) : { dealer, real: null, budget: null, delta_budget: null, prior_year: null, delta_prior_year: null });
      return;
    }
    const period = resolvedPeriod(dealer);
    const sec = period ? sectionFor(dealer, period, state.period) : undefined;
    let kpi = sec ? sec.kpis[key] : undefined;
    if (kpi) kpi = withSynthesizedPriorYear(dealer, period, state.period, kpi, (pySec) => pySec.kpis[key]);
    if (kpi) {
      rows.push(Object.assign({ dealer }, kpi));
    } else {
      rows.push({ dealer, real: null, budget: null, delta_budget: null, prior_year: null, delta_prior_year: null });
    }
  });
  return rows;
}

// Header suffix for a dealer column -- "(à venir)" only makes sense for a
// real dealer slot with no file loaded yet; the combined pseudo-dealer is
// never "à venir" (it either has a computed value or shows n/d like any
// other missing figure).
function dealerHeaderSuffix(k) {
  if (k === COMBINED_KEY) return '';
  return STORE.dealers[k] ? '' : ' <span style="font-style:italic;font-weight:400;">(à venir)</span>';
}

function renderChartsView(container) {
  const keys = collectKpiKeys(state.group);
  if (keys.size === 0) {
    const nd = document.createElement('div');
    nd.className = 'no-data';
    nd.textContent = 'Aucun indicateur disponible pour cette catégorie / période.';
    container.appendChild(nd);
    return;
  }
  keys.forEach((label, key) => {
    const rows = buildRowsForKpi(key);
    rows.__group = kpiFormat(key, state.group);
    container.appendChild(renderChartCard(key, label, rows));
  });
}

function renderTableView(container) {
  const keys = collectKpiKeys(state.group);
  const table = document.createElement('table');
  table.className = 'kpi-table';
  const caption = document.createElement('caption');
  caption.textContent = GROUP_LABELS[state.group];
  table.appendChild(caption);
  const dealerKeys = displayDealerKeys();
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  headRow.innerHTML = '<th>Indicateur</th>' + dealerKeys.map(k =>
    `<th>${dealerLabel(k)}${dealerHeaderSuffix(k)}${periodBadge(k) ? ` <span style="font-style:italic;font-weight:400;color:var(--muted);">(${periodBadge(k)})</span>` : ''}<br><span style="font-weight:400;text-transform:none;">Réel</span></th>` +
    `<th><span style="font-weight:400;text-transform:none;">vs ${compareLabel()}</span></th>`
  ).join('');
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = document.createElement('tbody');
  keys.forEach((label, key) => {
    const fmtGroup = kpiFormat(key, state.group);
    const tr = document.createElement('tr');
    let cells = `<td>${label}</td>`;
    dealerKeys.forEach(dealer => {
      let kpi;
      if (dealer === COMBINED_KEY) {
        kpi = combinedKpiFor(key);
      } else {
        const period = resolvedPeriod(dealer);
        const sec = period ? sectionFor(dealer, period, state.period) : undefined;
        kpi = sec ? sec.kpis[key] : undefined;
        if (kpi) kpi = withSynthesizedPriorYear(dealer, period, state.period, kpi, (pySec) => pySec.kpis[key]);
      }
      const real = kpi ? kpi.real : null;
      const delta = hasCompareData(kpi) ? kpi[deltaFieldForBasis()] : null;
      const deltaText = (delta === null || delta === undefined)
        ? '—'
        : fmtValue(fmtGroup, delta) + deltaAnnotation(kpi, fmtGroup);
      cells += `<td>${fmtValue(fmtGroup, real)}</td>`;
      cells += `<td style="color:${delta === null || delta === undefined ? 'inherit' : (delta >= 0 ? 'var(--good)' : 'var(--critical)')}">${deltaText}</td>`;
    });
    tr.innerHTML = cells;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);
}

function renderDepartmentChartsView(container) {
  if (!state.dept) {
    const nd = document.createElement('div');
    nd.className = 'no-data';
    nd.textContent = 'Aucun département disponible pour cette période (essayez Mois courant ou Cumulatif annuel).';
    container.appendChild(nd);
    return;
  }
  DEPARTMENT_METRICS.forEach(({ key, label, group }) => {
    const rows = buildRowsForDept(state.dept, key);
    if (rows.every(r => r.real === null || r.real === undefined)) return; // metric not present for this dept
    rows.__group = group;
    const sections = METRIC_LINE_ITEM_SECTIONS[key];
    const detailOpts = sections ? { deptName: state.dept, sections } : null;
    container.appendChild(renderChartCard(key, label, rows, detailOpts));
  });
}

function renderDepartmentTableView(container) {
  if (!state.dept) {
    const nd = document.createElement('div');
    nd.className = 'no-data';
    nd.textContent = 'Aucun département disponible pour cette période.';
    container.appendChild(nd);
    return;
  }
  const table = document.createElement('table');
  table.className = 'kpi-table';
  const caption = document.createElement('caption');
  caption.textContent = state.dept;
  table.appendChild(caption);
  const dealerKeys = displayDealerKeys();
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  headRow.innerHTML = '<th>Indicateur</th>' + dealerKeys.map(k =>
    `<th>${dealerLabel(k)}${dealerHeaderSuffix(k)}${periodBadge(k) ? ` <span style="font-style:italic;font-weight:400;color:var(--muted);">(${periodBadge(k)})</span>` : ''}<br><span style="font-weight:400;text-transform:none;">Réel</span></th>` +
    `<th><span style="font-weight:400;text-transform:none;">vs ${compareLabel()}</span></th>`
  ).join('');
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = document.createElement('tbody');
  DEPARTMENT_METRICS.forEach(({ key, label, group }) => {
    const rows = buildRowsForDept(state.dept, key);
    if (rows.every(r => r.real === null || r.real === undefined)) return;
    const sections = METRIC_LINE_ITEM_SECTIONS[key];
    const metaKey = state.dept + '::' + key;
    const expanded = !!(sections && expandedMetrics[metaKey]);
    const tr = document.createElement('tr');
    const toggleHtml = sections
      ? `<button type="button" class="detail-toggle" data-metric="${metaKey}">${expanded ? '▾' : '▸'}</button> `
      : '';
    let cells = `<td>${toggleHtml}${label}</td>`;
    dealerKeys.forEach(dealer => {
      const metric = rows.find(r => r.dealer === dealer);
      const real = metric ? metric.real : null;
      const delta = hasCompareData(metric) ? metric[deltaFieldForBasis()] : null;
      const deltaText = (delta === null || delta === undefined)
        ? '—'
        : fmtValue(group, delta) + deltaAnnotation(metric, group);
      const deptPct = deptPctLineText(metric);
      const realText = fmtValue(group, real) + (deptPct ? `<br><span style="font-weight:400;color:var(--muted);font-size:10px;">${deptPct}</span>` : '');
      cells += `<td>${realText}</td>`;
      cells += `<td style="color:${delta === null || delta === undefined ? 'inherit' : (delta >= 0 ? 'var(--good)' : 'var(--critical)')}">${deltaText}</td>`;
    });
    tr.innerHTML = cells;
    tbody.appendChild(tr);
    if (expanded) {
      const detailTr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 1 + dealerKeys.length * 2;
      td.style.padding = '4px 8px 14px 24px';
      td.style.background = 'var(--grid)';
      td.appendChild(renderLineItemDetailTable(state.dept, sections));
      detailTr.appendChild(td);
      tbody.appendChild(detailTr);
    }
  });
  table.appendChild(tbody);
  container.appendChild(table);
  tbody.querySelectorAll('.detail-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const k = btn.getAttribute('data-metric');
      expandedMetrics[k] = !expandedMetrics[k];
      renderContent();
    });
  });
}

// "Déposer un fichier" -- points to the real self-service update pipeline:
// dropping a new monthly Excel file into the sources/ folder of the GitHub
// repo triggers a GitHub Actions workflow that re-extracts the data and
// republishes this site automatically, no email or manual step by Claude
// needed. This page can't do that upload itself (a static site has no
// backend, and pushing to GitHub needs the uploader's own GitHub login) --
// it just gives the direct link and the steps.
function renderUploadView(container) {
  const wrap = document.createElement('div');
  wrap.className = 'chart-card upload-card';
  wrap.innerHTML = `
    <p class="chart-title">Mettre à jour les données mensuelles</p>
    <div class="chart-meta">Ce site se reconstruit automatiquement dès qu'un nouveau fichier « Réalisé » est déposé dans le dépôt GitHub — sans courriel ni intervention manuelle.</div>
    <div class="upload-steps upload-steps-standalone">
      <div>1. Cliquez sur le bouton ci-dessous (ouvre GitHub dans un nouvel onglet — connexion GitHub avec accès au dépôt requise).</div>
      <div>2. Glissez le fichier « Réalisé » (.xlsx) du concessionnaire dans la zone de dépôt de GitHub.</div>
      <div>3. Cliquez « Commit changes » pour valider.</div>
      <div>4. Le site se met à jour automatiquement en une à deux minutes — actualisez cette page pour voir les nouvelles données.</div>
    </div>
    <a class="pill active upload-mailto-btn" href="${GITHUB_SOURCES_URL}" target="_blank" rel="noopener">Ouvrir la page de dépôt sur GitHub</a>
    <div class="upload-note">
      Le fichier est ajouté au dossier <code>sources/</code> du dépôt ; un robot (GitHub Actions) relit alors tous les
      fichiers sources, recalcule les indicateurs et republie automatiquement <code>index.html</code>. Aucune vérification
      humaine des chiffres n'a lieu avant la republication — si un fichier a un format inattendu, la mise à jour
      automatique peut échouer (visible dans l'onglet « Actions » du dépôt).
    </div>
  `;
  container.appendChild(wrap);
}

function renderContent() {
  const container = document.getElementById('content');
  container.innerHTML = '';
  if (state.scope === 'upload') {
    renderUploadView(container);
    return;
  }
  if (state.scope === 'departments') {
    if (state.view === 'chart') renderDepartmentChartsView(container);
    else renderDepartmentTableView(container);
    return;
  }
  if (state.view === 'chart') renderChartsView(container);
  else renderTableView(container);
}

function renderAll() {
  renderTopControls();
  renderContent();
}

function initCombinedToggle() {
  const cb = document.getElementById('combinedToggle');
  if (!cb) return;
  cb.checked = state.showCombined;
  cb.addEventListener('change', () => { state.showCombined = cb.checked; renderContent(); });
}

function initTheme() {
  const btn = document.getElementById('themeToggle');
  const apply = () => {
    const t = document.documentElement.getAttribute('data-theme');
    btn.textContent = (t === 'dark') ? 'Mode clair' : 'Mode sombre';
  };
  btn.addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme');
    document.documentElement.setAttribute('data-theme', cur === 'dark' ? 'light' : 'dark');
    apply();
    renderAll();
  });
  apply();
}

function initDashboard() {
  renderLegend();
  renderDealerFilter();
  initCombinedToggle();
  renderAll();
  initTheme();
}

// --- Access gate --------------------------------------------------------
// This dashboard holds confidential dealer financials and is published on a
// public static site (GitHub Pages has no built-in access control on a free
// plan). This is a basic deterrent, not real security: the page and its data
// are still fully present in the file served to the browser, so anyone
// determined enough to read the page source could bypass it. Only the SHA-256
// hash of the password is stored here, never the password itself, and the
// unlocked state is kept in memory only (no cookies/storage), so it resets
// every time the page is loaded fresh.
const PASSWORD_HASH = 'dd7cf2ab4ce93e418e0a85271a6ae7233d9b97ae02d002dbc5d318a31b7cf410';

async function sha256Hex(text) {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('');
}

function initLockScreen() {
  const lockScreen = document.getElementById('lockScreen');
  const vizRoot = document.getElementById('vizRoot');
  const input = document.getElementById('lockInput');
  const btn = document.getElementById('lockBtn');
  const errorEl = document.getElementById('lockError');

  async function tryUnlock() {
    const value = input.value;
    if (!value) return;
    const hash = await sha256Hex(value);
    if (hash === PASSWORD_HASH) {
      lockScreen.style.display = 'none';
      vizRoot.style.display = '';
      initDashboard();
    } else {
      errorEl.textContent = 'Mot de passe incorrect.';
      input.value = '';
      input.focus();
    }
  }

  btn.addEventListener('click', tryUnlock);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') tryUnlock(); });
  input.focus();
}

initLockScreen();
</script>
</body>
</html>
"""
    html = html.replace("__GENERATED_AT__", generated_at_label)
    html = html.replace("__DATA_JSON__", data_json)
    html = html.replace("__COLORS_JSON__", colors_json)
    html = html.replace("__SERIES_LIGHT_JSON__", series_light_json)
    html = html.replace("__SERIES_DARK_JSON__", series_dark_json)
    html = html.replace("__GROUP_LABELS_JSON__", group_labels_json)
    html = html.replace("__GROUP_ORDER_JSON__", group_order_json)
    html = html.replace("__ROSTER_JSON__", roster_json)
    html = html.replace("__PERIODS_JSON__", periods_json)
    return html


if __name__ == "__main__":
    # Relative to this script's own location, same reasoning as extract.py --
    # works unchanged locally and from a GitHub Actions checkout.
    repo_root = Path(__file__).resolve().parent.parent
    store_path = str(repo_root / "data" / "data.json")
    out_path = sys.argv[1] if len(sys.argv) > 1 else str(repo_root / "dashboard.html")
    generated_at = sys.argv[2] if len(sys.argv) > 2 else default_generated_at_label()
    with open(store_path, "r", encoding="utf-8") as f:
        store = json.load(f)
    html = build_html(store, generated_at)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote", out_path)
