# glue-solar: what to send upstream

The pull requests are in [UPSTREAM_TRACKER.md](../../UPSTREAM_TRACKER.md): one row per PR in the order to open them,
with its fork branch, what is left to do before opening, and its state. The title, body and notes of each built row
are in `prs/<repo>-<branch>.md` here, the body between `~~~~~` fences. To open one, go to
`https://github.com/<upstream>/compare/main...nabobalis:<repo>:<branch>?expand=1`.

This file lists the rest: the issues and comments to paste, the irispy handoff and the email. None has been posted
or sent, except the irispy #360 comment the tracker lists (checked 2026-11-12).

This folder holds the texts only: `prs/`, `drafts/`, `reports/` and `wcslib/` (without the email). The files it
names under `code/` and `irispy/`, and `wcslib/email.md` (there `wcslib-email.md`), are in
`/data_fast/glue-solar-local/` on the Linux machine and on no remote.

## Checklist

### A. Issues and comments to paste

Each file has the title (for a new issue), the section to paste ("Body (paste)" or "Comment (paste)"), and notes for
you that are not to paste.

- [ ] 1. **glue, new issue**: a linked layer's buffer over the whole view (#85).
  https://github.com/glue-viz/glue/issues/new/choose → `reports/glue-layer-buffer.md`
- [ ] 2. **glue#2574, comment**: world axes of data with more world than pixel axes (#77).
  https://github.com/glue-viz/glue/issues/2574 → `reports/glue-2574-comment.md`
- [ ] 3. **dkist, new issue**: `VaryingCelestialTransform`'s thread race and per-index rebuild.
  https://github.com/DKISTDC/dkist/issues/new/choose → `reports/dkist-varying-transform.md`
- [ ] 4. **dkist#226, comment**: whole-file reads. https://github.com/DKISTDC/dkist/issues/226 →
  `reports/dkist-226-comment.md`
- [ ] 5. **astropy#19174, comment**: 8 threads corrupt -TAB results. Optionally build astropy main first and add its
  output (the file's notes). https://github.com/astropy/astropy/issues/19174 → `reports/astropy-19174-comment.md`
- [ ] 6. **filelock, new issue** (perf360 c1): the fork-safety audit hook slows every deepcopy.
  https://github.com/tox-dev/filelock/issues/new → `reports/perf360-filelock.md`
- [ ] 7. **ndcube, new issue** (perf360 c2, Performance Suggestions template): slicing deep-copies the whole NDMeta. It
  goes with ndcube row 6 of the tracker (open it first, or skip it and open the PR alone). https://github.com/sunpy/ndcube/issues/new/choose →
  `reports/perf360-ndcube.md`
- [ ] 8. **gwcs, new issue** (perf360 c3): `WCS(model, ...)` always deep-copies the model.
  https://github.com/spacetelescope/gwcs/issues/new → `reports/perf360-gwcs.md`
- [ ] 9. **astropy, new issue** (a side finding of astropy row 2 of the tracker): `enable_record_valued_keyword_cards = False` does not
  apply to parsed card images. https://github.com/astropy/astropy/issues/new/choose →
  `reports/astropy-rvkc-setting-ignored.md` (reproducer `code/astropy/rvkc_off.py`). `reports/perf360-astropy.md` is
  the plan that row carries out: nothing to post from it.

`reports/perf360-RESULT.md` is the summary of items 6-9 (findings, what was not run).

### B. Handoff

- [ ] 10. **irispy #360**: give `irispy/irispy-360-performance-handoff.md` (it embeds its diff) and
  `irispy/irispy-360-proposals.diff` to the agent working on LM-SAL/irispy #360 on the other machine.
  https://github.com/LM-SAL/irispy/pull/360
  Update 2026-10-29: c58ef2b has a1-a8; `irispy/irispy-360-c58ef2b-benchmark.md` has the new numbers and what is left
  (a9-a11). Its one side effect, a one-file read's `orbital phase` meta big-endian, is fixed in 5d662b1 (0 differences,
  load 24.6 s, restore 24.3 s with glue-solar's batched reads).

### C. Email

- [ ] 11. **WCSLIB, email to Mark Calabretta** (`wp0-wcslib-tab-inverse`; a new draft of 2026-10-29, replacing the one
  on your Mac): `tabs2x()` on 2-D -TAB tables, slow and ambiguous where cells overlap. Attach
  `wcslib/tab_inverse_repro.py` and `wcslib/tab_inverse_repro.out`. → `wcslib/email.md` (`wcslib/README.md` has the
  measurements, the real-data runs and what is not verified). Checked: the tab.c lines it cites are WCSLIB 8.10's,
  the reproducer reruns to the same numbers (8.1 ms against 7.8 ms per sit-and-stare point, under load), and the 0.64°
  slit tilt is IRIS's own `PC3_2` (0.0113 on 4204700143, 0.0107 on 3400606077).

## Not in this folder

- Nothing pending: every item is in this folder.

## Check before posting

- **What was not run:** astropy main for the #19174 comment (described from source; the notes say how to build and
  add it); main of filelock, ndcube, gwcs and astropy for perf360 (read from source); the filelock sketch and its
  tests; the 51.5 s DKIST figure in `perf-discover-links` and the ViSP figures in the dkist#226 comment (earlier
  measurements); ARM for dkist.
- **Local paths:** no PR body or paste section names a local scratch path. They appear only in the files' notes for
  you and headers (e.g. `scratchpad/fix13/...`, drafts these replace), in `code/run.sh` (this machine's env and the
  scratch folder), and in `code/astropy/perf360_astropy_irisread.py` (reads `/home/nabil/DATA/IRIS/...`). Several
  probes import `glue_solar`.

## Folder

- `prs/`: one file per built PR, `<repo>-<branch>.md`: repo, fork branch and head, label, title, the body as drafted
  (between `~~~~~` fences), and notes on what to do or decide. `close-2595.md` is the comment for the closed #2595.
- `drafts/`: notes on the two parked glue drafts, `glue-<n>.md`.
- `reports/`: the issue and comment texts, copied as they are.
- `code/<project>/`: reproducers and probes the texts and results name. `<branch>.patch` is `git format-patch` of
  each pushed branch against upstream main, as a fallback (`git am`). `code/glue-qt/pr75_followup.diff` is #75's follow-up, and the
  `perf360_*.diff` files are the sketches the perf360 texts show. `code/run.sh` is the reports' runner, with this
  machine's paths. The scripts are plain Python and run without it.
- `irispy/`: the irispy #360 handoff and its diff.
