"""Optional glue-core PR: x axis label carries the display unit (glue/viewers/profile/viewer.py:15-23)."""
import warnings; warnings.simplefilter("ignore")
from glue.config import settings; settings._save_to_disk = False; settings.SHOW_INFO_PROFILE_OPEN = False
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp5_units  # noqa: F401
import numpy as np
from astropy.wcs import WCS
from glue.core import Data, DataCollection
from glue.viewers.profile.viewer import MatplotlibProfileMixin

_orig_setup, _orig_update = MatplotlibProfileMixin.setup_callbacks, MatplotlibProfileMixin._update_axes
def setup_callbacks(self):
    _orig_setup(self)
    self.state.add_callback('x_display_unit', self._update_axes)          # PR line 1
def _update_axes(self, *args):
    _orig_update(self, *args)
    if self.state.x_att is not None and self.state.x_display_unit:
        self.state.x_axislabel = f'{self.state.x_att.label} [{self.state.x_display_unit}]'  # PR line 2
MatplotlibProfileMixin.setup_callbacks, MatplotlibProfileMixin._update_axes = setup_callbacks, _update_axes

from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
w = WCS(naxis=1); w.wcs.ctype = ['WAVE']; w.wcs.cunit = ['Angstrom']; w.wcs.crval = [1330]; w.wcs.cdelt = [0.1]; w.wcs.crpix = [1]
spec = Data(label='spec', flux=np.random.random(100), coords=w); spec.meta['rest_wavelength'] = 1335.71
app = GlueApplication(DataCollection([spec]))
v = app.new_data_viewer(ProfileViewer, data=spec); v.state.x_att = spec.world_component_ids[0]
for unit in ('Angstrom', 'nm', 'km / s'):
    v.state.x_display_unit = unit; v.axes.figure.canvas.draw(); print(unit, '->', repr(v.axes.get_xlabel()), flush=True)
