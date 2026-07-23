---
name: doctor
description: Diagnose AI Router plugin, provider, VPN, Codex, and OpenCode readiness without sending generation requests to routed providers. Use when the user invokes /ai-router:doctor or a route is unexpectedly unavailable.
argument-hint: "[fresh]"
disable-model-invocation: true
---

# Diagnose the router

Use ToolSearch to load `ai-router` MCP `route_catalog` and `health`. List the configured aliases, then check all non-premium routes. Use `fresh=true` only when `$ARGUMENTS` contains `fresh`, VPN state changed, or a cached route just failed.

Also run `"${CLAUDE_PLUGIN_ROOT}/bin/router-doctor"` and report each failing prerequisite. These checks do not generate model output. Never print keys, proxy credentials, private configuration contents, or environment values.

State that invoking this slash command still uses the current Claude session even though the provider checks themselves do not generate routed model output. End successful reports with the exact next-step form `/ai-router:workflow <software task>`.
