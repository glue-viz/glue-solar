"""
Scan a directory tree for IRIS Level 2 files and group them by observation.

Only primary headers are read, never data, so scanning a multi-GB archive
takes seconds. Files cached by pooch (``<md5>-<name>``) are handled.
"""

import gzip
import itertools
import re
import tarfile
import tempfile
import threading
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

import astropy.units as u
from astropy.io import fits
from astropy.time import Time

__all__ = ["Observation", "extract_archive", "find_observation_files", "scan_directory", "strip_pooch"]

_POOCH = re.compile(r"^[0-9a-f]{32}-")
# iris_l2_YYYYMMDD_HHMMSS_OBSID_... and the co-aligned aia_l2_... cutouts and Hinode sot_l2_... and sotsp_l2_... cubes
_L2_STEM = re.compile(r"^(?:iris|aia|sot|sotsp)_l2_(?P<date>\d{8})_(?P<time>\d{6})_(?P<obsid>\d{10})")
_FITS = (".fits", ".fits.gz")
# ponytail: how long before a time window an observation stamped in a filename may have begun; longer ones are missed
_LONGEST = 1 * u.day


def _primary_header(path):
    """
    The primary header of the FITS file ``path``, gzipped or not. astropy's ``getheader`` decompresses all of a
    gzipped file to find where the next HDU starts.
    """
    with open(path, "rb") as file:
        gzipped = file.read(2) == b"\x1f\x8b"
        file.seek(0)
        stream = gzip.GzipFile(fileobj=file) if gzipped else file
        # as astropy does: a header is read up to its END card, so any other file would be read to its end
        if stream.read(6) != b"SIMPLE":
            raise OSError(f"{path} is not a FITS file")
        stream.seek(0)
        return fits.Header.fromfile(stream)


def strip_pooch(name):
    """Remove the ``<md5>-`` prefix pooch puts on cached files."""
    return _POOCH.sub("", name)


def extract_archive(path):
    """
    Unpack a ``*.tar.gz`` next to itself, into ``<name without .tar.gz>/``.

    This is the layout irispy and pooch use, so a later `scan_directory`
    picks the files up under the same observation as the archive.

    Returns
    -------
    `~pathlib.Path`
        The directory the files were extracted into.
    """
    path = Path(path)
    target = path.with_suffix("").with_suffix("")
    if target.exists():
        raise FileExistsError(f"Extraction target already exists: {target}")
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=f".{target.name}-") as temporary:
        with tarfile.open(path, "r:*") as tar:
            tar.extractall(temporary, filter="data")
        if target.exists():
            raise FileExistsError(f"Extraction target already exists: {target}")
        Path(temporary).rename(target)
    return target


@dataclass
class Observation:
    """One IRIS observation (OBSID run at a given start time) and its files."""

    obsid: str
    startobs: str
    endobs: str | None = None
    description: str = ""
    xcen: float | None = None
    ycen: float | None = None
    sat_rot: float | None = None
    sji: dict[str, Path] = field(default_factory=dict)  # "SJI_1400" -> file
    rasters: list[Path] = field(default_factory=list)  # sorted by raster index
    windows: list[str] = field(default_factory=list)  # TDESC1..NWIN of the first raster
    window_tips: dict[str, str] = field(default_factory=dict)  # each window's detector and wavelength range
    sdo: dict[str, Path] = field(default_factory=dict)  # "171_THIN" -> AIA cutout
    sot: dict[str, Path] = field(default_factory=dict)  # "G band 4305", "6302A B_LOS" -> Hinode/SOT cube (ITN 32)
    archives: list[Path] = field(default_factory=list)  # un-extracted *.tar.gz, listed only

    @property
    def nfiles(self):
        return len(self.sji) + len(self.rasters) + len(self.sdo) + len(self.sot)


def _obsid_description(obsid):
    try:
        from irispy.obsid import ObsID

        return ObsID(int(obsid))["raster_fulldesc"]
    except Exception:  # noqa: BLE001 - only OBSID versions 36/38/40 decode
        return ""


def _key_from_name(name):
    m = _L2_STEM.match(name)
    if not m:
        return None
    d, t = m["date"], m["time"]
    return m["obsid"], f"{d[:4]}-{d[4:6]}-{d[6:]}T{t[:2]}:{t[2:4]}:{t[4:]}"


