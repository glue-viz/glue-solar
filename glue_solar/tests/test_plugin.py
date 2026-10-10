import gc
import inspect
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import glue.utils.matplotlib
import matplotlib.dates as mdates
import numpy as np
import pytest
from echo import delay_callback
from glue.config import (
    colormaps,
    data_factory,
    fit_plugin,
    layer_action,
    menubar_plugin,
    settings,
    startup_action,
    viewer_tool,
)
from glue.core import Data
from glue.core.component import DerivedComponent
from glue.core.data_factories import load_data
from glue.core.link_helpers import LinkSame
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue.core.units import UnitConverter
from glue.plugins.tools.path_slicer.path_sliced_data_links import PathRelativeLink
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.viewers.image.state import AggregateSlice
from glue.viewers.profile.state import ProfileViewerState
from glue_qt.app.application import GlueApplication
from glue_qt.app.layer_tree_widget import UserAction
from glue_qt.config import keyboard_shortcut
from glue_qt.viewers.histogram import HistogramViewer
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.image.profile_viewer_tool import ProfileViewerTool
from glue_qt.viewers.profile import ProfileViewer
from glue_qt.viewers.scatter import ScatterViewer
from glue_qt.viewers.table import TableViewer
from irispy.io import read_files
from irispy.io.sji import read_sji_lvl2
from matplotlib.backend_bases import KeyEvent, MouseButton, MouseEvent
from matplotlib.backends.backend_qt import NavigationToolbar2QT
from qtpy.QtCore import Qt
from qtpy.QtGui import QDesktopServices, QKeySequence
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QCheckBox, QDialog, QFileDialog, QInputDialog, QToolBar

import astropy.units as u
from astropy import constants
from astropy.coordinates import angular_separation
from astropy.io import fits
from astropy.table import QTable, Table
from astropy.time import Time
from astropy.visualization import PowerStretch
from astropy.visualization.wcsaxes import WCSAxes
from astropy.wcs import WCS

import glue_solar
from glue_solar import glue_patches
from glue_solar.conftest import MD5, OBS_A, find_irispy_test_file
from glue_solar.fitters import GaussianConstantFitter
from glue_solar.lines import rest_wavelength_iris
from glue_solar.quicklook import QuicklookImageViewer, _role, _wavelengths
from glue_solar.regrid import north_up_iris, rebin_iris, regrid_iris, regrid_on_time
from glue_solar.sources.bursts import bursts_iris
from glue_solar.sources.calibration import radiometric_calibration_iris, remove_dust_iris
from glue_solar.sources.doppler import doppler_iris
from glue_solar.sources.iris import (
    help_iris,
    iris_quicklook,
    is_iris_fits,
    link_iris,
    quicklook_iris,
    shift_pointing_iris,
)
from glue_solar.sources.line_ratio import line_ratio_iris
from glue_solar.sources.loaders.iris import _GlueWCS, image_data, link_hpc, raster_data
from glue_solar.sources.maps import read_sunpy_map
from glue_solar.sources.mg_features import mg_features_iris
from glue_solar.sources.moments import line_moments, mean_spectrum_iris, moments_iris
from glue_solar.sources.red_blue import red_blue_iris
from glue_solar.tests.helpers import count_tick_work, mouse, press, raster_point_on_sji
from glue_solar.tests.test_lazy import RASTER, SJI
from glue_solar.tests.test_quicklook import drifting_stack
from glue_solar.tools import PathData, sky_length


def test_setup_registers_hooks():
    glue_solar.setup()
    glue_solar.setup()  # glue calls it once; tests and reloads must not duplicate the tool
    assert "IRIS: browse observations…" in [label for label, _ in menubar_plugin]
    assert ("IRIS: link helioprojective coordinates", link_iris) in list(menubar_plugin)
    assert ("IRIS: quicklook…", quicklook_iris) in list(menubar_plugin)
    assert ("IRIS: user guide and issues", help_iris) in list(menubar_plugin)
    assert ("IRIS: restore last session", glue_solar.restore_last_session) in list(menubar_plugin)
    assert startup_action.members["iris_quicklook"] is iris_quicklook
    # the data actions by data kind: the spectral analyses, the image actions, then the coordinates
    ours = [(item.label, item.callback) for item in layer_action if item.callback.__module__[:10] == "glue_solar"]
    assert ours == [
        ("IRIS: set rest wavelength…", rest_wavelength_iris),
        ("IRIS: radiometric calibration", radiometric_calibration_iris),
        ("IRIS: subtract mean spectrum", mean_spectrum_iris),
        ("IRIS: line moments…", moments_iris),
        ("IRIS: Doppler image…", doppler_iris),
        ("IRIS: red-blue asymmetry…", red_blue_iris),
        ("IRIS: Mg II features… (Mg II)", mg_features_iris),
        ("IRIS: detect UV bursts… (Si IV, SJI 1400)", bursts_iris),
        ("IRIS: line ratio diagnostic…", line_ratio_iris),
        ("IRIS: remove dust (SJI)", remove_dust_iris),
        ("IRIS: north up (SJI, AIA, SOT)", north_up_iris),
        ("IRIS: regrid on time (sit-and-stare, stack, SJI, AIA, SOT)", regrid_iris),
        ("IRIS: rebin…", rebin_iris),
        ("IRIS: shift pointing…", shift_pointing_iris),
    ]
    for tool in ("solar:coordinate", "solar:modes", "solar:view"):
        assert ImageViewer.tools.count(tool) == 1
    assert ProfileViewer.tools.count("solar:lines") == ProfileViewer.tools.count("solar:velocity") == 1
    assert ProfileViewer.tools.index("solar:main_window") == 0  # right after glue's Home, Pan and Zoom
    assert ImageViewer.tools.count("solar:follow_lock") == ImageViewer.tools.count("image:point_selection") == 1
    assert ImageViewer.subtools["solar:modes"] == ["solar:measure", "solar:path", "solar:path_crosshair", "solar:slope"]
    view = ["solar:frame_time", "solar:hide_axes", "solar:per_frame_limits", "solar:band", "solar:physical_aspect"]
    view += ["solar:zoom_1_1", "solar:colour_bar"]
    if not hasattr(ImageViewer, "cursor_status"):
        view.append("solar:cursor_readout")
    assert ImageViewer.subtools["solar:view"] == view
    shown = ImageViewer.tools + [tool for tools in ImageViewer.subtools.values() for tool in tools]
    shortcuts = [viewer_tool.members[tool].shortcut for tool in shown]
    assert len(set(shortcuts) - {None}) == len(shortcuts) - shortcuts.count(None)  # glue-qt drops a repeated one
    assert ImageViewer.subtools["save"].count("solar:save_sequence") == 1
    assert ProfileViewer.subtools["save"].count("solar:save_profile") == 1
    # glue's Matplotlib viewers share one list
    assert "solar:save_sequence" not in ProfileViewer.subtools["save"]
    for viewer in (ImageViewer, ScatterViewer, HistogramViewer):
        assert "solar:save_profile" not in viewer.subtools["save"]
    iris = next(f for f in data_factory if f.label == "IRIS Level 2 FITS")
    for label in ("FITS file", "sunpy Map"):  # both also match IRIS files; ours must win
        other = next(f for f in data_factory if f.label == label)
        assert iris.priority > (other.priority or 0)


def test_data_actions_show_only_for_the_data_they_take(qtbot, irispy_test_files, iris_tree):
    """Each data action is offered only where its own guard takes the data selected."""
    windows = ["C II 1336", "Si IV 1403", "Mg II k 2796"]
    sns = raster_data([find_irispy_test_file(irispy_test_files, RASTER)], windows)  # sit-and-stare
    scans = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    [scanning] = raster_data(scans[:1], ["C II 1336"])
    [stack] = raster_data(scans, ["Mg II k 2796"], stack=True)
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    sot = image_data(next(p for p in irispy_test_files if "Gband" in p.name))
    aia = image_data(next(iris_tree.rglob("aia_l2_*.fits")))
    maps = line_moments(sns[1], 1402.77)
    plain = Data(label="plain table", x=[1.0, 2.0])
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([*sns, scanning, stack, sji, sot, aia, maps, plain])
    group = app.data_collection.new_subset_group()
    raster = [
        "IRIS: set rest wavelength…",
        "IRIS: radiometric calibration",
        "IRIS: subtract mean spectrum",
        "IRIS: line moments…",
        "IRIS: Doppler image…",
        "IRIS: red-blue asymmetry…",
    ]
    mg_ii, bursts = "IRIS: Mg II features… (Mg II)", "IRIS: detect UV bursts… (Si IV, SJI 1400)"
    ratio, dust, north_up = "IRIS: line ratio diagnostic…", "IRIS: remove dust (SJI)", "IRIS: north up (SJI, AIA, SOT)"
    regrid = "IRIS: regrid on time (sit-and-stare, stack, SJI, AIA, SOT)"
    rebin, shift = "IRIS: rebin…", "IRIS: shift pointing…"
    expected = [
        ([plain], []),
        ([sns[0]], [*raster, regrid, rebin, shift]),  # sit-and-stare C II
        ([sns[1]], [*raster, bursts, regrid, rebin, shift]),  # Si IV
        ([sns[2]], [*raster, mg_ii, regrid, rebin, shift]),  # Mg II k
        ([scanning], [*raster, rebin, shift]),  # scanning C II: not on time
        ([stack], [*raster, mg_ii, regrid, rebin, shift]),
        ([sji], [bursts, dust, north_up, regrid, rebin, shift]),  # 1400
        ([sot], [north_up, regrid, rebin, shift]),
        ([aia], [north_up, regrid, rebin, shift]),
        ([maps], [ratio, shift]),
        ([group], []),
        ([sns[0], sji], []),
        ([maps, sns[1]], [ratio]),
    ]
    installed = UserAction._can_trigger is glue_patches.user_action_can_trigger
    assert installed == glue_patches.needs_layer_action_applies_workaround()  # probes glue-qt's own registry
    tree = app._layer_widget.ui.layerTree
    labels = [action.label for action in layer_action if action.callback.__module__[:10] == "glue_solar"]
    for layers, shown in expected:
        tree.set_selected_layers(layers)
        assert [a.text() for a in tree.actions() if a.text() in labels and a.isVisible()] == shown, layers[0].label


_QT_5_IMPORT = """
import sys

import qtpy

qtpy.QT6, qtpy.API_NAME = False, "PyQt5"
try:
    import glue_solar
except RuntimeError:
    print(*[name for name in sys.modules if name.startswith("glue_solar")], "|")
"""


def test_import_refuses_qt_5_before_anything_registers():
    # in a process of its own, as glue_solar is imported here
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    result = subprocess.run([sys.executable, "-c", _QT_5_IMPORT], env=env, capture_output=True, text=True)
    assert result.stdout == "|\n", result.stderr[-2000:]
    # glue logs a plugin that fails to load only at info level, which it does not show
    assert re.search(r"glue-solar needs Qt 6 \(PyQt6\), not PyQt5 .* set QT_API=pyqt6", result.stderr)


