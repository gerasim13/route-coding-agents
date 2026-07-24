# Bounded Planning and Role-Based Model Routing

Date: 2026-07-24

## Understanding summary

- AI Router must stop spending hours repeatedly refining one planning slice.
- Complex work must first prove that its macro architecture is viable before any detailed execution planning begins.
- Detailed planning covers only the next one or two executable tasks; later work remains contract-level milestones.
- Routine supporting work must be performed by visible routed agents instead of the main Claude session.
- MiniMax, corporate LiteLLM, direct DeepSeek, OpenRouter, the Codex model tiers, and the Claude model tiers must all be selected when their capability fits the role.
- Every observed failure remains active work. A failed weak route escalates rather than terminating the task.
- The existing Claude visible-workflow interface, current session worktree, compact recovery, and usage accounting remain the primary user experience.

## Constraints and assumptions

- Initial planning has a 30-minute wall-clock deadline.
- Macro architecture permits an initial draft and at most one correction.
- Near-wave planning permits at most one tactical correction.
- Provider unavailability and malformed responses cause bounded same-phase failover, not replanning.
- The dependency graph controls concurrency; there is no artificial global two-agent limit.
- Source code may be sent to user-configured models. Secrets, credentials, `.env` files, and unrelated repository content may not be sent.
- OpenRouter is approved for ordinary budgeted routes and is no longer backup-only. Premium specialist routes such as Kimi K3 retain their explicit budget gate.
- Provider model catalogs are dynamic inputs, but role pools remain curated and testable.
- Corporate LiteLLM is available only while the required VPN path is active.

## Architecture

Planning becomes a bounded state machine:

1. **Deterministic inspection and routed discovery**
   - Local commands collect repository facts, tests, and logs without a model.
   - Visible MiniMax, DeepSeek, OpenRouter, LiteLLM, Codex Luna, or Claude Haiku agents perform bounded semantic discovery.

2. **Macro architecture**
   - A dedicated architecture schema records boundaries, state owners, data flow, lifecycles, public and persistence contracts, concurrency, dependency direction, migration, rollback, feasibility evidence, fatal risks, and high-level milestones.
   - It contains no detailed future task commands, signatures, or file-by-file implementation.

3. **Independent macro grill**
   - Grillers receive the goal, repository evidence, and architecture envelope only.
   - They do not receive the tactical RoutePlan.
   - Frontier work uses independent providers. `claude-best` selects Fable when available; Codex Sol and a suitable external model provide adversarial independence.

4. **Near-wave planning**
   - Only the next one or two evidence-ready tasks become executable RoutePlan tasks.
   - Later work remains milestone contracts with entry and exit conditions.

5. **Tactical criticism**
   - One bounded correction may repair commands, paths, checks, ordering, or task scope.
   - Tactical findings cannot silently reopen settled architecture.

6. **Execution and calibration**
   - Each dependency wave is executed and verified.
   - Calibration may reopen macro architecture only when new execution evidence proves an ownership, lifecycle, dependency, public-contract, persistence, migration, or feasibility contradiction.

## Planning limits and typed outcomes

The planning workflow allows:

- one parallel discovery wave;
- one initial macro architecture draft;
- one macro architecture correction;
- two independent macro grillers per frontier round;
- one near-wave plan;
- one tactical correction;
- one final independent critic;
- a 30-minute total deadline.

Before every generation, the remaining deadline constrains the node timeout. A route may fail over to at most two adequate providers in the same phase. Failover does not consume a semantic correction round.

Findings are typed:

- `ARCHITECTURE_FATAL`: the architecture cannot satisfy a required contract;
- `ARCHITECTURE_REPAIRABLE`: the one permitted macro correction can resolve it;
- `TACTICAL`: the next executable wave needs a bounded correction;
- `COMPILER`: the workflow schema or compiler cannot represent the required execution;
- `EXTERNAL`: provider, network, authorization, user decision, or scope blocker.

Only architecture findings return to macro architecture. A compiler finding fails fast as `BLOCKED_COMPILER`; it never invokes another planner.

## Role-based routing

Model and reasoning effort are independent routing dimensions. Selection is deterministic from role, required capability, health, provider independence, budget, and recent fair-share usage.

| Role | Preferred pool | Escalation |
|---|---|---|
| Test and log collection | Deterministic runner | None |
| Log compression and failure classification | MiniMax M2.7 Highspeed, DeepSeek V4 Flash, OpenRouter DeepSeek V4 Flash | Codex Luna, corporate strong route |
| Repository discovery and dependency mapping | Corporate Qwen3 Coder Next, MiniMax M3, OpenRouter DeepSeek V4 Flash | Codex Terra |
| Routine implementation | MiniMax M2.7/M3, DeepSeek Flash, Codex Luna | Codex Terra, Claude Sonnet |
| Strong implementation and diagnosis | Corporate LiteLLM, MiniMax M3, DeepSeek V4 Pro, Codex Terra | Codex Sol, Claude Opus |
| Independent verification | An adequate provider different from the worker | Codex Sol, Claude Opus |
| Macro architecture | Claude Best/Fable or Codex Sol | Independent frontier arbitration |
| Frontier recovery | Claude Best/Fable, Codex Sol, Claude Opus | A materially different frontier approach |

The live corporate LiteLLM catalog observed through VPN includes, among others:

- `cloudru/MiniMax-M3`
- `cloudru/Qwen3-Coder-Next`
- `cloudru/DeepSeek-V4-Pro`
- `deepseek/deepseek-v4-flash`
- `deepseek/deepseek-v4-pro`
- `cloudru/GLM-5.1`
- `cloudru/Qwen3.6-35B-A3B`
- `cloudru/Kimi-K2.6`
- `cloudru/gpt-oss-120b`
- `gpt-5.4-nano`, `gpt-5.4-mini`, and `gpt-5.4`

