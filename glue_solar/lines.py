"""
The main IRIS lines, a Profile viewer button that labels them, the rest wavelength of a spectral window (D11) and the
Doppler velocity from it, as a Profile x unit and top axis.

The main lines are the documented IRIS lines of irispy's line catalog, at its vacuum wavelengths in Angstrom (D44).
"""

import os
from functools import cache

import numpy as np
from glue.config import viewer_tool
from glue.core import Subset
from glue.core.data import Data
from glue.core.hub import HubListener
from glue.core.message import DataUpdateMessage
from glue.core.units import SimpleAstropyUnitConverter, UnitConverter
from glue.viewers.common.tool import Tool
from glue.viewers.profile.state import ProfileViewerState
from glue_qt.utils.decorators import messagebox_on_error
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.transforms import blended_transform_factory
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u

from glue_solar.glue_patches import layer_action
from glue_solar.quicklook import _spectral_axes, _wavelengths, _window

__all__ = [
    "DopplerConverter",
    "LineTool",
    "LinesInRangeTool",
    "VelocityTool",
    "main_lines",
    "rest_wavelength",
    "rest_wavelength_iris",
]

_NAMES = {2796.352: "Mg II k", 2803.53: "Mg II h"}  # irispy names both "Mg II"


@cache
def main_lines():
    """irispy's documented IRIS lines, as (name, wavelength in Angstrom), read at first use rather than at launch."""
    from irispy.utils.lines import get_lines

    lines = get_lines(main_only=True)
    waves = lines["wavelength"].to_value(u.AA).tolist()
    return tuple((_NAMES.get(wave, str(ion)), wave) for ion, wave in zip(lines["ion"], waves, strict=True))


MERGE = 0.01  # lines closer than this fraction of the plotted range share a label
KM_S = u.km / u.s


def _icon(name):
    """The file of glue-solar's icon ``name``: glue-qt's toolbar takes a path as a tool's ``icon``."""
    return os.path.join(os.path.dirname(__file__), "icons", f"{name}.png")


def _check(tool):
    """Check the Profile viewer button of ``tool``, a plain tool, while it is ``shown``."""
    action = tool.viewer.toolbar.actions[tool.tool_id]
    action.setCheckable(True)
    action.setChecked(tool.shown)


