"""
What a dataset is, as the quicklook, the viewer tools, the readers and the analyses ask it: its role and observation
(`role`, `observation_key`), its times and the axis they run along (`times`, `time_axis`, `nearest`), its wavelengths
and window (`wavelengths`, `window`), its axes (`cube_axes`, `hpc`) and where its pixels are on the Sun (`lon_lat`,
`frame_pixels`, `sji_to_raster`). It must not import Qt, glue-qt or matplotlib: it is for every module, GUI or not.
"""

import numpy as np

import astropy.units as u

from glue_solar.sources.dkist import DKISTData, _frame_axis, _slit, _SlitAt
from glue_solar.sources.loaders.iris import _HPC, _axes_of
from glue_solar.sources.loaders.scan import _observation

# The window the quicklook shows when the browser did not pick one
DEFAULT_WINDOW = "Mg II k 2796"


def observation_key(data):
    """
    The ``(OBSID, STARTOBS)`` pair that identifies the IRIS observation ``data`` belongs to, or None.

    The OBSID alone names an observing program, which runs many times, so both are needed. An SST cube's is that of the
    IRIS observation it is linked to (`~glue_solar.sources.loaders.iris.link_hpc`), else the one it shares with the SST
    cubes whose scan times overlap, or lie within a cadence of, its own (`Coordinator`), or before its collection has a
    coordinator ``('SST', DATE-OBS)``. A DKIST spectrograph's dataset and its context imager's share ``('DKIST', their
    observing program execution)`` once their collection has a coordinator, and other DKIST datasets have none.
    """
    if isinstance(data, DKISTData):
        return vars(data).get("_solar_time_key")
    meta = getattr(data, "meta", None) or {}
    obsid, start = meta.get("OBSID"), meta.get("STARTOBS")
    if role(data) == "sst":
        obsid, start = (
            meta.get("IRIS observation") or vars(data).get("_solar_time_key") or ("SST", meta.get("DATE-OBS"))
        )
    if obsid is None or start is None:
        return None
    try:
        start = np.datetime64(str(start), "ns")
    except ValueError:
        return None
    return None if np.isnat(start) else (_observation(obsid, start)[0], start)


def nearest(query, reference):
    """
    The index of the reference time nearest each query time, and the signed offset reference − query.

    The reference may be unsorted or descending, as a negative-step raster's times are. Ties go to the
    earlier time and equal times to the first index. Queries outside the reference's span get its
    nearest end, with the offset showing how far off it is.

    Parameters
    ----------
    query, reference : array-like of `numpy.datetime64`
        ``reference`` is one-dimensional and holds a time; its NaT, the gaps of data regridded on time, are never
        the nearest.

    Returns
    -------
    index : `numpy.ndarray` of int
    offset : `numpy.ndarray` of `numpy.timedelta64`
    """
    reference = np.asarray(reference, dtype="datetime64[ns]")
    query = np.asarray(query, dtype="datetime64[ns]")
    if reference.ndim != 1 or np.isnat(reference).all():
        raise ValueError("the reference times must be one-dimensional and hold a time")
    order = np.argsort(reference, kind="stable")  # equal times keep their order, so the first comes first
    order = order[~np.isnat(reference[order])]  # NaT sorts last
    ref = reference[order].view("int64")
    q = query.view("int64")
    if len(ref) == 1:
        pick = np.zeros(q.shape, dtype=int)
    else:
        after = np.clip(np.searchsorted(ref, q), 1, len(ref) - 1)
        before = after - 1
        pick = np.where(q - ref[before] <= ref[after] - q, before, after)  # a tie goes to the earlier time
    index = order[np.searchsorted(ref, ref[pick])]  # the first of equal times
    return index, reference[index] - query


def lon_lat(data, pixel):
    """Helioprojective longitude and latitude (arcsec) of ``data`` at the numpy-ordered ``pixel``."""
    world = data.coords.pixel_to_world_values(*pixel[::-1])
    types = list(data.coords.world_axis_physical_types)
    return tuple(np.asarray(world[types.index(kind)]) for kind in _HPC)


