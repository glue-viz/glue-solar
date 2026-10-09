"""
'IRIS: line ratio diagnostic…': a quantity such as log n_e or log T, mapped by irispy from the ratio of two maps on the
same grid, as a new dataset; from a table, or from CHIANTI's O IV ratio through fiasco.
"""

import numpy as np
from glue.config import layer_action
from glue.core.component import Component
from glue.core.data import Data
from glue_qt.utils.decorators import messagebox_on_error
from qtpy import QtWidgets

import astropy.units as u
from astropy.io import ascii

from glue_solar.sources.loaders.iris import keep_hpc_linked
from glue_solar.sources.moments import _accepted, _start

__all__ = ["line_ratio", "line_ratio_iris", "o_iv_density"]

# The names the dialog offers for the quantity, the first column of the theoretical ratio table, or one typed
QUANTITIES = ("log n_e", "log T")
# The dialog's preset: O IV's lines at CHIANTI's wavelengths in Angstrom, as in irispy's O IV example, and their ratio
# on electron densities in cm^-3, 0.1 dex apart, at temperatures in K about O IV's, of which irispy takes the formation
# temperature, log T 5.15
O_IV = "O IV 1399.8/1401.2 (CHIANTI, fiasco)"
O_IV_LINES = (1399.780, 1401.157)
DENSITIES = np.logspace(8, 13, 51)
TEMPERATURES = np.logspace(4.5, 6, 31)


def _same_grid(a, b):
    """Whether datasets ``a`` and ``b`` have the same shape and the same world coordinates at every pixel."""
    if a.shape != b.shape:
        return False
    if a.coords is None or b.coords is None:
        return a.coords is b.coords
    if a.coords.world_n_dim != b.coords.world_n_dim:
        return False
    pixels = np.indices(a.shape)  # in numpy order, as given to both
    return np.allclose(a.coords.pixel_to_world_values(*pixels), b.coords.pixel_to_world_values(*pixels), equal_nan=True)


def line_ratio(numerator, denominator, quantity, ratio, name=QUANTITIES[0]):
    """
    ``name`` from the ratio of ``numerator`` to ``denominator``, two components in the same unit on the same grid,
    mapped by irispy's `~irispy.utils.density.map_ratio_to_quantity` on the theoretical ``ratio`` at each ``quantity``,
    as one dataset on that grid.

    Its components are ``ratio``, NaN where the denominator is 0, and ``name``, interpolated linearly in ``quantity``,
    NaN where the ratio is missing or outside the theoretical one. ``meta`` holds the numerator's ``OBSID`` and
    ``STARTOBS``, and ``ratio_numerator`` and ``ratio_denominator``, each ``<dataset label>: <component label>``.

    Parameters
    ----------
    numerator, denominator : `~glue.core.component_id.ComponentID`
        The intensities, such as the ``intensity`` of two line moments maps.
    quantity : array-like or `~astropy.units.Quantity`
        The quantity at which ``ratio`` is sampled, such as log10 of the electron density in cm^-3.
    ratio : array-like
        The theoretical ratio of the numerator's line to the denominator's, monotonic in ``quantity``.
    name : str
        The quantity's component label.

    Raises
    ------
    ValueError
        For components on different grids or in different units, or a ``ratio`` irispy cannot map from.
    """
    from irispy.utils.density import map_ratio_to_quantity

    def mapped(over, under):
        observed = np.divide(over, under, out=np.full(over.shape, np.nan), where=under != 0)
        return observed, map_ratio_to_quantity(observed, quantity, ratio)

    return _map(numerator, denominator, name, mapped)


def o_iv_density(numerator, denominator):
    """
    ``log n_e`` from the ratio of ``numerator``, O IV 1399.8 Å, to ``denominator``, O IV 1401.2 Å, two components in
    the same unit on the same grid, by irispy's `~irispy.utils.density.density_diagnostic` on CHIANTI's ratio, which
    fiasco computes on electron densities of 10^8 to 10^13 cm^-3 at O IV's formation temperature, as one dataset on
    that grid, as `line_ratio`'s; its ``meta`` holds ``ratio_preset`` in place of ``ratio_table``.

    fiasco, from its git main (``pip install 'glue-solar[density]'``), downloads and builds the CHIANTI database on
    its first use, in ``~/.fiasco`` or where its ``~/.fiasco/fiascorc`` says.

    Raises
    ------
    ValueError
        For components on different grids or in different units.
    """
    import fiasco
    from irispy.utils.density import density_diagnostic

    def mapped(over, under):
        # ask_before: else fiasco asks on stdin; show_progress: its build's progress bar fails on a worker in a terminal
        ion = fiasco.Ion("O IV", TEMPERATURES * u.K, ask_before=False, show_progress=False)
        result = density_diagnostic(
            over,
            under,
            DENSITIES * u.cm**-3,
            ion=ion,
            numerator=O_IV_LINES[0] * u.AA,
            denominator=O_IV_LINES[1] * u.AA,
            line_ratio_kwargs={"use_two_ion_model": False},  # CHIANTI has no two-ion data for O IV, as fiasco warns
        )
        return result["ratio"].value, u.Quantity(np.log10(result["density"].to_value(u.cm**-3)))

    result = _map(numerator, denominator, QUANTITIES[0], mapped)
    result.meta["ratio_preset"] = O_IV
    return result


