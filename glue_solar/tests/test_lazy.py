"""
Lazily loaded IRIS data, on int16 copies of irispy's test files: Level 2 files store int16 with BSCALE and BZERO,
while irispy's test files hold float32.
"""

import gzip
import warnings
from itertools import combinations

import dask.array as da
import numpy as np
import pytest
from glue.core.component import Component
from glue.core.component_id import ComponentID
from glue.core.component_link import ComponentLink
from glue.core.data import Data
from glue.core.exceptions import IncompatibleAttribute
from glue.core.parse import ParsedCommand, ParsedComponentLink
from glue.core.subset import RangeSubsetState, SliceSubsetState
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.viewers.image.state import AggregateSlice
from irispy.io.sji import read_sji_lvl2
from matplotlib.backend_bases import KeyEvent

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
            values.flat[[1, 2, 3]] = -199, -199.5, -5.25  # raw -32764, -32766 and -31989
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


def zero_exposure(path, step):
    """``path`` with the FUV or slit-jaw exposure time of ``step`` 0 s, as 3610108077 records its Si IV step 157."""
    with fits.open(path, mode="update") as hdulist:
        aux = hdulist[-2]  # before the Level 1 file names
        aux.data[step, aux.header["EXPTIMES" if "EXPTIMES" in aux.header else "EXPTIMEF"]] = 0
    return path


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


class Reads:
    """``raw``, counting its reads and the values they return."""

    def __init__(self, raw):
        self.raw, self.shape, self.ndim, self.dtype, self.read, self.reads = raw, raw.shape, raw.ndim, raw.dtype, 0, 0

    def __getitem__(self, key):
        values = self.raw[key]
        self.read += np.size(values)
        self.reads += 1
        return values


def test_views_scale_only_what_they_select(int16_raster):
    raw, oracle = raw_of(int16_raster, WINDOW), expected(int16_raster, WINDOW)
    assert raw.dtype == ">i2"
    assert np.isnan(oracle).sum() > 1000
    assert (oracle == -199.5).any()
    for raw, oracle in ((raw, oracle), (raw[::-1], oracle[::-1])):  # a negative step, as irispy flips V34 rasters
        reads = Reads(raw)
        data, cid, mask = lazy_data(reads)
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
            reads.read = 0
            values = data[cid, view]
            assert reads.read == oracle[view].size
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
    # the values of a view too (see the next test); glue's own statistics for anything else: a subset or an axis
    eager = Data(values=oracle, label="eager")
    upper = data.compute_statistic("percentile", cid, percentile=99.75, view=(0,), random_subset=10000)
    assert upper == np.nanpercentile(oracle[0], 99.75)
    first = PixelSubsetState(data, [slice(0, 1), slice(None), slice(None)])
    assert data.compute_statistic("maximum", cid, subset_state=first, random_subset=10000) == np.nanmax(oracle[0])
    within = RangeSubsetState(5, 50, cid)  # a value range, whose mask glue reads through dask
    assert data.compute_statistic("minimum", cid, subset_state=within, random_subset=10000) == oracle[oracle >= 5].min()
    expected_maxima = eager.compute_statistic("maximum", eager.id["values"], axis=(0, 1))
    np.testing.assert_array_equal(data.compute_statistic("maximum", cid, axis=(0, 1)), expected_maxima)
    # NumPy's interpolation between unequal neighbours, in float32 to the last bit (compared as float64, as NumPy
    # compares a float32 with a Python float in float32)
    small, cid, _ = lazy_data(np.array([[[0, 1, 5, -32768]]], np.int16))
    for percentile in (20.0, 80.0):
        exact = float(np.nanpercentile(np.array([7992, 7992.25, 7993.25, np.nan], np.float32), percentile))
        assert small.compute_statistic("percentile", cid, percentile=percentile, random_subset=10000) == exact


