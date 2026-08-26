import json
import os

WORKDIR = os.environ.get('KPI_WORKDIR', '.')

P = json.load(open(os.path.join(WORKDIR, 'period.json')))
summaries = json.load(open(os.path.join(WORKDIR, 'dealer_summaries.json')))
DEALER_ORDER = [k for k in ['bmw', 'vw', 'stm', 'hyundai', 'hawks'] if k in summaries]

ADDITIVE = ['ventes_nettes', 'pb_total', 'pb_neuf', 'pb_usage', 'pb_service', 'pb_carrosserie',
            'pb_pieces', 'autres_revenus', 'depenses', 'depenses_variables', 'depenses_personnel',
            'depenses_semifixes', 'ebitda', 'ebt', 'unites_neuf', 'unites_usage', 'unites_flottes']


def sum_field(field, suffix):
    total = 0.0
    any_val = False
    for k in DEALER_ORDER:
        v = summaries[k].get(field + suffix)
        if v is not None:
            total += v
            any_val = True
    return total if any_val else None


group = {}
for f in ADDITIVE:
    group[f + '_cur'] = sum_field(f, '_cur')
    group[f + '_prior'] = sum_field(f, '_prior')


def pct_change(cur, prior):
    if cur is None or prior is None or prior == 0:
        return None
    return (cur - prior) / abs(prior)


def derive(d, prefix=''):
    out = {}
    for period in ['cur', 'prior']:
        rev = d.get(f'ventes_nettes_{period}')
        gp = d.get(f'pb_total_{period}')
        dep = d.get(f'depenses_{period}')  # negative
        autres = d.get(f'autres_revenus_{period}')
        ebt = d.get(f'ebt_{period}')
        ebitda = d.get(f'ebitda_{period}')
        new_u = d.get(f'unites_neuf_{period}')
        used_u = d.get(f'unites_usage_{period}')
        out[f'gross_margin_{period}'] = (gp / rev) if (gp is not None and rev) else None
        opex = (-dep) if dep is not None else None
        out[f'opex_{period}'] = opex
        out[f'operating_profit_{period}'] = (gp + dep) if (gp is not None and dep is not None) else None
        out[f'ebt_pct_revenue_{period}'] = (ebt / rev) if (ebt is not None and rev) else None
        out[f'ebt_pct_gp_{period}'] = (ebt / gp) if (ebt is not None and gp) else None
        out[f'ebitda_pct_revenue_{period}'] = (ebitda / rev) if (ebitda is not None and rev) else None
        out[f'expenses_pct_gp_{period}'] = (opex / gp) if (opex is not None and gp) else None
        out[f'total_retail_units_{period}'] = (new_u + used_u) if (new_u is not None and used_u is not None) else None
        out[f'new_used_ratio_{period}'] = (new_u / used_u) if (new_u is not None and used_u) else None
        out[f'gpa_neuf_{period}'] = (d.get(f'pb_neuf_{period}') / new_u) if (d.get(f'pb_neuf_{period}') is not None and new_u) else None
        out[f'gpa_usage_{period}'] = (d.get(f'pb_usage_{period}') / used_u) if (d.get(f'pb_usage_{period}') is not None and used_u) else None
    return out


group.update(derive(group))
for k in DEALER_ORDER:
    summaries[k].update(derive(summaries[k]))

# Percent changes for headline fields
HEADLINE = ['ventes_nettes', 'pb_total', 'opex', 'operating_profit', 'autres_revenus', 'ebt', 'ebitda',
            'depenses_variables', 'depenses_personnel', 'depenses_semifixes',
            'pb_neuf', 'pb_usage', 'pb_service', 'pb_carrosserie', 'pb_pieces',
            'unites_neuf', 'unites_usage', 'total_retail_units', 'gpa_neuf', 'gpa_usage']

# These fields are stored as NEGATIVE numbers (accounting-style expense
# outflows, e.g. -3,285,907 $). A raw (cur-prior)/prior on two negative
# numbers yields a sign that reads backwards to a human ("-23%" when the
# dealer actually spent 23% MORE) -- so for these specific fields we compute
# the delta on magnitude instead, matching how 'opex' (already flipped to
# positive by derive()) behaves: positive delta = spent more, negative = spent less.
MAGNITUDE_FIELDS = {'depenses_variables', 'depenses_personnel', 'depenses_semifixes', 'depenses'}


def add_deltas(d):
    for f in HEADLINE:
        c = d.get(f + '_cur')
        p = d.get(f + '_prior')
        if f in MAGNITUDE_FIELDS and c is not None and p is not None:
            c, p = abs(c), abs(p)
        d[f + '_delta_pct'] = pct_change(c, p)
        d[f + '_delta_abs'] = (c - p) if (c is not None and p is not None) else None


add_deltas(group)
for k in DEALER_ORDER:
    add_deltas(summaries[k])

report_data = {
    'group': group, 'dealers': {k: summaries[k] for k in DEALER_ORDER}, 'dealer_order': DEALER_ORDER,
    'period_label_cur': P['period_label_cur'], 'period_label_prior': P['period_label_prior'],
    **P,
}

json.dump(report_data, open(os.path.join(WORKDIR, 'report_data.json'), 'w'), indent=2, ensure_ascii=False)

print("GROUP TOTALS —", P['cur_period'], "vs", P['prior_period'])
for f in ['ventes_nettes', 'pb_total', 'opex', 'operating_profit', 'autres_revenus', 'ebt', 'ebitda']:
    print(f, 'cur=', round(group[f + '_cur'], 0) if group[f + '_cur'] is not None else None,
          'prior=', round(group[f + '_prior'], 0) if group[f + '_prior'] is not None else None,
          'delta%=', round(group[f + '_delta_pct'] * 100, 1) if group[f + '_delta_pct'] is not None else None)
print('gross_margin cur', group['gross_margin_cur'], 'prior', group['gross_margin_prior'])
print('units new cur/prior', group['unites_neuf_cur'], group['unites_neuf_prior'])
print('units used cur/prior', group['unites_usage_cur'], group['unites_usage_prior'])
print('dealers included:', DEALER_ORDER)
