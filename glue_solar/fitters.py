"""
Lines on a background, composed in Settings, for the Fit tab of glue's Profile viewer, which glue imports with its
first Profile viewer (D86).
"""

import copy
import functools
import operator
import time
import weakref

import numpy as np
from glue.config import fit_plugin
from glue.core.fitters import AstropyFitter1D
from glue.core.link_manager import is_convertible_to_single_pixel_cid
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.viewers.profile.profile_tools import ProfileTools
from matplotlib.colors import to_hex, to_rgb
from qtpy import QtWidgets
from scipy import signal

import astropy.units as u
from astropy.modeling import fitting, models

from glue_solar.glue_patches import _get_fitter
from glue_solar.lines import KM_S, _doppler_rest
from glue_solar.quicklook import _role
from glue_solar.sources.loaders.lazy import at_ceiling

_KINDS = {
    "Gaussian": models.Gaussian1D,
    "Lorentzian": models.Lorentz1D,
    "Constant": models.Const1D,
    "Linear": models.Linear1D,
    "Polynomial": models.Polynomial1D,
}
_LINES = (models.Gaussian1D, models.Lorentz1D)  # amplitude, center and width, as irispy's maps_from_fit takes them


def _component(leaf):
    """``leaf``, an astropy model, as a component of `GaussianConstantFitter`, each parameter's settings blank."""
    return leaf, {name: {"value": None, "fixed": False, "limits": None, "tie": None} for name in leaf.param_names}


def _name(name, index, components):
    """Parameter ``name`` of component ``index`` of ``components`` as astropy names it in their sum."""
    return f"{name}_{index}" if len(components) > 1 else name


def _label(leaf):
    """The kind of component ``leaf`` is."""
    kind = next(kind for kind, cls in _KINDS.items() if isinstance(leaf, cls))
    return f"{kind}, degree {leaf.degree}" if isinstance(leaf, models.Polynomial1D) else kind


def _leaves(model):
    """The components of ``model``."""
    return [model[index] for index in range(model.n_submodels)] if model.n_submodels > 1 else [model]


def _tie(other, factor, offset):
    """
    astropy's tie of a parameter to ``other``, times ``factor`` plus ``offset``: a closure, which dask pickles to its
    processes by value, and its ``args`` for `fit_maps._in_angstrom` to convert the offset.
    """

    def tie(model):
        return getattr(model, other).value * factor + offset

    tie.args = other, factor, offset
    return tie


def _number(edit):
    """The number in ``edit``, a line edit, or None for none."""
    return float(text) if (text := edit.text().strip()) else None


