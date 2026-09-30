"""
Checks that the recipes in the user guides do what they say, on the irispy fixtures.
"""

import re
import warnings

import numpy as np
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer

import astropy.units as u

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.tests.helpers import select_point

SNS = "iris_l2_20210905_001833_3620258102_{}.fits"


def arcsec(text):
    """The two angles of a WCSAxes readout such as '12" -34" (world)', in arcsec."""
    return [float(value.replace("−", "-")) for value in re.findall(r"(−?-?[\d.]+)\"", text)]


def test_scripting_recipe(qtbot, irispy_test_files):
    # docs/user_guide/scripting-iris-data.rst
    glue_solar.setup()
    rasters = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))
    app = GlueApplication()
    qtbot.addWidget(app)
    data_collection = app.data_collection
    data_collection.extend([*rasters, sji])
    raster = rasters[0]
    step, slit, pixel = 90, 20, 14
    wavelength, latitude, longitude = raster.coords.pixel_to_world_values(pixel, slit, step)

    # the coordinates are what the readout shows at a Pixel point on the raster map
    viewer = app.new_data_viewer(ImageViewer, data=raster)
    viewer.state.x_att, viewer.state.y_att = raster.pixel_component_ids[0], raster.pixel_component_ids[1]
    select_point(viewer, step, slit)
    point = data_collection.subset_groups[-1].subset_state
    assert isinstance(point, PixelSubsetState)
    assert [s.start for s in point.slices[:2]] == [step, slit]
    viewer.figure.canvas.draw()
    readout = viewer.axes.format_coord(step, slit)
    assert arcsec(readout) == [round(latitude), round(longitude)]  # WCS order: latitude first
    assert 1390e-10 < wavelength < 1410e-10  # Si IV 1403, in metres
    assert raster.coords.world_axis_units[0] == "m"
    assert (latitude * u.arcsec).unit == u.arcsec

    times = raster["Time"][:, 0, 0]
    assert times.dtype.kind == "M"
    assert len(times) == raster.shape[0]
    assert sji["Time"][:, 0, 0].dtype.kind == "M"

    # the Profile viewer's Mean against Wavelength is the mean over every step and slit position
    values = raster[raster.main_components[0]]
    profile = app.new_data_viewer(ProfileViewer, data=raster)
    profile.state.function = "mean"
    profile.state.x_att = raster.world_component_ids[2]
    _, mean = profile.state.layers[0].profile
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # wavelengths with no valid sample give NaN
        expected = np.nanmean(values, axis=(0, 1), dtype=float)
    np.testing.assert_allclose(mean, expected, rtol=1e-6)
    np.testing.assert_array_equal(values[step, slit], values[step, slit, :])
