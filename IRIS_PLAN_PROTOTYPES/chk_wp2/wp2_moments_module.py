"""
Line moments of an IRIS raster window, computed by irispy and added as one linked 2D dataset.
"""

import numpy as np
from glue.core.component import Component
from glue.core.link_helpers import LinkSame
from glue_qt.config import layer_action
from irispy.spectrograph import SpectrogramCube
from irispy.utils.constants import DN_UNIT
from irispy.utils.moments import calculate_moments
from qtpy import QtWidgets

import astropy.units as u

from glue_solar.sources.loaders.iris import _cube_data

__all__ = ["MomentsDialog", "line_moments", "moments_action"]


def _in_angstrom(cube):
    """D3: wavelengths in Angstrom. irispy reports nm (centroid, width) and DN nm (integrated intensity)."""
    unit = cube.unit
    return cube.to(u.CompositeUnit(1, [u.AA if base == u.nm else base for base in unit.bases], unit.powers))


def line_moments(data, *, rest_wavelength=None, wings=None, integrated=False, min_intensity=None, saturation_limit=None):
    """Run irispy's ``calculate_moments`` on one per-scan raster window; return one 2D Data with five components."""
    if data.ndim != 3 or "em.wl" not in data.coords.world_axis_physical_types:
        msg = "Line moments need a per-scan raster window (raster step, slit, wavelength). Load scans without stacking."
        raise ValueError(msg)
    cid = data.main_components[0]
    mask_cid = data.find_component_id(f"{cid.label} mask")
    with u.add_enabled_units(list(DN_UNIT.values())):  # DN_IRIS_* are irispy-defined units
        cube = SpectrogramCube(data[cid], data.coords._wcs, None, u.Unit(data.get_component(cid).units), data.meta,
                               mask=None if mask_cid is None else data[mask_cid])
        if integrated and min_intensity is not None:
            min_intensity = min_intensity * cube.unit * u.AA  # the integrated zeroth moment is DN Angstrom, not DN
        maps = calculate_moments(cube, rest_wavelength=rest_wavelength, wings=wings, integrated=integrated,
                                 min_intensity=min_intensity, saturation_limit=saturation_limit)
        maps = [(name, _in_angstrom(cube)) for name, cube in maps.items()]
    (first_name, first), *rest = maps
    result = _cube_data(first, first_name)  # component named after the map; coords, mask and Time come for free
    result.label = f"{data.label}-moments"
    for name, cube in rest:
        result.add_component(Component(np.asarray(cube.data), units=str(cube.unit)), name)
    if data.find_component_id("Time") is not None:  # the rewrap drops irispy's time extra coord; copy the loader's per-step times
        result.add_component(data["Time"][..., 0], "Time")
    return result


def _number(line_edit):
    text = line_edit.text().strip()
    return float(text) if text else None


class MomentsDialog(QtWidgets.QDialog):
    """Ask for the calculate_moments parameters, run, add the result to the data collection and link it."""

    def __init__(self, data, data_collection, parent=None):
        super().__init__(parent)
        self.data, self.data_collection, self.moments = data, data_collection, None  # not 'result': QDialog.result() is a method
        self.setWindowTitle(f"Line moments of {data.label}")
        self.rest, self.low, self.high, self.minimum, self.saturation = (QtWidgets.QLineEdit() for _ in range(5))
        self.integrated = QtWidgets.QCheckBox("Integrate over wavelength (unit DN Angstrom) instead of summing (DN)")
        try:
            self.rest.setText(f"{data.meta.rest_wavelength.to_value(u.AA):.2f}")
        except (AttributeError, TypeError, ValueError):
            pass  # no TWAVE (or dict meta): the user types it
        form = QtWidgets.QFormLayout(self)
        form.addRow("Rest wavelength [Angstrom]", self.rest)
        form.addRow("Blue wing, Angstrom below rest (blank = whole window)", self.low)
        form.addRow("Red wing, Angstrom above rest", self.high)
        form.addRow("Minimum zeroth moment [DN, or DN Angstrom when integrating]", self.minimum)
        form.addRow("Saturation limit, peak [DN]", self.saturation)
        form.addRow(self.integrated)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.run)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def run(self):
        try:
            rest, low, high = _number(self.rest), _number(self.low), _number(self.high)
            if (low is None) != (high is None):
                raise ValueError("Enter both wings, or leave both blank to use the whole window.")
            self.moments = line_moments(
                self.data,
                rest_wavelength=None if rest is None else rest * u.AA,
                wings=None if low is None else (low * u.AA, high * u.AA),
                integrated=self.integrated.isChecked(),
                min_intensity=_number(self.minimum),
                saturation_limit=_number(self.saturation),
            )
        except Exception as error:  # noqa: BLE001 - show irispy's message and keep the dialog open
            QtWidgets.QMessageBox.critical(self, "Line moments failed", str(error))
            return
        self.data_collection.append(self.moments)
        for source, target in zip(self.data.pixel_component_ids[:2], self.moments.pixel_component_ids):
            self.data_collection.add_link(LinkSame(source, target))  # maps share the raster's (step, slit) pixel grid
        self.accept()


@layer_action("IRIS: line moments…", single=True, data=True)
def moments_action(layer, data_collection):
    """Right-click on a raster dataset: compute line moments with irispy and add the maps as one linked dataset."""
    MomentsDialog(layer, data_collection, parent=QtWidgets.QApplication.activeWindow()).exec()
