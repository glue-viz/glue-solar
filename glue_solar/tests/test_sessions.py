"""
Sessions keep the coordinates and colormaps of every kind of dataset glue-solar makes from IRIS data, on irispy's test
files, the links `link_hpc` gives, the colormap of a sunpy map, and a quicklook's time master and point; they refer to
the files IRIS data are read from, so a quicklook's stays small, and two quicklooks restore twice alike; glue-solar keeps
the last one as glue closes, which its menu entry restores.
"""

import json
import os
import shutil

import dask.array as da
import glue.config
import numpy as np
import pytest
from glue.core import Data, DataCollection
from glue.core.link_helpers import LinkCollection
from glue.core.state import GlueSerializer, GlueUnSerializer
from glue.viewers.image.state import AggregateSlice
from glue.viewers.profile.state import ProfileViewerState
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from matplotlib import colormaps
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDialog, QFileDialog, QInputDialog, QMessageBox

import astropy.units as u
from astropy.wcs import WCS

import sunpy.data.test
from sunpy.visualization.colormaps import cmlist

import glue_solar
from glue_solar import glue_patches
from glue_solar.conftest import MD5, OBS_A, find_irispy_test_file
from glue_solar.quicklook import coordinator, quicklook
from glue_solar.regrid import north_up, rebin, regrid_on_time
from glue_solar.sources.bursts import si_iv_bursts
from glue_solar.sources.calibration import radiometric_calibration
from glue_solar.sources.iris import browse_iris
from glue_solar.sources.loaders.iris import QtIRISImporter, image_data, link_hpc, raster_data
from glue_solar.sources.loaders.lazy import LazyData
from glue_solar.sources.maps import read_sunpy_map
from glue_solar.sources.moments import line_moments
from glue_solar.tests.helpers import load_selected, mouse, scanned, select_point, shift
from glue_solar.tests.test_bursts import SI_IV
from glue_solar.tests.test_importer import _row
from glue_solar.tests.test_quicklook import (
    POINT_CURVES,
    SCAN,
    SNS,
    drifting_stack,
    marks,
    menu_action,
    readout,
    slit_jaw,
    time_series,
)
from glue_solar.tools import _pointing

SJI = "iris_l2_20210905_001833_3620258102_SJI_1330_t000.fits"


def twice(obj):
    """Yields ``obj`` saved in a session by glue and restored, then that restore saved and restored again."""
    for _ in range(2):
        obj = GlueUnSerializer.loads(GlueSerializer(obj).dumps()).object("__main__")
        yield obj


def assert_same_coordinates(coords, data, stride=1):
    """``coords`` give those of ``data`` at and between its pixels and back (every ``stride``-th), within 1e-9, and keep its offset."""
    grid = np.meshgrid(*[np.arange(n) for n in data.shape[::-1]], indexing="ij")
    for fraction in (0, 0.37):
        pixels = [axis + fraction for axis in grid]
        for got, expected in zip(coords.pixel_to_world_values(*pixels), data.coords.pixel_to_world_values(*pixels)):
            np.testing.assert_allclose(got, expected, rtol=0, atol=1e-9)
    world = data.coords.pixel_to_world_values(*[axis[(slice(None, None, stride),) * axis.ndim] for axis in grid])
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


def test_a_session_restores_the_links_link_hpc_gives_a_stack_and_a_map(tmp_path, irispy_test_files):
    sji = image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))
    times = sji[sji.id["Time"]].copy()
    times[3] = np.datetime64("NaT", "ns")  # a frame without a time, as in the gaps regrid_on_time leaves
    sji.update_components({sji.id["Time"]: times})
    stack, _ = drifting_stack(tmp_path, irispy_test_files)
    aia = read_sunpy_map(sunpy.data.test.get_test_filepath("aia_171_level1.fits"))  # linked with its units
    collection = DataCollection([sji, stack, aia])
    collection.add_link(link_hpc(collection))
    assert not glue_patches.needs_link_restore_workaround()  # glue-core 1.27.0 alone opens no such session
    scans = sji[stack.id["Scan"]]
    assert set(np.unique(np.delete(scans, 3, axis=0))) == {0, 1}
    assert np.isnan(scans[3]).all()
    for restored in twice(collection):
        np.testing.assert_array_equal(restored[0][restored[1].id["Scan"]], scans)
        assert link_hpc(restored) == []


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


