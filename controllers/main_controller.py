from PyQt5.QtCore import pyqtSlot
from models.settings_manager import settings_manager
from views.main_window import MainWindow
from utils.detect import MotionDetector


class MainController:
    def __init__(self, main_window):
        self.views = main_window
        self.detector = MotionDetector()
        self.connect_signals()

    def connect_signals(self):
        self.views.signal_run.connect(self.algo_run)
        self.views.signal_send_rect.connect(self.detector.set_detection_roi)
        self.detector.worker.frame_processed.connect(self.views.put_frame)
        self.detector.worker.detection_signal.connect(self.views.put_detect_status)
        settings_manager.settings_changed.connect(self._handle_settings_change)


    def algo_run(self, launch):
        if launch:
            self.detector.start()
        else:
            self.detector.stop()
            self.views.clear_holst()

    def _handle_settings_change(self, new_settings):
        # if {"is_webcam", "rtsp_or_path"} & new_settings.keys():
        #     # if self.detector.worker.running:
        #     #     self.detector.restart()
        #     pass
        self.detector.worker._apply_current_settings()