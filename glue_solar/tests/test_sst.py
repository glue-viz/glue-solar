"""
SST CRISP and CHROMIS cubes, on small files written as the SST archive's SSTRED exports are: File → Open gives the cube
alone, memory-mapped, with its time and wavelength at every pixel, its cavity maps and coordinates that sessions keep,
and once linked on request a region drawn on it selects the IRIS pixels at its place in the scan nearest their time.
The SST quicklook shows one cube in a tab, its panels on one point and one time, which other cubes and, once linked,
IRIS data share.
"""

import copy
import mmap
import sys
import threading

import glue.config
import numpy as np
import pytest
from glue.core import Data, DataCollection
from glue.core.autolinking import find_possible_links
from glue.core.data_factories import load_data
from glue.core.exceptions import IncompatibleAttribute
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from glue_qt.viewers.profile.layer_artist import QThreadedProfileLayerArtist
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.wcs.wcsapi.fitswcs
from astropy.io import fits
from astropy.wcs import WCS

import glue_solar
from glue_solar.quicklook import (
    QuicklookImageViewer,
    _role,
    _timed,
    _times,
    coordinator,
    nearest,
    observation_key,
    quicklook,
)
from glue_solar.sources.iris import iris_quicklook, link_iris, quicklook_iris, quicklook_sst
from glue_solar.sources.loaders.iris import WCS_LOCK, _LockedWCS, image_data, keep_hpc_linked, raster_data
from glue_solar.sources.loaders.scan import scan_directory
from glue_solar.sources.sst import _Cube, _line_core, _LockedTabularWCS, _TabularWCS, sst_data
from glue_solar.tests.helpers import mouse_click, press, select_point
from glue_solar.tests.test_linking import RASTER, SJI, _real
from glue_solar.tests.test_quicklook import (
    bare_app_for,
    browse,
    changes,
    entries,
    menu_action,
    panels_list,
    point_window,
    rows,
    settle,
    slide,
    tick,
)

DATEREF = "2021-09-05T00:00:00"


@pytest.fixture
def sns(irispy_test_files):
    """irispy's sit-and-stare SJI 1400 and Si IV 1403 raster, of 2021-09-05."""
    [raster] = raster_data([_real(irispy_test_files, RASTER)], ["Si IV 1403"])
    return image_data(_real(irispy_test_files, SJI)), raster


def write_sst_cube(
    path,
    shape=(3, 1, 5, 12, 16),
    centre=(-55.0, -400.0),
    drift=(0.0, 0.0),
    scale=1.0,
    roll=0.0,
    start=1200.0,
    cadence=60.0,
    prefilters=None,
    knots=2,
    core=None,
):
    """
    Write an SST cube as SSTRED exports one, of ``shape`` (scans, Stokes, tunings, y, x): its pixel (x, y) at scan t is
    at ``centre + t * drift + R(roll) @ scale * (x - centre pixel, y - centre pixel)``, in arcsec, and its tuning k at
    scan t at ``start + t * cadence + 0.25 * k`` s since 2021-09-05 UTC, as its DATE-AVG table gives it too, and
    656.28 nm, H-alpha's, at tuning ``core``, the middle one by default, 0.01 nm apart. ``prefilters`` are the tunings of
    each cavity map, all of them in one map without OFFSET.3 and SCALE.3 by default; the map of extension version v is v
    + 0.001 * (scan + x / 100 + y / 10000) nm. The table gives the pointing at ``knots`` points along x, the corners by
    default. Returns the file's coordinate table, (scans, tunings, y corner, x point, lon, lat, wavelength, time).
    """
    scans, stokes, tunings, rows, columns = shape
    core = tunings // 2 if core is None else core
    t, k, j, i = np.indices((scans, tunings, 2, knots), dtype=float)
    dx, dy = (i / (knots - 1) - 0.5) * (columns - 1) * scale, (j * (rows - 1) - (rows - 1) / 2) * scale
    cos, sin = np.cos(np.deg2rad(roll)), np.sin(np.deg2rad(roll))
    lon, lat = centre[0] + t * drift[0] + cos * dx - sin * dy, centre[1] + t * drift[1] + sin * dx + cos * dy
    coord = np.stack([lon, lat, 656.28 + 0.01 * (k - core), start + t * cadence + 0.25 * k], -1)
    header = fits.Header({"DATEREF": DATEREF, "DATE-OBS": DATEREF, "INSTRUME": "CRISP", "TIMESYS": "UTC"})
    header.update({"OBSGEO-X": 5327403, "OBSGEO-Y": -1718726, "OBSGEO-Z": 3051730})  # the SST's
    header.update(BUNIT="W m^-2 Hz^-1 sr^-1", BTYPE="Intensity")
    axes = {
        1: ("HPLN-TAB", "arcsec", "HPLN-INDEX"),
        2: ("HPLT-TAB", "arcsec", "HPLT-INDEX"),
        3: ("WAVE-TAB", "nm", None),
        5: ("UTC--TAB", "s", None),
    }
    for m, (axis, (ctype, unit, index)) in enumerate(axes.items(), 1):
        header.update(
            {
                f"CTYPE{axis}": ctype,
                f"CUNIT{axis}": unit,
                f"PS{axis}_0": "WCS-TAB",
                f"PS{axis}_1": "HPLN+HPLT+WAVE+TIME",
                f"PV{axis}_3": m,
                f"CRPIX{axis}": 0,
                f"CRVAL{axis}": 0,
                f"CDELT{axis}": 1,
            }
        )
        if index:
            header[f"PS{axis}_2"] = index
    header.update(CTYPE4="STOKES", CRPIX4=1, CRVAL4=1, CDELT4=1, CWERR3=0.005, CWDIS3="Lookup")
    maps = prefilters or [range(tunings)]
    for version, indices in enumerate(maps, 1):
        header.append(fits.Card("DW3.EXTVER", version))
        if prefilters:  # as SSTRED's red_fitscube_addcmap maps them
            first, last, eps = indices[0] - 0.5, indices[-1] + 0.5, 1e-3
            header.append(fits.Card("DW3.OFFSET.3", (last * (0.5 + eps) - (1.5 - eps) * first) / (1 - 2 * eps)))
            header.append(fits.Card("DW3.SCALE.3", (1 - 2 * eps) / (last - first)))
        header.append(fits.Card("DW3.APPLY", 6))
    values = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
    table = fits.BinTableHDU.from_columns(
        [
            fits.Column(
                "HPLN+HPLT+WAVE+TIME", f"{coord.size}D", dim=str(coord.shape[::-1]).replace(" ", ""), array=coord[None]
            ),
            fits.Column("HPLN-INDEX", f"{knots}E", array=[np.linspace(1, columns, knots)]),
            fits.Column("HPLT-INDEX", "2E", array=[[1, rows]]),
        ],
        name="WCS-TAB",
    )
    lookups = []
    for version in range(1, len(maps) + 1):
        scan, _, _, y, x = np.indices((scans, 1, 1, rows, columns))
        lookup = fits.ImageHDU(np.float32(version + 0.001 * (scan + x / 100 + y / 10000)), name="WCSDVARR", ver=version)
        lookup.header["DISTNAME"] = "Cavity error"
        lookups.append(lookup)
    # SOLARNET's variable keywords: the time of each scan and tuning, and the seeing at times of its own
    times = np.datetime64(DATEREF) + np.round(coord[:, :, 0, 0, 3] * 1e3).astype("timedelta64[ms]")
    dates = np.datetime_as_string(times, unit="ms").reshape(scans, 1, tunings, 1, 1)
    dates = fits.Column("DATE-AVG", f"{dates.size * 25}A", dim=f"(25,1,1,{tunings},1,{scans})", array=dates[None])
    seeing = fits.Column("ATMOS_R0", "6E", dim="(2,3)", array=[[[0.1, 0.2]] * 3]), fits.Column("TIME-ATMOS_R0", "3D")
    tables = [fits.BinTableHDU.from_columns(c, name=f"VAR-EXT-{c[0].name}") for c in ([dates], seeing)]
    fits.HDUList([fits.PrimaryHDU(values, header), table, *lookups, *tables]).writeto(path)
    return coord


def _mapped(values):
    """Whether the array ``values`` views a memory-mapped file."""
    while not isinstance(values, mmap.mmap) and getattr(values, "base", None) is not None:
        values = values.base
    return isinstance(values, mmap.mmap)


