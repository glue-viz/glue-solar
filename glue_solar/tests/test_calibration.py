"""
'IRIS: remove dust' and 'IRIS: radiometric calibration', on int16 copies of irispy's test files and irispy-data
files: what glue gets of irispy's own calls.
"""

import glue.config
import numpy as np
import pytest
from glue.core import Data
from irispy.io.sji import read_sji_lvl2
from irispy.io.spectrograph import read_spectrograph_lvl2
from irispy.utils.dust import remove_dust as irispy_remove_dust
from irispy.utils.spectrograph import radiometric_calibration as irispys_calibration
from qtpy import QtWidgets

from astropy.io import fits

import glue_solar
from glue_solar.conftest import find_irispy_test_file, int16_copy
from glue_solar.regrid import rebin, regrid_on_time
from glue_solar.sources import calibration
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.helpers import refused, restore
from glue_solar.tests.test_bursts import SJI_1400

DUST = "IRIS: remove dust"
RADIANCE = "IRIS: radiometric calibration"


@pytest.fixture
def sji_path(tmp_path, irispy_test_files):
    """
    4000255147's SJI 1400, 3 frames, stored as int16: lazy in glue; saturated, raw 32760, across the edge of its dust
    at (1, 319, 295) and in a block away from it; frame 0's slit moved 3 pixels right, so part of each frame's dust is
    replaced from the other frames; irispy's cutouts of 3620258102 hold no dust of its bad-pixel table.
    """
    path = int16_copy(find_irispy_test_file(irispy_test_files, SJI_1400), tmp_path / SJI_1400, [0])
    with fits.open(path, mode="update", do_not_scale_image_data=True) as hdulist:
        hdulist[0].data[1, 317:321, 295] = hdulist[0].data[0, 200:203, 200:203] = 32760
        hdulist[1].data[0, hdulist[1].header["SLTPX1IX"]] += 3
    return path


def assert_irispys_dust_removed(dust, path):
    """
    ``dust`` is irispy's ``remove_dust`` of ``path`` read in memory, masked where irispy masks it: NaN, or saturated
    at its value (D85).
    """
    cube = read_sji_lvl2(path, memmap=False, uncertainty=False)
    direct = irispy_remove_dust(cube)
    [cid, mask] = dust.main_components[:2]
    values, kept = dust[cid], ~direct.mask
    np.testing.assert_array_equal(dust[mask], direct.mask)
    shown = direct.mask & (direct.data >= 16182)  # saturated, by irispy's read rather than glue's values
    np.testing.assert_array_equal(values[shown], direct.data[shown])
    np.testing.assert_allclose(values[kept], direct.data[kept], rtol=1e-6, atol=0)
    assert (direct.data[kept] != cube.data[kept]).sum() > 100  # dust replaced


def test_the_action_adds_irispys_dust_removed_slit_jaw_image_linked_and_no_viewer(
    app, qtbot, monkeypatch, sji_path, scan_path
):
    monkeypatch.setattr(calibration, "SLAB", 417 * 388)  # slabs of 1 frame, each with 2 on either side
    sji = image_data(sji_path)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection, tree = app.data_collection, app._layer_widget
    collection.extend([raster, sji])
    keep_hpc_linked(collection)
    tree.ui.layerTree.set_selected_layers([sji])
    assert tree._actions[DUST].isVisible()
    tree._actions[DUST].trigger()
    assert iris._RUNNING  # on glue-qt's worker
    assert app.statusBar().currentMessage() == f"Removing dust from {sji.label}…"
    qtbot.waitUntil(lambda: len(collection) == 3 and not iris._RUNNING, timeout=60000)  # irispy on a slow runner
    assert app.statusBar().currentMessage() == ""
    dust = collection[-1]
    label = f"{sji.label} dust removed"
    assert dust.label == label
    name = sji.main_components[0].label  # its values', as the slit-jaw image's
    assert [(cid.label, dust.get_component(cid).units) for cid in dust.main_components] == [
        (name, "DN_IRIS_SJI_1400"),  # its passband's DN, as irispy reads it
        (f"{name} mask", ""),
        ("Time", ""),
        ("Exposure time", "s"),
    ]
    assert dust.get_component(f"{name} DN / s").units == "DN / s"
    assert_irispys_dust_removed(dust, sji_path)
    assert not any(app.viewers)
    assert tree.ui.layerTree.selected_layers() == [dust]
    assert not tree._actions[DUST].isVisible()  # its dust removed already
    # the slit-jaw image's coordinates, times and per-frame pointing, its helioprojective ones linked
    assert dust.coords._wcs is sji.coords._wcs
    for cid, sji_cid in zip(dust.world_component_ids, sji.world_component_ids):
        np.testing.assert_array_equal(dust[cid], sji[sji_cid])
    for name in ("Time", "Exposure time"):
        np.testing.assert_array_equal(dust[name], sji[name])
    assert {key: dust.meta[key] for key in ("INSTRUME", "TWAVE1", "dust_removed")} == {
        "INSTRUME": "SJI",
        "TWAVE1": 1400.0,
        "dust_removed": True,
    }
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
    radiance, factor = raster.id[f"{cid.label} radiance"], raster.id[f"{cid.label} radiance per DN / s"]
    assert raster.get_component(radiance).units == "erg / (Angstrom s sr cm2)"
    assert raster.get_component(factor).units == "erg / (Angstrom DN sr cm2)"
    assert not any(raster.get_component(factor).data.strides[:-1])  # one spectrum held
    direct = irispys_calibration(read_spectrograph_lvl2(path, spectral_windows=[window], memmap=False)[window][0])
    values, kept = raster[radiance], ~direct.mask
    np.testing.assert_array_equal(np.isnan(values), direct.mask)
    np.testing.assert_allclose(values[kept], direct.data[kept], rtol=1e-6, atol=0)


