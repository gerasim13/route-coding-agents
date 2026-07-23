import fs from 'node:fs'

const [scriptPath, scenario = 'success'] = process.argv.slice(2)
if (!scriptPath) throw new Error('script path is required')

const source = fs.readFileSync(scriptPath, 'utf8').replace('export const meta =', 'const meta =')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const labels = []
let active = 0
let maxActive = 0

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function agent(_prompt, options = {}) {
  const label = options.label || 'unlabeled'
  labels.push(label)
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
  if (label.startsWith('verifier:') || label.startsWith('final-gate:')) {
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
    changed_files: ['src/mock'],
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