class _Settings(QtWidgets.QDialog):
    """
    The IRIS fitter's Settings, glue-qt's dialog for a fitter's ``settings_widget`` (`glue_patches._on_settings`):
    its components, added and removed, and each parameter's start, Fixed, either bound and, for a line, a tie to a line
    above it: its amplitude or width that line's times the ratio, blank for 1, or its center that line's plus the
    separation, in the x unit (D86); "Mg II two peaks" sets the components to two lines on a constant (D98).
    """

    def __init__(self, fitter, parent=None):
        super().__init__(parent)
        self.fitter, self.components, self.table = fitter, copy.deepcopy(fitter.components), None
        self.setWindowTitle(f"{fitter.label} settings")
        self.kind, self.degree, add = QtWidgets.QComboBox(), QtWidgets.QSpinBox(), QtWidgets.QPushButton("Add")
        mg_ii = QtWidgets.QPushButton("Mg II two peaks")
        mg_ii.setToolTip(
            "Two Gaussians on a constant, for the blue and red emission peaks of the Mg II k or h line in the Fit range,"
            " each starting at its peak (IRIS Technical Note 39)"
        )
        mg_ii.clicked.connect(self._mg_ii)
        self.kind.addItems(_KINDS)
        self.kind.currentTextChanged.connect(lambda kind: self.degree.setEnabled(kind == "Polynomial"))
        self.degree.setRange(2, 5)
        self.degree.setPrefix("degree ")
        self.degree.setEnabled(False)
        add.clicked.connect(self._add)
        bar = QtWidgets.QHBoxLayout()
        for widget in (self.kind, self.degree, add, mg_ii):
            bar.addWidget(widget)
        bar.addStretch()
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.box = QtWidgets.QVBoxLayout(self)
        self.box.addLayout(bar)
        self.box.addWidget(buttons)
        self._build()

    def _build(self):
        """A title and Remove for each component, then a row of each parameter's settings."""
        if self.table is not None:  # out of the dialog at once, deleted once the Remove clicked in it returns
            self.table.setParent(None)
            self.table.deleteLater()
        self.table = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(self.table)
        for column, title in enumerate(["", "Start", "Fixed", "Lower", "Upper", "Tied to", "Ratio or separation"]):
            grid.addWidget(QtWidgets.QLabel(title), 0, column)
        self.rows = {}  # each parameter's widgets, by its name in the model
        for index, (leaf, settings) in enumerate(self.components):
            row = grid.rowCount()
            grid.addWidget(QtWidgets.QLabel(f"<b>{index}: {_label(leaf)}</b>"), row, 0, 1, 6)
            remove = QtWidgets.QPushButton("Remove")
            remove.clicked.connect(functools.partial(self._remove, index))
            grid.addWidget(remove, row, 6)
            for position, name in enumerate(leaf.param_names):
                setting = settings[name]
                target, tied_by = setting["tie"] or (None, None)
                start, lower, upper, by = (
                    QtWidgets.QLineEdit("" if value is None else str(value))
                    for value in (setting["value"], *(setting["limits"] or (None, None)), tied_by)
                )
                fixed, tie = QtWidgets.QCheckBox(), QtWidgets.QComboBox()
                fixed.setChecked(setting["fixed"])
                tie.addItem("", None)
                for other, (line, _) in enumerate(self.components[:index] if isinstance(leaf, _LINES) else []):
                    if isinstance(line, _LINES):  # a line above it, the same parameter
                        tie.addItem(_name(line.param_names[position], other, self.components), other)
                tie.setCurrentIndex(max(tie.findData(target), 0))
                tie.setEnabled(tie.count() > 1)
                by.setEnabled(tie.count() > 1)
                row, full = grid.rowCount(), _name(name, index, self.components)
                grid.addWidget(QtWidgets.QLabel(full), row, 0)
                self.rows[full] = start, fixed, lower, upper, tie, by
                for column, widget in enumerate(self.rows[full], 1):
                    grid.addWidget(widget, row, column)
        self.box.insertWidget(1, self.table)

    def _read(self):
        """Set ``components`` from the rows; raises for a field that is not a number."""
        for index, (_, settings) in enumerate(self.components):
            for name in settings:
                start, fixed, lower, upper, tie, by = self.rows[_name(name, index, self.components)]
                limits = _number(lower), _number(upper)
                settings[name] = {
                    "value": _number(start),
                    "fixed": fixed.isChecked(),
                    "limits": None if limits == (None, None) else limits,
                    "tie": None if tie.currentData() is None else (tie.currentData(), _number(by)),
                }

    @messagebox_on_error("Could not add the component")
    def _add(self, *_):
        self._read()
        cls = _KINDS[self.kind.currentText()]
        self.components.append(_component(cls(self.degree.value()) if cls is models.Polynomial1D else cls()))
        self._build()

    def _mg_ii(self, *_):
        self.components = [_component(leaf) for leaf in (models.Const1D(), models.Gaussian1D(), models.Gaussian1D())]
        for _, settings in self.components[1:]:
            settings["amplitude"]["limits"] = (0, None)  # emission peaks
        self._build()

    @messagebox_on_error("Could not remove the component")
    def _remove(self, index, *_):
        self._read()
        del self.components[index]
        for _, settings in self.components:  # ties to it dropped, to those after it renumbered
            for setting in settings.values():
                if setting["tie"] is not None:
                    target, by = setting["tie"]
                    setting["tie"] = None if target == index else (target - (target > index), by)
        self._build()

    @messagebox_on_error("Could not apply the settings")
    def accept(self):
        self._read()
        if not self.components:
            raise ValueError("Add a component to fit.")
        self.fitter.components = self.components
        super().accept()


