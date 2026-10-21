"""Prototype fixes and wall-clock timers for prof.py --patch NAME, as monkeypatches."""

import atexit
import time
from functools import wraps

TOTALS = {}


def _timed(owner, name, label=None):
    function = getattr(owner, name)
    label = label or f"{owner.__name__.rsplit('.', 1)[-1]}.{name}"

    @wraps(function)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            seconds, calls = TOTALS.get(label, (0.0, 0))
            TOTALS[label] = (seconds + time.perf_counter() - start, calls + 1)

    setattr(owner, name, wrapper)


def timers():
    """Wall time of the load's pieces, without a profiler's overhead, printed at exit (nested times overlap)."""
    import irispy.io.spectrograph as spectrograph
    import irispy.io.utils as utils
    import irispy.meta as meta
    import sunpy.coordinates.ephemeris as ephemeris
    from irispy import spectrograph as cubes

    from glue_solar.sources.loaders import iris, lazy, stack_spectrograms

    _timed(utils, "read_spectrograph_lvl2")  # as read_files calls it
    _timed(utils, "_primary_header")
    _timed(spectrograph, "_create_tabular_wcs")
    _timed(spectrograph, "_memmap_fill_mask")
    _timed(spectrograph, "SGMeta")
    _timed(spectrograph, "get_body_heliographic_stonyhurst")
    _timed(spectrograph, "_nuv_t_obs_from_source_filenames")
    _timed(spectrograph, "SpectrogramCube")
    _timed(spectrograph, "SpectrogramCubeSequence")
    _timed(spectrograph, "RasterCollection")
    _timed(spectrograph, "_set_wcs_aux_obs_coord")
    del meta, ephemeris, cubes
    import irispy.io

    _timed(irispy.io, "read_files")
    _timed(iris, "_window_scaling")
    _timed(iris, "_raster_collection_data")
    _timed(iris, "stack_times")
    _timed(iris, "stack_wcs")
    _timed(iris, "_dataset")
    _timed(iris, "_add_exposure")
    _timed(iris, "_add_time")
    _timed(iris, "_logged")
    _timed(iris, "_raster_windows_data")
    _timed(iris, "raster_files_data")
    _timed(iris, "image_data")
    _timed(lazy.RawComponent, "_sample", "RawComponent._sample")
    del stack_spectrograms

    @atexit.register
    def show():
        for label, (seconds, calls) in sorted(TOTALS.items(), key=lambda item: -item[1][0]):
            print(f"TIMER {seconds:8.2f} s {calls:7d} calls  {label}", flush=True)


# The spectral keys, the only cards that differ between the windows of a raster file (checked on 3860107071)
_SPECTRAL = ("NAXIS1", "CRVAL1", "CDELT1", "CRPIX1")


def tabular_once():
    """
    irispy: build the FITS-TAB WCS once a file and give each window a copy with its own spectral axis, rather than a
    BinTableHDU, a header and wcslib's parse of both per window (`_create_tabular_wcs`).
    """
    import copy

    import astropy.units as u
    import irispy.io.spectrograph as spectrograph

    build, cache = spectrograph._create_tabular_wcs, {}

    def _create_tabular_wcs(header, auxiliary_hdu, *, date_obs, flip=False):
        key = (tuple((k, v) for k, v in header.items() if k not in _SPECTRAL), date_obs, flip)
        if cache.get("aux") is not auxiliary_hdu or key not in cache:
            if cache.get("aux") is not auxiliary_hdu:  # a new file: one entry a file, held while it is read
                cache.clear()
                cache["aux"] = auxiliary_hdu
            cache[key] = (build(header, auxiliary_hdu, date_obs=date_obs, flip=flip), header)
        made, first = cache[key]
        wcs = copy.deepcopy(made)
        scale = u.Unit(header["CUNIT1"]).to(wcs.wcs.cunit[0])  # wcslib holds the spectral axis in SI
        wcs.wcs.crval[0], wcs.wcs.cdelt[0] = header["CRVAL1"] * scale, header["CDELT1"] * scale
        wcs.wcs.crpix[0] = header["CRPIX1"]
        wcs.wcs.set()
        wcs.pixel_shape = (header["NAXIS1"], *made.pixel_shape[1:])
        return wcs

    spectrograph._create_tabular_wcs = _create_tabular_wcs
    return build


def meta_dict():
    """irispy: each window's SGMeta from one dict of the primary header a file, not a walk of its 412 cards a window."""
    import irispy.io.spectrograph as spectrograph

    original, last = spectrograph.SGMeta, [None, None]

    def SGMeta(header, window, **kwargs):
        if last[0] is not header:
            last[:] = header, dict(header.items())  # as NDMeta copies it
        meta = original(last[1], window, **kwargs)
        meta._original_meta = meta._fits_header = header
        return meta

    spectrograph.SGMeta = SGMeta
    return original


def times_table():
    """glue-solar: a stack's times from each scan's time table, not ndcube's gWCS of its extra coordinates."""
    import numpy as np

    from glue_solar.sources.loaders import iris

    def stack_times(cube_sequence):
        tables = [cube.extra_coords["time"]._lookup_tables[0][1].table for cube in cube_sequence]
        return np.stack([table.utc.to_value("datetime64") for table in tables])

    iris.stack_times = stack_times


def all_fixes():
    tabular_once()
    meta_dict()
    times_table()


def check(path):
    """The prototypes give what irispy and glue-solar give, on every window of the raster file ``path``."""
    import numpy as np

    from astropy.io import fits
    from irispy.io import read_files

    from glue_solar.sources.loaders.stack_spectrograms import stack_times

    before = read_files([path], memmap=True, uncertainty=False)
    original_times = {w: stack_times(before[w]) for w in before}
    build, sgmeta = tabular_once(), meta_dict()
    times_table()
    from glue_solar.sources.loaders import iris

    after = read_files([path], memmap=True, uncertainty=False)
    rng = np.random.default_rng(1)
    with fits.open(path) as hdulist:
        for i, window in enumerate(before, 1):
            old, new = before[window][0], after[window][0]
            shape = old.wcs.low_level_wcs.pixel_shape
            assert new.wcs.low_level_wcs.pixel_shape == shape
            pixels = [rng.uniform(-0.5, n - 0.5, 200) for n in shape]
            for a, b in zip(old.wcs.low_level_wcs.pixel_to_world_values(*pixels),
                            new.wcs.low_level_wcs.pixel_to_world_values(*pixels)):
                np.testing.assert_allclose(a, b, rtol=1e-12, atol=1e-14)
            assert old.wcs.low_level_wcs.to_header() == new.wcs.low_level_wcs.to_header()
            assert dict(old.meta) .keys() == dict(new.meta).keys()
            assert all(np.all(old.meta[k] == new.meta[k]) for k in old.meta if not hasattr(old.meta[k], "frame"))
            assert new.meta.fits_header is hdulist[0].header or new.meta.fits_header == old.meta.fits_header
            assert new.meta.spectral_window == old.meta.spectral_window
            assert (iris.stack_times(after[window]) == original_times[window]).all()
    print("CHECK ok", len(before), "windows")
