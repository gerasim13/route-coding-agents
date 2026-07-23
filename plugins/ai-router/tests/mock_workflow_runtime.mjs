import fs from 'node:fs'

const [scriptPath, scenario = 'success'] = process.argv.slice(2)
if (!scriptPath) throw new Error('script path is required')

const source = fs.readFileSync(scriptPath, 'utf8').replace('export const meta =', 'const meta =')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const labels = []
const labelCounts = new Map()
let active = 0
let maxActive = 0

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function agent(_prompt, options = {}) {
  const label = options.label || 'unlabeled'
  labels.push(label)
  labelCounts.set(label, (labelCounts.get(label) || 0) + 1)
  active += 1
  maxActive = Math.max(maxActive, active)
  await delay(8)
  active -= 1

  if (label.startsWith('replan:')) {
    return {
      can_progress: true,
      revised_objective: 'Use a materially different approach',
      approach_fingerprint: `approach-${labels.length}`,
      rationale: 'Mock frontier replan',
      additional_checks: [],
      blocker: null,
    }
  }
  if (label.startsWith('check:')) {
    const targetedFailure =
      (scenario === 'check-fail-once' || scenario === 'out-of-scope') &&
      label.includes(':implementation:targeted:') &&
      labels.filter((item) => item.startsWith('check:implementation:targeted:')).length === 1
    const flaky =
      scenario === 'flaky-then-repair' &&
      label.includes(':implementation:targeted:') &&
      labels.filter((item) => item.startsWith('check:implementation:targeted:')).length === 1
    const regressionFailure = scenario === 'regression-never-green' && label.includes(':regression:')
    const status = flaky ? 'SUSPECTED_FLAKY' : (targetedFailure || regressionFailure) ? 'FAIL' : 'PASS'
    return {
      status,
      level: label.includes(':regression:') ? 'regression' : label.includes(':affected:') ? 'affected' : 'targeted',
      command: 'mock-check',
      attempts: status === 'PASS' ? 1 : 2,
      rerun_performed: status !== 'PASS',
      return_code: status === 'PASS' ? 0 : 1,
      duration_ms: 8,
      workspace_changed: false,
      failure_signature: status === 'PASS' ? null : 'mock-failure-signature',
      stdout_excerpt: '',
      stderr_excerpt: status === 'PASS' ? '' : 'mock failure',
      log_path: '/tmp/mock-check.log',
      zero_tolerance: true,
    }
  }
  if (label.startsWith('diagnose:')) {
    const outOfScope = scenario === 'out-of-scope'
    return {
      status: 'DIAGNOSED',
      cause: outOfScope ? 'Fix requires another module' : 'Mock root cause',
      confidence: 'high',
      suspected_paths: outOfScope ? ['outside/contract'] : ['src/mock'],
      summary: 'Mock strong diagnosis',
      failure_signature: 'mock-failure-signature',
      recommended_fix: 'Apply a bounded mock repair',
      repair_tier: 'strong',
      scope_status: outOfScope ? 'OUT_OF_SCOPE' : 'IN_SCOPE',
      blocker: null,
    }
  }
  if (label.startsWith('verifier:') || label.startsWith('test-intent-verifier:') || label.startsWith('final-gate:')) {
    const shouldFail =
      (scenario === 'escalate-once' && label.includes(':implementation:codex-luna:a1')) ||
      (scenario === 'final-gate-escalate' && label.startsWith('final-gate:') && label.includes(':codex-terra:')) ||
      (scenario === 'final-gate-fail-all' && label.startsWith('final-gate:'))
    return {
      verdict: shouldFail ? 'FAIL' : 'PASS',
      summary: shouldFail ? 'Mock verifier rejected the first route' : 'Mock verification passed',
      findings: shouldFail ? ['first route failed'] : [],
      checks: ['mock-check'],
      failure_packet: shouldFail ? 'exact mock failure packet' : '',
    }
  }
  return {
    status: 'COMPLETED',
    summary: 'Mock worker completed',
    changed_files: scenario === 'test-intent' ? ['tests/mock.test.js'] : ['src/mock'],
    checks: ['mock-check'],
    error: null,
  }
}

async function parallel(functions) {
  return Promise.all(functions.map((fn) => fn()))
}

function phase(_name) {}

const run = new AsyncFunction('agent', 'parallel', 'phase', source)
const result = await run(agent, parallel, phase)
process.stdout.write(JSON.stringify({ result, labels, max_active: maxActive }))