class GaussianConstantFitter(AstropyFitter1D):
    """
    The sum of the components set in Settings (`_Settings`), by default a Gaussian on a constant, fitted with astropy's
    ``TRFLSQFitter`` to the finite samples, as an IRIS window's fill is NaN, one at least per free parameter, but for
    those ``saturated``, a lower bound only, which place the starts alone (D87). Starts left blank come from the data:
    the first background at their median, flat, and each line at its peak from it, emission or absorption, among the
    samples nearer its center than any other line's, the center its start, its tie, or else one of the most prominent
    peaks, and its width that of its samples above half the peak, a Gaussian's standard deviation or a Lorentzian's
    full width at half maximum. An amplitude with no bounds keeps its start's sign, as a blend otherwise fits as one line
    up and one down (D81). The summary adds each center and its Doppler velocity from the layer's rest wavelength
    (D11), how many saturated samples were left out and how many kept include saturated pixels.
    """

    label = "Gaussian + constant (IRIS)"
    fitting_cls = fitting.TRFLSQFitter
    settings_widget = _Settings  # glue-qt's Settings, with `glue_patches._on_settings`

    def __init__(self, **params):
        self.components = [_component(models.Const1D()), _component(models.Gaussian1D())]
        super().__init__(**params)

    @property
    def param_names(self):
        return list(self.constraints)

    @property
    def constraints(self):  # glue's, of each parameter not tied, as glue sets no ties
        return {
            _name(name, index, self.components): {key: setting[key] for key in ("value", "fixed", "limits")}
            for index, (_, settings) in enumerate(self.components)
            for name, setting in settings.items()
            if setting["tie"] is None
        }

    def set_constraint(self, parameter_name, value=None, fixed=None, limits=None):
        # glue's, of the parameter's component, replaced as Settings replaces it
        [setting] = [
            setting
            for index, (_, settings) in enumerate(self.components)
            for name, setting in settings.items()
            if _name(name, index, self.components) == parameter_name
        ]
        setting.update(value=value, fixed=bool(fixed), limits=limits)

    def model_cls(self, **starts):  # glue's hook, given each parameter's start
        model = functools.reduce(operator.add, [leaf.copy() for leaf, _ in self.components])
        for index, (leaf, settings) in enumerate(self.components):
            for position, name in enumerate(leaf.param_names):
                full, tie = _name(name, index, self.components), settings[name]["tie"]
                parameter = getattr(model, full)
                if starts.get(full) is not None:
                    parameter.value = starts[full]
                if isinstance(leaf, _LINES) and position == 0:  # keeps its sign
                    parameter.bounds = (0, None) if parameter.value >= 0 else (None, 0)
                if isinstance(leaf, _LINES) and position == 2:  # positive, as irispy's
                    parameter.bounds = (models.Gaussian1D.stddev.bounds[0], None)
                if tie is not None:  # a center's separation, an amplitude's or width's ratio, blank for the same
                    target, by = tie
                    other = _name(self.components[target][0].param_names[position], target, self.components)
                    # to the root of a chain, through its target's tie, set above: astropy computes each tie from the
                    # values before any tie (fitting.py `fitter_to_model_params_array`), so a tie to a tied one is stale
                    root, factor, offset = getattr(getattr(model, other).tied, "args", (other, 1, 0))
                    ratio, separation = (1, by or 0) if position == 1 else (1 if by is None else by, 0)
                    parameter.tied = _tie(root, factor * ratio, offset * ratio + separation)
        return model

    def fit(self, x, y, dy, constraints, saturated=False, **options):  # the options are read from the fitter
        keep = np.isfinite(y)
        fitted = (keep & np.logical_not(saturated))[keep]
        free, finite = sum(not constraint["fixed"] for constraint in constraints.values()), np.count_nonzero(fitted)
        if finite < free:  # in place of scipy's "Improper input" traceback
            raise ValueError(
                f"{self.label} needs at least {free} finite, unsaturated samples in the range, one per free parameter, "
                f"and has {finite}: widen the range"
            )
        x, y, dy = x[keep], y[keep], dy if dy is None else dy[keep]
        for name, start in self.parameter_guesses(x, y, dy).items():  # glue leaves one fixed with no estimate None
            if constraints[name]["fixed"] and constraints[name]["value"] is None:
                constraints[name]["value"] = start
        model, fitter = self._get_model_fitter(x, y, dy, constraints)
        for name, (lower, upper) in model.bounds.items():  # a start from the data within the bounds set in Settings
            if not (model.fixed[name] or model.tied[name]):
                parameter = getattr(model, name)
                parameter.value = np.clip(
                    parameter.value, -np.inf if lower is None else lower, np.inf if upper is None else upper
                )
        x, y, dy = x[fitted], y[fitted], dy if dy is None else dy[fitted]
        return fitter(model, x, y, weights=self._sigma_to_weights(dy), **_jacobian(model)), fitter

    def parameter_guesses(self, x, y, dy):
        level, spacing = np.median(y), np.ptp(x) / (len(x) - 1)
        lines = [
            (index, leaf, settings)
            for index, (leaf, settings) in enumerate(self.components)
            if isinstance(leaf, _LINES)
        ]
        centered = [settings[leaf.param_names[1]] for _, leaf, settings in lines]  # each center's settings
        unset = [setting for setting in centered if setting["tie"] is None and setting["value"] is None]
        # zero beyond the range, so that a line at its edge is a peak
        peaks, found = signal.find_peaks(np.pad(np.abs(y - level), 1), prominence=0)
        if len(peaks) < len(unset):
            raise ValueError(
                f"{self.label} needs a peak in the range for each line without a start, {len(unset)}, and finds "
                f"{len(peaks)}: widen the range, or give lines starts or remove some in Settings"
            )
        peaks = iter(np.sort(peaks[np.argsort(-found["prominences"], kind="stable")[: len(unset)]]) - 1)
        centers = {}
        for index, leaf, settings in lines:  # a center's start, tie, to a line above, or else a peak
            setting = settings[leaf.param_names[1]]
            if setting["tie"] is not None:
                target, by = setting["tie"]
                centers[index] = centers[target] + (by or 0)
            else:
                centers[index] = x[next(peaks)] if setting["value"] is None else setting["value"]
        starts = {}
        for index, leaf, settings in lines:
            # emission or absorption, as its amplitude's bounds set, else the stronger
            lower, upper = settings[leaf.param_names[0]]["limits"] or (None, None)
            sign = 1 if lower is not None and lower >= 0 else -1 if upper is not None and upper <= 0 else None
            excess = np.abs(y - level) if sign is None else sign * (y - level)
            distance = np.abs(x - centers[index])
            # the samples nearer its center than any other line's, its nearest at least
            cell = np.all([distance <= np.abs(x - other) for other in centers.values()], 0) | (
                distance == distance.min()
            )
            near = np.where(cell, excess, -np.inf)
            peak = np.argmax(near)
            fwhm = (np.count_nonzero(near >= near[peak] / 2) or 1) * spacing
            amplitude, center, width = (_name(name, index, self.components) for name in leaf.param_names)
            starts.update({amplitude: y[peak] - level, center: x[peak]})
            starts[width] = fwhm / np.sqrt(8 * np.log(2)) if isinstance(leaf, models.Gaussian1D) else fwhm
        backgrounds = [(index, leaf) for index, (leaf, _) in enumerate(self.components) if not isinstance(leaf, _LINES)]
        for number, (index, leaf) in enumerate(backgrounds):  # the first at the median, flat
            for name in leaf.param_names:
                starts[_name(name, index, self.components)] = (
                    level if number == 0 and name in ("amplitude", "intercept", "c0") else 0
                )
        names = self.param_names
        return {name: start for name, start in starts.items() if name in names}

    def plot(self, fit_result, axes, x, linewidth=None, alpha=None, color=None, normalize=None):
        """
        glue's curve of the fit, then each line's on the background, dashed (kept by `glue_patches._plot_fit`), in a
        shade of the layer's color, wider and above the data, so the fit stands out from its spectrum (D98).
        """
        if color is not None:
            rgb = np.array(to_rgb(color))
            # darker, or lighter for a dark color, such as glue's default gray, which a darker shade would not change
            # a string, as glue's own plot passes it as matplotlib's format
            color = to_hex(rgb * 0.55 if rgb @ [0.299, 0.587, 0.114] > 0.3 else rgb + (1 - rgb) * 0.5)
        linewidth = 3 * (linewidth or 0.5)  # 1.5 times the layer's: glue-qt passes half its width
        artists = super().plot(fit_result, axes, x, linewidth, alpha, color, normalize)
        leaves = _leaves(fit_result[0])
        background = sum(leaf(x) for leaf in leaves if not isinstance(leaf, _LINES))
        for leaf in leaves:
            if isinstance(leaf, _LINES):
                y = background + leaf(x)
                y = y if normalize is None else normalize(y)
                artists += axes.plot(x, y, color=color, lw=linewidth, alpha=alpha, ls="--", scalex=False, scaley=False)
        for artist in artists:
            artist.set_zorder(100)  # above every layer's
        return artists

    def summarize(self, fit_result, x, y, dy=None):
        model = fit_result[0]  # glue-qt summarizes with a new fitter, its components at their defaults
        rest, unit = model.meta.get("rest_wavelength"), model.meta.get("x_unit")
        text = f"{super().summarize(fit_result, x, y, dy)}\n"
        for index, leaf in enumerate(_leaves(model)):
            if isinstance(leaf, _LINES):
                center = leaf.parameters[1]
                text += f"\ncenter_{index} = {center:.6f}"
                if rest is not None:
                    velocity = (center * u.Unit(unit)).to_value(KM_S, u.doppler_optical(rest * u.AA))
                    text += f", {velocity:+.2f} {KM_S} from {rest} Å"
        if count := model.meta.get("saturated"):
            text += f"\n{count} saturated sample{'s' if count > 1 else ''} left out"
        if count := model.meta.get("partly_saturated"):  # their mean biased low
            text += f"\n{count} wavelength{'s include' if count > 1 else ' includes'} saturated pixels"
        return text


