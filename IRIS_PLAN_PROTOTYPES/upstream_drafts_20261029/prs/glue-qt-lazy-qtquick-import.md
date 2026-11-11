# Import QtQuick only when creating the Qt6 application

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:lazy-qtquick-import` at `fe4c58e781` (pushed 2026-11-12)
- Label: enhancement

## Body

~~~~~markdown
`glue_qt.utils.app` imports `QtQuick` at module level, but only `get_qapp` uses it, and only under Qt6, to select the OpenGL graphics API before it creates the application. The import now happens there.

The gain is on Qt5 only, where QtQuick (with QtQml and QtNetwork) was imported for nothing: about 31 ms of import time and 35 ms of the time to the glue window. On Qt6 nothing is gained, as the application is always created.

`test_import_does_not_import_qtquick` in the new `glue_qt/utils/tests/test_app.py` imports `glue_qt.utils.app` in a subprocess and checks that `qtpy.QtQuick` is not in `sys.modules`. It fails without the change. `.ruff.toml` gets a per-file ignore of S603 for that subprocess call.
~~~~~

## Notes for the owner (not to paste)

- New branch: half of the fork's `perf-q6-startup-qt`, from `qt-small/patches/q6a-qtquick-import.diff` as it is.
- The Qt5 numbers are the original commit's. Not re-measured: this environment has only PyQt6.
- `enhancement` lists it under New Features in the release notes; no label lists it under Other Changes.
- Merge before #68 (`macos-integration`): both add `glue_qt/utils/tests/test_app.py`. `perf-q5-lazy-terminal` also edits `.ruff.toml`, on other lines: the two merge cleanly (checked).
- Tests on the branch: `test_app.py`, 1 passed. With the test on main: `CalledProcessError ... returned non-zero exit status 1` (the `assert 'qtpy.QtQuick' not in sys.modules` in the subprocess), 1 failed.
- ruff: passes.
