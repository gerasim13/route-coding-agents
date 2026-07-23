from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ADAPTIVE_PATH = PLUGIN_ROOT / "mcp-server" / "adaptive_core.py"
SPEC = importlib.util.spec_from_file_location("adaptive_core", ADAPTIVE_PATH)
assert SPEC and SPEC.loader
adaptive_core = importlib.util.module_from_spec(SPEC)
sys.modules["adaptive_core"] = adaptive_core
SPEC.loader.exec_module(adaptive_core)


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "router-tests@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Router Tests"], check=True)
    (path / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "baseline"], check=True)


class AdaptiveSessionTests(unittest.TestCase):
    def test_start_resumes_active_session_for_same_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"

            first = adaptive_core.start_session("Implement feature", str(repo), state)
            resumed = adaptive_core.start_session("A different prompt", str(repo), state)

            self.assertFalse(first["resumed"])
            self.assertTrue(resumed["resumed"])
            self.assertEqual(resumed["session_id"], first["session_id"])
            self.assertEqual(resumed["objective"], "Implement feature")
            self.assertEqual(resumed["state"], "INSPECTING")

    def test_checkpoint_enforces_state_machine_and_redacts_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            session = adaptive_core.start_session("Investigate", str(repo), state)

            updated = adaptive_core.checkpoint_session(
                session["session_id"],
                "DISCOVERING",
                "Found Authorization: Bearer sk-example-secret-value",
                {"decision": "token=super-secret-value"},
                state,
            )
            self.assertEqual(updated["state"], "DISCOVERING")
            raw = (state / "sessions" / f"{session['session_id']}.json").read_text(encoding="utf-8")
            self.assertNotIn("sk-example-secret-value", raw)
            self.assertNotIn("super-secret-value", raw)

            with self.assertRaisesRegex(ValueError, "invalid session transition"):
                adaptive_core.checkpoint_session(session["session_id"], "VERIFIED", "", {}, state)

    def test_terminal_session_allows_new_session_in_same_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            first = adaptive_core.start_session("First", str(repo), state)
            adaptive_core.checkpoint_session(first["session_id"], "BLOCKED", "real blocker", {}, state)
            second = adaptive_core.start_session("Second", str(repo), state)
            self.assertNotEqual(first["session_id"], second["session_id"])
            self.assertFalse(second["resumed"])

    def test_execution_checkpoint_holds_and_releases_one_worktree_lease(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            session = adaptive_core.start_session("Build", str(repo), state)
            for next_state in ("PLANNING", "CRITIQUING", "READY_FOR_APPROVAL", "EXECUTING"):
                adaptive_core.checkpoint_session(session["session_id"], next_state, next_state, {}, state)
            leases = list((state / "leases").glob("*.workflow.json"))
            self.assertEqual(len(leases), 1)
            lease = json.loads(leases[0].read_text(encoding="utf-8"))
            self.assertEqual(lease["session_id"], session["session_id"])

            adaptive_core.checkpoint_session(
                session["session_id"], "AWAITING_SCOPE_APPROVAL", "scope amendment required", {}, state
            )
            self.assertEqual(list((state / "leases").glob("*.workflow.json")), [])


class WorkspaceInspectionTests(unittest.TestCase):
    def test_fingerprint_changes_with_tracked_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            init_repo(repo)
            before = adaptive_core.workspace_fingerprint(repo)
            (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
            after = adaptive_core.workspace_fingerprint(repo)
            self.assertNotEqual(before, after)

    def test_inspection_detects_candidate_commands_without_running_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            init_repo(repo)
            (repo / "package.json").write_text(
                json.dumps({"scripts": {"test": "vitest", "lint": "eslint .", "build": "vite build"}}),
                encoding="utf-8",
            )
            result = adaptive_core.inspect_workspace(str(repo))
            commands = {item["command"] for item in result["candidate_checks"]}
            self.assertIn("npm run test", commands)
            self.assertIn("npm run lint", commands)
            self.assertIn("npm run build", commands)
            self.assertEqual(result["working_directory"], str(repo.resolve()))
            self.assertTrue(result["head"])


class CheckRunnerTests(unittest.TestCase):
    def test_successful_check_records_stable_structured_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            result = adaptive_core.run_check(
                command="test -f tracked.txt",
                working_directory=str(repo),
                level="targeted",
                workflow_id="workflow-1",
                task_id="task-1",
                state_root=root / "state",
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["return_code"], 0)
            self.assertFalse(result["workspace_changed"])
            self.assertEqual(result["attempts"], 1)
            log_path = Path(result["log_path"])
            self.assertTrue(log_path.is_file())
            self.assertEqual(stat.S_IMODE(log_path.stat().st_mode), 0o600)

    def test_failure_runs_one_explicit_rerun_and_redacts_logs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            result = adaptive_core.run_check(
                command="printf 'Authorization: Bearer sk-example-secret-value\\n' >&2; exit 7",
                rerun_command="printf 'same assertion failed\\n' >&2; exit 7",
                working_directory=str(repo),
                level="targeted",
                workflow_id="workflow-1",
                task_id="task-1",
                state_root=root / "state",
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["attempts"], 2)
            self.assertTrue(result["rerun_performed"])
            self.assertTrue(result["failure_signature"])
            payload = json.dumps(result)
            self.assertNotIn("sk-example-secret-value", payload)
            self.assertNotIn("sk-example-secret-value", Path(result["log_path"]).read_text(encoding="utf-8"))

    def test_source_change_during_check_invalidates_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            result = adaptive_core.run_check(
                command="printf 'mutated\\n' >> tracked.txt",
                working_directory=str(repo),
                level="affected",
                workflow_id="workflow-1",
                task_id="task-1",
                state_root=root / "state",
            )
            self.assertEqual(result["status"], "STALE")
            self.assertTrue(result["workspace_changed"])

    def test_dangerous_or_secret_reading_commands_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            init_repo(repo)
            for command in (
                "git reset --hard",
                "rm -rf build",
                "sed -n '1p' .env",
                "sed -n '1p' /tmp/project/.env.production",
            ):
                with self.subTest(command=command):
                    with self.assertRaisesRegex(ValueError, "forbidden"):
                        adaptive_core.run_check(
                            command=command,
                            working_directory=str(repo),
                            level="targeted",
                            workflow_id="workflow-1",
                            task_id="task-1",
                            state_root=repo / "state",
                        )

    def test_check_environment_does_not_expose_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            secret = "unique-environment-secret-12345"
            with mock.patch.dict(os.environ, {"AI_ROUTER_TEST_API_TOKEN": secret}):
                result = adaptive_core.run_check(
                    command="printf '%s' \"$AI_ROUTER_TEST_API_TOKEN\"",
                    working_directory=str(repo),
                    level="targeted",
                    workflow_id="workflow-1",
                    task_id="task-1",
                    state_root=root / "state",
                )
            self.assertEqual(result["status"], "PASS")
            self.assertNotIn(secret, json.dumps(result))
            self.assertNotIn(secret, Path(result["log_path"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
