from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


@dataclass(frozen=True)
class Route:
    alias: str
    engine: str
    capability: int
    provider: str
    premium: bool = False
    native: bool = False
    model: str | None = None
    effort: str | None = None


ROUTES: dict[str, Route] = {
    "cheap": Route("cheap", "opencode", 1, "deepseek"),
    "minimax": Route("minimax", "opencode", 1, "minimax"),
    "openrouter-cheap": Route("openrouter-cheap", "opencode", 1, "openrouter"),
    "codex-luna": Route(
        "codex-luna", "codex", 1, "openai-subscription", model="gpt-5.6-luna", effort="low"
    ),
    "claude-haiku": Route(
        "claude-haiku", "claude", 1, "anthropic-subscription", native=True, model="haiku"
    ),
    "corporate-pro": Route("corporate-pro", "opencode", 2, "corporate-litellm"),
    "codex-terra": Route(
        "codex-terra", "codex", 2, "openai-subscription", model="gpt-5.6-terra", effort="medium"
    ),
    "codex": Route(
        "codex", "codex", 2, "openai-subscription", model="gpt-5.6-terra", effort="medium"
    ),
    "claude-sonnet": Route(
        "claude-sonnet", "claude", 2, "anthropic-subscription", native=True, model="sonnet", effort="medium"
    ),
    "codex-sol": Route(
        "codex-sol", "codex", 3, "openai-subscription", model="gpt-5.6-sol", effort="high"
    ),
    "codex-high": Route(
        "codex-high", "codex", 3, "openai-subscription", model="gpt-5.6-sol", effort="high"
    ),
    "claude-opus": Route(
        "claude-opus", "claude", 3, "anthropic-subscription", native=True, model="opus", effort="high"
    ),
    "claude-best": Route(
        "claude-best", "claude", 3, "anthropic-subscription", native=True, model="best", effort="high"
    ),
    "kimi-k3": Route("kimi-k3", "opencode", 3, "openrouter", premium=True),
}

PROFILES = {"review", "verify", "build"}
ROLES = {"worker", "verifier", "repair", "frontier-replanner", "final-gate"}
COMPLEXITY_LEVELS = {"routine": 1, "strong": 2, "frontier": 3}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SECRET_PATH_RE = re.compile(r"(^|/)(\.env(?:\..*)?|[^/]*(?:credential|secret)[^/]*)($|/)", re.IGNORECASE)
GLOBAL_CLEAN_CHECK_RE = re.compile(
    r"(?:\bgit\s+status\b.{0,80}\bclean\b|\bclean\b.{0,40}\bworktree\b|\bworktree\b.{0,40}\bclean\b)",
    re.IGNORECASE,
)


class PlanValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _string_list(value: Any, field: str, errors: list[str], *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        errors.append(f"{field} must be a list of non-empty strings")
        return []
    if not allow_empty and not value:
        errors.append(f"{field} must not be empty")
    return value


def _validate_route_ladder(routes: list[str], field: str, errors: list[str]) -> None:
    unknown = [route for route in routes if route not in ROUTES]
    if unknown:
        errors.append(f"{field} contains unknown routes: {', '.join(unknown)}")
        return
    levels = [ROUTES[route].capability for route in routes]
    if levels != sorted(levels):
        errors.append(f"{field} must be ordered from weaker to stronger capability")


def _has_cycle(task_ids: set[str], dependencies: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> bool:
        if task_id in visiting:
            return True
        if task_id in visited:
            return False
        visiting.add(task_id)
        for dependency in dependencies.get(task_id, []):
            if dependency in task_ids and visit(dependency):
                return True
        visiting.remove(task_id)
        visited.add(task_id)
        return False

    return any(visit(task_id) for task_id in task_ids)


def validate_plan(plan: Any, *, check_directory: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        raise PlanValidationError(["plan must be an object"])

    if plan.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    workflow_id = plan.get("workflow_id")
    if not isinstance(workflow_id, str) or not ID_RE.fullmatch(workflow_id):
        errors.append("workflow_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    if not isinstance(plan.get("objective"), str) or not plan["objective"].strip():
        errors.append("objective must be a non-empty string")

    working_directory = plan.get("working_directory")
    if not isinstance(working_directory, str) or not os.path.isabs(working_directory):
        errors.append("working_directory must be an absolute path")
    elif check_directory and not os.path.isdir(working_directory):
        errors.append("working_directory must exist")

    approval = plan.get("approval", {})
    if not isinstance(approval, dict):
        errors.append("approval must be an object")
        approval = {}
    premium_routes = _string_list(approval.get("premium_routes", []), "approval.premium_routes", errors)
    max_budget = approval.get("max_api_budget_usd")
    if max_budget is not None and (not isinstance(max_budget, (int, float)) or isinstance(max_budget, bool) or max_budget <= 0):
        errors.append("approval.max_api_budget_usd must be null or a positive number")

    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        errors.append("tasks must be a non-empty list")
        tasks = []

    task_ids: set[str] = set()
    dependencies: dict[str, list[str]] = {}
    premium_used: set[str] = set()

    for index, task in enumerate(tasks):
        prefix = f"tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{prefix} must be an object")
            continue
        task_id = task.get("id")
        if not isinstance(task_id, str) or not ID_RE.fullmatch(task_id):
            errors.append(f"{prefix}.id is invalid")
            continue
        if task_id in task_ids:
            errors.append(f"duplicate task id: {task_id}")
        task_ids.add(task_id)
        if not isinstance(task.get("objective"), str) or not task["objective"].strip():
            errors.append(f"{prefix}.objective must be a non-empty string")
        if not isinstance(task.get("expected_artifact"), str) or not task["expected_artifact"].strip():
            errors.append(f"{prefix}.expected_artifact must be a non-empty string")
        permission = task.get("permission")
        if permission not in {"review", "build"}:
            errors.append(f"{prefix}.permission must be review or build")
        complexity = task.get("complexity")
        if complexity not in COMPLEXITY_LEVELS:
            errors.append(f"{prefix}.complexity must be routine, strong, or frontier")

        deps = _string_list(task.get("dependencies", []), f"{prefix}.dependencies", errors)
        dependencies[task_id] = deps
        _string_list(task.get("non_goals", []), f"{prefix}.non_goals", errors)
        allowed_paths = _string_list(task.get("allowed_paths", []), f"{prefix}.allowed_paths", errors, allow_empty=False)
        for allowed_path in allowed_paths:
            normalized = allowed_path.replace("\\", "/")
            if os.path.isabs(allowed_path) or normalized.startswith("../") or "/../" in normalized:
                errors.append(f"{prefix}.allowed_paths must stay inside working_directory: {allowed_path}")
            if SECRET_PATH_RE.search(normalized):
                errors.append(f"{prefix}.allowed_paths contains a protected path: {allowed_path}")
        _string_list(task.get("acceptance_checks", []), f"{prefix}.acceptance_checks", errors, allow_empty=False)

        routes = _string_list(task.get("routes", []), f"{prefix}.routes", errors, allow_empty=False)
        verifier_routes = _string_list(task.get("verifier_routes", []), f"{prefix}.verifier_routes", errors, allow_empty=False)
        _validate_route_ladder(routes, f"{prefix}.routes", errors)
        _validate_route_ladder(verifier_routes, f"{prefix}.verifier_routes", errors)
        if routes and verifier_routes and all(route in ROUTES for route in routes + verifier_routes):
            if complexity in COMPLEXITY_LEVELS and ROUTES[routes[0]].capability != COMPLEXITY_LEVELS[complexity]:
                errors.append(
                    f"{prefix}.routes must start at capability {COMPLEXITY_LEVELS[complexity]} "
                    f"for {complexity} complexity"
                )
            if ROUTES[routes[-1]].capability < 3:
                errors.append(f"{prefix}.routes must end with a frontier-capability fallback")
            if ROUTES[verifier_routes[-1]].capability < 3:
                errors.append(f"{prefix}.verifier_routes must end with a frontier-capability verifier")
            for route_index, worker_route in enumerate(routes):
                verifier_route = verifier_routes[min(route_index, len(verifier_routes) - 1)]
                if ROUTES[verifier_route].capability < ROUTES[worker_route].capability:
                    errors.append(f"{prefix}.verifier_routes becomes weaker than the worker at escalation step {route_index + 1}")
                    break
                if ROUTES[worker_route].provider == ROUTES[verifier_route].provider:
                    errors.append(f"{prefix} worker and verifier must use independent providers at escalation step {route_index + 1}")
                    break
        if routes and routes[0] == "openrouter-cheap" and not approval.get("allow_openrouter_primary", False):
            errors.append(f"{prefix}.routes cannot start with OpenRouter unless allow_openrouter_primary is approved")
        premium_used.update(route for route in routes + verifier_routes if route in ROUTES and ROUTES[route].premium)

    for task_id, deps in dependencies.items():
        for dependency in deps:
            if dependency == task_id:
                errors.append(f"task {task_id} cannot depend on itself")
            elif dependency not in task_ids:
                errors.append(f"task {task_id} depends on unknown task {dependency}")
    if _has_cycle(task_ids, dependencies):
        errors.append("task dependencies contain a cycle")

    final_gate = plan.get("final_gate")
    if not isinstance(final_gate, dict):
        errors.append("final_gate must be an object")
    else:
        final_routes = _string_list(final_gate.get("routes", []), "final_gate.routes", errors, allow_empty=False)
        final_verifiers = _string_list(final_gate.get("verifier_routes", []), "final_gate.verifier_routes", errors, allow_empty=False)
        _validate_route_ladder(final_routes, "final_gate.routes", errors)
        _validate_route_ladder(final_verifiers, "final_gate.verifier_routes", errors)
        final_checks = _string_list(
            final_gate.get("acceptance_checks", []),
            "final_gate.acceptance_checks",
            errors,
            allow_empty=False,
        )
        if any(GLOBAL_CLEAN_CHECK_RE.search(check) for check in final_checks):
            errors.append(
                "final_gate.acceptance_checks must not require a globally clean worktree; "
                "compare the approved scope against the pre-workflow baseline"
            )
        if final_routes and final_verifiers and all(route in ROUTES for route in final_routes + final_verifiers):
            if ROUTES[final_routes[-1]].capability < 3:
                errors.append("final_gate.routes must end with a frontier-capability fallback")
            if ROUTES[final_verifiers[-1]].capability < 3:
                errors.append("final_gate.verifier_routes must end with a frontier-capability verifier")
            for route_index, worker_route in enumerate(final_routes):
                verifier_route = final_verifiers[min(route_index, len(final_verifiers) - 1)]
                if ROUTES[verifier_route].capability < ROUTES[worker_route].capability:
                    errors.append(
                        "final_gate.verifier_routes becomes weaker than the repair worker "
                        f"at escalation step {route_index + 1}"
                    )
                    break
                if ROUTES[worker_route].provider == ROUTES[verifier_route].provider:
                    errors.append(
                        "final_gate repair worker and verifier must use independent providers "
                        f"at escalation step {route_index + 1}"
                    )
                    break
        premium_used.update(route for route in final_routes + final_verifiers if route in ROUTES and ROUTES[route].premium)

    missing_approvals = sorted(premium_used.difference(premium_routes))
    if missing_approvals:
        errors.append(f"premium routes lack approval: {', '.join(missing_approvals)}")
    if premium_used and max_budget is None:
        errors.append("premium routes require approval.max_api_budget_usd")

    if errors:
        raise PlanValidationError(errors)
    return plan


def state_directory() -> Path:
    configured = os.environ.get("AI_ROUTER_STATE_DIR", "")
    if not configured or "${" in configured:
        configured = str(Path.home() / ".local" / "state" / "ai-router")
    path = Path(configured).expanduser()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.chmod(0o700)
    except OSError:
        pass
    return path


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def plan_summary(plan: dict[str, Any], plan_id: str) -> dict[str, Any]:
    tasks = []
    for task in plan["tasks"]:
        tasks.append(
            {
                "id": task["id"],
                "permission": task["permission"],
                "complexity": task["complexity"],
                "dependencies": task["dependencies"],
                "routes": task["routes"],
                "verifier_routes": task["verifier_routes"],
                "worker_ladder": [route_summary(route) for route in task["routes"]],
                "verifier_ladder": [route_summary(route) for route in task["verifier_routes"]],
                "acceptance_checks": task["acceptance_checks"],
            }
        )
    return {
        "plan_id": plan_id,
        "workflow_id": plan["workflow_id"],
        "objective": plan["objective"],
        "working_directory": plan["working_directory"],
        "tasks": tasks,
        "final_gate": plan["final_gate"],
        "final_gate_worker_ladder": [route_summary(route) for route in plan["final_gate"]["routes"]],
        "final_gate_verifier_ladder": [route_summary(route) for route in plan["final_gate"]["verifier_routes"]],
        "minimum_visible_model_agents": len(tasks) * 2 + 1,
        "premium_routes": plan.get("approval", {}).get("premium_routes", []),
        "max_api_budget_usd": plan.get("approval", {}).get("max_api_budget_usd"),
    }


def route_summary(alias: str) -> dict[str, Any]:
    route = ROUTES[alias]
    return {
        "alias": alias,
        "provider": route.provider,
        "model": resolved_model(alias),
        "effort": route.effort,
        "capability": route.capability,
        "premium": route.premium,
        "native_claude_workflow": route.native,
    }


def prepare_plan(plan: dict[str, Any]) -> dict[str, Any]:
    validate_plan(plan)
    plan_id = uuid.uuid4().hex
    payload = {
        "plan_id": plan_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending-approval",
        "plan": plan,
    }
    path = state_directory() / "plans" / f"{plan_id}.json"
    _atomic_json(path, payload)
    return plan_summary(plan, plan_id)


def compile_workflow(plan_id: str, template_path: Path) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{32}", plan_id):
        raise PlanValidationError(["plan_id is invalid"])
    plan_path = state_directory() / "plans" / f"{plan_id}.json"
    if not plan_path.is_file():
        raise PlanValidationError(["prepared plan was not found"])
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    if payload.get("status") not in {"pending-approval", "compiled"}:
        raise PlanValidationError(["prepared plan is not compilable"])
    plan = validate_plan(payload.get("plan"))
    template = template_path.read_text(encoding="utf-8")
    plan_marker = "/*__AI_ROUTER_PLAN__*/ null"
    meta_marker = "/*__AI_ROUTER_META__*/ null"
    if template.count(plan_marker) != 1 or template.count(meta_marker) != 1:
        raise RuntimeError("workflow template markers are missing or duplicated")
    workflow_meta = {
        "name": f"ai-router-{plan['workflow_id']}",
        "description": f"Visible multi-model route, verify, and escalation workflow: {plan['objective']}",
        "phases": [
            {"title": "Execute", "detail": "Run approved task workers; independent tasks may run concurrently"},
            {"title": "Verify", "detail": "Independently inspect every worker result and run acceptance checks"},
            {"title": "Escalate", "detail": "Move failed work to stronger models and require a new approach at frontier"},
            {"title": "Final gate", "detail": "Verify the combined worktree before completion"},
        ],
    }
    source = template.replace(meta_marker, json.dumps(workflow_meta, ensure_ascii=False, separators=(",", ":")))
    source = source.replace(plan_marker, json.dumps(plan, ensure_ascii=False, separators=(",", ":")))
    workflow_dir = state_directory() / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    script_path = workflow_dir / f"{plan_id}-{plan['workflow_id']}.js"
    descriptor = os.open(script_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(source)
    payload["status"] = "compiled"
    payload["compiled_at"] = datetime.now(timezone.utc).isoformat()
    payload["script_path"] = str(script_path)
    _atomic_json(plan_path, payload)
    return {
        "plan_id": plan_id,
        "workflow_id": plan["workflow_id"],
        "script_path": str(script_path),
        "tasks": len(plan["tasks"]),
        "instruction": "Launch the native Workflow tool with scriptPath exactly as returned.",
    }


class UsageStore:
    def __init__(self, root: Path | None = None):
        self.root = root or state_directory()
        self.path = self.root / "usage.jsonl"

    def append(self, record: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        descriptor = os.open(self.path, flags, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.write(line)
            handle.flush()
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def aggregate(self, period: str = "day", workflow_id: str | None = None) -> dict[str, Any]:
        if period not in {"day", "week", "all"}:
            raise ValueError("period must be day, week, or all")
        now = datetime.now(timezone.utc)
        cutoff = None
        if period == "day":
            cutoff = now - timedelta(days=1)
        elif period == "week":
            cutoff = now - timedelta(days=7)

        records: list[dict[str, Any]] = []
        if self.path.is_file():
            with self.path.open("r", encoding="utf-8") as handle:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
                for line in handle:
                    try:
                        record = json.loads(line)
                        timestamp = datetime.fromisoformat(record["timestamp"])
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                    if cutoff and timestamp < cutoff:
                        continue
                    if workflow_id and record.get("workflow_id") != workflow_id:
                        continue
                    records.append(record)
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        by_route: dict[str, dict[str, Any]] = {}
        totals = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "cache_read_tokens": 0}
        verdicts = {"pass": 0, "fail": 0, "blocked": 0}
        total_cost = 0.0
        known_cost_records = 0
        for record in records:
            if record.get("event") == "verdict":
                verdict = record.get("verdict")
                if verdict in verdicts:
                    verdicts[verdict] += 1
                continue
            if record.get("event") != "delegate":
                continue
            route = record.get("route", "unknown")
            bucket = by_route.setdefault(route, {"calls": 0, "completed": 0, "failed": 0, "cost_usd": 0.0})
            bucket["calls"] += 1
            if record.get("status") == "completed":
                bucket["completed"] += 1
            else:
                bucket["failed"] += 1
            usage = record.get("usage") or {}
            for key in totals:
                value = usage.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    totals[key] += int(value)
            cost = record.get("cost_usd")
            if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                total_cost += float(cost)
                bucket["cost_usd"] += float(cost)
                known_cost_records += 1

        return {
            "period": period,
            "workflow_id": workflow_id,
            "external_calls": sum(bucket["calls"] for bucket in by_route.values()),
            "usage": totals,
            "known_external_cost_usd": round(total_cost, 8),
            "cost_records": known_cost_records,
            "verdicts": verdicts,
            "by_route": by_route,
            "note": "Native Claude workflow tokens are shown by /workflows. Subscription remaining quota is not available through a reliable API.",
        }


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def parse_agent_jsonl(stdout: str, engine: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)

    texts: list[str] = []
    usage = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "cache_read_tokens": 0}
    cost_usd: float | None = None

    if engine == "codex":
        for event in events:
            item = event.get("item")
            if event.get("type") == "item.completed" and isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text)
            candidate = event.get("usage")
            if isinstance(candidate, dict):
                usage = {
                    "input_tokens": int(candidate.get("input_tokens") or 0),
                    "output_tokens": int(candidate.get("output_tokens") or 0),
                    "reasoning_tokens": int(candidate.get("reasoning_tokens") or 0),
                    "cache_read_tokens": int(candidate.get("cached_input_tokens") or candidate.get("cache_read_tokens") or 0),
                }
    else:
        seen_parts: set[str] = set()
        seen_text_parts: set[str] = set()
        seen_cost_parts: set[str] = set()
        for event in events:
            part = event.get("part")
            if not isinstance(part, dict):
                part = event.get("properties", {}).get("part") if isinstance(event.get("properties"), dict) else None
            if isinstance(part, dict):
                part_id = str(part.get("id") or f"{event.get('type')}:{len(seen_parts)}")
                if (
                    part.get("type") == "text"
                    and isinstance(part.get("text"), str)
                    and part.get("text", "").strip()
                    and part_id not in seen_text_parts
                ):
                    texts.append(part["text"])
                    seen_text_parts.add(part_id)
                tokens = part.get("tokens")
                if isinstance(tokens, dict) and part_id not in seen_parts:
                    seen_parts.add(part_id)
                    usage["input_tokens"] += int(tokens.get("input") or tokens.get("input_tokens") or 0)
                    usage["output_tokens"] += int(tokens.get("output") or tokens.get("output_tokens") or 0)
                    usage["reasoning_tokens"] += int(tokens.get("reasoning") or tokens.get("reasoning_tokens") or 0)
                    cache = tokens.get("cache")
                    if isinstance(cache, dict):
                        usage["cache_read_tokens"] += int(cache.get("read") or 0)
                    else:
                        usage["cache_read_tokens"] += int(tokens.get("cache_read") or 0)
                part_cost = _number(part.get("cost"))
                if part_cost is not None and part_id not in seen_cost_parts:
                    cost_usd = (cost_usd or 0.0) + part_cost
                    seen_cost_parts.add(part_id)
            if isinstance(event.get("result"), str) and event["result"].strip():
                texts.append(event["result"])

    if not texts:
        plain_lines = [line for line in stdout.splitlines() if line.strip() and not line.lstrip().startswith("{")]
        if plain_lines:
            texts.append("\n".join(plain_lines[-200:]))
    output = texts[-1] if texts else ""
    return {"output": output, "usage": usage, "cost_usd": cost_usd, "event_count": len(events)}


def parse_model_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    candidates = [stripped]
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, re.IGNORECASE | re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1))
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if 0 <= first_brace < last_brace:
        candidates.append(stripped[first_brace : last_brace + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _private_config() -> dict[str, Any]:
    path = Path(os.environ.get("AI_ROUTER_PRIVATE_CONFIG", Path.home() / ".config" / "ai-coding-router" / "providers.private.json"))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def resolved_model(alias: str) -> str:
    route = ROUTES[alias]
    if route.model:
        return route.model
    mapping = {
        "corporate-pro": ("extra_litellm", "smart_model"),
        "minimax": ("minimax", "cheap_model"),
        "cheap": ("deepseek", "cheap_model"),
        "openrouter-cheap": ("openrouter", "cheap_model"),
        "kimi-k3": ("openrouter", "smart_model"),
    }
    provider, field = mapping[alias]
    return str(_private_config().get(provider, {}).get(field) or alias)


def router_runner(plugin_root: Path) -> Path:
    override = os.environ.get("AI_ROUTER_RUNNER", "")
    return Path(override).expanduser() if override else plugin_root / "bin" / "router-run"


def run_delegate(arguments: dict[str, Any], plugin_root: Path, store: UsageStore | None = None) -> dict[str, Any]:
    route_alias = arguments.get("route")
    if route_alias not in ROUTES:
        raise ValueError(f"unknown route: {route_alias}")
    route = ROUTES[route_alias]
    if route.native:
        raise ValueError(f"{route_alias} is native to Claude Workflow and must not be delegated through MCP")
    profile = arguments.get("profile")
    if profile not in PROFILES:
        raise ValueError("profile must be review, verify, or build")
    role = arguments.get("role")
    if role not in ROLES:
        raise ValueError(f"role must be one of: {', '.join(sorted(ROLES))}")
    record_verdict_from_output = arguments.get("record_verdict_from_output", False)
    if not isinstance(record_verdict_from_output, bool):
        raise ValueError("record_verdict_from_output must be a boolean")
    if record_verdict_from_output and role not in {"verifier", "final-gate"}:
        raise ValueError("record_verdict_from_output is only valid for verifier and final-gate roles")
    working_directory = arguments.get("working_directory")
    if not isinstance(working_directory, str) or not os.path.isabs(working_directory) or not os.path.isdir(working_directory):
        raise ValueError("working_directory must be an existing absolute path")
    prompt = arguments.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be non-empty")
    if len(prompt.encode("utf-8")) > 1_000_000:
        raise ValueError("prompt exceeds the 1 MB safety limit")
    workflow_id = arguments.get("workflow_id")
    task_id = arguments.get("task_id")
    if not isinstance(workflow_id, str) or not ID_RE.fullmatch(workflow_id):
        raise ValueError("workflow_id is invalid")
    if not isinstance(task_id, str) or not ID_RE.fullmatch(task_id):
        raise ValueError("task_id is invalid")

    timeout_seconds = arguments.get("timeout_seconds", 3600)
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or not 30 <= timeout_seconds <= 14400:
        raise ValueError("timeout_seconds must be between 30 and 14400")

    command = [
        str(router_runner(plugin_root)),
        "--profile",
        profile,
        "--model",
        route_alias,
        "--dir",
        working_directory,
        "--json",
    ]
    if profile == "build":
        command.append("--worktree-confirmed")
    if route.premium:
        budget = arguments.get("budget_usd")
        if not isinstance(budget, (int, float)) or isinstance(budget, bool) or budget <= 0:
            raise ValueError("premium route requires positive budget_usd")
        command.extend(["--confirm-premium", "--budget-usd", str(budget)])

    started = time.monotonic()
    status = "failed"
    return_code: int | None = None
    stdout = ""
    stderr = ""
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            env=os.environ.copy(),
        )
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        status = "completed" if return_code == 0 else ("unavailable" if "UNAVAILABLE" in stderr else "failed")
    except subprocess.TimeoutExpired as error:
        status = "timed_out"
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

    parsed = parse_agent_jsonl(stdout, route.engine)
    duration_ms = int((time.monotonic() - started) * 1000)
    result = {
        "status": status,
        "workflow_id": workflow_id,
        "task_id": task_id,
        "role": role,
        "route": route_alias,
        "provider": route.provider,
        "model": resolved_model(route_alias),
        "profile": profile,
        "duration_ms": duration_ms,
        "return_code": return_code,
        "output": parsed["output"],
        "usage": parsed["usage"],
        "cost_usd": parsed["cost_usd"],
        "event_count": parsed["event_count"],
        "error": stderr.strip()[-4000:] if status != "completed" else None,
        "verdict_recorded": False,
    }
    usage_store = store or UsageStore()
    usage_store.append(
        {
            "event": "delegate",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": workflow_id,
            "task_id": task_id,
            "role": role,
            "route": route_alias,
            "provider": route.provider,
            "model": result["model"],
            "profile": profile,
            "status": status,
            "duration_ms": duration_ms,
            "usage": parsed["usage"],
            "cost_usd": parsed["cost_usd"],
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }
    )
    if record_verdict_from_output:
        verdict_output = parse_model_json_object(result["output"])
        verdict = str((verdict_output or {}).get("verdict", "")).lower()
        if verdict in {"pass", "fail", "blocked"}:
            evidence = json.dumps(verdict_output, ensure_ascii=False, sort_keys=True)
            record_verdict(
                {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "verdict": verdict,
                    "route": route_alias,
                    "evidence": evidence,
                },
                usage_store,
            )
            result["verdict_recorded"] = True
    return result


def health(routes: list[str], plugin_root: Path, *, fresh: bool = False) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    check = plugin_root / "bin" / "router-check"
    for alias in routes:
        if alias not in ROUTES:
            results.append({"route": alias, "available": False, "detail": "unknown route"})
            continue
        route = ROUTES[alias]
        if route.native:
            available = shutil.which("claude") is not None
            results.append(
                {
                    "route": alias,
                    "available": available,
                    "cached": False,
                    "model": route.model,
                    "effort": route.effort,
                    "entitlement_check": "on_generation",
                    "detail": "claude command" if available else "claude command missing",
                }
            )
            continue
        command = [str(check)]
        if fresh:
            command.append("--fresh")
        command.append(alias)
        completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
        detail = (completed.stdout or completed.stderr).strip()
        results.append(
            {
                "route": alias,
                "available": completed.returncode == 0,
                "cached": "cached=true" in detail,
                "model": resolved_model(alias),
                "effort": route.effort,
                "entitlement_check": "on_generation" if route.engine == "codex" else "not_applicable",
                "detail": detail,
            }
        )
    return {"routes": results, "all_available": all(item["available"] for item in results)}


def record_verdict(arguments: dict[str, Any], store: UsageStore | None = None) -> dict[str, Any]:
    workflow_id = arguments.get("workflow_id")
    task_id = arguments.get("task_id")
    verdict = arguments.get("verdict")
    if not isinstance(workflow_id, str) or not ID_RE.fullmatch(workflow_id):
        raise ValueError("workflow_id is invalid")
    if not isinstance(task_id, str) or not ID_RE.fullmatch(task_id):
        raise ValueError("task_id is invalid")
    if verdict not in {"pass", "fail", "blocked"}:
        raise ValueError("verdict must be pass, fail, or blocked")
    record = {
        "event": "verdict",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow_id": workflow_id,
        "task_id": task_id,
        "verdict": verdict,
        "route": arguments.get("route"),
        "evidence_sha256": hashlib.sha256(str(arguments.get("evidence", "")).encode("utf-8")).hexdigest(),
    }
    (store or UsageStore()).append(record)
    return {"recorded": True, "workflow_id": workflow_id, "task_id": task_id, "verdict": verdict}