def _key_from_header(header):
    obsid, startobs = header.get("OBSID"), header.get("STARTOBS")
    if not obsid or not startobs:
        return None
    # AIA cutouts store the full "YYYYMMDD_HHMMSS_OBSID" stem in OBSID
    return str(obsid).split("_")[-1], str(startobs)[:19]


def _fill(obs, header):
    """Fill observation-level keywords from the first header that has them."""
    obs.endobs = obs.endobs or header.get("ENDOBS")
    obs.description = obs.description or str(header.get("OBS_DESC", "")).strip()
    for attr, key in (("xcen", "XCEN"), ("ycen", "YCEN"), ("sat_rot", "SAT_ROT")):
        if getattr(obs, attr) is None and header.get(key) is not None:
            setattr(obs, attr, float(header[key]))


def _window_tip(header, i):
    """Raster window ``i``'s detector and wavelength range, from the primary header: 'FUV1, 1332.7–1337.2 Å'."""
    tip = str(header.get(f"TDET{i}", ""))
    low, high = header.get(f"TWMIN{i}"), header.get(f"TWMAX{i}")
    return tip if low is None or high is None else f"{tip}, {low:.1f}–{high:.1f} Å"


def _sji_key(header, name):
    """The SJI's TDESC1, plus the variant its filename names: deconvolved SJIs share the plain TDESC1."""
    band = header.get("TDESC1", name)
    return f"{band} (deconvolved)" if "_deconvolved." in name else band


def _is_supported_file(name, header):
    """Accept IRIS science files and the aligned AIA cutouts and Hinode/SOT cubes produced for them."""
    instrume = str(header.get("INSTRUME", ""))
    if instrume in {"SPEC", "SJI"}:
        return header.get("TELESCOP") == "IRIS"
    if name.startswith(("sot_l2_", "sotsp_l2_")):
        return instrume.startswith("SOT")
    return name.startswith("aia_l2_") and instrume.startswith("AIA")


def _isot(time):
    """``time`` in UTC to the second, as the filenames and STARTOBS give it: '2013-09-02T16:39:35'."""
    return None if time is None else Time(time).utc.isot[:19]


def _wanted(name, pattern, earliest, end):
    """Whether to read the file ``name``: it matches ``pattern`` and, if its name has one, its stamp is in range."""
    if pattern is not None and not fnmatch(name, pattern):
        return False
    key = _key_from_name(name)
    return key is None or ((earliest is None or key[1] >= earliest) and (end is None or key[1] <= end))


