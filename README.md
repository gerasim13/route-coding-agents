# route-coding-agents / AI Router

AI Router turns multi-model coding delegation into a visible Claude Code Dynamic Workflow:

- one adaptive entry point that compiles a visible planning graph from a rough task;
- risk-gated adversarial grill for strong/frontier plans, skipped for routine work;
- two independent frontier planning agents before execution;
- one digest-bound route plan and one native execution approval card;
- one inspectable workflow agent for every model call;
- a workflow-only controller hook that blocks silent serial fallback;
- compact/resume recovery from durable MCP state;
- batched deterministic test-suite nodes with per-command evidence, plus independent verification after every worker;
- strong root-cause diagnosis before repair;
- escalation from routine to strong and frontier models;
- reset to the appropriate initial tier for each new task;
- zero tolerance for pre-existing, flaky, timed-out, or otherwise failing tests;
- routed token and known API-cost accounting.

Supported routes are native Claude workers, the official Codex subscription client, corporate LiteLLM, MiniMax, direct DeepSeek, and OpenRouter backup. The planner selects both model tier and reasoning effort: Claude Haiku/Sonnet/Opus and Codex Luna/Terra/Sol map to routine/strong/frontier work, with low/medium/high effort where the client supports it. At the hardest Claude step, the `best` alias selects Fable when the account has access and otherwise Opus. Every escalation ladder ends at a frontier model. Kimi K3 remains confirmation- and budget-gated. Antigravity is deliberately excluded.

## Install the Claude plugin

From Claude Code:

```text
/plugin marketplace add gerasim13/route-coding-agents
/plugin install ai-router@ai-router-marketplace
```

Or from a terminal:

```bash
claude plugin marketplace add gerasim13/route-coding-agents
claude plugin install ai-router@ai-router-marketplace --scope user
```

Start a new Claude session, then run:

```text
/ai-router:doctor fresh
/ai-router:start-workflow <rough software goal>
```

`/ai-router:start-workflow` first performs a free local inspection and
zero-token risk classification, then compiles one registered Planning Workflow
containing only the needed discovery, an adaptive Haiku/Sonnet/Opus planner,
risk-gated grillers, and an independent tier-appropriate critic. A planner that
finds higher risk visibly escalates to the next tier. Routine plans skip grill.
MCP verifies the returned RoutePlan digest
before compiling the registered Execution Workflow. Use
`/ai-router:workflow <precise software task>` as the expert fast path.

Use `/workflows` before and after approval to inspect planning, workers,
deterministic checks, calibrators, diagnosticians, verifiers, repairs, prompts,
results, time, and Claude tokens. While a router session is active, plugin
hooks reject direct main-session `Bash`/edits/model delegation, inline workflow
scripts, and script digest changes. Compact and resume restore the exact
controller action from durable state.
Use `/ai-router:usage` for routed external usage and known API cost.

Claude's auto mode may accept the Workflow card through its classifier. Switch out of auto mode before launch when you want a mandatory manual click.

## Install the portable skill

Codex, OpenCode, Warp, and other Agent Skills clients can use the same routing policy without claiming Claude's native workflow UI:

```bash
DISABLE_TELEMETRY=1 npx skills add gerasim13/route-coding-agents \
  --skill route-coding-agents --global \
  --agent claude-code codex opencode warp --yes
```

Provider keys and private endpoints remain under `~/.config/ai-coding-router/` and are never committed. After first installation, add the read-only OpenCode verifier profile and keep a timestamped backup:

```bash
plugins/ai-router/bin/router-configure
plugins/ai-router/bin/router-doctor --network
```

## Development verification

```bash
python3 -m unittest discover -s plugins/ai-router/tests -v
claude plugin validate .
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

See [SKILL.md](SKILL.md) for the portable protocol and [the adaptive workflow design](docs/plans/2026-07-23-adaptive-start-workflow.md) for the full architecture and decision log.

## Security properties

- official subscription clients and documented provider APIs only;
- no cookie, OAuth-session, or account-rotation tricks;
- no hidden model retries;
- no worker Git-history mutation or publication;
- no automatic extra worktrees;
- secrets excluded from plans, prompts, and accounting logs;
- no successful result while any mandatory test is failing;
- explicit premium-route approval and budget cap.

## License

MIT
