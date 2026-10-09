"""
'IRIS: line ratio diagnostic…', on line moments of irispy's test raster and on synthetic maps: what glue gets of
irispy's map_ratio_to_quantity, and of its density_diagnostic on a stand-in for fiasco, which CI does not install.
"""

import sys
from types import SimpleNamespace

import numpy as np
import pytest
from glue.core import Data
from glue.core.component import Component
from glue_qt.app.application import GlueApplication
from irispy.utils.density import density_diagnostic, map_ratio_to_quantity
from qtpy import QtWidgets

import astropy.units as u
from astropy.wcs import WCS

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.sources.line_ratio import DENSITIES, O_IV, TEMPERATURES
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import keep_hpc_linked, link_hpc, raster_data
from glue_solar.sources.moments import line_moments
from glue_solar.tests.test_quicklook import SCAN

ACTION = "IRIS: line ratio diagnostic…"
# A synthetic theoretical ratio, increasing with log10 n_e in cm^-3
LOG_NE = np.linspace(9, 13, 41)
CURVE = 0.15 + 0.3 / (1 + np.exp(4 * (11 - LOG_NE)))


@pytest.fixture
def app(qtbot):
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    return app


@pytest.fixture
def table(tmp_path):
    """A text table of the synthetic curve, with a # header."""
    path = tmp_path / "ratio.txt"
    np.savetxt(path, np.column_stack([LOG_NE, CURVE]), header="log10 n_e [cm^-3], ratio")
    return str(path)


def answer(monkeypatch, table, picks=(), quantity=None, accept=True, browse=False):
    """
    Make each dialog return as if ``table`` were typed, or picked with Browse…, the numerator and denominator at
    ``picks`` and any ``quantity`` chosen, and OK, or Cancel, pressed; returns what each dialog opened with.
    """
    opened = []

    def exec_(dialog):
        boxes = [dialog.findChild(QtWidgets.QComboBox, name) for name in ("numerator", "denominator", "quantity")]
        opened.append(tuple(box.currentText() for box in boxes))
        if browse:
            monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", lambda *args: (table, ""))
            dialog.findChild(QtWidgets.QPushButton, "browse").click()
        else:
            dialog.findChild(QtWidgets.QLineEdit, "table").setText(table)
        for box, index in zip(boxes, picks):
            box.setCurrentIndex(index)
        if quantity is not None:
            boxes[2].setEditText(quantity)
        return QtWidgets.QDialog.Accepted if accept else QtWidgets.QDialog.Rejected

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    return opened


def run(app, layers):
    """Trigger the action on the selected ``layers``."""
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers(layers)
    tree._actions[ACTION].trigger()
    return app.data_collection[-1]


def direct(numerator, denominator, quantity=LOG_NE, curve=CURVE):
    """irispy's own map from the ratio of the arrays ``numerator`` to ``denominator``, NaN where it is 0."""
    ratio = np.divide(numerator, denominator, out=np.full(numerator.shape, np.nan), where=denominator != 0)
    return ratio, map_ratio_to_quantity(ratio, quantity, curve).value


def test_the_action_adds_irispys_map_of_two_moments_maps_as_one_linked_dataset_and_no_viewer(
    app, monkeypatch, irispy_test_files, table
):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["Si IV 1403"])
    lines = [line_moments(raster, centre) for centre in (1399.77, 1401.16)]  # O IV
    collection = app.data_collection
    collection.extend([raster, *lines])
    keep_hpc_linked(collection)
    opened = answer(monkeypatch, table)
    result = run(app, lines)
    names = [f"{maps.label}: intensity" for maps in lines]
    assert opened == [(*names, "log n_e")]  # their intensities
    assert result.label == f"{lines[0].label} / {lines[1].label} log n_e"
    assert result.meta == {
        "OBSID": raster.meta["OBSID"],
        "STARTOBS": raster.meta["STARTOBS"],
        "ratio_numerator": names[0],
        "ratio_denominator": names[1],
        "ratio_table": table,
    }
    assert [(cid.label, result.get_component(cid).units) for cid in result.main_components] == [
        ("ratio", ""),
        ("log n_e", ""),
    ]
    assert not any(app.viewers)
    # on the maps' raster steps and slit pixels, their helioprojective coordinates linked with the others'
    assert result.coords is lines[0].coords
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(result.world_component_ids) <= linked
    ratio, log_ne = direct(lines[0]["intensity"], lines[1]["intensity"])
    np.testing.assert_array_equal(result["ratio"], ratio)
    np.testing.assert_array_equal(result["log n_e"], log_ne)
    assert np.isfinite(log_ne).any()
    assert np.isnan(log_ne).any()