def scan_directory(root, recursive=True, skipped=None, stop=None, report=None, start=None, end=None, pattern=None):
    """
    Group every IRIS Level 2 file below ``root``, outside hidden files and folders, into `Observation` objects.

    ``start``, ``end`` and ``pattern`` leave files out by their names, before any header is read: a time window
    reads only the files whose names are stamped from a day before ``start`` to ``end``, and those with no stamp.

    Parameters
    ----------
    root : path-like
        Directory to scan.
    recursive : bool
        Descend into subdirectories.
    skipped : list, optional
        Gets the path of every IRIS raster file left out because it is not Level 2 (its ``DATA_LEV`` is not 2), such
        as a product derived from rasters.
    stop : `threading.Event`, optional
        Once set, ends the scan between files, or while it lists them, with what it found so far.
    report : callable, optional
        ``report(percent)`` with the percentage of the files read, before each file, and 100 once every file is read.
    start, end : `~astropy.time.Time`, `~datetime.datetime` or str, optional
        List only the observations that run at some time from ``start`` to ``end``. An archive's observation is
        listed if it begins within a day before ``start``, as its end is not known until it is extracted.
    pattern : str, optional
        A glob, such as ``"*SJI_1400*"``, that the file names, without pooch's prefix, must match.

    Returns
    -------
    list of `Observation`, sorted by start time.
    """
    root = Path(root)
    earliest = None if start is None else _isot(Time(start) - _LONGEST)
    start, end = _isot(start), _isot(end)
    skipped = [] if skipped is None else skipped
    stop = threading.Event() if stop is None else stop
    report = report or (lambda percent: None)
    paths = itertools.takewhile(lambda _: not stop.is_set(), root.rglob("*") if recursive else root.iterdir())
    found = {}
    headers = []
    # not hidden ones, such as the folder `extract_archive` unpacks into before it renames it
    visible = (p for p in paths if not any(part.startswith(".") for part in p.relative_to(root).parts))
    files = sorted(p for p in visible if _wanted(strip_pooch(p.name), pattern, earliest, end) and p.is_file())
    for n, path in enumerate(files):
        report(100 * n // len(files))
        if stop.is_set():
            break
        name = strip_pooch(path.name)
        if name.endswith(".tar.gz"):
            key = _key_from_name(name)
            extracted = path.with_suffix("").with_suffix("").is_dir()  # already unpacked next to it
            if key and not extracted:
                found.setdefault(key, Observation(*key)).archives.append(path)
            continue
        if not name.endswith(_FITS):
            continue
        try:
            header = _primary_header(path)
        except Exception:  # noqa: BLE001 - not a FITS file after all
            continue
        if not _is_supported_file(name, header):
            continue
        if header["INSTRUME"] == "SPEC" and header.get("DATA_LEV") != 2:
            skipped.append(path)
            continue
        key = _key_from_name(name) or _key_from_header(header)
        if key is not None:
            headers.append((path, name, key, header))
    else:
        if files or not stop.is_set():  # unless a Stop cut the listing short of any file
            report(100)  # a Stop from now on leaves nothing out
    # IRIS headers first so pointing/description come from the instrument, not an AIA cutout or SOT cube
    raster_names = set()
    for path, name, key, header in sorted(
        headers, key=lambda h: (str(h[3].get("INSTRUME", "")).startswith(("AIA", "SOT")), h[1], str(h[0]))
    ):
        obs = found.setdefault(key, Observation(*key))
        _fill(obs, header)
        instrume = str(header.get("INSTRUME", ""))
        if instrume == "SJI":
            obs.sji[_sji_key(header, name)] = path
        elif instrume == "SPEC":
            identity = (*key, name)
            if identity in raster_names:
                continue
            raster_names.add(identity)
            obs.rasters.append(path)
            if not obs.windows:
                obs.windows = [header[f"TDESC{i}"] for i in range(1, header.get("NWIN", 0) + 1)]
                obs.window_tips = {header[f"TDESC{i}"]: _window_tip(header, i) for i in range(1, len(obs.windows) + 1)}
        elif instrume.startswith("AIA"):
            obs.sdo[header.get("TDESC1", name)] = path
        elif instrume.startswith("SOT"):
            band = str(header.get("TDESC1", name))
            if instrume == "SOT-SP":  # every SP map's TDESC1 is 6302A
                band += f" {header.get('BTYPE', '')}"
            # as irispy's read_files keys them, a repeat with its file's name
            obs.sot[band if band not in obs.sot else f"{band} ({Path(name).stem})"] = path
    found = [
        obs
        for obs in found.values()
        if (end is None or obs.startobs <= end)
        and (start is None or obs.endobs is None or str(obs.endobs)[:19] >= start)
    ]
    for obs in found:
        obs.rasters.sort(key=lambda p: strip_pooch(p.name))
        obs.description = obs.description or _obsid_description(obs.obsid)
    return sorted(found, key=lambda o: (o.startobs, o.obsid))


def find_observation_files(directory, start=None, end=None, pattern=None, recursive=True):
    """
    The files of the observations below ``directory`` that run at some time from ``start`` to ``end``, as
    `scan_directory` finds them: per observation, by start time, its rasters, slit-jaw images, AIA cutouts, Hinode/SOT
    cubes and un-extracted archives.

    Pass the same time as ``start`` and ``end`` for the observation running at that time, and a ``pattern`` such
    as ``"*_raster_t*"`` for only its rasters.

    Returns
    -------
    list of `~pathlib.Path`
    """
    return [
        path
        for obs in scan_directory(directory, recursive, start=start, end=end, pattern=pattern)
        for path in (*obs.rasters, *obs.sji.values(), *obs.sdo.values(), *obs.sot.values(), *obs.archives)
    ]
