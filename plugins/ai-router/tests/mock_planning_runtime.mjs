import fs from 'node:fs'

const [scriptPath, scenario = 'pass'] = process.argv.slice(2)
if (!scriptPath) throw new Error('script path is required')

const source = fs.readFileSync(scriptPath, 'utf8').replace('export const meta =', 'const meta =')
const specMatch = source.match(/const SPEC = (.+)\nconst DELEGATE_TOOL/)
if (!specMatch) throw new Error('planning spec was not embedded')
const planningSpec = JSON.parse(specMatch[1])
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const labels = []
const phases = []
let active = 0
let maxActive = 0
let criticCalls = 0

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
  if (label.startsWith('discover:')) {
    return {
      summary: 'Bounded discovery complete',
      evidence: ['mock evidence'],
      uncertainties: [],
      material_questions: [],
    }
  }
  if (label.startsWith('planner:')) {
    const routineCorrection = scenario === 'routine-critic-correction'
    return {
      status: 'DRAFT_READY',
      risk_level: routineCorrection ? 'routine' : 'frontier',
      architecture_envelope: {
        boundaries: ['mock boundary'],
        invariants: ['mock invariant'],
        milestones: ['mock milestone'],
      },
      tasks: [{
        id: 'implementation',
        objective: 'Implement the bounded result',
        expected_artifact: 'Verified implementation',
        dependencies: [],
        non_goals: ['No unrelated work'],
        allowed_paths: ['src', 'tests'],
        permission: 'build',
        complexity: routineCorrection ? 'routine' : 'frontier',
        acceptance_checks: ['The bounded behavior works'],
        targeted_commands: ['true'],
        affected_commands: ['true'],
      }],
      final_acceptance_checks: ['Complete regression is green'],
      regression_commands: ['true'],
      material_questions: [],
      assumptions: [],
      blocker: null,
    }
  }
  if (label.startsWith('grill:')) {
    return {
      verdict: 'PASS',
      blocking_findings: [],
      counterexamples: [],
      invalid_assumptions: [],
      missing_tests: [],
      scope_rollback_concerns: [],
      material_questions: [],
      recommended_changes: [],
    }
  }
  if (label.startsWith('critic:')) {
    criticCalls += 1
    if (
      (scenario === 'critic-question' || scenario === 'routine-critic-correction') &&
      criticCalls === 1
    ) {
      return {
        verdict: 'CHALLENGE',
        findings: [],
        material_questions: ['Should the planner correct this calculable check detail?'],
        summary: 'This is a plan correction, not a user decision',
      }
    }
    return {
      verdict: 'PASS',
      findings: [],
      material_questions: [],
      summary: 'Independent critic passed',
    }
  }
  throw new Error(`unexpected planning label: ${label}`)
}

async function parallel(functions) {
  return Promise.all(functions.map((fn) => fn()))
}

function phase(name) {
  phases.push(name)
}

const run = new AsyncFunction('agent', 'parallel', 'phase', source)
const result = await run(agent, parallel, phase)
process.stdout.write(JSON.stringify({
  result,
  labels,
  phases,
  max_active: maxActive,
  critic_calls: criticCalls,
}))
