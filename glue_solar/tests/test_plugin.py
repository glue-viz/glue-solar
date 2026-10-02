import os
import shutil
import subprocess
import sys
from collections import Counter

import numpy as np
import pytest
from glue.config import colormaps, data_factory, menubar_plugin, settings, startup_action
from glue.core import Data
from glue.core.data_factories import load_data
from glue.viewers.image.state import AggregateSlice
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from irispy.io import read_files
from matplotlib.backend_bases import MouseEvent

from astropy.io import fits
from astropy.wcs import WCS

import glue_solar
from glue_solar import glue_patches
from glue_solar.conftest import MD5, OBS_A, find_irispy_test_file
from glue_solar.sources.iris import iris_quicklook, is_iris_fits, link_iris, quicklook_iris
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.sources.maps import read_sunpy_map
from glue_solar.tests.helpers import count_tick_work


def test_setup_registers_hooks():
    glue_solar.setup()
    glue_solar.setup()  # glue calls it once; tests and reloads must not duplicate the tool
    assert "IRIS: browse observations…" in [label for label, _ in menubar_plugin]
    assert ("IRIS: link helioprojective coordinates", link_iris) in list(menubar_plugin)
    assert ("IRIS: quicklook…", quicklook_iris) in list(menubar_plugin)
    assert startup_action.members["iris_quicklook"] is iris_quicklook
    assert ImageViewer.tools.count("solar:frame_time") == 1
    assert ImageViewer.tools.count("solar:coordinate") == 1
    assert ImageViewer.tools.count("solar:hide_axes") == 1
    assert ImageViewer.tools.count("solar:cursor_readout") == (0 if hasattr(ImageViewer, "cursor_status") else 1)
    iris = next(f for f in data_factory if f.label == "IRIS Level 2 FITS")
    for label in ("FITS file", "sunpy Map"):  # both also match IRIS files; ours must win
        other = next(f for f in data_factory if f.label == label)
        assert iris.priority > (other.priority or 0)


_PLUGIN_LOAD = """
import sys

import glue_solar

glue_solar.setup()
print(*[name for name in ("irispy", "sunpy.map", "ndcube") if name in sys.modules], "|")

import sunpy.data.test
import sunpy.map
from glue.core.parsers import parse_data

print(parse_data(sunpy.map.Map(sunpy.data.test.get_test_filepath("aia_171_level1.fits")), "aia").label)
"""


def test_plugin_load_leaves_the_readers_libraries_to_the_first_read():
    # in a process of its own, since the other tests import them
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    result = subprocess.run([sys.executable, "-c", _PLUGIN_LOAD], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-2000:]
    # a map made after the plugin loaded still finds its parser
    assert result.stdout.splitlines()[:2] == ["|", "aia-AIA 171.0 Angstrom 2011-02-15 00:00:00"]


def test_data_factory_claims_only_iris_files(iris_tree):
    d, t, o = OBS_A
    sji = iris_tree / f"{MD5}iris_l2_{d}_{t}_{o}_SJI_1400_t000.fits.gz"
    aia = iris_tree / f"{MD5}iris_l2_{d}_{t}_{o}_SDO" / f"aia_l2_{d}_{t}_{o}_171.fits"
    assert is_iris_fits(str(sji))
    assert not is_iris_fits(str(aia))  # TELESCOP is blank on the cutouts
    assert not is_iris_fits(str(iris_tree / "notes.txt"))


def test_open_real_sji_through_load_data(irispy_test_files):
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    data = load_data(str(path))
    assert data.label == "SJI_1400-3620258102-2021-09-05T00:18:33"
    assert data.shape == (62, 40, 37)
    assert data.style.preferred_cmap.name == "irissji1400"
    # SJI keeps time in its gWCS rather than an extra coordinate; every frame gets its UTC time
    expected_times = read_files(str(path), memmap=False, uncertainty=False).axis_world_coords("time")[0]
    np.testing.assert_array_equal(data["Time"][:, 0, 0], expected_times.utc.to_value("datetime64"))
    np.testing.assert_array_equal(data["Time"][:, -1, -1], expected_times.utc.to_value("datetime64"))


def test_open_real_raster_through_load_data(irispy_test_files):
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits")
    datasets = load_data(str(path))
    assert len(datasets) == 9
    assert datasets[0].label == "C_II_1336-3860258481-2014-03-29T14:09:38-r00000"  # its raster number
    assert datasets[0].shape == (8, 109, 17)
    assert datasets[0].find_component_id("Time") is not None


