"""
'Regrid on time', on int16 copies of irispy's test files whose exposures, frames and scans are taken at known times;
'North up', on a rolled slit-jaw image and irispy's; and 'Rebin…', on int16 copies of irispy's test files.
"""

import warnings

import numpy as np
import pytest
from glue.core import Data
from glue.core.component_link import CoordinateComponentLink
from glue_qt.app.application import GlueApplication
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from scipy.interpolate import make_interp_spline

from astropy.io import fits

import glue_solar
from glue_solar.conftest import OBS_A, _header, _write_image, find_irispy_test_file, startobs
from glue_solar.quicklook import quicklook
from glue_solar.regrid import north_up, north_up_iris, rebin, regrid_on_time
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import _SJI_POINTING, image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.sources.loaders.lazy import LazyData, RawComponent
from glue_solar.sources.moments import line_moments
from glue_solar.tests.helpers import press
from glue_solar.tests.test_lazy import RASTER, SJI, int16_copy, int16_raster_copy, zero_exposure
from glue_solar.tests.test_quicklook import SCAN, expected_nearest, menu_action, readout

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
    # scan 2 left out, and scan 4 2 s late at its middle step, which times it, in shorter steps than the others; the
    # fixture's 3 scans, the first again for scan 4, in folders that sort in scan order, give the 4 a median cadence
    # that the gap leaves out
    for scan, source, start, step in ((0, 0, 0, 5.0), (1, 1, 60, 5.0), (3, 2, 180, 5.0), (4, 0, 246, 4.0)):
        path = tmp_path / f"scan{scan}" / sources[source].name
        paths.append(with_times(int16_raster_copy(sources[source], path), start + step * np.arange(8)))
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


def rolled_sji(tmp_path, roll):
    """A slit-jaw image of 3 frames rolled ``roll`` degrees, its samples numbered, pointing 1" further west a frame."""
    d, t, o = OBS_A
    path = tmp_path / f"iris_l2_{d}_{t}_{o}_SJI_1400_t000.fits"
    _write_image(path, _header("SJI", o, startobs(d, t), TDESC1="SJI_1400", TWAVE1=1400.0, NWIN=1), roll=roll)
    with fits.open(path, mode="update") as hdulist:
        hdulist[0].data[:] = np.arange(hdulist[0].data.size).reshape(hdulist[0].data.shape)
        aux = hdulist[1]
        aux.data[:, aux.header["XCENIX"]] += np.arange(len(aux.data))
    return image_data(path)


def north_angle(data, grid, frame):
    """
    The angle in degrees from the y axis of ``grid``'s pixels to solar north at the centre of ``data``'s frame
    ``frame``, and from that of ``data``'s own pixels, east of north positive.
    """
    _, ny, nx = data.shape
    lon, lat, time = data.coords.pixel_to_world_values((nx - 1) / 2, (ny - 1) / 2, frame)
    angles = []
    for coords in (grid.coords, data.coords):
        x, y, _ = coords.world_to_pixel_values([lon, lon], [lat, lat + 1], [time, time])
        angles.append(np.degrees(np.arctan2(x[0] - x[1], y[1] - y[0])))
    return angles