_PLUGIN_LOAD = """
import sys

import glue_solar

glue_solar.setup()
# and the Profile fitter's astropy.modeling to the first Profile viewer
print(
    *[name for name in ("irispy", "sunpy.map", "ndcube", "fiasco", "spectral_cube", "astropy.modeling") if name in sys.modules],
    "|",
)

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


def test_data_factory_claims_only_iris_files_and_aligned_aia_cutouts(iris_tree):
    import sunpy.data.test

    d, t, o = OBS_A
    sji = iris_tree / f"{MD5}iris_l2_{d}_{t}_{o}_SJI_1400_t000.fits.gz"
    aia = iris_tree / f"{MD5}iris_l2_{d}_{t}_{o}_SDO" / f"aia_l2_{d}_{t}_{o}_171.fits"
    assert is_iris_fits(str(sji))
    assert is_iris_fits(str(aia))  # by name and INSTRUME, as the browser takes them: TELESCOP is blank
    assert not is_iris_fits(sunpy.data.test.get_test_filepath("aia_171_level1.fits"))  # a sunpy Map
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


@pytest.mark.remote_data
def test_open_real_aia_cutout_through_load_data(irispy_data):
    [path] = [
        p for p in irispy_data("iris_l2_20250519_165924_3640107442_cutout_SDO.tar.gz") if p.endswith("_1700.fits")
    ]
    data, browser = load_data(path), image_data(path)  # File -> Open gives what the observation browser loads
    assert isinstance(data.coords, _GlueWCS)
    assert data.label == browser.label == "1700-3640107442-2025-05-19T16:59:24"
    assert [cid.label for cid in data.components] == [cid.label for cid in browser.components]
    np.testing.assert_array_equal(data[data.id["Time"]], browser[browser.id["Time"]])
    assert _role(data) == "aia"
    assert regrid_on_time(data).meta["time_step"] == pytest.approx(24, abs=0.01)  # as it times a slit-jaw image


@pytest.mark.parametrize(
    ("name", "label", "units", "cmap"),
    [
        ("_Gband4305_FG_", "G band 4305-3603259402-2015-08-30T07:09:53", "DN", "hinodesotintensity"),
        ("_TFNaI5896_MG_", "TF Na I 5896-3680100932-2016-01-08T19:12:11", "", "gray"),
        ("_blapp_index_", "6302A B_LOS 18:50:06-3680100932-2016-01-08T19:12:11", "G", "gray"),
    ],
)
def test_open_sot_cube_through_load_data(tmp_path, irispy_test_files, name, label, units, cmap):
    # Hinode/SOT cubes of IRIS Technical Note 32 load as AIA cutouts do, in their own unit
    [source] = [path for path in irispy_test_files if name in path.name]
    path = shutil.copy2(source, tmp_path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].data[0, 0, 0] = -200  # IRIS's fill code, a value in a SOT cube
    data, cube = load_data(path), read_sji_lvl2(path)
    assert isinstance(data.coords, _GlueWCS)
    assert (data.label, data.style.preferred_cmap.name) == (label, cmap)
    assert _role(data) == "aia"  # which follows the time as an AIA cutout
    science = data.get_component(data.main_components[0])
    assert science.units == units
    assert (science.data[0, 0, 0], data[f"{label} mask"][0, 0, 0]) == (-200, 0)
    np.testing.assert_array_equal(science.data, cube.data)  # NaN where missing, and negative fields kept
    assert (data.find_component_id(f"{label} DN/s") is not None) == (units == "DN")
    sky, times = cube.axis_world_coords()  # each frame at its own pointing
    np.testing.assert_array_equal(data["Time"][:, 0, 0], times.utc.to_value("datetime64"))
    for axis, expected in (("Longitude", sky.Tx), ("Latitude", sky.Ty)):
        np.testing.assert_allclose(data[f"Helioprojective {axis}"], expected.to_value(u.arcsec), rtol=0, atol=1e-9)


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
    other.figure.canvas.draw()  # WCSAxes only formats positions once drawn
    assert other.axes.format_coord(1, 1).endswith(" (world) · 2020-01-01T12:00:00.000 UTC")  # the mouse-over readout


@pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")  # glue's Collapse of the NaN beside the image
def test_frame_time_tool_survives_an_empty_collapse(qtbot):
    glue_solar.setup()
    cube = Data(label="cube", flux=np.zeros((4, 5, 6)), obs_date=np.full((4, 5, 6), np.datetime64("2020-01-01T12:00:00")))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(cube)
    viewer = app.new_data_viewer(ImageViewer, data=cube)
    tool = viewer.toolbar.tools["solar:frame_time"]
    viewer.state.slices = (AggregateSlice(slice(2, 2), 2, np.nanmean), 0, 0)  # sample 2 (`glue_patches`)
    assert tool.label.text() == "2020-01-01T12:00:00.000 UTC"


@pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")  # glue's Collapse of the NaN beside the image
def test_an_empty_collapse_range_draws(qtbot):
    installed = AggregateSlice.__init__ is glue_patches.aggregate_slice_init
    assert installed == glue_patches.needs_empty_collapse_workaround()  # probes glue's own image buffer
    glue_solar.setup()
    cube = Data(label="cube", flux=np.arange(120.0).reshape(4, 5, 6))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(cube)
    viewer = app.new_data_viewer(ImageViewer, data=cube)
    viewer.state.slices = (AggregateSlice(slice(2, 2), 2, np.nanmean), 0, 0)  # a Profile Collapse inside sample 2
    viewer.figure.canvas.draw()  # glue 1.27.0 alone raises here, and in every later draw
    assert viewer.state.slices[0].slice == slice(2, 3)


def test_readout_gives_arcsec_only_where_wcsaxes_shows_arcsec(qtbot):
    import sunpy.data.test

    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    # an AIA map, whose FITS WCS gives a longitude just west of 0 as nearly 360°
    aia = read_sunpy_map(sunpy.data.test.get_test_filepath("aia_171_level1.fits"))
    app.data_collection.append(aia)
    viewer = app.new_data_viewer(ImageViewer, data=aia)
    viewer.figure.canvas.draw()
    for x in (2, 100):  # east and west of 0
        position = aia.coords.pixel_to_world(x, 60)
        assert viewer.axes.format_coord(x, 60) == f'{position.Tx.arcsec:.2f}" {position.Ty.arcsec:.2f}" (world)'
    # a right ascension, a Carrington longitude and a wavelength in metres keep WCSAxes' own text
    for ctype in (("RA---TAN", "DEC--TAN"), ("CRLN-CEA", "CRLT-CEA"), ("WAVE", "LINEAR")):
        wcs = WCS(naxis=2)
        wcs.wcs.ctype, wcs.wcs.crval = ctype, (150, 2)
        image = Data(label=ctype[0], flux=np.zeros((10, 10)), coords=wcs)
        app.data_collection.append(image)
        viewer = app.new_data_viewer(ImageViewer, data=image)
        viewer.figure.canvas.draw()
        assert viewer.axes.format_coord(3, 4) == viewer.axes._display_world_coords(3, 4)  # WCSAxes' readout


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


def test_toolbar_menus_hold_the_mouse_modes_and_display_tools(qtbot, monkeypatch):
    glue_solar.setup()
    # the band dialog picks 5 wavelength pixels, then 1
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args: (args[3][1 - args[4]], True))
    app = GlueApplication()
    qtbot.addWidget(app)
    wcs = WCS(naxis=3)
    wcs.wcs.ctype[2] = "WAVE"  # along the slider, for the band
    times = np.full((3, 4, 5), np.datetime64("2013-09-02T16:39:35"))  # for the frame time, after the flux
    cube = Data(label="cube", flux=np.arange(60.0).reshape(3, 4, 5), time=times, coords=wcs)
    app.data_collection.append(cube)
    viewer = app.new_data_viewer(ImageViewer, data=cube)
    toolbar = viewer.toolbar
    assert len(QToolBar.actions(toolbar)) <= 21  # of 26 buttons before, which needed a viewer 1200 px wide
    # glue-solar's buttons right after glue's Home, Pan and Zoom, so that a narrow viewer hides glue's tools first
    ids = {id(action): tool_id for tool_id, action in toolbar.actions.items()}
    order = [ids.get(id(action)) for action in QToolBar.actions(toolbar)]
    ours = ["solar:follow_lock", "solar:modes", "solar:coordinate", "solar:view"]
    assert order[: len(ours) + 5] == ["save", "window", "mpl:home", "mpl:pan", "mpl:zoom", *ours]
    # every menu button's tooltip and its entries' show on hover, glue's Save and Window too, and glue's Profile
    # viewer button gets one
    for menu in ("save", "window", "solar:modes", "solar:coordinate", "solar:view"):
        button = toolbar.widgetForAction(toolbar.actions[menu])
        assert button.toolTip() == toolbar.tools[menu].tool_tip
        assert button.menu().toolTipsVisible()
    assert toolbar.actions["profile-viewer"].toolTip() == ProfileViewerTool.tool_tip != ""

    def entries(menu):
        """Every entry of ``menu`` and of its submenus, and whether each menu shows tooltips."""
        for entry in menu.actions():
            yield entry, menu.toolTipsVisible()
            if entry.menu() is not None:
                yield from entries(entry.menu())

    for menu in ours[1:]:
        for entry, tips in entries(toolbar.widgetForAction(toolbar.actions[menu]).menu()):
            assert tips
            assert entry.toolTip() not in ("", entry.text())  # glue-qt's default tooltip, the text
    # glue-solar's save entries after glue's
    save = toolbar.widgetForAction(toolbar.actions["save"]).menu()
    assert [entry.text() for entry in save.actions()][-2:] == [
        "Save Python script to reproduce plot",
        "Save frames or movie…",
    ]
    menus = {}
    for menu in ("solar:modes", "solar:view"):
        menus[menu] = toolbar.widgetForAction(toolbar.actions[menu]).menu()
        # each tool's entry, by its id as for a button, and Path diagram's path entries and sampling
        entries = [toolbar.actions[tool] for tool in ImageViewer.subtools[menu]]
        extra = ["Save path as ECSV…", "Open path from ECSV…", "Path on other data…", "Path sampling"]
        extra = extra if menu == "solar:modes" else []
        assert menus[menu].actions()[: len(entries)] == entries
        assert [entry.text() for entry in menus[menu].actions()[len(entries) :]] == extra
    sampling = menus["solar:modes"].actions()[-1]
    assert sampling.text() == "Path sampling"

    # the mouse modes, checked while on, the crosshair, Slope and saving a path on a path diagram only, placing one
    # on other data once one is drawn, and Path diagram's L
    shown = [entry.isVisible() for entry in menus["solar:modes"].actions()]
    assert shown == [True, True, False, False, False, True, False, True]
    toolbar.active_tool = "image:point_selection"
    measure = toolbar.actions["solar:measure"]
    measure.trigger()
    assert (toolbar.active_tool, measure.isChecked()) == (toolbar.tools["solar:measure"], True)
    toolbar.active_tool = "image:point_selection"
    assert not measure.isChecked()
    app.show()
    toolbar.setFocus()
    qtbot.waitUntil(toolbar.hasFocus)  # as a button's key, while the toolbar has the keyboard
    QTest.keyClick(toolbar, Qt.Key_L)
    assert (toolbar.active_tool, toolbar.actions["solar:path"].isChecked()) == (toolbar.tools["solar:path"], True)

    # the display tools, checked while on, leaving the mouse mode on
    toolbar.active_tool = "image:point_selection"
    pixel = toolbar.active_tool
    for tool_id in ImageViewer.subtools["solar:view"]:
        tool, entry = toolbar.tools[tool_id], toolbar.actions[tool_id]
        assert entry.isCheckable() == (tool_id != "solar:zoom_1_1")
        for _ in range(2):
            was = getattr(tool, "checked", None)
            entry.trigger()
            menus["solar:view"].aboutToShow.emit()
            assert toolbar.active_tool is pixel
            if entry.isCheckable():
                assert entry.isChecked() == tool.checked != was
    # the band only while the wavelength has a slider
    viewer.state.x_att = cube.pixel_component_ids[0]
    assert not toolbar.actions["solar:band"].isEnabled()
    viewer.state.x_att = cube.pixel_component_ids[2]
    assert toolbar.actions["solar:band"].isEnabled()

    # no L while Path diagram is off, as on a 2D image, which has no wavelength band or time either
    still = Data(label="still", flux=np.ones((4, 5)))
    app.data_collection.append(still)
    viewer.add_data(still)
    viewer.state.reference_data = still
    assert not toolbar.actions["solar:path"].isEnabled()
    assert not sampling.isVisible()
    assert not toolbar.actions["solar:band"].isEnabled()
    assert not toolbar.actions["solar:frame_time"].isEnabled()
    QTest.keyClick(toolbar, Qt.Key_L)
    assert toolbar.active_tool is pixel


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
        assert '" (world) · ' in shown.axes.format_coord(10, 20)  # arcsec, then the frame's time
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
        assert '" (world) · ' in viewer.axes.format_coord(10, 20)
    full = shown.axes.format_coord(10.3, 20.7)
    for viewer in (shown, hidden):
        viewer.state.x_min, viewer.state.x_max, viewer.state.y_min, viewer.state.y_max = 10, 11, 20, 21
        viewer.figure.canvas.draw()
    assert hidden.axes.format_coord(10.3, 20.7) == shown.axes.format_coord(10.3, 20.7) == full  # whatever the zoom


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


def test_sessions_with_per_frame_limits_fail_to_restore(qtbot, tmp_path):
    # glue 1.27.0 restores a layer's per-frame limits before it has a viewer (wp0-core-session-reports), as the user
    # guide says; once a glue release restores them, this fails and the guide changes
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    cube = Data(label="cube", flux=np.arange(60.0).reshape(3, 4, 5))
    app.data_collection.append(cube)
    app.new_data_viewer(ImageViewer, data=cube).toolbar.actions["solar:per_frame_limits"].trigger()
    app.save_session(str(tmp_path / "limits.glu"))
    with pytest.raises(AttributeError, match="add_callback"):
        GlueApplication.restore_session(str(tmp_path / "limits.glu"))


def test_colour_bar_draws_glues_colours_and_is_saved(qtbot, monkeypatch, tmp_path):
    import matplotlib
    from matplotlib.backends.qt_compat import QtWidgets
    from matplotlib.image import imread

    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    # every row of the first frame runs from 0 to 100 in the 256 steps of the bar, of the second from 0 to 200
    ramp = np.linspace(0, 100, 256)
    cube = Data(label="cube", flux=np.stack([np.tile(ramp, (4, 1)), np.tile(2 * ramp, (4, 1))]))
    app.data_collection.append(cube)
    viewer = app.new_data_viewer(ImageViewer, data=cube)
    layer = viewer.state.layers[0]
    layer.v_min, layer.v_max = 0, 100
    paths = iter(tmp_path / name for name in ("off.png", "on.png"))
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *args: (str(next(paths)), ""))
    monkeypatch.setitem(matplotlib.rcParams, "savefig.directory", str(tmp_path))  # which saving changes
    menu = viewer.toolbar.widgetForAction(viewer.toolbar.actions["save"]).menu()
    [save] = [action for action in menu.actions() if action.text() == "Save plot to file"]  # mpl:save
    save.trigger()

    viewer.toolbar.active_tool = "image:point_selection"
    pixel, button = viewer.toolbar.active_tool, viewer.toolbar.actions["solar:colour_bar"]
    tool, width = viewer.toolbar.tools["solar:colour_bar"], viewer.axes.get_window_extent().width
    button.trigger()
    assert viewer.toolbar.active_tool is pixel
    beside = viewer.axes.get_window_extent().width
    assert beside < width  # the bar's room

    def drawn():
        """The bar's colours, glue's colours of a row of the image, and the bar's value limits."""
        viewer.figure.canvas.draw()
        return np.asarray(tool.bar.images[0].get_array())[:, 0], viewer.axes._composite()[0], tool.bar.get_ylim()

    bar = drawn()[0]
    layer.contrast, layer.bias, layer.cmap = 1.5, 0.3, matplotlib.colormaps["viridis"]
    for stretch in ("linear", "log", "sqrt", "arcsinh", "gamma_2.2"):
        layer.stretch = stretch
        colours, image, limits = drawn()
        assert (np.array_equal(colours, image), limits) == (True, (0, 100))
        assert not np.array_equal(colours, bar)  # changed with the stretch, contrast and bias or colormap
        bar = colours
    viewer.state.color_mode = "One color per layer"
    colours, image, limits = drawn()
    assert (np.array_equal(colours, image), limits) == (True, (0, 100))
    viewer.state.color_mode = "Colormaps"
    # the limits of each frame, from glue's per-frame limits
    viewer.toolbar.actions["solar:per_frame_limits"].trigger()
    layer.percentile = 100
    for frame, top in ((1, 200), (0, 100)):
        viewer.state.slices = (frame, 0, 0)
        colours, image, limits = drawn()
        assert (np.array_equal(colours, image), limits) == (True, (0, top))
    layer.v_min, layer.v_max = 20, 80
    assert drawn()[2] == (20, 80)
    layer.v_min = 80  # a constant frame's limits
    assert drawn()[2] == (76, 84)
    layer.v_min = 20

    save.trigger()
    off, on = (imread(tmp_path / name) for name in ("off.png", "on.png"))
    assert off.shape == on.shape
    # the bar's colours at its place in the file, whose pixels are the window's at the figure's dpi
    x0, y0, x1, y1 = tool.bar.get_window_extent().extents
    saved = on[int(on.shape[0] - y1) + 2 : int(on.shape[0] - y0) - 2, int(x0) + 1 : int(x1) - 1]
    assert len(np.unique(saved.reshape(-1, 4), axis=0)) > 100
    button.trigger()
    assert not tool.bar.get_visible()
    assert viewer.axes.get_window_extent().width > beside


