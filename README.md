# route-coding-agents

A conservative agent skill for routing software-development work by cost, risk, scope, and verification quality.

It keeps one interactive supervisor and delegates bounded work through official channels. Default priority is Codex/corporate LiteLLM, then MiniMax, then direct DeepSeek, with OpenRouter reserved as backup:

- ChatGPT/Codex subscription via the official Codex CLI/MCP server;
- corporate LiteLLM;
- MiniMax and DeepSeek APIs;
- OpenRouter backup with a cheap DeepSeek tier and confirmation-gated Kimi K3.

Antigravity is deliberately excluded from automatic routing because Google prohibits third-party agents from using an Antigravity subscription session.

## Install

```bash
DISABLE_TELEMETRY=1 npx skills add gerasim13/route-coding-agents \
  --skill route-coding-agents --global \
  --agent claude-code codex opencode warp --yes
```

The skill contains no credentials. Local provider configuration remains under `~/.config/ai-coding-router/` and must not be committed.

Run the local preflight after installation:

```bash
scripts/router-doctor --network
```

Every `router-run` call also performs a no-generation availability check for the selected provider and exact model. Successful checks are shared in a 120-second local cache, keeping the normal path fast while preventing prompts from being sent when a VPN is disconnected or a configured model has disappeared.

See `SKILL.md` for the workflow and `references/routing-policy.md` for the routing matrix.

## Security properties

- no cookie or OAuth-session reuse;
- no account rotation;
- no recursive delegation;
- read-only review profile;
- isolated-worktree confirmation for mutations;
- no worker commit/push/merge/reset;
- explicit confirmation and local cap for Kimi K3;
- secrets stay outside the repository.

## License

MIT