def test_north_up_shows_a_rolled_slit_jaw_image_north_up(app, tmp_path):
    sji = rolled_sji(tmp_path, 30)
    collection = app.data_collection
    collection.append(sji)
    keep_hpc_linked(collection)
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([sji])
    tree._actions["North up"].trigger()
    grid = collection[-1]
    [viewer] = app.viewers[0]
    assert viewer.state.reference_data is grid
    assert [(layer.layer, layer.visible) for layer in viewer.state.layers] == [(grid, False), (sji, True)]
    assert grid.label == f"{sji.label} north up"
    assert link_hpc(collection) == []
    # every frame lies on the grid, as its own pointing places it
    nt, ny, nx = sji.shape
    corners = np.meshgrid([-0.5, nx - 0.5], [-0.5, ny - 0.5], np.arange(nt))
    x, y, t = grid.coords.world_to_pixel_values(*sji.coords.pixel_to_world_values(*corners))
    assert np.all((x >= -0.5) & (x <= grid.shape[2] - 0.5) & (y >= -0.5) & (y <= grid.shape[1] - 0.5))
    np.testing.assert_allclose(t, corners[2], atol=1e-9)
    cid = sji.main_components[0]
    for frame in range(nt):
        viewer.state.slices = (frame, 0, 0)  # the grid's slider steps through the image's frames
        up, rolled = north_angle(sji, grid, frame)
        assert abs(up) < 0.001
        assert abs(rolled) == pytest.approx(30, abs=0.01)
        # glue draws each grid pixel with the frame's sample nearest it on the Sun, as the frame's own pointing
        # places it, and NaN off the frame
        gy, gx = np.mgrid[: grid.shape[1], : grid.shape[2]]
        sx, sy, st = sji.coords.world_to_pixel_values(*grid.coords.pixel_to_world_values(gx, gy, frame))
        sx, sy = np.round(sx).astype(int), np.round(sy).astype(int)
        inside = (sx >= 0) & (sx < nx) & (sy >= 0) & (sy < ny)
        expected = np.where(inside, np.asarray(sji[cid])[frame][np.clip(sy, 0, ny - 1), np.clip(sx, 0, nx - 1)], np.nan)
        np.testing.assert_allclose(st, frame, atol=1e-9)
        np.testing.assert_array_equal(viewer.state.layers[1].get_sliced_data(), expected)
    for other in (Data(label="plain", x=np.zeros((3, 4, 5))), grid):
        with pytest.raises(ValueError, match="not a slit-jaw image or aligned AIA cutout"):
            north_up(other)


def test_north_up_steps_through_irispys_slit_jaw_image(app, tmp_path, irispy_test_files):
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    raster = sit_and_stare(tmp_path, irispy_test_files)
    collection = app.data_collection
    collection.extend([raster, sji])
    keep_hpc_linked(collection)
    north_up_iris(sji, collection)
    grid = collection[-1]
    [viewer] = app.viewers[0]
    assert grid.shape[0] == sji.shape[0]
    # its own roll, 0.65°, more than half a degree
    for frame in (0, 30, sji.shape[0] - 1):
        viewer.state.slices = (frame, 0, 0)
        up, rolled = north_angle(sji, grid, frame)
        assert abs(up) < 0.001 < 0.5 < abs(rolled)
        assert readout(viewer) == f"{np.datetime_as_string(sji[sji.id['Time']][frame, 0, 0], unit='ms')} UTC"
        assert np.isfinite(viewer.state.layers[1].get_sliced_data()).any()
    press(viewer, Qt.Key_F)  # on, round from the last frame to the first: no time master moves it
    assert viewer.state.slices == (0, 0, 0)
    # its time is linked with the image's, and with no other dataset's, the datasets' own coordinates left out
    links = [link for link in collection.links if not isinstance(link, CoordinateComponentLink)]
    linked = [{link.get_to_id(), *link.get_from_ids()} for link in links]
    times = [cids for cids in linked if any(cid.label.startswith("Time") for cid in cids)]
    assert times == [{grid.world_component_ids[0], sji.world_component_ids[0]}]
    with pytest.raises(ValueError, match="not a slit-jaw image or aligned AIA cutout"):
        north_up(raster)


@pytest.mark.remote_data
def test_north_up_shows_an_aia_cutout_north_up(irispy_data):
    [path] = [p for p in irispy_data("iris_l2_20250519_165924_3640107442_cutout_SDO.tar.gz") if p.endswith("_171.fits")]
    aia = image_data(path)
    grid = north_up(aia)
    assert grid.shape[0] == aia.shape[0]
    assert abs(north_angle(aia, grid, 0)[0]) < 0.001


