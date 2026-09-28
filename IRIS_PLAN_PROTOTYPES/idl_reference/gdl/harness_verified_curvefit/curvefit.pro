; sensitivity probe: IDL CURVEFIT defaults (TOL=1e-3, ITMAX=20) passed to mpcurvefit
FUNCTION CURVEFIT, x, y, w, p, sigma, FUNCTION_NAME=fcn, ITMAX=maxiter, TOL=tol, CHISQ=bestnorm, YERROR=yerror, STATUS=status, _EXTRA=extra
  if n_elements(tol) eq 0 then tol = 1e-3
  if n_elements(maxiter) eq 0 then maxiter = 20
  if n_elements(w) eq 0 then w = x*0+1.
  return, mpcurvefit(x, y, w, p, sigma, function_name=fcn, itmax=maxiter, chisq=bestnorm, /nocovar, yerror=yerror, ftol=tol, status=status, /quiet)
END
