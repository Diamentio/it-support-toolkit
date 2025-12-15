#!/usr/bin/env python3
"""
it-support-toolkit
A small, practical IT support CLI: sysinfo + network checks + support report export.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None  # graceful fallback


# ----------------------------
# Logging
# ----------------------------
LOG = logging.getLogger("toolkit")


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


# ----------------------------
# Data models
# ----------------------------
@dataclass
class SysInfo:
    timestamp_utc: str
    hostname: str
    os: str
    os_version: str
    python_version: str
    cpu_count_logical: Optional[int]
    memory_total_gb: Optional[float]
    disk_total_gb: Optional[float]
    disk_free_gb: Optional[float]


@dataclass
class NetCheck:
    local_ip: Optional[str]
    dns_test: Dict[str, Any]
    ping_test: Dict[str, Any]


# ----------------------------
# Helpers
# ----------------------------
def utc_now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def get_local_ip() -> Optional[str]:
    """Best-effort local IP discovery."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def run_cmd(cmd: List[str], timeout: int = 8) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"
    except Exception as e:
        return 1, "", f"Command error: {e}"


def ping(host: str, count: int = 2) -> Dict[str, Any]:
    """
    Cross-platform ping wrapper.
    Windows: ping -n <count>
    mac/linux: ping -c <count>
    """
    is_windows = platform.system().lower().startswith("win")
    cmd = ["ping", "-n" if is_windows else "-c", str(count), host]
    code, out, err = run_cmd(cmd, timeout=10)
    return {"host": host, "ok": code == 0, "code": code, "stdout": out, "stderr": err}


def dns_lookup(host: str) -> Dict[str, Any]:
    try:
        infos = socket.getaddrinfo(host, None)
        ips = sorted({i[4][0] for i in infos})
        return {"host": host, "ok": True, "ips": ips}
    except Exception as e:
        return {"host": host, "ok": False, "error": str(e)}


# ----------------------------
# Core features
# ----------------------------
def collect_sysinfo() -> SysInfo:
    hostname = socket.gethostname()
    os_name = platform.system()
    os_version = platform.version()
    pyver = platform.python_version()

    cpu_count = None
    mem_total_gb = None
    disk_total_gb = None
    disk_free_gb = None

    if psutil:
        cpu_count = psutil.cpu_count(logical=True)
        mem_total_gb = round(psutil.virtual_memory().total / (1024**3), 2)
        du = psutil.disk_usage(os.path.abspath(os.sep))
        disk_total_gb = round(du.total / (1024**3), 2)
        disk_free_gb = round(du.free / (1024**3), 2)
    else:
        # basic fallback if psutil isn't installed
        cpu_count = os.cpu_count()
        total, used, free = shutil.disk_usage(os.path.abspath(os.sep))
        disk_total_gb = round(total / (1024**3), 2)
        disk_free_gb = round(free / (1024**3), 2)

    return SysInfo(
        timestamp_utc=utc_now_iso(),
        hostname=hostname,
        os=os_name,
        os_version=os_version,
        python_version=pyver,
        cpu_count_logical=cpu_count,
        memory_total_gb=mem_total_gb,
        disk_total_gb=disk_total_gb,
        disk_free_gb=disk_free_gb,
    )


def run_netcheck(dns_host: str, ping_host: str) -> NetCheck:
    lip = get_local_ip()
    dns_res = dns_lookup(dns_host)
    ping_res = ping(ping_host)
    return NetCheck(local_ip=lip, dns_test=dns_res, ping_test=ping_res)


def build_report(dns_host: str, ping_host: str) -> Dict[str, Any]:
    sysinfo = collect_sysinfo()
    net = run_netcheck(dns_host, ping_host)
    return {
        "sysinfo": asdict(sysinfo),
        "netcheck": asdict(net),
    }


def save_report(report: Dict[str, Any], out_prefix: str) -> Tuple[str, str]:
    json_path = out_prefix + ".json"
    txt_path = out_prefix + ".txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # simple human-readable text summary
    si = report["sysinfo"]
    nc = report["netcheck"]
    lines = [
        f"IT Support Report ({si['timestamp_utc']})",
        "-" * 40,
        f"Host: {si['hostname']}",
        f"OS: {si['os']} ({si['os_version']})",
        f"Python: {si['python_version']}",
        f"CPU (logical): {si['cpu_count_logical']}",
        f"Memory total (GB): {si['memory_total_gb']}",
        f"Disk total/free (GB): {si['disk_total_gb']} / {si['disk_free_gb']}",
        "",
        "Network:",
        f"Local IP: {nc['local_ip']}",
        f"DNS lookup: {nc['dns_test']}",
        f"Ping test: {nc['ping_test']['host']} ok={nc['ping_test']['ok']} code={nc['ping_test']['code']}",
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return json_path, txt_path


# ----------------------------
# CLI
# ----------------------------
def cmd_sysinfo(_: argparse.Namespace) -> int:
    info = collect_sysinfo()
    print(json.dumps(asdict(info), indent=2))
    return 0


def cmd_netcheck(args: argparse.Namespace) -> int:
    net = run_netcheck(args.dns, args.ping)
    print(json.dumps(asdict(net), indent=2))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    report = build_report(args.dns, args.ping)
    ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_prefix = args.out or f"support_report_{ts}"
    json_path, txt_path = save_report(report, out_prefix)
    print(f"Wrote: {json_path}")
    print(f"Wrote: {txt_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="toolkit", description="IT Support Toolkit (sysinfo + netcheck + report)")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("sysinfo", help="Print system info as JSON")
    s1.set_defaults(func=cmd_sysinfo)

    s2 = sub.add_parser("netcheck", help="Run DNS + ping checks")
    s2.add_argument("--dns", default="google.com", help="Host to DNS-resolve")
    s2.add_argument("--ping", default="8.8.8.8", help="Host/IP to ping")
    s2.set_defaults(func=cmd_netcheck)

    s3 = sub.add_parser("report", help="Generate JSON + TXT support report")
    s3.add_argument("--dns", default="google.com", help="Host to DNS-resolve")
    s3.add_argument("--ping", default="8.8.8.8", help="Host/IP to ping")
    s3.add_argument("--out", help="Output file prefix (no extension)")
    s3.set_defaults(func=cmd_report)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.verbose)
    LOG.debug("Args: %s", args)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