def test_a_calibrated_session_is_kept_and_restores_the_radiance(app, qtbot, monkeypatch, tmp_path, scan_path):
    """
    The calibration of the nine windows of 3860258481's scan grows the session glue-solar keeps as glue closes by under
    0.1 MB, not by their factors' 1.3 MB of float64 values, over the 1 MB it keeps, and the session restores each
    factor as one spectrum held and the same radiance (D75).
    """
    monkeypatch.setattr(glue.config, "CFG_DIR", str(tmp_path))  # glue's settings folder, not the user's
    windows = raster_data([scan_path])
    app.data_collection.extend(windows)
    app.save_session(str(tmp_path / "before.glu"))
    radiances = [calibration.radiometric_calibration(data) for data in windows]
    app.show()
    glue_solar._save_last_session(app)  # as glue's window closes
    last = tmp_path / "glue-solar-last-session.glu"
    assert last.stat().st_size - (tmp_path / "before.glu").stat().st_size < 1e5
    restored = restore(qtbot, monkeypatch, last)
    for data, back, radiance in zip(windows, restored.data_collection, radiances, strict=True):
        factor = back.get_component(f"{radiance.label} per DN / s")
        assert factor.units == "erg / (Angstrom DN sr cm2)"
        assert not any(factor.data.strides[:-1])
        np.testing.assert_array_equal(back[radiance.label], data[radiance])


def test_a_stacks_radiance_is_each_scans_own(app, stack_paths):
    """
    The action's ``<label> radiance`` of a lazy stack of 3860258481's three scans is, at each scan, that of the scan
    loaded alone within 0.2%: its factor a spectrum a scan, at the scan's own wavelengths, the stack's first date.
    """
    [stack] = raster_data(stack_paths, ["Mg II k 2796"], stack=True)
    app.data_collection.append(stack)
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([stack])
    tree._actions[RADIANCE].trigger()
    cid = stack.main_components[0]
    radiance, factor = stack.id[f"{cid.label} radiance"], stack.id[f"{cid.label} radiance per DN / s"]
    assert not any(stack.get_component(factor).data.strides[1:-1])  # a spectrum a scan held
    assert len({tuple(spectrum) for spectrum in stack[factor][:, 0, 0]}) == 1  # the scans share their wavelengths
    for k, path in enumerate(stack_paths):
        [scan] = raster_data([path], ["Mg II k 2796"])
        alone = calibration.radiometric_calibration(scan)
        # the response at the stack's first date rather than the scan's own: the effective area changes by at most
        # 0.12% in 10 hours
        np.testing.assert_allclose(stack[radiance][k], scan[alone], rtol=0 if k == 0 else 2e-3, atol=0)


@pytest.mark.parametrize(("axis", "first"), [(0, 1), (1, 2), (2, 1)])
def test_a_stack_whose_scans_cdelt_differ_is_refused_naming_the_first(app, monkeypatch, stack_paths, axis, first):
    """
    A stack of 3860258481's three scans, or that stack rebinned, with CDELT1, 2 or 3 of scans 1 and 2, or of scan 2
    alone, changed in memory, is not offered the calibration, and glue says why, naming the first scan that differs:
    every scan's factor takes scan 0's spectral dispersion and solid angle.
    """
    [stack] = raster_data(stack_paths, ["Mg II k 2796"], stack=True)
    rebinned = rebin(stack, (1, 1, 2, 1))
    collection = app.data_collection
    collection.extend([stack, rebinned])
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([stack])
    assert tree._actions[RADIANCE].isVisible()  # offered while the scans' CDELT1-3 are alike
    for wcs in stack.coords._wcs._wcses[first:]:  # each scan's own FITS WCS (stack_wcs)
        cdelt = wcs.wcs.cdelt.copy()
        cdelt[axis] *= 1.001
        wcs.wcs.cdelt = cdelt
    shown, components = [], [len(data.components) for data in (rebinned, stack)]
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    for data in (rebinned, stack):
        tree.ui.layerTree.set_selected_layers([data])
        refused(tree._actions[RADIANCE])
    why = "differ from scan 0's, whose spectral dispersion and solid angle the calibration takes for every scan."
    assert shown == [
        f"Could not calibrate the radiance\nThe pixel sizes (CDELT1-3) of scan {first} of {data.label} {why}"
        for data in (rebinned, stack)
    ]
    assert [len(data.components) for data in (rebinned, stack)] == components  # nothing added


@pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")  # a bin with every sample missing: NaN
@pytest.mark.parametrize("bins", [(2, 2, 1), (1, 1, 2), (1, 2, 3), (2, 1, 1, 2)])
def test_a_rebinned_windows_radiance_is_its_radiance_rebinned(app, scan_path, stack_paths, bins):
    """
    The action's ``<label> radiance`` of 3860258481's C II 1336, or a stack of its scans, rebinned by 'IRIS: rebin…' is
    its radiance rebinned within the factor's change across one bin, as a bin is the mean of the window's pixels: the
    factor, of the window's spectral dispersion and solid angle at each bin's middle, is within 1e-4 of the window's
    mean over the bin.
    """
    stack = len(bins) == 4
    [data] = raster_data(stack_paths if stack else [scan_path], ["C II 1336"], stack=stack)
    rebinned = rebin(data, bins)
    app.data_collection.append(rebinned)
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([rebinned])
    tree._actions[RADIANCE].trigger()
    cid, label = rebinned.main_components[0], data.main_components[0].label
    radiance = data[calibration.radiometric_calibration(data)]
    factor = data[f"{label} radiance per DN / s"]
    covered = tuple(slice(0, n * b) for n, b in zip(rebinned.shape, bins))
    shape = [m for n, b in zip(rebinned.shape, bins) for m in (n, b)]

    def binned(values, operation=np.nanmean):  # as 'IRIS: rebin…' bins them
        return operation(values[covered].reshape(shape), axis=tuple(range(1, len(shape), 2)))

    np.testing.assert_allclose(rebinned[f"{cid.label} radiance per DN / s"], binned(factor, np.mean), rtol=1e-4, atol=0)
    change = (binned(factor, np.max) - binned(factor, np.min)) / binned(factor, np.mean)
    got, expected = rebinned[f"{cid.label} radiance"], binned(radiance)
    np.testing.assert_array_equal(np.isnan(got), np.isnan(expected))
    kept = ~np.isnan(expected)
    # and 1e-5: the rebinned DN / s is a bin's mean DN over its mean exposure time, its steps' 1e-6 apart
    assert np.all(np.abs(got - expected)[kept] <= ((change + 1e-5) * binned(np.abs(radiance)))[kept])


def test_refusals_show_why(app, monkeypatch, sji_path, scan_path):
    sji = image_data(sji_path)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    dust = calibration.remove_dust(sji)
    rebinned = rebin(dust, (1, 2, 2))  # data made from it keep its meta['dust_removed']
    regridded, binned = regrid_on_time(dust), rebin(sji, (1, 2, 2))  # whose pixels irispy cannot place dust in
    collection = app.data_collection
    collection.extend([sji, raster, plain, dust, rebinned, regridded, binned])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    for action, datasets in ((DUST, (raster, plain, dust, rebinned, regridded, binned)), (RADIANCE, (sji, plain))):
        for data in datasets:
            tree.ui.layerTree.set_selected_layers([data])
            refused(tree._actions[action])
    tree.ui.layerTree.set_selected_layers([raster])
    tree._actions[RADIANCE].trigger()
    refused(tree._actions[RADIANCE])  # calibrated already: hidden at once, the row still selected
    assert not iris._RUNNING  # no thread started
    assert shown == [
        f"Could not remove dust\n{raster.label} is not an IRIS slit-jaw image.",
        "Could not remove dust\nplain is not an IRIS slit-jaw image.",
        f"Could not remove dust\n{dust.label} has its dust removed already.",
        f"Could not remove dust\n{rebinned.label} has its dust removed already.",
        f"Could not remove dust\n{regridded.label} has its dust removed already.",
        f"Could not remove dust\n{binned.label} is rebinned or regridded: irispy finds dust in the pixels of a file only.",
        f"Could not calibrate the radiance\n{sji.label} is not an IRIS raster window.",
        "Could not calibrate the radiance\nplain is not an IRIS raster window.",
        f"Could not calibrate the radiance\n{raster.label} has its radiance already.",
    ]
    assert len(collection) == 7
