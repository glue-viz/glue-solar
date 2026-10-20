import itertools
import shutil
import threading
from types import SimpleNamespace

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
from glue.core.subset import RoiSubsetState, SubsetState
from glue.plugins.tools.path_slicer.path_sliced_data_links import PathRelativeLink
from glue.plugins.wcs_autolinking import wcs_autolinking
from glue.plugins.wcs_autolinking.wcs_autolinking import IncompatibleWCS, WCSLink
from glue.viewers.image import pixel_selection_subset_state
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.app import GlueApplication
from glue_qt.dialogs.link_editor.state import LinkEditorState
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile.layer_artist import QThreadedProfileLayerArtist
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u
import astropy.wcs.wcsapi.fitswcs
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.wcsapi import HighLevelWCSWrapper

import glue_solar
from glue_solar import glue_patches
from glue_solar.conftest import SCAN, find_irispy_test_file
from glue_solar.quicklook import _role, coordinator, nearest, quicklook
from glue_solar.regrid import north_up, rebin, regrid_on_time
from glue_solar.sources.bursts import si_iv_bursts, sji_bursts
from glue_solar.sources.calibration import radiometric_calibration, remove_dust
from glue_solar.sources.doppler import doppler_image
from glue_solar.sources.iris import browse_iris, link_iris, shift_pointing_iris
from glue_solar.sources.loaders.iris import (
    WCS_LOCK,
    QtIRISImporter,
    _HeldWCS,
    _LockedWCS,
    image_data,
    keep_hpc_linked,
    link_hpc,
    raster_data,
)
from glue_solar.sources.mg_features import mg_features
from glue_solar.sources.moments import line_moments
from glue_solar.sources.red_blue import red_blue_asymmetry
from glue_solar.sources.sst import sst_data
from glue_solar.tests.helpers import (
    angles,
    inversions,
    linked_data,
    load_selected,
    raster_point_on_sji,
    scanned,
    select_point,
    shift,
)
from glue_solar.tests.test_bursts import SI_IV, SJI_1400
from glue_solar.tests.test_quicklook import drifting_stack
from glue_solar.tests.test_sessions import twice

SJI = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
RASTER = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
HPC = ["Helioprojective Longitude", "Helioprojective Latitude"]
# what of a linked dataset's WCS holds the WCS lock: wcslib's transforms, copies and the properties that read its struct
LOCKED_TRANSFORMS = (
    "all_pix2world",
    "all_world2pix",
    "wcs_pix2world",
    "wcs_world2pix",
    "pixel_to_world_values",
    "world_to_pixel_values",
    "sub",
    "to_header",
    "__copy__",
    "__deepcopy__",
)
LOCKED_PROPERTIES = (
    "axis_correlation_matrix",
    "world_axis_physical_types",
    "world_axis_units",
    "world_axis_names",
    "world_axis_object_components",
    "world_axis_object_classes",
    "pixel_n_dim",
    "world_n_dim",
    "array_shape",
    "pixel_shape",
    "pixel_bounds",
    "has_distortion",
    "has_celestial",
    "has_spectral",
    "has_temporal",
)


def _cid(data, label):
    return next(cid for cid in data.world_component_ids if cid.label == label)


def test_sji_and_raster_share_axis_names(sns):
    sji, raster = sns
    assert [c.label for c in sji.world_component_ids] == ["Time (Utc)", *HPC[::-1]]
    assert [c.label for c in raster.world_component_ids] == [*HPC, "Wavelength"]
    assert [c.label for c in sji.components].count("Time") == 1


def test_link_editor_wcs_link_works_or_refuses_cleanly(sns, irispy_test_files):
    # The link editor's "WCS link" between IRIS datasets raised AttributeError: 'has_celestial'
    sji, raster = sns
    sji_2796 = image_data(find_irispy_test_file(irispy_test_files, SJI.replace("1400", "2796")))
    DataCollection([sji, raster, sji_2796]).add_link(WCSLink(sji, sji_2796))
    assert [sji[cid][3, 20, 10] for cid in sji_2796.pixel_component_ids[1:]] == pytest.approx([20, 10], abs=0.01)
    try:
        WCSLink(sji, raster)
    except IncompatibleWCS:  # glue-core 1.27.0: SJI and raster share only lon/lat, which link_hpc links
        pass


def test_wcs_link_between_two_raster_windows(irispy_test_files):
    # glue's "WCS link" raised IncompatibleWCS: its SkyCoord took the arcsec values for degrees
    windows = raster_data([find_irispy_test_file(irispy_test_files, RASTER)], ["C II 1336", "Si IV 1403"])
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
    installed = component_link.world2pixel_single_axis.__wrapped__ is glue_patches.world2pixel_single_axis
    assert installed == glue_patches.needs_inverse_workaround()  # probes glue's own function
    assert coordinate_helpers.world2pixel_single_axis is component_link.world2pixel_single_axis
    assert not glue_patches.needs_inverse_workaround(glue_patches.world2pixel_single_axis)


