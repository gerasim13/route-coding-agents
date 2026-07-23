from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


SESSION_STATES = {
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
}
TERMINAL_STATES = {"VERIFIED", "BLOCKED"}
TRANSITIONS = {
    "INSPECTING": {"DISCOVERING", "PLANNING", "BLOCKED"},
    "DISCOVERING": {"AWAITING_USER_DECISION", "PLANNING", "BLOCKED"},
    "AWAITING_USER_DECISION": {"DISCOVERING", "GRILLING", "PLANNING", "BLOCKED"},
    "PLANNING": {"GRILLING", "CRITIQUING", "BLOCKED"},
    "GRILLING": {"AWAITING_USER_DECISION", "PLANNING", "CRITIQUING", "BLOCKED"},
    "CRITIQUING": {"PLANNING", "READY_FOR_APPROVAL", "BLOCKED"},
    "READY_FOR_APPROVAL": {"EXECUTING", "BLOCKED"},
    "EXECUTING": {"AWAITING_SCOPE_APPROVAL", "VERIFIED", "BLOCKED"},
    "AWAITING_SCOPE_APPROVAL": {"PLANNING", "EXECUTING", "BLOCKED"},
    "VERIFIED": set(),
    "BLOCKED": set(),
}
CHECK_LEVELS = {"targeted", "affected", "regression"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SENSITIVE_PATH_RE = re.compile(
    r"(^|/)(?:\.env(?:\.[^/]*)?|[^/]*(?:credential|secret)[^/]*)($|/)",
    re.IGNORECASE,
)
PROTECTED_COMMAND_PATH_RE = re.compile(
    r"(?:^|[\s'\"=])(?:[^\s'\";&|]*/)?(?:"
    r"\.env(?:\.[A-Za-z0-9_.-]+)?|"
    r"(?:credentials?|secrets?)(?:\.[A-Za-z0-9_.-]+)?"
    r")(?:$|[\s'\";|&])",
    re.IGNORECASE,
)
SENSITIVE_ENV_NAME_RE = re.compile(
    r"(?:^|_)(?:api_?key|auth|cookie|credential|key|pass(?:word)?|secret|token)(?:_|$)",
    re.IGNORECASE,
)
FORBIDDEN_CHECK_RE = re.compile(
    r"(?:"
    r"\brm\s+-[A-Za-z]*r[A-Za-z]*f\b|"
    r"\bgit\s+(?:reset|clean|checkout|restore|stash|commit|push|merge|rebase)\b|"
    r"\b(?:sudo|shutdown|reboot|mkfs)\b"
    r")",
    re.IGNORECASE,
)
REDACTIONS: list[tuple[re.Pattern[str], bool]] = [
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s\"']+"), True),
    (re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{8,}\b"), False),
    (re.compile(r"(?i)\bAIza[A-Za-z0-9_-]{8,}\b"), False),
    (re.compile(r"(?i)\b((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s\"']+"), True),
]
GENERATED_DIRS = {
    ".git",
    ".gradle",
    ".pytest_cache",
    ".swiftpm",
    "build",
    "dist",
    "node_modules",
    "target",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_root(root: Path | None = None) -> Path:
    if root is None:
        configured = os.environ.get("AI_ROUTER_STATE_DIR", "")
        if not configured or "${" in configured:
            configured = str(Path.home() / ".local" / "state" / "ai-router")
        root = Path(configured).expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    return root


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def redact_text(value: str, *, limit: int | None = None) -> str:
    redacted = value
    for pattern, preserve_prefix in REDACTIONS:
        replacement = (lambda match: f"{match.group(1)}[REDACTED]") if preserve_prefix else "[REDACTED]"
        redacted = pattern.sub(replacement, redacted)
    if limit is not None and len(redacted) > limit:
        return redacted[: limit // 2] + "\n...[TRUNCATED]...\n" + redacted[-limit // 2 :]
    return redacted


def _sanitize_json(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[TRUNCATED]"
    if isinstance(value, str):
        return redact_text(value, limit=20_000)
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in list(value.items())[:200]:
            safe_key = redact_text(str(key), limit=200)
            result[safe_key] = _sanitize_json(item, depth=depth + 1)
        return result
    if isinstance(value, list):
        return [_sanitize_json(item, depth=depth + 1) for item in value[:500]]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return redact_text(str(value), limit=2_000)


def _git(path: Path, *arguments: str, timeout: int = 30) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(path), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def _git_text(path: Path, *arguments: str) -> str:
    completed = _git(path, *arguments)
    if completed.returncode != 0:
        return ""
    return completed.stdout.decode("utf-8", errors="replace").strip()


def _worktree_identity(working_directory: str | Path) -> dict[str, str]:
    path = Path(working_directory).expanduser().resolve()
    if not path.is_dir():
        raise ValueError("working_directory must be an existing directory")
    top_level = _git_text(path, "rev-parse", "--show-toplevel")
    canonical = Path(top_level).resolve() if top_level else path
    common_dir = _git_text(canonical, "rev-parse", "--git-common-dir")
    if common_dir:
        common_path = Path(common_dir)
        if not common_path.is_absolute():
            common_path = (canonical / common_path).resolve()
        common_dir = str(common_path)
    branch = _git_text(canonical, "branch", "--show-current")
    head = _git_text(canonical, "rev-parse", "HEAD")
    return {
        "working_directory": str(path),
        "worktree": str(canonical),
        "git_common_directory": common_dir,
        "branch": branch,
        "head": head,
    }


def _is_generated_path(relative: str) -> bool:
    parts = Path(relative).parts
    return any(part in GENERATED_DIRS for part in parts)


def workspace_fingerprint(working_directory: str | Path) -> str:
    identity = _worktree_identity(working_directory)
    root = Path(identity["worktree"])
    hasher = hashlib.sha256()
    hasher.update(json.dumps(identity, sort_keys=True).encode("utf-8"))
    if identity["head"]:
        for arguments in (
            ("diff", "--binary", "--no-ext-diff"),
            ("diff", "--cached", "--binary", "--no-ext-diff"),
        ):
            completed = _git(root, *arguments, timeout=120)
            hasher.update(completed.stdout)
            hasher.update(completed.stderr)
        untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z", timeout=60)
        for raw_path in sorted(item for item in untracked.stdout.split(b"\0") if item):
            relative = raw_path.decode("utf-8", errors="replace")
            if _is_generated_path(relative) or SENSITIVE_PATH_RE.search(relative):
                continue
            file_path = root / relative
            try:
                metadata = file_path.stat()
            except OSError:
                continue
            hasher.update(relative.encode("utf-8"))
            hasher.update(f"{metadata.st_size}:{metadata.st_mtime_ns}".encode("ascii"))
            if file_path.is_file() and metadata.st_size <= 1_000_000:
                try:
                    hasher.update(file_path.read_bytes())
                except OSError:
                    pass
    else:
        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file():
                continue
            relative = str(file_path.relative_to(root))
            if _is_generated_path(relative) or SENSITIVE_PATH_RE.search(relative):
                continue
            metadata = file_path.stat()
            hasher.update(relative.encode("utf-8"))
            hasher.update(f"{metadata.st_size}:{metadata.st_mtime_ns}".encode("ascii"))
    return hasher.hexdigest()


def _candidate_checks(root: Path) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []

    def add(level: str, command: str, source: str) -> None:
        if not any(item["command"] == command for item in candidates):
            candidates.append({"level": level, "command": command, "source": source})

    package_json = root / "package.json"
    if package_json.is_file():
        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
        except (OSError, json.JSONDecodeError, AttributeError):
            scripts = {}
        if isinstance(scripts, dict):
            for name, level in (("test", "regression"), ("lint", "affected"), ("typecheck", "affected"), ("build", "affected")):
                if isinstance(scripts.get(name), str):
                    add(level, f"npm run {name}", "package.json")
    if (root / "Cargo.toml").is_file():
        add("regression", "cargo test", "Cargo.toml")
        add("affected", "cargo clippy --all-targets --all-features", "Cargo.toml")
    if (root / "pyproject.toml").is_file() or (root / "pytest.ini").is_file():
        add("regression", "python3 -m pytest", "Python test configuration")
    if (root / "go.mod").is_file():
        add("regression", "go test ./...", "go.mod")
    if (root / "Package.swift").is_file():
        add("regression", "swift test", "Package.swift")
    if (root / "gradlew").is_file():
        add("regression", "./gradlew test", "gradlew")
    if (root / "justfile").is_file() or (root / "Justfile").is_file():
        add("regression", "just test", "justfile")
    if (root / "Makefile").is_file():
        try:
            makefile = (root / "Makefile").read_text(encoding="utf-8", errors="replace")
        except OSError:
            makefile = ""
        if re.search(r"(?m)^test\s*:", makefile):
            add("regression", "make test", "Makefile")
    return candidates


def inspect_workspace(working_directory: str) -> dict[str, Any]:
    identity = _worktree_identity(working_directory)
    root = Path(identity["worktree"])
    status = _git_text(root, "status", "--short", "--untracked-files=all")
    changed_files = []
    for line in status.splitlines():
        candidate = line[3:].strip() if len(line) > 3 else ""
        if candidate and not SENSITIVE_PATH_RE.search(candidate):
            changed_files.append(candidate)
    tracked_count = 0
    extension_counts: dict[str, int] = {}
    tracked_paths: list[str] = []
    tracked = _git(root, "ls-files", "-z")
    if tracked.returncode == 0:
        tracked_paths = [
            item.decode("utf-8", errors="replace")
            for item in tracked.stdout.split(b"\0")
            if item
        ]
        tracked_count = len(tracked_paths)
        for relative in tracked_paths:
            if SENSITIVE_PATH_RE.search(relative):
                continue
            suffix = Path(relative).suffix.lower() or "[no-extension]"
            extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
    manifest_names = {
        "AGENTS.md",
        "CLAUDE.md",
        "Cargo.toml",
        "Package.swift",
        "README.md",
        "go.mod",
        "package.json",
        "pyproject.toml",
    }
    repository_markers = [
        relative
        for relative in tracked_paths
        if Path(relative).name in manifest_names
        or relative.startswith(".github/workflows/")
        or relative.startswith(".gitlab-ci")
    ][:200]
    language_extensions = sorted(
        extension_counts.items(), key=lambda item: (-item[1], item[0])
    )[:20]
    return {
        **identity,
        "workspace_fingerprint": workspace_fingerprint(root),
        "changed_files": changed_files[:500],
        "changed_file_count": len(changed_files),
        "tracked_file_count": tracked_count,
        "repository_markers": repository_markers,
        "extension_counts": [
            {"extension": extension, "count": count}
            for extension, count in language_extensions
        ],
        "candidate_checks": _candidate_checks(root),
        "inspection_is_non_generating": True,
    }


def _session_paths(session_id: str, root: Path) -> tuple[Path, Path]:
    if not re.fullmatch(r"[a-f0-9]{32}", session_id):
        raise ValueError("session_id is invalid")
    session_path = root / "sessions" / f"{session_id}.json"
    return session_path, root / "sessions" / "by-worktree"


def _workflow_lease_path(payload: dict[str, Any], root: Path) -> Path:
    worktree = str(payload["identity"]["worktree"])
    key = hashlib.sha256(worktree.encode("utf-8")).hexdigest()
    return root / "leases" / f"{key}.workflow.json"


def _acquire_workflow_lease(payload: dict[str, Any], root: Path) -> None:
    path = _workflow_lease_path(payload, root)
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if existing.get("session_id") != payload["session_id"]:
            raise ValueError(
                "another adaptive build workflow already owns this worktree; "
                "resume or reconcile that session first"
            )
    _atomic_json(
        path,
        {
            "session_id": payload["session_id"],
            "worktree": payload["identity"]["worktree"],
            "acquired_at": _utc_now(),
            "owner_pid": os.getpid(),
        },
    )


def _release_workflow_lease(payload: dict[str, Any], root: Path) -> None:
    path = _workflow_lease_path(payload, root)
    if not path.is_file():
        return
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if existing.get("session_id") == payload["session_id"]:
        path.unlink(missing_ok=True)


def _session_summary(payload: dict[str, Any], *, resumed: bool) -> dict[str, Any]:
    return {
        "session_id": payload["session_id"],
        "resumed": resumed,
        "objective": payload["objective"],
        "state": payload["state"],
        "working_directory": payload["identity"]["working_directory"],
        "worktree": payload["identity"]["worktree"],
        "branch": payload["identity"]["branch"],
        "head": payload["identity"]["head"],
        "workspace_fingerprint": payload["workspace_fingerprint"],
        "updated_at": payload["updated_at"],
        "last_checkpoint": payload["checkpoints"][-1] if payload["checkpoints"] else None,
    }


def start_session(objective: str, working_directory: str, root: Path | None = None) -> dict[str, Any]:
    if not isinstance(objective, str) or not objective.strip():
        raise ValueError("objective must be non-empty")
    state = _state_root(root)
    identity = _worktree_identity(working_directory)
    worktree_key = hashlib.sha256(
        f"{identity['worktree']}\0{identity['git_common_directory']}".encode("utf-8")
    ).hexdigest()
    index_path = state / "sessions" / "by-worktree" / f"{worktree_key}.json"
    if index_path.is_file():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            existing_path, _ = _session_paths(str(index.get("session_id", "")), state)
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            existing = {}
        if existing.get("state") in SESSION_STATES.difference(TERMINAL_STATES):
            return _session_summary(existing, resumed=True)

    session_id = uuid.uuid4().hex
    now = _utc_now()
    payload = {
        "schema_version": 1,
        "session_id": session_id,
        "objective": redact_text(objective.strip(), limit=20_000),
        "state": "INSPECTING",
        "identity": identity,
        "workspace_fingerprint": workspace_fingerprint(identity["worktree"]),
        "created_at": now,
        "updated_at": now,
        "checkpoints": [],
    }
    session_path, _ = _session_paths(session_id, state)
    _atomic_json(session_path, payload)
    _atomic_json(index_path, {"session_id": session_id, "updated_at": now})
    return _session_summary(payload, resumed=False)


def session_status(
    *,
    session_id: str | None = None,
    working_directory: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    state = _state_root(root)
    if session_id is None:
        if not working_directory:
            raise ValueError("session_id or working_directory is required")
        identity = _worktree_identity(working_directory)
        worktree_key = hashlib.sha256(
            f"{identity['worktree']}\0{identity['git_common_directory']}".encode("utf-8")
        ).hexdigest()
        index_path = state / "sessions" / "by-worktree" / f"{worktree_key}.json"
        if not index_path.is_file():
            return {"found": False}
        index = json.loads(index_path.read_text(encoding="utf-8"))
        session_id = str(index.get("session_id", ""))
    session_path, _ = _session_paths(session_id, state)
    if not session_path.is_file():
        return {"found": False}
    payload = json.loads(session_path.read_text(encoding="utf-8"))
    summary = _session_summary(payload, resumed=True)
    summary["found"] = True
    summary["workspace_changed"] = (
        workspace_fingerprint(payload["identity"]["worktree"]) != payload["workspace_fingerprint"]
    )
    return summary


def checkpoint_session(
    session_id: str,
    next_state: str,
    summary: str,
    data: dict[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    state = _state_root(root)
    session_path, _ = _session_paths(session_id, state)
    if not session_path.is_file():
        raise ValueError("adaptive session was not found")
    payload = json.loads(session_path.read_text(encoding="utf-8"))
    current = payload.get("state")
    if next_state not in SESSION_STATES:
        raise ValueError("next_state is invalid")
    if next_state not in TRANSITIONS.get(str(current), set()):
        raise ValueError(f"invalid session transition: {current} -> {next_state}")
    if next_state == "EXECUTING":
        _acquire_workflow_lease(payload, state)
    now = _utc_now()
    checkpoint = {
        "from": current,
        "to": next_state,
        "at": now,
        "summary": redact_text(summary or "", limit=20_000),
        "data": _sanitize_json(data or {}),
    }
    payload["state"] = next_state
    payload["updated_at"] = now
    payload["workspace_fingerprint"] = workspace_fingerprint(payload["identity"]["worktree"])
    payload.setdefault("checkpoints", []).append(checkpoint)
    payload["checkpoints"] = payload["checkpoints"][-200:]
    _atomic_json(session_path, payload)
    if current == "EXECUTING" and next_state in {
        "AWAITING_SCOPE_APPROVAL",
        "VERIFIED",
        "BLOCKED",
    }:
        _release_workflow_lease(payload, state)
    return _session_summary(payload, resumed=True)


def _validate_check_command(command: str) -> str:
    if not isinstance(command, str) or not command.strip():
        raise ValueError("check command must be non-empty")
    command = command.strip()
    if len(command.encode("utf-8")) > 16_000:
        raise ValueError("check command is too large")
    if "\x00" in command or FORBIDDEN_CHECK_RE.search(command) or PROTECTED_COMMAND_PATH_RE.search(command):
        raise ValueError("check command contains a forbidden operation or protected path")
    return command


def _safe_check_environment() -> tuple[dict[str, str], list[str]]:
    safe: dict[str, str] = {}
    removed_values: list[str] = []
    for name, value in os.environ.items():
        proxy_with_credentials = "PROXY" in name.upper() and "@" in value
        if SENSITIVE_ENV_NAME_RE.search(name) or proxy_with_credentials:
            if len(value) >= 4:
                removed_values.append(value)
            continue
        safe[name] = value
    return safe, removed_values


def _redact_command_output(value: str, removed_values: list[str]) -> str:
    redacted = redact_text(value)
    for secret in sorted(set(removed_values), key=len, reverse=True):
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _run_command(command: str, working_directory: Path, timeout_seconds: int) -> dict[str, Any]:
    started = time.monotonic()
    environment, removed_values = _safe_check_environment()
    try:
        completed = subprocess.run(
            ["/bin/zsh", "-dfc", command],
            cwd=working_directory,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            env=environment,
        )
        return {
            "return_code": completed.returncode,
            "timed_out": False,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "stdout": _redact_command_output(completed.stdout, removed_values),
            "stderr": _redact_command_output(completed.stderr, removed_values),
        }
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "return_code": None,
            "timed_out": True,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "stdout": _redact_command_output(stdout, removed_values),
            "stderr": _redact_command_output(stderr, removed_values),
        }


def _failure_signature(attempts: list[dict[str, Any]]) -> str | None:
    failed = [attempt for attempt in attempts if attempt["return_code"] not in {0}]
    if not failed:
        return None
    value = "\n".join(
        f"{attempt['return_code']}:{attempt['stderr'][-8_000:]}:{attempt['stdout'][-4_000:]}"
        for attempt in failed
    )
    normalized = re.sub(r"\b\d+(?:\.\d+)?(?:ms|s)?\b", "#", value.lower())
    normalized = re.sub(r"/[^\s:]+", "<path>", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _write_check_log(
    root: Path,
    workflow_id: str,
    task_id: str,
    attempts: list[dict[str, Any]],
) -> Path:
    directory = root / "check-logs" / workflow_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f"{task_id}-{uuid.uuid4().hex}.log"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for index, attempt in enumerate(attempts, start=1):
            handle.write(
                f"attempt={index} return_code={attempt['return_code']} "
                f"timed_out={str(attempt['timed_out']).lower()} duration_ms={attempt['duration_ms']}\n"
            )
            handle.write("[stdout]\n")
            handle.write(attempt["stdout"])
            handle.write("\n[stderr]\n")
            handle.write(attempt["stderr"])
            handle.write("\n")
    return path


def run_check(
    *,
    command: str,
    working_directory: str,
    level: str,
    workflow_id: str,
    task_id: str,
    timeout_seconds: int = 3600,
    rerun_command: str | None = None,
    state_root: Path | None = None,
) -> dict[str, Any]:
    command = _validate_check_command(command)
    if rerun_command is not None:
        rerun_command = _validate_check_command(rerun_command)
    if level not in CHECK_LEVELS:
        raise ValueError("level must be targeted, affected, or regression")
    if not ID_RE.fullmatch(workflow_id) or not ID_RE.fullmatch(task_id):
        raise ValueError("workflow_id and task_id must be safe identifiers")
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or not 1 <= timeout_seconds <= 14_400:
        raise ValueError("timeout_seconds must be between 1 and 14400")
    directory = Path(working_directory).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError("working_directory must be an existing directory")
    root = _state_root(state_root)
    lease_directory = root / "leases"
    lease_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lease_key = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()
    lease_path = lease_directory / f"{lease_key}.test.lock"
    lease_descriptor = os.open(lease_path, os.O_RDWR | os.O_CREAT, 0o600)
    attempts: list[dict[str, Any]] = []
    before = workspace_fingerprint(directory)
    try:
        if fcntl is not None:
            fcntl.flock(lease_descriptor, fcntl.LOCK_EX)
        attempts.append(_run_command(command, directory, timeout_seconds))
        if attempts[0]["return_code"] != 0 and not attempts[0]["timed_out"] and rerun_command:
            attempts.append(_run_command(rerun_command, directory, timeout_seconds))
    finally:
        if fcntl is not None:
            fcntl.flock(lease_descriptor, fcntl.LOCK_UN)
        os.close(lease_descriptor)
    after = workspace_fingerprint(directory)
    workspace_changed = before != after
    first = attempts[0]
    last = attempts[-1]
    if workspace_changed:
        status = "STALE"
    elif first["timed_out"] or last["timed_out"]:
        status = "TIMED_OUT"
    elif first["return_code"] == 0:
        status = "PASS"
    elif len(attempts) > 1 and last["return_code"] == 0:
        status = "SUSPECTED_FLAKY"
    else:
        status = "FAIL"
    log_path = _write_check_log(root, workflow_id, task_id, attempts)
    combined_stdout = "\n".join(attempt["stdout"] for attempt in attempts)
    combined_stderr = "\n".join(attempt["stderr"] for attempt in attempts)
    return {
        "status": status,
        "level": level,
        "command": redact_text(command, limit=16_000),
        "rerun_command": redact_text(rerun_command, limit=16_000) if rerun_command else None,
        "attempts": len(attempts),
        "rerun_performed": len(attempts) > 1,
        "return_code": last["return_code"],
        "duration_ms": sum(int(attempt["duration_ms"]) for attempt in attempts),
        "workspace_fingerprint_before": before,
        "workspace_fingerprint_after": after,
        "workspace_changed": workspace_changed,
        "failure_signature": _failure_signature(attempts),
        "stdout_excerpt": redact_text(combined_stdout, limit=12_000),
        "stderr_excerpt": redact_text(combined_stderr, limit=12_000),
        "log_path": str(log_path),
        "zero_tolerance": True,
    }