@viewer_tool
class LineTool(Tool):
    """
    Label the main IRIS lines (`main_lines`) on a Profile viewer whose x axis is the wavelength of IRIS data: a thin
    marker at each line within the plotted range and its name at the top, in the axis's display unit, less the main
    lines unticked in 'Lines in this range…' (`hidden`) and with the lines ticked there (`labeled`) (D98). Lines too
    close to tell apart at the plotted range share one label; a label that would overlap another goes below it. The
    button, checked while they show, switches them off and on; they start on.
    """

    icon = "glue_spectrum"
    tool_id = "solar:lines"
    action_text = "IRIS lines"
    tool_tip = "Show or hide the main IRIS lines"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.shown = True
        self.artists = []
        self.labeled = []  # (name, wavelength in Angstrom) of lines ticked in 'Lines in this range…'
        self.hidden = set()  # the wavelengths of main lines unticked there
        for prop in ("reference_data", "x_att", "x_display_unit", "x_min", "x_max"):
            viewer.state.add_callback(prop, self.refresh)
        self._resized = viewer.figure.canvas.mpl_connect("resize_event", self.refresh)  # the labels' overlaps change
        self.refresh()
        viewer.toolbar_added.connect(lambda: _check(self))

    def activate(self):
        self.shown = not self.shown
        self.refresh()
        _check(self)

    def close(self):
        for prop in ("reference_data", "x_att", "x_display_unit", "x_min", "x_max"):
            self.viewer.state.remove_callback(prop, self.refresh)
        self.viewer.figure.canvas.mpl_disconnect(self._resized)
        super().close()

    def positions(self):
        """Each label and its x, within the plotted range, or none where the x axis is not an IRIS wavelength."""
        state = self.viewer.state
        if not self.shown or not _shows_wavelength(state) or None in (state.x_min, state.x_max):
            return []
        data, lines = state.reference_data, [line for line in main_lines() if line[1] not in self.hidden] + self.labeled
        native = u.Unit(data.get_component(state.x_att).units or "Angstrom")
        waves = (np.array([wave for _, wave in lines]) * u.AA).to_value(native)
        x = np.asarray(UnitConverter().to_unit(data, state.x_att, waves, state.x_display_unit), float)
        low, high = sorted((state.x_min, state.x_max))
        labels = []
        for (name, _), at in sorted(zip(lines, x), key=lambda pair: pair[1]):
            if low <= at <= high:
                if labels and at - labels[-1][1][-1] < MERGE * (high - low):
                    if name not in labels[-1][0]:
                        labels[-1][0].append(name)
                    labels[-1][1].append(at)
                else:
                    labels.append(([name], [at]))
        return [(", ".join(names), xs) for names, xs in labels]

    def refresh(self, *_):
        for artist in self.artists:
            artist.remove()
        self.artists = []
        axes = self.viewer.axes
        transform = blended_transform_factory(axes.transData, axes.transAxes)
        boxes = []  # the labels' extents on screen
        for label, xs in self.positions():
            for at in xs:
                line = Line2D([at, at], [0, 1], transform=transform, color="0.5", linewidth=0.5, zorder=0)
                self.artists.append(axes.add_artist(line))
            text = Text(np.mean(xs), 0.98, label, transform=transform, rotation=90, ha="right", va="top", fontsize=7,
                        color="0.35")
            self.artists.append(axes.add_artist(text))
            box = text.get_window_extent()
            # below the lowest label it would overlap, such as Mg II k's and the triplet's on a narrow panel (P8)
            below = [other.y0 for other in boxes if other.x0 < box.x1 and box.x0 < other.x1]
            if below:
                text.set_y(axes.transAxes.inverted().transform((0, min(below) - 2))[1])
                box = text.get_window_extent()
            boxes.append(box)
        self.viewer.figure.canvas.draw_idle()


def _shows_wavelength(state):
    """Whether a Profile viewer plots against the one wavelength axis of its reference data."""
    data = state.reference_data
    axes = _spectral_axes(data) if data is not None and data.coords is not None else set()
    return len(axes) == 1 and state.x_att is data.world_component_ids[next(iter(axes))]


_REGIONS = {"Quiet Sun": "quiet_sun", "Active region": "active_region", "Flare": "flare"}


