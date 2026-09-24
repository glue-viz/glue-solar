> Historical snapshot, archived 2026-09-05. Not an active checklist.
> Original location: `glue/PROFILE_WCS_RESTART_TODO.md`. Body preserved verbatim; paths and status claims describe that original context and may be stale.
> Current instructions: [the central work plan](../../../IRIS_GLUE_GAP_PLAN.md).

# TODO: restart `1dprofile_wcs` — WCS support in the 1D Profile viewer
Status updated 2026-09-02 from the glue-solar plan review; details in ~/Git/glue-solar/IRIS_GLUE_GAP_PLAN.md (WP0).

2026-09-05 follow-up: slice intensities used the selected row while numeric world coordinates used row zero. The fixes now use the same view for both and for Python export, and are pushed on profile-slice (1c19021d) and profile-wcsaxes (6cc8f20b, merging profile-slice). Worktrees remain in ~/Git/glue-fixes/core-profile-slice and core-profile-wcsaxes. Regressions cover linked/transposed layers, display-unit overrides, changing slices, and exported data/subsets. Profile suites pass 42/1 and 63/1 (passed/skipped). Qt profile-wcs-pr (f5444473) now contains ci-fixes and is also pushed; its full suite with the core WCSAxes branch passes 625/4/2 (passed/skipped/xfailed). Land #69 before #70. Fresh remote CI has not yet been validated. See ~/Git/glue-solar/IRIS_BRANCH_REVIEW.md. This TODO remains local and untracked.

Audit date 2026-08-29, against `main` = `upstream/main` = `dae530c3`.
Old branch: `origin/1dprofile_wcs` — 5 commits (`18a86e10`, `774c749c`,
`f84b919a`, `6b6bd790`, `586d1948`), merge-base `1c718378` (2022-05-04),
878 upstream commits behind.

**Verdict: do NOT rebase. Restart fresh off `main`, in three separate
pieces.** Salvage is complete (commit f767d320 on `profile-wcs`): close
glue-viz/glue#2248 closed and `origin/1dprofile_wcs` deleted on 2026-09-02.

Status 2026-09-02: Pieces A-C are implemented on `glue:profile-wcs` (175e7129,
f767d320, 98d7bb7c, c3bcd75b) and `glue-qt:profile-wcs` (1133c0e9); suites
green (glue profile 57/1; glue-qt 81/1 with both forks, 68/14 on released
glue-core). Opened on 2026-09-02 as draft PRs: glue-viz/glue#2596 (C,
`profile-slice`), glue-viz/glue#2601 (A, `profile-wcsaxes`, stacked on C) and
glue-viz/glue-qt#70 (B, `profile-wcs-pr`). Lint fixed, `_version.py` dropped,
commit messages shortened (the SHAs above are the pre-rewrite ones).

## Why rebasing is dead

- 9 of the 17 touched files no longer exist in glue-core: everything under
  `glue/viewers/profile/qt/`, `glue/viewers/image/qt/` and `glue/app/qt/`
  moved to the separate **glue-qt** repository in the 2023 split
  (`ead416ed` / `5217e3c7`). The `SliceWidget` base class the branch's new
  slider widget imports (`glue/viewers/common/qt/data_slice_widget.py`) is
  gone from glue-core entirely.
- `git merge-tree --write-tree main origin/1dprofile_wcs` → 12 conflicting
  paths; the three real content conflicts (`glue/viewers/profile/state.py`,
  `viewer.py`, `layer_artist.py`) are all in code rewritten since by the
  display-units work — resolution is a redesign, not conflict surgery.