def test_file_open_gives_the_cube_alone_memory_mapped(tmp_path):
    # SST12: not glue's 33 datasets, the WCSDVARR image and empty ones for the WCS-TAB and VAR-EXT tables; a cube of
    # intensities without its Stokes axis of length 1 (227-1), the VAR-EXT tables as metadata (227-3)
    path = tmp_path / "nb_6563_scans=0-2_im.fits"
    write_sst_cube(path)
    data = load_data(str(path))  # File → Open Data Set's choice of reader
    assert data.label == "nb_6563_scans=0-2_im"
    assert [cid.label for cid in data.main_components] == ["Intensity", "Time", "Cavity error"]
    values = data.get_component("Intensity").data
    assert _mapped(values)
    np.testing.assert_array_equal(values, fits.getdata(path)[:, 0])
    assert isinstance(data.coords, _TabularWCS)
    assert data.shape == (3, 5, 12, 16)
    assert "phys.polarization.stokes" not in data.coords.world_axis_physical_types
    tables = data.meta["VAR-EXT"]
    assert {name: column.shape for name, column in tables.items()} == {
        "DATE-AVG": (3, 5, 1, 1),  # on the cube's axes, 1 long along those it does not change on
        "ATMOS_R0": (3, 2),  # at times of its own
        "TIME-ATMOS_R0": (3,),
    }
    write_sst_cube(tmp_path / "stokes.fits", (3, 4, 5, 12, 16))
    stokes = sst_data(tmp_path / "stokes.fits")
    assert stokes.shape == (3, 4, 5, 12, 16)
    assert stokes.meta["VAR-EXT"]["DATE-AVG"].shape == (3, 1, 5, 1, 1)
    assert data.meta["SPECSYS"] == "TOPOCENT"  # SST2: astropy needs one beside OBSGEO
    assert _role(data) == "sst"
    assert _timed(data)  # in the time sync of the SST cubes whose scan times overlap its own (230-9)


def test_time_and_wavelengths_are_the_table_s_at_every_pixel(tmp_path):
    # glue's own reader gave every tuning of a scan the time of its first: astropy says time depends on the scan only
    path = tmp_path / "cube.fits"
    coord = write_sst_cube(path, drift=(5.0, -3.0), roll=10.0)
    data = sst_data(path)
    times = np.datetime64(DATEREF, "ns") + np.round(coord[:, :, 0, 0, 3] * 1e9).astype("timedelta64[ns]")
    np.testing.assert_array_equal(data["Time"], np.broadcast_to(times[:, :, None, None], data.shape))
    # each scan's and tuning's, as the file's DATE-AVG table gives it (227-3)
    dates = data.meta["VAR-EXT"]["DATE-AVG"].astype("datetime64[ns]")
    np.testing.assert_array_equal(data["Time"], np.broadcast_to(dates, data.shape))
    seconds, wavelength, lat, lon = data.world_component_ids
    np.testing.assert_allclose(data[seconds], np.broadcast_to(coord[:, :, :1, :1, 3], data.shape), rtol=1e-12)
    np.testing.assert_allclose(data[wavelength], np.broadcast_to(coord[:, :, :1, :1, 2], data.shape), rtol=1e-12)
    # the pointing of each scan, at the field's corners
    corners = data[lon][:, 0][:, [0, -1]][:, :, [0, -1]], data[lat][:, 0][:, [0, -1]][:, :, [0, -1]]
    np.testing.assert_allclose(corners, np.moveaxis(coord[:, 0, :, :, :2], -1, 0), atol=1e-9)


def test_the_cavity_error_is_each_tuning_s_map(tmp_path):
    # CHROMIS's Ca II H & K cube has a map for each prefilter, by tuning, and none for its continuum tuning, where the
    # nominal wavelength is the one to take (227-10)
    path = tmp_path / "cube.fits"
    write_sst_cube(path, shape=(2, 1, 7, 4, 5), prefilters=[range(3), range(3, 6)])
    data = sst_data(path)
    cavity = data.get_component("Cavity error")
    assert cavity.units == "nm"
    with fits.open(path) as hdulist:
        maps = [hdulist["WCSDVARR", version].data[:, :, 0] for version in (1, 2)]
    expected = np.concatenate([maps[0]] * 3 + [maps[1]] * 3 + [np.zeros_like(maps[0])], axis=1)
    np.testing.assert_array_equal(data["Cavity error"], np.broadcast_to(expected, data.shape))
    np.testing.assert_array_equal(data["Cavity error", (1, slice(None), 2, 3)], expected[1, :, 2, 3])
    # 5-D with four Stokes parameters
    write_sst_cube(tmp_path / "stokes.fits", shape=(2, 4, 7, 4, 5), prefilters=[range(3), range(3, 6)])
    stokes = sst_data(tmp_path / "stokes.fits")
    np.testing.assert_array_equal(stokes["Cavity error"], np.broadcast_to(expected[:, None], stokes.shape))


@pytest.mark.parametrize("stokes", [1, 4])
def test_the_inverse_is_wcslib_s_inside_the_table_and_takes_the_line_core_outside(tmp_path, stokes):
    path = tmp_path / "cube.fits"
    coord = write_sst_cube(path, (3, stokes, 5, 12, 16), drift=(5.0, -3.0), roll=10.0, core=1)
    coords = sst_data(path).coords
    assert coords.core == 1  # H-alpha's tuning, not the middle one
    i, stokes_i = ([0], [1]) if stokes == 4 else ([], [])  # the pixel and the value of Stokes I, if any
    rng = np.random.default_rng(0)
    pixels = [
        rng.uniform(-2, 17, 40),
        rng.uniform(-2, 13, 40),
        rng.integers(0, 5, 40),
        *[rng.integers(0, 4, 40) for _ in i],
        rng.integers(0, 3, 40),
    ]
    world = coords.pixel_to_world_values(*pixels)
    inside = WCS.world_to_pixel_values(coords, *world)  # NaN off the field, where this inverse goes on
    for got, wcslib, pixel in zip(coords.world_to_pixel_values(*world), inside, pixels):
        np.testing.assert_allclose(got, pixel, atol=1e-9)
        np.testing.assert_allclose(got[~np.isnan(wcslib)], wcslib[~np.isnan(wcslib)], atol=1e-6)  # wcslib's tolerance
    assert (~np.isnan(inside[0])).sum() >= 20
    # glue's CRVAL, 0, for a wavelength and time: the line core of the nearest scan, the first, where wcslib gives NaN
    lon, lat, *_ = coords.pixel_to_world_values(3.5, 7.25, 2, *i, 0)
    assert np.isnan(WCS.world_to_pixel_values(coords, lon, lat, 0, *stokes_i, 0)[0])
    x, y, wavelength, *pixel_i, scan = coords.world_to_pixel_values(lon, lat, 0, *stokes_i, 0)
    np.testing.assert_allclose([x, y, *pixel_i, scan], [3.5, 7.25, *i, 0], atol=1e-9)
    assert np.isnan(wavelength)
    # a time: the scan nearest it at the line core, ties to the earlier, where the middle tuning is 0.25 s later
    core = coord[1, 1, 0, 0, 3]
    for seconds, nearest_scan in ((core + 29, 1), (core + 30, 1), (core + 30.1, 2), (1e9, 2)):
        lon, lat, *_ = coords.pixel_to_world_values(3.5, 7.25, 2, *i, nearest_scan)
        got = coords.world_to_pixel_values(lon, lat, 0, *stokes_i, seconds)
        np.testing.assert_allclose(got[:2], [3.5, 7.25], atol=1e-9)


