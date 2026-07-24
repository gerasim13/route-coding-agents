export const meta = /*__AI_ROUTER_PLANNING_META__*/ null

const SPEC = /*__AI_ROUTER_PLANNING_SPEC__*/ null
const DELEGATE_TOOL = 'mcp__plugin_ai-router_ai-router__delegate'
const TIER_LEVEL = { routine: 1, strong: 2, frontier: 3 }
const STARTED_AT = Date.now()
const DEADLINE_MS = (SPEC.planning_limits?.deadline_seconds || 1800) * 1000
const MAX_MACRO_ROUNDS = SPEC.planning_limits?.macro_rounds || 2
const MAX_TACTICAL_CORRECTIONS = SPEC.planning_limits?.tactical_corrections || 1
const MAX_PROVIDER_ATTEMPTS = (SPEC.planning_limits?.provider_failovers_per_node || 2) + 1

const ROUTE_FIELDS = {
  route_status: {
    type: 'string',
    enum: ['OK', 'UNAVAILABLE', 'TIMED_OUT', 'MALFORMED'],
  },
  route_error: { type: ['string', 'null'] },
}

const DISCOVERY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'summary', 'evidence', 'uncertainties', 'material_questions',
    'route_status', 'route_error',
  ],
  properties: {
    summary: { type: 'string' },
    evidence: { type: 'array', items: { type: 'string' } },
    uncertainties: { type: 'array', items: { type: 'string' } },
    material_questions: { type: 'array', items: { type: 'string' } },
    ...ROUTE_FIELDS,
  },
}

const ARCHITECTURE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'status', 'risk_level', 'architecture_envelope', 'material_questions',
    'assumptions', 'blocker', 'route_status', 'route_error',
  ],
  properties: {
    status: {
      type: 'string',
      enum: ['DRAFT_READY', 'AWAITING_USER_DECISION', 'BLOCKED'],
    },
    risk_level: { type: 'string', enum: ['routine', 'strong', 'frontier'] },
    architecture_envelope: { type: 'object' },
    material_questions: { type: 'array', items: { type: 'string' } },
    assumptions: { type: 'array', items: { type: 'string' } },
    blocker: { type: ['string', 'null'] },
    ...ROUTE_FIELDS,
  },
}

const TASK_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'id', 'objective', 'expected_artifact', 'dependencies', 'non_goals',
    'allowed_paths', 'permission', 'complexity', 'acceptance_checks',
    'targeted_commands', 'affected_commands',
  ],
  properties: {
    id: { type: 'string' },
    objective: { type: 'string' },
    expected_artifact: { type: 'string' },
    dependencies: { type: 'array', items: { type: 'string' } },
    non_goals: { type: 'array', items: { type: 'string' } },
    allowed_paths: { type: 'array', items: { type: 'string' } },
    permission: { type: 'string', enum: ['review', 'build'] },
    complexity: { type: 'string', enum: ['routine', 'strong', 'frontier'] },
    acceptance_checks: { type: 'array', items: { type: 'string' } },
    targeted_commands: { type: 'array', items: { type: 'string' } },
    affected_commands: { type: 'array', items: { type: 'string' } },
  },
}

const TACTICAL_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'status', 'risk_level', 'execution_objective', 'tasks', 'future_milestones',
    'final_acceptance_checks', 'regression_commands', 'material_questions',
    'assumptions', 'blocker', 'route_status', 'route_error',
  ],
  properties: {
    status: {
      type: 'string',
      enum: ['DRAFT_READY', 'AWAITING_USER_DECISION', 'BLOCKED'],
    },
    risk_level: { type: 'string', enum: ['routine', 'strong', 'frontier'] },
    execution_objective: { type: 'string' },
    tasks: { type: 'array', minItems: 1, maxItems: 2, items: TASK_SCHEMA },
    future_milestones: { type: 'array', items: { type: 'string' } },
    final_acceptance_checks: { type: 'array', items: { type: 'string' } },
    regression_commands: { type: 'array', items: { type: 'string' } },
    material_questions: { type: 'array', items: { type: 'string' } },
    assumptions: { type: 'array', items: { type: 'string' } },
    blocker: { type: ['string', 'null'] },
    ...ROUTE_FIELDS,
  },
}

const MACRO_GRILL_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'verdict', 'finding_type', 'blocking_findings', 'counterexamples',
    'invalid_assumptions', 'material_questions', 'recommended_changes',
    'route_status', 'route_error',
  ],
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'CHALLENGE'] },
    finding_type: {
      type: 'string',
      enum: [
        'NONE', 'ARCHITECTURE_FATAL', 'ARCHITECTURE_REPAIRABLE', 'EXTERNAL',
      ],
    },
    blocking_findings: { type: 'array', items: { type: 'string' } },
    counterexamples: { type: 'array', items: { type: 'string' } },
    invalid_assumptions: { type: 'array', items: { type: 'string' } },
    material_questions: { type: 'array', items: { type: 'string' } },
    recommended_changes: { type: 'array', items: { type: 'string' } },
    ...ROUTE_FIELDS,
  },
}