def placeable(data):
    """Whether helioprojective positions can be placed in ``data``'s frames through its coordinates."""
    types = getattr(data.coords, "world_axis_physical_types", None) or ()
    return {*_HPC, "time"} <= set(types)


def frame_pixels(data, at, lon, lat):
    """
    The pixels, (x, y) along its last two axes, of ``data``'s frame at the numpy-ordered ``at``, such as a slit-jaw or
    DKIST context image's, at helioprojective ``lon`` and ``lat`` (arcsec), at that frame's time and other axes.
    """
    types = list(data.coords.world_axis_physical_types)
    world = list(data.coords.pixel_to_world_values(*at[::-1]))
    for kind, angle in zip(_HPC, (lon, lat)):
        world[types.index(kind)] = angle
    x, y, *_ = data.coords.world_to_pixel_values(*np.broadcast_arrays(*world))
    return x, y


def sji_to_raster(sji, frame, x, y, raster):
    """
    The pixel of ``raster`` under pixel ``x, y`` of the slit-jaw image ``sji``'s frame ``frame``, placed with that
    frame's own pointing.

    A scanning raster's step and slit row are those nearest that place. A sit-and-stare raster's exposure is the one
    nearest the frame's time, as its slit stays in place, if within half its cadence, and its slit row the one
    level with the pixel, beside the slit too. A stack's scan is the one nearest the frame's time at the step scan 0
    places there, however far from it, and its step and slit row are those nearest that place with that scan's own
    pointing.

    Parameters
    ----------
    sji : `~glue.core.data.Data`
        A slit-jaw image as glue-solar loads it.
    frame : int
    x, y : float
    raster : `~glue.core.data.Data`
        A raster or a stack of scans as glue-solar loads them, of the same observation.

    Returns
    -------
    tuple of int, or None
        ``(step, slit)``, a stack's ``(scan, step, slit)``, or None outside the raster: more than half a step past
        its first or last step or half a pixel past either end of its slit, or for a sit-and-stare more than half a
        cadence from its exposures.
    """
    lon, lat = lon_lat(sji, (frame, y, x))
    when = times(sji, None)[frame]
    steps, rows = raster.shape[-3:-1]
    if raster.ndim == 3 and is_sit_and_stare(raster):
        # the slit row from the slit's ends: the raster's world-to-pixel is slow here, and ambiguous along time
        raster_times = times(raster, None)
        [step], [offset] = nearest([when], raster_times)
        if abs(offset) > half_cadence(raster_times):
            return None
        lons, lats = lon_lat(raster, (np.full(2, step), [0, rows - 1], np.zeros(2)))
        along = np.array([lons[1] - lons[0], lats[1] - lats[0]]) / (rows - 1)  # one slit pixel
        slit = np.dot([lon - lons[0], lat - lats[0]], along) / np.dot(along, along)
    else:
        # from each step's slit as a line, as a DKIST raster's (`_SlitAt`), NaN past half a step beyond a first or last
        # step: WCSLIB's -TAB inverse has no pixel past their centers, which a stack's later scans drift across
        def place(scan):
            _, starts, pixels = _slit(raster, raster.ndim - 3, {0: scan} if raster.ndim == 4 else None)
            return (_SlitAt(starts, pixels, along)(lon, lat) for along in (False, True))

        scan = 0
        step, slit = place(scan)
        if raster.ndim == 4 and 0 <= np.round(step) < steps:  # again in the scan's own pointing
            [scan], _ = nearest([when], times(raster, int(np.round(step))))
            step, slit = place(scan)
    step, slit = np.round(step), np.round(slit)
    if not (0 <= step < steps and 0 <= slit < rows):
        return None
    index = (int(step), int(slit))
    return index if raster.ndim == 3 else (int(scan), *index)


def time_axis(data):
    """
    The axis along which ``data`` steps through time (frames, exposures or scans), or None for a scanning raster, whose
    steps are places on the Sun; a DKIST pair's frames or raster steps (`_frame_axis`).
    """
    if dkist(data):
        return _frame_axis(data)
    kind = role(data)
    if kind in ("sji", "aia", "sst") or (kind == "raster" and (data.ndim == 4 or is_sit_and_stare(data))):
        return 0
    return None


