"""Re-verify glue-core faults on the installed release or on a main clone: python -I probes.py release|main."""
import os
import sys
import tempfile
import traceback

S = "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/df774a44-db13-4c72-b097-0d85fb986df9/scratchpad/upstream/glue-core"
MODE = sys.argv[1]
if MODE == "main":
    sys.path.insert(0, os.path.join(S, "glue-main"))
sys.path.insert(0, os.path.join(S, "gs"))

import matplotlib  # noqa: E402

SUNPY_CMAP_REGISTERED_AT_START = "sdoaia171" in matplotlib.colormaps  # before anything imports sunpy

import numpy as np  # noqa: E402
import dask.array as da  # noqa: E402
import astropy.units as u  # noqa: E402
from astropy.io import fits  # noqa: E402
from astropy.wcs import WCS  # noqa: E402
import glue  # noqa: E402
from glue.core import Data, DataCollection  # noqa: E402
from glue.core.component import DerivedComponent  # noqa: E402
from glue.core.component_link import ComponentLink  # noqa: E402
from glue.core.link_helpers import LinkSameWithUnits  # noqa: E402
from glue.core.state import GlueSerializeError, GlueSerializer, GlueUnSerializer  # noqa: E402
from glue.core.subset import SliceSubsetState, RangeSubsetState  # noqa: E402
from glue.config import data_exporter  # noqa: E402

print("glue from", glue.__file__, "version", glue.__version__)
results = {}


def probe(name):
    def deco(f):
        try:
            results[name] = f()
        except Exception as e:  # noqa: BLE001
            results[name] = f"ERROR {type(e).__name__}: {str(e)[:160]}"
            if os.environ.get("PROBE_TRACE"):
                traceback.print_exc()
        return f
    return deco


TMP = tempfile.mkdtemp(dir=S)


# ---- session savers --------------------------------------------------------
@probe("quantity_saver_missing (wp0-core-quantity-saver)")
def _():
    return u.Quantity not in GlueSerializer.dispatch


@probe("meta_quantity_save_fails (#2597; array and scalar Quantity in Data.meta)")
def _():
    out = {}
    for key, value in (("array", [1.0, 2.0] * u.s), ("scalar", 1.0 * u.s)):
        d = Data(x=np.arange(3.0), label="d")
        d.meta[key] = value
        try:
            rec = GlueSerializer(DataCollection([d])).dumps()
            d2 = GlueUnSerializer.loads(rec).object("__main__")[0]
            out[key] = f"saved; meta restored as {type(d2.meta.get(key)).__name__}: {d2.meta.get(key)!r}"
        except Exception as e:  # noqa: BLE001
            out[key] = f"{type(e).__name__}: {str(e)[:80]}"
    return out


@probe("meta_object_array (wp0-core-session-reports)")
def _():
    d = Data(x=np.arange(3.0), label="d")
    d.meta["obj"] = np.array([None, "a"], dtype=object)
    try:
        rec = GlueSerializer(DataCollection([d])).dumps()
    except Exception as e:  # noqa: BLE001
        return f"save {type(e).__name__}: {str(e)[:80]}"
    try:
        d2 = GlueUnSerializer.loads(rec).object("__main__")[0]
        return f"round trip ok, meta={d2.meta.get('obj')!r}"
    except Exception as e:  # noqa: BLE001
        return f"load {type(e).__name__}: {str(e)[:80]}"


@probe("preferred_cmap_save_fails (#2597; maps._Style)")
def _():
    d = Data(x=np.arange(3.0), label="d")
    d.style.preferred_cmap = "viridis"
    try:
        GlueSerializer(DataCollection([d])).dumps()
        return False
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {str(e)[:80]}"


@probe("sunpy_cmap_name_not_in_registry_before_sunpy_import (_add_session_colormaps)")
def _():
    return not SUNPY_CMAP_REGISTERED_AT_START


@probe("link_same_with_units_session_fails (#205)")
def _():
    first, second = Data(x=np.zeros(1), label="first"), Data(y=np.zeros(1), label="second")
    collection = DataCollection([first, second])
    collection.add_link(LinkSameWithUnits(first.id["x"], second.id["y"]))
    try:
        GlueUnSerializer.loads(GlueSerializer(collection).dumps()).object("__main__")
    except GlueSerializeError as e:
        return f"GlueSerializeError: {str(e)[:60]}"
    return False


