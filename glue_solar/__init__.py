from glue.config import colormaps
from glue.viewers.image.qt import ImageViewer

from sunpy.visualization.colormaps import cmlist

from .pixel_tool import PixelInfoTool  # NOQA
from .version import version as __version__


def setup():
    # List of all plugins to enable to the default ImageViewer
    ImageViewer.tools.append("solar:pixel_info")
    # Enables sunpy colormaps to be used in glueviz
    for _, ctable in sorted(cmlist.items()):
        colormaps.add(ctable.name, ctable)