def test_colour_limits_of_a_slice_count_its_values(int16_raster):
    # per-frame colour limits (glue's stretch_global off) of a raster map at one wavelength, a slice subset of more
    # values than the 10,000 glue picks at random: exactly those of every value, as for a view of the same slice
    raw = np.concatenate([raw_of(int16_raster, WINDOW)] * 2, axis=1)
    oracle = np.concatenate([expected(int16_raster, WINDOW)] * 2, axis=1)
    data, cid, _ = lazy_data(raw)
    for wavelength in (1, data.shape[2] // 2):
        view = (slice(None), slice(None), wavelength)
        assert np.isfinite(oracle[view]).sum() > 10000
        for where in ({"subset_state": SliceSubsetState(data, list(view))}, {"view": view}):
            for percentile in (0.25, 99.75):
                limit = data.compute_statistic("percentile", cid, percentile=percentile, random_subset=10000, **where)
                assert limit == np.nanpercentile(oracle[view], percentile)
            assert data.compute_statistic("maximum", cid, random_subset=10000, **where) == np.nanmax(oracle[view])
        # glue's own answers for the slice within a view, and for a slice of another dataset
        both = {"subset_state": SliceSubsetState(data, list(view)), "view": (0,)}
        assert data.compute_statistic("maximum", cid, random_subset=10000, **both) == np.nanmax(oracle[0, :, wavelength])
        with pytest.raises(IncompatibleAttribute):
            data.compute_statistic("maximum", cid, subset_state=SliceSubsetState(Data(x=oracle), list(view)))


def test_colour_limits_of_a_large_window_count_evenly_spaced_planes(monkeypatch, int16_raster):
    raw, oracle = raw_of(int16_raster, WINDOW), expected(int16_raster, WINDOW)
    monkeypatch.setattr(lazy, "SAMPLE_BYTES", 3 * raw[0].nbytes)  # three of the 187 steps: the first, middle and last
    data, cid, _ = lazy_data(raw)
    sample = oracle[[0, 93, 186]]
    for percentile in (0.25, 99.75):
        limit = data.compute_statistic("percentile", cid, percentile=percentile, random_subset=10000)
        assert limit == np.nanpercentile(sample, percentile)


def test_colour_limits_of_a_derived_attribute_sample_random_points(int16_raster):
    # a rate, as glue's arithmetic attribute editor makes it; glue's own sample of its ten dask chunk corners is fill
    [data] = raster_data([int16_raster], ["Si IV 1403"])
    rate = ComponentID("rate", parent=data)
    command = ParsedCommand("{raw} / {exposure}", {"raw": data.main_components[0], "exposure": data.id["Exposure time"]})
    data.add_component_link(ParsedComponentLink(rate, command))
    values = np.asarray(data[rate])
    for percentile, low, high in ((0.25, 0, 1), (50, 45, 55), (99.75, 99, 100)):
        limit = data.compute_statistic("percentile", rate, percentile=percentile, random_subset=10000)
        assert np.nanpercentile(values, low) <= limit <= np.nanpercentile(values, high)
    # per-frame limits: glue's own, of every value of a slice of fewer than 10,000, not a sample of the whole cube
    view = (slice(None), slice(None), 1)
    limit = data.compute_statistic("percentile", rate, percentile=99.75, random_subset=10000,
                                   subset_state=SliceSubsetState(data, list(view)))
    assert limit == np.nanpercentile(values[view], 99.75)


def test_a_stack_reads_only_the_scans_it_selects(int16_raster):
    raws = [raw_of(int16_raster, WINDOW), raw_of(int16_raster, WINDOW)[::-1]]
    scans = [Reads(raw) for raw in raws]
    stack, whole = RawStack(scans), np.stack(raws)
    n, ny, nl = raws[0].shape
    index = np.arange(min(ny, nl))
    keys = [1, (0, 2), (slice(None), 3), (slice(None, None, -1), 1, slice(2, 5)), (index % 2, index % n, index, index),
            (index[:0],) * 4, (np.array([1, 0]), 2, slice(None)), (np.array([[1], [0]]), slice(1, 3), 4)]
    for key in keys:
        for scan in scans:
            scan.read = scan.reads = 0
        np.testing.assert_array_equal(stack[key], whole[key])
        assert sum(scan.read for scan in scans) == whole[key].size
        assert all(scan.reads <= 1 for scan in scans)  # one read a scan, however its samples are spread
    data, cid, _ = lazy_data(stack)
    np.testing.assert_array_equal(data[cid, (1, 2)], expected(int16_raster, WINDOW)[::-1][2])
    assert data[cid, (np.array([0, 1]), 0, 2, slice(None))].shape == (2, nl)  # a spectrum of two scans
    with pytest.raises(ValueError, match="same shape"):
        RawStack([raws[0], raws[1][:-1]])


@pytest.mark.parametrize(("soft", "hard", "raised"), [(256, 10**6, 10240), (256, 1000, 1000), (20000, 10**6, None)])
def test_open_file_limit_is_raised_never_lowered(monkeypatch, soft, hard, raised):
    import resource

    calls = []
    monkeypatch.setattr(resource, "getrlimit", lambda kind: (soft, hard))
    monkeypatch.setattr(resource, "setrlimit", lambda kind, limits: calls.append(limits))
    allow_open_files()
    assert calls == ([] if raised is None else [(raised, hard)])


def lazy_and_eager(monkeypatch, load):
    """
    What ``load()`` gives lazily, and as before, with `~glue_solar.sources.loaders.iris.LAZY` off; only the lazy
    load raises the open-file limit.
    """
    raised = []
    monkeypatch.setattr(iris, "allow_open_files", lambda: raised.append(True))
    lazy_result = load()
    monkeypatch.setattr(iris, "LAZY", False)
    eager = load()
    monkeypatch.setattr(iris, "LAZY", True)
    assert raised == [True]
    return lazy_result, eager


def assert_loads_as_before(lazy, eager):
    """
    ``lazy`` holds raw int16 and its mask is a glue derived component, while ``eager`` is laid out as before; every
    value, NaN, mask sample, time, exposure and DN/s, and glue's image buffers of every pair of axes, are the same.
    DN/s, a glue derived component of both, is the data over a positive exposure time, else NaN, in float32.
    """
    assert type(lazy) is LazyData
    assert type(eager) is Data
    [science, mask, rate] = lazy.main_components[:1] + lazy.derived_components
    assert isinstance(lazy.get_component(science), RawComponent)
    assert [type(eager.get_component(cid)) for cid in eager.main_components[:2]] == [Component, Component]
    assert [cid.label for cid in lazy.components] == [cid.label for cid in eager.components]
    assert lazy.get_component(science).units == eager.get_component(eager.main_components[0]).units
    assert rate.label == f"{science.label} DN/s"
    assert [data.get_component(data.id[rate.label]).units for data in (lazy, eager)] == ["DN/s", "DN/s"]
    assert [data[rate.label].dtype for data in (lazy, eager)] == [np.float32, np.float32]  # the data's precision
    assert lazy[mask].dtype == np.uint8
    pairs = [(science, eager.main_components[0]), (mask, eager.main_components[1])]
    for name in ("Time", "Exposure time", rate.label):
        pairs.append((lazy.id[name], eager.id[name]))
    for lazy_cid, eager_cid in pairs:
        np.testing.assert_array_equal(lazy[lazy_cid], eager[eager_cid])
    exposure = eager["Exposure time"]
    oracle = eager[eager.main_components[0]] / np.where(exposure > 0, exposure, np.nan)
    np.testing.assert_allclose(lazy[rate], oracle, rtol=1e-6)
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
    # irispy's float32 test file loads as before, as do a file with only one window stored as int16 and one stored
    # as int32, more codes than the colour limits count
    (tmp_path / "partly").mkdir()
    partly = int16_copy(source, tmp_path / "partly" / RASTER, [WINDOW])
    int32 = tmp_path / "int32" / RASTER
    int32.parent.mkdir()
    with fits.open(int16_raster) as hdulist:
        for i in range(1, hdulist[0].header["NWIN"] + 1):
            hdulist[i].scale("int32", bscale=BSCALE, bzero=BZERO)
        hdulist.writeto(int32)
    for path in (source, partly, int32):
        [loaded] = raster_data([path], ["Si IV 1403"])
        assert type(loaded) is Data
        assert [type(loaded.get_component(cid)) for cid in loaded.main_components[:2]] == [Component, Component]


def test_raster_files_stored_differently_load_as_before(monkeypatch, int16_raster, irispy_test_files):
    # an int16 copy beside irispy's float32 file, which irispy reads first: each scan and their stack
    files = [int16_raster, find_irispy_test_file(irispy_test_files, RASTER)]
    for stack in (False, True):
        mixed = raster_data(files, ["Si IV 1403"], stack)
        monkeypatch.setattr(iris, "LAZY", False)
        eager = raster_data(files, ["Si IV 1403"], stack)
        monkeypatch.setattr(iris, "LAZY", True)
        for data, before in zip(mixed, eager, strict=True):
            np.testing.assert_array_equal(data[data.main_components[0]], before[before.main_components[0]])


def test_int16_stacks_load_lazily_scan_by_scan(monkeypatch, tmp_path, irispy_test_files):
    sources = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name)[:3]
    paths = [int16_raster_copy(source, tmp_path / source.name) for source in sources]
    [stack], [eager] = lazy_and_eager(monkeypatch, lambda: raster_data(paths, ["C II 1336"], stack=True))
    assert_loads_as_before(stack, eager)
    # a value subset, whose mask glue reads with an Ellipsis
    np.testing.assert_array_equal(*[(data.main_components[0] > 10).to_mask(data) for data in (stack, eager)])
    [science, mask, rate] = stack.main_components[:1] + stack.derived_components
    for i, scan in enumerate(raster_data(paths, ["C II 1336"])):
        np.testing.assert_array_equal(stack[science, (i,)], scan[scan.main_components[0]])
        np.testing.assert_array_equal(stack[mask, (i,)], scan[scan.derived_components[0]])
        np.testing.assert_array_equal(stack[rate, (i,)], scan[scan.derived_components[1]])  # each scan's exposures
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
    assert_loads_as_before(*lazy_and_eager(monkeypatch, lambda: iris_data(gzipped)))  # File -> Open


