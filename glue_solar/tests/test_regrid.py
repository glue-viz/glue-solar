"""
'Regrid on time', on int16 copies of irispy's test files whose exposures, frames and scans are taken at known times.
"""

import numpy as np
import pytest
from glue.core import Data
from glue_qt.app.application import GlueApplication
from qtpy import QtWidgets
from scipy.interpolate import make_interp_spline

from astropy.io import fits

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.quicklook import quicklook
from glue_solar.regrid import regrid_on_time
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import _SJI_POINTING, image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.sources.loaders.lazy import LazyData, RawComponent
from glue_solar.tests.test_lazy import RASTER, SJI, int16_copy, int16_raster_copy
from glue_solar.tests.test_quicklook import SCAN, menu_action, readout

GAP = 100  # the first exposure of the sit-and-stare raster after the 10 left out


def known_times(n, step, gap):
    """
    Seconds after STARTOBS of ``n`` exposures or frames every ``step`` s, with 10 left out before number ``gap``, one
    early and one late by 0.45 steps, and the last 0.3 steps late, so that it fills the last two pixels.
    """
    seconds = step * (np.arange(n) + 10 * (np.arange(n) >= gap))
    seconds[[gap // 5, gap // 3, -1]] += np.array([0.45, -0.45, 0.3]) * step
    return seconds


def with_times(path, seconds):
    """``path`` with its exposures or frames taken ``seconds`` after STARTOBS: the TIME of its auxiliary HDU."""
    with fits.open(path, mode="update") as hdulist:
        aux = hdulist[-2]  # before the Level 1 file names
        aux.data[:, aux.header["TIME"]] = seconds
    return path


def sit_and_stare(tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, RASTER)
    path = with_times(int16_raster_copy(source, tmp_path / RASTER), known_times(187, 3.0, GAP))
    return raster_data([path], ["Si IV 1403"])[0]


def expected_regrid(times):
    """
    The median step between ``times`` (s), and the index of the time nearest each multiple of it after the first time
    up to the last (the earlier of two as near), or -1 where none is within 0.75 steps: by brute force.
    """
    seconds = (times - times[0]) / np.timedelta64(1, "s")
    step = np.median(np.diff(seconds))
    distance = np.abs(np.arange(np.ceil(seconds[-1] / step) + 1)[:, None] * step - seconds)
    return step, np.where(distance.min(axis=1) <= 0.75 * step, distance.argmin(axis=1), -1)


def check_regrid(source, regridded):
    """
    ``regridded`` holds ``source``, in its units and colormap, at the indices `expected_regrid` gives, with NaN, NaT,
    missing samples and no pointing in its gaps, and the coordinates of ``source`` at the time of each pixel; returns
    the gaps.
    """
    middle = (source.shape[1] // 2,) if source.ndim == 4 else ()  # a stack's scans by their middle step's times
    times = source[source.id["Time"]][(slice(None), *middle, 0, 0)]
    step, index = expected_regrid(times)
    gaps = index < 0
    assert regridded.shape == (len(index), *source.shape[1:])
    assert regridded.meta["time_step"] == pytest.approx(step, abs=1e-9)
    cid = regridded.main_components[0]
    assert regridded.get_component(cid).units == source.get_component(source.main_components[0]).units
    assert regridded.style.preferred_cmap == source.style.preferred_cmap
    values = np.asarray(source[source.main_components[0]])[np.maximum(index, 0)]
    values[gaps] = np.nan
    np.testing.assert_array_equal(regridded[cid], values)
    np.testing.assert_array_equal(regridded[f"{cid.label} mask"], np.isnan(values))
    assert f"{cid.label} DN/s" in [component.label for component in regridded.derived_components]
    lead = (slice(None),) * (source.ndim - 2) + (0, 0)  # per exposure, frame, or scan and step
    for name, gap in (("Time", np.datetime64("NaT", "ns")), ("Exposure time", np.nan)):
        expected = source[source.id[name], lead][np.maximum(index, 0)]
        expected[gaps] = gap
        np.testing.assert_array_equal(regridded[regridded.id[name], lead], expected)
    for name in set(_SJI_POINTING) & set(source.meta):
        expected = np.asarray(source.meta[name], float)[np.maximum(index, 0)]
        expected[gaps] = np.nan
        np.testing.assert_array_equal(regridded.meta[name], expected)
    # the source's coordinates at each pixel's time, between its exposures, frames or scans (at its last time past
    # it), and back through the source's own: pixels between its pixels, and beyond its ends, linearly
    pixels = np.arange(len(index))
    seconds = (times - times[0]) / np.timedelta64(1, "s")
    positions = np.interp(pixels * step, seconds, np.arange(len(times)))
    others = [np.full(len(index), n // 3) for n in source.shape[:0:-1]]
    world = source.coords.pixel_to_world_values(*others, positions)
    np.testing.assert_allclose(regridded.coords.pixel_to_world_values(*others, pixels), world, rtol=1e-9)
    back = make_interp_spline(positions, pixels, k=1)(source.coords.world_to_pixel_values(*world)[-1])
    np.testing.assert_allclose(regridded.coords.world_to_pixel_values(*world)[-1], back, atol=1e-9)
    if isinstance(regridded, LazyData):  # glue's 99.5% colour limits, exactly as from every value
        for percentile in (0.25, 99.75):
            limit = regridded.compute_statistic("percentile", cid, percentile=percentile, random_subset=10000)
            assert limit == np.nanpercentile(values, percentile)
    return np.flatnonzero(gaps)


def test_a_sit_and_stare_regrids_at_its_median_exposure_step(monkeypatch, tmp_path, irispy_test_files):
    raster = sit_and_stare(tmp_path, irispy_test_files)
    regridded = regrid_on_time(raster)
    # ceil(span / step) + 1 pixels, NaN where the 10 exposures were left out, and only there
    gaps = list(check_regrid(raster, regridded))
    assert gaps == list(range(GAP, GAP + 10))
    # its planes stay in the file: views of the source's, but in the gaps
    assert type(regridded) is LazyData
    component = regridded.get_component(regridded.main_components[0])
    assert isinstance(component, RawComponent)
    planes, raw = component._source.raw.scans, raster.get_component(raster.main_components[0])._source.raw
    assert [np.may_share_memory(plane, raw) for plane in planes] == [i not in gaps for i in range(len(planes))]
    assert regridded.shape[0] == 198
    assert regridded.label == f"{raster.label} regridded"
    assert regridded.meta["OBSID"] == raster.meta["OBSID"]
    # and as before from data loaded in memory
    monkeypatch.setattr(iris, "LAZY", False)
    eager = regrid_on_time(raster_data([tmp_path / RASTER], ["Si IV 1403"])[0])
    assert type(eager) is Data
    np.testing.assert_array_equal(eager[eager.main_components[0]], regridded[regridded.main_components[0]])


def test_a_slit_jaw_image_regrids_on_its_frame_times(tmp_path, irispy_test_files):
    path = with_times(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]),
                      known_times(62, 10.0, 30))
    sji = image_data(path)
    regridded = regrid_on_time(sji)
    assert list(check_regrid(sji, regridded)) == list(range(30, 40))
    assert regridded.shape[0] == 73
    assert set(_SJI_POINTING) <= set(sji.meta)
    # a regular time axis: steps after frame 0's time, as the slit-jaw image's own coordinates give it, up to its
    # last frame's, which the last pixel, past it, takes
    time = list(sji.coords.world_axis_physical_types).index("time")
    start, end = (sji.coords.pixel_to_world_values(0, 0, frame)[time] for frame in (0, sji.shape[0] - 1))
    pixels = np.arange(regridded.shape[0])
    times = regridded.coords.pixel_to_world_values(0, 0, pixels)[time]
    np.testing.assert_allclose(times[:-1], start + pixels[:-1] * regridded.meta["time_step"], atol=1e-6)
    assert start + pixels[-1] * regridded.meta["time_step"] > end == times[-1]


def test_a_stack_regrids_its_scans(tmp_path, irispy_test_files):
    sources = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name)
    paths = []
    # scan 2 left out, and scan 4 2 s late at its middle step, which times it, in shorter steps than the others
    for scan, start, step in ((0, 0, 5.0), (1, 60, 5.0), (3, 180, 5.0), (4, 246, 4.0)):
        paths.append(with_times(int16_raster_copy(sources[scan], tmp_path / sources[scan].name),
                                start + step * np.arange(8)))
    [stack] = raster_data(paths, ["C II 1336"], stack=True)
    regridded = regrid_on_time(stack)
    assert list(check_regrid(stack, regridded)) == [2]
    assert regridded.shape[0] == 5


def test_a_scanning_raster_and_other_data_are_refused(tmp_path, irispy_test_files):
    path = int16_raster_copy(find_irispy_test_file(irispy_test_files, SCAN), tmp_path / SCAN)
    [scan] = raster_data([path], ["C II 1336"])
    with pytest.raises(ValueError, match="steps of a scanning raster are places on the Sun"):
        regrid_on_time(scan)
    with pytest.raises(ValueError, match="not an IRIS sit-and-stare raster, slit-jaw image or stack"):
        regrid_on_time(Data(label="plain", x=np.zeros((3, 4, 5))))


@pytest.fixture
def app(qtbot):
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    return app


def test_the_action_adds_one_linked_dataset_and_no_viewer(app, monkeypatch, tmp_path, irispy_test_files):
    raster = sit_and_stare(tmp_path, irispy_test_files)
    sji = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
    scan = raster_data([int16_raster_copy(find_irispy_test_file(irispy_test_files, SCAN), tmp_path / SCAN)],
                       ["C II 1336"])[0]
    collection = app.data_collection
    collection.extend([sji, raster, scan])
    keep_hpc_linked(collection)
    tree = app._layer_widget
    action = tree._actions["Regrid on time"]
    tree.ui.layerTree.set_selected_layers([raster])
    assert action.isVisible()
    action.trigger()
    regridded = collection[-1]
    assert len(collection) == 4
    np.testing.assert_array_equal(regridded["Time"], regrid_on_time(raster)["Time"])
    assert not any(app.viewers)
    # its helioprojective coordinates are linked with the others'
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(regridded.world_component_ids[:2]) <= linked
    # a scanning raster is refused, and glue shows why
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree.ui.layerTree.set_selected_layers([scan])
    action.trigger()
    [text] = shown
    assert text.startswith("Could not regrid on time\n")
    assert "places on the Sun" in text
    assert len(collection) == 4
    tree.ui.layerTree.set_selected_layers([raster, sji])  # one dataset at a time
    assert not action.isVisible()


def test_the_quicklook_shows_a_regridded_raster(app, qtbot, tmp_path, irispy_test_files):
    raster = sit_and_stare(tmp_path, irispy_test_files)
    regridded = regrid_on_time(raster)
    # slit-jaw frames every 100 s: frame 3 falls in the raster's gap
    sji = image_data(with_times(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]),
                                100.0 * np.arange(62)))
    viewers = quicklook(app, [regridded, sji])
    [sji_viewer] = viewers["sji"]
    assert viewers["map"].state.reference_data is regridded
    times = regridded[regridded.id["Time"]][:, 0, 0]
    first, last = (np.datetime_as_string(t, unit="s") for t in (times[0], times[~np.isnat(times)][-1]))
    assert viewers["map"].state.x_axislabel == f"Time (3 s per pixel)\n{first} – {last[11:]} UTC"
    # a pixel in the gap has no time: the slit-jaw image keeps its frame, greyed
    spectrogram = viewers["spectrogram"]
    frame = sji_viewer.state.slices[0]
    spectrogram.state.slices = (GAP + 5, *spectrogram.state.slices[1:])
    qtbot.waitUntil(lambda: readout(sji_viewer).endswith(" · NO MATCH"))
    assert readout(spectrogram) == ""
    assert sji_viewer.state.slices[0] == frame
    # a slit-jaw master moves the raster to the pixel nearest each frame's time, never into the gap
    menu_action(sji_viewer, "Time master").trigger()
    [group] = app.session.edit_subset_mode.edit_subset
    for frame in (2, 3):
        sji_viewer.state.slices = (frame, 0, 0)
        offsets = np.abs(times - sji[sji.id["Time"]][frame, 0, 0]) / np.timedelta64(1, "s")  # NaN in the gap
        pixel = np.nanargmin(offsets)
        if offsets[pixel] <= 1.5:  # half the 3 s step
            qtbot.waitUntil(lambda pixel=pixel: group.subset_state.slices[0] == slice(pixel, pixel + 1))
        else:
            qtbot.waitUntil(lambda: "NO MATCH" in readout(spectrogram))
