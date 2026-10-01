"""
Lazily loaded IRIS data, on int16 copies of irispy's test files: Level 2 files store int16 with BSCALE and BZERO,
while irispy's test files hold float32.
"""

from itertools import combinations

import numpy as np
import pytest
from glue.core.component import Component
from glue.core.component_id import ComponentID
from glue.core.component_link import ComponentLink
from glue.core.data import Data

from astropy.io import fits

from glue_solar.conftest import find_irispy_test_file
from glue_solar.sources.loaders import iris, lazy
from glue_solar.sources.loaders.iris import image_data, iris_data, raster_data
from glue_solar.sources.loaders.lazy import LazyData, RawComponent, RawStack, allow_open_files, fill_mask

RASTER = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
SJI = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
WINDOW = 5  # Si IV 1403, which holds missing data
BSCALE, BZERO = 0.25, 7992


def int16_copy(source, path, hdus, **header):
    """
    ``source`` written to ``path`` with the image HDUs ``hdus`` stored as Level 2 files store them, int16 with
    BSCALE 0.25 and BZERO 7992, and with -199 (missing), -199.5 and -5.25 (data) planted in each. ``header`` updates
    the primary header.
    """
    with fits.open(source) as hdulist:
        hdulist[0].header.update(header)
        for i in hdus:
            values = hdulist[i].data
            fill = values == -200
            values = np.clip(values, -199.75, 16000)
            values[fill] = -200
            values.flat[[1, 2, 3]] = -199, -199.5, -5.25  # raw -32764, -32766 and -32789
            hdulist[i].data = values
            hdulist[i].scale("int16", bscale=BSCALE, bzero=BZERO)
        hdulist.writeto(path)
    return path


def int16_raster_copy(source, path, **header):
    """The raster file ``source`` with every window stored as int16 (`int16_copy`)."""
    with fits.open(source) as hdulist:
        windows = range(1, hdulist[0].header["NWIN"] + 1)
    path.parent.mkdir(exist_ok=True)
    return int16_copy(source, path, windows, **header)


@pytest.fixture
def int16_raster(tmp_path, irispy_test_files):
    return int16_raster_copy(find_irispy_test_file(irispy_test_files, RASTER), tmp_path / RASTER)


def expected(path, hdu):
    """What eager loading gives: astropy's scaled values, with the missing codes -200 and -199 NaN."""
    values = fits.getdata(path, hdu)
    values[np.isin(values, (-200, -199))] = np.nan
    return values


def lazy_data(raw, label="raw"):
    """A dataset of ``raw`` and its mask, as the loader builds it."""
    data = LazyData(label=label)
    cid = data.add_component(RawComponent(raw, BSCALE, BZERO, (-200, -199)), label)
    data.add_component_link(ComponentLink([cid], ComponentID(f"{label} mask", parent=data), using=fill_mask))
    return data, cid, data.id[f"{label} mask"]


def raw_of(path, hdu):
    with fits.open(path, memmap=True, do_not_scale_image_data=True) as hdulist:
        return hdulist[hdu].data


