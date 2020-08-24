import os
import unittest.mock as mock

import numpy as np
import pytest
from glue_solar.instruments.iris import read_iris_raster


DATA = os.path.join(os.path.dirname(__file__), 'data')


def test_iris_raster_reader():
    """
    To test whether the read_iris_raster is returning a list or a str
    """

    with mock.patch('glue_solar.instruments.iris', return_value=np.zeros((42, 42, 42))) \
            as mock_iris:
        raster_data = mock_iris.read_iris_raster(os.path.join(DATA, 'iris_test_data'))
        print(type(raster_data))
        assert isinstance(raster_data, list) is False
