#!/usr/bin/env python3
"""
Orchestrates a full quarterly Groupeautomax report run: fetches the live KPI
dashboard data, computes the period configuration, runs the extraction/build
pipeline for the group report and all 5 per-dealer reports, renders every HTML
report to PDF, and writes the 6 finished PDFs into an output directory.

Usage:
    python3 run_quarter.py --outdir /path/to/output
    python3 run_quarter.py --outdir /path/to/output --period 2026-09   # force a quarter
    python3 run_quarter.py --outdir /path/to/output --data-url https://...  # override data source
    python3 run_quarter.py --outdir /path/to/output --data-file /path/to/data.json  # use a local snapshot instead of fetching

Requires: the sibling pipeline scripts in this same directory (period.py,
extract_summary.py, build_report_data.py, scorecard.py, mix_data.py,
per_dealer_mix.py, make_charts.py, make_dealer_charts.py, build_html.py,
build_dealer_html.py), plus playwright with a Chromium install (this sandbox
provides one at /opt/pw-browsers/chromium; PLAYWRIGHT_CHROMIUM_PATH overrides).
"""
import argparse
import json
import os
import subprocess
import sys
import shutil
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_URL = "https://raw.githubusercontent.com/groupeautomax/kpi-groupeautomax/main/data/data.json"
DEALER_ORDER = ['bmw', 'vw', 'stm', 'hyundai', 'hawks']
DEALER_FILE_NAMES = {
    'bmw': 'BMW_Sherbrooke', 'vw': 'Volkswagen', 'stm': 'STM', 'hyundai': 'Hyundai', 'hawks': 'HAWKS',
}


def run(cmd, workdir_env):
    env = dict(os.environ)
    env['KPI_WORKDIR'] = workdir_env
    print(f"$ {' '.join(cmd)}  (KPI_WORKDIR={workdir_env})")
    subprocess.run(cmd, check=True, env=env, cwd=HERE)


def render_pdf(html_path, pdf_path, chromium_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_path)
        page = browser.new_page()
        page.goto('file://' + os.path.abspath(html_path))
        page.pdf(path=pdf_path, format='Letter', print_background=True, margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outdir', required=True, help='directory to write the 6 final PDFs into')
    ap.add_argument('--period', default=None, help='YYYY-MM quarter-end month, e.g. 2026-09 (default: auto-detect most recently completed quarter)')
    ap.add_argument('--prep-date', default=None, help='YYYY-MM-DD override for the "prepared on" date')
    ap.add_argument('--data-url', default=DEFAULT_DATA_URL)
    ap.add_argument('--data-file', default=None, help='use a local data.json snapshot instead of fetching --data-url')
    ap.add_argument('--chromium-path', default=os.environ.get('PLAYWRIGHT_CHROMIUM_PATH', '/opt/pw-browsers/chromium'))
    ap.add_argument('--keep-work', action='store_true', help='keep the intermediate working directory (default: cleaned up on success)')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    workdir = os.path.join(args.outdir, '_work')
    os.makedirs(workdir, exist_ok=True)

    # 1. Data source
    data_path = os.path.join(workdir, 'live_data.json')
    if args.data_file:
        shutil.copy(args.data_file, data_path)
        print(f"Using local data snapshot: {args.data_file}")
    else:
        print(f"Fetching {args.data_url} ...")
        urllib.request.urlretrieve(args.data_url, data_path)

    # 2. Period config
    period_cmd = [sys.executable, os.path.join(HERE, 'period.py'), '--workdir', workdir]
    if args.period:
        period_cmd += ['--period', args.period]
    if args.prep_date:
        period_cmd += ['--prep-date', args.prep_date]
    subprocess.run(period_cmd, check=True)
    P = json.load(open(os.path.join(workdir, 'period.json')))
    print(f"\n=== Période cible: {P['quarter_label']} (cur={P['cur_period']}, prior={P['prior_period']}) ===\n")

    # 3. Group pipeline
    for script in ['extract_summary.py', 'build_report_data.py', 'scorecard.py', 'mix_data.py', 'make_charts.py']:
        run([sys.executable, os.path.join(HERE, script)], workdir)
    run([sys.executable, os.path.join(HERE, 'build_html.py')], workdir)

    # 4. Per-dealer pipeline
    run([sys.executable, os.path.join(HERE, 'per_dealer_mix.py')], workdir)
    run([sys.executable, os.path.join(HERE, 'make_dealer_charts.py')], workdir)
    run([sys.executable, os.path.join(HERE, 'build_dealer_html.py')], workdir)

    # 5. Render PDFs
    stamp = P['file_stamp']
    render_pdf(os.path.join(workdir, 'report.html'),
               os.path.join(args.outdir, f'Groupeautomax_Rapport_Performance_{stamp}.pdf'),
               args.chromium_path)
    print(f"-> Groupeautomax_Rapport_Performance_{stamp}.pdf")

    report_data = json.load(open(os.path.join(workdir, 'report_data.json')))
    for key in report_data['dealer_order']:
        html_path = os.path.join(workdir, f'report_{key}.html')
        if not os.path.exists(html_path):
            print(f"AVERTISSEMENT: pas de rapport HTML pour '{key}' (probablement absent des données de cette période), ignoré.")
            continue
        fname = DEALER_FILE_NAMES.get(key, key)
        pdf_path = os.path.join(args.outdir, f'Rapport_{fname}_{stamp}.pdf')
        render_pdf(html_path, pdf_path, args.chromium_path)
        print(f"-> Rapport_{fname}_{stamp}.pdf")

    if not args.keep_work:
        shutil.rmtree(workdir, ignore_errors=True)
    else:
        print(f"(dossier de travail conservé: {workdir})")

    print(f"\nTerminé. {len(report_data['dealer_order']) + 1} PDF(s) dans {args.outdir}")


if __name__ == '__main__':
    main()
