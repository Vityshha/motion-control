import os
import time
import cv2
import numpy as np
import threading
import collections
from PyQt5.QtCore import QObject, pyqtSignal
from models.settings_manager import settings_manager


class MotionDetectorWorker(QObject):
    detection_signal = pyqtSignal(list)

    RECORDING_TIME = 5              # Время записи (сек)
    STORAGE_TIME = 7                # Время хранения записей (дней)
    REPEAT_DETECTION_COOLDOWN = 5   # Задержка между уведомлениями (сек)

    def __init__(self, is_bot=False):
        super().__init__()
        self.running = False
        self.thread = None
        self.cap = None
        self.roi_list = []
        self.is_bot = is_bot

        self.notification_callback = None

        self.video_dir = "videos"
        os.makedirs(self.video_dir, exist_ok=True)

        self.last_motion_time = 0

        self._connect_settings()
        self.apply_current_settings()

    def _connect_settings(self):
        settings_manager.settings_changed.connect(self._on_settings_changed)

    def apply_current_settings(self):
        settings = settings_manager.settings
        self.ostov_size = settings["ostov_size"]
        self.p_dop = settings["p_dop"]
        self.time_sleep = settings["time_sleep"]
        self.use_filter = settings["use_filter"]
        self.is_webcam = settings["is_webcam"]
        self.rtsp_or_path = settings["rtsp_or_path"]
        self.ostov_template = np.ones((self.ostov_size, self.ostov_size), dtype=np.uint8)

    def set_notification_callback(self, callback):
        self.notification_callback = callback

    def set_roi(self, roi_list):
        self.roi_list = [tuple(map(int, roi)) for roi in roi_list if len(roi) == 4]

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.thread:
            self.thread.join()

    def _on_settings_changed(self, new_settings):
        self.apply_current_settings()
        if self.running and ("is_webcam" in new_settings or "rtsp_or_path" in new_settings):
            self.stop()
            self.start()

    def _init_video_capture(self):
        if self.is_webcam:
            self.cap = cv2.VideoCapture(0)
        else:
            self.cap = cv2.VideoCapture(self.rtsp_or_path) if self.rtsp_or_path else cv2.VideoCapture(0)

    def _cleanup_old_videos(self):
        now = time.time()
        for fname in os.listdir(self.video_dir):
            fpath = os.path.join(self.video_dir, fname)
            if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > self.STORAGE_TIME * 86400:
                os.remove(fpath)

    def _run(self):
        print("[MotionDetectorWorker] Классическая детекция запущена")
        self._init_video_capture()
        self._cleanup_old_videos()
        prev_gray = None

        frame_buffer = collections.deque(maxlen=150)  # ~5 сек при 30 FPS
        recording = False
        recording_start = 0
        video_writer = None
        video_path = None

        last_process_time = time.time()

        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            now = time.time()
            frame_buffer.append(frame.copy())

            if self.is_bot:
                height, width = frame.shape[:2]
                self.roi_list = [(0, 0, width, height)]

            if now - last_process_time < self.time_sleep:
                if recording and video_writer:
                    video_writer.write(frame)
                continue
            last_process_time = now

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self.use_filter:
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_gray is None:
                prev_gray = gray
                continue

            diff = cv2.absdiff(gray, prev_gray)
            _, diff_thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            if self.use_filter:
                diff_thresh = cv2.morphologyEx(diff_thresh, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

            prev_gray = gray.copy()

            detections = []
            motion_detected = False
            for roi in self.roi_list:
                x, y, w, h = map(int, roi)
                roi_mask = diff_thresh[y:y + h, x:x + w]
                if roi_mask.size == 0:
                    detections.append({'roi': roi, 'detected': False, 'activity': 0.0})
                    continue

                img_bin = (roi_mask // 255).astype(np.uint8)
                p = np.sum(img_bin) / img_bin.size

                if p < self.p_dop:
                    detections.append({'roi': roi, 'detected': False, 'activity': p})
                    continue

                found = self._scan_for_template(img_bin, self.ostov_template)
                detections.append({'roi': roi, 'detected': found, 'activity': p})

                if found:
                    current_time = time.time()
                    if current_time - self.last_motion_time > self.REPEAT_DETECTION_COOLDOWN:
                        motion_detected = True
                        self.last_motion_time = current_time
                        if self.notification_callback:
                            self.notification_callback("motion", frame.copy())

            if motion_detected and not recording:
                recording = True
                recording_start = time.time()
                height, width = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"{timestamp}_motion.mp4"
                video_path = os.path.join(self.video_dir, filename)
                video_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))
                for f in frame_buffer:
                    video_writer.write(f)
                print(f"[MotionDetectorWorker] Начата запись: {video_path}")

            if recording and video_writer:
                video_writer.write(frame)
                if time.time() - recording_start > self.RECORDING_TIME:
                    recording = False
                    video_writer.release()
                    video_writer = None
                    with open("log.txt", "a", encoding="utf-8") as log:
                        log.write(f"{timestamp} — обнаружено движение — {filename}\n")
                    print(f"[MotionDetectorWorker] Завершена запись: {video_path}")

            self.detection_signal.emit(detections)

        self.cap.release()
        if video_writer:
            video_writer.release()
        print("[MotionDetectorWorker] Остановлен")

    def _scan_for_template(self, area_matrix, template):
        h, w = template.shape
        H, W = area_matrix.shape
        for y in range(H - h + 1):
            for x in range(W - w + 1):
                block = area_matrix[y:y + h, x:x + w]
                if np.array_equal(block, template):
                    return True
        return False