def test_open_synthetic_sji_through_load_data(iris_tree):
    # The synthetic fixtures are complete enough for irispy's readers
    path = next(iris_tree.glob(f"{MD5}iris_l2_20250328_*_SJI_1400_t000.fits.gz"))
    data = load_data(str(path))
    assert data.shape == (3, 4, 5)
    assert tuple(data.coords.world_axis_physical_types) == (
        "custom:pos.helioprojective.lon",
        "custom:pos.helioprojective.lat",
        "time",
    )


def test_open_synthetic_raster_through_load_data(iris_tree):
    raster_dir = next(iris_tree.glob(f"{MD5}iris_l2_20250328_*_raster"))
    path = sorted(raster_dir.glob("*.fits"))[0]
    datasets = load_data(str(path))
    assert len(datasets) == 2
    for data in datasets:
        assert data.shape == (3, 4, 5)
        assert tuple(data.coords.world_axis_physical_types) == (
            "em.wl",
            "custom:pos.helioprojective.lat",
            "custom:pos.helioprojective.lon",
        )


def test_autolink_synthetic_sji_raster(iris_tree):
    # SJI + raster autolink with no manual step: glue must pair the
    # helioprojective axes across the two instruments (permuting the world
    # order and slicing the SJI time axis away).
    try:
        from glue.plugins.wcs_autolinking.wcs_autolinking import permuted_values_functions  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("glue-core without APE-14 low-level WCS autolinking")
    from glue.core import DataCollection
    from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink

    sji = load_data(str(next(iris_tree.glob(f"{MD5}iris_l2_20250328_*_SJI_1400_t000.fits.gz"))))
    raster_dir = next(iris_tree.glob(f"{MD5}iris_l2_20250328_*_raster"))
    raster = load_data(str(sorted(raster_dir.glob("*.fits"))[0]))[0]

    links = wcs_autolink(DataCollection([sji, raster]))
    assert len(links) == 1
    link = links[0]
    assert len(link) == 4

    # The two celestial pixel axes on each side; the SJI time axis and the
    # raster wavelength axis are sliced away
    assert {cid.axis for cid in link.cids1} == {1, 2}
    assert {cid.axis for cid in link.cids2} == {0, 1}


def test_frame_time_tool_follows_the_sliders(qtbot, irispy_test_files):
    glue_solar.setup()
    sji = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    sji = load_data(str(sji))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(sji)
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    tool = viewer.toolbar.tools["solar:frame_time"]
    stamp = [np.datetime_as_string(t, unit="ms") for t in sji["Time"][:, 0, 0]]
    exposure = sji["Exposure time"][:, 0, 0]

    viewer.state.slices = (5, 0, 0)
    assert tool.label.text() == f"{stamp[5]} UTC · exp {exposure[5]:.4g} s"
    assert f"PZT offset {sji.meta['pztx'][5]:.2f}″, {sji.meta['pzty'][5]:.2f}″" in tool.label.toolTip()

    viewer.state.x_att = sji.pixel_component_ids[0]  # exposure against slit spans the whole sequence
    shortest, longest = f"{exposure.min():.4g}", f"{exposure.max():.4g}"
    span = shortest if shortest == longest else f"{shortest}–{longest}"
    assert tool.label.text() == f"{stamp[0]} – {stamp[-1]} UTC · exp {span} s"
    assert tool.label.toolTip() == ""  # no single frame, so no pointing

    # the button leaves the mouse mode on, which glue-qt ends for a plain button
    viewer.toolbar.active_tool = "image:point_selection"
    pixel, button = viewer.toolbar.active_tool, viewer.toolbar.actions["solar:frame_time"]
    button.trigger()
    assert (tool.label.isHidden(), viewer.toolbar.active_tool) == (True, pixel)
    button.trigger()
    assert (tool.label.isHidden(), viewer.toolbar.active_tool) == (False, pixel)

    # Any loader's datetime component will do, whatever it is called
    still = Data(label="still", flux=np.zeros((4, 5)), obs_date=np.full((4, 5), np.datetime64("2020-01-01T12:00:00")))
    app.data_collection.append(still)
    other = app.new_data_viewer(ImageViewer, data=still)
    assert other.toolbar.tools["solar:frame_time"].label.text() == "2020-01-01T12:00:00.000 UTC"


