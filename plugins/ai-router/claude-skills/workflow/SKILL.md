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
3. Choose routes by task complexity, not by always starting cheap:
   - routine: `minimax` or `cheap`;
   - strong: `corporate-pro`, `codex`, or `claude-sonnet`;
   - frontier: `codex-high` or `claude-opus`;
   - specialist: `kimi-k3` only after the user explicitly authorizes it and a dollar cap;
   - `openrouter-cheap` is backup-only unless the user explicitly approves it as primary.
   Deterministic documentation comparisons, bounded grep/config inspection, formatting, and mechanical edits with a strong oracle are routine. Start them on `minimax` or `cheap` with `codex` as verifier; do not spend Opus or high-effort Codex unless evidence forces escalation.
4. When routes are equally adequate, prefer corporate LiteLLM, Codex, or available Claude subscription capacity; then MiniMax; then direct DeepSeek; then OpenRouter.
5. Every task must have an independent verifier route at least as capable as the corresponding worker route.
6. Put progressively stronger routes in each task's `routes`. A confirmed failure never goes back to the same weak model.
7. Do not impose a planning cap on independent tasks or agents. Dependencies determine sequencing; independent tasks may run concurrently. The Claude runtime itself currently enforces its documented concurrency and total-agent safety limits.
8. Run cached `health` checks only for routes present in the proposed plan. Remove unavailable routes or keep them only as explicit pre-approved fallbacks.
9. Treat the current worktree state as the pre-workflow baseline. Final checks may inspect `git status`, but must never require a globally clean worktree unless it was explicitly observed clean before planning. Check only approved scope and workflow-caused changes.
10. For an all-`review` plan, use read-only oracles (content comparison, hashes captured before and after, or a scoped diff against a known baseline). The final gate stays read-only and must never launch a repair worker.

Construct this exact plan shape:

```json
{
  "schema_version": 1,
  "workflow_id": "short-kebab-id",
  "objective": "complete objective",
  "working_directory": "/absolute/current/worktree",
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
      "acceptance_checks": ["exact deterministic command or review oracle"],
      "routes": ["minimax", "corporate-pro", "codex-high"],
      "verifier_routes": ["codex", "claude-sonnet", "claude-opus"]
    }
  ],
  "final_gate": {
    "routes": ["corporate-pro", "codex-high", "claude-opus"],
    "verifier_routes": ["codex", "claude-opus", "codex-high"],
    "acceptance_checks": ["project-specific final verification"]
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
