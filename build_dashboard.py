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
  html { -webkit-text-size-adjust: 100%; }
  body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--page); color: var(--text-primary); }
  button, select, input { font-family: inherit; }
  .app { max-width: 1240px; margin: 0 auto; padding: 24px 20px 64px; }

  /* --- En-tête --------------------------------------------------------- */
  header.top { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom: 16px; }
  h1 { font-size: 21px; margin: 0 0 2px; letter-spacing:-0.01em; }
  .subtitle { color: var(--muted); font-size: 12.5px; }
  .theme-toggle { border:1px solid var(--border); background:var(--surface-1); color:var(--text-secondary); border-radius:8px; padding:6px 12px; font-size:12px; cursor:pointer; }
  .theme-toggle:hover { color: var(--text-primary); }

  /* --- Filtres (une seule rangée, au-dessus de tout ce qu'ils filtrent) --- */
  .controls { display:flex; flex-wrap:wrap; gap:12px 14px; align-items:flex-end; margin-bottom: 18px; padding: 12px 14px; background: var(--surface-1); border:1px solid var(--border); border-radius: 12px; }
  .control { display:flex; flex-direction:column; gap:4px; min-width:0; }
  .control-label { font-size:10.5px; text-transform:uppercase; letter-spacing:0.05em; color: var(--muted); }
  .month-select, .dropdown-multi summary { border:1px solid var(--border); background: var(--page); color: var(--text-primary); border-radius:8px; padding:7px 10px; font-size:13px; cursor:pointer; min-width:150px; width:100%; }
  .month-select:focus, .dropdown-multi summary:focus-visible { outline: 2px solid var(--text-secondary); outline-offset:1px; }
  .dropdown-multi { position: relative; }
  .dropdown-multi summary { list-style:none; white-space:nowrap; }
  .dropdown-multi summary::-webkit-details-marker { display:none; }
  .dropdown-multi summary::after { content: ' \\25BE'; color: var(--muted); }
  .dropdown-multi[open] summary::after { content: ' \\25B4'; }
  .dropdown-multi .dropdown-panel { position:absolute; z-index:30; top: calc(100% + 6px); left:0; background: var(--surface-1); border:1px solid var(--border); border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:6px; min-width:230px; box-shadow: 0 8px 24px rgba(0,0,0,0.14); }
  #dealerFilter { display:flex; flex-direction:column; gap:6px; }
  .dealer-check { display:flex; align-items:center; gap:7px; font-size:13px; border:1px solid var(--border); border-radius:8px; padding:6px 10px; cursor:pointer; color: var(--text-secondary); }
  .dealer-check input { accent-color: var(--text-primary); margin:0; }
  .dealer-check.pending { opacity: 0.55; font-style: italic; border-style: dashed; }
  .dealer-check.combined { border-style: dashed; margin-top:4px; }

  /* --- Navigation --------------------------------------------------------- */
  .layout { display:flex; gap:20px; align-items:flex-start; }
  .sidebar { width:210px; flex-shrink:0; background:var(--surface-1); border:1px solid var(--border); border-radius:12px; padding:8px; position:sticky; top:16px; }
  .main-pane { flex:1 1 auto; min-width:0; }
  .nav-section { margin-bottom:4px; }
  .nav-parent { display:block; width:100%; text-align:left; background:none; border:none; border-radius:8px; padding:9px 10px; font-size:13px; font-weight:600; color:var(--text-primary); cursor:pointer; }
  .nav-parent:hover { background:var(--grid); }
  .nav-parent.active { background:var(--text-primary); color:var(--page); }
  .nav-sub { display:flex; flex-direction:column; margin:2px 0 8px; padding-left:8px; border-left:2px solid var(--border); margin-left:10px; }
  .nav-item { display:block; width:100%; text-align:left; background:none; border:none; padding:7px 10px; font-size:12.5px; color:var(--text-secondary); cursor:pointer; border-radius:6px; }
  .nav-item:hover { background:var(--grid); color:var(--text-primary); }
  .nav-item.active { background:var(--grid); color:var(--text-primary); font-weight:600; }
  .nav-section-upload { margin-top:8px; padding-top:8px; border-top:1px solid var(--border); }
  .nav-parent-upload { color: var(--text-secondary); font-weight:500; }
  .mobile-nav { display:none; }
  .filters-toggle { display:none; }

  /* --- Titre de page + contexte ----------------------------------------- */
  .page-head { margin: 2px 0 14px; }
  .page-title { font-size:18px; font-weight:650; margin:0; letter-spacing:-0.01em; }
  .page-context { font-size:12.5px; color: var(--text-secondary); margin-top:3px; }
  .page-context .sep { color: var(--baseline); margin: 0 6px; }

  /* --- Cartes ----------------------------------------------------------- */
  .chart-card { background: var(--surface-1); border:1px solid var(--border); border-radius:12px; padding:16px 18px; margin-bottom:14px; }
  .card-head { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; flex-wrap:wrap; margin-bottom:10px; }
  .chart-title { font-size:14px; font-weight:600; margin:0 0 2px; }
  .chart-meta { font-size:11.5px; color: var(--muted); }
  .chart-meta .tick-key { display:inline-block; width:2px; height:10px; background: var(--text-primary); vertical-align:-1px; margin: 0 3px 0 1px; border-radius:1px; }
  .group-line { text-align:right; }
  .group-line .g-label { font-size:10.5px; text-transform:uppercase; letter-spacing:0.05em; color: var(--muted); }
  .group-line .g-value { font-size:17px; font-weight:650; line-height:1.2; }
  .group-line .delta-badge { font-size:11.5px; }
  .card-foot { margin-top:10px; padding-top:8px; border-top:1px solid var(--grid); font-size:11px; color: var(--muted); line-height:1.5; }

  /* --- Barres (une rangée par concession, triée) ------------------------ */
  .bar-head, .bar-row { display:grid; grid-template-columns: minmax(120px, 170px) minmax(80px, 1fr) 150px 64px; align-items:center; gap:12px; }
  .bar-head { font-size:10px; color: var(--muted); text-transform:uppercase; letter-spacing:0.04em; padding-bottom:4px; }
  .bar-head span:nth-child(3), .bar-head span:nth-child(4) { text-align:right; }
  .bar-head span:nth-child(4) { text-align:center; }
  .bar-row { padding:6px 4px; margin: 0 -4px; border-radius:6px; outline:none; }
  .bar-row:hover, .bar-row:focus-visible { background: var(--grid); }
  .dealer-name { font-size:12.5px; color: var(--text-primary); display:flex; align-items:center; gap:7px; min-width:0; }
  .dealer-name .nm { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .swatch { width:10px; height:10px; border-radius:2px; flex-shrink:0; }
  .bar-track { position:relative; height:18px; }
  .bar-track .zero { position:absolute; top:-2px; bottom:-2px; width:1px; background: var(--baseline); }
  .bar-fill { position:absolute; top:2px; bottom:2px; border-radius:0 4px 4px 0; min-width:2px; }
  .bar-fill.neg { border-radius:4px 0 0 4px; }
  .target-tick { position:absolute; top:-3px; bottom:-3px; width:2px; margin-left:-1px; background: var(--text-primary); border-radius:1px; box-shadow: 0 0 0 1.5px var(--surface-1); }
  .bar-value { font-size:12.5px; font-variant-numeric: tabular-nums; color: var(--text-primary); text-align:right; font-weight:500; }
  .delta-badge { font-size:11px; font-variant-numeric: tabular-nums; line-height:1.35; text-align:right; }
  .delta-badge.good { color: var(--good); }
  .delta-badge.critical { color: var(--critical); }
  .delta-badge.neutral { color: var(--muted); }
  .delta-pct { opacity:0.85; }
  .dept-pct-line { font-size:10px; color: var(--muted); text-align:right; font-variant-numeric: tabular-nums; margin-top:1px; }
  .no-data { color: var(--muted); font-size: 12.5px; font-style: italic; padding: 4px 0; }
  .sparkline-wrap { display:flex; justify-content:center; align-items:center; }
  .sparkline-wrap svg { overflow:visible; cursor:crosshair; }
  .sparkline-wrap .no-data { font-size:10px; padding:0; text-align:center; }

  /* --- Sommaire direction ------------------------------------------------ */
  .summary-top { display:grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); gap:14px; margin-bottom:14px; }
  .summary-top .chart-card { margin-bottom:0; }
  .hero-label { font-size:12px; color: var(--text-secondary); font-weight:600; }
  .hero-value { font-size:44px; font-weight:650; letter-spacing:-0.02em; line-height:1.1; margin:6px 0 4px; }
  .hero-delta { font-size:13px; }
  .hero-delta .cov { color: var(--muted); font-size:11.5px; display:block; margin-top:2px; }
  .hero-trend { margin-top:14px; }
  .hero-trend svg { display:block; width:100%; height:80px; overflow:visible; cursor:crosshair; }
  .hero-trend .axis-labels { display:flex; justify-content:space-between; font-size:10.5px; color: var(--muted); margin-top:4px; }
  .highlights { list-style:none; padding:0; margin:8px 0 0; display:flex; flex-direction:column; gap:10px; }
  .highlights li { font-size:13px; line-height:1.45; color: var(--text-primary); display:flex; gap:9px; align-items:flex-start; }
  .highlights .hl-icon { flex-shrink:0; width:18px; height:18px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:700; margin-top:1px; }
  .highlights .hl-icon.good { background: color-mix(in srgb, var(--good) 14%, transparent); color: var(--good); }
  .highlights .hl-icon.critical { background: color-mix(in srgb, var(--critical) 14%, transparent); color: var(--critical); }
  .highlights .hl-icon.info { background: var(--grid); color: var(--text-secondary); }
  .highlights .muted { color: var(--muted); }
  .stat-tiles { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; margin-bottom:14px; }
  .stat-tile { background: var(--surface-1); border:1px solid var(--border); border-radius:12px; padding:13px 14px 12px; text-align:left; color: inherit; cursor:pointer; display:flex; flex-direction:column; gap:3px; font: inherit; }
  .stat-tile:hover { border-color: var(--baseline); }
  .stat-tile:focus-visible { outline: 2px solid var(--text-secondary); outline-offset:1px; }
  .stat-tile .t-label { font-size:12px; color: var(--text-secondary); }
  .stat-tile .t-row { display:flex; align-items:flex-end; justify-content:space-between; gap:8px; }
  .stat-tile .t-value { font-size:22px; font-weight:650; letter-spacing:-0.01em; line-height:1.2; }
  .stat-tile .delta-badge { text-align:left; font-size:11.5px; }
  .stat-tile .cov { color: var(--muted); font-size:11px; }

  /* --- Tableaux --------------------------------------------------------- */
  .table-scroll { overflow-x:auto; -webkit-overflow-scrolling: touch; margin: 0 -18px; padding: 0 18px; }
  table.kpi-table { width:100%; border-collapse: separate; border-spacing:0; font-size:12.5px; }
  table.kpi-table th, table.kpi-table td { text-align:right; padding:8px 10px; border-bottom:1px solid var(--grid); font-variant-numeric: tabular-nums; white-space:nowrap; }
  table.kpi-table th:first-child, table.kpi-table td:first-child { text-align:left; font-variant-numeric: normal; position:sticky; left:0; background: var(--surface-1); z-index:1; white-space:normal; min-width:150px; }
  table.kpi-table thead th { color: var(--muted); font-weight:500; font-size:10.5px; text-transform:uppercase; letter-spacing:0.04em; vertical-align:bottom; }
  table.kpi-table thead th .th-dealer { display:inline-flex; align-items:center; gap:5px; color: var(--text-secondary); font-weight:600; }
  table.kpi-table tbody tr:hover td { background: var(--grid); }
  table.kpi-table td.delta { font-size:11.5px; }
  table.kpi-table td.delta.good { color: var(--good); }
  table.kpi-table td.delta.critical { color: var(--critical); }
  table.kpi-table td.delta.neutral { color: var(--muted); }
  table.kpi-table tr.group-row td { font-weight:650; border-top:1px solid var(--baseline); }
  table.kpi-table tr.group-row td:first-child { font-weight:650; }
  table.kpi-table .col-group { border-left:1px solid var(--grid); }
  .cell-main { display:block; }
  .cell-sub { display:block; font-size:10.5px; margin-top:1px; }
  .cell-sub.good { color: var(--good); } .cell-sub.critical { color: var(--critical); } .cell-sub.neutral { color: var(--muted); }
  .scorecard td:first-child .dealer-name { font-weight:500; }

  .detail-toggle-link { background:none; border:none; cursor:pointer; padding:0; margin:0 0 8px; font-size:11.5px; color: var(--text-secondary); text-decoration:underline; text-underline-offset:2px; }
  .detail-toggle-link:hover { color: var(--text-primary); }
  .detail-toggle { background:none; border:none; cursor:pointer; padding:0; color: var(--muted); font-size:10px; vertical-align:middle; }
  .detail-toggle:hover { color: var(--text-primary); }
  .line-item-detail { margin-top:12px; padding-top:12px; border-top:1px dashed var(--border); }
  table.detail-table { font-size:11px; }
  table.detail-table th, table.detail-table td { padding:4px 6px; }

  .upload-steps { margin-top:14px; font-size:12.5px; color: var(--text-secondary); line-height:1.8; }
  .upload-mailto-btn { display:inline-block; text-decoration:none; margin-top:14px; }
  .upload-note { margin-top:18px; font-size:11.5px; color: var(--muted); line-height:1.6; }
  .upload-note code { background: var(--grid); border-radius:4px; padding:1px 5px; font-size:11px; }
  .pill { border:1px solid var(--border); background:transparent; color:var(--text-secondary); border-radius:999px; padding:6px 13px; font-size:12.5px; cursor:pointer; white-space:nowrap; }
  .pill.active { background: var(--text-primary); color: var(--page); border-color: var(--text-primary); }

  footer.notes { margin-top: 28px; font-size:12px; color: var(--muted); line-height:1.6; border-top:1px solid var(--border); padding-top:14px; }

  /* --- Infobulle ------------------------------------------------------- */
  .tip { position:fixed; z-index:200; pointer-events:none; background: var(--text-primary); color: var(--page); border-radius:8px; padding:8px 10px; font-size:12px; line-height:1.45; max-width:280px; box-shadow: 0 6px 18px rgba(0,0,0,0.18); opacity:0; transition: opacity .08s; }
  .tip.show { opacity:1; }
  .tip b { font-weight:650; }
  .tip .tip-row { display:flex; justify-content:space-between; gap:14px; font-variant-numeric: tabular-nums; }
  .tip .tip-row span:first-child { opacity:0.7; }

  .lock-screen { position:fixed; inset:0; background: var(--page); display:flex; align-items:center; justify-content:center; z-index:1000; padding:20px; }
  .lock-card { width:100%; max-width:340px; background: var(--surface-1); border:1px solid var(--border); border-radius:14px; padding:28px 26px; text-align:center; }
  .lock-card h1 { font-size:17px; margin:0 0 4px; }
  .lock-card p { font-size:12.5px; color: var(--text-secondary); margin:0 0 18px; }
  .lock-input { width:100%; box-sizing:border-box; padding:10px 12px; border-radius:8px; border:1px solid var(--border); background: var(--page); color: var(--text-primary); font-size:16px; margin-bottom:10px; }
  .lock-btn { width:100%; padding:10px 12px; border-radius:8px; border:none; background: var(--text-primary); color: var(--page); font-size:13.5px; font-weight:600; cursor:pointer; }
  .lock-error { color: var(--critical); font-size:12px; margin-top:10px; min-height:16px; }

  /* --- Tablette ---------------------------------------------------------- */
  @media (max-width: 980px) {
    .summary-top { grid-template-columns: 1fr; }
    .stat-tiles { grid-template-columns: repeat(2, minmax(0,1fr)); }
  }

  /* --- Mobile ----------------------------------------------------------- */
  @media (max-width: 780px) {
    .app { padding: 16px 16px 48px; }
    h1 { font-size:17px; }
    header.top { margin-bottom:12px; }
    .layout { display:block; }
    .sidebar { display:none; }
    .mobile-nav { display:block; position:sticky; top:0; z-index:20; background: var(--page); margin: 0 -16px 12px; padding: 8px 16px 8px; border-bottom:1px solid var(--border); }
    .mobile-nav .row { display:flex; gap:6px; overflow-x:auto; scrollbar-width:none; -webkit-overflow-scrolling: touch; }
    .mobile-nav .row::-webkit-scrollbar { display:none; }
    .mobile-nav .row + .row { margin-top:8px; }
    .mobile-nav .row.sub .pill { font-size:12px; padding:5px 11px; }
    header.top { flex-wrap:nowrap; align-items:flex-start; }
    .theme-toggle { padding:5px 9px; font-size:11.5px; flex-shrink:0; }
    .mobile-nav .row { gap:5px; }
    .mobile-nav .pill { font-size:12px; padding:6px 10px; }
    .filters-toggle { display:flex; width:100%; align-items:center; justify-content:space-between; gap:8px; border:1px solid var(--border); background: var(--surface-1); color: var(--text-primary); border-radius:10px; padding:9px 12px; font-size:13px; cursor:pointer; margin-bottom:12px; text-align:left; }
    .filters-toggle .ft-sum { color: var(--text-secondary); font-size:12.5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .filters-toggle .ft-chev { color: var(--muted); flex-shrink:0; }
    .controls { display:none; grid-template-columns: 1fr 1fr; gap:10px; padding:10px; margin-top:-4px; }
    .controls.open { display:grid; }
    table.kpi-table th:first-child, table.kpi-table td:first-child { min-width:118px; }
    .control { width:auto; }
    .month-select, .dropdown-multi summary { min-width:0; font-size:14px; padding:8px 9px; }
    .dropdown-multi .dropdown-panel { min-width:0; width: calc(100vw - 52px); max-width:320px; }
    .chart-card { padding:14px; border-radius:10px; }
    .table-scroll { margin: 0 -14px; padding: 0 14px; }
    .bar-head { display:none; }
    .bar-row { grid-template-columns: minmax(0,1fr) auto 56px; grid-template-areas: "name value spark" "track track track"; gap:4px 10px; padding:8px 4px; }
    .bar-row .dealer-name { grid-area: name; }
    .bar-row .bar-track { grid-area: track; height:14px; }
    .bar-row .val-wrap { grid-area: value; }
    .bar-row .sparkline-wrap { grid-area: spark; }
    .val-wrap { display:flex; flex-direction:column; align-items:flex-end; }
    .hero-value { font-size:36px; }
    .stat-tiles { gap:10px; }
    .stat-tile { padding:11px 12px; }
    .stat-tile .t-value { font-size:19px; }
    .stat-tile .t-row .sparkline-wrap { display:none; }
    .group-line { text-align:left; }
    .card-head { flex-direction:column; gap:6px; }
    .page-title { font-size:16px; }
  }
  @media (max-width: 380px) {
    .controls { grid-template-columns: 1fr; }
    .stat-tiles { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="lock-screen" id="lockScreen">
  <div class="lock-card">
    <h1>Comparateur KPI — Groupe AutoMax</h1>
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
      <h1>Comparateur KPI — Groupe AutoMax</h1>
      <div class="subtitle" id="subtitle">Mis à jour le __GENERATED_AT__</div>
    </div>
    <button class="theme-toggle" id="themeToggle" type="button">Mode sombre</button>
  </header>

  <nav class="mobile-nav" id="mobileNav" aria-label="Sections"></nav>

  <button type="button" class="filters-toggle" id="filtersToggle" aria-expanded="false" aria-controls="controlsPanel"></button>
  <div class="controls" id="controlsPanel">
    <label class="control">
      <span class="control-label">Mois</span>
      <select id="refPeriodSelect" class="month-select"></select>
    </label>
    <label class="control">
      <span class="control-label">Période</span>
      <select id="periodSelect" class="month-select"></select>
    </label>
    <label class="control">
      <span class="control-label">Comparer à</span>
      <select id="basisSelect" class="month-select"></select>
    </label>
    <div class="control">
      <span class="control-label">Concessions</span>
      <details class="dropdown-multi" id="dealerDropdown">
        <summary id="dealerDropdownSummary">Concessions</summary>
        <div class="dropdown-panel">
          <div id="dealerFilter"></div>
          <label class="dealer-check combined" id="combinedToggleWrap">
            <input type="checkbox" id="combinedToggle" checked>
            <span>Afficher le total du groupe</span>
          </label>
        </div>
      </details>
    </div>
    <label class="control" id="viewControl">
      <span class="control-label">Affichage</span>
      <select id="viewSelect" class="month-select"></select>
    </label>
  </div>

  <div class="layout">
    <nav class="sidebar" id="sidebarNav" aria-label="Sections"></nav>
    <div class="main-pane">
      <div class="page-head" id="pageHead"></div>
      <div id="content"></div>
    </div>
  </div>

  <footer class="notes">
    Concessions suivies : BMW Sherbrooke, Ste-Marie Auto (STM), HAWKS, Volkswagen, Hyundai.
    Les écarts du groupe sont calculés à périmètre comparable : seules les concessions qui ont un budget (ou une année précédente) pour l'indicateur entrent dans l'écart.
    Pour ajouter un mois : section « Déposer un fichier ».
  </footer>
</div>
</div>
<div class="tip" id="tip" role="tooltip"></div>
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
// dealer -- "le groupe". It is never part of the roster/checkbox filter; it
// is shown as the headline figure of each card, as the first column of the
// tables and as the hero of the Sommaire.
const COMBINED_KEY = '__combined__';
// Where a new monthly source file actually needs to land for the automated
// GitHub Actions pipeline to pick it up and rebuild this site -- see
// renderUploadView() and .github/workflows/update-dashboard.yml.
const GITHUB_SOURCES_URL = 'https://github.com/groupeautomax/kpi-groupeautomax/upload/main/sources';
const NBSP = ' ';

function dealerLabel(key) {
  if (key === COMBINED_KEY) return 'Groupe';
  const d = DEALER_ROSTER.find(x => x.key === key);
  return d ? d.label : key;
}
function dealerListText(keys) {
  const names = keys.map(dealerLabel);
  if (names.length <= 1) return names.join('');
  return names.slice(0, -1).join(', ') + ' et ' + names[names.length - 1];
}
function periodLabel(periodKey) {
  const p = PERIOD_LIST.find(x => x.key === periodKey);
  return p ? p.label : periodKey;
}
function periodShortLabel(periodKey) {
  const m = /^(\\d{4})-(\\d{2})$/.exec(periodKey || '');
  if (!m) return periodKey;
  const names = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
  return names[parseInt(m[2], 10) - 1] + ' ' + m[1].slice(2);
}
function orderedKeys(keys) {
  const set = new Set(keys);
  return DEALER_ROSTER.map(d => d.key).filter(k => set.has(k));
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function isDark() {
  const stamp = document.documentElement.getAttribute('data-theme');
  if (stamp === 'dark') return true;
  if (stamp === 'light') return false;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}
// Color follows the dealer, never its rank: sorting or filtering never
// repaints a dealer.
function seriesColor(dealer) {
  if (dealer === COMBINED_KEY) return isDark() ? '#ffffff' : '#0b0b0b';
  const idx = DEALER_COLOR_INDEX[dealer] ?? 0;
  const arr = isDark() ? SERIES_DARK : SERIES_LIGHT;
  return arr[idx % arr.length];
}

const state = {
  dealers: new Set(DEALER_ROSTER.map(d => d.key)), // all 5 slots shown by default
  refPeriod: PERIOD_LIST.length ? PERIOD_LIST[PERIOD_LIST.length - 1].key : null, // which month, e.g. "2026-07" -- same for every dealer, never mixed
  period: 'month', // month | ytd | quarter -- which slice of that one reference month
  basis: 'budget', // budget | prior_year
  scope: 'summary', // summary | overview | departments | upload
  group: 'volume',
  dept: null, // selected department name when scope === 'departments'
  view: 'chart', // chart | table
  showCombined: true // whether the "Groupe" total is shown in cards and tables
};

// Canonical department order + French labels for the "Départements" view.
// Extra/unexpected department names found in the data (a dealer-specific
// line like STM's "Wholesale autres") are appended after these, so nothing
// is silently dropped.
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
// each top-line department metric.
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
const expandedMetrics = {};

// --- Sens des indicateurs --------------------------------------------------
// Top-level expense KPIs come out of the source files as negative numbers.
// They are shown as positive amounts ("Dépenses 410 379 $") so that a bar,
// an arrow and a sort all read the natural way; the colour of an écart then
// says whether the move is good (spending less than budget = green).
const NEGATE_FOR_DISPLAY = new Set(['depenses', 'depenses_variables', 'depenses_personnel', 'depenses_semifixes']);
const LOWER_IS_BETTER = new Set(['depenses', 'depenses_variables', 'depenses_personnel', 'depenses_semifixes',
  'total_variables', 'total_personnel', 'total_semifixes', 'total_depenses', 'impot']);
const LOWER_IS_BETTER_SECTIONS = new Set(['variables', 'personnel', 'semifixes']);
// Ratio KPIs: the group figure is recomputed from the summed numerator and
// denominator (never a sum or an average of each dealer's ratio).
const RATIO_KPIS = {
  ebt_pct_profit_brut: ['ebt', 'pb_total'],
  ros: ['ebt', 'ventes_nettes'],
  gpa_neuf: ['pb_neuf', 'unites_neuf'],
  gpa_usage: ['pb_usage', 'unites_usage'],
};

function isNum(v) { return typeof v === 'number' && isFinite(v); }
function displaySign(key) { return NEGATE_FOR_DISPLAY.has(key) ? -1 : 1; }
function displayKv(key, kv) {
  if (!kv || !NEGATE_FOR_DISPLAY.has(key)) return kv;
  const out = Object.assign({}, kv);
  ['real', 'budget', 'prior_year', 'delta_budget', 'delta_prior_year'].forEach(f => {
    if (isNum(out[f])) out[f] = -out[f];
  });
  return out;
}
// good / critical / neutral for an écart, given which direction is good.
function toneFor(key, delta, lowerIsBetter) {
  if (!isNum(delta) || Math.abs(delta) < 1e-9) return 'neutral';
  const lower = lowerIsBetter !== undefined ? lowerIsBetter : LOWER_IS_BETTER.has(key);
  return ((delta > 0) !== lower) ? 'good' : 'critical';
}

// --- Formats (fr-CA) ---------------------------------------------------
function fmtMoney(v) {
  if (!isNum(v)) return '—';
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 }).format(v);
}
function fmtMoneyCompact(v) {
  if (!isNum(v)) return '—';
  if (Math.abs(v) >= 1e6) {
    return (v / 1e6).toLocaleString('fr-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + NBSP + 'M$';
  }
  return fmtMoney(v);
}
function fmtNum(v) {
  if (!isNum(v)) return '—';
  return new Intl.NumberFormat('fr-CA', { maximumFractionDigits: 0 }).format(v);
}
function fmtDec1(v) {
  return v.toLocaleString('fr-CA', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}
function fmtPercent(v) {
  if (!isNum(v)) return '—';
  return fmtDec1(v * 100) + NBSP + '%';
}
function fmtValue(group, v) {
  if (group === 'volume') return fmtNum(v);
  if (group === 'percent') return fmtPercent(v);
  return fmtMoney(v);
}
function fmtValueCompact(group, v) {
  if (group === 'volume' || group === 'percent') return fmtValue(group, v);
  return fmtMoneyCompact(v);
}
function fmtSignedPct(pct) {
  if (!isNum(pct)) return '';
  const r = Math.round(pct * 10) / 10;
  return (r > 0 ? '+' : r < 0 ? '−' : '') + fmtDec1(Math.abs(r)) + NBSP + '%';
}
function fmtSignedPts(delta) { // delta of a ratio, e.g. 0.012 -> "+1,2 pt"
  if (!isNum(delta)) return '';
  const r = Math.round(delta * 1000) / 10;
  return (r > 0 ? '+' : r < 0 ? '−' : '') + fmtDec1(Math.abs(r)) + NBSP + 'pt';
}
function fmtSignedValue(group, delta) {
  if (!isNum(delta)) return '—';
  if (group === 'percent') return fmtSignedPts(delta);
  const s = delta > 0 ? '+' : delta < 0 ? '−' : '';
  return s + fmtValue(group, Math.abs(delta));
}

// A KPI's own `.format` field (only set on the two EBT ratio KPIs) overrides
// the tab-level group for value formatting.
function kpiFormat(key, fallbackGroup) {
  for (const dealer of orderedKeys(state.dealers)) {
    const period = resolvedPeriod(dealer);
    const sec = period ? sectionFor(dealer, period, state.period) : undefined;
    const kpi = sec ? sec.kpis[key] : undefined;
    if (kpi && kpi.format) return kpi.format;
  }
  if (fallbackGroup === 'volume' || fallbackGroup === 'percent') return fallbackGroup;
  return 'money';
}

// Every dealer is read at the SAME globally-selected reference period
// (state.refPeriod) -- never each dealer's own latest. A dealer with no data
// for that exact period returns undefined (shows n/d), it never falls back
// to a different month.
function resolvedPeriod(dealer) {
  if (dealer === COMBINED_KEY) {
    const hasAny = orderedKeys(state.dealers).some(k => STORE.dealers[k]?.periods?.[state.refPeriod]);
    return hasAny ? state.refPeriod : undefined;
  }
  const periods = STORE.dealers[dealer]?.periods || {};
  return periods[state.refPeriod] ? state.refPeriod : undefined;
}
// Dealers that actually carry figures for the selected month AND period
// mode (a dealer's file may have the month but no quarter block).
function dealersWithData() {
  return orderedKeys(state.dealers).filter(d => {
    const p = resolvedPeriod(d);
    return p && sectionFor(d, p, state.period);
  });
}

// Quarter mode: one single quarter for the whole dashboard, the one most of
// the selected dealers carry for that month (ties -> the most recent), so a
// dealer's Q2 is never shown beside another dealer's Q3 as if they matched.
function globalQuarterKey(period) {
  const counts = {};
  orderedKeys(state.dealers).forEach(d => {
    const secs = STORE.dealers[d]?.periods?.[period]?.sections || {};
    Object.keys(secs).filter(k => k.startsWith('quarter_')).forEach(k => { counts[k] = (counts[k] || 0) + 1; });
  });
  const keys = Object.keys(counts);
  if (!keys.length) return undefined;
  keys.sort((a, b) => (counts[b] - counts[a]) || (a < b ? 1 : -1));
  return keys[0];
}
function sectionFor(dealer, period, periodMode) {
  const sections = STORE.dealers[dealer]?.periods?.[period]?.sections || {};
  if (periodMode === 'month') return sections['month'];
  if (periodMode === 'ytd') return sections['ytd'];
  if (periodMode === 'quarter') {
    const qk = globalQuarterKey(period);
    return qk ? sections[qk] : undefined;
  }
  return undefined;
}
function periodModeLabel() {
  if (state.period === 'ytd') return 'Cumulatif annuel';
  if (state.period === 'quarter') {
    const qk = globalQuarterKey(state.refPeriod);
    return qk ? 'Trimestre ' + qk.replace('quarter_q', 'T') : 'Trimestre';
  }
  return 'Mois';
}

// Same calendar month one year earlier, e.g. "2026-07" -> "2025-07".
function priorYearPeriodKey(periodKey) {
  const m = /^(\\d{4})-(\\d{2})$/.exec(periodKey || '');
  if (!m) return null;
  return `${parseInt(m[1], 10) - 1}-${m[2]}`;
}

// HAWKS' and STM's GM "Composite Financial Statement" .xlsm months carry no
// budget/prior-year columns at all -- the dashboard computes the
// year-over-year comparison itself from our own store when the same month a
// year earlier is on file. An explicit prior_year already provided by a
// source file is always left untouched.
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

// Display-ready KPI for one dealer at the selected period (synthesized prior
// year + expense sign applied).
function dealerKpi(dealer, key) {
  const period = resolvedPeriod(dealer);
  const sec = period ? sectionFor(dealer, period, state.period) : undefined;
  let kpi = sec ? sec.kpis[key] : undefined;
  if (!kpi) return undefined;
  kpi = withSynthesizedPriorYear(dealer, period, state.period, kpi, (pySec) => pySec.kpis[key]);
  return displayKv(key, kpi);
}
function dealerDeptMetric(dealer, deptName, metricKey) {
  const period = resolvedPeriod(dealer);
  const sec = period ? sectionFor(dealer, period, state.period) : undefined;
  const dept = sec && sec.departments ? sec.departments[deptName] : undefined;
  const metric = dept ? dept[metricKey] : undefined;
  if (!metric) return undefined;
  return withSynthesizedPriorYear(dealer, period, state.period, metric,
    (pySec) => pySec.departments && pySec.departments[deptName] ? pySec.departments[deptName][metricKey] : undefined);
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

// --- Le groupe (total des concessions cochées) ----------------------------
// The group's own real figure sums every checked dealer. Its écart vs budget
// (or prior year) is computed at comparable scope: only the dealers that
// actually carry a comparison figure for that KPI enter both sides of the
// écart -- otherwise five dealers' real would be set against two dealers'
// budget (e.g. "+253 %" on new units). `coverage` records who is in / out,
// so each card can say so.
function usableCompare(kv, field) {
  if (!kv || !isNum(kv.real)) return false;
  const v = kv[field];
  if (!isNum(v)) return false;
  if (field === 'budget' && v === 0) return false; // 0 = budget non saisi
  return true;
}
function deltaFieldFor(field) { return field === 'budget' ? 'delta_budget' : 'delta_prior_year'; }

function sumKv(entries) { // entries: [{dealer, kv}]
  const withReal = entries.filter(e => e.kv && isNum(e.kv.real));
  if (!withReal.length) return null;
  const out = { real: withReal.reduce((a, e) => a + e.kv.real, 0), dealers: withReal.map(e => e.dealer), coverage: {} };
  ['budget', 'prior_year'].forEach(f => {
    const sub = withReal.filter(e => usableCompare(e.kv, f));
    if (sub.length) {
      const cmp = sub.reduce((a, e) => a + e.kv[f], 0);
      const realSub = sub.reduce((a, e) => a + e.kv.real, 0);
      out[f] = cmp;
      out[deltaFieldFor(f)] = realSub - cmp;
    } else {
      out[f] = null;
      out[deltaFieldFor(f)] = null;
    }
    out.coverage[f] = { included: sub.map(e => e.dealer), missing: withReal.filter(e => !sub.includes(e)).map(e => e.dealer) };
  });
  return out;
}

// rows: [{dealer, n: kv, de: kv, r: kv|null}] -> group ratio = sum(n) / sum(d)
function ratioOfSums(rows, format) {
  const usable = rows.filter(x => x.n && x.de && isNum(x.n.real) && isNum(x.de.real));
  if (!usable.length) return null;
  const sum = (arr, get) => arr.reduce((a, x) => a + get(x), 0);
  const denR = sum(usable, x => x.de.real);
  const out = { real: denR ? sum(usable, x => x.n.real) / denR : null, format, dealers: usable.map(x => x.dealer), coverage: {} };
  ['budget', 'prior_year'].forEach(f => {
    // A dealer enters the comparison only if it has the comparison figure
    // for the ratio itself (KPI ratios) or for the numerator (dept %), plus
    // both components.
    const sub = usable.filter(x => usableCompare(x.r || x.n, f) && isNum(x.n[f]) && isNum(x.de[f]));
    const denC = sum(sub, x => x.de[f]);
    const denRs = sum(sub, x => x.de.real);
    if (sub.length && denC && denRs) {
      out[f] = sum(sub, x => x.n[f]) / denC;
      out[deltaFieldFor(f)] = sum(sub, x => x.n.real) / denRs - out[f];
    } else {
      out[f] = null;
      out[deltaFieldFor(f)] = null;
    }
    out.coverage[f] = { included: sub.map(x => x.dealer), missing: usable.filter(x => !sub.includes(x)).map(x => x.dealer) };
  });
  return out;
}

function combinedKpiFor(key) {
  if (RATIO_KPIS[key]) {
    const [numKey, denKey] = RATIO_KPIS[key];
    const rows = [];
    orderedKeys(state.dealers).forEach(d => {
      const r = dealerKpi(d, key);
      if (!r) return;
      rows.push({ dealer: d, r, n: dealerKpi(d, numKey), de: dealerKpi(d, denKey) });
    });
    const fmt = rows.length && rows[0].r.format ? rows[0].r.format : null;
    const out = ratioOfSums(rows, fmt);
    if (out) out.format = fmt;
    return out;
  }
  return sumKv(orderedKeys(state.dealers).map(d => ({ dealer: d, kv: dealerKpi(d, key) })));
}

// Department metric keys that carry a nested "% of profit brut" sub-field --
// for the group it is recomputed from summed expense $ over summed
// department profit brut $, never averaged per dealer.
const DEPT_PCT_KEYS_JS = new Set(['total_variables', 'total_personnel', 'total_semifixes', 'total_depenses']);

function combinedDeptMetricFor(deptName, metricKey) {
  const entries = orderedKeys(state.dealers).map(d => ({ dealer: d, kv: dealerDeptMetric(d, deptName, metricKey) }));
  const combined = sumKv(entries);
  if (!combined) return null;
  if (DEPT_PCT_KEYS_JS.has(metricKey)) {
    const rows = entries.filter(e => e.kv).map(e => ({ dealer: e.dealer, n: e.kv, de: dealerDeptMetric(e.dealer, deptName, 'profit_brut'), r: null }));
    const ratio = ratioOfSums(rows, 'percent');
    if (ratio) combined.pct = { real: ratio.real, delta_budget: ratio.delta_budget, delta_prior_year: ratio.delta_prior_year };
  }
  return combined;
}

// --- Historique (tendance 12 mois) ---------------------------------------
const TREND_MAX_POINTS = 12;

function metricKvFromSection(sec, key, detailOpts) {
  if (!sec) return undefined;
  if (detailOpts) {
    const dept = sec.departments ? sec.departments[detailOpts.deptName] : undefined;
    return dept ? dept[key] : undefined;
  }
  return sec.kpis ? sec.kpis[key] : undefined;
}
function periodsUpToRef(periodKeys) {
  return periodKeys.filter(p => !state.refPeriod || p <= state.refPeriod).sort();
}
function historyFor(dealer, key, detailOpts) {
  const periods = periodsUpToRef(Object.keys(STORE.dealers[dealer]?.periods || {}));
  const points = [];
  const sign = detailOpts ? 1 : displaySign(key);
  periods.forEach(periodKey => {
    const val = metricKvFromSection(sectionFor(dealer, periodKey, state.period), key, detailOpts);
    if (val && isNum(val.real)) points.push({ period: periodKey, value: sign * val.real });
  });
  return points.slice(-TREND_MAX_POINTS);
}
// Group trend: only the months where EVERY selected dealer has a figure, so a
// dealer joining the file history (Hyundai from April 2026) doesn't show up
// as a fake jump in the group line.
function historyForCombined(key, detailOpts) {
  const dealers = orderedKeys(state.dealers).filter(d => STORE.dealers[d]);
  if (!dealers.length) return [];
  const allPeriods = new Set();
  dealers.forEach(d => Object.keys(STORE.dealers[d].periods || {}).forEach(p => allPeriods.add(p)));
  const sign = detailOpts ? 1 : displaySign(key);
  const ratio = !detailOpts && RATIO_KPIS[key];
  const points = [];
  periodsUpToRef(Array.from(allPeriods)).forEach(periodKey => {
    let num = 0, den = 0, ok = true;
    dealers.forEach(d => {
      if (!ok) return;
      const sec = sectionFor(d, periodKey, state.period);
      if (ratio) {
        const n = metricKvFromSection(sec, ratio[0]), de = metricKvFromSection(sec, ratio[1]);
        if (!n || !de || !isNum(n.real) || !isNum(de.real)) { ok = false; return; }
        num += n.real; den += de.real;
      } else {
        const v = metricKvFromSection(sec, key, detailOpts);
        if (!v || !isNum(v.real)) { ok = false; return; }
        num += sign * v.real;
      }
    });
    if (!ok) return;
    if (ratio) { if (den) points.push({ period: periodKey, value: num / den }); }
    else points.push({ period: periodKey, value: num });
  });
  return points.slice(-TREND_MAX_POINTS);
}

// --- Infobulle ------------------------------------------------------------
function tipEl() { return document.getElementById('tip'); }
function positionTip(x, y) {
  const t = tipEl();
  const pad = 10, w = t.offsetWidth, h = t.offsetHeight;
  let left = x + 14, top = y + 16;
  if (left + w + pad > window.innerWidth) left = x - w - 14;
  if (top + h + pad > window.innerHeight) top = y - h - 12;
  t.style.left = Math.max(pad, left) + 'px';
  t.style.top = Math.max(pad, top) + 'px';
}
function showTip(html, x, y) {
  const t = tipEl();
  t.innerHTML = html;
  t.classList.add('show');
  positionTip(x, y);
}
function hideTip() { const t = tipEl(); if (t) t.classList.remove('show'); }
function attachTip(el, htmlFn) {
  el._tipFn = htmlFn;
  el.setAttribute('data-tiphost', '1');
  if (!el.hasAttribute('tabindex')) el.tabIndex = 0;
  el.addEventListener('mouseenter', e => showTip(htmlFn(), e.clientX, e.clientY));
  el.addEventListener('mousemove', e => positionTip(e.clientX, e.clientY));
  el.addEventListener('mouseleave', hideTip);
  el.addEventListener('focus', () => { const r = el.getBoundingClientRect(); showTip(htmlFn(), r.left + Math.min(r.width / 2, 160), r.bottom - 4); });
  el.addEventListener('blur', hideTip);
}
function tipRows(pairs) {
  return pairs.filter(Boolean).map(([k, v]) => `<div class="tip-row"><span>${k}</span><span>${v}</span></div>`).join('');
}
window.addEventListener('scroll', hideTip, { passive: true });
document.addEventListener('touchstart', (e) => { if (!e.target.closest || !e.target.closest('[data-tiphost], .sparkline-wrap, .hero-trend')) hideTip(); }, { passive: true });

// --- Sparkline (12 points) with hover ------------------------------------
// Trend shape in the muted ink; the current period is a dot in the dealer's
// own colour; hovering reads any month.
function renderSparkline(points, color, group, opts) {
  const o = Object.assign({ w: 56, h: 22 }, opts || {});
  const wrap = document.createElement('div');
  wrap.className = 'sparkline-wrap';
  if (!points || points.length < 2) {
    const nd = document.createElement('span');
    nd.className = 'no-data';
    nd.textContent = 'n/d';
    wrap.appendChild(nd);
    return wrap;
  }
  const w = o.w, h = o.h, pad = 3;
  const vals = points.map(p => p.value);
  const min = Math.min(...vals), max = Math.max(...vals);
  const range = (max - min) || Math.abs(max) || 1;
  const stepX = (w - pad * 2) / (points.length - 1);
  const xy = points.map((p, i) => [pad + i * stepX, h - pad - ((p.value - min) / range) * (h - pad * 2)]);
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('width', String(w));
  svg.setAttribute('height', String(h));
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Tendance : ' + points.map(p => `${periodLabel(p.period)} ${fmtValue(group, p.value)}`).join(', '));
  const line = document.createElementNS(NS, 'path');
  line.setAttribute('d', xy.map(([x, y], i) => (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1)).join(' '));
  line.setAttribute('fill', 'none');
  line.setAttribute('stroke', 'var(--muted)');
  line.setAttribute('stroke-width', '1.5');
  line.setAttribute('stroke-linecap', 'round');
  line.setAttribute('stroke-linejoin', 'round');
  svg.appendChild(line);
  const [lastX, lastY] = xy[xy.length - 1];
  const dot = document.createElementNS(NS, 'circle');
  dot.setAttribute('cx', String(lastX));
  dot.setAttribute('cy', String(lastY));
  dot.setAttribute('r', '2.5');
  dot.setAttribute('fill', color);
  svg.appendChild(dot);
  const hover = document.createElementNS(NS, 'circle');
  hover.setAttribute('r', '3');
  hover.setAttribute('fill', 'var(--text-primary)');
  hover.setAttribute('stroke', 'var(--surface-1)');
  hover.setAttribute('stroke-width', '1.5');
  hover.style.display = 'none';
  svg.appendChild(hover);
  const hit = document.createElementNS(NS, 'rect');
  hit.setAttribute('x', '-4'); hit.setAttribute('y', '-6');
  hit.setAttribute('width', String(w + 8)); hit.setAttribute('height', String(h + 12));
  hit.setAttribute('fill', 'transparent');
  svg.appendChild(hit);
  const onMove = (e) => {
    const r = svg.getBoundingClientRect();
    const x = (e.clientX - r.left) * (w / r.width);
    const i = Math.max(0, Math.min(points.length - 1, Math.round((x - pad) / stepX)));
    hover.setAttribute('cx', String(xy[i][0]));
    hover.setAttribute('cy', String(xy[i][1]));
    hover.style.display = '';
    showTip(`<b>${periodLabel(points[i].period)}</b><br>${fmtValue(group, points[i].value)}`, e.clientX, e.clientY);
  };
  svg.addEventListener('mousemove', (e) => { e.stopPropagation(); onMove(e); });
  svg.addEventListener('mouseleave', (e) => {
    hover.style.display = 'none';
    const host = wrap.closest('[data-tiphost]');
    if (host && host._tipFn) showTip(host._tipFn(), e.clientX, e.clientY); else hideTip();
  });
  wrap.appendChild(svg);
  return wrap;
}

// Larger trend line for the Sommaire hero (fluid width, HTML overlay for the
// dots so they stay round whatever the width).
function renderTrendChart(points, group) {
  const wrap = document.createElement('div');
  wrap.className = 'hero-trend';
  if (!points || points.length < 2) {
    wrap.innerHTML = '<div class="no-data">Pas assez d\\'historique commun pour tracer une tendance.</div>';
    return wrap;
  }
  const W = 600, H = 80, padY = 6;
  const vals = points.map(p => p.value);
  let min = Math.min(...vals), max = Math.max(...vals);
  if (min > 0 && (max - min) < max * 0.02) min = min * 0.98;
  const range = (max - min) || 1;
  const xs = points.map((p, i) => i / (points.length - 1) * W);
  const ys = points.map(p => H - padY - ((p.value - min) / range) * (H - padY * 2));
  const NS = 'http://www.w3.org/2000/svg';
  const box = document.createElement('div');
  box.style.position = 'relative';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Tendance du groupe : ' + points.map(p => `${periodLabel(p.period)} ${fmtValue(group, p.value)}`).join(', '));
  const linePath = xs.map((x, i) => (i ? 'L' : 'M') + x.toFixed(1) + ',' + ys[i].toFixed(1)).join(' ');
  const area = document.createElementNS(NS, 'path');
  area.setAttribute('d', linePath + ` L${W},${H} L0,${H} Z`);
  area.setAttribute('fill', 'var(--text-primary)');
  area.setAttribute('fill-opacity', '0.05');
  svg.appendChild(area);
  if (min < 0 && max > 0) {
    const zy = H - padY - ((0 - min) / range) * (H - padY * 2);
    const z = document.createElementNS(NS, 'line');
    z.setAttribute('x1', '0'); z.setAttribute('x2', String(W));
    z.setAttribute('y1', String(zy)); z.setAttribute('y2', String(zy));
    z.setAttribute('stroke', 'var(--baseline)'); z.setAttribute('vector-effect', 'non-scaling-stroke');
    svg.appendChild(z);
  }
  const line = document.createElementNS(NS, 'path');
  line.setAttribute('d', linePath);
  line.setAttribute('fill', 'none');
  line.setAttribute('stroke', 'var(--text-primary)');
  line.setAttribute('stroke-width', '2');
  line.setAttribute('stroke-linejoin', 'round');
  line.setAttribute('vector-effect', 'non-scaling-stroke');
  svg.appendChild(line);
  box.appendChild(svg);
  const mkDot = (bg) => {
    const d = document.createElement('div');
    d.style.cssText = `position:absolute;width:9px;height:9px;border-radius:50%;background:${bg};box-shadow:0 0 0 2px var(--surface-1);transform:translate(-50%,-50%);pointer-events:none;`;
    return d;
  };
  const last = mkDot('var(--text-primary)');
  last.style.left = '100%'; last.style.top = (ys[ys.length - 1] / H * 100) + '%';
  box.appendChild(last);
  const hv = mkDot('var(--text-primary)');
  hv.style.display = 'none';
  const hair = document.createElement('div');
  hair.style.cssText = 'position:absolute;top:0;bottom:0;width:1px;background:var(--baseline);pointer-events:none;display:none;';
  box.appendChild(hair);
  box.appendChild(hv);
  box.addEventListener('mousemove', (e) => {
    const r = box.getBoundingClientRect();
    const f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
    const i = Math.round(f * (points.length - 1));
    const lp = (i / (points.length - 1) * 100) + '%';
    hv.style.left = lp; hv.style.top = (ys[i] / H * 100) + '%'; hv.style.display = '';
    hair.style.left = lp; hair.style.display = '';
    showTip(`<b>${periodLabel(points[i].period)}</b><br>${fmtValue(group, points[i].value)}`, e.clientX, e.clientY);
  });
  box.addEventListener('mouseleave', () => { hv.style.display = 'none'; hair.style.display = 'none'; hideTip(); });
  wrap.appendChild(box);
  const axis = document.createElement('div');
  axis.className = 'axis-labels';
  axis.innerHTML = `<span>${periodShortLabel(points[0].period)}</span><span>${periodShortLabel(points[points.length - 1].period)}</span>`;
  wrap.appendChild(axis);
  return wrap;
}

// --- Filtres --------------------------------------------------------------
function updateDealerDropdownSummary() {
  const summary = document.getElementById('dealerDropdownSummary');
  if (!summary) return;
  const total = DEALER_ROSTER.length;
  const n = state.dealers.size;
  summary.textContent = n === total ? `Toutes (${total})` : `${n} sur ${total}`;
}
function renderDealerFilter() {
  const el = document.getElementById('dealerFilter');
  el.innerHTML = '';
  DEALER_ROSTER.forEach(({ key, label }) => {
    const has = !!STORE.dealers[key];
    const wrap = document.createElement('label');
    wrap.className = 'dealer-check' + (has ? '' : ' pending');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = state.dealers.has(key);
    cb.addEventListener('change', () => {
      if (cb.checked) state.dealers.add(key); else state.dealers.delete(key);
      updateDealerDropdownSummary();
      renderAll();
    });
    wrap.appendChild(cb);
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = seriesColor(key);
    wrap.appendChild(sw);
    const span = document.createElement('span');
    span.textContent = has ? label : label + ' (à venir)';
    wrap.appendChild(span);
    el.appendChild(wrap);
  });
  updateDealerDropdownSummary();
}
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
  ], state.basis, (k) => { state.basis = k; renderAll(); });
  makeSelect(document.getElementById('viewSelect'), [
    { key: 'chart', label: 'Graphiques' },
    { key: 'table', label: 'Tableau' }
  ], state.view, (k) => { state.view = k; renderAll(); });
  const vc = document.getElementById('viewControl');
  if (vc) vc.style.display = (state.scope === 'overview' || state.scope === 'departments') ? '' : 'none';
  renderSidebar();
  renderMobileNav();
  renderFiltersToggle();
  syncThemeLabel();
}
function renderFiltersToggle() {
  const btn = document.getElementById('filtersToggle');
  if (!btn) return;
  const panel = document.getElementById('controlsPanel');
  const open = panel.classList.contains('open');
  const n = state.dealers.size, total = DEALER_ROSTER.length;
  const sum = [periodLabel(state.refPeriod), periodModeLabel(), 'vs ' + compareLabel(), n === total ? 'toutes les concessions' : `${n} sur ${total} concessions`].join(' · ');
  btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  btn.innerHTML = `<span><b>Filtres</b> <span class="ft-sum">${escapeHtml(sum)}</span></span><span class="ft-chev">${open ? '▴' : '▾'}</span>`;
  btn.onclick = () => { panel.classList.toggle('open'); renderFiltersToggle(); };
}
function syncThemeLabel() {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = isDark() ? 'Mode clair' : 'Mode sombre';
}

// --- Navigation -----------------------------------------------------------
function setScope(scope) {
  state.scope = scope;
  if (scope === 'departments') {
    const deptNames = collectDepartmentNames();
    if (!state.dept || !deptNames.includes(state.dept)) state.dept = deptNames[0] || null;
  }
  renderAll();
  window.scrollTo({ top: 0 });
}
function subNavItems() {
  if (state.scope === 'overview') {
    return GROUP_ORDER.filter(g => g !== 'other' || hasOtherKpis()).map(g => ({
      label: GROUP_LABELS[g], active: state.group === g, go: () => { state.group = g; renderAll(); }
    }));
  }
  if (state.scope === 'departments') {
    const deptNames = collectDepartmentNames();
    if (!state.dept || !deptNames.includes(state.dept)) state.dept = deptNames[0] || null;
    return deptNames.map(n => ({ label: n, active: state.dept === n, go: () => { state.dept = n; renderAll(); } }));
  }
  return [];
}
const NAV_SECTIONS = [
  { scope: 'summary', label: 'Sommaire', short: 'Sommaire' },
  { scope: 'overview', label: 'Indicateurs', short: 'Indicateurs' },
  { scope: 'departments', label: 'Départements', short: 'Départements' },
];
function renderSidebar() {
  const nav = document.getElementById('sidebarNav');
  nav.innerHTML = '';
  NAV_SECTIONS.forEach(s => {
    const section = document.createElement('div');
    section.className = 'nav-section';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nav-parent' + (state.scope === s.scope ? ' active' : '');
    btn.textContent = s.label;
    btn.addEventListener('click', () => setScope(s.scope));
    section.appendChild(btn);
    if (state.scope === s.scope) {
      const items = subNavItems();
      if (items.length) {
        const sub = document.createElement('div');
        sub.className = 'nav-sub';
        items.forEach(it => {
          const b = document.createElement('button');
          b.type = 'button';
          b.className = 'nav-item' + (it.active ? ' active' : '');
          b.textContent = it.label;
          b.addEventListener('click', it.go);
          sub.appendChild(b);
        });
        section.appendChild(sub);
      }
    }
    nav.appendChild(section);
  });
  const uploadSection = document.createElement('div');
  uploadSection.className = 'nav-section nav-section-upload';
  const uploadBtn = document.createElement('button');
  uploadBtn.type = 'button';
  uploadBtn.className = 'nav-parent nav-parent-upload' + (state.scope === 'upload' ? ' active' : '');
  uploadBtn.textContent = '+ Déposer un fichier';
  uploadBtn.addEventListener('click', () => setScope('upload'));
  uploadSection.appendChild(uploadBtn);
  nav.appendChild(uploadSection);
}
// Phone: the sidebar becomes two scrollable pill rows pinned at the top.
function renderMobileNav() {
  const nav = document.getElementById('mobileNav');
  if (!nav) return;
  nav.innerHTML = '';
  const row = document.createElement('div');
  row.className = 'row';
  NAV_SECTIONS.concat([{ scope: 'upload', short: '+ Fichier' }]).forEach(s => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'pill' + (state.scope === s.scope ? ' active' : '');
    b.textContent = s.short;
    b.addEventListener('click', () => setScope(s.scope));
    row.appendChild(b);
  });
  nav.appendChild(row);
  const items = subNavItems();
  if (items.length) {
    const sub = document.createElement('div');
    sub.className = 'row sub';
    let activeBtn = null;
    items.forEach(it => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'pill' + (it.active ? ' active' : '');
      b.textContent = it.label;
      b.addEventListener('click', it.go);
      if (it.active) activeBtn = b;
      sub.appendChild(b);
    });
    nav.appendChild(sub);
    if (activeBtn) requestAnimationFrame(() => {
      const left = activeBtn.offsetLeft - 16;
      if (left > sub.scrollLeft + sub.clientWidth - activeBtn.offsetWidth || left < sub.scrollLeft) sub.scrollLeft = Math.max(0, left);
    });
  }
}
function hasOtherKpis() {
  let found = false;
  Object.keys(STORE.dealers).forEach(dealer => {
    const period = resolvedPeriod(dealer);
    if (!period) return;
    ['month', 'ytd'].forEach(pm => {
      const sec = sectionFor(dealer, period, pm);
      if (sec) Object.values(sec.kpis).forEach(k => { if (k.group === 'other') found = true; });
    });
  });
  return found;
}

