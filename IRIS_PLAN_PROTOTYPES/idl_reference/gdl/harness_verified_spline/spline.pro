function spline, x, y, t, sigma
  s = sort(t) & z = t * 0d
  z[s] = spline_core(x, y, t[s], sigma)
  return, z
end