def test_a_raster_held_in_memory_gives_its_bursts_and_radiance_once_restored(monkeypatch, irispy_test_files):
    monkeypatch.setattr("glue_solar.sources.loaders.iris.LAZY", False)  # its metadata restored as glue's dict
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SI_IV)])
    restored = [collection[0] for collection in twice(DataCollection([raster]))]
    assert type(restored[0].meta) is not type(raster.meta)
    labels = si_iv_bursts(raster, threshold=80)[0]["label"]
    radiance = raster[radiometric_calibration(raster)]
    for data in restored:
        np.testing.assert_array_equal(si_iv_bursts(data, threshold=80)[0]["label"], labels)
        np.testing.assert_array_equal(data[radiometric_calibration(data)], radiance)


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


def test_a_session_refers_to_the_files_the_browser_loads_and_opens_after_they_move(
    qtbot, monkeypatch, tmp_path, iris_tree
):
    shutil.copytree(iris_tree, tmp_path / "first" / "data")
    dialog = QtIRISImporter(tmp_path / "first" / "data")
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    tree = dialog.obs_tree
    stem = "iris_l2_{}_{}_{}".format(*OBS_A)
    row = next(
        tree.topLevelItem(i) for i in range(tree.topLevelItemCount()) if tree.topLevelItem(i).text(1) == OBS_A[2]
    )
    row.setCheckState(0, Qt.Checked)  # its slit-jaw image, AIA cutout and two raster windows
    dialog.stack.setChecked(True)  # of its two raster files
    load_selected(qtbot, dialog)
    app = GlueApplication()
    qtbot.addWidget(app)
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))  # not glue's modal dialog
    app.data_collection.extend(dialog.datasets)
    dialog.datasets[0].coords.pointing_offset = (1.5, -2.25)
    dialog.datasets[0].meta["rest_wavelength"] = 2796.35
    # with paths relative to the session file, the type glue's Export Session dialog starts with
    app.save_session(str(tmp_path / "first" / "session.glu"), absolute_paths=False)
    records = json.loads((tmp_path / "first" / "session.glu").read_text())
    logs = [(record["path"], dict(*record["kwargs"])) for record in records.values() if "LoadLog" in record["_type"]]
    files = [f"{stem}_raster_t000_r0000{r}.fits" for r in range(2)]
    raster = f"data/{MD5}{stem}_raster/{files[0]}"
    assert sorted(logs, key=str) == sorted(
        [
            (f"data/{MD5}{stem}_SJI_1400_t000.fits.gz", {}),
            (f"data/{MD5}{stem}_SDO/{stem.replace('iris', 'aia')}_171.fits", {}),
            (raster, {"files": files, "windows": ["C II 1336"], "stack": True}),
            (raster, {"files": files, "windows": ["Mg II k 2796"], "stack": True}),
        ],
        key=str,
    )
    # no values in the session: each component is its file's, a pixel or world coordinate, or derived from those
    components = [records[component] for data in dialog.datasets for _, component in records[data.label]["components"]]
    assert all(
        "log" in record or record["_type"].endswith(("CoordinateComponent", "DerivedComponent"))
        for record in components
    )
    # nor coordinates or metadata, which the files give, but for the offset and metadata added since
    assert not any(record["_type"].endswith("_GlueWCS") for record in records.values())
    meta = [records[data.label]["meta"]["contents"] for data in dialog.datasets]
    assert meta == [{"st__rest_wavelength": 2796.35}, {}, {}, {}]
    (tmp_path / "first").rename(tmp_path / "moved")
    restored = GlueApplication.restore_session(str(tmp_path / "moved" / "session.glu"), show=False)
    qtbot.addWidget(restored)
    monkeypatch.setattr(restored, "report_error", lambda message, detail: pytest.fail(detail))
    for data, expected in zip(restored.data_collection, dialog.datasets, strict=True):
        assert data.label == expected.label
        for cid, expected_cid in zip(data.components, expected.components, strict=True):
            if cid not in data.coordinate_components:
                np.testing.assert_array_equal(data[cid], expected[expected_cid])
        assert_same_coordinates(data.coords, expected)
        # glue's restore of a Data, with irispy's metadata and the class whose colour limits count the raw values
        assert type(data) is LazyData
        assert type(data.meta) is type(expected.meta)
        assert data.meta.keys() == expected.meta.keys()
        for key, value in data.meta.items():
            if isinstance(expected.meta[key], u.Quantity):
                assert value.unit == expected.meta[key].unit
            np.testing.assert_array_equal(value, expected.meta[key])
        assert data.style.preferred_cmap.name == expected.style.preferred_cmap.name
    # and a session saved from the restored one refers to them alike
    restored.save_session(str(tmp_path / "moved" / "again.glu"), absolute_paths=False)
    assert json.loads((tmp_path / "moved" / "again.glu").read_text()).keys() == records.keys()