@probe("link_editor_fails_on_LinkSameWithUnits_and_PathRelativeLink (#245)")
def _():
    from glue.dialogs.link_editor.state import LinkEditorState
    from glue.plugins.tools.path_slicer.path_sliced_data import PathSlicedData
    from glue.plugins.tools.path_slicer.path_sliced_data_links import PathRelativeLink
    first, second = Data(x=np.zeros((2, 2)), label="first"), Data(y=np.zeros((2, 2)), label="second")
    paths = [PathSlicedData(d, d.pixel_component_ids[1], [0, 1], d.pixel_component_ids[0], [0, 1]) for d in (first, second)]
    collection = DataCollection([first, second, *paths])
    collection.add_link([LinkSameWithUnits(first.id["x"], second.id["y"]), PathRelativeLink(*paths)])
    try:
        for _ in range(2):
            LinkEditorState(collection).update_links_in_collection()
    except (AttributeError, TypeError, ValueError) as e:
        return f"{type(e).__name__}: {str(e)[:80]}"
    return False


@probe("derived_component_units_lost (wp0-core-derived-units)")
def _():
    d = Data(x=np.arange(3.0), label="d")
    d.add_component(DerivedComponent(d, d.id["x"] * 2, units="DN/s"), "y")
    assert d.get_component(d.id["y"]).units == "DN/s"
    rec = GlueSerializer(DataCollection([d])).dumps()
    d2 = GlueUnSerializer.loads(rec).object("__main__")[0]
    return repr(d2.get_component(d2.id["y"]).units)


@probe("image_layer_state_round_trip (stretch_global=False, stretch_parameters)")
def _():
    from glue.viewers.image.state import ImageViewerState, ImageLayerState
    out = {}
    for stretch_global in (True, False):
        d = Data(x=np.arange(12.0).reshape(3, 4), label="d")
        vs = ImageViewerState()
        ls = ImageLayerState(layer=d, viewer_state=vs)
        vs.layers.append(ls)
        ls.stretch = "log"
        ls.stretch_parameters = {"a": 123.0}
        ls.stretch_global = stretch_global
        ls.v_min, ls.v_max = 1.0, 5.0
        names = [n for n in ls.callback_properties() if n not in ("layer", "viewer_state")]
        before = {n: repr(getattr(ls, n)) for n in names}
        rec = GlueSerializer(vs).dumps()
        try:
            ls2 = GlueUnSerializer.loads(rec).object("__main__").layers[0]
        except Exception as e:  # noqa: BLE001
            out[f"stretch_global={stretch_global}"] = f"restore {type(e).__name__}: {str(e)[:60]}"
            continue
        after = {n: repr(getattr(ls2, n)) for n in names}
        out[f"stretch_global={stretch_global}"] = {n: (before[n], after[n]) for n in names if before[n] != after[n]} or "all restored"
    return out


@probe("tab_wcs_session_fails (_save_wcs/_load_wcs, SST5)")
def _():
    coords = np.array([(np.linspace(500.0, 600.0, 10).reshape(10, 1),)], dtype=[("COORDS", float, (10, 1))])
    table = fits.BinTableHDU(coords, name="WCS-TAB")
    header = fits.Header({"CTYPE1": "WAVE-TAB", "CUNIT1": "nm", "PS1_0": "WCS-TAB", "PS1_1": "COORDS", "NAXIS": 1, "NAXIS1": 10})
    hdul = fits.HDUList([fits.PrimaryHDU(np.zeros(10), header=header), table])
    wcs = WCS(hdul[0].header, fobj=hdul)
    assert np.allclose(wcs.pixel_to_world_values(9), 600.0)
    from glue.core.state import _save_wcs, _load_wcs
    try:
        _load_wcs(_save_wcs(wcs, None), None)
        return False
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {str(e)[:80]}"


# ---- exporters and importers ----------------------------------------------
@probe("exporters_on_datetime64 (wp0-core-datetime-export)")
def _():
    import glue.core.data_exporters.gridded_fits  # noqa: F401 - registers the exporters, as glue's plugin loading does
    import glue.core.data_exporters.hdf5  # noqa: F401
    import glue.core.data_exporters.astropy_table  # noqa: F401
    d = Data(t=np.array(["2021-01-01T00:00:00", "2021-01-01T00:00:01"], dtype="datetime64[ns]"), x=[1.0, 2.0], label="d")
    out = {}
    for exporter in data_exporter.members:
        path = os.path.join(TMP, "dt." + exporter.extension[0])
        try:
            exporter.function(path, d)
            if exporter.label.startswith("Comma"):
                with open(path) as f:
                    out[exporter.label] = "writes: " + f.read().replace("\n", " | ")[:120]
            else:
                out[exporter.label] = "ok"
        except Exception as e:  # noqa: BLE001
            out[exporter.label] = f"{type(e).__name__}: {str(e)[:70]}"
    return out


