import matplotlib
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer
d = Data(x=[1, 2, 3], label='d')
d.style.preferred_cmap = matplotlib.colormaps['viridis']   # any plugin setting a Colormap object
print('preferred_cmap is', type(d.style.preferred_cmap).__name__)
try:
    GlueSerializer(DataCollection([d])).dumps(); print('save OK')
except Exception as e:
    print('save FAILS:', type(e).__name__, str(e)[:80])
# proposed one-line fix in glue/core/state.py _save_style
import glue.core.state as st
from glue.core.visual import VisualAttributes
def _save_style_fixed(style, context):
    return dict((a, getattr(getattr(style, a), 'name', getattr(style, a))) for a in style._atts)
st.saver.members[VisualAttributes][1] = (_save_style_fixed, st.saver.members[VisualAttributes][1][1]) if isinstance(st.saver.members[VisualAttributes][1], tuple) else _save_style_fixed
s = GlueSerializer(DataCollection([d])).dumps(); print('with getattr(.., "name") fix: save OK,', len(s), 'bytes')
