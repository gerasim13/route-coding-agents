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
        "schema_version": 4,
        "workflow_id": "test-workflow",
        "objective": "Implement and verify a bounded change",
        "working_directory": working_directory,
        "planning": {
            "mode": "adaptive",
            "session_id": "0123456789abcdef0123456789abcdef",
            "discovery_performed": True,
            "planner_route": "codex-sol",
            "critic_route": "claude-opus",
            "critic_verdict": "PASS",
            "assumptions": [],
            "grill": {
                "level": "routine",
                "required": False,
                "signals": [],
                "routes": [],
                "roles": [],
                "rounds": 0,
                "open_blockers": [],
                "verdict": "SKIPPED",
            },
        },
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
                "diagnosis_routes": ["corporate-pro", "codex-sol"],
                "test_intent_verifier_routes": ["codex-terra", "claude-opus"],
                "test_plan": {
                    "targeted": [{"command": "python3 -m unittest tests.test_unit"}],
                    "affected": [{"command": "python3 -m unittest", "rerun_command": "python3 -m unittest"}],
                },
            }
        ],
        "final_gate": {
            "routes": ["corporate-pro", "codex-sol", "claude-best"],
            "verifier_routes": ["codex-terra", "claude-opus", "codex-sol"],
            "diagnosis_routes": ["corporate-pro", "codex-sol"],
            "acceptance_checks": ["python3 -m unittest"],
            "test_plan": {
                "regression": [{"command": "python3 -m unittest", "rerun_command": "python3 -m unittest"}],
            },
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

    def test_rejects_planning_pair_weaker_than_task_or_same_provider(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["complexity"] = "strong"
        plan["tasks"][0]["routes"] = ["corporate-pro", "codex-sol"]
        plan["tasks"][0]["verifier_routes"] = ["codex-terra", "claude-opus"]
        plan["tasks"][0]["test_intent_verifier_routes"] = ["codex-terra", "claude-opus"]
        plan["planning"]["planner_route"] = "codex-luna"
        with self.assertRaisesRegex(router_core.PlanValidationError, "weaker"):
            router_core.validate_plan(plan)

        plan = valid_plan(self.directory)
        plan["planning"]["critic_route"] = "codex-high"
        with self.assertRaisesRegex(router_core.PlanValidationError, "independent"):
            router_core.validate_plan(plan)

    def test_rejects_unapproved_or_unpassed_plan_critique(self) -> None:
        plan = valid_plan(self.directory)
        plan["planning"]["critic_verdict"] = "FAIL"
        with self.assertRaisesRegex(router_core.PlanValidationError, "critic_verdict"):
            router_core.validate_plan(plan)

    def test_strong_plan_requires_completed_adversarial_grill(self) -> None:
        plan = valid_plan(self.directory)
        task = plan["tasks"][0]
        task["complexity"] = "strong"
        task["routes"] = ["corporate-pro", "codex-sol"]
        task["verifier_routes"] = ["codex-terra", "claude-opus"]
        task["test_intent_verifier_routes"] = ["codex-terra", "claude-opus"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "grill"):
            router_core.validate_plan(plan)

        plan["planning"]["grill"] = {
            "level": "strong",
            "required": True,
            "signals": ["multi-file semantic change"],
            "routes": ["codex-terra"],
            "roles": ["assumption-breaker"],
            "rounds": 1,
            "open_blockers": [],
            "verdict": "PASS",
        }
        with self.assertRaisesRegex(router_core.PlanValidationError, "independent from the planner"):
            router_core.validate_plan(plan)

        plan["planning"]["grill"]["routes"] = ["claude-sonnet"]
        self.assertIs(router_core.validate_plan(plan), plan)

    def test_frontier_grill_requires_two_independent_frontier_providers(self) -> None:
        plan = valid_plan(self.directory)
        task = plan["tasks"][0]
        task["complexity"] = "frontier"
        task["routes"] = ["codex-sol"]
        task["verifier_routes"] = ["claude-opus"]
        task["test_intent_verifier_routes"] = ["claude-opus"]
        plan["planning"]["grill"] = {
            "level": "frontier",
            "required": True,
            "signals": ["public contract and concurrency"],
            "routes": ["codex-sol", "codex-high"],
            "roles": ["architecture-breaker", "failure-mode-breaker"],
            "rounds": 1,
            "open_blockers": [],
            "verdict": "PASS",
        }
        with self.assertRaisesRegex(router_core.PlanValidationError, "independent providers"):
            router_core.validate_plan(plan)

        plan["planning"]["grill"]["routes"] = ["codex-sol", "claude-opus"]
        self.assertIs(router_core.validate_plan(plan), plan)

    def test_grill_cannot_pass_with_open_blockers(self) -> None:
        plan = valid_plan(self.directory)
        plan["planning"]["grill"] = {
            "level": "strong",
            "required": True,
            "signals": ["architecture risk"],
            "routes": ["claude-sonnet"],
            "roles": ["architecture-breaker"],
            "rounds": 1,
            "open_blockers": ["persistence rollback is undefined"],
            "verdict": "PASS",
        }
        with self.assertRaisesRegex(router_core.PlanValidationError, "open_blockers"):
            router_core.validate_plan(plan)

    def test_rejects_missing_test_pyramid_or_weak_diagnostician(self) -> None:
        plan = valid_plan(self.directory)
        plan["tasks"][0]["test_plan"]["affected"] = []
        plan["tasks"][0]["diagnosis_routes"] = ["minimax", "codex-sol"]
        with self.assertRaises(router_core.PlanValidationError) as raised:
            router_core.validate_plan(plan)
        self.assertIn("affected", str(raised.exception))
        self.assertIn("capability 2", str(raised.exception))

    def test_rejects_ignore_preexisting_failure_semantics(self) -> None:
        plan = valid_plan(self.directory)
        plan["final_gate"]["acceptance_checks"] = ["Ignore pre-existing test failures"]
        with self.assertRaisesRegex(router_core.PlanValidationError, "zero-tolerance"):
            router_core.validate_plan(plan)

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

    def test_premium_grill_route_requires_explicit_budget_approval(self) -> None:
        plan = valid_plan(self.directory)
        task = plan["tasks"][0]
        task["complexity"] = "frontier"
        task["routes"] = ["codex-sol"]
        task["verifier_routes"] = ["claude-opus"]
        task["test_intent_verifier_routes"] = ["claude-opus"]
        plan["planning"]["grill"] = {
            "level": "frontier",
            "required": True,
            "signals": ["cross-system public contract"],
            "routes": ["codex-sol", "kimi-k3"],
            "roles": ["contract-breaker", "failure-mode-breaker"],
            "rounds": 1,
            "open_blockers": [],
            "verdict": "PASS",
        }
        with self.assertRaisesRegex(router_core.PlanValidationError, "premium"):
            router_core.validate_plan(plan)

        plan["approval"]["premium_routes"] = ["kimi-k3"]
        plan["approval"]["max_api_budget_usd"] = 1.0
        self.assertIs(router_core.validate_plan(plan), plan)

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
        self.assertEqual(
            router_core.resolved_model("corporate-qwen"),
            "cloudru/Qwen3-Coder-Next",
        )
        self.assertEqual(
            router_core.resolved_model("corporate-minimax"),
            "cloudru/MiniMax-M3",
        )
        self.assertEqual(router_core.resolved_model("minimax-m3"), "MiniMax-M3")
        self.assertEqual(
            router_core.resolved_model("openrouter-cheap"),
            "deepseek/deepseek-v4-flash",
        )
        self.assertEqual(
            router_core.resolved_model("openrouter-deepseek"),
            "deepseek/deepseek-v4-pro",
        )

    def test_plan_summary_exposes_model_and_effort_ladders(self) -> None:
        summary = router_core.plan_summary(valid_plan(self.directory), "plan-id")
        first_worker = summary["tasks"][0]["worker_ladder"][0]
        self.assertEqual(first_worker["alias"], "minimax")
        first_verifier = summary["tasks"][0]["verifier_ladder"][0]
        self.assertEqual(first_verifier["model"], "gpt-5.6-luna")
        self.assertEqual(first_verifier["effort"], "low")
        self.assertEqual(summary["planning"]["grill"]["verdict"], "SKIPPED")
        self.assertEqual(summary["minimum_planning_model_agents"], 2)
        self.assertEqual(summary["deterministic_command_count"], 3)
        self.assertEqual(summary["deterministic_check_suite_nodes"], 3)
        self.assertEqual(summary["dependency_wave_count"], 1)
        self.assertEqual(summary["minimum_execution_visible_agents"], 7)

        plan = valid_plan(self.directory)
        plan["tasks"][0]["test_plan"]["affected"] = json.loads(
            json.dumps(plan["tasks"][0]["test_plan"]["targeted"])
        )
        reused_summary = router_core.plan_summary(plan, "reused-plan-id")
        self.assertEqual(reused_summary["deterministic_command_count"], 3)
        self.assertEqual(reused_summary["deterministic_check_suite_nodes"], 2)

    def test_delegate_roles_include_plan_griller(self) -> None:
        self.assertIn("plan-griller", router_core.ROLES)


class DocumentationTests(unittest.TestCase):
    def test_activation_command_is_identical_in_readme_and_skills(self) -> None:
        exact_command = "/ai-router:start-workflow <rough software goal>"
        readme = (PLUGIN_ROOT.parents[1] / "README.md").read_text(encoding="utf-8")
        portable_skill = (PLUGIN_ROOT.parents[1] / "SKILL.md").read_text(encoding="utf-8")
        start_skill = (PLUGIN_ROOT / "claude-skills" / "start-workflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(exact_command, readme)
        self.assertIn(exact_command, portable_skill)
        self.assertIn(f'argument-hint: "<rough software goal>"', start_skill)


class CompilePlanningWorkflowTests(unittest.TestCase):
    def test_compiles_one_parallel_visible_planning_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            worktree = root / "repo"
            worktree.mkdir()
            request = {
                "session_id": "a" * 32,
                "objective": "Implement a bounded feature",
                "working_directory": str(worktree),
                "inspection": {
                    "worktree": str(worktree.resolve()),
                    "tracked_file_count": 10,
                    "candidate_checks": [],
                },
                "discovery_tasks": [
                    {
                        "id": "architecture",
                        "objective": "Map relevant ownership and contracts",
                    },
                    {
                        "id": "tests",
                        "objective": "Map test oracles and mandatory regression",
                    },
                ],
                "context": {},
            }
            with mock.patch.dict(os.environ, {"AI_ROUTER_STATE_DIR": str(state)}):
                compiled = router_core.compile_planning_workflow(
                    request,
                    PLUGIN_ROOT / "workflow" / "planning.template.js",
                )
            script = Path(compiled["script_path"])
            self.assertTrue(script.is_file())
            self.assertEqual(stat.S_IMODE(script.stat().st_mode), 0o600)
            self.assertEqual(compiled["discovery_agents"], 2)
            self.assertEqual(compiled["initial_planning_tier"], "strong")
            self.assertEqual(
                compiled["protocol_version"],
                router_core.WORKFLOW_PROTOCOL_VERSION,
            )
            self.assertEqual(
                compiled["planning_routes"]["planners"]["strong"],
                "corporate-minimax",
            )
            self.assertEqual(
                compiled["planning_routes"]["tactical_planners"]["strong"],
                "openrouter-deepseek",
            )
            self.assertEqual(
                compiled["script_sha256"],
                hashlib.sha256(script.read_bytes()).hexdigest(),
            )
            source = script.read_text(encoding="utf-8")
            self.assertIn("'ai-router:planning-readonly'", source)
            self.assertIn("agentType: 'ai-router:external-worker'", source)
            self.assertIn("const ARCHITECTURE_SCHEMA", source)
            self.assertIn("const TACTICAL_SCHEMA", source)
            self.assertNotIn("const ROUTE_PLAN_SCHEMA", source)
            self.assertIn("function buildRoutePlan", source)
            self.assertIn("const ROUTING_LADDERS", source)
            self.assertIn("'openrouter-cheap'", source)
            self.assertIn("'corporate-minimax'", source)
            self.assertIn("'claude-best'", source)
            self.assertIn("regression: checkSpecs(draft.regression_commands)", source)
            self.assertNotIn("while (true)", source)
            checked = subprocess.run(
                ["node", "--check", str(script)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            completed = subprocess.run(
                [
                    "node",
                    str(PLUGIN_ROOT / "tests" / "mock_planning_runtime.mjs"),
                    str(script),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "PLAN_READY")
            self.assertGreaterEqual(result["max_active"], 2)
            self.assertEqual(result["architecture_calls"], 1)
            self.assertEqual(result["tactical_calls"], 1)
            self.assertTrue(
                any(
                    label.startswith("discover:architecture:corporate-flash:")
                    for label in result["labels"]
                )
            )
            self.assertTrue(
                any(
                    label.startswith("discover:tests:minimax-fast:")
                    for label in result["labels"]
                )
            )
            self.assertEqual(
                len([label for label in result["labels"] if label.startswith("macro-grill:")]),
                1,
            )
            self.assertTrue(
                any(label.startswith("tactical-critic:") for label in result["labels"])
            )
            macro_prompt = next(
                item["prompt"]
                for item in result["prompts"]
                if item["label"].startswith("macro-grill:")
            )
            self.assertNotIn("targeted_commands", macro_prompt)
            self.assertNotIn("allowed_paths", macro_prompt)
            route_plan = result["result"]["route_plan"]
            router_core.validate_plan(route_plan)
            self.assertLessEqual(len(route_plan["tasks"]), 2)
            self.assertIn("corporate-minimax", route_plan["tasks"][0]["routes"])
            self.assertIn("minimax-m3", route_plan["tasks"][0]["routes"])
            self.assertIn("openrouter-deepseek", route_plan["tasks"][0]["verifier_routes"])
            self.assertEqual(
                route_plan["tasks"][0]["test_plan"]["targeted"][0]["timeout_seconds"],
                600,
            )
            self.assertNotIn("routes", result["result"]["architecture_envelope"])

    def test_frontier_planning_uses_fable_codex_and_openrouter_roles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            worktree = root / "repo"
            worktree.mkdir()
            request = {
                "session_id": "f" * 32,
                "objective": "Redesign a public concurrent persistence architecture and migration protocol",
                "working_directory": str(worktree),
                "inspection": {
                    "worktree": str(worktree.resolve()),
                    "tracked_file_count": 2000,
                    "changed_file_count": 20,
                    "candidate_checks": [],
                },
                "discovery_tasks": [],
                "context": {},
            }
            with mock.patch.dict(os.environ, {"AI_ROUTER_STATE_DIR": str(state)}):
                compiled = router_core.compile_planning_workflow(
                    request,
                    PLUGIN_ROOT / "workflow" / "planning.template.js",
                )
            self.assertEqual(compiled["initial_planning_tier"], "frontier")
            completed = subprocess.run(
                [
                    "node",
                    str(PLUGIN_ROOT / "tests" / "mock_planning_runtime.mjs"),
                    compiled["script_path"],
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "PLAN_READY")
            self.assertTrue(
                any(
                    label.startswith("architecture:r1:claude-best:")
                    for label in result["labels"]
                )
            )
            grill_labels = [
                label for label in result["labels"] if label.startswith("macro-grill:")
            ]
            self.assertEqual(len(grill_labels), 2)
            self.assertTrue(any(":codex-sol:" in label for label in grill_labels))
            self.assertTrue(
                any(":openrouter-deepseek-frontier:" in label for label in grill_labels)
            )

    def test_critic_plan_correction_returns_to_planner_not_user(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            worktree = root / "repo"
            worktree.mkdir()
            request = {
                "session_id": "b" * 32,
                "objective": "Implement a bounded feature",
                "working_directory": str(worktree),
                "inspection": {
                    "worktree": str(worktree.resolve()),
                    "tracked_file_count": 10,
                    "candidate_checks": [],
                },
                "discovery_tasks": [],
                "context": {},
            }
            with mock.patch.dict(os.environ, {"AI_ROUTER_STATE_DIR": str(state)}):
                compiled = router_core.compile_planning_workflow(
                    request,
                    PLUGIN_ROOT / "workflow" / "planning.template.js",
                )
            completed = subprocess.run(
                [
                    "node",
                    str(PLUGIN_ROOT / "tests" / "mock_planning_runtime.mjs"),
                    compiled["script_path"],
                    "critic-correction",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "PLAN_READY")
            self.assertEqual(result["critic_calls"], 2)
            self.assertEqual(result["tactical_calls"], 2)
            self.assertEqual(result["architecture_calls"], 1)

    def test_routine_correction_uses_external_routine_pool(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            worktree = root / "repo"
            worktree.mkdir()
            request = {
                "session_id": "c" * 32,
                "objective": "Create one text file containing exactly hello",
                "working_directory": str(worktree),
                "inspection": {
                    "worktree": str(worktree.resolve()),
                    "tracked_file_count": 1,
                    "changed_file_count": 0,
                    "candidate_checks": [],
                },
                "discovery_tasks": [],
                "context": {},
            }
            with mock.patch.dict(os.environ, {"AI_ROUTER_STATE_DIR": str(state)}):
                compiled = router_core.compile_planning_workflow(
                    request,
                    PLUGIN_ROOT / "workflow" / "planning.template.js",
                )
            completed = subprocess.run(
                [
                    "node",
                    str(PLUGIN_ROOT / "tests" / "mock_planning_runtime.mjs"),
                    compiled["script_path"],
                    "routine-critic-correction",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "PLAN_READY")
            architecture_labels = [
                label for label in result["labels"] if label.startswith("architecture:")
            ]
            tactical_labels = [
                label for label in result["labels"] if label.startswith("tactical-plan:")
            ]
            self.assertEqual(len(architecture_labels), 1)
            self.assertTrue(all(":minimax-fast:" in label for label in architecture_labels))
            self.assertEqual(len(tactical_labels), 2)
            self.assertTrue(all(":openrouter-cheap:" in label for label in tactical_labels))

    def test_macro_architecture_has_one_correction_and_fatal_stops(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            worktree = root / "repo"
            worktree.mkdir()
            request = {
                "session_id": "d" * 32,
                "objective": "Implement a bounded feature",
                "working_directory": str(worktree),
                "inspection": {
                    "worktree": str(worktree.resolve()),
                    "tracked_file_count": 10,
                    "candidate_checks": [],
                },
                "discovery_tasks": [],
                "context": {},
            }
            with mock.patch.dict(os.environ, {"AI_ROUTER_STATE_DIR": str(state)}):
                compiled = router_core.compile_planning_workflow(
                    request,
                    PLUGIN_ROOT / "workflow" / "planning.template.js",
                )
            corrected = subprocess.run(
                [
                    "node",
                    str(PLUGIN_ROOT / "tests" / "mock_planning_runtime.mjs"),
                    compiled["script_path"],
                    "macro-correction",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(corrected.returncode, 0, corrected.stderr)
            corrected_result = json.loads(corrected.stdout)
            self.assertEqual(corrected_result["result"]["status"], "PLAN_READY")
            self.assertEqual(corrected_result["architecture_calls"], 2)

            fatal = subprocess.run(
                [
                    "node",
                    str(PLUGIN_ROOT / "tests" / "mock_planning_runtime.mjs"),
                    compiled["script_path"],
                    "macro-fatal",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(fatal.returncode, 0, fatal.stderr)
            fatal_result = json.loads(fatal.stdout)
            self.assertEqual(fatal_result["result"]["status"], "BLOCKED")
            self.assertIn("ARCHITECTURE_FATAL", fatal_result["result"]["blocker"])
            self.assertEqual(fatal_result["tactical_calls"], 0)

    def test_compiler_finding_fails_without_replanning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            worktree = root / "repo"
            worktree.mkdir()
            request = {
                "session_id": "e" * 32,
                "objective": "Implement a bounded feature",
                "working_directory": str(worktree),
                "inspection": {
                    "worktree": str(worktree.resolve()),
                    "tracked_file_count": 10,
                    "candidate_checks": [],
                },
                "discovery_tasks": [],
                "context": {},
            }
            with mock.patch.dict(os.environ, {"AI_ROUTER_STATE_DIR": str(state)}):
                compiled = router_core.compile_planning_workflow(
                    request,
                    PLUGIN_ROOT / "workflow" / "planning.template.js",
                )
            completed = subprocess.run(
                [
                    "node",
                    str(PLUGIN_ROOT / "tests" / "mock_planning_runtime.mjs"),
                    compiled["script_path"],
                    "compiler-block",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "BLOCKED")
            self.assertIn("BLOCKED_COMPILER", result["result"]["blocker"])
            self.assertEqual(result["tactical_calls"], 1)

    def test_zero_token_classifier_keeps_single_artifact_work_on_haiku(self) -> None:
        tier, signals = router_core.classify_planning_tier(
            "Create one text file containing exactly hello",
            {"tracked_file_count": 0, "changed_file_count": 0},
        )
        self.assertEqual(tier, "routine")
        self.assertTrue(signals)

    def test_zero_token_classifier_routes_architecture_to_frontier(self) -> None:
        tier, signals = router_core.classify_planning_tier(
            "Design a concurrent schema migration with rollback",
            {"tracked_file_count": 100, "changed_file_count": 0},
        )
        self.assertEqual(tier, "frontier")
        self.assertTrue(signals)


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
            self.assertIn("agentType: 'ai-router:coding-worker'", script.read_text(encoding="utf-8"))
            self.assertIn("agentType: 'ai-router:reviewer-readonly'", script.read_text(encoding="utf-8"))
            self.assertIn("agentType: 'ai-router:external-worker'", script.read_text(encoding="utf-8"))
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
            self.assertTrue(any(label.startswith("calibrate:wave-") for label in labels))

    def test_failed_deterministic_check_gets_strong_diagnosis_then_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            script = self._compile(root / "state", valid_plan(str(worktree)))
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "check-fail-once"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "VERIFIED")
            labels = result["labels"]
            self.assertTrue(any(label.startswith("check-suite:implementation:targeted:") for label in labels))
            summarizer_index = next(
                index
                for index, label in enumerate(labels)
                if label.startswith("log-summarizer:implementation:")
            )
            diagnosis_index = next(
                index
                for index, label in enumerate(labels)
                if label.startswith("diagnose:implementation:")
            )
            self.assertLess(summarizer_index, diagnosis_index)
            self.assertTrue(any(label.startswith("diagnose:implementation:corporate-pro:") for label in labels))
            self.assertTrue(any(label.startswith("repair:implementation:corporate-pro:") for label in labels))

    def test_identical_affected_check_reuses_green_targeted_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            plan = valid_plan(str(worktree))
            plan["tasks"][0]["test_plan"]["affected"] = json.loads(
                json.dumps(plan["tasks"][0]["test_plan"]["targeted"])
            )
            script = self._compile(root / "state", plan)
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "success"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "VERIFIED")
            task_checks = [
                label
                for label in result["labels"]
                if label.startswith("check-suite:implementation:")
            ]
            self.assertEqual(
                len([label for label in task_checks if ":targeted:" in label]),
                1,
            )
            self.assertFalse(any(":affected:" in label for label in task_checks))

    def test_suspected_flaky_is_diagnosed_and_never_treated_as_green(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            script = self._compile(root / "state", valid_plan(str(worktree)))
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "flaky-then-repair"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "VERIFIED")
            self.assertTrue(
                any(
                    label.startswith("log-summarizer:implementation:")
                    for label in result["labels"]
                )
            )
            self.assertTrue(any(label.startswith("diagnose:implementation:") for label in result["labels"]))
            self.assertTrue(any(label.startswith("repair:implementation:") for label in result["labels"]))

    def test_existing_test_edit_triggers_independent_test_intent_agent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            script = self._compile(root / "state", valid_plan(str(worktree)))
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "test-intent"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "VERIFIED")
            self.assertTrue(any(label.startswith("test-intent-verifier:implementation:") for label in result["labels"]))

    def test_out_of_scope_diagnosis_requests_plan_amendment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            script = self._compile(root / "state", valid_plan(str(worktree)))
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "out-of-scope"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "AWAITING_SCOPE_APPROVAL")
            self.assertIn("outside/contract", json.dumps(result["result"]))

    def test_failing_mandatory_regression_can_never_return_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "repo"
            worktree.mkdir()
            script = self._compile(root / "state", valid_plan(str(worktree)))
            completed = subprocess.run(
                ["node", str(PLUGIN_ROOT / "tests" / "mock_workflow_runtime.mjs"), str(script), "regression-never-green"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["result"]["status"], "BLOCKED")
            self.assertTrue(any(label.startswith("check-suite:") and ":regression:" in label for label in result["labels"]))

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
            with (
                mock.patch.dict(os.environ, {"AI_ROUTER_RUNNER": str(runner)}),
                mock.patch.object(
                    router_core,
                    "health",
                    return_value={
                        "all_available": True,
                        "routes": [{"available": True, "detail": "mock ready"}],
                    },
                ),
            ):
                result = router_core.run_delegate(arguments, PLUGIN_ROOT, store)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["output"], "worker complete")
            raw_log = store.path.read_text(encoding="utf-8")
            self.assertNotIn("private task prompt", raw_log)
            aggregate = store.aggregate("day", "workflow-1")
            self.assertEqual(aggregate["external_calls"], 1)
            self.assertEqual(aggregate["usage"]["input_tokens"], 12)
            self.assertAlmostEqual(aggregate["known_external_cost_usd"], 0.02)
            self.assertEqual(aggregate["by_role"]["worker"]["calls"], 1)
            self.assertEqual(aggregate["by_provider"]["deepseek"]["calls"], 1)

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
            with (
                mock.patch.dict(os.environ, {"AI_ROUTER_RUNNER": str(runner)}),
                mock.patch.object(
                    router_core,
                    "health",
                    return_value={
                        "all_available": True,
                        "routes": [{"available": True, "detail": "mock ready"}],
                    },
                ),
            ):
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
        self.assertTrue(
            {
                "start_session",
                "session_status",
                "checkpoint_session",
                "inspect_workspace",
                "run_check",
                "run_check_suite",
                "compile_planning_workflow",
                "prepare_plan",
                "compile_workflow",
                "delegate",
                "usage",
                "health",
            }.issubset(names)
        )
        tools = {tool["name"]: tool for tool in listed["result"]["tools"]}
        self.assertIn("session_id", tools["prepare_plan"]["inputSchema"]["properties"])
        delegate_role_enum = tools["delegate"]["inputSchema"]["properties"]["role"]["enum"]
        checkpoint_state_enum = tools["checkpoint_session"]["inputSchema"]["properties"]["next_state"]["enum"]
        self.assertIn("plan-griller", delegate_role_enum)
        self.assertIn("calibrator", delegate_role_enum)
        self.assertIn("GRILLING", checkpoint_state_enum)


class AgentManifestTests(unittest.TestCase):
    def test_external_worker_has_only_exact_router_action_tools(self) -> None:
        manifest = (PLUGIN_ROOT / "agents" / "external-worker.md").read_text(encoding="utf-8")
        self.assertIn(
            "tools: mcp__plugin_ai-router_ai-router__delegate, "
            "mcp__plugin_ai-router_ai-router__run_check, "
            "mcp__plugin_ai-router_ai-router__run_check_suite",
            manifest,
        )
        self.assertNotIn("tools: ToolSearch", manifest)
        self.assertNotIn("tools: Bash", manifest)

    def test_native_reviewer_can_record_without_deferred_tool_search(self) -> None:
        manifest = (PLUGIN_ROOT / "agents" / "reviewer-readonly.md").read_text(encoding="utf-8")
        self.assertIn("mcp__plugin_ai-router_ai-router__record_verdict", manifest)
        self.assertNotIn("ToolSearch", manifest)
        self.assertNotIn(", Edit", manifest)
        self.assertNotIn(", Write", manifest)


if __name__ == "__main__":
    unittest.main()
