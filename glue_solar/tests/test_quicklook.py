import shutil
from collections import Counter

import numpy as np
import pytest
from glue.config import settings
from glue.core import Data
from glue.core.component import DateTimeComponent
from glue.core.hub import HubListener
from glue.core.link_manager import LinkManager
from glue.core.message import SettingsChangeMessage, SubsetUpdateMessage
from glue.core.subset import SubsetState
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.viewers.image.state import AggregateSlice
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.io import fits

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.quicklook import QuicklookImageViewer, coordinator, nearest, observation_key, quicklook
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.tests.helpers import count_tick_work, mouse, raster_point_on_sji, select_point

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
    """The C II 1336 window of the 13 fixture scans of 3860258481, as scan 0 and as a stack."""
    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    assert len(files) == 13
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
    stack_map = image(app, stack, 1, 2, (5, 0, 0, 8))
    select_point(stack_map, 2, 40)
    # the Pixel tool's assignment and one by the coordinator, which does not answer its own
    assert updates.counts == {scan.label: 2, stack.label: 2}
    assert app.data_collection.subset_groups[0].subset_state.slices == [
        slice(5, 6),
        slice(2, 3),
        slice(40, 41),
        slice(None),
    ]
    assert stack_map.state.slices == (5, 0, 0, 8)


def test_menu_entries_keep_the_pixel_tool(app, scans):
    scan, _ = scans
    app.data_collection.append(scan)
    raster_map = image(app, scan, 0, 1)
    select_point(raster_map, 3, 50)
    coord = coordinator(app.data_collection)

    menu_action(raster_map, "Time master").trigger()
    assert coord.masters == {observation_key(scan): scan}
    menu_action(raster_map, "Clear point").trigger()
    assert coord.point is None
    assert not app.data_collection.subset_groups[0].subset_state.to_mask(scan).any()
    for _ in range(2):
        assert raster_map.toolbar.active_tool.tool_id == "image:point_selection"
        assert raster_map.toolbar.actions["image:point_selection"].isChecked()
        menu_action(raster_map, "Time master").trigger()


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
        assert not [tool for tool in viewers[role].toolbar.tools if tool.startswith("select:")]
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


def test_a_sit_and_stare_exposure_axis(bare_app, monkeypatch, irispy_test_files):
    raster, _ = sit_and_stare(irispy_test_files)
    bare_app.show()  # the quicklook's own panel sizes
    viewers = quicklook(bare_app, [raster])
    times = raster[raster.id["Time"]][:, 0, 0]
    first, last = (np.datetime_as_string(t, unit="s") for t in (times[0], times[-1]))
    label = f"Exposure (acquisition order)\n{first} – {last[11:]} UTC"  # one day

    def check(viewer, axis):
        state = viewer.state
        other = "y" if axis == "x" else "x"
        near, far, other_near, other_far = "btlr" if axis == "x" else "lrbt"
        assert getattr(state, f"{axis}_axislabel") == label
        ticks = drawn_ticks(viewer, near)
        assert list(ticks) == [label]  # exposure numbers, and no world coordinate along the axis
        assert len(ticks[label]) >= 2
        assert {int(tick) for tick in ticks[label]} <= set(range(raster.shape[0]))
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
    assert label.startswith("Exposure (acquisition order)\n")
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


@pytest.mark.remote_data
def test_quicklook_gives_aia_cutouts_no_role(bare_app, tmp_path, irispy_data, irispy_test_files):
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


@pytest.mark.remote_data
def test_quicklook_of_a_full_raster(bare_app, irispy_data):
    [data] = raster_data([irispy_data("iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz")])
    viewers = quicklook(bare_app, [data])
    check_panels(bare_app, viewers, data, {"map": (0, 1), "spectrogram": (2, 1), "wavelength": (2, 0)})


def test_quicklook_without_a_raster(bare_app, irispy_test_files):
    sjis = [image_data(find_irispy_test_file(irispy_test_files, SNS.format(f"SJI_{c}_t000"))) for c in (1400, 2796)]
    viewers = quicklook(bare_app, sjis)
    assert set(viewers) == {"sji"}
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
            viewers["map"].state.slices = (4, *viewers["map"].state.slices[1:])
            qtbot.waitUntil(lambda viewers=viewers: viewers["spectrogram"].state.slices[0] == 4)
            np.testing.assert_array_equal(spectrum(viewers), cube(data)[4, 1, 30])
            assert viewers["wavelength"].state.slices[1:3] == (1, 30)


