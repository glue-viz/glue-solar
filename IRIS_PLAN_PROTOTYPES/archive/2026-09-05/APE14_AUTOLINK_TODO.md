> Historical snapshot, archived 2026-09-05. Not an active checklist.
> Original location: `glue/APE14_AUTOLINK_TODO.md`. Body preserved verbatim; paths and status claims describe that original context and may be stale.
> Current instructions: [the central work plan](../../../IRIS_GLUE_GAP_PLAN.md).

# TODO: APE-14 support in `WCSLink` / `wcs_autolink` (glue-core)
Status updated 2026-09-02 from the glue-solar plan review; details in ~/Git/glue-solar/IRIS_GLUE_GAP_PLAN.md (WP0).

2026-09-05 follow-up: the Astropy 6.1.7 mixed-WCS regression is fixed in commit 656017b9, pushed to origin/ape14-wcs-autolink. The fix in ~/Git/glue-fixes/core-ape14 avoids no-op sliced wrappers and retains scalar/array transform assertions. The autolinking suite passes on Astropy 6.1.7 and 8.0.1: 31 passed, 1 xfailed, 1 xpassed on each. See ~/Git/glue-solar/IRIS_BRANCH_REVIEW.md. Fresh remote CI has not yet been validated; acceptance is not a claim that the published PR is green. This TODO remains local and untracked.

Target: one PR to `glue-viz/glue` against `main`. Implemented on branch
`ape14-wcs-autolink` (b16a3703, 016d9cf2; merge-base dae530c3 == upstream/main
on 2026-09-02). Opened as draft PR glue-viz/glue#2595 on 2026-09-02 with the
keyword-only tweak; commit messages were shortened, so the SHAs above are the
pre-rewrite ones (tip now bad24b99, same tree).
Everything lives in
`glue/plugins/wcs_autolinking/wcs_autolinking.py` (346 lines) plus its tests.

Motivation: glue-solar's IRIS datasets expose APE-14 low-level WCS objects
(irispy's SJI gWCS, the raster FITS `-TAB` WCS, and a `_GlueWCS`
`BaseWCSWrapper` around both). The glue-solar capability audit ('Data loading
and representation' bullet, lines 129-131, and the 'SJI and raster temporal
coordination' row, line 182, of `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` in that
repo) measured that autolinking
finds 0 links for them today, and that forcing the attempt crashes. glue-solar
keeps its Phase 1.4 `link_hpc` helper (world links by physical type, time-aware);
this PR adds the complementary frame-0 pixel WCSLink (decision D1, 2026-09-02).

Related upstream issue: glue-viz/glue#2152 "Add an APE-14 wrapper that
preserves units" — reference it in the PR; glue-solar's `_GlueWCS`
(arcsecond-converting wrapper) is a live example of such a wrapper.

---

## 1. The three defects (verified against main)

### 1a. The gatekeeper silently drops low-level WCS datasets

`wcs_autolink`, lines 320–321:

```python
wcs_datasets = [data for data in data_collection
                if hasattr(data, 'coords') and isinstance(data.coords, BaseHighLevelWCS)]
```

Any dataset whose `coords` is only `BaseLowLevelWCS` (e.g. a
`BaseWCSWrapper`) is excluded before linking is attempted. This is why the
IRIS pair produces 0 links with no error.

### 1b. The "generalized APE 14-compatible way" requires astropy `WCS`

`WCSLink.__init__`, lines 146–162 use `wcs.has_celestial`, `wcs.celestial`,
`wcs.wcs.naxis`, `wcs.wcs.lng`, `wcs.wcs.lat` — none of which exist on the
APE-14 ABCs. A low-level WCS reaching this path dies with
`AttributeError: ... has no attribute 'has_celestial'` (the exact crash the
glue-solar audit measured). The rest of that path is already APE-14-clean:
the physical-type matching loop (lines 172–181), `SlicedLowLevelWCS`,
`HighLevelWCSWrapper`, and `pixel_to_pixel` in `get_cids_and_functions`
(lines 79–97).

### 1c. World→pixel axis mapping assumes reversed order

Lines 177 and 180 map matched world axis `i` to pixel axis
`world_n_dim - i - 1`. That holds for astropy `WCS` but is not guaranteed by
APE-14; the correct source is `axis_correlation_matrix`.

---

## 2. Fix plan

- [x] `wcs_autolink`: accept `BaseLowLevelWCS` as well as `BaseHighLevelWCS`.
      Normalize at entry: wrap bare low-level objects in
      `HighLevelWCSWrapper` before use — path 1's
      `pixel_to_pixel(wcs1, wcs2, ...)` requires the high-level API
      (`pixel_to_world` / `world_to_pixel`).
