"""One link graph for D1 (link_hpc) + #2595 WCS autolinks + WP4 time links? Designs x 6 orders x checks (a)-(e)."""
import itertools
import json
import os
import warnings

import numpy as np
from irispy.data.test import get_test_data_filenames

from glue.core import DataCollection
from glue.core.component_link import ComponentLink
from glue.core.exceptions import IncompatibleAttribute, IncompatibleDataException
from glue.core.fixed_resolution_buffer import compute_fixed_resolution_buffer
from glue.core.link_manager import discover_links
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_solar.sources.loaders.iris import image_data, raster_data, link_hpc

import wp4_common as w

warnings.simplefilter("ignore")
FS = list(get_test_data_filenames())
PICK = lambda n: next(str(f) for f in FS if f.name.replace("_test.fits", ".fits") == n and f.parent.name == "sns")
SJI = PICK("iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
RAS = PICK("iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")
OUT = os.environ.get("LINKGRAPH_OUT", "linkgraph.json")


def pair():
    return image_data(SJI), raster_data([RAS], ["Si IV 1403"])[0]


# ------------------------------------------------------------------ link sets
def add_wcs(dc, sji, ras):
    dc.add_link(wcs_autolink(dc))


def add_hpc(dc, sji, ras):
    dc.add_link(link_hpc(dc))


def add_time_plan(dc, sji, ras):  # WP4 prototype: identity links onto pixel component IDs
    w.link_time(dc, sji, ras)


def add_time_index(dc, sji, ras):  # design B: same nearest indices, linked to plain index components (no pixel CID)
    near = w.nearest(sji["Time"][:, 0, 0], ras["Time"][:, 0, 0])
    back = w.nearest(ras["Time"][:, 0, 0], sji["Time"][:, 0, 0])
    col = lambda a, d: np.broadcast_to(np.asarray(a, dtype=np.int32).reshape(-1, 1, 1), d.shape)
    sji.add_component(col(near, sji), f"Nearest exposure: {ras.label}")
    sji.add_component(col(np.arange(sji.shape[0]), sji), "Frame index")
    ras.add_component(col(back, ras), f"Nearest frame: {sji.label}")
    ras.add_component(col(np.arange(ras.shape[0]), ras), "Exposure index")
    dc.add_link([ComponentLink([sji.id[f"Nearest exposure: {ras.label}"]], ras.id["Exposure index"]),
                 ComponentLink([ras.id[f"Nearest frame: {sji.label}"]], sji.id["Frame index"])])


def add_hpc_tworld(dc, sji, ras):
    add_hpc(dc, sji, ras)
    add_tworld(dc, sji, ras)


def add_none(dc, sji, ras):  # design C: no time links; sync reads the Time components directly
    pass


def add_tworld(dc, sji, ras):  # D1 archive's time-aware world link: raster Time -> SJI world time (seconds)
    t = sji["Time"][:, 0, 0]
    tw = float(sji.coords.pixel_to_world_values(0., 0., 0.)[2])
    ref = t[0] - np.timedelta64(int(round(tw * 1e9)), "ns")
    tcid = next(c for c in sji.world_component_ids if c.label.startswith("Time"))
    dc.add_link(ComponentLink([ras.id["Time"]], tcid, using=lambda x: (x - ref) / np.timedelta64(1, "s")))


# sync readers: SJI frame f -> raster step, raster step s -> SJI frame
def sync_pixel(sji, ras, f, pt):  # what wp4_common.sync_slices evaluates (wp4_common.py:126)
    return sji[ras.pixel_component_ids[0], (np.array([f]),) + tuple(np.array([p]) for p in pt)][0]


def back_pixel(sji, ras, s, pt):
    return ras[sji.pixel_component_ids[0], (np.array([s]),) + tuple(np.array([p]) for p in pt)][0]


def sync_index(sji, ras, f, pt):
    return sji[ras.id["Exposure index"], (np.array([f]),) + tuple(np.array([p]) for p in pt)][0]


def back_index(sji, ras, s, pt):
    return ras[sji.id["Frame index"], (np.array([s]),) + tuple(np.array([p]) for p in pt)][0]


def sync_time(sji, ras, f, pt):  # message/callback-driven: nearest() over Time components, no links
    return w.nearest(sji["Time"][f:f + 1, 0, 0], ras["Time"][:, 0, 0])[0]


def back_time(sji, ras, s, pt):
    return w.nearest(ras["Time"][s:s + 1, 0, 0], sji["Time"][:, 0, 0])[0]


DESIGNS = {
    "P plan (wcs+hpc+pixel time links)": ({"wcs": add_wcs, "hpc": add_hpc, "time": add_time_plan}, sync_pixel, back_pixel),
    "B index components (wcs+hpc+index links)": ({"wcs": add_wcs, "hpc": add_hpc, "time": add_time_index}, sync_index, back_index),
    "C no time links (wcs+hpc, sync from Time)": ({"wcs": add_wcs, "hpc": add_hpc, "time": add_none}, sync_time, back_time),
    "F plan+D1 world time (wcs+hpc&tworld+index)": ({"wcs": add_wcs, "hpc": add_hpc_tworld, "time": add_time_index}, sync_index, back_index),
    "E no WCSLink (hpc+tworld+index links)": ({"tworld": add_tworld, "hpc": add_hpc, "time": add_time_index}, sync_index, back_index),
}


# ------------------------------------------------------------------ checks
def hp(d):
    types = list(d.coords.world_axis_physical_types)[::-1]
    return {t: c for t, c in zip(types, d.world_component_ids) if t and t.startswith("custom:pos.helioprojective.")}


def roi(d, xa, ya, x0, x1, y0, y1):
    p = d.pixel_component_ids
    return RoiSubsetState(xatt=p[xa], yatt=p[ya], roi=RectangularROI(x0, x1, y0, y1))


def safe(fn):
    try:
        return fn()
    except (IncompatibleAttribute, IncompatibleDataException) as e:
        return f"{type(e).__name__}"
    except Exception as e:  # noqa: BLE001
        return f"ERROR {type(e).__name__}: {str(e)[:60]}"


def check_a(sji, ras):
    st = PixelSubsetState(sji, [slice(None), slice(25, 26), slice(25, 26)])
    xy = safe(lambda: tuple(int(v) for v in st.get_xy(ras, 1, 0)))
    spec = safe(lambda: np.shape(st.to_array(ras, ras.main_components[0])))
    return {"xy": xy, "spec": spec}


RAS_STEPS = [100, 180]  # replaced by the steps the wcs+hpc baseline reaches


def check_b(sji, ras):
    ny, nx = sji.shape[1:]
    out = {}
    for key, fn in (("sji_full->ras", lambda: ras.get_mask(roi(sji, 2, 1, -0.5, nx - 0.5, -0.5, ny - 0.5))),
                    ("sji_rect->ras", lambda: ras.get_mask(roi(sji, 2, 1, 10, 30, 10, 30))),
                    ("ras_map->sji", lambda: sji.get_mask(roi(ras, 0, 1, RAS_STEPS[0], RAS_STEPS[1], 10, 20)))):
        out[key] = safe(fn)
    return out


def check_c(sji, ras, fwd, back):
    near = w.nearest(sji["Time"][:, 0, 0], ras["Time"][:, 0, 0])
    far = w.nearest(ras["Time"][:, 0, 0], sji["Time"][:, 0, 0])
    bad_f = bad_b = 0
    errs = set()
    for f in range(sji.shape[0]):
        for pt in ((0, 0), (25, 25)):
            got = safe(lambda: fwd(sji, ras, f, pt))
            if isinstance(got, str):
                errs.add(got)
                bad_f += 1
            elif not np.isfinite(got) or int(round(float(got))) != near[f]:
                bad_f += 1
    for s in range(ras.shape[0]):
        for pt in ((0, 0), (20, 3)):
            got = safe(lambda: back(sji, ras, s, pt))
            if isinstance(got, str):
                errs.add(got)
                bad_b += 1
            elif not np.isfinite(got) or int(round(float(got))) != far[s]:
                bad_b += 1
    return {"fwd_bad": bad_f, "fwd_n": 2 * sji.shape[0], "back_bad": bad_b, "back_n": 2 * ras.shape[0], "errs": sorted(errs)}


def check_d(sji, ras, ref_sji, ref_ras):
    hs, hr, out = hp(sji), hp(ras), {}
    for t in hs:
        short = t.split(".")[-1]
        out[f"sji[ras {short}]==sji {short}"] = safe(lambda: bool(np.allclose(sji[hr[t]], sji[hs[t]], equal_nan=True)))
        out[f"ras[sji {short}]==ras {short}"] = safe(lambda: bool(np.allclose(ras[hs[t]], ras[hr[t]], equal_nan=True)))
    out["own world unchanged"] = all(np.array_equal(d[c], r[c2], equal_nan=True)
                                     for d, r in ((sji, ref_sji), (ras, ref_ras))
                                     for c, c2 in zip(d.world_component_ids, r.world_component_ids))
    return out


def check_e(sji, ras):
    nf, ny, nx = sji.shape
    ns, nsl, nw = ras.shape
    sji_on_ras = safe(lambda: compute_fixed_resolution_buffer(sji, [(0, ns - 1, ns), (0, nsl - 1, nsl), nw // 2], target_data=ras,
                                                              target_cid=sji.main_components[0], broadcast=False).shape)
    ras_on_sji = safe(lambda: compute_fixed_resolution_buffer(ras, [nf // 2, (0, ny - 1, ny), (0, nx - 1, nx)], target_data=sji,
                                                              target_cid=ras.main_components[0], broadcast=False).shape)
    return {"sji layer in raster viewer": sji_on_ras, "raster layer in SJI viewer": ras_on_sji}


def winner(data, cid):
    link = data._get_external_link(cid)
    if link is None:
        return "none"
    return ("identity " if link.identity else type(link).__name__ + " ") + ",".join(c.label for c in link.get_from_ids())


def summarise(v):
    if isinstance(v, np.ndarray):
        return {"sum": int(v.sum()), "lead_hit": int(v.any(axis=(1, 2)).sum())}
    return v


# ------------------------------------------------------------------ baseline + matrix
def run_design(name, slots, fwd, back, base, ref_sji, ref_ras):
    rows = []
    for order in itertools.permutations(slots):
        sji, ras = pair()
        dc = DataCollection([sji, ras])
        for s in order:
            slots[s](dc, sji, ras)
        a, b, c = check_a(sji, ras), check_b(sji, ras), check_c(sji, ras, fwd, back)
        d, e = check_d(sji, ras, ref_sji, ref_ras), check_e(sji, ras)
        a_ok = not isinstance(a["xy"], str) and not isinstance(a["spec"], str) and a["spec"][-1] == ras.shape[-1] and \
            all(abs(p - q) <= 1 for p, q in zip(a["xy"], base["a"]["xy"]))
        b_ok = all(isinstance(v, np.ndarray) and v.any() for v in b.values())
        b_same = b_ok and all(np.array_equal(b[k], base["b"][k]) for k in b)
        c_ok = c["fwd_bad"] == 0 and c["back_bad"] == 0
        d_ok = all(v is True for v in d.values())
        e_ok = not any(isinstance(v, str) and v.startswith("ERROR") for v in e.values())
        row = {"design": name, "order": ",".join(order),
               "a": a_ok, "b": b_ok, "b_equals_wcs_hpc": b_same, "c": c_ok, "d": d_ok, "e": e_ok,
               "win sji<-ras.pix0": winner(sji, ras.pixel_component_ids[0]),
               "win ras<-sji.pix0": winner(ras, sji.pixel_component_ids[0]),
               "win sji<-ras.lon": winner(sji, list(hp(ras).values())[0]),
               "detail": {"a": a, "b": {k: summarise(v) for k, v in b.items()}, "c": c, "d": d, "e": e}}
        rows.append(row)
        print(f"{name:45s} {row['order']:18s} a={a_ok!s:5} b={b_ok!s:5}(=base {b_same!s:5}) c={c_ok!s:5} d={d_ok!s:5} e={e_ok!s:5} "
              f"| sji<-ras.pix0: {row['win sji<-ras.pix0'][:40]} | ras<-sji.pix0: {row['win ras<-sji.pix0'][:40]} "
              f"| a={a} | c fwd {c['fwd_bad']}/{c['fwd_n']} back {c['back_bad']}/{c['back_n']} {c['errs']} "
              f"| b={ {k: summarise(v) for k, v in b.items()} } | e={e}", flush=True)
    return rows


def test_matrix():
    ref_sji, ref_ras = pair()
    print(f"\nfiles {SJI} {RAS}\nSJI shape {ref_sji.shape} raster shape {ref_ras.shape}")
    sji, ras = pair()
    dc = DataCollection([sji, ras])
    add_wcs(dc, sji, ras)
    add_hpc(dc, sji, ras)
    print("external links on this core:", [type(l).__name__ for l in dc.external_links])
    full = check_b(sji, ras)["sji_full->ras"]
    if isinstance(full, np.ndarray):
        hit = np.nonzero(full.any(axis=(1, 2)))[0]
        RAS_STEPS[:] = [int(hit.min()), int(hit.max())]
    print("raster ROI steps", RAS_STEPS, "slit 10-20 (inside the baseline footprint)")
    base = {"a": check_a(sji, ras), "b": check_b(sji, ras)}
    print("baseline wcs+hpc: a", base["a"], "b", {k: summarise(v) for k, v in base["b"].items()},
          "| win sji<-ras.pix0", winner(sji, ras.pixel_component_ids[0]), "| win sji<-ras.lon", winner(sji, list(hp(ras).values())[0]),
          "| win ras<-sji.pix1", winner(ras, sji.pixel_component_ids[1]))
    rows = []
    for name, (slots, fwd, back) in DESIGNS.items():
        rows += run_design(name, slots, fwd, back, base, ref_sji, ref_ras)
    with open(OUT, "w") as fh:
        json.dump(rows, fh, indent=1, default=str)


def test_tie_rule_is_iteration_order():
    """Same links, two list orders: discover_links picks the first accessible link at equal depth."""
    sji, ras = pair()
    dc = DataCollection([sji, ras])
    add_wcs(dc, sji, ras)
    add_hpc(dc, sji, ras)
    add_time_plan(dc, sji, ras)
    links = list(dc._link_manager._links | dc._link_manager._inverse_links)
    target = ras.pixel_component_ids[0]
    cand = [l for l in links if l.get_to_id() is target]
    print("\ncandidates for sji<-raster pixel0:", [("identity" if l.identity else type(l).__name__, [c.label for c in l.get_from_ids()]) for l in cand])
    for label, key in (("time first", lambda l: not l.identity), ("wcs first", lambda l: l.identity)):
        found = discover_links(sji, sorted(links, key=key))[target]
        print(f"{label}: winner", "identity" if found.identity else type(found).__name__, [c.label for c in found.get_from_ids()])
    print("ComponentLink uses object.__hash__:", type(cand[0]).__hash__ is object.__hash__,
          "| LinkManager passes a", type(dc._link_manager._links | dc._link_manager._inverse_links).__name__)
    wins = []
    for _ in range(6):
        sji, ras = pair()
        dc = DataCollection([sji, ras])
        junk = [object() for _ in range(np.random.randint(1, 5000))]  # perturb allocation only
        add_time_plan(dc, sji, ras)
        add_wcs(dc, sji, ras)
        add_hpc(dc, sji, ras)
        wins.append(winner(sji, ras.pixel_component_ids[0]).split()[0])
        del junk
    print("fixed add order time,wcs,hpc with perturbed allocation -> winners:", wins)


def test_qt_overlay(qtbot):
    """P graph: drag the SJI into the raster map viewer; does the uncaught translate_pixel Exception reach the user?"""
    from glue_qt.app import GlueApplication
    from glue_qt.viewers.image import ImageViewer
    for name, slots in (("P", DESIGNS["P plan (wcs+hpc+pixel time links)"][0]), ("B", DESIGNS["B index components (wcs+hpc+index links)"][0])):
        sji, ras = pair()
        dc = DataCollection([sji, ras])
        for s in ("wcs", "hpc", "time"):
            slots[s](dc, sji, ras)
        app = GlueApplication(dc)
        qtbot.addWidget(app)
        viewer = app.new_data_viewer(ImageViewer, data=ras)
        viewer.state.x_att, viewer.state.y_att = ras.pixel_component_ids[0], ras.pixel_component_ids[1]
        try:
            viewer.add_data(sji)
            viewer.state.layers[-1].visible = True
            viewer.axes.figure.canvas.draw()
            arts = [(type(a.layer).__name__, a.enabled, a.disabled_message[:60] if not a.enabled else "") for a in viewer.layers]
            print(f"\n{name}: add SJI to raster viewer -> ok; layer artists {arts}")
        except Exception as e:  # noqa: BLE001
            print(f"\n{name}: add SJI to raster viewer -> {type(e).__name__}: {str(e)[:90]}")
        app.close()


def test_d_needs_hpc():
    """Is link_hpc what keeps cross-dataset world readouts/subsets working next to WCSLink?"""
    ref_sji, ref_ras = pair()
    for name, steps in (("wcs only", (add_wcs,)), ("wcs+hpc", (add_wcs, add_hpc)), ("hpc only", (add_hpc,))):
        sji, ras = pair()
        dc = DataCollection([sji, ras])
        for s in steps:
            s(dc, sji, ras)
        print(f"\n{name}: d={check_d(sji, ras, ref_sji, ref_ras)} a={check_a(sji, ras)}")
