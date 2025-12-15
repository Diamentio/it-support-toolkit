# IT Support Toolkit

A cross-platform Python command-line tool for basic IT support diagnostics.

Designed to simulate real-world Tier 1 / Tier 2 support workflows:
- Collect system information
- Perform DNS resolution and network connectivity checks
- Generate ticket-ready support reports (JSON + TXT)

---

## Features

- System diagnostics (OS, CPU, memory, disk, Python version)
- Network troubleshooting (DNS lookup, ping test)
- Report generation suitable for helpdesk ticket attachments
- Graceful fallback when optional dependencies are unavailable
- Cross-platform (Windows, macOS, Linux)

---

## Installation

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