def test_dn_per_s_is_nan_where_an_exposure_took_0_s(monkeypatch, tmp_path, irispy_test_files):
    # as at step 157 of 3610108077 Si IV: a raster step, a slit-jaw frame and a step of a stack's second scan
    raster = zero_exposure(int16_raster_copy(find_irispy_test_file(irispy_test_files, RASTER), tmp_path / RASTER), 157)
    sji = zero_exposure(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]), 1)
    sources = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name)[:2]
    scans = [int16_raster_copy(source, tmp_path / source.name) for source in sources]
    zero_exposure(scans[1], 3)
    loads = {
        (157,): lambda: raster_data([raster], ["Si IV 1403"])[0],
        (1,): lambda: image_data(sji),
        (1, 3): lambda: raster_data(scans, ["C II 1336"], stack=True)[0],
    }
    for zero, load in loads.items():
        lazy_result, eager = lazy_and_eager(monkeypatch, load)
        assert_loads_as_before(lazy_result, eager)
        [science, _, rate] = lazy_result.main_components[:1] + lazy_result.derived_components
        assert lazy_result["Exposure time"][zero].max() == 0
        assert not np.isnan(lazy_result[science, zero]).all()
        assert np.isnan(lazy_result[rate, zero]).all()


def test_a_gzipped_slit_jaw_file_is_decompressed_once(monkeypatch, tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, SJI)
    plain, gzipped = int16_copy(source, tmp_path / SJI, [0]), int16_copy(source, tmp_path / f"{SJI}.gz", [0])
    reads = []
    monkeypatch.setattr(
        "irispy.io.sji.read_sji_lvl2",
        lambda file, **kwargs: reads.append((file, read_sji_lvl2(file, **kwargs))) or reads[-1][1],
    )
    expected = image_data(plain)
    assert expected.get_component(expected.main_components[0])._source.raw is reads[0][1].data  # irispy's memmap
    opened = []
    init = gzip.GzipFile.__init__
    monkeypatch.setattr(gzip.GzipFile, "__init__", lambda self, *args, **kwargs: (
        opened.append(True) or init(self, *args, **kwargs)
    ))
    data = image_data(gzipped)
    assert opened == [True]
    raw, [content, cube] = data.get_component(data.main_components[0])._source.raw, reads[1]
    assert raw is cube.data
    assert np.shares_memory(raw, np.frombuffer(content, np.uint8))  # a view of the decompressed bytes, uncopied
    assert data.label == expected.label
    # values, mask, times, exposures and every pixel's coordinates
    assert [cid.label for cid in data.components] == [cid.label for cid in expected.components]
    for cid, expected_cid in zip(data.components, expected.components):
        np.testing.assert_array_equal(data[cid], expected[expected_cid])
    assert data.meta.keys() == expected.meta.keys()
    for key, value in expected.meta.items():
        np.testing.assert_equal(data.meta[key], value)


