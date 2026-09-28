#!/bin/sh
# Download the three inputs of iris_ref_run.pro from the LMSAL IRIS archive (about 1 GB, 1.9 GB unpacked),
# check them against the copies the GDL run used, and unpack the rasters into the layout the script searches.
# Usage: sh fetch_data.sh [data_dir]    (default: iris_ref_data)
set -e
dir=${1:-iris_ref_data}
base=https://www.lmsal.com/solarsoft/irisa/data/level2_compressed
mkdir -p "$dir"
cd "$dir"

fetch() {
  if [ ! -f "$2" ]; then
    curl -fL --retry 3 -o "$2.part" "$base/$1/$2"
    mv "$2.part" "$2"
  fi
  sum=$( (md5sum "$2" 2>/dev/null || md5 -r "$2") | cut -d' ' -f1 )
  if [ "$sum" != "$3" ]; then
    echo "MD5 mismatch for $2: $sum (expected $3)" >&2
    exit 1
  fi
  echo "ok $2"
}

fetch 2013/09/02/20130902_182935_4000005156 iris_l2_20130902_182935_4000005156_raster.tar.gz 6fcaf618e84a4f5b33729014d4c04b87
fetch 2014/07/08/20140708_114109_3824262996 iris_l2_20140708_114109_3824262996_raster.tar.gz fb36627ccaf1146762105ff1f109f1cc
fetch 2013/09/02/20130902_163935_4000255147 iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits.gz e35f6ea0691b06d89a6e202e693fa3a4

for obs in 20130902_182935_4000005156 20140708_114109_3824262996; do
  mkdir -p "iris_l2_${obs}_raster"
  tar -xzf "iris_l2_${obs}_raster.tar.gz" -C "iris_l2_${obs}_raster"
done
echo "Data in $(pwd)"