@pytest.mark.parametrize("needed", [True, False])
def test_the_link_patches_hold_the_wcs_lock(monkeypatch, needed):
    # SST1: glue's profile workers reach the WCS of each linked dataset through these, one restored unlocked too; glue's
    # own, once fixed, still hold it (D73)
    patched = (
        (coordinate_helpers, "world2pixel_single_axis"),
        (component_link, "world2pixel_single_axis"),  # which imports it by name
        (PixelSubsetState, "_to_linked_pixel_coords"),
    )
    for owner, name in patched:
        monkeypatch.setattr(owner, name, getattr(owner, name))  # put back after
    for probe in ("needs_inverse_workaround", "needs_pixel_point_workaround"):
        monkeypatch.setattr(glue_patches, probe, lambda *args: needed)
    glue_patches._hold_wcs_lock()
    *inverses, point = (getattr(owner, name) for owner, name in patched)
    fixes = glue_patches.world2pixel_single_axis, glue_patches._to_linked_pixel_coords
    assert [function.__wrapped__ in fixes for function in (*inverses, point)] == [needed] * 3
    held = []
    wcs = SimpleNamespace(
        axis_correlation_matrix=np.eye(2, dtype=bool),
        world_to_pixel_values=lambda *world: held.append(WCS_LOCK._is_owned()) or world,
    )
    for inverse in inverses:
        inverse(wcs, np.zeros(3), np.zeros(3), pixel_axis=0)
    for module in (glue_patches, pixel_selection_subset_state):  # the fix's and glue's
        monkeypatch.setattr(
            module,
            "pixel_cid_to_pixel_cid_matrix",
            lambda *args: held.append(WCS_LOCK._is_owned()) or np.zeros((0, 0), bool),
        )
    linked, iris, unlinked = (
        SimpleNamespace(coords=coords, pixel_component_ids=[]) for coords in (_LockedWCS(naxis=2), None, WCS(naxis=2))
    )
    for reference, data in ((linked, iris), (iris, linked), (iris, unlinked), (unlinked, unlinked)):
        point(SimpleNamespace(reference_data=reference, slices=[]), data)
    # and WCSAxes, which calls wcslib's wcsset on the WCS of a linked dataset, as glue at each slice of an SST cube
    monkeypatch.setattr(glue_patches, "_original_reset_wcs", lambda *args: held.append(WCS_LOCK._is_owned()))
    glue_patches.reset_wcs(None, wcs=_LockedWCS(naxis=2))
    glue_patches.reset_wcs(None, wcs=WCS(naxis=2))  # an unlinked one waits for no profile worker
    assert held == [True, True, True, True, False, False, True, False]  # nor a point to or on an unlinked one (227-9)
    # and each transform, copy and property reading wcslib's struct of a linked dataset's WCS (a lock on the transforms
    # alone still crashed), as glue's autolinker reads has_celestial of every dataset's WCS as data load: wcsset again
    for name in LOCKED_TRANSFORMS:
        assert getattr(_LockedWCS, name).__wrapped__ is getattr(WCS, name)
    for name in LOCKED_PROPERTIES:
        assert getattr(_LockedWCS, name).fget.__wrapped__ is getattr(WCS, name).fget
    # and nothing else is wrapped that these lists do not name
    wrapped = {name for name, value in vars(_HeldWCS).items() if hasattr(getattr(value, "fget", value), "__wrapped__")}
    assert wrapped == {*LOCKED_TRANSFORMS, *LOCKED_PROPERTIES}


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


def test_inverse_workaround_leaves_wcsaxes_readouts_alone(app, sns, monkeypatch):
    sji, _ = sns
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
    [other] = raster_data([find_irispy_test_file(irispy_test_files, RASTER)], ["C II 1336"])
    aia = _parse_sunpy_map(sunpy.map.Map(sunpy.data.test.get_test_filepath("aia_171_level1.fits")), "aia")
    assert set(aia.coords.world_axis_units) == {"deg"}
    dc = DataCollection([sji, raster, aia, other])
    assert len(link_hpc(dc)) == 4  # the map only when named (226-3)
    links = link_hpc(dc, others=[aia])
    assert len(links) == 6
    assert {link.cids1[0] for link in links} == {_cid(sji, label) for label in HPC}
    # the map's degrees to arcsec; IRIS data keep LinkSame, which glue-core 1.27.0 restores from a session and
    # LinkSameWithUnits not
    assert {type(link) for link in links if link.cids2[0].parent is aia} == {LinkSameWithUnits}
    assert {type(link) for link in links if link.cids2[0].parent is not aia} == {LinkSame}
    link_iris(None, dc)  # the map too, on request
    dc.remove(sji)  # the others were linked through it
    qtbot.waitUntil(lambda: len(dc.external_links) == 4)
    np.testing.assert_allclose(other[_cid(raster, HPC[1])], other[_cid(other, HPC[1])])
    dc.clear()  # one relink after all the removals, with nothing left to link
    qtbot.wait(10)
    assert not dc.external_links


@pytest.mark.parametrize("opened", [False, True])
def test_a_restored_session_keeps_the_data_linked_on_request_linked(qtbot, tmp_path, irispy_test_files, sns, opened):
    # D73: a session saves the links 'Link helioprojective coordinates' made, not that they were asked for: once
    # the IRIS dataset they went through was removed, a restored SST cube, SOT cube or map was left unlinked, quicklook
    # opened first or not
    from glue_solar.tests.test_sst import write_sst_cube  # which imports this module

    write_sst_cube(tmp_path / "cube.fits")
    [path] = [path for path in irispy_test_files if "_Gband4305_FG_" in path.name]
    lon, lat, _ = sns[0].coords.pixel_to_world_values(18, 20, 0)
    others = [sst_data(tmp_path / "cube.fits"), image_data(path), _sunpy_map(lon, lat, 0.6, (80, 160), "aia")]
    collection = DataCollection([*sns, *others])
    link_iris(None, collection)
    restored = next(twice(collection))
    sji, raster, *others = restored
    if opened:
        glue_solar.setup()
        app = GlueApplication(restored)
        qtbot.addWidget(app)
        quicklook(app, [raster, sji])
    restored.remove(sji)  # the others were linked through it

    def linked():  # by longitude and latitude, not only by time
        links = [link for link in restored.external_links if hasattr(link, "cids1")]
        return {(link.cids1[0].parent, link.cids2[0].parent) for link in links}

    qtbot.waitUntil(lambda: linked() == {(raster, data) for data in others})
    np.testing.assert_allclose(others[1][_cid(raster, HPC[1])], others[1][_cid(others[1], HPC[1])])


