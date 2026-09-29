// --- Opérations fixes (après-vente) ------------------------------------------
// Lit sections.<mois|cumul>.apres_vente (src/apres_vente.py) : BT par type,
// main-d'œuvre, pièces, heures, atelier. Ratios du Groupe recalculés à partir
// des sommes ; heures : seulement les concessions qui en ont.
const FO_TYPES = [['client', 'Client (détail)'], ['garantie', 'Garantie'], ['entretien', 'Entretien BMW'], ['interne', 'Interne'], ['esthetique', 'Esthétique']];
// Types qui portent des pièces ; « entretien » : BMW seulement (état BMW Canada, pages 8 et 9).
const FO_PC_TYPES = ['client', 'garantie', 'entretien', 'interne'];
const FO_DETAIL = { mobile: 'dont service mobile', inspection: 'dont inspection des véhicules neufs' };
// STM : le compte 460D (service mobile) n’est utilisé qu’à partir de l’état d’août 2026 (cumul retraité).
const FO_MEAS = [['bt', 'bt'], ['mo_ventes', 'mo_v'], ['mo_pb', 'mo_pb'], ['pc_ventes', 'pc_v'], ['pc_pb', 'pc_pb'], ['heures', 'h']];
const FO_METRICS = [
  { key: 'bt', label: 'Nombre de BT', fmt: 'volume' },
  { key: 'mo_bt', label: 'Main-d’œuvre par BT', fmt: 'money' },
  { key: 'pc_bt', label: 'Pièces par BT', fmt: 'money' },
  { key: 'tot_bt', label: 'Total par BT (M-O + pièces)', fmt: 'money', strong: true },
  { key: 'pb_bt', label: 'Profit brut par BT', fmt: 'money' },
  { key: 'h_bt', label: 'Heures vendues par BT', fmt: 'dec2' },
  { key: 'elr', label: 'Taux effectif (M-O ÷ heure vendue)', fmt: 'money' },
  { key: 'marge_mo', label: 'Marge brute M-O', fmt: 'percent' },
  { key: 'mo_v', label: 'Ventes M-O', fmt: 'money' },
  { key: 'pc_v', label: 'Ventes de pièces sur ces BT', fmt: 'money' },
];
const FO_VIEWS = [['bt', 'Bons de travail'], ['atelier', 'Atelier et heures'], ['pieces', 'Pièces'], ['tendances', 'Tendances']];
const FO_PC_CHANNELS = [['client', 'BT client'], ['garantie', 'BT garantie'], ['entretien', 'BT entretien BMW'], ['interne', 'BT interne'], ['carrosserie', 'Carrosserie'],
  ['comptoir', 'Comptoir (détail)'], ['accessoires', 'Accessoires'], ['gros', 'Gros'], ['pneus', 'Pneus'], ['huile', 'Huiles et graisse'], ['divers', 'Divers']];