def generated_map():
    """A raster map of 30 steps of 2″ along a slit of 300 pixels of 0.33″, rolled by 10°."""
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = "HPLN-TAN", "HPLT-TAN"
    wcs.wcs.cunit = "arcsec", "arcsec"
    roll = np.deg2rad(10)
    wcs.wcs.cd = np.array([[np.cos(roll), -np.sin(roll)], [np.sin(roll), np.cos(roll)]]) @ np.diag([2.0, 0.33])
    wcs.wcs.crpix = 15.5, 150.5
    wcs.wcs.crval = 100.0, -200.0
    return Data(label="map", flux=np.zeros((300, 30)), coords=wcs)


def sky_square(viewer, side=10):
    """
    The lengths on screen, in screen pixels, of the sides of a ``side``″ square of sky about the view centre, along
    its longitude and along its latitude, placed with the reference data's own coordinates.
    """
    state = viewer.state
    data, x, y = state.reference_data, state.x_att.axis, state.y_att.axis
    coords, last = data.coords, data.ndim - 1  # WCS axes run in reverse
    kinds = coords.world_axis_physical_types
    lon, lat = (next(i for i, kind in enumerate(kinds) if kind.endswith(end)) for end in (".lon", ".lat"))
    pixel = [float(s) for s in state.slices[::-1]]
    pixel[last - x], pixel[last - y] = (state.x_min + state.x_max) / 2, (state.y_min + state.y_max) / 2
    centre = coords.pixel_to_world_values(*pixel)
    half = (side / 2 * u.arcsec).to_value(coords.world_axis_units[lon])
    ends = []
    for axis in (lon, lat):
        for sign in (-1, 1):
            world = list(centre)
            world[axis] = world[axis] + sign * half
            end = coords.world_to_pixel_values(*world)
            ends.append((end[last - x], end[last - y]))
    a, b, c, d = viewer.axes.transData.transform(ends)
    return np.hypot(*(b - a)), np.hypot(*(d - c))


@pytest.mark.parametrize(
    "source",
    [
        None,  # generated_map: 6:1
        # 4000005156 scan 0, Si IV 1403: 2″ steps along a slit of 0.17″ pixels, about 12:1
        pytest.param(
            "iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz", marks=pytest.mark.remote_data
        ),
        # 3400109360: 1″ steps along a slit of 0.33″ pixels, about 3:1
        pytest.param("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz", marks=pytest.mark.remote_data),
    ],
)
def test_physical_aspect_draws_a_square_of_sky_square(qtbot, request, source):
    from glue_solar.tests.helpers import mouse

    glue_solar.setup()
    if source is None:
        data, x, y = generated_map(), 1, 0
    else:  # real rasters, whose step axis is a -TAB lookup table
        paths = request.getfixturevalue("irispy_data")(source)
        [data] = raster_data(paths if isinstance(paths, list) else [paths])
        x, y = 0, 1
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    state = viewer.state
    state.x_att, state.y_att = data.pixel_component_ids[x], data.pixel_component_ids[y]  # step against slit
    state.aspect = "auto"  # as on a quicklook raster panel, which shows the whole image
    state.reset_limits()
    app.show()  # for resizes to reach the canvas

    def resize(width, height):
        viewer.viewer_size = (width, height)
        box = viewer.axes.get_window_extent
        qtbot.waitUntil(lambda: (box().width > box().height) == (width > height))

    def square():
        width, height = sky_square(viewer)
        return abs(width / height - 1) < 0.05

    def square_pixels():  # glue's 'Square Pixels'
        return (state.y_max - state.y_min) / (state.x_max - state.x_min) == pytest.approx(viewer.axes_ratio, rel=1e-3)

    def pan(dx):
        with delay_callback(state, "x_min", "x_max"):
            state.x_min, state.x_max = state.x_min + dx, state.x_max + dx

    resize(600, 400)
    assert not square()
    viewer.toolbar.active_tool = "image:point_selection"
    pixel, button = viewer.toolbar.active_tool, viewer.toolbar.actions["solar:physical_aspect"]
    button.trigger()  # leaving the mouse mode on, which glue-qt ends for a plain button
    assert (state.aspect, viewer.toolbar.active_tool) == ("equal", pixel)
    assert square()
    nx, ny = data.shape[x], data.shape[y]
    assert state.x_min <= -0.5 < nx - 0.5 <= state.x_max  # the whole image still shows
    assert state.y_min <= -0.5 < ny - 0.5 <= state.y_max

    resize(300, 700)
    assert square()

    shown = (state.x_max - state.x_min, state.y_max - state.y_min)
    viewer.toolbar.active_tool = "mpl:zoom"  # glue's Zoom: a drag across the middle of the axes
    for name, corner in (("button_press_event", (0.3, 0.3)), ("button_release_event", (0.6, 0.5))):
        mouse(viewer, name, *viewer.axes.transData.inverted().transform(viewer.axes.transAxes.transform(corner)))
    assert state.x_max - state.x_min < shown[0]
    assert state.y_max - state.y_min < shown[1]
    assert square()

    state.x_att, state.y_att = data.pixel_component_ids[y], data.pixel_component_ids[x]  # slit against step
    assert square()
    assert (state.x_min, state.x_max) == (-0.5, ny - 0.5) or (state.y_min, state.y_max) == (-0.5, nx - 0.5)  # fitted

    button.trigger()  # back to glue's aspect, filling the axes with the image again
    assert state.aspect == "auto"
    assert (state.x_min, state.x_max, state.y_min, state.y_max) == (-0.5, ny - 0.5, -0.5, nx - 0.5)
    assert not square()

    state.x_att, state.y_att = data.pixel_component_ids[x], data.pixel_component_ids[y]  # off, it stays off
    button.trigger()
    assert state.aspect == "equal"
    assert square()

    state.aspect = "auto"  # 'Automatic' in the viewer's options switches it off too,
    state.aspect = "equal"  # and 'Square Pixels' then gives square pixels
    assert square_pixels()

    pan(nx)  # the view centre past the last step, where -TAB rasters have no coordinates
    button.trigger()  # from 'Square Pixels', as on a slit-jaw viewer,
    pan(-nx)
    assert square()
    button.trigger()  # and back to them
    assert state.aspect == "equal"
    assert square_pixels()


def test_physical_aspect_is_the_same_all_along_a_raster(qtbot, irispy_test_files):
    # pointing jitter makes 3860258481's 2″ steps differ by up to 2.6 % from one to the next
    data = raster_data([find_irispy_test_file(irispy_test_files, SCANNING)])[0]
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    state = viewer.state
    state.x_att, state.y_att = data.pixel_component_ids[0], data.pixel_component_ids[1]  # step against slit
    state.aspect = "auto"
    button = viewer.toolbar.actions["solar:physical_aspect"]
    proportions = []
    for step in (0, 2):  # zoomed on steps 0 and 1, 1.994″ apart, then on steps 2 and 3, 2.047″ apart
        with delay_callback(state, "x_min", "x_max"):
            state.x_min, state.x_max = step - 0.5, step + 1.5
        button.trigger()
        proportions.append((state.y_max - state.y_min) / (state.x_max - state.x_min))
        button.trigger()
    assert proportions[0] == pytest.approx(proportions[1], rel=1e-3)


def test_physical_aspect_stands_aside_without_glues_aspect_hooks(qtbot, monkeypatch):
    from glue_solar import tools

    glue_solar.setup()
    monkeypatch.setattr(tools, "_ASPECT_HOOKS", (*tools._ASPECT_HOOKS, "_renamed_in_a_later_glue"))
    app = GlueApplication()
    qtbot.addWidget(app)
    image = Data(label="image", flux=np.arange(20.0).reshape(4, 5))
    app.data_collection.append(image)
    viewer = app.new_data_viewer(ImageViewer, data=image)  # the viewer still opens
    viewer.toolbar.actions["solar:physical_aspect"].trigger()  # and the button does nothing
    assert viewer.toolbar.tools["solar:physical_aspect"].ratio is None
    viewer.close(warn=False)


@pytest.mark.parametrize("case", ["spectrogram", "sit-and-stare exposures", "slit-jaw x–t", "no WCS"])
def test_physical_aspect_gives_square_pixels_off_the_sky(qtbot, irispy_test_files, case):
    def bundled(name):
        return find_irispy_test_file(irispy_test_files, name)

    # the dataset and its x and y pixel axes: wavelength, exposures or time against the slit or x, or no coordinates
    data, x, y = {
        "spectrogram": (lambda: raster_data([bundled(SCANNING)])[0], 2, 1),
        # exposures of one place, which the pointing and the solar rotation move by a fraction of a slit pixel
        "sit-and-stare exposures": (lambda: raster_data([bundled(SIT_AND_STARE.format("raster_t000_r00000"))])[0], 0, 1),
        "slit-jaw x–t": (lambda: image_data(bundled(SIT_AND_STARE.format("SJI_1400_t000"))), 2, 0),
        "no WCS": (lambda: Data(label="cube", flux=np.zeros((8, 40, 50))), 2, 1),
    }[case]
    data = data()
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    state = viewer.state
    state.x_att, state.y_att = data.pixel_component_ids[x], data.pixel_component_ids[y]
    state.aspect = "auto"
    viewer.toolbar.actions["solar:physical_aspect"].trigger()
    assert state.aspect == "equal"
    assert (state.y_max - state.y_min) / (state.x_max - state.x_min) == pytest.approx(viewer.axes_ratio, rel=1e-3)


def _separation(lon, lat, unit):
    """The great-circle angle in arcsec between two world positions, longitudes ``lon`` and latitudes ``lat``."""
    return angular_separation(lon[0] * unit, lat[0] * unit, lon[1] * unit, lat[1] * unit).to_value(u.arcsec)


def test_measure_reports_a_dragged_line(qtbot, irispy_test_files):
    data = image_data(find_irispy_test_file(irispy_test_files, SIT_AND_STARE.format("SJI_1400_t000")))
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    viewer.state.slices = (5, 0, 0)
    viewer.toolbar.active_tool = "solar:measure"
    tool = viewer.toolbar.tools["solar:measure"]
    mouse(viewer, "button_press_event", 3, 4)
    mouse(viewer, "motion_notify_event", 30, 35)
    assert tool._line.get_visible()  # drawn while dragging
    mouse(viewer, "button_release_event", 30, 35)
    (x0, x1), (y0, y1) = tool._line.get_data()  # the ends, at the screen pixels the mouse was on
    # the oracle: the dataset's own coordinates at both ends, in frame 5, at the observer's distance
    lon, lat, _ = data.coords.pixel_to_world_values([x0, x1], [y0, y1], [5, 5])
    arcsec = _separation(lon, lat, u.arcsec)
    km = (arcsec * u.arcsec).to_value(u.rad) * data.meta["DSUN_OBS"] / 1000
    text = f'Length {np.hypot(x1 - x0, y1 - y0):.1f} px · {arcsec:.2f}" · {km:,.0f} km'
    assert tool.label.text() == text
    mouse(viewer, "motion_notify_event", 10, 10)  # the line stays until the next drag
    assert tool.label.text() == text
    viewer.toolbar.actions["solar:hide_axes"].trigger()  # and through glue-solar's buttons
    assert viewer.toolbar.active_tool is tool
    assert tool._line.get_visible()
    assert tool.label.text() == text

    viewer.state.y_att = data.pixel_component_ids[0]  # x against time: not the line's axes, then pixels only
    assert not tool._line.get_visible()
    assert tool.label.text() == ""
    mouse(viewer, "button_press_event", 3, 1)
    mouse(viewer, "button_release_event", 30, 20)
    (x0, x1), (y0, y1) = tool._line.get_data()
    assert tool.label.text() == f"Length {np.hypot(x1 - x0, y1 - y0):.1f} px (no sky length here)"

    viewer.toolbar.active_tool = None  # another mouse mode, or none, ends it
    assert not tool._line.get_visible()
    assert tool.label.isHidden()


