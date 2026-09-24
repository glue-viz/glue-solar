"""WP1: display units reach the viewers; high-level API also works for the 4D stack and 2D moment maps."""
import warnings; warnings.simplefilter("ignore")
import numpy as np, astropy.units as u
from astropy.wcs.wcsapi import HighLevelWCSWrapper
from irispy.data.test import get_test_data_filenames
from irispy.io import read_files
from irispy.utils.moments import calculate_moments
from glue_solar.sources.loaders.iris import raster_data, _cube_data, image_data
files = list(get_test_data_filenames())
scans = sorted(p for p in files if "3860258481_raster_t000_r0000" in p.name)[:2]
[stack] = raster_data(scans, ["C II 1336"], stack=True)
cube = read_files(scans[:1], spectral_windows=["Mg II k 2796"], memmap=False, uncertainty=False)["Mg II k 2796"][0]
vel = _cube_data(calculate_moments(cube)["velocity"], "velocity")
for name, d, px in (("4D stack", stack, (3, 50, 4, 1)), ("2D moment map", vel, (50, 4))):
    hl = HighLevelWCSWrapper(d.coords); objs = hl.pixel_to_world(*px); objs = objs if isinstance(objs, list) else [objs]; vals = d.coords.pixel_to_world_values(*px)
    sky = next(o for o in objs if hasattr(o, "Tx"))
    print(f"{name}: units {d.coords.world_axis_units} | low-level {np.round(vals, 3).tolist()} | SkyCoord Tx,Ty arcsec {sky.Tx.to_value(u.arcsec):.3f},{sky.Ty.to_value(u.arcsec):.3f} | round trip {np.round(hl.world_to_pixel(*objs), 4).tolist()}")
# viewers
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
sns = lambda n: next(p for p in files if p.name.endswith(n) and p.parent.name == "sns")
[ras] = raster_data([sns("raster_t000_r00000.fits")], ["Si IV 1403"]); sji = image_data(sns("SJI_1400_t000.fits"))
app = GlueApplication(); dc = app.data_collection; dc.append(ras); dc.append(sji)
v = app.new_data_viewer(ImageViewer, data=ras); v.figure.canvas.draw()
print("raster ImageViewer default axes:", v.state.x_att_world, "/", v.state.y_att_world, "| format_coord(10, 20):", v.axes.format_coord(10, 20), "| xlabel:", v.axes.get_xlabel())
p = app.new_data_viewer(ProfileViewer, data=ras); p.state.x_att = next(c for c in ras.world_component_ids if c.label == "Wavelength"); p.figure.canvas.draw()
x = p.layers[0].state.profile[0]; print("ProfileViewer x=Wavelength range:", round(float(x.min()), 2), round(float(x.max()), 2), "| x_display_unit:", p.state.x_display_unit)
s = app.new_data_viewer(ImageViewer, data=sji); s.figure.canvas.draw()
print("SJI ImageViewer axes:", s.state.x_att_world, "/", s.state.y_att_world, "| format_coord(18, 20):", s.axes.format_coord(18, 20))
app.close()
