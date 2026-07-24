#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from adaptive_core import (
    bind_prepared_plan,
    checkpoint_session,
    inspect_workspace,
    json_digest,
    registered_route_plan,
    register_compiled_workflow,
    run_check,
    run_check_suite,
    session_status,
    start_session,
)
from router_core import (
    ROUTES,
    PlanValidationError,
    UsageStore,
    compile_planning_workflow,
    compile_workflow,
    health,
    prepare_plan,
    record_verdict,
    resolved_model,
    run_delegate,
)


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_TEMPLATE = PLUGIN_ROOT / "workflow" / "execute.template.js"
PLANNING_WORKFLOW_TEMPLATE = PLUGIN_ROOT / "workflow" / "planning.template.js"


TOOLS = [
    {
        "name": "start_session",
        "description": "Start or resume one durable adaptive planning session for the canonical worktree. Stores only compact redacted state; does not call a model.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["objective", "working_directory"],
            "properties": {
                "objective": {"type": "string"},
                "working_directory": {"type": "string"},
            },
        },
        "annotations": {"readOnlyHint": False, "openWorldHint": False},
    },
    {
        "name": "session_status",
        "description": "Read resumable adaptive-session state by session id or canonical worktree and report whether the workspace changed.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "session_id": {"type": "string"},
                "working_directory": {"type": "string"},
            },
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "checkpoint_session",
        "description": "Advance an adaptive session through its enforced state machine with a compact redacted checkpoint.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["session_id", "next_state", "summary"],
            "properties": {
                "session_id": {"type": "string"},
                "next_state": {
                    "type": "string",
                    "enum": [
                        "INSPECTING",
                        "DISCOVERING",
                        "AWAITING_USER_DECISION",
                        "PLANNING",
                        "GRILLING",
                        "CRITIQUING",
                        "READY_FOR_APPROVAL",
                        "EXECUTING",
                        "AWAITING_SCOPE_APPROVAL",
                        "VERIFIED",
                        "BLOCKED",
                    ],
                },
                "summary": {"type": "string"},
                "data": {"type": "object"},
            },
        },
        "annotations": {"readOnlyHint": False, "openWorldHint": False},
    },
    {
        "name": "inspect_workspace",
        "description": "Perform a lightweight, non-generating workspace inspection and discover candidate test commands without executing them or reading secret files.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["working_directory"],
            "properties": {"working_directory": {"type": "string"}},
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "run_check",
        "description": "Run one approved deterministic targeted, affected, or regression check under a worktree test lease. On failure, optionally performs exactly one explicit isolated rerun and returns redacted structured evidence.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["command", "working_directory", "level", "workflow_id", "task_id"],
            "properties": {
                "command": {"type": "string"},
                "rerun_command": {"type": "string"},
                "working_directory": {"type": "string"},
                "level": {"type": "string", "enum": ["targeted", "affected", "regression"]},
                "workflow_id": {"type": "string"},
                "task_id": {"type": "string"},
                "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 14400, "default": 3600},
            },
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "run_check_suite",
        "description": "Run one ordered suite of approved deterministic checks under the same zero-tolerance policy. Stops at the first non-green result and returns each command's redacted evidence. Batching avoids spending one model-wrapper call per shell command.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["checks", "working_directory", "level", "workflow_id", "task_id"],
            "properties": {
                "checks": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["command"],
                        "properties": {
                            "command": {"type": "string"},
                            "rerun_command": {"type": "string"},
                            "timeout_seconds": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 14400,
                                "default": 3600,
                            },
                        },
                    },
                },
                "working_directory": {"type": "string"},
                "level": {"type": "string", "enum": ["targeted", "affected", "regression"]},
                "workflow_id": {"type": "string"},
                "task_id": {"type": "string"},
            },
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "route_catalog",
        "description": "List AI Router route aliases, capability levels, provider identities, premium gates, and resolved local model names. This does not call a model.",
        "inputSchema": {"type": "object", "additionalProperties": False, "properties": {}},
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "health",
        "description": "Perform lightweight, non-generating availability checks for selected AI Router routes. Successful checks are cached unless fresh is true.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "routes": {"type": "array", "items": {"type": "string"}},
                "fresh": {"type": "boolean", "default": False},
            },
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "compile_planning_workflow",
        "description": "Compile and register one visible read-only Planning Workflow graph for discovery, frontier planning, risk-gated architectural grill, and independent criticism. Inline or ad-hoc planning workflows are rejected by the controller hook.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["request"],
            "properties": {"request": {"type": "object"}},
        },
        "annotations": {"readOnlyHint": False, "openWorldHint": False},
    },
    {
        "name": "prepare_plan",
        "description": "Validate and persist the exact RoutePlan returned by a completed registered Planning Workflow. Pass session_id so the server loads the result directly without retranscribing large JSON. The plan property remains for backward compatibility. Returns a plan_id and display summary; does not call a model.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "session_id": {"type": "string"},
                "plan": {"type": "object"},
            },
            "anyOf": [
                {"required": ["session_id"]},
                {"required": ["plan"]},
            ],
        },
        "annotations": {"readOnlyHint": False, "openWorldHint": False},
    },
    {
        "name": "compile_workflow",
        "description": "Compile a prepared RoutePlan into a native Claude Dynamic Workflow script. Present the complete plan first, then launch Workflow with the returned scriptPath; Claude's native workflow approval card is the user's one execution confirmation.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["plan_id"],
            "properties": {"plan_id": {"type": "string"}},
        },
        "annotations": {"readOnlyHint": False, "openWorldHint": False},
    },
    {
        "name": "delegate",
        "description": "Run exactly one visible workflow agent delegation through an approved Codex, corporate LiteLLM, MiniMax, DeepSeek, or OpenRouter route. Returns structured output and usage. Native Claude routes must run directly in Workflow instead.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["workflow_id", "task_id", "role", "route", "profile", "working_directory", "prompt"],
            "properties": {
                "workflow_id": {"type": "string"},
                "task_id": {"type": "string"},
                "role": {
                    "type": "string",
                    "enum": [
                        "worker",
                        "verifier",
                        "repair",
                        "frontier-replanner",
                        "final-gate",
                        "discovery",
                        "planner",
                        "architecture-drafter",
                        "architecture-griller",
                        "architecture-arbiter",
                        "plan-griller",
                        "plan-critic",
                        "calibrator",
                        "log-summarizer",
                        "failure-triage",
                        "dependency-mapper",
                        "test-inventory",
                        "diagnostician",
                        "test-intent-verifier",
                    ],
                },
                "route": {"type": "string"},
                "profile": {"type": "string", "enum": ["review", "verify", "build"]},
                "working_directory": {"type": "string"},
                "prompt": {"type": "string"},
                "timeout_seconds": {"type": "integer", "minimum": 30, "maximum": 14400, "default": 3600},
                "budget_usd": {"type": "number", "exclusiveMinimum": 0},
                "record_verdict_from_output": {
                    "type": "boolean",
                    "default": False,
                    "description": "For verifier/final-gate roles, parse and record a valid delegated JSON verdict in this same local call.",
                },
            },
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "record_verdict",
        "description": "Record verifier pass, fail, or blocked metadata without storing the evidence text. Does not call a model.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["workflow_id", "task_id", "verdict", "route", "evidence"],
            "properties": {
                "workflow_id": {"type": "string"},
                "task_id": {"type": "string"},
                "verdict": {"type": "string", "enum": ["pass", "fail", "blocked"]},
                "route": {"type": "string"},
                "evidence": {"type": "string"},
            },
        },
        "annotations": {"readOnlyHint": False, "openWorldHint": False},
    },
    {
        "name": "usage",
        "description": "Summarize routed external calls, tokens, known API cost, and verdict counts for the last day, week, all history, or a workflow id.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "period": {"type": "string", "enum": ["day", "week", "all"], "default": "day"},
                "workflow_id": {"type": "string"},
            },
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
]


