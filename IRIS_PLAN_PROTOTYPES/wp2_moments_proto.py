"""WP2 prototype: the moments layer_action as it would ship in glue_solar/sources/moments.py, plus checks."""
import os, time, warnings
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg")
warnings.simplefilter("ignore")
import numpy as np
import astropy.units as u
from glue.core import DataCollection
from glue.core.component import Component
from glue.core.link_helpers import LinkSame
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue_qt.config import layer_action
from irispy.spectrograph import SpectrogramCube
from irispy.utils.constants import DN_UNIT
from irispy.utils.moments import calculate_moments
from qtpy import QtWidgets

from glue_solar.sources.loaders.iris import _cube_data, raster_data, image_data

# ---------------------------------------------------------------- module as it would ship
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
        maps = calculate_moments(cube, rest_wavelength=rest_wavelength, wings=wings, integrated=integrated,
                                 min_intensity=min_intensity, saturation_limit=saturation_limit)
    (first_name, first), *rest = maps.items()
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
        form.addRow("Minimum summed intensity [DN]", self.minimum)
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


# ---------------------------------------------------------------- checks
if __name__ == "__main__":
    from glue_qt.utils import get_qapp
    get_qapp()
    shown = []
    QtWidgets.QMessageBox.critical = staticmethod(lambda *a: (shown.append(a[2]), print("MESSAGEBOX:", a[2])))
    from irispy.data.test import get_test_data_filenames
    files = [str(f) for f in get_test_data_filenames() if str(f).endswith(".fits")]
    sns = [next(f for f in files if f.endswith("sns/iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"))]  # the same file is also under raster/; two copies break read_files
    [d] = raster_data(sns, ["Mg II k 2796"])
    wl = d.coords.pixel_to_world_values(np.arange(d.shape[2]), 0, 0)[0] * u.Unit(d.coords.world_axis_units[0])  # WCS order: (wavelength, lat, lon)
    wl = wl.to_value(u.AA)
    print("sns raster:", d.label, d.shape, "wavelength window [A]", wl.min(), "..", wl.max(), "| step", np.diff(wl).mean())
    rest = f"{(wl.min() + wl.max()) / 2:.2f}"
    print("source comps:", [c.label for c in d.main_components])
    print("registered:", "IRIS: line moments…" in [item.label for item in layer_action])

    dc = DataCollection([d])
    dlg = MomentsDialog(d, dc)
    print("prefilled rest (TWAVE):", repr(dlg.rest.text()), "| using in-window rest:", rest)
    dlg.rest.setText(rest); dlg.low.setText("0.5"); dlg.high.setText("0.5"); dlg.minimum.setText("50")
    dlg.run()
    r = dlg.moments
    print("accepted:", dlg.result() == QtWidgets.QDialog.Accepted, "| dc:", [x.label for x in dc])
    print("result:", r.label, r.shape, [(c.label, r.get_component(c).units) for c in r.main_components])
    print("world:", [c.label for c in r.world_component_ids], r.coords.world_axis_units)
    inten, vel = r["intensity"], r["velocity"]
    print("velocity finite where intensity > 50:", bool(np.isfinite(vel[inten > 50]).all()), "| finite px", int(np.isfinite(vel).sum()), "/", vel.size, "| nanmedian v", float(np.nanmedian(vel)))
    print("external links:", len(dc.external_links), [type(l).__name__ for l in dc.external_links])
    dc.new_subset_group("roi-map", RoiSubsetState(xatt=r.pixel_component_ids[1], yatt=r.pixel_component_ids[0], roi=RectangularROI(10, 30, 2, 5)))
    print("ROI on map:", int(r.subsets[0].to_mask().sum()), "px -> source:", int(d.subsets[0].to_mask().sum()), "px; nwave =", d.shape[2])
    dc.new_subset_group("roi-src", RoiSubsetState(xatt=d.pixel_component_ids[1], yatt=d.pixel_component_ids[0], roi=RectangularROI(0, 10, 100, 120)))
    print("ROI on source:", int(d.subsets[1].to_mask().sum()), "px -> map:", int(r.subsets[1].to_mask().sum()), "px")

    # error path keeps the dialog open
    dlg2 = MomentsDialog(d, dc)
    dlg2.rest.setText("3000"); dlg2.low.setText("0.1"); dlg2.high.setText("0.1")
    dlg2.run()
    print("error path:", shown, "| still open:", dlg2.result() == 0, "| dc size unchanged:", len(dc) == 2)
    dlg3 = MomentsDialog(d, dc); dlg3.low.setText("0.5"); dlg3.run()
    print("half wings:", shown[-1])
    # no wings, no rest (blank): 3 maps only
    dlg4 = MomentsDialog(d, dc); dlg4.rest.setText(""); dlg4.run()
    print("no rest, no wings:", [c.label for c in dlg4.moments.main_components])
    # integrated
    dlg5 = MomentsDialog(d, dc); dlg5.integrated.setChecked(True); dlg5.run()
    print("integrated unit:", dlg5.moments.get_component(dlg5.moments.id["intensity"]).units)

    # stack and SJI are rejected with a clear message
    multi = sorted(f for f in files if "20140329" in f and "raster" in f)
    [stack] = raster_data(multi, ["Mg II k 2796"], stack=True)
    sji = image_data(next(f for f in files if "SJI_1400" in f and "20210905" in f))
    for other in (stack, sji):
        try:
            line_moments(other)
        except ValueError as e:
            print("rejected", other.ndim, "D", type(other.meta).__name__, "->", e)

    # GUI path: the action is enabled for a selected dataset in the layer tree
    from glue_qt.app import GlueApplication
    app = GlueApplication(dc)
    app._layer_widget.ui.layerTree.set_selected_layers([d])
    action = app._layer_widget._actions["IRIS: line moments…"]
    print("layer tree action can trigger on data:", action._can_trigger())
    app._layer_widget.ui.layerTree.set_selected_layers([d.subsets[0]])
    print("... on a subset:", action._can_trigger())

    # RBA follow-up timing
    from irispy.utils.red_blue import calculate_red_blue_asymmetry
    with u.add_enabled_units(list(DN_UNIT.values())):
        cube = SpectrogramCube(d[d.main_components[0]], d.coords._wcs, None, u.Unit("DN_IRIS_NUV"), d.meta)
        t0 = time.perf_counter(); rba = calculate_red_blue_asymmetry(cube, rest_wavelength=float(rest) * u.AA, return_profiles=False); dt = time.perf_counter() - t0
    npx = d.shape[0] * d.shape[1]
    print(f"RBA return_profiles=False: keys {list(rba)} {dt:.2f}s / {npx} px = {dt / npx * 1e6:.0f} us/px; 1096x400 est {dt / npx * 1096 * 400:.0f}s")
    try:
        import fiasco  # noqa
    except ImportError as e:
        print("fiasco:", e)
