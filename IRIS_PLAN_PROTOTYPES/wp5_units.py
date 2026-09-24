"""WP5 (a) shipping code: velocity display units for IRIS spectral windows (target: glue_solar/viewers.py)."""
import astropy.units as u
from glue.config import unit_converter
from glue.core.units import SimpleAstropyUnitConverter

WAVELENGTH_UNITS = ("Angstrom", "nm")   # ponytail: fixed short list instead of astropy's 131 prefixed length units
ANGLE_UNITS = ("arcsec", "arcmin", "deg")
VELOCITY_UNIT = "km / s"


def rest_wavelength(data):
    """Rest wavelength of a dataset's spectral window as a Quantity, or None.

    ``meta['rest_wavelength']`` (a float in Angstrom; written by the loader for 4-D stacks or by the
    user override) wins over irispy's ``SGMeta.rest_wavelength`` (derived from the TWAVE card).
    """
    meta = getattr(data, "meta", None)
    if meta is None:
        return None
    try:
        rest = meta["rest_wavelength"] if "rest_wavelength" in meta else meta.rest_wavelength
    except (AttributeError, TypeError, ValueError):  # plain dict, or irispy 0.8.1 with no TWAVE card (float(None))
        rest = None
    return None if rest is None else u.Quantity(rest, u.AA)


class IRISUnitConverter(SimpleAstropyUnitConverter):
    """glue's default converter plus wavelength <-> velocity for datasets with a rest wavelength."""

    def _equivalencies(self, data):
        rest = rest_wavelength(data)
        return [] if rest is None else u.doppler_optical(rest)

    def equivalent_units(self, data, cid, units):
        unit = u.Unit(units)
        if unit.is_equivalent(u.m):
            velocity = [VELOCITY_UNIT] if rest_wavelength(data) is not None else []
            return [x for x in WAVELENGTH_UNITS if x != units] + velocity
        if unit.is_equivalent(u.deg):
            return [x for x in ANGLE_UNITS if x != units]
        return super().equivalent_units(data, cid, units)

    def to_unit(self, data, cid, values, original_units, target_units):
        return (values * u.Unit(original_units)).to_value(target_units, equivalencies=self._equivalencies(data))


def install():
    # Override the built-in 'default' entry. Do NOT register a new name and point settings.UNIT_CONVERTER
    # at it: glue-qt persists that setting to ~/.glue/settings.cfg and `import glue` then fails with
    # KeyError (glue/config.py:938) whenever the plugin is not importable at startup.
    unit_converter.members["default"] = IRISUnitConverter


install()
