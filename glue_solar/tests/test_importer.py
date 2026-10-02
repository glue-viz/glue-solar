import copy
import gzip
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest
from irispy.io import read_files
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.io import fits
from astropy.utils.masked import Masked
from astropy.wcs.wcsapi import HighLevelWCSWrapper
from astropy.wcs.wcsapi.high_level_api import values_to_high_level_objects
from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper

from glue_solar.conftest import MD5, OBS_A, OBS_B, OBS_C, OBS_S, find_irispy_test_file, startobs
from glue_solar.sources.iris import is_iris_fits, read_iris_file
from glue_solar.sources.loaders.iris import QtIRISImporter, image_data, raster_data
from glue_solar.sources.loaders.scan import scan_directory
from glue_solar.sources.loaders.stack_spectrograms import stack_spectrogram_sequence

# The unit glue is shown each world axis in, by physical type; time, scan and the others keep their own
SHOWN = {"em.wl": u.AA, "custom:pos.helioprojective.lat": u.arcsec, "custom:pos.helioprojective.lon": u.arcsec}


@pytest.fixture
def dialog(qtbot, iris_tree):
    dlg = QtIRISImporter(iris_tree)
    qtbot.addWidget(dlg)
    return dlg


def _row(dialog, obsid):
    tree = dialog.obs_tree
    return next(tree.topLevelItem(i) for i in range(tree.topLevelItemCount()) if tree.topLevelItem(i).text(1) == obsid)


@pytest.mark.parametrize("suffix", ["", "_test"])
def test_find_irispy_test_file(tmp_path, suffix):
    path = tmp_path / f"iris_l2_example{suffix}.fits"
    assert find_irispy_test_file([path], "iris_l2_example.fits") == path


def test_tests_keep_off_the_users_settings(tmp_path):
    from glue import config

    from glue_solar.sources.loaders import iris

    assert os.path.dirname(iris.QSettings("glue-solar", "glue-solar").fileName()) == str(tmp_path)
    assert config.CFG_DIR != os.path.join(os.path.expanduser("~"), ".glue")


def test_tree_lists_observations_and_files(dialog):
    assert dialog.obs_tree.topLevelItemCount() == 3
    row = _row(dialog, OBS_A[2])
    children = [row.child(i).text(0) for i in range(row.childCount())]
    assert children == [
        "SJI_1400",
        "C II 1336 — 2 raster file(s)",
        "Mg II k 2796 — 2 raster file(s)",
        "AIA 171_THIN",
    ]
    assert row.text(2) == "Test raster 1x2 3s"
    assert row.text(6) == "4"


def test_derived_raster_file_is_never_a_window_and_counted(dialog, tmp_path):
    tree = dialog.obs_tree
    assert OBS_S not in [tree.topLevelItem(i).text(1) for i in range(tree.topLevelItemCount())]
    assert dialog.progress.text() == "Skipped 1 raster file(s) that are not Level 2"
    dialog.set_directory(tmp_path)  # nothing left out, so the count goes
    assert dialog.progress.format() == "%p%"


def test_ticking_the_observation_ticks_its_files(dialog):
    row = _row(dialog, OBS_A[2])
    row.setCheckState(0, Qt.Checked)
    assert len(dialog.selected()) == 4


def test_load_selected_real_sji(qtbot, tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    shutil.copy2(source, tmp_path / source.name)
    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
    dialog.finalize()
    assert len(dialog.datasets) == 1
    data = dialog.datasets[0]
    assert data is dialog.first_image
    assert data.label == "SJI_1400-3620258102-2021-09-05T00:18:33"
    assert data.shape == (62, 40, 37)
    assert data.style.preferred_cmap.name == "irissji1400"


def test_ticked_raster_windows_of_an_observation_are_read_at_once(qtbot, monkeypatch, irispy_test_files):
    # each read maps every raster file, and a mapped file stays open
    reads = []

    def read(files, **kwargs):
        reads.append(kwargs["spectral_windows"])
        return read_files(files, **kwargs)

    monkeypatch.setattr("irispy.io.read_files", read)  # the loaders import it as they read
    scans = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name)
    dialog = QtIRISImporter(scans[0].parent)
    qtbot.addWidget(dialog)
    row = _row(dialog, "3860258481")
    entries = [row.child(i) for i in range(row.childCount()) if "raster file(s)" in row.child(i).text(0)][:2]
    for entry in entries:
        entry.setCheckState(0, Qt.Checked)
    dialog.finalize()
    windows = [name for _, _, name, _ in dialog.loaded]
    assert reads == [windows]
    assert len(windows) == 2
    for _, _, name, datasets in dialog.loaded:
        assert [data.label for data in datasets] == [data.label for data in raster_data(scans, [name])]