function foField(kv, f) { return (kv && typeof kv === 'object' && isNum(kv[f])) ? kv[f] : null; }
function foDiv(a, b) { return (isNum(a) && isNum(b) && b !== 0) ? a / b : null; }
// Montants servant aux ratios « par BT » : seulement si le type a des BT
// (ex. esthétique VW : ventes sans nombre de BT, exclues des ratios).
const FO_BT_BASED = ['mo_v', 'mo_pb', 'pc_v', 'pc_pb'];
function foSetBtBase(t) { FO_BT_BASED.forEach(m => { t[m + '_b'] = t.bt ? t[m] : null; }); }
function foBtB(t, m) { return (m + '_b') in t ? t[m + '_b'] : (t.bt ? t[m] : null); }
function foFlat(av, f) {
  if (!av) return null;
  const out = { types: {}, detail: {}, pieces: {}, service: {}, carrosserie: {}, atelier: {} };
  ['types', 'detail'].forEach(g => Object.entries(av[g] || {}).forEach(([k, m]) => {
    const t = {};
    FO_MEAS.forEach(([a, b]) => { t[b] = foField(m[a], f); });
    if (!t.h) t.h = null; // heures à 0 : donnée absente
    foSetBtBase(t);
    out[g][k] = t;
  }));
  ['pieces', 'service', 'carrosserie'].forEach(g => Object.entries(av[g] || {}).forEach(([k, m]) => {
    out[g][k] = { v: foField(m.ventes, f), pb: foField(m.pb, f), bt: foField(m.bt, f) };
  }));
  if (f === 'real') out.atelier = Object.assign({}, av.atelier || {});
  const has = Object.values(out.types).some(t => Object.values(t).some(v => v));
  return has ? out : null;
}
function foAv(dealer, period, mode) {
  return STORE.dealers[dealer]?.periods?.[period]?.sections?.[mode]?.apres_vente || null;
}
function foHasNativeAp(av) {
  return !!av && Object.values(av.types || {}).some(t => foField(t.bt, 'prior_year') || foField(t.mo_ventes, 'prior_year'));
}
// base : real | budget | prior_year. L'an passé vient des colonnes du Réalisé
// quand il les a, sinon du fichier du même mois de l'an passé.
function foGet(dealer, period, mode, base) {
  if (!period) return null;
  const av = foAv(dealer, period, mode);
  if (base === 'real') return foFlat(av, 'real');
  if (base === 'budget') {
    const f = foFlat(av, 'budget');
    return f && Object.values(f.types).some(t => t.bt || t.mo_v) ? f : null;
  }
  const prev = foFlat(foAv(dealer, priorYearPeriodKey(period), mode), 'real');
  if (foHasNativeAp(av)) {
    const f = foFlat(av, 'prior_year');
    if (f) {
      ['types', 'detail'].forEach(g => Object.entries(f[g]).forEach(([k, t]) => { t.h = prev && prev[g][k] ? prev[g][k].h : null; }));
      f.atelier = prev ? prev.atelier : {};
    }
    return f;
  }
  return prev;
}
function foSum(flats) {
  flats = flats.filter(Boolean);
  if (!flats.length) return null;
  const out = { types: {}, detail: {}, pieces: {}, service: {}, carrosserie: {}, atelier: {} };
  ['types', 'detail'].forEach(g => {
    const keys = new Set(); flats.forEach(f => Object.keys(f[g]).forEach(k => keys.add(k)));
    keys.forEach(k => {
      const acc = { h_bt_base: 0, h_mo_base: 0 };
      flats.forEach(f => {
        const t = f[g][k]; if (!t) return;
        FO_MEAS.forEach(([, m]) => { if (isNum(t[m])) acc[m] = (acc[m] || 0) + t[m]; });
        FO_BT_BASED.forEach(m => { const v = foBtB(t, m); if (isNum(v)) acc[m + '_b'] = (acc[m + '_b'] || 0) + v; });
        if (t.h) { acc.h_bt_base += t.bt || 0; acc.h_mo_base += t.mo_v || 0; }
      });
      out[g][k] = acc;
    });
  });
  ['pieces', 'service', 'carrosserie'].forEach(g => {
    const keys = new Set(); flats.forEach(f => Object.keys(f[g]).forEach(k => keys.add(k)));
    keys.forEach(k => {
      const acc = {};
      flats.forEach(f => Object.entries(f[g][k] || {}).forEach(([m, v]) => { if (isNum(v)) acc[m] = (acc[m] || 0) + v; }));
      out[g][k] = acc;
    });
  });
  ['heures_disponibles', 'heures_pointees', 'heures_vendues'].forEach(k => {
    const vals = flats.filter(f => f.atelier && f.atelier.heures_disponibles).map(f => f.atelier[k]).filter(isNum);
    if (vals.length) out.atelier[k] = vals.reduce((a, b) => a + b, 0);
  });
  let techs = 0, tn = 0;
  flats.forEach(f => { const t = f.atelier && f.atelier.heures_disponibles && f.atelier.techniciens ? f.atelier.techniciens.mecanique : null; if (isNum(t)) { techs += t; tn++; } });
  if (tn) out.atelier.techniciens = { mecanique: techs };
  return out;
}
function foTypeMetrics(t) {
  if (!t) return {};
  const bt = t.bt, mo = t.mo_v, pc = t.pc_v;
  const tot = (isNum(mo) || isNum(pc)) ? (mo || 0) + (pc || 0) : null;
  const pb = (isNum(t.mo_pb) || isNum(t.pc_pb)) ? (t.mo_pb || 0) + (t.pc_pb || 0) : null;
  const hb = isNum(t.h_bt_base) ? t.h_bt_base : bt;
  const hm = isNum(t.h_mo_base) ? t.h_mo_base : mo;
  const mob = foBtB(t, 'mo_v'), pcb = foBtB(t, 'pc_v'), mopbb = foBtB(t, 'mo_pb'), pcpbb = foBtB(t, 'pc_pb');
  const totb = (isNum(mob) || isNum(pcb)) ? (mob || 0) + (pcb || 0) : null;
  const pbb = (isNum(mopbb) || isNum(pcpbb)) ? (mopbb || 0) + (pcpbb || 0) : null;
  return {
    bt, mo_v: mo, pc_v: pc, tot_v: tot, pb, h: t.h,
    mo_bt: foDiv(mob, bt), pc_bt: foDiv(pcb, bt), tot_bt: foDiv(totb, bt), pb_bt: foDiv(pbb, bt),
    h_bt: t.h ? foDiv(t.h, hb) : null, elr: t.h ? foDiv(hm, t.h) : null,
    marge_mo: foDiv(t.mo_pb, mo), marge_pc: foDiv(t.pc_pb, pc), pc_mo: foDiv(pc, mo),
  };
}
function foAllTypes(f) {
  if (!f) return null;
  const acc = { h_bt_base: 0, h_mo_base: 0 };
  let hasH = false;
  Object.values(f.types).forEach(t => {
    FO_MEAS.forEach(([, m]) => { if (isNum(t[m])) acc[m] = (acc[m] || 0) + t[m]; });
    FO_BT_BASED.forEach(m => { const v = foBtB(t, m); if (isNum(v)) acc[m + '_b'] = (acc[m + '_b'] || 0) + v; });
    if (t.h) { hasH = true; acc.h_bt_base += isNum(t.h_bt_base) ? t.h_bt_base : (t.bt || 0); acc.h_mo_base += isNum(t.h_mo_base) ? t.h_mo_base : (t.mo_v || 0); }
  });
  if (!hasH) { acc.h = null; }
  return acc;
}
function foAtelier(f) {
  const a = (f && f.atelier) || {};
  // techniciens : seulement avec les heures de l'atelier (ceux de l'état GM ne sont pas fiables)
  const techs = (a.techniciens && a.heures_disponibles) ? a.techniciens.mecanique : null;
  return {
    disp: a.heures_disponibles, pointees: a.heures_pointees, vendues: a.heures_vendues,
    productivite: foDiv(a.heures_pointees, a.heures_disponibles), efficacite: foDiv(a.heures_vendues, a.heures_pointees),
    rendement: foDiv(a.heures_vendues, a.heures_disponibles),
    techs: techs, h_tech: (isNum(techs) && techs >= 2) ? foDiv(a.heures_vendues, techs) : null,
  };
}
function foBasis() { return state.basis === 'budget' ? 'budget' : 'prior_year'; }
function foMode() { return state.period === 'ytd' ? 'ytd' : 'month'; }
// Pour chaque colonne : (réel, base de comparaison), le Groupe à périmètre comparable.
function foColumns(pick) {
  const P = state.refPeriod, mode = foMode(), basis = foBasis();
  const cols = [];
  const dealers = orderedKeys(state.dealers);
  const per = {};
  dealers.forEach(d => { per[d] = { real: foGet(d, P, mode, 'real'), base: foGet(d, P, mode, basis) }; });
  displayDealerKeys().forEach(k => {
    if (k === COMBINED_KEY) {
      const withData = dealers.filter(d => per[d].real);
      const realAll = foSum(withData.map(d => per[d].real));
      const cmp = withData.filter(d => per[d].base && pick(per[d].base) !== undefined);
      cols.push({ key: k, real: realAll, cmpReal: foSum(cmp.map(d => per[d].real)), cmpBase: foSum(cmp.map(d => per[d].base)),
        members: withData.filter(d => per[d].base).map(d => per[d]) });
    } else {
      cols.push({ key: k, real: per[k] ? per[k].real : null, cmpReal: per[k] ? per[k].real : null, cmpBase: per[k] ? per[k].base : null });
    }
  });
  return cols;
}
function foHasHours(f, typ) {
  if (!f) return false;
  if (typ === 'atelier') return !!(f.atelier && f.atelier.heures_disponibles);
  if (typ === 'all') return Object.values(f.types).some(t => t.h);
  return !!(f.types[typ] && f.types[typ].h);
}
function foFmt(fmt, v) {
  if (!isNum(v)) return '—';
  if (fmt === 'dec2') return v.toLocaleString('fr-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (fmt === 'dec1') return fmtDec1(v);
  return fmtValue(fmt, v);
}
function foAxis(fmt, v) {
  if (fmt === 'money') return Math.round(v).toLocaleString('fr-CA') + NBSP + '$';
  if (fmt === 'percent') return Math.round(v * 100) + NBSP + '%';
  if (fmt === 'dec2' || fmt === 'dec1') return v.toLocaleString('fr-CA', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  return Math.round(v).toLocaleString('fr-CA');
}
function foCell(fmt, r, cr, cb, extra) {
  if (!isNum(r)) return '<td><span class="cell-main" style="color:var(--muted)">—</span></td>';
  let sub = '<span class="cell-sub neutral">—</span>';
  if (isNum(cr) && isNum(cb) && !(state.basis === 'budget' && cb === 0)) {
    const d = cr - cb;
    const tone = Math.abs(d) < 1e-9 ? 'neutral' : (d > 0 ? 'good' : 'critical');
    const txt = fmt === 'percent' ? fmtSignedPts(d) : (cb ? fmtSignedPct(d / Math.abs(cb) * 100) : '');
    sub = `<span class="cell-sub ${tone}">${txt || '—'}</span>`;
  }
  return `<td><span class="cell-main">${foFmt(fmt, r)}</span>${sub}${extra || ''}</td>`;
}
function foTable(firstLabel, rows, cols) {
  // rows : [{label, fmt, get(flat) -> valeur, sec?, sub?}]
  const table = document.createElement('table');
  table.className = 'kpi-table';
  table.innerHTML = tableHeaderHtml(firstLabel, cols.map(c => c.key));
  const tb = document.createElement('tbody');
  rows.forEach(row => {
    const tr = document.createElement('tr');
    if (row.sec) {
      tr.innerHTML = `<td colspan="${cols.length + 1}" style="font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600;padding-top:14px">${escapeHtml(row.sec)}</td>`;
      tb.appendChild(tr); return;
    }
    if (row.strong) tr.className = 'group-row';
    const lab = row.sub ? `<span style="padding-left:14px;color:var(--text-secondary)">${escapeHtml(row.label)}</span>` : escapeHtml(row.label);
    tr.innerHTML = `<td>${lab}</td>` + cols.map(c => {
      const r = c.real ? row.get(c.real) : null;
      let cr = c.cmpReal ? row.get(c.cmpReal) : null;
      let cb = c.cmpBase ? row.get(c.cmpBase) : null;
      if (c.members && row.htyp) {
        // heures : Groupe comparé seulement sur les concessions qui ont les heures les deux années
        const m = c.members.filter(x => foHasHours(x.real, row.htyp) && foHasHours(x.base, row.htyp));
        cr = m.length ? row.get(foSum(m.map(x => x.real))) : null;
        cb = m.length ? row.get(foSum(m.map(x => x.base))) : null;
      }
      return foCell(row.fmt, r, cr, cb).replace('<td>', c.key === COMBINED_KEY ? '<td class="col-group" style="font-weight:600">' : '<td>');
    }).join('');
    tb.appendChild(tr);
  });
  table.appendChild(tb);
  const scroll = document.createElement('div');
  scroll.className = 'table-scroll';
  scroll.appendChild(table);
  return scroll;
}
function foCard(title, meta, body, foot) {
  const card = document.createElement('div');
  card.className = 'chart-card';
  card.innerHTML = `<p class="chart-title">${escapeHtml(title)}</p>` + (meta ? `<div class="chart-meta">${meta}</div>` : '');
  card.appendChild(body);
  if (foot) { const f = document.createElement('div'); f.className = 'card-foot'; f.innerHTML = foot; card.appendChild(f); }
  return card;
}
function foFootBasis() {
  return `Chaque cellule : valeur, puis l’écart vs ${compareLabel()} (en points pour les marges). Groupe : ratios recalculés à partir des sommes ; ` +
    `l’écart du Groupe ne compte que les concessions qui ont ${state.basis === 'budget' ? 'un budget' : 'l’année précédente'} pour la ligne.`;
}
function foNoHoursNote() {
  // Mention des heures manquantes retirée (demande du 29 septembre 2026).
  return '';
}

function renderFoBtView(container) {
  // Vue d'ensemble
  const colsAll = foColumns(f => foAllTypes(f).bt);
  const allRows = FO_METRICS.map(m => ({ label: m.label, fmt: m.fmt, strong: m.strong, htyp: ['h_bt', 'elr'].includes(m.key) ? 'all' : null, get: f => foTypeMetrics(foAllTypes(f))[m.key] }));
  container.appendChild(foCard('Tous les bons de travail (mécanique)',
    'Client + garantie + entretien BMW + interne + esthétique · ' + escapeHtml(periodLabel(state.refPeriod)) + ' · ' + escapeHtml(periodModeLabel()),
    foTable('Indicateur', allRows, colsAll), foFootBasis() + (foNoHoursNote() ? '<br>' + foNoHoursNote() : '')));
  FO_TYPES.forEach(([typ, lab]) => {
    const cols = foColumns(f => (f.types[typ] || {}).bt);
    if (!cols.some(c => c.real && c.real.types[typ] && (c.real.types[typ].bt || c.real.types[typ].mo_v))) return;
    const rows = FO_METRICS.map(m => ({ label: m.label, fmt: m.fmt, strong: m.strong, htyp: ['h_bt', 'elr'].includes(m.key) ? typ : null, get: f => foTypeMetrics(f.types[typ])[m.key] }));
    Object.entries(FO_DETAIL).forEach(([dk, dl]) => {
      if (!cols.some(c => c.real && c.real.detail[dk] && c.real.detail[dk].bt)) return;
      if ((dk === 'mobile' && typ !== 'client') || (dk === 'inspection' && typ !== 'interne')) return;
      rows.push({ sec: dl.replace('dont ', '') + ' (inclus ci-dessus)' });
      rows.push({ label: 'Nombre de BT', fmt: 'volume', sub: true, get: f => foTypeMetrics(f.detail[dk]).bt });
      rows.push({ label: 'Main-d’œuvre par BT', fmt: 'money', sub: true, get: f => foTypeMetrics(f.detail[dk]).mo_bt });
    });
    const typeNote = typ === 'client' ? 'Client : BT payés par le client (atelier, service rapide, contrats et entretien prépayé ; service mobile de STM inclus).'
      : typ === 'interne' ? 'Interne : travaux facturés aux autres départements (reconditionnement des usagés, préparation des neufs ; inspection des véhicules neufs incluse à l’état GM).'
      : typ === 'garantie' ? 'Garantie : travaux remboursés par le constructeur (BMW : garantie seulement, l’entretien payé par BMW est à part).'
      : typ === 'entretien' ? 'Entretien BMW : entretien payé par BMW (BMW Service Inclus), état BMW Canada pages 8 et 9.'
      : 'Esthétique : BT d’esthétique (VW : Réalisé ; BMW : programme SPA de l’état BMW Canada).';
    container.appendChild(foCard(lab, escapeHtml(typeNote), foTable('Indicateur', rows, cols), ''));
  });
}
function renderFoAtelierView(container) {
  const cols = foColumns(f => (f.atelier || {}).heures_disponibles);
  const A = k => f => foAtelier(f)[k];
  const rows = [
    { sec: 'Heures de l’atelier mécanique' },
    { label: 'Heures disponibles (techniciens présents)', htyp: 'atelier', fmt: 'volume', get: A('disp') },
    { label: 'Heures pointées sur les BT', htyp: 'atelier', fmt: 'volume', get: A('pointees') },
    { label: 'Heures vendues (facturées)', htyp: 'atelier', fmt: 'volume', get: A('vendues'), strong: true },
    { label: 'Productivité (pointées ÷ disponibles)', htyp: 'atelier', fmt: 'percent', get: A('productivite') },
    { label: 'Efficacité (vendues ÷ pointées)', htyp: 'atelier', fmt: 'percent', get: A('efficacite') },
    { label: 'Rendement (vendues ÷ disponibles)', htyp: 'atelier', fmt: 'percent', get: A('rendement') },
    { label: 'Techniciens (mécanique)', htyp: 'atelier', fmt: 'dec1', get: A('techs') },
    { label: 'Heures vendues par technicien', htyp: 'atelier', fmt: 'volume', get: A('h_tech') },
    { sec: 'Heures vendues et taux effectif par type' },
  ];
  FO_TYPES.filter(([t]) => FO_PC_TYPES.includes(t)).forEach(([typ, lab]) => {
    rows.push({ label: 'Heures vendues — ' + lab.toLowerCase(), fmt: 'volume', htyp: typ, get: f => (f.types[typ] || {}).h || null });
    rows.push({ label: 'Heures par BT — ' + lab.toLowerCase(), fmt: 'dec2', sub: true, htyp: typ, get: f => foTypeMetrics(f.types[typ]).h_bt });
    rows.push({ label: 'Taux effectif — ' + lab.toLowerCase(), fmt: 'money', sub: true, htyp: typ, get: f => foTypeMetrics(f.types[typ]).elr });
  });
  rows.push({ sec: 'Déclaré au constructeur (état BMW Canada, page 10)' });
  rows.push({ label: 'Taux de main-d’œuvre en vigueur ($ l’heure, taux effectif déclaré)', fmt: 'dec2', get: f => (f.atelier || {}).taux_effectif_declare || null });
  rows.push({ label: 'Taux affiché client', fmt: 'money', sub: true, get: f => ((f.atelier || {}).taux_affiche || {}).client || null });
  container.appendChild(foCard('Atelier et heures vendues', escapeHtml(periodLabel(state.refPeriod)) + ' · ' + escapeHtml(periodModeLabel()),
    foTable('Indicateur', rows, cols),
    'Sources : état Volkswagen Canada (Page 6), état Hyundai Canada (Page 6) ; taux effectif déclaré et taux affichés : état BMW Canada (page 10) et états GM (Page 4). ' + (foNoHoursNote() || '') +
    ' Taux effectif = ventes de main-d’œuvre ÷ heures vendues.'));
}
function renderFoPiecesView(container) {
  const cols = foColumns(f => (f.pieces.total || {}).v);
  const rows = [{ sec: 'Ventes par canal' }];
  const chanV = ch => f => (FO_PC_TYPES.includes(ch) ? (f.types[ch] || {}).pc_v : (f.pieces[ch] || {}).v) || null;
  const chanPb = ch => f => (FO_PC_TYPES.includes(ch) ? (f.types[ch] || {}).pc_pb : (f.pieces[ch] || {}).pb);
  const present = FO_PC_CHANNELS.filter(([ch]) => cols.some(c => c.real && chanV(ch)(c.real)));
  present.forEach(([ch, lab]) => rows.push({ label: lab, fmt: 'money', get: chanV(ch) }));
  rows.push({ label: 'Total du département Pièces', fmt: 'money', strong: true, get: f => (f.pieces.total || {}).v || null });
  rows.push({ sec: 'Marge brute par canal' });
  present.forEach(([ch, lab]) => rows.push({ label: lab, fmt: 'percent', get: f => foDiv(chanPb(ch)(f), chanV(ch)(f)) }));
  rows.push({ label: 'Total du département Pièces', fmt: 'percent', strong: true, get: f => foDiv((f.pieces.total || {}).pb, (f.pieces.total || {}).v) });
  rows.push({ sec: 'Pièces par dollar de main-d’œuvre' });
  FO_TYPES.filter(([t]) => FO_PC_TYPES.includes(t)).forEach(([typ, lab]) => rows.push({ label: lab, fmt: 'dec2', get: f => foTypeMetrics(f.types[typ]).pc_mo }));
  container.appendChild(foCard('Pièces', escapeHtml(periodLabel(state.refPeriod)) + ' · ' + escapeHtml(periodModeLabel()),
    foTable('Indicateur', rows, cols),
    'Pièces sur BT client / garantie / entretien BMW / interne : ventes de pièces facturées sur ces bons de travail. ' +
    'Ajustements (escomptes, allocations d’achat, rectifications d’inventaire) : dans le total seulement. ' + foFootBasis()));
}
function foMultiLine(seriesList, fmt, height) {
  // seriesList : [{dealer, points:[{period, value}]}]
  const NS = 'http://www.w3.org/2000/svg';
  const W = 640, H = height || 170, pl = 46, pr = 10, pt = 8, pb = 22;
  const all = [];
  seriesList.forEach(s => s.points.forEach(p => { if (isNum(p.value)) all.push(p.value); }));
  const wrap = document.createElement('div');
  if (!all.length) { wrap.innerHTML = '<div class="no-data">Pas de données pour cette période.</div>'; return wrap; }
  let lo = Math.min(...all), hi = Math.max(...all);
  if (lo > 0) lo = Math.max(0, lo - (hi - lo) * 0.15);
  if (hi === lo) hi = lo + 1;
  const n = seriesList[0].points.length;
  const x = i => pl + (n <= 1 ? 0 : i / (n - 1) * (W - pl - pr));
  const y = v => pt + (1 - (v - lo) / (hi - lo)) * (H - pt - pb);
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.style.cssText = 'width:100%;height:auto;display:block;overflow:visible';
  for (let k = 0; k <= 3; k++) {
    const v = lo + (hi - lo) * k / 3, yy = y(v);
    const ln = document.createElementNS(NS, 'line');
    ln.setAttribute('x1', pl); ln.setAttribute('x2', W - pr); ln.setAttribute('y1', yy); ln.setAttribute('y2', yy);
    ln.setAttribute('stroke', 'var(--grid)'); svg.appendChild(ln);
    const tx = document.createElementNS(NS, 'text');
    tx.setAttribute('x', pl - 6); tx.setAttribute('y', yy + 3); tx.setAttribute('text-anchor', 'end');
    tx.setAttribute('font-size', '10'); tx.setAttribute('fill', 'var(--muted)');
    tx.textContent = foAxis(fmt, v);
    svg.appendChild(tx);
  }
  seriesList[0].points.forEach((p, i) => {
    if (i % 3 !== (n - 1) % 3) return;
    const tx = document.createElementNS(NS, 'text');
    tx.setAttribute('x', x(i)); tx.setAttribute('y', H - 6); tx.setAttribute('text-anchor', 'middle');
    tx.setAttribute('font-size', '10'); tx.setAttribute('fill', 'var(--muted)');
    tx.textContent = periodShortLabel(p.period); svg.appendChild(tx);
  });
  seriesList.forEach(s => {
    let d = '', pen = false;
    s.points.forEach((p, i) => {
      if (!isNum(p.value)) { pen = false; return; }
      d += (pen ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(p.value).toFixed(1) + ' ';
      pen = true;
    });
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', d); path.setAttribute('fill', 'none');
    path.setAttribute('stroke', seriesColor(s.dealer)); path.setAttribute('stroke-width', s.dealer === COMBINED_KEY ? '2.6' : '1.8');
    path.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(path);
    s.points.forEach((p, i) => {
      if (!isNum(p.value)) return;
      const c = document.createElementNS(NS, 'circle');
      c.setAttribute('cx', x(i)); c.setAttribute('cy', y(p.value)); c.setAttribute('r', '6'); c.setAttribute('fill', 'transparent');
      c.addEventListener('mousemove', e => showTip(`<b>${escapeHtml(dealerLabel(s.dealer))}</b> · ${escapeHtml(periodLabel(p.period))}<br>${foFmt(fmt, p.value)}`, e.clientX, e.clientY));
      c.addEventListener('mouseleave', hideTip);
      svg.appendChild(c);
    });
  });
  wrap.appendChild(svg);
  const lg = document.createElement('div');
  lg.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px 14px;font-size:11.5px;color:var(--text-secondary);margin-top:6px';
  lg.innerHTML = seriesList.map(s => `<span style="display:inline-flex;align-items:center;gap:5px"><span class="swatch" style="background:${seriesColor(s.dealer)}"></span>${escapeHtml(dealerLabel(s.dealer))}</span>`).join('');
  wrap.appendChild(lg);
  return wrap;
}
function foSeries(typ, key, n) {
  const m = /^(\d{4})-(\d{2})$/.exec(state.refPeriod || '');
  if (!m) return [];
  let y = parseInt(m[1], 10), mo = parseInt(m[2], 10);
  const periods = [];
  for (let i = 0; i < n; i++) { periods.unshift(`${y}-${String(mo).padStart(2, '0')}`); mo--; if (mo === 0) { mo = 12; y--; } }
  const dealers = orderedKeys(state.dealers);
  const out = dealers.map(d => ({ dealer: d, points: periods.map(p => {
    const f = foGet(d, p, 'month', 'real');
    const t = typ === 'all' ? foAllTypes(f) : (f ? f.types[typ] : null);
    return { period: p, value: foTypeMetrics(t)[key] };
  }) })).filter(s => s.points.some(p => isNum(p.value)));
  if (state.showCombined && dealers.length > 1 && key !== 'bt') { // volumes : le Groupe écraserait l’échelle
    out.unshift({ dealer: COMBINED_KEY, points: periods.map(p => {
      const fl = dealers.map(d => foGet(d, p, 'month', 'real'));
      if (fl.some(f => !f)) return { period: p, value: null };
      const g = foSum(fl);
      const t = typ === 'all' ? foAllTypes(g) : (g ? g.types[typ] : null);
      return { period: p, value: foTypeMetrics(t)[key] };
    }) });
  }
  return out;
}
function renderFoTrendsView(container) {
  const specs = [
    ['client', 'mo_bt', 'money', 'Main-d’œuvre par BT client'],
    ['client', 'tot_bt', 'money', 'Total par BT client (M-O + pièces)'],
    ['client', 'bt', 'volume', 'Nombre de BT client'],
    ['client', 'h_bt', 'dec2', 'Heures vendues par BT client'],
    ['garantie', 'mo_bt', 'money', 'Main-d’œuvre par BT garantie'],
    ['interne', 'mo_bt', 'money', 'Main-d’œuvre par BT interne'],
    ['all', 'bt', 'volume', 'Nombre total de BT'],
    ['client', 'elr', 'money', 'Taux effectif client ($ M-O / heure vendue)'],
  ];
  specs.forEach(([typ, key, fmt, title]) => {
    const series = foSeries(typ, key, 24);
    container.appendChild(foCard(title, '24 derniers mois jusqu’à ' + escapeHtml(periodLabel(state.refPeriod)) + ' · mois',
      foMultiLine(series, fmt), state.showCombined ? 'Groupe : seulement les mois où toutes les concessions cochées ont des données.' : ''));
  });
}
function renderFixedOpsView(container) {
  if (state.period === 'quarter') {
    container.innerHTML = '<div class="chart-card no-data">Opérations fixes : disponibles en « Mois » et en « Cumulatif annuel ».</div>';
    return;
  }
  const v = state.foView || 'bt';
  if (v === 'atelier') renderFoAtelierView(container);
  else if (v === 'pieces') renderFoPiecesView(container);
  else if (v === 'tendances') renderFoTrendsView(container);
  else renderFoBtView(container);
}
