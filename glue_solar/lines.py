"""
The main IRIS lines, a Profile viewer button that labels them, the rest wavelength of a spectral window (D11) and the
Doppler velocity from it, as a Profile x unit and top axis.

Wavelengths are NIST ASD vacuum wavelengths in Angstrom: the observed one where NIST gives one, else its Ritz value
(D44). irispy's line database is to replace this table (`wp5-irispy-line-database` in the plan).
"""

import numpy as np
from glue.config import layer_action, viewer_tool
from glue.core import Subset
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

import astropy.units as u

from glue_solar.quicklook import _spectral_axes, _wavelengths, _window

__all__ = ["MAIN_LINES", "DopplerConverter", "LineTool", "VelocityTool", "rest_wavelength", "rest_wavelength_iris"]

MAIN_LINES = (
    ("C II", 1334.5323),
    ("C II", 1335.6628),
    ("C II", 1335.7079),
    ("Fe XII", 1349.40),
    ("Fe XXI", 1354.08),
    ("O I", 1355.5977),  # Ritz
    ("O I", 1358.5123),  # Ritz
    ("Si IV", 1393.76),
    ("Si IV", 1402.77),
    ("Mg II", 2791.599),
    ("Mg II k", 2796.352),
    ("Mg II", 2798.754),  # Ritz
    ("Mg II", 2798.823),
    ("Mg II h", 2803.530),
)

MERGE = 0.01  # lines closer than this fraction of the plotted range share a label
KM_S = u.km / u.s


@viewer_tool
class LineTool(Tool):
    """
    Label the main IRIS lines (`MAIN_LINES`) on a Profile viewer whose x axis is the wavelength of IRIS data: a thin
    marker at each line within the plotted range and its name at the top, in the axis's display unit. Lines too close
    to tell apart at the plotted range share one label. The button switches them off and on; they start on.
    """

    icon = "glue_spectrum"
    tool_id = "solar:lines"
    action_text = "IRIS lines"
    tool_tip = "Show or hide the main IRIS lines"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.shown = True
        self.artists = []
        for prop in ("reference_data", "x_att", "x_display_unit", "x_min", "x_max"):
            viewer.state.add_callback(prop, self.refresh)
        self.refresh()

    def activate(self):
        self.shown = not self.shown
        self.refresh()

    def close(self):
        for prop in ("reference_data", "x_att", "x_display_unit", "x_min", "x_max"):
            self.viewer.state.remove_callback(prop, self.refresh)
        super().close()

    def positions(self):
        """Each label and its x, within the plotted range, or none where the x axis is not an IRIS wavelength."""
        state = self.viewer.state
        data = state.reference_data
        axes = _spectral_axes(data) if data is not None and data.coords is not None else set()
        if not self.shown or len(axes) != 1 or None in (state.x_min, state.x_max):
            return []
        [axis] = axes
        if state.x_att is not data.world_component_ids[axis]:
            return []
        native = u.Unit(data.get_component(state.x_att).units or "Angstrom")
        waves = (np.array([wave for _, wave in MAIN_LINES]) * u.AA).to_value(native)
        x = np.asarray(UnitConverter().to_unit(data, state.x_att, waves, state.x_display_unit), float)
        low, high = sorted((state.x_min, state.x_max))
        labels = []
        for (name, _), at in sorted(zip(MAIN_LINES, x), key=lambda pair: pair[1]):
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
        for label, xs in self.positions():
            for at in xs:
                line = Line2D([at, at], [0, 1], transform=transform, color="0.5", linewidth=0.5, zorder=0)
                self.artists.append(axes.add_artist(line))
            text = Text(np.mean(xs), 0.98, label, transform=transform, rotation=90, ha="right", va="top", fontsize=7,
                        color="0.35")
            self.artists.append(axes.add_artist(text))
        self.viewer.figure.canvas.draw_idle()


def _within(data):
    """The main lines within the wavelengths of ``data``, which has one wavelength axis, as (name, wavelength)."""
    wavelengths, _ = _wavelengths(data)
    return [(name, wave) for name, wave in MAIN_LINES if np.nanmin(wavelengths) <= wave <= np.nanmax(wavelengths)]


