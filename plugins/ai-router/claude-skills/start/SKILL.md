---
name: start
description: Adaptively inspect, discover, plan, critique, and execute a rough software goal as visible Claude agents plus one native Dynamic Workflow. Use only when the user explicitly invokes /ai-router:start.
argument-hint: "<rough software goal>"
disable-model-invocation: true
---

# Start an adaptive AI Router session

Treat `$ARGUMENTS` as a rough goal in the current worktree. Never create another
worktree. This command owns the whole lifecycle from clarification to verified
execution.

The main conversation is the interactive controller. It may inspect and ask a
material question, but it must not implement the goal. Every model generation
for discovery, planning, criticism, implementation, diagnosis, repair, or
verification must be a separate visible agent. Local search, state updates, and
deterministic checks are not model generations.

## Load the controller

Use ToolSearch to load these `ai-router` MCP tools:

- `start_session`, `session_status`, `checkpoint_session`;
- `inspect_workspace`, `run_check`, `route_catalog`, `health`;
- `prepare_plan`, `compile_workflow`, `delegate`;
- `usage`.

Call `start_session` with the complete rough goal and absolute current working
directory. If it resumes the same objective, announce the checkpoint and
continue from it. If an unfinished session has a materially different
objective, ask whether to resume it; if the user declines, checkpoint it as
`BLOCKED`, start the new session, and continue.

Call `inspect_workspace` before any model. It is the free, non-generating pass.
Use its canonical worktree, fingerprint, changed files, repository shape, and
candidate checks. Do not read `.env`, credentials, secrets, or unrelated files.

## Discover only what is missing

Skip routed discovery when local evidence already establishes bounded paths,
contracts, dependencies, risks, and deterministic checks. Checkpoint directly
from `INSPECTING` to `PLANNING`.

Otherwise checkpoint `DISCOVERING` and create bounded, read-only visible agents:

- routine file/config semantics: Haiku, Codex Luna/low, MiniMax, or DeepSeek;
- cross-file or ambiguous semantics: corporate LiteLLM, Codex Terra/medium, or
  Claude Sonnet/medium;
- frontier only when strong discovery remains ambiguous.

Run independent discovery agents concurrently. Native Claude discovery uses
Claude's `Agent` tool with only read/search tools. External discovery uses a
Haiku wrapper agent that calls MCP `delegate` exactly once with
`role=discovery`, then faithfully returns its result. Never call `delegate`
directly from the main conversation.

Ask one question only when the answer materially changes product behavior,
public/persistence contract, architecture, security exposure, premium cost,
scope, or risk. Checkpoint `AWAITING_USER_DECISION` before asking and return to
`DISCOVERING` or `PLANNING` after the answer. Resolve repository facts yourself;
record minor choices as explicit assumptions.

Discovery may run bounded baseline checks through `run_check`. Any failure found
here is an active defect and must be included in the plan. “Pre-existing” is
provenance only, never permission to skip it.

## Require a frontier planner and critic

Every final plan uses two explicit visible frontier agents from independent
providers:

1. a planner that produces the complete task graph and adaptive test pyramid;
2. a critic that checks scope, architecture, dependencies, risks, test
   coverage, routing, verifier independence, and cost.

Normally pair Claude Opus/high or Claude Best/high with Codex Sol/high. Check
route health first. `claude-best` remains the hardest native Claude option and
may resolve to Fable when entitled; otherwise use explicit `claude-opus`.
Kimi K3 is a premium frontier fallback only after explicit user approval and a
dollar cap. A frontier planner and critic must never share a provider.

Native Claude planner/critic calls are normal visible `Agent` nodes with
read-only tools. External planner/critic calls are Haiku wrapper agents that
call `delegate` exactly once with `role=planner` or `role=plan-critic`. Planning
may automatically use subscriptions and corporate LiteLLM. Paid APIs must stay
inside the approved planning budget.

Checkpoint `PLANNING`, run the planner, checkpoint `CRITIQUING`, and run the
critic. A critic failure returns to a new planner revision and a new critic
agent. Continue until `critic_verdict=PASS` or a real blocker exists.

## Build RoutePlan v3

Use this shape:

