"""WP7 SDO v2: FOV polygon via axis_correlation_matrix (non-spatial axes at 0), AIA Data through _GlueWCS
so physical-type LinkSame works in arcsec, subset propagation counts, ImageViewer. No network."""
import faulthandler, os, warnings; faulthandler.dump_traceback_later(300, exit=True)
warnings.filterwarnings("ignore")
import numpy as np, astropy.units as u
from astropy.coordinates import SkyCoord
import sunpy.map
from sunpy.map.header_helper import make_fitswcs_header
from sunpy.coordinates import Helioprojective, propagate_with_solar_surface
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.maps import _parse_sunpy_map
from glue_solar.sources.loaders.iris import image_data, raster_data, _GlueWCS

HPC = "custom:pos.helioprojective."

def fov_polygon(data):
    """4 (lon, lat) corners in arcsec of the first exposure/scan, in polygon order."""
    wcs = data.coords
    types = list(wcs.world_axis_physical_types)
    ilon, ilat = types.index(HPC + "lon"), types.index(HPC + "lat")
    corr = wcs.axis_correlation_matrix                       # (world, pixel)
    spatial = [p for p in range(wcs.pixel_n_dim) if corr[ilon, p] or corr[ilat, p]]
    other = [w for w in range(wcs.world_n_dim) if w not in (ilon, ilat)]
    spatial = [p for p in spatial if not corr[other, p].any()]  # drop time/scan/wavelength pixel axes
    assert len(spatial) == 2, spatial
    px, py = spatial                                          # APE-14 pixel axes (x first)
    shape = data.shape[::-1]                                  # pixel-axis order
    corners = np.zeros((4, wcs.pixel_n_dim))                  # ponytail: pixel centres, half a pixel short
    corners[:, px] = [0, shape[px] - 1, shape[px] - 1, 0]
    corners[:, py] = [0, 0, shape[py] - 1, shape[py] - 1]
    world = wcs.pixel_to_world_values(*corners.T)
    return np.asarray(world[ilon]), np.asarray(world[ilat]), spatial

fs = get_test_data_filenames()
sji = image_data(str([f for f in fs if f.name.endswith("3620258102_SJI_1400_t000.fits")][0]))
ras = raster_data([str(f) for f in fs if f.name.endswith("3620258102_raster_t000_r00000.fits")][:1], ["Mg II k 2796"])[0]
stack = raster_data(sorted(str(f) for f in fs if "3860258481_raster_t000_r0000" in f.name)[:2], ["C II 1336"], stack=True)[0]
for d in (sji, ras, stack):
    print("corr matrix", d.label, d.shape, "\n", d.coords.axis_correlation_matrix.astype(int))
    lon, lat, spatial = fov_polygon(d)
    print("  spatial pixel axes:", spatial, "polygon lon:", np.round(lon, 1), "lat:", np.round(lat, 1))

t0 = str(sji.meta["STARTOBS"])
lon, lat, _ = fov_polygon(sji)
corners = SkyCoord(lon * u.arcsec, lat * u.arcsec, frame=Helioprojective(obstime=t0, observer="earth"))

def synthetic_aia(obstime, centre, n=800):
    ref = SkyCoord(*centre, frame=Helioprojective(obstime=obstime, observer="earth"))
    hdr = make_fitswcs_header(np.zeros((n, n)), ref, scale=[0.6, 0.6] * u.arcsec / u.pix,
                              instrument="AIA", telescope="SDO/AIA", observatory="SDO", wavelength=171 * u.AA, exposure=2 * u.s)
    return sunpy.map.Map(np.random.default_rng(0).random((n, n)), hdr)

aia = synthetic_aia(t0, (lon.mean() * u.arcsec, lat.mean() * u.arcsec))
plain = corners.transform_to(aia.coordinate_frame)
with propagate_with_solar_surface():
    c_aia = corners.transform_to(aia.coordinate_frame)
print("same-time transform identical:", np.allclose(plain.Tx.value, c_aia.Tx.value), np.allclose(plain.Ty.value, c_aia.Ty.value))
margin = 100 * u.arcsec
bl = SkyCoord(c_aia.Tx.min() - margin, c_aia.Ty.min() - margin, frame=aia.coordinate_frame)
tr = SkyCoord(c_aia.Tx.max() + margin, c_aia.Ty.max() + margin, frame=aia.coordinate_frame)
ctx = aia.submap(bl, top_right=tr)
print("full map:", aia.dimensions, "-> submap:", ctx.dimensions)
gd = _parse_sunpy_map(ctx, "SDO context")
print("raw map wcs names/units:", ctx.wcs.world_axis_names, ctx.wcs.world_axis_units, "| glue world:", [str(c) for c in gd.world_component_ids], "units:", [gd.get_component(c).units for c in gd.world_component_ids])
gd.coords = _GlueWCS(ctx.wcs)
print("with _GlueWCS: world:", [str(c) for c in gd.world_component_ids], "units:", [gd.get_component(c).units for c in gd.world_component_ids], "| IRIS SJI units:", [sji.get_component(c).units for c in sji.world_component_ids])
from glue.core import DataCollection
from glue.core.roi import PolygonalROI
from glue.core.subset import RoiSubsetState
from glue.core.link_helpers import LinkSame
px, py = ctx.wcs.world_to_pixel(c_aia)
state = RoiSubsetState(xatt=gd.pixel_component_ids[1], yatt=gd.pixel_component_ids[0], roi=PolygonalROI(vx=list(px), vy=list(py)))
dc = DataCollection([gd, sji, ras])
dc.new_subset_group("IRIS FOV", state)
print("FOV subset on AIA:", int(gd.subsets[0].to_mask().sum()), "px of", gd.size)
def by_type(d):
    return {p: c for c, p in zip(d.world_component_ids, d.coords.world_axis_physical_types[::-1])}
for other in (sji, ras):
    for p in (HPC + "lon", HPC + "lat"):
        dc.add_link(LinkSame(by_type(gd)[p], by_type(other)[p]))
m = sji.subsets[0].to_mask(); print("FOV subset on SJI ->", int(m.sum()), "of", sji.size, "| per frame first 3:", m.reshape(62, -1).sum(1)[:3], "last:", m.reshape(62, -1).sum(1)[-1])
m = ras.subsets[0].to_mask(); print("FOV subset on raster ->", int(m.sum()), "of", ras.size, "| steps hit:", np.flatnonzero(m.reshape(187, -1).sum(1))[[0, -1]] if m.any() else None)
# reverse direction: an SJI pixel ROI shows up on the AIA context
from glue.core.roi import RectangularROI
st2 = RoiSubsetState(xatt=sji.pixel_component_ids[2], yatt=sji.pixel_component_ids[1], roi=RectangularROI(5, 15, 5, 15))
dc.new_subset_group("SJI box", st2)
try:
    print("SJI box on AIA ->", int(gd.subsets[1].to_mask().sum()), "px")
except Exception as e:
    print("SJI pixel ROI -> AIA:", type(e).__name__, "(SJI gWCS needs time to invert; expected)")
aia.save(os.path.join(os.environ["HOME"], "synthetic_aia171.fits"), overwrite=True)
m2 = sunpy.map.Map(os.path.join(os.environ["HOME"], "synthetic_aia171.fits")); print("round-trip FITS:", type(m2).__name__, m2.date.isot, m2.dimensions)
print("dc.links:", len(dc.links))
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
app = GlueApplication(dc)
iv = app.new_data_viewer(ImageViewer, data=gd)
iv.figure.canvas.draw()
print("ImageViewer layers:", [(type(l).__name__, l.enabled) for l in iv.layers])
os._exit(0)
