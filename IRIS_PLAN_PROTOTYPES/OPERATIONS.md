# Operating notes

Versions, environments, data, worktrees, archives and tooling for the plan (`IRIS_GLUE_GAP_PLAN.md`), by machine.
The plan keeps the rules and open items; this file keeps what a session needs to run them. Keep it true: say when
something was removed rather than leaving a dead path.

## Versions

glue-core 1.28.0 (glue-solar's floor since #372) and glue-qt 0.4.2 (all fixes glue-solar needs). irispy from git
main (D47), pinned at f058705 (#347, D91) while irispy's gwcs port (#368, which replaced #360 on 2026-11-13) is in
progress; irispy's last release is
0.9.1 and the user is still changing its API. Since D104 every dependency floor is its latest release (#382, #388;
reproject by #391): the list is `pyproject.toml` on main. The user's draft irispy #182 (gWCS rasters, D14) was closed
unmerged on 2026-10-19.

## Linux machine (`CachyOS-Work`, x86-64, 188 GB RAM, 32 cores), as of 2026-11-18

The working machine since 2026-10-20 (then `fedora`). It was reinstalled on 2026-11-09: the `iris-plan-*` envs, the
worktrees and everything under `/tmp` went, and `~/Git/glue-solar` is a fresh clone.

- Env: the user's `glue-solar` in `~/.local/share/mamba/envs` (micromamba at `~/.local/bin/micromamba`), which
  sessions may use but not change: Python 3.14.10 and the latest releases (astropy 8.0.3, numpy 2.5.5, ndcube 2.4.3,
  sunpy 8.0.1, dkist 1.19.0, echo 0.17.0, gwcs 1.0.3, glue-core 1.28.0, glue-qt 0.4.2, PyQt6 6.12.1, irispy f058705).
  A session upgrades it only on the user's word, as with the floors on 2026-11-19. It has
  no pytest, ruff or fiasco: install those with `pip install --target <scratch>/deps` and put that folder on the path. Its editable
  `glue_solar` points at `~/Git/glue-solar`, on `main`: put the checkout
  under test first on `PYTHONPATH`, as `run_checks.py` does, give a fresh worktree a `glue_solar/version.py`
  (the env has no setuptools-scm), and pass `-c <checkout>/pytest.ini`, which pytest does not find from a scratch
  folder. `~/.cache/glue-solar-checks/pooch` is the kept remote-data cache (1.6 GB).
- Every probe and pytest runs under `systemd-run --user --scope -p MemoryMax=24G -p MemorySwapMax=0`
  (2026-10-23: systemd-oomd killed a whole terminal at 104 GB).

Data: IRIS in `~/DATA/IRIS` (ten observations; sets differ from the Mac's; `/data_slow/IRIS` has eighteen, among
them 3660100039 and 3860258481, the follow-irispy PR's two with empty raster files), SST cubes in `~/DATA/SST`, DKIST's
complete datasets in `~/DATA/DKIST/<id>/` (each an ASDF and its FITS files: ViSP TXIPCV and VBI LOQEPP, observed
together; Cryo-NIRSP AIOMGG and NDFHBO of one observation; DL-NIRSP CARJML, a 108-tile mosaic; ViSP CZKPML, 50
repeats of an 80-step raster, 32.7 GiB); `/data_slow` has 63 TB free and `/data_fast` 950 GB (empty since
2026-11-16).

Checkouts and worktrees: `~/Git/glue-solar` (branch `main` since 2026-11-18: the user runs glue from it, so
fast-forward it after a merge); `~/Git/glue-solar-plan`, the plan checkout; `~/Git/glue-solar-main`, a detached main
checkout (move it for a new run);
`~/Git/glue-solar-follow-irispy-main`, the worktree of `follow-irispy-main` (on origin).

Local only, on no remote (lost if this disk is): `~/Downloads/glue-solar-local/`.

- `code/`: the reproducers and probes the upstream texts cite, four patch sketches on no fork
  (`glue-qt/pr75_followup.diff` and the `perf360_*.diff` files), and `git format-patch` copies of the eleven fork
  branches.
- `irispy/`: the #360 performance handoff, its diff and the c58ef2b benchmark.
- `wcslib-email.md`: the unsent email to WCSLIB's author.
- `review-20261112/`: the candidate fixes and probes of the review of the fork branches (UPSTREAM_TRACKER.md),
  and `glue-solar-main-before-rewrite-20261112.bundle`, main as it was when a rewrite was weighed (D114).
- `build-20261112/`: the probes, timing scripts and test runners behind the branches built on 2026-11-12, among
  them `glue-wcs/pr2595_tests.py`, the eleven tests of the closed glue #2595.
- `archives/`: `wcsaxes_study_20261001.tar.gz`, the WCSAxes tick study with the prototypes of the memo and batching
  PRs, which have no fork branch (`performance-detail.md` describes them), and `glue-solar-wiki-20261001.bundle`
  (D34).
- `code/glue-solar/link-probes-20261118/`: the headless real-data link probes of 2026-11-18 and their outputs
  (`iris-raster-sji/link_probe2.py` is the one to rerun: raster against slit-jaw images, per observation;
  `on-request-aia-sot-map/`, `dkist-sst/`). They import `glue_solar` only, need no pytest, and take the data
  folder as an absolute path, as the runs set a scratch HOME.
- `git-backup/`: from the backup made before the reinstall, `uv.lock` and `IRIS_PLAN_PROTOTYPES/` with the session
  archives `session_20261021.tar.gz` (the reviews of #330-#346, bug hunts, workflow scripts, `make_envs.sh`) and
  `session_20261021b.tar.gz` (177 MB: `fix25/follow-batched/` with the follow-irispy PR's body, `bench360b/`,
  `perf360/`, the DKIST profiles, `updrafts/`).

The irispy side's notes (`beta-notes/glue-solar-handoff.md`, `upstream-drafts/`) and its unpushed branches were in
`~/Downloads/git-backup-2026-11-09/irispy/` and `_unpushed-branches/irispy.bundle`, the user's own. That folder has
been in the desktop Trash since 2026-11-16 (`~/.local/share/Trash/files/git-backup-2026-11-09`): it goes when the
Trash is emptied.

### Linking checks by hand (2026-11-18)

What the headless probes could not see, on this machine's data; each says what to do and what to expect. Report a
failure by its number with the observation and the frame, step and scan shown.

1. **Time sync, a stack.** Browse `~/DATA/IRIS`, tick 3630104144's Mg II k 2796 and its four slit-jaw images, load
   with 'Open quicklook'. Click the map, then step time with D and F: every slit-jaw panel follows, its 'Frame time'
   within half a cadence or gray with NO MATCH, and with 'Raster overlays' on the white slit lies on the dark slit.
2. **A raster of few steps.** 3860107071 (4 steps, 1230 files: about a minute to load). On SJI 1400, in a late scan,
   click on the slit of the first step and of the last: the point moves there.
3. **Rolled.** 3620104038 (roll -45 degrees). Click a bright feature on a slit-jaw image: the map's crosshair is
   on the same feature. Draw a rectangle on the map: it shows turned on the slit-jaw images, over the same
   features.
4. **Negative steps.** 3400606077. Click left, then right, of the slit on a slit-jaw image: the map's point moves
   the same way on the Sun, and the overlays' slit lines lie on the dark slit in every frame.
5. **Sit-and-stare.** 3460259103. A click beside the slit takes the row level with it; D and F step exposures and
   the slit-jaw images follow.
6. **AIA and SOT panels.** Browse `~/DATA/IRIS`, tick all of 3860107071 and
   load: the Panels list has 'AIA' and 'SOT', unticked. Tick 'AIA 1600': its panel joins a row below, follows the
   time, marks the point, and with 'Raster overlays' on draws the four slits, about 3 AIA pixels apart; a click
   on a slit moves the point, one a few pixels beside them says 'outside raster FOV'. 'SOT Ca II H line' is gray
   with NO MATCH until the time reaches 16:02. A region drawn on the map shows on both without the menu action.
   'IRIS field of view' in the AIA panel's View menu draws a thin box, the raster's field, inside a square one, the
   slit-jaw image's, on the AIA and SOT panels; chosen again, they go.
   A map opened through File, Open as 'sunpy Map' still links only after 'Link helioprojective coordinates'.
7. **Session.** Save 6 with a region and a point as a session with relative paths, quit, open it: the links, the
   point, the region and the time master are back, and a slit-jaw click still moves the point.
8. **DKIST and SST.** Open `~/DATA/DKIST/TXIPCV` and `LOQEPP` and accept glue's offered links; 'Quicklook…' on the
   ViSP dataset shows the VBI panel with the slit and the point, and a click on a VBI tile moves the ViSP point.
   A region on the ViSP map shows on VBI as a band across the frames of those steps: by design, say if it reads
   as a fault. The two 2024-07-05 SST cubes, linked, show a region 1.7 to 1.9 arcsec off between them: the
   files' own pointing.

## Mac (`Nabils-MacBook-Pro`, Apple Silicon, 24 GB RAM), as of 2026-10-31

The Linux machine runs the full-size work; the Mac has:

- `~/Git/glue-solar`, the plan checkout (branch `plan`; rebuilt as one commit on 2026-11-11, so `git fetch` and
  `git reset --hard origin/plan` once); `~/Git/glue-solar-main`, a detached main checkout (96dffa2,
  #405, 2026-10-31; move it to origin/main before a run), the editable install of the Mac env; a worktree `~/Git/glue-solar-<branch>` per PR branch in flight.
- Env `iris-plan-latest-mac` in `~/mamba/envs` (2026-10-31; recipe `envbuild/build.sh` in the session scratchpad,
  kept in `IRIS_PLAN_PROTOTYPES/plan_tooling/make_env_mac.sh`): the latest conda-forge releases of main's
  dependencies, glue-qt 0.4.2 and irispy f058705 by pip `--no-deps`, main's `tests` and `docs` extras, ruff at the
  pre-commit's pin (0.16.1), and `~/Git/glue-solar-main` editable. Run tests with `run_checks.py` (the plan's
  Validation), which puts the worktree under test first on `PYTHONPATH`.
- The user's own checkouts, never touched: `~/Git/astropy`, `~/Git/irispy`, `~/Git/glue`, `~/Git/glue-qt`; the
  user's own envs `glue`, `glue-solar`, `irispy`, `sunpy`, `ndcube`, `wcsaxes` and the muse envs: not baselines.
- No `Glue Solar.app` is installed and no app build is on hand: an app check needs a rebuild first
  (`packaging/macos/build_app.sh`, D55). SST and DKIST scale checks run on the Linux machine.
- `~/Library/Caches/glue-solar-checks/{astropy,pooch}` are `run_checks.py`'s kept caches: astropy's IERS tables and the remote-data files (1.7 GB with DKIST's samples, hash-checked by pooch on use); `~/.glue/` is the user's.

Session archives on the Mac (local, excluded from git): `session_20261014.tar.gz`, `session_20261015.tar.gz` (a
superset: the choice review with the user's marks, decision notes, PR texts, `briefs/fitting.md`, the audits
`audit/` and `audit2/`, RESTORE.md), `session_20261017.tar.gz` (RULES.md for agents, `briefs/fit-tool/`, the
whole-code reviews `review/` and `review2/`, RESTORE-20261019.md) and `session_20261019.tar.gz` (session 6873e77f:
PR texts, probes, the WCSLIB email text, `tools/suites.sh`, RESTORE-20261020.md). Extract one into the session
scratchpad (`tar xzf <archive> -C <scratchpad>`) and set `PLAN_SCRATCH` to it for `ship_locked.sh`.

## Tooling in git

The plan branch is one commit on top of `main` (2026-11-11): after an edit, `git commit --amend`, and after main
moves, `git rebase origin/main`; either way `git push --force-with-lease origin plan`, and another machine's
checkout then takes `git fetch` and `git reset --hard origin/plan`. Nothing of the branch's earlier history is kept.

`IRIS_PLAN_PROTOTYPES/`:

- `run_checks.py`: the test runner (isolated HOME and caches; see the plan's Validation).
- `plan_tooling/`: `ship_locked.sh KEY TITLE BODYFILE CTYPE CTEXT` (with `PLAN_SCRATCH` set; `CTYPE none` for no
  changelog) runs `pr_cycle.sh` (push, draft PR, changelog commit, CI, ready, merge) and `plan_record.py` (drops the
  merged item and sets 'Main is at'; written for a plan branch of many commits, so check it before its next use);
  `plan-item-workflow.js` for the Workflow tool (args key, item, extra, scratch: an Opus implementer, a Fable
  review, an Opus fix pass); `resolve_additive.py` for additive merge conflicts; `make_env_mac.sh` (the Mac env
  recipe). Never SendMessage an agent inside a running workflow: it starts a duplicate.
- `upstream_review_20261019/`: UPSTREAM_REVIEW.md's four section tables, brief and reproducers (`wp0-upstream`).
  Every performance finding (R1-R37, S13, SST1-SST13) is a row there; `performance-detail.md` beside them keeps
  each one's approach and measurements (from GLUE_SPEED.md, checked against the installed releases on 2026-11-11).
- `upstream_drafts_20261029/`: the checklist of what to open or post upstream (its README), the PR bodies
  (`prs/`), the notes on the rebased glue drafts (`drafts/`), the issue and comment texts (`reports/`) and the
  WCSLIB -TAB inverse's measurements and reproducer (`wcslib/`).

## Worktree and git rules

`git -C <path>`, never `cd` then git; a long probe gets its own detached main checkout; remove a worktree only after
its PR is confirmed merged (`git merge-base --is-ancestor <head> origin/main`) and no run uses it; stage named files
only, never `git add -A`; never run Python with a checkout as the working directory.
