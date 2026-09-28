; sswgdl-work patch: GDL's lib/spline.pro has no 4th (sigma/tension) argument, IDL's does.
; Accept and IGNORE sigma: result is a natural cubic spline (IDL clamps sigma>=0.001, i.e.
; near-cubic but NOT bit-identical to IDL's tension spline).
function spline, xx, yy, tt, sigma, deriv=deriv, double=double
  compile_opt idl2
  n = n_elements(xx)
  if xx[n-1] lt xx[0] then return, spl_interp(reverse(xx), reverse(yy), spl_init(reverse(xx), reverse(yy)), tt)
  return, spl_interp(xx, yy, spl_init(xx, yy), tt)
end