const CRITIC_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'verdict', 'finding_type', 'findings', 'material_questions', 'summary',
    'route_status', 'route_error',
  ],
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'CHALLENGE'] },
    finding_type: {
      type: 'string',
      enum: ['NONE', 'TACTICAL', 'COMPILER', 'EXTERNAL'],
    },
    findings: { type: 'array', items: { type: 'string' } },
    material_questions: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    ...ROUTE_FIELDS,
  },
}

const ROUTE_CAPABILITY = {
  cheap: 1,
  minimax: 1,
  'minimax-fast': 1,
  'corporate-flash': 1,
  'openrouter-cheap': 1,
  'openrouter-cheap': 1,
  'codex-luna': 1,
  'claude-haiku': 1,
  'corporate-pro': 2,
  'corporate-qwen': 2,
  'corporate-minimax': 2,
  'corporate-glm': 2,
  'minimax-m3': 2,
  'deepseek-pro': 2,
  'openrouter-deepseek': 2,
  'codex-terra': 2,
  codex: 2,
  'claude-sonnet': 2,
  'codex-sol': 3,
  'codex-high': 3,
  'claude-opus': 3,
  'claude-best': 3,
  'openrouter-deepseek-frontier': 3,
  'kimi-k3': 3,
}

const ROUTING_LADDERS = {
  routine: {
    routes: [
      'minimax-fast', 'openrouter-cheap', 'cheap',
      'corporate-qwen', 'codex-terra', 'claude-best',
    ],
    verifier_routes: [
      'openrouter-cheap', 'cheap', 'corporate-qwen',
      'codex-terra', 'claude-sonnet', 'codex-sol',
    ],
    test_intent_verifier_routes: [
      'openrouter-cheap', 'cheap', 'corporate-qwen',
      'codex-terra', 'claude-sonnet', 'codex-sol',
    ],
  },
  strong: {
    routes: [
      'corporate-minimax', 'minimax-m3', 'deepseek-pro',
      'codex-terra', 'claude-best',
    ],
    verifier_routes: [
      'deepseek-pro', 'openrouter-deepseek', 'corporate-qwen',
      'claude-sonnet', 'codex-sol',
    ],
    test_intent_verifier_routes: [
      'deepseek-pro', 'openrouter-deepseek', 'corporate-qwen',
      'claude-sonnet', 'codex-sol',
    ],
  },
  frontier: {
    routes: ['claude-best', 'codex-sol', 'openrouter-deepseek-frontier'],
    verifier_routes: ['codex-sol', 'claude-best', 'claude-opus'],
    test_intent_verifier_routes: ['codex-sol', 'claude-best', 'claude-opus'],
  },
}

const DIAGNOSIS_ROUTES = [
  'corporate-qwen', 'minimax-m3', 'deepseek-pro',
  'codex-sol', 'claude-best',
]

function isNative(route) {
  return route === 'claude-haiku' || route === 'claude-sonnet' ||
    route === 'claude-opus' || route === 'claude-best'
}

function nativeModel(route) {
  if (route === 'claude-haiku') return 'haiku'
  if (route === 'claude-opus') return 'opus'
  if (route === 'claude-best') return 'best'
  return 'sonnet'
}

function nativeEffort(route) {
  if (route === 'claude-opus' || route === 'claude-best') return 'high'
  if (route === 'claude-sonnet') return 'medium'
  return null
}

function withNativeEffort(route, options) {
  const effort = nativeEffort(route)
  return effort ? { ...options, effort } : options
}

function providerGroup(route) {
  if (route.startsWith('codex')) return 'openai-subscription'
  if (route.startsWith('claude')) return 'anthropic-subscription'
  if (route.startsWith('corporate')) return 'corporate-litellm'
  if (route.startsWith('minimax')) return 'minimax'
  if (route === 'cheap' || route === 'deepseek-pro') return 'deepseek'
  return 'openrouter'
}

function planningExpired() {
  return Date.now() - STARTED_AT >= DEADLINE_MS
}

function remainingSeconds(defaultSeconds = 900) {
  const remaining = Math.max(30, Math.floor((DEADLINE_MS - (Date.now() - STARTED_AT)) / 1000))
  return Math.min(defaultSeconds, remaining)
}

function deadlineBlocker(phaseName) {
  return {
    status: 'BLOCKED',
    route_plan: null,
    material_questions: [],
    blocker: `PLANNING_DEADLINE_EXCEEDED:${phaseName}:30-minute planning budget exhausted`,
  }
}

function delegationArgs(route, role, taskId, prompt) {
  const value = {
    workflow_id: `planning-${SPEC.session_id.slice(0, 8)}`,
    task_id: taskId,
    role,
    route,
    profile: 'review',
    working_directory: SPEC.working_directory,
    prompt,
    timeout_seconds: remainingSeconds(),
  }
  if (SPEC.planning_budget_usd != null) value.budget_usd = SPEC.planning_budget_usd
  return value
}

