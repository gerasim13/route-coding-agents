# Routing policy

## Decision matrix

Start with local tools whenever a deterministic operation can solve the task. A model is warranted when the task requires semantic judgment, code synthesis, diagnosis, or an independent review.

| Conditions | Route | Escalation trigger |
|---|---|---|
| Routine review or mechanical work using the OpenAI subscription | Codex Luna with low effort | Concrete evidence that routine reasoning is insufficient |
| Cross-file review/debugging with subscription capacity | Codex Terra with medium effort, priority 1 | Evidence that medium reasoning missed the cause |
| Bounded implementation needing stronger reasoning | Corporate DeepSeek V4 Pro, priority 1 | Failing acceptance test with a concrete diff |
| Need an independent alternative | MiniMax M2.7, priority 2 | Disagreement that cannot be resolved by tests |
| Mechanical, narrow, strong tests | Direct DeepSeek V4 Flash, priority 3 | Two distinct failed attempts or unclear root cause |
| Higher-priority provider unavailable | OpenRouter DeepSeek V4 Flash, backup only | Provider failure or explicit user choice |
| Failed bounded attempt with strong evidence | Codex Sol with high effort | Only after the failure packet is prepared |
| Routine/strong/frontier native Claude task | Haiku/no effort; Sonnet/medium; Opus/high; Best/high | Escalate only with task complexity or failure evidence; Best selects Fable when available and otherwise Opus |
| Large repository, multimodal evidence, long horizon | Kimi K3 | Explicit user approval and dollar cap required |
| High risk, unclear goal, no oracle | Frontier supervisor | Reduce ambiguity before delegation |

## Default gates

- A verified worker failure moves the task to a stronger route; it never ends the task merely because a cheap worker failed.
- Codex Terra/medium and corporate LiteLLM share first priority for strong work; choose by task type or observable remaining quota, never by blind fan-out.
- Model family and reasoning effort are independent routing dimensions. The explicit aliases are `codex-luna`/low, `codex-terra`/medium, and `codex-sol`/high; `codex` and `codex-high` remain compatibility aliases for Terra and Sol.
- Native Claude aliases are `claude-haiku` without an effort argument, `claude-sonnet` with medium effort, `claude-opus` with high effort, and `claude-best` with high effort. Reserve Best for the hardest frontier step; Claude Code resolves it to Fable when entitled and otherwise to Opus.
- Every task declares `routine`, `strong`, or `frontier`. Its first worker must match that capability; every worker and verifier ladder ends with a frontier fallback.
- OpenRouter is backup-only and must not be selected while an adequate higher-priority route is healthy.
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

At the strongest approved tier, create a separate frontier replanner. It must produce a materially different approach fingerprint before another frontier worker runs. Continue while new evidence or distinct approaches exist. After the task passes verification, discard its escalation state and route the next task from its own complexity.

## Verification hierarchy

Use the strongest available oracle in this order:

1. Exact deterministic unit/integration test.
2. Static checks and type/lint/build validation.
3. Focused diff review against acceptance criteria.
4. Real runtime, device, browser, audio, or deployed-service observation.
5. Model agreement only when no stronger oracle exists.

Two models agreeing is not proof when executable evidence is available.
