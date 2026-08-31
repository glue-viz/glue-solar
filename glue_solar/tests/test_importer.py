import shutil

import numpy as np
import pytest
from irispy.io import read_files
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.io import fits

from glue_solar.conftest import MD5, OBS_A, OBS_B, OBS_C
from glue_solar.sources.loaders.iris import QtIRISImporter, image_data, raster_data
from glue_solar.sources.loaders.stack_spectrograms import stack_spectrogram_sequence


@pytest.fixture
def dialog(qtbot, iris_tree):
    dlg = QtIRISImporter(iris_tree)
    qtbot.addWidget(dlg)
    return dlg


def _row(dialog, obsid):
    tree = dialog.obs_tree
    return next(tree.topLevelItem(i) for i in range(tree.topLevelItemCount()) if tree.topLevelItem(i).text(1) == obsid)


def _real(files, name):
    return next(path for path in files if path.name == name)


def test_tree_lists_observations_and_files(dialog):
    assert dialog.obs_tree.topLevelItemCount() == 4
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


def test_ticking_the_observation_ticks_its_files(dialog):
    row = _row(dialog, OBS_A[2])
    row.setCheckState(0, Qt.Checked)
    assert len(dialog.selected()) == 4


def test_load_selected_real_sji(qtbot, tmp_path, irispy_test_files):
    source = _real(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000_test.fits")
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


def test_real_sji_adapter_preserves_mask_units_and_coordinates(irispy_test_files):
    path = _real(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000_test.fits")
    cube = read_files(path, memmap=False, uncertainty=False)
    data = image_data(path)

    science, mask = data.main_components
    assert data.shape == cube.shape
    assert data.get_component(science).units == str(cube.unit)
    np.testing.assert_array_equal(data.get_component(mask).data, cube.mask)

    longitude = next(component for component in data.world_component_ids if component.label == "Longitude")
    expected = cube.axis_world_coords()[0][0, 0, 0].Tx.to_value(u.arcsec)
    assert data.get_component(longitude).units == "arcsec"
    assert data.get_component(longitude).data[0, 0, 0] == pytest.approx(expected)
    assert np.nanmax(np.abs(data.get_component(longitude).data)) < 180 * 3600
    world = data.coords.pixel_to_world_values(0, 0, 0)
    assert data.coords.world_to_pixel_values(*world) == pytest.approx((0, 0, 0), abs=1e-8)


def test_aia_cube_uses_the_same_irispy_adapter(tmp_path, irispy_test_files):
    source = _real(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000_test.fits")
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
    assert len(data.main_components) == 2


def test_real_raster_preserves_exact_exposure_times(irispy_test_files):
    path = _real(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000_test.fits")
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
    assert len(data[0].main_components) == 3


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
    raw_last[sequence[-1].mask] = np.nan
    assert data.shape == (len(paths), 8, 109, 17)
    assert [c.label for c in data.world_component_ids][0] == "Scan"
    assert data.coords.world_axis_units == ("m", "arcsec", "arcsec", "")
    np.testing.assert_array_equal(values[-1], raw_last)
    np.testing.assert_array_equal(data.get_component(mask).data, ~np.isfinite(values))
    for i, expected in enumerate(expected_times):
        np.testing.assert_array_equal(times[i, :, 0, 0], expected)
        np.testing.assert_array_equal(times[i, :, -1, -1], expected)
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
        if physical_type.startswith("custom:pos.helioprojective."):
            expected = (expected * u.Unit(unit)).to_value(u.arcsec)
        np.testing.assert_allclose(actual, expected)
    for actual, expected in zip(
        data.coords.world_to_pixel_values(*stacked_world),
        (wavelength, slit, step, np.zeros_like(wavelength)),
    ):
        np.testing.assert_allclose(actual, expected, atol=3e-6)

    with pytest.raises(ValueError, match="same shape"):
        stack_spectrogram_sequence([sequence[0], sequence[1][:-1]], memmap=False)


def test_duplicate_real_raster_is_listed_and_loaded_once(qtbot, tmp_path, irispy_test_files):
    source = _real(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000_test.fits")
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


def test_reader_failure_stays_in_dialog(qtbot, tmp_path):
    path = tmp_path / "iris_l2_20240101_000000_1234567890_SJI_1400_t000.fits"
    fits.PrimaryHDU(
        header=fits.Header(
            {
                "TELESCOP": "IRIS",
                "INSTRUME": "SJI",
                "OBSID": "1234567890",
                "STARTOBS": "2024-01-01T00:00:00",
                "TDESC1": "SJI_1400",
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
    assert dialog.progress.format().startswith("Loading SJI_1400 failed:")