def test_a_synthetic_ratio_gives_irispys_quantity(app, monkeypatch, tmp_path):
    """
    Two maps whose ratio is known give irispy's own quantity for it, here from a decreasing curve in a CSV table with
    a header, picked with Browse…, the numerator and denominator swapped and the quantity typed: NaN for a ratio
    outside the curve, a denominator of 0 or a missing sample.
    """
    path = tmp_path / "ratio.csv"
    path.write_text("log_t,ratio\n" + "".join(f"{x},{y}\n" for x, y in zip(LOG_NE[::-1], CURVE)))
    known = np.array([[CURVE[0], CURVE[13], CURVE[20], CURVE[40]], [0.1, 0.5, 0.3, 0.3]])
    values = np.array([[2.0, 4.0, 8.0, 0.5], [1.0, 16.0, 0.0, np.nan]])  # powers of 2: the ratio is exactly known
    over, under = Data(label="over"), Data(label="under")
    over.add_component(Component(known * values, units="DN/s"), "intensity")
    under.add_component(Component(values, units="DN/s"), "intensity")
    app.data_collection.extend([under, over])
    opened = answer(monkeypatch, str(path), (1, 0), "log T", browse=True)
    result = run(app, [under, over])
    assert opened == [("under: intensity", "over: intensity", "log n_e")]
    assert result.label == "over / under log T"
    assert result.meta["ratio_table"] == str(path)
    ratio, log_t = direct(known * values, values, LOG_NE[::-1])
    np.testing.assert_array_equal(result["ratio"], ratio)
    np.testing.assert_array_equal(result["log T"], log_t)
    np.testing.assert_allclose(log_t[0], LOG_NE[::-1][[0, 13, 20, 40]], rtol=0, atol=1e-12)
    assert np.isnan(log_t[1]).all()


def test_refusals_and_errors_show_why(app, monkeypatch, tmp_path, irispy_test_files, table):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["Si IV 1403"])
    maps = line_moments(raster, 1399.77)
    shape = maps.shape
    small = Data(label="small", intensity=np.ones((2, 3)))
    plain = Data(label="plain", intensity=np.ones(shape))
    shifted = Data(label="shifted", intensity=np.ones(shape), coords=WCS(naxis=2))
    counts = Data(label="counts", intensity=np.ones(shape), coords=maps.coords)
    partner = Data(label="partner", coords=maps.coords)
    partner.add_component(Component(np.ones(shape), units="DN_IRIS_FUV / s"), "intensity")
    collection = app.data_collection
    collection.extend([raster, maps, small, plain, shifted, counts, partner])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    opened = answer(monkeypatch, table)
    run(app, [raster])
    assert opened == []  # refused before asking
    for other in (small, plain, shifted, counts):
        run(app, [maps, other])
    one_column, curl = tmp_path / "one.txt", tmp_path / "curl.txt"
    one_column.write_text("1\n2\n")
    curl.write_text("1 0.1\n2 0.3\n3 0.2\n")
    for path in (tmp_path / "none.txt", one_column, curl):
        answer(monkeypatch, str(path))
        run(app, [maps, partner])
    assert all(text.startswith("Could not map the line ratio\n") for text in shown)
    assert [text.split("\n", 1)[1] for text in shown] == [
        "Select two maps on the same grid, such as the line moments of two lines.",
        f"{maps.label} and small are not on the same grid.",
        f"{maps.label} and plain are not on the same grid.",
        f"{maps.label} and shifted are not on the same grid.",
        f"{maps.label}: intensity is in 'DN_IRIS_FUV / s' but counts: intensity in ''.",
        f"[Errno 2] No such file or directory: '{tmp_path / 'none.txt'}'",
        f"{one_column} is not a table of two columns: the quantity and the theoretical ratio.",
        "theoretical_ratio must be monotonic to map ratios back to a quantity. Restrict the grid to a monotonic "
        "interval first.",
    ]
    # a blank table or quantity, or Cancel, adds nothing
    for typed, quantity, accept in (("", None, True), (table, " ", True), (table, None, False)):
        answer(monkeypatch, typed, quantity=quantity, accept=accept)
        run(app, [maps, partner])
    assert len(shown) == 8
    assert len(collection) == 7


@pytest.fixture
def fiasco(monkeypatch, tmp_path):
    """
    A stand-in for fiasco with ``line_ratio``, the synthetic curve at each density, and no CHIANTI database built;
    ``calls`` holds what its ``Ion`` and ``line_ratio`` were given.
    """
    calls = []

    def ion(*args, **kwargs):
        calls.append(("Ion", args, kwargs))
        return SimpleNamespace()

    def line_ratio(*args, **kwargs):
        calls.append(("line_ratio", args, kwargs))
        return 0.15 + 0.3 / (1 + np.exp(4 * (11 - np.log10(args[3].to_value(u.cm**-3)))))

    fake = SimpleNamespace(
        Ion=ion, line_ratio=line_ratio, defaults={"hdf5_dbase_root": tmp_path / "none.h5"}, calls=calls
    )
    monkeypatch.setitem(sys.modules, "fiasco", fake)
    return fake


# The dialog's widgets for a table, disabled while the O IV preset is ticked
TABLE_WIDGETS = ((QtWidgets.QLineEdit, "table"), (QtWidgets.QPushButton, "browse"), (QtWidgets.QComboBox, "quantity"))


