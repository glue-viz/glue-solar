import shutil

import numpy as np
import pytest
from glue.core import Data, DataCollection, component_link, coordinate_helpers
from glue.core.exceptions import IncompatibleAttribute
from glue.core.link_helpers import LinkSame
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue.plugins.wcs_autolinking.wcs_autolinking import IncompatibleWCS, WCSLink
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.wcs.wcsapi import HighLevelWCSWrapper

from glue_solar import glue_patches
from glue_solar.sources.iris import browse_iris, link_iris
from glue_solar.sources.loaders.iris import QtIRISImporter, image_data, keep_hpc_linked, link_hpc, raster_data

SJI = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
RASTER = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
HPC = ["Helioprojective Longitude", "Helioprojective Latitude"]


def _real(files, name):
    return next(
        path for path in files if path.name.replace("_test.fits", ".fits") == name and path.parent.name == "sns"
    )


def _cid(data, label):
    return next(cid for cid in data.world_component_ids if cid.label == label)


@pytest.fixture
def sns(irispy_test_files):
    """The matched sit-and-stare SJI 1400 + Si IV 1403 raster pair shipped with irispy."""
    [raster] = raster_data([_real(irispy_test_files, RASTER)], ["Si IV 1403"])
    return image_data(_real(irispy_test_files, SJI)), raster


def test_sji_and_raster_share_axis_names(sns):
    sji, raster = sns
    assert [c.label for c in sji.world_component_ids] == ["Time (Utc)", *HPC[::-1]]
    assert [c.label for c in raster.world_component_ids] == [*HPC, "Wavelength"]
    assert [c.label for c in sji.components].count("Time") == 1


def test_link_editor_wcs_link_works_or_refuses_cleanly(sns, irispy_test_files):
    # The link editor's "WCS link" between IRIS datasets raised AttributeError: 'has_celestial'
    sji, raster = sns
    sji_2796 = image_data(_real(irispy_test_files, SJI.replace("1400", "2796")))
    DataCollection([sji, raster, sji_2796]).add_link(WCSLink(sji, sji_2796))
    assert [sji[cid][3, 20, 10] for cid in sji_2796.pixel_component_ids[1:]] == pytest.approx([20, 10], abs=0.01)
    try:
        link = WCSLink(sji, raster)
    except IncompatibleWCS:  # glue-core 1.27.0: SJI and raster share only lon/lat, which link_hpc links
        return
    # glue-viz/glue#2595 links the SJI image axes to the raster's step and slit
    assert {cid.axis for cid in link.cids1} == {1, 2}
    assert {cid.axis for cid in link.cids2} == {0, 1}


def test_sji_high_level_api_round_trips(sns):
    sji, _ = sns
    pixel = (10, 10, 5)
    wcs = HighLevelWCSWrapper(sji.coords)
    objects = wcs.pixel_to_world(*pixel)
    values = sji.coords.pixel_to_world_values(*pixel)
    types = list(sji.coords.world_axis_physical_types)
    sky = next(o for o in objects if hasattr(o, "Tx"))
    assert sky.Tx.to_value(u.arcsec) == pytest.approx(values[types.index("custom:pos.helioprojective.lon")])
    assert sky.Ty.to_value(u.arcsec) == pytest.approx(values[types.index("custom:pos.helioprojective.lat")])
    assert wcs.world_to_pixel(*objects) == pytest.approx(pixel, abs=1e-4)


def test_inverse_workaround_installs_only_where_glue_needs_it():
    installed = component_link.world2pixel_single_axis is glue_patches.world2pixel_single_axis
    assert installed == glue_patches.needs_inverse_workaround()  # probes glue's own function
    assert coordinate_helpers.world2pixel_single_axis is component_link.world2pixel_single_axis
    assert not glue_patches.needs_inverse_workaround(glue_patches.world2pixel_single_axis)


def test_world_links_into_the_sji_use_each_exposure_time(sns):
    # glue-core 1.27.0 inverts every frame at exposure 0: x = 22.4 and 35.4 px at frames 30 and 61
    sji, _ = sns
    frames = np.arange(sji.shape[0], dtype=float)
    lon, lat, time = sji.coords.pixel_to_world_values(10.0, 10.0, frames)
    points = Data(label="points", lon=lon, lat=lat, t=time)
    dc = DataCollection([sji, points])
    dc.add_link(
        [LinkSame(points.id[k], _cid(sji, label)) for k, label in zip("lon lat t".split(), [*HPC, "Time (Utc)"])]
    )
    np.testing.assert_allclose(points[sji.pixel_component_ids[2]], 10, atol=1e-6)
    np.testing.assert_allclose(points[sji.pixel_component_ids[1]], 10, atol=1e-6)
    np.testing.assert_allclose(points[sji.pixel_component_ids[0]], frames, atol=1e-6)


def test_inverse_workaround_leaves_wcsaxes_readouts_alone(qtbot, sns, monkeypatch):
    sji, _ = sns
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(sji)
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    viewer.state.slices = (30, 0, 0)
    readouts = []
    for patch in (glue_patches.world2pixel_single_axis, glue_patches._original_world2pixel_single_axis):
        monkeypatch.setattr(coordinate_helpers, "world2pixel_single_axis", patch)
        monkeypatch.setattr(component_link, "world2pixel_single_axis", patch)
        viewer.figure.canvas.draw()  # WCSAxes only formats positions once drawn
        readouts.append([viewer.axes.format_coord(x, 20) for x in (0, 10, 30)])
    assert readouts[0] == readouts[1]


