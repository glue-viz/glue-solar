"""
Real-data checks for `wp10-fill-nan` (manual gate; needs ~/DATA/IRIS).

Run through the Validation runner with the feature worktree as the first root, e.g. from
the plan checkout:

    env HOME="$(mktemp -d)" PYTHONPATH=IRIS_PLAN_PROTOTYPES/review_20260905 \
      ~/mamba/envs/iris-plan/bin/python -B IRIS_PLAN_PROTOTYPES/review_20260905/run_checks.py \
      "$WT:$PWD/IRIS_PLAN_PROTOTYPES/review_20260905" \
      IRIS_PLAN_PROTOTYPES/review_20260927/probes/wp10/test_fill_nan_data.py -p qs_isolate -s

where WT is the `wp10-fill-nan` worktree (~/Git/glue-solar-wp10-fill-nan).
"""

import os
import pwd
from pathlib import Path

import numpy as np
import pytest
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState

from astropy.io import fits

import glue_solar
from glue_solar.sources.loaders.iris import image_data, raster_data

# ~/DATA/IRIS of the real user: the runner points HOME at a temporary directory
DATA = Path(pwd.getpwuid(os.getuid()).pw_dir) / "DATA" / "IRIS"
CODES = (-200, -199)
pytestmark = pytest.mark.skipif(not DATA.is_dir(), reason="needs ~/DATA/IRIS")


def _files(obsid):
    return sorted(DATA.glob(f"*_{obsid}_raster/*_raster_t000_r*.fits"))


def _raw(path, window):
    with fits.open(path) as hdul:
        names = [hdul[0].header[f"TDESC{i}"] for i in range(1, hdul[0].header["NWIN"] + 1)]
        return np.asarray(hdul[names.index(window) + 1].data), float(hdul[0].header["STEPS_AV"]), names


def _values(data):
    return data[data.main_components[0]]


def test_import_origin():
    print("glue_solar from", glue_solar.__file__)
    assert "glue-solar-wp10-fill-nan" in glue_solar.__file__


def test_4000005156_si_iv_scan0(qtbot):
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.image import ImageViewer
    from glue_qt.viewers.profile import ProfileViewer

    files = _files("4000005156")
    assert len(files) == 2
    raw0, steps_av, _ = _raw(files[0], "Si IV 1403")
    raw1, _, _ = _raw(files[1], "Si IV 1403")
    assert steps_av > 0  # positive step: no flip
    raw_fill = np.isin(raw0, CODES)
    print("raw dtype", raw0.dtype, "shape", raw0.shape, "raw -200/-199 count", int(raw_fill.sum()),
          "(-199:", int((raw0 == -199).sum()), ") raw min", float(raw0.min()))
    # 3,050,445 is the plan's -200 count (followup-3-3); the D12 rule also counts -199
    assert int((raw0 == -200).sum()) == 3_050_445

    scans = raster_data(files, ["Si IV 1403"])
    stack = raster_data(files, ["Si IV 1403"], stack=True)[0]
    v0, v1, vs = _values(scans[0]), _values(scans[1]), _values(stack)
    print("scan0", scans[0].label, v0.dtype, "stack", stack.label, vs.dtype, vs.shape)
    assert not np.isin(v0, CODES).any()
    assert int(np.isnan(v0).sum()) == int(raw_fill.sum())
    np.testing.assert_array_equal(np.isnan(v0), raw_fill)
    np.testing.assert_array_equal(v0, np.where(raw_fill, np.nan, raw0))
    np.testing.assert_array_equal(v1, np.where(np.isin(raw1, CODES), np.nan, raw1))
    np.testing.assert_array_equal(vs[0], v0)  # the same samples, NaN in the same places
    np.testing.assert_array_equal(vs[1], v1)

    # Exact limits: per-scan and stack agree on the same samples, and fill no longer sets the floor
    both = np.concatenate([v0.ravel(), v1.ravel()])
    exact = {
        "raw scan0 min/0.25%": (float(raw0.min()), float(np.percentile(raw0, 0.25))),
        "scan0 nanmin/0.25%": (float(np.nanmin(v0)), float(np.nanpercentile(v0, 0.25))),
        "stack nanmin/0.25%": (float(np.nanmin(vs)), float(np.nanpercentile(vs, 0.25))),
        "scans nanmin/0.25%": (float(np.nanmin(both)), float(np.nanpercentile(both, 0.25))),
    }
    for key, value in exact.items():
        print("exact", key, value)
    assert exact["stack nanmin/0.25%"] == exact["scans nanmin/0.25%"]
    assert np.nanmax(vs) == np.nanmax(both)
    assert np.nanpercentile(vs, 99.75) == np.nanpercentile(both, 99.75)
    assert exact["scan0 nanmin/0.25%"][0] > -199 and exact["scan0 nanmin/0.25%"][1] > -199

    # glue's own default limits (percentile 100, 10,000-sample random subset) and the preset's 99.5 %
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([scans[0], scans[1], stack])
    limits = {}
    for data in (scans[0], scans[1], stack):
        viewer = app.new_data_viewer(ImageViewer, data=data)
        state = viewer.layers[0].state
        limits[data.label] = {100: (state.v_min, state.v_max)}
        state.percentile = 99.5
        limits[data.label][99.5] = (state.v_min, state.v_max)
        print("glue limits", data.label, limits[data.label])
        assert state.percentile == 99.5
        assert all(v_min > -199 for v_min, _ in limits[data.label].values())
        viewer.close(warn=False)

    # A one-pixel Pixel subset's Mean spectrum is the raw spectrum with fill as NaN
    counts = raw_fill.sum(axis=2)
    step, slit = 32, 400
    if not 0 < counts[step, slit] < raw0.shape[2]:
        step, slit = map(int, np.argwhere((counts > 0) & (counts < raw0.shape[2]))[0])
    print("pixel", (step, slit), "fill samples in spectrum", int(counts[step, slit]), "of", raw0.shape[2])
    slices = [slice(step, step + 1), slice(slit, slit + 1), slice(None)]
    group = app.data_collection.new_subset_group("pixel", PixelSubsetState(scans[0], slices))
    profile = app.new_data_viewer(ProfileViewer, data=scans[0])
    profile.state.function = "mean"
    profile.state.x_att = scans[0].pixel_component_ids[2]
    layer = next(l for l in profile.layers if l.layer is group.subsets[0])
    x, y = layer.state.profile
    expected = np.where(raw_fill[step, slit], np.nan, raw0[step, slit])
    np.testing.assert_array_equal(np.asarray(y, dtype=np.float32), expected)
    print("pixel mean spectrum NaN count", int(np.isnan(y).sum()), "matches raw with fill as NaN")