def test_a_click_on_a_wavelength_panel_moves_the_map_to_its_wavelength(bare_app, qtbot, scans):
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
    select_point(viewers["sji"][0], 10, 20)
    qtbot.wait(20)
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
    for viewer in (sji_viewer, viewers["map"]):  # the slit-jaw viewer gets the point, then drops it
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
    for viewer in (viewers["sji"][0], viewers["map"]):  # a slit-jaw point, then a raster point
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
    stack_map.state.slices = (5, *stack_map.state.slices[1:])
    select_point(stack_map, 3, 70)
    qtbot.wait(20)
    [group] = bare_app.session.edit_subset_mode.edit_subset
    point = group.subset_state.slices
    viewer = bare_app.new_data_viewer(ImageViewer, data=stack)  # glue resets its sliders to 0
    qtbot.wait(20)
    assert group.subset_state.slices == point
    assert viewer.state.slices[:2] == (5, 3)  # it shows wavelength against slit at the point's scan and step
    other = bare_app.new_data_viewer(ImageViewer, data=scan)
    other.add_data(stack)
    other.state.reference_data = stack
    qtbot.wait(20)
    assert group.subset_state.slices == point
    assert other.state.slices[0] == 5


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
    for bad in (np.array(["NaT", "2021-01-01"], "datetime64[ns]"), times[:0], times.reshape(2, 2)):
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


def check_follower(app, qtbot, master_time, follower, viewer):
    """
    The follower's frame is the nearest to the master's time, or NO MATCH when half a cadence away,
    and then the frame is kept. Call it after moving the master, before Qt runs the sync.
    """
    before = viewer.state.slices[0]
    times = follower[follower.id["Time"]][:, 0, 0]
    index = expected_nearest(master_time, times)
    offset = times[index] - master_time
    half = np.median(np.diff(np.sort(times))) / 2
    delta = offset / np.timedelta64(1, "s")
    if abs(offset) <= half:
        qtbot.waitUntil(lambda: f" · Δt {delta:+.1f} s" in readout(viewer))
        assert viewer.state.slices[0] == index
        assert not viewer.toolbar.tools["solar:frame_time"]._grey.get_visible()
    else:
        qtbot.waitUntil(lambda: f"NO MATCH Δt = {delta:+.1f} s" in readout(viewer))
        assert viewer.state.slices[0] == before
        assert viewer.toolbar.tools["solar:frame_time"]._grey.get_visible()
    return abs(offset) <= half


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
    for scan, step in ((6, 4), (6, 0), (6, 7), (12, 7), (0, 0)):
        viewers["spectrogram"].state.slices = (scan, step, *viewers["spectrogram"].state.slices[2:])
        assert check_follower(bare_app, qtbot, raster_time(stack, (scan, step)), sji, sji_viewer)
        qtbot.waitUntil(lambda step=step: f"time master, step {step}" in readout(viewers["map"]))
        assert heard[-1][2] == stack[stack.id["Exposure time"]][scan, step, 0, 0]


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


def test_time_sync_without_a_raster_point(bare_app, qtbot, irispy_test_files):
    raster, sji = sit_and_stare(irispy_test_files)
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    coord = coordinator(bare_app.data_collection)
    viewers["spectrogram"].state.slices = (1, *viewers["spectrogram"].state.slices[1:])
    qtbot.waitUntil(lambda: sji_viewer.state.slices[0] == 0)
    select_point(sji_viewer, 10, 20)  # a slit-jaw point leaves the frame where it is
    qtbot.wait(20)
    assert sji_viewer.state.slices[0] == 0
    menu_action(viewers["map"], "Clear point").trigger()  # and the exposure slider still leads
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


def browse(app, monkeypatch, folder, rows):
    """Load observation ``rows`` of ``folder`` through the observation browser, with its quicklook box as is."""
    from glue_solar.sources.iris import browse_iris
    from glue_solar.sources.loaders.iris import QtIRISImporter

    monkeypatch.setattr(QtWidgets.QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(folder))

    def tick_and_load(dialog):
        for row in rows:
            dialog.obs_tree.topLevelItem(row).setCheckState(0, Qt.Checked)
        dialog.finalize()
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
        if path == "browser":
            browse(app, monkeypatch, folder, [0])
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
    browse(app, monkeypatch, folder, [1])  # the second observation only
    assert app.tab_count == 2
    shown = app.viewers[-1][0].state.reference_data
    browsed = app.data_collection[0]
    assert observation_key(shown) == observation_key(browsed)
    # both observations loaded: the menu asks, and opens the one chosen
    browse(app, monkeypatch, folder, [0])
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
    assert len(set(labels)) == len(labels) == 13 * 9  # each file's windows are labelled by its raster number
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
