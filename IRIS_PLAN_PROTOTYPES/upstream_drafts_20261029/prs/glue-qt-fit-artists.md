# Profile fit: Clear removes every artist a fitter plots

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:fit-artists` at `65f296421b` (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
`BaseFitter1D.plot` returns a list of matplotlib artists (its docstring says plots will not be cleared properly otherwise). `ProfileTools._plot_fit` kept only the first one, `fitter.plot(...)[0]`. For a fit plugin whose `plot` draws more than one line, such as one per model component, the other lines stayed on the axes after Clear and after the next fit.

It now keeps all of them. Fitters that plot one line, as all of glue-core's do, are unchanged.

`test_fit_plot_artists` in `glue_qt/viewers/profile/tests/test_profile_tools.py` gives the fitter a `plot` that draws two lines and checks that Clear removes both. It fails without the change (`assert 1 == 2`).
~~~~~

## Notes for the owner (not to paste)

- Existing fork branch, to force-push. The source change is now the two lines that matter (`append` to `extend`, `)[0])` to `))`); the commented-out `# y_model = ...` line is left alone and the two-line comment is gone.
- I changed the test's place and set-up, not what it checks. As it was (imports of `patch` and `PolynomialFitter`, test placed after `test_fit_polynomial`) it conflicts with `fitter-settings` in `test_profile_tools.py`: `git merge-tree` reports `CONFLICT (content)`. It is now the last test of the class, uses pytest's `monkeypatch` on the tools' current fit function and adds no import, so the two merge in either order.
- Tests on the branch: `test_profile_tools.py`, 5 passed. Without the source change: `assert 1 == 2` (`len([<matplotlib.lines.Line2D ...>])`), 1 failed, 4 passed.
- ruff: passes.