def test_a_restored_session_keeps_sst_cubes_linked_without_iris_data(qtbot, tmp_path):
    # D97: with no IRIS data, cubes linked on request link to each other again once the one they were linked through
    # is removed, in a restored session as in a live one
    from glue_solar.tests.test_sst import write_sst_cube  # which imports this module

    for name in "abc":
        write_sst_cube(tmp_path / f"{name}.fits")
    collection = DataCollection([sst_data(tmp_path / f"{name}.fits") for name in "abc"])
    link_iris(None, collection)
    restored = next(twice(collection))
    first, *others = restored
    restored.remove(first)
    qtbot.waitUntil(lambda: linked_data(restored) == set(others))


def test_a_map_linked_by_hand_to_another_iris_dataset_is_not_linked_on_request(qtbot, sns):
    # D73: only a link to the IRIS dataset `link_hpc` links to is taken as one made on request, not one made in glue's
    # Link Data dialog to another
    sji, raster = sns
    lon, lat, _ = sji.coords.pixel_to_world_values(18, 20, 0)
    aia = _sunpy_map(lon, lat, 0.6, (80, 160), "aia")
    dc = DataCollection([sji, raster, aia])
    keep_hpc_linked(dc)
    dc.add_link([LinkSameWithUnits(_cid(raster, h), _cid(aia, m)) for h, m in zip(HPC, ["Hpln", "Hplt"])])
    keep_hpc_linked(dc)
    assert type(aia.coords) is WCS
    assert not dc._solar_relinker.others


def test_a_sot_cube_loaded_first_is_linked_on_request_to_the_raster(sns, irispy_test_files):
    # D72: a Hinode/SOT cube's longitude and latitude, each frame at its own pointing, as IRIS data read them, linked
    # only on request, and to the IRIS raster loaded after it, never the raster to it
    _, raster = sns
    [path] = [path for path in irispy_test_files if "_Gband4305_FG_" in path.name]
    sot = image_data(path)
    sots = DataCollection([image_data(path), image_data(path)])
    # with no IRIS dataset, one SOT cube to the other on request (D97, reversing 212-3)
    assert [type(link) for link in link_hpc(sots, others=sots)] == [LinkSame, LinkSame]
    dc = DataCollection([sot, raster])
    assert link_hpc(dc) == []
    link_iris(None, dc)
    assert [(type(link), link.cids1[0], link.cids2[0]) for link in dc.external_links] == [
        (LinkSame, _cid(raster, label), _cid(sot, label)) for label in HPC[::-1]
    ]
    for label in HPC:
        np.testing.assert_array_equal(sot[_cid(raster, label)], sot[_cid(sot, label)])
    lon = _cid(raster, HPC[0])
    assert 0 < sot.get_mask(lon > float(np.nanmedian(sot[lon]))).sum() < sot.size


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