- [x] `WCSLink.__init__`: guard the celestial special case behind
      `isinstance(<unwrapped wcs>, astropy.wcs.WCS)` for BOTH datasets. It
      exists to link *different* sky frames (e.g. galactic ↔ equatorial)
      through SkyCoord and can keep doing that for astropy pairs. Everything
      else falls through to physical-type matching. Note: the IRIS case needs
      no celestial handling at all — SJI and raster both expose
      `custom:pos.helioprojective.lon/lat`, so the existing matching loop
      finds them once the crash is gone.
- [x] Replace the `world_n_dim - i - 1` mapping with pixel axes read from
      `wcs.axis_correlation_matrix` (all pixel axes correlated with the
      matched world axis must be kept out of the integer slices so
      `SlicedLowLevelWCS` retains them — celestial `-TAB` axes couple two
      pixel axes to each world axis).
- [x] Failure hygiene: a pair whose world objects cannot transform (e.g.
      helioprojective frames where one WCS carries no observer — the bare
      SJI header case from the glue-solar audit) must raise
      `IncompatibleWCS` cleanly via the existing try/except in
      `get_cids_and_functions`, never a traceback. Verify the except clause
      catches what sunpy raises (`ConvertError`).
- [x] Keep `as_affine_link`, `__gluestate__`, `OffsetLink`, `AffineLink`
      untouched — they operate on the produced pixel functions and cids.

## 3. Tests (`glue/plugins/wcs_autolinking/tests/test_wcs_autolinking.py`)

The existing file is built entirely on astropy `WCS`; there is no APE-14
low-level fixture anywhere in it.

- [x] Add a minimal synthetic `BaseLowLevelWCS` subclass fixture (linear
      transform, settable `world_axis_physical_types`, `world_axis_units`,
      `axis_correlation_matrix`, `world_axis_object_classes/components`).
- [x] `wcs_autolink` finds a link for: low-level ↔ low-level, and
      low-level ↔ astropy `WCS`, when physical types match.
- [x] No link and no exception when physical types are disjoint.
- [x] A fixture with a non-trivial (coupled) `axis_correlation_matrix`
      exercising the 1c fix.
- [x] Forwards/backwards asserted against analytic expected values in every
      new test (stronger than a `pixel_to_pixel` comparison; `pixel_to_pixel`
      is not called by the new tests).
- [x] All existing astropy-`WCS` tests pass unchanged (the celestial
      cross-frame path must not regress).

## 4. Downstream (glue-solar, after a glue release)

- [ ] Regression test in glue-solar: `wcs_autolink` on
      `DataCollection([sji, raster])` built from the irispy fixtures in
      `glue_solar/conftest.py` yields exactly one `WCSLink` pairing the HPC
      axes (the audit's "temporal coordination" row flipped to a pass).
      Gate: skip unless `from glue.plugins.wcs_autolinking.wcs_autolinking
      import kept_numpy_axes` succeeds; use the `sns/` copies of the irispy
      files (the `raster/` copy of the 2021 raster does not load in irispy 0.8.1).
- [ ] Check `_GlueWCS` exposes coherent
      `world_axis_object_classes/components` after its arcsecond conversion —
      the high-level SkyCoord construction depends on them; fix in glue-solar
      if not.
      Verified broken 2026-09-02: `_GlueWCS` inherits deg object classes, so
      `HighLevelWCSWrapper(_GlueWCS(raster)).pixel_to_world` raises
      `ValueError: Latitude angle(s) must be within -90 deg <= angle <= 90 deg`
      and raster<->raster pairs get 0 links even on the branch. Fix (WP1):
      override `world_axis_object_classes` (arcsec unit kwarg; entries are
      mixed 3-/4-tuples, unpack `cls, args, kwargs, *rest`) and
      `world_axis_object_components` getters (~15 lines).
      Raster<->map pairs fail the same way (`IncompatibleWCS`).
- [x] Decided 2026-09-02 (D1): Phase 1.4 `link_hpc` stays; it is complementary
      (time-aware world links), not replaced by this PR.

## 5. Acceptance criteria

- [x] IRIS SJI + raster autolink in glue with no manual step (verified in
      glue-solar against a dev glue install before the upstream release).
- [x] No behavior change for astropy-`WCS`-only collections.
- [x] Incompatible pairs fail silently in `wcs_autolink` (skip) and with
      `IncompatibleWCS` from direct `WCSLink(...)` construction — never a
      traceback.
- [x] PR references glue-viz/glue#2152 and describes the IRIS use case
      (needs `forwards`/`backwards` and `transform` options keyword-only first:
      PLR0917 under ruff 0.16, see WP0 brief).
- [ ] Expect a review question on `clone(link)` for low-level coords: it raises
      `GlueSerializeError` because glue-core only has `@saver(astropy.wcs.WCS)`;
      pre-existing gap, not introduced by this branch.
- [ ] Remove this TODO file when the PR is merged.