def test_3400109360_nan_positions_follow_the_flipped_data():
    files = _files("3400109360")
    assert len(files) == 8
    _, steps_av, windows = _raw(files[0], "Si IV 1403")
    assert steps_av < -0.01
    flipped = {}
    for index, path in enumerate(files):
        scans = raster_data([path])
        assert len(scans) == len(windows)
        for window in windows:
            data = next(d for d in scans if d.label.startswith(window.replace(" ", "_") + "-"))
            raw, _, _ = _raw(path, window)
            fill = np.flip(np.isin(raw, CODES), axis=0)
            values = _values(data)
            np.testing.assert_array_equal(np.isnan(values), fill)
            assert not np.isin(values, CODES).any()
            old = np.asarray(data[data.main_components[1]], dtype=bool)  # irispy's mask, built before the flip
            print(f"r{index:05d} {window:>13}: fill {int(fill.sum()):>9,d} NaN equal; irispy mask differs at "
                  f"{int((old != fill).sum()):,d}")
            if index < 2:
                flipped[index, window] = fill
        del scans

    stack = raster_data(files[:2], stack=True)
    assert len(stack) == len(windows)
    for window in windows:
        data = next(d for d in stack if d.label.startswith(window.replace(" ", "_") + "-"))
        values = _values(data)
        assert values.shape[0] == 2
        for i in range(2):
            np.testing.assert_array_equal(np.isnan(values[i]), flipped[i, window])
        print(f"stack {window:>13}: NaN equal to the flipped raw fill in both scans")


def test_3640107442_aia_cutouts():
    paths = sorted(DATA.glob("*_3640107442_SDO/aia_l2_*.fits"))
    assert len(paths) == 9
    for path in paths:
        with fits.open(path) as hdul:
            raw = np.asarray(hdul[0].data)
        data = image_data(path)
        values = _values(data)
        n200, n199 = int((raw == -200).sum()), int((raw == -199).sum())
        print(f"{path.name}: raw {raw.dtype} -200 {n200:,d} -199 {n199:,d} -> {values.dtype} NaN {int(np.isnan(values).sum()) if values.dtype.kind == 'f' else 0:,d}")
        if n200:
            assert values.dtype == np.float32
            np.testing.assert_array_equal(np.isnan(values), raw == -200)
            assert int((values == -199).sum()) == n199
        else:
            assert np.issubdtype(values.dtype, np.int16)
            np.testing.assert_array_equal(values, raw)
