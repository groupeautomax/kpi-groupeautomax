import json
import os

WORKDIR = os.environ.get('KPI_WORKDIR', '.')

P = json.load(open(os.path.join(WORKDIR, 'period.json')))
d = json.load(open(os.path.join(WORKDIR, 'live_data.json')))
dealers_raw = d['dealers']

DEALER_ORDER = ['bmw', 'vw', 'stm', 'hyundai', 'hawks']
CUR_PERIOD = P['cur_period']
PRIOR_PERIOD = P['prior_period']


def g(kv, key='real'):
    if kv is None:
        return None
    return kv.get(key)


def dealer_summary(key):
    dd = dealers_raw[key]
    cur_p = dd['periods'].get(CUR_PERIOD)
    if not cur_p:
        return None
    cur = cur_p['sections']['ytd']
    kpis = cur['kpis']

    # Determine prior-year kpis: prefer embedded prior_year field; if a dealer's
    # prior-period file exists as a standalone period entry (real-only formats
    # like HAWKS, or simply a case where the embedded prior_year is missing),
    # pull that period's own kpis directly instead.
    prior_kpis = None
    prior_source = 'embedded'
    sample_kv = next((v for v in kpis.values() if v), None)
    embedded_missing = sample_kv is not None and sample_kv.get('prior_year') is None
    if embedded_missing and PRIOR_PERIOD in dd['periods']:
        prior_kpis = dd['periods'][PRIOR_PERIOD]['sections']['ytd']['kpis']
        prior_source = 'separate_file'

    def cur_val(k):
        return g(kpis.get(k))

    def prior_val(k):
        if prior_kpis is not None:
            return g(prior_kpis.get(k))
        kv = kpis.get(k)
        return g(kv, 'prior_year') if kv else None

    fields = ['ventes_nettes', 'pb_total', 'pb_neuf', 'pb_usage', 'pb_service', 'pb_carrosserie',
              'pb_pieces', 'autres_revenus', 'depenses', 'depenses_variables', 'depenses_personnel',
              'depenses_semifixes', 'ebitda', 'ebt', 'unites_neuf', 'unites_usage', 'unites_flottes',
              'gpa_neuf', 'gpa_usage']

    out = {'key': key, 'display_name': dd['display_name'], 'source_title_cur': cur.get('source_title'),
           'prior_source': prior_source}
    for f in fields:
        out[f + '_cur'] = cur_val(f)
        out[f + '_prior'] = prior_val(f)
    return out


summaries = {}
for k in DEALER_ORDER:
    s = dealer_summary(k)
    if s:
        summaries[k] = s
    else:
        print(f"AVERTISSEMENT: aucune donnée pour '{k}' à la période {CUR_PERIOD} -- absent du rapport.")

json.dump(summaries, open(os.path.join(WORKDIR, 'dealer_summaries.json'), 'w'), indent=2, ensure_ascii=False)
print("Wrote summaries for:", list(summaries.keys()))
for k, s in summaries.items():
    print(k, '| cur src', s['source_title_cur'], '| prior_source', s['prior_source'],
          '| revenue cur', s['ventes_nettes_cur'], '| revenue prior', s['ventes_nettes_prior'])
