"""
Coordination of the Image viewers that show one IRIS observation.
"""

from contextlib import contextmanager

import numpy as np
from glue.core.hub import HubListener
from glue.core.message import SubsetCreateMessage, SubsetUpdateMessage
from glue.core.subset import SubsetState
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.viewers.image.state import AggregateSlice

__all__ = ["Coordinator", "coordinator", "observation_key"]


def observation_key(data):
    """
    The ``(OBSID, STARTOBS)`` pair that identifies the IRIS observation ``data`` belongs to, or None.

    The OBSID alone names an observing program, which runs many times, so both are needed.
    """
    meta = getattr(data, "meta", None) or {}
    obsid, start = meta.get("OBSID"), meta.get("STARTOBS")
    if obsid is None or start is None:
        return None
    try:
        start = np.datetime64(str(start), "ns")
    except ValueError:
        return None
    # AIA cutouts spell the OBSID as date_time_obsid
    return None if np.isnat(start) else (str(obsid).split("_")[-1], start)


def coordinator(data_collection):
    """The `Coordinator` of ``data_collection``, created on first use and kept on the collection."""
    if not hasattr(data_collection, "_solar_coordinator"):
        # the hub holds its listeners weakly
        data_collection._solar_coordinator = Coordinator(data_collection)
    return data_collection._solar_coordinator


def _spectral_axes(data):
    """The array axes of ``data`` along which the wavelength varies."""
    wcs = data.coords
    types = getattr(wcs, "world_axis_physical_types", None) or ()
    matrix = getattr(wcs, "axis_correlation_matrix", None)
    return {
        data.ndim - 1 - pixel  # APE 14 orders pixel axes opposite to numpy
        for world, kind in enumerate(types)
        if kind == "em.wl"
        for pixel in np.nonzero(matrix[world])[0]
    }


def _shown(state):
    """The array axes an Image viewer state displays."""
    return {att.axis for att in (state.x_att, state.y_att) if att is not None}


class Coordinator(HubListener):
    """
    Keep the Image viewers of each IRIS observation on one selected point.

    The point is the Pixel tool's selection: the coordinator follows the last subset group given a
    `~glue.viewers.image.pixel_selection_subset_state.PixelSubsetState` on IRIS data. On a
    spectral cube the point fixes every axis but wavelength, so a click takes the axes the clicked
    viewer does not show, such as a stack's scan, from its sliders, and a viewer of that cube
    whose displayed axes change moves its new sliders to the point. Wavelength sliders are never
    moved. Each data collection has one coordinator (`coordinator`), and the ``solar:coordinate``
    tool registers every Image viewer with it.
    """

    def __init__(self, data_collection):
        self.data_collection = data_collection
        self.group = None
        self.masters = {}  # observation key -> the dataset chosen as its time master
        self._viewers = {}  # registered viewer -> its callback
        self._busy = False
        hub = data_collection.hub
        hub.subscribe(self, SubsetCreateMessage, handler=self._subset_changed)
        hub.subscribe(
            self, SubsetUpdateMessage, handler=self._subset_changed, filter=lambda m: m.attribute == "subset_state"
        )

    @property
    def point(self):
        """The followed group's subset state if it is still a Pixel selection, else None."""
        group = self.group
        if group is None or group not in self.data_collection.subset_groups:
            return None
        state = group.subset_state
        return state if isinstance(state, PixelSubsetState) else None

    def register(self, viewer):
        """Coordinate ``viewer``, an Image viewer of this data collection."""
        if viewer in self._viewers:
            return

        def callback(*_):
            self._apply_point(viewer)

        for prop in ("reference_data", "x_att", "y_att"):
            viewer.state.add_callback(prop, callback)
        self._viewers[viewer] = callback

    def unregister(self, viewer):
        """Stop coordinating ``viewer``; unregistering it again does nothing."""
        callback = self._viewers.pop(viewer, None)
        if callback is not None:
            for prop in ("reference_data", "x_att", "y_att"):
                viewer.state.remove_callback(prop, callback)

    def set_master(self, data):
        """Make ``data`` the time master of its observation."""
        key = observation_key(data)
        if key is not None:
            self.masters[key] = data

    def clear_point(self):
        """Empty the followed group, which hides its crosshairs."""
        if self.point is not None:
            self.group.subset_state = SubsetState()

    @contextmanager
    def _writing(self):
        self._busy = True
        try:
            yield
        finally:
            self._busy = False

    def _subset_changed(self, message):
        subset = message.subset
        state = subset.subset_state
        # a group sends one message per dataset; answer the one of the point's own dataset
        if self._busy or not isinstance(state, PixelSubsetState) or subset.data is not state.reference_data:
            return
        group = getattr(subset, "group", None)
        if group is None or observation_key(subset.data) is None:
            return
        self.group = group
        self._pin(state)

    def _pin(self, state):
        """Fix the point's free axes, wavelength aside, at the sliders of the viewer it was clicked in."""
        data = state.reference_data
        spectral = _spectral_axes(data)
        if not spectral:
            return  # a slit-jaw point is a detector pixel in every frame
        clicked = {axis for axis, s in enumerate(state.slices) if s.start is not None}
        # ponytail: the first viewer that shows the clicked axes; ask the Pixel tool which one if two ever do
        viewer = next((v for v in self._viewers if v.state.reference_data is data and _shown(v.state) == clicked), None)
        if viewer is None:
            return
        slices = list(state.slices)
        for axis, s in enumerate(state.slices):
            if s.start is None and axis not in spectral:
                index = getattr(viewer.state.slices[axis], "center", viewer.state.slices[axis])
                slices[axis] = slice(index, index + 1)
        if slices != list(state.slices):
            with self._writing():
                self.group.subset_state = PixelSubsetState(data, slices)

    def _apply_point(self, viewer):
        """Move the viewer's sliders along the point's fixed axes to the point, wavelength aside."""
        state, point = viewer.state, self.point
        data, shown = state.reference_data, _shown(state)
        # mid-way through an axis change a viewer can show fewer than two axes
        if self._busy or point is None or data is not point.reference_data or len(shown) < 2:
            return
        if len(state.slices) != data.ndim:
            return
        spectral = _spectral_axes(data)
        slices = list(state.slices)
        for axis, s in enumerate(point.slices):
            # a Profile's collapse leaves an AggregateSlice, which stays
            if s.start is not None and axis not in (shown | spectral) and not isinstance(slices[axis], AggregateSlice):
                slices[axis] = s.start
        if slices != list(state.slices):
            with self._writing():
                state.slices = tuple(slices)
