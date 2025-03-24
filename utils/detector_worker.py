import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class MotionDetectorWorker(QObject):
    frame_processed = pyqtSignal(np.ndarray, np.ndarray)
    detection_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.running = False
        self.cap = None
        self.current_roi = None

        # Параметры детекции
        self.alpha = 0.95
        self.activity_alpha = 0.9
        self.activity_threshold = 0.3
        self.detection_threshold = 0.02  # 2% порог заполнения
        self.min_object_area = 500

        # Состояние обработки
        self.accumulated_diff = None
        self.activity_map = None
        self.current_object_mask = None

    @pyqtSlot()
    def start_detection(self):
        """Запуск детекции в отдельном потоке"""
        self.running = True
        self.cap = cv2.VideoCapture(0)
        self.accumulated_diff = None
        self.activity_map = None
        self.process_frames()

    @pyqtSlot()
    def stop_detection(self):
        """Остановка детекции"""
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()

    @pyqtSlot(float, float, float, float)
    def update_settings(self, alpha, activity_alpha, activity_threshold, min_object_area):
        """Обновление параметров детекции"""
        self.alpha = alpha
        self.activity_alpha = activity_alpha
        self.activity_threshold = activity_threshold
        self.min_object_area = min_object_area

    @pyqtSlot(int, int, int, int)
    def set_roi(self, x, y, w, h):
        """Установка новой области интереса"""
        self.current_roi = (x, y, w, h)

    def process_frames(self):
        """Основной цикл обработки кадров"""
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            # Предобработка кадра
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # Инициализация фоновой модели
            if self.accumulated_diff is None:
                self.accumulated_diff = gray.astype("float32")
                self.activity_map = np.zeros_like(gray, dtype="float32")
                continue

            # Вычисление разницы с фоном
            current_diff = cv2.absdiff(gray, cv2.convertScaleAbs(self.accumulated_diff))
            _, threshold_diff = cv2.threshold(current_diff.astype("uint8"), 25, 255, cv2.THRESH_BINARY)

            # Обновление фоновой модели и карты активности
            self.accumulated_diff = self.alpha * self.accumulated_diff + (1 - self.alpha) * gray.astype("float32")
            self.activity_map = self.activity_alpha * self.activity_map + (1 - self.activity_alpha) * (
                        threshold_diff / 255.0)

            # Постобработка маски
            _, object_mask = cv2.threshold((self.activity_map * 255).astype("uint8"),
                                           int(self.activity_threshold * 255), 255, cv2.THRESH_BINARY)
            object_mask = cv2.morphologyEx(object_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

            # Фильтрация контуров
            contours, _ = cv2.findContours(object_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            object_mask_filtered = np.zeros_like(object_mask)
            for cnt in contours:
                if cv2.contourArea(cnt) > self.min_object_area:
                    cv2.drawContours(object_mask_filtered, [cnt], -1, 255, -1)

            # Сохранение и передача результатов
            self.current_object_mask = object_mask_filtered
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            bin_frame = cv2.cvtColor(object_mask_filtered, cv2.COLOR_GRAY2RGB)
            self.frame_processed.emit(rgb_frame, bin_frame)

            if self.current_roi:
                x, y, w, h = self.current_roi
                self.check_movement(x, y, w, h)

        self.stop_detection()

    def check_movement(self, x, y, w, h):
        """Проверка движения в указанной области"""
        if self.current_object_mask is None:
            return

        mask_height, mask_width = self.current_object_mask.shape[:2]

        # Проверка валидности координат
        x1 = max(int(x), 0)
        y1 = max(int(y), 0)
        x2 = min(int(x + w), mask_width)
        y2 = min(int(y + h), mask_height)

        if x1 >= x2 or y1 >= y2:
            return

        # Анализ области интереса
        roi = self.current_object_mask[y1:y2, x1:x2]
        if roi.size == 0:
            return

        # Расчет активности
        active_pixels = cv2.countNonZero(roi)
        activity_ratio = active_pixels / roi.size
        detected = activity_ratio > self.detection_threshold

        # Отправка сигнала
        self.detection_signal.emit(detected)
        if detected:
            print(f"Movement in ROI [{x1}:{x2}, {y1}:{y2}] - Activity: {activity_ratio:.2%}")
        else:
            print('')