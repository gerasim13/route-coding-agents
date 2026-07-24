---
name: start-workflow
description: Adaptively turn a rough software goal into one registered visible Planning Workflow and one registered visible Execution Workflow with routed agents, adversarial grill, verification, escalation, and compact-safe recovery. Use only when the user explicitly invokes /ai-router:start-workflow.
argument-hint: "<rough software goal>"
disable-model-invocation: true
---

# Start a workflow-only AI Router session

Treat `$ARGUMENTS` as the rough goal in the current worktree. Never create
another worktree. The main conversation is a controller, not a worker.

All model generations must run inside a registered native Workflow graph.
Never use direct `Agent`, `Task`, model MCP, `codex exec`, inline `Workflow`,
`Bash`, `Edit`, or `Write` calls from the controller. Plugin hooks enforce this
while the session is active. Workflow agents retain only the tools declared by
their compiled graph.

## Load and recover the controller

Load these `ai-router` MCP tools:

- `start_session`, `session_status`, `checkpoint_session`;
- `inspect_workspace`, `route_catalog`, `health`;
- `compile_planning_workflow`, `prepare_plan`, `compile_workflow`;
- `usage`.

Call `start_session` immediately with the complete rough goal and absolute
current working directory. Then call `session_status`.

When a session resumes after `/compact`, restart, or an interrupted turn, obey
`recovery_directive`. Do not reconstruct the protocol from conversation
memory. A normal continuation needs no additional command: the user may say
“continue,” and the controller resumes the registered next action. If
`controller.needs_recompile` is true, replace the old registered graph in the
same session exactly as directed. Never require a new user command or a new
conversation merely because the plugin protocol changed.

If an unfinished session has a materially different objective, ask whether to
resume it. If declined, checkpoint the old session `BLOCKED`, start the new
objective, and continue.

## Inspect without generation

Call `inspect_workspace` before compiling planning. It is the lightweight,
non-generating pass for:

- canonical worktree, branch, HEAD, fingerprint, and current changes;
- repository markers and language shape;
- candidate targeted, affected, and regression commands.

Do not read `.env`, credentials, secrets, production data, or unrelated files.
Any observed failure is active work. “Pre-existing” records provenance only.

## Compile one visible Planning Workflow

Create a compact planning request:

```json
{
  "session_id": "session id from start_session",
  "objective": "complete rough goal",
  "working_directory": "/absolute/canonical/worktree",
  "inspection": {
    "working_directory": "/absolute/canonical/worktree",
    "worktree": "/absolute/canonical/worktree",
    "git_common_directory": "/absolute/canonical/worktree/.git",
    "branch": "current branch",
    "head": "current HEAD",
    "workspace_fingerprint": "returned fingerprint",
    "changed_files": [],
    "changed_file_count": 0,
    "tracked_file_count": 0,
    "repository_markers": [],
    "extension_counts": [],
    "candidate_checks": [],
    "inspection_is_non_generating": true
  },
  "discovery_tasks": [
    {
      "id": "bounded-read-only-question",
      "objective": "one repository question local inspection could not answer"
    }
  ],
  "context": {},
  "planning_budget_usd": null,
  "planning_timeout_seconds": 1800
}
```

Pass the complete `inspect_workspace` result as `inspection` verbatim. Never
nest it under `exact`, `result`, `data`, or another wrapper.

Keep deterministic search out of discovery tasks. Use no discovery task when
paths, contracts, dependencies, tests, and risks are already clear. Otherwise
create as many independent bounded tasks as the actual unknowns require and
normally omit `routes`: the compiler spreads independent routine evidence work
across healthy corporate LiteLLM, MiniMax, OpenRouter, direct DeepSeek, and
Codex Luna routes using recent routed usage. Specify `routes` only when the
task needs a known capability or provider-independent failover.

The compiler creates one graph containing:

1. parallel bounded discovery;
2. a macro architecture draft with no file-level task choreography;
3. an independent architecture grill that cannot see tactical detail;
4. a near-wave plan for only the next one or two executable tasks;
5. an independent tactical critic.

