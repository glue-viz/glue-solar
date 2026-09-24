"""Offscreen check: three ways to overlay the raster slit on the SJI image viewer."""
import warnings; warnings.simplefilter("ignore")
import numpy as np
from glue.core import Data
from glue.core.link_helpers import LinkSame
from glue.core.application_base import Application
from glue.viewers.image.viewer import SimpleImageViewer
from irispy.data.test import get_test_data_filenames
from irispy.io import read_files
from glue_solar.sources.loaders.iris import image_data, raster_data

files = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in files if "sns/" in f and "SJI_1400" in f][0]
ras_paths = [f for f in files if "sns/" in f and "raster" in f]

sji = image_data(sji_path)
[ras] = raster_data(ras_paths, ["C II 1336"])
print("raster world cids:", [c.label for c in ras.world_component_ids], ras.coords.world_axis_units)
app = Application()
dc = app.data_collection
dc.append(sji); dc.append(ras)

# --- slit geometry from the raster -TAB WCS (glue Data world components, arcsec) ---
nstep, ny = ras.shape[0], ras.shape[1]
lon = ras[ras.world_component_ids[0]][:, :, 0]   # (step, slit) arcsec; glue lists world cids reversed: [lon, lat, wave]
lat = ras[ras.world_component_ids[1]][:, :, 0]
t_ras = ras["Time"][:, 0, 0]                       # datetime64 per step
cube = read_files(sji_path, memmap=False, uncertainty=False)
(t_sji,) = cube.axis_world_coords("time")
t_sji = t_sji.utc.to_value("datetime64")
t_world = sji[sji.world_component_ids[0]][:, 0, 0]  # SJI gWCS time world value (s) per frame
print("SJI world 'Time (Utc)' per frame (s):", t_world[:3], "...", t_world[-1])
nearest = np.array([np.abs(t_ras - t).argmin() for t in t_sji])   # raster step per SJI frame
print("nearest raster step per SJI frame:", nearest[:5], "...", nearest[-3:])

# ---------- A: scatter Data in SJI pixel coords (projected via the SJI gWCS), pixel-linked ----------
px, py = [], []
frames = np.repeat(np.arange(sji.shape[0]), ny)
for f, i in enumerate(nearest):
    x, y, _ = sji.coords.world_to_pixel_values(lon[i], lat[i], np.full(ny, t_world[f]))
    px.append(x); py.append(y)
slit_px = Data(label="slit-px", x=np.concatenate(px), y=np.concatenate(py), frame=frames)
dc.append(slit_px)
dc.add_link(LinkSame(slit_px.id["x"], sji.pixel_component_ids[2]))
dc.add_link(LinkSame(slit_px.id["y"], sji.pixel_component_ids[1]))
v = app.new_data_viewer(SimpleImageViewer, data=sji)
v.add_data(slit_px)
la = v.layers[1]
off = la.plot_artist.get_xydata() if hasattr(la, "plot_artist") else None
print("A pixel-linked scatter: enabled =", la.enabled, "| n points drawn =", 0 if off is None else len(off),
      "| x range", None if off is None or not len(off) else (off[:, 0].min().round(2), off[:, 0].max().round(2)))
v.state.slices = (30, 0, 0)
la.update()
print("   after slices=(30,0,0): points drawn =", len(la.plot_artist.get_xydata()), "(scatter is NOT sliced by the slider)")

# ---------- B: scatter Data in world coords, LinkSame on lon/lat only, then + time ----------
slit_w = Data(label="slit-world", lon=lon[nearest].ravel(), lat=lat[nearest].ravel(),
              t=np.repeat(t_world, ny))
dc.append(slit_w)
dc.add_link(LinkSame(slit_w.id["lon"], sji.world_component_ids[2]))
dc.add_link(LinkSame(slit_w.id["lat"], sji.world_component_ids[1]))
v2 = app.new_data_viewer(SimpleImageViewer, data=sji)
v2.add_data(slit_w)
lb = v2.layers[1]
print("B world-linked (lon/lat only): enabled =", lb.enabled, "| disabled reason:", getattr(lb, "disabled_message", "")[:120])
dc.add_link(LinkSame(slit_w.id["t"], sji.world_component_ids[0]))
lb.update()
offb = lb.plot_artist.get_xydata()
print("B world-linked (+time):        enabled =", lb.enabled, "| n points", len(offb),
      "| x range", (offb[:, 0].min().round(2), offb[:, 0].max().round(2)) if len(offb) else None)

# ---------- C: subset of the SJI dataset itself (slider-aware, no links) ----------
slit_x = np.array([np.asarray(sji.coords.world_to_pixel_values(lon[i, ny // 2], lat[i, ny // 2], t_world[f]))[0]
                   for f, i in enumerate(nearest)])
sji.add_component(np.broadcast_to(slit_x[:, None, None], sji.shape), "Slit x")
pix_x = sji.pixel_component_ids[2]
state = (pix_x > sji.id["Slit x"] - 0.5) & (pix_x <= sji.id["Slit x"] + 0.5)
sg = dc.new_subset_group("Slit", state)
mask = sji.subsets[0].to_mask()
print("C subset on SJI: frame0 columns flagged =", np.unique(np.where(mask[0])[1]), "| per-frame true count =", mask.sum(axis=(1, 2))[:3],
      "| viewer subset layer enabled =", [l.enabled for l in v.layers if l.layer is sji.subsets[0]])
v.state.slices = (10, 0, 0)
for l in v.layers:
    if l.layer is sji.subsets[0]:
        l.update()
        img = l.get_image_data() if hasattr(l, "get_image_data") else None
        print("   subset layer rendered slice shape:", None if img is None else np.asarray(img).shape,
              "| flagged column in rendered slice:", None if img is None else np.unique(np.where(np.asarray(img))[1]))

# ---------- B diagnostics: what glue derives for SJI pixel x on the world-linked data ----------
xa = np.concatenate(px)
xb = slit_w[sji.pixel_component_ids[2]]
print("B derived SJI pixel-x vs A direct: first 3 per frame 0/30/61:",
      [(round(float(xa[f*ny]), 2), round(float(xb[f*ny]), 2)) for f in (0, 30, 61)])
for link in sji.coordinate_links:
    if link.get_to_id() is sji.pixel_component_ids[2]:
        print("  coordinate link -> pixel x: from_needed =", link.from_needed, " from =", [c.label for c in link.get_from_ids()])
# what does the link's 'using' do with the given lon/lat/t?
f = 61
print("  direct _GlueWCS.world_to_pixel_values(lon,lat,t) for frame 61 mid-slit:",
      np.asarray(sji.coords.world_to_pixel_values(lon[nearest[f], 20], lat[nearest[f], 20], t_world[f])).round(2))
print("  ...with t=0 instead:", np.asarray(sji.coords.world_to_pixel_values(lon[nearest[f], 20], lat[nearest[f], 20], 0.0)).round(2))
# ---------- C: per-slice rendering via SubsetArray ----------
sub_layer = [l for l in v.layers if l.layer is sji.subsets[0]][0]
bounds = [(0, sji.shape[1] - 1, sji.shape[1]), (0, sji.shape[2] - 1, sji.shape[2])]
for s in (0, 30, 61):
    v.state.slices = (s, 0, 0)
    arr = sub_layer.subset_array(bounds)
    print(f"  C rendered subset at slice {s}: shape {arr.shape}, flagged column(s) {np.unique(np.where(np.asarray(arr) > 0)[1])}")
