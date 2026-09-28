#!/bin/sh
# iris_sji_burst_check takes a date and looks the SJI 1400 file up under $IRIS_DATA/level2/YYYY/MM/DD/<obs>/,
# so build that layout for the 4000255147 SJI 1400 (decompressed; about 124 MB).
# Usage: sh make_sji_tree.sh [data_dir] [tree_dir]
set -e
data_dir=${1:-$HOME/DATA/IRIS}
tree=${2:-iris_ref_tree}
src=$(ls "$data_dir"/*_4000255147_SJI_1400_t000.fits.gz | head -1)
dest="$tree/level2/2013/09/02/20130902_163935_4000255147"
mkdir -p "$dest"
gunzip -c "$src" > "$dest/iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits"
echo "IRIS_DATA tree: $(cd "$tree" && pwd)"
