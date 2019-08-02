from pkg_resources import get_distribution, DistributionNotFound
from sunpy.cm import cmlist
from glue.viewers.image.qt import ImageViewer
from glue_solar.pixel_extraction import PixelExtractionTool  # noqa
from glue.config import colormaps
from glue_solar.instruments import *

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    pass

def setup():
    ImageViewer.tools.append('solar:pixel_extraction')
    ImageViewer.tools.append('timestamp_button')
    for name, ctable in sorted(cmlist.items()):
        colormaps.add(ctable.name, ctable)
