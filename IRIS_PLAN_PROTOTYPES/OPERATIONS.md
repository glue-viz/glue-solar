# Operating notes

Versions, environments, data, worktrees, archives and tooling for the plan (`IRIS_GLUE_GAP_PLAN.md`), by machine.
The plan keeps the rules and open items; this file keeps what a session needs to run them. Keep it true: say when
something was removed rather than leaving a dead path.

## Versions

glue-core 1.28.0 (glue-solar's floor since #372) and glue-qt 0.4.2 (all fixes glue-solar needs). irispy from git
main (D47), pinned at f058705 (#347, D91) while irispy's gwcs port (#360) is in progress; irispy's last release is
0.9.1 and the user is still changing its API. Since D104 every dependency floor is its latest release (#382, #388;
reproject by #391): the list is `pyproject.toml` on main. The user's draft irispy #182 (gWCS rasters, D14) was closed
unmerged on 2026-10-19.

## Linux machine (`fedora`, x86-64, 188 GB RAM, 32 cores), as recorded on 2026-10-29

The working machine since 2026-10-20. Envs in `~/.local/share/mamba/envs` by `/opt/micromamba/micromamba`:

- `iris-plan-latest-1028` (the latest releases, Python 3.13: astropy 8.0.2, ndcube 2.4.3, sunpy 8.0.1, dkist 1.18.1,
  asdf 6.0.0, echo 0.16.0, gwcs 1.0.3, glue-core 1.28.0, glue-qt 0.4.2 and irispy f058705 by pip `--no-deps`, PyQt6
  6.12.0 on Qt 6.12.0, pytest 9.2.0): every PR's env; `iris-plan-docs-latest` for the docs build;
  `iris-plan-latest-irispy` (irispy #360's head 17900bd) and `iris-plan-irispy-360` (5d662b1) for `follow-irispy-main`,
  rebuilt when #360 merges. A clone of an env drops its pip packages: reinstall them.
- Removed on 2026-10-29 (user: prune what is unused): `iris-plan-latest`, the `-f058`, `-f058-g128` and `-34ff`
  baseline, floor and docs envs, and the scratch `iris-plan-qt6-802-gwcs`.
- Every workflow probe and pytest runs under `systemd-run --user --scope -p MemoryMax=24G -p MemorySwapMax=0`
  (2026-10-23: systemd-oomd killed a whole terminal at 104 GB).

Data: IRIS in `~/DATA/IRIS` (sets differ from the Mac's; 3630104144 was on both), SST cubes in `~/DATA/SST` up to
135 GB, DKIST's complete datasets in `~/DATA/DKIST/<id>/` (each an ASDF and its FITS files: ViSP TXIPCV and VBI
LOQEPP, observed together; Cryo-NIRSP AIOMGG and NDFHBO of one observation; DL-NIRSP CARJML, a 108-tile mosaic; ViSP
CZKPML, 50 repeats of an 80-step raster, 32.7 GiB; YETNFH not downloaded), dkist's sample data in
`~/.local/share/dkist`; `/data` has 64 TB free.

Checkouts and worktrees: `~/Git/glue-solar-main`, a detached main checkout at c52fcc1, the survey's baseline (move it
for a new run); the five fix branches' worktrees `~/Git/glue-solar-<branch>`; irispy's drafts clone
`~/Git/irispy-drafts` (SSH remote: an HTTPS push hangs for credentials) with `~/Git/irispy-read-empty-rasters` (#301).

Texts and branches for the user: `~/Downloads/glue-solar-upstream/` (its README is the checklist: eleven fork
branches to open as PRs, the six rebased drafts, issue and comment texts, the irispy #360 handoff and benchmark, the
WCSLIB email in `wcslib/`); `~/Downloads/glue-solar-texts/` (the Linux survey steps, the earlier WCSLIB email text).

Session archive: `session_20261021.tar.gz` (session b6e23444, 2026-10-20 to 10-29, kept out of git by
`.git/info/exclude`): the Fable reviews of #330-#346 (`review/`), their fixes (`fix/`), the bug hunts' findings and
verdicts (`hunt/`), the survey's runner and raw lines (`survey/`), the workflow scripts (`workflows/`), the env recipe
(`make_envs.sh`), the DKIST profiles (`dkist-profile/`, `dkist-profile2/`), irispy #360's profile and benchmarks
(`perf360/`, `bench360b/`), the follow-irispy PR text and register row (`fix25/follow-batched/`) and the upstream
drafts (`updrafts/`), with RESTORE-20261021.md.

## Mac (`Nabils-MacBook-Pro`, Apple Silicon, 24 GB RAM), as of 2026-10-31

The plan's machine until 2026-10-20; since then the Linux machine runs the work and the Mac was pruned. Here now:

- `~/Git/glue-solar`, the plan checkout (branch `plan`); `~/Git/glue-solar-main`, a detached main checkout (96dffa2,
  #405, 2026-10-31; move it to origin/main before a run), the editable install of the Mac env; a worktree `~/Git/glue-solar-<branch>` per PR branch in flight.
- Env `iris-plan-latest-mac` in `~/mamba/envs` (2026-10-31; recipe `envbuild/build.sh` in the session scratchpad,
  kept in `IRIS_PLAN_PROTOTYPES/plan_tooling/make_env_mac.sh`): the latest conda-forge releases of main's
  dependencies, glue-qt 0.4.2 and irispy f058705 by pip `--no-deps`, main's `tests` and `docs` extras, ruff at the
  pre-commit's pin (0.16.1), and `~/Git/glue-solar-main` editable. Run tests with `run_checks.py` (the plan's
  Validation), which puts the worktree under test first on `PYTHONPATH`.
- The user's own checkouts, never touched: `~/Git/astropy`, `~/Git/irispy`, `~/Git/glue`, `~/Git/glue-qt`; the
  user's own envs `glue`, `glue-solar`, `irispy`, `sunpy`, `ndcube`, `wcsaxes` and the muse envs: not baselines.
- Removed before 2026-10-31 (the user, pruning): every `iris-plan-*` and `glue-solar-app-*` env and `ruff-0161`;
  `~/DATA/IRIS`, `~/DATA/SST` and the saturated flare files (`~/DATA` holds `muse_runs` only); the 2026-10-20 app
  build `~/Downloads/Glue Solar.dmg`; `~/Downloads/glue-solar-texts/`; the irispy and glue-qt worktrees. No
  `Glue Solar.app` is installed. So on the Mac: no full-size data (remote-data tests still fetch irispy-data's cutouts
  and dkist's sample data), no app check without a rebuild (`packaging/macos/build_app.sh`, D55), no SST or DKIST
  scale checks.
- Full-size data is on the user's external USB SSD, `/Volumes/PSSD4TB/DATA/` (exFAT through FSKit, 3.7 TB; read-only,
  never write there), when it is plugged in: `IRIS/` (45 GB: ten observations, the big stack
  `20150311_151947_3860107071` and `20150917_073915_3630104144` among them, plus `mosaics/` and `pipeline/`), `SST/`
  (284 GB: the 2022-05-12 cubes 3950, 4846 and 6302 at 13-15 GB, and the 2024-07-05 cubes 3950 and 8542 at 135 and
  129 GB), `DKIST/` (94 GB: AIOMGG, CARJML, CZKPML, LOQEPP, NDFHBO, TXIPCV), `MUSE/` and a CHIANTI database. It reads
  1.26 GB/s sequentially cold (2026-10-31), so it is a latency test for scattered reads, not a bandwidth one; the
  scan-step scripts (`scanstep_20261021/common.py`) take it as the Mac's SST root; the 2026-10-31 check is in
  GLUE_SPEED.md ('USB slow-I/O check on the Mac').
- `~/Library/Caches/glue-solar-checks/astropy` is `run_checks.py`'s kept astropy cache; `~/.glue/` is the user's.

Session archives on the Mac (local, excluded from git): `session_20261014.tar.gz`, `session_20261015.tar.gz` (a
superset: the choice review with the user's marks, decision notes, PR texts, `briefs/fitting.md`, the audits
`audit/` and `audit2/`, RESTORE.md), `session_20261017.tar.gz` (RULES.md for agents, `briefs/fit-tool/`, the
whole-code reviews `review/` and `review2/`, RESTORE-20261019.md) and `session_20261019.tar.gz` (session 6873e77f:
PR texts, probes, the WCSLIB email text, `tools/suites.sh`, RESTORE-20261020.md). Extract one into the session
scratchpad (`tar xzf <archive> -C <scratchpad>`) and set `PLAN_SCRATCH` to it for `ship_locked.sh`.

## Tooling and archives in git

`IRIS_PLAN_PROTOTYPES/`:

- `run_checks.py`: the test runner (isolated HOME and caches; see the plan's Validation).
- `plan_tooling/`: `ship_locked.sh KEY TITLE BODYFILE CTYPE CTEXT` (with `PLAN_SCRATCH` set; `CTYPE none` for no
  changelog) runs `pr_cycle.sh` (push, draft PR, changelog commit, CI, ready, merge) and `plan_record.py` (drops the
  merged item and sets 'Main is at'); `plan-item-workflow.js` for the Workflow tool (args key, item, extra, scratch:
  an Opus implementer, a Fable review, an Opus fix pass); `resolve_additive.py` for additive merge conflicts;
  `make_env_mac.sh` (the Mac env recipe). Never SendMessage an agent inside a running workflow: it starts a duplicate.
- `upstream_review_20261019/`: UPSTREAM_REVIEW.md's four section tables, brief and reproducers (`wp0-upstream`).
- `scale_checks/`: the Linux machine's survey scripts and their results (D100).
- `scanstep_20261021/`, `speed_20261020/`, `bigstack_20261020/`: the scan-step, speed and big-stack probes of
  2026-10-20/21 (GLUE_SPEED.md 'SST performance survey 2'; `wp10-follow-irispy`).
- Archives: `perf_survey_20261001.tar.gz`, `wcsaxes_study_20261001.tar.gz` and `wcsaxes_core_20261001.tar.gz` (the
  profiling survey, the WCSAxes tick study and the matplotlib-free WCSAxes core prototype, whose branches are on the
  user's astropy fork; UPSTREAM_REVIEW.md has the findings), `sst_stress_20261010.tar.gz` (the stress survey, D63),
  `saturation_sources_20261008.tar.gz` and `saturation_observation_20261008.tar.gz` (D49),
  `irispy_designs_20261009.tar.gz` (the designs for irispy's moments continuum, sit-and-stare -TAB WCS and NaN float
  rasters), `glue-solar-wiki-20261001.bundle` (D34). Prototypes and probes of merged work were removed on 2026-10-17
  and are in git at 7b0234a.

GLUE_SPEED.md beside the plan holds every performance finding (R1-R37, S13, SST1-SST13, the two surveys and the
WCSAxes study); UPSTREAM_REVIEW.md folded its upstream findings in on 2026-10-19.

## Worktree and git rules

`git -C <path>`, never `cd` then git; a long probe gets its own detached main checkout; remove a worktree only after
its PR is confirmed merged (`git merge-base --is-ancestor <head> origin/main`) and no run uses it; stage named files
only, never `git add -A`; never run Python with a checkout as the working directory.
