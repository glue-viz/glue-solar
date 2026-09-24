from functools import reduce
import numpy as np
import astropy.units as u
from astropy.wcs.wcsapi import BaseWCSWrapper
# irispy's FITS WCSes carry no axis names (Glue would say "World N") and its gWCS uses other ones ("Longitude"),
# so one name per physical type keeps SJI, raster and map components identically labelled.
_AXIS_NAMES = {
    "em.wl": "Wavelength",
    "custom:pos.helioprojective.lon": "Helioprojective Longitude",
    "custom:pos.helioprojective.lat": "Helioprojective Latitude",
}
# Display units, whatever the file stores: helioprojective axes in arcsec, wavelength in Angstrom.
_AXIS_UNITS = {
    "em.wl": u.AA,
    "custom:pos.helioprojective.lon": u.arcsec,
    "custom:pos.helioprojective.lat": u.arcsec,
}


class _GlueWCS(BaseWCSWrapper):
    """
    Present named helioprojective coordinates in arcsec and wavelengths in Angstrom to Glue.

    The low-level values API and the high-level object API (`~astropy.wcs.wcsapi.HighLevelWCSWrapper`,
    `~astropy.wcs.utils.pixel_to_pixel`, hence Glue's WCS autolinker) both speak the display units.
    """

    def _units(self, world_axis):
        """``(stored unit, display unit)`` of a world axis, or `None` when it is shown as stored."""
        target = _AXIS_UNITS.get(self._wcs.world_axis_physical_types[world_axis])
        return (u.Unit(self._wcs.world_axis_units[world_axis]), target) if target else None

    @property
    def world_axis_names(self):
        return [
            _AXIS_NAMES.get(physical_type) or name or physical_type or ""
            for name, physical_type in zip(self._wcs.world_axis_names, self._wcs.world_axis_physical_types)
        ]

    @property
    def world_axis_units(self):
        return tuple(str(units[1]) if (units := self._units(i)) else unit for i, unit in enumerate(self._wcs.world_axis_units))

    def pixel_to_world_values(self, *pixel_arrays):
        values = list(self._wcs.pixel_to_world_values(*pixel_arrays))
        for i, physical_type in enumerate(self.world_axis_physical_types):
            if units := self._units(i):
                stored, target = units
                values[i] = np.asarray(values[i])
                if physical_type.endswith(".lon"):
                    full_circle = (360 * u.deg).to_value(stored)
                    values[i] = (values[i] + full_circle / 2) % full_circle - full_circle / 2
                values[i] = (values[i] * stored).to_value(target)
        return tuple(values)

    def world_to_pixel_values(self, *world_arrays):
        values = list(world_arrays)
        for i in range(self.world_n_dim):
            if units := self._units(i):
                stored, target = units
                values[i] = (np.asarray(values[i]) * target).to_value(stored)
        return self._wcs.world_to_pixel_values(*values)

    # The high-level API builds objects from, and reads values back through, the two properties below; they
    # must use the same units as the value methods above or SkyCoord sees arcsec as degrees.
    @property
    def world_axis_object_components(self):
        components = []
        for i, (key, index, getter) in enumerate(self._wcs.world_axis_object_components):
            if units := self._units(i):
                getter = self._converting_getter(getter, *units)
            components.append((key, index, getter))
        return components

    @staticmethod
    def _converting_getter(getter, stored, target):
        def convert(obj):
            value = getter(obj) if callable(getter) else reduce(getattr, getter.split("."), obj)
            return (np.asarray(value) * stored).to_value(target)

        return convert

    @property
    def world_axis_object_classes(self):
        classes = {}
        for key, (cls, args, kwargs, *rest) in self._wcs.world_axis_object_classes.items():
            construct = rest[0] if rest else cls
            converted = {
                index: units
                for i, (k, index, _) in enumerate(self._wcs.world_axis_object_components)
                if k == key and (units := self._units(i))
            }
            if converted:
                construct = self._converting_constructor(construct, cls, len(args), converted)
            classes[key] = (cls, args, kwargs, construct)
        return classes

    @staticmethod
    def _converting_constructor(construct, cls, n_args, converted):
        def convert(*values, **kwargs):
            values = list(values)
            for index, (stored, target) in converted.items():
                value = values[n_args + index]
                if not isinstance(value, cls):  # a bare value in display units, not an already-built object
                    values[n_args + index] = (np.asarray(value) * target).to_value(stored)
            return construct(*values, **kwargs)

        return convert