def test_sky_length_of_a_map_in_degrees_without_an_observer_distance(qtbot):
    data = generated_map()  # an astropy WCS gives degrees; no DSUN_OBS
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    x, y = [2, 25, 25], [10, 280, 100]
    pixels, arcsec, km = sky_length(viewer, x, y)
    lon, lat = data.coords.pixel_to_world_values(x, y)
    expected = sum(_separation(lon[i : i + 2], lat[i : i + 2], u.deg) for i in (0, 1))
    assert (pixels, arcsec, km) == (pytest.approx(np.hypot(23, 270) + 180), pytest.approx(expected), None)


def test_sky_length_on_a_raster_map(qtbot, irispy_test_files):
    data = raster_data([find_irispy_test_file(irispy_test_files, SCANNING)])[0]
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    viewer.state.x_att, viewer.state.y_att = data.pixel_component_ids[0], data.pixel_component_ids[1]  # step, slit
    _, lat, lon = data.coords.pixel_to_world_values([0, 0], [10, 90], [0, 7])  # IRIS rasters: wavelength, lat, lon
    assert sky_length(viewer, [0, 7], [10, 90])[1] == pytest.approx(_separation(lon, lat, u.arcsec))
    # a -TAB raster has no coordinates past its outer steps
    assert sky_length(viewer, [-1, 3], [10, 90])[1:] == (None, None)


@pytest.mark.remote_data
def test_measure_on_a_full_size_slit_jaw_image(qtbot, irispy_data):
    # 4000255147 SJI 1400: 0.16635" pixels, seen from 1.50921e11 m
    data = image_data(irispy_data("iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz"))
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    viewer.toolbar.active_tool = "solar:measure"
    tool = viewer.toolbar.tools["solar:measure"]
    for name, x in (("press", 100), ("release", 200)):  # a line of exactly 100 pixels
        getattr(tool, name)(SimpleNamespace(button=MouseButton.LEFT, inaxes=viewer.axes, xdata=x, ydata=200))
    pixels, arcsec, km = sky_length(viewer, [100, 200], [200, 200])
    lon, lat, _ = data.coords.pixel_to_world_values([100, 200], [200, 200], [0, 0])
    assert abs(arcsec - _separation(lon, lat, u.arcsec)) < 0.01
    assert arcsec == pytest.approx(16.635, abs=0.01)
    assert km == pytest.approx(12172, rel=1e-3)
    assert tool.label.text() == f'Length 100.0 px · {arcsec:.2f}" · 12,172 km'


def test_zoom_1_1_gives_a_data_pixel_a_screen_pixel(qtbot, irispy_test_files):
    data = raster_data([find_irispy_test_file(irispy_test_files, SCANNING)])[0]
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    app.show()  # for the resize to reach the canvas
    viewer.viewer_size = (600, 400)
    box = viewer.axes.bbox  # in screen pixels
    qtbot.waitUntil(lambda: box.width > box.height)
    state, button = viewer.state, viewer.toolbar.actions["solar:zoom_1_1"]
    viewer.toolbar.active_tool = "image:point_selection"
    pixel = viewer.toolbar.active_tool
    # step against slit, slit against step, and wavelength against slit; 'Automatic' and 'Square Pixels'
    for x, y, aspect in ((0, 1, "auto"), (1, 0, "equal"), (2, 1, "equal")):
        state.x_att, state.y_att = data.pixel_component_ids[x], data.pixel_component_ids[y]
        state.aspect = aspect
        centre = ((state.x_min + state.x_max) / 2, (state.y_min + state.y_max) / 2)
        for _ in range(2):  # and again, at 1:1 already
            button.trigger()
            assert viewer.toolbar.active_tool is pixel
            assert (state.x_max - state.x_min, state.y_max - state.y_min) == pytest.approx((box.width, box.height))
            assert ((state.x_min + state.x_max) / 2, (state.y_min + state.y_max) / 2) == pytest.approx(centre)
    # with 'Physical aspect', a y pixel spans the sky's proportion of an x pixel
    state.x_att, state.y_att = data.pixel_component_ids[0], data.pixel_component_ids[1]
    viewer.toolbar.actions["solar:physical_aspect"].trigger()
    ratio = viewer.toolbar.tools["solar:physical_aspect"].ratio
    assert ratio != pytest.approx(1)
    for _ in range(2):
        button.trigger()
        assert (state.x_max - state.x_min, state.y_max - state.y_min) == pytest.approx((box.width, box.height / ratio))
    # a screen pixel is a device pixel: on a HiDPI screen the view spans twice the data pixels
    width = box.width
    viewer.figure.canvas._set_device_pixel_ratio(2)
    button.trigger()
    assert state.x_max - state.x_min == pytest.approx(box.width) == pytest.approx(2 * width)


def _key(viewer, key):
    canvas = viewer.figure.canvas
    canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", canvas, key))


def _draw_path(viewer, x, y):
    """Click the vertices ``x, y`` with the Path diagram tool and press Enter; the diagrams it makes."""
    viewer.toolbar.active_tool = "solar:path"
    for vx, vy in zip(x, y):
        mouse(viewer, "button_press_event", vx, vy)
        mouse(viewer, "button_release_event", vx, vy)
    _key(viewer, "enter")
    return viewer.toolbar.tools["solar:path"]._traces[-1]


def _along(data, cid, path, on=slice(None)):
    """
    ``data``'s ``cid`` at the pixels glue-core samples the samples ``on`` of ``path`` at, its other axes kept in order,
    the path's last.
    """
    index = [slice(None)] * data.ndim
    columns = []
    for index[path.cid_x.axis], index[path.cid_y.axis] in zip(path.x[on].astype(int), path.y[on].astype(int)):
        columns.append(data[cid, tuple(index)])
    return np.stack(columns, axis=-1)


def test_path_diagrams_of_a_slit_jaw_image_and_a_raster_on_it(qtbot, irispy_test_files):
    sji = image_data(find_irispy_test_file(irispy_test_files, SIT_AND_STARE.format("SJI_1400_t000")))
    raster_file = find_irispy_test_file(irispy_test_files, SIT_AND_STARE.format("raster_t000_r00000"))
    [raster] = raster_data([raster_file], ["Si IV 1403"])
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([sji, raster])
    app.data_collection.add_link(link_hpc(app.data_collection))
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    viewer.add_data(raster)
    viewer.state.slices = (5, 0, 0)
    assert viewer.toolbar.tools["solar:path"].enabled
    path, on_raster = _draw_path(viewer, [5, 18, 30], [3, 20, 35])
    diagrams = viewer.toolbar.tools["solar:path"]._slice_viewer
    assert [layer.layer for layer in diagrams.layers] == [path]  # the raster's, on frames, would be disabled
    assert {path, on_raster} <= set(app.data_collection)
    # frames against the path, and wavelength against the same samples
    n = len(path.x)
    assert path.shape == (sji.shape[0], n)
    assert on_raster.shape == (raster.shape[2], n)
    for cid in (sji.main_components[0], sji.id["Time"]):
        np.testing.assert_array_equal(path[cid], _along(sji, cid, path))
    assert path[sji.id["Time"]].dtype.kind == "M"

    # the raster samples lie where the path's do, through the raster's coordinates and frame 5's, and are NaN off it
    on = np.isfinite(on_raster.x)
    assert 0 < on.sum() < n
    position = {on_raster.cid_x.axis: on_raster.x[on], on_raster.cid_y.axis: on_raster.y[on]}  # exposure, slit
    x, y = raster_point_on_sji(raster, sji, position[0], position[1], frame=5)
    assert np.hypot(x - path.x[on], y - path.y[on]).max() < 0.5
    flux = raster.main_components[0]
    np.testing.assert_array_equal(on_raster[flux][:, on], _along(raster, flux, on_raster, on))
    assert np.isnan(on_raster[flux][:, ~on]).all()

    # the crosshair: along the diagram it marks the path and moves the slit-jaw image to the frame
    diagrams.toolbar.active_tool = "solar:path_crosshair"
    mouse(diagrams, "button_press_event", 3, 10)
    mouse(diagrams, "motion_notify_event", 10, 40)
    assert viewer.state.slices[0] == 40
    crosshair = diagrams.toolbar.tools["solar:path_crosshair"]._crosshair
    assert crosshair.get_data() == ([path.x[10]], [path.y[10]])
    mouse(diagrams, "button_release_event", 10, 40)
    # the diagram's readout gives the frame's time
    when = sji[sji.id["Time"], (40, int(path.y[10]), int(path.x[10]))]
    assert np.datetime_as_string(when, unit="ms") in diagrams.axes.format_coord(10, 40)


def test_path_diagram_of_a_stack_on_a_slit_jaw_image(qtbot, tmp_path, irispy_test_files):
    sji = image_data(find_irispy_test_file(irispy_test_files, SIT_AND_STARE.format("SJI_1400_t000")))
    stack, alone = drifting_stack(tmp_path, irispy_test_files)
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([sji, stack])
    app.data_collection.add_link(link_hpc(app.data_collection))
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    viewer.add_data(stack)
    flux = stack.main_components[0]
    for frame, scan in ((0, 0), (sji.shape[0] - 1, 1)):
        viewer.state.slices = (frame, 0, 0)
        path, on_stack = _draw_path(viewer, [5, 18, 30], [3, 20, 35])
        # scans and wavelength against the path, its steps and slit rows placed with the pointing of the scan nearest
        # the frame's time, by its middle step
        assert on_stack.shape == (stack.shape[0], stack.shape[3], len(path.x))
        on = np.isfinite(on_stack.x)
        assert on.sum() >= 5
        offsets = []
        for k in (scan, 1 - scan):  # from the path's samples, of the stack's placed through each scan on its own
            x, y = raster_point_on_sji(alone[k], sji, on_stack.x[on], on_stack.y[on], frame)
            offsets.append(np.hypot(x - path.x[on], y - path.y[on]).max())
        assert offsets[0] < 0.5 < 1 < offsets[1]
        np.testing.assert_array_equal(on_stack[flux][..., on], _along(stack, flux, on_stack, on))


def test_path_diagram_of_a_stack(qtbot, irispy_test_files):
    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    [stack] = raster_data(files, ["Si IV 1403"], stack=True)
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(stack)
    viewer = app.new_data_viewer(ImageViewer, data=stack)
    viewer.state.x_att, viewer.state.y_att = stack.pixel_component_ids[1], stack.pixel_component_ids[2]  # step, slit
    viewer.state.slices = (1, 0, 0, 12)
    assert viewer.toolbar.tools["solar:path"].enabled  # 4D, which glue-core's is not
    [path] = _draw_path(viewer, [0.5, 3, 6.5], [10, 60, 100])
    # scans and wavelength against the path, with the stack's own wavelengths and scans
    assert path.shape == (stack.shape[0], stack.shape[3], len(path.x))
    flux = stack.main_components[0]
    np.testing.assert_array_equal(path[flux], _along(stack, flux, path))
    assert path.coords.world_axis_names == ["Offset", "Wavelength", "Scan"]
    wavelength = path.world_component_ids[1]
    np.testing.assert_allclose(path[wavelength][0, :, 0], stack[stack.world_component_ids[3]][0, 0, 0, :])
    app.new_data_viewer(ProfileViewer, data=path).figure.canvas.draw()  # its profile, along its own wavelengths

    # the crosshair moves the wavelength only, which the diagram's y axis shows
    diagrams = viewer.toolbar.tools["solar:path"]._slice_viewer
    assert not diagrams.toolbar.tools["solar:path"].enabled  # a diagram, 3D too, is not a dataset to draw on
    diagrams.toolbar.active_tool = "solar:path_crosshair"
    mouse(diagrams, "button_press_event", 2, 3)
    mouse(diagrams, "motion_notify_event", 2, 7)
    assert viewer.state.slices == (1, 0, 0, 7)


