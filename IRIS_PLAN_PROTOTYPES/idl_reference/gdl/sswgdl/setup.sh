#!/bin/sh
# Rebuild the sswgdl-work tree (SSW gen+iris+ontology under GDL). Scratch-only; no sudo.
# Usage: sh setup.sh            (then see run lines at the bottom)
set -e
W=<scratch>/sswgdl-work
R=<scratch>/features/gdl-reference/gdl.app/Contents/Resources
TAR=https://sohoftp.nascom.nasa.gov/solarsoft/offline/swmaint/tar
mkdir -p "$W/dl" "$W/ssw/vobs" "$W/gdldir/bin" "$W/home" "$W/out" "$W/logs"

# 1. SSW tarballs (~510 MB): gen 27M, iris 279M, site 7K, vobs/ontology 180M
for p in ssw_ssw_site ssw_ssw_gen ssw_ssw_iris ssw_vobs_ontology; do
  [ -s "$W/dl/$p.tar.Z" ] || curl -sSL --retry 3 -o "$W/dl/$p.tar.Z" "$TAR/$p.tar.Z"
done
( cd "$W/ssw" && for p in ssw_ssw_site ssw_ssw_gen ssw_ssw_iris; do tar -xzf "../dl/$p.tar.Z"; done )
( cd "$W/ssw/vobs" && tar -xzf ../../dl/ssw_vobs_ontology.tar.Z )   # tarball is relative to $SSW/vobs

# 2. "Make GDL pretend to be IDL" (sswgdl README) without touching gdl.app: own IDL_DIR with bin/idl
ln -sf "$R/bin/gdl" "$W/gdldir/bin/gdl"
ln -sf "$R/bin/gdl" "$W/gdldir/bin/idl"
ln -sfn "$R/share" "$W/gdldir/share"

# 3. iris_sji_burst_check finds files via $IRIS_DATA/level2/YYYY/MM/DD/<obs>/*.fits (uncompressed)
D=$W/irisdata/level2/2013/09/02/20130902_163935_4000255147
mkdir -p "$D"
[ -s "$D/iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits" ] || \
  gunzip -c ~/DATA/IRIS/534d789bb0a2821fb2b78eb36d1d6753-iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits.gz \
  > "$D/iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits"

# Run (sswgdl launcher + pro/ + patches/ are in $W):
#   cd $W && printf '.run run_wavecorr run_mg run_burst run_burst_lo run_sjiburst run_all\nrun_all\nexit\n' | \
#     SSWGDL_PATCHES=$W/patches SSWGDL_OUT=$W/out SSWGDL_IRISDATA=$W/irisdata ./sswgdl > logs/run_all.log 2>&1