// --- Comparaison (budget / année précédente) ------------------------------
function deltaFieldForBasis() { return deltaFieldFor(state.basis); }
function compareValueFieldForBasis() { return state.basis === 'budget' ? 'budget' : 'prior_year'; }
function compareLabel() { return state.basis === 'budget' ? 'budget' : 'année préc.'; }
function compareLabelLong() { return state.basis === 'budget' ? 'Budget' : 'Année précédente'; }
function compareMissingText(keys) {
  if (!keys.length) return '';
  return (state.basis === 'budget' ? 'Sans budget pour cet indicateur : ' : 'Sans année précédente pour cet indicateur : ') + dealerListText(keys) + '.';
}
// A budget of exactly 0 generally means "not entered" -- hide the comparison
// rather than show a misleading variance.
function hasCompareData(kpi) {
  if (!kpi) return false;
  const base = kpi[compareValueFieldForBasis()];
  if (!isNum(base)) return false;
  if (state.basis === 'budget' && base === 0) return false;
  return isNum(kpi[deltaFieldForBasis()]);
}
// Variance in % vs the comparison basis, same sign as the $ delta. |base| as
// denominator so a negative base doesn't flip the sign.
function deltaPct(kpi) {
  if (!hasCompareData(kpi)) return null;
  const base = kpi[compareValueFieldForBasis()];
  const delta = kpi[deltaFieldForBasis()];
  if (!base) return null;
  const pct = (delta / Math.abs(base)) * 100;
  return isFinite(pct) ? pct : null;
}
// "▲ 5 (+20,8 %)" -- arrow = direction of the figure, colour = good or bad.
function deltaInfo(key, kpi, group, lowerIsBetter) {
  if (!hasCompareData(kpi)) return null;
  const d = kpi[deltaFieldForBasis()];
  const tone = toneFor(key, d, lowerIsBetter);
  const arrow = d > 0 ? '▲' : d < 0 ? '▼' : '=';
  let text, short;
  if (group === 'percent') {
    text = arrow + ' ' + fmtSignedPts(d).replace(/^[+−]/, '');
    short = fmtSignedPts(d);
  } else {
    const pct = deltaPct(kpi);
    text = arrow + ' ' + fmtValue(group, Math.abs(d)) + (isNum(pct) ? ` <span class="delta-pct">(${fmtSignedPct(pct)})</span>` : '');
    short = isNum(pct) ? fmtSignedPct(pct) : fmtSignedValue(group, d);
  }
  return { tone, text, short, delta: d };
}
function deptPctLineText(kpi) {
  if (!kpi || !kpi.pct || !isNum(kpi.pct.real)) return null;
  let text = Math.round(kpi.pct.real * 100) + NBSP + '% du profit brut';
  const ptDelta = kpi.pct[deltaFieldForBasis()];
  if (isNum(ptDelta)) text += ' (' + fmtSignedPts(ptDelta) + ')';
  return text;
}
function coverageNote(kv) {
  if (!kv || !kv.coverage) return '';
  const cov = kv.coverage[compareValueFieldForBasis()];
  if (!cov || !cov.missing.length || !cov.included.length) return '';
  const tot = cov.included.length + cov.missing.length;
  return `${cov.included.length} concession${cov.included.length > 1 ? 's' : ''} sur ${tot}`;
}

