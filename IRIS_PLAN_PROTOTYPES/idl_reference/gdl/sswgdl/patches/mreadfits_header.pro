pro mreadfits_header,infits,index, debug=debug, $
   only_tags=only_tags, template=template, loud=loud, all_headers=all_headers, $
   extension=extension
;+
;   Name: mreadfits_header
;
;   Purpose: 3D FITS -> header structures - mreadfits helper for speed
;
;   Input Paramters:
;      fitsfiles - FITS file list (local nfs or urls) 
;   
;   Output Parameters:
;      index - vector of header-structures
;
;   Keyword Parameters:
;      only_tags - optional tag list desired subset (for speed!)
;      template - optional structure template to use
;                 (implies ONLY_TAGS & output tag datatyping) 
;      loud - if set, be more verbose n
;      all_headers - optional INPUT of all headers as 1D (bypass read but apply same string->struct
;
;   Calling Sequence:
;      IDL> mreadfits_header, fitsfiles, index [,only_tags=taglist]
;
;   Calling Examples: 
;      IDL> mreadfits_header,fitsfiles, index ; all FITS -> index.TAGS
;      IDL> mreadfits_header,fitsfiles, index, $
;              only_tags='naxis1,naxis2,xcen,ycen,cdelt1,wavelen' ; much faster
;      IDL> help,index,/str ; show output of above
;
;   History:
;      11-July-2006 - S.L.Freeland - speed up the 3D FITS->structure process
;      17-July-2006 - S.L.Freeland - add ONLY_TAGS, online beta version
;      31-July-2006 - S.L.Freeland - in line comment protection...
;      26-July-2006 - S.L.Freeland - assure TEMPLATE is scalar
;      15-oct-2007 -  S.L.Freeland - add /LOUD and changed default->quiet
;      27-nov-2007 - S.L.Freeland - allow escaped tags (DATE-OBS=DATE_D$OBS for example)
;      16-mar-2009 - S.L.Freeland - add all_headers
;      10-jul-2009 - S.L.Freeland - allow URLS for 'infits'
;      10-apr-2010 - S.L.Freeland - add EXTENSION keywords, 
;      25-sep-2012 - S.L.Freeland - avoid more stuff if ALL_HEADERS supplied (ref: ssw_jp20002struct calls this)
;      12-oct-2012 - S.L.Freeland - ~handle (e.g. dont crash)  mis-matched data types
;
;   Notes:
;      Preliminary tests indicate factor of at least 4 faster
;      Use of ONLY_TAGS may give another order of magnitude improvement
;
;   Restrictions:
;      COMMENT and HISTORY not yet implemented - check tommorrow
;      Assumes that all files have same set of FITS keywords (1:1)
;      After testing, plan to integrate this ~transparently -> mreadfits.pro
;
;-
;
; use first for template
debug=keyword_set(debug)

      
loud=keyword_set(loud)
quiet=1-loud
nf=n_elements(infits)
if n_elements(extension) eq 0 then extension=0 ; default is primary header
case 1 of 
   data_chk(all_headers,/string) and data_chk(template,/struct): ;user supplies 1D string array  -AND- TEMPLATE
   n_params() eq 0: begin 
      box_message,'mreadfits_header,<fitsfiles>,index
      return
   endcase
   strpos(infits(0),'http:') ne -1: begin 
      sock_fits,infits(0),data,header,/nodata,err=err 
      if err(0) eq '' then begin 
         template=fitshead2struct(header)
         if keyword_set(only_tags) then template=str_subset(template,only_tags)
         all_headers=header
         for i=1,nf-1 do begin 
            sock_fits,infits(i),data,header,/nodata,err=err 
            all_headers=[temporary(all_headers),header]
         endfor
      endif else begin 
         box_message,['Error in url processing',err,'...returning']
stop,'err
         return ; !!!! Early Exit
      endelse
   endcase
   1-file_exist(infits(0)): begin 
      box_message,'first file does not exist, aborting...'
      return
   endcase
   else: begin 
      head=headfits(infits(0),ext=extension)
      if not data_chk(template,/struct) then begin 
         ; mreadfits,infits(0),template ; use first for template
         thead=headfits(infits(0),ext=extension)
         template=fitshead2struct(thead)
         template=template(0)
         if keyword_set(only_tags) then $ 
            template=str_subset(template,id_esc(str2arr(only_tags)))
      endif
   endcase
endcase

if n_elements(all_headers) eq 0 then begin 
pad=10
nh=n_elements(head)+pad

allstr=strarr((nh+pad)*nf)  ; some padding * nFITS
      
for i=0l,nf-1 do begin 
   pnt=i*nh
   allstr(pnt)=headfits(infits(i),ext=extension)
endfor

endif else allstr=all_headers  ; user supplied 1D header vector
 
sscom=where(strpos(allstr,'/') gt 9 and strpos(allstr,'COMMENT') ne 0 and strpos(allstr,'HISTORY') ne 0,ccnt)
vals=allstr
if ccnt gt 0 then vals(sscom)=ssw_strsplit(allstr(sscom),'/',tail=comments)
vstr=strtrim(strmid(vals,9,100),2)
bool=where(vstr eq 'T' or vstr eq 'F',bcnt)
if bcnt gt 0 then vstr(bool)=vstr(bool) eq 'T'
keywords=strtrim(strmids(allstr,0,strpos(allstr,'=')),2)
vstr=strtrim(str_replace(vstr,"'"," "),2)

index=replicate(template,nf) 
ntags=n_tags(template)
tname=tag_names(template)
for i=0,ntags-1 do begin 
   delvarx,tempx
   tempx=index.(i)
   ;if is_member(tname(i),'SIMPLE,EXTEND') then tempx=strtrim(tempx,2)
   ss=where(id_unesc(tname(i)) eq keywords,sscnt)
   if sscnt eq nf then begin 
      catch, ioerr  ; sswgdl-work patch: GDL ON_IOERROR does not trap READS conversion errors
      if ioerr eq 0 then reads,vstr(ss),tempx else if loud then box_message,"conversion error: "+tname(i)
      catch, /cancel
      if ioerr ne 0 then goto, skip
      if data_chk(tempx,/string) then tempx=str_replace(tempx,"'"," ")
skip: index.(i)=tempx
   endif else begin
      if loud then box_message,'#tags ne #files for tag: ' + tname(i)
   endelse
endfor

if required_tags(index,'date_obs,date_d$obs') and n_elements(index) gt 1 then begin
   date_obs=all_vals(index.date_obs)
   date_d$obs=all_vals(index.date_d$obs)
   if n_elements(date_d$obs) gt n_elements(date_obs) then index.date_obs=index.date_d$obs
endif

if debug then stop
return
end
   


