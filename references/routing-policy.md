# Routing policy

## Decision matrix

Start with local tools whenever a deterministic operation can solve the task. A model is warranted when the task requires semantic judgment, code synthesis, diagnosis, or an independent review.

| Conditions | Route | Escalation trigger |
|---|---|---|
| Discovery, log compression, dependency/test inventory | Corporate DeepSeek V4 Flash, MiniMax high-speed, OpenRouter DeepSeek V4 Flash, direct DeepSeek V4 Flash, or Codex Luna | Evidence requires cross-file semantic reasoning |
| Cross-file review/debugging | Corporate MiniMax M3/Qwen/GLM, direct MiniMax M3/DeepSeek Pro, OpenRouter DeepSeek Pro, Codex Terra, or Claude Sonnet | Evidence that strong reasoning missed the cause |
| Provider-independent strong alternative | Choose a different provider from the worker | Disagreement that executable evidence cannot resolve |
| Failed bounded attempt with strong evidence | Codex Sol with high effort | Only after the failure packet is prepared |
| Routine/strong/frontier native Claude task | Haiku/no effort; Sonnet/medium; Opus/high; Best/high | Escalate only with task complexity or failure evidence; Best selects Fable when available and otherwise Opus |
| Large repository, multimodal evidence, long horizon | Kimi K3 | Explicit user approval and dollar cap required |
| High risk, unclear goal, no oracle | Frontier supervisor | Reduce ambiguity before delegation |

## Default gates

- A verified worker failure moves the task to a stronger route; it never ends the task merely because a cheap worker failed.
- Route by role and capability, then use recent per-route usage to spread equally suitable low-cost work. Corporate LiteLLM, MiniMax, OpenRouter, direct DeepSeek, Codex, and Claude all receive explicit graph roles.
- Model family and reasoning effort are independent routing dimensions. The explicit aliases are `codex-luna`/low, `codex-terra`/medium, and `codex-sol`/high; `codex` and `codex-high` remain compatibility aliases for Terra and Sol.
- Native Claude aliases are `claude-haiku` without an effort argument, `claude-sonnet` with medium effort, `claude-opus` with high effort, and `claude-best` with high effort. Reserve Best for the hardest frontier step; Claude Code resolves it to Fable when entitled and otherwise to Opus.
- Every task declares `routine`, `strong`, or `frontier`. Its first worker must match that capability; every worker and verifier ladder ends with a frontier fallback.
- OpenRouter is a normal metered route for bounded discovery, tactical planning, criticism, verification, and independent failover. It is not a silent hidden backup.
- Review worker: read-only; no network, edits, subagents, or arbitrary shell.
- Build worker: the current session worktree; bounded commands and approved paths; no Git history mutation or publication.
- Codex MCP registration remains a medium default for ad-hoc calls. Routed workflow calls pin their own model and effort explicitly.
- Kimi K3: confirmation required for every task. The local cap is a gate, not a provider-side hard limit; also configure a provider/dashboard limit.
- Maximum delegation depth: one.
- The router does not impose a fixed agent-count or concurrency cap. The approved dependency graph decides which tasks can run concurrently. All workers use the current session worktree; the planner must order overlapping work when simultaneous edits would invalidate the task graph.

## Escalation packet

Escalation should reduce context, not forward an entire polluted conversation. Include only:

1. Objective and acceptance criteria.
2. Relevant files or diff.
3. Exact failing command and error.
4. One-paragraph diagnosis attempted so far.
5. Explicit question for the stronger model.

The raw deterministic failure packet first goes to a visible routine
`log-summarizer` agent. That agent extracts the failing command, smallest
relevant excerpt, involved tests/files, and artifact paths without diagnosing
or editing. A strong diagnostician receives both the original bounded evidence
and the compact summary.

## Bounded planning

Planning proves macro feasibility before tactical detail:

1. Independent discovery gathers only missing repository facts.
2. A macro draft describes owners, boundaries, data/lifecycle flow, contracts,
   migration, rollback, and executable oracles without file-by-file steps.
3. An independent griller can return `ARCHITECTURE_FATAL`,
   `ARCHITECTURE_REPAIRABLE`, or `EXTERNAL`.
4. At most one repair draft is allowed.
5. Only after the architecture passes, the tactical planner details the next
   one or two tasks and records distant work as milestones.
6. The tactical critic gets at most one correction.

The complete planning graph has a 30-minute deadline. A compiler/schema error
fails immediately. Provider failures use at most two separately visible
failovers for that node. No condition can start an unbounded planning loop.

At the strongest approved tier, create a separate frontier replanner. It must produce a materially different approach fingerprint before another frontier worker runs. Continue while new evidence or distinct approaches exist. After the task passes verification, discard its escalation state and route the next task from its own complexity.

## Verification hierarchy

Use the strongest available oracle in this order:

1. Exact deterministic unit/integration test.
2. Static checks and type/lint/build validation.
3. Focused diff review against acceptance criteria.
4. Real runtime, device, browser, audio, or deployed-service observation.
5. Model agreement only when no stronger oracle exists.

Two models agreeing is not proof when executable evidence is available.
