"""
A reader for `sunpy.map.Map`.
"""
import sys
from abc import ABC

from glue.config import data_factory, qglue_parser
from glue.core.component import Component
from glue.core.data import Data
from glue.core.data_factories import is_fits
from glue.core.visual import VisualAttributes

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
    result.style = VisualAttributes(color="#FDB813", preferred_cmap=scan_map.cmap)

    return result


@data_factory("sunpy Map", is_fits)
def read_sunpy_map(sunpy_map_file):
    """
    For ``glue`` to read in parsed sunpy map.
    """
    import sunpy.map

    sunpy_map_data = _parse_sunpy_map(sunpy.map.Map(sunpy_map_file), "sunpy-map")
    return sunpy_map_data