OpenRouter becomes a normal independent route. Its active pool uses DeepSeek
V4 Flash for discovery, log analysis, and routine verification, plus DeepSeek
V4 Pro as a strong/frontier alternative. Kimi K3 remains a premium specialist.
Qwen3 Coder Next was removed after a live generation returned `No allowed
providers are available for the selected model` under the account's
upstream-provider policy; both OpenRouter DeepSeek routes passed live
generation checks.

The selector chooses the least recently used adequate healthy provider among equal candidates. It does not fan out models merely to satisfy a quota.

## Enforced visible delegation

The controller performs state transitions, user-decision handling, and frontier arbitration only. It may not silently absorb routed roles.

The compiler creates explicit visible nodes for:

- `repository-discovery`
- `dependency-mapper`
- `test-inventory`
- `log-summarizer`
- `failure-triage`
- `root-cause-diagnostician`
- `worker` or `repair`
- `diff-verifier`
- `test-intent-verifier`
- `architecture-drafter`
- `architecture-griller`
- `architecture-arbiter`
- `calibrator`

For a failing test, the deterministic runner stores the full log and returns a compact machine packet containing status, failure signature, log path, and bounded excerpts. A visible cheap `log-summarizer` creates the semantic evidence packet. A visible strong diagnostician then finds the cause. The main session does not replace either node.

If a cheap result is unavailable or malformed, a separate visible agent uses the next adequate provider. A compiler invariant rejects an execution graph that handles a non-green test without the required summarizer and diagnostician nodes.

## Health, catalogs, and usage

- Exact route health is non-generating and cached for 120 seconds.
- Provider model catalogs are refreshed at a low frequency, initially every six hours.
- A missing curated model is removed from candidate selection until the next catalog refresh.
- VPN-dependent LiteLLM failure causes immediate same-role failover.
- TLS mismatch, redirect, DNS, authentication, and exact-model failures receive distinct doctor diagnostics.
- Usage is grouped by workflow, provider, model, role, success, tokens, and known API cost.
- Workflow summaries expose requested route, resolved provider/model, and any failover.

## Check execution and failure recovery

The planning compiler no longer hardcodes a 300-second check timeout. Check specifications carry an explicit timeout inferred from repository inspection or use a 3600-second default. The supported maximum remains 14,400 seconds.

The execution loop is:

1. deterministic check suite;
2. visible cheap log summarizer for non-green evidence;
3. visible strong root-cause diagnosis;
4. bounded repair at the diagnosed tier;
5. deterministic rerun;
6. independent verification;
7. escalation to a stronger worker when required;
8. macro recalibration only when concrete evidence invalidates architecture.

A weak model failure never terminates otherwise-progressable work.

## Compatibility and rollout

Generated workflow scripts embed a plugin version. On resume after compact, the controller compares the checkpoint version with the installed version.

- Compatible execution checkpoints continue normally.
- Planning checkpoints generated by the unbounded planner are recompiled from the saved goal, decisions, inspection, discovery, and architecture evidence in the same Claude session.
- Confirmed user decisions are preserved.
- No new worktree or chat session is required.

Rollout updates the repository plugin version, personal marketplace entry, Claude global installation, generated configuration, and documentation without replacing real keys.

## Verification strategy

Local unit and mock tests must prove:

- planning cannot exceed its deadline or round budgets;
- macro grillers never receive tactical RoutePlan details;
- compiler errors fail fast;
- a non-green check necessarily creates visible summarizer and diagnostician nodes;
- route selection uses MiniMax, LiteLLM, DeepSeek, OpenRouter, Codex, and Claude for eligible roles;
- Fable is reachable through `claude-best` for frontier architecture or recovery;
- verifier provider independence is maintained when an adequate alternative exists;
- provider failure triggers same-phase failover;
- old planning checkpoints recompile without a new session.

Minimal real smoke checks validate exact-model availability and short bounded generations for MiniMax, direct DeepSeek, OpenRouter, and corporate LiteLLM. They must use strict output and dollar limits.

## Decision log

1. **Keep the Claude visible-workflow harness.**
   - Rejected: replacing it immediately with a standalone scheduler.
   - Reason: preserve the current interface and reduce migration risk.

2. **Split macro architecture from tactical planning.**
   - Rejected: merely capping the existing mixed grill loop.
   - Reason: detailed findings must not hide fatal macro contradictions.

3. **Use a 30-minute planning deadline.**
   - Alternatives: 45 minutes or round-only limits.
   - Reason: bound subscription and API burn even when calls time out.

4. **Permit one macro correction and one tactical correction.**
   - Rejected: convergence by repeated blocker fingerprints.
   - Reason: textual variation is not a reliable convergence signal.

5. **Plan only the next one or two executable tasks.**
   - Rejected: detailed full-horizon task plans.
   - Reason: execution evidence invalidates distant detail.

6. **Make OpenRouter a normal independent route.**
   - Rejected: backup-only selection.
   - Reason: use existing balance and improve provider independence.

7. **Enforce routed supporting roles in the compiled graph.**
   - Rejected: prompt-only encouragement.
   - Reason: the main model currently absorbs log analysis and discovery despite configured routes.

8. **Let the dependency graph control parallelism.**
   - Rejected: a fixed two-worker global cap.
   - Reason: safe independent work should run concurrently.

9. **Treat provider failure as failover, not replanning.**
   - Rejected: converting timeout or malformed output into an architectural challenge.
   - Reason: transport failures carry no architectural evidence.