async function runExternal(route, role, taskId, prompt, label, phaseName, schema) {
  const args = delegationArgs(route, role, taskId, prompt)
  const wrapperPrompt = [
    'You are a transparent one-generation AI Router planning wrapper.',
    `Call ${DELEGATE_TOOL} EXACTLY ONCE with the JSON arguments below.`,
    'Do not inspect the repository, solve the task, retry, or call another model yourself.',
    'Map a valid delegated JSON object faithfully into the requested schema.',
    'Set route_status=OK and route_error=null only for a valid completed delegated result.',
    'For unavailable, timed-out, or malformed delegated output, preserve the failure using route_status=UNAVAILABLE, TIMED_OUT, or MALFORMED and put the exact compact cause in route_error.',
    '',
    JSON.stringify(args),
  ].join('\n')
  return agent(wrapperPrompt, {
    label,
    phase: phaseName,
    schema,
    model: 'haiku',
    agentType: 'ai-router:external-worker',
    maxTurns: 4,
  })
}

async function runNative(route, prompt, label, phaseName, schema, agentType = 'ai-router:planning-readonly') {
  return agent(
    [
      prompt,
      '',
      `Work read-only in ${SPEC.working_directory}.`,
      'Never edit files, create worktrees, change Git state, or run implementation.',
      'Return exactly the requested structured object with route_status=OK and route_error=null.',
    ].join('\n'),
    withNativeEffort(route, {
      label,
      phase: phaseName,
      schema,
      model: nativeModel(route),
      agentType,
      maxTurns: 16,
    }),
  )
}

async function runRouted(route, role, taskId, prompt, label, phaseName, schema) {
  return isNative(route)
    ? runNative(route, prompt, label, phaseName, schema)
    : runExternal(route, role, taskId, prompt, label, phaseName, schema)
}

async function runRoutedPool(routes, role, taskId, prompt, label, phaseName, schema) {
  let last = null
  const uniqueRoutes = [...new Set(routes)].slice(0, MAX_PROVIDER_ATTEMPTS)
  for (let index = 0; index < uniqueRoutes.length; index += 1) {
    if (planningExpired()) return { route: uniqueRoutes[index], result: null, deadline: true }
    const route = uniqueRoutes[index]
    const result = await runRouted(
      route,
      role,
      taskId,
      prompt,
      `${label}:${route}:f${index + 1}`,
      phaseName,
      schema,
    )
    last = { route, result, deadline: false }
    if (result?.route_status === 'OK') return last
  }
  return last || { route: uniqueRoutes[0], result: null, deadline: false }
}

function seedValue(value) {
  return [...value].reduce((total, character) => (total + character.charCodeAt(0)) % 65536, 0)
}

function recentCalls(route) {
  return Number(SPEC.route_usage?.[route] || 0)
}

function fairOrder(items, seed, routeForItem = (item) => item) {
  return [...items].sort((left, right) => {
    const leftRoute = routeForItem(left)
    const rightRoute = routeForItem(right)
    const usageDifference = recentCalls(leftRoute) - recentCalls(rightRoute)
    if (usageDifference) return usageDifference
    return seedValue(`${seed}:${leftRoute}`) - seedValue(`${seed}:${rightRoute}`)
  })
}

function rotateLadderPairs(ladders, seed) {
  const rows = ladders.routes.map((route, index) => ({
    route,
    verifier: ladders.verifier_routes[index],
    intent: ladders.test_intent_verifier_routes[index],
    capability: ROUTE_CAPABILITY[route],
  }))
  const result = []
  for (const capability of [1, 2, 3]) {
    const group = rows.filter((row) => row.capability === capability)
    result.push(...fairOrder(
      group,
      seed + capability,
      (row) => row.route,
    ))
  }
  return {
    routes: result.map((row) => row.route),
    verifier_routes: result.map((row) => row.verifier),
    test_intent_verifier_routes: result.map((row) => row.intent),
  }
}

function rotateCapabilityGroups(routes, seed) {
  const result = []
  for (const capability of [1, 2, 3]) {
    result.push(...fairOrder(
      routes.filter((route) => ROUTE_CAPABILITY[route] === capability),
      seed + capability,
    ))
  }
  return result
}

function architecturePool(tier) {
  const primary = SPEC.routes.planners[tier]
  if (tier === 'routine') {
    return [primary, 'corporate-flash', 'codex-luna']
  }
  if (tier === 'strong') {
    return [primary, 'minimax-m3', 'deepseek-pro', 'claude-sonnet']
  }
  return [primary, 'codex-sol', 'openrouter-deepseek-frontier', 'claude-opus']
}

function tacticalPool(tier) {
  const primary = SPEC.routes.tactical_planners[tier]
  if (tier === 'routine') {
    return [primary, 'minimax-fast', 'cheap', 'codex-luna']
  }
  if (tier === 'strong') {
    return [primary, 'minimax-m3', 'deepseek-pro', 'codex-terra', 'claude-sonnet']
  }
  return [primary, 'openrouter-deepseek-frontier', 'claude-opus']
}

