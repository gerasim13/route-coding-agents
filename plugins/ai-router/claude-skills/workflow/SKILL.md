---
name: workflow
description: Plan and execute a software task as a visible Claude Dynamic Workflow that routes work across Claude, Codex, corporate LiteLLM, MiniMax, DeepSeek, and OpenRouter; independently verifies every model result; and escalates failures to stronger models. Use only when the user explicitly invokes /ai-router:workflow.
argument-hint: "<software task>"
disable-model-invocation: true
---

# Launch the mandatory AI Router workflow

Treat `$ARGUMENTS` as the objective. Operate from the current Claude working directory and never create another worktree.

This command is an execution contract, not optional advice:

- The main conversation may inspect a small amount of repository context only to create the route plan.
- It must never complete, implement, or verify the objective directly, even when the task looks trivial.
- After inspection it must call `prepare_plan`, `compile_workflow`, and the native `Workflow` tool. A direct answer is a failed command invocation.
- The human invoked a command containing the workflow opt-in keyword. If the native `Workflow` tool is still unavailable, stop without doing the task and report that Dynamic workflows must be enabled or Claude Code updated.
- Every model generation that works on or verifies the objective belongs in a visible workflow agent.

## Build the route plan

1. Inspect only enough repository context to split the objective into bounded tasks with real acceptance checks. Inspection is not task completion.
2. Use ToolSearch to load the `ai-router` MCP `route_catalog`, `health`, `prepare_plan`, and `compile_workflow` tools.
3. Even on this expert fast path, create two visible frontier planning agents from independent providers: one planner and one critic. Normally pair Claude Opus/high or Best/high with Codex Sol/high. The critic must return PASS before plan preparation. External planner or critic calls use a Haiku wrapper that calls `delegate` exactly once with `role=planner` or `role=plan-critic`.
4. Choose routes by task complexity, not by always starting cheap:
   - routine: `claude-haiku`, `codex-luna`, `minimax`, or `cheap`;
   - strong: `corporate-pro`, `codex-terra`, or `claude-sonnet`;
   - frontier: `codex-sol`, `claude-opus`, or `claude-best`;
   - specialist: `kimi-k3` only after the user explicitly authorizes it and a dollar cap;
   - `openrouter-cheap` is backup-only unless the user explicitly approves it as primary.
   Deterministic documentation comparisons, bounded grep/config inspection, formatting, and mechanical edits with a strong oracle are routine. Start them on a routine route and do not spend Opus or Sol unless evidence forces escalation. Use `codex` as a compatibility alias for `codex-terra`, and `codex-high` as a compatibility alias for `codex-sol`.
5. Treat model strength and reasoning effort as separate routing dimensions:
   - `claude-haiku`: Haiku, no effort parameter;
   - `claude-sonnet`: Sonnet, medium effort;
   - `claude-opus`: Opus, high effort;
   - `claude-best`: Fable when the account can use it, otherwise the latest Opus, high effort;
   - `codex-luna`: `gpt-5.6-luna`, low effort;
   - `codex-terra`: `gpt-5.6-terra`, medium effort;
   - `codex-sol`: `gpt-5.6-sol`, high effort.
   Do not raise effort merely because capacity remains. Raise the tier or effort only when task complexity or concrete failure evidence warrants it.
6. When routes are equally adequate, prefer corporate LiteLLM, Codex, or available Claude subscription capacity; then MiniMax; then direct DeepSeek; then OpenRouter.
7. Every task must declare `complexity` as `routine`, `strong`, or `frontier`. Its first worker route must match that capability, so routine models are not silently skipped and frontier work does not begin underpowered.
8. Every task must have an independent verifier route at least as capable as the corresponding worker route, a strong-to-frontier diagnosis ladder, and an independent strong-to-frontier test-intent ladder.
9. Put progressively stronger routes in each ladder and end every ladder at frontier capability. A confirmed failure never goes back to the same weak model.
10. Do not impose a planning cap on independent tasks or agents. Dependencies determine sequencing; independent tasks may run concurrently. The Claude runtime itself currently enforces its documented concurrency and total-agent safety limits.
11. Run cached, non-generating `health` checks only for routes present in the proposed plan. Remove routes whose client, credentials, endpoint, or network path is unavailable. Exact Claude/Codex account entitlement is finally confirmed by the attempted generation; if it is unavailable, record that result and continue along the approved ladder.
12. Treat the current worktree state as the pre-workflow baseline. Final checks may inspect `git status`, but must never require a globally clean worktree unless it was explicitly observed clean before planning. Check only approved scope and workflow-caused changes. Never ignore a test failure because it is pre-existing.
13. For an all-`review` plan, use read-only oracles (content comparison, hashes captured before and after, or a scoped diff against a known baseline). The final gate stays read-only and must never launch a repair worker.

Construct this exact plan shape:

```json
{
  "schema_version": 3,
  "workflow_id": "short-kebab-id",
  "objective": "complete objective",
  "working_directory": "/absolute/current/worktree",
  "planning": {
    "mode": "fast-path",
    "session_id": null,
    "discovery_performed": false,
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
      "id": "bounded-task-id",
      "objective": "bounded objective",
      "expected_artifact": "observable result",
      "dependencies": [],
      "non_goals": ["explicit exclusion"],
      "allowed_paths": ["relative/path", "tests"],
      "permission": "build",
      "complexity": "routine",
      "acceptance_checks": ["exact deterministic command or review oracle"],
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
    "acceptance_checks": ["project-specific final verification"],
    "test_plan": {
      "regression": [{"command": "complete mandatory suite", "rerun_command": "same isolated suite"}]
    }
  }
}
```

Use `review` permission only for tasks that must not edit. Never include `.env`, credential, secret, or unrelated paths.

## Present and launch

1. Call `prepare_plan`. Fix every validation error before continuing.
2. Show its complete summary as a compact table: task, dependencies, worker ladder, verifier ladder, checks, premium/API budget. State how many model agents the successful path uses at minimum and that failures add visible escalation agents.
3. Do not ask for a separate textual confirmation. Call `compile_workflow` with the returned `plan_id`, then immediately call Claude's native `Workflow` tool with the returned `scriptPath`.
4. The native Workflow approval card is the user's one execution confirmation when manual approval is active. Claude auto mode may accept it through its classifier; the user must switch out of auto mode before launch when a mandatory manual click is desired.
5. After launch, tell the user to inspect progress through `/workflows` or the Desktop Background Tasks pane. Do not duplicate workflow polling in the main conversation.

## Completion and recovery

- Accept only a final `VERIFIED` result.
- If a weak worker fails, let the compiled workflow escalate it; do not stop the task.
- A failing final verifier escalates through the complete verifier ladder before any repair. A read-only workflow never repairs. A build repair is limited to the union of the original build-task paths.
- After a task passes, the next task starts from its own planned initial complexity.
- If the workflow returns `BLOCKED`, distinguish a real external blocker from model failure. For unresolved model work, prepare a new plan that begins at the stronger evidence-supported tier. For new premium scope, show a new plan and use another native approval card.
- Never hide retries in the main conversation or call MCP `delegate` directly from the main thread. Every generation belongs to a visible workflow agent.
