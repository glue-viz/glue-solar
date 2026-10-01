import os
import sys
import tarfile
import tempfile
import traceback
from types import SimpleNamespace

import numpy as np
import pytest
from qtpy.QtCore import QSettings

from astropy.io import fits

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_configure(config):
    # As glue's and glue-qt's conftests do: an error in a viewer's add_data or add_subset raises instead of
    # opening a message box, and close prompts are skipped
    os.environ["GLUE_TESTING"] = "True"
    # and never read or write the user's ~/.glue
    from glue import config as glue_config

    glue_config.CFG_DIR = tempfile.mkdtemp()


def pytest_unconfigure(config):
    os.environ.pop("GLUE_TESTING", None)


@pytest.fixture(autouse=True)
def _idle_draw_errors_fail():
    """Fail a test in which a Qt canvas raised during an idle draw, which matplotlib only prints."""
    from matplotlib.backends import backend_qt

    errors = []

    def print_exc():
        traceback.print_exc()
        errors.append(sys.exc_info()[1])

    original, backend_qt.traceback = backend_qt.traceback, SimpleNamespace(print_exc=print_exc)
    try:
        yield
    finally:
        backend_qt.traceback = original
    if errors:
        pytest.fail(f"an idle draw raised {errors[0]!r}")


class IsolatedQSettings(QSettings):
    """``QSettings(organization, application)`` kept in an INI file in one test's ``tmp_path``."""

    directory = None

    def __init__(self, organization, application):
        super().__init__(os.path.join(self.directory, f"{organization}-{application}.ini"), QSettings.IniFormat)


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Keep the loader's settings, such as the last browsed folder, out of the user's own."""
    from glue_solar.sources.loaders import iris

    monkeypatch.setattr(IsolatedQSettings, "directory", str(tmp_path))
    monkeypatch.setattr(iris, "QSettings", IsolatedQSettings)

MD5 = "0123456789abcdef0123456789abcdef-"
# (date, time, obsid): raster + SJI + AIA cutout, split across pooch-style dirs
OBS_A = ("20250328", "225628", "3400109360")
# SJI only, gzipped
OBS_B = ("20230211", "083601", "3880012095")
# un-extracted archive only
OBS_C = ("20140708", "114109", "3824262996")
# hand-made file with a sparse header and no L2 stem in its name
OBS_S = "3860259453"


def startobs(date, time):
    return f"{date[:4]}-{date[4:6]}-{date[6:]}T{time[:2]}:{time[2:4]}:{time[4:]}.500"


N_EXPOSURES = 3


def _header(instrume, obsid, start, **extra):
    h = fits.Header()
    h["TELESCOP"] = "IRIS"
    h["INSTRUME"] = instrume
    h["OBSID"] = obsid
    h["STARTOBS"] = start
    h["ENDOBS"] = start
    h["DATE_OBS"] = start
    h["DATE_END"] = start
    h["OBS_DESC"] = "Test raster 1x2 3s"
    h["XCEN"] = 1.5
    h["YCEN"] = -2.5
    h["SAT_ROT"] = 0.0
    h["NEXP"] = N_EXPOSURES
    h["NEXPOBS"] = N_EXPOSURES
    h["NRASTERP"] = 1
    h["STEPS_AV"] = 0.0
    h["EXPTIME"] = 2.0
    for key, value in extra.items():
        h[key] = value
    return h


def _aux_hdu(names, values):
    # Real files store per-exposure values in an image HDU whose header maps
    # column names to column indices
    data = np.zeros((N_EXPOSURES, len(names)))
    for name, column in values.items():
        data[:, names.index(name)] = column
    return fits.ImageHDU(data, header=fits.Header({name: i for i, name in enumerate(names)}))


def _source_filename_hdu(start, column):
    # Level 1 source filenames encode the exposure midpoints, e.g.
    # iris20210905_00183775_nuv.fits
    stamp = start[:10].replace("-", "")
    names = [f"iris{stamp}_{hour:02d}000000_{column[:3].lower()}.fits" for hour in range(N_EXPOSURES)]
    return fits.BinTableHDU.from_columns([fits.Column(name=column, format="66A", array=names)])


def _write_image(path, header, roll=1.0):
    # A small real rotation by default avoids irispy 0.8.1 treating zero
    # off-diagonal PC entries as missing pointing samples.
    angle = np.deg2rad(roll)
    # real SJI files spell the units this way; astropy's WCS warns unless they are normalised
    header["CUNIT1"], header["CUNIT2"], header["CUNIT3"] = "arcsecs", "arcsecs", "seconds"
    header.update({
        "CTYPE1": "HPLN-TAN", "CTYPE2": "HPLT-TAN", "CTYPE3": "Time",
        "CRPIX1": 3.0, "CRPIX2": 2.5, "CRPIX3": 2.0,
        "CRVAL1": header["XCEN"], "CRVAL2": header["YCEN"], "CRVAL3": 3600.0,
        "CDELT1": 0.5, "CDELT2": 0.5, "CDELT3": 3600.0,
        "PC1_1": np.cos(angle), "PC1_2": -np.sin(angle),
        "PC2_1": np.sin(angle), "PC2_2": np.cos(angle),
    })
    primary = fits.PrimaryHDU(np.zeros((N_EXPOSURES, 4, 5), dtype=np.int16), header=header)
    # XCENIX:YCENIX and PC1_1IX:PC2_2IX must be contiguous - the SJI reader
    # slices them as blocks
    aux = _aux_hdu(
        ("TIME", "PZTX", "PZTY", "EXPTIMES", "OBS_VRIX", "OPHASEIX",
         "SLTPX1IX", "SLTPX2IX",
         "XCENIX", "YCENIX", "PC1_1IX", "PC1_2IX", "PC2_1IX", "PC2_2IX"),
        {
            "TIME": np.arange(N_EXPOSURES) * 3600.0,
            "EXPTIMES": 2.0,
            "XCENIX": header["XCEN"],
            "YCENIX": header["YCEN"],
            "PC1_1IX": header["PC1_1"],
            "PC1_2IX": header["PC1_2"],
            "PC2_1IX": header["PC2_1"],
            "PC2_2IX": header["PC2_2"],
        },
    )
    source = _source_filename_hdu(header["STARTOBS"], "SJIfilename")
    fits.HDUList([primary, aux, source]).writeto(path)


def _window_hdu(start, twave, xcen, ycen):
    header = fits.Header({
        "CTYPE1": "WAVE", "CUNIT1": "Angstrom", "CRPIX1": 1.0, "CRVAL1": twave, "CDELT1": 0.05,
        "CTYPE2": "HPLT-TAN", "CUNIT2": "arcsec", "CRPIX2": 2.0, "CRVAL2": ycen, "CDELT2": 0.33,
        # sit-and-stare files have CDELT3 == 0; the reader falls back to CDELT2
        "CTYPE3": "HPLN-TAN", "CUNIT3": "arcsec", "CRPIX3": 1.0, "CRVAL3": xcen, "CDELT3": 0.0,
        "DATE-OBS": start,
    })
    return fits.ImageHDU(np.zeros((N_EXPOSURES, 4, 5), dtype=np.int16), header=header)


def _write_raster(path, obsid, start):
    primary = fits.PrimaryHDU(header=_header(
        "SPEC", obsid, start,
        NWIN=2,
        TDESC1="C II 1336", TDET1="FUV1", TWAVE1=1335.7,
        TDESC2="Mg II k 2796", TDET2="NUV", TWAVE2=2796.4,
    ))
    xcen, ycen = primary.header["XCEN"], primary.header["YCEN"]
    windows = [_window_hdu(start, primary.header[f"TWAVE{i}"], xcen, ycen) for i in (1, 2)]
    aux = _aux_hdu(
        ("TIME", "PZTX", "PZTY", "EXPTIMEF", "EXPTIMEN", "OBS_VRIX",
         "OPHASEIX", "XCENIX", "YCENIX", "PC2_2IX", "PC3_2IX"),
        {
            "TIME": np.arange(N_EXPOSURES) * 3600.0,
            "EXPTIMEF": 2.0,
            "EXPTIMEN": 2.0,
            "XCENIX": xcen,
            "YCENIX": ycen,
            "PC2_2IX": 1.0,
        },
    )
    source = _source_filename_hdu(start, "NUVfilename")
    fits.HDUList([primary, *windows, aux, source]).writeto(path)


@pytest.fixture(scope="session")
def iris_tree(tmp_path_factory):
    """A pooch-cache-like folder holding four IRIS observations plus junk."""
    root = tmp_path_factory.mktemp("pooch")
    d, t, o = OBS_A
    stem = f"iris_l2_{d}_{t}_{o}"
    _write_image(root / f"{MD5}{stem}_SJI_1400_t000.fits.gz",
                 _header("SJI", o, startobs(d, t), TDESC1="SJI_1400", TWAVE1=1400.0, NWIN=1))
    raster_dir = root / f"{MD5}{stem}_raster"
    raster_dir.mkdir()
    for r in range(2):
        _write_raster(raster_dir / f"{stem}_raster_t000_r0000{r}.fits", o, startobs(d, t))
    sdo_dir = root / f"{MD5}{stem}_SDO"
    sdo_dir.mkdir()
    aia = _header("AIA_3", f"{d}_{t}_{o}", startobs(d, t), TDESC1="171_THIN", TWAVE1=171.0, OBS_DESC="")
    aia["TELESCOP"] = ""
    _write_image(sdo_dir / f"aia_l2_{d}_{t}_{o}_171.fits", aia)

    d, t, o = OBS_B
    _write_image(root / f"{MD5}iris_l2_{d}_{t}_{o}_SJI_2832_t000.fits.gz",
                 _header("SJI", o, startobs(d, t), TDESC1="SJI_2832", TWAVE1=2832.0, NWIN=1))

    d, t, o = OBS_C
    member = tmp_path_factory.mktemp("tar") / f"iris_l2_{d}_{t}_{o}_raster_t000_r00000.fits"
    _write_raster(member, o, startobs(d, t))
    with tarfile.open(root / f"{MD5}iris_l2_{d}_{t}_{o}_raster.tar.gz", "w:gz") as tar:
        tar.add(member, arcname=member.name)

    sparse = fits.Header()
    sparse["TELESCOP"] = "IRIS"
    sparse["INSTRUME"] = "SPEC"
    sparse["OBSID"] = OBS_S
    sparse["STARTOBS"] = "2014-09-10T11:28:25.590"
    fits.PrimaryHDU(header=sparse).writeto(root / f"{MD5}iris_l2_20140910_fexxi_rb_steps.fits.gz")

    (root / "tmpabc").write_bytes(b"\x1f\x8b\x08junk")
    (root / "notes.txt").write_text("not a fits file")
    return root


def find_irispy_test_file(files, name):
    """Match both 0.8.1 filenames and irispy's later explicit _test suffix."""
    return next(path for path in files if path.name.replace("_test.fits", ".fits") == name)


