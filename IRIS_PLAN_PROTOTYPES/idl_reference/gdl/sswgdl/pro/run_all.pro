; Runs the four IRIS routines and records which source file every compiled routine came from.
pro run_all
  run_wavecorr
  run_mg
  run_burst
  run_burst_lo
  run_sjiburst
  s = [routine_info(/source), routine_info(/source, /functions)]
  openw, u, getenv('SSWGDL_OUT')+'/compiled_sources.txt', /get_lun
  for i = 0, n_elements(s)-1 do printf, u, s[i].name, '  ', s[i].path
  free_lun, u
end