@pytest.mark.parametrize("frame", [0, -1])
def test_link_hpc_places_a_sunpy_map_on_each_sji_frame(sns, frame):
    # glue converts the map's degrees to the arcsec of IRIS data, and each slit-jaw frame keeps its own pointing
    sji, _ = sns
    lon, lat, _ = sji.coords.pixel_to_world_values(18, 20, sji.shape[0] // 2)
    aia = _sunpy_map(lon, lat, 0.6, (80, 160), "aia", rotation=10, obstime=sji.meta["DATE_OBS"])
    dc = DataCollection([aia, sji])
    links = link_hpc(dc, others=[aia])
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


def test_shift_pointing_moves_a_sunpy_map_over_a_slit_jaw_image(app, monkeypatch, sns):
    # co-aligning: a map shown over a slit-jaw image is placed again through the image's shifted coordinates
    sji, _ = sns
    lon, lat, _ = sji.coords.pixel_to_world_values(18, 20, 0)
    aia = _sunpy_map(lon, lat, 0.6, (80, 160), "aia", obstime=sji.meta["DATE_OBS"])
    aia.update_components({aia.main_components[0]: np.arange(aia.size, dtype=float).reshape(aia.shape)})
    app.data_collection.extend([sji, aia])
    link_iris(app.session, app.data_collection)
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    viewer.add_data(aia)
    [layer] = [artist for artist in viewer.layers if artist.layer is aia]
    bounds = [(0, n - 1, n) for n in sji.shape[1:]]
    before = layer.state.get_sliced_data(bounds=bounds)  # glue's image of the map, which it keeps
    shift(monkeypatch, sji, app.data_collection, (2, -1))
    # the map's pixels under each slit-jaw pixel, from its shifted longitude and latitude
    y, x = np.indices(sji.shape[1:])
    lon, lat, _ = sji.coords.pixel_to_world_values(x, y, 0)
    expected = aia.coords.world_to_pixel_values((lon * u.arcsec).to_value(u.deg), (lat * u.arcsec).to_value(u.deg))
    for cid, values in zip(aia.pixel_component_ids[::-1], expected):
        np.testing.assert_allclose(sji[cid][0], values, rtol=0, atol=0.05)
    # and the viewer draws the map there, not glue's image of it from before
    after = layer.state.get_sliced_data(bounds=bounds)
    placed = aia.compute_fixed_resolution_buffer([0, *bounds], target_data=sji, target_cid=layer.state.attribute)
    np.testing.assert_array_equal(after, placed)
    assert not np.array_equal(after, before, equal_nan=True)


def test_data_made_from_a_dataset_follow_every_shift_of_it(qtbot, monkeypatch, irispy_test_files):
    [si_iv] = raster_data([find_irispy_test_file(irispy_test_files, SI_IV)])
    c_ii, mg_ii = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["C II 1336", "Mg II k 2796"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI_1400))
    rebinned, dust = rebin(si_iv, (2, 2, 1)), remove_dust(sji)
    maps, rebinned_maps = line_moments(si_iv, 1402.77), line_moments(rebinned, 1402.77)
    bursts, events = si_iv_bursts(si_iv, 80)
    sji_labels, sji_events = sji_bursts(dust)
    of_si_iv = [maps, rebinned, rebinned_maps, bursts, red_blue_asymmetry(si_iv, 1402.77)]
    of_si_iv.append(doppler_image(si_iv, 1402.77))
    of_sji = [regrid_on_time(sji), rebin(sji, (1, 2, 2)), dust, sji_labels]
    features, grid = mg_features(mg_ii), north_up(sji)
    collection = DataCollection([si_iv, c_ii, mg_ii, sji, *of_si_iv, *of_sji, features, grid, events, sji_events])
    keep_hpc_linked(collection)
    before = {data.label: angles(data) for data in collection if data not in (events, sji_events)}
    places = {table.label: (table["coordinate.Tx"], table["coordinate.Ty"]) for table in (events, sji_events)}
    lon, lat = si_iv.world_component_ids[:2]

    def region():  # drawn on raster steps 20 to 40, slit pixels 60 to 120, as their angles now are
        corners = si_iv.coords.pixel_to_world_values(0, [60, 120], [20, 40])
        return RoiSubsetState(lon, lat, RectangularROI(*sorted(corners[2]), *sorted(corners[1])))

    selected = region().to_mask(maps)
    assert 0 < selected.sum() < maps.size

    def assert_followed(datasets, offset, of=before):
        for data in datasets:
            assert data.coords.pointing_offset == offset
            expected = of[data.label] + np.reshape(offset, (2, 1))
            np.testing.assert_allclose(angles(data), expected, rtol=0, atol=1e-9, err_msg=data.label)

    def assert_events(table, offset):
        for got, start, shift_ in zip((table["coordinate.Tx"], table["coordinate.Ty"]), places[table.label], offset):
            np.testing.assert_allclose(got, start + shift_, rtol=0, atol=1e-9)

    # each shift moves the data made from the shifted dataset, a raster's other windows' too, and from those in turn
    for offset in [(5.0, -3.0), (0.5, 0.25)]:
        shift(monkeypatch, si_iv, collection, offset)
        shift(monkeypatch, c_ii, collection, offset[::-1])  # mg_ii, its file's other window, too
        shift(monkeypatch, sji, collection, (-offset[0], offset[1]))
        assert_followed(of_si_iv, offset)
        assert_followed([features], offset[::-1])
        assert_followed(of_sji, (-offset[0], offset[1]))
        assert_events(events, offset)
        assert_events(sji_events, (-offset[0], offset[1]))
        # the links still place them: a region drawn again on the same raster pixels selects the same map pixels
        np.testing.assert_array_equal(region().to_mask(maps), selected)
    # a north-up grid stays, and the slit-jaw image moves across it
    np.testing.assert_array_equal(angles(grid), before[grid.label])
    # one made from another shifts the furthest one it is made from instead, which the dialog names, and so the whole
    # family: the raster file's other windows, what is made from any of them and the events tables
    asked = []

    def cancel(dialog):
        asked.append((dialog.windowTitle(), dialog.findChild(QtWidgets.QLabel, "source").text()))

    monkeypatch.setattr(QtWidgets.QDialog, "exec", cancel)
    shift_pointing_iris(rebinned_maps, collection)
    assert asked == [(f"Shift pointing of {si_iv.label}", f"{rebinned_maps.label} is made from it and moves with it.")]
    assert shift(monkeypatch, rebinned_maps, collection, (1.0, 1.0)) == (0.5, 0.25)
    assert_followed([si_iv, *of_si_iv], (1.0, 1.0))
    assert_events(events, (1.0, 1.0))
    shift(monkeypatch, features, collection, (2.0, -1.0))
    assert_followed([c_ii, mg_ii, features], (2.0, -1.0))
    shift(monkeypatch, sji_labels, collection, (-1.5, 0.5))
    assert_followed([sji, *of_sji], (-1.5, 0.5))
    assert_events(sji_events, (-1.5, 0.5))
    # once removed, what it was made from moves it no more, while what that was made from still does, and a dataset
    # none of whose sources is left shifts on its own, with what is made from it
    collection.remove(rebinned)
    collection.remove(mg_ii)
    collection.remove(sji)
    shift(monkeypatch, rebinned_maps, collection, (2.0, 2.0))
    shift(monkeypatch, c_ii, collection, (3.0, 3.0))
    assert_followed([si_iv, maps, rebinned_maps], (2.0, 2.0), of=before)
    assert_followed([features], (2.0, -1.0), of=before)
    shift(monkeypatch, features, collection, (0.25, 0.5))
    assert_followed([features], (0.25, 0.5), of=before)
    assert_followed([c_ii], (3.0, 3.0), of=before)
    shift(monkeypatch, sji_labels, collection, (1.0, 0.0))  # its dust-removed image is the furthest left
    assert_followed([dust, sji_labels], (1.0, 0.0), of=before)
    assert_followed([of_sji[0]], (-1.5, 0.5), of=before)
    assert_events(sji_events, (1.0, 0.0))


