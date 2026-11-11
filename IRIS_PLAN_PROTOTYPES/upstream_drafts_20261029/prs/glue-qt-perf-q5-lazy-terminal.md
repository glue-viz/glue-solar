# Import the IPython terminal only when it is first opened

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:perf-q5-lazy-terminal` at `06b51bd85f` (on the fork, not rebuilt)
- Needs: pairs with glue `perf-g6-lazy-ipython` (either order)
- Label: enhancement

## Body

~~~~~markdown
`glue_qt.app.application` imports `glue_qt.app.terminal` at module level, which pulls in IPython, ipykernel and qtconsole, although the terminal is created only when the user first opens it. `_fix_ipython_pylab`, called from `GlueApplication.start`, also imports IPython just to look for a running shell, which cannot exist if IPython was never imported.

The terminal is now imported in `_create_terminal`, and `_fix_ipython_pylab` returns early if IPython is not in `sys.modules`. A broken IPython, ipykernel or qtconsole install now fails when the terminal is first opened, not at import.

Importing `glue_qt.app.application` no longer imports the terminal, which took 55 ms on top of IPython (median of 7 runs of `python -X importtime`, glue-core 1.27.0, PyQt5, macOS). glue-core still imports IPython itself, from `glue.viewers.common.viewer`; once it stops (glue-viz/glue#GLUE-PR), importing `glue_qt.app` imports none of the three and saves 155 ms.

Tests in `glue_qt/app/tests/test_application.py`: `test_import_does_not_import_terminal` (in a subprocess) and `test_fix_ipython_pylab_does_not_import_ipython`. Both fail without the change. `.ruff.toml` gets S603 for the subprocess call in that test file.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt: the fork's branch as it is, 3 files, +37 -7. The body is drawn from its commit message.
- Checked today: both tests pass on the branch and both fail on main (`assert 'True' == 'False'`; `assert 'IPython' not in sys.modules`). The timings are the commit's own (macOS), not re-measured.
- Replace `glue-viz/glue#GLUE-PR` with the number of the glue PR "No IPython import from viewers.common.viewer" (`perf-g6-lazy-ipython`, glue row 20) once it is open, or cut that clause.
