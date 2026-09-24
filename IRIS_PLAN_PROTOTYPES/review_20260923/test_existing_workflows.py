"""Evidence of existing Glue workflows, without WP1/WP3/WP4/WP5 patches.

Run on released core, then core #2601 + Qt #70. See the active plan for
interpretation: correct arrays do not make scan indices into UTC coordinates.
"""
from types import SimpleNamespace

import numpy as np
import pytest
from astropy.wcs import WCS
from glue.core import Data, DataCollection
from glue.core.aggregate import mom1
from glue.viewers.profile.state import ProfileViewerState
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from matplotlib.backend_bases import MouseEvent

HAS_SLICE = hasattr(ProfileViewerState, 'slices')


@pytest.fixture
def cube_app(qtbot):
    scan, step, slit, wave = np.indices((4, 3, 5, 6))
    values = 1000 * scan + 100 * step + 10 * slit + wave
    wcs = WCS(naxis=4)
    wcs.wcs.ctype = ['WAVE', 'LINEAR', 'LINEAR', 'LINEAR']
    wcs.wcs.cunit = ['Angstrom', '', '', '']
    wcs.wcs.cname = ['Wavelength', 'Slit', 'Step', 'Scan']
    wcs.wcs.crval = [1400, 0, 0, 0]
    wcs.wcs.crpix = [1, 1, 1, 1]
    wcs.wcs.cdelt = [0.1, 1, 1, 1]
    data = Data(flux=values.astype(float), coords=wcs)
    app = GlueApplication(DataCollection([data])); qtbot.addWidget(app)
    yield data, app
    for tab in app.viewers:
        for viewer in list(tab):
            viewer.close(warn=False)


def image(app, data, x, y, slices):
    viewer = app.new_data_viewer(ImageViewer, data=data)
    viewer.state.x_att = data.pixel_component_ids[x]
    viewer.state.y_att = data.pixel_component_ids[y]
    viewer.state.slices = slices
    return viewer


def mouse(viewer, name, x, y, button=1):
    viewer.figure.canvas.draw()
    px, py = viewer.axes.transData.transform((x, y))
    event = MouseEvent(name, viewer.figure.canvas, px, py, button=button)
    viewer.figure.canvas.callbacks.process(name, event)


def select_point(viewer, x, y):
    viewer.toolbar.active_tool = 'image:point_selection'
    mouse(viewer, 'button_press_event', x, y)
    mouse(viewer, 'button_release_event', x, y)


def test_4d_time_wavelength_is_existing_axis_selection(cube_app):
    data, app = cube_app
    viewer = image(app, data, 3, 0, (0, 1, 2, 0))
    np.testing.assert_array_equal(viewer.state.layers[0].get_sliced_data(), data['flux'][:, 1, 2, :])
    # The same viewer becomes a spectrogram by swapping the vertical axis.
    viewer.state.y_att = data.pixel_component_ids[2]
    viewer.state.slices = (3, 1, 0, 0)
    np.testing.assert_array_equal(viewer.state.layers[0].get_sliced_data(), data['flux'][3, 1, :, :])


def test_point_subset_spectrum_curve_drag_and_release(cube_app):
    data, app = cube_app
    spatial = image(app, data, 1, 2, (0, 0, 0, 0))
    profile = app.new_data_viewer(ProfileViewer, data=data)
    profile.state.x_att = data.pixel_component_ids[3]
    profile.state.function = 'mean'
    select_point(spatial, 1, 2)
    subset = data.subsets[0]
    state = next(layer for layer in profile.state.layers if layer.layer is subset)
    np.testing.assert_allclose(state.profile[1], data['flux'][:, 1, 2, :].mean(axis=0))
    profile.state.x_att = data.pixel_component_ids[0]
    np.testing.assert_allclose(state.profile[1], data['flux'][:, 1, 2, :].mean(axis=1))
    # A spectral band is an intersection with an existing range subset.
    band = (data.pixel_component_ids[3] >= 1) & (data.pixel_component_ids[3] < 3)
    app.data_collection.subset_groups[0].subset_state &= band
    np.testing.assert_allclose(state.profile[1], data['flux'][:, 1, 2, 1:3].mean(axis=1))
    # Press-drag updates the same selection; release already holds it in place.
    mouse(spatial, 'button_press_event', 1, 2)
    mouse(spatial, 'motion_notify_event', 2, 3)
    mouse(spatial, 'button_release_event', 2, 3)
    expected = data['flux'][:, 2, 3, :].mean(axis=1)
    np.testing.assert_allclose(state.profile[1], expected)
    mouse(spatial, 'motion_notify_event', 0, 0, button=None)
    np.testing.assert_allclose(state.profile[1], expected)


@pytest.mark.skipif(not HAS_SLICE, reason='needs core #2596/#2601 and Qt #70')
def test_draft_slice_profile_switches_axes_but_selection_does_not_set_sliders(cube_app):
    data, app = cube_app
    spatial = image(app, data, 1, 2, (2, 0, 0, 4))
    profile = app.new_data_viewer(ProfileViewer, data=data)
    profile.state.function = 'slice'
    profile.state.x_att = data.world_component_ids[-1]
    profile.state.slices = (2, 1, 3, 4)
    np.testing.assert_array_equal(profile.state.layers[0].profile[1], data['flux'][2, 1, 3, :])
    profile.state.x_att = data.pixel_component_ids[0]
    np.testing.assert_array_equal(profile.state.layers[0].profile[1], data['flux'][:, 1, 3, 4])
    before = tuple(profile.state.slices)
    select_point(spatial, 0, 1)
    assert tuple(profile.state.slices) == before  # subset selection does not drive a different viewer's sliders