def test_the_line_core_is_the_tuning_nearest_the_line_nearest_wavelnth():
    # 227-4: tunings of the SST archive's cubes, whose WAVELNTH is the prefilter's; the middle tuning of obs 495's Ca II
    # H & K cube is in Ca II H, but the line nearest its WAVELNTH is Ca II K
    chromis = [393.2674, 393.3675, 393.5326, 396.7562, 396.8415, 396.9, 399.9]
    assert _line_core(chromis, 395.0) == 1  # 393.3675 nm, Ca II K
    fe = [630.1883, 630.2183, 630.2363, 630.2483, 630.2543, 630.2783, 630.3083]
    assert _line_core(fe, 630.26) == 3  # 630.2483 nm, Fe I 630.25, the one of the two within the tunings
    # 232-1: the line's NIST air wavelength, not redshifted by the Sun's gravity to 393.3671 nm
    assert _line_core([393.3660, 393.3672], 395.0) == 0  # Ca II K at 393.3663 nm
    # obs 492 Ca II 8542's 21 tunings, 9 and 10 each 3.0 pm from Ca II 854.2091 nm: the middle one, 10, not WAVELNTH's
    crisp = np.r_[853.9720965796, 854.1580965796 + 0.006 * np.arange(19), 854.4520965796]
    assert _line_core(crisp, 854.1) == 10
    # of two as near to 0.05 pm, 2.98 and 3.02 pm off, the one nearer the middle tuning; 0.1 pm apart, the nearer
    assert _line_core([853.9721, 854.20612, 854.21212, 854.2661, 854.4521], 854.1) == 2
    assert _line_core([853.9721, 854.20614, 854.21216, 854.2661, 854.4521], 854.1) == 1
    assert _line_core([500.0, 500.1, 500.2, 500.3], 500.12) == 1  # no line of the table: WAVELNTH's tuning
    assert _line_core(chromis) == 4  # without WAVELNTH, the line nearest the middle tuning: Ca II H


def _views(monkeypatch):
    """A list that records the view of each statistic glue computes."""
    views, compute = [], Data.compute_statistic

    def read(self, *args, view=None, **kwargs):
        views.append(view)
        return compute(self, *args, view=view, **kwargs)

    monkeypatch.setattr(Data, "compute_statistic", read)
    return views


def test_colour_limits_sample_evenly_spaced_planes_rows_and_columns(monkeypatch, tmp_path):
    # SST10: glue's 10,000 random values each lie on another page of the file
    write_sst_cube(tmp_path / "cube.fits", (2, 1, 23, 49, 97))
    cube, values = sst_data(tmp_path / "cube.fits"), fits.getdata(tmp_path / "cube.fits")

    def random(*args):
        raise AssertionError("glue's random sample")

    monkeypatch.setattr("glue.core.data.random_indices_for_array", random)
    cid, views = cube.main_components[0], _views(monkeypatch)
    # 16 of the 46 planes, a tuning each, of either scan, and 25 of the rows and of the columns
    scans = [0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]
    tunings = [0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 16, 18, 19, 21, 22]
    sample = values[scans, 0, tunings][:, ::2, ::4]
    for percentile in (0.25, 50, 99.75):
        limit = cube.compute_statistic("percentile", cid, percentile=percentile, random_subset=10000)
        assert limit == np.nanpercentile(sample, percentile)
    assert [index.ravel().tolist() for index in views[-1][:-2]] == [scans, tunings]
    # every plane of a cube of 16 or fewer, and 25 or 26 of the rows and of the columns
    for shape in ((2, 1, 8, 49, 97), (3, 1, 5, 51, 101)):
        path = tmp_path / f"{shape[2]}.fits"
        write_sst_cube(path, shape)
        small, sample = sst_data(path), fits.getdata(path)[..., ::2, ::4]
        for percentile in (0.25, 50, 99.75):
            limit = small.compute_statistic(
                "percentile", small.main_components[0], percentile=percentile, random_subset=10000
            )
            assert limit == np.nanpercentile(sample, percentile)
    # glue's own sample for an axis or a subset
    first = PixelSubsetState(cube, [slice(0, 1)] + [slice(None)] * 3)
    for where in ({"axis": (1, 2, 3)}, {"subset_state": first}):
        with pytest.raises(AssertionError, match="glue's random sample"):
            cube.compute_statistic("maximum", cid, random_subset=10000, **where)


@pytest.mark.parametrize("stokes", [1, 4])
def test_colour_limits_of_a_line_are_glue_s_when_15_divides_the_scans(monkeypatch, tmp_path, stokes):
    # D73: planes evenly spaced over the scan, Stokes and tuning together were each the first or last tuning, and the
    # line-core map opened black
    path, shape = tmp_path / "cube.fits", (30, stokes, 13, 40, 40)
    write_sst_cube(path, shape)
    k = np.arange(13)[:, None, None]
    with fits.open(path, mode="update") as hdul:
        noise = 1 + 0.02 * np.random.RandomState(0).standard_normal(shape)  # numpy's frozen stream
        hdul[0].data[...] = (1 - 0.8 * np.exp(-(((k - 6) / 2) ** 2))) * noise  # an absorption line, its core at 6
    cube = sst_data(path)
    cid, views = cube.main_components[0], _views(monkeypatch)
    monkeypatch.setattr(np.random, "randint", np.random.RandomState(0).randint)  # glue's sample, the same each run
    for percentile in (0.25, 99.75):
        glue = Data.compute_statistic(cube, "percentile", cid, percentile=percentile, random_subset=10000)
        limit = cube.compute_statistic("percentile", cid, percentile=percentile, random_subset=10000)
        assert limit == pytest.approx(glue, rel=0.02)
    # 16 planes, no two alike, of 16 scans, every Stokes parameter and every tuning, and 25 of their rows and columns
    plane = views[-1][:-2]
    assert np.broadcast(*views[-1]).shape == (16, 25, 25)
    assert len(set(zip(*(index.ravel() for index in plane)))) == 16
    assert [len(np.unique(index)) for index in plane] == ([16, 4, 13] if stokes == 4 else [16, 13])
    if stokes == 4:
        assert plane[1].ravel().tolist() == [0, 1, 2, 3] * 4  # the Stokes parameters in turn
        # the quicklook's limits of U from the same scans and tunings, all of U (230-6)
        u = cube._sample(10000, 2)
        assert u[1].ravel().tolist() == [2] * 16
        for axis in (0, 2, 3, 4):
            np.testing.assert_array_equal(u[axis], views[-1][axis])


def test_an_image_viewer_shows_a_cube_without_specsys(qtbot, tmp_path):
    # SST2: astropy refuses an empty SPECSYS beside the observatory's place, and no viewer took the cube
    path = tmp_path / "cube.fits"
    write_sst_cube(path, drift=(5.0, -3.0))
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    data = app.load_data(str(path))  # File → Open Data Set
    viewer = app.new_data_viewer(ImageViewer, data=data)
    readout = viewer.toolbar.tools["solar:frame_time"].label
    for slices in ((0, 0, 0, 0), (2, 4, 0, 0)):  # the scan and tuning sliders, and that tuning's time
        viewer.state.slices = slices
        qtbot.wait(20)  # the time sync, which the readout gives too
        assert readout.text() == f"{np.datetime_as_string(data['Time', slices], unit='ms')} UTC · time master"
    assert viewer.layers[0].enabled


def test_a_table_of_more_points_than_the_field_s_corners_takes_wcslib_s_inverse(tmp_path):
    # the loader's own inverse solves SSTRED's tables of the field's corners only
    path = tmp_path / "cube.fits"
    write_sst_cube(path, drift=(5.0, -3.0), roll=10.0, knots=3)
    coords = sst_data(path).coords
    world = coords.pixel_to_world_values(3.5, 7.25, 2, 1)
    np.testing.assert_allclose(coords.world_to_pixel_values(*world), [3.5, 7.25, 2, 1], atol=1e-6)
    assert np.isnan(coords.world_to_pixel_values(*world[:2], 0, 0)[0])  # wcslib's NaN outside the table


def test_glue_s_autolinker_leaves_the_table_s_celestial_axes_whole(tmp_path):
    # glue's autolinker took the celestial axes of a cube and a map, which wcslib cut out of the cube's table and
    # crashed (SIGSEGV); with the cube first, glue 1.27's slicing of the two still fails, with a ValueError
    write_sst_cube(tmp_path / "cube.fits")
    cube = sst_data(tmp_path / "cube.fits")
    assert not cube.coords.has_celestial
    header = {"CTYPE1": "HPLN-TAN", "CTYPE2": "HPLT-TAN", "CUNIT1": "arcsec", "CUNIT2": "arcsec", "CRVAL1": -55}
    find_possible_links(DataCollection([Data(x=np.zeros((4, 5)), coords=WCS(header)), cube]))


