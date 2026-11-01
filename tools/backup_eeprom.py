#!/usr/bin/env python3
"""Read-only backup for QA75QN85BAJXXZ on T-PTMUABC-1651.7.

Usage: python3 backup_eeprom.py TV_IP SDB_PATH SAMSUNG_TV_ROOT_PATH
The bundled 32-bit reader performs two I2C random reads and checks equality.
"""
import base64
import datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys


def main():
    if len(sys.argv) != 4:
        raise ValueError("用法: python3 backup_eeprom.py 电视IP sdb路径 samsung-tv-root路径")
    tv_ip = str(ipaddress.IPv4Address(sys.argv[1]))
    sdb = str(Path(sys.argv[2]).expanduser().resolve(strict=True))
    root = str(Path(sys.argv[3]).expanduser().resolve(strict=True))
    source = Path(__file__).resolve().parent
    files = ("EepromRead.dll", "EepromRead.runtimeconfig.json")
    for name in files:
        if not (source / name).is_file():
            raise ValueError("缺少备份程序文件: " + name)

    def execute(command):
        p = subprocess.run(command, capture_output=True, text=True, timeout=70)
        if p.returncode:
            detail = p.stderr.strip()[:500] or ("退出码 " + str(p.returncode))
            raise RuntimeError("命令失败: " + detail)
        return p.stdout

    def root_commands(*commands):
        args = [root, "--sdb", sdb, "-o", "json", "archive-root", "root", tv_ip]
        for command in commands:
            args.extend(("--command", command))
        args.extend(("--command-timeout", "25"))
        result = json.loads(execute(args))
        if not result.get("authenticated"):
            raise RuntimeError("未取得临时 root")
        for item in result["commands"]:
            if item.get("exit_code") != 0 or item.get("timed_out"):
                raise RuntimeError("电视端命令失败: " + item.get("stderr", "")[:300])
        return result["commands"]

    serial = tv_ip + ":26101"
    execute([sdb, "connect", serial])
    check = root_commands(
        "gdbus call --system --timeout 5 --dest org.tizen.tv.factory-service "
        "--object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetVersionInfo",
        "readlink /sys/bus/i2c/devices/3-0050/driver",
    )
    version = check[0]["stdout"]
    if "Model : QA75QN85BAJXXZ" not in version or not re.search(r"T-PTMUABC-1651\.7(?:\\n|\s|')", version):
        raise RuntimeError("型号或固件不匹配：本工具只适用于 QA75QN85BAJXXZ / T-PTMUABC-1651.7")
    if not check[1]["stdout"].strip().endswith("/s24c512c"):
        raise RuntimeError("EEPROM 驱动不匹配，未进行读取")

    remote = "/home/owner/share/tmp/sdk_tools/tv-region-backup-" + secrets.token_hex(6)
    created = False
    try:
        root_commands("mkdir " + remote)
        created = True
        for name in files:
            execute([sdb, "-s", serial, "push", str(source / name), remote + "/" + name])
        result = root_commands("dotnet " + remote + "/EepromRead.dll --read-i2c")[0]["stdout"]
        lines = result.splitlines()
        reported = next(x.split("=", 1)[1] for x in lines if x.startswith("SHA256="))
        image = base64.b64decode(next(x.split("=", 1)[1] for x in lines if x.startswith("FACTORY_BASE64=")), validate=True)
        digest = hashlib.sha256(image).hexdigest()
        if len(image) != 65536 or digest != reported:
            raise RuntimeError("备份长度或 SHA-256 不匹配，未保存")
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = Path.cwd() / ("电视EEPROM备份-" + timestamp + ".bin")
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(image)
        print("已保存:", dest)
        print("长度:", len(image), "字节；两次读取一致")
        print("SHA-256:", digest)
        print("备份含设备专属信息；恢复方法尚未验证，请勿公开。")
    finally:
        if created:
            try:
                root_commands("rm -f " + remote + "/EepromRead.dll " + remote + "/EepromRead.runtimeconfig.json; rmdir " + remote)
            except Exception:
                print("注意：电视端临时目录未能自动清理:", remote, file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError, StopIteration) as exc:
        print("备份未完成:", str(exc), file=sys.stderr)
        sys.exit(1)
