import time

from glue.utils import defer_draw
from glue.viewers.matplotlib.qt.compute_worker import ComputeWorker

from glue_solar.pixel_tool.layer_artist import PixelLayerArtist

__all__ = ["QThreadedPixelLayerArtist"]


class QThreadedPixelLayerArtist(PixelLayerArtist):
    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)
        self.setup_thread()

    def wait(self):
        # Wait 0.5 seconds to make sure that the computation has properly started
        time.sleep(0.5)
        while self._worker.running:
            time.sleep(1 / 25)
        from glue.utils.qt import process_events

        process_events()

    def remove(self):
        super().remove()
        if self._worker is not None:
            self._worker.work_queue.put("stop")
            self._worker.exit()
            # Need to wait otherwise the thread will be destroyed while still
            # running, causing a segmentation fault
            self._worker.wait()
            self._worker = None

    @property
    def is_computing(self):
        return self._worker is not None and self._worker.running

    def setup_thread(self):
        self._worker = ComputeWorker(self._calculate_profile_thread)
        self._worker.compute_end.connect(self._calculate_profile_postthread)
        self._worker.compute_error.connect(self._calculate_profile_error)
        self._worker.compute_start.connect(self.notify_start_computation)
        self._worker.start()

    @defer_draw
    def _calculate_profile(self, reset=False):
        if self.state.layer is not None and self.state.layer.size > 1e7:
            self._worker.work_queue.put(reset)
        else:
            super()._calculate_profile(reset=reset)

    def _calculate_profile_postthread(self):
        # If the worker has started running again, we should stop at this point
        # since this function will get called again.
        if self._worker is not None and self._worker.running:
            return
        super()._calculate_profile_postthread()