def test_scripting_recipe_computes_spectra_of_lazy_data(int16_raster):
    # docs/user_guide/scripting-iris-data.rst, whose raster is lazy when stored as int16, as Level 2 files store it
    [raster] = raster_data([int16_raster], ["Si IV 1403"])
    step, slit = 90, 20
    cid = raster.main_components[0]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # wavelengths with no valid sample give NaN
        mean_spectrum = np.asarray(np.nanmean(raster[cid], axis=(0, 1), dtype=float))
        expected_mean = np.nanmean(expected(int16_raster, WINDOW), axis=(0, 1), dtype=float)
    point_spectrum = raster[cid, step, slit]
    assert type(mean_spectrum) is type(point_spectrum) is np.ndarray
    np.testing.assert_allclose(mean_spectrum, expected_mean)
    np.testing.assert_array_equal(point_spectrum, expected(int16_raster, WINDOW)[step, slit])


def test_lazy_rasters_in_glues_viewers_and_sessions(qtbot, monkeypatch, tmp_path, int16_raster):
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.histogram import HistogramViewer
    from glue_qt.viewers.image import ImageViewer
    from glue_qt.viewers.profile import ProfileViewer

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
    # and DN/s, with colour limits from random points, whose unit labels a profile
    rate = data.derived_components[1]
    rates = np.asarray(data[rate])
    layer.attribute = rate
    assert np.nanpercentile(rates, 0) <= layer.v_min <= np.nanpercentile(rates, 1)
    assert np.nanpercentile(rates, 99) <= layer.v_max <= np.nanpercentile(rates, 100)
    viewer.figure.canvas.draw()
    profile = app.new_data_viewer(ProfileViewer, data=data)
    profile.state.layers[0].attribute = rate
    profile.state.y_display_unit = "DN/s"  # which glue offers, as it refuses units it does not
    assert profile.state.y_axislabel == "Data values [DN/s]"
    histogram = app.new_data_viewer(HistogramViewer, data=data)
    histogram.state.x_att = data.main_components[0]
    assert [histogram.state.hist_x_min, histogram.state.hist_x_max] == [np.nanmin(oracle), np.nanmax(oracle)]
    # a session cannot hold lazy data yet (WP3): glue reports it and writes nothing. irispy's Quantity metadata fails
    # first, lazy or not, so it goes
    errors = []
    monkeypatch.setattr(app, "report_error", lambda message, detail: errors.append(detail))
    data.meta.clear()
    app.save_session(str(tmp_path / "lazy.glu"))
    assert "serialize dask.array" in errors[0]
    assert not (tmp_path / "lazy.glu").exists()


