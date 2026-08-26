import json
import os

WORKDIR = os.environ.get('KPI_WORKDIR', '.')

d = json.load(open(os.path.join(WORKDIR, 'report_data.json')))
DEALERS = d['dealers']
ORDER = d['dealer_order']


def dept_mix(dd, period):
    neuf = dd[f'pb_neuf_{period}'] or 0
    usage = dd[f'pb_usage_{period}'] or 0
    service = dd[f'pb_service_{period}'] or 0
    carr = dd[f'pb_carrosserie_{period}'] or 0
    pieces = dd[f'pb_pieces_{period}'] or 0
    total = dd[f'pb_total_{period}'] or 0
    known = neuf + usage + service + carr + pieces
    autres = total - known
    return {'Neuf': neuf, 'Usagé': usage, 'Service': service, 'Carrosserie': carr, 'Pièces': pieces, 'Autres': autres}, total


def expense_mix(dd, period):
    var = -(dd[f'depenses_variables_{period}'] or 0)
    pers = -(dd[f'depenses_personnel_{period}'] or 0)
    semi = -(dd[f'depenses_semifixes_{period}'] or 0)
    opex = dd[f'opex_{period}'] or 0
    known = var + pers + semi
    fixe = opex - known
    return {'Variables': var, 'Personnel': pers, 'Semi-fixes': semi, 'Fixes / non ventilées': fixe}, opex


out = {}
for k in ORDER:
    dd = DEALERS[k]
    out[k] = {
        'dept_mix_prior': dept_mix(dd, 'prior')[0], 'dept_mix_cur': dept_mix(dd, 'cur')[0],
        'dept_total_prior': dept_mix(dd, 'prior')[1], 'dept_total_cur': dept_mix(dd, 'cur')[1],
        'expense_mix_prior': expense_mix(dd, 'prior')[0], 'expense_mix_cur': expense_mix(dd, 'cur')[0],
        'expense_total_prior': expense_mix(dd, 'prior')[1], 'expense_total_cur': expense_mix(dd, 'cur')[1],
    }

json.dump(out, open(os.path.join(WORKDIR, 'per_dealer_mix.json'), 'w'), indent=2, ensure_ascii=False)
for k in ORDER:
    print(k, 'dept_total_cur', round(out[k]['dept_total_cur']), 'expense_total_cur', round(out[k]['expense_total_cur']))
