"""
Sessions keep the coordinates and colormaps of every kind of dataset glue-solar makes from IRIS data, on irispy's test
files, and the colormap of a sunpy map.
"""

import numpy as np
import pytest
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer
from glue.viewers.profile.state import ProfileViewerState
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer

import astropy.units as u
from astropy.wcs import WCS

import sunpy.data.test
from sunpy.visualization.colormaps import cmlist

import glue_solar
from glue_solar import glue_patches
from glue_solar.conftest import find_irispy_test_file
from glue_solar.regrid import north_up, rebin, regrid_on_time
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.sources.maps import read_sunpy_map
from glue_solar.sources.moments import line_moments
from glue_solar.tests.test_quicklook import SCAN
from glue_solar.tools import _pointing

SJI = "iris_l2_20210905_001833_3620258102_SJI_1330_t000.fits"


def twice(obj):
    """Yields ``obj`` saved in a session by glue and restored, then that restore saved and restored again."""
    for _ in range(2):
        obj = GlueUnSerializer.loads(GlueSerializer(obj).dumps()).object("__main__")
        yield obj


def assert_same_coordinates(coords, data):
    """``coords`` give those of ``data`` at and between its pixels and back, within 1e-9, and keep its offset."""
    grid = np.meshgrid(*[np.arange(n) for n in data.shape[::-1]], indexing="ij")
    for shift in (0, 0.37):
        pixels = [axis + shift for axis in grid]
        for got, expected in zip(coords.pixel_to_world_values(*pixels), data.coords.pixel_to_world_values(*pixels)):
            np.testing.assert_allclose(got, expected, rtol=0, atol=1e-9)
    world = data.coords.pixel_to_world_values(*grid)
    for got, expected in zip(coords.world_to_pixel_values(*world), data.coords.world_to_pixel_values(*world)):
        np.testing.assert_allclose(got, expected, rtol=0, atol=1e-9)
    assert coords.world_axis_names == data.coords.world_axis_names
    assert coords.world_axis_units == data.coords.world_axis_units
    assert coords.pointing_offset == data.coords.pointing_offset


def test_the_coordinates_of_each_kind_of_dataset_round_trip_twice(irispy_test_files):
    scans = sorted(path for path in irispy_test_files if "3860258481_raster" in path.name)
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))  # a gWCS
    raster = raster_data(scans[:1], ["C II 1336"])[0]  # a FITS-TAB WCS
    raster.coords.pointing_offset = (1.5, -2.25)
    stack = raster_data(scans, ["C II 1336"], stack=True)[0]
    datasets = [
        sji,
        raster,
        stack,
        line_moments(raster, 1335.71),
        regrid_on_time(sji),
        north_up(sji),
        rebin(stack, (1, 2, 3, 1)),
    ]
    # the coordinates and styles alone
    for restored in twice([[data.coords, data.style] for data in datasets]):
        for (coords, style), data in zip(restored, datasets, strict=True):
            assert_same_coordinates(coords, data)
            assert style.color == data.style.color
            assert getattr(style.preferred_cmap, "name", None) == getattr(data.style.preferred_cmap, "name", None)
    assert sji.style.preferred_cmap.name == "irissji1330"


def test_a_session_restores_a_moments_map_on_its_raster_steps(irispy_test_files):
    raster = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["C II 1336"])[0]
    raster.coords.pointing_offset = (1.5, -2.25)
    maps = line_moments(raster, 1335.71)
    for (restored,) in twice(DataCollection([maps])):
        assert_same_coordinates(restored.coords, maps)
        for cid, expected in zip(restored.world_component_ids, maps.world_component_ids, strict=True):
            assert cid.label == expected.label
            np.testing.assert_allclose(restored[cid], maps[expected], rtol=0, atol=1e-9)


def test_a_session_restores_the_metadata_of_a_raster_and_a_slit_jaw_image(irispy_test_files):
    raster = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["C II 1336"])[0]
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    # glue leaves out what it cannot save: irispy's Time and SkyCoord
    left_out = [{"auxiliary times", "exposure FOV center"}, set()]
    for restored in twice(DataCollection([raster, sji])):
        for data, expected, missing in zip(restored, (raster, sji), left_out, strict=True):
            assert set(expected.meta) - set(data.meta) == missing
            for key, value in data.meta.items():
                if isinstance(expected.meta[key], u.Quantity):  # the exposure times and radial velocities
                    assert value.unit == expected.meta[key].unit
                np.testing.assert_array_equal(value, expected.meta[key])
        headers = restored[1].meta["frame_wcs_headers"]
        assert WCS(headers[5]).to_header_string() == WCS(sji.meta["frame_wcs_headers"][5]).to_header_string()
        assert _pointing(restored[1].meta, 5) == _pointing(sji.meta, 5)  # the Frame time tooltip


def test_an_aia_map_session_restores_its_colormap(qtbot, monkeypatch, tmp_path):
    glue_solar.setup()  # every sunpy colormap listed
    app = GlueApplication()
    qtbot.addWidget(app)
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))  # not glue's modal dialog
    aia = read_sunpy_map(sunpy.data.test.get_test_filepath("aia_171_level1.fits"))
    app.data_collection.append(aia)
    app.new_data_viewer(ImageViewer, data=aia)
    app.save_session(str(tmp_path / "aia.glu"))  # glue-core 1.27.0 alone fails on the map's colormap
    restored = GlueApplication.restore_session(str(tmp_path / "aia.glu"))
    qtbot.addWidget(restored)
    assert restored.data_collection[0].style.preferred_cmap.name == "sdoaia171"  # glue's restore drops it
    # its colours: glue's menu shows the first sunpy colormap of the same colours, here GOES-R SUVI 171's
    assert restored.viewers[0][0].layers[0].state.cmap == cmlist["sdoaia171"]


def test_a_session_restores_a_profile_along_the_last_axis_in_its_unit(qtbot, monkeypatch, tmp_path):
    installed = ProfileViewerState._update_priority is glue_patches._update_priority
    assert installed == glue_patches.needs_profile_restore_workaround()  # probes glue's own method
    assert not glue_patches.needs_profile_restore_workaround(glue_patches._update_priority)
    wcs = WCS(naxis=3)  # wavelength on the last axis, as an IRIS raster's
    wcs.wcs.ctype = ["WAVE", "HPLT-TAN", "HPLN-TAN"]
    wcs.wcs.cunit = ["Angstrom", "arcsec", "arcsec"]
    wcs.wcs.cdelt = [0.025, 0.33, 2]
    wcs.wcs.crval = [1335.7, 0, 0]
    cube = Data(label="cube", flux=np.arange(60.0).reshape(3, 4, 5), coords=wcs)
    app = GlueApplication()
    qtbot.addWidget(app)
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))
    app.data_collection.append(cube)
    saved = []
    for unit, limits in (("Angstrom", (1335.72, 1335.77)), ("nm", (133.572, 133.577))):
        state = app.new_data_viewer(ProfileViewer, data=cube).state
        state.x_att, state.x_display_unit = cube.world_component_ids[2], unit
        state.x_min, state.x_max = limits
        saved.append((state.x_att.label, state.x_display_unit, state.x_min, state.x_max))
    app.save_session(str(tmp_path / "profile.glu"))
    restored = GlueApplication.restore_session(str(tmp_path / "profile.glu"))  # glue-core 1.27.0 alone raises
    qtbot.addWidget(restored)
    states = [viewer.state for viewer in restored.viewers[0]]
    assert [(s.x_att.label, s.x_display_unit, s.x_min, s.x_max) for s in states] == saved