function criticPool(tier, plannerRoute) {
  const configured = SPEC.routes.critics[tier]
  const candidates = tier === 'routine'
    ? [configured, 'openrouter-cheap', 'codex-luna', 'claude-haiku']
    : tier === 'strong'
      ? [configured, 'deepseek-pro', 'corporate-qwen', 'codex-terra', 'claude-sonnet']
      : [configured, 'claude-opus', 'codex-sol']
  const independent = candidates.filter(
    (route) => providerGroup(route) !== providerGroup(plannerRoute),
  )
  return independent.length ? independent : candidates
}

function materialQuestions(results) {
  return [...new Set(results.flatMap((result) => result?.material_questions || []))]
}

async function runDiscovery() {
  if (!SPEC.discovery_tasks.length) return []
  const calls = SPEC.discovery_tasks.map((task) => async () => {
    const prompt = [
      'Perform one bounded read-only repository discovery task.',
      `Goal: ${SPEC.objective}`,
      `Discovery objective: ${task.objective}`,
      `Local inspection: ${JSON.stringify(SPEC.inspection)}`,
      'Return only evidence that changes architecture, scope, tests, routing, or risk.',
      'Do not write an implementation plan. Ask only a material product, contract, architecture, security, cost, or scope question unavailable from the repository.',
    ].join('\n\n')
    const routed = await runRoutedPool(
      task.routes,
      'discovery',
      task.id,
      prompt,
      `discover:${task.id}`,
      'Discover',
      DISCOVERY_SCHEMA,
    )
    return { route: routed.route, ...routed.result }
  })
  return calls.length === 1 ? [await calls[0]()] : parallel(calls)
}

async function runArchitecture(discovery, correctionEvidence, round, tier) {
  const prompt = [
    `Act as the ${tier}-tier macro architecture drafter.`,
    `Original goal: ${SPEC.objective}`,
    `Working directory: ${SPEC.working_directory}`,
    `Local inspection: ${JSON.stringify(SPEC.inspection)}`,
    `Discovery evidence: ${JSON.stringify(discovery)}`,
    `Persisted user/context evidence: ${JSON.stringify(SPEC.context)}`,
    correctionEvidence.length
      ? `One bounded architecture correction is requested from: ${JSON.stringify(correctionEvidence)}`
      : '',
    'Produce only a macro architecture envelope. Settle system boundaries, state owners, data flow, lifecycles, public and persistence contracts, concurrency, dependency direction, feasibility, migration, rollback, fatal risks, and contract-level milestones.',
    'Do not plan files, signatures, commands, fixtures, or detailed future tasks.',
    'Prove that the architecture is implementable before optimizing a narrow component.',
    'Do not ask for repository facts. Ask only a genuinely material user decision.',
  ].filter(Boolean).join('\n\n')
  return runRoutedPool(
    architecturePool(tier),
    'architecture-drafter',
    `architecture-r${round}`,
    prompt,
    `architecture:r${round}`,
    'Architecture',
    ARCHITECTURE_SCHEMA,
  )
}

function grillAssignments(riskLevel) {
  if (riskLevel === 'routine') return []
  if (riskLevel === 'strong') {
    return [{
      routes: [
        SPEC.routes.strong_griller,
        'minimax-m3',
        'openrouter-deepseek',
        'claude-sonnet',
      ],
      role: 'macro-contract-feasibility-breaker',
    }]
  }
  return [
    {
      routes: [
        SPEC.routes.frontier_grillers[0],
        'claude-opus',
        'openrouter-deepseek-frontier',
      ],
      role: 'ownership-lifecycle-dependency-breaker',
    },
    {
      routes: [
        SPEC.routes.frontier_grillers[1],
        'codex-sol',
        'claude-opus',
      ],
      role: 'contract-migration-feasibility-breaker',
    },
  ]
}

async function runMacroGrill(architecture, riskLevel, round) {
  const assignments = grillAssignments(riskLevel)
  if (!assignments.length) return []
  const calls = assignments.map((assignment, index) => async () => {
    const prompt = [
      `Act as the ${assignment.role} in a macro architecture grill.`,
      `Original goal: ${SPEC.objective}`,
      `Repository evidence: ${JSON.stringify({ inspection: SPEC.inspection, context: SPEC.context })}`,
      `Architecture envelope: ${JSON.stringify(architecture.architecture_envelope)}`,
      'You intentionally do not receive a tactical RoutePlan.',
      'Try to prove fatal contradictions in ownership, state lifecycle, data flow, dependency direction, public or persistence contracts, concurrency, migration, rollback, or implementability.',
      'Do not discuss commands, timeouts, fixtures, file-level scope, implementation signatures, or distant task details.',
      'Use ARCHITECTURE_FATAL only when no bounded correction can satisfy the approved goal.',
      'Use ARCHITECTURE_REPAIRABLE for a precise envelope correction. Use EXTERNAL only for a real unavailable decision or dependency.',
      'PASS only when no macro blocker remains.',
    ].join('\n\n')
    const routed = await runRoutedPool(
      assignment.routes,
      'architecture-griller',
      `macro-grill-${round}-${index + 1}`,
      prompt,
      `macro-grill:${assignment.role}:r${round}`,
      'Architecture grill',
      MACRO_GRILL_SCHEMA,
    )
    return { route: routed.route, role: assignment.role, ...routed.result }
  })
  return calls.length === 1 ? [await calls[0]()] : parallel(calls)
}

