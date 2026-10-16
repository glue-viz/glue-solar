"""
irispy's line on a background for the Fit tab of glue's Profile viewer, which glue imports with its first Profile
viewer.
"""

import numpy as np
from glue.config import fit_plugin
from glue.core.fitters import AstropyFitter1D
from glue.core.simpleforms import BoolOption
from irispy.utils.fitting import profiles_on_background

from astropy import constants
from astropy.modeling import fitting

from glue_solar.lines import KM_S, MAIN_LINES

__all__ = ["GaussianConstantFitter"]

NEAR = 0.5  # a center within this many Angstrom of a main IRIS line gets its velocity from it


class GaussianConstantFitter(AstropyFitter1D):
    """
    irispy's ``profiles_on_background`` model of one line, a Gaussian on a constant, or on a sloping background with
    `linear_background` and a Lorentzian with `lorentzian`, fitted with astropy's ``TRFLSQFitter`` to the finite
    samples, as an IRIS window's fill is NaN, one at least per free parameter. It starts from the data: the background
    their median, flat, the line their sample farthest from it, an emission or absorption line, and the width from
    where they are beyond half of that, a Gaussian's standard deviation or a Lorentzian's full width at half maximum.
    The summary adds the center and, within `NEAR` of a main IRIS line (`lines.MAIN_LINES`) for an x axis in Angstrom,
    its Doppler velocity from that line.

    glue-qt's Profile tools call the fitter registered for a new one at each Settings and each fit, so the one
    registered returns itself, keeping its Settings for every fit (report candidate).
    """

    label = "Gaussian + constant (IRIS)"
    linear_background = BoolOption(label="Linear background")
    lorentzian = BoolOption(label="Lorentzian profile")
    fitting_cls = fitting.TRFLSQFitter

    def __call__(self):
        return self

    def set_constraint(self, parameter_name, value=None, fixed=None, limits=None):
        # Settings' row replaces the entry, as glue's keeps an estimate or bounds cleared there (report candidate)
        self._constraints[parameter_name] = {"value": value, "fixed": bool(fixed), "limits": limits}

    def _kinds(self):
        return {
            "background": "linear" if self.linear_background else "constant",
            "profile": "lorentzian" if self.lorentzian else "gaussian",
        }

    @property
    def param_names(self):
        return list(profiles_on_background(0, **self._kinds()).param_names)

    def model_cls(self, **starts):  # glue's hook, given each parameter's start
        *_, level, amplitude, center, width = self.param_names
        model = profiles_on_background(
            starts[center],
            amplitudes=[starts[amplitude]],
            widths=[starts[width]],
            background_level=starts[level],
            **self._kinds(),
        )
        if starts.get("slope_0") is not None:  # set in Settings: irispy's starts flat
            model.slope_0 = starts["slope_0"]
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
        return super().fit(x, y, dy, constraints)

    def parameter_guesses(self, x, y, dy):
        constant = np.median(y)
        peak = np.argmax(np.abs(y - constant))
        amplitude = y[peak] - constant
        fwhm = np.count_nonzero(np.abs(y - constant) >= np.abs(amplitude) / 2) * np.ptp(x) / (len(x) - 1)
        *_, level, height, center, width = self.param_names
        return {
            level: constant,
            height: amplitude,
            center: x[peak],
            width: fwhm if self.lorentzian else fwhm / np.sqrt(8 * np.log(2)),
        }

    def summarize(self, fit_result, x, y, dy=None):
        model = fit_result[0]
        center = getattr(model, model.param_names[-2]).value
        text = f"{super().summarize(fit_result, x, y, dy)}\n\ncenter = {center:.6f}"
        name, rest = min(MAIN_LINES, key=lambda line: abs(line[1] - center))
        if abs(center - rest) <= NEAR:
            text += f"\n{name} {rest} Å: {(center / rest - 1) * constants.c.to_value(KM_S):+.2f} {KM_S}"
        return text


FITTER = GaussianConstantFitter()  # the one in glue's Fit tab


def setup():
    if FITTER not in fit_plugin:  # glue_solar.setup() may run more than once
        fit_plugin.add(FITTER)
