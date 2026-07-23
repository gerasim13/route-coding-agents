#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "mcp-server"))

from adaptive_core import (  # noqa: E402
    controller_tool_decision,
    record_compaction,
    record_workflow_launch,
    recovery_context,
)


def _read_input() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _response_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)

def _workflow_run_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("runId", "run_id"):
            candidate = value.get(key)
            if isinstance(candidate, str) and re.fullmatch(r"wf_[A-Za-z0-9._-]+", candidate):
                return candidate
        for item in value.values():
            candidate = _workflow_run_id(item)
            if candidate:
                return candidate
        return None
    if isinstance(value, list):
        for item in value:
            candidate = _workflow_run_id(item)
            if candidate:
                return candidate
        return None
    if isinstance(value, str):
        match = re.search(r"\bRun ID:\s*(wf_[A-Za-z0-9._-]+)", value)
        if match:
            return match.group(1)
        match = re.search(r'"runId"\s*:\s*"(wf_[A-Za-z0-9._-]+)"', value)
        if match:
            return match.group(1)
    return None


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )


def pre_tool(hook_input: dict[str, Any]) -> None:
    decision = controller_tool_decision(hook_input)
    if not decision.get("allow", True):
        _deny(str(decision.get("reason") or "AI Router workflow-only controller denied this tool."))


def post_tool(hook_input: dict[str, Any]) -> None:
    if hook_input.get("tool_name") != "Workflow":
        return
    tool_input = hook_input.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    script_path = tool_input.get("scriptPath")
    if not isinstance(script_path, str) or not script_path:
        return
    tool_response = hook_input.get("tool_response")
    run_id = _workflow_run_id(tool_response)
    if run_id is None:
        run_id = _workflow_run_id(_response_text(tool_response))
    if run_id is None:
        return
    record_workflow_launch(
        working_directory=str(hook_input.get("cwd") or ""),
        script_path=script_path,
        transcript_path=str(hook_input.get("transcript_path") or ""),
        run_id=run_id,
    )


def post_compact(hook_input: dict[str, Any]) -> None:
    record_compaction(
        working_directory=str(hook_input.get("cwd") or ""),
        trigger=str(hook_input.get("trigger") or ""),
        compact_summary=str(hook_input.get("compact_summary") or ""),
    )


def recover(hook_input: dict[str, Any]) -> None:
    context = recovery_context(str(hook_input.get("cwd") or ""))
    if context:
        print(context)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    hook_input = _read_input()
    try:
        if mode == "pre-tool":
            pre_tool(hook_input)
        elif mode == "post-tool":
            post_tool(hook_input)
        elif mode == "post-compact":
            post_compact(hook_input)
        elif mode == "recover":
            recover(hook_input)
    except Exception as error:  # Hook failures must be visible without breaking unrelated sessions.
        print(f"[ai-router] controller hook error: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