function macroBlockers(results) {
  return results.flatMap((result) => {
    if (
      !result ||
      result.route_status !== 'OK' ||
      result.verdict !== 'PASS' ||
      result.material_questions?.length
    ) {
      return [
        ...(result?.blocking_findings || []),
        ...(result?.invalid_assumptions || []),
        ...(result?.material_questions || []),
        ...(result?.route_error ? [result.route_error] : []),
      ]
    }
    return []
  })
}

function highestMacroFinding(results) {
  if (results.some((result) => result?.finding_type === 'ARCHITECTURE_FATAL')) {
    return 'ARCHITECTURE_FATAL'
  }
  if (results.some((result) => result?.finding_type === 'ARCHITECTURE_REPAIRABLE')) {
    return 'ARCHITECTURE_REPAIRABLE'
  }
  if (results.some((result) => result?.finding_type === 'EXTERNAL' || result?.route_status !== 'OK')) {
    return 'EXTERNAL'
  }
  return 'NONE'
}

async function runTacticalPlanner(architecture, discovery, correctionEvidence, correction, tier) {
  const prompt = [
    `Act as the ${tier}-tier near-wave execution planner.`,
    `Original goal: ${SPEC.objective}`,
    `Locked architecture envelope: ${JSON.stringify(architecture.architecture_envelope)}`,
    `Discovery evidence: ${JSON.stringify(discovery)}`,
    correctionEvidence.length
      ? `Apply the single permitted tactical correction: ${JSON.stringify(correctionEvidence)}`
      : '',
    'Return exactly one or two evidence-ready tasks for the immediate dependency wave.',
    'Put all later work in future_milestones as contract-level statements only.',
    'Do not reopen macro architecture without new repository evidence.',
    'Return execution_objective as the narrow current objective consistent with the locked architecture and original user goal.',
    'For each immediate task return id, objective, expected_artifact, dependencies, non_goals, relative allowed_paths, permission, complexity, acceptance_checks, targeted_commands, and affected_commands.',
    'Every command is one non-destructive post-implementation check. Never place implementation commands in check arrays.',
    'Return the complete mandatory regression_commands for the final zero-tolerance gate.',
    'Every observed failure remains active work, including timeout, flaky, infrastructure, stale, and pre-existing failures.',
    `This is tactical draft ${correction + 1}; there is no planning permission beyond one correction.`,
  ].filter(Boolean).join('\n\n')
  return runRoutedPool(
    tacticalPool(tier),
    'planner',
    `tactical-plan-c${correction}`,
    prompt,
    `tactical-plan:c${correction}`,
    'Near-wave plan',
    TACTICAL_SCHEMA,
  )
}

function semanticDraftFindings(draft) {
  const findings = []
  const nonEmptyStrings = (value) =>
    Array.isArray(value) && value.length > 0 &&
    value.every((item) => typeof item === 'string' && item.trim())
  if (!Array.isArray(draft.tasks) || !draft.tasks.length || draft.tasks.length > 2) {
    findings.push('near-wave plan must contain one or two tasks')
    return findings
  }
  const ids = new Set()
  for (const task of draft.tasks) {
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(task.id || '')) {
      findings.push(`task id is unsafe or malformed: ${JSON.stringify(task.id)}`)
    } else if (ids.has(task.id)) {
      findings.push(`task id is duplicated: ${task.id}`)
    } else {
      ids.add(task.id)
    }
    for (const field of ['allowed_paths', 'acceptance_checks', 'targeted_commands']) {
      if (!nonEmptyStrings(task[field])) {
        findings.push(`task ${task.id || '<unknown>'}.${field} must contain non-empty strings`)
      }
    }
    if (!Array.isArray(task.affected_commands)) {
      findings.push(`task ${task.id || '<unknown>'}.affected_commands must be an array`)
    }
    for (const path of task.allowed_paths || []) {
      const normalized = path.replaceAll('\\', '/')
      if (
        normalized.startsWith('/') || normalized === '..' ||
        normalized.startsWith('../') || normalized.includes('/../')
      ) {
        findings.push(`task ${task.id || '<unknown>'} path escapes the worktree: ${path}`)
      }
      if (/(^|\/)(?:\.env(?:\.|$)|[^/]*(?:credential|secret)[^/]*)(?:\/|$)/i.test(normalized)) {
        findings.push(`task ${task.id || '<unknown>'} includes a protected path: ${path}`)
      }
    }
  }
  for (const task of draft.tasks) {
    for (const dependency of task.dependencies || []) {
      if (dependency === task.id) findings.push(`task ${task.id} depends on itself`)
      else if (!ids.has(dependency)) findings.push(`task ${task.id} depends on unknown task ${dependency}`)
    }
  }
  if (!nonEmptyStrings(draft.final_acceptance_checks)) {
    findings.push('final_acceptance_checks must contain non-empty strings')
  }
  if (!nonEmptyStrings(draft.regression_commands)) {
    findings.push('regression_commands must contain non-empty executable commands')
  }
  return findings
}

