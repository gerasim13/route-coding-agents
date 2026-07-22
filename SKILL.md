---
name: route-coding-agents
description: Route software-development tasks across official Codex subscription access, corporate LiteLLM, MiniMax, DeepSeek, and OpenRouter by cost, risk, scope, and verification needs. Use when the user asks to delegate coding work, reduce token burn, choose a cheaper model, orchestrate multiple coding agents, enforce per-task budgets, or recover from an agent that is going in the wrong direction.
---

# Route coding agents

Use one supervisor to classify work, delegate only bounded tasks, and verify every result. Optimize completed work per unit of subscription/API budget rather than minimizing the cost of an individual call.

## Non-negotiable rules

- Use only official subscription clients and documented provider APIs.
- Never extract or reuse browser cookies, OAuth tokens, or session credentials in another harness.
- Never rotate accounts to evade quotas or rate limits.
- Never invoke Antigravity from Claude Code, Codex, OpenCode, MCP, or this skill. Antigravity subscription work is a separate manual workflow.
- Never delegate recursively. Maximum delegation depth is one.
- Never send secrets, `.env` files, credentials, production data, or unrelated repository content to a worker.
- Never let a worker commit, push, merge, rebase, reset, or publish.
- Keep one mutable task in one isolated worktree. A review worker must remain read-only.
- Premium model use requires explicit user confirmation and a stated dollar cap.

## Preflight

Run `scripts/router-doctor` before the first delegation in a session or after configuration changes. Add `--network` when VPN or provider reachability may have changed; it performs `/models` checks but no model generation.

`scripts/router-run` also invokes `scripts/router-check` immediately before every real delegation. It verifies authentication, provider reachability, and the exact configured model without sending the task prompt. Successful checks are cached for 120 seconds across sessions, so the normal hot path is only a local file read. Use `scripts/router-check --fresh MODEL_ALIAS` after a VPN state change. If a check fails, no generation occurs and no model tokens are spent.

Expected local configuration:

- `~/.config/ai-coding-router/providers.private.json`, mode `600`.
- `~/.config/ai-coding-router/opencode.json`.
- `~/.config/ai-coding-router/keys/`, mode `700`, with individual key files mode `600`.
- Claude MCP server `codex` running the official `codex mcp-server`.

If preflight fails, report the unavailable route and select the next healthy priority tier. Do not silently fall back to a more expensive model, and never resubmit a task that already produced a generation without user/supervisor review.

## Classify the task

Evaluate four dimensions before selecting a route:

1. **Risk:** production data, auth, migrations, money, destructive operations, public APIs, or security-sensitive code.
2. **Ambiguity:** unclear goal, unknown failure cause, conflicting requirements, or missing acceptance criteria.
3. **Scope:** local/mechanical, bounded multi-file, repository-wide, or cross-system.
4. **Verification:** deterministic tests, review-only evidence, live runtime/device proof, or no reliable oracle.

Keep high-risk, ambiguous, or weakly verifiable work with the frontier supervisor until it has been reduced to a bounded task.

## Choose the cheapest adequate route

Use these priority tiers. Never fan out the same task across a whole tier unless the user explicitly requests independent reviews.

1. **Codex medium and corporate LiteLLM share first priority.** Choose Codex for diagnosis, review, and ambiguous cross-file reasoning; choose corporate DeepSeek V4 Pro for bounded implementation. If both fit equally, prefer the route with more observable remaining quota.
2. **MiniMax M2.7** is the second tier.
3. **Direct DeepSeek** is the third tier.
4. **OpenRouter is backup-only.** Use it when the earlier tiers are unavailable or when the user explicitly approves Kimi K3.

| Route | Best use | Default profile |
|---|---|---|
| No model | Search, formatting, deterministic scripts, existing tests | Local tools |
| Codex medium | Subscription-backed code review, debugging, or a second opinion | `codex` |
| Corporate DeepSeek V4 Pro | Strong bounded implementation/review using approved corporate LiteLLM | `corporate-pro` |
| MiniMax M2.7 | Independent implementation draft or alternative approach | `minimax` |
| Direct DeepSeek V4 Flash | Mechanical implementation, test repair, narrow refactors | `cheap` |
| OpenRouter DeepSeek V4 Flash | Backup when higher-priority routes are unavailable | `openrouter-cheap` |
| Codex high | Escalation after a concrete failed attempt with evidence | `codex-high` |
| Kimi K3 | Large-repository, multimodal, or long-horizon escalation | `kimi-k3` |

Do not select Kimi K3 merely because a task is large. First reduce the task, try a cheaper route, and collect the failed attempt plus test evidence.

## Bound the delegation

Every worker prompt must contain:

- objective and expected artifact;
- exact repository/worktree and allowed file scope;
- explicit non-goals;
- acceptance criteria and commands used to verify them;
- permission level: review or build;
- stopping conditions and time/budget limit;
- instruction to report uncertainty rather than expand scope.

Use this compact contract:

```text
Objective:
Scope:
Non-goals:
Acceptance checks:
Evidence already collected:
Stop when:
```

## Run a worker

Prefer `scripts/router-run` so model aliases, worktree confirmation, and premium gates are consistent.

Read-only review:

```bash
scripts/router-run --profile review --model corporate-pro --dir "$PWD" --prompt "..."
```

Mutable work in an isolated worktree:

```bash
scripts/router-run --profile build --model cheap --dir "/path/to/worktree" --worktree-confirmed --prompt "..."
```

Kimi K3 requires both confirmation flags:

```bash
scripts/router-run --profile review --model kimi-k3 --dir "$PWD" \
  --confirm-premium --budget-usd 1.00 --prompt "..."
```

When Claude exposes the official Codex MCP, prefer that MCP for `codex` routes. `router-run` uses the official Codex CLI as a fallback.

## Verify and escalate

After a worker returns:

1. Inspect the diff and confirm scope.
2. Run the smallest deterministic check, then the relevant suite.
3. Validate the real runtime surface when the task concerns a device, deployed service, UI, audio, or performance.
4. Reject unrelated edits and unsupported claims.
5. Escalate only with the prompt, diff, failing command, exact error, and what was already tried.

Stop a worker that repeats the same failure, expands scope, reads unrelated files, or spends tokens without producing new evidence. Start a fresh bounded session instead of carrying a polluted context forward.

See `references/routing-policy.md` for the detailed decision matrix and budget guidance.