def test_raster_pixels_reach_a_sunpy_map_whose_longitudes_run_from_0_to_360(sns):
    # astropy gives a map whose reference longitude is not negative longitudes from 0 to 360 degrees, so a raster
    # east of that reference is near 360 degrees there
    _, raster = sns
    aia = _sunpy_map(10, -430, 0.5, (60, 240), "aia")
    assert aia[aia.world_component_ids[1]].max() > 359
    dc = DataCollection([raster, aia])
    dc.add_link(link_hpc(dc, others=[aia]))
    y, x = np.indices(aia.shape)
    sky = aia.coords.pixel_to_world(x, y)
    wavelength = np.full(x.shape, raster.coords.pixel_to_world_values(0, 0, 0)[0])
    lon, lat = sky.Tx.to_value(u.arcsec), sky.Ty.to_value(u.arcsec)
    _, slit, step = raster.coords.world_to_pixel_values(wavelength, lat, lon)
    assert np.isfinite(step).sum() > 1000
    np.testing.assert_allclose(aia[raster.pixel_component_ids[0]], step, rtol=0, atol=0.05)
    np.testing.assert_allclose(aia[raster.pixel_component_ids[1]], slit, rtol=0, atol=0.05)
    # the same a turn lower, as a map whose reference longitude is negative gives longitudes from -360 to 0 degrees
    turned = raster.coords.world_to_pixel_values(wavelength, lat, lon - (360 * u.deg).to_value(u.arcsec))
    np.testing.assert_allclose(turned[1:], [slit, step], rtol=0, atol=1e-6)


def test_a_raster_map_region_reaches_a_sunpy_map_whose_longitudes_run_from_0_to_360(app, monkeypatch, sns):
    # a region drawn on a quicklook's raster map reaches the map by its outline in longitude and latitude, where it
    # lies near 360 degrees: the same pixels as glue's own region on the raster's pixels
    sji, raster = sns
    aia = _sunpy_map(10, -430, 0.5, (60, 240), "aia")
    app.data_collection.append(aia)
    viewers = quicklook(app, [raster, sji])
    link_iris(app.session, app.data_collection)  # the map, which a quicklook leaves unlinked
    roi = RectangularROI(80.5, 100.5, 2.3, 9.7)
    viewers["map"].apply_roi(roi)
    group = app.data_collection.subset_groups[-1]  # a new subset
    expected = aia.get_mask(RoiSubsetState(raster.pixel_component_ids[0], raster.pixel_component_ids[1], roi))
    assert expected.sum() >= 50
    inverted = inversions(monkeypatch, raster)
    np.testing.assert_array_equal(aia.get_mask(group.subset_state), expected)
    assert not inverted