def test_a_quicklook_session_stays_small_and_opens(qtbot, monkeypatch, tmp_path, iris_tree):
    def load(dialog):
        qtbot.addWidget(dialog)
        scanned(qtbot, dialog)
        _row(dialog, OBS_A[2]).setCheckState(0, Qt.Checked)
        dialog.stack.setChecked(True)
        load_selected(qtbot, dialog)
        return QDialog.Accepted

    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(iris_tree))
    monkeypatch.setattr(QtIRISImporter, "exec", load)
    browse_iris(app.session, app.data_collection)  # a quicklook of its slit-jaw image and two stacked windows
    app.save_session(str(tmp_path / "quicklook.glu"), absolute_paths=False)
    # its viewers, point and links: about 5 kB a dataset or viewer, whatever the data's size (33 kB for a full-size
    # quicklook of 4000255147's Si IV 1403 window and slit-jaw image)
    viewers = [viewer for tab in app.viewers for viewer in tab]
    assert (tmp_path / "quicklook.glu").stat().st_size < 8000 * (len(app.data_collection) + len(viewers))
    records = json.loads((tmp_path / "quicklook.glu").read_text())
    # nothing saved with its values
    assert not any(record["_type"].endswith("Component") and "data" in record for record in records.values())
    restored = GlueApplication.restore_session(str(tmp_path / "quicklook.glu"), show=False)
    qtbot.addWidget(restored)
    assert restored.tab_names == app.tab_names
    assert [[type(viewer) for viewer in tab] for tab in restored.viewers] == [
        [type(viewer) for viewer in tab] for tab in app.viewers
    ]
    assert [data.label for data in restored.data_collection] == [data.label for data in app.data_collection]
    [point], [expected] = restored.data_collection.subset_groups, app.data_collection.subset_groups
    assert (point.label, point.subset_state.slices) == ("Point", expected.subset_state.slices)


def slices(state):
    """An Image viewer's slices, a band (`AggregateSlice`) as its range, centre and function."""
    return [(s.slice, s.center, s.function.__name__) if isinstance(s, AggregateSlice) else s for s in state.slices]


def responses(app, tab=-1):
    """
    What the coordinator gives the quicklook in ``app``'s tab ``tab``, shown: its time master, edit subset and point,
    the panels the point drives, and each Image panel's slices and time sync; and the point's place on each slit-jaw
    image and its spectrum.
    """
    coord = coordinator(app.data_collection)
    [master] = coord.masters.values()
    given = [master.label, [group.label for group in app.session.edit_subset_mode.edit_subset], coord.point.slices]
    given.append([i for i, viewer in enumerate(app.viewers[tab]) if viewer in coord._owners.get(coord.group, ())])
    where = []
    for viewer in app.viewers[tab]:
        if isinstance(viewer, ProfileViewer):
            [layer] = [layer for layer in viewer.layers if layer.state.layer.label == "Point"]
            where.append(layer.state.profile[1])
        else:
            given.append((slices(viewer.state), coord.time_status(viewer)))
            where.append(coord.point_on(viewer) or ())
    return given, where


