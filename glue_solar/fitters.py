"""
irispy's lines on a background for the Fit tab of glue's Profile viewer, which glue imports with its first Profile
viewer.
"""

import numpy as np
from glue.config import fit_plugin
from glue.core.fitters import AstropyFitter1D
from glue.core.simpleforms import BoolOption, IntOption
from glue_qt.viewers.profile.profile_tools import ProfileTools
from irispy.utils.fitting import profiles_on_background
from scipy import signal

import astropy.units as u
from astropy.modeling import fitting

from glue_solar.lines import KM_S, _doppler_rest

__all__ = ["GaussianConstantFitter"]


class GaussianConstantFitter(AstropyFitter1D):
    """
    irispy's ``profiles_on_background`` model of `n_lines` lines, Gaussians on a constant, or on a sloping background
    with `linear_background` and Lorentzians with `lorentzian`, fitted with astropy's ``TRFLSQFitter`` to the finite
    samples, as an IRIS window's fill is NaN, one at least per free parameter. It starts from the data: the background
    their median, flat, and the lines at their most prominent peaks from it, emission or absorption, each width at
    half its peak, a Gaussian's standard deviation or a Lorentzian's full width at half maximum. Each amplitude keeps
    its start's sign, as a blend otherwise fits as one line up and one down (D81), and `same_width` ties every width to
    the first line's. The summary adds each center and its Doppler velocity from the layer's rest wavelength (D11).
    """

    label = "Gaussian + constant (IRIS)"
    linear_background = BoolOption(label="Linear background")
    lorentzian = BoolOption(label="Lorentzian profile")
    n_lines = IntOption(min=1, max=4, default=1, label="Number of lines")
    same_width = BoolOption(label="Same width")
    fitting_cls = fitting.TRFLSQFitter

    def set_constraint(self, parameter_name, value=None, fixed=None, limits=None):
        # Settings' row replaces the entry, as glue's keeps an estimate or bounds cleared there (report candidate)
        self._constraints[parameter_name] = {"value": value, "fixed": bool(fixed), "limits": limits}

    def _kinds(self):
        return {
            "background": "linear" if self.linear_background else "constant",
            "profile": "lorentzian" if self.lorentzian else "gaussian",
        }

    def _lines(self):
        """Each line's amplitude, center and width, as irispy names them."""
        center, width = ("x_0", "fwhm") if self.lorentzian else ("mean", "stddev")
        return [(f"amplitude_{line}", f"{center}_{line}", f"{width}_{line}") for line in range(1, self.n_lines + 1)]

    @property
    def param_names(self):
        tied = [width for *_, width in self._lines()[1:]] if self.same_width else []  # no row: glue sets no ties
        names = profiles_on_background(np.zeros(self.n_lines), **self._kinds()).param_names
        return [name for name in names if name not in tied]

    def model_cls(self, **starts):  # glue's hook, given each parameter's start
        lines = self._lines()
        first = lines[0][2]
        model = profiles_on_background(
            [starts[center] for _, center, _ in lines],
            amplitudes=[starts[amplitude] for amplitude, *_ in lines],
            widths=[starts.get(width, starts[first]) for *_, width in lines],
            background_level=starts["intercept_0" if self.linear_background else "amplitude_0"],
            bounds={amplitude: (0, None) if starts[amplitude] >= 0 else (None, 0) for amplitude, *_ in lines},
            **self._kinds(),
        )
        if starts.get("slope_0") is not None:  # set in Settings: irispy's starts flat
            model.slope_0 = starts["slope_0"]
        for *_, width in lines[1:] if self.same_width else []:
            getattr(model, width).tied = lambda model: getattr(model, first).value
        return model

    def fit(self, x, y, dy, constraints, **options):  # the options are read from the fitter
        keep = np.isfinite(y)
        free, finite = sum(not constraint["fixed"] for constraint in constraints.values()), np.count_nonzero(keep)
        if finite < free:  # in place of scipy's "Improper input" traceback
            raise ValueError(
                f"{self.label} needs at least {free} finite samples in the range, one per free parameter, and has "
                f"{finite}: widen the range"
            )
        x, y, dy = x[keep], y[keep], dy if dy is None else dy[keep]
        for name, start in self.parameter_guesses(x, y, dy).items():  # glue leaves one fixed with no estimate None
            if constraints[name]["fixed"] and constraints[name]["value"] is None:
                constraints[name]["value"] = start
        model, fitter = self._get_model_fitter(x, y, dy, constraints)
        # astropy's analytic Jacobian drops a tied width's part (fitting.py `_wrap_deriv`, report candidate), so tied
        # widths fit with an estimated one, its step 1e-6 of each parameter up to astropy 8.0.1, which takes the square
        # root, and 1e-12 from 8.0.2 (astropy#20462): 8.0.1's default, 1e-4, is wider than a line at 1335 Å
        tied = {"estimate_jacobian": True, "epsilon": 1e-12} if model.has_tied else {}
        return fitter(model, x, y, weights=self._sigma_to_weights(dy), **tied), fitter

    def parameter_guesses(self, x, y, dy):
        constant = np.median(y)
        excess = np.pad(np.abs(y - constant), 1)  # zero beyond the range, so that a line at its edge is a peak
        peaks, found = signal.find_peaks(excess, prominence=0)
        if len(peaks) < self.n_lines:
            raise ValueError(
                f"{self.label} needs a peak in the range per line, {self.n_lines}, and finds {len(peaks)}: widen the "
                "range or lower 'Number of lines' in Settings"
            )
        peaks = np.sort(peaks[np.argsort(-found["prominences"], kind="stable")[: self.n_lines]])
        fwhms = signal.peak_widths(excess, peaks, rel_height=0.5)[0] * np.ptp(x) / (len(x) - 1)
        starts = {"intercept_0" if self.linear_background else "amplitude_0": constant}
        for (amplitude, center, width), peak, fwhm in zip(self._lines(), peaks - 1, fwhms, strict=True):
            starts.update({amplitude: y[peak] - constant, center: x[peak]})
            starts[width] = fwhm if self.lorentzian else fwhm / np.sqrt(8 * np.log(2))
        names = self.param_names
        return {name: start for name, start in starts.items() if name in names}

    def summarize(self, fit_result, x, y, dy=None):
        model = fit_result[0]  # glue-qt summarizes with a new fitter, its options at their defaults
        rest, unit = model.meta.get("rest_wavelength"), model.meta.get("x_unit")
        text = f"{super().summarize(fit_result, x, y, dy)}\n"
        for line in range(1, model.n_submodels):
            center = getattr(model, f"{model[line].param_names[1]}_{line}").value  # a line's second parameter
            text += f"\ncenter_{line} = {center:.6f}"
            if rest is not None:
                velocity = (center * u.Unit(unit)).to_value(KM_S, u.doppler_optical(rest * u.AA))
                text += f", {velocity:+.2f} {KM_S} from {rest} Å"
        return text


_profile_fit = ProfileTools._fit


def _fit(self, fitter, xlim=None):
    """
    glue-qt's fit of each layer, an IRIS fit's model given the layer's rest wavelength and the x unit for
    `GaussianConstantFitter.summarize`, which glue-qt passes neither layer nor viewer.
    """
    results, x, y = _profile_fit(self, fitter, xlim)
    if isinstance(fitter, GaussianConstantFitter):
        state = self.viewer.state
        for layer, (model, _) in results.items():
            model.meta.update(rest_wavelength=_doppler_rest(layer.layer, state.x_att), x_unit=state.x_display_unit)
    return results, x, y


ProfileTools._fit = _fit


def setup():
    if GaussianConstantFitter not in fit_plugin:  # glue_solar.setup() may run more than once
        fit_plugin.add(GaussianConstantFitter)
