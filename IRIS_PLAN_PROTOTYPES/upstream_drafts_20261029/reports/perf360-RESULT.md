# perf360 upstream reports: RESULT

Folder: `/tmp/claude-1000/-home-nabil-Git-glue-solar/69a1ec2a-a15b-4ef0-a5e7-b33024cca348/scratchpad/updrafts/reports/`
(below, paths are relative to it). From the #360 profile, REPORT (c). Nothing was pushed, posted or opened.

## Summary

| # | Report file | Goes to | Release run | Main |
| --- | --- | --- | --- | --- |
| c1 | `perf360-filelock.md` | new filelock issue, with a sketch | 4.2.4: deepcopy 1.76x (nested) and 1.66x (astropy model) slower after `import filelock`; a do-nothing hook 1.44x and 1.39x; 81 ns per event | 715a8de, read from source: the same hook, installed at import (`_api.py:1978`) |
| c2 | `perf360-ndcube.md` | new ndcube issue (Performance template), offers the PR | 2.4.3: `cube[0]` 0.72 ms with an NDMeta of a 412-card header, 0.016 ms with a dict meta; prototype 0.05 ms, same meta; ndcube suite 610 passed both ways | f4d58976, read from source: `meta.py` identical, deepcopy at `:370` |
| c3 | `perf360-gwcs.md` | new gwcs issue, offers the PR | 1.0.3: `WCS(model, ...)` 0.73 ms, steps form 0.001 ms, `model.copy()` 0.72 ms; same world coordinates | 7f7e664, read from source: still `forward_transform.copy()` (`_pipeline.py:406`) |
| c4 | `perf360-astropy.md` | astropy PR (a few lines in `card.py`), Ref #12504 | 8.0.2: 824 config reads, 2.51 ms per 412-card parse and read; prototype 61 reads, 1.54 ms (-39%), equal values; snapshot 1.55 ms; io.fits tests unchanged | d3ad3b66f2, read from source: `card.py` identical |

Each file has where it goes, the title, the body to paste (standalone reproducer, its output, the suggestion, and a
diff sketch for c1, c2 and c4), and notes for you that are not to paste.

Found on the way:
- **c4 has an open issue: #12504** ("ConfigNamespace is slow", 2021, names io.fits header parsing). The fix there, #17461
  (a value cache on the ConfigItem), was reverted in #18144 because it broke `reload_config` (#18138). So c4 is a
  narrow io.fits PR that leaves the config system alone. It reads the config only where it can change the result:
  `isinstance(value, str)` before `strip_header_whitespace`, and no RVKC config read for a card image without `": "`.
- **"Read the config once per header parse" would break a test:** `test_header_strip_whitespace` changes
  `strip_header_whitespace` with `set_temp` after building the header and expects the values to change. The
  snapshot is kept only as the ceiling. The prototype comes close to it: on real data (irispy #360 `read_files` of
  1230 files in one call) stock 20.5 / 20.4 s, prototype 17.6 / 17.6 s, snapshot 17.0 / 16.8 s.
- **filelock's hook is mostly the cost of any Python hook:** a do-nothing Python hook takes 1.44x where filelock's
  takes 1.76x. A cheaper hook body would not help much. So the suggestion is to install the hook with the first lock
  (in the three lock metaclasses and `AsyncReadWriteLock.__init__`), not at import. The hook came with #652
  (3.30.0); #747 (4.0.3) already skips it on CPython 3.10 and 3.11, where the at-fork callbacks still work.
- **ndcube:** `copy.copy(NDMeta)` today shares `_axes` with the original (an `add` on the copy shows up in the
  original's axes, checked on 2.4.3). The sketch's `NDMeta.__copy__` fixes that too. Related open issues: #815 (copy
  or deepcopy in `rebin`) and your #989.
- **gwcs:** the list-of-steps form shares the caller's model, and setting the WCS's `bounding_box` reaches it. That
  is why the body proposes an opt-in `copy=False` (or docs), not dropping the copy.

Not done:
- **No main was run.** The session's permission classifier refused to run the filelock clone's code ("Code from
  External"). The other clones were not tried, as that is the same action (and astropy also needs a build). Each draft says main was read from
  source and what is unchanged. Before posting, you may run each script with `PYTHONPATH=clones/perf360-<name>`
  (`src` for filelock). A build of filelock, gwcs or ndcube generates its version file (`version.py` or `_version.py`),
  which a source checkout lacks.
- The filelock sketch was not run, and filelock's tests were not run on it (the same refusal). Only ruff (0.16.1,
  filelock's config) was run on the four edited files. From the source, one test fails with it:
  `test_import_adds_audit_hook_only_where_settrace_survives_it` asserts that `import filelock` adds the hook; the
  draft says so.
- The REPORT's irispy and glue-solar figures used in the bodies were not re-run: 15% of the load in filelock's hook,
  85,000 hook calls per file, 76.3 → 67.8 ms per file, 11,070 slices, 1.3 of 2.3 ms, 17.7% in the gwcs copy. c4's
  real-data line is new.

After the check (F1-F4): the filelock sketch now also installs the hook in `AsyncReadWriteLock.__init__`, which
registers itself and enters a fork transition before it builds its `ReadWriteLock`; the filelock body names the test
the sketch breaks; the astropy header cites `test_header.py:2369` (was 2389); the gwcs header no longer calls #422
(slicing) a copy issue. No reproducer changed, so none was rerun; ruff was rerun on the new sketch.

How things ran: env iris-plan-latest-1028 (Python 3.13.16, filelock 4.2.4, ndcube 2.4.3, gwcs 1.0.3, astropy 8.0.2,
numpy 2.5.4), `python -I -B scripts/perf360_<name>.py` under `systemd-run --user --scope -p MemoryMax=24G
-p MemorySwapMax=0`, with HOME, XDG_CONFIG_HOME and XDG_CACHE_HOME in a probe folder, `QT_QPA_PLATFORM=offscreen`,
`MPLBACKEND=agg`. The probe folder (`perf360_probe/`) is removed. c4's real-data check used iris-plan-irispy-360.
Load average 0.2-4.8 (another agent was running). Peaks: c1 115 MB per interpreter, c2 312 MB, c3 147 MB, c4
61 MB, the c4 real-data read 1.13 GB, the ndcube suite 1.4 GB, astropy's io.fits tests 8.7 GB. Nothing hit the cap.

Files: drafts `perf360-{filelock,ndcube,gwcs,astropy}.md`; reproducers `scripts/perf360_{filelock,ndcube,gwcs,
astropy}.py`; pytest plugins for the prototypes `scripts/perf360_{ndcube,astropy}_plugin.py`; the real-data check
`scripts/perf360_astropy_irisread.py`; outputs `out/perf360_*_rel.txt`, `out/perf360_*_tests_{stock,proto}.txt`,
`out/perf360_astropy_irisread.txt`; diffs to apply `out/perf360_{filelock,ndcube,astropy}.diff` (against each main).
Clones (kept): `clones/perf360-filelock` 715a8de, `clones/perf360-ndcube` f4d58976, `clones/perf360-gwcs` 7f7e664
(it carries every `pr/*` branch, so it was slow to clone), `clones/perf360-astropy` d3ad3b66f2 (blobless).

Cleanup: the xdist workers ignored `-B` and wrote 62 pytest `*.cpython-313-pytest-9.2.0.pyc` files into
iris-plan-latest-1028's `ndcube/` and `astropy/` (all made between 12:12 and 12:18). They were removed by exact
path; the `__pycache__` folders' mtimes changed. To re-run the test checks without that, add
`PYTHONDONTWRITEBYTECODE=1`.
