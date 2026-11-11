# Fix the fit settings dialog for check box (BoolOption) options

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:fit-settings-bool-option` at `d3c8dd7e16` (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
Clicking OK in the Settings dialog of the profile viewer's Fit tab raises `AttributeError: 'QCheckBox' object has no attribute 'value'` for a fitter that has a `BoolOption`. `FitSettingsWidget.update_fitter_from_settings` reads every option with `widget.value()`, which only the spin boxes of `IntOption` and `FloatOption` have.

It now reads `item.value` from the form item, which each kind of item in `glue_qt/core/simpleforms.py` already defines for its own widget.

No fitter in glue-core has a `BoolOption`, so this only shows with a fit plugin that has one.

`test_bool_option` in `glue_qt/core/tests/test_fitters.py` fails without the change, with the error above.
~~~~~

## Notes for the owner (not to paste)

- The second commit of the fork's `fitter-settings` (f3aad9c0), unchanged apart from its message. Touches no file the other Fit tab branches touch.
- Tests on the branch: `glue_qt/core/tests/test_fitters.py`, 6 passed. Without the source change: `AttributeError: 'QCheckBox' object has no attribute 'value'`, 1 failed, 5 passed.
- ruff 0.14.14 (the pre-commit pin): passes.
