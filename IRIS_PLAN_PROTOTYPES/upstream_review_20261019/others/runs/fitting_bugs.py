import warnings, numpy as np, astropy
from astropy.modeling import models, fitting
from astropy.modeling.fitting import fitter_to_model_params_array, LevMarLSQFitter, TRFLSQFitter
warnings.simplefilter("ignore"); print("astropy", astropy.__version__)
# 1. tie chain: mean_2 tied to mean_1 tied to mean_0
m = models.Gaussian1D(1, 0, 1) + models.Gaussian1D(1, 0, 1) + models.Gaussian1D(1, 0, 1)
m.mean_1.tied = lambda mm: mm.mean_0 + 1
m.mean_2.tied = lambda mm: mm.mean_1 + 1
params = np.array(m.parameters); params[1] = 5.0  # mean_0 = 5 -> mean_1 should be 6, mean_2 7
out = fitter_to_model_params_array(m, params[[0, 2, 3, 5, 6, 8]] if False else params.copy())
print("tie chain: mean_0", out[1], "mean_1", out[4], "mean_2", out[7], "-> stale" if out[7] != 7 else "-> ok")
# 2. tied Jacobian: fit with analytic derivative vs estimated, parameter tied
x = np.linspace(-10, 10, 400); truth = models.Gaussian1D(3, -2, 1) + models.Gaussian1D(1.5, 2, 1)
y = truth(x) + np.random.default_rng(0).normal(0, 0.02, x.size)
def model():
    mm = models.Gaussian1D(2, -2.5, 1.2) + models.Gaussian1D(2, 1.5, 1.2); mm.amplitude_1.tied = lambda q: 0.5 * q.amplitude_0; return mm
f = LevMarLSQFitter()
ana = f(model(), x, y, estimate_jacobian=False); est = f(model(), x, y, estimate_jacobian=True)
print(f"tied Jacobian: analytic amp0 {ana.amplitude_0.value:.4f} est amp0 {est.amplitude_0.value:.4f}; analytic nfev {f.fit_info.get('nfev')}")
r_ana = np.sum((ana(x) - y) ** 2); r_est = np.sum((est(x) - y) ** 2)
print(f"  residual sum sq analytic {r_ana:.5f} estimated {r_est:.5f}")
# 3. FitInfoSubset KeyError in FitInfoArrayContainer
from astropy.modeling._fitting_parallel import FitInfoSubset, FitInfoArrayContainer
arr = np.empty((2,), dtype=object); arr[0] = FitInfoSubset(success=True); arr[1] = None
try:
    print("FitInfoArrayContainer[0]:", FitInfoArrayContainer(arr)[0])
except Exception as e:
    print("FitInfoArrayContainer[0]:", type(e).__name__, e)
try:
    hasattr(FitInfoSubset(success=True), "ndim"); print("hasattr ok")
except Exception as e:
    print("hasattr(FitInfoSubset, 'ndim'):", type(e).__name__, e)
