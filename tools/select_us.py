#!/usr/bin/env python3
"""Run the checked TV-side selector through samsung-tv-root."""
import ipaddress
import json
from pathlib import Path
import shlex
import subprocess
import sys

try:
    if len(sys.argv) != 5 or sys.argv[4] not in ("--check", "--apply"):
        raise ValueError("用法: python3 select_us.py 电视IP sdb路径 samsung-tv-root路径 --check 或 --apply")
    ip = str(ipaddress.IPv4Address(sys.argv[1]))
    sdb = str(Path(sys.argv[2]).expanduser().resolve(strict=True))
    root = str(Path(sys.argv[3]).expanduser().resolve(strict=True))
    code = (Path(__file__).resolve().parent / "select_us.sh").read_text()
    command = "sh -c " + shlex.quote(code) + " sh " + shlex.quote(sys.argv[4])
    p = subprocess.run([root, "--sdb", sdb, "-o", "json", "archive-root", "root", ip,
                        "--command", command, "--command-timeout", "25"],
                       capture_output=True, text=True, timeout=70)
    try:
        result = json.loads(p.stdout)
    except json.JSONDecodeError:
        raise RuntimeError((p.stderr or p.stdout).strip()[:600])
    item = result["commands"][0]
    print(item.get("stdout", ""), end="")
    if p.returncode or item.get("exit_code") != 0 or item.get("timed_out"):
        raise RuntimeError(item.get("stderr", "")[:300] or "电视端检查失败")
except (ValueError, RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError) as exc:
    print("未完成:", exc, file=sys.stderr)
    sys.exit(1)