def test_path_diagram_sampling_on_a_ramp(qtbot):
    # a ramp, which bilinear sampling gives exactly, against scipy's map_coordinates: order 0, the nearest pixel, and
    # order 1, NaN where a pixel around the sample is off the data
    from scipy.ndimage import map_coordinates

    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    t, y, x = np.indices((2, 12, 16), dtype=float)
    times = np.datetime64("2013-09-02T16:39") + (60 * t).astype("timedelta64[s]")
    ramp = Data(label="ramp", flux=0.7 * x - 1.3 * y + 2.5 + 10 * t)
    ramp.add_component(times, "Time")
    app.data_collection.append(ramp)
    viewer = app.new_data_viewer(ImageViewer, data=ramp)
    menu = viewer.toolbar.widgetForAction(viewer.toolbar.actions["solar:modes"]).menu().actions()[-1].menu()
    assert [(entry.text(), entry.isChecked()) for entry in menu.actions()] == [
        ("Truncate", True),
        ("Nearest", False),
        ("Linear", False),
    ]
    flux = ramp.id["flux"]
    for count, (entry, order, mode) in enumerate(zip(menu.actions()[1:], (0, 1), ("grid-constant", "constant")), 1):
        entry.trigger()
        assert viewer.toolbar.active_tool is None  # the mouse mode stays
        [path] = _draw_path(viewer, [0.3, 7.7, 15.3], [2.2, 10.9, 4.6])
        sampling = entry.text().lower()
        assert (path.sampling, path.label) == (sampling, f"ramp [slice {count}, {sampling}]")
        frames = np.broadcast_to(np.arange(2.0)[:, None], (2, len(path.x)))
        # times are not interpolated: the nearest pixel's
        np.testing.assert_array_equal(path[ramp.id["Time"]], times[:, 0, :1].repeat(len(path.x), axis=1))
        if order:  # the ramp itself, NaN past the last x centre, where the last sample is
            assert path.x[-1] > 15
            ramp_values = np.where(path.x <= 15, 0.7 * path.x - 1.3 * path.y + 2.5 + 10 * frames, np.nan)
            np.testing.assert_allclose(path[flux], ramp_values, atol=1e-6)
        # the drawn diagram, which glue asks for by index arrays
        view = [(0, 1, 2), (0, len(path.x) - 1, len(path.x))]
        drawn = path.compute_fixed_resolution_buffer(view, target_data=path, target_cid=flux)
        np.testing.assert_array_equal(drawn, path[flux])
        for xs, ys in ((path.x, path.y), ([0.5, 1.5, 2.5, 3.5], [2.5] * 4)):  # then halfway, which rounds up
            path.set_xy(xs, ys)
            frames = np.broadcast_to(np.arange(2.0)[:, None], (2, len(path.x)))
            pixels = [frames, np.broadcast_to(path.y, frames.shape), np.broadcast_to(path.x, frames.shape)]
            reference = map_coordinates(ramp[flux], pixels, order=order, mode=mode, cval=np.nan)
            np.testing.assert_allclose(path[flux], reference, atol=1e-6)


def _click(tool, x, y):
    """Click ``x, y`` with the mouse mode ``tool``, exactly, where a mouse event lands on a screen pixel."""
    event = SimpleNamespace(button=MouseButton.LEFT, inaxes=tool.viewer.axes, x=0, y=0, xdata=x, ydata=y, key=None)
    tool.press(event)
    tool.release(event)


def test_slope_recovers_an_injected_features_speed_and_acceleration(qtbot):
    # a slit-jaw-like cube of 0.1663" pixels seen from 1 AU, 60 frames 12 s apart, in which a blob moves along x from
    # 50 km/s, accelerating at 100 m/s²
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    observer, seconds = 1.496e11, 12.0 * np.arange(60)
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = "HPLN-TAN", "HPLT-TAN", ""
    wcs.wcs.cunit = "arcsec", "arcsec", ""
    wcs.wcs.cdelt = 0.1663, 0.1663, 1
    wcs.wcs.crpix, wcs.wcs.crval = (280, 5, 1), (400, -300, 0)
    km = (0.1663 * u.arcsec).to_value(u.rad) * observer / 1000  # a pixel's
    centre = 20 + (50 * seconds + 0.1 / 2 * seconds**2) / km
    _, y, x = np.indices((60, 9, 560))
    cube = Data(label="cube", flux=100 * np.exp(-((x - centre[:, None, None]) ** 2 + (y - 4) ** 2) / 8), coords=wcs)
    times = np.datetime64("2013-09-02T16:39:35") + (1000 * seconds).astype("timedelta64[ms]")
    cube.add_component(np.broadcast_to(times[:, None, None], cube.shape), "Time")
    cube.meta["DSUN_OBS"] = observer
    app.data_collection.append(cube)
    viewer = app.new_data_viewer(ImageViewer, data=cube)
    [path] = _draw_path(viewer, [0.3, 559], [4, 4])
    diagram = viewer.toolbar.tools["solar:path"]._slice_viewer
    tool = diagram.toolbar.tools["solar:slope"]
    assert (tool.enabled, viewer.toolbar.tools["solar:slope"].enabled) == (True, False)  # on diagrams only
    diagram.toolbar.active_tool = "solar:slope"

    # the ridge, clicked as a user would: each frame's brightest sample, to a fraction of a sample, as the log of a
    # Gaussian is a parabola through its three brightest
    values, frames = path[cube.id["flux"]], np.arange(60)
    peak = values.argmax(axis=1)
    left, middle, right = (np.log(values[frames, peak + i]) for i in (-1, 0, 1))
    ridge = peak + (left - right) / (2 * (left - 2 * middle + right))
    for frame in frames[::6]:
        _click(tool, ridge[frame], frame)
    _key(diagram, "enter")
    table = path.slopes
    assert table.label == "cube [slice 1] slopes"
    assert (table["t0 (UTC)"][0], table["t1 (UTC)"][0]) == ("2013-09-02T16:39:35.000", "2013-09-02T16:50:23.000")
    assert table["d0 (km)"][0] == pytest.approx(20 * km)  # from the path's first sample, at pixel 0
    assert table["speed (km/s)"][0] == pytest.approx(50, rel=0.01)
    assert table["acceleration (m/s²)"][0] == pytest.approx(100, rel=0.02)
    assert tool.label.text() == "Speed 50.00 km/s · acceleration 100.0 m/s²"
    [shown] = [viewer for tab in app.viewers for viewer in tab if isinstance(viewer, TableViewer)]
    assert diagram.toolbar.active_tool is tool  # still on, for the next track

    # two points give the mean speed between them, a row more in the Table viewer
    _click(tool, ridge[-1], 59)  # from the track's end
    _click(tool, ridge[0], 0)
    _key(diagram, "enter")
    assert table["t0 (UTC)"][1] < table["t1 (UTC)"][1]
    assert table["speed (km/s)"][1] == pytest.approx(50 + 0.1 * seconds[-1] / 2, rel=0.01)
    assert np.isnan(table["acceleration (m/s²)"][1])
    assert shown.model.rowCount() == 2

    # points at one time give none, and Esc clears them
    _click(tool, 10, 3)
    _click(tool, 200, 3)
    assert tool.label.text() == "No speed here"
    _key(diagram, "enter")
    assert table.shape == (2,)
    _click(tool, 10, 3)
    _key(diagram, "escape")
    assert (tool.label.text(), tool.roi().to_polygon()) == ("", ([], []))


def _modes_entry(viewer, text):
    """The entry ``text`` of the viewer's pencil menu."""
    menu = viewer.toolbar.widgetForAction(viewer.toolbar.actions["solar:modes"]).menu()
    return next(action for action in menu.actions() if action.text() == text)


def _assert_same_diagram(got, expected):
    """The diagram ``got`` has the parent, path, sampling, values and coordinates of ``expected``."""
    assert (got.original_data.label, got.sampling) == (expected.original_data.label, expected.sampling)
    np.testing.assert_array_equal(np.stack([got.x, got.y]), np.stack([expected.x, expected.y]))
    for cid, original in zip(got.components, expected.components, strict=True):
        assert cid.label == original.label
        np.testing.assert_array_equal(got[cid], expected[original])


def test_a_path_diagram_reopens_from_ecsv_and_from_a_session(qtbot, monkeypatch, tmp_path):
    # a slit-jaw-like cube of 0.1663" pixels seen from 1 AU, with times, and another dataset on its pixels
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = "HPLN-TAN", "HPLT-TAN", ""
    wcs.wcs.cunit = "arcsec", "arcsec", ""
    wcs.wcs.cdelt = 0.1663, 0.1663, 1
    wcs.wcs.crpix, wcs.wcs.crval = (8, 6, 1), (400, -300, 0)
    rng = np.random.default_rng(0)
    cube = Data(label="cube", flux=rng.random((3, 12, 16)), coords=wcs)
    times = np.datetime64("2013-09-02T16:39:35") + np.arange(3) * np.timedelta64(12, "s")
    cube.add_component(np.broadcast_to(times[:, None, None], cube.shape), "Time")
    cube.meta["DSUN_OBS"] = 1.496e11
    other = Data(label="other", flux=rng.random((3, 12, 16)))
    app.data_collection.extend([cube, other])
    for cid, same in zip(cube.pixel_component_ids, other.pixel_component_ids, strict=True):
        app.data_collection.add_link(LinkSame(cid, same))
    viewer = app.new_data_viewer(ImageViewer, data=cube)
    viewer.add_data(other)
    viewer.toolbar.tools["solar:path"].sampling = "linear"
    path, on_other = _draw_path(viewer, [0.3, 15.3], [4.6, 4.6])  # along x
    diagram = viewer.toolbar.tools["solar:path"]._slice_viewer
    entries = ("Save path as ECSV…", "Open path from ECSV…")
    # saved from a diagram, opened where a path is drawn
    assert [_modes_entry(shown, text).isVisible() for shown in (diagram, viewer) for text in entries] == [
        True,
        False,
        False,
        True,
    ]

    # its samples in the cube's pixels and on the sky, 0.1663" and 120.6 km apart
    file = str(tmp_path / "path.ecsv")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (file, ""))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (file, ""))
    _modes_entry(diagram, entries[0]).trigger()
    table = QTable.read(file)
    assert dict(table.meta) == {"data": "cube", "axes": [2, 1], "sampling": "linear"}
    np.testing.assert_array_equal(np.stack([table["x"], table["y"]]), np.stack([path.x, path.y]))
    lon, lat, _ = wcs.pixel_to_world_values(path.x, path.y, 0)
    np.testing.assert_allclose(table["lon"].to_value(u.arcsec), lon * 3600, rtol=0, atol=1e-6)
    np.testing.assert_allclose(table["lat"].to_value(u.arcsec), lat * 3600, rtol=0, atol=1e-6)
    np.testing.assert_allclose(table["distance"].to_value(u.arcsec), 0.1663 * np.arange(len(table)), rtol=1e-6)
    assert table["distance_km"][1].to_value(u.km) == pytest.approx(120.6143, rel=1e-6)
    # opened on the cube, it makes the same diagrams again, with the saved sampling
    viewer.toolbar.tools["solar:path"].sampling = "truncate"
    _modes_entry(viewer, entries[1]).trigger()
    again, again_on_other = viewer.toolbar.tools["solar:path"]._traces[-1]
    assert again.label == "cube [slice 2, linear]"
    for got, expected in ((again, path), (again_on_other, on_other)):
        _assert_same_diagram(got, expected)

    # a session, saved and restored twice, gives the diagrams, their viewer, a region on one and the link between
    # their paths
    box = RoiSubsetState(path.pixel_component_ids[1], path.pixel_component_ids[0], RectangularROI(2, 9, -1, 1.5))
    app.data_collection.new_subset_group("box", box)
    mask = path.subsets[0].to_mask()
    assert 0 < mask.sum() < mask.size
    session = str(tmp_path / "path.glu")
    for _ in range(2):
        app.save_session(session)
        app = GlueApplication.restore_session(session)
        qtbot.addWidget(app)
        restored = {data.label: data for data in app.data_collection if isinstance(data, PathData)}
        assert list(restored) == [path.label, on_other.label, again.label, again_on_other.label]
        for expected in (path, on_other):
            got = restored[expected.label]
            _assert_same_diagram(got, expected)
            assert all(cid.parent is got for cid in got.pixel_component_ids + got.world_component_ids)
        [shown] = [shown for tab in app.viewers for shown in tab if shown.state.reference_data is restored[path.label]]
        assert shown.state.x_att is restored[path.label].pixel_component_ids[1]
        shown.figure.canvas.draw()
        np.testing.assert_array_equal(restored[path.label].subsets[0].to_mask(), mask)
        links = [link for link in app.data_collection.external_links if isinstance(link, PathRelativeLink)]
        pairs = {(link._slice_from, link._slice_to) for link in links}
        assert (restored[on_other.label], restored[path.label]) in pairs
    # opened on the restored cube, numbered past its restored diagrams
    [image] = [shown for tab in app.viewers for shown in tab if shown.state.reference_data.label == "cube"]
    _modes_entry(image, entries[1]).trigger()
    assert image.toolbar.tools["solar:path"]._traces[-1][0].label == "cube [slice 3, linear]"


