# it-support-toolkit

A small IT support command-line toolkit that:
- prints system info
- runs DNS + ping checks
- generates a support report in JSON + TXT (attachable to tickets)

## Install
python -m venv .venv
# Windows: .venv\Scripts\activate
# mac/linux: source .venv/bin/activate
pip install -r requirements.txt

## Examples
python toolkit.py sysinfo
python toolkit.py netcheck --dns google.com --ping 8.8.8.8
python toolkit.py report --out sample_reports/my_pc_report
