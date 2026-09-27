import os, traceback, warnings; warnings.simplefilter("ignore")
import numpy as np, shapely
from astropy.wcs import WCS
from glue.core import Data
from glue.core.application_base import Application
from glue.core.data_region import RegionData
from glue.core.link_helpers import LinkSame
from glue.viewers.image.viewer import SimpleImageViewer
w = WCS(naxis=2); w.wcs.ctype = ['HPLN-TAN', 'HPLT-TAN']; w.wcs.cunit = ['arcsec', 'arcsec']
w.wcs.cdelt = [1, 1]; w.wcs.crpix = [8, 8]; w.wcs.crval = [0, 0]
d = Data(label='img', x=np.zeros((16, 16)))
d.coords = None if os.environ.get('NOCOORDS') else w
reg = RegionData(label='fov', regions=np.array([shapely.Polygon([(4, 4), (8, 4), (8, 9), (4, 9)])]))
app = Application(); dc = app.data_collection; dc.append(d); dc.append(reg)
v = app.new_data_viewer(SimpleImageViewer, data=d)
dc.add_link(LinkSame(reg.center_x_id, d.pixel_component_ids[1]))
dc.add_link(LinkSame(reg.center_y_id, d.pixel_component_ids[0]))
v.add_data(reg)
try:
    v.figure.canvas.draw(); print('coords=%s: draw OK, layers %s' % (type(d.coords).__name__, [(type(l).__name__, l.enabled) for l in v.layers]))
except Exception as e:
    tb = traceback.extract_tb(e.__traceback__)[-3:]
    print('coords=%s: draw FAILS %s: %s' % (type(d.coords).__name__, type(e).__name__, e)); [print('   ', f.filename.split('site-packages/')[-1], f.lineno, f.name) for f in tb]
