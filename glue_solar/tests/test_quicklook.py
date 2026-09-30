import shutil
from collections import Counter

import numpy as np
import pytest
from glue.core import Data
from glue.core.component import DateTimeComponent
from glue.core.hub import HubListener
from glue.core.message import SubsetUpdateMessage
from glue.viewers.image.state import AggregateSlice
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from qtpy import QtWidgets

import astropy.units as u
from astropy.io import fits

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.quicklook import QuicklookImageViewer, coordinator, nearest, observation_key, quicklook
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.tests.helpers import mouse, select_point

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
        # nor does glue draw the point's crosshair on a slit-jaw image
        assert [layer.visible for layer in viewer.state.layers if layer.layer.label == "Point"] == [False]
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


def test_quicklook_of_a_raster_and_of_a_stack(bare_app, scans):
    scan, stack = scans
    viewers = quicklook(bare_app, [scan])
    check_panels(bare_app, viewers, scan, {"map": (0, 1), "spectrogram": (2, 1), "wavelength": (2, 0)})
    assert viewers["wavelength"].state.title == "C II 1336 λ–step"
    viewers = quicklook(bare_app, [scan, stack])  # a stack of the window is shown rather than one scan
    check_panels(bare_app, viewers, stack, {"map": (1, 2), "spectrogram": (3, 2), "wavelength": (3, 0)})
    assert viewers["map"].state.slices[0] == 0


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
    second = quicklook(bare_app, [stack])
    [second_point] = bare_app.session.edit_subset_mode.edit_subset
    assert second_point is not first_point
    for viewer in (*[first[role] for role in ("map", "spectrogram", "wavelength", "spectrum")], *second["sji"]):
        assert not [layer for layer in viewer.state.layers if layer.visible and layer.layer in second_point.subsets]
    for role in ("map", "spectrum"):
        shown = [layer.layer.group for layer in second[role].state.layers if hasattr(layer.layer, "group") and layer.visible]
        assert shown == [second_point]
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
    # the point shows on the slit-jaw image it was clicked on, not on the raster panels
    for viewer, shown in ((viewers["sji"][0], True), *((viewers[role], False) for role in RASTER_PANELS)):
        assert [layer.visible for layer in viewer.state.layers if getattr(layer.layer, "group", None) is group] == [
            shown
        ]


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
    for step in (2, 3, 4, 5):
        mouse(viewers["map"], "motion_notify_event", step, 30)
    mouse(viewers["map"], "button_release_event", 5, 30)
    assert written == []  # nothing yet: the panels follow when Qt next runs
    qtbot.waitUntil(lambda: viewers["spectrogram"].state.slices[0] == 5)
    assert written == [5]
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
    """The follower's frame is the nearest to the master's time, or NO MATCH when half a cadence away."""
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
        assert viewer.toolbar.tools["solar:frame_time"]._grey.get_visible()
    return abs(offset) <= half


def test_a_raster_master_moves_the_slit_jaw_images(bare_app, qtbot, irispy_test_files):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))
    viewers = quicklook(bare_app, [raster, sji])
    [sji_viewer] = viewers["sji"]
    wavelengths = [viewers[role].state.slices[-1] for role in RASTER_PANELS]
    matched = []
    for step in (93, 0, 186, 1):
        viewers["spectrogram"].state.slices = (step, *viewers["spectrogram"].state.slices[1:])
        matched.append(check_follower(bare_app, qtbot, raster_time(raster, (step,)), sji, sji_viewer))
        assert f"time master, step {step}" in readout(viewers["spectrogram"])
    assert matched == [False, True, True, True]  # the decimated fixture's frames are 4.6 minutes apart
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
    menu_action(sji_viewer, "Time master").trigger()
    exposures = raster[raster.id["Time"]][:, 0, 0]
    for frame in (5, 40):
        sji_viewer.state.slices = (frame, 0, 0)
        [exposure], _ = nearest([sji[sji.id["Time"]][frame, 0, 0]], exposures)
        qtbot.waitUntil(lambda exposure=exposure: group.subset_state.slices[0] == slice(exposure, exposure + 1))
        assert group.subset_state.slices[1] == slit  # the slit stays
        qtbot.waitUntil(lambda exposure=exposure: viewers["spectrogram"].state.slices[0] == exposure)
        assert "time master" in readout(sji_viewer)


def test_an_unmatched_slit_jaw_keeps_its_frame(bare_app, qtbot, scans):
    scan, _ = scans
    late = raster_time(scan, (0,)) + np.timedelta64(1, "D") + np.arange(5) * np.timedelta64(10, "s")
    sji = slit_jaw(late, scan)
    viewers = quicklook(bare_app, [scan, sji])
    [sji_viewer] = viewers["sji"]
    sji_viewer.state.slices = (3, 0, 0)
    viewers["spectrogram"].state.slices = (2, *viewers["spectrogram"].state.slices[1:])
    qtbot.waitUntil(lambda: "NO MATCH Δt = " in readout(sji_viewer))
    assert sji_viewer.state.slices[0] == 3
    assert sji_viewer.toolbar.tools["solar:frame_time"]._grey.get_visible()


