import json
import os

WORKDIR = os.environ.get('KPI_WORKDIR', '.')

d = json.load(open(os.path.join(WORKDIR, 'report_data.json')))
g = d['group']


def dept_mix(period):
    neuf = g[f'pb_neuf_{period}'] or 0
    usage = g[f'pb_usage_{period}'] or 0
    service = g[f'pb_service_{period}'] or 0
    carr = g[f'pb_carrosserie_{period}'] or 0
    pieces = g[f'pb_pieces_{period}'] or 0
    total = g[f'pb_total_{period}'] or 0
    known = neuf + usage + service + carr + pieces
    autres = total - known
    return {
        'Neuf': neuf, 'Usagé': usage, 'Service': service,
        'Carrosserie': carr, 'Pièces': pieces, 'Autres': autres,
    }, total


def expense_mix(period):
    var = -(g[f'depenses_variables_{period}'] or 0)
    pers = -(g[f'depenses_personnel_{period}'] or 0)
    semi = -(g[f'depenses_semifixes_{period}'] or 0)
    opex = g[f'opex_{period}'] or 0
    known = var + pers + semi
    fixe = opex - known
    return {'Variables': var, 'Personnel': pers, 'Semi-fixes': semi, 'Fixes / non ventilées': fixe}, opex


for period in ['prior', 'cur']:
    mix, total = dept_mix(period)
    print(period, 'dept mix total', total, mix, 'sum check', sum(mix.values()))
print()
for period in ['prior', 'cur']:
    mix, total = expense_mix(period)
    print(period, 'expense mix total', total, mix, 'sum check', sum(mix.values()))

out = {'dept_mix_prior': dept_mix('prior')[0], 'dept_mix_cur': dept_mix('cur')[0],
       'dept_total_prior': dept_mix('prior')[1], 'dept_total_cur': dept_mix('cur')[1],
       'expense_mix_prior': expense_mix('prior')[0], 'expense_mix_cur': expense_mix('cur')[0],
       'expense_total_prior': expense_mix('prior')[1], 'expense_total_cur': expense_mix('cur')[1]}
json.dump(out, open(os.path.join(WORKDIR, 'mix_data.json'), 'w'), indent=2, ensure_ascii=False)
