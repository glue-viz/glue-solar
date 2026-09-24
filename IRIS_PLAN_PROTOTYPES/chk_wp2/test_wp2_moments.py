import numpy as np
import pytest
from glue.core import DataCollection
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue_qt.config import layer_action
from qtpy import QtWidgets

from glue_solar.sources.loaders.iris import image_data, raster_data
from wp2_moments_module import MomentsDialog, line_moments  # ships as glue_solar.sources.moments

SNS_RASTER = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
IN_WINDOW_REST = "2794.09"  # the test window spans 2793.44-2794.74 A; TWAVE (2796.20 A) lies outside it


@pytest.fixture(scope="session")
def irispy_test_files():
    from irispy.data.test import get_test_data_filenames

    return get_test_data_filenames()


@pytest.fixture
def raster(irispy_test_files):
    path = next(p for p in irispy_test_files if p.name == SNS_RASTER and p.parent.name == "sns")  # listed twice
    return raster_data([path], ["Mg II k 2796"])[0]


def test_action_is_registered():
    assert "IRIS: line moments…" in [item.label for item in layer_action]


def test_dialog_adds_one_linked_moments_dataset(qtbot, raster):
    dc = DataCollection([raster])
    dialog = MomentsDialog(raster, dc)
    qtbot.addWidget(dialog)
    assert dialog.rest.text() == "2796.20"  # prefilled from TWAVE
    dialog.rest.setText(IN_WINDOW_REST)
    dialog.low.setText("0.5")
    dialog.high.setText("0.5")
    dialog.minimum.setText("50")
    dialog.run()

    assert dialog.result() == QtWidgets.QDialog.Accepted
    assert [d.label for d in dc] == [raster.label, f"{raster.label}-moments"]
    maps = dc[1]
    assert maps.shape == raster.shape[:2]
    assert [(c.label, maps.get_component(c).units) for c in maps.main_components] == [
        ("intensity", "DN_IRIS_NUV"),
        ("intensity mask", ""),
        ("centroid", "Angstrom"),
        ("width", "Angstrom"),
        ("velocity", "km / s"),
        ("velocity_width", "km / s"),
        ("Time", ""),
    ]
    assert [c.label for c in maps.world_component_ids] == ["Helioprojective Longitude", "Helioprojective Latitude"]
    assert maps.coords.world_axis_units == ("arcsec", "arcsec")
    intensity, velocity = maps["intensity"], maps["velocity"]
    assert np.isfinite(velocity[intensity > 50]).all()
    assert np.isnan(velocity[~(intensity > 50)]).all()
    assert abs(np.nanmedian(velocity)) < 20  # rest wavelength inside the window: no bulk offset
    np.testing.assert_array_equal(maps["Time"], raster["Time"][..., 0])

    assert len(dc.external_links) == 2
    dc.new_subset_group(
        "map roi", RoiSubsetState(xatt=maps.pixel_component_ids[1], yatt=maps.pixel_component_ids[0], roi=RectangularROI(10, 30, 2, 5))
    )
    assert maps.subsets[0].to_mask().sum() == 38
    assert raster.subsets[0].to_mask().sum() == 38 * raster.shape[2]


def test_failure_keeps_dialog_open(qtbot, raster, monkeypatch):
    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args: shown.append(args[2]))
    dc = DataCollection([raster])
    dialog = MomentsDialog(raster, dc)
    qtbot.addWidget(dialog)
    dialog.rest.setText("3000")
    dialog.low.setText("0.1")
    dialog.high.setText("0.1")
    dialog.run()
    assert shown == ["No wavelength points found within the specified wings"]
    assert dialog.result() == 0
    assert len(dc) == 1
    dialog.rest.setText(IN_WINDOW_REST)
    dialog.high.clear()
    dialog.run()
    assert shown[-1].startswith("Enter both wings")
    assert len(dc) == 1


def test_integrated_zeroth_moment_is_dn_angstrom(raster):
    summed = line_moments(raster)
    maps = line_moments(raster, integrated=True, min_intensity=50)
    assert maps.get_component(maps.id["intensity"]).units == "Angstrom DN_IRIS_NUV"
    integrated = summed["intensity"] * 0.02546  # the window's wavelength step in Angstrom
    finite = np.isfinite(maps["intensity"])
    assert finite.sum() == (integrated >= 50).sum()  # the threshold is applied in DN Angstrom, not DN nm
    np.testing.assert_allclose(maps["intensity"][finite], integrated[finite], rtol=1e-3)


def test_stack_and_sji_are_rejected(irispy_test_files):
    scans = sorted(p for p in irispy_test_files if "20140329_140938_3860258481_raster_t000_r" in p.name)
    stack = raster_data(scans, ["Mg II k 2796"], stack=True)[0]
    sji = image_data(next(p for p in irispy_test_files if p.name == "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"))
    for data in (stack, sji):
        with pytest.raises(ValueError, match="per-scan raster window"):
            line_moments(data)