def test_per_frame_limits_follow_the_wavelength_lazily_and_as_before(qtbot, monkeypatch, int16_raster):
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.image import ImageViewer

    import glue_solar
    from glue_solar.tests.helpers import select_point

    glue_solar.setup()
    oracle = expected(int16_raster, WINDOW)
    app = GlueApplication()
    qtbot.addWidget(app)
    datasets = lazy_and_eager(monkeypatch, lambda: raster_data([int16_raster], ["Si IV 1403"])[0])
    stack = Data(label="stack", values=np.zeros((2, *oracle.shape)))
    app.data_collection.extend([*datasets, stack])
    for data in datasets:
        # a raster map, step against slit, of the wavelength on the slider, with a Pixel point
        viewer = app.new_data_viewer(ImageViewer, data=data)
        viewer.state.x_att, viewer.state.y_att = data.pixel_component_ids[:2]
        layer = viewer.state.layers[0]
        layer.percentile = 99.5
        whole = [layer.v_min, layer.v_max]
        select_point(viewer, 3, 5)
        other = next(other for other in datasets if other is not data)
        viewer.add_data(other)  # a layer of another dataset keeps its limits
        [other] = [state for state in viewer.state.layers if state.layer is other]
        viewer.add_data(data)  # a second layer of the dataset, already per frame: the first click turns both on
        twin = [state for state in viewer.state.layers if state.layer is data][1]
        twin.stretch_global = False
        pixel, button = viewer.toolbar.active_tool, viewer.toolbar.actions["solar:per_frame_limits"]
        for per_frame in (True, False):
            button.trigger()
            assert (layer.stretch_global, twin.stretch_global, other.stretch_global) == (not per_frame,) * 2 + (True,)
            assert viewer.toolbar.active_tool is pixel  # the Pixel tool stays on
            for wavelength in (1, 14, 20):
                viewer.state.slices = (0, 0, wavelength)
                limits = [np.nanpercentile(oracle[:, :, wavelength], p) for p in (0.25, 99.75)] if per_frame else whole
                assert [layer.v_min, layer.v_max] == limits
    # a 4D reference data, whose slices the layer cannot take: its whole cube's limits again, with a subset shown (a
    # value range, as glue fails to show a point on 4D data); a new choice of reference data keeps the limits
    button.trigger()
    app.data_collection.subset_groups[0].subset_state = RangeSubsetState(0, 10, data.main_components[0])
    viewer.add_data(stack)
    assert not layer.stretch_global
    viewer.state.reference_data = stack
    assert (layer.stretch_global, [layer.v_min, layer.v_max]) == (True, whole)