def _sky_cube(label, shape, axes, pc=None):
    """
    Random values of ``shape`` on a FITS WCS of ``axes``, each (ctype, cunit, cdelt, crpix, crval) in WCS order, seen
    from 1 AU.
    """
    wcs = WCS(naxis=len(axes))
    wcs.wcs.ctype, wcs.wcs.cunit, wcs.wcs.cdelt, wcs.wcs.crpix, wcs.wcs.crval = map(list, zip(*axes, strict=True))
    wcs.wcs.dateobs, wcs.wcs.aux.hgln_obs, wcs.wcs.aux.hglt_obs, wcs.wcs.aux.dsun_obs = "2013-09-02", 0, 0, 1.496e11
    if pc is not None:
        wcs.wcs.pc = pc
    return Data(label=label, flux=np.random.default_rng(len(label)).random(shape), coords=wcs)


def _paths_drawn(viewer):
    """The x and y of each path drawn on the viewer's image, and whether it is the bright one."""
    lines = viewer.toolbar.tools["solar:path"]._overlays.values()
    return [(*line.get_data(), line.get_alpha() == 1) for line in lines]


def test_a_path_is_drawn_on_every_viewer_of_its_image_and_placed_on_other_data(qtbot, monkeypatch, tmp_path):
    # a slit-jaw-like cube of 0.1663" pixels, frames 12 s apart; two raster-like windows of 0.33" slit pixels and 0.35"
    # steps, rolled 2 degrees; a slit-jaw-like cube of 0.2" pixels whose pointing drifts 1" a frame, its frame 2 at the
    # first's frame 0; and a cube with no coordinates
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    times = np.datetime64("2013-09-02T16:39:35") + np.arange(4) * np.timedelta64(12, "s")
    hpln, hplt, frame = ("HPLN-TAN", "arcsec"), ("HPLT-TAN", "arcsec"), ("", "", 1, 1, 0)
    sji = _sky_cube("sji", (4, 30, 40), [(*hpln, 0.1663, 20, 400), (*hplt, 0.1663, 15, -300), frame])
    cos, sin = np.cos(np.deg2rad(2)), np.sin(np.deg2rad(2))
    windows = []
    for name, n, wave in (("Si IV", 6, 1400), ("Mg II k", 9, 2796)):
        axes = [("WAVE", "Angstrom", 0.05, 1, wave), (*hplt, 0.33, 20, -300), (*hpln, 0.35, 10, 400)]
        windows.append(_sky_cube(name, (20, 40, n), axes, [[1, 0, 0], [0, cos, -sin], [0, sin, cos]]))
    drift = [[1, 0, 5], [0, 1, 0], [0, 0, 1]]  # 5 pixels of x a frame
    jaw = _sky_cube("jaw", (4, 25, 30), [(*hpln, 0.2, 15, 400), (*hplt, 0.2, 12, -300), frame], drift)
    sji.add_component(np.broadcast_to(times[:, None, None], sji.shape), "Time")
    jaw.add_component(np.broadcast_to(times[:, None, None] - np.timedelta64(24, "s"), jaw.shape), "Time")
    app.data_collection.extend([sji, *windows, jaw, Data(label="plain", flux=np.ones((2, 3, 4)))])
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    other = app.new_data_viewer(ImageViewer, data=sji)
    other.state.x_att, other.state.y_att = sji.pixel_component_ids[1], sji.pixel_component_ids[2]  # transposed
    reuse = _modes_entry(viewer, "Path on other data…")
    reuse.parent().aboutToShow.emit()
    assert not reuse.isVisible()  # no path drawn yet

    # drawn in one viewer, it is drawn in every viewer of the image, opened before or after
    viewer.toolbar.tools["solar:path"].sampling = "linear"
    [path] = _draw_path(viewer, [3, 30], [5, 25])
    third = app.new_data_viewer(ImageViewer, data=sji)
    for shown, (x, y) in ((viewer, (path.x, path.y)), (other, (path.y, path.x)), (third, (path.x, path.y))):
        [(drawn_x, drawn_y, bright)] = _paths_drawn(shown)
        np.testing.assert_array_equal(np.stack([drawn_x, drawn_y]), np.stack([x, y]))
        assert bright
        _modes_entry(shown, reuse.text()).parent().aboutToShow.emit()
        assert _modes_entry(shown, reuse.text()).isVisible()
    # redrawn as a viewer's axes change, and not drawn off the image's axes
    third.state.x_att, third.state.y_att = sji.pixel_component_ids[1], sji.pixel_component_ids[2]
    [(drawn_x, drawn_y, _)] = _paths_drawn(third)
    np.testing.assert_array_equal(np.stack([drawn_x, drawn_y]), np.stack([path.y, path.x]))
    third.state.x_att = sji.pixel_component_ids[0]
    assert _paths_drawn(third) == []
    third.state.x_att = sji.pixel_component_ids[1]

    # placed on the datasets ticked of those it lies on, from its diagram's viewer: one diagram each, in a new viewer
    offered = []

    def tick_all(dialog):
        ticks = dialog.findChildren(QCheckBox)
        offered.extend(tick.text() for tick in ticks)
        for tick in ticks:
            tick.setChecked(True)
        return QDialog.Accepted

    monkeypatch.setattr(QDialog, "exec", tick_all)
    diagram = viewer.toolbar.tools["solar:path"]._slice_viewer
    count = len(app.viewers[0])
    _modes_entry(diagram, reuse.text()).trigger()
    assert offered == ["Si IV", "Mg II k", "jaw"]
    made = [data for data in app.data_collection if isinstance(data, PathData)][1:]
    assert [data.label for data in made] == [f"{name} [slice 1, linear]" for name in offered]
    assert [shown.state.reference_data for shown in app.viewers[0][count:]] == made
    links = [link for link in app.data_collection.external_links if isinstance(link, PathRelativeLink)]
    assert {frozenset((link._slice_from, link._slice_to)) for link in links} >= {frozenset((path, d)) for d in made}

    # each the diagram of the path's sky positions on the image's frame 0 drawn on the dataset's own viewer, the
    # drifting one's at its frame 2, nearest frame 0's time
    lon, lat, _ = sji.coords.pixel_to_world_values(path.x, path.y, 0)
    for data, got in zip([*windows, jaw], made, strict=True):
        wcs = data.coords
        if data is jaw:  # y and x, of x, y and frame
            along = wcs.world_to_pixel_values(lon, lat, wcs.pixel_to_world_values(0, 0, 2)[2])[1::-1]
        else:  # step and slit, of wavelength, slit and step
            along = wcs.world_to_pixel_values(wcs.pixel_to_world_values(0, 0, 0)[0], lat, lon)[:0:-1]
        own = app.new_data_viewer(ImageViewer, data=data)
        own.state.x_att, own.state.y_att = (data.pixel_component_ids[axis] for axis in got.sliced_dims)
        own.toolbar.tools["solar:path"]._extract(*along, "linear")
        expected = own.toolbar.tools["solar:path"]._traces[-1][0]
        np.testing.assert_allclose(np.stack([got.x, got.y]), np.stack([expected.x, expected.y]), rtol=0, atol=1e-9)
        assert 0 < np.isfinite(got[data.id["flux"]]).mean()
        np.testing.assert_allclose(got[data.id["flux"]], expected[data.id["flux"]], rtol=1e-6)
        # and drawn on that viewer too, before the newer one
        assert [bright for *_, bright in _paths_drawn(own)] == [False, True]
    # 10 pixels left of where frame 0's pointing places it
    x, _, _ = jaw.coords.world_to_pixel_values(lon, lat, jaw.coords.pixel_to_world_values(0, 0, 0)[2])
    np.testing.assert_allclose(got.y - x, -10, atol=1e-6)

    # a restored session draws the path in each viewer of the image
    session = str(tmp_path / "paths.glu")
    app.save_session(session)
    app = GlueApplication.restore_session(session)
    qtbot.addWidget(app)
    shown = [shown for shown in app.viewers[0] if shown.state.reference_data.label == "sji"]
    assert len(shown) == 3
    for restored in shown:
        [(drawn_x, drawn_y, _)] = _paths_drawn(restored)
        assert {tuple(drawn_x), tuple(drawn_y)} == {tuple(path.x), tuple(path.y)}
    # deleting the diagram removes its path
    app.data_collection.remove(next(data for data in app.data_collection if data.label == path.label))
    assert [_paths_drawn(restored) for restored in shown] == [[], [], []]


@pytest.mark.remote_data
def test_path_diagram_of_a_full_size_slit_jaw_image(qtbot, monkeypatch, tmp_path, irispy_data):
    # 4000255147 SJI 1400, read lazily, whose diagram is its 50 frames against the path
    data = image_data(irispy_data("iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz"))
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    [path] = _draw_path(viewer, [60, 200, 330], [80, 300, 150])
    assert path.shape == (50, len(path.x))
    flux = data.main_components[0]
    np.testing.assert_array_equal(path[flux], _along(data, flux, path))
    viewer.toolbar.tools["solar:path"]._slice_viewer.figure.canvas.draw()
    # its path saved as ECSV, on the sky of the first frame, and opened again
    file = str(tmp_path / "path.ecsv")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (file, ""))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (file, ""))
    _modes_entry(viewer.toolbar.tools["solar:path"]._slice_viewer, "Save path as ECSV…").trigger()
    _modes_entry(viewer, "Open path from ECSV…").trigger()
    [again] = viewer.toolbar.tools["solar:path"]._traces[-1]
    _assert_same_diagram(again, path)
    assert np.isfinite(QTable.read(file)["distance_km"]).all()


def _cmap_menu(viewer):
    """The colormap menu of the viewer's first layer."""
    return viewer.layer_view().layout_style_widgets[viewer.layers[0]].ui.combodata_cmap


# sunpy's RHESSI test image has no observer position
@pytest.mark.filterwarnings("ignore:Missing metadata for observer")
def test_every_sunpy_colormap_is_listed(qtbot, monkeypatch, irispy_test_files):
    import sunpy.data.test
    from sunpy.visualization.colormaps import cmlist

    # glue's own colormaps only, which glue lists on first use
    monkeypatch.setattr(colormaps, "_members", [])
    monkeypatch.setattr(colormaps, "_loaded", False)
    glue_solar.setup()
    glue_solar.setup()
    listed = colormaps.default_members() + [[cmlist[name].name, cmlist[name]] for name in sorted(cmlist)]
    assert colormaps.members == listed
    sji = load_data(str(find_irispy_test_file(irispy_test_files, SIT_AND_STARE.format("SJI_1400_t000"))))
    rhessi = read_sunpy_map(sunpy.data.test.get_test_filepath("hsi_image_20101016_191218.fits"))
    assert colormaps.members == listed  # a map's own already
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([sji, rhessi])
    for data, cmap in ((sji, cmlist["irissji1400"]), (rhessi, cmlist["rhessi"])):
        menu = _cmap_menu(app.new_data_viewer(ImageViewer, data=data))
        assert menu.currentText() == cmap.name
        assert [[menu.itemText(i), menu.itemData(i).data] for i in range(menu.count())] == listed


def test_colormap_icons_are_drawn_once(qtbot, monkeypatch):
    from glue_qt.utils import colors

    glue_solar.setup()  # every sunpy colormap listed
    assert colors.QColormapCombo._update_icons is glue_patches.update_icons  # always, probing at the first combo
    glue_patches._icons_need_workaround.cache_clear()  # the patch probes glue-qt's method within this probe
    assert not glue_patches.needs_icon_cache_workaround(glue_patches.update_icons)
    assert glue_patches._icons_need_workaround() == glue_patches.needs_icon_cache_workaround()  # glue-qt's own method
    first = colors.QColormapCombo()
    qtbot.addWidget(first)
    drawn, draw = [], colors.cmap2pixmap
    monkeypatch.setattr(colors, "cmap2pixmap", lambda *args, **kwargs: drawn.append(args) or draw(*args, **kwargs))
    second = colors.QColormapCombo()
    qtbot.addWidget(second)
    assert second.width() == first.width()
    assert not drawn
    assert second.itemIcon(0).cacheKey() == first.itemIcon(0).cacheKey()
    # keyed on the colormap, not its name: sunpy has two of each of these
    i, j = [k for k in range(first.count()) if first.itemText(k) == "SOHO LASCO C2"]
    assert first.itemIcon(i).cacheKey() != first.itemIcon(j).cacheKey()


def test_a_session_restores_a_sunpy_colormap_it_names(qtbot, monkeypatch, tmp_path):
    from sunpy.visualization.colormaps import cmlist

    monkeypatch.setattr(colormaps, "_members", [])
    monkeypatch.setattr(colormaps, "_loaded", False)
    app = GlueApplication()
    qtbot.addWidget(app)
    image = Data(label="image", flux=np.arange(20.0).reshape(4, 5))
    app.data_collection.append(image)
    app.new_data_viewer(ImageViewer, data=image)
    app.save_session(str(tmp_path / "cmap.glu"))
    session = (tmp_path / "cmap.glu").read_text()
    # glue restores a colormap by its name, here one not listed yet: setup(), not run here, lists every sunpy one
    # rhessi's name is its sunpy key; the HMI magnetogram's, as most are, is not
    for name in ("rhessi", cmlist["hmimag"].name):
        glue_solar._add_session_colormaps({"layer": {"cmap": name}})  # which the restore below would hang without
        assert name in [label for label, _ in colormaps.members]
        (tmp_path / "cmap.glu").write_text(session.replace('"cmap": "gray"', f'"cmap": "{name}"'))
        restored = GlueApplication.restore_session(str(tmp_path / "cmap.glu"))
        qtbot.addWidget(restored)
        assert _cmap_menu(restored.viewers[0][0]).currentText() == name