def test_a_sunpy_map_over_quicklook_panels_leaves_one_crosshair(app, sns):
    # glue-core 1.27.0 places each layer's Pixel crosshair at the point's pixel in the layer's own dataset: a map
    # linked to the raster added a second crosshair on the raster map, and raised IndexError over a slit-jaw image
    import inspect

    from glue.viewers.image.layer_artist import ImageSubsetLayerArtist

    installed = ImageSubsetLayerArtist._update_data is glue_patches._update_data
    assert installed == glue_patches.needs_reference_crosshair_workaround()  # probes glue's own method
    assert not glue_patches.needs_reference_crosshair_workaround(glue_patches._update_data)
    # a private method: pin its signature on the released baseline
    assert list(inspect.signature(glue_patches._original_update_data).parameters) == ["self"]
    sji, raster = sns
    lon, lat, _ = sji.coords.pixel_to_world_values(18, 20, sji.shape[0] // 2)
    aia = _sunpy_map(lon, lat, 0.6, (80, 160), "aia", rotation=10)
    app.data_collection.append(aia)
    viewers = quicklook(app, [raster, sji])
    link_iris(app.session, app.data_collection)  # the map, which a quicklook leaves unlinked
    select_point(viewers["map"], 30, 15)
    crosshairs = {}
    for viewer in (viewers["map"], *viewers["sji"]):
        viewer.add_data(aia)
        viewer.figure.canvas.draw()
        crosshairs[viewer] = {
            (artist._line_x.get_xdata()[0], artist._line_y.get_ydata()[0])
            for artist in viewer.layers
            if artist.layer.label == "Point" and artist._line_x.get_visible()
        }
    assert list(crosshairs.values()) == [{(30, 15)}, set()]


def test_data_outside_the_iris_observations_link_only_on_request(app, sns):
    # D64: data load, the analyses and a quicklook link IRIS data only, as each quicklook panel would otherwise invert
    # the other data's WCS (SST3); 'Link helioprojective coordinates' links the others too, their WCS locked
    sji, raster = sns
    dc = app.data_collection
    lon, lat, _ = sji.coords.pixel_to_world_values(18, 20, 0)
    aia = _sunpy_map(lon, lat, 0.6, (80, 160), "aia")
    dc.append(aia)
    keep_hpc_linked(dc)
    quicklook(app, [raster, sji])
    assert linked_data(dc) == {sji, raster}
    assert type(aia.coords) is WCS
    link_iris(app.session, dc)
    assert linked_data(dc) == {sji, raster, aia}
    assert isinstance(aia.coords, _LockedWCS)


def test_profile_workers_reach_a_linked_map_s_wcs_holding_the_lock(app, qtbot, monkeypatch, sns):
    # SST1: wcslib is not thread-safe, and a quicklook's spectrum panels compute a region drawn on other linked data
    # over the raster on glue-qt's worker threads, as the GUI thread draws that data: each call holds WCS_LOCK
    sji, raster = sns
    # on the worker thread, as glue-qt computes the profiles of data of over 1e7 values, such as a whole raster
    monkeypatch.setattr(
        QThreadedProfileLayerArtist, "_calculate_profile", lambda self, reset=False: self._worker.work_queue.put(reset)
    )
    lon, lat, _ = sji.coords.pixel_to_world_values(18, 20, 0)
    aia = _sunpy_map(lon, lat, 0.6, (80, 160), "aia")  # over the raster
    app.data_collection.append(aia)
    quicklook(app, [raster, sji])
    link_iris(app.session, app.data_collection)
    calls = []  # (on the GUI thread, the transform or property, holding the lock) of each read of the map's WCS
    names = {*LOCKED_TRANSFORMS, *LOCKED_PROPERTIES}

    def profile(frame, event, arg):
        if event == "call" and frame.f_code.co_name in names and frame.f_locals.get("self") is aia.coords:
            main = threading.current_thread() is threading.main_thread()
            calls.append((main, frame.f_code.co_name, WCS_LOCK._is_owned()))

    app.new_data_viewer(ImageViewer, data=aia)
    group = app.data_collection.new_subset_group("region", SubsetState())  # and the workers of its profiles
    threading.setprofile_all_threads(profile)  # its workers too, waiting for work: a QThread started later is not
    try:
        roi = RectangularROI(20, 140, 10, 70)
        group.subset_state = RoiSubsetState(aia.pixel_component_ids[1], aia.pixel_component_ids[0], roi)
        # on both threads, properties too off the GUI thread
        qtbot.waitUntil(
            lambda: (
                {main for main, *_ in calls} == {True, False}
                and any(not main and name in LOCKED_PROPERTIES for main, name, _ in calls)
            ),
            timeout=30_000,
        )
    finally:
        threading.setprofile_all_threads(None)
    assert all(locked for *_, locked in calls)


def test_the_analyses_hold_the_wcs_lock_in_each_wcslib_call_not_across_irispy(stack_paths):
    # review F3: the analyses run on a worker beside the GUI thread's WCS calls, which waited about 1.4 s each as they
    # held WCS_LOCK through irispy's whole slab; each wcslib call on a stack's scans' WCSes now holds it for itself
    si, mg = raster_data(stack_paths, ["Si IV 1403", "Mg II k 2796"], stack=True)
    raws = [*si.coords._wcs._wcses, *mg.coords._wcs._wcses]
    raws += [w.coords._wcs._wcs._wcs[1]._wcs for w in (si, mg)]  # the scan axis's, which irispy copies and reads too
    assert {type(raw) for raw in raws} == {_LockedWCS}  # as `_GlueWCS` makes them
    owners = {id(owner) for raw in raws for owner in (raw, raw.wcs)}  # each WCS and its wcslib struct
    files = {astropy.wcs.wcs.__file__, astropy.wcs.wcsapi.fitswcs.__file__}
    irispy = {
        "calculate_red_blue_asymmetry",
        "subtract_background",
        "calculate_moments",
        "calculate_mg_features",
        "calculate_dn_to_radiance_factor",
    }
    calls, entered, reads = [], [], []  # (the function, holding the lock); irispy's struct reads, holding it

    def profile(frame, event, arg):
        if event == "c_call" and id(getattr(arg, "__self__", None)) in owners:
            calls.append((arg.__name__, WCS_LOCK._is_owned()))
        elif event == "call" and frame.f_code.co_filename in files and id(frame.f_locals.get("self")) in owners:
            calls.append((frame.f_code.co_name, WCS_LOCK._is_owned()))
        elif event == "call" and frame.f_code.co_name in irispy:
            entered.append((frame.f_code.co_name, WCS_LOCK._is_owned()))
        elif event == "call" and frame.f_code.co_name in ("spectral_dispersion", "solid_angle"):
            reads.append(WCS_LOCK._is_owned())

    threading.setprofile_all_threads(profile)
    try:
        red_blue_asymmetry(si, 1402.77)
        line_moments(si, 1402.77, continuum=[(1400.0, 1400.5)])
        mg_features(mg)
        radiometric_calibration(si)  # which holds it to read the struct, irispy's spectral dispersion and solid angle
    finally:
        threading.setprofile_all_threads(None)
    assert {"_all_pix2world", "pixel_to_world_values", "__deepcopy__"} <= {name for name, _ in calls}
    assert {name for name, locked in calls if not locked} <= {"serialized_classes"}  # astropy's False, no wcslib
    assert {name for name, _ in entered} == irispy
    assert not any(locked for _, locked in entered)
    assert reads
    assert all(reads)  # wcs.wcs.ctype, cdelt and cunit, which `_LockedWCS` cannot guard


def _inside(sji, frame, raster, roi):
    """
    The pixels of ``sji``'s frame ``frame`` inside ``roi``, steps and slit rows of ``raster``, from their coordinates,
    and those within 0.05 raster pixel of its edge.
    """
    y, x = np.indices(sji.shape[1:])
    lon, lat, _ = sji.coords.pixel_to_world_values(x, y, frame % sji.shape[0])
    wavelength = np.full(lon.shape, raster.coords.pixel_to_world_values(0, 0, 0)[0])
    _, slit, step = raster.coords.world_to_pixel_values(wavelength, lat, lon)
    (x, y), half_width, half_height = roi.center(), roi.width() / 2, roi.height() / 2

    def inside(margin):
        return (abs(step - x) < half_width + margin) & (abs(slit - y) < half_height + margin)

    return inside(0), inside(0.05) != inside(-0.05)


@pytest.mark.parametrize("frame", [0, -1])
def test_raster_map_roi_selects_the_sji_pixels_inside_it(linked_sns, frame):
    # Each SJI frame's own coordinates decide, so the selection follows that frame's pointing
    sji, raster = linked_sns
    roi = RectangularROI(80, 100, 10.3, 19.8)  # raster steps and slit rows, edges off the SJI pixel grid
    mask = sji.get_mask(
        RoiSubsetState(xatt=raster.pixel_component_ids[0], yatt=raster.pixel_component_ids[1], roi=roi)
    )[frame]
    expected, edge = _inside(sji, frame, raster, roi)
    assert expected.sum() >= 10
    assert edge.sum() <= expected.sum() // 10
    np.testing.assert_array_equal(mask[~edge], expected[~edge])


@pytest.mark.parametrize("frame", [0, -1])
def test_stack_map_roi_selects_the_sji_pixels_inside_it_in_the_nearest_scan(tmp_path, irispy_test_files, frame):
    # glue's own region on a stack's steps and slit rows, as a plain Image viewer of its map makes: in each SJI frame,
    # the pixels inside it in the scan nearest the frame's time, by its middle step, at that scan's own pointing
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    stack, alone = drifting_stack(tmp_path, irispy_test_files)
    dc = DataCollection([sji, stack])
    dc.add_link(link_hpc(dc))
    roi = RectangularROI(60, 120, 10.3, 19.8)
    mask = sji.get_mask(RoiSubsetState(xatt=stack.pixel_component_ids[1], yatt=stack.pixel_component_ids[2], roi=roi))
    scan = 0 if frame == 0 else 1
    expected, edge = _inside(sji, frame, alone[scan], roi)
    assert expected.sum() >= 10
    assert edge.sum() <= expected.sum() // 10
    np.testing.assert_array_equal(mask[frame][~edge], expected[~edge])
    assert (_inside(sji, frame, alone[1 - scan], roi)[0] != expected).sum() >= 10  # the other scan's pointing differs


def test_the_link_editor_keeps_a_stack_s_scans(tmp_path, irispy_test_files):
    # glue-qt's Link Data dialog lists the scan link with its one input, and OK keeps it
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    stack, _ = drifting_stack(tmp_path, irispy_test_files)
    dc = DataCollection([sji, stack])
    dc.add_link(link_hpc(dc))
    scans = sji[stack.id["Scan"]]
    LinkEditorState(dc).update_links_in_collection()
    np.testing.assert_array_equal(sji[stack.id["Scan"]], scans)


def test_the_link_editor_opens_on_a_linked_sunpy_map(sns):
    # glue-core 1.27.0 names both ends of the map's LinkSameWithUnits 'values', so Link Data and Link Suggestions
    # raised ValueError and never opened; the dialog lists each with the SJI's component and the map's, and OK, which
    # makes every link again from its components, keeps them
    sji, _ = sns
    lon, lat, _ = sji.coords.pixel_to_world_values(18, 20, 0)
    aia = _sunpy_map(lon, lat, 0.6, (80, 160), "aia", obstime=sji.meta["DATE_OBS"])
    dc = DataCollection([sji, aia])
    dc.add_link(link_hpc(dc, others=[aia]))
    pixels = [sji[cid] for cid in aia.pixel_component_ids]
    state = LinkEditorState(dc)
    assert [(link.x, link.y) for link in state.links] == [(link.cids1[0], link.cids2[0]) for link in dc.external_links]
    state.update_links_in_collection()
    assert {type(link) for link in dc.external_links} == {LinkSameWithUnits}
    assert link_hpc(dc) == []
    for cid, expected in zip(aia.pixel_component_ids, pixels, strict=True):
        np.testing.assert_array_equal(sji[cid], expected)


def test_link_editor_workaround_installs_only_where_glue_needs_it():
    installed = LinkSameWithUnits.__init__ is glue_patches.link_with_units_init
    assert installed == (PathRelativeLink.__init__ is glue_patches.path_link_init)
    assert installed == glue_patches.needs_link_editor_workaround()  # probes glue's own classes
    assert not glue_patches.needs_link_editor_workaround(glue_patches.link_with_units_init, glue_patches.path_link_init)


def test_browse_iris_links_what_it_loads(app, qtbot, tmp_path, irispy_test_files, monkeypatch):
    for name in (SJI, SJI.replace("1400", "2796"), RASTER):
        shutil.copy2(find_irispy_test_file(irispy_test_files, name), tmp_path / name)
    # a Hinode/SOT cube of the observation, as its SOTFG tarball gives one
    [path] = [path for path in irispy_test_files if "_Gband4305_FG_" in path.name]
    shutil.copy2(path, sot := tmp_path / "sot_l2_20210905_001833_3620258102_20210905003000_Gband4305_FG.fits")
    with fits.open(sot, mode="update") as hdul:
        hdul[0].header.update(OBSID="20210905_001833_3620258102", STARTOBS="2021-09-05T00:18:33.640")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    # glue-qt asks in a modal dialog whenever glue suggests links; this test is about link_hpc
    monkeypatch.setattr("glue_qt.app.application.run_autolinker", lambda data_collection: None)

    def tick_everything_and_load(dialog):
        scanned(qtbot, dialog)
        dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
        load_selected(qtbot, dialog)
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtIRISImporter, "exec", tick_everything_and_load)
    dc = app.data_collection
    dc.append(_sunpy_map(0, 0, 2, (40, 50), "aia"))  # loaded before, which the browser leaves to the link action
    on_gui, broadcast = [], Hub.broadcast
    monkeypatch.setattr(Hub, "broadcast", lambda hub, message: (
        on_gui.append(threading.current_thread() is threading.main_thread()) or broadcast(hub, message)
    ))
    browse_iris(app.session, dc)
    assert on_gui
    assert all(on_gui)  # glue's hub has no locks: the datasets are added on the GUI thread
    assert len(dc) > 5  # the map, two SJIs, the SOT cube and every raster window
    # longitude and latitude of each IRIS dataset to the first, and the quicklook's exposure and slit pixels of each
    # other raster window to the one it shows; not the SOT cube's, through loading and the quicklook (D72)
    windows = 2 * (sum(_role(data) == "raster" for data in dc) - 1)
    hpc = [link for link in dc.external_links if {cid.label for cid in (*link.cids1, *link.cids2)} <= set(HPC)]
    assert (len(hpc), len(dc.external_links) - len(hpc)) == (2 * (len(dc) - 3), windows)
    [cube] = [data for data in dc if data.meta.get("INSTRUME") == "SOT"]
    assert cube not in linked_data(dc)
    assert app.tab_count == 2  # its quicklook
    dc.append(image_data(find_irispy_test_file(irispy_test_files, SJI.replace("1400", "1330"))))  # loaded later
    link_iris(app.session, dc)  # and the map and SOT cube, on request
    assert len(dc.external_links) == 2 * (len(dc) - 1) + windows


