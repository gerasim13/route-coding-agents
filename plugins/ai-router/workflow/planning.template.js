export const meta = /*__AI_ROUTER_PLANNING_META__*/ null

const SPEC = /*__AI_ROUTER_PLANNING_SPEC__*/ null
const DELEGATE_TOOL = 'mcp__plugin_ai-router_ai-router__delegate'
const TIER_LEVEL = { routine: 1, strong: 2, frontier: 3 }

const DISCOVERY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['summary', 'evidence', 'uncertainties', 'material_questions'],
  properties: {
    summary: { type: 'string' },
    evidence: { type: 'array', items: { type: 'string' } },
    uncertainties: { type: 'array', items: { type: 'string' } },
    material_questions: { type: 'array', items: { type: 'string' } },
  },
}

const NON_EMPTY_STRING = { type: 'string', minLength: 1 }
const STRING_LIST = { type: 'array', items: NON_EMPTY_STRING }
const NON_EMPTY_STRING_LIST = { type: 'array', minItems: 1, items: NON_EMPTY_STRING }

const PLANNER_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'status', 'risk_level', 'architecture_envelope', 'tasks',
    'final_acceptance_checks', 'regression_commands', 'material_questions',
    'assumptions', 'blocker',
  ],
  properties: {
    status: { type: 'string', enum: ['DRAFT_READY', 'AWAITING_USER_DECISION', 'BLOCKED'] },
    risk_level: { type: 'string', enum: ['routine', 'strong', 'frontier'] },
    architecture_envelope: { type: 'object' },
    tasks: {
      type: 'array',
      items: {
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
      },
    },
    final_acceptance_checks: { type: 'array', items: { type: 'string' } },
    regression_commands: { type: 'array', items: { type: 'string' } },
    material_questions: { type: 'array', items: { type: 'string' } },
    assumptions: { type: 'array', items: { type: 'string' } },
    blocker: { type: ['string', 'null'] },
  },
}

const ROUTING_LADDERS = {
  routine: {
    routes: ['minimax', 'corporate-pro', 'codex-sol'],
    verifier_routes: ['codex-luna', 'claude-sonnet', 'claude-opus'],
    test_intent_verifier_routes: ['codex-terra', 'claude-opus'],
  },
  strong: {
    routes: ['corporate-pro', 'codex-sol'],
    verifier_routes: ['claude-sonnet', 'claude-opus'],
    test_intent_verifier_routes: ['codex-terra', 'claude-opus'],
  },
  frontier: {
    routes: ['codex-sol'],
    verifier_routes: ['claude-opus'],
    test_intent_verifier_routes: ['claude-opus'],
  },
}
const DIAGNOSIS_ROUTES = ['corporate-pro', 'codex-sol']

const GRILL_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'verdict', 'blocking_findings', 'counterexamples', 'invalid_assumptions',
    'missing_tests', 'scope_rollback_concerns', 'material_questions',
    'recommended_changes',
  ],
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'CHALLENGE'] },
    blocking_findings: { type: 'array', items: { type: 'string' } },
    counterexamples: { type: 'array', items: { type: 'string' } },
    invalid_assumptions: { type: 'array', items: { type: 'string' } },
    missing_tests: { type: 'array', items: { type: 'string' } },
    scope_rollback_concerns: { type: 'array', items: { type: 'string' } },
    material_questions: { type: 'array', items: { type: 'string' } },
    recommended_changes: { type: 'array', items: { type: 'string' } },
  },
}

const CRITIC_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['verdict', 'findings', 'material_questions', 'summary'],
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'CHALLENGE'] },
    findings: { type: 'array', items: { type: 'string' } },
    material_questions: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
}

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

