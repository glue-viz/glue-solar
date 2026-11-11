# Profile fit: use the fitter configured in Settings

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:fitter-settings` at `d871900191` (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
In the profile viewer's Fit tab, nothing set in the Settings dialog reaches a fit. `ProfileTools._on_settings` opens the dialog on a new `self.fit_function()`, which is dropped when the dialog closes, and `_on_fit` then makes another one. Set the polynomial degree to 1, click Fit, and the default degree 3 is fitted.

`ProfileTools` now keeps one fitter per fitter class and uses it for both the dialog and the fit. Each profile viewer has its own, so two viewers can fit with different settings. The settings last as long as the viewer; they are not saved in sessions.

One limit is left, in glue-core: a parameter value or bound set in the dialog cannot be cleared again. Emptying the field or unticking Bounded passes `None` to `BaseFitter1D.set_constraint`, which ignores `None`, so the earlier value stays until `set_constraint` accepts `None`. Before this change nothing set in the dialog had any effect.

`test_fit_settings` and `test_fit_settings_per_viewer` in `glue_qt/viewers/profile/tests/test_profile_tools.py` fail without the change.
~~~~~

## Notes for the owner (not to paste)

- Existing fork branch, to force-push: it now holds only its first commit (f28fa72d) with a new message. Its second commit is `fit-settings-bool-option`.
- The constraints-clearing change is not in it, as asked (`qt-small/patches/constraints-clear-option.diff` is the one-line glue-qt version; it reads glue-core's private `_constraints`). The body's third paragraph states the limit.
- Tests on the branch: `test_profile_tools.py`, 6 passed. Without the source change: 2 failed (`test_fit_settings`: `assert ['-2.132160e-...3.500000e+00'] == ['8.000000e+0...3.500000e+00']`; `test_fit_settings_per_viewer`: `assert 4 == 2`), 4 passed.
- ruff: passes.
- `fitter-settings-widget` is stacked on this one.
