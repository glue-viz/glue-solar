# Let a fitter provide its own settings dialog (`settings_widget`)

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:fitter-settings-widget` at `74ba110484` (pushed 2026-11-12)
- Needs: `fitter-settings` (stacked on it)
- Label: enhancement

## Body

~~~~~markdown
The Settings button of the profile viewer's Fit tab always opens `FitSettingsWidget`, a form of the fitter's options and constraints. A fit plugin whose settings are of another kind, such as a model to compose from several components, has no way to show them.

A fitter class can now set a `settings_widget` class attribute. It is called with the fitter and returns a dialog, which is shown with its `exec_()` method. Fitters without one get `FitSettingsWidget`, as before.

This is stacked on #FITTER-SETTINGS-PR (use the fitter configured in Settings); only the last commit is new. With that PR the dialog is given the fitter that the fits use, so what it sets reaches the fit. Without it the dialog would get a fitter that is dropped when it closes.

`doc/customizing_guide/fitting.rst` gets a short section on the hook. `test_fitter_settings_widget` in `glue_qt/viewers/profile/tests/test_profile_tools.py` fails without the change.
~~~~~

## Notes for the owner (not to paste)

- Replace `#FITTER-SETTINGS-PR` with the number of the `fitter-settings` PR. Open after that one merges (then the PR shows one commit), or as a stacked PR that says so.
- Existing fork branch, to force-push: rebuilt on `fitter-settings` from `qt-small/patches/fitter-settings-widget-on-f28fa72d.diff`. Its own commit: 3 files, +42 -1.
- Changes from the reviewer's patch: the source comment is one line; the test compares the dialogs' fitter with `ProfileTools._get_fitter()` (the same object for both dialogs), not only its type, since that is what makes the hook work; the docs section is new (15 lines of rst).
- The hook reads `getattr(fitter, 'settings_widget', ...)`, on the instance, as the patch does. A plain function set as a class attribute would be called as a bound method (fitter passed twice); the docs show a dialog class.
- Tests on the branch: `test_profile_tools.py`, 7 passed. With the test file on `fitter-settings`: `test_fitter_settings_widget` fails (the second dialog is `FitSettingsWidget`, not `OwnSettings`), 1 failed, 6 passed.
- ruff: passes. The new rst parses with docutils; the docs were not built.