def test_a_colormap_menu_names_the_layers_colormap_of_equal_colours(qtbot, tmp_path):
    from echo.qt import connect

    import sunpy.data.test

    installed = connect._find_combo_data is glue_patches.find_combo_data
    assert installed == glue_patches.needs_combo_match_workaround()  # probes echo's own function
    assert not glue_patches.needs_combo_match_workaround(glue_patches.find_combo_data)
    glue_solar.setup()
    # sunpy's AIA 171 colormap has the colours of SUVI 171, listed before it, and of EUI 174
    aia = read_sunpy_map(sunpy.data.test.get_test_filepath("aia_171_level1.fits"))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(aia)
    assert _cmap_menu(app.new_data_viewer(ImageViewer, data=aia)).currentText() == "SDO AIA 171.0 Angstrom"
    app.save_session(str(tmp_path / "aia.glu"))
    restored = GlueApplication.restore_session(str(tmp_path / "aia.glu"))
    qtbot.addWidget(restored)
    menu = _cmap_menu(restored.viewers[0][0])
    assert menu.currentText() == "SDO AIA 171.0 Angstrom"
    for i in range(menu.count()):  # each entry, picked after the one before it
        menu.setCurrentIndex(i)
        assert menu.currentText() == menu.itemText(i)


def test_gamma_stretches_are_listed_and_restored(qtbot, tmp_path):
    glue_solar.setup()
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    image = Data(label="image", flux=np.arange(20.0).reshape(4, 5))
    app.data_collection.append(image)
    viewer = app.new_data_viewer(ImageViewer, data=image)
    menu = viewer.layer_view().layout_style_widgets[viewer.layers[0]].ui.combosel_stretch
    gammas = ["Gamma 0.4", "Gamma 0.75", "Gamma 1.5", "Gamma 2.2"]
    assert [menu.itemText(i) for i in range(menu.count())][-4:] == gammas
    menu.setCurrentIndex(menu.findText("Gamma 0.75"))
    assert viewer.state.layers[0].stretch == "gamma_0.75"  # sessions save the key; one renamed fails to restore
    assert isinstance(viewer.state.layers[0].stretch_object, PowerStretch)
    assert viewer.state.layers[0].stretch_object.a == 0.75
    app.save_session(str(tmp_path / "gamma.glu"))
    restored = GlueApplication.restore_session(str(tmp_path / "gamma.glu"))
    qtbot.addWidget(restored)
    assert restored.viewers[0][0].state.layers[0].stretch_object.a == 0.75


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
        hdul[0].data[0, 2, 3] = -199
    aia = image_data(path)
    flux = np.asarray(aia[aia.main_components[0]])
    assert flux.dtype == np.float32
    np.testing.assert_array_equal(np.argwhere(np.isnan(flux)), [[0, 1, 2], [0, 2, 3]])

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


def test_keys_step_frames_and_wavelengths_round_and_play(qtbot, monkeypatch, irispy_test_files):
    glue_solar.setup()
    glue_solar.setup()  # nothing registered twice
    keys = keyboard_shortcut.members
    for cls in (ImageViewer, QuicklookImageViewer, ProfileViewer):
        assert {Qt.Key_D, Qt.Key_F, Qt.Key_A, Qt.Key_S, Qt.Key_Space} <= set(keys[cls])
    # glue-qt finds a viewer's keys by its exact class: the quicklook's raster panels take the Image viewer's, glue-qt's
    # own Tab and Backspace too
    assert keys[QuicklookImageViewer] == keys[ImageViewer]
    sji = image_data(find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"))
    scan = find_irispy_test_file(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits")
    [raster] = raster_data([scan], ["C II 1336"])  # of another observation
    cube = Data(label="cube", flux=np.zeros((3, 4, 5)))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([sji, raster, cube])
    saved = []
    monkeypatch.setattr(NavigationToolbar2QT, "save_figure", lambda *args: saved.append(args))
    frames = app.new_data_viewer(ImageViewer, data=sji)
    last = sji.shape[0] - 1
    # F and D step the frame, round from either end; a slit-jaw image has no wavelength for A and S
    frames.state.slices = (last, 0, 0)
    for key, frame in ((Qt.Key_F, 0), (Qt.Key_D, last), (Qt.Key_D, last - 1)):
        press(frames, key)
        assert frames.state.slices == (frame, 0, 0)
    press(frames, Qt.Key_A)
    press(frames, Qt.Key_S)
    assert frames.state.slices == (last - 1, 0, 0)
    # matplotlib's own F and S, which glue-qt's canvases have too, neither show its empty figure window full screen nor
    # open its save dialog
    assert not frames.figure.canvas.manager.window.isVisible()
    assert saved == []
    # nor do its grid, log scale, pan and zoom keys, alone or with Shift; its others, such as H for home, stay
    handled = []
    monkeypatch.setattr(glue_patches, "key_press_handler", lambda event: handled.append(event.key))
    for key in (Qt.Key_G, Qt.Key_L, Qt.Key_K, Qt.Key_P, Qt.Key_O, Qt.Key_H):
        press(frames, key)
    for key in (Qt.Key_G, Qt.Key_L):
        QTest.keyClick(frames.figure.canvas, key, Qt.ShiftModifier)
    assert [key for key in handled if key != "shift"] == ["h"]  # the Shift key's own press
    # Space plays the frames, round as glue-qt's play button does, and pauses them
    slider = frames.options_widget().slice_helper._sliders[0]
    shown = []
    frames.state.add_callback("slices", lambda slices: shown.append(slices[0]))
    press(frames, Qt.Key_Space)
    slider._play_timer.setInterval(1)
    qtbot.waitUntil(lambda: len(shown) >= 3)
    press(frames, Qt.Key_Space)
    assert not slider._play_timer.isActive()
    assert shown[:3] == [last, 0, 1]
    # A and S step a raster map's wavelength only, round from either end
    waves = app.new_data_viewer(ImageViewer, data=raster)
    waves.state.x_att, waves.state.y_att = raster.pixel_component_ids[0], raster.pixel_component_ids[1]
    waves.state.slices = (0, 0, 0)
    for key, wavelength in ((Qt.Key_A, raster.shape[2] - 1), (Qt.Key_S, 0), (Qt.Key_S, 1)):
        press(waves, key)
        assert waves.state.slices == (0, 0, wavelength)
    # a Profile viewer of other data takes the keys and moves nothing
    profile = app.new_data_viewer(ProfileViewer, data=cube)
    for key in (Qt.Key_D, Qt.Key_F, Qt.Key_A, Qt.Key_S, Qt.Key_Space, Qt.Key_Space):
        press(profile, key)
    assert (frames.state.slices, waves.state.slices) == ((shown[-1], 0, 0), (0, 0, 1))


def test_band_shows_the_mean_about_the_wavelength_slider(qtbot, monkeypatch):
    glue_solar.setup()
    wcs = WCS(naxis=4)
    wcs.wcs.ctype[0] = "WAVE"
    flux = np.random.default_rng(0).random((2, 3, 4, 20))
    flux[..., 5] = np.nan
    cube = Data(label="stack", flux=flux, coords=wcs)
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(cube)
    viewer = app.new_data_viewer(ImageViewer, data=cube)
    state = viewer.state
    state.x_att, state.y_att = cube.pixel_component_ids[1], cube.pixel_component_ids[2]  # the map of steps and slit
    state.slices = (1, 0, 0, 7)
    picked = []
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args: (picked.pop(), True))

    def shown():
        """The map displayed, and the scan and the mean expected of the band about the wavelength slider's index."""
        scan, wave = state.slices[0], state.slices[3]
        lo, hi = max(wave.center - 2, 0), wave.center + 3
        return state.layers[0].get_sliced_data(), np.nanmean(flux[scan, :, :, lo:hi], axis=2).T

    picked.append("5")
    viewer.toolbar.actions["solar:band"].trigger()
    assert viewer.toolbar.tools["solar:band"].checked
    np.testing.assert_allclose(*shown())
    # it follows the slider, as A and S and a drag move it, cut at the end of the axis, and stays on a scan move
    sliders = viewer.options_widget().slice_helper._sliders
    for move in (
        lambda: press(viewer, Qt.Key_S),
        lambda: sliders[3].value_slice_center.setValue(19),
        lambda: sliders[3].value_slice_center.setValue(1),
        lambda: sliders[0].value_slice_center.setValue(0),
    ):
        move()
        np.testing.assert_allclose(*shown())
    assert (state.slices[0], state.slices[3].center) == (0, 1)
    # 1 shows the slider's wavelength alone again
    picked.append("1")
    viewer.toolbar.actions["solar:band"].trigger()
    assert state.slices == (0, 0, 0, 1)
    press(viewer, Qt.Key_S)
    assert state.slices == (0, 0, 0, 2)


_GLUE_START = """
from qtpy.QtCore import Qt

import glue_solar

glue_solar.setup()  # before glue-qt's application loads, as at glue's start

from glue_qt.app import GlueApplication
from glue_qt.config import keyboard_shortcut

from glue_solar.quicklook import QuicklookImageViewer

print(*(key in keyboard_shortcut.members[QuicklookImageViewer] for key in (Qt.Key_Tab, Qt.Key_Backspace)))
"""


def test_quicklook_panels_take_glue_qts_tab_and_backspace_at_glues_start():
    # in a process of its own, since the other tests load glue-qt's application, which registers them, first
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    result = subprocess.run([sys.executable, "-c", _GLUE_START], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.split() == ["True", "True"]


def test_the_key_table_lists_every_key_of_glue_solars_viewers_and_tools(request):
    # docs/user_guide/viewer-tools-and-windows.rst: the keys glue-solar gives viewers, its tools' shortcuts, and the
    # keys of its mouse modes, the glue modes they extend and the WCSAxes readout, and the Qt keys its modules name,
    # once each
    glue_solar.setup()
    keys = [
        key
        for keys in keyboard_shortcut.members.values()
        for key, function in keys.items()
        if getattr(function, "func", function).__module__.startswith("glue_solar")
    ]
    tools = [tool for tool in viewer_tool.members.values() if tool.__module__.startswith("glue_solar")]
    keys += [tool.shortcut for tool in tools if tool.shortcut]
    handlers = [vars(cls)["key"] for tool in tools for cls in tool.__mro__ if "key" in vars(cls)]
    for handler in [*handlers, WCSAxes._set_cursor_prefs]:
        keys += re.findall(r"event\.key == ['\"](\w+)", inspect.getsource(handler))
    package = Path(glue_solar.__file__).parent
    for module in package.rglob("*.py"):
        # not the observation browser's Return, a dialog's key, which the loading guide gives
        if module.relative_to(package).parts[0] != "tests" and module.parent.name != "loaders":
            keys += re.findall(r"Qt\.Key_(\w+)", module.read_text())
    guide = request.config.rootpath / "docs" / "user_guide" / "viewer-tools-and-windows.rst"
    if not guide.exists():
        pytest.skip("the package is installed without its docs")
    table = re.search(r"\.\. list-table:: Keys\n((?:\n| .*\n)*)", guide.read_text())[1]
    listed = re.findall(r":kbd:`([^`]+)`", table)
    assert sorted(listed) == sorted({QKeySequence(key).toString() for key in keys})


def test_help_opens_the_user_guide_and_the_issues(monkeypatch):
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()))
    help_iris(None, None)
    assert opened == [
        "https://glue-solar.readthedocs.io/en/latest/user_guide/index.html",
        "https://github.com/glue-viz/glue-solar/issues",
    ]


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


def test_a_2021_scatter_ticks_in_2021(qtbot):
    installed = glue.utils.matplotlib.datetime64_to_mpl is glue_patches.datetime64_to_mpl
    assert installed == glue_patches.needs_date_epoch_workaround()  # probes glue's own conversion
    assert not glue_patches.needs_date_epoch_workaround(glue_patches.datetime64_to_mpl)
    when = np.array(["2021-09-05T00:00", "2021-09-06T00:00"], "datetime64[ns]")
    np.testing.assert_array_equal(glue_patches.mpl_to_datetime64(glue_patches.datetime64_to_mpl(when)), when)
    data = Data(time=when, value=[1.0, 2.0], label="dates")
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ScatterViewer, data=data)
    viewer.state.x_att = data.id["time"]
    viewer.figure.canvas.draw()
    assert {date.year for date in mdates.num2date(viewer.axes.get_xlim())} == {2021}  # glue 1.27.0 alone: 3990


def test_a_scatter_plot_of_linked_times(qtbot):
    installed = DerivedComponent.datetime.fget is glue_patches.derived_datetime
    assert installed == glue_patches.needs_derived_datetime_workaround()  # probes glue's own property
    assert not glue_patches.needs_derived_datetime_workaround(DerivedComponent.datetime)
    when = np.array(["2021-09-05T00:00", "2021-09-06T00:00"], "datetime64[ns]")
    first, second = (Data(time=when, value=[1.0, 2.0], label=label) for label in ("first", "second"))
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([first, second])
    app.data_collection.add_link([LinkSame(first.id[name], second.id[name]) for name in ("time", "value")])
    viewer = app.new_data_viewer(ScatterViewer, data=first)
    viewer.state.x_att = first.id["time"]
    viewer.add_data(second)  # glue 1.27.0 alone: "Unknown data kind"
    assert all(layer.enabled for layer in viewer.layers)


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