def rest_wavelength(data):
    """
    The rest wavelength of the line in ``data``, in Angstrom, or None (D11): ``meta['rest_wavelength']`` where set,
    else the one main line within its wavelengths or, of several, the one nearest the wavelength its window is named
    for, such as 2796 in Mg II k 2796, if within 1 Å; never the window's TWAVE, which is not the line's.
    """
    if data.meta.get("rest_wavelength") is not None:
        return float(data.meta["rest_wavelength"])
    if len(_spectral_axes(data)) != 1:
        return None
    within = [wave for _, wave in _within(data)]
    if len(within) > 1:
        try:
            named = float(str(_window(data)[0]).split()[-1])
        except (IndexError, ValueError):  # no name, or no wavelength in it
            return None
        nearest = min(within, key=lambda wave: abs(wave - named))
        within = [nearest] if abs(nearest - named) <= 1 else []
    return within[0] if within else None


def _doppler_rest(data, cid):
    """The `rest_wavelength` of ``data``, or of a subset's data, where ``cid`` is its wavelength, else None."""
    data = data.data if isinstance(data, Subset) else data
    axes = _spectral_axes(data)
    if len(axes) != 1 or cid is not data.world_component_ids[min(axes)]:
        return None
    return rest_wavelength(data)


class DopplerConverter(SimpleAstropyUnitConverter):
    """
    glue's own unit converter, with 'km / s' too for the wavelength of data with a `rest_wavelength`: the optical
    Doppler velocity from it, c (λ / rest - 1). glue-solar makes it glue's 'default' converter, so a Profile viewer
    offers it as an x unit, after the lengths; data without a rest wavelength get the lengths only.
    """

    def equivalent_units(self, data, cid, units):
        units = list(super().equivalent_units(data, cid, units))
        return units if _doppler_rest(data, cid) is None else [*units, "km / s"]

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
    and glue's x label and tick sizes. 'Set rest wavelength…' moves it and, in every Profile viewer of the data, offers
    'km / s' or not and redraws the profiles in it. The button switches the axis off and on; it starts off.
    """

    icon = "glue_forward"
    tool_id = "solar:velocity"
    action_text = "Velocity axis"
    tool_tip = "Show or hide a top axis of the Doppler velocity from the rest wavelength"

    WATCHED = ("reference_data", "x_att", "x_display_unit", "x_axislabel_size", "x_ticklabel_size")

    def __init__(self, viewer):
        super().__init__(viewer)
        self.shown = False
        self.axis = None
        for prop in self.WATCHED:
            viewer.state.add_callback(prop, self.refresh)
        self._hub = viewer.session.hub
        self._hub.subscribe(self, DataUpdateMessage, handler=self._rest_changed, filter=self._is_reference_meta)
        viewer.destroyed.connect(self._forget)  # also for a viewer torn down without closing its tools

    def activate(self):
        self.shown = not self.shown
        self.refresh()

    def close(self):
        self._forget()
        for prop in self.WATCHED:
            self.viewer.state.remove_callback(prop, self.refresh)
        super().close()

    def _forget(self, *_):
        self._hub.unsubscribe_all(self)

    def _is_reference_meta(self, message):
        return message.attribute == "meta" and message.sender is self.viewer.state.reference_data

    def _rest_changed(self, message):
        state = self.viewer.state
        if state.x_att is None:
            return
        unit = state.x_display_unit
        lost = unit == "km / s" and _doppler_rest(state.reference_data, state.x_att) is None
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
        rest = None
        if self.shown and state.reference_data is not None and state.x_display_unit:
            if u.Unit(state.x_display_unit).is_equivalent(u.AA):
                rest = _doppler_rest(state.reference_data, state.x_att)
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
            self.axis.set_xlabel(f"Velocity from {rest} Å [km / s]", size=state.x_axislabel_size)
            self.axis.tick_params(labelsize=state.x_ticklabel_size)
        axes.resizer.on_resize(None)  # also draws


def _wavelength(text):
    """``text``, typed in Angstrom, as a float."""
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"'{text}' is not a wavelength in Angstrom, such as 1402.77.") from None


@layer_action(
    "Set rest wavelength…",
    single=True,
    data=True,
    tooltip="Set the rest wavelength of the line in this spectral window, which the line dialogs start from",
)
@messagebox_on_error("Could not set the rest wavelength")
def rest_wavelength_iris(data, data_collection):
    """
    Set ``meta['rest_wavelength']`` of ``data`` to a main line within it picked or a wavelength typed in Angstrom, or
    remove it for a blank one; the dialog starts at its `rest_wavelength`. glue shows why for data without one
    wavelength axis.
    """
    if len(_spectral_axes(data)) != 1:
        raise ValueError(f"{data.label} has no wavelength axis.")
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
