import numpy as np
from glue.core import Data
from glue.core.application_base import Application
from glue.viewers.scatter.viewer import SimpleScatterViewer
t = np.array(['2021-09-05T00:18:47', '2021-09-05T01:19:54'], dtype='datetime64[s]')
d = Data(label='goes', time=t, flux=[1.0, 2.0])
app = Application(); app.data_collection.append(d)
v = app.new_data_viewer(SimpleScatterViewer, data=d)
v.state.x_att = d.id['time']; v.state.y_att = d.id['flux']
v.figure.canvas.draw()
print('x tick labels:', [t.get_text() for t in v.axes.get_xticklabels()][:4])
import matplotlib.dates as mdates
print('xlim as dates:', [mdates.num2date(x).date().isoformat() for x in v.axes.get_xlim()])