def test_profile_navigate_already_drives_image_wavelength_and_scan(cube_app):
    data, app = cube_app
    spatial = image(app, data, 1, 2, (0, 0, 0, 0))
    second = image(app, data, 1, 2, (0, 0, 0, 0))
    profile = app.new_data_viewer(ProfileViewer, data=data)
    tools = profile.toolbar.tools['profile-analysis']._profile_tools
    profile.state.x_att = data.pixel_component_ids[3]
    tools._on_nav_activate()
    tools.nav_mode.state.x = 4
    assert spatial.state.slices[-1] == second.state.slices[-1] == 4
    profile.state.x_att = data.pixel_component_ids[0]
    tools._on_nav_activate()
    tools.nav_mode.state.x = 2
    assert spatial.state.slices[0] == second.state.slices[0] == 2
    if HAS_SLICE:  # Qt #70 also fixes display-unit navigation.
        # WCSAxes uses pixel positions; an overridden unit uses numeric wavelengths.
        profile.state.x_att = data.world_component_ids[-1]
        profile.state.x_display_unit = 'Angstrom'
        tools._on_nav_activate()
        tools.nav_mode.state.x = 1400.3
        assert spatial.state.slices[-1] == 3


def test_point_subset_does_not_drive_other_image_slice(cube_app):
    data, app = cube_app
    spatial = image(app, data, 1, 2, (0, 0, 0, 0))
    temporal = image(app, data, 3, 0, (0, 0, 0, 0))
    select_point(spatial, 1, 2)
    assert temporal.state.slices == (0, 0, 0, 0)
    # Existing selection is a mask overlay, not a request to move this plane.


@pytest.mark.filterwarnings('ignore:Setting colormap using "color" key is deprecated:UserWarning')
@pytest.mark.filterwarnings("ignore:COPY_IF_NEEDED is no longer needed:astropy.utils.exceptions.AstropyPendingDeprecationWarning")
def test_stock_pv_slit_extracts_time_distance_and_navigates_parent(qtbot):
    from glue_qt.plugins.tools.pv_slicer.pv_slicer import PVSlicerMode
    values = np.arange(4 * 5 * 6).reshape((4, 5, 6)).astype(float)
    data = Data(flux=values)
    app = GlueApplication(DataCollection([data])); qtbot.addWidget(app)
    viewer = image(app, data, 2, 1, (0, 0, 0))
    tool = PVSlicerMode(viewer)
    tool._build_from_vertices([-0.5, 5.5], [2, 2])
    child = tool._slice_widget
    np.testing.assert_array_equal(child._im_array, values[:, 2, :])
    event = SimpleNamespace(xdata=3, ydata=2, inaxes=child.axes, canvas=child.axes.figure.canvas)
    child._on_click(event)
    assert viewer.state.slices[0] == 2
    assert child._pos_in_parent(event) == (3, 2, 2)
    child.close(); tool.close(); viewer.close(warn=False)


def test_playback_exists_and_wraps(qtbot):
    from glue_qt.viewers.common.data_slice_widget import SliceWidget
    widget = SliceWidget(); qtbot.addWidget(widget)
    widget.value_slice_center.setRange(0, 3)
    widget.value_slice_center.setValue(3)
    widget._adjust_play('forw')
    assert widget._play_timer.isActive()
    widget._play_slice()
    assert widget.value_slice_center.value() == 0
    widget._adjust_play('stop')
    assert not widget._play_timer.isActive()


def test_generic_moment_is_already_available_but_in_pixel_units():
    values = np.array([1., 2., 1.])[:, None, None]
    np.testing.assert_allclose(mom1(values, axis=0), [[1.]])


@pytest.mark.skipif(not HAS_SLICE, reason='uses the draft slice-profile controls')
def test_real_stacked_iris_axis_switching(qtbot, irispy_test_files):
    from glue_solar.sources.loaders.iris import raster_data
    names = [f'iris_l2_20140329_140938_3860258481_raster_t000_r0000{i}.fits' for i in range(3)]
    paths = [next(path for path in irispy_test_files if path.name == name) for name in names]
    data = raster_data(paths, ['C II 1336'], stack=True)[0]
    app = GlueApplication(DataCollection([data])); qtbot.addWidget(app)
    view = image(app, data, 3, 0, (0, 2, 30, 0))
    flux = data.main_components[0]
    np.testing.assert_allclose(view.state.layers[0].get_sliced_data(), data[flux][:, 2, 30, :], equal_nan=True)
    assert not view.toolbar.tools['slice'].enabled  # stock Qt path tool is limited to 3D
    profile = app.new_data_viewer(ProfileViewer, data=data)
    profile.state.function = 'slice'
    profile.state.x_att = data.world_component_ids[0]  # Scan is a coordinate, Time is a data component
    profile.state.slices = (0, 2, 30, 4)
    np.testing.assert_allclose(profile.state.layers[0].profile[1], data[flux][:, 2, 30, 4], equal_nan=True)
    assert data.id['Time'] not in type(profile.state).x_att.get_choices(profile.state)
    profile.state.x_att = data.world_component_ids[-1]
    profile.state.slices = (1, 2, 30, 0)
    np.testing.assert_allclose(profile.state.layers[0].profile[1], data[flux][1, 2, 30, :], equal_nan=True)
    view.close(warn=False); profile.close(warn=False)