The architecture stage proves system boundaries, owners, data flow,
lifecycles, invariants, contracts, migration feasibility, rollback, and test
oracles before tactical detail can begin. It emits only future milestones for
later waves. The planning graph has a hard 30-minute deadline, at most two
macro drafts (initial plus one repair), and at most one tactical correction.
An architecture-fatal finding stops before tactical planning. Compiler or
external blockers fail closed instead of provoking another planning loop.

A zero-token local preclassifier selects the starting risk tier. Routine work
uses low-cost external/native routes; strong work deliberately assigns macro
drafting, grill, tactical planning, and criticism to independent corporate
LiteLLM, MiniMax, direct DeepSeek, and OpenRouter roles; frontier work uses
Claude Best (Fable when available, otherwise Opus), Codex Sol, and an
independent OpenRouter frontier critic. Provider failure launches a separately
visible failover node, never a hidden retry. Recent role and route usage
breaks ties between equally suitable low-cost routes.

The planner returns only semantic architecture, bounded tasks, scope, checks,
and complexity. The workflow compiler—not the planning model—injects provider
aliases, Claude/Codex model tiers, effort, independent verifier ladders,
diagnosis routes, and frontier fallbacks into strict RoutePlan v4.

Call `compile_planning_workflow`, then immediately launch native `Workflow`
with its exact `scriptPath`. Never send an inline script. Tell the user the
graph is visible through `/workflows`; do not replace it with serial status
messages. Registration already moves the controller to `PLANNING`; never issue
a redundant `PLANNING` checkpoint.

## Handle the planning result

The Planning Workflow returns one of:

- `PLAN_READY`: use its exact `route_plan`;
- `AWAITING_USER_DECISION`: ask only the returned material question, place the
  answer in the next request `context`, and compile another registered Planning
  Workflow;
- `BLOCKED`: report the exact external/evidence blocker.

After the native workflow notification, call `session_status` before acting on
the result. This reconciles the exact registered run and automatically moves a
`PLAN_READY` session to `CRITIQUING`; never synthesize launch metadata or skip
that reconciliation.

Do not rewrite, quote, or retranscribe a returned RoutePlan in the main
conversation. Call `prepare_plan` with only `session_id`; MCP loads the exact
registered workflow result from its native run record and verifies its digest.

Present the prepared compact summary: architecture envelope, assumptions,
grill evidence, task dependencies, allowed paths, worker/verifier/diagnosis
ladders with model and effort, targeted/affected/regression checks, planning
usage, known API cost, premium routes, and budget.

## Compile and launch execution

Checkpoint `READY_FOR_APPROVAL`, call `compile_workflow`, then checkpoint
`EXECUTING`. Both transitions are rejected unless the registered planning
result, prepared plan, execution script path, and SHA-256 digest match.

Immediately launch native `Workflow` with the returned exact `scriptPath`.
The native Workflow approval card is the normal implementation confirmation;
do not ask for a duplicate textual confirmation.

The compiled graph owns:

- every implementation, diagnosis, repair, and verification generation;
- deterministic targeted and affected checks after work;
- one isolated rerun before strong diagnosis of a failure;
- one visible low-cost evidence agent that compresses failed test logs before
  every strong diagnosis;
- escalation to a stronger route instead of stopping after a weak failure;
- independent verification of every worker and existing-test change;
- calibration at dependency boundaries;
- the mandatory complete regression suite and final verifier ladder.

Never poll by starting another agent or execute fallback work in the main
conversation. `/workflows` is the live graph and drill-down UI.

## Finish, amend, or recover

Call `session_status` after the workflow notification or on the next user
prompt. It reconciles the registered native run:

- `VERIFIED`: only after every mandatory regression and final verifier passes;
- `AWAITING_SCOPE_APPROVAL`: show exact required new paths, then replan through
  another registered Planning Workflow after approval;
- `BLOCKED`: only for a real external blocker or exhausted independent
  frontier approaches;
- failed/cancelled workflow engine run: recompile or resume a registered graph;
  never fall back to direct sequential execution.

Compaction and resume hooks restore this state automatically. There is no
successful state with a known failure.