def test_raster_windows_and_stacks_open_in_their_detectors_colormap(qtbot, monkeypatch, tmp_path, int16_raster,
                                                                    irispy_test_files):
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.image import ImageViewer

    from sunpy.visualization.colormaps import cmlist

    # every window of the sit-and-stare raster through File -> Open, and four windows of two scans stacked, lazily
    # and as before: sunpy's IRIS FUV colormap for the FUV1 and FUV2 windows, its NUV one for the NUV windows
    fuv, nuv = "irissjiFUV", "irissjiNUV"
    bands = {"C_II_1336": fuv, "Fe_XII_1349": fuv, "O_I_1356": fuv, "Si_IV_1394": fuv, "Si_IV_1403": fuv,
             "2832": nuv, "2814": nuv, "Mg_II_k_2796": nuv}
    sources = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name)[:2]
    scans = [int16_raster_copy(source, tmp_path / source.name) for source in sources]
    windows = ["C II 1336", "Si IV 1403", "Mg II k 2796", "2832"]
    loads = (lambda: iris_data(int16_raster), lambda: raster_data(scans, windows, stack=True))
    datasets = [data for load in loads for results in lazy_and_eager(monkeypatch, load) for data in results]
    cmaps = [bands[data.label.split("-")[0]] for data in datasets]
    assert len(datasets) == 2 * (8 + 4)
    assert [data.style.preferred_cmap.name for data in datasets] == cmaps
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend(datasets[-4:])  # the stacks, as before
    for data, cmap in zip(datasets[-4:], cmaps[-4:]):
        assert app.new_data_viewer(ImageViewer, data=data).layers[0].state.cmap == cmlist[cmap]


def hover(viewer, x, y):
    """The status bar's readout with the mouse over data position ``x, y`` of the viewer's axes."""
    from glue_solar.tests.helpers import mouse

    mouse(viewer, "motion_notify_event", x, y)
    return viewer.statusBar().currentMessage()


def time_and_exposure(data, pixel):
    """What the readout gives after the position for ``pixel`` of ``data``: its own time and exposure there."""
    utc = np.datetime_as_string(data["Time"][pixel], unit="ms")
    return f" (world) · {utc} UTC · exp {data['Exposure time'][pixel]:.4g} s"