def binned(values, bins):
    """The nanmean of ``values`` over each bin of ``bins`` along its leading axes, the remainder left out, in float64."""
    values = np.asarray(values, dtype=float)
    cover = tuple(slice(0, length // n * n) for n, length in zip(bins, values.shape))
    shape = [part for n, length in zip(bins, values[cover].shape) for part in (length // n, n)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # a bin with every value missing: NaN
        return np.nanmean(values[cover].reshape(shape), axis=tuple(range(1, len(shape), 2))), values[cover]


@pytest.mark.parametrize("kind", ["raster", "sji"])
def test_rebin_takes_each_bins_mean_of_its_values_and_keeps_the_finite_mean(tmp_path, irispy_test_files, kind):
    """
    3 raster steps by 2 slit pixels of 3860258481's Si IV 1403, with missing samples, the steps past the last whole
    bin left out, and a step of 0 s, or 2 frames by 3 by 3 pixels of 3620258102's SJI 1400.
    """
    if kind == "raster":
        path = int16_raster_copy(find_irispy_test_file(irispy_test_files, SCAN), tmp_path / SCAN)
        [data] = raster_data([zero_exposure(path, 4)], ["Si IV 1403"])
        bins = (3, 2, 1)
    else:
        data = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
        bins = (2, 3, 3)
    data.coords.pointing_offset = (1.5, -0.5)  # 'Shift pointing…'
    rebinned = rebin(data, bins)
    cid = data.main_components[0]
    label = f"{data.label} rebinned {'x'.join(map(str, bins))}"
    expected, covered = binned(data[cid], bins)
    assert rebinned.label == label
    assert rebinned.shape == expected.shape == tuple(length // n for n, length in zip(bins, data.shape))
    assert rebinned.get_component(label).units == data.get_component(cid).units
    assert rebinned.style.preferred_cmap == data.style.preferred_cmap
    assert rebinned.meta["rebinned"] == bins
    assert rebinned.meta["INSTRUME"] == data.meta["INSTRUME"]
    assert not set(_SJI_POINTING) & set(rebinned.meta)
    assert rebinned.coords.pointing_offset == (1.5, -0.5)
    values = rebinned[label]
    assert values.dtype == np.float32
    assert np.isnan(expected).any()  # where every value is missing
    np.testing.assert_allclose(values, expected, rtol=1e-6, equal_nan=True)
    np.testing.assert_array_equal(rebinned[f"{label} mask"], np.isnan(expected))
    # the mean of the values, missing ones left out: the bins' means, each weighted by how many values it holds
    counts = binned(np.isfinite(covered), bins)[0] * np.prod(bins)
    assert np.nansum(values * counts) / counts.sum() == pytest.approx(np.nanmean(covered), rel=1e-6)
    # a pixel at its bin's centre
    pixels = [np.arange(length) for length in rebinned.shape[::-1]]
    pixels = np.meshgrid(*pixels, indexing="ij")
    centres = [(pixel + 0.5) * n - 0.5 for pixel, n in zip(pixels, bins[::-1])]
    np.testing.assert_allclose(
        rebinned.coords.pixel_to_world_values(*pixels), data.coords.pixel_to_world_values(*centres), rtol=1e-12
    )
    np.testing.assert_allclose(  # given pixels that broadcast, as the quicklook gives a slit-jaw image's frames
        rebinned.coords.pixel_to_world_values(0, 0, np.arange(2)),
        rebinned.coords.pixel_to_world_values(np.zeros(2), np.zeros(2), np.arange(2)),
    )
    # the mean time and exposure time of each bin, NaN where one is 0 s, over which its DN/s are its values
    times = data[data.id["Time"]][:, 0, 0]
    start = times[0]
    mean = start + (binned((times - start) / np.timedelta64(1, "ns"), bins[:1])[0]).astype("timedelta64[ns]")
    np.testing.assert_array_equal(rebinned[rebinned.id["Time"]][:, 0, 0], mean)
    seconds = data["Exposure time"][: len(mean) * bins[0], 0, 0]
    exposure = rebinned["Exposure time"][:, 0, 0]
    np.testing.assert_allclose(exposure, np.where(seconds > 0, seconds, np.nan).reshape(-1, bins[0]).mean(1), rtol=1e-6)
    assert list(np.flatnonzero(np.isnan(exposure))) == ([1] if kind == "raster" else [])
    np.testing.assert_allclose(rebinned[f"{label} DN/s"], values / exposure[:, None, None], rtol=1e-6, equal_nan=True)


def test_rebin_refuses_other_data_and_bins_that_do_not_fit(tmp_path, irispy_test_files):
    [scan] = raster_data(
        [int16_raster_copy(find_irispy_test_file(irispy_test_files, SCAN), tmp_path / SCAN)], ["Si IV 1403"]
    )
    with pytest.raises(ValueError, match="plain is not an IRIS raster window, slit-jaw image or AIA cutout"):
        rebin(Data(label="plain", x=np.zeros((3, 4, 5))), (1, 2, 2))
    for bins in ((2, 2), (0, 2, 1), (9, 2, 1)):
        with pytest.raises(ValueError, match=r"of \(8, 109, 29\) pixels, cannot be binned by"):
            rebin(scan, bins)


def test_the_rebin_action_adds_a_linked_dataset_that_follows_the_time_sync(
    app, qtbot, monkeypatch, tmp_path, irispy_test_files
):
    """
    The dialog opens at 2 by 2 pixels of the map or image; the dataset added, in the background, is linked, opens no
    viewer, and in a quicklook leads the time sync; its error maps are refused.
    """
    raster = sit_and_stare(tmp_path, irispy_test_files)
    sji = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
    collection, tree = app.data_collection, app._layer_widget
    collection.extend([raster, sji])
    keep_hpc_linked(collection)
    opened = []

    def exec_(dialog):
        opened.append([dialog.findChild(QtWidgets.QSpinBox, f"axis {axis}").value() for axis in range(3)])
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    for data in (raster, sji):
        tree.ui.layerTree.set_selected_layers([data])
        tree._actions["Rebin…"].trigger()
        assert app.statusBar().currentMessage() == f"Rebinning {data.label}…"
        qtbot.waitUntil(lambda: not iris._RUNNING)
    assert opened == [[2, 2, 1], [1, 2, 2]]  # exposures and slit pixels; y and x
    binned_raster, binned_sji = collection[-2:]
    assert binned_raster.shape == (raster.shape[0] // 2, raster.shape[1] // 2, raster.shape[2])
    assert binned_sji.shape == (sji.shape[0], sji.shape[1] // 2, sji.shape[2] // 2)
    assert app.statusBar().currentMessage() == ""
    assert not any(app.viewers)
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(binned_raster.world_component_ids[1:]) | set(binned_sji.world_component_ids[1:]) <= linked
    # the slit-jaw image follows the rebinned exposure's time
    viewers = quicklook(app, [binned_raster, binned_sji])
    [sji_viewer] = viewers["sji"]
    exposures, frames = (data[data.id["Time"]][:, 0, 0] for data in (binned_raster, binned_sji))
    assert [expected_nearest(exposures[exposure], frames) for exposure in (0, 30, 90)] == [0, 1, 2]
    for exposure in (30, 90):
        viewers["spectrogram"].state.slices = (exposure, *viewers["spectrogram"].state.slices[1:])
        qtbot.waitUntil(lambda e=exposure: sji_viewer.state.slices[0] == expected_nearest(exposures[e], frames))
    # other data are refused, and glue shows why
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    collection.append(plain)
    tree.ui.layerTree.set_selected_layers([plain])
    tree._actions["Rebin…"].trigger()
    assert shown == ["Could not rebin\nplain is not an IRIS raster window, slit-jaw image or AIA cutout."]
    with pytest.raises(ValueError, match="is rebinned: irispy would give each bin the noise of one sample"):
        line_moments(binned_raster, 1402.77, errors=True)
    assert np.isfinite(line_moments(binned_raster, 1402.77)["intensity"]).any()
