"""
Computes the period configuration for a quarterly Groupeautomax report run.

Given a target "quarter-end" month (Mars/Juin/Septembre/Décembre), derives every
period-dependent label used across the report pipeline (CUR/PRIOR period keys for
data.json, French month names, formatted dates, quarter labels, file-name stamps).

Usage:
    python3 period.py                    # auto-detect: most recently completed quarter as of today
    python3 period.py --period 2026-06   # force a specific quarter-end month (YYYY-MM)
    python3 period.py --period 2026-06 --prep-date 2026-07-05   # also override the "prepared on" date
"""
import argparse
import json
import os
import sys
from datetime import date

MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}
NB_MOIS_TXT = {
    1: "un", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq", 6: "six",
    7: "sept", 8: "huit", 9: "neuf", 10: "dix", 11: "onze", 12: "douze",
}
# Valid quarter-end (month, last day) pairs.
QUARTER_ENDS = [(3, 31), (6, 30), (9, 30), (12, 31)]


def most_recent_quarter_end(today):
    candidates = []
    for y in (today.year - 1, today.year):
        for m, d in QUARTER_ENDS:
            candidates.append(date(y, m, d))
    candidates = [c for c in candidates if c <= today]
    return max(candidates)


def build_period(cur_period_str=None, prep_date=None):
    if cur_period_str:
        y, m = (int(x) for x in cur_period_str.split('-'))
        if (m, {3: 31, 6: 30, 9: 30, 12: 31}.get(m)) not in QUARTER_ENDS:
            raise SystemExit(f"--period doit se terminer sur un mois de fin de trimestre (03/06/09/12), reçu: {cur_period_str}")
        end = date(y, m, {3: 31, 6: 30, 9: 30, 12: 31}[m])
    else:
        end = most_recent_quarter_end(date.today())

    year_cur, month_end = end.year, end.month
    year_prior = year_cur - 1
    jour_fin = end.day
    quarter_num = month_end // 3

    mois_cur = MOIS_FR[month_end]
    mois_cur_cap = mois_cur.capitalize()

    if prep_date:
        py, pm, pd = (int(x) for x in prep_date.split('-'))
        prep = date(py, pm, pd)
    else:
        prep = date.today()
    prep_label = f"{MOIS_FR[prep.month]} {prep.year}"

    cfg = {
        "cur_period": f"{year_cur}-{month_end:02d}",
        "prior_period": f"{year_prior}-{month_end:02d}",
        "year_cur": year_cur,
        "year_prior": year_prior,
        "yy_cur": f"{year_cur % 100:02d}",
        "yy_prior": f"{year_prior % 100:02d}",
        "mois_cur": mois_cur,
        "mois_cur_cap": mois_cur_cap,
        "jour_fin": str(jour_fin),
        "date_fin_cur": f"{jour_fin} {mois_cur} {year_cur}",
        "date_fin_prior": f"{jour_fin} {mois_cur} {year_prior}",
        "nb_mois": month_end,
        "nb_mois_txt": NB_MOIS_TXT[month_end],
        "period_label_cur": f"Janvier - {mois_cur_cap} {year_cur}",
        "period_label_prior": f"Janvier - {mois_cur_cap} {year_prior}",
        "quarter_num": quarter_num,
        "quarter_label": f"T{quarter_num} {year_cur}",
        "file_stamp": f"T{quarter_num}-{year_cur}",
        "prep_label": prep_label,
    }
    return cfg


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--period', default=None, help='YYYY-MM quarter-end month, e.g. 2026-06')
    ap.add_argument('--prep-date', default=None, help='YYYY-MM-DD, overrides "prepared on" date (defaults to today)')
    ap.add_argument('--workdir', default='.')
    args = ap.parse_args()

    cfg = build_period(args.period, args.prep_date)
    out_path = os.path.join(args.workdir, 'period.json')
    json.dump(cfg, open(out_path, 'w'), indent=2, ensure_ascii=False)
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
