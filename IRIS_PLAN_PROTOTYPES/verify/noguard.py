import warnings; warnings.simplefilter("ignore")
import numpy as np
from astropy.modeling import models as m
from astropy.modeling.fitting import LMLSQFitter, parallel_fit_dask
x = np.linspace(-1, 1, 20); data = np.exp(-x**2/0.1)[None, None, :].repeat(4, 0).repeat(3, 1)
fit = parallel_fit_dask(data=data, fitting_axes=2, world=(x,), model=m.Gaussian1D(1, 0, 0.3), fitter=LMLSQFitter(), scheduler="processes")
print("noguard OK", fit.amplitude.shape)
