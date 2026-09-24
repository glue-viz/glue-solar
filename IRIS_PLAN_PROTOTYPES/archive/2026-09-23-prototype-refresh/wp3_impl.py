"""
WP3 final-form code, applied by monkeypatch because the repo is read-only.
Everything below the marker is what goes into glue_solar/sources/loaders/iris.py
(plus `read_iris_rasters`, and maps.py switching to SolarVisualAttributes).
"""
import base64
import io
import os

import numpy as np
import asdf
import gwcs
from glue.core.state import GlueSerializeError, loader, saver
from glue.core.visual import VisualAttributes
from ndcube.wcs.wrappers import CompoundLowLevelWCS

import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS

import glue_solar.sources.loaders.iris as L
import glue_solar.sources.maps as M

# ---------------------------------------------------------------- session support


def _tab_record(wcs):
    """Header string plus a rebuilt WCS-TABLE extension: astropy can read -TAB tables but not write them."""
    # ponytail: relies on irispy's WCS-TABLE layout (irispy/io/spectrograph.py _create_tabular_wcs):
    # one table, PS2_1 == PS3_1 == the coordinate column, and linear index vectors
    # psi(1)..psi(NAXIS) with K samples. astropy exposes Tabprm.coord but not the index vectors.
    header = fits.Header.fromstring(wcs.wcs.to_header(relax=True))
    table = wcs.wcs.tab[0]
    columns = {header["PS2_1"]: np.ascontiguousarray(table.coord)}
    for axis in (2, 3):
        pixels = np.array([1, wcs.pixel_shape[axis - 1]], dtype=float)
        psi = wcs.wcs.crval[axis - 1] + wcs.wcs.cdelt[axis - 1] * (pixels - wcs.wcs.crpix[axis - 1])
        columns[header[f"PS{axis}_2"]] = np.linspace(psi[0], psi[1], table.K[axis - 2])
    record = np.array([tuple(columns.values())], dtype=[(k, float, v.shape) for k, v in columns.items()])
    buffer = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(record, name=header["PS2_0"])]).writeto(buffer)
    return {"kind": "fits-tab", "header": header.tostring(), "table": base64.b64encode(buffer.getvalue()).decode()}


def _wcs_record(wcs):
    """JSON-safe record of any WCS the IRIS loaders produce, recursing through wrappers."""
    if isinstance(wcs, gwcs.WCS):
        buffer = io.BytesIO()
        asdf.AsdfFile({"wcs": wcs}).write_to(buffer)
        return {"kind": "asdf", "b64": base64.b64encode(buffer.getvalue()).decode()}
    if isinstance(wcs, WCS):
        shape = None if wcs.pixel_shape is None else [int(n) for n in wcs.pixel_shape]
        if any(ctype.endswith("-TAB") for ctype in wcs.wcs.ctype):
            return {**_tab_record(wcs), "shape": shape}
        return {"kind": "fits", "header": wcs.to_header_string(), "shape": shape}
    if isinstance(wcs, SlicedLowLevelWCS):
        # array order: that is what the SlicedLowLevelWCS constructor takes (_slices_pixel is reversed)
        slices = [s if isinstance(s, int) else [s.start, s.stop, s.step] for s in wcs._slices_array]
        return {"kind": "sliced", "wcs": _wcs_record(wcs._wcs), "slices": slices}
    if isinstance(wcs, CompoundLowLevelWCS):
        return {"kind": "compound", "parts": [_wcs_record(w) for w in wcs._wcs], "mapping": [int(m) for m in wcs.mapping.mapping]}
    raise GlueSerializeError(f"Cannot save a {type(wcs).__name__} in a session")


def _wcs_from_record(rec):
    kind = rec["kind"]
    if kind == "asdf":
        with asdf.open(io.BytesIO(base64.b64decode(rec["b64"])), lazy_load=False, memmap=False) as af:
            return af["wcs"]
    if kind == "sliced":
        slices = [s if isinstance(s, int) else slice(*s) for s in rec["slices"]]
        return SlicedLowLevelWCS(_wcs_from_record(rec["wcs"]), slices)
    if kind == "compound":
        return CompoundLowLevelWCS(*map(_wcs_from_record, rec["parts"]), mapping=rec["mapping"])
    header = fits.Header.fromstring(rec["header"])
    if kind == "fits-tab":
        wcs = WCS(header, fits.open(io.BytesIO(base64.b64decode(rec["table"]))))
    else:
        wcs = WCS(header)
    if rec.get("shape"):
        wcs.pixel_shape = tuple(rec["shape"])  # to_header drops NAXISn; the -TAB rebuild needs it on a re-save
    return wcs


# methods of _GlueWCS (glue checks __gluestate__ before its saver registry, state.py:378)
def __gluestate__(self, context):
    return {"wcs": _wcs_record(self._wcs)}


@classmethod
def __setgluestate__(cls, rec, context):
    return cls(_wcs_from_record(rec["wcs"]))


@saver(u.Quantity)
def _save_quantity(quantity, context):
    # glue-core routes Quantity to its ndarray saver, and np.save raises on it
    return {"value": context.do(np.asarray(quantity.value)), "unit": quantity.unit.to_string()}


@loader(u.Quantity)
def _load_quantity(rec, context):
    return u.Quantity(context.object(rec["value"]), rec["unit"])


class SolarVisualAttributes(VisualAttributes):
    """Style whose preferred colormap survives a session (glue-core writes the Colormap object, which is not JSON)."""

    def __gluestate__(self, context):
        atts = {name: getattr(self, name) for name in self.DEFAULT_ATTS}
        atts["preferred_cmap"] = getattr(atts["preferred_cmap"], "name", atts["preferred_cmap"])
        return atts

    @classmethod
    def __setgluestate__(cls, rec, context):
        atts = {name: rec[name] for name in cls.DEFAULT_ATTS}
        try:
            return cls(**atts)
        except ValueError:  # colormap name unknown in this environment; keep the rest of the style
            return cls(**{**atts, "preferred_cmap": None})


def read_iris_rasters(path, files=None, windows=None, stack=False):
    """
    Data-factory form of `raster_data` so `load_data` can log how to re-read the files.

    ``path`` is the first raster file; ``files`` lists every raster file of the observation
    relative to its folder (so a session saved with relative paths can move with the data).
    """
    folder = os.path.dirname(path)
    files = [path] if files is None else [os.path.join(folder, name) for name in files]
    return L.raster_data(files, windows, stack)


# ---------------------------------------------------------------- apply to the installed package
L._GlueWCS.__gluestate__ = __gluestate__
L._GlueWCS.__setgluestate__ = __setgluestate__
L.VisualAttributes = SolarVisualAttributes  # _cube_data builds data.style from this name
M.VisualAttributes = SolarVisualAttributes  # _parse_sunpy_map likewise
