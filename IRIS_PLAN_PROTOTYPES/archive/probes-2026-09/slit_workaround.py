"""Does a fully-coupled correlation matrix on _GlueWCS make HPC world links to the SJI correct?"""
import warnings; warnings.simplefilter("ignore")
import numpy as np
from glue.core import Data, DataCollection
from glue.core.link_helpers import LinkSame
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders import iris as loader

files = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in files if "sns/" in f and "SJI_1400" in f][0]
ras_paths = [f for f in files if "sns/" in f and "raster" in f]

def run(patched):
    if patched:
        # transitive closure: a pixel axis feeds every world axis coupled to any world axis it feeds
        def acm(self):
            m = self._wcs.axis_correlation_matrix
            closure = m.copy()
            for _ in range(m.shape[0]):
                closure = closure | ((closure @ closure.T.astype(int)) > 0) @ m
            return closure
        loader._GlueWCS.axis_correlation_matrix = property(acm)
    sji = loader.image_data(sji_path)
    [ras] = loader.raster_data(ras_paths, ["C II 1336"])
    dc = DataCollection([sji, ras])
    ny = ras.shape[1]
    lon = ras[ras.world_component_ids[0]][:, :, 0]; lat = ras[ras.world_component_ids[1]][:, :, 0]
    t_ras = ras["Time"][:, 0, 0]
    from irispy.io import read_files
    (t_sji,) = read_files(sji_path, memmap=False, uncertainty=False).axis_world_coords("time")
    t_sji = t_sji.utc.to_value("datetime64")
    t_world = sji[sji.world_component_ids[0]][:, 0, 0]
    nearest = np.array([np.abs(t_ras - t).argmin() for t in t_sji])
    slit = Data(label="slit", lon=lon[nearest].ravel(), lat=lat[nearest].ravel(), t=np.repeat(t_world, ny))
    dc.append(slit)
    dc.add_link(LinkSame(slit.id["lon"], sji.world_component_ids[2]))
    dc.add_link(LinkSame(slit.id["lat"], sji.world_component_ids[1]))
    dc.add_link(LinkSame(slit.id["t"], sji.world_component_ids[0]))
    x = slit[sji.pixel_component_ids[2]]
    print(f"patched={patched}: matrix\n{sji.coords.axis_correlation_matrix.astype(int)}\n  derived SJI pixel-x mid-slit frames 0/30/61:",
          [round(float(x[f*ny + 20]), 2) for f in (0, 30, 61)], "(direct gWCS: 21.05 / 20.62 / 21.24)")
    # sanity: does the raster<->SJI HPC LinkSame (P1.4 style) place raster pixels in the SJI right? derive SJI x for raster step 186
    dc.add_link(LinkSame(ras.world_component_ids[0], sji.world_component_ids[2]))
    dc.add_link(LinkSame(ras.world_component_ids[1], sji.world_component_ids[1]))
    try:
        rx = ras[sji.pixel_component_ids[2]]
        print("  raster->SJI pixel x via lon/lat-only LinkSame: step0", round(float(rx[0, 20, 0]), 2), "step186", round(float(rx[186, 20, 0]), 2))
    except Exception as e:
        print("  raster->SJI pixel x via lon/lat-only LinkSame: ", type(e).__name__, str(e)[:80])

run(False)
run(True)