def test_frame_time_tool_survives_an_empty_collapse(qtbot):
    glue_solar.setup()
    cube = Data(label="cube", flux=np.zeros((4, 5, 6)), obs_date=np.full((4, 5, 6), np.datetime64("2020-01-01T12:00:00")))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(cube)
    viewer = app.new_data_viewer(ImageViewer, data=cube)
    tool = viewer.toolbar.tools["solar:frame_time"]
    viewer.state.slices = (AggregateSlice(slice(2, 2), 2, np.nanmean), 0, 0)
    assert tool.label.text() == ""


def test_cursor_readout_shows_position_and_value(qtbot, irispy_test_files):
    if hasattr(ImageViewer, "cursor_status"):
        pytest.skip("this glue-qt shows the position under the mouse itself")
    glue_solar.setup()
    sji = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    sji = load_data(str(sji))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(sji)
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    tool = viewer.toolbar.tools["solar:cursor_readout"]
    icons = [t.icon for t in viewer.toolbar.tools.values()]
    assert all(icons.count(viewer.toolbar.tools[t].icon) == 1 for t in ("solar:frame_time", "solar:cursor_readout"))
    canvas = viewer.axes.figure.canvas
    canvas.draw()  # WCSAxes only formats positions once drawn

    def move_to(x, y):
        event = MouseEvent("motion_notify_event", canvas, *viewer.axes.transData.transform((x, y)))
        canvas.callbacks.process("motion_notify_event", event)
        return event

    event = move_to(10, 20)
    message = viewer.statusBar().currentMessage()
    assert message == tool.describe(event.xdata, event.ydata)
    assert message.startswith(viewer.axes.format_coord(event.xdata, event.ydata))
    assert message.endswith(f"| value = {float(sji[viewer.layers[0].state.attribute, (0, 20, 10)]):.6g}")
    viewer.state.slices = (5, 0, 0)
    assert tool.describe(10, 20).endswith(f"| value = {float(sji[viewer.layers[0].state.attribute, (5, 20, 10)]):.6g}")
    assert tool.describe(-3, 20) == viewer.axes.format_coord(-3, 20)  # outside the image: position only

    viewer.toolbar.active_tool = "image:point_selection"
    pixel, button = viewer.toolbar.active_tool, viewer.toolbar.actions["solar:cursor_readout"]
    button.trigger()  # hide, leaving the mouse mode on
    assert viewer.toolbar.active_tool is pixel
    assert viewer.statusBar().currentMessage() == ""
    move_to(10, 20)
    assert viewer.statusBar().currentMessage() == ""
    button.trigger()  # show again
    assert viewer.toolbar.active_tool is pixel
    event = move_to(10, 20)
    assert viewer.statusBar().currentMessage() == tool.describe(event.xdata, event.ydata) != ""

    # Attributes not named after their dataset are named in the readout
    still = Data(label="still", flux=np.full((4, 5), 3.5))
    app.data_collection.append(still)
    other = app.new_data_viewer(ImageViewer, data=still)
    assert other.toolbar.tools["solar:cursor_readout"].describe(1, 1).endswith(" | flux = 3.5")


def margins(viewer):
    """The colours the canvas draws left of and below the viewer's axes, where WCSAxes puts its ticks and labels."""
    viewer.figure.canvas.draw()
    rgba = np.asarray(viewer.figure.canvas.buffer_rgba())
    box = viewer.axes.get_window_extent()
    left, below = rgba[:, : int(box.x0) - 2], rgba[rgba.shape[0] - int(box.y0) + 2 :]
    return {tuple(colour) for part in (left, below) for colour in part.reshape(-1, 4)}