@viewer_tool
class LinesInRangeTool(Tool):
    """
    List the lines of irispy's catalog within a Profile viewer's Fit and Collapse range, else its plotted range,
    strongest first in a region type's model at coronal or photospheric abundances, lines it predicts no strength for
    after (D44, D97), each ticked while `LineTool` shows it: a tick labels a line beside the main lines, an untick hides
    one, a main line too (D98).
    """

    #: :meta hide-value:
    icon = _icon("solar_lines_in_range")
    tool_id = "solar:lines_in_range"
    action_text = "Lines in this range…"
    tool_tip = "List the IRIS lines in the Fit range, else in the plotted range, strongest first"
    dialog = None

    @messagebox_on_error("Could not list the lines")
    def activate(self):
        from irispy.utils.lines import get_lines

        if self.dialog is not None:  # one list per viewer, of the range it was asked for last (D98)
            self.dialog.close()
        state = self.viewer.state
        if not _shows_wavelength(state):
            raise ValueError("Plot IRIS data against its wavelength first")
        mode = self.viewer.toolbar.tools["profile-analysis"]._profile_tools.rng_mode
        ends = mode.state.x_range if mode.active and None not in mode.state.x_range else (state.x_min, state.x_max)
        data = state.reference_data
        native = u.Unit(data.get_component(state.x_att).units or "Angstrom")
        ends = UnitConverter().to_native(data, state.x_att, np.array(ends, float), state.x_display_unit) * native
        low, high = sorted(ends.to_value(u.AA))
        self.dialog = dialog = QtWidgets.QDialog(self.viewer, windowTitle=f"IRIS lines in {low:.2f}–{high:.2f} Å")
        region, abundance, listing = QtWidgets.QComboBox(), QtWidgets.QComboBox(), QtWidgets.QListWidget()
        region.addItems(_REGIONS)
        abundance.addItems(["Coronal", "Photospheric"])
        layout = QtWidgets.QFormLayout(dialog)
        layout.addRow("Strongest in", region)
        layout.addRow("Abundances", abundance)
        layout.addRow(listing)

        lines, main = self.viewer.toolbar.tools[LineTool.tool_id], {wave for _, wave in main_lines()}

        def fill(*_):
            model = _REGIONS[region.currentText()], abundance.currentText().lower()
            catalog = get_lines([low, high] * u.AA, region=model[0], abundance=model[1], minimum_strength=0)
            listing.clear()
            strengths = np.asarray(catalog["intensity_{}_{}".format(*model)], float)
            for ion, wave, strength in zip(catalog["ion"], catalog["wavelength"].to_value(u.AA).tolist(), strengths):
                item = QtWidgets.QListWidgetItem(f"{ion} {wave:.3f} Å" + (f", {strength:.2g}" if strength >= 0 else ""))
                item.setData(Qt.UserRole, (str(ion), wave))
                shown = wave not in lines.hidden if wave in main else (str(ion), wave) in lines.labeled
                item.setCheckState(Qt.Checked if shown else Qt.Unchecked)  # before it is listed: no itemChanged
                listing.addItem(item)

        def tick(item):
            line, on = item.data(Qt.UserRole), item.checkState() == Qt.Checked
            if line[1] in main:
                (lines.hidden.discard if on else lines.hidden.add)(line[1])
            elif on:
                lines.labeled.append(line)
            elif line in lines.labeled:  # not when the catalog lists it twice, as a multiplet's components
                lines.labeled.remove(line)
            lines.shown = True
            lines.refresh()
            _check(lines)

        region.currentTextChanged.connect(fill)
        abundance.currentTextChanged.connect(fill)
        listing.itemChanged.connect(tick)
        fill()
        dialog.show()


def _within(data):
    """The main lines within the wavelengths of ``data``, which has one wavelength axis, as (name, wavelength)."""
    wavelengths, _ = _wavelengths(data)
    return [(name, wave) for name, wave in main_lines() if np.nanmin(wavelengths) <= wave <= np.nanmax(wavelengths)]


def rest_wavelength(data):
    """
    The rest wavelength of the line in ``data``, in Angstrom, or None (D11): ``meta['rest_wavelength']`` where set,
    else the one main line within its wavelengths or, of several, the one of the window's own ion (C I 1355.85 is
    nearer 1356 than O I 1355.60) nearest the wavelength its window is named for, such as 2796 in Mg II k 2796, if
    within 1 Å; never the window's TWAVE, which is not the line's.
    """
    if data.meta.get("rest_wavelength") is not None:
        return float(data.meta["rest_wavelength"])
    if len(_spectral_axes(data)) != 1:
        return None
    within = _within(data)
    if len(within) > 1:
        title = str(_window(data)[0])
        try:
            named = float(title.split()[-1])
        except (IndexError, ValueError):  # no name, or no wavelength in it
            return None
        within = [line for line in within if title.startswith(f"{line[0]} ")] or within
        nearest = min((wave for _, wave in within), key=lambda wave: abs(wave - named))
        return nearest if abs(nearest - named) <= 1 else None
    return within[0][1] if within else None


def _doppler_rest(data, cid):
    """The `rest_wavelength` of ``data``, or of a subset's data, where ``cid`` is its wavelength, else None."""
    data = data.data if isinstance(data, Subset) else data
    axes = _spectral_axes(data)
    if len(axes) != 1 or cid is not data.world_component_ids[min(axes)]:
        return None
    return rest_wavelength(data)


