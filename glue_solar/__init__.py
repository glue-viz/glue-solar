from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    pass

from glue_solar.instruments import *


def setup():
    from glue.viewers.image.qt import ImageViewer
    from glue_solar.pixel_extraction import PixelExtractionTool  # noqa
    from glue_solar.pixel_hover import HoverExtractionTool
    ImageViewer.tools.append('solar:pixel_extraction')
    ImageViewer.tools.append('solar:hover_extraction')
