; part of GDL - GNU Data Language (GPL)
; by Sylwester Arabas <slayoo@igf.fuw.edu.pl>
;
; search & replace helper for strmatch()
;
; 14-Aug-2012 : Now GDL enforces scalar type in FOR loop ... take care
; of STRLEN ! We ensure to work on pure STRING = '' , not STRING = Array[1]
; 
function STRMATCH_STRREPLACE, str, a, b
compile_opt hidden, idl2
on_error, 2
pos = STRPOS(str, a)
if (pos eq -1) then return, str
ret = STRMID(str,0,pos)
la = STRLEN(a[0])
last = pos 
for i = pos, STRLEN(str[0]) - 1 do begin
   if STRMID(str,i,la) eq a && (i eq 0 || STRMID(str,i-1,1) ne '\') then begin
      ret += STRMID(str,last,i-last) + b 
      last = i + la
   endif
endfor
ret += STRMID(str,last)
return, ret
end

; quick & dirty STRMATCH() implementation using STREGEX()
;
function STRMATCH, mstr, sstr, fold_case=fold_case
;
compile_opt hidden, idl2
on_error, 2
; sswgdl-work patch: IDL accepts a 1-element array pattern (and element-wise arrays)
if n_elements(sstr) gt 1 then begin
  if n_elements(sstr) ne n_elements(mstr) then MESSAGE, 'pattern array must match string array size'
  res = bytarr(size(mstr,/dim))
  for k = 0L, n_elements(mstr)-1 do res[k] = STRMATCH(mstr[k], sstr[k], fold_case=fold_case)
  return, res
endif
;
tmp = sstr[0]
;; . -> \. (but not \.)
tmp = STRMATCH_STRREPLACE(tmp, '.', '\.')
;; ( -> \( (but not \()
tmp = STRMATCH_STRREPLACE(tmp, '(', '\(')
; ) -> \) (but not \))
tmp = STRMATCH_STRREPLACE(tmp, ')', '\)')
; + -> \+ (but not \+)
tmp = STRMATCH_STRREPLACE(tmp, '+', '\+')
; { -> \{ (but not \{)
tmp = STRMATCH_STRREPLACE(tmp, '{', '\{')
; } -> \} (but not \})
tmp = STRMATCH_STRREPLACE(tmp, '}', '\}')
; | -> \| (but not \|)
tmp = STRMATCH_STRREPLACE(tmp, '|', '\|')
; ^ -> \^ (but not \^)
tmp = STRMATCH_STRREPLACE(tmp, '^', '\^')
; $ -> \$ (but not \$)
tmp = STRMATCH_STRREPLACE(tmp, '$', '\$')
; * -> .* (but not \*)
tmp = STRMATCH_STRREPLACE(tmp, '*', '.*')
; ? -> . (but not \?)
tmp = STRMATCH_STRREPLACE(tmp, '?', '.')
; [!...] -> [^...] (but not \[!...)
tmp = STRMATCH_STRREPLACE(tmp, '[!', '[^')
; the leading a trailing markers
tmp = '^' + tmp + '$'
return, STREGEX(mstr, tmp, /boolean, fold_case=fold_case)
end
