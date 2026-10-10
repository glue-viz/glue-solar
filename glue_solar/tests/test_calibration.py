"""
'IRIS: remove dust' and 'IRIS: radiometric calibration', on int16 copies of irispy's test files and irispy-data
files: what glue gets of irispy's own calls.
"""

import numpy as np
import pytest
from glue.core import Data
from glue_qt.app.application import GlueApplication
from irispy.io.sji import read_sji_lvl2
from irispy.io.spectrograph import read_spectrograph_lvl2
from irispy.utils.spectrograph import radiometric_calibration as irispys_calibration
from qtpy import QtWidgets

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.sources import calibration
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.test_lazy import SJI, int16_copy, int16_raster_copy
from glue_solar.tests.test_quicklook import SCAN

DUST = "IRIS: remove dust"
RADIANCE = "IRIS: radiometric calibration"


@pytest.fixture
def app(qtbot):
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    return app


@pytest.fixture
def sji_path(tmp_path, irispy_test_files):
    """3620258102's SJI 1400, 62 frames, stored as int16: lazy in glue."""
    return int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0])


@pytest.fixture
def scan_path(tmp_path, irispy_test_files):
    return int16_raster_copy(find_irispy_test_file(irispy_test_files, SCAN), tmp_path / SCAN)


@pytest.fixture
def stack_paths(tmp_path, irispy_test_files):
    """The three scans of 3860258481, stored as int16."""
    files = sorted(p for p in irispy_test_files if "3860258481_raster" in p.name)
    return [int16_raster_copy(p, tmp_path / p.name) for p in files]


def assert_irispys_dust_removed(dust, path):
    """``dust`` is irispy's ``remove_dust`` of ``path`` read in memory, NaN where irispy masks it."""
    cube = read_sji_lvl2(path, memmap=False, uncertainty=False)
    direct = cube.remove_dust()
    values, kept = dust[dust.main_components[0]], ~direct.mask
    np.testing.assert_array_equal(np.isnan(values), direct.mask)
    np.testing.assert_allclose(values[kept], direct.data[kept], rtol=1e-6, atol=0)
    assert (direct.data[kept] != cube.data[kept]).sum() > 1000  # dust replaced


def test_the_action_adds_irispys_dust_removed_slit_jaw_image_linked_and_no_viewer(
    app, qtbot, monkeypatch, sji_path, scan_path
):
    monkeypatch.setattr(calibration, "SLAB", 5 * 40 * 37)  # slabs of 5 frames, each with 2 on either side
    sji = image_data(sji_path)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection, tree = app.data_collection, app._layer_widget
    collection.extend([raster, sji])
    keep_hpc_linked(collection)
    tree.ui.layerTree.set_selected_layers([sji])
    tree._actions[DUST].trigger()
    assert iris._RUNNING  # on glue-qt's worker
    assert app.statusBar().currentMessage() == f"Removing dust from {sji.label}…"
    qtbot.waitUntil(lambda: len(collection) == 3 and not iris._RUNNING)
    assert app.statusBar().currentMessage() == ""
    dust = collection[-1]
    label = f"{sji.label} dust removed"
    assert dust.label == label
    assert [(cid.label, dust.get_component(cid).units) for cid in dust.main_components] == [
        (label, "DN_IRIS_SJI"),
        (f"{label} mask", ""),
        ("Time", ""),
        ("Exposure time", "s"),
    ]
    assert dust.get_component(f"{label} DN/s").units == "DN/s"
    assert_irispys_dust_removed(dust, sji_path)
    assert not any(app.viewers)
    # the slit-jaw image's coordinates, times and per-frame pointing, its helioprojective ones linked
    assert dust.coords._wcs is sji.coords._wcs
    for cid, sji_cid in zip(dust.world_component_ids, sji.world_component_ids):
        np.testing.assert_array_equal(dust[cid], sji[sji_cid])
    for name in ("Time", "Exposure time"):
        np.testing.assert_array_equal(dust[name], sji[name])
    assert {key: dust.meta[key] for key in ("INSTRUME", "TWAVE1")} == {"INSTRUME": "SJI", "TWAVE1": 1400.0}
    np.testing.assert_array_equal(dust.meta["xcenix"], sji.meta["xcenix"])
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(dust.world_component_ids[1:]) <= linked


