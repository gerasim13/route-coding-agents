import fs from 'node:fs'

const [scriptPath, scenario = 'pass'] = process.argv.slice(2)
if (!scriptPath) throw new Error('planning script path is required')

const source = fs.readFileSync(scriptPath, 'utf8').replace('export const meta =', 'const meta =')
const specMatch = source.match(/const SPEC = (.+)\nconst DELEGATE_TOOL/)
if (!specMatch) throw new Error('planning spec was not embedded')
const planningSpec = JSON.parse(specMatch[1])
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const labels = []
const prompts = []
const phases = []
let active = 0
let maxActive = 0
let criticCalls = 0
let architectureCalls = 0
let macroGrillCalls = 0
let tacticalCalls = 0

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function routed(value) {
  return { ...value, route_status: 'OK', route_error: null }
}

async function agent(prompt, options = {}) {
  const label = options.label || 'unlabeled'
  labels.push(label)
  prompts.push({ label, prompt })
  active += 1
  maxActive = Math.max(maxActive, active)
  await delay(8)
  active -= 1

  if (label.startsWith('discover:')) {
    return routed({
      summary: 'Bounded discovery complete',
      evidence: ['mock evidence'],
      uncertainties: [],
      material_questions: [],
    })
  }
  if (label.startsWith('architecture:')) {
    architectureCalls += 1
    const routine = planningSpec.initial_planning_tier === 'routine'
    return routed({
      status: 'DRAFT_READY',
      risk_level: routine ? 'routine' : 'strong',
      architecture_envelope: {
        boundaries: ['mock boundary'],
        owners: ['mock owner'],
        data_flow: ['mock flow'],
        lifecycles: ['mock lifecycle'],
        contracts: ['mock contract'],
        feasibility: ['mock proof'],
        milestones: ['mock milestone'],
      },
      material_questions: [],
      assumptions: [],
      blocker: null,
    })
  }
  if (label.startsWith('macro-grill:')) {
    macroGrillCalls += 1
    const challenge = scenario === 'macro-correction' && macroGrillCalls === 1
    const fatal = scenario === 'macro-fatal'
    return routed({
      verdict: challenge || fatal ? 'CHALLENGE' : 'PASS',
      finding_type: fatal
        ? 'ARCHITECTURE_FATAL'
        : challenge
          ? 'ARCHITECTURE_REPAIRABLE'
          : 'NONE',
      blocking_findings: fatal
        ? ['mock fatal ownership contradiction']
        : challenge
          ? ['mock repairable lifecycle contradiction']
          : [],
      counterexamples: [],
      invalid_assumptions: [],
      material_questions: [],
      recommended_changes: challenge ? ['repair mock lifecycle'] : [],
    })
  }
  if (label.startsWith('tactical-plan:')) {
    tacticalCalls += 1
    const routine = planningSpec.initial_planning_tier === 'routine'
    return routed({
      status: 'DRAFT_READY',
      risk_level: routine ? 'routine' : 'strong',
      execution_objective: 'Implement the bounded immediate wave',
      tasks: [{
        id: 'implementation',
        objective: 'Implement the bounded result',
        expected_artifact: 'Verified implementation',
        dependencies: [],
        non_goals: ['No unrelated work'],
        allowed_paths: ['src', 'tests'],
        permission: 'build',
        complexity: routine ? 'routine' : 'strong',
        acceptance_checks: ['The bounded behavior works'],
        targeted_commands: ['true'],
        affected_commands: ['true'],
      }],
      future_milestones: ['Recalibrate before the next milestone'],
      final_acceptance_checks: ['Complete regression is green'],
      regression_commands: ['true'],
      material_questions: [],
      assumptions: [],
      blocker: null,
    })
  }
  if (label.startsWith('tactical-critic:')) {
    criticCalls += 1
    const challenge =
      (scenario === 'critic-correction' || scenario === 'routine-critic-correction') &&
      criticCalls === 1
    const compiler = scenario === 'compiler-block'
    return routed({
      verdict: challenge || compiler ? 'CHALLENGE' : 'PASS',
      finding_type: compiler ? 'COMPILER' : challenge ? 'TACTICAL' : 'NONE',
      findings: compiler
        ? ['mock compiler cannot represent required checkpoint']
        : challenge
          ? ['mock immediate check needs correction']
          : [],
      material_questions: [],
      summary: compiler
        ? 'Compiler representation is impossible'
        : challenge
          ? 'One tactical correction is required'
          : 'Independent critic passed',
    })
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
  prompts,
  phases,
  max_active: maxActive,
  architecture_calls: architectureCalls,
  macro_grill_calls: macroGrillCalls,
  tactical_calls: tacticalCalls,
  critic_calls: criticCalls,
}))
