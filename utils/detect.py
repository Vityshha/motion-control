import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot

from utils.detector_worker import MotionDetectorWorker


class MotionDetector(QObject):
    def __init__(self):
        super().__init__()
        self.worker = MotionDetectorWorker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.start_detection)
        self.worker.finished.connect(self.thread.quit)

    def start(self):
        if not self.thread.isRunning():
            self.thread.start()

    def stop(self):
        self.worker.stop_detection()

    def restart(self):
        self.stop()
        self.start()

    def set_detection_roi(self, x, y, w, h):
        self.worker.set_roi(x, y, w, h)