def test_hide_axes(qtbot, monkeypatch, irispy_test_files):
    from astropy.visualization.wcsaxes.coordinate_helpers import CoordinateHelper

    from glue_solar.tests.helpers import mouse

    glue_solar.setup()
    sji = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    sji = load_data(str(sji))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(sji)
    shown = app.new_data_viewer(ImageViewer, data=sji)
    monkeypatch.setattr(settings, "SOLAR_SHOW_AXES", False)  # for new viewers
    hidden = app.new_data_viewer(ImageViewer, data=sji)
    assert (shown.state.show_axes, shown.axes.axison) == (True, True)
    assert (hidden.state.show_axes, hidden.axes.axison) == (False, False)
    placed = Counter()
    update_ticks = CoordinateHelper._update_ticks

    def counted(self):
        placed[self.parent_axes] += 1
        return update_ticks(self)

    monkeypatch.setattr(CoordinateHelper, "_update_ticks", counted)
    for frame in (0, 5):
        for viewer in (shown, hidden):
            viewer.state.slices = (frame, 0, 0)
            placed.clear()
            viewer.figure.canvas.draw()
            assert (placed[viewer.axes] > 0) == viewer.state.show_axes  # no tick placement in a draw without axes
        assert len(margins(shown)) > 1  # ticks and labels
        assert len(margins(hidden)) == 1  # the background only
        # the mouse-over readout stays in world coordinates, placing the ticks once after the step to format them
        placed.clear()
        assert hidden.axes.format_coord(10, 20) == shown.axes.format_coord(10, 20)
        assert hidden.axes.format_coord(11, 21) == shown.axes.format_coord(11, 21)
        assert shown.axes.format_coord(10, 20).endswith("\" (world)")  # arcsec
        assert placed[hidden.axes] == 3  # longitude, latitude and the hidden time

    # the button repaints the viewer and leaves its mouse mode on, which glue-qt ends for a plain button
    hidden.toolbar.active_tool = "image:point_selection"
    pixel, button = hidden.toolbar.active_tool, hidden.toolbar.actions["solar:hide_axes"]
    draw, draws = hidden.figure.canvas.draw, []
    monkeypatch.setattr(hidden.figure.canvas, "draw", lambda *args: draws.append(args) or draw(*args))
    for show in (True, False):
        qtbot.wait(10)  # draws already queued
        draws.clear()
        button.trigger()
        assert (hidden.state.show_axes, hidden.axes.axison, hidden.toolbar.active_tool) == (show, show, pixel)
        qtbot.waitUntil(lambda: bool(draws), timeout=1000)
        assert (len(margins(hidden)) > 1) == show
    mouse(hidden, "button_press_event", 10, 20)  # a Pixel click: subsets work without axes
    mouse(hidden, "button_release_event", 10, 20)
    [group] = app.data_collection.subset_groups
    assert [(s.start, s.stop) for s in group.subset_state.slices] == [(None, None), (20, 21), (10, 11)]
    for viewer in (shown, hidden):
        viewer.state.slices = (6, 0, 0)  # a readout between a step and its draw, as during playback
        assert viewer.axes.format_coord(10, 20).endswith("\" (world)")
    full = shown.axes.format_coord(10.3, 20.7)
    for viewer in (shown, hidden):
        viewer.state.x_min, viewer.state.x_max, viewer.state.y_min, viewer.state.y_max = 10, 11, 20, 21
        viewer.figure.canvas.draw()
    assert hidden.axes.format_coord(10.3, 20.7) == shown.axes.format_coord(10.3, 20.7) != full  # finer, zoomed in


def test_sessions_keep_each_viewers_axes(qtbot, monkeypatch, tmp_path):
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    image = Data(label="image", flux=np.arange(20.0).reshape(4, 5))
    app.data_collection.append(image)
    viewers = [app.new_data_viewer(ImageViewer, data=image) for _ in range(2)]
    viewers[0].toolbar.actions["solar:hide_axes"].trigger()
    app.save_session(str(tmp_path / "axes.glu"))
    monkeypatch.setattr(settings, "SOLAR_SHOW_AXES", False)  # applies to new viewers only
    restored = GlueApplication.restore_session(str(tmp_path / "axes.glu"))
    qtbot.addWidget(restored)
    assert [(viewer.state.show_axes, viewer.axes.axison) for viewer in restored.viewers[0]] == [
        (False, False),
        (True, True),
    ]


def _cmap_menu(viewer):
    """The colormap menu of the viewer's first layer."""
    return viewer.layer_view().layout_style_widgets[viewer.layers[0]].ui.combodata_cmap