@probe("fits_exporter_uint8_subset (export_fits)")
def _():
    from glue.core.data_exporters.gridded_fits import fits_writer
    d = Data(m=np.zeros((2, 2), np.uint8), label="d")
    s = d.new_subset()
    try:
        fits_writer(os.path.join(TMP, "u8.fits"), s)
        return False
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {str(e)[:80]}"


@probe("fits_subset_mask_importer_refuses_uint8")
def _():
    from glue.io.formats.fits.subset_mask import fits_subset_mask_importer
    path = os.path.join(TMP, "mask.fits")
    fits.writeto(path, np.ones((2, 2), np.uint8), overwrite=True)
    try:
        fits_subset_mask_importer(path)
        return False
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {str(e)[:80]}"


# ---- statistics ---------------------------------------------------------------
@probe("compute_statistic_slice_state_not_padded (#183)")
def _():
    d = Data(x=np.random.random((3, 4, 6)), label="d")
    band = SliceSubsetState(d, [slice(None), slice(None), slice(2, 4)])
    by_slice = d.compute_statistic("mean", d.id["x"], axis=(0, 1), subset_state=band)
    same = RangeSubsetState(2, 3, d.pixel_component_ids[2])  # inclusive range: pixels 2 and 3
    by_range = d.compute_statistic("mean", d.id["x"], axis=(0, 1), subset_state=same)
    return f"SliceSubsetState gives {by_slice.shape} values along a {d.shape[2]}-long axis; RangeSubsetState gives {by_range.shape} ({np.isnan(by_range).sum()} NaN-padded)"


@probe("random_views_for_dask_array_only_chunk_corners (#2413, PR #2605)")
def _():
    from glue.utils import random_views_for_dask_array
    arr = da.zeros((100, 100), chunks=50)
    views = random_views_for_dask_array(arr, 400, n_chunks=10)
    starts = [(v[0].start, v[1].start) for v in views]
    sizes = [(v[0].stop - v[0].start, v[1].stop - v[1].start) for v in views]
    return f"starts {sorted(set(starts))}, view sizes {sorted(set(sizes))}; all at chunk corners: {all(s % 50 == 0 for st in starts for s in st)}"


@probe("set_constraint_None_does_not_clear (fitters.set_constraint)")
def _():
    from glue.core.fitters import PolynomialFitter
    f = PolynomialFitter()
    f.set_constraint("c0", value=1.0, fixed=True)
    f.set_constraint("c0", value=None, fixed=None)
    return f._constraints["c0"]


# ---- path slicer ---------------------------------------------------------------
@probe("path_sliced_data_no_saver_and_dc_saver_calls_component_ids")
def _():
    from glue.plugins.tools.path_slicer.path_sliced_data import PathSlicedData
    d = Data(x=np.random.random((3, 4, 5)), label="d")
    p = PathSlicedData(d, d.pixel_component_ids[2], [0.0, 2.0], d.pixel_component_ids[1], [0.0, 2.0])
    out = {"PathSlicedData saver registered": PathSlicedData in GlueSerializer.dispatch,
           "has component_ids": hasattr(p, "component_ids")}
    try:
        GlueSerializer(DataCollection([d, p])).dumps()
        out["dc save"] = "ok"
    except Exception as e:  # noqa: BLE001
        out["dc save"] = f"{type(e).__name__}: {str(e)[:80]}"
    return out


@probe("path_sliced_data_off_data_and_time (0 off the data; Time cast to float; one pixel shape)")
def _():
    from glue.plugins.tools.path_slicer.path_sliced_data import PathSlicedData
    t = (np.datetime64("2021-01-01T00:00:00") + np.arange(60).astype("timedelta64[s]")).reshape(3, 4, 5)
    d = Data(x=np.ones((3, 4, 5)), t=t, label="d")
    off = PathSlicedData(d, d.pixel_component_ids[2], [10.0, 12.0], d.pixel_component_ids[1], [10.0, 12.0])
    one = PathSlicedData(d, d.pixel_component_ids[2], [1.0, 2.0], d.pixel_component_ids[1], [1.0, 1.0])  # one spacing long
    return {
        "x off the data": repr(np.asarray(off[d.id["x"]]).ravel()[:4]),
        "t kind": f"{d.get_kind(d.id['t'])} -> diagram dtype {np.asarray(off[d.id['t']]).dtype}",
        "one pixel shape": one.shape,
    }


