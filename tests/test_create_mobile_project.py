from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "create-tuist-mobile-project" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import create_mobile_project as bpm  # type: ignore[import]

WIZARD_SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "create-tuist-mobile-project" / "scripts"
sys.path.insert(0, str(WIZARD_SCRIPT_DIR))

import create_mobile_project_wizard as wizard  # type: ignore[import]


def make_status(name: str, state: str, detail: str | None = None) -> bpm.CapabilityStatus:
    return bpm.CapabilityStatus(name=name, state=state, detail=detail or state)


class CapabilityDetectionTests(unittest.TestCase):
    @mock.patch("create_mobile_project.subprocess.run")
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


class InteractiveQuestionTests(unittest.TestCase):
    def test_mode_question_preserves_all_modes_and_marks_blocked_ones(self) -> None:
        statuses = [
            make_status("git", "available"),
            make_status("gh", "missing"),
            make_status("gh auth status", "missing"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "unauthenticated"),
        ]

        question = bpm.build_mode_question(statuses)

        self.assertEqual(question["id"], "mode")
        self.assertEqual([option["value"] for option in question["options"]], [
            "local-only",
            "github-backed",
            "github-and-tuist-cloud",
        ])
        self.assertEqual(question["options"][0]["availability"], "available")
        self.assertEqual(question["options"][1]["availability"], "blocked")
        self.assertIn("gh", question["options"][1]["blocked_reason"])
        self.assertEqual(question["options"][2]["availability"], "blocked")
        self.assertIn("tuist auth whoami", question["options"][2]["blocked_reason"])

    def test_template_question_can_render_as_request_user_input(self) -> None:
        question = bpm.build_template_question()

        self.assertTrue(bpm.can_render_request_user_input(question))
        payload = bpm.to_request_user_input_question(question)

        self.assertEqual(payload["header"], "Template")
        self.assertEqual(payload["id"], "template")
        self.assertEqual([option["label"] for option in payload["options"]], ["Pure iOS", "iOS + Catalyst"])

    def test_destination_strategy_question_can_render_as_request_user_input(self) -> None:
        question = bpm.build_destination_strategy_question("~/Downloads/Starter")

        self.assertTrue(bpm.can_render_request_user_input(question))
        payload = bpm.to_request_user_input_question(question)

        self.assertEqual(payload["header"], "Directory")
        self.assertIn("already exists", payload["question"])
        self.assertEqual([option["label"] for option in payload["options"]], ["Reuse", "Replace", "Abort"])

    def test_blocked_mode_question_refuses_request_user_input_mapping(self) -> None:
        statuses = [
            make_status("git", "available"),
            make_status("gh", "missing"),
            make_status("gh auth status", "missing"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available"),
        ]

        question = bpm.build_mode_question(statuses)

        self.assertFalse(bpm.can_render_request_user_input(question))
        with self.assertRaisesRegex(ValueError, "blocked options"):
            bpm.to_request_user_input_question(question)

    def test_codex_text_fallback_question_preserves_default(self) -> None:
        question = bpm.build_text_question(
            "project_name",
            "Project Name",
            "Choose the project name.",
            default="StarterApp",
        )

        payload = bpm.to_codex_text_fallback_question(question)

        self.assertEqual(payload["header"], "Project Name")
        self.assertEqual(payload["default"], "StarterApp")

    def test_claude_code_ask_user_question_renders_choice_prompt(self) -> None:
        prompt = bpm.to_claude_code_ask_user_question(
            bpm.build_template_question(),
            project_label="Zach-Skills",
            branch="feat/test",
            task_label="Choose template",
        )["prompt"]

        self.assertIn("Project: Zach-Skills", prompt)
        self.assertIn("RECOMMENDATION:", prompt)
        self.assertIn("A) Pure iOS", prompt)
        self.assertIn("B) iOS + Catalyst", prompt)

    def test_claude_code_ask_user_question_renders_text_prompt(self) -> None:
        prompt = bpm.to_claude_code_ask_user_question(
            bpm.build_text_question(
                "bundle_id",
                "Bundle Identifier",
                "Choose the bundle identifier.",
                default="com.example.app",
            ),
            project_label="Zach-Skills",
            branch="feat/test",
            task_label="Collect metadata",
        )["prompt"]

        self.assertIn("Default: com.example.app", prompt)
        self.assertIn("Reply with one value only.", prompt)

    def test_next_interview_question_walks_core_order(self) -> None:
        capabilities = [
            make_status("git", "available"),
            make_status("gh", "available"),
            make_status("gh auth status", "available"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available", "zach"),
        ]

        state: bpm.InterviewState = {}
        self.assertEqual(bpm.next_interview_question(capabilities=capabilities, state=state)["id"], "mode")
        state = bpm.apply_choice_answer(state, "mode", "github-and-tuist-cloud")
        self.assertEqual(bpm.next_interview_question(capabilities=capabilities, state=state)["id"], "template")
        state = bpm.apply_choice_answer(state, "template", "ios")
        self.assertEqual(bpm.next_interview_question(capabilities=capabilities, state=state)["id"], "project_name")

    def test_next_interview_question_handles_repo_exists_branch(self) -> None:
        capabilities = [
            make_status("git", "available"),
            make_status("gh", "available"),
            make_status("gh auth status", "available"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available", "zach"),
        ]
        state: bpm.InterviewState = {
            "mode": "github-backed",
            "template": "ios",
            "project_name": "Starter",
            "destination_path": "/tmp/starter",
            "owner": "zach",
            "repo_name": "starter",
            "repo_exists": True,
        }

        question = bpm.next_interview_question(capabilities=capabilities, state=state)
        self.assertEqual(question["id"], "repo_exists_resolution")

        state = bpm.apply_choice_answer(state, "repo_exists_resolution", "switch-to-local-only")
        self.assertEqual(state["mode"], "local-only")
        self.assertNotIn("owner", state)
        self.assertEqual(bpm.next_interview_question(capabilities=capabilities, state=state)["id"], "bundle_id")

    def test_next_interview_question_handles_cloud_handle_branch(self) -> None:
        capabilities = [
            make_status("git", "available"),
            make_status("gh", "available"),
            make_status("gh auth status", "available"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available", "zach"),
        ]
        state: bpm.InterviewState = {
            "mode": "github-and-tuist-cloud",
            "template": "ios",
            "project_name": "Starter",
            "destination_path": "/tmp/starter",
            "owner": "zach",
            "repo_name": "starter",
            "visibility": "private",
            "bundle_id": "com.example.starter",
            "ios_simulator_device": "iPhone 16",
            "create_tuist_cloud_project": True,
            "setup_tuist_cache": True,
        }

        question = bpm.next_interview_question(capabilities=capabilities, state=state, tuist_owner="zach")
        self.assertEqual(question["id"], "full_handle")
        self.assertEqual(question["default"], "zach/starter")

    def test_build_codex_interaction_question_returns_clickable_choice_when_safe(self) -> None:
        capabilities = [
            make_status("git", "available"),
            make_status("gh", "available"),
            make_status("gh auth status", "available"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available", "zach"),
        ]
        state: bpm.InterviewState = {"mode": "local-only"}

        payload = bpm.build_codex_interaction_question(capabilities=capabilities, state=state)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["id"], "template")
        self.assertEqual(len(payload["options"]), 2)

    def test_build_codex_interaction_question_returns_none_for_text_question(self) -> None:
        capabilities = [
            make_status("git", "available"),
            make_status("gh", "available"),
            make_status("gh auth status", "available"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available", "zach"),
        ]
        state: bpm.InterviewState = {
            "mode": "local-only",
            "template": "ios",
        }

        payload = bpm.build_codex_interaction_question(capabilities=capabilities, state=state)

        self.assertIsNone(payload)

    def test_build_codex_interaction_question_returns_none_for_blocked_choice(self) -> None:
        capabilities = [
            make_status("git", "available"),
            make_status("gh", "missing"),
            make_status("gh auth status", "missing"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available"),
        ]
        state: bpm.InterviewState = {}

        payload = bpm.build_codex_interaction_question(capabilities=capabilities, state=state)

        self.assertIsNone(payload)

    def test_build_claude_interaction_prompt_uses_next_question(self) -> None:
        capabilities = [
            make_status("git", "available"),
            make_status("gh", "available"),
            make_status("gh auth status", "available"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available", "zach"),
        ]
        state: bpm.InterviewState = {
            "mode": "github-backed",
            "template": "ios",
            "project_name": "Starter",
            "destination_path": "/tmp/starter",
        }

        prompt = bpm.build_claude_interaction_prompt(
            capabilities=capabilities,
            state=state,
            project_label="Zach-Skills",
            branch="feat/create-tuist-mobile-project-clickable-v3",
            task_label="Continue interview",
        )

        self.assertIsNotNone(prompt)
        assert prompt is not None
        self.assertIn("GitHub Owner", prompt)
        self.assertIn("Reply with one value only.", prompt)


class WizardHelpersTests(unittest.TestCase):
    def test_slugify_project_name(self) -> None:
        self.assertEqual(wizard.slugify_project_name("My App"), "my-app")
        self.assertEqual(wizard.slugify_project_name("___"), "app")

    def test_validators(self) -> None:
        self.assertIsNone(wizard.validate_project_name("My App"))
        self.assertIsNotNone(wizard.validate_project_name("!bad"))
        self.assertIsNone(wizard.validate_repo_owner("Zach677"))
        self.assertIsNotNone(wizard.validate_repo_owner("bad owner"))
        self.assertIsNone(wizard.validate_repo_name("starter-app"))
        self.assertIsNotNone(wizard.validate_repo_name("Starter App"))
        self.assertIsNone(wizard.validate_bundle_id("com.example.app"))
        self.assertIsNotNone(wizard.validate_bundle_id("badbundle"))

    def test_prompt_choice_rejects_blocked_option_then_accepts_available_one(self) -> None:
        question = bpm.build_mode_question(
            [
                make_status("git", "available"),
                make_status("gh", "missing"),
                make_status("gh auth status", "missing"),
                make_status("mise", "available"),
                make_status("tuist", "available"),
                make_status("tuist auth whoami", "available"),
            ]
        )
        answers = iter(["B", "A"])
        output = []

        choice = wizard.prompt_choice(
            question,
            input_fn=lambda _prompt: next(answers),
            output_fn=output.append,
        )

        self.assertEqual(choice, "local-only")
        self.assertTrue(any("blocked" in line for line in output))


class FakeWizardDependencies:
    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        self.last_payload = None
        self.last_approvals = None
        self.last_destination = None
        self.existing_repos: set[tuple[str, str]] = set()

    def detect_capabilities(self, _cwd: str | Path | None) -> list[bpm.CapabilityStatus]:
        return [
            make_status("git", "available"),
            make_status("gh", "available"),
            make_status("gh auth status", "available"),
            make_status("mise", "available"),
            make_status("tuist", "available"),
            make_status("tuist auth whoami", "available", "zach"),
        ]

    def build_payload(self, **kwargs):
        return bpm.build_payload(**kwargs)

    def clone_template(self, _template: str):
        return self.template_path, None

    def github_repo_exists(self, owner: str, repo_name: str) -> bool:
        return (owner, repo_name) in self.existing_repos

    def run_initializer(self, payload):
        self.last_payload = payload
        destination = Path(payload["destination_path"])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "mise.toml").write_text("[tools]\n", encoding="utf-8")
        return {"status": "ok", "destination_path": str(destination)}

    def execute_side_effects(self, *, payload, approvals, destination_path):
        self.last_payload = payload
        self.last_approvals = approvals
        self.last_destination = Path(destination_path)


class WizardFlowTests(unittest.TestCase):
    def test_run_wizard_local_only_builds_payload_and_reports_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            answers = iter(
                [
                    "A",  # local-only
                    "A",  # ios
                    "SkillSmokeApp",
                    "",   # default destination
                    "",   # default bundle id
                    "",   # default simulator
                    "n",  # no initial commit
                ]
            )
            template_dir = Path("/tmp/template")
            deps = FakeWizardDependencies(template_dir)
            output = io.StringIO()
            cwd = Path(tmpdir)

            code = wizard.run_wizard(
                cwd=cwd,
                repo_root=Path("/Users/star/Developer/zach-repo/Zach-Skills"),
                input_fn=lambda _prompt: next(answers),
                output_stream=output,
                dependencies=deps,
            )

            self.assertEqual(code, 0)
            self.assertEqual(deps.last_payload["mode"], "local-only")
            self.assertEqual(deps.last_payload["template"], "ios")
            self.assertEqual(deps.last_payload["project_name"], "SkillSmokeApp")
            self.assertEqual(deps.last_payload["bundle_id"], "com.example.skillsmokeapp")
            self.assertEqual(deps.last_payload["destination_path"], str(cwd / "SkillSmokeApp"))
            self.assertEqual(deps.last_approvals["create_github_repo"], "declined")
            self.assertEqual(deps.last_approvals["create_initial_commit"], "declined")
            self.assertIn("Project created.", output.getvalue())

    def test_run_wizard_repo_exists_can_fallback_to_local_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            answers = iter(
                [
                    "B",  # github-backed
                    "A",  # ios
                    "RepoExistsApp",
                    "",   # default destination
                    "Zach677",
                    "",   # default repo name
                    "n",  # do not choose another repo name
                    "A",  # switch to local-only
                    "",   # default bundle id
                    "",   # default simulator
                    "n",  # no initial commit
                ]
            )
            template_dir = Path("/tmp/template")
            deps = FakeWizardDependencies(template_dir)
            deps.existing_repos.add(("Zach677", "repoexistsapp"))
            output = io.StringIO()
            cwd = Path(tmpdir)

            code = wizard.run_wizard(
                cwd=cwd,
                repo_root=Path("/Users/star/Developer/zach-repo/Zach-Skills"),
                input_fn=lambda _prompt: next(answers),
                output_stream=output,
                dependencies=deps,
            )

            self.assertEqual(code, 0)
            self.assertEqual(deps.last_payload["mode"], "local-only")
            self.assertEqual(deps.last_approvals["create_github_repo"], "declined")
            self.assertIn("already exists on GitHub", output.getvalue())


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
        self.assertNotIn("full_handle", payload)
        self.assertNotIn("cache_service_slug", payload)

    def test_build_payload_only_derives_full_handle_for_cloud_or_cache(self) -> None:
        approvals = {
            "create_github_repo": "confirmed",
            "create_tuist_cloud_project": "declined",
            "setup_tuist_cache": "declined",
            "create_initial_commit": "declined",
            "push_after_init": "declined",
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

        self.assertNotIn("full_handle", payload)
        self.assertNotIn("cache_service_slug", payload)

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


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    def create_github_repo(self, owner: str, repo_name: str, visibility: str) -> None:
        self.calls.append(("create_github_repo", (owner, repo_name, visibility)))

    def tuist_project_create(self, destination: Path, full_handle: str) -> None:
        self.calls.append(("tuist_project_create", (destination, full_handle)))

    def tuist_setup_cache(self, destination: Path) -> None:
        self.calls.append(("tuist_setup_cache", (destination,)))

    def warm_external_cache(self, destination: Path) -> None:
        self.calls.append(("warm_external_cache", (destination,)))

    def mise_trust(self, mise_toml_path: Path) -> None:
        self.calls.append(("mise_trust", (mise_toml_path,)))

    def git_init(self, destination: Path) -> None:
        self.calls.append(("git_init", (destination,)))

    def git_add(self, destination: Path) -> None:
        self.calls.append(("git_add", (destination,)))

    def git_commit(self, destination: Path, message: str) -> None:
        self.calls.append(("git_commit", (destination, message)))

    def git_push(self, destination: Path) -> None:
        self.calls.append(("git_push", (destination,)))

    def git_remote_add(self, destination: Path, remote_name: str, remote_url: str) -> None:
        self.calls.append(("git_remote_add", (destination, remote_name, remote_url)))


class SideEffectSequenceTests(unittest.TestCase):
    def _run_sequence(self, approvals: dict[str, str], **payload_kwargs) -> FakeExecutor:
        approvals = {**approvals}
        payload = bpm.build_payload(**payload_kwargs, approvals=approvals)
        destination = Path(payload["destination_path"])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "mise.toml").write_text("[tools]\n", encoding="utf-8")
        executor = FakeExecutor()
        bpm.execute_side_effects(
            payload=payload,
            approvals=approvals,
            destination_path=destination,
            executor=executor,
        )
        return executor

    def test_local_only_sequence_runs_cache_then_git(self) -> None:
        approvals = bpm.collect_approvals()
        approvals.update(
            {
                "create_github_repo": "declined",
                "create_tuist_cloud_project": "declined",
                "setup_tuist_cache": "declined",
                "create_initial_commit": "confirmed",
                "push_after_init": "confirmed",
            }
        )

        executor = self._run_sequence(
            approvals,
            mode="local-only",
            template="ios",
            template_source_path="/tmp/template",
            destination_path="/tmp/project",
            destination_strategy="create",
            project_name="SubPanda",
            bundle_id="org.zach.subpanda",
            ios_simulator_device="iPhone 16",
        )

        expected_path = Path("/tmp/project").resolve()
        expected = [
            ("mise_trust", (expected_path / "mise.toml",)),
            ("warm_external_cache", (expected_path,)),
            ("git_init", (expected_path,)),
            ("git_add", (expected_path,)),
            ("git_commit", (expected_path, "Initial commit")),
        ]
        self.assertEqual(expected, executor.calls)

    def test_github_backed_sequence_creates_repo_and_pushes(self) -> None:
        approvals = bpm.collect_approvals()
        approvals.update(
            {
                "create_github_repo": "confirmed",
                "create_tuist_cloud_project": "declined",
                "setup_tuist_cache": "declined",
                "create_initial_commit": "confirmed",
                "push_after_init": "confirmed",
            }
        )

        executor = self._run_sequence(
            approvals,
            mode="github-backed",
            template="ios",
            template_source_path="/tmp/template",
            destination_path="/tmp/github",
            destination_strategy="create",
            project_name="Starter",
            bundle_id="org.example.starter",
            ios_simulator_device="iPhone 16",
            owner="zach",
            repo_name="starter",
            visibility="public",
        )

        expected_names = [call[0] for call in executor.calls]
        self.assertIn("create_github_repo", expected_names)
        self.assertIn("git_remote_add", expected_names)
        self.assertIn("mise_trust", expected_names)
        self.assertNotIn("tuist_project_create", expected_names)
        self.assertNotIn("tuist_setup_cache", expected_names)
        self.assertIn("git_push", expected_names)

    def test_cloud_sequence_runs_tuist_commands_and_skips_push(self) -> None:
        approvals = bpm.collect_approvals()
        approvals.update(
            {
                "create_github_repo": "confirmed",
                "create_tuist_cloud_project": "confirmed",
                "setup_tuist_cache": "confirmed",
                "create_initial_commit": "confirmed",
                "push_after_init": "declined",
            }
        )

        executor = self._run_sequence(
            approvals,
            mode="github-and-tuist-cloud",
            template="ios-catalyst",
            template_source_path="/tmp/template",
            destination_path="/tmp/cloud",
            destination_strategy="create",
            project_name="Starter",
            bundle_id="org.example.starter",
            ios_simulator_device="iPhone 16",
            owner="zach",
            repo_name="starter",
            visibility="private",
        )

        names = [call[0] for call in executor.calls]
        self.assertEqual(names[0], "mise_trust")
        self.assertIn("git_remote_add", names)
        self.assertIn("mise_trust", names)
        self.assertIn("tuist_project_create", names)
        self.assertIn("tuist_setup_cache", names)
        self.assertTrue("git_push" not in names)
        self.assertLess(names.index("git_init"), names.index("git_remote_add"))

        remote_call = next(call for call in executor.calls if call[0] == "git_remote_add")
        self.assertEqual(remote_call[1][2], "https://github.com/zach/starter.git")

    def test_cache_setup_can_run_without_cloud_creation_when_handle_exists(self) -> None:
        approvals = bpm.collect_approvals()
        approvals.update(
            {
                "create_github_repo": "declined",
                "create_tuist_cloud_project": "declined",
                "setup_tuist_cache": "confirmed",
                "create_initial_commit": "declined",
                "push_after_init": "declined",
            }
        )

        executor = self._run_sequence(
            approvals,
            mode="github-and-tuist-cloud",
            template="ios",
            template_source_path="/tmp/template",
            destination_path="/tmp/cloud",
            destination_strategy="create",
            project_name="Starter",
            bundle_id="org.example.starter",
            ios_simulator_device="iPhone 16",
            owner="zach",
            repo_name="starter",
            visibility="private",
            full_handle="zach/starter",
        )

        names = [call[0] for call in executor.calls]
        self.assertNotIn("tuist_project_create", names)
        self.assertIn("tuist_setup_cache", names)

    def test_requires_explicit_github_approval(self) -> None:
        approvals = {
            "create_github_repo": "not_asked",
            "create_tuist_cloud_project": "declined",
            "setup_tuist_cache": "declined",
            "create_initial_commit": "declined",
            "push_after_init": "declined",
        }

        payload: dict[str, object] = {
            "mode": "github-backed",
            "template": "ios",
            "template_source_path": "/tmp/template",
            "destination_path": "/tmp/github",
            "destination_strategy": "create",
            "project_name": "Starter",
            "bundle_id": "org.example.starter",
            "ios_simulator_device": "iPhone 16",
            "create_initial_commit": False,
            "push_after_init": False,
            "setup_tuist_cloud": False,
            "setup_tuist_cache": False,
            "owner": "zach",
            "repo_name": "starter",
            "visibility": "private",
        }

        with self.assertRaisesRegex(ValueError, "GitHub repo creation"):
            bpm.execute_side_effects(
                payload=payload,
                approvals=approvals,
                destination_path=Path("/tmp/github"),
                executor=FakeExecutor(),
            )

    def test_requires_explicit_cloud_approval_before_cloud_side_effects(self) -> None:
        approvals = {
            "create_github_repo": "declined",
            "create_tuist_cloud_project": "not_asked",
            "setup_tuist_cache": "confirmed",
            "create_initial_commit": "declined",
            "push_after_init": "declined",
        }
        payload = bpm.build_payload(
            mode="github-and-tuist-cloud",
            template="ios",
            template_source_path="/tmp/template",
            destination_path="/tmp/cloud",
            destination_strategy="create",
            project_name="Starter",
            bundle_id="org.example.starter",
            ios_simulator_device="iPhone 16",
            approvals={
                "create_github_repo": "declined",
                "create_tuist_cloud_project": "confirmed",
                "setup_tuist_cache": "confirmed",
                "create_initial_commit": "declined",
                "push_after_init": "declined",
            },
            owner="zach",
            repo_name="starter",
            visibility="private",
        )

        with self.assertRaisesRegex(ValueError, "Tuist Cloud project creation"):
            bpm.execute_side_effects(
                payload=payload,
                approvals=approvals,
                destination_path=Path("/tmp/cloud"),
                executor=FakeExecutor(),
            )


if __name__ == "__main__":
    unittest.main()
