"""
A reader for `sunpy.map.Map`.
"""
import sys
from abc import ABC

import matplotlib
from glue.config import colormaps, data_factory, qglue_parser
from glue.core.component import Component
from glue.core.data import Data
from glue.core.data_factories import is_fits
from glue.core.state import _load_style, _save_style
from glue.core.visual import VisualAttributes

from sunpy.visualization.colormaps import cmlist

__all__ = ["read_sunpy_map", "_parse_sunpy_map"]


class _GenericMap(ABC):
    """
    `sunpy.map.GenericMap` for glue's ``isinstance`` check, without importing sunpy.map at glue's launch: a map
    exists only once something has imported it.
    """

    @classmethod
    def __subclasshook__(cls, subclass):
        mapbase = sys.modules.get("sunpy.map.mapbase")
        return True if mapbase and issubclass(subclass, mapbase.GenericMap) else NotImplemented


def _add_colormap(name):
    """
    List sunpy's colormap ``name``, its key or its own name (which glue saves and maps give), if sunpy has one, in
    glue's colormap menus.
    """
    ctable = cmlist.get(name) or next((cmap for cmap in cmlist.values() if cmap.name == name), None)
    if ctable is not None and all(ctable is not cmap for _, cmap in colormaps.members):
        colormaps.add(ctable.name, ctable)
    if ctable is not None and ctable.name not in matplotlib.colormaps:
        # glue restores a session's colormap from matplotlib's, where sunpy lists most under their key only
        matplotlib.colormaps.register(ctable, name=ctable.name)


class _Style(VisualAttributes):
    """
    glue's style of a dataset, which a session saves with its preferred colormap: glue-core 1.27.0 writes that colormap
    as it is, which fails the save, and restores a style without one.
    """

    def __gluestate__(self, context):
        return {**_save_style(self, context), "preferred_cmap": context.id(self.preferred_cmap)}

    @classmethod
    def __setgluestate__(cls, rec, context):
        style = cls()
        style.set(_load_style(rec, context))
        style.preferred_cmap = context.object(rec["preferred_cmap"])  # glue's saver of a colormap, by its name
        return style


@qglue_parser(_GenericMap)
def _parse_sunpy_map(data, label):
    """
    Parse sunpy map so that it can be loaded by ``glue``.
    """
    scan_map = data
    label = label + "-" + scan_map.name
    result = Data(label=label)
    result.coords = scan_map.wcs  # preferred way, preserves more info in some cases
    result.add_component(Component(scan_map.data), scan_map.name)
    result.meta = scan_map.meta
    _add_colormap(scan_map.cmap.name)  # for the colormap menu of its Image layers
    result.style = _Style(color="#FDB813", preferred_cmap=scan_map.cmap)

    return result


@data_factory("sunpy Map", is_fits)
def read_sunpy_map(sunpy_map_file):
    """
    For ``glue`` to read in parsed sunpy map.
    """
    import sunpy.map

    sunpy_map_data = _parse_sunpy_map(sunpy.map.Map(sunpy_map_file), "sunpy-map")
    return sunpy_map_data

