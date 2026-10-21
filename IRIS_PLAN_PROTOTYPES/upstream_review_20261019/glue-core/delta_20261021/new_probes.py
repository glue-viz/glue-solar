"""The delta's new glue-core items: python -I new_probes.py release|main|g7 (no glue_solar import)."""
import os
import sys
from types import SimpleNamespace

S = "/tmp/claude-1000/-home-nabil-Git-glue-solar/69a1ec2a-a15b-4ef0-a5e7-b33024cca348/scratchpad/upstream-delta/glue-core"
MODE = sys.argv[1]
if MODE != "release":
    sys.path.insert(0, os.path.join(S, {"main": "glue", "g7": "glue-g7"}[MODE]))

import numpy as np  # noqa: E402
import dask.array as da  # noqa: E402
from astropy.modeling import models  # noqa: E402
from astropy.wcs import WCS  # noqa: E402
import glue  # noqa: E402
from glue.core import Data, DataCollection  # noqa: E402
from glue.core.application_base import Application  # noqa: E402
from glue.core.component import DaskComponent  # noqa: E402
from glue.core.link_helpers import LinkSame  # noqa: E402

print("glue from", glue.__file__)
results = {}


def probe(name):
    def deco(f):
        try:
            results[name] = f()
        except Exception as e:  # noqa: BLE001
            results[name] = f"ERROR {type(e).__name__}: {str(e)[:160]}"
        return f
    return deco


@probe("69 pixel_off_image (PixelSelectionTool._select_pixel at x=2 on a 2x2 image, then a linked dataset)")
def _():
    from glue.viewers.image.pixel_selection_mode import PixelSelectionTool
    a, b = Data(x=np.zeros((2, 2)), label="a"), Data(y=np.zeros((2, 2)), label="b")
    dc = DataCollection([a, b])
    for i in range(2):
        dc.add_link(LinkSame(a.pixel_component_ids[i], b.pixel_component_ids[i]))
    done = []
    state = SimpleNamespace(reference_data=a, x_att=a.pixel_component_ids[1], y_att=a.pixel_component_ids[0])
    viewer = SimpleNamespace(state=state, _data=dc, _session=SimpleNamespace(command_stack=SimpleNamespace(do=done.append)))
    PixelSelectionTool._select_pixel(SimpleNamespace(_pressed=True, _event_xdata=2.0, _event_ydata=0.0, viewer=viewer), None)
    out = {"subset made": bool(done), "slices": done[0].subset_state.slices if done else None}
    try:
        out["linked coords"] = done[0].subset_state._to_linked_pixel_coords(b)
    except Exception as e:  # noqa: BLE001
        out["linked coords"] = f"{type(e).__name__}: {e}"
    return out


@probe("70 update_slice_subset (stretch_global=False layer, its data removed from the collection)")
def _():
    from glue.viewers.image.viewer import SimpleImageViewer
    app = Application()
    a = Data(x=np.arange(24.0).reshape((2, 3, 4)), label="a")
    app.data_collection.append(a)
    viewer = app.new_data_viewer(SimpleImageViewer)
    viewer.add_data(a)
    viewer.state.layers[0].stretch_global = False
    try:
        app.data_collection.remove(a)
        removal = "ok"
    except Exception as e:  # noqa: BLE001
        removal = f"{type(e).__name__}: {e}"
    return {"removal": removal, "layers left": len(viewer.state.layers), "in collection": a in app.data_collection}


@probe("71 model_fitter_none_limit (GaussianFitter, stddev limits (None, 5))")
def _():
    from glue.core.fitters import GaussianFitter
    fitter = GaussianFitter()
    fitter.set_constraint("stddev", limits=(None, 5))
    x = np.linspace(-5, 5, 41)
    model, _ = fitter._get_model_fitter(x, np.exp(-x**2 / 2), None, fitter.constraints)
    return {"Gaussian1D.stddev.bounds": models.Gaussian1D.stddev.bounds, "fitted model's": model.stddev.bounds}