# sunpy's RHESSI test image has no observer position
@pytest.mark.filterwarnings("ignore:Missing metadata for observer")
def test_only_the_colormaps_data_ask_for_are_listed(qtbot, monkeypatch, irispy_test_files):
    import sunpy.data.test
    from sunpy.visualization.colormaps import cmlist

    # glue's own colormaps only: glue-qt draws every one listed whenever it builds an Image layer's menu
    monkeypatch.setattr(colormaps, "_members", colormaps.default_members())
    glue_solar.setup()
    glue_solar.setup()
    iris_and_aia = [cmlist[name] for name in sorted(cmlist) if name.startswith(("irissji", "sdoaia"))]
    assert colormaps.members[len(colormaps.default_members()):] == [[cmap.name, cmap] for cmap in iris_and_aia]
    sji = load_data(str(find_irispy_test_file(irispy_test_files, SIT_AND_STARE.format("SJI_1400_t000"))))
    rhessi = read_sunpy_map(sunpy.data.test.get_test_filepath("hsi_image_20101016_191218.fits"))
    assert colormaps.members[-1] == [cmlist["rhessi"].name, cmlist["rhessi"]]  # a map lists its own
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([sji, rhessi])
    for data, cmap in ((sji, cmlist["irissji1400"]), (rhessi, cmlist["rhessi"])):
        assert _cmap_menu(app.new_data_viewer(ImageViewer, data=data)).currentText() == cmap.name


