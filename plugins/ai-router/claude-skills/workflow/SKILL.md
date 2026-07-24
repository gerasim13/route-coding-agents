---
name: workflow
description: Execute a precise software task through one registered visible Planning Workflow and one registered visible Execution Workflow with routed models, verification, escalation, and compact-safe enforcement. Use only when the user explicitly invokes /ai-router:workflow.
argument-hint: "<precise software task>"
disable-model-invocation: true
---

# Run the precise workflow fast path

Treat `$ARGUMENTS` as a precise task in the current worktree. This is the expert
fast path for users who already supplied bounded scope and acceptance intent.
It skips speculative routed discovery, not registered planning or independent
criticism.

The main conversation is a controller. Never implement, invoke direct model
MCP tools, create an inline Workflow, create a worktree, or use direct
`Agent`, `Task`, `Bash`, `Edit`, or `Write`. Plugin hooks enforce this contract
for the active session.

## Start and inspect

Load:

- `start_session`, `session_status`, `checkpoint_session`;
- `inspect_workspace`, `route_catalog`, `health`;
- `compile_planning_workflow`, `prepare_plan`, `compile_workflow`;
- `usage`.

Call `start_session` immediately with the complete task and absolute current
working directory. Follow `recovery_directive` when resuming. Call
`inspect_workspace`. If `controller.needs_recompile` is true, replace the
stale registered graph in the same session; do not ask the user to start over.

## Launch the registered planning graph

Call `compile_planning_workflow` with:

- the session id, exact task, canonical worktree, and inspection result;
- `discovery_tasks=[]` unless the supplied task lacks a fact required to make
  its scope or oracle executable;
- omit `routes` so the compiler selects independent corporate LiteLLM,
  MiniMax, direct DeepSeek, OpenRouter, Codex, and Claude roles from the
  locally classified tier, escalating visibly when evidence requires it;
- use the default 1800-second planning deadline;
- no paid planning budget unless already approved.

Pass the complete `inspect_workspace` result directly as `inspection`; never
nest it under `exact`, `result`, `data`, or another wrapper.

Launch native `Workflow` with the exact returned `scriptPath`. Inline scripts
are forbidden. The graph first validates a macro architecture without tactical
task detail, then details only the next one or two tasks and independently
criticizes them. It is bounded to an initial macro draft plus one repair and
one tactical correction. The workflow deterministically injects
provider/model/effort and escalation ladders into strict RoutePlan v4.

If it returns `AWAITING_USER_DECISION`, ask only that material question and
compile another registered planning graph with the answer in `context`. If it
returns `PLAN_READY`, call `session_status`, then call `prepare_plan` with only
`session_id`; MCP loads the exact registered RoutePlan and rejects any digest
mismatch without retranscribing the plan through the conversation.

## Launch the registered execution graph

Show the prepared plan summary, checkpoint `READY_FOR_APPROVAL`, call
`compile_workflow`, checkpoint `EXECUTING`, and immediately call native
`Workflow` with the exact returned `scriptPath`. The Workflow approval card is
the normal execution confirmation.

The compiled graph owns all workers, checks, low-cost log summarizers,
diagnosticians, repairs, verifiers, escalation, calibration, and the final
complete regression gate. Every generation and provider failover is a visible
node. Never duplicate execution, log reading, discovery, or fallback in the
main conversation.

After notification or compact/resume, call `session_status`. Continue only
through registered workflow scripts until the state is `VERIFIED`,
`AWAITING_SCOPE_APPROVAL`, or a concrete `BLOCKED`.
