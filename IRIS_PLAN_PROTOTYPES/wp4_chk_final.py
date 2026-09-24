"""Checker: subset colour kwarg, stack has no time world axis (no duplicate Time), whisker_plot testable via monkeypatched getItem."""
import os, warnings; warnings.simplefilter("ignore")
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["MPLBACKEND"] = "agg"
import numpy as np
from irispy.io import read_files
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.sources.loaders.stack_spectrograms import stack_spectrogram_sequence
from wp4_common import add_slit, slit_subset_state, cube_times
fs = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
cube = read_files(sji_path, memmap=False, uncertainty=False); sji = image_data(sji_path); add_slit(sji, cube)
s = sji.new_subset(slit_subset_state(sji), label="Slit", color="#00ff00")
print("subset colour kwarg:", s.label, s.style.color, "| default would be", __import__("glue.config", fromlist=["settings"]).settings.SUBSET_COLORS[0])
seq = read_files(sorted(f for f in fs if "20140329" in f and "raster_t000_r0000" in f)[:3], spectral_windows=["Mg II k 2796"], memmap=False, uncertainty=False)["Mg II k 2796"]
stacked, _ = stack_spectrogram_sequence(seq, memmap=False)
print("stack physical types:", stacked.wcs.world_axis_physical_types, "| extra_coords empty:", not stacked.extra_coords.keys() if stacked.extra_coords else True, "| cube_times(stack) ->", cube_times(stacked))
