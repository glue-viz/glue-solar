"""WP7 SDO: generic FOV bbox from a glue Data's coords, synthetic AIA map, propagate_with_solar_surface,
submap, _parse_sunpy_map, PolygonalROI subset, ImageViewer, physical-type LinkSame. No network."""
import faulthandler, os, itertools, warnings; faulthandler.dump_traceback_later(240, exit=True)
warnings.filterwarnings("ignore")
import numpy as np, astropy.units as u
from astropy.coordinates import SkyCoord
import sunpy.map
from sunpy.map.header_helper import make_fitswcs_header
from sunpy.coordinates import Helioprojective, propagate_with_solar_surface
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.maps import _parse_sunpy_map
from glue_solar.sources.loaders.iris import image_data, raster_data

HPC = "custom:pos.helioprojective."

def fov_bbox(data, edges=True):
    """(lon_min, lon_max, lat_min, lat_max) in arcsec from every pixel corner of ``data``."""
    off = 0.5 if edges else 0.0
    corners = np.array(list(itertools.product(*[(-off, n - 1 + off) for n in data.shape])))  # numpy order
    pix = corners[:, ::-1].T                     # APE-14 pixel order (x first)
    world = data.coords.pixel_to_world_values(*pix)
    types = data.coords.world_axis_physical_types
    lon = np.asarray(world[types.index(HPC + "lon")]); lat = np.asarray(world[types.index(HPC + "lat")])
    return np.nanmin(lon), np.nanmax(lon), np.nanmin(lat), np.nanmax(lat), int(np.isnan(lon).sum())

fs = get_test_data_filenames()
sji = image_data(str([f for f in fs if f.name.endswith("3620258102_SJI_1400_t000.fits")][0]))
ras = raster_data([str(f) for f in fs if f.name.endswith("3620258102_raster_t000_r00000.fits")][:1], ["Mg II k 2796"])[0]
for d in (sji, ras):
    print(d.label, d.shape, "edges bbox:", np.round(fov_bbox(d)[:4], 1), "nan corners:", fov_bbox(d)[4], "| centres bbox:", np.round(fov_bbox(d, edges=False)[:4], 1))
# world_component_ids[i] <-> physical_types[ndim-1-i] ?
for d in (sji, ras):
    print("  ", [(str(c), p) for c, p in zip(d.world_component_ids, d.coords.world_axis_physical_types[::-1])])

t0 = str(sji.meta["STARTOBS"])
lon0, lon1, lat0, lat1, _ = fov_bbox(sji)
frame = Helioprojective(obstime=t0, observer="earth")
corners = SkyCoord([lon0, lon1, lon1, lon0] * u.arcsec, [lat0, lat0, lat1, lat1] * u.arcsec, frame=frame)

def synthetic_aia(obstime, centre):
    ref = SkyCoord(*centre, frame=Helioprojective(obstime=obstime, observer="earth"))
    hdr = make_fitswcs_header(np.zeros((300, 300)), ref, scale=[0.6, 0.6] * u.arcsec / u.pix,
                              instrument="AIA", telescope="SDO/AIA", observatory="SDO", wavelength=171 * u.AA, exposure=2 * u.s)
    return sunpy.map.Map(np.random.default_rng(0).random((300, 300)), hdr)

aia = synthetic_aia(t0, ((lon0 + lon1) / 2 * u.arcsec, (lat0 + lat1) / 2 * u.arcsec))
print("synthetic map:", type(aia).__name__, aia.date.isot, aia.dimensions, "cmap:", aia.cmap.name, "wavelength:", aia.wavelength)
# propagate_with_solar_surface: only matters when the AIA time differs from STARTOBS
late = synthetic_aia("2021-09-05T03:18:33", ((lon0 + lon1) / 2 * u.arcsec, (lat0 + lat1) / 2 * u.arcsec))
plain = corners.transform_to(late.coordinate_frame)
with propagate_with_solar_surface():
    rotated = corners.transform_to(late.coordinate_frame)
print("3h later: plain Tx", np.round(plain.Tx.to_value(u.arcsec), 1), "| propagated Tx", np.round(rotated.Tx.to_value(u.arcsec), 1))
with propagate_with_solar_surface():
    c_aia = corners.transform_to(aia.coordinate_frame)
margin = 100 * u.arcsec
bl = SkyCoord(c_aia.Tx.min() - margin, c_aia.Ty.min() - margin, frame=aia.coordinate_frame)
tr = SkyCoord(c_aia.Tx.max() + margin, c_aia.Ty.max() + margin, frame=aia.coordinate_frame)
ctx = aia.submap(bl, top_right=tr)
print("submap:", ctx.dimensions)
gd = _parse_sunpy_map(ctx, "AIA 171 context")
print("glue Data:", gd.label, gd.shape, "world:", [str(c) for c in gd.world_component_ids], "phys:", gd.coords.world_axis_physical_types, "cmap:", gd.style.preferred_cmap.name, "meta type:", type(gd.meta).__name__)
# FOV polygon as a subset in AIA pixel coords (no link needed)
from glue.core import DataCollection
from glue.core.roi import PolygonalROI
from glue.core.subset import RoiSubsetState
px, py = ctx.wcs.world_to_pixel(c_aia)
state = RoiSubsetState(xatt=gd.pixel_component_ids[1], yatt=gd.pixel_component_ids[0], roi=PolygonalROI(vx=list(px), vy=list(py)))
dc = DataCollection([gd, sji, ras])
sg = dc.new_subset_group("IRIS FOV", state)
print("FOV subset on AIA: px", int(gd.subsets[0].to_mask().sum()), "of", gd.size, "| polygon px:", np.round(px, 1), np.round(py, 1))
# physical-type LinkSame (what WP1 link_hpc does) -> subset propagates to the IRIS datasets
from glue.core.link_helpers import LinkSame
def by_type(d):
    return {p: c for c, p in zip(d.world_component_ids, d.coords.world_axis_physical_types[::-1])}
for other in (sji, ras):
    for p in (HPC + "lon", HPC + "lat"):
        dc.add_link(LinkSame(by_type(gd)[p], by_type(other)[p]))
for other in (sji, ras):
    m = other.subsets[0].to_mask(); print("FOV subset on", other.label, "->", int(m.sum()), "of", other.size)
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
app = GlueApplication(dc)
iv = app.new_data_viewer(ImageViewer, data=gd)
iv.figure.canvas.draw()
print("ImageViewer layers:", [(type(l).__name__, l.enabled) for l in iv.layers])
os._exit(0)
