import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot

from utils.detector_worker import MotionDetectorWorker


class MotionDetector(QObject):
    signal_send_frame = pyqtSignal(np.ndarray)
    signal_send_binary_frame = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.worker = MotionDetectorWorker()
        self.thread = QThread()

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start_detection)
        self.thread.finished.connect(self.worker.deleteLater)

        self.worker.frame_processed.connect(self.handle_frames)


    def start(self):
        """Запуск потока обработки"""
        if not self.thread.isRunning():
            self.thread.start()

    def stop(self):
        """Остановка потока обработки"""
        self.worker.stop_detection()
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(1000)

    def handle_frames(self, frame, bin_frame):
        """Обработка полученных кадров"""
        self.signal_send_frame.emit(frame)
        self.signal_send_binary_frame.emit(bin_frame)

    @pyqtSlot(int, int, int, int)
    def set_detection_roi(self, x, y, w, h):
        """Установка области для постоянного мониторинга движения"""
        self.worker.set_roi(x, y, w, h)

    def update_settings(self, alpha, activity_alpha, activity_threshold, detection_threshold, min_object_area, use_filter):
        """Обновление параметров детекции"""
        self.worker.update_settings(alpha, activity_alpha, activity_threshold, detection_threshold,  min_object_area, use_filter)