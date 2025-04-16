import time
import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from models.settings_manager import settings_manager


class MotionDetectorWorker(QObject):
    frame_processed = pyqtSignal(np.ndarray, np.ndarray)
    detection_signal = pyqtSignal(list)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running = False
        self.cap = None
        self.roi_list = []
        self.accumulated_diff = None
        self.activity_map = None
        self.current_object_mask = None

        # Инициализация параметров
        self._connect_settings()
        self.apply_current_settings()

    def _connect_settings(self):
        settings_manager.settings_changed.connect(self._on_settings_changed)

    def apply_current_settings(self):
        """Обновление параметров из менеджера настроек"""
        settings = settings_manager.settings
        self.ostov_size = settings["ostov_size"]        # Размер остова, задает форму активности (паттерн)
        self.p_dop = settings['p_dop']                  # Порог чувствительности

        self.time_sleep = settings['time_sleep']
        self.use_filter = settings["use_filter"]
        self.is_webcam = settings["is_webcam"]
        self.rtsp_or_path = settings["rtsp_or_path"]

        self.ostov_template = np.ones((self.ostov_size, self.ostov_size), dtype=np.uint8)  # Остов из единиц


    @pyqtSlot(dict)
    def _on_settings_changed(self, new_settings):
        """Обработка изменений настроек"""
        self.apply_current_settings()
        if self.running and ("is_webcam" in new_settings or "rtsp_or_path" in new_settings):
            self.restart_detector()

    def restart_detector(self):
        """Перезапуск детектора с новыми настройками"""
        self.stop_detection()
        self.start_detection()

    @pyqtSlot()
    def start_detection(self):
        """Запуск процесса детекции"""
        self.running = True
        self._init_video_capture()
        self.accumulated_diff = None
        self.activity_map = None
        self.process_frames()

    def _init_video_capture(self):
        """Инициализация видеопотока"""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.is_webcam:
            self.cap = cv2.VideoCapture(0)
        else:
            self.cap = cv2.VideoCapture(self.rtsp_or_path) if self.rtsp_or_path else cv2.VideoCapture(0)

    @pyqtSlot()
    def stop_detection(self):
        """Остановка процесса детекции"""
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        self.finished.emit()

    @pyqtSlot(list)
    def set_roi(self, roi_list):
        """Обновление списка областей интереса"""
        self.roi_list = [tuple(map(int, roi)) for roi in roi_list if len(roi) == 4]

    def process_frames(self):
        """Обработка кадров с анализом изменений на основе p_dop и ostov"""

        prev_gray = None

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self.use_filter:
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_gray is None:
                prev_gray = gray
                continue

            # 1. Вычисляем разницу между текущим и предыдущим кадром
            diff = cv2.absdiff(gray, prev_gray)
            _, diff_thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

            if self.use_filter:
                diff_thresh = cv2.morphologyEx(diff_thresh, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

            prev_gray = gray.copy()  # Обновляем предыдущий кадр

            detections = []
            for idx, roi in enumerate(self.roi_list):
                if len(roi) != 4:
                    continue
                time_start = time.time()
                x, y, w, h = map(int, roi)
                roi_mask = diff_thresh[y:y + h, x:x + w]
                if roi_mask.size == 0:
                    time_end = time.time()
                    detections.append({'roi': roi, 'detected': False, 'activity': 0.0, 'time': time_end - time_start})
                    continue

                # 2: Бинаризация
                img_anobl = (roi_mask // 255).astype(np.uint8)
                # 3: Кол-во единиц
                b = np.sum(img_anobl)
                # 4: Относительная плотность
                p = b / img_anobl.size

                if p < self.p_dop:
                    # Если уровень активности меньше порога, то допустимое движение
                    time_end = time.time()
                    detections.append({'roi': roi, 'detected': False, 'activity': p, 'time': time_end - time_start})
                    continue

                # 5: Поиск остова
                found = self._scan_for_template(img_anobl, self.ostov_template)
                # if found: движение недопустимо
                # else: движение допустимо
                time_end = time.time()
                detections.append({'roi': roi, 'detected': found, 'activity': p, 'time': time_end - time_start})

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            bin_frame = cv2.cvtColor(diff_thresh, cv2.COLOR_GRAY2RGB)
            self.frame_processed.emit(rgb_frame, bin_frame)
            self.detection_signal.emit(detections)

            time.sleep(self.time_sleep)

        self.stop_detection()

    def _scan_for_template(self, area_matrix, template):
        """Проверка, есть ли в area_matrix блок, совпадающий с template"""
        h, w = template.shape
        H, W = area_matrix.shape

        for y in range(H - h + 1):
            for x in range(W - w + 1):
                block = area_matrix[y:y + h, x:x + w]
                if np.array_equal(block, template):
                    return True
        return False