function checkTimeout(command) {
  if (/^(?:true|false|pwd|rg\b|git\s+(?:diff|status)\b|node\s+--check\b)/.test(command.trim())) {
    return 600
  }
  return 3600
}

function checkSpecs(commands) {
  return commands.map((command) => ({
    command,
    timeout_seconds: checkTimeout(command),
  }))
}

function effectiveRisk(draft, architectureRisk) {
  return draft.tasks.reduce(
    (highest, task) => TIER_LEVEL[task.complexity] > TIER_LEVEL[highest]
      ? task.complexity
      : highest,
    architectureRisk,
  )
}

function buildRoutePlan(
  draft,
  architecture,
  riskLevel,
  architecturePlannerRoute,
  criticRoute,
  grillResults,
  macroRounds,
) {
  const assignments = grillAssignments(riskLevel)
  const required = riskLevel !== 'routine'
  const finalLadders = rotateLadderPairs(
    ROUTING_LADDERS[riskLevel],
    seedValue(`${SPEC.session_id}:final`),
  )
  return {
    schema_version: 4,
    workflow_id: `workflow-${SPEC.session_id.slice(0, 12)}`,
    objective: draft.execution_objective,
    working_directory: SPEC.working_directory,
    planning: {
      mode: 'adaptive',
      workflow_protocol_version: SPEC.workflow_protocol_version,
      session_id: SPEC.session_id,
      discovery_performed: SPEC.discovery_tasks.length > 0,
      planner_route: architecturePlannerRoute,
      critic_route: criticRoute,
      critic_verdict: 'PASS',
      assumptions: [...architecture.assumptions, ...draft.assumptions],
      architecture_envelope: architecture.architecture_envelope,
      original_objective: SPEC.objective,
      future_milestones: draft.future_milestones,
      limits: SPEC.planning_limits,
      route_usage: SPEC.route_usage || {},
      grill: {
        level: riskLevel,
        required,
        signals: required
          ? [`${riskLevel} macro architecture risk requires independent feasibility proof`]
          : [],
        routes: required ? grillResults.map((result) => result.route) : [],
        roles: required ? grillResults.map((result) => result.role) : [],
        rounds: required ? macroRounds : 0,
        open_blockers: [],
        verdict: required ? 'PASS' : 'SKIPPED',
      },
    },
    approval: {
      premium_routes: [],
      max_api_budget_usd: null,
      allow_openrouter_primary: true,
    },
    tasks: draft.tasks.map((task) => {
      const seed = seedValue(`${SPEC.session_id}:${task.id}`)
      const ladders = rotateLadderPairs(ROUTING_LADDERS[task.complexity], seed)
      return {
        id: task.id,
        objective: task.objective,
        expected_artifact: task.expected_artifact,
        dependencies: task.dependencies,
        non_goals: task.non_goals,
        allowed_paths: task.allowed_paths,
        permission: task.permission,
        complexity: task.complexity,
        acceptance_checks: task.acceptance_checks,
        routes: ladders.routes,
        verifier_routes: ladders.verifier_routes,
        diagnosis_routes: rotateCapabilityGroups(DIAGNOSIS_ROUTES, seed),
        test_intent_verifier_routes: ladders.test_intent_verifier_routes,
        test_plan: {
          targeted: checkSpecs(task.targeted_commands),
          affected: checkSpecs(
            task.affected_commands.length
              ? task.affected_commands
              : task.targeted_commands,
          ),
        },
      }
    }),
    final_gate: {
      routes: finalLadders.routes,
      verifier_routes: finalLadders.verifier_routes,
      diagnosis_routes: rotateCapabilityGroups(
        DIAGNOSIS_ROUTES,
        seedValue(`${SPEC.session_id}:final-diagnosis`),
      ),
      acceptance_checks: draft.final_acceptance_checks,
      test_plan: {
        regression: checkSpecs(draft.regression_commands),
      },
    },
  }
}

