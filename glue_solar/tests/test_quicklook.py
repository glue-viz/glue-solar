import itertools
import re
import shutil
import time
from collections import Counter

import numpy as np
import pytest
from echo import delay_callback
from glue.config import settings
from glue.core import Data
from glue.core.component import DateTimeComponent
from glue.core.edit_subset_mode import OrMode
from glue.core.exceptions import IncompatibleAttribute
from glue.core.hub import HubListener
from glue.core.link_manager import LinkManager
from glue.core.message import SettingsChangeMessage, SubsetUpdateMessage
from glue.core.roi import CircularROI, PolygonalROI, RectangularROI, XRangeROI, YRangeROI
from glue.core.subset import SubsetState, roi_to_subset_state
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.viewers.image.state import AggregateSlice
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.common.data_slice_widget import SliceWidget
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.text import Text
from qtpy import QtWidgets
from qtpy.QtCore import Qt, QTimer

import astropy.units as u
from astropy.io import fits
from astropy.visualization.wcsaxes.ticklabels import TickLabels
from astropy.wcs import WCS

import glue_solar
from glue_solar.conftest import MD5, OBS_B, find_irispy_test_file
from glue_solar.quicklook import (
    Coordinator,
    QuicklookImageViewer,
    _half_cadence,
    coordinator,
    nearest,
    observation_key,
    quicklook,
    sji_to_raster,
)
from glue_solar.regrid import regrid_on_time
from glue_solar.sources import moments
from glue_solar.sources.iris import shift_pointing_iris
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.tests.helpers import (
    count_tick_work,
    inversions,
    load_selected,
    mouse,
    press,
    raster_point_on_sji,
    select_point,
    shift,
)

SCAN = "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits"


class SubsetUpdates(HubListener):
    """Count the subset-state updates each dataset receives."""

    def __init__(self, hub):
        self.counts = Counter()
        hub.subscribe(self, SubsetUpdateMessage, handler=self._count, filter=lambda m: m.attribute == "subset_state")

    def _count(self, message):
        self.counts[message.subset.data.label] += 1


@pytest.fixture
def app(qtbot):
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    point = app.data_collection.new_subset_group(label="Point")
    app.session.edit_subset_mode.edit_subset = [point]
    return app


@pytest.fixture
def scans(irispy_test_files):
    """The C II 1336 window of the 3 fixture scans of 3860258481, as scan 0 and as a stack."""
    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    assert len(files) == 3
    [scan] = raster_data(files[:1], ["C II 1336"])
    [stack] = raster_data(files, ["C II 1336"], stack=True)
    return scan, stack


def image(app, data, x, y, slices=None):
    viewer = app.new_data_viewer(ImageViewer, data=data)
    viewer.state.x_att, viewer.state.y_att = data.pixel_component_ids[x], data.pixel_component_ids[y]
    if slices is not None:
        viewer.state.slices = slices
    return viewer


def menu_action(viewer, text):
    """The action of the ``solar:coordinate`` menu entry ``text``, as the toolbar shows it."""
    button = viewer.toolbar.widgetForAction(viewer.toolbar.actions["solar:coordinate"])
    return next(action for action in button.menu().actions() if action.text() == text)


def test_observation_key():
    raster = Data(label="raster")
    raster.meta.update(OBSID="3860258481", STARTOBS="2014-03-29T14:09:38.830")
    aia = Data(label="aia")
    aia.meta.update(OBSID="20140329_140938_3860258481", STARTOBS="2014-03-29T14:09:38.83")
    assert observation_key(raster) == observation_key(aia) == ("3860258481", np.datetime64("2014-03-29T14:09:38.830"))
    rerun = Data(label="rerun")
    rerun.meta.update(OBSID="3860258481", STARTOBS="2014-03-30T09:00:00")
    assert observation_key(rerun) != observation_key(raster)
    assert observation_key(Data(label="plain")) is None
    bad = Data(label="bad")
    bad.meta.update(OBSID="3860258481", STARTOBS="not a time")
    assert observation_key(bad) is None


def test_viewers_join_and_leave(app, qtbot, tmp_path):
    data = Data(label="plain", flux=np.arange(24.0).reshape(2, 3, 4))
    app.data_collection.append(data)
    coord = coordinator(app.data_collection)
    assert coordinator(app.data_collection) is coord
    first = app.new_data_viewer(ImageViewer, data=data)
    later = app.new_data_viewer(ImageViewer, data=data)
    assert list(coord._viewers) == [first, later]
    first.close(warn=False)
    assert list(coord._viewers) == [later]
    coord.unregister(first)  # a second unregister does nothing

    session = tmp_path / "session.glu"
    app.save_session(str(session))
    restored = GlueApplication.restore_session(str(session), show=False)
    qtbot.addWidget(restored)
    assert list(coordinator(restored.data_collection)._viewers) == list(restored.viewers[0])


def test_map_click_on_a_raster_needs_no_coordination(app, scans):
    scan, stack = scans
    app.data_collection.extend([scan, stack])
    updates = SubsetUpdates(app.data_collection.hub)
    raster_map = image(app, scan, 0, 1)
    select_point(raster_map, 3, 50)
    # one assignment by the Pixel tool, none by the coordinator
    assert updates.counts == {scan.label: 1, stack.label: 1}
    point = app.data_collection.subset_groups[0].subset_state
    assert point.slices == [slice(3, 4), slice(50, 51), slice(None)]
    assert coordinator(app.data_collection).point is point


def test_map_click_on_a_stack_pins_the_scan(app, scans):
    scan, stack = scans
    app.data_collection.extend([scan, stack])
    updates = SubsetUpdates(app.data_collection.hub)
    stack_map = image(app, stack, 1, 2, (1, 0, 0, 8))
    select_point(stack_map, 2, 40)
    # the Pixel tool's assignment and one by the coordinator, which does not answer its own
    assert updates.counts == {scan.label: 2, stack.label: 2}
    assert app.data_collection.subset_groups[0].subset_state.slices == [
        slice(1, 2),
        slice(2, 3),
        slice(40, 41),
        slice(None),
    ]
    assert stack_map.state.slices == (1, 0, 0, 8)


def test_menu_entries_keep_the_pixel_tool(app, scans):
    scan, _ = scans
    app.data_collection.append(scan)
    raster_map = image(app, scan, 0, 1)
    select_point(raster_map, 3, 50)
    coord = coordinator(app.data_collection)

    menu_action(raster_map, "Time master").trigger()
    assert coord.masters == {observation_key(scan): scan}
    entries = ["Clear point", "Time master", "Set blink partner here", "Blink", "Blink"]
    intervals = menu_action(raster_map, "Blink interval").menu().actions()
    for action in [*(menu_action(raster_map, text) for text in entries), *intervals]:
        action.trigger()
        assert raster_map.toolbar.active_tool.tool_id == "image:point_selection"
        assert raster_map.toolbar.actions["image:point_selection"].isChecked()
    assert coord.point is None
    assert not app.data_collection.subset_groups[0].subset_state.to_mask(scan).any()


def test_a_slit_jaw_click_outside_a_quicklook_stays_a_slit_jaw_point(app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    app.data_collection.extend([raster, sji])
    image(app, raster, 0, 1)
    select_point(image(app, sji, 2, 1), 10, 20)
    qtbot.wait(20)
    assert app.data_collection.subset_groups[0].subset_state.reference_data is sji


def check_axis_swap(app, data):
    """Swap a map to wavelength against slit: its step slider goes to the point, no wavelength slider moves."""
    app.data_collection.append(data)
    step, slit = data.shape[0] // 2, data.shape[1] // 3
    wavelength = data.shape[2] // 2
    raster_map = image(app, data, 0, 1, (0, 0, wavelength))
    other_map = image(app, data, 0, 1, (0, 0, wavelength - 1))
    select_point(raster_map, step, slit)
    raster_map.state.x_att_world = data.world_component_ids[2]  # what the axis combo does
    assert raster_map.state.x_att is data.pixel_component_ids[2]
    assert raster_map.state.slices == (step, 0, wavelength)
    assert other_map.state.slices == (0, 0, wavelength - 1)


def test_axis_swap_moves_the_step_slider_to_the_point(app, scans):
    check_axis_swap(app, scans[0])


@pytest.mark.remote_data
def test_axis_swap_on_a_full_raster(app, irispy_data):
    # 4000005156 scan 0, Si IV 1403: 64 steps of a full-resolution raster
    [data] = raster_data([irispy_data("iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz")])
    assert data.shape[0] == 64
    check_axis_swap(app, data)


def test_a_second_observation_is_never_coupled(app, scans, irispy_test_files):
    scan, _ = scans
    [other] = raster_data(
        [find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")],
        ["Si IV 1403"],
    )
    assert observation_key(other) != observation_key(scan)
    app.data_collection.extend([scan, other])
    other_map = image(app, other, 0, 1, (0, 0, 3))
    select_point(image(app, scan, 0, 1), 3, 50)
    other_map.state.x_att_world = other.world_component_ids[2]
    assert other_map.state.slices == (0, 0, 3)


SNS = "iris_l2_20210905_001833_3620258102_{}.fits"
# glue's region selection tools, as an Image viewer has them
SELECT_TOOLS = ["select:rectangle", "select:xrange", "select:yrange", "select:circle", "select:polygon"]


@pytest.fixture
def bare_app(qtbot, monkeypatch):
    """An application whose modal dialogs fail the test, with glue's large-data prompt set to fire on any size."""
    glue_solar.setup()

    def modal(*args, **kwargs):
        raise AssertionError("a modal dialog opened")

    for cls in (QtWidgets.QMessageBox, QtWidgets.QDialog):
        monkeypatch.setattr(cls, "exec_", modal, raising=False)
        monkeypatch.setattr(cls, "exec", modal, raising=False)
    monkeypatch.setattr(ProfileViewer, "large_data_size", 1)
    app = GlueApplication()
    qtbot.addWidget(app)
    return app


def expected_start(data):
    """The point's first position: the map centre, scan 0 of a stack, and the pixel nearest the window's TWAVE."""
    wave = data[data.world_component_ids[-1], (0,) * (data.ndim - 1)] * u.Unit(data.coords.world_axis_units[0])
    wave = wave.to_value(u.AA)
    twaves = [data.meta[f"TWAVE{n}"] for n in range(1, data.meta["NWIN"] + 1)]
    [twave] = [t for t in twaves if wave.min() <= t <= wave.max()]
    centre = [n // 2 for n in data.shape[:-1]]
    if data.ndim == 4:
        centre[0] = 0
    return (*centre, int(np.argmin(np.abs(wave - twave))))


def check_panels(app, viewers, data, rows):
    """Each raster panel shows ``rows[role] = (x, y)`` at the point, as the plan's panel table says."""
    [group] = app.session.edit_subset_mode.edit_subset
    point = group.subset_state
    assert group.label == "Point"
    assert point.reference_data is data
    index = tuple(s.start if s.start is not None else viewers["map"].state.slices[i] for i, s in enumerate(point.slices))
    assert index == expected_start(data)
    for role, (x, y) in rows.items():
        state = viewers[role].state
        assert (state.x_att, state.y_att) == (data.pixel_component_ids[x], data.pixel_component_ids[y])
        assert state.slices == index
        assert state.aspect == "auto"
        assert (state.x_min, state.x_max) == (-0.5, data.shape[x] - 0.5)  # the whole axis, not glue's padding
        assert isinstance(viewers[role], QuicklookImageViewer)
        assert [tool for tool in viewers[role].toolbar.tools if tool.startswith("select:")] == SELECT_TOOLS
    assert coordinator(app.data_collection).point is point
    assert viewers["map"].toolbar.active_tool.tool_id == "image:point_selection"
    for viewer in [viewers[role] for role in rows] + viewers["sji"]:
        layer = viewer.state.layers[0]
        assert layer.percentile == 99.5
        assert np.isfinite(layer.v_min)
        assert layer.v_min < layer.v_max
    spectrum = viewers["spectrum"].state
    assert spectrum.function == "mean"
    # the point's own spectrum only: not the whole cube, nor an earlier quicklook's point
    assert [layer.layer for layer in spectrum.layers if layer.visible] == [s for s in group.subsets if s.data is data]
    assert ProfileViewer.large_data_size == 1  # the prompt was skipped for this viewer only
    assert spectrum.x_display_unit == data.coords.world_axis_units[0]  # no display-unit override
    assert spectrum.y_min <= 0 <= spectrum.y_max
    assert [0, 0] in [list(line.get_ydata()) for line in viewers["spectrum"].axes.lines]
    assert data.label in app.statusBar().currentMessage()
    assert set(app.viewers[-1]) == {*[viewers[role] for role in rows], viewers["spectrum"], *viewers["sji"]}


def test_quicklook_of_a_sit_and_stare(bare_app, tmp_path, irispy_test_files):
    rasters = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))])
    sjis = [image_data(find_irispy_test_file(irispy_test_files, SNS.format(f"SJI_{c}_t000"))) for c in (1400, 2796)]
    deconvolved = tmp_path / SNS.format("SJI_2796_t000_deconvolved")
    shutil.copy2(find_irispy_test_file(irispy_test_files, SNS.format("SJI_2796_t000")), deconvolved)
    sjis.append(image_data(deconvolved))
    viewers = quicklook(bare_app, rasters + sjis[::-1])  # the deconvolved SJI first
    [mg] = [data for data in rasters if data.label.startswith("Mg_II_k_2796")]
    check_panels(bare_app, viewers, mg, {"map": (0, 1), "spectrogram": (2, 1), "wavelength": (2, 0)})
    assert [viewers[role].state.title for role in ("map", "wavelength")] == [
        "Mg II k 2796 slit vs time",
        "Mg II k 2796 λ–time",
    ]
    # the plain SJI 2796 is shown and the deconvolved one offered
    assert [viewer.state.reference_data for viewer in viewers["sji"]] == sjis[1::-1]
    assert sjis[2].label in bare_app.statusBar().currentMessage()
    for viewer in viewers["sji"]:
        assert viewer.state.aspect == "equal"
        # nor does glue draw, or update, the point's crosshair on a slit-jaw image
        assert [layer for layer in viewer.state.layers if layer.layer.label == "Point"] == []
    assert bare_app.data_collection.external_links  # the datasets were added and linked
    # the stock axis combo still turns the spectrogram into a map and back
    spectrogram = viewers["spectrogram"].state
    spectrogram.x_att_world = mg.world_component_ids[0]
    assert spectrogram.x_att is mg.pixel_component_ids[0]
    spectrogram.x_att_world = mg.world_component_ids[2]
    assert spectrogram.x_att is mg.pixel_component_ids[2]


def test_quicklook_shows_the_chosen_window(bare_app, irispy_test_files):
    rasters = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))])
    viewers = quicklook(bare_app, rasters, window="Si IV 1403")
    assert viewers["map"].state.reference_data.label.startswith("Si_IV_1403")
    assert viewers["map"].state.title == "Si IV 1403 slit vs time"


def drawn_ticks(viewer, side):
    """The tick labels WCSAxes draws on ``side`` ('b', 'l', 't' or 'r') of an Image viewer, by axis label."""
    viewer.figure.canvas.draw()
    return {
        coord.get_axislabel(): list(coord._ticklabels.text[side])
        for coords in viewer.axes._all_coords  # the world coordinates and any overlay
        for coord in coords
        if coord.get_ticklabel_visible() and side in coord.get_ticklabel_position() and coord._ticklabels.text.get(side)
    }


def exposure_axis(viewer, label):
    """The exposure-number coordinate the frame-time tool adds to an Image viewer, by its axis label."""
    [coord] = [coord for coords in viewer.axes._all_coords[1:] for coord in coords if coord.get_axislabel() == label]
    return coord


EXPOSURES = "Exposure (acquisition order)"


def check_exposure_axis(viewer, axis, label, exposures):
    """``axis`` shows ``label`` and integer exposure numbers on its near side, and no world coordinate."""
    assert getattr(viewer.state, f"{axis}_axislabel") == label
    ticks = drawn_ticks(viewer, "b" if axis == "x" else "l")
    assert list(ticks) == [label]
    assert len(ticks[label]) >= 2
    assert {int(tick) for tick in ticks[label]} <= set(range(exposures))
    exposure_axis(viewer, label)  # one exposure coordinate, no stale copy


def test_a_sit_and_stare_exposure_axis(bare_app, monkeypatch, irispy_test_files):
    raster, _ = sit_and_stare(irispy_test_files)
    bare_app.show()  # the quicklook's own panel sizes
    viewers = quicklook(bare_app, [raster])
    times = raster[raster.id["Time"]][:, 0, 0]
    first, last = (np.datetime_as_string(t, unit="s") for t in (times[0], times[-1]))
    label = f"{EXPOSURES}\n{first} – {last[11:]} UTC"  # one day

    def check(viewer, axis):
        state = viewer.state
        other = "y" if axis == "x" else "x"
        _, far, other_near, other_far = "btlr" if axis == "x" else "lrbt"
        check_exposure_axis(viewer, axis, label, raster.shape[0])
        # the other axis shows glue's own coordinate and label, on its near side only
        assert list(drawn_ticks(viewer, other_near)) == [getattr(state, f"{other}_axislabel")]
        assert not drawn_ticks(viewer, far)
        assert not drawn_ticks(viewer, other_far)
        # the whole label, with its UTC range, fits the panel along the axis
        box = exposure_axis(viewer, label)._axislabels.get_window_extent()
        (start, end), (low, high) = getattr(box, f"interval{axis}"), getattr(viewer.figure.bbox, f"interval{axis}")
        assert low <= start < end <= high

    check(viewers["map"], "x")
    viewers["map"].state.x_min, viewers["map"].state.x_max = 2.6, 4.4  # zoomed: WCSAxes would move the coordinates
    check(viewers["map"], "x")
    wavelength = viewers["wavelength"]
    check(wavelength, "y")
    wavelength.state.y_min, wavelength.state.y_max = 2.6, 4.4
    check(wavelength, "y")
    coords = wavelength.axes.coords
    wavelength.state.slices = (wavelength.state.slices[0], 5, wavelength.state.slices[2])  # the slit slider
    assert wavelength.axes.coords is not coords  # glue reset the axes
    check(wavelength, "y")
    wavelength.state.y_att_world = raster.world_component_ids[1]  # the axis combo: slit
    assert wavelength.state.y_axislabel == raster.world_component_ids[1].label  # glue's own
    assert label not in drawn_ticks(wavelength, "l")
    wavelength.state.y_att_world = raster.world_component_ids[0]
    check(wavelength, "y")
    wavelength.state.x_att_world = raster.world_component_ids[0]  # exposure on x, wavelength on y
    check(wavelength, "x")
    # sizes from the axes options, and colours from the Preferences, as glue gives its own coordinates
    exposures = exposure_axis(wavelength, label)
    wavelength.state.x_axislabel_size = 12
    assert exposures._axislabels.get_size() == 12
    wavelength.state.x_ticklabel_size = 7
    assert exposures._ticklabels.get_size() == 7
    monkeypatch.setattr(settings, "FOREGROUND_COLOR", "#ff0000")
    bare_app.session.hub.broadcast(SettingsChangeMessage(bare_app, ("FOREGROUND_COLOR",)))
    parts = (exposures._axislabels, exposures._ticklabels, exposures._ticks)
    assert {part.get_color() for part in parts} == {"#ff0000"}
    wavelength.state.x_axislabel = "Exposure"  # typed in the axes options
    assert list(drawn_ticks(wavelength, "b")) == ["Exposure"]


def test_a_slit_step_relabels_the_exposure_axis_without_placing_its_ticks(bare_app, monkeypatch, irispy_test_files):
    raster, _ = sit_and_stare(irispy_test_files)
    wavelength = quicklook(bare_app, [raster])["wavelength"]  # exposure on y
    label = wavelength.state.y_axislabel
    assert label.startswith(f"{EXPOSURES}\n")
    edit = wavelength.options_widget().ui.axes_editor.ui.text_y_axislabel  # the axes options
    for typed in ("", wavelength.state.y_att_world.label):  # glue's own labels, typed: the exposure label again
        edit.setText(typed)
        edit.editingFinished.emit()
        assert wavelength.state.y_axislabel == edit.text() == label
        assert list(drawn_ticks(wavelength, "l")) == [label]
    calls = count_tick_work(monkeypatch, wavelength.axes)
    for typed in (False, True):
        coords = wavelength.axes.coords
        calls.clear()
        wavelength.state.slices = (wavelength.state.slices[0], 5 + typed, wavelength.state.slices[2])
        assert wavelength.axes.coords is not coords  # glue reset the axes and their labels
        # glue's '' and world labels, and the exposure label again, go on their coordinates, which places
        # no tick until the draw (glue-core 1.27.0 alone: 6 set_xlabel and set_ylabel and 28 tick updates)
        assert calls == {}
        assert wavelength.state.y_axislabel == edit.text() == label
        assert list(drawn_ticks(wavelength, "l")) == [label]
        edit.setText("Exposure")  # typed in the axes options: kept until glue resets the axes
        edit.editingFinished.emit()
        assert wavelength.state.y_axislabel == "Exposure"
        assert list(drawn_ticks(wavelength, "l")) == ["Exposure"]


def crosshair(viewer):
    """Where the Point's crosshair shows in an Image viewer, or None."""
    [artist] = [artist for artist in viewer.layers if artist.layer.label == "Point"]
    if not (artist._line_x.get_visible() or artist._line_y.get_visible()):
        return None
    return artist._line_x.get_xdata()[0], artist._line_y.get_ydata()[0]


def test_no_crosshair_where_the_point_has_no_position(bare_app, irispy_test_files):
    import inspect

    from glue.viewers.image.layer_artist import ImageSubsetLayerArtist

    from glue_solar import glue_patches

    installed = ImageSubsetLayerArtist._update_visual_attributes is glue_patches._update_visual_attributes
    assert installed == glue_patches.needs_crosshair_workaround()  # probes glue's own method
    assert not glue_patches.needs_crosshair_workaround(glue_patches._update_visual_attributes)
    # a private method: pin its signature on the released baseline
    parameters = inspect.signature(glue_patches._original_update_visual_attributes).parameters
    assert list(parameters) == ["self", "redraw"]

    raster, _ = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster])
    [group] = bare_app.session.edit_subset_mode.edit_subset
    exposure, slit, _ = (s.start for s in group.subset_state.slices)
    assert crosshair(viewers["map"]) == (exposure, slit)
    # the point is free in wavelength: glue-core 1.27.0 alone draws these at (0, 0)
    panels = [viewers[role] for role in ("spectrogram", "wavelength")]
    assert [crosshair(viewer) for viewer in panels] == [None, None]
    viewers["wavelength"].state.slices = (exposure, 5, viewers["wavelength"].state.slices[2])  # moves the point
    assert crosshair(viewers["map"]) == (exposure, 5)
    for viewer in panels:
        [layer] = [layer for layer in viewer.state.layers if layer.layer.label == "Point"]
        layer.visible = False
        layer.visible = True  # glue updates only the visual attributes
        assert crosshair(viewer) is None


def test_quicklook_of_a_raster_and_of_a_stack(bare_app, scans):
    scan, stack = scans
    viewers = quicklook(bare_app, [scan])
    check_panels(bare_app, viewers, scan, {"map": (0, 1), "spectrogram": (2, 1), "wavelength": (2, 0)})
    assert viewers["wavelength"].state.title == "C II 1336 λ–step"
    # a scanning raster's steps are places on the Sun: glue's own label
    assert viewers["map"].state.x_axislabel == scan.world_component_ids[0].label
    viewers = quicklook(bare_app, [scan, stack])  # a stack of the window is shown rather than one scan
    check_panels(bare_app, viewers, stack, {"map": (1, 2), "spectrogram": (3, 2), "wavelength": (3, 0)})
    assert viewers["map"].state.slices[0] == 0


