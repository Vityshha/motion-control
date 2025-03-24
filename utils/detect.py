import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal


class MotionDetector(QObject):

    signal_send_frame = pyqtSignal(np.ndarray)
    signal_send_binary_frame = pyqtSignal(np.ndarray)
    signal_detect = pyqtSignal(bool)

    def __init__(self):
        super(MotionDetector, self).__init__()
        self.running = False
        self.alpha = 0.95
        self.activity_alpha = 0.9
        self.activity_threshold = 0.3
        self.min_object_area = 500
        self.accumulated_diff = None
        self.activity_map = None
        self.cap = None

    def start(self):
        """Запуск детекции"""
        if not self.running:
            self.running = True
            self.cap = cv2.VideoCapture(0)
            self.accumulated_diff = None
            self.activity_map = None

    def stop(self):
        """Остановка детекции"""
        if self.running:
            self.running = False
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()

    def update_settings(self, alpha=None, activity_alpha=None,
                       activity_threshold=None, min_object_area=None):
        """Обновление параметров на лету"""
        if alpha is not None:
            self.alpha = alpha
        if activity_alpha is not None:
            self.activity_alpha = activity_alpha
        if activity_threshold is not None:
            self.activity_threshold = activity_threshold
        if min_object_area is not None:
            self.min_object_area = min_object_area

    def run(self):
        """Основной цикл обработки"""
        while True:
            if not self.running:
                # Пауза при остановке
                key = cv2.waitKey(100)
                if key == ord('q'):
                    break
                continue

            ret, frame = self.cap.read()
            if not ret:
                break

            # Предобработка
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if self.accumulated_diff is None:
                self.accumulated_diff = gray.astype("float32")
                self.activity_map = np.zeros_like(gray, dtype="float32")
                continue

            # Обработка кадра
            current_diff = cv2.absdiff(gray, cv2.convertScaleAbs(self.accumulated_diff))
            _, threshold_diff = cv2.threshold(current_diff.astype("uint8"), 25, 255, cv2.THRESH_BINARY)

            self.accumulated_diff = self.alpha * self.accumulated_diff + (1 - self.alpha) * gray.astype("float32")
            self.activity_map = self.activity_alpha * self.activity_map + (1 - self.activity_alpha) * (threshold_diff / 255.0)

            _, object_mask = cv2.threshold((self.activity_map * 255).astype("uint8"),
                                         int(self.activity_threshold * 255), 255, cv2.THRESH_BINARY)

            object_mask = cv2.morphologyEx(object_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
            contours, _ = cv2.findContours(object_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            object_mask_filtered = np.zeros_like(object_mask)
            for cnt in contours:
                if cv2.contourArea(cnt) > self.min_object_area:
                    cv2.drawContours(object_mask_filtered, [cnt], -1, 255, -1)

            self.signal_send_frame.emit(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self.signal_send_binary_frame.emit(cv2.cvtColor(object_mask_filtered, cv2.COLOR_BGR2RGB))

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):  # Пауза/старт по клавише 'p'
                self.running = not self.running

        self.stop()