def test_views_scale_only_what_they_select(int16_raster):
    raw, oracle = raw_of(int16_raster, WINDOW), expected(int16_raster, WINDOW)
    assert raw.dtype == ">i2"
    assert np.isnan(oracle).sum() > 1000
    assert (oracle == -199.5).any()
    for raw, oracle in ((raw, oracle), (raw[::-1], oracle[::-1])):  # a negative step, as irispy flips V34 rasters
        data, cid, mask = lazy_data(raw)
        n, ny, nl = data.shape
        index = np.arange(min(ny, nl))
        views = [
            (2,),
            (slice(None), 7),
            (slice(None), slice(None), nl // 2),
            (1, 2, 3),
            (slice(1, 5, 2), slice(None, None, -3)),
            (index % n, index, index),
            (oracle > 10,),
        ]
        for view in views:
            values = data[cid, view]
            assert values.dtype == np.float32
            np.testing.assert_array_equal(values, oracle[view])
            assert data[mask, view].dtype == np.uint8
            np.testing.assert_array_equal(data[mask, view], np.isnan(oracle[view]))
        np.testing.assert_array_equal(data.get_component(cid).data, oracle)  # the whole component, through dask
        eager = Data(values=oracle, mask=np.isnan(oracle).view(np.uint8), label="eager")
        for bounds in ([(0, n - 1, n), (0, ny - 1, ny), nl // 2], [n // 2, (0, ny - 1, 13), (0, nl - 1, 7)]):
            for cids in ((cid, eager.id["values"]), (mask, eager.id["mask"])):
                buffers = [d.compute_fixed_resolution_buffer(bounds, target_cid=c) for d, c in zip((data, eager), cids)]
                np.testing.assert_array_equal(*buffers)


def test_colour_limits_count_every_raw_value(int16_raster):
    data, cid, _ = lazy_data(raw_of(int16_raster, WINDOW))
    oracle = expected(int16_raster, WINDOW)
    # exactly what glue computes from every value of eager data: glue's 99.5% and 90% presets, and the median
    for percentile in (0.25, 5.0, 50.0, 99.75):
        exact = np.nanpercentile(oracle, percentile)
        assert data.compute_statistic("percentile", cid, percentile=percentile, random_subset=10000) == exact
    assert data.compute_statistic("minimum", cid, random_subset=10000) == np.nanmin(oracle) == -199.75
    assert data.compute_statistic("maximum", cid, random_subset=10000) == np.nanmax(oracle)
    positive = oracle[oracle > 0]
    lowest = data.compute_statistic("percentile", cid, percentile=1.0, positive=True, random_subset=10000)
    assert lowest == np.percentile(positive, 1.0)
    # glue's own statistics for anything else: a view or an axis
    eager = Data(values=oracle, label="eager")
    assert data.compute_statistic("percentile", cid, percentile=50, view=(0,)) == np.nanpercentile(oracle[0], 50)
    expected_maxima = eager.compute_statistic("maximum", eager.id["values"], axis=(0, 1))
    np.testing.assert_array_equal(data.compute_statistic("maximum", cid, axis=(0, 1)), expected_maxima)


def test_colour_limits_of_a_large_window_count_evenly_spaced_planes(monkeypatch, int16_raster):
    raw, oracle = raw_of(int16_raster, WINDOW), expected(int16_raster, WINDOW)
    monkeypatch.setattr(lazy, "SAMPLE_BYTES", 3 * raw[0].nbytes)  # three of the 187 steps: the first, middle and last
    data, cid, _ = lazy_data(raw)
    sample = oracle[[0, 93, 186]]
    for percentile in (0.25, 99.75):
        limit = data.compute_statistic("percentile", cid, percentile=percentile, random_subset=10000)
        assert limit == np.nanpercentile(sample, percentile)


def test_a_stack_reads_only_the_scans_it_selects(int16_raster):
    scans = [raw_of(int16_raster, WINDOW), raw_of(int16_raster, WINDOW)[::-1]]
    stack, whole = RawStack(scans), np.stack(scans)
    n, ny, nl = scans[0].shape
    index = np.arange(min(ny, nl))
    keys = [1, (0, 2), (slice(None), 3), (slice(None, None, -1), 1, slice(2, 5)), (index % 2, index % n, index, index)]
    for key in keys:
        np.testing.assert_array_equal(stack[key], whole[key])
    data, cid, _ = lazy_data(stack)
    np.testing.assert_array_equal(data[cid, (1, 2)], expected(int16_raster, WINDOW)[::-1][2])
    with pytest.raises(ValueError, match="same shape"):
        RawStack([scans[0], scans[1][:-1]])


@pytest.mark.parametrize(("soft", "hard", "raised"), [(256, 10**6, 10240), (256, 1000, 1000), (20000, 10**6, None)])
def test_open_file_limit_is_raised_never_lowered(monkeypatch, soft, hard, raised):
    import resource

    calls = []
    monkeypatch.setattr(resource, "getrlimit", lambda kind: (soft, hard))
    monkeypatch.setattr(resource, "setrlimit", lambda kind, limits: calls.append(limits))
    allow_open_files()
    assert calls == ([] if raised is None else [(raised, hard)])


def lazy_and_eager(monkeypatch, load):
    """What ``load()`` gives lazily, and as before, with `~glue_solar.sources.loaders.iris.LAZY` off."""
    lazy_result = load()
    monkeypatch.setattr(iris, "LAZY", False)
    eager = load()
    monkeypatch.setattr(iris, "LAZY", True)
    return lazy_result, eager


def assert_loads_as_before(lazy, eager):
    """
    ``lazy`` holds raw int16 and its mask is a glue derived component, while ``eager`` is laid out as before; every
    value, NaN, mask sample, time and exposure, and glue's image buffers of every pair of axes, are the same.
    """
    assert type(lazy) is LazyData
    assert type(eager) is Data
    [science, mask] = lazy.main_components[:1] + lazy.derived_components
    assert isinstance(lazy.get_component(science), RawComponent)
    assert [type(eager.get_component(cid)) for cid in eager.main_components[:2]] == [Component, Component]
    assert [cid.label for cid in lazy.components] == [cid.label for cid in eager.components]
    assert lazy.get_component(science).units == eager.get_component(eager.main_components[0]).units
    assert lazy[mask].dtype == np.uint8
    pairs = [(science, eager.main_components[0]), (mask, eager.main_components[1])]
    for name in ("Time", "Exposure time"):
        pairs.append((lazy.id[name], eager.id[name]))
    for lazy_cid, eager_cid in pairs:
        np.testing.assert_array_equal(lazy[lazy_cid], eager[eager_cid])
    for percentile in (0.25, 99.75):  # glue's 99.5% colour limits, exactly as from every eager value
        exact = np.nanpercentile(eager[eager.main_components[0]], percentile)
        assert lazy.compute_statistic("percentile", science, percentile=percentile, random_subset=10000) == exact
    for axes in combinations(range(lazy.ndim), 2):
        bounds = [(0, n - 1, n) if axis in axes else n // 2 for axis, n in enumerate(lazy.shape)]
        resampled = [(0, n - 1, 2 * n - 1) if axis in axes else n // 3 for axis, n in enumerate(lazy.shape)]
        for bounds in (bounds, resampled):
            for lazy_cid, eager_cid in pairs[:2]:
                np.testing.assert_array_equal(
                    lazy.compute_fixed_resolution_buffer(bounds, target_cid=lazy_cid),
                    eager.compute_fixed_resolution_buffer(bounds, target_cid=eager_cid),
                )


def test_int16_rasters_load_lazily_and_float32_ones_as_before(monkeypatch, tmp_path, int16_raster, irispy_test_files):
    for window in ("Si IV 1403", "Mg II k 2796"):
        assert_loads_as_before(*lazy_and_eager(monkeypatch, lambda: raster_data([int16_raster], [window])[0]))
    # File -> Open, every window
    for lazy_result, eager in zip(*lazy_and_eager(monkeypatch, lambda: iris_data(int16_raster)), strict=True):
        assert lazy_result.label == eager.label
        assert_loads_as_before(lazy_result, eager)
    # a negative raster step, which irispy flips (D10), and a gzipped file, held in memory as int16
    source = find_irispy_test_file(irispy_test_files, RASTER)
    flipped = int16_raster_copy(source, tmp_path / "flipped" / RASTER, STEPS_AV=-1.0)
    gzipped = int16_raster_copy(source, tmp_path / "gzipped" / f"{RASTER}.gz")
    for path in (flipped, gzipped):
        assert_loads_as_before(*lazy_and_eager(monkeypatch, lambda path=path: raster_data([path], ["Si IV 1403"])[0]))
    # irispy's float32 test file loads as before
    [float32] = raster_data([source], ["Si IV 1403"])
    assert type(float32) is Data
    assert [type(float32.get_component(cid)) for cid in float32.main_components[:2]] == [Component, Component]


def test_int16_stacks_load_lazily_scan_by_scan(monkeypatch, tmp_path, irispy_test_files):
    sources = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name)[:3]
    paths = [int16_raster_copy(source, tmp_path / source.name) for source in sources]
    [stack], [eager] = lazy_and_eager(monkeypatch, lambda: raster_data(paths, ["C II 1336"], stack=True))
    assert_loads_as_before(stack, eager)
    [science, mask] = stack.main_components[:1] + stack.derived_components
    for i, scan in enumerate(raster_data(paths, ["C II 1336"])):
        np.testing.assert_array_equal(stack[science, (i,)], scan[scan.main_components[0]])
        np.testing.assert_array_equal(stack[mask, (i,)], scan[scan.derived_components[0]])
        for name in ("Time", "Exposure time"):
            np.testing.assert_array_equal(stack[name][i], scan[name])


def test_int16_slit_jaw_and_aia_cubes_load_lazily(monkeypatch, tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, SJI)
    plain, gzipped = int16_copy(source, tmp_path / SJI, [0]), int16_copy(source, tmp_path / f"{SJI}.gz", [0])
    aia = tmp_path / "aia_l2_20210905_001833_3620258102_171.fits"
    int16_copy(source, aia, [0], INSTRUME="AIA_3", OBSID="20210905_001833_3620258102", TDESC1="171_THIN", TWAVE1=171)
    for path in (plain, gzipped, aia):
        lazy_result, eager = lazy_and_eager(monkeypatch, lambda path=path: image_data(path))
        assert_loads_as_before(lazy_result, eager)
        assert lazy_result.meta["scaled"]
    assert (lazy_result[lazy_result.main_components[0]] == -199).any()  # data in AIA cutouts, unverified as missing
    assert_loads_as_before(*lazy_and_eager(monkeypatch, lambda: iris_data(gzipped)))  # File -> Open


def test_lazy_rasters_in_glues_viewers_and_sessions(qtbot, monkeypatch, tmp_path, int16_raster):
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.histogram import HistogramViewer
    from glue_qt.viewers.image import ImageViewer

    [data] = raster_data([int16_raster], ["Si IV 1403"])
    oracle = expected(int16_raster, WINDOW)
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    layer = viewer.state.layers[0]
    layer.percentile = 99.5
    assert [layer.v_min, layer.v_max] == [np.nanpercentile(oracle, 0.25), np.nanpercentile(oracle, 99.75)]
    layer.attribute = data.derived_components[0]  # the mask draws too
    viewer.figure.canvas.draw()
    histogram = app.new_data_viewer(HistogramViewer, data=data)
    histogram.state.x_att = data.main_components[0]
    assert [histogram.state.hist_x_min, histogram.state.hist_x_max] == [np.nanmin(oracle), np.nanmax(oracle)]
    # a session cannot hold lazy data yet (WP3): glue reports it and writes nothing
    errors = []
    monkeypatch.setattr(app, "report_error", lambda message, detail: errors.append(message))
    app.save_session(str(tmp_path / "lazy.glu"))
    assert errors[0].startswith("Failed to save session")
    assert not (tmp_path / "lazy.glu").exists()


@pytest.mark.remote_data
def test_level_2_rasters_load_lazily_as_before(monkeypatch, irispy_data):
    negative_step = irispy_data("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz")
    gzipped = [irispy_data("iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz")]
    for files in (negative_step, gzipped):
        for lazy_result, eager in zip(*lazy_and_eager(monkeypatch, lambda files=files: raster_data(files)), strict=True):
            assert_loads_as_before(lazy_result, eager)


@pytest.mark.remote_data
def test_level_2_slit_jaw_and_aia_cubes_load_lazily_as_before(monkeypatch, irispy_data):
    paths = [irispy_data("iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz")]
    paths += irispy_data("iris_l2_20250519_165924_3640107442_cutout_SDO.tar.gz")  # nine AIA channels
    for path in paths:
        assert_loads_as_before(*lazy_and_eager(monkeypatch, lambda path=path: image_data(path)))
