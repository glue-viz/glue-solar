import itertools
import shutil
import threading

import numpy as np
import pytest
from glue.core import Data, DataCollection, component_link, coordinate_helpers
from glue.core.autolinking import find_possible_links
from glue.core.component_id import PixelComponentID
from glue.core.component_link import CoordinateComponentLink
from glue.core.exceptions import IncompatibleAttribute
from glue.core.hub import Hub
from glue.core.link_helpers import LinkSame, LinkSameWithUnits
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue.plugins.wcs_autolinking import wcs_autolinking
from glue.plugins.wcs_autolinking.wcs_autolinking import IncompatibleWCS, WCSLink
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
from astropy.wcs.wcsapi import HighLevelWCSWrapper

import glue_solar
from glue_solar import glue_patches
from glue_solar.quicklook import coordinator, nearest, quicklook
from glue_solar.sources.iris import browse_iris, link_iris
from glue_solar.sources.loaders.iris import QtIRISImporter, image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.helpers import load_selected, raster_point_on_sji, select_point

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


def test_wcs_link_between_two_raster_windows(irispy_test_files):
    # glue's "WCS link" raised IncompatibleWCS: its SkyCoord took the arcsec values for degrees
    windows = raster_data([_real(irispy_test_files, RASTER)], ["C II 1336", "Si IV 1403"])
    wrapped = [Data(x=np.zeros(data.shape), coords=data.coords._wcs, label=data.label) for data in windows]
    link, expected = WCSLink(*windows), WCSLink(*wrapped)
    pixel = [np.array([n / 2 + 0.25]) for n in windows[0].shape]
    args = [pixel[cid.axis] for cid in link.cids1]
    assert [cid.axis for cid in expected.cids1] == [cid.axis for cid in link.cids1]
    np.testing.assert_allclose(link.forwards(*args), expected.forwards(*args), rtol=0, atol=1e-9)


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
    assert len(links) == 6
    assert {link.cids1[0] for link in links} == {_cid(sji, label) for label in HPC}
    # the map's degrees to arcsec; IRIS data keep LinkSame, which glue-core 1.27.0 restores from a session and
    # LinkSameWithUnits not
    assert {type(link) for link in links if link.cids2[0].parent is aia} == {LinkSameWithUnits}
    assert {type(link) for link in links if link.cids2[0].parent is not aia} == {LinkSame}
    keep_hpc_linked(dc)
    dc.remove(sji)  # the others were linked through it
    qtbot.waitUntil(lambda: len(dc.external_links) == 4)
    np.testing.assert_allclose(other[_cid(raster, HPC[1])], other[_cid(other, HPC[1])])
    dc.clear()  # one relink after all the removals, with nothing left to link
    qtbot.wait(10)
    assert not dc.external_links


def _sunpy_map(lon, lat, scale, shape, label, rotation=0, obstime="2021-09-05T00:30"):
    """A map of ``shape`` pixels of ``scale``″ around (``lon``, ``lat``)″ seen from Earth, as glue-solar loads one."""
    import sunpy.map
    from sunpy.coordinates import frames

    from glue_solar.sources.maps import _parse_sunpy_map

    center = SkyCoord(lon * u.arcsec, lat * u.arcsec, obstime=obstime, observer="earth", frame=frames.Helioprojective)
    header = sunpy.map.make_fitswcs_header(
        shape, center, scale=[scale, scale] * u.arcsec / u.pix, rotation_angle=rotation * u.deg
    )
    return _parse_sunpy_map(sunpy.map.Map(np.zeros(shape), header), label)


def test_two_overlapping_sunpy_maps_autolink():
    # sunpy maps keep their astropy WCS, so glue's own WCS autolinker links them, through their observers' frames
    first = _sunpy_map(0, 0, 2, (40, 50), "first")
    second = _sunpy_map(10, 5, 1.5, (40, 50), "second", rotation=30, obstime="2021-09-05T01:30")
    assert isinstance(first.coords, WCS)
    dc = DataCollection([first, second])
    assert link_hpc(dc) == []  # it links maps to IRIS data only
    [link] = _autolink(dc)
    assert isinstance(link, WCSLink)
    y, x = np.indices(first.shape)
    expected = second.coords.world_to_pixel(first.coords.pixel_to_world(x, y))
    for cid, values in zip(second.pixel_component_ids[::-1], expected):
        np.testing.assert_allclose(first[cid], values, rtol=0, atol=1e-6)