@probe("72 profile_vminmax (subset move: _calculate_profile calls, normalize off)")
def _():
    from unittest.mock import patch
    from glue.viewers.profile.viewer import SimpleProfileViewer
    data = Data(x=np.arange(24).reshape((4, 3, 2)), label="data")
    app = Application()
    app.data_collection.append(data)
    viewer = app.new_data_viewer(SimpleProfileViewer)
    viewer.add_data(data)
    group = app.data_collection.new_subset_group(subset_state=data.id["x"] < 20, label="subset")
    artist = viewer.layers[1]
    with patch.object(artist, "_calculate_profile", wraps=artist._calculate_profile) as calc:
        group.subset_state = data.id["x"] < 22
    return {"calls": calc.call_count, "v_max": artist.state.v_max}


@probe("73 path_roi_finalize (MplPathROI on Agg: two clicks, then finalize)")
def _():
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from glue.core.roi import MplPathROI
    fig = Figure()
    FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    roi = MplPathROI(ax)
    ev = [SimpleNamespace(xdata=x, ydata=y, inaxes=ax, key=None, x=0, y=0) for x, y in ((0.1, 0.1), (0.8, 0.6))]
    roi.start_selection(ev[0])
    roi.update_selection(ev[1])
    cached = roi._background_cache is not None
    try:
        roi.finalize_selection(ev[1])
        return {"background cached": cached, "finalize": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"background cached": cached, "finalize": f"{type(e).__name__}: {e}"}


def _drifting_cube(dask=False):
    """(time, y, x) cube whose longitude drifts with time, as an SST cube's pointing."""
    w = WCS(naxis=3)
    w.wcs.ctype = ["HPLN-TAN", "HPLT-TAN", "UTC"]
    w.wcs.cunit = ["arcsec", "arcsec", "s"]
    w.wcs.cdelt = [0.06, 0.06, 10]
    w.wcs.crpix = [1, 1, 1]
    w.wcs.pc = [[1, 0, 0.01], [0, 1, 0], [0, 0, 1]]
    w.wcs.set()
    values = np.arange(5 * 6 * 7, dtype=float).reshape((5, 6, 7))
    data = Data(coords=w, label="cube")
    data.add_component(DaskComponent(da.from_array(values, chunks=3)) if dask else values, "x")
    return data


@probe("19e path_coords_moving_pointing (PathSlicedData of a cube whose longitude drifts with time)")
def _():
    from glue.plugins.tools.path_slicer.path_sliced_data import PathSlicedData
    data = _drifting_cube()
    path = PathSlicedData(data, data.pixel_component_ids[2], np.array([0.0, 1, 2]), data.pixel_component_ids[1],
                          np.array([0.0, 1, 2]))
    out = {"pixel_n_dim": path.coords.pixel_n_dim, "world_n_dim": path.coords.world_n_dim}
    try:
        out["world components"] = [cid.label for cid in path.world_component_ids]
    except Exception as e:  # noqa: BLE001
        out["world components"] = f"{type(e).__name__}: {e}"
    return out


@probe("74 path_dask_component (PathSlicedData.get_data of a DaskComponent)")
def _():
    from glue.plugins.tools.path_slicer.path_sliced_data import PathSlicedData
    plain, lazy = _drifting_cube(), _drifting_cube(dask=True)
    out = {}
    for name, data in (("numpy", plain), ("DaskComponent", lazy)):
        path = PathSlicedData(data, data.pixel_component_ids[2], np.array([0.0, 1, 2]),
                              data.pixel_component_ids[1], np.array([0.0, 1, 2]))
        try:
            out[name] = path.get_data(data.id["x"]).shape
        except Exception as e:  # noqa: BLE001
            out[name] = f"{type(e).__name__}: {str(e)[:100]}"
    return out


for name, value in results.items():
    print(f"{name}: {value}")