- The branch tip is internally broken:
  - `wcsaxes_slice` hardcodes `0` for every non-x axis, so the sliders
    change the profile data but never the WCS the axis is drawn with — the
    branch's two features were never actually connected.
  - The last commit (`586d1948`, "undone some other changes - unsure if
    this is a good idea") reverted the branch's own world-axis changes but
    left the edited test expectations in
    `glue/viewers/profile/tests/test_state.py`, so `test_basic`,
    `test_basic_world` and `test_subset` fail at the tip.
  - Assorted regressions: no `reference_data is None` guard in `_set_wcs`;
    `as_steps` ignored in the layer artist; `reset=True` unconditionally;
    `session=` passed to `MatplotlibLayerState.__init__` which does not
    accept it; `numeric=True, categorical=False` dropped from the attribute
    combo helper.

## The design decision to make first

Main's profile viewer **already plots world coordinates** — as plain numeric
values on a normal Axes: `_display_world` (`state.py:164`), world-cid
preference in `_reference_data_changed` (`state.py:322-327`), world limits in
`_reset_x_limits` (`state.py:194-206`) — with full display-unit conversion
(`x_display_unit`/`y_display_unit`, `state.py:40-41`; ROI values
round-tripped through `UnitConverter`). What the old branch adds on top is
WCSAxes *formatting* (proper tick formatting via `coords[0]`, sexagesimal
where applicable).

WCSAxes tick formatting and `x_display_unit` are two competing owners of the
same axis. Proposed rule, to settle before writing code: **use WCSAxes
formatting only when displaying world coordinates AND no `x_display_unit`
override is active; fall back to the plain Axes path otherwise.** Whatever
the decision, it goes in the PR description.

Decided (f767d320): WCSAxes formatting only when reference coords are real (not
None/LegacyCoordinates), `x_att` is a world component, and
`(x_display_unit or '') == component native unit` (`_wcsaxes_with_unit`). In that
mode the profile, x limits and ROI are in pixel coordinates (image-viewer model);
crossing the unit boundary resets x limits; `x_limits_pixel` records the mode in
sessions.

---

## Piece A — glue-core: WCSAxes in the profile viewer

Branch off `main`, touching only `glue/viewers/profile/viewer.py` and
`glue/viewers/profile/state.py` (+ tests).

Salvage from the old branch (copy as snippets, do not cherry-pick):

- [x] `_set_wcs()` pattern from the branch's `viewer.py`:
      `axes.frame_class = RectangularFrame1D` +
      `axes.reset_wcs(slices=<wcsaxes_slice>, wcs=ref_coords)`, mirroring
      the image viewer's mechanism (`glue/viewers/image/viewer.py:115` on
      main). Add the missing `reference_data is None` guard; fall back to
      `get_identity_wcs(ndim)` for `None`/`LegacyCoordinates` coords —
      import it from `glue.viewers.image.viewer` (line 22) where it still
      lives; do NOT move it to a new `glue/utils/wcs.py` (python-export
      writes that import path into generated scripts,
      `glue/viewers/image/viewer.py:243`).
- [x] `wcsaxes_slice`: reads the per-axis index from `self.slices`, reversed to
      WCS order; implemented as a read-only property (no state mutation).
- [x] `update_x_ticklabel` override using
      `self.axes.coords[0].set_ticklabel(size=...)` — WCSAxes needs it and
      main's `MatplotlibProfileMixin` has no equivalent.
- [x] Reconcile with units: axis label and ROI handling stay owned by the
      existing `x_display_unit` code paths per the design rule above; keep
      main's `x_att` → `_update_axes` callback (the old branch deleted it)
      (apply_roi builds the subset on `x_att_pixel` only when `wcsaxes_active`).
- [x] Tests: extend `glue/viewers/profile/tests/` — WCSAxes active for a
      dataset with real coords, identity fallback without, slice handling
      for ndim > 1, and no regressions in the units tests
      (`test_state.py`, `test_viewer.py`).

Explicitly dead — do not carry from the old branch:

- The `x_att -> x_att_pixel` swap in `is_convertible_to_single_pixel_cid`.
  (The `apply_roi` swap was deliberately reinstated, but only while
  `wcsaxes_active`: the profile is in pixel coordinates in that mode.)
- All `layer_artist.py` changes; the `ProfileLayerState.__init__` changes;
  the `StateAttributeLimitsHelper` addition.