@probe("path_sliced_coordinates_axis_label_IndexError (correlated world axes)")
def _():
    from glue.plugins.tools.path_slicer.path_sliced_data import PathSlicedData
    from glue.core.coordinate_helpers import axis_label
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = ["HPLN-TAN", "HPLT-TAN", "UTC"]
    wcs.wcs.cunit = ["arcsec", "arcsec", "s"]
    wcs.wcs.pc = [[1, 0, 0.1], [0, 1, 0], [0, 0, 1]]  # pointing moves with time, as an SJI's
    d = Data(x=np.ones((3, 4, 5)), coords=wcs, label="sji")
    p = PathSlicedData(d, d.pixel_component_ids[2], [0.0, 2.0], d.pixel_component_ids[1], [0.0, 2.0])
    c = p.coords
    out = {"pixel_n_dim": c.pixel_n_dim, "world_n_dim": c.world_n_dim}
    for axis in range(p.ndim):
        try:
            out[f"axis_label({axis})"] = axis_label(c, axis)
        except Exception as e:  # noqa: BLE001
            out[f"axis_label({axis})"] = f"{type(e).__name__}"
    return out


@probe("drive_parent_slice_truncates_and_no_clamp (code: common.py int(slice_y))")
def _():
    import inspect
    from glue.plugins.tools.path_slicer import common
    src = inspect.getsource(common.drive_parent_slice)
    return {"int(": "int(slice_y)" in src, "clip/round": any(k in src for k in ("clip", "round"))}


# ---- labels and links ----------------------------------------------------------
@probe("axis_label_indexing_bug (#227: world_axis_names[axis] checked, [n-1-axis] returned)")
def _():
    from glue.core.coordinate_helpers import axis_label
    wcs = WCS(naxis=5)
    wcs.wcs.ctype = ["HPLN-TAN", "HPLT-TAN", "WAVE", "UTC", "STOKES"]
    wcs.wcs.cname = ["HPLN", "HPLT", "WAVE", "UTC", ""]  # no CNAME for Stokes, as an SSTRED cube
    return {axis: axis_label(wcs, axis) for axis in range(5)}  # numpy axis 0 is Stokes


@probe("wcslink_shared_lists (wp0-core-wcslink-lists)")
def _():
    from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink, IncompatibleWCS

    class NoCelestial(WCS):  # as glue-solar's _TabularWCS (has_celestial = False against a wcslib crash)
        has_celestial = False

    def cube(ctypes):
        w = NoCelestial(naxis=len(ctypes))
        w.wcs.ctype = ctypes
        return Data(x=np.zeros((2,) * len(ctypes)), coords=w, label="cube%d" % len(ctypes))

    def image():
        w = WCS(naxis=2)
        w.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]
        return Data(y=np.zeros((2, 2)), coords=w, label="map")

    out = {}
    for label, pair in (("map after 5-axis cube", (cube(["HPLN-TAN", "HPLT-TAN", "WAVE", "UTC", "STOKES"]), image())),
                        ("4-axis cube after 5-axis cube", (cube(["HPLN-TAN", "HPLT-TAN", "WAVE", "UTC", "STOKES"]), cube(["HPLN-TAN", "HPLT-TAN", "WAVE", "UTC"])))):
        try:
            WCSLink(*pair)
            out[label] = "linked"
        except IncompatibleWCS as e:
            out[label] = f"IncompatibleWCS (expected): {str(e)[:50]}"
        except Exception as e:  # noqa: BLE001
            out[label] = f"{type(e).__name__}: {str(e)[:80]}"
    return out


@probe("profile_x_label_without_display_unit (D90 axis-unit labels)")
def _():
    from glue.core import Session
    from glue.viewers.profile.viewer import SimpleProfileViewer
    wcs = WCS(naxis=1)
    wcs.wcs.ctype = ["WAVE"]
    wcs.wcs.cunit = ["Angstrom"]
    d = Data(x=np.arange(5.0), coords=wcs, label="spec")
    dc = DataCollection([d])
    v = SimpleProfileViewer(Session(data_collection=dc))
    v.add_data(d)
    v.state.x_display_unit = "nm"
    v.state.y_display_unit = None
    return {"x_axislabel": v.state.x_axislabel, "y_axislabel": v.state.y_axislabel, "x_display_unit": v.state.x_display_unit}


# ---- the glue_patches probes (each tests glue's original) ---------------------
import glue_solar.glue_patches as gp  # noqa: E402

for name in ("needs_inverse_workaround", "needs_fits_export_dask_workaround", "needs_pixel_point_workaround",
             "needs_redo_workaround", "needs_crosshair_workaround", "needs_reference_crosshair_workaround",
             "needs_axis_label_workaround", "needs_date_epoch_workaround", "needs_empty_collapse_workaround",
             "needs_derived_datetime_workaround", "needs_profile_restore_workaround"):
    probe("glue_patches." + name)(getattr(gp, name))

for name, value in results.items():
    print(f"{name}: {value}")
