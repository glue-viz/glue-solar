; GDL shim: GDL's SPLINE has no 4th (tension, SIGMA) argument; IDL's does.
; ponytail: ignores SIGMA and uses GDL's natural cubic spline (SPL_INIT/SPL_INTERP).
; IDL's tension spline (Cline) with small sigma is close to cubic, but end conditions
; may differ, so outputs near the interpolation range edges are not bit-identical.
function spline, xx, yy, tt, sigma, deriv=deriv
  compile_opt idl2
  n = n_elements(xx)
  if xx[n-1] lt xx[0] then return, spl_interp(reverse(xx), reverse(yy), spl_init(reverse(xx), reverse(yy)), tt)
  return, spl_interp(xx, yy, spl_init(xx, yy), tt)
end
