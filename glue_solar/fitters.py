"""
A Gaussian on a constant for the Fit tab of glue's Profile viewer, which glue imports with its first Profile viewer.
"""

import numpy as np
from glue.config import fit_plugin
from glue.core.fitters import AstropyFitter1D, SimpleAstropyGaussianFitter

from astropy import constants
from astropy.modeling import models

from glue_solar.lines import MAIN_LINES

__all__ = ["GaussianConstantFitter"]

NEAR = 0.5  # a centre within this many Angstrom of a main IRIS line gets its velocity from it


def _model(amplitude_0, amplitude_1, mean_1, stddev_1):
    return models.Const1D(amplitude_0) + models.Gaussian1D(amplitude_1, mean_1, stddev_1)


class GaussianConstantFitter(AstropyFitter1D):
    """
    A `~astropy.modeling.functional_models.Gaussian1D` on a `~astropy.modeling.functional_models.Const1D`, numbered as
    irispy's ``profiles_on_background`` numbers them (``amplitude_0`` the constant), fitted with the fitter class of
    glue's Gaussian to the finite samples, as an IRIS window's fill is NaN. It starts from the data: the constant their
    median, the line their sample farthest from it, an emission or absorption line, and the standard deviation from
    the width where they are beyond half of that. The summary adds the centre and, within `NEAR` of a main IRIS line
    (`lines.MAIN_LINES`) for an x axis in Angstrom, its Doppler velocity from that line.
    """

    label = "Gaussian + constant (IRIS)"
    model_cls = staticmethod(_model)
    param_names = ["amplitude_0", "amplitude_1", "mean_1", "stddev_1"]
    fitting_cls = SimpleAstropyGaussianFitter.fitting_cls

    def fit(self, x, y, dy, constraints):
        keep = np.isfinite(y)
        return super().fit(x[keep], y[keep], dy if dy is None else dy[keep], constraints)

    def parameter_guesses(self, x, y, dy):
        constant = np.median(y)
        peak = np.argmax(np.abs(y - constant))
        amplitude = y[peak] - constant
        fwhm = np.count_nonzero(np.abs(y - constant) >= np.abs(amplitude) / 2) * np.ptp(x) / (len(x) - 1)
        stddev = fwhm / np.sqrt(8 * np.log(2))
        return {"amplitude_0": constant, "amplitude_1": amplitude, "mean_1": x[peak], "stddev_1": stddev}

    def summarize(self, fit_result, x, y, dy=None):
        centre = fit_result[0].mean_1.value
        text = f"{super().summarize(fit_result, x, y, dy)}\n\ncentre = {centre:.6f}"
        name, rest = min(MAIN_LINES, key=lambda line: abs(line[1] - centre))
        if abs(centre - rest) <= NEAR:
            text += f"\n{name} {rest} Å: {(centre / rest - 1) * constants.c.to_value('km/s'):+.2f} km/s"
        return text


def setup():
    if GaussianConstantFitter not in fit_plugin:  # glue_solar.setup() may run more than once
        fit_plugin.add(GaussianConstantFitter)