def test_a_draw_queued_as_the_test_returns_runs_on_a_live_application(qtbot):
    # pytest-qt processes events between a test and closing its widgets: had the conftest not kept this
    # application, a garbage collection in the queued draw would delete the canvas under it
    app = GlueApplication()
    qtbot.addWidget(app)
    app.itself = app  # a reference cycle, as a quicklook's leaves: only garbage collection frees it
    canvas = app.new_data_viewer(ImageViewer).figure.canvas
    canvas.mpl_connect("draw_event", lambda event: gc.collect())
    canvas.draw_idle()


def test_profiles_label_the_main_iris_lines(qtbot, irispy_test_files):
    glue_solar.setup()
    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    [mg] = raster_data(files[:1], ["Mg II k 2796"])
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(mg)
    viewer = app.new_data_viewer(ProfileViewer, data=mg)
    viewer.state.x_att = mg.world_component_ids[mg.ndim - 1]  # wavelength
    tool = viewer.toolbar.tools["solar:lines"]

    def labels():
        return [(text.get_text(), text.get_position()[0]) for text in viewer.axes.texts if text in tool.artists]

    # the window's lines at their vacuum wavelengths; 2798.754 and 2798.823 Å share a label between them
    assert [name for name, _ in labels()] == ["Mg II", "Mg II k", "Mg II", "Mg II h"]
    assert [x for _, x in labels()] == pytest.approx([2791.599, 2796.352, 2798.7885, 2803.530])
    viewer.state.x_display_unit = "nm"
    assert dict(labels())["Mg II k"] == pytest.approx(279.6352)
    button = viewer.toolbar.actions["solar:lines"]
    assert button.isChecked()  # while they show
    button.trigger()  # off
    assert labels() == []
    assert not button.isChecked()
    tool.activate()
    assert len(labels()) == 4
    assert button.isChecked()


def test_profiles_give_the_doppler_velocity_from_the_rest_wavelength(qtbot, monkeypatch, tmp_path, irispy_test_files):
    glue_solar.setup()
    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    [none, mg] = sorted(raster_data(files[:1], ["Mg II k 2796", "2832"]), key=lambda data: data.label)
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([mg, none])
    viewer = app.new_data_viewer(ProfileViewer, data=mg)
    viewer.add_data(none)
    state = viewer.state
    state.x_att = mg.world_component_ids[mg.ndim - 1]  # wavelength
    units = ProfileViewerState.x_display_unit.get_choices
    assert units(state)[-1] == "km/s"  # after the lengths
    assert UnitConverter().to_unit(mg, state.x_att, 2796.352, "km/s") == pytest.approx(0, abs=1e-9)  # Mg II k
    tool, button = viewer.toolbar.tools["solar:velocity"], viewer.toolbar.actions["solar:velocity"]
    assert tool.axis is None  # it starts off
    assert (button.isCheckable(), button.isChecked(), button.isEnabled()) == (True, False, True)
    button.trigger()
    assert button.isChecked()
    state.x_min, state.x_max = 2795, 2798

    def velocities(waves, rest):
        return (np.asarray(waves) / rest - 1) * constants.c.to_value("km/s")

    viewer.figure.canvas.draw()
    assert tool.axis.get_xlim() == pytest.approx(velocities([2795, 2798], 2796.352))
    assert tool.axis.get_xlabel() == "Velocity from 2796.352 Å [km/s]"  # as the x unit is written

    def zero():
        """Where the top axis has its tick at 0 km/s, in Å."""
        viewer.figure.canvas.draw()
        assert 0 in tool.axis.get_xticks()
        return viewer.axes.transData.inverted().transform(tool.axis.transData.transform((0, 0)))[0]

    def set_rest(text):
        monkeypatch.setattr(QInputDialog, "getItem", lambda *args: (text, True))
        rest_wavelength_iris(state.reference_data, app.data_collection)

    assert zero() == pytest.approx(2796.352, abs=1e-6)
    set_rest("2796.2")
    assert zero() == pytest.approx(2796.2, abs=1e-6)
    state.x_display_unit = "km/s"  # the profile and its range from the rest wavelength, and no top axis
    assert tool.axis is None
    assert [state.x_min, state.x_max] == pytest.approx(velocities([2795, 2798], 2796.2))
    assert viewer.layers[0].state.profile[0] == pytest.approx(velocities(_wavelengths(mg)[0], 2796.2))
    set_rest("")  # back to Mg II k, still in km/s
    assert state.x_display_unit == "km/s"
    assert viewer.layers[0].state.profile[0] == pytest.approx(velocities(_wavelengths(mg)[0], 2796.352))
    # a session saved with the unit as astropy writes it opens in km/s
    app.save_session(str(tmp_path / "kms.glu"))
    saved = (tmp_path / "kms.glu").read_text()
    assert '"st__km/s"' in saved
    (tmp_path / "kms.glu").write_text(saved.replace('"st__km/s"', '"st__km / s"'))
    restored = GlueApplication.restore_session(str(tmp_path / "kms.glu"), show=False)
    qtbot.addWidget(restored)
    assert restored.viewers[0][0].state.x_display_unit == "km/s"
    # 2832 has no line: no km/s or velocity axis until a rest wavelength is set, and none after, back in Å
    state.reference_data = none
    state.x_att = none.world_component_ids[none.ndim - 1]
    assert "km/s" not in units(state)
    assert not button.isEnabled()
    set_rest("2832.7")
    assert units(state)[-1] == "km/s"
    assert button.isEnabled()
    state.x_display_unit = "km/s"
    set_rest("")
    assert "km/s" not in units(state)
    assert state.x_display_unit == "Angstrom"
    assert 2830 < state.x_min < state.x_max < 2835


def test_profiles_save_as_drawn_to_ecsv(qtbot, monkeypatch, tmp_path, irispy_test_files):
    glue_solar.setup()
    sit_and_stare = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, sit_and_stare)], ["Si IV 1403"])
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(raster)
    # (exposure, slit, wavelength): a light curve and a spectrum
    raster.new_subset(PixelSubsetState(raster, [slice(None), slice(5, 6), slice(10, 11)]), label="Curve")
    raster.new_subset(PixelSubsetState(raster, [slice(3, 4), slice(5, 6), slice(None)]), label="Spectrum")
    viewer = app.new_data_viewer(ProfileViewer, data=raster)
    state = viewer.state
    whole, curve, spectrum = state.layers
    state.x_att = raster.pixel_component_ids[0]  # the exposures
    spectrum.visible = False  # left out, and not named
    path = tmp_path / "profiles.ecsv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(path), ""))
    [tool] = [tool for tool in viewer.toolbar.tools["save"].subtools if tool.tool_id == "solar:save_profile"]
    save = viewer.toolbar.widgetForAction(viewer.toolbar.actions["save"]).menu()  # after glue's entries
    assert [entry.text() for entry in save.actions()][-2:] == ["Save Python script to reproduce plot", tool.action_text]

    def saved():
        tool.activate()
        return Table.read(path, format="ascii.ecsv")

    def check(table, i, layer):
        np.testing.assert_array_equal(table[f"x{i}"], layer.profile[0])
        np.testing.assert_array_equal(table[f"y{i}"], layer.profile[1])
        assert (table[f"x{i}"].description, table[f"y{i}"].description) == (state.x_att.label, layer.layer.label)

    table = saved()
    assert table.colnames == ["x1", "y1", "time1", "x2", "y2", "time2"]
    check(table, 1, whole)
    check(table, 2, curve)
    times = raster[raster.id["Time"]]
    assert isinstance(table["time2"], Time)
    np.testing.assert_array_equal(table["time2"].datetime64, times[:, 5, 10])
    np.testing.assert_array_equal(table["time1"].datetime64, times[:, 0, 0])
    assert table["y2"].unit == raster.get_component(raster.main_components[0]).units
    assert table["y2"].meta["pixel"] == {"Pixel Axis 1 [y]": 5, "Pixel Axis 2 [x]": 10}
    sky = [float(raster[cid, (0, 5, 10)]) for cid in raster.world_component_ids[:2]]  # at the first exposure
    assert [table["y2"].meta[name].to_value(u.arcsec) for name in ("lon", "lat")] == pytest.approx(sky)
    assert table.meta == {"function": "maximum", **{key: str(raster.meta[key]) for key in ("OBSID", "STARTOBS")}}
    assert app.statusBar().currentMessage() == ""
    # the spectrum, in km/s from Si IV 1402.77 Å, and the curve, one wavelength wide, is left out
    spectrum.visible = True
    state.x_att = raster.world_component_ids[2]
    state.x_display_unit = "km/s"
    state.function = "mean"
    table = saved()
    assert app.statusBar().currentMessage() == "Left out, without a profile: Curve"
    assert table.colnames == ["x1", "y1", "x2", "y2"]  # no times along the wavelength
    check(table, 1, whole)
    check(table, 2, spectrum)
    assert table["x2"].unit == "km/s"
    assert table["y2"].meta["pixel"] == {"Pixel Axis 0 [z]": 3, "Pixel Axis 1 [y]": 5}
    assert table.meta["function"] == "mean"
    state.normalize = True  # as drawn
    table = saved()
    np.testing.assert_allclose(table["y1"], whole.normalize_values(whole.profile[1]))
    assert table["y1"].unit is None
    for layer in state.layers:
        layer.visible = False
    with pytest.raises(ValueError, match="No visible layer has a profile"):
        tool.activate()
    # a stack's scans, whose times differ by step: at the Pixel subset's step, slit row and wavelength
    files = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    [stack] = raster_data(files, ["Si IV 1403"], stack=True)
    app.data_collection.append(stack)
    stack.new_subset(PixelSubsetState(stack, [slice(None), slice(1, 2), slice(3, 4), slice(4, 5)]), label="Scans")
    viewer = app.new_data_viewer(ProfileViewer, data=stack)
    viewer.state.x_att = stack.pixel_component_ids[0]
    [tool] = [tool for tool in viewer.toolbar.tools["save"].subtools if tool.tool_id == "solar:save_profile"]
    times = stack[stack.id["Time"]]
    assert not np.array_equal(times[:, 1, 3, 4], times[:, 0, 0, 0])
    table = saved()
    np.testing.assert_array_equal(table["time2"].datetime64, times[:, 1, 3, 4])
    np.testing.assert_array_equal(table["time1"].datetime64, times[:, 0, 0, 0])
    assert app.statusBar().currentMessage() == ""  # the earlier note cleared, as nothing was left out


def test_profile_fit_tab_fits_a_gaussian_on_a_constant(qtbot):
    glue_solar.setup()
    glue_solar.setup()
    assert list(fit_plugin).count(GaussianConstantFitter) == 1
    wcs = WCS({"CTYPE1": "WAVE", "CUNIT1": "Angstrom", "CRPIX1": 1, "CRVAL1": 1355, "CDELT1": 0.025})
    x = 1355 + 0.025 * np.arange(49)
    y = 3 + 40 * np.exp(-0.5 * ((x - 1355.62) / 0.04) ** 2)
    y[0] = np.nan  # fill
    data = Data(label="O I", flux=y, coords=wcs)
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ProfileViewer, data=data)
    viewer.state.x_att = data.world_component_ids[0]
    viewer.state.x_display_unit = "Angstrom"
    viewer.toolbar.active_tool = "profile-analysis"
    tools = viewer.toolbar.tools["profile-analysis"]._profile_tools
    tools.fit_function = GaussianConstantFitter
    tools.rng_mode.state.x_min, tools.rng_mode.state.x_max = 1354, 1356.5
    tools.ui.button_fit.click()
    tools.wait_for_fit()
    qtbot.waitUntil(lambda: "km/s" in tools.text_log.toPlainText())
    # the fill left out, its centre and its velocity from O I 1355.5977, (1355.62 / 1355.5977 - 1) c
    assert tools.text_log.toPlainText().splitlines()[-2:] == ["centre = 1355.620000", "O I 1355.5977 Å: +4.93 km/s"]
    model, _ = GaussianConstantFitter().build_and_fit(x, y)
    assert model.parameters == pytest.approx([3, 40, 1355.62, 0.04])
    model, _ = GaussianConstantFitter().build_and_fit(x, 50 - y)
    assert model.parameters == pytest.approx([47, -40, 1355.62, 0.04])  # absorption


def test_gaussian_on_a_constant_says_when_the_range_holds_too_few_samples():
    x = np.arange(4.0)
    y = 1 + 4 * np.exp(-0.5 * ((x - 1) / 0.5) ** 2)
    y[3] = np.nan  # three finite samples for four parameters
    message = r"Gaussian \+ constant \(IRIS\) needs at least 4 finite samples in the range, one per free parameter, and"
    with pytest.raises(ValueError, match=f"{message} has 3: widen the range"):
        GaussianConstantFitter().build_and_fit(x, y)
    fitter = GaussianConstantFitter()
    fitter.set_constraint("amplitude_0", value=1, fixed=True)
    model, _ = fitter.build_and_fit(x, y)  # three free parameters, which three samples fit
    assert np.abs(model.parameters) == pytest.approx([1, 4, 1, 0.5])
