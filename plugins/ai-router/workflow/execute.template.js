export const meta = /*__AI_ROUTER_META__*/ null

const PLAN = /*__AI_ROUTER_PLAN__*/ null
const DELEGATE_TOOL = 'mcp__plugin_ai-router_ai-router__delegate'
const RECORD_VERDICT_TOOL = 'mcp__plugin_ai-router_ai-router__record_verdict'

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

function isNative(route) {
  return route === 'claude-sonnet' || route === 'claude-opus'
}

function nativeModel(route) {
  return route === 'claude-opus' ? 'opus' : 'sonnet'
}

function rolePhase(role) {
  if (role === 'verifier' || role === 'final-gate') return role === 'final-gate' ? 'Final gate' : 'Verify'
  if (role === 'frontier-replanner' || role === 'repair') return 'Escalate'
  return 'Execute'
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
    timeout_seconds: 7200,
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
    effort: 'low',
    tools: [DELEGATE_TOOL],
    maxTurns: 4,
  })
}

async function runNativeWorker(route, role, task, prompt, label) {
  return agent(
    `${prompt}\n\nYou are the native Claude ${role} for this visible workflow node. Work only in ${PLAN.working_directory}. Do not commit, push, merge, rebase, reset, clean, stash, or publish. Return the requested structured report.`,
    {
      label,
      phase: rolePhase(role),
      schema: WORKER_SCHEMA,
      model: nativeModel(route),
      effort: route === 'claude-opus' ? 'high' : 'medium',
      tools: ['Read', 'Edit', 'Write', 'Glob', 'Grep', 'Bash'],
    },
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
    'Do not modify Git history or publish. Report uncertainty instead of expanding scope.',
    'Return status, concise summary, changed_files, checks actually run, and error.',
  ].filter(Boolean).join('\n\n')
  return isNative(route)
    ? runNativeWorker(route, role, task, prompt, label)
    : runExternalWorker(route, role, task, prompt, label, profile)
}

async function runExternalVerifier(route, task, workerRoute, workerResult, attempt, finalGate = false) {
  const role = finalGate ? 'final-gate' : 'verifier'
  const taskId = finalGate ? 'final-gate' : task.id
  const verifierPrompt = [
    'You are an independent, read-only verifier. Inspect the CURRENT worktree yourself.',
    `Objective: ${task.objective}`,
    `Expected artifact: ${task.expected_artifact}`,
    `Allowed paths: ${task.allowed_paths.join(', ')}`,
    `Acceptance checks:\n${task.acceptance_checks.join('\n')}`,
    `Worker route: ${workerRoute}`,
    `Worker report:\n${JSON.stringify(workerResult)}`,
    'Run the deterministic checks where possible. Do not edit source files.',
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
    effort: 'low',
    tools: [DELEGATE_TOOL],
    maxTurns: 4,
  })
}

async function runNativeVerifier(route, task, workerRoute, workerResult, attempt, finalGate = false) {
  const role = finalGate ? 'final-gate' : 'verifier'
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
    'Run deterministic checks where possible. Do not edit source files or Git history.',
    'PASS only with evidence. On FAIL, failure_packet must include exact errors, diff scope, failed approach, and instructions for a stronger worker.',
    `Call ${RECORD_VERDICT_TOOL} after deciding. Call it exactly once with workflow_id=${PLAN.workflow_id}, task_id=${taskId}, route=${route}, the lowercase verdict, and concise evidence. This recorder does not call a model; preserve your verdict if recording fails.`,
  ].join('\n\n')
  return agent(prompt, {
    label: `${role}:${taskId}:${route}:a${attempt}`,
    phase: rolePhase(role),
    schema: VERIFIER_SCHEMA,
    model: nativeModel(route),
    effort: route === 'claude-opus' ? 'high' : 'medium',
    tools: ['Read', 'Glob', 'Grep', 'Bash', RECORD_VERDICT_TOOL],
  })
}

async function runVerifier(route, task, workerRoute, workerResult, attempt, finalGate = false) {
  return isNative(route)
    ? runNativeVerifier(route, task, workerRoute, workerResult, attempt, finalGate)
    : runExternalVerifier(route, task, workerRoute, workerResult, attempt, finalGate)
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
    phase: 'Escalate', schema: REPLAN_SCHEMA, model: 'haiku', effort: 'low',
    tools: [DELEGATE_TOOL], maxTurns: 4,
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
  return agent(prompt, {
    label: `replan:${task.id}:${route}:c${cycle}`,
    phase: 'Escalate', schema: REPLAN_SCHEMA, model: nativeModel(route),
    effort: route === 'claude-opus' ? 'high' : 'medium',
    tools: ['Read', 'Glob', 'Grep', 'Bash'],
  })
}

async function runReplanner(route, task, evidence, cycle) {
  return isNative(route)
    ? runNativeReplanner(route, task, evidence, cycle)
    : runExternalReplanner(route, task, evidence, cycle)
}

