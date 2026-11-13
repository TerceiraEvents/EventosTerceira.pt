"""Unit tests for the ingest-PR merge coordinator.

The pure classification logic (decide/latest_run/ingest_workflow/
report_body) is exercised against synthetic `gh` JSON payloads, the driver
against an injected fake `gh`, and the workflow contract against the real
files under .github/workflows/.

Run from the repo root:

    python -m unittest scripts.tests.test_merge_ingest_prs -v
"""
from __future__ import annotations

import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import merge_ingest_prs as m

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
WORKFLOWS = os.path.join(REPO_ROOT, ".github", "workflows")

SHA = "c6fdb8e0123456789012345678901234567890"


def pr(**overrides):
    base = {
        "number": 296,
        "title": "Auto-ingest: new events from CMAH",
        "headRefName": "auto/cmah-ingest",
        "headRefOid": SHA,
        "author": {"login": m.BOT},
        "isDraft": False,
        "isCrossRepository": False,
        "files": [{"path": "_data/special_events.yml"}],
    }
    base.update(overrides)
    return base


def run(gate, status="completed", conclusion="success", sha=SHA):
    return {
        "databaseId": 1,
        "headSha": sha,
        "status": status,
        "conclusion": conclusion,
        "url": f"https://example.test/runs/{gate}",
        "createdAt": "2026-01-01T00:00:00Z",
        "workflow": gate,
    }


def all_runs(**overrides):
    runs = {gate: run(gate) for gate in m.GATES}
    runs.update(overrides)
    return runs


WORKFLOW_FILES = {"ingest-cmah.yml", "ingest-cmpv.yml"}


class DecideTests(unittest.TestCase):
    def test_skip_cases(self):
        cases = [
            ("non-bot author", pr(author={"login": "chris"})),
            ("draft", pr(isDraft=True)),
            ("cross-repo", pr(isCrossRepository=True)),
            ("non-ingest branch", pr(headRefName="auto/cmah")),
            ("non-auto-ingest title", pr(title="new events from CMAH")),
            ("extra file touched", pr(files=[
                {"path": "_data/special_events.yml"},
                {"path": ".github/workflows/x.yml"},
            ])),
            ("no files", pr(files=[])),
        ]
        for name, item in cases:
            with self.subTest(case=name):
                decision = m.decide(item, [], all_runs(), WORKFLOW_FILES)
                self.assertEqual(decision.action, "skip")

    def test_skip_detail_lists_offending_paths(self):
        item = pr(files=[
            {"path": "_data/special_events.yml"},
            {"path": ".github/workflows/x.yml"},
        ])
        decision = m.decide(item, [], all_runs(), WORKFLOW_FILES)
        self.assertEqual(decision.action, "skip")
        self.assertIn(".github/workflows/x.yml", decision.detail)
        self.assertNotIn("_data/special_events.yml", decision.detail)

    def test_regenerate_when_main_moved(self):
        decision = m.decide(
            pr(), ["_data/special_events.yml"], all_runs(), WORKFLOW_FILES
        )
        self.assertEqual(decision, m.Decision("regenerate", ("ingest-cmah.yml",)))

    def test_regenerate_skips_when_workflow_missing(self):
        decision = m.decide(pr(), ["x.md"], all_runs(), {"ingest-cmpv.yml"})
        self.assertEqual(decision.action, "skip")

    def test_dispatch_missing_gates_in_order(self):
        runs = all_runs()
        runs["validate-events.yml"] = None
        runs["validate-ingesters.yml"] = None
        decision = m.decide(pr(), [], runs, WORKFLOW_FILES)
        self.assertEqual(decision.action, "dispatch")
        self.assertEqual(
            decision.detail, ("validate-events.yml", "validate-ingesters.yml")
        )

    def test_wait_on_incomplete_run(self):
        runs = all_runs()
        runs["validate-templates.yml"] = run(
            "validate-templates.yml", status="in_progress", conclusion=None
        )
        decision = m.decide(pr(), [], runs, WORKFLOW_FILES)
        self.assertEqual(decision.action, "wait")
        self.assertEqual(
            [r["workflow"] for r in decision.detail], ["validate-templates.yml"]
        )

    def test_report_on_failed_run(self):
        for conclusion in ("failure", "cancelled", "action_required"):
            with self.subTest(conclusion=conclusion):
                bad = run("validate-events.yml", conclusion=conclusion)
                runs = all_runs(**{"validate-events.yml": bad})
                decision = m.decide(pr(), [], runs, WORKFLOW_FILES)
                self.assertEqual(decision.action, "report")
                self.assertEqual(decision.detail, (bad,))

    def test_merge_when_all_pass(self):
        decision = m.decide(pr(), [], all_runs(), WORKFLOW_FILES)
        self.assertEqual(decision, m.Decision("merge"))