def _jacobian(model):
    """
    The fitter's options for ``model``: astropy's analytic Jacobian drops a tied parameter's part (fitting.py
    `_wrap_deriv`, report candidate), so tied models fit with an estimated one, its step 1e-6 of each parameter up to
    astropy 8.0.1, which takes the square root, and 1e-12 from 8.0.2 (astropy#20462): 8.0.1's default, 1e-4, is wider
    than a line at 1335 Å.
    """
    return {"estimate_jacobian": True, "epsilon": 1e-12} if model.has_tied else {}


_profile_fit = ProfileTools._fit


def _saturated(layer, state):
    """
    Which samples of the profile of ``layer``, IRIS data or a subset of them, in a Profile viewer of ``state`` are
    saturated, a lower bound only, and which combine saturated DN with others, a mean biased low (D87): the first where
    every DN its function combines is at the ceiling (`at_ceiling`), any for its Maximum, the second where some are,
    from glue's minimum and maximum of the DN over the same subset, which read what the profile reads; none for other
    data.
    """
    data = layer.data
    if _role(data) not in ("raster", "sji"):
        return False, False
    axis = is_convertible_to_single_pixel_cid(data, state.x_att_pixel).axis
    axes = tuple(i for i in range(data.ndim) if i != axis)
    subset_state = getattr(layer, "subset_state", None)
    cid = data.main_components[0]
    some = at_ceiling(data.compute_statistic("maximum", cid, axis=axes, subset_state=subset_state))
    if state.function == "maximum":
        return some, False
    every = at_ceiling(data.compute_statistic("minimum", cid, axis=axes, subset_state=subset_state))
    return every, some & ~every


