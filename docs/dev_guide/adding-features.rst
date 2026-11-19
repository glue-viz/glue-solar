.. _glue_solar_dev_docs_adding_features:

===============
Adding features
===============

Each kind of feature below has an example, which ``glue_solar/tests/test_documented_workflows.py``
runs line for line.

A data action
-------------

A data action is an entry in a dataset's right-click menu: a function of the dataset and the data
collection, registered with ``layer_action`` from ``glue_solar.glue_patches``. Its ``check`` raises a
``ValueError`` saying why it refuses a dataset: the entry shows only for the data it takes, and the
action calls it first. ``single=True`` and ``data=True`` are glue's own, for one dataset selected.
``messagebox_on_error`` shows an error in a box. A label starts with "IRIS: " where the action takes
IRIS data only.

This one says a slit-jaw image's cadence in glue's status bar::

    import numpy as np
    from glue_qt.utils.decorators import messagebox_on_error

    from glue_solar import describe
    from glue_solar.glue_patches import layer_action
    from glue_solar.sources import analysis


    def _check(data):
        """Raise why ``data`` is not an IRIS slit-jaw image."""
        if describe.role(data) != "sji":
            raise ValueError(f"{data.label} is not an IRIS slit-jaw image.")


    @layer_action(
        "IRIS: cadence",
        single=True,
        data=True,
        check=_check,
        tooltip="Show the median time between the frames of this slit-jaw image",
    )
    @messagebox_on_error("Could not show the cadence")
    def cadence_iris(data, data_collection):
        """Say the median time between the frames of ``data`` in glue's status bar."""
        _check(data)
        seconds = describe.cadence(data["Time"][:, 0, 0]) / np.timedelta64(1, "s")
        analysis.status_bar(data_collection).showMessage(f"{data.label}: {seconds:.2f} s between frames")

``glue_solar/describe.py`` tells what a dataset is, such as its ``role``.

A viewer tool
-------------

A viewer tool is a button or a menu entry of a viewer's toolbar: a subclass of glue's ``Tool``,
registered with glue's ``viewer_tool``. glue calls ``activate`` when the user chooses it. Its
``tool_id`` starts with ``solar:``, and its ``icon`` names one of glue's icons or is the path of a PNG
file.

This one switches a Profile viewer's y axis between a linear and a logarithmic scale::

    from glue.config import viewer_tool
    from glue.viewers.common.tool import Tool


    @viewer_tool
    class LogScaleTool(Tool):
        """The 'Log scale' button of a Profile viewer."""

        icon = "glue_spectrum"
        tool_id = "solar:log_scale"
        action_text = "Log scale"
        tool_tip = "Plot the profiles on a logarithmic or a linear y axis"

        def activate(self):
            self.viewer.state.y_log = not self.viewer.state.y_log

``setup`` in ``glue_solar/__init__.py`` adds each tool to its viewer. A Profile viewer's tools are
buttons::

    if LogScaleTool.tool_id not in ProfileViewer.tools:
        ProfileViewer.tools.append(LogScaleTool.tool_id)

An Image viewer's tools are in menus, which ``setup`` lists in ``menus``: the View menu's display
tools under ``tools.ViewTool`` and the mouse modes under ``tools.ModesTool``. An entry with a
``checked`` property has a check mark while it is true. A Coordinate menu entry is a subclass of
``_CoordinateEntry`` in ``glue_solar/tools.py``, listed in ``CoordinateTool.ENTRIES`` or ``SUBMENUS``,
with ``run(coordinator)`` in place of ``activate``.

An analysis
-----------

An analysis is a data action that computes a new dataset in the background and adds it, linked.
``glue_solar/sources/analysis.py`` has what the analyses share:

- ``check(data)`` raises why ``data`` is not an IRIS raster window or a stack of its scans.
- ``dataset(data, label)`` makes the new dataset, on the raster's scans, steps and slit pixels.
- ``start(data_collection, text, title, function, *args)`` computes ``function(*args)`` on a worker
  thread while glue's status bar says ``text``, then adds the result, its helioprojective coordinates
  linked with the other IRIS data's. An error shows in a box, under ``title``. With ``view=True`` the
  result opens in an Image viewer.
- ``form(title)`` and ``accepted(dialog, form)`` make and run a dialog for settings: see ``_ask`` in
  ``glue_solar/sources/mg_features.py``.

This one maps the largest value of each spectrum::

    import numpy as np
    from glue.core.component import Component
    from glue_qt.utils.decorators import messagebox_on_error

    from glue_solar.glue_patches import layer_action
    from glue_solar.sources import analysis


    def peak(data):
        """The largest value of each spectrum of ``data``, an IRIS raster window or a stack of its scans."""
        analysis.check(data)
        cid = data.main_components[0]
        values = np.fmax.reduce(data[cid], axis=-1)  # NaN where every sample is missing
        maps = analysis.dataset(data, f"{data.label} peak")
        maps.add_component(Component(values, units=data.get_component(cid).units), "peak")
        return maps


    @layer_action(
        "IRIS: peak map",
        single=True,
        data=True,
        check=analysis.check,
        tooltip="Add the largest value of each spectrum of this raster window or stack",
    )
    @messagebox_on_error("Could not compute the peak map")
    def peak_iris(data, data_collection):
        """Add the `peak` of ``data``, computed in the background."""
        text, title = f"Computing the peak map of {data.label}…", "Could not compute the peak map"
        analysis.start(data_collection, text, title, peak, data, view=True)

``peak`` reads the whole window at once. ``analysis.slabs`` reads large data a slab of raster steps at
a time, as in ``glue_solar/sources/red_blue.py``.

Where the code goes
-------------------

Put a new data action or analysis in a module of ``glue_solar/sources``, as ``calibration.py`` is,
and a viewer tool in ``glue_solar/tools.py``. A module imports no name of another that starts with an
underscore.

glue loads glue-solar by calling ``setup`` in ``glue_solar/__init__.py``, the ``glue.plugins`` entry
point in ``pyproject.toml``. Import a new module at the top of that file, which registers its actions
and tools. List a new data action in ``_DATA_ACTIONS`` there, which orders the right-click menu.

Running the tests
-----------------

In a clone, install glue-solar with what its tests need, then run one module's tests, or all::

    pip install -e ".[tests]"
    pytest glue_solar/tests/test_regrid.py
    pytest

The tests that download data run only with ``--remote-data=any``.