- The `test_state.py` expectation edits (they encode behavior the branch
  itself reverted).
- `.gitignore` and `glue/core/data.py` typo hunks: noise.

## Piece B — glue-qt: sliders and viewer wiring

Separate PR to `glue-viz/glue-qt`, after (or parallel with) Piece A.
Verified 2026-08-29 against the local clone `~/Git/glue-qt`
(fork `nabobalis/glue-qt`, current with `upstream/main` at `9780eaf9`):

- [x] Reuse `MultiSliceWidgetHelper` — it already lives in the shared
      location `glue_qt/viewers/common/slice_widget.py`, not under the
      image viewer, and is written against a generic viewer state
      (`x_att`/`slices`/`reference_data`). Done as a refactor: `y_att`/`z_att`
      are hasattr-guarded in a loop, `_plot_atts` uses `x_att_pixel` when
      present, stale sliders are cleared when data/atts become None, and sync
      is skipped while `len(slices) != ndim`. No profile-specific copy of the
      helper is needed (the old branch's `ProfileMultiSliceWidgetHelper`
      near-copy is obsolete).
- [x] Show/hide the sliders from
      `glue_qt/viewers/profile/options_widget.py` / `.ui` when the collapse
      function is `'slice'` (Piece C).
- [x] Pass `wcs=True` where `glue_qt/viewers/profile/data_viewer.py`
      constructs the matplotlib viewer — copy the image viewer's pattern at
      `glue_qt/viewers/image/data_viewer.py:48` — gated by
      `hasattr(ProfileViewerState, 'wcsaxes')` feature detection (no release
      contains A yet); switch to a version floor after the glue-core release.
- [ ] The `profile_tools.py` nearest-index fix (main ignores `x_display_unit`
      there) is independent of A/C and mergeable today; consider splitting it
      into its own tiny glue-qt PR.

## Piece C — glue-core: the `'slice'` collapse function (independent, ship first)

A standalone small PR — none of the WCS conflicts touch it:

- [x] Add `'slice'` to the profile `FUNCTIONS`; in
      `ProfileLayerState.update_profile` (around `state.py:474` on main),
      bypass `compute_statistic` and use
      `data.get_data(attribute, view=tuple(data_slice))` with
      `data_slice[pix_cid.axis] = slice(None)` and the other axes taken
      from viewer slice state.
- [x] Apply `UnitConverter` to the result (main's unit conversion at
      `state.py:480-487` postdates the old branch — the old snippet skips
      it).
- [x] `slices` state property on `ProfileViewerState` with sensible
      defaults (the old branch's `_set_default_slices` was never wired up —
      wire it).
- [x] Tests: slice profile equals the corresponding raw data row; units
      conversion applies; works when `ndim == 1` (sliders irrelevant).
- [x] (98d7bb7c) `ProfileLayerState.slice_view` translates the reference slice
      to each linked layer through the links
      (`ref[data.pixel_component_ids[axis], point]`), raising
      `IncompatibleDataException` on `IncompatibleAttribute` or out-of-range.
      Known wart: an out-of-range slice on the reference data itself raises
      `IndexError` at state.py:582 and the artist is hidden silently.

## Order and acceptance

1. Piece C -> glue-viz/glue#2596 from `profile-slice` (175e7129 + 98d7bb7c + RUF059 fix).
2. Piece A -> glue-viz/glue#2601 from `profile-wcsaxes` stacked on C (f767d320 + c3bcd75b + RUF059 fix).
3. Piece B -> glue-viz/glue-qt#70 from `profile-wcs-pr` (1133c0e9 without `glue_qt/_version.py`).

This TODO maps to no gap-plan phase; the nearest is 3.2, but 98d7bb7c is
intra-viewer slice translation only, not cross-viewer sync.

- [x] Old branch `origin/1dprofile_wcs` deleted (2026-09-02) only after A–C capture the
      salvage (blocked only on opening PR A; do it right after).
- [ ] Remove this TODO file when all three pieces are merged.
