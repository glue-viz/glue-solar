import os
import tarfile

import numpy as np
import pytest

from astropy.io import fits

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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


def _write_image(path, header):
    # real SJI files spell the units this way; astropy's WCS warns unless they are normalised
    header["CUNIT1"], header["CUNIT2"], header["CUNIT3"] = "arcsecs", "arcsecs", "seconds"
    header.update({
        "CTYPE1": "HPLN-TAN", "CTYPE2": "HPLT-TAN", "CTYPE3": "Time",
        "CRPIX1": 3.0, "CRPIX2": 2.5, "CRPIX3": 2.0,
        "CRVAL1": header["XCEN"], "CRVAL2": header["YCEN"], "CRVAL3": 3600.0,
        "CDELT1": 0.5, "CDELT2": 0.5, "CDELT3": 3600.0,
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
            # an unrotated observation: identity PC matrix (needs irispy with
            # row-wise dropped-pointing handling to load)
            "PC1_1IX": 1.0,
            "PC2_2IX": 1.0,
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


@pytest.fixture(scope="session")
def irispy_test_files():
    """Real files shipped with irispy and exposed through its public test-data helper."""
    from irispy.data.test import get_test_data_filenames

    files = get_test_data_filenames()
    assert files
    return files