async function runCritic(draft, architecture, routePlan, tier, architecturePlannerRoute, correction) {
  const prompt = [
    `Act as the independent ${tier}-tier tactical critic.`,
    `Original goal: ${SPEC.objective}`,
    `Locked architecture envelope: ${JSON.stringify(architecture.architecture_envelope)}`,
    `Near-wave RoutePlan: ${JSON.stringify(routePlan)}`,
    'Check only immediate task executability, scope, dependency order, route independence, checks, and consistency with the locked architecture.',
    'Do not re-litigate macro architecture without new repository evidence.',
    'Do not demand detailed distant tasks. Future milestones are intentionally contract-level.',
    'Use COMPILER when the RoutePlan schema or generated policy cannot represent required execution. A COMPILER finding must fail fast and must never trigger another model round.',
    'Use TACTICAL for one bounded correction. Use EXTERNAL only for a real unavailable user choice or dependency.',
    `This is critic pass ${correction + 1}; at most one tactical correction is permitted.`,
    'PASS only when the immediate wave is executable.',
  ].join('\n\n')
  return runRoutedPool(
    criticPool(tier, architecturePlannerRoute),
    'plan-critic',
    `tactical-critic-c${correction}`,
    prompt,
    `tactical-critic:c${correction}`,
    'Critique',
    CRITIC_SCHEMA,
  )
}

phase('Discover')
const discovery = await runDiscovery()
if (planningExpired()) return deadlineBlocker('discovery')
const discoveryFailures = discovery.filter((result) => result?.route_status !== 'OK')
if (discoveryFailures.length) {
  return {
    status: 'BLOCKED',
    route_plan: null,
    material_questions: [],
    blocker: `PROVIDER_BLOCKED:discovery:${JSON.stringify(discoveryFailures)}`,
    discovery,
  }
}
const discoveryQuestions = materialQuestions(discovery)
if (discoveryQuestions.length) {
  return {
    status: 'AWAITING_USER_DECISION',
    route_plan: null,
    material_questions: discoveryQuestions,
    blocker: null,
    discovery,
  }
}

let architectureTier = SPEC.initial_planning_tier
let architecture = null
let architecturePlannerRoute = null
let macroRounds = 0
let macroGrill = []
const architectureCorrections = []

while (macroRounds < MAX_MACRO_ROUNDS) {
  if (planningExpired()) return deadlineBlocker('macro-architecture')
  macroRounds += 1
  phase('Architecture')
  const routedArchitecture = await runArchitecture(
    discovery,
    architectureCorrections,
    macroRounds,
    architectureTier,
  )
  architecturePlannerRoute = routedArchitecture.route
  architecture = routedArchitecture.result
  if (routedArchitecture.deadline || planningExpired()) {
    return deadlineBlocker('macro-architecture')
  }
  if (!architecture || architecture.route_status !== 'OK') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `PROVIDER_BLOCKED:architecture:${architecture?.route_error || 'no valid result'}`,
      discovery,
    }
  }
  if (architecture.status === 'BLOCKED') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: architecture.blocker || 'architecture drafter returned BLOCKED',
      discovery,
    }
  }
  if (architecture.status === 'AWAITING_USER_DECISION' || architecture.material_questions.length) {
    return {
      status: 'AWAITING_USER_DECISION',
      route_plan: null,
      material_questions: architecture.material_questions,
      blocker: null,
      discovery,
    }
  }
  if (TIER_LEVEL[architecture.risk_level] > TIER_LEVEL[architectureTier]) {
    architectureCorrections.push({
      type: 'risk-escalation',
      from: architectureTier,
      to: architecture.risk_level,
      reason: 'macro drafter found higher contract or feasibility risk',
    })
    architectureTier = architecture.risk_level
    if (macroRounds >= MAX_MACRO_ROUNDS) {
      return {
        status: 'BLOCKED',
        route_plan: null,
        material_questions: [],
        blocker: 'ARCHITECTURE_LIMIT:higher risk was discovered after the final permitted macro draft',
        discovery,
      }
    }
    continue
  }
  architectureTier = TIER_LEVEL[architecture.risk_level] > TIER_LEVEL[architectureTier]
    ? architecture.risk_level
    : architectureTier

  phase('Architecture grill')
  macroGrill = await runMacroGrill(architecture, architectureTier, macroRounds)
  if (planningExpired()) return deadlineBlocker('macro-grill')
  const questions = materialQuestions(macroGrill)
  if (questions.length) {
    return {
      status: 'AWAITING_USER_DECISION',
      route_plan: null,
      material_questions: questions,
      blocker: null,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
      macro_grill: macroGrill,
    }
  }
  const blockers = macroBlockers(macroGrill)
  if (!blockers.length) break
  const findingType = highestMacroFinding(macroGrill)
  if (findingType === 'ARCHITECTURE_FATAL') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `ARCHITECTURE_FATAL:${blockers.join(' | ')}`,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
      macro_grill: macroGrill,
    }
  }
  if (findingType === 'EXTERNAL') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `PROVIDER_BLOCKED:macro-grill:${blockers.join(' | ')}`,
      discovery,
      macro_grill: macroGrill,
    }
  }
  if (macroRounds >= MAX_MACRO_ROUNDS) {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `ARCHITECTURE_LIMIT:one correction exhausted:${blockers.join(' | ')}`,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
      macro_grill: macroGrill,
    }
  }
  architectureCorrections.push({
    type: 'ARCHITECTURE_REPAIRABLE',
    findings: blockers,
    reports: macroGrill,
  })
}