async function runTask(task) {
  const evidence = []
  let objective = task.objective
  let attempt = 0

  for (let routeIndex = 0; routeIndex < task.routes.length; routeIndex += 1) {
    attempt += 1
    const workerRoute = task.routes[routeIndex]
    const worker = await runWorker(workerRoute, routeIndex ? 'repair' : 'worker', task, objective, evidence, attempt)
    if (!worker) {
      evidence.push({ route: workerRoute, failure: 'worker returned no structured result' })
      continue
    }
    if (worker.status === 'UNAVAILABLE') {
      evidence.push({ route: workerRoute, failure: worker.error || worker.summary || 'route unavailable' })
      continue
    }
    const verifierRoute = task.verifier_routes[Math.min(routeIndex, task.verifier_routes.length - 1)]
    const verifier = await runVerifier(verifierRoute, task, workerRoute, worker, attempt)
    if (verifier && verifier.verdict === 'PASS') {
      return { status: 'VERIFIED', task_id: task.id, worker_route: workerRoute, verifier_route: verifierRoute, worker, verifier, attempts: attempt }
    }
    evidence.push({
      route: workerRoute,
      worker,
      verifier_route: verifierRoute,
      verifier: verifier || { verdict: 'FAIL', failure_packet: 'verifier returned no structured result' },
    })
  }

  const frontierRoute = task.routes[task.routes.length - 1]
  const frontierVerifier = task.verifier_routes[task.verifier_routes.length - 1]
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
    const verifier = worker && worker.status !== 'UNAVAILABLE'
      ? await runVerifier(frontierVerifier, task, frontierRoute, worker, attempt)
      : null
    if (verifier && verifier.verdict === 'PASS') {
      return { status: 'VERIFIED', task_id: task.id, worker_route: frontierRoute, verifier_route: frontierVerifier, worker, verifier, attempts: attempt, frontier_cycles: cycle }
    }
    evidence.push({ frontier_cycle: cycle, replan, worker, verifier })
  }
}

async function runTaskGraph() {
  const pending = new Map(PLAN.tasks.map((task) => [task.id, task]))
  const results = {}
  while (pending.size) {
    for (const [taskId, task] of [...pending.entries()]) {
      const blockedDependency = task.dependencies.find((dependency) => results[dependency] && results[dependency].status !== 'VERIFIED')
      if (blockedDependency) {
        results[taskId] = { status: 'BLOCKED', task_id: taskId, blocker: `dependency ${blockedDependency} was not verified` }
        pending.delete(taskId)
      }
    }
    const ready = [...pending.values()].filter((task) => task.dependencies.every((dependency) => results[dependency]?.status === 'VERIFIED'))
    if (!ready.length) break
    const batch = ready.length === 1
      ? [await runTask(ready[0])]
      : await parallel(ready.map((task) => () => runTask(task)))
    ready.forEach((task, index) => {
      results[task.id] = batch[index]
      pending.delete(task.id)
    })
  }
  for (const taskId of pending.keys()) {
    results[taskId] = { status: 'BLOCKED', task_id: taskId, blocker: 'no runnable dependency path remained' }
  }
  return results
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
      'Do not treat pre-existing worktree changes as workflow failures.',
      'Do not require a globally clean worktree unless the plan recorded a clean pre-workflow baseline.',
    ],
    allowed_paths: allAllowedPaths,
    permission: buildTasks.length ? 'build' : 'review',
    acceptance_checks: PLAN.final_gate.acceptance_checks,
    routes: PLAN.final_gate.routes,
    verifier_routes: PLAN.final_gate.verifier_routes,
  }
  const seenFailurePackets = new Set()
  let cycle = 0
  let verifierAttempt = 0
  while (true) {
    cycle += 1
    const gates = []
    for (const verifierRoute of PLAN.final_gate.verifier_routes) {
      verifierAttempt += 1
      const gate = await runVerifier(
        verifierRoute,
        finalTask,
        'combined-workflow',
        { status: 'COMPLETED', summary: JSON.stringify(taskResults), changed_files: [], checks: [], error: null },
        verifierAttempt,
        true,
      )
      gates.push({ route: verifierRoute, result: gate })
      if (gate && gate.verdict === 'PASS') {
        return { status: 'VERIFIED', gate, gates, cycles: cycle }
      }
    }

    const failurePacket = gates
      .map(({ route, result }) => `${route}:${result?.failure_packet || result?.summary || 'missing final gate result'}`)
      .join('\n')
    const failureFingerprint = failurePacket.toLowerCase().replace(/\s+/g, ' ').trim()
    if (seenFailurePackets.has(failureFingerprint)) {
      return {
        status: 'BLOCKED',
        blocker: 'the complete final-gate verifier ladder repeated the same failure after a verified repair',
        gates,
        cycles: cycle,
      }
    }
    seenFailurePackets.add(failureFingerprint)

    if (!buildTasks.length) {
      return {
        status: 'BLOCKED',
        blocker: 'read-only workflow failed the complete final-gate verifier ladder; automatic repair is forbidden',
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
const taskResults = await runTaskGraph()
const blockedTasks = Object.values(taskResults).filter((result) => result.status !== 'VERIFIED')
if (blockedTasks.length) {
  return { status: 'BLOCKED', workflow_id: PLAN.workflow_id, tasks: taskResults, blocked: blockedTasks }
}

phase('Final gate')
const finalGate = await runFinalGate(taskResults)
return { status: finalGate.status, workflow_id: PLAN.workflow_id, tasks: taskResults, final_gate: finalGate }