def timed(data):
    """
    Whether ``data`` takes part in time sync: an IRIS dataset, aligned AIA cutout, SST cube or DKIST dataset of a pair
    (`dkist`) with times.
    """
    timed = role(data) in ("raster", "sji", "aia", "sst") or dkist(data)
    return bool(timed) and data.find_component_id("Time") is not None


def times(data, step):
    """
    The 1-D times of ``data``: per frame, exposure or step, per scan at raster step ``step`` of a stack, or per scan of
    an SST cube at its line core, as `~glue_solar.sources.loaders.iris.link_hpc` times them; a DKIST pair's along its
    frames or steps, at ``step``'s (axis, index) pairs, such as its repeat's (`Coordinator._timing`).
    """
    index = [0] * data.ndim
    index[time_axis(data) or 0] = slice(None)  # a DKIST pair's at its other axes' first pixels, but ``step``'s
    if role(data) == "sst":
        index[-3] = data.coords.core  # its tuning (`glue_solar.sources.sst.sst_data`)
    elif data.ndim == 4 and role(data) == "raster":
        index[1] = step
    elif dkist(data):
        for axis, at in step or ():
            index[axis] = at
    return data[data.find_component_id("Time"), tuple(index)]


def cadence(times):
    """The median interval between successive times, NaT left out, or 0 without two different times."""
    steps = np.diff(np.sort(times)).astype("timedelta64[ns]").view("int64")
    steps = steps[steps > 0]  # NaT sorts last, and its intervals are the least int64
    return np.timedelta64(int(np.median(steps)) if len(steps) else 0, "ns")


def half_cadence(times):
    """Half the median interval between successive times: the widest offset that still matches."""
    return cadence(times) / 2


def spectral_axes(data):
    """The array axes of ``data`` along which the wavelength varies."""
    return _axes_of(data, "em.wl")


def role(data):
    """
    'raster', 'sji', 'aia', 'sst' or None, from the INSTRUME keyword: AIA cutouts and Hinode/SOT cubes load as slit-jaw
    cubes and follow the time as they do, without their quicklook panel, raster point or overlays; SST CRISP and
    CHROMIS cubes step through time by scan, and have a quicklook of their own (`_cube_table`).
    """
    meta = getattr(data, "meta", None) or {}
    instrument = str(meta.get("INSTRUME") or "")
    if instrument.startswith(("AIA", "SOT")):
        return "aia"
    return {"SPEC": "raster", "SJI": "sji", "CRISP": "sst", "CHROMIS": "sst"}.get(instrument)


IRIS_ROLES = ("raster", "sji", "aia")  # an IRIS observation's own data, whose point `_link_points` leaves alone


def image_cube(data):
    """
    Whether ``data`` is an image cube of an IRIS observation, placed frame by frame: a slit-jaw image, or an aligned AIA
    cutout or Hinode/SOT cube, which a quicklook of its observation takes as it takes a slit-jaw image.
    """
    return role(data) in ("sji", "aia")


def dkist(data):
    """
    'raster' or 'imager' for a DKIST spectrograph's dataset or its context imager's tile observed with it, which share a
    time key (`observation_key`), as IRIS's raster and slit-jaw images; else None.
    """
    if not isinstance(data, DKISTData) or observation_key(data) is None:
        return None
    return "raster" if spectral_axes(data) else "imager"


def is_raster(data):
    """Whether ``data`` is a raster of either instrument: IRIS's (`role`) or a DKIST spectrograph's (`dkist`)."""
    return role(data) == "raster" or dkist(data) == "raster"


def is_context_image(data):
    """
    Whether ``data`` is an image of either instrument placed frame by frame: IRIS's (`image_cube`) or a DKIST context
    imager's (`dkist`).
    """
    return image_cube(data) or dkist(data) == "imager"


def hpc(data):
    """
    The world axes of the helioprojective longitude and latitude of ``data``, in WCS order, and its pixel axes along
    which only they vary, in glue's order, or None.
    """
    wcs = data.coords
    types = list(getattr(wcs, "world_axis_physical_types", None) or ())
    if not set(_HPC) <= set(types):
        return None
    world = [types.index(physical_type) for physical_type in _HPC]
    matrix = np.asarray(wcs.axis_correlation_matrix)
    spatial = matrix[world].any(axis=0) & ~np.delete(matrix, world, axis=0).any(axis=0)
    return world, [data.ndim - 1 - axis for axis in np.nonzero(spatial)[0]]