class LatestRunTests(unittest.TestCase):
    def test_picks_newest_matching_sha(self):
        runs = [
            {"headSha": "other", "createdAt": "2026-01-03"},
            {"headSha": SHA, "createdAt": "2026-01-02"},
            {"headSha": SHA, "createdAt": "2026-01-01"},
        ]
        self.assertEqual(m.latest_run(runs, SHA)["createdAt"], "2026-01-02")

    def test_ignores_other_shas_and_none_when_no_match(self):
        runs = [{"headSha": "abc"}, {"headSha": "def"}]
        self.assertIsNone(m.latest_run(runs, SHA))


class IngestWorkflowTests(unittest.TestCase):
    def test_maps_branch_to_workflow(self):
        self.assertEqual(
            m.ingest_workflow("auto/museu-angra-ingest"), "ingest-museu-angra.yml"
        )
        self.assertEqual(m.ingest_workflow("auto/cmah-ingest"), "ingest-cmah.yml")

    def test_non_ingest_branch(self):
        for branch in ("main", "auto/cmah", "feature/x", "auto/x-ingest/extra"):
            with self.subTest(branch=branch):
                self.assertIsNone(m.ingest_workflow(branch))


class ReportBodyTests(unittest.TestCase):
    def test_contains_marker_and_failed_run_urls(self):
        failed = [run("validate-templates.yml", conclusion="failure")]
        body = m.report_body(SHA, failed)
        self.assertIn(m.MARKER.format(sha=SHA), body)
        self.assertIn(SHA[:7], body)
        self.assertIn("https://example.test/runs/validate-templates.yml", body)
        self.assertIn("failure", body)


def load_workflow(name):
    with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class WorkflowContractTests(unittest.TestCase):
    def test_ingest_branch_matches_workflow_filename(self):
        names = sorted(
            f for f in os.listdir(WORKFLOWS)
            if f.startswith("ingest-") and f.endswith(".yml")
        )
        self.assertEqual(len(names), 7)
        for name in names:
            with self.subTest(workflow=name):
                data = load_workflow(name)
                branch = None
                for job in data["jobs"].values():
                    for step in job.get("steps", []):
                        if "create-pull-request" in str(step.get("uses", "")):
                            branch = step["with"]["branch"]
                slug = name[len("ingest-"):-len(".yml")]
                self.assertEqual(branch, f"auto/{slug}-ingest")

    def test_workflow_run_list_matches_ingest_names(self):
        ingest_names = {
            load_workflow(f)["name"]
            for f in os.listdir(WORKFLOWS)
            if f.startswith("ingest-") and f.endswith(".yml")
        }
        merge = load_workflow("merge-ingest-prs.yml")
        on = merge.get("on", merge.get(True))
        self.assertEqual(set(on["workflow_run"]["workflows"]), ingest_names)

    def test_each_gate_accepts_workflow_dispatch(self):
        for gate in m.GATES:
            with self.subTest(gate=gate):
                data = load_workflow(gate)
                on = data.get("on", data.get(True))
                self.assertIn("workflow_dispatch", on)


class DriverTests(unittest.TestCase):
    def test_merges_green_pr_and_dispatches_gates_on_main(self):
        calls = []

        def fake_gh(args):
            calls.append(args)
            if args[:2] == ["pr", "list"]:
                return [pr()]
            if args[:2] == ["pr", "view"]:
                return {"headRefOid": SHA, "state": "OPEN"}
            if args[0] == "api":
                return []
            if args[:2] == ["run", "list"]:
                return [run("gate")]
            return None

        exit_code = m.main([], gh_call=fake_gh, sleep=lambda s: None)
        self.assertEqual(exit_code, 0)
        self.assertIn(
            ["pr", "merge", "296", "--squash", "--match-head-commit", SHA],
            calls,
        )
        for gate in m.GATES:
            self.assertIn(["workflow", "run", gate, "--ref", "main"], calls)

    def test_no_duplicate_comment_when_marker_present(self):
        bad = run("validate-events.yml", conclusion="failure")
        gate_runs = {
            "validate-events.yml": [bad],
            "validate-templates.yml": [run("validate-templates.yml")],
            "validate-ingesters.yml": [run("validate-ingesters.yml")],
        }
        calls = []

        def fake_gh(args):
            calls.append(args)
            if args[:2] == ["pr", "list"]:
                return [pr()]
            if args[:2] == ["pr", "view"] and "comments" in args[-1]:
                return {
                    "comments": [{"body": m.MARKER.format(sha=SHA) + "\n..."}]
                }
            if args[:2] == ["pr", "view"]:
                return {"headRefOid": SHA, "state": "OPEN"}
            if args[0] == "api":
                return []
            if args[:2] == ["run", "list"]:
                gate = args[args.index("--workflow") + 1]
                return gate_runs.get(gate, [])
            return None

        exit_code = m.main([], gh_call=fake_gh, sleep=lambda s: None)
        self.assertEqual(exit_code, 0)
        self.assertFalse(
            any(c[:2] == ["pr", "comment"] for c in calls),
            "expected no new comment when the sha marker is already present",
        )
        self.assertFalse(any(c[:2] == ["pr", "merge"] for c in calls))


if __name__ == "__main__":
    unittest.main()
