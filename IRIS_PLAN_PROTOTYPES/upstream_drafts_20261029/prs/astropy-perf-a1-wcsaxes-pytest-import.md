# wcsaxes: import pytest only when matplotlib is missing

- Upstream: astropy/astropy (branch is one commit on main 7732926be)
- Fork branch: `nabobalis:perf-a1-wcsaxes-pytest-import` at `6ed1b6f07d5fefd607fdc555c5bfed69fe1890bb` (existing name: force-push)
- Changelog fragment to rename: `docs/changes/visualization/PLACEHOLDER.perf.rst` to `<PR number>.perf.rst`

## Body

~~~~~markdown
### Description

This pull request is to address `import astropy.visualization.wcsaxes` importing `pytest` in every process where `pytest` is installed. The package's `__init__.py` calls `pytest.importorskip("matplotlib")` so that test collection skips the package when matplotlib is missing. With matplotlib installed that call does nothing, but `pytest` is slow to import.

The change tries `import matplotlib` first and falls back to `pytest.importorskip` only if that fails, the approach suggested in the review of #10302 (closed unmerged). With matplotlib missing nothing changes: the import still raises `Skipped` where pytest is installed and `ModuleNotFoundError` where it is not.

Importing `astropy.visualization.wcsaxes` with `matplotlib`, `astropy.wcs` and `astropy.coordinates` already imported takes 83 ms instead of 111 ms (median of 15 fresh processes, Python 3.14, pytest 9.2). There is no saving where pytest is not installed.

The new `test_import_does_not_import_pytest` runs the import in a subprocess and fails without the change.

Ref #10302

### AI Disclosure
Written with Claude Code (Anthropic); model and version: **[OWNER TO FILL: model name and version, not recorded]**. Claude Code wrote the code change, the test, the changelog fragment, the commit message and this description, and ran the tests and the import timings. **[OWNER TO ADD: one line on your own review.]**

- [ ] I certify that I am human and that I take full responsibility for this pull request including all interactions with reviewers.

### Merge method
- [ ] By checking this box, the PR author has requested that maintainers do **NOT** use the "Squash and Merge" button. Maintainers should respect this when possible; however, the final decision is at the discretion of the maintainer that merges the PR.
~~~~~

## Notes for the owner (not to paste)

- Blanks to fill in the AI Disclosure: the model name and version (not recorded anywhere), and one line on your own review.
- The certification box is left unticked on purpose: you must tick it yourself. The Merge method box is optional.
- The template's `Fixes #` line is removed, as the PR closes no issue; it says `Ref #10302`.
- #10302 is a closed, unmerged PR from 2020 ("Speed up wcsaxes import by avoiding unnecessary pytest import"). A maintainer suggested exactly this approach in a comment there. The body cites it without an @-mention so nobody is pinged.
- astropy's AI policy also requires that you engage with reviewers yourself and can explain every change.
- Changed from the fork branch: the fragment is added (`perf` is a valid type in a sub-directory per `docs/changes/README.rst`, and the saving is measurable through a public import), and the commit message's measurement now reads "from 111 ms to 83 ms, median of 15 fresh processes on Python 3.14 with pytest 9.2", measured twice in this build. It said 150 to 108 ms on Python 3.13, which could not be rerun.
- Run: `astropy/visualization/wcsaxes/tests/test_misc.py`, 50 passed, 3 skipped (TeX unavailable), 1 xfailed. With upstream's `__init__.py`: 1 failed, 49 passed, 3 skipped, 1 xfailed: `test_import_does_not_import_pytest`, `CalledProcessError`, with the subprocess's `assert 'pytest' not in sys.modules` raising `AssertionError`.
- Run: with matplotlib blocked, the import raises `Skipped` where pytest is installed and `ModuleNotFoundError` where it is not, the same before and after.
- Run: the import timing, two rounds of 15 fresh processes each way: medians 111.0 and 112.3 ms before, 82.9 and 82.5 ms after.
- These runs used the branch's (main's) `wcsaxes` folder on the compiled core of astropy 8.0.2; astropy main was not built, and the installed copy has no pytest config, so warnings-as-errors was not in force.
- Lint: ruff 0.16.1 check and format pass; upstream pins v0.17.3, which was not available.
- Not run: the whole suite, the docs build, towncrier, the other pre-commit hooks. CI's changelog check fails until the fragment is renamed.
