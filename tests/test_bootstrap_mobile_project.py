from __future__ import annotations

import sys
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "bootstrap-tuist-mobile-project" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import bootstrap_mobile_project as bpm  # type: ignore[import]


def make_status(name: str, state: str, detail: str | None = None) -> bpm.CapabilityStatus:
    return bpm.CapabilityStatus(name=name, state=state, detail=detail or state)


class CapabilityDetectionTests(unittest.TestCase):
    @mock.patch("bootstrap_mobile_project.subprocess.run")
    def test_detect_capabilities_records_states(self, fake_run) -> None:
        fake_run.side_effect = [
            CompletedProcess((), 0, stdout="git version 2.x", stderr=""),
            FileNotFoundError(),
            FileNotFoundError(),
            CompletedProcess((), 0, stdout="mise 0.1", stderr=""),
            CompletedProcess((), 0, stdout="tuist 3.0", stderr=""),
            CompletedProcess((), 1, stdout="", stderr="not signed in"),
        ]

        statuses = bpm.detect_capabilities("/tmp/project-root")

        self.assertEqual(statuses[0].name, "git")
        self.assertEqual(statuses[0].state, "available")
        self.assertEqual(statuses[1].name, "gh")
        self.assertEqual(statuses[1].state, "missing")
        self.assertEqual(statuses[2].name, "gh auth status")
        self.assertEqual(statuses[2].state, "missing")
        self.assertEqual(statuses[-1].name, "tuist auth whoami")
        self.assertEqual(statuses[-1].state, "unauthenticated")


class ModeBlockerTests(unittest.TestCase):
    def test_blocked_modes_report_missing_tools(self) -> None:
        statuses = [
            make_status("git", "available"),
            make_status("gh", "missing"),
            make_status("gh auth status", "missing"),
            make_status("mise", "missing"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available"),
        ]

        blockers = bpm.describe_mode_blockers(statuses)

        self.assertListEqual(blockers["local-only"], ["mise"])
        self.assertListEqual(blockers["github-backed"], ["mise", "gh", "gh auth status"])
        self.assertListEqual(blockers["github-and-tuist-cloud"], ["mise", "gh", "gh auth status"])

    def test_mode_messages_explain_blocked_modes(self) -> None:
        statuses = [
            make_status("git", "available"),
            make_status("gh", "missing"),
            make_status("gh auth status", "missing"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "unauthenticated"),
        ]

        messages = bpm.describe_mode_messages(statuses)

        self.assertEqual(messages["local-only"], "available")
        self.assertIn("gh", messages["github-backed"])
        self.assertIn("tuist auth whoami", messages["github-and-tuist-cloud"])

    def test_mode_validation_raises_when_blocked(self) -> None:
        statuses = [
            make_status("git", "available"),
            make_status("gh", "missing"),
            make_status("gh auth status", "missing"),
            make_status("mise", "missing"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available"),
        ]

        with self.assertRaisesRegex(ValueError, "gh"):
            bpm.ensure_mode_capabilities("github-backed", statuses)


class PayloadAndApprovalTests(unittest.TestCase):
    def test_collect_approvals_defaults_to_not_asked(self) -> None:
        approvals = bpm.collect_approvals()
        self.assertEqual(approvals["create_github_repo"], "not_asked")
        self.assertEqual(approvals["create_tuist_cloud_project"], "not_asked")
        self.assertEqual(approvals["setup_tuist_cache"], "not_asked")
        self.assertEqual(approvals["create_initial_commit"], "not_asked")
        self.assertEqual(approvals["push_after_init"], "not_asked")

    def test_require_confirmed_approval_rejects_not_asked(self) -> None:
        approvals = bpm.collect_approvals()

        with self.assertRaisesRegex(ValueError, "explicit approval"):
            bpm.require_confirmed_approval(approvals, "create_github_repo", "repo creation")

    def test_require_confirmed_approval_accepts_confirmed(self) -> None:
        approvals = bpm.collect_approvals()
        approvals["create_github_repo"] = "confirmed"

        bpm.require_confirmed_approval(approvals, "create_github_repo", "repo creation")

    def test_build_payload_includes_approvals_and_optional_fields(self) -> None:
        approvals = {
            "create_github_repo": "confirmed",
            "create_tuist_cloud_project": "not_asked",
            "setup_tuist_cache": "not_asked",
            "create_initial_commit": "confirmed",
            "push_after_init": "declined",
        }

        payload = bpm.build_payload(
            mode="github-backed",
            template="ios",
            template_source_path="/tmp/template",
            destination_path="/tmp/out",
            destination_strategy="create",
            project_name="SubPanda",
            bundle_id="org.zach.subpanda",
            ios_simulator_device="iPhone 16",
            approvals=approvals,
            owner="zach",
            repo_name="subpanda",
            visibility="public",
            full_handle="zach/subpanda",
            cache_service_slug="zach-subpanda",
        )

        self.assertEqual(payload["mode"], "github-backed")
        self.assertTrue(payload["create_initial_commit"])
        self.assertFalse(payload["push_after_init"])
        self.assertEqual(payload["visibility"], "public")
        self.assertEqual(payload["cache_service_slug"], "zach-subpanda")
        self.assertFalse(payload["setup_tuist_cloud"])
        self.assertFalse(payload["setup_tuist_cache"])

    def test_build_payload_only_enables_cloud_flags_for_cloud_mode(self) -> None:
        approvals = {
            "create_github_repo": "confirmed",
            "create_tuist_cloud_project": "confirmed",
            "setup_tuist_cache": "confirmed",
            "create_initial_commit": "declined",
            "push_after_init": "declined",
        }

        payload = bpm.build_payload(
            mode="github-and-tuist-cloud",
            template="ios-catalyst",
            template_source_path="/tmp/template",
            destination_path="/tmp/out",
            destination_strategy="create",
            project_name="Starter",
            bundle_id="org.example.starter",
            ios_simulator_device="iPhone 16",
            approvals=approvals,
            owner="zach",
            repo_name="starter",
            visibility="private",
        )

        self.assertTrue(payload["setup_tuist_cloud"])
        self.assertTrue(payload["setup_tuist_cache"])

    def test_build_payload_disables_push_without_commit(self) -> None:
        approvals = {
            "create_github_repo": "confirmed",
            "create_tuist_cloud_project": "declined",
            "setup_tuist_cache": "declined",
            "create_initial_commit": "declined",
            "push_after_init": "confirmed",
        }

        payload = bpm.build_payload(
            mode="github-backed",
            template="ios",
            template_source_path="/tmp/template",
            destination_path="/tmp/out",
            destination_strategy="create",
            project_name="Starter",
            bundle_id="org.example.starter",
            ios_simulator_device="iPhone 16",
            approvals=approvals,
            owner="zach",
            repo_name="starter",
            visibility="private",
        )

        self.assertFalse(payload["create_initial_commit"])
        self.assertFalse(payload["push_after_init"])

    def test_build_payload_rejects_unresolved_approvals(self) -> None:
        approvals = bpm.collect_approvals()
        approvals["create_github_repo"] = "declined"
        approvals["create_tuist_cloud_project"] = "declined"
        approvals["setup_tuist_cache"] = "declined"

        with self.assertRaisesRegex(ValueError, "Approvals are unresolved"):
            bpm.build_payload(
                mode="local-only",
                template="ios",
                template_source_path="/tmp/template",
                destination_path="/tmp/out",
                destination_strategy="create",
                project_name="Starter",
                bundle_id="org.example.starter",
                ios_simulator_device="iPhone 16",
                approvals=approvals,
            )


if __name__ == "__main__":
    unittest.main()