@pytest.mark.remote_data
def test_a_full_size_slit_jaw_image_gives_irispys_dust_removed(monkeypatch, irispy_data):
    """4000255147's SJI 1400, 50 full-size frames gzipped, held as int16, in slabs of 20 frames."""
    path = irispy_data("iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz")
    monkeypatch.setattr(calibration, "SLAB", 20 * 417 * 388)
    assert_irispys_dust_removed(calibration.remove_dust(image_data(path)), path)


@pytest.mark.parametrize(
    ("which", "window"),
    [
        ("3860258481", "Si IV 1403"),
        ("3860258481", "Mg II k 2796"),
        pytest.param("4000005156", "Si IV 1403", marks=pytest.mark.remote_data),
    ],
)
def test_the_radiance_is_irispys_radiometric_calibration(app, request, which, window):
    """The action's ``<label> radiance``, of an FUV or NUV window, is irispy's calibration of it read in memory."""
    if which == "3860258481":
        path = request.getfixturevalue("scan_path")
    else:
        path = request.getfixturevalue("irispy_data")(
            "iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz"
        )
    [raster] = raster_data([path], [window])
    app.data_collection.append(raster)
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([raster])
    tree._actions[RADIANCE].trigger()
    cid = raster.main_components[0]
    radiance, factor = raster.id[f"{cid.label} radiance"], raster.id[f"{cid.label} radiance per DN/s"]
    assert raster.get_component(radiance).units == "erg / (Angstrom s sr cm2)"
    assert raster.get_component(factor).units == "erg / (Angstrom DN sr cm2)"
    assert not any(raster.get_component(factor).data.strides[:-1])  # one spectrum held
    direct = irispys_calibration(read_spectrograph_lvl2(path, spectral_windows=[window], memmap=False)[window][0])
    values, kept = raster[radiance], ~direct.mask
    np.testing.assert_array_equal(np.isnan(values), direct.mask)
    np.testing.assert_allclose(values[kept], direct.data[kept], rtol=1e-6, atol=0)


def test_a_stacks_radiance_is_each_scans_own(app, stack_paths):
    """
    The action's ``<label> radiance`` of a lazy stack of 3860258481's three scans is, at each scan, that of the scan
    loaded alone, at its own date: its factor a spectrum a scan.
    """
    [stack] = raster_data(stack_paths, ["Mg II k 2796"], stack=True)
    app.data_collection.append(stack)
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([stack])
    tree._actions[RADIANCE].trigger()
    cid = stack.main_components[0]
    radiance, factor = stack.id[f"{cid.label} radiance"], stack.id[f"{cid.label} radiance per DN/s"]
    assert not any(stack.get_component(factor).data.strides[1:-1])  # a spectrum a scan held
    assert len({tuple(spectrum) for spectrum in stack[factor][:, 0, 0]}) == 3  # each at its scan's date
    for k, path in enumerate(stack_paths):
        [scan] = raster_data([path], ["Mg II k 2796"])
        alone = calibration.radiometric_calibration(scan)
        np.testing.assert_array_equal(stack[radiance][k], scan[alone])


def test_refusals_show_why(app, monkeypatch, sji_path, scan_path):
    sji = image_data(sji_path)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    collection = app.data_collection
    collection.extend([sji, raster, plain])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    for action, datasets in ((DUST, (raster, plain)), (RADIANCE, (sji, plain, raster, raster))):
        for data in datasets:
            tree.ui.layerTree.set_selected_layers([data])
            tree._actions[action].trigger()
    assert not iris._RUNNING  # no thread started
    assert shown == [
        f"Could not remove dust\n{raster.label} is not an IRIS slit-jaw image.",
        "Could not remove dust\nplain is not an IRIS slit-jaw image.",
        f"Could not calibrate the radiance\n{sji.label} is not an IRIS raster window.",
        "Could not calibrate the radiance\nplain is not an IRIS raster window.",
        f"Could not calibrate the radiance\n{raster.label} has its radiance already.",
    ]
    assert len(collection) == 3