def test_a_session_and_the_last_session_restore_a_cube_and_its_viewer(qtbot, monkeypatch, tmp_path):
    # SST5: glue rebuilt the coordinates from their header alone, without their table ('HDUList is required')
    monkeypatch.setattr(glue.config, "CFG_DIR", str(tmp_path / ".glue"))  # glue's settings folder, not the user's
    path = tmp_path / "cube.fits"
    write_sst_cube(path, drift=(5.0, -3.0), roll=10.0, prefilters=[range(2), range(2, 5)], core=1)
    glue_solar.setup()
    app = GlueApplication()  # not given to qtbot, which cannot close it once glue-qt has deleted it as it closed
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))  # not glue's modal dialog
    data = app.load_data(str(path))  # File → Open Data Set
    app.new_data_viewer(ImageViewer, data=data).state.slices = (2, 3, 0, 0)
    app.save_session(str(tmp_path / "cube.glu"))
    app.show()
    app.close()  # as File → Quit does, which keeps the last session
    fresh = GlueApplication()
    next(action for action in fresh._actions["plugins"] if action.text() == "IRIS: restore last session").trigger()
    for restored in (GlueApplication.restore_session(str(tmp_path / "cube.glu")), fresh._new_application):
        qtbot.addWidget(restored)
        [cube] = restored.data_collection
        assert isinstance(cube.coords, _TabularWCS)
        pixels = np.meshgrid(*map(np.arange, cube.shape[::-1]), indexing="ij")
        for got, expected in zip(
            cube.coords.pixel_to_world_values(*pixels), data.coords.pixel_to_world_values(*pixels)
        ):
            np.testing.assert_allclose(got, expected, rtol=1e-12)
        world = data.coords.pixel_to_world_values(*pixels)
        for got, expected in zip(cube.coords.world_to_pixel_values(*world), pixels):
            np.testing.assert_allclose(got, expected, atol=1e-9)
        for component in ("Intensity", "Time", "Cavity error"):
            np.testing.assert_array_equal(cube[component], data[component])
        assert cube.coords.core == 1
        for name, values in data.meta["VAR-EXT"].items():  # read from the file again, not held in the session
            np.testing.assert_array_equal(cube.meta["VAR-EXT"][name], values)
        assert "ATMOS_R0" not in (tmp_path / "cube.glu").read_text()
        assert tuple(restored.viewers[0][0].state.slices) == (2, 3, 0, 0)
    monkeypatch.setattr(restored, "report_error", lambda message, detail: pytest.fail(detail))
    restored.save_session(str(tmp_path / "again.glu"))  # from a restored session
    again = GlueApplication.restore_session(str(tmp_path / "again.glu"))
    qtbot.addWidget(again)
    [cube] = again.data_collection
    np.testing.assert_array_equal(cube.meta["VAR-EXT"]["DATE-AVG"], data.meta["VAR-EXT"]["DATE-AVG"])