def test_quicklook_adds_its_datasets_in_one_link_update(bare_app, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    sjis = [sji, image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_2796_t000")))]
    collection = bare_app.data_collection
    updates = []
    update = LinkManager.update_externally_derivable_components

    def counted(self, *args, **kwargs):
        updates.append(len(collection))
        return update(self, *args, **kwargs)

    monkeypatch.setattr(LinkManager, "update_externally_derivable_components", counted)
    quicklook(bare_app, [raster, *sjis, raster])
    # each update pairs every two datasets: one for the three, and one for the links between them
    assert updates == [3, 3]
    assert list(collection) == [raster, *sjis]
    assert len(collection.external_links) == 4  # each slit-jaw's longitude and latitude to the raster's
    updates.clear()
    quicklook(bare_app, [raster, *sjis])  # already added and linked
    assert updates == []


def test_quicklook_fits_a_spectrum_computed_on_a_thread(bare_app, qtbot, monkeypatch, irispy_test_files):
    # glue computes the profiles of cubes above 1e7 elements on a worker thread
    monkeypatch.setattr(Data, "size", property(lambda self: 10**8))
    rasters = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    spectrum = quicklook(bare_app, rasters)["spectrum"].state
    [point] = [layer for layer in spectrum.layers if layer.visible]
    qtbot.waitUntil(lambda: point.profile is not None and spectrum.y_max != 1, timeout=10000)
    _, values = point.profile
    assert (spectrum.y_min, spectrum.y_max) == (np.nanmin(values), np.nanmax(values))


def test_the_spectrum_panel_never_profiles_the_whole_cube(bare_app, qtbot, monkeypatch, scans):
    # glue would compute the mean spectrum of the whole cube for a layer that is only hidden again
    whole = []
    compute = Data.compute_statistic

    def counted(self, *args, **kwargs):
        if kwargs.get("axis") is not None and kwargs.get("subset_state") is None:
            whole.append(self.label)
        return compute(self, *args, **kwargs)

    monkeypatch.setattr(Data, "compute_statistic", counted)
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    select_point(viewers["map"], 1, 30)
    qtbot.wait(50)
    assert whole == []
    [cube] = [layer for layer in viewers["spectrum"].state.layers if layer.layer is scan]
    assert not cube.visible
    # a raster added again later shows as glue adds it
    viewers["spectrum"].remove_data(scan)
    viewers["spectrum"].add_data(scan)
    [cube] = [layer for layer in viewers["spectrum"].state.layers if layer.layer is scan]
    assert cube.visible


@pytest.mark.remote_data
def test_quicklook_gives_aia_cutouts_no_panel(bare_app, tmp_path, irispy_data, irispy_test_files):
    # A real AIA cutout claiming the fixture observation loads as a slit-jaw cube, but INSTRUME says AIA
    [path] = [p for p in irispy_data("iris_l2_20250519_165924_3640107442_cutout_SDO.tar.gz") if p.endswith("_171.fits")]
    copy = tmp_path / "aia_l2_20210905_001833_3620258102_171.fits"
    shutil.copy2(path, copy)
    with fits.open(copy, mode="update") as hdul:
        hdul[0].header["OBSID"] = "20210905_001833_3620258102"
        hdul[0].header["STARTOBS"] = "2021-09-05T00:18:33.640"
    aia = image_data(copy)
    rasters = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    assert observation_key(aia) == observation_key(rasters[0])
    viewers = quicklook(bare_app, [*rasters, aia])
    assert viewers["sji"] == []
    assert all(viewer.state.reference_data is not aia for viewer in bare_app.viewers[-1] if hasattr(viewer.state, "reference_data"))


def drawn_tick_labels(monkeypatch, viewer):
    """The text and window extent of every tick label the viewer draws."""
    drawn, draw = [], Text.draw

    def spy(self, renderer):
        draw(self, renderer)
        if isinstance(self, TickLabels) and self.get_visible() and self.get_text():
            drawn.append((self.get_text(), self.get_window_extent(renderer)))

    with monkeypatch.context() as patch:
        patch.setattr(Text, "draw", spy)
        viewer.figure.canvas.draw()
    return drawn


@pytest.mark.remote_data
def test_quicklook_of_a_full_raster(bare_app, monkeypatch, irispy_data):
    [data] = raster_data([irispy_data("iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz")])
    viewers = quicklook(bare_app, [data])
    check_panels(bare_app, viewers, data, {"map": (0, 1), "spectrogram": (2, 1), "wavelength": (2, 0)})
    for role in ("map", "spectrogram", "wavelength"):  # no tick label over another or off the panel
        drawn = drawn_tick_labels(monkeypatch, viewers[role])
        width, height = viewers[role].figure.canvas.get_width_height()
        assert all(0 <= box.x0 and box.x1 <= width and 0 <= box.y0 and box.y1 <= height for _, box in drawn)
        boxes = [box for _, box in drawn]
        assert not [(a, b) for i, a in enumerate(boxes) for b in boxes[i + 1:] if a.overlaps(b)], role


def test_raster_panels_show_wavelengths_in_angstrom(bare_app, scans):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    # the dataset's own wavelengths, from the WCS it wraps
    wave = (scan.coords._wcs.pixel_to_world_values(np.arange(scan.shape[2]), 0, 0)[0] * u.m).to_value(u.AA)
    np.testing.assert_allclose(scan[scan.world_component_ids[2], 0, 0], wave, rtol=0, atol=1e-6)
    k = viewers["map"].state.slices[2]
    [slider] = [w.state for w in viewers["map"].options_widget().findChildren(SliceWidget) if w.state.slider_unit]
    assert slider.slider_unit == "Angstrom"
    decimals = len(slider.slider_label.partition(".")[2])  # as few as tell every wavelength apart
    assert abs(float(slider.slider_label) - wave[k]) <= 0.5 * 10.0**-decimals
    spectrum = viewers["spectrum"].state
    assert spectrum.x_display_unit == "Angstrom"
    [x] = [layer.profile[0] for layer in spectrum.layers if layer.visible]
    np.testing.assert_allclose(x, wave, rtol=0, atol=1e-6)
    panel = viewers["wavelength"]
    panel.figure.canvas.draw()
    shown = panel.toolbar.tools["solar:cursor_readout"].describe(k, 3).split()[0]
    decimals = len(shown.partition(".")[2])
    assert abs(float(shown) - wave[k]) <= 0.5 * 10.0**-decimals


def tick_label_sides(viewer):
    """The tick label positions of the viewer's longitude and latitude, by name, after a draw."""
    viewer.figure.canvas.draw()
    return {c.default_label: c.get_ticklabel_position() for c in viewer.axes.coords if c.coord_type != "scalar"}


def test_flat_helioprojective_coordinates_have_no_tick_labels(bare_app, scans):
    # latitude along the steps jitters back and forth across each tick value, and WCSAxes labels every crossing
    scan, stack = scans
    viewers = quicklook(bare_app, [scan])
    sides = tick_label_sides(viewers["wavelength"])
    assert sides == {"Helioprojective Latitude": [], "Helioprojective Longitude": ["l", "#"]}
    assert tick_label_sides(viewers["spectrogram"])["Helioprojective Longitude"] == []
    assert [] not in tick_label_sides(viewers["map"]).values()
    viewers["wavelength"].state.slices = (0, 3, 0)  # a slit step resets the axes
    assert tick_label_sides(viewers["wavelength"])["Helioprojective Latitude"] == []
    # a stack's λ–scan panel: each scan's pointing moves both angles, which leave the scan its own axis
    viewers = quicklook(bare_app, [stack])
    assert tick_label_sides(viewers["wavelength"]) == {"Helioprojective Latitude": [], "Helioprojective Longitude": []}
    assert [] not in tick_label_sides(viewers["map"]).values()


@pytest.mark.parametrize(
    ("ctype", "unit", "crval", "cdelt", "shape"),
    [
        (["HPLN-TAN", "HPLT-TAN"], "arcsec", [10, 20], 0.6, (400, 400)),  # across Tx = 0
        (["HPLN-TAN", "HPLT-TAN"], "arcsec", [10, 20], 0.6, (500, 20)),  # a narrow strip
        (["RA---TAN", "DEC--TAN"], "deg", [0, 10], 0.02, (100, 100)),  # across RA = 0
    ],
)
def test_a_map_keeps_the_tick_labels_of_both_angles(bare_app, ctype, unit, crval, cdelt, shape):
    # with no other coordinate beside them, both angles change across the image, however narrow or wherever it is
    wcs = WCS(naxis=2)
    wcs.wcs.ctype, wcs.wcs.cunit, wcs.wcs.crval, wcs.wcs.cdelt = ctype, [unit] * 2, crval, [cdelt] * 2
    wcs.wcs.crpix = [shape[1] / 2, shape[0] / 2]
    data = Data(label="map", flux=np.zeros(shape), coords=wcs)
    bare_app.data_collection.append(data)
    assert [] not in tick_label_sides(bare_app.new_data_viewer(ImageViewer, data=data)).values()


def test_a_flat_longitude_across_0_has_no_tick_labels(bare_app):
    # a FITS WCS gives longitudes from 0° to 360°: a slit at Tx = 0 rolled by 1° must not look 360° wide in longitude
    wcs = WCS(naxis=3)
    wcs.wcs.ctype, wcs.wcs.cunit = ["HPLN-TAN", "HPLT-TAN", "TIME"], ["arcsec", "arcsec", "s"]
    wcs.wcs.crpix, wcs.wcs.cdelt, wcs.wcs.crval = [3, 50, 1], [0.6, 0.6, 10], [0, 20, 0]
    roll = np.deg2rad(1)
    wcs.wcs.pc = [[np.cos(roll), -np.sin(roll), 0], [np.sin(roll), np.cos(roll), 0], [0, 0, 1]]
    data = Data(label="raster", flux=np.zeros((40, 100, 5)), coords=wcs)
    bare_app.data_collection.append(data)
    sides = tick_label_sides(image(bare_app, data, 0, 1, (0, 0, 2)))  # the slit at Tx = 0 against time
    assert sides == {"custom:pos.helioprojective.lat": ["l", "#"], "custom:pos.helioprojective.lon": []}


def test_a_flat_latitude_beside_corners_off_the_sky_has_no_tick_labels(bare_app):
    # an all-sky image has no coordinates in its corners, which must not hide how far its longitude goes
    wcs = WCS(naxis=3)
    wcs.wcs.ctype, wcs.wcs.cunit = ["GLON-AIT", "GLAT-AIT", "VRAD"], ["deg", "deg", "m/s"]
    wcs.wcs.crpix, wcs.wcs.cdelt = [90.5, 1, 1], [-2, 2, 1000]
    data = Data(label="cube", flux=np.zeros((5, 45, 180)), coords=wcs)
    bare_app.data_collection.append(data)
    sides = tick_label_sides(image(bare_app, data, 2, 0))  # longitude against velocity along the equator
    assert sides == {"pos.galactic.lon": ["b", "#"], "pos.galactic.lat": []}


def test_quicklook_without_a_raster(bare_app, irispy_test_files):
    sjis = [image_data(find_irispy_test_file(irispy_test_files, SNS.format(f"SJI_{c}_t000"))) for c in (1400, 2796)]
    viewers = quicklook(bare_app, sjis)
    assert viewers.keys() == {"sji", "windows"}
    assert viewers["windows"] == []
    assert [viewer.state.reference_data for viewer in viewers["sji"]] == sjis


def test_quicklook_reports_a_spectrum_it_could_not_add(bare_app, monkeypatch, scans):
    monkeypatch.setattr(ProfileViewer, "add_data", lambda self, data: False)
    viewers = quicklook(bare_app, [scans[0]])
    assert "could not add" in bare_app.statusBar().currentMessage()
    assert viewers["map"].toolbar.active_tool.tool_id == "image:point_selection"


def test_each_quicklook_edits_its_own_point(bare_app, scans):
    scan, stack = scans
    first = quicklook(bare_app, [scan])
    first_tab = bare_app.tab_count - 1
    [first_point] = bare_app.session.edit_subset_mode.edit_subset
    mine = bare_app.data_collection.new_subset_group(label="mine", subset_state=SubsetState())
    second = quicklook(bare_app, [stack])
    [second_point] = bare_app.session.edit_subset_mode.edit_subset
    assert second_point is not first_point
    # not even as hidden layers, which glue would still update and redraw at each move
    for viewer in (*[first[role] for role in ("map", "spectrogram", "wavelength", "spectrum")], *second["sji"]):
        assert not [layer for layer in viewer.state.layers if layer.layer in second_point.subsets]
    for role in ("map", "spectrum"):
        # another subset is only hidden
        subsets = [layer for layer in second[role].state.layers if hasattr(layer.layer, "group")]
        assert {layer.layer.group: layer.visible for layer in subsets} == {second_point: True, mine: False}
    bare_app.tab_widget.setCurrentIndex(first_tab)
    assert bare_app.session.edit_subset_mode.edit_subset == [first_point]


def test_quicklook_keeps_the_users_spectrum_range(bare_app, scans):
    viewers = quicklook(bare_app, [scans[0]])
    spectrum = viewers["spectrum"].state
    spectrum.y_min, spectrum.y_max = -3, 7
    select_point(viewers["map"], 1, 2)
    assert (spectrum.y_min, spectrum.y_max) == (-3, 7)


RASTER_PANELS = ("map", "spectrogram", "wavelength")


def spectrum(viewers):
    """The spectrum the spectrum panel shows for the point."""
    [layer] = [layer for layer in viewers["spectrum"].state.layers if layer.visible]
    return layer.profile[1]


def cube(data):
    return data[data.main_components[0]]


def test_a_map_click_moves_the_other_panels(bare_app, qtbot, scans):
    for data in scans:
        viewers = quicklook(bare_app, [data])
        step, slit = data.ndim - 3, data.ndim - 2
        if data.ndim == 4:
            viewers["map"].state.slices = (2, *viewers["map"].state.slices[1:])
        wavelengths = [viewers[role].state.slices[-1] for role in RASTER_PANELS]
        select_point(viewers["map"], 1, 30)
        qtbot.waitUntil(lambda viewers=viewers, step=step: viewers["spectrogram"].state.slices[step] == 1)
        assert viewers["wavelength"].state.slices[slit] == 30
        assert [viewers[role].state.slices[-1] for role in RASTER_PANELS] == wavelengths
        np.testing.assert_array_equal(spectrum(viewers), cube(data)[(2,) * (data.ndim == 4) + (1, 30)])
        if data.ndim == 4:  # the point follows the map's scan, at the same step and slit
            assert viewers["spectrogram"].state.slices[0] == 2
            viewers["map"].state.slices = (0, *viewers["map"].state.slices[1:])
            qtbot.waitUntil(lambda viewers=viewers: viewers["spectrogram"].state.slices[0] == 0)
            np.testing.assert_array_equal(spectrum(viewers), cube(data)[0, 1, 30])
            assert viewers["wavelength"].state.slices[1:3] == (1, 30)


# glue averages the band over the NaN fill too, which numpy warns about
@pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")
def test_a_click_on_a_wavelength_panel_moves_the_map_to_its_wavelength(bare_app, qtbot, monkeypatch, scans):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    step, wavelength = viewers["spectrogram"].state.slices[0], viewers["spectrogram"].state.slices[2]
    select_point(viewers["spectrogram"], 5, 40)  # wavelength 5, slit 40
    [group] = bare_app.session.edit_subset_mode.edit_subset
    assert group.subset_state.slices == [slice(step, step + 1), slice(40, 41), slice(None)]
    assert viewers["map"].state.slices[2] == 5
    qtbot.waitUntil(lambda: viewers["wavelength"].state.slices[1] == 40)
    select_point(viewers["wavelength"], 9, 6)  # wavelength 9, step 6
    assert group.subset_state.slices == [slice(6, 7), slice(40, 41), slice(None)]
    assert viewers["map"].state.slices[2] == 9
    qtbot.waitUntil(lambda: viewers["spectrogram"].state.slices[0] == 6)
    # the panels that show wavelength never have their wavelength slider written
    assert viewers["spectrogram"].state.slices[2] == viewers["wavelength"].state.slices[2] == wavelength
    # the map's wavelength band, unlike a collapse, moves to the click
    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", lambda *args: ("5", True))
    viewers["map"].toolbar.actions["solar:band"].trigger()
    select_point(viewers["spectrogram"], 12, 40)
    band = viewers["map"].state.slices[2]
    assert (band.slice, band.center) == (slice(10, 15), 12)


def test_typing_a_step_moves_the_point_once(bare_app, qtbot, scans):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    [group] = bare_app.session.edit_subset_mode.edit_subset
    slit = group.subset_state.slices[1]
    updates = SubsetUpdates(bare_app.data_collection.hub)
    viewers["spectrogram"].state.slices = (6, *viewers["spectrogram"].state.slices[1:])
    qtbot.wait(20)
    assert updates.counts == {scan.label: 1}
    assert group.subset_state.slices == [slice(6, 7), slit, slice(None)]
    np.testing.assert_array_equal(spectrum(viewers), cube(scan)[6, slit.start])


# glue collapses the NaN fill too, which numpy warns about
@pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")
def test_a_collapse_is_never_overwritten(bare_app, qtbot, scans):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    collapse = AggregateSlice(slice(0, 4), 2, np.nanmean)
    viewers["spectrogram"].state.slices = (collapse, *viewers["spectrogram"].state.slices[1:])
    select_point(viewers["map"], 5, 12)
    select_point(viewers["wavelength"], 3, 5)
    qtbot.wait(20)
    assert viewers["spectrogram"].state.slices[0] is collapse


def test_clearing_the_point_stops_the_coupling(bare_app, qtbot, scans):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    menu_action(viewers["map"], "Clear point").trigger()
    slit = viewers["wavelength"].state.slices[1]
    viewers["spectrogram"].state.slices = (6, 20, viewers["spectrogram"].state.slices[2])
    qtbot.wait(20)
    assert coordinator(bare_app.data_collection).point is None
    assert viewers["wavelength"].state.slices[1] == slit


def test_an_sji_point_moves_no_raster_panel(bare_app, qtbot, irispy_test_files):
    rasters = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))
    viewers = quicklook(bare_app, [*rasters, sji])
    before = {role: viewers[role].state.slices for role in RASTER_PANELS}
    select_point(viewers["map"], 30, 10)  # a raster point first: stepping the SJI leaves it alone
    qtbot.wait(20)
    [group] = bare_app.session.edit_subset_mode.edit_subset
    point = group.subset_state.slices
    before = {role: viewers[role].state.slices for role in RASTER_PANELS}
    viewers["sji"][0].state.slices = (7, 0, 0)
    qtbot.wait(20)
    assert group.subset_state.slices == point
    # a click on the slit-jaw image showing its frame axis, which is no place on the Sun, stays a slit-jaw point, also
    # beside another viewer of the image showing a frame
    image(bare_app, sji, 2, 1)
    viewers["sji"][0].state.x_att = sji.pixel_component_ids[0]
    select_point(viewers["sji"][0], 10, 20)
    qtbot.wait(20)
    assert group.subset_state.reference_data is sji
    assert {role: viewers[role].state.slices for role in RASTER_PANELS} == before
    # the point shows on the slit-jaw image it was clicked on, and the raster panels drop its layer, until
    # the next raster click
    for click in (False, True):
        for viewer, shown in ((viewers["sji"][0], not click), *((viewers[role], click) for role in RASTER_PANELS)):
            layers = [layer.visible for layer in viewer.state.layers if getattr(layer.layer, "group", None) is group]
            assert layers == ([True] if shown else [])
        select_point(viewers["map"], 30, 10)
        qtbot.wait(20)
    assert crosshair(viewers["map"]) == (30, 10)


def test_a_raster_point_move_leaves_the_slit_jaw_layers_alone(bare_app, qtbot, monkeypatch, irispy_test_files):
    from glue.viewers.image.layer_artist import ImageSubsetLayerArtist

    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    for viewer in (sji_viewer, viewers["map"]):  # a slit-jaw click and a map click both make a raster point
        select_point(viewer, 10, 20)
        qtbot.wait(20)
    updated = []
    update = ImageSubsetLayerArtist.update

    def counted(self, *args, **kwargs):
        updated.append(self.state.viewer_state)
        return update(self, *args, **kwargs)

    monkeypatch.setattr(ImageSubsetLayerArtist, "update", counted)
    for exposure in (1, 2, 3):
        viewers["spectrogram"].state.slices = (exposure, *viewers["spectrogram"].state.slices[1:])
        qtbot.waitUntil(lambda exposure=exposure: f"step {exposure}" in readout(viewers["spectrogram"]))
    qtbot.wait(20)
    # glue updates, and redraws, a hidden layer at every move of its subset
    assert [state for state in updated if state is sji_viewer.state] == []
    assert len([state for state in updated if state is viewers["map"].state]) == 3
    assert crosshair(viewers["map"])[0] == 3