def test_a_session_restores_a_sunpy_colormap_it_names(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(colormaps, "_members", colormaps.default_members())
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    image = Data(label="image", flux=np.arange(20.0).reshape(4, 5))
    app.data_collection.append(image)
    app.new_data_viewer(ImageViewer, data=image)
    app.save_session(str(tmp_path / "cmap.glu"))
    session = (tmp_path / "cmap.glu").read_text()
    # glue restores a colormap by its name, here one that setup() does not list
    (tmp_path / "cmap.glu").write_text(session.replace('"cmap": "gray"', '"cmap": "rhessi"'))
    restored = GlueApplication.restore_session(str(tmp_path / "cmap.glu"))
    qtbot.addWidget(restored)
    assert _cmap_menu(restored.viewers[0][0]).currentText() == "rhessi"


def test_iris_image_layers_render_nan_transparent(qtbot, irispy_test_files):
    sji = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    sji = load_data(str(sji))
    still = Data(label="still", flux=np.array([[np.nan, 1.0], [2.0, 3.0]]))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([sji, still])

    viewer = app.new_data_viewer(ImageViewer, data=sji)
    assert viewer.layers[0].state.cmap_bad == (0, 0, 0, 0)
    frame = sji[viewer.layers[0].state.attribute][0]
    iy, ix = np.argwhere(np.isnan(frame))[0]
    image = viewer.axes._composite(bounds=[(-0.5, frame.shape[0] - 0.5, frame.shape[0]), (-0.5, frame.shape[1] - 0.5, frame.shape[1])])
    np.testing.assert_array_equal(image[iy, ix], [1, 1, 1, 1])  # the white background shows through

    other = app.new_data_viewer(ImageViewer, data=still)  # not IRIS: glue's default stays
    assert other.layers[0].state.cmap_bad is None


def test_aia_cutout_fill_renders_transparent(qtbot, tmp_path, iris_tree):
    d, t, o = OBS_A
    source = iris_tree / f"{MD5}iris_l2_{d}_{t}_{o}_SDO" / f"aia_l2_{d}_{t}_{o}_171.fits"
    clean = image_data(source)
    assert not np.isnan(clean[clean.main_components[0]]).any()  # no fill

    path = tmp_path / source.name
    shutil.copy2(source, path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].data[0, 1, 2] = -200
        hdul[0].data[0, 2, 3] = -199  # unverified as missing in AIA cutouts, so it stays data
    aia = image_data(path)
    flux = np.asarray(aia[aia.main_components[0]])
    assert flux.dtype == np.float32
    np.testing.assert_array_equal(np.argwhere(np.isnan(flux)), [[0, 1, 2]])
    assert flux[0, 2, 3] == -199

    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(aia)
    viewer = app.new_data_viewer(ImageViewer, data=aia)
    image = viewer.axes._composite(bounds=[(-0.5, 3.5, 4), (-0.5, 4.5, 5)])
    np.testing.assert_array_equal(image[1, 2], [1, 1, 1, 1])  # the white background shows through


def test_slice_sliders_follow_a_drag_with_its_latest_position(qtbot):
    from qtpy import QtCore, QtWidgets

    glue_solar.setup()
    cube = Data(label="cube", flux=np.zeros((30, 4, 5)))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(cube)
    viewer = app.new_data_viewer(ImageViewer, data=cube)

    def sliders():
        return viewer.options_widget().findChildren(QtWidgets.QSlider, "value_slice_center")

    [slider] = sliders()
    assert not slider.hasTracking()
    applied = []
    viewer.state.add_callback("slices", lambda slices: applied.append(slices[0]))
    slider.setSliderDown(True)  # a drag across ten positions, as Qt delivers input queued behind a redraw
    for position in range(11, 21):
        slider.setSliderPosition(position)
    assert applied == []  # nothing applied at each position
    later = []
    QtCore.QTimer.singleShot(1, lambda: later.append(list(applied)))
    qtbot.waitUntil(lambda: bool(later))
    assert later == [[20]]  # only the latest, applied with no wait of its own
    slider.setSliderPosition(25)
    slider.setSliderDown(False)  # the release applies the last position
    assert viewer.state.slices[0] == 25

    slider.setValue(3)  # keys, clicks and playback apply at once
    assert viewer.state.slices[0] == 3

    viewer.state.x_att = cube.pixel_component_ids[0]  # glue-qt rebuilds the sliders
    assert sliders()
    assert not any(slider.hasTracking() for slider in sliders())



# glue-qt 0.4.2's PV slice window sets its colormap through glue's deprecated 'color' key, and its pvextractor
# imports spectral-cube, which uses astropy's deprecated COPY_IF_NEEDED where spectral-cube is installed
@pytest.mark.filterwarnings("ignore:Setting colormap using")
@pytest.mark.filterwarnings("ignore:COPY_IF_NEEDED is no longer needed")
def test_a_pv_slice_click_leaves_numbers_in_the_slices(qtbot, irispy_test_files):
    from glue_qt.plugins.tools.pv_slicer import pv_slicer

    from glue_solar import glue_patches

    installed = pv_slicer.PVSliceWidget._sync_slice is glue_patches.sync_pv_slice
    assert installed == glue_patches.needs_pv_slice_workaround()  # probes glue-qt's own function
    assert not glue_patches.needs_pv_slice_workaround(glue_patches.sync_pv_slice)
    glue_solar.setup()
    sji = load_data(str(find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(sji)
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    tool = viewer.toolbar.tools["slice"]
    tool._build_from_vertices(np.array([5.0, 30.0]), np.array([10.0, 30.0]))  # a path drawn on the frame
    widget = tool._slice_widget
    canvas = widget.axes.figure.canvas
    canvas.draw()
    # a click in the PV slice window at frame 7 moves the viewer to it
    click = MouseEvent("button_press_event", canvas, *widget.axes.transData.transform((3, 7)), button=1)
    widget._sync_slice(click)
    assert viewer.state.slices[0] == 7
    assert not any(isinstance(s, str) for s in viewer.state.slices)
    viewer.state.y_att_world = sji.world_component_ids[0]  # glue-qt 0.4.2 alone raises int('y') here
    assert viewer.state.y_att.axis == 0


SIT_AND_STARE = "iris_l2_20210905_001833_3620258102_{}.fits"
PATCHED_LABELS = (glue_patches.update_x_axislabel, glue_patches.update_y_axislabel)


def test_axis_label_workaround_installs_only_where_glue_needs_it(qtbot, monkeypatch, irispy_test_files):
    installed = ImageViewer.update_x_axislabel is glue_patches.update_x_axislabel
    assert installed == glue_patches.needs_axis_label_workaround()  # probes glue-qt's own methods
    assert not glue_patches.needs_axis_label_workaround(PATCHED_LABELS)
    glue_solar.setup()
    sji = load_data(str(find_irispy_test_file(irispy_test_files, SIT_AND_STARE.format("SJI_1400_t000"))))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(sji)
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    viewer.figure.canvas.draw()
    calls = count_tick_work(monkeypatch, viewer.axes)
    coords = viewer.axes.coords
    viewer.state.slices = (5, 0, 0)  # a frame step
    assert viewer.axes.coords is not coords  # glue reset the axes, and set both labels twice
    # glue-core 1.27.0 alone: 2 set_xlabel, 2 set_ylabel and 12 tick updates, then the draw places them again
    assert calls == {}
    viewer.figure.canvas.draw()
    assert calls == {"_update_ticks": 3}  # one per coordinate: longitude, latitude and the hidden time
    draw, draws = viewer.figure.canvas.draw, []
    monkeypatch.setattr(viewer.figure.canvas, "draw", lambda *args: draws.append(args) or draw(*args))
    qtbot.wait(10)  # draws already queued
    draws.clear()
    viewer.state.x_axislabel = "typed"  # in the axes options: it shows at once
    qtbot.waitUntil(lambda: bool(draws), timeout=1000)
    assert viewer.axes.coords[0].get_axislabel() == "typed"
    app.data_collection.remove(sji)  # glue keeps x_att without its reference data
    viewer.state.x_axislabel, viewer.state.y_axislabel_weight = "empty", "bold"


def test_a_slit_jaw_redraw_reuses_its_coordinates(qtbot, monkeypatch, irispy_test_files):
    glue_solar.setup()
    sji = image_data(find_irispy_test_file(irispy_test_files, SIT_AND_STARE.format("SJI_1400_t000")))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(sji)
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    wrapped = sji.coords._wcs
    convert, inputs = wrapped.pixel_to_world_values, []

    def counted(*pixel):
        inputs.append(tuple(np.asarray(p).tobytes() for p in pixel))
        return convert(*pixel)

    monkeypatch.setattr(wrapped, "pixel_to_world_values", counted)
    for frame in (0, 5):
        viewer.state.slices = (frame, 0, 0)
        inputs.clear()
        viewer.figure.canvas.draw()
        # WCSAxes asks most of its questions twice in a draw (without the memo: 37 conversions, 17 different)
        assert inputs
        assert len(set(inputs)) == len(inputs)
        inputs.clear()
        viewer.figure.canvas.draw()
        assert inputs == []  # an unchanged redraw, as for a subset or contrast change, converts nothing


def drawn_labels(viewer):
    """The viewer's canvas, and the text, spines and box of each WCSAxes coordinate's axis label on a spine."""
    canvas = viewer.figure.canvas
    canvas.draw()
    labels = [
        (coord.get_axislabel(), coord.get_axislabel_position(), coord._axislabels.get_window_extent().bounds)
        for coords in viewer.axes._all_coords  # the world coordinates and any overlay, such as exposure numbers
        for coord in coords
        if coord.get_axislabel_position()
    ]
    return bytes(canvas.buffer_rgba()), labels


def own_names(viewer):
    """Whether each world coordinate labelled on a spine has its own name as its label."""
    names = viewer.state.reference_data.coords.world_axis_names
    shown = [coord for coord in viewer.axes.coords if coord.get_axislabel_position()]
    return all(coord.get_axislabel() == names[coord.coord_index] for coord in shown)


SCANNING = "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits"


@pytest.mark.parametrize(
    "case",
    [
        "slit-jaw",
        "slit-jaw rolled 30°",
        "raster map",
        "spectrogram",
        "sit-and-stare exposures",
        "λ–time",
        "map",
        "no WCS",
        "λ–step",
        "slit-jaw rolled 60°",
    ],
)
def test_axis_labels_on_their_coordinates_draw_as_glues(qtbot, tmp_path, irispy_test_files, case):
    from glue_solar.conftest import OBS_A, _header, _write_image, startobs

    def rolled(roll):
        d, t, o = OBS_A
        path = tmp_path / f"iris_l2_{d}_{t}_{o}_SJI_1400_t000.fits"
        _write_image(path, _header("SJI", o, startobs(d, t), TDESC1="SJI_1400", TWAVE1=1400.0, NWIN=1), roll=roll)
        return image_data(path)

    def raster(name, window):
        return raster_data([find_irispy_test_file(irispy_test_files, name)], [window])[0]

    def plain_map():
        wcs = WCS(naxis=2)
        wcs.wcs.ctype, wcs.wcs.cunit = ["HPLN-TAN", "HPLT-TAN"], ["arcsec", "arcsec"]
        wcs.wcs.crpix, wcs.wcs.cdelt, wcs.wcs.crval = [25, 30], [0.6, 0.6], [100, -200]
        return Data(label="map", flux=np.random.default_rng(0).random((60, 50)), coords=wcs)

    def cube():
        return Data(label="cube", flux=np.random.default_rng(1).random((8, 40, 50)))

    sji = find_irispy_test_file(irispy_test_files, SIT_AND_STARE.format("SJI_1400_t000"))
    sit_and_stare = SIT_AND_STARE.format("raster_t000_r00000")
    # the dataset, its x and y pixel axes, and the slices of two steps, the second after an axis swap
    data, x, y, steps = {
        "slit-jaw": (lambda: image_data(sji), 2, 1, [(5, 0, 0), (6, 0, 0)]),
        "slit-jaw rolled 30°": (lambda: rolled(30), 2, 1, [(1, 0, 0), (2, 0, 0)]),
        "raster map": (lambda: raster(SCANNING, "C II 1336"), 0, 1, [(0, 0, 8), (0, 0, 9)]),
        "spectrogram": (lambda: raster(SCANNING, "C II 1336"), 2, 1, [(3, 0, 0), (4, 0, 0)]),
        "sit-and-stare exposures": (lambda: raster(sit_and_stare, "Si IV 1403"), 0, 1, [(0, 0, 5), (0, 0, 6)]),
        "λ–time": (lambda: raster(sit_and_stare, "Si IV 1403"), 2, 0, [(0, 20, 0), (0, 21, 0)]),
        "map": (plain_map, 1, 0, []),
        "no WCS": (cube, 2, 1, [(3, 0, 0), (4, 0, 0)]),
        "λ–step": (lambda: raster(SCANNING, "C II 1336"), 2, 0, [(0, 50, 0), (0, 51, 0)]),
        "slit-jaw rolled 60°": (lambda: rolled(60), 2, 1, [(1, 0, 0), (2, 0, 0)]),
    }[case]
    data = data()
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewers = []
    for updates in (glue_patches._original_update_axislabels, PATCHED_LABELS):
        with pytest.MonkeyPatch.context() as patch:  # a viewer keeps the label updates it was made with
            patch.setattr(ImageViewer, "update_x_axislabel", updates[0])
            patch.setattr(ImageViewer, "update_y_axislabel", updates[1])
            viewers.append(app.new_data_viewer(ImageViewer, data=data))
    for viewer in viewers:
        viewer.state.x_att, viewer.state.y_att = data.pixel_component_ids[x], data.pixel_component_ids[y]
    glues, ours = viewers
    for step in [None, steps[:1], "swap", steps[1:], "style"]:
        for viewer in viewers:
            if step == "swap":
                viewer.state.x_att, viewer.state.y_att = viewer.state.y_att, viewer.state.x_att
            elif step == "style":  # as set in the axes options
                viewer.state.x_axislabel_size, viewer.state.x_axislabel_weight = 14, "bold"
                viewer.state.y_axislabel_size, viewer.state.y_axislabel_weight = 7, "light"
            elif step:
                viewer.state.slices = step[0]
        if case == "λ–step":
            # no latitude tick labels, which pointing jitter piles up (FrameTimeTool), so longitude takes the step
            # axis' near side, where glue labels it: the same drawing
            assert drawn_labels(ours)[0] == drawn_labels(glues)[0]
        elif case != "slit-jaw rolled 60°":
            assert drawn_labels(ours) == drawn_labels(glues)
            if case in ("sit-and-stare exposures", "λ–time"):  # with the exposure numbers of the frame-time tool
                assert any(text.startswith("Exposure") for text, _, _ in drawn_labels(ours)[1])
        else:
            # WCSAxes shows a coordinate on another spine than the axis glue maps it to: past a 45° roll,
            # latitude along x. glue labels the coordinates on the bottom and left spines after the x and y
            # axes; each coordinate keeps its own name here.
            assert drawn_labels(ours)[0] != drawn_labels(glues)[0]
            assert own_names(ours)
            assert not own_names(glues)
    if case in ("map", "no WCS"):  # restored from a session, which can hold plain Data but not yet IRIS data
        app.save_session(str(tmp_path / "labels.glu"))
        sessions = []
        for updates in (glue_patches._original_update_axislabels, PATCHED_LABELS):
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr(ImageViewer, "update_x_axislabel", updates[0])
                patch.setattr(ImageViewer, "update_y_axislabel", updates[1])
                sessions.append(GlueApplication.restore_session(str(tmp_path / "labels.glu")))
            qtbot.addWidget(sessions[-1])
        glues, ours = (session.viewers[0][0] for session in sessions)  # swapped and styled
        assert drawn_labels(ours) == drawn_labels(glues)