# Real IRIS files for remote-data tests: release assets of LM-SAL/irispy-data, checked by SHA-256
IRISPY_DATA = "https://github.com/LM-SAL/irispy-data/releases/download/v1/"
IRISPY_DATA_HASHES = {
    # OBSID 3400109360 (STEPS_AV -0.998): scan 0, Mg II k 2796 only
    "iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz": "56574d2e425fdf2f4e2d4343c112c3c3d85dad7e121ca0bc2fa4200d7cc8adf8",
    # OBSID 4000005156: scan 0 of the 64-step raster, Si IV 1403 only
    "iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz": "ac50a0255b73af1610702653e17d3b3b9c8fc37bc487a313e1c9fb3a2983428a",
    # OBSID 3640107442: five minutes of the nine aligned AIA channels
    "iris_l2_20250519_165924_3640107442_cutout_SDO.tar.gz": "db95aec5c0b3400e39d077b0e840e9280f72e2fac798e1fd15975257f3677dc4",
    # OBSID 4000255147: the first 50 frames of SJI 1400, full size
    "iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz": "b9a0b8cf2d98f5e1121000a14168079b113fdb0b169668ec1213411915afdb8f",
}


@pytest.fixture(scope="session")
def irispy_data():
    """Fetch a file of LM-SAL/irispy-data into pooch's cache; a tarball gives its sorted FITS files."""
    import pooch

    def fetch(name):
        if name.endswith(".tar.gz"):
            paths = pooch.retrieve(IRISPY_DATA + name, known_hash=IRISPY_DATA_HASHES[name], processor=pooch.Untar())
            return sorted(path for path in paths if path.endswith(".fits"))
        return pooch.retrieve(IRISPY_DATA + name, known_hash=IRISPY_DATA_HASHES[name])

    return fetch


@pytest.fixture(scope="session")
def irispy_test_files():
    """Real files shipped with irispy and exposed through its public test-data helper."""
    from irispy.data.test import get_test_data_filenames

    files = get_test_data_filenames()
    assert files
    return files
