from glue.config import colormaps

from sunpy.visualization.colormaps import cmlist

from glue_solar.sources import iris, maps, sst
from glue_solar.version import version as __version__

__all__ = ["setup", "__version__", "iris", "maps", "sst"]

def setup():
    # Enables sunpy colormaps to be used in glueviz
    for _, ctable in sorted(cmlist.items()):
        colormaps.add(ctable.name, ctable)
