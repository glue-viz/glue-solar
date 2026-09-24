"""Acceptance checks for wp3_impl; run in an isolated process with the prototype on sys.path."""
import json
import shutil

import numpy as np
import sunpy.map
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer
from ndcube.wcs.wrappers import CompoundLowLevelWCS
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.coordinates import SkyCoord
from sunpy.coordinates import Helioprojective

import wp3_impl

wp3_impl.install_browser_factories()

from glue_solar.sources.loaders.iris import QtIRISImporter, image_data, raster_data
from glue_solar.sources.maps import _parse_sunpy_map

SJI_1330 = "iris_l2_20210905_001833_3620258102_SJI_1330_t000.fits"
SJI_1400 = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
RASTERS = [f"iris_l2_20140329_140938_3860258481_raster_t000_r0000{i}.fits" for i in range(3)]


def _real(files, name):
    return next(path for path in files if path.name == name)


def _round_trip(data):
    dc = DataCollection([data])  # a Data can join only one DataCollection (hub); build a fresh Data per test
    s = GlueSerializer(dc).dumps()
    return s, GlueUnSerializer.loads(s).object("__main__")


def _assert_same_coords(original, restored):
    grid = np.meshgrid(*[np.arange(n) for n in original.shape[::-1]], indexing="ij")
    for shift in (0, 0.37):
        pixels = [g + shift for g in grid]
        for expected, actual in zip(original.coords.pixel_to_world_values(*pixels), restored.coords.pixel_to_world_values(*pixels)):
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)
    world = original.coords.pixel_to_world_values(*grid)
    for expected, actual in zip(original.coords.world_to_pixel_values(*world), restored.coords.world_to_pixel_values(*world)):
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)
    assert restored.coords.world_axis_names == original.coords.world_axis_names
    assert restored.coords.world_axis_units == original.coords.world_axis_units
    assert [c.label for c in restored.world_component_ids] == [c.label for c in original.world_component_ids]


def _style_record(s, label):
    return next(rec for rec in json.loads(s).values() if isinstance(rec, dict) and rec.get("label") == label)["style"]


def test_sji_session_restores_gwcs_meta_and_colormap(irispy_test_files):
    original = image_data(_real(irispy_test_files, SJI_1330))
    s, dc = _round_trip(original)
    restored = dc[0]
    _assert_same_coords(original, restored)
    assert type(restored.coords._wcs).__module__.startswith("gwcs")
    np.testing.assert_array_equal(restored["Time"], original["Time"])
    assert set(restored.meta) == set(original.meta)
    assert restored.style.preferred_cmap.name == "irissji1330"
    style = _style_record(s, original.label)
    assert style["_type"] == "wp3_impl.SolarVisualAttributes"
    assert "_protocol" not in style


def test_raster_session_rebuilds_the_tab_table(irispy_test_files):
    original = raster_data([_real(irispy_test_files, RASTERS[0])], ["C II 1336"])[0]
    s, dc = _round_trip(original)
    restored = dc[0]
    _assert_same_coords(original, restored)
    assert list(restored.coords._wcs.wcs.ctype)[1:] == ["HPLT-TAB", "HPLN-TAB"]
    assert isinstance(restored.meta["exposure time"], u.Quantity)
    assert restored.meta["exposure time"].unit == u.s
    np.testing.assert_array_equal(restored.meta["exposure time"], original.meta["exposure time"])
    assert "auxiliary times" not in restored.meta
    assert "exposure FOV center" not in restored.meta
    np.testing.assert_array_equal(restored["Time"], original["Time"])
    s2 = GlueSerializer(dc).dumps()  # re-save the restored dataset (guards pixel_shape)
    restored2 = GlueUnSerializer.loads(s2).object("__main__")[0]
    _assert_same_coords(original, restored2)