def test_a_slit_jaw_master_picks_the_scan_of_a_stack(bare_app, qtbot, scans):
    _, stack = scans
    step = stack.shape[1] // 2
    scan_times = stack[stack.id["Time"]][:, step, 0, 0]
    sji = slit_jaw(scan_times[0] + np.arange(40) * (scan_times[-1] - scan_times[0]) / 39, stack)
    viewers = quicklook(bare_app, [stack, sji])
    [sji_viewer] = viewers["sji"]
    [group] = bare_app.session.edit_subset_mode.edit_subset
    point = group.subset_state.slices
    menu_action(sji_viewer, "Time master").trigger()
    for frame in (0, 20, 39):
        sji_viewer.state.slices = (frame, 0, 0)
        [scan], _ = nearest([sji[sji.id["Time"]][frame, 0, 0]], scan_times)
        qtbot.waitUntil(lambda scan=scan: group.subset_state.slices[0] == slice(scan, scan + 1))
        assert group.subset_state.slices[1:] == point[1:]  # step and slit stay
        qtbot.waitUntil(lambda scan=scan: viewers["spectrogram"].state.slices[0] == scan)


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
    sji = slit_jaw(frames, scan)
    viewers = quicklook(bare_app, [scan, sji])
    [sji_viewer] = viewers["sji"]
    for step in (0, 10, 20, 21, scan.shape[0] - 1):
        viewers["spectrogram"].state.slices = (step, *viewers["spectrogram"].state.slices[1:])
        check_follower(bare_app, qtbot, times[step], sji, sji_viewer)
    # a stack of two scans at the same times, and the slit-jaw image as master: the first scan
    [stack] = raster_data([path, path], stack=True)
    viewers = quicklook(bare_app, [stack, sji])
    [sji_viewer] = viewers["sji"]
    [group] = bare_app.session.edit_subset_mode.edit_subset
    menu_action(sji_viewer, "Time master").trigger()
    for frame in (0, 29):
        sji_viewer.state.slices = (frame, 0, 0)
        qtbot.wait(20)
        assert group.subset_state.slices[0] == slice(0, 1)


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


def test_slit_jaw_panels(bare_app, qtbot, tmp_path, irispy_test_files):
    from glue_solar import quicklook as module

    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    channels = (1330, 1400, 2796, 2832)
    sjis = [image_data(find_irispy_test_file(irispy_test_files, SNS.format(f"SJI_{c}_t000"))) for c in channels]
    viewers = quicklook(bare_app, [raster, *sjis])
    assert [viewer.state.title for viewer in viewers["sji"]] == [f"SJI {c}" for c in channels]
    # each opens on the raster's field of view, with a margin
    corners = [module._lon_lat(raster, [step, slit, 0]) for step in (0, 186) for slit in (0, 39)]
    lon, lat = (np.array([corner[i] for corner in corners], dtype=float) for i in (0, 1))
    for viewer in viewers["sji"]:
        x, y = module._sji_pixels(viewer.state.reference_data, 0, lon, lat)
        state = viewer.state
        assert state.x_min < x.min()
        assert x.max() < state.x_max
        assert state.y_min < y.min()
        assert y.max() < state.y_max
    # all follow the time master
    viewers["spectrogram"].state.slices = (120, *viewers["spectrogram"].state.slices[1:])
    for viewer in viewers["sji"]:
        qtbot.waitUntil(lambda viewer=viewer: " · Δt " in readout(viewer) or "NO MATCH" in readout(viewer))

    # the raster point, projected into the displayed frame: inside, or outside the field of view
    coord = coordinator(bare_app.data_collection)
    sji_viewer = viewers["sji"][1]
    ny, nx = sjis[1].shape[1:]
    viewers["spectrogram"].state.slices = (1, *viewers["spectrogram"].state.slices[1:])  # matched in time
    qtbot.waitUntil(lambda: " · Δt " in readout(sji_viewer))
    x, y = coord.point_on(sji_viewer)
    assert 1.5 < x < nx - 2.5
    assert 1.5 < y < ny - 2.5
    assert "outside SJI FOV" not in readout(sji_viewer)
    viewers["spectrogram"].state.slices = (186, *viewers["spectrogram"].state.slices[1:])
    qtbot.wait(20)
    sji_viewer.state.slices = (0, 0, 0)  # moved back by hand: the late exposure is off the first frame
    x, _ = coord.point_on(sji_viewer)
    assert x > nx - 0.5 + 2
    assert "outside SJI FOV" in readout(sji_viewer)

    deconvolved = tmp_path / SNS.format("SJI_2796_t000_deconvolved")
    shutil.copy2(find_irispy_test_file(irispy_test_files, SNS.format("SJI_2796_t000")), deconvolved)
    viewers = quicklook(bare_app, [raster, image_data(deconvolved)])
    assert [viewer.state.title for viewer in viewers["sji"]] == ["SJI 2796 (deconvolved)"]
