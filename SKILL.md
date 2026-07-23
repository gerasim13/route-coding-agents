---
name: route-coding-agents
description: Route software-development tasks across Claude, official Codex subscription access, corporate LiteLLM, MiniMax, DeepSeek, and OpenRouter using a visible plan, independent verification after every model call, adaptive escalation, provider health checks, and routed usage accounting. Use when the user asks to delegate coding work, reduce token burn, orchestrate several coding agents, verify a cheaper model, control API spend, or recover from an agent that failed or went in the wrong direction.
---

# Route coding agents

Use one supervisor to plan a graph of bounded workers and independent verifiers. Optimize verified completed work per unit of subscription/API capacity.

## Prefer the Claude plugin

When running in Claude Code/Desktop with the `ai-router` plugin installed,
invoke `/ai-router:start-workflow <rough software goal>`. It performs adaptive discovery,
material clarification, and independent frontier planning before compiling one
native Dynamic Workflow where every model call, deterministic check,
diagnostician, verifier, repair, and replan is visible. Inspect it through
`/workflows`. Use `/ai-router:workflow <precise software task>` only as the
non-interactive expert fast path.

Outside Claude, reproduce the same task graph with the harness's native subagents/tasks. Do not claim Claude's workflow UI in Codex, OpenCode, or Warp.

## Keep these invariants

- Use official subscription clients and documented provider APIs only.
- Never reuse browser cookies, OAuth tokens, or subscription credentials in another harness.
- Never rotate accounts to evade quotas or rate limits.
- Never invoke Antigravity from this router.
- Never send secrets, `.env` files, credentials, production data, or unrelated repository content to workers.
- Use the current session worktree. Do not create extra worktrees.
- Treat its existing changes as the workflow baseline. Never require or manufacture a globally clean worktree; compare only the approved scope against known pre-workflow evidence.
- Do not let workers commit, push, merge, rebase, reset, clean, stash, or publish.
- Require explicit approval and a dollar cap for premium routes.
- Make every generation a separate visible agent/task. Never hide retries inside a script or MCP call.
- Treat every observed failure as active work. “Pre-existing” is provenance, not permission to ignore it.
- Require the complete mandatory regression suite to be green before success.

## Plan before routing

For each bounded task, show:

- objective, artifact, allowed paths, and non-goals;
- dependencies and whether it can run concurrently;
- initial worker route and progressively stronger escalation routes;
- an independent verifier route for every worker level;
- deterministic acceptance checks;
- targeted, affected, and complete regression commands;
- strong-to-frontier diagnosis and independent test-intent routes;
- approved fallbacks and API budget.

Choose the initial level by task complexity. Do not force every task through the cheapest model.

| Level | Routes | Use |
|---|---|---|
| Routine | Claude Haiku; Codex Luna/low; MiniMax; direct DeepSeek | Mechanical changes with strong tests |
| Strong | corporate LiteLLM; Codex Terra/medium; Claude Sonnet/medium | Normal implementation, debugging, multi-file work |
| Frontier | Codex Sol/high; Claude Opus/high; Claude Best/high | Ambiguity, architecture, repeated failure; Best resolves to Fable when available, otherwise Opus |
| Specialist | Kimi K3 | Explicitly approved long-context use |
| Backup | OpenRouter | Only when an adequate preferred route is unavailable |

When routes are equally adequate, prefer corporate LiteLLM, Codex, or available Claude subscription capacity; then MiniMax; then direct DeepSeek; then OpenRouter.

Treat model family and reasoning effort as separate choices. Use `claude-haiku`, `claude-sonnet`, and `claude-opus` for explicit native Claude tiers; use `claude-best` only at the hardest frontier step so Claude Code can select Fable when entitled and otherwise fall back to Opus. Use `codex-luna`, `codex-terra`, and `codex-sol` for explicit Codex tiers. The legacy aliases `codex` and `codex-high` remain compatible with Terra/medium and Sol/high respectively. Every task declares `routine`, `strong`, or `frontier`; its initial route must match that level, while both worker and verifier ladders must end at frontier capability.

## Verify and escalate

After every worker generation:

1. Inspect the current diff and allowed scope.
2. Run targeted and affected commands through the deterministic check runner.
3. On any failure, run one isolated rerun and send the compact redacted evidence to a strong read-only diagnostician.
4. Use an independent verifier at least as capable as the worker.
5. If an existing test changed, require a separate independent test-intent verifier.
6. Give failed work to the next evidence-appropriate stronger model. Never return a confirmed failure to the same weak model.
7. If the frontier worker fails, run a separate frontier replanner, then a new frontier worker with a materially different approach.
8. Continue while new evidence or approaches exist. Pause only for a real external blocker, a required user decision, unavailable providers, new scope, or premium authorization.
9. After verification passes, reset escalation for the next task and route it independently.

At the final gate, run the complete mandatory regression suite before the
verifier ladder. Flaky, timeout, crash, infrastructure, stale, and pre-existing
failures are all non-green. All-review plans remain read-only and return a
blocker instead of repairing. Build repairs may touch only paths already
approved for build tasks; otherwise request a scope amendment and a new
workflow card.

## Use the bundled runner outside native workflows

Run `scripts/router-doctor` once after configuration changes. Add `--network` after VPN changes. Normal route checks are non-generating and cached for 120 seconds.

Examples:

```bash
scripts/router-run --profile build --model minimax --dir "$PWD" --worktree-confirmed --prompt "..."
scripts/router-run --profile verify --model codex-terra --dir "$PWD" --prompt "..."
```

Use `--json` when structured usage must be collected. See `references/routing-policy.md` for the detailed matrix.