def preset(monkeypatch):
    """Make each dialog tick the O IV preset, if it can, and press OK; returns whether it could and its tooltip."""
    opened = []

    def exec_(dialog):
        box = dialog.findChild(QtWidgets.QCheckBox, "preset")
        opened.append((box.isEnabled(), box.toolTip()))
        box.setChecked(box.isEnabled())  # as a click would
        disabled = [not dialog.findChild(kind, name).isEnabled() for kind, name in TABLE_WIDGETS]
        assert disabled == [box.isChecked()] * 3
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    return opened


def test_the_o_iv_preset_adds_irispys_density_diagnostic_of_two_moments_maps(
    app, monkeypatch, qtbot, irispy_test_files, fiasco
):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["Si IV 1403"])
    lines = [line_moments(raster, centre) for centre in (1399.77, 1401.16)]
    collection = app.data_collection
    collection.extend([raster, *lines])
    keep_hpc_linked(collection)
    opened = preset(monkeypatch)
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers(lines)
    tree._actions[ACTION].trigger()
    assert opened == [(True, "log n_e from irispy's density_diagnostic, in place of a table")]
    assert iris._RUNNING  # on glue-qt's worker, as fiasco may first download and build CHIANTI
    assert app.statusBar().currentMessage() == "Mapping the O IV density; fiasco first builds CHIANTI, for minutes…"
    qtbot.waitUntil(lambda: len(collection) == 4 and not iris._RUNNING)
    assert app.statusBar().currentMessage() == ""
    result = collection[-1]
    names = [f"{maps.label}: intensity" for maps in lines]
    assert result.label == f"{lines[0].label} / {lines[1].label} log n_e"
    assert result.meta == {
        "OBSID": raster.meta["OBSID"],
        "STARTOBS": raster.meta["STARTOBS"],
        "ratio_numerator": names[0],
        "ratio_denominator": names[1],
        "ratio_preset": O_IV,
    }
    assert [(cid.label, result.get_component(cid).units) for cid in result.main_components] == [
        ("ratio", ""),
        ("log n_e", ""),
    ]
    assert not any(app.viewers)
    assert result.coords is lines[0].coords
    assert link_hpc(collection) == []
    # fiasco's O IV, never asking on stdin, and its ratio of irispy's O IV lines on the densities
    [(_, ion_args, ion_kwargs), (_, ratio_args, ratio_kwargs)] = fiasco.calls
    assert ion_args[0] == "O IV"
    np.testing.assert_array_equal(ion_args[1], TEMPERATURES * u.K)
    assert ion_kwargs == {"ask_before": False, "show_progress": False}
    assert ratio_args[1:3] == (1399.780 * u.AA, 1401.157 * u.AA)
    np.testing.assert_array_equal(ratio_args[3], DENSITIES * u.cm**-3)
    assert ratio_kwargs == {"use_two_ion_model": False}
    over, under = (maps["intensity"] for maps in lines)
    direct = density_diagnostic(
        over,
        under,
        DENSITIES * u.cm**-3,
        ion=ratio_args[0],
        numerator=1399.780 * u.AA,
        denominator=1401.157 * u.AA,
        line_ratio_kwargs={"use_two_ion_model": False},
    )
    np.testing.assert_array_equal(result["ratio"], direct["ratio"].value)
    np.testing.assert_array_equal(result["log n_e"], np.log10(direct["density"].to_value(u.cm**-3)))
    assert np.isfinite(result["log n_e"]).any()
    # once built, the status bar says no more; an error is shown as the table's are
    fiasco.defaults["hdf5_dbase_root"].touch()
    counts = Data(label="counts", intensity=np.ones(lines[0].shape), coords=lines[0].coords)
    collection.append(counts)
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree.ui.layerTree.set_selected_layers([lines[0], counts])
    tree._actions[ACTION].trigger()
    assert app.statusBar().currentMessage() == "Mapping the O IV density…"
    qtbot.waitUntil(lambda: len(shown) == 1 and not iris._RUNNING)
    assert shown == [f"Could not map the line ratio\n{names[0]} is in 'DN_IRIS_FUV / s' but counts: intensity in ''."]
    assert len(collection) == 5


@pytest.mark.parametrize("fake", [None, SimpleNamespace()], ids=["no fiasco", "fiasco without line_ratio"])
def test_the_o_iv_preset_needs_fiascos_line_ratio(app, monkeypatch, fake):
    monkeypatch.setitem(sys.modules, "fiasco", fake)  # None: import fiasco fails
    over, under = Data(label="over", intensity=np.ones((2, 3))), Data(label="under", intensity=np.ones((2, 3)))
    app.data_collection.extend([over, under])
    opened = preset(monkeypatch)
    run(app, [over, under])
    assert opened == [(False, "Needs fiasco's line_ratio: pip install 'glue-solar[density]'")]
    assert len(app.data_collection) == 2  # unticked, with no table: nothing added
