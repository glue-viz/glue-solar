"""
The main IRIS lines, and a Profile viewer button that labels them.

Wavelengths are NIST ASD vacuum wavelengths in Angstrom: the observed one where NIST gives one, else its Ritz value
(D44). irispy's line database is to replace this table (`wp5-irispy-line-database` in the plan).
"""

import numpy as np
from glue.config import viewer_tool
from glue.core.units import UnitConverter
from glue.viewers.common.tool import Tool
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.transforms import blended_transform_factory

import astropy.units as u

from glue_solar.quicklook import _spectral_axes

__all__ = ["MAIN_LINES", "LineTool"]

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