class DopplerConverter(SimpleAstropyUnitConverter):
    """
    glue's own unit converter, with `VELOCITY` too for the wavelength of data with a `rest_wavelength`: the optical
    Doppler velocity from it, c (λ / rest - 1). glue-solar makes it glue's 'default' converter, so a Profile viewer
    offers it as an x unit, after the lengths; data without a rest wavelength get the lengths only.
    """

    VELOCITY = KM_S.to_string()  # 'km / s', as glue lists units

    def equivalent_units(self, data, cid, units):
        units = list(super().equivalent_units(data, cid, units))
        return units if _doppler_rest(data, cid) is None else [*units, self.VELOCITY]

    def to_unit(self, data, cid, values, original_units, target_units):
        try:
            return super().to_unit(data, cid, values, original_units, target_units)
        except u.UnitConversionError:  # a wavelength to or from km / s
            rest = _doppler_rest(data, cid)
            if rest is None:
                raise
            return (values * u.Unit(original_units)).to_value(target_units, u.doppler_optical(rest * u.AA))


@viewer_tool
class VelocityTool(Tool, HubListener):
    """
    A top axis of the Doppler velocity, as the x unit 'km / s' gives it (`DopplerConverter`), on a Profile viewer
    whose x axis is the wavelength of data with a `rest_wavelength`, in a length unit. It follows the x range and unit
    and glue's x label and tick sizes. 'Set rest wavelength…' moves it and, in every Profile viewer of the data,
    offers 'km / s' or not and redraws the profiles in it. The button, checked while it is on and grayed without a rest
    wavelength, switches the axis off and on; it starts off. It also gives glue's axes their units (`_label_x`,
    `_unit_y`).
    """

    #: :meta hide-value:
    icon = _icon("solar_velocity_axis")
    tool_id = "solar:velocity"
    action_text = "Velocity axis"
    tool_tip = "Show or hide a top axis of the Doppler velocity from the rest wavelength"

    WATCHED = ("reference_data", "x_att", "x_display_unit", "x_axislabel_size", "x_ticklabel_size")
    # after glue's own x label, which these reset
    LABELED = ("reference_data", "x_att", "x_display_unit", "y_display_unit", "normalize")

    def __init__(self, viewer):
        super().__init__(viewer)
        self.shown = False
        self.axis = None
        for prop in self.WATCHED:
            viewer.state.add_callback(prop, self.refresh)
        for prop in self.LABELED:
            viewer.state.add_callback(prop, self._label_x)
        self._shown = None  # the layers and attributes `_unit_y` last saw
        viewer.state.add_callback("layers", self._unit_y)  # after glue's own y unit choices
        self._label_x()
        self._unit_y()
        self._hub = viewer.session.hub
        self._hub.subscribe(self, DataUpdateMessage, handler=self._rest_changed, filter=self._is_reference_meta)
        viewer.destroyed.connect(self._forget)  # also for a viewer torn down without closing its tools
        viewer.toolbar_added.connect(self.refresh)

    def activate(self):
        self.shown = not self.shown
        self.refresh()

    def close(self):
        self._forget()
        for prop in self.WATCHED:
            self.viewer.state.remove_callback(prop, self.refresh)
        for prop in self.LABELED:
            self.viewer.state.remove_callback(prop, self._label_x)
        self.viewer.state.remove_callback("layers", self._unit_y)
        super().close()

    def _forget(self, *_):
        self._hub.unsubscribe_all(self)

    def _label_x(self, *_):
        """glue's x label with its display unit, which glue leaves out, such as 'Wavelength [Angstrom]' (D90)."""
        state = self.viewer.state
        if state.x_att is not None and state.x_display_unit:
            state.x_axislabel = f"{state.x_att.label} [{state.x_display_unit}]"

    def _unit_y(self, *_):
        """
        The layers' one unit as the y display unit, so glue labels the axis 'Data values [DN / s]' (D90), as their data or
        attributes change and while it is glue's 'Native units'; glue offers the units of its Data layers only.
        """
        if self.viewer is None:  # closed by an earlier callback of the same change, glue's layer-artist sync
            return
        state = self.viewer.state
        shown = [(id(layer.layer), id(layer.attribute)) for layer in state.layers]  # as glue checks them
        if shown == self._shown:
            return
        self._shown = shown
        layers = [(layer.layer.data, layer.attribute) for layer in state.layers]
        # glue's own data only, not a path diagram's
        units = {data.get_component(att).units for data, att in layers if isinstance(data, Data) and att is not None}
        units -= {"", None}
        if state.y_display_unit is None and len(units) == 1:
            [unit] = units
            if unit in ProfileViewerState.y_display_unit.get_choices(state):
                state.y_display_unit = unit

    def _is_reference_meta(self, message):
        return message.attribute == "meta" and message.sender is self.viewer.state.reference_data

    def _rest_changed(self, message):
        state = self.viewer.state
        if state.x_att is None:
            return
        unit = state.x_display_unit
        lost = unit == DopplerConverter.VELOCITY and _doppler_rest(state.reference_data, state.x_att) is None
        if lost:  # glue cannot convert the x range from km / s now
            state._previous_x_att = None
        state._update_x_display_unit_choices()  # glue's own, which sets the data's unit
        if lost:
            state._reset_x_limits()
        elif unit in ProfileViewerState.x_display_unit.get_choices(state):
            state.x_display_unit = unit  # glue converts the x range and redraws the profiles
        self.refresh()

    def refresh(self, *_):
        state, axes = self.viewer.state, self.viewer.axes
        rest = None if state.reference_data is None else _doppler_rest(state.reference_data, state.x_att)
        if self.tool_id in self.viewer.toolbar.actions:  # once glue-qt has added the button
            _check(self)
            self.viewer.toolbar.actions[self.tool_id].setEnabled(rest is not None)
        if not (self.shown and state.x_display_unit and u.Unit(state.x_display_unit).is_equivalent(u.AA)):
            rest = None
        if rest is None and self.axis is None:
            return
        if rest is None:
            self.axis.remove()
            self.axis = None
            axes.resizer.margins = self.margins
        else:
            unit, doppler = u.Unit(state.x_display_unit), u.doppler_optical(rest * u.AA)
            functions = (lambda x: (x * unit).to_value(KM_S, doppler), lambda v: (v * KM_S).to_value(unit, doppler))
            if self.axis is None:
                self.margins = axes.resizer.margins
                axes.resizer.margins = [*self.margins[:3], 0.5]  # glue's bottom margin, for the ticks and label
                self.axis = axes.secondary_xaxis("top", functions=functions)
            else:
                self.axis.set_functions(functions)
            self.axis.set_xlabel(f"Velocity from {rest} Å [{DopplerConverter.VELOCITY}]", size=state.x_axislabel_size)
            self.axis.tick_params(labelsize=state.x_ticklabel_size)
        axes.resizer.on_resize(None)  # also draws