@pytest.fixture
def linked_sns(sns):
    dc = DataCollection(list(sns))
    dc.add_link(link_hpc(dc))
    return sns


def test_link_hpc_pairs_longitude_and_latitude_only(sns):
    sji, raster = sns
    dc = DataCollection([sji, raster])
    links = link_hpc(dc)
    assert all(isinstance(link, LinkSame) for link in links)
    # nothing links the SJI's time, so each SJI frame is placed with its own pointing
    assert sorted((link.cids1[0].label, link.cids2[0].label) for link in links) == [(HPC[1], HPC[1]), (HPC[0], HPC[0])]
    dc.add_link(LinkSame(_cid(raster, HPC[0]), _cid(sji, HPC[0])))  # as made by hand in the link editor
    link_iris(None, dc)  # the menu action adds only the missing pair
    assert len(dc.external_links) == 2
    assert link_hpc(dc) == []
    for label in HPC:
        np.testing.assert_allclose(raster[_cid(sji, label)], raster[_cid(raster, label)])
    for source, target in ((sji, raster), (raster, sji)):  # world subsets carry over both ways
        lon = _cid(source, HPC[0])
        assert 0 < target.get_mask(lon > float(np.nanmedian(source[lon]))).sum() < target.size
    # an SJI pixel subset needs the time of an SJI frame, which the raster does not have
    sji_roi = RoiSubsetState(
        xatt=sji.pixel_component_ids[2], yatt=sji.pixel_component_ids[1], roi=RectangularROI(10, 25, 10, 30)
    )
    with pytest.raises(IncompatibleAttribute):
        raster.get_mask(sji_roi)


def test_link_hpc_links_every_iris_dataset_to_the_first(qtbot, sns, irispy_test_files):
    import sunpy.data.test
    import sunpy.map

    from glue_solar.sources.maps import _parse_sunpy_map

    sji, raster = sns
    [other] = raster_data([_real(irispy_test_files, RASTER)], ["C II 1336"])
    aia = _parse_sunpy_map(sunpy.map.Map(sunpy.data.test.get_test_filepath("aia_171_level1.fits")), "aia")
    assert set(aia.coords.world_axis_units) == {"deg"}
    dc = DataCollection([sji, raster, aia, other])
    links = link_hpc(dc)
    assert len(links) == 4  # never degrees to arcsec
    assert {link.cids1[0] for link in links} == {_cid(sji, label) for label in HPC}
    keep_hpc_linked(dc)
    dc.remove(sji)  # the others were linked through it
    qtbot.waitUntil(lambda: len(dc.external_links) == 2)
    np.testing.assert_allclose(other[_cid(raster, HPC[1])], other[_cid(other, HPC[1])])
    dc.clear()  # one relink after all the removals, with nothing left to link
    qtbot.wait(10)
    assert not dc.external_links


@pytest.mark.parametrize("frame", [0, -1])
def test_raster_map_roi_selects_the_sji_pixels_inside_it(linked_sns, frame):
    # Each SJI frame's own coordinates decide, so the selection follows that frame's pointing
    sji, raster = linked_sns
    roi = RectangularROI(80, 100, 10.3, 19.8)  # raster steps and slit rows, edges off the SJI pixel grid
    mask = sji.get_mask(
        RoiSubsetState(xatt=raster.pixel_component_ids[0], yatt=raster.pixel_component_ids[1], roi=roi)
    )[frame]
    y, x = np.indices(mask.shape)
    lon, lat, _ = sji.coords.pixel_to_world_values(x, y, frame % sji.shape[0])
    wavelength = np.full(lon.shape, raster.coords.pixel_to_world_values(0, 0, 0)[0])
    _, slit, step = raster.coords.world_to_pixel_values(wavelength, lat, lon)
    (x, y), half_width, half_height = roi.center(), roi.width() / 2, roi.height() / 2

    def inside(margin):
        return (abs(step - x) < half_width + margin) & (abs(slit - y) < half_height + margin)

    expected, edge = inside(0), inside(0.05) != inside(-0.05)
    assert expected.sum() >= 10
    assert edge.sum() <= expected.sum() // 10
    np.testing.assert_array_equal(mask[~edge], expected[~edge])


def test_browse_iris_links_what_it_loads(qtbot, tmp_path, irispy_test_files, monkeypatch):
    for name in (SJI, SJI.replace("1400", "2796"), RASTER):
        shutil.copy2(_real(irispy_test_files, name), tmp_path / name)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    # glue-qt asks in a modal dialog whenever glue suggests links; this test is about link_hpc
    monkeypatch.setattr("glue_qt.app.application.run_autolinker", lambda data_collection: None)

    def tick_everything_and_load(dialog):
        dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
        dialog.finalize()
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtIRISImporter, "exec", tick_everything_and_load)
    app = GlueApplication()
    qtbot.addWidget(app)
    dc = app.data_collection
    browse_iris(app.session, dc)
    assert len(dc) > 3  # two SJIs and every raster window
    assert len(dc.external_links) == 2 * (len(dc) - 1)  # longitude and latitude of each to the first
    assert {cid.label for link in dc.external_links for cid in (*link.cids1, *link.cids2)} == set(HPC)
    dc.append(image_data(_real(irispy_test_files, SJI.replace("1400", "1330"))))  # loaded later
    link_iris(app.session, dc)
    assert len(dc.external_links) == 2 * (len(dc) - 1)