SNS_FILES = ("raster_t000_r00000", "SJI_1400_t000", "SJI_2796_t000")


@pytest.mark.parametrize("kind", ["sit-and-stare", "scanning"])
def test_a_restored_quicklook_keeps_its_time_master_and_follows_a_pixel_drag(
    qtbot, monkeypatch, tmp_path, irispy_test_files, kind
):
    if kind == "sit-and-stare":
        files = [find_irispy_test_file(irispy_test_files, SNS.format(name)) for name in SNS_FILES]
        datasets = [*raster_data(files[:1], ["Si IV 1403"]), *map(image_data, files[1:])]
    else:  # 3860258481 has no slit-jaw file
        datasets = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["C II 1336"])
        times = datasets[0][datasets[0].id["Time"]][:, 0, 0]
        datasets.append(slit_jaw(times[0] + np.arange(4) * (times[-1] - times[0]) / 3, datasets[0]))
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))  # not glue's modal dialog
    viewers = quicklook(app, datasets)
    menu_action(viewers["sji"][0], "Time master").trigger()
    viewers["sji"][0].state.slices = (2, 0, 0)
    qtbot.waitUntil(lambda: " · Δt " in readout(viewers["map"]))  # the raster follows
    app.save_session(str(tmp_path / "quicklook.glu"), absolute_paths=False)
    restored = GlueApplication.restore_session(str(tmp_path / "quicklook.glu"), show=False)
    qtbot.addWidget(restored)
    monkeypatch.setattr(restored, "report_error", lambda message, detail: pytest.fail(detail))
    for drag in (False, True):
        if drag:  # with the Pixel tool, on each quicklook's map
            for application in (app, restored):
                panel = application.viewers[-1][0]
                panel.toolbar.active_tool = "image:point_selection"
                for name, x in [("button_press", 1), ("motion_notify", 2), ("motion_notify", 3), ("button_release", 3)]:
                    mouse(panel, f"{name}_event", x, 10 + x)
            qtbot.waitUntil(lambda: app.viewers[-1][2].state.slices[1] == 13)  # the drag's end reaches the panels
        # once the restored quicklook's coordinator has synced it
        qtbot.waitUntil(lambda: responses(restored)[0] == responses(app)[0])
        for got, expected in zip(responses(restored)[1], responses(app)[1], strict=True):
            np.testing.assert_allclose(got, expected, rtol=1e-12)


def test_a_restored_quicklook_marks_its_master_exposure_again(qtbot, monkeypatch, tmp_path, irispy_test_files):
    files = [find_irispy_test_file(irispy_test_files, SNS.format(name)) for name in SNS_FILES[:2]]
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))  # not glue's modal dialog
    viewers = quicklook(app, [*raster_data(files[:1], ["Si IV 1403"]), image_data(files[1])])
    raster = viewers["map"].state.reference_data
    time_series(app, raster)
    viewers["spectrogram"].state.slices = (7, *viewers["spectrogram"].state.slices[1:])
    qtbot.waitUntil(lambda: marks(app, raster, 7))
    session = tmp_path / "quicklook.glu"
    app.save_session(str(session), absolute_paths=False)
    for step in (100, 50):  # opened, and that saved and opened again: one group, which follows the master
        opened = GlueApplication.restore_session(str(session), show=False)
        qtbot.addWidget(opened)
        monkeypatch.setattr(opened, "report_error", lambda message, detail: pytest.fail(detail))
        spectrogram = opened.viewers[-1][1]  # the quicklook's
        raster = spectrogram.state.reference_data
        spectrogram.state.slices = (step, *spectrogram.state.slices[1:])
        qtbot.waitUntil(lambda: marks(opened, raster, step))
        opened.save_session(str(session), absolute_paths=False)