def test_readout_gives_the_hovered_raster_steps_time_and_exposure(qtbot, tmp_path, irispy_test_files):
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.image import ImageViewer

    import glue_solar
    from glue_solar.tests.helpers import select_point

    glue_solar.setup()
    sources = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name)[:3]
    paths = [int16_raster_copy(source, tmp_path / source.name) for source in sources]
    zero_exposure(paths[2], 5)
    [scan] = raster_data(paths[:1], ["C II 1336"])
    [stack] = raster_data(paths, ["C II 1336"], stack=True)
    assert stack["Exposure time"][2, 5, 0, 0] == 0  # so the readout must give the hovered scan's exposure
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([scan, stack])
    k = 8
    for data, scans in ((scan, ()), (stack, (2,))):
        assert isinstance(data, LazyData)
        # a raster map, step against slit, at wavelength k, in the Pixel mode the quicklook opens in
        viewer = app.new_data_viewer(ImageViewer, data=data)
        step_axis = len(scans)
        viewer.state.x_att, viewer.state.y_att = data.pixel_component_ids[step_axis : step_axis + 2]
        viewer.state.slices = (*scans, 0, 0, k)
        viewer.toolbar.active_tool = "image:point_selection"
        for step, slit in ((0, 10), (5, 50), (7, 100)):
            pixel = (*scans, step, slit, k)
            _, latitude, longitude = data.coords.pixel_to_world_values(*pixel[::-1])[:3]
            position = f'{latitude:.2f}" {longitude:.2f}"'  # the wavelength is on the slider
            assert hover(viewer, step, slit).startswith(position + time_and_exposure(data, pixel))
    # W switches WCSAxes to pixel positions, which the readout keeps
    canvas = viewer.figure.canvas
    canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", canvas, "w"))
    assert time_and_exposure(stack, (2, 5, 50, k)).replace("world", "pixel") in hover(viewer, 5, 50)
    # the Pixel tool still selects a point
    select_point(viewer, 5, 50)
    assert viewer.toolbar.active_tool.tool_id == "image:point_selection"
    [group] = app.data_collection.subset_groups
    assert [(s.start, s.stop) for s in group.subset_state.slices[1:3]] == [(5, 6), (50, 51)]


def test_readout_reads_the_time_along_sit_and_stare_exposures_and_slit_jaw_frames(qtbot, tmp_path, int16_raster,
                                                                                    irispy_test_files):
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.image import ImageViewer

    import glue_solar

    glue_solar.setup()
    [raster] = raster_data([int16_raster], ["Si IV 1403"])
    sji = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
    assert isinstance(raster, LazyData)
    assert isinstance(sji, LazyData)
    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.extend([raster, sji])
    viewer = app.new_data_viewer(ImageViewer, data=raster)
    slit, k = 20, 14
    for exposure in (0, 90, 186):
        pixel = (exposure, slit, k)
        wavelength, latitude, _ = raster.coords.pixel_to_world_values(k, slit, exposure)
        # λ–time: the wavelength and the hovered exposure's time, not where the slit pixel was then
        viewer.state.x_att, viewer.state.y_att = raster.pixel_component_ids[2], raster.pixel_component_ids[0]
        viewer.state.slices = (0, slit, 0)
        assert hover(viewer, k, exposure).startswith(f"{wavelength:.3f} Å" + time_and_exposure(raster, pixel))
        # slit against time: the latitude along the slit
        viewer.state.x_att, viewer.state.y_att = raster.pixel_component_ids[0], raster.pixel_component_ids[1]
        viewer.state.slices = (0, 0, k)
        assert hover(viewer, exposure, slit).startswith(f'{latitude:.2f}"' + time_and_exposure(raster, pixel))
    # a slit-jaw frame, and x against the frames
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    viewer.state.slices = (30, 0, 0)
    longitude, latitude, _ = sji.coords.pixel_to_world_values(10, 20, 30)
    assert hover(viewer, 10, 20).startswith(f'{longitude:.2f}" {latitude:.2f}"' + time_and_exposure(sji, (30, 20, 10)))
    viewer.state.slices = (AggregateSlice(slice(10, 15), 12, np.nansum), 0, 0)  # a Collapse: its middle frame's
    assert time_and_exposure(sji, (12, 20, 10)) in hover(viewer, 10, 20)
    viewer.state.x_att, viewer.state.y_att = sji.pixel_component_ids[0], sji.pixel_component_ids[2]
    viewer.state.slices = (0, 20, 0)
    for frame in (0, 30, sji.shape[0] - 1):
        assert time_and_exposure(sji, (frame, 20, 10)) in hover(viewer, frame, 10)


