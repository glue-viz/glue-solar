pro which_impl
  gdlssw_setup
  foreach n, ['GAUSSFIT','SILENT_GAUSSFIT','MPFITFUN','MPFIT','CURVEFIT','POLY_FIT','INTERPOL','SPLINE','STDEV','AVERAGE','LAMB2V','DERIV','ANYTIM2TAI','READFITS','MRDFITS','MEDIAN','SMOOTH','REGION_GROW','LABEL_REGION'] do begin
    f = file_which(strlowcase(n) + '.pro')
    print, n + ' -> ' + (f eq '' ? '(built-in or missing)' : f)
  endforeach
end
