#!/usr/bin/env python3
"""
Scheduled Daily Queue Dispatcher
Scans inputs/shows/*/queue/ sorted chronologically by mtime, transfers 1 file
per cycle to /audio_staging/, and appends a CAP-LOG-QUEUE audit event.
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timezone


def feed_hopper(repo_root: Path, rate: int = 1) -> list:
    shows_dir = repo_root / "inputs" / "shows"
    staging_dir = repo_root / "audio_staging"
    log_file = repo_root / "captains_log_staging.json"
    staging_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    for queue_dir in shows_dir.glob("*/queue"):
        if queue_dir.is_dir():
            show_slug = queue_dir.parent.name
            for audio_file in queue_dir.iterdir():
                if audio_file.suffix.lower() in [".m4a", ".mp3", ".wav"]:
                    candidates.append((audio_file.stat().st_mtime, audio_file, show_slug))

    # Sort chronologically (oldest modified first)
    candidates.sort(key=lambda x: x[0])
    selected = candidates[:rate]
    dispatched = []

    for _, src_file, show_slug in selected:
        dest_file = staging_dir / src_file.name
        shutil.move(str(src_file), str(dest_file))
        dispatched.append({"file": src_file.name, "show": show_slug, "destination": str(dest_file)})

        # Append audit entry to captains_log_staging.json
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log_entry = {
            "id": f"CAP-LOG-QUEUE-{int(datetime.now(timezone.utc).timestamp())}",
            "timestamp": now_iso,
            "subject": f"Dispatch: {src_file.name} to /audio_staging/",
            "audited": True,
            "category": "Hopper_Dispatch",
            "location": "scripts/daily_hopper_feeder.py",
            "primary_data": f"Moved {src_file.name} from show {show_slug} to staging hopper.",
            "secondary_data": f"Source: {src_file} | Destination: {dest_file}",
            "tags": ["Hopper", "Queue", "Automation", "BareMetal"],
            "metadata": {
                "legacy_id": "FIFO_DISPATCH",
                "threat_level": "NOMINAL",
                "cognitive_state": "Low-RAM Serial Single-Tasking Optimal"
            }
        }

        existing_logs = []
        if log_file.exists():
            try:
                existing_logs = json.loads(log_file.read_text(encoding="utf-8"))
            except Exception:
                existing_logs = []

        existing_logs.append(log_entry)
        log_file.write_text(json.dumps(existing_logs, indent=2), encoding="utf-8")

    return dispatched


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispatch oldest audio candidate to staging hopper.")
    parser.add_argument("--rate", type=int, default=1, help="Number of files to dispatch per run.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    result = feed_hopper(root, rate=args.rate)
    print(f"[HOPPER_FEED] Dispatched {len(result)} asset(s) to audio_staging.")