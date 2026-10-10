"""
SST CRISP and CHROMIS cubes, on small files written as the SST archive's SSTRED exports are: File → Open gives the cube
alone, memory-mapped, with its time and wavelength at every pixel, its cavity maps and coordinates that sessions keep,
and once linked on request a region drawn on it selects the IRIS pixels at its place in the scan nearest their time.
"""

import mmap

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

from astropy.io import fits
from astropy.wcs import WCS

import glue_solar
from glue_solar.quicklook import _role, _timed, _times, nearest
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, raster_data
from glue_solar.sources.sst import _TabularWCS, sst_data
from glue_solar.tests.test_linking import RASTER, SJI, _real

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
):
    """
    Write an SST cube as SSTRED exports one, of ``shape`` (scans, Stokes, tunings, y, x): its pixel (x, y) at scan t is
    at ``centre + t * drift + R(roll) @ scale * (x - centre pixel, y - centre pixel)``, in arcsec, and its tuning k at
    scan t at ``start + t * cadence + 0.25 * k`` s since 2021-09-05 UTC. ``prefilters`` are the tunings of each cavity
    map, all of them in one map without OFFSET.3 and SCALE.3 by default; the map of extension version v is v + 0.001 *
    (scan + x / 100 + y / 10000) nm. The table gives the pointing at ``knots`` points along x, the corners by default.
    Returns the file's coordinate table, (scans, tunings, y corner, x point, lon, lat, wavelength, time).
    """
    scans, stokes, tunings, rows, columns = shape
    t, k, j, i = np.indices((scans, tunings, 2, knots), dtype=float)
    dx, dy = (i / (knots - 1) - 0.5) * (columns - 1) * scale, (j * (rows - 1) - (rows - 1) / 2) * scale
    cos, sin = np.cos(np.deg2rad(roll)), np.sin(np.deg2rad(roll))
    lon, lat = centre[0] + t * drift[0] + cos * dx - sin * dy, centre[1] + t * drift[1] + sin * dx + cos * dy
    coord = np.stack([lon, lat, 656.28 + 0.01 * (k - tunings // 2), start + t * cadence + 0.25 * k], -1)
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
    dates = fits.BinTableHDU.from_columns(
        [fits.Column("DATE-AVG", "25A", array=["2021-09-05T00:20:00.000000000"])], name="VAR-EXT-DATE-AVG"
    )
    fits.HDUList([fits.PrimaryHDU(values, header), table, *lookups, dates]).writeto(path)
    return coord


def _mapped(values):
    """Whether the array ``values`` views a memory-mapped file."""
    while not isinstance(values, mmap.mmap) and getattr(values, "base", None) is not None:
        values = values.base
    return isinstance(values, mmap.mmap)


def test_file_open_gives_the_cube_alone_memory_mapped(tmp_path):
    # SST12: not glue's 33 datasets, the WCSDVARR image and empty ones for the WCS-TAB and VAR-EXT tables
    path = tmp_path / "nb_6563_scans=0-2_im.fits"
    write_sst_cube(path)
    data = load_data(str(path))  # File → Open Data Set's choice of reader
    assert data.label == "nb_6563_scans=0-2_im"
    assert [cid.label for cid in data.main_components] == ["Intensity", "Time", "Cavity error"]
    values = data.get_component("Intensity").data
    assert _mapped(values)
    np.testing.assert_array_equal(values, fits.getdata(path))
    assert isinstance(data.coords, _TabularWCS)
    assert data.meta["SPECSYS"] == "TOPOCENT"  # SST2: astropy needs one beside OBSGEO
    assert _role(data) == "sst"
    assert not _timed(data)  # in no time sync yet


def test_time_and_wavelengths_are_the_table_s_at_every_pixel(tmp_path):
    # glue's own reader gave every tuning of a scan the time of its first: astropy says time depends on the scan only
    path = tmp_path / "cube.fits"
    coord = write_sst_cube(path, drift=(5.0, -3.0), roll=10.0)
    data = sst_data(path)
    times = np.datetime64(DATEREF, "ns") + np.round(coord[:, :, 0, 0, 3] * 1e9).astype("timedelta64[ns]")
    np.testing.assert_array_equal(data["Time"], np.broadcast_to(times[:, None, :, None, None], data.shape))
    seconds, _, wavelength, lat, lon = data.world_component_ids
    np.testing.assert_allclose(data[seconds], np.broadcast_to(coord[:, None, :, :1, :1, 3], data.shape), rtol=1e-12)
    np.testing.assert_allclose(data[wavelength], np.broadcast_to(coord[:, None, :, :1, :1, 2], data.shape), rtol=1e-12)
    # the pointing of each scan, at the field's corners
    corners = data[lon][:, 0, 0][:, [0, -1]][:, :, [0, -1]], data[lat][:, 0, 0][:, [0, -1]][:, :, [0, -1]]
    np.testing.assert_allclose(corners, np.moveaxis(coord[:, 0, :, :, :2], -1, 0), atol=1e-9)


def test_the_cavity_error_is_each_tuning_s_map(tmp_path):
    # CHROMIS's Ca II H & K cube has a map for each prefilter, by tuning, and none for its continuum tuning
    path = tmp_path / "cube.fits"
    write_sst_cube(path, shape=(2, 1, 7, 4, 5), prefilters=[range(3), range(3, 6)])
    data = sst_data(path)
    cavity = data.get_component("Cavity error")
    assert cavity.units == "nm"
    with fits.open(path) as hdulist:
        maps = [hdulist["WCSDVARR", version].data[:, :, 0] for version in (1, 2)]
    expected = np.concatenate([maps[0]] * 3 + [maps[1]] * 3 + [np.full_like(maps[0], np.nan)], axis=1)
    np.testing.assert_array_equal(data["Cavity error"], np.broadcast_to(expected[:, None], data.shape))
    np.testing.assert_array_equal(data["Cavity error", (1, 0, slice(None), 2, 3)], expected[1, :, 2, 3])


def test_the_inverse_is_wcslib_s_inside_the_table_and_takes_the_line_core_outside(tmp_path):
    path = tmp_path / "cube.fits"
    coord = write_sst_cube(path, drift=(5.0, -3.0), roll=10.0)
    coords = sst_data(path).coords
    rng = np.random.default_rng(0)
    pixels = [
        rng.uniform(-2, 17, 40),
        rng.uniform(-2, 13, 40),
        rng.integers(0, 5, 40),
        np.zeros(40),
        rng.integers(0, 3, 40),
    ]
    world = coords.pixel_to_world_values(*pixels)
    inside = WCS.world_to_pixel_values(coords, *world)  # NaN off the field, where this inverse goes on
    for got, wcslib, pixel in zip(coords.world_to_pixel_values(*world), inside, pixels):
        np.testing.assert_allclose(got, pixel, atol=1e-9)
        np.testing.assert_allclose(got[~np.isnan(wcslib)], wcslib[~np.isnan(wcslib)], atol=1e-6)  # wcslib's tolerance
    assert (~np.isnan(inside[0])).sum() >= 20
    # glue's CRVAL, 0, for a wavelength and time: the line core of the nearest scan, the first, where wcslib gives NaN
    lon, lat, *_ = coords.pixel_to_world_values(3.5, 7.25, 2, 0, 0)
    assert np.isnan(WCS.world_to_pixel_values(coords, lon, lat, 0, 1, 0)[0])
    x, y, wavelength, stokes, scan = coords.world_to_pixel_values(lon, lat, 0, 1, 0)
    np.testing.assert_allclose([x, y, stokes, scan], [3.5, 7.25, 0, 0], atol=1e-9)
    assert np.isnan(wavelength)
    # a time: the scan nearest it, ties to the earlier
    for seconds, nearest_scan in ((coord[1, 2, 0, 0, 3] + 29, 1), (coord[1, 2, 0, 0, 3] + 30, 1), (1e9, 2)):
        lon, lat, *_ = coords.pixel_to_world_values(3.5, 7.25, 2, 0, nearest_scan)
        np.testing.assert_allclose(coords.world_to_pixel_values(lon, lat, 0, 1, seconds)[:2], [3.5, 7.25], atol=1e-9)


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
    for slices in ((0, 0, 0, 0, 0), (2, 0, 4, 0, 0)):  # the scan and tuning sliders, and that tuning's time
        viewer.state.slices = slices
        viewer.figure.canvas.draw()
        assert readout.text() == f"{np.datetime_as_string(data['Time', slices], unit='ms')} UTC"
    assert viewer.layers[0].enabled


def test_a_table_of_more_points_than_the_field_s_corners_takes_wcslib_s_inverse(tmp_path):
    # the loader's own inverse solves SSTRED's tables of the field's corners only
    path = tmp_path / "cube.fits"
    write_sst_cube(path, drift=(5.0, -3.0), roll=10.0, knots=3)
    coords = sst_data(path).coords
    world = coords.pixel_to_world_values(3.5, 7.25, 2, 0, 1)
    np.testing.assert_allclose(coords.world_to_pixel_values(*world), [3.5, 7.25, 2, 0, 1], atol=1e-6)
    assert np.isnan(coords.world_to_pixel_values(*world[:2], 0, 1, 0)[0])  # wcslib's NaN outside the table


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
    write_sst_cube(path, drift=(5.0, -3.0), roll=10.0, prefilters=[range(2), range(2, 5)])
    glue_solar.setup()
    app = GlueApplication()  # not given to qtbot, which cannot close it once glue-qt has deleted it as it closed
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))  # not glue's modal dialog
    data = app.load_data(str(path))  # File → Open Data Set
    app.new_data_viewer(ImageViewer, data=data).state.slices = (2, 0, 3, 0, 0)
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
        assert tuple(restored.viewers[0][0].state.slices) == (2, 0, 3, 0, 0)


def _sst_pixels(coord, lon, lat, when, shape, scale, roll):
    """
    The pixel (x, y) of a cube ``write_sst_cube`` wrote with ``coord``, ``shape``, ``scale`` and ``roll`` at ``lon``,
    ``lat`` in the scan nearest each time ``when``, timed by its middle tuning, from the cube's own geometry.
    """
    *_, tunings, rows, columns = shape
    seconds = (when - np.datetime64(DATEREF)) / np.timedelta64(1, "s")
    scans = coord[:, tunings // 2, 0, 0, 3]
    scan = np.argmin(abs(np.asarray(seconds)[..., None] - scans), axis=-1)
    du, dv = lon - coord[scan, 0, :, :, 0].mean((-1, -2)), lat - coord[scan, 0, :, :, 1].mean((-1, -2))
    cos, sin = np.cos(np.deg2rad(roll)), np.sin(np.deg2rad(roll))
    return (cos * du + sin * dv) / scale + (columns - 1) / 2, (cos * dv - sin * du) / scale + (rows - 1) / 2


def test_once_linked_an_sst_region_or_point_selects_the_iris_pixels_at_its_place(tmp_path, sns):
    # D67: glue gave the cube's wavelength and time their CRVAL, 0, outside its table, which selected nothing; a mosaic's
    # pointing changes with each scan, so each SJI frame and raster exposure takes the scan nearest it
    sji, raster = sns
    frames = _times(sji, 0)
    start, cadence = (frames[10] - np.datetime64(DATEREF)), (frames[-1] - frames[10]) / 3  # from the 11th frame
    shape, scale, roll = (4, 1, 5, 30, 40), 1.1, 8.0
    seconds = [time / np.timedelta64(1, "s") for time in (start, cadence)]
    coord = write_sst_cube(tmp_path / "cube.fits", shape, (-55.0, -400.0), (4.0, -3.0), scale, roll, *seconds)
    cube = sst_data(tmp_path / "cube.fits")
    dc = DataCollection([sji, raster, cube])
    keep_hpc_linked(dc)
    roi = RectangularROI(10.3, 29.6, 6.2, 21.7)
    region = RoiSubsetState(xatt=cube.pixel_component_ids[4], yatt=cube.pixel_component_ids[3], roi=roi)
    with pytest.raises(IncompatibleAttribute):  # D64: linked on request only
        sji.get_mask(region)
    keep_hpc_linked(dc, others=dc)  # 'IRIS: link helioprojective coordinates'
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
    # glue's Pixel point, at the cube's first scan and tuning: the raster's exposure and slit row nearest it, and in the
    # slit-jaw frame nearest that scan, the pixel there
    point = PixelSubsetState(cube, [slice(None)] * 3 + [slice(15, 16), slice(30, 31)])
    lon, lat, *_ = cube.coords.pixel_to_world_values(30, 15, 0, 0, 0)
    exposure, slit = np.indices(raster.shape[:2])
    _, lats, lons = raster.coords.pixel_to_world_values(0, slit, exposure)
    assert point._to_linked_pixel_coords(raster) == [
        *np.unravel_index(np.argmin(np.hypot(lons - lon, lats - lat)), raster.shape[:2]),
        None,
    ]
    [frame], _ = nearest([np.datetime64(DATEREF) + np.timedelta64(int(coord[0, 2, 0, 0, 3] * 1e9), "ns")], frames)
    x, y, _ = sji.coords.world_to_pixel_values(lon, lat, sji.coords.pixel_to_world_values(0, 0, frame)[2])
    assert point._to_linked_pixel_coords(sji) == [frame, round(float(y)), round(float(x))]
