import shutil
from collections import Counter

import numpy as np
import pytest
from glue.core import Data
from glue.core.hub import HubListener
from glue.core.message import SubsetUpdateMessage
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.io import fits

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.quicklook import QuicklookImageViewer, coordinator, observation_key, quicklook
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.tests.helpers import select_point

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
