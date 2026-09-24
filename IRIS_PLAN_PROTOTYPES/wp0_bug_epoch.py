import numpy as np, matplotlib, matplotlib.dates as mdates
from glue.utils.matplotlib import datetime64_to_mpl
d = np.array(['2021-09-05T00:18:47'], dtype='datetime64[s]')
num = datetime64_to_mpl(d)
print('matplotlib', matplotlib.__version__, 'epoch', mdates.get_epoch())
print('glue datetime64_to_mpl ->', num, '-> num2date:', mdates.num2date(num)[0].isoformat())
print('matplotlib date2num     ->', mdates.date2num(d))
