"""
Scan a directory tree for IRIS Level 2 files and group them by observation.

Only primary headers are read, never data, so scanning a multi-GB archive
takes seconds. Files cached by pooch (``<md5>-<name>``) are handled.
"""

import re
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from astropy.io import fits

__all__ = ["Observation", "extract_archive", "scan_directory", "strip_pooch"]

_POOCH = re.compile(r"^[0-9a-f]{32}-")
# iris_l2_YYYYMMDD_HHMMSS_OBSID_... and the co-aligned aia_l2_... cutouts
_L2_STEM = re.compile(r"^(?:iris|aia)_l2_(?P<date>\d{8})_(?P<time>\d{6})_(?P<obsid>\d{10})")
_FITS = (".fits", ".fits.gz")


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
    sdo: dict[str, Path] = field(default_factory=dict)  # "171_THIN" -> AIA cutout
    archives: list[Path] = field(default_factory=list)  # un-extracted *.tar.gz, listed only

    @property
    def nfiles(self):
        return len(self.sji) + len(self.rasters) + len(self.sdo)


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


def _is_supported_file(name, header):
    """Accept IRIS science files and the aligned AIA cutouts produced for them."""
    instrume = str(header.get("INSTRUME", ""))
    if instrume in {"SPEC", "SJI"}:
        return header.get("TELESCOP") == "IRIS"
    return name.startswith("aia_l2_") and instrume.startswith("AIA")


def scan_directory(root, recursive=True):
    """
    Group every IRIS Level 2 file below ``root`` into `Observation` objects.

    Parameters
    ----------
    root : path-like
        Directory to scan.
    recursive : bool
        Descend into subdirectories.

    Returns
    -------
    list of `Observation`, sorted by start time.
    """
    root = Path(root)
    paths = root.rglob("*") if recursive else root.iterdir()
    found = {}
    headers = []
    for path in sorted(p for p in paths if p.is_file()):
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
            header = fits.getheader(path)
        except Exception:  # noqa: BLE001 - not a FITS file after all
            continue
        if not _is_supported_file(name, header):
            continue
        key = _key_from_name(name) or _key_from_header(header)
        if key is not None:
            headers.append((path, name, key, header))
    # IRIS headers first so pointing/description come from the instrument, not the AIA cutout
    raster_names = set()
    for path, name, key, header in sorted(
        headers, key=lambda h: (str(h[3].get("INSTRUME", "")).startswith("AIA"), h[1], str(h[0]))
    ):
        obs = found.setdefault(key, Observation(*key))
        _fill(obs, header)
        instrume = str(header.get("INSTRUME", ""))
        if instrume == "SJI":
            obs.sji[header.get("TDESC1", name)] = path
        elif instrume == "SPEC":
            identity = (*key, name)
            if identity in raster_names:
                continue
            raster_names.add(identity)
            obs.rasters.append(path)
            if not obs.windows:
                obs.windows = [header[f"TDESC{i}"] for i in range(1, header.get("NWIN", 0) + 1)]
        elif instrume.startswith("AIA"):
            obs.sdo[header.get("TDESC1", name)] = path
    for obs in found.values():
        obs.rasters.sort(key=lambda p: strip_pooch(p.name))
        obs.description = obs.description or _obsid_description(obs.obsid)
    return sorted(found.values(), key=lambda o: (o.startobs, o.obsid))