def test_a_restored_quicklook_keeps_its_light_curves_where_they_were(qtbot, monkeypatch, tmp_path, irispy_test_files):
    files = [find_irispy_test_file(irispy_test_files, SNS.format(name)) for name in SNS_FILES[:2]]
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))  # not glue's modal dialog
    viewers = quicklook(app, [*raster_data(files[:1], ["Si IV 1403"]), image_data(files[1])])
    menu_action(viewers["map"], POINT_CURVES).trigger()

    def curves(app):
        return {
            data.label: (data[data.id["Time"]], data[data.id["Value"]], data.get_component("Value").units, data.meta)
            for data in app.data_collection
            if data.ndim == 1
        }

    saved = curves(app)
    assert len(saved) == 2
    session = tmp_path / "curves.glu"
    app.save_session(str(session), absolute_paths=False)
    opened = GlueApplication.restore_session(str(session), show=False)
    qtbot.addWidget(opened)
    monkeypatch.setattr(opened, "report_error", lambda message, detail: pytest.fail(detail))
    restored = curves(opened)
    assert restored.keys() == saved.keys()
    for label, (times, values, units, meta) in restored.items():
        np.testing.assert_array_equal(times, saved[label][0])
        np.testing.assert_array_equal(values, saved[label][1])
        assert (units, meta) == saved[label][2:]
    plot = opened.viewers[-1][-1]
    layers = [layer for layer in plot.layers if layer.layer.label in saved]
    assert len(layers) == 2
    assert all(layer.enabled and layer.state.line_visible for layer in layers)
    # the time master's exposure marks them again, and a click leaves them where they were
    spectrogram, raster_map = opened.viewers[-1][1], opened.viewers[-1][0]
    raster = spectrogram.state.reference_data
    spectrogram.state.slices = (7, *spectrogram.state.slices[1:])
    qtbot.waitUntil(lambda: marks(opened, raster, 7))
    [marker] = [group for group in opened.data_collection.subset_groups if group.label == "Master exposure"]
    assert marker.subset_state.att.parent.label in saved
    select_point(raster_map, 5, 3)
    [point] = opened.session.edit_subset_mode.edit_subset
    assert point.subset_state.slices[1] == slice(3, 4)
    qtbot.wait(400)
    for label, (_, values, *_) in curves(opened).items():
        np.testing.assert_array_equal(values, saved[label][1])


def links(collection):
    """``collection``'s links, each as its datasets' and components' labels, its function and a `_ScanAt`'s scans."""
    found = set()
    for link in collection.external_links:
        for member in link if isinstance(link, LinkCollection) else [link]:
            using = member.get_using()
            ids = [(cid.parent.label, cid.label) for cid in (*member.get_from_ids(), member.get_to_id())]
            found.add((type(link).__name__, *ids, using.__name__, tuple(getattr(using, "scans", ()))))
    return found


def shown(app):
    """Each viewer of each tab of ``app``: its slices, every layer's colormap and a Profile's axis, units and range."""
    given = []
    for tab in app.viewers:
        for viewer in tab:
            state = viewer.state
            if isinstance(viewer, ProfileViewer):
                given.append((state.x_att.label, state.x_display_unit, state.y_display_unit, state.x_min, state.x_max))
                continue
            cmaps = [getattr(layer.state, "cmap", None) for layer in viewer.layers]
            given.append((slices(state), [(cmap.name, cmap) for cmap in cmaps if cmap is not None]))
    return given


