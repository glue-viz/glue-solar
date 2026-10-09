export const meta = {
  name: 'plan-item',
  description: 'One glue-solar plan item: Opus implements, Fable reviews, Opus applies confirmed fixes (3 agents)',
  phases: [
    { title: 'Implement', detail: 'Opus: check glue first (D18), design, implement, test, commit locally' },
    { title: 'Review', detail: 'Fable reviews and verifies its findings', model: 'fable' },
    { title: 'Fix', detail: 'Opus applies confirmed fixes' },
  ],
}

const KEY = args.key
const W = `/Users/nabil/Git/glue-solar-${KEY}`
const S = `${args.scratch}/items/${KEY}`  // args.scratch: the session scratchpad

const RULES = `
Repo and environment rules (must follow):
- Work only in the worktree ${W} (branch ${KEY} from origin/main). Read-only: ~/Git/glue-solar (plan branch: IRIS_GLUE_GAP_PLAN.md, GLUE_SPEED.md, IRIS_PLAN_PROTOTYPES/). No push, no PRs, no other repos. Stage named files only (never git add -A). Commit messages: one plain imperative sentence like the repo's history (no prefixes, no attribution or trailers, no issue refs).
- glue-solar depends on irispy git main (D47) and Python >= 3.13. Envs: /Users/nabil/mamba/envs/iris-plan-main (glue-core 1.27.0, glue-qt 0.4.2, irispy main d0e7764) and iris-plan-floor-main (astropy 8.0.0, ndcube 2.4.0); library sources under /Users/nabil/mamba/envs/iris-plan-main/lib/python3.13/site-packages. Tests from the worktree: P=/Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES; env HOME="$(mktemp -d)" PYTHONPATH=$P /Users/nabil/mamba/envs/iris-plan-main/bin/python -B $P/run_checks.py "$PWD:$P" glue_solar [-k expr] [--remote-data=any]; the full suite with --remote-data=any must pass in BOTH envs. Lint: /Users/nabil/mamba/envs/ruff-0161/bin/ruff check glue_solar (ruff format --check already fails on 16 files on main; keep new code formatted).
- Docs: /Users/nabil/mamba/envs/iris-plan-docs/bin/python -m setuptools_scm --root ${W} --config ${W}/pyproject.toml --force-write-version-files ; then from a scratch dir: env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen MPLBACKEND=agg PYTHONPATH=${W} /Users/nabil/mamba/envs/iris-plan-docs/bin/sphinx-build -W --keep-going -b html ${W}/docs <scratch>/html (warning-free).
- Headless runs: isolated HOME, QT_QPA_PLATFORM=offscreen, MPLBACKEND=agg; probes in ${S}/<label>/, never with a checkout as cwd. Full-size data under /Users/nabil/DATA/IRIS (real home via pwd.getpwuid(os.getuid()).pw_dir).
- D18: before building anything, check glue-core and glue-qt (released and main on GitHub) for the feature, and prefer configuring, defaulting, documenting or calling glue's own API. glue-solar tests cover the GUI/glue side only, never irispy's numerics; real-data tests are @pytest.mark.remote_data on LM-SAL/irispy-data release assets via the irispy_data fixture (glue_solar/conftest.py IRISPY_DATA_HASHES), never local paths or committed data; new irispy-data assets need the user.
- Keep it the smallest change that meets the done-when; match the surrounding style and comment density (terse docstring prose as in glue_solar/tools.py, quicklook.py, sources/moments.py); docs updated in the same PR; NO changelog fragment (added once the PR number exists).
- Any choice the user should make: take the lowest-risk default and mark it PROVISIONAL in your report with the alternative.`

const SPEC = `
Item: ${args.item}
Plan context (the item's work package, its notes, the decisions it needs): ${S}/PLAN.md — read it all.
${args.extra ?? ''}`

phase('Implement')
const impl = await agent(`${RULES}\n\n${SPEC}\n\nTask: implement the item: code, tests, docs. Measure the done-when on the named data (full size where named; report numbers). Run the full suite in both envs, ruff and the docs build until all pass. Commit as one commit with a message naming the change. Return: the SHA, a short summary, PROVISIONAL choices with alternatives, deviations from the plan text with reasons, the done-when measurements, and pass counts for both envs.`,
  { label: `implement:${KEY}`, phase: 'Implement' })

const FINDINGS = {
  type: 'object',
  properties: {
    verdict: { type: 'string' },
    tests_run: { type: 'string' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['bug', 'spec', 'test-gap', 'docs', 'style'] },
      location: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' },
    }, required: ['id', 'severity', 'location', 'problem', 'evidence', 'fix'] } },
  },
  required: ['verdict', 'tests_run', 'findings'],
}

phase('Review')
const review = await agent(`${RULES}\n\n${SPEC}\n\nTask: review the commit(s) on branch ${KEY} (git -C ${W} diff origin/main...HEAD) as a demanding senior reviewer; READ-ONLY on the worktree (mutation checks in a detached worktree under ${S}/review/, removed after). Check: the done-when (re-measure yourself); D18 (did glue already offer this?); correctness and edge cases; interactions with the coordinator, quicklook, existing tools and keys; tests fail when the feature is broken; docs accuracy; concision of code, comments and docs; over-engineering. Verify every finding yourself; report only real ones. Implementer's report:\n${impl ?? '(implementer failed)'}`,
  { label: `review:${KEY}`, phase: 'Review', model: 'fable', schema: FINDINGS })

const real = (review?.findings ?? []).filter(f => f.severity !== 'style' || /unused|dead|duplicate|stale|verbose|concis|leak|format|line-length|characters/i.test(f.problem))
log(`${KEY} review: ${review?.findings?.length ?? 0} findings, ${real.length} to fix`)
let fix = null
if (real.length) {
  phase('Fix')
  fix = await agent(`${RULES}\n\n${SPEC}\n\nTask: apply these verified review findings, each minimal; skip any that prove wrong and say why. Re-run affected tests, the full suite in both envs, ruff and docs. Commit as one commit "Address the review" (named files only). Return the SHA, the change per finding id, and final pass counts.\n\nFindings:\n${JSON.stringify(real, null, 2)}`,
    { label: `fix:${KEY}`, phase: 'Fix' })
}
return { key: KEY, impl, review, fix }
