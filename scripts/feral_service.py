#!/usr/bin/env python3
"""
Unified Service Controller (feralctl)
Manages daemon lifecycles for lcars_hopper_watcher and golem_telemetry_bridge.
"""

import os
import sys
import socket
import signal
import subprocess
from pathlib import Path

PID_DIR = Path("/tmp/feral_pids")
LOG_DIR = Path("/tmp/feral_logs")
REPO_ROOT = Path(__file__).resolve().parent.parent

SERVICES = {
    "watcher": "scripts/lcars_hopper_watcher.py",
    "bridge": "scripts/golem_telemetry_bridge.py"
}


def ensure_dirs():
    PID_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def check_port_8765() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", 8765)) == 0


def start_service(name: str):
    ensure_dirs()
    pid_file = PID_DIR / f"{name}.pid"
    if pid_file.exists():
        print(f"[{name.upper()}] Already active (PID: {pid_file.read_text().strip()}).")
        return

    script_path = REPO_ROOT / SERVICES[name]
    log_out = LOG_DIR / f"{name}.log"
    with open(log_out, "a") as log:
        proc = subprocess.Popen([sys.executable, str(script_path)], stdout=log, stderr=log)

    pid_file.write_text(str(proc.pid))
    print(f"[{name.upper()}] Started (PID: {proc.pid}) -> Logs: {log_out}")


def stop_service(name: str):
    pid_file = PID_DIR / f"{name}.pid"
    if not pid_file.exists():
        print(f"[{name.upper()}] Not running.")
        return

    pid = int(pid_file.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"[{name.upper()}] Terminated (PID: {pid}).")
    except ProcessLookupError:
        print(f"[{name.upper()}] Process {pid} not found. Purging PID entry.")
    finally:
        pid_file.unlink(missing_ok=True)


def print_status():
    ensure_dirs()
    print("=================================================================")
    print("  FERAL SERVICE DAEMON CONTROLLER (feralctl) // SAIPH HOUSE LLC  ")
    print("=================================================================")
    for name in SERVICES:
        pid_file = PID_DIR / f"{name}.pid"
        if pid_file.exists():
            print(f"  * {name.ljust(10)}: RUNNING (PID: {pid_file.read_text().strip()})")
        else:
            print(f"  * {name.ljust(10)}: STOPPED")

    port_status = "LISTENING (READY)" if check_port_8765() else "CLOSED (OFFLINE)"
    print(f"  * port_8765 : {port_status}")
    print("=================================================================")


def install_systemd():
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)
    for name, script in SERVICES.items():
        unit_content = f"""[Unit]
Description=Feral Holodeck {name.capitalize()} Daemon
After=network.target

[Service]
Type=simple
ExecStart={sys.executable} {REPO_ROOT / script}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""
        unit_file = systemd_dir / f"feral-{name}.service"
        unit_file.write_text(unit_content)
        print(f"[SYSTEMD] Unit generated: {unit_file}")
    print("[SYSTEMD] Execute: systemctl --user daemon-reload && systemctl --user enable --now feral-watcher feral-bridge")


def install_launchd():
    launchd_dir = Path.home() / "Library" / "LaunchAgents"
    launchd_dir.mkdir(parents=True, exist_ok=True)
    for name, script in SERVICES.items():
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.feral.{name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{str(REPO_ROOT / script)}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
        plist_file = launchd_dir / f"com.feral.{name}.plist"
        plist_file.write_text(plist_content)
        print(f"[LAUNCHD] Plist generated: {plist_file}")
    print("[LAUNCHD] Execute: launchctl load ~/Library/LaunchAgents/com.feral.*.plist")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print_status()
    elif cmd == "start":
        for s in SERVICES:
            start_service(s)
    elif cmd == "stop":
        for s in SERVICES:
            stop_service(s)
    elif cmd == "restart":
        for s in SERVICES:
            stop_service(s)
        for s in SERVICES:
            start_service(s)
    elif cmd == "install-systemd":
        install_systemd()
    elif cmd == "install-launchd":
        install_launchd()
    else:
        print(f"Unknown command: {cmd}. Use: status | start | stop | restart | install-systemd | install-launchd")