# glue averages the band over the NaN fill too, which numpy warns about
@pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")
def test_two_quicklooks_restore_twice_from_their_files(qtbot, monkeypatch, tmp_path, irispy_test_files, iris_tree):
    def load(dialog):
        qtbot.addWidget(dialog)
        scanned(qtbot, dialog)
        _row(dialog, OBS_A[2]).setCheckState(0, Qt.Checked)
        dialog.stack.setChecked(True)
        load_selected(qtbot, dialog)
        return QDialog.Accepted

    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))  # not glue's modal dialog
    # a sit-and-stare raster and two slit-jaw images, held in memory, and a stack and slit-jaw image of the
    # observation browser, read from their files as they are viewed
    files = [find_irispy_test_file(irispy_test_files, SNS.format(name)) for name in SNS_FILES]
    sns = quicklook(app, [*raster_data(files[:1], ["Si IV 1403"]), *map(image_data, files[1:])])
    menu_action(sns["sji"][0], "Time master").trigger()
    sns["sji"][0].state.slices = (2, 0, 0)
    qtbot.waitUntil(lambda: " · Δt " in readout(sns["map"]))  # the raster follows
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(iris_tree))
    monkeypatch.setattr(QtIRISImporter, "exec", load)
    browse_iris(app.session, app.data_collection)
    stack = app.viewers[-1]
    shift(monkeypatch, sns["map"].state.reference_data, app.data_collection, (1.5, -2.25))
    shift(monkeypatch, stack[0].state.reference_data, app.data_collection, (-0.5, 0.75))
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("5", True))
    sns["map"].toolbar.tools["solar:band"].activate()  # a band of five wavelengths
    sns["sji"][1].layers[0].state.cmap = cmlist["irissji1400"]
    stack[0].layers[0].state.cmap = colormaps["viridis"]
    sns["spectrum"].state.x_display_unit = "km / s"
    [spectrum, *_] = [viewer for viewer in stack if isinstance(viewer, ProfileViewer)]
    spectrum.state.x_display_unit = "nm"
    session = tmp_path / "first.glu"
    app.save_session(str(session), absolute_paths=False)
    restored = []
    for name in ("again.glu", "third.glu"):
        opened = GlueApplication.restore_session(str(session), show=False)
        qtbot.addWidget(opened)
        monkeypatch.setattr(opened, "report_error", lambda message, detail: pytest.fail(detail))
        restored.append(opened)
        session = tmp_path / name
        opened.save_session(str(session), absolute_paths=False)
    for opened in restored:
        assert opened.tab_names == app.tab_names
        for data, expected in zip(opened.data_collection, app.data_collection, strict=True):
            assert data.label == expected.label
            assert_same_coordinates(data.coords, expected, stride=7)  # inverting every pixel takes 25 s
            assert [data.get_component(cid).units for cid in data.main_components] == [
                expected.get_component(cid).units for cid in expected.main_components
            ]
            assert data.style.preferred_cmap.name == expected.style.preferred_cmap.name
            missing = set(expected.meta) - set(data.meta)
            if isinstance(expected, LazyData):  # irispy's, which its files give again
                assert type(data.meta) is type(expected.meta)
                assert not missing
            else:  # glue's dict, without irispy's Time and SkyCoord, of which bursts and calibration make irispy's
                assert missing <= {"auxiliary times", "exposure FOV center"}
            for key, value in data.meta.items():
                if isinstance(expected.meta[key], u.Quantity):
                    assert value.unit == expected.meta[key].unit
                np.testing.assert_array_equal(value, expected.meta[key])
        # iris_tree's scans share a time, so the scans the stack's links give are checked by
        # test_a_session_restores_the_links_link_hpc_gives_a_stack_and_a_map
        assert links(opened.data_collection) == links(app.data_collection)
        assert link_hpc(opened.data_collection) == []
        assert shown(opened) == shown(app)
    for tab in (1, 2):  # each quicklook, shown, and then dragged on with the Pixel tool on its map
        for application in (app, *restored):
            application.tab_widget.setCurrentIndex(tab)
        for drag in (False, True):
            if drag:
                before = responses(app, tab)[0]
                for application in (app, *restored):
                    panel = application.viewers[tab][0]
                    panel.toolbar.active_tool = "image:point_selection"
                    for name, x in [("button_press", 0), ("motion_notify", 1), ("button_release", 2)]:
                        mouse(panel, f"{name}_event", x, 1 + x)
                qtbot.waitUntil(lambda: responses(app, tab)[0] != before)  # the drag reaches the panels
            for opened in restored:  # once its coordinator has synced it
                qtbot.waitUntil(lambda: responses(opened, tab)[0] == responses(app, tab)[0])
                for got, expected in zip(responses(opened, tab)[1], responses(app, tab)[1], strict=True):
                    np.testing.assert_allclose(got, expected, rtol=1e-12)


