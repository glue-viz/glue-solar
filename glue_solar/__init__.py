from glue.config import colormaps
from glue.viewers.image.qt import ImageViewer

from sunpy.visualization.colormaps import cmlist

from glue_solar.pixel_extraction.pixel_extraction import PixelExtractionTool  # NOQA
from glue_solar.sources import iris, maps, sst  # NOQA
from glue_solar.version import version as __version__


def setup():
    # List of all plugins to enable to the default ImageViewer
    ImageViewer.tools.append("solar:pixel_extraction")
    # Enables sunpy colormaps to be used in glueviz
    for _, ctable in sorted(cmlist.items()):
        colormaps.add(ctable.name, ctable)
