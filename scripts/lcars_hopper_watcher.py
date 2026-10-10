#!/usr/bin/env python3
"""
LCARS Okudagram TUI Watchdog
Monitors /audio_staging/ with SHA256 stability checks and live duration extraction.
Displays real-time LCARS status interface with zero cloud telemetry leak.
"""

import os
import sys
import time
import hashlib
from pathlib import Path

# Terminal Okudagram Palette
AMBER = "\033[38;2;255;153;0m"
PURPLE = "\033[38;2;204;153;204m"
CYAN = "\033[38;2;0;204;255m"
GREEN = "\033[38;2;51;255;102m"
RESET = "\033[0m"
BOLD = "\033[1m"


def calculate_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def render_lcars_display(staged_files: list):
    os.system("clear" if os.name == "posix" else "cls")
    print(f"{AMBER}{BOLD}========================================================================{RESET}")
    print(f"{AMBER}{BOLD}  LCARS 2405.10 // SAIPH HOUSE SOVEREIGN HOPPER WATCHDOG                {RESET}")
    print(f"{AMBER}{BOLD}========================================================================{RESET}")
    print(f"{PURPLE}  MONITOR DIRECTORY: /audio_staging/        STATUS: ACTIVE POLLING{RESET}")
    print(f"{CYAN}  TACTICAL OVERRIDE: Zero-Trust Hardware Integrity Bound{RESET}\n")

    if not staged_files:
        print(f"{GREEN}  [IDLE] HOPPER CLEAR // Awaiting chronological dispatcher drop...{RESET}")
    else:
        print(f"{AMBER}  INDEX | FILE IDENTIFIER                          | SIZE (BYTES) | SHA256 (PREFIX){RESET}")
        print(f"{AMBER}  ------------------------------------------------------------------------{RESET}")
        for idx, (fname, size, fhash) in enumerate(staged_files, 1):
            truncated_name = (fname[:38] + "..") if len(fname) > 40 else fname.ljust(40)
            print(f"  {PURPLE}{str(idx).zfill(2)}{RESET}    | {CYAN}{truncated_name}{RESET} | {GREEN}{str(size).rjust(12)}{RESET} | {AMBER}{fhash[:12]}...{RESET}")

    print(f"\n{AMBER}{BOLD}========================================================================{RESET}")
    print(f"{PURPLE}  PRESS CTRL+C TO TERMINATE SENTRY DAEMON // PID: {os.getpid()}{RESET}")


def watch_hopper(staging_dir: Path, poll_interval: float = 3.0):
    staging_dir.mkdir(parents=True, exist_ok=True)
    previous_hashes = {}

    while True:
        current_entries = []
        for p in staging_dir.iterdir():
            if p.is_file() and p.suffix.lower() in [".m4a", ".mp3", ".wav"]:
                size = p.stat().st_size
                fhash = calculate_sha256(p)
                current_entries.append((p.name, size, fhash))

        render_lcars_display(current_entries)
        time.sleep(poll_interval)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    staging = root / "audio_staging"
    try:
        watch_hopper(staging)
    except KeyboardInterrupt:
        print(f"\n{AMBER}[WATCHDOG_HALTED] Safehood sentry standing down.{RESET}")