def _text_result(value: Any, *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}],
        "structuredContent": value if isinstance(value, dict) else {"value": value},
        "isError": is_error,
    }


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "start_session":
        return _text_result(start_session(arguments.get("objective", ""), arguments.get("working_directory", "")))
    if name == "session_status":
        return _text_result(
            session_status(
                session_id=arguments.get("session_id"),
                working_directory=arguments.get("working_directory"),
            )
        )
    if name == "checkpoint_session":
        return _text_result(
            checkpoint_session(
                arguments.get("session_id", ""),
                arguments.get("next_state", ""),
                arguments.get("summary", ""),
                arguments.get("data"),
            )
        )
    if name == "inspect_workspace":
        return _text_result(inspect_workspace(arguments.get("working_directory", "")))
    if name == "run_check":
        return _text_result(
            run_check(
                command=arguments.get("command", ""),
                rerun_command=arguments.get("rerun_command"),
                working_directory=arguments.get("working_directory", ""),
                level=arguments.get("level", ""),
                workflow_id=arguments.get("workflow_id", ""),
                task_id=arguments.get("task_id", ""),
                timeout_seconds=arguments.get("timeout_seconds", 3600),
            )
        )
    if name == "run_check_suite":
        return _text_result(
            run_check_suite(
                checks=arguments.get("checks", []),
                working_directory=arguments.get("working_directory", ""),
                level=arguments.get("level", ""),
                workflow_id=arguments.get("workflow_id", ""),
                task_id=arguments.get("task_id", ""),
            )
        )
    if name == "route_catalog":
        routes = []
        for alias, route in ROUTES.items():
            routes.append(
                {
                    "alias": alias,
                    "engine": route.engine,
                    "provider": route.provider,
                    "capability": route.capability,
                    "premium": route.premium,
                    "native_claude_workflow": route.native,
                    "model": resolved_model(alias),
                    "effort": route.effort,
                }
            )
        return _text_result({"routes": routes})
    if name == "health":
        routes = arguments.get("routes") or [
            "corporate-pro",
            "codex-terra",
            "claude-sonnet",
            "minimax",
            "cheap",
            "openrouter-cheap",
        ]
        return _text_result(health(routes, PLUGIN_ROOT, fresh=bool(arguments.get("fresh", False))))
    if name == "compile_planning_workflow":
        compiled = compile_planning_workflow(
            arguments.get("request"),
            PLANNING_WORKFLOW_TEMPLATE,
        )
        register_compiled_workflow(
            compiled["session_id"],
            "planning",
            compilation_id=compiled["compilation_id"],
            workflow_id=compiled["workflow_id"],
            script_path=compiled["script_path"],
            script_sha256=compiled["script_sha256"],
            protocol_version=compiled["protocol_version"],
        )
        return _text_result(compiled)
    if name == "prepare_plan":
        session_id_argument = arguments.get("session_id")
        plan = (
            registered_route_plan(session_id_argument)
            if isinstance(session_id_argument, str) and session_id_argument
            else arguments.get("plan")
        )
        prepared = prepare_plan(plan)
        session_id = prepared.get("session_id")
        if session_id:
            bind_prepared_plan(
                session_id,
                plan_id=prepared["plan_id"],
                workflow_id=prepared["workflow_id"],
                plan_digest=prepared.get("plan_digest") or json_digest(plan),
            )
        return _text_result(prepared)
    if name == "compile_workflow":
        compiled = compile_workflow(arguments.get("plan_id", ""), WORKFLOW_TEMPLATE)
        if compiled.get("session_id"):
            register_compiled_workflow(
                compiled["session_id"],
                "execution",
                compilation_id=compiled["plan_id"],
                workflow_id=compiled["workflow_id"],
                plan_id=compiled["plan_id"],
                script_path=compiled["script_path"],
                script_sha256=compiled["script_sha256"],
                protocol_version=compiled["protocol_version"],
            )
        return _text_result(compiled)
    if name == "delegate":
        return _text_result(run_delegate(arguments, PLUGIN_ROOT))
    if name == "record_verdict":
        return _text_result(record_verdict(arguments))
    if name == "usage":
        return _text_result(UsageStore().aggregate(arguments.get("period", "day"), arguments.get("workflow_id")))
    raise ValueError(f"unknown tool: {name}")


def dispatch(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        result = {
            "protocolVersion": request.get("params", {}).get("protocolVersion", "2024-11-05"),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "ai-router", "version": "0.8.1"},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = request.get("params") or {}
        result = call_tool(params.get("name", ""), params.get("arguments") or {})
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> int:
    os.umask(0o077)
    if "--self-test" in sys.argv:
        print(json.dumps({"server": "ai-router", "tools": [tool["name"] for tool in TOOLS], "template": WORKFLOW_TEMPLATE.is_file()}))
        return 0
    for raw_line in sys.stdin.buffer:
        if not raw_line.strip():
            continue
        try:
            request = json.loads(raw_line)
            response = dispatch(request)
        except (ValueError, PlanValidationError) as error:
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if isinstance(request, dict) else None,
                "error": {
                    "code": -32602,
                    "message": str(error),
                    "data": {"errors": getattr(error, "errors", [str(error)])},
                },
            }
        except Exception as error:  # pragma: no cover - last-resort MCP boundary
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if isinstance(request, dict) else None,
                "error": {"code": -32603, "message": f"Internal error: {type(error).__name__}"},
            }
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
