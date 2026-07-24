from __future__ import annotations

import importlib.util
import hashlib
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
HOOK_PATH = PLUGIN_ROOT / "hooks" / "controller_gate.py"
HOOK_SPEC = importlib.util.spec_from_file_location("controller_gate", HOOK_PATH)
assert HOOK_SPEC and HOOK_SPEC.loader
controller_gate = importlib.util.module_from_spec(HOOK_SPEC)
HOOK_SPEC.loader.exec_module(controller_gate)


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "router-tests@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Router Tests"], check=True)
    (path / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "baseline"], check=True)


def complete_planning_contract(
    session: dict,
    repo: Path,
    state: Path,
    route_plan: dict | None = None,
) -> dict:
    route_plan = route_plan or {"workflow_id": "bound-plan"}
    script = state / "compiled-planning.js"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("return { status: 'PLAN_READY' }\n", encoding="utf-8")
    adaptive_core.register_compiled_workflow(
        session["session_id"],
        "planning",
        compilation_id="planning-compilation",
        workflow_id="planning-workflow",
        script_path=str(script),
        script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
        root=state,
    )
    transcript = state / "claude-session.jsonl"
    adaptive_core.record_workflow_launch(
        working_directory=str(repo),
        script_path=str(script),
        transcript_path=str(transcript),
        run_id="wf_planning",
        root=state,
    )
    record = transcript.with_suffix("") / "workflows" / "wf_planning.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        json.dumps(
            {
                "status": "completed",
                "result": {"status": "PLAN_READY", "route_plan": route_plan},
            }
        ),
        encoding="utf-8",
    )
    adaptive_core.session_status(session_id=session["session_id"], root=state)
    adaptive_core.bind_prepared_plan(
        session["session_id"],
        plan_id="a" * 32,
        workflow_id="bound-plan",
        plan_digest=adaptive_core.json_digest(route_plan),
        root=state,
    )
    return route_plan


def register_execution_contract(session: dict, state: Path) -> None:
    script = state / "compiled-execution.js"
    script.write_text("return { status: 'VERIFIED' }\n", encoding="utf-8")
    adaptive_core.register_compiled_workflow(
        session["session_id"],
        "execution",
        compilation_id="a" * 32,
        workflow_id="bound-plan",
        plan_id="a" * 32,
        script_path=str(script),
        script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
        root=state,
    )


class ControllerHookTests(unittest.TestCase):
    def test_post_workflow_parses_structured_run_id(self) -> None:
        hook_input = {
            "tool_name": "Workflow",
            "tool_input": {"scriptPath": "/tmp/registered.js"},
            "tool_response": {
                "tool_use_result": {
                    "runId": "wf_structured-7c9",
                    "status": "async_launched",
                }
            },
            "cwd": "/tmp/worktree",
            "transcript_path": "/tmp/session.jsonl",
        }
        with mock.patch.object(controller_gate, "record_workflow_launch") as record:
            controller_gate.post_tool(hook_input)
        record.assert_called_once_with(
            working_directory="/tmp/worktree",
            script_path="/tmp/registered.js",
            transcript_path="/tmp/session.jsonl",
            run_id="wf_structured-7c9",
        )

    def test_post_workflow_keeps_text_run_id_compatibility(self) -> None:
        hook_input = {
            "tool_name": "Workflow",
            "tool_input": {"scriptPath": "/tmp/registered.js"},
            "tool_response": "Workflow launched\nRun ID: wf_text-123\n",
            "cwd": "/tmp/worktree",
            "transcript_path": "/tmp/session.jsonl",
        }
        with mock.patch.object(controller_gate, "record_workflow_launch") as record:
            controller_gate.post_tool(hook_input)
        self.assertEqual(record.call_args.kwargs["run_id"], "wf_text-123")


