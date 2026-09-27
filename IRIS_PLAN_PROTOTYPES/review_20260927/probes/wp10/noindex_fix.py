import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


def without_step_index(wcs):
    """wcslib searches a -TAB index vector linearly, so irispy's 1..N exposure index costs O(exposure) per point; drop it (FITS implies 1..N)."""
    hdr = wcs.to_header()
    if len(wcs.wcs.tab) != 1 or hdr.get("PS3_2") != "RASTER":
        return wcs
    tab = wcs.wcs.tab[0]
    spatial = wcs.wcs.crval[1] + wcs.wcs.cdelt[1] * (np.array([1.0, wcs.pixel_shape[1]]) - wcs.wcs.crpix[1])
    table = np.array([(tab.coord, spatial)], dtype=[("COORDS", float, tab.coord.shape), ("SPATIAL", float, spatial.shape)])
    del hdr["PS3_2"]
    new = WCS(hdr, fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(table, name=hdr["PS2_0"])]))
    new.pixel_shape = wcs.pixel_shape
    probe = [np.array([0.0, 3.0]), np.array([0.0, wcs.pixel_shape[1] - 1.0]), np.array([0.0, wcs.pixel_shape[2] - 1.0])]
    return new if np.allclose(new.pixel_to_world_values(*probe), wcs.pixel_to_world_values(*probe), rtol=0, atol=1e-12) else wcs


