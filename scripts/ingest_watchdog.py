#!/usr/bin/env python3
"""Recover missing daily ingest runs; --dry-run reports without dispatching."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys

CONFIG = Path(__file__).resolve().parent.parent / "_data/ingest_watchdog.json"
UTC = dt.timezone.utc


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def latest_run(workflow):
    repo = os.environ["GH_REPO"]
    response = json.loads(gh("api", f"repos/{repo}/actions/workflows/{workflow}/runs?per_page=1"))
    runs = response["workflow_runs"]
    return dt.datetime.fromisoformat(runs[0]["created_at"].replace("Z", "+00:00")) if runs else None


def dispatch(workflow):
    repo = os.environ["GH_REPO"]
    gh("api", "--method", "POST", f"repos/{repo}/actions/workflows/{workflow}/dispatches", "-f", "ref=main")


def check_window(window, now, dry_run):
    hour, minute = map(int, window["time_utc"].split(":"))
    start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if start > now:
        start -= dt.timedelta(days=1)
    age = now - start
    if age < dt.timedelta(minutes=window["grace_minutes"]) or age > dt.timedelta(minutes=window["max_age_minutes"]):
        return
    workflow = window["workflow"]
    latest = latest_run(workflow)
    if latest is not None and latest >= start:
        return
    if not dry_run:
        dispatch(workflow)
    print(f"{'Would recover' if dry_run else 'Recovered'} {workflow} window {start.isoformat()}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    windows = json.loads(CONFIG.read_text())["windows"]
    now = dt.datetime.now(UTC)
    failed = False
    for window in windows:
        try:
            check_window(window, now, args.dry_run)
        except (subprocess.CalledProcessError, ValueError, KeyError) as exc:
            print(f"{window['workflow']}: {exc}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
