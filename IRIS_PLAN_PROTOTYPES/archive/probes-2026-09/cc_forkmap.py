"""Q2: on fork ape14-wcs-autolink, does the _GlueWCS coherence fix (P3.1-sec4) also make raster3D<->moment-map2D autolink (P2.1-link said IncompatibleWCS)?"""
import warnings, numpy as np, astropy.units as u; warnings.simplefilter("ignore")
import glue; print("glue from", glue.__file__)
from irispy.data.test import get_test_data_filenames
from irispy.io import read_files
from irispy.utils.moments import calculate_moments
from glue_solar.sources.loaders.iris import raster_data, _cube_data, _GlueWCS
from glue.core import DataCollection
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink, WCSLink, IncompatibleWCS
class FixedGlueWCS(_GlueWCS):
    def _hpc(self, i):
        t = self.world_axis_physical_types[i]; return bool(t) and t.startswith("custom:pos.helioprojective.")
    @property
    def world_axis_object_components(self):
        comps = []
        for i, (key, attr, getter) in enumerate(self._wcs.world_axis_object_components):
            if self._hpc(i):
                unit = u.Unit(self._wcs.world_axis_units[i])
                getter = lambda obj, g=getter, unit=unit: (np.asarray(g(obj)) * unit).to_value(u.arcsec)
            comps.append((key, attr, getter))
        return comps
    @property
    def world_axis_object_classes(self):
        comps = self._wcs.world_axis_object_components; out = {}
        for key, (cls, args, kwargs, *rest) in self._wcs.world_axis_object_classes.items():
            if "unit" in kwargs and any(self._hpc(i) for i, c in enumerate(comps) if c[0] == key):
                kwargs = {**kwargs, "unit": tuple([u.arcsec] * len([c for c in comps if c[0] == key]))}
            out[key] = (cls, args, kwargs, *rest)
        return out
fs = [str(f) for f in get_test_data_filenames() if str(f).endswith(".fits")]
f = [x for x in fs if "20140329" in x and "r00000" in x]
cube = read_files(f, spectral_windows=["Mg II k 2796"], uncertainty=False, memmap=False)["Mg II k 2796"][0]
maps = calculate_moments(cube, rest_wavelength=2791.3 * u.AA, wings=0.5 * u.AA, min_intensity=50)
def fresh(wrap):
    [src] = raster_data(f, ["Mg II k 2796"]); vel = _cube_data(maps["velocity"], "vel"); inten = _cube_data(maps["intensity"], "int")
    for d in (src, vel, inten): d.coords = wrap(d)
    return src, vel, inten
for label, wrap in (("stock _GlueWCS", lambda d: d.coords), ("FixedGlueWCS", lambda d: FixedGlueWCS(d.coords._wcs))):
    for pair, name in (((0, 1), "raster3D<->map2D"), ((1, 2), "map2D<->map2D")):
        ds = fresh(wrap); a, b = ds[pair[0]], ds[pair[1]]
        links = wcs_autolink(DataCollection([a, b]))
        try: WCSLink(a, b); direct = "WCSLink ok"
        except IncompatibleWCS as e: direct = f"IncompatibleWCS({str(e)[:60]})"
        except Exception as e: direct = f"{type(e).__name__}: {str(e)[:60]}"
        print(f"{label:14s} {name:18s} autolink={len(links)} direct={direct}")
        if links:
            l = links[0]; print("     cids:", [c.label for c in l.cids1], "<->", [c.label for c in l.cids2])