def _fit(self, fitter, xlim=None):
    """
    glue-qt's fit of each layer, an IRIS fit with the layer's saturated samples left out (`_saturated`) and its model
    given what `GaussianConstantFitter.summarize`, which glue-qt passes neither layer nor viewer, and 'Fit every
    spectrum' take: the layer's rest wavelength and attribute, the viewer's x unit and function, the range, how many
    saturated samples it left out and how many it kept that include saturated DN; the viewer keeps its last IRIS fit of
    each dataset while the dataset lives (D86), of the layer listed last where a dataset and a subset of it are both
    fitted.
    """
    if not isinstance(fitter, GaussianConstantFitter):
        return _profile_fit(self, fitter, xlim)
    if not hasattr(ProfileTools, "_get_fitter"):  # else glue-qt gives its own, which its Settings set
        fitter = _get_fitter(self, type(fitter))  # as `_profile_fit`
    state, fits = self.viewer.state, vars(self).setdefault("_iris_fits", weakref.WeakKeyDictionary())
    results = {}
    for layer in self.viewer.layers:  # glue-qt's loop, as it gives a fitter no layer
        if layer.enabled and layer.visible:
            x, y = (np.asarray(values) for values in layer.state.profile)
            if len(x) > 0:
                keep = (x >= min(xlim)) & (x <= max(xlim))
                every, some = _saturated(layer.layer, state)
                saturated = (keep & every)[keep]
                # the options too, as glue's ``build_and_fit``
                model, _ = results[layer] = fitter.fit(
                    x[keep], y[keep], None, fitter.constraints, saturated, **fitter.options
                )
                model.meta.update(
                    rest_wavelength=_doppler_rest(layer.layer, state.x_att),
                    x_unit=state.x_display_unit,
                    function=state.function,
                    attribute=layer.state.attribute.label,
                    x_range=tuple(sorted(xlim)),
                    saturated=int(saturated.sum()),
                    partly_saturated=int((keep & some).sum()),
                    fitted=time.monotonic(),
                )
                fits[layer.layer.data] = model  # a subset's data too
    return results, x, y


ProfileTools._fit = _fit


def setup():
    if GaussianConstantFitter not in fit_plugin:  # glue_solar.setup() may run more than once
        fit_plugin.add(GaussianConstantFitter)