def same_file(data, other):
    """
    Whether ``data`` and ``other`` are windows of one raster file or stack, which share their scans, steps or exposures
    and slit pixels: one observation, shape but wavelength, DATE_OBS and ``meta['raster files']``.
    """
    if data is other:
        return data is not None
    return (
        role(data) == role(other) == "raster"
        and observation_key(data) == observation_key(other)
        and data.shape[:-1] == other.shape[:-1]
        and all(data.meta.get(key) == other.meta.get(key) for key in ("DATE_OBS", "raster files"))
    )


def wavelengths(data):
    """The wavelength of each pixel along the spectral axis of ``data``, in Angstrom, and that axis."""
    [axis] = spectral_axes(data)
    index = [0] * data.ndim
    index[axis] = slice(None)
    unit = u.Unit(data.coords.world_axis_units[data.coords.world_n_dim - 1 - axis])  # glue's world axis
    return (data[data.world_component_ids[axis], tuple(index)] * unit).to_value(u.AA), axis


def window(data):
    """
    The name and TWAVE of the window ``data`` holds, from the TWAVEn inside its wavelengths, as every window's keywords
    describe window 1; (None, None) if none is.
    """
    meta = data.meta
    wave, _ = wavelengths(data)
    for n in range(1, int(meta.get("NWIN", 0) or 0) + 1):
        twave = meta.get(f"TWAVE{n}")
        if twave is not None and np.nanmin(wave) <= float(twave) <= np.nanmax(wave):
            return str(meta.get(f"TDESC{n}")), float(twave)
    return None, None


def is_sit_and_stare(data):
    meta = data.meta
    return float(meta.get("STEPS_AV", -1) or 0) == 0 and int(meta.get("NRASTERP", 0) or 0) == 1


def cube_axes(data):
    """
    The array axes of ``data`` by the world coordinates along them, ``(time, Stokes, wavelength, y, x)``, None for
    those it does not have: one wavelength axis, of two wavelengths or more, two others of position, on the sky or the
    Sun, and any of time and Stokes parameter; or None for data of other axes. A slit raster's steps are x and its slit
    y, as IRIS's maps, and the other axes its pointing moves along, a DKIST raster's repeats or measurements, are left
    to sliders, as Stokes.
    """
    types = [str(kind) for kind in getattr(data.coords, "world_axis_physical_types", None) or ()]
    matrix = getattr(data.coords, "axis_correlation_matrix", None)
    if not types or np.shape(matrix) != (len(types), data.ndim):
        return None

    def along(*kinds):  # APE 14 orders pixel axes opposite to numpy
        worlds = [world for world, kind in enumerate(types) if kind.startswith(kinds)]
        return {data.ndim - 1 - pixel for pixel in np.flatnonzero(matrix[worlds].any(axis=0)).tolist()}

    wave = along("em.wl")
    stokes = along("phys.polarization.stokes") - wave
    place = along("pos.", "custom:pos.") - wave - stokes
    time = along("time") - wave - stokes
    moving = place
    if len(place) > 2:  # those glue gives a position, as a DKIST raster's where its pointing moves most (`_glue_order`)
        place = {axis for axis in place if types[len(types) - 1 - axis].startswith(("pos.", "custom:pos."))}
    steps = time & place  # a slit raster's step, whose time changes too, is a place
    sliders = moving - place if steps else set()  # its repeats or measurements, raveled with its steps
    time -= place | sliders
    sizes = len(time), len(stokes), len(wave), len(place)
    if sizes[2:] != (1, 2) or max(sizes[:2]) > 1 or sum(sizes) + len(sliders) != data.ndim or data.shape[min(wave)] < 2:
        return None  # one wavelength has no spectrum
    y, x = sorted(place, key=lambda axis: (axis in steps, axis))
    return (next(iter(time), None), next(iter(stokes), None), *wave, y, x)
