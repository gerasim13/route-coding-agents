export const meta = /*__AI_ROUTER_META__*/ null

const PLAN = /*__AI_ROUTER_PLAN__*/ null
const DELEGATE_TOOL = 'mcp__plugin_ai-router_ai-router__delegate'
const RECORD_VERDICT_TOOL = 'mcp__plugin_ai-router_ai-router__record_verdict'
const RUN_CHECK_SUITE_TOOL = 'mcp__plugin_ai-router_ai-router__run_check_suite'

const WORKER_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['status', 'summary', 'changed_files', 'checks', 'error'],
  properties: {
    status: { type: 'string', enum: ['COMPLETED', 'FAILED', 'UNAVAILABLE', 'TIMED_OUT', 'BLOCKED'] },
    summary: { type: 'string' },
    changed_files: { type: 'array', items: { type: 'string' } },
    checks: { type: 'array', items: { type: 'string' } },
    error: { type: ['string', 'null'] },
  },
}

const VERIFIER_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['verdict', 'summary', 'findings', 'checks', 'failure_packet'],
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'FAIL', 'BLOCKED'] },
    summary: { type: 'string' },
    findings: { type: 'array', items: { type: 'string' } },
    checks: { type: 'array', items: { type: 'string' } },
    failure_packet: { type: 'string' },
  },
}

const REPLAN_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['can_progress', 'revised_objective', 'approach_fingerprint', 'rationale', 'additional_checks', 'blocker'],
  properties: {
    can_progress: { type: 'boolean' },
    revised_objective: { type: 'string' },
    approach_fingerprint: { type: 'string' },
    rationale: { type: 'string' },
    additional_checks: { type: 'array', items: { type: 'string' } },
    blocker: { type: ['string', 'null'] },
  },
}

const CHECK_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: [
    'status', 'level', 'command', 'attempts', 'rerun_performed', 'return_code',
    'duration_ms', 'workspace_changed', 'failure_signature', 'stdout_excerpt',
    'stderr_excerpt', 'log_path', 'zero_tolerance',
  ],
  properties: {
    status: { type: 'string', enum: ['PASS', 'FAIL', 'SUSPECTED_FLAKY', 'TIMED_OUT', 'STALE'] },
    level: { type: 'string', enum: ['targeted', 'affected', 'regression'] },
    command: { type: 'string' },
    attempts: { type: 'integer' },
    rerun_performed: { type: 'boolean' },
    return_code: { type: ['integer', 'null'] },
    duration_ms: { type: 'integer' },
    workspace_changed: { type: 'boolean' },
    failure_signature: { type: ['string', 'null'] },
    stdout_excerpt: { type: 'string' },
    stderr_excerpt: { type: 'string' },
    log_path: { type: 'string' },
    zero_tolerance: { type: 'boolean' },
  },
}

const CHECK_SUITE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: [
    'status', 'level', 'checks_requested', 'checks_completed', 'results',
    'first_non_green', 'duration_ms', 'zero_tolerance',
  ],
  properties: {
    status: { type: 'string', enum: ['PASS', 'FAIL', 'SUSPECTED_FLAKY', 'TIMED_OUT', 'STALE'] },
    level: { type: 'string', enum: ['targeted', 'affected', 'regression'] },
    checks_requested: { type: 'integer' },
    checks_completed: { type: 'integer' },
    results: { type: 'array', items: CHECK_SCHEMA },
    first_non_green: { anyOf: [CHECK_SCHEMA, { type: 'null' }] },
    duration_ms: { type: 'integer' },
    zero_tolerance: { type: 'boolean' },
  },
}

const DIAGNOSIS_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: [
    'status', 'cause', 'confidence', 'suspected_paths', 'summary',
    'failure_signature', 'recommended_fix', 'repair_tier', 'scope_status', 'blocker',
  ],
  properties: {
    status: { type: 'string', enum: ['DIAGNOSED', 'BLOCKED'] },
    cause: { type: 'string' },
    confidence: { type: 'string', enum: ['low', 'medium', 'high'] },
    suspected_paths: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    failure_signature: { type: ['string', 'null'] },
    recommended_fix: { type: 'string' },
    repair_tier: { type: 'string', enum: ['routine', 'strong', 'frontier'] },
    scope_status: { type: 'string', enum: ['IN_SCOPE', 'OUT_OF_SCOPE'] },
    blocker: { type: ['string', 'null'] },
  },
}

const EVIDENCE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: [
    'status', 'summary', 'failure_signature', 'evidence', 'log_path',
    'route_status', 'route_error',
  ],
  properties: {
    status: { type: 'string', enum: ['SUMMARIZED', 'BLOCKED'] },
    summary: { type: 'string' },
    failure_signature: { type: ['string', 'null'] },
    evidence: { type: 'array', items: { type: 'string' } },
    log_path: { type: ['string', 'null'] },
    route_status: {
      type: 'string',
      enum: ['OK', 'UNAVAILABLE', 'TIMED_OUT', 'MALFORMED'],
    },
    route_error: { type: ['string', 'null'] },
  },
}

