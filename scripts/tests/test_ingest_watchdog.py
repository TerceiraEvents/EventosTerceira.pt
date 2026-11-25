import datetime as dt
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from scripts import ingest_watchdog as watchdog

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 25, 7, 0, tzinfo=UTC)
WINDOW = {"workflow": "ingest-cmah.yml", "time_utc": "06:00", "grace_minutes": 45, "max_age_minutes": 1440}


class WatchdogTests(unittest.TestCase):
    def test_missing_run_dry_run_and_live(self):
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run), patch.object(watchdog, "latest_run", return_value=dt.datetime(2026, 11, 24, 6, tzinfo=UTC)), patch.object(watchdog, "dispatch") as dispatch, patch("builtins.print") as output:
                watchdog.check_window(WINDOW, NOW, dry_run)
                self.assertEqual(dispatch.call_count, 0 if dry_run else 1)
                output.assert_called_once()
                self.assertIn("2026-11-25T06:00:00+00:00", output.call_args.args[0])

    @patch.dict("os.environ", {"GH_REPO": "owner/repo"})
    def test_live_api_calls_for_missing_and_fresh_runs(self):
        for created, expected in (("2026-11-24T06:00:00Z", 1), ("2026-11-25T06:01:00Z", 0)):
            response = json.dumps({"workflow_runs": [{"created_at": created}]})
            with self.subTest(created=created), patch.object(watchdog.subprocess, "check_output", return_value=response) as api, patch("builtins.print"):
                watchdog.check_window(WINDOW, NOW, False)
                posts = [call for call in api.call_args_list if "POST" in call.args[0]]
                self.assertEqual(len(posts), expected)

    def test_fresh_run_and_grace_do_not_dispatch(self):
        for now, latest in ((NOW, dt.datetime(2026, 11, 25, 6, tzinfo=UTC)), (dt.datetime(2026, 11, 25, 6, 44, tzinfo=UTC), None)):
            with self.subTest(now=now), patch.object(watchdog, "latest_run", return_value=latest), patch.object(watchdog, "dispatch") as dispatch:
                watchdog.check_window(WINDOW, now, False)
                dispatch.assert_not_called()

    @patch.dict("os.environ", {"GH_REPO": "owner/repo"})
    def test_latest_run_parses_any_event_and_empty_response(self):
        with patch.object(watchdog, "gh", return_value='{"workflow_runs": [{"created_at": "2026-11-25T06:00:00Z"}]}') as gh:
            self.assertEqual(watchdog.latest_run("ingest-cmah.yml"), dt.datetime(2026, 11, 25, 6, tzinfo=UTC))
            self.assertNotIn("event=", " ".join(gh.call_args.args))
        with patch.object(watchdog, "gh", return_value='{"workflow_runs": []}'):
            self.assertIsNone(watchdog.latest_run("ingest-cmah.yml"))

    @patch.dict("os.environ", {"GH_REPO": "owner/repo"})
    def test_dispatch_uses_workflow_dispatch_api(self):
        with patch.object(watchdog, "gh") as gh:
            watchdog.dispatch("ingest-cmah.yml")
            gh.assert_called_once_with("api", "--method", "POST", "repos/owner/repo/actions/workflows/ingest-cmah.yml/dispatches", "-f", "ref=main")

    def test_config_matches_scheduled_workflows(self):
        windows = json.loads(watchdog.CONFIG.read_text())["windows"]
        self.assertEqual(len(windows), 6)
        for window in windows:
            workflow = Path(".github/workflows") / window["workflow"]
            cron = re.search(r'cron: "(\d+) (\d+) \* \* \*"', workflow.read_text())
            self.assertIsNotNone(cron, window["workflow"])
            self.assertEqual(window["time_utc"], f"{int(cron[2]):02d}:{int(cron[1]):02d}")

    def test_expired_window_is_not_dispatched(self):
        window = dict(WINDOW, max_age_minutes=50)
        with patch.object(watchdog, "latest_run") as latest, patch.object(watchdog, "dispatch") as dispatch:
            watchdog.check_window(window, NOW, False)
            latest.assert_not_called()
            dispatch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