class AdaptiveSessionTests(unittest.TestCase):
    def test_old_planning_protocol_recompiles_in_same_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            session = adaptive_core.start_session("upgrade planning", str(repo), state)
            script = state / "old-planning.js"
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text("return {}\n", encoding="utf-8")

            adaptive_core.register_compiled_workflow(
                session["session_id"],
                "planning",
                compilation_id="old-planning",
                workflow_id="old-planning",
                script_path=str(script),
                script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                protocol_version=adaptive_core.CONTROLLER_PROTOCOL_VERSION - 1,
                root=state,
            )
            stale = adaptive_core.session_status(
                session_id=session["session_id"],
                root=state,
            )
            self.assertTrue(stale["controller"]["needs_recompile"])
            self.assertIn("older AI Router protocol", stale["recovery_directive"])
            self.assertIn("same session", stale["recovery_directive"])

            adaptive_core.register_compiled_workflow(
                session["session_id"],
                "planning",
                compilation_id="new-planning",
                workflow_id="new-planning",
                script_path=str(script),
                script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                root=state,
            )
            current = adaptive_core.session_status(
                session_id=session["session_id"],
                root=state,
            )
            self.assertFalse(current["controller"]["needs_recompile"])

    def test_state_root_falls_back_to_claude_plugin_data_for_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin_data = Path(directory) / "plugin-data"
            with mock.patch.dict(
                os.environ,
                {
                    "AI_ROUTER_STATE_DIR": "",
                    "CLAUDE_PLUGIN_DATA": str(plugin_data),
                },
                clear=False,
            ):
                self.assertEqual(adaptive_core._state_root(), plugin_data)

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
            complete_planning_contract(session, repo, state)
            adaptive_core.checkpoint_session(
                session["session_id"], "READY_FOR_APPROVAL", "plan prepared", {}, state
            )
            register_execution_contract(session, state)
            adaptive_core.checkpoint_session(
                session["session_id"], "EXECUTING", "workflow compiled", {}, state
            )
            leases = list((state / "leases").glob("*.workflow.json"))
            self.assertEqual(len(leases), 1)
            lease = json.loads(leases[0].read_text(encoding="utf-8"))
            self.assertEqual(lease["session_id"], session["session_id"])

            adaptive_core.checkpoint_session(
                session["session_id"], "AWAITING_SCOPE_APPROVAL", "scope amendment required", {}, state
            )
            self.assertEqual(list((state / "leases").glob("*.workflow.json")), [])

    def test_complex_planning_can_grill_ask_and_resume_before_critique(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            session = adaptive_core.start_session("Design a risky migration", str(repo), state)
            adaptive_core.checkpoint_session(
                session["session_id"], "PLANNING", "soft planning", {}, state
            )
            adaptive_core.checkpoint_session(
                session["session_id"], "CRITIQUING", "soft criticism", {}, state
            )
            with self.assertRaisesRegex(ValueError, "prepared plan"):
                adaptive_core.checkpoint_session(
                    session["session_id"], "READY_FOR_APPROVAL", "soft prompt only", {}, state
                )
            complete_planning_contract(session, repo, state)
            updated = adaptive_core.checkpoint_session(
                session["session_id"], "READY_FOR_APPROVAL", "registered plan ready", {}, state
            )
            self.assertEqual(updated["state"], "READY_FOR_APPROVAL")

    def test_registered_route_plan_loads_exact_native_workflow_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            session = adaptive_core.start_session("Prepare without retranscription", str(repo), state)
            expected = {"workflow_id": "bound-plan", "commands": ["printf 'hello\\n'"]}
            complete_planning_contract(session, repo, state, expected)
            self.assertEqual(
                adaptive_core.registered_route_plan(session["session_id"], state),
                expected,
            )

            session_path = state / "sessions" / f"{session['session_id']}.json"
            payload = json.loads(session_path.read_text(encoding="utf-8"))
            payload["controller"]["planning"]["result_plan_digest"] = "0" * 64
            session_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest changed"):
                adaptive_core.registered_route_plan(session["session_id"], state)

    def test_controller_gate_blocks_serial_main_execution_but_allows_registered_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            session = adaptive_core.start_session("Build visibly", str(repo), state)
            main_hook = {
                "cwd": str(repo),
                "transcript_path": str(root / "main.jsonl"),
                "tool_name": "Bash",
                "tool_input": {"command": "codex exec 'implement it'"},
            }
            denied = adaptive_core.controller_tool_decision(main_hook, state)
            self.assertFalse(denied["allow"])
            self.assertIn("workflow-only", denied["reason"])

            inline = adaptive_core.controller_tool_decision(
                {**main_hook, "tool_name": "Workflow", "tool_input": {"script": "return {}"}},
                state,
            )
            self.assertFalse(inline["allow"])
            self.assertIn("inline Workflow", inline["reason"])

            unregistered_delegate = adaptive_core.controller_tool_decision(
                {
                    **main_hook,
                    "tool_name": "mcp__plugin_ai-router_ai-router__delegate",
                    "tool_input": {
                        "workflow_id": "unregistered",
                        "task_id": "planner",
                        "role": "planner",
                        "route": "corporate-pro",
                        "profile": "review",
                        "working_directory": str(repo),
                        "prompt": "Plan the task.",
                    },
                },
                state,
            )
            self.assertFalse(unregistered_delegate["allow"])

            subagent = adaptive_core.controller_tool_decision(
                {
                    **main_hook,
                    "transcript_path": str(root / "main" / "subagents" / "workflows" / "agent.jsonl"),
                },
                state,
            )
            self.assertTrue(subagent["allow"])

            script = state / "planning.js"
            script.write_text("return {}\n", encoding="utf-8")
            adaptive_core.register_compiled_workflow(
                session["session_id"],
                "planning",
                compilation_id="planning-gate",
                workflow_id="planning-gate",
                script_path=str(script),
                script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                root=state,
            )
            registered_delegate = adaptive_core.controller_tool_decision(
                {
                    **main_hook,
                    "tool_name": "mcp__plugin_ai-router_ai-router__delegate",
                    "tool_input": {
                        "workflow_id": "planning-gate",
                        "task_id": "planner",
                        "role": "planner",
                        "route": "corporate-pro",
                        "profile": "review",
                        "working_directory": str(repo),
                        "prompt": "Plan the task.",
                    },
                },
                state,
            )
            self.assertTrue(registered_delegate["allow"])
            wrong_worktree_delegate = adaptive_core.controller_tool_decision(
                {
                    **main_hook,
                    "tool_name": "mcp__plugin_ai-router_ai-router__delegate",
                    "tool_input": {
                        **registered_delegate,
                        "workflow_id": "planning-gate",
                        "task_id": "planner",
                        "role": "planner",
                        "route": "corporate-pro",
                        "profile": "review",
                        "working_directory": str(root),
                        "prompt": "Plan the task.",
                    },
                },
                state,
            )
            self.assertFalse(wrong_worktree_delegate["allow"])
            registered = adaptive_core.controller_tool_decision(
                {
                    **main_hook,
                    "tool_name": "Workflow",
                    "tool_input": {"scriptPath": str(script)},
                },
                state,
            )
            self.assertTrue(registered["allow"])
            script.write_text("tampered\n", encoding="utf-8")
            tampered = adaptive_core.controller_tool_decision(
                {
                    **main_hook,
                    "tool_name": "Workflow",
                    "tool_input": {"scriptPath": str(script)},
                },
                state,
            )
            self.assertFalse(tampered["allow"])
            self.assertIn("digest changed", tampered["reason"])

    def test_compaction_recovery_restores_exact_controller_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            session = adaptive_core.start_session("Long task", str(repo), state)
            recorded = adaptive_core.record_compaction(
                working_directory=str(repo),
                trigger="manual",
                compact_summary="secret-free compact summary",
                root=state,
            )
            self.assertEqual(recorded["session_id"], session["session_id"])
            context = adaptive_core.recovery_context(str(repo), state)
            self.assertIn(session["session_id"], context)
            self.assertIn("Compile and launch a registered Planning Workflow", context)

    def test_controller_gate_allows_exact_registered_execution_delegate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            session = adaptive_core.start_session("Execute visibly", str(repo), state)
            complete_planning_contract(session, repo, state)
            adaptive_core.checkpoint_session(
                session["session_id"],
                "READY_FOR_APPROVAL",
                "registered plan ready",
                {},
                state,
            )
            register_execution_contract(session, state)

            decision = adaptive_core.controller_tool_decision(
                {
                    "cwd": str(repo),
                    "transcript_path": str(root / "main.jsonl"),
                    "tool_name": "mcp__plugin_ai-router_ai-router__delegate",
                    "tool_input": {
                        "workflow_id": "bound-plan",
                        "task_id": "task-1",
                        "role": "worker",
                        "route": "minimax",
                        "profile": "build",
                        "working_directory": str(repo),
                        "prompt": "Implement the bounded task.",
                    },
                },
                state,
            )
            self.assertTrue(decision["allow"])
            self.assertIn("registered execution", decision["reason"])

    def test_controller_gate_recovers_registered_native_agent_tool_by_tool_use_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            state = root / "state"
            session = adaptive_core.start_session("Execute natively", str(repo), state)
            complete_planning_contract(session, repo, state)
            adaptive_core.checkpoint_session(
                session["session_id"],
                "READY_FOR_APPROVAL",
                "registered plan ready",
                {},
                state,
            )
            register_execution_contract(session, state)
            transcript = root / "main.jsonl"
            adaptive_core.record_workflow_launch(
                working_directory=str(repo),
                script_path=str(state / "compiled-execution.js"),
                transcript_path=str(transcript),
                run_id="wf_execution",
                root=state,
            )
            agent_directory = (
                transcript.with_suffix("")
                / "subagents"
                / "workflows"
                / "wf_execution"
            )
            agent_directory.mkdir(parents=True)
            (agent_directory / "agent-calibrator.jsonl").write_text(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "toolu_registered_agent_123",
                                    "name": "Bash",
                                }
                            ]
                        },
                    },
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            main_hook = {
                "cwd": str(repo),
                "transcript_path": str(transcript),
                "tool_name": "Bash",
                "tool_input": {"command": "git status --short"},
            }
            registered_agent = adaptive_core.controller_tool_decision(
                {**main_hook, "tool_use_id": "toolu_registered_agent_123"},
                state,
            )
            self.assertTrue(registered_agent["allow"])
            self.assertIn("registered execution workflow agent", registered_agent["reason"])

            unregistered_main = adaptive_core.controller_tool_decision(
                {**main_hook, "tool_use_id": "toolu_unregistered_main_123"},
                state,
            )
            self.assertFalse(unregistered_main["allow"])


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
    def test_check_suite_runs_in_order_and_stops_at_first_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            init_repo(repo)
            result = adaptive_core.run_check_suite(
                checks=[
                    {"command": "test -f tracked.txt"},
                    {"command": "test -f missing.txt"},
                    {"command": "exit 0"},
                ],
                working_directory=str(repo),
                level="targeted",
                workflow_id="suite-workflow",
                task_id="suite-task",
                root=root / "state",
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["checks_requested"], 3)
            self.assertEqual(result["checks_completed"], 2)
            self.assertEqual(len(result["results"]), 2)
            self.assertEqual(result["first_non_green"]["command"], "test -f missing.txt")

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