def _autolink(data_collection):
    """Add every link glue's autolinkers suggest, as glue-qt's run_autolinker does when set to always accept."""
    links = [link for found in find_possible_links(data_collection).values() for link in found]
    data_collection.add_link(links)
    return links


@pytest.mark.parametrize("order", list(itertools.permutations(["autolinker", "link_hpc", "quicklook"])), ids="-".join)
def test_link_graph_in_every_add_order(app, qtbot, sns, order):
    sji, raster = sns
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


def test_a_pixel_click_off_the_image_leaves_the_point(app):
    assert glue_patches.needs_pixel_off_image_workaround()  # glue's own Pixel tool makes one
    assert not glue_patches.needs_pixel_off_image_workaround(glue_patches._select_pixel)
    data = Data(x=np.zeros((3, 4)), label="image")
    app.data_collection.append(data)
    tool = app.new_data_viewer(ImageViewer, data=data).toolbar.tools["image:point_selection"]
    tool._pressed = True
    # a press, then a drag past the right, left and top edges, as in a quicklook panel's margin
    for x, y in ((1.2, 2.4), (3.6, 1), (-0.6, 1), (1, 2.6)):
        tool._event_xdata, tool._event_ydata = x, y
        tool._move_callback(tool)
    [subset] = data.subsets
    assert subset.subset_state.slices == [slice(2, 3), slice(1, 2)]