```json
{
  "schema_version": 3,
  "workflow_id": "short-kebab-id",
  "objective": "complete objective",
  "working_directory": "/absolute/canonical/worktree",
  "planning": {
    "mode": "adaptive",
    "session_id": "32-lowercase-hex",
    "discovery_performed": true,
    "planner_route": "claude-opus",
    "critic_route": "codex-sol",
    "critic_verdict": "PASS",
    "assumptions": []
  },
  "approval": {
    "premium_routes": [],
    "max_api_budget_usd": null,
    "allow_openrouter_primary": false
  },
  "tasks": [
    {
      "id": "bounded-task",
      "objective": "bounded objective",
      "expected_artifact": "observable result",
      "dependencies": [],
      "non_goals": ["explicit exclusion"],
      "allowed_paths": ["src", "tests"],
      "permission": "build",
      "complexity": "routine",
      "acceptance_checks": ["observable acceptance contract"],
      "routes": ["minimax", "corporate-pro", "codex-sol"],
      "verifier_routes": ["codex-luna", "claude-sonnet", "claude-best"],
      "diagnosis_routes": ["corporate-pro", "codex-sol"],
      "test_intent_verifier_routes": ["codex-terra", "claude-opus"],
      "test_plan": {
        "targeted": [{"command": "small exact check"}],
        "affected": [{"command": "module check", "rerun_command": "same isolated module check"}]
      }
    }
  ],
  "final_gate": {
    "routes": ["corporate-pro", "codex-sol", "claude-best"],
    "verifier_routes": ["codex-terra", "claude-opus", "codex-sol"],
    "diagnosis_routes": ["corporate-pro", "codex-sol"],
    "acceptance_checks": ["complete project acceptance contract"],
    "test_plan": {
      "regression": [{"command": "complete mandatory suite", "rerun_command": "same isolated suite"}]
    }
  }
}
```

Routing rules:

- Initial route matches task complexity: routine=1, strong=2, frontier=3.
- Worker, verifier, diagnosis, and test-intent ladders end at frontier.
- Verifiers are at least as capable as workers and use an independent provider.
- Corporate LiteLLM and Codex subscription are preferred when equally adequate,
  then available Claude capacity, MiniMax, DeepSeek, and finally OpenRouter.
- Do not start OpenRouter as primary without approval.
- Do not raise model tier or reasoning effort without task complexity or failure
  evidence.
- Existing test edits require strong diagnosis and an independent test-intent
  verifier. Never weaken assertions merely to obtain green output.
- Targeted checks run after a change, affected checks after a task, and the
  complete regression suite always runs at the final gate.
- Any failure, flaky result, timeout, crash, infrastructure failure, or stale
  fingerprint is non-green.

## Show one execution card

Call `prepare_plan` and repair every validation error. Present its compact
summary: assumptions, task graph, allowed paths, worker/verifier/diagnosis
ladders with model and effort, targeted/affected/regression checks, planning
usage, known API cost, premium routes, and budget.

Checkpoint `READY_FOR_APPROVAL`, call `compile_workflow`, checkpoint
`EXECUTING`, then immediately launch Claude's native `Workflow` tool with the
returned `scriptPath`. Do not request a second textual confirmation. The native
Workflow approval card is the one execution confirmation.

The compiled workflow owns all edits and test-diagnose-repair loops. Check
runner nodes are visible but non-generating. A failed check gets one isolated
rerun, then a strong diagnosis. Weak-model failure escalates rather than
stopping. Each next task resets to its planned initial tier.

Tell the user that `/workflows` or Desktop Background Tasks shows every node.
Do not poll or duplicate execution in the main conversation.

## Finish, amend, or resume

- `VERIFIED`: checkpoint `VERIFIED` only after the mandatory regression and
  independent final verifier pass.
- `AWAITING_SCOPE_APPROVAL`: checkpoint that state, show the diagnosis and exact
  new paths, amend/re-criticize the plan after approval, and launch a new native
  Workflow card for remaining work.
- `BLOCKED`: checkpoint `BLOCKED` only for an exact external blocker or after
  independent frontier approaches are exhausted.
- If Claude restarts, call `session_status`, reconcile a changed fingerprint,
  preserve completed evidence, and compile only the remaining graph.

Never claim a failure is ignorable because it predates the session. There is no
successful state with known failures.