def test_deconvolved_sji_is_listed_and_loaded_beside_the_plain_one(qtbot, tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    plain = tmp_path / "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
    deconvolved = tmp_path / "iris_l2_20210905_001833_3620258102_SJI_1400_t000_deconvolved.fits"
    shutil.copy2(source, plain)
    shutil.copy2(source, deconvolved)
    [observation] = scan_directory(tmp_path)
    assert observation.sji == {"SJI_1400": plain, "SJI_1400 (deconvolved)": deconvolved}

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
    dialog.finalize()
    labels = [data.label for data in dialog.datasets]
    assert labels == [
        "SJI_1400-3620258102-2021-09-05T00:18:33",
        "SJI_1400_deconvolved-3620258102-2021-09-05T00:18:33",
    ]
    assert read_iris_file(str(deconvolved)).label == labels[1]  # File -> Open labels it the same way
    assert read_iris_file(str(plain)).label == labels[0]


def test_single_entry_observation_is_ticked_on_its_own_row(dialog):
    row = _row(dialog, OBS_B[2])  # SJI only
    assert row.childCount() == 0
    assert row.text(6) == "1 — SJI_2832"
    row.setCheckState(0, Qt.Checked)
    assert [(kind, name) for _, kind, name in dialog.selected()] == [("sji", "SJI_2832")]


def test_recursive_toggle_rescans(dialog):
    dialog.recursive.setChecked(False)
    row = _row(dialog, OBS_A[2])
    assert row.childCount() == 0  # only the top-level SJI is left, so it collapses onto the row
    assert row.text(6) == "1 — SJI_1400"


def test_extract_archive_then_lists_its_windows(qtbot, iris_tree, tmp_path):
    tree = tmp_path / "copy"
    shutil.copytree(iris_tree, tree)  # extraction writes next to the archive; keep the shared fixture pristine
    dlg = QtIRISImporter(tree)
    qtbot.addWidget(dlg)
    row = _row(dlg, OBS_C[2])
    assert row.childCount() == 0
    assert row.text(6).startswith("0 — Extract ")
    row.setCheckState(0, Qt.Checked)
    dlg.finalize()
    assert dlg.result() == 0  # stays open
    assert dlg.datasets == []
    assert (tree / f"{MD5}iris_l2_{'_'.join(OBS_C)}_raster").is_dir()
    row = _row(dlg, OBS_C[2])
    assert [row.child(i).text(0) for i in range(row.childCount())] == [  # archive entry gone once unpacked
        "C II 1336 — 1 raster file(s)",
        "Mg II k 2796 — 1 raster file(s)",
    ]


def test_browser_and_file_open_read_only_the_primary_header_of_a_gzipped_file(tmp_path):
    d, t, o = OBS_B
    header = fits.PrimaryHDU(np.zeros((100, 100), np.int16)).header
    header.update(TELESCOP="IRIS", INSTRUME="SJI", OBSID=o, STARTOBS=startobs(d, t), TDESC1="SJI_2832")
    path = tmp_path / f"iris_l2_{d}_{t}_{o}_SJI_2832_t000.fits.gz"
    # not even gzip after the header: reading on into the data, as astropy's getheader does, fails
    path.write_bytes(gzip.compress(header.tostring().encode()) + b"not the data")
    [observation] = scan_directory(tmp_path)
    assert observation.sji == {"SJI_2832": path}
    assert is_iris_fits(str(path))


def test_file_open_reads_no_header_from_a_file_that_does_not_start_as_fits(tmp_path):
    # File > Open asks about every file; read on to an END card, a large file of another kind is read whole
    path = tmp_path / "table.csv"
    path.write_text(fits.Header({"TELESCOP": "IRIS"}).tostring())
    assert not is_iris_fits(str(path))


def test_real_sji_adapter_preserves_mask_units_and_coordinates(irispy_test_files):
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    cube = read_files(path, memmap=False, uncertainty=False)
    data = image_data(path)

    science, mask, _time, exposure = data.main_components
    assert data.shape == cube.shape
    assert data.get_component(exposure).units == "s"
    with fits.open(path) as hdul:
        aux = hdul[1]
        np.testing.assert_array_equal(data[exposure][:, 0, 0], aux.data[:, aux.header["EXPTIMES"]])
        for key, column in (("pztx", "PZTX"), ("pzty", "PZTY"), ("xcenix", "XCENIX"), ("slit x position", "SLTPX1IX")):
            np.testing.assert_array_equal(data.meta[key], aux.data[:, aux.header[column]])
    assert data.get_component(science).units == str(cube.unit)
    [rate] = data.derived_components
    assert rate.label == f"{science.label} DN/s"
    assert data.get_component(rate).units == "DN/s"
    np.testing.assert_allclose(data[rate], data[science] / data[exposure], rtol=1e-6)
    mask = data.get_component(mask).data
    assert mask.dtype == np.uint8
    np.testing.assert_array_equal(mask, np.isnan(data.get_component(science).data))
    np.testing.assert_array_equal(mask, cube.mask | (cube.data == -199))  # irispy masks only -200

    longitude = next(component for component in data.world_component_ids if component.label == "Helioprojective Longitude")
    expected = cube.axis_world_coords()[0][0, 0, 0].Tx.to_value(u.arcsec)
    assert data.get_component(longitude).units == "arcsec"
    assert data.get_component(longitude).data[0, 0, 0] == pytest.approx(expected)
    assert np.nanmax(np.abs(data.get_component(longitude).data)) < 180 * 3600
    world = data.coords.pixel_to_world_values(0, 0, 0)
    assert data.coords.world_to_pixel_values(*world) == pytest.approx((0, 0, 0), abs=1e-8)


def test_aia_cube_uses_the_same_irispy_adapter(tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    path = tmp_path / "aia_l2_20210905_001833_3620258102_171.fits"
    shutil.copy2(source, path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].header["INSTRUME"] = "AIA_3"
        hdul[0].header["OBSID"] = "20210905_001833_3620258102"
        hdul[0].header["TDESC1"] = "171_THIN"
        hdul[0].header["TWAVE1"] = 171

    data = image_data(path)
    assert data.label == "171_THIN-3620258102-2021-09-05T00:18:33"
    assert data.style.preferred_cmap.name == "sdoaia171"
    assert len(data.main_components) == 4  # science, mask and the per-frame Time and Exposure time


def test_real_raster_preserves_exact_exposure_times(irispy_test_files):
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits")
    data = raster_data([path], ["C II 1336"], stack=True)
    cube = read_files(path, spectral_windows=["C II 1336"], memmap=False, uncertainty=False)["C II 1336"][0]
    expected_times = cube.axis_world_coords("time", wcs=cube.extra_coords)[0].utc.to_value("datetime64")

    assert len(data) == 1
    assert data[0].label == "C_II_1336-3860258481-2014-03-29T14:09:38-scan-0"
    assert data[0].shape == (8, 109, 17)
    assert [c.label for c in data[0].world_component_ids] == [
        "Helioprojective Longitude",
        "Helioprojective Latitude",
        "Wavelength",
    ]
    assert data[0].get_component(data[0].main_components[0]).units == "DN_IRIS_FUV"
    assert [data[0].get_component(cid).units for cid in data[0].world_component_ids[:2]] == ["arcsec", "arcsec"]
    np.testing.assert_array_equal(data[0]["Time"][:, 0, 0], expected_times)
    np.testing.assert_array_equal(data[0]["Time"][:, -1, -1], expected_times)
    world = data[0].coords.pixel_to_world_values(0, 0, 0)
    assert data[0].coords.world_to_pixel_values(*world) == pytest.approx((0, 0, 0), abs=1e-8)
    assert len(data[0].main_components) == 4
    np.testing.assert_array_equal(data[0]["Exposure time"][:, 0, 0], cube.meta["exposure time"].to_value(u.s))


def test_real_rasters_stack_without_resampling_and_keep_scan_times(irispy_test_files):
    paths = sorted(path for path in irispy_test_files if "20140329_140938_3860258481_raster_t000_r" in path.name)
    sequence = read_files(paths, spectral_windows=["C II 1336"], memmap=False, uncertainty=False)["C II 1336"]
    expected_times = [
        cube.axis_world_coords("time", wcs=cube.extra_coords)[0].utc.to_value("datetime64") for cube in sequence
    ]
    data = raster_data(paths, ["C II 1336"], stack=True)[0]

    science = data.id[data.label]
    mask = data.id[f"{data.label} mask"]
    values = data.get_component(science).data
    times = data["Time"]
    raw_last = np.asarray(sequence[-1].data, dtype=np.float32).copy()
    raw_last[np.isin(raw_last, (-200, -199))] = np.nan
    assert data.shape == (len(paths), 8, 109, 17)
    assert [c.label for c in data.world_component_ids][0] == "Scan"
    assert data.coords.world_axis_units == ("Angstrom", "arcsec", "arcsec", "")
    np.testing.assert_array_equal(values[-1], raw_last)
    assert data.get_component(mask).data.dtype == np.uint8
    np.testing.assert_array_equal(data.get_component(mask).data, np.isnan(values))
    for i, expected in enumerate(expected_times):
        np.testing.assert_array_equal(times[i, :, 0, 0], expected)
        np.testing.assert_array_equal(times[i, :, -1, -1], expected)
    for i, scan in enumerate(sequence):  # each scan's own exposure times, not scan 0's
        exposure = scan.meta["exposure time"].to_value(u.s)
        np.testing.assert_array_equal(data["Exposure time"][i, :, 0, 0], exposure)
        np.testing.assert_allclose(data[f"{data.label} DN/s"][i], values[i] / exposure[:, None, None], rtol=1e-6)
    np.testing.assert_array_equal(
        data.coords.pixel_to_world_values(0, 0, 0, np.arange(len(paths)))[-1], np.arange(len(paths))
    )

    wavelength, slit, step = np.meshgrid(np.arange(17), np.arange(109), np.arange(8), indexing="ij")
    source_world = sequence[0].wcs.pixel_to_world_values(wavelength, slit, step)
    stacked_world = data.coords.pixel_to_world_values(wavelength, slit, step, np.zeros_like(wavelength))
    for expected, actual, unit, physical_type in zip(
        source_world,
        stacked_world[:3],
        sequence[0].wcs.world_axis_units,
        sequence[0].wcs.world_axis_physical_types,
    ):
        if physical_type in SHOWN:
            expected = (expected * u.Unit(unit)).to_value(SHOWN[physical_type])
        np.testing.assert_allclose(actual, expected)
    for actual, expected in zip(
        data.coords.world_to_pixel_values(*stacked_world),
        (wavelength, slit, step, np.zeros_like(wavelength)),
    ):
        np.testing.assert_allclose(actual, expected, atol=3e-6)

    with pytest.raises(ValueError, match="same shape"):
        stack_spectrogram_sequence([sequence[0], sequence[1][:-1]], memmap=False)


def test_real_raster_fill_values_become_nan(irispy_test_files):
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")
    data = raster_data([path], ["Si IV 1403"])[0]
    values = data[data.main_components[0]]
    assert values.size == 216_920
    assert not np.isin(values, (-200, -199)).any()
    assert np.isnan(values).sum() == 35_027
    mask = data[f"{data.label} mask"]
    assert mask.dtype == np.uint8
    np.testing.assert_array_equal(mask, np.isnan(values))


class _CountedWCS(BaseWCSWrapper):
    """A WCS that counts how often its world axis units and physical types are read, and its conversions to world."""

    def __init__(self, wcs):
        super().__init__(wcs)
        self.reads = 0
        self.conversions = 0

    @property
    def world_axis_units(self):
        self.reads += 1
        return self._wcs.world_axis_units

    @property
    def world_axis_physical_types(self):
        self.reads += 1
        return self._wcs.world_axis_physical_types

    def pixel_to_world_values(self, *pixel_arrays):
        self.conversions += 1
        return self._wcs.pixel_to_world_values(*pixel_arrays)

    def world_to_pixel_values(self, *world_arrays):
        return self._wcs.world_to_pixel_values(*world_arrays)


def test_arcsec_coordinates_read_the_axes_once(irispy_test_files):
    obs = "iris_l2_20210905_001833_3620258102_{}.fits"
    raster = raster_data([find_irispy_test_file(irispy_test_files, obs.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, obs.format("SJI_1400_t000")))
    for data in (*raster, sji):
        raw = _CountedWCS(data.coords._wcs)
        wcs = type(data.coords)(raw)
        units, kinds = raw._wcs.world_axis_units, raw._wcs.world_axis_physical_types
        arrays = [np.array([-0.5, 1.5, n - 1.5]) for n in data.shape[::-1]]
        missing = [np.array([np.nan, 1.5])] * raw.pixel_n_dim  # gWCS cannot take NaN back to pixels
        for pixel in (missing, arrays, [1] * raw.pixel_n_dim, [np.float64(2.5)] * raw.pixel_n_dim):
            world = wcs.pixel_to_world_values(*pixel)
            # the values of a Quantity conversion, bit for bit
            for value, expected, unit, kind in zip(world, raw.pixel_to_world_values(*pixel), units, kinds):
                if kind in SHOWN:
                    if kind.endswith(".lon"):
                        circle = (360 * u.deg).to_value(unit)
                        expected = (np.asarray(expected) + circle / 2) % circle - circle / 2
                    expected = (np.asarray(expected) * u.Unit(unit)).to_value(SHOWN[kind])
                assert type(value) is type(expected)
                assert np.asarray(value).tobytes() == np.asarray(expected).tobytes()
            if pixel is not missing:
                # and back, also as a single-precision world position
                for where in (world, [np.asarray(value, dtype=np.float32) for value in world]):
                    native = [
                        value if kind not in SHOWN else (np.asarray(value) * SHOWN[kind]).to_value(unit)
                        for value, unit, kind in zip(where, units, kinds)
                    ]
                    for value, expected in zip(wcs.world_to_pixel_values(*where), raw.world_to_pixel_values(*native)):
                        assert np.asarray(value).tobytes() == np.asarray(expected).tobytes()
        # WCSAxes converts through these dozens of times per draw: the axes are read once, not per call
        assert raw.reads == 2


def _same(shown, wrapped):
    """Whether two high-level world objects are the same position, time or quantity."""
    if hasattr(shown, "Tx"):
        return u.allclose(shown.Tx, wrapped.Tx, rtol=0, atol=1e-9 * u.arcsec) and u.allclose(
            shown.Ty, wrapped.Ty, rtol=0, atol=1e-9 * u.arcsec
        )
    if hasattr(shown, "jd"):
        return abs((shown - wrapped).to_value(u.s)) < 1e-6
    return u.allclose(shown, wrapped, rtol=1e-15)


def test_high_level_objects_agree_with_the_values(irispy_test_files):
    # glue's WCS link builds SkyCoords and SpectralCoords from the values: they said degrees and metres while the
    # values were arcsec and Angstrom, which raised (latitude past 90 deg) or gave positions 3600 times too far out
    obs = "iris_l2_20210905_001833_3620258102_{}.fits"
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, obs.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, obs.format("SJI_1400_t000")))
    scans = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    [stack] = raster_data(scans, ["C II 1336"], stack=True)
    for data in (raster, sji, stack):
        pixel = [n / 2 + 0.25 for n in data.shape[::-1]]
        shown, wrapped = HighLevelWCSWrapper(data.coords), HighLevelWCSWrapper(data.coords._wcs)
        objects = shown.pixel_to_world(*pixel)
        assert all(map(_same, objects, wrapped.pixel_to_world(*pixel)))
        assert shown.world_to_pixel(*objects) == pytest.approx(wrapped.world_to_pixel(*objects), abs=1e-9)
        values = map(Masked, data.coords.pixel_to_world_values(*pixel))  # astropy takes masked low-level values too
        assert all(map(_same, values_to_high_level_objects(*values, low_level_wcs=data.coords), objects))


def test_arcsec_coordinates_reuse_identical_conversions(irispy_test_files):
    from glue_solar.sources.loaders.iris import _MEMO_ENTRIES, _MEMO_SAMPLES

    obs = "iris_l2_20210905_001833_3620258102_{}.fits"
    raster = raster_data([find_irispy_test_file(irispy_test_files, obs.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, obs.format("SJI_1400_t000")))
    for data in (*raster, sji):
        raw = _CountedWCS(data.coords._wcs)
        wcs, fresh = type(data.coords)(raw), type(data.coords)(raw)
        pixel = [np.array([-0.5, 1.5, n - 1.5]) for n in data.shape[::-1]]
        for inputs in (pixel, [np.float64(2.5)] * raw.pixel_n_dim):
            first = wcs.pixel_to_world_values(*inputs)
            conversions = raw.conversions
            again = wcs.pixel_to_world_values(*copy.deepcopy(inputs))  # the same inputs in other objects
            assert raw.conversions == conversions  # reused
            # bit for bit what the wrapped WCS gives, of the same types
            for value, expected in zip(again, fresh.pixel_to_world_values(*inputs)):
                assert type(value) is type(expected)
                assert np.asarray(value).tobytes() == np.asarray(expected).tobytes()
            # each caller has its own arrays: changing them changes nothing kept
            for value in (*first, *again):
                if isinstance(value, np.ndarray):
                    value[...] = 0
            for value, expected in zip(wcs.pixel_to_world_values(*inputs), fresh.pixel_to_world_values(*inputs)):
                assert np.asarray(value).tobytes() == np.asarray(expected).tobytes()
        # another type, dtype, shape or value is converted again
        conversions = raw.conversions
        wcs.pixel_to_world_values(*[np.asarray(2.5)] * raw.pixel_n_dim)  # a 0-d array, not a scalar
        for change in (lambda p: p.astype(np.float32), lambda p: p[:2], lambda p: np.nextafter(p, 0)):
            wcs.pixel_to_world_values(*map(change, pixel))
        assert raw.conversions == conversions + 4
        # at most the _MEMO_ENTRIES inputs used last are kept, and none larger than _MEMO_SAMPLES samples
        scalars = [np.float64(2.5)] * raw.pixel_n_dim
        for shift in range(1, 2 * _MEMO_ENTRIES + 1):
            wcs.pixel_to_world_values(*[p + shift for p in pixel])
            conversions = raw.conversions
            wcs.pixel_to_world_values(*scalars)  # used after each new input, as by an unchanged panel's redraw
            assert raw.conversions == conversions
        assert len(wcs._memo) == _MEMO_ENTRIES
        conversions = raw.conversions
        wcs.pixel_to_world_values(*[p + 2 * _MEMO_ENTRIES for p in pixel])  # the latest is kept
        wcs.pixel_to_world_values(*pixel)  # the first is not
        large = [np.zeros(_MEMO_SAMPLES + 1)] * raw.pixel_n_dim
        side = int(_MEMO_SAMPLES**0.5) + 1  # small inputs that broadcast to more samples
        spread = [np.zeros((side, 1)), np.zeros((1, side)), *[np.zeros((1, 1))] * (raw.pixel_n_dim - 2)]
        for inputs in (large, large, spread, spread):
            wcs.pixel_to_world_values(*inputs)
        assert raw.conversions == conversions + 5


_THREADS = """
import os, sys, threading, traceback
import numpy as np
from glue_solar.sources.loaders import iris

wcs = iris.raster_data([sys.argv[1]], ["Si IV 1403"])[0].coords
pixels = [np.arange(1000.0) % n for n in wcs.pixel_shape]
done = threading.Event()

def pixels_of(i):  # more inputs than the wrapper keeps, so each conversion reaches wcslib
    return [p + i % 300 * 1e-3 for p in pixels]

def convert():
    try:
        i = 0
        while not done.is_set():
            wcs.pixel_to_world_values(*pixels_of(i))
            wcs.axis_correlation_matrix
            i += 1
    except Exception:  # wcslib errors from a race are as much a failure as a crash
        traceback.print_exc()
        os._exit(1)

thread = threading.Thread(target=convert)
thread.start()
for i in range(20_000):
    wcs.pixel_to_world_values(*pixels_of(i))
done.set()
thread.join()

# then threads that reuse and evict the wrapper's kept conversions at once, with room for 2 of 4 inputs
iris._MEMO_ENTRIES = 2
wcs._memo.clear()
sys.setswitchinterval(1e-6)

def reuse(seed):
    try:
        for i in np.random.default_rng(seed).integers(0, 4, 5000):
            wcs.pixel_to_world_values(*[p[:2] + i for p in pixels])
    except Exception:
        traceback.print_exc()
        os._exit(1)

threads = [threading.Thread(target=reuse, args=(seed,)) for seed in range(4)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
"""


def test_raster_coordinates_are_thread_safe(irispy_test_files):
    # wcslib crashes when two threads use one -TAB WCS (astropy/astropy#19174), so run it apart
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    result = subprocess.run([sys.executable, "-c", _THREADS, str(path)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-2000:]


def test_negative_step_raster_fill_follows_the_flipped_data(tmp_path, irispy_test_files):
    # The fill must follow irispy's flip of STEPS_AV < -0.01 rasters and cover -199, which irispy's mask,
    # -200 only, leaves out
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")
    path = tmp_path / source.name
    shutil.copy2(source, path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].header["STEPS_AV"] = -1.0
        window = [hdul[0].header[f"TDESC{i}"] for i in range(1, hdul[0].header["NWIN"] + 1)].index("Si IV 1403") + 1
        first = hdul[window].data[0]
        first[tuple(np.argwhere(first != -200)[0])] = -199  # the fixtures hold no -199
    with fits.open(path) as hdul:
        fill = np.flip(np.isin(hdul[window].data, (-200, -199)), axis=0)
    cube = read_files(path, spectral_windows=["Si IV 1403"], memmap=False, uncertainty=False)["Si IV 1403"][0]
    assert not np.array_equal(cube.mask, fill)

    scan = raster_data([path], ["Si IV 1403"])[0]
    np.testing.assert_array_equal(np.isnan(scan[scan.main_components[0]]), fill)
    np.testing.assert_array_equal(scan[f"{scan.label} mask"], fill)
    stack = raster_data([path, path], ["Si IV 1403"], stack=True)[0]
    for values in stack[stack.main_components[0]]:
        np.testing.assert_array_equal(np.isnan(values), fill)


def test_duplicate_real_raster_is_listed_and_loaded_once(qtbot, tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits")
    for directory in (tmp_path / "download", tmp_path / "extracted"):
        directory.mkdir()
        shutil.copy2(source, directory / source.name)

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    row = dialog.obs_tree.topLevelItem(0)
    assert row.text(6) == "1"
    assert all("1 raster file(s)" in row.child(i).text(0) for i in range(row.childCount()))
    row.child(0).setCheckState(0, Qt.Checked)
    dialog.stack.setChecked(True)
    dialog.finalize()
    assert len(dialog.datasets) == 1


@pytest.mark.parametrize(
    ("name", "instrume", "band"),
    [
        ("iris_l2_20240101_000000_1234567890_SJI_1400_t000.fits", "SJI", "SJI_1400"),
        ("aia_l2_20240101_000000_1234567890_171.fits", "AIA_3", "171_THIN"),
    ],
)
def test_reader_failure_stays_in_dialog(qtbot, tmp_path, name, instrume, band):
    path = tmp_path / name
    fits.PrimaryHDU(
        header=fits.Header(
            {
                "TELESCOP": "IRIS",
                "INSTRUME": instrume,
                "OBSID": "1234567890",
                "STARTOBS": "2024-01-01T00:00:00",
                "TDESC1": band,
                "TWAVE1": 1400,
            }
        )
    ).writeto(path)

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
    dialog.finalize()

    assert dialog.result() == 0
    assert dialog.datasets == []
    assert dialog.progress.format().startswith(f"Loading {band} from {name} failed:")


def test_raster_load_failure_names_the_file_that_fails(qtbot, tmp_path, irispy_test_files):
    scans = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r0000" in path.name)[:2]
    for scan in scans:
        shutil.copy2(scan, tmp_path / scan.name)
    truncated = tmp_path / scans[1].name
    data = truncated.read_bytes()
    truncated.write_bytes(data[: len(data) // 2])  # as an interrupted download leaves it

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    _row(dialog, "3860258481").child(0).setCheckState(0, Qt.Checked)
    dialog.finalize()

    assert dialog.result() == 0
    window = dialog.observations[0].windows[0]
    assert dialog.progress.format().startswith(f"Loading {window} from {truncated.name} failed:")


def test_raster_load_failure_of_files_that_load_alone_names_how_many(qtbot, tmp_path, monkeypatch, irispy_test_files):
    def fail(_sequence):
        raise ValueError("the scans differ")

    monkeypatch.setattr("glue_solar.sources.loaders.iris.stack_spectrogram_sequence", fail)
    for scan in sorted(path for path in irispy_test_files if "3860258481_raster_t000_r0000" in path.name)[:2]:
        shutil.copy2(scan, tmp_path / scan.name)

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    _row(dialog, "3860258481").child(0).setCheckState(0, Qt.Checked)
    dialog.stack.setChecked(True)
    dialog.finalize()

    window = dialog.observations[0].windows[0]
    assert dialog.progress.format() == f"Loading {window} from 2 raster files failed: the scans differ"


@pytest.mark.remote_data
def test_negative_step_raster_keeps_irispys_orientation(qtbot, irispy_data):
    # D10: a STEPS_AV < 0 raster keeps irispy's orientation, unflipped, and longitude grows with step
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.image import ImageViewer

    [path] = irispy_data("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz")
    [scan] = raster_data([path], ["Mg II k 2796"])
    [stack] = raster_data([path, path], ["Mg II k 2796"], stack=True)
    assert scan.meta["STEPS_AV"] < -0.01
    row = scan.shape[1] // 2

    longitude = scan[scan.id["Helioprojective Longitude"]][:, row, 0]
    with fits.open(path) as hdul:  # the per-step FOV centre, stored in acquisition order
        aux = hdul[hdul[0].header["NWIN"] + 1]
        np.testing.assert_allclose(longitude, aux.data[::-1, aux.header["XCENIX"]], atol=0.01)
    assert longitude[[0, 63]] == pytest.approx([-970.73, -907.89], abs=0.01)
    assert (np.diff(longitude) > 0).all()
    for i in range(2):  # every scan of the stack keeps scan 0's orientation
        np.testing.assert_array_equal(stack[stack.id["Helioprojective Longitude"]][i, :, row, 0], longitude)
    times = scan["Time"][:, 0, 0]
    assert (np.diff(times) < np.timedelta64(0, "s")).all()  # acquired from the last step to the first
    assert np.datetime_as_string(times[[0, 63]], unit="s").tolist() == ["2025-03-28T23:06:15", "2025-03-28T22:56:32"]

    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(scan)
    viewer = app.new_data_viewer(ImageViewer, data=scan)
    viewer.state.x_att, viewer.state.y_att = scan.pixel_component_ids[0], scan.pixel_component_ids[1]
    assert viewer.state.x_min < viewer.state.x_max  # unflipped: step, and so longitude, grows to the right
    viewer.figure.canvas.draw()  # WCSAxes only formats positions once drawn
    assert '−971"' in viewer.axes.format_coord(0, row)
    assert '−908"' in viewer.axes.format_coord(63, row)
