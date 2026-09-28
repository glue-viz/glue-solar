; self-check for the region_grow stand-in: run with  gdl -e test_region_grow
pro test_region_grow
  m = bytarr(8,8) & m[2:3,2:3] = 1b & m[4,4] = 1b & m[6,1] = 1b & m[0,5] = 1b
  r = region_grow(m, 2+2*8L, /all_neigh)      ; diagonal link (3,3)-(4,4) joins
  if ~array_equal(r, [18,19,26,27,36]) then message, 'all_neighbors grow wrong: '+strjoin(strtrim(r,2),',')
  r = region_grow(m, 2+2*8L)                  ; 4-connectivity: (4,4) not joined
  if ~array_equal(r, [18,19,26,27]) then message, '4-neighbour grow wrong'
  if region_grow(m, 0+5*8L, /all_neigh) ne -1 then message, 'edge seed should give -1'
  print, 'test_region_grow OK'
end
