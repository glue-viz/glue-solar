"""
Sessions keep the coordinates of every kind of dataset glue-solar makes from IRIS data, on irispy's test files.
"""

import numpy as np
from glue.core import DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer

from glue_solar.conftest import find_irispy_test_file
from glue_solar.regrid import north_up, rebin, regrid_on_time
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.sources.moments import line_moments
from glue_solar.tests.test_quicklook import SCAN

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
    # the coordinates alone: sessions cannot save the metadata and colormaps of most of these yet
    for restored in twice([data.coords for data in datasets]):
        for coords, data in zip(restored, datasets, strict=True):
            assert_same_coordinates(coords, data)


def test_a_session_restores_a_moments_map_on_its_raster_steps(irispy_test_files):
    raster = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["C II 1336"])[0]
    raster.coords.pointing_offset = (1.5, -2.25)
    maps = line_moments(raster, 1335.71)
    for (restored,) in twice(DataCollection([maps])):
        assert_same_coordinates(restored.coords, maps)
        for cid, expected in zip(restored.world_component_ids, maps.world_component_ids, strict=True):
            assert cid.label == expected.label
            np.testing.assert_allclose(restored[cid], maps[expected], rtol=0, atol=1e-9)