def test_a_closed_panel_gets_no_point(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    spectrogram = viewers["spectrogram"]
    spectrogram.close(warn=False)
    layers = list(spectrogram.state.layers)
    for viewer in (viewers["sji"][0], viewers["map"]):  # a slit-jaw click, then a raster click
        select_point(viewer, 10, 20)
        qtbot.wait(20)
    assert list(spectrogram.state.layers) == layers


@pytest.mark.remote_data
def test_a_spectrogram_click_on_a_full_raster(bare_app, qtbot, irispy_data):
    [data] = raster_data([irispy_data("iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz")])
    viewers = quicklook(bare_app, [data])
    step = viewers["spectrogram"].state.slices[0]
    select_point(viewers["spectrogram"], 300, 500)
    assert viewers["map"].state.slices[2] == 300
    [group] = bare_app.session.edit_subset_mode.edit_subset
    assert group.subset_state.slices == [slice(step, step + 1), slice(500, 501), slice(None)]
    np.testing.assert_array_equal(spectrum(viewers), cube(data)[step, 500])


def test_a_new_viewer_of_the_cube_joins_the_point(bare_app, qtbot, scans):
    scan, stack = scans
    viewers = quicklook(bare_app, [scan, stack])
    stack_map = viewers["map"]
    stack_map.state.slices = (2, *stack_map.state.slices[1:])
    select_point(stack_map, 3, 70)
    qtbot.wait(20)
    [group] = bare_app.session.edit_subset_mode.edit_subset
    point = group.subset_state.slices
    viewer = bare_app.new_data_viewer(ImageViewer, data=stack)  # glue resets its sliders to 0
    qtbot.wait(20)
    assert group.subset_state.slices == point
    assert viewer.state.slices[:2] == (2, 3)  # it shows wavelength against slit at the point's scan and step
    other = bare_app.new_data_viewer(ImageViewer, data=scan)
    other.add_data(stack)
    other.state.reference_data = stack
    qtbot.wait(20)
    assert group.subset_state.slices == point
    assert other.state.slices[0] == 2


def test_each_tab_moves_its_own_point(bare_app, qtbot, scans):
    scan, stack = scans
    first = quicklook(bare_app, [scan])
    first_tab = bare_app.tab_count - 1
    [first_point] = bare_app.session.edit_subset_mode.edit_subset
    quicklook(bare_app, [stack])
    [second_point] = bare_app.session.edit_subset_mode.edit_subset
    second = second_point.subset_state.slices
    bare_app.tab_widget.setCurrentIndex(first_tab)
    first["spectrogram"].state.slices = (6, *first["spectrogram"].state.slices[1:])
    qtbot.wait(20)
    assert first_point.subset_state.slices[0] == slice(6, 7)
    assert second_point.subset_state.slices == second
    # two quicklooks of one cube: a click in the second leaves the first's panels alone
    again = quicklook(bare_app, [scan])
    before = {role: first[role].state.slices for role in RASTER_PANELS}
    select_point(again["map"], 1, 90)
    qtbot.wait(20)
    assert {role: first[role].state.slices for role in RASTER_PANELS} == before


def test_a_drag_moves_the_other_panels_once(bare_app, qtbot, scans):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    written = []
    viewers["spectrogram"].state.add_callback("slices", lambda slices: written.append(slices[0]))
    mouse(viewers["map"], "button_press_event", 1, 30)
    assert written == [1]  # the press, like a click, at once
    for step in (2, 3, 4, 5):
        mouse(viewers["map"], "motion_notify_event", step, 30)
    mouse(viewers["map"], "button_release_event", 5, 30)
    assert written == [1]  # the drag only when Qt next runs, at its last position
    qtbot.waitUntil(lambda: viewers["spectrogram"].state.slices[0] == 5)
    assert written == [1, 5]
    select_point(viewers["map"], 7, 30)  # and the next click at once again
    assert written == [1, 5, 7]


def test_a_click_draws_each_other_panel_once(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    qtbot.wait(50)
    draws = Counter()
    panels = {"spectrogram": viewers["spectrogram"], "wavelength": viewers["wavelength"], "sji": viewers["sji"][0]}
    for role, viewer in panels.items():
        draw = viewer.figure.canvas.draw
        monkeypatch.setattr(viewer.figure.canvas, "draw", lambda draw=draw, role=role: draws.update([role]) or draw())
    select_point(viewers["map"], 100, 30)  # the map's own draws are the helper's
    # moved before glue draws the click: each draws once, with its new slider and the new point
    assert viewers["spectrogram"].state.slices[0] == 100
    assert viewers["wavelength"].state.slices[1] == 30
    qtbot.waitUntil(lambda: " · Δt " in readout(panels["sji"]))
    qtbot.wait(50)
    assert draws == {"spectrogram": 1, "wavelength": 1, "sji": 1}


def test_an_error_after_a_click_is_reported(bare_app, qtbot, monkeypatch, scans):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    with monkeypatch.context() as patch, qtbot.captureExceptions() as errors:
        patch.setattr(coordinator(bare_app.data_collection), "_sync", lambda key: 1 / 0)
        select_point(viewers["map"], 1, 30)  # matplotlib's mouse events would only print it
    assert [type(error) for _, error, _ in errors] == [ZeroDivisionError]


def expected_nearest(when, times):
    """The nearest time's index by brute force: of equally near times the earliest, of equal times the first."""
    distance = np.abs(times - when)
    best = np.flatnonzero(distance == distance.min())
    return int(best[times[best] == times[best].min()][0])


def seconds(*values):
    return np.datetime64("2021-01-01T00:00:00", "ns") + np.array(values, "timedelta64[ms]")


def test_nearest():
    times = seconds(0, 10000, 20000, 30000)
    index, offset = nearest(seconds(4000, 5000, 6000), times)
    assert list(index) == [0, 0, 1]  # 5 s is a tie: the earlier time
    assert list(offset / np.timedelta64(1, "ms")) == [-4000, -5000, 4000]
    assert list(nearest(seconds(4000, 5000, 6000), times[::-1])[0]) == [3, 3, 2]  # descending
    assert list(nearest(seconds(0), times[[2, 0, 1]])[0]) == [1]  # unsorted
    assert list(nearest(seconds(10000, 11000), times[[0, 1, 1, 2]])[0]) == [1, 1]  # equal times: the first
    index, offset = nearest(seconds(-60000, 90000), times)  # outside: the nearest end, and how far
    assert list(index) == [0, 3]
    assert list(offset / np.timedelta64(1, "s")) == [60, -60]
    index, _ = nearest(seconds(12000, 18000), times[[0, 3]])  # a gap: still the nearest
    assert list(index) == [0, 1]
    # NaT, the gaps of data regridded on time, is never the nearest, even past the last time, and has no cadence
    gaps = np.insert(times, 1, [np.datetime64("NaT", "ns")] * 3)
    index, offset = nearest(seconds(4000, 16000, 35000), gaps)
    assert list(index) == [0, 5, 6]
    assert list(offset / np.timedelta64(1, "ms")) == [-4000, 4000, -5000]
    assert list(nearest(seconds(35000), gaps)[0]) == [6]
    assert _half_cadence(np.append(times, [np.datetime64("NaT", "ns")] * 9)) == np.timedelta64(5, "s")
    for bad in (np.array(["NaT", "NaT"], "datetime64[ns]"), times[:0], times.reshape(2, 2)):
        with pytest.raises(ValueError, match="reference times"):
            nearest(seconds(0), bad)


def slit_jaw(times, like, label="SJI_1400"):
    """A slit-jaw cube of the observation of ``like`` with frames at ``times``."""
    data = Data(label=label, **{label: np.arange(len(times) * 20, dtype=float).reshape(len(times), 4, 5)})
    data.meta = {"INSTRUME": "SJI", "TDESC1": label, "OBSID": like.meta["OBSID"], "STARTOBS": like.meta["STARTOBS"]}
    data.add_component(DateTimeComponent(np.repeat(times, 20).reshape(data.shape)), "Time")
    return data


def readout(viewer):
    return viewer.toolbar.tools["solar:frame_time"].label.text()


def raster_time(data, index):
    return data[data.id["Time"]][(*index, 0, 0)]


def nearest_frame(data, when):
    """The frame of ``data`` nearest ``when``, or None when more than half its median cadence away (NO MATCH)."""
    frames = data[data.id["Time"]][:, 0, 0]
    index = expected_nearest(when, frames)
    return index if abs(frames[index] - when) <= np.median(np.diff(np.sort(frames))) / 2 else None


def check_follower(app, qtbot, master_time, follower, viewer):
    """
    The follower's frame is the nearest to the master's time, or NO MATCH when half a cadence away,
    and then the frame is kept. Call it after moving the master, before Qt runs the sync.
    """
    before = viewer.state.slices[0]
    times = follower[follower.id["Time"]][:, 0, 0]
    index = expected_nearest(master_time, times)
    delta = (times[index] - master_time) / np.timedelta64(1, "s")
    matched = nearest_frame(follower, master_time) is not None
    if matched:
        qtbot.waitUntil(lambda: f" · Δt {delta:+.1f} s" in readout(viewer))
        assert viewer.state.slices[0] == index
        assert not viewer.toolbar.tools["solar:frame_time"]._grey.get_visible()
    else:
        qtbot.waitUntil(lambda: f"NO MATCH Δt = {delta:+.1f} s" in readout(viewer))
        assert viewer.state.slices[0] == before
        assert viewer.toolbar.tools["solar:frame_time"]._grey.get_visible()
    return matched


def test_a_raster_master_moves_the_slit_jaw_images(bare_app, qtbot, irispy_test_files):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    wavelengths = [viewers[role].state.slices[-1] for role in RASTER_PANELS]
    matched = []
    # the decimated fixture's frames are 4.6 minutes apart; step 35 is 139.7 s from the nearest, beyond
    # half the median gap (139.0 s) but not half the mean (141.9 s)
    for step in (93, 35, 0, 186, 1):
        viewers["spectrogram"].state.slices = (step, *viewers["spectrogram"].state.slices[1:])
        matched.append(check_follower(bare_app, qtbot, raster_time(raster, (step,)), sji, sji_viewer))
        assert f"time master, step {step}" in readout(viewers["spectrogram"])
    assert matched == [False, False, True, True, True]
    heard = []
    coordinator(bare_app.data_collection).add_listener(lambda *args: heard.append(args))
    viewers["spectrogram"].state.slices = (7, *viewers["spectrogram"].state.slices[1:])
    qtbot.waitUntil(lambda: bool(heard))
    key, when, exposure = heard[-1]
    assert (key, when) == (observation_key(raster), raster_time(raster, (7,)))
    assert exposure == raster[raster.id["Exposure time"]][7, 0, 0]
    assert [viewers[role].state.slices[-1] for role in RASTER_PANELS] == wavelengths


def test_a_slit_jaw_master_moves_the_raster_exposure(bare_app, qtbot, irispy_test_files):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    [group] = bare_app.session.edit_subset_mode.edit_subset
    slit = group.subset_state.slices[1]
    wavelengths = [viewers[role].state.slices[-1] for role in RASTER_PANELS]
    menu_action(sji_viewer, "Time master").trigger()
    exposures = raster[raster.id["Time"]][:, 0, 0]
    for frame in (5, 40):
        sji_viewer.state.slices = (frame, 0, 0)
        [exposure], _ = nearest([sji[sji.id["Time"]][frame, 0, 0]], exposures)
        qtbot.waitUntil(lambda exposure=exposure: group.subset_state.slices[0] == slice(exposure, exposure + 1))
        assert group.subset_state.slices[1] == slit  # the slit stays
        qtbot.waitUntil(lambda exposure=exposure: viewers["spectrogram"].state.slices[0] == exposure)
        assert [viewers[role].state.slices[-1] for role in RASTER_PANELS] == wavelengths
        assert "time master" in readout(sji_viewer)


def test_an_aia_cutout_follows_the_time_master_and_can_be_it(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    aia = slit_jaw(raster_time(raster, (0,)) + np.arange(150) * np.timedelta64(24, "s"), raster, "1700")  # an hour
    aia.meta["INSTRUME"] = "AIA_3"
    viewers = quicklook(bare_app, [raster, sji, aia])
    assert viewers["sji"][0].state.reference_data is sji  # the cutout gets no panel
    aia_viewer = bare_app.new_data_viewer(ImageViewer, data=aia)
    matched = []
    for step in (20, 1, 100):  # the cutout ends before step 100
        viewers["spectrogram"].state.slices = (step, *viewers["spectrogram"].state.slices[1:])
        matched.append(check_follower(bare_app, qtbot, raster_time(raster, (step,)), aia, aia_viewer))
    assert matched == [True, True, False]
    menu_action(aia_viewer, "Time master").trigger()
    for frame in (40, 7):
        aia_viewer.state.slices = (frame, 0, 0)
        [exposure], _ = nearest([aia[aia.id["Time"]][frame, 0, 0]], raster[raster.id["Time"]][:, 0, 0])
        qtbot.waitUntil(lambda exposure=exposure: viewers["spectrogram"].state.slices[0] == exposure)
        assert "time master" in readout(aia_viewer)


def test_an_unmatched_slit_jaw_keeps_its_frame(bare_app, qtbot, scans):
    scan, _ = scans
    late = raster_time(scan, (0,)) + np.timedelta64(1, "D") + np.arange(5) * np.timedelta64(10, "s")
    sji = slit_jaw(late, scan)
    viewers = quicklook(bare_app, [scan, sji])
    [sji_viewer] = viewers["sji"]
    sji_viewer.state.slices = (3, 0, 0)
    viewers["spectrogram"].state.slices = (2, *viewers["spectrogram"].state.slices[1:])
    # step 2's own offset, as the readout already says NO MATCH for the mid-raster step
    delta = (late[0] - raster_time(scan, (2,))) / np.timedelta64(1, "s")
    qtbot.waitUntil(lambda: f"NO MATCH Δt = {delta:+.1f} s" in readout(sji_viewer))
    assert sji_viewer.state.slices[0] == 3
    assert sji_viewer.toolbar.tools["solar:frame_time"]._grey.get_visible()


def test_a_stack_master_moves_the_slit_jaw_image_by_scan_and_step(bare_app, qtbot, scans):
    _, stack = scans
    start = stack[stack.id["Time"]][0, 0, 0, 0]
    sji = slit_jaw(start + np.arange(50) * np.timedelta64(20, "s"), stack)
    viewers = quicklook(bare_app, [stack, sji])
    [sji_viewer] = viewers["sji"]
    heard = []
    coordinator(bare_app.data_collection).add_listener(lambda *args: heard.append(args))
    for scan, step in ((1, 4), (1, 0), (1, 7), (2, 7), (0, 0)):
        viewers["spectrogram"].state.slices = (scan, step, *viewers["spectrogram"].state.slices[2:])
        assert check_follower(bare_app, qtbot, raster_time(stack, (scan, step)), sji, sji_viewer)
        qtbot.waitUntil(lambda step=step: f"time master, step {step}" in readout(viewers["map"]))
        assert heard[-1][2] == stack[stack.id["Exposure time"]][scan, step, 0, 0]


def test_after_clear_point_a_stacks_scan_slider_still_moves_the_slit_jaw_image(bare_app, qtbot, scans):
    scan, stack = scans
    quicklook(bare_app, [scan])  # in a tab now hidden: its raster is not the stack's master
    times = stack[stack.id["Time"]][:, :, 0, 0]
    frames = np.sort(times, axis=None)  # a frame at each step of each scan
    viewers = quicklook(bare_app, [stack, slit_jaw(frames, stack)])
    [sji_viewer] = viewers["sji"]
    [group] = bare_app.session.edit_subset_mode.edit_subset
    step = group.subset_state.slices[1].start  # the timing step, kept after Clear point
    menu_action(viewers["map"], "Clear point").trigger()
    qtbot.wait(20)
    for index in (1, 2):
        slide(viewers["map"], 0, index)
        frame = np.searchsorted(frames, times[index, step])
        qtbot.waitUntil(lambda frame=frame: sji_viewer.state.slices[0] == frame)


def test_a_slit_jaw_master_over_a_scanning_raster(bare_app, qtbot, scans):
    scan, _ = scans
    times = scan[scan.id["Time"]][:, 0, 0]
    second = np.timedelta64(1, "s")
    frames = np.array([times[0] - 60 * second, times[0] + 30 * second, times[-1] + 3 * second, times[-1] + 60 * second])
    viewers = quicklook(bare_app, [scan, slit_jaw(frames, scan)])
    [sji_viewer] = viewers["sji"]
    menu_action(sji_viewer, "Time master").trigger()
    step = scan.shape[0] // 2  # the point's
    grey = viewers["map"].toolbar.tools["solar:frame_time"]._grey
    # the offset at the timing step, NO MATCH only outside the steps' span and half a cadence
    for frame, matched in enumerate((False, True, True, False)):
        sji_viewer.state.slices = (frame, 0, 0)
        delta = (times[step] - frames[frame]) / second
        text = f" · Δt {delta:+.1f} s" if matched else f"NO MATCH Δt = {delta:+.1f} s"
        qtbot.waitUntil(lambda text=text: text in readout(viewers["map"]))
        assert grey.get_visible() is not matched


def test_a_slit_jaw_master_picks_the_scan_of_a_stack(bare_app, qtbot, scans):
    _, stack = scans
    step = stack.shape[1] // 2
    scan_times = stack[stack.id["Time"]][:, step, 0, 0]
    sji = slit_jaw(scan_times[0] + np.arange(40) * (scan_times[-1] - scan_times[0]) / 39, stack)
    viewers = quicklook(bare_app, [stack, sji])
    [sji_viewer] = viewers["sji"]
    [group] = bare_app.session.edit_subset_mode.edit_subset
    point = group.subset_state.slices
    wavelengths = [viewers[role].state.slices[-1] for role in RASTER_PANELS]
    menu_action(sji_viewer, "Time master").trigger()
    for frame in (0, 20, 39):
        sji_viewer.state.slices = (frame, 0, 0)
        [scan], _ = nearest([sji[sji.id["Time"]][frame, 0, 0]], scan_times)
        qtbot.waitUntil(lambda scan=scan: group.subset_state.slices[0] == slice(scan, scan + 1))
        assert group.subset_state.slices[1:] == point[1:]  # step and slit stay
        qtbot.waitUntil(lambda scan=scan: viewers["spectrogram"].state.slices[0] == scan)
        assert [viewers[role].state.slices[-1] for role in RASTER_PANELS] == wavelengths


# glue collapses the NaN fill too, which numpy warns about
@pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")
def test_a_collapse_on_the_master_and_a_follower(bare_app, qtbot, irispy_test_files):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    collapse = AggregateSlice(slice(0, 4), 2, np.nanmean)
    sji_viewer.state.slices = (collapse, 0, 0)  # a follower's collapse stays
    viewers["spectrogram"].state.slices = (120, *viewers["spectrogram"].state.slices[1:])
    qtbot.wait(20)
    assert sji_viewer.state.slices[0] is collapse
    menu_action(sji_viewer, "Time master").trigger()  # a collapsed master's time is at its centre
    [group] = bare_app.session.edit_subset_mode.edit_subset
    [exposure], _ = nearest([sji[sji.id["Time"]][2, 0, 0]], raster[raster.id["Time"]][:, 0, 0])
    qtbot.waitUntil(lambda: group.subset_state.slices[0] == slice(exposure, exposure + 1))


@pytest.mark.remote_data
def test_time_sync_on_a_negative_step_raster(bare_app, qtbot, irispy_data):
    # 3400109360: STEPS_AV -0.998, so irispy's orientation makes Time run backwards along the step axis
    [path] = irispy_data("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz")
    [scan] = raster_data([path])
    times = scan[scan.id["Time"]][:, 0, 0]
    assert (np.diff(times) < np.timedelta64(0, "s")).all()
    first, last = np.sort(times)[[0, -1]]
    frames = first + np.arange(30) * (last - first) / 29
    frames[5] = times[21] + (times[20] - times[21]) / 2  # a frame halfway between two steps: a tie
    frames[6] = frames[7]  # two frames at one time: the first
    gap = (last - first) / 29
    frames = np.concatenate([[first - gap], frames, [last + gap]])  # and one frame either side of the scan
    sji = slit_jaw(frames, scan)
    viewers = quicklook(bare_app, [scan, sji])
    [sji_viewer] = viewers["sji"]
    for step in (0, 10, 20, 21, scan.shape[0] - 1):
        viewers["spectrogram"].state.slices = (step, *viewers["spectrogram"].state.slices[1:])
        check_follower(bare_app, qtbot, times[step], sji, sji_viewer)
    # the slit-jaw image as master: the scan's offset at its timing step, NO MATCH outside its span
    menu_action(sji_viewer, "Time master").trigger()
    step = scan.shape[0] - 1  # the point's, the scan's earliest
    for frame, matched in ((0, False), (1, True), (15, True), (len(frames) - 1, False)):
        sji_viewer.state.slices = (frame, 0, 0)
        delta = (times[step] - frames[frame]) / np.timedelta64(1, "s")
        text = f" · Δt {delta:+.1f} s" if matched else f"NO MATCH Δt = {delta:+.1f} s"
        qtbot.waitUntil(lambda text=text: text in readout(viewers["map"]))
    # a stack of the scan and its copy one scan later, with a slit-jaw image across both as master
    [stack] = raster_data([path, path], stack=True)
    later = stack[stack.id["Time"]].copy()
    later[1] += last - first + np.median(np.abs(np.diff(times)))
    stack.update_components({stack.id["Time"]: later})
    span = later.max() - first
    sji = slit_jaw(first + np.arange(40) * span / 39, stack, label="SJI_2796")
    viewers = quicklook(bare_app, [stack, sji])
    [sji_viewer] = viewers["sji"]
    [group] = bare_app.session.edit_subset_mode.edit_subset
    step = stack.shape[1] // 2  # the point's
    menu_action(sji_viewer, "Time master").trigger()
    for frame in (0, 19, 20, 39):
        sji_viewer.state.slices = (frame, 0, 0)
        scan = expected_nearest(sji[sji.id["Time"]][frame, 0, 0], later[:, step, 0, 0])
        qtbot.waitUntil(lambda scan=scan: group.subset_state.slices[0] == slice(scan, scan + 1))
        assert group.subset_state.slices[1].start == step


def sit_and_stare(irispy_test_files):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    return raster, image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))


def test_glue_draws_between_the_viewers_of_a_quicklook(bare_app, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    events = []
    timer = QTimer()
    timer.setInterval(0)
    timer.timeout.connect(lambda: events.append("turn"))
    new_data_viewer = bare_app.new_data_viewer
    monkeypatch.setattr(bare_app, "new_data_viewer", lambda *args, **kwargs: (
        events.append("viewer") or new_data_viewer(*args, **kwargs)
    ))
    timer.start()
    quicklook(bare_app, [raster, sji])
    timer.stop()
    viewers = [i for i, event in enumerate(events) if event == "viewer"]
    assert len(viewers) == 5
    assert all(i > 0 and events[i - 1] == "turn" for i in viewers)  # the event loop turned before each viewer


def test_time_sync_without_a_raster_point(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    coord = coordinator(bare_app.data_collection)
    viewers["spectrogram"].state.slices = (1, *viewers["spectrogram"].state.slices[1:])
    qtbot.waitUntil(lambda: sji_viewer.state.slices[0] == 0)
    select_point(sji_viewer, 10, 20)  # a slit-jaw click leaves the frame where it is
    qtbot.wait(20)
    assert sji_viewer.state.slices[0] == 0
    menu_action(viewers["map"], "Clear point").trigger()  # and the exposure slider still leads
    top = raster.shape[1] - 1  # also after a slit-jaw click past the slit's end, which leaves no point
    select_point(sji_viewer, *np.round(past(raster, sji, (1, top), (1, top - 1), 0)))
    qtbot.wait(20)
    assert coord.point is None
    viewers["spectrogram"].state.slices = (186, *viewers["spectrogram"].state.slices[1:])
    expected = expected_nearest(raster_time(raster, (186,)), sji[sji.id["Time"]][:, 0, 0])
    qtbot.waitUntil(lambda: sji_viewer.state.slices[0] == expected)
    assert "time master, step 186" in readout(viewers["spectrogram"])
    for step in range(0, 187, 11):  # one cached pair, whichever exposure
        viewers["spectrogram"].state.slices = (step, *viewers["spectrogram"].state.slices[1:])
        qtbot.wait(5)
    assert len(coord._pairs) == 1


def test_each_follower_viewer_reads_its_own_frame(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    viewers["spectrogram"].state.slices = (1, *viewers["spectrogram"].state.slices[1:])
    qtbot.waitUntil(lambda: " · Δt " in readout(sji_viewer))
    other = bare_app.new_data_viewer(ImageViewer, data=sji)  # a new viewer joins the master's time
    qtbot.waitUntil(lambda: other.state.slices[0] == sji_viewer.state.slices[0])
    other.state.slices = (40, 0, 0)  # moved away by hand: its own offset, and greyed
    offset = sji[sji.id["Time"]][40, 0, 0] - raster_time(raster, (1,))
    qtbot.waitUntil(lambda: f"NO MATCH Δt = {offset / np.timedelta64(1, 's'):+.1f} s" in readout(other))
    assert " · Δt " in readout(sji_viewer)


def footprint(raster, sji):
    """The raster's four corners in the slit-jaw image's first frame, from both datasets' own coordinates."""
    corners = [(step, slit) for step in (0, raster.shape[0] - 1) for slit in (0, raster.shape[1] - 1)]
    return np.transpose([raster_point_on_sji(raster, sji, step, slit) for step, slit in corners])


def test_slit_jaw_panels(bare_app, qtbot, tmp_path, monkeypatch, irispy_test_files):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    channels = (1330, 1400, 2796, 2832)
    sjis = [image_data(find_irispy_test_file(irispy_test_files, SNS.format(f"SJI_{c}_t000"))) for c in channels]
    viewers = quicklook(bare_app, [raster, *sjis])
    assert [viewer.state.title for viewer in viewers["sji"]] == [f"SJI {c}" for c in channels]
    # each opens on the raster's field of view in its first frame, centred, with a margin
    for viewer, sji in zip(viewers["sji"], sjis):
        x, y = footprint(raster, sji)
        margin = max(10, 0.1 * max(np.ptp(x), np.ptp(y)))
        state = viewer.state
        assert state.x_min <= x.min() - margin + 1e-6
        assert x.max() + margin - 1e-6 <= state.x_max
        assert state.y_min <= y.min() - margin + 1e-6
        assert y.max() + margin - 1e-6 <= state.y_max
        assert (state.x_min + state.x_max) / 2 == pytest.approx((x.min() + x.max()) / 2, abs=0.5)
        assert (state.y_min + state.y_max) / 2 == pytest.approx((y.min() + y.max()) / 2, abs=0.5)

    # all follow the time master, and the matched frame holds the raster point
    coord = coordinator(bare_app.data_collection)
    spectrogram = viewers["spectrogram"]
    for step in (120, 186):
        spectrogram.state.slices = (step, *spectrogram.state.slices[1:])
        for viewer, sji in zip(viewers["sji"], sjis):
            assert check_follower(bare_app, qtbot, raster_time(raster, (step,)), sji, viewer)
            assert "outside SJI FOV" not in readout(viewer)

    # the point is placed through the displayed frame: off the image at the other end of the run
    sji_viewer, sji = viewers["sji"][1], sjis[1]
    n, ny, nx = sji.shape
    sji_viewer.state.slices = (0, 0, 0)  # moved back by hand: the last exposure is off the first frame
    assert coord.point_on(sji_viewer)[0] > nx - 0.5 + 2
    assert "outside SJI FOV" in readout(sji_viewer)
    [group] = bare_app.session.edit_subset_mode.edit_subset
    point = group.subset_state
    group.subset_state = SubsetState()  # another selection replaces the point, and the label goes
    qtbot.waitUntil(lambda: "outside SJI FOV" not in readout(sji_viewer))
    group.subset_state = PixelSubsetState(raster, [slice(0, 1), *point.slices[1:]])
    qtbot.waitUntil(lambda: "time master, step 0" in readout(spectrogram))
    sji_viewer.state.slices = (n - 1, 0, 0)  # the first exposure is off the last frame
    assert coord.point_on(sji_viewer)[0] < -0.5 - 2
    assert "outside SJI FOV" in readout(sji_viewer)
    sji_viewer.state.x_att = sji.pixel_component_ids[0]  # with the frame axis shown there is no frame to place it in
    assert coord.point_on(sji_viewer) is None
    assert "outside SJI FOV" not in readout(sji_viewer)
    sji_viewer.state.x_att = sji.pixel_component_ids[2]
    assert "outside SJI FOV" in readout(sji_viewer)
    bare_app.data_collection.remove_subset_group(group)  # deleting the point's group takes the label too
    qtbot.waitUntil(lambda: "outside SJI FOV" not in readout(sji_viewer))

    # the label's bounds on every edge, with the point placed by hand (the fixture's slit spans the image)
    tool = sji_viewer.toolbar.tools["solar:frame_time"]
    for where, outside in [
        ((nx / 2, ny - 0.5 + 2.5), True),
        ((nx / 2, -0.5 - 2.5), True),
        ((nx - 0.5 + 2.5, ny / 2), True),
        ((-0.5 - 2.5, ny / 2), True),
        ((nx / 2, ny - 0.5 - 2.5), False),
        ((nx / 2, -0.5 + 2.5), False),
        ((nx - 0.5 - 2.5, ny / 2), False),
        ((-0.5 + 2.5, ny / 2), False),
    ]:
        monkeypatch.setattr(coord, "point_on", lambda viewer, where=where: where)
        tool._refresh()
        assert ("outside SJI FOV" in readout(sji_viewer)) is outside, where

    deconvolved = tmp_path / SNS.format("SJI_2796_t000_deconvolved")
    shutil.copy2(find_irispy_test_file(irispy_test_files, SNS.format("SJI_2796_t000")), deconvolved)
    viewers = quicklook(bare_app, [raster, image_data(deconvolved)])
    assert [viewer.state.title for viewer in viewers["sji"]] == ["SJI 2796 (deconvolved)"]



def overlays(viewer):
    """The slit line's data while it shows, and where the raster point's marker is while it shows."""
    tool = viewer.toolbar.tools["solar:coordinate"]
    slit, marker = tool._slit, tool._marker
    return (
        slit.get_xydata().tolist() if slit.get_visible() else None,
        tuple(marker.get_xydata()[0]) if marker.get_visible() else None,
    )


@pytest.mark.parametrize("show_axes", [True, False])
def test_slit_and_point_on_a_slit_jaw_image(bare_app, qtbot, monkeypatch, irispy_test_files, show_axes):
    raster, sji = sit_and_stare(irispy_test_files)
    # the fixture keeps full-size slit positions for 10x smaller frames: give each frame its own
    n, ny, nx = sji.shape
    slit = 1 + np.linspace(3, nx - 4, n)
    slit[[5, 6]] = 0, np.nan  # frames without a slit position
    sji.meta["slit x position"] = slit
    monkeypatch.setattr(settings, "SOLAR_SHOW_AXES", show_axes)  # all the same without axes
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    assert {viewer.axes.axison for viewer in bare_app.viewers[-1] if isinstance(viewer, ImageViewer)} == {show_axes}
    coord = coordinator(bare_app.data_collection)
    for frame in (0, n // 2, n - 1):
        sji_viewer.state.slices = (frame, 0, 0)
        assert overlays(sji_viewer)[0] == [[slit[frame] - 1, -0.5], [slit[frame] - 1, ny - 0.5]]
    for frame in (5, 6):
        sji_viewer.state.slices = (frame, 0, 0)
        assert overlays(sji_viewer)[0] is None

    # the raster point follows the time master into the frame it matches
    for step in (1, 186):
        viewers["spectrogram"].state.slices = (step, *viewers["spectrogram"].state.slices[1:])
        qtbot.waitUntil(lambda step=step: f"step {step}" in readout(viewers["spectrogram"]))
        qtbot.waitUntil(lambda: " · Δt " in readout(sji_viewer))
        frame = sji_viewer.state.slices[0]
        where = coord.point_on(sji_viewer)
        assert where is not None
        assert -0.5 <= where[0] <= nx - 0.5
        assert -0.5 <= where[1] <= ny - 0.5
        assert overlays(sji_viewer) == ([[slit[frame] - 1, -0.5], [slit[frame] - 1, ny - 0.5]], pytest.approx(where))
    sji_viewer.state.slices = (0, 0, 0)  # moved back by hand: the late exposure is off the first frame
    assert overlays(sji_viewer)[1] is None
    assert "outside SJI FOV" in readout(sji_viewer)
    sji_viewer.state.slices = (frame, 0, 0)
    assert overlays(sji_viewer)[1] == pytest.approx(where)

    # shown transposed, both swap; with the frame axis shown, neither shows
    sji_viewer.state.x_att, sji_viewer.state.y_att = sji.pixel_component_ids[1], sji.pixel_component_ids[2]
    sji_viewer.state.slices = (frame, 0, 0)
    assert overlays(sji_viewer) == ([[-0.5, slit[frame] - 1], [ny - 0.5, slit[frame] - 1]], pytest.approx(where[::-1]))
    sji_viewer.state.x_att = sji.pixel_component_ids[0]
    assert overlays(sji_viewer) == (None, None)
    sji_viewer.state.x_att, sji_viewer.state.y_att = sji.pixel_component_ids[2], sji.pixel_component_ids[1]
    sji_viewer.state.slices = (frame, 0, 0)
    assert overlays(sji_viewer)[1] == pytest.approx(where)

    sji_viewer.show_crosshairs(1, 1)  # glue's own crosshair, which the PV slicer moves and hides, is another artist
    sji_viewer.hide_crosshairs()
    assert overlays(sji_viewer)[1] == pytest.approx(where)
    menu_action(viewers["map"], "Clear point").trigger()
    qtbot.waitUntil(lambda: overlays(sji_viewer)[1] is None)
    assert overlays(sji_viewer)[0] is not None  # the slit stays


def test_a_wavelength_step_leaves_the_time_sync_alone(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    coord = coordinator(bare_app.data_collection)
    qtbot.wait(20)
    syncs = []
    sync = coord._sync
    monkeypatch.setattr(coord, "_sync", lambda key: syncs.append(key) or sync(key))
    for wavelength in (3, 4, 5):  # the time master's map
        viewers["map"].state.slices = (*viewers["map"].state.slices[:2], wavelength)
        qtbot.wait(20)
    assert syncs == []
    assert "time master" in readout(viewers["map"])
    viewers["spectrogram"].state.slices = (1, *viewers["spectrogram"].state.slices[1:])  # its exposure slider
    assert check_follower(bare_app, qtbot, raster_time(raster, (1,)), sji, sji_viewer)
    assert syncs == [observation_key(raster)]


def test_the_raster_point_is_placed_once_per_frame(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    coord = coordinator(bare_app.data_collection)
    [group] = bare_app.session.edit_subset_mode.edit_subset
    qtbot.wait(20)
    placed = []
    place = glue_solar.quicklook._sji_pixels

    def counted(data, frame, lon, lat):
        placed.append(frame)
        return place(data, frame, lon, lat)

    monkeypatch.setattr(glue_solar.quicklook, "_sji_pixels", counted)
    viewers["spectrogram"].state.slices = (186, *viewers["spectrogram"].state.slices[1:])
    qtbot.waitUntil(lambda: " · Δt " in readout(sji_viewer))
    qtbot.wait(20)
    frame = sji_viewer.state.slices[0]
    # the frame-time readout and the marker share one projection through the frame's coordinates
    assert placed == [frame]
    # and it follows the point and the frame
    for slit in (group.subset_state.slices[1].start + 3, group.subset_state.slices[1].start):
        group.subset_state = PixelSubsetState(raster, [slice(186, 187), slice(slit, slit + 1), slice(None)])
        where = raster_point_on_sji(raster, sji, 186, slit, frame)
        qtbot.waitUntil(lambda where=where: overlays(sji_viewer)[1] == pytest.approx(where))
        assert coord.point_on(sji_viewer) == pytest.approx(where)
        sji_viewer.state.slices = (frame - 1, 0, 0)  # by hand
        where = raster_point_on_sji(raster, sji, 186, slit, frame - 1)
        assert overlays(sji_viewer)[1] == coord.point_on(sji_viewer) == pytest.approx(where)
        sji_viewer.state.slices = (frame, 0, 0)


def test_no_raster_point_on_another_observation(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster])
    other = image_data(find_irispy_test_file(irispy_test_files, "iris_l2_20230408_110821_3880012095_SJI_1400_t000.fits"))
    bare_app.data_collection.append(other)
    viewer = bare_app.new_data_viewer(ImageViewer, data=other)
    viewers["spectrogram"].state.slices = (1, *viewers["spectrogram"].state.slices[1:])
    qtbot.wait(20)
    assert overlays(viewer)[1] is None


def wavelengths(data):
    """The wavelength of each pixel along the last axis of ``data``, in Å, from its own coordinates."""
    wave = data[data.world_component_ids[-1], (0,) * (data.ndim - 1)] * u.Unit(data.coords.world_axis_units[0])
    return wave.to_value(u.AA)


def drawn(viewer, name):
    """
    Where the quicklook's ``name`` lines ('point', 'wavelength' or 'time') are on ``viewer``: ('x', positions) for
    lines at x positions, across the whole image or plot, ('y', positions) for lines at y positions, or None while
    they are hidden.
    """
    [line] = [line for line in viewer.axes.lines if line.get_gid() == f"solar:{name}"]
    if not line.get_visible():
        return None
    xy = line.get_xydata()
    ends = xy[~np.isnan(xy).any(axis=1)].reshape(-1, 2, 2)  # each line's two ends
    vertical = bool((ends[:, 0, 0] == ends[:, 1, 0]).all())
    if hasattr(viewer.state, "slices"):  # an image, crossed from edge to edge
        state = viewer.state
        other = (state.y_att if vertical else state.x_att).axis
        assert (np.sort(ends[:, :, int(vertical)]) == [-0.5, state.reference_data.shape[other] - 0.5]).all()
    else:  # the spectrum panel, from bottom to top
        assert vertical
        assert line.get_transform() == viewer.axes.get_xaxis_transform()
        assert (ends[:, :, 1] == [0, 1]).all()
    return ("x", list(ends[:, 0, 0])) if vertical else ("y", list(ends[:, 0, 1]))


def check_wavelength_lines(app, data):
    """The spectrum panel marks the wavelength of each raster panel with a wavelength slider, in its x unit."""
    viewers = quicklook(app, [data])
    spectrum, wave, axis = viewers["spectrum"], wavelengths(data), data.ndim - 1
    start = expected_start(data)[-1]
    assert drawn(spectrum, "wavelength") == ("x", [pytest.approx(wave[start])])
    slide(viewers["map"], axis, 3)
    assert drawn(spectrum, "wavelength") == ("x", [pytest.approx(wave[3])])
    spectrum.state.x_display_unit = "nm"
    assert drawn(spectrum, "wavelength") == ("x", [pytest.approx(wave[3] / 10)])
    slide(viewers["map"], axis, 14)
    assert drawn(spectrum, "wavelength") == ("x", [pytest.approx(wave[14] / 10)])
    # the spectrogram turned to step (or exposure) against slit: its wavelength slider, where it was, marks too
    viewers["spectrogram"].state.x_att = data.pixel_component_ids[data.ndim - 3]
    assert drawn(spectrum, "wavelength") == ("x", pytest.approx(sorted(wave[[start, 14]] / 10)))
    spectrum.state.x_att = data.pixel_component_ids[axis]  # against wavelength pixels: at the pixels
    assert drawn(spectrum, "wavelength") == ("x", sorted([start, 14]))
    spectrum.state.x_att = data.world_component_ids[0]  # against another axis: none
    assert drawn(spectrum, "wavelength") is None


def test_the_spectrum_panel_marks_the_map_wavelength(bare_app, scans):
    for data in scans:
        check_wavelength_lines(bare_app, data)


@pytest.mark.remote_data
def test_the_spectrum_panel_marks_the_map_wavelength_of_a_full_raster(bare_app, irispy_data):
    [data] = raster_data([irispy_data("iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz")])
    check_wavelength_lines(bare_app, data)


def lines(viewer):
    return {name: drawn(viewer, name) for name in ("point", "wavelength", "time")}


def test_lines_on_the_spectrogram_and_the_wavelength_panel(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    spectrogram, panel = viewers["spectrogram"], viewers["wavelength"]
    exposure, slit, wavelength = expected_start(raster)
    qtbot.wait(20)
    # the point's slit on the spectrogram; its exposure, the map's wavelength and the time master's exposure on the
    # λ–time panel
    assert lines(spectrogram) == {"point": ("y", [slit]), "wavelength": None, "time": None}
    assert lines(panel) == {"point": ("y", [exposure]), "wavelength": ("x", [wavelength]), "time": ("y", [exposure])}
    assert lines(viewers["map"]) == {"point": None, "wavelength": None, "time": None}  # glue's crosshair only
    select_point(viewers["map"], 78, 10)
    qtbot.wait(20)
    assert lines(spectrogram)["point"] == ("y", [10])
    assert lines(panel) == {"point": ("y", [78]), "wavelength": ("x", [wavelength]), "time": ("y", [78])}
    slide(spectrogram, 0, 80)  # the lines move with the point, before the time sync: glue draws the panel once
    assert lines(panel) == {"point": ("y", [80]), "wavelength": ("x", [wavelength]), "time": ("y", [80])}
    qtbot.wait(20)
    draws = Counter()
    for role in ("wavelength", "spectrum"):
        canvas = viewers[role].figure.canvas
        monkeypatch.setattr(canvas, "draw", lambda draw=canvas.draw, role=role: draws.update([role]) or draw())
    slide(viewers["map"], 2, 5)
    qtbot.wait(20)
    assert lines(panel)["wavelength"] == ("x", [5])
    assert draws == {"wavelength": 1, "spectrum": 1}  # for their lines alone
    menu_action(viewers["map"], "Time master").trigger()  # a time sync that moves nothing: no draw
    qtbot.wait(20)
    assert draws == {"wavelength": 1, "spectrum": 1}
    # a Profile's collapse of the map's wavelengths, at its centre
    viewers["map"].state.slices = (*viewers["map"].state.slices[:2], AggregateSlice(slice(3, 8), 5, np.nansum))
    assert lines(panel)["wavelength"] == ("x", [5])
    assert drawn(viewers["spectrum"], "wavelength") == ("x", [pytest.approx(wavelengths(raster)[5])])
    # axes swapped, the lines turn with them
    panel.state.x_att = raster.pixel_component_ids[0]
    assert lines(panel) == {"point": ("x", [80]), "wavelength": ("y", [5]), "time": ("x", [80])}
    spectrogram.state.x_att = raster.pixel_component_ids[1]
    assert lines(spectrogram)["point"] == ("x", [10])
    # under a slit-jaw master the raster's exposure follows its frame, and both lines with it
    menu_action(viewers["sji"][0], "Time master").trigger()
    slide(viewers["sji"][0], 0, 5)
    qtbot.wait(20)
    exposure = expected_nearest(sji[sji.id["Time"]][5, 0, 0], raster[raster.id["Time"]][:, 0, 0])
    assert lines(panel) == {"point": ("x", [exposure]), "wavelength": ("y", [5]), "time": ("x", [exposure])}
    # after Clear point only the time line, following the exposure slider of the raster master
    menu_action(viewers["map"], "Time master").trigger()
    menu_action(viewers["map"], "Clear point").trigger()
    slide(spectrogram, 0, 120)
    qtbot.wait(20)
    assert lines(spectrogram)["point"] is None
    assert lines(panel) == {"point": None, "wavelength": ("y", [5]), "time": ("x", [120])}
    # a slit-jaw point, clicked on an image showing its frames, has no line on the raster panels
    viewers["sji"][0].state.x_att = sji.pixel_component_ids[0]
    select_point(viewers["sji"][0], 3, 2)
    qtbot.wait(20)
    assert coordinator(bare_app.data_collection).point.reference_data is sji
    assert lines(spectrogram)["point"] is lines(panel)["point"] is None
    panel.state.y_att = raster.pixel_component_ids[1]  # exposure against slit: no wavelength, no lines
    assert lines(panel) == {"point": None, "wavelength": None, "time": None}


def test_the_time_line_follows_a_slit_jaw_master(bare_app, qtbot, scans):
    scan, stack = scans
    # a stack's λ–scan panel marks the point's scan
    viewers = quicklook(bare_app, [stack])
    qtbot.wait(20)
    assert lines(viewers["wavelength"])["time"] == lines(viewers["wavelength"])["point"] == ("y", [0])
    slide(viewers["map"], 0, 2)
    qtbot.wait(20)
    assert lines(viewers["wavelength"])["time"] == lines(viewers["wavelength"])["point"] == ("y", [2])
    times = scan[scan.id["Time"]][:, 0, 0]
    frames = times[0] + (np.arange(24) - 2) * ((times[-1] - times[0]) / 19)  # about three per step
    viewers = quicklook(bare_app, [scan, slit_jaw(frames, scan)])
    [sji_viewer] = viewers["sji"]
    select_point(viewers["map"], 1, 30)
    qtbot.wait(20)
    assert lines(viewers["wavelength"])["time"] == ("y", [1])
    # a slit-jaw master moves nothing on a scanning raster: the line marks the step nearest its frame, hidden beyond
    # half a step's time
    menu_action(sji_viewer, "Time master").trigger()
    for frame in (10, 0, 23, 4):
        slide(sji_viewer, 0, frame)
        qtbot.wait(20)
        step = nearest_frame(scan, frames[frame])
        assert lines(viewers["wavelength"])["time"] == (None if step is None else ("y", [step]))
        assert lines(viewers["wavelength"])["point"] == ("y", [1])
    assert nearest_frame(scan, frames[0]) is None


def slits(viewer):
    """The ends of each raster step's slit that the viewer's raster overlay draws, as (steps, 2, 2), or None."""
    [line] = [line for line in viewer.axes.lines if line.get_gid() == "solar:footprint"]
    if not line.get_visible():
        return None
    xy = line.get_xydata()
    return xy[~np.isnan(xy).any(axis=1)].reshape(-1, 2, 2)


def expected_slits(raster, sji, scan=0):
    """Each step's slit ends (a stack's at ``scan``) in the slit-jaw frame nearest its time, from their coordinates."""
    times = raster[raster.id["Time"]][(scan,) * (raster.ndim - 3) + (slice(None), 0, 0)]
    frames, top = sji[sji.id["Time"]][:, 0, 0], raster.shape[-2] - 0.5
    return np.array([
        [raster_point_on_sji(raster, sji, step, slit, expected_nearest(when, frames), scan) for slit in (-0.5, top)]
        for step, when in enumerate(times)
    ])


def overlays_toggled(app, qtbot, viewers, viewer):
    """Choose "Raster overlays" on ``viewer``, which moves nothing."""
    assert changes(app, qtbot, viewers, lambda: menu_action(viewer, "Raster overlays").trigger()) == {}


def test_raster_overlays_on_slit_jaw_images(bare_app, qtbot, monkeypatch, tmp_path, irispy_test_files):
    # a scanning raster: each step's slit placed through the frame nearest its time, whichever frame shows
    path = repointed(tmp_path / SNS.format("raster_t000_r00000"), irispy_test_files, step=0.3)
    [raster] = raster_data([path], ["Si IV 1403"])
    _, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    qtbot.wait(20)
    assert slits(sji_viewer) is None  # off until chosen
    overlays_toggled(bare_app, qtbot, viewers, viewers["map"])  # on any viewer of the observation
    expected = expected_slits(raster, sji)
    for frame in (0, sji.shape[0] - 1):
        slide(sji_viewer, 0, frame)
        assert slits(sji_viewer) == pytest.approx(expected, abs=0.01)
    sji_viewer.state.x_att, sji_viewer.state.y_att = sji.pixel_component_ids[1], sji.pixel_component_ids[2]
    assert slits(sji_viewer) == pytest.approx(expected[:, :, ::-1], abs=0.01)  # transposed
    sji_viewer.state.x_att = sji.pixel_component_ids[0]  # with the frame axis shown: none
    assert slits(sji_viewer) is None
    sji_viewer.state.x_att, sji_viewer.state.y_att = sji.pixel_component_ids[2], sji.pixel_component_ids[1]
    assert slits(sji_viewer) == pytest.approx(expected, abs=0.01)
    overlays_toggled(bare_app, qtbot, viewers, sji_viewer)
    assert slits(sji_viewer) is None

    # a sit-and-stare's slits make one column, placed once, not at each frame step
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    overlays_toggled(bare_app, qtbot, viewers, sji_viewer)
    drawn_slits = slits(sji_viewer)
    assert drawn_slits == pytest.approx(expected_slits(raster, sji), abs=0.01)
    assert np.ptp(drawn_slits[:, :, 0]) < 1
    calls = inversions(monkeypatch, sji)
    for frame in (1, 2, 3):
        slide(sji_viewer, 0, frame)
    assert len(calls) == 3  # the raster point's, one per frame

    # a stack: the slits of the scan its panels show, placed with that scan's own pointing, here drifting north
    later = repointed(tmp_path / SNS.format("raster_t000_r00001"), irispy_test_files, step=0.3, drift=0.01)
    [stack] = raster_data([path, later], ["Si IV 1403"], stack=True)
    [alone] = raster_data([later], ["Si IV 1403"])
    times = stack[stack.id["Time"]].copy()
    times[1] += times.max() - times.min()
    stack.update_components({stack.id["Time"]: times})
    alone.update_components({alone.id["Time"]: times[1]})
    _, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [stack, sji])
    [sji_viewer] = viewers["sji"]
    qtbot.wait(20)  # still on: the toggle is the observation's
    assert slits(sji_viewer) == pytest.approx(expected_slits(stack, sji, 0), abs=0.01)
    slide(viewers["map"], 0, 1)
    qtbot.wait(20)
    assert slits(sji_viewer) == pytest.approx(expected_slits(alone, sji), abs=0.01)
    assert not np.allclose(expected_slits(stack, sji, 0), expected_slits(alone, sji), atol=0.01)


def test_the_map_line_marks_the_step_at_the_master_time(bare_app, qtbot, scans):
    scan, stack = scans
    times = scan[scan.id["Time"]][:, 0, 0]
    frames = times[0] + (np.arange(24) - 2) * ((times[-1] - times[0]) / 19)  # about three per step
    viewers = quicklook(bare_app, [scan, slit_jaw(frames, scan)])
    [sji_viewer] = viewers["sji"]
    select_point(viewers["map"], 1, 30)
    qtbot.wait(20)
    assert drawn(viewers["map"], "step") is None  # off until chosen
    overlays_toggled(bare_app, qtbot, viewers, sji_viewer)
    assert drawn(viewers["map"], "step") == ("x", [1])  # the raster master's: the point's step
    assert slits(sji_viewer) is None  # a slit-jaw image without coordinates places nothing
    menu_action(sji_viewer, "Time master").trigger()
    for frame in (10, 0, 23, 4):  # the step taken nearest the frame, hidden beyond half a step's time (NO MATCH)
        slide(sji_viewer, 0, frame)
        qtbot.wait(20)
        step = nearest_frame(scan, frames[frame])
        assert drawn(viewers["map"], "step") == (None if step is None else ("x", [step]))
    assert nearest_frame(scan, frames[0]) is None
    overlays_toggled(bare_app, qtbot, viewers, viewers["spectrogram"])
    assert drawn(viewers["map"], "step") is None

    # a stack: the step of the scan the map shows
    times = stack[stack.id["Time"]][:, :, 0, 0]
    first, last = times.min(), times.max()
    frames = first + (np.arange(3 * times.size + 4) - 2) * ((last - first) / (3 * times.size - 1))
    viewers = quicklook(bare_app, [stack, slit_jaw(frames, stack)])
    [sji_viewer] = viewers["sji"]
    select_point(viewers["map"], 2, 30)
    overlays_toggled(bare_app, qtbot, viewers, viewers["map"])
    menu_action(sji_viewer, "Time master").trigger()
    shown_scans = set()
    for frame in (0, 40, 41, 47, 55, 65, len(frames) - 1):
        slide(sji_viewer, 0, frame)
        qtbot.wait(20)
        shown = viewers["map"].state.slices[0]
        shown_scans.add(shown)
        step = expected_nearest(frames[frame], times[shown])
        matched = abs(times[shown, step] - frames[frame]) <= np.median(np.diff(times[shown])) / 2
        assert drawn(viewers["map"], "step") == (("x", [step]) if matched else None), frame
    assert len(shown_scans) > 1


def test_the_spectrum_range_is_the_wavelength_panels(bare_app, qtbot, irispy_test_files):
    raster, _ = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster])
    spectrum, panel, spectrogram = (viewers[role].state for role in ("spectrum", "wavelength", "spectrogram"))
    wave = wavelengths(raster)
    exposures, wavelengths_shown = (panel.y_min, panel.y_max), (spectrogram.x_min, spectrogram.x_max)

    def show(low, high):
        spectrum.x_min, spectrum.x_max = low, high

    # a zoom on the spectrum panel moves no slider and gives the λ–time panel its wavelengths
    assert changes(bare_app, qtbot, viewers, lambda: show(wave[4], wave[9])) == {}
    assert (panel.x_min, panel.x_max) == (pytest.approx(4), pytest.approx(9))
    spectrum.x_display_unit = "nm"  # glue converts the range, the same wavelengths
    assert (panel.x_min, panel.x_max) == (pytest.approx(4), pytest.approx(9))
    show(wave[2] / 10, wave[12] / 10)
    assert (panel.x_min, panel.x_max) == (pytest.approx(2), pytest.approx(12))
    show(wave[0] / 10 - 0.1, wave[-1] / 10)  # past the window's first wavelength
    assert (panel.x_min, panel.x_max) == (pytest.approx(-0.1 / (wave[1] - wave[0]) * 10), pytest.approx(len(wave) - 1))
    assert (panel.y_min, panel.y_max) == exposures
    assert (spectrogram.x_min, spectrogram.x_max) == wavelengths_shown  # only the λ–time panel takes it
    # with wavelength up, the panel's y range
    panel.x_att = raster.pixel_component_ids[0]
    show(wave[5] / 10, wave[6] / 10)
    assert (panel.y_min, panel.y_max) == (pytest.approx(5), pytest.approx(6))


@pytest.mark.parametrize("unit", ["Angstrom", "nm"])
def test_navigate_moves_the_map_and_its_lines(bare_app, qtbot, scans, unit):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    spectrum = viewers["spectrum"]
    wave = (wavelengths(scan) * u.AA).to_value(unit)
    spectrum.state.x_display_unit = unit
    tools = spectrum.toolbar.tools["profile-analysis"]
    # behaviour probe: glue-qt 0.4.2 compares Navigate's position with the data's own unit, Å (glue-qt #70 converts)
    if tools._profile_tools._get_axis_and_pixel_slice(scan, wave[3])[1] != 3:
        pytest.skip("glue-qt's Navigate takes positions in the data's own unit only")
    tools.activate()  # glue's profile tools open on Navigate
    y = (spectrum.state.y_min + spectrum.state.y_max) / 2

    def navigate(x):
        mouse(spectrum, "button_press_event", x, y)
        mouse(spectrum, "button_release_event", x, y)

    for j in (7, 3):
        assert changes(bare_app, qtbot, viewers, lambda j=j: navigate(wave[j])) == {"map": (None, None, j)}
        assert drawn(spectrum, "wavelength") == ("x", [pytest.approx(wave[j])])
        assert drawn(viewers["wavelength"], "wavelength") == ("x", [j])


def test_the_lines_leave_closed_panels_and_go_with_their_tab(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    coord = coordinator(bare_app.data_collection)

    def kept():
        kind = glue_solar.quicklook._SpectralLines
        return [listener for listener in coord._listeners if isinstance(getattr(listener, "__self__", None), kind)]

    assert len(kept()) == 1
    closed = Counter()
    for role in ("spectrum", "wavelength"):
        viewers[role].close(warn=False)
        monkeypatch.setattr(viewers[role].figure.canvas, "draw_idle", lambda role=role: closed.update([role]))
    qtbot.wait(20)
    slide(viewers["map"], 2, 5)
    select_point(viewers["map"], 30, 12)
    qtbot.wait(20)
    assert lines(viewers["spectrogram"])["point"] == ("y", [12])
    assert closed == {}  # the closed panels are never drawn again
    # the Point group deleted, its line goes
    bare_app.data_collection.remove_subset_group(bare_app.session.edit_subset_mode.edit_subset[0])
    qtbot.wait(20)
    assert lines(viewers["spectrogram"])["point"] is None
    bare_app.close_tab(bare_app.tab_count - 1, warn=False)
    qtbot.wait(20)
    assert kept() == []


def past(raster, sji, end, inner, frame):
    """The slit-jaw pixel one raster pixel past ``end``, away from ``inner``, both (step, slit) pixels."""
    end, inner = (np.array(raster_point_on_sji(raster, sji, *pixel, frame)) for pixel in (end, inner))
    return 2 * end - inner


def repointed(path, irispy_test_files, step=0.0, drift=0.0, roll=0.0):
    """
    The sit-and-stare fixture's raster written to ``path``, stepping ``step`` arcsec west and drifting ``drift`` arcsec
    north per exposure, with its slit rolled ``roll`` degrees: a scanning raster unless ``step`` is 0.
    """
    with fits.open(find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))) as hdulist:
        aux, header = hdulist[-2], hdulist[0].header  # before the Level 1 file names
        n = np.arange(len(aux.data)) - len(aux.data) // 2
        aux.data[:, aux.header["XCENIX"]] = header["XCEN"] + step * n
        aux.data[:, aux.header["YCENIX"]] = header["YCEN"] + drift * n
        roll = np.radians(roll)
        aux.data[:, aux.header["PC3_2IX"]], aux.data[:, aux.header["PC2_2IX"]] = np.sin(roll), np.cos(roll)
        header["STEPS_AV"] = step
        hdulist.writeto(path)
    return path


def test_sji_to_raster_on_a_sit_and_stare(tmp_path, irispy_test_files):
    bundled, sji = sit_and_stare(irispy_test_files)
    # and a copy whose rolled slit drifts north: each exposure's slit is its own
    path = repointed(tmp_path / SNS.format("raster_t000_r00000"), irispy_test_files, drift=0.1, roll=20)
    [moved] = raster_data([path], ["Si IV 1403"])
    frames = sji[sji.id["Time"]][:, 0, 0]
    for raster in (bundled, moved):
        exposures, top = raster[raster.id["Time"]][:, 0, 0], raster.shape[1] - 1
        for frame in (0, len(frames) // 2, len(frames) - 1):
            exposure = expected_nearest(frames[frame], exposures)  # by time, not place
            low, high = (np.array(raster_point_on_sji(raster, sji, exposure, slit, frame)) for slit in (0, top))
            across = np.array([low[1] - high[1], high[0] - low[0]]) / np.hypot(*(high - low))  # one pixel
            for slit in (0, top // 2, top):
                x, y = raster_point_on_sji(raster, sji, exposure, slit, frame)
                assert sji_to_raster(sji, frame, x, y, raster) == (exposure, slit)
                # beside the slit: its row
                assert sji_to_raster(sji, frame, *np.add((x, y), 5 * across), raster) == (exposure, slit)
            for end, inner in ((0, 1), (top, top - 1)):  # past either end of the slit: outside the raster
                pixel = past(raster, sji, (exposure, end), (exposure, inner), frame)
                assert sji_to_raster(sji, frame, *pixel, raster) is None
    # a day later: no exposure within half a cadence
    x, y = raster_point_on_sji(bundled, sji, 0, 9, 0)
    sji.update_components({sji.id["Time"]: sji[sji.id["Time"]] + np.timedelta64(1, "D")})
    assert sji_to_raster(sji, 0, x, y, bundled) is None


def test_sji_to_raster_on_a_scanning_raster_and_a_stack(tmp_path, irispy_test_files):
    path = repointed(tmp_path / SNS.format("raster_t000_r00000"), irispy_test_files, step=0.3)
    [raster] = raster_data([path], ["Si IV 1403"])
    _, sji = sit_and_stare(irispy_test_files)
    last, top = raster.shape[0] - 1, raster.shape[1] - 1
    # by place, through each frame's own pointing, which follows the Sun's rotation
    for frame in (0, sji.shape[0] - 1):
        for step in (0, last // 2, last):
            for slit in (0, top // 2, top):
                x, y = raster_point_on_sji(raster, sji, step, slit, frame)
                assert sji_to_raster(sji, frame, x, y, raster) == (step, slit)
        # the nearest step and slit row
        assert sji_to_raster(sji, frame, *raster_point_on_sji(raster, sji, 10.4, 20.4, frame), raster) == (10, 20)
        assert sji_to_raster(sji, frame, *raster_point_on_sji(raster, sji, 10.6, 20.6, frame), raster) == (11, 21)
        for end, inner in ((0, 1), (last, last - 1)):  # past the first or last step: outside the raster
            assert sji_to_raster(sji, frame, *past(raster, sji, (end, 9), (inner, 9), frame), raster) is None

    # a stack of the scan and a copy right after it drifting north: the scan nearest the frame's time at the step, and
    # the slit row in that scan's own pointing
    later = repointed(tmp_path / SNS.format("raster_t000_r00001"), irispy_test_files, step=0.3, drift=0.01)
    [stack] = raster_data([path, later], ["Si IV 1403"], stack=True)
    alone = [raster, *raster_data([later], ["Si IV 1403"])]
    times = stack[stack.id["Time"]].copy()
    times[1] += times.max() - times.min()
    stack.update_components({stack.id["Time"]: times})
    frames = sji[sji.id["Time"]][:, 0, 0]
    scans = []
    for frame in (0, len(frames) - 1):
        for step in (0, last):
            scans.append(expected_nearest(frames[frame], times[:, step, 0, 0]))
            x, y = raster_point_on_sji(alone[scans[-1]], sji, step, 9, frame)
            assert sji_to_raster(sji, frame, x, y, stack) == (scans[-1], step, 9)
    assert set(scans) == {0, 1}
    # a day later: the later scan, however far; a scan's steps are places
    sji.update_components({sji.id["Time"]: sji[sji.id["Time"]] + np.timedelta64(1, "D")})
    x, y = raster_point_on_sji(alone[1], sji, 0, 9, 0)
    assert sji_to_raster(sji, 0, x, y, stack) == (1, 0, 9)
    x, y = raster_point_on_sji(raster, sji, 0, 9, 0)
    assert sji_to_raster(sji, 0, x, y, raster) == (0, 9)


def draw_region(app, viewer, roi):
    """Draw ``roi`` on ``viewer``, which makes a new subset, and return the region's subset state."""
    viewer.apply_roi(roi)
    return app.data_collection.subset_groups[-1].subset_state


def check_outline(monkeypatch, raster, sji, region, pixels):
    """Check that ``region`` selects what glue's ``pixels`` does on ``raster`` and in ``sji``'s frames."""
    # glue's own region on the raster's pixels: the raster's own pixels inside it, exactly
    np.testing.assert_array_equal(raster.get_mask(region), raster.get_mask(pixels))
    frames = (0, sji.shape[0] // 2, sji.shape[0] - 1)
    expected = [sji.get_mask(pixels, view=(frame,)) for frame in frames]
    assert np.sum(expected) >= 20
    # and in each slit-jaw frame the same pixels, without inverting the raster's coordinates
    inverted = inversions(monkeypatch, raster)
    for frame, mask in zip(frames, expected):
        np.testing.assert_array_equal(sji.get_mask(region, view=(frame,)), mask)
    assert not inverted


@pytest.mark.parametrize("step", [0.0, 0.3], ids=["sit-and-stare", "scanning"])
@pytest.mark.parametrize(
    "roi",
    [
        RectangularROI(80.3, 100.6, 10.3, 19.8),
        RectangularROI(-20.5, 30.2, -3.7, 25.4),  # past the first step and slit row
        XRangeROI(20.5, 60.2),
        YRangeROI(3.3, 30.1),
        CircularROI(90.2, 20.4, 8.5),
        PolygonalROI([30.2, 150.7, 90.4], [2.3, 15.6, 45.2]),
    ],
    ids=lambda roi: type(roi).__name__,
)
def test_a_map_region_reaches_a_slit_jaw_image_by_its_outline(
    bare_app, monkeypatch, tmp_path, irispy_test_files, roi, step
):
    raster, sji = sit_and_stare(irispy_test_files)
    if step:  # a copy stepping west at each exposure
        path = repointed(tmp_path / SNS.format("raster_t000_r00000"), irispy_test_files, step)
        [raster] = raster_data([path], ["Si IV 1403"])
    viewers = quicklook(bare_app, [raster, sji])
    region = draw_region(bare_app, viewers["map"], roi)
    pixels = roi_to_subset_state(roi, x_att=raster.pixel_component_ids[0], y_att=raster.pixel_component_ids[1])
    check_outline(monkeypatch, raster, sji, region, pixels)


def test_a_region_on_a_map_with_its_axes_swapped(bare_app, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    state = viewers["map"].state
    state.x_att, state.y_att = raster.pixel_component_ids[1], raster.pixel_component_ids[0]  # slit across, exposures up
    # the outline still has a corner at every exposure, past the first exposure and slit row too
    roi = RectangularROI(-3.7, 25.4, -20.5, 30.2)
    region = draw_region(bare_app, viewers["map"], roi)
    pixels = roi_to_subset_state(roi, x_att=raster.pixel_component_ids[1], y_att=raster.pixel_component_ids[0])
    check_outline(monkeypatch, raster, sji, region, pixels)


def test_a_stack_map_region_reaches_another_window_by_its_outline(bare_app, monkeypatch, irispy_test_files):
    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    [stack] = raster_data(files, ["C II 1336"], stack=True)
    [scan] = raster_data(files[2:], ["C II 1336"])
    viewers = quicklook(bare_app, [stack, scan])
    viewers["map"].state.slices = (2, *viewers["map"].state.slices[1:])
    # glue's own region on the stack's pixels selects its steps and slit rows in every scan; its outline, in the
    # pointing of scan 2, those of scan 2 through glue's world coordinates of each scan, and in scan 2 on its own,
    # which stands in for another window of that scan, the pixel at each of them, the first step and last slit row too
    for roi, edge in ((XRangeROI(2.5, 5.5), (3, -1)), (RectangularROI(-3.4, 2.6, 10.3, 50.7), (0, 11))):
        region = draw_region(bare_app, viewers["map"], roi)
        pixels = roi_to_subset_state(roi, x_att=stack.pixel_component_ids[1], y_att=stack.pixel_component_ids[2])
        np.testing.assert_array_equal(stack.get_mask(region), stack.get_mask(pixels))
        np.testing.assert_array_equal(stack.get_mask(region.world)[2], stack.get_mask(pixels)[2])
        expected = scan.get_mask(
            roi_to_subset_state(roi, x_att=scan.pixel_component_ids[0], y_att=scan.pixel_component_ids[1])
        )
        assert expected[edge].all()
        with monkeypatch.context() as patch:
            inverted = inversions(patch, stack)
            np.testing.assert_array_equal(scan.get_mask(region), expected)
        assert not inverted


def test_a_raster_region_is_a_new_subset(bare_app, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    collection, mode = bare_app.data_collection, bare_app.session.edit_subset_mode
    [point] = mode.edit_subset
    state = point.subset_state
    roi = RectangularROI(80.3, 100.6, 10.3, 19.8)
    # the point stays as it was, and the edit subset; one undo removes the region
    viewers["map"].apply_roi(roi)
    assert len(collection.subset_groups) == 2
    assert point.subset_state is state
    assert mode.edit_subset == [point]
    bare_app.session.command_stack.undo()
    assert collection.subset_groups == (point,)
    assert point.subset_state is state
    assert mode.edit_subset == [point]
    bare_app.session.command_stack.redo()
    [_, region] = collection.subset_groups
    assert mode.edit_subset == [point]
    # a subset like any other: on the raster panels, the slit-jaw images and the spectrum
    for viewer in [viewers[role] for role in RASTER_PANELS] + viewers["sji"] + [viewers["spectrum"]]:
        [layer] = [layer for layer in viewer.state.layers if getattr(layer.layer, "group", None) is region]
        assert layer.visible
    pixels = roi_to_subset_state(roi, x_att=raster.pixel_component_ids[0], y_att=raster.pixel_component_ids[1])
    check_outline(monkeypatch, raster, sji, region.subset_state, pixels)
    # the Pixel tool still moves the point, and Clear point leaves the region
    drawn = region.subset_state
    select_point(viewers["map"], 30, 2)
    assert [s.start for s in point.subset_state.slices[:2]] == [30, 2]
    menu_action(viewers["map"], "Clear point").trigger()
    assert coordinator(collection).point is None
    assert collection.subset_groups == (point, region)
    assert region.subset_state is drawn


def test_a_raster_region_edits_only_a_region_picked_to_edit(bare_app, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    collection, mode = bare_app.data_collection, bare_app.session.edit_subset_mode
    first, second = RectangularROI(10.5, 20.5, 2.5, 5.5), RectangularROI(30.5, 40.5, 2.5, 5.5)
    # while the point is the edit subset a region is a new subset, whatever glue's selection mode
    mode.mode = OrMode
    viewers["map"].apply_roi(first)
    [point, region] = collection.subset_groups
    # a region picked to edit, as in the data collection, takes glue's selection mode
    mode.edit_subset = [region]
    viewers["map"].apply_roi(second)
    assert collection.subset_groups == (point, region)
    step, slit = raster.pixel_component_ids[:2]
    expected = roi_to_subset_state(first, x_att=step, y_att=slit) | roi_to_subset_state(second, x_att=step, y_att=slit)
    np.testing.assert_array_equal(raster.get_mask(region.subset_state), raster.get_mask(expected))
    np.testing.assert_array_equal(sji.get_mask(region.subset_state, view=(0,)), sji.get_mask(expected, view=(0,)))
    # undoing both leaves no removed subset to edit
    bare_app.session.command_stack.undo()
    bare_app.session.command_stack.undo()
    assert collection.subset_groups == (point,)
    assert mode.edit_subset == []


def inside_in_frame(raster, sji, frame, roi):
    """
    Whether each raster pixel lies inside ``roi`` within slit-jaw frame ``frame``, between its first and last pixel
    centres, from the datasets' coordinates.
    """
    step, slit = np.indices(raster.shape[:2])
    x, y = raster_point_on_sji(raster, sji, step, slit, frame)
    inside = roi.contains(x, y) & (0 <= x) & (x <= sji.shape[2] - 1) & (0 <= y) & (y <= sji.shape[1] - 1)
    return np.repeat(inside[..., None], raster.shape[2], axis=2)


@pytest.mark.parametrize("step", [0.0, 0.3], ids=["sit-and-stare", "scanning"])
def test_a_slit_jaw_region_is_a_new_subset(bare_app, monkeypatch, tmp_path, irispy_test_files, step):
    raster, sji = sit_and_stare(irispy_test_files)
    if step:  # a copy stepping west at each exposure
        path = repointed(tmp_path / SNS.format("raster_t000_r00000"), irispy_test_files, step)
        [raster] = raster_data([path], ["Si IV 1403"])
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    collection, mode = bare_app.data_collection, bare_app.session.edit_subset_mode
    [point] = mode.edit_subset
    state = point.subset_state
    frame = sji.shape[0] // 2
    sji_viewer.state.slices = (frame, 0, 0)
    roi = RectangularROI(10.3, 20.6, 5.4, 25.7)
    # the point stays as it was, and the edit subset; one undo removes the region
    sji_viewer.apply_roi(roi)
    assert len(collection.subset_groups) == 2
    assert point.subset_state is state
    assert mode.edit_subset == [point]
    bare_app.session.command_stack.undo()
    assert collection.subset_groups == (point,)
    assert point.subset_state is state
    assert mode.edit_subset == [point]
    bare_app.session.command_stack.redo()
    [_, region] = collection.subset_groups
    assert mode.edit_subset == [point]
    # a subset like any other: on the raster panels, the slit-jaw image and the spectrum
    for viewer in [viewers[role] for role in RASTER_PANELS] + [sji_viewer, viewers["spectrum"]]:
        [layer] = [layer for layer in viewer.state.layers if getattr(layer.layer, "group", None) is region]
        assert layer.visible
    # glue's own region on the slit-jaw image's pixels, in every frame
    pixels = roi_to_subset_state(roi, x_att=sji.pixel_component_ids[2], y_att=sji.pixel_component_ids[1])
    np.testing.assert_array_equal(sji.get_mask(region.subset_state), sji.get_mask(pixels))
    # and the raster's pixels inside it at the pointing of the frame it was drawn on, each placed once rather than at
    # every wavelength, which made a full raster's spectrum take seconds
    expected = inside_in_frame(raster, sji, frame, roi)
    assert expected.sum() >= 20 * raster.shape[2]
    placed, contains = [], PolygonalROI.contains
    monkeypatch.setattr(PolygonalROI, "contains", lambda self, x, y: placed.append(np.size(x)) or contains(self, x, y))
    np.testing.assert_array_equal(raster.get_mask(region.subset_state), expected)
    assert placed == [raster.shape[0] * raster.shape[1]]
    # a Pixel click on the slit-jaw image still moves the point to the raster there, and leaves the region
    drawn = region.subset_state
    index = sji_to_raster(sji, frame, 15, 15, raster)
    assert index is not None
    select_point(sji_viewer, 15, 15)
    assert point.subset_state.reference_data is raster
    assert [s.start for s in point.subset_state.slices] == [*index, None]
    assert region.subset_state is drawn


def test_a_slit_jaw_region_edits_only_a_region_picked_to_edit(bare_app, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    collection, mode = bare_app.data_collection, bare_app.session.edit_subset_mode
    first, second = RectangularROI(26.3, 32.6, 5.4, 15.7), RectangularROI(16.3, 24.6, 20.4, 30.7)
    # while the point is the edit subset a region is a new subset, whatever glue's selection mode
    mode.mode = OrMode
    sji_viewer.apply_roi(first)
    [point, region] = collection.subset_groups
    state = point.subset_state
    # a region picked to edit takes glue's selection mode, on the raster too
    mode.edit_subset = [region]
    sji_viewer.apply_roi(second)
    assert collection.subset_groups == (point, region)
    expected = [inside_in_frame(raster, sji, 0, roi) for roi in (first, second)]
    assert all(mask.any() for mask in expected)  # each on the raster, so that replacing one with the other shows
    np.testing.assert_array_equal(raster.get_mask(region.subset_state), expected[0] | expected[1])
    # and the Pixel tool replaces it with the slit-jaw pixel clicked, as on the raster panels, leaving the point
    select_point(sji_viewer, 15, 15)
    assert region.subset_state.reference_data is sji
    assert [s.start for s in region.subset_state.slices] == [None, 15, 15]
    assert point.subset_state is state


def test_a_slit_jaw_range_or_frame_axis_region(bare_app, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    collection = bare_app.data_collection
    [point] = collection.subset_groups
    state = point.subset_state
    # a range across the slit-jaw frame reaches the raster within the frame, which the raster runs past here
    frame = sji_viewer.state.slices[0]
    for roi in (XRangeROI(16.3, 24.6), YRangeROI(10.2, 20.7)):
        expected = inside_in_frame(raster, sji, frame, roi)
        assert expected.sum() >= 20 * raster.shape[2]
        np.testing.assert_array_equal(raster.get_mask(draw_region(bare_app, sji_viewer, roi)), expected)
    # on a slit-jaw viewer showing the frame axis, a region is glue's own, on that image only
    sji_viewer.state.x_att = sji.pixel_component_ids[0]
    roi = RectangularROI(10.3, 40.6, 5.4, 25.7)
    region = draw_region(bare_app, sji_viewer, roi)
    pixels = roi_to_subset_state(roi, x_att=sji.pixel_component_ids[0], y_att=sji.pixel_component_ids[1])
    np.testing.assert_array_equal(sji.get_mask(region), sji.get_mask(pixels))
    with pytest.raises(IncompatibleAttribute):
        raster.get_mask(region)
    assert len(collection.subset_groups) == 4
    assert point.subset_state is state


@pytest.mark.remote_data
def test_the_slit_on_a_full_slit_jaw_image(bare_app, irispy_data):
    sji = image_data(irispy_data("iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz"))
    [viewer] = quicklook(bare_app, [sji])["sji"]
    n, ny, _ = sji.shape
    for frame in (0, n // 2, n - 1):
        viewer.state.slices = (frame, 0, 0)
        x = sji.meta["slit x position"][frame] - 1
        assert overlays(viewer)[0] == [[x, -0.5], [x, ny - 0.5]]


def viewer_rows(app):
    """What each viewer of the last tab shows."""
    return [
        (
            type(v).__name__,
            v.state.title,
            *(getattr(getattr(v.state, att, None), "label", None) for att in ("x_att", "y_att")),
            getattr(v.state, "slices", None),
        )
        for v in app.viewers[-1]
    ]


def copy_files(folder, paths):
    folder.mkdir()
    for path in paths:
        shutil.copy2(path, folder / path.name.replace("_test.fits", ".fits"))
    return folder


def browse(qtbot, app, monkeypatch, folder, rows, only=None):
    """
    Load observation ``rows`` of ``folder`` through the observation browser, with its quicklook box as is: every
    entry, or with ``only`` those whose names start with any of it.
    """
    from glue_solar.sources.iris import browse_iris
    from glue_solar.sources.loaders.iris import QtIRISImporter

    monkeypatch.setattr(QtWidgets.QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(folder))

    def tick_and_load(dialog):
        for row in rows:
            item = dialog.obs_tree.topLevelItem(row)
            item.setCheckState(0, Qt.Checked)
            for entry in map(item.child, range(item.childCount()) if only else ()):
                entry.setCheckState(0, Qt.Checked if entry.text(0).startswith(only) else Qt.Unchecked)
        load_selected(qtbot, dialog)
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtIRISImporter, "exec", tick_and_load)
    browse_iris(app.session, app.data_collection)


def test_the_three_entry_points_open_the_same_quicklook(qtbot, monkeypatch, tmp_path, irispy_test_files):
    from glue.core.data_factories import load_data

    from glue_solar.sources.iris import iris_quicklook, quicklook_iris

    paths = [find_irispy_test_file(irispy_test_files, SNS.format(name)) for name in ("raster_t000_r00000", "SJI_1400_t000")]
    folder = copy_files(tmp_path / "sns", paths)
    rows = []
    for path in ("browser", "menu", "startup"):
        app = bare_app_for(qtbot, monkeypatch)
        if path == "browser":  # one raster window ticked: the others would join its quicklook
            browse(qtbot, app, monkeypatch, folder, [0], only=("Mg II k", "SJI"))
        else:
            # glue loads command-line files with add_datasets, whose autolinker has nothing to suggest for
            # IRIS data on glue-core 1.27.0 (with glue-viz/glue#2595 it asks, before any startup action)
            app.data_collection.extend([data for p in sorted(folder.iterdir()) for data in as_list(load_data(str(p)))])
            (quicklook_iris if path == "menu" else iris_quicklook)(app.session, app.data_collection)
        rows.append(viewer_rows(app))
    assert rows[0] == rows[1] == rows[2]
    assert len(rows[0]) == 5  # map, spectrogram, wavelength, SJI 1400 and spectrum


def test_the_browser_and_the_menu_open_the_chosen_observation(qtbot, monkeypatch, tmp_path, irispy_test_files):
    from glue_solar.sources.iris import quicklook_iris

    sns = find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))
    other = find_irispy_test_file(irispy_test_files, SCAN)
    folder = copy_files(tmp_path / "two", [sns, other])
    app = bare_app_for(qtbot, monkeypatch)
    browse(qtbot, app, monkeypatch, folder, [1])  # the second observation only
    assert app.tab_count == 2
    shown = app.viewers[-1][0].state.reference_data
    browsed = app.data_collection[0]
    assert observation_key(shown) == observation_key(browsed)
    # both observations loaded: the menu asks, and opens the one chosen
    browse(qtbot, app, monkeypatch, folder, [0])
    keys = [observation_key(data) for data in app.data_collection]
    choice = {}

    def choose(parent, title, label, items, *args):
        choice["items"] = items
        return items[1], True

    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", choose)
    tabs = app.tab_count
    quicklook_iris(app.session, app.data_collection)
    assert len(choice["items"]) == 2
    assert app.tab_count == tabs + 1
    assert observation_key(app.viewers[-1][0].state.reference_data) == sorted(set(keys), key=keys.index)[1]


def test_startup_shows_the_first_raster_file(qtbot, monkeypatch, irispy_test_files):
    from glue.core.data_factories import load_data

    from glue_solar.sources.iris import iris_quicklook

    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    app = bare_app_for(qtbot, monkeypatch)
    app.data_collection.extend([data for path in files for data in load_data(path)])
    labels = [data.label for data in app.data_collection]
    assert len(set(labels)) == len(labels) == 3 * 9  # each file's windows are labelled by its raster number
    iris_quicklook(app.session, app.data_collection)
    shown = app.viewers[-1][0].state.reference_data
    assert shown.ndim == 3
    assert shown.label == "Mg_II_k_2796-3860258481-2014-03-29T14:09:38-r00000"
    assert "stacks of scans need" in app.statusBar().currentMessage()


def as_list(value):
    return value if isinstance(value, list) else [value]


def bare_app_for(qtbot, monkeypatch):
    """An application like ``bare_app``, for tests that need several."""

    def modal(*args, **kwargs):
        raise AssertionError("a modal dialog opened")

    for cls in (QtWidgets.QMessageBox, QtWidgets.QDialog):
        monkeypatch.setattr(cls, "exec_", modal, raising=False)
        monkeypatch.setattr(cls, "exec", modal, raising=False)
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    return app


# The move/stay matrix: each event changes the sliders and the point it lists, and nothing else


def sliders(app, viewers):
    """
    Each Image panel's slider positions, None along its shown axes, keyed by role and 'sji0', 'sji1', ... for
    the slit-jaw panels; and the point as its dataset's label and indices (None along free axes), or None.
    """
    found = {}
    panels = [(role, viewers[role]) for role in RASTER_PANELS] + [(f"sji{n}", v) for n, v in enumerate(viewers["sji"])]
    # another window's λ–time or λ–scan panel: 'wavelength1', 'wavelength2', ...
    others = [panels["wavelength"] for panels in viewers.get("windows", []) if "wavelength" in panels]
    panels += [(f"wavelength{n}", viewer) for n, viewer in enumerate(others, 1)]
    for key, viewer in panels:
        shown = {viewer.state.x_att.axis, viewer.state.y_att.axis}
        found[key] = tuple(None if axis in shown else index for axis, index in enumerate(viewer.state.slices))
    [group] = app.session.edit_subset_mode.edit_subset
    point = group.subset_state
    if isinstance(point, PixelSubsetState):
        found["point"] = (point.reference_data.label, tuple(s.start for s in point.slices))
    else:
        found["point"] = None
    return found


def changes(app, qtbot, viewers, event):
    """Run ``event``, let Qt run the coordinator's deferred work, and return what it changed in ``sliders``."""
    before = sliders(app, viewers)
    event()
    qtbot.wait(20)
    after = sliders(app, viewers)
    return {key: value for key, value in after.items() if value != before[key]}


def slide(viewer, axis, index):
    """Move the viewer's slice slider along ``axis`` to ``index``, as a click on its track or a key does."""
    viewer.options_widget().slice_helper._sliders[axis].value_slice_center.setValue(index)


def type_index(viewer, axis, index):
    """Type ``index`` into the box next to the viewer's slice slider along ``axis``."""
    box = viewer.options_widget().slice_helper._sliders[axis].text_slider_label
    box.setText(str(index))
    box.editingFinished.emit()


def test_what_moves_on_a_scanning_raster(bare_app, qtbot, scans):
    scan, _ = scans
    times = scan[scan.id["Time"]][:, 0, 0]
    frames = times[0] + (np.arange(24) - 2) * ((times[-1] - times[0]) / 19)  # about three per step
    sji = slit_jaw(frames, scan)
    viewers = quicklook(bare_app, [scan, sji])
    [sji_viewer] = viewers["sji"]
    label = scan.label

    def frame(step):
        return expected_nearest(times[step], frames)

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    assert len({frame(step) for step in range(scan.shape[0])}) == scan.shape[0]  # each step its own frame
    # a map click moves the point; the spectrogram to its step, the λ panel to its slit, the SJI to its time
    assert event(lambda: select_point(viewers["map"], 1, 30)) == {
        "point": (label, (1, 30, None)),
        "spectrogram": (1, None, None),
        "wavelength": (None, 30, None),
        "sji0": (frame(1), None, None),
    }
    # a spectrogram click (wavelength 5, slit 40) keeps the step, so the time
    assert event(lambda: select_point(viewers["spectrogram"], 5, 40)) == {
        "point": (label, (1, 40, None)),
        "wavelength": (None, 40, None),
        "map": (None, None, 5),
    }
    # a λ panel click (wavelength 9, step 6) keeps the slit
    assert event(lambda: select_point(viewers["wavelength"], 9, 6)) == {
        "point": (label, (6, 40, None)),
        "spectrogram": (6, None, None),
        "map": (None, None, 9),
        "sji0": (frame(6), None, None),
    }
    # the step slider, moved or typed, moves the point and the time; no wavelength slider moves
    for move, step in ((slide, 2), (type_index, 3)):
        assert event(lambda move=move, step=step: move(viewers["spectrogram"], 0, step)) == {
            "point": (label, (step, 40, None)),
            "spectrogram": (step, None, None),
            "sji0": (frame(step), None, None),
        }
    assert event(lambda: slide(viewers["map"], 2, 11)) == {"map": (None, None, 11)}
    assert event(lambda: slide(viewers["wavelength"], 1, 7)) == {
        "point": (label, (3, 7, None)),
        "wavelength": (None, 7, None),
    }
    # a slit-jaw follower moved by hand keeps its frame until the next sync
    assert event(lambda: slide(sji_viewer, 0, 0)) == {"sji0": (0, None, None)}
    assert event(lambda: slide(viewers["spectrogram"], 0, 5)) == {
        "point": (label, (5, 7, None)),
        "spectrogram": (5, None, None),
        "sji0": (frame(5), None, None),
    }
    # a slit-jaw master moves nothing on a scanning raster, whose time is the point's step
    assert event(lambda: menu_action(sji_viewer, "Time master").trigger()) == {}
    assert "time master" in readout(sji_viewer)
    assert event(lambda: slide(sji_viewer, 0, 10)) == {"sji0": (10, None, None)}
    assert event(lambda: select_point(viewers["spectrogram"], 4, 60)) == {
        "point": (label, (5, 60, None)),
        "wavelength": (None, 60, None),
        "map": (None, None, 4),
    }
    assert event(lambda: menu_action(viewers["map"], "Time master").trigger()) == {"sji0": (frame(5), None, None)}
    # after Clear point the time stays at the last point's step, and nothing follows the sliders
    assert event(lambda: menu_action(viewers["map"], "Clear point").trigger()) == {"point": None}
    assert event(lambda: slide(viewers["spectrogram"], 0, 0)) == {"spectrogram": (0, None, None)}
    assert event(lambda: slide(viewers["wavelength"], 1, 20)) == {"wavelength": (None, 20, None)}
    assert "time master, step 5" in readout(viewers["spectrogram"])
    # until the next click
    assert event(lambda: select_point(viewers["map"], 2, 50)) == {
        "point": (label, (2, 50, None)),
        "spectrogram": (2, None, None),
        "wavelength": (None, 50, None),
        "sji0": (frame(2), None, None),
    }


def test_what_moves_on_a_stack(bare_app, qtbot, scans):
    _, stack = scans
    times = stack[stack.id["Time"]][:, :, 0, 0]  # by scan and step
    first, last = times.min(), times.max()
    # about three frames per step, from just before the first scan to just after the last
    frames = first + (np.arange(3 * times.size + 4) - 2) * ((last - first) / (3 * times.size - 1))
    viewers = quicklook(bare_app, [stack, slit_jaw(frames, stack)])
    [sji_viewer] = viewers["sji"]
    label = stack.label
    wave = expected_start(stack)[-1]  # the map's wavelength

    def frame(scan, step):
        return expected_nearest(times[scan, step], frames)

    def scan_at(index, step):  # the scan nearest slit-jaw frame ``index`` at raster step ``step``
        return expected_nearest(frames[index], times[:, step])

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    assert len({frame(scan, step) for scan, step in np.ndindex(times.shape)}) == times.size  # each its own frame
    # a map click moves the point at the map's scan: the spectrogram to its step, the λ panel to its step and
    # slit, the SJI to the time of its scan and step
    assert event(lambda: select_point(viewers["map"], 2, 30)) == {
        "point": (label, (0, 2, 30, None)),
        "spectrogram": (0, 2, None, None),
        "wavelength": (None, 2, 30, None),
        "sji0": (frame(0, 2), None, None),
    }
    # the scan slider of the map or of the spectrogram moves the point, the other's scan and the time
    assert event(lambda: slide(viewers["map"], 0, 1)) == {
        "point": (label, (1, 2, 30, None)),
        "map": (1, None, None, wave),
        "spectrogram": (1, 2, None, None),
        "sji0": (frame(1, 2), None, None),
    }
    assert event(lambda: slide(viewers["spectrogram"], 0, 2)) == {
        "point": (label, (2, 2, 30, None)),
        "map": (2, None, None, wave),
        "spectrogram": (2, 2, None, None),
        "sji0": (frame(2, 2), None, None),
    }
    # a typed step moves the point, the λ panel's step and the time
    assert event(lambda: type_index(viewers["spectrogram"], 1, 6)) == {
        "point": (label, (2, 6, 30, None)),
        "spectrogram": (2, 6, None, None),
        "wavelength": (None, 6, 30, None),
        "sji0": (frame(2, 6), None, None),
    }
    # a λ–scan click (wavelength 9, scan 0) moves the map to its scan and wavelength; step and slit stay
    assert event(lambda: select_point(viewers["wavelength"], 9, 0)) == {
        "point": (label, (0, 6, 30, None)),
        "map": (0, None, None, 9),
        "spectrogram": (0, 6, None, None),
        "sji0": (frame(0, 6), None, None),
    }
    # a slit-jaw follower moved by hand keeps its frame through a wavelength step, until the next sync
    assert event(lambda: slide(sji_viewer, 0, 40)) == {"sji0": (40, None, None)}
    assert event(lambda: slide(viewers["map"], 3, 14)) == {"map": (0, None, None, 14)}
    assert event(lambda: slide(viewers["wavelength"], 2, 70)) == {
        "point": (label, (0, 6, 70, None)),
        "wavelength": (None, 6, 70, None),
        "sji0": (frame(0, 6), None, None),
    }
    # a slit-jaw master moves the point to the scan nearest its frame at the point's step; step and slit stay
    assert event(lambda: slide(sji_viewer, 0, 60)) == {"sji0": (60, None, None)}
    scan = scan_at(60, 6)
    assert event(lambda: menu_action(sji_viewer, "Time master").trigger()) == {
        "point": (label, (scan, 6, 70, None)),
        "map": (scan, None, None, 14),
        "spectrogram": (scan, 6, None, None),
    }
    assert "time master" in readout(sji_viewer)
    scan = scan_at(36, 6)
    assert event(lambda: slide(sji_viewer, 0, 36)) == {
        "point": (label, (scan, 6, 70, None)),
        "map": (scan, None, None, 14),
        "spectrogram": (scan, 6, None, None),
        "sji0": (36, None, None),
    }
    # the master rules: the map's scan slider moved by hand snaps back
    shown = []
    viewers["map"].state.add_callback("slices", lambda slices: shown.append(slices[0]))
    assert event(lambda: slide(viewers["map"], 0, 0)) == {}
    assert shown == [0, scan]
    assert event(lambda: menu_action(viewers["map"], "Time master").trigger()) == {"sji0": (frame(scan, 6), None, None)}
    # after Clear point the time follows the map's scan slider at the last point's step, and nothing else
    assert event(lambda: menu_action(viewers["map"], "Clear point").trigger()) == {"point": None}
    assert event(lambda: slide(viewers["spectrogram"], 0, 0)) == {"spectrogram": (0, 6, None, None)}
    assert event(lambda: type_index(viewers["spectrogram"], 1, 0)) == {"spectrogram": (0, 0, None, None)}
    assert event(lambda: slide(viewers["map"], 0, 2)) == {
        "map": (2, None, None, 14),
        "sji0": (frame(2, 6), None, None),
    }
    assert "time master, step 6" in readout(viewers["map"])
    # until the next click, at the map's scan
    assert event(lambda: select_point(viewers["map"], 3, 20)) == {
        "point": (label, (2, 3, 20, None)),
        "spectrogram": (2, 3, None, None),
        "wavelength": (None, 3, 20, None),
        "sji0": (frame(2, 3), None, None),
    }
    # a click on a slit-jaw image without coordinates, which places nothing, stays a slit-jaw point
    sji = sji_viewer.state.reference_data
    assert event(lambda: select_point(sji_viewer, 2, 1)) == {"point": (sji.label, (None, 1, 2))}


def test_a_click_on_another_scan_snaps_back_to_a_slit_jaw_master(bare_app, qtbot, scans):
    _, stack = scans
    scan_times = stack[stack.id["Time"]][:, expected_start(stack)[1], 0, 0]  # at the point's step
    frames = scan_times[0] + np.arange(40) * (scan_times[-1] - scan_times[0]) / 39
    viewers = quicklook(bare_app, [stack, slit_jaw(frames, stack)])
    [sji_viewer] = viewers["sji"]
    menu_action(sji_viewer, "Time master").trigger()
    slide(sji_viewer, 0, 20)
    scan = expected_nearest(frames[20], scan_times)
    qtbot.waitUntil(lambda: viewers["map"].state.slices[0] == scan)
    # a λ–scan click (wavelength 2, scan 0) moves only the map's wavelength
    assert changes(bare_app, qtbot, viewers, lambda: select_point(viewers["wavelength"], 2, 0)) == {
        "map": (scan, None, None, 2),
    }


def test_what_moves_on_a_sit_and_stare(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    sjis = [sji, image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_2796_t000")))]
    viewers = quicklook(bare_app, [raster, *sjis])
    label = raster.label
    times = raster[raster.id["Time"]][:, 0, 0]
    master_times = sji[sji.id["Time"]][:, 0, 0]
    # per exposure, the frame of SJI 1400 and of SJI 2796 that matches it, or None
    f1400, f2796 = ([nearest_frame(data, when) for when in times] for data in sjis)

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    def no_match(n, when):
        """SJI ``n`` keeps its frame, greyed, and reads NO MATCH with the nearest frame's offset from ``when``."""
        return not check_follower(bare_app, qtbot, when, sjis[n], viewers["sji"][n])

    start, _, wavelength = expected_start(raster)
    qtbot.wait(20)
    # the point opens on an exposure half a cadence from both slit-jaw images: each keeps frame 0
    assert [viewer.state.slices[0] for viewer in viewers["sji"]] == [0, 0]
    assert no_match(0, times[start])
    assert no_match(1, times[start])
    # a map click (exposure 78, slit 10) moves the spectrogram to its exposure, the λ–time panel to its slit and
    # SJI 1400 to its time; SJI 2796 has no frame near it and keeps its own
    assert f2796[78] is None
    assert event(lambda: select_point(viewers["map"], 78, 10)) == {
        "point": (label, (78, 10, None)),
        "spectrogram": (78, None, None),
        "wavelength": (None, 10, None),
        "sji0": (f1400[78], None, None),
    }
    assert no_match(1, times[78])
    # a spectrogram click (wavelength 5, slit 30) keeps the exposure, so the time
    assert event(lambda: select_point(viewers["spectrogram"], 5, 30)) == {
        "point": (label, (78, 30, None)),
        "wavelength": (None, 30, None),
        "map": (None, None, 5),
    }
    # a λ–time click (wavelength 9, exposure 35) keeps the slit; now SJI 1400 has no frame near the time
    assert f1400[35] is None
    assert event(lambda: select_point(viewers["wavelength"], 9, 35)) == {
        "point": (label, (35, 30, None)),
        "spectrogram": (35, None, None),
        "map": (None, None, 9),
        "sji1": (f2796[35], None, None),
    }
    assert no_match(0, times[35])
    # the exposure slider, moved or typed, moves the point and both slit-jaw images; no wavelength slider moves
    for move, exposure in ((slide, 130), (type_index, 61)):
        assert event(lambda move=move, exposure=exposure: move(viewers["spectrogram"], 0, exposure)) == {
            "point": (label, (exposure, 30, None)),
            "spectrogram": (exposure, None, None),
            "sji0": (f1400[exposure], None, None),
            "sji1": (f2796[exposure], None, None),
        }
    # a slit-jaw follower moved by hand keeps its frame through a wavelength step, until the next sync: the slit
    # slider moves the point, which syncs
    assert event(lambda: slide(viewers["sji"][1], 0, 0)) == {"sji1": (0, None, None)}
    assert event(lambda: slide(viewers["map"], 2, 11)) == {"map": (None, None, 11)}
    assert event(lambda: slide(viewers["wavelength"], 1, 7)) == {
        "point": (label, (61, 7, None)),
        "wavelength": (None, 7, None),
        "sji1": (f2796[61], None, None),
    }

    # SJI 1400 as time master: its frame already matches the exposure and SJI 2796's frame, so nothing moves
    assert expected_nearest(master_times[f1400[61]], times) == 61
    assert nearest_frame(sjis[1], master_times[f1400[61]]) == f2796[61]
    assert event(lambda: menu_action(viewers["sji"][0], "Time master").trigger()) == {}
    assert "time master" in readout(viewers["sji"][0])
    # its frame, moved or typed, moves the raster's exposure, the point and SJI 2796 to the nearest of each
    for move, frame in ((slide, 5), (type_index, 40)):
        exposure = expected_nearest(master_times[frame], times)
        assert event(lambda move=move, frame=frame: move(viewers["sji"][0], 0, frame)) == {
            "sji0": (frame, None, None),
            "point": (label, (exposure, 7, None)),
            "spectrogram": (exposure, None, None),
            "sji1": (nearest_frame(sjis[1], master_times[frame]), None, None),
        }
        assert check_follower(bare_app, qtbot, master_times[frame], raster, viewers["spectrogram"])
    # the master rules: the raster's own exposure slider, or a map or λ–time click on another exposure, snaps back
    # to frame 40's exposure; a click's slit or wavelength still moves
    shown = []
    viewers["spectrogram"].state.add_callback("slices", lambda slices: shown.append(slices[0]))
    assert event(lambda: slide(viewers["spectrogram"], 0, 100)) == {}
    assert shown == [100, exposure]
    assert event(lambda: select_point(viewers["map"], 150, 33)) == {
        "point": (label, (exposure, 33, None)),
        "wavelength": (None, 33, None),
    }
    assert event(lambda: select_point(viewers["wavelength"], 7, 150)) == {"map": (None, None, 7)}
    # SJI 2796 moved by hand keeps its frame until the next sync, here the map taking the time master back, which
    # leaves SJI 1400 on frame 40
    assert event(lambda: slide(viewers["sji"][1], 0, 0)) == {"sji1": (0, None, None)}
    assert f1400[exposure] == 40
    assert event(lambda: menu_action(viewers["map"], "Time master").trigger()) == {
        "sji1": (f2796[exposure], None, None)
    }
    assert f"time master, step {exposure}" in readout(viewers["spectrogram"])

    # after Clear point the exposure slider still drives the time, and nothing else follows
    assert event(lambda: menu_action(viewers["map"], "Clear point").trigger()) == {"point": None}
    assert event(lambda: slide(viewers["spectrogram"], 0, 186)) == {
        "spectrogram": (186, None, None),
        "sji0": (f1400[186], None, None),
        "sji1": (f2796[186], None, None),
    }
    assert "time master, step 186" in readout(viewers["spectrogram"])
    assert event(lambda: slide(viewers["wavelength"], 1, 25)) == {"wavelength": (None, 25, None)}
    # until the next click
    assert event(lambda: select_point(viewers["map"], 3, 12)) == {
        "point": (label, (3, 12, None)),
        "spectrogram": (3, None, None),
        "wavelength": (None, 12, None),
        "sji0": (f1400[3], None, None),
        "sji1": (f2796[3], None, None),
    }

    # the spectrogram's axis combo to exposure against slit: glue shows its wavelength slider, where the spectrogram
    # last had it, and a λ–time click moves it as the map's
    spectrogram = viewers["spectrogram"].state

    def x_axis(world):
        spectrogram.x_att_world = raster.world_component_ids[world]

    assert event(lambda: x_axis(0)) == {"spectrogram": (None, None, wavelength)}
    assert spectrogram.x_axislabel.startswith(f"{EXPOSURES}\n")
    assert event(lambda: select_point(viewers["wavelength"], 20, 100)) == {
        "point": (label, (100, 12, None)),
        "map": (None, None, 20),
        "spectrogram": (None, None, 20),
        "sji0": (f1400[100], None, None),
        "sji1": (f2796[100], None, None),
    }
    # and back to wavelength: the coordinator puts its exposure slider on the point
    assert event(lambda: x_axis(2)) == {"spectrogram": (100, None, None)}


def test_closing_the_slit_jaw_master_makes_the_raster_master_again(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    sjis = [sji, image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_2796_t000")))]
    viewers = quicklook(bare_app, [raster, *sjis])
    label = raster.label
    times = raster[raster.id["Time"]][:, 0, 0]
    master_times = sji[sji.id["Time"]][:, 0, 0]
    _, slit, _ = expected_start(raster)

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    menu_action(viewers["sji"][0], "Time master").trigger()
    exposure = expected_nearest(master_times[40], times)
    assert event(lambda: slide(viewers["sji"][0], 0, 40)) == {
        "sji0": (40, None, None),
        "point": (label, (exposure, slit, None)),
        "spectrogram": (exposure, None, None),
        "sji1": (nearest_frame(sjis[1], master_times[40]), None, None),
    }
    # closing it moves nothing; the raster is master again, and SJI 2796 follows its exposure slider
    assert event(lambda: viewers["sji"][0].close(warn=False)) == {}
    assert f"time master, step {exposure}" in readout(viewers["spectrogram"])
    assert event(lambda: slide(viewers["spectrogram"], 0, 186)) == {
        "point": (label, (186, slit, None)),
        "spectrogram": (186, None, None),
        "sji1": (nearest_frame(sjis[1], times[186]), None, None),
    }
    assert "time master, step 186" in readout(viewers["spectrogram"])


def type_in_dialog(monkeypatch, typed, tick=False, every=1):
    """
    Make each text or range dialog return ``typed``, as if typed and confirmed, with its box ticked if ``tick`` and
    Loop's every Nth index at ``every``; returns the texts the dialogs opened with, for Loop with that index and box.
    """
    opened = []
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText", lambda *args, text="", **kwargs: opened.append(text) or (typed, True)
    )

    def exec_(dialog):
        line = dialog.findChild(QtWidgets.QLineEdit)
        assert line.selectedText() == line.text()
        spins, boxes = dialog.findChildren(QtWidgets.QSpinBox), dialog.findChildren(QtWidgets.QCheckBox)
        if spins:  # Loop's
            opened.append((line.text(), *[spin.value() for spin in spins], *[box.isChecked() for box in boxes]))
        else:
            opened.append(line.text())
            assert not any(box.isChecked() for box in boxes)
        line.setText(typed)
        for spin in spins:
            spin.setValue(every)
        for box in boxes:
            box.setChecked(tick)
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    return opened


def utc(when):
    return np.datetime_as_string(when, unit="ms")


def refusals(monkeypatch):
    """The texts of glue's error boxes from now on, which glue would raise instead while testing."""
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    return shown


def test_what_moves_on_go_to_utc(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    label = raster.label
    times, frames = (data[data.id["Time"]][:, 0, 0] for data in (raster, sji))
    _, slit, _ = expected_start(raster)

    def go_to(viewer, text):
        opened = type_in_dialog(monkeypatch, text)
        return changes(bare_app, qtbot, viewers, lambda: menu_action(viewer, "Go to UTC…").trigger()), opened

    # under the raster master the spectrogram's exposure slider goes to the exposure nearest the typed time, from the
    # displayed exposure's, and the point and the slit-jaw image follow, as for the slider
    when = times[150] + (times[151] - times[150]) * 0.45
    shown = viewers["spectrogram"].state.slices[0]
    assert go_to(viewers["spectrogram"], utc(when)) == (
        {
            "point": (label, (150, slit, None)),
            "spectrogram": (150, None, None),
            "sji0": (nearest_frame(sji, times[150]), None, None),
        },
        [utc(times[shown])],
    )
    # typed in the slit-jaw viewer, or in the map, which shows the exposures, the raster goes all the same, from the
    # master's time, and the slit-jaw image follows it
    shown = 150
    for viewer, when in ((sji_viewer, frames[20] + np.timedelta64(40, "s")), (viewers["map"], times[100])):
        exposure = expected_nearest(when, times)
        assert go_to(viewer, utc(when)) == (
            {
                "point": (label, (exposure, slit, None)),
                "spectrogram": (exposure, None, None),
                "sji0": (nearest_frame(sji, times[exposure]), None, None),
            },
            [utc(times[shown])],
        )
        shown = exposure
    # a slit-jaw image of an observation without a time master, here outside any quicklook, moves itself
    other = image_data(
        find_irispy_test_file(irispy_test_files, "iris_l2_20230408_110821_3880012095_SJI_1400_t000.fits")
    )
    bare_app.data_collection.append(other)
    alone = bare_app.new_data_viewer(ImageViewer, data=other)
    alone_times = other[other.id["Time"]][:, 0, 0]
    assert go_to(alone, utc(alone_times[1])) == ({}, [utc(alone_times[0])])
    assert alone.state.slices[0] == 1
    # nothing within half the master's cadence, typed in the slit-jaw viewer, whose last frame is within half its own;
    # an unreadable time; a viewer of data without IRIS times, even of the observation, as an AIA cutout: nothing
    # moves, and glue says why
    assert times[-1] + np.timedelta64(60, "s") - frames[-1] <= _half_cadence(frames)
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    plain.meta.update(OBSID=raster.meta["OBSID"], STARTOBS=raster.meta["STARTOBS"])
    bare_app.data_collection.append(plain)
    shown = refusals(monkeypatch)
    for viewer, text, message in (
        (sji_viewer, utc(times[-1] + np.timedelta64(60, "s")), f"Nothing in {label} is within half a cadence"),
        (viewers["spectrogram"], "noon", "'noon' is not a UTC time"),
        (bare_app.new_data_viewer(ImageViewer, data=plain), utc(when), "slider of IRIS data"),
    ):
        assert go_to(viewer, text)[0] == {}
        assert shown[-1].startswith("Could not go to UTC\n")
        assert message in shown[-1]
    assert len(shown) == 3

    # SJI 1400 as time master goes to the frame nearest the typed time, here the later one, and the raster follows
    menu_action(sji_viewer, "Time master").trigger()
    qtbot.wait(20)
    exposure = nearest_frame(raster, frames[30])
    assert exposure is not None
    assert go_to(sji_viewer, utc(frames[30] - np.timedelta64(60, "s")))[0] == {
        "sji0": (30, None, None),
        "point": (label, (exposure, slit, None)),
        "spectrogram": (exposure, None, None),
    }
    assert "time master" in readout(sji_viewer)
    # and typed in the spectrogram, the slit-jaw image goes, from its time, and the raster follows it
    frame = expected_nearest(times[10], frames)
    exposure = nearest_frame(raster, frames[frame])
    assert go_to(viewers["spectrogram"], utc(times[10])) == (
        {
            "sji0": (frame, None, None),
            "point": (label, (exposure, slit, None)),
            "spectrogram": (exposure, None, None),
        },
        [utc(frames[30])],
    )


def test_go_to_utc_on_a_stack_takes_the_scan_at_the_points_step(bare_app, qtbot, monkeypatch, scans):
    _, stack = scans
    _, step, slit, wavelength = expected_start(stack)
    times = stack[stack.id["Time"]][:, :, 0, 0]
    sji = slit_jaw(times[0, step] + np.arange(40) * (times[-1, step] - times[0, step]) / 39, stack)
    viewers = quicklook(bare_app, [stack, sji])
    [sji_viewer] = viewers["sji"]
    when = times[1, step] + (times[2, step] - times[1, step]) * 0.45
    assert expected_nearest(when, times[:, 0]) == 2  # at the first step, another scan
    # typed in the map or in the slit-jaw viewer, the stack goes to the scan nearest at the point's step, from the
    # master's time, and the slit-jaw image follows it
    for viewer, when, scan, shown in ((viewers["map"], when, 1, 0), (sji_viewer, times[0, step], 0, 1)):
        opened = type_in_dialog(monkeypatch, utc(when))
        assert changes(bare_app, qtbot, viewers, menu_action(viewer, "Go to UTC…").trigger) == {
            "point": (stack.label, (scan, step, slit, None)),
            "map": (scan, None, None, wavelength),
            "spectrogram": (scan, step, None, None),
            "sji0": (nearest_frame(sji, times[scan, step]), None, None),
        }
        assert opened == [utc(times[shown, step])]
    # without a point too: the scan sliders move, and the time stays at the step the point left
    menu_action(viewers["map"], "Clear point").trigger()
    opened = type_in_dialog(monkeypatch, utc(times[2, step]))
    assert changes(bare_app, qtbot, viewers, menu_action(sji_viewer, "Go to UTC…").trigger) == {
        "map": (2, None, None, wavelength),
        "spectrogram": (2, step, None, None),
        "sji0": (nearest_frame(sji, times[2, step]), None, None),
    }
    assert opened == [utc(times[0, step])]
    assert f"time master, step {step}" in readout(viewers["spectrogram"])


def test_go_to_utc_on_a_scanning_raster_moves_its_step(bare_app, qtbot, monkeypatch, scans):
    scan, _ = scans
    times = scan[scan.id["Time"]][:, 0, 0]
    frames = times[0] + (np.arange(24) - 2) * ((times[-1] - times[0]) / 19)  # about three per step
    viewers = quicklook(bare_app, [scan, slit_jaw(frames, scan)])
    [sji_viewer] = viewers["sji"]
    _, slit, _ = expected_start(scan)

    def go_to(when):
        type_in_dialog(monkeypatch, utc(when))
        return changes(bare_app, qtbot, viewers, lambda: menu_action(sji_viewer, "Go to UTC…").trigger())

    # typed in the slit-jaw viewer, the raster goes to the step nearest the typed time, which moves the point, and
    # the slit-jaw image follows it
    assert go_to(times[2]) == {
        "point": (scan.label, (2, slit, None)),
        "spectrogram": (2, None, None),
        "sji0": (expected_nearest(times[2], frames), None, None),
    }
    # without a point too, though its step slider no longer moves the time
    menu_action(viewers["map"], "Clear point").trigger()
    assert go_to(times[6]) == {"spectrogram": (6, None, None), "sji0": (expected_nearest(times[6], frames), None, None)}
    assert "time master, step 6" in readout(viewers["spectrogram"])


def test_go_to_utc_without_an_exposure_slider(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    times = raster[raster.id["Time"]][:, 0, 0]
    # the map and the wavelength panel show the exposures: without the spectrogram and the point, no slider holds
    # the raster's exposure, which goes all the same, and the slit-jaw image follows it
    viewers["spectrogram"].close(warn=False)
    menu_action(viewers["map"], "Clear point").trigger()
    type_in_dialog(monkeypatch, utc(times[100]))
    assert changes(bare_app, qtbot, viewers, menu_action(sji_viewer, "Go to UTC…").trigger) == {
        "sji0": (nearest_frame(sji, times[100]), None, None)
    }
    assert "time master, step 100" in readout(viewers["map"])


def play(qtbot, viewer, button, frames):
    """Press the play ``button`` of the viewer's first slider with a 1 ms timer; return at least ``frames`` shown."""
    slider = viewer.options_widget().slice_helper._sliders[0]
    shown = []

    def record(slices):
        shown.append(slices[0])

    viewer.state.add_callback("slices", record)
    getattr(slider, button).click()
    slider._play_timer.setInterval(1)
    qtbot.waitUntil(lambda: len(shown) >= frames)
    slider.button_stop.click()
    viewer.state.remove_callback("slices", record)
    return shown


def test_a_loop_plays_only_its_frames(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    menu_action(sji_viewer, "Time master").trigger()
    sji_viewer.state.slices = (0, 0, 0)
    opened = type_in_dialog(monkeypatch, "20 25")
    menu_action(sji_viewer, "Loop…").trigger()
    assert opened == [("0 61", 1, False)]  # the whole range, every frame, round
    # forwards from frame 0: from the first, round and round; then backwards from where it stopped
    shown = play(qtbot, sji_viewer, "button_forw", 14)
    assert shown == [20 + i % 6 for i in range(len(shown))]
    back = play(qtbot, sji_viewer, "button_back", 8)
    assert back == [20 + (shown[-1] - 21 - i) % 6 for i in range(len(back))]
    # the raster followed
    frames = sji[sji.id["Time"]][:, 0, 0]
    assert check_follower(bare_app, qtbot, frames[back[-1]], raster, viewers["spectrogram"])
    # a range out of order, past the last frame or of one index keeps the loop, which the next dialog opens on
    shown = refusals(monkeypatch)
    for text in ("25 20", "20 62", "20"):
        opened = type_in_dialog(monkeypatch, text)
        menu_action(sji_viewer, "Loop…").trigger()
        assert opened == [("20 25", 1, False)]
        assert shown[-1] == (
            f"Could not loop\n'{text}' is not two indices from 0 to 61, the first not after the last, or ±N."
        )
    # the whole range plays as glue does
    type_in_dialog(monkeypatch, "0 61")
    menu_action(sji_viewer, "Loop…").trigger()
    sji_viewer.state.slices = (59, 0, 0)
    assert play(qtbot, sji_viewer, "button_forw", 4)[:4] == [60, 61, 0, 1]


def test_a_loop_plays_every_nth_frame_round_or_back_and_forth(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    menu_action(sji_viewer, "Time master").trigger()
    sji_viewer.state.slices = (30, 0, 0)
    # every 3rd of the 5 frames either side of frame 30: on from 30, then round from 25
    type_in_dialog(monkeypatch, "±5", every=3)
    menu_action(sji_viewer, "Loop…").trigger()
    assert play(qtbot, sji_viewer, "button_forw", 9)[:9] == [33, 25, 28, 31, 34, 25, 28, 31, 34]
    # bouncing from outside the loop: from 25 forwards, back from the last frame played, 34, and on again from 25,
    # each played once; the raster follows
    opened = type_in_dialog(monkeypatch, "25 35", tick=True, every=3)
    menu_action(sji_viewer, "Loop…").trigger()
    assert opened == [("25 35", 3, False)]
    sji_viewer.state.slices = (40, 0, 0)
    shown = play(qtbot, sji_viewer, "button_forw", 10)
    assert shown[:10] == [25, 28, 31, 34, 31, 28, 25, 28, 31, 34]
    frames = sji[sji.id["Time"]][:, 0, 0]
    assert check_follower(bare_app, qtbot, frames[shown[-1]], raster, viewers["spectrogram"])
    # +- for ±, cut to the first frame; the dialog opens on the loop, which a refusal keeps
    opened = type_in_dialog(monkeypatch, "+-5")
    sji_viewer.state.slices = (2, 0, 0)
    menu_action(sji_viewer, "Loop…").trigger()
    assert opened == [("25 35", 3, True)]
    shown = refusals(monkeypatch)
    opened = type_in_dialog(monkeypatch, "±-1")
    menu_action(sji_viewer, "Loop…").trigger()
    assert opened == [("0 7", 1, False)]
    assert shown == ["Could not loop\n'±-1' is not two indices from 0 to 61, the first not after the last, or ±N."]


def test_closing_the_master_stops_its_playback(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    menu_action(sji_viewer, "Time master").trigger()
    slider = sji_viewer.options_widget().slice_helper._sliders[0]
    shown = []
    sji_viewer.state.add_callback("slices", lambda slices: shown.append(slices[0]))
    slider.button_forw.click()
    slider._play_timer.setInterval(1)
    qtbot.waitUntil(lambda: len(shown) >= 3)
    # a close cancelled at glue-qt's confirmation leaves it playing
    sji_viewer._warn_close = True
    monkeypatch.setattr(sji_viewer, "_confirm_close", lambda: False)
    assert not sji_viewer._mdi_wrapper.close()
    assert slider._play_timer.isActive()
    sji_viewer.close(warn=False)
    assert not slider._play_timer.isActive()
    played = len(shown)
    qtbot.wait(20)
    assert len(shown) == played


def test_frames_and_movies_save_what_save_plot_saves(bare_app, qtbot, monkeypatch, tmp_path, irispy_test_files):
    from matplotlib import animation, rcParams
    from matplotlib.image import imread
    from PIL import Image

    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    menu_action(sji_viewer, "Time master").trigger()
    sji_viewer.state.slices = (20, 0, 0)
    sji_viewer.toolbar.actions["solar:per_frame_limits"].trigger()
    [layer] = [layer for layer in sji_viewer.state.layers if layer.layer is sji]
    button = sji_viewer.toolbar.widgetForAction(sji_viewer.toolbar.actions["save"])
    entries = {action.text(): action for action in button.menu().actions()}
    monkeypatch.setitem(rcParams, "savefig.directory", str(tmp_path))  # 'Save plot to file' sets it
    cancel_at = []

    def cancel(slices):
        if slices[0] in cancel_at:
            sji_viewer.findChildren(QtWidgets.QProgressDialog)[-1].cancel()

    sji_viewer.state.add_callback("slices", cancel)

    def save(entry, name, typed="0 9", tick=False):
        type_in_dialog(monkeypatch, typed, tick)
        monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *args: (str(tmp_path / name), ""))
        entries[entry].trigger()

    # frames 0 to 9, with the raster following
    QtWidgets.QApplication.processEvents()  # the time sync of frame 20
    times = sji[sji.id["Time"]][:, 0, 0]
    exposures = []
    viewers["spectrogram"].state.add_callback("slices", lambda slices: exposures.append(slices[0]))
    slider = sji_viewer.options_widget().slice_helper._sliders[0]
    slider.button_forw.click()  # playing, which the export stops
    slider._play_timer.setInterval(1)
    save("Save frames or movie…", "sji.png")
    assert not slider._play_timer.isActive()
    assert exposures == [nearest_frame(raster, when) for when in times[:10]]
    # the viewer returns to its frame and per-frame limits
    assert (sji_viewer.state.slices, layer.stretch_global) == ((20, 0, 0), False)
    # each at the whole cube's limits, as 'Save plot to file' saves it then
    layer.stretch_global = True
    for frame in range(10):
        sji_viewer.state.slices = (frame, 0, 0)
        QtWidgets.QApplication.processEvents()  # the time sync, which moves the raster point's cross
        save("Save plot to file", "plot.png")
        np.testing.assert_array_equal(imread(tmp_path / f"sji_{frame:04d}.png"), imread(tmp_path / "plot.png"))
    assert sorted(path.name for path in tmp_path.glob("sji_*.png")) == [f"sji_{frame:04d}.png" for frame in range(10)]
    # ticked, each frame has its time to 0.01 s, drawn during the export only
    figure, drawn = sji_viewer.figure, []
    savefig = figure.savefig
    monkeypatch.setattr(
        figure, "savefig", lambda *args: drawn.append([text.get_text() for text in figure.texts]) or savefig(*args)
    )
    save("Save frames or movie…", "utc.png", tick=True)
    assert drawn == [[f"{utc(when)[:-1]} UTC"] for when in times[:10]]
    assert (figure.texts, sji_viewer.state.slices) == ([], (9, 0, 0))
    monkeypatch.setattr(figure, "savefig", savefig)
    save("Save frames or movie…", "sji.gif")
    with Image.open(tmp_path / "sji.gif") as gif:
        assert gif.n_frames == 10
    # Cancel keeps the frames saved, the one being saved too
    cancel_at.append(3)
    save("Save frames or movie…", "cut.png")
    assert sorted(path.name for path in tmp_path.glob("cut_*.png")) == [f"cut_{frame:04d}.png" for frame in range(4)]
    save("Save frames or movie…", "cut.gif")
    with Image.open(tmp_path / "cut.gif") as gif:
        assert gif.n_frames == 4
    assert sji_viewer.state.slices == (9, 0, 0)
    # an MP4 where ffmpeg is installed, which CI may lack, of an odd frame height, which matplotlib evens out: the
    # viewer keeps its size and zoom
    if animation.writers.is_available("ffmpeg"):
        bare_app.show()  # for resizes to reach the canvas
        canvas, state = sji_viewer.figure.canvas, sji_viewer.state
        for height in (301, 302):  # one gives the canvas an odd height, whatever the viewer's toolbar and status bar
            sji_viewer.viewer_size = (400, height)
            QtWidgets.QApplication.processEvents()
            if canvas.get_width_height(physical=True)[1] % 2:
                break
        before = canvas.get_width_height(), (state.x_min, state.x_max, state.y_min, state.y_max)
        save("Save frames or movie…", "sji.mp4", "0 2")
        assert (tmp_path / "sji.mp4").stat().st_size > 0
        assert (canvas.get_width_height(), (state.x_min, state.x_max, state.y_min, state.y_max)) == before


def test_what_the_keys_move_on_a_sit_and_stare(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    label = raster.label
    times, frames = (data[data.id["Time"]][:, 0, 0] for data in (raster, sji))
    start, slit, wavelength = expected_start(raster)
    last, waves = raster.shape[0] - 1, raster.shape[2]
    f1400 = [nearest_frame(sji, when) for when in times]

    def key(viewer, pressed):
        return changes(bare_app, qtbot, viewers, lambda: press(viewer, pressed))

    # F and D move the raster master's exposure, pressed on any panel, the spectrum's too: the point and the slit-jaw
    # image follow, as for the exposure slider
    assert f1400[start] is None
    assert key(viewers["map"], Qt.Key_F) == {
        "point": (label, (start + 1, slit, None)),
        "spectrogram": (start + 1, None, None),
        "sji0": (f1400[start + 1], None, None),
    }
    assert key(sji_viewer, Qt.Key_D) == {"point": (label, (start, slit, None)), "spectrogram": (start, None, None)}
    assert key(viewers["spectrum"], Qt.Key_D) == {
        "point": (label, (start - 1, slit, None)),
        "spectrogram": (start - 1, None, None),
        "sji0": (f1400[start - 1], None, None),
    }
    # round from either end
    slide(viewers["spectrogram"], 0, last)
    for pressed, exposure in ((Qt.Key_F, 0), (Qt.Key_D, last)):
        assert key(viewers["wavelength"], pressed) == {
            "point": (label, (exposure, slit, None)),
            "spectrogram": (exposure, None, None),
            "sji0": (f1400[exposure], None, None),
        }
    # A and S step the map's wavelength only, pressed on any panel, round from either end
    for viewer, pressed, index in (
        (viewers["map"], Qt.Key_S, wavelength + 1),
        (viewers["spectrogram"], Qt.Key_A, wavelength),
        (sji_viewer, Qt.Key_A, wavelength - 1),
        (viewers["spectrum"], Qt.Key_S, wavelength),
    ):
        assert key(viewer, pressed) == {"map": (None, None, index)}
    slide(viewers["map"], 2, 0)
    assert key(viewers["wavelength"], Qt.Key_A) == {"map": (None, None, waves - 1)}
    assert key(viewers["wavelength"], Qt.Key_S) == {"map": (None, None, 0)}
    # under a slit-jaw master F and D move its frame, round from either end, and the raster follows
    menu_action(sji_viewer, "Time master").trigger()
    qtbot.wait(20)
    for pressed, frame in ((Qt.Key_F, 0), (Qt.Key_D, sji.shape[0] - 1)):
        exposure = expected_nearest(frames[frame], times)
        assert key(viewers["map"], pressed) == {
            "sji0": (frame, None, None),
            "point": (label, (exposure, slit, None)),
            "spectrogram": (exposure, None, None),
        }


def test_what_the_keys_move_on_a_scanning_raster_and_a_stack(bare_app, qtbot, scans):
    scan, stack = scans
    times = scan[scan.id["Time"]][:, 0, 0]
    frames = times[0] + (np.arange(24) - 2) * ((times[-1] - times[0]) / 19)  # about three per step
    viewers = first = quicklook(bare_app, [scan, slit_jaw(frames, scan)])
    step, slit, _ = expected_start(scan)
    # a scanning raster's step, which moves the point, and the slit-jaw image follows it
    assert changes(bare_app, qtbot, viewers, lambda: press(viewers["map"], Qt.Key_F)) == {
        "point": (scan.label, (step + 1, slit, None)),
        "spectrogram": (step + 1, None, None),
        "sji0": (expected_nearest(times[step + 1], frames), None, None),
    }
    # a stack's scan, at the point's step, round from the first to the last
    scan_times = stack[stack.id["Time"]][:, :, 0, 0]
    _, step, slit, wavelength = expected_start(stack)
    last = stack.shape[0] - 1
    frames = np.sort(scan_times, axis=None)
    viewers = quicklook(bare_app, [stack, slit_jaw(frames, stack)])
    assert changes(bare_app, qtbot, viewers, lambda: press(viewers["spectrogram"], Qt.Key_D)) == {
        "point": (stack.label, (last, step, slit, None)),
        "map": (last, None, None, wavelength),
        "spectrogram": (last, step, None, None),
        "sji0": (expected_nearest(scan_times[last, step], frames), None, None),
    }
    # A and S in a quicklook's tab step its own map's wavelength, not an earlier quicklook's; outside a quicklook's tab,
    # the viewer's own only
    first_map = first["map"].state.slices
    assert changes(bare_app, qtbot, viewers, lambda: press(viewers["spectrogram"], Qt.Key_S)) == {
        "map": (last, None, None, wavelength + 1)
    }
    bare_app.new_tab()
    plain = image(bare_app, stack, 1, 2)
    qtbot.wait(20)
    index = plain.state.slices[3]
    assert changes(bare_app, qtbot, viewers, lambda: press(plain, Qt.Key_A)) == {}
    assert plain.state.slices[3] == (index - 1) % stack.shape[3]
    assert first["map"].state.slices == first_map


def test_space_plays_the_time_master_round_its_loop(bare_app, qtbot, monkeypatch, irispy_test_files, scans):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]

    def space(viewer, played, frames):
        """Press Space on ``viewer``, see ``frames`` of the ``played`` viewer's first slider, and press Space again."""
        slider = played.options_widget().slice_helper._sliders[0]
        shown = []

        def record(slices):
            shown.append(slices[0])

        played.state.add_callback("slices", record)
        press(viewer, Qt.Key_Space)
        assert slider._play_timer.isActive()
        slider._play_timer.setInterval(1)
        qtbot.waitUntil(lambda: len(shown) >= frames)
        press(viewer, Qt.Key_Space)
        played.state.remove_callback("slices", record)
        assert not slider._play_timer.isActive()
        return shown

    # pressed on the map, which shows the exposures, Space plays the raster master's exposure slider, round its loop
    type_in_dialog(monkeypatch, "150 153")
    menu_action(viewers["spectrogram"], "Loop…").trigger()
    shown = space(viewers["map"], viewers["spectrogram"], 6)
    assert shown == [150 + i % 4 for i in range(len(shown))]
    # under a slit-jaw master, its frames, pressed on the spectrum panel; the raster follows
    menu_action(sji_viewer, "Time master").trigger()
    qtbot.wait(20)
    frame = sji_viewer.state.slices[0]
    shown = space(viewers["spectrum"], sji_viewer, 3)
    assert shown == list(range(frame + 1, frame + 1 + len(shown)))
    frames = sji[sji.id["Time"]][:, 0, 0]
    assert check_follower(bare_app, qtbot, frames[shown[-1]], raster, viewers["spectrogram"])
    # and pressed on the spectrogram, whose own exposure slider has the loop
    frame = sji_viewer.state.slices[0]
    shown = space(viewers["spectrogram"], sji_viewer, 3)
    assert shown == [(frame + 1 + i) % sji.shape[0] for i in range(len(shown))]
    # a stack's map and spectrogram both have its scan slider: pressed on the map, Space plays the one with a loop
    viewers = quicklook(bare_app, [scans[1]])
    type_in_dialog(monkeypatch, "1 2")
    menu_action(viewers["spectrogram"], "Loop…").trigger()
    slide(viewers["map"], 0, 2)  # from outside the loop, played on from its first scan
    qtbot.wait(20)
    shown = space(viewers["map"], viewers["spectrogram"], 4)
    assert shown == [1 + i % 2 for i in range(len(shown))]


def test_backspace_closes_a_quicklook_raster_panel(bare_app, irispy_test_files):
    viewers = quicklook(bare_app, list(sit_and_stare(irispy_test_files)))
    press(viewers["wavelength"], Qt.Key_Backspace)  # glue-qt's own, which asks first outside tests
    assert [viewers[role]._closed for role in RASTER_PANELS] == [False, False, True]
    assert viewers["wavelength"] not in coordinator(bare_app.data_collection)._viewers


def test_what_a_region_moves(bare_app, qtbot, scans, irispy_test_files):
    scan, stack = scans
    for data, sji in (
        (scan, slit_jaw(scan[scan.id["Time"]][:, 0, 0], scan)),
        (stack, slit_jaw(np.sort(stack[stack.id["Time"]][:, :, 0, 0], axis=None), stack)),
        sit_and_stare(irispy_test_files),
    ):
        viewers = quicklook(bare_app, [data, sji])
        [point] = bare_app.session.edit_subset_mode.edit_subset
        # a region on any panel, raster or slit-jaw, is a new subset: the point, still the edit subset, and every
        # slider stay
        roi = RectangularROI(1.5, 3.5, 5.5, 9.5)
        for viewer in [viewers[role] for role in RASTER_PANELS] + viewers["sji"]:
            groups = len(bare_app.data_collection.subset_groups)
            assert changes(bare_app, qtbot, viewers, lambda viewer=viewer: viewer.apply_roi(roi)) == {}
            assert len(bare_app.data_collection.subset_groups) == groups + 1
            assert bare_app.session.edit_subset_mode.edit_subset == [point]


def test_regions_leave_a_slit_jaw_click_the_point_window_and_the_time_controls(
    bare_app, qtbot, monkeypatch, tmp_path, irispy_test_files
):
    path = repointed(tmp_path / SNS.format("raster_t000_r00000"), irispy_test_files, step=0.3)
    [raster] = raster_data([path], ["Si IV 1403"])
    _, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    window = point_window(bare_app)
    collection, mode = bare_app.data_collection, bare_app.session.edit_subset_mode
    [point] = mode.edit_subset
    times = raster[raster.id["Time"]][:, 0, 0]
    type_in_dialog(monkeypatch, "150 153")
    menu_action(viewers["spectrogram"], "Loop…").trigger()
    qtbot.wait(20)
    # a slit-jaw click moves the point to the raster there and keeps the frame clicked (NO MATCH); then a click outside
    # the raster leaves the point
    frame = sji_viewer.state.slices[0]
    (x, y), (step, slit) = clicked(sji_viewer, raster, 30, 25)
    select_point(sji_viewer, x, y)
    select_point(sji_viewer, *np.round(past(raster, sji, (0, slit), (20, slit), frame)))
    settle(qtbot, window)
    text, before = readout(sji_viewer), rows(window)
    assert "NO MATCH" in text
    assert "outside raster FOV" in text
    assert before[0][1] == f"step {step}, slit {slit}, λ {viewers['map'].state.slices[2]}"
    # a region on each panel, the slit-jaw image clicked too, moves nothing: the point, the frame clicked, the readout
    # and the Point window, which gives the point, not a region, stay
    roi = RectangularROI(20.5, 40.5, 10.5, 30.5)
    for viewer in [viewers[role] for role in RASTER_PANELS] + [sji_viewer]:
        assert changes(bare_app, qtbot, viewers, lambda viewer=viewer: viewer.apply_roi(roi)) == {}
        settle(qtbot, window)
        assert (readout(sji_viewer), rows(window)) == (text, before)
    regions = collection.subset_groups[1:]
    drawn = [group.subset_state for group in regions]
    assert len(regions) == 4
    assert mode.edit_subset == [point]
    # one Undo takes back the last region only
    assert changes(bare_app, qtbot, viewers, bare_app.session.command_stack.undo) == {}
    assert collection.subset_groups == (point, *regions[:3])
    assert readout(sji_viewer) == text
    # Go to UTC moves the raster master, the point and the slit-jaw image as without regions, and leaves them
    assert nearest_frame(sji, times[150]) != frame
    type_in_dialog(monkeypatch, utc(times[150]))
    assert changes(bare_app, qtbot, viewers, menu_action(sji_viewer, "Go to UTC…").trigger) == {
        "point": (raster.label, (150, slit, None)),
        "spectrogram": (150, None, None),
        "sji0": (nearest_frame(sji, times[150]), None, None),
    }
    assert [group.subset_state for group in collection.subset_groups[1:]] == drawn[:3]
    # and the loop set before the regions still plays only its steps
    shown = play(qtbot, viewers["spectrogram"], "button_forw", 6)
    assert shown == [150 + (1 + i) % 4 for i in range(len(shown))]
    assert [group.subset_state for group in collection.subset_groups[1:]] == drawn[:3]


@pytest.mark.remote_data
def test_what_moves_on_a_negative_step_raster(bare_app, qtbot, irispy_data):
    # 3400109360: STEPS_AV -0.998, so Time runs backwards along the step axis
    [scan] = raster_data(irispy_data("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz"))
    times = scan[scan.id["Time"]][:, 0, 0]
    first, last = np.sort(times)[[0, -1]]
    frames = first + (np.arange(130) - 3) * ((last - first) / 125)  # about two per step, more before than after
    sji = slit_jaw(frames, scan)
    viewers = quicklook(bare_app, [scan, sji])
    [sji_viewer] = viewers["sji"]
    check_panels(bare_app, viewers, scan, {"map": (0, 1), "spectrogram": (2, 1), "wavelength": (2, 0)})
    label = scan.label

    def frame(step):
        return expected_nearest(times[step], frames)

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    # each step its own frame, and a higher step an earlier one
    assert (np.diff([frame(step) for step in range(scan.shape[0])]) < 0).all()
    # a map click moves the point; the spectrogram to its step, the λ panel to its slit, the SJI to its time
    assert event(lambda: select_point(viewers["map"], 2, 100)) == {
        "point": (label, (2, 100, None)),
        "spectrogram": (2, None, None),
        "wavelength": (None, 100, None),
        "sji0": (frame(2), None, None),
    }
    # a spectrogram click (wavelength 50, slit 400) keeps the step, so the time
    assert event(lambda: select_point(viewers["spectrogram"], 50, 400)) == {
        "point": (label, (2, 400, None)),
        "wavelength": (None, 400, None),
        "map": (None, None, 50),
    }
    # a λ–step click (wavelength 90, step 61) keeps the slit; the later step is earlier, so is its frame
    assert event(lambda: select_point(viewers["wavelength"], 90, 61)) == {
        "point": (label, (61, 400, None)),
        "spectrogram": (61, None, None),
        "map": (None, None, 90),
        "sji0": (frame(61), None, None),
    }
    assert event(lambda: slide(viewers["map"], 2, 130)) == {"map": (None, None, 130)}
    # a slit-jaw master moves nothing on a single scan, whose time is the point's step, even to another step's frame
    assert event(lambda: menu_action(sji_viewer, "Time master").trigger()) == {}
    assert "time master" in readout(sji_viewer)
    assert event(lambda: slide(sji_viewer, 0, frame(2))) == {"sji0": (frame(2), None, None)}
    # and a step moved by hand moves the point, not the master's time
    assert event(lambda: slide(viewers["spectrogram"], 0, 40)) == {
        "point": (label, (40, 400, None)),
        "spectrogram": (40, None, None),
    }
    # the steps are places on the Sun, not a sit-and-stare's exposures: glue's own labels, the scanning titles
    longitude = scan.world_component_ids[0].label
    assert viewers["map"].state.x_axislabel == viewers["wavelength"].state.y_axislabel == longitude
    assert [viewers[role].state.title.split()[-1] for role in ("map", "wavelength")] == ["map", "λ–step"]


def clicked(viewer, raster, step, slit):
    """
    The slit-jaw pixel a Pixel click takes nearest raster pixel ``step, slit`` (at a stack's scan 0) in the frame the
    viewer shows, and the raster pixel `sji_to_raster` finds there.
    """
    sji, frame = viewer.state.reference_data, viewer.state.slices[0]
    x, y = np.round(raster_point_on_sji(raster, sji, step, slit, frame))
    return (x, y), sji_to_raster(sji, frame, x, y, raster)


@pytest.mark.parametrize("arcsec", [0.3, -0.3])  # per step: a scanning raster, and one of negative step (D10)
def test_what_a_slit_jaw_click_moves_on_a_scanning_raster(bare_app, qtbot, tmp_path, irispy_test_files, arcsec):
    path = repointed(tmp_path / SNS.format("raster_t000_r00000"), irispy_test_files, step=arcsec)
    [raster] = raster_data([path], ["Si IV 1403"])
    _, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    label = raster.label
    times = raster[raster.id["Time"]][:, 0, 0]

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    qtbot.wait(20)
    frame = sji_viewer.state.slices[0]
    # a click moves the point to the step and slit there, placed with the frame shown: the spectrogram to its step, the
    # λ panel to its slit; the frame stays, though taken at another step's time (so NO MATCH), and marks the point
    (x, y), (step, slit) = clicked(sji_viewer, raster, 30, 25)
    assert nearest_frame(sji, times[step]) not in (frame, None)
    assert event(lambda: select_point(sji_viewer, x, y)) == {
        "point": (label, (step, slit, None)),
        "spectrogram": (step, None, None),
        "wavelength": (None, slit, None),
    }
    assert "NO MATCH" in readout(sji_viewer)
    assert "outside raster FOV" not in readout(sji_viewer)
    assert overlays(sji_viewer)[1] == pytest.approx(raster_point_on_sji(raster, sji, step, slit, frame))
    # a click 20 steps before the first leaves the point and the panels as they were, and the readout says so
    outside = np.round(past(raster, sji, (0, slit), (20, slit), frame))
    assert event(lambda: select_point(sji_viewer, *outside)) == {}
    assert "outside raster FOV" in readout(sji_viewer)
    # until the point moves, here by the step slider, which takes the slit-jaw image to the time of the point's step
    assert event(lambda: slide(viewers["spectrogram"], 0, 150)) == {
        "point": (label, (150, slit, None)),
        "spectrogram": (150, None, None),
        "sji0": (nearest_frame(sji, times[150]), None, None),
    }
    assert "outside raster FOV" not in readout(sji_viewer)
    # a slit-jaw image moved back by hand keeps its frame through a click outside the raster
    assert event(lambda: slide(sji_viewer, 0, frame)) == {"sji0": (frame, None, None)}
    assert event(lambda: select_point(sji_viewer, *outside)) == {}
    assert "outside raster FOV" in readout(sji_viewer)


def test_what_a_slit_jaw_click_moves_on_a_stack(bare_app, qtbot, tmp_path, irispy_test_files):
    path = repointed(tmp_path / SNS.format("raster_t000_r00000"), irispy_test_files, step=0.3)
    [stack] = raster_data([path, path], ["Si IV 1403"], stack=True)
    times = stack[stack.id["Time"]].copy()
    times[0] -= times.max() - times.min()  # scan 0 before the slit-jaw image, scan 1 during it
    stack.update_components({stack.id["Time"]: times})
    _, sji = sit_and_stare(irispy_test_files)
    # the slit-jaw image first: glue tells the stack's subset of the click after the coordinator has replaced it
    viewers = quicklook(bare_app, [sji, stack])
    [sji_viewer] = viewers["sji"]
    qtbot.wait(20)
    assert sji_viewer.state.slices[0] == 0  # NO MATCH with scan 0
    # a click moves the point to the step and slit there and to the scan nearest the frame's time at that step: the map
    # to the scan, the spectrogram to its scan and step, the λ–scan panel to its step and slit; the frame stays
    (x, y), (scan, step, slit) = clicked(sji_viewer, stack, 30, 25)
    assert scan == 1
    assert changes(bare_app, qtbot, viewers, lambda: select_point(sji_viewer, x, y)) == {
        "point": (stack.label, (1, step, slit, None)),
        "map": (1, None, None, expected_start(stack)[-1]),
        "spectrogram": (1, step, None, None),
        "wavelength": (None, step, slit, None),
    }


def test_what_a_slit_jaw_click_moves_on_a_sit_and_stare(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    sjis = [sji, image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_2796_t000")))]
    viewers = quicklook(bare_app, [raster, *sjis])
    label = raster.label
    times = raster[raster.id["Time"]][:, 0, 0]

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    qtbot.wait(20)
    # SJI 1400 moved by hand, then clicked on the slit: the point moves to the exposure nearest the frame's time and the
    # slit row there, the spectrogram to its exposure, the λ–time panel to its slit, and SJI 2796 follows the time
    assert event(lambda: slide(viewers["sji"][0], 0, 20)) == {"sji0": (20, None, None)}
    exposure = expected_nearest(sji[sji.id["Time"]][20, 0, 0], times)
    (x, y), index = clicked(viewers["sji"][0], raster, exposure, 30)
    assert index == (exposure, 30)
    assert event(lambda: select_point(viewers["sji"][0], x, y)) == {
        "point": (label, (exposure, 30, None)),
        "spectrogram": (exposure, None, None),
        "wavelength": (None, 30, None),
        "sji1": (nearest_frame(sjis[1], times[exposure]), None, None),
    }
    # beside the slit, however far: the row level with the click
    assert event(lambda: select_point(viewers["sji"][0], x - 5, y - 5)) == {
        "point": (label, (exposure, 25, None)),
        "wavelength": (None, 25, None),
    }
    # under a slit-jaw time master, a click on another moves the point's slit row, while the master rules: the
    # exposure snaps back to the master's, and the image clicked follows the master too
    assert event(lambda: menu_action(viewers["sji"][1], "Time master").trigger()) == {}
    assert event(lambda: slide(viewers["sji"][0], 0, 40)) == {"sji0": (40, None, None)}
    assert event(lambda: select_point(viewers["sji"][0], x, y)) == {
        "point": (label, (exposure, 30, None)),
        "wavelength": (None, 30, None),
        "sji0": (20, None, None),
    }


def test_one_undo_reverts_a_slit_jaw_click(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    undo = bare_app._actions["undo"]
    qtbot.wait(20)
    assert not undo.isEnabled()
    before = sliders(bare_app, viewers)
    updates = SubsetUpdates(bare_app.data_collection.hub)
    (x, y), index = clicked(sji_viewer, raster, 0, 30)
    select_point(sji_viewer, x, y)
    qtbot.wait(20)
    assert sliders(bare_app, viewers)["point"] == (raster.label, (*index, None))
    # one undo step, glue's, which the Pixel tool's slit-jaw point and the coordinator's raster point there share: the
    # coordinator replaces the one by the other as glue applies it, and does not answer its own assignment
    assert updates.counts == {raster.label: 2, sji.label: 2}
    assert undo.isEnabled()
    assert undo.text() == "Undo apply subset"
    undo.trigger()
    qtbot.wait(20)
    assert sliders(bare_app, viewers) == before
    assert not undo.isEnabled()


def arcsec_read_out(viewer, x, y):
    """The angles the viewer's mouse-over readout gives at pixel ``x, y``, in arcsec."""
    text = viewer.toolbar.tools["solar:cursor_readout"].describe(x, y)
    return [float(value) for value in re.findall(r'(-?\d+\.\d+)"', text)]


def test_shift_pointing_moves_the_readout_and_what_the_raster_meets(
    bare_app, qtbot, monkeypatch, tmp_path, irispy_test_files
):
    path = repointed(tmp_path / SNS.format("raster_t000_r00000"), irispy_test_files, step=0.3)
    _, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [*raster_data([path], ["Si IV 1403", "C II 1336"]), sji])
    [sji_viewer], raster = viewers["sji"], viewers["map"].state.reference_data
    [window] = [data for data in bare_app.data_collection if data not in (raster, sji)]
    collection, [point] = bare_app.data_collection, bare_app.session.edit_subset_mode.edit_subset
    overlays_toggled(bare_app, qtbot, viewers, sji_viewer)
    frame = sji_viewer.state.slices[0]
    (x, y), (step, slit) = clicked(sji_viewer, raster, 30, 25)
    select_point(sji_viewer, x, y)
    qtbot.wait(20)
    lon, lat, _ = sji.coords.pixel_to_world_values(x, y, frame)
    read_out, marker, drawn = arcsec_read_out(sji_viewer, x, y), overlays(sji_viewer)[1], slits(sji_viewer)

    # the slit-jaw image's longitude and latitude, and its readout, move by the offset, the raster's stay
    assert shift(monkeypatch, sji, collection, (2, -1)) == (0, 0)
    qtbot.wait(20)
    assert sji.coords.pixel_to_world_values(x, y, frame)[:2] == pytest.approx((lon + 2, lat - 1), abs=1e-9)
    assert arcsec_read_out(sji_viewer, x, y) == pytest.approx(np.add(read_out, (2, -1)), abs=1e-6)
    assert raster.coords.pointing_offset == window.coords.pointing_offset == (0, 0)
    # the point stays on its raster pixel, while its cross and the raster's slits move to where they now fall
    assert overlays(sji_viewer)[1] == pytest.approx(raster_point_on_sji(raster, sji, step, slit, frame))
    assert overlays(sji_viewer)[1] != pytest.approx(marker, abs=1)
    assert slits(sji_viewer) == pytest.approx(expected_slits(raster, sji), abs=0.01)
    assert slits(sji_viewer) != pytest.approx(drawn, abs=1)
    # and a click at the same pixel reaches the raster pixel at its new longitude and latitude
    types = list(raster.coords.world_axis_physical_types)
    world = list(raster.coords.pixel_to_world_values(0, 0, 0))
    world[types.index("custom:pos.helioprojective.lon")], world[types.index("custom:pos.helioprojective.lat")] = (
        lon + 2,
        lat - 1,
    )
    *moved, _ = np.round(raster.coords.world_to_pixel_values(*world)[::-1]).astype(int)
    assert moved != [step, slit]
    select_point(sji_viewer, x, y)
    qtbot.wait(20)
    assert point.subset_state.reference_data is raster
    assert [s.start for s in point.subset_state.slices[:2]] == moved
    # data made from it takes its offset
    assert regrid_on_time(sji).coords.pointing_offset == (2, -1)

    # a raster window shifts with the other windows of its file
    assert shift(monkeypatch, window, collection, (0.5, 0.25)) == (0, 0)
    assert raster.coords.pointing_offset == window.coords.pointing_offset == (0.5, 0.25)
    assert moments._dataset(window, "x").coords.pointing_offset == (0.5, 0.25)
    # the dialog opens at the offset, and 0, 0 takes it away
    assert shift(monkeypatch, sji, collection, (0, 0)) == (2, -1)
    assert sji.coords.pixel_to_world_values(x, y, frame)[:2] == (lon, lat)
    # glue says why for data without IRIS coordinates
    plain = Data(label="plain", values=np.zeros((2, 2)))
    collection.append(plain)
    with pytest.raises(ValueError, match="plain has no IRIS coordinates to shift"):
        shift_pointing_iris(plain, collection)


def follow(viewer):
    """Make Follow/lock the viewer's mouse mode."""
    viewer.toolbar.active_tool = "solar:follow_lock"


def hover(qtbot, viewer, x, y):
    """Move the mouse, no button down, to data position ``x, y`` of the viewer, and let Follow/lock's throttle run."""
    mouse(viewer, "motion_notify_event", x, y, button=None)
    qtbot.waitUntil(lambda: not viewer.toolbar.tools["solar:follow_lock"]._timer.isActive())


def click(viewer, x, y, button=1):
    """Press and release the mouse ``button`` (3 is the right one) at data position ``x, y`` of the viewer."""
    mouse(viewer, "button_press_event", x, y, button)
    mouse(viewer, "button_release_event", x, y, button)


def key(viewer, name):
    """Press the key ``name``, such as 'escape', on the viewer's image, which has the keyboard after a click there."""
    canvas = viewer.figure.canvas
    canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", canvas, name))


def test_what_moves_on_hover_and_lock(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    label = raster.label
    times = raster[raster.id["Time"]][:, 0, 0]
    f1400 = [nearest_frame(sji, when) for when in times]
    undo = bare_app._actions["undo"]

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    qtbot.wait(20)
    # Follow/lock on the map: the mouse moving over it moves the point as a Pixel click there does, with no Undo step
    assert event(lambda: follow(viewers["map"])) == {}
    assert event(lambda: hover(qtbot, viewers["map"], 78, 10)) == {
        "point": (label, (78, 10, None)),
        "spectrogram": (78, None, None),
        "wavelength": (None, 10, None),
        "sji0": (f1400[78], None, None),
    }
    np.testing.assert_array_equal(spectrum(viewers), cube(raster)[78, 10])
    assert not undo.isEnabled()
    # a left click moves the point there and locks it, in one Undo step
    assert event(lambda: click(viewers["map"], 100, 20)) == {
        "point": (label, (100, 20, None)),
        "spectrogram": (100, None, None),
        "wavelength": (None, 20, None),
        "sji0": (f1400[100], None, None),
    }
    assert undo.text() == "Undo lock point"
    # a locked point stays as the mouse moves, over any viewer in Follow/lock, and stays locked through exposure steps,
    # which move it as before
    follow(sji_viewer)
    assert event(lambda: hover(qtbot, viewers["map"], 130, 30)) == {}
    assert event(lambda: hover(qtbot, sji_viewer, 10, 20)) == {}
    for move, exposure in ((slide, 130), (type_index, 61)):
        assert event(lambda move=move, exposure=exposure: move(viewers["spectrogram"], 0, exposure)) == {
            "point": (label, (exposure, 20, None)),
            "spectrogram": (exposure, None, None),
            "sji0": (f1400[exposure], None, None),
        }
        assert event(lambda: hover(qtbot, viewers["map"], 3, 12)) == {}
    # Esc unlocks it: on a slit-jaw image the point follows the mouse to the raster pixel there, as a click there moves
    # it, and the frame stays
    assert event(lambda: key(viewers["map"], "escape")) == {}
    assert event(lambda: slide(sji_viewer, 0, 40)) == {"sji0": (40, None, None)}
    exposure = expected_nearest(sji[sji.id["Time"]][40, 0, 0], times)
    (x, y), index = clicked(sji_viewer, raster, exposure, 30)
    assert index == (exposure, 30)
    assert event(lambda: hover(qtbot, sji_viewer, x, y)) == {
        "point": (label, (exposure, 30, None)),
        "spectrogram": (exposure, None, None),
        "wavelength": (None, 30, None),
    }
    # a left click there locks it at the slit row level with the click, and a right click on any viewer unlocks it
    assert event(lambda: click(sji_viewer, x - 5, y - 5)) == {
        "point": (label, (exposure, 25, None)),
        "wavelength": (None, 25, None),
    }
    assert event(lambda: hover(qtbot, viewers["map"], 3, 12)) == {}
    assert event(lambda: click(viewers["map"], 3, 12, button=3)) == {}
    assert event(lambda: hover(qtbot, viewers["map"], 3, 12)) == {
        "point": (label, (3, 12, None)),
        "spectrogram": (3, None, None),
        "wavelength": (None, 12, None),
        "sji0": (f1400[3], None, None),
    }
    # a click locks it again; Pixel stays, and its click moves a locked point, which stays locked
    assert event(lambda: click(viewers["map"], 78, 10)) == {
        "point": (label, (78, 10, None)),
        "spectrogram": (78, None, None),
        "wavelength": (None, 10, None),
        "sji0": (f1400[78], None, None),
    }
    assert event(lambda: select_point(viewers["map"], 100, 20)) == {
        "point": (label, (100, 20, None)),
        "spectrogram": (100, None, None),
        "wavelength": (None, 20, None),
        "sji0": (f1400[100], None, None),
    }
    follow(viewers["map"])
    assert event(lambda: hover(qtbot, viewers["map"], 3, 12)) == {}
    # the mouse alone leaves a region picked to edit
    [point] = bare_app.session.edit_subset_mode.edit_subset
    region = bare_app.data_collection.new_subset_group(label="region", subset_state=raster.pixel_component_ids[1] > 5)
    bare_app.session.edit_subset_mode.edit_subset = [region]
    assert event(lambda: hover(qtbot, viewers["map"], 40, 20)) == {}
    # Clear point empties the point and leaves it locked and Follow/lock on; once unlocked, the mouse moves it again
    bare_app.session.edit_subset_mode.edit_subset = [point]
    assert event(lambda: menu_action(viewers["map"], "Clear point").trigger()) == {"point": None}
    assert event(lambda: hover(qtbot, viewers["map"], 3, 12)) == {}
    assert event(lambda: key(viewers["map"], "escape")) == {}
    assert event(lambda: hover(qtbot, viewers["map"], 3, 12)) == {
        "point": (label, (3, 12, None)),
        "spectrogram": (3, None, None),
        "wavelength": (None, 12, None),
        "sji0": (f1400[3], None, None),
    }


def test_one_undo_takes_back_a_lock_which_survives_scan_steps(bare_app, qtbot, scans):
    _, stack = scans
    viewers = quicklook(bare_app, [stack])
    label = stack.label
    wave = expected_start(stack)[-1]  # the map's wavelength
    undo, redo = bare_app._actions["undo"], bare_app._actions["redo"]

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    # the mouse over a stack's map moves the point at the map's scan, as a click does
    follow(viewers["map"])
    assert event(lambda: hover(qtbot, viewers["map"], 1, 30)) == {
        "point": (label, (0, 1, 30, None)),
        "spectrogram": (0, 1, None, None),
        "wavelength": (None, 1, 30, None),
    }
    hovered = sliders(bare_app, viewers)
    locked = {
        "point": (label, (0, 5, 40, None)),
        "spectrogram": (0, 5, None, None),
        "wavelength": (None, 5, 40, None),
    }
    assert event(lambda: click(viewers["map"], 5, 40)) == locked
    # one Undo takes the point back to where the mouse had moved it, and unlocks it
    undo.trigger()
    qtbot.wait(20)
    assert sliders(bare_app, viewers) == hovered
    assert not undo.isEnabled()
    assert event(lambda: hover(qtbot, viewers["map"], 2, 60)) == {
        "point": (label, (0, 2, 60, None)),
        "spectrogram": (0, 2, None, None),
        "wavelength": (None, 2, 60, None),
    }
    # Redo locks it again where it was clicked
    assert event(redo.trigger) == locked
    assert event(lambda: hover(qtbot, viewers["map"], 1, 30)) == {}
    # the lock survives scan steps, which move the point as before
    assert event(lambda: slide(viewers["map"], 0, 2)) == {
        "point": (label, (2, 5, 40, None)),
        "map": (2, None, None, wave),
        "spectrogram": (2, 5, None, None),
    }
    assert event(lambda: hover(qtbot, viewers["map"], 1, 30)) == {}


def test_the_point_follows_the_mouse_at_most_once_in_50_ms(bare_app, qtbot, scans):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    viewer = viewers["map"]
    [group] = bare_app.session.edit_subset_mode.edit_subset
    steps, slits = scan.shape[:2]
    follow(viewer)
    viewer.figure.canvas.draw()
    updates = SubsetUpdates(bare_app.data_collection.hub)

    def move(n):
        x, y = viewer.axes.transData.transform((n % steps, n % slits))
        canvas = viewer.figure.canvas
        canvas.callbacks.process("motion_notify_event", MouseEvent("motion_notify_event", canvas, x, y))

    # a move moves the point 50 ms later
    fired = []
    viewer.toolbar.tools["solar:follow_lock"]._timer.timeout.connect(lambda: fired.append(time.monotonic()))
    start = time.monotonic()
    move(0)
    qtbot.waitUntil(lambda: updates.counts == {scan.label: 1})
    assert fired[0] - start >= 0.045  # Qt's coarse timers may fire up to 5 % early
    # 100 moves at once: the point moves once, to the last, when the throttle runs
    updates.counts.clear()
    for n in range(100):
        move(n)
    assert updates.counts == {}
    qtbot.waitUntil(lambda: updates.counts == {scan.label: 1})
    qtbot.wait(100)
    assert updates.counts == {scan.label: 1}
    assert group.subset_state.slices[:2] == [slice(99 % steps, 99 % steps + 1), slice(99 % slits, 99 % slits + 1)]
    # 100 moves 2 ms apart: at most one move in each 50 ms
    updates.counts.clear()
    start = time.monotonic()
    for n in range(100):
        move(n)
        qtbot.wait(2)
    qtbot.wait(100)
    assert 1 < updates.counts[scan.label] <= (time.monotonic() - start) / 0.05 + 1
    # off the image, here zoomed out, or off the axes, the point stays, as after a move just before another mouse mode
    # is chosen
    viewer.state.x_min = -5
    updates.counts.clear()
    for x, y in ((-3, 50), (2, -1000)):
        hover(qtbot, viewer, x, y)
    move(1)
    viewer.toolbar.active_tool = "image:point_selection"
    qtbot.wait(100)
    assert updates.counts == {}


def test_the_mouse_over_a_stack_map_pins_its_own_scan(app, qtbot, scans):
    _, stack = scans
    app.data_collection.append(stack)
    image(app, stack, 1, 2, (2, 0, 0, 8))
    stack_map = image(app, stack, 1, 2, (1, 0, 0, 8))
    follow(stack_map)
    hover(qtbot, stack_map, 2, 40)
    point = app.data_collection.subset_groups[0].subset_state
    assert point.slices == [slice(1, 2), slice(2, 3), slice(40, 41), slice(None)]


def exposure_labels(viewer):
    """The exposure labels a viewer has, in its axes options or drawn on any side, and its overlays' coordinates."""
    state = viewer.state
    drawn = [label for side in "bltr" for label in drawn_ticks(viewer, side)]
    labels = [label for label in (state.x_axislabel, state.y_axislabel, *drawn) if label.startswith(EXPOSURES)]
    return labels, [coord for coords in viewer.axes._all_coords[1:] for coord in coords]


def test_a_scanning_raster_has_no_exposure_axis(bare_app, scans):
    scan, _ = scans
    viewers = quicklook(bare_app, [scan])
    # its steps are places on the Sun: glue's own labels and coordinates on every panel
    for role in RASTER_PANELS:
        assert exposure_labels(viewers[role]) == ([], [])
    spectrogram = viewers["spectrogram"]
    spectrogram.state.x_att_world = scan.world_component_ids[0]  # the axis combo: step
    assert spectrogram.state.x_att is scan.pixel_component_ids[0]
    assert exposure_labels(spectrogram) == ([], [])


def test_an_exposure_axis_across_midnight_gives_both_dates(bare_app, irispy_test_files):
    raster, _ = sit_and_stare(irispy_test_files)
    times = raster[raster.id["Time"]]
    late = times + (np.datetime64("2021-09-05T23:59:00") - times.min())  # one minute before midnight
    raster.update_components({raster.id["Time"]: late})
    first, last = (np.datetime_as_string(t, unit="s") for t in (late.min(), late.max()))
    assert (first[:10], last[:10]) == ("2021-09-05", "2021-09-06")
    bare_app.data_collection.append(raster)
    viewer = image(bare_app, raster, 0, 1, (0, 0, 5))
    check_exposure_axis(viewer, "x", f"{EXPOSURES}\n{first} – {last} UTC", raster.shape[0])


def test_an_exposure_axis_without_times_has_a_one_line_label(bare_app, irispy_test_files):
    raster, _ = sit_and_stare(irispy_test_files)
    raster.remove_component(raster.id["Time"])  # which also keeps it out of its observation's time sync
    bare_app.data_collection.append(raster)
    viewer = image(bare_app, raster, 0, 1, (0, 0, 5))
    check_exposure_axis(viewer, "x", EXPOSURES, raster.shape[0])


def test_the_exposure_axis_after_the_combo_hidden_axes_and_another_dataset(bare_app, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    exposures = raster.shape[0]
    times = raster[raster.id["Time"]][:, 0, 0]
    first, last = (np.datetime_as_string(t, unit="s") for t in (times[0], times[-1]))
    label = f"{EXPOSURES}\n{first} – {last[11:]} UTC"  # one day
    wavelength = viewers["wavelength"]  # exposure on y
    check_exposure_axis(wavelength, "y", label, exposures)
    # the spectrogram's axis combo to exposure: the label and exposure numbers there too
    spectrogram = viewers["spectrogram"]
    assert exposure_labels(spectrogram) == ([], [])
    spectrogram.state.x_att_world = raster.world_component_ids[0]
    check_exposure_axis(spectrogram, "x", label, exposures)

    # a slit step while the axes are hidden resets them; shown again, the label and numbers are back
    hide = wavelength.toolbar.actions["solar:hide_axes"]
    hide.trigger()
    assert not wavelength.axes.axison
    coords = wavelength.axes.coords
    wavelength.state.slices = (wavelength.state.slices[0], 5, wavelength.state.slices[2])  # the slit slider
    assert wavelength.axes.coords is not coords  # glue reset the axes
    hide.trigger()
    assert wavelength.axes.axison
    check_exposure_axis(wavelength, "y", label, exposures)

    # another dataset as the map's reference data: glue's labels and coordinates, no exposure numbers left
    raster_map = viewers["map"]
    check_exposure_axis(raster_map, "x", label, exposures)
    raster_map.add_data(sji)
    raster_map.state.reference_data = sji
    assert exposure_labels(raster_map) == ([], [])
    raster_map.state.x_att = sji.pixel_component_ids[0]  # nor on its frames, which are not a raster's exposures
    assert not raster_map.state.x_axislabel.startswith(EXPOSURES)  # not drawn: a time axis draws slowly
    assert raster_map.axes._all_coords[1:] == []
    raster_map.state.reference_data = raster  # and back, with exposure on x again
    raster_map.state.x_att = raster.pixel_component_ids[0]
    check_exposure_axis(raster_map, "x", label, exposures)


# The Point window


def point_window(app, tab=None):
    """The Point window of the quicklook in tab ``tab``, the current one by default."""
    [window] = [sub.widget() for sub in app.tab(tab).subWindowList() if isinstance(sub.widget(), QtWidgets.QTableView)]
    return window


def settle(qtbot, *windows):
    """Let Qt run the coordinator's deferred work, then the windows' refresh, which follows it."""
    qtbot.wait(20)
    qtbot.waitUntil(lambda: not any(window._timer.isActive() for window in windows))


def rows(window):
    columns = range(window.columnCount())
    return [[window.item(row, column).text() for column in columns] for row in range(window.rowCount())]


def read_at(data, names, pixel, sync):
    """The Point window's row for ``data`` at ``pixel``, whose axes are ``names``, as read from the data."""
    world = dict(zip(data.coords.world_axis_physical_types, data.coords.pixel_to_world_values(*pixel[::-1])))
    # longitude and latitude in arcsec, then any wavelength in Angstrom, as IRIS data give them; time has its own column
    position = [f'{world[f"custom:pos.helioprojective.{name}"]:.2f}"' for name in ("lon", "lat")]
    position += [f"{world['em.wl']:.3f} Å"] if "em.wl" in world else []
    return [
        data.label,
        ", ".join(f"{name} {index}" for name, index in zip(names, pixel)),
        " ".join(position),
        f"{np.datetime_as_string(data[data.id['Time'], pixel], unit='ms')} UTC",
        f"{data[data.id['Exposure time'], pixel]:.4g} s",
        f"{data[data.id[data.label], pixel]:.6g}",
        sync,
    ]


def unpointed(data, sync):
    return [data.label, "", "", "", "", "", sync]


@pytest.mark.parametrize("stacked", [False, True], ids=["scan", "stack"])
def test_the_point_window_reads_the_raster_at_the_point(bare_app, qtbot, scans, iris_tree, stacked):
    data = scans[stacked]
    # exposure times that differ from step to step in the 4 significant figures the window gives
    exposure = data.id["Exposure time"]
    data.update_components({exposure: data[exposure] * (1 + np.arange(data.shape[-3]).reshape(-1, 1, 1) / 100)})
    d, t, o = OBS_B
    other = image_data(iris_tree / f"{MD5}iris_l2_{d}_{t}_{o}_SJI_2832_t000.fits.gz")  # another observation
    viewers = quicklook(bare_app, [data, other])
    window = point_window(bare_app)
    assert window.parentWidget().windowTitle() == "Point"
    header = [window.horizontalHeaderItem(column).text() for column in range(window.columnCount())]
    assert header == ["Dataset", "Pixel", "Position", "Time", "Exposure", "Value", "Time sync"]
    # below the panels, overlapping none
    place = window.parentWidget().geometry()
    assert not [viewer for viewer in bare_app.viewers[-1] if viewer.parentWidget().geometry().intersects(place)]
    names = ("scan", "step", "slit", "λ")[-data.ndim :]
    no_match = [other.label, "no match", "", "", "", "", ""]

    def event(action, pixel):
        action()
        settle(qtbot, window)
        assert rows(window) == [read_at(data, names, pixel, f"time master, step {pixel[-3]}"), no_match]

    # it opens at the map's centre and wavelength, and follows map clicks, the map's wavelength slider, and a
    # spectrogram click, which moves the map to its wavelength
    start = expected_start(data)
    event(lambda: None, start)
    scan = (0,) * (data.ndim - 3)
    event(lambda: select_point(viewers["map"], 3, 50), (*scan, 3, 50, start[-1]))
    event(lambda: slide(viewers["map"], data.ndim - 1, 9), (*scan, 3, 50, 9))
    if stacked:
        event(lambda: slide(viewers["map"], 0, 2), (2, 3, 50, 9))
        scan = (2,)
    event(lambda: select_point(viewers["spectrogram"], 5, 40), (*scan, 3, 40, 5))
    # the value is that of the component the map shows
    [layer] = [layer for layer in viewers["map"].state.layers if layer.layer is data]
    layer.attribute = data.id[f"{data.label} DN/s"]
    settle(qtbot, window)
    pixel = (*scan, 3, 40, 5)
    assert rows(window)[0][5] == f"{data[layer.attribute, pixel]:.6g}" != read_at(data, names, pixel, "")[5]
    # Clear point leaves the time sync only
    menu_action(viewers["map"], "Clear point").trigger()
    settle(qtbot, window)
    assert rows(window) == [unpointed(data, "time master, step 3"), no_match]


def test_the_point_window_places_the_point_on_each_slit_jaw_image(bare_app, qtbot, monkeypatch, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    sjis = [sji, image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_2796_t000")))]
    viewers = quicklook(bare_app, [raster, *sjis])
    window = point_window(bare_app)
    shows = [(raster, viewers["map"]), *zip(sjis, viewers["sji"])]
    settle(qtbot, window)
    assert window.parentWidget().height() >= window.parentWidget().sizeHint().height()  # as tall as its rows

    def sync(viewer):
        """The time sync as the viewer's Frame time readout gives it."""
        return readout(viewer).rsplit(" · ", 1)[1]

    def expected(exposure, slit):
        wavelength = viewers["map"].state.slices[2]
        found = [read_at(raster, ("exposure", "slit", "λ"), (exposure, slit, wavelength), sync(viewers["map"]))]
        for data, viewer in shows[1:]:
            frame = viewer.state.slices[0]
            x, y = raster_point_on_sji(raster, data, exposure, slit, frame)
            found.append(read_at(data, ("frame", "y", "x"), (frame, round(y), round(x)), sync(viewer)))
        return found

    # exposure 78 has a frame of SJI 1400 near it but not of SJI 2796, which keeps frame 0 (NO MATCH)
    select_point(viewers["map"], 78, 10)
    settle(qtbot, window)
    assert [sync(viewer) for viewer in viewers["sji"]][1].startswith("NO MATCH")
    assert rows(window) == expected(78, 10)
    # a slit-jaw frame moved by hand, and a wavelength step
    slide(viewers["sji"][1], 0, 5)
    slide(viewers["map"], 2, 7)
    settle(qtbot, window)
    assert rows(window) == expected(78, 10)
    # off a slit-jaw image, as the Frame time readout says

    def off_the_image(self, viewer, point_on=Coordinator.point_on):
        return (-5.0, 3.0) if viewer is viewers["sji"][1] else point_on(self, viewer)

    monkeypatch.setattr(Coordinator, "point_on", off_the_image)
    slide(viewers["sji"][1], 0, 6)
    settle(qtbot, window)
    off = [sjis[1].label, "outside SJI FOV", "", "", "", "", sync(viewers["sji"][1])]
    assert "outside SJI FOV" in readout(viewers["sji"][1])
    assert rows(window)[1:] == [expected(78, 10)[1], off]
    monkeypatch.undo()
    # a click on a slit-jaw image moves the point to the raster pixel there
    (x, y), (exposure, slit) = clicked(viewers["sji"][0], raster, 78, 30)
    select_point(viewers["sji"][0], x, y)
    settle(qtbot, window)
    assert rows(window) == expected(exposure, slit)
    menu_action(viewers["map"], "Clear point").trigger()
    settle(qtbot, window)
    assert rows(window) == [unpointed(data, sync(viewer)) for data, viewer in shows]
    # a closed panel's dataset leaves the window
    viewers["sji"][1].close(warn=False)
    settle(qtbot, window)
    assert rows(window) == [unpointed(data, sync(viewer)) for data, viewer in shows[:2]]


def test_each_quicklook_has_its_own_point_window(bare_app, qtbot, monkeypatch, scans):
    scan, stack = scans
    refreshed = []
    cls = glue_solar.quicklook._PointWindow
    monkeypatch.setattr(cls, "refresh", lambda self, refresh=cls.refresh: refreshed.append(self) or refresh(self))
    first = quicklook(bare_app, [scan])
    quicklook(bare_app, [stack])
    tabs = (bare_app.tab_count - 2, bare_app.tab_count - 1)
    windows = [point_window(bare_app, tab) for tab in tabs]
    settle(qtbot, *windows)
    before = rows(windows[0])

    def refreshes(action):
        refreshed.clear()
        action()
        settle(qtbot, *windows)
        return refreshed

    # each move refreshes the shown tab's window once, and a hidden one not at all
    second = bare_app.viewers[-1]
    assert refreshes(lambda: select_point(second[0], 2, 30)) == [windows[1]]
    assert refreshes(lambda: slide(second[0], 3, 9)) == [windows[1]]
    assert refreshes(lambda: menu_action(second[0], "Clear point").trigger()) == [windows[1]]
    assert rows(windows[0]) == before
    # shown again, a window follows its own point
    assert refreshes(lambda: bare_app.tab_widget.setCurrentIndex(tabs[0])) == [windows[0]]
    assert refreshes(lambda: select_point(first["map"], 6, 20)) == [windows[0]]
    assert rows(windows[0])[0][1] == f"step 6, slit 20, λ {first['map'].state.slices[2]}"
    # closing its tab removes it, and it stops listening
    closed = windows.pop()
    with qtbot.waitSignal(closed.destroyed):
        bare_app.close_tab(tabs[1], warn=False)
    assert not [f for f in coordinator(bare_app.data_collection)._listeners if getattr(f, "__self__", 0) is closed]
    assert refreshes(lambda: select_point(first["map"], 7, 20)) == [windows[0]]


def test_a_point_window_closed_alone_stops_listening(bare_app, qtbot, scans):
    viewers = quicklook(bare_app, [scans[0]])
    window = point_window(bare_app)
    settle(qtbot, window)
    with qtbot.waitSignal(window.destroyed):
        window.parentWidget().close()
    # its panels' next click and slider step reach no deleted window
    select_point(viewers["map"], 3, 40)
    slide(viewers["spectrogram"], 0, 5)
    qtbot.wait(20)
    assert not [f for f in coordinator(bare_app.data_collection)._listeners if getattr(f, "__self__", 0) is window]


# Several windows of one raster file in one quicklook

THREE = ["C II 1336", "Si IV 1403", "Mg II k 2796"]


def windows_of(irispy_test_files, kind):
    """C II 1336, Si IV 1403 and Mg II k 2796 of the bundled sit-and-stare, or of 3860258481's scan 0 or stack."""
    if kind == "sit-and-stare":
        return raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], THREE)
    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    return raster_data(files[:1] if kind == "scan" else files, THREE, stack=kind == "stack")


@pytest.mark.parametrize("kind", ["scan", "sit-and-stare", "stack"])
def test_each_window_of_the_file_joins_the_quicklook(bare_app, qtbot, irispy_test_files, kind):
    rasters = windows_of(irispy_test_files, kind)
    others, mg = rasters[:2], rasters[2]
    viewers = quicklook(bare_app, rasters, window=THREE)
    collection = bare_app.data_collection
    assert viewers["map"].state.reference_data is mg
    # a spectrum for each other window, and a λ–time or λ–scan panel where it has a time axis, laid out apart
    title = {"scan": None, "sit-and-stare": "λ–time", "stack": "λ–scan"}[kind]
    for data, panels in zip(others, viewers["windows"], strict=True):
        name = data.label.split("-")[0].replace("_", " ")
        assert panels["spectrum"].state.title == f"{name} spectrum"
        assert set(panels) == ({"spectrum"} if title is None else {"spectrum", "wavelength"})
        if title is not None:
            state = panels["wavelength"].state
            assert (state.reference_data, state.title) == (data, f"{name} {title}")
            assert (state.x_att, state.y_att) == (data.pixel_component_ids[-1], data.pixel_component_ids[0])
    windows = bare_app.tab(bare_app.tab_count - 1).subWindowList()
    assert len(windows) == 5 + 2 * (1 + (title is not None))  # with the Point window
    assert not any(a.geometry().intersects(b.geometry()) for a, b in itertools.combinations(windows, 2))
    # a map of each window, as a user opens one, and a point at (scan,) step or exposure s, slit y
    maps = [image(bare_app, data, data.ndim - 3, data.ndim - 2) for data in others]
    lead = (2,) * (kind == "stack")
    if lead:
        viewers["map"].state.slices = (*lead, *viewers["map"].state.slices[1:])
    select_point(viewers["map"], 5, 20)
    qtbot.waitUntil(lambda: viewers["spectrogram"].state.slices[mg.ndim - 3] == 5)
    # every window at the same (scan,) step or exposure and slit: its own spectrum there, and a crosshair on its map
    for data, panels in zip(rasters, [*viewers["windows"], viewers]):
        [layer] = [layer for layer in panels["spectrum"].state.layers if layer.visible]
        np.testing.assert_array_equal(layer.profile[1], cube(data)[(*lead, 5, 20)])
    for viewer in [*maps, viewers["map"]]:
        assert viewer.state.slices[: len(lead)] == lead
        assert crosshair(viewer) == (5, 20)
    # a second quicklook of the same windows adds no link
    links = len(collection.external_links)
    quicklook(bare_app, rasters, window=THREE)
    assert len(collection.external_links) == links


def test_what_moves_with_other_windows_of_a_sit_and_stare(bare_app, qtbot, irispy_test_files):
    c2, si4, mg = windows_of(irispy_test_files, "sit-and-stare")
    viewers = quicklook(bare_app, [c2, si4, mg], window=THREE)
    c2_panel = viewers["windows"][0]["wavelength"]

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    # a map click moves every λ–time panel to the slit
    assert event(lambda: select_point(viewers["map"], 78, 10)) == {
        "point": (mg.label, (78, 10, None)),
        "spectrogram": (78, None, None),
        "wavelength": (None, 10, None),
        "wavelength1": (None, 10, None),
        "wavelength2": (None, 10, None),
    }
    # the slit slider of another window's panel moves the point
    assert event(lambda: slide(c2_panel, 1, 20)) == {
        "point": (mg.label, (78, 20, None)),
        "wavelength": (None, 20, None),
        "wavelength1": (None, 20, None),
        "wavelength2": (None, 20, None),
    }
    # a click on it moves the point to that window's exposure there, and every window's panels follow
    assert event(lambda: select_point(c2_panel, 3, 50)) == {
        "point": (c2.label, (50, 20, None)),
        "spectrogram": (50, None, None),
    }
    # the shown window's map has its crosshair, every λ–time panel its line, and the Point window reads it there
    assert crosshair(viewers["map"]) == (50, 20)
    for viewer in [viewers["wavelength"], *(panels["wavelength"] for panels in viewers["windows"])]:
        assert drawn(viewer, "point") == ("y", [50])
    window = point_window(bare_app)
    settle(qtbot, window)
    assert rows(window)[0][1].startswith("exposure 50, slit 20, λ ")
    for data, panels in zip([c2, si4, mg], [*viewers["windows"], viewers]):
        [layer] = [layer for layer in panels["spectrum"].state.layers if layer.visible]
        np.testing.assert_array_equal(layer.profile[1], cube(data)[50, 20])
    assert event(lambda: select_point(viewers["map"], 60, 5)) == {
        "point": (mg.label, (60, 5, None)),
        "spectrogram": (60, None, None),
        "wavelength": (None, 5, None),
        "wavelength1": (None, 5, None),
        "wavelength2": (None, 5, None),
    }


def test_what_moves_with_other_windows_of_a_stack(bare_app, qtbot, irispy_test_files):
    c2, si4, mg = windows_of(irispy_test_files, "stack")
    viewers = quicklook(bare_app, [c2, si4, mg], window=THREE)
    wave = expected_start(mg)[-1]

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    # a map click moves every λ–scan panel to the step and slit
    assert event(lambda: select_point(viewers["map"], 2, 30)) == {
        "point": (mg.label, (0, 2, 30, None)),
        "spectrogram": (0, 2, None, None),
        "wavelength": (None, 2, 30, None),
        "wavelength1": (None, 2, 30, None),
        "wavelength2": (None, 2, 30, None),
    }
    # the map's scan moves the point, whose scan the λ–scan panels show
    assert event(lambda: slide(viewers["map"], 0, 2)) == {
        "point": (mg.label, (2, 2, 30, None)),
        "map": (2, None, None, wave),
        "spectrogram": (2, 2, None, None),
    }
    # the step slider of another window's panel moves the point
    assert event(lambda: slide(viewers["windows"][1]["wavelength"], 1, 5)) == {
        "point": (mg.label, (2, 5, 30, None)),
        "spectrogram": (2, 5, None, None),
        "wavelength": (None, 5, 30, None),
        "wavelength1": (None, 5, 30, None),
        "wavelength2": (None, 5, 30, None),
    }
    # a click on another window's panel moves the point to that window, and the time of every window follows its step
    c2_panel = viewers["windows"][0]["wavelength"]
    assert event(lambda: select_point(c2_panel, 10, 2)) == {"point": (c2.label, (2, 5, 30, None))}
    assert event(lambda: slide(c2_panel, 1, 0)) == {
        "point": (c2.label, (2, 0, 30, None)),
        "spectrogram": (2, 0, None, None),
        "wavelength": (None, 0, 30, None),
        "wavelength1": (None, 0, 30, None),
        "wavelength2": (None, 0, 30, None),
    }
    assert [drawn(viewer, "time") for viewer in (viewers["wavelength"], c2_panel)] == [("y", [2])] * 2


def test_a_stack_of_other_scans_is_not_a_window_of_the_stack(bare_app, irispy_test_files):
    # scans 0 and 1 against 0 and 2: the same first scan, shape and DATE_OBS
    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    [c2] = raster_data(files[:2], ["C II 1336"], stack=True)
    [si4] = raster_data([files[0], files[2]], ["Si IV 1403"], stack=True)
    assert quicklook(bare_app, [c2, si4], window=THREE[:2])["windows"] == []


@pytest.mark.parametrize("chosen", [True, False])
def test_time_moves_a_point_on_another_window(bare_app, qtbot, monkeypatch, irispy_test_files, chosen):
    c2, _, mg = windows_of(irispy_test_files, "sit-and-stare")
    viewers = quicklook(bare_app, [c2, mg], window=THREE[::2])
    c2_panel = viewers["windows"][0]["wavelength"]
    if chosen:
        menu_action(viewers["map"], "Time master").trigger()
    select_point(c2_panel, 3, 50)
    qtbot.wait(20)
    slit = sliders(bare_app, viewers)["point"][1][1]
    if not chosen:  # the time master is then the shown window again
        c2_panel.close(warn=False)

    def event(action):
        return changes(bare_app, qtbot, viewers, action)

    # F and Go to UTC move the time master's exposure, and the point, on its other window, goes with it
    assert event(lambda: press(viewers["map"], Qt.Key_F)) == {
        "point": (c2.label, (51, slit, None)),
        "spectrogram": (51, None, None),
    }
    type_in_dialog(monkeypatch, utc(mg[mg.id["Time"]][100, 0, 0]))
    assert event(lambda: menu_action(viewers["map"], "Go to UTC…").trigger()) == {
        "point": (c2.label, (100, slit, None)),
        "spectrogram": (100, None, None),
    }


def test_the_browser_shows_each_ticked_window(qtbot, monkeypatch, tmp_path, irispy_test_files):
    path = find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))
    app = bare_app_for(qtbot, monkeypatch)
    browse(qtbot, app, monkeypatch, copy_files(tmp_path / "sns", [path]), [0], only=("C II", "Mg II k"))
    titles = [row[1] for row in viewer_rows(app)]
    assert titles == [
        "Mg II k 2796 slit vs time",
        "Mg II k 2796 spectrogram",
        "Mg II k 2796 λ–time",
        "Mg II k 2796 spectrum",
        "C II 1336 λ–time",
        "C II 1336 spectrum",
    ]


def test_each_band_opens_with_its_stretch(bare_app, irispy_test_files):
    rasters = windows_of(irispy_test_files, "sit-and-stare")
    sjis = [image_data(find_irispy_test_file(irispy_test_files, SNS.format(f"SJI_{band}_t000")))
            for band in (1330, 1400, 2796, 2832)]
    viewers = quicklook(bare_app, [*rasters, *sjis], window=THREE)
    # D43: log in the FUV, sqrt about Mg II k and h, linear for slit-jaw 2832; glue's controls change them
    stretches = {role: viewers[role].state.layers[0].stretch for role in ("map", "spectrogram", "wavelength")}
    assert stretches == dict.fromkeys(stretches, "sqrt")  # Mg II k 2796
    assert [panels["wavelength"].state.layers[0].stretch for panels in viewers["windows"]] == ["log", "log"]
    assert {str(v.state.reference_data.meta["TDESC1"]): v.state.layers[0].stretch for v in viewers["sji"]} == {
        "SJI_1330": "log", "SJI_1400": "log", "SJI_2796": "sqrt", "SJI_2832": "linear"}


def test_the_spectrum_panel_labels_the_main_lines(bare_app, scans):
    viewers = quicklook(bare_app, [scans[0]])  # C II 1336
    tool = viewers["spectrum"].toolbar.tools["solar:lines"]
    assert sorted(x for _, xs in tool.positions() for x in xs) == pytest.approx([1334.5323, 1335.6628, 1335.7079])


# Blink (D41): one viewer alternating two positions, each a dataset and its slider position


def show(viewer, data, slices):
    """Show ``data`` at ``slices`` on the viewer's axes, as its options' reference data and axes and its sliders do."""
    state = viewer.state
    x, y = state.x_att.axis, state.y_att.axis
    state.reference_data = data
    state.x_att, state.y_att = data.pixel_component_ids[x], data.pixel_component_ids[y]
    state.slices = slices


def position(viewer):
    """The viewer's dataset, slices, shown axes, limits and the datasets whose layers are visible."""
    state = viewer.state
    visible = {layer.layer.data.label for layer in state.layers if layer.visible}
    limits = (state.x_min, state.x_max, state.y_min, state.y_max)
    return state.reference_data, tuple(state.slices), state.x_att.axis, state.y_att.axis, limits, visible


def blink_windows(app, qtbot, irispy_test_files):
    """
    The quicklook of 3860258481's scan 0 and its three windows, with Si IV 1403 added to the Mg II k map and set as
    its blink partner at wavelength 20; the map is back on Mg II k, zoomed in.
    """
    c2, si4, mg = windows_of(irispy_test_files, "scan")
    viewers = quicklook(app, [c2, si4, mg], window=THREE)
    raster_map = viewers["map"]
    slices = raster_map.state.slices
    raster_map.add_data(si4)
    show(raster_map, si4, (0, 0, 20))
    menu_action(raster_map, "Set blink partner here").trigger()
    show(raster_map, mg, slices)
    state = raster_map.state
    with delay_callback(state, "x_min", "x_max", "y_min", "y_max"):
        state.x_min, state.x_max, state.y_min, state.y_max = 0.5, 5.5, 20.5, 80.5
    qtbot.wait(20)
    return viewers, (c2, si4, mg)


def test_blink_alternates_two_windows_exactly(bare_app, qtbot, irispy_test_files):
    viewers, (_, si4, mg) = blink_windows(bare_app, qtbot, irispy_test_files)
    raster_map = viewers["map"]
    state = raster_map.state
    tool, blink = raster_map.toolbar.tools["solar:coordinate"], menu_action(raster_map, "Blink")

    def styles():
        return [
            (layer.stretch, layer.percentile, layer.v_min, layer.v_max)
            for layer in state.layers
            if hasattr(layer, "stretch")
        ]

    before = styles()
    zoom = (state.x_min, state.x_max, state.y_min, state.y_max)
    a = (mg, tuple(state.slices), 0, 1, zoom, {mg.label})  # Si IV 1403 hidden while Mg II k shows
    b = (si4, (0, 0, 20), 0, 1, zoom, {si4.label})
    shown = []
    tool._blink.timeout.connect(lambda: shown.append(position(raster_map)))
    blink.trigger()
    shown.insert(0, position(raster_map))  # the first flip, at once
    assert blink.isChecked()
    tool._blink.setInterval(1)
    qtbot.waitUntil(lambda: len(shown) >= 6)
    blink.trigger()
    assert not tool._blink.isActive()
    assert not blink.isChecked()
    assert shown == [(b, a)[i % 2] for i in range(len(shown))]
    # each layer keeps its stretch and limits, and both windows' layers show again
    assert styles() == before
    assert position(raster_map)[-1] == {si4.label, mg.label}
    assert raster_map.toolbar.active_tool.tool_id == "image:point_selection"
    # a new partner mid-blink stops it, showing the window left
    blink.trigger()
    menu_action(raster_map, "Set blink partner here").trigger()
    assert not tool._blink.isActive()
    assert position(raster_map)[-1] == {si4.label, mg.label}


def test_what_moves_on_a_blink(bare_app, qtbot, irispy_test_files):
    viewers, (_, si4, mg) = blink_windows(bare_app, qtbot, irispy_test_files)
    raster_map = viewers["map"]
    tool, coord = raster_map.toolbar.tools["solar:coordinate"], coordinator(bare_app.data_collection)
    wavelength = raster_map.state.slices[2]
    master = coord._master(observation_key(mg))

    def flip():
        tool._flip()
        assert not coord._timer.isActive()  # no time sync, and the map does not join the point

    # the map alone, on the partner's window and wavelength and back; the point, the panels and the master stay
    assert changes(bare_app, qtbot, viewers, flip) == {"map": (None, None, 20)}
    assert raster_map.state.reference_data is si4
    assert changes(bare_app, qtbot, viewers, flip) == {"map": (None, None, wavelength)}
    assert raster_map.state.reference_data is mg
    assert coord._master(observation_key(mg)) is master


def test_blink_in_one_cube(bare_app, qtbot, irispy_test_files):
    *_, mg = windows_of(irispy_test_files, "scan")
    viewers = quicklook(bare_app, [mg])
    raster_map, spectrogram = viewers["map"], viewers["spectrogram"]
    state = raster_map.state
    wavelength = state.slices[2]
    slide(raster_map, 2, 10)
    menu_action(raster_map, "Set blink partner here").trigger()
    slide(raster_map, 2, wavelength)
    limits = (state.x_min, state.x_max, state.y_min, state.y_max)
    slider = raster_map.options_widget().slice_helper._sliders[2]
    tool = raster_map.toolbar.tools["solar:coordinate"]
    tool._blink.setInterval(60_000)  # no tick of its own between the flips by hand, however slow the machine
    # the wavelength slider alone, the same widget, as a frame slider would in a blink in time
    assert changes(bare_app, qtbot, viewers, menu_action(raster_map, "Blink").trigger) == {"map": (None, None, 10)}
    assert changes(bare_app, qtbot, viewers, tool._flip) == {"map": (None, None, wavelength)}
    assert raster_map.options_widget().slice_helper._sliders[2] is slider
    assert (state.x_min, state.x_max, state.y_min, state.y_max) == limits
    menu_action(raster_map, "Blink").trigger()
    # a blink of the spectrogram's step leaves the point, which its slider would move
    tool = spectrogram.toolbar.tools["solar:coordinate"]
    assert spectrogram.state.slices[0] != 2
    tool.partner = (mg, (2, *spectrogram.state.slices[1:]))
    assert changes(bare_app, qtbot, viewers, tool._flip) == {"spectrogram": (2, None, None)}


def test_blink_in_time(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    menu_action(sji_viewer, "Time master").trigger()
    sji_viewer.state.slices = (10, 0, 0)
    menu_action(sji_viewer, "Set blink partner here").trigger()
    sji_viewer.state.slices = (40, 0, 0)
    qtbot.wait(20)
    tool = sji_viewer.toolbar.tools["solar:coordinate"]
    tool._blink.setInterval(60_000)  # no tick of its own between the flips by hand, however slow the machine
    # two frames of the time master: its frame alone, the raster staying at frame 40's time (D41)
    assert changes(bare_app, qtbot, viewers, menu_action(sji_viewer, "Blink").trigger) == {"sji0": (10, None, None)}
    assert changes(bare_app, qtbot, viewers, tool._flip) == {"sji0": (40, None, None)}
    assert changes(bare_app, qtbot, viewers, tool._flip) == {"sji0": (10, None, None)}
    menu_action(sji_viewer, "Blink").trigger()
    assert not tool._blink.isActive()


def test_blink_interval(app, scans):
    scan, _ = scans
    app.data_collection.append(scan)
    raster_map = image(app, scan, 0, 1)
    tool = raster_map.toolbar.tools["solar:coordinate"]
    intervals = menu_action(raster_map, "Blink interval").menu().actions()
    assert [action.text() for action in intervals] == ["0.25 s", "0.5 s", "1 s", "2 s"]
    assert [action.isChecked() for action in intervals] == [False, True, False, False]
    assert tool._blink.interval() == 500
    menu_action(raster_map, "Set blink partner here").trigger()
    menu_action(raster_map, "Blink").trigger()
    intervals[0].trigger()  # while it blinks
    assert (tool._blink.interval(), tool._blink.isActive()) == (250, True)
    assert [action.isChecked() for action in intervals] == [True, False, False, False]
    intervals[3].trigger()
    assert tool._blink.interval() == 2000
    assert [action.isChecked() for action in intervals] == [False, False, False, True]


def test_blink_stops_when_its_viewer_closes(bare_app, qtbot, monkeypatch, irispy_test_files):
    viewers, _ = blink_windows(bare_app, qtbot, irispy_test_files)
    raster_map = viewers["map"]
    tool = raster_map.toolbar.tools["solar:coordinate"]
    flips = []
    tool._blink.timeout.connect(lambda: flips.append(1))
    menu_action(raster_map, "Blink").trigger()
    tool._blink.setInterval(1)
    qtbot.waitUntil(lambda: len(flips) >= 2)
    # a close cancelled at glue-qt's confirmation leaves it blinking
    raster_map._warn_close = True
    monkeypatch.setattr(raster_map, "_confirm_close", lambda: False)
    assert not raster_map._mdi_wrapper.close()
    assert tool._blink.isActive()
    raster_map.close(warn=False)
    assert not tool._blink.isActive()
    flipped = len(flips)
    qtbot.wait(20)
    assert len(flips) == flipped


def test_blink_stops_when_the_partner_goes(bare_app, qtbot, monkeypatch, irispy_test_files):
    viewers, (c2, si4, mg) = blink_windows(bare_app, qtbot, irispy_test_files)
    raster_map = viewers["map"]
    tool, blink = raster_map.toolbar.tools["solar:coordinate"], menu_action(raster_map, "Blink")
    a = position(raster_map)[:-1]
    blink.trigger()
    tool._flip()  # Mg II k again, against Si IV 1403
    bare_app.data_collection.remove(si4)
    tool._blink.setInterval(1)
    qtbot.waitUntil(lambda: not tool._blink.isActive())
    assert not blink.isChecked()
    assert position(raster_map) == (*a, {mg.label})
    # Blink with no partner says why
    shown = refusals(monkeypatch)
    blink.trigger()
    assert shown == ["Could not blink\nChoose 'Set blink partner here' first, at the position to blink against."]
    assert not blink.isChecked()
    # a shown window removed: glue shows the partner's, which the blink had hidden, and the blink stops showing it
    raster_map.add_data(c2)
    show(raster_map, c2, (0, 0, 5))
    menu_action(raster_map, "Set blink partner here").trigger()
    show(raster_map, mg, a[1])
    blink.trigger()
    assert raster_map.state.reference_data is c2
    bare_app.data_collection.remove(c2)
    qtbot.waitUntil(lambda: not tool._blink.isActive())
    assert not blink.isChecked()
    assert raster_map.state.reference_data is mg
    assert all(layer.visible for layer in raster_map.state.layers)