// --- Détail des postes (département) -------------------------------------
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
function lineItemPrimary(item) {
  if (item.money) return item.money;
  if (item.units) return item.units;
  return item.pct;
}
function lineItemGroup(item) { return item.money ? 'money' : 'volume'; }
function lineItemUnitsNote(item) {
  if (item.section === 'ventes' && item.money && item.units && isNum(item.units.real)) return fmtNum(item.units.real) + ' un.';
  return null;
}
function renderLineItemDetailTable(deptName, sections) {
  const labels = collectLineItemLabels(deptName, sections);
  const wrap = document.createElement('div');
  wrap.className = 'line-item-detail';
  if (!labels.length) {
    wrap.innerHTML = '<div class="no-data">Aucun détail disponible pour la sélection actuelle.</div>';
    return wrap;
  }
  const dealerKeys = orderedKeys(state.dealers);
  const scroll = document.createElement('div');
  scroll.className = 'table-scroll';
  const table = document.createElement('table');
  table.className = 'kpi-table detail-table';
  table.innerHTML = '<thead><tr><th>Poste (détail source)</th>' + dealerKeys.map(k =>
    `<th><span class="th-dealer"><span class="swatch" style="background:${seriesColor(k)}"></span>${escapeHtml(dealerLabel(k))}</span></th>`).join('') + '</tr></thead>';
  const tbody = document.createElement('tbody');
  labels.forEach(label => {
    const tr = document.createElement('tr');
    let isTotal = false;
    let cells = '';
    dealerKeys.forEach(dealer => {
      const item = lineItemFor(dealer, deptName, label, sections);
      if (!item) { cells += '<td>—</td>'; return; }
      if (item.is_total) isTotal = true;
      const primary = lineItemPrimary(item);
      const group = lineItemGroup(item);
      const note = lineItemUnitsNote(item);
      const info = primary ? deltaInfo(label, primary, group, LOWER_IS_BETTER_SECTIONS.has(item.section)) : null;
      cells += `<td><span class="cell-main">${fmtValue(group, primary ? primary.real : null)}${note ? ` <span style="color:var(--muted);font-size:10px;">(${note})</span>` : ''}</span>` +
        (info ? `<span class="cell-sub ${info.tone}">${info.short}</span>` : '') + '</td>';
    });
    tr.innerHTML = `<td style="${isTotal ? 'font-weight:600;' : 'padding-left:18px;color:var(--text-secondary);'}">${escapeHtml(label)}</td>` + cells;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  scroll.appendChild(table);
  wrap.appendChild(scroll);
  return wrap;
}

// --- Carte « barres par concession » --------------------------------------
// One row per dealer, sorted high -> low, bar anchored at zero, a thin tick
// at the comparison value (budget or prior year), the group total as the
// card's headline figure instead of an oversized bar that flattened
// everyone else.
function renderChartCard(key, label, rows, detailOpts, opts) {
  const o = opts || {};
  const group = rows.__group;
  const cmpField = compareValueFieldForBasis();
  const card = document.createElement('div');
  card.className = 'chart-card';
  const head = document.createElement('div');
  head.className = 'card-head';
  const left = document.createElement('div');
  const anyCompare = rows.some(r => hasCompareData(r));
  left.innerHTML = `<p class="chart-title">${escapeHtml(o.title || label)}</p>` +
    `<div class="chart-meta">${o.meta ? escapeHtml(o.meta) + ' · ' : ''}Réel par concession${anyCompare ? ` · <span class="tick-key"></span> = ${compareLabel()}` : ''}</div>`;
  head.appendChild(left);

  if (state.showCombined && !o.hideGroup) {
    const combined = detailOpts ? combinedDeptMetricFor(detailOpts.deptName, key) : combinedKpiFor(key);
    if (combined && isNum(combined.real)) {
      const gl = document.createElement('div');
      gl.className = 'group-line';
      const info = deltaInfo(key, combined, group);
      const cov = coverageNote(combined);
      gl.innerHTML = `<div class="g-label">Groupe</div><div class="g-value">${fmtValue(group, combined.real)}</div>` +
        (info ? `<div class="delta-badge ${info.tone}">${info.text} vs ${compareLabel()}${cov ? `<br><span style="color:var(--muted)">(${cov})</span>` : ''}</div>` : '');
      head.appendChild(gl);
    }
  }
  card.appendChild(head);

  let metaKey = null;
  if (detailOpts) {
    metaKey = detailOpts.deptName + '::' + key;
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'detail-toggle-link';
    toggle.textContent = (expandedMetrics[metaKey] ? '▾ ' : '▸ ') + 'Voir le détail des postes';
    toggle.addEventListener('click', () => { expandedMetrics[metaKey] = !expandedMetrics[metaKey]; renderContent(); });
    card.appendChild(toggle);
  }

  const withData = rows.filter(r => isNum(r.real)).sort((a, b) => b.real - a.real);
  const noData = rows.filter(r => !isNum(r.real));
  if (!withData.length) {
    const nd = document.createElement('div');
    nd.className = 'no-data';
    nd.textContent = 'Aucune donnée pour la sélection actuelle.';
    card.appendChild(nd);
  } else {
    const vals = [];
    withData.forEach(r => { vals.push(r.real); if (hasCompareData(r)) vals.push(r[cmpField]); });
    let min = Math.min(0, ...vals), max = Math.max(0, ...vals);
    if (max === min) max = min + 1;
    const pos = v => ((v - min) / (max - min)) * 100;
    const zero = pos(0);

    const bh = document.createElement('div');
    bh.className = 'bar-head';
    bh.innerHTML = `<span>Concession</span><span>${anyCompare ? 'Réel vs ' + compareLabel() : 'Réel'}</span><span>Valeur</span><span>12 mois</span>`;
    card.appendChild(bh);

    withData.concat(noData).forEach(r => {
      const row = document.createElement('div');
      row.className = 'bar-row';
      const name = document.createElement('div');
      name.className = 'dealer-name';
      name.innerHTML = `<span class="swatch" style="background:${seriesColor(r.dealer)}"></span><span class="nm">${escapeHtml(dealerLabel(r.dealer))}</span>`;
      row.appendChild(name);

      const track = document.createElement('div');
      track.className = 'bar-track';
      if (!isNum(r.real)) {
        track.innerHTML = '<span class="no-data" style="font-size:11px;padding:0;">n/d pour cette période</span>';
      } else {
        const z = document.createElement('div');
        z.className = 'zero';
        z.style.left = zero + '%';
        track.appendChild(z);
        const fill = document.createElement('div');
        fill.className = 'bar-fill' + (r.real < 0 ? ' neg' : '');
        fill.style.background = seriesColor(r.dealer);
        const a = pos(Math.min(0, r.real)), b = pos(Math.max(0, r.real));
        fill.style.left = a + '%';
        fill.style.width = Math.max(0, b - a) + '%';
        track.appendChild(fill);
        if (hasCompareData(r)) {
          const t = document.createElement('div');
          t.className = 'target-tick';
          t.style.left = pos(r[cmpField]) + '%';
          track.appendChild(t);
        }
      }
      row.appendChild(track);

      const valueWrap = document.createElement('div');
      valueWrap.className = 'val-wrap';
      const info = deltaInfo(key, r, group);
      valueWrap.innerHTML = `<div class="bar-value">${fmtValue(group, r.real)}</div>` +
        (info ? `<div class="delta-badge ${info.tone}">${info.text}</div>` : '');
      const deptPct = deptPctLineText(r);
      if (deptPct) valueWrap.innerHTML += `<div class="dept-pct-line">${deptPct}</div>`;
      row.appendChild(valueWrap);

      const pts = historyFor(r.dealer, key, detailOpts);
      row.appendChild(renderSparkline(pts, seriesColor(r.dealer), group));

      attachTip(row, () => {
        if (!isNum(r.real)) return `<b>${escapeHtml(dealerLabel(r.dealer))}</b><br>Aucune donnée pour ${escapeHtml(periodLabel(state.refPeriod))} (${escapeHtml(periodModeLabel().toLowerCase())}).`;
        const pct = deltaPct(r);
        return `<b>${escapeHtml(dealerLabel(r.dealer))}</b> · ${escapeHtml(periodLabel(state.refPeriod))}<br>` + tipRows([
          ['Réel', fmtValue(group, r.real)],
          hasCompareData(r) ? [compareLabelLong(), fmtValue(group, r[cmpField])] : [compareLabelLong(), 'n/d'],
          info ? ['Écart', fmtSignedValue(group, info.delta) + (group !== 'percent' && isNum(pct) ? ' (' + fmtSignedPct(pct) + ')' : '')] : null,
          deptPct ? ['Part', deptPct] : null,
        ]);
      });
      card.appendChild(row);
    });

    const missing = withData.filter(r => !hasCompareData(r)).map(r => r.dealer);
    const notes = [];
    if (missing.length && missing.length < withData.length) notes.push(compareMissingText(missing));
    if (missing.length && missing.length === withData.length) notes.push(state.basis === 'budget' ? 'Aucune concession n\\'a de budget pour cet indicateur.' : 'Aucune année précédente disponible pour cet indicateur.');
    if (notes.length) {
      const foot = document.createElement('div');
      foot.className = 'card-foot';
      foot.textContent = notes.join(' ');
      card.appendChild(foot);
    }
  }

  if (detailOpts && metaKey && expandedMetrics[metaKey]) {
    card.appendChild(renderLineItemDetailTable(detailOpts.deptName, detailOpts.sections));
  }
  return card;
}

function buildRowsForKpi(key) {
  return orderedKeys(state.dealers).map(dealer => Object.assign({ dealer }, dealerKpi(dealer, key) || { real: null }));
}
function buildRowsForDept(deptName, metricKey) {
  return orderedKeys(state.dealers).map(dealer => Object.assign({ dealer }, dealerDeptMetric(dealer, deptName, metricKey) || { real: null }));
}

function renderChartsView(container) {
  const keys = collectKpiKeys(state.group);
  if (keys.size === 0) {
    container.innerHTML = '<div class="chart-card no-data">Aucun indicateur disponible pour cette catégorie / période.</div>';
    return;
  }
  keys.forEach((label, key) => {
    const rows = buildRowsForKpi(key);
    rows.__group = kpiFormat(key, state.group);
    container.appendChild(renderChartCard(key, label, rows));
  });
}

// --- Tableaux: une colonne par concession, valeur + écart dans la cellule --
function tableCell(key, kv, group, lowerIsBetter, extraHtml) {
  if (!kv || !isNum(kv.real)) return '<td><span class="cell-main" style="color:var(--muted)">—</span></td>';
  const info = deltaInfo(key, kv, group, lowerIsBetter);
  return `<td><span class="cell-main">${fmtValue(group, kv.real)}</span>` +
    `<span class="cell-sub ${info ? info.tone : 'neutral'}">${info ? info.short : '—'}</span>${extraHtml || ''}</td>`;
}
function tableHeaderHtml(firstLabel, dealerKeys) {
  return `<thead><tr><th>${firstLabel}</th>` + dealerKeys.map(k =>
    `<th class="${k === COMBINED_KEY ? 'col-group' : ''}"><span class="th-dealer">${k === COMBINED_KEY ? '' : `<span class="swatch" style="background:${seriesColor(k)}"></span>`}${escapeHtml(dealerLabel(k))}${k !== COMBINED_KEY && !STORE.dealers[k] ? ' (à venir)' : ''}</span></th>`
  ).join('') + '</tr></thead>';
}
function tableFootNote(card) {
  const foot = document.createElement('div');
  foot.className = 'card-foot';
  foot.textContent = `Chaque cellule : valeur réelle, puis l'écart en % vs ${compareLabel()} (en points pour les ratios). ` +
    (state.showCombined ? 'L\\'écart du groupe ne compte que les concessions qui ont un ' + (state.basis === 'budget' ? 'budget.' : 'historique de l\\'année précédente.') : '');
  card.appendChild(foot);
}
function displayDealerKeys() {
  const keys = orderedKeys(state.dealers);
  return (state.showCombined && keys.length > 0) ? [COMBINED_KEY].concat(keys) : keys;
}
function renderTableView(container) {
  const keys = collectKpiKeys(state.group);
  const card = document.createElement('div');
  card.className = 'chart-card';
  const dealerKeys = displayDealerKeys();
  const scroll = document.createElement('div');
  scroll.className = 'table-scroll';
  const table = document.createElement('table');
  table.className = 'kpi-table';
  table.innerHTML = tableHeaderHtml('Indicateur', dealerKeys);
  const tbody = document.createElement('tbody');
  keys.forEach((label, key) => {
    const fmtGroup = kpiFormat(key, state.group);
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${escapeHtml(label)}</td>` + dealerKeys.map(dealer => {
      const kv = dealer === COMBINED_KEY ? combinedKpiFor(key) : dealerKpi(dealer, key);
      return tableCell(key, kv, fmtGroup).replace('<td>', dealer === COMBINED_KEY ? '<td class="col-group" style="font-weight:600">' : '<td>');
    }).join('');
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  scroll.appendChild(table);
  card.appendChild(scroll);
  tableFootNote(card);
  container.appendChild(card);
}

function renderDepartmentChartsView(container) {
  if (!state.dept) {
    container.innerHTML = '<div class="chart-card no-data">Aucun département disponible pour cette période (essayez Mois courant ou Cumulatif annuel).</div>';
    return;
  }
  DEPARTMENT_METRICS.forEach(({ key, label, group }) => {
    const rows = buildRowsForDept(state.dept, key);
    if (rows.every(r => !isNum(r.real))) return;
    rows.__group = group;
    const sections = METRIC_LINE_ITEM_SECTIONS[key];
    const detailOpts = sections ? { deptName: state.dept, sections } : null;
    container.appendChild(renderChartCard(key, label, rows, detailOpts));
  });
}
function renderDepartmentTableView(container) {
  if (!state.dept) {
    container.innerHTML = '<div class="chart-card no-data">Aucun département disponible pour cette période.</div>';
    return;
  }
  const card = document.createElement('div');
  card.className = 'chart-card';
  const dealerKeys = displayDealerKeys();
  const scroll = document.createElement('div');
  scroll.className = 'table-scroll';
  const table = document.createElement('table');
  table.className = 'kpi-table';
  table.innerHTML = tableHeaderHtml('Indicateur', dealerKeys);
  const tbody = document.createElement('tbody');
  DEPARTMENT_METRICS.forEach(({ key, label, group }) => {
    const rows = buildRowsForDept(state.dept, key);
    if (rows.every(r => !isNum(r.real))) return;
    const sections = METRIC_LINE_ITEM_SECTIONS[key];
    const metaKey = state.dept + '::' + key;
    const expanded = !!(sections && expandedMetrics[metaKey]);
    const tr = document.createElement('tr');
    const toggleHtml = sections ? `<button type="button" class="detail-toggle" data-metric="${escapeHtml(metaKey)}">${expanded ? '▾' : '▸'}</button> ` : '';
    tr.innerHTML = `<td>${toggleHtml}${escapeHtml(label)}</td>` + dealerKeys.map(dealer => {
      const kv = dealer === COMBINED_KEY ? combinedDeptMetricFor(state.dept, key) : rows.find(r => r.dealer === dealer);
      const pct = deptPctLineText(kv);
      return tableCell(key, kv, group, undefined, pct ? `<span class="cell-sub neutral">${pct}</span>` : '')
        .replace('<td>', dealer === COMBINED_KEY ? '<td class="col-group" style="font-weight:600">' : '<td>');
    }).join('');
    tbody.appendChild(tr);
    if (expanded) {
      const detailTr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 1 + dealerKeys.length;
      td.style.cssText = 'padding:4px 8px 14px 24px;background:var(--page);position:static;';
      td.appendChild(renderLineItemDetailTable(state.dept, sections));
      detailTr.appendChild(td);
      tbody.appendChild(detailTr);
    }
  });
  table.appendChild(tbody);
  scroll.appendChild(table);
  card.appendChild(scroll);
  tableFootNote(card);
  container.appendChild(card);
  tbody.querySelectorAll('.detail-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const k = btn.getAttribute('data-metric');
      expandedMetrics[k] = !expandedMetrics[k];
      renderContent();
    });
  });
}

// --- Sommaire direction ---------------------------------------------------
// Landing page: the group's profit net as the one hero figure, a short list
// of facts computed from the data, six headline tiles, the profit net bars
// and a one-glance scorecard of every dealer.
const SUMMARY_TILES = [
  { key: 'pb_total', label: 'Profit brut total', group: 'profit' },
  { key: 'ventes_nettes', label: 'Ventes nettes', group: 'ebitda' },
  { key: 'depenses', label: 'Dépenses', group: 'revenue_expense' },
  { key: 'unites_neuf', label: 'Unités neuves', group: 'volume' },
  { key: 'unites_usage', label: 'Unités usagées', group: 'volume' },
  { key: 'ebt_pct_profit_brut', label: 'EBT en % du profit brut', group: 'ebitda' },
];
const SCORECARD_COLS = [
  { key: 'profit_net', label: 'Profit net', group: 'net' },
  { key: 'pb_total', label: 'Profit brut', group: 'profit' },
  { key: 'ventes_nettes', label: 'Ventes nettes', group: 'ebitda', compact: true },
  { key: 'unites_neuf', label: 'Unités neuves', group: 'volume' },
  { key: 'unites_usage', label: 'Unités usagées', group: 'volume' },
  { key: 'ebt_pct_profit_brut', label: 'EBT % profit brut', group: 'ebitda' },
];
function fmtGroupFor(key, navGroup) { return kpiFormat(key, navGroup === 'volume' ? 'volume' : 'money'); }

function buildHighlights(key) {
  const items = [];
  const group = fmtGroupFor(key, 'net');
  const rows = dealersWithData().map(d => ({ dealer: d, kv: dealerKpi(d, key) })).filter(x => x.kv && isNum(x.kv.real));
  if (!rows.length) return items;
  const combined = combinedKpiFor(key);
  const top = rows.slice().sort((a, b) => b.kv.real - a.kv.real)[0];
  if (combined && combined.real > 0 && top.kv.real > 0 && rows.length > 1) {
    items.push({ tone: 'info', icon: '1', html: `<b>${escapeHtml(dealerLabel(top.dealer))}</b> est le plus gros contributeur : ${fmtValue(group, top.kv.real)}, soit ${Math.round(top.kv.real / combined.real * 100)}${NBSP}% du profit net du groupe.` });
  }
  const cmp = rows.filter(x => hasCompareData(x.kv));
  if (cmp.length) {
    const byDelta = cmp.slice().sort((a, b) => b.kv[deltaFieldForBasis()] - a.kv[deltaFieldForBasis()]);
    const best = byDelta[0], worst = byDelta[byDelta.length - 1];
    const line = (x) => {
      const d = x.kv[deltaFieldForBasis()], pct = deltaPct(x.kv);
      return `<b>${escapeHtml(dealerLabel(x.dealer))}</b> : ${fmtSignedValue(group, d)}${isNum(pct) ? ' (' + fmtSignedPct(pct) + ')' : ''} vs ${state.basis === 'budget' ? 'budget' : 'l\\'année précédente'}`;
    };
    if (best.kv[deltaFieldForBasis()] > 0) items.push({ tone: 'good', icon: '▲', html: 'Meilleur écart — ' + line(best) + '.' });
    if (worst !== best && worst.kv[deltaFieldForBasis()] < 0) items.push({ tone: 'critical', icon: '▼', html: 'Plus faible écart — ' + line(worst) + '.' });
    else if (cmp.length === 1 && best.kv[deltaFieldForBasis()] < 0) items.push({ tone: 'critical', icon: '▼', html: line(best) + '.' });
    const above = cmp.filter(x => x.kv[deltaFieldForBasis()] > 0).length;
    if (cmp.length > 1) items.push({ tone: 'info', icon: '#', html: `${above} concession${above > 1 ? 's' : ''} sur ${cmp.length} au-dessus ${state.basis === 'budget' ? 'du budget' : 'de l\\'année précédente'}.` });
  }
  rows.filter(x => x.kv.real < 0).forEach(x => {
    items.push({ tone: 'critical', icon: '!', html: `<b>${escapeHtml(dealerLabel(x.dealer))}</b> est en perte : ${fmtValue(group, x.kv.real)}.` });
  });
  const missing = rows.filter(x => !hasCompareData(x.kv)).map(x => x.dealer);
  if (missing.length) {
    items.push({ tone: 'info', icon: 'i', html: `<span class="muted">${escapeHtml(dealerListText(missing))} : pas ${state.basis === 'budget' ? 'de budget' : 'd\\'année précédente'} dans ${missing.length > 1 ? 'leurs fichiers' : 'son fichier'}, donc hors des écarts.</span>` });
  }
  const present = new Set(dealersWithData());
  const absent = orderedKeys(state.dealers).filter(d => STORE.dealers[d] && !present.has(d));
  if (absent.length) {
    items.push({ tone: 'info', icon: 'i', html: `<span class="muted">Aucune donnée pour ${escapeHtml(periodLabel(state.refPeriod))} (${escapeHtml(periodModeLabel().toLowerCase())}) : ${escapeHtml(dealerListText(absent))}.</span>` });
  }
  return items;
}

function renderSummaryView(container) {
  if (!dealersWithData().length) {
    container.innerHTML = '<div class="chart-card no-data">Aucune donnée pour cette sélection. Choisissez un autre mois ou cochez au moins une concession.</div>';
    return;
  }
  // Rangée 1 : héros + faits saillants
  const top = document.createElement('div');
  top.className = 'summary-top';
  const hero = document.createElement('div');
  hero.className = 'chart-card';
  const heroKv = combinedKpiFor('profit_net');
  const heroGroup = fmtGroupFor('profit_net', 'net');
  const heroInfo = heroKv ? deltaInfo('profit_net', heroKv, heroGroup) : null;
  const heroCov = heroKv ? heroKv.coverage[compareValueFieldForBasis()] : null;
  hero.innerHTML = `<div class="hero-label">Profit net — groupe (${heroKv ? heroKv.dealers.length : 0} concession${heroKv && heroKv.dealers.length > 1 ? 's' : ''})</div>` +
    `<div class="hero-value">${heroKv ? fmtValue(heroGroup, heroKv.real) : '—'}</div>` +
    `<div class="hero-delta">` + (heroInfo
      ? `<span class="delta-badge ${heroInfo.tone}" style="font-size:13px">${heroInfo.text} vs ${compareLabel()}</span>` +
        (heroCov && heroCov.missing.length ? `<span class="cov">Écart calculé sur ${escapeHtml(dealerListText(heroCov.included))} — les autres n'ont pas ${state.basis === 'budget' ? 'de budget' : 'd\\'année précédente'}.</span>` : '')
      : `<span class="cov">Pas de ${state.basis === 'budget' ? 'budget' : 'donnée de l\\'année précédente'} pour comparer.</span>`) + `</div>`;
  const trendLabel = document.createElement('div');
  trendLabel.className = 'chart-meta';
  trendLabel.style.marginTop = '14px';
  trendLabel.textContent = (state.period === 'ytd' ? 'Cumulatif annuel' : state.period === 'quarter' ? 'Trimestre' : 'Évolution mensuelle') + ' du groupe — mois où toutes les concessions cochées ont des données';
  hero.appendChild(trendLabel);
  hero.appendChild(renderTrendChart(historyForCombined('profit_net'), heroGroup));
  top.appendChild(hero);

  const hl = document.createElement('div');
  hl.className = 'chart-card';
  hl.innerHTML = '<p class="chart-title">Faits saillants</p><div class="chart-meta">Profit net · ' + escapeHtml(periodLabel(state.refPeriod)) + ' · vs ' + compareLabel() + '</div>';
  const ul = document.createElement('ul');
  ul.className = 'highlights';
  const items = buildHighlights('profit_net');
  if (!items.length) ul.innerHTML = '<li class="muted">Rien à signaler pour cette sélection.</li>';
  items.forEach(it => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="hl-icon ${it.tone}">${it.icon}</span><span>${it.html}</span>`;
    ul.appendChild(li);
  });
  hl.appendChild(ul);
  top.appendChild(hl);
  container.appendChild(top);

  // Rangée 2 : tuiles
  const tiles = document.createElement('div');
  tiles.className = 'stat-tiles';
  SUMMARY_TILES.forEach(t => {
    const kv = combinedKpiFor(t.key);
    const group = fmtGroupFor(t.key, t.group);
    const tile = document.createElement('button');
    tile.type = 'button';
    tile.className = 'stat-tile';
    tile.title = 'Voir le détail par concession';
    const info = kv ? deltaInfo(t.key, kv, group) : null;
    const cov = kv ? coverageNote(kv) : '';
    tile.innerHTML = `<span class="t-label">${escapeHtml(t.label)}</span>` +
      `<span class="t-row"><span class="t-value">${kv ? fmtValueCompact(group, kv.real) : '—'}</span></span>` +
      (info ? `<span class="delta-badge ${info.tone}">${info.text}</span><span class="cov">vs ${compareLabel()}${cov ? ' · ' + cov : ''}</span>`
            : `<span class="delta-badge neutral">n/d vs ${compareLabel()}</span>`);
    tile.querySelector('.t-row').appendChild(renderSparkline(historyForCombined(t.key), seriesColor(COMBINED_KEY), group, { w: 72, h: 26 }));
    tile.addEventListener('click', () => { state.group = t.group; setScope('overview'); });
    tiles.appendChild(tile);
  });
  container.appendChild(tiles);

  // Rangée 3 : profit net par concession
  const rows = buildRowsForKpi('profit_net');
  rows.__group = heroGroup;
  container.appendChild(renderChartCard('profit_net', 'Profit net par concession', rows, null, { hideGroup: true }));

  // Rangée 4 : tableau de bord des concessions
  const card = document.createElement('div');
  card.className = 'chart-card';
  card.innerHTML = `<p class="chart-title">Vue d'ensemble par concession</p><div class="chart-meta">Classé par profit net · sous chaque valeur : écart vs ${compareLabel()}</div>`;
  const scroll = document.createElement('div');
  scroll.className = 'table-scroll';
  scroll.style.marginTop = '8px';
  const table = document.createElement('table');
  table.className = 'kpi-table scorecard';
  table.innerHTML = '<thead><tr><th>Concession</th>' + SCORECARD_COLS.map(c => `<th>${escapeHtml(c.label)}</th>`).join('') + '</tr></thead>';
  const tbody = document.createElement('tbody');
  const dealers = orderedKeys(state.dealers).filter(d => STORE.dealers[d]);
  const pn = d => { const kv = dealerKpi(d, 'profit_net'); return kv && isNum(kv.real) ? kv.real : -Infinity; };
  dealers.sort((a, b) => pn(b) - pn(a));
  const cell = (key, kv, c) => {
    const group = fmtGroupFor(key, c.group);
    if (!kv || !isNum(kv.real)) return '<td><span class="cell-main" style="color:var(--muted)">—</span></td>';
    const info = deltaInfo(key, kv, group);
    return `<td><span class="cell-main">${c.compact ? fmtValueCompact(group, kv.real) : fmtValue(group, kv.real)}</span>` +
      `<span class="cell-sub ${info ? info.tone : 'neutral'}">${info ? info.short : '—'}</span></td>`;
  };
  dealers.forEach(d => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><span class="dealer-name"><span class="swatch" style="background:${seriesColor(d)}"></span><span class="nm">${escapeHtml(dealerLabel(d))}</span></span></td>` +
      SCORECARD_COLS.map(c => cell(c.key, dealerKpi(d, c.key), c)).join('');
    tbody.appendChild(tr);
  });
  const gtr = document.createElement('tr');
  gtr.className = 'group-row';
  gtr.innerHTML = '<td>Groupe</td>' + SCORECARD_COLS.map(c => cell(c.key, combinedKpiFor(c.key), c)).join('');
  tbody.appendChild(gtr);
  table.appendChild(tbody);
  scroll.appendChild(table);
  card.appendChild(scroll);
  const foot = document.createElement('div');
  foot.className = 'card-foot';
  foot.textContent = 'Écarts en % (en points pour l\\'EBT % du profit brut). La rangée Groupe compare seulement les concessions qui ont un ' +
    (state.basis === 'budget' ? 'budget' : 'historique de l\\'année précédente') + ' pour chaque indicateur.';
  card.appendChild(foot);
  container.appendChild(card);
}

// --- En-tête de page ------------------------------------------------------
function renderPageHead() {
  const el = document.getElementById('pageHead');
  if (!el) return;
  let title = '';
  if (state.scope === 'summary') title = 'Sommaire';
  else if (state.scope === 'overview') title = GROUP_LABELS[state.group] || 'Indicateurs';
  else if (state.scope === 'departments') title = state.dept ? 'Département — ' + state.dept : 'Départements';
  else title = 'Déposer un fichier';
  if (state.scope === 'upload') { el.innerHTML = `<h2 class="page-title">${escapeHtml(title)}</h2>`; return; }
  const withData = dealersWithData().length;
  const selected = orderedKeys(state.dealers).length;
  const parts = [escapeHtml(periodLabel(state.refPeriod)), escapeHtml(periodModeLabel()),
    'comparé ' + (state.basis === 'budget' ? 'au budget' : 'à l\\'année précédente'),
    `${withData} concession${withData > 1 ? 's' : ''} sur ${selected} avec données`];
  el.innerHTML = `<h2 class="page-title">${escapeHtml(title)}</h2><div class="page-context">${parts.join('<span class="sep">·</span>')}</div>`;
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
  hideTip();
  renderPageHead();
  const container = document.getElementById('content');
  container.innerHTML = '';
  if (state.scope === 'upload') { renderUploadView(container); return; }
  if (!orderedKeys(state.dealers).length) {
    container.innerHTML = '<div class="chart-card no-data">Cochez au moins une concession dans le filtre « Concessions ».</div>';
    return;
  }
  if (state.scope === 'summary') { renderSummaryView(container); return; }
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
  const apply = syncThemeLabel;
  btn.addEventListener('click', () => {
    document.documentElement.setAttribute('data-theme', isDark() ? 'light' : 'dark');
    apply();
    renderDealerFilter();
    renderAll();
  });
  apply();
}

function initDashboard() {
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
