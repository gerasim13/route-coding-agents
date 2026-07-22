# Routing policy

## Decision matrix

Start with local tools whenever a deterministic operation can solve the task. A model is warranted when the task requires semantic judgment, code synthesis, diagnosis, or an independent review.

| Conditions | Route | Escalation trigger |
|---|---|---|
| Cross-file review/debugging with subscription capacity | Codex medium, priority 1 | Evidence that medium reasoning missed the cause |
| Bounded implementation needing stronger reasoning | Corporate DeepSeek V4 Pro, priority 1 | Failing acceptance test with a concrete diff |
| Need an independent alternative | MiniMax M2.7, priority 2 | Disagreement that cannot be resolved by tests |
| Mechanical, narrow, strong tests | Direct DeepSeek V4 Flash, priority 3 | Two distinct failed attempts or unclear root cause |
| Higher-priority provider unavailable | OpenRouter DeepSeek V4 Flash, backup only | Provider failure or explicit user choice |
| Failed bounded attempt with strong evidence | Codex high | Only after the failure packet is prepared |
| Large repository, multimodal evidence, long horizon | Kimi K3 | Explicit user approval and dollar cap required |
| High risk, unclear goal, no oracle | Frontier supervisor | Reduce ambiguity before delegation |

## Default gates

- Routine API worker: one attempt, one correction, then stop.
- Codex medium and corporate LiteLLM share first priority; choose by task type or observable remaining quota, never by blind fan-out.
- OpenRouter is backup-only and must not be selected while an adequate higher-priority route is healthy.
- Review worker: read-only; no network, edits, subagents, or arbitrary shell.
- Build worker: isolated worktree; bounded commands; no Git history mutation or publication.
- Codex MCP: `medium` by default. Use `high` only with collected evidence.
- Kimi K3: confirmation required for every task. The local cap is a gate, not a provider-side hard limit; also configure a provider/dashboard limit.
- Maximum delegation depth: one.
- Maximum concurrent mutable workers per worktree: one.

## Escalation packet

Escalation should reduce context, not forward an entire polluted conversation. Include only:

1. Objective and acceptance criteria.
2. Relevant files or diff.
3. Exact failing command and error.
4. One-paragraph diagnosis attempted so far.
5. Explicit question for the stronger model.

## Verification hierarchy

Use the strongest available oracle in this order:

1. Exact deterministic unit/integration test.
2. Static checks and type/lint/build validation.
3. Focused diff review against acceptance criteria.
4. Real runtime, device, browser, audio, or deployed-service observation.
5. Model agreement only when no stronger oracle exists.

Two models agreeing is not proof when executable evidence is available.