if (!architecture) {
  return {
    status: 'BLOCKED',
    route_plan: null,
    material_questions: [],
    blocker: 'ARCHITECTURE_LIMIT:no architecture draft completed',
    discovery,
  }
}

let tacticalCorrection = 0
let tacticalEvidence = []
while (tacticalCorrection <= MAX_TACTICAL_CORRECTIONS) {
  if (planningExpired()) return deadlineBlocker('near-wave-plan')
  phase('Near-wave plan')
  const routedDraft = await runTacticalPlanner(
    architecture,
    discovery,
    tacticalEvidence,
    tacticalCorrection,
    architectureTier,
  )
  const draft = routedDraft.result
  if (routedDraft.deadline || planningExpired()) return deadlineBlocker('near-wave-plan')
  if (!draft || draft.route_status !== 'OK') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `PROVIDER_BLOCKED:tactical-plan:${draft?.route_error || 'no valid result'}`,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
    }
  }
  if (draft.status === 'BLOCKED') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: draft.blocker || 'near-wave planner returned BLOCKED',
      discovery,
      architecture_envelope: architecture.architecture_envelope,
    }
  }
  if (draft.status === 'AWAITING_USER_DECISION' || draft.material_questions.length) {
    return {
      status: 'AWAITING_USER_DECISION',
      route_plan: null,
      material_questions: draft.material_questions,
      blocker: null,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
    }
  }
  const findings = semanticDraftFindings(draft)
  if (findings.length) {
    if (tacticalCorrection >= MAX_TACTICAL_CORRECTIONS) {
      return {
        status: 'BLOCKED',
        route_plan: null,
        material_questions: [],
        blocker: `BLOCKED_COMPILER:${findings.join(' | ')}`,
        discovery,
        architecture_envelope: architecture.architecture_envelope,
      }
    }
    tacticalEvidence = [{ finding_type: 'TACTICAL', findings }]
    tacticalCorrection += 1
    continue
  }
  const riskLevel = effectiveRisk(draft, architectureTier)
  if (TIER_LEVEL[riskLevel] > TIER_LEVEL[architectureTier]) {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `ARCHITECTURE_REOPEN_REQUIRED:near-wave task risk ${riskLevel} exceeds locked ${architectureTier} architecture`,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
    }
  }
  const provisionalCriticRoute = criticPool(
    riskLevel,
    architecturePlannerRoute,
  )[0]
  const routePlan = buildRoutePlan(
    draft,
    architecture,
    riskLevel,
    architecturePlannerRoute,
    provisionalCriticRoute,
    macroGrill,
    macroRounds,
  )
  phase('Critique')
  const routedCritic = await runCritic(
    draft,
    architecture,
    routePlan,
    riskLevel,
    architecturePlannerRoute,
    tacticalCorrection,
  )
  const critic = routedCritic.result
  if (routedCritic.deadline || planningExpired()) return deadlineBlocker('tactical-critic')
  if (!critic || critic.route_status !== 'OK') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `PROVIDER_BLOCKED:tactical-critic:${critic?.route_error || 'no valid result'}`,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
    }
  }
  if (critic.verdict === 'PASS' && !critic.material_questions.length) {
    routePlan.planning.critic_route = routedCritic.route
    return {
      status: 'PLAN_READY',
      route_plan: routePlan,
      material_questions: [],
      blocker: null,
      architecture_envelope: architecture.architecture_envelope,
      discovery,
      macro_grill: macroGrill,
      critic,
      macro_rounds: macroRounds,
      tactical_corrections: tacticalCorrection,
      elapsed_ms: Date.now() - STARTED_AT,
    }
  }
  if (critic.material_questions.length) {
    return {
      status: 'AWAITING_USER_DECISION',
      route_plan: null,
      material_questions: critic.material_questions,
      blocker: null,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
    }
  }
  if (critic.finding_type === 'COMPILER') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `BLOCKED_COMPILER:${critic.findings.join(' | ') || critic.summary}`,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
    }
  }
  if (critic.finding_type === 'EXTERNAL') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `EXTERNAL:${critic.findings.join(' | ') || critic.summary}`,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
    }
  }
  if (tacticalCorrection >= MAX_TACTICAL_CORRECTIONS) {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: `TACTICAL_LIMIT:one correction exhausted:${critic.findings.join(' | ') || critic.summary}`,
      discovery,
      architecture_envelope: architecture.architecture_envelope,
    }
  }
  tacticalEvidence = [{
    finding_type: 'TACTICAL',
    findings: critic.findings,
    summary: critic.summary,
  }]
  tacticalCorrection += 1
}

return {
  status: 'BLOCKED',
  route_plan: null,
  material_questions: [],
  blocker: 'TACTICAL_LIMIT:planning exited without an executable near-wave plan',
  discovery,
  architecture_envelope: architecture.architecture_envelope,
}
