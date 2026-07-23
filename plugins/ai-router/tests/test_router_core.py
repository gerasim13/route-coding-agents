from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = PLUGIN_ROOT / "mcp-server" / "router_core.py"
SPEC = importlib.util.spec_from_file_location("router_core", CORE_PATH)
assert SPEC and SPEC.loader
router_core = importlib.util.module_from_spec(SPEC)
sys.modules["router_core"] = router_core
SPEC.loader.exec_module(router_core)


def valid_plan(working_directory: str) -> dict:
    return {
        "schema_version": 2,
        "workflow_id": "test-workflow",
        "objective": "Implement and verify a bounded change",
        "working_directory": working_directory,
        "approval": {
            "premium_routes": [],
            "max_api_budget_usd": None,
            "allow_openrouter_primary": False,
        },
        "tasks": [
            {
                "id": "implementation",
                "objective": "Change one bounded component",
                "expected_artifact": "A passing implementation",
                "dependencies": [],
                "non_goals": ["No publication"],
                "allowed_paths": ["src", "tests"],
                "permission": "build",
                "complexity": "routine",
                "acceptance_checks": ["python3 -m unittest"],
                "routes": ["minimax", "corporate-pro", "codex-sol"],
                "verifier_routes": ["codex-luna", "claude-sonnet", "claude-best"],
            }
        ],
        "final_gate": {
            "routes": ["corporate-pro", "codex-sol", "claude-best"],
            "verifier_routes": ["codex-terra", "claude-opus", "codex-sol"],
            "acceptance_checks": ["python3 -m unittest"],
        },
    }


class PlanValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.directory = self.temp.name

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_accepts_valid_plan(self) -> None:
        plan = valid_plan(self.directory)
        self.assertIs(router_core.validate_plan(plan), plan)

    def test_rejects_dependency_cycle(self) -> None:
        plan = valid_plan(self.directory)
        second = dict(plan["tasks"][0])
        second.update({"id": "second", "dependencies": ["implementation"]})
        plan["tasks"][0]["dependencies"] = ["second"]
        plan["tasks"].append(second)
        with self.assertRaisesRegex(router_core.PlanValidationError, "cycle"):
            router_core.validate_plan(plan)

    def test_rejects_worker_without_independent_verifier(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["verifier_routes"] = ["minimax", "codex-terra", "claude-opus"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "independent"):
            router_core.validate_plan(plan)

    def test_rejects_weaker_verifier_after_escalation(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["verifier_routes"] = ["codex-luna"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "weaker"):
            router_core.validate_plan(plan)

    def test_rejects_unapproved_premium_route(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["routes"].append("kimi-k3")
        with self.assertRaisesRegex(router_core.PlanValidationError, "premium"):
            router_core.validate_plan(plan)

    def test_accepts_approved_premium_route(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["routes"].append("kimi-k3")
        plan["tasks"][0]["verifier_routes"].append("claude-opus")
        plan["approval"]["premium_routes"] = ["kimi-k3"]
        plan["approval"]["max_api_budget_usd"] = 1.0
        router_core.validate_plan(plan)

    def test_rejects_openrouter_as_silent_primary(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["routes"] = ["openrouter-cheap", "corporate-pro", "codex-sol"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "OpenRouter"):
            router_core.validate_plan(plan)

    def test_rejects_secret_path(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["allowed_paths"] = [".env.production"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "protected"):
            router_core.validate_plan(plan)

    def test_rejects_global_clean_worktree_final_gate(self) -> None:
        plan = valid_plan(self.directory)
        plan["final_gate"]["acceptance_checks"] = ["git status must show a clean worktree"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "globally clean worktree"):
            router_core.validate_plan(plan)

    def test_rejects_starting_routine_task_on_frontier(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["routes"] = ["codex-sol"]
        plan["tasks"][0]["verifier_routes"] = ["claude-opus"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "for routine complexity"):
            router_core.validate_plan(plan)

    def test_rejects_ladder_without_frontier_fallback(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["routes"] = ["minimax", "corporate-pro"]
        plan["tasks"][0]["verifier_routes"] = ["codex-luna", "claude-sonnet"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "frontier-capability fallback"):
            router_core.validate_plan(plan)

    def test_rejects_final_gate_without_frontier_fallback(self) -> None:
        plan = valid_plan(self.directory)
        plan["final_gate"]["routes"] = ["corporate-pro"]
        plan["final_gate"]["verifier_routes"] = ["codex-terra"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "final_gate.routes must end"):
            router_core.validate_plan(plan)

    def test_route_catalog_has_explicit_codex_model_and_effort_tiers(self) -> None:
        self.assertEqual(router_core.resolved_model("codex-luna"), "gpt-5.6-luna")
        self.assertEqual(router_core.ROUTES["codex-luna"].effort, "low")
        self.assertEqual(router_core.resolved_model("codex-terra"), "gpt-5.6-terra")
        self.assertEqual(router_core.ROUTES["codex-terra"].effort, "medium")
        self.assertEqual(router_core.resolved_model("codex-sol"), "gpt-5.6-sol")
        self.assertEqual(router_core.ROUTES["codex-sol"].effort, "high")
        self.assertEqual(router_core.resolved_model("codex"), "gpt-5.6-terra")
        self.assertEqual(router_core.resolved_model("codex-high"), "gpt-5.6-sol")
        self.assertEqual(router_core.ROUTES["claude-sonnet"].effort, "medium")
        self.assertEqual(router_core.ROUTES["claude-opus"].effort, "high")
        self.assertEqual(router_core.resolved_model("claude-best"), "best")
        self.assertEqual(router_core.ROUTES["claude-best"].effort, "high")
        self.assertIsNone(router_core.ROUTES["claude-haiku"].effort)

    def test_plan_summary_exposes_model_and_effort_ladders(self) -> None:
        summary = router_core.plan_summary(valid_plan(self.directory), "plan-id")
        first_worker = summary["tasks"][0]["worker_ladder"][0]
        self.assertEqual(first_worker["alias"], "minimax")
        first_verifier = summary["tasks"][0]["verifier_ladder"][0]
        self.assertEqual(first_verifier["model"], "gpt-5.6-luna")
        self.assertEqual(first_verifier["effort"], "low")


class DocumentationTests(unittest.TestCase):
    def test_activation_command_is_identical_in_readme_and_skills(self) -> None:
        exact_command = "/ai-router:workflow <software task>"
        readme = (PLUGIN_ROOT.parents[1] / "README.md").read_text(encoding="utf-8")
        portable_skill = (PLUGIN_ROOT.parents[1] / "SKILL.md").read_text(encoding="utf-8")
        workflow_skill = (PLUGIN_ROOT / "claude-skills" / "workflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(exact_command, readme)
        self.assertIn(exact_command, portable_skill)
        self.assertIn(f'argument-hint: "<software task>"', workflow_skill)


class CompileWorkflowTests(unittest.TestCase):
    def test_prepares_and_compiles_private_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            worktree = Path(directory) / "repo"
            worktree.mkdir()
            plan = valid_plan(str(worktree))
            with mock.patch.dict(os.environ, {"AI_ROUTER_STATE_DIR": str(state)}):
                prepared = router_core.prepare_plan(plan)
                compiled = router_core.compile_workflow(prepared["plan_id"], PLUGIN_ROOT / "workflow" / "execute.template.js")
            script = Path(compiled["script_path"])
            self.assertTrue(script.is_file())
            self.assertNotIn("/*__AI_ROUTER_PLAN__*/ null", script.read_text(encoding="utf-8"))
            self.assertNotIn("/*__AI_ROUTER_META__*/ null", script.read_text(encoding="utf-8"))
            self.assertIn('"workflow_id":"test-workflow"', script.read_text(encoding="utf-8"))
            self.assertTrue(script.read_text(encoding="utf-8").startswith("export const meta = {"))
            self.assertEqual(stat.S_IMODE(script.stat().st_mode), 0o600)
            checked = subprocess.run(["node", "--check", str(script)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(checked.returncode, 0, checked.stderr)

    def _compile(self, state: Path, plan: dict) -> Path:
        with mock.patch.dict(os.environ, {"AI_ROUTER_STATE_DIR": str(state)}):
            prepared = router_core.prepare_plan(plan)
            compiled = router_core.compile_workflow(prepared["plan_id"], PLUGIN_ROOT / "workflow" / "execute.template.js")
        return Path(compiled["script_path"])

    def test_mock_runtime_escalates_failed_worker_to_stronger_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            plan = valid_plan(str(worktree))
            script = self._compile(root / "state", plan)
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "escalate-once"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "VERIFIED")
            labels = result["labels"]
            self.assertTrue(any("worker:implementation:minimax:a1" in label for label in labels))
            self.assertTrue(any("repair:implementation:corporate-pro:a2" in label for label in labels))

    def test_mock_runtime_runs_ten_independent_workers_concurrently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            plan = valid_plan(str(worktree))
            prototype = plan["tasks"][0]
            plan["tasks"] = []
            for index in range(10):
                task = json.loads(json.dumps(prototype))
                task["id"] = f"task-{index}"
                plan["tasks"].append(task)
            script = self._compile(root / "state", plan)
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "success"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "VERIFIED")
            self.assertGreaterEqual(result["max_active"], 10)

    def test_final_gate_escalates_verifier_before_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            plan = valid_plan(str(worktree))
            script = self._compile(root / "state", plan)
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "final-gate-escalate"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "VERIFIED")
            labels = result["labels"]
            self.assertTrue(any("final-gate:final-gate:codex-terra:" in label for label in labels))
            self.assertTrue(any("final-gate:final-gate:claude-opus:" in label for label in labels))
            self.assertFalse(any("final-repair" in label for label in labels))

    def test_read_only_final_gate_never_repairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            plan = valid_plan(str(worktree))
            plan["tasks"][0]["permission"] = "review"
            script = self._compile(root / "state", plan)
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "final-gate-fail-all"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "BLOCKED")
            self.assertIn("read-only workflow", result["result"]["final_gate"]["blocker"])
            self.assertFalse(any("final-repair" in label for label in result["labels"]))


class ParserTests(unittest.TestCase):
    def test_parses_codex_jsonl(self) -> None:
        stdout = "\n".join(
            [
                json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}),
                json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 4, "cached_input_tokens": 3}}),
            ]
        )
        parsed = router_core.parse_agent_jsonl(stdout, "codex")
        self.assertEqual(parsed["output"], "done")
        self.assertEqual(parsed["usage"]["input_tokens"], 10)
        self.assertEqual(parsed["usage"]["cache_read_tokens"], 3)

    def test_parses_opencode_jsonl(self) -> None:
        text_event = {"type": "text", "part": {"id": "text-1", "type": "text", "text": "done"}}
        finish_event = {
            "type": "step_finish",
            "part": {"id": "step-1", "tokens": {"input": 20, "output": 5, "reasoning": 2, "cache": {"read": 8}}, "cost": 0.012},
        }
        stdout = "\n".join(json.dumps(event) for event in [text_event, text_event, finish_event, finish_event])
        parsed = router_core.parse_agent_jsonl(stdout, "opencode")
        self.assertEqual(parsed["output"], "done")
        self.assertEqual(parsed["usage"]["input_tokens"], 20)
        self.assertEqual(parsed["usage"]["reasoning_tokens"], 2)
        self.assertAlmostEqual(parsed["cost_usd"], 0.012)

    def test_parses_fenced_model_json_object(self) -> None:
        parsed = router_core.parse_model_json_object('```json\n{"verdict":"PASS","checks":[]}\n```')
        self.assertEqual(parsed, {"verdict": "PASS", "checks": []})


class RouterRunTests(unittest.TestCase):
    def test_codex_luna_dry_run_pins_model_and_low_effort(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [
                    str(PLUGIN_ROOT / "bin" / "router-run"),
                    "--profile",
                    "review",
                    "--model",
                    "codex-luna",
                    "--dir",
                    directory,
                    "--prompt",
                    "bounded check",
                    "--dry-run",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("model=gpt-5.6-luna", completed.stdout)
        self.assertIn("effort=low", completed.stdout)


class UsageAndDelegateTests(unittest.TestCase):
    def test_usage_aggregates_without_storing_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = root / "fake-runner"
            runner.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "print(json.dumps({'type':'text','part':{'id':'t','type':'text','text':'worker complete'}}))\n"
                "print(json.dumps({'type':'step_finish','part':{'id':'s','tokens':{'input':12,'output':3},'cost':0.02}}))\n",
                encoding="utf-8",
            )
            runner.chmod(0o700)
            worktree = root / "repo"
            worktree.mkdir()
            store = router_core.UsageStore(root / "state")
            arguments = {
                "workflow_id": "workflow-1",
                "task_id": "task-1",
                "role": "worker",
                "route": "cheap",
                "profile": "build",
                "working_directory": str(worktree),
                "prompt": "private task prompt",
                "timeout_seconds": 30,
            }
            with mock.patch.dict(os.environ, {"AI_ROUTER_RUNNER": str(runner)}):
                result = router_core.run_delegate(arguments, PLUGIN_ROOT, store)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["output"], "worker complete")
            raw_log = store.path.read_text(encoding="utf-8")
            self.assertNotIn("private task prompt", raw_log)
            aggregate = store.aggregate("day", "workflow-1")
            self.assertEqual(aggregate["external_calls"], 1)
            self.assertEqual(aggregate["usage"]["input_tokens"], 12)
            self.assertAlmostEqual(aggregate["known_external_cost_usd"], 0.02)

            router_core.record_verdict(
                {
                    "workflow_id": "workflow-1",
                    "task_id": "task-1",
                    "verdict": "pass",
                    "route": "codex",
                    "evidence": "tests passed",
                },
                store,
            )
            aggregate = store.aggregate("day", "workflow-1")
            self.assertEqual(aggregate["verdicts"], {"pass": 1, "fail": 0, "blocked": 0})
            self.assertNotIn("tests passed", store.path.read_text(encoding="utf-8"))

    def test_usage_skips_corrupt_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = router_core.UsageStore(Path(directory))
            store.path.write_text("not-json\n", encoding="utf-8")
            store.append(
                {
                    "event": "delegate",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "workflow_id": "w",
                    "route": "codex",
                    "status": "completed",
                    "usage": {},
                    "cost_usd": None,
                }
            )
            self.assertEqual(store.aggregate("all")["external_calls"], 1)

    def test_delegate_records_valid_verifier_output_in_same_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = root / "fake-runner"
            verdict = {
                "verdict": "PASS",
                "summary": "verified",
                "findings": [],
                "checks": ["mock-check"],
                "failure_packet": "",
            }
            runner.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                f"verdict = {verdict!r}\n"
                "print(json.dumps({'type':'text','part':{'id':'t','type':'text','text':json.dumps(verdict)}}))\n"
                "print(json.dumps({'type':'step_finish','part':{'id':'s','tokens':{'input':4,'output':2},'cost':0.0}}))\n",
                encoding="utf-8",
            )
            runner.chmod(0o700)
            worktree = root / "repo"
            worktree.mkdir()
            store = router_core.UsageStore(root / "state")
            arguments = {
                "workflow_id": "workflow-1",
                "task_id": "task-1",
                "role": "verifier",
                "route": "cheap",
                "profile": "verify",
                "working_directory": str(worktree),
                "prompt": "verify",
                "timeout_seconds": 30,
                "record_verdict_from_output": True,
            }
            with mock.patch.dict(os.environ, {"AI_ROUTER_RUNNER": str(runner)}):
                result = router_core.run_delegate(arguments, PLUGIN_ROOT, store)
            self.assertTrue(result["verdict_recorded"])
            self.assertEqual(store.aggregate("all", "workflow-1")["verdicts"]["pass"], 1)


class McpProtocolTests(unittest.TestCase):
    def test_server_lists_required_tools(self) -> None:
        process = subprocess.Popen(
            [sys.executable, str(PLUGIN_ROOT / "mcp-server" / "server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdin and process.stdout
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        for request in requests:
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
        initialized = json.loads(process.stdout.readline())
        listed = json.loads(process.stdout.readline())
        process.stdin.close()
        process.terminate()
        process.wait(timeout=5)
        assert process.stdout and process.stderr
        process.stdout.close()
        process.stderr.close()
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "ai-router")
        names = {tool["name"] for tool in listed["result"]["tools"]}
        self.assertTrue({"prepare_plan", "compile_workflow", "delegate", "usage", "health"}.issubset(names))


if __name__ == "__main__":
    unittest.main()
