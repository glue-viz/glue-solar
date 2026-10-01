"""
Lazily loaded IRIS data, on int16 copies of irispy's test files: Level 2 files store int16 with BSCALE and BZERO,
while irispy's test files hold float32.
"""

import numpy as np
import pytest
from glue.core.component_id import ComponentID
from glue.core.component_link import ComponentLink
from glue.core.data import Data

from astropy.io import fits

from glue_solar.conftest import find_irispy_test_file
from glue_solar.sources.loaders import lazy
from glue_solar.sources.loaders.lazy import LazyData, RawComponent, RawStack, allow_open_files, fill_mask

RASTER = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
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


@pytest.fixture
def int16_raster(tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, RASTER)
    with fits.open(source) as hdulist:
        windows = range(1, hdulist[0].header["NWIN"] + 1)
    return int16_copy(source, tmp_path / RASTER, windows)


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
