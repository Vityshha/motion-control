import os
import cv2
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal
from ultralytics import YOLO
from ultralytics.utils import LOGGER
import collections

class YoloDetector(QObject):

    detect_signal = pyqtSignal(str)

    RECORDING_TIME = 5              # Время записи (сек)
    STORAGE_TIME = 7                # Время хранения записей (дни)
    REPEAT_DETECTION_COOLDOWN = 5   # Задержка между повторными уведомлениями о том же объекте (сек)

    def __init__(self, model_path="yolo11n.pt", source=0):
        super().__init__()
        LOGGER.setLevel("WARNING")
        self.model = YOLO(model_path)
        self.source = source
        self.running = False
        self.thread = None

        self.video_dir = "videos"
        os.makedirs(self.video_dir, exist_ok=True)

        self.target_classes = ["person", "cat"]
        self.class_names = self.model.names
        self.target_ids = [cls_id for cls_id, name in self.class_names.items() if name in self.target_classes]

        self.last_seen = {label: 0 for label in self.target_classes}
        self.active_flags = {label: False for label in self.target_classes}
        self.notification_callback = None


    def set_notification_callback(self, callback):
        self.notification_callback = callback


    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()


    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        cv2.destroyAllWindows()


    def _cleanup_old_videos(self, days=7):
        now = time.time()
        for fname in os.listdir(self.video_dir):
            fpath = os.path.join(self.video_dir, fname)
            if os.path.isfile(fpath):
                if now - os.path.getmtime(fpath) > days * 86400:
                    os.remove(fpath)


    def _run(self):
        self._cleanup_old_videos()
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            print(f"[ERROR] Не удалось открыть источник видео: {self.source}")
            self.running = False
            return

        print("[INFO] YOLO-детектор запущен.")

        frame_buffer = collections.deque(maxlen=150)  # ~5 секунд при 30 FPS
        recording = False
        recording_start = 0
        video_writer = None
        video_path = None

        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_time = time.time()
            detected_labels = set()
            frame_buffer.append(frame.copy())

            results = self.model(frame, stream=True)
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    if cls_id in self.target_ids:
                        label = self.class_names[cls_id]
                        detected_labels.add(label)

                        if current_time - self.last_seen[label] > self.REPEAT_DETECTION_COOLDOWN:
                            if not self.active_flags[label]:

                                # Запуск записи видео
                                if not recording:
                                    recording = True
                                    recording_start = time.time()

                                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                                    height, width = frame.shape[:2]

                                    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                                    filename = f"{timestamp}_{label}.mp4"
                                    video_path = os.path.join(self.video_dir, filename)

                                    video_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))

                                    # Сохраняем буфер до срабатывания
                                    for buffered_frame in frame_buffer:
                                        video_writer.write(buffered_frame)

                                if self.notification_callback:
                                    self.notification_callback(label, frame.copy())

                                self.active_flags[label] = True
                        self.last_seen[label] = current_time


            if recording and video_writer:
                video_writer.write(frame)
                if time.time() - recording_start > self.RECORDING_TIME:
                    recording = False
                    video_writer.release()
                    video_writer = None
                    with open("log.txt", "a", encoding="utf-8") as log:
                        log.write(f"{timestamp} — обнаружен {label} — {filename}\n")
                    print(f"[INFO] Видео записано: {video_path}")

            for label in self.target_classes:
                if label not in detected_labels and self.active_flags[label]:
                    if current_time - self.last_seen[label] > self.REPEAT_DETECTION_COOLDOWN:
                        self.active_flags[label] = False

        cap.release()
        if video_writer:
            video_writer.release()
        self.running = False
        print("[INFO] YOLO-детектор остановлен.")