def plugin_action(app, label):
    """The entry ``label`` of ``app``'s Plugins menu."""
    return next(action for action in app._actions["plugins"] if action.text() == label)


def test_a_quicklook_kept_as_glue_quits_restores_from_the_menu(qtbot, monkeypatch, tmp_path, iris_tree):
    def load(dialog):
        scanned(qtbot, dialog)
        _row(dialog, OBS_A[2]).setCheckState(0, Qt.Checked)
        dialog.stack.setChecked(True)
        load_selected(qtbot, dialog)
        return QDialog.Accepted

    monkeypatch.setattr(glue.config, "CFG_DIR", str(tmp_path / ".glue"))  # glue's settings folder, not the user's
    told = []
    monkeypatch.setattr(QMessageBox, "information", lambda parent, title, text: told.append(text))
    glue_solar.setup()
    # qtbot is given only the window left open: glue-qt deletes a window as it closes, with its dialogs, and pytest-qt
    # cannot close a deleted one
    app = GlueApplication()
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))  # not glue's modal dialog
    plugin_action(app, "Restore last session").trigger()
    assert told == ["No session kept yet: glue-solar keeps one as glue's window closes with data."]
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(iris_tree))
    monkeypatch.setattr(QtIRISImporter, "exec", load)
    browse_iris(app.session, app.data_collection)  # a quicklook of its slit-jaw image and two stacked windows
    expected = app.tab_names, [[type(viewer) for viewer in tab] for tab in app.viewers]
    labels = [data.label for data in app.data_collection]
    app.show()
    app.close()  # as File → Quit does
    records = json.loads((tmp_path / ".glue" / "glue-solar-last-session.glu").read_text())
    paths = [record["path"] for record in records.values() if "LoadLog" in record["_type"]]
    assert len(paths) == len(labels)
    assert all(map(os.path.isabs, paths))  # its files, wherever glue starts
    fresh = GlueApplication()
    plugin_action(fresh, "Restore last session").trigger()
    restored = fresh._new_application  # as File → Open Session gives it, closing ``fresh``
    qtbot.addWidget(restored)
    monkeypatch.setattr(restored, "report_error", lambda message, detail: pytest.fail(detail))
    assert (restored.tab_names, [[type(viewer) for viewer in tab] for tab in restored.viewers]) == expected
    assert [data.label for data in restored.data_collection] == labels


@pytest.mark.parametrize("kind", ["empty", "values over 1 MB", "over 1 MB", "unserializable", "unwritable"])
def test_a_session_glue_cannot_keep_leaves_the_last_one(qtbot, monkeypatch, tmp_path, caplog, kind):
    monkeypatch.setattr(glue.config, "CFG_DIR", str(tmp_path))
    last = tmp_path / "glue-solar-last-session.glu"
    last.write_text("the session before")
    glue_solar.setup()
    app = GlueApplication()  # not given to qtbot, which cannot close it once glue-qt has deleted it as it closed
    values = {
        "values over 1 MB": np.random.default_rng(0).random(150_000),  # 1.2 MB of values, not encoded
        "over 1 MB": np.random.default_rng(0).random(100_000),  # 0.8 MB of values, 1.07 MB encoded
        "unserializable": da.ones(3),  # as data regridded on time from data read as they are viewed
        "unwritable": np.ones(3),
    }
    if kind in values:
        app.data_collection.append(Data(x=values[kind], label="x"))
    if kind == "unwritable":

        def replace(*args):
            raise PermissionError("read-only")

        monkeypatch.setattr(os, "replace", replace)
    app.show()
    app.close()
    assert [path.name for path in tmp_path.glob("*.glu")] == [last.name]  # nor a temporary file
    assert last.read_text() == "the session before"
    logged = [record.getMessage() for record in caplog.records if "last session" in record.getMessage()]
    assert len(logged) == (kind != "empty")
    reasons = {
        "values over 1 MB": "MB of values, over 1 MB",
        "over 1 MB": "MB, over 1 MB",
        "unserializable": "serialize dask.array",
        "unwritable": "read-only",
    }
    assert all(reasons[kind] in message for message in logged)