def _map(numerator, denominator, name, mapped):
    """
    The dataset of `line_ratio`, with ``mapped(numerator values, denominator values)`` giving its ratio and ``name``.
    """
    top, bottom = numerator.parent, denominator.parent
    if not _same_grid(top, bottom):
        raise ValueError(f"{top.label} and {bottom.label} are not on the same grid.")
    names = [f"{cid.parent.label}: {cid.label}" for cid in (numerator, denominator)]
    units = [cid.parent.get_component(cid).units for cid in (numerator, denominator)]
    if units[0] != units[1]:
        raise ValueError(f"{names[0]} is in '{units[0]}' but {names[1]} in '{units[1]}'.")
    observed, quantity = mapped(top[numerator], bottom[denominator])
    result = Data(label=f"{top.label} / {bottom.label} {name}", coords=top.coords)
    result.meta = {key: top.meta[key] for key in ("OBSID", "STARTOBS") if key in top.meta}
    result.meta.update(ratio_numerator=names[0], ratio_denominator=names[1])
    result.add_component(Component(observed), "ratio")
    result.add_component(Component(quantity.value, units=str(quantity.unit)), name)
    return result


def _has_line_ratio():
    """Whether fiasco is installed with ``line_ratio``, which irispy's density_diagnostic needs."""
    try:
        import fiasco
    except ImportError:
        return False
    return hasattr(fiasco, "line_ratio")


def _ask(datasets):
    """
    The numerator and denominator picked among the components of ``datasets``, the path of the theoretical ratio
    table, None for the `O_IV` preset, and the quantity's name; or None for a blank path or name, or Cancel.
    """
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle("IRIS: line ratio diagnostic")
    form = QtWidgets.QFormLayout(dialog)
    cids = [cid for data in datasets for cid in data.main_components]
    intensities = [index for index, cid in enumerate(cids) if cid.label == "intensity"]
    boxes = []
    for side, index in zip(("numerator", "denominator"), intensities if len(intensities) > 1 else (0, 1)):
        box = QtWidgets.QComboBox(objectName=side)
        for cid in cids:
            box.addItem(f"{cid.parent.label}: {cid.label}", cid)
        box.setCurrentIndex(index)
        form.addRow(f"{side.capitalize()}:", box)
        boxes.append(box)
    table = QtWidgets.QLineEdit(objectName="table", placeholderText="columns: the quantity, the ratio")
    browse = QtWidgets.QPushButton("Browse…", objectName="browse")
    browse.clicked.connect(
        lambda: table.setText(
            QtWidgets.QFileDialog.getOpenFileName(dialog, "Theoretical ratio table")[0] or table.text()
        )
    )
    row = QtWidgets.QHBoxLayout()
    row.addWidget(table)
    row.addWidget(browse)
    form.addRow("Ratio table:", row)
    quantity = QtWidgets.QComboBox(objectName="quantity", editable=True)
    quantity.addItems(QUANTITIES)
    preset = QtWidgets.QCheckBox(O_IV, objectName="preset")
    preset.toggled.connect(lambda on: [widget.setDisabled(on) for widget in (table, browse, quantity)])
    if _has_line_ratio():  # imports fiasco, at the first dialog rather than at the plugin's load
        preset.setToolTip("log n_e from irispy's density_diagnostic, in place of a table")
    else:
        preset.setEnabled(False)
        preset.setToolTip("Needs fiasco's line_ratio: pip install 'glue-solar[density]'")
    form.addRow("Or:", preset)
    form.addRow("Quantity:", quantity)
    if not _accepted(dialog, form):
        return None
    if preset.isChecked():
        return boxes[0].currentData(), boxes[1].currentData(), None, QUANTITIES[0]
    path, name = table.text().strip(), quantity.currentText().strip()
    if not path or not name:
        return None
    return boxes[0].currentData(), boxes[1].currentData(), path, name


@messagebox_on_error("Could not map the line ratio")
def _failed(exc_info):
    raise exc_info[1]


@layer_action(
    "IRIS: line ratio diagnostic…",
    single=False,
    tooltip="Add a quantity such as log n_e mapped by irispy from the ratio of two maps on the same grid",
)
@messagebox_on_error("Could not map the line ratio")
def line_ratio_iris(layers, data_collection):
    """
    Add the `line_ratio` of two components picked among those of the selected maps, on the first two columns of a
    picked text table, or their `o_iv_density`, to the data collection, with its helioprojective coordinates linked,
    and no viewer; glue shows why for fewer than two components, or a table without two columns. fiasco and irispy
    map the O IV density in the background, while glue's status bar says so.
    """
    datasets = [layer for layer in layers if isinstance(layer, Data) and layer.ndim == 2]
    if sum(len(data.main_components) for data in datasets) < 2:
        raise ValueError("Select two maps on the same grid, such as the line moments of two lines.")
    picked = _ask(datasets)
    if picked is None:
        return
    numerator, denominator, path, name = picked
    if path is None:
        import fiasco

        first = "" if fiasco.defaults["hdf5_dbase_root"].is_file() else "; fiasco first builds CHIANTI, for minutes"
        _start(data_collection, f"Mapping the O IV density{first}…", _failed, o_iv_density, numerator, denominator)
        return
    table = ascii.read(path)  # spaces or commas, an optional header line and # comments
    if len(table.colnames) < 2:
        raise ValueError(f"{path} is not a table of two columns: the quantity and the theoretical ratio.")
    result = line_ratio(numerator, denominator, table.columns[0], table.columns[1], name)
    result.meta["ratio_table"] = path
    data_collection.append(result)
    keep_hpc_linked(data_collection)
