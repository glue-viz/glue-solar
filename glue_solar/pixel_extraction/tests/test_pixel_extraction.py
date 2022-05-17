import numpy as np
from glue.app.qt import GlueApplication
from glue.core.data import Data
from glue.utils.qt import process_events
from glue.viewers.image.qt import ImageViewer
from numpy.testing import assert_allclose


class TestPixelExtraction:
    def setup_method(self, method):
        self.data = Data(label="d1")
        self.data["x"] = np.arange(24).reshape((3, 4, 2)).astype(float)

        self.app = GlueApplication()
        self.session = self.app.session
        self.hub = self.session.hub

        self.data_collection = self.session.data_collection
        self.data_collection.append(self.data)

        self.viewer = self.app.new_data_viewer(ImageViewer)

    def teardown_method(self, method):
        self.viewer.close(warn=False)
        self.viewer = None
        self.app.close()
        self.app = None

    def test_navigate_sync_image(self):
        self.viewer.add_data(self.data)
        self.viewer.toolbar.active_tool = "solar:pixel_extraction"

        self.viewer.axes.figure.canvas.draw()
        process_events()

        x, y = self.viewer.axes.transData.transform([[1, 2]])[0]
        self.viewer.axes.figure.canvas.button_press_event(x, y, 1)
        self.viewer.axes.figure.canvas.button_release_event(x, y, 1)
        assert len(self.data_collection) == 2

        derived1 = self.data_collection[1]
        assert derived1.label == "d1[:,2,1]"
        assert derived1.shape == (3,)
        assert_allclose(derived1["x"], self.data["x"][:, 2, 1])

        x, y = self.viewer.axes.transData.transform([[1, 1]])[0]
        self.viewer.axes.figure.canvas.button_press_event(x, y, 1)
        self.viewer.axes.figure.canvas.button_release_event(x, y, 1)
        assert len(self.data_collection) == 2

        derived2 = self.data_collection[1]
        assert derived2 is derived1
        assert derived2.label == "d1[:,1,1]"
        assert derived2.shape == (3,)
        assert_allclose(derived2["x"], self.data["x"][:, 1, 1])

        self.viewer.state.x_att = self.data.pixel_component_ids[0]

        self.viewer.axes.figure.canvas.draw()
        process_events()

        x, y = self.viewer.axes.transData.transform([[1, 0]])[0]
        self.viewer.axes.figure.canvas.button_press_event(x, y, 1)
        self.viewer.axes.figure.canvas.button_release_event(x, y, 1)
        assert len(self.data_collection) == 2

        derived3 = self.data_collection[1]
        assert derived3 is not derived1
        assert derived3.label == "d1[1,0,:]"
        assert derived3.shape == (2,)
        assert_allclose(derived3["x"], self.data["x"][1, 0, :])
