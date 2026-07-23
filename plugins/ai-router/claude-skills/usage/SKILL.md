---
name: usage
description: Show AI Router usage and known external API cost for the current workflow, last day, last week, or all routed history. Use only when the user invokes /ai-router:usage or explicitly asks for router spending.
argument-hint: "[day|week|all] [workflow-id]"
disable-model-invocation: true
---

# Show routed usage

Use ToolSearch to load the `ai-router` MCP `usage` tool. Parse `$ARGUMENTS`; default to `day`. Call the tool once and present:

- calls and success/failure by route;
- external input/output/reasoning/cache tokens;
- known API cost;
- which costs are unknown or subscription-backed.

State clearly that native Claude workflow tokens remain visible in `/workflows` and that neither Claude nor Codex exposes a reliable remaining subscription-quota API. Do not infer an exact remaining quota.
