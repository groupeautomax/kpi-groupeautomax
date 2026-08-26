import json
import os

WORKDIR = os.environ.get('KPI_WORKDIR', '.')

d = json.load(open(os.path.join(WORKDIR, 'report_data.json')))
dealers = d['dealers']
order = d['dealer_order']

rows = []
for k in order:
    dd = dealers[k]
    rows.append({
        'key': k,
        'display_name': dd['display_name'],
        'rev_cur': dd['ventes_nettes_cur'], 'rev_prior': dd['ventes_nettes_prior'],
        'ebt_cur': dd['ebt_cur'], 'ebt_prior': dd['ebt_prior'],
        'ebt_delta_abs': dd['ebt_delta_abs'], 'ebt_delta_pct': dd['ebt_delta_pct'],
    })

rows.sort(key=lambda r: r['ebt_delta_abs'] if r['ebt_delta_abs'] is not None else 0, reverse=True)


def status(r):
    pct = r['ebt_delta_pct']
    if pct is None:
        return 'N/D'
    if pct >= 0.10:
        return 'EN CROISSANCE'
    if pct >= -0.05:
        return 'STABLE'
    if pct >= -0.20:
        return 'SOUS FOCUS'
    return 'PRIORITE H2'


for r in rows:
    r['status'] = status(r)

group_ebt_cur = d['group']['ebt_cur']
group_ebt_prior = d['group']['ebt_prior']

concentration = []
for k in order:
    dd = dealers[k]
    concentration.append({
        'key': k, 'display_name': dd['display_name'],
        'ebt_cur': dd['ebt_cur'], 'ebt_prior': dd['ebt_prior'],
        'share_cur': (dd['ebt_cur'] / group_ebt_cur) if (dd['ebt_cur'] is not None and group_ebt_cur) else None,
        'share_prior': (dd['ebt_prior'] / group_ebt_prior) if (dd['ebt_prior'] is not None and group_ebt_prior) else None,
    })
concentration.sort(key=lambda r: r['share_cur'] or 0, reverse=True)

out = {'scorecard': rows, 'concentration': concentration}
json.dump(out, open(os.path.join(WORKDIR, 'scorecard.json'), 'w'), indent=2, ensure_ascii=False)

for r in rows:
    print(f"{r['display_name']:20s} EBTcur={r['ebt_cur']:>12,.0f}  EBTprior={r['ebt_prior']:>12,.0f}  "
          f"Δ$={r['ebt_delta_abs']:>12,.0f}  Δ%={r['ebt_delta_pct']*100:>6.1f}%  {r['status']}")
print()
for c in concentration:
    print(f"{c['display_name']:20s} part cur={c['share_cur']*100:5.1f}%  part prior={c['share_prior']*100:5.1f}%")