@pytest.mark.remote_data
def test_level_2_rasters_load_lazily_as_before(monkeypatch, irispy_data):
    negative_step = irispy_data("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz")
    gzipped = [irispy_data("iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz")]
    for files in (negative_step, gzipped):
        lazy_results, eager = lazy_and_eager(monkeypatch, lambda files=files: raster_data(files))
        for pair in zip(lazy_results, eager, strict=True):
            assert_loads_as_before(*pair)


@pytest.mark.remote_data
def test_level_2_slit_jaw_and_aia_cubes_load_lazily_as_before(monkeypatch, irispy_data):
    paths = [irispy_data("iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz")]
    paths += irispy_data("iris_l2_20250519_165924_3640107442_cutout_SDO.tar.gz")  # nine AIA channels
    for path in paths:
        assert_loads_as_before(*lazy_and_eager(monkeypatch, lambda path=path: image_data(path)))


# pvextractor imports spectral-cube, which uses astropy's deprecated COPY_IF_NEEDED where spectral-cube is installed,
# and glue's exporter names each HDU after its component, a longer EXTNAME than a FITS card holds with its comment
@pytest.mark.filterwarnings("ignore:COPY_IF_NEEDED is no longer needed")
@pytest.mark.filterwarnings("ignore:Card is too long")
def test_pv_slices_and_subset_exports_of_lazy_data(monkeypatch, tmp_path, int16_raster):
    from glue.config import data_exporter
    from glue_qt.plugins.tools.pv_slicer import pv_slicer

    from glue_solar import glue_patches

    assert pv_slicer._slice_from_path is glue_patches.pv_slice_from_path  # always, probing on the first slice
    assert glue_patches._pv_needs_workaround() == glue_patches.needs_pv_dask_workaround()  # glue-qt's own function
    assert not glue_patches.needs_pv_dask_workaround(glue_patches.pv_slice_from_path)
    exporter = next(exporter for exporter in data_exporter if exporter.label == "FITS (1 component/HDU)")
    installed = exporter.function is glue_patches.export_fits
    assert installed == glue_patches.needs_fits_export_dask_workaround()  # probes glue's own exporter
    assert not glue_patches.needs_fits_export_dask_workaround(glue_patches.export_fits)

    def dask_export(filename, subset):  # an upstream fix could keep the values dask, which astropy writes to a file
        values = subset.data[subset.data.main_components[0]]
        fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(da.where(subset.to_mask(), values, np.nan))]).writeto(filename)

    assert not glue_patches.needs_fits_export_dask_workaround(dask_export)

    lazy_result, eager = lazy_and_eager(monkeypatch, lambda: raster_data([int16_raster], ["Si IV 1403"])[0])
    path = (np.array([3.0, 25.0]), np.array([5.0, 30.0]))  # drawn on a spectrogram, slit against wavelength
    pv = pv_slicer._slice_from_path
    slices = [pv(*path, data, data.main_components[0], [0, "y", "x"]) for data in (lazy_result, eager)]
    np.testing.assert_array_equal(slices[0][0], slices[1][0])
    # a Pixel point exported: its spectrum, NaN elsewhere
    point = lazy_result.new_subset(PixelSubsetState(lazy_result, [slice(2, 3), slice(5, 6), slice(None)]))
    exporter.function(str(tmp_path / "point.fits"), point)
    oracle = expected(int16_raster, WINDOW)
    values = np.full(oracle.shape, np.nan, np.float32)
    values[2, 5] = oracle[2, 5]
    np.testing.assert_array_equal(fits.getdata(tmp_path / "point.fits", lazy_result.main_components[0].label), values)
    # and its mask, unsigned, whole
    mask = fits.getdata(tmp_path / "point.fits", lazy_result.derived_components[0].label)
    assert mask.dtype == np.uint8
    np.testing.assert_array_equal(mask, np.isnan(oracle))