@pytest.mark.parametrize("frame", [0, -1])
def test_link_hpc_places_a_sunpy_map_on_each_sji_frame(sns, frame):
    # glue converts the map's degrees to the arcsec of IRIS data, and each slit-jaw frame keeps its own pointing
    sji, _ = sns
    lon, lat, _ = sji.coords.pixel_to_world_values(18, 20, sji.shape[0] // 2)
    aia = _sunpy_map(lon, lat, 0.6, (80, 160), "aia", rotation=10, obstime=sji.meta["DATE_OBS"])
    dc = DataCollection([aia, sji])
    links = link_hpc(dc)
    # to the IRIS dataset, though the map came first
    assert [(type(link), link.cids1[0], link.cids2[0]) for link in links] == [
        (LinkSameWithUnits, _cid(sji, label), cid) for label, cid in zip(HPC[::-1], aia.world_component_ids)
    ]
    dc.add_link(links)
    assert link_hpc(dc) == []
    y, x = np.indices(sji.shape[1:])
    lon, lat, _ = sji.coords.pixel_to_world_values(x, y, frame % sji.shape[0])
    expected = aia.coords.world_to_pixel_values((lon * u.arcsec).to_value(u.deg), (lat * u.arcsec).to_value(u.deg))
    for cid, values in zip(aia.pixel_component_ids[::-1], expected):
        np.testing.assert_allclose(sji[cid][frame], values, rtol=0, atol=0.05)


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
        load_selected(qtbot, dialog)
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtIRISImporter, "exec", tick_everything_and_load)
    app = GlueApplication()
    qtbot.addWidget(app)
    dc = app.data_collection
    on_gui, broadcast = [], Hub.broadcast
    monkeypatch.setattr(Hub, "broadcast", lambda hub, message: (
        on_gui.append(threading.current_thread() is threading.main_thread()) or broadcast(hub, message)
    ))
    browse_iris(app.session, dc)
    assert on_gui
    assert all(on_gui)  # glue's hub has no locks: the datasets are added on the GUI thread
    assert len(dc) > 3  # two SJIs and every raster window
    assert len(dc.external_links) == 2 * (len(dc) - 1)  # longitude and latitude of each to the first
    assert {cid.label for link in dc.external_links for cid in (*link.cids1, *link.cids2)} == set(HPC)
    dc.append(image_data(_real(irispy_test_files, SJI.replace("1400", "1330"))))  # loaded later
    link_iris(app.session, dc)
    assert len(dc.external_links) == 2 * (len(dc) - 1)


def _autolink(data_collection):
    """Add every link glue's autolinkers suggest, as glue-qt's run_autolinker does when set to always accept."""
    links = [link for found in find_possible_links(data_collection).values() for link in found]
    data_collection.add_link(links)
    return links