def test_stack_session_restores_compound_wcs(irispy_test_files):
    paths = [_real(irispy_test_files, name) for name in RASTERS]
    original = raster_data(paths, ["C II 1336"], stack=True)[0]
    s, dc = _round_trip(original)
    restored = dc[0]
    _assert_same_coords(original, restored)
    assert restored.coords.world_axis_names[-1] == "Scan"
    assert isinstance(restored.coords._wcs, CompoundLowLevelWCS)
    label = original.label
    np.testing.assert_array_equal(restored["Time"], original["Time"])
    np.testing.assert_array_equal(restored[f"{label} mask"], original[f"{label} mask"])
    assert np.array_equal(restored[label], original[label], equal_nan=True)


def test_sunpy_map_session_saves_and_keeps_colormap():
    coord = SkyCoord(0 * u.arcsec, 0 * u.arcsec, obstime="2020-01-01", observer="earth", frame=Helioprojective)
    header = sunpy.map.make_fitswcs_header(
        np.zeros((16, 16)), coord, scale=[2, 2] * u.arcsec / u.pix, instrument="AIA", wavelength=171 * u.angstrom, telescope="SDO"
    )
    original = _parse_sunpy_map(sunpy.map.Map(np.zeros((16, 16)), header), "sunpy-map")
    s, dc = _round_trip(original)
    restored = dc[0]
    assert restored.style.preferred_cmap.name == "sdoaia171"
    assert set(restored.meta) == set(original.meta)
    _assert_same_coords(original, restored)


def test_browser_datasets_reference_their_files(qtbot, tmp_path, irispy_test_files, monkeypatch):
    for name in [SJI_1400, *RASTERS]:
        shutil.copy2(_real(irispy_test_files, name), tmp_path / name)
    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    tree = dialog.obs_tree
    rows = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    next(row for row in rows if row.childCount() == 0).setCheckState(0, Qt.Checked)  # SJI-only observation
    raster_row = next(row for row in rows if row.childCount() > 0)
    next(raster_row.child(j) for j in range(raster_row.childCount()) if raster_row.child(j).text(0).startswith("C II 1336")).setCheckState(0, Qt.Checked)
    dialog.stack.setChecked(True)
    dialog.finalize()
    assert len(dialog.datasets) == 2
    assert all(hasattr(d, "_load_log") for d in dialog.datasets)
    monkeypatch.chdir(tmp_path)
    dc = DataCollection(dialog.datasets)
    s = GlueSerializer(dc, include_data=False, absolute_paths=False).dumps()
    assert len(s) < 200_000
    logs = [rec for rec in json.loads(s).values() if isinstance(rec, dict) and rec.get("_type", "").endswith("LoadLog")]
    stack_log = next(log for log in logs if log["kwargs"] != [[]])
    assert stack_log["kwargs"] == [[["files", RASTERS], ["windows", ["C II 1336"]], ["stack", True]]]
    assert all("/" not in log["path"] for log in logs)
    # Move the referenced files, then re-save and restore once more at a second location.
    moved = tmp_path / "moved"
    moved.mkdir()
    for name in [SJI_1400, *RASTERS]:
        shutil.move(tmp_path / name, moved / name)
    monkeypatch.chdir(moved)
    restored = GlueUnSerializer.loads(s).object("__main__")
    second = GlueSerializer(restored, include_data=False, absolute_paths=False).dumps()
    moved_again = tmp_path / "moved_again"
    moved_again.mkdir()
    for name in [SJI_1400, *RASTERS]:
        shutil.move(moved / name, moved_again / name)
    monkeypatch.chdir(moved_again)
    restored = GlueUnSerializer.loads(second).object("__main__")
    stack = next(d for d in dialog.datasets if d.label.endswith("-stack"))
    stack2 = next(d for d in restored if d.label.endswith("-stack"))
    assert np.array_equal(stack2[stack.label], stack[stack.label], equal_nan=True)
    _assert_same_coords(stack, stack2)


def test_plain_data_keeps_the_stock_style_record():
    s, _ = _round_trip(Data(x=[1, 2, 3], label="plain"))
    style = _style_record(s, "plain")
    assert style["_type"] == "glue.core.visual.VisualAttributes"
    assert "_protocol" not in style
