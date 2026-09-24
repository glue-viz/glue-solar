> Historical snapshot, archived 2026-09-05. Not an active checklist.
> Original location: `glue-qt/MACOS_INTEGRATION_TODO.md`. Body preserved verbatim; paths and status claims describe that original context and may be stale.
> Current instructions: [the central work plan](../../../IRIS_GLUE_GAP_PLAN.md).

# TODO: macOS integration fixes (glue-qt)
Status updated 2026-09-05; findings and fix evidence are in ~/Git/glue-solar/IRIS_BRANCH_REVIEW.md.
The #68 rewrite, force-push, body and draft update are complete. The 2026-09-05 follow-up is now pushed on `macos-integration` at `0b16dd55`; the historical `macos-integration-v2` alias remains at `4d93c64f`. Do not rerun the old push/reset procedure.
The permission test needs a pending plugin edit because newer glue-core skips unchanged saves. That correction is committed and pushed on `ci-fixes` (`5cc9e23e`, PR #69), then merged here and into `profile-wcs-pr` (`f5444473`), which also inherits the shared CI repairs. Full local suites with development core pass: 622 passed / 4 skipped / 2 xfailed here, 619 / 4 / 2 for #69. These are local results; fresh remote CI has not yet been validated. This TODO remains local and untracked.

Scoped 2026-08-29 against `main` = `upstream/main` = `9780eaf9`.
Evidence: screenshot of glue on macOS (`~/Screenshot 2026-08-29 at
6.45.32 AM.png`) showing (a) the menu-bar application name as **python**,
(b) toolbar text visibly smaller than the native menu-bar font, with small
icons. All changes land in **glue-qt**; nothing is needed in glue-core.

---

## Issue 1 — application name shows "python"

**Cause.** `glue_qt/utils/app.py:56` creates the app as
`QtWidgets.QApplication([''])` — empty argv, and no
`setApplicationName`/`setApplicationDisplayName` anywhere in the codebase
(verified by grep). On macOS the bold app-menu title comes from the process
/ bundle name (`CFBundleName` of the Python framework's `Python.app`), so a
script-launched Qt app shows "python" regardless of Qt-side names.

**Fix plan** (all in `get_qapp`, `glue_qt/utils/app.py`):

- [x] Construct with a real argv: `QApplication(['glue'])`, and call
      `setApplicationName('glue')`. The redundant
      `setApplicationDisplayName('glue')` call was removed in the published rewrite.
      On macOS the menu title and the About/Hide/Quit labels come from
      `CFBundleName` (qtbase `qcocoahelpers.mm` `qt_mac_applicationName`), so
      the Qt-side names change nothing there. On Linux/Windows the QPA plugin
      appends the display name to native top-level window titles
      (`qplatformwindow.cpp` `formatWindowTitle`, case-sensitive `endsWith`), so
      the main window `Glue` would read `Glue - glue`: drop
      `setApplicationDisplayName` (decided 2026-09-02). `QSettings` grep done:
      no direct use in glue-qt; `setApplicationName` moves the default macOS
      `QSettings` plist from `org.python.python.Python` to `org.python.python.glue`,
      which glue does not use (`glue.config`/`save_settings`), so nothing is lost.
- [x] The bold menu-bar title itself needs the Cocoa bundle-name fix,
      applied BEFORE the `QApplication` is instantiated (the Cocoa menu is
      built at app init). Standard approach:

      ```python
      if platform.system() == 'Darwin':
          try:
              from Foundation import NSBundle
              info = (NSBundle.mainBundle().localizedInfoDictionary()
                      or NSBundle.mainBundle().infoDictionary())
              info['CFBundleName'] = 'glue'
          except ImportError:
              pass
      ```

      Place it in `get_qapp` inside the `if qapp is None:` block, ahead of
      the `QApplication` construction.
- [x] Dependency: add `pyobjc-framework-Cocoa; sys_platform == "darwin"`
      to glue-qt's dependencies (platform-conditional, small; decide hard
      dep vs. a `macos` extra — recommend the hard conditional dep so every
      mac user gets the fix without opting in).
      Follow-up: the conda-forge glue-qt-feedstock recipe has no pyobjc
      (`python.app [osx]`, `pyqt` only); open a feedstock issue after the
      release (`pyobjc-framework-cocoa  # [osx]`).
- [ ] The Dock icon is already handled
      (`glue_qt/app/application.py:291-292` sets the glue icon); verify the
      Dock *name* also picks up `CFBundleName` after the fix.
- [ ] Manual verification on macOS: menu-bar title, About item, Quit item,
      Cmd-Tab switcher label. Automated test: `test_mac_bundle_name` asserts
      `NSBundle.mainBundle().infoDictionary()['CFBundleName'] == 'glue'` after
      `get_qapp()` (headless-verifiable; 3 passed offscreen).

## Issue 2 — text and icons render too small

**Causes, all verified in source:**

1. **Deliberate font shrink on mac.** `__get_font_size_offset`
   (`glue_qt/utils/app.py:13-23`) subtracts **2 points** from the
   application font on Darwin ("fonts are generally too large", a legacy
   workaround), and 1 point elsewhere. The native macOS menu bar is not
   affected by `qapp.setFont`, so in-app text sits ~2pt below system size —
   exactly the mismatch in the screenshot.
2. **Stale persisted base size.** `settings.FONT_SIZE` is derived once from
   a default-constructed `QFont().pointSize()` and then saved forever
   (`app.py:65-68`); a value captured under an older Qt/platform persists
   across upgrades.
3. **Hardcoded font sizes** scattered around:
   - `glue_qt/viewers/common/base_widget.py:34` — status bar forced to
     `font-size:10px`.
   - `glue_qt/dialogs/link_editor/data_graph.py:74` — `setPointSize(10)`.
   - `glue_qt/viewers/common/data_slice_widget.py:46` — 0.75 × app font.
4. **Point/pixel mixing.** `fix_tab_widget_fontsize` (`app.py:83-90`) and
   `glue_qt/app/preferences.py:95` write `font.pointSize()` into a `px`
   stylesheet. Points equal pixels only under macOS's 72-dpi convention;
   the workaround also targets a Qt4/5-era tab-font bug that may not exist
   under Qt6 at all.
5. **Tiny fixed toolbar icons**: 16 px (`glue_qt/app/application.py:381`,
   `edit_subset_mode_toolbar.py:32`, `data_collection_model.py:457`),
   14 px (`application.py:445`), 15 px (`layer_artist_model.py:203`) —
   small against modern macOS chrome and contributing to the shrunken look.

**Fix plan:**

- [x] Drop the Darwin `size_offset` (zeroed on every platform; Linux/Windows
      in-app text grows by 1 pt, stated in the PR body). The system font size is
      the correct default on every modern platform; `FONT_SIZE` remains a
      pure user preference on top.
- [x] Stop persisting the derived default: when `FONT_SIZE` is `None`/`-1`,
      use the current default font at startup without writing it back, so
      the baseline tracks the platform/Qt in use. Only persist values the
      user actually sets in preferences (`update_global_font_size` path).
      Migrate a legacy saved value equal to the current platform default
      back to `-1` once.
- [x] Sweep the hardcoded sizes: status bar and link-editor overrides deleted.
- [ ] `data_slice_widget.py:46` still scales its label to 0.75x; default keep,
      check in the manual pass, delete only if unreadable at 13 pt.
- [x] Re-test the Qt tab-title bug on Qt6/macOS. Qt6 propagates the native
      application font, so skip the stylesheet workaround there. Retain the
      `pt` workaround for supported Qt5 versions.
- [x] Toolbar icon sizes: replace the fixed 14–16 px values with the
      platform default (`style().pixelMetric(QStyle.PM_ToolBarIconSize)`,
      capped at 24 px), including the related subset combo and layer lists.
      The PNG assets shipped in glue-core are at least 125 px and scale
      cleanly at this size.
- [x] `AA_UseHighDpiPixmaps` handling (`app.py:74-78`) is already correct
      for Qt6 (default, guarded try/except) — no change.
- [ ] Regression sweep after the font change: dialogs built from `.ui`
      files with fixed geometries may clip at +2pt — open every dialog on
      macOS once (preferences, link editor, data importers) and fix any
      clipped layout.

## Acceptance

- [ ] Menu bar reads **glue** (title, About, Quit, Cmd-Tab).
- [x] In-app toolbar/status text matches the system UI size; side-by-side
      before/after screenshots against the 6.45.32 AM baseline.
- [ ] No clipped dialogs on macOS at the new sizes (manual).
- [ ] Linux/Windows remote CI green after the 2026-09-05 CI-test fix push.
      The shared fixes are in glue-viz/glue-qt#69 and its dependent branches;
      fresh remote results still need validation.
- [ ] Runs clean on PyQt6 + Retina (primary target) and PyQt5 (still
      supported by glue-qt).
- [ ] Remove this TODO file when merged.
- [ ] Before judging visually: `~/.glue/settings.cfg` must say `font_size = -1.0`;
      headless runs of main-based glue_qt write 9.0 there, which the branch keeps
      as a 9 pt override.

## Follow-ups (not part of this PR)

Further macOS integrations, roughly by value per effort. Each is its own
small PR unless noted.

1. - [ ] **Native menu roles.** Give the Preferences action
         `QAction.PreferencesRole` and the About action `AboutRole` so
         "Settings… ⌘," and "About glue" land in the application menu where
         macOS users expect them (`glue_qt/app/actions.py` /
         `application.py` menu construction). A few lines.
2. - [ ] **`QFileOpenEvent` handling.** Handle Apple open-document events on
         the `QApplication` so `open -a glue session.glu` (and, once file
         associations exist, double-click) loads the session or data file.
         Small; belongs near `get_qapp`/`GlueApplication` startup.
3. - [ ] **Dock feedback.** `QApplication.alert()` bounce (or a Dock badge)
         when a long computation or directory scan finishes while glue is in
         the background. Small.
4. - [ ] **Dark mode.** Follow the system appearance via Qt ≥ 6.5's
         `QStyleHints.colorScheme` + `colorSchemeChanged`, and offer to sync
         the plot foreground/background theme (ties into the existing
         Black-on-White / White-on-Black themes in preferences). Medium.
5. - [ ] **Trackpad pinch-zoom.** Map `QNativeGestureEvent` zoom gestures to
         viewer zoom in the matplotlib viewers
         (`glue_qt/viewers/matplotlib/widget.py`). Medium.
6. - [ ] **A real `.app` bundle** (briefcase/py2app): true `.glu` file
         associations, proper identity everywhere without the NSBundle
         workaround, notarization for distribution. A separate project, not
         a PR to this repo.
