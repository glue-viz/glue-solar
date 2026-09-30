import shutil

import numpy as np
import pytest
from glue.config import data_factory, menubar_plugin
from glue.core import Data
from glue.core.data_factories import load_data
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from irispy.io import read_files
from matplotlib.backend_bases import MouseEvent

from astropy.io import fits

import glue_solar
from glue_solar.conftest import MD5, OBS_A, find_irispy_test_file
from glue_solar.sources.iris import is_iris_fits, link_iris
from glue_solar.sources.loaders.iris import image_data


def test_setup_registers_hooks():
    glue_solar.setup()
    glue_solar.setup()  # glue calls it once; tests and reloads must not duplicate the tool
    assert "IRIS: browse observations…" in [label for label, _ in menubar_plugin]
    assert ("IRIS: link helioprojective coordinates", link_iris) in list(menubar_plugin)
    assert ImageViewer.tools.count("solar:frame_time") == 1
    assert ImageViewer.tools.count("solar:coordinate") == 1
    assert ImageViewer.tools.count("solar:cursor_readout") == (0 if hasattr(ImageViewer, "cursor_status") else 1)
    iris = next(f for f in data_factory if f.label == "IRIS Level 2 FITS")
    for label in ("FITS file", "sunpy Map"):  # both also match IRIS files; ours must win
        other = next(f for f in data_factory if f.label == label)
        assert iris.priority > (other.priority or 0)


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
    assert datasets[0].label == "C_II_1336-3860258481-2014-03-29T14:09:38-scan-0"
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

    tool.activate()
    assert tool.label.isHidden()
    tool.activate()
    assert not tool.label.isHidden()

    # Any loader's datetime component will do, whatever it is called
    still = Data(label="still", flux=np.zeros((4, 5)), obs_date=np.full((4, 5), np.datetime64("2020-01-01T12:00:00")))
    app.data_collection.append(still)
    other = app.new_data_viewer(ImageViewer, data=still)
    assert other.toolbar.tools["solar:frame_time"].label.text() == "2020-01-01T12:00:00.000 UTC"


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

    tool.activate()  # hide
    assert viewer.statusBar().currentMessage() == ""
    move_to(10, 20)
    assert viewer.statusBar().currentMessage() == ""
    tool.activate()  # show again
    event = move_to(10, 20)
    assert viewer.statusBar().currentMessage() == tool.describe(event.xdata, event.ydata) != ""

    # Attributes not named after their dataset are named in the readout
    still = Data(label="still", flux=np.full((4, 5), 3.5))
    app.data_collection.append(still)
    other = app.new_data_viewer(ImageViewer, data=still)
    assert other.toolbar.tools["solar:cursor_readout"].describe(1, 1).endswith(" | flux = 3.5")


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
    assert np.issubdtype(clean[clean.main_components[0]].dtype, np.int16)  # no fill, no conversion

    path = tmp_path / source.name
    shutil.copy2(source, path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].data[0, 1, 2] = -200
        hdul[0].data[0, 2, 3] = -199  # unverified as missing in AIA cutouts, so it stays data
    aia = image_data(path)
    flux = aia[aia.main_components[0]]
    assert flux.dtype == np.float32
    np.testing.assert_array_equal(np.argwhere(np.isnan(flux)), [[0, 1, 2]])
    assert flux[0, 2, 3] == -199

    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(aia)
    viewer = app.new_data_viewer(ImageViewer, data=aia)
    image = viewer.axes._composite(bounds=[(-0.5, 3.5, 4), (-0.5, 4.5, 5)])
    np.testing.assert_array_equal(image[1, 2], [1, 1, 1, 1])  # the white background shows through


def test_slice_sliders_follow_a_drag_at_most_every_tenth_of_a_second(qtbot):
    from qtpy import QtWidgets

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
    start = viewer.state.slices[0]
    slider.setSliderDown(True)  # a drag across ten positions
    for position in range(11, 21):
        slider.setSliderPosition(position)
    assert viewer.state.slices[0] == start  # nothing applied at each position
    qtbot.waitUntil(lambda: viewer.state.slices[0] == 20, timeout=1000)  # the timer applies the latest
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
