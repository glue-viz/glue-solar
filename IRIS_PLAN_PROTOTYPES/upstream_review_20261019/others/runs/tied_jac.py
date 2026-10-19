import warnings, numpy as np, astropy
from astropy.modeling import models
from astropy.modeling.fitting import LevMarLSQFitter, fitter_to_model_params, model_to_fit_params
warnings.simplefilter("ignore")
x = np.linspace(-10, 10, 50)
m = models.Gaussian1D(2, -2.5, 1.2) + models.Gaussian1D(2, 1.5, 1.2); m.amplitude_1.tied = lambda q: 0.5 * q.amplitude_0
free, *_ = model_to_fit_params(m)
jac = np.array(LevMarLSQFitter._wrap_deriv(free, m, None, x, np.zeros_like(x)))  # rows: free params
def model_at(p):
    mm = m.copy(); fitter_to_model_params(mm, p); return mm(x)
h = 1e-6; fd = np.array([(model_at(free + h * e) - model_at(free - h * e)) / (2 * h) for e in np.eye(free.size)])
print(f"astropy {astropy.__version__}: max |analytic - finite difference| per free parameter:", np.abs(jac - fd).max(axis=1).round(4), "(amplitude_0 row should include 0.5 x the second Gaussian)")
