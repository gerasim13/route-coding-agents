#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from router_core import (
    ROUTES,
    PlanValidationError,
    UsageStore,
    compile_workflow,
    health,
    prepare_plan,
    record_verdict,
    resolved_model,
    run_delegate,
)


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_TEMPLATE = PLUGIN_ROOT / "workflow" / "execute.template.js"


TOOLS = [
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
        "name": "prepare_plan",
        "description": "Validate and persist a pending RoutePlan before showing it for the user's one-time approval. Returns a plan_id and a display summary. Does not call a model.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["plan"],
            "properties": {"plan": {"type": "object"}},
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
                "role": {"type": "string", "enum": ["worker", "verifier", "repair", "frontier-replanner", "final-gate"]},
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
    if name == "prepare_plan":
        return _text_result(prepare_plan(arguments.get("plan")))
    if name == "compile_workflow":
        return _text_result(compile_workflow(arguments.get("plan_id", ""), WORKFLOW_TEMPLATE))
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
            "serverInfo": {"name": "ai-router", "version": "0.4.0"},
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