def _sst_pixels(coord, lon, lat, when, shape, scale, roll):
    """
    The pixel (x, y) of a cube ``write_sst_cube`` wrote with ``coord``, ``shape``, ``scale`` and ``roll`` at ``lon``,
    ``lat`` in the scan nearest each time ``when``, timed by its line core, the middle tuning, from the cube's own
    geometry.
    """
    *_, tunings, rows, columns = shape
    seconds = (when - np.datetime64(DATEREF)) / np.timedelta64(1, "s")
    scans = coord[:, tunings // 2, 0, 0, 3]
    scan = np.argmin(abs(np.asarray(seconds)[..., None] - scans), axis=-1)
    du, dv = lon - coord[scan, 0, :, :, 0].mean((-1, -2)), lat - coord[scan, 0, :, :, 1].mean((-1, -2))
    cos, sin = np.cos(np.deg2rad(roll)), np.sin(np.deg2rad(roll))
    return (cos * du + sin * dv) / scale + (columns - 1) / 2, (cos * dv - sin * du) / scale + (rows - 1) / 2


@pytest.mark.parametrize("stokes", [1, 4])
def test_once_linked_an_sst_region_or_point_selects_the_iris_pixels_at_its_place(tmp_path, sns, stokes):
    # D67: glue gave the cube's wavelength and time their CRVAL, 0, outside its table, which selected nothing; a mosaic's
    # pointing changes with each scan, so each SJI frame and raster exposure takes the scan nearest it
    sji, raster = sns
    frames = _times(sji, 0)
    start, cadence = (frames[10] - np.datetime64(DATEREF)), (frames[-1] - frames[10]) / 3  # from the 11th frame
    shape, scale, roll = (4, stokes, 5, 30, 40), 1.1, 8.0
    seconds = [time / np.timedelta64(1, "s") for time in (start, cadence)]
    coord = write_sst_cube(tmp_path / "cube.fits", shape, (-55.0, -400.0), (4.0, -3.0), scale, roll, *seconds)
    cube = sst_data(tmp_path / "cube.fits")
    dc = DataCollection([sji, raster, cube])
    keep_hpc_linked(dc)
    roi = RectangularROI(10.3, 29.6, 6.2, 21.7)
    region = RoiSubsetState(xatt=cube.pixel_component_ids[-1], yatt=cube.pixel_component_ids[-2], roi=roi)
    with pytest.raises(IncompatibleAttribute):  # D64: linked on request only
        sji.get_mask(region)
    assert not isinstance(cube.coords, _LockedWCS)  # 227-9: nor behind the WCS lock until then
    keep_hpc_linked(dc, others=dc)  # 'IRIS: link helioprojective coordinates'
    assert isinstance(cube.coords, _LockedWCS)
    for data, mask in ((sji, sji.get_mask(region)), (raster, raster.get_mask(region)[..., 0])):
        index = np.indices(mask.shape)
        if data is sji:
            lon, lat, _ = sji.coords.pixel_to_world_values(*index[::-1])
        else:
            _, lat, lon = raster.coords.pixel_to_world_values(0, index[1], index[0])
        (xc, yc), half_width, half_height = roi.center(), roi.width() / 2, roi.height() / 2

        def inside(when, margin=0):
            x, y = _sst_pixels(coord, lon, lat, when, shape, scale, roll)
            return (abs(x - xc) < half_width + margin) & (abs(y - yc) < half_height + margin)

        when = _times(data, 0)[index[0]]
        expected, edge = inside(when), inside(when, 0.01) != inside(when, -0.01)
        assert expected.sum() >= 50
        assert edge.sum() <= expected.sum() // 20
        np.testing.assert_array_equal(mask[~edge], expected[~edge])
        assert (inside(frames[0]) != expected).sum() >= 10  # not in the first scan's pointing throughout
    # glue's Pixel point, at the cube's first tuning: the raster's exposure and slit row nearest it, and in the slit-jaw
    # frame nearest its scan, the pixel there; at the first scan with the scan free, and at a scan's own pointing with
    # it fixed, as the quicklook fixes it and any Stokes parameter, which reach no IRIS axis (D73)
    exposure, slit = np.indices(raster.shape[:2])
    _, lats, lons = raster.coords.pixel_to_world_values(0, slit, exposure)
    quicklook_point = [slice(2, 3)] + [slice(1, 2)] * (stokes > 1)
    for scan, fixed in ((0, [slice(None)] * (cube.ndim - 3)), (2, quicklook_point)):
        point = PixelSubsetState(cube, [*fixed, slice(None), slice(15, 16), slice(30, 31)])
        lon, lat, *_ = cube.coords.pixel_to_world_values(30, 15, 0, *[0] * (stokes > 1), scan)
        assert point._to_linked_pixel_coords(raster) == [
            *np.unravel_index(np.argmin(np.hypot(lons - lon, lats - lat)), raster.shape[:2]),
            None,
        ]
        when = np.datetime64(DATEREF) + np.timedelta64(int(coord[scan, 2, 0, 0, 3] * 1e9), "ns")
        [frame], _ = nearest([when], frames)
        x, y, _ = sji.coords.world_to_pixel_values(lon, lat, sji.coords.pixel_to_world_values(0, 0, frame)[2])
        assert point._to_linked_pixel_coords(sji) == [frame, round(float(y)), round(float(x))]


@pytest.fixture
def sst_app(qtbot, monkeypatch):
    """An application whose modal dialogs fail the test, with glue's large-data prompt set to fire on any size."""
    monkeypatch.setattr(ProfileViewer, "large_data_size", 1)
    return bare_app_for(qtbot, monkeypatch)


def stokes_cube(path, shape=(3, 4, 5, 12, 16), line="H-alpha", **kwargs):
    """A cube ``write_sst_cube`` writes at ``path``, named as the archive names ``line``, and its file's values."""
    write_sst_cube(path, shape, drift=(5.0, -3.0), **kwargs)
    fits.setval(path, "WAVEBAND", value=line)
    return sst_data(path), fits.getdata(path)


def check_sst_panels(viewers, values, group):
    """
    Each panel of an SST quicklook is the file's ``values`` at the point, its scan and Stokes, and the wavelengths
    shown; a cube of intensities has no Stokes axis.
    """
    point = group.subset_state.slices
    s, k, y, x = point[0].start, point[1].start if len(point) == 5 else 0, point[-2].start, point[-1].start
    w, wing = viewers["map"].state.slices[-3], viewers["wing"].state.slices[-3]
    images = {"map": values[s, k, w], "wing": values[s, k, wing], "slit": values[s, k, :, :, x].T}
    images["wavelength"] = values[:, k, :, y, x]
    for role, expected in images.items():
        np.testing.assert_array_equal(viewers[role].state.layers[0].get_sliced_data(), expected)
    for stokes, spectrum in enumerate(viewers["spectra"]):
        np.testing.assert_array_equal(spectrum.state.layers[0].profile[1], values[s, stokes, :, y, x])
    np.testing.assert_array_equal(viewers["curve"].state.layers[0].profile[1], values[:, k, w, y, x])


def test_the_sst_quicklook_shows_a_cube_in_its_panels(sst_app, qtbot, tmp_path):
    # D68: the maps and the virtual slit on top, the spectra of I, Q, U and V below them, then wavelength against time
    # and the light curve at the point, every panel computing only the point
    cube, values = stokes_cube(tmp_path / "cube.fits")
    viewers = quicklook(sst_app, [cube])
    assert sst_app.tab_names[-1] == "SST H-alpha"
    titles = [[viewer.state.title for viewer in row] for row in viewers["rows"]]
    assert titles == [
        ["H-alpha map", "H-alpha second map", "H-alpha virtual slit"],
        ["H-alpha Stokes I", "H-alpha Stokes Q", "H-alpha Stokes U", "H-alpha Stokes V"],
        ["H-alpha λ–time", "H-alpha light curve"],
    ]
    assert set(sst_app.viewers[-1]) == {viewer for row in viewers["rows"] for viewer in row}
    pixel = cube.pixel_component_ids
    # the map at the line core, H-alpha's tuning, the second map at the first, the point at the map's centre in scan 0
    # and Stokes I
    for role, x, y, tuning in (("map", 4, 3, 2), ("wing", 4, 3, 0), ("slit", 2, 3, 2), ("wavelength", 2, 0, 2)):
        state = viewers[role].state
        assert isinstance(viewers[role], QuicklookImageViewer)
        assert (state.x_att, state.y_att, state.slices) == (pixel[x], pixel[y], (0, 0, tuning, 6, 8))
        assert state.layers[0].percentile == 99.5
    [group] = sst_app.session.edit_subset_mode.edit_subset
    assert group.label == "Point"
    assert group.subset_state.slices == [slice(0, 1), slice(0, 1), slice(None), slice(6, 7), slice(8, 9)]
    assert viewers["map"].toolbar.active_tool.tool_id == "image:point_selection"
    for viewer in [*viewers["spectra"], viewers["curve"]]:  # no profile of the whole cube, which glue asks about
        [layer] = viewer.state.layers
        assert layer.layer.group is not group
        assert layer.layer.data is cube
    np.testing.assert_allclose(viewers["spectra"][0].state.layers[0].profile[0], 656.28 + 0.01 * np.arange(-2, 3))
    assert viewers["curve"].state.x_att is pixel[0]
    check_sst_panels(viewers, values, group)
    # in rows, the Point window and the Panels list below them
    tops = [{viewer.parent().y() for viewer in row} for row in viewers["rows"]]
    assert [len(top) for top in tops] == [1, 1, 1]
    assert tops[0].pop() < tops[1].pop() < tops[2].pop()
    window = point_window(sst_app)
    assert window.parent().y() > viewers["curve"].parent().y()
    assert entries(panels_list(sst_app)) == [("Axes", False), *((title, True) for row in titles for title in row)]
    # the image panels without axes, until the Axes box shows them (D71); the spectra and light curve keep theirs
    images = [viewers[role] for role in ("map", "wing", "slit", "wavelength")]
    profiles = [*viewers["spectra"], viewers["curve"]]
    assert [viewer.axes.axison for viewer in images + profiles] == [False] * 4 + [True] * 5
    tick(panels_list(sst_app), "Axes")
    assert all(viewer.axes.axison for viewer in images)
    settle(qtbot, window)
    lon, lat, wavelength, _, _ = cube.coords.pixel_to_world_values(8, 6, 2, 0, 0)
    position = f'{lon:.2f}" {lat:.2f}" {wavelength * 10:.3f} Å'
    time = f"{np.datetime_as_string(cube['Time', 0, 0, 2, 6, 8], unit='ms')} UTC"
    value = f"{values[0, 0, 2, 6, 8]:.6g}"
    assert rows(window) == [[cube.label, "scan 0, Stokes 0, λ 2, y 6, x 8", position, time, "", value, "time master"]]
    # a click, the scan, Stokes and wavelength sliders: every panel follows
    select_point(viewers["map"], 3, 7)
    slide(viewers["map"], 0, 2)
    slide(viewers["map"], 1, 3)
    slide(viewers["map"], 2, 4)
    qtbot.wait(20)
    check_sst_panels(viewers, values, group)
    # a cube of intensities, without a Stokes axis (227-1), has one spectrum, the '&' of CHROMIS's line not a shortcut in
    # Qt's titles; its maps open at its line core (227-4), here its second tuning, and at the scan of the time the other
    # cube's quicklook left; one cube to a tab
    single, values = stokes_cube(tmp_path / "single.fits", shape=(3, 1, 5, 12, 16), line="Ca II H & K", core=1)
    viewers = quicklook(sst_app, [single])
    assert sst_app.tab_names[-1] == "SST Ca II H and K"
    assert [viewer.state.title for viewer in viewers["rows"][1]] == ["Ca II H and K spectrum"]
    pixel = single.pixel_component_ids
    for role, x, y, tuning in (("map", 3, 2, 1), ("wing", 3, 2, 0), ("slit", 1, 2, 1), ("wavelength", 1, 0, 1)):
        state = viewers[role].state
        assert (state.x_att, state.y_att, state.slices) == (pixel[x], pixel[y], (2, tuning, 6, 8))
    [group] = sst_app.session.edit_subset_mode.edit_subset
    assert group.subset_state.slices == [slice(2, 3), slice(None), slice(6, 7), slice(8, 9)]
    check_sst_panels(viewers, values, group)
    window = point_window(sst_app)
    settle(qtbot, window)
    assert rows(window)[0][1] == "scan 2, λ 1, y 6, x 8"
    # a click takes the scan of the map's slider; the scan and wavelength sliders: every panel follows
    slide(viewers["map"], 0, 1)
    select_point(viewers["map"], 3, 7)
    slide(viewers["map"], 1, 4)
    qtbot.wait(20)
    assert group.subset_state.slices == [slice(1, 2), slice(None), slice(7, 8), slice(3, 4)]
    check_sst_panels(viewers, values, group)
    with pytest.raises(ValueError, match="one cube"):
        quicklook(sst_app, [cube, single])


def test_q_u_and_v_show_with_limits_symmetric_about_0(sst_app, qtbot, tmp_path):
    # 230-6: glue's 99.5% over the whole cube, I's values mostly, showed Q, U and V flat
    path = tmp_path / "cube.fits"
    write_sst_cube(path, (3, 4, 5, 12, 16))
    rng = np.random.default_rng(0)
    with fits.open(path, mode="update") as hdul:
        hdul[0].data[:, 0] = rng.normal(1000, 10, (3, 5, 12, 16))
        hdul[0].data[:, 1:] = rng.normal(0, 1, (3, 3, 5, 12, 16)) * np.array([1, 1.5, 2])[:, None, None, None]
        values = hdul[0].data.copy()
    viewers = quicklook(sst_app, [sst_data(path)])
    layers = [viewers[role].state.layers[0] for role in ("map", "wing", "slit", "wavelength")]
    whole = [(layer.v_min, layer.v_max) for layer in layers]
    assert [layer.percentile for layer in layers] == [99.5] * 4
    for stokes in (1, 2, 3, 0):
        slide(viewers["map"], 1, stokes)
        qtbot.waitUntil(lambda: all(layer.viewer_state.slices[1] == stokes for layer in layers))
        if stokes == 0:  # glue's again
            assert [(layer.v_min, layer.v_max, layer.percentile) for layer in layers] == [(*w, 99.5) for w in whole]
            continue
        # every value of the parameter, as a cube of 16 planes of it or fewer gives
        limit = np.percentile(abs(values[:, stokes]), 99.5)
        for layer in layers:
            assert (layer.v_min, layer.v_max) == (pytest.approx(-limit), pytest.approx(limit))
        assert limit < 0.01 * (whole[0][1] - whole[0][0])  # the 1% of glue's range they took
    # with 'Per-frame limits' on, glue's 99.5% of the frame shown
    layers[0].stretch_global = False
    slide(viewers["map"], 1, 3)
    qtbot.waitUntil(lambda: layers[0].viewer_state.slices[1] == 3)
    frame = np.percentile(values[0, 3, 2], [0.25, 99.75])
    assert (layers[0].v_min, layers[0].v_max, layers[0].percentile) == (*map(pytest.approx, frame), 99.5)


def test_a_profile_viewer_adds_a_large_cube_hidden(sst_app, monkeypatch, tmp_path, sns):
    # SST4: glue profiles a cube added to a Profile viewer on the main thread first, reading the whole file (30 s on obs
    # 492 Ca II 8542); one of glue's large-data size or more, here any, that the IRIS reader did not read comes hidden
    cube, values = stokes_cube(tmp_path / "cube.fits")
    _, raster = sns
    sst_app.data_collection.extend([cube, raster])
    whole = []
    compute = Data.compute_statistic

    def counted(self, *args, **kwargs):
        if kwargs.get("axis") is not None and kwargs.get("subset_state") is None:
            whole.append(self.label)
        return compute(self, *args, **kwargs)

    monkeypatch.setattr(Data, "compute_statistic", counted)
    # glue-qt's Profile button, its note and 'Add large data set?' answered OK
    monkeypatch.setattr("glue_qt.viewers.image.profile_viewer_tool.info", lambda *args, **kwargs: True)
    monkeypatch.setattr(ProfileViewer, "warn", lambda *args, **kwargs: True)
    # a subset group on the raster, not linked to the cube, which glue adds to the viewer with no profile
    pixel = raster.pixel_component_ids
    sst_app.data_collection.new_subset_group("Point", RoiSubsetState(pixel[-1], pixel[-2], RectangularROI(0, 2, 0, 2)))
    sst_app.session.edit_subset_mode.edit_subset = []
    image = sst_app.new_data_viewer(ImageViewer, data=cube)
    image.toolbar.tools["profile-viewer"].activate()
    profile = sst_app.viewers[0][-1]
    [layer, _] = profile.state.layers
    assert not layer.visible
    assert cube.label in profile.statusBar().currentMessage()
    # a rectangle's profile, the maximum along wavelength, and the range fitted to it
    image.apply_roi(RectangularROI(1.5, 5.5, 2.5, 7.5))
    [_, _, rectangle] = profile.state.layers
    expected = values[..., 3:8, 2:6].max(axis=(0, 1, 3, 4))
    np.testing.assert_array_equal(rectangle.profile[1], expected)
    assert (profile.state.y_min, profile.state.y_max) == (expected.min(), expected.max())
    assert whole == []
    # ticked in the layer list, the cube's own
    layer.visible = True
    np.testing.assert_array_equal(layer.profile[1], values.max(axis=(0, 1, 3, 4)))
    # an IRIS raster shows as glue adds it
    iris = sst_app.new_data_viewer(ProfileViewer, data=raster).state.layers[0]
    assert iris.layer is raster
    assert iris.visible
    # and a cube below glue's large-data size
    monkeypatch.setattr(ProfileViewer, "large_data_size", cube.size + 1)
    assert sst_app.new_data_viewer(ProfileViewer, data=cube).state.layers[0].visible


def test_what_moves_on_an_sst_cube(sst_app, qtbot, tmp_path):
    cube, values = stokes_cube(tmp_path / "cube.fits")
    viewers = quicklook(sst_app, [cube])
    [group] = sst_app.session.edit_subset_mode.edit_subset
    label = cube.label

    def event(action):
        return changes(sst_app, qtbot, viewers, action)

    # a map click moves the point: the virtual slit to its x, wavelength against time to its y and x
    assert event(lambda: select_point(viewers["map"], 3, 7)) == {
        "point": (label, (0, 0, None, 7, 3)),
        "slit": (0, 0, None, None, 3),
        "wavelength": (None, 0, None, 7, 3),
    }
    # a click on the virtual slit (wavelength 4, y 2) keeps x, and moves the map, not the second map, to its wavelength
    assert event(lambda: select_point(viewers["slit"], 4, 2)) == {
        "point": (label, (0, 0, None, 2, 3)),
        "map": (0, 0, 4, None, None),
        "wavelength": (None, 0, None, 2, 3),
    }
    # one on wavelength against time (wavelength 1, scan 2) moves the point, the maps and the slit to its scan
    assert event(lambda: select_point(viewers["wavelength"], 1, 2)) == {
        "point": (label, (2, 0, None, 2, 3)),
        "map": (2, 0, 1, None, None),
        "wing": (2, 0, 0, None, None),
        "slit": (2, 0, None, None, 3),
    }
    # the scan and Stokes sliders of either map move the point and the other panels
    assert event(lambda: slide(viewers["map"], 0, 1)) == {
        "point": (label, (1, 0, None, 2, 3)),
        "map": (1, 0, 1, None, None),
        "wing": (1, 0, 0, None, None),
        "slit": (1, 0, None, None, 3),
    }
    assert event(lambda: slide(viewers["wing"], 1, 3)) == {
        "point": (label, (1, 3, None, 2, 3)),
        "map": (1, 3, 1, None, None),
        "wing": (1, 3, 0, None, None),
        "slit": (1, 3, None, None, 3),
        "wavelength": (None, 3, None, 2, 3),
    }
    check_sst_panels(viewers, values, group)
    # a wavelength slider moves its own map only, and A and S the second map only pressed on it
    assert event(lambda: slide(viewers["map"], 2, 3)) == {"map": (1, 3, 3, None, None)}
    assert event(lambda: slide(viewers["wing"], 2, 4)) == {"wing": (1, 3, 4, None, None)}
    assert event(lambda: press(viewers["slit"], Qt.Key_S)) == {"map": (1, 3, 4, None, None)}
    assert event(lambda: press(viewers["wing"], Qt.Key_A)) == {
        "map": (1, 3, 3, None, None),
        "wing": (1, 3, 3, None, None),
    }
    # the slit's x slider and the y slider of wavelength against time move the point
    assert event(lambda: slide(viewers["slit"], 4, 10)) == {
        "point": (label, (1, 3, None, 2, 10)),
        "slit": (1, 3, None, None, 10),
        "wavelength": (None, 3, None, 2, 10),
    }
    assert event(lambda: slide(viewers["wavelength"], 3, 9)) == {
        "point": (label, (1, 3, None, 9, 10)),
        "wavelength": (None, 3, None, 9, 10),
    }
    check_sst_panels(viewers, values, group)
    # after Clear point the panels stay, but for the time
    assert event(lambda: menu_action(viewers["map"], "Clear point").trigger()) == {"point": None}
    assert event(lambda: slide(viewers["map"], 0, 2)) == {"map": (2, 3, 3, None, None)}
    assert "time master" in viewers["map"].toolbar.tools["solar:frame_time"].label.text()


def test_the_first_click_on_any_sst_panel_moves_the_point(sst_app, qtbot, tmp_path):
    # each panel takes the Pixel tool as its window becomes active, as in the IRIS quicklook (D75)
    cube, _ = stokes_cube(tmp_path / "cube.fits")
    sst_app.show()
    qtbot.waitUntil(sst_app.isActiveWindow)  # for a click to make its window the active one
    viewers = quicklook(sst_app, [cube])
    label = cube.label

    def moved(action):
        return changes(sst_app, qtbot, viewers, action)["point"]

    assert moved(lambda: mouse_click(viewers["wing"], 3, 7)) == (label, (0, 0, None, 7, 3))
    assert moved(lambda: mouse_click(viewers["slit"], 4, 2)) == (label, (0, 0, None, 2, 3))
    assert moved(lambda: mouse_click(viewers["wavelength"], 1, 2)) == (label, (2, 0, None, 2, 3))
    assert moved(lambda: mouse_click(viewers["map"], 5, 9)) == (label, (2, 0, None, 9, 5))
    assert moved(lambda: press(viewers["slit"], Qt.Key_F)) == (label, (0, 0, None, 9, 5))
    assert [group.label for group in sst_app.session.edit_subset_mode.edit_subset] == ["Point"]


def shown_scan(viewers):
    return viewers["map"].state.slices[0]


def show_tab(app, qtbot, index):
    app.tab_widget.setCurrentIndex(index)
    qtbot.wait(20)


def test_two_sst_quicklooks_keep_one_time(sst_app, qtbot, tmp_path):
    # D68: one cube to a tab, the SST cubes whose scan times overlap in one time sync (230-9): the cube shown leads the
    # time, and one shown next starts at its scan nearest that time, unless within half the longer cadence of it; a cube
    # from later in the day keeps its own
    write_sst_cube(tmp_path / "a.fits", (4, 1, 5, 12, 16), start=1200.0, cadence=60.0)  # 1200 to 1381 s
    write_sst_cube(tmp_path / "b.fits", (5, 1, 3, 10, 14), start=1170.0, cadence=50.0)  # 1170 to 1370.5 s
    write_sst_cube(tmp_path / "c.fits", (3, 1, 5, 12, 16), start=5000.0, cadence=60.0)  # 5000 to 5121 s
    first, second, later = (sst_data(tmp_path / f"{name}.fits") for name in "abc")
    a = quicklook(sst_app, [first])
    slide(a["map"], 0, 2)
    qtbot.wait(20)
    b = quicklook(sst_app, [second])  # 1320.25 s is nearest 1320.5 s
    qtbot.wait(20)
    assert (shown_scan(a), shown_scan(b)) == (2, 3)
    assert sst_app.session.edit_subset_mode.edit_subset[0].subset_state.slices[0] == slice(3, 4)
    slide(b["map"], 0, 1)  # 1220.25 s
    show_tab(sst_app, qtbot, 1)
    assert (shown_scan(a), shown_scan(b)) == (0, 1)  # 1200.5 s
    slide(a["map"], 0, 1)  # 1260.5 s
    show_tab(sst_app, qtbot, 2)
    assert (shown_scan(a), shown_scan(b)) == (1, 2)  # 1270.25 s
    show_tab(sst_app, qtbot, 1)  # within 30 s already: no step back and forth
    assert (shown_scan(a), shown_scan(b)) == (1, 2)
    c = quicklook(sst_app, [later])
    day = np.datetime64(DATEREF, "ns")
    assert observation_key(first) == observation_key(second) == ("SST", day + np.timedelta64(1170, "s"))
    assert observation_key(later) == ("SST", day + np.timedelta64(5000, "s"))
    # shown, the later cube leads its own time only, and the first two keep theirs
    coord = coordinator(sst_app.data_collection)
    slide(c["map"], 0, 2)
    assert [coord._master(observation_key(data)) for data in (first, second, later)] == [first, first, later]
    show_tab(sst_app, qtbot, 2)
    assert (shown_scan(a), shown_scan(b), shown_scan(c)) == (1, 2, 2)
    assert [coord._master(observation_key(data)) for data in (first, second, later)] == [second, second, later]


def test_once_linked_an_sst_quicklook_shares_the_iris_time(sst_app, qtbot, tmp_path, sns):
    # D64, D68: an SST cube joins the time sync of the IRIS observation it is linked to, on request only, each scan timed
    # at its line core (227-4), here its second tuning; and only then behind the WCS lock (227-9)
    sji, raster = sns
    frames = _times(sji, 0)
    start, cadence = (frames[10] - np.datetime64(DATEREF)), (frames[-1] - frames[10]) / 3
    seconds = [time / np.timedelta64(1, "s") for time in (start, cadence)]
    write_sst_cube(tmp_path / "cube.fits", (4, 1, 5, 30, 40), (-55.0, -400.0), (4.0, -3.0), 1.1, 8.0, *seconds, core=1)
    cube = sst_data(tmp_path / "cube.fits")
    scans = cube["Time"][:, 1, 0, 0]
    np.testing.assert_array_equal(_times(cube, None), scans)
    iris = quicklook(sst_app, [raster, sji])
    sst = quicklook(sst_app, [cube])
    coord = coordinator(sst_app.data_collection)
    slide(sst["map"], 0, 3)
    show_tab(sst_app, qtbot, 1)  # unlinked, the tabs keep their own times
    exposure = iris["spectrogram"].state.slices[0]  # a sit-and-stare's map is slit against time
    show_tab(sst_app, qtbot, 2)
    assert shown_scan(sst) == 3
    assert observation_key(cube) == ("SST", cube["Time"].min())  # its own, the only cube
    assert not isinstance(cube.coords, _LockedWCS)
    link_iris(sst_app.session, sst_app.data_collection)  # 'IRIS: link helioprojective coordinates'
    assert isinstance(cube.coords, _LockedWCS)
    key = observation_key(raster)
    assert observation_key(cube) == key
    assert cube.meta["IRIS observation"] == [key[0], str(key[1])]
    # shown, the IRIS quicklook takes the time from the cube's scan, and the cube then from its exposure
    times = _times(raster, None)
    show_tab(sst_app, qtbot, 1)
    [nearest_exposure], _ = nearest([scans[3]], times)
    assert iris["spectrogram"].state.slices[0] == nearest_exposure != exposure
    coord.move_master(raster, 5)
    qtbot.wait(20)
    show_tab(sst_app, qtbot, 2)
    [scan], [offset] = nearest([times[5]], scans)
    assert shown_scan(sst) == scan
    assert abs(offset) <= cadence / 2
    assert "time master" in sst["map"].toolbar.tools["solar:frame_time"].label.text()


def test_a_cube_shares_its_sst_cubes_time_again_once_the_iris_data_go(sst_app, qtbot, tmp_path, sns):
    # D73: a cube kept the key of the IRIS data it was linked to once they were removed, out of its cubes' time sync
    sji, raster = sns
    frames = _times(sji, 0)
    start, cadence = (frames[10] - np.datetime64(DATEREF)), (frames[-1] - frames[10]) / 3
    seconds = [time / np.timedelta64(1, "s") for time in (start, cadence)]
    for name in ("linked", "other"):
        write_sst_cube(tmp_path / f"{name}.fits", (4, 1, 5, 30, 40), (-55.0, -400.0), (4.0, -3.0), 1.1, 8.0, *seconds)
    linked, other = sst_data(tmp_path / "linked.fits"), sst_data(tmp_path / "other.fits")
    sst_app.data_collection.extend([sji, raster, linked])
    link_iris(sst_app.session, sst_app.data_collection)  # 'IRIS: link helioprojective coordinates'
    assert observation_key(linked) == observation_key(raster)
    sst_app.data_collection.remove(sji)
    sst_app.data_collection.remove(raster)
    qtbot.waitUntil(lambda: "IRIS observation" not in linked.meta)  # as the links are made again
    quicklook(sst_app, [other])
    assert observation_key(linked) == observation_key(other) == ("SST", other["Time"].min())


@pytest.mark.parametrize("stokes", [4, 1])
def test_a_session_restores_the_sst_quicklook(sst_app, qtbot, tmp_path, stokes):
    cube, values = stokes_cube(tmp_path / "cube.fits", (3, stokes, 5, 12, 16), core=1)
    viewers = quicklook(sst_app, [cube])
    select_point(viewers["map"], 3, 7)
    slide(viewers["map"], 0, 2)
    qtbot.wait(20)
    sst_app.save_session(str(tmp_path / "sst.glu"))
    restored = GlueApplication.restore_session(str(tmp_path / "sst.glu"), show=False)
    qtbot.addWidget(restored)
    qtbot.wait(20)
    panels = {viewer.state.title.split(" ", 1)[1]: viewer for viewer in restored.viewers[1]}
    again = {role: panels[title] for role, title in (("map", "map"), ("wing", "second map"), ("slit", "virtual slit"))}
    again.update(wavelength=panels["λ–time"], curve=panels["light curve"])
    again["spectra"] = [panels[f"Stokes {name}"] for name in "IQUV"] if stokes == 4 else [panels["spectrum"]]
    [group] = restored.session.edit_subset_mode.edit_subset
    [data] = restored.data_collection
    assert isinstance(data, _Cube)  # its colour limits' sample too
    assert data.coords.core == again["map"].state.slices[-3] == 1
    assert group.label == "Point"
    i = [slice(0, 1)] if stokes == 4 else []  # Stokes I, if any
    assert group.subset_state.slices[: 1 + len(i)] == [slice(2, 3), *i]
    check_sst_panels(again, values, group)
    # a click moves every panel, the spectra and the light curve too
    select_point(again["map"], 10, 4)
    qtbot.wait(20)
    assert group.subset_state.slices == [slice(2, 3), *i, slice(None), slice(4, 5), slice(10, 11)]
    check_sst_panels(again, values, group)


def test_an_unlinked_cube_never_takes_the_wcs_lock(sst_app, qtbot, monkeypatch, tmp_path, sns):
    # 227-9: an SST cube is behind the WCS lock only once linked to IRIS data, as maps are (#226), so that its viewers
    # never wait for IRIS data's threads until then; with the axes shown, WCSAxes draws through its coordinates
    taken, lock = [], WCS_LOCK

    class Counted:
        def __enter__(self):
            taken.append(threading.current_thread().name)
            return lock.__enter__()

        def __exit__(self, *args):
            return lock.__exit__(*args)

    for name, module in list(sys.modules.items()):
        if name.startswith("glue_solar") and getattr(module, "WCS_LOCK", None) is WCS_LOCK:  # each imports it by name
            monkeypatch.setattr(module, "WCS_LOCK", Counted())
    cube, _ = stokes_cube(tmp_path / "cube.fits")
    single, values = stokes_cube(tmp_path / "single.fits", (3, 1, 5, 12, 16))
    for data in (cube, single):  # the second's viewers also show the first's point
        viewers = quicklook(sst_app, [data])
        tick(panels_list(sst_app), "Axes")
        select_point(viewers["map"], 3, 7)
        slide(viewers["map"], 0, 2)
        select_point(viewers["slit"], 2, 4)
        settle(qtbot, point_window(sst_app))
    check_sst_panels(viewers, values, sst_app.session.edit_subset_mode.edit_subset[0])
    assert taken == []
    sst_app.data_collection.extend(sns)
    link_iris(sst_app.session, sst_app.data_collection)  # 'IRIS: link helioprojective coordinates'
    taken.clear()  # as the links reach the IRIS data's coordinates
    slide(viewers["map"], 0, 1)
    settle(qtbot, point_window(sst_app))
    assert taken


def test_every_wcslib_call_on_an_unlinked_cube_holds_its_own_lock(sst_app, qtbot, monkeypatch, tmp_path):
    # D73: glue-qt computes the spectra of a cube of over 1e7 values on worker threads, as the GUI thread draws its
    # coordinates and resets them (wcsset) at each scan; wcslib writes the table's scratch values as it reads them, which
    # gave wrong values and crashed glue. So each call into wcslib, or into astropy's code that reads its struct, holds
    # the cube's own lock, and not the WCS lock (227-9)
    monkeypatch.setattr(
        QThreadedProfileLayerArtist, "_calculate_profile", lambda self, reset=False: self._worker.work_queue.put(reset)
    )
    cube, _ = stokes_cube(tmp_path / "cube.fits")
    wcs, struct = cube.coords, cube.coords.wcs
    viewers = quicklook(sst_app, [cube])
    tick(panels_list(sst_app), "Axes")
    files = {astropy.wcs.wcs.__file__, astropy.wcs.wcsapi.fitswcs.__file__}
    calls = []  # (on the GUI thread, the function, holding the cube's lock, holding the WCS lock)

    def profile(frame, event, arg):
        if event == "c_call" and any(getattr(arg, "__self__", None) is owner for owner in (wcs, struct)):
            name = arg.__name__
        # astropy's methods that touch self.wcs, the struct
        elif event == "call" and frame.f_code.co_filename in files and "wcs" in frame.f_code.co_names:
            if frame.f_locals.get("self") is not wcs:
                return
            name = frame.f_code.co_name
        else:
            return
        main = threading.current_thread() is threading.main_thread()
        calls.append((main, name, wcs._lock._is_owned(), WCS_LOCK._is_owned()))

    threading.setprofile_all_threads(profile)  # glue-qt's workers too, which wait for work
    try:
        for scan, (x, y) in enumerate([(3, 7), (10, 4)], 1):
            select_point(viewers["map"], x, y)
            slide(viewers["map"], 0, scan)
            settle(qtbot, point_window(sst_app))
        qtbot.waitUntil(lambda: {main for main, *_ in calls} == {True, False}, timeout=30_000)
        sst_app.save_session(str(tmp_path / "sst.glu"))
    finally:
        threading.setprofile_all_threads(None)
    assert {"_all_pix2world", "set", "world_axis_units", "to_header"} <= {name for _, name, *_ in calls}
    assert [call for call in calls if not call[2] or call[3]] == []
    assert copy.deepcopy(wcs)._lock is not wcs._lock  # a copy's own, as its struct is


def test_a_cube_linked_mid_transform_neither_hangs_nor_races(tmp_path):
    # link_hpc makes a cube's coordinates `_LockedTabularWCS` in place, maybe as a profile worker is in a transform,
    # which calls into them again: one that took the WCS lock there waited for good for the GUI thread's next call, which
    # held that and waited for the cube's lock
    cube, _ = stokes_cube(tmp_path / "cube.fits")
    wcs, pixel = cube.coords, [np.linspace(0, n - 1, 20_000) for n in cube.shape[::-1]]
    expected, results, started, linked = wcs.pixel_to_world_values(*pixel), [], threading.Event(), threading.Event()

    def worker():  # a profile worker
        while not linked.is_set():
            results.append(wcs.pixel_to_world_values(*pixel))
            started.set()

    def link():  # link_hpc, then the GUI thread
        wcs.__class__ = _LockedTabularWCS
        results.append(wcs.pixel_to_world_values(*pixel))
        linked.set()

    threads = [threading.Thread(target=target, daemon=True) for target in (worker, link)]
    threads[0].start()
    assert started.wait(10)  # and in its next transform
    threads[1].start()
    for thread in threads:
        thread.join(timeout=10)
    assert not any(thread.is_alive() for thread in threads)
    assert all(np.array_equal(got, want) for values in results for got, want in zip(values, expected))


def test_the_browser_lists_and_opens_each_sst_cube(qtbot, monkeypatch, tmp_path):
    # D68: an archive folder's observation, an entry per cube, a quicklook per cube; and the Plugins menu's SST entry,
    # IRIS's offering none (230-13)
    folder = tmp_path / "SST-archive_obs492_20230919_CRISP_stokes"
    folder.mkdir()
    for name, line, stokes in (("nb_8542_im.fits", "Ca II 8542", 4), ("nb_6173_im.fits", "Fe I 6173", 1)):
        write_sst_cube(folder / name, (3, stokes, 5, 12, 16))
        for keyword, value in (("WAVEBAND", line), ("STARTOBS", "2021-09-05T00:19:00"), ("DATE-END", DATEREF)):
            fits.setval(folder / name, keyword, value=value)
    [observation] = scan_directory(tmp_path)
    assert (observation.obsid, observation.startobs) == ("CRISP", "2021-09-05T00:19:00")
    assert observation.description == folder.name
    stokes = "Ca II 8542, Stokes I, Q, U and V"
    assert observation.sst == {stokes: folder / "nb_8542_im.fits", "Fe I 6173": folder / "nb_6173_im.fits"}
    monkeypatch.setattr(ProfileViewer, "large_data_size", 1)
    app = bare_app_for(qtbot, monkeypatch)
    browse(qtbot, app, monkeypatch, tmp_path, [0])
    assert app.tab_names[1:] == ["SST Ca II 8542", "SST Fe I 6173"]
    assert [len(app.viewers[tab]) for tab in (1, 2)] == [9, 6]
    choice = {}

    def choose(parent, title, label, items, *args):
        choice["items"] = items
        return items[1], True

    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", choose)
    quicklook_sst(app.session, app.data_collection)  # 'SST: quicklook…'
    assert choice["items"] == ["SST Ca II 8542", "SST Fe I 6173"]
    assert app.tab_names[-1] == "SST Fe I 6173"
    messages = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda parent, title, text: messages.append(text))
    quicklook_iris(app.session, app.data_collection)  # 'IRIS: quicklook…'
    assert messages == ["No IRIS observation with a raster or slit-jaw image is loaded."]
    assert app.tab_names[-1] == "SST Fe I 6173"
    iris_quicklook(app.session, app.data_collection)  # glue --startup=iris_quicklook
    assert app.tab_names[-2:] == ["SST Ca II 8542", "SST Fe I 6173"]
    assert len(app.viewers[-1]) == 6  # and no Image viewer of a cube
