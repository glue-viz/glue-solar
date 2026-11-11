import io, numpy as np, matplotlib; matplotlib.use("QtAgg")
import matplotlib.pyplot as plt, mpl_scatter_density
from mpl_scatter_density.base_image_artist import supports_resize
rng = np.random.default_rng(0); x, y = rng.normal(size=(2, 200000))
fig = plt.figure(figsize=(4, 4)); ax = fig.add_subplot(111, projection="scatter_density"); art = ax.scatter_density(x, y)
print("supports_resize(QtAgg):", supports_resize(fig.canvas))
fig.canvas.draw()
def png(): b = io.BytesIO(); fig.savefig(b, format="png"); return b.getvalue()
before = png()
fig.set_size_inches(8, 3); fig.canvas.resize_event() if hasattr(fig.canvas, "resize_event") else None
fig.canvas.draw()
held = png()
art.on_release(); fig.canvas.draw(); released = png()
print("pressed after resize:", art._pressed, "| saved during hold == saved after release:", held == released, "| extent during hold:", art.get_extent() if art._pressed else "n/a")
