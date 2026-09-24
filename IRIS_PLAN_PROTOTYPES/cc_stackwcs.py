"""Q3/Q5: per-scan exact WCS for the 4-D stack via gwcs + astropy tabular_model(3), no glue-core change."""
import warnings, numpy as np, astropy.units as u; warnings.simplefilter("ignore")
from astropy.modeling.tabular import tabular_model
from astropy.modeling.models import Mapping, Identity, Shift, Scale
from astropy import coordinates as coord
import gwcs, gwcs.coordinate_frames as cf
from irispy.io import read_files
from irispy.data.test import get_test_data_filenames
fs = sorted(str(f) for f in get_test_data_filenames() if "20140329" in str(f) and "raster_t000_r0000" in str(f))[:3]
seq = read_files(fs, spectral_windows=["Mg II k 2796"], uncertainty=False, memmap=False)["Mg II k 2796"]
lon = np.stack([c.axis_world_coords_values("custom:pos.helioprojective.lon")[0].to_value(u.arcsec) for c in seq])  # (nscan, nstep, nslit)
lat = np.stack([c.axis_world_coords_values("custom:pos.helioprojective.lat")[0].to_value(u.arcsec) for c in seq])
nscan, nstep, nslit = lon.shape; nwl = seq[0].data.shape[-1]
wl = seq[0].axis_world_coords_values("em.wl")[0].to_value(u.nm)
Tab3 = tabular_model(3)
pts = (np.arange(nscan), np.arange(nstep), np.arange(nslit))
tlon = Tab3(points=pts, lookup_table=lon, bounds_error=False, fill_value=np.nan, name="lon")
tlat = Tab3(points=pts, lookup_table=lat, bounds_error=False, fill_value=np.nan, name="lat")
twl = tabular_model(1)(points=(np.arange(nwl),), lookup_table=wl, bounds_error=False, fill_value=np.nan)
# pixel order (scan, step, slit, wl) -> world (scan, lon, lat, wl)
fwd = Mapping((0, 0, 1, 2, 0, 1, 2, 3)) | (Identity(1) & tlon & tlat & twl)
frames = cf.CompositeFrame([cf.CoordinateFrame(1, "SCAN", (0,), unit=(u.pix,), axes_names=("scan",), name="scan"),
                            cf.CelestialFrame(reference_frame=coord.ICRS(), axes_order=(1, 2), unit=(u.arcsec, u.arcsec), axes_names=("Tx", "Ty"), name="hpc"),
                            cf.SpectralFrame(axes_order=(3,), unit=(u.nm,), axes_names=("wl",), name="spec")])
pix = cf.CoordinateFrame(4, ["PIXEL"] * 4, range(4), unit=[u.pix] * 4, name="pix")
w = gwcs.WCS([(pix, fwd), (frames, None)])
print("physical types:", w.world_axis_physical_types, "corr rows:", w.axis_correlation_matrix.astype(int).tolist())
for s in range(nscan):
    sc, lo, la, wv = w.pixel_to_world_values(s, 3, 50, 7)
    wv0, la0, lo0 = seq[s].wcs.pixel_to_world_values(7, 50, 3)
    print(f"scan {s}: gwcs lon/lat {lo:.3f}/{la:.3f} vs per-scan -TAB {lo0*3600:.3f}/{la0*3600:.3f}  dlon={lo - lo0*3600:.2e}")
try:
    inv = w.numerical_inverse(*w.pixel_to_world_values(2, 3, 50, 7), with_units=False, maxiter=50, tolerance=1e-6)
    print("numerical_inverse:", np.round(inv, 3), "(expect 2,3,50,7)")
except Exception as e:
    print("numerical_inverse failed:", type(e).__name__, str(e)[:120])
try:
    print("world_to_pixel_values:", np.round(w.world_to_pixel_values(*w.pixel_to_world_values(2, 3, 50, 7)), 3))
except Exception as e:
    print("world_to_pixel_values failed:", type(e).__name__, str(e)[:100])