def test_a_slit_jaw_pixel_at_a_time_off_its_frames_is_nan(sns, monkeypatch):
    # irispy's slit-jaw gWCS gives a time off its frames a NaN frame index, which dkist casts to an int: on x86-64 the
    # least int64, off its table, where its per-frame transform has no inverse (NotImplementedError), on ARM 0. Such a
    # world position, as another dataset's point gives, is off the image: NaN, as the forward transform says, not an error
    from dkist.wcs.models import BaseVaryingCelestialTransform

    def as_on_x86(ind):
        ind = np.asarray(getattr(ind, "value", ind), float)
        return np.where(np.isnan(ind), np.iinfo(np.int64).min, np.round(np.nan_to_num(ind))).astype(int)

    monkeypatch.setattr(BaseVaryingCelestialTransform, "sanitize_index", staticmethod(as_on_x86))
    sji, _ = sns
    last = sji.shape[0] - 1
    lon, lat, time = sji.coords.pixel_to_world_values(5, 6, last)
    after = time + 0.6 * (time - sji.coords.pixel_to_world_values(5, 6, last - 1)[2])  # past the last frame, by its index
    pixels = sji.coords.world_to_pixel_values(np.array([lon, lon]), np.array([lat, lat]), np.array([time, after]))
    np.testing.assert_allclose([pixel[0] for pixel in pixels], [5, 6, last], atol=1e-6)
    assert np.isnan([pixel[1] for pixel in pixels]).all()
    assert np.isnan(sji.coords.world_to_pixel_values(lon, lat, after)).all()


def test_pixel_point_workaround_installs_only_where_glue_needs_it(sns, tmp_path, irispy_test_files):
    import inspect

    installed = PixelSubsetState._to_linked_pixel_coords.__wrapped__ is glue_patches._to_linked_pixel_coords
    assert installed == glue_patches.needs_pixel_point_workaround()  # probes glue's own method
    assert not glue_patches.needs_pixel_point_workaround(glue_patches._to_linked_pixel_coords)

    def rounding_fixed(self, data):  # glue's with a point off ``data`` incompatible, still refusing fixed axes
        try:
            return glue_patches._original_to_linked_pixel_coords(self, data)
        except ValueError:
            raise IncompatibleAttribute() from None

    assert glue_patches.needs_pixel_point_workaround(rounding_fixed)
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
    # a raster point's wavelength, which reaches no axis of a stack, leaves it the pixel the point gives without it; a
    # slit row, whose stack pixel depends on its free exposure too, and a wavelength alone stay incompatible (D73)
    stack, _ = drifting_stack(tmp_path, irispy_test_files)
    dc.append(stack)
    dc.add_link(link_hpc(dc))
    pixel = PixelSubsetState(raster, [slice(93, 94), slice(20, 21), slice(None)])._to_linked_pixel_coords(stack)
    assert PixelSubsetState(raster, [slice(93, 94), slice(20, 21), slice(5, 6)])._to_linked_pixel_coords(stack) == pixel
    for slices in ([slice(None), slice(20, 21), slice(None)], [slice(None), slice(None), slice(5, 6)]):
        with pytest.raises(IncompatibleAttribute):
            PixelSubsetState(raster, slices)._to_linked_pixel_coords(stack)
    # a free axis reaching an axis the fixed ones do not leaves the point as glue places it
    cube, image = Data(x=np.zeros((2, 2, 2)), label="cube"), Data(y=np.zeros((2, 2, 2)), label="image")
    dc = DataCollection([cube, image])
    dc.add_link([LinkSame(a, b) for a, b in zip(cube.pixel_component_ids, image.pixel_component_ids)])
    point = PixelSubsetState(cube, [slice(None), slice(1, 2), slice(1, 2)])
    assert point._to_linked_pixel_coords(image) == [None, 1, 1]