def _wavelength(text):
    """``text``, typed in Angstrom, as a float."""
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"'{text}' is not a wavelength in Angstrom, such as 1402.77.") from None


def _check_wavelength(data):
    """Raise why ``data`` has not one wavelength axis."""
    if len(_spectral_axes(data)) != 1:
        raise ValueError(f"{data.label} has no wavelength axis.")


@layer_action(
    "Set rest wavelength…",
    single=True,
    data=True,
    check=_check_wavelength,
    tooltip="Set the rest wavelength of the line in this spectral window, which the line dialogs start from",
)
@messagebox_on_error("Could not set the rest wavelength")
def rest_wavelength_iris(data, data_collection):
    """Set ``meta['rest_wavelength']`` of ``data`` to a main line picked or a wavelength typed, or remove it for none."""
    _check_wavelength(data)
    choices = {f"{name} {wave}": wave for name, wave in _within(data)}
    rest = rest_wavelength(data)
    shown = next((text for text, wave in choices.items() if wave == rest), "" if rest is None else str(rest))
    items = list(choices) if shown in choices else [shown, *choices]
    title, label = f"Rest wavelength of {data.label}", "Rest wavelength [Å], blank for the main line's:"
    text, ok = QtWidgets.QInputDialog.getItem(
        QtWidgets.QApplication.activeWindow(), title, label, items, items.index(shown), True
    )
    text = text.strip()
    if ok and text:
        data.meta["rest_wavelength"] = choices[text] if text in choices else _wavelength(text)
    elif ok:
        data.meta.pop("rest_wavelength", None)
    if ok:
        data.broadcast("meta")  # for the Profile viewers' velocities (`VelocityTool`)