@pytest.mark.parametrize("order", list(itertools.permutations(["autolinker", "link_hpc", "quicklook"])), ids="-".join)
def test_link_graph_in_every_add_order(qtbot, sns, order):
    sji, raster = sns
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    dc = app.data_collection
    dc.extend([sji, raster])
    suggested = []
    for step in order:
        if step == "autolinker":
            suggested = _autolink(dc)
        elif step == "link_hpc":
            dc.add_link(link_hpc(dc))
        else:
            viewers = quicklook(app, [raster, sji])  # with its coordinator; it adds link_hpc's links if missing
    # link_hpc's longitude and latitude, glue's own suggestions, and nothing else
    hpc = [link for link in dc.external_links if link not in suggested]
    assert all(isinstance(link, LinkSame) for link in hpc)
    assert sorted((link.cids1[0].label, link.cids2[0].label) for link in hpc) == [(HPC[1], HPC[1]), (HPC[0], HPC[0])]
    time = _cid(sji, "Time (Utc)")
    for link in dc.links:
        if isinstance(link, CoordinateComponentLink):
            continue  # each dataset's own pixel-world conversions
        cids = [*link.get_from_ids(), link.get_to_id()]
        assert time not in cids
        # only glue's WCS links, from pixel to pixel, reach pixel components (D8)
        assert len({isinstance(cid, PixelComponentID) for cid in cids}) == 1

    # a raster point reaches the other panels, and the slit-jaw image at the nearest frame
    links, components = dc.external_links, [list(data.components) for data in dc]
    sji_times, raster_times = (data[data.id["Time"]][:, 0, 0] for data in (sji, raster))
    [sji_viewer] = viewers["sji"]
    marker = sji_viewer.toolbar.tools["solar:coordinate"]._marker
    slit = 20
    for step in (2, 186):  # the nearest slit-jaw frame comes after, then before, the exposure
        select_point(viewers["map"], step, slit)
        qtbot.waitUntil(lambda: viewers["spectrogram"].state.slices[0] == step)
        assert viewers["wavelength"].state.slices[1] == slit
        [spectrum] = [layer for layer in viewers["spectrum"].state.layers if layer.visible]
        np.testing.assert_array_equal(spectrum.profile[1], raster[raster.main_components[0]][step, slit])
        [frame], _ = nearest(raster_times[step : step + 1], sji_times)
        qtbot.waitUntil(lambda: sji_viewer.state.slices[0] == frame)
        qtbot.waitUntil(marker.get_visible)
        assert tuple(marker.get_xydata()[0]) == pytest.approx(raster_point_on_sji(raster, sji, step, slit, frame))
    assert [layer for layer in sji_viewer.state.layers if layer.layer.label == "Point"] == []

    # and a slit-jaw time master moves the point to the nearest exposure
    coordinator(dc).set_master(sji)
    [group] = app.session.edit_subset_mode.edit_subset
    for frame in (8, 40):  # the nearest exposure comes after, then before, the frame
        sji_viewer.state.slices = (frame, 0, 0)
        [exposure], _ = nearest(sji_times[frame : frame + 1], raster_times)
        qtbot.waitUntil(lambda: group.subset_state.slices[:2] == [slice(exposure, exposure + 1), slice(slit, slit + 1)])
    assert dc.external_links == links  # time sync adds no links
    assert [list(data.components) for data in dc] == components


@pytest.mark.parametrize("autolink_first", [True, False])
def test_wcs_autolinks_leave_link_hpc_unchanged(sns, autolink_first):
    if not hasattr(wcs_autolinking, "permuted_values_functions"):
        pytest.skip("glue-core without APE-14 low-level WCS autolinking")
    sji, raster = sns
    dc = DataCollection([sji, raster])
    if autolink_first:
        suggested = _autolink(dc)
    dc.add_link(link_hpc(dc))
    if not autolink_first:
        suggested = _autolink(dc)
    [wcs_link] = suggested  # glue-viz/glue#2595 links the SJI image axes to the raster's step and slit
    assert isinstance(wcs_link, WCSLink)
    hpc = [link for link in dc.external_links if link is not wcs_link]
    assert sorted((link.cids1[0].label, link.cids2[0].label) for link in hpc) == [(HPC[1], HPC[1]), (HPC[0], HPC[0])]
    # each reads the other's longitude and latitude through link_hpc, not the WCS link's first frame
    # (raster pixel selections in the slit-jaw image do take the WCS link)
    for label in HPC:
        np.testing.assert_array_equal(raster[_cid(sji, label)], raster[_cid(raster, label)])
        np.testing.assert_array_equal(sji[_cid(raster, label)], sji[_cid(sji, label)])


def test_pixel_point_workaround_installs_only_where_glue_needs_it(sns):
    import inspect

    from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState

    installed = PixelSubsetState._to_linked_pixel_coords is glue_patches._to_linked_pixel_coords
    assert installed == glue_patches.needs_pixel_point_workaround()  # probes glue's own method
    assert not glue_patches.needs_pixel_point_workaround(glue_patches._to_linked_pixel_coords)
    # a private method: pin its signature on the released baseline
    assert list(inspect.signature(glue_patches._original_to_linked_pixel_coords).parameters) == ["self", "data"]
    # a slit-jaw point off the raster, as a click beside its field of view, is incompatible with the
    # raster (no crosshair, no spectrum) instead of an error box
    sji, raster = sns
    dc = DataCollection([sji, raster])
    dc.add_link(link_hpc(dc))
    point = PixelSubsetState(sji, [slice(0, 1), slice(0, 1), slice(0, 1)])
    with pytest.raises(IncompatibleAttribute):
        point.to_array(raster, raster.main_components[0])