const CALIBRATION_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: [
    'verdict', 'summary', 'findings', 'task_updates',
    'material_question', 'requested_paths',
  ],
  properties: {
    verdict: { type: 'string', enum: ['ALIGNED', 'REPLAN', 'SCOPE_CHANGE', 'BLOCKED'] },
    summary: { type: 'string' },
    findings: { type: 'array', items: { type: 'string' } },
    task_updates: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'revised_objective', 'additional_checks'],
        properties: {
          id: { type: 'string' },
          revised_objective: { type: 'string' },
          additional_checks: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    material_question: { type: ['string', 'null'] },
    requested_paths: { type: 'array', items: { type: 'string' } },
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

function rolePhase(role) {
  if (role === 'verifier' || role === 'test-intent-verifier' || role === 'final-gate') {
    return role === 'final-gate' ? 'Final gate' : 'Verify'
  }
  if (role === 'log-summarizer' || role === 'failure-triage') return 'Triage'
  if (role === 'frontier-replanner' || role === 'repair' || role === 'diagnostician') return 'Escalate'
  return 'Execute'
}

function routeCapability(route) {
  if ([
    'codex-sol', 'codex-high', 'claude-opus', 'claude-best',
    'openrouter-deepseek-frontier', 'kimi-k3',
  ].includes(route)) return 3
  if ([
    'corporate-pro', 'corporate-qwen', 'corporate-minimax', 'corporate-glm',
    'minimax-m3', 'deepseek-pro', 'openrouter-deepseek',
    'codex-terra', 'codex', 'claude-sonnet',
  ].includes(route)) return 2
  return 1
}

function providerGroup(route) {
  if (route.startsWith('codex')) return 'openai-subscription'
  if (route.startsWith('claude')) return 'anthropic-subscription'
  if (route.startsWith('corporate')) return 'corporate-litellm'
  if (route.startsWith('minimax')) return 'minimax'
  if (route === 'cheap' || route === 'deepseek-pro') return 'deepseek'
  return 'openrouter'
}

function routeSeed(value) {
  return [...value].reduce(
    (total, character) => (total + character.charCodeAt(0)) % 65536,
    0,
  )
}

function evidenceRoutes(task, attempt) {
  const seed = routeSeed(`${PLAN.workflow_id}:${task.id}:${attempt}`)
  return [
    'minimax-fast',
    'openrouter-cheap',
    'cheap',
    'corporate-flash',
    'codex-luna',
  ].sort((left, right) => {
    const leftCalls = Number(PLAN.planning.route_usage?.[left] || 0)
    const rightCalls = Number(PLAN.planning.route_usage?.[right] || 0)
    if (leftCalls !== rightCalls) return leftCalls - rightCalls
    return routeSeed(`${seed}:${left}`) - routeSeed(`${seed}:${right}`)
  })
}

function statusFromRouter(status) {
  if (status === 'completed') return 'COMPLETED'
  if (status === 'unavailable') return 'UNAVAILABLE'
  if (status === 'timed_out') return 'TIMED_OUT'
  return 'FAILED'
}

function delegationArgs(route, role, taskId, profile, prompt) {
  const value = {
    workflow_id: PLAN.workflow_id,
    task_id: taskId,
    role,
    route,
    profile,
    working_directory: PLAN.working_directory,
    prompt,
    timeout_seconds: profile === 'build' ? 1800 : 600,
  }
  if (route === 'kimi-k3') value.budget_usd = PLAN.approval.max_api_budget_usd
  return value
}

async function runExternalWorker(route, role, task, prompt, label, profile) {
  const args = delegationArgs(route, role, task.id, profile, prompt)
  const wrapperPrompt = [
    'You are a transparent one-generation AI Router wrapper.',
    'Do not inspect the repository and do not solve the coding task yourself.',
    `Call ${DELEGATE_TOOL} EXACTLY ONCE with the JSON arguments below. It is your only available action tool.`,
    'Do not retry inside this agent. A failure must remain visible to the workflow as a separate later agent.',
    'Map the tool result into the requested schema. Use its output as summary. Preserve status faithfully.',
    `Map router status with this rule: completed=COMPLETED, unavailable=UNAVAILABLE, timed_out=TIMED_OUT, otherwise FAILED.`,
    '',
    JSON.stringify(args),
  ].join('\n')
  return agent(wrapperPrompt, {
    label,
    phase: rolePhase(role),
    schema: WORKER_SCHEMA,
    model: 'haiku',
    agentType: 'ai-router:external-worker',
    maxTurns: 4,
  })
}

async function runNativeWorker(route, role, task, prompt, label) {
  return agent(
    `${prompt}\n\nYou are the native Claude ${role} for this visible workflow node. Work only in ${PLAN.working_directory}. Do not commit, push, merge, rebase, reset, clean, stash, or publish. Return the requested structured report.`,
    withNativeEffort(route, {
      label,
      phase: rolePhase(role),
      schema: WORKER_SCHEMA,
      model: nativeModel(route),
      agentType: 'ai-router:coding-worker',
    }),
  )
}

async function runWorker(route, role, task, objective, evidence, attempt) {
  const profile = task.permission === 'build' ? 'build' : 'review'
  const label = `${role}:${task.id}:${route}:a${attempt}`
  const prompt = [
    `OBJECTIVE:\n${objective}`,
    `EXPECTED ARTIFACT:\n${task.expected_artifact}`,
    `WORKING DIRECTORY:\n${PLAN.working_directory}`,
    `ALLOWED PATHS:\n${task.allowed_paths.join('\n')}`,
    `NON-GOALS:\n${(task.non_goals || []).join('\n') || 'None beyond scope.'}`,
    `ACCEPTANCE CHECKS:\n${task.acceptance_checks.join('\n')}`,
    evidence.length ? `FAILURE EVIDENCE FROM EARLIER ATTEMPTS:\n${JSON.stringify(evidence)}` : '',
    'Implement or investigate the bounded task. Inspect the current worktree rather than trusting earlier claims.',
    'Do not run the planned targeted, affected, or regression commands yourself; deterministic check nodes own them.',
    'Do not modify Git history or publish. Report uncertainty instead of expanding scope.',
    'Return status, concise summary, changed_files, checks actually run, and error.',
  ].filter(Boolean).join('\n\n')
  return isNative(route)
    ? runNativeWorker(route, role, task, prompt, label)
    : runExternalWorker(route, role, task, prompt, label, profile)
}

async function runDeterministicCheckSuite(taskId, level, checks, sequence) {
  const args = {
    workflow_id: PLAN.workflow_id,
    task_id: `${taskId}-${level}-${sequence}`.slice(0, 64),
    working_directory: PLAN.working_directory,
    level,
    checks: checks.map((check) => ({
      command: check.command,
      ...(check.rerun_command ? { rerun_command: check.rerun_command } : {}),
      timeout_seconds: check.timeout_seconds || 3600,
    })),
  }
  const prompt = [
    'You are a transparent deterministic check-suite wrapper, not a coding model.',
    'Do not inspect, edit, diagnose, retry, or summarize the repository yourself.',
    `Call ${RUN_CHECK_SUITE_TOOL} EXACTLY ONCE with the JSON below. It is your only action tool.`,
    'Map the returned suite and per-command evidence into the requested schema without changing status.',
    'FAIL, SUSPECTED_FLAKY, TIMED_OUT, and STALE are all non-green.',
    '',
    JSON.stringify(args),
  ].join('\n')
  return agent(prompt, {
    label: `check-suite:${taskId}:${level}:${sequence}`,
    phase: level === 'regression' ? 'Final gate' : 'Check',
    schema: CHECK_SUITE_SCHEMA,
    model: 'haiku',
    agentType: 'ai-router:external-worker',
    maxTurns: 4,
  })
}

function deterministicCheckKey(check) {
  return JSON.stringify([
    check.command,
    check.rerun_command || null,
    check.timeout_seconds || 3600,
  ])
}

async function runCheckLevel(task, level, sequenceBase = 0, passedChecks = new Map()) {
  const checks = task.test_plan?.[level] || []
  const results = []
  const pendingChecks = []
  for (const check of checks) {
    const checkKey = deterministicCheckKey(check)
    const reusable = passedChecks.get(checkKey)
    if (
      reusable &&
      reusable.status === 'PASS' &&
      reusable.workspace_changed === false
    ) {
      results.push({
        ...reusable,
        level,
        reused_from_level: reusable.level,
        reused_identical_check: true,
      })
      continue
    }
    pendingChecks.push(check)
  }
  if (!pendingChecks.length) return results
  const suite = await runDeterministicCheckSuite(
    task.id,
    level,
    pendingChecks,
    sequenceBase + 1,
  )
  for (let index = 0; index < (suite?.results || []).length; index += 1) {
    const result = suite.results[index]
    results.push(result)
    if (
      result &&
      result.status === 'PASS' &&
      result.workspace_changed === false
    ) {
      passedChecks.set(deterministicCheckKey(pendingChecks[index]), result)
    }
  }
  if (!suite || !suite.results?.length) {
    results.push(null)
  }
  return results
}

function firstNonGreen(checks) {
  return checks.find((check) => !check || check.status !== 'PASS') || null
}

async function runExternalVerifier(route, task, workerRoute, workerResult, attempt, finalGate = false, verificationRole = 'verifier') {
  const role = finalGate ? 'final-gate' : verificationRole
  const taskId = finalGate ? 'final-gate' : task.id
  const verifierPrompt = [
    'You are an independent, read-only verifier. Inspect the CURRENT worktree yourself.',
    `Objective: ${task.objective}`,
    `Expected artifact: ${task.expected_artifact}`,
    `Allowed paths: ${task.allowed_paths.join(', ')}`,
    `Acceptance checks:\n${task.acceptance_checks.join('\n')}`,
    `Worker route: ${workerRoute}`,
    `Worker report:\n${JSON.stringify(workerResult)}`,
    'Use the supplied deterministic check evidence. Do not rerun tests and do not edit source files.',
    'Return exactly one JSON object with keys: verdict (PASS|FAIL|BLOCKED), summary, findings (string array), checks (string array), failure_packet.',
    'PASS only with evidence. On FAIL, failure_packet must contain the exact error, relevant diff scope, failed approach, and what a stronger worker should change.',
  ].join('\n\n')
  const args = {
    ...delegationArgs(route, role, taskId, 'verify', verifierPrompt),
    record_verdict_from_output: true,
  }
  const wrapperPrompt = [
    'You are a transparent one-generation AI Router verifier wrapper.',
    `Call ${DELEGATE_TOOL} EXACTLY ONCE with the JSON arguments below.`,
    'Do not inspect or edit the repository yourself. Do not retry.',
    'The delegated model was asked for a JSON verdict. Map it into the requested schema.',
    'If its response is malformed, unavailable, timed out, or lacks executable evidence, return FAIL and include the raw issue in failure_packet.',
    'The delegate call records any valid JSON verdict locally in the same call; do not call another tool.',
    '',
    JSON.stringify(args),
  ].join('\n')
  return agent(wrapperPrompt, {
    label: `${role}:${taskId}:${route}:a${attempt}`,
    phase: rolePhase(role),
    schema: VERIFIER_SCHEMA,
    model: 'haiku',
    agentType: 'ai-router:external-worker',
    maxTurns: 4,
  })
}

async function runNativeVerifier(route, task, workerRoute, workerResult, attempt, finalGate = false, verificationRole = 'verifier') {
  const role = finalGate ? 'final-gate' : verificationRole
  const taskId = finalGate ? 'final-gate' : task.id
  const prompt = [
    'Act as an independent, read-only verifier. Inspect the CURRENT worktree yourself.',
    `Working directory: ${PLAN.working_directory}`,
    `Objective: ${task.objective}`,
    `Expected artifact: ${task.expected_artifact}`,
    `Allowed paths: ${task.allowed_paths.join(', ')}`,
    `Acceptance checks:\n${task.acceptance_checks.join('\n')}`,
    `Worker route: ${workerRoute}`,
    `Worker report:\n${JSON.stringify(workerResult)}`,
    'Use the supplied deterministic check evidence. Do not rerun tests or edit source files or Git history.',
    'PASS only with evidence. On FAIL, failure_packet must include exact errors, diff scope, failed approach, and instructions for a stronger worker.',
    `Call ${RECORD_VERDICT_TOOL} after deciding. Call it exactly once with workflow_id=${PLAN.workflow_id}, task_id=${taskId}, route=${route}, the lowercase verdict, and concise evidence. This recorder does not call a model; preserve your verdict if recording fails.`,
  ].join('\n\n')
  return agent(prompt, withNativeEffort(route, {
    label: `${role}:${taskId}:${route}:a${attempt}`,
    phase: rolePhase(role),
    schema: VERIFIER_SCHEMA,
    model: nativeModel(route),
    agentType: 'ai-router:reviewer-readonly',
  }))
}

async function runVerifier(route, task, workerRoute, workerResult, attempt, finalGate = false, verificationRole = 'verifier') {
  return isNative(route)
    ? runNativeVerifier(route, task, workerRoute, workerResult, attempt, finalGate, verificationRole)
    : runExternalVerifier(route, task, workerRoute, workerResult, attempt, finalGate, verificationRole)
}

async function runEvidenceSummarizer(task, failureEvidence, attempt) {
  const routes = evidenceRoutes(task, attempt)
  const attempts = []
  for (let index = 0; index < Math.min(routes.length, 3); index += 1) {
    const route = routes[index]
    const prompt = [
      'Act as a bounded failure-evidence summarizer, not a root-cause diagnostician.',
      `Working directory: ${PLAN.working_directory}`,
      `Task objective: ${task.objective}`,
      `Structured non-green evidence: ${JSON.stringify(failureEvidence)}`,
      'Read only the explicitly cited log_path files when their bounded excerpts are insufficient.',
      'Do not edit, rerun tests, inspect unrelated code, propose a fix, or dismiss failures as pre-existing.',
      'Return the stable failure signature, exact errors, relevant log facts, and a compact lossless summary for a separate strong diagnostician.',
      'Set route_status=OK and route_error=null only for a valid completed summary.',
    ].join('\n\n')
    const args = {
      ...delegationArgs(
        route,
        'log-summarizer',
        `${task.id}-evidence-${attempt}-${index + 1}`.slice(0, 64),
        'review',
        prompt,
      ),
      timeout_seconds: 300,
    }
    const wrapperPrompt = [
      'You are a transparent one-generation AI Router evidence wrapper.',
      `Call ${DELEGATE_TOOL} EXACTLY ONCE with the JSON below.`,
      'Do not inspect logs, diagnose, edit, or retry yourself.',
      'Map a valid delegated JSON object into the requested schema with route_status=OK.',
      'For unavailable, timed-out, or malformed output, return status=BLOCKED, preserve the exact cause in route_error, and set route_status accordingly.',
      '',
      JSON.stringify(args),
    ].join('\n')
    const result = await agent(wrapperPrompt, {
      label: `log-summarizer:${task.id}:${route}:a${attempt}:f${index + 1}`,
      phase: 'Triage',
      schema: EVIDENCE_SCHEMA,
      model: 'haiku',
      agentType: 'ai-router:external-worker',
      maxTurns: 4,
    })
    attempts.push({ route, result })
    if (result?.route_status === 'OK' && result?.status === 'SUMMARIZED') {
      return { route, result, attempts }
    }
  }
  return {
    route: attempts[attempts.length - 1]?.route || routes[0],
    result: null,
    attempts,
  }
}

async function runExternalDiagnosis(route, task, failureEvidence, attempt) {
  const prompt = [
    'You are a strong read-only root-cause diagnostician. Do not edit files and do not rerun tests.',
    `Working directory: ${PLAN.working_directory}`,
    `Objective: ${task.objective}`,
    `Allowed paths: ${task.allowed_paths.join(', ')}`,
    `Structured failure evidence:\n${JSON.stringify(failureEvidence)}`,
    'Inspect only the relevant current code. A pre-existing failure is still an active defect, never permission to ignore it.',
    'Classify scope as OUT_OF_SCOPE when the required fix needs paths outside the approved allowed_paths.',
    'Choose repair_tier by the diagnosed repair itself: routine for precise mechanical work, strong for substantial work, frontier for ambiguity or contract/architecture risk.',
    'Return exactly one JSON object matching: status, cause, confidence, suspected_paths, summary, failure_signature, recommended_fix, repair_tier, scope_status, blocker.',
  ].join('\n\n')
  const args = delegationArgs(route, 'diagnostician', task.id, 'review', prompt)
  const wrapperPrompt = [
    'You are a transparent one-generation AI Router diagnosis wrapper.',
    `Call ${DELEGATE_TOOL} EXACTLY ONCE with the JSON below.`,
    'Do not inspect, edit, retry, or diagnose anything yourself. Map delegated JSON into the requested schema.',
    'If malformed or unavailable, return status=BLOCKED, confidence=low, scope_status=IN_SCOPE, repair_tier=frontier, and explain the exact issue in blocker.',
    '',
    JSON.stringify(args),
  ].join('\n')
  return agent(wrapperPrompt, {
    label: `diagnose:${task.id}:${route}:a${attempt}`,
    phase: 'Escalate',
    schema: DIAGNOSIS_SCHEMA,
    model: 'haiku',
    agentType: 'ai-router:external-worker',
    maxTurns: 4,
  })
}

async function runNativeDiagnosis(route, task, failureEvidence, attempt) {
  const prompt = [
    'Act as a strong read-only root-cause diagnostician. Do not edit files and do not rerun tests.',
    `Working directory: ${PLAN.working_directory}`,
    `Objective: ${task.objective}`,
    `Allowed paths: ${task.allowed_paths.join(', ')}`,
    `Structured failure evidence:\n${JSON.stringify(failureEvidence)}`,
    'Inspect only relevant current code. Any observed failure is an active defect even if it predates this workflow.',
    'Use OUT_OF_SCOPE only when the required fix needs paths outside allowed_paths.',
    'Choose repair_tier from the diagnosed repair complexity. Return the requested structured diagnosis.',
  ].join('\n\n')
  return agent(prompt, withNativeEffort(route, {
    label: `diagnose:${task.id}:${route}:a${attempt}`,
    phase: 'Escalate',
    schema: DIAGNOSIS_SCHEMA,
    model: nativeModel(route),
    agentType: 'ai-router:reviewer-readonly',
  }))
}

async function runDiagnosis(task, failureEvidence, attempt) {
  const results = []
  const start = Math.min(attempt - 1, task.diagnosis_routes.length - 1)
  for (let index = start; index < task.diagnosis_routes.length; index += 1) {
    const route = task.diagnosis_routes[index]
    const result = isNative(route)
      ? await runNativeDiagnosis(route, task, failureEvidence, index + 1)
      : await runExternalDiagnosis(route, task, failureEvidence, index + 1)
    results.push({ route, result })
    if (result?.status === 'DIAGNOSED') return { route, result, attempts: results }
  }
  return {
    route: task.diagnosis_routes[task.diagnosis_routes.length - 1],
    result: results[results.length - 1]?.result || null,
    attempts: results,
  }
}

function changedExistingTests(worker) {
  return (worker?.changed_files || []).filter((path) =>
    /(^|\/)(tests?|specs?)(\/|$)|(?:^|[._-])(?:test|spec)\.[^/]+$/i.test(path)
  )
}

async function runTestIntentVerifier(task, workerRoute, worker, checkEvidence, attempt) {
  const changedTests = changedExistingTests(worker)
  if (!changedTests.length) return null
  const route = task.test_intent_verifier_routes[
    Math.min(attempt - 1, task.test_intent_verifier_routes.length - 1)
  ]
  const intentTask = {
    ...task,
    objective: [
      'Verify that existing test changes preserve intended contract and coverage.',
      `Changed tests: ${changedTests.join(', ')}`,
      'Reject deleted or weakened assertions whose only purpose is obtaining green output.',
    ].join('\n'),
  }
  const result = await runVerifier(
    route,
    intentTask,
    workerRoute,
    { ...worker, checks: checkEvidence },
    attempt,
    false,
    'test-intent-verifier',
  )
  return { route, result, changed_tests: changedTests }
}

async function runExternalReplanner(route, task, evidence, cycle) {
  const prompt = [
    'You are the frontier replanner for a coding task that failed after escalation.',
    `Objective: ${task.objective}`,
    `Expected artifact: ${task.expected_artifact}`,
    `Acceptance checks:\n${task.acceptance_checks.join('\n')}`,
    `Accumulated failure evidence:\n${JSON.stringify(evidence)}`,
    'Do not edit files. Find a materially different approach using the current repository state.',
    'Return exactly one JSON object: can_progress, revised_objective, approach_fingerprint, rationale, additional_checks, blocker.',
    'Set can_progress=false only for a real external blocker or when no distinct evidence-based approach exists.',
  ].join('\n\n')
  const args = delegationArgs(route, 'frontier-replanner', task.id, 'review', prompt)
  const wrapperPrompt = [
    'You are a transparent one-generation AI Router frontier-replanner wrapper.',
    `Call ${DELEGATE_TOOL} EXACTLY ONCE with the JSON below. It is your only available action tool.`,
    'Do not inspect the repository or retry. Map the delegated JSON into the requested schema.',
    'If malformed, return can_progress=false and describe the malformed result as blocker.',
    '',
    JSON.stringify(args),
  ].join('\n')
  return agent(wrapperPrompt, {
    label: `replan:${task.id}:${route}:c${cycle}`,
    phase: 'Escalate', schema: REPLAN_SCHEMA, model: 'haiku',
    agentType: 'ai-router:external-worker', maxTurns: 4,
  })
}

async function runNativeReplanner(route, task, evidence, cycle) {
  const prompt = [
    'You are the frontier replanner for a coding task that failed after escalation.',
    `Working directory: ${PLAN.working_directory}`,
    `Objective: ${task.objective}`,
    `Expected artifact: ${task.expected_artifact}`,
    `Acceptance checks:\n${task.acceptance_checks.join('\n')}`,
    `Accumulated failure evidence:\n${JSON.stringify(evidence)}`,
    'Inspect read-only. Find a materially different approach. Do not edit files.',
    'Set can_progress=false only for a real external blocker or when no distinct evidence-based approach exists.',
  ].join('\n\n')
  return agent(prompt, withNativeEffort(route, {
    label: `replan:${task.id}:${route}:c${cycle}`,
    phase: 'Escalate', schema: REPLAN_SCHEMA, model: nativeModel(route),
    agentType: 'ai-router:reviewer-readonly',
  }))
}

async function runReplanner(route, task, evidence, cycle) {
  return isNative(route)
    ? runNativeReplanner(route, task, evidence, cycle)
    : runExternalReplanner(route, task, evidence, cycle)
}

async function evaluateWorker(task, workerRoute, worker, attempt) {
  const passedChecks = new Map()
  const targeted = await runCheckLevel(task, 'targeted', attempt * 100, passedChecks)
  const targetedFailure = firstNonGreen(targeted)
  if (targetedFailure) {
    return {
      passed: false,
      failure: { stage: 'targeted', check: targetedFailure, checks: targeted, worker },
    }
  }
  const affected = await runCheckLevel(
    task,
    'affected',
    attempt * 100 + targeted.length,
    passedChecks,
  )
  const affectedFailure = firstNonGreen(affected)
  const checkEvidence = [...targeted, ...affected]
  if (affectedFailure) {
    return {
      passed: false,
      failure: { stage: 'affected', check: affectedFailure, checks: checkEvidence, worker },
    }
  }

  const testIntent = await runTestIntentVerifier(task, workerRoute, worker, checkEvidence, attempt)
  if (testIntent && testIntent.result?.verdict !== 'PASS') {
    return {
      passed: false,
      failure: { stage: 'test-intent', test_intent: testIntent, checks: checkEvidence, worker },
    }
  }

  const verifierRoute = task.verifier_routes[Math.min(attempt - 1, task.verifier_routes.length - 1)]
  const verifier = await runVerifier(
    verifierRoute,
    task,
    workerRoute,
    { ...worker, checks: checkEvidence },
    attempt,
  )
  if (!verifier || verifier.verdict !== 'PASS') {
    return {
      passed: false,
      failure: {
        stage: 'independent-verifier',
        verifier_route: verifierRoute,
        verifier: verifier || { verdict: 'FAIL', failure_packet: 'verifier returned no structured result' },
        checks: checkEvidence,
        worker,
      },
    }
  }
  return { passed: true, checks: checkEvidence, verifier, verifier_route: verifierRoute, test_intent: testIntent }
}

function nextRepairIndex(routes, currentIndex, diagnosis) {
  const required = diagnosis?.repair_tier === 'frontier' ? 3 : diagnosis?.repair_tier === 'strong' ? 2 : 1
  for (let index = currentIndex + 1; index < routes.length; index += 1) {
    if (routeCapability(routes[index]) >= required) return index
  }
  return routes.length
}

async function diagnoseOrScope(task, failure, attempt) {
  const evidenceSummary = await runEvidenceSummarizer(task, failure, attempt)
  const diagnosis = await runDiagnosis(
    task,
    {
      raw_failure: failure,
      routed_evidence_summary: evidenceSummary.result,
      summarizer_route: evidenceSummary.route,
      summarizer_attempts: evidenceSummary.attempts,
    },
    attempt,
  )
  if (diagnosis.result?.status !== 'DIAGNOSED') {
    return {
      terminal: {
        status: 'BLOCKED',
        task_id: task.id,
        blocker: diagnosis.result?.blocker || 'all strong/frontier diagnosticians failed to establish a repair path',
        diagnosis,
        evidence_summary: evidenceSummary,
      },
      diagnosis,
      evidenceSummary,
    }
  }
  if (diagnosis.result.scope_status === 'OUT_OF_SCOPE') {
    return {
      terminal: {
        status: 'AWAITING_SCOPE_APPROVAL',
        task_id: task.id,
        blocker: 'the diagnosed repair requires paths outside the approved scope',
        requested_paths: diagnosis.result.suspected_paths,
        diagnosis,
        evidence_summary: evidenceSummary,
      },
      diagnosis,
      evidenceSummary,
    }
  }
  return { terminal: null, diagnosis, evidenceSummary }
}

async function runTask(task) {
  const evidence = []
  let objective = task.objective
  let attempt = 0
  let routeIndex = 0

  while (routeIndex < task.routes.length) {
    attempt += 1
    const workerRoute = task.routes[routeIndex]
    const worker = await runWorker(workerRoute, routeIndex ? 'repair' : 'worker', task, objective, evidence, attempt)
    if (!worker) {
      evidence.push({ route: workerRoute, failure: 'worker returned no structured result' })
      routeIndex += 1
      continue
    }
    if (worker.status === 'UNAVAILABLE') {
      evidence.push({ route: workerRoute, failure: worker.error || worker.summary || 'route unavailable' })
      routeIndex += 1
      continue
    }
    const evaluation = worker.status === 'COMPLETED'
      ? await evaluateWorker(task, workerRoute, worker, attempt)
      : { passed: false, failure: { stage: 'worker', worker } }
    if (evaluation.passed) {
      return {
        status: 'VERIFIED',
        task_id: task.id,
        worker_route: workerRoute,
        verifier_route: evaluation.verifier_route,
        worker,
        verifier: evaluation.verifier,
        test_intent: evaluation.test_intent,
        checks: evaluation.checks,
        attempts: attempt,
      }
    }
    const diagnosed = await diagnoseOrScope(task, evaluation.failure, attempt)
    evidence.push({
      route: workerRoute,
      worker,
      failure: evaluation.failure,
      evidence_summary: diagnosed.evidenceSummary,
      diagnosis: diagnosed.diagnosis,
    })
    if (diagnosed.terminal) return { ...diagnosed.terminal, evidence }
    objective = [
      task.objective,
      'Apply this independently diagnosed repair without ignoring any observed failure:',
      diagnosed.diagnosis.result.recommended_fix,
    ].join('\n\n')
    routeIndex = nextRepairIndex(task.routes, routeIndex, diagnosed.diagnosis.result)
  }

  const frontierRoute = task.routes[task.routes.length - 1]
  const seenApproaches = new Set()
  let cycle = 0
  while (true) {
    cycle += 1
    const replan = await runReplanner(frontierRoute, task, evidence, cycle)
    if (!replan || !replan.can_progress) {
      return { status: 'BLOCKED', task_id: task.id, blocker: replan?.blocker || 'frontier replanner found no evidence-based next approach', evidence }
    }
    const fingerprint = replan.approach_fingerprint.trim()
    if (!fingerprint || seenApproaches.has(fingerprint)) {
      return { status: 'BLOCKED', task_id: task.id, blocker: 'frontier replanner repeated an already-failed approach', evidence, replan }
    }
    seenApproaches.add(fingerprint)
    objective = replan.revised_objective
    if (replan.additional_checks?.length) {
      task = { ...task, acceptance_checks: [...task.acceptance_checks, ...replan.additional_checks] }
    }
    attempt += 1
    const worker = await runWorker(frontierRoute, 'repair', task, objective, evidence, attempt)
    if (!worker || worker.status === 'UNAVAILABLE') {
      evidence.push({ frontier_cycle: cycle, replan, worker })
      continue
    }
    const evaluation = worker.status === 'COMPLETED'
      ? await evaluateWorker(task, frontierRoute, worker, attempt)
      : { passed: false, failure: { stage: 'worker', worker } }
    if (evaluation.passed) {
      return {
        status: 'VERIFIED',
        task_id: task.id,
        worker_route: frontierRoute,
        verifier_route: evaluation.verifier_route,
        worker,
        verifier: evaluation.verifier,
        test_intent: evaluation.test_intent,
        checks: evaluation.checks,
        attempts: attempt,
        frontier_cycles: cycle,
      }
    }
    const diagnosed = await diagnoseOrScope(task, evaluation.failure, attempt)
    evidence.push({
      frontier_cycle: cycle,
      replan,
      worker,
      failure: evaluation.failure,
      evidence_summary: diagnosed.evidenceSummary,
      diagnosis: diagnosed.diagnosis,
    })
    if (diagnosed.terminal) return { ...diagnosed.terminal, evidence }
  }
}

async function runExternalCalibration(route, completedIds, remainingTasks, taskResults, wave, priorEvidence) {
  const prompt = [
    'Act as an independent read-only execution calibrator after one dependency wave.',
    `Approved objective: ${PLAN.objective}`,
    `Architecture envelope: ${JSON.stringify(PLAN.planning.architecture_envelope || {})}`,
    `Completed task ids: ${completedIds.join(', ')}`,
    `Completed results: ${JSON.stringify(taskResults)}`,
    `Remaining approved tasks: ${JSON.stringify(remainingTasks)}`,
    priorEvidence.length ? `Earlier calibration evidence: ${JSON.stringify(priorEvidence)}` : '',
    'Compare current repository evidence with the approved architecture, scope, completed wave, and next dependency wave.',
    'Use ALIGNED when the plan remains sound. Use REPLAN for in-scope drift that requires revised objectives or checks.',
    'Use SCOPE_CHANGE only when required paths or product/public/persistence behavior exceed approved scope.',
    'Use BLOCKED only for an exact external blocker. Do not ignore any observed failure as pre-existing.',
    'Return concise findings and proposed task_updates, but do not edit or run tests.',
  ].filter(Boolean).join('\n\n')
  const args = delegationArgs(route, 'calibrator', `calibration-wave-${wave}`, 'verify', prompt)
  const wrapperPrompt = [
    'You are a transparent one-generation AI Router calibration wrapper.',
    `Call ${DELEGATE_TOOL} EXACTLY ONCE with the JSON below.`,
    'Do not inspect, edit, retry, or calibrate anything yourself. Map delegated JSON into the requested schema.',
    'If malformed or unavailable, return verdict=BLOCKED with the exact provider failure in findings.',
    '',
    JSON.stringify(args),
  ].join('\n')
  return agent(wrapperPrompt, {
    label: `calibrate:wave-${wave}:${route}`,
    phase: 'Calibrate',
    schema: CALIBRATION_SCHEMA,
    model: 'haiku',
    agentType: 'ai-router:external-worker',
    maxTurns: 4,
  })
}

async function runNativeCalibration(route, completedIds, remainingTasks, taskResults, wave, priorEvidence) {
  const prompt = [
    'Act as an independent read-only execution calibrator after one dependency wave.',
    `Working directory: ${PLAN.working_directory}`,
    `Approved objective: ${PLAN.objective}`,
    `Architecture envelope: ${JSON.stringify(PLAN.planning.architecture_envelope || {})}`,
    `Completed task ids: ${completedIds.join(', ')}`,
    `Completed results: ${JSON.stringify(taskResults)}`,
    `Remaining approved tasks: ${JSON.stringify(remainingTasks)}`,
    priorEvidence.length ? `Earlier calibration evidence: ${JSON.stringify(priorEvidence)}` : '',
    'Inspect the current repository and compare it with the approved architecture, scope, completed wave, and next dependency wave.',
    'Do not edit or run the planned tests. ALIGNED means the plan remains sound; REPLAN means in-scope drift; SCOPE_CHANGE means new approval is required.',
    'Every observed failure remains active work regardless of provenance.',
  ].filter(Boolean).join('\n\n')
  return agent(prompt, withNativeEffort(route, {
    label: `calibrate:wave-${wave}:${route}`,
    phase: 'Calibrate',
    schema: CALIBRATION_SCHEMA,
    model: nativeModel(route),
    agentType: 'ai-router:reviewer-readonly',
  }))
}

async function runCalibrationRoute(route, completedIds, remainingTasks, taskResults, wave, priorEvidence = []) {
  return isNative(route)
    ? runNativeCalibration(route, completedIds, remainingTasks, taskResults, wave, priorEvidence)
    : runExternalCalibration(route, completedIds, remainingTasks, taskResults, wave, priorEvidence)
}

function chooseCalibrationRoute(taskResults) {
  const workerProviders = new Set(
    Object.values(taskResults)
      .map((result) => result?.worker_route)
      .filter(Boolean)
      .map(providerGroup),
  )
  return [
    'corporate-glm',
    'minimax-m3',
    'openrouter-deepseek',
    'codex-terra',
    'claude-sonnet',
  ]
    .find((route) => !workerProviders.has(providerGroup(route))) || 'codex-terra'
}

async function calibrateWave(completedIds, pending, taskResults, wave) {
  const remainingTasks = [...pending.values()]
  const terminalRoutineWave =
    remainingTasks.length === 0 &&
    PLAN.tasks.every((task) => task.complexity === 'routine')
  const strongRoute = terminalRoutineWave
    ? 'claude-haiku'
    : chooseCalibrationRoute(taskResults)
  const strong = await runCalibrationRoute(
    strongRoute,
    completedIds,
    remainingTasks,
    taskResults,
    wave,
  )
  if (strong?.verdict === 'ALIGNED') return { terminal: null, calibration: { strongRoute, strong } }
  if (strong?.verdict === 'SCOPE_CHANGE') {
    return {
      terminal: {
        status: 'AWAITING_SCOPE_APPROVAL',
        blocker: strong.material_question || 'calibration found a required scope change',
        requested_paths: strong.requested_paths,
        calibration: { strongRoute, strong },
      },
      calibration: { strongRoute, strong },
    }
  }

  const frontierRoutes = ['claude-best', 'openrouter-deepseek-frontier']
  const frontier = await parallel(frontierRoutes.map((route) => () =>
    runCalibrationRoute(
      route,
      completedIds,
      remainingTasks,
      taskResults,
      wave,
      [{ route: strongRoute, result: strong }],
    ),
  ))
  const scopeFinding = frontier.find((result) => result?.verdict === 'SCOPE_CHANGE')
  if (scopeFinding) {
    return {
      terminal: {
        status: 'AWAITING_SCOPE_APPROVAL',
        blocker: scopeFinding.material_question || 'frontier calibration confirmed a required scope change',
        requested_paths: scopeFinding.requested_paths,
        calibration: { strongRoute, strong, frontierRoutes, frontier },
      },
      calibration: { strongRoute, strong, frontierRoutes, frontier },
    }
  }
  if (frontier.every((result) => result?.verdict === 'ALIGNED')) {
    return {
      terminal: null,
      calibration: { strongRoute, strong, frontierRoutes, frontier, resolution: 'frontier-overruled-strong-drift' },
    }
  }
  if (!remainingTasks.length) {
    return {
      terminal: null,
      calibration: { strongRoute, strong, frontierRoutes, frontier, resolution: 'final-gate-must-resolve-drift' },
    }
  }

  const evidence = [{ route: strongRoute, result: strong }, ...frontierRoutes.map(
    (route, index) => ({ route, result: frontier[index] }),
  )]
  const replans = await parallel(remainingTasks.map((task, index) => () =>
    runReplanner(frontierRoutes[index % frontierRoutes.length], task, evidence, wave),
  ))
  for (let index = 0; index < remainingTasks.length; index += 1) {
    const task = remainingTasks[index]
    const replan = replans[index]
    if (!replan?.can_progress) {
      return {
        terminal: {
          status: 'BLOCKED',
          task_id: task.id,
          blocker: replan?.blocker || 'frontier recalibration found no distinct in-scope next approach',
          calibration: { strongRoute, strong, frontierRoutes, frontier, replans },
        },
        calibration: { strongRoute, strong, frontierRoutes, frontier, replans },
      }
    }
    const updated = {
      ...task,
      objective: replan.revised_objective,
      acceptance_checks: [
        ...task.acceptance_checks,
        ...(replan.additional_checks || []),
      ],
    }
    pending.set(task.id, updated)
  }
  return {
    terminal: null,
    calibration: { strongRoute, strong, frontierRoutes, frontier, replans, resolution: 'remaining-wave-replanned' },
  }
}

async function runTaskGraph() {
  const pending = new Map(PLAN.tasks.map((task) => [task.id, task]))
  const results = {}
  const calibrations = []
  let wave = 0
  while (pending.size) {
    for (const [taskId, task] of [...pending.entries()]) {
      const blockedDependency = task.dependencies.find((dependency) => results[dependency] && results[dependency].status !== 'VERIFIED')
      if (blockedDependency) {
        const dependencyStatus = results[blockedDependency].status
        results[taskId] = {
          status: dependencyStatus === 'AWAITING_SCOPE_APPROVAL' ? 'AWAITING_SCOPE_APPROVAL' : 'BLOCKED',
          task_id: taskId,
          blocker: `dependency ${blockedDependency} was not verified`,
        }
        pending.delete(taskId)
      }
    }
    const ready = [...pending.values()].filter((task) => task.dependencies.every((dependency) => results[dependency]?.status === 'VERIFIED'))
    if (!ready.length) break
    wave += 1
    const batch = ready.length === 1
      ? [await runTask(ready[0])]
      : await parallel(ready.map((task) => () => runTask(task)))
    ready.forEach((task, index) => {
      results[task.id] = batch[index]
      pending.delete(task.id)
    })
    if (batch.every((result) => result?.status === 'VERIFIED')) {
      phase('Calibrate')
      const calibrated = await calibrateWave(
        ready.map((task) => task.id),
        pending,
        results,
        wave,
      )
      calibrations.push(calibrated.calibration)
      if (calibrated.terminal) {
        return { results, calibrations, terminal: calibrated.terminal }
      }
      phase('Execute')
    }
  }
  for (const taskId of pending.keys()) {
    results[taskId] = { status: 'BLOCKED', task_id: taskId, blocker: 'no runnable dependency path remained' }
  }
  return { results, calibrations, terminal: null }
}

async function runFinalGate(taskResults) {
  const buildTasks = PLAN.tasks.filter((task) => task.permission === 'build')
  const allAllowedPaths = [...new Set(PLAN.tasks.flatMap((task) => task.allowed_paths))]
  const repairAllowedPaths = [...new Set(buildTasks.flatMap((task) => task.allowed_paths))]
  const finalTask = {
    id: 'final-gate',
    objective: `Verify the combined worktree for: ${PLAN.objective}`,
    expected_artifact: 'A fully verified worktree satisfying every approved task',
    dependencies: [],
    non_goals: [
      'Preserve unrelated pre-workflow source changes unless the diagnosed repair requires an approved scope amendment.',
      'Never ignore a test failure because it appears pre-existing; provenance is diagnostic evidence only.',
      'Do not require a globally clean worktree unless the plan recorded a clean pre-workflow baseline.',
    ],
    allowed_paths: allAllowedPaths,
    permission: buildTasks.length ? 'build' : 'review',
    acceptance_checks: PLAN.final_gate.acceptance_checks,
    routes: PLAN.final_gate.routes,
    verifier_routes: PLAN.final_gate.verifier_routes,
    diagnosis_routes: PLAN.final_gate.diagnosis_routes,
    test_intent_verifier_routes: PLAN.final_gate.verifier_routes.filter((route) => routeCapability(route) >= 2),
    test_plan: {
      targeted: [],
      affected: [],
      regression: PLAN.final_gate.test_plan.regression,
    },
  }
  const seenFailurePackets = new Set()
  let cycle = 0
  let verifierAttempt = 0
  while (true) {
    cycle += 1
    const regression = await runCheckLevel(finalTask, 'regression', cycle * 1000)
    const regressionFailure = firstNonGreen(regression)
    const gates = []
    let failurePacket = ''
    if (regressionFailure) {
      const diagnosed = await diagnoseOrScope(
        finalTask,
        { stage: 'regression', check: regressionFailure, checks: regression },
        cycle,
      )
      if (diagnosed.terminal) {
        return {
          ...diagnosed.terminal,
          regression,
          cycles: cycle,
        }
      }
      failurePacket = [
        'Mandatory regression is not green.',
        JSON.stringify(regressionFailure),
        `Diagnosis: ${JSON.stringify(diagnosed.diagnosis)}`,
      ].join('\n')
    } else {
      for (const verifierRoute of PLAN.final_gate.verifier_routes) {
        verifierAttempt += 1
        const gate = await runVerifier(
          verifierRoute,
          finalTask,
          'combined-workflow',
          {
            status: 'COMPLETED',
            summary: JSON.stringify(taskResults),
            changed_files: [],
            checks: regression,
            error: null,
          },
          verifierAttempt,
          true,
        )
        gates.push({ route: verifierRoute, result: gate })
        if (gate && gate.verdict === 'PASS') {
          return { status: 'VERIFIED', regression, gate, gates, cycles: cycle }
        }
      }
      failurePacket = gates
        .map(({ route, result }) => `${route}:${result?.failure_packet || result?.summary || 'missing final gate result'}`)
        .join('\n')
      const diagnosed = await diagnoseOrScope(
        finalTask,
        { stage: 'final-verifier', gates, regression },
        cycle,
      )
      if (diagnosed.terminal) {
        return {
          ...diagnosed.terminal,
          regression,
          gates,
          cycles: cycle,
        }
      }
      failurePacket += `\nDiagnosis: ${JSON.stringify(diagnosed.diagnosis)}`
    }
    const failureFingerprint = failurePacket.toLowerCase().replace(/\s+/g, ' ').trim()
    if (seenFailurePackets.has(failureFingerprint)) {
      return {
        status: 'BLOCKED',
        blocker: 'the complete final-gate verifier ladder repeated the same failure after a verified repair',
        regression,
        gates,
        cycles: cycle,
      }
    }
    seenFailurePackets.add(failureFingerprint)

    if (!buildTasks.length) {
      return {
        status: 'BLOCKED',
        blocker: 'read-only workflow is not fully green; automatic repair is forbidden',
        regression,
        gates,
        cycles: cycle,
      }
    }

    const escalationIndex = Math.min(cycle - 1, PLAN.final_gate.routes.length - 1)
    const repairRoutes = PLAN.final_gate.routes.slice(escalationIndex)
    const repairVerifierRoutes = repairRoutes.map(
      (_route, index) => PLAN.final_gate.verifier_routes[
        Math.min(escalationIndex + index, PLAN.final_gate.verifier_routes.length - 1)
      ],
    )
    const repairTask = {
      ...finalTask,
      id: `final-repair-${cycle}`,
      objective: `Resolve the independently confirmed final-gate failures without touching pre-existing out-of-scope changes:\n${failurePacket}`,
      allowed_paths: repairAllowedPaths,
      permission: 'build',
      routes: repairRoutes,
      verifier_routes: repairVerifierRoutes,
    }
    const repair = await runTask(repairTask)
    if (!repair || repair.status !== 'VERIFIED') {
      return { status: 'BLOCKED', gates, repair, cycles: cycle }
    }
  }
}

phase('Execute')
const graph = await runTaskGraph()
const taskResults = graph.results
if (graph.terminal) {
  return {
    status: graph.terminal.status,
    workflow_id: PLAN.workflow_id,
    tasks: taskResults,
    calibrations: graph.calibrations,
    blocked: [graph.terminal],
  }
}
const blockedTasks = Object.values(taskResults).filter((result) => result.status !== 'VERIFIED')
if (blockedTasks.length) {
  const status = blockedTasks.some((result) => result.status === 'AWAITING_SCOPE_APPROVAL')
    ? 'AWAITING_SCOPE_APPROVAL'
    : 'BLOCKED'
  return {
    status,
    workflow_id: PLAN.workflow_id,
    tasks: taskResults,
    calibrations: graph.calibrations,
    blocked: blockedTasks,
  }
}

phase('Final gate')
const finalGate = await runFinalGate(taskResults)
return {
  status: finalGate.status,
  workflow_id: PLAN.workflow_id,
  tasks: taskResults,
  calibrations: graph.calibrations,
  final_gate: finalGate,
}
