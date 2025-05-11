import asyncio
import tempfile
import cv2
import os
from aiogram.types import FSInputFile
from PyQt5.QtCore import QObject, pyqtSlot
from utils.classic_detector_worker import MotionDetectorWorker
from utils.yolo_detector_worker import YoloDetector


class DetectorManager(QObject):
    def __init__(self, model_mode="yolo", yolo_model_path="yolo11x.pt", source=0):
        super().__init__()
        self.model_mode = model_mode
        self.yolo = YoloDetector(model_path=yolo_model_path, source=source)
        self.motion = MotionDetectorWorker(is_bot=True)

        self.motion.detection_signal.connect(self._on_motion_detected)
        self._motion_callback = None


    def start(self):
        if self.model_mode == "classic":
            self.motion.start()
        elif self.model_mode == "yolo":
            self.yolo.start()
        print(f"[DetectorManager] Активный режим: {self.model_mode}")

    def stop(self):
        if self.model_mode == "classic":
            self.motion.stop()
        elif self.model_mode == "yolo":
            self.yolo.stop()

    def restart(self):
        self.stop()
        self.start()

    def set_model_mode(self, mode: str):
        """Переключение между 'classic' и 'yolo'"""
        if self.model_mode != mode:
            self.stop()
            self.model_mode = mode
            self.start()

    def set_detection_roi(self, list_rects):
        """Установка ROI только для классического детектора"""
        if self.model_mode == "classic":
            self.motion.set_roi(list_rects)

    def set_notification_target(self, bot, chat_id):
        print(f"[DetectorManager] Подключаем обработчик уведомлений для {self.model_mode}")
        loop = asyncio.get_running_loop()

        def send_detection_message(label, frame):
            async def send_alert():
                try:
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
                        img_path = tmp_img.name
                        cv2.imwrite(img_path, frame)

                    await bot.send_photo(chat_id, FSInputFile(img_path),
                                         caption=f"🚨 Обнаружено: <b>{label}</b>",
                                         parse_mode="HTML")
                finally:
                    if os.path.exists(img_path):
                        os.remove(img_path)

            loop.call_soon_threadsafe(asyncio.create_task, send_alert())

        self._motion_callback = send_detection_message
        self.motion.set_notification_callback(send_detection_message)
        self.yolo.set_notification_callback(send_detection_message)

    @pyqtSlot(list)
    def _on_motion_detected(self, detections):
        print("[DetectorManager] Получено событие движения:", detections)