function delegationArgs(route, role, taskId, prompt) {
  const value = {
    workflow_id: `planning-${SPEC.session_id.slice(0, 8)}`,
    task_id: taskId,
    role,
    route,
    profile: 'review',
    working_directory: SPEC.working_directory,
    prompt,
    timeout_seconds: 900,
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
    'The delegated model was asked to return one JSON object. Map it faithfully into the requested schema.',
    'If the delegated result is unavailable or malformed, preserve that fact as a BLOCKED or CHALLENGE result allowed by the schema.',
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

async function runNative(route, prompt, label, phaseName, schema) {
  return agent(
    [
      prompt,
      '',
      `Work read-only in ${SPEC.working_directory}.`,
      'Never edit files, create worktrees, change Git state, or run the implementation.',
      'Return exactly the requested structured object.',
    ].join('\n'),
    withNativeEffort(route, {
      label,
      phase: phaseName,
      schema,
      model: nativeModel(route),
      agentType: 'ai-router:planning-readonly',
    }),
  )
}

async function runRouted(route, role, taskId, prompt, label, phaseName, schema) {
  return isNative(route)
    ? runNative(route, prompt, label, phaseName, schema)
    : runExternal(route, role, taskId, prompt, label, phaseName, schema)
}

async function runDiscovery() {
  if (!SPEC.discovery_tasks.length) return []
  const calls = SPEC.discovery_tasks.map((task) => async () => {
    const prompt = [
      'Perform one bounded read-only discovery task for a software plan.',
      `Rough goal: ${SPEC.objective}`,
      `Discovery objective: ${task.objective}`,
      `Local inspection: ${JSON.stringify(SPEC.inspection)}`,
      'Return only repository evidence that changes architecture, scope, tests, routing, or risk.',
      'Do not write an implementation plan and do not ask for facts available from the repository.',
      'A material question is only one whose answer changes product behavior, public/persistence contract, architecture, security, cost, scope, or risk.',
    ].join('\n\n')
    return runRouted(
      task.route,
      'discovery',
      task.id,
      prompt,
      `discover:${task.id}:${task.route}`,
      'Discover',
      DISCOVERY_SCHEMA,
    )
  })
  return calls.length === 1 ? [await calls[0]()] : parallel(calls)
}

function plannerContract() {
  return [
    'Return a compact semantic planning draft. The workflow deterministically injects provider/model/effort routing and compiles RoutePlan v4; never choose or describe route aliases.',
    'For each bounded task return id, objective, expected_artifact, dependencies, non_goals, relative allowed_paths, permission, complexity, acceptance_checks, targeted_commands, and affected_commands.',
    'Return final_acceptance_checks and the complete mandatory regression_commands for the final zero-tolerance gate.',
    '- zero tolerance for every observed failure, including flaky, timeout, infrastructure, stale, and pre-existing failures.',
    'Every targeted/affected/regression command is one non-destructive verification or test command that runs after implementation, never a prose test name or a command that creates/edits the requested artifact.',
    'A build worker performs implementation. Never put implementation commands such as output redirection into targeted_commands, affected_commands, or regression_commands.',
    'acceptance_checks describe observable outcomes and invariants, not implementation steps.',
    'Use the minimum dependency graph. Fold deterministic verification into the implementing task checks instead of inventing separate review tasks unless a real dependency boundary requires one.',
    'affected_commands may be empty when there is no wider affected suite; the compiler then reuses targeted_commands without another planning round.',
    'allowed_paths are relative to working_directory, never absolute.',
    'Use safe unique task ids matching letters, digits, dot, underscore, or hyphen. Dependencies must reference task ids in this same draft and must be acyclic.',
    'All DRAFT_READY arrays required for execution must be non-empty: tasks, each allowed_paths/acceptance_checks/targeted_commands/affected_commands, final_acceptance_checks, and regression_commands.',
    'The architecture envelope must settle system boundaries, owners, data flow, invariants, approved scope, rollback, and high-level milestones.',
    'Detail only the immediate dependency wave and, when evidence-stable, the next wave. Keep later milestones at contract level; do not invent line-by-line implementation ten steps ahead.',
    'The complete task graph must still cover the approved objective, and every future task must begin with recalibration against current repository evidence.',
  ].join('\n')
}

function plannerRoute(tier) {
  return SPEC.routes.planners[tier]
}

function criticRoute(tier) {
  return SPEC.routes.critics[tier]
}

async function runPlanner(discovery, revisionEvidence, round, tier) {
  const route = plannerRoute(tier)
  const prompt = [
    `Act as the ${tier}-tier planning agent for a visible software-development workflow.`,
    `Rough goal: ${SPEC.objective}`,
    `Working directory: ${SPEC.working_directory}`,
    `Local inspection: ${JSON.stringify(SPEC.inspection)}`,
    `Bounded discovery results: ${JSON.stringify(discovery)}`,
    `Persisted user/context evidence: ${JSON.stringify(SPEC.context)}`,
    `The zero-token preclassifier selected ${SPEC.initial_planning_tier}: ${SPEC.tier_signals.join('; ')}`,
    revisionEvidence.length
      ? `Bounded correction evidence from earlier rounds: ${JSON.stringify(revisionEvidence)}`
      : '',
    plannerContract(),
    'Classify risk as routine, strong, or frontier from architecture, contracts, migration, concurrency, security, cross-system coupling, rollback, and interacting unknowns.',
    'Do not raise risk or expand proof obligations merely because an earlier critic found a local command, wording, or coverage defect. Correct that defect at the current tier.',
    'Do not invent acceptance requirements beyond the user goal and repository evidence. In particular, do not add mtime, ignored-file inventory, internal .git snapshots, or similar proof obligations unless the original goal requires them.',
    'When a critic flags an unnecessary self-imposed invariant, remove that invariant instead of adding checks for it.',
    'Keep deterministic checks minimal, executable, and directly traceable to one user requirement or repository contract.',
    'Ask only material user decisions. Resolve repository facts yourself from the supplied evidence or read-only tools.',
    'Return status=DRAFT_READY with the compact task draft, or AWAITING_USER_DECISION/BLOCKED with exact evidence.',
  ].filter(Boolean).join('\n\n')
  return runRouted(
    route,
    'planner',
    `planner-r${round}`,
    prompt,
    `planner:${route}:r${round}`,
    'Plan',
    PLANNER_SCHEMA,
  )
}

function grillAssignments(riskLevel) {
  if (riskLevel === 'routine') return []
  if (riskLevel === 'strong') {
    return [{
      route: SPEC.routes.strong_griller,
      role: 'architecture-contract-breaker',
    }]
  }
  const roles = [
    'assumption-architecture-breaker',
    'failure-mode-test-scope-breaker',
  ]
  return SPEC.routes.frontier_grillers.map((route, index) => ({
    route,
    role: roles[index] || `independent-breaker-${index + 1}`,
  }))
}

async function runGrill(draft, routePlan, round) {
  const assignments = grillAssignments(draft.risk_level)
  if (!assignments.length) return []
  const calls = assignments.map((assignment, index) => async () => {
    const prompt = [
      `Act as the ${assignment.role} for an adversarial architecture grill.`,
      `Goal: ${SPEC.objective}`,
      `Architecture envelope: ${JSON.stringify(draft.architecture_envelope)}`,
      `Deterministically compiled RoutePlan: ${JSON.stringify(routePlan)}`,
      'Try to break architecture, ownership, contracts, sequencing, rollback, scope, test oracles, and the immediate execution wave.',
      'Your own review harness is intentionally read-only. That is not evidence that the later coding worker or target worktree is read-only.',
      `Treat the supplied target-workspace inspection as authoritative: ${JSON.stringify(SPEC.inspection)}`,
      'Do not challenge the plan merely because this reviewer cannot write files, cannot mutate Git, or has a restricted tool profile.',
      'A planner contradiction, invented requirement, malformed command, or calculable fact is a revision finding, never a user decision.',
      'A proposed choice between two corrective edits to the plan is a revision finding, not a user decision.',
      'Ask the user only when the original goal leaves a genuinely material product, contract, architecture, security, cost, or scope choice unresolved.',
      'Do not perform detailed implementation planning for distant milestones. Challenge them only when their high-level contracts contradict the architecture envelope.',
      'Do not re-litigate settled choices without new evidence. A repository-answerable uncertainty is not a user question.',
      'PASS only when no material blocker remains.',
    ].join('\n\n')
    return runRouted(
      assignment.route,
      'plan-griller',
      `grill-${round}-${index + 1}`,
      prompt,
      `grill:${assignment.role}:${assignment.route}:r${round}`,
      'Grill',
      GRILL_SCHEMA,
    )
  })
  return calls.length === 1 ? [await calls[0]()] : parallel(calls)
}

async function runCritic(draft, routePlan, grillResults, round) {
  const route = criticRoute(draft.risk_level)
  const prompt = [
    `Act as the independent ${draft.risk_level}-or-stronger critic for the final RoutePlan.`,
    `Goal: ${SPEC.objective}`,
    `Architecture envelope: ${JSON.stringify(draft.architecture_envelope)}`,
    `Observed grill results: ${JSON.stringify(grillResults)}`,
    `Deterministically compiled RoutePlan: ${JSON.stringify(routePlan)}`,
    'Your own critic harness is intentionally read-only. That is not evidence that the later coding worker or target worktree is read-only.',
    `Treat the supplied target-workspace inspection as authoritative: ${JSON.stringify(SPEC.inspection)}`,
    'Do not challenge the plan merely because this critic cannot write files, mutate Git, create temporary files, or has a restricted tool profile.',
    'A planner contradiction, invented requirement, malformed command, or calculable fact belongs in findings, not material_questions.',
    'A proposed choice between two corrective edits to the plan belongs in findings, not material_questions.',
    'Ask the user only when the original goal leaves a genuinely material product, contract, architecture, security, cost, or scope choice unresolved.',
    'The RoutePlan is JSON-serialized in this prompt. Judge command strings after JSON decoding; JSON escaping such as \\n does not by itself add a runtime backslash or make a command malformed.',
    'Require evidence only for the original goal, repository contracts, and material architecture claims needed to execute it. Do not turn optional or gratuitous planner wording into a new acceptance requirement.',
    'If the plan contains a stronger self-imposed invariant than the user requested, challenge it only when it creates execution risk; recommend removing the gratuitous invariant rather than adding tests for it.',
    'Do not require mtime proof, ignored-file inventory, or internal .git snapshots unless the original goal explicitly asks for those properties.',
    'A local check-command or wording defect is a bounded same-tier correction, not evidence that the task itself needs a frontier planner.',
    'Do not require snapshots of internal .git metadata for an ordinary source/file-scope promise; worker tool policy already forbids Git-history mutation unless the original goal explicitly concerns Git internals.',
    'Check scope, architecture, dependencies, risk, route/effort selection, provider independence, test pyramid, zero-tolerance acceptance, budget, and rollback.',
    'Reject detailed speculation about distant implementation when a high-level milestone contract plus mandatory recalibration is sufficient.',
    'PASS only if the plan is executable as a visible workflow and no material blocker remains.',
  ].join('\n\n')
  return runRouted(
    route,
    'plan-critic',
    `critic-r${round}`,
    prompt,
    `critic:${route}:r${round}`,
    'Critique',
    CRITIC_SCHEMA,
  )
}

function fingerprint(value) {
  return JSON.stringify(value).toLowerCase().replace(/\s+/g, ' ').trim()
}

function nextTier(tier) {
  if (tier === 'routine') return 'strong'
  return 'frontier'
}

function semanticDraftFindings(draft) {
  const findings = []
  const nonEmptyStrings = (value) =>
    Array.isArray(value) && value.length > 0 &&
    value.every((item) => typeof item === 'string' && item.trim())
  if (!Array.isArray(draft.tasks) || !draft.tasks.length) {
    findings.push('DRAFT_READY requires at least one bounded task')
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
    if (typeof task.objective !== 'string' || !task.objective.trim()) {
      findings.push(`task ${task.id || '<unknown>'}.objective must be non-empty`)
    }
    if (typeof task.expected_artifact !== 'string' || !task.expected_artifact.trim()) {
      findings.push(`task ${task.id || '<unknown>'}.expected_artifact must be non-empty`)
    }
    for (const field of ['allowed_paths', 'acceptance_checks', 'targeted_commands']) {
      if (!nonEmptyStrings(task[field])) {
        findings.push(`task ${task.id || '<unknown>'}.${field} must contain non-empty strings`)
      }
    }
    if (
      !Array.isArray(task.affected_commands) ||
      !task.affected_commands.every((item) => typeof item === 'string' && item.trim())
    ) {
      findings.push(`task ${task.id || '<unknown>'}.affected_commands must contain only non-empty strings`)
    }
    for (const path of task.allowed_paths || []) {
      const normalized = path.replaceAll('\\', '/')
      if (
        normalized.startsWith('/') || normalized === '..' ||
        normalized.startsWith('../') || normalized.includes('/../')
      ) {
        findings.push(`task ${task.id || '<unknown>'} path escapes the working directory: ${path}`)
      }
      if (/(^|\/)(?:\.env(?:\.|$)|[^/]*(?:credential|secret)[^/]*)(?:\/|$)/i.test(normalized)) {
        findings.push(`task ${task.id || '<unknown>'} includes a protected path: ${path}`)
      }
    }
    for (const command of [
      ...(task.targeted_commands || []),
      ...(task.affected_commands || []),
    ]) {
      if (
        /\brm\s+-[A-Za-z]*r[A-Za-z]*f\b|\bgit\s+(?:reset|clean|checkout|restore|stash|commit|push|merge|rebase)\b|\b(?:sudo|shutdown|reboot|mkfs)\b/i.test(command)
      ) {
        findings.push(`task ${task.id || '<unknown>'} contains a destructive check command: ${command}`)
      }
    }
  }
  for (const task of draft.tasks) {
    for (const dependency of task.dependencies || []) {
      if (dependency === task.id) {
        findings.push(`task ${task.id} depends on itself`)
      } else if (!ids.has(dependency)) {
        findings.push(`task ${task.id} depends on unknown task ${dependency}`)
      }
    }
  }
  const visiting = new Set()
  const visited = new Set()
  const taskById = new Map(draft.tasks.map((task) => [task.id, task]))
  const hasCycle = (taskId) => {
    if (visiting.has(taskId)) return true
    if (visited.has(taskId) || !taskById.has(taskId)) return false
    visiting.add(taskId)
    for (const dependency of taskById.get(taskId).dependencies || []) {
      if (hasCycle(dependency)) return true
    }
    visiting.delete(taskId)
    visited.add(taskId)
    return false
  }
  if ([...taskById.keys()].some((taskId) => hasCycle(taskId))) {
    findings.push('task dependencies contain a cycle')
  }
  if (!nonEmptyStrings(draft.final_acceptance_checks)) {
    findings.push('final_acceptance_checks must contain non-empty strings')
  }
  if (!nonEmptyStrings(draft.regression_commands)) {
    findings.push('regression_commands must contain non-empty executable commands')
  }
  for (const command of draft.regression_commands || []) {
    if (
      /\brm\s+-[A-Za-z]*r[A-Za-z]*f\b|\bgit\s+(?:reset|clean|checkout|restore|stash|commit|push|merge|rebase)\b|\b(?:sudo|shutdown|reboot|mkfs)\b/i.test(command)
    ) {
      findings.push(`regression_commands contains a destructive check command: ${command}`)
    }
  }
  return findings
}

function materialQuestions(results) {
  return [...new Set(results.flatMap((result) => result?.material_questions || []))]
}

function grillBlockers(results) {
  return results.flatMap((result) => {
    if (!result || result.verdict !== 'PASS' || result.material_questions?.length) {
      return [
        ...(result?.blocking_findings || ['griller returned no valid PASS result']),
        ...(result?.invalid_assumptions || []),
        ...(result?.missing_tests || []),
        ...(result?.scope_rollback_concerns || []),
        ...(result?.material_questions || []),
      ]
    }
    return []
  })
}

function checkSpecs(commands) {
  return commands.map((command) => ({ command, timeout_seconds: 300 }))
}

function effectiveRisk(draft) {
  return draft.tasks.reduce(
    (highest, task) => TIER_LEVEL[task.complexity] > TIER_LEVEL[highest]
      ? task.complexity
      : highest,
    draft.risk_level,
  )
}

function buildRoutePlan(draft, planner, rounds) {
  const riskLevel = effectiveRisk(draft)
  const assignments = grillAssignments(riskLevel)
  const required = riskLevel !== 'routine'
  const finalLadders = ROUTING_LADDERS[riskLevel]
  return {
    schema_version: 4,
    workflow_id: `workflow-${SPEC.session_id.slice(0, 12)}`,
    objective: SPEC.objective,
    working_directory: SPEC.working_directory,
    planning: {
      mode: 'adaptive',
      session_id: SPEC.session_id,
      discovery_performed: SPEC.discovery_tasks.length > 0,
      planner_route: planner,
      critic_route: criticRoute(riskLevel),
      critic_verdict: 'PASS',
      assumptions: draft.assumptions,
      architecture_envelope: draft.architecture_envelope,
      grill: {
        level: riskLevel,
        required,
        signals: required
          ? [`${riskLevel} risk selected from architecture, task complexity, and repository evidence`]
          : [],
        routes: assignments.map((item) => item.route),
        roles: assignments.map((item) => item.role),
        rounds: required ? rounds : 0,
        open_blockers: [],
        verdict: required ? 'PASS' : 'SKIPPED',
      },
    },
    approval: {
      premium_routes: [],
      max_api_budget_usd: null,
      allow_openrouter_primary: false,
    },
    tasks: draft.tasks.map((task) => {
      const ladders = ROUTING_LADDERS[task.complexity]
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
        routes: [...ladders.routes],
        verifier_routes: [...ladders.verifier_routes],
        diagnosis_routes: [...DIAGNOSIS_ROUTES],
        test_intent_verifier_routes: [...ladders.test_intent_verifier_routes],
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
      routes: [...finalLadders.routes],
      verifier_routes: [...finalLadders.verifier_routes],
      diagnosis_routes: [...DIAGNOSIS_ROUTES],
      acceptance_checks: draft.final_acceptance_checks,
      test_plan: {
        regression: checkSpecs(draft.regression_commands),
      },
    },
  }
}

function applyPlanningEvidence(routePlan, draft, rounds, planner) {
  const assignments = grillAssignments(draft.risk_level)
  const required = draft.risk_level !== 'routine'
  routePlan.planning = {
    ...routePlan.planning,
    mode: 'adaptive',
    session_id: SPEC.session_id,
    discovery_performed: SPEC.discovery_tasks.length > 0,
    planner_route: planner,
    critic_route: criticRoute(draft.risk_level),
    critic_verdict: 'PASS',
    assumptions: draft.assumptions,
    architecture_envelope: draft.architecture_envelope,
    grill: {
      level: draft.risk_level,
      required,
      signals: required
        ? [`${draft.risk_level} risk selected by the adaptive planner from architecture and repository evidence`]
        : [],
      routes: assignments.map((item) => item.route),
      roles: assignments.map((item) => item.role),
      rounds: required ? rounds : 0,
      open_blockers: [],
      verdict: required ? 'PASS' : 'SKIPPED',
    },
  }
}

phase('Discover')
const discovery = await runDiscovery()
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

const seenFindings = new Set()
const revisionEvidence = []
const correctionFailuresByTier = { routine: 0, strong: 0, frontier: 0 }
let round = 1
let planningTier = SPEC.initial_planning_tier

function tierAfterCorrection(currentTier) {
  correctionFailuresByTier[currentTier] += 1
  if (correctionFailuresByTier[currentTier] < 2 || currentTier === 'frontier') {
    return currentTier
  }
  return nextTier(currentTier)
}

while (true) {
  phase('Plan')
  const activePlanner = plannerRoute(planningTier)
  const draft = await runPlanner(discovery, revisionEvidence, round, planningTier)
  if (!draft || draft.status === 'BLOCKED') {
    return {
      status: 'BLOCKED',
      route_plan: null,
      material_questions: [],
      blocker: draft?.blocker || 'adaptive planner returned no valid draft',
      discovery,
    }
  }
  if (draft.status === 'AWAITING_USER_DECISION' || draft.material_questions.length) {
    return {
      status: 'AWAITING_USER_DECISION',
      route_plan: null,
      material_questions: draft.material_questions,
      blocker: null,
      discovery,
    }
  }
  const draftFindings = semanticDraftFindings(draft)
  if (draftFindings.length) {
    const draftFingerprint = fingerprint(draftFindings)
    if (seenFindings.has(draftFingerprint) && planningTier === 'frontier') {
      return {
        status: 'BLOCKED',
        route_plan: null,
        material_questions: [],
        blocker: 'frontier planner repeated the same malformed semantic draft',
        discovery,
      }
    }
    seenFindings.add(draftFingerprint)
    revisionEvidence.push({
      source: 'semantic-draft-validation',
      round,
      findings: draftFindings,
    })
    planningTier = nextTier(planningTier)
    round += 1
    continue
  }
  const requiredTier = effectiveRisk(draft)
  if (TIER_LEVEL[requiredTier] > TIER_LEVEL[planningTier]) {
    revisionEvidence.push({
      source: 'risk-escalation',
      round,
      from: planningTier,
      to: requiredTier,
      reason: 'planner found higher architecture or task risk than the current planning tier',
    })
    planningTier = requiredTier
    round += 1
    continue
  }
  draft.risk_level = requiredTier
  const routePlan = buildRoutePlan(draft, activePlanner, round)

  phase('Grill')
  const grillResults = await runGrill(draft, routePlan, round)
  const blockers = grillBlockers(grillResults)
  if (blockers.length) {
    const findingFingerprint = fingerprint(blockers)
    if (seenFindings.has(findingFingerprint)) {
      if (planningTier === 'frontier') {
        return {
          status: 'BLOCKED',
          route_plan: null,
          material_questions: [],
          blocker: 'frontier adversarial grill repeated the same unresolved material findings',
          discovery,
          grill: grillResults,
        }
      }
      revisionEvidence.push({
        source: 'grill-repeat-escalation',
        round,
        blockers,
        reports: grillResults,
      })
      planningTier = nextTier(planningTier)
      round += 1
      continue
    }
    seenFindings.add(findingFingerprint)
    revisionEvidence.push({ source: 'grill', round, blockers, reports: grillResults })
    planningTier = tierAfterCorrection(planningTier)
    round += 1
    continue
  }

  applyPlanningEvidence(routePlan, draft, round, activePlanner)
  phase('Critique')
  const critic = await runCritic(draft, routePlan, grillResults, round)
  if (critic?.verdict === 'PASS' && !critic?.material_questions?.length) {
    return {
      status: 'PLAN_READY',
      route_plan: routePlan,
      material_questions: [],
      blocker: null,
      architecture_envelope: draft.architecture_envelope,
      discovery,
      grill: grillResults,
      critic,
      rounds: round,
    }
  }
  const criticFindings = [
    ...(critic?.findings || []),
    ...(critic?.material_questions || []),
  ]
  if (!criticFindings.length) {
    criticFindings.push('independent critic returned no valid PASS result')
  }
  const criticFingerprint = fingerprint(criticFindings)
  if (seenFindings.has(criticFingerprint)) {
    if (planningTier === 'frontier') {
      return {
        status: 'BLOCKED',
        route_plan: null,
        material_questions: [],
        blocker: 'frontier critic repeated the same unresolved material findings',
        discovery,
        grill: grillResults,
        critic,
      }
    }
    revisionEvidence.push({
      source: 'critic-repeat-escalation',
      round,
      findings: criticFindings,
      report: critic,
    })
    planningTier = nextTier(planningTier)
    round += 1
    continue
  }
  seenFindings.add(criticFingerprint)
  revisionEvidence.push({ source: 'critic', round, findings: criticFindings, report: critic })
  planningTier = tierAfterCorrection(planningTier)
  round += 1
}
